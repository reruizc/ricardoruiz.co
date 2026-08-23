"""Local BM25 retrieval for the compact Corte Constitucional corpus."""
from __future__ import annotations

from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path

from .retrieval import BM25Index, Chunk


DEFAULT_INDEX = Path("data/jurisprudence/corte-chunks-pilot-500.jsonl.gz")


@lru_cache(maxsize=1)
def _index(path_text: str) -> BM25Index:
    path = Path(path_text)
    chunks: list[Chunk] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            row = json.loads(raw)
            sentence = str(row["sentencia"])
            chunks.append(Chunk(
                chunk_id=str(row["chunk_id"]), concept_id=str(row["id"]), radicado=sentence,
                anio=int(str(row["fecha"])[:4]), titulo=f"Corte Constitucional · Sentencia {sentence}",
                tema=str(row.get("temas", "")), subtema=str(row.get("sala", "")), pagina=int(row["posicion"]),
                posicion_en_pagina=int(row["posicion"]), texto=str(row["texto"]), palabras=int(row["palabras"]),
                nombre_archivo_pdf=sentence, sha256_pdf=hashlib.sha256(sentence.encode()).hexdigest(),
                url_ficha=str(row["url"]), url_pdf=str(row["url"]),
            ))
    return BM25Index(chunks)


def search_corte_constitucional(question: str, path: Path = DEFAULT_INDEX, limit: int = 5) -> tuple[dict[str, str], ...]:
    """Return distinct official decisions; an unavailable local pilot is non-fatal."""
    if not path.is_file():
        return ()
    results = _index(str(path)).search(question, limit=limit * 5)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in results:
        chunk = result.chunk
        if not chunk.radicado or chunk.radicado in seen:
            continue
        seen.add(chunk.radicado)
        rows.append({
            "court": "Corte Constitucional", "sentencia": chunk.radicado,
            "label": f"Sentencia {chunk.radicado}", "url": chunk.url_ficha,
            "coverage": str(chunk.anio), "summary": chunk.texto[:700], "sala": chunk.subtema or "",
        })
        if len(rows) == limit:
            break
    return tuple(rows)


def as_evidence(results: tuple[dict[str, str], ...]) -> list[dict[str, object]]:
    return [{
        "id": f"CC {row['sentencia']}", "radicado": row["sentencia"], "chunk_id": None, "score": None,
        "titulo": f"Corte Constitucional · Sentencia {row['sentencia']}", "pagina": "s. p.",
        "url_ficha": row["url"], "url_pdf": row["url"], "texto": row["summary"],
    } for row in results]
