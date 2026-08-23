#!/usr/bin/env python3
"""Local web interface for the source-grounded Concepthia draft workflow."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from http import HTTPStatus
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus
from wsgiref.simple_server import make_server

from .answer import make_sources, provider_from_env, retrieve


MAX_BODY_BYTES = 8_000
STATIC_DIR = Path(__file__).parent / "static"
LOGGER = logging.getLogger(__name__)
MONTHS_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def display_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return f"{parsed.day} de {MONTHS_ES[parsed.month - 1]} de {parsed.year}"


def jurisprudence_links(question: str) -> list[dict[str, str]]:
    """Prepare traceable searches in the official court repositories."""
    encoded = quote_plus(question)
    return [
        {
            "court": "Corte Constitucional",
            "label": "Buscar providencias en la Relatoría",
            "url": f"https://www.corteconstitucional.gov.co/relatoria/buscador-jurisprudencia?texto={encoded}",
            "coverage": "Providencias publicadas desde 1992",
        },
        {
            "court": "Consejo de Estado",
            "label": "Buscar decisiones en Mi Relatoría",
            "url": "https://consejodeestado.gov.co/buscador-de-jurisprudencia2/",
            "coverage": "Decisiones tituladas desde el 1 de diciembre de 2021 y buscador histórico",
        },
    ]


def json_response(start_response: Callable, status: HTTPStatus, body: dict[str, object]) -> list[bytes]:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    start_response(f"{status.value} {status.phrase}", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(payload))),
        ("Cache-Control", "no-store"),
    ])
    return [payload]


def static_response(start_response: Callable, filename: str) -> list[bytes]:
    path = STATIC_DIR / filename
    if not path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"No encontrado"]
    payload = path.read_bytes()
    content_type = "text/css; charset=utf-8" if path.suffix == ".css" else "text/html; charset=utf-8"
    start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(payload)))])
    return [payload]


def app(data_dir: Path):
    def application(environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method, path = str(environ.get("REQUEST_METHOD")), str(environ.get("PATH_INFO"))
        if method == "GET" and path in ("/", "/index.html"):
            return static_response(start_response, "index.html")
        if method == "GET" and path == "/styles.css":
            return static_response(start_response, "styles.css")
        if method != "POST" or path != "/api/answer":
            return json_response(start_response, HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
        try:
            length = int(str(environ.get("CONTENT_LENGTH") or "0"))
        except ValueError:
            length = MAX_BODY_BYTES + 1
        if length < 1 or length > MAX_BODY_BYTES:
            return json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "La solicitud debe tener entre 1 y 8.000 bytes."})
        try:
            request = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
            question = request.get("question", "").strip()
            review_jurisprudence = request.get("review_jurisprudence") is True
            radicado = str(request.get("radicado", "")).strip() or "{{RADICADO}}"
            fecha = display_date(str(request.get("fecha", "")).strip()) or "{{FECHA}}"
            destinatario = str(request.get("destinatario", "")).strip() or "{{DESTINATARIO}}"
            subdirector = str(request.get("subdirector", "")).strip() or "{{SUBDIRECTOR}}"
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Solicitud inválida."})
        if not 3 <= len(question) <= 1_500:
            return json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Escribe una pregunta de 3 a 1.500 caracteres."})
        if any(len(value) > 160 for value in (radicado, fecha, destinatario, subdirector)):
            return json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Los datos del oficio son demasiado largos."})
        try:
            results = retrieve(data_dir / "index" / "chunks.jsonl", question, top_chunks=6)
        except FileNotFoundError:
            return json_response(start_response, HTTPStatus.SERVICE_UNAVAILABLE, {"error": "No existe el índice local. Ejecuta primero el comando de build."})
        if not results:
            return json_response(start_response, HTTPStatus.OK, {"answer": None, "sources": [], "message": "No encontré evidencia suficiente en el corpus local."})
        sources = make_sources(results)
        drafting_request = (
            f"Consulta sustantiva: {question}\nRadicado: {radicado}\nFecha: {fecha}\n"
            f"Destinatario: {destinatario}\nSubdirector Jurídico: {subdirector}"
        )
        try:
            draft = provider_from_env().draft(drafting_request, sources)
        except RuntimeError as error:
            return json_response(start_response, HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error), "sources": sources})
        except Exception:
            LOGGER.exception("Fallo inesperado al generar el borrador")
            return json_response(start_response, HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": "La consulta se interrumpió inesperadamente. Intenta nuevamente en unos segundos.",
                "sources": sources,
            })
        return json_response(start_response, HTTPStatus.OK, {
            "answer": draft, "sources": sources,
            "jurisprudence": jurisprudence_links(question) if review_jurisprudence else [],
            "warning": "Borrador informativo: requiere revisión humana; no constituye asesoría jurídica.",
        })
    return application


def main() -> int:
    parser = argparse.ArgumentParser(description="Interfaz web local de Concepthia")
    parser.add_argument("--host", default="127.0.0.1", help="Por seguridad, el valor predeterminado es localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    with make_server(args.host, args.port, app(args.data_dir)) as server:
        print(f"Concepthia disponible en http://{args.host}:{args.port}")
        print("Pulsa Ctrl+C para detener el servidor.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
