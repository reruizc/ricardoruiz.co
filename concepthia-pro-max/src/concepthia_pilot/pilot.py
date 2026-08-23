#!/usr/bin/env python3
"""Download a small, respectful pilot corpus from the public DASCD catalogue.

The crawler only follows concept detail pages discovered on the official catalogue,
then downloads the PDF explicitly linked on each detail page.  It does not probe
storage services or construct potential document URLs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

BASE_URL = "https://www.serviciocivil.gov.co"
CATALOGUE_URL = f"{BASE_URL}/transparencia/conceptos-juridicos"
USER_AGENT = "ConcepthiaProMaxPilot/0.1 (public-catalogue research; contact: contacto@example.invalid)"
SEED_TERMS = ("vacaciones", "teletrabajo", "inhabilidades", "encargo", "prima técnica", "acoso laboral")
PDF_MAGIC = b"%PDF-"
TOTAL_REQUEST_TIMEOUT_SECONDS = 8


class TotalRequestTimeout(TimeoutError):
    pass


@dataclass
class Concept:
    id: str | None
    radicado: str | None
    anio: int | None
    fecha: str | None
    titulo: str | None
    tema: str | None
    subtema: str | None
    url_ficha: str
    url_pdf: str | None
    nombre_archivo: str | None
    tamano_bytes: int | None
    numero_paginas: int | None
    sha256: str | None
    pdf_valido: bool | None
    texto_extraible: bool | None
    fuente_catalogo: str


class PublicCatalogueCrawler:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.1"})

    def get(self, url: str, **kwargs: object) -> requests.Response:
        started_at = time.monotonic()
        response = self.session.get(url, timeout=(10, 10), stream=True, **kwargs)
        try:
            response.raise_for_status()
            chunks = []
            for chunk in response.iter_content(chunk_size=1024):
                if time.monotonic() - started_at > TOTAL_REQUEST_TIMEOUT_SECONDS:
                    raise TotalRequestTimeout(f"La respuesta superó {TOTAL_REQUEST_TIMEOUT_SECONDS} segundos")
                if chunk:
                    chunks.append(chunk)
            response._content = b"".join(chunks)
            return response
        finally:
            response.close()
            time.sleep(self.delay_seconds)

    def catalogue_candidates(self, term: str, page: int) -> list[dict[str, object]]:
        response = self.get(CATALOGUE_URL, params={
            "title": term,
            "field_terma_target_id": "All",
            "field_sub_tema_target_id": "All",
            "page": page,
        })
        source_url = response.url
        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[dict[str, object]] = []
        for row in soup.select(".view-conceptos-juridicos .views-row"):
            link = row.select_one(".views-field-title a[href]")
            if not link:
                continue
            date = row.select_one("time[datetime]")
            taxonomy = [node.get_text(" ", strip=True) or None for node in row.select(".views-field-field-terma .field-content, .views-field-field-sub-tema .field-content")]
            date_value = date.get("datetime") if date else None
            candidates.append({
                "url_ficha": urljoin(BASE_URL, link["href"]),
                "titulo": link.get_text(" ", strip=True) or None,
                "fecha": date_value,
                "anio": int(date_value[:4]) if date_value and date_value[:4].isdigit() else None,
                "tema": taxonomy[0] if taxonomy else None,
                "subtema": taxonomy[1] if len(taxonomy) > 1 else None,
                "fuente_catalogo": source_url,
            })
        return candidates

    def detail(self, candidate: dict[str, object]) -> Concept:
        response = self.get(str(candidate["url_ficha"]))
        soup = BeautifulSoup(response.text, "html.parser")
        pdf_link = soup.select_one(
            ".field--name-field-archivo2 a[href*='.pdf' i], "
            ".file--application-pdf a[href], "
            "main a[href*='/conceptos-juridicos/' i][href*='.pdf' i]"
        )
        pdf_url = urljoin(BASE_URL, pdf_link["href"]) if pdf_link else None
        filename = pdf_link.get_text(" ", strip=True) if pdf_link else None
        fields = {label.get_text(" ", strip=True).lower(): label.parent.get_text(" ", strip=True) for label in soup.select(".field__label")}
        detail_date = _first_date(fields.get("fecha de expedición de la norma")) or candidate.get("fecha")
        title = soup.select_one("h1")
        radicado = _extract_radicado(
            " ".join(filter(None, [Path(urlparse(pdf_url).path).name if pdf_url else None, filename,
                                    title.get_text(" ", strip=True) if title else None]))
        )
        node_id = None
        settings_element = soup.select_one('script[data-drupal-selector="drupal-settings-json"]')
        if settings_element and settings_element.string:
            try:
                current_path = str(json.loads(settings_element.string).get("path", {}).get("currentPath", ""))
                node_match = re.fullmatch(r"node/(\d+)", current_path)
                node_id = node_match.group(1) if node_match else None
            except json.JSONDecodeError:
                node_id = None
        return Concept(
            id=node_id,
            radicado=radicado,
            anio=int(str(detail_date)[:4]) if detail_date and str(detail_date)[:4].isdigit() else candidate.get("anio"),
            fecha=str(detail_date) if detail_date else None,
            titulo=title.get_text(" ", strip=True) if title else candidate.get("titulo"),
            tema=_field_value(fields.get("tema")) or candidate.get("tema"),
            subtema=_field_value(fields.get("sub tema")) or candidate.get("subtema"),
            url_ficha=response.url,
            url_pdf=pdf_url,
            nombre_archivo=filename or None,
            tamano_bytes=None, numero_paginas=None, sha256=None, pdf_valido=None, texto_extraible=None,
            fuente_catalogo=str(candidate["fuente_catalogo"]),
        )

    def download_pdf(self, concept: Concept, destination: Path) -> Concept:
        if not concept.url_pdf:
            raise ValueError("La ficha no publicó un PDF enlazado")
        response = self.get(concept.url_pdf)
        payload = response.content
        if not payload.startswith(PDF_MAGIC):
            raise ValueError("La respuesta enlazada no tiene la firma PDF")
        filename = _safe_filename(concept.nombre_archivo or Path(urlparse(concept.url_pdf).path).name or "documento.pdf")
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        path = destination / filename
        # URL/PDF hashes prevent a duplicate response from being retained twice.
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != hashlib.sha256(payload).hexdigest():
            path = destination / f"{hashlib.sha256(payload).hexdigest()[:12]}_{filename}"
        path.write_bytes(payload)
        try:
            reader = PdfReader(path)
            pages = len(reader.pages)
            # This is only a coverage measurement, not persisted extraction (milestone 3).
            concept.texto_extraible = len("".join((page.extract_text() or "") for page in reader.pages).strip()) >= 100
        except Exception as error:
            raise ValueError(f"PDF no legible por pypdf: {error}") from error
        concept.nombre_archivo = path.name
        concept.tamano_bytes = len(payload)
        concept.numero_paginas = pages
        concept.sha256 = hashlib.sha256(payload).hexdigest()
        concept.pdf_valido = True
        return concept


def _field_value(raw: str | None) -> str | None:
    if not raw:
        return None
    return re.sub(r"^(Tema|Sub Tema)\s*", "", raw, flags=re.I).strip() or None


def _first_date(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def _extract_radicado(text: str) -> str | None:
    match = re.search(r"(?<!\d)\d{1,2}[-_]20\d{2}[-_]\d{2,}(?=$|[^\d])", text)
    return match.group(0).replace("_", "-") if match else None


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "documento.pdf"


def _pick_diverse(candidates: Iterable[dict[str, object]], limit: int) -> list[dict[str, object]]:
    """Include each published year before filling by subject diversity."""
    unique: dict[str, dict[str, object]] = {str(row["url_ficha"]): row for row in candidates}
    newest_first = sorted(
        unique.values(),
        key=lambda row: (row.get("anio") is not None, row.get("anio") or 0, str(row.get("titulo") or "")),
        reverse=True,
    )
    chosen: list[dict[str, object]] = []
    years: set[object] = set()
    topics: set[object] = set()
    # Establish a genuine historical sample first (oldest and newest available).
    for candidate in newest_first:
        if len(chosen) == limit:
            break
        year = candidate.get("anio")
        if year is not None and year not in years:
            chosen.append(candidate); years.add(year); topics.add(candidate.get("tema"))
    for candidate in newest_first:
        if len(chosen) == limit:
            break
        year, topic = candidate.get("anio"), candidate.get("tema")
        if (year not in years or topic not in topics) and candidate not in chosen:
            chosen.append(candidate); years.add(year); topics.add(topic)
    for candidate in newest_first:
        if len(chosen) == limit:
            break
        if candidate not in chosen:
            chosen.append(candidate)
    return chosen


def write_report(concepts: list[Concept], errors: list[dict[str, str]], reports_dir: Path) -> dict[str, object]:
    valid = [item for item in concepts if item.pdf_valido and item.tamano_bytes is not None]
    sizes = [item.tamano_bytes for item in valid]
    pages = [item.numero_paginas for item in valid if item.numero_paginas is not None]
    total = sum(sizes)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "documentos_validos": len(valid),
        "tamano_total_bytes": total, "tamano_promedio_bytes": round(statistics.mean(sizes), 2) if sizes else None,
        "tamano_mediana_bytes": statistics.median(sizes) if sizes else None, "tamano_minimo_bytes": min(sizes) if sizes else None,
        "tamano_maximo_bytes": max(sizes) if sizes else None, "paginas_totales": sum(pages),
        "paginas_promedio": round(statistics.mean(pages), 2) if pages else None,
        "porcentaje_texto_extraible": round(100 * sum(item.texto_extraible is True for item in valid) / len(valid), 2) if valid else None,
        "pdfs_problematicos": [error for error in errors if "PDF" in error["error"] and "no publicó" not in error["error"]],
        "fichas_sin_pdf_publicado": sum("no publicó un PDF" in error["error"] for error in errors),
        "proyeccion_200_pdfs_bytes": round(total / len(valid) * 200) if valid else None,
        "proyeccion_2800_pdfs_bytes": round(total / len(valid) * 2800) if valid else None,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "pilot_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# Reporte del corpus piloto",
        "",
        f"- PDFs válidos: {len(valid)}",
        f"- Tamaño total: {total:,} bytes",
        f"- Tamaño promedio: {result['tamano_promedio_bytes']:,} bytes" if sizes else "- Sin PDFs válidos",
        f"- Mediana: {result['tamano_mediana_bytes']:,} bytes" if sizes else "- Mediana: n/a",
        f"- Mínimo: {result['tamano_minimo_bytes']:,} bytes" if sizes else "- Mínimo: n/a",
        f"- Máximo: {result['tamano_maximo_bytes']:,} bytes" if sizes else "- Máximo: n/a",
        f"- Páginas totales: {sum(pages):,}",
        f"- Páginas promedio: {result['paginas_promedio']}",
        f"- Texto extraíble: {result['porcentaje_texto_extraible']}%",
        f"- PDFs problemáticos: {len(result['pdfs_problematicos'])}",
        f"- Fichas revisadas sin PDF publicado: {result['fichas_sin_pdf_publicado']}",
        f"- Proyección 200 PDFs: {result['proyeccion_200_pdfs_bytes']:,} bytes",
        f"- Proyección 2.800 PDFs: {result['proyeccion_2800_pdfs_bytes']:,} bytes",
    ]
    (reports_dir / "pilot_report.md").write_text("\n".join(lines) + "\n")
    return result


def load_existing(metadata_file: Path) -> list[Concept]:
    if not metadata_file.exists():
        return []
    records: list[Concept] = []
    for line in metadata_file.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        item.setdefault("texto_extraible", None)
        pdf_name = Path(urlparse(str(item.get("url_pdf") or "")).path).name
        pdf_radicado = _extract_radicado(pdf_name)
        if pdf_radicado:
            item["radicado"] = pdf_radicado
        records.append(Concept(**item))
    return records


def write_metadata(metadata_file: Path, concepts: list[Concept]) -> None:
    temporary_file = metadata_file.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as output:
        for item in concepts:
            output.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
    temporary_file.replace(metadata_file)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--catalogue-pages", type=int, default=5, help="Páginas públicas a consultar por término de búsqueda")
    parser.add_argument("--terms", default=",".join(SEED_TERMS),
                        help="Términos públicos del catálogo, separados por comas")
    parser.add_argument("--max-candidates", type=int, default=None,
                        help="Máximo de fichas a revisar; evita recorridos extensos de fichas sin PDF")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    raw_dir, metadata_dir, reports_dir = args.data_dir / "raw" / "pdf", args.data_dir / "metadata", args.data_dir / "reports"
    raw_dir.mkdir(parents=True, exist_ok=True); metadata_dir.mkdir(parents=True, exist_ok=True)
    crawler, candidates, errors = PublicCatalogueCrawler(args.delay), [], []
    metadata_file = metadata_dir / "concepts.jsonl"
    saved = load_existing(metadata_file)
    known_fichas = {item.url_ficha for item in saved}
    known_hashes = {item.sha256 for item in saved if item.sha256}
    if len(saved) > args.limit:
        saved = saved[:args.limit]
    terms = tuple(term.strip() for term in args.terms.split(",") if term.strip())
    if not terms:
        parser.error("--terms debe incluir al menos un término")
    if args.max_candidates is not None and args.max_candidates < 1:
        parser.error("--max-candidates debe ser al menos 1")
    for term in terms:
        for page in range(args.catalogue_pages):
            try:
                rows = crawler.catalogue_candidates(term, page)
                if not rows:
                    break
                candidates.extend(rows)
            except (requests.RequestException, TotalRequestTimeout) as error:
                errors.append({"stage": "catalogue", "item": f"{term} / página {page}", "error": str(error)})
    candidate_limit = args.max_candidates or max(args.limit * 6, 300)
    for candidate in _pick_diverse(candidates, candidate_limit):
        if len(saved) >= args.limit: break
        if str(candidate["url_ficha"]) in known_fichas:
            continue
        try:
            concept = crawler.download_pdf(crawler.detail(candidate), raw_dir)
            if concept.sha256 in known_hashes:
                continue
            saved.append(concept)
            known_fichas.add(concept.url_ficha)
            known_hashes.add(concept.sha256)
            write_metadata(metadata_file, saved)
            print(f"OK {len(saved):02d}/{args.limit}: {concept.nombre_archivo} ({concept.numero_paginas} páginas)")
        except (requests.RequestException, TotalRequestTimeout, ValueError) as error:
            errors.append({"stage": "detail_or_download", "item": str(candidate["url_ficha"]), "error": str(error)})
            print(f"ERROR: {candidate['url_ficha']}: {error}")
    write_metadata(metadata_file, saved)
    (metadata_dir / "crawl_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2) + "\n")
    report = write_report(saved, errors, reports_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if len(saved) == args.limit else 2


if __name__ == "__main__":
    raise SystemExit(main())
