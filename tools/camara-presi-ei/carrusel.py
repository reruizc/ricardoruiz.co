#!/usr/bin/env python3
"""Genera el hilo visual: 12 imágenes Twitter (1200x900) + 10 Instagram (1080x1080).
Tema: a dónde fue en la 1V el voto de cada lista que eligió Cámara/Senado por
Bogotá, a propósito de la noticia Juvinao+Claudia López -> Cepeda.

Identidad de los carruseles del proyecto (Arima + kicker oxblood) PERO fondo
AZUL MUY CLARO en vez del papel salmón. Cepeda rojo / Abelardo azul.

  python3 carrusel.py            # ambos
  python3 carrusel.py tw|ig      # uno
"""
import os, sys, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "edad-1v-2026", "fonts")
for f in ("Arima-Bold.ttf", "Arima-SemiBold.ttf"):
    fp = os.path.join(FONTS, f)
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
ARIMA = fm.FontProperties(family="Arima", weight="bold")
plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]

# ---- paleta: fondo azul muy claro ----
BG   = "#e7eef9"     # azul muy claro (antes papel #f1eee4)
FG   = "#15233b"     # tinta navy
SUB  = "#566479"     # subtítulos
INK3 = "#8b97a8"
OX   = "#8a1e16"     # oxblood: kickers/acentos
CEP  = "#d1322e"     # Cepeda / izquierda
ABE  = "#1f47cc"     # Abelardo / derecha
RES  = "#9aa1ad"     # resto (gris azulado)
CARD = "#f3f7fd"     # tarjeta clara sobre el fondo

TW = (1200, 900); IG = (1080, 1080)
PHOTO = os.path.join(HERE, "assets", "captura_juvinao.png")   # foto de contexto (portada)

# ---------- datos ----------
CAM = [  # (lista, cepeda, abelardo, resto, sublabel)
 ("Pacto Histórico", 77, 9, 14, "8 representantes electos"),
 ("Partido Liberal", 40, 39, 21, "Bleidy Pérez"),
 ("Alianza Verde", 36, 40, 24, "Juvinao · Toro"),
 ("Salvación Nacional", 30, 47, 23, "Carol Borda"),
 ("Centro Democrático", 14, 61, 25, "5 reps. menores"),
 ("Daniel Briceño", 13, 60, 27, "voto preferente propio"),
]
# Senado NACIONAL · 7 senadores electos más votados (EI individual por mesa, por depto)
SEN7 = [  # (nombre, cep, abe, res, sublabel=lista)
 ("Yessid Pulgar", 49, 38, 13, "Liberal · Caribe"),
 ("Nadya Blel", 44, 44, 12, "Conservador"),
 ("Lidio García", 41, 45, 14, "Liberal"),
 ("Señor Bíter", 41, 43, 16, "Liberal · G. Vargas"),
 ("Jota Pe Hernández", 40, 44, 16, "Alianza por Colombia"),
 ("Jennifer Pedraza", 39, 44, 17, "Ahora Colombia"),
 ("Enrique Gómez", 38, 46, 16, "Salvación Nacional"),
]

# ---------- helpers ----------
def fig_new(size):
    w, h = size
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG)
    return fig

def wrap(t, n): return "\n".join(textwrap.wrap(t, n))

def header(fig, kicker, title, sub=None, ky=0.93, tsize=46, ty=0.865, sy=None, subn=64):
    fig.text(0.065, ky, kicker.upper(), color=OX, fontsize=15.5, fontweight="bold",
             ha="left", va="top")
    fig.text(0.065, ty, title, color=FG, fontsize=tsize, ha="left", va="top",
             fontproperties=ARIMA, linespacing=1.05)
    if sub:
        fig.text(0.065, sy if sy else ty - 0.135, wrap(sub, subn), color=SUB,
                 fontsize=16.5, ha="left", va="top", linespacing=1.45)

