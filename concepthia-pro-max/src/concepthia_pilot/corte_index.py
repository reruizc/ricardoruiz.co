#!/usr/bin/env python3
"""Build a compact, reproducible Corte Constitucional corpus from official sources.

The catalogue is datos.gov.co/Socrata v2k4-2t8s. Document text is fetched only
from the Corte's Relatoría; the resulting JSONL.gz can be stored in S3.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


SOCRATA_URL = "https://www.datos.gov.co/resource/v2k4-2t8s.json"
RELATORIA_URL = "https://www.corteconstitucional.gov.co/relatoria"
USER_AGENT = "ConcepthIA/2.0 (public-source research; contacto@serviciocivil.gov.co)"


def clean_html(raw: bytes) -> str:
    text = raw.decode("windows-1252", errors="replace")
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def sentence_url(sentence: str, date_value: str) -> str:
    year = date_value[:4]
    return f"{RELATORIA_URL}/{year}/{sentence.replace('/', '-')}.htm"


def catalogue(from_year: int, limit: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    offset = 0
    while limit is None or len(rows) < limit:
        page_size = min(1000, limit - len(rows)) if limit else 1000
        params = {
            "$select": "sentencia,fecha_sentencia,magistrado_a,sala,sentencia_tipo",
            "$where": f"fecha_sentencia >= '{from_year}-01-01'",
            "$order": "fecha_sentencia DESC",
            "$limit": page_size,
            "$offset": offset,
        }
        response = requests.get(SOCRATA_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        page = response.json()
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += len(page)
    return rows


def fetch_document(item: dict[str, str]) -> dict[str, str] | None:
    date_value = item.get("fecha_sentencia", "")
    sentence = item.get("sentencia", "")
    if not re.match(r"^[A-Z]+-\d+[A-Z]?/\d{2}$", sentence) or len(date_value) < 4:
        return None
    url = sentence_url(sentence, date_value)
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None
    # The Relatoría returns a small SPA shell for non-existing documents.
    if len(response.content) < 20_000:
        return None
    text = clean_html(response.content)
    if len(text) < 5_000:
        return None
    themes_at = text.find("TEMAS-SUBTEMAS")
    themes = text[themes_at:themes_at + 2400] if themes_at >= 0 else text[:2400]
    return {
        "id": f"CC {sentence}", "court": "Corte Constitucional", "sentencia": sentence,
        "fecha": date_value[:10], "magistrado": item.get("magistrado_a", ""),
        "sala": item.get("sala", ""), "tipo": item.get("sentencia_tipo", ""),
        "url": url, "temas": themes, "texto": text,
    }


def build(from_year: int, limit: int | None, workers: int, output: Path) -> tuple[int, int]:
    items = catalogue(from_year, limit)
    output.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with gzip.open(output, "wt", encoding="utf-8") as handle, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_document, item) for item in items]
        for future in as_completed(futures):
            document = future.result()
            if document:
                handle.write(json.dumps(document, ensure_ascii=False) + "\n")
                kept += 1
    return len(items), kept


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye corpus oficial de jurisprudencia constitucional")
    parser.add_argument("--from-year", type=int, default=2016)
    parser.add_argument("--limit", type=int, help="Útil para piloto; omítelo para cubrir todo el período")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("data/jurisprudence/corte-documents.jsonl.gz"))
    parser.add_argument("--s3-uri", help="Ej.: s3://elecciones-2026/.../jurisprudence/corte-documents.jsonl.gz")
    args = parser.parse_args()
    if args.from_year < 1992 or args.workers < 1 or args.limit == 0:
        parser.error("Revisa --from-year, --workers y --limit.")
    total, kept = build(args.from_year, args.limit, args.workers, args.output)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "catalogue_records": total, "documents": kept, "output": str(args.output)}
    print(json.dumps(report, ensure_ascii=False))
    if args.s3_uri:
        subprocess.run(["aws", "s3", "cp", str(args.output), args.s3_uri], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
