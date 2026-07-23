#!/usr/bin/env python3
"""Cruza los 286 electos 2026-2030 contra las fichas de Congreso Visible.

Match por subconjunto de tokens (mismo algoritmo de build_roster.py): el nombre
legal de la Registraduria trae segundos nombres que Congreso Visible a veces omite.

Salida: electos-nacimiento.json  (+ reporte de no-matcheados a stdout)
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Bases de datos"
OUT = DATA / "congresistas-nacimiento"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]+", " ", s.upper())


# particulas que no aportan al match
STOP = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "SAN", "DA", "DI"}


def toks(s: str) -> frozenset:
    return frozenset(t for t in norm(s).split() if len(t) > 1 and t not in STOP)


def main():
    electos = json.loads((DATA / "mxd-congreso-2026" / "electos-2026-2030.json")
                         .read_text(encoding="utf-8"))
    perfiles = json.loads((OUT / "perfiles.json").read_text(encoding="utf-8"))

    # indice CV: tokens -> ficha (la de cuatrienio mas alto gana)
    cv = []
    for p in perfiles:
        cv.append((toks(f"{p['nombres']} {p['apellidos']}"), p))

    exacto = {}
    for t, p in cv:
        if t not in exacto or p["cuatrienio_id"] > exacto[t]["cuatrienio_id"]:
            exacto[t] = p

    res, sin = [], []
    for e in electos:
        te = toks(e["nombre"])
        hit = exacto.get(te)
        how = "exacto"
        if not hit:
            # subconjunto: el nombre CV esta contenido en el de la Registraduria (o al reves)
            cands = [p for t, p in cv
                     if len(t) >= 3 and (t <= te or te <= t)]
            if cands:
                hit = max(cands, key=lambda p: p["cuatrienio_id"])
                how = "subconjunto"
        if not hit:
            # ultimo recurso: >=3 tokens en comun incluyendo 2 apellidos
            cands = [(len(t & te), p) for t, p in cv if len(t & te) >= 3]
            if cands:
                n, hit = max(cands, key=lambda x: (x[0], x[1]["cuatrienio_id"]))
                how = f"parcial({n})"
        if hit:
            res.append({**e, "cv_id": hit["persona_id"],
                        "cv_nombre": f"{hit['nombres']} {hit['apellidos']}",
                        "lugar_nacimiento": hit["lugar_nacimiento"],
                        "fecha_nacimiento": hit["fecha_nacimiento"],
                        "match": how})
        else:
            sin.append(e)
            res.append({**e, "cv_id": None, "lugar_nacimiento": None, "match": None})

    (OUT / "electos-nacimiento.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    con = sum(1 for r in res if r["lugar_nacimiento"])
    print(f"{con}/{len(res)} electos con lugar de nacimiento ({con/len(res)*100:.0f}%)")
    from collections import Counter
    print("tipo de match:", Counter(r["match"] for r in res))
    if sin:
        print(f"\nSIN MATCH ({len(sin)}):")
        for e in sin:
            print(f"  {e['corp']:7} {e['dep']:22} {e['nombre']}")


if __name__ == "__main__":
    main()
