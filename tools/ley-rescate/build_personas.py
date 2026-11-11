#!/usr/bin/env python3
"""Fotos y fichas de las personas del seguimiento de la Ley de Rescate.

  python3 tools/ley-rescate/build_personas.py

Congresistas: foto oficial del Senado (API pública) y de la Cámara (camara.gov.co/representantes).
Los demás: imagen principal de su artículo en Wikipedia, SOLO con licencia libre, y con su crédito.
Quien no tenga foto verificable sale con iniciales: nunca se adivina una cara.

Escribe imagenes/ley-rescate/{slug}.jpg, personas.json y la plantilla de cada bancada en votos.json.
"""
import io
import json
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
DEST = REPO / 'imagenes' / 'ley-rescate'
UA_NAV = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'
UA_WIKI = 'ricardoruiz.co-ley-rescate/1.0 (https://ricardoruiz.co)'
WIKI = {'José Manuel Restrepo': 'José Manuel Restrepo Abondano', 'Miguel Gómez Martínez': 'Miguel Gómez Martínez', 'Álvaro Uribe': 'Álvaro Uribe',
        'Gustavo Petro': 'Gustavo Petro', 'Mauricio Cárdenas': 'Mauricio Cárdenas Santamaría', 'Iván Duque': 'Iván Duque', 'Paloma Valencia': 'Paloma Valencia',
        'Carolina Corcho': 'Carolina Corcho', 'María Fernanda Cabal': 'María Fernanda Cabal', 'Vicky Dávila': 'Vicky Dávila',
        'María Fernanda Carrascal': 'María Fernanda Carrascal', 'Lisandro Junco': 'Lisandro Junco', 'Fabio Arias': 'Fabio Arias Giraldo',
        'Iván Cepeda': 'Iván Cepeda Castro', 'José Antonio Ocampo': 'José Antonio Ocampo', 'Alberto Carrasquilla': 'Alberto Carrasquilla Barrera',
        'Juan Camilo Restrepo': 'Juan Camilo Restrepo Salazar', 'Juan Daniel Oviedo': 'Juan Daniel Oviedo', 'Andrés Julián Rendón': 'Andrés Julián Rendón',
        'Luis Carlos Reyes': 'Luis Carlos Reyes Hernández', 'María Claudia Lacouture': 'María Claudia Lacouture', 'Jennifer Pedraza': 'Jennifer Pedraza'}
BLOQUE = [('salvacion', 'sn'), ('centro democratico', 'cd'), ('conservador', 'con'), ('cambio radical', 'cr'), ('partido de la u', 'u'), ('liberal', 'lib'),
          ('alianza social independiente', 'asi'), ('verde', 'verde'), ('pacto historico', 'pacto'), ('pa-vida|uraba|paz es vida', 'paz')]


def norm(s):
    return re.sub(r'\s+', ' ', ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')).strip()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', norm(s)).strip('-')


def bajar(url, ua=UA_NAV):
    # curl: la Cámara y el Senado cortan a urllib por TLS y por huella del cliente.
    r = subprocess.run(['curl', '-s', '-L', '-m', '60', '-A', ua, url], capture_output=True, check=False)
    return r.stdout


def foto(url, nombre, ua=UA_NAV):
    b = bajar(url, ua)
    try:
        im = Image.open(io.BytesIO(b)).convert('RGB')
    except Exception:                                         # noqa: BLE001
        return None
    w, h = im.size
    lado = min(w, h)
    arriba = 0 if h > w else 0
    x = (w - lado) // 2
    im = im.crop((x, arriba, x + lado, arriba + lado)).resize((180, 180), Image.LANCZOS)
    DEST.mkdir(parents=True, exist_ok=True)
    s = slug(nombre)
    im.save(DEST / f'{s}.jpg', quality=82, optimize=True)
    return f'imagenes/ley-rescate/{s}.jpg'


def wiki(titulo):
    q = urllib.parse.urlencode({'action': 'query', 'format': 'json', 'titles': titulo, 'prop': 'pageimages', 'piprop': 'name', 'redirects': 1})
    d = json.loads(bajar('https://es.wikipedia.org/w/api.php?' + q, UA_WIKI))
    pag = next(iter(d['query']['pages'].values()))
    arch = pag.get('pageimage')
    if not arch:
        return None
    q = urllib.parse.urlencode({'action': 'query', 'format': 'json', 'titles': 'File:' + arch, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 420})
    d = json.loads(bajar('https://commons.wikimedia.org/w/api.php?' + q, UA_WIKI))
    p = next(iter(d['query']['pages'].values()))
    ii = (p.get('imageinfo') or [{}])[0]
    m = ii.get('extmetadata') or {}
    lic = (m.get('LicenseShortName') or {}).get('value', '')
    if not re.search(r'CC|Public domain|Dominio p', lic, re.I) or re.search(r'NC|ND', lic):
        print('  licencia no libre:', titulo, lic)
        return None
    autor = re.sub(r'<[^>]+>', '', (m.get('Artist') or {}).get('value', '')).strip()[:70]
    return {'url': ii.get('thumburl') or ii.get('url'), 'licencia': lic, 'autor': autor, 'archivo': ii.get('descriptionurl')}


def bloque(partido):
    n = norm(partido)
    for pat, b in BLOQUE:
        if re.search(pat, n):
            return b
    raise SystemExit('partido sin bloque: ' + partido)


