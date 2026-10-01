#!/usr/bin/env python3
"""build_cruce_siedco.py — series mensuales 2025-2026 de la entrega SIEDCO para
cruzar con MinDefensa en policia-abiertos.html: hechos por mes (nacional y 10
ciudades) y % con «barrio pendiente por asignar» por mes y delito.
    python3 tools/ponal/build_cruce_siedco.py → Bases de datos/output_ponal/siedco-mes.json
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build_ponal import CANON, SRC_2, BARRIO_NULO  # noqa
csv.field_size_limit(10**9)
R = Path(__file__).resolve().parents[2]
OUT = R / "Bases de datos" / "output_ponal" / "siedco-mes.json"
CIU = {"11001", "05001", "76001", "08001", "13001", "68001", "54001", "08758", "25754", "47001"}
nac = defaultdict(lambda: defaultdict(int))
ciu = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
pend = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))  # dane|nac → delito → mes → [pend, tot]
fem = defaultdict(int)
with SRC_2.open(encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f, delimiter=";")
    h = next(rd)
    I = {k: h.index(k) for k in ("Nombre Delitos", "Cantidad", "Fecha", "Hechos.CODIGO_DANE", "Hechos.BARRIOS_HECHO", "Person.GENERO")}
    for row in rd:
        did = CANON.get(row[I["Nombre Delitos"]].strip().lower())
        fe = row[I["Fecha"]]
        if not did or len(fe) < 10:
            continue
        m = f"{fe[6:10]}-{fe[3:5]}"
        try:
            q = int(row[I["Cantidad"]] or 1) or 1
        except ValueError:
            q = 1
        nac[did][m] += q
        cod = row[I["Hechos.CODIGO_DANE"]].strip()
        dane = cod[:-3].zfill(5) if cod.isdigit() and len(cod) >= 6 else ""
        p = BARRIO_NULO in row[I["Hechos.BARRIOS_HECHO"]].upper()
        for k in ("nac", dane) if dane in CIU else ("nac",):
            pend[k][did][m][1] += q
            if p:
                pend[k][did][m][0] += q
        if dane in CIU:
            ciu[dane][did][m] += q
        if did == "homicidios" and row[I["Person.GENERO"]].upper().startswith("FEM"):
            fem[m] += q
J = {"v": "2026-09-30", "nac": {d: dict(sorted(v.items())) for d, v in nac.items()},
     "ciudad": {c: {d: dict(sorted(v.items())) for d, v in x.items()} for c, x in ciu.items()},
     "pendiente": {k: {d: {m: v for m, v in sorted(x.items())} for d, x in y.items()} for k, y in pend.items()},
     "homicidio_mujeres_mes": dict(sorted(fem.items()))}
OUT.write_text(json.dumps(J, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(OUT, f"{OUT.stat().st_size/1024:.0f} KB")
