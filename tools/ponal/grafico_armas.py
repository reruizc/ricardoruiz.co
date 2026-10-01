#!/usr/bin/env python3
"""grafico_armas.py — armas de fuego incautadas por año (DIJIN, 2iz5-9bbz)
contra el % de homicidios (MinDefensa, m8fd-ahd9) y de hurtos (SIEDCO) cometidos
con arma de fuego.  → rrss/twitter/armas-incautadas/armas-vs-fuego.png (+ .json)
Requiere: Bases de datos/output_ponal/arma_anio.json (tools/ponal/arma_anio.py)
          y la caché de build_mindefensa.py o consulta directa a Socrata.
"""
import json, urllib.request, urllib.parse
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

R = Path(__file__).resolve().parents[2]
OUT = R / "rrss" / "twitter" / "armas-incautadas"
OUT.mkdir(parents=True, exist_ok=True)
for p in ["tools/edad-1v-2026/fonts/Arima-Bold.ttf", "tools/pacto-1v-2026/fonts/Inter-Regular.ttf",
          "tools/pacto-1v-2026/fonts/Inter-Bold.ttf"]:
    fm.fontManager.addfont(str(R / p))
plt.rcParams["font.family"] = "Inter"
PAPER, INK, OX, AMB, AZ, GR = "#f1eee4", "#1a1510", "#8a1e16", "#cf7d2a", "#1f47cc", "#d4ccb8"

def q(ds, params):
    url = f"https://www.datos.gov.co/resource/{ds}.json?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ricardoruiz.co"}), timeout=300) as r:
        return json.loads(r.read())

arm = {int(r["a"]): int(float(r["s"])) for r in q("2iz5-9bbz", {"$select": "substring(fecha_hecho,7,4) as a,sum(cantidad::number) as s", "$group": "a"}) if r.get("a")}
t, f = defaultdict(int), defaultdict(int)
for r in q("m8fd-ahd9", {"$select": "date_extract_y(fecha_hecho) as a,arma_medio,sum(cantidad) as n", "$group": "a,arma_medio", "$limit": 5000}):
    a, n = int(r["a"]), int(r["n"])
    t[a] += n
    if "FUEGO" in r.get("arma_medio", "").upper():
        f[a] += n
d = json.loads((R / "Bases de datos/output_ponal/arma_anio.json").read_text())
H = ["hurto_personas", "hurto_comercios", "hurto_residencias", "hurto_motos", "hurto_autos"]
A = list(range(2010, 2027)); AH = list(range(2015, 2027))
hom = {a: 100 * f[a] / t[a] for a in A}
hp = {a: 100 * d["hurto_personas"][str(a)].get("fuego", 0) / sum(d["hurto_personas"][str(a)].values()) for a in AH}
ht = {a: 100 * sum(d[k][str(a)].get("fuego", 0) for k in H) / sum(sum(d[k][str(a)].values()) for k in H) for a in AH}
(OUT / "armas-vs-fuego.json").write_text(json.dumps({"armas_incautadas": arm, "homicidio_pct_fuego": hom,
    "hurto_personas_pct_fuego": hp, "hurtos_5_tipos_pct_fuego": ht,
    "notas": "armas 2026 = ene-jul (DIJIN); % 2026 = ene-ago. Hurtos: personas+comercio+residencias+motos+autos (sin celulares, que se superponen con personas)."}, indent=1))

fig = plt.figure(figsize=(12, 9), dpi=150, facecolor=PAPER)
ax = fig.add_axes([0.08, 0.18, 0.84, 0.56], facecolor=PAPER)
bars = ax.bar(A, [arm[a] for a in A], color=[GR if a < 2026 else "none" for a in A], width=0.7,
              edgecolor=["#a89f8a"] * len(A), hatch=["" if a < 2026 else "////" for a in A], linewidth=1, zorder=2)
