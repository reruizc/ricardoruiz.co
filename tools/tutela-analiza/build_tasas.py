#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_tasas.py — tabla de tasas de concesión de tutelas de SALUD.

Hito 1 del módulo `tutela-analiza`. Produce el insumo del score de viabilidad
de `tutelas-salud.html`: la frecuencia empírica REAL con que se resuelven a
favor las tutelas de salud, condicionada por pretensión × departamento × sujeto
de especial protección (SEP).

El % que ve el usuario NO lo inventa un modelo: sale de aquí. Por eso el script
guarda, junto a cada tasa, el n, el intervalo de Wilson y el nivel de estrato al
que tuvo que caer para resolverla (honestidad estadística).

Fuente
------
Corte Constitucional · datos.gov.co (Socrata), dataset `g3ma-7zce`
("Pretensiones reclamadas en las tutelas"), 1 fila por (expediente × pretensión).
Abierto, sin token, CC BY-SA 4.0, refresco mensual.
OJO: `anio` es TEXTO en el dataset -> comparar con '2025', no con 2025.

Agregamos server-side con SoQL ($group) en vez de bajar ~2M filas: 11 requests
en vez de 40 páginas.

Definición de FAVORABLE (declarada y fija)
------------------------------------------
    Concede + Concede parcial + Hecho superado
"Hecho superado" cuenta como favorable porque es victoria de facto: la entidad
cumplió antes del fallo, que es exactamente lo que el accionante buscaba.
Se guarda el desglose completo para que la metodología sea auditable.

Uso
---
    python3 tools/tutela-analiza/build_tasas.py
    python3 tools/tutela-analiza/build_tasas.py --no-cache   # ignora crudo local

Salidas (gitignored)
--------------------
    Bases de datos/tutelas-salud/raw/g3ma-7zce-salud-{anio}.json   (cache crudo)
    Bases de datos/tutelas-salud/tasas-tutela-salud.json           (el entregable)
