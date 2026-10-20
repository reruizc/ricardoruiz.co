#!/usr/bin/env python3
"""
Consultas del Pacto Histórico 2025 (26-oct-2025) para el Centro de Descargas,
con NOMBRES de departamento, municipio y puesto y los votos como número.

Los crudos que estaban publicados traían solo códigos de la Registraduría
(`28 · 280 · 99 · 05`), sin ceros a la izquierda en el municipio, y el Excel
por mesa guardaba los votos como TEXTO (una suma o tabla dinámica no
funcionaba sin convertirlos). Además cada archivo traía las columnas en un
orden distinto.

Por cada consulta (presidencial · Cámara · Senado) emite cuatro variantes con
el mismo orden de columnas:
  GCS_2025CONSU{,_CAM,_SEN}.csv / .xlsx                 una fila por mesa
  GCS_2025CONSU{,_CAM,_SEN}_PUESTO.csv / .xlsx          agregado por puesto

Columnas: FUENTE FEC_ELEC COD_COR DES_COR COD_CIR DES_CIR
          COD_DDE DES_DDE COD_MME DES_MME COD_ZZ COD_PP DES_PP [DES_MS]
          COD_PAR DES_PAR COD_CAN DES_CAN NUM_VOT

Los nombres salen de las mismas fuentes que tools/build-csv-names (divipola +
georef 2026 + Divipol 2021) y lo que Divipole no nombra lleva el rótulo
estructural entre corchetes. El agregado por puesto se calcula aquí desde el
de mesa (no se reutiliza el viejo) y se valida contra el publicado.

Uso: python3 tools/build-consultas-2025-names/build.py [--src-dir=DIR]
Salida: Bases de datos/output_csv_names/consultas-2025/
"""
import csv
import sys
import time
from collections import OrderedDict
from pathlib import Path

ROOT = Path("/Users/ricardoruiz/ricardoruiz.co")
sys.path.insert(0, str(ROOT / "tools/build-csv-names"))
from build import load_maps, MUN_HISTORICOS, rotulo_puesto  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font  # noqa: E402

SRC_DEFAULT = ROOT / "Bases de datos/FINAL SUBIDA GCS"
OUT_DIR = ROOT / "Bases de datos/output_csv_names/consultas-2025"

ARCHIVOS = OrderedDict([
    ("GCS_2025CONSU", "Consulta presidencial del Pacto Histórico"),
    ("GCS_2025CONSU_CAM", "Consulta del Pacto Histórico a la Cámara de Representantes"),
    ("GCS_2025CONSU_SEN", "Consulta del Pacto Histórico al Senado de la República"),
])

COLS = ["FUENTE", "FEC_ELEC", "COD_COR", "DES_COR", "COD_CIR", "DES_CIR",
        "COD_DDE", "DES_DDE", "COD_MME", "DES_MME", "COD_ZZ", "COD_PP", "DES_PP",
        "DES_MS", "COD_PAR", "DES_PAR", "COD_CAN", "DES_CAN", "NUM_VOT"]
COLS_PUESTO = [c for c in COLS if c != "DES_MS"]

DESCRIPCION = {
    "FUENTE": "Archivo de origen de la Registraduría",
    "FEC_ELEC": "Fecha de la elección (26 de octubre de 2025)",
    "COD_COR": "Código de la corporación",
    "DES_COR": "Corporación",
    "COD_CIR": "Código de la circunscripción",
    "DES_CIR": "Circunscripción",
    "COD_DDE": "Código del departamento (Registraduría, NO DANE)",
    "DES_DDE": "Departamento",
    "COD_MME": "Código del municipio (Registraduría, NO DANE)",
    "DES_MME": "Municipio",
    "COD_ZZ": "Zona electoral",
    "COD_PP": "Puesto de votación dentro de la zona",
    "DES_PP": "Nombre del puesto de votación",
    "DES_MS": "Número de mesa",
    "COD_PAR": "Código del partido",
    "DES_PAR": "Partido",
    "COD_CAN": "Código del candidato",
    "DES_CAN": "Candidato (o votos nulos / no marcados)",
    "NUM_VOT": "Votos",
}


def leer(csv_in: Path, maps):
    """Lee el crudo de mesa y devuelve filas ya enriquecidas en el orden COLS."""
    dep_nombre, mun_nombre, puesto_nombre = maps
    filas, stats = [], {"pp_rot": 0, "mun_rot": 0}
    with csv_in.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            dep2 = r["COD_DDE"].strip().zfill(2)
            mun3 = r["COD_MME"].strip().zfill(3)
            zz2 = r["COD_ZZ"].strip().zfill(2)
            pp2 = r["COD_PP"].strip().zfill(2)
            dep_n = dep_nombre.get(dep2, "")
            mun_n = mun_nombre.get(f"{dep2}-{mun3}", "") or MUN_HISTORICOS.get(f"{dep2}-{mun3}", "")
            if not mun_n:
                mun_n = "[PAIS NO IDENTIFICADO]" if dep2 == "88" else "[MUNICIPIO NO IDENTIFICADO]"
                stats["mun_rot"] += 1
            pp_n = puesto_nombre.get(dep2 + mun3 + zz2 + pp2, "")
            if not pp_n:
                pp_n = rotulo_puesto(dep2, mun3, zz2, pp2, dep_n, mun_n)
                stats["pp_rot"] += 1
            filas.append([
                r["FUENTE"].strip(), r["FEC_ELEC"].strip(),
                r["COD_COR"].strip(), r["DES_COR"].strip(),
                r["COD_CIR"].strip(), r["DES_CIR"].strip(),
                dep2, dep_n, mun3, mun_n, zz2, pp2, pp_n,
                r["DES_MS"].strip(),
                r["COD_PAR"].strip(), r["DES_PAR"].strip(),
                r["COD_CAN"].strip(), r["DES_CAN"].strip(),
                int(r["NUM_VOT"]),
            ])
    return filas, stats


