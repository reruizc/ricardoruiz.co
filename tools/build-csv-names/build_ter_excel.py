#!/usr/bin/env python3
"""
Excel con nombres de los crudos TERRITORIALES (Centro de Descargas · nov-2026).

Para cada año (2011 · 2015 · 2019 · 2023) produce, a partir de los CSV que ya
llevan nombres (salida de build_historicos.py, validados al voto):

  GCS_<año>TER_PUESTO.xlsx    agregado por puesto, un solo libro
                              (≈2 M de filas → hojas «Datos», «Datos 2»…)
  GCS_<año>TER_BY_DEPTO.zip   por mesa, un Excel por departamento adentro
                              (13-21 M de filas no caben en un libro)

Cada libro lleva una hoja «Léeme» primero: elección, nivel, filas y votos del
libro, corporaciones (los códigos COD_COR cambian por año), qué es cada columna
y de dónde sale el nombre del puesto.

Convenciones del Excel (iguales para los cuatro años):
  · Mismo orden de columnas en todos los años. 2011 trae en el CSV NUM_VOT antes
    de partido y DES_MM (municipio en mayúsculas, de la fuente); aquí va como en
    los demás años, con DES_MME.
  · Sin FUENTE ni FEC_ELEC (constantes: van en el Léeme).
  · Códigos de lugar como TEXTO con ceros a la izquierda (Antioquia «01», no 1):
    COD_DDE 2 · COD_MME 3 · COD_ZZ 2 · COD_PP 2. Votos como número.
  · DES_PP solo en 2019 (censo 2019) y 2023 (censo 2023). 2011 y 2015 no lo
    llevan: no existe censo por puesto de esos años (ver build_historicos.py).

Validación: los totales por (COD_DDE, COD_MME, COD_COR, COD_PAR, COD_CAN) y el número de filas se
calculan DE NUEVO desde el CSV original de la Registraduría («FINAL SUBIDA GCS»)
y se comparan con lo que se lee de vuelta de cada .xlsx ya escrito (calamine).
Si algo no cuadra, el script sale con error y no deja el archivo como bueno.

Uso:
  /opt/homebrew/bin/python3.14 tools/build-csv-names/build_ter_excel.py 2019 [puesto|mesa] [--validar]
  (--validar relee los .xlsx/.zip ya generados contra la fuente, sin reescribirlos)
Salida: Bases de datos/output_csv_names/historicos/excel/
"""
import csv
import json
import sys
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import xlsxwriter

ROOT = Path("/Users/ricardoruiz/ricardoruiz.co")
SRC = ROOT / "Bases de datos/FINAL SUBIDA GCS"
NOMB = ROOT / "Bases de datos/output_csv_names/historicos"
OUT = NOMB / "excel"
MAX_FILAS = 1_048_575          # filas de datos por hoja (+1 de encabezado)

FECHA = {2011: "30 de octubre de 2011", 2015: "25 de octubre de 2015",
         2019: "27 de octubre de 2019", 2023: "29 de octubre de 2023"}
FUENTE_PP = {2019: "censo electoral de 2019 por puesto (Registraduría, autoridades territoriales)",
             2023: "censo electoral de 2023 por puesto (Registraduría, autoridades territoriales)"}

COLS = ["FUENTE", "FEC_ELEC", "COD_COR", "DES_COR", "COD_CIR", "DES_CIR",
        "COD_DDE", "DES_DDE", "COD_MME", "DES_MME", "COD_ZZ", "COD_PP", "DES_PP",
        "DES_MS", "COD_PAR", "DES_PAR", "COD_CAN", "DES_CAN", "NUM_VOT"]
PAD = {"COD_DDE": 2, "COD_MME": 3, "COD_ZZ": 2, "COD_PP": 2}
NUM = {"COD_COR", "COD_CIR", "COD_PAR", "COD_CAN", "NUM_VOT"}
ANCHO = {"FUENTE": 18, "FEC_ELEC": 17, "DES_COR": 14, "DES_CIR": 15, "DES_DDE": 20,
         "DES_MME": 22, "DES_PP": 34, "DES_PAR": 40, "DES_CAN": 36}
