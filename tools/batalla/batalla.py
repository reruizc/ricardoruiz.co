#!/usr/bin/env python3
"""Anatomía de una batalla mediática · recolector y motor.

Una «batalla» es la disputa entre bandos por el enmarcado de un hecho con fecha
y hora conocidas (una marcha, una votación, un decreto). Este script recoge la
cobertura, la clasifica con diccionarios declarados en `batallas/<id>.json` y
calcula lo que se dibuja en `batalla.html`:

  · FASES       preparación → despliegue → choque → quiebre → desenlace → secuelas
  · MARCADOR    correlación de fuerzas por la ley cuadrática de Lanchester:
                fuerza = N² × q  (N = medios distintos que llevan el marco del
                bando · q = peso medio de esos medios). Duplicar los medios vale
                lo que cuadruplicar la calidad.
  · FRENTES     cada marco como un batallón: medios, primer disparo, velocidad.
  · INICIATIVA  cuánto tarda cada bando en enmarcar el primer choque.
  · COLISIÓN    titulares donde chocan los dos marcos vs conversaciones paralelas.
  · NODOS       quién dispara primero y quién amplifica.
  · TERRENO     ciudades nombradas en la cobertura, con la tensión de cada una.
  · MIRADA EXTERNA  prensa en inglés y financiera + TRM.

  python3 tools/batalla/batalla.py marcha-14oct-2026            # recoge y calcula
  python3 tools/batalla/batalla.py marcha-14oct-2026 --subir    # + publica en S3
  python3 tools/batalla/batalla.py marcha-14oct-2026 --offline  # recalcula sin red

LÍMITES QUE LA PÁGINA DECLARA
- Lee TITULARES, no notas completas: un titular neutro que cita a un bando no
  se cuenta como marco de ese bando salvo que use sus palabras.
- Google News devuelve hasta 100 resultados por consulta y ordena por
  relevancia: el corpus se ACUMULA corrida a corrida, así que lo de antes del
  primer arranque puede estar incompleto.
- Sin X (Apify) no hay cuentas: los «nodos» son medios, no personas.
"""
import argparse
import datetime as dt
import email.utils
import gzip
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
DATOS = REPO / 'Bases de datos' / 'batalla'
S3 = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/batalla'
BOG = dt.timezone(dt.timedelta(hours=-5))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'

FASES = [
    ('preparacion', 'Preparación', 'Convocatoria, rutas, decreto: las fuerzas se alistan.'),
    ('despliegue', 'Despliegue', 'La gente llega a las plazas; se toman posiciones.'),
    ('choque', 'Choque', 'Contacto: disturbios, bloqueos, capturas, gases.'),
    ('quiebre', 'Punto de quiebre', 'Un hecho grave cambia la batalla: muertos, heridos graves, incendios.'),
    ('desenlace', 'Desenlace', 'Balances, cifras oficiales y repliegue.'),
    ('secuelas', 'Secuelas', 'Las ondas: demandas, debates, mercados, la siguiente batalla.'),
]

# Peso de cada medio (la q de Lanchester). Declarado y movible, no un ranking de
# calidad: mide alcance probable. Lo que no está en la lista entra con 0,4.
TIER1 = ['el tiempo', 'el espectador', 'semana', 'el colombiano', 'el pais', 'caracol', 'blu radio',
         'w radio', 'la fm', 'rcn', 'infobae', 'portafolio', 'valora analitik', 'la silla vacia', 'cambio',
         'ntn24', 'pulzo', 'publimetro', 'canal 1', 'cm&', 'el heraldo', 'el universal', 'vanguardia',
         'la republica', 'bloomberg', 'cnn', 'france 24', 'dw', 'bbc', 'el nuevo siglo', 'razon publica',
         'kienyke', 'las2orillas', 'citytv', 'canal capital', 'reuters', 'associated press', 'ap news',
         'afp', 'efe', 'financial times', 'wall street journal', 'new york times', 'guardian', 'el pais america']
TIER2 = ['la patria', 'el nuevo dia', 'la opinion', 'el informador', 'el meridiano', 'la nacion', 'diario del huila',
         'diario del sur', 'hoy diario', 'alerta', 'mioriente', 'minuto30', 'telemedellin', 'teleantioquia',
         'telepacifico', '90 minutos', 'qhubo', 'extra', 'zona cero', 'diario occidente', 'el pilon',
         'chicanoticias', 'caracol tv', 'telecaribe', 'canal tro', 'teleislas', 'la cronica', 'el olfato',
         'proclama', 'seguimiento', 'denuncias', 'vorágine', 'voragine', 'el frente', 'boyaca7dias',
         'cuestion publica', 'colombiano', 'diario', 'noticias']
