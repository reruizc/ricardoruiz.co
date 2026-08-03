#!/usr/bin/env python3
"""
Cosecha la FICHA INDIVIDUAL de cada proyecto de origen Cámara para recuperar lo
que el listado (harvest_camara_historico.py) no trae: fecha de radicación,
fechas de aprobación por debate, comisión y las gacetas del trámite.

POR QUÉ EXISTE (el hueco que cierra)
------------------------------------
El listado AJAX de Cámara da título/estado/autores pero NO fechas. Consecuencia
medida antes de este script: de los 4.080 proyectos de origen Cámara que entran
al dataset (27% del universo), 4.080 venían con fecha_presentacion = None. Por
eso build_dataset calculaba el embudo y dias_a_primer_debate SOLO sobre el
registro del Senado (`embudo_alcance: 'registro_senado'`), y el hallazgo bandera
—"74% mueren antes del primer debate"— estaba medido sobre medio universo.

Las fechas SÍ están, una por una, en la ficha pública: GET /{link_web}.

QUÉ TRAE LA FICHA (verificado en muestras de 2015, 2019, 2023, 2025 y 2026)
---------------------------------------------------------------------------
  · Fecha de Radicación Cámara / Senado      → KPI cards (dd/m/aaaa)
  · Comisión, tipo de ley, estado, objeto
  · Gaceta de radicación, con DEEP-LINK de la Imprenta que trae ent+fec+num —
    justo el triple que necesita tools/caudal/actas/descargar_gaceta.py. Es la
    llave para bajar el texto de las gacetas de Cámara (que hasta ahora no
    teníamos: 0% de los proyectos de Cámara tenían texto indexado).
  · Un acordeón por debate ("Primer/Segundo Debate Cámara|Senado") con ponentes
    y publicaciones: ponencia (con su gaceta) y actas de anuncio/aprobación con
    su fecha en prosa ("Acta 20 del 4 de junio de 2014").

QUÉ **NO** TRAE — y no se inventa
---------------------------------
La CAUSA del archivo. Se buscó explícitamente ("190", "tránsito", "vencimiento",
"Ley 5", "motivo", "causa") en fichas archivadas de 4 épocas distintas: los
únicos hits son ruido del menú y del footer del sitio. La ficha dice "Archivado"
y nada más. Así que los archivados de Cámara siguen cayendo en ARCHIVADO_OTRO y
NUNCA en ARCHIVADO_TIEMPO — eso no es "no murió por tiempo", es "la fuente no lo
informa", y stats.json lo expone aparte (archivado_causa_no_informada). Derivar
el art. 190 de las fechas sería estimarlo, no medirlo.

MECÁNICA
--------
GET https://www.camara.gov.co/{link_web}/  (seguir redirecciones, con UA de
navegador). Es OTRO host que leyes.senado.gov.co: no tiene su WAF, así que
admite concurrencia moderada. Aun así el ritmo es cortés (workers pocos + una
pausa mínima), porque no hay prisa: el harvester es resumible.

CACHÉ: se guarda solo el FRAGMENTO de la ficha (4-10 KB), no el HTML completo
(730 KB, casi todo menú y CSS del sitio). Así las 4.080 fichas caben en ~30 MB
en vez de ~3 GB, y se puede re-parsear sin volver a la red (--offline).

Uso:
  python3 tools/leyes-senado/harvest_camara_fichas.py                 # las que faltan
  python3 tools/leyes-senado/harvest_camara_fichas.py --workers 6
  python3 tools/leyes-senado/harvest_camara_fichas.py --offline       # re-parsea el caché
  python3 tools/leyes-senado/harvest_camara_fichas.py --limit 20      # prueba
  python3 tools/leyes-senado/harvest_camara_fichas.py --todos         # incl. los que ya cruzaron al Senado

Salidas (gitignored, en Bases de datos/leyes-senado/camara/):
  fichas/raw/{slug}.html   fragmento cacheado (resumible)
  fichas.jsonl             una ficha parseada por línea  → lo lee camara_merge.py
"""
import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = 'https://www.camara.gov.co'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
OUT = SRC / 'camara'
RAWDIR = OUT / 'fichas' / 'raw'
DEST = OUT / 'fichas.jsonl'

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camara_merge as cam  # noqa: E402

# ------------------------------------------------------------------ descarga

