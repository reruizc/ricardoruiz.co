#!/usr/bin/env python3
"""
scrape_cne.py — refresca el inventario del CNE de encuestas 2026.

Recorre la grilla paginada en https://www.cne.gov.co/encuestas-2026
(paginas ?start=0,10,20,...) hasta agotar resultados, descarga cada
pagina de detalle y produce dos artefactos con el mismo shape que ya
consume el ponderador:

  Bases de datos/cne_encuestas_2026.json
  Bases de datos/cne_encuestas_2026.csv

Diseñado pensando en sandboxes con TLS roto (Python 3.14 stdlib sin
certifi): hace los GET via `curl` (subprocess) para evitar errores de
CERTIFICATE_VERIFY_FAILED.

Uso:
  python3 tools/ponderador/scrape_cne.py                  # corre y escribe
  python3 tools/ponderador/scrape_cne.py --out-dir tmp/   # escribe en otro dir
  python3 tools/ponderador/scrape_cne.py --dry-run        # no escribe nada
  python3 tools/ponderador/scrape_cne.py --diff           # imprime diff vs JSON actual

No depende de paquetes externos. Demora ~30-60s para 50 encuestas.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CNE_BASE = "https://www.cne.gov.co"
LIST_URL = f"{CNE_BASE}/encuestas-2026"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
PAGE_STEP = 10  # joomla paginator default
MAX_PAGES = 30  # safety stop (~300 encuestas)

# Repo root: el script vive en tools/ponderador/, los datos en
# "Bases de datos/" del repo principal — NO en el worktree (gitignored).
SCRIPT_DIR = Path(__file__).resolve().parent
WORKTREE_GUESS = SCRIPT_DIR.parents[1]
# Si estamos dentro de .claude/worktrees/<wt>/tools/ponderador, subir al repo principal.
if ".claude" in WORKTREE_GUESS.parts and "worktrees" in WORKTREE_GUESS.parts:
    idx = WORKTREE_GUESS.parts.index(".claude")
    DEFAULT_OUT = Path(*WORKTREE_GUESS.parts[:idx]) / "Bases de datos"
else:
    DEFAULT_OUT = WORKTREE_GUESS / "Bases de datos"


# ---------- HTTP via curl (robusto contra TLS local) ----------

def fetch(url: str, timeout: int = 25, retries: int = 2) -> str:
    """GET via curl. Retorna texto utf-8 o levanta RuntimeError."""
    last_err = ""
    for attempt in range(retries + 1):
        try:
            res = subprocess.run(
                ["curl", "-sS", "-A", UA, "--max-time", str(timeout), url],
                capture_output=True, check=True, timeout=timeout + 5,
            )
            text = res.stdout.decode("utf-8", errors="replace")
            if text and "<html" in text.lower():
                return text
            last_err = "respuesta corta o sin HTML"
        except subprocess.CalledProcessError as e:
            last_err = f"curl exit {e.returncode}: {e.stderr.decode('utf-8','replace')[:200]}"
        except subprocess.TimeoutExpired:
            last_err = "timeout"
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} fallo: {last_err}")


# ---------- Listado: enumera todos los slugs ----------

SLUG_RE = re.compile(r"/encuestas-2026/(\d+)-([a-z0-9\-]+)")


def enumerate_slugs(verbose: bool = True) -> list[tuple[int, str]]:
    """Recorre el listado paginado y devuelve [(id_num, 'N-slug'), ...] ordenado por id."""
    seen: dict[int, str] = {}
    for page in range(MAX_PAGES):
        start = page * PAGE_STEP
        url = LIST_URL if start == 0 else f"{LIST_URL}?start={start}"
        try:
            html_text = fetch(url)
        except RuntimeError as e:
            print(f"  [warn] {url}: {e}", file=sys.stderr)
            break
        new_here: list[tuple[int, str]] = []
        for m in SLUG_RE.finditer(html_text):
            n = int(m.group(1))
            slug = m.group(2)
            full = f"{n}-{slug}"
            if n not in seen:
                seen[n] = full
                new_here.append((n, full))
        if verbose:
            print(f"  start={start:>3}  nuevas={len(new_here):>2}  acumuladas={len(seen)}")
        if not new_here:
            # dos páginas sin novedades = fin
            if page > 0:
                break
    return sorted(seen.items())


# ---------- Parser del detalle ----------

DL_FIELD_RE = re.compile(r"<dt[^>]*>\s*([^<]+?)\s*</dt>\s*<dd[^>]*>(.*?)</dd>", flags=re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
HREF_RE = re.compile(r'href="([^"]+)"', flags=re.I)

LABEL_KEYS = {
    "no": "NO",
    "n°": "NO",
    "radicado": "RADICADO",
    "fecha radicado": "FECHA RADICADO",
    "firma encuestadora": "FIRMA ENCUESTADORA",
    "fecha de realizacion": "FECHA DE REALIZACIÓN",
    "fecha de realización": "FECHA DE REALIZACIÓN",
    "fecha de publicacion": "FECHA DE PUBLICACIÓN",
    "fecha de publicación": "FECHA DE PUBLICACIÓN",
    "persona natural o juridica quien la encomendo": "PERSONA NATURAL O JURÍDICA QUIÉN LA ENCOMENDÓ",
    "persona natural o jurídica quién la encomendó": "PERSONA NATURAL O JURÍDICA QUIÉN LA ENCOMENDÓ",
    "fuente de financiacion": "FUENTE DE FINANCIACIÓN",
    "fuente de financiación": "FUENTE DE FINANCIACIÓN",
    "universo representado": "UNIVERSO REPRESENTADO",
    "proposito del estudio": "PROPOSITO DEL ESTUDIO",
    "propósito del estudio": "PROPOSITO DEL ESTUDIO",
    "tipo y tamano de la muestra": "TIPO Y TAMAÑO DE LA MUESTRA",
    "tipo y tamaño de la muestra": "TIPO Y TAMAÑO DE LA MUESTRA",
    "margen de error y nivel de confianza": "MARGEN DE ERROR Y NIVEL DE CONFIANZA",
    "metodo de recoleccion de datos": "MÉTODO DE RECOLECCIÓN DE DATOS",
    "método de recolección de datos": "MÉTODO DE RECOLECCIÓN DE DATOS",
    "enlace a documento": "ENLACE A DOCUMENTO",
}


def _strip_tags_keep_href(value_html: str) -> tuple[str, str | None]:
    """Devuelve (texto_plano, primer_href_o_None) de un fragmento HTML."""
    href = None
    m = HREF_RE.search(value_html)
    if m:
        href = html.unescape(m.group(1))
    text = TAG_RE.sub(" ", value_html)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    return text, href


def _norm_label(raw: str) -> str | None:
    raw = raw.rstrip(": ").strip().lower()
    # quitar tildes para normalizar
    norm = (
        raw.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )
    return LABEL_KEYS.get(norm) or LABEL_KEYS.get(raw)


def parse_detail(slug: str, page_html: str) -> dict:
    """Extrae campos del <dl>...</dl> del detalle."""
    campos: dict[str, str] = {}
    doc_url: str | None = None
    for m in DL_FIELD_RE.finditer(page_html):
        label = _norm_label(m.group(1))
        if not label:
            continue
        value_text, href = _strip_tags_keep_href(m.group(2))
        campos[label] = value_text
        if label == "ENLACE A DOCUMENTO" and href:
            doc_url = href

    firma_raw = campos.get("FIRMA ENCUESTADORA", "")
    firma_nombre = _firma_a_nombre(firma_raw)
    # Si la firma está rota (operador del CNE escribió una fecha o número),
    # caer a la persona/fuente que encomendó, y luego al slug.
    if _firma_es_invalida(firma_raw):
        for alt_key in (
            "PERSONA NATURAL O JURÍDICA QUIÉN LA ENCOMENDÓ",
            "FUENTE DE FINANCIACIÓN",
        ):
            alt = _firma_a_nombre(campos.get(alt_key, ""))
            if alt and not _firma_es_invalida(alt):
                firma_nombre = alt
                break
        else:
            firma_nombre = _firma_a_nombre(slug.split("-", 1)[1] if "-" in slug else slug)

    out: dict = {
        "id": slug,
        "encuestadora_slug": slug.split("-", 1)[1] if "-" in slug else slug,
        "url": f"{CNE_BASE}/encuestas-2026/{slug}",
        "campos": campos,
        "encuestadora_nombre": firma_nombre,
        "n_muestra": _extraer_n_muestra(campos.get("TIPO Y TAMAÑO DE LA MUESTRA", "")),
        "modo": _extraer_modo(
            campos.get("MÉTODO DE RECOLECCIÓN DE DATOS", "") + " " +
            campos.get("TIPO Y TAMAÑO DE LA MUESTRA", "")
        ),
        "documento_url": doc_url,
    }
    f_ini, f_fin = _parse_rango_fechas(campos.get("FECHA DE REALIZACIÓN", ""))
    out["fecha_inicio"] = f_ini
    out["fecha_fin"] = f_fin
    return out


def _firma_es_invalida(raw: str) -> bool:
    """True si el campo FIRMA viene roto (fecha, número solo, vacío)."""
    if not raw or len(raw.strip()) < 3:
        return True
    s = raw.strip()
    # Fecha pura: '30/04/2026', '2026-04-30', etc.
    if re.fullmatch(r"[\d/\-\.\s:]+", s):
        return True
    # Año aislado
    if re.fullmatch(r"\d{4}", s):
        return True
    return False


# ---------- Heurísticas de normalización ----------

FIRMA_OVERRIDES = {
    "ATLASINTEL": "Atlas Intel",
    "ATLAS INTEL": "Atlas Intel",
    "GAD3": "GAD3",
    "GAD 3": "GAD3",
    "INVAMER": "Invamer",
    "GUARUMO": "Guarumo / EcoAnalítica",
    "GUARUMO / ECOANALITICA": "Guarumo / EcoAnalítica",
    "GUARUMO / ECOANALÍTICA": "Guarumo / EcoAnalítica",
    "GUARUMO Y ECOANALÍTICA": "Guarumo / EcoAnalítica",
    "GUARUMO Y ECOANALITICA": "Guarumo / EcoAnalítica",
    "CENTRO NACIONAL DE CONSULTORÍA": "Centro Nacional de Consultoría",
    "CENTRO NACIONAL DE CONSULTORIA": "Centro Nacional de Consultoría",
    "CIFRAS & CONCEPTOS": "Cifras & Conceptos",
    "CIFRAS Y CONCEPTOS": "Cifras & Conceptos",
    "YANHAAS": "YanHaas",
    "GENESIS CREA": "Génesis Crea",
    "GÉNESIS CREA": "Génesis Crea",
    "ANALIZAR Y LOMBANA": "Analizar y Lombana",
    "ANALIZAR & LOMBANA": "Analizar y Lombana",
    "MEDICIONES ESTRATÉGICAS": "Mediciones Estratégicas",
    "MEDICIONES ESTRATEGICAS": "Mediciones Estratégicas",
    "MAGDALENA LÍDER": "Magdalena Líder",
    "MAGDALENA LIDER": "Magdalena Líder",
    "UNIVERSIDAD ICESI": "Universidad ICESI",
    "CIRCULO DE OPINIÓN": "Círculo de Opinión",
    "CÍRCULO DE OPINIÓN": "Círculo de Opinión",
}


def _firma_a_nombre(raw: str) -> str:
    if not raw:
        return ""
    key = raw.strip().upper().rstrip(".")
    if key in FIRMA_OVERRIDES:
        return FIRMA_OVERRIDES[key]
    # Match por prefijo: "GUARUMO Y ECOANALÍTICA: MEDICIÓN Y CONCEPTOS..." → "Guarumo / EcoAnalítica"
    for alias, canon in FIRMA_OVERRIDES.items():
        if key.startswith(alias + " ") or key.startswith(alias + ":") or key.startswith(alias + ","):
            return canon
    # Title case "snake-friendly"
    return " ".join(w.capitalize() if w.isalpha() else w for w in raw.strip().split())


def _extraer_n_muestra(raw: str) -> int | None:
    """Encuentra el tamaño de muestra dentro del campo TIPO Y TAMAÑO.

    Estrategia en dos pasadas:
      1. Buscar patrones explícitos ("muestra de N", "Encuesta a N adultos",
         "N encuestas en M municipios", "tamaño muestral N", etc.).
         Si hay match, devolverlo (excluye años 1900-2100).
      2. Fallback: primer número entero entre 200 y 200.000 que NO sea año.
    """
    if not raw:
        return None

    def _to_int(s: str) -> int | None:
        token = s.replace(".", "").replace(",", "").replace(" ", "")
        try:
            return int(token)
        except ValueError:
            return None

    NUM = r"(\d{1,3}(?:[.,\s]\d{3})+|\d{3,6})"

    patterns = [
        rf"muestra\s+(?:de|muestral|total)?\s*(?:de\s+)?{NUM}",
        rf"tama[ñn]o\s+(?:de\s+)?(?:la\s+)?muestra\s+(?:de\s+)?{NUM}",
        rf"Encuesta\s+a\s+{NUM}\s+(?:adultos|personas|colombianos|encuestados)",
        rf"{NUM}\s+encuestados",
        rf"{NUM}\s+encuestas\b",
        rf"{NUM}\s+(?:adultos|personas|colombianos)\s+(?:encuestados|con\s+intenci|mayores)",
        rf"n\s*=\s*{NUM}",
    ]
    for pat in patterns:
        m = re.search(pat, raw, flags=re.I)
        if not m:
            continue
        n = _to_int(m.group(1))
        if n is None:
            continue
        # rechazar años
        if 1900 <= n <= 2100:
            continue
        if 200 <= n <= 200_000:
            return n

    # Fallback: primer número grande que no sea año
    for m in re.finditer(NUM, raw):
        n = _to_int(m.group(1))
        if n is None:
            continue
        if 1900 <= n <= 2100:
            continue
        if 200 <= n <= 200_000:
            return n
    return None


def _extraer_modo(raw: str) -> str:
    if not raw:
        return "desconocido"
    t = raw.lower()
    has_pres = bool(re.search(r"presencial|cara a cara|cara-a-cara|hogar|personal en", t))
    has_tel = bool(re.search(r"telef[oó]n|cati|ivr|llamada", t))
    has_dig = bool(re.search(r"digital|online|en l[ií]nea|web|internet|panel", t))
    flags = [k for k, v in [("presencial", has_pres), ("telefonico", has_tel), ("digital", has_dig)] if v]
    if len(flags) == 0:
        return "desconocido"
    if len(flags) == 1:
        return flags[0]
    return "mixto"


# Meses en español → numero
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_rango_fechas(raw: str) -> tuple[str | None, str | None]:
    """Soporta:
       '5 al 8 enero 2026' → ('2026-01-05', '2026-01-08')
       '1 al 10 de diciembre de 2025' → ('2025-12-01', '2025-12-10')
       '25 abril al 5 de mayo de 2026' → ('2026-04-25', '2026-05-05')
       '15 al 24 de abril de 2026' → ('2026-04-15', '2026-04-24')
    """
    if not raw:
        return None, None
    s = raw.lower()
    # Caso 0: 'DD/MM/YYYY-DD/MM/YYYY' o 'DD/MM/YYYY al DD/MM/YYYY'
    m = re.search(
        r"(\d{1,2})/(\d{1,2})/(\d{4})\s*(?:-|al|a)\s*(\d{1,2})/(\d{1,2})/(\d{4})",
        s,
    )
    if m:
        d1, m1, y1, d2, m2, y2 = (int(m.group(i)) for i in range(1, 7))
        return f"{y1:04d}-{m1:02d}-{d1:02d}", f"{y2:04d}-{m2:02d}-{d2:02d}"
    s = s.replace("de ", "")
    # Caso A: 'D1 mesA al D2 [de] mesB [de] YYYY'
    m = re.search(
        r"(\d{1,2})\s+(" + "|".join(MESES) + r")\s+al\s+(\d{1,2})\s+(" + "|".join(MESES) + r")\s+(\d{4})",
        s,
    )
    if m:
        d1 = int(m.group(1)); mesA = MESES[m.group(2)]
        d2 = int(m.group(3)); mesB = MESES[m.group(4)]
        y = int(m.group(5))
        # Si mesA > mesB el año del inicio probablemente es el anterior
        yA = y if mesA <= mesB else y - 1
        return f"{yA:04d}-{mesA:02d}-{d1:02d}", f"{y:04d}-{mesB:02d}-{d2:02d}"
    # Caso B: 'D1 al D2 [de] mes [de] YYYY'
    m = re.search(
        r"(\d{1,2})\s+al\s+(\d{1,2})\s+(" + "|".join(MESES) + r")\s+(\d{4})",
        s,
    )
    if m:
        d1 = int(m.group(1)); d2 = int(m.group(2))
        mes = MESES[m.group(3)]; y = int(m.group(4))
        return f"{y:04d}-{mes:02d}-{d1:02d}", f"{y:04d}-{mes:02d}-{d2:02d}"
    # Caso C: una sola fecha 'D mes YYYY'
    m = re.search(r"(\d{1,2})\s+(" + "|".join(MESES) + r")\s+(\d{4})", s)
    if m:
        d = int(m.group(1)); mes = MESES[m.group(2)]; y = int(m.group(3))
        iso = f"{y:04d}-{mes:02d}-{d:02d}"
        return iso, iso
    return None, None


# ---------- Persistencia ----------

CSV_COLUMNS = [
    "id", "encuestadora_nombre", "encuestadora_slug", "n_muestra", "modo",
    "fecha_inicio", "fecha_fin", "margen_error_texto", "metodo_recoleccion_texto",
    "objetivo_texto", "documento_url", "url",
]


def write_outputs(rows: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "cne_encuestas_2026.json"
    csv_path = out_dir / "cne_encuestas_2026.csv"
    # JSON: ordenado por id numérico ascendente
    rows_sorted = sorted(rows, key=lambda r: int(r["id"].split("-", 1)[0]))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows_sorted, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows_sorted:
            campos = r.get("campos", {})
            w.writerow({
                "id": r["id"],
                "encuestadora_nombre": r.get("encuestadora_nombre", ""),
                "encuestadora_slug": r.get("encuestadora_slug", ""),
                "n_muestra": r.get("n_muestra") if r.get("n_muestra") is not None else "",
                "modo": r.get("modo", ""),
                "fecha_inicio": r.get("fecha_inicio") or "",
                "fecha_fin": r.get("fecha_fin") or "",
                "margen_error_texto": campos.get("MARGEN DE ERROR Y NIVEL DE CONFIANZA", ""),
                "metodo_recoleccion_texto": campos.get("MÉTODO DE RECOLECCIÓN DE DATOS", ""),
                "objetivo_texto": campos.get("PROPOSITO DEL ESTUDIO", ""),
                "documento_url": r.get("documento_url") or "",
                "url": r["url"],
            })
    return json_path, csv_path


# ---------- Main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Refresca el inventario CNE de encuestas 2026.")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT,
                    help=f"Directorio destino (default: {DEFAULT_OUT})")
    ap.add_argument("--dry-run", action="store_true",
                    help="No escribe ningún archivo. Solo imprime resumen.")
    ap.add_argument("--diff", action="store_true",
                    help="Imprime diff vs el JSON anterior (si existe).")
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="Pausa entre requests (segundos).")
    ap.add_argument("--quiet", action="store_true", help="Menos ruido en stdout.")
    args = ap.parse_args()

    verbose = not args.quiet

    if verbose:
        print(f"== Enumerando listado de encuestas en {LIST_URL} ==")
    slugs = enumerate_slugs(verbose=verbose)
    if not slugs:
        print("ERROR: no se encontraron encuestas. ¿CNE caído o cambió el HTML?", file=sys.stderr)
        return 2
    if verbose:
        print(f"\n== Total encuestas listadas: {len(slugs)} (max id: {slugs[-1][0]}) ==\n")

    rows: list[dict] = []
    failures: list[tuple[str, str]] = []
    for n, slug in slugs:
        url = f"{CNE_BASE}/encuestas-2026/{slug}"
        try:
            page_html = fetch(url)
            row = parse_detail(slug, page_html)
            if not row.get("encuestadora_nombre"):
                failures.append((slug, "FIRMA ENCUESTADORA vacío"))
            rows.append(row)
            if verbose:
                print(f"  ✓ {slug:48s} firma={row['encuestadora_nombre']:30s} fin={row.get('fecha_fin') or '???'} n={row.get('n_muestra')}")
        except RuntimeError as e:
            failures.append((slug, str(e)))
            print(f"  ✗ {slug:48s} {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if args.diff:
        prev_path = args.out_dir / "cne_encuestas_2026.json"
        if prev_path.exists():
            with open(prev_path, encoding="utf-8") as f:
                prev_rows = json.load(f)
            prev_ids = {r["id"] for r in prev_rows}
            new_ids = {r["id"] for r in rows}
            added = sorted(new_ids - prev_ids, key=lambda s: int(s.split("-", 1)[0]))
            removed = sorted(prev_ids - new_ids, key=lambda s: int(s.split("-", 1)[0]))
            print("\n== DIFF vs snapshot anterior ==")
            print(f"  Antes:   {len(prev_rows)} entradas")
            print(f"  Ahora:   {len(rows)} entradas")
            print(f"  NUEVAS:  {len(added)}")
            for sid in added:
                row = next(r for r in rows if r["id"] == sid)
                print(f"    + {sid:42s}  {row.get('encuestadora_nombre',''):25s}  fin={row.get('fecha_fin')}  n={row.get('n_muestra')}")
            if removed:
                print(f"  ELIMINADAS (raro):")
                for sid in removed:
                    print(f"    - {sid}")
        else:
            print(f"\n(--diff: no existe {prev_path}, salto el diff)")

    if args.dry_run:
        print(f"\n[dry-run] No se escribió nada. {len(rows)} encuestas parseadas, {len(failures)} fallos.")
        return 0

    json_path, csv_path = write_outputs(rows, args.out_dir)
    print(f"\n✓ Escrito: {json_path}")
    print(f"✓ Escrito: {csv_path}")
    if failures:
        print(f"\n⚠ {len(failures)} encuestas con problemas:")
        for slug, msg in failures:
            print(f"    - {slug}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
