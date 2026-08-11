#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de ¿Quién queda? — mercados de pronóstico sobre elecciones de segundo
grado (Contralor, CNE, Defensor, Procurador...).

Cada corrida:
  1. cosecha titulares de Google News RSS (gratis, sin API key)
  2. descarta los ya vistos y los que no traen contexto del mercado
  3. le pasa los NUEVOS a DeepSeek, que propone ajustes al respaldo político
  4. aplica salvaguardas y recalcula índice + probabilidades
  5. escribe el estado sólo si algo cambió de verdad

    índice = 0,60·respaldo + 0,25·convergencia + 0,15·puntaje_norm

`respaldo` es el componente de juicio; lo mueve el modelo. `convergencia` se
mide sola (share of voice normalizado al líder). `puntaje_norm` es estático.

SALVAGUARDAS (el modelo corre sin revisión humana, así que el código lo acota):
  · clamp: nadie se mueve más de MAX_DELTA puntos de respaldo por corrida
  · todo ajuste debe citar un titular que exista LITERALMENTE en el corpus;
    si el modelo lo inventa, el ajuste se descarta y queda registrado
  · si la respuesta no valida, se conserva el estado anterior (falla cerrado)
  · convergencia sólo se mueve con muestra suficiente (MIN_MENCIONES)
  · todo cambio queda en `log`, con su titular y enlace, visible en la página

Uso:
    python3 motor.py                 # todos los mercados abiertos
    python3 motor.py contralor-2026  # uno solo
    python3 motor.py --dry-run       # no escribe ni sube
    python3 motor.py --sin-llm       # sólo la parte medible (sin DeepSeek)
