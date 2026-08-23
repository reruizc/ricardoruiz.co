"""Create a Lambda-friendly Corte Constitucional retrieval index.

The complete chunk bank stays in S3 for reproducibility.  This companion file
stores a representative excerpt per decision, making interactive retrieval fast
enough for a serverless request.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


def compact_text(text: str, word_limit: int = 1_800) -> str:
    return " ".join(text.split()[:word_limit])


def build(source: Path, output: Path, word_limit: int) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with gzip.open(source, "rt", encoding="utf-8") as input_handle, gzip.open(output, "wt", encoding="utf-8") as output_handle:
        for raw in input_handle:
            row = json.loads(raw)
            row["texto"] = compact_text(str(row.get("texto", "")), word_limit)
            row["temas"] = compact_text(str(row.get("temas", "")), 400)
            output_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Compacta providencias para búsqueda serverless")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--word-limit", type=int, default=1_800)
    args = parser.parse_args()
    print(f"Providencias compactadas: {build(args.source, args.output, args.word_limit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
