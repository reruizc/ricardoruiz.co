#!/usr/bin/env python3
"""
El diccionario de empresas, en el formato que necesita la pregunta de entrada
de caudal.html («¿en qué sector estás y, si quieres, qué empresa eres?»).

Sale de `tools/caudal/empresas.py` —la misma fuente que usa la búsqueda— y no
de una lista aparte: si el diccionario crece, el selector crece con él al
volver a correr esto.

    python3 tools/caudal/diccionario/build_selector.py

→ `caudal-empresas.json` en la raíz del sitio (lo sirve GitHub Pages). Es
público a propósito: el diccionario ya lo es en el repo.

Cada empresa trae los SECTORES DE CAUDAL que toca (`x`), que son los 15
presets públicos de la Rosa de los Vientos. Se derivan de sus tópicos del
tesauro, en orden: primero el núcleo (la actividad que ES la empresa), después
el contexto, y si nada casa, su sector del diccionario. Uber sale con
Transporte, Trabajo y Comercio y consumo: eso es lo que hace que la pregunta
de sector sea de opción múltiple y no de una sola respuesta.

El logo (`l`) sale de lo que ya está en `Bases de datos/caudal-logos/logos/`,
que es lo mismo que se subió a `congreso-2026/output/caudal/logos/`. Si se
suben logos nuevos, volver a correr esto.
"""
import json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(AQUI, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'caudal'))
import empresas as E          # noqa: E402
import caudal_core as C       # noqa: E402

OUT = os.path.join(ROOT, 'caudal-empresas.json')
LOGOS = os.path.join(ROOT, 'Bases de datos', 'caudal-logos', 'logos')

# Los presets que se ofrecen a cualquiera. DiDi, Binance y Cauce son clientes
# con nombre y solo los ve el equipo: no van en la pregunta de entrada.
PRIVADOS = {'didi', 'binance', 'cauce'}

# Tópico del tesauro → sector(es) de Caudal. Lo que no tiene un sector propio
# (tributario, víctimas, propiedad intelectual…) atraviesa a todos y no
# sugiere ninguno: sugerirlo sería ruido.
TOPICO_SECTOR = {
    'comercio y retail': ['comercio'],
    'salud / EPS e IPS': ['salud'],
    'sector agropecuario': ['agro'],
    'alimentos / etiquetado': ['comercio'],
    'sector financiero': ['financiero'],
    'ambiental / medio ambiente': ['ambiente'],
    'puertos y logistica': ['puertos'],
    'comercio exterior y aduanas': ['puertos'],
    'obra publica y contratacion estatal': ['contratacion'],
    'tecnologia digital / IA': ['tic'],
    'laboral': ['trabajo'],
    'vivienda y construccion': ['vivienda'],
    'competencia y consumidor': ['comercio'],
    'energia y servicios publicos': ['energia'],
    'mineria e hidrocarburos': ['energia'],
    'telecomunicaciones': ['tic'],
    'farmaceutico / medicamentos': ['salud'],
    'educacion superior': ['educacion'],
    'agua y saneamiento': ['energia'],
    'turismo y hoteleria': ['turismo'],
    'ordenamiento territorial y urbanismo': ['vivienda'],
    'economia solidaria / cooperativas': ['pymes'],
    'palma y biocombustibles': ['agro'],
    'seguros': ['financiero'],
    'datos personales / habeas data': ['tic'],
    'criptoactivos y activos virtuales': ['financiero'],
    'licores y tabaco': ['comercio'],
    'pensiones y cesantias': ['trabajo'],
    'consulta previa / comunidades etnicas': ['ambiente'],
    'aviacion / transporte aereo': ['transporte'],
    'transporte por plataformas': ['transporte'],
}

