# -*- coding: utf-8 -*-
"""
Carrusel Instagram (10 slides · 1080x1080) — Herramientas anticorrupción.
Portada full-bleed + 9 slides de análisis. Fuente SERIA Times New Roman,
paleta AZUL, paper #f1eee4.

Rediseño v3 (jun-2026): texto JUSTIFICADO (motor propio por palabra vía
TextPath), jerarquía de tamaños, pull-quotes grandes en bloque azul y
palabras clave resaltadas dentro del cuerpo. Slide 2 gira sobre la paradoja
"más leyes ≠ menos corrupción" (Mungiu-Pippidi), no sobre el ranking.

Corre: python3 tools/anticorrupcion/build_carrusel_ig.py
Salida: rrss/instagram/carrusel-anticorrupcion/01..10.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from matplotlib.textpath import TextPath
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
OUT = os.path.join(ROOT, 'rrss/instagram/carrusel-anticorrupcion')
LOGO = os.path.join(ROOT, 'Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png')
os.makedirs(OUT, exist_ok=True)

TNR_DIR = '/System/Library/Fonts/Supplemental'
_tnr = os.path.join(TNR_DIR, 'Times New Roman.ttf')
_tnrb = os.path.join(TNR_DIR, 'Times New Roman Bold.ttf')
_tnri = os.path.join(TNR_DIR, 'Times New Roman Italic.ttf')
for f in (_tnr, _tnrb, _tnri):
    if os.path.exists(f):
        fm.fontManager.addfont(f)
AR = fm.FontProperties(fname=_tnrb)
SANS = fm.FontProperties(fname=_tnr)
SANSB = fm.FontProperties(fname=_tnrb)
ITAL = fm.FontProperties(fname=_tnri)

PAPER = '#f1eee4'; INK = '#1a1510'; MUT = '#6b6258'; BODY = '#241f19'
BLUE = '#17457e'; MID = '#2f6e8e'; STEEL = '#4d6b86'
BAND = '#e7e0d0'; BLUEBAND = '#e2e8f0'; CARD = '#e4dfd1'
N = 10
FIGW_PT = 10.8 * 72.0  # ancho de figura en puntos (para justificar)

plt.rcParams['font.family'] = 'serif'
plt.rcParams['text.color'] = INK


# ---------- medición / justificación ----------
def _tw(s, fs, prop):
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=fs, prop=prop).get_extents().width / FIGW_PT


def _spw(fs, prop):
    return _tw('a a', fs, prop) - _tw('aa', fs, prop)


def _norm(w):
    return ''.join(c for c in w.lower() if c.isalnum())


def jtext(fig, text, y0, x0, x1, fs, dy, color=BODY, prop=SANS, propb=SANSB,
          hot=frozenset(), hot_color=BLUE):
    """Párrafo JUSTIFICADO. Envuelve por ancho y estira cada línea salvo la
    última. Palabras en `hot` (token normalizado) salen bold + hot_color."""
    maxw = x1 - x0
    sp = _spw(fs, prop)
    words = text.split()
    lines, cur, cw = [], [], 0.0
    for w in words:
        ww = _tw(w, fs, propb if _norm(w) in hot else prop)
        if not cur:
            cur, cw = [w], ww
        elif cw + sp + ww <= maxw:
            cur.append(w); cw += sp + ww
        else:
            lines.append(cur); cur, cw = [w], ww
    if cur:
        lines.append(cur)
    for li, ws in enumerate(lines):
        y = y0 - li * dy
        last = (li == len(lines) - 1)
        widths = [_tw(w, fs, propb if _norm(w) in hot else prop) for w in ws]
        if last or len(ws) == 1:
            gap = sp
        else:
            gap = (maxw - sum(widths)) / (len(ws) - 1)
        x = x0
        for w, ww in zip(ws, widths):
            h = _norm(w) in hot
            fig.text(x, y, w, fontsize=fs, fontproperties=(propb if h else prop),
                     color=(hot_color if h else color), va='top', ha='left')
            x += ww + gap
    return len(lines)


# ---------- chasis ----------
def canvas():
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(PAPER)
    return fig


def chrome(fig, n):
    lg = Image.open(LOGO).convert('RGBA'); r = lg.height / lg.width
    w = 0.20
    axl = fig.add_axes([0.066, 0.034, w, w * r]); axl.imshow(lg); axl.axis('off')
    fig.text(0.934, 0.045, 'ricardoruiz.co', fontsize=16, color=MUT,
             fontproperties=SANSB, ha='right', va='center')
    fig.text(0.5, 0.045, f'{n} / {N}', fontsize=14, color=MUT, fontproperties=SANS,
             ha='center', va='center')


def kicker(fig, t, y=0.945, color=BLUE):
    fig.text(0.066, y, ' '.join(t), fontsize=16, color=color, fontproperties=SANSB,
             va='center')


def title(fig, t, y=0.9, fs=58, color=INK):
    fig.text(0.066, y, t, fontsize=fs, color=color, fontproperties=AR, va='top',
             linespacing=1.03)


def band(fig, y, h, x=0.066, w=0.868, fc=BAND, tick=None):
    fig.patches.append(Rectangle((x, y), w, h, transform=fig.transFigure,
                                 facecolor=fc, edgecolor='none'))
    if tick:
        fig.patches.append(Rectangle((x, y), 0.013, h, transform=fig.transFigure,
                                     facecolor=tick, edgecolor='none'))


def pullblock(fig, y, h, lines, fs, fc=BLUEBAND, tick=BLUE, color=BLUE, x=0.066,
              w=0.868, lh=None):
    """Bloque de cita/pull-quote grande."""
    band(fig, y, h, x=x, w=w, fc=fc, tick=tick)
    lh = lh or (fs * 1.14 / FIGW_PT)
    n = len(lines)
    ytop = y + h / 2 + (n - 1) * lh / 2
    for i, ln in enumerate(lines):
        fig.text(x + 0.035, ytop - i * lh, ln, fontsize=fs, color=color,
                 fontproperties=SANSB, va='center')


# =====================================================================
# 01 · PORTADA
# =====================================================================
def portada(n):
    fig = canvas()
    im = Image.open(os.path.join(ASSETS, 'portada-bg.jpeg')).convert('RGB')
    im = im.crop((430, 0, 1030, 600))
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.axis('off'); ax.set_zorder(0)
    axd = fig.add_axes([0, 0, 1, 1]); axd.axis('off'); axd.set_zorder(1)
    axd.add_patch(Rectangle((0, 0), 1, 1, facecolor='#0b1a2b', alpha=0.20))
    grad = np.zeros((256, 1, 4)); grad[:, 0, 3] = np.linspace(0.0, 0.93, 256)
    axg = fig.add_axes([0, 0, 1, 0.66]); axg.set_zorder(2)
    axg.imshow(grad, extent=[0, 1, 0, 1], aspect='auto'); axg.axis('off')
    fig.text(0.066, 0.95, ' '.join('HERRAMIENTAS ANTICORRUPCIÓN'), fontsize=15.5,
             color='#bcd3e4', fontproperties=SANSB, va='center')
    # título grande (hero): la frase de acción
    tl = ['Tres elementos', 'anticorrupción que', 'Abelardo puede', 'cambiar']
    ty0, tdy, tfs = 0.485, 0.068, 58
    for i, ln in enumerate(tl):
        fig.text(0.066, ty0 - i * tdy, ln, fontsize=tfs, color='#f6f3ec',
                 fontproperties=AR, va='top')
    _xya = 0.066 + _tw('cambiar', tfs, AR) + _spw(tfs, AR)
    fig.text(_xya, ty0 - 3 * tdy, 'YA', fontsize=tfs, color='#7fb2e0',
             fontproperties=AR, va='top')
    # subtítulo pequeño abajo
    fig.text(0.066, 0.15, 'Antes de acusar, hay que poder ver.', fontsize=26,
             color='#cdd9e4', fontproperties=SANS, va='top')
    fig.text(0.066, 0.045, 'Ricardo Ruiz', fontsize=17, color='#eef2f5',
             fontproperties=SANSB, va='center')
    fig.text(0.5, 0.045, f'{n} / {N}', fontsize=14, color='#c7d3dd', fontproperties=SANS,
             ha='center', va='center')
    fig.text(0.934, 0.045, 'ricardoruiz.co', fontsize=16, color='#eef2f5',
             fontproperties=SANSB, ha='right', va='center')
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d} portada')


# =====================================================================
# 02 · diagnóstico → la paradoja (más leyes ≠ menos corrupción)
# =====================================================================
def s_diag(n):
    fig = canvas(); kicker(fig, 'EL DIAGNÓSTICO')
    title(fig, 'El problema no es\nfalta de leyes', y=0.9, fs=64)
    pullblock(fig, 0.545, 0.16,
              ['Los países más corruptos son,', 'justamente, los que más leyes tienen.'],
              fs=31)
    jtext(fig,
          'Décadas de estudios de Alina Mungiu-Pippidi muestran que crear otra '
          'agencia o expedir otra ley, por sí sola, no mueve la aguja. La llaman '
          'la brecha de implementación: mucha norma en el papel, poco control '
          'real en la práctica.',
          y0=0.47, x0=0.066, x1=0.934, fs=25, dy=0.052,
          hot=frozenset({_norm('brecha'), _norm('implementación'),
                         _norm('implementacion')}))
    fig.text(0.066, 0.135, 'El discurso anticorrupción sobra. Lo que falta es',
             fontsize=20, color=MUT, fontproperties=ITAL, va='center')
    fig.text(0.066, 0.104, 'infraestructura para ver.', fontsize=20, color=MUT,
             fontproperties=ITAL, va='center')
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 03 · la tesis · 3 cambios sin Congreso
# =====================================================================
def s_tesis(n):
    fig = canvas(); kicker(fig, 'LA TESIS')
    title(fig, 'Tres cambios,\ncero leyes nuevas', y=0.9, fs=60)
    jtext(fig,
          'Acusar sin capacidad de ver termina en cacería, no en control. Estas '
          'tres cosas el presidente las puede ordenar por decreto, sin pedirle '
          'permiso al Congreso:',
          y0=0.665, x0=0.066, x1=0.934, fs=23, dy=0.049,
          hot=frozenset({_norm('decreto'), _norm('Congreso')}))
    items = [('1', 'Integrar la información del Estado'),
             ('2', 'Meterle IA de control ciudadano al nuevo SECOP'),
             ('3', 'Que la alerta detenga el cheque')]
    y = 0.475
    for num, txt in items:
        band(fig, y - 0.052, 0.088, tick=MID, fc=BLUEBAND)
        fig.text(0.10, y - 0.008, num, fontsize=40, color=MID, fontproperties=AR,
                 va='center')
        fig.text(0.185, y - 0.008, txt, fontsize=23.5, color=INK, fontproperties=SANSB,
                 va='center')
        y -= 0.108
    fig.text(0.066, 0.125, 'Una columna vertebral: la integralidad de la información.',
             fontsize=20, color=BLUE, fontproperties=ITAL, va='center')
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 04 · cambio 1 · integralidad (once-only)
# =====================================================================
def s_integ(n):
    fig = canvas(); kicker(fig, 'CAMBIO 1 · INTEGRALIDAD', color=MID)
    title(fig, 'Que el Estado deje de\npedir lo que ya tiene', y=0.9, fs=54)
    jtext(fig,
          'Estonia lo consagró por ley hace dos décadas: si una entidad ya tiene '
          'tu dato, ninguna otra te lo puede volver a pedir. Nunca. Lo llaman '
          'once-only. Le ahorra al país cerca del 2% del PIB al año en trámites '
          'que dejaron de existir.',
          y0=0.665, x0=0.066, x1=0.934, fs=24, dy=0.051,
          hot=frozenset({_norm('once-only'), _norm('onceonly'), _norm('2')}))
    pullblock(fig, 0.145, 0.155,
              ['Y cruzar los datos', 'es la única forma de ver.'], fs=32)
    fig.text(0.066, 0.108,
             'Facilita la vida del ciudadano y, de paso, habilita la vigilancia.',
             fontsize=19.5, color=MUT, fontproperties=ITAL, va='center')
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 05 · contrafáctico · Centros Poblados
# =====================================================================
def s_cp(n):
    fig = canvas(); kicker(fig, 'SI LO HUBIÉRAMOS TENIDO')
    title(fig, 'Centros Poblados, 2021', y=0.9, fs=54)
    jtext(fig,
          'Un contrato de $1 billón para llevar internet a 7.000 comunidades '
          'rurales. El contratista lo ganó con pólizas bancarias falsas y un '
          'anticipo de $70.000 millones que terminó en una cuenta en Delaware.',
          y0=0.73, x0=0.066, x1=0.934, fs=24, dy=0.051,
          hot=frozenset({_norm('falsas'), _norm('Delaware')}))
    pullblock(fig, 0.335, 0.15,
              ['Probablemente ese anticipo', 'nunca se gira.'], fs=33)
    jtext(fig,
          'Bastaba con que el sistema verificara esa póliza contra el banco en '
          'tiempo real. No hizo falta un fiscal heroico: hizo falta que dos bases '
          'de datos se hablaran.',
          y0=0.265, x0=0.066, x1=0.934, fs=21, dy=0.044,
          hot=frozenset({_norm('tiempo'), _norm('real')}))
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 06 · cambio 2 · SECOP III
# =====================================================================
def s_secop(n):
    fig = canvas(); kicker(fig, 'CAMBIO 2 · SECOP III', color=MID)
    title(fig, 'La ventana que se\nestá cerrando', y=0.9, fs=58)
    jtext(fig,
          'Colombia construye ahora mismo el nuevo SECOP: unos $23.497 millones, '
          'código fuente del Estado, en desarrollo por fases hasta 2029. Revisé '
          'los requisitos técnicos publicados y no mencionan inteligencia '
          'artificial ni analítica de datos.',
          y0=0.675, x0=0.066, x1=0.934, fs=24, dy=0.051,
          hot=frozenset({_norm('ahora'), _norm('no'), _norm('mencionan')}))
    pullblock(fig, 0.15, 0.185,
              ['Se diseña para contratar más rápido.',
               'No para contratar más vigilable.',
               'Todavía se puede cambiar — y solo', 'depende del Ejecutivo.'],
              fs=24, lh=0.045)
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 07 · qué gana el ciudadano
# =====================================================================
def s_ciudadano(n):
    fig = canvas(); kicker(fig, 'IA SOBRE EL SECOP', color=MID)
    title(fig, 'Qué cambiaría\npara ti', y=0.9, fs=58)
    fig.text(0.066, 0.715, 'Hoy casi nadie sabe consultar el SECOP. Con IA encima:',
             fontsize=21, color=MUT, fontproperties=ITAL, va='top')
    rows = [
        ('Preguntas en español, no en SQL',
         '“¿qué contratos de mi pueblo ganó una empresa creada hace 6 meses?”'),
        ('Resúmenes en lenguaje claro',
         'un contrato de 200 páginas: qué se compró, a quién y a qué precio.'),
        ('Alertas hechas para ti',
         '“avísame si firman un contrato de un solo oferente en mi municipio.”'),
        ('Patrones que un humano no ve',
         'el mismo contratista ganándolo todo; empresas del mismo dueño compitiendo.'),
    ]
    y = 0.66
    for head, ex in rows:
        band(fig, y - 0.118, 0.108, tick=MID, fc=BLUEBAND)
        fig.text(0.095, y - 0.024, head, fontsize=23, color=BLUE, fontproperties=SANSB,
                 va='top')
        fig.text(0.095, y - 0.070, ex, fontsize=16.5, color=BODY, fontproperties=SANS,
                 va='top')
        y -= 0.138
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 08 · contrafáctico · carrotanques + DOZORRO + caveat
# =====================================================================
def s_carro(n):
    fig = canvas(); kicker(fig, 'SI LO HUBIÉRAMOS TENIDO')
    title(fig, 'Carrotanques,\nUNGRD 2023', y=0.9, fs=54)
    jtext(fig,
          '40 carrotanques para La Guajira con sobrecostos de miles de millones. '
          '¿Cómo se armó? Empresas sin experiencia, vinculadas entre sí, '
          'coordinándose para inflar los precios.',
          y0=0.70, x0=0.066, x1=0.934, fs=23, dy=0.049,
          hot=frozenset({_norm('vinculadas'), _norm('inflar')}))
    pullblock(fig, 0.40, 0.135,
              ['Ese patrón enciende un motor',
               'de banderas rojas antes del pago.'], fs=27, lh=0.05)
    jtext(fig,
          'Ya existe: DOZORRO, en Ucrania, es una IA que marca las licitaciones '
          'sospechosas y las manda a la ciudadanía. Más de 300.000 usuarios.',
          y0=0.355, x0=0.066, x1=0.934, fs=19.5, dy=0.04,
          hot=frozenset({_norm('DOZORRO')}))
    band(fig, 0.115, 0.115, fc='#e4e7e2', tick=STEEL)
    fig.text(0.095, 0.205, 'Sin sobrevender:', fontsize=19.5, color=STEEL,
             fontproperties=SANSB, va='top')
    fig.text(0.095, 0.170, 'una bandera roja no es prueba. Es una señal de dónde',
             fontsize=17.5, color=INK, fontproperties=SANS, va='top')
    fig.text(0.095, 0.142, 'mirar. El algoritmo prioriza; el humano verifica.',
             fontsize=17.5, color=INK, fontproperties=SANS, va='top')
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 09 · cambio 3 · la alerta detiene el cheque
# =====================================================================
def s_dientes(n):
    fig = canvas(); kicker(fig, 'CAMBIO 3 · LOS DIENTES')
    title(fig, 'Que la alerta\ndetenga el cheque', y=0.9, fs=58)
    jtext(fig,
          'La tecnología detecta; no sanciona. Pero cerrar el ciclo tampoco '
          'necesita al Congreso: el presidente controla la plata de su propia '
          'rama. Por decreto puede ordenar que…',
          y0=0.685, x0=0.066, x1=0.934, fs=22, dy=0.046,
          hot=frozenset({_norm('detecta'), _norm('decreto')}))
    bullets = ['Ningún contrato con bandera roja se pague hasta justificarse.',
               'Las alertas fluyan solas a Contraloría, Fiscalía y ciudadanía.',
               'Todo nazca público, salvo lo estrictamente reservado.']
    y = 0.50
    for b in bullets:
        band(fig, y - 0.038, 0.066, tick=BLUE, fc=BLUEBAND)
        fig.text(0.10, y - 0.005, b, fontsize=20, color=INK, fontproperties=SANS,
                 va='center')
        y -= 0.083
    jtext(fig,
          'Ferraz y Finan probaron en Brasil que divulgar las auditorías redujo '
          'la reelección de los corruptos. La transparencia es munición.',
          y0=0.185, x0=0.066, x1=0.934, fs=19, dy=0.04, color=MUT,
          hot=frozenset())
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


# =====================================================================
# 10 · cierre
# =====================================================================
def s_cierre(n):
    fig = canvas(); kicker(fig, 'EN RESUMEN')
    title(fig, 'Facilitar y vigilar\nno son opuestos', y=0.9, fs=58)
    jtext(fig,
          'Son el mismo diseño: un Estado que no te vuelve a pedir lo que ya '
          'tiene, un SECOP más rápido para el funcionario honesto y más '
          'transparente para el ciudadano que lo vigila, y una alerta que, en vez '
          'de archivarse, detiene el pago.',
          y0=0.685, x0=0.066, x1=0.934, fs=24, dy=0.051,
          hot=frozenset({_norm('mismo'), _norm('diseño'), _norm('diseno')}))
    pullblock(fig, 0.235, 0.17,
              ['Nada de esto pasa por el Congreso.',
               'La corrupción se combate con',
               'arquitectura, no con discursos.'], fs=27, lh=0.05)
    fig.text(0.066, 0.155, 'Y se decide hoy, mientras el sistema todavía se puede',
             fontsize=19.5, color=MUT, fontproperties=ITAL, va='top')
    fig.text(0.066, 0.126, 'modificar. Mañana será un parche.',
             fontsize=19.5, color=MUT, fontproperties=ITAL, va='top')
    chrome(fig, n)
    fig.savefig(os.path.join(OUT, f'{n:02d}.png'), facecolor=PAPER)
    plt.close(fig); print(f'OK {n:02d}')


SLIDES = [portada, s_diag, s_tesis, s_integ, s_cp, s_secop, s_ciudadano,
          s_carro, s_dientes, s_cierre]

if __name__ == '__main__':
    for i, fn in enumerate(SLIDES, 1):
        fn(i)
    print('\ncarrusel listo en', OUT)
