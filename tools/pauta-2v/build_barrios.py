# -*- coding: utf-8 -*-
"""Capa por BARRIO para el plan de pauta 2V.
Por cada ciudad con polígonos de barrio, asigna cada puesto a su barrio por
PIP (lat/lon de PUESTOS_GEOREF) y agrega:
  - rec   = voto recuperable / movilización (twov puesto, suma)
  - young = % 18-35 del electorado (composición, w26 por puesto)
  - men   = % hombres del censo (georef)
  - censo = M+H
EDAD y SEXO van como COMPOSICIÓN del electorado (dónde se concentran jóvenes /
hombres), NO como voto por demografía — eso a nivel barrio sería EI demasiado
ruidosa. Es justo lo que se targetea en Meta (radio × edad × sexo).

Salidas:
  output_pauta_2v/barrios/<slug>.json   GeoJSON simplificado + métricas (para el HTML)
  output_pauta_2v/png/m_<slug>_{rec,young,men}_barrio.png   (para el Word)
"""
import csv, json, os
from collections import defaultdict
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACTO = os.path.join(ROOT, "Bases de datos", "output_pacto_1v_2026")
GEO = os.path.join(PACTO, "geo")
EDAD = os.path.join(ROOT, "Bases de datos", "output_edad_1v")
GEOREF = os.path.join(ROOT, "Bases de datos", "PUESTOS_GEOREF.csv")
OUT = os.path.join(ROOT, "Bases de datos", "output_pauta_2v")
os.makedirs(os.path.join(OUT, "barrios"), exist_ok=True)
os.makedirs(os.path.join(OUT, "png"), exist_ok=True)

# Inter para los PNG (mismo look del Word)
FDIR = os.path.join(ROOT, "tools", "pacto-1v-2026", "fonts")
for fn in ("Inter-Regular.ttf","Inter-Bold.ttf"):
    p = os.path.join(FDIR, fn)
    if os.path.exists(p): font_manager.fontManager.addfont(p)
plt.rcParams["font.family"] = "Inter"

OX = "#8a1e16"; INK = "#1a1510"; PAPER = "#f4f0e7"; GR = "#5a5448"

# slug, nombre, code(dep+mun electoral), geojson, namefield, lean(izq/der/mixto), approx, frame_pts
CITIES = [
    ("bogota","Bogotá","16001","BOG-BARRIOS-CATASTRALES.json","nombre","izq",False,False),
    ("cali","Cali","31001","CALI-BARRIOS.json","barrio","izq",False,False),
    ("cartagena","Cartagena","05001","CARTAGENA-BARRIOS.json","NOMBRE","izq",False,True),
    ("barranquilla","Barranquilla","03001","BARRANQUILLA-BARRIOS.json","NOMBRE","izq",False,False),
    ("soledad","Soledad","03052","SOLEDAD-BARRIOS.json","barrio","izq",False,False),
    ("buenaventura","Buenaventura","31019","BUENAVENTURA-BARRIOS.json","barrio","izq",False,True),
    ("santamarta","Santa Marta","21001","SANTAMARTA-BARRIOS-REAL.json","barrio","izq",False,True),
    ("medellin","Medellín","01001","MEDELLIN_BARRIOS_OFICIAL.json","NOMBRE","mixto",False,False),
    ("quibdo","Quibdó","17001","QUIBDO-BARRIOS.json","barrio","izq",False,True),
    ("pasto","Pasto","23001","PASTO-BARRIOS.json","barrio","izq",True,True),
    ("sincelejo","Sincelejo","28001","SINCELEJO-BARRIOS.json","barrio","izq",True,True),
    ("palmira","Palmira","31079","PALMIRA-BARRIOS.json","barrio","izq",True,True),
    ("bucaramanga","Bucaramanga","27001","BUCARAMANGA-BARRIOS.json","barrio","der",False,False),
    ("cucuta","Cúcuta","25001","CUCUTA-BARRIOS.json","barrio","der",False,False),
]
WORD_CITIES = {"bogota","cali","cartagena","barranquilla","buenaventura","medellin"}

