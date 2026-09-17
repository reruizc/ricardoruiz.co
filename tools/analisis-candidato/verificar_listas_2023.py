#!/usr/bin/env python3
"""
verificar_listas_2023.py — comprueba que los índices de 2023 regenerados traen
el voto de LISTA y que con él el reparto de curules da el resultado real.

Es la prueba de aceptación de la regeneración: sin esto uno se entera de que el
índice quedó mal cuando un cliente ve una meta absurda. Hace tres cosas:

  1. cuadra cada lista contra sus propios candidatos (total = personal + lista)
     y marca como cerradas las que no tienen voto preferente;
  2. compara el Concejo de Bogotá contra el ESCRUTINIO publicado, lista por
     lista (el preconteo difiere poco, así que se admite un margen);
  3. reconstruye el reparto de Bogotá con umbral y cifra repartidora —44 curules
     por repartidora y una del estatuto de oposición— y exige que dé la
     composición real del cabildo 2024-2027.

    python3 tools/analisis-candidato/verificar_listas_2023.py
    python3 tools/analisis-candidato/verificar_listas_2023.py --dir "Bases de datos"
    python3 tools/analisis-candidato/verificar_listas_2023.py --solo-estructura

Sale con código 1 si algo no cuadra, para poder encadenarlo en un script.
"""
import argparse, json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Concejo de Bogotá 2023, acto de escrutinio: votación de cada lista, curules
# obtenidas y si fue cerrada. La 45.ª curul es de Juan Daniel Oviedo, por el
# estatuto de oposición (Ley 1909 de 2018), y no sale de la cifra repartidora.
BOGOTA_2023 = [
    ('PARTIDO ALIANZA VERDE',                                   419884, 8, False),
    ('NUEVO LIBERALISMO EN MARCHA',                             401187, 8, False),
    ('PACTO HISTÓRICO',                                         376733, 7, True),
    ('PARTIDO CENTRO DEMOCRÁTICO',                              358140, 7, False),
    ('PARTIDO LIBERAL COLOMBIANO',                              296637, 6, False),
    ('PARTIDO CAMBIO RADICAL - PARTIDO MIRA - PARTIDO DE LA U',  217085, 4, False),
    ('LIDERAZGO AMPLIO DE RENOVACIÓN AVANZADA DE BTÁ "LARA BOGOTÁ"', 138445, 2, False),
    ('PARTIDO CONSERVADOR - PARTIDO COLOMBIA JUSTA LIBRES',       85834, 1, False),
    ('BOGOTÁ MÁS FUERTE',                                         52581, 1, False),
]
CURULES_BOGOTA = 45
MARGEN = 0.02   # preconteo vs escrutinio


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return ' '.join(c if c.isalnum() else ' ' for c in s).split()


def clave(s):
    return ' '.join(norm(s))


def reparto(listas, curules, oposicion, blanco=0):
    """Art. 263: umbral del 50 % del cuociente electoral y cifra repartidora.
    `listas` = [(nombre, votos)]. Devuelve {nombre: curules}."""
    asignables = max(1, curules - oposicion)
    validos = sum(v for _, v in listas) + blanco
    umbral = validos / curules / 2
    elegibles = [(n, v) for n, v in listas if v >= umbral] or list(listas)
    cocientes = sorted(((v / d, n) for n, v in elegibles for d in range(1, asignables + 1)), reverse=True)
    out = {}
    for _, n in cocientes[:asignables]:
        out[n] = out.get(n, 0) + 1
    return out


