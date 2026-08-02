#!/usr/bin/env python3
"""
Probe: ¿qué % de tutelas en la API pública de la Rama Judicial tienen la
SENTENCIA como documento descargable?

Mide la viabilidad del corpus propio de fallos de instancia para el analizador
LLM de tutelas-salud.html (puerta 2: "¿mi tutela está bien hecha?" — necesita
saber por qué se caen las reales).

Estrategia: NO enumerar idProceso (espacio fragmentado por idConexion, bandas
vacías, API lenta en misses). En su lugar se CONSTRUYEN números de radicación:
    llaveProceso (23 díg) = codDespachoCompleto(12) + año(4) + consecutivo(5) + instancia(2)
y se consultan por /Procesos/Consulta/NumeroRadicacion, que devuelve
sujetosProcesales (para filtrar EPS) + idProceso. Luego:
    /Proceso/Detalle/{id}      → tipoProceso == "Acción de Tutela"
    /Proceso/Actuaciones/{id}  → actuación "Sentencia..." → conDocumentos
    /Proceso/DocumentosActuacion/{idRegActuacion} → inventario del documento
    (+ intento de descarga de UN documento para validar end-to-end)

API: https://consultaprocesos.ramajudicial.gov.co:448/api/v2  (¡puerto 448!)
Sin auth ni captcha, PERO con WAF (Azure Application Gateway): una ráfaga con
6 workers produjo 403 sostenido (ban por volumen+fingerprint, como el WAF de
leyes.senado). Ritmo obligatorio: SECUENCIAL con ~1s entre llamadas, y backoff
largo si aparece el 403.

Uso:
  python3 tools/tutela-analiza/probe_rama_docs.py            # corre el probe
  python3 tools/tutela-analiza/probe_rama_docs.py --por-ano 40   # muestra por año
Salida:
  Bases de datos/tutelas-salud/probe-rama/probe-report.json  (+ resumen en consola)
"""
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "tutelas-salud" / "probe-rama"

# Despachos semilla (codDespachoCompleto de 12 dígitos). Las tutelas se
# reparten a TODAS las jurisdicciones, así que mezclamos ciudades y
# especialidades. Formato: ciudad(5) + entidad(2) + especialidad(2) + nro(3).
#   31 = juzgado de circuito · 40 = juzgado municipal
#   03 = civil · 05 = laboral · 04 = penal
DESPACHOS = [
    "110013103001",  # Bogotá · civil circuito 001 (verificado con tutela real)
    "110014003001",  # Bogotá · civil municipal 001
    "110013105001",  # Bogotá · laboral circuito 001
    "050013103001",  # Medellín · civil circuito 001
    "050014003001",  # Medellín · civil municipal 001
    "760013103001",  # Cali · civil circuito 001
    "760014003001",  # Cali · civil municipal 001
    "080013103001",  # Barranquilla · civil circuito 001
    "680013103001",  # Bucaramanga · civil circuito 001
    "130013103001",  # Cartagena · civil circuito 001
]
ANOS = ["2023", "2024", "2025", "2026"]

EPS_RE = re.compile(
    r"\bE\.?P\.?S\b|NUEVA EPS|SANITAS|SURA|SALUD TOTAL|COMPENSAR|FAMISANAR|"
    r"COOSALUD|MUTUAL SER|EMSSANAR|ASMET|COMFENALCO|CAPITAL SALUD|SAVIA SALUD|"
    r"ALIANSALUD|CAJACOPI|COMFACHOCO|DUSAKAWI|PIJAOS|ANAS WAYUU|SALUDMIA|FOMAG",
    re.I,
)


DELAY = 1.0          # segundos entre llamadas (el WAF castiga ráfagas)
BAN_BACKOFF = 120    # si aparece 403, esperar esto y reintentar
_banned_count = 0


def curl_json(url, timeout=15, retries=1):
    """GET → dict | None. curl por subprocess (esquiva el TLS de python 3.14).
    Detecta el 403 HTML del WAF y hace backoff largo en vez de quemar la cuota."""
    global _banned_count
    for _ in range(retries + 1):
        try:
            r = subprocess.run(
                ["curl", "-s", "-m", str(timeout), url, "-H", f"User-Agent: {UA}"],
                capture_output=True, timeout=timeout + 5,
            )
            if r.returncode == 0 and r.stdout:
                raw = r.stdout.decode("utf-8", errors="replace")
                if raw.lstrip().startswith("<") and "403" in raw[:200]:
                    _banned_count += 1
                    print(f"  ⚠ WAF 403 — backoff {BAN_BACKOFF}s (van {_banned_count})")
                    time.sleep(BAN_BACKOFF)
                    continue
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.4)
    return None