# ── puestos: pcode -> lat/lon, M, H, rec, young, total ──────────────────────
geo_pue = {}   # pcode -> dict
with open(GEOREF, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f, delimiter=";"):
        cc = (row.get("CÓDIGO COMPLETO") or "").strip()
        if len(cc) != 9 or cc[5:7] in ("90","98"): continue
        try: la=float(row.get("LATITUD") or "nan"); lo=float(row.get("LONGITUD") or "nan")
        except: continue
        if not (-5<la<14 and -82<lo<-66): continue
        try: cM=int(float(row.get("MUJERES") or 0)); cH=int(float(row.get("HOMBRES") or 0))
        except: cM=cH=0
        geo_pue[cc] = {"lat":la,"lon":lo,"M":cM,"H":cH,"rec":0,"young":0.0,"tot":0.0,"mun":cc[:5]}

terr = json.load(open(os.path.join(PACTO, "twov_territorial.json")))
for p in terr["puesto"]:
    pc = str(p.get("pcode","")).zfill(9)
    if pc in geo_pue: geo_pue[pc]["rec"] += max(0, p.get("recuperar",0) or 0)

with open(os.path.join(EDAD, "w26-puesto.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        pc = row["pcode"].split("-")
        if len(pc) < 4: continue
        key = pc[0].zfill(2)+pc[1].zfill(3)+pc[2].zfill(2)+pc[3].zfill(2)
        if key not in geo_pue: continue
        try: bands=[float(row[f"b{i}"]) for i in range(10)]
        except: continue
        geo_pue[key]["young"] += sum(bands[:4]); geo_pue[key]["tot"] += sum(bands)

# GeoDataFrame de puestos
recs = list(geo_pue.values())
pts = gpd.GeoDataFrame(
    pd.DataFrame(recs),
    geometry=[Point(r["lon"], r["lat"]) for r in recs], crs="EPSG:4326")

def find_namefield(gdf, pref):
    if pref in gdf.columns: return pref
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object: return c
    return None

def render_png(gdf, col, fname, title, cmap):
    notna = gdf[gdf[col].notna()]
    if not len(notna): return
    vmin, vmax = float(notna[col].min()), float(notna[col].max())
    direct = gdf[(gdf[col].notna()) & (gdf["f"]==0)]
    filled = gdf[(gdf[col].notna()) & (gdf["f"]==1)]
    fig, ax = plt.subplots(figsize=(6.6,6.2), dpi=130)
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    gdf.plot(ax=ax, color="#e6e0d4", edgecolor="#cdc6b6", linewidth=.25)
    if len(filled):  # heredados del vecino: traslúcidos
        filled.plot(ax=ax, column=col, cmap=cmap, vmin=vmin, vmax=vmax,
                    edgecolor="#00000018", linewidth=.15, alpha=.45)
    direct.plot(ax=ax, column=col, cmap=cmap, vmin=vmin, vmax=vmax,
                edgecolor="#00000022", linewidth=.2, legend=True,
                legend_kwds={"shrink":.5,"pad":.01})
    minx,miny,maxx,maxy = notna.total_bounds
    ax.set_xlim(minx-.005,maxx+.005); ax.set_ylim(miny-.005,maxy+.005)
    ax.set_axis_off(); ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="left")
    fig.savefig(os.path.join(OUT,"png",fname), bbox_inches="tight", facecolor=PAPER); plt.close(fig)

index = []
for slug,name,code,gj,nf,lean,approx,frame in CITIES:
    path = os.path.join(GEO, gj)
    if not os.path.exists(path): print("  ⚠ falta", gj); continue
    g = gpd.read_file(path).to_crs("EPSG:4326")
    nfield = find_namefield(g, nf)
    g = g[[nfield,"geometry"]].rename(columns={nfield:"nm"}).reset_index(drop=True)
    g["nm"] = g["nm"].fillna("(sin nombre)").astype(str)
    # puestos de la ciudad (por municipio; frame_pts amplía un poco)
    cp = pts[pts["mun"] == code].copy()
    if not len(cp): print("  ⚠ sin puestos", slug); continue
    j = gpd.sjoin(cp, g.reset_index().rename(columns={"index":"bi"}), predicate="within", how="inner")
    agg = j.groupby("bi").agg(rec=("rec","sum"), M=("M","sum"), H=("H","sum"),
                              young=("young","sum"), tot=("tot","sum"), npue=("rec","size"))
    g["rec"]=None; g["young"]=None; g["men"]=None; g["censo"]=None; g["npue"]=0
    for bi,r in agg.iterrows():
        censo = int(r["M"]+r["H"])
        g.at[bi,"rec"]=int(r["rec"]); g.at[bi,"censo"]=censo; g.at[bi,"npue"]=int(r["npue"])
        g.at[bi,"young"]=round(r["young"]/r["tot"],3) if r["tot"]>0 else None
        g.at[bi,"men"]=round(r["H"]/censo,3) if censo>0 else None
    for c in ("rec","young","men","censo"): g[c]=pd.to_numeric(g[c], errors="coerce")
    g["npue"]=pd.to_numeric(g["npue"], errors="coerce").fillna(0).astype(int)
    # ── heredar del vecino más cercano: barrios sin puesto propio ───────────
    g["f"]=0
    have = g[g["npue"]>0]; need = g[g["npue"]==0]
    if len(have) and len(need):
        hc = have.copy(); hc["geometry"]=hc.geometry.to_crs(3857).centroid.to_crs(4326)
        nc = need.copy(); nc["geometry"]=nc.geometry.to_crs(3857).centroid.to_crs(4326)
        nn = gpd.sjoin_nearest(nc[["geometry"]].to_crs(3857),
                               hc[["rec","young","men","geometry"]].to_crs(3857), how="left")
        nn = nn[~nn.index.duplicated(keep="first")]
        for idx,row in nn.iterrows():
            for c in ("rec","young","men"): g.at[idx,c]=row[c]
            g.at[idx,"f"]=1
    # centroide REAL (lat/lon) como propiedad → el "copiar para Meta" del HTML
    # usa coords verdaderas aunque Bogotá se gire para mostrarse.
    cent = g.geometry.to_crs(3857).centroid.to_crs(4326)
    g["clon"] = cent.x.round(5); g["clat"] = cent.y.round(5)
    # Bogotá se gira 90° a la izquierda (convención del sitio) — solo para DISPLAY
    if slug == "bogota":
        g["geometry"] = g.geometry.rotate(90, origin=(-74.08, 4.65))
    pts_city = j  # (sin uso tras cambiar el encuadre a notna.total_bounds)
    # PNG para el Word (no rotamos: orientación geográfica real)
    if slug in WORD_CITIES:
        render_png(g, "rec", f"m_{slug}_rec_barrio.png", f"{name} · voto recuperable por barrio", "Reds")
        render_png(g, "young", f"m_{slug}_young_barrio.png", f"{name} · % jóvenes (18-35) por barrio", "Purples")
        render_png(g, "men", f"m_{slug}_men_barrio.png", f"{name} · % hombres por barrio", "YlGn")
    # GeoJSON simplificado para el HTML
    gw = g.copy(); gw["geometry"] = gw["geometry"].simplify(0.0004, preserve_topology=True)
    gw = gw[gw.geometry.notna() & ~gw.geometry.is_empty]
    out_path = os.path.join(OUT,"barrios",f"{slug}.json")
    gw.to_file(out_path, driver="GeoJSON")
    nb = int((g["npue"]>0).sum())   # directos (los heredados llevan f=1)
    sz = round(os.path.getsize(out_path)/1024,1)
    index.append({"slug":slug,"name":name,"lean":lean,"approx":approx,
                  "nbarrios":int(len(g)),"con_dato":int(nb),"kb":sz})
    print(f"  · {name:14} {len(g):4} barrios · {nb:4} con dato · {sz:6} KB"
          + ("  [PNG]" if slug in WORD_CITIES else "") + ("  ~aprox" if approx else ""))

json.dump(index, open(os.path.join(OUT,"barrios","_index.json"),"w"), ensure_ascii=False, indent=1)
print(f"\n✓ {len(index)} ciudades · índice en barrios/_index.json")