"""
import json, os, re, sys, time, hashlib, urllib.request, urllib.parse
import unicodedata, datetime as dt
from xml.etree import ElementTree
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(ROOT))
OUT_DIR = os.path.join(REPO, 'Bases de datos', 'pronosticos')
S3_PREFIX = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pronosticos'

PESOS = {'respaldo': .60, 'convergencia': .25, 'puntaje': .15}
MAX_DELTA = 12          # tope de movimiento del respaldo por corrida
MIN_MENCIONES = 6       # muestra mínima para mover convergencia
VENTANA_DIAS = 14       # ventana de la convergencia
SUAVIZADO = .5          # peso de la medición nueva frente a la anterior
MAX_TITULARES_LLM = 45  # cuántos titulares nuevos ve el modelo
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Solidez de la fuente. No todo titular pesa igual: el modelo cita fuente pero
# no sabe cuál es seria, y sin esto un portal pequeño movía a un candidato lo
# mismo que una investigación de Cambio (medido: Castro subió 6 puntos por un
# titular especulativo de un diario regional).
# El factor multiplica el movimiento, no lo vetea: una exclusiva puede salir en
# un medio chico, pero entonces mueve poco hasta que la confirme otro.
MEDIOS_REFERENCIA = {  # ×1,0 — reporteo político propio y verificable
    'cambio', 'la silla vacia', 'lasillavacia', 'revista semana', 'semana',
    'el espectador', 'elespectador', 'el tiempo', 'eltiempo', 'el colombiano',
    'elcolombiano', 'blu radio', 'bluradio', 'caracol radio', 'caracol',
    'noticias caracol', 'la fm', 'lafm', 'w radio', 'wradio', 'rcn radio',
    'newsroom rcn radio', 'noticias rcn', 'infobae', 'portafolio', 'la republica',
    'larepublica', 'el heraldo', 'elheraldo', 'el pais', 'elpais', 'el universal',
    'eluniversal', 'rtvc noticias', 'el nuevo siglo', 'elnuevosiglo', 'la opinion',
    'laopinion', 'vanguardia', 'asuntos legales', 'valora analitik', 'valoraanalitik',
}
MEDIOS_SECUNDARIOS = {  # ×0,6 — agregadores y prensa regional establecida
    'pulzo', 'minuto30', 'minuto60', 'las2orillas', 'colombia.com', 'kienyke',
    'diario del huila', 'diario del sur', 'diario del cauca', 'hsb noticias',
    'ifm noticias', 'el frente', 'telemedellin', 'canal 1 en vivo', 'canal 1',
    'red mas', 'redmas', 'yahoo', 'msn', 'el expediente', 'la libertad',
}
PESO_DESCONOCIDO = .35  # conservador: si no lo reconozco, mueve poco


def peso_medio(medio):
    m = norm(medio or '')
    if not m:
        return PESO_DESCONOCIDO
    for k in MEDIOS_REFERENCIA:
        if k in m:
            return 1.0
    for k in MEDIOS_SECUNDARIOS:
        if k in m:
            return .6
    return PESO_DESCONOCIDO


DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'
DEEPSEEK_MODEL = 'deepseek-v4-flash'
PROMPT_VERSION = 'v1'


# ---------------------------------------------------------------- utilidades
def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def ahora():
    return dt.datetime.now(dt.timezone.utc).astimezone(
        dt.timezone(dt.timedelta(hours=-5)))


def iso(d=None):
    return (d or ahora()).isoformat(timespec='seconds')


def hid(s):
    return hashlib.sha256(norm(s).encode()).hexdigest()[:16]


def log(*a):
    print(f"[{iso()[11:19]}]", *a, flush=True)


# ------------------------------------------------------------------ cosecha
def gn_url(q, dias):
    query = urllib.parse.quote(f'{q} when:{dias}d')
    return (f'https://news.google.com/rss/search?q={query}'
            '&hl=es-419&gl=CO&ceid=CO:es')


def fetch_rss(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_rss(xml_bytes):
    out = []
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return out
    for it in root.iter('item'):
        titulo = (it.findtext('title') or '').strip()
        if not titulo:
            continue
        medio = ''
        src = it.find('source')
        if src is not None and src.text:
            medio = src.text.strip()
            # Google News repite el medio como sufijo del título
            if medio and titulo.endswith(' - ' + medio):
                titulo = titulo[:-(len(medio) + 3)].strip()
        pub = it.findtext('pubDate') or ''
        try:
            fecha = dt.datetime.strptime(pub[:25], '%a, %d %b %Y %H:%M:%S').date().isoformat()
        except Exception:
            fecha = ahora().date().isoformat()
        out.append({'titulo': titulo, 'medio': medio,
                    'url': (it.findtext('link') or '').strip(), 'fecha': fecha})
    return out


def queries_de(mercado):
    """Consultas por TEMA + una por CANDIDATO vivo.

    Buscar sólo por tema deja ciego al motor frente a la noticia que mueve a
    UNA persona: medido, con sólo las consultas temáticas el corpus traía un
    único titular sobre Zuluaga —del 3-ago y favorable— justo el día en que la
    prensa reportaba que perdía los votos. La caída existía y el motor no la
    veía. Una consulta por nombre resuelve eso.
    """
    qs = list(mercado['queries'])
    ancla = (mercado.get('contexto') or [''])[0]
    vivos = [c for c in mercado['candidatos'] if c.get('respaldo', 0) >= 12]
    for c in sorted(vivos, key=lambda c: -c.get('respaldo', 0))[:8]:
        qs.append(f"{c['nombre']} {ancla}")
    return qs


def cosechar(mercado, dias=VENTANA_DIAS):
    """Titulares del mercado, deduplicados y filtrados a su contexto."""
    urls = [gn_url(q, dias) for q in queries_de(mercado)]
    filas = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(lambda u: _safe_fetch(u), urls):
            filas.extend(res)
    ctx = [norm(c) for c in mercado.get('contexto', [])]
    vistos, out = set(), []
    for f in filas:
        k = hid(f['titulo'][:80])
        if k in vistos:
            continue
        vistos.add(k)
        t = norm(f['titulo'])
        if ctx and not any(c in t for c in ctx):
            continue                      # descarta homónimos y ruido
        f['id'] = k
        out.append(f)
    out.sort(key=lambda f: f['fecha'], reverse=True)
    return out


def _safe_fetch(u):
    try:
        return parse_rss(fetch_rss(u))
    except Exception as e:
        log('  ! fallo RSS:', str(e)[:70])
        return []


# ------------------------------------------------------------- convergencia
def convergencia(mercado, titulares, previa):
    """Share of voice normalizado al líder.

    Dos correcciones aprendidas midiendo: el corpus de una ventana es chico
    (decenas de titulares, no miles), así que
      · se suaviza con Laplace (+1): no salir en UNA ventana no puede hundir a
        cero a alguien que la prensa sí cuenta entre los punteros;
      · se promedia con la medición anterior, para que una ventana rara mueva
        el índice a la mitad de velocidad y no de un salto.
    Y si no hay muestra suficiente, no se mueve nada.
    """
    cuenta = {c['id']: 0 for c in mercado['candidatos']}
    for f in titulares:
        t = norm(f['titulo'])
        for c in mercado['candidatos']:
            if any(norm(a) in t for a in c['alias']):
                cuenta[c['id']] += 1
    total = sum(cuenta.values())
    if total < MIN_MENCIONES:
        log(f'  convergencia: muestra insuficiente ({total}), se conserva')
        return previa, cuenta
    mx = max(cuenta.values())

    def escalon(v):
        # Escalonado, no proporcional: el componente mide PRESENCIA en el
        # reporteo, no volumen. Con corpus de decenas de titulares, un share
        # proporcional ordena entre punteros por ruido (2 menciones vs 6 no
        # significa el doble de opción); el escalón separa presentes de
        # ausentes, que es para lo que sirve.
        if v == 0:
            return 25
        if v >= mx:
            return 100
        return 85 if v >= mx / 2 else 65

    cruda = {k: escalon(v) for k, v in cuenta.items()}
    if not previa or not any(previa.values()):
        return {k: round(v) for k, v in cruda.items()}, cuenta   # primera corrida
    return ({k: round(SUAVIZADO * v + (1 - SUAVIZADO) * previa.get(k, v))
             for k, v in cruda.items()}, cuenta)


# ------------------------------------------------------------------- modelo
SYSTEM = """Eres un analista político colombiano que mantiene un índice de opción
para una elección de segundo grado (la elige el Congreso o una corporación, no
el voto popular).

