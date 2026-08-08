#!/usr/bin/env python3
"""build_frames.py — deja los frames de la secuencia en peso servible.

Los PNG que salen del generador de imágenes pesan ~1,6 MB cada uno: los 10 suman
16 MB, siete veces el resto de la página junta. Nadie con datos móviles espera eso,
y el público de esta herramienta es justo el que paga los datos por megabyte.

Qué hace: recorta el margen sobrante, genera dos anchos (móvil y escritorio) y
convierte a WebP. No hay transparencia que preservar —el generador entregó fondo
opaco— y eso juega a favor: el fondo gris de las imágenes es casi idéntico al
--paper de la página, así que se funden sin recortar la silueta.

Uso:
  python3 tools/tutela-analiza/build_frames.py            # convierte
  python3 tools/tutela-analiza/build_frames.py --check    # solo mide, no escribe
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageEnhance

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / 'tutelas-salud'
OUT = RAIZ / 'tutelas-salud' / 'w'

# Dos anchos: el chico cubre móviles hasta ~430 CSS px a densidad 2x; el grande
# cubre el contenedor de escritorio, que nunca pasa de ~560 px de lado.
ANCHOS = [(760, 'sm'), (1120, 'lg')]
CALIDAD = 80          # medido: por debajo de 78 se ve banding en el degradado del fondo
N_FRAMES = 10


def bbox_papel(im):
    """Recuadro de la hoja: es lo más claro sobre el fondo gris.

    Sirve de ancla para alinear los frames entre sí. El generador de imágenes no
    reproduce la hoja en el mismo sitio ni al mismo tamaño en cada corrida — medido
    sobre estos 10: hasta 23 px de desplazamiento vertical y 2% de diferencia de
    escala. Al encadenarlos con fundido eso se ve como un micro-zoom que delata que
    son imágenes distintas, justo lo que la secuencia quiere disimular.
    """
    g = im.convert('L')
    w, h = g.size
    px = g.load()
    # Se mide sobre la fila y la columna CENTRALES, no sobre toda la imagen. Dos
    # razones medidas: el fondo trae un degradado sutil, así que un umbral global
    # "fondo + k" agranda el recuadro en los frames más oscuros (el 6 quedaba 24 px
    # descuadrado); y papel y fondo están tan cerca en brillo que el histograma no
    # los separa. En el centro el contraste es máximo y no hay esquinas que estorben.
    # El blíster no interfiere: los bordes se buscan desde afuera hacia adentro.
    fondo = min(px[6, 6], px[w - 7, 6], px[6, h - 7], px[w - 7, h - 7])

    def bordes(perfil, salto=8):
        """Los dos cantos de la hoja: PRIMER salto de brillo entrando desde cada extremo.

        Dos intentos previos fallaron y vale dejar constancia. Un umbral absoluto no
        sirve: el fondo tiene un degradado de ~12 niveles entre esquinas y cualquier
        corte fijo se lo traga en unos frames y no en otros. Y el máximo de la derivada
        tampoco: el texto y el blíster contrastan MÁS que el canto de la hoja, así que
        el máximo aterriza en el contenido (daba 525 px de dispersión).
        Lo que sí distingue al canto es su POSICIÓN: nada del contenido está por fuera
        de la hoja, luego el primer escalón que aparece entrando desde el borde de la
        imagen es siempre el papel.
        """
        n = len(perfil)
        d = [perfil[i + 3] - perfil[i - 3] for i in range(3, n - 3)]
        ini = next((i + 3 for i in range(len(d)) if d[i] > salto), 0)
        fin = next((i + 3 for i in range(len(d) - 1, -1, -1) if d[i] < -salto), n - 1)
        return ini, fin

    fila = [px[x, h // 2] for x in range(w)]
    izq, der = bordes(fila)

    # El eje vertical se mide sobre VARIAS columnas de los márgenes de la hoja —donde
    # el papel está limpio de texto y blíster— y se toma la mediana. Con una sola
    # columna el resultado era intermitente: en algunos frames el canto superior
    # queda por debajo del umbral y la búsqueda se iba hasta el borde inferior.
    cols = [izq + k for k in (10, 18, 26, 34)] + [der - k for k in (10, 18, 26, 34)]
    arrs, abas = [], []
    for x in cols:
        if not (0 <= x < w):
            continue
        a, b = bordes([px[x, y] for y in range(h)], salto=5)
        if b - a > h * 0.4:              # descarta las columnas que no vieron la hoja
            arrs.append(a)
            abas.append(b)
    med = lambda v: sorted(v)[len(v) // 2] if v else 0
    return izq, med(arrs), der, (med(abas) or h - 1), fondo


def alinear(im, bb, ref, fondo_ref):
    """Lleva la hoja de este frame a la posición y escala del frame de referencia.

    Escala y traslada respecto del CENTRO de la hoja, y rellena el borde que queda
    descubierto con el gris de fondo del frame de referencia — así el fondo también
    queda parejo en toda la secuencia (venía variando 7 niveles de gris).
    """
    izq, arr, der, aba, fondo = bb
    rizq, rarr, rder, raba, fref = ref
    w, h = im.size
    # El generador entregó el fondo con hasta 10 niveles de gris de diferencia entre
    # frames. En un fundido eso se ve como un parpadeo de toda la superficie, que es
    # lo más grande del cuadro. Un ajuste lineal de brillo lo empareja; al ser del
    # orden del 4% no altera de forma perceptible el papel ni el contenido.
    if fondo and abs(fref - fondo) >= 2:
        im = ImageEnhance.Brightness(im).enhance(fref / fondo)
    escala = ((rder - rizq) / (der - izq) + (raba - rarr) / (aba - arr)) / 2
    cx, cy = (izq + der) / 2, (arr + aba) / 2
    rcx, rcy = (rizq + rder) / 2, (rarr + raba) / 2
    # transformación afín inversa que PIL espera: destino → origen
    a = 1 / escala
    lienzo = Image.new('RGB', (w, h), (fondo_ref, fondo_ref, fondo_ref))
    mov = im.transform((w, h), Image.AFFINE,
                       (a, 0, cx - rcx * a, 0, a, cy - rcy * a),
                       resample=Image.BICUBIC, fillcolor=(fondo, fondo, fondo))
    lienzo.paste(mov, (0, 0))
    return lienzo


def falta_cwebp():
    if shutil.which('cwebp'):
        return False
    print('Falta cwebp. Instálalo con:  brew install webp', file=sys.stderr)
    return True


def kb(p):
    return p.stat().st_size / 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='solo medir el estado actual')
    ap.add_argument('--calidad', type=int, default=CALIDAD)
    args = ap.parse_args()

    fuentes = [SRC / f'frame{i}.png' for i in range(1, N_FRAMES + 1)]
    faltan = [f.name for f in fuentes if not f.exists()]
    if faltan:
        sys.exit(f'Faltan frames: {", ".join(faltan)}')

    orig = sum(kb(f) for f in fuentes)
    print(f'origen: {len(fuentes)} PNG · {orig/1024:.1f} MB')
    if args.check:
        for f in fuentes:
            print(f'  {f.name:12s} {kb(f):7.0f} KB')
        return

    if falta_cwebp():
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / '_tmp.png'

    ref = None
    total = 0
    for f in fuentes:
        n = f.stem.replace('frame', '')
        im = Image.open(f).convert('RGB')
        bb = bbox_papel(im)
        if ref is None:
            ref = bb                      # el frame 1 fija dónde va la hoja
            dx = dy = 0
        else:
            dx, dy = bb[0] - ref[0], bb[1] - ref[1]
            im = alinear(im, bb, ref, ref[4])
        im.save(tmp)
        for ancho, suf in ANCHOS:
            dst = OUT / f'f{n}-{suf}.webp'
            # -resize con alto 0 mantiene la proporción; -m 6 es el esfuerzo máximo
            # de compresión (más lento al construir, nada al servir)
            r = subprocess.run(
                ['cwebp', '-q', str(args.calidad), '-m', '6', '-resize', str(ancho), '0',
                 '-quiet', str(tmp), '-o', str(dst)],
                capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f'cwebp falló en {f.name}: {r.stderr[:200]}')
            total += kb(dst)
        ajuste = f'  [alineado {dx:+d},{dy:+d} px]' if (dx or dy) else '  [referencia]'
        print(f'  frame{n:>2s}: {kb(f):6.0f} KB → '
              + ' + '.join(f'{kb(OUT / f"f{n}-{s}.webp"):5.0f} KB ({s})' for _, s in ANCHOS)
              + ajuste)
    tmp.unlink(missing_ok=True)

    print(f'\ntotal: {orig/1024:.1f} MB → {total/1024:.2f} MB  ({total/orig*100:.0f}% del origen)')
    solo_sm = sum(kb(OUT / f'f{i}-sm.webp') for i in range(1, N_FRAMES + 1))
    print(f'lo que baja un celular (solo -sm): {solo_sm:.0f} KB')


if __name__ == '__main__':
    main()