def footer(fig, handle, src):
    fig.text(0.065, 0.052, src, color=INK3, fontsize=11.5, ha="left", va="center")
    fig.text(0.935, 0.052, f"{handle}   ·   ricardoruiz.co", color=FG, fontsize=13,
             ha="right", va="center", fontweight="bold")
    fig.lines.append(plt.Line2D([0.065, 0.935], [0.085, 0.085], color="#c4cfdf",
                     lw=1.0, transform=fig.transFigure))

def legend(fig, y=0.11, x=0.065):
    items = [("Cepeda", CEP), ("otro / blanco-nulo", RES), ("Abelardo", ABE)]
    dx = x
    for lab, col in items:
        fig.patches.append(plt.Rectangle((dx, y), 0.018, 0.022, color=col,
                           transform=fig.transFigure, zorder=5))
        fig.text(dx + 0.024, y + 0.011, lab, color=FG, fontsize=12.5, va="center")
        dx += 0.024 + 0.012 * len(lab) + 0.03

def bars(fig, rows, rect, lab_size=15, val_size=14.5, show_sub=True):
    ax = fig.add_axes(rect); ax.set_facecolor("none")
    n = len(rows); ax.set_xlim(0, 100); ax.set_ylim(-0.5, n - 0.5); ax.invert_yaxis()
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_xticks([])
    labs = []
    for i, (lab, cep, abe, res, sub) in enumerate(rows):
        tot = cep + abe + res
        c, a, r = cep / tot * 100, abe / tot * 100, res / tot * 100
        ax.barh(i, c, color=CEP, height=0.62)
        ax.barh(i, r, left=c, color=RES, height=0.62)
        ax.barh(i, a, left=c + r, color=ABE, height=0.62)
        ax.text(c / 2, i, f"{round(cep)}", color="white", ha="center", va="center",
                fontsize=val_size, fontweight="bold")
        ax.text(c + r + a / 2, i, f"{round(abe)}", color="white", ha="center",
                va="center", fontsize=val_size, fontweight="bold")
        if r > 7:
            ax.text(c + r / 2, i, f"{round(res)}", color="#3c4350", ha="center",
                    va="center", fontsize=val_size - 1, fontweight="bold")
        labs.append((lab, sub))
    ax.set_yticks(range(n))
    ax.set_yticklabels([l for l, _ in labs], fontproperties=ARIMA, fontsize=lab_size,
                       color=FG)
    ax.tick_params(length=0)
    if show_sub:
        for i, (_, sub) in enumerate(labs):
            if sub:
                ax.annotate(sub, (0, i), xytext=(-12, -16), textcoords="offset points",
                            ha="right", va="center", fontsize=10.5, color=INK3)
    return ax

def bignum(fig, num, unit, desc, color=CEP, x=0.065, y=0.55):
    fig.text(x, y, num, color=color, fontsize=180, ha="left", va="center",
             fontproperties=ARIMA)
    # ancho aproximado del número para colocar la unidad
    fig.text(x, y - 0.20, desc, color=FG, fontsize=22, ha="left", va="top",
             fontproperties=ARIMA, linespacing=1.1)

def _resolve(path):
    if os.path.exists(path):
        return path
    stem = os.path.splitext(path)[0]
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG", ".webp"):
        if os.path.exists(stem + ext):
            return stem + ext
    return path