OFICIAL = ['gov.co', 'alcaldia', 'gobernacion', 'presidencia', 'policia nacional', 'ministerio', 'concejo de',
           'defensoria', 'procuraduria', 'registraduria']


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9&\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def patron(terminos):
    """Regex de un grupo de términos. «x*» = raíz; «x» = palabra entera."""
    partes = []
    for t in terminos:
        raiz = t.endswith('*')
        t = norm(t.rstrip('*'))
        if not t:
            continue
        p = r'\s+'.join(re.escape(w) for w in t.split())
        partes.append(p + (r'\w*' if raiz else r'\b'))
    return re.compile(r'\b(?:' + '|'.join(partes) + ')') if partes else None


def tier(medio):
    m = norm(medio)
    if any(k in m for k in OFICIAL):
        return 0.8, 'oficial'
    if any(k in m for k in TIER1):
        return 1.0, 'nacional'
    if any(k in m for k in TIER2):
        return 0.6, 'regional'
    return 0.4, 'otro'


# ---------------------------------------------------------------- recolección

def google_news(q, lang='es'):
    if lang == 'en':
        base = dict(hl='en-US', gl='US', ceid='US:en')
    else:
        base = dict(hl='es-419', gl='CO', ceid='CO:es')
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode(dict(q=f'{q} when:3d', **base))
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    out = []
    for it in root.iter('item'):
        titulo = (it.findtext('title') or '').strip()
        if 'Ã' in titulo or 'â€' in titulo:          # UTF-8 leído como Latin-1 en la fuente (pasa con Aporrea)
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
        except Exception:                                       # noqa: BLE001
            continue
        out.append({'titulo': titulo, 'medio': medio or '¿?', 'url': it.findtext('link') or '',
                    'pub': pub.isoformat(timespec='seconds'), 'lang': lang})
    return out


def recoger(cfg, corpus, ext):
    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    nuevos, fallas = 0, []
    plan = [(q, 'es', corpus) for q in cfg['consultas']]
    plan += [(q, 'en', ext) for q in cfg.get('consultas_externas', [])]
    plan += [(q, 'es', ext) for q in cfg.get('consultas_externas_es', [])]
    for q, lang, destino in plan:
        try:
            items = google_news(q, lang)
        except Exception as e:                                  # noqa: BLE001
            fallas.append(f'{q}: {e}')
            continue
        for x in items:
            k = hashlib.md5((norm(x['titulo']) + '|' + norm(x['medio'])).encode()).hexdigest()[:16]
            if k not in destino:
                x['visto'] = ahora
                x['q'] = [q]
                destino[k] = x
                nuevos += 1
            elif q not in destino[k]['q']:
                destino[k]['q'].append(q)
        time.sleep(0.6)
    return nuevos, fallas


def trm():
    """TRM del Banco de la República vía datos.gov.co (sin llave)."""
    url = ('https://www.datos.gov.co/resource/32sa-8pi3.json?'
           + urllib.parse.urlencode({'$order': 'vigenciadesde DESC', '$limit': 30}))
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        return [{'f': x['vigenciadesde'][:10], 'v': round(float(x['valor']), 2)} for x in reversed(d)]
    except Exception as e:                                      # noqa: BLE001
        print('  · TRM no disponible:', e)
        return None


# ---------------------------------------------------------------- clasificación

CLAS_VERSION = 'v2'
CLAS_PROMPT = """Clasificas titulares de prensa sobre {hecho} ({fecha}). Es un análisis de enmarcado:
qué marco ACTIVA cada titular, no si es cierto.
Libro de códigos (multi-etiqueta; un titular puede activar varios o ninguno):
{codigos}
Para cada titular devuelve:
- rel: 1 si trata de la marcha/protesta de esa fecha, de sus convocantes o del decreto sobre la protesta; 0 si no.
- m: ids de marcos que el titular activa por sus palabras o por la cita que destaca. Un titular de servicio
  (rutas, horarios, cierres viales) va con "logistica". Si informa sin enmarcar, lista vacía.
- h: 0 nada · 1 concentración o avance pacífico · 2 choque (disturbios, bloqueos, capturas, heridos leves, gases)
  · 3 hecho grave (muerte, herido grave, incendio, disparo, atentado). SOLO si el titular REPORTA que ya ocurrió
  en la protesta: anuncios, advertencias, controles preventivos o videos de entrenamiento = 0.
- v: quién habla o es la fuente destacada del titular:
{voces}
  o "" si el titular no cita a nadie. Un actor mencionado como objeto de la noticia NO es la voz.
No inventes: si dudas, lista vacía, h=0 y v="".
Responde SOLO JSON: {{"r":[{{"i":0,"rel":1,"m":[],"h":0,"v":""}}]}} con un objeto por titular, en el mismo orden."""


