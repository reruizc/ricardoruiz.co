#!/usr/bin/env python3
"""Descriptivos del voto femenino 1V-2026 (sin EI, salvo descomposición):

  1. Peso nacional: votantes mujeres vs hombres (proyectado), % del censo,
     brecha de participación.
  2. Participación por sexo por DEPARTAMENTO: votantes proyectados / censo
     observado (COMUNAS_DATA). Dónde salen más las mujeres vs los hombres.
  3. Share de mujeres entre los VOTANTES por ciudad/depto (dónde votan
     proporcionalmente más mujeres).
  4. Descomposición composición vs preferencia del escenario "solo mujeres"
     usando las betas etarias robustas (ei-final.csv del pipeline de edad):
     si solo cambiara la ESTRUCTURA de edad (mujeres más viejas), ¿hacia
     dónde iría? -> aísla el canal demográfico del de preferencia.
"""
import csv
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "..", "Bases de datos")
OUT = os.path.join(BASE, "output_mujeres_1v")
EOUT = os.path.join(BASE, "output_edad_1v")

HCOLS = [f"H{b}" for b in range(10)]
MCOLS = [f"M{b}" for b in range(10)]

DEPNAME = {  # cod RNEC -> nombre (de build_blocs_depto si hace falta, aquí lite)
}


def load_censo_sexo():
    """COMUNAS_DATA -> censo mujeres/hombres por puesto (pcode) y por depto."""
    pc, dep = {}, {}
    with open(os.path.join(BASE, "COMUNAS_DATA.csv"), encoding="utf-8-sig") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            dd = row["dd"].zfill(2); mm = row["mm"].zfill(3)
            zz = row["zz"].zfill(2); pp = row["pp"].zfill(2)
            key = f"{dd}-{mm}-{zz}-{pp}"
            m = int(float(row["mujeres"] or 0)); h = int(float(row["hombres"] or 0))
            pc[key] = (m, h)
            d = dep.setdefault(dd, [0, 0, row["departamento"]])
            d[0] += m; d[1] += h
    return pc, dep


