"""Valida las tuplas nuevas ANTES de tocar empresas.py:
claves duplicadas · tópicos inválidos · sectores inválidos · alias que chocan
entre sí o con el diccionario vivo · alias peligrosos (palabra común corta)."""
import glob, sys, re
sys.path.insert(0,'/Users/ricardoruiz/ricardoruiz.co/tools/caudal')
import os
S = os.environ.get("CAUDAL_DICC_DIR", "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/caudal-diccionario")
import empresas as E, caudal_core as C

AMBIGUOS = {
    'zenu', 'exito', 'meta', 'ara', 'claro', 'familia', 'corona', 'consumo',
    'finca', 'suizo', 'duquesa', 'centro', 'grupo', 'nacional', 'popular',
    'bolivar', 'santander', 'colombia', 'occidente', 'oriente', 'norte', 'sur',
    'union', 'social', 'mundial', 'total', 'general', 'central', 'ela', 'urra',
}
TOP = {t['k'] for t in C.SINONIMOS}
SEC = {e['sector'] for e in E.EMPRESAS}
# ⚠ El diccionario vivo YA puede tener integrada una versión anterior de estas
# mismas tandas (el integrador es idempotente). Comparar contra él a secas
# reporta "ya existe" para cada tupla propia. Se excluyen las claves de tanda.
import glob as _g
_propias = set()
for _f in _g.glob(f"{S}/tandas/*.py"):
    _gd = {}; exec(open(_f).read(), _gd)
    for _t in _gd['TUPLAS']: _propias.add(_t[0])
viejas_k = {e['k'] for e in E.EMPRESAS if e['k'] not in _propias}
viejas_alias = {}
for e in E.EMPRESAS:
    if e['k'] in _propias: continue
    for a in e['alias']: viejas_alias.setdefault(a, e['nombre'])

nuevas = []
for f in sorted(glob.glob(f"{S}/tandas/*.py")):
    g = {}
    exec(open(f).read(), g)
    for t in g['TUPLAS']: nuevas.append((f.split('/')[-1], t))

err = []
vistas_k, vistas_alias = {}, {}
for src, t in nuevas:
    if len(t) not in (7, 8): err.append((src, t[0], f'tupla de {len(t)} campos')); continue
    k, nombre, sector, alias, tops, ent, veto = t[:7]
    if not re.fullmatch(r'[a-z0-9]+', k):
        err.append((src, k, 'la clave debe ser minúsculas/dígitos sin espacios'))
    if k in viejas_k: err.append((src, k, 'clave YA EXISTE en el diccionario'))
    if k in vistas_k: err.append((src, k, f'clave duplicada (también en {vistas_k[k]})'))
    vistas_k[k] = src
    if sector not in SEC: err.append((src, k, f'sector inválido: {sector}'))
    for tp in tops.split(','):
        tp = tp.strip().lstrip('*')
        if tp and tp not in TOP: err.append((src, k, f'tópico inválido: {tp}'))
    for a in [x.strip() for x in alias.split('|') if x.strip()]:
        if a in viejas_alias: err.append((src, k, f'alias «{a}» ya es de {viejas_alias[a]}'))
        if a in vistas_alias: err.append((src, k, f'alias «{a}» choca con {vistas_alias[a]}'))
        vistas_alias[a] = k
        # el riesgo no es la longitud sino la AMBIGÜEDAD: que el alias sea una
        # palabra del español, un apellido o un topónimo. Medido: 'zenu' choca con
        # el pueblo Zenú, 'claro'/'exito' con palabras comunes. Marcas inventadas
        # como 'zoetis' o 'pulzo' no tienen ese problema por cortas que sean.
        if a in AMBIGUOS:
            err.append((src, k, f'alias AMBIGUO (palabra común/etnia/topónimo): «{a}»'))
        if len(a) < 4:
            err.append((src, k, f'alias de menos de 4 letras: «{a}»'))
print(f'tuplas nuevas: {len(nuevas)}')
if err:
    print(f'PROBLEMAS: {len(err)}')
    for s, k, m in err: print(f'  [{s}] {k}: {m}')
else:
    print('sin problemas estructurales')
