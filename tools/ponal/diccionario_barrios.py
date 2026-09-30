#!/usr/bin/env python3
"""
diccionario_barrios.py — diccionario barrio → comuna/localidad para las
ciudades con mapa de comuna del hub de Policía (Bogotá, Medellín, Cali).

    python3 tools/ponal/diccionario_barrios.py
    → Bases de datos/PONAL-SIEDCO/diccionario-barrio-comuna.csv   (para revisar)
    → tools/ponal/barrio_comuna.json                             (lo que usan los builds)

Por qué existe: en las entregas SIEDCO 2025-2026 el barrio dejó de traer el
sufijo de comuna (Bogotá: 89,6% con sufijo en 2015-2024 → 5,9% en 2025 →
3,5% en 2026), y la columna `COMUNAS_ZONAS_DESCRIPCION` no sirve de respaldo:
los barrios sin asignar llegan estampados «UPZ No. 14 USAQUEN E-1» (Bogotá) o
«COMUNA No. 4 ARANJUEZ» (Medellín), y hasta barrios con nombre vienen mal
(«PUENTE ARANDA» como UPZ de Usaquén). El barrio, en cambio, sí es estable.

Cómo se arma, en orden de autoridad:
  1. `tools/ponal/barrio_comuna_manual.csv` — correcciones a mano. Manda siempre.
  2. Votos del sufijo en TODA la base (2015-2024 + 2025-2026): cada vez que el
     barrio llegó con «C-14» o «E-7» es un voto por esa comuna. Se toma la
     moda. Si la moda tiene menos del 80% de los votos, el barrio queda con
     `revisar=1` (nombres que existen en dos comunas, o mal digitados) y NO
     entra al JSON hasta que alguien lo resuelva en el manual.
  3. Bogotá: el CATASTRO (`candidato-360-data/bogota-barrios/{loc}.js`, 1.000
     barrios con `loc_codigo`). Las entregas 2025-2026 usan nombres catastrales
     («EL CHANCO I», «CIUDAD SALITRE NOR-ORIENTAL») que en 2015-2024 nunca
     llegaron con sufijo. Solo nombres ÚNICOS en el catastro (un nombre que
     existe en dos localidades no se asigna). Si el sufijo quedó en `revisar`,
     el catastro lo resuelve solo si su localidad está entre las votadas.
  4. Medellín: los corregimientos no llevan «C-XX» sino su sigla: S.C. (San
     Cristóbal, 60), S.A.P. (San Antonio de Prado, 80), STA. E. (Santa Elena,
     90), «- PALMITAS» (50), ALTAVISTA (70). Códigos del GeoJSON MEDELLINX.
  5. Nada más. No se adivina por parecido de nombre.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ponal import CIUDADES, SRC, SRC_2, BARRIO_NULO, VERTEDEROS, sin_tildes, clave_barrio  # noqa

csv.field_size_limit(10 ** 9)
RAIZ = Path(__file__).resolve().parents[2]
OUT_CSV = RAIZ / "Bases de datos" / "PONAL-SIEDCO" / "diccionario-barrio-comuna.csv"
OUT_JSON = Path(__file__).parent / "barrio_comuna.json"
MANUAL = Path(__file__).parent / "barrio_comuna_manual.csv"
UMBRAL = 0.80
MIN_VOTOS = 3


def clave(nom):
    """Llave del barrio: sin tildes, mayúscula, espacios colapsados y sin
    prefijos de tipo que la fuente pone o quita según el año. Es la MISMA
    función que usa build_ponal al leer el diccionario."""
    return clave_barrio(nom)


CORREG_MDE = [(re.compile(r"\bS\.\s?A\.\s?P\.?$"), 80), (re.compile(r"\bS\.\s?C\.?$"), 60),
              (re.compile(r"\bSTA\.?\s?E\.?$"), 90), (re.compile(r"PALMITAS$"), 50),
              (re.compile(r"^ALTAVISTA\b"), 70)]


def catastro_bogota():
    """nombre catastral (clave) -> localidad, solo nombres únicos."""
    por = defaultdict(set)
    for p in sorted((RAIZ / "candidato-360-data" / "bogota-barrios").glob("*.js")):
        t = p.read_text(encoding="utf-8")
        g = json.loads(t[t.index("={") + 1:].rstrip().rstrip(";"))
        for f in g["features"]:
            pr = f["properties"]
            if pr.get("nombre") and pr.get("loc_codigo"):
                por[clave(pr["nombre"])].add(int(pr["loc_codigo"]))
    return {k: next(iter(v)) for k, v in por.items() if len(v) == 1}


def main():
    suf = {d: re.compile(c["suf"]) for d, c in CIUDADES.items()}
    votos = defaultdict(Counter)          # (dane, clave) -> Counter(comuna)
    hechos_sin = Counter()                # (dane, clave) -> hechos sin sufijo 2025-26
    nombre = {}
    for path in [SRC, SRC_2]:
        if not path.exists():
            continue
        nuevo = path == SRC_2
        with path.open(encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f, delimiter=";")
            h = next(rd)
            i_cod, i_bar, i_q = h.index("Hechos.CODIGO_DANE"), h.index("Hechos.BARRIOS_HECHO"), h.index("Cantidad")
            for n, row in enumerate(rd):
                if len(row) != len(h):
                    continue
                cod = row[i_cod].strip()
                if not (cod.isdigit() and len(cod) >= 6):
                    continue
                dane = cod[:-3].zfill(5)
                if dane not in CIUDADES:
                    continue
                b = row[i_bar].strip()
                if not b or BARRIO_NULO in b.upper():
                    continue
                m = suf[dane].search(b)
                nom = (b[:m.start()] if m else b).strip()
                k = clave(nom)
                if (dane, nom.upper()) in VERTEDEROS:
                    continue
                nombre.setdefault((dane, k), nom)
                try:
                    q = int(row[i_q] or 1) or 1
                except ValueError:
                    q = 1
                if m:
                    votos[(dane, k)][int(m.group(1))] += q
                elif nuevo:
                    hechos_sin[(dane, k)] += q
                if n % 2000000 == 0 and n:
                    print(f"  ... {path.name} {n:,}", file=sys.stderr, flush=True)

    manual = {}
    if MANUAL.exists():
        for r in csv.DictReader(MANUAL.open(encoding="utf-8")):
            if r.get("dane") and r.get("barrio") and r.get("comuna"):
                manual[(r["dane"].zfill(5), clave(r["barrio"]))] = int(r["comuna"])

    cat = catastro_bogota()
    filas, dic = [], defaultdict(dict)
    llaves = set(votos) | set(hechos_sin) | set(manual)
    for (dane, k) in llaves:
        v = votos.get((dane, k), Counter())
        tot = sum(v.values())
        moda, nm = (v.most_common(1)[0] if v else (None, 0))
        share = nm / tot if tot else 0
        man = manual.get((dane, k))
        if man is not None:
            com, fuente, revisar = man, "manual", 0
        elif tot >= MIN_VOTOS and share >= UMBRAL:
            com, fuente, revisar = moda, "sufijo", 0
        elif dane == "11001" and k in cat and (not tot or cat[k] in v):
            com, fuente, revisar = cat[k], ("catastro+sufijo" if tot else "catastro"), 0
        elif dane == "05001" and any(rx.search(k) for rx, _ in CORREG_MDE):
            com = next(c for rx, c in CORREG_MDE if rx.search(k))
            fuente, revisar = "corregimiento", 0
        else:
            com, fuente, revisar = None, "", 1 if tot else 0
        if com is not None:
            dic[dane][k] = com
        filas.append({
            "ciudad": CIUDADES[dane]["n"], "dane": dane, "barrio": nombre.get((dane, k), k),
            "clave": k, "comuna": com if com is not None else "",
            "fuente": fuente, "votos_sufijo": tot, "moda": moda or "",
            "share_moda": round(share, 3) if tot else "",
            "otras_comunas": ";".join(f"{c}:{n}" for c, n in v.most_common()[1:4]),
            "hechos_sin_sufijo_2025_26": hechos_sin.get((dane, k), 0),
            "revisar": revisar,
        })
    filas.sort(key=lambda r: (r["dane"], -r["hechos_sin_sufijo_2025_26"], -r["votos_sufijo"]))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    OUT_JSON.write_text(json.dumps(
        {"v": "2026-09-30", "umbral": UMBRAL, "min_votos": MIN_VOTOS,
         "nota": "barrio (clave normalizada) -> comuna. Generado por diccionario_barrios.py; "
                 "corregir en barrio_comuna_manual.csv, no aquí.",
         "ciudades": {d: dict(sorted(v.items())) for d, v in dic.items()}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for dane in CIUDADES:
        fs = [r for r in filas if r["dane"] == dane]
        sin = sum(r["hechos_sin_sufijo_2025_26"] for r in fs)
        cub = sum(r["hechos_sin_sufijo_2025_26"] for r in fs if r["comuna"] != "")
        rev = [r for r in fs if r["revisar"]]
        print(f"  {CIUDADES[dane]['n']:9s} {len(dic[dane]):>5} barrios en el diccionario · "
              f"2025-26 sin sufijo: {sin:,} hechos, {100*cub/max(1,sin):.1f}% ubicados · "
              f"{len(rev)} para revisar ({sum(r['hechos_sin_sufijo_2025_26'] for r in rev):,} hechos 2025-26)")
    print(f"  → {OUT_CSV.relative_to(RAIZ)}\n  → {OUT_JSON.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
