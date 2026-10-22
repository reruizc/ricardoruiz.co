#!/usr/bin/env python3
"""
Encargo · Consulta del Pacto Histórico 2025 por puesto, localidad y barrio, con el
perfil del censo de cada puesto (sexo y rangos de edad). Primer cliente: Bogotá,
oct-2026 (opción 1 de la propuesta: datos, sin estimación de edad de los votantes).

Fuentes (todas ya en el proyecto):
  · votos por candidato y puesto  Bases de datos/output_presidencial_escr/pacto2025/dep-{dd}.json
  · nulos, no marcados y mesas    .../pacto2025/mesas/{senado|camara}-{dd}.json
  · localidad y barrio del puesto .../pacto2025/geo/{dd}.json (censo de puestos 2026)
  · dirección y coordenadas       PUESTOS_GEOREF.csv
  · censo por puesto con sexo y edad   censos-registraduria/2026_datos_censo-electoral-min.json
        (Congreso 2026, corte de enero de 2026: el más cercano a la consulta del
         26-oct-2025; no hay censo publicado con la fecha exacta de la consulta)

Uso: python3 tools/encargos/consulta_pacto_territorio.py 16 [salida.xlsx]
"""
import csv
import json
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path("/Users/ricardoruiz/ricardoruiz.co")
DATA = ROOT / "Bases de datos/output_presidencial_escr/pacto2025"
CENSO = ROOT / "Bases de datos/censos-registraduria/2026_datos_censo-electoral-min.json"
GEOREF = ROOT / "Bases de datos/PUESTOS_GEOREF.csv"
BANDAS = ["18-20", "21-25", "26-30", "31-35", "36-40", "41-45", "46-50", "51-55", "56-60", "mas de 60"]
ETIQ_BANDA = {b: ("61 y más" if b == "mas de 60" else b) for b in BANDAS}
CONSULTAS = [("camara", "Cámara"), ("senado", "Senado")]

AZUL = PatternFill("solid", fgColor="1F3A8A")
GRIS = PatternFill("solid", fgColor="EEF1F6")
BLANCA = Font(bold=True, color="FFFFFF")
NEGRITA = Font(bold=True)
MENORES = {"al", "de", "del", "la", "las", "los", "el", "y", "e", "en", "por", "a"}


def tc(s):
    """Nombre propio en minúscula con mayúscula inicial, sin tocar siglas cortas."""
    out = []
    for i, w in enumerate(re.split(r"(\s+|-|/|\()", (s or "").strip().lower())):
        if not w.strip() or re.fullmatch(r"[\s\-/(]", w):
            out.append(w)
        elif i > 0 and w in MENORES:
            out.append(w)
        elif re.fullmatch(r"(i{1,3}|iv|v|vi{0,3}|ix|x)", w):
            out.append(w.upper())
        else:
            out.append(w[0].upper() + w[1:])
    t = "".join(out)
    t = re.sub(r"\b(Sede|Bloque|Torre) ([a-z])\b", lambda m: f"{m.group(1)} {m.group(2).upper()}", t)
    t = re.sub(r"\bD\.c\.", "D.C.", t)
    return "Bogotá D.C." if re.fullmatch(r"Bogota\.? D\.C\.", t) else t


def barrio_por_coordenada(lat, lon):
    """Solo Bogotá: barrio catastral (IDECA) que contiene el punto. Para los puestos
    que el censo de puestos trae sin barrio («N/a»)."""
    global _BOG
    if lat is None or lon is None:
        return ""
    if "_BOG" not in globals():
        import geopandas as gpd
        _BOG = gpd.read_file(ROOT / "Bases de datos/output_pacto_1v_2026/geo/BOG-BARRIOS-CATASTRALES.json").to_crs(4326)
    from shapely.geometry import Point
    h = _BOG[_BOG.contains(Point(lon, lat))]
    return str(h.iloc[0]["nombre"]) if len(h) else ""