def clasificar_llm(cfg, corpus, carpeta, key, lote=30, hilos=6):
    """Etiqueta con modelo los titulares que aún no tienen etiqueta. Caché por id."""
    from concurrent.futures import ThreadPoolExecutor
    f = carpeta / 'clasificacion.json'
    cache = json.loads(f.read_text()) if f.exists() else {}
    if cache.get('_v') != CLAS_VERSION:
        cache = {'_v': CLAS_VERSION}
    pend = [k for k in corpus if k not in cache]
    if not pend or not key:
        return cache, 0
    codigos = '\n'.join(f"- {m['id']} ({cfg['bandos'][m['bando']]['nombre']}): {m['nombre']}. {m['nota']}"
                        for m in cfg['marcos'])
    voces = '\n'.join(f'  "{k}" {v}' for k, v in cfg.get('voz', {}).items())
    sistema = CLAS_PROMPT.format(hecho=cfg['titulo'], fecha=cfg.get('fecha_hecho', ''), codigos=codigos, voces=voces)
    validos = {m['id'] for m in cfg['marcos']}

    def una(ks):
        lista = '\n'.join(f"{n}. {corpus[k]['titulo']} — {corpus[k]['medio']}" for n, k in enumerate(ks))
        body = {'model': 'deepseek-v4-flash', 'temperature': 0, 'response_format': {'type': 'json_object'},
                'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': lista}]}
        for techo in (9000, 18000):
            body['max_tokens'] = techo
            try:
                req = urllib.request.Request('https://api.deepseek.com/chat/completions', data=json.dumps(body).encode(),
                                             headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=180) as r:
                    txt = (json.load(r)['choices'][0]['message'].get('content') or '').strip()
                if not txt:
                    continue
                res = {}
                for x in json.loads(txt).get('r', []):
                    i = x.get('i')
                    if isinstance(i, int) and 0 <= i < len(ks):
                        res[ks[i]] = {'rel': int(bool(x.get('rel'))), 'm': [m for m in x.get('m', []) if m in validos],
                                      'h': max(0, min(3, int(x.get('h') or 0))),
                                      'v': x.get('v') if x.get('v') in ('G', 'O', 'T') else ''}
                return res
            except json.JSONDecodeError:
                continue                                        # JSON cortado: otra vez con más techo
            except Exception as e:                              # noqa: BLE001
                print('  · lote de clasificación falló:', str(e)[:120])
                return {}
        print('  · lote de clasificación sin JSON válido (queda para la próxima corrida)')
        return {}

    lotes = [pend[i:i + lote] for i in range(0, len(pend), lote)]
    with ThreadPoolExecutor(hilos) as ex:
        for res in ex.map(una, lotes):
            cache.update(res)
    f.write_text(json.dumps(cache, ensure_ascii=False))
    return cache, sum(1 for k in pend if k in cache)


class Clasificador:
    def __init__(self, cfg, ciudades, llm=None):
        self.llm = llm or {}
        self.ancla = patron(cfg.get('ancla', {}).get('terminos', []))
        self.marcos = [(m['id'], m['bando'], patron(m['terminos'])) for m in cfg['marcos']]
        self.hechos = {k: (h['nivel'], patron(h['terminos'])) for k, h in cfg['hechos'].items()}
        self.actores = [(a['id'], a['bando'], patron(a['terminos'])) for a in cfg['actores']]
        self.ciudades = [(c['id'], patron(c['claves'])) for c in ciudades]

    def __call__(self, k, it):
        t = norm(it['titulo'])
        dic = [mid for mid, _, rx in self.marcos if rx and rx.search(t)]
        lab = self.llm.get(k)
        rel = lab['rel'] if lab else int(bool(self.ancla and self.ancla.search(t)))
        marcos = (lab['m'] if lab else dic) if rel else []
        bandos = sorted({b for mid, b, _ in self.marcos if mid in marcos and b in 'GO'})
        nivel, flags = 0, []
        for k, (nv, rx) in self.hechos.items():
            if rx and rx.search(t):
                if nv:
                    nivel = max(nivel, nv)
                else:
                    flags.append(k)
        if lab:
            # Dos llaves: el modelo dice que hubo choque Y el titular trae una palabra de hecho.
            # Solo con el modelo, una nota sobre el decreto («reglas para el uso de la fuerza») salía como choque.
            nivel = min(lab['h'], nivel) if lab['h'] >= 2 else lab['h']
        if not rel:
            nivel, flags = 0, []
        actores = [aid for aid, _, rx in self.actores if rx and rx.search(t)]
        ciudades = [cid for cid, rx in self.ciudades if rx and rx.search(t)]
        q, clase = tier(it['medio'])
        it['c'] = {'rel': rel, 'm': marcos, 'v': (lab.get('v', '') if lab and rel else ''), 'dic': dic, 'src': 'modelo' if lab else 'diccionario',
                   'b': ''.join(bandos), 'h': nivel, 'f': flags, 'a': actores if rel else [],
                   'ci': ciudades if rel else [], 'q': q, 'tm': clase}
        return it


# ---------------------------------------------------------------- métricas

def ts(it):
    return dt.datetime.fromisoformat(it['pub'])


def bando_de(it):
    b = it['c']['b']
    return 'C' if b == 'GO' else (b or ('N' if it['c']['m'] else ''))


