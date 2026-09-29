"""revisar.py — la revisión mensual de contendientes de Candidato 360 (fase 5).

Corre el día 1 de cada mes en GitHub Actions (candidato-360-contendientes.yml).
Para cada TERRITORIO con candidaturas activas (inventario del worker; no las
personas, que el worker no expone), lee la prensa del último mes y deja
PROPUESTAS en el worker. Una persona las aprueba o descarta en
admin-c360-contendientes.html; lo que no necesita revisión se sella solo.

Tres clases de propuesta (PLAN §8):
  · aspirante  · un nombre propio que aparece en titulares con vocabulario de
                 aspiración y el territorio, en ≥ 2 medios distintos, y que no
                 es ya un rival conocido. SIEMPRE lo decide una persona.
  · aval       · un titular que nombra a un rival conocido con vocabulario de
                 cambio de partido. Lo decide una persona (y escribe el
                 partido nuevo: del titular no se saca con confianza).
  · titulares  · titulares nuevos que nombran a un rival conocido. Se aprueban
                 solos: son literales y solo se cuentan.

Reglas:
  · Nada de prensa entra a la lista sin revisión humana.
  · Nada se resume con un modelo: se guardan titulares literales con su enlace.
  · Un territorio sin nada se sella igual: «revisado, sin cambios» es un dato.
  · Si la prensa no responde para un territorio, NO se sella: sellar diría
    «sin cambios» sobre algo que no se leyó.

Uso:
  CAUDAL_ALERTAS_TOKEN=… python3 revisar.py              # corrida real
  python3 revisar.py --seco                              # lee todo, no escribe
  python3 revisar.py --inventario inv.json --seco        # sin worker
  python3 revisar.py --prueba                            # chequeos sin red
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('motor_briefing', AQUI.parent / 'briefing' / 'motor.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)          # el motor del briefing: http, token, norm y la Lambda de prensa

DIAS = 31
MIN_MEDIOS_ASPIRANTE = 2
MAX_RIVALES_CONSULTA = 20            # rivales conocidos que se buscan por nombre en cada territorio
MAX_TITULARES = 5

ASPIRA = re.compile(r'\b(ASPIRA|ASPIRANTE|ASPIRANTES|PRECANDIDAT\w*|SE LANZA|LANZA SU|LANZO SU|LANZAMIENTO|CANDIDATURA|CANDIDATA A|CANDIDATO A|'
                    r'SUENA|SUENAN|SONAJERO|INSCRIBE|INSCRIBIO|AVAL|AVALADO|AVALADA|QUIERE SER)\b')
CAMBIO_AVAL = re.compile(r'\b(ADHIERE|ADHESION|RENUNCIA AL PARTIDO|RENUNCIO AL PARTIDO|SE PASA A|SE PASO A|SE UNE A|SE UNIO A|'
                         r'CAMBIA DE PARTIDO|CAMBIO DE PARTIDO|DEJA EL PARTIDO|NUEVO AVAL|RECIBE EL AVAL|RECIBIO EL AVAL|OTORGA AVAL|OTORGO AVAL)\b')
CONECTORES = {'de', 'del', 'la', 'las', 'los', 'y'}
# El titular tiene que nombrar el cargo en disputa: medido, al buscar la
# Gobernación del Valle salía una candidatura a la Alcaldía de Cali.
CARGO = {'concejo': re.compile(r'\b(CONCEJO|CONCEJAL\w*)\b'), 'alcaldia': re.compile(r'\b(ALCALDIA|ALCALDE|ALCALDESA)\b'),
         'gobernacion': re.compile(r'\b(GOBERNACION|GOBERNADOR\w*)\b'), 'asamblea': re.compile(r'\b(ASAMBLEA|DIPUTAD\w*)\b'),
         'jal': re.compile(r'\b(JAL|EDIL\w*|JUNTA ADMINISTRADORA)\b')}
ROLES = {'CONCEJAL', 'CONCEJALA', 'EXCONCEJAL', 'EXCONCEJALA', 'EDIL', 'EDILESA', 'ALCALDE', 'ALCALDESA', 'EXALCALDE', 'EXALCALDESA', 'GOBERNADOR',
         'GOBERNADORA', 'EXGOBERNADOR', 'EXGOBERNADORA', 'DIPUTADO', 'DIPUTADA', 'SENADOR', 'SENADORA', 'EXSENADOR', 'EXSENADORA', 'REPRESENTANTE',
         'PRECANDIDATO', 'PRECANDIDATA', 'CANDIDATO', 'CANDIDATA', 'PRESIDENTE', 'PRESIDENTA', 'MINISTRO', 'MINISTRA', 'EXMINISTRO', 'EXMINISTRA',
         'SECRETARIO', 'SECRETARIA', 'LIDER', 'LIDERESA', 'EL', 'LA', 'LOS', 'LAS', 'DON', 'DOÑA', 'DONA', 'DR', 'DRA'}
NO_PERSONA = {'CONCEJO', 'ALCALDIA', 'GOBERNACION', 'ASAMBLEA', 'JAL', 'JUNTA', 'PARTIDO', 'PACTO', 'HISTORICO', 'CENTRO', 'DEMOCRATICO',
              'LIBERAL', 'CONSERVADOR', 'CAMBIO', 'RADICAL', 'VERDE', 'ALIANZA', 'COLOMBIA', 'COLOMBIANO', 'REGISTRADURIA', 'CNE', 'CONGRESO',
              'SENADO', 'CAMARA', 'GOBIERNO', 'NACIONAL', 'DISTRITO', 'MUNICIPIO', 'DEPARTAMENTO', 'LOCALIDAD', 'COMUNA', 'MOVIMIENTO',
              'COALICION', 'NUEVO', 'LIBERALISMO', 'FUERZA', 'CIUDADANA', 'DIGNIDAD', 'COMPROMISO', 'SALVACION', 'CREEMOS', 'MIRA',
              'POLICIA', 'FISCALIA', 'PROCURADURIA', 'CONTRALORIA', 'PERSONERIA', 'EPS', 'ESE', 'SAS', 'ELECCIONES', 'ELECCION', 'CAMPANA',
              'PLAN', 'DESARROLLO', 'PRESUPUESTO', 'METRO', 'TRANSMILENIO', 'UNIVERSIDAD', 'CONSEJO', 'ESTADO', 'CORTE', 'TRIBUNAL',
              'GRUPO', 'AVAL', 'BANCO', 'EMPRESA', 'FUNDACION', 'SECTOR'}


ANTES_OK = {'CONCEJAL', 'CONCEJALA', 'EXCONCEJAL', 'EXCONCEJALA', 'EDIL', 'EDILESA', 'ALCALDE', 'ALCALDESA', 'EXALCALDE', 'EXALCALDESA', 'GOBERNADOR',
            'GOBERNADORA', 'DIPUTADO', 'DIPUTADA', 'SENADOR', 'SENADORA', 'REPRESENTANTE', 'CANDIDATO', 'CANDIDATA', 'PRECANDIDATO', 'PRECANDIDATA',
            'EXSENADOR', 'EXSENADORA', 'LIDER', 'LIDERESA', 'VIDEO', 'HOY', 'EXCLUSIVA', 'ATENCION', 'OPINION', 'ENTREVISTA', 'POLEMICA', 'ASI'}


def _palabras(titulo):
    out = []
    for w in str(titulo or '').split():
        if not re.search(r'[A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9]', w):
            if out:
                out[-1]['corte'] = True
            continue
        limpio = re.sub(r'^[«"“\'‘(¿¡]+', '', w)
        out.append({'n': M.norm(limpio), 'mayus': bool(re.match(r'[A-ZÁÉÍÓÚÑÜ]', limpio)),
                    'corte': bool(re.search(r'[,.:;!?)»"”’|]$', w)), 'antes_corte': limpio != w})
    return out


def mencion(titulo, nombre):
    """El mismo criterio de mencionaPersona en candidato-360-contendientes.js:
    exacta con 3 componentes; parcial (nombre + un apellido) solo si no viene
    pegada a otro nombre propio. Medido: «Carlos Galán» casaba dentro de «Luis
    Carlos Galán Sarmiento» y los titulares de su padre salían como suyos."""
    tk = [t for t in M.norm(nombre).split() if len(t) >= 3 and t not in {'DEL', 'LAS', 'LOS', 'SAN', 'SANTA'}]
    if len(tk) < 2:
        return False
    s_, P = set(tk), _palabras(titulo)
    n = sum(1 for t in tk if any(p['n'] == t for p in P))
    if n < 2:
        return False
    if n >= min(3, len(tk)):
        return True
    i = 0
    while i < len(P):
        if P[i]['n'] not in s_:
            i += 1
            continue
        j = i
        while j + 1 < len(P) and not P[j]['corte'] and P[j + 1]['n'] in s_:
            j += 1
        if j > i:
            a = P[i - 1] if i > 0 else None
            d = P[j + 1] if j + 1 < len(P) else None
            antes_mal = a and not a['corte'] and not P[i]['antes_corte'] and a['mayus'] and a['n'] not in ANTES_OK
            despues_mal = d and not P[j]['corte'] and not d['antes_corte'] and d['mayus'] and d['n'] not in s_
            if not antes_mal and not despues_mal:
                return True
        i = j + 1
    return False


def consultas_persona(nombre):
    w = str(nombre or '').strip().split()
    q = [' '.join(w)]
    if len(w) >= 4:            # con tres palabras la forma corta pueden ser dos nombres de pila
        q.append(f'{w[0]} {w[2]}')
    return list(dict.fromkeys(f'"{M.oracion(x)}"' for x in q if len(x.split()) >= 2))


def nombres_en(titulo):
    """Nombres propios de 2 a 5 palabras en Tipo Título. Aproximación: por
    eso todo lo que sale de aquí pasa por una persona antes de publicarse."""
    t = re.sub(r'\s+[|–—-]\s+[^|–—-]{2,40}$', '', str(titulo or ''))
    t = re.sub(r'[«»"“”‘’\'()]', ' ', t)
    t = re.sub(r'[,.:;¿?¡!|–—]|\s-\s', ' · ', t)
    salida, actual = [], []

    def cerrar():
        while actual and actual[-1].lower() in CONECTORES:
            actual.pop()
        while actual and (M.norm(actual[0]) in ROLES or actual[0].lower() in CONECTORES):
            actual.pop(0)
        fuertes = [w for w in actual if w.lower() not in CONECTORES]
        if 2 <= len(fuertes) <= 5:
            salida.append(' '.join(actual))
        actual.clear()

    for w in t.split():
        if w == '·':
            cerrar()
            continue
        limpio = w.strip()
        if limpio[:1].isupper() and not (len(limpio) > 3 and limpio.isupper()) and re.fullmatch(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", limpio):
            actual.append(limpio)
        elif actual and limpio.lower() in CONECTORES:
            actual.append(limpio)
        else:
            cerrar()
    cerrar()
    return [n for n in salida if es_persona(n)]


def es_persona(n):
    tk = [x for x in M.norm(n).split() if x.lower() not in CONECTORES]
    return len(tk) >= 2 and all(len(x) >= 2 for x in tk) and not any(x in NO_PERSONA or x in ROLES for x in tk)


def lugar_de(item):
    """Etiqueta, términos locales y consultas de aspiración de un territorio."""
    t, tr = item['t'], item.get('territorio') or {}
    corp = t.split(':')[0]
    dep = tr.get('departamentoNombre') or ''
    mun = re.sub(r',?\s*D\.?\s*C\.?$', '', tr.get('municipio') or '', flags=re.I).strip()
    loc = tr.get('localidad') or ''
    es_bogota = 'BOGOTA' in M.norm(mun) or 'BOGOTA' in M.norm(dep)
    base = 'Bogotá' if es_bogota else M.oracion(mun)
    if corp in ('asamblea', 'gobernacion'):
        lugar = M.oracion(dep)
        locales = M.toks(dep, 4)
        consultas = [f'"Gobernación de {lugar}" 2027', f'"{lugar}" precandidato gobernación'] if corp == 'gobernacion' else \
                    [f'"Asamblea de {lugar}" 2027', f'"{lugar}" aspira Asamblea']
    else:
        lugar = base
        locales = ['BOGOTA'] if es_bogota else M.toks(mun, 4)
        if corp == 'alcaldia':
            consultas = [f'"Alcaldía de {base}" 2027', f'"{base}" precandidato alcaldía']
        elif corp == 'concejo':
            consultas = [f'"Concejo de {base}" 2027', f'"{base}" aspira al Concejo']
        else:
            lugar = f'{M.oracion(loc)} · {base}' if loc else base
            locales = (M.toks(loc, 4) or []) + locales
            consultas = [f'"{M.oracion(loc)}" edil 2027', f'"{M.oracion(loc)}" JAL candidato'] if loc else [f'"{base}" JAL 2027']
    return {'corp': corp, 'lugar': lugar, 'locales': [x for x in locales if x], 'consultas': consultas}


def buscar(query, dias=DIAS):
    d = M.api({'action': 'medios', 'query': query, 'dias': dias}, timeout=60)
    if not d or d.get('error'):
        return None
    return [{'titulo': r.get('titulo') or '', 'medio': r.get('medio') or '', 'url': r.get('url') or '', 'fecha': r.get('fecha') or ''}
            for r in d.get('resultados') or [] if r.get('titulo')]


def proponer(item, leer=buscar, desde=None):
    """Las propuestas de UN territorio. Devuelve (propuestas, fallos, leidas)."""
    L = lugar_de(item)
    conocidos = item.get('personas') or []
    fallos = leidas = 0
    por_consulta = {}
    tareas = [('territorio', q, None) for q in L['consultas']]
    for p in conocidos[:MAX_RIVALES_CONSULTA]:
        tareas += [('rival', q, p) for q in consultas_persona(p['nombre'])]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futuros = {ex.submit(leer, q): (tipo, q, p) for tipo, q, p in tareas}
        for f in cf.as_completed(futuros):
            tipo, q, p = futuros[f]
            r = f.result()
            if r is None:
                fallos += 1
                continue
            leidas += 1
            por_consulta[(tipo, q, p['k'] if p else '')] = (p, r)

    def nuevo(it):
        return not desde or str(it.get('fecha') or '')[:10] > desde

    propuestas = []
    # 1 · Titulares y cambios de aval de los rivales conocidos.
    for p in conocidos[:MAX_RIVALES_CONSULTA]:
        vistos, suyos, aval = set(), [], []
        for (tipo, q, k), (pp, r) in por_consulta.items():
            if tipo != 'rival' or k != p['k']:
                continue
            for it in r:
                clave = M.norm(it['titulo'])[:90]
                if clave in vistos or not nuevo(it) or not mencion(it['titulo'], p['nombre']):
                    continue
                vistos.add(clave)
                suyos.append(it)
                if CAMBIO_AVAL.search(M.norm(it['titulo'])):
                    aval.append(it)
        suyos.sort(key=lambda x: str(x['fecha']), reverse=True)
        if suyos:
            propuestas.append({'tipo': 'titulares', 'nombre': p['nombre'], 'k': p['k'], 'titulares': suyos[:MAX_TITULARES],
                               'medios': len({M.norm(x['medio']) for x in suyos if x['medio']})})
        if aval:
            propuestas.append({'tipo': 'aval', 'nombre': p['nombre'], 'k': p['k'], 'aval': '', 'titulares': aval[:MAX_TITULARES],
                               'medios': len({M.norm(x['medio']) for x in aval if x['medio']})})
    # 2 · Aspirantes nuevos: nombre propio + vocabulario de aspiración + el territorio.
    candidatos = {}
    for (tipo, q, k), (pp, r) in por_consulta.items():
        if tipo != 'territorio':
            continue
        for it in r:
            n = M.norm(it['titulo'])
            if not nuevo(it) or not ASPIRA.search(n) or not CARGO[L['corp']].search(n) or (L['locales'] and not any(f' {x} ' in f' {n} ' for x in L['locales'])):
                continue
            for nombre in nombres_en(it['titulo']):
                if any(mencion(nombre, c['nombre']) for c in conocidos):
                    continue            # ya es rival: sus titulares van por la vía 1
                c = candidatos.setdefault(M.norm(nombre), {'nombre': nombre, 'titulares': [], 'medios': set(), 'vistos': set()})
                clave = n[:90]
                if clave in c['vistos']:
                    continue
                c['vistos'].add(clave)
                c['titulares'].append(it)
                if it['medio']:
                    c['medios'].add(M.norm(it['medio']))
    for c in candidatos.values():
        if len(c['medios']) >= MIN_MEDIOS_ASPIRANTE:
            c['titulares'].sort(key=lambda x: str(x['fecha']), reverse=True)
            propuestas.append({'tipo': 'aspirante', 'nombre': c['nombre'], 'titulares': c['titulares'][:MAX_TITULARES], 'medios': len(c['medios'])})
    return propuestas, fallos, leidas


def mes_actual():
    return dt.datetime.now(M.BOGOTA).strftime('%Y-%m')


def correr(args):
    if args.inventario:
        inv = json.loads(Path(args.inventario).read_text())
    else:
        inv = M.worker('/c360/contendientes/inventario')
    territorios = inv.get('territorios') or []
    mes = args.mes or mes_actual()
    print(f'Revisión {mes} · {len(territorios)} territorio(s){" · en seco" if args.seco else ""}')
    resumen = {'sellados': 0, 'pendientes': 0, 'sin_prensa': 0}
    for item in territorios:
        if args.solo and item['t'] != args.solo:
            continue
        # Solo lo publicado desde la última revisión sellada (su mes), o el último mes.
        desde = (item.get('ultima') + '-01') if item.get('ultima') and item.get('ultima') < mes else None
        props, fallos, leidas = proponer(item, desde=desde)
        tipos = {}
        for p in props:
            tipos[p['tipo']] = tipos.get(p['tipo'], 0) + 1
        print(f"  {item['t']}: {leidas} consultas leídas, {fallos} sin respuesta · {tipos or 'sin propuestas'}")
        for p in props:
            if p['tipo'] != 'titulares':
                print(f"     · {p['tipo']}: {p['nombre']} ({p['medios']} medios) — {p['titulares'][0]['titulo'][:90] if p['titulares'] else ''}")
        if args.seco:
            continue
        if leidas == 0:
            resumen['sin_prensa'] += 1
            print('     ! la prensa no respondió: no se sella (diría «sin cambios» sobre algo que no se leyó)')
            continue
        if props:
            r = M.worker('/c360/contendientes/propuesta', {'t': item['t'], 'mes': mes, 'propuestas': props})
            if not r.get('ok'):
                print(f"     ! no se guardaron las propuestas: {r.get('error')}")
                continue
        s = M.worker('/c360/contendientes/sellar', {'t': item['t'], 'mes': mes})
        if s.get('sellado'):
            resumen['sellados'] += 1
        else:
            resumen['pendientes'] += 1
            print(f"     → {s.get('pendientes', '?')} esperan revisión en admin-c360-contendientes.html")
    print(f"Listo: {resumen['sellados']} sellados · {resumen['pendientes']} esperan revisión · {resumen['sin_prensa']} sin prensa")
    return 0


def prueba():
    fallas = 0

    def ok(c, m):
        nonlocal fallas
        print(('✓ ' if c else '✗ ') + m)
        fallas += 0 if c else 1

    ok(nombres_en('Marta Lucía Rincón aspira al Concejo de Bogotá - El Tiempo') == ['Marta Lucía Rincón'], 'el nombre sale sin el verbo, sin la institución y sin el medio')
    ok(nombres_en('Concejal Juan Carlos Pérez se lanza a la Alcaldía') == ['Juan Carlos Pérez'], 'el cargo delante no es parte del nombre')
    ok(nombres_en('Partido Liberal da aval en Tunja') == [], 'un partido no es una persona')
    ok(nombres_en('Precandidata Ana de la Hoz recibe aval') == ['Ana de la Hoz'], 'conectores dentro del nombre')
    ok(nombres_en('Presidenta de Grupo Aval advierte golpe al sector financiero') == [], 'medido: «de Grupo Aval» no es una persona')
    item_v = {'t': 'gobernacion:31', 'territorio': {'departamentoNombre': 'Valle del Cauca'}, 'personas': []}
    cali = [{'titulo': 'Clara Luz Roldán confirma candidatura a la Alcaldía de Cali, Valle', 'medio': m, 'url': 'u', 'fecha': '2026-10-01'} for m in ('A', 'B')]
    ok(proponer(item_v, leer=lambda q: cali)[0] == [], 'medido: una candidatura a la Alcaldía de Cali no es aspirante a la Gobernación del Valle')
    ok(mencion('Ana María Pérez propone nuevo metro', 'ANA MARIA PEREZ ROJAS') and not mencion('Anamaría Perezoso abre tienda', 'ANA MARIA PEREZ ROJAS'),
       'la mención va por palabras enteras')
    ok(not mencion('Juicio por el magnicidio de Luis Carlos Galán se reanudó', 'CARLOS FERNANDO GALAN PACHON')
       and mencion('Alcalde Carlos Galán anuncia metro', 'CARLOS FERNANDO GALAN PACHON'), 'medido: el padre no cuenta; el alcalde con su cargo sí')
    ok(consultas_persona('NATALIA SOPHIA PARRA ROJAS') == ['"Natalia Sophia Parra Rojas"', '"Natalia Parra"'], 'nombre completo y forma corta')
    item = {'t': 'concejo:16-001', 'territorio': {'municipio': 'BOGOTÁ D.C.', 'departamentoNombre': 'Bogotá D.C.'},
            'personas': [{'k': 'ANA MARIA PEREZ ROJAS', 'nombre': 'ANA MARIA PEREZ ROJAS', 'partido': 'X'}]}
    falsa = {
        '"Concejo de Bogotá" 2027': [
            {'titulo': 'Marta Lucía Rincón aspira al Concejo de Bogotá', 'medio': 'El Tiempo', 'url': 'u1', 'fecha': '2026-10-05'},
            {'titulo': 'Luis Mora, el único que suena en Medellín', 'medio': 'Semana', 'url': 'u2', 'fecha': '2026-10-06'}],
        '"Bogotá" aspira al Concejo': [
            {'titulo': 'Rincón: Marta Lucía Rincón se lanza al Concejo de Bogotá', 'medio': 'Semana', 'url': 'u3', 'fecha': '2026-10-07'},
            {'titulo': 'Ana María Pérez aspira a repetir en el Concejo de Bogotá', 'medio': 'Semana', 'url': 'u4', 'fecha': '2026-10-08'}],
        '"Ana Maria Perez Rojas"': [],
        '"Ana Perez"': [{'titulo': 'Ana María Pérez se une a Nuevo Liberalismo', 'medio': 'El Espectador', 'url': 'u5', 'fecha': '2026-10-09'}],
    }
    props, fallos, leidas = proponer(item, leer=lambda q: falsa.get(q, []), desde='2026-09-30')
    tipos = sorted(p['tipo'] for p in props)
    ok(tipos == ['aspirante', 'aval', 'titulares'], f'territorio: una aspirante nueva, un cambio de aval y titulares del conocido ({tipos})')
    asp = next(p for p in props if p['tipo'] == 'aspirante')
    ok(asp['nombre'] == 'Marta Lucía Rincón' and asp['medios'] == 2, 'la aspirante está en dos medios distintos')
    ok(not any(p['nombre'].startswith('Luis') for p in props), 'un nombre en un solo medio y en otro territorio no entra')
    ok(not any(p['tipo'] == 'aspirante' and 'Pérez' in p['nombre'] for p in props), 'el rival conocido no se propone como aspirante')
    props2, _, _ = proponer(item, leer=lambda q: falsa.get(q, []), desde='2026-10-31')
    ok(props2 == [], 'lo anterior a la última revisión no vuelve a proponerse')
    print(f'\n{fallas} falla(s)' if fallas else '\nTodo en orden')
    return 1 if fallas else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--seco', action='store_true', help='lee todo y no escribe en el worker')
    ap.add_argument('--inventario', help='JSON con la forma de /c360/contendientes/inventario')
    ap.add_argument('--solo', help='un solo territorio (p. ej. concejo:16-001)')
    ap.add_argument('--mes', help='AAAA-MM (por defecto, el mes corriente en Bogotá)')
    ap.add_argument('--prueba', action='store_true', help='chequeos sin red')
    ap.add_argument('--worker', help='otra base del worker (p. ej. un wrangler dev)')
    args = ap.parse_args()
    if args.prueba:
        sys.exit(prueba())
    if args.worker:
        M.WORKER = args.worker
    sys.exit(correr(args))


if __name__ == '__main__':
    main()
