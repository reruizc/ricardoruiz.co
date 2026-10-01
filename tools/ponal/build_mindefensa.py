#!/usr/bin/env python3
"""
build_mindefensa.py — baja de datos.gov.co (Socrata) las series públicas de
MinDefensa y la DIJIN que complementan la entrega SIEDCO, y las deja en UN
JSON que lee `policia-mindefensa.html`.

    python3 tools/ponal/build_mindefensa.py            # usa caché de consultas
    python3 tools/ponal/build_mindefensa.py --no-cache # vuelve a pegarle a Socrata

→ Bases de datos/output_ponal/mindefensa.json
Caché de cada consulta en Bases de datos/PONAL-SIEDCO/mindefensa-raw/{hash}.json

Dos familias con formato distinto (ver fuentes-mindefensa-datosgov.md):
  · MinDefensa: `fecha_hecho` real → date_extract_y(); `cantidad` numérico → sum().
  · DIJIN:      `fecha_hecho` TEXTO dd/mm/aaaa → substring(fecha_hecho,7,4);
                `cantidad` texto → count(*) o sum(cantidad::number).
Las consultas sobre capturas (3,7 M filas) tardan 30-120 s: por eso hay caché.
"""
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "Bases de datos" / "output_ponal" / "mindefensa.json"
CACHE = RAIZ / "Bases de datos" / "PONAL-SIEDCO" / "mindefensa-raw"
CACHE.mkdir(parents=True, exist_ok=True)
NO_CACHE = "--no-cache" in sys.argv
UA = "ricardoruiz.co/policia (reruizc@gmail.com)"

CIUDADES = {"11001": "Bogotá", "05001": "Medellín", "76001": "Cali", "08001": "Barranquilla",
            "13001": "Cartagena", "68001": "Bucaramanga", "54001": "Cúcuta", "08758": "Soledad",
            "25754": "Soacha", "47001": "Santa Marta"}
CIU_DIJIN = {k + "000": k for k in CIUDADES}       # codigo_dane de 8 dígitos
CIU_IN = ",".join(f"'{c}'" for c in CIUDADES)
CIU_IN8 = ",".join(f"'{c}'" for c in CIU_DIJIN)

# id → (delito del hub, nombre, campo de desglose opcional)
DELITOS_MD = [
    ("m8fd-ahd9", "homicidios", "Homicidios", None),
    ("gepp-dxcs", "violencia_intra", "Violencia intrafamiliar", None),
    ("bz43-8ahq", "delitos_sexuales", "Delitos sexuales", None),
    ("jr6v-i33g", "lesiones", "Lesiones personales", None),
    ("4rxi-8m8d", "hurto_personas", "Hurto a personas", None),
    ("7i2x-h5vp", "hurto_comercios", "Hurto a comercios", None),
    ("7mn7-vzqp", "hurto_residencias", "Hurto a residencias", None),
    ("csb4-y6v2", "hurto_vehiculos", "Hurto a vehículos", "tipo_delito"),
    ("q2ib-t9am", "extorsiones", "Extorsión", None),
    ("d7zw-hpf4", "secuestros", "Secuestro", "tipo_delito"),
    ("yi5j-5fe9", "terrorismo", "Terrorismo", None),
    ("sutf-7dyz", "pirateria", "Piratería terrestre", None),
    ("p88b-5ac7", "hurto_ganado", "Abigeato", None),
    ("i7h7-wmjc", "hurto_financieras", "Hurto a entidades financieras", None),
    ("uav5-b85g", "homicidios_at", "Homicidios en acc. de tránsito", None),
    ("ntej-qq7v", "lesiones_at", "Lesiones en acc. de tránsito", None),
    ("4v6r-wu98", "del_informaticos", "Delitos informáticos", None),
    ("95c7-mm6s", "trata", "Trata de personas", None),
]