"""

import argparse
import json
import math
import os
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------- constantes

RESOURCE = "g3ma-7zce"
BASE_URL = f"https://www.datos.gov.co/resource/{RESOURCE}.json"
DERECHO = "SALUD"

# Años con datos en el dataset (verificado). 2026 va parcial (corte ~may-2026).
ANIOS = ["2016", "2017", "2018", "2019", "2020", "2021",
         "2022", "2023", "2024", "2025", "2026"]

# Ventana para el score: SOLO el último año completo.
#
# Verificado con backtest.py (entrenar -> predecir 2025): la favorabilidad viene
# subiendo de forma monótona (86,3% en 2019 -> 92,5% en 2025, +6,2 pp), así que
# ampliar la ventana mete años viejos y sesga el score HACIA ABAJO. Medido:
#     2024 solo        MAE 1,78 pp · sesgo -1,18 pp   <- mejor
#     2023+2024        MAE 1,88 pp · sesgo -1,41 pp
#     2022+2023+2024   MAE 2,18 pp · sesgo -1,78 pp
# Se excluye el año en curso porque llega parcial (corte de actualización).
VENTANA_SCORE = [str(max(int(a) for a in ANIOS if int(a) < datetime.now().year))]

FAVORABLES = ["Concede", "Concede parcial", "Hecho superado"]

# n mínimo para aceptar una celda en su estrato más fino. Por debajo, se cae al
# siguiente nivel de la cascada.
MIN_N = 100

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "Bases de datos", "tutelas-salud")
RAW_DIR = os.path.join(OUT_DIR, "raw")
OUT_JSON = os.path.join(OUT_DIR, "tasas-tutela-salud.json")

# Las 3 pretensiones que atiende tutelas-salud.html, mapeadas al vocabulario
# exacto del dataset de la Corte.
CASOS_HERRAMIENTA = {
    "medicamentos": "Entrega oportuna de medicamentos o insumos",
    "citas": "Asignación de citas médicas",
    "procedimientos": "Práctica oportuna de procedimiento médico",
}


# ------------------------------------------------------------------ utilidades

def log(msg):
    print(msg, flush=True)


def fetch(params, intentos=3):
    """GET a Socrata vía curl (evita el TLS de python 3.14 sin certifi)."""
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    for i in range(intentos):
        try:
            r = subprocess.run(
                ["curl", "-s", "-m", "90", "-A", UA, "-H", "Accept: application/json", url],
                capture_output=True, timeout=120,
            )
            txt = r.stdout.decode("utf-8", errors="replace")
            if not txt.strip():
                raise ValueError("respuesta vacía")
            data = json.loads(txt)
            if isinstance(data, dict) and data.get("error"):
                raise ValueError(data.get("message", "error de Socrata"))
            return data
        except Exception as e:
            if i == intentos - 1:
                raise
            log(f"    reintento {i + 1}/{intentos - 1} tras error: {e}")
    return []


def wilson(k, n, z=1.96):
    """Intervalo de Wilson para una proporción. Se ensancha si n es chico."""
    if n <= 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, centro - margen), min(1.0, centro + margen))


def resumir(desglose):
    """{decision: n} -> bloque con tasa favorable + Wilson + desglose."""
    n = sum(desglose.values())
    k = sum(v for d, v in desglose.items() if d in FAVORABLES)
    p, lo, hi = wilson(k, n)
    return {
        "n": n,
        "favorable_n": k,
        "p": round(p, 4),
        "lo": round(lo, 4),
        "hi": round(hi, 4),
        "desglose": {d: desglose[d] for d in sorted(desglose, key=lambda x: -desglose[x])},
    }


# ------------------------------------------------------------------ descarga

def bajar_anio(anio, usar_cache=True):
    """Conteos agregados server-side para un año: pretensión × depto × SEP × decisión."""
    cache = os.path.join(RAW_DIR, f"{RESOURCE}-salud-{anio}.json")
    if usar_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            filas = json.load(f)
        log(f"  {anio}: {len(filas):>6} grupos (cache)")
        return filas

    filas, offset, LIMITE = [], 0, 50000
    while True:
        lote = fetch({
            "$select": "pretension, departamento, cod_dpto, sep, decision_1, count(1) as n",
            "$where": f"derecho='{DERECHO}' AND anio='{anio}'",
            "$group": "pretension, departamento, cod_dpto, sep, decision_1",
            "$limit": LIMITE,
            "$offset": offset,
        })
        filas.extend(lote)
        if len(lote) < LIMITE:
            break
        offset += LIMITE

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False)
    log(f"  {anio}: {len(filas):>6} grupos")
    return filas


# ------------------------------------------------------------------ agregación

def construir(usar_cache=True):
    log(f"Descargando conteos de tutelas de {DERECHO} ({RESOURCE})…")
    por_anio = {a: bajar_anio(a, usar_cache) for a in ANIOS}

    # Acumuladores. Cada uno: clave -> {decision: n}
    fino = defaultdict(lambda: defaultdict(int))      # pretensión|depto|sep
    pret_depto = defaultdict(lambda: defaultdict(int))
    pret_sep = defaultdict(lambda: defaultdict(int))
    pret = defaultdict(lambda: defaultdict(int))
    global_ = defaultdict(int)
    serie = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # pret -> anio -> dec
    serie_nac = defaultdict(lambda: defaultdict(int))                   # anio -> dec
    deptos = {}

    for anio, filas in por_anio.items():
        for r in filas:
            p = (r.get("pretension") or "").strip()
            d = (r.get("departamento") or "").strip()
            s = (r.get("sep") or "").strip()
            dec = (r.get("decision_1") or "").strip()
            if not p or not dec:
                continue
            try:
                n = int(r.get("n") or 0)
            except (TypeError, ValueError):
                continue
            if n <= 0:
                continue

            cod = (r.get("cod_dpto") or "").strip()
            if d and cod:
                deptos[d] = cod

            # La serie histórica usa todos los años; el score solo la ventana.
            serie[p][anio][dec] += n
            serie_nac[anio][dec] += n
            if anio not in VENTANA_SCORE:
                continue

            fino[f"{p}||{d}||{s}"][dec] += n
            pret_depto[f"{p}||{d}"][dec] += n
            pret_sep[f"{p}||{s}"][dec] += n
            pret[p][dec] += n
            global_[dec] += n

    # --- resolución en cascada, hecha aquí para que el consumidor solo busque
    celdas = {}
    for clave, desg in fino.items():
        p, d, s = clave.split("||")
        if sum(desg.values()) >= MIN_N:
            base, nivel = desg, "pretension+depto+sep"
        elif sum(pret_depto[f"{p}||{d}"].values()) >= MIN_N:
            base, nivel = pret_depto[f"{p}||{d}"], "pretension+depto"
        elif sum(pret_sep[f"{p}||{s}"].values()) >= MIN_N:
            base, nivel = pret_sep[f"{p}||{s}"], "pretension+sep"
        elif sum(pret[p].values()) >= MIN_N:
            base, nivel = pret[p], "pretension"
        else:
            base, nivel = global_, "nacional"
        bloque = resumir(base)
        bloque["nivel"] = nivel
        bloque["n_celda_fina"] = sum(desg.values())
        celdas[clave] = bloque

    salida = {
        "v": datetime.now(timezone.utc).strftime("%Y%m%d"),
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": {
            "nombre": "Corte Constitucional — Pretensiones reclamadas en las tutelas",
            "dataset": RESOURCE,
            "url": f"https://www.datos.gov.co/d/{RESOURCE}",
            "licencia": "CC BY-SA 4.0",
            "nota": ("Universo de tutelas remitidas a la Corte para eventual revisión, "
                     "con la decisión reportada en el expediente. Anonimizado: no "
                     "incluye EPS accionada, identidad ni detalle clínico."),
        },
        "metodologia": {
            "favorable": FAVORABLES,
            "no_favorable": ["Niega", "Improcedente", "Rechaza",
                             "Daño consumado", "Situación sobreviniente"],
            "nota_hecho_superado": ("Se cuenta como favorable: la entidad cumplió antes "
                                    "del fallo, que es el resultado que buscaba quien tuteló."),
            "ventana_score": VENTANA_SCORE,
            "min_n": MIN_N,
            "intervalo": "Wilson 95%",
            "cascada": ["pretension+depto+sep", "pretension+depto",
                        "pretension+sep", "pretension", "nacional"],
        },
        "casos_herramienta": CASOS_HERRAMIENTA,
        "departamentos": deptos,
        "nacional": resumir(global_),
        "por_pretension": {p: resumir(v) for p, v in
                           sorted(pret.items(), key=lambda kv: -sum(kv[1].values()))},
        "celdas": celdas,
        "serie_nacional": {a: resumir(v) for a, v in sorted(serie_nac.items())},
        "serie_por_pretension": {
            p: {a: resumir(v) for a, v in sorted(av.items())}
            for p, av in serie.items()
            if p in CASOS_HERRAMIENTA.values()
        },
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    return salida


# ------------------------------------------------------------------ reporte

def reportar(s):
    kb = os.path.getsize(OUT_JSON) / 1024
    nac = s["nacional"]
    log("")
    log("=" * 74)
    log(f"  tasas-tutela-salud.json  ·  {kb:.0f} KB  ·  ventana {'-'.join(VENTANA_SCORE)}")
    log("=" * 74)
    log(f"  Nacional salud: n={nac['n']:,}  favorable={nac['p']:.1%} "
        f"[{nac['lo']:.1%}–{nac['hi']:.1%}]")
    log("")
    log("  Los 3 casos de la herramienta:")
    for slug, pretension in CASOS_HERRAMIENTA.items():
        b = s["por_pretension"].get(pretension)
        if not b:
            log(f"    {slug:<16} SIN DATOS (¿cambió el vocabulario del dataset?)")
            continue
        niega = b["desglose"].get("Niega", 0)
        log(f"    {slug:<16} n={b['n']:>7,}  favorable={b['p']:.1%} "
            f"[{b['lo']:.1%}–{b['hi']:.1%}]  niega={niega / b['n']:.1%}")
    log("")
    niveles = defaultdict(int)
    for c in s["celdas"].values():
        niveles[c["nivel"]] += 1
    log(f"  Celdas resueltas: {len(s['celdas']):,}")
    for n, c in sorted(niveles.items(), key=lambda kv: -kv[1]):
        log(f"    {n:<28} {c:>5}")
    log("")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-cache", action="store_true",
                    help="ignora el crudo local y vuelve a consultar Socrata")
    args = ap.parse_args()
    try:
        reportar(construir(usar_cache=not args.no_cache))
    except Exception as e:
        log(f"ERROR: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