def main():
    J = {}
    w = pd.read_csv(os.path.join(OUT, "w26-gen-puesto.csv"), dtype={"pcode": str})
    w["muj"] = w[MCOLS].sum(axis=1)
    w["hom"] = w[HCOLS].sum(axis=1)
    w["dep"] = w["pcode"].str[:2]
    w["mun"] = w["pcode"].str[:6]

    pc_cens, dep_cens = load_censo_sexo()

    # ---- 1. peso nacional ----
    Vm, Vh = w["muj"].sum(), w["hom"].sum()
    Cm = sum(v[0] for v in pc_cens.values())
    Ch = sum(v[1] for v in pc_cens.values())
    tw = Vm / Cm * 100; th = Vh / Ch * 100
    J["peso"] = dict(
        votantes_muj=int(round(Vm)), votantes_hom=int(round(Vh)),
        share_votantes_muj=round(Vm/(Vm+Vh)*100, 2),
        censo_muj=Cm, censo_hom=Ch, share_censo_muj=round(Cm/(Cm+Ch)*100, 2),
        participacion_muj=round(tw, 2), participacion_hom=round(th, 2),
        brecha_participacion_pp=round(tw-th, 2))
    print("== 1. PESO NACIONAL ==")
    print(f"  votantes mujeres {Vm:,.0f} ({Vm/(Vm+Vh)*100:.1f}% de votantes) · "
          f"hombres {Vh:,.0f}")
    print(f"  censo mujeres {Cm:,} ({Cm/(Cm+Ch)*100:.1f}% del censo) · hombres {Ch:,}")
    print(f"  participación mujeres {tw:.1f}% vs hombres {th:.1f}% · "
          f"brecha {tw-th:+.1f} pp")

    # ---- 2. participación por sexo por depto ----
    print("\n== 2. PARTICIPACIÓN POR SEXO · DEPTO (brecha M-H) ==")
    rows = []
    wm = w.groupby("dep")[["muj", "hom"]].sum()
    for dep, (cm, ch, name) in dep_cens.items():
        if dep not in wm.index or cm == 0 or ch == 0:
            continue
        vm, vh = wm.loc[dep, "muj"], wm.loc[dep, "hom"]
        tm, tH = vm/cm*100, vh/ch*100
        rows.append(dict(dep=dep, name=name, part_muj=round(tm, 1),
                         part_hom=round(tH, 1), brecha=round(tm-tH, 1),
                         share_votantes_muj=round(vm/(vm+vh)*100, 1)))
    rows.sort(key=lambda r: -r["brecha"])
    J["participacion_depto"] = rows
    for r in rows[:8] + rows[-4:]:
        print(f"  {r['name'][:18]:18s} M {r['part_muj']:5.1f}% H {r['part_hom']:5.1f}% "
              f"brecha {r['brecha']:+5.1f}  (mujeres={r['share_votantes_muj']}% de votantes)")

    # ---- 3. share de mujeres entre votantes por ciudad ----
    CIUDADES = {"Bogotá": "16-001", "Medellín": "01-001", "Cali": "31-001",
                "Barranquilla": "08-001", "Cartagena": "13-001",
                "Cúcuta": "54-001", "Bucaramanga": "68-001", "Ibagué": "73-001",
                "Pereira": "66-001", "Manizales": "17-001", "Pasto": "52-001",
                "Villavicencio": "50-001", "Montería": "23-001",
                "Soledad": "08-758", "Soacha": "25-754", "Neiva": "41-001",
                "Armenia": "63-001", "Popayán": "19-001", "Valledupar": "20-001",
                "Sincelejo": "70-001", "Sta Marta": "47-001"}
    # ojo: w usa códigos RNEC; CIUDADES arriba mezcla. Resolver por mun real en w.
    # Construyo share por mun y mapeo por nombre de depto+capital vía top-mun.
    wm2 = w.groupby("mun")[["muj", "hom"]].sum()
    wm2["share_muj"] = wm2["muj"]/(wm2["muj"]+wm2["hom"])*100
    wm2["tot"] = wm2["muj"]+wm2["hom"]
    # ciudades grandes = muns con más votantes
    big = wm2[wm2["tot"] >= 60000].sort_values("share_muj", ascending=False)
    print("\n== 3. SHARE DE MUJERES ENTRE VOTANTES · muns grandes (>=60k votantes) ==")
    rows3 = []
    for mun, r in big.iterrows():
        rows3.append(dict(mun=mun, share_muj=round(r["share_muj"], 2),
                          votantes=int(r["tot"])))
    for r in rows3[:12]:
        print(f"  {r['mun']}  {r['share_muj']:.1f}%  ({r['votantes']:,} votantes)")
    J["share_muj_muns_grandes"] = rows3

    # ---- 4. descomposición composición vs preferencia ----
    # betas etarias robustas 2026 (5 grupos) de ei-final.csv
    ei = pd.read_csv(os.path.join(EOUT, "ei-final.csv"))
    ei26 = ei[ei["year"] == 2026]
    GROUPS5 = ["18-25", "26-35", "36-45", "46-60", "61+"]
    cand_order = ["Cepeda", "Abelardo", "Paloma", "Fajardo", "Blanco", "Otros*"]
    beta = {}
    for c in cand_order:
        sub = ei26[ei26["cand"] == c].set_index("grupo")
        beta[c] = np.array([sub.loc[g, "beta"] if g in sub.index else 0 for g in GROUPS5])
    # composición etaria de votantes M y H (5 grupos) desde w26-gen
    B5 = [[0, 1], [2, 3], [4, 5], [6, 7, 8], [9]]
    M = w[MCOLS].values.sum(axis=0)   # 10 bandas
    H = w[HCOLS].values.sum(axis=0)
    M5 = np.array([M[idx].sum() for idx in B5]); M5 = M5/M5.sum()
    H5 = np.array([H[idx].sum() for idx in B5]); H5 = H5/H5.sum()
    allv = M+H; A5 = np.array([allv[idx].sum() for idx in B5]); A5 = A5/A5.sum()
    print("\n== 4. DESCOMPOSICIÓN (canal composición de edad) ==")
    print("  composición etaria de votantes (5 grupos):")
    print("    " + "  ".join(f"{g}" for g in GROUPS5))
    print("    M: " + "  ".join(f"{x*100:.0f}" for x in M5))
    print("    H: " + "  ".join(f"{x*100:.0f}" for x in H5))
    comp = {}
    print("  resultado SOLO por estructura de edad (misma preferencia por banda):")
    for c in cand_order:
        rm = float(beta[c] @ M5)*100
        rh = float(beta[c] @ H5)*100
        ra = float(beta[c] @ A5)*100
        comp[c] = dict(muj_solo_edad=round(rm, 1), hom_solo_edad=round(rh, 1),
                       real_implicito=round(ra, 1))
        print(f"    {c:9s} M {rm:5.1f}  H {rh:5.1f}  (canal edad: brecha {rm-rh:+.1f})")
    J["descomposicion_edad"] = comp
    J["comp_edad_votantes"] = dict(muj={GROUPS5[i]: round(M5[i]*100, 1) for i in range(5)},
                                   hom={GROUPS5[i]: round(H5[i]*100, 1) for i in range(5)})

    with open(os.path.join(OUT, "mujeres-descriptivos.json"), "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print("\nmujeres-descriptivos.json escrito.")


if __name__ == "__main__":
    main()