# inventario para la tabla de la página (id, grupo, qué es)
INVENTARIO = [
    *[(i, "delitos", n) for i, _, n, _ in DELITOS_MD],
    ("u8eq-92tb", "delitos", "Masacres (casos y víctimas)"),
    ("meew-mguv", "dijin", "Amenazas (género y grupo etario)"),
    ("vuyt-mqpw", "dijin", "Violencia intrafamiliar (género y grupo etario)"),
    ("72sg-cybi", "dijin", "Lesiones personales y en accidente de tránsito"),
    ("ha6j-pa2r", "dijin", "Homicidios en accidente de tránsito"),
    ("d4fr-sbn2", "dijin", "Hurto por modalidades (I)"),
    ("6sqw-8cg5", "dijin", "Hurto por modalidades (II)"),
    ("3jdh-nmwu", "operativos", "Capturas por municipio y artículo penal"),
    ("2iz5-9bbz", "operativos", "Armas de fuego incautadas"),
    ("kk69-w2jj", "operativos", "Incautación de estupefacientes (DIJIN)"),
    ("nxbk-nikm", "operativos", "Incautación de base de coca"),
    ("26zg-9p9r", "operativos", "Incautación de cocaína"),
    ("g228-vp9d", "operativos", "Incautación de marihuana"),
    ("iat2-gskt", "operativos", "Incautación de heroína"),
    ("3cjd-phaj", "operativos", "Incautación de basuco"),
    ("p72f-qcvk", "operativos", "Erradicación de cultivos"),
    ("uvrw-m4tm", "operativos", "Aspersión"),
    ("s29y-2xjd", "operativos", "Destrucción de laboratorios"),
    ("3wcs-8xp9", "operativos", "Minería ilegal · capturas"),
    ("dxs6-mdeg", "operativos", "Minería ilegal · maquinaria"),
    ("gr35-i7pm", "operativos", "Minería ilegal · minas intervenidas"),
    ("8rpn-wpty", "operativos", "Afectación de la Fuerza Pública (heridos y asesinados)"),
    ("3pur-d5ez", "operativos", "Desmovilización individual"),
    ("ajsa-ebuq", "operativos", "Desvinculación de menores"),
    ("xg7g-dzk4", "operativos", "Sometimiento individual"),
    ("4y5w-y5sj", "operativos", "Resultados operativos (2024→)"),
    ("xac8-4he4", "codigo", "Comparendos Código de Policía (I)"),
    ("wbem-smzr", "codigo", "Comparendos Código de Policía (II)"),
    ("7j4w-6p73", "codigo", "Comparendos Código de Policía (III)"),
    ("ct4m-8t9m", "codigo", "Medidas correctivas (I)"),
    ("q4qm-6tai", "codigo", "Medidas correctivas (II)"),
    ("728x-tk8r", "codigo", "Medidas correctivas (III)"),
    ("c6wg-wr7w", "codigo", "Medios de policía"),
    ("rgdq-uqqk", "codigo", "Incautaciones por Código de Policía"),
    ("8mcu-22np", "victimas", "NNA víctimas de delitos"),
    ("makj-p2yr", "victimas", "Aprehensiones de menores"),
    ("6u2i-cstb", "victimas", "Capturas por delitos sexuales contra NNA"),
    ("p2r3-hbie", "victimas", "Turistas víctimas"),
    ("4uxk-dt6c", "otros", "Demandas notificadas a la Policía"),
    ("7r8m-evfz", "otros", "Fallos judiciales contra la Policía"),
    ("jwvi-unqh", "otros", "Directorio de cuadrantes"),
    ("cmxv-8tb9", "otros", "Frentes de seguridad por barrio"),
    ("h3f7-urhw", "otros", "Encuentros comunitarios por barrio"),
    ("7i66-rps2", "otros", "Estado de vías"),
    ("2ecm-y5we", "otros", "Preinscritos a patrullero"),
]


def soql(dataset, params, timeout=300):
    """GET a Socrata con caché en disco. Devuelve la lista de filas."""
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"https://www.datos.gov.co/resource/{dataset}.json?{qs}"
    key = hashlib.md5(url.encode()).hexdigest()
    cf = CACHE / f"{dataset}-{key}.json"
    if cf.exists() and not NO_CACHE:
        return json.loads(cf.read_text(encoding="utf-8"))
    t = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # noqa
            print(f"    reintento {intento+1} {dataset}: {e}", file=sys.stderr)
            time.sleep(5)
    else:
        raise RuntimeError(f"Socrata no respondió: {url}")
    cf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"  {dataset} {len(data):>6} filas · {time.time()-t:5.1f}s · {params.get('$select','')[:60]}", file=sys.stderr)
    return data