def curl(url, timeout=90, retries=3):
    """GET siguiendo redirecciones. Devuelve '' si nunca respondió cuerpo.

    Medido: la primera petición a una ficha vieja puede devolver 0 bytes y a la
    segunda responder 200 con el HTML completo (el sitio calienta la caché de la
    URL). Por eso los reintentos existen incluso sin error de red."""
    for intento in range(retries):
        r = subprocess.run(
            ['/usr/bin/curl', '-s', '-L', '-A', UA, '--max-time', str(timeout), url],
            capture_output=True)
        body = r.stdout.decode('utf-8', 'replace')
        if len(body) > 5000:          # una ficha real ronda los 730 KB
            return body
        if intento < retries - 1:
            time.sleep(2 * (intento + 1))
    return ''


# ------------------------------------------------------------------ recorte

_RE_STYLE = re.compile(r'<style[^>]*>.*?</style>', re.S)
_RE_SCRIPT = re.compile(r'<script[^>]*>.*?</script>', re.S)
_RE_SVG = re.compile(r'<svg.*?</svg>', re.S)


def recortar(html):
    """Deja solo la región de la ficha (4-10 KB) — el resto es menú y CSS."""
    h = _RE_SVG.sub(' ', _RE_SCRIPT.sub(' ', _RE_STYLE.sub(' ', html)))
    i = h.find('pl-print-actions')
    if i < 0:
        i = h.find('pl-kpi-label')
    if i < 0:
        return ''
    j = max(h.rfind('</details>'), h.rfind('pl-accordion'), h.rfind('pl-pub-item'))
    if j <= i:
        j = min(len(h), i + 40000)
    return h[i:j + 400]


# ------------------------------------------------------------------ parseo

_MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
          'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
          'noviembre': 11, 'diciembre': 12}

_RE_DMY = re.compile(r'\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b')
# "4 de junio de 2014"
_RE_PROSA = re.compile(r'\b(\d{1,2})\s+de\s+([a-zñ]+)\s+de\s+(\d{4})\b', re.I)
# "Junio 10 2015" / "Mayo 20 2014"
_RE_MES_DIA = re.compile(r'\b([a-zñ]+)\s+(\d{1,2})\s+(\d{4})\b', re.I)


def _sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn')


def _iso(d, m, y):
    try:
        if not (1 <= m <= 12 and 1 <= d <= 31 and 1985 <= y <= 2030):
            return None
        import datetime
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return None


def fecha_de(txt):
    """Primera fecha reconocible del texto, en cualquiera de los 3 formatos que
    usa la ficha. None si no hay (no se adivina)."""
    if not txt:
        return None
    m = _RE_DMY.search(txt)
    if m:
        return _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    plano = _sin_tildes(txt).lower()
    m = _RE_PROSA.search(plano)
    if m and m.group(2) in _MESES:
        return _iso(int(m.group(1)), _MESES[m.group(2)], int(m.group(3)))
    m = _RE_MES_DIA.search(plano)
    if m and m.group(1) in _MESES:
        return _iso(int(m.group(2)), _MESES[m.group(1)], int(m.group(3)))
    return None


