#!/usr/bin/env python3
"""Favicon de ricardoruiz.co: las 4 barras del logo sobre fondo oscuro.

Genera en la raíz del repo, desde UNA sola geometría:

    favicon.svg            vectorial (lo usan Chrome, Firefox y Edge en la pestaña)
    favicon.ico            16x16 + 32x32 + 48x48 (lo pide todo navegador en /favicon.ico)
    apple-touch-icon.png   180x180 opaco (pantalla de inicio de iOS)

Uso:
    python3 tools/favicon/build.py

El logo del sitio es <span class="bars"> con 4 barras de 5 px de ancho, 3 px de
separación y alturas 9 · 14 · 20 · 12, alineadas abajo, en #0047FF. A 16x16 esas
proporciones no caben con margen, así que la geometría se rediseñó sobre una
cuadrícula de 32 unidades con TODOS los bordes en números pares: así caen en
píxel entero a 16, 32 y 48 px y las barras salen nítidas, sin borde difuminado.
Se conserva la silueta del logo (sube hasta la tercera barra y baja en la cuarta):

    alturas  9 · 14 · 20 · 12   (logo)      ->  0,45 · 0,70 · 1 · 0,60
             10 · 16 · 22 · 14  (favicon)   ->  0,45 · 0,73 · 1 · 0,64

El grupo queda 1 unidad arriba y a la izquierda del centro geométrico a propósito:
como las barras van alineadas abajo y la más alta está a la derecha, su peso visual
cae abajo a la derecha, y centrarlo por la caja lo haría ver caído.

⚠ No usa Pillow para dibujar ni para codificar: el rasterizado (cobertura exacta de
cada barra + supermuestreo de las esquinas redondeadas) y la escritura de PNG e ICO
son Python puro con struct/zlib. Así los bytes salen idénticos con o sin Pillow y en
cualquier versión de él. Si Pillow está instalado, solo se usa al final para releer
los archivos y comprobar que abren con el tamaño esperado.

Si cambias la geometría o los colores, vuelve a correr el script y sube los tres
archivos juntos.
"""

import struct
import sys
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

FONDO = (0x06, 0x08, 0x10)   # #060810 · fondo del sistema visual v2
AZUL = (0x00, 0x47, 0xFF)    # #0047FF · color de las barras del logo

# Geometría en una cuadrícula de 32 unidades.
LADO = 32
RADIO = 4                    # esquinas levemente redondeadas (12,5 % del lado)
BASE = 26                    # línea de base de las barras (margen de 4 arriba, 6 abajo)
ANCHO = 4
BARRAS = [                   # (x, alto)
    (4, 10),
    (10, 16),
    (16, 22),
    (22, 14),
]

SUBMUESTRAS = 16             # por eje, solo en los píxeles de las esquinas


def rects_barras():
    """Barras como (x0, y0, x1, y1) en unidades de la cuadrícula."""
    return [(x, BASE - alto, x + ANCHO, BASE) for x, alto in BARRAS]


# ─────────────────────────── SVG ───────────────────────────

def svg():
    barras = '\n'.join(
        f'    <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}"/>'
        for x0, y0, x1, y1 in rects_barras()
    )
    hexa = lambda c: '#%02X%02X%02X' % c
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LADO} {LADO}" '
        f'width="{LADO}" height="{LADO}">\n'
        f'  <rect width="{LADO}" height="{LADO}" rx="{RADIO}" fill="{hexa(FONDO)}"/>\n'
        f'  <g fill="{hexa(AZUL)}">\n{barras}\n  </g>\n'
        f'</svg>\n'
    )


# ─────────────────────────── rasterizado ───────────────────────────

