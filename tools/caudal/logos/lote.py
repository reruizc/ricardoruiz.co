#!/usr/bin/env python3
"""
Lote de logos para el diccionario de Caudal — sin pagar un modelo por logo.

    python3 tools/caudal/logos/lote.py buscar      # sitio oficial + logo en Wikidata
    python3 tools/caudal/logos/lote.py adivinar    # dominio probable, verificado por el título
    python3 tools/caudal/logos/lote.py candidatos  # bajar y normalizar candidatos
    python3 tools/caudal/logos/lote.py elegir      # el modelo local escoge (Ollama)
    python3 tools/caudal/logos/lote.py hojas       # hojas de 50 para revisión humana
    python3 tools/caudal/logos/lote.py publicar --rechazar 3,17,42   # tras revisar

Objetivo: las ~600 organizaciones notorias de `empresas-para-logos.csv` (la lista
curada a mano en sep-2026) que todavía no tienen logo ni están marcadas «sin logo
verificable». Datos en `Bases de datos/caudal-logos/lote-02/` (gitignorado).

De dónde sale cada logo, en orden de confianza:
  1. **Wikidata P154** (imagen del logo en Wikimedia Commons), si la entidad que
     casa es una organización con el mismo nombre. Commons rinde el SVG a PNG.
  2. **La página oficial** (P856 de Wikidata): las imágenes de la cabecera que se
     llaman o se marcan como «logo» — el mismo criterio de fetch-logo-candidates.
Nada se adivina: sin entidad que case por nombre no hay sitio, y sin sitio no hay
logo. Cada candidato guarda la URL exacta de donde salió.

El modelo local (Ollama, visión) solo PRESELECCIONA: mira cada candidato y dice si
se ve la marca de esa organización. El que aprueba es una persona, en las hojas
de contacto. Un logo equivocado es peor que las iniciales.
"""
from __future__ import annotations

import base64, csv, io, json, os, re, subprocess, sys, tempfile, time, unicodedata
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Bases de datos' / 'caudal-logos'
LOTE = BASE / 'lote-02'
LISTA = BASE / 'empresas-para-logos.csv'
HECHOS = BASE / 'logos'
LEDGER = BASE / 'logos-fuentes.csv'
UA = 'CaudalLogos/1.0 (https://ricardoruiz.co; hola@ricardoruiz.co) Python-urllib'
UA_WEB = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36'
OLLAMA = 'http://127.0.0.1:11434/api/chat'
MODELO = os.environ.get('LOGO_MODELO', 'qwen3.8:27b')
S3 = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/caudal/logos/'
HOY = time.strftime('%Y-%m-%d')
COLOMBIA = 'Q739'
NO_ORG = {'Q5', 'Q11424', 'Q482994', 'Q7889', 'Q5398426', 'Q4167410', 'Q13442814', 'Q515', 'Q486972'}


