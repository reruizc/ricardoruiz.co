#!/usr/bin/env python3
"""Carrusel IG 'La nueva legislatura 2026-2030' (MxD) · 10 piezas 1080x1080.

Identidad MxD reutilizada de tools/mujeres-1v-2026/carrusel.py (Reckless +
Inter + Turbinado, vinotinto/amarillo/lila). Textos aprobados en
rrss/instagram/carrusel-legislatura-2026/textos-carrusel.md con ajustes:
  - S1: foto del Capitolio (imagenes-index/legislativo.jpg, CC BY-SA 3.0).
  - S2: grafica de estancamiento (12->19,7->29->29) + asterisco CITREP.
  - S4: no asegura "cero mujeres" (los nombres no estan definidos).
  - S6: reencuadrada a ausencia de debate / voluntad politica (no "el reloj").

Datos: comunicado MxD 20-jul-2026 + Caudal stats.json (9.919 proyectos
1990-2026) + acuerdo de presidencias de Camara (AXIS) + analisis de bloqueo.
Salida: rrss/instagram/carrusel-legislatura-2026/NN_*.png

Uso: python3 tools/mxd-legislatura/build_carrusel.py [all | portada curva ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "mujeres-1v-2026"))

import carrusel as C  # noqa: E402  (registra fuentes + paleta + helpers)
from carrusel import (VINO, AMAR, LILA, BG, FG, SUB, INK3, SLATE,  # noqa: E402
                      TITLE_F, _mix, head)
import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

OUTM = os.path.join(ROOT, "Bases de datos", "output_mujeres_1v")
CDIR = os.path.join(ROOT, "rrss", "instagram", "carrusel-legislatura-2026")
FOTO = os.path.join(ROOT, "imagenes-index", "legislativo.jpg")

font_manager.fontManager.addfont(os.path.join(OUTM, "Turbinado Pro Regular",
                                              "Turbinado Pro Regular.ttf"))
F_TURB = FontProperties(fname=os.path.join(OUTM, "Turbinado Pro Regular",
                                           "Turbinado Pro Regular.ttf"))

LOGO = os.path.join(ROOT, "Bases de datos", "output_abelardo_cartagena",
                    "logo_ricardoruiz.png")
_LIM = Image.open(LOGO).convert("RGBA")
_LAR = _LIM.width / _LIM.height

N = lambda i: f"{i} / 10"


def _logo_tint(hexc):
    a = np.array(_LIM).copy()
    a[..., 0] = int(hexc[1:3], 16); a[..., 1] = int(hexc[3:5], 16)
    a[..., 2] = int(hexc[5:7], 16)
    return a


def foot(fig, n, extra=None, dark=False):
    """Footer MxD: firma grande + logo ricardoruiz (tintado) + contador."""
    src_c = "#e9d7e1" if dark else SUB
    mark_c = AMAR if dark else VINO
    logo_c = "#ffffff" if dark else VINO
    num_c = "#caa9ba" if dark else "#bda6b2"
    if extra:
        fig.text(0.065, 0.062, extra, fontsize=9, color=src_c, ha="left")
    fig.text(0.065, 0.028, "MUJERES POR LA DEMOCRACIA", fontsize=18.5,
             color=mark_c, ha="left", fontweight="bold")
    w = 0.27; h = w / _LAR
    axl = fig.add_axes([0.935 - w, 0.035 - h / 2, w, h]); axl.axis("off")
    axl.imshow(_logo_tint(logo_c), aspect="auto")
    if n:
        fig.text(0.935, 0.952, n, fontsize=15, color=num_c, ha="right",
                 fontweight="bold")


def save(fig, name):
    os.makedirs(CDIR, exist_ok=True)
    p = os.path.join(CDIR, name)
    fig.savefig(p, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ->", os.path.relpath(p, ROOT))


def head_dark(fig, kicker):
    fig.text(0.065, 0.945, kicker.upper(), fontsize=15.5, color=VINO,
             va="center", fontweight="bold", ha="left",
             bbox=dict(facecolor=AMAR, edgecolor="none",
                       boxstyle="square,pad=0.45"))


# ===================================================== 01 PORTADA
def s01(n):
    fig = C.new_fig(); fig.patch.set_facecolor(VINO)
    head_dark(fig, "20 de julio de 2026")
    fig.text(0.065, 0.895, "Hoy se instala", fontsize=56, color="#ffffff",
             va="top", **TITLE_F)
    fig.text(0.057, 0.815, "el Congreso", fontsize=105, color=AMAR, va="top",
             fontproperties=F_TURB)
    fig.text(0.065, 0.675, "2026–2030.", fontsize=56, color="#ffffff",
             va="top", **TITLE_F)
    fig.text(0.065, 0.588, "Los retos y las oportunidades de la\nnueva "
             "legislatura, en datos.", fontsize=22.5, color=LILA, va="top",
             linespacing=1.35, fontweight="bold")
    # foto del Capitolio (banda inferior, full-bleed)
    im = plt.imread(FOTO)
    axi = fig.add_axes([0.0, 0.105, 1.0, 0.375]); axi.axis("off")
    axi.imshow(im, aspect="auto")
    # filo amarillo sobre la foto
    axl = fig.add_axes([0.0, 0.478, 1.0, 0.006]); axl.axis("off")
    axl.set_facecolor(AMAR); axl.patch.set_alpha(1)
    axl.imshow(np.ones((1, 1, 3)) * np.array([249, 226, 84]) / 255,
               aspect="auto")
    foot(fig, n, extra="Foto: Capitolio Nacional · Rikimedia, Wikimedia "
         "Commons · CC BY-SA 3.0 (recortada).", dark=True)
    save(fig, "01_portada.png")


# ===================================================== 02 LA CURVA SE DETUVO
def s02(n):
    fig = C.new_fig()
    head(fig, "El reto Nº 1", "La curva se detuvo.", tsize=52, ty=0.905)
    fig.text(0.065, 0.795, "Mujeres en el Congreso · % de las curules",
             fontsize=18, color=SUB, va="top", fontweight="bold")
    # barras 1998 (Senado) · 2018 · 2022 · 2026
    ax = fig.add_axes([0.10, 0.36, 0.84, 0.385]); ax.set_facecolor(BG)
    ax.axis("off")
    datos = [("1998", 12, SLATE, "12 %", "solo\nSenado"),
             ("2018", 19.7, _mix(VINO, BG, 0.35), "19,7 %", None),
             ("2022", 29, VINO, "29 %", None),
             ("2026", 29, VINO, "29 %*", None)]
    ax.set_xlim(-0.6, 3.6); ax.set_ylim(0, 40)
    for i, (anio, v, c, lab, tag) in enumerate(datos):
        ax.bar(i, v, width=0.62, color=c)
        ax.text(i, v + 1.4, lab, ha="center", fontsize=23, color=FG,
                fontweight="bold")
        ax.text(i, -3.6, anio, ha="center", fontsize=19, color=SUB,
                fontweight="bold")
        if tag:
            ax.text(i, v / 2, tag, ha="center", va="center", fontsize=12.5,
                    color="#ffffff", fontweight="bold", linespacing=1.15)
    # bracket del estancamiento 2022-2026
    ax.plot([2, 3], [34.5, 34.5], color=VINO, lw=2)
    ax.plot([2, 2], [32.8, 34.5], color=VINO, lw=2)
    ax.plot([3, 3], [32.8, 34.5], color=VINO, lw=2)
    ax.text(2.5, 36.0, "sin avance", ha="center", fontsize=17, color=VINO,
            fontweight="bold")
    fig.text(0.065, 0.30, "El Congreso 2026–2030 lo integran 82 mujeres —32 "
             "senadoras y 50\nrepresentantes—: cerca del 29 % de las curules. "
             "La misma proporción\nde hace cuatro años, por primera vez en "
             "tres décadas sin subir.", fontsize=19.5, color=FG, va="top",
             linespacing=1.45)
    fig.text(0.065, 0.135, "*Cifra sin curules CITREP. Incluyéndolas: 85 de "
             "286 curules (29,7 %).", fontsize=13.5, color=SUB, va="top")
    foot(fig, n, extra="Composición reconstruida curul a curul · escrutinio "
         "oficial + listas · ONU Mujeres · MOE.")
    save(fig, "02_curva.png")


# ===================================================== 03 RÉCORD
def s03(n):
    fig = C.new_fig()
    head(fig, "No es un problema de votos",
         "Más candidatas que nunca.\nLas mismas curules.", tsize=40, ty=0.905)
    stats = [("40,9 %", "de las candidaturas al\nCongreso fueron de mujeres.\n"
              "Récord histórico."),
             ("29 %", "de las curules\nobtenidas.\nIgual que en 2022.")]
    for i, (big, lab) in enumerate(stats):
        x = 0.27 + i * 0.46
        fig.text(x, 0.615, big, fontsize=86, color=VINO, ha="center", **TITLE_F)
        fig.text(x, 0.50, lab, fontsize=19.5, color=SUB, ha="center",
                 va="top", linespacing=1.35, fontweight="bold")
    fig.text(0.50, 0.60, "→", fontsize=52, color=INK3, ha="center")
    fig.text(0.065, 0.315, "Entre postularse y llegar se pierden doce "
             "puntos.", fontsize=22, color=FG, va="top", **TITLE_F)
    fig.text(0.065, 0.255, "La diferencia la hacen las reglas de cada lista: "
             "donde hubo cremallera\n—alternancia mujer-hombre—, la bancada "
             "llegó con 45 % de mujeres.\nDonde no, ellas quedaron en los "
             "renglones que no eligen.", fontsize=19, color=SUB, va="top",
             linespacing=1.45)
    foot(fig, n, extra="Candidaturas RNEC 2026 · bancada con cremallera: "
         "Pacto Histórico (45 % mujeres).")
    save(fig, "03_record.png")


# ===================================================== 04 PODER REPARTIDO
def s04(n):
    fig = C.new_fig()
    head(fig, "Las decisiones de esta semana",
         "Presidencias pactadas\nhasta 2030.", tsize=46, ty=0.905)
    fig.text(0.065, 0.755, "Presidencia de la Cámara según el acuerdo entre "
             "partidos:", fontsize=18.5, color=SUB, va="top",
             fontweight="bold")
    partidos = [("AÑO 1", "Partido\nConservador"), ("AÑO 2", "Partido\nLiberal"),
                ("AÑO 3", "Centro\nDemocrático"), ("AÑO 4", "Centro\nDemocrático")]
    ax = fig.add_axes([0.065, 0.50, 0.87, 0.20]); ax.axis("off")
    ax.set_xlim(0, 4); ax.set_ylim(0, 1)
    for i, (anio, p) in enumerate(partidos):
        ax.add_patch(FancyBboxPatch((i + 0.035, 0.05), 0.93, 0.9,
                     boxstyle="round,pad=0,rounding_size=0.06",
                     fc=_mix(VINO, BG, 0.90), ec="none"))
        ax.text(i + 0.5, 0.76, anio, ha="center", fontsize=15, color=INK3,
                fontweight="bold")
        ax.text(i + 0.5, 0.42, p, ha="center", va="center", fontsize=16.5,
                color=VINO, fontweight="bold", linespacing=1.2)
    fig.text(0.065, 0.435, "La presidencia de la Cámara y la de sus 7 "
             "comisiones ya se repartieron\npor acuerdo entre cinco partidos "
             "para los cuatro años.", fontsize=19, color=FG, va="top",
             linespacing=1.45)
    fig.text(0.065, 0.32, "Los nombres aún no se definen, pero las mesas "
             "directivas se perfilan\nsin mujeres en las presidencias.",
             fontsize=20.5, color=VINO, va="top", linespacing=1.4,
             fontweight="bold")
    fig.text(0.065, 0.20, "Y el gabinete entrante aún debe nombrar las "
             "ministras que exige\nla Ley 2424 de 2024.", fontsize=19,
             color=SUB, va="top", linespacing=1.45)
    foot(fig, n, extra="Acuerdo de presidencias de Cámara 2026–2030 "
         "(documento en circulación) · Ley 2424 de 2024.")
    save(fig, "04_poder.png")


# ===================================================== 05 EMBUDO
def s05(n):
    fig = C.new_fig()
    head(fig, "Lo que dicen 36 años de datos",
         "Así de angosto es el\ncamino a ser ley.", tsize=44, ty=0.905)
    ax = fig.add_axes([0.065, 0.435, 0.87, 0.29]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 2.1)
    ax.barh(1.55, 100, color=_mix(VINO, BG, 0.82), height=0.52)
    ax.text(1.6, 1.55, "9.919 proyectos radicados (1990–2026)", fontsize=18.5,
            color=VINO, va="center", fontweight="bold")
    leyes_w = 2509 / 9919 * 100
    ax.barh(0.75, leyes_w, color=VINO, height=0.52)
    ax.text(leyes_w + 1.8, 0.75, "2.509 leyes", fontsize=18.5, color=VINO,
            va="center", fontweight="bold")
    fig.text(0.50, 0.345, "1 de cada 4", fontsize=76, color=VINO,
             ha="center", **TITLE_F)
    fig.text(0.065, 0.225, "La mayoría no pierde una votación:\nnunca llega "
             "a votarse.", fontsize=23, color=FG, va="top", linespacing=1.35,
             **TITLE_F)
    foot(fig, n, extra="Base propia: 9.919 proyectos de ley del Senado, "
         "1990–2026.")
    save(fig, "05_embudo.png")


# ===================================================== 06 SIN DEBATE
def s06(n):
    fig = C.new_fig()
    head(fig, "El dato que nadie mira",
         "Mueren sin ser debatidos.", tsize=45, ty=0.905)
    stats = [("2.804", "proyectos archivados por\nvencimiento de términos",
              VINO),
             ("2.509", "proyectos convertidos\nen ley", SLATE)]
    for i, (big, lab, c) in enumerate(stats):
        x = 0.27 + i * 0.46
        fig.text(x, 0.585, big, fontsize=74, color=c, ha="center", **TITLE_F)
        fig.text(x, 0.49, lab, fontsize=18.5, color=SUB, ha="center",
                 va="top", linespacing=1.35, fontweight="bold")
    fig.text(0.50, 0.585, ">", fontsize=56, color=INK3, ha="center")
    fig.text(0.065, 0.345, "Y no es falta de tiempo: es voluntad política.",
             fontsize=23.5, color=FG, va="top", **TITLE_F)
    fig.text(0.065, 0.28, "Los proyectos no se hunden en el voto: no se "
             "agendan, se aplazan una\ny otra vez, o no hay ambiente para "
             "ponerlos a discutir. La ausencia\nde debate archiva más "
             "proyectos que el debate mismo.", fontsize=19, color=SUB,
             va="top", linespacing=1.45)
    foot(fig, n, extra="Archivo por tránsito de legislatura (Art. 190, Ley "
         "5ª de 1992) · base propia 1990–2026.")
    save(fig, "06_sin_debate.png")


# ===================================================== 07 EL TURNO
def s07(n):
    fig = C.new_fig()
    head(fig, "Dónde se define todo",
         "No es el debate: es el turno.", tsize=42, ty=0.905)
    fig.text(0.065, 0.745, "Probabilidad de que un proyecto agendado sea "
             "tratado ese día\nen la comisión, según su puesto en el orden "
             "del día:", fontsize=18.5, color=SUB, va="top", linespacing=1.4)
    ax = fig.add_axes([0.10, 0.36, 0.84, 0.30]); ax.axis("off")
    ax.set_xlim(0, 66); ax.set_ylim(-0.55, 1.75)
    vals = [("1º en el orden del día", 53, VINO),
            ("Del 4º puesto en adelante", 21, SLATE)]
    for i, (lab, v, c) in enumerate(vals):
        y = 1 - i
        ax.text(0.5, y + 0.33, lab, fontsize=20, color=FG, va="bottom",
                fontweight="bold")
        ax.barh(y, v, height=0.44, color=c)
        ax.text(v + 1.5, y, f"{v} %", va="center", fontsize=30,
                fontweight="bold", color=c)
    fig.text(0.065, 0.255, "Quien arma la agenda decide qué se discute\n—sin "
             "votar nada.", fontsize=23, color=FG, va="top", linespacing=1.35,
             **TITLE_F)
    foot(fig, n, extra="Órdenes del día y actas de las comisiones de la "
         "Cámara · elaboración propia.")
    save(fig, "07_turno.png")


# ===================================================== 08 ELLAS RINDEN MÁS
def s08(n):
    fig = C.new_fig()
    head(fig, "El hallazgo que desmonta un prejuicio",
         "Los proyectos de ellas rinden\nmás. Y aun así se quedan\nen la "
         "antesala.", tsize=33, ty=0.91)
    fig.text(0.065, 0.72, "Proyectos según el género de su autoría "
             "principal (1990–2026):", fontsize=17.5, color=SUB, va="top")
    ax = fig.add_axes([0.10, 0.42, 0.84, 0.26]); ax.axis("off")
    ax.set_xlim(0, 60); ax.set_ylim(-0.7, 1.9)
    grupos = [("Llegan a primer debate", 44, 39, 1.05),
              ("Se convierten en ley", 17, 15, 0.0)]
    for lab, vm, vh, y in grupos:
        ax.text(0.5, y + 0.42, lab, fontsize=18.5, color=FG, va="bottom",
                fontweight="bold")
        ax.barh(y + 0.14, vm, height=0.24, color=VINO)
        ax.barh(y - 0.14, vh, height=0.24, color=SLATE)
        ax.text(vm + 1.2, y + 0.14, f"{vm} % autoras", va="center",
                fontsize=16.5, color=VINO, fontweight="bold")
        ax.text(vh + 1.2, y - 0.14, f"{vh} % autores", va="center",
                fontsize=16.5, color=SUB, fontweight="bold")
    pts = [("15 intentos, 0 leyes", "de paridad en las listas, en tres décadas."),
           ("31 años", "tardó la ley contra el acoso sexual (1993–2024)."),
           ("La Corte, no el Congreso", "destrabó los derechos reproductivos.")]
    y0 = 0.345
    for i, (t, s) in enumerate(pts):
        y = y0 - i * 0.075
        fig.text(0.065, y, "— " + t + ".", fontsize=19, color=VINO, va="top",
                 fontweight="bold")
        fig.text(0.42, y, s, fontsize=17.5, color=SUB, va="top")
    foot(fig, n, extra="Autoría principal por género (inferido por nombre), "
         "sin iniciativas del Gobierno · 1990–2026.")
    save(fig, "08_ellas.png")


# ===================================================== 09 LA VENTANA
def s09(n):
    fig = C.new_fig()
    head(fig, "La oportunidad",
         "Lo que importa se juega\nen 2026–2028.", tsize=44, ty=0.905)
    fig.text(0.065, 0.755, "Proyectos que mueren por vencimiento de "
             "términos, según el año\ndel cuatrienio en que se radican:",
             fontsize=18.5, color=SUB, va="top", linespacing=1.4)
    ax = fig.add_axes([0.10, 0.40, 0.84, 0.27]); ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(-0.6, 3.6); ax.set_ylim(0, 46)
    datos = [("Año 1\n(hoy)", 26, _mix(VINO, BG, 0.45)),
             ("Año 2", 26, _mix(VINO, BG, 0.45)),
             ("Año 3", 26, _mix(VINO, BG, 0.45)),
             ("Año 4\n(electoral)", 34.7, VINO)]
    for i, (lab, v, c) in enumerate(datos):
        ax.bar(i, v, width=0.62, color=c)
        vl = f"{v:.1f}".replace(".", ",") + " %" if v != 26 else "~26 %"
        ax.text(i, v + 1.6, vl, ha="center", fontsize=20, color=FG,
                fontweight="bold")
        ax.text(i, -8.5, lab, ha="center", fontsize=16, color=SUB,
                fontweight="bold", linespacing=1.15)
    fig.text(0.065, 0.30, "En el año electoral, la campaña se toma la agenda "
             "y la mortandad\nde proyectos se dispara.", fontsize=19,
             color=SUB, va="top", linespacing=1.45)
    fig.text(0.065, 0.20, "La ventana real de esta legislatura son sus dos\n"
             "primeros años. Lo que no se agende ahora,\ndifícilmente será "
             "ley.", fontsize=22, color=FG, va="top", linespacing=1.3,
             **TITLE_F)
    foot(fig, n, extra="Mortandad por año del cuatrienio en que se radica el "
         "proyecto · base propia 1990–2026.")
    save(fig, "09_ventana.png")


# ===================================================== 10 CIERRE
def s10(n):
    fig = C.new_fig(); fig.patch.set_facecolor(VINO)
    head_dark(fig, "Lo que pedimos")
    fig.text(0.065, 0.885, "Tres decisiones que sí\nmueven la cifra.",
             fontsize=44, color="#ffffff", va="top", linespacing=1.05,
             **TITLE_F)
    pts = [("1 · Paridad real.",
            "Cremallera en todas las listas,\nno solo en algunas."),
           ("2 · Un orden del día que responda.",
            "Transparencia sobre quién agenda\ny quién aplaza — y por qué."),
           ("3 · Cumplir lo que ya es ley.",
            "Las ministras de la Ley 2424 y mesas\ndirectivas que reflejen "
            "a la mitad del país.")]
    y0 = 0.685
    for i, (t, s) in enumerate(pts):
        y = y0 - i * 0.155
        fig.text(0.065, y, t, fontsize=26, color=AMAR, va="top", **TITLE_F)
        fig.text(0.065, y - 0.052, s, fontsize=18.5, color="#f0e0e9",
                 va="top", linespacing=1.35)
    fig.text(0.058, 0.215, "Proyecto por proyecto,", fontsize=42,
             color=LILA, va="top", fontproperties=F_TURB)
    fig.text(0.058, 0.152, "aplazamiento por aplazamiento.", fontsize=42,
             color=LILA, va="top", fontproperties=F_TURB)
    foot(fig, n, dark=True)
    save(fig, "10_cierre.png")


SLIDES = {"portada": s01, "curva": s02, "record": s03, "poder": s04,
          "embudo": s05, "sin_debate": s06, "turno": s07, "ellas": s08,
          "ventana": s09, "cierre": s10}
ORDER = list(SLIDES)

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    todo = ORDER if args == ["all"] else args
    for k in todo:
        SLIDES[k](N(ORDER.index(k) + 1))