def place_photo(fig, path, rect, caption=None):
    path = _resolve(path)
    ax = fig.add_axes(rect); ax.axis("off")
    w, h = fig.get_size_inches() * fig.dpi
    tgt = (rect[2] * w) / (rect[3] * h)         # aspecto destino (ancho/alto)
    if os.path.exists(path):
        try:
            from PIL import Image
            import numpy as np
            img = np.asarray(Image.open(path).convert("RGB"))
            H, W = img.shape[:2]; src = W / H
            if src > tgt:
                nw = int(H * tgt); x0 = (W - nw) // 2; img = img[:, x0:x0 + nw]
            else:
                nh = int(W / tgt); y0 = (H - nh) // 2; img = img[y0:y0 + nh, :]
            ax.imshow(img, aspect="auto")
        except Exception as e:
            ax.text(0.5, 0.5, f"(foto: {e})", ha="center", va="center", fontsize=10)
    else:
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc="#cdd7e6", ec="#9fb0c6", lw=1.5,
                     transform=ax.transAxes))
        ax.text(0.5, 0.5, "foto Juvinao\n(guardar en assets/juvinao.jpg)", ha="center",
                va="center", color="#5a6678", fontsize=12.5, transform=ax.transAxes)
    for s in ax.spines.values():
        s.set_visible(True); s.set_edgecolor("#ffffff"); s.set_linewidth(3)
    if caption:
        ax.text(0.5, -0.06, caption, ha="center", va="top", color=INK3, fontsize=11,
                transform=ax.transAxes)

def save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    print("  ·", os.path.relpath(path, HERE))

SRC_CAM = "Escrutinio Cámara Bogotá 8-mar + preconteo 1V · RNEC · EI por mesa (16.551)"
SRC_SEN = "Escrutinio Senado nacional 8-mar + preconteo 1V · RNEC · EI por mesa, por depto"

# ======================================================================
#  SLIDES  (cada función recibe size + handle y devuelve fig)
# ======================================================================
def s01_portada(size, handle):
    ig = size[0] == size[1]
    fig = fig_new(size)
    fig.text(0.065, 0.93, "BOGOTÁ · A DÓNDE FUE TU VOTO", color=OX,
             fontsize=15 if ig else 16, fontweight="bold", va="top")
    if ig:
        fig.text(0.065, 0.86, "El centro camina\nhacia Cepeda.\nSu voto se quedó\ncon Abelardo.",
                 color=FG, fontsize=47, va="top", fontproperties=ARIMA, linespacing=1.06)
        fig.text(0.065, 0.535, wrap("Juvinao y Claudia López negocian con Cepeda. Crucé "
                 "mesa a mesa el voto de Bogotá con la presidencial 1V.", 58),
                 color=SUB, fontsize=15.5, va="top", linespacing=1.4)
        place_photo(fig, PHOTO, [0.065, 0.10, 0.87, 0.34],
                    caption="Catherine Juvinao · La FM, 16 jun 2026")
    else:
        fig.text(0.065, 0.83, "El centro\ncamina hacia\nCepeda.\nSu voto se quedó\ncon Abelardo.",
                 color=FG, fontsize=46, va="top", fontproperties=ARIMA, linespacing=1.06)
        fig.text(0.065, 0.21, wrap("Juvinao y Claudia López negocian con Iván Cepeda. "
                 "Crucé mesa a mesa el voto de Bogotá (Cámara y Senado) con la "
                 "presidencial 1V para ver a dónde fue cada electorado.", 44),
                 color=SUB, fontsize=15.5, va="top", linespacing=1.4)
        place_photo(fig, PHOTO, [0.61, 0.205, 0.36, 0.60],
                    caption="Catherine Juvinao · La FM, 16 jun 2026")
    footer(fig, handle, "Un análisis de datos de Ricardo Ruiz")
    return fig

def s02_noticia(size, handle):
    fig = fig_new(size)
    header(fig, "El detonante", "Juvinao y Claudia,\nrumbo a Cepeda", tsize=50, ty=0.86)
    # cita del trino (estilo X): cuenta + texto + atribución, sin foto
    ax = fig.add_axes([0.065, 0.275, 0.87, 0.345]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.0, 0.0), 1, 1, boxstyle="round,pad=0.015,rounding_size=0.04",
                 fc="#ffffff", ec="#cdd7e6", lw=1.3, transform=ax.transAxes))
    ax.add_patch(plt.Rectangle((0.0, 0.0), 0.012, 1, fc=ABE, transform=ax.transAxes))
    ax.text(0.045, 0.82, "La FM", color=FG, fontsize=16, fontweight="bold",
            transform=ax.transAxes)
    ax.text(0.115, 0.82, "@lafm · 16 jun 2026", color=INK3, fontsize=12.5, va="center_baseline",
            transform=ax.transAxes)
    ax.text(0.93, 0.82, "𝕏", color=FG, fontsize=18, ha="right", transform=ax.transAxes)
    ax.text(0.045, 0.60, wrap("Tras aprobarse la escisión que le permite la salida del "
            "Partido Verde, la representante Catherine Juvinao confirma que ella y la "
            "exalcaldesa Claudia López están a la espera de suscribir un acuerdo "
            "programático con el candidato Iván Cepeda.", 62), color=FG, fontsize=15.5,
            va="top", transform=ax.transAxes, linespacing=1.42)
    fig.text(0.065, 0.205, "¿Las sigue su electorado?", color=OX, fontsize=24,
             fontproperties=ARIMA, va="top")
    footer(fig, handle, "Cita: trino de @lafm · 16 jun 2026")
    return fig

