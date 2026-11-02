#!/usr/bin/env python3
"""Rastreo diario de la Ley de Rescate Económico (PL 477 de 2026 Cámara).

  python3 tools/ley-rescate/rastreo.py                     # trámite + prensa + clasifica + calcula
  python3 tools/ley-rescate/rastreo.py --dias 6            # ventana de prensa (primera corrida)
  python3 tools/ley-rescate/rastreo.py --exportar p.json   # deja los textos sin clasificar y sale
  python3 tools/ley-rescate/rastreo.py --importar c.json   # mete una clasificación hecha aparte
  python3 tools/ley-rescate/rastreo.py --solo-calcular     # recalcula sin ir a la red
  python3 tools/ley-rescate/rastreo.py --publicar          # + copia estado.json a ley-rescate-data/ (lo sirve GitHub Pages)

Las llaves SOLO se leen del entorno: DEEPSEEK_API_KEY. Sin ella no hay postura nueva: el tema se
asigna por palabras y la postura queda vacía, porque el diccionario no sabe leer postura. La capa
de redes la trae redes.mjs a redes-crudo.json; aquí se mezcla y se clasifica.

Doc completa: tools/ley-rescate/LEEME.md
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import email.utils
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
DATOS = Path(os.environ.get('LR_DATOS') or REPO / 'Bases de datos' / 'ley-rescate')
sys.path.insert(0, str(REPO / 'tools' / 'batalla'))
sys.path.insert(0, str(REPO / 'tools' / 'leyes-senado'))
import batalla as bt                       # noqa: E402  norm · tier · internacional
import harvest_camara_fichas as hf         # noqa: E402  parser de la ficha de la Cámara

COL = dt.timezone(dt.timedelta(hours=-5))
UA = hf.UA
FICHA = 'https://www.camara.gov.co/ley-rescate-economico'
ORDENES = ('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/'
           'legislativo/ordenes-vigentes.json')
PUBLICO = REPO / 'ley-rescate-data' / 'estado.json'
MODELO = os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-flash')
FUENTES = ['prensa', 'x', 'tiktok', 'instagram', 'facebook']
POSTURAS = {'a': 'apoya', 'r': 'rechaza', 'm': 'mixta', 'i': 'informa'}
CLAS_VERSION = 'v1'

CONSULTAS = [
    '"Ley de Rescate"', '"Ley de Rescate Económico"', '"rescate fiscal"', '"rescate económico" Congreso',
    '"ley de rescate" ponentes', '"ley de rescate" ponencia', '"ley de rescate" "mensaje de urgencia"',
    '"ley de rescate" comisión tercera', '"ley de rescate" comisiones económicas', '"ley de rescate" votos bancada',
    '"ley de rescate" Centro Democrático', '"ley de rescate" Partido Liberal', '"ley de rescate" conservadores',
    '"ley de rescate" La U', '"ley de rescate" Cambio Radical', '"ley de rescate" Pacto Histórico', '"ley de rescate" Alianza Verde',
    '"ley de rescate" ANDI', '"ley de rescate" Fenalco', '"ley de rescate" Fedesarrollo', '"ley de rescate" Asobancaria',
    '"ley de rescate" SAC agricultores', '"ley de rescate" Acopi', '"ley de rescate" Camacol', '"ley de rescate" ACP petróleo',
    '"ley de rescate" CUT paro', '"ley de rescate" Fecode', '"ley de rescate" sindicatos', '"ley de rescate" CARF',
    '"ley de rescate" IVA alimentos', '"ley de rescate" café', '"ley de rescate" medicina prepagada',
    '"ley de rescate" celulares computadores', '"ley de rescate" internet IVA', '"ley de rescate" EfectIVA',
    '"ley de rescate" salud cotización', '"ley de rescate" clase media', '"ley de rescate" renta personas',
    '"ley de rescate" empresas renta', '"ley de rescate" parafiscales', '"ley de rescate" amnistía normalización',
    '"ley de rescate" criptomonedas', '"ley de rescate" RUGE', '"ley de rescate" patrimonio',
    '"ley de rescate" facultades extraordinarias', '"ley de rescate" contratistas', '"ley de rescate" ministerios',
    '"ley de rescate" licores cerveza', '"ley de rescate" cigarrillos', '"ley de rescate" gasolina',
    '"ley de rescate" apuestas', '"ley de rescate" regiones gobernadores', '"ley de rescate" venta activos',
    '"ley de rescate" regla fiscal', '"ley de rescate" contrabando',
]
ES_LEY = re.compile(r'(ley|proyecto|plan)( de)? (de )?rescate|rescate (economico|fiscal)|pl 477|proyecto 477', re.I)


def ahora():
    return dt.datetime.now(dt.timezone.utc)


def leer(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text())
    except (OSError, json.JSONDecodeError):
        return defecto


def escribir(ruta, datos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    t = Path(str(ruta) + '.tmp')
    t.write_text(json.dumps(datos, ensure_ascii=False))
    t.replace(ruta)


def get(url, tiempo=45):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=tiempo) as r:
        return r.read()


# ─────────────────────────────────────────────────────────── trámite

def tramite(previo):
    """La ficha oficial manda. Si la Cámara no responde se conserva lo anterior y se dice."""
    t = dict(previo or {})
    t['ficha_ok'] = False
    try:
        html = get(FICHA, 60).decode('utf-8', 'ignore')
        f = hf.parse_ficha(hf.recortar(html), 'ley-rescate-economico')
        t['ficha_ok'] = bool(f.get('nro_camara'))
    except Exception as e:                                    # noqa: BLE001
        f = None
        t['ficha_error'] = str(e)[:160]
    if f and f.get('nro_camara'):
        nuevo = {'estado': f.get('estado_ficha'), 'comision': f.get('comision') or None,
                 'nro_senado': f.get('nro_senado'), 'debates': f.get('debates') or []}
        if {k: t.get(k) for k in nuevo} != nuevo and t.get('estado'):
            t.setdefault('cambios', []).append({'fecha': ahora().astimezone(COL).date().isoformat(),
                                                'antes': t.get('estado'), 'ahora': nuevo['estado']})
        t.update(nuevo)
        t['ficha_leida'] = ahora().isoformat(timespec='minutes')
    try:
        o = json.loads(get(ORDENES))
    except Exception as e:                                    # noqa: BLE001
        o = None
        t['ordenes_error'] = str(e)[:160]
    if o:
        hits, no_leidas = [], []
        for s in o.get('ordenes', []):
            cuerpo = json.dumps(s.get('proyectos', []), ensure_ascii=False)
            amb = s.get('ambito', '')
            if re.search(r'\b477\b|[Rr]escate', cuerpo + ' ' + s.get('titulo', '')):
                hits.append({k: s.get(k) for k in ('fecha', 'corporacion', 'ambito', 'titulo', 'url')})
            elif s.get('pdf_error') and ('Tercera' in amb or 'Plenaria' in amb):
                no_leidas.append({k: s.get(k) for k in ('fecha', 'corporacion', 'ambito', 'url')})
        t['agenda'] = sorted(hits, key=lambda x: x['fecha'] or '')
        t['agenda_no_leida'] = no_leidas
        t['ordenes_v'] = o.get('v')
        t['ordenes_hasta'] = o.get('hasta')
    return t


# ─────────────────────────────────────────────────────────── prensa

def google_news(q, dias):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        dict(q=f'{q} when:{dias}d', hl='es-419', gl='CO', ceid='CO:es'))
    root = ET.fromstring(get(url, 30))
    out = []
    for it in root.iter('item'):
        titulo = (it.findtext('title') or '').strip()
        if 'Ã' in titulo or 'â€' in titulo:
            try:
                titulo = titulo.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        src = it.find('source')
        medio = (src.text or '').strip() if src is not None else ''
        if medio and titulo.endswith(' - ' + medio):
            titulo = titulo[: -len(' - ' + medio)].strip()
        try:
            pub = email.utils.parsedate_to_datetime(it.findtext('pubDate')).astimezone(dt.timezone.utc)
        except Exception:                                     # noqa: BLE001
            continue
        out.append({'titulo': titulo, 'medio': medio or '¿?', 'url': it.findtext('link') or '',
                    'dom': (src.get('url') or '') if src is not None else '', 'pub': pub.isoformat(timespec='seconds')})
    return out


def prensa(corpus, dias):
    def una(q):
        try:
            return google_news(q, dias)
        except Exception as e:                                # noqa: BLE001
            print('  ! consulta falló:', q, str(e)[:80])
            return []
    nuevos = 0
    with ThreadPoolExecutor(6) as ex:
        for lista in ex.map(una, CONSULTAS):
            for it in lista:
                if it['pub'] < '2026-10-20' or bt.internacional(it):
                    continue
                k = 'p' + hashlib.sha1((bt.norm(it['titulo']) + '|' + bt.norm(it['medio'])).encode()).hexdigest()[:14]
                if k in corpus:
                    continue
                peso, nivel = bt.tier(it['medio'])
                corpus[k] = {'f': 'prensa', 'txt': it['titulo'], 'medio': it['medio'], 'url': it['url'], 'pub': it['pub'],
                             'peso': peso, 'nivel': nivel}
                nuevos += 1
    return nuevos


def mezclar_redes(corpus):
    crudo = leer(DATOS / 'redes-crudo.json', None)
    if not crudo:
        return 0, None
    nuevos = 0
    for it in crudo.get('items', []):
        txt = (it.get('texto') or '').strip()
        if len(txt) < 8:
            continue
        k = 'r' + hashlib.sha1((it.get('red', '') + '|' + (it.get('url') or '') + '|' + txt[:80]).encode()).hexdigest()[:14]
        if k in corpus:
            corpus[k]['inter'] = max(corpus[k].get('inter', 0), it.get('inter') or 0)
            continue
        corpus[k] = {'f': it.get('red'), 'tipo': it.get('tipo'), 'txt': txt, 'autor': it.get('autor') or '',
                     'seg': it.get('seguidores') or 0, 'ver': bool(it.get('verificado')), 'url': it.get('url') or '',
                     'pub': normaliza_fecha(it.get('fecha')) or crudo.get('generado'), 'inter': it.get('inter') or 0}
        nuevos += 1
    return nuevos, crudo


def normaliza_fecha(v):
    if not v:
        return None
    if isinstance(v, (int, float)):
        v = v / 1000 if v > 1e12 else v
        return dt.datetime.fromtimestamp(v, dt.timezone.utc).isoformat(timespec='seconds')
    s = str(v)
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(dt.timezone.utc).isoformat(timespec='seconds')
    except ValueError:
        try:
            return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc).isoformat(timespec='seconds')
        except (TypeError, ValueError):
            return None


# ─────────────────────────────────────────────────────────── clasificación

def instrucciones(temas):
    lista = '\n'.join(f"- {t['id']}: {t['nombre']}. {t['nota']}" for t in temas)
    return f"""Eres analista legislativo en Colombia. Recibes textos sobre la Ley de Rescate Económico (PL 477 de 2026 Cámara), que radicó el gobierno De la Espriella el 29-oct-2026: recorte del Estado, reforma tributaria y facultades al presidente.

