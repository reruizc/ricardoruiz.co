"""
Forecast presidencial 1V Colombia 2026 — Capa 2 del modelo.

Toma los polls con de-bias por house effect (output de ponderador.py) y
produce:
  · una serie diaria interpolada (ensemble blended kernel smoothing)
  · una proyección de tendencia (Holt double exponential smoothing en log-odds)
  · un valor puntual proyectado al 31-may por candidato

La Capa 3 (Monte Carlo con shock 2022) se construye encima de este output.

Entradas:
  Bases de datos/output_ponderador/ponderador-detalle.json
    → contribuciones[].{fecha_fin, n_muestra, q_firma, predicciones_debiased}

Salida:
  Bases de datos/output_forecast/forecast-trend.json
    {
      fecha_corte, fecha_eleccion,
      candidatos: [...],
      serie_diaria: { cand: [{date, n_polls, kswa, holt_level, holt_trend}, ...] },
      proyeccion_31may: { cand: {kswa, holt, central}, ... },
      parametros: { kernel_sigma_days, kernel_window_days, holt_alpha, holt_beta }
    }

Cero dependencias: stdlib pura.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[2]
if ".claude" in ROOT.parts and "worktrees" in ROOT.parts:
    idx = ROOT.parts.index(".claude")
    ROOT = Path(*ROOT.parts[:idx])
DAT = ROOT / "Bases de datos"
DET_PATH = DAT / "output_ponderador" / "ponderador-detalle.json"
OUT_DIR = DAT / "output_forecast"
OUT_PATH = OUT_DIR / "forecast-trend.json"

# ---------- Constantes ----------
FECHA_ELECCION = date(2026, 5, 31)
HOY = date.today()

# Kernel smoothing
KERNEL_SIGMA_DAYS = 7         # ancho del kernel gaussiano
KERNEL_WINDOW_DAYS = 14       # corte estricto (no usar polls más allá de ±14d)

# Holt's double exponential smoothing
HOLT_ALPHA = 0.35             # level smoothing
HOLT_BETA = 0.15              # trend smoothing

# Candidatos a proyectar (los que tienen >= MIN_POLLS_FOR_FORECAST observaciones)
MIN_POLLS_FOR_FORECAST = 4

# Para logit transform — cota para evitar log(0) o log(∞)
LOGIT_EPS = 0.001


# ---------- Helpers ----------
def parse_date(s):
    return date.fromisoformat(s)


def logit(p):
    """log-odds. p en (0,1)."""
    p = max(LOGIT_EPS, min(1 - LOGIT_EPS, p))
    return math.log(p / (1 - p))


def inv_logit(x):
    """Inverso de logit."""
    return 1.0 / (1.0 + math.exp(-x))


# ---------- Pipeline ----------
def load_contribuciones():
    """Devuelve lista de dicts con fecha_fin (date), peso, predicciones_debiased."""
    raw = json.loads(DET_PATH.read_text(encoding="utf-8"))
    out = []
    for c in raw["contribuciones"]:
        out.append({
            "encuesta_id": c["encuesta_id"],
            "encuestadora": c["encuestadora"],
            "fecha": parse_date(c["fecha_fin"]),
            "n_muestra": c["n_muestra"],
            "q_firma": c["q_firma"],
            "preds": c.get("predicciones_debiased") or c["predicciones"],
        })
    return out


def kernel_weight(delta_days, sigma=KERNEL_SIGMA_DAYS, window=KERNEL_WINDOW_DAYS):
    """Gaussian kernel con corte estricto a ±window."""
    if abs(delta_days) > window:
        return 0.0
    return math.exp(-(delta_days ** 2) / (2 * sigma ** 2))


def build_daily_series(contribs, candidatos):
    """
    Construye serie diaria desde min(fecha) hasta HOY para cada candidato.

    Para cada (día d, candidato c):
      kswa(d, c) = Σ_p w(p, d) × pct_p(c) / Σ_p w(p, d)
      donde w(p, d) = n_muestra_p × q_firma_p × kernel(|d - fecha_p|)

    Devuelve dict {cand: [(date, pct_kswa, n_polls_in_window), ...]}
    """
    if not contribs:
        return {}
    fmin = min(c["fecha"] for c in contribs)
    fmax = HOY

    series = defaultdict(list)
    d = fmin
    while d <= fmax:
        for cand in candidatos:
            num = 0.0
            den = 0.0
            n_in = 0
            for c in contribs:
                if cand not in c["preds"]:
                    continue
                delta = (d - c["fecha"]).days
                k = kernel_weight(delta)
                if k == 0:
                    continue
                w = (c["n_muestra"] or 1) * c["q_firma"] * k
                num += w * c["preds"][cand]
                den += w
                n_in += 1
            if den > 0:
                pct = num / den
                series[cand].append((d, round(pct, 3), n_in))
        d += timedelta(days=1)
    return dict(series)


def holt(series_pct, alpha=HOLT_ALPHA, beta=HOLT_BETA):
    """
    Holt's double exponential smoothing sobre log-odds.

    Input: lista de (date, pct, n) — pct en escala 0-100.
    Output: lista de (date, pct_kswa, holt_level_pct, holt_trend_pp).
    """
    if len(series_pct) < 2:
        return [(d, p, p, 0.0) for d, p, _ in series_pct]

    # Convertir a log-odds (escala 0-1)
    obs = [(d, logit(p / 100.0)) for d, p, _ in series_pct]

    # Init: nivel = primer obs, tendencia = diff inicial
    L = obs[0][1]
    T = obs[1][1] - obs[0][1]

    out = []
    for i, (d, y) in enumerate(obs):
        if i == 0:
            L_new = y
            T_new = T
        else:
            L_new = alpha * y + (1 - alpha) * (L + T)
            T_new = beta * (L_new - L) + (1 - beta) * T
        L, T = L_new, T_new
        # convert back a pct 0-100
        level_pct = inv_logit(L) * 100
        # trend en pp por día (aproximación: derivada de logit cerca del nivel actual)
        # trend_pp ≈ T × p × (1-p) × 100
        p = inv_logit(L)
        trend_pp = T * p * (1 - p) * 100
        out.append((d, series_pct[i][1], round(level_pct, 3), round(trend_pp, 4)))
    return out


def project(holt_series, target_date):
    """
    Proyecta el último nivel + tendencia hasta target_date.
    Devuelve pct proyectado (clamped a [0, 100]).
    """
    if not holt_series:
        return 0.0
    last_d, _, level, trend_pp = holt_series[-1]
    days_ahead = (target_date - last_d).days
    if days_ahead <= 0:
        return level

    # Re-aplicar trend en log-odds para no salirse de [0,1]
    last_logit = logit(level / 100.0)
    p = inv_logit(last_logit)
    # tendencia diaria en log-odds (derivada inversa)
    if p * (1 - p) > 0:
        trend_logit = (trend_pp / 100.0) / (p * (1 - p))
    else:
        trend_logit = 0.0
    forecast_logit = last_logit + days_ahead * trend_logit
    return round(inv_logit(forecast_logit) * 100, 2)


def kswa_at_date(contribs, cand, target_date):
    """
    Kernel-smoothed weighted average para `cand` en `target_date`.
    Si no hay polls en ventana, devuelve None.
    """
    num = 0.0
    den = 0.0
    for c in contribs:
        if cand not in c["preds"]:
            continue
        delta = (target_date - c["fecha"]).days
        k = kernel_weight(delta)
        if k == 0:
            continue
        w = (c["n_muestra"] or 1) * c["q_firma"] * k
        num += w * c["preds"][cand]
        den += w
    if den == 0:
        return None
    return round(num / den, 2)


# ---------- Main ----------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contribs = load_contribuciones()

    if not contribs:
        raise SystemExit("No hay contribuciones en ponderador-detalle.json")

    # Universo de candidatos con suficientes polls
    cand_counts = defaultdict(int)
    for c in contribs:
        for cand in c["preds"]:
            cand_counts[cand] += 1
    candidatos = [c for c, n in cand_counts.items() if n >= MIN_POLLS_FOR_FORECAST]
    candidatos.sort(key=lambda c: -cand_counts[c])

    # Serie diaria kernel-smoothed
    daily = build_daily_series(contribs, candidatos)

    # Aplicar Holt por candidato
    holt_series = {}
    for cand, serie in daily.items():
        holt_series[cand] = holt(serie)

    # Proyecciones al 31-may por dos vías:
    #   KSWA pura: extender el kernel sin tendencia (mantiene el último valor)
    #   Holt: extrapola con la tendencia local
    proyeccion = {}
    for cand in candidatos:
        h = holt_series.get(cand, [])
        if not h:
            continue
        kswa_today = h[-1][1]    # el valor de kswa en HOY (último día con datos)
        holt_31may = project(h, FECHA_ELECCION)
        # Central = promedio de los dos enfoques (uno respeta nivel actual, el otro tendencia)
        central = round((kswa_today + holt_31may) / 2, 2)
        proyeccion[cand] = {
            "kswa_hoy": kswa_today,
            "holt_31may": holt_31may,
            "central_31may": central,
        }

    # Serializar
    out = {
        "fecha_corte": HOY.isoformat(),
        "fecha_eleccion": FECHA_ELECCION.isoformat(),
        "dias_para_eleccion": (FECHA_ELECCION - HOY).days,
        "candidatos": candidatos,
        "parametros": {
            "kernel_sigma_days": KERNEL_SIGMA_DAYS,
            "kernel_window_days": KERNEL_WINDOW_DAYS,
            "holt_alpha": HOLT_ALPHA,
            "holt_beta": HOLT_BETA,
            "min_polls_for_forecast": MIN_POLLS_FOR_FORECAST,
            "logit_eps": LOGIT_EPS,
        },
        "metodologia": (
            "Capa 2: serie diaria construida por kernel-smoothed weighted average "
            "(KSWA) con kernel gaussiano σ=%dd, ventana ±%dd, peso=n×q_firma. "
            "Sobre eso se aplica Holt double-exponential smoothing en log-odds. "
            "Proyección al 31-may combina nivel KSWA + tendencia Holt extrapolada."
        ) % (KERNEL_SIGMA_DAYS, KERNEL_WINDOW_DAYS),
        "serie_diaria": {
            cand: [
                {
                    "date": d.isoformat(),
                    "kswa": pct_kswa,
                    "holt_level": holt_lvl,
                    "holt_trend_pp_day": holt_trend,
                }
                for d, pct_kswa, holt_lvl, holt_trend in holt_series[cand]
            ]
            for cand in candidatos
        },
        "proyeccion_31may": proyeccion,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✓ {OUT_PATH}")
    print(f"  Candidatos proyectados: {len(candidatos)}")
    print(f"  Días para elección: {(FECHA_ELECCION - HOY).days}")
    print()
    print(f"  {'cand':20s} {'kswa hoy':>9s} {'holt 31m':>9s} {'central':>8s}")
    print("  " + "-" * 50)
    for cand in candidatos[:10]:
        p = proyeccion[cand]
        print(f"  {cand:20s} {p['kswa_hoy']:>9.2f} {p['holt_31may']:>9.2f} {p['central_31may']:>8.2f}")


if __name__ == "__main__":
    main()
