#!/usr/bin/env python3
"""Módulo 03 · Clima social — laboratorio sobre el banco de titulares propio.

Lee   Bases de datos/nuevo-liberalismo/medios/{raw,enriched}/**.jsonl
Emite Propuestas/nuevo-liberalismo/datos/clima.json   (la página no llama a S3 ni a CDN)

  python3.14 tools/nuevo-liberalismo/build_clima.py            # todo
  python3.14 tools/nuevo-liberalismo/build_clima.py --revisar  # imprime episodios para revisión a mano
  python3.14 tools/nuevo-liberalismo/build_clima.py --sin-gnews

Decisiones (todas van declaradas en la página):
- Unidad = titular ÚNICO (id). El RSS no es incremental: la misma nota sale en muchas corridas.
- Fecha = fecha_pub en hora de Bogotá. Periodo de análisis: 4-may-2026 (primera semana con
  los 17 medios) al último domingo completo.
- Series en PARTICIPACIÓN (% de los titulares de la semana), no en conteos: el volumen por
  medio no es parejo en el tiempo.
- «Asunto público» = todo tema menos `otros` y `cultura_deportes`; esos dos salen del
  denominador de la agenda (son 35 % del banco) y se informa su tamaño aparte.
- Episodio = estallido de un término del titular contra su propia línea base (ver EPISODIOS).
"""
import json, glob, os, re, sys, html, math, collections, datetime as dt, subprocess, urllib.parse
import xml.etree.ElementTree as ET

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
B = os.path.join(RAIZ, 'Bases de datos', 'nuevo-liberalismo', 'medios')
SAL = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos', 'clima.json')
STOP_F = os.path.join(RAIZ, 'tools', 'agenda-medios-aggregator', 'stopwords-es.txt')
TZ = dt.timezone(dt.timedelta(hours=-5))
INICIO = dt.date(2026, 5, 4)           # lunes; primera semana con todos los medios

MEDIOS = {
    'bluradio': 'Blu Radio', 'elcolombiano': 'El Colombiano', 'minuto30': 'Minuto30',
    'noscogiolanoche': 'Nos Cogió la Noche', 'mioriente': 'MiOriente', 'las2orillas': 'Las2orillas',
    'telemedellin': 'Telemedellín', 'semana': 'Semana', 'qhubomedellin': "Q'hubo Medellín",
    'vivirenelpoblado': 'Vivir en El Poblado', 'eltiempo-medellin': 'El Tiempo · Medellín',
    'pulzo': 'Pulzo', 'sinergia': 'Sinergia Informativa', 'centropolis': 'Centrópolis',
    'hacemosmemoria': 'Hacemos Memoria', 'periferia': 'Periferia', 'delaurbe': 'De la Urbe'}
NACIONALES = {'bluradio', 'semana', 'las2orillas', 'pulzo'}

# Color FIJO por tema. Los 8 mayores usan la paleta categórica validada contra el fondo oscuro
# (validate_palette.js --mode dark --surface #1f2124, 10-nov-2026: pasa las cinco pruebas de color con los
# vecinos del orden de apilado — seguridad abajo, política arriba — y política↔«resto» gris ΔE 15,8).
# Antes se repartían en otro orden y quedaban vecinos casi iguales (movilidad y economía, dos naranjas).
# El rojo vivo queda para el Nuevo Liberalismo: seguridad deja el coral y pasa a azul.
# Los menores van en gris y se agrupan como «resto» en el gráfico apilado.
TEMAS = {
    'seguridad': ('Seguridad', '#3987e5'), 'justicia': ('Justicia', '#d95926'),
    'internacional': ('Internacional', '#199e70'), 'salud': ('Salud', '#c98500'),
    'empleo_economia': ('Economía y empleo', '#d55181'), 'ambiente': ('Ambiente', '#008300'),
    'movilidad': ('Movilidad', '#e66767'), 'politica': ('Política', '#9085e9'),
    'social_protesta': ('Protesta social', '#9aa0ad'), 'infraestructura': ('Infraestructura', '#9aa0ad'),
    'drogas_narcotrafico': ('Drogas y narcotráfico', '#9aa0ad'), 'educacion': ('Educación', '#9aa0ad'),
    'corrupcion': ('Corrupción', '#9aa0ad'), 'vivienda_pot': ('Vivienda y POT', '#9aa0ad'),
    'cultura_deportes': ('Cultura y deportes', '#5c6272'), 'otros': ('Otros (sucesos, servicios, varios)', '#5c6272')}
ALIAS_TEMA = {'economia': 'empleo_economia', 'droga_narcotrafico': 'drogas_narcotrafico'}
FUERA = {'otros', 'cultura_deportes'}          # no son «asunto público»
SERIES8 = ['seguridad', 'justicia', 'internacional', 'salud', 'empleo_economia', 'ambiente', 'movilidad', 'politica']   # orden de apilado


def norm(s):
    s = s.lower()
    s = s.translate(str.maketrans('áéíóúüñ', 'aeiouun'))
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def cargar():
    raw = {}
    for f in sorted(glob.glob(B + '/raw/**/*.jsonl', recursive=True)):
        for ln in open(f, encoding='utf-8'):
            ln = ln.strip()
            if not ln: continue
            try: r = json.loads(ln)
            except Exception: continue
            raw.setdefault(r['id'], r)
    enr = {}
    for f in glob.glob(B + '/enriched/**/*.jsonl', recursive=True):
        for ln in open(f, encoding='utf-8'):
            ln = ln.strip()
            if not ln: continue
            try: r = json.loads(ln)
            except Exception: continue
            enr[r['id']] = r
    D = []
    for i, r in raw.items():
        try:
            cap = dt.datetime.fromisoformat(r['fecha_capturada']).astimezone(TZ)
            d = dt.datetime.fromisoformat(r.get('fecha_pub') or r['fecha_capturada']).astimezone(TZ)
        except Exception:
            continue
        if d > cap + dt.timedelta(days=1): d = cap      # fecha_pub en el futuro: manda la captura
        e = enr.get(i, {})
        res = re.sub(r'<[^>]+>', ' ', html.unescape(r.get('resumen') or ''))
        res = re.sub(r'https?://\S+|\S+\.(?:webp|jpe?g|png)\b', ' ', res)
        res = re.sub(r'La entrada .{0,200} aparece primero en .*$', '', res).strip()
        tema = e.get('tema'); tema = ALIAS_TEMA.get(tema, tema)
        if tema not in TEMAS: tema = None
        D.append({'id': i, 'm': r['medio'], 't': html.unescape(r.get('titulo') or '').strip(), 'r': res[:500],
                  'd': d.date(), 'tema': tema, 's': e.get('sentimiento'), 'a': e.get('actores') or [],
                  'u': r.get('url_canonica') or r.get('url')})
    return D, len(raw), len(enr)


