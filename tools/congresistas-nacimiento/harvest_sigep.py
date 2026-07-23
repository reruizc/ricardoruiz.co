#!/usr/bin/env python3
"""Completa lugar de nacimiento desde SIGEP II (Función Pública) para los electos
que Congreso Visible no cubre.

El buscador publico es Grails ("DAFP-INDEXER BHV"):
  POST /dafpIndexerBHV/hvSigep/index   (query=<nombre>&find=Buscar)  -> HTML con links detallarHV/{id}
  GET  /dafpIndexerBHV/hvSigep/detallarHV/{id}                       -> "Municipio de Nacimiento: MUN, DEPTO - PAIS"

Ventaja sobre Congreso Visible: trae el DEPARTAMENTO explicito (CV solo da el municipio,
que es ambiguo -- hay 3 Argelia, 2 Armenia, 2 Barbosa...).

Uso: python3 harvest_sigep.py
"""
import json
import re
import subprocess
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://www.funcionpublica.gov.co/dafpIndexerBHV/hvSigep"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = Path(__file__).resolve().parents[2] / "Bases de datos" / "congresistas-nacimiento"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]+", " ", s.upper())


STOP = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}


def toks(s):
    return frozenset(t for t in norm(s).split() if len(t) > 1 and t not in STOP)


def post(query: str) -> str:
    r = subprocess.run(
        ["/usr/bin/curl", "-sL", "-A", UA, "--max-time", "90", "-X", "POST",
         f"{BASE}/index", "--data-urlencode", f"query={query}",
         "--data-urlencode", "find=Buscar"],
        capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


def get(url: str) -> str:
    r = subprocess.run(["/usr/bin/curl", "-sL", "-A", UA, "--max-time", "90", url],
                       capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


HIT_RE = re.compile(r'detallarHV/([A-Za-z0-9\-]+)"[^>]*>\s*([^<\r\n]+?)\s*[\r\n<]')
# el valor va en un <span> aparte, despues del label y de un &nbsp;
MUN_RE = re.compile(
    r"Municipio de Nacimiento:</span>.*?<span>\s*(.*?)\s*</span>", re.S)


def buscar(nombre: str):
    """(sigep_id, nombre_sigep, tipo) si hay match confiable; si no, None.

    Solo acepta igualdad de tokens o subconjunto con >=3 tokens (mismo criterio
    que build_roster.py). NO usa "N tokens en comun": produce falsos positivos
    graves con nombres colombianos (DIEGO FERNANDO GARCIA ALFONSO matcheaba a
    DIEGO ALFONSO GARCIA FISCAL).
    """
    tn = toks(nombre)
    partes = norm(nombre).split()
    # 1) nombre completo · 2) solo apellidos (ultimos 2) · 3) primer nombre + apellidos
    variantes = [nombre]
    if len(partes) >= 3:
        variantes.append(" ".join(partes[-2:]))
        variantes.append(partes[0] + " " + " ".join(partes[-2:]))
    for v in variantes:
        for sid, nom in HIT_RE.findall(post(v)):
            ts = toks(nom)
            if ts == tn:
                return sid, nom.strip(), "exacto"
            if (ts <= tn or tn <= ts) and min(len(ts), len(tn)) >= 3:
                return sid, nom.strip(), "subconjunto"
    return None


def main():
    electos = json.loads((OUT / "electos-nacimiento.json").read_text(encoding="utf-8"))
    faltan = [e for e in electos if not e.get("lugar_nacimiento")]
    print(f"buscando {len(faltan)} en SIGEP...")

    def one(e):
        hit = buscar(e["nombre"])
        if not hit:
            return e["nombre"], None
        sid, nom, tipo = hit
        m = MUN_RE.search(get(f"{BASE}/detallarHV/{sid}"))
        lugar = re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        return e["nombre"], {"sigep_id": sid, "sigep_nombre": nom,
                             "sigep_match": tipo, "sigep_lugar": lugar}

    with ThreadPoolExecutor(max_workers=5) as ex:
        res = dict(ex.map(one, faltan))

    ok = {k: v for k, v in res.items() if v and v.get("sigep_lugar")}
    (OUT / "sigep.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print(f"-> sigep.json · {len(ok)}/{len(faltan)} resueltos")
    for k, v in ok.items():
        print(f"   {k:42} {v['sigep_lugar']}")


if __name__ == "__main__":
    main()