def meta(dataset):
    """Título y fecha de actualización del conjunto (api/views)."""
    cf = CACHE / f"meta-{dataset}.json"
    if cf.exists() and not NO_CACHE:
        return json.loads(cf.read_text(encoding="utf-8"))
    req = urllib.request.Request(f"https://www.datos.gov.co/api/views/{dataset}.json", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            v = json.loads(r.read().decode("utf-8"))
        m = {"nombre": v.get("name"), "actualizado": time.strftime("%Y-%m-%d", time.gmtime(v.get("rowsUpdatedAt", 0))),
             "filas": None, "columnas": [c.get("fieldName") for c in v.get("columns", [])],
             "desc": (v.get("description") or "")[:300]}
    except Exception as e:  # noqa
        m = {"nombre": None, "actualizado": None, "columnas": [], "desc": "", "error": str(e)[:80]}
    cf.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    return m


def n(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def anio_depto(dataset, campo=None, where=None):
    """MinDefensa: año × depto (× campo) → {clave: {anio: n}} y nacional."""
    sel = "date_extract_y(fecha_hecho) as a,cod_depto" + (f",{campo}" if campo else "") + ",sum(cantidad) as n"
    grp = "a,cod_depto" + (f",{campo}" if campo else "")
    p = {"$select": sel, "$group": grp, "$limit": 50000}
    if where:
        p["$where"] = where
    rows = soql(dataset, p)
    nac, dep = defaultdict(int), defaultdict(lambda: defaultdict(int))
    sub = defaultdict(lambda: defaultdict(int))
    for r in rows:
        a = r.get("a")
        if not a:
            continue
        nac[a] += n(r["n"])
        dep[r.get("cod_depto") or "?"][a] += n(r["n"])
        if campo:
            sub[r.get(campo) or "SIN DATO"][a] += n(r["n"])
    out = {"anio": dict(sorted(nac.items())), "depto": {k: dict(sorted(v.items())) for k, v in dep.items()}}
    if campo:
        out[campo] = {k: dict(sorted(v.items())) for k, v in sub.items()}
    return out


def anio_ciudad(dataset, campo=None):
    sel = "date_extract_y(fecha_hecho) as a,cod_muni" + (f",{campo}" if campo else "") + ",sum(cantidad) as n"
    grp = "a,cod_muni" + (f",{campo}" if campo else "")
    rows = soql(dataset, {"$select": sel, "$where": f"cod_muni in({CIU_IN})", "$group": grp, "$limit": 50000})
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for r in rows:
        if campo:
            out[r["cod_muni"]][r.get(campo) or "SIN DATO"][r["a"]] += n(r["n"])
        else:
            out[r["cod_muni"]]["_"][r["a"]] += n(r["n"])
    if campo:
        return {c: {k: dict(sorted(v.items())) for k, v in d.items()} for c, d in out.items()}
    return {c: dict(sorted(d["_"].items())) for c, d in out.items()}


def mes_nacional(dataset, desde=2024, where_extra=None):
    w = f"fecha_hecho >= '{desde}-01-01T00:00:00'"
    if where_extra:
        w += " AND " + where_extra
    rows = soql(dataset, {"$select": "date_trunc_ym(fecha_hecho) as m,sum(cantidad) as n", "$where": w,
                          "$group": "m", "$order": "m", "$limit": 5000})
    return {r["m"][:7]: n(r["n"]) for r in rows if r.get("m")}


def mes_ciudad(dataset, desde=2024):
    rows = soql(dataset, {"$select": "date_trunc_ym(fecha_hecho) as m,cod_muni,sum(cantidad) as n",
                          "$where": f"fecha_hecho >= '{desde}-01-01T00:00:00' AND cod_muni in({CIU_IN})",
                          "$group": "m,cod_muni", "$order": "m", "$limit": 5000})
    out = defaultdict(dict)
    for r in rows:
        if r.get("m"):
            out[r["cod_muni"]][r["m"][:7]] = n(r["n"])
    return dict(out)


def dijin_anio(dataset, where=None, campo=None):
    """DIJIN: año (texto) × campo → count(*) y sum(cantidad::number)."""
    sel = "substring(fecha_hecho,7,4) as a" + (f",{campo}" if campo else "") + ",count(*) as c,sum(cantidad::number) as s"
    grp = "a" + (f",{campo}" if campo else "")
    p = {"$select": sel, "$group": grp, "$limit": 50000}
    if where:
        p["$where"] = where
    rows = soql(dataset, p, timeout=600)
    if not campo:
        return {r["a"]: {"c": n(r["c"]), "s": n(r["s"])} for r in rows if r.get("a")}
    out = defaultdict(dict)
    for r in rows:
        if r.get("a"):
            out[r.get(campo) or "SIN DATO"][r["a"]] = {"c": n(r["c"]), "s": n(r["s"])}
    return dict(out)


def main():
    t0 = time.time()
    J = {"v": "2026-09-30", "corte": {"mindefensa": "2026-08-31", "dijin": "2026-07-31"},
         "ciudades": CIUDADES, "delitos": {}, "homicidio": {}, "inventario": []}

    # ── 1. delitos MinDefensa ────────────────────────────────────────────
    print("1. delitos MinDefensa", file=sys.stderr)
    for ds, did, nom, campo in DELITOS_MD:
        d = anio_depto(ds, campo)
        d["ciudad"] = anio_ciudad(ds, campo)
        d["mes"] = mes_nacional(ds)
        d["mes_ciudad"] = mes_ciudad(ds)
        d["dataset"], d["nombre"] = ds, nom
        J["delitos"][did] = d

    # ── 2. homicidio: lo que SIEDCO no trae ──────────────────────────────
    print("2. homicidio · modalidad, arma, sexo, feminicidio", file=sys.stderr)
    H = J["homicidio"]
    for campo in ("_modalidad_presunta", "arma_medio", "sexo", "spoa_caracterizacion", "zona"):
        H[campo] = anio_depto("m8fd-ahd9", campo)[campo]
        H[campo + "_ciudad"] = anio_ciudad("m8fd-ahd9", campo)
    fem = "spoa_caracterizacion='FEMINICIDIO'"
    H["feminicidio"] = anio_depto("m8fd-ahd9", None, fem)
    H["feminicidio"]["mes"] = mes_nacional("m8fd-ahd9", 2024, fem)
    rows = soql("m8fd-ahd9", {"$select": "date_extract_y(fecha_hecho) as a,cod_muni,sum(cantidad) as n",
                              "$where": fem + f" AND cod_muni in({CIU_IN})", "$group": "a,cod_muni", "$limit": 5000})
    fc = defaultdict(dict)
    for r in rows:
        fc[r["cod_muni"]][r["a"]] = n(r["n"])
    H["feminicidio"]["ciudad"] = dict(fc)
    # modalidad × mes 2025-2026 nacional (para ver el ritmo del sicariato)
    rows = soql("m8fd-ahd9", {"$select": "date_trunc_ym(fecha_hecho) as m,_modalidad_presunta as k,sum(cantidad) as n",
                              "$where": "fecha_hecho >= '2024-01-01T00:00:00'", "$group": "m,k", "$order": "m", "$limit": 5000})
    mm = defaultdict(dict)
    for r in rows:
        if r.get("m"):
            mm[r.get("k") or "SIN DATO"][r["m"][:7]] = n(r["n"])
    H["modalidad_mes"] = dict(mm)

    # ── 3. masacres y afectación FP ──────────────────────────────────────
    print("3. masacres · fuerza pública", file=sys.stderr)
    rows = soql("u8eq-92tb", {"$select": "date_extract_y(fecha_hecho) as a,cod_depto,sum(casos) as c,sum(victimas) as v",
                              "$group": "a,cod_depto", "$limit": 5000})
    ma, md = defaultdict(lambda: [0, 0]), defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in rows:
        if r.get("a"):
            ma[r["a"]][0] += n(r["c"]); ma[r["a"]][1] += n(r["v"])
            md[r.get("cod_depto") or "?"][r["a"]][0] += n(r["c"]); md[r.get("cod_depto") or "?"][r["a"]][1] += n(r["v"])
    J["masacres"] = {"anio": {a: {"casos": v[0], "victimas": v[1]} for a, v in sorted(ma.items())},
                     "depto": {d: {a: {"casos": v[0], "victimas": v[1]} for a, v in sorted(x.items())} for d, x in md.items()}}
    rows = soql("u8eq-92tb", {"$select": "cod_muni,municipio,departamento,sum(casos) as c,sum(victimas) as v",
                              "$where": "fecha_hecho >= '2025-01-01T00:00:00'", "$group": "cod_muni,municipio,departamento",
                              "$order": "v DESC", "$limit": 40})
    J["masacres"]["top_mun_2025_26"] = [{"m": r["municipio"], "d": r["departamento"], "casos": n(r["c"]), "victimas": n(r["v"])} for r in rows]
    fp = anio_depto("8rpn-wpty", "accion")
    J["fuerza_publica"] = {"anio": fp["accion"], "depto": fp["depto"]}
    rows = soql("8rpn-wpty", {"$select": "cod_depto,departamento,accion,sum(cantidad) as n",
                              "$where": "fecha_hecho >= '2025-01-01T00:00:00'", "$group": "cod_depto,departamento,accion", "$limit": 500})
    fd = defaultdict(lambda: {"HERIDO": 0, "ASESINADO": 0, "d": ""})
    for r in rows:
        fd[r["cod_depto"]][r["accion"]] = n(r["n"]); fd[r["cod_depto"]]["d"] = r["departamento"]
    J["fuerza_publica"]["depto_2025_26"] = dict(fd)

    # ── 4. capturas (DIJIN, lento) ───────────────────────────────────────
    print("4. capturas", file=sys.stderr)
    C = {}
    C["anio"] = dijin_anio("3jdh-nmwu")
    C["genero"] = dijin_anio("3jdh-nmwu", campo="genero")
    C["grupo_etario"] = dijin_anio("3jdh-nmwu", campo="grupo_etario")
    C["ciudad"] = {}
    rows = soql("3jdh-nmwu", {"$select": "substring(fecha_hecho,7,4) as a,codigo_dane,count(*) as c",
                              "$where": f"codigo_dane in({CIU_IN8})", "$group": "a,codigo_dane", "$limit": 5000}, timeout=600)
    for r in rows:
        C["ciudad"].setdefault(CIU_DIJIN.get(r["codigo_dane"], r["codigo_dane"]), {})[r["a"]] = n(r["c"])
    for a in ("2024", "2025", "2026"):
        rows = soql("3jdh-nmwu", {"$select": "descripcion_conducta_captura as k,count(*) as c",
                                  "$where": f"substring(fecha_hecho,7,4)='{a}'", "$group": "k", "$order": "c DESC", "$limit": 40}, timeout=600)
        C[f"conducta_{a}"] = [{"k": r["k"], "n": n(r["c"])} for r in rows]
    rows = soql("3jdh-nmwu", {"$select": "descripcion_conducta_captura as k,count(*) as c",
                              "$where": "substring(fecha_hecho,7,4)='2026' AND codigo_dane='11001000'", "$group": "k", "$order": "c DESC", "$limit": 25}, timeout=600)
    C["conducta_bogota_2026"] = [{"k": r["k"], "n": n(r["c"])} for r in rows]
    # capturas por homicidio (art. 103) nacional y ciudades
    rows = soql("3jdh-nmwu", {"$select": "substring(fecha_hecho,7,4) as a,count(*) as c",
                              "$where": "starts_with(descripcion_conducta_captura,'ARTÍCULO 103')", "$group": "a", "$limit": 100}, timeout=600)
    C["homicidio_anio"] = {r["a"]: n(r["c"]) for r in rows}
    rows = soql("3jdh-nmwu", {"$select": "substring(fecha_hecho,7,4) as a,codigo_dane,count(*) as c",
                              "$where": f"starts_with(descripcion_conducta_captura,'ARTÍCULO 103') AND codigo_dane in({CIU_IN8})",
                              "$group": "a,codigo_dane", "$limit": 1000}, timeout=600)
    C["homicidio_ciudad"] = {}
    for r in rows:
        C["homicidio_ciudad"].setdefault(CIU_DIJIN.get(r["codigo_dane"], r["codigo_dane"]), {})[r["a"]] = n(r["c"])
    J["capturas"] = C

    # ── 5. armas incautadas y estupefacientes (DIJIN) ────────────────────
    print("5. armas · estupefacientes", file=sys.stderr)
    A = {"anio": dijin_anio("2iz5-9bbz"), "clase": dijin_anio("2iz5-9bbz", campo="clase_bien"), "ciudad": {}}
    rows = soql("2iz5-9bbz", {"$select": "substring(fecha_hecho,7,4) as a,codigo_dane,sum(cantidad::number) as s",
                              "$where": f"codigo_dane in({CIU_IN8})", "$group": "a,codigo_dane", "$limit": 5000})
    for r in rows:
        A["ciudad"].setdefault(CIU_DIJIN.get(r["codigo_dane"], r["codigo_dane"]), {})[r["a"]] = n(r["s"])
    rows = soql("2iz5-9bbz", {"$select": "departamento,sum(cantidad::number) as s",
                              "$where": "substring(fecha_hecho,7,4)='2025'", "$group": "departamento", "$order": "s DESC", "$limit": 40})
    A["depto_2025"] = [{"d": r["departamento"], "n": n(r["s"])} for r in rows]
    J["armas"] = A
    J["estupefacientes"] = {"eventos_clase": dijin_anio("kk69-w2jj", campo="clase_bien")}

    # ── 6. Código de Policía ─────────────────────────────────────────────
    print("6. comparendos", file=sys.stderr)
    comp = {}
    # cada tabla trae su propio esquema: (campo de categoría, campo de cantidad, campo de municipio)
    ESQ = {"xac8-4he4": ("comportamiento", "cantidad", "lugar"),
           "wbem-smzr": ("numeral", "cant_ccc", "municipio"),
           "728x-tk8r": ("numeral", "cantidad_de_comparendos", "municipio"),
           "7j4w-6p73": ("medida_se_alada_del_codigo", "total", "municipio"),
           "ct4m-8t9m": ("literal", "cantidad", "municipio"),
           "q4qm-6tai": ("medida_aplicada_del_codigo", "total", "municipio")}
    for ds, (cat, qty, mun) in ESQ.items():
        m = meta(ds)
        rows = soql(ds, {"$select": f"{cat} as k,sum({qty}::number) as s", "$group": "k", "$order": "s DESC", "$limit": 20})
        rb = soql(ds, {"$select": f"{cat} as k,sum({qty}::number) as s", "$where": f"upper({mun}) like 'BOGOT%'",
                       "$group": "k", "$order": "s DESC", "$limit": 15})
        tot = soql(ds, {"$select": f"sum({qty}::number) as s"})
        comp[ds] = {"nombre": m.get("nombre"), "actualizado": m.get("actualizado"), "total": n(tot[0]["s"]) if tot else 0,
                    "top": [{"k": r["k"], "n": n(r["s"])} for r in rows], "top_bogota": [{"k": r["k"], "n": n(r["s"])} for r in rb]}
    J["codigo_policia"] = comp

    # ── 7. NNA víctimas ──────────────────────────────────────────────────
    print("7. NNA", file=sys.stderr)
    rows = soql("8mcu-22np", {"$select": "substring(fecha,1,4) as a,delito as k,count(*) as c", "$group": "a,k", "$limit": 5000})
    nn = defaultdict(dict)
    for r in rows:
        if r.get("a"):
            nn[r.get("k") or "SIN DATO"][r["a"]] = n(r["c"])
    rows2 = soql("8mcu-22np", {"$select": "substring(fecha,1,4) as a,genero as k,count(*) as c", "$group": "a,k", "$limit": 500})
    ng = defaultdict(dict)
    for r in rows2:
        if r.get("a"):
            ng[r.get("k") or "SIN DATO"][r["a"]] = n(r["c"])
    J["nna"] = {"delito": dict(nn), "genero": dict(ng)}

    # ── 8. inventario con metadatos ──────────────────────────────────────
    print("8. inventario", file=sys.stderr)
    for ds, grupo, que in INVENTARIO:
        m = meta(ds)
        J["inventario"].append({"id": ds, "grupo": grupo, "que": que, "nombre": m.get("nombre"),
                                "actualizado": m.get("actualizado"), "columnas": m.get("columnas", [])[:14]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(J, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"→ {OUT.relative_to(RAIZ)} ({OUT.stat().st_size/1024:.0f} KB) · {time.time()-t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
