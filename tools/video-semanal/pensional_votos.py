#!/usr/bin/env python3
"""Video semanal · reforma pensional: quién de la Cámara actual votó en 2024 y 2025.

Une el voto electrónico (dist/votaciones-camara-nominal.jsonl) con el voto MANUAL de
la sesión del 28-jun-2025, que viene escaneado en el acta 43742 y se transcribió a mano
(abajo). Con los dos, los totales cuadran con la cifra oficial: reabrir el articulado
se negó 100 a 11.

Salida: Bases de datos/video-semanal/<semana>/pensional-votos.json
"""
import collections, json, re, sys, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VOT = REPO / 'Bases de datos/leyes-senado/dist/votaciones-camara-nominal.jsonl'
INT = REPO / 'Bases de datos/legislativo/fuerzas-internas-2026.json'
SEMANA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-27'
OUT = REPO / 'Bases de datos/video-semanal' / SEMANA / 'pensional-votos.json'

VOTACIONES = {
    ('2024-06-14', '43505', 13): 'acoger_2024',      # acoger el texto del Senado (aprobación de fondo)
    ('2024-06-14', '43505', 8): 'juvinao_2024',      # prop. Juvinao: votar primero la vigencia (art. 94)
    ('2024-06-14', '43505', 7): 'bloque_2024',       # bloque de proposiciones de modificación
    ('2025-06-28', '43742', 4): 'acoger_2025',       # repetición ordenada por la Corte (Auto 841)
    ('2025-06-28', '43742', 5): 'reabrir_2025',      # prop. Wills: reabrir el articulado (lo que hoy se subsana)
}
# Voto manual del 28-jun-2025, acta 43742 «Votaciones manuales 28-06-2025.pdf» (escaneado).
MANUAL = {
    'acoger_2025': {'Si': """AGUIRRE JUVINAO INGRID JOHANA|AVILA MORALES CAMILO ESTEBAN|BARGUIL CUBILLOS NICOLAS ANTONIO|
        CAYCEDO ROSERO RUTH AMELIA|CERCHIARO FIGUEROA JORGE ALBERTO|CORTES DUEÑAS JUAN MANUEL|CRUZ CASADO LIBARDO|
        CUELLAR PINZON HECTOR MAURICIO|CUELLO BAUTE APE ALFREDO|DIAZ MATEUS LUIS EDUARDO|ISAZA BUENAVENTURA DELCY ESPERANZA|
        MOSQUERA TORRES JAMES HERMENEGILDO|PALENCIA VEGA LEONOR MARIA|PEINADO RAMIREZ JULIAN|PETE VIVAS ERMES EVELIO|
        QUEVEDO HERRERA JORGE ALEXANDER|ROBAYO BECHARA SARAY ELENA|WILLS OSPINA JUAN CARLOS|YEPES CARO GERARDO""", 'No': ''},
    'reabrir_2025': {'Si': 'OCAMPO GIRALDO JORGE ALEJANDRO', 'No': """AGUIRRE JUVINAO INGRID JOHANA|BECERRA YAÑEZ GABRIEL|
        CAYCEDO ROSERO RUTH AMELIA|CERCHIARO FIGUEROA JORGE ALBERTO|CORTES DUEÑAS JUAN MANUEL|COTES MARTINEZ KARYME ADRIANA|
        CRUZ CASADO LIBARDO|CUELLO BAUTE APE ALFREDO|DIAZ MATEUS LUIS EDUARDO|ESCAF TIJERINO AGMETH JOSE|
        ISAZA BUENAVENTURA DELCY ESPERANZA|LONDOÑO LUGO ALVARO MAURICIO|MONTAÑO ARIZALA GERSON LISIMACO|
        MOSQUERA TORRES JAMES HERMENEGILDO|PALENCIA VEGA LEONOR MARIA|PETE VIVAS ERMES EVELIO|ROBAYO BECHARA SARAY ELENA|
        TORRES ROMERO DOLCEY OSCAR|WILLS OSPINA JUAN CARLOS"""},
}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z ]', ' ', s)).strip()


def toks(s):
    return frozenset(t for t in norm(s).split() if len(t) > 2)


def misma(a, b):
    i = a & b
    return len(i) >= 3 or (len(i) >= 2 and (a <= b or b <= a))