def probar_radicado(despacho, ano, consecutivo):
    """Consulta un radicado construido. Devuelve dict con lo hallado o None."""
    llave = f"{despacho}{ano}{consecutivo:05d}00"
    d = curl_json(f"{BASE}/Procesos/Consulta/NumeroRadicacion?numero={llave}&SoloActivos=false&pagina=1")
    if not d or not d.get("procesos"):
        return None
    p = d["procesos"][0]
    return {
        "llave": llave, "ano": ano, "despacho": despacho,
        "idProceso": p["idProceso"],
        "sujetos": (p.get("sujetosProcesales") or "")[:220],
        "fecha": (p.get("fechaProceso") or "")[:10],
    }


def clasificar(hit):
    """Detalle → tipoProceso; solo seguimos si es tutela."""
    d = curl_json(f"{BASE}/Proceso/Detalle/{hit['idProceso']}")
    if not d:
        return None
    hit["tipoProceso"] = d.get("tipoProceso") or ""
    hit["esTutela"] = "tutela" in hit["tipoProceso"].lower()
    hit["esEPS"] = bool(EPS_RE.search(hit["sujetos"]))
    return hit


def actuaciones(hit):
    """Actuaciones → ¿hay sentencia? ¿trae documentos? ¿algún doc en el expediente?"""
    d = curl_json(f"{BASE}/Proceso/Actuaciones/{hit['idProceso']}?pagina=1")
    acts = (d or {}).get("actuaciones") or []
    hit["nActs"] = len(acts)
    hit["sentencia"] = None
    hit["docsEnAlgunaAct"] = False
    for a in acts:
        nombre = (a.get("actuacion") or "")
        if a.get("conDocumentos"):
            hit["docsEnAlgunaAct"] = True
        if "sentencia" in nombre.lower() and hit["sentencia"] is None:
            hit["sentencia"] = {
                "idRegActuacion": a.get("idRegActuacion"),
                "actuacion": nombre[:70],
                "fecha": (a.get("fechaActuacion") or "")[:10],
                "conDocumentos": bool(a.get("conDocumentos")),
            }
    return hit


def inventario_documentos(id_reg_actuacion):
    d = curl_json(f"{BASE}/Proceso/DocumentosActuacion/{id_reg_actuacion}")
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("documentos") or d.get("listaDocumentos") or []
    return []


def intentar_descarga(id_reg_documento, destino):
    """Valida end-to-end que el documento baja de verdad (magic bytes PDF/zip)."""
    url = f"{BASE}/Descarga/Documento/{id_reg_documento}"
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "40", url, "-H", f"User-Agent: {UA}", "-o", str(destino)],
            capture_output=True, timeout=50,
        )
        if r.returncode == 0 and destino.exists() and destino.stat().st_size > 500:
            head = destino.read_bytes()[:5]
            return {"ok": head.startswith(b"%PDF") or head.startswith(b"PK"),
                    "bytes": destino.stat().st_size, "magic": head.decode("latin-1"), "url": url}
    except subprocess.TimeoutExpired:
        pass
    return {"ok": False, "url": url}


