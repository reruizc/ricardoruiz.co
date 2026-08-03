#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — motor de push.

Convierte Caudal de pull a push: corre después del cron diario, compara el
estado de hoy contra el de ayer sobre las fuentes YA publicadas, clasifica lo
nuevo por sector y nivel, y arma un digest por sector.

    python3 motor.py                       corrida normal (hoy)
    python3 motor.py --baseline            sella el estado sin enviar nada
    python3 motor.py --dry-run             calcula y escribe, no envía ni guarda estado
    python3 motor.py --fecha 2026-08-02    una fecha concreta
    python3 motor.py --sectores salud,trabajo
    python3 motor.py --sin-api             sin prensa ni contratación (offline)
    python3 motor.py --estado              qué sabe el motor hasta ahora

La PRIMERA corrida es siempre baseline: sin estado previo, todo el universo
(7.019 sanciones, 11.000 normas) contaría como "nuevo" y el primer correo
llegaría con miles de items. Se sella el estado y se avisa.
"""

import argparse
import datetime as dt
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import fuentes as F                                            # noqa: E402
import reglas as R                                             # noqa: E402
import render                                                  # noqa: E402
import sender                                                  # noqa: E402

# Datos generados. Viven bajo tools/ porque es el único árbol que esta corrida
# tiene permitido escribir; el .gitignore de al lado los mantiene fuera de git.
# Para moverlos a "Bases de datos/leyes-senado/alertas/" (que es donde el
# proyecto guarda datos) basta cambiar CAUDAL_ALERTAS_DIR.
DIR_DATOS = os.environ.get('CAUDAL_ALERTAS_DIR', os.path.join(AQUI, 'datos'))
DIR_ESTADO = os.path.join(DIR_DATOS, 'estado')
DIR_DIGESTS = os.path.join(DIR_DATOS, 'digests')
DIR_CACHE = os.path.join(DIR_DATOS, 'cache')
RUTA_ESTADO = os.path.join(DIR_ESTADO, 'estado.json')
RUTA_DESTINATARIOS = os.path.join(AQUI, 'destinatarios.json')

# Días hacia atrás que se releen de novedades. Si el motor no corrió ayer (Mac
# dormido), la corrida de hoy recupera lo de ayer sola; el estado evita repetir.
DIAS_NOVEDADES = 3

# Ventana de frescura por pilar. Protege contra el backfill: si un harvester
# reconstruye su archivo y mete filas viejas, éstas son nuevas PARA EL ESTADO
# pero no son noticia. Se marcan como vistas y se cuentan aparte.
VENTANAS = {
    'congreso': 45,
    'regulatorio': 60,
    'ejecutivo': 60,
    'contratacion': 200,     # la Lambda ya acota a 180 días por valor
    'medios': 10,
}

# Tope por pilar dentro de cada sector. Lo que sobra NO se esconde: se cuenta.
TOPE_POR_PILAR = 6

# Cuántos titulares de corroboración se cuelgan de una señal antes de resumir.
TOPE_COBERTURA = 4

# Tope de alertas de prensa-sobre-empresa por sector. Es la única prensa que
# dispara sola, así que conviene que no pueda dominar el digest ni en un día raro.
TOPE_EMPRESA_SUELTA = 5

# Un digest solo sale si tiene al menos una señal de este nivel. Ver
# `hay_algo_que_decir`: el silencio es una salida legítima del motor.
NIVEL_MINIMO_ENVIO = 'medio'

SECTOR_DE_FUENTE = {'salud': 'salud', 'contratacion': 'contratacion',
                    'financiero': 'financiero'}


# ---------------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------------

def cargar_estado():
    if os.path.exists(RUTA_ESTADO):
        try:
            return json.load(open(RUTA_ESTADO, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {'v': 1, 'creado': None, 'ultima_corrida': None, 'corridas': 0,
            'vistos': {}, 'etags': {}}


def guardar_estado(estado):
    os.makedirs(DIR_ESTADO, exist_ok=True)
    tmp = RUTA_ESTADO + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(estado, fh, ensure_ascii=False)
    os.replace(tmp, RUTA_ESTADO)          # atómico: nunca un estado a medias


def podar_estado(estado, dias=120):
    """Los pilares que churnean (prensa, contratos) no necesitan memoria eterna."""
    corte = (dt.date.today() - dt.timedelta(days=dias)).isoformat()
    for pilar in ('medios', 'contratacion'):
        v = estado['vistos'].get(pilar) or {}
        estado['vistos'][pilar] = {k: f for k, f in v.items() if f >= corte}
    return estado


# ---------------------------------------------------------------------------
# RECOLECCIÓN
# ---------------------------------------------------------------------------

def recolectar(fecha, sectores_activos, usar_api=True, avisos=None):
    """Todos los eventos crudos del día, de las 5 fuentes."""
    avisos = avisos if avisos is not None else []
    eventos = []

    # --- 1. Radicados (el diff ya lo hizo el rastreo diario) ---------------
    hoy = dt.date.fromisoformat(fecha)
    faltantes_hoy = None
    for i in range(DIAS_NOVEDADES):
        f = (hoy - dt.timedelta(days=i)).isoformat()
        ev, faltantes = F.novedades(f)
        eventos += ev
        if i == 0:
            faltantes_hoy = faltantes
    if faltantes_hoy:
        avisos.append({'tipo': 'fuente_sin_datos', 'pilar': 'congreso',
                       'texto': 'Sin archivo de novedades hoy para: '
                                + ', '.join(faltantes_hoy)
                                + '. Puede ser un día sin sesión o el rastreo caído.'})

    # --- 2. S3: sanciones + normativa --------------------------------------
    for key, lector, pilar in (
            ('metadata/sanciones.jsonl', F.sanciones, 'regulatorio'),
            ('metadata/normativa.jsonl', F.normativa, 'ejecutivo')):
        destino = os.path.join(DIR_CACHE, os.path.basename(key))
        try:
            etag = F.s3_etag(key)
            if not os.path.exists(destino) or not etag or \
                    etag != (ESTADO_ETAGS.get(key)):
                F.s3_bajar(key, destino)
                ESTADO_ETAGS[key] = etag
            eventos += lector(destino)
        except (RuntimeError, OSError, ValueError) as e:
            avisos.append({'tipo': 'fuente_error', 'pilar': pilar,
                           'texto': f'No se pudo leer {key}: {str(e)[:200]}'})

    # --- 3. API: prensa y contratación por sector ---------------------------
    if usar_api:
        for k in sectores_activos:
            s = R.sector(k) or {}
            ev, errs = F.medios_sector(k, s.get('temas', [])[:3], dias=2)
            eventos += ev
            for e in errs:
                avisos.append({'tipo': 'api_error', 'pilar': 'medios',
                               'texto': f'prensa · {k} · {e}'})
            ev, err, _kpis = F.contratos_sector(k)
            eventos += ev
            if err:
                avisos.append({'tipo': 'api_error', 'pilar': 'contratacion',
                               'texto': f'contratación · {k} · {err}'})
    else:
        avisos.append({'tipo': 'omitido', 'pilar': 'medios',
                       'texto': 'Corrida sin API: no se consultó prensa ni contratación.'})
    return eventos


ESTADO_ETAGS = {}
# entidad normalizada → categorías de contratación ya vistas. Es la memoria que
# permite decir "categoría nueva para esta entidad" sin inventarlo: arranca
# vacía y se llena con cada corrida.
HISTORICO_ENTIDAD = {}


# ---------------------------------------------------------------------------
# CLASIFICACIÓN
# ---------------------------------------------------------------------------

def clasificar(ev):
    """Evento crudo → lista de (sector, nivel, porque). Vacío = no interesa."""
    pilar = ev['pilar']

    if pilar == 'congreso':
        return _clasificar_congreso(ev)

    if pilar == 'regulatorio':
        row = ev.get('_row', {})
        nivel, porque = R.nivel_acto_regulatorio(row)
        texto = ' '.join([ev['titulo'], ev.get('detalle', ''),
                          row.get('descripcion') or ''])
        secs = {k for k, _h in R.sectores_de(texto)}
        propio = SECTOR_DE_FUENTE.get(row.get('sector') or '')
        if propio:
            secs.add(propio)          # la fuente ya lo clasificó; se respeta
        return [(k, nivel, porque) for k in secs]

    if pilar == 'ejecutivo':
        nivel, porque = R.nivel_normativa(ev.get('_row', {}))
        texto = ev['titulo'] + ' ' + ev.get('detalle', '')
        return [(k, nivel, porque) for k, _h in R.sectores_de(texto)]

    if pilar == 'contratacion':
        meta = ev.get('meta', {})
        hist = HISTORICO_ENTIDAD.get(R.norm(meta.get('entidad', '')))
        nivel, porque, cat = R.nivel_contrato(meta, historico_entidad=hist)
        meta['categoria'] = cat
        return [(meta['sector'], nivel, porque)]

    # La prensa NO se clasifica como señal propia. Entra por otra puerta:
    # `colgar_cobertura` la pega a la señal del acto estatal que corrobora, y
    # solo si nombra una empresa vigilada sin acto detrás dispara sola.
    return []


def _clasificar_congreso(ev):
    if ev['tipo'] == 'radicado_nuevo':
        out = []
        for k, hits in R.sectores_de(ev['titulo']):
            nivel, porque, tipologia = R.nivel_radicado(
                ev['titulo'], ev['meta'].get('comision', ''), k, hits)
            ev['meta']['tipologia'] = tipologia
            out.append((k, nivel, porque))
        return out

    # trámite: primero se limpia el ruido del registro, después se mira sector
    deltas = R.deltas_utiles(ev['meta'].get('deltas'))
    if not deltas:
        return []
    ev['meta']['deltas_utiles'] = deltas
    titulo = ev['titulo'] or F.titulo_conocido(ev['meta'].get('numero', ''),
                                               ev['meta'].get('camara', ''))
    if titulo and not ev['titulo']:
        ev['titulo'] = titulo
    if not titulo:
        return []
    nivel = R.peor_nivel([d['nivel'] for d in deltas])
    etiquetas = ' · '.join(dict.fromkeys(d['etiqueta'] for d in deltas))
    return [(k, nivel, etiquetas) for k, _h in R.sectores_de(titulo)]


def colgar_cobertura(pilares, titulares):
    """La prensa se cuelga de la señal que corrobora; no dispara sola.

    Un digest en el que la prensa dispara alertas es un lector de RSS: medido,
    la prensa metía 79 de 84 señales en salud y enterraba lo que sí importaba.
    Un titular no es un hecho nuevo del Estado — es el eco de uno. Así que:

      · Si un titular habla de algo que HOY se movió en el Congreso, en un
        regulador o en el Ejecutivo, se cuelga de esa señal como cobertura
        («esto ya lo reportaron N medios»). Eso le sube el nivel a la señal:
        un proyecto que además tiene prensa encima se mueve distinto.
      · Excepción, y es la única que dispara sola: un titular que nombra una
        EMPRESA VIGILADA y no tiene acto del Estado que le corresponda. Ahí la
        prensa va por delante del registro, y esperar al acto es llegar tarde.
      · Todo lo demás se descarta y se cuenta.

    Devuelve las cifras de lo que entró y lo que se descartó, para que el digest
    pueda decirlo en vez de que el lector suponga.
    """
    # Solo los actos NORMATIVOS anclan cobertura. La contratación queda fuera a
    # propósito: un contrato no es algo que la prensa cubra, así que cruzarlo
    # con titulares solo produce coincidencias de vocabulario administrativo.
    # Medido: un contrato de vigilancia del IDIPRON en Bogotá "corroboraba" con
    # notas de México, España e Indonesia porque todas decían «seguridad social»
    # y «protección». Además el bump medio→alto contradecía su propio «por qué»,
    # que decía que aún no había histórico para afirmar novedad.
    anclas = [e for p in ('congreso', 'regulatorio', 'ejecutivo')
              for e in pilares.get(p, [])]
    usados = set()
    for ancla in anclas:
        cobertura = []
        for t in titulares:
            if id(t) in usados:
                continue
            ok, _a, comunes = R.corrobora(t['titulo'], [ancla])
            if ok:
                usados.add(id(t))
                cobertura.append({'titulo': t['titulo'], 'medio': (t.get('meta') or {}).get('medio', ''),
                                  'url': t.get('url', ''), 'comunes': comunes})
        if cobertura:
            # el conteo de medios se hace sobre TODA la cobertura, no sobre las
            # 4 que se alcanzan a mostrar: si no, el texto dice 6 y la lista 3.
            medios = len({c['medio'] for c in cobertura if c['medio']})
            ancla['cobertura'] = cobertura[:TOPE_COBERTURA]
            ancla['cobertura_total'] = len(cobertura)
            ancla['cobertura_medios'] = medios
            if ancla['nivel'] == 'medio':
                ancla['nivel'] = 'alto'
                ancla['porque'] += f' — y ya lo reportaron {medios} medios'
            else:
                ancla['porque'] += f' · lo reportaron {medios} medios'

    # Excepción: prensa sobre empresa vigilada, con hecho accionable, y sin acto
    # del Estado detrás. Los dos filtros son necesarios: solo "nombra empresa"
    # deja pasar la noticia comercial rutinaria (26 alertas altas en un día en
    # financiero, medido); solo "hecho accionable" deja pasar la crisis genérica
    # del sector, que no es de nadie en particular.
    n_cobertura = len(usados)
    sueltos, descartados_empresa = [], 0
    for t in titulares:
        if id(t) in usados:
            continue
        emp = R.empresa_en_texto(t['titulo'])
        if not emp:
            continue
        if not R.prensa_accionable(t['titulo']):
            descartados_empresa += 1
            continue
        nivel, porque = R.nivel_titular_empresa(t['titulo'], emp)
        t['nivel'] = nivel
        t['porque'] = porque
        t['empresa'] = emp['nombre']
        usados.add(id(t))
        sueltos.append(t)

    if sueltos:
        pilares.setdefault('medios', []).extend(sueltos[:TOPE_EMPRESA_SUELTA])

    return {'total': len(titulares), 'cobertura': n_cobertura,
            'sueltos': len(sueltos[:TOPE_EMPRESA_SUELTA]),
            'sueltos_omitidos': max(0, len(sueltos) - TOPE_EMPRESA_SUELTA),
            'empresa_sin_hecho': descartados_empresa,
            'descartados': len(titulares) - len(usados)}


def _fresco(ev, hoy):
    """¿La fecha del evento cae dentro de la ventana de su pilar?"""
    f = (ev.get('fecha') or '').strip()[:10]
    if not f:
        return True                       # sin fecha no se descarta en silencio
    try:
        d = dt.date.fromisoformat(f)
    except ValueError:
        return True
    if d > hoy + dt.timedelta(days=2):
        return False                      # fecha futura = error de captura
    return (hoy - d).days <= VENTANAS.get(ev['pilar'], 60)


# ---------------------------------------------------------------------------
# ARMADO DEL DIGEST
# ---------------------------------------------------------------------------

def construir(fecha, sectores_activos, usar_api=True, baseline=False):
    hoy = dt.date.fromisoformat(fecha)
    avisos = []
    estado = cargar_estado()
    ESTADO_ETAGS.update(estado.get('etags') or {})
    HISTORICO_ENTIDAD.update(estado.get('historico_entidad') or {})
    primera_vez = not estado.get('vistos')

    crudos = recolectar(fecha, sectores_activos, usar_api=usar_api, avisos=avisos)

    vistos = estado.setdefault('vistos', {})
    nuevos, suprimidos = [], {}
    for ev in crudos:
        cubo = vistos.setdefault(ev['pilar'], {})
        if ev['id'] in cubo:
            continue
        cubo[ev['id']] = fecha
        if not _fresco(ev, hoy):
            suprimidos[ev['pilar']] = suprimidos.get(ev['pilar'], 0) + 1
            continue
        nuevos.append(ev)

    for pilar, n in sorted(suprimidos.items()):
        avisos.append({'tipo': 'backfill', 'pilar': pilar,
                       'texto': f'{n} registros nuevos para el estado pero fuera de la '
                                f'ventana de {VENTANAS.get(pilar, 60)} días '
                                f'(backfill de la fuente): no se alertan.'})

    if primera_vez or baseline:
        estado['creado'] = estado.get('creado') or dt.datetime.now().isoformat(timespec='seconds')
        estado['ultima_corrida'] = dt.datetime.now().isoformat(timespec='seconds')
        estado['corridas'] = estado.get('corridas', 0) + 1
        estado['etags'] = dict(ESTADO_ETAGS)
        return {'fecha': fecha, 'baseline': True,
                'motivo': 'primera corrida' if primera_vez else 'baseline pedido',
                'sellados': sum(len(v) for v in vistos.values()),
                'avisos': avisos, 'sectores': {}, 'total': 0}, estado

    # --- por sector --------------------------------------------------------
    por_sector = {k: {} for k in sectores_activos}
    prensa = {k: [] for k in sectores_activos}
    for ev in nuevos:
        if ev['pilar'] == 'medios':
            k = (ev.get('meta') or {}).get('sector')
            if k in prensa:
                prensa[k].append(dict(ev))
            continue
        for k, nivel, porque in clasificar(ev):
            if k not in por_sector:
                continue
            item = dict(ev)
            item.pop('_row', None)
            item['nivel'] = nivel
            item['porque'] = porque
            por_sector[k].setdefault(ev['pilar'], []).append(item)

    prensa_stats = {}
    for k in sectores_activos:
        prensa_stats[k] = colgar_cobertura(por_sector.setdefault(k, {}), prensa.get(k) or [])

    salida = {}
    for k in sectores_activos:
        pilares, omitidos, total, altos, bajos = {}, {}, 0, 0, 0
        for pilar, items in (por_sector.get(k) or {}).items():
            visibles = [e for e in items if R.orden_nivel(e['nivel']) >= 2]
            bajos += len(items) - len(visibles)
            if not visibles:
                continue
            visibles.sort(key=lambda e: (-R.orden_nivel(e['nivel']), e.get('fecha') or ''))
            total += len(visibles)
            altos += sum(1 for e in visibles if e['nivel'] == 'alto')
            if len(visibles) > TOPE_POR_PILAR:
                omitidos[pilar] = len(visibles) - TOPE_POR_PILAR
            pilares[pilar] = visibles[:TOPE_POR_PILAR]
        if total:
            s = R.sector(k) or {}
            salida[k] = {'k': k, 'nombre': s.get('nombre', k),
                         'comision': s.get('comision', ''),
                         'total': total, 'altos': altos, 'bajos': bajos,
                         'prensa': prensa_stats.get(k, {}),
                         'pilares': pilares, 'omitidos': omitidos}

    # histórico de contratación: se aprende de lo visto hoy, para que la
    # detección de "categoría nueva" tenga contra qué comparar mañana.
    for k in sectores_activos:
        for ev in (por_sector.get(k) or {}).get('contratacion', []):
            m = ev.get('meta') or {}
            ent = R.norm(m.get('entidad', ''))
            if not ent or not m.get('categoria'):
                continue
            cats = HISTORICO_ENTIDAD.setdefault(ent, [])
            if m['categoria'] not in cats:
                cats.append(m['categoria'])

    # --- salud operativa (canal interno, no va a clientes) -----------------
    operacion = None
    est_salud = F.estado_operacion()
    if est_salud:
        problemas, ctx = R.problemas_operacion(est_salud)
        operacion = {
            'estado': est_salud.get('estado'),
            'resumen': est_salud.get('resumen', ''),
            'generado': est_salud.get('generado', ''),
            'problemas': problemas, 'contexto': ctx,
            'altos': sum(1 for p in problemas if p['nivel'] == 'alto'),
        }
    else:
        avisos.append({'tipo': 'sin_estado_salud', 'pilar': 'operacion',
                       'texto': 'No hay estado.json del chequeo de salud: esta corrida '
                                'no puede distinguir «no hubo novedades» de «el '
                                'rastreo no corrió».'})

    estado['ultima_corrida'] = dt.datetime.now().isoformat(timespec='seconds')
    estado['corridas'] = estado.get('corridas', 0) + 1
    estado['etags'] = dict(ESTADO_ETAGS)
    estado['historico_entidad'] = HISTORICO_ENTIDAD
    estado = podar_estado(estado)

    digest = {'fecha': fecha, 'baseline': False,
              'generado': dt.datetime.now().isoformat(timespec='seconds'),
              'avisos': avisos, 'sectores': salida, 'operacion': operacion,
              'total': sum(s['total'] for s in salida.values()),
              'altos': sum(s['altos'] for s in salida.values()),
              'evaluados': len(nuevos)}
    return digest, estado


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def destinatarios():
    if os.path.exists(RUTA_DESTINATARIOS):
        try:
            return json.load(open(RUTA_DESTINATARIOS, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {}


def main():
    ap = argparse.ArgumentParser(description='Caudal · motor de alertas')
    ap.add_argument('--fecha', default=dt.date.today().isoformat())
    ap.add_argument('--sectores', default='',
                    help='coma-separado; por defecto todos')
    ap.add_argument('--baseline', action='store_true',
                    help='sella el estado sin enviar nada')
    ap.add_argument('--dry-run', action='store_true',
                    help='calcula y escribe el digest, no envía ni guarda estado')
    ap.add_argument('--sin-api', action='store_true',
                    help='no consulta la Lambda (sin prensa ni contratación)')
    ap.add_argument('--estado', action='store_true', help='qué sabe el motor')
    args = ap.parse_args()

    if args.estado:
        e = cargar_estado()
        print(f"estado: {RUTA_ESTADO}")
        print(f"  corridas       {e.get('corridas', 0)}")
        print(f"  creado         {e.get('creado')}")
        print(f"  última corrida {e.get('ultima_corrida')}")
        for pilar, v in sorted((e.get('vistos') or {}).items()):
            print(f"  {pilar:<14} {len(v):>7} llaves vistas")
        return 0

    activos = [s.strip() for s in args.sectores.split(',') if s.strip()] \
        or [s['k'] for s in R.sectores()]

    digest, estado = construir(args.fecha, activos, usar_api=not args.sin_api,
                               baseline=args.baseline)

    dest_dir = os.path.join(DIR_DIGESTS, args.fecha)
    os.makedirs(dest_dir, exist_ok=True)
    with open(os.path.join(dest_dir, 'digest.json'), 'w', encoding='utf-8') as fh:
        json.dump(digest, fh, ensure_ascii=False, indent=1)

    if digest.get('baseline'):
        print(f"BASELINE ({digest['motivo']}): {digest['sellados']} llaves selladas.")
        print("No se envía nada. La próxima corrida ya alerta solo lo nuevo.")
        for a in digest['avisos']:
            print(f"  aviso · {a['pilar']}: {a['texto']}")
        if not args.dry_run:
            guardar_estado(estado)
        return 0

    print(f"Digest {digest['fecha']}: {digest['total']} señales "
          f"({digest['altos']} altas) en {len(digest['sectores'])} sectores "
          f"· {digest['evaluados']} eventos nuevos evaluados")
    for a in digest['avisos']:
        print(f"  aviso · {a['pilar']}: {a['texto']}")

    op = digest.get('operacion') or {}
    hay_operacion = bool(op.get('problemas'))

    # --- SILENCIO LEGÍTIMO -------------------------------------------------
    # Un día sin nada que decir es el caso normal, no una falla. Mandar un
    # correo vacío para "demostrar que el sistema vive" es cómo un canal de
    # alertas se vuelve ruido de fondo y deja de abrirse: a la tercera semana
    # de digests vacíos, el que importa tampoco se lee. Si el rastreo se cayó,
    # eso NO es silencio — sale por el canal de operación.
    if not digest['sectores'] and not hay_operacion:
        print('\nSin novedades de nivel suficiente. No se envía correo '
              '(el silencio es una salida válida del motor).')
        if not args.dry_run:
            guardar_estado(estado)
        return 0

    conf = destinatarios()
    resultados = []
    for k, s in digest['sectores'].items():
        html = render.digest_html(digest, s)
        txt = render.digest_texto(digest, s)
        with open(os.path.join(dest_dir, f'{k}.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        with open(os.path.join(dest_dir, f'{k}.txt'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        pr = s.get('prensa') or {}
        extra = (f" · prensa: {pr.get('cobertura', 0)} como cobertura, "
                 f"{pr.get('sueltos', 0)} sueltas, {pr.get('descartados', 0)} descartadas"
                 if pr.get('total') else '')
        print(f"  · {s['nombre']:<32} {s['total']:>3} señales ({s['altos']} altas){extra}")
        if not args.dry_run:
            para = conf.get(k) or conf.get('_todos') or []
            resultados.append(sender.enviar(
                asunto=render.asunto(digest, s), html=html, texto=txt,
                para=para, etiqueta=f"{args.fecha}-{k}", dir_salida=dest_dir))

    if hay_operacion:
        html = render.operacion_html(digest)
        txt = render.operacion_texto(digest)
        with open(os.path.join(dest_dir, 'operacion.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        with open(os.path.join(dest_dir, 'operacion.txt'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        print(f"  · {'OPERACIÓN (interno)':<32} {len(op['problemas']):>3} problemas "
              f"({op['altos']} críticos)")
        if not args.dry_run:
            para = conf.get('_operacion') or conf.get('_todos') or []
            resultados.append(sender.enviar(
                asunto=render.asunto_operacion(digest), html=html, texto=txt,
                para=para, etiqueta=f"{args.fecha}-operacion", dir_salida=dest_dir))

    if args.dry_run:
        print(f"\n--dry-run: escrito en {dest_dir}, sin enviar y sin guardar estado.")
        return 0

    guardar_estado(estado)
    sender.reportar(resultados)
    print(f"\nArtefactos en {dest_dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
