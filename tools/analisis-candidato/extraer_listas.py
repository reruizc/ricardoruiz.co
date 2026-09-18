#!/usr/bin/env python3
"""
extraer_listas.py — saca de los índices regenerados de 2023 el voto de LISTA de
todo el país y lo deja en un solo archivo compacto que el sitio puede servir.

Por qué existe: el índice completo vive en S3 y pesa decenas de MB, así que
mientras no se resuba el sitio no tiene de dónde leer el voto de lista. Esto es
lo mismo, pero sin los candidatos: unos cientos de KB que sí caben en el repo y
que `vote-target.js` lee para repartir las curules bien en cualquier municipio
—y no solo en Bogotá, que era lo único que estaba a mano.

Los nombres se internan (una tabla de circunscripciones y otra de partidos) y
cada lista es una fila corta, porque «PARTIDO CAMBIO RADICAL - PARTIDO MIRA -
PARTIDO DE LA U» repetido mil veces pesa más que todos los números juntos.

    python3 tools/analisis-candidato/extraer_listas.py
    python3 tools/analisis-candidato/extraer_listas.py --dir "Bases de datos" --salida candidato-360-data/listas-2023.json

Formato:
    { "v": "…", "corps": { "concejo": {
        "circ":  ["BOGOTÁ D.C.", …],          # circunscripciones
        "part":  ["PARTIDO ALIANZA VERDE", …], # partidos
        "listas": [[iCirc, iPart, lista, personal, cerrada01], …] } } }
"""
import argparse, json, os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPS = [('concejo', 'output_concejo_2023'), ('jal', 'output_jal_2023'), ('asamblea', 'output_asamblea_2023')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(RAIZ, 'Bases de datos'))
    ap.add_argument('--salida', default=os.path.join(RAIZ, 'candidato-360-data', 'listas-2023.json'))
    args = ap.parse_args()

    out = {'v': '2023', 'fuente': 'GCS de la Registraduría · fila COD_CAN=0 (voto de lista)', 'corps': {}}
    total = 0
    for corp, carpeta in CORPS:
        ruta = os.path.join(args.dir, carpeta, f'index-{corp}-2023.json')
        if not os.path.exists(ruta):
            print(f'⚠ {corp}: no está {ruta}, se omite')
            continue
        with open(ruta, encoding='utf-8') as f:
            idx = json.load(f)
        listas = idx.get('listas') or []
        if not listas:
            print(f'⚠ {corp}: el índice no trae `listas`, se omite')
            continue
        circ, part, filas = {}, {}, []
        for l in listas:
            c = l.get('circunscripcion') or ''
            p = l.get('partido') or ''
            ic = circ.setdefault(c, len(circ))
            ip = part.setdefault(p, len(part))
            filas.append([ic, ip, int(l.get('lista') or 0), int(l.get('personal') or 0), 1 if l.get('cerrada') else 0])
        out['corps'][corp] = {
            'circ': [c for c, _ in sorted(circ.items(), key=lambda kv: kv[1])],
            'part': [p for p, _ in sorted(part.items(), key=lambda kv: kv[1])],
            'listas': filas,
        }
        cerradas = sum(f[4] for f in filas)
        total += len(filas)
        print(f'{corp}: {len(filas):,} listas · {len(circ):,} circunscripciones · {len(part):,} partidos · {cerradas:,} cerradas')

    if not out['corps']:
        sys.exit('no se extrajo nada: ¿corrió regenerar_2023.sh?')
    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    with open(args.salida, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\n→ {args.salida} ({os.path.getsize(args.salida) / 1024:.0f} KB · {total:,} listas)')


if __name__ == '__main__':
    main()
