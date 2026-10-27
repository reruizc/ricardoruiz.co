#!/usr/bin/env python3
"""Gráficos del briefing de Candidato 360 (oct-27-2026).

Pedido de Ricardo: que el briefing no sea solo texto. Cuatro PNG que salen de
la MISMA lectura que arma el correo (`ciclo` de lectura.mjs + la captura de
redes), así que no pueden decir algo distinto del texto:

  prensa.png      de qué habló la prensa del territorio (% de titulares por tema)
  zonas.png       mapa de Bogotá: cuánto pesa cada localidad en la prioridad
  redes.png       lo que le comentan en sus publicaciones, red por red
  arquetipos.png  con qué arquetipos rinde por encima de la ciudad

Se dibujan a 2× (1200 px de ancho) para que se vean nítidos en un correo de 600.
Si falta un dato, ese gráfico simplemente no sale: nunca se inventa.

    from graficos import graficar
    rutas = graficar(ciclo, captura, salida_dir, desde, hasta)   # {clave: ruta}
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

RAIZ = Path(__file__).resolve().parents[3]
FUENTES = RAIZ / 'tools' / 'pacto-1v-2026' / 'fonts'
for f in ('Inter-Regular.ttf', 'Inter-Bold.ttf'):
    if (FUENTES / f).exists():
        font_manager.fontManager.addfont(str(FUENTES / f))
plt.rcParams.update({'font.family': 'Inter', 'font.size': 13, 'ytick.labelsize': 11, 'axes.edgecolor': '#d9d2c3', 'axes.linewidth': .8})

# Paleta de Candidato 360
TINTA, MUTED, PAPEL, CREMA = '#102238', '#637080', '#f6f1e8', '#fffdf8'
VERDE, CORAL, MENTA, GRIS = '#147c70', '#ef705d', '#b9ded2', '#b8bfc6'
RAMPA = ['#e3f1ec', '#b9ded2', '#7cc0ad', '#3f9d8a', '#147c70', '#0d5a51']   # secuencial, un solo tono

GEO_BOG = RAIZ / 'Bases de datos' / 'output_pacto_1v_2026' / 'geo' / 'BOG-LOCALIDADX.json'
NOMBRE_RED = {'x': 'X', 'instagram': 'Instagram', 'tiktok': 'TikTok', 'facebook': 'Facebook'}
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _norm(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '')) if unicodedata.category(c) != 'Mn').upper().strip()


def _titulo(s):
    # El mismo de correo_ciclo: pone la tilde de las localidades («ENGATIVA» → «Engativá»).
    import correo_ciclo
    return correo_ciclo.titulo(s)


def _rango(desde, hasta):
    return f'del {desde.day} al {hasta.day} de {MESES[hasta.month - 1]}' if desde.month == hasta.month else \
        f'del {desde.day} de {MESES[desde.month - 1]} al {hasta.day} de {MESES[hasta.month - 1]}'


def _lienzo(alto):
    fig, ax = plt.subplots(figsize=(6, alto), dpi=200)
    fig.patch.set_facecolor(CREMA)
    ax.set_facecolor(CREMA)
    return fig, ax


def _cabecera(fig, titulo, sub):
    h = fig.get_figheight()
    fig.text(.04, 1 - .14 / h, titulo, ha='left', va='top', fontsize=14.5, fontweight='bold', color=TINTA)
    fig.text(.04, 1 - .46 / h, sub, ha='left', va='top', fontsize=10.5, color=MUTED)


def _guardar(fig, ruta, pie=None):
    if pie:
        fig.text(.04, .015, pie, ha='left', va='bottom', fontsize=8.5, color=MUTED)
    fig.savefig(ruta, facecolor=fig.get_facecolor(), dpi=200)
    plt.close(fig)
    return str(ruta)


def _limpiar(ax):
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, colors=TINTA)


# ── 1. Prensa ───────────────────────────────────────────────────────────────
def prensa(ciclo, ruta, desde, hasta):
    pz = ciclo.get('prensa') or {}
    temas = [t for t in pz.get('temas') or [] if t.get('n')][:6]
    if not temas or not pz.get('N'):
        return None
    terr = ciclo.get('territorio') or 'su territorio'
    alto = 1.4 + .42 * len(temas)
    fig, ax = _lienzo(alto)
    nombres = [t['corto'][:1].upper() + t['corto'][1:] for t in temas][::-1]
    vals = [t['pct'] * 100 for t in temas][::-1]
    ns = [t['n'] for t in temas][::-1]
    barras = ax.barh(nombres, vals, height=.58, color=[VERDE if i == len(vals) - 1 else MENTA for i in range(len(vals))], edgecolor=CREMA, linewidth=1)
    for b, v, n in zip(barras, vals, ns):
        ax.text(b.get_width() + 1.2, b.get_y() + b.get_height() / 2, f'{v:.0f} %  ·  {n} titular{"es" if n != 1 else ""}',
                va='center', fontsize=10.5, color=TINTA)
    ax.set_xlim(0, max(vals) * 1.55)
    ax.set_xticks([])
    _limpiar(ax)
    ax.spines['bottom'].set_visible(False)
    fig.subplots_adjust(left=.31, right=.97, top=1 - .85 / alto, bottom=.42 / alto)
    _cabecera(fig, f'De qué habló la prensa de {terr}', f'{pz["N"]} titulares, {_rango(desde, hasta)}')
    return _guardar(fig, ruta, 'Fuente: prensa nacional y regional (Google News). Un titular puede tocar más de un tema.')


# ── 2. Zonas (mapa de Bogotá) ───────────────────────────────────────────────
def zonas(ciclo, ruta):
    """El mapa solo sale en Bogotá (la unidad son las 20 localidades). Para
    Medellín y Cartagena queda la lista del correo, que ya dice lo mismo."""
    if ciclo.get('ciudad') != 'bogota' or not GEO_BOG.exists():
        return None
    uni = ciclo.get('unidades') or []
    if not uni:
        return None
    import geopandas as gpd
    from shapely import affinity
    g = gpd.read_file(GEO_BOG)
    # Convención del proyecto: Bogotá rotada 90° a la izquierda. Sumapaz se
    # deja fuera del encuadre (es rural y aplasta la ciudad).
    g = g[g['LocNombre'].map(_norm) != 'SUMAPAZ'].copy()
    c = g.union_all().centroid
    g['geometry'] = g['geometry'].apply(lambda geo: affinity.rotate(geo, 90, origin=c))
    peso = {_norm(u['nombre']): u for u in uni}
    mx = max(u['share'] for u in uni) or 1
    def color(n):
        u = peso.get(_norm(n))
        if not u:
            return '#ece7dc'
        k = min(len(RAMPA) - 1, int(u['share'] / mx * (len(RAMPA) - 1) + .5))
        return RAMPA[max(1, k)]
    g['c'] = g['LocNombre'].map(color)
    fig, ax = plt.subplots(figsize=(6, 4.3), dpi=200)
    fig.patch.set_facecolor(CREMA)
    ax.set_facecolor(CREMA)
    g.plot(ax=ax, color=g['c'], edgecolor=CREMA, linewidth=1.4)
    ax.set_axis_off()
    # Números 1-3 en las tres localidades que más pesan
    for i, u in enumerate(uni[:3]):
        fila = g[g['LocNombre'].map(_norm) == _norm(u['nombre'])]
        if fila.empty:
            continue
        p = fila.iloc[0].geometry.representative_point()
        ax.scatter([p.x], [p.y], s=330, color=CORAL, edgecolor=CREMA, linewidth=1.6, zorder=5)
        ax.text(p.x, p.y, str(i + 1), ha='center', va='center', fontsize=10.5, fontweight='bold', color='white', zorder=6)
        ax.annotate(_titulo(u['nombre']), (p.x, p.y), xytext=(13, -2), textcoords='offset points', fontsize=10, fontweight='bold', color=TINTA, zorder=6)
    fig.subplots_adjust(left=.02, right=.98, top=.86, bottom=.13)
    fig.text(.04, .97, 'Dónde estar esta semana', ha='left', va='top', fontsize=14.5, fontweight='bold', color=TINTA)
    fig.text(.04, .905, 'Cuánto pesa cada localidad en la prioridad de este ciclo. Más oscuro, más peso.', ha='left', va='top', fontsize=10.5, color=MUTED)
    # Leyenda de la rampa
    x0, w = .04, .055
    for i, col in enumerate(RAMPA[1:]):
        fig.patches.append(plt.Rectangle((x0 + i * w, .065), w - .004, .022, transform=fig.transFigure, color=col))
    fig.text(x0, .045, 'menos', fontsize=8.5, color=MUTED, va='top')
    fig.text(x0 + 5 * w - .004, .045, 'más', fontsize=8.5, color=MUTED, va='top', ha='right')
    fig.text(.36, .076, 'En gris, fuera de la prioridad. Sumapaz no se muestra.', fontsize=8.5, color=MUTED, va='center')
    fig.savefig(ruta, facecolor=CREMA, dpi=200)
    plt.close(fig)
    return str(ruta)


# ── 3. Redes ────────────────────────────────────────────────────────────────
def redes(cap, ruta, fecha_redes=None):
    """Postura de lo que le comentan en SUS publicaciones. Es una escala con
    dos polos (a favor ↔ en contra), así que va verde · gris · coral, y cada
    tramo lleva su cifra: el color nunca va solo."""
    filas = []
    for red, R in ((cap or {}).get('redes') or {}).items():
        if not R or R.get('estado') != 'ok':
            continue
        C = R.get('comentarios_propios') or {}
        p = C.get('postura') or {}
        n = int(C.get('n') or 0)
        if n < 5:
            continue   # 3 comentarios no son una postura
        filas.append((NOMBRE_RED.get(red, red), int(p.get('a_favor') or 0), int(p.get('neutro') or 0),
                      int(p.get('en_contra') or 0) + int(p.get('ataque') or 0), n))
    if not filas:
        return None
    filas.sort(key=lambda f: -f[4])
    alto = 1.6 + .5 * len(filas)
    fig, ax = _lienzo(alto)
    for i, (nombre, fav, neu, hos, n) in enumerate(reversed(filas)):
        izq = 0
        for v, col, txt in ((fav, VERDE, 'white'), (neu, GRIS, TINTA), (hos, CORAL, TINTA)):
            w = v / n * 100
            if w <= 0:
                continue
            ax.barh(i, w, left=izq, height=.56, color=col, edgecolor=CREMA, linewidth=1.5)
            if w >= 7:
                ax.text(izq + w / 2, i, str(v), ha='center', va='center', fontsize=10, fontweight='bold', color=txt)
            izq += w
        # Lo que en contra queda chico no lleva cifra dentro: se dice al lado.
        ax.text(101.5, i, f'{n} comentarios' + (f' · {hos} en contra' if hos and hos / n * 100 < 7 else ''), va='center', fontsize=9, color=MUTED)
    ax.set_yticks(range(len(filas)), [f[0] for f in reversed(filas)])
    ax.set_xlim(0, 168)
    ax.set_xticks([])
    _limpiar(ax)
    ax.spines['bottom'].set_visible(False)
    fig.subplots_adjust(left=.17, right=.98, top=1 - 1.12 / alto, bottom=.5 / alto)
    _cabecera(fig, 'Lo que le comentan en sus publicaciones', 'Cuántos comentarios van a favor, neutros o en contra, red por red')
    # Leyenda (identidad nunca solo por color)
    for j, (col, txt) in enumerate(((VERDE, 'a favor'), (GRIS, 'neutro'), (CORAL, 'en contra o en ataque'))):
        x = .17 + j * .2
        fig.patches.append(plt.Rectangle((x, 1 - .95 / alto - .02), .022, .022 * 6 / alto * 1.6, transform=fig.transFigure, color=col))
        fig.text(x + .03, 1 - .95 / alto - .02 + .011 * 6 / alto * 1.6, txt, fontsize=9.5, color=TINTA, va='center')
    pie = 'Fuente: lectura de sus redes' + (f' del {fecha_redes}' if fecha_redes else '') + '. Redes con menos de 5 comentarios no se muestran.'
    return _guardar(fig, ruta, pie)


# ── 4. Arquetipos ───────────────────────────────────────────────────────────
def arquetipos(ciclo, ruta):
    arq = [a for a in ciclo.get('arquetipos') or [] if a.get('afin') is not None and a.get('act') is not None][:4]
    if len(arq) < 2:
        return None
    alto = 1.6 + .5 * len(arq)
    fig, ax = _lienzo(alto)
    nombres = [a['nombre'] for a in arq][::-1]
    vals = [a['afin'] for a in arq][::-1]
    cols = [a.get('color') or VERDE for a in arq][::-1]
    barras = ax.barh(nombres, vals, height=.56, color=cols, edgecolor=CREMA, linewidth=1)
    ax.axvline(1, color=TINTA, linewidth=1.2, linestyle=(0, (3, 3)))
    ax.text(1, len(vals) - .42, 'promedio de la ciudad', ha='center', va='bottom', fontsize=8.5, color=MUTED)
    temas = [a.get('temaNombre') or '' for a in arq][::-1]
    distintos = len(set(temas)) > 1          # si todos los mueve lo mismo, se dice una vez en el subtítulo
    for b, v, t in zip(barras, vals, temas):
        x = max(b.get_width(), 1) + .04       # la cifra nunca encima de la línea del promedio
        ax.text(x, b.get_y() + b.get_height() / 2, f'×{v:.2f}'.replace('.', ',') + (f'  ·  {t}' if distintos and t else ''),
                va='center', fontsize=10.5, fontweight='bold', color=TINTA)
    ax.set_xlim(0, max(max(vals) * (1.9 if distintos else 1.25), 1.5))
    ax.set_xticks([])
    _limpiar(ax)
    ax.spines['bottom'].set_visible(False)
    fig.subplots_adjust(left=.36, right=.98, top=1 - (1.3 if not distintos else 1.05) / alto, bottom=.45 / alto)
    sub = 'Cuánto rinde usted en cada arquetipo frente al promedio de la ciudad'
    if not distintos and temas[0]:
        sub += f'.\nA {"los cuatro" if len(temas) == 4 else "todos"} los mueve {temas[0]}.'
    _cabecera(fig, 'A quién le habla la agenda de estos días', sub)
    return _guardar(fig, ruta, 'Describe barrios, no personas: el voto es secreto.')


def graficar(ciclo, cap, salida, desde, hasta, fecha_redes=None):
    os.makedirs(salida, exist_ok=True)
    out = {}
    for clave, fn in (('prensa', lambda r: prensa(ciclo, r, desde, hasta)), ('zonas', lambda r: zonas(ciclo, r)),
                      ('arquetipos', lambda r: arquetipos(ciclo, r)), ('redes', lambda r: redes(cap, r, fecha_redes))):
        try:
            ruta = fn(os.path.join(salida, f'{clave}.png'))
        except Exception as e:      # un gráfico que falla no tumba el briefing
            print(f'   gráfico {clave}: {e}')
            ruta = None
        if ruta:
            out[clave] = ruta
    return out


if __name__ == '__main__':
    import datetime as dt
    import sys
    c = json.load(open(sys.argv[1]))
    cap = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    print(graficar(c, cap, sys.argv[3] if len(sys.argv) > 3 else 'graficos', dt.date(2026, 10, 24), dt.date(2026, 10, 27)))