def lanchester(items, filtro):
    medios = {}
    for it in items:
        if filtro(it):
            medios[it['medio']] = it['c']['q']
    n = len(medios)
    q = statistics.mean(medios.values()) if medios else 0
    return {'N': n, 'q': round(q, 2), 'F': round(n * n * q, 1)}


def fase_en(items, t, inicio):
    """Fase a la hora t, mirando los 90 minutos anteriores."""
    if t < inicio - dt.timedelta(minutes=30):
        return 'preparacion'
    ven = [i for i in items if t - dt.timedelta(minutes=90) <= ts(i) <= t]
    medios3 = {i['medio'] for i in ven if i['c']['h'] >= 3}
    n = len(ven) or 1
    choque = sum(1 for i in ven if i['c']['h'] >= 2) / n
    cierre = sum(1 for i in ven if 'desenlace' in i['c']['f']) / n
    secuela = sum(1 for i in ven if 'secuela' in i['c']['f']) / n
    horas = (t - inicio).total_seconds() / 3600
    if horas >= 30 or (horas >= 14 and secuela >= .15):
        return 'secuelas'
    if len(medios3) >= 2:
        return 'quiebre'
    if horas >= 5 and (cierre >= .2 or horas >= 11):
        return 'desenlace'
    if choque >= .2 and len(ven) >= 3:
        return 'choque'
    return 'despliegue'


