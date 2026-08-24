#!/usr/bin/env python3
"""Extract page-aware text from the locally validated DASCD PDF corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pypdf
from pypdf import PdfReader


MIN_PAGE_CHARS = 40
MIN_DOCUMENT_CHARS = 200
MIN_TEXT_PAGE_RATIO = 0.8


@dataclass
class ExtractionRecord:
    id: str | None
    radicado: str | None
    nombre_archivo_pdf: str
    sha256_pdf: str
    ruta_texto: str | None
    sha256_texto: str | None
    motor_extraccion: str
    version_motor: str
    extraido_en: str
    paginas_totales: int
    paginas_con_texto: int
    proporcion_paginas_con_texto: float
    caracteres_extraidos: int
    palabras_extraidas: int
    requiere_ocr: bool
    motivo_ocr: str | None
    estado: str
    error: str | None


def load_corpus(metadata_file: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in metadata_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def extraction_filename(pdf_filename: str) -> str:
    return f"{Path(pdf_filename).stem}.txt"


def extract_document(record: dict[str, object], raw_dir: Path, text_dir: Path) -> ExtractionRecord:
    filename = str(record["nombre_archivo"])
    pdf_path = raw_dir / filename
    extracted_at = datetime.now(timezone.utc).isoformat()
    try:
        pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        expected_hash = str(record.get("sha256") or "")
        if expected_hash and pdf_hash != expected_hash:
            raise ValueError("El SHA-256 local no coincide con metadata del crawler")

        reader = PdfReader(pdf_path)
        page_contents: list[str] = []
        text_page_count = 0
        character_count = 0
        word_count = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").replace("\x00", "").strip()
            if len(text) >= MIN_PAGE_CHARS:
                text_page_count += 1
            character_count += len(text)
            word_count += len(text.split())
            page_contents.append(f"--- PÁGINA {page_number} ---\n{text}\n")

        content = "\n".join(page_contents).rstrip() + "\n"
        page_count = len(page_contents)
        text_page_ratio = round(text_page_count / page_count, 4) if page_count else 0.0
        ocr_reasons = []
        if character_count < MIN_DOCUMENT_CHARS:
            ocr_reasons.append(f"menos de {MIN_DOCUMENT_CHARS} caracteres")
        if text_page_ratio < MIN_TEXT_PAGE_RATIO:
            ocr_reasons.append(f"texto útil en menos del {int(MIN_TEXT_PAGE_RATIO * 100)}% de páginas")

        output_path = text_dir / extraction_filename(filename)
        atomic_write_text(output_path, content)
        text_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ExtractionRecord(
            id=record.get("id"), radicado=record.get("radicado"), nombre_archivo_pdf=filename,
            sha256_pdf=pdf_hash, ruta_texto=str(output_path), sha256_texto=text_hash,
            motor_extraccion="pypdf", version_motor=pypdf.__version__, extraido_en=extracted_at,
            paginas_totales=page_count, paginas_con_texto=text_page_count,
            proporcion_paginas_con_texto=text_page_ratio, caracteres_extraidos=character_count,
            palabras_extraidas=word_count, requiere_ocr=bool(ocr_reasons),
            motivo_ocr="; ".join(ocr_reasons) or None, estado="ok", error=None,
        )
    except Exception as error:
        return ExtractionRecord(
            id=record.get("id"), radicado=record.get("radicado"), nombre_archivo_pdf=filename,
            sha256_pdf=str(record.get("sha256") or ""), ruta_texto=None, sha256_texto=None,
            motor_extraccion="pypdf", version_motor=pypdf.__version__, extraido_en=extracted_at,
            paginas_totales=int(record.get("numero_paginas") or 0), paginas_con_texto=0,
            proporcion_paginas_con_texto=0.0, caracteres_extraidos=0, palabras_extraidas=0,
            requiere_ocr=True, motivo_ocr="falló la extracción determinística", estado="error", error=str(error),
        )


def write_jsonl(path: Path, records: list[ExtractionRecord]) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    temporary.replace(path)


def load_extractions(path: Path) -> dict[str, ExtractionRecord]:
    if not path.exists():
        return {}
    records = (ExtractionRecord(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {record.nombre_archivo_pdf: record for record in records}


def reusable_extraction(record: ExtractionRecord | None, concept: dict[str, object], text_dir: Path) -> bool:
    if record is None or record.estado != "ok" or record.sha256_pdf != str(concept.get("sha256") or ""):
        return False
    text_path = text_dir / extraction_filename(record.nombre_archivo_pdf)
    if not text_path.is_file() or not record.sha256_texto:
        return False
    return hashlib.sha256(text_path.read_bytes()).hexdigest() == record.sha256_texto


def build_report(records: list[ExtractionRecord]) -> dict[str, object]:
    successful = [record for record in records if record.estado == "ok"]
    ocr_candidates = [record for record in records if record.requiere_ocr]
    total_pages = sum(record.paginas_totales for record in records)
    text_pages = sum(record.paginas_con_texto for record in records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documentos_procesados": len(records),
        "documentos_extraidos": len(successful),
        "documentos_con_error": len(records) - len(successful),
        "paginas_procesadas": total_pages,
        "paginas_con_texto": text_pages,
        "caracteres_extraidos": sum(record.caracteres_extraidos for record in records),
        "palabras_extraidas": sum(record.palabras_extraidas for record in records),
        "porcentaje_documentos_extraidos": round(100 * len(successful) / len(records), 2) if records else None,
        "porcentaje_paginas_con_texto": round(100 * text_pages / total_pages, 2) if total_pages else None,
        "candidatos_ocr": len(ocr_candidates),
        "archivos_candidatos_ocr": [record.nombre_archivo_pdf for record in ocr_candidates],
        "errores": [
            {"nombre_archivo_pdf": record.nombre_archivo_pdf, "error": record.error}
            for record in records if record.estado == "error"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    raw_dir = args.data_dir / "raw" / "pdf"
    text_dir = args.data_dir / "extracted" / "text"
    metadata_dir = args.data_dir / "metadata"
    reports_dir = args.data_dir / "reports"
    text_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(metadata_dir / "concepts.jsonl")
    extraction_file = metadata_dir / "extractions.jsonl"
    previous = load_extractions(extraction_file)
    records: list[ExtractionRecord] = []
    for index, concept in enumerate(corpus, start=1):
        filename = str(concept["nombre_archivo"])
        cached = previous.get(filename)
        if reusable_extraction(cached, concept, text_dir):
            result = cached
            state = "CACHE"
        else:
            result = extract_document(concept, raw_dir, text_dir)
            state = result.estado.upper()
        records.append(result)
        write_jsonl(extraction_file, records)
        print(f"{state} {index:03d}/{len(corpus)}: {result.nombre_archivo_pdf} ({result.caracteres_extraidos:,} caracteres)")

    report = build_report(records)
    atomic_write_text(reports_dir / "extraction_report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    markdown = [
        "# Reporte de extracción", "",
        f"- Documentos procesados: {report['documentos_procesados']}",
        f"- Documentos extraídos: {report['documentos_extraidos']}",
        f"- Páginas procesadas: {report['paginas_procesadas']}",
        f"- Páginas con texto: {report['paginas_con_texto']} ({report['porcentaje_paginas_con_texto']}%)",
        f"- Caracteres extraídos: {report['caracteres_extraidos']:,}",
        f"- Palabras extraídas: {report['palabras_extraidas']:,}",
        f"- Candidatos a OCR: {report['candidatos_ocr']}",
        f"- Errores: {report['documentos_con_error']}",
    ]
    atomic_write_text(reports_dir / "extraction_report.md", "\n".join(markdown) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["documentos_con_error"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