def s03_metodo(size, handle):
    fig = fig_new(size)
    header(fig, "Cómo se mide", "Mesa a mesa,\nno es una encuesta", tsize=50, ty=0.86,
           sub="Inferencia ecológica mesa a mesa. Como marzo y mayo son el mismo año, en "
           "cada mesa votaron las mismas cédulas. Cámara: 16.551 mesas de Bogotá. Senado: "
           "todo el país. Estimamos a dónde fue, en la 1ª vuelta, el voto de cada lista o "
           "senador electo.", sy=0.50, subn=66)
    fig.text(0.065, 0.235, "Cepeda 41% · Abelardo 37% · resto 21%", color=FG,
             fontsize=18, fontproperties=ARIMA, va="top")
    fig.text(0.065, 0.195, "así votó Bogotá en la 1ª vuelta (entre quienes votaron)",
             color=SUB, fontsize=14, va="top")
    footer(fig, handle, "Inferencia ecológica · King's EI regularizada")
    return fig

def s04_camara(size, handle):
    fig = fig_new(size)
    header(fig, "Cámara → presidencial", "A dónde fue el voto\nde cada lista", tsize=44,
           ty=0.875, sy=None)
    legend(fig, y=0.115)
    bars(fig, CAM, [0.30, 0.20, 0.64, 0.52])
    footer(fig, handle, SRC_CAM)
    return fig

def s05_pacto(size, handle):
    fig = fig_new(size)
    header(fig, "La izquierda", "El Pacto se fue\nen bloque con Cepeda", tsize=48, ty=0.90)
    fig.text(0.065, 0.50, "77%", color=CEP, fontsize=178, va="center",
             fontproperties=ARIMA)
    fig.text(0.62, 0.52, wrap("de los votantes del Pacto Histórico en Bogotá "
             "votaron por Cepeda en la 1ª vuelta.", 26), color=FG, fontsize=22,
             va="center", fontproperties=ARIMA, linespacing=1.2)
    fig.text(0.065, 0.205, wrap("En las mesas donde el Pacto es fuerte, Cepeda sacó "
             "45%. Pero sus votantes propios fueron mucho más cepedistas: la izquierda "
             "se consolidó en un solo candidato.", 72), color=SUB, fontsize=15.5,
             va="top", linespacing=1.4)
    footer(fig, handle, SRC_CAM)
    return fig

def s06_derecha(size, handle):
    fig = fig_new(size)
    header(fig, "La derecha", "Toda con Abelardo", tsize=48, ty=0.90)
    bars(fig, [CAM[5], CAM[4], CAM[3]], [0.34, 0.345, 0.60, 0.37], lab_size=15)  # Briceño, CD, Salvación
    legend(fig, y=0.265)
    fig.text(0.065, 0.185, wrap("Daniel Briceño —el más votado a la Cámara por Bogotá— "
             "se fue 60% con Abelardo, 13% con Cepeda. El resto del Centro Democrático y la "
             "lista de Salvación Nacional (Carol Borda), igual a la derecha.", 74),
             color=SUB, fontsize=15, va="top", linespacing=1.4)
    footer(fig, handle, SRC_CAM)
    return fig