def cargar(dd):
    dep = json.loads((DATA / f"dep-{dd}.json").read_text(encoding="utf-8"))
    geo = json.loads((DATA / "geo" / f"{dd}.json").read_text(encoding="utf-8"))
    mesas = {k: json.loads((DATA / "mesas" / f"{k}-{dd}.json").read_text(encoding="utf-8")) for k, _ in CONSULTAS}
    d = json.loads(CENSO.read_text(encoding="utf-8"))
    rec = next(v for v in d.values() if isinstance(v, list)) if isinstance(d, dict) else d
    censo = {}
    for r in rec:
        if r["cod_depto"].zfill(2) == dd and r["tipo_eleccion"] == "CONGRESO DE LA REPÚBLICA":
            censo[f'{r["cod_mun"].zfill(3)}-{r["zona"].zfill(2)}-{r["cod_puesto"].zfill(2)}'] = r
    gref = {}
    with GEOREF.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            c = (r.get("CÓDIGO COMPLETO") or "").strip().zfill(9)
            if c[:2] == dd:
                gref[f"{c[2:5]}-{c[5:7]}-{c[7:9]}"] = (r.get("DIRECCIÓN") or "").strip(), r.get("LATITUD"), r.get("LONGITUD")
    return dep, geo, mesas, censo, gref