# Sector del diccionario → sector de Caudal, solo como último recurso.
SECTOR_DICC = {
    'salud': 'salud', 'farma': 'salud', 'agro': 'agro', 'energia': 'energia',
    'mineria': 'energia', 'agua': 'energia', 'construccion': 'vivienda',
    'financiero': 'financiero', 'seguros': 'financiero', 'cripto': 'financiero',
    'pensiones': 'trabajo', 'tecnologia': 'tic', 'telecom': 'tic', 'medios': 'tic',
    'alimentos': 'comercio', 'retail': 'comercio', 'consumo': 'comercio',
    'comercio': 'comercio', 'textil': 'comercio', 'industria': 'comercio',
    'juegos': 'comercio', 'educacion': 'educacion', 'transporte': 'transporte',
    'automotriz': 'transporte', 'aviacion': 'transporte', 'logistica': 'puertos',
    'turismo': 'turismo',
}

MAX_SUG = 4

# Los temas de los presets son términos de búsqueda internos y van sin tildes
# («regimen pensional»). En un chip que lee una persona se ven descuidados, así
# que se les devuelve la tilde palabra por palabra. Solo para mostrar: la
# búsqueda normaliza y encuentra lo mismo con o sin ella.
TILDES = {
    'contratacion': 'contratación', 'publicas': 'públicas', 'publicos': 'públicos',
    'publico': 'público', 'energia': 'energía', 'transicion': 'transición',
    'energetica': 'energética', 'gestion': 'gestión', 'areas': 'áreas',
    'pequenas': 'pequeñas', 'educacion': 'educación', 'regimen': 'régimen',
    'proteccion': 'protección', 'electronico': 'electrónico', 'interes': 'interés',
    'politica': 'política', 'construccion': 'construcción', 'turisticos': 'turísticos',
    'turistica': 'turística', 'maritimos': 'marítimos', 'minimo': 'mínimo',
}


def con_tildes(t):
    return ' '.join(TILDES.get(w, w) for w in t.split(' '))


def sectores_de(e):
    out = []
    for t in list(e.get('nucleo') or []) + list(e.get('contexto') or []):
        for s in TOPICO_SECTOR.get(t, []):
            if s not in out:
                out.append(s)
    if not out and SECTOR_DICC.get(e.get('sector')):
        out.append(SECTOR_DICC[e['sector']])
    return out[:MAX_SUG]


def main():
    presets = [p for p in C.SECTORES_CLIENTE if p['k'] not in PRIVADOS]
    validos = {p['k'] for p in presets}
    for ss in list(TOPICO_SECTOR.values()) + [[v] for v in SECTOR_DICC.values()]:
        for s in ss:
            assert s in validos, f'sector desconocido en el mapa: {s}'

    logos = set()
    if os.path.isdir(LOGOS):
        logos = {f[:-4] for f in os.listdir(LOGOS) if f.endswith('.png')}

    emp = []
    for e in E.EMPRESAS:
        nombre = e['nombre']
        nn = E._n(nombre)
        alias = sorted({a for a in e.get('alias') or [] if a and a != nn and len(a) >= 3})
        r = {'k': e['k'], 'n': nombre, 's': e.get('sector') or '', 'x': sectores_de(e)}
        if e.get('tipo') != 'empresa':
            r['g'] = 1
        if alias:
            r['a'] = alias
        if e['k'] in logos:
            r['l'] = 1
        emp.append(r)

    doc = {
        'v': 1,
        'logos': 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/caudal/logos/',
        # tres temas por sector: los chips de búsqueda que se le ofrecen a quien
        # dijo que está en ese sector (salen del preset, no se escriben acá)
        'sectores': [{'k': p['k'], 'n': p['nombre'], 't': [con_tildes(t) for t in list(p.get('temas') or [])[:3]]} for p in presets],
        'empresas': emp,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))

    sin = sum(1 for r in emp if not r['x'])
    multi = sum(1 for r in emp if len(r['x']) > 1)
    print(f'{OUT} · {os.path.getsize(OUT)/1024:.0f} KB · {len(emp)} entradas · '
          f'{len(logos & {r["k"] for r in emp})} con logo · {multi} tocan varios sectores · '
          f'{sin} sin sector sugerido · {len(presets)} sectores')


if __name__ == '__main__':
    main()