def calcular(cfg, corpus, ext, ciudades, trm_serie):
    ahora = dt.datetime.now(dt.timezone.utc)
    inicio = dt.datetime.fromisoformat(cfg['inicio']).astimezone(dt.timezone.utc)
    desde = dt.datetime.fromisoformat(cfg['desde']).astimezone(dt.timezone.utc)
    items = sorted((i for i in corpus.values() if desde <= ts(i) <= ahora + dt.timedelta(minutes=10)), key=ts)
    relevantes = [i for i in items if i['c']['rel']]
    marcos_cfg = {m['id']: m for m in cfg['marcos']}

    # --- fase actual e historia por hora desde el día anterior
    fase = fase_en(relevantes, ahora, inicio)
    hist = []
    t = (inicio - dt.timedelta(hours=26)).replace(minute=0, second=0)
    while t <= ahora:
        hist.append({'t': t.isoformat(timespec='minutes'), 'f': fase_en(relevantes, t, inicio)})
        t += dt.timedelta(hours=1)

    # --- marcador: Lanchester en las últimas 3 horas y en toda la batalla
    hace3 = ahora - dt.timedelta(hours=3)
    ult3 = [i for i in relevantes if ts(i) >= hace3]
    dia = [i for i in relevantes if ts(i) >= inicio - dt.timedelta(hours=12)]

    def marcador(xs):
        fg = lanchester(xs, lambda i: 'G' in i['c']['b'])
        fo = lanchester(xs, lambda i: 'O' in i['c']['b'])
        tot = fg['F'] + fo['F']
        return {'G': fg, 'O': fo, 'share_G': round(fg['F'] / tot, 3) if tot else None,
                'items_G': sum(1 for i in xs if 'G' in i['c']['b']),
                'items_O': sum(1 for i in xs if 'O' in i['c']['b'])}
    marc = {'ult3h': marcador(ult3), 'batalla': marcador(dia)}

    # --- momentum: marcador móvil de 3 h cada 30 min (la «posesión» del partido)
    serie = []
    t0 = (inicio - dt.timedelta(hours=24)).replace(minute=0, second=0)
    t = t0
    while t <= ahora:
        t1 = t + dt.timedelta(minutes=30)
        b = [i for i in items if t <= ts(i) < t1]
        win = [i for i in relevantes if t1 - dt.timedelta(hours=3) <= ts(i) < t1]
        m = marcador(win)
        serie.append({'t': t.isoformat(timespec='minutes'),
                      'G': sum(1 for i in b if bando_de(i) == 'G'), 'O': sum(1 for i in b if bando_de(i) == 'O'),
                      'C': sum(1 for i in b if bando_de(i) == 'C'), 'N': sum(1 for i in b if bando_de(i) in ('N', '')),
                      'h2': sum(1 for i in b if i['c']['h'] == 2), 'h3': sum(1 for i in b if i['c']['h'] >= 3),
                      'sG': m['share_G']})
        t = t1

    # --- frentes: cada marco como batallón
    frentes = []
    for mid, m in marcos_cfg.items():
        xs = [i for i in dia if mid in i['c']['m']]
        if not xs and m['bando'] == 'N':
            continue
        f = lanchester(xs, lambda i: True)
        vistos, curva = set(), []
        for i in xs:
            if i['medio'] not in vistos:
                vistos.add(i['medio'])
                curva.append([ts(i).isoformat(timespec='minutes'), len(vistos)])
        h1 = {i['medio'] for i in xs if ts(i) >= ahora - dt.timedelta(hours=1)}
        h2 = {i['medio'] for i in xs if ahora - dt.timedelta(hours=2) <= ts(i) < ahora - dt.timedelta(hours=1)}
        primero = xs[0] if xs else None
        frentes.append({
            'id': mid, 'bando': m['bando'], 'nombre': m['nombre'], 'nota': m['nota'], 'items': len(xs), **f,
            'primero': ({'t': primero['pub'], 'medio': primero['medio'], 'titulo': primero['titulo'], 'url': primero['url']}
                        if primero else None),
            'medios_1h': len(h1), 'medios_1h_antes': len(h2), 'curva': curva[-60:],
            'ejemplo': ({'titulo': xs[-1]['titulo'], 'medio': xs[-1]['medio'], 'url': xs[-1]['url'], 't': xs[-1]['pub']}
                        if xs else None)})
    frentes.sort(key=lambda f: (-{'G': 1, 'O': 1}.get(f['bando'], 0), -f['F']))

    # --- iniciativa: quién enmarca primero el primer choque del día
    dia_marcha = [i for i in relevantes if ts(i) >= inicio - dt.timedelta(hours=1)]
    choque = next((i for i in dia_marcha if i['c']['h'] >= 2), None)
    ofi = opo = None
    if choque:
        tc = ts(choque)
        G_ACT = {a['id'] for a in cfg['actores'] if a['bando'] == 'G'}
        O_ACT = {a['id'] for a in cfg['actores'] if a['bando'] == 'O'}
        ofi = next((i for i in dia_marcha if ts(i) >= tc and i['c']['v'] == 'G'), None)
        opo = next((i for i in dia_marcha if ts(i) >= tc and i['c']['v'] == 'O'), None)

    def ref(i, base=None):
        if not i:
            return None
        r = {'t': i['pub'], 'medio': i['medio'], 'titulo': i['titulo'], 'url': i['url']}
        if base:
            r['lag_min'] = round((ts(i) - ts(base)).total_seconds() / 60)
        return r
    primer = {}
    for b in 'GO':
        x = next((i for i in dia if b in i['c']['b']), None)
        primer[b] = ref(x)
    # cada choque reportado (el primero de cada ciudad) y cuánto tarda cada voz en hablar después
    choques, vistos_c = [], set()
    for i in dia_marcha:
        if i['c']['h'] < 2:
            continue
        lugar = (i['c']['ci'] or ['?'])[0]
        if lugar in vistos_c:
            continue
        vistos_c.add(lugar)
        tc = ts(i)
        rg = next((x for x in dia_marcha if ts(x) >= tc and x['c']['v'] == 'G'), None)
        ro = next((x for x in dia_marcha if ts(x) >= tc and x['c']['v'] == 'O'), None)
        choques.append({**ref(i), 'nivel': i['c']['h'],
                        'ciudad': next((c['nombre'] for c in ciudades if c['id'] == lugar), None),
                        'resp_G': ref(rg, i), 'resp_O': ref(ro, i)})
    iniciativa = {'primer_choque': ref(choque), 'oficial': ref(ofi, choque), 'oposicion': ref(opo, choque),
                  'primer_marco': primer, 'choques': choques[:12]}

    # la voz de cada bando: dónde surge, quién la repite y a qué ritmo
    voces = {}
    for v in 'GOT':
        xs = [i for i in dia if i['c'].get('v') == v]
        cnt = Counter(i['medio'] for i in xs)
        vistos, curva = set(), []
        for i in xs:
            if i['medio'] not in vistos:
                vistos.add(i['medio'])
                curva.append([ts(i).isoformat(timespec='minutes'), len(vistos)])
        voces[v] = {'items': len(xs), 'medios': len(cnt), 'primero': ref(xs[0]) if xs else None,
                    'repetidores': [{'medio': m, 'n': n} for m, n in cnt.most_common(10)],
                    'ult': ref(xs[-1]) if xs else None, 'curva': curva[-80:],
                    'marcos': Counter(m for i in xs for m in i['c']['m']).most_common(5)}

    # --- colisión y conversaciones paralelas
    con_marco = [i for i in dia if i['c']['b']]
    nC = sum(1 for i in con_marco if i['c']['b'] == 'GO')
    nG = sum(1 for i in con_marco if i['c']['b'] == 'G')
    nO = sum(1 for i in con_marco if i['c']['b'] == 'O')
    por_medio = defaultdict(lambda: Counter())
    for i in dia:
        por_medio[i['medio']][bando_de(i) or 'x'] += 1
        por_medio[i['medio']]['tot'] += 1
    medios = []
    for md, c in por_medio.items():
        g, o = c['G'] + c['C'], c['O'] + c['C']
        medios.append({'medio': md, 'tot': c['tot'], 'G': c['G'], 'O': c['O'], 'C': c['C'],
                       'alin': round((o - g) / (o + g), 2) if (o + g) else None, 'q': tier(md)[0], 'tm': tier(md)[1]})
    medios.sort(key=lambda m: -m['tot'])
    eco = [m for m in medios if m['tot'] >= 3 and (m['G'] + m['O'] + m['C']) >= 2 and (m['G'] == 0 or m['O'] == 0) and m['C'] == 0]
    cruce = [m for m in medios if (m['G'] and m['O']) or m['C']]
    ejemplos_choque = [ref(i) for i in con_marco if i['c']['b'] == 'GO'][-6:]
    colision = {'indice': round(nC / (nC + nG + nO), 3) if (nC + nG + nO) else None, 'C': nC, 'G': nG, 'O': nO,
                'medios_cruce': len(cruce), 'medios_eco': len(eco),
                'eco': [m['medio'] for m in sorted(eco, key=lambda m: -m['tot'])[:10]],
                'ejemplos': list(reversed(ejemplos_choque))}

    # --- matices dentro de cada bando
    matices = {}
    for b in 'GO':
        cnt = Counter()
        for i in dia:
            for mid in i['c']['m']:
                if marcos_cfg[mid]['bando'] == b:
                    cnt[mid] += 1
        tot = sum(cnt.values()) or 1
        matices[b] = [{'id': k, 'nombre': marcos_cfg[k]['nombre'], 'n': v, 'p': round(v / tot, 3)}
                      for k, v in cnt.most_common()]

    # --- nodos: quién dispara primero y quién amplifica
    primeros = []
    for f in frentes:
        if f['bando'] not in 'GO':
            continue
        xs = [i for i in dia if f['id'] in i['c']['m']]
        vistos = []
        for i in xs:
            if i['medio'] not in [v['medio'] for v in vistos]:
                vistos.append({'medio': i['medio'], 't': i['pub']})
            if len(vistos) == 3:
                break
        primeros.append({'marco': f['id'], 'nombre': f['nombre'], 'bando': f['bando'], 'medios': vistos})
    nodos = {'primeros': primeros, 'amplificadores': [m for m in medios if m['tot'] >= 2][:16]}

    # --- terreno: ciudades
    cmap = {c['id']: c for c in ciudades}
    porc = defaultdict(list)
    for i in dia:
        for cid in i['c']['ci']:
            porc[cid].append(i)
    terreno = []
    for cid, xs in porc.items():
        c = cmap[cid]
        g = sum(1 for i in xs if 'G' in i['c']['b'])
        o = sum(1 for i in xs if 'O' in i['c']['b'])
        ult = xs[-1]
        terreno.append({'id': cid, 'nombre': c['nombre'], 'depto': c['depto'], 'lat': c['lat'], 'lon': c['lon'],
                        'items': len(xs), 'nivel': max(i['c']['h'] for i in xs),
                        'n2': sum(1 for i in xs if i['c']['h'] == 2), 'n3': sum(1 for i in xs if i['c']['h'] >= 3),
                        'G': g, 'O': o, 'ultimo': ref(ult)})
    terreno.sort(key=lambda c: -c['items'])

    # --- actores
    act = []
    for a in cfg['actores']:
        xs = [i for i in dia if a['id'] in i['c']['a']]
        if xs:
            act.append({'id': a['id'], 'nombre': a['nombre'], 'bando': a['bando'], 'n': len(xs),
                        'n3h': sum(1 for i in xs if ts(i) >= hace3), 'ultimo': ref(xs[-1])})
    act.sort(key=lambda a: -a['n'])

    # --- mirada externa
    RIESGO = patron(['unrest', 'protest*', 'clash*', 'violen*', 'turmoil', 'instabil*', 'risk*', 'polariz*',
                     'strike*', 'tension*', 'crackdown', 'authoritarian*', 'obstacle*', 'protestas', 'riesgo*',
                     'obstaculo*', 'incertidumbre', 'tension'])
    CONF = patron(['reform*', 'rally', 'gains', 'investor confidence', 'upgrade*', 'market friendly', 'pro market',
                   'austerity', 'bonds rise', 'peso strengthens', 'optimis*', 'reformas', 'confianza', 'apetito'])
    exts = sorted((x for x in ext.values() if ts(x) >= desde), key=ts)
    for x in exts:
        t_ = norm(x['titulo'])
        x['tono'] = 'riesgo' if RIESGO.search(t_) else ('confianza' if CONF.search(t_) else '')
    externa = {'items': len(exts), 'riesgo': sum(1 for x in exts if x['tono'] == 'riesgo'),
               'confianza': sum(1 for x in exts if x['tono'] == 'confianza'),
               'titulares': [{'t': x['pub'], 'medio': x['medio'], 'titulo': x['titulo'], 'url': x['url'],
                              'lang': x['lang'], 'tono': x['tono']} for x in reversed(exts[-24:])],
               'trm': trm_serie}

    feed = [{'t': i['pub'], 'medio': i['medio'], 'titulo': i['titulo'], 'url': i['url'], 'b': bando_de(i),
             'm': i['c']['m'], 'h': i['c']['h'], 'v': i['c'].get('v', ''), 's': i['c']['src'][0], 'ci': [cmap[c]['nombre'] for c in i['c']['ci']]}
            for i in reversed(relevantes[-120:])]

    return {
        'v': 1, 'id': cfg['id'], 'titulo': cfg['titulo'], 'subtitulo': cfg['subtitulo'], 'guerra': cfg.get('guerra'),
        'contexto': cfg.get('contexto', []), 'inicio': cfg['inicio'],
        'generado': ahora.isoformat(timespec='seconds'),
        'bandos': cfg['bandos'], 'fases': [{'id': a, 'nombre': b, 'nota': c} for a, b, c in FASES],
        'fase': fase, 'fase_hist': hist, 'marcador': marc, 'serie': serie, 'frentes': frentes,
        'matices': matices, 'iniciativa': iniciativa, 'voces': voces, 'colision': colision, 'nodos': nodos,
        'terreno': terreno, 'actores': act, 'externa': externa, 'feed': feed,
        'corpus': {'titulares': len(items), 'relevantes': len(relevantes), 'medios': len({i['medio'] for i in items}),
                   'desde': items[0]['pub'] if items else None},
        'x': None, 'lectura': None,
        'metodo': {'lanchester': 'fuerza = N² × q · N = medios distintos que llevan un marco del bando en la ventana · '
                                 'q = peso medio de esos medios (nacional 1 · oficial 0,8 · regional 0,6 · otro 0,4)',
                   'regla_terminos': cfg.get('regla_terminos'),
                   'marcos': [{'id': m['id'], 'bando': m['bando'], 'nombre': m['nombre'], 'terminos': m['terminos']}
                              for m in cfg['marcos']]},
    }


