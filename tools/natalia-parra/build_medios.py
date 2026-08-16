#!/usr/bin/env python3
"""
Pulso de prensa de la ficha: local (Barrios Unidos) · Bogotá · nacional.

Motor: Google News RSS — gratis, sin API key, y una sola consulta trae decenas
de titulares de todo el ecosistema (nacional y regional) con el nombre del medio
limpio en el tag <source>. Es el mismo motor del pilar Medios de Caudal y del
monitor de Radar Mujer.

⚠️ El puente es S3: este script corre FUERA del navegador y publica un JSON.
La página nunca llama a Google News — así no hay CORS, ni bloqueo por origen,
ni una clave viajando al cliente.

⚠️ `gl=CO` solo SESGA, no restringe: sin agregar "Colombia" a la consulta se
cuelan titulares de México y España. Se agrega salvo que ya lo mencione.

⚠️ Google News devuelve 302 → `urlopen` lo sigue solo (con curl haría falta -L).
El título trae el sufijo " - Medio", redundante con <source>: se recorta.

⚠️ Mide COBERTURA, no realidad: que un tema no aparezca significa que la prensa
no lo cubrió, no que no exista.

Salida (gitignored):  Bases de datos/natalia-parra/nsp-medios.json
Correr:  python3 tools/natalia-parra/build_medios.py [--dias 21]
"""
import argparse
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(RAIZ, 'Bases de datos', 'natalia-parra')

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
TIMEOUT = 25

GRUPOS = {
    # ⚠️ Las locales van ENTRECOMILLADAS (frase exacta). Sin comillas, un nombre
    # de barrio es ambiguo en toda la región: la consulta suelta `La Castellana
    # Bogotá` trajo una nota del Cauca sobre un homenaje en Tunía. Ver además el
    # filtro `es_local`, que exige que el titular nombre el territorio.
    'local': [
        '"Barrios Unidos" Bogotá',
        '"localidad de Barrios Unidos"',
        '"alcaldía local de Barrios Unidos"',
        '"Junta Administradora Local" Bogotá',
        'ediles Bogotá localidad',
        '"Doce de Octubre" Bogotá barrio',
        '"Siete de Agosto" Bogotá barrio',
        '"Polo Club" OR "Quinta Mutis" OR "Simón Bolívar" Bogotá barrio',
    ],
    'bogota': [
        'Concejo de Bogotá',
        'Alcaldía de Bogotá',
        'seguridad Bogotá',
        'movilidad Bogotá',
        'presupuesto Bogotá',
        'espacio público Bogotá',
        'Carlos Fernando Galán',
    ],
    'nacional': [
        'Congreso de Colombia',
        'Gobierno Nacional Colombia',
        'reforma Colombia',
        'Corte Constitucional Colombia',
        'elecciones 2027 Colombia',
    ],
}

# Comunicados de entidades: no son prensa editorial independiente.
INSTITUCIONAL = re.compile(
    r'\b(gobernacion|alcaldia|ministerio|universidad|camara de comercio|registraduria|'
    r'policia nacional|superintendencia|supersalud|superfinanciera|senado|'
    r'secretaria|distrital|personeria|veeduria|contraloria|procuraduria|defensoria|'
    r'idrd|idiger|idpac|instituto distrital|concejo de bogota|unidad administrativa)\b')
EXCLUIR_FUENTE = {'youtube.com', 'twitter.com', 'x.com', 'facebook.com',
                  'instagram.com', 't.co', 'tiktok.com'}

# El titular tiene que nombrar el territorio para contar como noticia local.
# Sin esto, consultas como "ediles Bogotá" arrastran nacionales sin relación.
TERMINOS_LOCALES = [
    'barrios unidos', 'doce de octubre', 'siete de agosto', 'la castellana',
    'polo club', 'quinta mutis', 'simon bolivar', 'san fernando', 'metropolis',
    'jose joaquin vargas', 'entrerios', 'alcazares', 'santa sofia', 'los andes',
    'popular modelo', 'once de noviembre', 'rionegro', 'juan xxiii', 'benjamin herrera',
]
GOBIERNO_LOCAL = ['edil', 'ediles', 'junta administradora', 'jal ', 'alcaldia local',
                  'localidad', 'localidades']