def main():
    sen = json.loads(bajar('https://app.senado.gov.co/backend/api/public/v1/senators?format=json'))
    html = bajar('https://www.camara.gov.co/representantes').decode('utf-8', 'ignore')
    reps = []
    for o in re.findall(r'\{[^{}]*"Partido":"[^"]*"[^{}]*\}', html):
        try:
            reps.append(json.loads(o))
        except json.JSONDecodeError:
            pass
    if len(sen) < 100 or len(reps) < 170:
        raise SystemExit(f'plantillas incompletas: {len(sen)} senadores, {len(reps)} representantes')
    gente = {}

    def persona(nombre, url, fuente):
        s = slug(nombre)
        if s not in gente:
            f = foto(url, nombre) if url else None
            gente[s] = {'n': nombre, 'foto': f, 'fuente': fuente if f else None}
        return s

    def nombre_sen(s):            # «Barguil Assis David Alejandro» → «David Alejandro Barguil Assis»
        p = s['name'].split()
        return ' '.join(p[2:] + p[:2]) if len(p) > 2 else s['name']
    votos = json.loads((AQUI / 'votos.json').read_text())
    for b in votos['bloques']:
        b['plantilla'] = {'senado': [], 'camara': []}
    por = {b['id']: b for b in votos['bloques']}
    # ⚠ La lista de integrantes sale de la ficha de la Comisión Tercera (/commissions), no del commission_id
    # de cada senador: en nov-2026 ese campo venía dañado para dos de los 15 (Martín Caicedo, 3040; Andrea
    # Padilla, 1016) y la gráfica mostró 13 senadores y 3 del Pacto cuando son 15 y 4.
    com = next(c for c in json.loads(bajar('https://app.senado.gov.co/backend/api/public/v1/commissions?format=json')) if c['id'] == 3)
    lista = [re.sub(r'\s*[—–-]\s*[^—–-]*$', '', l[1:]).strip() for l in com['description'].splitlines() if l.strip().startswith('*')]
    sen3 = []
    for n in lista:
        t = [x for x in norm(n).split() if len(x) > 2]
        hits = [s for s in sen if sum(x in norm(s['name']) for x in t) >= min(3, len(t))]
        if len(hits) != 1:
            raise SystemExit(f'Comisión Tercera: no casa «{n}» con un solo senador ({len(hits)})')
        sen3.append(hits[0])
    sueltos = [s['name'] for s in sen if str(s.get('commission_id')) == '3' and s not in sen3]
    if sueltos:
        raise SystemExit(f'senadores con commission_id 3 que la ficha no lista: {sueltos}')
    for s in sen3:
        n = nombre_sen(s)
        por[bloque(s['party_name'])]['plantilla']['senado'].append(persona(n, s.get('image'), 'Senado de la República'))
    for r in reps:
        if 'ercera' in (r.get('Comision') or ''):
            por[bloque(r['Partido'])]['plantilla']['camara'].append(persona(r['Nombre'], r.get('Imagen'), 'Cámara de Representantes'))
    for b in votos['bloques']:
        assert len(b['plantilla']['senado']) == b['senado'] and len(b['plantilla']['camara']) == b['camara'], b['id']
    (AQUI / 'votos.json').write_text(json.dumps(votos, ensure_ascii=False, indent=0))

    # Las voces: primero el registro oficial, después Wikipedia.
    voces = json.loads((AQUI / 'voces.json').read_text())
    sn = [(nombre_sen(s), s) for s in sen]
    for v in voces:
        if v.get('org'):
            continue
        v.pop('s', None)  # se recalcula: una foto vieja mal cruzada no puede sobrevivir a la corrida
        t = norm(v['q']).split()
        # Solo se busca en el registro del Congreso a quien está en el frente Congreso: un analista homónimo
        # recibiría la cara de otro (pasó con Simón Gómez contra el representante Simón Molina Gómez).
        es_con = v.get('g') == 'con'
        s_hit = next((s for n, s in sn if all(x in norm(n) for x in t)), None) if es_con else None
        r_hit = next((r for r in reps if all(x in norm(r['Nombre']) for x in t)), None) if es_con else None
        if s_hit:
            v['s'] = persona(nombre_sen(s_hit), s_hit.get('image'), 'Senado de la República')
        elif r_hit:
            v['s'] = persona(r_hit['Nombre'], r_hit.get('Imagen'), 'Cámara de Representantes')
        elif v['q'] in WIKI:
            w = wiki(WIKI[v['q']])
            if w and foto(w['url'], v['q'], UA_WIKI):
                s = slug(v['q'])
                gente[s] = {'n': v['q'], 'foto': f'imagenes/ley-rescate/{s}.jpg', 'fuente': 'Wikimedia Commons', 'credito': w['autor'], 'licencia': w['licencia'], 'archivo': w['archivo']}
                v['s'] = s
            else:
                print('sin foto:', v['q'])
        else:
            print('sin fuente:', v['q'])
    # Logos de organizaciones y fotos institucionales curadas a mano (imagenes-extra.json): el archivo ya está en imagenes/ley-rescate/.
    for s, d in json.loads((AQUI / 'imagenes-extra.json').read_text()).items():
        gente[s] = {k: v for k, v in d.items() if k not in ('q', 'url')}
        for v in voces:
            if v['q'] == d['q']:
                v['s'] = s
    (AQUI / 'voces.json').write_text(json.dumps(voces, ensure_ascii=False, indent=0))
    (AQUI / 'personas.json').write_text(json.dumps(gente, ensure_ascii=False, indent=0))
    print(len(gente), 'personas ·', sum(1 for g in gente.values() if g['foto']), 'con foto')


if __name__ == '__main__':
    sys.exit(main())
