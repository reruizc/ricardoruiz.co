#!/usr/bin/env python3
"""
Corpus de jurisprudencia REAL de salud — sentencias T de la Corte Constitucional.

Es la fuente del "por qué se cae una tutela" para el analizador de
tutelas-salud.html (puerta 2). Se eligió tras descartar la API de la Rama
Judicial, que resultó metadata-only (ver probe_rama_docs.py).

POR QUÉ SIRVE: la sentencia T es la REVISIÓN de un fallo de instancia, así que
narra qué decidió el juez de abajo y con qué argumento. Ejemplo real (T-361/25):
  "Sentencia de tutela de instancia. El 12 de febrero de 2025, el Juzgado Noveno
   Administrativo de Popayán negó la acción de tutela. Argumentó que la falta de
   una prescripción médica sobre la silla de ruedas impide que el juez…"
Eso es exactamente el material que el usuario necesita para saber por qué su
tutela podría fallar — y es citable, porque existe.

FUENTES
- Índice: datos.gov.co `v2k4-2t8s` (Socrata) — 21.162 sentencias T (1992→).
  Es la lista AUTORITATIVA: los soft-404 del sitio de la Corte corresponden a
  sentencias que no existen en el dataset.
- Texto: corteconstitucional.gov.co/relatoria/{año}/{T-NNN-YY}.htm

GOTCHAS (medidos 2026-08-01, no re-investigar)
- El HTML viene en **windows-1252**, no utf-8. Decodificarlo como utf-8 rompe
  todas las tildes y hace que las búsquedas por "negó" den cero.
- Soft-404: el sitio devuelve el shell del SPA (~8,6 KB) para sentencias
  inexistentes, con HTTP 200. Umbral: <20 KB = no existe.
- Cabecera `TEMAS-SUBTEMAS`: clasificación temática de la propia Corte. Permite
  filtrar salud sin ML ni full-text.
- Sufijos con letra (T-241A/22) existen, ~0,5%. El slug los conserva.
- El sitio NO tiene WAF agresivo: 6 descargas concurrentes en 0,5 s, todas 200.

DISCO: no se guarda el HTML (6 GB si fueran los 21k). Se extrae en memoria y se
persiste solo el texto de las sentencias de SALUD, en JSONL gzip.

Uso:
  python3 tools/tutela-analiza/harvest_relatoria.py index --desde 2016
  python3 tools/tutela-analiza/harvest_relatoria.py harvest --workers 5
  python3 tools/tutela-analiza/harvest_relatoria.py stats
Salida (gitignored):
  Bases de datos/tutelas-salud/relatoria/indice.json
  Bases de datos/tutelas-salud/relatoria/corpus-salud.jsonl.gz
  Bases de datos/tutelas-salud/relatoria/_vistos.json
"""
import gzip
import html as html_mod
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SOCRATA = "https://www.datos.gov.co/resource/v2k4-2t8s.json"
RELATORIA = "https://www.corteconstitucional.gov.co/relatoria"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT = Path(__file__).resolve().parents[2] / "Bases de datos" / "tutelas-salud" / "relatoria"
MIN_BYTES = 20_000  # por debajo de esto es el shell del SPA (soft-404)

# ── Clasificación temática ────────────────────────────────────────────────────
# Se aplica sobre el bloque TEMAS-SUBTEMAS (clasificación de la Corte), no sobre
# el cuerpo: el cuerpo cita normas de salud en casos que no son de salud.
RE_SALUD = re.compile(
    r"DERECHO A LA SALUD|SEGURIDAD SOCIAL EN SALUD|SERVICIO DE SALUD|"
    r"\bE\.?P\.?S\b|PLAN DE BENEFICIOS|\bPOS\b|\bPBS\b|TRATAMIENTO INTEGRAL|"
    r"MEDICAMENTO|ATENCION EN SALUD|ATENCIÓN EN SALUD|SISTEMA DE SALUD",
    re.I,
)
# Los 3 casos que cubre la herramienta (mapean con las pretensiones del microdato)
CASOS = {
    "medicamentos": re.compile(r"medicament|f[áa]rmac|insumo|suministro de", re.I),
    "citas": re.compile(r"\bcita[s]?\b|valoraci[óo]n por|consulta con especialista|asignaci[óo]n de cita", re.I),
    "procedimientos": re.compile(r"procedimiento|cirug[íi]a|interven(ci[óo]n|ir)|ex[áa]men|tratamiento", re.I),
}

