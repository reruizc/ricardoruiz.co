#!/usr/bin/env python3
"""Cámara 2026 · votos por PARTIDO en cada puesto, uno por departamento.

Para qué: la huella de un partido que NO tuvo lista en las territoriales de
2023. La lista de Oviedo en Bogotá, por ejemplo, no existía en 2023 pero sacó
74.131 votos a Cámara en 2026 — el mismo dato con el que el catálogo de
partidos del CRM la ofrece (tools/candidato-360/partidos/construir.mjs lee
Cámara 2026). Sin este archivo, la página del electorado (panel 06) no tenía
contra qué medir a un partido nuevo y se quedaba en «Todavía no».

Fuente: congreso-2026/output/camara/departamentos/{dep}/puestos.json (S3).
Ese archivo pesa hasta 22 MB porque trae candidatos y circunscripciones; el
navegador solo necesita partido × puesto, así que se recorta a ~1-3 %.

Salida: Bases de datos/output_camara_puesto/{dep}.json
  {"v": "...", "dep": "16", "partidos": [nombre, …],
   "puestos": {"160010101": [[índicePartido, votos], …], …}}
La llave es el código de puesto de 9 caracteres (dep·mun·zona·puesto), el
mismo de PUESTOS_GEOREF y de C360Electorado.puestos(). Los dos últimos pueden
llevar letra (0100199A1): no se limpian.

Subir (prefijo ya público):
  aws s3 cp "Bases de datos/output_camara_puesto/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/camara/partidos-puesto/" \
    --recursive --content-type application/json --content-encoding gzip  (ver --gzip)
"""
import gzip, json, os, sys, urllib.request, datetime

BASE = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/camara'
OUT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Bases de datos', 'output_camara_puesto')
UA = {'User-Agent': 'ricardoruiz.co build_camara_puesto', 'Accept-Encoding': 'gzip'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        raw = r.read()
    if r.headers.get('Content-Encoding') == 'gzip' or raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def main():
    os.makedirs(OUT, exist_ok=True)
    deps = sorted({str(x.get('cod') or x.get('dep_cod')).zfill(2) for x in get(f'{BASE}/departamentos.json')})
    deps = [d for d in deps if d != '88']   # exterior: no hay campaña territorial allá
    solo = sys.argv[1:]
    if solo: deps = [d for d in deps if d in solo]
    v = datetime.date.today().isoformat()
    for dep in deps:
        puestos = get(f'{BASE}/departamentos/{dep}/puestos.json')
        nombres, idx, out, total = [], {}, {}, 0
        for p in puestos:
            code = (str(p.get('dep_cod', dep)).zfill(2) + str(p['mun_cod']).zfill(3)
                    + str(p['zon_cod']).zfill(2) + str(p.get('pue_cod_raw') or '').zfill(2))
            fila = out.setdefault(code, {})
            for nombre, n in (p.get('partidos') or {}).items():
                if nombre.isdigit() or not n: continue   # 996/997/998: blanco, nulos, no marcados
                if nombre not in idx: idx[nombre] = len(nombres); nombres.append(nombre)
                fila[idx[nombre]] = fila.get(idx[nombre], 0) + int(n); total += int(n)
        doc = {'v': v, 'dep': dep, 'partidos': nombres,
               'puestos': {k: sorted(f.items(), key=lambda x: -x[1]) for k, f in out.items() if f}}
        ruta = os.path.join(OUT, f'{dep}.json')
        with open(ruta, 'w', encoding='utf-8') as fh: json.dump(doc, fh, ensure_ascii=False, separators=(',', ':'))
        print(f'{dep}: {len(doc["puestos"]):>5} puestos · {len(nombres):>3} partidos · {total:>10,} votos · {os.path.getsize(ruta)/1024:,.0f} KB')


if __name__ == '__main__':
    main()