votos = {v: {} for v in VOTACIONES.values()}   # clave -> {nombre_norm: (resp, partido)}
partido_de = {}
for line in open(VOT, encoding='utf-8'):
    r = json.loads(line)
    n = norm(r.get('roster_key') or r.get('congresista') or r.get('nombre') or '')
    if not n:
        continue
    if r.get('partido'):
        partido_de.setdefault(n, r['partido'])
    k = VOTACIONES.get((r['fecha'], r['acta_id'], r['votacion_numero']))
    if k:
        votos[k][n] = r['respuesta']
for k, d in MANUAL.items():
    for resp, lista in d.items():
        for n in filter(None, (x.strip() for x in lista.split('|'))):
            votos[k][norm(n)] = resp

def partido(n):
    t = toks(n)
    for m, p in partido_de.items():
        if misma(t, toks(m)):
            return p
    return None

def canon(p):
    p = norm(p)
    for clave, nom in (('PACTO', 'Pacto Histórico'), ('CENTRO DEMOCR', 'Centro Democrático'), ('CAMBIO RADICAL', 'Cambio Radical'),
                       ('LIBERAL', 'Partido Liberal'), ('CONSERVADOR', 'Partido Conservador'), ('UNION POR LA GENTE', 'Partido de la U'),
                       ('ALIANZA VERDE', 'Alianza Verde'), ('VERDE', 'Alianza Verde'), ('COMUNES', 'Comunes'), ('MIRA', 'MIRA'),
                       ('FUERZA CIUDADANA', 'Fuerza Ciudadana'), ('NUEVO LIBERALISMO', 'Nuevo Liberalismo'), ('SALVACION', 'Salvación Nacional'),
                       ('DIGNIDAD', 'Dignidad'), ('POLO', 'Pacto Histórico'), ('COLOMBIA HUMANA', 'Pacto Histórico'), ('LIGA', 'Liga Anticorrupción')):
        if clave in p:
            return nom
    return p.title() if p else 'Sin partido registrado'

resumen = {}
for k, d in votos.items():
    c = collections.defaultdict(collections.Counter)
    for n, resp in d.items():
        c[canon(partido(n))][resp] += 1
    resumen[k] = {'total': dict(collections.Counter(d.values())),
                  'por_partido': {p: dict(x) for p, x in sorted(c.items(), key=lambda kv: -sum(kv[1].values()))}}

I = json.load(open(INT))
actuales = I['camara']['miembros']
cruce = []
for m in actuales:
    t = toks(m['n'])
    fila = {'nombre': m['n'], 'bancada': m['b'], 'comision': m.get('c')}
    for k, d in votos.items():
        hit = next((resp for n, resp in d.items() if misma(t, toks(n))), None)
        if hit:
            fila[k] = hit
    cruce.append(fila)

por_bancada = collections.defaultdict(lambda: collections.Counter())
for f in cruce:
    b = f['bancada']
    por_bancada[b]['total'] += 1
    v = f.get('reabrir_2025') or ('ausente' if any(k.endswith('2025') for k in f) else None)
    estuvo = any(k in f for k in VOTACIONES.values())
    por_bancada[b]['estuvo' if estuvo else 'nuevo'] += 1
    if f.get('acoger_2025'): por_bancada[b]['acoger25_' + f['acoger_2025']] += 1
    if f.get('reabrir_2025'): por_bancada[b]['reabrir25_' + f['reabrir_2025']] += 1
    if f.get('acoger_2024'): por_bancada[b]['acoger24_' + f['acoger_2024']] += 1

OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump({'semana': SEMANA, 'resumen': resumen, 'camara_actual': len(actuales),
           'por_bancada_actual': {b: dict(x) for b, x in sorted(por_bancada.items(), key=lambda kv: -kv[1]['total'])},
           'repitentes': [f for f in cruce if len(f) > 3]},
          open(OUT, 'w'), ensure_ascii=False, indent=1)
for k, v in resumen.items():
    print(k, v['total'])
print('Cámara actual:', len(actuales), '· estuvieron en alguna de esas votaciones:', sum(1 for f in cruce if len(f) > 3))
for b, x in sorted(por_bancada.items(), key=lambda kv: -kv[1]['total']):
    print(f"  {b:28s} {dict(x)}")
print('→', OUT)