def agregar_puesto(filas):
    i_ms = COLS.index("DES_MS")
    acc = OrderedDict()
    for f in filas:
        k = tuple(f[:i_ms] + f[i_ms + 1:-1])
        acc[k] = acc.get(k, 0) + f[-1]
    return [list(k) + [v] for k, v in acc.items()]


def escribir_csv(path: Path, cols, filas):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        w.writerows(filas)


def escribir_xlsx(path: Path, cols, filas, titulo, nivel):
    wb = Workbook(write_only=True)
    lee = wb.create_sheet("Léeme")
    lee.column_dimensions["A"].width = 16
    lee.column_dimensions["B"].width = 70
    negrita = Font(bold=True)

    def celda(v, bold=False):
        from openpyxl.cell import WriteOnlyCell
        c = WriteOnlyCell(lee, value=v)
        if bold:
            c.font = negrita
        return c

    lee.append([celda(titulo, True)])
    lee.append([f"26 de octubre de 2025 · resultados {nivel} · fuente: Registraduría Nacional del Estado Civil"])
    lee.append([f"{len(filas):,} filas · {sum(f[-1] for f in filas):,} votos".replace(",", ".")])
    lee.append([])
    lee.append([celda("Columna", True), celda("Qué contiene", True)])
    for c in cols:
        lee.append([c, DESCRIPCION[c]])
    lee.append([])
    for nota in (
        "Los códigos son de la Registraduría y no coinciden con los del DANE (Antioquia es 01, no 05).",
        "Los nombres de puesto salen del censo electoral de 2026, o del de 2021 si el puesto ya no existe.",
        "Los rótulos entre corchetes ([CABECERA MUNICIPAL], [PUESTO RURAL · SIN NOMBRE EN DIVIPOLE]...)",
        "indican puestos sin nombre oficial en el censo; se deducen del código, no son el nombre real.",
        "Los votos nulos y no marcados vienen como filas aparte en DES_CAN.",
        "Datos de ricardoruiz.co · Centro de Descargas.",
    ):
        lee.append([nota])

    ws = wb.create_sheet("Datos")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{chr(64 + len(cols))}{len(filas) + 1}"
    from openpyxl.cell import WriteOnlyCell
    head = []
    for c in cols:
        hc = WriteOnlyCell(ws, value=c)
        hc.font = negrita
        head.append(hc)
    ws.append(head)
    for f in filas:
        ws.append(f)
    wb.save(path)


def validar_puesto(nuevas, viejo: Path):
    """El agregado nuevo debe dar el mismo voto por (puesto, candidato) que el publicado."""
    if not viejo.exists():
        return "sin archivo viejo para comparar"
    def clave(dep, mun, zz, pp, par, can):
        return (dep.strip().zfill(2), mun.strip().zfill(3), zz.strip().zfill(2),
                pp.strip().zfill(2), par.strip(), can.strip())
    vie = {}
    with viejo.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            k = clave(r["COD_DDE"], r["COD_MME"], r["COD_ZZ"], r["COD_PP"], r["COD_PAR"], r["COD_CAN"])
            vie[k] = vie.get(k, 0) + int(r["NUM_VOT"])
    nue = {}
    ix = [COLS_PUESTO.index(c) for c in ("COD_DDE", "COD_MME", "COD_ZZ", "COD_PP", "COD_PAR", "COD_CAN")]
    for f in nuevas:
        k = clave(*[f[i] for i in ix])
        nue[k] = nue.get(k, 0) + f[-1]
    if nue != vie:
        dif = sum(1 for k in set(nue) | set(vie) if nue.get(k) != vie.get(k))
        raise SystemExit(f"✗ el agregado por puesto NO cuadra con {viejo.name}: {dif} claves distintas")
    return f"cuadra con {viejo.name} ({len(vie):,} claves)"


def main():
    src_dir = SRC_DEFAULT
    viejos = None
    for a in sys.argv[1:]:
        if a.startswith("--src-dir="):
            src_dir = Path(a.split("=", 1)[1])
        if a.startswith("--viejos="):
            viejos = Path(a.split("=", 1)[1])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    maps = load_maps()
    for base, titulo in ARCHIVOS.items():
        t0 = time.time()
        filas, st = leer(src_dir / f"{base}.csv", maps)
        puesto = agregar_puesto(filas)
        tot = sum(f[-1] for f in filas)
        assert tot == sum(f[-1] for f in puesto)
        escribir_csv(OUT_DIR / f"{base}.csv", COLS, filas)
        escribir_csv(OUT_DIR / f"{base}_PUESTO.csv", COLS_PUESTO, puesto)
        escribir_xlsx(OUT_DIR / f"{base}.xlsx", COLS, filas, titulo, "por mesa")
        escribir_xlsx(OUT_DIR / f"{base}_PUESTO.xlsx", COLS_PUESTO, puesto, titulo, "por puesto de votación")
        print(f"{base}: {len(filas):,} filas mesa · {len(puesto):,} puesto · {tot:,} votos "
              f"· puestos con rótulo {st['pp_rot']:,} · municipios sin nombre {st['mun_rot']:,} "
              f"· {time.time() - t0:.0f}s")
        if viejos:
            print("   " + validar_puesto(puesto, viejos / f"{base}_PUESTO.csv"))


if __name__ == "__main__":
    main()