# ---------------------------------------------------------------- lectura automática

def deepseek_key():
    k = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if k:
        return k
    try:
        r = subprocess.run(['aws', 'lambda', 'get-function-configuration', '--function-name', 'caudal-analiza',
                            '--query', 'Environment.Variables.DEEPSEEK_API_KEY', '--output', 'text'],
                           capture_output=True, text=True, timeout=30)
        k = (r.stdout or '').strip()
        return '' if k in ('', 'None') else k
    except Exception:                                           # noqa: BLE001
        return ''


LECTURA_VERSION = 'v3'
LECTURA_PROMPT = """Eres un analista de medios neutral. Recibes las métricas de una «batalla de enmarcado»
entre dos bandos (Gobierno y Oposición) alrededor de un hecho político colombiano, y los titulares más recientes.
Escribe la lectura del momento en ESPAÑOL, tuteo neutro, como el relato de un partido, en 3 o 4 frases
(máximo 95 palabras). Reglas duras:
1. Usa SOLO las cifras y titulares que te paso. No inventes hechos, cifras ni citas.
2. No atribuyas intenciones ni especules sobre lo que un actor «busca» o «prepara».
3. No tomes partido ni califiques a los bandos; describe qué marco gana terreno y dónde.
4. Si los datos son pocos, dilo.
5. Nada de jerga técnica: no escribas «share», «items», «F» ni decimales como 0,009; di «titulares», «medios»,
   «fuerza» y porcentajes redondos. Un hecho de choque es un disturbio o enfrentamiento reportado, no un anuncio.
Devuelve JSON: {"lectura": "...", "titular": "frase de máximo 12 palabras para el marcador"}"""


