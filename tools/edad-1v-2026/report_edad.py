#!/usr/bin/env python3
"""Gráficas de publicación del análisis etario 1V-2026 vs 1V-2022.

Lee ei-final.csv (betas con IC y cotas) y recalcula los pesos de grupo
para la composición del electorado. Genera PNG light + dark (Twitter/web):

  g_perfil_2026   % del voto dentro de cada grupo etario · 2026 (con IC)
  g_perfil_2022   idem 2022
  g_herencia      Petro22 vs Cepeda26 · Fico22 vs Abelardo26
  g_electorado    composición etaria del electorado por candidato (2026)

Salida: Bases de datos/output_edad_1v/graficas/
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_ei import load_year, GNAMES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")
GDIR = os.path.join(OUT, "graficas")

THEMES = {
    "light": {"bg": "#f4f3ef", "fg": "#1a1a2e", "grid": "#dcdad4", "sub": "#6b6b76",
              "cands": {"Petro": "#51458F", "Fico": "#1866DF", "Rodolfo": "#c8702a",
                        "Cepeda": "#51458F", "Abelardo": "#1f2a8a",
                        "Paloma": "#1866DF", "Fajardo": "#c99a1c"}},
    "dark": {"bg": "#060810", "fg": "#f4f3ef", "grid": "#222636", "sub": "#9aa3b4",
             "cands": {"Petro": "#9f8fe8", "Fico": "#5aa2ff", "Rodolfo": "#fb923c",
                       "Cepeda": "#9f8fe8", "Abelardo": "#6e8bff",
                       "Paloma": "#5aa2ff", "Fajardo": "#f0c04a"}},
}
GRP_COLORS = {"light": ["#1866DF", "#51458F", "#9aa3b4", "#EEAA22", "#c8312c"],
              "dark": ["#5aa2ff", "#9f8fe8", "#9aa3b4", "#f0c04a", "#f87171"]}

FOOT = ("Inferencia ecológica por puesto de votación (IC 95% · bootstrap por municipios) · "
        "Fuentes: Registraduría (sufragantes por edad y sexo; preconteo 1V-2026) + DANE · ricardoruiz.co")

rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "DejaVu Sans", "sans-serif"]
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False


def style_ax(ax, t):
    ax.set_facecolor(t["bg"])
    for s in ("left", "bottom"):
        ax.spines[s].set_color(t["sub"])
    ax.tick_params(colors=t["fg"], labelsize=11)
    ax.grid(axis="y", color=t["grid"], linewidth=0.7)
    ax.set_axisbelow(True)


def footer(fig, t):
    fig.text(0.012, 0.012, FOOT, fontsize=7.8, color=t["sub"], ha="left")


def save(fig, name, theme):
    os.makedirs(GDIR, exist_ok=True)
    path = os.path.join(GDIR, f"{name}-{theme}.png")
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("  ->", os.path.relpath(path, os.path.join(HERE, "..", "..")))


def get_betas():
    df = pd.read_csv(os.path.join(OUT, "ei-final.csv"))
    return df


def group_weights(year):
    _, W, _, T = load_year(year)
    M = (W * T[:, None]).sum(axis=0)
    return M / M.sum()


# ------------------------------------------------------------- perfil por grupo
def g_perfil(df, year, cands, title, sub, theme):
    t = THEMES[theme]
    d = df[df.year == year]
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=180)
    fig.patch.set_facecolor(t["bg"])
    style_ax(ax, t)
    x = np.arange(len(GNAMES))
    for cand in cands:
        g = d[d.cand == cand].set_index("grupo").loc[GNAMES]
        c = t["cands"][cand]
        ax.plot(x, g.beta * 100, "-o", color=c, linewidth=3, markersize=7,
                label=cand, zorder=3)
        ax.fill_between(x, g.lo * 100, g.hi * 100, color=c, alpha=0.14, zorder=2)
        yv = g.beta.values * 100
        off = 2.4 if cand in ("Cepeda", "Petro", "Abelardo") else -3.4
        ax.annotate(f"{yv[-1]:.0f}%", (x[-1], yv[-1]), textcoords="offset points",
                    xytext=(10, 0), color=c, fontweight="bold", fontsize=12, va="center")
        ax.annotate(f"{yv[0]:.0f}%", (x[0], yv[0]), textcoords="offset points",
                    xytext=(-8, off + 4), color=c, fontweight="bold", fontsize=12,
                    ha="right", va="center")
    ax.set_xticks(x)
    ax.set_xticklabels([g + " años" if g != "61+" else "61+ años" for g in GNAMES])
    ax.set_xlim(-0.55, len(GNAMES) - 0.30)
    ax.set_ylim(0, 92)
    ax.set_ylabel("% del voto dentro del grupo etario", color=t["fg"], fontsize=11.5)
    ax.legend(loc="upper center", ncol=len(cands), frameon=False,
              fontsize=12.5, labelcolor=t["fg"])
    fig.suptitle(title, fontsize=19, fontweight="bold", color=t["fg"], x=0.012,
                 ha="left", y=0.985)
    ax.set_title(sub, fontsize=11.5, color=t["sub"], loc="left", pad=14)
    footer(fig, t)
    save(fig, f"g_perfil_{year}", theme)


# ------------------------------------------------------------- herencia
def g_herencia(df, theme):
    t = THEMES[theme]
    pairs = [("Petro", 2022, "Cepeda", 2026), ("Fico", 2022, "Abelardo", 2026)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.75), dpi=180, sharey=True)
    fig.patch.set_facecolor(t["bg"])
    x = np.arange(len(GNAMES))
    for ax, (c1, y1, c2, y2) in zip(axes, pairs):
        style_ax(ax, t)
        for cand, yr, ls in ((c1, y1, "--"), (c2, y2, "-")):
            g = df[(df.year == yr) & (df.cand == cand)].set_index("grupo").loc[GNAMES]
            c = t["cands"][cand]
            alpha = 0.55 if yr == 2022 else 1.0
            ax.plot(x, g.beta * 100, ls, marker="o", color=c, linewidth=2.8,
                    markersize=6, alpha=alpha, label=f"{cand} {yr}")
            if yr == 2026:
                ax.fill_between(x, g.lo * 100, g.hi * 100, color=c, alpha=0.12)
        ax.set_xticks(x)
        ax.set_xticklabels(GNAMES, fontsize=10)
        ax.set_ylim(0, 92)
        ax.legend(frameon=False, fontsize=11.5, labelcolor=t["fg"], loc="upper center")
    axes[0].set_ylabel("% del voto dentro del grupo etario", color=t["fg"], fontsize=11.5)
    fig.suptitle("La herencia generacional: 2022 → 2026", fontsize=19,
                 fontweight="bold", color=t["fg"], x=0.012, ha="left", y=0.985)
    axes[0].set_title("Cepeda calca el perfil joven de Petro", fontsize=11.5,
                      color=t["sub"], loc="left", pad=12)
    axes[1].set_title("Abelardo hereda y amplifica el perfil mayor de Fico",
                      fontsize=11.5, color=t["sub"], loc="left", pad=12)
    footer(fig, t)
    save(fig, "g_herencia", theme)


# ------------------------------------------------------------- electorado
def g_electorado(df, wsh26, theme):
    t = THEMES[theme]
    cands = ["Cepeda", "Abelardo", "Paloma", "Fajardo"]
    d = df[df.year == 2026]
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=180)
    fig.patch.set_facecolor(t["bg"])
    style_ax(ax, t)
    ax.grid(False)
    ypos = np.arange(len(cands))[::-1]
    for yi, cand in zip(ypos, cands):
        b = d[d.cand == cand].set_index("grupo").loc[GNAMES, "beta"].values
        gam = b * wsh26
        gam = gam / gam.sum() * 100
        left = 0.0
        for a, g in enumerate(GNAMES):
            ax.barh(yi, gam[a], left=left, height=0.62,
                    color=GRP_COLORS[theme][a], edgecolor=t["bg"], linewidth=1.2)
            if gam[a] >= 5.5:
                lum = 0 if theme == "light" and a in (2, 3) else 1
                ax.text(left + gam[a] / 2, yi, f"{gam[a]:.0f}",
                        ha="center", va="center", fontsize=11.5, fontweight="bold",
                        color="#1a1a2e" if lum == 0 else "#f7f7f4")
            left += gam[a]
    ax.set_yticks(ypos)
    ax.set_yticklabels(cands, fontsize=14, fontweight="bold", color=t["fg"])
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=GRP_COLORS[theme][a])
               for a in range(len(GNAMES))]
    ax.legend(handles, [g + " años" if g != "61+" else "61+ años" for g in GNAMES],
              loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=5,
              frameon=False, fontsize=11.5, labelcolor=t["fg"])
    fig.suptitle("¿De qué edades es el electorado de cada candidato?",
                 fontsize=19, fontweight="bold", color=t["fg"], x=0.012,
                 ha="left", y=0.985)
    ax.set_title("1V-2026 · cada barra suma 100% del voto del candidato",
                 fontsize=11.5, color=t["sub"], loc="left", pad=14)
    footer(fig, t)
    save(fig, "g_electorado", theme)


def main():
    df = get_betas()
    print("pesos de grupo (recalculando muestras EI)...")
    wsh26 = group_weights(2026)
    for theme in ("light", "dark"):
        g_perfil(df, 2026, ["Cepeda", "Abelardo", "Paloma", "Fajardo"],
                 "¿Quién ganó en cada generación? · 1ª vuelta 2026",
                 "% estimado del voto dentro de cada grupo etario · sombra = IC 95%",
                 theme)
        g_perfil(df, 2022, ["Petro", "Fico", "Rodolfo", "Fajardo"],
                 "El antecedente: 1ª vuelta 2022",
                 "% estimado del voto dentro de cada grupo etario · sombra = IC 95%",
                 theme)
        g_herencia(df, theme)
        g_electorado(df, wsh26, theme)
    print("listo.")


if __name__ == "__main__":
    main()