DESCRIPCION = {
    "FUENTE": "Archivo de origen de la Registraduría",
    "FEC_ELEC": "Fecha de la elección",
    "COD_COR": "Código de la corporación (cambia de un año a otro: ver la tabla de abajo)",
    "DES_COR": "Corporación: gobernación, asamblea, alcaldía, concejo y, en 2011 y 2015, JAL",
    "COD_CIR": "Código de la circunscripción",
    "DES_CIR": "Circunscripción (departamental, municipal…)",
    "COD_DDE": "Código de departamento de la Registraduría (no es el del DANE: Antioquia es 01)",
    "DES_DDE": "Nombre del departamento",
    "COD_MME": "Código de municipio de la Registraduría",
    "DES_MME": "Nombre del municipio",
    "COD_ZZ": "Zona electoral (en Bogotá y otras ciudades, la zona sigue a la localidad o comuna)",
    "COD_PP": "Puesto de votación dentro de la zona",
    "DES_PP": "Nombre del puesto según el censo electoral de ese mismo año",
    "DES_MS": "Número de mesa",
    "COD_PAR": "Código del partido o movimiento",
    "DES_PAR": "Partido o movimiento",
    "COD_CAN": "Código del candidato. 0 = voto solo por la lista (el logo). Los votos en blanco, nulos y no marcados van en filas aparte",
    "DES_CAN": "Candidato (o VOTOS EN BLANCO, VOTOS NULOS, VOTOS NO MARCADOS)",
    "NUM_VOT": "Votos",
}


def ascii_up(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() else "_" for c in s.upper()).strip("_")


def fila_estandar(row, idx):
    """Fila del CSV con nombres → valores en el orden COLS (None si la columna no existe)."""
    out = []
    for c in COLS:
        i = idx.get(c)
        if i is None:
            out.append(None)
            continue
        v = row[i].strip() if i < len(row) else ""
        if c in PAD:
            v = v.zfill(PAD[c]) if v.isdigit() else v
        elif c in NUM:
            v = int(v) if v.lstrip("-").isdigit() else (0 if c == "NUM_VOT" else v)
        elif c == "DES_MS" and v.isdigit():
            v = int(v)
        out.append(v)
    return out


def indices(cab):
    idx = {c: cab.index(c) for c in COLS if c in cab}
    if "DES_MME" not in idx and "DES_MM" in cab:      # 2011 mesa
        idx["DES_MME"] = cab.index("DES_MM")
    return idx


# ─── Totales de control, desde el CSV ORIGINAL (no el enriquecido) ─────────
def totales_fuente(anio):
    ruta = SRC / f"GCS_{anio}TER.csv"
    tot, n = Counter(), 0
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f, delimiter=";")
        h = next(rd)
        ic, ip, ik, iv = (h.index(c) for c in ("COD_COR", "COD_PAR", "COD_CAN", "NUM_VOT"))
        idd, imm = h.index("COD_DDE"), h.index("COD_MME")
        for r in rd:
            if len(r) <= max(ic, ip, ik, iv, idd, imm):
                continue
            n += 1
            try:
                v = int(r[iv] or 0)
            except ValueError:
                v = 0
            tot[(r[idd].strip(), r[imm].strip(), r[ic].strip(), r[ip].strip(), r[ik].strip())] += v
    return n, tot


