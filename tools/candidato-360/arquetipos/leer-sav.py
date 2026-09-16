#!/usr/bin/env python3
"""leer-sav.py — qué trae un archivo SPSS (.sav) de arquetipos, antes de usarlo.

Los arquetipos que llegan en .sav vienen de ENCUESTAS: cada fila es una persona,
no un barrio. Para llevarlos al mapa hace falta que el archivo traiga, además
del arquetipo, dónde vive la persona (parroquia, zona, recinto o barrio) y el
ponderador. Este script no analiza nada: dice qué hay, con las etiquetas que
SPSS guarda dentro del archivo, y si le indican las variables cruza arquetipo
por territorio, ponderado, para ver si la muestra alcanza por territorio.

  python3 tools/candidato-360/arquetipos/leer-sav.py archivo.sav
  python3 tools/candidato-360/arquetipos/leer-sav.py archivo.sav --arquetipo=SEG --territorio=PARROQUIA --pond=PESO

⚠️ Un .sav de encuesta trae datos de personas. Se lee local y NO se sube al
repo (está en .gitignore); lo que viaja son los agregados por territorio.
"""
import argparse, sys
try:
    import pyreadstat, pandas as pd
except ImportError:
    sys.exit("faltan pyreadstat y pandas:  pip install pyreadstat pandas")

ap = argparse.ArgumentParser()
ap.add_argument("archivo")
ap.add_argument("--arquetipo", help="variable del arquetipo o segmento")
ap.add_argument("--territorio", help="variable de dónde vive: parroquia, zona, recinto, barrio")
ap.add_argument("--pond", help="variable del ponderador (sin ella, cada fila pesa 1)")
ap.add_argument("--min", type=int, default=50, help="mínimo de encuestados por territorio para fiarse del cruce (50)")
a = ap.parse_args()

d, meta = pyreadstat.read_sav(a.archivo, apply_value_formats=True)
print(f"\n{a.archivo}\n{len(d):,} filas · {len(meta.column_names)} variables\n")
print(f"{'VARIABLE':<22}{'TIPO':<10}{'ETIQUETA':<44}VALORES")
print("─" * 110)
for nombre, etiqueta in zip(meta.column_names, meta.column_labels):
    vals = meta.variable_value_labels.get(nombre)
    tipo = "categórica" if vals else str(d[nombre].dtype)
    muestra = "; ".join(f"{k:g}={v}" for k, v in list(vals.items())[:4]) + (" …" if vals and len(vals) > 4 else "") if vals else f"{d[nombre].nunique()} distintos"
    print(f"{nombre:<22}{tipo:<10}{(etiqueta or '')[:42]:<44}{muestra[:60]}")

# Lo que hay que buscar para que esto llegue al mapa: dónde vive la persona.
pistas = [c for c in meta.column_names if any(p in c.lower() or p in (meta.column_labels[meta.column_names.index(c)] or '').lower() for p in ('parroq', 'zona', 'recinto', 'barrio', 'sector', 'canton', 'cantón', 'distrito'))]
print(f"\nVariables que parecen territorio: {', '.join(pistas) if pistas else 'NINGUNA — sin eso los arquetipos no se pueden poner en el mapa'}")
pesos = [c for c in meta.column_names if any(p in c.lower() for p in ('pond', 'peso', 'weight', 'factor'))]
print(f"Variables que parecen ponderador: {', '.join(pesos) if pesos else 'ninguna (cada fila pesaría 1)'}")

if a.arquetipo and a.territorio:
    w = d[a.pond] if a.pond else 1
    n = d.groupby(a.territorio, observed=True).size()
    t = pd.crosstab(d[a.territorio], d[a.arquetipo], values=w, aggfunc="sum", normalize="index").mul(100).round(1)
    t.insert(0, "n", n)
    print(f"\nArquetipo × {a.territorio} (ponderado, %):\n")
    print(t.to_string())
    flojos = n[n < a.min]
    if len(flojos):
        print(f"\n⚠ {len(flojos)} territorios con menos de {a.min} encuestados: {', '.join(map(str, flojos.index[:8]))}{' …' if len(flojos) > 8 else ''}.")
        print("  Ahí el porcentaje es ruido. Se resuelve con estimación de área pequeña (post-estratificación con el censo INEC 2022), no leyendo el cruce crudo.")
