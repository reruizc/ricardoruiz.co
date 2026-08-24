#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapas por barrio de Cartagena para el documento de 2V (campaña Abelardo).
Genera 5 PNG + barrio_labels.json (numeración de barrios prioritarios).
Los barrios sin puesto de votación heredan la tendencia del barrio vecino más
cercano (relleno de vecino), pintados con tono atenuado para distinguirlos.
"""
import json, os
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import matplotlib.patches as mpatches

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
GEO = f"{ROOT}/Bases de datos/output_pacto_1v_2026/geo/CARTAGENA-BARRIOS.json"
OUT = f"{ROOT}/Bases de datos/output_abelardo_cartagena"
DATA = f"{OUT}/cartagena_barrios.json"

for w in ["Regular", "Bold"]:
    fp = f"/Users/ricardoruiz/Library/Fonts/Inter-{w}.ttf"
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
plt.rcParams["font.family"] = "Inter"

ABE = "#1f47cc"; CEP = "#7a2d8f"; NODATA = "#e9e4d8"; INK = "#1a1a2e"
A_FILL = 0.42   # opacidad de los barrios heredados
BBOX = (-75.585, -75.435, 10.325, 10.505)

# ---- carga + asignación de datos
g = gpd.read_file(GEO)[["NOMBRE", "LOC", "geometry"]].to_crs("EPSG:4326").reset_index(drop=True)
rows = {x["barrio"]: x for x in json.load(open(DATA))}
g["d"] = g["NOMBRE"].map(lambda n: rows.get(n))
g["has"] = g["d"].notna()
FIELDS = ["abe_pct", "cep_pct", "margen", "ama_pct", "tier", "ganador"]
for f in FIELDS:
    g[f] = g["d"].map(lambda d: (d.get(f) if d else None))

# ---- relleno de vecino: cada barrio sin dato hereda el barrio con dato más cercano
data_idx = g.index[g["has"]].tolist()
fill_idx = g.index[~g["has"]].tolist()
if fill_idx:
    dP = g.loc[data_idx].to_crs("EPSG:3857")
    fP = g.loc[fill_idx].to_crs("EPSG:3857")
    jn = gpd.sjoin_nearest(fP[["geometry"]], dP[["geometry"]], how="left", distance_col="dist")
    jn = jn[~jn.index.duplicated(keep="first")]
    for fi, src in jn["index_right"].items():
        for f in FIELDS:
            g.at[fi, f] = g.at[src, f]
g["filled"] = ~g["has"]
g["cx"] = g.geometry.representative_point().x
g["cy"] = g.geometry.representative_point().y
print(f"barrios: {len(g)} · con dato directo: {g['has'].sum()} · heredados: {g['filled'].sum()}")


def base_ax(title, sub):
    fig, ax = plt.subplots(figsize=(7.4, 8.0))
    ax.set_xlim(BBOX[0], BBOX[1]); ax.set_ylim(BBOX[2], BBOX[3])
    ax.set_aspect(1 / 0.985); ax.axis("off")
    fig.text(0.045, 0.962, title, fontsize=15.5, weight="bold", color=INK)
    fig.text(0.045, 0.938, sub, fontsize=9.6, color="#55503f")
    return fig, ax


def outline(ax):
    g.boundary.plot(ax=ax, color="white", linewidth=0.45, zorder=3)


def footer(fig, txt):
    fig.text(0.045, 0.022, txt, fontsize=7.2, color="#8a8472")


def cat_plot(ax, field, mapping):
    """categórico: heredados con alpha, directos a opacidad plena."""
    for cat, c in mapping.items():
        sf = g[(g[field] == cat) & g["filled"]]
        if len(sf): sf.plot(ax=ax, color=c, edgecolor="white", linewidth=0.3, alpha=A_FILL, zorder=2)
        sd = g[(g[field] == cat) & ~g["filled"]]
        if len(sd): sd.plot(ax=ax, color=c, edgecolor="white", linewidth=0.4, zorder=2)


def cont_plot(ax, field, cmap, vmin, vmax, norm=None, label=""):
    """coroplético: heredados con alpha, directos plenos + barra de color."""
    kw = dict(cmap=cmap, norm=norm) if norm is not None else dict(cmap=cmap, vmin=vmin, vmax=vmax)
    gf = g[g["filled"]]
    if len(gf): gf.plot(ax=ax, column=field, edgecolor="white", linewidth=0.3, alpha=A_FILL, zorder=2, **kw)
    gd = g[~g["filled"]]
    gd.plot(ax=ax, column=field, edgecolor="white", linewidth=0.4, zorder=2,
            legend=True, legend_kwds=dict(shrink=0.4, label=label, orientation="vertical"), **kw)


SUB = "Preconteo oficial 1ª vuelta · 31-may-2026 · 137 puestos · 82 barrios con dato directo"
FOOT = ("Fuente: preconteo Registraduría por mesa + georreferenciación de puestos (PUESTOS_GEOREF) sobre 213 "
        "polígonos barriales (IDECA Cartagena). Barrios sin puesto propio: heredan la tendencia del vecino más "
        "cercano (tono atenuado).")

# ===================================================== 1 · GANADOR
fig, ax = base_ax("Cartagena · quién ganó cada barrio en 1ª vuelta",
                  SUB + "  ·  azul = Abelardo · morado = Cepeda")
cat_plot(ax, "ganador", {"Abelardo": ABE, "Cepeda": CEP})
outline(ax)
leg = [mpatches.Patch(color=ABE, label="Ganó Abelardo"),
       mpatches.Patch(color=CEP, label="Ganó Cepeda"),
       mpatches.Patch(color=ABE, alpha=A_FILL, label="Heredado del vecino")]
ax.legend(handles=leg, loc="lower right", frameon=False, fontsize=9.3)
footer(fig, FOOT); plt.savefig(f"{OUT}/m1_ganador.png", dpi=170, bbox_inches="tight"); plt.close()

# ===================================================== 2 · % ABELARDO
cmap_abe = LinearSegmentedColormap.from_list("abe", ["#f3f1ea", "#aac0ef", "#1f47cc", "#0a1f66"])
fig, ax = base_ax("Cartagena · fuerza de Abelardo por barrio (% sobre votos válidos)",
                  SUB + "  ·  más azul = más votó Abelardo")
cont_plot(ax, "abe_pct", cmap_abe, 15, 80, label="% Abelardo")
outline(ax); footer(fig, FOOT)
plt.savefig(f"{OUT}/m2_abelardo_pct.png", dpi=170, bbox_inches="tight"); plt.close()

# ===================================================== 3 · MARGEN
cmap_div = LinearSegmentedColormap.from_list("div", [CEP, "#d8c9e2", "#f3f1ea", "#aac0ef", ABE])
fig, ax = base_ax("Cartagena · margen Abelardo − Cepeda por barrio (puntos)",
                  SUB + "  ·  azul = ganó Abelardo · morado = ganó Cepeda")
cont_plot(ax, "margen", cmap_div, None, None, norm=TwoSlopeNorm(vmin=-70, vcenter=0, vmax=70), label="margen (pp)")
outline(ax); footer(fig, FOOT)
plt.savefig(f"{OUT}/m3_margen.png", dpi=170, bbox_inches="tight"); plt.close()

# ===================================================== 4 · BOLSA AMARILLA
cmap_ama = LinearSegmentedColormap.from_list("ama", ["#f3f1ea", "#f6dd8e", "#e8a33d", "#b5651d"])
fig, ax = base_ax("Cartagena · bolsa amarilla por barrio (% que votó por otros candidatos)",
                  SUB + "  ·  voto persuadible de 2ª vuelta")
cont_plot(ax, "ama_pct", cmap_ama, 3, 14, label="% amarillo")
outline(ax); footer(fig, FOOT)
plt.savefig(f"{OUT}/m4_amarillo.png", dpi=170, bbox_inches="tight"); plt.close()

# ===================================================== 5 · PRIORIDAD
TIER_COL = {"Disputado": "#e8b800", "Perdido cosechable": "#e07b39",
            "Bastión Cepeda": "#9a3b8f", "Bastión Abelardo": "#2a8a5a"}
TIER_LBL = {"Disputado": "Disputado — máxima prioridad",
            "Perdido cosechable": "Perdido pero cosechable",
            "Bastión Cepeda": "Bastión Cepeda — recursos mínimos",
            "Bastión Abelardo": "Bastión Abelardo — cuidar el voto"}
fig, ax = base_ax("Cartagena · mapa operativo de 2ª vuelta por barrio",
                  "Dónde concentrar el esfuerzo: amarillos por persuadir + verdes por cuidar")
cat_plot(ax, "tier", TIER_COL)
outline(ax)

labels = {}
n = 0
for r in sorted(rows.values(), key=lambda r: r["rank"]):
    if r["tier"] == "Bastión Abelardo":
        continue
    row = g[(g["NOMBRE"] == r["barrio"]) & ~g["filled"]]
    if not len(row):
        continue
    x, y = row.iloc[0]["cx"], row.iloc[0]["cy"]
    if not (BBOX[0] < x < BBOX[1] and BBOX[2] < y < BBOX[3]):
        continue
    n += 1
    labels[n] = dict(barrio=r["barrio"], tier=r["tier"], abe=r["abe_pct"], cep=r["cep_pct"],
                     margen=r["margen"], amarillo=r["amarillo"], verde=r["abelardo"], loc=r["loc_nombre"])
    ax.scatter([x], [y], s=128, color="white", edgecolor=INK, linewidth=0.8, zorder=4)
    ax.text(x, y, str(n), fontsize=6.8, weight="bold", ha="center", va="center", color=INK, zorder=5)
    if n >= 22:
        break

leg = [mpatches.Patch(color=c, label=TIER_LBL[t]) for t, c in TIER_COL.items()]
leg.append(mpatches.Patch(color="#9a3b8f", alpha=A_FILL, label="Heredado del vecino (tono claro)"))
ax.legend(handles=leg, loc="lower right", frameon=False, fontsize=8.4)
footer(fig, "Números = ranking de prioridad operativa (ver tabla). " + FOOT)
plt.savefig(f"{OUT}/m5_prioridad.png", dpi=170, bbox_inches="tight"); plt.close()

json.dump(labels, open(f"{OUT}/barrio_labels.json", "w"), ensure_ascii=False, indent=2)
print("mapas OK ·", n, "barrios numerados")
