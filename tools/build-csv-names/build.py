#!/usr/bin/env python3
"""
Enriquece un CSV crudo GCS con columnas de NOMBRE junto a cada código:
  DES_DDE (departamento)  tras COD_DDE
  DES_MME (municipio)     tras COD_MME
  DES_PP  (puesto)        tras COD_PP

Misma convención DES_* del formato oficial (DES_COR, DES_PAR, DES_CAN...).

Fuentes de nombres:
  dep/mun : Bases de datos/test-presidencial/divipola.json (códigos Registraduría)
  puesto  : PUESTOS_GEOREF.csv (censo 2026, primario)
            + Divipol 23.09.2021.xlsx (fallback para puestos que ya no existen)
            Los ~0,3% sin match (agregados especiales zona 90/99) quedan en blanco.

Uso:
  python3 tools/build-csv-names/build.py "GCS_2023TER.csv"
  python3 tools/build-csv-names/build.py "GCS_2023TER_PUESTO.csv" --src-dir "..." --out "..."

Salida por defecto: Bases de datos/output_csv_names/<mismo nombre>.csv
(delimitador ';', BOM utf-8 para Excel, CRLF)
"""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ricardoruiz/ricardoruiz.co")
SRC_DEFAULT = ROOT / "Bases de datos/FINAL SUBIDA GCS"
OUT_DIR = ROOT / "Bases de datos/output_csv_names"
DIVIPOLA = ROOT / "Bases de datos/test-presidencial/divipola.json"
GEOREF = ROOT / "Bases de datos/PUESTOS_GEOREF.csv"
DIVIPOL21 = ROOT / "Bases de datos/Divipol 23.09.2021.xlsx"


def load_maps():
    div = json.loads(DIVIPOLA.read_text(encoding="utf-8"))
    dep_nombre, mun_nombre = {}, {}
    for d in div["deptos"]:
        dep_nombre[d["cod"].zfill(2)] = d["nombre"]
        for m in d.get("muns", []):
            mun_nombre[f'{d["cod"].zfill(2)}-{m["cod"].zfill(3)}'] = m["nombre"]

    puesto_nombre = {}
    # fallback primero (2021), el primario (2026) lo pisa después
    try:
        import openpyxl
        wb = openpyxl.load_workbook(DIVIPOL21, read_only=True)
        ws = wb.active
        for i, r in enumerate(ws.iter_rows(values_only=True), 1):
            if i <= 5:      # 4 filas de membrete + header
                continue
            try:
                dd, mm, zz, pp, _dep, _mun, puesto = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
                if dd is None or puesto is None:
                    continue
                k = str(dd).zfill(2) + str(mm).zfill(3) + str(zz).zfill(2) + str(pp).zfill(2)
                puesto_nombre[k] = str(puesto).strip()
            except Exception:
                pass
        wb.close()
    except Exception as e:
        print(f"aviso: Divipol 2021 no cargó ({e}); sigo solo con georef 2026")

    with GEOREF.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            code = (row.get("CÓDIGO COMPLETO") or "").strip()
            name = (row.get("NOMBRE PUESTO") or "").strip()
            if code and name:
                puesto_nombre[code.zfill(9)] = name

    return dep_nombre, mun_nombre, puesto_nombre


def enrich(csv_in: Path, csv_out: Path):
    dep_nombre, mun_nombre, puesto_nombre = load_maps()
    csv_out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    n = 0
    stats = {"dep": 0, "mun": 0, "pp": 0}
    with csv_in.open("r", encoding="utf-8-sig", newline="") as fi, \
         csv_out.open("w", encoding="utf-8-sig", newline="") as fo:
        reader = csv.reader(fi, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer = csv.writer(fo, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        headers = next(reader)
        i_d = headers.index("COD_DDE")
        i_m = headers.index("COD_MME")
        i_z = headers.index("COD_ZZ")
        i_p = headers.index("COD_PP")

        # posiciones de inserción (orden: DDE < MME < PP en el formato GCS)
        assert i_d < i_m < i_p, "orden de columnas inesperado"
        out_head = (headers[:i_d+1] + ["DES_DDE"]
                    + headers[i_d+1:i_m+1] + ["DES_MME"]
                    + headers[i_m+1:i_p+1] + ["DES_PP"]
                    + headers[i_p+1:])
        writer.writerow(out_head)

        for row in reader:
            dep2 = row[i_d].strip().zfill(2)
            mun3 = row[i_m].strip().zfill(3)
            zz2  = row[i_z].strip().zfill(2)
            pp2  = row[i_p].strip().zfill(2)
            dep_n = dep_nombre.get(dep2, "")
            mun_n = mun_nombre.get(f"{dep2}-{mun3}", "")
            pp_n  = puesto_nombre.get(dep2 + mun3 + zz2 + pp2, "")
            if dep_n: stats["dep"] += 1
            if mun_n: stats["mun"] += 1
            if pp_n:  stats["pp"] += 1
            writer.writerow(row[:i_d+1] + [dep_n]
                            + row[i_d+1:i_m+1] + [mun_n]
                            + row[i_m+1:i_p+1] + [pp_n]
                            + row[i_p+1:])
            n += 1
            if n % 2_000_000 == 0:
                print(f"   {n:,} filas...", flush=True)

    dt = time.time() - t0
    print(f"OK · {n:,} filas en {dt:.0f}s → {csv_out}")
    for k, label in (("dep", "DES_DDE"), ("mun", "DES_MME"), ("pp", "DES_PP")):
        print(f"   {label}: {stats[k]:,} con nombre ({stats[k]/n*100:.3f}%)")
    return n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("uso: build.py <archivo.csv> [--src-dir=...] [--out=...]")
    src_dir = SRC_DEFAULT
    out = None
    for a in sys.argv[1:]:
        if a.startswith("--src-dir="):
            src_dir = Path(a.split("=", 1)[1])
        if a.startswith("--out="):
            out = Path(a.split("=", 1)[1])
    csv_in = Path(args[0])
    if not csv_in.exists():
        csv_in = src_dir / args[0]
    if not csv_in.exists():
        raise SystemExit(f"no existe: {args[0]}")
    csv_out = out or (OUT_DIR / csv_in.name)
    print(f"{csv_in.name} → {csv_out}")
    enrich(csv_in, csv_out)


if __name__ == "__main__":
    main()
