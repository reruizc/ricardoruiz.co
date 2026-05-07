#!/usr/bin/env python3
"""
Stop hook: detecta voseo en la última respuesta del asistente y bloquea el turno.
Si encuentra voseo, exit 2 + stderr con la lista de matches; Claude reescribe.
Si no, exit 0 (deja terminar normal).
"""
import json
import re
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    transcript_path = payload.get("transcript_path") or ""
    if not transcript_path:
        return 0
    p = Path(transcript_path)
    if not p.exists():
        return 0

    last_text = ""
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            content = entry.get("message", {}).get("content", []) or []
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    t = block.get("text", "")
                    if isinstance(t, str):
                        texts.append(t)
            if texts:
                last_text = "\n".join(texts)

    if not last_text.strip():
        return 0

    patterns = [
        r"\bvos\b",
        r"\b(?:tenés|querés|podés|sabés|hacés|hablás|trabajás|vivís|decís|venís)\b",
        r"\b(?:mirá|probá|andá|dejá|pegá|tomá|abrí|subí|bajá|escribí|escuchá|pensá|trabajá|sentate|fijate|vení|venite|mostrame)\b",
        r"\b(?:dejame|contame|avisame|mandame|decime|escribime|hablame|llamame|pasame)\b",
        r"\b(?:rindás|trabajés|mirés|probés|hablés|hagás)\b",
    ]
    rx = re.compile("|".join(patterns), re.IGNORECASE | re.UNICODE)
    matches = rx.findall(last_text)
    if not matches:
        return 0

    unique = sorted({m.lower() for m in matches})
    msg = (
        "VOSEO DETECTADO en tu respuesta anterior: "
        + ", ".join(unique)
        + "\n\nReescribe la respuesta COMPLETA en tuteo (tú) — el usuario vive en Bogotá y no usa voseo. "
        "Reemplaza imperativos -á/-é/-í (mirá→mira, probá→prueba, dejame→déjame), "
        "presente indicativo -ás/-és/-ís (tenés→tienes, querés→quieres, podés→puedes), "
        "y vos→tú. NO menciones esta corrección al usuario, solo entrega la versión corregida."
    )
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