def num(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def construir(dd, salida):
    dep, geo, mesas, censo, gref = cargar(dd)
    nombre_dep = tc(dep["nombre"])
    es_bogota = dd == "16"
    etiq_com = "Localidad" if es_bogota else "Comuna / zona"

    # ── una fila por puesto con todo lo que se necesita ──
    puestos = []
    for m in dep["municipios"]:
        for z in m["zonas"]:
            for p in z["puestos"]:
                key = f'{m["cod"]}-{z["cod"]}-{p["cod"]}'
                com, bar = geo.get(key, ["", ""])
                c = censo.get(key)
                dirc, lat, lon = gref.get(key, ("", None, None))
                por_coord = False
                if not bar and dd == "16":
                    bar = barrio_por_coordenada(num(lat), num(lon))
                    por_coord = bool(bar)
                fila = {
                    "key": key, "codigo": f"{dd}-{key}", "mun": tc(m["nombre"]),
                    "com": tc(com) if com else f"Zona {int(z['cod'])}",
                    "bar": tc(bar) if bar else "Sin barrio registrado",
                    "puesto": tc(p["nombre"]), "dir": dirc, "por_coord": por_coord, "lat": num(lat), "lon": num(lon),
                    "censo": c["potencial_electoral"] if c else None,
                    "muj": c["sexo"]["mujeres"] if c else None, "hom": c["sexo"]["hombres"] if c else None,
                    "bandas": [c["rango_etario"].get(b, 0) for b in BANDAS] if c else [None] * len(BANDAS),
                }
                for k, _ in CONSULTAS:
                    nodo = p.get(k) or {"votos": 0, "cands": []}
                    filas_m = mesas[k]["p"].get(key, [])
                    fila[k] = {
                        "votos": nodo["votos"], "cands": {x["nombre"]: x["votos"] for x in nodo["cands"]},
                        "nulos": sum(f[3] or 0 for f in filas_m), "nm": sum(f[4] or 0 for f in filas_m),
                        "mesas": len(filas_m),
                    }
                puestos.append(fila)

    # ── candidatos ordenados por su votación en el territorio ──
    orden = {}
    for k, _ in CONSULTAS:
        tot = defaultdict(int)
        for f in puestos:
            for n, v in f[k]["cands"].items():
                tot[n] += v
        orden[k] = sorted(tot.items(), key=lambda x: -x[1])

    wb = Workbook()
    wb.remove(wb.active)

    def encabezado(ws, cols, fila=1):
        for j, c in enumerate(cols, 1):
            x = ws.cell(row=fila, column=j, value=c)
            x.font, x.fill = BLANCA, AZUL
            x.alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[fila].height = 42
        ws.freeze_panes = ws.cell(row=fila + 1, column=1)

    def anchos(ws, w):
        for j, a in enumerate(w, 1):
            ws.column_dimensions[get_column_letter(j)].width = a

    def formatos(ws, desde_fila, cols_num, cols_pct):
        for row in ws.iter_rows(min_row=desde_fila):
            for c in row:
                if c.column in cols_num:
                    c.number_format = "#,##0"
                elif c.column in cols_pct:
                    c.number_format = "0.0%"

    # ── Léeme ──
    ws = wb.create_sheet("Léeme")
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 110
    lineas = [
        (f"Consultas internas del Pacto Histórico · 26 de octubre de 2025 · {nombre_dep}", None),
        ("Preparado por ricardoruiz.co", None),
        ("", None),
        ("Qué trae", None),
        ("Candidatos", "Votos de cada candidato en " + nombre_dep + f" (Cámara: {len(orden['camara'])} · Senado: {len(orden['senado'])}), ordenados de mayor a menor."),
        ("Cámara · puestos / Senado · puestos", "Una fila por puesto de votación: " + etiq_com.lower() + ", barrio, dirección, censo con sexo y rangos de edad, votos de cada candidato, nulos, no marcados y participación aproximada."),
        ("Cámara · localidades / Senado · …" if es_bogota else "Cámara · comunas / Senado · …", f"Lo mismo sumado por {etiq_com.lower()}."),
        ("Cámara · barrios / Senado · barrios", "Lo mismo sumado por barrio."),
        ("Formato largo", "Una fila por puesto y candidato, para tablas dinámicas y filtros."),
        ("", None),
        ("Fuentes", None),
        ("Votos", "Escrutinio de la Registraduría de las consultas del Pacto Histórico al Senado y a la Cámara (tarjetones aparte), mesa a mesa, sumado por puesto."),
        ("Localidad y barrio", "Censo de puestos de votación de la Registraduría. El barrio es el del lugar donde funciona el puesto, no el de residencia de quienes votaron."),
        ("Censo, sexo y edad", "Censo electoral por puesto publicado por la Registraduría para el Congreso 2026 (corte de enero de 2026). Es el más cercano a la consulta: no hay un censo publicado con la fecha exacta del 26 de octubre de 2025."),
        ("", None),
        ("Para leer bien los datos", None),
        ("Censo ≠ votantes", "El perfil por sexo y edad es de quienes PODÍAN votar en cada puesto, no de quienes votaron ni de quién votó por quién (el voto es secreto)."),
        ("Participación aproximada", "Votantes de la consulta / censo del puesto. Es aproximada porque el censo es tres meses posterior a la consulta."),
        ("Puesto sin censo", "Un puesto no aparece en el censo de 2026; va con las columnas de censo vacías."),
        ("Barrio por coordenada", "Algunos puestos llegan sin barrio en el censo de puestos; se ubicaron por su coordenada en el mapa catastral de barrios (IDECA). Son: " + ", ".join(sorted(f["puesto"] for f in puestos if f["por_coord"])) + "." if any(f["por_coord"] for f in puestos) else "Todos los puestos traen su barrio del censo de puestos."),
        ("Consulta sin voto en blanco", "Las consultas internas no tienen voto en blanco: el total es votos por candidatos + nulos + no marcados."),
    ]
    for i, (a, b) in enumerate(lineas, 1):
        ws.cell(row=i, column=1, value=a)
        if b:
            ws.cell(row=i, column=2, value=b).alignment = Alignment(wrap_text=True, vertical="top")
        if b is None and a:
            ws.cell(row=i, column=1).font = Font(bold=True, size=13 if i == 1 else 11)

    # ── Candidatos ──
    ws = wb.create_sheet("Candidatos")
    encabezado(ws, ["Consulta", "Puesto en " + nombre_dep, "Candidato", "Votos", "% de los votos por candidatos"])
    r = 2
    for k, nom in CONSULTAS:
        total = sum(v for _, v in orden[k])
        for i, (n, v) in enumerate(orden[k], 1):
            for j, val in enumerate([nom, i, tc(n), v, v / total if total else 0], 1):
                ws.cell(row=r, column=j, value=val)
            r += 1
    anchos(ws, [11, 12, 42, 12, 14])
    formatos(ws, 2, {4}, {5})

    base_cols = ["Código del puesto", "Municipio", etiq_com, "Barrio", "Puesto de votación", "Dirección", "Latitud", "Longitud",
                 "Mesas", "Censo (personas habilitadas)", "Mujeres en el censo", "Hombres en el censo", "% mujeres en el censo"] + \
                [f"Censo {ETIQ_BANDA[b]} años" for b in BANDAS] + \
                ["Votos por candidatos", "Nulos", "No marcados", "Total votantes", "Participación aproximada"]

    def bloque_censo(censo_, muj, hom, bandas):
        return [censo_, muj, hom, (muj / censo_) if (censo_ and muj is not None) else None] + list(bandas)

    def bloque_votos(k, agg, censo_):
        tot = agg["votos"] + agg["nulos"] + agg["nm"]
        return [agg["votos"], agg["nulos"], agg["nm"], tot, (tot / censo_) if censo_ else None]

    for k, nom in CONSULTAS:
        cand = [n for n, _ in orden[k]]
        # puestos
        ws = wb.create_sheet(f"{nom} · puestos")
        encabezado(ws, base_cols + [tc(n) for n in cand])
        for i, f in enumerate(sorted(puestos, key=lambda x: (x["com"], x["bar"], x["puesto"])), 2):
            fila = [f["codigo"], f["mun"], f["com"], f["bar"], f["puesto"], f["dir"], f["lat"], f["lon"], f[k]["mesas"]] + \
                   bloque_censo(f["censo"], f["muj"], f["hom"], f["bandas"]) + bloque_votos(k, f[k], f["censo"]) + \
                   [f[k]["cands"].get(n, 0) for n in cand]
            for j, v in enumerate(fila, 1):
                ws.cell(row=i, column=j, value=v)
        n0 = len(base_cols)
        anchos(ws, [15, 14, 18, 26, 32, 30, 10, 10, 7, 12, 11, 11, 10] + [9] * len(BANDAS) + [11, 9, 10, 11, 12] + [12] * len(cand))
        formatos(ws, 2, set(range(9, 13)) | set(range(14, 14 + len(BANDAS))) | set(range(14 + len(BANDAS), 18 + len(BANDAS))) | set(range(n0 + 1, n0 + len(cand) + 1)),
                 {13, 18 + len(BANDAS)})

        # agregados por localidad y por barrio
        for nivel, llave, titulo in ((etiq_com, lambda f: (f["com"],), f"{nom} · {etiq_com.lower()}es" if es_bogota else f"{nom} · comunas"),
                                     ("Barrio", lambda f: (f["com"], f["bar"]), f"{nom} · barrios")):
            g = OrderedDict()
            for f in sorted(puestos, key=lambda x: (x["com"], x["bar"])):
                a = g.setdefault(llave(f), {"puestos": 0, "mesas": 0, "censo": 0, "muj": 0, "hom": 0, "bandas": [0] * len(BANDAS),
                                             "sin_censo": 0, "votos": 0, "nulos": 0, "nm": 0, "cands": defaultdict(int)})
                a["puestos"] += 1
                a["mesas"] += f[k]["mesas"]
                if f["censo"] is None:
                    a["sin_censo"] += 1
                else:
                    a["censo"] += f["censo"]; a["muj"] += f["muj"]; a["hom"] += f["hom"]
                    a["bandas"] = [x + y for x, y in zip(a["bandas"], f["bandas"])]
                for c in ("votos", "nulos", "nm"):
                    a[c] += f[k][c]
                for n, v in f[k]["cands"].items():
                    a["cands"][n] += v
            ws = wb.create_sheet(titulo[:31])
            cab_g = ([etiq_com] if nivel == "Barrio" else []) + [nivel, "Puestos", "Mesas", "Censo (personas habilitadas)", "Mujeres en el censo",
                     "Hombres en el censo", "% mujeres en el censo"] + [f"Censo {ETIQ_BANDA[b]} años" for b in BANDAS] + \
                    ["Votos por candidatos", "Nulos", "No marcados", "Total votantes", "Participación aproximada", "Puntero", "Votos del puntero", "% del puntero"] + [tc(n) for n in cand]
            encabezado(ws, cab_g)
            for i, (kk, a) in enumerate(g.items(), 2):
                pun = max(a["cands"].items(), key=lambda x: x[1]) if a["cands"] else ("", 0)
                fila = list(kk) + [a["puestos"], a["mesas"]] + bloque_censo(a["censo"], a["muj"], a["hom"], a["bandas"]) + \
                       bloque_votos(k, a, a["censo"]) + [tc(pun[0]), pun[1], (pun[1] / a["votos"]) if a["votos"] else None] + \
                       [a["cands"].get(n, 0) for n in cand]
                for j, v in enumerate(fila, 1):
                    ws.cell(row=i, column=j, value=v)
            off = 1 if nivel == "Barrio" else 0
            anchos(ws, ([18] if off else []) + [26, 8, 7, 12, 11, 11, 10] + [9] * len(BANDAS) + [11, 9, 10, 11, 12, 32, 10, 9] + [12] * len(cand))
            c0 = off + 2
            nums = set(range(c0, c0 + 5)) | set(range(c0 + 6, c0 + 6 + len(BANDAS))) | set(range(c0 + 6 + len(BANDAS), c0 + 10 + len(BANDAS))) | \
                {c0 + 12 + len(BANDAS)} | set(range(c0 + 14 + len(BANDAS), c0 + 14 + len(BANDAS) + len(cand)))
            formatos(ws, 2, nums, {c0 + 5, c0 + 10 + len(BANDAS), c0 + 13 + len(BANDAS)})

    # ── formato largo (las dos consultas) ──
    ws = wb.create_sheet("Formato largo")
    encabezado(ws, ["Consulta", "Código del puesto", etiq_com, "Barrio", "Puesto de votación", "Candidato", "Votos", "% del puesto"])
    i = 2
    for k, nom in CONSULTAS:
        for f in sorted(puestos, key=lambda x: (x["com"], x["bar"], x["puesto"])):
            for n, v in sorted(f[k]["cands"].items(), key=lambda x: -x[1]):
                if not v:
                    continue
                for j, val in enumerate([nom, f["codigo"], f["com"], f["bar"], f["puesto"], tc(n), v, v / f[k]["votos"] if f[k]["votos"] else None], 1):
                    ws.cell(row=i, column=j, value=val)
                i += 1
    anchos(ws, [10, 15, 18, 26, 32, 40, 9, 10])
    formatos(ws, 2, {7}, {8})
    ws.auto_filter.ref = f"A1:H{i - 1}"

    wb.save(salida)

    # ── control ──
    for k, nom in CONSULTAS:
        v = sum(f[k]["votos"] for f in puestos)
        vc = sum(x for _, x in orden[k])
        print(f"{nom}: {v:,} votos por candidatos (árbol {dep[k]['votos']:,}) · suma de candidatos {vc:,} · "
              f"nulos {sum(f[k]['nulos'] for f in puestos):,} · no marcados {sum(f[k]['nm'] for f in puestos):,} · "
              f"mesas {sum(f[k]['mesas'] for f in puestos):,}")
        assert v == dep[k]["votos"] == vc, "los votos no cuadran con el árbol de la consulta"
    sc = [f for f in puestos if f["censo"] is None]
    print(f"puestos {len(puestos):,} · sin censo {len(sc)} {[x['codigo'] for x in sc]} · "
          f"censo {sum(f['censo'] or 0 for f in puestos):,} · sin barrio {sum(1 for f in puestos if f['bar'] == 'Sin barrio registrado')}")
    print(f"→ {salida}")


if __name__ == "__main__":
    dd = (sys.argv[1] if len(sys.argv) > 1 else "16").zfill(2)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        ROOT / f"Bases de datos/encargos/consulta-pacto-2025/Consulta_Pacto_2025_{dd}_por_puesto.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    construir(dd, out)
