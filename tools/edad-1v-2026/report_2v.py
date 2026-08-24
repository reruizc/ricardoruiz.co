#!/usr/bin/env python3
"""Figura comparativa del perfil etario de 2ª vuelta.
Lee ei-2v-final.csv y dibuja las 3 curvas (2V-2026, 1V-2026 cara a cara,
2V-2022) del share de la izquierda por grupo de edad. Light + dark."""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")
GDIR = os.path.join(OUT, "graficas")
os.makedirs(GDIR, exist_ok=True)

for fp in ("Arima-Bold.ttf", "Arima-SemiBold.ttf"):
    p = os.path.join(HERE, "fonts", fp)
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "DejaVu Sans", "sans-serif"]
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False

GN = ["18-25", "26-35", "36-45", "46-60", "61+"]
THEMES = {
    "light": dict(bg="#f1eee4", fg="#1a1510", grid="#d9d4c6", sub="#6b6258",
                  ox="#8a1e16"),
    "dark": dict(bg="#060810", fg="#f4f3ef", grid="#222636", sub="#9aa3b4",
                 ox="#e0593f"),
}
SERIES = [
    ("2V-2026", "Cepeda vs Abelardo", "#c0392b", "-", "o"),
    ("1V-2026 (cara a cara)", "Cepeda vs Abelardo (en 1ª vuelta)", "#cf7d2a", "--", "s"),
    ("2V-2022", "Petro vs Rodolfo", "#7a5cb0", "-.", "^"),
]


def draw(theme):
    t = THEMES[theme]
    df = pd.read_csv(os.path.join(OUT, "ei-2v-final.csv"))
    fig, ax = plt.subplots(figsize=(9.6, 6.4), dpi=150)
    fig.patch.set_facecolor(t["bg"])
    ax.set_facecolor(t["bg"])
    x = np.arange(5)
    for contest, lab, col, ls, mk in SERIES:
        d = df[df["contest"] == contest].set_index("grupo").loc[GN]
        y = d["izq_share"].values * 100
        lo = d["lo"].values * 100
        hi = d["hi"].values * 100
        ax.fill_between(x, lo, hi, color=col, alpha=0.10, linewidth=0)
        ax.plot(x, y, ls, color=col, lw=2.6, marker=mk, ms=8,
                markeredgecolor=t["bg"], markeredgewidth=1.2, label=lab, zorder=5)
    ax.axhline(50, color=t["sub"], lw=1, ls=":", zorder=1)
    ax.text(4.05, 51, "50% = empate", color=t["sub"], fontsize=9, va="bottom", ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(GN, fontsize=12, color=t["fg"])
    ax.set_yticks(range(0, 101, 20))
    ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)], fontsize=11, color=t["fg"])
    ax.set_ylim(-3, 103)
    ax.tick_params(colors=t["fg"])
    for s in ("left", "bottom"):
        ax.spines[s].set_color(t["sub"])
    ax.grid(axis="y", color=t["grid"], lw=0.7)
    ax.set_axisbelow(True)
    ax.set_ylabel("Voto que va a la IZQUIERDA\n(entre los dos finalistas)",
                  fontsize=11.5, color=t["fg"])
    ax.set_xlabel("Grupo de edad de los votantes", fontsize=11.5, color=t["sub"])

    fig.text(0.04, 0.965, "EL ABISMO GENERACIONAL DE LA SEGUNDA VUELTA",
             fontsize=17, fontfamily="Arima", fontweight="bold", color=t["fg"])
    fig.text(0.04, 0.925,
             "Los mayores de 60 votan a la derecha 9 de cada 10 — igual en 2022 que en 2026",
             fontsize=11.5, color=t["sub"])
    leg = ax.legend(loc="lower left", frameon=False, fontsize=10.5,
                    labelcolor=t["fg"])
    fig.text(0.04, 0.02,
             "Inferencia ecológica por puesto (IC 95%, bootstrap por municipios). "
             "Fuentes: Registraduría (edad de votantes; escrutinio 2022, preconteo 2026) + DANE · ricardoruiz.co",
             fontsize=7.6, color=t["sub"])
    fig.subplots_adjust(left=0.11, right=0.97, top=0.87, bottom=0.12)
    out = os.path.join(GDIR, f"g_2v_brecha_{theme}.png")
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print("->", out)


def draw_regional(theme):
    """Dumbbell: por región, share Cepeda entre jóvenes (18-25) vs mayores (61+),
    2V-2026, ordenado por brecha."""
    t = THEMES[theme]
    df = pd.read_csv(os.path.join(OUT, "ei-2v-regional.csv"))
    df = df[df["contest"] == "2V-2026"]
    young = (df[df["grupo"] == "18-25"].set_index("region")["izq_share"] * 100)
    old = (df[df["grupo"] == "61+"].set_index("region")["izq_share"] * 100)
    glob = (df.groupby("region")["global_izq"].first() * 100)
    order = (young - old).sort_values().index.tolist()
    y = np.arange(len(order))
    cep, abe = "#c0392b", "#1f47cc"
    fig, ax = plt.subplots(figsize=(9.6, 6.2), dpi=150)
    fig.patch.set_facecolor(t["bg"])
    ax.set_facecolor(t["bg"])
    for i, r in enumerate(order):
        yv, ov = young[r], old[r]
        ax.plot([ov, yv], [i, i], color=t["sub"], lw=2.2, zorder=1)
        ax.scatter([ov], [i], color="#9aa3b4", s=130, zorder=3, edgecolor=t["bg"], lw=1.3)
        ax.scatter([yv], [i], color=cep, s=130, zorder=3, edgecolor=t["bg"], lw=1.3)
        ax.text(yv + 2.5, i, f"{yv:.0f}", va="center", ha="left", fontsize=10,
                color=cep, fontweight="bold")
        ax.text(ov - 2.5, i, f"{ov:.0f}", va="center", ha="right", fontsize=10,
                color=t["sub"], fontweight="bold")
    ax.axvline(50, color=t["sub"], lw=1, ls=":", zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels([r.replace(" (Tolima-Huila-Amazonía)", "\n(Tolima-Huila)")
                        for r in order], fontsize=11, color=t["fg"])
    ax.set_xlim(-8, 108)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xticklabels([f"{v}%" for v in range(0, 101, 25)], fontsize=10, color=t["fg"])
    ax.tick_params(colors=t["fg"])
    for s in ("left", "bottom"):
        ax.spines[s].set_color(t["sub"])
    ax.grid(axis="x", color=t["grid"], lw=0.6)
    ax.set_axisbelow(True)
    fig.text(0.04, 0.965, "EL MISMO ACANTILADO, PENDIENTES DISTINTAS",
             fontsize=17, fontfamily="Arima", fontweight="bold", color=t["fg"])
    fig.text(0.04, 0.925,
             "Voto a Cepeda en 2ª vuelta entre jóvenes (18-25, rojo) y mayores de 60 (gris), por región",
             fontsize=11, color=t["sub"])
    fig.text(0.96, 0.925, "● jóvenes   ● mayores 60", fontsize=10,
             color=t["sub"], ha="right")
    fig.text(0.04, 0.02,
             "Inferencia ecológica por puesto. Fuentes: Registraduría (edad de votantes; preconteo 2V-2026) + DANE · ricardoruiz.co",
             fontsize=7.6, color=t["sub"])
    fig.subplots_adjust(left=0.205, right=0.97, top=0.87, bottom=0.10)
    out = os.path.join(GDIR, f"g_2v_regional_{theme}.png")
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print("->", out)


if __name__ == "__main__":
    draw("light")
    draw("dark")
    draw_regional("light")
    draw_regional("dark")
