#!/usr/bin/env python3
"""
build_poblacion.py — población municipal DANE para las tasas por 100.000 hab.

    python3 tools/ponal/build_poblacion.py

Fuente: `Bases de datos/output_observatorio_mujer/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx`
(126 MB · 84.245 filas · municipio × año × área × sexo × edad). Es el anexo
municipal de las Proyecciones de Población del DANE post-censo 2018.

Salida: `Bases de datos/output_ponal/poblacion.json`
    {"v":…, "anios":[2018..2024], "muns":{"05001":{"n":"Medellín","p":[…7…]}},
     "deptos":{"05":{"n":"Antioquia","p":[…]}}, "nacional":[…]}

⚠️ COBERTURA 2018-2024, NO 2015-2017. El anexo municipal arranca en 2018 (es
   post-censo). Para 2015-2017 hace falta la RETROPROYECCIÓN municipal del DANE
   («Retroproyecciones de población 1985-2017, anexo municipal por área»), que
   no está en el repo. Mientras tanto la página muestra tasa solo en los años
   con población y deja los primeros tres en volumen absoluto, declarándolo.
   NO se extrapola hacia atrás: inventar el denominador es peor que no darlo.

⚠️ Los dos archivos `PPED-AreaNac-*.xlsx` que están en la carpeta PONAL son
   NACIONALES (solo `Total Nacional` × año × Cabecera/Rural). Sirven para la
   tasa nacional y para el contexto urbano/rural, no para el mapa municipal.

⚠️ Se lee solo la fila `ÁREA GEOGRÁFICA == 'Total'`: el archivo trae además
   `Cabecera Municipal` y `Centros Poblados y Rural Disperso`, y sumarlas todas
   contaría cada municipio por partida doble.
"""

import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

RAIZ = SRC = None
RAIZ = Path(__file__).resolve().parents[2]
XLSX = RAIZ / "Bases de datos" / "output_observatorio_mujer" / "PPED-AreaSexoEdadMun-2018-2042_VP.xlsx"
NAC_NUEVO = RAIZ / "Bases de datos" / "PONAL" / "PPED-AreaNac-2018-2070.xlsx"
OUT = RAIZ / "Bases de datos" / "output_ponal" / "poblacion.json"

ANIOS = list(range(2018, 2025))          # lo que cubre el anexo y nos sirve
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HOJA = "PobMunicipalxÁreaSexoEdad"


def cols_de(fila_xml):
    """Devuelve {letra_columna: valor_texto} de un <row>, resolviendo shared strings."""
    out = {}
    for c in fila_xml.findall(f"{NS}c"):
        ref = c.get("r") or ""
        letra = "".join(ch for ch in ref if ch.isalpha())
        v = c.find(f"{NS}v")
        if v is None or v.text is None:
            continue
        out[letra] = (c.get("t"), v.text)
    return out


