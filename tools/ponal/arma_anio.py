#!/usr/bin/env python3
"""arma_anio.py — arma empleada × año × delito, nacional, desde las dos bases
PONAL (2015-2024 y 2025-2026). Sirve para el gráfico de armas incautadas vs
% de homicidios y hurtos con arma de fuego.
    python3 tools/ponal/arma_anio.py → Bases de datos/output_ponal/arma_anio.json
"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build_ponal import CANON, SRC, SRC_2  # noqa
csv.field_size_limit(10**9)
OUT = Path(__file__).resolve().parents[2] / "Bases de datos" / "output_ponal" / "arma_anio.json"
RE_A = re.compile(r"(\d{4})")

def grupo(a):
    a = (a or "").strip().upper()
    if not a or a in ("NO REPORTADO", "NO REPORTA", "SIN DATO", "-"):
        return "sin_dato"
    if "FUEGO" in a:
        return "fuego"
    if "BLANCA" in a or "CORTOPUNZANTE" in a or "CORTANTE" in a or "PUNZANTE" in a:
        return "blanca"
    if "CONTUNDENTE" in a:
        return "contundente"
    if "SIN EMPLEO" in a or "NO EMPLEO" in a:
        return "sin_arma"
    return "otra"

acc = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # delito → año → grupo
for path in (SRC, SRC_2):
    if not path.exists():
        continue
    with path.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f, delimiter=";")
        h = next(rd)
        i_d, i_q, i_f, i_a = h.index("Nombre Delitos"), h.index("Cantidad"), h.index("Fecha"), h.index("Arma empleada")
        for n, row in enumerate(rd):
            if len(row) != len(h):
                continue
            did = CANON.get(row[i_d].strip().lower())
            if not did:
                continue
            m = RE_A.search(row[i_f])
            if not m:
                continue
            a = int(m.group(1))
            if a < 2015 or a > 2026:
                continue
            try:
                q = int(row[i_q] or 1) or 1
            except ValueError:
                q = 1
            acc[did][a][grupo(row[i_a])] += q
            if n % 2000000 == 0 and n:
                print(f"  ... {path.name} {n:,}", file=sys.stderr, flush=True)
out = {d: {str(a): dict(g) for a, g in sorted(v.items())} for d, v in acc.items()}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("→", OUT)