# ─── Escritura ─────────────────────────────────────────────────────────────
class Libro:
    """Un .xlsx en modo memoria constante: Léeme + Datos (+ Datos 2…)."""

    def __init__(self, ruta, cols, titulo):
        self.ruta, self.cols, self.titulo = ruta, cols, titulo
        self.wb = xlsxwriter.Workbook(str(ruta), {"constant_memory": True})
        self.neg = self.wb.add_format({"bold": True})
        self.cab = self.wb.add_format({"bold": True, "bg_color": "#1F2A44", "font_color": "#FFFFFF"})
        self.miles = self.wb.add_format({"num_format": "#,##0"})
        self.lee = self.wb.add_worksheet("Léeme")
        self.lee.set_column(0, 0, 18)
        self.lee.set_column(1, 1, 96)
        self.hojas, self.ws, self.en_hoja = [], None, 0
        self.n, self.votos, self.cors = 0, 0, Counter()
        self.iv = cols.index("NUM_VOT")
        self.icod, self.ides = cols.index("COD_COR"), cols.index("DES_COR")

    def _nueva_hoja(self):
        if self.ws is not None:
            self.ws.autofilter(0, 0, self.en_hoja, len(self.cols) - 1)
        k = len(self.hojas) + 1
        ws = self.wb.add_worksheet("Datos" if k == 1 else f"Datos {k}")
        ws.freeze_panes(1, 0)
        for j, c in enumerate(self.cols):
            ws.set_column(j, j, ANCHO.get(c, 10), self.miles if c == "NUM_VOT" else None)
            ws.write_string(0, j, c, self.cab)
        self.hojas.append(ws)
        self.ws, self.en_hoja = ws, 0

    def fila(self, valores):
        if self.ws is None or self.en_hoja >= MAX_FILAS:
            self._nueva_hoja()
        self.en_hoja += 1
        r = self.en_hoja
        for j, v in enumerate(valores):
            if v is None or v == "":
                continue
            if isinstance(v, int):
                self.ws.write_number(r, j, v)
            else:
                self.ws.write_string(r, j, v)
        self.n += 1
        self.votos += valores[self.iv]
        self.cors[(valores[self.icod], valores[self.ides])] += valores[self.iv]

    def cerrar(self, lineas_extra):
        if self.ws is not None:
            self.ws.autofilter(0, 0, self.en_hoja, len(self.cols) - 1)
        le, r = self.lee, 0

        def w(texto, fmt=None, col=0):
            le.write_string(r, col, texto, fmt) if fmt else le.write_string(r, col, texto)

        w(self.titulo, self.neg); r += 1
        for t in lineas_extra:
            w(t); r += 1
        w(f"{self.n:,} filas · {self.votos:,} votos · {len(self.hojas)} hoja(s) de datos".replace(",", ".")); r += 1
        if len(self.hojas) > 1:
            w("Excel admite 1.048.576 filas por hoja: los datos siguen en «Datos 2», «Datos 3»…, con el mismo encabezado."); r += 1
        r += 1
        w("Corporación", self.neg); w("Código (COD_COR) y votos en este libro", self.neg, 1); r += 1
        for (cod, des), v in sorted(self.cors.items(), key=lambda x: (str(x[0][0]).zfill(3))):
            w(str(des)); w(f"{cod} · {v:,} votos".replace(",", "."), col=1); r += 1
        r += 1
        w("Columna", self.neg); w("Qué contiene", self.neg, 1); r += 1
        for c in self.cols:
            w(c); w(DESCRIPCION[c], col=1); r += 1
        self.wb.close()
        return self.n, self.votos


