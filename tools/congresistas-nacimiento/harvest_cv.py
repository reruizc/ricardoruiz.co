#!/usr/bin/env python3
"""Cosecha lugar de nacimiento de congresistas desde Congreso Visible (Uniandes).

El sitio es Next.js y sirve todo server-rendered:
  - listado  /congresistas/?corporacion={1|2}&cuatrienio={n}&rows=500
             -> __NEXT_DATA__.props.pageProps.ListaInicial (persona_id, nombres, apellidos, partido)
             (el parametro `rows` rompe la paginacion de 24, igual que en /votaciones/)
  - ficha    /congresistas/perfil/{slug}/{persona_id}/
             -> HTML con "Lugar de nacimiento" y "Fecha de nacimiento" en littleProfileCard

Requiere User-Agent de navegador (curl pelado da 403).

Uso:
    python3 harvest_cv.py index      # baja los listados -> index.json
    python3 harvest_cv.py perfiles   # baja las fichas   -> raw/{id}.html + perfiles.json
"""
import json
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://congresovisible.uniandes.edu.co"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

OUT = Path(__file__).resolve().parents[2] / "Bases de datos" / "congresistas-nacimiento"
RAW = OUT / "raw"

# corporacion: 1=Camara, 2=Senado · cuatrienio: 10=2026-2030, 9=2022-2026, 8=2018-2022
COMBOS = [(c, q) for c in (1, 2) for q in (10, 9, 8)]


def fetch(url: str) -> str:
    """curl por subprocess (esquiva el TLS de python 3.14, patron de scrape_cne.py)."""
    r = subprocess.run(
        ["/usr/bin/curl", "-s", "--compressed", "-A", UA, "--max-time", "60", url],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", errors="replace")


def next_data(html: str):
    m = re.search(r'__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def cmd_index():
    personas = {}
    for corp, cuat in COMBOS:
        url = f"{BASE}/congresistas/?corporacion={corp}&cuatrienio={cuat}&rows=500"
        d = next_data(fetch(url))
        lista = d["props"]["pageProps"]["ListaInicial"] if d else []
        for p in lista:
            pid = p["persona_id"]
            # la ficha mas reciente manda (cuatrienio mayor primero en COMBOS)
            personas.setdefault(pid, {
                "persona_id": pid,
                "nombres": (p.get("nombres") or "").strip(),
                "apellidos": (p.get("apellidos") or "").strip(),
                "partido": p.get("partido"),
                "corporacion_id": corp,
                "cuatrienio_id": cuat,
            })
        print(f"corp={corp} cuat={cuat}: {len(lista)} filas (acum {len(personas)})")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.json").write_text(
        json.dumps(list(personas.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> index.json · {len(personas)} personas unicas")


CARD_RE = re.compile(
    r"<small>\s*([^<]+?)\s*</small>\s*<p>\s*(.*?)\s*</p>", re.S)


def parse_perfil(html: str) -> dict:
    campos = {}
    for k, v in CARD_RE.findall(html):
        v = re.sub(r"<[^>]+>", "", v).strip()
        campos[k.strip()] = v
    return campos


def cmd_perfiles():
    RAW.mkdir(parents=True, exist_ok=True)
    idx = json.loads((OUT / "index.json").read_text(encoding="utf-8"))

    def one(p):
        pid = p["persona_id"]
        f = RAW / f"{pid}.html"
        if not f.exists() or f.stat().st_size < 2000:
            slug = slugify(f"{p['nombres']} {p['apellidos']}")
            html = fetch(f"{BASE}/congresistas/perfil/{slug}/{pid}/")
            f.write_text(html, encoding="utf-8")
        else:
            html = f.read_text(encoding="utf-8", errors="replace")
        c = parse_perfil(html)
        return {
            **p,
            "lugar_nacimiento": c.get("Lugar de nacimiento") or None,
            "fecha_nacimiento": c.get("Fecha de nacimiento") or None,
            "profesion": c.get("Profesión") or None,
        }

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, idx))

    con = sum(1 for r in res if r["lugar_nacimiento"])
    (OUT / "perfiles.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> perfiles.json · {len(res)} fichas · {con} con lugar de nacimiento "
          f"({con / max(1, len(res)) * 100:.0f}%)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "index"
    {"index": cmd_index, "perfiles": cmd_perfiles}[cmd]()