Tu única tarea: leer titulares de prensa NUEVOS y decidir si el RESPALDO POLÍTICO
de cada candidato subió, bajó o quedó igual. El respaldo es una escala 0-100:

  90-100  coalición mayoritaria cerrada y pública
  70-85   un partido grande + aliados, sin veto activo
  55-70   respaldos fuertes pero con veto o riesgo declarado
  30-50   respaldo que se está evaporando
  0-15    sin padrino

REGLAS DURAS:
1. Sólo mueves a un candidato si un titular NUEVO lo justifica. Sin titular, no
   hay movimiento.
2. Cada ajuste DEBE incluir el campo "titular" copiado LITERALMENTE de la lista
   que te doy. Si lo parafraseas o lo inventas, el ajuste se descarta.
3. No inventes respaldos, partidos, cifras de votos ni hechos que no estén en los
   titulares.
4. Un titular de perfil o entrevista NO es respaldo político. Un anuncio de
   bancada, un veto, un retiro o un conteo de votos SÍ lo son.
5. Ante la duda, no muevas. La estabilidad es preferible al ruido.
6. Distingue una fuente que afirma algo de un hecho confirmado: si un solo medio
   dice que un candidato "queda fuera" y otros lo siguen contando, baja moderado,
   no lo hundas.

Devuelve SÓLO un JSON válido, sin explicación ni marcas de código:
{"ajustes":[{"id":"<id_candidato>","respaldo":<0-100>,"motivo":"<10-20 palabras>",
"titular":"<titular literal de la lista>"}],"resumen":"<1 frase sobre el día>"}

