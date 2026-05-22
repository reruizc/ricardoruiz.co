"""
Monte Carlo presidencial 1V Colombia 2026 — Capa 3 del modelo.

Toma la proyección puntual de Capa 2 (forecast-trend.json) y la convierte en
una DISTRIBUCIÓN de 1000 simulaciones, capturando cuatro fuentes de
incertidumbre:

  1) Sampling noise: error estándar binomial por candidato según el tamaño
     efectivo de muestra de las polls de los últimos 14 días.

  2) House effect uncertainty: la std_pp medida en Capa 1 — refleja que el
     de-bias no es perfecto (las firmas pueden tener variabilidad real).

  3) Trend uncertainty: 1.5σ de la tendencia local de Holt aplicada a los
     días restantes — refleja que la tendencia puede revertir.

  4) Shock late-campaign 2022 por ARQUETIPO de candidato. Es el diferencial
     del modelo: cada candidato recibe una perturbación tomada de N(μ, σ)
     calibrada contra el error real de las encuestas vs el resultado del
     29-may-2022 (Petro, Fico, Rodolfo, Fajardo).

Tras combinar las 4 fuentes, se renormaliza cada simulación a 100% para
preservar la correlación negativa entre candidatos.

Salida:
  Bases de datos/output_forecast/forecast-montecarlo.json

Cero dependencias: stdlib.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[2]
if ".claude" in ROOT.parts and "worktrees" in ROOT.parts:
    idx = ROOT.parts.index(".claude")
    ROOT = Path(*ROOT.parts[:idx])
DAT = ROOT / "Bases de datos"
TREND_PATH = DAT / "output_forecast" / "forecast-trend.json"
DET_PATH = DAT / "output_ponderador" / "ponderador-detalle.json"
OUT_DIR = DAT / "output_forecast"
OUT_PATH = OUT_DIR / "forecast-montecarlo.json"

# ---------- Constantes ----------
FECHA_ELECCION = date(2026, 5, 31)
HOY = date.today()

N_SIMS = 1000
SEED = 20260521  # fija para reproducibilidad
RECENT_WINDOW_DAYS = 14

# Umbral debajo del cual los candidatos se agrupan en "Otros" (fijo en cada
# simulación). Evita que candidatos en 0.1-1% acumulen ruido por clipping en 0
# y drenen proporción de los mayores en la renormalización.
OTROS_THRESHOLD_PCT = 1.5

# ---------- Arquetipos (2026) ----------
# Cada candidato presidencial se mapea a un arquetipo. El shock 2022 se
# calibra contra el arquetipo, no contra el candidato individual.
ARQUETIPOS = {
    "Cepeda":           "incumbent_left",       # Pacto Histórico, oficialismo
    "De la Espriella":  "opposition_outsider",  # abogado anti-sistema en posición de runner-up
    "Valencia":         "opposition_establishment",  # CD, derecha clásica
    "Fajardo":          "centrist",
    "Claudia López":    "centrist",
    "Botero":           "outsider_anti_sistema",  # empresario protesta, low single digits
    # El resto (<1%) se tratan como ruido sin shock significativo.
}

# Shock late-campaign calibrado contra el error 2022 (polls del 13-20 may
# vs resultado 29-may). bias = poll - real (positivo = polls sobreestiman).
# Aplicamos -bias en la simulación.
# Bias atenuado vs el bias bruto 2022 porque ya hicimos de-bias en Capa 1.
SHOCK_2022 = {
    "incumbent_left":             {"bias": +0.5, "std": 2.0},
    # Petro 2022: polls 40.0-45.1 (~41.5 prom) vs real 40.34 → bias bruto +1.2.
    # Atenuado a +0.5 porque ya de-biasamos por house effect.

    "opposition_establishment":   {"bias": +2.5, "std": 3.0},
    # Fico 2022: polls 20.1-30.8 (~26.8 prom) vs real 23.94 → bias bruto +2.9.
    # Atenuado mínimamente porque el sesgo era cross-firma (no solo house effect).

    "opposition_outsider":        {"bias": +0.0, "std": 4.0},
    # No hay análogo claro en 2022. Bias neutral con alta varianza para reflejar
    # que De la Espriella podría sorprender en cualquier dirección.

    "outsider_anti_sistema":      {"bias": -5.0, "std": 2.5},
    # Rodolfo 2022: polls 20.3-21.9 (~21.0 prom) vs real 28.17 → bias bruto -7.3.
    # Atenuado a -5 porque la fuerza del momentum dependerá de viralización.

    "centrist":                   {"bias": +0.5, "std": 1.5},
    # Fajardo 2022: polls 4.3-8.8 (~5.4 prom) vs real 4.18 → bias bruto +1.2.

    "minor":                      {"bias": +0.0, "std": 0.3},
    # Candidatos <1%, sin movimiento esperado significativo.
}

# Factor para escalar la trend_pp_day proyectada hacia adelante con incertidumbre
TREND_STD_FACTOR = 1.5


# ---------- Helpers ----------
def parse_date(s):
    return date.fromisoformat(s)


def get_archetype(cand: str) -> str:
    return ARQUETIPOS.get(cand, "minor")


def effective_n_recent(contribs, cand, max_days=RECENT_WINDOW_DAYS):
    """Sample size efectivo: Σ(n × q_firma) sobre polls recientes que incluyen cand."""
    n_eff = 0.0
    for c in contribs:
        if cand not in c["preds"]:
            continue
        if c["dias"] > max_days:
            continue
        n_eff += (c["n_muestra"] or 1) * c["q_firma"]
    return max(1.0, n_eff)


def weighted_he_std(house_effect, contribs, cand):
    """
    Std del house effect, ponderada por el peso relativo de cada firma en
    los últimos RECENT_WINDOW_DAYS. Mide la incertidumbre del de-bias.
    """
    num = 0.0
    den = 0.0
    seen = set()
    for c in contribs:
        firma = c["encuestadora"]
        if firma in seen:
            continue
        if cand not in c["preds"]:
            continue
        if c["dias"] > RECENT_WINDOW_DAYS:
            continue
        seen.add(firma)
        he_entry = house_effect.get(firma, {}).get(cand)
        if not he_entry:
            continue
        # peso por contribución de la firma
        weight = (c["n_muestra"] or 1) * c["q_firma"]
        std = he_entry.get("std_pp", 0)
        # firmas con n_polls=1 no tienen std confiable
        if he_entry.get("n_polls", 0) < 2:
            std = 2.0  # default uncertainty cuando no se puede medir
        num += weight * std
        den += weight
    if den == 0:
        return 2.0  # fallback amplio
    return num / den


def current_trend(serie_diaria, cand):
    """
    Última tendencia (pp/día) de Holt para el candidato.
    """
    s = serie_diaria.get(cand, [])
    if not s:
        return 0.0
    return s[-1]["holt_trend_pp_day"]


def quantile(sorted_vals, q):
    """q en [0, 1]."""
    if not sorted_vals:
        return 0
    idx = int(q * (len(sorted_vals) - 1))
    return sorted_vals[idx]


# ---------- Main ----------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)

    trend = json.loads(TREND_PATH.read_text(encoding="utf-8"))
    detalle = json.loads(DET_PATH.read_text(encoding="utf-8"))

    contribs = []
    for c in detalle["contribuciones"]:
        contribs.append({
            "encuesta_id": c["encuesta_id"],
            "encuestadora": c["encuestadora"],
            "fecha": parse_date(c["fecha_fin"]),
            "dias": c["dias"],
            "n_muestra": c["n_muestra"],
            "q_firma": c["q_firma"],
            "preds": c.get("predicciones_debiased") or c["predicciones"],
        })

    house_effect = detalle.get("house_effect", {})
    candidatos_all = trend["candidatos"]
    serie_diaria = trend["serie_diaria"]
    proyeccion = trend["proyeccion_31may"]
    dias_para_eleccion = (FECHA_ELECCION - HOY).days

    # Particionar: candidatos principales (>= OTROS_THRESHOLD_PCT) vs minor (→ Otros fijo).
    candidatos = []
    otros_minor = []  # candidatos absorbidos en "Otros"
    otros_base = 0.0
    for c in candidatos_all:
        b = proyeccion[c]["central_31may"]
        if b >= OTROS_THRESHOLD_PCT:
            candidatos.append(c)
        else:
            otros_minor.append({"cand": c, "base": b})
            otros_base += b

    # Pre-computar parámetros por candidato (constantes a través de las sims)
    params = {}
    for cand in candidatos:
        base = proyeccion[cand]["central_31may"]
        n_eff = effective_n_recent(contribs, cand)
        p = base / 100
        sampling_se_pp = math.sqrt(p * (1 - p) / n_eff) * 100

        he_std = weighted_he_std(house_effect, contribs, cand)

        trend_pp_day = current_trend(serie_diaria, cand)
        # Std de la tendencia proyectada: TREND_STD_FACTOR × |trend| × días + un floor
        trend_std_pp = max(0.5, TREND_STD_FACTOR * abs(trend_pp_day) * dias_para_eleccion)

        archetype = get_archetype(cand)
        shock = SHOCK_2022[archetype]

        params[cand] = {
            "base": base,
            "sampling_se_pp": round(sampling_se_pp, 3),
            "he_std_pp": round(he_std, 3),
            "trend_pp_day": trend_pp_day,
            "trend_std_pp": round(trend_std_pp, 3),
            "archetype": archetype,
            "shock_bias": shock["bias"],
            "shock_std": shock["std"],
        }

    # Ejecutar simulaciones. "Otros" (suma de candidatos < umbral) entra como
    # bucket fijo al renormalizar, pero no se perturba — no contamina varianza.
    results = defaultdict(list)
    otros_results = []
    for _sim in range(N_SIMS):
        perturbed = {}
        for cand in candidatos:
            p = params[cand]
            delta = (
                random.gauss(0, p["sampling_se_pp"])
                + random.gauss(0, p["he_std_pp"])
                + random.gauss(0, p["trend_std_pp"])
                + random.gauss(-p["shock_bias"], p["shock_std"])
            )
            perturbed[cand] = max(0.0, p["base"] + delta)

        # Total incluye Otros fijo, renormalizamos a 100%.
        total = sum(perturbed.values()) + otros_base
        if total > 0:
            factor = 100.0 / total
            for cand in perturbed:
                perturbed[cand] *= factor
            otros_sim = otros_base * factor
        else:
            otros_sim = otros_base

        for cand, v in perturbed.items():
            results[cand].append(v)
        otros_results.append(otros_sim)

    # Estadísticos por candidato
    stats = {}
    for cand, vals in results.items():
        vals_sorted = sorted(vals)
        stats[cand] = {
            "mean":   round(statistics.mean(vals), 2),
            "median": round(quantile(vals_sorted, 0.5), 2),
            "p5":     round(quantile(vals_sorted, 0.05), 2),
            "p25":    round(quantile(vals_sorted, 0.25), 2),
            "p75":    round(quantile(vals_sorted, 0.75), 2),
            "p95":    round(quantile(vals_sorted, 0.95), 2),
            "std":    round(statistics.pstdev(vals), 2),
        }

    # Probabilidades clave
    n = N_SIMS
    sims_matrix = list(zip(*[results[c] for c in candidatos]))  # [(sim_i_pct por cand), ...]

    p_cepeda_gana_1v = sum(1 for sim in sims_matrix if sim[candidatos.index("Cepeda")] > 50) / n

    # Para cada simulación: quién queda en 2do
    def winner_and_runner(sim):
        ranked = sorted(zip(candidatos, sim), key=lambda x: -x[1])
        return ranked[0][0], ranked[1][0]

    runner_counts = defaultdict(int)
    winner_counts = defaultdict(int)
    pairs = defaultdict(int)
    for sim in sims_matrix:
        w, r = winner_and_runner(sim)
        winner_counts[w] += 1
        runner_counts[r] += 1
        pairs[(w, r)] += 1

    p_winners = {c: round(winner_counts[c] / n, 4) for c in candidatos if winner_counts[c] > 0}
    p_runners = {c: round(runner_counts[c] / n, 4) for c in candidatos if runner_counts[c] > 0}
    p_pairs = {f"{w} vs {r}": round(v / n, 4) for (w, r), v in pairs.items() if v / n >= 0.01}

    # Probabilidades de podio para los favoritos (cómo se ubican)
    podio = {}
    top_cands = ["Cepeda", "De la Espriella", "Valencia", "Fajardo", "Claudia López", "Botero"]
    for cand in top_cands:
        if cand not in candidatos:
            continue
        idx = candidatos.index(cand)
        n_first = 0
        n_second = 0
        n_third_or_worse = 0
        for sim in sims_matrix:
            ranked = sorted(zip(candidatos, sim), key=lambda x: -x[1])
            for i, (c, _) in enumerate(ranked):
                if c == cand:
                    if i == 0:   n_first += 1
                    elif i == 1: n_second += 1
                    else:        n_third_or_worse += 1
                    break
        podio[cand] = {
            "p_primero": round(n_first / n, 4),
            "p_segundo": round(n_second / n, 4),
            "p_pasa_2v": round((n_first + n_second) / n, 4),
        }

    # Estadístico "Otros"
    otros_sorted = sorted(otros_results)
    otros_stats = {
        "base": round(otros_base, 2),
        "mean": round(statistics.mean(otros_results), 2),
        "median": round(quantile(otros_sorted, 0.5), 2),
        "p5": round(quantile(otros_sorted, 0.05), 2),
        "p95": round(quantile(otros_sorted, 0.95), 2),
        "candidatos_incluidos": [m["cand"] for m in otros_minor],
    }

    out = {
        "fecha_corte": HOY.isoformat(),
        "fecha_eleccion": FECHA_ELECCION.isoformat(),
        "dias_para_eleccion": dias_para_eleccion,
        "n_simulaciones": n,
        "seed": SEED,
        "candidatos_simulados": candidatos,
        "otros": otros_stats,
        "metodologia": (
            "Capa 3: Monte Carlo de %d simulaciones. Cuatro fuentes de "
            "incertidumbre: (1) sampling noise por candidato; (2) std del "
            "house effect medido en Capa 1; (3) std de la tendencia Holt × "
            "días faltantes; (4) shock arquetípico calibrado contra error "
            "polls vs resultado 29-may-2022. Renormalización a 100%% por "
            "simulación. Arquetipos: incumbent_left, opposition_establishment, "
            "opposition_outsider, outsider_anti_sistema, centrist, minor."
        ) % n,
        "arquetipos": ARQUETIPOS,
        "shock_2022": SHOCK_2022,
        "parametros_por_candidato": params,
        "estadisticos": stats,
        "probabilidades": {
            "cepeda_gana_1v": round(p_cepeda_gana_1v, 4),
            "ganador_1v": p_winners,
            "pasa_2do_lugar": p_runners,
            "pares_2v": p_pairs,
            "podio_top6": podio,
        },
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✓ {OUT_PATH}")
    print(f"  Simulaciones: {n}")
    print(f"  Días para elección: {dias_para_eleccion}")
    print()
    print("  Distribuciones top:")
    print(f"  {'cand':20s} {'mean':>6s} {'p5':>6s} {'p25':>6s} {'p50':>6s} {'p75':>6s} {'p95':>6s} {'std':>5s}")
    print("  " + "-" * 65)
    for cand in candidatos[:8]:
        s = stats[cand]
        print(f"  {cand:20s} {s['mean']:>6.2f} {s['p5']:>6.2f} {s['p25']:>6.2f} {s['median']:>6.2f} {s['p75']:>6.2f} {s['p95']:>6.2f} {s['std']:>5.2f}")
    print()
    print(f"  P(Cepeda > 50% en 1V) = {p_cepeda_gana_1v:.1%}")
    print(f"  P(pasa a 2da vuelta):")
    for cand in top_cands:
        if cand in podio:
            print(f"    {cand:20s} {podio[cand]['p_pasa_2v']:>6.1%}  (P primero: {podio[cand]['p_primero']:>5.1%}, P segundo: {podio[cand]['p_segundo']:>5.1%})")
    print()
    print(f"  Pares 2da vuelta más probables:")
    for k, v in sorted(p_pairs.items(), key=lambda x: -x[1])[:5]:
        print(f"    {k:40s} {v:.1%}")


if __name__ == "__main__":
    main()
