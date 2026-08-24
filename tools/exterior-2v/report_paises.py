#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detalle por país + validación contra el master + trasvase exterior."""
import json, os

J = "/Users/ricardoruiz/ricardoruiz.co/tools/exterior-2v/exterior_1v_2v.json"
MASTER = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_2v/master_unificado_puesto.json"
d = json.load(open(J))
P = d["paises"]; T = d["totales"]

def pct(x,t): return 100*x/t if t else 0

# ---------- validación contra master (dep 88) ----------
m = json.load(open(MASTER))
ext = [r for r in m if r["dep"]=="88"]
mc1 = sum(r["v1"]["cepeda"] for r in ext); ma1 = sum(r["v1"]["abelardo"] for r in ext)
mc2 = sum(r["cep2"] for r in ext);         ma2 = sum(r["abe2"] for r in ext)
print("VALIDACIÓN master (dep 88) vs preconteo crudo")
print(f"  1V Cepeda   master {mc1:>9,} | crudo {T['1v']['cepeda']:>9,}  Δ {mc1-T['1v']['cepeda']:+,}")
print(f"  1V Abelardo master {ma1:>9,} | crudo {T['1v']['abelardo']:>9,}  Δ {ma1-T['1v']['abelardo']:+,}")
print(f"  2V Cepeda   master {mc2:>9,} | crudo {T['2v']['cepeda']:>9,}  Δ {mc2-T['2v']['cepeda']:+,}")
print(f"  2V Abelardo master {ma2:>9,} | crudo {T['2v']['abelardo']:>9,}  Δ {ma2-T['2v']['abelardo']:+,}")
print(f"  (puestos master exterior: {len(ext)})")

# ---------- top países por votos 2V ----------
print("\n" + "="*94)
print("TOP PAÍSES POR VOTOS 2V  ·  cara a cara Cepeda vs Abelardo  ·  shift de margen 1V→2V")
print("="*94)
print(f"{'País':<22}{'urna1V':>8}{'urna2V':>8}{'Δturn':>7} | {'Cep1V%':>7}{'Cep2V%':>7}{'ΔCep':>6} | {'gana 2V':>9}{'marg2V':>8}")
print("-"*94)
def row(p):
    cc1,ca1 = p["cep1"],p["abe1"]; cc2,ca2 = p["cep2"],p["abe2"]
    c1 = pct(cc1,cc1+ca1) if (cc1+ca1) else 0
    c2 = pct(cc2,cc2+ca2) if (cc2+ca2) else 0
    gana = "Cepeda" if cc2>ca2 else "Abelardo"
    marg = pct(max(cc2,ca2),cc2+ca2)-pct(min(cc2,ca2),cc2+ca2) if (cc2+ca2) else 0
    u1,u2 = p["v1"]["urna"], p["v2"]["urna"]
    dturn = pct(u2-u1,u1) if u1 else 0
    return (p["pais"],u1,u2,dturn,c1,c2,c2-c1,gana,marg,cc2+ca2)
rows = [row(p) for p in P]
for r in sorted(rows, key=lambda x:-x[2])[:25]:
    nm,u1,u2,dt,c1,c2,dc,g,mg,_ = r
    print(f"{nm:<22}{u1:>8,}{u2:>8,}{dt:>+6.0f}% | {c1:>6.1f}%{c2:>6.1f}%{dc:>+5.1f} | {g:>9}{mg:>6.0f}pp")

# ---------- ¿dónde ganó Cepeda en 2V? ----------
print("\n--- Países donde CEPEDA ganó la 2V (cep2 > abe2) ---")
win = [r for r in rows if r[7]=="Cepeda"]
win.sort(key=lambda x:-x[9])
if win:
    for r in win:
        print(f"  {r[0]:<22} Cep {r[5]:.1f}%  ({r[9]:,} válidos 2V)")
else:
    print("  NINGUNO.")

# ---------- mejores y peores para Cepeda (con volumen) ----------
big = [r for r in rows if r[9] >= 1000]   # >=1000 válidos 2V
print("\n--- Mejor Cepeda 2V (países con >=1.000 válidos) ---")
for r in sorted(big, key=lambda x:-x[5])[:8]:
    print(f"  {r[0]:<22} Cep {r[5]:.1f}%   (1V {r[4]:.1f}% → Δ{r[6]:+.1f})   {r[9]:,} válidos")
print("--- Peor Cepeda 2V (mayor feudo Abelardo) ---")
for r in sorted(big, key=lambda x:x[5])[:8]:
    print(f"  {r[0]:<22} Cep {r[5]:.1f}%   (1V {r[4]:.1f}% → Δ{r[6]:+.1f})   {r[9]:,} válidos")

# ---------- trasvase agregado exterior ----------
print("\n" + "="*60)
print("TRASVASE AGREGADO · EXTERIOR (cómo crecieron 1V→2V)")
print("="*60)
t1,t2 = T["1v"],T["2v"]
# bloques 1V
izq = t1["cepeda"]+t1["roy"]+t1["caicedo"]+t1["murillo"]
centro = t1["fajardo"]+t1["claudia"]
der = t1["abelardo"]+t1["paloma"]+t1["botero"]+t1["miguel_uribe"]+t1["macollins"]+t1["matamoros"]+t1["lizcano"]
print(f"  1V bloque izq (Cep+Roy+Caicedo+Murillo): {izq:,}")
print(f"  1V bloque centro (Fajardo+Claudia):      {centro:,}")
print(f"  1V bloque der (Abe+Paloma+menores):      {der:,}")
print(f"  Cepeda: 1V {t1['cepeda']:,} → 2V {t2['cepeda']:,}  (+{t2['cepeda']-t1['cepeda']:,})")
print(f"  Abelardo: 1V {t1['abelardo']:,} → 2V {t2['abelardo']:,}  (+{t2['abelardo']-t1['abelardo']:,})")
nuevos = (t2['cepeda']+t2['abelardo']) - (t1['cepeda']+t1['abelardo']+t1['paloma']+t1['fajardo']+t1['claudia']+t1['botero']+t1['lizcano']+t1['miguel_uribe']+t1['macollins']+t1['roy']+t1['caicedo']+t1['murillo']+t1['matamoros'])
print(f"  Crecimiento neto del campo (válidos 2V−1V): {(t2['cepeda']+t2['abelardo'])-559912:+,}")
