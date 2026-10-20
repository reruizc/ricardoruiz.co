#!/usr/bin/env python3
"""Quién ocupa hoy un cargo y por eso no puede ser contendiente en 2027.

Arma `candidato-360-data/cargos-actuales.js` (window.Candidato360CargosActuales)
con tres fuentes:

  · Congreso 2026-2030 · los 285 de legislativo-electos.js.
  · Alcaldías y gobernaciones 2024-2027 · el más votado de cada circunscripción
    en los índices de 2023 (S3). Su periodo termina el 31-dic-2027, después de
    la elección: no pueden competir.
  · Gobierno nacional · los nombrados, designados y encargados desde el 7-ago-2026
    en el Diario Oficial (tools/nombramientos/extraer.py). Cualquiera nombrado
    después de esa fecha está dentro de los 12 meses previos a la elección.

Solo se publican nombre, cargo y dónde: nada de cédulas (el repo es público).

⚠ Pendiente: las atípicas 2025-2026 (Bucaramanga, Tunja, Cartago, Girón…)
cambiaron al alcalde de 2023; aquí sigue el de 2023. Ninguna es de las cuatro
ciudades revisadas.

  python3 tools/candidato-360/contendientes/build_cargos.py
"""
import gzip
import json
import os
import re
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'
NOMBRAMIENTOS = os.path.join(RAIZ, 'Bases de datos', 'nombramientos', 'nombramientos-2026.json')
SALIDA = os.path.join(RAIZ, 'candidato-360-data', 'cargos-actuales.js')
# Municipios (código electoral) donde la lista ya se revisó a mano y se excluye.
REVISADAS = {'16001': 'Bogotá', '01001': 'Medellín', '31001': 'Cali', '05001': 'Cartagena'}
NO_CANDIDATOS = re.compile(r'VOTO|BLANCO|NULO|NO MARCAD', re.I)


def bajar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'c360-cargos/1.0', 'Accept-Encoding': 'gzip'}), timeout=120) as r:
        b = r.read()
    return json.loads(gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b)


def titulo(s):
    t = ' '.join(w.capitalize() for w in str(s).lower().split())
    return re.sub(r'\b(De|Del|La|Las|Los|Y)\b', lambda m: m.group(0).lower(), t)


def congreso():
    txt = open(os.path.join(RAIZ, 'legislativo-electos.js'), encoding='utf-8').read()
    raw = json.loads(re.search(r'ELECTOS_RAW\s*=\s*(\[.*?\]);', txt, re.S).group(1))
    out = []
    for corp, nombre, partido, dep, _ in raw:
        cargo = 'Senador(a) 2026-2030' if corp == 'S' else f'Representante a la Cámara 2026-2030 · {titulo(dep)}'
        out.append({'nombre': nombre, 'cargo': cargo, 'tipo': 'congreso'})
    return out


def ejecutivos_2023():
    out = []
    for corp, dir_, partes, rotulo in (('alcaldia', 'alcaldia-2023', 3, 'Alcalde(sa) 2024-2027'), ('gobernacion', 'gobernacion-2023', 2, 'Gobernador(a) 2024-2027')):
        d = bajar(f'{S3}/{dir_}/index-{dir_}.json')
        mejor = {}
        for c in d.get('candidatos') or []:
            if NO_CANDIDATOS.search(c.get('nombre') or ''):
                continue
            k = '-'.join(str(c.get('slug', '')).split('-')[:partes])
            if k not in mejor or (c.get('votos') or 0) > (mejor[k].get('votos') or 0):
                mejor[k] = c
        for c in mejor.values():
            out.append({'nombre': c['nombre'], 'cargo': f'{rotulo} · {titulo(c.get("circunscripcion", ""))}', 'tipo': corp})
    return out


def gobierno():
    if not os.path.exists(NOMBRAMIENTOS):
        print('  ! sin nombramientos-2026.json: el gobierno queda fuera')
        return []
    out, vistos = [], set()
    for x in json.load(open(NOMBRAMIENTOS, encoding='utf-8')):
        n = (x.get('nombre') or '').strip()
        if not n or n.lower() in vistos:
            continue
        vistos.add(n.lower())
        cargo = re.split(r',|\s+C[óo]digo\b|\s+Grado\b', x.get('cargo') or '')[0].strip()
        out.append({'nombre': n, 'cargo': f'{cargo[:110]} (gobierno nacional, {x.get("fecha", "")[:7]})', 'tipo': 'gobierno'})
    return out


def main():
    c, e, g = congreso(), ejecutivos_2023(), gobierno()
    datos = {'v': __import__('datetime').date.today().isoformat(), 'revisadas': REVISADAS, 'cargos': c + e + g}
    js = ('/* Generado por tools/candidato-360/contendientes/build_cargos.py · no editar a mano.\n'
          '   Quién ocupa hoy un cargo y no puede ser contendiente en 2027 (Congreso 2026-2030,\n'
          '   alcaldías y gobernaciones 2024-2027, gobierno nacional desde el 7-ago-2026). */\n'
          f'window.Candidato360CargosActuales = {json.dumps(datos, ensure_ascii=False, separators=(",", ":"))};\n')
    open(SALIDA, 'w', encoding='utf-8').write(js)
    print(f'→ {os.path.relpath(SALIDA, RAIZ)} · congreso {len(c)} · alcaldías y gobernaciones {len(e)} · gobierno {len(g)} · {len(js) // 1024} KB')


if __name__ == '__main__':
    main()
