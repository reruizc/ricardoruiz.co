#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest.py — ¿el score condicionado predice mejor que la tasa global?

Hito 2 del módulo `tutela-analiza`. Es la validación que vuelve defendible
mostrarle un porcentaje al usuario: no basta con que el número salga de datos
reales, hay que demostrar que PREDICE.

Diseño
------
    Entrena con 2023-2024  ->  predice 2025  (fuera de muestra, temporal)

Compara dos estimadores sobre los mismos casos de 2025:
    (a) CONDICIONADO — tasa de la celda pretensión × depto × SEP (con la misma
        cascada y MIN_N de build_tasas.py)
    (b) BASE — una sola tasa global de salud para todo el mundo

Métricas
--------
    Brier score  (error cuadrático medio; más bajo = mejor). Con datos agregados
                 se calcula exacto: una celda con n casos, k favorables y
                 predicción p aporta  k(1-p)² + (n-k)p².
    Skill        1 - Brier(cond)/Brier(base). >0 = el condicionamiento aporta.
    Calibración  predicho vs observado por deciles: ¿cuando decimos 94%, pasa 94%?
    MAE          error absoluto medio ponderado por celda.

Si el skill es ~0, el honesto es NO mostrar un % por caso y quedarse con la
tasa por pretensión: significaría que depto y SEP no agregan información.

Uso
---
    python3 tools/tutela-analiza/backtest.py
    (requiere el caché crudo que deja build_tasas.py)
"""

import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT, "Bases de datos", "tutelas-salud", "raw")
RESOURCE = "g3ma-7zce"

TRAIN = ["2023", "2024"]
TEST = "2025"
FAVORABLES = {"Concede", "Concede parcial", "Hecho superado"}
MIN_N = 100


def log(m):
    print(m, flush=True)


def cargar(anio):
    p = os.path.join(RAW_DIR, f"{RESOURCE}-salud-{anio}.json")
    if not os.path.exists(p):
        raise SystemExit(f"Falta el caché {p}. Corre antes build_tasas.py")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def acumular(anios):
    """-> dict de acumuladores {clave: {decision: n}} en varios niveles."""
    fino = defaultdict(lambda: defaultdict(int))
    pd_ = defaultdict(lambda: defaultdict(int))
    ps = defaultdict(lambda: defaultdict(int))
    pr = defaultdict(lambda: defaultdict(int))
    gl = defaultdict(int)
    for a in anios:
        for r in cargar(a):
            p = (r.get("pretension") or "").strip()
            d = (r.get("departamento") or "").strip()
            s = (r.get("sep") or "").strip()
            dec = (r.get("decision_1") or "").strip()
            try:
                n = int(r.get("n") or 0)
            except (TypeError, ValueError):
                continue
            if not p or not dec or n <= 0:
                continue
            fino[(p, d, s)][dec] += n
            pd_[(p, d)][dec] += n
            ps[(p, s)][dec] += n
            pr[p][dec] += n
            gl[dec] += n
    return fino, pd_, ps, pr, gl


def tasa(desg):
    n = sum(desg.values())
    if n == 0:
        return None, 0
    k = sum(v for d, v in desg.items() if d in FAVORABLES)
    return k / n, n


def predecir(clave, acc):
    """Tasa condicionada con cascada. -> (p, nivel)"""
    fino, pd_, ps, pr, gl = acc
    p, d, s = clave
    for cand, nivel in (
        (fino.get((p, d, s)), "pretension+depto+sep"),
        (pd_.get((p, d)), "pretension+depto"),
        (ps.get((p, s)), "pretension+sep"),
        (pr.get(p), "pretension"),
    ):
        if cand:
            t, n = tasa(cand)
            if t is not None and n >= MIN_N:
                return t, nivel
    t, _ = tasa(gl)
    return (t if t is not None else 0.0), "nacional"


def main():
    log(f"Entrenando con {'+'.join(TRAIN)} · probando en {TEST}\n")
    acc = acumular(TRAIN)
    base_p, base_n = tasa(acc[4])
    log(f"  Tasa BASE de entrenamiento: {base_p:.4f}  (n={base_n:,})\n")

    # Casos reales de 2025, agregados por celda
    real = defaultdict(lambda: defaultdict(int))
    for r in cargar(TEST):
        p = (r.get("pretension") or "").strip()
        d = (r.get("departamento") or "").strip()
        s = (r.get("sep") or "").strip()
        dec = (r.get("decision_1") or "").strip()
        try:
            n = int(r.get("n") or 0)
        except (TypeError, ValueError):
            continue
        if p and dec and n > 0:
            real[(p, d, s)][dec] += n

    tot = brier_c = brier_b = mae_num = 0
    niveles = defaultdict(int)
    bins = defaultdict(lambda: [0, 0, 0.0])  # decil -> [n, favorables, suma_pred]

    for clave, desg in real.items():
        n = sum(desg.values())
        k = sum(v for d, v in desg.items() if d in FAVORABLES)
        pc, nivel = predecir(clave, acc)
        niveles[nivel] += n
        # Brier exacto sobre casos individuales
        brier_c += k * (1 - pc) ** 2 + (n - k) * pc ** 2
        brier_b += k * (1 - base_p) ** 2 + (n - k) * base_p ** 2
        mae_num += abs((k / n) - pc) * n
        tot += n
        b = bins[min(9, int(pc * 10))]
        b[0] += n
        b[1] += k
        b[2] += pc * n

    bc, bb = brier_c / tot, brier_b / tot
    skill = 1 - bc / bb if bb else 0.0

    log(f"  Casos evaluados en {TEST}: {tot:,}")
    log(f"  Tasa observada {TEST}: {sum(sum(v for d,v in x.items() if d in FAVORABLES) for x in real.values())/tot:.4f}\n")
    log("  " + "-" * 56)
    log(f"  Brier CONDICIONADO : {bc:.5f}")
    log(f"  Brier BASE (global): {bb:.5f}")
    log(f"  Skill score        : {skill:+.4f}   ({skill*100:+.2f}% de mejora)")
    log(f"  MAE ponderado      : {mae_num/tot:.4f}")
    log("  " + "-" * 56 + "\n")

    log("  Calibración (¿lo que predecimos es lo que pasa?):")
    log(f"    {'predicho':>10} {'observado':>10} {'casos':>10}  {'gap':>7}")
    for d in sorted(bins):
        n, k, sp = bins[d]
        if n < 500:
            continue
        pred, obs = sp / n, k / n
        flag = "  <-- desvío" if abs(pred - obs) > 0.03 else ""
        log(f"    {pred:>9.1%} {obs:>10.1%} {n:>10,}  {pred-obs:>+7.1%}{flag}")

    log("\n  Nivel de estrato usado (por volumen de casos):")
    for niv, n in sorted(niveles.items(), key=lambda kv: -kv[1]):
        log(f"    {niv:<24} {n:>9,}  ({n/tot:.1%})")

    log("\n  " + "=" * 56)
    if skill > 0.02:
        log("  VEREDICTO: el condicionamiento aporta. Score por caso defendible.")
    elif skill > 0:
        log("  VEREDICTO: aporta poco. Defendible, pero el % variará poco entre")
        log("             usuarios; considerar mostrar la tasa por pretensión.")
    else:
        log("  VEREDICTO: NO aporta. Lo honesto es NO mostrar un % por caso y")
        log("             quedarse con la tasa por pretensión, citada.")
    log("  " + "=" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
