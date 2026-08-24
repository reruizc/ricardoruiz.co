#!/usr/bin/env python3
"""
Sprint E.2 · Pipeline build-indicadores-mun (Fase A).

Descarga 6 datasets de datos.gov.co (Socrata API) y genera un JSON
unificado de indicadores municipales con panel temporal 2018-2024.

Cobertura Fase A (8 indicadores derivados de 6 datasets):
  · Homicidios               (Policía Nacional · m8fd-ahd9)
  · Hurto a personas         (Policía Nacional · 4rxi-8m8d)
  · Hurto a vehículos        (Policía Nacional · csb4-y6v2)
  · Violencia intrafamiliar  (Policía Nacional · gepp-dxcs)
  · Delitos sexuales         (Policía Nacional · bz43-8ahq)
  · Cobertura neta 5-16      (MEN · sras-4t5p) → vía mapping ETC→DIVIPOLA
  · Deserción escolar        (MEN · sras-4t5p) → mismo
  · Matrícula 5-16           (MEN · sras-4t5p) → mismo

Output:
  Bases de datos/indicadores-mun/indicadores-mun.json   (~250-400 KB)

Stdlib pura — sin pandas, sin pip. Solo urllib + json.

Uso:
  python3 tools/build-indicadores-mun/build.py
  python3 tools/build-indicadores-mun/build.py --dataset homicidios   # solo uno
  python3 tools/build-indicadores-mun/build.py --no-cache              # ignora cache local
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "Bases de datos" / "indicadores-mun" / "raw"
OUT_DIR = ROOT / "Bases de datos" / "indicadores-mun"
RAW_DIR.mkdir(parents=True, exist_ok=True)

YEAR_FROM = 2018
YEAR_TO = 2024  # 2025-2026 quedan fuera por ser parciales

# ─────────────────────────────────────────────────────────────────────────
# Configuración de datasets Socrata
# ─────────────────────────────────────────────────────────────────────────
SECURITY_DATASETS = [
    {
        "id": "homicidios",
        "socrata": "m8fd-ahd9",
        "nombre": "Homicidios (víctimas)",
        "unidad": "víctimas/año",
        "categoria": "seguridad",
        "fuente": "Policía Nacional · Ministerio de Defensa",
        "fuente_url": "https://www.datos.gov.co/d/m8fd-ahd9",
        "nota": "Conteo de víctimas por homicidio intencional, registrado por DIJIN."
    },
    {
        "id": "hurto_personas",
        "socrata": "4rxi-8m8d",
        "nombre": "Hurto a personas",
        "unidad": "casos/año",
        "categoria": "seguridad",
        "fuente": "Policía Nacional · Ministerio de Defensa",
        "fuente_url": "https://www.datos.gov.co/d/4rxi-8m8d",
        "nota": "Casos reportados de hurto a personas."
    },
    {
        "id": "hurto_vehiculos",
        "socrata": "csb4-y6v2",
        "nombre": "Hurto a vehículos",
        "unidad": "casos/año",
        "categoria": "seguridad",
        "fuente": "Policía Nacional · Ministerio de Defensa",
        "fuente_url": "https://www.datos.gov.co/d/csb4-y6v2",
        "nota": "Hurto de motocicletas y automotores agregado."
    },
    {
        "id": "violencia_intrafamiliar",
        "socrata": "gepp-dxcs",
        "nombre": "Violencia intrafamiliar",
        "unidad": "víctimas/año",
        "categoria": "seguridad",
        "fuente": "Policía Nacional · Ministerio de Defensa",
        "fuente_url": "https://www.datos.gov.co/d/gepp-dxcs",
        "nota": "Casos de violencia al interior del núcleo familiar."
    },
    {
        "id": "delitos_sexuales",
        "socrata": "bz43-8ahq",
        "nombre": "Delitos sexuales",
        "unidad": "víctimas/año",
        "categoria": "seguridad",
        "fuente": "Policía Nacional · Ministerio de Defensa",
        "fuente_url": "https://www.datos.gov.co/d/bz43-8ahq",
        "nota": "Delitos del Título IV del Código Penal (artículos 205-219)."
    }
]

MEN_DATASET = {
    "socrata": "sras-4t5p",
    "fuente": "Ministerio de Educación Nacional",
    "fuente_url": "https://www.datos.gov.co/d/sras-4t5p",
    "nota_etc": "Reportado por Entidad Territorial Certificada (ETC). Para municipios no certificados, se aplica el valor del ETC departamental como aproximación.",
    "indicadores": [
        {
            "id": "cobertura_neta",
            "campo_socrata": "cobertura_neta",
            "nombre": "Cobertura neta educativa (5-16 años)",
            "unidad": "%",
            "categoria": "educacion"
        },
        {
            "id": "desercion",
            "campo_socrata": "desercion",
            "nombre": "Deserción escolar intra-anual",
            "unidad": "%",
            "categoria": "educacion"
        },
        {
            "id": "matricula_5_16",
            "campo_socrata": "poblacion_5_16",
            "nombre": "Población matriculada (5-16 años)",
            "unidad": "estudiantes",
            "categoria": "educacion"
        }
    ]
}

# ─────────────────────────────────────────────────────────────────────────
# Helpers de descarga Socrata
# ─────────────────────────────────────────────────────────────────────────
def _socrata_get(resource_id, query):
    """Ejecuta query Socrata y devuelve lista de dicts."""
    url = f"https://www.datos.gov.co/resource/{resource_id}.json?" + urllib.parse.urlencode(query, doseq=True, quote_via=urllib.parse.quote)
    req = urllib.request.Request(url, headers={"User-Agent": "ricardoruiz.co lab-indicadores/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def _fetch_security_panel(resource_id, cache_key, use_cache=True):
    """Devuelve dict { cod_muni: { año: total } } usando query agregada."""
    cache = RAW_DIR / f"{cache_key}.json"
    if use_cache and cache.exists():
        print(f"  ↪ cache hit: {cache.name}")
        return json.loads(cache.read_text())
    print(f"  ↓ socrata: {resource_id}", flush=True)
    rows = _socrata_get(resource_id, {
        "$select": f"cod_muni, date_extract_y(fecha_hecho) as anio, sum(cantidad) as total",
        "$where": f"date_extract_y(fecha_hecho)>={YEAR_FROM} AND date_extract_y(fecha_hecho)<={YEAR_TO}",
        "$group": "cod_muni, anio",
        "$limit": 50000
    })
    out = {}
    for r in rows:
        mun = (r.get("cod_muni") or "").zfill(5)
        anio = int(r.get("anio") or 0)
        tot = int(float(r.get("total") or 0))
        if not mun or not anio: continue
        out.setdefault(mun, {})[str(anio)] = tot
    cache.write_text(json.dumps(out, ensure_ascii=False))
    print(f"    {len(out)} muns con datos")
    return out

def _fetch_mun_master(use_cache=True):
    """Lista maestra de municipios con DIVIPOLA + nombre + depto. La construimos
    del dataset de homicidios (todos los muns aparecen en alguna fila histórica)."""
    cache = RAW_DIR / "_mun_master.json"
    if use_cache and cache.exists():
        print("  ↪ cache hit: _mun_master.json")
        return json.loads(cache.read_text())
    print("  ↓ socrata: catálogo de municipios (vía homicidios histórico)", flush=True)
    rows = _socrata_get("m8fd-ahd9", {
        "$select": "cod_muni, municipio, cod_depto, departamento",
        "$group": "cod_muni, municipio, cod_depto, departamento",
        "$limit": 50000
    })
    master = {}
    for r in rows:
        mun = (r.get("cod_muni") or "").zfill(5)
        if not mun or mun == "00000": continue
        # Si hay varios nombres por código (cambios históricos), elegimos el más reciente
        # — por simplicidad, el primero que aparezca con nombre no vacío.
        if mun not in master and r.get("municipio"):
            master[mun] = {
                "nombre": (r.get("municipio") or "").strip().title(),
                "depto":  (r.get("departamento") or "").strip().title(),
                "cod_depto": (r.get("cod_depto") or "").zfill(2)
            }
    cache.write_text(json.dumps(master, ensure_ascii=False, indent=2))
    print(f"    {len(master)} municipios en el catálogo")
    return master

def _fetch_men_panel(use_cache=True):
    """Devuelve dict { cod_etc: { 'nombre':..., año: {cobertura_neta, desercion, poblacion_5_16} } }."""
    cache = RAW_DIR / "men_panel.json"
    if use_cache and cache.exists():
        print("  ↪ cache hit: men_panel.json")
        return json.loads(cache.read_text())
    print(f"  ↓ socrata: {MEN_DATASET['socrata']}", flush=True)
    rows = _socrata_get(MEN_DATASET["socrata"], {
        "$select": "ano, cod_etc, nombre_etc, cobertura_neta, desercion, poblacion_5_16",
        "$where": f"ano>={YEAR_FROM} AND ano<={YEAR_TO}",
        "$limit": 50000
    })
    out = {}
    for r in rows:
        etc = str(r.get("cod_etc") or "").strip()
        anio = str(r.get("ano") or "")
        if not etc or not anio: continue
        item = out.setdefault(etc, { "nombre": (r.get("nombre_etc") or "").strip(), "anios": {} })
        item["anios"][anio] = {
            "cobertura_neta": _try_float(r.get("cobertura_neta")),
            "desercion":      _try_float(r.get("desercion")),
            "matricula_5_16": _try_int(r.get("poblacion_5_16"))
        }
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"    {len(out)} ETCs con datos")
    return out

def _try_float(v):
    if v is None or v == "": return None
    try: return round(float(v), 2)
    except (ValueError, TypeError): return None

def _try_int(v):
    if v is None or v == "": return None
    try: return int(float(v))
    except (ValueError, TypeError): return None

# ─────────────────────────────────────────────────────────────────────────
# Mapping ETC → DIVIPOLA
# ─────────────────────────────────────────────────────────────────────────
# Los 95 ETCs del MEN: 32 departamentales + 63 municipios certificados.
# Construimos el mapping por nombre normalizado: si nombre_etc matchea un
# departamento → aplica a todos los muns de ese depto. Si matchea un mun
# certificado → aplica solo a ese mun.
def _norm(s):
    if not s: return ""
    s = s.upper().strip()
    repl = (("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),("Ñ","N"),("Ü","U"),
            ("(ETC)",""),("D.C.","DC"),(".",""),(",",""),("  "," "))
    for a,b in repl: s = s.replace(a, b)
    # Quitar parentéticos tipo "(Antioquia)" o "(ANTIOQUIA)" si quedaron
    import re
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()

# Aliases manuales: el MEN usa nombres ligeramente distintos a los de DIVIPOLA
# del dataset de homicidios. Estos son los 4 casos detectados en la corrida inicial.
ETC_ALIASES = {
    "CARTAGENA": "CARTAGENA DE INDIAS",             # → 13001
    "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA": "SAN ANDRES ISLAS",  # depto 88
    "ARCHIPIELAGO DE SAN ANDRES": "SAN ANDRES ISLAS",
    "BOGOTA DC": "BOGOTA DC"  # ya debería matchear; alias por si el master lo trae como "BOGOTA"
}

def _build_etc_to_divipola(men_panel, mun_master):
    """Devuelve dict { cod_etc: { 'muns': [divipola...], 'tipo': 'depto'|'mun' } }."""
    # Nombre normalizado del depto → cod_depto
    depto_by_norm = {}
    for code, info in mun_master.items():
        depto_by_norm[_norm(info["depto"])] = info["cod_depto"]
    # Nombre normalizado de mun → divipola
    mun_by_norm = {}
    for code, info in mun_master.items():
        key = (_norm(info["nombre"]), info["cod_depto"])
        mun_by_norm[key] = code
    # Recolectar muns por cod_depto
    muns_by_depto = {}
    for code, info in mun_master.items():
        muns_by_depto.setdefault(info["cod_depto"], []).append(code)

    mapping = {}
    unmatched = []
    for etc_code, etc_info in men_panel.items():
        name_norm = _norm(etc_info["nombre"])
        # Aplicar alias manual si existe
        name_norm = ETC_ALIASES.get(name_norm, name_norm)
        # Caso 1: ETC departamental (ej "Antioquia (ETC)", "Bogotá D.C.")
        if name_norm in depto_by_norm:
            dep = depto_by_norm[name_norm]
            mapping[etc_code] = { "tipo": "depto", "muns": muns_by_depto.get(dep, []), "nombre": etc_info["nombre"] }
            continue
        # Caso 2: ETC municipio certificado (ej "Medellín", "Cali", "Cartagena")
        candidate_muns = []
        for code, info in mun_master.items():
            if _norm(info["nombre"]) == name_norm:
                candidate_muns.append(code)
        if len(candidate_muns) == 1:
            mapping[etc_code] = { "tipo": "mun", "muns": candidate_muns, "nombre": etc_info["nombre"] }
        elif len(candidate_muns) > 1:
            # Múltiples muns con mismo nombre — preferimos el de cod_depto más bajo
            candidate_muns.sort()
            mapping[etc_code] = { "tipo": "mun", "muns": [candidate_muns[0]], "nombre": etc_info["nombre"] + " (ambiguo)" }
        else:
            unmatched.append((etc_code, etc_info["nombre"]))
    if unmatched:
        print(f"  ⚠ {len(unmatched)} ETCs no matcheados:")
        for c, n in unmatched[:10]:
            print(f"     - {c}: {n}  (norm: {_norm(n)})")
    return mapping

# ─────────────────────────────────────────────────────────────────────────
# Ensamblar JSON final
# ─────────────────────────────────────────────────────────────────────────
def build(use_cache=True, only_dataset=None):
    print("Sprint E · build-indicadores-mun (Fase A)")
    print(f"Periodo: {YEAR_FROM}-{YEAR_TO}")
    print(f"Salida: {OUT_DIR / 'indicadores-mun.json'}")
    print()

    # 1) Catálogo maestro de municipios
    print("[1/3] Catálogo maestro de municipios")
    mun_master = _fetch_mun_master(use_cache=use_cache)

    # 2) Datos de seguridad (5 indicadores, panel por DIVIPOLA)
    print("\n[2/3] Indicadores de seguridad")
    sec_panels = {}
    for ds in SECURITY_DATASETS:
        if only_dataset and ds["id"] != only_dataset: continue
        sec_panels[ds["id"]] = _fetch_security_panel(ds["socrata"], ds["id"], use_cache=use_cache)
        time.sleep(0.3)  # cortesía con la API

    # 3) Datos educativos (3 indicadores derivados, panel por ETC → DIVIPOLA)
    print("\n[3/3] Indicadores educativos MEN")
    men_panel = {}
    etc_mapping = {}
    if not only_dataset or only_dataset.startswith("cobertura") or only_dataset == "desercion" or only_dataset == "matricula_5_16":
        men_panel = _fetch_men_panel(use_cache=use_cache)
        etc_mapping = _build_etc_to_divipola(men_panel, mun_master)

    # ─── Ensamblar
    print("\n[final] Ensamblando JSON")
    indicadores_meta = []
    for ds in SECURITY_DATASETS:
        indicadores_meta.append({
            "id": ds["id"], "nombre": ds["nombre"], "unidad": ds["unidad"],
            "categoria": ds["categoria"], "fuente": ds["fuente"], "fuente_url": ds["fuente_url"],
            "nota": ds["nota"],
            "panel": list(range(YEAR_FROM, YEAR_TO + 1))
        })
    for ind in MEN_DATASET["indicadores"]:
        indicadores_meta.append({
            "id": ind["id"], "nombre": ind["nombre"], "unidad": ind["unidad"],
            "categoria": ind["categoria"], "fuente": MEN_DATASET["fuente"],
            "fuente_url": MEN_DATASET["fuente_url"],
            "nota": MEN_DATASET["nota_etc"],
            "panel": list(range(YEAR_FROM, YEAR_TO + 1))
        })

    # Estructura por mun
    muns_out = {}
    for divipola, info in mun_master.items():
        m = { "nombre": info["nombre"], "depto": info["depto"], "cod_depto": info["cod_depto"], "datos": {} }
        # Seguridad: el panel viene directo
        for ds in SECURITY_DATASETS:
            data = sec_panels.get(ds["id"], {}).get(divipola, {})
            if data:
                m["datos"][ds["id"]] = data
        # MEN: buscar qué ETC cubre este DIVIPOLA
        if men_panel:
            for etc_code, mapping_info in etc_mapping.items():
                if divipola in mapping_info["muns"]:
                    etc_data = men_panel[etc_code]["anios"]
                    for ind in MEN_DATASET["indicadores"]:
                        serie = {}
                        for anio, datos in etc_data.items():
                            v = datos.get(ind["id"]) if ind["id"] in datos else datos.get(ind["campo_socrata"])
                            # ind.id ya es la key (cobertura_neta, desercion, matricula_5_16)
                            v = datos.get(ind["id"])
                            if v is not None: serie[anio] = v
                        if serie:
                            m["datos"][ind["id"]] = serie
                            # Marcar como aproximación si viene de ETC departamental
                            if mapping_info["tipo"] == "depto":
                                m["datos"].setdefault("_meta", {})[ind["id"]] = "ETC departamental (aprox)"
                    break  # un mun pertenece a un solo ETC
        muns_out[divipola] = m

    out = {
        "v": time.strftime("%Y%m%d"),
        "sprint": "E.2",
        "fase": "A",
        "periodo": [YEAR_FROM, YEAR_TO],
        "indicadores": indicadores_meta,
        "muns": muns_out,
        "stats": {
            "n_muns": len(muns_out),
            "n_indicadores": len(indicadores_meta),
            "muns_con_seguridad": sum(1 for m in muns_out.values() if any(k in m["datos"] for k in ["homicidios","hurto_personas"])),
            "muns_con_educacion": sum(1 for m in muns_out.values() if "cobertura_neta" in m["datos"])
        }
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "indicadores-mun.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"\n✓ Generado: {out_path}")
    print(f"  Tamaño: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"  Municipios: {out['stats']['n_muns']}")
    print(f"  Indicadores: {out['stats']['n_indicadores']}")
    print(f"  Muns con seguridad: {out['stats']['muns_con_seguridad']}")
    print(f"  Muns con educación: {out['stats']['muns_con_educacion']}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-cache", action="store_true", help="Ignora cache local y re-descarga")
    ap.add_argument("--dataset", help="Procesa solo un dataset (id)")
    args = ap.parse_args()
    build(use_cache=not args.no_cache, only_dataset=args.dataset)