def notas(anio):
    pp = (f"Nombre del puesto (DES_PP): {FUENTE_PP[anio]}. El código de un puesto no siempre es el mismo "
          "lugar de una elección a otra, por eso no se usa el censo de 2026."
          if anio in FUENTE_PP else
          f"No hay nombre de puesto: no existe censo por puesto de {anio} y el código de un puesto no siempre es "
          "el mismo lugar años después, así que nombrarlo con un censo posterior podría poner los votos en otro sitio. "
          "El puesto se identifica por zona (COD_ZZ) y número (COD_PP).")
    return [
        f"Elecciones de autoridades territoriales del {FECHA[anio]} · fuente: Registraduría Nacional del Estado Civil "
        f"(archivo GCS_{anio}TER, «{anio}_Territoriales»)",
        "Los nombres de departamento y municipio se agregaron junto a cada código; el resto es el dato original.",
        pp,
        "Los rótulos entre corchetes ([CABECERA MUNICIPAL], [PUESTO RURAL · SIN NOMBRE EN DIVIPOLE]…) se deducen del "
        "código: no son el nombre real del puesto." if anio in FUENTE_PP else "",
        "Datos de ricardoruiz.co · Centro de Descargas.",
    ]


# FUENTE y FEC_ELEC son constantes en todo el archivo: van en el Léeme y no en
# cada fila (aligera el libro ~10 %; el CSV las conserva).
def cols_de(anio):
    return [c for c in COLS if c not in ("FUENTE", "FEC_ELEC")
            and not (c == "DES_PP" and anio not in FUENTE_PP)]


def generar_puesto(anio):
    entrada = NOMB / f"GCS_{anio}TER_PUESTO.csv"
    salida = OUT / f"GCS_{anio}TER_PUESTO.xlsx"
    cols = [c for c in cols_de(anio) if c != "DES_MS"]
    libro = Libro(salida, cols, f"Territoriales {anio} · resultados por puesto de votación")
    with entrada.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f, delimiter=";")
        idx = indices(next(rd))
        sel = [COLS.index(c) for c in cols]
        for row in rd:
            v = fila_estandar(row, idx)
            libro.fila([v[i] for i in sel])
    libro.cerrar([t for t in notas(anio) if t])
    return [salida]


def generar_mesa(anio):
    entrada = NOMB / f"GCS_{anio}TER.csv"
    tmp = OUT / f"_tmp_{anio}"
    tmp.mkdir(parents=True, exist_ok=True)
    cols = cols_de(anio)
    sel = [COLS.index(c) for c in cols]
    libros = {}
    with entrada.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f, delimiter=";")
        idx = indices(next(rd))
        for k, row in enumerate(rd, 1):
            v = fila_estandar(row, idx)
            dd, dn = v[COLS.index("COD_DDE")], v[COLS.index("DES_DDE")] or "SIN_NOMBRE"
            lb = libros.get(dd)
            if lb is None:
                ruta = tmp / f"{dd}_{ascii_up(dn)}.xlsx"
                lb = libros[dd] = Libro(ruta, cols, f"Territoriales {anio} · {dn} · resultados por mesa")
            lb.fila([v[i] for i in sel])
            if k % 2_000_000 == 0:
                print(f"   {anio} mesa: {k:,} filas…", flush=True)
    for dd, lb in libros.items():
        lb.cerrar([t for t in notas(anio) if t])
    zip_out = OUT / f"GCS_{anio}TER_BY_DEPTO.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for dd in sorted(libros):
            zf.write(libros[dd].ruta, arcname=libros[dd].ruta.name)
    return [zip_out], [libros[dd].ruta for dd in sorted(libros)], tmp


# ─── Relectura del Excel escrito ───────────────────────────────────────────
def leer_xlsx(ruta):
    from python_calamine import CalamineWorkbook
    wb = CalamineWorkbook.from_path(str(ruta))
    tot, n = Counter(), 0
    hojas = [s for s in wb.sheet_names if s.startswith("Datos")]
    for s in hojas:
        filas = wb.get_sheet_by_name(s).to_python()
        cab = [str(c) for c in filas[0]]
        ic, ip, ik, iv = (cab.index(c) for c in ("COD_COR", "COD_PAR", "COD_CAN", "NUM_VOT"))
        idd, imm = cab.index("COD_DDE"), cab.index("COD_MME")
        for r in filas[1:]:
            n += 1
            assert isinstance(r[idd], str) and len(r[idd]) == 2, f"COD_DDE no es texto de 2: {r[idd]!r}"
            assert isinstance(r[imm], str) and len(r[imm]) == 3, f"COD_MME no es texto de 3: {r[imm]!r}"
            tot[(str(int(r[idd])), str(int(r[imm])), str(int(r[ic])), str(int(r[ip])), str(int(r[ik])))] += int(r[iv])
    return n, tot, len(hojas)