# ── Extracción de la narración de instancia ───────────────────────────────────
# El patrón estable es una frase de decisión + un verbo de motivación.
RE_DECISION_INST = re.compile(
    r"[^.]{0,300}?\b(?:Juzgado|Tribunal|juez)\b[^.]{0,200}?"
    r"\b(neg[óo]|declar[óo] improcedente|rechaz[óo]|concedi[óo]|ampar[óo]|tutel[óo])\b"
    r"[^.]{0,300}\.",
    re.I,
)
RE_MOTIVO = re.compile(
    r"(?:Argument[óo]|Consider[óo]|Sostuvo|Estim[óo]|Explic[óo]|Indic[óo]|Se[ñn]al[óo]|"
    r"Fundament[óo]|Concluy[óo])\b[^.]{20,600}\.",
    re.I,
)
RE_RESUELVE = re.compile(r"\bRESUELVE\b(.{0,2500})", re.S)


def curl(url, timeout=60):
    """GET → bytes | None. curl por subprocess (esquiva el TLS de python 3.14)."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(timeout), url, "-H", f"User-Agent: {UA}"],
            capture_output=True, timeout=timeout + 10,
        )
        return r.stdout if r.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None


def curl_json(url, timeout=45):
    b = curl(url, timeout)
    if not b:
        return None
    try:
        return json.loads(b.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def slug(sentencia):
    """'T-361/25' → 'T-361-25'.  'T-241A/22' → 'T-241A-22'."""
    return sentencia.replace("/", "-")


def limpiar(raw_bytes):
    """HTML (windows-1252) → texto plano legible."""
    raw = raw_bytes.decode("windows-1252", errors="replace")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def bloque_temas(txt):
    """El encabezado TEMAS-SUBTEMAS: clasificación temática de la Corte."""
    i = txt.find("TEMAS-SUBTEMAS")
    if i < 0:
        return ""
    return txt[i + 14: i + 1400].strip()


def extraer_instancia(txt):
    """Qué decidió el juez de instancia y con qué argumento.
    Devuelve hasta 3 pasajes: decisión + el motivo que la sigue."""
    pasajes = []
    for m in RE_DECISION_INST.finditer(txt):
        frag = " ".join(m.group(0).split())
        if len(frag) < 60:
            continue
        cola = txt[m.end(): m.end() + 900]
        mot = RE_MOTIVO.search(cola)
        pasajes.append({
            "decision": frag[:600],
            "motivo": " ".join(mot.group(0).split())[:600] if mot else None,
        })
        if len(pasajes) >= 3:
            break
    return pasajes


def extraer_resuelve(txt):
    m = RE_RESUELVE.search(txt)
    if not m:
        return None
    r = " ".join(m.group(1).split())
    return r[:1200]


def procesar(item):
    """Descarga y extrae UNA sentencia. Devuelve el registro o un motivo de descarte."""
    ano4 = item["ano"]
    url = f"{RELATORIA}/{ano4}/{slug(item['sentencia'])}.htm"
    b = curl(url)
    if not b:
        return {"sentencia": item["sentencia"], "estado": "fail_download"}
    if len(b) < MIN_BYTES:
        return {"sentencia": item["sentencia"], "estado": "soft404", "bytes": len(b)}

    txt = limpiar(b)
    temas = bloque_temas(txt)
    # El filtro va sobre TEMAS (clasificación de la Corte). Si no hay bloque de
    # temas, se cae al encabezado del documento — nunca al cuerpo completo.
    base = temas if temas else txt[:1500]
    if not RE_SALUD.search(base):
        return {"sentencia": item["sentencia"], "estado": "no_salud"}

    casos = [k for k, rx in CASOS.items() if rx.search(base)]
    inst = extraer_instancia(txt)
    return {
        "sentencia": item["sentencia"],
        "estado": "ok",
        "ano": ano4,
        "fecha": item["fecha"],
        "magistrado": item.get("magistrado"),
        "url": url,
        "temas": temas[:900],
        "casos": casos,
        "instancia": inst,
        "resuelve": extraer_resuelve(txt),
        "n_chars": len(txt),
        "texto": txt,
    }


# ── Comandos ──────────────────────────────────────────────────────────────────
def cmd_index(desde):
    OUT.mkdir(parents=True, exist_ok=True)
    todos, offset = [], 0
    while True:
        url = (f"{SOCRATA}?$select=sentencia,fecha_sentencia,magistrado_a"
               f"&$where=sentencia_tipo%3D'T'%20AND%20fecha_sentencia%3E%3D'{desde}-01-01'"
               f"&$order=fecha_sentencia&$limit=1000&$offset={offset}")
        rows = curl_json(url)
        if not rows:
            break
        for r in rows:
            f = (r.get("fecha_sentencia") or "")[:10]
            todos.append({"sentencia": r["sentencia"], "fecha": f, "ano": f[:4],
                          "magistrado": r.get("magistrado_a")})
        if len(rows) < 1000:
            break
        offset += 1000
        time.sleep(0.3)
    (OUT / "indice.json").write_text(json.dumps(todos, ensure_ascii=False, indent=1))
    por_ano = {}
    for t in todos:
        por_ano[t["ano"]] = por_ano.get(t["ano"], 0) + 1
    print(f"Índice: {len(todos)} sentencias T desde {desde}")
    for a in sorted(por_ano):
        print(f"  {a}: {por_ano[a]}")


def cmd_harvest(workers):
    idx = json.loads((OUT / "indice.json").read_text())
    vistos_p = OUT / "_vistos.json"
    vistos = set(json.loads(vistos_p.read_text())) if vistos_p.exists() else set()
    pend = [i for i in idx if i["sentencia"] not in vistos]
    print(f"{len(idx)} en índice · {len(vistos)} ya vistas · {len(pend)} pendientes")
    if not pend:
        return

    corpus_p = OUT / "corpus-salud.jsonl.gz"
    n_ok = n_no = n_fail = 0
    t0 = time.time()
    # append binario: gzip soporta concatenación de miembros, así que se puede
    # reanudar sin releer lo ya escrito.
    with gzip.open(corpus_p, "at", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(procesar, i): i for i in pend}
            for k, f in enumerate(as_completed(futs), 1):
                r = f.result()
                vistos.add(r["sentencia"])
                if r["estado"] == "ok":
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    n_ok += 1
                elif r["estado"] == "no_salud":
                    n_no += 1
                else:
                    n_fail += 1
                if k % 100 == 0:
                    el = time.time() - t0
                    print(f"  {k}/{len(pend)} · salud {n_ok} · otras {n_no} · fallos {n_fail}"
                          f" · {k/el:.1f}/s")
                    vistos_p.write_text(json.dumps(sorted(vistos)))
    vistos_p.write_text(json.dumps(sorted(vistos)))
    print(f"\nSalud: {n_ok} · no salud: {n_no} · fallos: {n_fail}")
    print(f"Corpus: {corpus_p} ({corpus_p.stat().st_size/1e6:.1f} MB gz)")


def cmd_stats():
    corpus_p = OUT / "corpus-salud.jsonl.gz"
    rows = [json.loads(l) for l in gzip.open(corpus_p, "rt", encoding="utf-8")]
    print(f"Sentencias de salud en el corpus: {len(rows)}")
    por_ano, por_caso = {}, {}
    con_inst = con_motivo = 0
    for r in rows:
        por_ano[r["ano"]] = por_ano.get(r["ano"], 0) + 1
        for c in r["casos"] or ["(sin caso)"]:
            por_caso[c] = por_caso.get(c, 0) + 1
        if r["instancia"]:
            con_inst += 1
            if any(p.get("motivo") for p in r["instancia"]):
                con_motivo += 1
    print("\nPor año:")
    for a in sorted(por_ano):
        print(f"  {a}: {por_ano[a]}")
    print("\nPor caso de la herramienta:")
    for c, n in sorted(por_caso.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    print(f"\nCon narración de instancia: {con_inst} ({100*con_inst/len(rows):.0f}%)")
    print(f"  … y con el MOTIVO del juez: {con_motivo} ({100*con_motivo/len(rows):.0f}%)")
    tot = sum(r["n_chars"] for r in rows)
    print(f"\nTexto total: {tot/1e6:.1f} M chars (~{tot/4/1e6:.1f} M tokens)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    arg = lambda flag, d: (sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else d)
    if cmd == "index":
        cmd_index(arg("--desde", "2016"))
    elif cmd == "harvest":
        cmd_harvest(int(arg("--workers", "5")))
    else:
        cmd_stats()


if __name__ == "__main__":
    main()
