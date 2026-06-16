#!/usr/bin/env python3
"""
build_depto1v.py — agrega el preconteo/escrutinio 1V 2026 por departamento
para el simulador de trasvase de `ponderador-2v.html`.

Entrada : Bases de datos/output_pacto_1v_2026/master_2026_puesto.json
          (14.220 puestos georef · todas las columnas de candidato + blanco/
           nulo/no-marcado + total_votos_urna + pot[encial])
Salida  : tools/ponderador-2v/depto1v.json  (~4 KB)
          → se PEGA inline en `ponderador-2v.html` (const D1V = {...}).

Notas:
- Claudia López llega en 0 por puesto en el preconteo; se RECUPERA como el
  residual `total_votos_urna − suma(partes)` (idéntico al truco documentado
  en CLAUDE.md → 225.287 nacional exacto). Se agrega al bucket `cla`.
- `otr` = menores reales (Botero, Lizcano, Miguel Uribe, Macollins, Roy,
  Murillo, Caicedo, Matamoros).
- `bln` = blanco + nulo + no-marcado (bloque protesta/invalido de 1V).
- Exterior (dep 88) entra al nacional pero NO al mapa (sin polígono).
- Las cifras son ~99,9% del potencial (snapshot 0247). Cuando salga el
  escrutinio oficial definitivo, re-correr sobre el master actualizado.

Uso: python3 tools/ponderador-2v/build_depto1v.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC  = os.path.join(ROOT, "Bases de datos/output_pacto_1v_2026/master_2026_puesto.json")
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "depto1v.json")

DEP = {'16':'Bogotá','01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá',
       '09':'Caldas','11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca',
       '17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda',
       '25':'Norte de Santander','26':'Quindío','27':'Santander','28':'Sucre',
       '29':'Tolima','31':'Valle del Cauca','40':'Arauca','44':'Caquetá',
       '46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare',
       '56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada',
       '88':'Exterior'}
CANDS   = ['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe',
           'macollins','roy','murillo','caicedo','matamoros','claudia']
MENORES = ['botero','lizcano','miguel_uribe','macollins','roy','murillo','caicedo','matamoros']

def main():
    d = json.load(open(SRC))
    agg = {}
    for r in d:
        dep = r['dep']
        a = agg.setdefault(dep, {k:0 for k in ['cep','abe','pal','faj','cla','otr','bln','urna','pot']})
        partes = sum((r.get(c,0) or 0) for c in CANDS)
        partes += sum((r.get(k,0) or 0) for k in ['votos_blanco','votos_nulos','votos_no_marcados'])
        tot = r.get('total_votos_urna',0) or 0
        a['cep'] += r.get('cepeda',0) or 0
        a['abe'] += r.get('abelardo',0) or 0
        a['pal'] += r.get('paloma',0) or 0
        a['faj'] += r.get('fajardo',0) or 0
        a['cla'] += max(0, tot - partes)               # Claudia recuperada (residual)
        a['otr'] += sum((r.get(c,0) or 0) for c in MENORES)
        a['bln'] += (r.get('votos_blanco',0) or 0)+(r.get('votos_nulos',0) or 0)+(r.get('votos_no_marcados',0) or 0)
        a['urna'] += tot
        a['pot']  += r.get('pot',0) or 0

    out = {"v":"2026-06-15",
           "fuente":"preconteo 1V 2026 (snapshot 0247, ~99,9% del potencial)",
           "nacional":{}, "deptos":{}}
    nac = {k:0 for k in ['cep','abe','pal','faj','cla','otr','bln','urna','pot']}
    for dep, a in agg.items():
        for k in nac: nac[k] += a[k]
        if dep == '88': continue
        out["deptos"][DEP[dep]] = a
    out["nacional"] = nac
    json.dump(out, open(OUT,"w"), ensure_ascii=False, separators=(',',':'))
    print(f"escrito {OUT} ({os.path.getsize(OUT)} bytes · {len(out['deptos'])} deptos)")
    print(f"nacional Cepeda {nac['cep']:,} · Abelardo {nac['abe']:,}")

    # ── mun1v.json: 1V por municipio para el toggle Departamentos/Municipios.
    # Formato compacto: { "DDMMM": [cep,abe,pal,faj,cla,otr,bln,urna,pot] }.
    # Clave = dep+mun (electoral) → coincide con dep_electoral+mun_elec del GeoJSON.
    mun = {}
    for r in d:
        dep = r['dep']; mn = r['mun']
        if dep == '88': continue
        key = dep + mn
        a = mun.setdefault(key, [0]*9)
        partes = sum((r.get(c,0) or 0) for c in CANDS)
        partes += sum((r.get(k,0) or 0) for k in ['votos_blanco','votos_nulos','votos_no_marcados'])
        tot = r.get('total_votos_urna',0) or 0
        a[0] += r.get('cepeda',0) or 0
        a[1] += r.get('abelardo',0) or 0
        a[2] += r.get('paloma',0) or 0
        a[3] += r.get('fajardo',0) or 0
        a[4] += max(0, tot - partes)
        a[5] += sum((r.get(c,0) or 0) for c in MENORES)
        a[6] += (r.get('votos_blanco',0) or 0)+(r.get('votos_nulos',0) or 0)+(r.get('votos_no_marcados',0) or 0)
        a[7] += tot
        a[8] += r.get('pot',0) or 0
    munpath = os.path.join(os.path.dirname(OUT), "mun1v.json")
    json.dump(mun, open(munpath,"w"), separators=(',',':'))
    print(f"escrito {munpath} ({os.path.getsize(munpath)} bytes · {len(mun)} muns)")

if __name__ == "__main__":
    main()
