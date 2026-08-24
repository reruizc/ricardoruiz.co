#!/usr/bin/env python3
"""Carrusel IG 'voto femenino 1V-2026' · 10 piezas cuadradas 1080x1080.

Identidad de los carruseles previos (edad/conflicto): títulos Arima 700,
kicker Helvetica bold oxblood #8a1e16, papel #f1eee4, tinta #1a1510.
🔴 Cepeda/izquierda · 🔵 Abelardo/derecha · 🟣 acento mujeres (berry).

Eje: las mujeres deciden (mayoría + más participación) y, contra el cliché,
se inclinan a la DERECHA. Número duro propio: mesa con efectos fijos de puesto
(resultados reales 2022); 2026 confirmado por encuesta AtlasIntel.

Lee:  output_mujeres_1v/mesa-robusto-2022.json · mujeres-descriptivos.json
      output_pacto_1v_2026/geo/DEPARTAMENTOS2.json
Salida: output_mujeres_1v/carrusel/NN_*.png
Uso: python3 carrusel.py [all|portada|peso|giro|metodo|duelo|generacional|
                          ciudades|mapapart|mapadiv|cierre]
"""
import json
import os
import re
import sys
import unicodedata

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_mujeres_1v")
CDIR = os.path.join(OUT, "carrusel")
GEOF = os.path.join(HERE, "..", "..", "Bases de datos", "output_pacto_1v_2026",
                    "geo", "DEPARTAMENTOS2.json")

# ---- identidad Mujeres por la Democracia (brand sheet nov-2024) ----
# paleta: vinotinto + amarillo + blanco (80%) · lila acento (≤15%)
BG = "#FCFAF5"        # blanco cálido
VINO = "#5E003F"      # vinotinto · protagonista
AMAR = "#F9E254"      # amarillo · protagonista
LILA = "#EEBCFF"      # lila · acento
FG = VINO; SUB = "#7c5a6c"; INK3 = "#bda6b2"; GRID = "#e7dcd6"
OX = VINO             # kicker en vinotinto
RED = "#d1322e"       # Cepeda / izquierda (dato político)
BLUE = "#1f47cc"      # Abelardo / derecha (dato político)
PALOMA = "#6b8fe0"    # Paloma · azul claro
OTROS = "#bcaeb6"     # otros · gris malva
BERRY = VINO          # "mujeres" en datos -> vinotinto de marca
BERRY_D = "#42002c"   # vinotinto oscuro
SLATE = "#b09aa6"     # "hombres" -> malva neutro

from matplotlib.font_manager import FontProperties  # noqa: E402
RFONT = os.path.join(OUT, "reckless-font-family")
INTERD = os.path.join(HERE, "..", "pacto-1v-2026", "fonts")
for f in ("Inter-Regular.ttf", "Inter-Bold.ttf", "Inter-Italic.ttf"):
    font_manager.fontManager.addfont(os.path.join(INTERD, f))
F_TITLE = FontProperties(fname=os.path.join(RFONT, "RecklessStandardXL-TRIAL-SemiBold.otf"))
F_TITLE_M = FontProperties(fname=os.path.join(RFONT, "RecklessStandardXL-TRIAL-Medium.otf"))
TITLE_F = {"fontproperties": F_TITLE}
rcParams["font.family"] = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
DPI = 100
W = H = 1080

J = json.load(open(os.path.join(OUT, "mesa-robusto-2022.json")))
D = json.load(open(os.path.join(OUT, "mujeres-descriptivos.json")))
NIV = json.load(open(os.path.join(OUT, "genero-edad-niveles.json")))
_CJ = json.load(open(os.path.join(OUT, "comp-2026-sexedad.json")))
COMP = _CJ["comp"]
COMP_NAC = _CJ["nacional"]


def nrm(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z ]", "", s.upper()).strip()