def cargar(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(ROOT, 'Bases de datos'))
    ap.add_argument('--solo-estructura', action='store_true',
                    help='no compara con el escrutinio de Bogotá (útil con datos de prueba)')
    args = ap.parse_args()

    fallos, avisos = [], []

    def revisar(t, ok):
        print(f"{'✓' if ok else '✗'} {t}")
        if not ok:
            fallos.append(t)

    for corp, carpeta in (('concejo', 'output_concejo_2023'), ('jal', 'output_jal_2023'), ('asamblea', 'output_asamblea_2023')):
        idx = cargar(os.path.join(args.dir, carpeta, f'index-{corp}-2023.json'))
        if idx is None:
            avisos.append(f'{corp}: no se encontró el índice, se omite')
            continue
        listas = idx.get('listas')
        revisar(f'{corp}: el índice trae `listas`', isinstance(listas, list) and len(listas) > 0)
        if not listas:
            continue
        # el voto personal de cada lista tiene que ser el de sus candidatos
        personal = {}
        for c in idx.get('candidatos', []):
            k = (clave(c.get('circunscripcion')), clave(c.get('partido')))
            personal[k] = personal.get(k, 0) + int(c.get('votos') or 0)
        malas = [l for l in listas
                 if l.get('total') != (l.get('lista') or 0) + (l.get('personal') or 0)
                 or l.get('personal') != personal.get((clave(l.get('circunscripcion')), clave(l.get('partido'))), 0)]
        revisar(f'{corp}: cada lista cuadra con sus candidatos (total = personal + lista)', not malas)
        if malas:
            for l in malas[:5]:
                print(f'    · {l.get("circunscripcion")} / {l.get("partido")}: {l}')
        cerradas = [l for l in listas if l.get('cerrada')]
        malcerradas = [l for l in cerradas if l.get('personal')]
        revisar(f'{corp}: las cerradas no tienen voto preferente ({len(cerradas)} cerradas de {len(listas)})', not malcerradas)

    # ── El Concejo de Bogotá contra el escrutinio ────────────────────────────
    idx = cargar(os.path.join(args.dir, 'output_concejo_2023', 'index-concejo-2023.json'))
    if args.solo_estructura or not idx or not idx.get('listas'):
        print('· no se compara con el escrutinio de Bogotá')
    else:
        bog = {clave(l['partido']): l for l in idx['listas'] if clave(l['circunscripcion']) == clave('BOGOTÁ D.C.')}
        faltan = [n for n, *_ in BOGOTA_2023 if clave(n) not in bog]
        revisar(f'Bogotá: están las {len(BOGOTA_2023)} listas del escrutinio', not faltan)
        if faltan:
            print('    faltan:', ', '.join(faltan))
        lejos = []
        for nombre, total, _cur, cerrada in BOGOTA_2023:
            l = bog.get(clave(nombre))
            if not l:
                continue
            if abs(l['total'] - total) / total > MARGEN:
                lejos.append(f'{nombre}: índice {l["total"]:,} vs escrutinio {total:,}')
            if bool(l.get('cerrada')) != cerrada:
                lejos.append(f'{nombre}: cerrada={l.get("cerrada")}, debía ser {cerrada}')
        revisar(f'Bogotá: cada lista está a menos del {MARGEN:.0%} del escrutinio', not lejos)
        for x in lejos[:8]:
            print(f'    · {x}')
        if bog and not faltan:
            res = {clave(l['circunscripcion']): 0 for l in idx['listas']}
            del res
            curules = reparto([(n, bog[clave(n)]['total']) for n, *_ in BOGOTA_2023], CURULES_BOGOTA, 1)
            esperado = {n: c for n, _t, c, _x in BOGOTA_2023}
            iguales = all(curules.get(n, 0) == c for n, c in esperado.items())
            revisar('Bogotá: el reparto da la composición real del cabildo 2024-2027', iguales)
            if not iguales:
                for n, c in esperado.items():
                    got = curules.get(n, 0)
                    print(f'    {"·" if got == c else "✗"} {n[:46]:48} {got} (real {c})')
            revisar(f'Bogotá: se reparten 44 y una es del estatuto de oposición',
                    sum(curules.values()) == CURULES_BOGOTA - 1)

    for a in avisos:
        print(f'⚠ {a}')
    print(f'\n{len(fallos)} fallaron' if fallos else '\nTodo cuadra')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