def lunes(d): return d - dt.timedelta(days=d.weekday())
def iso(d): return d.isoformat()


# ───────────────────────── AGENDA ─────────────────────────
def agenda(D, fin):
    semanas = []
    d = INICIO
    while d + dt.timedelta(days=6) <= fin:
        semanas.append(d); d += dt.timedelta(days=7)
    idx = {s: i for i, s in enumerate(semanas)}
    tot = [0] * len(semanas); pub = [0] * len(semanas); sincl = [0] * len(semanas)
    por = {t: [0] * len(semanas) for t in TEMAS}
    neg = {t: [0] * len(semanas) for t in TEMAS}
    med = collections.defaultdict(lambda: [0] * len(semanas))
    for x in D:
        i = idx.get(lunes(x['d']))
        if i is None: continue
        tot[i] += 1; med[x['m']][i] += 1
        if not x['tema']: sincl[i] += 1; continue
        por[x['tema']][i] += 1
        if x['s'] == 'negativo': neg[x['tema']][i] += 1
        if x['tema'] not in FUERA: pub[i] += 1
    part = {t: [round(por[t][i] / pub[i], 4) if pub[i] else 0 for i in range(len(semanas))]
            for t in TEMAS if t not in FUERA}
    n = len(semanas); k = n // 3
    cambio = []
    for t in part:
        a = sum(por[t][:k]) / max(1, sum(pub[:k])); b = sum(por[t][-k:]) / max(1, sum(pub[-k:]))
        u4 = sum(por[t][-4:]) / max(1, sum(pub[-4:]))
        h3 = sum(por[t][-17:-13]) / max(1, sum(pub[-17:-13]))    # mismas 4 semanas, 13 semanas antes
        lider = sum(1 for i in range(n) if all(por[t][i] >= por[o][i] for o in part))
        cambio.append({'tema': t, 'ini': round(a, 4), 'fin': round(b, 4), 'dif': round(b - a, 4),
                       'ult4': round(u4, 4), 'hace3m': round(h3, 4), 'n': sum(por[t]),
                       'n_ini': sum(por[t][:k]), 'n_fin': sum(por[t][-k:]), 'sem_lider': lider,
                       'max': max(part[t]), 'min': min(part[t]),
                       'cv': round(_cv(part[t]), 3)})
    cambio.sort(key=lambda r: -r['fin'])
    return {'semanas': [iso(s) for s in semanas], 'total': tot, 'publico': pub, 'sin_clasificar': sincl,
            'fuera_part': {t: [round(por[t][i] / tot[i], 4) if tot[i] else 0 for i in range(len(semanas))] for t in FUERA},
            'conteo': por, 'part': part, 'cambio': cambio, 'tercio': k,
            'medios_sem': {m: v for m, v in med.items()}}


def _cv(v):
    m = sum(v) / len(v)
    if not m: return 0
    return (sum((x - m) ** 2 for x in v) / len(v)) ** .5 / m


# ───────────────────────── EPISODIOS ─────────────────────────
"""Método (declarado en la página):
1. Términos = palabras (≥4 letras) y pares de palabras contiguas del TITULAR, sin palabras vacías.
2. Serie diaria del término = titulares únicos que lo traen. Línea base = promedio de la mitad
   más baja de los días (aguanta una crisis que dure hasta medio periodo sin volverla «normal»).
   Se descartan los términos «crónicos» (línea base > 0,7 al día): siempre están (Petro, Medellín,
   policía) y no son una historia.
3. Estallido = día con ≥ PICO_MIN titulares y ≥ 4 veces (línea base + 0,5).
4. El episodio corre desde el pico hacia atrás y adelante mientras el promedio móvil de 3 días
   siga sobre el umbral = el mayor entre UMBRAL_MIN titulares al día y el doble de la línea base.
5. Términos cuyo episodio se solapa en fechas y comparte la mitad de sus titulares son la misma
   historia. La serie de la historia es la unión de sus titulares.
6. Vida media = días desde el pico hasta que el promedio móvil de 3 días cae a la mitad del pico.
"""
PICO_MIN = 6
UMBRAL_MIN = 2.0
# Pares de palabras que estallan pero no son UNA historia (rótulos de época o de lugar).
ANCLA_NO = {'gobierno petro', 'gobierno espriella', 'presidente espriella', 'espriella presidente',
            'valle aburra', 'pico placa', 'gobierno nacional', 'presidente petro', 'area metropolitana'}