def _solape(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def _cobertura_fondo(px, py, w, h, r):
    """Fracción del píxel (px, py) cubierta por el rectángulo redondeado [0,w]x[0,h]."""
    if r <= 0:
        return 1.0
    # Fuera de las cuatro cajas de esquina el píxel está completo.
    en_esquina_x = px < r or px + 1 > w - r
    en_esquina_y = py < r or py + 1 > h - r
    if not (en_esquina_x and en_esquina_y):
        return 1.0
    dentro = 0
    n = SUBMUESTRAS
    for j in range(n):
        y = py + (j + 0.5) / n
        for i in range(n):
            x = px + (i + 0.5) / n
            cx = r if x < r else (w - r if x > w - r else x)
            cy = r if y < r else (h - r if y > h - r else y)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                dentro += 1
    return dentro / (n * n)


def _canal(v):
    return max(0, min(255, int(v + 0.5)))


def rasterizar(lado_px, escala, origen, radio_px):
    """Filas de tuplas (r, g, b, a) de arriba hacia abajo.

    Cada barra ocupa  origen + unidad * escala  en píxeles. Las barras no se
    solapan, así que su cobertura es la suma exacta del área de cada una.
    """
    barras = [
        (origen + x0 * escala, origen + y0 * escala,
         origen + x1 * escala, origen + y1 * escala)
        for x0, y0, x1, y1 in rects_barras()
    ]
    filas = []
    for py in range(lado_px):
        fila = []
        for px in range(lado_px):
            cf = _cobertura_fondo(px, py, lado_px, lado_px, radio_px)
            cb = 0.0
            for x0, y0, x1, y1 in barras:
                cb += _solape(px, px + 1, x0, x1) * _solape(py, py + 1, y0, y1)
            cb = min(1.0, cb)
            a = cb + cf * (1.0 - cb)
            if a <= 0:
                fila.append((0, 0, 0, 0))
                continue
            color = tuple(
                (AZUL[k] * cb + FONDO[k] * cf * (1.0 - cb)) / a for k in range(3)
            )
            fila.append((_canal(color[0]), _canal(color[1]), _canal(color[2]), _canal(a * 255)))
        filas.append(fila)
    return filas


def favicon(lado_px):
    """Ícono de pestaña: la cuadrícula escalada al tamaño, con esquinas redondeadas."""
    escala = lado_px / LADO
    return rasterizar(lado_px, escala, 0.0, RADIO * escala)


def apple_touch():
    """180x180 opaco y a sangre: iOS le pone su propia máscara de esquinas.

    Escala 5 (unidad = 5 px) en vez de 180/32 para que los bordes caigan en píxel
    entero; el grupo de barras ocupa 110 px (61 %), dentro de la zona segura de la
    máscara, con el mismo margen 4:6 que el favicon (28 px arriba/izquierda, 42 px
    abajo/derecha).
    """
    return rasterizar(180, 5, 8, 0)


# ─────────────────────────── codificación ───────────────────────────

def _chunk(tipo, datos):
    return (struct.pack('>I', len(datos)) + tipo + datos
            + struct.pack('>I', zlib.crc32(tipo + datos) & 0xFFFFFFFF))


def png(filas, alfa=True):
    alto, ancho = len(filas), len(filas[0])
    crudo = bytearray()
    for fila in filas:
        crudo.append(0)  # filtro "None" en cada fila
        for r, g, b, a in fila:
            crudo += bytes((r, g, b, a)) if alfa else bytes((r, g, b))
    ihdr = struct.pack('>IIBBBBB', ancho, alto, 8, 6 if alfa else 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', ihdr)
            + _chunk(b'IDAT', zlib.compress(bytes(crudo), 9)) + _chunk(b'IEND', b''))


def _dib(filas):
    """Imagen BMP de 32 bits para ICO (la variante que abre en cualquier Windows)."""
    lado = len(filas)
    xor = bytearray()
    for fila in reversed(filas):                 # BMP va de abajo hacia arriba
        for r, g, b, a in fila:
            xor += bytes((b, g, r, a))
    paso = ((lado + 31) // 32) * 4               # máscara AND de 1 bit, filas a 32 bits
    mascara = bytearray()
    for fila in reversed(filas):
        bits = bytearray(paso)
        for x, (_, _, _, a) in enumerate(fila):
            if a == 0:                           # 1 = transparente
                bits[x // 8] |= 0x80 >> (x % 8)
        mascara += bits
    cabecera = struct.pack('<IiiHHIIiiII', 40, lado, lado * 2, 1, 32, 0,
                           len(xor) + len(mascara), 0, 0, 0, 0)
    return cabecera + bytes(xor) + bytes(mascara)


def ico(tamanos):
    imagenes = [(t, _dib(favicon(t))) for t in tamanos]
    salida = struct.pack('<HHH', 0, 1, len(imagenes))
    desplazamiento = 6 + 16 * len(imagenes)
    for t, datos in imagenes:
        salida += struct.pack('<BBBBHHII', t % 256, t % 256, 0, 0, 1, 32,
                              len(datos), desplazamiento)
        desplazamiento += len(datos)
    for _, datos in imagenes:
        salida += datos
    return salida


# ─────────────────────────── verificación opcional ───────────────────────────

def comprobar_con_pillow():
    try:
        from PIL import Image
    except ImportError:
        print('  (Pillow no está instalado: se omite la relectura de los archivos)')
        return
    with Image.open(RAIZ / 'favicon.ico') as im:
        tamanos = sorted(im.info.get('sizes', set()))
        assert tamanos == [(16, 16), (32, 32), (48, 48)], tamanos
        for t in (16, 32, 48):
            im.size = (t, t)
            im.load()
            assert im.size == (t, t)
    with Image.open(RAIZ / 'apple-touch-icon.png') as im:
        assert im.size == (180, 180) and im.mode == 'RGB', (im.size, im.mode)
    print('  ✓ Pillow relee los tres tamaños del ICO y el PNG de 180')


def main():
    (RAIZ / 'favicon.svg').write_text(svg(), encoding='utf-8')
    (RAIZ / 'favicon.ico').write_bytes(ico([16, 32, 48]))
    (RAIZ / 'apple-touch-icon.png').write_bytes(png(apple_touch(), alfa=False))
    for nombre in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png'):
        print(f'  {nombre:<22} {(RAIZ / nombre).stat().st_size:>6} bytes')
    comprobar_con_pillow()
    return 0


if __name__ == '__main__':
    sys.exit(main())
