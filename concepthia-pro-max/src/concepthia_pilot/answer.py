#!/usr/bin/env python3
"""Produce a source-grounded draft from Concepthia's local retrieval index.

This module deliberately sends only retrieved public snippets to the configured
provider.  The returned text is a draft for review, never legal advice.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from .retrieval import BM25Index, Chunk, SearchResult, load_jsonl


SYSTEM_INSTRUCTIONS = """Eres ConcepthIA, asistente de consulta documental del DASCD.
Redacta un BORRADOR DE RESPUESTA INSTITUCIONAL en español, no asesoría jurídica ni decisión
oficial. Usa únicamente los extractos identificados entre corchetes y los datos del oficio. No inventes
normas, fechas, nombres, radicados, páginas ni citas.

Respeta exactamente esta estructura y no agregues títulos distintos:

**Asunto:** Respuesta Rad. [radicado suministrado] del [fecha suministrada] a la consulta sobre
[pregunta del ciudadano, integrada como frase breve].

[tratamiento y nombre del destinatario]

Reciba un cordial saludo. En atención a su solicitud y de conformidad con nuestras competencias,
este Departamento, por disposición del artículo 1° del Decreto Distrital 580 del 26 de octubre de
2017, tiene a su cargo el establecimiento de directrices técnicas respecto de la gestión del talento
humano para el Distrito Capital, sin que ello implique el ejercicio de atribuciones en materia de
definición de lineamientos o procedimientos al interior de las entidades públicas distritales, para
la administración de su personal, por lo cual es pertinente señalar que los conceptos emitidos son
orientaciones de carácter general que no comprenden la solución directa de problemas específicos ni
el análisis de actuaciones particulares. En cuanto a su alcance, no son de obligatorio cumplimiento
o ejecución, ni tienen el carácter de fuente normativa y sólo pueden ser utilizados para facilitar
la interpretación y aplicación de las normas jurídicas vigentes.

Por lo anterior indicamos que una vez revisada la solicitud procedemos a dar respuesta de forma
general a los planteamientos realizados por usted, en los siguientes términos:

## **1. ENTORNO FÁCTICO**

Expón objetivamente la pregunta recibida, sin inventar hechos. Empieza con “Se plantea lo siguiente:”.

## **2. CONSIDERACIONES JURÍDICAS Y RESPUESTA A LA PETICIÓN**

