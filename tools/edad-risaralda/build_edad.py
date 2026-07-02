#!/usr/bin/env python3
"""Ensambla el resultado edad×bloque alternativo para Risaralda, 3 elecciones:
  2019 territorial (gobernación) — edad REAL 2019.
  2023 territorial (gobernación) — edad 2019 × factor DANE 2019->2023.
  Cámara 2026                    — edad 2022 × factor DANE 2022->2026.
Scopes: Risaralda + Pereira/Dosquebradas/Santa Rosa (muns grandes).
Salida: Bases de datos/output_edad_risaralda/edad-resultados.json
"""
import sys, os, json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,"/Users/ricardoruiz/ricardoruiz.co/tools/edad-1v-2026")
import numpy as np
from fit import load_age, vote_puestos, ei_bloc, GN, GROUPS
from probe_viabilidad import load_dane

OUT="Bases de datos/output_edad_risaralda"
SCOPES=[("RISARALDA",None),("Pereira","1"),("Dosquebradas","25"),("Santa Rosa de Cabal","86")]

def dane_factors():
    dane=load_dane(years=(2019,2022,2023,2026))
    k=[x for x in dane if "RISARALD" in x][0]
    p={y:np.array(dane[k][y]) for y in (2019,2022,2023,2026)}
    def grp_fac(a,b):
        return {g:(sum(p[b][i] for i in GROUPS[g])/sum(p[a][i] for i in GROUPS[g])) for g in GN}
    return grp_fac(2019,2023), grp_fac(2022,2026)

def project_age(agePuestos, fac):
    """Reescala los conteos por grupo con el factor de envejecimiento."""
    out={}
    for pk,v in agePuestos.items():
        g=[v["g"][i]*fac[GN[i]] for i in range(len(GN))]
        out[pk]={"g":g,"suf":sum(g)}
    return out

def run(agePuestos, votePuestos):
    res={}
    for nombre,mf in SCOPES:
        r=ei_bloc(agePuestos, votePuestos, mf)
        if r: r["nombre"]=nombre; res[mf or "DEP"]=r
    return res

def main():
    f1923,f2226=dane_factors()
    print("factor 2019->2023:",{g:round(v,3) for g,v in f1923.items()})
    print("factor 2022->2026:",{g:round(v,3) for g,v in f2226.items()})
    age19=load_age("edad-2019-local.json"); age22=load_age("edad-2022-congreso.json")
    v19=vote_puestos("risaralda-2019-puestos.json","gobernacion")
    v23=vote_puestos("risaralda-2023-puestos.json","gobernacion")
    vcam=vote_puestos("risaralda-camara-2026-puestos.json",None)

    out={"generated": None, "grupos":GN,
         "def_bloque":"Verde + Pacto + izquierda histórica (Polo, Colombia Humana, UP, MAIS, ADA/Frente Amplio, Comunes)",
         "elecciones":{}}
    out["elecciones"]["2019"]={"label":"Territorial 2019 · Gobernación","corp":"gobernacion","proy":False,
        "scopes":run(age19, v19)}
    out["elecciones"]["2023"]={"label":"Territorial 2023 · Gobernación","corp":"gobernacion","proy":True,
        "nota":"Composición etaria proyectada desde 2019 (mismo tipo de elección) con crecimiento DANE 2019→2023.",
        "scopes":run(project_age(age19,f1923), v23)}
    out["elecciones"]["camara"]={"label":"Cámara 2026","corp":None,"proy":True,
        "nota":"Composición etaria proyectada desde el Congreso 2022 (mismo tipo) con crecimiento DANE 2022→2026.",
        "scopes":run(project_age(age22,f2226), vcam)}
    json.dump(out, open(os.path.join(OUT,"edad-resultados.json"),"w"))

    # reporte
    for e,ed in out["elecciones"].items():
        print(f"\n### {ed['label']} {'(proyectado)' if ed['proy'] else '(edad real)'}")
        for mf,r in ed["scopes"].items():
            print(f"  {r['nombre']:20} n={r['n_puestos']:3}  alt {r['alt_pct_scope']}%")
            for gn,g in r["grupos"].items():
                print(f"     {gn:6} alt {g['beta']:5.1f}%  [IC {g['lo']:.0f}–{g['hi']:.0f}]")

if __name__=="__main__": main()