def comparar(nombre, n_f, tot_f, n_x, tot_x, filas_esperadas=None):
    ok = True
    if filas_esperadas is not None and n_x != filas_esperadas:
        print(f"   ✗ {nombre}: {n_x:,} filas en el Excel, {filas_esperadas:,} en el CSV con nombres")
        ok = False
    norm = Counter({tuple(str(int(x)) for x in llave): v for llave, v in tot_f.items()
                    if all(x.lstrip("-").isdigit() for x in llave)})
    descartadas = sum(v for llave, v in tot_f.items() if not all(x.lstrip("-").isdigit() for x in llave))
    if descartadas:
        print(f"   ✗ {nombre}: {descartadas:,} votos de la fuente con códigos no numéricos")
        ok = False
    if norm != tot_x:
        dif = [(k, norm.get(k, 0), tot_x.get(k, 0)) for k in set(norm) | set(tot_x) if norm.get(k, 0) != tot_x.get(k, 0)]
        print(f"   ✗ {nombre}: {len(dif)} combinaciones municipio·corporación·partido·candidato no cuadran, p.ej. {dif[:5]}")
        ok = False
    esp = sum(v for llave, v in norm.items() if llave[-1] in {"996", "997", "998", "999"})
    print(f"   {'✓' if ok else '✗'} {nombre}: {n_x:,} filas · {sum(tot_x.values()):,} votos · "
          f"blanco/nulos/no marcados {esp:,} · {len(tot_x):,} combinaciones municipio·corporación·partido·candidato", flush=True)
    return ok


def main():
    anio = int(sys.argv[1])
    validar = "--validar" in sys.argv          # relee lo ya generado, sin reescribir
    que = [a for a in sys.argv[2:] if not a.startswith("-")] or ["puesto", "mesa"]
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    n_src, tot_src = totales_fuente(anio)
    print(f"{anio}: fuente {n_src:,} filas mesa · {sum(tot_src.values()):,} votos", flush=True)
    ok = True
    if "puesto" in que:
        (sal,) = [OUT / f"GCS_{anio}TER_PUESTO.xlsx"] if validar else generar_puesto(anio)
        n_x, tot_x, hojas = leer_xlsx(sal)
        with (NOMB / f"GCS_{anio}TER_PUESTO.csv").open(encoding="utf-8-sig") as f:
            filas = sum(1 for _ in f) - 1
        ok &= comparar(f"{sal.name} ({hojas} hojas, {sal.stat().st_size/2**20:.1f} MB)",
                       n_src, tot_src, n_x, tot_x, filas)
    if "mesa" in que:
        if validar:
            zip_out, tmp = OUT / f"GCS_{anio}TER_BY_DEPTO.zip", OUT / f"_val_{anio}"
            tmp.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_out) as zf:
                zf.extractall(tmp)
                libros = [tmp / m for m in sorted(zf.namelist())]
        else:
            (zip_out,), libros, tmp = generar_mesa(anio)
        n_t, tot_t = 0, Counter()
        for lb in libros:
            n_x, tot_x, _ = leer_xlsx(lb)
            n_t += n_x
            tot_t.update(tot_x)
        ok &= comparar(f"{zip_out.name} ({len(libros)} deptos, {zip_out.stat().st_size/2**20:.1f} MB)",
                       n_src, tot_src, n_t, tot_t, n_src)
        if ok:
            for lb in libros:
                lb.unlink()
            tmp.rmdir()
    print(f"{anio}: {time.time() - t0:.0f} s", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