def main():
    por_ano = 40
    if "--por-ano" in sys.argv:
        por_ano = int(sys.argv[sys.argv.index("--por-ano") + 1])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260801)

    # SECUENCIAL, pipeline por candidato: consulta → (si existe) detalle →
    # (si es tutela) actuaciones. Corte temprano cuando el año llena su cupo.
    tutelas, tipos, n_probados, n_hits = [], {}, 0, 0
    for ano in ANOS:
        conseguidas = 0
        # Ventanas de consecutivos CORRELATIVOS por despacho: en un juzgado los
        # números de radicación son secuenciales, así que una ventana desde un
        # arranque al azar es densa en existencia (el azar puro desperdicia
        # llamadas contra el WAF). 5 despachos rotados × ventana de 30.
        desps = rng.sample(DESPACHOS, 5)
        candidatos = []
        for d in desps:
            start = rng.randint(1, 200)
            candidatos += [(d, ano, start + i) for i in range(30)]
        print(f"— {ano}: buscando {por_ano} tutelas en {len(desps)} despachos…")
        for d, a, c in candidatos:
            if conseguidas >= por_ano:
                break
            n_probados += 1
            time.sleep(DELAY)
            h = probar_radicado(d, a, c)
            if not h:
                continue
            n_hits += 1
            time.sleep(DELAY)
            h = clasificar(h)
            if not h:
                continue
            tipos[h["tipoProceso"]] = tipos.get(h["tipoProceso"], 0) + 1
            if not h["esTutela"]:
                continue
            time.sleep(DELAY)
            h = actuaciones(h)
            tutelas.append(h)
            conseguidas += 1
            if conseguidas % 10 == 0:
                print(f"  {conseguidas}/{por_ano} · probados {n_probados}")
        print(f"  → {ano}: {conseguidas} tutelas")

    # Validación end-to-end de descarga (hasta 5 sentencias con documentos)
    print("Validando descarga de documentos…")
    descargas = []
    con_docs = [t for t in tutelas if t.get("sentencia") and t["sentencia"]["conDocumentos"]]
    for t in con_docs[:5]:
        time.sleep(DELAY)
        inv = inventario_documentos(t["sentencia"]["idRegActuacion"])
        t["inventarioDocs"] = [
            {k: d.get(k) for k in ("idRegDocumento", "nombre", "descripcion") if k in d}
            for d in inv[:4]
        ] if inv else []
        if inv and inv[0].get("idRegDocumento"):
            res = intentar_descarga(inv[0]["idRegDocumento"], OUT_DIR / f"doc-{t['idProceso']}.pdf")
            res["llave"] = t["llave"]
            descargas.append(res)

    # 5 · Reporte
    def tasa(sub):
        n = len(sub)
        con_sent = [t for t in sub if t.get("sentencia")]
        sent_doc = [t for t in con_sent if t["sentencia"]["conDocumentos"]]
        algun_doc = [t for t in sub if t.get("docsEnAlgunaAct")]
        return {
            "tutelas": n,
            "con_sentencia": len(con_sent),
            "sentencia_con_doc": len(sent_doc),
            "pct_sentencia_con_doc": round(100 * len(sent_doc) / len(con_sent), 1) if con_sent else None,
            "algun_doc_en_expediente": len(algun_doc),
            "eps": sum(1 for t in sub if t.get("esEPS")),
        }

    reporte = {
        "generado": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "muestra": {"radicados_probados": n_probados, "procesos_existentes": n_hits,
                    "tutelas": len(tutelas), "tipos_hallados": tipos,
                    "bans_waf": _banned_count},
        "global": tasa(tutelas),
        "por_ano": {a: tasa([t for t in tutelas if t["ano"] == a]) for a in ANOS},
        "eps_solo": tasa([t for t in tutelas if t.get("esEPS")]),
        "descargas_validadas": descargas,
        "tutelas": tutelas,
    }
    out = OUT_DIR / "probe-report.json"
    out.write_text(json.dumps(reporte, ensure_ascii=False, indent=1))

    print("\n══════════ RESULTADO ══════════")
    print(f"Tutelas muestreadas: {len(tutelas)}  (contra EPS: {reporte['global']['eps']})")
    g = reporte["global"]
    print(f"Con actuación de sentencia: {g['con_sentencia']}")
    print(f"Sentencia CON documento adjunto: {g['sentencia_con_doc']}"
          f"  ({g['pct_sentencia_con_doc']}% de las que tienen sentencia)")
    print(f"Expedientes con ALGÚN documento: {g['algun_doc_en_expediente']}")
    for a in ANOS:
        pa = reporte["por_ano"][a]
        print(f"  {a}: {pa['tutelas']} tutelas · sentencia c/doc {pa['sentencia_con_doc']}"
              f"/{pa['con_sentencia']} ({pa['pct_sentencia_con_doc']}%)")
    if descargas:
        ok = [d for d in descargas if d.get("ok")]
        print(f"Descargas end-to-end: {len(ok)}/{len(descargas)} OK")
        for d in descargas:
            print(f"  {'✓' if d.get('ok') else '✗'} {d.get('llave','?')} → {d.get('bytes','—')} bytes {d.get('magic','')}")
    print(f"\nReporte: {out}")


if __name__ == "__main__":
    main()
