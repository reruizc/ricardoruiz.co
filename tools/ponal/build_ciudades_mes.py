#!/usr/bin/env python3
"""
build_ciudades_mes.py — hechos por mes, comuna y barrio para las ciudades
principales, desde la entrega SIEDCO 2025-2026. Alimenta el módulo «Ciudades»
de policia-abiertos.html (mes contra mes anterior y año corrido).

    python3 tools/ponal/build_ciudades_mes.py
    → Bases de datos/output_ponal/ciudades-mes/{dane}.json  +  index.json

Cómo se ubica cada hecho:
  · BARRIO → polígono: por nombre normalizado contra la cartografía barrial de
    la ciudad (la misma de mapas-2026). Tres intentos, del más estricto al más
    laxo: exacto (`clave_barrio`), flexible (sin artículos, «sector», «etapa»,
    números romanos) y prefijo ÚNICO (el nombre de la denuncia es el comienzo
    de un solo polígono, o al revés). Si dos polígonos califican, no se asigna.
  · COMUNA: Bogotá, Medellín y Cali usan la misma cadena del hub (sufijo del
    barrio → diccionario barrio_comuna.json → descripción del hecho); si nada
    de eso da, la comuna del polígono casado. Las otras seis ciudades toman la
    comuna del polígono, porque su barrio nunca trajo el sufijo. En Pereira la
    denuncia escribe la comuna entre paréntesis — «(PER. CUBA)» — y se usa.
  · «Barrio pendiente por asignar» → sin barrio y sin comuna. Nunca se reparte.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ponal import (CANON, CIUDADES, SRC_2, BARRIO_NULO, VERTEDEROS, DIC_BARRIO,  # noqa
                         clave_barrio, comuna_por_desc, sin_tildes)

csv.field_size_limit(10 ** 9)
R = Path(__file__).resolve().parents[2]
GEO = R / "Bases de datos" / "PONAL-SIEDCO" / "geo-ciudades"
OUT = R / "Bases de datos" / "output_ponal" / "ciudades-mes"
OUT.mkdir(parents=True, exist_ok=True)
S3M = "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/"
S3B = "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/"
MESES = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]
MI = {m: i for i, m in enumerate(MESES)}

def num(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None

def nk(s):
    return re.sub(r"[^A-Z0-9]", "", sin_tildes(str(s or "")).upper())

def loc_baq(v):
    """Barranquilla: la capa de barrios escribe «Suroriental» donde la de
    localidades dice «SURORIENTE», y 5 barrios traen dos localidades separadas
    por coma (quedan con la primera)."""
    k = nk(str(v or "").split(",")[0])
    return {"SURORIENTAL": "SURORIENTE"}.get(k, k) or None

def com_cuc(p):
    """Cúcuta: un polígono de CUCUTAX llega sin número. Medido por punto en
    polígono: adentro caen 15 barrios, todos de la comuna 6, y la 6 es la única
    que falta en la capa. Ojo: la capa está incompleta — 45 barrios de la
    comuna 6 quedan fuera de todo polígono."""
    v = num(p.get("Comuna"))
    return 6 if v is None else v

# comuna del polígono de barrio → código de la capa de comunas
CFG = {
    "11001": dict(n="Bogotá", tipo="localidad", rot=True, encuadre="bar",  # sin Sumapaz
                  com=("BOG-LOCALIDADX.json", lambda p: num(p["LocCodigo"]), lambda p: p["LocNombre"].title()),
                  bar=("BOG-BARRIOS-CATASTRALES.json", "nombre", lambda p: num(p["loc_codigo"])), bar_url=S3M),
    "05001": dict(n="Medellín", tipo="comuna", rot=False, encuadre=list(range(1, 17)),  # casco urbano
                  com=("MEDELLINX.json", lambda p: num(p["CODIGO"]), lambda p: p["NOMBRE"]),
                  bar=("MEDELLIN_BARRIOS_OFICIAL.json", "NOMBRE", lambda p: num(str(p["CODIGO"])[:2])), bar_url=S3B),
    "76001": dict(n="Cali", tipo="comuna", rot=False,
                  com=("CALIX.json", lambda p: num(p["comuna"]), lambda p: p["nombre"]),
                  bar=("CALI-BARRIOS.json", "barrio", lambda p: num(p["comuna"])), bar_url=S3M),
    "08001": dict(n="Barranquilla", tipo="localidad", rot=False,
                  com=("BARRANQUILLAX.json", lambda p: nk(p["nombre"]), lambda p: p["nombre"].title()),
                  bar=("BARRANQUILLA-BARRIOS.json", "NOMBRE", lambda p: loc_baq(p["LOCALIDAD"])), bar_url=S3M),
    "13001": dict(n="Cartagena", tipo="UCG", rot=False,
                  com=("CARTAGENA-UCG.json", lambda p: num(p["UCG"]), lambda p: p["NOMBRE"]),
                  bar=("CARTAGENAX.json", "NOMBRE", lambda p: num(p["UCG"])), bar_url=S3M,
                  ventana=[10.34, 10.47, -75.57, -75.45]),
    "68001": dict(n="Bucaramanga", tipo="comuna", rot=False,
                  com=("BUCARAMANGAX.json", lambda p: num(p["COD_COMUNA"]), lambda p: p["NOMBRE_COM"]),
                  bar=("BUCARAMANGA-BARRIOS.json", "barrio", lambda p: num(p["cod_comuna"])), bar_url=S3M),
    "54001": dict(n="Cúcuta", tipo="comuna", rot=False,
                  com=("CUCUTAX.json", com_cuc, lambda p: f"Comuna {com_cuc(p)}"),
                  bar=("CUCUTA-BARRIOS.json", "barrio", lambda p: num(p["comuna"])), bar_url=S3M),
    "66001": dict(n="Pereira", tipo="comuna", rot=False,
                  com=("PEREIRAX.json", lambda p: nk(p["Comuna"]), lambda p: p["Comuna"]),
                  bar=("PEREIRA-BARRIOS.json", "NOMBRE", lambda p: nk(p["COMUNA"])), bar_url=S3M),
    "17001": dict(n="Manizales", tipo="comuna", rot=False,
                  com=("MANIZALESX.json", lambda p: num(p["ID_COMUNA"]), lambda p: p["NOMBRES_CO"]),
                  bar=("MANIZALES-BARRIOS.json", "BARRIOS", lambda p: num(p["Id_Comuna"])), bar_url=S3M),
}

STOP = r"\b(SECTOR|SEC|ETAPA|ET|URBANIZACION|URB|CONJUNTO|CONJ|BARRIO|BARIO|BRR|BR|INVASION|ASENTAMIENTO|CTO|CORREG|CORREGIMIENTO|VDA|VEREDA|LA|EL|LOS|LAS|DE|DEL|Y|NO)\b"

def flex(s):
    s = clave_barrio(re.sub(r"\(.*?\)", " ", str(s)))
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(STOP, " ", s)
    s = re.sub(r"\b([IVX]+|\d+)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()

GENERICAS = set("""CIUDAD VILLA VILLAS LOMA LOMAS QUINTA QUINTAS CENTRO CEMENTERIO PARQUE JARDIN
JARDINES BOSQUE BOSQUES ALTOS ALTO PORTAL BRISAS NUEVA NUEVO SANTA SAN CAMPO VALLE PRADO PRADOS
COLINAS MIRADOR BELLO BUENOS PUERTO PLAZA RESIDENCIAL CONDOMINIO TORRES MANZANA LOTE ZONA""".split())


class Casador:
    """Nombre de barrio de la denuncia → índice del polígono."""
    def __init__(self, nombres):
        self.ex, self.fl = defaultdict(set), defaultdict(set)
        self.lista = []
        for i, nm in enumerate(nombres):
            if not nm:
                continue
            self.ex[clave_barrio(nm)].add(i)
            f = flex(nm)
            if f:
                self.fl[f].add(i)
                self.lista.append((f, i))
        self.cache, self.modo = {}, Counter()

    def __call__(self, nom):
        if nom in self.cache:
            return self.cache[nom]
        r, modo = None, "sin"
        e = self.ex.get(clave_barrio(nom))
        if e and len(e) == 1:
            r, modo = next(iter(e)), "exacto"
        else:
            f = flex(nom)
            fl = self.fl.get(f)
            if fl and len(fl) == 1:
                r, modo = next(iter(fl)), "flexible"
            elif f and len(f) >= 5:
                # prefijo: el lado corto tiene que ser distintivo. Medido: con una
                # palabra genérica casaba «Ciudad Pacífica → Ciudad 2000»,
                # «Loma del Barro → La Loma», «Quinta Bosch → La Quinta».
                ok = lambda g: len(g.split()) >= 2 or (len(g) >= 6 and g not in GENERICAS)
                c = {i for g, i in self.lista
                     if (g.startswith(f + " ") and ok(f)) or (f.startswith(g + " ") and ok(g))}
                if len(c) == 1:
                    r, modo = next(iter(c)), "prefijo"
        self.cache[nom] = r
        self.modo[modo] += 1
        return r

RE_PER = re.compile(r"\((?:PER|CORREG)\.?\s*([^)]+)\)")

def main():
    ciu = {}
    for dane, c in CFG.items():
        gc = json.load(open(GEO / c["com"][0], encoding="utf-8"))
        gb = json.load(open(GEO / c["bar"][0], encoding="utf-8"))
        com_feat = [c["com"][1](f["properties"]) for f in gc["features"]]
        com_nom = {}
        for f in gc["features"]:
            k = c["com"][1](f["properties"])
            if k is not None:
                com_nom[k] = c["com"][2](f["properties"])
        bar_nom = [f["properties"].get(c["bar"][1]) or "" for f in gb["features"]]
        bar_com = [c["bar"][2](f["properties"]) for f in gb["features"]]
        ciu[dane] = dict(cfg=c, com_feat=com_feat, com_nom=com_nom, bar_nom=bar_nom, bar_com=bar_com,
                         cas=Casador(bar_nom), suf=re.compile(CIUDADES[dane]["suf"]) if dane in CIUDADES else None,
                         ciudad=defaultdict(lambda: [0] * len(MESES)), pend=defaultdict(lambda: [0] * len(MESES)),
                         sin_com=defaultdict(lambda: [0] * len(MESES)),
                         com=defaultdict(lambda: defaultdict(lambda: [0] * len(MESES))),
                         bar=defaultdict(lambda: defaultdict(lambda: [0] * len(MESES))),
                         bar_info={}, casado=0, con_barrio=0, total=0)

    with SRC_2.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f, delimiter=";")
        h = next(rd)
        I = {k: h.index(k) for k in ("Nombre Delitos", "Cantidad", "Fecha", "Hechos.CODIGO_DANE",
                                      "Hechos.BARRIOS_HECHO", "Hechos.COMUNAS_ZONAS_DESCRIPCION")}
        for row in rd:
            cod = row[I["Hechos.CODIGO_DANE"]].strip()
            dane = cod[:-3].zfill(5) if cod.isdigit() and len(cod) >= 6 else ""
            C = ciu.get(dane)
            if not C:
                continue
            did = CANON.get(row[I["Nombre Delitos"]].strip().lower())
            fe = row[I["Fecha"]]
            mi = MI.get(f"{fe[6:10]}-{fe[3:5]}") if len(fe) >= 10 else None
            if not did or mi is None:
                continue
            try:
                q = int(row[I["Cantidad"]] or 1) or 1
            except ValueError:
                q = 1
            C["ciudad"][did][mi] += q
            C["total"] += q
            b = row[I["Hechos.BARRIOS_HECHO"]].strip()
            if not b or BARRIO_NULO in b.upper():
                C["pend"][did][mi] += q
                C["sin_com"][did][mi] += q
                continue
            com = None
            if C["suf"]:
                m = C["suf"].search(b)
                if m:
                    com = int(m.group(1))
                    b = b[:m.start()].strip()
            if (dane, b.upper()) in VERTEDEROS:
                C["sin_com"][did][mi] += q
                continue
            C["con_barrio"] += q
            pi = C["cas"](b)
            if pi is not None:
                C["casado"] += q
            if dane in CIUDADES:
                if com is None:
                    com = DIC_BARRIO.get(dane, {}).get(clave_barrio(b))
                    d = comuna_por_desc(dane, row[I["Hechos.COMUNAS_ZONAS_DESCRIPCION"]])
                    if d is not None:
                        com = d
                if com is None and pi is not None:
                    com = C["bar_com"][pi]
            else:
                if pi is not None:
                    com = C["bar_com"][pi]
                elif dane == "66001":
                    m = RE_PER.search(b.upper())
                    if m and nk(m.group(1)) in C["com_nom"]:
                        com = nk(m.group(1))
            if com is not None and com not in C["com_nom"]:
                com = None
            if com is None:
                C["sin_com"][did][mi] += q
            else:
                C["com"][com][did][mi] += q
            key = clave_barrio(b)
            C["bar"][key][did][mi] += q
            inf = C["bar_info"].setdefault(key, {"n": Counter(), "p": pi, "c": Counter()})
            inf["n"][b.title()] += q
            if com is not None:
                inf["c"][com] += q

    index = []
    for dane, C in ciu.items():
        c = C["cfg"]
        dels = sorted(C["ciudad"], key=lambda d: -sum(C["ciudad"][d]))
        barrios = []
        for key, dd in C["bar"].items():
            inf = C["bar_info"][key]
            barrios.append([inf["n"].most_common(1)[0][0], inf["p"] if inf["p"] is not None else -1,
                            inf["c"].most_common(1)[0][0] if inf["c"] else None,
                            {d: v for d, v in dd.items() if any(v)}])
        barrios.sort(key=lambda x: -sum(sum(v) for v in x[3].values()))
        out = {"v": "2026-09-30", "dane": dane, "n": c["n"], "tipo": c["tipo"], "rot": c["rot"],
               "ventana": c.get("ventana"), "encuadre": c.get("encuadre"), "meses": MESES, "delitos": dels,
               "geo": {"com": S3M + c["com"][0], "bar": c["bar_url"] + c["bar"][0], "bar_campo": c["bar"][1]},
               "com_feat": C["com_feat"], "com_nom": {str(k): v for k, v in C["com_nom"].items()},
               "ciudad": dict(C["ciudad"]), "pend": {d: v for d, v in C["pend"].items() if any(v)},
               "sin_com": {d: v for d, v in C["sin_com"].items() if any(v)},
               "comunas": {str(k): {d: v for d, v in x.items() if any(v)} for k, x in C["com"].items()},
               "barrios": [[n, p, (str(cm) if cm is not None else None), d] for n, p, cm, d in barrios],
               "cobertura": {"hechos": C["total"], "con_barrio": C["con_barrio"], "casado": C["casado"],
                             "modos": dict(C["cas"].modo),
                             "con_comuna": C["total"] - sum(sum(v) for v in C["sin_com"].values())}}
        (OUT / f"{dane}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        cb = out["cobertura"]
        index.append({"dane": dane, "n": c["n"], "tipo": c["tipo"], "hechos": cb["hechos"]})
        print(f"  {c['n']:12s} {cb['hechos']:>8,} hechos · con barrio {100*cb['con_barrio']/cb['hechos']:.1f}% · "
              f"casado a polígono {100*cb['casado']/max(1,cb['con_barrio']):.1f}% · con comuna {100*cb['con_comuna']/cb['hechos']:.1f}% · "
              f"{len(barrios)} barrios · {(OUT / f'{dane}.json').stat().st_size/1024:.0f} KB · {dict(C['cas'].modo)}")
    index.sort(key=lambda x: -x["hechos"])
    (OUT / "index.json").write_text(json.dumps({"v": "2026-09-30", "meses": MESES, "ciudades": index}, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