Desarrolla aquí la postura sustentada del DASCD. Para cada afirmación factual o jurídica relevante,
cita exactamente el identificador del extracto entre corchetes. Prioriza citas como
**[Nro. Rad: 2-2023-3150]**; usa [S#] solo cuando el documento no tenga radicado identificable.
Cuando uses una providencia del Consejo de Estado, cita exactamente su identificador
**[CE Rad: …]**. Preséntala como jurisprudencia de esa Corporación, nunca como un concepto
emitido por el DASCD.
Cuando uses una sentencia de la Corte Constitucional, cita exactamente **[CC …]** y preséntala
como jurisprudencia constitucional, nunca como un concepto emitido por el DASCD.
Si los extractos no permiten concluir algo, indícalo expresamente. Señala fuentes
insuficientes, desactualizadas o potencialmente inaplicables.

Atentamente,

[nombre suministrado del Subdirector Jurídico]

Subdirector Jurídico

No añadas una segunda conclusión, advertencia o lista de fuentes: la interfaz las presenta aparte."""


class LLMProvider(Protocol):
    def draft(self, question: str, sources: list[dict[str, object]]) -> str: ...


class OpenAIResponsesProvider:
    """Minimal Responses API client; credentials are read only from the environment."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def draft(self, question: str, sources: list[dict[str, object]]) -> str:
        evidence = "\n\n".join(
            f"[{item['id']}] {item['titulo']} — página {item['pagina']}\n"
            f"Ficha: {item['url_ficha']}\nExtracto: {item['texto']}"
            for item in sources
        )
        payload = {
            "model": self.model,
            "store": False,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": f"Pregunta del usuario:\n{question}\n\nExtractos recuperados:\n{evidence}",
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise RuntimeError(
                    "La clave de OpenAI no es válida o fue revocada. Configura una nueva OPENAI_API_KEY y reinicia el servidor."
                ) from error
            if error.code == 429:
                raise RuntimeError(
                    "OpenAI rechazó temporalmente la solicitud por límite de uso o falta de saldo. Revisa los límites del proyecto."
                ) from error
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"OpenAI devolvió HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"No fue posible conectar con OpenAI: {error.reason}") from error
        except (TimeoutError, ConnectionError, OSError) as error:
            raise RuntimeError(
                "La conexión con OpenAI se interrumpió. Intenta nuevamente en unos segundos."
            ) from error
        text = data.get("output_text")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("El proveedor no devolvió texto utilizable")
        return text.strip()


class DeepSeekChatProvider:
    """Minimal DeepSeek Chat Completions client using the official HTTP API."""

    endpoint = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def draft(self, question: str, sources: list[dict[str, object]]) -> str:
        evidence = "\n\n".join(
            f"[{item['id']}] {item['titulo']} — página {item['pagina']}\n"
            f"Ficha: {item['url_ficha']}\nExtracto: {item['texto']}"
            for item in sources
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": f"Pregunta del usuario:\n{question}\n\nExtractos recuperados:\n{evidence}"},
            ],
            "stream": False,
            "thinking": {"type": "disabled"},
            "max_tokens": 1800,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise RuntimeError(
                    "La clave de DeepSeek no es válida o fue revocada. Configura DEEPSEEK_API_KEY y reinicia el servidor."
                ) from error
            if error.code == 402:
                raise RuntimeError("La cuenta de DeepSeek no tiene saldo disponible.") from error
            if error.code == 429:
                raise RuntimeError("DeepSeek alcanzó temporalmente el límite de solicitudes. Intenta de nuevo en un momento.") from error
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"DeepSeek devolvió HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"No fue posible conectar con DeepSeek: {error.reason}") from error
        except (TimeoutError, ConnectionError, OSError) as error:
            raise RuntimeError(
                "La conexión con DeepSeek se interrumpió. Intenta nuevamente en unos segundos."
            ) from error
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("DeepSeek no devolvió una respuesta utilizable") from error
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("DeepSeek no devolvió texto utilizable")
        return text.strip()


def retrieve(index_path: Path, question: str, top_chunks: int) -> list[SearchResult]:
    chunks = [Chunk(**row) for row in load_jsonl(index_path)]
    candidates = BM25Index(chunks).search(question, limit=max(top_chunks * 6, top_chunks))
    selected: list[SearchResult] = []
    seen_documents: set[str] = set()
    for result in candidates:
        if result.chunk.sha256_pdf in seen_documents:
            continue
        selected.append(result)
        seen_documents.add(result.chunk.sha256_pdf)
        if len(selected) == top_chunks:
            break
    return selected


def make_sources(results: list[SearchResult]) -> list[dict[str, object]]:
    return [
        {
            "id": f"Nro. Rad: {result.chunk.radicado}" if result.chunk.radicado else f"S{position}",
            "radicado": result.chunk.radicado, "chunk_id": result.chunk.chunk_id,
            "score": round(result.score, 6), "titulo": result.chunk.titulo or "Sin título",
            "pagina": result.chunk.pagina, "url_ficha": result.chunk.url_ficha,
            "url_pdf": result.chunk.url_pdf, "texto": result.chunk.texto,
        }
        for position, result in enumerate(results, start=1)
    ]


def provider_from_env() -> LLMProvider:
    selected = os.environ.get("CONCEPTHIA_LLM_PROVIDER", "").strip().lower()
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if selected not in ("", "deepseek", "openai"):
        raise RuntimeError("CONCEPTHIA_LLM_PROVIDER debe ser 'deepseek' u 'openai'.")
    if selected == "deepseek" or (not selected and deepseek_key):
        if not deepseek_key:
            raise RuntimeError("Falta DEEPSEEK_API_KEY. Exporte la clave y reinicie el servidor.")
        return DeepSeekChatProvider(
            deepseek_key, os.environ.get("CONCEPTHIA_DEEPSEEK_MODEL", "deepseek-v4-flash")
        )
    if selected == "openai" or openai_key:
        if not openai_key:
            raise RuntimeError("Falta OPENAI_API_KEY. Exporte la clave y reinicie el servidor.")
        return OpenAIResponsesProvider(openai_key, os.environ.get("CONCEPTHIA_OPENAI_MODEL", "gpt-5"))
    raise RuntimeError("Falta una clave: configure DEEPSEEK_API_KEY u OPENAI_API_KEY.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un borrador con fuentes recuperadas de Concepthia")
    parser.add_argument("question", help="Pregunta en lenguaje natural")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--top-chunks", type=int, default=6)
    parser.add_argument("--json", action="store_true", help="Imprime respuesta y evidencia como JSON")
    args = parser.parse_args()
    if args.top_chunks < 1:
        parser.error("--top-chunks debe ser al menos 1")
    results = retrieve(args.data_dir / "index" / "chunks.jsonl", args.question, args.top_chunks)
    if not results:
        print("No encontré evidencia suficiente en el corpus local para elaborar un borrador.", file=sys.stderr)
        return 1
    sources = make_sources(results)
    try:
        draft = provider_from_env().draft(args.question, sources)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    response = {"advertencia": "Borrador informativo; requiere revisión humana.", "pregunta": args.question,
                "respuesta": draft, "fuentes": sources}
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print("BORRADOR INFORMATIVO — requiere revisión humana\n")
        print(draft)
        print("\nFuentes recuperadas:")
        for source in sources:
            print(f"[{source['id']}] {source['titulo']} — p. {source['pagina']} — {source['url_ficha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
