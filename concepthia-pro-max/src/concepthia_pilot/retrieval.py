#!/usr/bin/env python3
"""Build and query a small page-aware BM25 index for the local corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PAGE_PATTERN = re.compile(r"--- PÁGINA (\d+) ---\n(.*?)(?=\n--- PÁGINA \d+ ---|\Z)", re.DOTALL)
TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]+", re.IGNORECASE)
DEFAULT_CHUNK_WORDS = 220
DEFAULT_OVERLAP_WORDS = 40
MIN_INDEXABLE_WORDS = 40
SMOKE_QUERIES = (
    "vacaciones por incapacidad superior a 180 días",
    "prima técnica estudios experiencia profesional",
    "teletrabajo",
)
SPANISH_STOPWORDS = {
    "a", "al", "ante", "como", "con", "de", "del", "el", "en", "entre", "es", "esta", "la", "las",
    "lo", "los", "o", "para", "por", "que", "se", "sin", "su", "sus", "un", "una", "y",
    "cómo", "cuál", "cuáles", "cuándo", "qué", "funciona", "funcionan", "aplica", "aplican",
    "ocurre", "pasa", "puede", "pueden", "luego", "reglas", "superar",
}


@dataclass
class Chunk:
    chunk_id: str
    concept_id: str | None
    radicado: str | None
    anio: int | None
    titulo: str | None
    tema: str | None
    subtema: str | None
    pagina: int
    posicion_en_pagina: int
    texto: str
    palabras: int
    nombre_archivo_pdf: str
    sha256_pdf: str
    url_ficha: str
    url_pdf: str


@dataclass
class SearchResult:
    score: float
    chunk: Chunk


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in SPANISH_STOPWORDS]


def searchable_text(chunk: Chunk) -> str:
    metadata = " ".join(filter(None, [chunk.titulo, chunk.tema, chunk.subtema]))
    return f"{metadata} {metadata} {metadata} {chunk.texto}"


def normalize_page_text(text: str) -> str:
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_words(text: str, chunk_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if chunk_words <= overlap_words:
        raise ValueError("chunk_words debe ser mayor que overlap_words")
    step = chunk_words - overlap_words
    chunks = []
    for start in range(0, len(words), step):
        if start and len(words) - start <= overlap_words:
            break
        chunks.append(" ".join(words[start:start + chunk_words]))
    return chunks


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_chunks(data_dir: Path, chunk_words: int, overlap_words: int) -> list[Chunk]:
    concepts = load_jsonl(data_dir / "metadata" / "concepts.jsonl")
    extractions = load_jsonl(data_dir / "metadata" / "extractions.jsonl")
    extraction_by_pdf = {str(row["nombre_archivo_pdf"]): row for row in extractions}
    chunks: list[Chunk] = []
    for concept in concepts:
        filename = str(concept["nombre_archivo"])
        extraction = extraction_by_pdf.get(filename)
        if not extraction or extraction.get("estado") != "ok" or not extraction.get("ruta_texto"):
            continue
        content = Path(str(extraction["ruta_texto"])).read_text(encoding="utf-8")
        for page_match in PAGE_PATTERN.finditer(content):
            page_number = int(page_match.group(1))
            page_text = normalize_page_text(page_match.group(2))
            for position, chunk_text in enumerate(split_words(page_text, chunk_words, overlap_words), start=1):
                if len(chunk_text.split()) < MIN_INDEXABLE_WORDS:
                    continue
                chunk_key = f"{concept['sha256']}:{page_number}:{position}:{chunk_words}:{overlap_words}"
                chunks.append(Chunk(
                    chunk_id=hashlib.sha256(chunk_key.encode()).hexdigest()[:24],
                    concept_id=concept.get("id"), radicado=concept.get("radicado"), anio=concept.get("anio"),
                    titulo=concept.get("titulo"), tema=concept.get("tema"), subtema=concept.get("subtema"),
                    pagina=page_number, posicion_en_pagina=position, texto=chunk_text,
                    palabras=len(chunk_text.split()), nombre_archivo_pdf=filename,
                    sha256_pdf=str(concept["sha256"]), url_ficha=str(concept["url_ficha"]),
                    url_pdf=str(concept["url_pdf"]),
                ))
    return chunks


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(path)


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(searchable_text(chunk))) for chunk in chunks]
        self.lengths = [sum(frequencies.values()) for frequencies in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            document_frequency.update(frequencies.keys())
        total = len(chunks)
        self.idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query_terms or not self.chunks:
            return []
        scores: list[SearchResult] = []
        for chunk, frequencies, length in zip(self.chunks, self.term_frequencies, self.lengths):
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scores.append(SearchResult(score=score, chunk=chunk))
        return sorted(scores, key=lambda result: (-result.score, result.chunk.chunk_id))[:limit]


def aggregate_documents(results: list[SearchResult], limit: int) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for result in results:
        key = result.chunk.sha256_pdf
        if key not in grouped:
            grouped[key] = {
                "score": 0.0, "concept_id": result.chunk.concept_id, "radicado": result.chunk.radicado,
                "anio": result.chunk.anio, "titulo": result.chunk.titulo, "tema": result.chunk.tema,
                "subtema": result.chunk.subtema, "nombre_archivo_pdf": result.chunk.nombre_archivo_pdf,
                "url_ficha": result.chunk.url_ficha, "url_pdf": result.chunk.url_pdf, "fragmentos": [],
            }
        grouped[key]["fragmentos"].append({
            "chunk_id": result.chunk.chunk_id, "score": round(result.score, 6),
            "pagina": result.chunk.pagina, "texto": result.chunk.texto,
        })
    for document in grouped.values():
        fragment_scores = sorted((float(fragment["score"]) for fragment in document["fragmentos"]), reverse=True)
        document["score"] = round(fragment_scores[0] + 0.2 * sum(fragment_scores[1:]), 6)
    return sorted(grouped.values(), key=lambda row: (-float(row["score"]), str(row["nombre_archivo_pdf"])))[:limit]


def build_command(args: argparse.Namespace) -> int:
    chunks = build_chunks(args.data_dir, args.chunk_words, args.overlap_words)
    index_dir = args.data_dir / "index"
    atomic_write_jsonl(index_dir / "chunks.jsonl", (asdict(chunk) for chunk in chunks))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "documentos_indexados": len({chunk.sha256_pdf for chunk in chunks}),
        "paginas_indexadas": len({(chunk.sha256_pdf, chunk.pagina) for chunk in chunks}), "chunks": len(chunks),
        "palabras_por_chunk_objetivo": args.chunk_words, "solapamiento_palabras": args.overlap_words,
        "minimo_palabras_indexables": MIN_INDEXABLE_WORDS,
        "palabras_totales_en_chunks": sum(chunk.palabras for chunk in chunks),
    }
    (index_dir / "index_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["documentos_indexados"] else 2


def search_command(args: argparse.Namespace) -> int:
    chunks = [Chunk(**row) for row in load_jsonl(args.data_dir / "index" / "chunks.jsonl")]
    index = BM25Index(chunks)
    chunk_results = index.search(args.query, limit=max(args.top_chunks, args.top_documents) * 3)
    documents = aggregate_documents(chunk_results[:args.top_chunks], args.top_documents)
    response = {"consulta": args.query, "documentos": documents}
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print(f"Consulta: {args.query}\n")
        for position, document in enumerate(documents, start=1):
            print(f"{position}. [{document['score']:.4f}] {document['titulo']} ({document['anio'] or 'año n/d'})")
            print(f"   Tema: {document['tema'] or 'n/d'} / {document['subtema'] or 'n/d'}")
            print(f"   Fuente: {document['url_ficha']}")
            for fragment in document["fragmentos"][:2]:
                preview = str(fragment["texto"])[:320].replace("\n", " ")
                print(f"   p. {fragment['pagina']} [{fragment['score']:.4f}]: {preview}…")
            print()
    return 0 if documents else 1


def smoke_command(args: argparse.Namespace) -> int:
    chunks = [Chunk(**row) for row in load_jsonl(args.data_dir / "index" / "chunks.jsonl")]
    index = BM25Index(chunks)
    evaluations = []
    for query in SMOKE_QUERIES:
        results = index.search(query, limit=12)
        documents = aggregate_documents(results, 3)
        evaluations.append({
            "consulta": query,
            "resultados": [{
                "posicion": position,
                "score": document["score"],
                "titulo": document["titulo"],
                "tema": document["tema"],
                "url_ficha": document["url_ficha"],
                "pagina_principal": document["fragmentos"][0]["pagina"],
            } for position, document in enumerate(documents, start=1)],
        })
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "motor": "BM25 local",
        "consultas": evaluations,
    }
    reports_dir = args.data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "retrieval_smoke_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = ["# Pruebas de retrieval BM25", ""]
    for evaluation in evaluations:
        markdown.extend([f"## {evaluation['consulta']}", ""])
        for result in evaluation["resultados"]:
            markdown.append(
                f"{result['posicion']}. **{result['titulo']}** - score {result['score']} - "
                f"página {result['pagina_principal']} - {result['url_ficha']}"
            )
        markdown.append("")
    (reports_dir / "retrieval_smoke_report.md").write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(evaluation["resultados"] for evaluation in evaluations) else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    build_parser.add_argument("--overlap-words", type=int, default=DEFAULT_OVERLAP_WORDS)
    build_parser.set_defaults(handler=build_command)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-documents", type=int, default=5)
    search_parser.add_argument("--top-chunks", type=int, default=12)
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(handler=search_command)
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.set_defaults(handler=smoke_command)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