for a in A:
    ax.text(a, 1200, f"{arm[a]/1000:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=9.5, color="#4a4438", fontweight="bold")
ax.set_ylim(0, 50000); ax.set_yticks([])
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#bdb6a5")
ax.set_xticks(A); ax.set_xticklabels([str(a) if a < 2026 else "2026*" for a in A], fontsize=10, color=INK)
ax.tick_params(axis="x", length=0)

ax2 = ax.twinx()
ax2.plot(A, [hom[a] for a in A], color=OX, lw=3, marker="o", ms=6, zorder=5)
ax2.plot(AH, [hp[a] for a in AH], color=AZ, lw=2.6, marker="o", ms=5, zorder=5)
ax2.plot(AH, [ht[a] for a in AH], color=AZ, lw=1.6, ls=(0, (4, 3)), zorder=4)
ax2.set_ylim(0, 100); ax2.set_yticks([0, 20, 40, 60, 80]); ax2.set_yticklabels(["0%", "20%", "40%", "60%", "80%"], fontsize=10, color=INK)
for s in ("top", "left", "bottom"):
    ax2.spines[s].set_visible(False)
ax2.spines["right"].set_color("#bdb6a5"); ax2.grid(axis="y", color="#d9d3c4", lw=0.7, zorder=0); ax2.set_axisbelow(True)
def lab(x, y, s, c, dy=0, ha="left"):
    ax2.annotate(s, (x, y), xytext=(6 if ha == "left" else -6, dy), textcoords="offset points", fontsize=10.5, color=c, fontweight="bold", va="center", ha=ha)
lab(2010, hom[2010], f"{hom[2010]:.0f}%".replace(".", ","), OX, 12, "right")
lab(2016, hom[2016], f"{hom[2016]:.0f}%", OX, -14)
lab(2026, hom[2026], f"{hom[2026]:.0f}%", OX, 0)
lab(2026, hp[2026], f"{hp[2026]:.0f}%", AZ, 0)
lab(2015, hp[2015], f"{hp[2015]:.0f}%", AZ, 12, "right")
lab(2021, hp[2021], f"{hp[2021]:.0f}%", AZ, 12)
ax2.text(2010.6, 89, "Homicidios con arma de fuego", color=OX, fontsize=11.5, fontweight="bold")
ax2.text(2015.1, 33, "Hurto a personas con arma de fuego", color=AZ, fontsize=11.5, fontweight="bold", bbox=dict(fc=PAPER, ec="none", pad=2))
ax2.text(2015.1, 28.5, "- - -  cinco tipos de hurto juntos", color=AZ, fontsize=9.5, bbox=dict(fc=PAPER, ec="none", pad=2))
ax.text(2010, 48500, "Barras: armas de fuego incautadas en el año, en miles (cifra al pie de cada barra)", color="#6b6456", fontsize=10.5, va="top")

fig.text(0.08, 0.935, "Se incautan menos armas que en 2010,", fontfamily="Arima", fontsize=27, color=INK, fontweight="bold")
fig.text(0.08, 0.885, "y la bala pesa más en el homicidio", fontfamily="Arima", fontsize=27, color=INK, fontweight="bold")
fig.text(0.08, 0.795, "Armas de fuego incautadas por año (barras) y porcentaje de homicidios y hurtos cometidos\ncon arma de fuego (líneas). Colombia, 2010-2026.",
         fontsize=12, color="#4a4438", linespacing=1.45)
fig.text(0.08, 0.045, "* 2026: armas de enero a julio (barra rayada, año incompleto); porcentajes de enero a agosto.\n"
         "Las dos series no prueban que una cause la otra: entre 2015 y 2025 su correlación es −0,57 en homicidio y −0,3 en hurto, y cambia de signo si se mira desde 2010.\n"
         "Fuentes: armas, DIJIN (datos.gov.co 2iz5-9bbz) · homicidios, MinDefensa (m8fd-ahd9) · hurtos, Policía Nacional, SIEDCO (2015-2024 y derecho de petición 2025-2026).",
         fontsize=8.6, color="#6b6456", linespacing=1.5)
fig.text(0.92, 0.02, "Ricardo.Ruiz", ha="right", fontfamily="Arima", fontsize=12, color=OX, fontweight="bold")
fig.savefig(OUT / "armas-vs-fuego.png", facecolor=PAPER)
print(OUT / "armas-vs-fuego.png")
