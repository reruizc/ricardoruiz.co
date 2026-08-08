#!/usr/bin/env python3
"""
build_mujer.py — violencia contra las mujeres, desde la base PONAL 2015-2024.

    python3 tools/ponal/build_mujer.py [--limite N]

Alimenta el módulo 07 del observatorio de MxD. Es una pasada aparte sobre
`Bases de datos/PONAL/BD-PONAL-15-24.csv` porque `build_ponal.py` agrega el
género SOLO a nivel nacional: sus JSON territoriales traen `delito × año` y
nada de sexo, así que el mapa de víctimas mujeres no se puede derivar de ellos.

Salidas en `Bases de datos/output_observatorio_mujer/`:
    violencia-meta.json        catálogo, cobertura y las advertencias a publicar
    violencia-nacional.json    series por delito × sexo × año + perfil de la víctima
    violencia-deptos.json      departamento × delito × sexo × año
    violencia-municipios.json  municipio (DANE) × delito × sexo × año
    violencia-ciudades.json    comuna/localidad × delito × sexo (Bogotá·Medellín·Cali)

Las constantes de la fuente (mapa canónico de delitos, departamentos, ciudades,
limpieza) se IMPORTAN de `build_ponal.py` a propósito: si el lote del año que
viene trae otra convención de nombres, se arregla en un solo sitio y los dos
builds la heredan. Duplicarlas es la forma de que uno de los dos empiece a dar
cero en silencio.

Lo que se midió antes de construir esto (ago-2026, pasada completa)
-------------------------------------------------------------------
✔ `Person.GENERO` NO tiene problema de cobertura en lo que importa. El 78,2%
  global asusta pero lo hunden los delitos sin víctima-persona (terrorismo,
  hurto a comercios y hurto de celulares van en 0,0%). En los delitos de este
  módulo el campo está lleno: homicidios/lesiones/hurto a personas/secuestro
  100%, amenazas y violencia intrafamiliar 99,8%, delitos sexuales 99,5%.
✔ Alcanza para mapa municipal: hay víctimas mujeres en 1.102 municipios para
  violencia intrafamiliar (945 con 30 o más) y 1.108 para delitos sexuales.

⚠️⚠️ FEMINICIDIO — las dos advertencias que NO se pueden omitir al publicar
  ① La serie va **2015-2023, no 2024**. El artículo penal vive en
    `ListaC.DESCRIPCION_CONDUCTA`, que no viene parejo: en homicidios está al
    100% hasta 2023 y al **0% en 2024**. Un 2024 en cero se leería como «no
    hubo feminicidios» — es la trampa ① del lote 2024 otra vez. Por eso el año
    2024 va como `null` y no como 0, y `meta` lo declara.
  ② Son **1.336 hechos** en nueve años (~148/año), muy por debajo de Medicina
    Legal y Fiscalía. Es «homicidios que la Policía tipificó como feminicidio»,
    no «feminicidios», y así se rotula. La curva 27 (2015) → 219 (2021) refleja
    la ADOPCIÓN del tipo penal (Ley 1761 de julio de 2015, Rosa Elvira Cely),
    no un aumento real de ocho veces. Publicarla sin ese rótulo es vender como
    tendencia lo que es un cambio administrativo de registro.

⚠️ NO existe la relación víctima-agresor. `Conduc.MOVIL_AGRESOR` es cómo se
  movía el agresor (a pie, en moto), no si era la pareja. Con esta fuente NO se
  puede decir «el X% fue la pareja»: ese dato es de Medicina Legal (Forensis).
  Se emite igual porque distingue el atraco del ataque, pero rotulado por lo
  que es.

⚠️ La medianoche es un nulo disfrazado (`Hora` escribe 00:00 cuando la fuente
  no la conoce). Acá se emite la hora cruda MÁS `h0_ratio` por delito —la hora
  0 contra el promedio de las otras 23 del MISMO delito— para que la página
  aparte el nulo con el mismo umbral (ratio ≥ 2) del hub de Policía, sin borrar
  las medianoches verdaderas. Medido en víctimas mujeres: delitos sexuales
  ~9×, violencia intrafamiliar ~7×, homicidios ~1× (ese es real).

⚠️ Delitos sexuales trae 52% de registros sin año: los totales son completos,
  la serie temporal es sobre la mitad. Va en `meta.sin_anio` por delito.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import csv

from build_ponal import (  # noqa: E402  — fuente única de las constantes
    CANON, CIUDADES, CIUDADES_SOLO_BARRIO, BARRIO_NULO, DEPTOS,
    ANIOS, AIX, NA, MESES, DIAS, DIX, EDAD_LAB,
    VERTEDEROS, VERT_PESO, VERT_CAIDA, detectar_vertederos,
    RE_FECHA, RE_HORA, banda_edad, bonito, limpio,
)

csv.field_size_limit(10 ** 9)

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "Bases de datos" / "PONAL" / "BD-PONAL-15-24.csv"
OUT = RAIZ / "Bases de datos" / "output_observatorio_mujer"

# Delitos del módulo: los que tienen víctima-persona y el sexo lleno (≥97%).
# El resto de la base (hurtos de cosas, terrorismo) no dice nada sobre mujeres.
FOCO = [
    ("violencia_intra",  "Violencia intrafamiliar"),
    ("delitos_sexuales", "Delitos sexuales"),
    ("amenazas",         "Amenazas"),
    ("lesiones",         "Lesiones personales"),
    ("homicidios",       "Homicidios"),
    ("hurto_personas",   "Hurto a personas"),
    ("extorsiones",      "Extorsión"),
    ("secuestros",       "Secuestro"),
]
FOCO_IDS = [d for d, _ in FOCO]
FSET = set(FOCO_IDS)
# En el mapa municipal solo entran los que tienen masa suficiente para pintar
# un municipio sin que sea ruido; extorsión y secuestro se quedan en nacional
# y departamento (secuestro tiene 2 municipios con 30+ víctimas mujeres).
MUNICIPAL = ["violencia_intra", "delitos_sexuales", "amenazas",
             "lesiones", "homicidios", "hurto_personas"]

RE_FEM = re.compile(r"104\s*A|FEMINICID", re.I)

# Un delito con demasiados registros sin año no tiene serie: su curva dibuja la
# calidad del registro, no la violencia. Mismo umbral que el hub de Policía.
# Medido: delitos sexuales 52,2% sin año y amenazas 53,6% → sin serie; los otros
# seis van en 0,0%. Sin este corte, delitos sexuales «sube» de 8.047 (2023) a
# 25.021 (2024), que es solo el lote de 2024 trayendo fecha.
UMBRAL_PARCIAL = 0.15
# La Ley 1761 (Rosa Elvira Cely) es de julio de 2015: el tipo penal no existe
# antes, y el registro tarda en adoptarlo. Y en 2024 el artículo no viene.
FEM_ANIOS_VALIDOS = (2015, 2023)

TOP_CAT = 12          # cuántos valores se guardan de cada variable cualitativa

# Los vertederos de registro (BELLA SUIZA en Bogotá, PARQUE NORTE en Medellín)
# y su detector viven en `build_ponal`, que es la fuente única: los mismos dos
# barrios hay que sacarlos del mapa de comunas del hub de Policía y de este
# módulo. El porqué, con las cifras medidas, está en el comentario de allá.
# Aquí se miden sobre los 8 delitos del FOCO, así que el peso relativo es
# distinto del que reporta build_ponal sobre la base completa.


def top(cnt, n=TOP_CAT):
    """Los n valores más frecuentes + el resto agrupado, como en build_ponal."""
    items = sorted(cnt.items(), key=lambda kv: -kv[1])
    return {"top": items[:n], "otros": sum(v for _, v in items[n:])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0, help="procesar solo N filas (prueba)")
    args = ap.parse_args()
    if not SRC.exists():
        sys.exit(f"no encuentro {SRC}")
    OUT.mkdir(parents=True, exist_ok=True)

    fh = SRC.open(encoding="utf-8-sig", newline="")
    rd = csv.reader(fh, delimiter=";")
    hdr = next(rd)
    ix = {c: i for i, c in enumerate(hdr)}
    ncol = len(hdr)
    need = ["Nombre Delitos", "Cantidad", "Fecha", "Hora", "Día",
            "Hechos.CODIGO_DANE", "Hechos.MUNICIPIO_HECHO", "Hechos.ZONA",
            "Hechos.BARRIOS_HECHO", "Person.GENERO", "Person.EDAD",
            "Arma empleada", "Clase de sitio", "Conduc.MOVIL_AGRESOR",
            "ListaC.DESCRIPCION_CONDUCTA", "Estado Civil",
            "Person.GRADO_INSTRUCCION_PERSONA", "País de nacimiento"]
    falta = [c for c in need if c not in ix]
    if falta:
        sys.exit(f"al CSV le faltan columnas: {falta}")
    C = {c: ix[c] for c in need}
    SUF = {d: re.compile(c["suf"]) for d, c in CIUDADES.items()}

    # ── acumuladores ───────────────────────────────────────────────────
    nac_sexo = defaultdict(int)        # (delito, sexo) -> n
    nac_sexo_anio = defaultdict(int)   # (delito, sexo, anio)
    dep_sexo = defaultdict(int)        # (dep, delito, sexo)
    dep_sexo_anio = defaultdict(int)   # (dep, delito, sexo, anio)
    mun_sexo = defaultdict(int)        # (dane, delito, sexo)
    mun_sexo_anio = defaultdict(int)   # (dane, delito, sexo, anio)
    mun_nom = defaultdict(Counter)
    ciu_sexo = defaultdict(int)        # (dane, comuna, delito, sexo)
    ciu_sin_com = defaultdict(int)
    ciu_bar = defaultdict(int)         # (dane, barrio) — solo para el detector
    ciu_bar_anio = defaultdict(int)    # (dane, barrio, anio)

    # perfil SOLO de víctimas mujeres (el agregado mixto esconde justo lo que
    # este módulo quiere ver: en homicidios ellas son el 8%)
    f_edad = defaultdict(int)          # (delito, banda)
    f_hora = defaultdict(int)          # (delito, hora)
    f_dia = defaultdict(int)
    f_mes = defaultdict(int)
    f_zona = defaultdict(int)
    f_sitio = defaultdict(lambda: Counter())
    f_arma = defaultdict(lambda: Counter())
    f_movil = defaultdict(lambda: Counter())
    f_civil = defaultdict(lambda: Counter())
    f_educ = defaultdict(lambda: Counter())
    f_pais = defaultdict(lambda: Counter())
    f_art = defaultdict(lambda: Counter())
    # el mismo perfil para hombres, solo en las variables que se comparan
    m_edad = defaultdict(int)
    m_hora = defaultdict(int)

    # feminicidio
    fem_anio = defaultdict(int)
    fem_dep = defaultdict(int)
    fem_mun = defaultdict(int)
    fem_edad = defaultdict(int)
    fem_arma = Counter()
    fem_sitio = Counter()
    fem_zona = Counter()
    fem_sexo = Counter()

    sin_anio = defaultdict(int)        # (delito, sexo) sin año
    sin_sexo = defaultdict(int)        # delito -> hechos sin sexo
    tot_delito = defaultdict(int)
    filas = 0

    for row in rd:
        if len(row) < ncol:
            continue
        filas += 1
        if args.limite and filas > args.limite:
            break
        did = CANON.get(row[C["Nombre Delitos"]].strip().lower())
        if did not in FSET:
            continue
        try:
            q = int(float(row[C["Cantidad"]] or 1))
        except ValueError:
            q = 1
        tot_delito[did] += q

        # año
        anio = None
        m = RE_FECHA.match(row[C["Fecha"]].strip())
        if m:
            yy = int(m.group(3))
            if yy in AIX:
                anio = yy
                f_mes_key = int(m.group(2)) - 1
            else:
                f_mes_key = None
        else:
            f_mes_key = None

        # sexo de la víctima
        g = limpio(row[C["Person.GENERO"]]).upper()
        sexo = "F" if g == "FEMENINO" else ("M" if g == "MASCULINO" else "")
        if not sexo:
            sin_sexo[did] += q

        # geografía (misma derivación que build_ponal: el departamento sale del
        # DANE, no de la columna `Departamento`, que mete Bogotá en Cundinamarca)
        cod = row[C["Hechos.CODIGO_DANE"]].strip()
        dane = cod[:-3].zfill(5) if cod.isdigit() and len(cod) >= 6 else ""
        dep = dane[:2] if dane[:2] in DEPTOS else ""

        if sexo:
            nac_sexo[(did, sexo)] += q
            if anio is not None:
                nac_sexo_anio[(did, sexo, anio)] += q
            else:
                sin_anio[(did, sexo)] += q
            if dep:
                dep_sexo[(dep, did, sexo)] += q
                if anio is not None:
                    dep_sexo_anio[(dep, did, sexo, anio)] += q
                if did in MUNICIPAL:
                    mun_sexo[(dane, did, sexo)] += q
                    if anio is not None:
                        mun_sexo_anio[(dane, did, sexo, anio)] += q
                    nm = row[C["Hechos.MUNICIPIO_HECHO"]].strip()
                    if nm:
                        mun_nom[dane][nm] += 1

        # comuna de las tres ciudades cuyo barrio trae el sufijo
        if sexo and dane in CIUDADES:
            b = row[C["Hechos.BARRIOS_HECHO"]].strip()
            if b and BARRIO_NULO not in b.upper():
                mm = SUF[dane].search(b)
                if mm:
                    nom_b = b[:mm.start()].strip().upper()
                    # vigilancia del vertedero: se mide SIEMPRE, se excluye solo
                    # a los confirmados (así el próximo lote delata al que siga)
                    ciu_bar[(dane, nom_b)] += q
                    if anio is not None:
                        ciu_bar_anio[(dane, nom_b, anio)] += q
                    if (dane, nom_b) in VERTEDEROS:
                        ciu_sin_com[dane] += q
                    else:
                        ciu_sexo[(dane, int(mm.group(1)), did, sexo)] += q
                else:
                    ciu_sin_com[dane] += q
            else:
                ciu_sin_com[dane] += q

        # ── perfil ─────────────────────────────────────────────────────
        banda = banda_edad(limpio(row[C["Person.EDAD"]]))
        hm = RE_HORA.search(row[C["Hora"]])
        hora = int(hm.group(1)) if hm and 0 <= int(hm.group(1)) <= 23 else None
        if sexo == "M":
            if banda is not None:
                m_edad[(did, banda)] += q
            if hora is not None:
                m_hora[(did, hora)] += q
        elif sexo == "F":
            if banda is not None:
                f_edad[(did, banda)] += q
            if hora is not None:
                f_hora[(did, hora)] += q
            d = DIX.get(row[C["Día"]].strip())
            if d is not None:
                f_dia[(did, d)] += q
            if f_mes_key is not None and 0 <= f_mes_key <= 11:
                f_mes[(did, f_mes_key)] += q
            z = limpio(row[C["Hechos.ZONA"]]).upper()
            if z in ("URBANA", "RURAL"):
                f_zona[(did, z)] += q
            for col, acc in (("Clase de sitio", f_sitio), ("Arma empleada", f_arma),
                             ("Conduc.MOVIL_AGRESOR", f_movil), ("Estado Civil", f_civil),
                             ("Person.GRADO_INSTRUCCION_PERSONA", f_educ),
                             ("País de nacimiento", f_pais),
                             ("ListaC.DESCRIPCION_CONDUCTA", f_art)):
                v = limpio(row[C[col]])
                if v:
                    acc[did][v.upper()] += q

        # ── feminicidio ────────────────────────────────────────────────
        if did == "homicidios":
            cond = limpio(row[C["ListaC.DESCRIPCION_CONDUCTA"]])
            if cond and RE_FEM.search(cond):
                fem_sexo[sexo or "(sin dato)"] += q
                if anio is not None:
                    fem_anio[anio] += q
                if dep:
                    fem_dep[dep] += q
                if dane:
                    fem_mun[dane] += q
                    nm = row[C["Hechos.MUNICIPIO_HECHO"]].strip()
                    if nm:
                        mun_nom[dane][nm] += 1
                if banda is not None:
                    fem_edad[banda] += q
                for col, acc in (("Arma empleada", fem_arma),
                                 ("Clase de sitio", fem_sitio),
                                 ("Hechos.ZONA", fem_zona)):
                    v = limpio(row[C[col]])
                    if v:
                        acc[v.upper()] += q
    fh.close()

    # ── detector de vertederos nuevos ──────────────────────────────────
    sospechosos = detectar_vertederos(ciu_bar, ciu_bar_anio)

    # ── la hora 0 es un nulo: se mide, no se borra ─────────────────────
    h0 = {}
    for d in FOCO_IDS:
        serie = [f_hora.get((d, h), 0) for h in range(24)]
        resto = sum(serie[1:]) / 23 if sum(serie[1:]) else 0
        h0[d] = round(serie[0] / resto, 2) if resto else None

    def sx(acc, key, sexo):
        return [acc.get(key + (sexo, a), 0) for a in ANIOS]

    # ── nacional ───────────────────────────────────────────────────────
    nacional = {
        "anios": ANIOS, "meses": MESES, "dias": DIAS, "edad_labels": EDAD_LAB,
        "delitos": {
            d: {
                "f": nac_sexo.get((d, "F"), 0),
                "m": nac_sexo.get((d, "M"), 0),
                "f_anio": [nac_sexo_anio.get((d, "F", a), 0) for a in ANIOS],
                "m_anio": [nac_sexo_anio.get((d, "M", a), 0) for a in ANIOS],
                "sin_anio_f": sin_anio.get((d, "F"), 0),
                "sin_sexo": sin_sexo.get(d, 0),
                "total": tot_delito.get(d, 0),
            } for d in FOCO_IDS},
        "perfil_f": {
            d: {
                "edad": [f_edad.get((d, i), 0) for i in range(len(EDAD_LAB))],
                "edad_m": [m_edad.get((d, i), 0) for i in range(len(EDAD_LAB))],
                "hora": [f_hora.get((d, h), 0) for h in range(24)],
                "hora_m": [m_hora.get((d, h), 0) for h in range(24)],
                "h0_ratio": h0[d],
                "dia": [f_dia.get((d, i), 0) for i in range(7)],
                "mes": [f_mes.get((d, i), 0) for i in range(12)],
                "zona": {"URBANA": f_zona.get((d, "URBANA"), 0),
                         "RURAL": f_zona.get((d, "RURAL"), 0)},
                "sitio": top(f_sitio[d]), "arma": top(f_arma[d]),
                "movil_agresor": top(f_movil[d], 8), "estado_civil": top(f_civil[d], 8),
                "educacion": top(f_educ[d], 8), "pais": top(f_pais[d], 8),
                "articulo": top(f_art[d], 10),
            } for d in FOCO_IDS},
        "feminicidio": {
            "anios": ANIOS,
            # 2024 va en null, NO en 0: el artículo penal no viene en ese lote
            "serie": [fem_anio.get(a, 0) if FEM_ANIOS_VALIDOS[0] <= a <= FEM_ANIOS_VALIDOS[1]
                      else None for a in ANIOS],
            "total": sum(fem_anio.values()),
            "sexo_registrado": dict(fem_sexo),
            "edad": [fem_edad.get(i, 0) for i in range(len(EDAD_LAB))],
            "arma": top(fem_arma, 8), "sitio": top(fem_sitio, 8),
            "zona": dict(fem_zona),
            "deptos": sorted(((d, DEPTOS[d], n) for d, n in fem_dep.items() if d in DEPTOS),
                             key=lambda x: -x[2]),
            "muns": sorted(((k, bonito(mun_nom[k].most_common(1)[0][0]) if mun_nom.get(k) else k, n)
                            for k, n in fem_mun.items()), key=lambda x: -x[2])[:40],
        },
    }

    # ── departamentos ──────────────────────────────────────────────────
    deptos = {"anios": ANIOS, "deptos": {}}
    for dep, nom in sorted(DEPTOS.items()):
        d_out = {}
        for d in FOCO_IDS:
            f = dep_sexo.get((dep, d, "F"), 0)
            if not f and not dep_sexo.get((dep, d, "M"), 0):
                continue
            d_out[d] = {"f": f, "m": dep_sexo.get((dep, d, "M"), 0),
                        "fy": sx(dep_sexo_anio, (dep, d), "F"),
                        "my": sx(dep_sexo_anio, (dep, d), "M")}
        if d_out:
            deptos["deptos"][dep] = {"n": nom, "d": d_out}

    # ── municipios ─────────────────────────────────────────────────────
    muns = {"anios": ANIOS, "delitos": MUNICIPAL, "muns": {}}
    danes = sorted({k[0] for k in mun_sexo})
    sin_mun = 0
    for dane in danes:
        # `52000` («No Reportado») es el agregado departamental que la fuente usa
        # cuando no sabe el municipio: no tiene polígono ni población, así que
        # como fila de mapa sería un municipio inventado. Se cuenta aparte.
        if dane.endswith("000"):
            sin_mun += sum(v for k, v in mun_sexo.items() if k[0] == dane and k[2] == "F")
            continue
        d_out = {}
        for d in MUNICIPAL:
            f = mun_sexo.get((dane, d, "F"), 0)
            mm = mun_sexo.get((dane, d, "M"), 0)
            if not f and not mm:
                continue
            d_out[d] = {"f": f, "m": mm,
                        "fy": sx(mun_sexo_anio, (dane, d), "F"),
                        "my": sx(mun_sexo_anio, (dane, d), "M")}
        if not d_out:
            continue
        nom = bonito(mun_nom[dane].most_common(1)[0][0]) if mun_nom.get(dane) else dane
        muns["muns"][dane] = {"n": nom, "dp": dane[:2], "d": d_out}

    # ── ciudades (comuna / localidad) ──────────────────────────────────
    ciudades = {"ciudades": {}}
    for dane, cfg in CIUDADES.items():
        comunas = sorted({k[1] for k in ciu_sexo if k[0] == dane})
        if not comunas:
            continue
        ciudades["ciudades"][dane] = {
            "n": cfg["n"], "geo": cfg["geo"], "prop": cfg["prop"],
            "tipo": cfg["tipo"], "rot": cfg["rot"],
            "sin_comuna": ciu_sin_com.get(dane, 0),
            "comunas": {str(c): {d: [ciu_sexo.get((dane, c, d, "F"), 0),
                                     ciu_sexo.get((dane, c, d, "M"), 0)]
                                 for d in FOCO_IDS
                                 if ciu_sexo.get((dane, c, d, "F"), 0)
                                 or ciu_sexo.get((dane, c, d, "M"), 0)}
                        for c in comunas},
        }

    # ── meta ───────────────────────────────────────────────────────────
    meta = {
        "v": "2026-08-08",
        "fuente": "Policía Nacional · comisión de delitos 2015-2024",
        "archivo": SRC.name,
        "anios": ANIOS,
        "delitos": [{"id": d, "label": lab,
                     "f": nac_sexo.get((d, "F"), 0), "m": nac_sexo.get((d, "M"), 0),
                     "pct_f": round(100 * nac_sexo.get((d, "F"), 0)
                                    / max(1, nac_sexo.get((d, "F"), 0) + nac_sexo.get((d, "M"), 0)), 1),
                     "municipal": d in MUNICIPAL,
                     "sin_anio_f": sin_anio.get((d, "F"), 0),
                     # el frontend NO decide esto: si va en false, no se dibuja serie
                     "serie": (sin_anio.get((d, "F"), 0)
                               / max(1, nac_sexo.get((d, "F"), 1))) < UMBRAL_PARCIAL,
                     "cob_sexo": round(100 * (1 - sin_sexo.get(d, 0) / max(1, tot_delito.get(d, 1))), 1)}
                    for d, lab in FOCO],
        "muns_con_dato": {d: sum(1 for k in mun_sexo if k[1] == d and k[2] == "F" and mun_sexo[k])
                          for d in MUNICIPAL},
        "sin_municipio_f": sin_mun,
        "poblacion": {
            "archivo": "poblacion.json (DANE, campo `f` = mujeres)",
            "anios": list(range(2018, 2025)),
            "nota": ("La tasa por 100.000 mujeres solo se puede calcular 2018-2024: "
                     "el anexo municipal del DANE es post-censo y no cubre 2015-2017. "
                     "Esos tres años van en volumen absoluto, declarado. No se extrapola."),
        },
        "avisos": {
            "cobertura_sexo": (
                "En estos delitos el sexo de la víctima está registrado en el 97-100% de "
                "los hechos. El 78% que aparece en el total de la base lo bajan los delitos "
                "sin víctima-persona (terrorismo, hurto a comercios, hurto de celulares), "
                "que no entran a este módulo."),
            "feminicidio": (
                "Son homicidios que la Policía tipificó como feminicidio (artículo 104A), "
                "no el universo de feminicidios del país: 1.336 en nueve años está muy por "
                "debajo de Medicina Legal y Fiscalía. El crecimiento de 2015 a 2021 recoge "
                "sobre todo la adopción del tipo penal —la Ley 1761 es de julio de 2015— y "
                "no debe leerse como un aumento de esa magnitud. 2024 no tiene dato: el "
                "lote de ese año no trae el artículo penal en homicidios."),
            "feminicidio_2024": "sin dato (el lote 2024 no trae artículo penal en homicidios)",
            "relacion_agresor": (
                "La fuente NO registra la relación entre la víctima y el agresor. "
                "El «móvil del agresor» describe cómo se movía (a pie, en moto), no si "
                "era la pareja. Ese dato es de Medicina Legal, no de la Policía."),
            "hora_medianoche": (
                "La hora 00:00 es el valor que la fuente escribe cuando no conoce la hora. "
                "Se aparta cuando supera el doble del promedio de las otras 23 horas del "
                "mismo delito; en homicidios (ratio ~1) la medianoche es real y se conserva."),
            "sin_anio": (
                "Delitos sexuales (52%) y amenazas (54%) llegan sin año en más de la mitad "
                "de los registros. Sus totales y su perfil sí son completos, pero NO tienen "
                "serie: la curva dibujaría la calidad del registro y no la violencia. Van "
                "con `serie: false` y la página no les pinta tendencia."),
            "denuncia": (
                "Todo esto es DENUNCIA registrada, no ocurrencia. Una zona con más casos "
                "puede tener más violencia, más confianza para denunciar o más presencia "
                "institucional. La serie mide el registro."),
            "vertederos": (
                "Dos barrios quedaron fuera del mapa de comunas porque el sistema de "
                "registro los usó como valor por defecto durante unos años: Bella Suiza "
                "(Bogotá) y Parque Norte (Medellín). Sus casos no se borran —se cuentan "
                "como «sin localidad»— pero dejarlos adentro hacía de Usaquén la "
                "localidad más violenta de Bogotá, que es falso."),
        },
        "vertederos": {"excluidos": sorted(f"{c}·{b}" for c, b in VERTEDEROS),
                       "vigilados": sorted(sospechosos, key=lambda x: -x["hechos"])},
        "h0_ratio": h0,
    }

    for nom, obj in (("violencia-meta.json", meta),
                     ("violencia-nacional.json", nacional),
                     ("violencia-deptos.json", deptos),
                     ("violencia-municipios.json", muns),
                     ("violencia-ciudades.json", ciudades)):
        p = OUT / nom
        p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  → {nom:28} {p.stat().st_size/1024:>8,.0f} KB")

    print(f"\n  filas leídas {filas:,}")
    print(f"  municipios con víctimas mujeres: {len(muns['muns']):,}")
    print("\n  víctimas por delito (F / M / %F / cobertura del sexo):")
    for d, lab in FOCO:
        f, m2 = nac_sexo.get((d, "F"), 0), nac_sexo.get((d, "M"), 0)
        cob = 100 * (1 - sin_sexo.get(d, 0) / max(1, tot_delito.get(d, 1)))
        print(f"    {lab:26} {f:>9,} / {m2:>9,}   {100*f/max(1,f+m2):5.1f}%   cob {cob:5.1f}%")
    print(f"\n  feminicidio (art. 104A) · total {sum(fem_anio.values()):,} · sexo {dict(fem_sexo)}")
    print("    serie", {a: (fem_anio.get(a, 0) if a <= FEM_ANIOS_VALIDOS[1] else None) for a in ANIOS})
    print("    hora 0 / promedio de las otras 23 (ratio ≥2 = nulo disfrazado):")
    print("   ", {d: h0[d] for d in FOCO_IDS})


if __name__ == "__main__":
    main()
