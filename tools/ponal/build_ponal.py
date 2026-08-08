#!/usr/bin/env python3
"""
build_ponal.py — agrega la base de delitos de la Policía Nacional 2015-2024.

    python3 tools/ponal/build_ponal.py [--limite N]

Lee de un solo tirón `Bases de datos/PONAL/BD-PONAL-15-24.csv` (8,4 GB,
8.564.219 filas) y emite los agregados que consume el hub de policía:

    Bases de datos/output_ponal/
      meta.json        catálogo de delitos, años, totales y notas de calidad
      nacional.json    series nacionales (año, mes, día, hora, zona, perfil)
      deptos.json      departamento × delito × año
      municipios.json  municipio (DANE) × delito × año

Las cuatro trampas de la fuente, y cómo se tratan aquí
------------------------------------------------------
① El lote de 2024 llegó con OTRA convención de nombres: los archivos de
   2015-2023 traen `hurto personas` y los de 2024 el nombre de la hoja de
   Excel, `HURTO A PERSONAS dic/Sheet1`. Son 37 etiquetas para 21 delitos.
   Sin el mapa `CANON` de abajo, 2024 no desaparece con un error: da CERO,
   que es peor. Cada etiqueta nueva que aparezca aborta el build a propósito
   (ver `canon()`), en vez de irse en silencio a una bolsa de "otros".

② Bogotá viene DENTRO de Cundinamarca en la columna `Departamento` (ese
   departamento pesa 35% del archivo por eso). El departamento se deriva de
   los dos primeros dígitos del código DANE, no de esa columna, y así 11
   (Bogotá D.C.) y 25 (Cundinamarca) quedan separados solos.

③ El nombre del municipio viene con mayúsculas mezcladas — `BOGOTÁ D.C. (CT)`
   y `Bogotá D.C. (CT)` son filas distintas — y produce 2.209 municipios donde
   hay 1.105. La llave es `Hechos.CODIGO_DANE`, que sí está limpio; el nombre
   se resuelve por moda (la grafía más frecuente de ese código).

④ 676.289 filas (7,9%) no traen año. No es parejo: golpea amenazas (59%),
   hurto a comercios (60%) y delitos sexuales (58%). Traen mes y día de
   semana, pero sin año no hay serie posible, así que entran a los totales y
   al perfil y se EXCLUYEN de todo lo que sea temporal. El conteo va en
   `meta.json` para poder declararlo en la página.

Notas menores de la fuente:
  · `Cantidad` no siempre es 1 (suma 8.853.912 sobre 8.564.219 filas) → se
    suma, nunca se cuentan filas.
  · `Hora` usa la época de Excel (`30/12/1899 6:00:00`): la fecha es basura,
    la hora sirve.
  · `Calend.MES` está 39% vacío y con dos convenciones (`oct.` y `oct`) → el
    mes se deriva de `Fecha`, no de esa columna.
  · Se ignoran `Grupo de Edad` (97% vacío), `LINEA` (mal nombrada: es la
    línea del vehículo hurtado) y `COMUNAS_ZONAS_DESCRIPCION` (86,5% vacío y
    con nombres corrompidos por un reemplazo de texto: `UPZ No. 14 USAQUEN
    ENO REPORTADO1`).
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10 ** 9)

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "Bases de datos" / "PONAL" / "BD-PONAL-15-24.csv"
OUT = RAIZ / "Bases de datos" / "output_ponal"

# ── delitos ────────────────────────────────────────────────────────────
# Cada delito: id corto, rótulo, y las etiquetas crudas que lo alimentan.
# El primer grupo tiene serie 2015-2024; el segundo SOLO existe en 2024
# (la Policía los empezó a entregar en ese lote) → se marcan `solo_2024`
# para que la página no dibuje una tendencia que no existe.
DELITOS = [
    ("homicidios",        "Homicidios",                    ["homicidios", "HOMICIDIOS dic/Sheet1"]),
    ("lesiones",          "Lesiones personales",           ["lesiones", "LESIONES PERSONALES dic/Sheet1"]),
    ("violencia_intra",   "Violencia intrafamiliar",       ["violencia intra", "Violencia Intrafamiliar"]),
    ("delitos_sexuales",  "Delitos sexuales",              ["delitos sexuales", "DELITOS SEXUALES dic/Sheet1"]),
    ("amenazas",          "Amenazas",                      ["amenazas", "AMENAZAS dic/Sheet1"]),
    ("extorsiones",       "Extorsión",                     ["extorsiones", "EXTORSION dic/Sheet1"]),
    ("secuestros",        "Secuestro",                     ["secuestros", "SECUESTRO dic/Sheet1"]),
    ("terrorismo",        "Terrorismo",                    ["terrorismo", "TERRORISMO dic/Sheet1"]),
    ("hurto_personas",    "Hurto a personas",              ["hurto personas", "HURTO A PERSONAS dic/Sheet1"]),
    ("hurto_celulares",   "Hurto de celulares",            ["hurto celulares", "HURTO A CELULAR dic/Sheet1"]),
    ("hurto_comercios",   "Hurto a comercios",             ["hurto comercios", "HURTO A COMERCIO dic/Sheet1"]),
    ("hurto_residencias", "Hurto a residencias",           ["hurto residencias", "Hurto a Residencias"]),
    ("hurto_motos",       "Hurto de motocicletas",         ["hurto motos", "HURTO MOTOCICLETAS dic/Sheet1"]),
    ("hurto_autos",       "Hurto de automotores",          ["hurto autos", "HURTO AUTOMOTORES dic/Sheet1"]),
    ("del_informaticos",  "Delitos informáticos",          ["del informaticos", "DELITOS INFORMATICOS dic/Sheet1"]),
    ("homicidios_at",     "Homicidios en acc. de tránsito", ["homicidios acc transito", "HOMICIDIOS AT dic/Sheet1"]),
    # solo 2024
    ("lesiones_at",       "Lesiones en acc. de tránsito",  ["LESIONES EN ACCIDENTES DE TRANSITO dic/Sheet1"]),
    ("hurto_bicicletas",  "Hurto de bicicletas",           ["HURTO BICICLETAS dic/Sheet1"]),
    ("hurto_ganado",      "Hurto de ganado",               ["HURTO A CABEZAS DE GANADO dic/Sheet1"]),
    ("pirateria",         "Piratería terrestre",           ["HURTO PIRATERIA TERRESTRE dic/Sheet1"]),
    ("hurto_financieras", "Hurto a entidades financieras", ["HURTO ENTIDADES FINANCIERAS dic/Sheet1"]),
]
SOLO_2024 = {"lesiones_at", "hurto_bicicletas", "hurto_ganado", "pirateria", "hurto_financieras"}

DID = {d[0]: i for i, d in enumerate(DELITOS)}
CANON = {}
for _id, _lab, _raws in DELITOS:
    for _r in _raws:
        CANON[_r.strip().lower()] = _id

# ── departamentos DANE ─────────────────────────────────────────────────
# Los dos primeros dígitos del código DANE. Es lo que separa a Bogotá (11)
# de Cundinamarca (25), que en la columna `Departamento` van pegados.
DEPTOS = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá D.C.", "13": "Bolívar",
    "15": "Boyacá", "17": "Caldas", "18": "Caquetá", "19": "Cauca",
    "20": "Cesar", "23": "Córdoba", "25": "Cundinamarca", "27": "Chocó",
    "41": "Huila", "44": "La Guajira", "47": "Magdalena", "50": "Meta",
    "52": "Nariño", "54": "Norte de Santander", "63": "Quindío",
    "66": "Risaralda", "68": "Santander", "70": "Sucre", "73": "Tolima",
    "76": "Valle del Cauca", "81": "Arauca", "85": "Casanare",
    "86": "Putumayo", "88": "San Andrés y Providencia", "91": "Amazonas",
    "94": "Guainía", "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
}

# ── ciudades ───────────────────────────────────────────────────────────
# `Hechos.COMUNAS_ZONAS_DESCRIPCION` está 87% VACÍA y lo poco que trae viene
# corrupto, así que no sirve. Pero `Hechos.BARRIOS_HECHO` está llena al 100% en
# las ciudades grandes y **en tres de ellas el nombre trae la comuna pegada
# como sufijo**: `EL POBLADO C-14` · `BOSA E-7` · `LILI E17`. De ahí sale el
# mapa por comuna, sin depender de la columna rota.
#
# ⚠️ MEDIDO: ese sufijo SOLO existe en Bogotá (89,6%), Medellín (83,1%) y Cali
# (96,7%). En Bucaramanga, Cúcuta, Ibagué, Manizales, Montería, Neiva, Popayán
# y Villavicencio la cobertura es 0,0% — sus barrios no traen código de comuna.
# Por eso el mapa por comuna es de tres ciudades y el resto va con ranking de
# barrios. Inventarles la comuna a las otras ocho sería inventar el mapa.
#
# `geo`/`prop` es el polígono y el campo con el número de comuna; el frontend
# casa por NÚMERO, que es lo único estable entre fuentes.
CIUDADES = {
    "11001": {"n": "Bogotá",   "geo": "BOG-LOCALIDADX.json", "prop": "LocCodigo", "tipo": "localidad",
              "suf": r"\s+E-?\s?(\d{1,2})$", "rot": True},
    "05001": {"n": "Medellín", "geo": "MEDELLINX.json",      "prop": "CODIGO",    "tipo": "comuna",
              "suf": r"\s+C-?\s?(\d{1,2})$", "rot": False},
    "76001": {"n": "Cali",     "geo": "CALIX.json",          "prop": "comuna",    "tipo": "comuna",
              "suf": r"\s+E-?\s?(\d{1,2})$", "rot": False},
}
# Ciudades sin mapa de comuna pero con ranking de barrios (el dato está, lo que
# falta es el código de comuna en el nombre).
CIUDADES_SOLO_BARRIO = {
    "08001": "Barranquilla", "13001": "Cartagena", "68001": "Bucaramanga",
    "54001": "Cúcuta", "73001": "Ibagué", "17001": "Manizales", "23001": "Montería",
    "41001": "Neiva", "19001": "Popayán", "50001": "Villavicencio", "66001": "Pereira",
    "52001": "Pasto", "47001": "Santa Marta", "63001": "Armenia", "20001": "Valledupar",
    "08758": "Soledad", "25754": "Soacha",
}
# marcador de nulo de la fuente: no es un barrio
BARRIO_NULO = "PENDIENTE POR ASIGNAR"

ANIOS = list(range(2015, 2025))
AIX = {a: i for i, a in enumerate(ANIOS)}
NA = len(ANIOS)

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIX = {d: i for i, d in enumerate(DIAS)}
# bandas de edad: los cortes son los del Código de Infancia (14/18) y luego
# tramos laborales; la fuente trae la edad exacta en el 79% de las filas
EDAD_CORTES = [(0, 13), (14, 17), (18, 25), (26, 35), (36, 45), (46, 60), (61, 200)]
EDAD_LAB = ["0-13", "14-17", "18-25", "26-35", "36-45", "46-60", "61+"]

RE_FECHA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
RE_HORA = re.compile(r"\b(\d{1,2}):\d{2}")
VACIO = {"", "-", "NO REPORTADO", "NO REPORTA", "SIN DATO", "NULL"}


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def bonito(nom):
    """`BOGOTÁ D.C. (CT)` → `Bogotá D.C.`  ·  `EL SANTUARIO` → `El Santuario`."""
    s = re.sub(r"\s*\(CT\)\s*$", "", nom.strip())
    s = s.lower()
    s = re.sub(r"(^|[ \-'])(\w)", lambda m: m.group(1) + m.group(2).upper(), s)
    # las siglas quedan bien: D.c. → D.C.
    return re.sub(r"\bD\.c\.", "D.C.", s)


def limpio(v):
    v = (v or "").strip()
    return "" if v.upper() in VACIO else v


def banda_edad(v):
    try:
        e = int(v)
    except (TypeError, ValueError):
        return None
    if e < 0 or e > 120:
        return None
    for i, (lo, hi) in enumerate(EDAD_CORTES):
        if lo <= e <= hi:
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0, help="procesar solo N filas (prueba)")
    args = ap.parse_args()

    if not SRC.exists():
        sys.exit(f"no encuentro {SRC}")
    OUT.mkdir(parents=True, exist_ok=True)

    f = SRC.open(encoding="utf-8-sig", newline="")
    rd = csv.reader(f, delimiter=";")
    hdr = next(rd)
    ix = {c: i for i, c in enumerate(hdr)}
    ncol = len(hdr)
    need = ["Nombre Delitos", "Cantidad", "Fecha", "Hora", "Día", "Hechos.CODIGO_DANE",
            "Hechos.MUNICIPIO_HECHO", "Hechos.ZONA", "Person.GENERO", "Person.EDAD",
            "Arma empleada", "Clase de sitio"]
    falta = [c for c in need if c not in ix]
    if falta:
        sys.exit(f"al CSV le faltan columnas: {falta}")

    # acumuladores
    nac_anio = defaultdict(int)      # (delito, anio) -> n
    nac_mes = defaultdict(int)       # (delito, mes)
    nac_dia = defaultdict(int)       # (delito, diasem)
    nac_hora = defaultdict(int)      # (delito, hora)
    nac_zona = defaultdict(int)      # (delito, zona)
    nac_gen = defaultdict(int)       # (delito, genero)
    nac_edad = defaultdict(int)      # (delito, banda)
    nac_arma = defaultdict(int)      # (delito, arma)
    nac_sitio = defaultdict(int)     # (delito, sitio)
    nac_mag = defaultdict(int)       # (delito, móvil del agresor)
    nac_mvi = defaultdict(int)       # (delito, móvil de la víctima)
    # ciudades: comuna × delito × año, y barrio × delito (sin año, por tamaño)
    ciu_com = defaultdict(int)       # (dane, comuna, delito, anio)
    ciu_com_t = defaultdict(int)     # (dane, comuna, delito)
    ciu_bar = defaultdict(int)       # (dane, barrio, delito)
    ciu_bar_com = {}                 # (dane, barrio) -> comuna
    ciu_tot = defaultdict(int)       # dane -> hechos
    ciu_sin_com = defaultdict(int)   # dane -> hechos sin comuna derivable
    SUF = {d: re.compile(c["suf"]) for d, c in CIUDADES.items()}
    dep_anio = defaultdict(int)      # (dep, delito, anio)
    dep_tot = defaultdict(int)       # (dep, delito)  incluye filas sin año
    mun_anio = defaultdict(int)      # (dane, delito, anio)
    mun_tot = defaultdict(int)       # (dane, delito)
    mun_nom = defaultdict(Counter)   # dane -> Counter(nombre)
    total_delito = defaultdict(int)
    sin_anio = defaultdict(int)      # delito -> n sin año
    fuera_rango = defaultdict(int)   # anio -> n  (fechas fuera de 2015-2024)
    sin_dane = 0
    etiquetas_nuevas = Counter()
    n = filas = 0

    for row in rd:
        n += 1
        if args.limite and n > args.limite:
            break
        if len(row) != ncol:
            continue
        bruto = row[ix["Nombre Delitos"]].strip().lower()
        did = CANON.get(bruto)
        if did is None:
            etiquetas_nuevas[bruto] += 1
            continue
        try:
            q = int(row[ix["Cantidad"]] or 1)
        except ValueError:
            q = 1
        if q <= 0:
            q = 1
        filas += q
        total_delito[did] += q

        # ── tiempo ──────────────────────────────────────────────────
        anio = None
        m = RE_FECHA.match(row[ix["Fecha"]].strip())
        if m:
            dd, mm, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if yy in AIX and 1 <= mm <= 12:
                anio = yy
                nac_mes[(did, mm - 1)] += q
            else:
                fuera_rango[yy] += q
        else:
            sin_anio[did] += q
        if anio is not None:
            nac_anio[(did, anio)] += q

        # día de semana y hora vienen completos aunque falte el año
        d = DIX.get(row[ix["Día"]].strip())
        if d is not None:
            nac_dia[(did, d)] += q
        mh = RE_HORA.search(row[ix["Hora"]])
        if mh:
            h = int(mh.group(1))
            if 0 <= h <= 23:
                nac_hora[(did, h)] += q

        # ── geografía ───────────────────────────────────────────────
        cod = row[ix["Hechos.CODIGO_DANE"]].strip()
        dane = ""
        if cod.isdigit() and len(cod) >= 6:
            dane = cod[:-3].zfill(5)          # 5697000 → 05697 · 47170000 → 47170
        if dane and dane[:2] in DEPTOS:
            dep = dane[:2]
            dep_tot[(dep, did)] += q
            mun_tot[(dane, did)] += q
            if anio is not None:
                dep_anio[(dep, did, anio)] += q
                mun_anio[(dane, did, anio)] += q
            nm = row[ix["Hechos.MUNICIPIO_HECHO"]].strip()
            if nm:
                mun_nom[dane][nm] += 1
        else:
            sin_dane += q

        # ── perfil ──────────────────────────────────────────────────
        z = limpio(row[ix["Hechos.ZONA"]]).upper()
        if z in ("URBANA", "RURAL"):
            nac_zona[(did, z)] += q
        g = limpio(row[ix["Person.GENERO"]]).upper()
        if g in ("MASCULINO", "FEMENINO"):
            nac_gen[(did, g)] += q
        b = banda_edad(limpio(row[ix["Person.EDAD"]]))
        if b is not None:
            nac_edad[(did, b)] += q
        a = limpio(row[ix["Arma empleada"]])
        if a:
            nac_arma[(did, a.upper())] += q
        s = limpio(row[ix["Clase de sitio"]])
        if s:
            nac_sitio[(did, s.upper())] += q
        ag = limpio(row[ix["Conduc.MOVIL_AGRESOR"]])
        if ag:
            nac_mag[(did, ag.upper())] += q
        vi = limpio(row[ix["Móvil Victima"]])
        if vi:
            nac_mvi[(did, vi.upper())] += q

        # ── ciudades: comuna (por sufijo del barrio) y barrio ────────
        if dane and (dane in CIUDADES or dane in CIUDADES_SOLO_BARRIO):
            ciu_tot[dane] += q
            b = row[ix["Hechos.BARRIOS_HECHO"]].strip()
            if b and BARRIO_NULO not in b.upper():
                rx = SUF.get(dane)
                m = rx.search(b) if rx else None
                com = int(m.group(1)) if m else None
                # el nombre del barrio se guarda SIN el sufijo de comuna
                nom = (b[:m.start()] if m else b).strip()
                ciu_bar[(dane, nom, did)] += q
                if com is not None:
                    ciu_bar_com[(dane, nom)] = com
                    ciu_com[(dane, com, did, anio)] += q if anio is not None else 0
                    ciu_com_t[(dane, com, did)] += q
                elif dane in CIUDADES:
                    ciu_sin_com[dane] += q
            else:
                ciu_sin_com[dane] += q

        if n % 1000000 == 0:
            print(f"  ... {n:,}", file=sys.stderr, flush=True)

    f.close()

    # Una etiqueta desconocida significa que la Policía mandó un lote con otra
    # convención (ya pasó con 2024). Abortar es a propósito: si se dejara
    # pasar, ese delito daría CERO en la página sin avisar.
    if etiquetas_nuevas:
        print("\n⚠️  etiquetas de delito NO reconocidas — agrégalas a DELITOS:", file=sys.stderr)
        for k, v in etiquetas_nuevas.most_common(20):
            print(f"     {k!r}  ({v:,} filas)", file=sys.stderr)
        sys.exit(1)

    # ── serialización ──────────────────────────────────────────────
    def serie(dd):
        """[(delito, anio)] → lista de 10 enteros por delito, sin claves vacías."""
        out = {}
        for did, _l, _r in DELITOS:
            v = [nac_anio.get((did, a), 0) for a in ANIOS]
            if any(v):
                out[did] = v
        return out

    def porcat(acc, cats):
        out = {}
        for did, _l, _r in DELITOS:
            v = [acc.get((did, c), 0) for c in cats]
            if any(v):
                out[did] = v
        return out

    def topcat(acc, k=12):
        """arma y sitio tienen cola larga → top k por delito + resto agrupado."""
        por = defaultdict(Counter)
        for (did, c), v in acc.items():
            por[did][c] += v
        out = {}
        for did, cnt in por.items():
            top = cnt.most_common(k)
            resto = sum(cnt.values()) - sum(v for _, v in top)
            out[did] = {"top": [[c, v] for c, v in top], "otros": resto}
        return out

    meta = {
        "v": "2026-08-07",
        "fuente": "Policía Nacional · comisión de delitos 2015-2024",
        "archivo": SRC.name,
        "filas_csv": n,
        "hechos": filas,
        "anios": ANIOS,
        "delitos": [
            {"id": i, "label": l, "solo_2024": i in SOLO_2024,
             "total": total_delito.get(i, 0), "sin_anio": sin_anio.get(i, 0)}
            for i, l, _r in DELITOS
        ],
        "calidad": {
            "sin_anio_total": sum(sin_anio.values()),
            "sin_anio_pct": round(100 * sum(sin_anio.values()) / max(1, filas), 2),
            "sin_dane": sin_dane,
            "fuera_de_rango": dict(sorted(fuera_rango.items())),
            "nota_sin_anio": (
                "Las filas sin año traen mes y día de la semana pero no el año, "
                "así que entran en los totales y en el perfil, y quedan fuera de "
                "toda serie temporal."),
            "nota_2024": (
                "El lote de 2024 llegó con otra convención de nombres de delito; "
                "aquí está unificado con el de 2015-2023."),
            "nota_bogota": (
                "Bogotá viene dentro de Cundinamarca en la fuente. El departamento "
                "se deriva del código DANE, así que van separados."),
        },
        "municipios": len(mun_nom),
        "departamentos": len({d for d, _x in dep_tot}),
    }

    nacional = {
        "anios": ANIOS,
        "por_anio": serie(nac_anio),
        "por_mes": porcat(nac_mes, list(range(12))),
        "por_dia": porcat(nac_dia, list(range(7))),
        "por_hora": porcat(nac_hora, list(range(24))),
        "por_zona": porcat(nac_zona, ["URBANA", "RURAL"]),
        "por_genero": porcat(nac_gen, ["MASCULINO", "FEMENINO"]),
        "por_edad": porcat(nac_edad, list(range(len(EDAD_CORTES)))),
        "edad_labels": EDAD_LAB,
        "meses": MESES,
        "dias": DIAS,
        "por_arma": topcat(nac_arma),
        "por_sitio": topcat(nac_sitio),
        # los dos móviles traen ~16 valores cerrados y solo 2,5% vacío: entran
        # completos (k alto), no recortados como arma y sitio
        "por_movil_agresor": topcat(nac_mag, 18),
        "por_movil_victima": topcat(nac_mvi, 18),
    }

    deps = {}
    for cod, nom in DEPTOS.items():
        v = {}
        for did, _l, _r in DELITOS:
            t = dep_tot.get((cod, did), 0)
            if not t:
                continue
            v[did] = {"t": t, "y": [dep_anio.get((cod, did, a), 0) for a in ANIOS]}
        if v:
            deps[cod] = {"n": nom, "d": v}
    deptos = {"anios": ANIOS, "deptos": deps}

    muns = {}
    for dane, cnt in mun_nom.items():
        v = {}
        for did, _l, _r in DELITOS:
            t = mun_tot.get((dane, did), 0)
            if not t:
                continue
            v[did] = {"t": t, "y": [mun_anio.get((dane, did, a), 0) for a in ANIOS]}
        muns[dane] = {
            "n": bonito(cnt.most_common(1)[0][0]),   # grafía más frecuente
            "dp": dane[:2],
            "d": v,
        }
    municipios = {"anios": ANIOS, "muns": muns}

    # ── ciudades: un índice liviano + un archivo por ciudad (carga diferida) ──
    (OUT / "ciudades").mkdir(parents=True, exist_ok=True)
    indice = {}
    for dane in list(CIUDADES) + list(CIUDADES_SOLO_BARRIO):
        if not ciu_tot.get(dane):
            continue
        cfg = CIUDADES.get(dane)
        # comunas (solo las 3 ciudades con sufijo)
        comunas = {}
        if cfg:
            vistas = {c for (d, c, _x) in ciu_com_t if d == dane}
            for c in sorted(vistas):
                dd = {}
                for did, _l, _r in DELITOS:
                    t = ciu_com_t.get((dane, c, did), 0)
                    if not t:
                        continue
                    dd[did] = {"t": t, "y": [ciu_com.get((dane, c, did, a), 0) for a in ANIOS]}
                if dd:
                    comunas[str(c)] = {"d": dd}
        # barrios: total por delito, sin año (el cruce barrio×delito×año son
        # ~1,5 M celdas solo en Bogotá y no cabe en una carga de navegador)
        # ⚠️ `nb`, no `n`: `n` es el contador de filas del bucle principal y
        # reusarlo aquí lo convertía en un str y reventaba el resumen final.
        nombres = {nb for (d, nb, _x) in ciu_bar if d == dane}
        barrios = []
        for nb in nombres:
            dd = {}
            for did, _l, _r in DELITOS:
                t = ciu_bar.get((dane, nb, did), 0)
                if t:
                    dd[did] = t
            if dd:
                b = {"n": nb, "t": sum(dd.values()), "d": dd}
                c = ciu_bar_com.get((dane, nb))
                if c is not None:
                    b["c"] = c
                barrios.append(b)
        barrios.sort(key=lambda x: -x["t"])
        p = OUT / "ciudades" / f"{dane}.json"
        p.write_text(json.dumps({"anios": ANIOS, "comunas": comunas, "barrios": barrios},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        indice[dane] = {
            "n": cfg["n"] if cfg else CIUDADES_SOLO_BARRIO[dane],
            "hechos": ciu_tot[dane],
            "barrios": len(barrios),
            "mapa": bool(cfg),
            "sin_comuna": ciu_sin_com.get(dane, 0),
            **({"geo": cfg["geo"], "prop": cfg["prop"], "tipo": cfg["tipo"],
                "rot": cfg["rot"], "comunas": len(comunas)} if cfg else {}),
        }
    (OUT / "ciudades.json").write_text(
        json.dumps({"anios": ANIOS, "ciudades": indice,
                    "nota": ("El mapa por comuna existe donde el nombre del barrio trae el "
                             "código de comuna pegado (Bogotá, Medellín y Cali). En las demás "
                             "ciudades la fuente no lo trae, así que va el ranking de barrios "
                             "y no un mapa.")},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {'ciudades.json':18} {(OUT/'ciudades.json').stat().st_size/1024:>9,.0f} KB "
          f"({len(indice)} ciudades, {sum(1 for v in indice.values() if v['mapa'])} con mapa)")
    for d in CIUDADES:
        if d in indice:
            f2 = OUT / "ciudades" / f"{d}.json"
            print(f"    {indice[d]['n']:14} {f2.stat().st_size/1024:>8,.0f} KB · "
                  f"{indice[d].get('comunas',0)} {CIUDADES[d]['tipo']}es · "
                  f"{indice[d]['barrios']:,} barrios · "
                  f"{100*indice[d]['sin_comuna']/max(1,ciu_tot[d]):.1f}% sin comuna")

    for nombre, obj in [("meta.json", meta), ("nacional.json", nacional),
                        ("deptos.json", deptos), ("municipios.json", municipios)]:
        p = OUT / nombre
        p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  {nombre:18} {p.stat().st_size/1024:>9,.0f} KB")

    print(f"\nOK · {n:,} filas leídas · {filas:,} hechos · "
          f"{len(muns)} municipios · {len(deps)} departamentos")


if __name__ == "__main__":
    main()