# Fusión revisada a mano (término principal, día pico ±2): sinónimos y tandas del mismo hecho
# que el solape de titulares no une solo.
FUSION = [
    [('terremoto', '2026-08-11'), ('sismo', '2026-08-10')],
    [('terremotos', '2026-06-25'), ('terremoto venezuela', '2026-06-25')],
    [('posesion presidencial', '2026-08-06'), ('posesion abelardo', '2026-08-07'), ('posesion espriella', '2026-08-06')],
    [('elecciones presidenciales', '2026-06-21'), ('jornada electoral', '2026-06-21'), ('preconteo', '2026-06-21')],
    [('elecciones presidenciales', '2026-05-31'), ('jornada electoral', '2026-05-31')],
]
# Nombre legible de las historias mayores, puesto a mano tras leer sus titulares.
ROTULOS = {
    ('terremoto', '2026-08-11'): 'Terremoto del 10 de agosto (magnitud 7,4)',
    ('cepeda', '2026-06-01'): 'Campaña presidencial: Cepeda, encuestas y adhesiones',
    ('vuelta', '2026-05-31'): 'La segunda vuelta presidencial',
    ('incendios', '2026-08-25'): 'Incendios forestales (Tolima y otras regiones)',
    ('terremotos', '2026-06-25'): 'Terremotos de Venezuela',
    ('yulixa', '2026-05-19'): 'Caso Yulixa Toloza (cirugía en centro ilegal)',
    ('paloma', '2026-05-31'): 'Paloma Valencia y Fajardo antes de la primera vuelta',
    ('electo', '2026-06-25'): 'La transición: el presidente electo',
    ('halloween', '2026-10-30'): 'Operativos y restricciones de Halloween',
    ('empalme', '2026-07-07'): 'El empalme entre gobiernos (y su suspensión)',
    ('mateo perez', '2026-05-08'): 'Asesinato del periodista Mateo Pérez en Briceño',
    ('elecciones presidenciales', '2026-05-31'): 'Primera vuelta: jornada y resultados',
    ('elecciones presidenciales', '2026-06-21'): 'Segunda vuelta: jornada, preconteo y resultados',
    ('alcocer', '2026-10-13'): 'Denuncias de Eva Ferrer contra Verónica Alcocer',
    ('hantavirus', '2026-05-07'): 'Brote de hantavirus en un crucero',
    ('vargas lleras', '2026-05-08'): 'Muerte de Germán Vargas Lleras',
    ('bendito', '2026-09-04'): 'Operativo contra alias Bendito Menor',
    ('bolsonaro', '2026-10-27'): 'Elecciones en Brasil: Flávio Bolsonaro',
    ('fenomeno nino', '2026-05-15'): 'Alerta por el fenómeno de El Niño',
    ('fenomeno nino', '2026-08-28'): 'El Niño: racionamiento de agua',
    ('escrutinio', '2026-06-23'): 'El escrutinio de la segunda vuelta',
    ('angie rodriguez', '2026-07-28'): 'Denuncias de Angie Rodríguez contra Petro',
    ('posesion presidencial', '2026-08-06'): 'La posesión de De la Espriella en Cali',
    ('leon xiv', '2026-10-13'): 'Cirugía del papa León XIV',
    ('ley rescate', '2026-10-30'): 'Radicación de la Ley de Rescate Fiscal',
    ('marchas', '2026-10-14'): 'Las marchas del 14 de octubre',
    ('marco rubio', '2026-09-08'): 'Visita de Marco Rubio a Colombia',
    ('san andres', '2026-10-19'): 'El regaño del presidente en San Andrés',
    ('miguel quintero', '2026-10-02'): 'Casa por cárcel a Miguel Quintero (caso AMVA)',
    ('miguel quintero', '2026-10-30'): 'Miguel Quintero, enviado a Cómbita',
    ('villa leyva', '2026-09-21'): 'Incendio en Villa de Leyva',
    ('deicy jimenez', '2026-11-05'): 'Caso Deicy Jiménez (contratos)',
    ('terremoto panama', '2026-10-09'): 'Terremoto de Panamá (magnitud 8,0)',
    ('camila potosi', '2026-07-31'): 'Crimen de María Camila Potosí',
    ('juliana guerrero', '2026-07-27'): 'Escándalo Juliana Guerrero',
    ('juliana guerrero', '2026-09-09'): 'Juliana Guerrero: títulos falsos',
    ('presupuesto 2027', '2026-10-21'): 'El Presupuesto 2027 sale por decreto',
    ('navarro', '2026-11-01'): 'Muerte de Antonio Navarro Wolff',
    ('santa marta', '2026-09-23'): 'Paro armado y militarización de Santa Marta',
    ('receso', '2026-10-02'): 'Semana de receso escolar',
    ('rodrigo lara', '2026-10-22'): 'Salida de Rodrigo Lara del Ministerio del Interior',
    ('paro armado', '2026-09-24'): 'Paro armado (septiembre)',
    ('porte', '2026-09-08'): 'Decreto que revive el porte de armas',
    ('daniel quintero', '2026-07-10'): 'Señalamientos al hermano de Daniel Quintero',
    ('pacto valledupar', '2026-10-19'): 'El «pacto de Valledupar»',
}
GEN = set('''anos ano hoy dia dias video videos fotos foto nuevo nueva nuevos nuevas tras asi mas sera seran
 mejor mejores gran grandes primer primera cada casi solo ahora luego aqui todo toda todos todas quien quienes
 colombia colombiano colombiana colombianos medellin antioquia bogota pais nacional ciudad municipio
 conozca sepa mira vea habla hablo dijo dice revela revelan anuncia anuncian asegura confirma confirman
 lunes martes miercoles jueves viernes sabado domingo enero febrero marzo abril mayo junio julio agosto
 septiembre octubre noviembre diciembre 2025 2026 2027 semana mes horas hora minuto vivo directo ultima ultimo
 noticias noticia caso casos personas persona millones mil pesos tiene tienen esta estan fue fueron hay
 minuto30 bluradio semana pulzo telemedellin debe deben puede pueden habria harian piden pide'''.split())


def tokens(t, stop):
    w = [x for x in norm(t).split() if len(x) >= 3 and x not in stop]
    uni = {x for x in w if len(x) >= 4 and x not in GEN and not x.isdigit()}
    bi = {a + ' ' + b for a, b in zip(w, w[1:]) if not (a in GEN and b in GEN) and not (a.isdigit() and b.isdigit())}
    return uni | bi


