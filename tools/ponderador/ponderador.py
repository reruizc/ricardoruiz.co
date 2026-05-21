"""
Ponderador de encuestas presidenciales 2026 — ricardoruiz.co

Toma:
  Bases de datos/cne_encuestas_clasificadas.csv  (inventario + filtro de tipo)
  Bases de datos/encuestas_porcentajes.csv       (% por candidato; long format)
  Bases de datos/output_agregados/consultas/resumen.json  (ground truth 8-mar)

Calcula:
  q_firma       — calibrado por MAE de cada firma vs resultado del 8-mar.
                  Firmas sin datos pre-8-mar quedan en 1.0 (neutro, flag).
  q_modo        — agregado por modo de levantamiento.
  Δ_recencia    — decaimiento exponencial por días desde la encuesta.
  house_effect  — desviación de cada firma frente a la mediana semanal,
                  para cada candidato (sólo polls post-marzo).

Emite:
  Bases de datos/output_ponderador/ponderador-actual.json
      → para previa-1v.html (estructura mínima de candidatos + meta)
  Bases de datos/output_ponderador/ponderador-detalle.json
      → transparencia total: pesos por encuesta, contribuciones, MAE, etc.

Cero dependencias: stdlib pura.

HISTORIA / RECONSTRUCCIÓN (2026-05-20)
======================================
El .py original se perdió; sobrevivió sólo el .pyc en
tools/ponderador/__pycache__/ponderador.cpython-314.pyc.

Este archivo es una reconstrucción derivada de:
  · docstring + nombres de funciones del .pyc (via `marshal` + `dis`)
  · bytecode de calcular_q_firma / calcular_q_modo / delta_recencia
    (mapeo lineal MAE→q_firma confirmado: q = 1 - 0.6·(m-mn)/(mx-mn))
  · re-cómputo client-side embebido en previa-1v.html líneas 6938-7013
    (fórmula peso = q_firma × q_modo × exp(-λ·max(0,días)))
  · outputs `ponderador-actual.json` y `ponderador-detalle.json`
    usados como fixtures de validación.

Validación: al correr el script sobre los CSV originales y sin overrides,
el output reproduce el ponderador del 15-may al pp.

NUEVA FEATURE — Q_FIRMA_OVERRIDE
================================
Permite sub-ponderar manualmente encuestas no calibrables (firmas sin
participación pre-8-mar) o sospechosas de cocina compartida. Se aplica
por encuesta_id ANTES del fallback al q_firma calibrado o al default 1.0.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[2]
# Si estamos dentro de .claude/worktrees/<wt>/tools/ponderador, subir al repo principal
if ".claude" in ROOT.parts and "worktrees" in ROOT.parts:
    idx = ROOT.parts.index(".claude")
    ROOT = Path(*ROOT.parts[:idx])
DAT = ROOT / "Bases de datos"
CLAS_PATH = DAT / "cne_encuestas_clasificadas.csv"
PCT_PATH = DAT / "encuestas_porcentajes.csv"
RESULTADOS_PATH = DAT / "output_agregados" / "consultas" / "resumen.json"
OUT_DIR = DAT / "output_ponderador"
OUT_PUB = OUT_DIR / "ponderador-actual.json"
OUT_DET = OUT_DIR / "ponderador-detalle.json"

# ---------- Constantes ----------
FECHA_CONSULTAS = date(2026, 3, 8)
FECHA_ELECCION = date(2026, 5, 31)
HOY = date.today()

LAMBDA_RECENCIA = 0.1
SIGMA_HOUSE_PP = 2.5
DIAS_VIGENCIA = 60
Q_FIRMA_DEFAULT = 1.0
Q_MODO_DEFAULT = {
    "presencial": 1.0,
    "digital": 1.0,
    "telefonico": 1.0,
    "mixto": 1.0,
    "": 1.0,
}

# Overrides manuales de q_firma por encuesta_id.
# Caso de uso: firmas no calibradas + sospecha de cocina compartida.
# Aplicado por id, ANTES del fallback al q_firma calibrado / default.
Q_FIRMA_OVERRIDE = {
    # Génesis Crea (11-may) y Corp. MMM (17-may) son la misma cocina operativa
    # (confirmado por el operativo Casanare 27-feb radicado bajo ambos sellos
    # con cifras idénticas: id 24-genesis-crea y 26-corporacion-miguel-maldonado).
    # Atenuamos a 0.45 cada una para evitar doble conteo (peso conjunto ~ una
    # encuesta calibrada con q ≈ 0.9 en lugar de dos con q ≈ 1.0).
    "45-genesis-may11": 0.45,
    "46-corp-mmm-may17": 0.45,
}


# ---------- Modelo ----------
@dataclass
class Encuesta:
    encuesta_id: str
    encuestadora: str
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    n_muestra: int = 0
    modo: str = ""
    categoria: str = ""
    objetivo: str = ""

    @property
    def fecha_efectiva(self) -> Optional[date]:
        return self.fecha_fin or self.fecha_inicio


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ---------- Loaders ----------
def cargar_resultados():
    """Devuelve {consulta_clave: {candidato_apellido: pct_real}}."""
    raw = json.loads(RESULTADOS_PATH.read_text(encoding="utf-8"))
    APELLIDO = {
        "Paloma Susana Valencia Laserna": "Valencia",
        "Juan Daniel Oviedo Arango": "Oviedo",
        "Juan Manuel Galan Pachon": "Galán",
        "Juan Carlos Pinzon Bueno": "Pinzón",
        "Victoria Eugenia Davila Hoyos": "Dávila",
        "Enrique Peñalosa Londoño": "Peñalosa",
        "Anibal Gaviria Correa": "Gaviria",
        "David Andres Luna Sanchez": "Luna",
        "Mauricio Cardenas Santamaria": "Cárdenas",
        "Roy Leonardo Barreras Montealegre": "Barreras",
        "Daniel Quintero Calle": "Quintero",
        "Edison Lucio Torres Moreno": "Torres",
        "Martha Viviana Bernal Amaya": "Bernal",
        "Hector Elias Pineda Salazar": "Pineda",
        "Claudia Nayibe Lopez Hernandez": "López",
        "Leonardo Humberto Huerta Gutierrez": "Huerta",
    }
    out = {}
    for c in raw["consultas"]:
        total = c["votos"]
        clave = c["clave"]
        out[clave] = {}
        for cand in c["candidatos"]:
            apellido = APELLIDO.get(cand["nombre"], cand["nombre"])
            out[clave][apellido] = cand["votos"] / total * 100
    return out


def cargar_inventario():
    out = {}
    with open(CLAS_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cat = (r.get("categoria_confirmada") or r.get("categoria_auto") or "").strip()
            if cat != "presidencial_nacional":
                continue
            try:
                n = int(r.get("n_muestra") or 0)
            except ValueError:
                n = 0
            out[r["id"]] = Encuesta(
                encuesta_id=r["id"],
                encuestadora=r["encuestadora"],
                fecha_inicio=parse_date(r.get("fecha_inicio")),
                fecha_fin=parse_date(r.get("fecha_fin")),
                n_muestra=n,
                modo=(r.get("modo") or "").strip(),
                categoria=cat,
                objetivo=r.get("objetivo") or "",
            )
    return out


def cargar_predicciones():
    """Devuelve {encuesta_id: {consulta: {candidato: pct}}}"""
    raw = defaultdict(lambda: defaultdict(dict))
    with open(PCT_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pct_s = (r.get("pct") or "").strip()
            if not pct_s:
                continue
            try:
                pct = float(pct_s)
            except ValueError:
                continue
            eid = r["encuesta_id"]
            consultas = raw[eid]
            consulta = r["consulta"]
            consultas[consulta][r["candidato"]] = pct
    return {k: {kk: dict(vv) for kk, vv in v.items()} for k, v in raw.items()}


# ---------- Cálculo ----------
def calcular_q_firma(encuestas, predicciones, resultados):
    """
    Para cada firma, identifica su(s) encuesta(s) más cercana(s) al 8-mar
    (con fecha entre 7-feb y 8-mar) que tienen datos para la consulta
    Gran o Frente. Calcula MAE por (firma, consulta) y promedia.

    Devuelve (q_firma_dict, detalle_calibracion).
    """
    detalle = defaultdict(list)
    for eid, enc in encuestas.items():
        if not enc.fecha_efectiva:
            continue
        if enc.fecha_efectiva > FECHA_CONSULTAS:
            continue
        if (FECHA_CONSULTAS - enc.fecha_efectiva).days > 30:
            continue
        preds = predicciones.get(eid, {})
        for consulta in ("gran", "frente", "soluciones"):
            pred_c = preds.get(consulta)
            actual_c = resultados.get(consulta)
            if not pred_c or not actual_c:
                continue
            # Filtrar predicciones a candidatos que sí están en el resultado
            # (esto descarta candidatos extintos / fantasmas antes de normalizar).
            pred_filt = {k: v for k, v in pred_c.items() if k in actual_c}
            s = sum(pred_filt.values())
            if s == 0:
                continue
            pred_filt = {k: v / s * 100 for k, v in pred_filt.items()}
            keys = set(pred_filt) | set(actual_c)
            errs = [abs(pred_filt.get(k, 0) - actual_c.get(k, 0)) for k in keys]
            mae = sum(errs) / len(errs)
            pred_winner = max(pred_filt, key=pred_filt.get)
            actual_winner = max(actual_c, key=actual_c.get)
            detalle[enc.encuestadora].append({
                "encuesta_id": eid,
                "consulta": consulta,
                "mae": round(mae, 2),
                "max_err": round(max(errs), 2),
                "n_cands": len(keys),
                "winner_ok": pred_winner == actual_winner,
                "fecha_fin": enc.fecha_efectiva.isoformat(),
                "n_muestra": enc.n_muestra,
            })

    # MAE por firma: promedio (firma, consulta), luego promedio entre consultas.
    mae_por_firma = {}
    for firma, items in detalle.items():
        if not items:
            continue
        por_consulta = defaultdict(list)
        for it in items:
            por_consulta[it["consulta"]].append(it["mae"])
        consulta_means = [statistics.mean(v) for v in por_consulta.values()]
        mae_por_firma[firma] = statistics.mean(consulta_means)

    # Mapeo lineal MAE [min, max] → q_firma [1.0, 0.4].
    if mae_por_firma:
        maes = list(mae_por_firma.values())
        mn, mx = min(maes), max(maes)
        q_firma = {}
        for firma, mae in mae_por_firma.items():
            if mx == mn:
                q_firma[firma] = 1.0
            else:
                q_firma[firma] = round(1.0 - 0.6 * (mae - mn) / (mx - mn), 3)
    else:
        q_firma = {}

    calibracion = {
        firma: {
            "mae_promedio": round(mae_por_firma[firma], 2),
            "q_firma": q_firma[firma],
            "evaluaciones": detalle[firma],
        }
        for firma in mae_por_firma
    }
    return q_firma, calibracion


def calcular_q_modo(encuestas, q_firma):
    """Promedia q_firma de las firmas calibradas, agrupando por modo."""
    por_modo = defaultdict(list)
    for enc in encuestas.values():
        if enc.encuestadora not in q_firma:
            continue
        if not enc.modo:
            continue
        por_modo[enc.modo].append(q_firma[enc.encuestadora])
    out = dict(Q_MODO_DEFAULT)
    for modo, vals in por_modo.items():
        if vals:
            out[modo] = round(statistics.mean(vals), 3)
    return out


def delta_recencia(dias, lam):
    return math.exp(-lam * max(0, dias))


def calcular_promedio_primera_vuelta(encuestas, predicciones, q_firma, q_modo):
    contribuciones = []
    excluidas = []
    candidatos_universo = set()
    elegibles = []

    for eid, enc in encuestas.items():
        if not enc.fecha_efectiva:
            excluidas.append({"encuesta_id": eid, "razón": "sin fecha"})
            continue
        if enc.categoria != "presidencial_nacional":
            excluidas.append({"encuesta_id": eid, "razón": f"categoría={enc.categoria}"})
            continue
        dias = (HOY - enc.fecha_efectiva).days
        if dias > DIAS_VIGENCIA:
            excluidas.append({"encuesta_id": eid, "razón": f"demasiado vieja ({dias}d > {DIAS_VIGENCIA}d)"})
            continue
        preds = predicciones.get(eid, {}).get("primera_vuelta")
        if not preds:
            excluidas.append({"encuesta_id": eid, "razón": "sin datos primera_vuelta en CSV"})
            continue
        elegibles.append((eid, enc, dias, preds))
        candidatos_universo.update(preds.keys())

    for eid, enc, dias, preds in elegibles:
        # Override por id si existe; si no, q_firma calibrada; si no, default.
        if eid in Q_FIRMA_OVERRIDE:
            qf = Q_FIRMA_OVERRIDE[eid]
        else:
            qf = q_firma.get(enc.encuestadora, Q_FIRMA_DEFAULT)
        qm = q_modo.get(enc.modo, 1.0)
        dr = delta_recencia(dias, LAMBDA_RECENCIA)
        peso = qf * qm * dr
        contribuciones.append({
            "encuesta_id": eid,
            "encuestadora": enc.encuestadora,
            "fecha_fin": enc.fecha_efectiva.isoformat(),
            "dias": dias,
            "n_muestra": enc.n_muestra,
            "modo": enc.modo,
            "q_firma": qf,
            "q_modo": qm,
            "delta_recencia": round(dr, 4),
            "peso_final": round(peso, 5),
            "predicciones": preds,
        })

    promedio = {}
    if contribuciones:
        total = sum(c["peso_final"] for c in contribuciones)
        for cand in candidatos_universo:
            num = sum(c["peso_final"] * c["predicciones"].get(cand, 0) for c in contribuciones)
            promedio[cand] = round(num / total, 2) if total else 0
        for c in contribuciones:
            c["peso_relativo_pct"] = round(c["peso_final"] / total * 100, 2) if total else 0

    return promedio, contribuciones, excluidas


def calcular_house_effect(encuestas, predicciones):
    """
    Por candidato: desviación promedio (pp) de cada firma frente a la mediana
    semanal de todas las firmas. Solo polls post-marzo (>= 2026-03-09).
    """
    por_semana = defaultdict(lambda: defaultdict(list))  # {(yr,wk): {cand: [(firma, pct), ...]}}
    for eid, enc in encuestas.items():
        if not enc.fecha_efectiva or enc.fecha_efectiva <= FECHA_CONSULTAS:
            continue
        preds = predicciones.get(eid, {}).get("primera_vuelta", {})
        if not preds:
            continue
        iso_year, iso_week, _ = enc.fecha_efectiva.isocalendar()
        for cand, pct in preds.items():
            por_semana[(iso_year, iso_week)][cand].append((enc.encuestadora, pct))

    # Desviación por (firma, cand): valor − mediana_semanal_cand
    desvs = defaultdict(lambda: defaultdict(list))
    for _semana, por_cand in por_semana.items():
        for cand, vals in por_cand.items():
            if len(vals) < 2:
                continue
            mediana = statistics.median([v for _, v in vals])
            for firma, pct in vals:
                desvs[firma][cand].append(pct - mediana)

    out = {}
    for firma, por_cand in desvs.items():
        out[firma] = {}
        for cand, ds in por_cand.items():
            out[firma][cand] = {
                "house_effect_pp": round(statistics.mean(ds), 2),
                "n_polls": len(ds),
                "std_pp": round(statistics.pstdev(ds), 2) if len(ds) > 1 else 0.0,
            }
    return out


TOP_PUBLIC = (
    "Cepeda", "De la Espriella", "Valencia", "Fajardo",
    "Claudia López", "Barreras", "Blanco",
)
NS_NR_KEYS = ("NS-NR", "Ninguno", "No sabe", "No votaría")


def construir_publico(promedio, meta):
    """
    Versión mínima para previa-1v.html. Colapsa el universo de ~17 candidatos
    a {TOP_PUBLIC + 'NS-NR' + 'Otros'} para mantener el shape histórico que
    consume el frontend (ver previa-1v.html líneas 1531-1542). 'Otros' se
    calcula como residuo para garantizar cierre exacto al 100%.
    """
    cands_out = {}
    for cand in TOP_PUBLIC:
        if cand in promedio:
            cands_out[cand] = {"pct": round(promedio[cand], 2)}
    ns_nr = sum(promedio.get(k, 0) for k in NS_NR_KEYS)
    if ns_nr > 0:
        cands_out["NS-NR"] = {"pct": round(ns_nr, 2)}
    explicit = sum(v["pct"] for v in cands_out.values())
    otros = max(0.0, round(100.0 - explicit, 2))
    if otros > 0:
        cands_out["Otros"] = {"pct": otros}
    return {
        "fuente": "ricardoruiz.co — ponderador propio",
        "fecha_corte": HOY.isoformat(),
        "candidatos": cands_out,
        "meta": meta,
        "url_metodologia": "https://ricardoruiz.co/metodologia-simulador-presidencial-2026.pdf",
    }


# ---------- Main ----------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    resultados = cargar_resultados()
    encuestas = cargar_inventario()
    predicciones = cargar_predicciones()

    q_firma, calibracion = calcular_q_firma(encuestas, predicciones, resultados)
    q_modo = calcular_q_modo(encuestas, q_firma)
    promedio, contribuciones, excluidas = calcular_promedio_primera_vuelta(
        encuestas, predicciones, q_firma, q_modo
    )
    house = calcular_house_effect(encuestas, predicciones)

    meta = {
        "encuestas_usadas": len(contribuciones),
        "encuestas_excluidas": len(excluidas),
        "firmas_calibradas": len(q_firma),
        "lambda_recencia": LAMBDA_RECENCIA,
        "sigma_house_pp": SIGMA_HOUSE_PP,
        "dias_vigencia": DIAS_VIGENCIA,
    }

    publico = construir_publico(promedio, meta)
    OUT_PUB.write_text(json.dumps(publico, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    detalle = {
        "fecha_corte": HOY.isoformat(),
        "parametros": {
            "lambda_recencia": LAMBDA_RECENCIA,
            "sigma_house_pp": SIGMA_HOUSE_PP,
            "dias_vigencia": DIAS_VIGENCIA,
        },
        "calibracion_8mar": calibracion,
        "q_firma": q_firma,
        "q_firma_override": Q_FIRMA_OVERRIDE,
        "q_modo": q_modo,
        "promedio_primera_vuelta": promedio,
        "contribuciones": contribuciones,
        "excluidas": excluidas,
        "house_effect": house,
    }
    OUT_DET.write_text(json.dumps(detalle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✓ {OUT_PUB}")
    print(f"✓ {OUT_DET}")
    print(f"  Encuestas usadas: {len(contribuciones)}")
    print(f"  Encuestas excluidas: {len(excluidas)}")
    print(f"  Firmas calibradas: {len(q_firma)}")
    if Q_FIRMA_OVERRIDE:
        print(f"  Q_FIRMA_OVERRIDE activos: {len(Q_FIRMA_OVERRIDE)}")
        for eid, qf in Q_FIRMA_OVERRIDE.items():
            print(f"    {eid:35s} → q_firma={qf}")


if __name__ == "__main__":
    main()
