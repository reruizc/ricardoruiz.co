#!/usr/bin/env python3
"""Carrusel 1V-2026 'cómo votó Colombia por edades' (Twitter-first).

9 piezas. Formato apaisado 1200x900 (4:3) para que se vean bien en el feed;
solo la 02 (flechas por depto) va vertical 1080x1350. Identidad de los
carruseles previos: títulos Arima 700, kicker Helvetica Neue bold en oxblood
#8a1e16, papel #f1eee4, tinta #1a1510 (rrss/instagram/carousel-conflicto.html
+ analisis-leyseca/carrusel.py).

Lee:
  blocs-depto.csv  (Pacto share + margen cara-a-cara Pacto vs mejor derecha)
  ei-final.csv     (EI nacional por edad, 5 bandas, con IC)
  ei-ciudades.csv  (EI head-to-head Cepeda/Abelardo por edad · 6 ciudades + nac)
  ei-deptos.csv    (EI head-to-head por depto, para mapas)
  geo/DEPARTAMENTOS2.json

Salida: Bases de datos/output_edad_1v/carrusel/NN_*.png
Uso: python3 report_carrusel.py [all|portada|shift|mapashift|perfil|herencia|
                                  electorado|ciudades|mapaedad|cierre]
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")
CDIR = os.path.join(OUT, "carrusel")
GEOF = os.path.join(HERE, "..", "..", "Bases de datos", "output_pacto_1v_2026",
                    "geo", "DEPARTAMENTOS2.json")

# ---- identidad de la casa (carruseles previos) ----
BG = "#f1eee4"       # paper
FG = "#1a1510"       # ink
SUB = "#6b6354"      # ink2
INK3 = "#9a9180"
OX = "#8a1e16"       # oxblood: kickers y acentos
GRID = "#dcd5c4"
RED = "#d1322e"      # Cepeda / izquierda (dato)
BLUE = "#1f47cc"     # Abelardo / derecha (dato)
PALOMA = "#6b8fe0"
AMBER = "#c98a1e"

GN5 = ["18-25", "26-35", "36-45", "46-60", "61+"]
GN3 = ["18-35", "36-60", "61+"]

for f in ("Arima-SemiBold.ttf", "Arima-Bold.ttf"):
    font_manager.fontManager.addfont(os.path.join(HERE, "fonts", f))
TITLE_F = {"family": "Arima", "weight": "bold"}
rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False

DPI = 100
SIZES = {"default": (1200, 900), "shift": (1080, 1350)}
IG = False     # modo Instagram: todo cuadrado 1080x1080 -> carrusel-ig/


def new_fig(slide="default"):
    w, h = (1080, 1080) if IG else SIZES.get(slide, SIZES["default"])
    fig = plt.figure(figsize=(w / DPI, h / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def head(fig, kicker, title, sub, tall=False, tsize=34):
    ky, ty, sy = (0.952, 0.922, 0.852) if tall else (0.935, 0.895, 0.80)
    if IG and tall:
        sy = 0.832          # en cuadrado el título de 2 líneas baja más
    fig.text(0.06, ky, kicker.upper(), fontsize=15, color=OX, fontweight="bold",
             ha="left")
    fig.text(0.06, ty, title, fontsize=tsize, color=FG, ha="left", va="top",
             linespacing=1.02, **TITLE_F)
    if sub:
        fig.text(0.06, sy, sub, fontsize=15.5, color=SUB, ha="left", va="top",
                 linespacing=1.3)


def foot(fig, n, extra=None):
    src = ("Estimación por puesto de votación (inferencia ecológica) · "
           "Fuentes: Registraduría + DANE")
    fig.text(0.06, 0.040, extra or src, fontsize=10.5, color=SUB, ha="left")
    fig.text(0.94, 0.040, "ricardoruiz.co", fontsize=12.5, color=FG,
             ha="right", fontweight="bold")
    if n:
        fig.text(0.94, 0.945, n, fontsize=13, color=INK3, ha="right",
                 fontweight="bold")


def save(fig, name):
    d = CDIR + ("-ig" if IG else "")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    fig.savefig(p, facecolor=BG)
    plt.close(fig)
    print("  ->", os.path.relpath(p, os.path.join(HERE, "..", "..")))


# ============================================================ 01 PORTADA
def slide_portada(n):
    fig = new_fig()
    fig.text(0.06, 0.91, "ELECCIONES · 1ª VUELTA · 2026", fontsize=16, color=OX,
             fontweight="bold")
    if IG:   # cuadrado: título a todo el ancho arriba, barras abajo
        fig.text(0.06, 0.84, "Colombia votó\npor edades", fontsize=58, color=FG,
                 va="top", linespacing=1.0, **TITLE_F)
        fig.text(0.06, 0.60, "Quién ganó en cada generación, ciudad por ciudad. "
                 "Una estimación\na partir de 23 millones de votos y la edad de "
                 "quienes sufragaron\nen cada puesto del país.",
                 fontsize=17, color=SUB, va="top", linespacing=1.4)
        ax = fig.add_axes([0.10, 0.085, 0.84, 0.40])
    else:
        fig.text(0.06, 0.83, "Colombia votó\npor edades", fontsize=64, color=FG,
                 va="top", linespacing=1.0, **TITLE_F)
        fig.text(0.06, 0.40, "Quién ganó en cada generación, ciudad por\nciudad. "
                 "Una estimación a partir de 23 millones\nde votos y la edad de "
                 "quienes sufragaron\nen cada puesto del país.",
                 fontsize=19, color=SUB, va="top", linespacing=1.4)
        ax = fig.add_axes([0.52, 0.13, 0.42, 0.64])
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    data = [("18-25", .62), ("26-35", .58), ("36-45", .50), ("46-60", .47), ("61+", .12)]
    for i, (g, cep) in enumerate(data):
        y = 0.86 - i * 0.19
        ax.text(0.0, y, g, fontsize=15, color=FG, ha="left", va="center",
                fontweight="bold")
        ax.barh(y, cep * 0.80, left=0.17, height=0.10, color=RED)
        ax.barh(y, (1 - cep) * 0.80, left=0.17 + cep * 0.80, height=0.10, color=BLUE)
    ax.text(0.17, 0.99, "Cepeda", color=RED, fontsize=14, fontweight="bold", ha="left")
    ax.text(0.97, 0.99, "Abelardo", color=BLUE, fontsize=14, fontweight="bold", ha="right")
    foot(fig, n)
    save(fig, "01_portada.png")


# ============================================================ 02 FLECHAS (vertical)
def slide_shift(n):
    df = pd.read_csv(os.path.join(OUT, "blocs-depto.csv")).sort_values(
        "dep_name", ascending=True).reset_index(drop=True)
    fig = new_fig("shift")
    head(fig, "El panorama · ¿quién va adelante?",
         "La izquierda sigue adelante en 18\nde 33 deptos, con menos ventaja",
         "Ventaja del candidato del Pacto (Petro 2022 → Cepeda 2026) sobre el\n"
         "candidato de derecha más votado. El punto es 2022; la flecha llega a 2026.",
         tall=True, tsize=30)
    ax = fig.add_axes([0.27, 0.075, 0.67, 0.70]); ax.set_facecolor(BG)
    nrow = len(df)
    # zonas: izquierda adelante (derecha del 0) · derecha adelante (izquierda)
    ax.axvspan(-65, 0, color=BLUE, alpha=0.045, zorder=0)
    ax.axvspan(0, 70, color=RED, alpha=0.045, zorder=0)
    ax.axvline(0, color=FG, lw=1.2, alpha=0.75)
    for i, r in df.iterrows():
        y = nrow - 1 - i
        a, b = r["h2h22"], r["h2h26"]
        col = RED if b >= a else BLUE
        ax.annotate("", xy=(b, y), xytext=(a, y),
                    arrowprops=dict(arrowstyle="-|>,head_width=0.30,head_length=0.55",
                                    color=col, lw=2.2))
        ax.plot(a, y, "o", ms=5, color=col, alpha=0.45, zorder=2)
    ax.text(-32, nrow + 1.1, "← va adelante la derecha", fontsize=12.5, color=BLUE,
            ha="center", fontweight="bold")
    ax.text(35, nrow + 1.1, "va adelante la izquierda →", fontsize=12.5, color=RED,
            ha="center", fontweight="bold")
    ax.set_yticks([nrow - 1 - i for i in range(nrow)])
    ax.set_yticklabels(df["dep_name"], fontsize=10.2, color=FG)
    ax.set_ylim(-1.4, nrow + 2.0); ax.set_xlim(-65, 70)
    ax.set_xticks([-50, -25, 0, 25, 50])
    ax.set_xticklabels(["-50 pp", "-25", "0", "+25", "+50 pp"], fontsize=10.5, color=SUB)
    ax.tick_params(length=0)
    for s in ("left", "top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    foot(fig, n, extra="Flecha roja = la izquierda ganó terreno · azul = lo perdió. "
         "Voto por puesto · Registraduría (escrutinio 2022, preconteo 2026).")
    save(fig, "02_shift_deptos.png")


# ============================================================ geo helper
_GEO = None


def geo():
    global _GEO
    if _GEO is None:
        import geopandas as gpd
        g = gpd.read_file(GEOF)
        g["key"] = g["name"]
        _GEO = g
    return _GEO


def draw_map(ax, valby, cmap_fn, default="#e3ddcd"):
    import matplotlib.colors as mc
    g = geo().copy()
    g["val"] = g["key"].map(valby)
    colors = [mc.to_hex(cmap_fn(v)) if pd.notna(v) else default for v in g["val"]]
    g.plot(ax=ax, color=colors, edgecolor=BG, linewidth=0.6, aspect=None)
    ax.set_xlim(-79.3, -66.8); ax.set_ylim(-4.4, 13.7)
    ax.set_aspect(1 / np.cos(4.6 * np.pi / 180))
    ax.axis("off")


def _mix(c1, c2, t):
    import matplotlib.colors as mc
    a = np.array(mc.to_rgb(c1)); b = np.array(mc.to_rgb(c2))
    return tuple(a + (b - a) * t)


# ============================================================ 03 MAPA SHIFT
def slide_mapa_shift(n):
    df = pd.read_csv(os.path.join(OUT, "blocs-depto.csv"))
    val = dict(zip(df["geoname"], df["pacto_shift"]))

    def cm(v):
        if v >= 0:
            return _mix("#f0e6e2", RED, min(v / 12, 1))
        return _mix("#e4e6f0", BLUE, min(-v / 6, 1))
    fig = new_fig()
    fig.text(0.06, 0.935, "EL PANORAMA · EN VOTOS", fontsize=15, color=OX,
             fontweight="bold")
    fig.text(0.06, 0.885, "Dónde creció y dónde\ncayó la izquierda", fontsize=37,
             color=FG, ha="left", va="top", linespacing=1.04, **TITLE_F)
    fig.text(0.06, 0.70, "Cambio en el voto del Pacto\n(Petro 2022 → Cepeda 2026),\n"
             "en puntos, por departamento.", fontsize=17.5, color=SUB, va="top",
             linespacing=1.4)
    fig.text(0.06, 0.52, "Creció en 27 de 33 departamentos\n—Orinoquía, Amazonía, "
             "Santander—\npero cayó donde más votos hay:\nBogotá (−5,4) y "
             "Atlántico (−2,7).", fontsize=16.5, color=FG, va="top", linespacing=1.45)
    # leyenda gradiente
    lax = fig.add_axes([0.06, 0.255, 0.30, 0.030]); lax.axis("off")
    for i in range(60):
        t = i / 59; v = (t - 0.5) * 2
        c = _mix("#e4e6f0", BLUE, min(abs(v), 1)) if v < 0 else _mix("#f0e6e2", RED, min(v, 1))
        lax.barh(0.5, 1 / 60, left=i / 60, height=1, color=c)
    lax.set_xlim(0, 1)
    fig.text(0.06, 0.225, "cayó", fontsize=13, color=BLUE, ha="left", fontweight="bold")
    fig.text(0.36, 0.225, "creció", fontsize=13, color=RED, ha="right", fontweight="bold")
    # mapa a la derecha, sin solaparse
    ax = fig.add_axes([0.43, 0.075, 0.55, 0.84])
    draw_map(ax, val, cm)
    foot(fig, n, extra="Voto por puesto · Registraduría (escrutinio 2022, "
         "preconteo 2026). Pacto = Petro / Cepeda.")
    save(fig, "03_mapa_shift.png")


# ============================================================ 04 PERFIL 2026
def slide_perfil(n):
    df = pd.read_csv(os.path.join(OUT, "ei-final.csv"))
    d = df[df.year == 2026]
    fig = new_fig()
    head(fig, "Quién ganó cada generación",
         "Cepeda barrió entre los jóvenes;\nAbelardo, entre los mayores",
         "% estimado del voto en cada grupo de edad · 1ª vuelta 2026.\n"
         "La sombra es el intervalo de confianza (95%).", tsize=31)
    ax = fig.add_axes([0.085, 0.135, 0.80, 0.56]); ax.set_facecolor(BG)
    x = np.arange(len(GN5))
    series = [("Cepeda", RED), ("Abelardo", BLUE), ("Paloma", PALOMA),
              ("Fajardo", AMBER)]
    ends = []
    for cand, c in series:
        g = d[d.cand == cand].set_index("grupo").loc[GN5]
        ax.plot(x, g.beta.values * 100, "-o", color=c, lw=3.4, ms=8.5, zorder=3)
        ax.fill_between(x, g.lo * 100, g.hi * 100, color=c, alpha=0.13, zorder=2)
        yv = g.beta.values * 100
        ax.annotate(f"{yv[0]:.0f}", (0, yv[0]), textcoords="offset points",
                    xytext=(-13, 0), color=c, fontsize=14, fontweight="bold",
                    va="center", ha="right")
        ends.append([yv[-1], cand, c])
    # etiquetas directas al final (dodge vertical para que no se encimen)
    ends.sort(key=lambda e: -e[0])
    ys = [e[0] for e in ends]
    for i in range(1, len(ys)):
        if ys[i - 1] - ys[i] < 7:
            ys[i] = ys[i - 1] - 7
    ys[-1] = max(ys[-1], 3.0)          # que no pise las etiquetas del eje x
    for i in range(len(ys) - 2, -1, -1):
        ys[i] = max(ys[i], ys[i + 1] + 7)
    for (v, cand, c), y in zip(ends, ys):
        ax.annotate(f"{cand} {v:.0f}%", (len(GN5) - 1, v),
                    xytext=(len(GN5) - 1 + 0.13, y), textcoords="data",
                    color=c, fontsize=15, fontweight="bold", va="center")
    ax.set_xticks(x); ax.set_xticklabels([g + " años" for g in GN5],
                                         fontsize=13.5, color=FG)
    ax.set_xlim(-0.55, len(GN5) + 0.75); ax.set_ylim(0, 90)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.set_yticklabels(["0", "20", "40", "60", "80%"], color=SUB, fontsize=12)
    ax.tick_params(length=0); ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    foot(fig, n)
    save(fig, "04_perfil_2026.png")


# ============================================================ 05 HERENCIA
def slide_herencia(n):
    df = pd.read_csv(os.path.join(OUT, "ei-final.csv"))
    fig = new_fig()
    head(fig, "La herencia · 2022 → 2026",
         "Cada bloque heredó la edad de su antecesor",
         "Punteado: 1ª vuelta 2022 (Petro, Fico). Línea llena: 2026 (Cepeda, Abelardo). "
         "% del voto por grupo de edad.", tsize=30)
    pairs = [("Petro", "Cepeda", RED, "Izquierda: Petro → Cepeda"),
             ("Fico", "Abelardo", BLUE, "Derecha: Fico → Abelardo")]
    x = np.arange(len(GN5))
    for k, (c22, c26, col, t) in enumerate(pairs):
        ax = fig.add_axes([0.085 + k * 0.47, 0.135, 0.39, 0.50])
        ax.set_facecolor(BG)
        for cand, yr, ls, al in ((c22, 2022, (0, (3, 2)), 0.45), (c26, 2026, "solid", 1.0)):
            g = df[(df.year == yr) & (df.cand == cand)].set_index("grupo").loc[GN5]
            ax.plot(x, g.beta.values * 100, marker="o", linestyle=ls, color=col,
                    lw=3, ms=6.5, alpha=al, label=f"{cand} {yr}")
        ax.set_xticks(x); ax.set_xticklabels(GN5, fontsize=11, color=FG)
        ax.set_ylim(0, 90); ax.set_xlim(-0.4, len(GN5) - 0.6)
        ax.set_yticks([0, 40, 80])
        ax.set_yticklabels(["0", "40", "80%"], color=SUB, fontsize=11)
        ax.tick_params(length=0); ax.grid(axis="y", color=GRID, lw=0.7)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.set_title(t, fontsize=16, color=FG, loc="left", pad=10, **TITLE_F)
        ax.legend(frameon=False, fontsize=12.5, labelcolor=FG, loc="upper left"
                  if col == BLUE else "upper right")
    foot(fig, n)
    save(fig, "05_herencia.png")


# ============================================================ 06 ELECTORADO
def slide_electorado(n):
    df = pd.read_csv(os.path.join(OUT, "ei-final.csv"))
    sys.path.insert(0, HERE)
    from fit_ei import load_year
    _, Wm, _, T = load_year(2026)
    wsh = (Wm * T[:, None]).sum(0) / T.sum()
    cands = ["Cepeda", "Abelardo", "Paloma", "Fajardo"]
    gcol = [RED, "#c9682e", "#c9b89a", "#5b78d6", BLUE]
    fig = new_fig()
    head(fig, "El retrato de cada voto",
         "El electorado de Abelardo es mayor;\nel de Cepeda, joven",
         "De cada 100 votos de cada candidato, cuántos puso cada grupo de edad.",
         tsize=31)
    ax = fig.add_axes([0.16, 0.165, 0.78, 0.52]); ax.set_facecolor(BG)
    ypos = np.arange(len(cands))[::-1]
    d26 = df[df.year == 2026]
    for yi, cand in zip(ypos, cands):
        b = d26[d26.cand == cand].set_index("grupo").loc[GN5, "beta"].values
        gam = b * wsh; gam = gam / gam.sum() * 100
        left = 0
        for a in range(5):
            ax.barh(yi, gam[a], left=left, height=0.66, color=gcol[a],
                    edgecolor=BG, linewidth=1.6)
            if gam[a] >= 6:
                ax.text(left + gam[a] / 2, yi, f"{gam[a]:.0f}", ha="center",
                        va="center", fontsize=13.5, fontweight="bold",
                        color=FG if a == 2 else "white")
            left += gam[a]
        ax.text(-1.6, yi, cand, ha="right", va="center", fontsize=17,
                fontweight="bold", color=FG)
    ax.set_xlim(0, 100); ax.set_ylim(-0.6, len(cands) - 0.4); ax.axis("off")
    hs = [plt.Rectangle((0, 0), 1, 1, color=gcol[a]) for a in range(5)]
    ax.legend(hs, [g + " años" for g in GN5], loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=5, frameon=False, fontsize=12.5,
              labelcolor=FG, handlelength=1.2, columnspacing=1.5)
    foot(fig, n)
    save(fig, "06_electorado.png")


# ============================================================ 07 CIUDADES (WaPo)
def slide_ciudades(n):
    df = pd.read_csv(os.path.join(OUT, "ei-ciudades.csv"))
    units = ["Nacional", "Bogotá", "Medellín", "Cali", "Barranquilla",
             "Cartagena", "Bucaramanga"]
    fig = new_fig()
    head(fig, "Las ciudades",
         "En todas, el voto se voltea con la edad",
         "Cómo se repartió cada generación entre los dos punteros.\n"
         "Izquierda roja = Cepeda · derecha azul = Abelardo.", tsize=31)
    lab = {"18-35": "18-35 años", "36-60": "36-60 años", "61+": "61+ años"}
    RED_P, BLUE_P = _mix(RED, BG, 0.78), _mix(BLUE, BG, 0.78)   # tintes pálidos
    ax = fig.add_axes([0.155, 0.115, 0.80, 0.60]); ax.set_facecolor(BG)
    ncols, nrows = len(GN3), len(units)
    ax.set_xlim(-0.04, ncols); ax.set_ylim(-0.75, nrows - 0.25)
    ax.axis("off"); ax.invert_yaxis()
    BW, BH = 0.88, 0.52        # ancho de caja (100%) y alto
    for j, g in enumerate(GN3):
        ax.text(j + BW / 2, -0.68, lab[g], fontsize=14.5, color=FG, ha="center",
                fontweight="bold")
    for i, unit in enumerate(units):
        nac = unit == "Nacional"
        ax.text(-0.10, i, unit, fontsize=13.5 if nac else 12.5, color=FG,
                ha="right", va="center", fontweight="bold" if nac else "normal")
        for j, g in enumerate(GN3):
            ce = df[(df.unit == unit) & (df.grupo == g)]["cepeda"].iloc[0]
            ab = 1 - ce
            x0 = j
            cw = ce * BW
            win_c = ce >= ab
            if nac:   # fila nacional saturada (como la fila U.S. de WaPo)
                fc_c, fc_a = RED, BLUE
                tc_c, tc_a = "white", "white"
            else:
                fc_c = RED if False else RED_P
                fc_a = BLUE_P
                tc_c, tc_a = OX, "#16235e"
            ax.barh(i, cw, left=x0, height=BH, color=fc_c, zorder=2)
            ax.barh(i, BW - cw, left=x0 + cw, height=BH, color=fc_a, zorder=2)
            if not nac:   # borde saturado al lado ganador
                from matplotlib.patches import Rectangle
                if win_c:
                    ax.add_patch(Rectangle((x0, i - BH / 2), cw, BH, fill=False,
                                           edgecolor=RED, lw=2.2, zorder=3))
                else:
                    ax.add_patch(Rectangle((x0 + cw, i - BH / 2), BW - cw, BH,
                                           fill=False, edgecolor=BLUE, lw=2.2, zorder=3))
            # números ADENTRO de cada lado (si el lado es muy angosto, afuera).
            # Bajo 5% se reporta "<5": a ese nivel la EI no fija el valor exacto.
            def fmt(v):
                if v < 0.05:
                    return "<5"
                if v > 0.95:
                    return ">95"
                return f"{v*100:.0f}%"
            cv, av = fmt(ce), fmt(ab)
            if ce >= 0.17:
                ax.text(x0 + 0.025, i, cv, ha="left", va="center", fontsize=11.5,
                        color=tc_c, fontweight="bold" if (win_c or nac) else "normal")
            else:
                ax.text(x0 - 0.012, i, cv, ha="right", va="center", fontsize=10.5,
                        color=OX)
            if ab >= 0.17:
                ax.text(x0 + BW - 0.025, i, av, ha="right", va="center", fontsize=11.5,
                        color=tc_a, fontweight="bold" if ((not win_c) or nac) else "normal")
            else:
                ax.text(x0 + BW + 0.012, i, av, ha="left", va="center", fontsize=10.5,
                        color="#16235e")
    foot(fig, n, extra="Duelo Cepeda–Abelardo (suma 100) por localidad/comuna · "
         "el 61+ de Cepeda es el dato menos preciso.")
    save(fig, "07_ciudades_edad.png")


# ============================================================ 08 MAPA EDAD
def slide_mapa_edad(n):
    df = pd.read_csv(os.path.join(OUT, "ei-deptos.csv"))
    df = df[df.robust >= 1]    # robust=2: deptos pequeños, muestra ampliada
    yng = dict(zip(df[df.grupo == "18-35"]["geoname"], df[df.grupo == "18-35"]["cepeda"]))
    old = dict(zip(df[df.grupo == "61+"]["geoname"], df[df.grupo == "61+"]["cepeda"]))

    def cm(v):
        m = (v - 0.5) * 2
        return _mix("#eceef4", BLUE, min(-m, 1)) if m < 0 else _mix("#f4ebe8", RED, min(m, 1))
    fig = new_fig()
    head(fig, "La geografía de la edad",
         "El mismo país, dos elecciones según la edad",
         "Quién gana el duelo Cepeda–Abelardo en cada departamento, por grupo.",
         tsize=30)
    a1 = fig.add_axes([0.045, 0.115, 0.42, 0.56]); draw_map(a1, yng, cm)
    a2 = fig.add_axes([0.535, 0.115, 0.42, 0.56]); draw_map(a2, old, cm)
    fig.text(0.255, 0.685, "Si solo votaran los jóvenes (18-35)", fontsize=16,
             color=FG, ha="center", fontweight="bold")
    fig.text(0.745, 0.685, "Si solo votaran los mayores (61+)", fontsize=16,
             color=FG, ha="center", fontweight="bold")
    fig.text(0.385, 0.058, "■", color=RED, fontsize=15, ha="left")
    fig.text(0.405, 0.058, "gana Cepeda", color=FG, fontsize=12.5, ha="left")
    fig.text(0.535, 0.058, "■", color=BLUE, fontsize=15, ha="left")
    fig.text(0.555, 0.058, "gana Abelardo", color=FG, fontsize=12.5, ha="left")
    foot(fig, n, extra="Duelo Cepeda–Abelardo por puesto. En la Amazonía-Orinoquía "
         "y San Andrés (pocos puestos) el dato es menos preciso.")
    save(fig, "08_mapa_edad.png")


# ============================================================ 09 CIERRE
def slide_cierre(n):
    fig = new_fig()
    fig.text(0.06, 0.92, "EN RESUMEN", fontsize=16, color=OX, fontweight="bold")
    pts = [
        ("Un choque de generaciones.",
         "Cepeda ganó 6 de cada 10 votos jóvenes;\nAbelardo, 8 de cada 10 mayores."),
        ("La edad se heredó de 2022.",
         "Cepeda calcó el perfil joven de Petro;\nAbelardo, el perfil mayor de Fico."),
        ("Pasa en todas las ciudades.",
         "El voto se voltea de joven a mayor en\nBogotá, Cali, Medellín, la Costa…"),
        ("La izquierda creció; la derecha se unió.",
         "Cepeda superó a Petro en 27 de 33 deptos,\npero la ventaja se le encogió."),
    ]
    pos = [(0.06, 0.80), (0.53, 0.80), (0.06, 0.52), (0.53, 0.52)]
    for (xx, yy), (t, s) in zip(pos, pts):
        fig.text(xx, yy, t, fontsize=21, color=FG, va="top", **TITLE_F)
        fig.text(xx, yy - 0.062, s, fontsize=14.5, color=SUB, va="top",
                 linespacing=1.35)
    fig.text(0.06, 0.22, "Metodología y gráficos en alta en", fontsize=15, color=SUB)
    fig.text(0.06, 0.175, "ricardoruiz.co", fontsize=34, color=FG, va="top", **TITLE_F)
    foot(fig, n, extra="Inferencia ecológica por puesto · sufragantes por edad "
         "(Registraduría) + proyección DANE · 1ª vuelta 2026.")
    save(fig, "09_cierre.png")


SLIDES = {
    "portada": (slide_portada, "1 / 9"), "shift": (slide_shift, "2 / 9"),
    "mapashift": (slide_mapa_shift, "3 / 9"), "perfil": (slide_perfil, "4 / 9"),
    "herencia": (slide_herencia, "5 / 9"), "electorado": (slide_electorado, "6 / 9"),
    "ciudades": (slide_ciudades, "7 / 9"), "mapaedad": (slide_mapa_edad, "8 / 9"),
    "cierre": (slide_cierre, "9 / 9"),
}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if "ig" in args:
        IG = True
        args.remove("ig")
    args = args or ["all"]
    todo = list(SLIDES) if args == ["all"] else args
    for k in todo:
        fn, num = SLIDES[k]
        fn(num)
