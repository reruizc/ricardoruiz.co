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
  python3 tools/build-csv-names/build.py "GCS_2023TER.csv" [--rotulos]
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


# divipola.json trae 2 nombres de depto defectuosos; se corrigen aquí.
DEP_FIXES = {"25": "Norte De Santander", "31": "Valle Del Cauca"}


def load_maps():
    div = json.loads(DIVIPOLA.read_text(encoding="utf-8"))
    dep_nombre, mun_nombre = {}, {}
    for d in div["deptos"]:
        dep_nombre[d["cod"].zfill(2)] = d["nombre"]
        for m in d.get("muns", []):
            mun_nombre[f'{d["cod"].zfill(2)}-{m["cod"].zfill(3)}'] = m["nombre"]
    dep_nombre.update(DEP_FIXES)

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


# ─── Municipios que existieron y desaparecieron del Divipole ───────────────
# El código de municipio de un año viejo puede no existir hoy porque la entidad
# se fusionó o se absorbió. Cada entrada se resuelve por eliminación contra el
# universo real del departamento, nunca a ojo, y se deja escrita la cadena.
#
# 50-050 · MAPIRIPANA (Guainía)
#   · 2014 y 2018 traen 9 entidades en el dep 50; Divipol 2021 y el georef 2026
#     solo traen 8, y la que falta es exactamente el código 050.
#   · Guainía = Inírida + 8 corregimientos departamentales. Los códigos vivos
#     cubren 7 de esos 8 (070 Barrancominas · 073 Cacahual · 078 La Guadalupe ·
#     083 Morichal · 087 Pana Pana · 090 Puerto Colombia · 092 San Felipe): el
#     único corregimiento sin código es Mapiripana.
#   · Hoy Mapiripana existe como PUESTO dentro de Barrancominas
#     (50-070-99-05 "COLEGIO DIVINO NIÑO DE MAPIRIPANA"), coherente con que el
#     municipio de Barrancominas lo absorbiera.
#   · En 2014/2018 el 050 y el 070 conviven como entidades distintas, así que no
#     son el mismo lugar renumerado.
MUN_HISTORICOS = {
    "50-050": "Mapiripana",
}


# ─── Rótulos estructurales para lo que Divipole no nombra ──────────────────
# Los códigos de puesto de 2014/2018 no siempre existen en Divipol 2021 ni en
# el georef 2026: puestos cerrados, consulados renumerados, zonas especiales.
# En vez de dejar la celda vacía se pone un rótulo DERIVADO DEL PROPIO CÓDIGO,
# entre corchetes para que nunca se confunda con el nombre real del puesto.
#
# La base de cada rótulo se midió sobre Divipol 2021, no se supuso:
#   zona 00 · puesto 00 → 851 de 868 (98,0%) se llaman "PUESTO CABECERA MUNICIPAL"
#                          y 17 "CORREGIMIENTO DEPARTAMENTAL" (deptos 50/60/68)
#   zona 98             → 66% son "CARCEL" y variantes
#   zona 99             → 4.966 nombres distintos en 6.996 puestos: es la zona
#                          RURAL y cada puesto tiene nombre propio → NO se infiere
#   zona 90             → 106 nombres distintos en 108 puestos (estadios, centros
#                          de convención): tampoco se infiere; solo se dice qué es
# El exterior (dep 88) sí conserva el país, que viene de divipola; la ciudad va
# en la zona/puesto y esa no se puede recuperar sin el Divipole de ese año.
CORREG_DEPTOS = {"50", "60", "68"}   # Guainía, Amazonas, Vaupés


def rotulo_puesto(dep2, mun3, zz2, pp2, dep_n, mun_n):
    """Rótulo estructural cuando no hay nombre oficial. Siempre entre corchetes."""
    if dep2 == "88":
        # dep_n aquí es literalmente "Consulados": no aporta y no debe repetirse.
        pais = mun_n if mun_n and not mun_n.startswith("[") else ""
        return f"[CONSULADO · {pais.upper()}]" if pais else "[CONSULADO]"
    if zz2 == "00" and pp2 == "00":
        return "[CORREGIMIENTO DEPARTAMENTAL]" if dep2 in CORREG_DEPTOS else "[CABECERA MUNICIPAL]"
    if zz2 == "90":
        return "[PUESTO CENSO]"
    if zz2 == "98":
        return "[CARCEL]"
    if zz2 == "99":
        return "[PUESTO RURAL · SIN NOMBRE EN DIVIPOLE]"
    return "[PUESTO SIN NOMBRE EN DIVIPOLE]"


def enrich(csv_in: Path, csv_out: Path, rotulos: bool = False):
    dep_nombre, mun_nombre, puesto_nombre = load_maps()
    csv_out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    n = 0
    stats = {"dep": 0, "mun": 0, "pp": 0, "rot": 0}
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
            mun_n = mun_nombre.get(f"{dep2}-{mun3}", "") or MUN_HISTORICOS.get(f"{dep2}-{mun3}", "")
            if not mun_n and rotulos:
                mun_n = "[PAIS NO IDENTIFICADO]" if dep2 == "88" else "[MUNICIPIO NO IDENTIFICADO]"
            pp_n  = puesto_nombre.get(dep2 + mun3 + zz2 + pp2, "")
            if not pp_n and rotulos:
                pp_n = rotulo_puesto(dep2, mun3, zz2, pp2, dep_n, mun_n)
                stats["rot"] += 1
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
    if rotulos:
        print(f"   DES_PP rótulo estructural: {stats['rot']:,} ({stats['rot']/n*100:.3f}%)")
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
    enrich(csv_in, csv_out, rotulos="--rotulos" in sys.argv)


if __name__ == "__main__":
    main()