def _texto(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


_RE_KPI = re.compile(r'pl-kpi-label">([^<]*)<.*?pl-kpi-value">([^<]*)<', re.S)
_RE_CARD = re.compile(r'pl-title">([^<]*)</div>\s*<div class="pl-body">(.*?)</div>\s*</div>', re.S)
_RE_DETAILS = re.compile(r'<details.*?</details>', re.S)
_RE_SUMMARY = re.compile(r'<summary[^>]*>(.*?)</summary>', re.S)
_RE_LI = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
_RE_HREF = re.compile(r'href="([^"]*)"')
_RE_GACETA = re.compile(r'Gaceta\s*(?:No\.?)?\s*(\d{1,4})\s*(?:/|del?\s+(?:a[nñ]o\s+)?)\s*(\d{4})', re.I)
_RE_ORDINALES = ('Primera', 'Segunda', 'Tercera', 'Cuarta', 'Quinta', 'Sexta', 'Séptima')


def _gaceta_num(txt):
    m = _RE_GACETA.search(txt or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def _deep_link(href):
    """Del href de la Imprenta saca (ent, fec, num) — el triple que necesita
    descargar_gaceta.py. El HTML trae las & escapadas como &#038;."""
    if not href or 'index2.xhtml' not in href:
        return None
    h = href.replace('&#038;', '&').replace('&amp;', '&')
    q = dict(re.findall(r'[?&]([a-z]+)=([^&]*)', h))
    ent, fec, num = q.get('ent', ''), q.get('fec', ''), q.get('num', '')
    if not (fec and num):
        return None
    from urllib.parse import unquote
    return {'ent': unquote(ent) or 'Cámara', 'fec': fec, 'num': num}


def _comision(txt):
    plano = _sin_tildes(txt or '').lower()
    for o in _RE_ORDINALES:
        if _sin_tildes(o).lower() in plano:
            return o
    return ''


def parse_ficha(frag, slug):
    """Fragmento de ficha → dict. Campos ausentes quedan None/[] — nunca se
    rellenan por inferencia."""
    kpis = [(a.strip(), b.strip()) for a, b in _RE_KPI.findall(frag)]
    cards = {}
    for t, b in _RE_CARD.findall(frag):
        cards.setdefault(t.strip(), []).append(_texto(b))

    # Los KPI vienen en dos grupos con las MISMAS etiquetas 'Cámara'/'Senado':
    # primero los números de radicado, después las fechas. Se distinguen por el
    # contenido (una fecha trae '/'), no por la posición, que puede variar.
    fechas = {'camara': None, 'senado': None}
    numeros = {'camara': None, 'senado': None}
    extra = {}
    for label, val in kpis:
        low = _sin_tildes(label).lower()
        if low in ('camara', 'senado'):
            f = fecha_de(val)
            if f:
                fechas[low] = fechas[low] or f
            elif val and val not in ('—', '-', '–'):
                numeros[low] = numeros[low] or val
        else:
            extra[low] = val

    # debates: un <details> por debate, con ponentes y publicaciones
    debates = []
    for det in _RE_DETAILS.findall(frag):
        ms = _RE_SUMMARY.search(det)
        nombre = _texto(ms.group(1)) if ms else ''
        cuerpo = det[ms.end():] if ms else det
        ponentes, pubs = [], []
        # Los <li> de ponentes son texto pelado; los de publicaciones traen un
        # <div> con el rótulo y (a veces) un <a> con la gaceta.
        for li in _RE_LI.findall(cuerpo):
            txt = _texto(li)
            if not txt:
                continue
            if '<div' in li or 'Gaceta' in txt:
                href = _RE_HREF.search(li)
                pubs.append({
                    'texto': txt,
                    'gaceta': _gaceta_num(txt),
                    'fecha': fecha_de(txt),
                    'deep': _deep_link(href.group(1) if href else ''),
                })
            else:
                ponentes.append(txt)
        debates.append({'nombre': nombre, 'ponentes': ponentes, 'publicaciones': pubs})

    # gaceta de radicación + su deep-link (bloque 'Publicación' de arriba)
    gaceta_rad, deep_rad, pdf_url = None, None, None
    for m in re.finditer(r'pl-pub-item">(.*?)</div>', frag, re.S):
        chunk = m.group(1)
        txt = _texto(chunk)
        href_m = _RE_HREF.search(chunk)
        href = href_m.group(1) if href_m else ''
        if gaceta_rad is None:
            gaceta_rad = _gaceta_num(txt)
        if deep_rad is None:
            deep_rad = _deep_link(href)
        if pdf_url is None and href.lower().endswith('.pdf'):
            pdf_url = href.replace('&#038;', '&')

    estado = None
    me = re.search(r'estado-valor">([^<]*)<', frag)
    if me:
        estado = me.group(1).strip()

    return {
        'link_web': slug,
        'nro_camara': numeros['camara'],
        'nro_senado': numeros['senado'],
        'fecha_radicacion_camara': fechas['camara'],
        'fecha_radicacion_senado': fechas['senado'],
        'comision': _comision(' '.join(cards.get('Comisión(es)', []))),
        'tipo_de_ley': extra.get('tipo de ley'),
        'origen': extra.get('origen'),
        'legislatura': extra.get('legislatura'),
        'estado_ficha': estado,
        'objeto': (cards.get('Objeto del proyecto') or [''])[0][:1200] or None,
        'gaceta_radicacion': gaceta_rad,
        'gaceta_radicacion_deep': deep_rad,
        'pdf_url': pdf_url,
        'debates': debates,
    }


# ------------------------------------------------------------------ objetivo

def objetivo(todos=False):
    """Los slugs a cosechar: por defecto solo los proyectos de Cámara que ENTRAN
    al dataset (los que nunca cruzaron al Senado y por tanto no tienen fecha por
    ningún otro lado). Con --todos, cualquier item de origen Cámara.

    Incluye la legislatura EN CURSO leyendo el rastreo diario: el listado
    histórico se cachea por legislatura, así que la viva se le queda corta y sin
    esto los radicados de hoy nunca tendrían ficha (ni fecha)."""
    rows = [json.loads(l) for l in open(OUT / 'camara.jsonl', encoding='utf-8') if l.strip()]
    vistos = {(r.get('nro_camara'), r.get('legislatura')) for r in rows}
    for p in sorted((SRC / 'diario-camara').glob('*/proyectos.jsonl')):
        for line in p.open(encoding='utf-8'):
            if not line.strip():
                continue
            r = json.loads(line)
            k = (r.get('numero_camara'), r.get('legislatura'))
            if k not in vistos:
                vistos.add(k)
                rows.append({'nro_camara': r.get('numero_camara'),
                             'nro_senado': r.get('numero_senado'),
                             'titulo': r.get('titulo'), 'tipo': r.get('tipo'),
                             'origen': r.get('origen'), 'link_web': r.get('link_web'),
                             'legislatura': r.get('legislatura')})
    if todos:
        return sorted({r['link_web'] for r in rows
                       if r.get('link_web') and (r.get('origen') or '') == 'Cámara'})
    raw_pdly = [json.loads(l) for l in open(SRC / 'pdly.jsonl', encoding='utf-8')]
    raw_pal = [json.loads(l) for l in open(SRC / 'pal.jsonl', encoding='utf-8')]
    ex_p, ex_a, _ = cam.merge(raw_pdly, raw_pal, rows)
    return sorted({r['_link_web'] for r in ex_p + ex_a if r.get('_link_web')})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--offline', action='store_true',
                    help='no toca la red: re-parsea el caché ya bajado')
    ap.add_argument('--todos', action='store_true',
                    help='incluye los de Cámara que ya cruzaron al Senado')
    ap.add_argument('--force', action='store_true', help='re-baja aunque haya caché')
    a = ap.parse_args()

    RAWDIR.mkdir(parents=True, exist_ok=True)
    slugs = objetivo(a.todos)
    if a.limit:
        slugs = slugs[:a.limit]
    print(f'· objetivo: {len(slugs)} fichas de Cámara')

    def cache_de(slug):
        return RAWDIR / f'{slug[:150]}.html'

    pendientes = [] if a.offline else [
        s for s in slugs if a.force or not cache_de(s).exists()]
    n_ok = n_fail = 0
    if pendientes:
        print(f'· bajando {len(pendientes)} (caché: {len(slugs) - len(pendientes)})')

        def _bajar(slug):
            html = curl(f'{BASE}/{slug}/')
            if not html:
                return slug, False
            frag = recortar(html)
            if not frag:
                return slug, False
            cache_de(slug).write_text(frag, encoding='utf-8')
            time.sleep(0.15)
            return slug, True

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(_bajar, s): s for s in pendientes}
            hechos = 0
            for fut in as_completed(futs):
                try:
                    _, ok = fut.result()
                except Exception:
                    ok = False
                hechos += 1
                n_ok += ok
                n_fail += (not ok)
                if hechos % 200 == 0:
                    print(f'  …{hechos}/{len(pendientes)} · ok={n_ok} fallo={n_fail}')
        print(f'· descarga: {n_ok} ok · {n_fail} sin respuesta '
              f'(re-correr el script las reintenta)')

    fichas, sin_cache = [], 0
    for s in slugs:
        p = cache_de(s)
        if not p.exists():
            sin_cache += 1
            continue
        try:
            fichas.append(parse_ficha(p.read_text(encoding='utf-8'), s))
        except Exception as e:                      # una ficha rota no tumba la corrida
            print(f'  ! parse {s}: {e}')

    with open(DEST, 'w', encoding='utf-8') as f:
        for r in fichas:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    con_fecha = sum(1 for r in fichas if r['fecha_radicacion_camara'])
    con_com = sum(1 for r in fichas if r['comision'])
    con_gac = sum(1 for r in fichas if r['gaceta_radicacion'])
    con_deep = sum(1 for r in fichas if r['gaceta_radicacion_deep'])
    con_deb = sum(1 for r in fichas if r['debates'])
    print(f'\nfichas.jsonl : {len(fichas)} parseadas · {sin_cache} sin caché')
    print(f'  fecha de radicación : {con_fecha} ({100*con_fecha/max(len(fichas),1):.1f}%)')
    print(f'  comisión            : {con_com}')
    print(f'  gaceta radicación   : {con_gac} ({con_deep} con deep-link ent+fec+num)')
    print(f'  con debates         : {con_deb}')
    print(f'  → {DEST.relative_to(REPO)}')


if __name__ == '__main__':
    main()