def sin_tildes(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def compacta(s):
    return re.sub(r'[^a-z0-9]', '', sin_tildes(s))


def es_institucional(medio):
    """⚠️ El chequeo por palabra va sobre el nombre CON espacios, no sobre la
    forma compactada: `\\bgobernacion\\b` nunca casa dentro de
    'gobernaciondelvalle' porque ahí no hay frontera de palabra. Sobre la
    compactada solo se miran dominios, donde la frontera no existe igual."""
    plano = sin_tildes(medio)
    if '.gov.co' in plano or '.edu.co' in plano or '.mil.co' in plano:
        return True
    return bool(INSTITUCIONAL.search(plano))


def url_gn(q, dias):
    if 'colombia' not in compacta(q):
        q = f'{q} Colombia'
    consulta = urllib.parse.quote(f'{q} when:{dias}d')
    return (f'https://news.google.com/rss/search?q={consulta}'
            f'&hl=es-419&gl=CO&ceid=CO:es')


def trae(q, dias, grupo):
    try:
        req = urllib.request.Request(url_gn(q, dias), headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            xml = r.read()
    except Exception as e:
        print(f'    ! "{q}": {e}')
        return []
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f'    ! "{q}" XML: {e}')
        return []

    salida = []
    for it in raiz.iter('item'):
        titulo = (it.findtext('title') or '').strip()
        enlace = (it.findtext('link') or '').strip()
        src = it.find('source')
        medio = (src.text or '').strip() if src is not None else ''
        if not titulo or not enlace:
            continue
        # El título repite " - Medio" al final; se recorta solo si coincide.
        if medio and titulo.endswith(f' - {medio}'):
            titulo = titulo[: -len(medio) - 3].strip()
        if not medio or medio.lower() in EXCLUIR_FUENTE or es_institucional(medio):
            continue
        fecha = ''
        pub = it.findtext('pubDate')
        if pub:
            try:
                fecha = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
            except Exception:
                fecha = ''
        item = {'titulo': titulo, 'url': enlace, 'medio': medio,
                'fecha': fecha, 'grupo': grupo, 'q': q}
        if grupo == 'local':
            t = sin_tildes(titulo)
            item['exacto'] = any(x in t for x in TERMINOS_LOCALES)
            # Se conserva si nombra el territorio, o si habla de gobierno local
            # EN Bogotá. Lo demás es arrastre de la consulta, no noticia local.
            if not item['exacto'] and not (
                    'bogota' in t and any(g in t for g in GOBIERNO_LOCAL)):
                continue
        salida.append(item)
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=21)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    tareas = [(q, g) for g, qs in GRUPOS.items() for q in qs]
    with ThreadPoolExecutor(max_workers=6) as ex:
        lotes = list(ex.map(lambda t: trae(t[0], args.dias, t[1]), tareas))

    # Dedup por (título normalizado, medio): la misma nota sale en varias consultas.
    vistos, items = set(), []
    for lote in lotes:
        for it in lote:
            llave = (compacta(it['titulo'])[:90], compacta(it['medio']))
            if llave in vistos:
                continue
            vistos.add(llave)
            items.append(it)

    items.sort(key=lambda x: x['fecha'], reverse=True)

    grupos = {}
    for g in GRUPOS:
        del_g = [i for i in items if i['grupo'] == g]
        if g == 'local':   # primero los que nombran el territorio
            del_g.sort(key=lambda i: (not i.get('exacto'), i['fecha'] or ''), reverse=False)
        grupos[g] = {
            'titulares': del_g[:40],
            'n': len(del_g),
            'medios': len({compacta(i['medio']) for i in del_g}),
            'consultas': GRUPOS[g],
        }

    datos = {
        'v': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'ventana_dias': args.dias,
        'fuente': 'Google News RSS',
        'total': len(items),
        'medios': len({compacta(i['medio']) for i in items}),
        'grupos': grupos,
        'aviso': ('Mide cobertura de prensa, no realidad: la ausencia de titulares sobre un '
                  'tema significa que los medios no lo cubrieron en la ventana, no que no '
                  'esté pasando. Se excluyen comunicados de entidades públicas y redes.'),
    }

    for g, d in grupos.items():
        print(f'  {g:9} {d["n"]:4} titulares · {d["medios"]:3} medios')
    print(f'  TOTAL     {len(items):4} titulares · {datos["medios"]} medios · ventana {args.dias}d')

    if args.dry_run:
        for i in items[:8]:
            print(f'    [{i["grupo"]}] {i["medio"]}: {i["titulo"][:90]}')
        return

    os.makedirs(OUT, exist_ok=True)
    ruta = os.path.join(OUT, 'nsp-medios.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'  nsp-medios.json  {os.path.getsize(ruta)/1024:.0f} KB')


if __name__ == '__main__':
    main()
