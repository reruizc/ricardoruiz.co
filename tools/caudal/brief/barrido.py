#!/usr/bin/env python3
"""
Barrido parametrizado — el insumo del brief, derivado de la FICHA del cliente.

QUÉ RESUELVE. `barrido_binance.py` tiene las treinta consultas escritas a mano:
los temas, los reguladores, los diecisiete países. Para tres cuentas de piloto
eso son tres archivos que hay que mantener cada vez que un cliente cambia de
foco. Acá las consultas se DERIVAN del perfil, así que sirve para cualquier
cliente sin escribir una línea nueva.

DE DÓNDE SALE CADA CONSULTA (y por qué la ficha es lo que lo hace posible):
  · `lineas`         → una consulta de Congreso por línea de negocio, con sus
                       temas. Es lo que hace que el brief hable de negocios y no
                       de comisiones: DiDi cae en cuatro comisiones distintas.
  · `temas`          → Congreso, Ejecutivo y consultas públicas (SUCOP).
  · `empresas` y
    `competencia`    → identidad: sanciones, contratación y prensa con el nombre
                       propio de la empresa. El diccionario ya sabe traducirlo.
  · `interlocutores` → prensa institucional: qué dijo su supervisor.
  · `jurisdicciones` → prensa del país, y lo que está fuera de Colombia se
                       declara sin cobertura en vez de dejarlo asumir.
  · `no_interesa`    → se marca el ruido ANTES de que llegue al modelo.

NO llama acciones caras (nada de lectura del modelo), así que corre sin
credencial y cuesta cero.

VENTANA. 72 horas por defecto — es la ventana del brief. Con una ventana tan
corta, lo que NO se movió importa tanto como lo que sí, así que el barrido
separa lo que se movió de lo que solo está vigente, y declara hasta dónde llega
cada registro (el del Ejecutivo se publica con ~16 días de rezago: reportar 0
sin decirlo haría que el brief afirmara que no pasó nada).

  python3 tools/caudal/brief/barrido.py cauce                 # un preset, 72 h
  python3 tools/caudal/brief/barrido.py cauce --dias 7        # una semana
  python3 tools/caudal/brief/barrido.py --perfil perfil.json  # un perfil guardado
  python3 tools/caudal/brief/barrido.py cauce --json salida.json --texto brief.txt
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import caudal_core  # noqa: E402

W = 'https://rr-auth.reruizc.workers.dev/caudal/api'
S3 = ('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/'
      'congreso-2026/output/legislativo/')
UA = 'caudal-brief/2.0 (+ricardoruiz.co)'
# El proxy limita por IP (60/min anónimo). Seis en vuelo deja margen y no
# convierte un barrido en un 429 a mitad de camino.
CONCURRENCIA = 6
# Tope de titulares por consulta de prensa (ver el bucle de medios).
MEDIOS_POR_CONSULTA = 12


def post(payload, timeout=70):
    req = urllib.request.Request(
        W, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:                                       # noqa: BLE001
        return {'error': str(e)[:140]}


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# Medios extranjeros reconocibles por dominio. El pilar ya le agrega «Colombia»
# a la consulta, pero Google News igual trae vecinos: medido, «reforma electoral»
# devolvió media página de Milei y del PVEM mexicano. Para un cliente que solo
# opera en Colombia eso no es contexto, es ruido que le quita espacio a lo suyo.
_DOM_EXTRANJERO = ('.ar', '.mx', '.cl', '.pe', '.uy', '.py', '.bo', '.ec',
                   '.ve', '.es', '.gt', '.cr', '.pa', '.do', '.hn', '.sv', '.ni')
_PISTAS_EXTRANJERO = ('milei', 'sheinbaum', 'kicillof', 'casa rosada', 'psoe',
                      'pvem', 'boric', 'bukele', 'maduro', 'lula', 'bolsonaro')


def _es_extranjero(medio, titulo):
    """¿Esta nota es de otro país y no menciona Colombia?"""
    m = (medio or '').lower()
    t = (titulo or '').lower()
    if 'colombia' in t or 'colombia' in m:
        return False
    if any(m.endswith(d) or d + '/' in m for d in _DOM_EXTRANJERO):
        return True
    return any(x in t for x in _PISTAS_EXTRANJERO)


def _norm_titular(t):
    """Titular sin tildes ni puntuación, para reconocer la misma nota."""
    import re
    import unicodedata
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', t).strip()[:70]


def iso(f):
    """Las fechas llegan 2026-09-02 o 2026/09/02 según la fuente."""
    return (f or '')[:10].replace('/', '-')


# ── qué se le pregunta a cada pilar, derivado del perfil ───────────────────
def plan_de_consultas(p, dias):
    """Perfil → las consultas que hay que correr, ya etiquetadas.

    Devuelve una lista de (clave, payload). La clave dice de dónde salió la
    consulta, para poder atribuir cada hallazgo a su origen en el brief.
    """
    temas = list(p.get('temas') or [])
    jobs = []

    # Congreso · por LÍNEA de negocio primero (con sus temas), y después los
    # temas sueltos que ninguna línea cubre. Sin esto, una empresa multinegocio
    # recibe un solo montón indiferenciado.
    cubiertos = set()
    for ln in (p.get('lineas') or []):
        for t in (ln.get('temas') or []):
            cubiertos.add(t.lower())
            jobs.append((f"congreso::linea::{ln['nombre']}::{t}",
                         {'action': 'tema', 'query': t, 'lectura': False}))
    for t in temas:
        if t.lower() in cubiertos:
            continue
        jobs.append((f'congreso::tema::{t}',
                     {'action': 'tema', 'query': t, 'lectura': False}))

    # Regulatorio · por sector declarado y por identidad de cada vigilada.
    if p.get('sector_sanciones'):
        jobs.append((f"regulatorio::sector::{p['sector_sanciones']}",
                     {'action': 'sanciones', 'sector': p['sector_sanciones'],
                      'tipo_acto': 'todo'}))
    for e in (p.get('empresas') or []) + (p.get('competencia') or []):
        nombre = e['nombre'] if isinstance(e, dict) else str(e)
        jobs.append((f'regulatorio::empresa::{nombre}',
                     {'action': 'sanciones', 'query': nombre, 'tipo_acto': 'todo'}))
    # Sin vigiladas —una consultora, un gremio— el pilar quedaba MUDO: todas sus
    # consultas salían de `empresas`. Los interlocutores lo destapan: lo que
    # hace el supervisor es noticia aunque no sancione a nadie del cliente.
    if not (p.get('empresas') or p.get('competencia')):
        for ent in (p.get('interlocutores') or [])[:6]:
            jobs.append((f'regulatorio::entidad::{ent}',
                         {'action': 'sanciones', 'query': ent, 'tipo_acto': 'todo'}))

    # Ejecutivo y consultas públicas · por tema. SUCOP importa por el plazo:
    # una consulta abierta se cuenta en días, no en meses.
    for t in temas[:8]:
        jobs.append((f'ejecutivo::tema::{t}', {'action': 'ejecutivo', 'query': t}))
        jobs.append((f'sucop::tema::{t}', {'action': 'sucop', 'query': t}))
    jobs.append(('sucop::abiertas', {'action': 'sucop', 'estado': 'abiertas'}))

    # Prensa · tres entradas distintas, y cada una responde otra pregunta:
    # el tema (de qué se habla), la vigilada (quién habla de mi cliente) y el
    # interlocutor (qué dijo mi supervisor).
    for t in temas[:8]:
        jobs.append((f'medios::tema::{t}',
                     {'action': 'medios', 'query': t, 'dias': dias}))
    for e in (p.get('empresas') or []) + (p.get('competencia') or []):
        nombre = e['nombre'] if isinstance(e, dict) else str(e)
        jobs.append((f'medios::empresa::{nombre}',
                     {'action': 'medios', 'query': nombre, 'dias': dias}))
    for ent in (p.get('interlocutores') or [])[:8]:
        jobs.append((f'medios::interlocutor::{ent}',
                     {'action': 'medios', 'query': ent, 'dias': dias}))

    # Contratación · solo por identidad. Un contrato importa por QUIÉN lo firma;
    # buscarlo por tema devuelve el ruido de todo el Estado comprando.
    for e in (p.get('empresas') or []) + (p.get('competencia') or []):
        nombre = e['nombre'] if isinstance(e, dict) else str(e)
        jobs.append((f'contratacion::empresa::{nombre}',
                     {'action': 'contratacion', 'query': nombre}))

    # Lo radicado en la legislatura viva: es la única fuente que responde «qué
    # entró esta semana». `tema` devuelve el histórico del tema con la fecha del
    # intento, que para una ventana de 72 horas siempre queda fuera.
    jobs.append(('radicados', {'action': 'radicados'}))
    # Cobertura del Ejecutivo: hasta qué fecha llega el registro de Presidencia.
    # Sin esto, un pilar en cero se lee como «no pasó nada» cuando lo que pasa
    # es que todavía no lo publican.
    jobs.append(('ejecutivo::cobertura', {'action': 'ejecutivo'}))

    # El radar ya priorizado, tal como lo ve el cliente en la Rosa.
    jobs.append(('radar', {'action': 'cliente',
                           'perfil': _perfil_para_api(p), 'lectura': False}))
    return jobs


def _perfil_para_api(p):
    """El perfil en la forma que acepta la acción `cliente`."""
    return {
        'nombre': p.get('nombre', ''), 'temas': list(p.get('temas') or []),
        'empresas': [e['k'] if isinstance(e, dict) else e
                     for e in (p.get('empresas') or [])],
        'competencia': [e['k'] if isinstance(e, dict) else e
                        for e in (p.get('competencia') or [])],
        'sector_sanciones': p.get('sector_sanciones', ''),
        'comision': p.get('comision', ''),
        'tipo': p.get('tipo', ''),
        'lineas': list(p.get('lineas') or []),
        'que_hace': p.get('que_hace', ''), 'lector': p.get('lector', ''),
        'decisiones': list(p.get('decisiones') or []),
        'jurisdicciones': list(p.get('jurisdicciones') or []),
        'interlocutores': list(p.get('interlocutores') or []),
        'relojes': list(p.get('relojes') or []),
        'no_interesa': list(p.get('no_interesa') or []),
    }


# ── el ruido declarado se marca, no se borra ───────────────────────────────
def _ruidoso(texto, exclusiones):
    t = (texto or '').lower()
    return [x for x in exclusiones if x.lower() in t]


def barrer(p, dias, desde):
    """Corre el plan y devuelve la evidencia agrupada por pilar."""
    jobs = plan_de_consultas(p, dias)
    with ThreadPoolExecutor(max_workers=CONCURRENCIA) as pool:
        res = list(pool.map(lambda kv: post(kv[1]), jobs))
    crudo = {k: d for (k, _), d in zip(jobs, res)}

    try:
        crudo['agenda'] = get(S3 + 'ordenes-vigentes.json')
    except Exception as e:                                       # noqa: BLE001
        crudo['agenda'] = {'error': str(e)[:120]}

    hoy = datetime.date.today().isoformat()
    excl = list(p.get('no_interesa') or [])
    solo_colombia = not (p.get('fuera_de_alcance') or [])
    ev = {'congreso': [], 'congreso_frente': [], 'regulatorio': [],
          'ejecutivo': [], 'sucop': [], 'medios': [], 'contratacion': [],
          'agenda': [], 'errores': []}
    vistos = {k: set() for k in ev}

    cobertura = {}

    def marcar_cobertura(pilar, fecha):
        f = iso(fecha)
        if f and f > cobertura.get(pilar, ''):
            cobertura[pilar] = f

    def add(pilar, llave, item, origen):
        if llave in vistos[pilar]:
            return
        vistos[pilar].add(llave)
        item['_origen'] = origen
        ruido = _ruidoso(' '.join(str(v) for v in item.values() if isinstance(v, str)), excl)
        if ruido:
            item['_ruido'] = ruido
        ev[pilar].append(item)

    for clave, d in crudo.items():
        if clave in ('agenda', 'radar'):
            continue
        if clave == 'radicados':
            # Filtra a los temas del cliente: la legislatura radica de todo, y
            # un brief que trae los 90 radicados de la semana no es un brief.
            claves_t = [t.lower().split()[0] for t in (p.get('temas') or [])]
            rs = (d.get('radicados') or []) + (d.get('radicados_camara') or [])
            for r in rs:
                f = iso(r.get('fecha'))
                marcar_cobertura('congreso', f)
                if f < desde:
                    continue
                tit = (r.get('titulo') or '')
                if claves_t and not any(k in tit.lower() for k in claves_t):
                    continue
                add('congreso', str(r.get('numero_senado') or r.get('numero_camara')
                                    or tit[:60]), {
                    'numero': r.get('numero_senado') or r.get('numero_camara') or '',
                    'anio': f[:4], 'titulo': tit, 'estado': 'RADICADO',
                    'comision': r.get('comision', ''),
                    'autores': (r.get('autores') or '')[:120]
                                if isinstance(r.get('autores'), str)
                                else (r.get('autores') or [])[:3],
                    'fecha': f,
                }, 'radicado de la ventana')
            continue
        if clave == 'ejecutivo::cobertura':
            # ⚠️ `rango_fechas` es una LISTA [desde, hasta], no un objeto.
            rango = d.get('rango_fechas') or []
            cobertura['ejecutivo'] = (rango[-1] if isinstance(rango, list) and rango
                                      else (d.get('recientes') or [{}])[0].get('fecha', ''))
            continue
        if isinstance(d, dict) and d.get('error'):
            ev['errores'].append({'consulta': clave, 'error': d['error']})
            continue
        pilar, _, origen = clave.partition('::')

        if pilar == 'congreso':
            # ⚠️ Un proyecto EN_TRAMITE de 2012 NO es noticia de esta semana, y
            # el filtro viejo los dejaba pasar todos: el barrido de Cauce salía
            # con 112 ítems, la mitad de hace más de diez años. Se separa lo que
            # SE MOVIÓ en la ventana (es noticia) de lo que solo ESTÁ vigente
            # (es el estado del frente) — la misma distinción que hace la Rosa
            # entre movimiento y estado, y la que el brief necesita para no
            # presentar como nuevo algo viejo.
            for i in ((d.get('resumen') or {}).get('intentos') or []):
                f = iso(i.get('fecha'))
                item = {
                    'numero': i.get('numero_senado') or i.get('numero_camara') or '',
                    'anio': i.get('anio'), 'titulo': i.get('titulo', ''),
                    'estado': i.get('resultado'), 'comision': i.get('comision', ''),
                    'autores': (i.get('autores') or [])[:3], 'fecha': f,
                }
                llave = str(i.get('id') or i.get('titulo', ''))[:80]
                if f >= desde:
                    add('congreso', llave, item, origen)
                elif i.get('resultado') == 'EN_TRAMITE':
                    add('congreso_frente', llave, item, origen)
        elif pilar == 'regulatorio':
            for x in (d.get('resultados') or []):
                marcar_cobertura('regulatorio', x.get('fecha'))
                if iso(x.get('fecha')) < desde:
                    continue
                add('regulatorio', str(x.get('_id') or x.get('resolucion', ''))[:80], {
                    'fecha': iso(x.get('fecha')), 'fuente': x.get('fuente_nombre', ''),
                    'tipo_acto': x.get('tipo_acto', ''),
                    'destinatario': x.get('sancionado', ''),
                    'motivo': (x.get('motivo') or x.get('descripcion') or '')[:300],
                    'resolucion': x.get('resolucion', ''),
                }, origen)
        elif pilar == 'ejecutivo':
            # El registro de Presidencia se publica con rezago (medido: ~16
            # días). Reportar 0 a secas haría que el brief dijera «no se movió
            # nada», que es distinto de «todavía no lo han publicado». La
            # cobertura real se guarda aparte y el brief la declara.
            for x in (d.get('resultados') or []):
                ev.setdefault('_eje_ultima', '')
                if iso(x.get('fecha')) > ev['_eje_ultima']:
                    ev['_eje_ultima'] = iso(x.get('fecha'))
                if iso(x.get('fecha')) < desde:
                    continue
                add('ejecutivo', str(x.get('titulo', ''))[:80], {
                    'fecha': iso(x.get('fecha')), 'tipo': x.get('tipo', ''),
                    'titulo': x.get('titulo', ''),
                    'descripcion': (x.get('descripcion') or '')[:300],
                    'url': x.get('url', ''),
                }, origen)
        elif pilar == 'sucop':
            # ⚠️ Las consultas por TEMA traen el histórico completo, con cierres
            # de 2021: una consulta ya cerrada no es una oportunidad, es una
            # que se perdió. Solo entra lo que todavía se puede comentar.
            for x in (d.get('resultados') or []):
                cierra = iso(x.get('fecha_fin') or x.get('cierra', ''))
                if cierra and cierra < hoy:
                    continue
                # Una consulta por TEMA sin fecha de cierre es casi siempre
                # histórico sin cerrar en la fuente. La lista de `abiertas` sí
                # está curada por el propio pilar, así que esa entra completa.
                if not cierra and origen != 'abiertas':
                    continue
                add('sucop', str(x.get('titulo', ''))[:80], {
                    'entidad': x.get('entidad', ''), 'titulo': x.get('titulo', ''),
                    'estado': x.get('estado_consulta', ''),
                    'cierra': cierra or 'sin fecha de cierre publicada',
                }, origen)
        elif pilar == 'medios':
            # Tope por consulta: sin esto «presupuesto» aporta 300 titulares y
            # los demás temas del cliente desaparecen del brief por volumen.
            for x in (d.get('resultados') or [])[:MEDIOS_POR_CONSULTA]:
                marcar_cobertura('medios', x.get('fecha'))
                if iso(x.get('fecha')) < desde:
                    continue
                # Solo si el cliente no declara operación fuera de Colombia:
                # a Binance, que sigue seis países, la nota del vecino SÍ le
                # sirve. Lo decide la ficha, no una regla global.
                if solo_colombia and _es_extranjero(x.get('medio'), x.get('titulo')):
                    continue
                # dedup por titular normalizado: la misma nota replicada por
                # cuatro medios es UNA señal, no cuatro. Sin esto el barrido de
                # Cauce traía 671 titulares y el modelo se ahogaba en repetidos.
                add('medios', _norm_titular(x.get('titulo') or ''), {
                    'fecha': iso(x.get('fecha')), 'medio': x.get('medio', ''),
                    'titulo': x.get('titulo', ''), 'url': x.get('url', ''),
                    'alcance': x.get('alcance', ''),
                }, origen)
        elif pilar == 'contratacion':
            for x in (d.get('resultados') or [])[:12]:
                marcar_cobertura('contratacion', x.get('fecha'))
                add('contratacion', str(x.get('id') or x.get('referencia', ''))[:80], {
                    'fecha': iso(x.get('fecha')), 'entidad': x.get('entidad', ''),
                    'proveedor': x.get('proveedor', ''),
                    'objeto': (x.get('objeto') or '')[:200],
                    'valor': x.get('valor'),
                }, origen)

    # Agenda: solo lo que viene, y solo si toca un tema del cliente.
    o = crudo.get('agenda') or {}
    claves = [t.lower() for t in (p.get('temas') or [])]
    for s in (o.get('ordenes') or []):
        if iso(s.get('fecha')) < hoy:
            continue
        txt = json.dumps(s, ensure_ascii=False).lower()
        if claves and not any(k.split()[0] in txt for k in claves):
            continue
        ev['agenda'].append({
            'fecha': iso(s.get('fecha')), 'corporacion': s.get('corporacion', ''),
            'ambito': s.get('ambito', ''),
            'proyectos': [(x.get('numero') or x.get('num'), (x.get('titulo') or '')[:90])
                          for x in (s.get('proyectos') or [])][:6],
        })

    radar = crudo.get('radar') or {}
    return {
        'perfil': {k: p.get(k) for k in (
            'nombre', 'tipo', 'que_hace', 'lector', 'decisiones', 'lineas',
            'jurisdicciones', 'fuera_de_alcance', 'interlocutores', 'relojes',
            'no_interesa', 'temas', 'comision', 'sector_sanciones')},
        'ventana': {'desde': desde, 'hasta': hoy, 'dias_prensa': dias},
        'kpis': radar.get('kpis') or {},
        'evidencia': ev,
        'cobertura': cobertura,
        'n_consultas': len(jobs),
    }


def resumen_texto(b):
    """El barrido en texto plano — lo que se lee antes de escribir el brief."""
    L = []
    p, v, ev = b['perfil'], b['ventana'], b['evidencia']
    horas = v.get('dias_prensa', 3) * 24
    L.append(f"BARRIDO · {p['nombre']} · últimas {horas} horas "
             f"({v['desde']} → {v['hasta']}) · {b['n_consultas']} consultas")
    if p.get('fuera_de_alcance'):
        L.append(f"  ⚠ fuera del alcance de las fuentes: {', '.join(p['fuera_de_alcance'])}")
    for pilar in ('congreso', 'congreso_frente', 'regulatorio', 'ejecutivo',
                  'sucop', 'medios', 'contratacion', 'agenda'):
        xs = ev.get(pilar) or []
        ruido = sum(1 for x in xs if x.get('_ruido'))
        extra = ""
        cob = (b.get('cobertura') or {}).get(pilar)
        if not xs and cob:
            # Esto es lo que separa «no se movió nada» de «no lo han publicado»:
            # sin la fecha, un pilar vacío se lee como quietud del país.
            extra = (f" · sin novedades en la ventana; el registro llega hasta "
                     f"{cob} — verificado, no asumido")
        if pilar == 'congreso_frente':
            extra = " · proyectos vigentes que NO se movieron en la ventana"
        L.append(f"\n== {pilar.upper()} · {len(xs)}"
                 + (f" ({ruido} marcados como ruido declarado)" if ruido else "") + extra)
        for x in xs[:14]:
            if pilar in ('congreso', 'congreso_frente'):
                L.append(f"  - [{x['estado']}] {x['numero']} {x['titulo'][:95]}"
                         f" · {x['comision']} · ({x['_origen']})")
            elif pilar == 'regulatorio':
                L.append(f"  - {x['fecha']} {x['fuente']} · {x['tipo_acto']} · "
                         f"{x['destinatario']}: {x['motivo'][:90]}")
            elif pilar == 'ejecutivo':
                L.append(f"  - {x['fecha']} {x['tipo']}: {x['descripcion'][:110]}")
            elif pilar == 'sucop':
                L.append(f"  - {x['entidad']}: {x['titulo'][:80]} · cierra {x['cierra']}")
            elif pilar == 'medios':
                L.append(f"  - {x['fecha']} {x['medio']}: {x['titulo'][:100]}")
            elif pilar == 'contratacion':
                L.append(f"  - {x['fecha']} {x['entidad']} → {x['proveedor']}: "
                         f"{x['objeto'][:80]}")
            else:
                L.append(f"  - {x['fecha']} {x['corporacion']} {x['ambito']}: "
                         f"{x['proyectos']}")
        if len(xs) > 14:
            L.append(f"  … y {len(xs) - 14} más")
    if ev['errores']:
        L.append(f"\n== CONSULTAS QUE FALLARON · {len(ev['errores'])}")
        for e in ev['errores'][:6]:
            L.append(f"  - {e['consulta']}: {e['error']}")
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sector', nargs='?', help='llave de un preset (cauce, binance, didi…)')
    ap.add_argument('--perfil', help='archivo JSON con un perfil guardado')
    # 72 HORAS es la ventana del brief (decisión de producto, la misma que usa
    # la Rosa para separar movimiento de estado). Con una ventana tan corta, lo
    # que NO se movió importa tanto como lo que sí: por eso el barrido separa
    # `congreso` (se movió en la ventana) de `congreso_frente` (vigente, sin
    # movimiento), y declara hasta dónde llega cada registro.
    ap.add_argument('--dias', type=int, default=3,
                    help='ventana del brief en días (default 3 = 72 horas)')
    ap.add_argument('--desde', help='YYYY-MM-DD (default: hace --dias)')
    ap.add_argument('--json', help='guardar la evidencia cruda acá')
    ap.add_argument('--texto', help='guardar el resumen legible acá')
    a = ap.parse_args()

    if a.perfil:
        p = caudal_core.normalizar_perfil(json.load(open(a.perfil, encoding='utf-8')))
    elif a.sector:
        p = caudal_core.perfil_desde_sector(a.sector)
        if not p:
            sys.exit(f'no existe el preset «{a.sector}»')
    else:
        sys.exit('dame un preset o --perfil')

    desde = a.desde or (datetime.date.today()
                        - datetime.timedelta(days=a.dias)).isoformat()
    b = barrer(p, a.dias, desde)
    txt = resumen_texto(b)
    print(txt)
    if a.json:
        json.dump(b, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'\n[evidencia cruda → {a.json}]')
    if a.texto:
        open(a.texto, 'w', encoding='utf-8').write(txt)
        print(f'[resumen → {a.texto}]')


if __name__ == '__main__':
    main()