Para CADA línea «índice<TAB>texto» devuelve un objeto con:
- i: el índice.
- rel: 1 si el texto habla de ESTA ley; 0 si no.
- t: lista de hasta 3 pares [tema, postura]. Tema es uno de:
{lista}
- general: la ley en conjunto, su trámite, el default, las negociaciones, sin una medida concreta.
  Postura: «a» apoya la medida · «r» la rechaza o la critica · «m» la acepta con reparos o pide cambiarla · «i» informa sin tomar partido.
- v: quién habla: gobierno · oposicion · congreso · gremio · experto · sindicato · medio · ciudadano.

Reglas:
- La postura es frente a la MEDIDA, no frente al Gobierno. Un uribista que rechaza el IVA a la comida es «r» en iva_alimentos.
- Un titular que solo cuenta qué dice la norma es «i», aunque la noticia sea mala. «La medicina prepagada podría subir» es «i».
- Si el titular cita a alguien que apoya o rechaza, la postura es la de esa persona: «No acompañaré estas medidas: Norma Hurtado» es «r».
- El sarcasmo existe. Ante la duda, «i». Nunca inventes un tema que el texto no toque.
Responde SOLO un arreglo JSON, sin texto alrededor."""


def deepseek(system, user, llave, max_tokens=16000):
    cuerpo = json.dumps({'model': MODELO, 'temperature': 0, 'max_tokens': max_tokens,
                         'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}).encode()
    req = urllib.request.Request('https://api.deepseek.com/chat/completions', data=cuerpo, headers={
        'content-type': 'application/json', 'authorization': f'Bearer {llave}'})
    with urllib.request.urlopen(req, timeout=170) as r:
        d = json.load(r)
    return (d['choices'][0]['message'].get('content') or '').strip()


def json_de(txt):
    txt = re.sub(r'^```(?:json)?|```$', '', txt.strip()).strip()
    return json.loads(txt)


def valida(fila, ids):
    rel = 1 if fila.get('rel') else 0
    t = []
    for par in (fila.get('t') or [])[:3]:
        if isinstance(par, (list, tuple)) and len(par) == 2 and par[0] in ids and par[1] in POSTURAS:
            t.append([par[0], par[1]])
    return {'rel': rel, 't': t, 'v': str(fila.get('v') or '')[:12]}


def clasificar(corpus, clas, temas, llave, lote=40):
    ids = {t['id'] for t in temas} | {'general'}
    faltan = [k for k in corpus if clas.get(k, {}).get('cv') != CLAS_VERSION]
    if not llave:
        for k in faltan:                                       # respaldo: tema por palabras, sin postura
            if k not in clas:
                n = bt.norm(corpus[k]['txt'])
                ts = [t['id'] for t in temas if any(bt.norm(c) in n for c in t['claves'])][:3]
                clas[k] = {'rel': 1 if ES_LEY.search(n) or ts else 0, 't': [[x, None] for x in (ts or ['general'])],
                           'v': '', 'm': 'palabras'}
        return 0
    sistema = instrucciones(temas)

    def uno(ks):
        linea = '\n'.join(f"{i}\t{corpus[k]['txt'][:300]}" for i, k in enumerate(ks))
        for _ in range(2):
            try:
                return ks, json_de(deepseek(sistema, linea, llave))
            except Exception as e:                            # noqa: BLE001
                err = e
        print('  ! lote falló:', str(err)[:120])
        return ks, []
    lotes = [faltan[i:i + lote] for i in range(0, len(faltan), lote)]
    with ThreadPoolExecutor(5) as ex:
        for ks, filas in ex.map(uno, lotes):
            for f in filas if isinstance(filas, list) else []:
                try:
                    k = ks[int(f.get('i'))]
                except (TypeError, ValueError, IndexError):
                    continue
                clas[k] = {**valida(f, ids), 'm': MODELO, 'cv': CLAS_VERSION}
    return len(faltan)


# ─────────────────────────────────────────────────────────── cálculo

def limpia_cita(txt):
    """Lo que se publica de una persona común: sin @, sin enlaces, sin teléfonos ni correos."""
    txt = re.sub(r'https?://\S+|www\.\S+', '', txt)
    txt = re.sub(r'\S+@\S+\.\S+', '', txt)
    txt = re.sub(r'@\w+', '@…', txt)
    txt = re.sub(r'\+?\d[\d\s\-]{6,}\d', '', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return ''.join(list(txt)[:220])


def calcular(corpus, clas, temas, tram, cfg, crudo):
    hoy = ahora().astimezone(COL).date()
    items = []
    for k, it in corpus.items():
        c = clas.get(k)
        if not c or not c.get('rel'):
            continue
        items.append((k, it, c))
    base = {f: Counter() for f in FUENTES}
    tablero = {t['id']: {f: Counter() for f in FUENTES} for t in temas}
    tablero['general'] = {f: Counter() for f in FUENTES}
    serie = {t: defaultdict(lambda: Counter()) for t in tablero}
    total_dia = defaultdict(Counter)
    voz = {t: Counter() for t in tablero}
    tit, cit = defaultdict(list), defaultdict(list)
    medios, autores = Counter(), Counter()
    for k, it, c in items:
        f = it['f']
        if f not in base:
            continue
        dia = (it.get('pub') or '')[:10]
        try:
            dia = dt.datetime.fromisoformat(it['pub']).astimezone(COL).date().isoformat()
        except (KeyError, TypeError, ValueError):
            pass
        base[f]['n'] += 1
        total_dia[dia][f] += 1
        if f == 'prensa':
            medios[it['medio']] += 1
        else:
            autores[it.get('autor') or k] += 1
        for tema, p in c['t'] or [['general', None]]:
            if tema not in tablero:
                continue
            b = tablero[tema][f]
            b['n'] += 1
            b[POSTURAS.get(p, 'sin')] += 1
            b['inter'] += it.get('inter') or 0
            if c.get('v'):
                voz[tema][c['v']] += 1
            serie[tema][dia][f] += 1
            if f == 'prensa':
                tit[tema].append({'t': it['txt'], 'm': it['medio'], 'u': it['url'], 'f': dia, 'p': p, 'w': it.get('peso', .4)})
            elif p in ('a', 'r', 'm'):
                pub = it.get('ver') or (it.get('seg') or 0) >= 50000
                cit[tema].append({'t': limpia_cita(it['txt']), 'r': f, 'p': p, 'i': it.get('inter') or 0, 'f': dia,
                                  'a': it.get('autor') if pub else None, 'u': it.get('url') if pub else None})
    salida = []
    fichas = temas + [{'id': 'general', 'nombre': 'La ley en conjunto', 'corto': 'Lo que se dice del proyecto sin hablar de una medida concreta: el trámite, el default, las negociaciones.', 'arts': [], 'pag': '', 'rige': ''}]
    for t in fichas:
        i = t['id']
        titulares = sorted(tit[i], key=lambda x: (x['f'], x['w']), reverse=True)
        visto, unicos = set(), []
        for x in titulares:
            n = bt.norm(x['t'])[:60]
            if n in visto:
                continue
            visto.add(n)
            unicos.append({k: x[k] for k in 'tmufp'})
        citas = []
        for p in 'rmar':
            for c in sorted([x for x in cit[i] if x['p'] == p and x not in citas], key=lambda x: -x['i'])[:2]:
                citas.append(c)
        salida.append({'id': i, 'nombre': t['nombre'], 'corto': t['corto'], 'arts': t['arts'], 'pag': t['pag'], 'rige': t['rige'],
                       'por': {f: dict(tablero[i][f]) for f in FUENTES if tablero[i][f]['n']},
                       'serie': {d: dict(v) for d, v in sorted(serie[i].items())},
                       'voz': dict(voz[i]), 'titulares': unicos[:14], 'citas': citas[:6]})
    sin_postura = sum(1 for _, _, c in items if any(p is None for _, p in c['t']))
    fuentes = {f: {'n': base[f]['n']} for f in FUENTES}
    fuentes['prensa']['medios'] = len(medios)
    fuentes['prensa']['top'] = medios.most_common(8)
    for f in FUENTES[1:]:
        fuentes[f]['posts'] = sum(1 for _, it, _ in items if it['f'] == f and it.get('tipo') == 'post')
        fuentes[f]['comentarios'] = sum(1 for _, it, _ in items if it['f'] == f and it.get('tipo') == 'comentario')
    return {
        'v': ahora().isoformat(timespec='minutes'), 'hoy': hoy.isoformat(),
        'proyecto': cfg['proyecto'], 'tramite': tram, 'hitos': cfg['hitos'], 'voces': cfg['voces'], 'votos': cfg['votos'],
        'temas': salida, 'articulos': cfg['articulos'], 'fuentes': fuentes,
        'serie_total': {d: dict(v) for d, v in sorted(total_dia.items())},
        'clasificacion': {'modelos': dict(Counter(c.get('m', '?') for _, _, c in items)), 'sin_postura': sin_postura,
                          'textos': len(corpus), 'pertinentes': len(items)},
        'redes': {'usd': crudo.get('usd'), 'generado': crudo.get('generado'), 'informe': crudo.get('informe')} if crudo else None,
        'lectura': leer(DATOS / 'lectura.json', None),
    }


def lectura_llm(estado, llave):
    resumen = [{'tema': t['nombre'], 'n': {f: v['n'] for f, v in t['por'].items()},
                'posturas': {f: {k: v.get(k, 0) for k in ('apoya', 'rechaza', 'mixta', 'informa')} for f, v in t['por'].items()},
                'titulares': [x['t'] for x in t['titulares'][:4]]} for t in estado['temas']]
    system = ('Eres analista legislativo. Escribe en español de Colombia, sin adjetivos de relleno. Reglas: usa solo lo que está en el '
              'resumen; di «lo clasificado como» y nunca «la opinión pública»; una cifra de redes no representa al país; no predigas el voto. '
              'Devuelve JSON {"titular": una frase de máximo 14 palabras, "lectura": [tres frases cortas], '
              '"senales": [{"tipo": "ponentes|urgencia|audiencia|cambio_texto|votacion|protesta|gremio", "texto": frase, "titular_cita": título EXACTO del resumen}]}. '
              'Una señal solo si un titular la dice literalmente.')
    try:
        j = json_de(deepseek(system, json.dumps({'tramite': estado['tramite'].get('estado'), 'temas': resumen}, ensure_ascii=False), llave, 24000))
    except Exception as e:                                    # noqa: BLE001
        print('  ! lectura falló:', str(e)[:120])
        return None
    todos = {x['t'] for t in estado['temas'] for x in t['titulares']}
    j['senales'] = [s for s in j.get('senales', []) if s.get('titular_cita') in todos]
    j['modelo'], j['fecha'] = MODELO, estado['hoy']
    return j


def publicar(ruta):
    """estado.json va al repo: lo sirve GitHub Pages y no tiene datos de personas (ver limpia_cita)."""
    PUBLICO.parent.mkdir(parents=True, exist_ok=True)
    PUBLICO.write_bytes(Path(ruta).read_bytes())
    print('Publicado en', PUBLICO.relative_to(REPO))


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--dias', type=int, default=3)
    a.add_argument('--exportar')
    a.add_argument('--importar')
    a.add_argument('--solo-calcular', action='store_true')
    a.add_argument('--sin-prensa', action='store_true')
    a.add_argument('--publicar', action='store_true')
    o = a.parse_args()
    cod = leer(AQUI / 'temas.json', {})
    temas = cod['temas']
    corpus = leer(DATOS / 'corpus.json', {})
    clas = leer(DATOS / 'clasif.json', {})
    tram = leer(DATOS / 'tramite.json', {})
    crudo = None
    if not o.solo_calcular:
        tram = tramite(tram)
        escribir(DATOS / 'tramite.json', tram)
        print('Trámite:', tram.get('estado'), '· comisión:', tram.get('comision'), '· agenda:', len(tram.get('agenda', [])), '· ficha ok:', tram.get('ficha_ok'))
        if not o.sin_prensa:
            print('Prensa nueva:', prensa(corpus, o.dias))
    n, crudo = mezclar_redes(corpus)
    print('Redes nuevas:', n)
    if o.importar:
        ids = {t['id'] for t in temas} | {'general'}
        d = leer(o.importar, {})
        for k, f in d.items():
            if k in corpus:
                clas[k] = {**valida(f, ids), 'm': 'lectura-asistida', 'cv': CLAS_VERSION}
        print('Importadas:', len(d))
    if o.exportar:
        faltan = {k: corpus[k]['txt'] for k in corpus if clas.get(k, {}).get('cv') != CLAS_VERSION}
        escribir(o.exportar, faltan)
        escribir(DATOS / 'corpus.json', corpus)
        print('Sin clasificar:', len(faltan), '→', o.exportar)
        return
    llave = os.environ.get('DEEPSEEK_API_KEY')
    print('Clasificados con modelo:', clasificar(corpus, clas, temas, llave))
    escribir(DATOS / 'corpus.json', corpus)
    escribir(DATOS / 'clasif.json', clas)
    cfg = {'proyecto': leer(AQUI / 'proyecto.json', {}), 'hitos': leer(AQUI / 'hitos.json', []), 'voces': leer(AQUI / 'voces.json', []),
           'votos': leer(AQUI / 'votos.json', {}), 'articulos': leer(AQUI / 'articulos.json', [])}
    estado = calcular(corpus, clas, temas, tram, cfg, crudo)
    if llave and not o.solo_calcular:
        lect = lectura_llm(estado, llave)
        if lect:
            escribir(DATOS / 'lectura.json', lect)
            estado['lectura'] = lect
    ruta = DATOS / 'estado.json'
    escribir(ruta, estado)
    print(f"estado.json · {ruta.stat().st_size // 1024} KB · pertinentes {estado['clasificacion']['pertinentes']} de {len(corpus)}")
    if o.publicar:
        publicar(ruta)


if __name__ == '__main__':
    main()
