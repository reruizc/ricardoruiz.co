#!/usr/bin/env python3
"""Composición del voto 2026 por SEXO x EDAD (Cepeda/Abelardo/Paloma/Otros),
que suma 100% por grupo. NO hay género por mesa en 2026, así que se combinan
dos piezas robustas:
  (1) estructura por edad 2026 (EI por edad, todos los votantes) — robusta.
  (2) brecha de género por edad medida mesa a mesa en 2022 — robusta, y cuya
      DIRECCIÓN confirma la encuesta AtlasIntel 2026.
Modelo: se desplaza la fracción de Cepeda según la brecha de género por edad
(gL) y se redistribuye proporcionalmente al resto (Abelardo, Paloma, Otros).
Salida: output_mujeres_1v/comp-2026-sexedad.json
"""
import json
import os
import sys

import numpy as np

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
sys.path.insert(0, os.path.abspath(EDAD))
from fit_ei import load_year, fit_national  # noqa

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "Bases de datos", "output_mujeres_1v")
NIV = json.load(open(os.path.join(OUT, "genero-edad-niveles.json")))["izq_niveles"]

AGE = ["18-35", "36-60", "61+"]
COLLAPSE3 = [[0, 1], [2, 3], [4]]
W_MUJ = 0.541   # share de mujeres entre votantes
# gap de género (mujer - hombre) en voto de izquierda por edad (2022, robusto)
gL = {a: round(NIV["Mujeres"][a] - NIV["Hombres"][a], 2) for a in AGE}

# 2026 share por candidato dentro de cada banda de edad (todos los votantes)
meta, W5, Y6, T = load_year(2026)
W3 = np.stack([W5[:, idx].sum(1) for idx in COLLAPSE3], axis=1)
W3 = W3 / W3.sum(1, keepdims=True)
B, _, _ = fit_national(meta, W3, Y6, T)   # 6 cand x 3 edades
CANDS = ["cepeda", "abelardo", "paloma", "fajardo26", "blanco", "resto"]
ci = CANDS.index("cepeda")

res = {"Mujeres": {}, "Hombres": {}}
for a_i, a in enumerate(AGE):
    base = {c: B[CANDS.index(c), a_i] * 100 for c in CANDS}
    cep = base["cepeda"]
    rest = {c: base[c] for c in CANDS if c != "cepeda"}
    rsum = sum(rest.values())
    for sexo, sign in (("Mujeres", 1 - W_MUJ), ("Hombres", -W_MUJ)):
        dcep = sign * gL[a]                       # cambio en Cepeda
        cep_s = max(cep + dcep, 0.5)
        # redistribuir -dcep al resto proporcional a su tamaño
        rest_s = {c: rest[c] * (1 - dcep / max(rsum, 1e-6)) for c in rest}
        # agrupar: Cepeda / Abelardo / Paloma / Otros
        otros = rest_s["fajardo26"] + rest_s["blanco"] + rest_s["resto"]
        comp = {"Cepeda": cep_s, "Abelardo": rest_s["abelardo"],
                "Paloma": rest_s["paloma"], "Otros": otros}
        tot = sum(comp.values())
        res[sexo][a] = {k: round(v / tot * 100, 1) for k, v in comp.items()}

print("Composición 2026 por sexo x edad (% dentro del grupo, suma 100):")
for sexo in ("Mujeres", "Hombres"):
    print(f"  {sexo}:")
    for a in AGE:
        d = res[sexo][a]
        print(f"    {a:6s} Cep {d['Cepeda']:4.0f} · Abe {d['Abelardo']:4.0f} · "
              f"Pal {d['Paloma']:4.0f} · Otros {d['Otros']:4.0f}")

# agregado NACIONAL por sexo (pondera bandas de edad por votantes)
agew = np.array([(W3[:, i] * T).sum() for i in range(3)])
agew = agew / agew.sum()
nacional = {}
for sexo in ("Mujeres", "Hombres"):
    acc = {k: 0.0 for k in ("Cepeda", "Abelardo", "Paloma", "Otros")}
    for i, a in enumerate(AGE):
        for k in acc:
            acc[k] += agew[i] * res[sexo][a][k]
    s = sum(acc.values())
    nacional[sexo] = {k: round(v / s * 100, 1) for k, v in acc.items()}
print("\nNacional por sexo (1ª vuelta, suma 100):")
for sexo in ("Mujeres", "Hombres"):
    d = nacional[sexo]
    print(f"  {sexo}: Cep {d['Cepeda']:.0f} · Abe {d['Abelardo']:.0f} · "
          f"Pal {d['Paloma']:.0f} · Otros {d['Otros']:.0f}")
json.dump({"comp": res, "nacional": nacional, "gL": gL},
          open(os.path.join(OUT, "comp-2026-sexedad.json"), "w"),
          ensure_ascii=False, indent=1)
print("-> comp-2026-sexedad.json")