Si nada cambió: {"ajustes":[],"resumen":"sin movimientos"}"""


def deepseek_key():
    k = os.environ.get('DEEPSEEK_API_KEY')
    if k:
        return k
    # patrón del proyecto: leerla de la config de la Lambda caudal-analiza
    import subprocess
    try:
        r = subprocess.run(
            ['aws', 'lambda', 'get-function-configuration',
             '--function-name', 'caudal-analiza',
             '--query', 'Environment.Variables.DEEPSEEK_API_KEY',
             '--output', 'text'],
            capture_output=True, text=True, timeout=30)
        k = (r.stdout or '').strip()
        return k if k and k != 'None' else None
    except Exception:
        return None


def llamar_llm(mercado, estado, nuevos):
    key = deepseek_key()
    if not key:
        log('  ! sin DEEPSEEK_API_KEY: se omite el ajuste de respaldo')
        return None
    cands = "\n".join(
        f"- {c['id']}: {c['nombre']} ({c['cargo']}) — respaldo actual "
        f"{estado['respaldo'].get(c['id'], c['respaldo'])}/100"
        for c in mercado['candidatos'])
    tits = "\n".join(f"- [{f['fecha']}] {f['medio']}: {f['titulo']}"
                     for f in nuevos[:MAX_TITULARES_LLM])
    user = (f"ELECCIÓN: {mercado['titulo']} ({mercado['cuerpo']}, "
            f"umbral {mercado['umbral']}, se decide el {mercado['cierra'][:10]}).\n\n"
            f"CANDIDATOS Y RESPALDO ACTUAL:\n{cands}\n\n"
            f"TITULARES NUEVOS DESDE LA ÚLTIMA CORRIDA:\n{tits}")
    # V4 gasta presupuesto en razonamiento: con prompt largo puede devolver
    # content vacío y finish_reason=length. Se reintenta con más techo.
    for max_tok in (16000, 24000):
        try:
            body = json.dumps({
                'model': DEEPSEEK_MODEL,
                'messages': [{'role': 'system', 'content': SYSTEM},
                             {'role': 'user', 'content': user}],
                'temperature': 0.2, 'max_tokens': max_tok,
            }).encode()
            req = urllib.request.Request(
                DEEPSEEK_URL, data=body,
                headers={'Content-Type': 'application/json',
                         'Authorization': f'Bearer {key}'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            ch = data['choices'][0]
            txt = (ch['message'].get('content') or '').strip()
            txt = re.sub(r'^```(?:json)?\s*|\s*```$', '', txt, flags=re.M).strip()
            if not txt:
                u = data.get('usage', {})
                log(f"  ! content vacío (finish={ch.get('finish_reason')}, "
                    f"razonamiento={u.get('completion_tokens_details', {}).get('reasoning_tokens')}, "
                    f"techo={max_tok})")
                continue
            return json.loads(txt)
        except json.JSONDecodeError as e:
            log('  ! JSON inválido del modelo:', str(e)[:90])
            continue
        except Exception as e:
            log('  ! DeepSeek falló:', str(e)[:120])
            return None
    return None


def aplicar_ajustes(mercado, estado, prop, nuevos):
    """Aplica los ajustes del modelo con todas las salvaguardas."""
    if not prop or not isinstance(prop.get('ajustes'), list):
        return [], []
    titulares_ok = {norm(f['titulo']): f for f in nuevos}
    ids = {c['id'] for c in mercado['candidatos']}
    aplicados, descartados = [], []
    for a in prop['ajustes'][:12]:
        cid = str(a.get('id', ''))
        if cid not in ids:
            descartados.append({'motivo': 'candidato inexistente', 'raw': a}); continue
        try:
            nuevo = int(round(float(a.get('respaldo'))))
        except Exception:
            descartados.append({'motivo': 'respaldo no numérico', 'raw': a}); continue
        if not 0 <= nuevo <= 100:
            descartados.append({'motivo': 'respaldo fuera de rango', 'raw': a}); continue

        # el titular debe existir literalmente en el corpus nuevo
        tit = norm(a.get('titular', ''))
        fuente = titulares_ok.get(tit)
        if not fuente:
            fuente = next((f for t, f in titulares_ok.items()
                           if tit and (tit in t or t in tit)), None)
        if not fuente:
            descartados.append({'motivo': 'titular inventado o no verificable',
                                'raw': a}); continue

        viejo = estado['respaldo'].get(cid, 50)
        peso = peso_medio(fuente['medio'])
        pedido = nuevo - viejo
        # primero se pondera por la solidez del medio, después se aplica el tope
        delta = int(round(pedido * peso))
        delta = max(-MAX_DELTA, min(MAX_DELTA, delta))
        if delta == 0:
            continue
        estado['respaldo'][cid] = max(0, min(100, viejo + delta))
        aplicados.append({
            'id': cid, 'de': viejo, 'a': estado['respaldo'][cid],
            'motivo': str(a.get('motivo', ''))[:160],
            'titular': fuente['titulo'], 'medio': fuente['medio'],
            'url': fuente['url'], 'fecha': fuente['fecha'],
            'peso': peso, 'pedido': pedido,
            'recortado': abs(delta) < abs(pedido),
        })
    return aplicados, descartados


# ------------------------------------------------------------------ cálculo
def calcular(mercado, respaldo, conv):
    pts = [c['pts'] for c in mercado['candidatos']]
    lo, hi = min(pts), max(pts)
    filas = []
    for c in mercado['candidatos']:
        pn = 100 * (c['pts'] - lo) / (hi - lo) if hi > lo else 50
        idx = (PESOS['respaldo'] * respaldo.get(c['id'], c['respaldo'])
               + PESOS['convergencia'] * conv.get(c['id'], 0)
               + PESOS['puntaje'] * pn)
        filas.append({**{k: c[k] for k in
                         ('id', 'nombre', 'corto', 'cargo', 'pts')},
                      'respaldo': respaldo.get(c['id'], c['respaldo']),
                      'convergencia': conv.get(c['id'], 0),
                      'indice': round(idx)})
    tot = sum(f['indice'] for f in filas) or 1
    for f in filas:
        f['prob'] = round(100 * f['indice'] / tot)
    # cuadrar a 100 tras redondear
    dif = 100 - sum(f['prob'] for f in filas)
    if dif and filas:
        filas.sort(key=lambda f: -f['indice'])
        filas[0]['prob'] += dif
    filas.sort(key=lambda f: -f['indice'])
    return filas


# ------------------------------------------------------------------- estado
def path_estado(mid):
    return os.path.join(OUT_DIR, f'{mid}.json')


def cargar_estado(mercado):
    p = path_estado(mercado['id'])
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding='utf-8'))
        except Exception:
            log('  ! estado corrupto, se reinicia')
    return {
        'id': mercado['id'],
        'respaldo': {c['id']: c['respaldo'] for c in mercado['candidatos']},
        'convergencia': {c['id']: 0 for c in mercado['candidatos']},
        'vistos': [], 'historia': [], 'log': [],
        'creado': iso(),
    }


def correr(mercado, dry=False, sin_llm=False):
    log(f"— {mercado['id']}")
    estado = cargar_estado(mercado)
    estado.setdefault('respaldo', {})
    for c in mercado['candidatos']:
        estado['respaldo'].setdefault(c['id'], c['respaldo'])

    titulares = cosechar(mercado)
    log(f"  {len(titulares)} titulares en ventana de {VENTANA_DIAS} días")
    vistos = set(estado.get('vistos', []))
    nuevos = [f for f in titulares if f['id'] not in vistos]
    log(f"  {len(nuevos)} nuevos desde la última corrida")

    conv_prev = estado.get('convergencia', {})
    conv, cuenta = convergencia(mercado, titulares, conv_prev)

    aplicados, descartados = [], []
    resumen = ''
    if nuevos and not sin_llm:
        prop = llamar_llm(mercado, estado, nuevos)
        if prop:
            aplicados, descartados = aplicar_ajustes(mercado, estado, prop, nuevos)
            resumen = str(prop.get('resumen', ''))[:220]
            log(f"  modelo: {len(aplicados)} ajustes aplicados, "
                f"{len(descartados)} descartados")
            for d in descartados:
                log(f"    ✗ descartado ({d['motivo']})")

    filas = calcular(mercado, estado['respaldo'], conv)
    prev = {f['id']: f['prob'] for f in estado.get('tabla', [])}
    for f in filas:
        f['prob_prev'] = prev.get(f['id'])
        f['delta'] = None if f['prob_prev'] is None else f['prob'] - f['prob_prev']

    # "Cambió" = pasó algo en la política, que es lo que lee quien entra.
    # Manda el ajuste del modelo (que siempre viene con una fuente detrás); la
    # convergencia se reacomoda sola en cada corrida y sus ±1-2 puntos NO son
    # noticia — sin este filtro la página decía "se acaba de mover" mientras el
    # propio modelo reportaba "sin movimientos". Sólo un corrimiento grande de
    # presencia (≥5) cuenta por sí solo.
    cambio = bool(aplicados) or any(abs(f['delta'] or 0) >= 5 for f in filas)
    ts = iso()
    if cambio:
        estado['ultimo_cambio'] = ts
        estado['historia'] = (estado.get('historia', []) +
                              [{'ts': ts, 'probs': {f['id']: f['prob'] for f in filas}}])[-120:]
        for a in aplicados:
            estado['log'] = ([{**a, 'ts': ts}] + estado.get('log', []))[:60]
    estado.update({
        'actualizado': ts,
        'ultimo_cambio': estado.get('ultimo_cambio', ts),
        'convergencia': conv, 'menciones': cuenta, 'tabla': filas,
        'resumen': resumen or estado.get('resumen', ''),
        'n_titulares': len(titulares), 'n_nuevos': len(nuevos),
        'descartados_ultima': len(descartados),
        'meta': {'titulo': mercado['titulo'], 'cuerpo': mercado['cuerpo'],
                 'umbral': mercado['umbral'], 'cierra': mercado['cierra'],
                 'estado': mercado['estado'], 'pts_label': mercado['pts_label'],
                 'pesos': PESOS, 'prompt': PROMPT_VERSION},
    })
    estado['vistos'] = ([f['id'] for f in titulares] + estado.get('vistos', []))[:600]

    log(f"  {'CAMBIÓ' if cambio else 'sin cambios'} · " +
        " · ".join(f"{f['corto']} {f['prob']}%" for f in filas[:5]))
    if dry:
        log('  (dry-run: no se escribe)')
        return estado, cambio
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = path_estado(mercado['id']) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(estado, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path_estado(mercado['id']))
    return estado, cambio


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    sin_llm = '--sin-llm' in sys.argv
    cfg = json.load(open(os.path.join(ROOT, 'mercados.json'), encoding='utf-8'))
    ms = [m for m in cfg['mercados']
          if (not args or m['id'] in args) and m.get('estado') == 'abierto']
    if not ms:
        log('no hay mercados abiertos'); return 0
    idx = []
    for m in ms:
        est, _ = correr(m, dry=dry, sin_llm=sin_llm)
        idx.append({'id': m['id'], 'titulo': m['titulo'],
                    'cierra': m['cierra'], 'estado': m['estado'],
                    'actualizado': est['actualizado']})
    if not dry:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, 'index.json'), 'w', encoding='utf-8') as fh:
            json.dump({'v': iso(), 'mercados': idx}, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
