"""Verificador de evidencia: una empresa propuesta solo entra al diccionario si
el DATO la respalda. Tres fuentes, ninguna inventada:
  · SECOP    — es proveedor del Estado (razón social con NIT)
  · actos    — tiene acto regulatorio a su nombre
  · texto    — el articulado del Congreso la nombra
Uso:  python3 verificar_evidencia.py nombres.txt   (un nombre por línea)
"""
import json, re, sys, unicodedata
from collections import defaultdict
import os
S = os.environ.get("CAUDAL_DICC_DIR", "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/caudal-diccionario")
BASE="/Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado"

def n(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ', re.sub(r'[^a-z0-9 ]',' ',s)).strip()

_cache = {}
def cargar():
    if _cache: return _cache
    # SECOP: proveedores por conteo y por valor
    prov = {}
    for f in ('secop_nit.json','secop_valor.json'):
        try: d = json.load(open(f"{S}/{f}"))
        except Exception: continue
        for p in d:
            k = n(p.get('proveedor_adjudicado'))
            if len(k) < 4: continue
            r = prov.setdefault(k, {'n':0,'v':0.0,'raw':p.get('proveedor_adjudicado')})
            r['n'] = max(r['n'], int(p.get('n') or 0))
            r['v'] = max(r['v'], float(p.get('v') or 0))
    # actos regulatorios
    actos = defaultdict(int)
    with open(f"{BASE}/supers/dist/sanciones.jsonl") as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except Exception: continue
            k = n(r.get('sancionado'))
            if len(k) >= 5: actos[k] += 1
    # articulado del Congreso: palabras -> nº de proyectos
    try: ti = json.load(open(f"{BASE}/dist/texto-index.json"))
    except Exception: ti = {}
    idx = ti.get('idx') or ti.get('index') or ti if isinstance(ti, dict) else {}
    _cache.update(prov=prov, actos=dict(actos), texto=idx)
    return _cache

def evidencia(nombre):
    c = cargar()
    k = n(nombre)
    toks = [t for t in k.split() if len(t) > 3]
    out = {'secop': 0, 'valor': 0.0, 'actos': 0, 'texto': 0, 'razon_social': None}
    # SECOP / actos: la clave aparece como palabra dentro de la razón social
    rx = re.compile(r'(?<![a-z0-9])' + re.escape(k) + r'(?![a-z0-9])')
    for rk, r in c['prov'].items():
        if rx.search(rk):
            if r['n'] > out['secop']:
                out['secop'], out['valor'], out['razon_social'] = r['n'], r['v'], r['raw']
    for rk, v in c['actos'].items():
        if rx.search(rk): out['actos'] += v
    # articulado: la palabra más distintiva del nombre
    if toks:
        d = c['texto']
        cand = [t for t in toks if t in d]
        if cand: out['texto'] = max(len(d[t]) if isinstance(d[t], (list, dict)) else 0 for t in cand)
    out['ok'] = bool(out['secop'] or out['actos'] or out['texto'])
    return out

if __name__ == '__main__':
    nombres = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
    cargar()
    con = sin = 0
    for nm in nombres:
        e = evidencia(nm)
        if e['ok']:
            con += 1
            print(f"OK    {nm:38.38s} secop:{e['secop']:5d} actos:{e['actos']:4d} texto:{e['texto']:4d}  {(e['razon_social'] or '')[:40]}")
        else:
            sin += 1
            print(f"--    {nm:38.38s} sin evidencia en ninguna fuente")
    print(f"\n{con} con evidencia · {sin} sin evidencia · de {len(nombres)}")
