"""Live, source-preserving search against the Consejo de Estado's SAMAI relatoría."""
from __future__ import annotations

from functools import lru_cache
from html import unescape
import re

import requests
from bs4 import BeautifulSoup


SAMAI_URL = "https://samai.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx"
TIMEOUT_SECONDS = 18
MAX_RESULTS = 5


def _clean(value: str) -> str:
    return " ".join(unescape(value).split())


def _query_terms(question: str) -> str:
    """Keep the official full-text query focused enough for SAMAI."""
    return " ".join(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9]+", question)[:18])


@lru_cache(maxsize=128)
def search_consejo_estado(question: str) -> tuple[dict[str, str], ...]:
    """Return the first titled decisions from the official SAMAI search."""
    terms = _query_terms(question)
    if not terms:
        return ()
    try:
        with requests.Session() as session:
            initial = session.get(SAMAI_URL, timeout=TIMEOUT_SECONDS)
            initial.raise_for_status()
            form = BeautifulSoup(initial.text, "html.parser")
            payload = {field["name"]: field.get("value", "") for field in form.select('input[type="hidden"][name]')}
            payload.update({"ctl00$MainContent$BusquedaRapidaTextBox": terms, "__EVENTTARGET": "ctl00$MainContent$BusquedaRapidaLinkButton"})
            response = session.post(SAMAI_URL, data=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
    except requests.RequestException:
        return ()

    soup = BeautifulSoup(response.text, "html.parser")
    items: list[dict[str, str]] = []
    for radicado_node in soup.select('[id*="HypRadicado_"]')[:MAX_RESULTS]:
        match = re.search(r"_(\d+)$", radicado_node.get("id", ""))
        if not match:
            continue
        index = match.group(1)
        document = soup.find(id=re.compile(rf"documentlink_{index}$"))
        url_match = re.search(r"CargarVentana\('([^']+)'", document.get("onclick", "") if document else "", re.I)
        if not url_match:
            continue
        problema = soup.find(id=re.compile(rf"ProblemaJuridicoLabel_{index}_"))
        fecha = soup.find(id=re.compile(rf"Label1_{index}$"))
        sala = soup.find(id=re.compile(rf"LbNombreSalaDecision_{index}$"))
        interno = soup.find(id=re.compile(rf"LblInterno_{index}$"))
        summary = _clean(problema.get_text(" ", strip=True) if problema else "")
        items.append({
            "court": "Consejo de Estado",
            "label": f"Rad. {_clean(radicado_node.get_text())} · Interno {_clean(interno.get_text()) if interno else 's. d.'}",
            "url": url_match.group(1),
            "coverage": _clean(fecha.get_text()) if fecha else "Providencia titulada en SAMAI",
            "summary": summary[:700],
            "sala": _clean(sala.get_text()) if sala else "",
        })
    return tuple(items)


def as_evidence(results: tuple[dict[str, str], ...]) -> list[dict[str, object]]:
    """Adapt official result cards to the evidence contract used by the LLM."""
    evidence: list[dict[str, object]] = []
    for item in results:
        radicado = item["label"].split(" · ", 1)[0].removeprefix("Rad. ")
        evidence.append({
            "id": f"CE Rad: {radicado}",
            "radicado": radicado,
            "chunk_id": None,
            "score": None,
            "titulo": f"Consejo de Estado · {item['sala'] or 'Mi Relatoría'}",
            "pagina": "s. p.",
            "url_ficha": item["url"],
            "url_pdf": item["url"],
            "texto": item["summary"],
        })
    return evidence