def s07_juvinao(size, handle):
    fig = fig_new(size)
    header(fig, "El nudo", "El voto de Juvinao\nse inclinó a Abelardo", tsize=46, ty=0.90)
    fig.text(0.065, 0.52, "40%", color=ABE, fontsize=168, va="center", fontproperties=ARIMA)
    fig.text(0.60, 0.565, wrap("de los votantes de Catherine Juvinao (Alianza Verde) "
             "votaron Abelardo en la 1ª vuelta.", 24), color=FG, fontsize=21, va="center",
             fontproperties=ARIMA, linespacing=1.2)
    fig.text(0.60, 0.40, "Solo 36% votó Cepeda.", color=CEP, fontsize=20, va="center",
             fontproperties=ARIMA)
    fig.text(0.065, 0.205, wrap("Juvinao se mueve hacia Cepeda. Pero su propio electorado, "
             "en mayo, miró al otro lado. Sumar dirigentes no es lo mismo que sumar votantes.",
             76), color=OX, fontsize=16.5, va="top", linespacing=1.4)
    footer(fig, handle, SRC_CAM)
    return fig

def s07b_juvinao_demo(size, handle):
    fig = fig_new(size)
    header(fig, "El perfil · Juvinao", "Ni más joven\nni más femenina", tsize=46, ty=0.90)
    rows = [("Mujeres", 55, 57), ("Jóvenes 18-35", 29, 30), ("Mayores 61+", 22, 22)]
    for i, (lab, jv, bg) in enumerate(rows):
        yy = 0.585 - i * 0.125
        fig.text(0.065, yy, lab, color=SUB, fontsize=16.5, va="center")
        fig.text(0.50, yy, f"{jv}%", color=FG, fontsize=38, va="center",
                 fontproperties=ARIMA, ha="right")
        fig.text(0.535, yy, f"vs {bg}% en Bogotá", color=INK3, fontsize=14, va="center")
    fig.text(0.065, 0.165, wrap("El electorado de Juvinao es casi un calco del de Bogotá. "
             "El voto joven que sugiere la marca Verde no aparece: es de mediana edad y "
             "apenas un poco más masculino que el promedio.", 78), color=OX, fontsize=15.5,
             va="top", linespacing=1.4)
    footer(fig, handle, "Mesa-EF (efectos fijos de puesto) · estructura demográfica 2022 → 2026 · RNEC")
    return fig

def s08_centro(size, handle):
    fig = fig_new(size)
    header(fig, "El centro", "El votante más\nparejo de Bogotá", tsize=46, ty=0.90)
    bars(fig, [CAM[1]], [0.30, 0.52, 0.64, 0.13], lab_size=17)   # solo Liberal (Bleidy)
    legend(fig, y=0.42)
    fig.text(0.065, 0.31, wrap("El electorado liberal de Bleidy Pérez se repartió casi por "
             "mitades: 40% Cepeda, 39% Abelardo. El único de Bogotá que no se inclinó "
             "claramente a ningún lado.", 70), color=FG, fontsize=18, va="top",
             fontproperties=ARIMA, linespacing=1.3)
    footer(fig, handle, SRC_CAM)
    return fig

def s09_senado(size, handle):
    fig = fig_new(size)
    header(fig, "Senado · nacional · electos", "Los 7 senadores\nmás votados del país", tsize=38,
           ty=0.885)
    legend(fig, y=0.745)
    bars(fig, SEN7, [0.30, 0.125, 0.64, 0.585], lab_size=14)
    footer(fig, handle, SRC_SEN)
    return fig