def lectura(out, carpeta):
    cache = carpeta / 'lectura.json'
    prev = json.loads(cache.read_text()) if cache.exists() else None
    if prev and prev.get('v') == LECTURA_VERSION and \
            (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(prev['generado'])).total_seconds() < 25 * 60:
        return prev
    key = deepseek_key()
    if not key:
        return prev
    m = out['marcador']

    def local(x):
        # el modelo repite las horas que recibe: se le pasan en hora de Colombia, no en UTC
        if isinstance(x, dict):
            return {k: (dt.datetime.fromisoformat(v).astimezone(BOG).strftime('%d-%b %I:%M %p')
                        if k == 't' and isinstance(v, str) else local(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [local(v) for v in x]
        return x
    resumen = {
        'hecho': out['titulo'], 'fase_actual': out['fase'],
        'marcador_ult3h': {'gobierno_fuerza': m['ult3h']['G'], 'oposicion_fuerza': m['ult3h']['O'],
                           'share_gobierno': m['ult3h']['share_G']},
        'frentes': [{k: f[k] for k in ('nombre', 'bando', 'N', 'items', 'medios_1h')} for f in out['frentes'][:8]],
        'colision': {k: out['colision'][k] for k in ('indice', 'C', 'G', 'O')},
        'iniciativa': local(out['iniciativa']),
        'hora_actual_colombia': dt.datetime.now(BOG).strftime('%d-%b %I:%M %p'),
        'ciudades': [{k: c[k] for k in ('nombre', 'items', 'nivel')} for c in out['terreno'][:6]],
        'titulares': [f"{x['medio']}: {x['titulo']}" for x in out['feed'][:25]],
    }
    body = {'model': 'deepseek-v4-flash', 'temperature': 0.3, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': LECTURA_PROMPT},
                         {'role': 'user', 'content': json.dumps(resumen, ensure_ascii=False)}]}
    for techo in (6000, 14000):
        body['max_tokens'] = techo
        try:
            req = urllib.request.Request('https://api.deepseek.com/chat/completions',
                                         data=json.dumps(body).encode(),
                                         headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            txt = (d['choices'][0]['message'].get('content') or '').strip()
            if not txt:
                continue
            j = json.loads(txt)
            res = {'texto': j.get('lectura', '').strip(), 'titular': j.get('titular', '').strip(),
                   'generado': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                   'modelo': 'deepseek-v4-flash', 'v': LECTURA_VERSION}
            if res['texto']:
                cache.write_text(json.dumps(res, ensure_ascii=False))
                return res
        except Exception as e:                                  # noqa: BLE001
            print('  · lectura falló:', e)
            break
    return prev


# ---------------------------------------------------------------- main

def subir(ruta, key):
    tmp = ruta.with_suffix('.json.gz')
    tmp.write_bytes(gzip.compress(ruta.read_bytes()))
    r = subprocess.run(['aws', 's3', 'cp', str(tmp), f'{S3}/{key}', '--content-type', 'application/json',
                        '--content-encoding', 'gzip', '--cache-control', 'public, max-age=60'],
                       capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if r.returncode:
        raise SystemExit(f'S3 falló: {r.stderr.strip()}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batalla')
    ap.add_argument('--subir', action='store_true')
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--sin-lectura', action='store_true')
    ap.add_argument('--sin-modelo', action='store_true', help='solo diccionario')
    a = ap.parse_args()

    cfg = json.loads((AQUI / 'batallas' / f'{a.batalla}.json').read_text())
    ciudades = json.loads((AQUI / 'ciudades.json').read_text())
    carpeta = DATOS / cfg['id']
    carpeta.mkdir(parents=True, exist_ok=True)
    f_corpus, f_ext = carpeta / 'corpus.json', carpeta / 'externa.json'
    corpus = json.loads(f_corpus.read_text()) if f_corpus.exists() else {}
    ext = json.loads(f_ext.read_text()) if f_ext.exists() else {}

    t0 = time.time()
    fallas = []
    if not a.offline:
        nuevos, fallas = recoger(cfg, corpus, ext)
        print(f'  · {nuevos} titulares nuevos · corpus {len(corpus)} · externa {len(ext)}'
              + (f' · {len(fallas)} consultas fallaron' if fallas else ''))
        f_corpus.write_text(json.dumps(corpus, ensure_ascii=False))
        f_ext.write_text(json.dumps(ext, ensure_ascii=False))
    trm_serie = None if a.offline else trm()

    llm, n_llm = ({}, 0)
    if not a.sin_modelo:
        llm, n_llm = clasificar_llm(cfg, corpus, carpeta, deepseek_key() if not a.offline else '')
        if a.offline:
            f_cl = carpeta / 'clasificacion.json'
            llm = json.loads(f_cl.read_text()) if f_cl.exists() else {}
        print(f'  · {n_llm} titulares clasificados con modelo · {len(llm) - 1 if llm else 0} en caché')
    clas = Clasificador(cfg, ciudades, llm)
    for k, it in corpus.items():
        clas(k, it)
    out = calcular(cfg, corpus, ext, ciudades, trm_serie)
    out['fallas'] = fallas[:10]
    f_x = carpeta / 'x.json'                       # capa X (x_capa.py), solo si es de las últimas 3 h
    if f_x.exists():
        x = json.loads(f_x.read_text())
        if (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(x['generado'])).total_seconds() < 3 * 3600:
            out['x'] = x
    if not a.sin_lectura and not a.offline:
        out['lectura'] = lectura(out, carpeta)

    ruta = carpeta / 'batalla.json'
    ruta.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    m = out['marcador']['ult3h']
    print(f"  · fase {out['fase']} · últimas 3 h: Gobierno F={m['G']['F']} (N={m['G']['N']}) · "
          f"Oposición F={m['O']['F']} (N={m['O']['N']}) · {len(ruta.read_bytes()) // 1024} KB · {time.time() - t0:.0f} s")
    if a.subir:
        subir(ruta, f"{cfg['id']}.json")
        idx = {'v': 1, 'batallas': [{'id': cfg['id'], 'titulo': cfg['titulo'], 'inicio': cfg['inicio'],
                                     'generado': out['generado'], 'fase': out['fase']}]}
        f_idx = DATOS / 'index.json'
        f_idx.write_text(json.dumps(idx, ensure_ascii=False))
        subir(f_idx, 'index.json')
        print('  · publicado en S3')


if __name__ == '__main__':
    main()
