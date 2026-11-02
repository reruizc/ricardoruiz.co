#!/usr/bin/env python3
"""Guarda antes de subir: ¿el archivo nuevo trae al menos lo que ya está publicado?

Una cosecha que se corta a la mitad (el WAF de la Imprenta, una consulta de la
Corte que no responde) produce un índice válido y más corto. Subirlo borraría
de la vista lo que ya existía, sin que nada falle. Esto compara un campo
numérico del JSON local contra el mismo campo del objeto que hoy está en S3 y
sale con 1 si el nuevo baja más de lo tolerado.

    python3 tools/caudal/salud/piso.py --local dist/s3/gacetas.json \\
        --s3 s3://caudal-legislativo/metadata/gacetas.json --campo n

Si el objeto de S3 no existe o no se puede leer, deja pasar: la primera subida
no tiene contra qué compararse, y un fallo de red no debe trabar la publicación
(la subida misma va a fallar igual si no hay red).
"""
import argparse, json, os, subprocess, sys, tempfile


def leer(path, campo):
    with open(path, encoding='utf-8') as f:
        return int(json.load(f)[campo])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--local', required=True)
    ap.add_argument('--s3', required=True)
    ap.add_argument('--campo', required=True)
    ap.add_argument('--tolera', type=float, default=0.03, help='caída máxima aceptada (0.03 = 3 %%)')
    a = ap.parse_args()

    nuevo = leer(a.local, a.campo)
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, 'publicado.json')
        r = subprocess.run(['aws', 's3', 'cp', a.s3, dest, '--only-show-errors'],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f'piso: no pude leer {a.s3} ({r.stderr.strip()[:120]}); dejo pasar')
            return 0
        antes = leer(dest, a.campo)
    if nuevo < antes * (1 - a.tolera):
        print(f'piso: {a.campo} bajó de {antes} a {nuevo} (más del {a.tolera:.0%}); no se sube')
        return 1
    print(f'piso: {a.campo} {antes} → {nuevo} · ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
