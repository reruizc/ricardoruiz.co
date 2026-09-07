#!/usr/bin/env python3
"""
Verificación de disponibilidad de las fuentes citadas en el aporte al
diagnóstico del sector TIC (PND 2026-2030).

Pide cada URL del inventario de `fuentes.py` y reporta el código de respuesta.
No descarga el contenido completo: usa HEAD y, cuando el servidor no lo admite,
un GET con rango de un byte. El objetivo es dejar constancia reproducible de que
cada referencia del documento estaba publicada y accesible en la fecha de corte.

ADVERTENCIA IMPORTANTE. Esta rutina comprueba que la URL responde, no que la
cifra citada esté en el documento. Un "ok" aquí NO convierte una fuente de nivel
B en nivel A: para eso hay que abrir la publicación y cotejar el dato.

Debe ejecutarse desde una red sin restricciones de salida. En entornos con proxy
corporativo o de agente, el propio proxy rechaza la conexión y devuelve 403 o 407
sin llegar al servidor; esos casos se reportan aparte, como "bloqueado", para no
confundirlos con una fuente caída.

Uso:
    python3 verificar_fuentes.py            # verifica todo el inventario
    python3 verificar_fuentes.py --tema 7   # solo un tema
    python3 verificar_fuentes.py --json out.json
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fuentes import FUENTES  # noqa: E402

CURL = "/usr/bin/curl"
AGENTE = "Mozilla/5.0 (compatible; DNP-verificacion-fuentes/1.0)"

# curl 56 con "CONNECT tunnel failed" y curl 35 son el proxy rechazando la
# conexión, no el servidor de la fuente respondiendo.
SALIDAS_DE_PROXY = {56, 35, 7}


def consultar(url, tiempo=45):
    """Código HTTP final siguiendo redirecciones, o un estado no numérico
    cuando la conexión no llegó al servidor."""
    ultimo = "000"
    for args in (["-I"], ["-r", "0-0"]):
        try:
            r = subprocess.run(
                [CURL, "-sS", "-o", os.devnull, "-w", "%{http_code}",
                 "-L", "--max-time", str(tiempo), "-A", AGENTE, *args, url],
                capture_output=True, text=True, timeout=tiempo + 10)
        except subprocess.TimeoutExpired:
            return "timeout"
        if r.returncode in SALIDAS_DE_PROXY:
            return "bloqueado"
        cod = r.stdout.strip()
        # 403 y 405 sobre HEAD suelen ser el método, no el recurso: se
        # reintenta con el GET de un byte antes de darlos por buenos.
        if cod and cod not in ("000", "403", "405"):
            return cod
        ultimo = cod or ultimo
    return ultimo


def clasificar(codigo):
    if codigo.startswith(("2", "3")):
        return "ok"
    if codigo == "bloqueado":
        return "bloqueado"
    return "revisar"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tema", type=int, help="verificar solo este tema")
    ap.add_argument("--json", help="ruta para guardar el resultado")
    args = ap.parse_args()

    filas = [f for f in FUENTES if args.tema is None or args.tema in f["temas"]]
    if not filas:
        print(f"no hay fuentes registradas para el tema {args.tema}")
        return 1

    resultados = []
    ancho = max(len(f["sigla"]) for f in filas)
    for f in filas:
        cod = consultar(f["url"])
        estado = clasificar(cod)
        resultados.append({"sigla": f["sigla"], "url": f["url"], "nivel": f["nivel"],
                           "codigo": cod, "estado": estado})
        print(f"{f['sigla']:<{ancho}}  {cod:>9}  {estado:<9}  {f['url']}")

    ok = [r for r in resultados if r["estado"] == "ok"]
    bloqueadas = [r for r in resultados if r["estado"] == "bloqueado"]
    revisar = [r for r in resultados if r["estado"] == "revisar"]

    print(f"\n{len(ok)} de {len(resultados)} respondieron.")
    if bloqueadas:
        print(f"{len(bloqueadas)} no se pudieron consultar porque la red bloqueó "
              f"la salida; repetir desde una conexión sin proxy:")
        for r in bloqueadas:
            print(f"  {r['sigla']}")
    if revisar:
        print("Pendientes de revisar:")
        for r in revisar:
            print(f"  {r['sigla']}: {r['codigo']}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(resultados, fh, indent=1, ensure_ascii=False)
        print(f"\nresultado en {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
