#!/usr/bin/env python3
"""
Análisis exploratorio del corpus de política pública TIC e IA (Colombia).

Reproduce las cifras reportadas en el capítulo de aplicación exploratoria de
analítica de texto del Informe Técnico - Entrega 2 (contrato DNP-1025-2026).

Corpus: documentos CONPES 3975 de 2019 y 4144 de 2025, descargados de la
biblioteca pública del DNP (colaboracion.dnp.gov.co).

Unidad de análisis: el párrafo. Se descartan los bloques de menos de 25
palabras para excluir encabezados, pies de página, entradas de tabla de
contenido y elementos de tabla, que no son texto argumentativo.

Uso:
    python3 analisis_corpus.py              # descarga, procesa e imprime
    python3 analisis_corpus.py --json out.json

Requiere: pdftotext (poppler) en el PATH. Sin dependencias de Python.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata

CONPES = {
    "CONPES 3975 (2019)": "3975",
    "CONPES 4144 (2025)": "4144",
}
URL = "https://colaboracion.dnp.gov.co/CDT/Conpes/Econ%C3%B3micos/{}.pdf"

# Familias léxicas. Cada familia se evalúa como "el párrafo menciona al menos
# uno de estos patrones", no como conteo de ocurrencias: interesa la extensión
# temática del documento, no la repetición de una palabra dentro de un párrafo.
FAMILIAS = {
    "territorial": [r"\bterritori", r"\bregion", r"\bmunicipi", r"\bdepartamental",
                    r"\brural", r"\bcabecera"],
    "diferencial": [r"\benfoque diferencial", r"\binterseccional", r"\bgenero\b",
                    r"\bmujeres\b", r"\betnic", r"\bdiscapacidad", r"\bindigena",
                    r"\bcampesin"],
    "habilidades": [r"\bhabilidades digitales", r"\balfabetizacion digital",
                    r"\bcompetencias digitales", r"\btalento digital", r"\bapropiacion"],
}

# Términos cuya frecuencia absoluta permite observar el desplazamiento del
# vocabulario de política entre 2019 y 2025.
TERMINOS = ["inteligencia artificial", "transformacion digital", "gobernanza",
            "etic", "riesgo", "capacidades", "datos"]


def plegar(texto):
    """Minúsculas sin tildes, para comparar sin depender de la acentuación."""
    s = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def descargar(num, destino):
    if os.path.exists(destino):
        return destino
    subprocess.run(["/usr/bin/curl", "-sLk", "-A", "Mozilla/5.0", URL.format(num),
                    "-o", destino], check=True)
    return destino


def extraer_texto(pdf):
    txt = pdf.replace(".pdf", ".txt")
    if not os.path.exists(txt):
        subprocess.run(["pdftotext", "-layout", pdf, txt], check=True)
    return open(txt, encoding="utf-8", errors="replace").read()


def parrafos(texto, minimo=25):
    bloques = re.split(r"\n\s*\n", texto)
    limpios = (re.sub(r"\s+", " ", b).strip() for b in bloques)
    return [p for p in limpios if len(p.split()) >= minimo]


def analizar(nombre, texto):
    ps = parrafos(texto)
    plegados = [plegar(p) for p in ps]
    total = len(ps)
    resultado = {"parrafos": total, "palabras": len(texto.split()), "familias": {}, "terminos": {}}
    for familia, patrones in FAMILIAS.items():
        hits = sum(1 for p in plegados if any(re.search(x, p) for x in patrones))
        resultado["familias"][familia] = {
            "parrafos": hits,
            "porcentaje": round(100 * hits / total, 1) if total else 0.0,
        }
    plegado_total = plegar(texto)
    for termino in TERMINOS:
        resultado["terminos"][termino] = len(re.findall(termino, plegado_total))
    return resultado


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="directorio de trabajo para los PDF")
    ap.add_argument("--json", help="ruta para guardar los resultados")
    args = ap.parse_args()

    salida = {}
    for nombre, num in CONPES.items():
        pdf = os.path.join(args.dir, f"conpes{num}.pdf")
        descargar(num, pdf)
        salida[nombre] = analizar(nombre, extraer_texto(pdf))

    ancho = max(len(n) for n in salida)
    print(f"{'documento':<{ancho}}  párrafos  territorial  diferencial  habilidades")
    for nombre, r in salida.items():
        f = r["familias"]
        print(f"{nombre:<{ancho}}  {r['parrafos']:>8}  "
              f"{f['territorial']['porcentaje']:>10}%  "
              f"{f['diferencial']['porcentaje']:>10}%  "
              f"{f['habilidades']['porcentaje']:>10}%")

    print("\nfrecuencia de términos")
    for termino in TERMINOS:
        fila = "  ".join(f"{n}: {r['terminos'][termino]}" for n, r in salida.items())
        print(f"  {termino:<24} {fila}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(salida, fh, indent=1, ensure_ascii=False)
        print(f"\nresultados en {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
