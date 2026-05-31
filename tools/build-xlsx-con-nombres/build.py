#!/usr/bin/env python3
"""
Genera XLSX 'amigables' para consultores: además de los códigos GCS originales,
agrega columnas con NOMBRES de departamento, municipio, puesto y comuna,
cruzando contra Bases de datos/PUESTOS_GEOREF.csv.

Columnas nuevas al final: DES_DDE, DES_MME, DES_PP, COD_COMUNA, DES_COMUNA.

Uso:
  python3 tools/build-xlsx-con-nombres/build.py [archivo1.csv [archivo2.csv ...]]

Si no se pasan archivos, procesa por default PRES1V 2022 y PRES2V 2022.

Sube los xlsx a S3 con sufijo `_CON_NOMBRES.xlsx` al lado del original.
"""
import csv
import subprocess
import sys
import time
from pathlib import Path
from openpyxl import Workbook

SRC = Path("/Users/ricardoruiz/ricardoruiz.co/Bases de datos")
GCS_DIR = SRC / "FINAL SUBIDA GCS"
GEOREF = SRC / "PUESTOS_GEOREF.csv"
OUT = SRC / "output_xlsx_con_nombres"
OUT.mkdir(parents=True, exist_ok=True)

S3_BASE = "s3://elecciones-2026/ricardoruiz.co/DESCARGAS/raw"

# (gcs_name, categoria_s3, año)
DEFAULTS = [
    ("GCS_2022PRES1V.csv", "presidencial-1v", 2022),
    ("GCS_2022PRES2V.csv", "presidencial-2v", 2022),
]

SHEET_ROWS = 1_000_000


def load_geo_lookup():
    """Lee PUESTOS_GEOREF.csv y devuelve dict (dde,mme,zz,pp) → info."""
    print(f"Cargando {GEOREF.name}…", flush=True)
    lookup = {}
    with GEOREF.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            codigo = (row.get("CÓDIGO COMPLETO") or "").strip()
            if len(codigo) != 9:
                continue
            try:
                dde = codigo[0:2]
                mme = codigo[2:5]
                zz  = codigo[5:7]
                pp  = codigo[7:9]
                int(dde); int(mme); int(zz); int(pp)
            except ValueError:
                continue
            nom_comuna = (row.get("NOMBRE COMUNA") or "").strip()
            cod_comuna = (row.get("CÓDIGO COMUNA") or "").strip()
            # El NOMBRE COMUNA viene con prefix del CÓDIGO ("01COMUNA 1 POPULAR" → "COMUNA 1 POPULAR")
            if cod_comuna and nom_comuna.startswith(cod_comuna):
                nom_comuna = nom_comuna[len(cod_comuna):].strip()
            lookup[(dde, mme, zz, pp)] = {
                "depto":      (row.get("DEPARTAMENTO") or "").strip(),
                "municipio":  (row.get("MUNICIPIO") or "").strip(),
                "puesto":     (row.get("NOMBRE PUESTO") or "").strip(),
                "cod_comuna": cod_comuna,
                "comuna":     nom_comuna,
            }
    print(f"  → {len(lookup):,} puestos georreferenciados", flush=True)
    return lookup


def enrich(gcs_in: Path, xlsx_out: Path, lookup: dict):
    new_cols = ["DES_DDE", "DES_MME", "DES_PP", "COD_COMUNA", "DES_COMUNA"]
    misses = 0
    hits = 0
    with gcs_in.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = next(reader)
        try:
            idx_dde = headers.index("COD_DDE")
            idx_mme = headers.index("COD_MME")
            idx_zz  = headers.index("COD_ZZ")
            idx_pp  = headers.index("COD_PP")
        except ValueError as e:
            raise SystemExit(f"Falta columna en {gcs_in.name}: {e}")

        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Datos")
        ws.append(headers + new_cols)
        rows_in_sheet = 1
        sheet_idx = 1

        for row in reader:
            try:
                dde = row[idx_dde].strip().zfill(2)
                mme = row[idx_mme].strip().zfill(3)
                zz  = row[idx_zz].strip().zfill(2)
                pp  = row[idx_pp].strip().zfill(2)
                info = lookup.get((dde, mme, zz, pp))
            except IndexError:
                info = None
            if info:
                hits += 1
                enriched = row + [info["depto"], info["municipio"], info["puesto"], info["cod_comuna"], info["comuna"]]
            else:
                misses += 1
                enriched = row + ["", "", "", "", ""]
            if rows_in_sheet >= SHEET_ROWS:
                sheet_idx += 1
                ws = wb.create_sheet(f"Datos {sheet_idx}")
                ws.append(headers + new_cols)
                rows_in_sheet = 1
            ws.append(enriched)
            rows_in_sheet += 1

        wb.save(xlsx_out)
    return {
        "hits": hits, "misses": misses,
        "match_pct": round(hits / (hits + misses) * 100, 2) if (hits + misses) else 0,
        "mb": round(xlsx_out.stat().st_size / (1024 * 1024), 2),
        "sheets": sheet_idx,
    }


def s3_upload(local_path: Path, cat: str, año: int):
    s3_key = f"{S3_BASE}/{cat}/{año}/{local_path.name}"
    cmd = ["aws", "s3", "cp", str(local_path), s3_key,
           "--content-type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           "--cache-control", "public, max-age=86400",
           "--no-progress"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return s3_key.replace("s3://elecciones-2026/", "https://elecciones-2026.s3.us-east-1.amazonaws.com/")
    except subprocess.CalledProcessError as e:
        print(f"   S3 upload FAIL ({local_path.name}): {e.stderr.strip()[:200]}", flush=True)
        return None


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    upload  = "--no-upload" not in sys.argv

    archivos = DEFAULTS
    if only:
        archivos = [(n, c, a) for (n, c, a) in DEFAULTS if n in only]
        # Permite archivos que no sean defaults también
        for n in only:
            if not any(x[0] == n for x in archivos):
                # Inferir cat/año por nombre
                cat, año = ("custom", 0)
                archivos.append((n, cat, año))

    lookup = load_geo_lookup()

    for idx, (csv_name, cat, año) in enumerate(archivos, 1):
        csv_in = GCS_DIR / csv_name
        if not csv_in.exists():
            print(f"[{idx}/{len(archivos)}] SKIP (no existe): {csv_name}")
            continue
        out_dir = OUT / cat / str(año)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = csv_name.replace(".csv", "_CON_NOMBRES.xlsx")
        xlsx_out = out_dir / out_name
        print(f"[{idx}/{len(archivos)}] {csv_name} → {out_name}", flush=True)
        t0 = time.time()
        stats = enrich(csv_in, xlsx_out, lookup)
        stats["sec"] = round(time.time() - t0, 1)
        print(f"   OK · {stats['hits']:,} hits / {stats['misses']:,} misses ({stats['match_pct']}% match) · {stats['mb']} MB · {stats['sheets']} hojas · {stats['sec']}s", flush=True)
        if upload:
            url = s3_upload(xlsx_out, cat, año)
            if url:
                print(f"   ↑ {url}", flush=True)


if __name__ == "__main__":
    main()
