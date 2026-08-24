#!/usr/bin/env python3
"""Carrusel IG 'voto femenino · SEGUNDA VUELTA 2026' · 10 piezas 1080x1080.

Reutiliza la identidad MxD de carrusel.py (Reckless + Inter + Turbinado, paleta
vinotinto/amarillo/lila). Tesis: el balotaje (Abelardo 50,5 vs Cepeda 49,5, <1pp)
lo desempató el género — las mujeres, mayoría y más constantes, inclinaron a la
derecha; si solo votaran hombres, gana Cepeda.

Datos: output_2v/agg_municipio.json (resultado 2V por municipio) + descriptivos
1V (share mujeres) + COMUNAS_DATA (censo) + encuesta AtlasIntel 2V + método
mesa-2022. Salida: output_mujeres_1v/carrusel-2v/NN_*.png
"""
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carrusel as C  # noqa: E402  (registra fuentes + paleta + helpers)
from carrusel import (VINO, AMAR, LILA, BG, FG, SUB, GRID, RED, BLUE, SLATE,  # noqa
                      BERRY_D, TITLE_F, _mix, draw_map, to_geoname, GEONAMES, REGION,
                      RN, NIV, head, foot)
import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(ROOT, "Bases de datos", "output_mujeres_1v")
CDIR2 = os.path.join(OUT, "carrusel-2v")
CAND = os.path.join(ROOT, "_candidatos")

font_manager.fontManager.addfont(os.path.join(OUT, "Turbinado Pro Regular",
                                              "Turbinado Pro Regular.ttf"))
F_TURB = FontProperties(fname=os.path.join(OUT, "Turbinado Pro Regular",
                                           "Turbinado Pro Regular.ttf"))

# ----------------------------------------------------------------- datos 2V
AGG = json.load(open(os.path.join(ROOT, "Bases de datos", "output_2v",
                                  "agg_municipio.json")))
DEPNAME = {r["dep"]: r["name"] for r in C.D["participacion_depto"]}
WSH = {r["dep"]: r["share_votantes_muj"] for r in C.D["participacion_depto"]}

# nacional 2V
C2 = sum(m["cep2"] for m in AGG); A2 = sum(m["abe2"] for m in AGG)
CEP_PCT = C2 / (C2 + A2) * 100
ABE_PCT = A2 / (C2 + A2) * 100
MARGEN = abs(A2 - C2)

# por depto: Cepeda % del duelo + voto 2V
dep2 = defaultdict(lambda: [0, 0])
for m in AGG:
    dep2[m["dep"]][0] += m["cep2"]; dep2[m["dep"]][1] += m["abe2"]
CEP_DEP = {d: c / (c + a) * 100 for d, (c, a) in dep2.items() if c + a > 0}
NCEP = sum(1 for v in CEP_DEP.values() if v >= 50)
NABE = sum(1 for v in CEP_DEP.values() if v < 50)

# participación / abstención femenina 2V (share mujeres 1V × votos 2V / censo)
urna2 = defaultdict(int)
for m in AGG:
    urna2[m["dep"]] += m["urna2"]
cm = defaultdict(int); ch = defaultdict(int)
with open(os.path.join(ROOT, "Bases de datos", "COMUNAS_DATA.csv"),
          encoding="utf-8-sig") as f:
    for row in csv.DictReader(f, delimiter=";"):
        dd = row["dd"].zfill(2)
        cm[dd] += int(float(row["mujeres"] or 0)); ch[dd] += int(float(row["hombres"] or 0))
prows = []
TM = TV = CM = CH = 0
for dep, v in urna2.items():
    if dep not in WSH or dep not in cm:
        continue
    wv = WSH[dep] / 100 * v
    prows.append({"dep": dep, "name": DEPNAME.get(dep, dep),
                  "pw": wv / cm[dep] * 100, "pm": (v - wv) / ch[dep] * 100})
    TM += wv; TV += v; CM += cm[dep]; CH += ch[dep]
PART_W = TM / CM * 100          # 67.0
PART_M = (TV - TM) / CH * 100   # 60.2
PART_NAC = TV / (CM + CH) * 100
ABST_W = 100 - PART_W
N_ABST_W = (CM - TM) / 1e6
TOP_PART = sorted(prows, key=lambda r: -r["pw"])[:3]
TOP_ABST = sorted(prows, key=lambda r: r["pw"])[:3]