def episodios(D, fin, stop):
    dias = [(INICIO + dt.timedelta(days=i)) for i in range((fin - INICIO).days + 1)]
    di = {d: i for i, d in enumerate(dias)}; n = len(dias)
    docs = [x for x in D if x['d'] in di]
    post = collections.defaultdict(list)                 # término -> [índice de doc]
    for j, x in enumerate(docs):
        for t in tokens(x['t'], stop): post[t].append(j)
    cand = []
    for term, js in post.items():
        if len(js) < 12: continue
        c = [0] * n
        for j in js: c[di[docs[j]['d']]] += 1
        s = sorted(c); base = sum(s[:n // 2]) / (n // 2)      # promedio de la mitad más baja de los días
        if base > 0.7: continue                              # término crónico: no es una historia
        usados = [False] * n
        for _ in range(4):                               # hasta 4 episodios por término
            p = max((i for i in range(n) if not usados[i]), key=lambda i: c[i], default=None)
            if p is None or c[p] < PICO_MIN or c[p] < 4 * (base + .5): break
            thr = max(UMBRAL_MIN, 2 * base)
            mm = lambda i: sum(c[max(0, i - 1):i + 2]) / len(c[max(0, i - 1):i + 2])
            a = p
            sub = max(thr, .1 * c[p])        # hacia atrás el umbral es relativo: la cola de OTRA historia no cuenta como arranque
            while a - 1 >= 0 and mm(a - 1) >= sub and not usados[a - 1]: a -= 1
            b = p
            while b + 1 < n and mm(b + 1) >= thr and not usados[b + 1]: b += 1
            while a < p and c[a] < thr: a += 1           # recorta bordes por debajo del umbral
            while b > p and c[b] < thr: b -= 1
            for i in range(max(0, a - 2), min(n, b + 3)): usados[i] = True
            dset = {j for j in js if a <= di[docs[j]['d']] <= b}
            if len(dset) < 8 or len({docs[j]['m'] for j in dset}) < 2: continue
            cand.append({'term': term, 'a': a, 'b': b, 'p': p, 'base': base, 'docs': dset,
                         'esp': c[p] / (base + .5), 'conc': len(dset) / len(js)})
    # ── fusionar términos que son la misma historia ──
    # Ancla = término con identidad propia: un par de palabras, o una palabra que casi solo existe en
    # ese episodio (≥60 % de sus titulares del semestre). Solo las anclas abren o amplían una historia;
    # las palabras sueltas comunes (nombres de pila, «campaña», «crisis») solo se le cuelgan como rótulo.
    for e in cand: e['ancla'] = ((' ' in e['term']) or e['conc'] >= .6) and e['term'] not in ANCLA_NO
    cand.sort(key=lambda e: (not e['ancla'], -len(e['docs']) * math.log(1 + e['esp'])))
    hist = []
    for e in cand:
        if not e['ancla']:
            for h in hist:
                if e['a'] > h['b'] + 1 or e['b'] < h['a'] - 1: continue
                if len(e['docs'] & h['docs']) / len(e['docs']) >= .6:
                    if e['term'] not in h['terms']: h['terms'].append(e['term'])
                    break
            continue
        hogar = None
        for h in hist:
            if e['a'] > h['b'] + 1 or e['b'] < h['a'] - 1: continue
            inter = len(e['docs'] & h['docs'])
            if inter / min(len(e['docs']), len(h['docs'])) >= .5:
                hogar = h; break
        if hogar:
            # solo amplía la historia si el término aporta poco titular ajeno (evita arrastre)
            nuevos = e['docs'] - hogar['docs']
            if len(nuevos) <= .6 * len(e['docs']):
                hogar['docs'] |= e['docs']
                hogar['a'] = min(hogar['a'], e['a']); hogar['b'] = max(hogar['b'], e['b'])
            if e['term'] not in hogar['terms']: hogar['terms'].append(e['term'])
            hogar['conc'] = max(hogar['conc'], e['conc'])
        else:
            hist.append({'terms': [e['term']], 'a': e['a'], 'b': e['b'], 'docs': set(e['docs']), 'conc': e['conc']})
    # Una historia necesita identidad: un par de palabras, o una palabra que casi solo existe en ese episodio.
    # «campaña», «crisis», «fuerte» o «madre» estallan, pero no son UNA historia.
    hist = [h for h in hist if any(' ' in t for t in h['terms']) or h['conc'] >= .6]
    # Fusión revisada a mano: sinónimos que el solape de titulares no une (sismo / temblor / terremoto).
    def pico_de(h):
        c = collections.Counter(di[docs[j]['d']] for j in h['docs'])
        return max(range(h['a'], h['b'] + 1), key=lambda i: c[i])
    def casa(h, clave):
        t, f = clave
        return h['terms'][0] == t and abs((dias[pico_de(h)] - dt.date.fromisoformat(f)).days) <= 2
    for grupo in FUSION:
        ms = [h for h in hist if any(casa(h, k) for k in grupo)]
        if len(ms) > 1:
            ms.sort(key=lambda h: -len(h['docs']))
            for o in ms[1:]:
                ms[0]['docs'] |= o['docs']; ms[0]['a'] = min(ms[0]['a'], o['a']); ms[0]['b'] = max(ms[0]['b'], o['b'])
                ms[0]['terms'] += [t for t in o['terms'] if t not in ms[0]['terms']]
                hist.remove(o)
    out = []
    for h in hist:
        c = [0] * n
        for j in h['docs']: c[di[docs[j]['d']]] += 1
        a, b = h['a'], h['b']
        p = max(range(a, b + 1), key=lambda i: c[i])
        mm = lambda i: sum(c[max(0, i - 1):i + 2]) / len(c[max(0, i - 1):i + 2])
        mp = max(mm(i) for i in range(max(a, p - 1), min(b, p + 1) + 1))
        vm = None
        for i in range(p + 1, n):
            if mm(i) <= mp / 2: vm = i - p; break
        activos = sum(1 for i in range(a, b + 1) if c[i] >= UMBRAL_MIN)
        dd = [docs[j] for j in h['docs']]
        temas = collections.Counter(x['tema'] for x in dd if x['tema'])
        tema = temas.most_common(1)[0][0] if temas else 'otros'
        sent = collections.Counter(x['s'] for x in dd)
        act = collections.Counter(a_ for x in dd for a_ in x['a'])
        med = collections.Counter(x['m'] for x in dd)
        # titulares de ejemplo: los del día pico con más términos de la historia, de medios distintos
        ts = set(h['terms'])
        dd.sort(key=lambda x: (-(len(tokens(x['t'], stop) & ts)), abs((x['d'] - dias[p]).days)))
        ej, vistos = [], set()
        for x in dd:
            if x['m'] in vistos: continue
            vistos.add(x['m']); ej.append({'t': x['t'], 'm': x['m'], 'd': iso(x['d']), 'u': x['u']})
            if len(ej) == 3: break
        rev = [f"{iso(x['d'])} {x['m']} | {x['t']}" for x in sorted(dd, key=lambda x: x['d'])]
        rev = rev[::max(1, len(rev) // 9)][:10]
        i0, i1 = max(0, a - 5), min(n - 1, b + 10)
        out.append({'terms': h['terms'][:6], 'ini': iso(dias[a]), 'fin': iso(dias[b]), 'pico': iso(dias[p]),
                    'dur': b - a + 1, 'activos': activos, 'vida_media': vm, 'n': len(h['docs']),
                    'pico_n': c[p], 'tema': tema, 'pub': tema != 'cultura_deportes',
                    'crisis': sent['negativo'] / len(dd) >= .5 and tema != 'cultura_deportes',
                    'titulo': next((v for k, v in ROTULOS.items() if casa(h, k)), None),
                    'tema_pct': round(temas[tema] / max(1, sum(temas.values())), 2),
                    'neg': round(sent['negativo'] / len(dd), 2), 'pos': round(sent['positivo'] / len(dd), 2),
                    'actores': [k for k, _ in act.most_common(3)], 'medios': len(med),
                    'medios_top': [k for k, _ in med.most_common(4)],
                    'cortado': b >= n - 2, 'ej': ej, '_rev': rev, 'serie': c[i0:i1 + 1], 'serie_ini': iso(dias[i0])})
    out.sort(key=lambda e: -e['n'])
    return out, n


# Sagas: nombre del asunto completo (no el de una de sus tandas) y pares que NO son una saga
# (nombres de persona sin un caso detrás, o el calendario electoral).
SAGAS_NOMBRE = {
    'fenomeno nino': 'Fenómeno de El Niño', 'miguel quintero': 'Caso Miguel Quintero (contratos del Área Metropolitana)',
    'daniel quintero': 'Daniel Quintero: procesos y señalamientos', 'mateo perez': 'Asesinato del periodista Mateo Pérez',
    'angie rodriguez': 'Denuncias de Angie Rodríguez', 'leon xiv': 'Salud del papa León XIV',
    'juliana guerrero': 'Caso Juliana Guerrero', 'rodrigo lara': 'Rodrigo Lara: nombramiento y salida del Ministerio del Interior',
    'carcel itagui': 'Cárcel de Itagüí'}
SAGAS_NO = {'federico gutierrez', 'elecciones presidenciales', 'ivan cepeda', 'posesion abelardo', 'paloma valencia'}


def sagas(ep):
    """Historias que vuelven: el mismo término ancla con dos o más estallidos separados."""
    g = collections.defaultdict(list)
    for e in ep:
        if e['pub']: g[e['terms'][0]].append(e)
    out = []
    for t, v in g.items():
        if len(v) < 2 or t in SAGAS_NO: continue
        v.sort(key=lambda e: e['pico'])
        out.append({'term': t, 'veces': len(v), 'n': sum(e['n'] for e in v), 'tema': v[0]['tema'],
                    'picos': [e['pico'] for e in v], 'durs': [e['dur'] for e in v],
                    'titulo': SAGAS_NOMBRE.get(t),
                    'dias_entre': (dt.date.fromisoformat(v[-1]['pico']) - dt.date.fromisoformat(v[0]['pico'])).days})
    out.sort(key=lambda r: (-r['veces'], -r['n']))
    return out[:14]


def resumen_dur(ep):
    v = sorted(e['dur'] for e in ep)
    if not v: return {}
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    vm = sorted(e['vida_media'] for e in ep if e['vida_media'] is not None)
    return {'n': len(v), 'mediana': q(.5), 'p75': q(.75), 'p90': q(.9), 'max': v[-1],
            'un_dia': sum(1 for x in v if x <= 1) / len(v), 'hasta3': sum(1 for x in v if x <= 3) / len(v),
            'mas7': sum(1 for x in v if x > 7) / len(v), 'mas14': sum(1 for x in v if x > 14) / len(v),
            'n_mas7': sum(1 for x in v if x > 7), 'n_mas14': sum(1 for x in v if x > 14),
            'vm_mediana': vm[len(vm) // 2] if vm else None,
            'vm_1dia': sum(1 for x in vm if x <= 1) / len(vm) if vm else None,
            'hist': [sum(1 for x in v if lo <= x <= hi) for lo, hi in
                     ((1, 1), (2, 2), (3, 3), (4, 5), (6, 7), (8, 14), (15, 999))]}


# ───────────────────────── ACTORES Y FUERZAS ─────────────────────────
# Se buscan en titular + resumen. Regex sobre texto ORIGINAL (con mayúsculas) cuando la palabra es común.
_GALAN = re.compile(r'\bGal[aá]n\b')
def _galan(cual):
    """Clasifica cada mención del apellido. «Cuando el titular lo permite»: si el texto no trae nombre
    de pila ni contexto de Bogotá o de alcalde, la mención queda como indeterminada y no se le suma a nadie."""
    def f(x):
        t, r = x['t'], x['r']
        if not (_GALAN.search(t) or _GALAN.search(r)): return None
        txt = t + ' ' + r
        if re.search(r'Juan Manuel Gal[aá]n', txt): c = 'jm'
        elif re.search(r'Luis Carlos Gal[aá]n', txt): c = 'lc'
        elif re.search(r'Carlos Fernando|[Aa]lcald|Bogot[aá]|bogotan|Distrito|TransMilenio|pico y placa|\\bcapital\\b', txt): c = 'cf'
        else: c = 'x'
        return bool(_GALAN.search(t)) if c == cual else None
    return f

_BR = re.compile(r'Bolsonaro|Brasil|Lula|Paraguay|Honduras|Canad[aá]')
def _liberal(x):
    R = re.compile(r'Partido Liberal|\b[Ll]os liberales\b|congresistas liberales|bancada liberal')
    txt = x['t'] + ' ' + x['r']
    if not R.search(txt) or _BR.search(txt): return None
    return bool(R.search(x['t']))

FUERZAS = [
    ('nl',        'Nuevo Liberalismo',      r'Nuevo Liberalismo'),
    ('ahora',     'Ahora Colombia',         r'Ahora Colombia'),
    ('mira',      'MIRA',                   r'[Pp]artido MIRA|\b(?:el|del|al) MIRA\b'),
    ('dignidad',  'Dignidad y Compromiso',  r'Dignidad (?:y|&) Compromiso'),
    ('pacto',     'Pacto Histórico',        r'Pacto Hist[oó]rico'),
    ('cd',        'Centro Democrático',     r'Centro Democr[aá]tico|\buribismo\b|\buribistas?\b'),
    ('u',         'Partido de la U',        r'Partido de la U\b|\bLa U\b(?![\.\w]| de| Nacional)'),
    ('cr',        'Cambio Radical',         r'Cambio Radical'),
    ('salvacion', 'Salvación Nacional',     r'Salvaci[oó]n Nacional'),
    ('verde',     'Alianza Verde',          r'Alianza Verde|Partido Verde|\b[Ll]os verdes\b'),
    ('conservador', 'Partido Conservador',  r'Partido Conservador|\b(?:[Ll]os|con|entre) conservadores\b'),
    ('liberal',   'Partido Liberal',        _liberal),
    ('creemos',   'Creemos',                r'(?:movimiento|partido|de|del|por) Creemos\b'),
    ('comunes',   'Comunes',                r'[Pp]artido Comunes'),
]
GALANES = [
    ('galan_cf',  'Carlos Fernando Galán (alcalde de Bogotá)', _galan('cf')),
    ('galan_jm',  'Juan Manuel Galán (director del partido)',  _galan('jm')),
    ('galan_lc',  'Luis Carlos Galán (memoria)',               _galan('lc')),
    ('galan_x',   'Otro Galán o sin contexto',                 _galan('x')),
]
PERSONAS = [
    ('abelardo', 'Abelardo de la Espriella', r'De la Espriella|Abelardo'),
    ('petro',    'Gustavo Petro',            r'\bPetro\b'),
    ('cepeda',   'Iván Cepeda',              r'\bCepeda\b'),
    ('fico',     'Federico Gutiérrez',       r'Federico Guti[eé]rrez|\bFico\b'),
    ('uribe',    'Álvaro Uribe',             r'[AÁ]lvaro Uribe|expresidente Uribe'),
    ('paloma',   'Paloma Valencia',          r'Paloma Valencia'),
    ('fajardo',  'Sergio Fajardo',           r'\bFajardo\b'),
    ('claudia',  'Claudia López',            r'Claudia L[oó]pez'),
    ('quintero', 'Daniel Quintero',          r'Daniel Quintero|\bQuintero\b'),
    ('rendon',   'Andrés Julián Rendón',     r'Andr[eé]s Juli[aá]n|gobernador Rend[oó]n'),
]


def menciones(D, fin, lista):
    meses = sorted({x['d'].strftime('%Y-%m') for x in D if INICIO <= x['d'] <= fin})
    mi = {m: i for i, m in enumerate(meses)}
    tot_mes = [0] * len(meses)
    for x in D:
        if INICIO <= x['d'] <= fin: tot_mes[mi[x['d'].strftime('%Y-%m')]] += 1
    out = []
    for k, nom, rx in lista:
        if callable(rx): fn = rx
        else:
            R = re.compile(rx)
            fn = (lambda R: lambda x: (True if R.search(x['t']) else (False if R.search(x['r']) else None)))(R)
        serie = [0] * len(meses); sent = collections.Counter(); tit = 0; hits = []
        temas = collections.Counter(); med = collections.Counter()
        for x in D:
            if not (INICIO <= x['d'] <= fin): continue
            en_t = fn(x)
            if en_t is None: continue
            x['_t'] = en_t
            serie[mi[x['d'].strftime('%Y-%m')]] += 1
            sent[x['s'] or 'sin'] += 1; tit += en_t; med[x['m']] += 1
            if x['tema']: temas[x['tema']] += 1
            hits.append(x)
        n = sum(serie)
        hits.sort(key=lambda x: (not x['_t'], -x['d'].toordinal()))
        out.append({'k': k, 'n': nom, 'total': n, 'en_titular': tit, 'serie': serie,
                    'neg': round(sent['negativo'] / n, 3) if n else None,
                    'pos': round(sent['positivo'] / n, 3) if n else None,
                    'neu': round(sent['neutro'] / n, 3) if n else None,
                    'temas': temas.most_common(4), 'medios': med.most_common(4),
                    'ej': [{'t': x['t'], 'm': x['m'], 'd': iso(x['d']), 'u': x['u'], 's': x['s'], 'tit': x['_t']} for x in hits[:10]]})
    return {'meses': meses, 'tot_mes': tot_mes, 'lista': out}


def actores_campo(D, fin):
    """Campo `actores` del clasificador (lista cerrada, centrada en Medellín y Antioquia)."""
    c = collections.Counter(); s = collections.defaultdict(collections.Counter)
    for x in D:
        if not (INICIO <= x['d'] <= fin): continue
        for a in x['a']:
            c[a] += 1; s[a][x['s']] += 1
    return [{'n': a, 'total': v, 'neg': round(s[a]['negativo'] / v, 3), 'pos': round(s[a]['positivo'] / v, 3)}
            for a, v in c.most_common(15)]


def tono(D, fin):
    c = collections.defaultdict(collections.Counter)
    for x in D:
        if INICIO <= x['d'] <= fin and x['tema']: c[x['tema']][x['s']] += 1
    out = []
    for t, v in c.items():
        n = sum(v.values())
        out.append({'tema': t, 'n': n, 'neg': round(v['negativo'] / n, 3), 'neu': round(v['neutro'] / n, 3),
                    'pos': round(v['positivo'] / n, 3)})
    out.sort(key=lambda r: -r['neg'])
    return out


# ───────────────────────── CRISIS SOSTENIDA: el entorno de Petro ─────────────────────────
# La detección de historias corta cada caso en brotes de 2 a 5 días. Pero los casos del círculo del gobierno
# Petro se relevan unos a otros todo el semestre: esto mide la crisis como conjunto. Solo TITULAR (no resumen),
# cada titular se asigna al primer caso que lo nombra. «Primera dama» suelta no cuenta: en la prensa de
# Antioquia la usan las gestoras sociales de los municipios.
CASOS_PETRO = [
    ('ungrd',   'UNGRD (carrotanques y contratos)', r'\bUNGRD\b|carrotanques.{0,50}(?:UNGRD|Guajira|esc[aá]ndalo)|esc[aá]ndalo.{0,50}carrotanques',
     r'terremoto|sismo|damnific|lluvias|temporada|ayudas|alerta|emergencia|fallecid|desaparecid|invierno|v[ií]ctimas|reporta|escombros|incendio|El Ni[ñn]o|sequ[ií]a|subdirector|nombra|sin agua|acueducto|hect[aá]reas|articularse'),
    ('angie',   'Angie Rodríguez',                   r'Angie Rodr[ií]guez'),
    ('juliana', 'Juliana Guerrero',                  r'Juliana Guerrero'),
    ('alcocer', 'Verónica Alcocer y Eva Ferrer',     r'Ver[oó]nica Alcocer|\bAlcocer\b|Eva Ferrer'),
    ('deicy',   'Denuncia de Deicy Jiménez (presuntos «sexocontratos»)', r'De[iy]c[iy] Jim[eé]nez|sexocontrat|(?:Petro|contrat)\w*.{0,70}favores sexuales|favores sexuales.{0,70}(?:Petro|contrat)'),
    ('nicolas', 'Nicolás Petro',                     r'Nicol[aá]s Petro'),
]


def crisis_petro(D, fin):
    dias = [INICIO + dt.timedelta(days=i) for i in range((fin - INICIO).days + 1)]
    di = {d: i for i, d in enumerate(dias)}
    R = [(c[0], c[1], re.compile(c[2], re.I), re.compile(c[3], re.I) if len(c) > 3 else None) for c in CASOS_PETRO]
    serie = {k: [0] * len(dias) for k, _, _, _ in R}
    sent = collections.Counter(); ej = collections.defaultdict(list); medios = collections.Counter()
    pub_dia = [0] * len(dias)
    for x in D:
        if not (INICIO <= x['d'] <= fin): continue
        if x['tema'] and x['tema'] not in FUERA: pub_dia[di[x['d']]] += 1
        for k, _, rx, no in R:
            if rx.search(x['t']) and not (no and no.search(x['t'])):
                serie[k][di[x['d']]] += 1; sent[x['s'] or 'sin'] += 1; medios[x['m']] += 1
                ej[k].append(x); break
    tot = [sum(serie[k][i] for k in serie) for i in range(len(dias))]
    n = sum(tot)
    # rachas: días seguidos con al menos un titular; y el silencio más largo entre el primero y el último
    con = [i for i, v in enumerate(tot) if v > 0]
    racha = mejor = 0; silencio = s = 0
    for i in range(con[0], con[-1] + 1):
        if tot[i] > 0: racha += 1; mejor = max(mejor, racha); s = 0
        else: racha = 0; s += 1; silencio = max(silencio, s)
    sem = []
    for j in range(0, len(dias) - 6, 7):
        c = sum(tot[j:j + 7]); p = sum(pub_dia[j:j + 7])
        sem.append({'d': iso(dias[j]), 'n': c, 'part': round(c / p, 4) if p else 0,
                    'casos': {k: sum(serie[k][j:j + 7]) for k in serie}})
    casos = []
    for k, nom, _, _ in R:
        v = serie[k]; m = sum(v)
        if not m: continue
        idx = [i for i, c in enumerate(v) if c]
        pk = max(range(len(v)), key=lambda i: v[i])
        brotes = 0; prev = -99
        for i in idx:                       # un brote nuevo tras 7 días o más sin titulares del caso
            if i - prev > 7: brotes += 1
            prev = i
        vistos = set(); muestra = []
        for x in sorted(ej[k], key=lambda x: x['d']):
            kk = norm(x['t'])[:60]
            if kk in vistos: continue
            vistos.add(kk); muestra.append(x)
        paso = max(1, len(muestra) // 4)
        muestra = muestra[::paso][:4]
        casos.append({'k': k, 'n': nom, 'total': m, 'ini': iso(dias[idx[0]]), 'fin': iso(dias[idx[-1]]),
                      'dias_con': len(idx), 'pico': iso(dias[pk]), 'pico_n': v[pk], 'brotes': brotes,
                      'serie': v,
                      'ej': [{'t': x['t'], 'm': x['m'], 'd': iso(x['d']), 'u': x['u']} for x in muestra]})
    casos.sort(key=lambda c: -c['total'])
    return {'ini': iso(INICIO), 'dias': len(dias), 'total': n, 'dias_con': len(con), 'racha': mejor,
            'silencio': silencio, 'semanas_con': sum(1 for w in sem if w['n'] > 0), 'semanas': sem,
            'neg': round(sent['negativo'] / n, 3) if n else None, 'medios': len(medios),
            'nota': 'Titulares (no resúmenes) que nombran alguno de los casos; cada titular cuenta una vez.',
            'casos': casos}


# ───────────────────────── GOOGLE NEWS (opcional, prensa nacional) ─────────────────────────
_OTRO_PAIS = re.compile(r'plra|paraguay|efrain|alegre|vaesken|asuncion|concepcion|bolsonaro|brasil|lula|honduras|canada|carney|trudeau|australia|argentina|milei|chile|peru|mexico|espana', re.I)
_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'


def _gn(q, ventana):
    url = ('https://news.google.com/rss/search?q=' + urllib.parse.quote(q + ' when:' + ventana) +
           '&hl=es-419&gl=CO&ceid=CO:es-419')
    xml = subprocess.run(['/usr/bin/curl', '-sL', '--max-time', '40', '-A', _UA, url],
                         capture_output=True, timeout=60).stdout
    root = ET.fromstring(xml)
    items = []
    for it in root.iter('item'):
        t = (it.findtext('title') or '').strip()
        src = (it.findtext('source') or '').strip()
        if src and t.endswith(' - ' + src): t = t[:-len(src) - 3]
        try: d = dt.datetime.strptime(it.findtext('pubDate'), '%a, %d %b %Y %H:%M:%S %Z').date()
        except Exception: continue
        items.append({'t': t, 'm': src, 'd': iso(d)})
    return items


def gnews():
    """Prensa nacional vía Google News RSS. Muestra, no censo: el RSS entrega como máximo ~100 resultados
    por consulta. Solo se cuentan titulares que traen el nombre y no nombran otro país (hay un «Nuevo
    Liberalismo» en Paraguay y un «Partido Liberal» en Brasil)."""
    cons = [('nl', 'Nuevo Liberalismo', '"Nuevo Liberalismo"'),
            ('galan_cf', 'Carlos Fernando Galán', '"Carlos Fernando Galán"'),
            ('galan_jm', 'Juan Manuel Galán', '"Juan Manuel Galán"')]
    res = []
    for k, nom, q in cons:
        try: bruto = _gn(q, '60d')
        except Exception as e:
            res.append({'k': k, 'n': nom, 'error': str(e)[:80], 'items': []}); continue
        nuc = norm(nom).split()
        items = [x for x in bruto if all(w in norm(x['t']) for w in nuc[-2:]) and not _OTRO_PAIS.search(norm(x['t']))
                 and x['m'] not in ('La Nación', 'La Política Online', 'ABC Color', 'Última Hora', 'Hoy')]
        items.sort(key=lambda x: x['d'], reverse=True)
        sem = collections.Counter(iso(lunes(dt.date.fromisoformat(x['d']))) for x in items)
        res.append({'k': k, 'n': nom, 'devueltos': len(bruto), 'total': len(items), 'tope': len(bruto) >= 95,
                    'medios': collections.Counter(x['m'] for x in items).most_common(8),
                    'semanas': sorted(sem.items()), 'items': items[:14]})
    comp = []
    for nom in ['Nuevo Liberalismo', 'Pacto Histórico', 'Centro Democrático', 'Partido Liberal', 'Partido Conservador',
                'Cambio Radical', 'Alianza Verde', 'Partido de la U', 'Salvación Nacional', 'Partido MIRA']:
        try: bruto = _gn('"' + nom + '"', '7d')
        except Exception: comp.append({'n': nom, 'error': True}); continue
        nuc = norm(nom).split()
        ok = [x for x in bruto if all(w in norm(x['t']) for w in nuc) and not _OTRO_PAIS.search(norm(x['t']))]
        comp.append({'n': nom, 'devueltos': len(bruto), 'en_titular': len(ok), 'tope': len(bruto) >= 95})
    return {'consultado': iso(dt.datetime.now(TZ).date()), 'ventana': '60 días',
            'nota': 'Google News entrega como máximo ~100 resultados por consulta: es una muestra, no un censo.',
            'consultas': res, 'comparacion_7d': comp}


def main():
    stop = {norm(l.strip()).strip() for l in open(STOP_F, encoding='utf-8') if l.strip() and not l.startswith('#')}
    D, n_raw, n_enr = cargar()
    ult = max(x['d'] for x in D)
    fin = ult - dt.timedelta(days=(ult.weekday() + 1) % 7)        # último domingo completo
    if fin >= ult: fin -= dt.timedelta(days=7) if ult.weekday() != 6 else dt.timedelta(0)
    per = [x for x in D if INICIO <= x['d'] <= fin]
    med = collections.Counter(x['m'] for x in per)
    ag = agenda(D, fin)
    ep, ndias = episodios(D, fin, stop)
    if '--revisar' in sys.argv:
        for e in ep[:int(sys.argv[sys.argv.index('--revisar') + 1]) if len(sys.argv) > sys.argv.index('--revisar') + 1 else 60]:
            print(f"\n[{e['tema']}{'' if e['pub'] else ' ·FUERA'}] n={e['n']} dur={e['dur']} act={e['activos']} vm={e['vida_media']} pico={e['pico']}({e['pico_n']}) {e['ini']}→{e['fin']} medios={e['medios']} :: {', '.join(e['terms'])}")
            for x in e['_rev']: print('    ', x[:170])
        return
    pub = [e for e in ep if e['pub'] and not e['cortado']]
    sal = {
        'v': iso(dt.datetime.now(TZ).date()),
        'cobertura': {
            'unicos_banco': len(D), 'clasificados_banco': sum(1 for x in D if x['tema']),
            'lineas_crudas': n_raw, 'ini': iso(INICIO), 'fin': iso(fin), 'dias': ndias,
            'unicos': len(per), 'con_tema': sum(1 for x in per if x['tema']),
            'publico': sum(1 for x in per if x['tema'] and x['tema'] not in FUERA),
            'fuera': {t: sum(1 for x in per if x['tema'] == t) for t in FUERA},
            'medios': [{'k': m, 'n': MEDIOS.get(m, m), 'total': v, 'nacional': m in NACIONALES}
                       for m, v in med.most_common()],
            'sent': dict(collections.Counter(x['s'] for x in per if x['s'])),
            'dia_min': min(collections.Counter(x['d'] for x in per).values()),
            'dia_max': max(collections.Counter(x['d'] for x in per).values())},
        'temas': {k: {'n': v[0], 'c': v[1]} for k, v in TEMAS.items()},
        'series8': SERIES8,
        'agenda': ag,
        'episodios': {'metodo': {'pico_min': PICO_MIN, 'umbral_min': UMBRAL_MIN},
                      'todos': resumen_dur([e for e in ep if not e['cortado']]),
                      'publico': resumen_dur(pub),
                      'por_tema': {t: resumen_dur([e for e in pub if e['tema'] == t])
                                   for t in TEMAS if t not in FUERA and sum(1 for e in pub if e['tema'] == t) >= 8},
                      'lista': [{k: v for k, v in e.items() if k != '_rev'} for e in ep]},
        'fuerzas': menciones(D, fin, FUERZAS),
        'galanes': menciones(D, fin, GALANES),
        'hitos': [{'d': '2026-05-31', 't': 'Primera vuelta'}, {'d': '2026-06-21', 't': 'Segunda vuelta'},
                  {'d': '2026-08-07', 't': 'Posesión'}, {'d': '2026-08-10', 't': 'Terremoto'},
                  {'d': '2026-10-29', 't': 'Ley de Rescate'}],
        'sagas': sagas(ep),
        'personas': menciones(D, fin, PERSONAS),
        'actores': actores_campo(D, fin),
        'tono': tono(D, fin),
        'crisis': crisis_petro(D, fin),
    }
    if '--sin-gnews' not in sys.argv:
        sal['gnews'] = gnews()
    elif os.path.exists(SAL):                       # conserva la última consulta a Google News
        prev = json.load(open(SAL, encoding='utf-8')).get('gnews')
        if prev: sal['gnews'] = prev
    os.makedirs(os.path.dirname(SAL), exist_ok=True)
    txt = json.dumps(sal, ensure_ascii=False, separators=(',', ':'), default=str)
    open(SAL, 'w', encoding='utf-8').write(txt)
    # gemelo .js: NL.dato('clima') lo carga con <script>, así la página abre también con file://
    open(SAL[:-5] + '.js', 'w', encoding='utf-8').write('window.NLD=window.NLD||{};window.NLD.clima=' + txt + ';\n')
    print('→', SAL, round(os.path.getsize(SAL) / 1024), 'KB')
    c = sal['cobertura']; print(c['unicos'], 'titulares', c['ini'], c['fin'], '| públicos', c['publico'])
    print('episodios', len(ep), '| públicos cerrados', len(pub), sal['episodios']['publico'])
    for f in sal['fuerzas']['lista']: print(f"  {f['n']:<24} {f['total']:>5}  titular {f['en_titular']:>4}  neg {f['neg']}")


if __name__ == '__main__':
    main()