def main():
    if not XLSX.exists():
        sys.exit(f"no encuentro {XLSX}")

    # openpyxl tarda mucho con 84k filas × ~312 columnas porque construye la fila
    # entera; acá solo hacen falta 7 columnas, así que se lee el XML de la hoja
    # en streaming y se descartan las demás celdas sin materializarlas.
    z = zipfile.ZipFile(XLSX)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        with z.open("xl/sharedStrings.xml") as fh:
            for _, el in ET.iterparse(fh, events=("end",)):
                if el.tag == f"{NS}si":
                    shared.append("".join(t.text or "" for t in el.iter(f"{NS}t")))
                    el.clear()
    # localizar el sheet de la hoja por nombre
    with z.open("xl/workbook.xml") as fh:
        wb = ET.parse(fh).getroot()
    rid = None
    for sh in wb.iter(f"{NS}sheet"):
        if sh.get("name") == HOJA:
            rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    NSR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    with z.open("xl/_rels/workbook.xml.rels") as fh:
        rels = ET.parse(fh).getroot()
    destino = None
    for r in rels.iter(f"{NSR}Relationship"):
        if r.get("Id") == rid:
            destino = r.get("Target")
    if not destino:
        sys.exit(f"no encuentro la hoja {HOJA!r} en el xlsx")
    ruta = "xl/" + destino.lstrip("/").replace("xl/", "", 1)

    def txt(par):
        if not par:
            return ""
        t, v = par
        return shared[int(v)] if t == "s" else v

    # A=DP  B=DPNOM  C=MPIO  D=DPMP  E=AÑO  F=ÁREA  G=Total  H=Hombres  I=Mujeres
    # (de J en adelante van los 303 desagregados por edad simple: total, hombres,
    #  mujeres × 0..100 — no se leen)
    # ⚠️ `f` (mujeres) es el denominador de las tasas del módulo de violencia
    #    contra la mujer; `p` (total) el del hub de Policía. Verificado en la
    #    fuente: Medellín 2018 → 1.141.343 H + 1.285.790 M = 2.427.133 total.
    muns = defaultdict(lambda: {"n": "", "p": {}, "f": {}})
    deps = defaultdict(lambda: {"n": "", "p": defaultdict(int), "f": defaultdict(int)})
    nac = defaultdict(int)
    nac_f = defaultdict(int)
    filas = usadas = 0
    with z.open(ruta) as fh:
        for _, row in ET.iterparse(fh, events=("end",)):
            if row.tag != f"{NS}row":
                continue
            c = cols_de(row)
            row.clear()
            filas += 1
            mpio, anio, area = txt(c.get("C")), txt(c.get("E")), txt(c.get("F"))
            if not mpio or not anio.isdigit():
                continue
            if area.strip().lower() != "total":       # ⚠️ no sumar las tres áreas
                continue
            a = int(anio)
            if a not in ANIOS:
                continue
            try:
                pob = int(float(txt(c.get("G")) or 0))
            except ValueError:
                continue
            try:
                muj = int(float(txt(c.get("I")) or 0))
            except ValueError:
                muj = 0
            dane = mpio.strip().zfill(5)
            muns[dane]["n"] = txt(c.get("D")).strip()
            muns[dane]["p"][a] = pob
            muns[dane]["f"][a] = muj
            dp = dane[:2]
            deps[dp]["n"] = txt(c.get("B")).strip()
            deps[dp]["p"][a] += pob
            deps[dp]["f"][a] += muj
            nac[a] += pob
            nac_f[a] += muj
            usadas += 1
    z.close()

    out = {
        "v": "2026-08-08",
        "fuente": "DANE · Proyecciones de población municipal por área, sexo y edad 2018-2042",
        "archivo": XLSX.name,
        "anios": ANIOS,
        "nota_cobertura": ("El anexo municipal del DANE arranca en 2018 (es post-censo). "
                           "Para 2015-2017 hace falta la retroproyección municipal 1985-2017, "
                           "que no está en el repo: esos años se muestran en volumen absoluto, "
                           "sin tasa. No se extrapola hacia atrás."),
        "muns": {k: {"n": v["n"], "p": [v["p"].get(a, 0) for a in ANIOS],
                     "f": [v["f"].get(a, 0) for a in ANIOS]} for k, v in sorted(muns.items())},
        "deptos": {k: {"n": v["n"], "p": [v["p"].get(a, 0) for a in ANIOS],
                       "f": [v["f"].get(a, 0) for a in ANIOS]} for k, v in sorted(deps.items())},
        "nacional": [nac.get(a, 0) for a in ANIOS],
        "nacional_f": [nac_f.get(a, 0) for a in ANIOS],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"  filas leídas {filas:,} · usadas {usadas:,}")
    print(f"  municipios {len(out['muns']):,} · departamentos {len(out['deptos'])}")
    for a, p, f in zip(ANIOS, out["nacional"], out["nacional_f"]):
        print(f"    {a}  {p:>12,}   mujeres {f:>12,}  ({100*f/p:.1f}%)")
    print(f"  → {OUT.name}  {OUT.stat().st_size/1024:,.0f} KB")
    # control: Medellín y Bogotá contra la cifra publicada
    for d in ("05001", "11001"):
        m = out["muns"].get(d)
        if m:
            print(f"  control {d} {m['n']}: {m['p'][0]:,} (2018) → {m['p'][-1]:,} (2024)"
                  f" · mujeres {m['f'][0]:,} → {m['f'][-1]:,}")


if __name__ == "__main__":
    main()