def n(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'\b(s\.?\s?a\.?\s?s?\.?|sas|s a|ltda|e\.?s\.?p\.?|esp|inc|corp|colombia)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def get(url, ua=UA, accept='*/*', timeout=30, referer=None):
    h = {'User-Agent': ua, 'Accept': accept}
    if referer:
        h['Referer'] = referer
    with urlopen(Request(url, headers=h), timeout=timeout) as r:
        return r.read(), r.headers.get('content-type', ''), r.geturl()


def get_json(url):
    for i in range(3):
        try:
            return json.loads(get(url, accept='application/json')[0])
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def pendientes():
    rows = list(csv.DictReader(open(LISTA, encoding='utf-8-sig')))
    hechos = {f[:-4] for f in os.listdir(HECHOS) if f.endswith('.png')}
    vistos = {r['clave'] for r in csv.DictReader(open(LEDGER, encoding='utf-8'))}
    return [r for r in rows if r['clave'] not in hechos and r['clave'] not in vistos]


# ── 1 · buscar: la entidad en Wikidata ──────────────────────────────────────────
def _claims(ent, p):
    out = []
    for c in ent.get('claims', {}).get(p, []):
        v = c.get('mainsnak', {}).get('datavalue', {}).get('value')
        if isinstance(v, dict) and 'id' in v:
            out.append(v['id'])
        elif v is not None:
            out.append(v)
    return out


# Palabras que delatan el sector en la descripción de Wikidata (es/en). Sirven
# para desempatar homónimos: «Chubb» aseguradora frente a «Chubb Fire & Security»,
# «Olímpica» supermercado frente a «Olímpica Stéreo».
SECTOR_KW = {
    'seguros': 'insur|asegur|seguro', 'financiero': 'bank|banco|financ|fiduci|bolsa|credit|crédit|invest|payment|pago',
    'cripto': 'crypto|cripto|exchange|bitcoin|blockchain', 'pensiones': 'pension|pensión|fondo',
    'retail': 'supermark|supermerc|retail|tienda|store|almac|minor|department', 'consumo': 'consum|product|bebida|beverage|food',
    'alimentos': 'food|aliment|bebida|beverage|brew|cervec|lácte|dairy|snack', 'energia': 'energ|electric|eléctr|oil|petrol|gas|power|utility|hidro',
    'mineria': 'min|coal|carbón|gold|oro|nickel|níquel', 'construccion': 'construc|cement|cemento|ingenier|engineer|infra|vivienda|real estate|inmobil',
    'salud': 'health|salud|hospital|clínic|clinic|eps|ips|medic|médic', 'farma': 'pharma|farma|medic|drug|laborator',
    'tecnologia': 'software|tech|tecnolog|internet|digital|app|platform|plataforma|comput', 'telecom': 'telecom|mobile|móvil|operador|internet|cable',
    'transporte': 'transport|taxi|ride|movilidad|bus|logíst|logist|delivery|domicil', 'logistica': 'logist|logíst|shipping|cargo|carga|courier|mensajer|port',
    'aviacion': 'airline|aerol|aviat|aviac|airport|aeropuert', 'automotriz': 'automo|car|vehic|motor', 'textil': 'textil|textile|ropa|cloth|fashion|moda|apparel',
    'medios': 'newspaper|periódico|diario|radio|televis|tv|magazine|revista|media|medio', 'educacion': 'universi|educa|school|colegio|instituto',
    'industria': 'manufact|industr|chemic|químic|packag|empaque|steel|acero|plastic', 'turismo': 'hotel|turis|tourism|travel|viaje',
    'seguridad': 'secur|seguridad|vigilan', 'juegos': 'lotter|lotería|apuesta|betting|casino|gambl', 'agro': 'agri|agro|palm|café|coffee|flor|flower|sugar|azúcar|banan',
    'agua': 'water|agua|acueduct|aseo|waste|residu|sewer',
}


def elegir_entidad(todos, r):
    kw = SECTOR_KW.get(r.get('sector', ''), '')
    def pts(t):
        sec = bool(kw) and re.search(kw, t['desc'], re.I) is not None
        return 4 * t['colombia'] + 3 * sec + 2 * bool(t['logo']) + bool(t['web']), sec
    mejor = None
    for t in todos:
        p, sec = pts(t)
        # una entidad de otro país solo vale si la descripción coincide con el
        # sector: sin eso, un homónimo extranjero se cuela con su logo
        if not t['colombia'] and not sec:
            continue
        if not mejor or p > mejor[0]:
            mejor = (p, dict(t, puntos=p, sector_ok=sec))
    return mejor[1] if mejor else None


def buscar_uno(r):
    k = r['clave']
    dest = LOTE / 'wikidata' / f'{k}.json'
    if dest.exists():
        o = json.loads(dest.read_text())
        if o.get('v') == 2:
            o['wd'] = elegir_entidad(o['todos'], r)      # la regla puede cambiar sin volver a buscar
            dest.write_text(json.dumps(o, ensure_ascii=False))
            return o
    nombres = [re.sub(r'\(.*?\)', '', r['nombre']).strip()]
    for a in (r.get('alias') or '').split('|'):
        a = a.strip()
        if a and len(a) >= 4 and n(a) not in {n(x) for x in nombres}:
            nombres.append(a)
    objetivo = {n(x) for x in nombres + [r['nombre']]} - {''}
    ids = []
    for q in nombres[:3]:
        d = get_json('https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&type=item&limit=6'
                     f'&language=es&uselang=es&search={quote(q)}')
        for it in (d or {}).get('search', []):
            if it['id'] not in ids:
                ids.append(it['id'])
    todos = []
    if ids:
        d = get_json('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json'
                     f'&props=labels|aliases|descriptions|claims&languages=es|en&ids={"|".join(ids[:15])}')
        for qid, ent in ((d or {}).get('entities') or {}).items():
            etiquetas = [v['value'] for v in ent.get('labels', {}).values()]
            etiquetas += [a['value'] for lst in ent.get('aliases', {}).values() for a in lst]
            if not any(n(e) in objetivo for e in etiquetas):
                continue                      # sin el mismo nombre no es ella
            p31 = set(_claims(ent, 'P31'))
            if p31 & NO_ORG:
                continue                      # una persona, una película, un lugar
            desc = ' '.join(v['value'] for v in ent.get('descriptions', {}).values()).lower()
            col = COLOMBIA in _claims(ent, 'P17') or 'colombia' in desc
            logo = _claims(ent, 'P154')
            web = [w for w in _claims(ent, 'P856') if isinstance(w, str)]
            if not (logo or web):
                continue
            todos.append({'qid': qid, 'colombia': col, 'desc': desc[:200],
                          'logo': logo[0] if logo else '', 'web': web[0] if web else ''})
    out = {'v': 2, 'clave': k, 'nombre': r['nombre'], 'sector': r['sector'], 'todos': todos,
           'wd': elegir_entidad(todos, r)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False))
    return out


def etapa_buscar():
    rows = pendientes()
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(buscar_uno, rows))
    con = [x for x in res if x['wd']]
    print(f'{len(rows)} pendientes · {len(con)} con entidad en Wikidata · '
          f'{sum(1 for x in con if x["wd"]["logo"])} con logo en Commons · '
          f'{sum(1 for x in con if x["wd"]["web"])} con sitio oficial')


# ── 1b · adivinar: el dominio probable, verificado por el título ────────────────
# Para las que Wikidata no conoce. Se prueban dominios armados con el nombre
# (`arrozdiana.com.co`, `arroz-diana.com`…) y solo se acepta uno si la página
# dice el nombre de la organización en su <title> u og:site_name. Un dominio
# estacionado («este dominio está en venta») se descarta aunque lo diga.
TLDS = ('.com.co', '.co', '.com', '.org.co', '.org', '.gov.co')
STOP = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'grupo', 'sa', 'sas', 'the', 'and', 'en', 'para'}
PARQUEADO = re.compile(r'for sale|en venta|domain|dominio|parked|godaddy|sedo|hugedomains|afternic|coming soon|under construction', re.I)


def _slugs(r):
    base = [re.sub(r'\(.*?\)', '', r['nombre'])] + re.findall(r'\((.*?)\)', r['nombre'])
    base += [a for a in (r.get('alias') or '').split('|') if a.strip()]
    out = []
    for t in base:
        for parte in re.split(r'[/,]', t):
            w = [x for x in n(parte).split() if x]
            for sl in (''.join(w), '-'.join(w)):
                if len(sl) >= 4 and sl not in out:
                    out.append(sl)
    return out[:5]


def _titulo(html):
    t = re.findall(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)[:1]
    t += re.findall(r'<meta[^>]+(?:og:site_name|og:title)[^>]+content=["\'](.*?)["\']', html, re.I)
    t += re.findall(r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:og:site_name|og:title)', html, re.I)
    return ' '.join(t)


def adivinar_uno(r):
    dest = LOTE / 'wikidata' / f'{r["clave"]}.json'
    o = json.loads(dest.read_text())
    if o.get('wd') or 'adivinado' in o:
        return o
    clave_n = [w for w in n(re.sub(r'\(.*?\)', '', r['nombre'])).split() if w not in STOP and len(w) >= 3]
    hallado = ''
    for sl in _slugs(r):
        for tld in TLDS:
            url = f'https://www.{sl}{tld}/'
            try:
                html, ct, final = get(url, ua=UA_WEB, accept='text/html', timeout=8)
            except Exception:
                continue
            html = html[:200000].decode('utf-8', 'replace')
            tit = _titulo(html)
            tn = n(tit)
            if PARQUEADO.search(tit) or not clave_n:
                continue
            if all(w in tn.split() or w in tn.replace(' ', '') for w in clave_n):
                hallado = final
                break
        if hallado:
            break
    o['adivinado'] = hallado
    dest.write_text(json.dumps(o, ensure_ascii=False))
    return o


def etapa_adivinar():
    rows = {r['clave']: r for r in pendientes()}
    infos = [json.loads(p.read_text()) for p in sorted((LOTE / 'wikidata').glob('*.json'))]
    sin = [rows[i['clave']] for i in infos if not i.get('wd') and i['clave'] in rows]
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(adivinar_uno, sin))
    ok = [x for x in res if x.get('adivinado')]
    # las que ganaron sitio vuelven a pasar por candidatos
    for x in ok:
        m = LOTE / 'cand' / x['clave'] / 'meta.json'
        if m.exists() and not any(c.get('archivo') for c in json.loads(m.read_text())['cand']):
            m.unlink()
    print(f'{len(sin)} sin Wikidata · {len(ok)} con sitio adivinado y verificado por el título')


# ── 2 · candidatos ──────────────────────────────────────────────────────────────
def candidate_urls(page_url, html):
    scored = []
    for tag in re.findall(r'<(?:img|source|link|meta)\b[^>]*>', html, re.I | re.S):
        attrs = tag.lower()
        urls = []
        for key in ('src', 'data-src', 'data-lazy-src', 'href', 'content'):
            m = re.search(rf'\b{key}\s*=\s*([\'"])(.*?)\1', tag, re.I | re.S)
            if m:
                urls.append(m.group(2))
        ss = re.search(r'\b(?:data-)?srcset\s*=\s*([\'"])(.*?)\1', tag, re.I | re.S)
        if ss:
            urls.extend(p.strip().split()[0] for p in ss.group(2).split(',') if p.strip())
        for raw in urls:
            if raw.startswith('data:'):
                continue
            absolute = urljoin(page_url, raw)
            lower = absolute.lower().split('?', 1)[0]
            ext_ok = re.search(r'\.(?:svg|png|webp|jpe?g)$', lower) is not None
            score = 0
            if 'logo' in attrs or 'logo' in lower:
                score += 20
            if any(x in attrs for x in ('header', 'navbar', 'brand', 'site-logo')):
                score += 8
            if tag.lower().startswith('<link') and any(x in attrs for x in ('apple-touch',)):
                score += 3
            if any(x in lower for x in ('footer', 'partner', 'aliado', 'cliente', 'sponsor', 'patrocin', 'certif', 'iso', 'sello', 'banner', 'slide')):
                score -= 15
            if ext_ok and score > 0:
                scored.append((score, absolute))
    seen = set()
    return [u for _, u in sorted(scored, reverse=True) if not (u in seen or seen.add(u))][:4]


def remove_edge_white(image):
    rgba = image.convert('RGBA')
    w, h = rgba.size
    px = rgba.load()
    ok = lambda x, y: px[x, y][3] > 0 and min(px[x, y][:3]) >= 245   # noqa: E731
    q = deque()
    seen = set()
    for x in range(w):
        q.extend(((x, 0), (x, h - 1)))
    for y in range(h):
        q.extend(((0, y), (w - 1, y)))
    while q:
        x, y = q.popleft()
        if (x, y) in seen or not ok(x, y):
            continue
        seen.add((x, y))
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        if x: q.append((x - 1, y))
        if x + 1 < w: q.append((x + 1, y))
        if y: q.append((x, y - 1))
        if y + 1 < h: q.append((x, y + 1))
    return rgba


def to_png(raw, ctype, dest):
    is_svg = 'svg' in ctype.lower() or b'<svg' in raw[:2000]
    with tempfile.TemporaryDirectory() as tmp:
        if is_svg:
            svg, png = Path(tmp) / 's.svg', Path(tmp) / 's.png'
            svg.write_bytes(raw)
            subprocess.run(['sips', '-s', 'format', 'png', str(svg), '--out', str(png)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            im = Image.open(png)
        else:
            im = Image.open(io.BytesIO(raw))
        im.load()
        had_alpha = 'A' in im.getbands() or im.info.get('transparency') is not None
        rgba = im.convert('RGBA')
        if not had_alpha:
            rgba = remove_edge_white(rgba)
        bbox = rgba.getbbox()
        if not bbox:
            raise ValueError('imagen vacía')
        rgba = rgba.crop(bbox)
        if max(rgba.size) < 48:
            raise ValueError(f'muy pequeña ({rgba.size[0]}x{rgba.size[1]})')
        esc = 512 / max(rgba.size)
        rgba = rgba.resize((max(1, round(rgba.width * esc)), max(1, round(rgba.height * esc))), Image.Resampling.LANCZOS)
        rgba.save(dest, 'PNG', optimize=True)


def candidatos_uno(info):
    k, wd = info['clave'], info['wd']
    carpeta = LOTE / 'cand' / k
    meta = carpeta / 'meta.json'
    if meta.exists():
        return json.loads(meta.read_text())
    carpeta.mkdir(parents=True, exist_ok=True)
    fuentes = []
    if wd and wd['logo']:
        fn = wd['logo'].replace(' ', '_')
        fuentes.append(('commons', f'https://commons.wikimedia.org/wiki/Special:FilePath/{quote(fn)}?width=512',
                        f'https://commons.wikimedia.org/wiki/File:{quote(fn)}', UA))
    web = (wd or {}).get('web') or info.get('adivinado') or ''
    if web:
        try:
            html, ct, final = get(web, ua=UA_WEB, accept='text/html,application/xhtml+xml', timeout=25)
            html = html.decode('utf-8', 'replace')
            for u in candidate_urls(final, html):
                fuentes.append(('sitio', u, final, UA_WEB))
        except Exception as exc:
            fuentes.append(('error', '', web, f'{exc}'[:120]))
    out = []
    for i, (metodo, url, ref, ua) in enumerate(fuentes, 1):
        if metodo == 'error':
            out.append({'i': i, 'metodo': 'error', 'pagina': ref, 'error': ua})
            continue
        dest = carpeta / f'{i:02d}.png'
        try:
            raw, ct, _ = get(url, ua=ua, accept='image/*', timeout=30, referer=ref if metodo == 'sitio' else None)
            to_png(raw, ct, dest)
            out.append({'i': i, 'metodo': metodo if (wd or {}).get('web') or metodo == 'commons' else 'dominio',
                        'url': url, 'pagina': ref, 'archivo': dest.name})
        except Exception as exc:
            out.append({'i': i, 'metodo': metodo, 'url': url, 'pagina': ref, 'error': f'{exc}'[:120]})
    res = {'clave': k, 'nombre': info['nombre'], 'sector': info['sector'], 'wd': wd, 'cand': out}
    meta.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def etapa_candidatos():
    infos = [json.loads(p.read_text()) for p in sorted((LOTE / 'wikidata').glob('*.json'))]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(candidatos_uno, infos))
    con = [r for r in res if any(c.get('archivo') for c in r['cand'])]
    print(f'{len(res)} buscadas · {len(con)} con al menos un candidato · '
          f'{sum(len([c for c in r["cand"] if c.get("archivo")]) for r in res)} candidatos en total')


# ── 3 · elegir: el modelo local mira cada candidato ─────────────────────────────
PROMPT = ('Mira la imagen. ¿Es el logotipo de la organización «{nombre}» (sector {sector}, Colombia)? '
          'Un logotipo es la marca: el nombre escrito con su tipografía y/o el símbolo. NO cuenta: una foto, '
          'un banner publicitario, un ícono genérico, el logo de OTRA organización, un sello o certificación. '
          'Responde SOLO con JSON: {{"es_logo": true|false, "texto_visible": "lo que se lee en la imagen", '
          '"confianza": "alta"|"media"|"baja"}}')


def ver(png_path, nombre, sector):
    im = Image.open(png_path).convert('RGBA')
    fondo = Image.new('RGBA', (im.width + 40, im.height + 40), (255, 255, 255, 255))
    fondo.alpha_composite(im, (20, 20))
    buf = io.BytesIO()
    fondo.convert('RGB').save(buf, 'PNG')
    body = {'model': MODELO, 'stream': False, 'think': False, 'format': 'json',
            'options': {'temperature': 0},
            'messages': [{'role': 'user', 'content': PROMPT.format(nombre=nombre, sector=sector),
                          'images': [base64.b64encode(buf.getvalue()).decode()]}]}
    req = Request(OLLAMA, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=300) as r:
        txt = json.loads(r.read())['message']['content']
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'\{.*\}', txt, re.S)
        return json.loads(m.group(0)) if m else {'es_logo': False, 'texto_visible': txt[:80], 'confianza': 'baja'}


def etapa_elegir():
    (LOTE / 'elegidos').mkdir(parents=True, exist_ok=True)
    conf = {'alta': 3, 'media': 2, 'baja': 1}
    filas = []
    metas = sorted((LOTE / 'cand').glob('*/meta.json'))
    for j, mp in enumerate(metas, 1):
        m = json.loads(mp.read_text())
        juicio_p = mp.parent / 'juicio.json'
        juicio = json.loads(juicio_p.read_text()) if juicio_p.exists() else {}
        for c in m['cand']:
            if not c.get('archivo') or str(c['i']) in juicio:
                continue
            try:
                juicio[str(c['i'])] = ver(mp.parent / c['archivo'], m['nombre'], m['sector'])
            except Exception as exc:
                juicio[str(c['i'])] = {'es_logo': False, 'error': f'{exc}'[:100], 'confianza': 'baja'}
            juicio_p.write_text(json.dumps(juicio, ensure_ascii=False))
        mejor = None
        for c in m['cand']:
            v = juicio.get(str(c['i']))
            if not v or not v.get('es_logo'):
                continue
            nombre_n, texto_n = n(m['nombre']), n(v.get('texto_visible', ''))
            lee = bool(nombre_n) and (nombre_n in texto_n or any(w in texto_n.split() for w in nombre_n.split() if len(w) >= 4))
            p = conf.get(v.get('confianza'), 1) + 2 * lee + (1 if c['metodo'] == 'commons' else 0)
            if not mejor or p > mejor[0]:
                mejor = (p, c, v, lee)
        if mejor:
            p, c, v, lee = mejor
            dest = LOTE / 'elegidos' / f'{m["clave"]}.png'
            dest.write_bytes((mp.parent / c['archivo']).read_bytes())
            filas.append({'clave': m['clave'], 'nombre': m['nombre'], 'sector': m['sector'], 'metodo': c['metodo'],
                          'url_fuente': c['url'], 'pagina': c['pagina'], 'confianza': v.get('confianza', ''),
                          'lee_nombre': int(lee), 'texto_visible': v.get('texto_visible', '')[:80],
                          'sector_ok': int(bool((m.get('wd') or {}).get('sector_ok', True)))})
        if j % 25 == 0:
            print(f'… {j}/{len(metas)} · {len(filas)} elegidos', flush=True)
    with open(LOTE / 'elegidos.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()) if filas else ['clave'])
        w.writeheader()
        w.writerows(filas)
    print(f'{len(metas)} con candidatos · {len(filas)} con un logo preseleccionado · '
          f'{sum(f["lee_nombre"] for f in filas)} donde el modelo lee el nombre')


# ── 4 · hojas de contacto ───────────────────────────────────────────────────────
def _fuente(tam, negrita=False):
    for f in ([ROOT / 'tools/pacto-1v-2026/fonts/Inter-Bold.ttf'] if negrita else []) + [ROOT / 'tools/pacto-1v-2026/fonts/Inter-Regular.ttf']:
        if f.exists():
            return ImageFont.truetype(str(f), tam)
    return ImageFont.load_default()


def etapa_hojas():
    filas = list(csv.DictReader(open(LOTE / 'elegidos.csv', encoding='utf-8')))
    # lo que el modelo leyó con su nombre va primero: se revisa más rápido
    filas.sort(key=lambda f: (-int(f['lee_nombre']), f['sector'], f['nombre']))
    out = LOTE / 'hojas'
    out.mkdir(exist_ok=True)
    for p in out.glob('*.png'):
        p.unlink()
    COL, FIL, W, H = 5, 10, 300, 210
    f_n, f_s, f_num = _fuente(15, True), _fuente(12), _fuente(14, True)
    with open(LOTE / 'revision.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['n', 'clave', 'nombre', 'metodo', 'confianza', 'lee_nombre', 'url_fuente'])
        for h in range(0, len(filas), COL * FIL):
            lote = filas[h:h + COL * FIL]
            hoja = Image.new('RGB', (COL * W, FIL * H), (240, 240, 240))
            d = ImageDraw.Draw(hoja)
            for i, f in enumerate(lote):
                num = h + i + 1
                x, y = (i % COL) * W, (i // COL) * H
                d.rectangle([x + 6, y + 6, x + W - 6, y + H - 6], fill=(255, 255, 255), outline=(220, 220, 225))
                im = Image.open(LOTE / 'elegidos' / f'{f["clave"]}.png').convert('RGBA')
                im.thumbnail((W - 60, 110))
                hoja.paste(im, (x + (W - im.width) // 2, y + 18 + (110 - im.height) // 2), im)
                d.text((x + 14, y + 12), str(num), fill=(61, 110, 184), font=f_num)
                d.text((x + 14, y + 142), f['nombre'][:34], fill=(20, 22, 28), font=f_n)
                marca = ('* lee el nombre · ' if f['lee_nombre'] == '1' else '') + f['metodo'] + ' · ' + f['confianza']
                if f.get('sector_ok') == '0':
                    marca = '¿otro sector? · ' + marca
                d.text((x + 14, y + 164), marca.replace('✓', '*'), fill=(102, 112, 133), font=f_s)
                d.text((x + 14, y + 182), urlparse(f['url_fuente']).netloc[:38], fill=(150, 155, 165), font=f_s)
                w.writerow([num, f['clave'], f['nombre'], f['metodo'], f['confianza'], f['lee_nombre'], f['url_fuente']])
            hoja.save(out / f'hoja-{h // (COL * FIL) + 1:02d}.png', optimize=True)
    print(f'{len(filas)} logos en {len(list(out.glob("*.png")))} hojas · {out}')


# ── 5 · publicar lo aprobado ────────────────────────────────────────────────────
def etapa_publicar(rechazar):
    rev = list(csv.DictReader(open(LOTE / 'revision.csv', encoding='utf-8')))
    eleg = {f['clave']: f for f in csv.DictReader(open(LOTE / 'elegidos.csv', encoding='utf-8'))}
    aprobados = [r for r in rev if int(r['n']) not in rechazar]
    led = list(csv.DictReader(open(LEDGER, encoding='utf-8')))
    ya = {r['clave'] for r in led}
    for r in aprobados:
        k = r['clave']
        (HECHOS / f'{k}.png').write_bytes((LOTE / 'elegidos' / f'{k}.png').read_bytes())
        f = eleg[k]
        nota = ('Logo de Wikimedia Commons enlazado desde Wikidata.' if f['metodo'] == 'commons'
                else 'Logo de la cabecera del sitio oficial.') + ' Preseleccionado por modelo local y revisado a mano.'
        if k not in ya:
            led.append({'clave': k, 'archivo': f'{k}.png', 'url_fuente': f['url_fuente'], 'fecha': HOY, 'nota': nota})
        subprocess.run(['aws', 's3', 'cp', str(HECHOS / f'{k}.png'), S3 + f'{k}.png', '--content-type', 'image/png',
                        '--cache-control', 'public, max-age=86400', '--only-show-errors'], check=True)
    with open(LEDGER, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['clave', 'archivo', 'url_fuente', 'fecha', 'nota'])
        w.writeheader()
        w.writerows(led)
    subprocess.run(['aws', 's3', 'cp', str(LEDGER), S3 + 'fuentes.csv', '--content-type', 'text/csv; charset=utf-8',
                    '--only-show-errors'], check=True)
    print(f'{len(aprobados)} publicados · {len(rechazar)} rechazados')


if __name__ == '__main__':
    etapa = sys.argv[1] if len(sys.argv) > 1 else ''
    LOTE.mkdir(parents=True, exist_ok=True)
    if etapa == 'buscar':
        etapa_buscar()
    elif etapa == 'adivinar':
        etapa_adivinar()
    elif etapa == 'candidatos':
        etapa_candidatos()
    elif etapa == 'elegir':
        etapa_elegir()
    elif etapa == 'hojas':
        etapa_hojas()
    elif etapa == 'publicar':
        rech = set()
        if '--rechazar' in sys.argv:
            rech = {int(x) for x in sys.argv[sys.argv.index('--rechazar') + 1].split(',') if x.strip()}
        etapa_publicar(rech)
    else:
        print(__doc__)
