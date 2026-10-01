#!/usr/bin/env python3
"""
build_modalidad.py — modalidad presunta del homicidio (MinDefensa, datos.gov.co
m8fd-ahd9, campo `_modalidad_presunta`) por año, departamento y municipio, para
el hub de Policía (policia-mapa.html y policia-historico.html).

    python3 tools/ponal/build_modalidad.py → Bases de datos/output_ponal/homicidio-modalidad.json

La entrega SIEDCO trae el arma pero no la modalidad; MinDefensa publica la
modalidad sobre el mismo registro (cuadran mes a mes, ver policia-abiertos).

La fuente trae ~72 modalidades. Se agrupan en siete con `grupo()`.
⚠️ La MISMA regla vive en JavaScript en policia-abiertos.html (`grupoMod`):
si se cambia aquí, cambiarla allá.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_mindefensa import soql, n  # noqa  (caché compartida)

R = Path(__file__).resolve().parents[2]
OUT = R / "Bases de datos" / "output_ponal" / "homicidio-modalidad.json"
ANIOS = list(range(2010, 2027))
GRUPOS = ["sicariato", "armados", "rina", "atraco", "familia", "otras", "establecer"]
LABEL = {"sicariato": "Sicariato", "armados": "Grupos armados y enfrentamientos", "rina": "Riña",
         "atraco": "Atraco", "familia": "Familia o pareja", "otras": "Otras", "establecer": "Por establecer"}
FAMILIA = re.compile(r"INTRAFAMILIAR|COMPA[ÑN]EROS PERMANENTES|ESPOSOS|HERMANOS|HIJO|POR EL PADRE")


def grupo(k):
    k = (k or "").upper()
    if k == "SICARIATO":
        return "sicariato"
    if FAMILIA.search(k):
        return "familia"
    if re.match(r"^RI[ÑN]A", k):
        return "rina"
    if re.search(r"ATRACO|SECUESTRO AL PASO", k):
        return "atraco"
    if re.search(r"GAO|AUTODEFENSAS|SUBVERSI|ENFRENTAMIENTO|BACRIM|TERRORISMO|FRANCOTIRADOR", k):
        return "armados"
    if re.search(r"POR ESTABLECER|NO REPORTADA|SIN DATO", k) or not k:
        return "establecer"
    return "otras"


def main():
    nac = defaultdict(lambda: [0] * len(ANIOS))
    dep = defaultdict(lambda: defaultdict(lambda: [0] * len(ANIOS)))
    mun = defaultdict(lambda: defaultdict(lambda: [0] * len(ANIOS)))
    crudas = defaultdict(int)
    for i, a in enumerate(ANIOS):
        rows = soql("m8fd-ahd9", {
            "$select": "cod_depto,cod_muni,_modalidad_presunta as k,sum(cantidad) as n",
            "$where": f"date_extract_y(fecha_hecho)={a}",
            "$group": "cod_depto,cod_muni,k", "$limit": 50000})
        if len(rows) >= 50000:
            raise SystemExit(f"{a}: la consulta tocó el tope de filas; partirla")
        for r in rows:
            g, q = grupo(r.get("k")), n(r["n"])
            crudas[r.get("k") or "SIN DATO"] += q
            nac[g][i] += q
            dep[r.get("cod_depto") or "?"][g][i] += q
            mun[r.get("cod_muni") or "?"][g][i] += q
    comp = lambda d: {g: v for g, v in d.items() if any(v)}
    out = {"v": "2026-09-30", "fuente": "MinDefensa · datos.gov.co m8fd-ahd9 · _modalidad_presunta",
           "corte": "2026-08-31", "anio_parcial": 2026, "anios": ANIOS, "grupos": GRUPOS, "label": LABEL,
           "nac": dict(nac), "deptos": {d: comp(v) for d, v in dep.items()},
           "muns": {m: comp(v) for m, v in mun.items()},
           "crudas_top": sorted(crudas.items(), key=lambda x: -x[1])[:40]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    t = {g: v[ANIOS.index(2025)] for g, v in nac.items()}
    print(f"→ {OUT.name} {OUT.stat().st_size/1024:.0f} KB · {len(out['muns'])} municipios · 2025 {t} · total {sum(t.values())}")


if __name__ == "__main__":
    main()
