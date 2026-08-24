"""AWS Lambda adapter for the ConcepthIA WSGI application.

The source indices remain in S3.  Each warm Lambda environment caches the two
compact retrieval files in /tmp, so the original PDF corpus is never deployed.
"""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any

import boto3

from concepthia_pilot.web import app


DATA_DIR = Path("/tmp/concepthia-data")
BUCKET = os.environ["CONCEPTHIA_S3_BUCKET"]
PREFIX = os.environ.get("CONCEPTHIA_S3_PREFIX", "ricardoruiz.co/concepthia-pro-max")
CORPUS_FILES = {
    "index/chunks.jsonl": "index/chunks.jsonl",
    "jurisprudence/corte-search-pilot-500.jsonl.gz": "jurisprudence/corte-search-pilot-500.jsonl.gz",
}
_application = None


def ensure_corpus() -> Path:
    """Download missing compact index files once per Lambda execution environment."""
    client = boto3.client("s3")
    for local_name, remote_name in CORPUS_FILES.items():
        target = DATA_DIR / local_name
        if target.is_file() and target.stat().st_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        client.download_file(BUCKET, f"{PREFIX}/{remote_name}", str(temporary))
        temporary.replace(target)
    return DATA_DIR


def application():
    global _application
    if _application is None:
        data_dir = ensure_corpus()
        os.environ.setdefault("CONCEPTHIA_CORTE_INDEX", str(data_dir / "jurisprudence/corte-search-pilot-500.jsonl.gz"))
        _application = app(data_dir)
    return _application


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Translate an API Gateway HTTP API v2 request to the small WSGI app."""
    request_context = event.get("requestContext", {}).get("http", {})
    method = request_context.get("method", "GET")
    path = event.get("rawPath") or request_context.get("path") or "/"
    raw_body = event.get("body") or ""
    body = base64.b64decode(raw_body) if event.get("isBase64Encoded") else raw_body.encode("utf-8")
    headers = {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}
    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": headers.get("content-length", str(len(body))),
        "CONTENT_TYPE": headers.get("content-type", ""),
        "wsgi.input": io.BytesIO(body),
        "wsgi.url_scheme": headers.get("x-forwarded-proto", "https"),
    }
    captured: dict[str, Any] = {}

    def start_response(status: str, response_headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    response_body = b"".join(application()(environ, start_response))
    response_headers = {key: value for key, value in captured["headers"]}
    content_type = response_headers.get("Content-Type", "")
    is_binary = "openxmlformats-officedocument" in content_type
    return {
        "statusCode": int(captured["status"].split(" ", 1)[0]),
        "headers": response_headers,
        "body": base64.b64encode(response_body).decode("ascii") if is_binary else response_body.decode("utf-8"),
        "isBase64Encoded": is_binary,
    }