N = lambda i: f"{i} / 10"


def save2(fig, name):
    os.makedirs(CDIR2, exist_ok=True)
    p = os.path.join(CDIR2, name)
    fig.savefig(p, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ->", os.path.relpath(p, ROOT))


def circ_photo(fig, path, x, y, d, ring=AMAR, lw=4.5):
    """foto circular; (x,y)=esquina inf-izq, d=diámetro (frac figura, cuadrada)."""
    im = plt.imread(path)
    h, w = im.shape[:2]
    s = min(h, w)
    im = im[(h - s) // 2:(h - s) // 2 + s, (w - s) // 2:(w - s) // 2 + s]
    ax = fig.add_axes([x, y, d, d]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    pic = ax.imshow(im, extent=[0, 1, 0, 1], origin="upper", zorder=2)
    pic.set_clip_path(Circle((0.5, 0.5), 0.5, transform=ax.transData))
    ax.add_patch(Circle((0.5, 0.5), 0.5, fill=False, ec=ring, lw=lw, zorder=3))


from PIL import Image  # noqa: E402
LOGO = os.path.join(ROOT, "Bases de datos", "output_abelardo_cartagena",
                    "logo_ricardoruiz.png")
_LIM = Image.open(LOGO).convert("RGBA")
_LAR = _LIM.width / _LIM.height


def _logo_tint(hexc):
    a = np.array(_LIM).copy()
    a[..., 0] = int(hexc[1:3], 16); a[..., 1] = int(hexc[3:5], 16)
    a[..., 2] = int(hexc[5:7], 16)
    return a


def foot2(fig, n, extra=None, dark=False):
    """Footer MxD: firma grande + logo ricardoruiz (tintado)."""
    src_c = "#e9d7e1" if dark else SUB
    mark_c = AMAR if dark else VINO
    logo_c = "#ffffff" if dark else VINO
    num_c = "#caa9ba" if dark else "#bda6b2"
    if extra:
        fig.text(0.065, 0.062, extra, fontsize=9, color=src_c, ha="left")
    fig.text(0.065, 0.028, "MUJERES POR LA DEMOCRACIA", fontsize=18.5, color=mark_c,
             ha="left", fontweight="bold")
    w = 0.27; h = w / _LAR
    axl = fig.add_axes([0.935 - w, 0.035 - h / 2, w, h]); axl.axis("off")
    axl.imshow(_logo_tint(logo_c), aspect="auto")
    if n:
        fig.text(0.935, 0.952, n, fontsize=15, color=num_c, ha="right", fontweight="bold")


# winner por depto si solo votaran mujeres / hombres
# (resultado 2V real del depto + brecha de género regional medida en 2022)
W_MUJ = 0.54
WCEP, MCEP = {}, {}
for _dep, _c in CEP_DEP.items():
    _g = to_geoname(DEPNAME.get(_dep, ""))
    if not _g:
        continue
    _rg = REGION.get(C.nrm(_g))
    _gap = C.J["region_2022"][_rg]["petro"] if _rg in C.J["region_2022"] else 0
    WCEP[_g] = _c + (1 - W_MUJ) * _gap     # mujeres: menos Cepeda
    MCEP[_g] = _c - W_MUJ * _gap           # hombres: más Cepeda
PART_NAC_S = f"{PART_NAC:.1f}%".replace(".", ",")

# Cepeda % entre mujeres / hombres por región (2V real + brecha regional 2022)
_regv = defaultdict(lambda: [0, 0])
for _m in AGG:
    _g = to_geoname(DEPNAME.get(_m["dep"], ""))
    _rg = REGION.get(C.nrm(_g)) if _g else None
    if _rg:
        _regv[_rg][0] += _m["cep2"]; _regv[_rg][1] += _m["abe2"]
REGION_GENDER = {}
for _rg, (_c, _a) in _regv.items():
    _base = _c / (_c + _a) * 100
    _gap = C.J["region_2022"][_rg]["petro"] if _rg in C.J["region_2022"] else 0
    REGION_GENDER[_rg] = (_base + (1 - W_MUJ) * _gap, _base - W_MUJ * _gap)


# ===================================================== 01 PORTADA
def s01(n):
    fig = C.new_fig(); fig.patch.set_facecolor(VINO)
    fig.text(0.065, 0.945, "VOTO FEMENINO · SEGUNDA VUELTA 2026", fontsize=15.5,
             color=VINO, va="center", fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none", boxstyle="square,pad=0.45"))
    fig.text(0.065, 0.90, "La 2ª vuelta la", fontsize=53, color="#ffffff", va="top",
             **TITLE_F)
    fig.text(0.057, 0.825, "desempató", fontsize=108, color=AMAR, va="top",
             fontproperties=F_TURB)
    fig.text(0.065, 0.685, "el género.", fontsize=53, color="#ffffff", va="top",
             **TITLE_F)
    fig.text(0.065, 0.605, "Por menos de un punto: "
             f"{ABE_PCT:.1f}".replace(".", ",") + " vs "
             f"{CEP_PCT:.1f}".replace(".", ",") + ".", fontsize=21, color=LILA,
             va="top", fontweight="bold")
    # ilustración de siluetas (PNG con fondo transparente → se ve el vino)
    img = plt.imread(os.path.join(CDIR2, "ChatGPT Image 24 jun 2026, 02_29_32 p.m..png"))
    axi = fig.add_axes([0.07, 0.085, 0.86, 0.50]); axi.axis("off")
    axi.patch.set_alpha(0)
    axi.imshow(img, aspect="auto")
    foot2(fig, n, extra="Resultado 2ª vuelta · diferencia ≈250.000 votos.", dark=True)
    save2(fig, "01_portada.png")


# ===================================================== 02 RESULTADO
def s02(n):
    fig = C.new_fig()
    head(fig, "El más estrecho en décadas", "Un país partido\ncasi por la mitad",
         tsize=51, ty=0.905)
    ax = fig.add_axes([0.065, 0.585, 0.87, 0.125]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 1)
    ax.barh(0.5, CEP_PCT, color=RED, height=0.62)
    ax.barh(0.5, ABE_PCT, left=CEP_PCT, color=BLUE, height=0.62)
    ax.text(2, 0.5, f"Cepeda {CEP_PCT:.1f}".replace(".", ","), color="white",
            fontsize=25, va="center", fontweight="bold")
    ax.text(98, 0.5, f"Abelardo {ABE_PCT:.1f}".replace(".", ","), color="white",
            fontsize=25, va="center", ha="right", fontweight="bold")
    stats = [("~250 mil", "votos de diferencia\n(≈1 punto)"),
             (PART_NAC_S, "participación récord\n(subió desde 58%)")]
    for i, (big, lab) in enumerate(stats):
        x = 0.27 + i * 0.42
        fig.text(x, 0.45, big, fontsize=62, color=VINO, ha="center", **TITLE_F)
        fig.text(x, 0.315, lab, fontsize=21, color=SUB, ha="center", va="top",
                 linespacing=1.3, fontweight="bold")
    fig.text(0.065, 0.155, "Un país empatado: cualquier grupo que se mueva, decide.",
             fontsize=23.5, color=FG, **TITLE_F)
    foot2(fig, n, extra="Resultado 2ª vuelta por municipio · RNEC.")
    save2(fig, "02_resultado.png")


# ===================================================== 03 CONTRAFACTUAL
def s03(n):
    fig = C.new_fig()
    head(fig, "El contrafactual",
         "Si solo votaran los hombres,\nCepeda sería presidente", tsize=36, ty=0.905)
    fig.text(0.065, 0.775, "La misma segunda vuelta, contando un solo sexo a la vez\n"
             "(duelo Cepeda–Abelardo).", fontsize=19.5, color=SUB, va="top",
             linespacing=1.4)
    dsp = lambda v: (f"{v:.0f}" if abs(v - round(v)) < 0.1 else f"{v:.1f}").replace(".", ",")
    rows = [("SOLO HOMBRES", "Cepeda", 57, "Abelardo", 43, RED, BLUE),
            ("RESULTADO REAL", "Cepeda", CEP_PCT, "Abelardo", ABE_PCT, RED, BLUE),
            ("SOLO MUJERES", "Abelardo", 57, "Cepeda", 43, BLUE, RED)]
    ax = fig.add_axes([0.065, 0.295, 0.87, 0.385]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 1)
    for i, (lab, w1, v1, w2, v2, c1, c2) in enumerate(rows):
        y = 0.85 - i * 0.36
        ax.text(0, y + 0.15, lab, fontsize=18.5, color=FG, fontweight="bold")
        ax.barh(y, v1, color=c1, height=0.185)
        ax.barh(y, v2, left=v1, color=c2, height=0.185)
        ax.text(1.5, y, f"{w1} {dsp(v1)}", color="white", fontsize=18, va="center",
                fontweight="bold")
        ax.text(98.5, y, f"{w2} {dsp(v2)}", color="white", fontsize=18, va="center",
                ha="right", fontweight="bold")
    fig.text(0.065, 0.245, "La brecha por sexo fue de ~14 puntos. El margen real, "
             "de 1.", fontsize=21, color=FG, **TITLE_F)
    fig.text(0.062, 0.155, "El género desempató.", fontsize=50, color=VINO, va="top",
             fontproperties=F_TURB)
    foot2(fig, n, extra="Resultado real + brecha de género (AtlasIntel 2V + mesa-2022).")
    save2(fig, "03_contrafactual.png")


# ===================================================== 04 PESO
def s04(n):
    fig = C.new_fig()
    head(fig, "El peso de ellas", "Mayoría — y deciden\nel empate", tsize=47, ty=0.905)
    fig.text(0.205, 0.585, "54%", fontsize=180, color=VINO, ha="center", va="center",
             **TITLE_F)
    rx = 0.45
    fig.text(rx, 0.685, "de los votos de la\nsegunda vuelta\nfueron de mujeres.",
             fontsize=26, color=FG, va="center", linespacing=1.2, fontweight="bold")
    fig.text(rx, 0.49, "Cerca de 13,8 millones de\nmujeres marcaron tarjetón.",
             fontsize=20.5, color=SUB, va="center", linespacing=1.3)
    censo_w = CM / (CM + CH) * 100
    fig.text(rx, 0.355, "Y ya son mayoría en el censo:\nel "
             f"{censo_w:.0f}% del padrón es mujer.", fontsize=20.5, color=SUB,
             va="center", linespacing=1.3)
    fig.text(0.065, 0.21, "En un país partido casi por la mitad, la mayoría\nque sí "
             "va a votar inclina la balanza.", fontsize=26, color=FG, va="top",
             linespacing=1.35, **TITLE_F)
    foot2(fig, n, extra="Votantes por sexo + censo electoral CNE 2026 · proyección 2V.")
    save2(fig, "04_peso.png")


# ===================================================== 05 RÉCORD POR GÉNERO
def s05(n):
    fig = C.new_fig()
    head(fig, "Quién empujó el récord",
         "Ellas movieron la\nparticipación", tsize=48, ty=0.905)
    fig.text(0.065, 0.715, "De cada grupo habilitado, cuánto votó en la segunda vuelta:",
             fontsize=20, color=SUB, va="top")
    ax = fig.add_axes([0.165, 0.30, 0.77, 0.40]); ax.set_facecolor(BG)
    vals = [("Mujeres", PART_W, VINO), ("Hombres", PART_M, SLATE)]
    for i, (lab, v, c) in enumerate(vals):
        y = 1 - i
        ax.text(2, y + 0.33, lab, fontsize=23, color=FG, va="bottom", fontweight="bold")
        ax.barh(y, v, height=0.46, color=c)
        ax.text(v + 1.5, y, f"{v:.0f}%", va="center", fontsize=33, fontweight="bold",
                color=FG)
    ax.set_xlim(0, 88); ax.set_ylim(-0.5, 1.75); ax.axis("off")
    fig.text(0.065, 0.19, f"Participación récord de {PART_NAC_S}, impulsada sobre "
             "todo por ellas.\nVotó el "
             f"{PART_W:.0f}% de las mujeres habilitadas, frente al {PART_M:.0f}% "
             "de los hombres.", fontsize=21, color=FG, va="top", linespacing=1.45)
    foot2(fig, n, extra="Participación = votantes / censo, por sexo · 2ª vuelta.")
    save2(fig, "05_record.png")


# ===================================================== 06 DÓNDE VOTAN Y NO
def s06(n):
    fig = C.new_fig()
    head(fig, "Dónde votan y dónde no",
         "Aun con récord, una de cada\ntres mujeres no votó", tsize=33, ty=0.90)
    abst_m = f"{N_ABST_W:.1f}".replace(".", ",")
    fig.text(0.065, 0.76, f"{ABST_W:.0f}% de las mujeres habilitadas se quedó en "
             f"casa (~{abst_m} millones).", fontsize=19.5, color=SUB, va="top")
    SHORT = {"San Andrés y Providencia": "San Andrés",
             "Norte de Santander": "N. de Santander", "Valle del Cauca": "Valle"}
    # dos cajas de contraste
    ax = fig.add_axes([0.065, 0.205, 0.87, 0.51]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    cards = [(0.0, 0.475, "MÁS PARTICIPAN", TOP_PART, lambda r: f"{r['pw']:.0f}%",
              _mix(VINO, BG, 0.86), VINO),
             (0.525, 1.0, "MÁS SE ABSTIENEN", TOP_ABST, lambda r: f"{100 - r['pw']:.0f}%",
              _mix("#8a7150", BG, 0.84), "#6e5733")]
    for x0, x1, title, rows, val, fc, accent in cards:
        ax.add_patch(FancyBboxPatch((x0, 0.03), x1 - x0, 0.94,
                     boxstyle="round,pad=0,rounding_size=0.025", fc=fc, ec="none"))
        ax.text(x0 + 0.045, 0.85, title, fontsize=17.5, color=accent, fontweight="bold")
        for i, r in enumerate(rows):
            y = 0.62 - i * 0.21
            nm = to_geoname(r["name"]) or r["name"].title()
            ax.text(x0 + 0.045, y, SHORT.get(nm, nm),
                    fontsize=20.5, color=FG, va="center")
            ax.text(x1 - 0.04, y, val(r), fontsize=25, color=accent, ha="right",
                    va="center", fontweight="bold")
    fig.text(0.065, 0.175, "Cundinamarca y el Cauca lideran la participación femenina; "
             "la periferia\n(Guainía, San Andrés, Vaupés) sigue rezagada.",
             fontsize=19, color=FG, va="top", linespacing=1.45)
    foot2(fig, n, extra="Participación / abstención femenina por departamento · 2ª vuelta.")
    save2(fig, "06_abstencion.png")


# ===================================================== 07 GENERACIONAL
def s07(n):
    niv = NIV["izq_niveles"]; AGE = ["18-35", "36-60", "61+"]
    fig = C.new_fig()
    head(fig, "Edad y sexo se suman",
         "El hombre joven con Cepeda;\nla mujer mayor, con Abelardo", tsize=35, ty=0.905)
    fig.text(0.065, 0.755, "El duelo Cepeda–Abelardo por sexo y edad (cada barra suma "
             "100).\nEn cada par, la mujer (arriba) pone menos rojo (Cepeda) que el "
             "hombre.", fontsize=18.5, color=SUB, va="top", linespacing=1.4)
    ax = fig.add_axes([0.135, 0.205, 0.81, 0.46]); ax.set_xlim(-15, 100)
    ax.axis("off")
    ypos = {}
    y = 5.4
    for a in AGE:
        ypos[(a, "Mujeres")] = y; ypos[(a, "Hombres")] = y - 0.85; y -= 2.25
    for (a, sexo), yy in ypos.items():
        cep = niv[sexo][a]; abe = 100 - cep
        ax.barh(yy, cep, color=RED, height=0.72, edgecolor=BG, lw=1.2)
        ax.barh(yy, abe, left=cep, color=BLUE, height=0.72, edgecolor=BG, lw=1.2)
        ax.text(cep / 2, yy, f"{cep:.0f}", ha="center", va="center", fontsize=14.5,
                color="white", fontweight="bold")
        ax.text(cep + abe / 2, yy, f"{abe:.0f}", ha="center", va="center",
                fontsize=14.5, color="white", fontweight="bold")
        ax.text(-1.5, yy, "M" if sexo == "Mujeres" else "H", ha="right", va="center",
                fontsize=14, color=FG, fontweight="bold")
    for a in AGE:
        ym = (ypos[(a, "Mujeres")] + ypos[(a, "Hombres")]) / 2
        ax.text(-10, ym, f"{a}\naños", ha="center", va="center", fontsize=16.5,
                color=FG, fontweight="bold")
    ax.set_ylim(-0.1, 6.1)
    hs = [plt.Rectangle((0, 0), 1, 1, color=RED), plt.Rectangle((0, 0), 1, 1, color=BLUE)]
    ax.legend(hs, ["Cepeda", "Abelardo"], loc="upper center",
              bbox_to_anchor=(0.5, -0.03), ncol=2, frameon=False, fontsize=14.5,
              labelcolor=FG, handlelength=1.1, columnspacing=1.8)
    fig.text(0.065, 0.105, "Joven y hombre, lo más Cepeda; mayor y mujer, lo más "
             "Abelardo.", fontsize=18.5, color=FG, va="top")
    foot2(fig, n, extra="Voto Cepeda por sexo y edad · mesa con efectos fijos de puesto, 2022.")
    save2(fig, "07_generacional.png")


# ===================================================== 08 GEOGRAFÍA (dos mapas)
def s08(n):
    def cm(v):
        return _mix("#f4e6e4", RED, min((v - 50) / 22, 1)) if v >= 50 \
            else _mix("#e4e6f0", BLUE, min((50 - v) / 22, 1))
    fig = C.new_fig()
    head(fig, "La geografía por sexo",
         "El mapa cambia según\nquién vote", tsize=35, ty=0.905)
    fig.text(0.065, 0.765, "Quién habría ganado en cada departamento si solo votara "
             "cada sexo.", fontsize=19, color=SUB, va="top")
    a1 = fig.add_axes([0.05, 0.255, 0.425, 0.45]); draw_map(a1, WCEP, cm)
    a2 = fig.add_axes([0.525, 0.255, 0.425, 0.45]); draw_map(a2, MCEP, cm)
    fig.text(0.2625, 0.715, "Si solo votaran las mujeres", fontsize=19, color=FG,
             ha="center", fontweight="bold")
    fig.text(0.7375, 0.715, "Si solo votaran los hombres", fontsize=19, color=FG,
             ha="center", fontweight="bold")
    fig.text(0.285, 0.205, "■", color=RED, fontsize=18, ha="left", va="center")
    fig.text(0.315, 0.205, "gana Cepeda", color=FG, fontsize=18, ha="left", va="center")
    fig.text(0.55, 0.205, "■", color=BLUE, fontsize=18, ha="left", va="center")
    fig.text(0.58, 0.205, "gana Abelardo", color=FG, fontsize=18, ha="left", va="center")
    fig.text(0.065, 0.15, "Entre hombres el país se vuelve más rojo (Cepeda); entre "
             "mujeres, más azul\n(Abelardo). El mismo país, dos resultados.",
             fontsize=18, color=FG, va="top", linespacing=1.4)
    foot2(fig, n, extra="Duelo Cepeda–Abelardo por sexo y depto · resultado 2V + brecha 2022.")
    save2(fig, "08_geografia.png")


# ===================================================== 09 ELLAS VS ELLOS POR REGIÓN
def s09(n):
    fig = C.new_fig()
    head(fig, "Ellas y ellos, lado a lado",
         "El apoyo a Cepeda:\nmujeres vs hombres", tsize=38, ty=0.905)
    fig.text(0.065, 0.75, "% que votó por Cepeda en cada región. El punto vino son "
             "ellas; el gris, ellos.\nA la derecha de la línea gana Cepeda; a la "
             "izquierda, Abelardo.", fontsize=18.5, color=SUB, va="top", linespacing=1.4)
    order = sorted(REGION_GENDER.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
    ax = fig.add_axes([0.24, 0.215, 0.69, 0.45]); ax.set_facecolor(BG)
    ax.set_xlim(20, 84)
    nr = len(order)
    ax.axvline(50, color="#c9b9c1", lw=1.4, ls=(0, (4, 3)), zorder=1)
    for i, (rg, (w, m)) in enumerate(order):
        yy = nr - 1 - i
        ax.plot([w, m], [yy, yy], color=_mix(VINO, SLATE, 0.5), lw=2.8, zorder=2)
        ax.plot(w, yy, "o", color=VINO, ms=14.5, zorder=3)
        ax.plot(m, yy, "o", color=SLATE, ms=14.5, zorder=3)
        ax.text(18.5, yy, RN[rg], ha="right", va="center", fontsize=16.5, color=FG)
    ax.set_ylim(-0.6, nr - 0.4); ax.set_yticks([])
    ax.set_xticks([30, 50, 70]); ax.set_xticklabels(["30%", "50%", "70%"],
                                                    fontsize=13, color=SUB)
    ax.tick_params(length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    hs = [plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=VINO, ms=13),
          plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=SLATE, ms=13)]
    ax.legend(hs, ["Mujeres", "Hombres"], loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=2, frameon=False, fontsize=16.5,
              labelcolor=FG, handletextpad=0.2, columnspacing=1.6)
    fig.text(0.065, 0.13, "En cada región, ellos apoyan más a Cepeda que ellas;\n"
             "en la costa la distancia es mayor.", fontsize=18, color=FG, va="top",
             linespacing=1.4)
    foot2(fig, n, extra="Apoyo a Cepeda por sexo y región · resultado 2V + brecha 2022.")
    save2(fig, "09_ellas_ellos.png")


# ===================================================== 10 CIERRE
def s10(n):
    fig = C.new_fig(); fig.patch.set_facecolor(VINO)
    fig.text(0.065, 0.94, "EN RESUMEN", fontsize=15.5, color=VINO, va="center",
             fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none", boxstyle="square,pad=0.45"))
    pts = [("Son decisivas.", "54% de los votos y +7 puntos\nde participación que ellos."),
           ("El género desempató.", "Solo hombres → Cepeda.\nSolo mujeres → Abelardo."),
           ("La grieta también es de edad.", "Joven y hombre, a la izquierda;\nmayor y mujer, a la derecha."),
           ("Y millones no votan.", "Una de cada tres mujeres\nse quedó en casa.")]
    pos = [(0.065, 0.85), (0.535, 0.85), (0.065, 0.565), (0.535, 0.565)]
    for (xx, yy), (t, s) in zip(pos, pts):
        fig.text(xx, yy, t, fontsize=27, color=AMAR, va="top", **TITLE_F)
        fig.text(xx, yy - 0.075, s, fontsize=18.5, color="#f0e0e9", va="top",
                 linespacing=1.35)
    fig.text(0.065, 0.355, "Esto es análisis del electorado, no un respaldo a ningún "
             "candidato.", fontsize=20, color="#ffffff", va="top", fontweight="bold")
    fig.text(0.065, 0.225, "Mesa a mesa (efectos fijos de puesto) + encuesta · RNEC · "
             "DANE · AtlasIntel.", fontsize=16, color="#e9d7e1", va="top")
    fig.text(0.065, 0.12, "MUJERES POR LA DEMOCRACIA", fontsize=24, color=AMAR,
             ha="left", va="center", fontweight="bold")
    _lw = 0.36; _lh = _lw / _LAR
    _al = fig.add_axes([0.935 - _lw, 0.12 - _lh / 2, _lw, _lh]); _al.axis("off")
    _al.imshow(_logo_tint("#ffffff"), aspect="auto")
    fig.text(0.935, 0.94, n, fontsize=15, color="#caa9ba", ha="right", fontweight="bold")
    save2(fig, "10_cierre.png")


SLIDES = {"portada": s01, "resultado": s02, "contrafactual": s03, "peso": s04,
          "record": s05, "abstencion": s06, "generacional": s07, "geografia": s08,
          "brecha": s09, "cierre": s10}
ORDER = list(SLIDES)

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    todo = ORDER if args == ["all"] else args
    for k in todo:
        SLIDES[k](N(ORDER.index(k) + 1))
