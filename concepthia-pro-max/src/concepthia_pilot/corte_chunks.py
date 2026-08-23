#!/usr/bin/env python3
"""Turn the official Corte corpus into page-independent, citable BM25 chunks."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from .retrieval import MIN_INDEXABLE_WORDS, split_words


def build(source: Path, output: Path, chunk_words: int, overlap_words: int) -> dict[str, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    documents = chunks = words = 0
    with gzip.open(source, "rt", encoding="utf-8") as incoming, gzip.open(output, "wt", encoding="utf-8") as outgoing:
        for raw in incoming:
            document = json.loads(raw)
            documents += 1
            for position, text in enumerate(split_words(document["texto"], chunk_words, overlap_words), start=1):
                count = len(text.split())
                if count < MIN_INDEXABLE_WORDS:
                    continue
                identifier = f"{document['sentencia']}:{position}:{chunk_words}:{overlap_words}"
                outgoing.write(json.dumps({
                    "chunk_id": hashlib.sha256(identifier.encode()).hexdigest()[:24],
                    "id": document["id"], "court": document["court"], "sentencia": document["sentencia"],
                    "fecha": document["fecha"], "magistrado": document["magistrado"], "sala": document["sala"],
                    "tipo": document["tipo"], "url": document["url"], "temas": document["temas"],
                    "posicion": position, "palabras": count, "texto": text,
                }, ensure_ascii=False) + "\n")
                chunks += 1
                words += count
    return {"documentos": documents, "chunks": chunks, "palabras_en_chunks": words}


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera chunks citables del corpus de la Corte Constitucional")
    parser.add_argument("--source", type=Path, default=Path("data/jurisprudence/corte-documents-pilot-500.jsonl.gz"))
    parser.add_argument("--output", type=Path, default=Path("data/jurisprudence/corte-chunks-pilot-500.jsonl.gz"))
    parser.add_argument("--chunk-words", type=int, default=260)
    parser.add_argument("--overlap-words", type=int, default=50)
    parser.add_argument("--s3-uri")
    args = parser.parse_args()
    if not args.source.is_file() or args.chunk_words <= args.overlap_words or args.overlap_words < 0:
        parser.error("Revisa --source, --chunk-words y --overlap-words.")
    report = build(args.source, args.output, args.chunk_words, args.overlap_words)
    report.update({"source": str(args.source), "output": str(args.output), "chunk_words": args.chunk_words, "overlap_words": args.overlap_words})
    print(json.dumps(report, ensure_ascii=False))
    if args.s3_uri:
        import subprocess
        subprocess.run(["aws", "s3", "cp", str(args.output), args.s3_uri], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