def new_fig():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def head(fig, kicker, title, sub=None, tsize=40, ty=0.90, sy=None):
    fig.text(0.065, 0.953, kicker.upper(), fontsize=14, color=VINO, va="center",
             fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none", boxstyle="square,pad=0.45"))
    fig.text(0.065, ty, title, fontsize=tsize, color=FG, ha="left", va="top",
             linespacing=1.03, **TITLE_F)
    if sub:
        fig.text(0.065, sy or (ty - 0.105), sub, fontsize=17, color=SUB, ha="left",
                 va="top", linespacing=1.4)


def foot(fig, n, extra=None, dark=False):
    src_c = "#e9d7e1" if dark else SUB
    mark_c = AMAR if dark else VINO
    rr_c = "#ffffff" if dark else VINO
    num_c = "#caa9ba" if dark else INK3
    src = "Voto por sexo: mesa con efectos fijos de puesto + encuesta · RNEC · DANE · AtlasIntel"
    fig.text(0.065, 0.047, extra or src, fontsize=9, color=src_c, ha="left")
    fig.text(0.065, 0.023, "MUJERES POR LA DEMOCRACIA", fontsize=10, color=mark_c,
             ha="left", fontweight="bold")
    fig.text(0.935, 0.023, "ricardoruiz.co", fontsize=12.5, color=rr_c, ha="right",
             fontweight="bold")
    if n:
        fig.text(0.935, 0.953, n, fontsize=13, color=num_c, ha="right",
                 fontweight="bold")


def save(fig, name):
    os.makedirs(CDIR, exist_ok=True)
    p = os.path.join(CDIR, name)
    fig.savefig(p, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ->", os.path.relpath(p, os.path.join(HERE, "..", "..")))


def _mix(c1, c2, t):
    import matplotlib.colors as mc
    a = np.array(mc.to_rgb(c1)); b = np.array(mc.to_rgb(c2))
    return tuple(a + (b - a) * t)


_GEO = None


def geo_feats():
    global _GEO
    if _GEO is None:
        _GEO = json.load(open(GEOF))["features"]
    return _GEO


def draw_map(ax, valby, cmap_fn, default="#e3ddcd"):
    import matplotlib.colors as mc
    from matplotlib.patches import Polygon as MplPoly
    for ft in geo_feats():
        name = ft["properties"].get("name")
        v = valby.get(name)
        col = (mc.to_hex(cmap_fn(v)) if (v is not None and not
               (isinstance(v, float) and np.isnan(v))) else default)
        geom = ft.get("geometry")
        if not geom or not geom.get("coordinates"):
            continue
        polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
        for poly in polys:
            ext = np.asarray(poly[0], dtype=float)
            ax.add_patch(MplPoly(ext, closed=True, facecolor=col, edgecolor=BG,
                                 linewidth=0.6))
    ax.set_xlim(-79.3, -66.8); ax.set_ylim(-4.4, 13.7)
    ax.set_aspect(1 / np.cos(4.6 * np.pi / 180)); ax.axis("off")


# nombre RNEC/COMUNAS -> nombre del geojson
GEONAMES = ['Nariño', 'Putumayo', 'Chocó', 'Guainía', 'Vaupés', 'Amazonas',
            'La Guajira', 'Cesar', 'Norte de Santander', 'Arauca', 'Boyacá',
            'Vichada', 'Cauca', 'Valle del Cauca', 'Antioquia', 'Córdoba',
            'Sucre', 'Bolívar', 'Atlántico', 'Magdalena',
            'San Andrés y Providencia', 'Caquetá', 'Huila', 'Guaviare',
            'Caldas', 'Casanare', 'Meta', 'Distrito Capital de Bogotá',
            'Santander', 'Tolima', 'Quindío', 'Cundinamarca', 'Risaralda']
GN_NORM = {nrm(g): g for g in GEONAMES}


def to_geoname(name):
    n = nrm(name)
    if n in GN_NORM:
        return GN_NORM[n]
    if "BOGOTA" in n:
        return "Distrito Capital de Bogotá"
    if "SAN ANDRES" in n:
        return "San Andrés y Providencia"
    if "VALLE" in n:
        return "Valle del Cauca"
    for k, v in GN_NORM.items():
        if n in k or k in n:
            return v
    return None


REGION = {}
for n in "ATLANTICO BOLIVAR CESAR CORDOBA MAGDALENA SUCRE".split():
    REGION[n] = "CARIBE"
REGION.update({"LA GUAJIRA": "CARIBE", "SAN ANDRES Y PROVIDENCIA": "CARIBE"})
for n in "ANTIOQUIA CALDAS QUINDIO RISARALDA".split():
    REGION[n] = "ANT-EJE"
for n in ["CAUCA", "NARINO", "CHOCO", "VALLE DEL CAUCA"]:
    REGION[n] = "PACIFICO"
for n in ["CUNDINAMARCA", "BOYACA", "SANTANDER", "NORTE DE SANTANDER"]:
    REGION[n] = "CEN-ORIENTE"
for n in ["TOLIMA", "HUILA", "CAQUETA", "PUTUMAYO", "AMAZONAS"]:
    REGION[n] = "SUR"
for n in ["META", "CASANARE", "ARAUCA", "VICHADA", "GUAVIARE", "GUAINIA", "VAUPES"]:
    REGION[n] = "LLANOS"
REGION["DISTRITO CAPITAL DE BOGOTA"] = "BOGOTA"


# ===================================================== 01 PORTADA
def s01(n):
    fig = new_fig(); fig.patch.set_facecolor(VINO)
    fig.text(0.065, 0.935, "VOTO FEMENINO · 1ª VUELTA 2026", fontsize=14, color=VINO,
             va="center", fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none", boxstyle="square,pad=0.45"))
    fig.text(0.065, 0.855, "La elección la\ndeciden las mujeres.", fontsize=57,
             color="#ffffff", va="top", linespacing=1.0, **TITLE_F)
    fig.text(0.065, 0.585, "Y no como crees.", fontsize=57, color=AMAR, va="top",
             **TITLE_F)
    fig.text(0.065, 0.46, "Son mayoría, salen más a votar… y rompen el cliché\n"
             "sobre cómo vota una mujer.", fontsize=20, color=LILA, va="top",
             linespacing=1.45)
    fig.text(0.065, 0.345, "PARTICIPACIÓN EN LAS URNAS", fontsize=12.5, color=LILA,
             fontweight="bold")
    ax = fig.add_axes([0.065, 0.10, 0.87, 0.24]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 1)
    for i, (lab, v, c, tc) in enumerate([("Mujeres", 59, AMAR, VINO),
                                         ("Hombres", 53, "#9a6f88", "#ffffff")]):
        y = 0.62 - i * 0.42
        ax.barh(y, v, height=0.30, color=c)
        ax.text(1.5, y, f"{lab}  {v}%", color=tc, fontsize=15, va="center",
                fontweight="bold")
    foot(fig, n, extra="Participación femenina vs masculina · votantes / censo 2026.",
         dark=True)
    save(fig, "01_portada.png")


# ===================================================== 02 EL PESO
def s02(n):
    p = D["peso"]
    fig = new_fig()
    head(fig, "Primero, lo indiscutible", "Mayoría — y más constantes\nen las urnas",
         tsize=42, ty=0.90)
    # tres cifras grandes
    com = lambda v: f"{v:.1f}".replace(".", ",")
    stats = [(f"{p['share_votantes_muj']:.0f}%", "de quienes votaron\nson mujeres",
              f"{com(p['votantes_muj']/1e6)} M vs {com(p['votantes_hom']/1e6)} M hombres"),
             (f"+{com(p['brecha_participacion_pp'])}", "puntos más de\nparticipación",
              f"{p['participacion_muj']:.0f}% de ellas vs "
              f"{p['participacion_hom']:.0f}% de ellos"),
             ("1,8 M", "más mujeres que\nhombres votando",
              "la diferencia que\ndefine quién gana")]
    for i, (big, lab, sub) in enumerate(stats):
        x = 0.18 + i * 0.32
        fig.text(x, 0.66, big, fontsize=66, color=BERRY, ha="center", **TITLE_F)
        fig.text(x, 0.525, lab, fontsize=19, color=FG, ha="center", va="top",
                 linespacing=1.25, fontweight="bold")
        fig.text(x, 0.405, sub, fontsize=14, color=SUB, ha="center", va="top",
                 linespacing=1.35)
    fig.text(0.5, 0.235, "Quien quiera ser presidente\nnecesita el voto de ellas.",
             fontsize=27, color=FG, ha="center", va="top", linespacing=1.1, **TITLE_F)
    fig.text(0.5, 0.115, "Censo: 51,4% mujeres. Urnas: 54%. Salen más.",
             fontsize=16, color=SUB, ha="center")
    foot(fig, n, extra="Votantes proyectados por puesto + censo CNE 2026.")
    save(fig, "02_peso.png")


# ===================================================== 03 EL GIRO
def s03(n):
    fig = new_fig()
    head(fig, "El giro contraintuitivo",
         "En el Norte global, la mujer\nvota más a la izquierda.", tsize=37, ty=0.90)
    fig.text(0.065, 0.685, "En Colombia, al revés:", fontsize=39, color=OX,
             va="top", **TITLE_F)
    # dos filas: GRUPO -> LADO
    ax = fig.add_axes([0.065, 0.33, 0.87, 0.25]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    rows = [(0.72, "MUJER", BERRY_D, "DERECHA", BLUE),
            (0.24, "HOMBRE", SLATE, "IZQUIERDA", RED)]
    for y, g, gc, dest, dc in rows:
        ax.text(0.0, y, g, fontsize=27, color=gc, va="center", fontweight="bold")
        ax.annotate("", xy=(0.56, y), xytext=(0.34, y),
                    arrowprops=dict(arrowstyle="-|>,head_width=0.55,head_length=1.0",
                                    color=dc, lw=4.5))
        ax.text(0.60, y, dest, fontsize=27, color=dc, va="center", fontweight="bold")
    fig.text(0.065, 0.245, "El 'gender gap' del Norte global —mujeres más a la izquierda— "
             "está documentado\n(Inglehart & Norris, 2000). América Latina suele ir al "
             "contrario: voto\nfemenino más conservador y de orden.", fontsize=15.5,
             color=SUB, va="top", linespacing=1.4)
    fig.text(0.065, 0.105, "El cliché estaba al revés.", fontsize=24, color=FG,
             **TITLE_F)
    foot(fig, n)
    save(fig, "03_giro.png")


# ===================================================== 04 CÓMO LO SABEMOS
def s04(n):
    fig = new_fig()
    head(fig, "Cómo lo sabemos · el método",
         "No solo lo dicen las encuestas:\nlo verificamos mesa a mesa", tsize=33,
         ty=0.90)
    fig.text(0.065, 0.765, "La cédula separa por sexo y las mesas se asignan por "
             "rango de cédula:\ndentro de un mismo puesto hay mesas casi puras de "
             "mujeres y de hombres.", fontsize=15.5, color=SUB, va="top",
             linespacing=1.4)
    # esquema: un puesto con mesas rosadas/azules (izquierda)
    ax = fig.add_axes([0.065, 0.37, 0.55, 0.32]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0.02, 0.05), 0.96, 0.90,
                 boxstyle="round,pad=0.01,rounding_size=0.04", fc="#e7e2d4",
                 ec=GRID, lw=1.5))
    ax.text(0.06, 0.86, "UN PUESTO · mismo barrio y estrato", fontsize=11.5,
            color=FG, fontweight="bold")
    mesas = [BERRY, BERRY, SLATE, BERRY, SLATE, SLATE, BERRY, SLATE]
    labs = ["98%", "91%", "6%", "88%", "9%", "3%", "82%", "12%"]
    for i, (c, lb) in enumerate(zip(mesas, labs)):
        x = 0.07 + (i % 4) * 0.235; y = 0.47 - (i // 4) * 0.32
        ax.add_patch(Rectangle((x, y), 0.18, 0.24, fc=_mix(c, BG, 0.12), ec=c, lw=1.5))
        ax.text(x + 0.09, y + 0.12, lb, fontsize=12.5, color="white",
                ha="center", va="center", fontweight="bold")
    ax.text(0.07, -0.02, "vinotinto = mesa de mujeres   ·   malva = mesa de hombres",
            fontsize=10, color=SUB)
    # resultado: barras VERTICALES (derecha)
    fig.text(0.80, 0.66, "Brecha mujer − hombre", fontsize=13, color=FG,
             ha="center", fontweight="bold")
    fig.text(0.80, 0.633, "(voto 2022, en puntos)", fontsize=11.5, color=SUB, ha="center")
    ax2 = fig.add_axes([0.66, 0.40, 0.30, 0.21]); ax2.set_facecolor(BG)
    items = [(0, "Izquierda", -6.9, RED), (1, "Derecha", 4.7, BLUE)]
    for xx, lb, v, c in items:
        ax2.bar(xx, v, width=0.55, color=c)
        ax2.text(xx, v + (0.7 if v > 0 else -0.7), f"{v:+.0f}",
                 ha="center", va="bottom" if v > 0 else "top", fontsize=17,
                 fontweight="bold", color=c)
        ax2.text(xx, 1.2 if v < 0 else -1.2, lb, ha="center",
                 va="bottom" if v < 0 else "top", fontsize=12.5, color=FG)
    ax2.axhline(0, color=FG, lw=1.1); ax2.set_xlim(-0.7, 1.7); ax2.set_ylim(-9, 7)
    ax2.axis("off")
    fig.text(0.065, 0.30, "Comparar esas mesas DENTRO del puesto aísla el sexo de "
             "todo lo demás.", fontsize=18, color=FG, va="top", **TITLE_F)
    fig.text(0.065, 0.205, "96.000 mesas reales. Más de la mitad de los votos salen "
             "de mesas con >80% de un\nsolo sexo: casi no se extrapola. Y la encuesta "
             "AtlasIntel (11-06-2026) confirma\nla dirección, con dato individual.",
             fontsize=15, color=SUB, va="top", linespacing=1.5)
    foot(fig, n, extra="Efectos fijos de puesto + control de edad · 1V 2022 (RNEC).")
    save(fig, "04_metodo.png")


# ===================================================== 05 SI SOLO VOTARAN
def s05(n):
    SEG = [("Cepeda", RED), ("Abelardo", BLUE), ("Paloma", PALOMA), ("Otros", OTROS)]
    fig = new_fig()
    head(fig, "Dos elecciones en un país",
         "Si solo votaran ellas, gana Abelardo;\nsi solo ellos, gana Cepeda",
         tsize=31, ty=0.905)
    fig.text(0.065, 0.75, "Cómo habría quedado la PRIMERA VUELTA contando solo un "
             "sexo a la vez.", fontsize=15.5, color=SUB, va="top")
    ax = fig.add_axes([0.065, 0.33, 0.87, 0.40]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 1)
    for i, (lab, sexo) in enumerate([("SOLO MUJERES", "Mujeres"),
                                     ("SOLO HOMBRES", "Hombres")]):
        y = 0.74 - i * 0.46
        ax.text(0, y + 0.165, lab, fontsize=17, color=FG, fontweight="bold")
        left = 0
        d = COMP_NAC[sexo]
        for name, c in SEG:
            v = d[name]
            ax.barh(y, v, left=left, height=0.20, color=c, edgecolor=BG, lw=1.2)
            if name in ("Cepeda", "Abelardo"):
                ha, xx = ("left", left + 1.5) if left < 50 else ("right", left + v - 1.5)
                ax.text(xx, y, f"{name} {v:.0f}", color="white", fontsize=14.5,
                        va="center", ha=ha, fontweight="bold")
            elif v >= 6:
                ax.text(left + v / 2, y, f"{v:.0f}", color=FG if name == "Otros"
                        else "white", fontsize=11.5, va="center", ha="center")
            left += v
    # leyenda
    lax = fig.add_axes([0.065, 0.255, 0.87, 0.04]); lax.axis("off")
    lax.set_xlim(0, 1); lax.set_ylim(0, 1)
    xx = 0.0
    for name, c in SEG:
        lax.add_patch(Rectangle((xx, 0.3), 0.022, 0.45, color=c))
        lbl = "Otros (Fajardo, blanco, nulos)" if name == "Otros" else name
        lax.text(xx + 0.03, 0.52, lbl, fontsize=12.5, color=FG, va="center")
        xx += 0.10 + 0.022 + (0.20 if name == "Paloma" else 0.04)
    fig.text(0.065, 0.18, "El empate nacional (Abelardo 43,7 · Cepeda 40,9) lo "
             "desempata el género.", fontsize=17, color=FG, **TITLE_F)
    fig.text(0.065, 0.125, "Su base es femenina; la de Cepeda, masculina. AtlasIntel "
             "daba a las mujeres\ncon Abelardo cerca del 60% rumbo a segunda vuelta.",
             fontsize=14.5, color=SUB, va="top", linespacing=1.4)
    foot(fig, n, extra="Estimación propia: voto de 1ª vuelta por sexo (resultado 1V "
         "+ brecha medida en 2022). Confirma: AtlasIntel 11-06-2026.")
    save(fig, "05_duelo.png")


# ===================================================== 06 GENERACIONAL
def s06(n):
    AGE = ["18-35", "36-60", "61+"]
    SEG = [("Cepeda", RED), ("Abelardo", BLUE), ("Paloma", PALOMA), ("Otros", OTROS)]
    fig = new_fig()
    head(fig, "Edad y sexo se suman",
         "En cada edad, ellas se inclinan\nmás a la derecha que ellos", tsize=33,
         ty=0.90)
    fig.text(0.065, 0.755, "Cómo se repartió el voto por sexo y edad. En cada par, "
             "la mujer (arriba) pone\nmenos rojo (Cepeda) y más azul (Abelardo y "
             "Paloma) que el hombre.", fontsize=15, color=SUB, va="top",
             linespacing=1.4)
    ax = fig.add_axes([0.115, 0.165, 0.83, 0.50]); ax.set_facecolor(BG)
    ax.set_xlim(0, 100); ax.axis("off")
    ypos = {}
    y = 5.4
    for a in AGE:
        ypos[(a, "Mujeres")] = y; ypos[(a, "Hombres")] = y - 0.85
        y -= 2.25
    for (a, sexo), yy in ypos.items():
        left = 0
        d = COMP[sexo][a]
        for name, col in SEG:
            v = d[name]
            ax.barh(yy, v, left=left, height=0.72, color=col, edgecolor=BG, lw=1.2)
            if v >= 8:
                ax.text(left + v / 2, yy, f"{v:.0f}", ha="center", va="center",
                        fontsize=12, fontweight="bold",
                        color=FG if name == "Otros" else "white")
            left += v
        ax.text(-1.5, yy, "M" if sexo == "Mujeres" else "H", ha="right", va="center",
                fontsize=12.5, color=FG, fontweight="bold")
    for a in AGE:
        ymid = (ypos[(a, "Mujeres")] + ypos[(a, "Hombres")]) / 2
        ax.text(-7.5, ymid, f"{a}\naños", ha="center", va="center", fontsize=13,
                color=FG, fontweight="bold")
    ax.set_ylim(-0.1, 6.1); ax.set_xlim(-12, 100)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in SEG]
    ax.legend(hs, [s for s, _ in SEG], loc="upper center",
              bbox_to_anchor=(0.5, -0.04), ncol=4, frameon=False, fontsize=12.5,
              labelcolor=FG, handlelength=1.1, columnspacing=1.6)
    fig.text(0.065, 0.10, "Joven y hombre, lo más de izquierda; mayor y mujer, lo "
             "opuesto.\nLa derecha suma a las mujeres en todas las edades.",
             fontsize=14, color=FG, va="top", linespacing=1.35)
    foot(fig, n, extra="Estructura por edad 2026 (EI) × brecha de género medida en 2022.")
    save(fig, "06_generacional.png")


# ===================================================== 07 CIUDADES
def s07(n):
    rows = D["share_muj_muns_grandes"]
    # nombres
    NAMES = {"31-019": "Buenaventura", "44-001": "Florencia", "01-121": "Envigado",
             "52-001": "Villavicencio", "07-001": "Tunja", "11-001": "Popayán",
             "15-247": "Soacha", "23-001": "Pasto", "48-001": "Riohacha",
             "01-001": "Medellín", "29-001": "Ibagué", "19-001": "Neiva",
             "16-001": "Bogotá", "31-001": "Cali", "08-001": "Barranquilla"}
    pick = [r for r in rows if r["mun"] in NAMES][:10]
    fig = new_fig()
    head(fig, "Dónde votan más mujeres",
         "Buenaventura, la ciudad más\nfemenina de las urnas", tsize=34, ty=0.90)
    fig.text(0.065, 0.745, "% de mujeres entre quienes votaron · ciudades de "
             ">60 mil votantes.", fontsize=16, color=SUB, va="top")
    ax = fig.add_axes([0.30, 0.16, 0.62, 0.55]); ax.set_facecolor(BG)
    pick = pick[::-1]
    ys = np.arange(len(pick))
    for i, r in enumerate(pick):
        nm = NAMES[r["mun"]]; v = r["share_muj"]
        big = nm in ("Buenaventura", "Medellín")
        ax.barh(i, v, height=0.66, color=BERRY if big else _mix(BERRY, BG, 0.45))
        ax.text(v - 0.25, i, f"{v:.1f}%".replace(".", ","), va="center", ha="right",
                color="white", fontsize=12.5, fontweight="bold")
        ax.text(49.85, i, nm, va="center", ha="right", fontsize=13.5, color=FG,
                fontweight="bold" if big else "normal")
    ax.set_xlim(50, 60.5); ax.set_ylim(-0.6, len(pick) - 0.4); ax.axis("off")
    fig.text(0.065, 0.10, "Entre los grandes metros lidera Medellín (56%). Donde menos: "
             "pueblos\npetroleros e industriales (Barrancabermeja, Buga): llega mano de "
             "obra masculina.", fontsize=13.5, color=SUB, va="top", linespacing=1.4)
    foot(fig, n, extra="Mujeres entre votantes proyectados 2026 por municipio.")
    save(fig, "07_ciudades.png")


# ===================================================== 08 MAPA PARTICIPACIÓN
def s08(n):
    part = {to_geoname(r["name"]): r["brecha"] for r in D["participacion_depto"]
            if to_geoname(r["name"])}
    vmax = 12.6

    def cm(v):
        return _mix("#efe6ea", BERRY_D, min(v / vmax, 1))
    fig = new_fig()
    head(fig, "Dónde salen MÁS a votar que ellos",
         "En los Llanos y la Amazonía\nellas dejan atrás a los hombres", tsize=31,
         ty=0.90)
    fig.text(0.065, 0.755, "Cuántos puntos más participan las mujeres que los "
             "hombres, por depto.", fontsize=15.5, color=SUB, va="top")
    ax = fig.add_axes([0.05, 0.135, 0.60, 0.60]); draw_map(ax, part, cm)
    # ranking lateral
    top = sorted(D["participacion_depto"], key=lambda r: -r["brecha"])[:6]
    bot = sorted(D["participacion_depto"], key=lambda r: r["brecha"])[:3]
    fig.text(0.66, 0.66, "MÁS BRECHA", fontsize=13, color=BERRY_D, fontweight="bold")
    for i, r in enumerate(top):
        fig.text(0.66, 0.615 - i * 0.045, to_geoname(r["name"]) or r["name"].title(),
                 fontsize=13.5, color=FG)
        fig.text(0.935, 0.615 - i * 0.045, f"+{r['brecha']:.1f}", fontsize=13.5,
                 color=BERRY_D, ha="right", fontweight="bold")
    fig.text(0.66, 0.30, "MENOS (Caribe)", fontsize=13, color=SUB, fontweight="bold")
    for i, r in enumerate(bot):
        fig.text(0.66, 0.255 - i * 0.045, to_geoname(r["name"]) or r["name"].title(),
                 fontsize=13.5, color=SUB)
        fig.text(0.935, 0.255 - i * 0.045, f"+{r['brecha']:.1f}", fontsize=13.5,
                 color=SUB, ha="right", fontweight="bold")
    foot(fig, n, extra="Participación = votantes / censo, por sexo y departamento.")
    save(fig, "08_mapa_participacion.png")


# ===================================================== 09 MAPA DIVERGENCIA
RN = {"ANT-EJE": "Antioquia–Eje", "BOGOTA": "Bogotá", "CARIBE": "Caribe",
      "CEN-ORIENTE": "Centro-Oriente", "LLANOS": "Llanos", "PACIFICO": "Pacífico",
      "SUR": "Sur"}


def _mapa_gap(n, metric, accent, light, title, sub, bottom, fname, hdr):
    """Mapa de brecha de género por región. metric(reg_dict)->pp positivo."""
    reg = J["region_2022"]
    val, vmax = {}, max(metric(d) for d in reg.values())
    for g in GEONAMES:
        rg = REGION.get(nrm(g))
        if rg and rg in reg:
            val[g] = metric(reg[rg])

    def cm(v):
        return _mix(light, accent, min(v / vmax, 1))
    fig = new_fig()
    head(fig, "Geografía del voto por género", title, tsize=32, ty=0.90)
    fig.text(0.065, 0.775, sub, fontsize=15, color=SUB, va="top", linespacing=1.4)
    ax = fig.add_axes([0.045, 0.115, 0.56, 0.55]); draw_map(ax, val, cm)
    order = sorted(reg.items(), key=lambda kv: -metric(kv[1]))
    fig.text(0.63, 0.635, hdr, fontsize=12.5, color=accent, fontweight="bold")
    for i, (rg, d) in enumerate(order):
        fig.text(0.63, 0.585 - i * 0.05, RN[rg], fontsize=13.5, color=FG)
        fig.text(0.94, 0.585 - i * 0.05, f"{metric(d):.1f} pp", fontsize=13.5,
                 color=accent, ha="right", fontweight="bold")
    fig.text(0.065, 0.095, bottom, fontsize=14.5, color=FG, va="top", linespacing=1.4)
    foot(fig, n, extra="Brecha de género por región · mesa con efectos fijos de "
         "puesto, 2022.")
    save(fig, fname)


def s09(n):   # Abelardo: mujeres - hombres en voto de derecha (fico gap)
    _mapa_gap(n, lambda d: d["fico"], BLUE, "#e4e6f0",
              "El Caribe y Antioquia: donde\nellas votaron más a Abelardo",
              "En estas regiones las mujeres respaldaron a Abelardo bastante más\n"
              "que los hombres. Más oscuro = mayor diferencia (mujer − hombre).",
              "En la costa y en Antioquia, ellas empujaron al candidato de la derecha.",
              "09_mapa_abelardo.png", "ELLAS, MÁS A ABELARDO")


def s10b(n):  # Cepeda: hombres - mujeres en voto de izquierda (|petro| gap)
    _mapa_gap(n, lambda d: abs(d["petro"]), RED, "#f4e6e4",
              "El Caribe y Bogotá: donde\nellos votaron más a Cepeda",
              "Y al revés: aquí los hombres respaldaron a Cepeda bastante más\n"
              "que las mujeres. Más oscuro = mayor diferencia (hombre − mujer).",
              "Donde ella se va a la derecha, él se queda con Cepeda — y al máximo "
              "en la costa.",
              "10_mapa_cepeda.png", "ELLOS, MÁS A CEPEDA")


# ===================================================== 11 ABSTENCIÓN
def s_abst(n):
    p = D["peso"]
    abst_nac = 100 - p["participacion_muj"]
    n_abst = p["censo_muj"] * (1 - p["participacion_muj"] / 100) / 1e6
    rows = sorted(D["participacion_depto"], key=lambda r: r["part_muj"])[:8]
    fig = new_fig()
    head(fig, "El reto que queda",
         "Pero casi 9 millones de\nmujeres no votaron", tsize=34, ty=0.90)
    fig.text(0.065, 0.745, f"El {abst_nac:.0f}% de las habilitadas se quedó en casa "
             f"(los hombres, {100 - p['participacion_hom']:.0f}%). Dónde más:",
             fontsize=15.5, color=SUB, va="top")
    ax = fig.add_axes([0.30, 0.165, 0.62, 0.52]); ax.set_facecolor(BG)
    rows = rows[::-1]
    for i, r in enumerate(rows):
        ab = 100 - r["part_muj"]
        nm = to_geoname(r["name"]) or r["name"].title()
        ax.barh(i, ab, height=0.66, color=_mix("#cabfa6", "#473d2c", min(ab / 68, 1)))
        ax.text(ab - 1.2, i, f"{ab:.0f}%", va="center", ha="right", color="white",
                fontsize=12.5, fontweight="bold")
        ax.text(-1.5, i, nm, va="center", ha="right", fontsize=13.5, color=FG)
    ax.set_xlim(0, 72); ax.set_ylim(-0.6, len(rows) - 0.4); ax.axis("off")
    fig.text(0.065, 0.10, "Más que izquierda o derecha, ese es el verdadero pulso "
             "democrático:\nla mitad del país que aún se queda por fuera.",
             fontsize=14.5, color=FG, va="top", linespacing=1.4)
    foot(fig, n, extra="Abstención femenina = 1 − (votantes / censo), por depto · "
         "proyección 2026.")
    save(fig, "11_abstencion.png")


# ===================================================== 12 CIERRE
def s11(n):
    fig = new_fig(); fig.patch.set_facecolor(VINO)
    fig.text(0.065, 0.935, "EN RESUMEN", fontsize=14, color=VINO, va="center",
             fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none", boxstyle="square,pad=0.45"))
    pts = [("Son decisivas.",
            "Son el 54% de los votos y participan\n6 puntos más que los hombres."),
           ("Se inclinan a la derecha.",
            "En promedio —pero no son un bloque:\njóvenes, voto en blanco y regiones varían."),
           ("La grieta también es de edad.",
            "El hombre joven, a la izquierda;\nla mujer mayor, a la derecha."),
           ("Y millones no votan.",
            "Casi 9 millones de mujeres\nse quedaron en casa.")]
    pos = [(0.065, 0.83), (0.53, 0.83), (0.065, 0.585), (0.53, 0.585)]
    for (xx, yy), (t, s) in zip(pos, pts):
        fig.text(xx, yy, t, fontsize=23, color=AMAR, va="top", **TITLE_F)
        fig.text(xx, yy - 0.064, s, fontsize=14, color="#f0e0e9", va="top",
                 linespacing=1.35)
    fig.text(0.065, 0.335, "Esto es análisis del electorado, no un respaldo a ningún "
             "candidato.", fontsize=17, color="#ffffff", va="top", fontweight="bold")
    fig.text(0.065, 0.205, "Mesa a mesa (efectos fijos de puesto) + encuesta · RNEC · "
             "DANE · AtlasIntel.", fontsize=14, color="#e9d7e1", va="top")
    fig.text(0.065, 0.105, "MUJERES POR LA DEMOCRACIA", fontsize=23, color=AMAR,
             ha="left", fontweight="bold")
    fig.text(0.935, 0.105, "ricardoruiz.co", fontsize=23, color="#ffffff", ha="right",
             fontweight="bold")
    fig.text(0.935, 0.953, n, fontsize=13, color="#caa9ba", ha="right",
             fontweight="bold")
    save(fig, "12_cierre.png")


SLIDES = {"portada": (s01, "1 / 12"), "peso": (s02, "2 / 12"),
          "giro": (s03, "3 / 12"), "metodo": (s04, "4 / 12"),
          "duelo": (s05, "5 / 12"), "generacional": (s06, "6 / 12"),
          "ciudades": (s07, "7 / 12"), "mapapart": (s08, "8 / 12"),
          "mapaabe": (s09, "9 / 12"), "mapacep": (s10b, "10 / 12"),
          "abstencion": (s_abst, "11 / 12"), "cierre": (s11, "12 / 12")}

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    todo = list(SLIDES) if args == ["all"] else args
    for k in todo:
        fn, num = SLIDES[k]
        fn(num)
