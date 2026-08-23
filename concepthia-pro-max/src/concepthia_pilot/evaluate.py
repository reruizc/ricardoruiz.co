#!/usr/bin/env python3
"""Run transparent retrieval checks against a small, versioned evaluation set."""
from __future__ import annotations

import argparse
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .answer import retrieve


def load_cases(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("El archivo de evaluación debe ser una lista no vacía")
    return data


def is_relevant(title: str | None, required_terms: list[object]) -> bool:
    def normalize(value: object) -> str:
        decomposed = unicodedata.normalize("NFD", str(value).upper())
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    normalized = normalize(title or "")
    return all(normalize(term) in normalized for term in required_terms)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa la recuperación local de Concepthia")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--cases", type=Path, default=Path("data/evals/retrieval_cases.json"))
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k debe ser al menos 1")
    cases = load_cases(args.cases)
    results = []
    for case in cases:
        retrieved = retrieve(args.data_dir / "index" / "chunks.jsonl", str(case["consulta"]), top_chunks=args.top_k * 4)
        documents: list[dict[str, object]] = []
        seen_hashes: set[str] = set()
        for result in retrieved:
            if result.chunk.sha256_pdf in seen_hashes:
                continue
            seen_hashes.add(result.chunk.sha256_pdf)
            documents.append({"titulo": result.chunk.titulo, "pagina": result.chunk.pagina, "url_ficha": result.chunk.url_ficha})
            if len(documents) == args.top_k:
                break
        rank = next((position for position, document in enumerate(documents, start=1)
                     if is_relevant(str(document["titulo"]), list(case["debe_aparecer_en_titulo"]))), None)
        results.append({"id": case["id"], "consulta": case["consulta"], "relevante_en_rango": rank,
                        "ok_top_k": rank is not None, "documentos": documents})
    hit_rate = sum(item["ok_top_k"] for item in results) / len(results)
    report = {"generado_en": datetime.now(timezone.utc).isoformat(), "motor": "BM25 local",
              "casos": len(results), "top_k": args.top_k, "hit_rate_top_k": round(hit_rate, 4), "resultados": results}
    output = args.data_dir / "reports" / "retrieval_evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if hit_rate == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