def s10_sen_insight(size, handle):
    fig = fig_new(size)
    header(fig, "El contraste", "Hasta los\nindependientes", tsize=48, ty=0.90)
    bars(fig, [SEN7[4], SEN7[5]], [0.36, 0.46, 0.58, 0.19], lab_size=15)   # Jota Pe · Pedraza
    legend(fig, y=0.385)
    fig.text(0.065, 0.275, wrap("El voto de Jota Pe Hernández (independiente) y de Jennifer "
             "Pedraza (centro-izquierda) también se fue con Abelardo. De los 7, el único cuyo "
             "electorado se inclinó a Cepeda fue Yessid Pulgar, liberal del Caribe.", 70),
             color=SUB, fontsize=15.5, va="top", linespacing=1.4)
    fig.text(0.065, 0.135, "Yessid Pulgar · 49% Cepeda — la excepción.", color=OX,
             fontsize=16.5, va="top", fontproperties=ARIMA)
    footer(fig, handle, SRC_SEN)
    return fig

def s11_lectura(size, handle):
    fig = fig_new(size)
    header(fig, "La lectura", "El reto del acuerdo", tsize=52, ty=0.90)
    fig.text(0.065, 0.62, wrap("Fuera del núcleo del Pacto, casi todo Bogotá se inclinó "
             "a Abelardo en la 1ª vuelta —incluido el voto de las listas cuyos "
             "dirigentes hoy caminan hacia Cepeda.", 56), color=FG, fontsize=27,
             va="top", fontproperties=ARIMA, linespacing=1.25)
    fig.text(0.065, 0.30, wrap("El acuerdo con Juvinao y Claudia López le suma figuras. "
             "Convertir eso en votos —los de sus propios electorados, que en mayo "
             "miraron al otro lado— es la verdadera tarea de cara a la 2ª vuelta.", 70),
             color=SUB, fontsize=16, va="top", linespacing=1.45)
    footer(fig, handle, "Análisis · Ricardo Ruiz")
    return fig

def s12_ficha(size, handle):
    fig = fig_new(size)
    header(fig, "Cómo se hizo", "Ficha técnica", tsize=50, ty=0.90)
    txt = ("Inferencia ecológica (King's EI regularizada) a nivel de MESA: las mismas "
           "cédulas votaron en marzo y mayo. Cámara: 16.551 mesas de Bogotá. Senado: "
           "106 mil mesas de todo el país, estimación estratificada por departamento.\n\n"
           "Se estima a dónde fue el voto de cada lista (Cámara) o de cada senador electo "
           "(Senado) entre quienes volvieron a votar. En Cámara los co-partidarios de una "
           "lista comparten perfil; los senadores con base regional se identifican uno a uno.\n\n"
           "Fuentes: escrutinio Cámara y Senado del 8-mar + preconteo presidencial 1V del "
           "31-may (Registraduría).")
    fig.text(0.065, 0.74, wrap(txt, 74).replace("\n\n", "\n \n"), color=SUB,
             fontsize=15.5, va="top", linespacing=1.5)
    footer(fig, handle, "ricardoruiz.co")
    return fig

TW_SLIDES = [s01_portada, s02_noticia, s03_metodo, s04_camara, s05_pacto, s06_derecha,
             s07_juvinao, s07b_juvinao_demo, s08_centro, s09_senado, s10_sen_insight,
             s11_lectura, s12_ficha]
# IG: 11 piezas (sin método ni ficha; cierre fusiona lectura)
IG_SLIDES = [s01_portada, s02_noticia, s04_camara, s05_pacto, s06_derecha, s07_juvinao,
             s07b_juvinao_demo, s08_centro, s09_senado, s10_sen_insight, s11_lectura]

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("tw", "both"):
        print("Twitter (@RicardoRuiz_):")
        for i, fn in enumerate(TW_SLIDES, 1):
            save(fn(TW, "@RicardoRuiz_"), os.path.join(HERE, "out", "twitter", f"tw-{i:02d}.png"))
    if which in ("ig", "both"):
        print("Instagram (@RicardoeRuiz_):")
        for i, fn in enumerate(IG_SLIDES, 1):
            save(fn(IG, "@RicardoeRuiz_"), os.path.join(HERE, "out", "instagram", f"ig-{i:02d}.png"))

if __name__ == "__main__":
    main()
