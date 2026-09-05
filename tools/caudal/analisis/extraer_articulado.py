#!/usr/bin/env python3
"""
Caudal · QUÉ DICE el articulado (extracción estructurada con DeepSeek).

El índice invertido de texto (build_texto_index.py) contesta "qué proyectos
MENCIONAN X". No contesta "qué CAMBIA este proyecto" — que es lo que un gremio
paga. Este módulo lee el texto que ya está en S3 y lo convierte en campos:

    qué norma modifica · qué obligaciones nuevas crea y sobre quién ·
    a quién le aplica · qué sanciones establece · quién vigila/reglamenta ·
    desde cuándo rige y con qué transiciones

REGLAS DURAS (no negociables, van dentro del prompt y se verifican al normalizar)
--------------------------------------------------------------------------------
  · CERO invención. Cada campo sale del texto o queda vacío/null. Si el
    documento no lo dice, el campo va null — nada de "probablemente".
  · Cada extracción DECLARA su `base`: de qué documento salió (texto radicado,
    exposición de motivos, ponencia, o solo el título). La UI lo muestra, igual
    que el resumen ciudadano de legislativo-en-vivo.html.
  · PROMPT_VERSION entra a la llave de caché: al cambiar el prompt, las
    extracciones viejas se re-piden solas.
  · Presupuesto de salida generoso, con reintento. MEDIDO en este proyecto: con
    2000, V4 gasta el presupuesto en razonamiento y devuelve `content` VACÍO con
    finish_reason=length en 7 de 20 docs. Subir el techo no encarece: solo se
    cobran los tokens generados. Ojo: acá el techo arranca MÁS ALTO que los 6000
    de harvest_supersalud_registro.py porque un articulado de 60 artículos
    genera mucha más salida que una resolución de la Supersalud — medido, 2 de 3
    radicados se truncaban con 6000 y uno seguía truncándose con 12000. Y el
    reintento no es gratis: vuelve a mandar TODO el input, así que arrancar bajo
    para "ahorrar" sale más caro que arrancar alto.

DE DÓNDE SALE EL TEXTO (y por qué en ese orden)
-----------------------------------------------
  1. `texto_radicado`      — texto_s3 (radicados-texto/…): el radicado completo
                             de la legislatura viva. Es UN documento por
                             proyecto, sin contaminación. La mejor base.
  2. `exposicion_motivos`  — gaceta de expo-motivos compartida por ≤2 proyectos:
                             ahí la gaceta ES el texto radicado del proyecto.
  3. `ponencia`            — gaceta de ponencia compartida por ≤4 proyectos:
                             trae el pliego de modificaciones y el texto
                             propuesto (a veces más actual que el radicado).
  4. `titulo`              — sin documento. Se extrae SOLO lo que el título dice
                             de verdad (casi siempre nada más que qué norma
                             modifica) y el resto queda null, declarado.

Los umbrales de "compartida" son los MISMOS de build_texto_index.py: una gaceta
referenciada por muchos proyectos es un boletín de radicación masiva y atribuirle
su contenido a cada uno sería inventar.

Comandos (resumible; una extracción por proyecto en caché):
  python3 tools/caudal/analisis/extraer_articulado.py plan
  python3 tools/caudal/analisis/extraer_articulado.py extract --cuatrienio 2026-2030
  python3 tools/caudal/analisis/extraer_articulado.py extract --limit 50 --workers 4
  python3 tools/caudal/analisis/extraer_articulado.py build      # → dist/s3/articulado.json
  python3 tools/caudal/analisis/extraer_articulado.py stats

Necesita DEEPSEEK_API_KEY en el entorno:
  export DEEPSEEK_API_KEY=$(aws lambda get-function-configuration \
    --function-name caudal-analiza \
    --query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)

Todo stdlib (curl/aws por subprocess, urllib para la API).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'analisis'
EXDIR = Path(os.environ['CAUDAL_EXTRACCION_DIR']) if os.environ.get('CAUDAL_EXTRACCION_DIR') \
    else OUT / 'extract'                 # una respuesta por proyecto (caché)
TXTCACHE = OUT / 'txt'               # ventana enviada al modelo (para auditar)

# Cuántas obligaciones se le piden al modelo por documento. Medido: con 8, el
# 32B llega al tope en el 60% de los documentos con texto radicado (el 30B en
# el 27%) — o sea que en más de la mitad de los casos el techo lo pone el
# prompt, no el modelo. Subirlo es más barato que un modelo más grande.
MAX_OBLIGACIONES = int(os.environ.get('CAUDAL_MAX_OBLIGACIONES', '8'))
BUCKET = 'caudal-legislativo'

DEEPSEEK_MODEL = os.environ.get('CAUDAL_EXTRACCION_MODEL', 'deepseek-v4-flash')
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'

# ── Backend LOCAL (sep-2026) ─────────────────────────────────────────────────
# La Mac M5 Pro (48 GB) corre un modelo local por Ollama. Se elige con
#   CAUDAL_EXTRACCION_BACKEND=ollama  CAUDAL_EXTRACCION_MODEL=qwen3:30b-a3b
# y va por la API NATIVA de Ollama (/api/chat), no por la OpenAI-compatible:
# solo la nativa acepta `think:false` (Qwen3 razona por defecto y eso triplica
# la salida) y `options.num_ctx` (el default de Ollama es 4k y la ventana que
# se manda son ~8k tokens: sin esto trunca el documento EN SILENCIO).
# Las extracciones locales van a un caché APARTE (CAUDAL_EXTRACCION_DIR) para
# poder compararlas contra las de DeepSeek sin pisarlas.
BACKEND = os.environ.get('CAUDAL_EXTRACCION_BACKEND', 'deepseek')
OLLAMA_URL = os.environ.get('CAUDAL_OLLAMA_URL', 'http://localhost:11434/api/chat')
OLLAMA_NUM_CTX = int(os.environ.get('CAUDAL_OLLAMA_CTX', '32768'))

# ⚠ Sube esto al tocar ART_SYSTEM o el vocabulario de sectores: entra a la llave
# de caché (`_pv`) y las extracciones viejas se re-piden solas.
# Van SEPARADOS a propósito (documento vs solo-título): tocar el prompt del
# título no puede obligar a re-extraer los 133 radicados, que son los caros.
PROMPT_VERSION = 'a2'
PROMPT_VERSION_TITULO = 't2'


def _pv(base):
    return PROMPT_VERSION_TITULO if base == 'titulo' else PROMPT_VERSION

# Precio de referencia de V4 Flash (USD por millón de tokens). Solo se usa para
# REPORTAR costo; el gasto real lo dice el `usage` de cada llamada, que se
# guarda por documento. Si el proveedor cambia la tarifa, cambia acá.
USD_IN_PER_M = 0.28
USD_OUT_PER_M = 0.42

# Ventana máxima de texto que se le manda al modelo. Los radicados van de 15 KB a
# 300 KB; mandar todo multiplicaría el costo sin ganar precisión (el articulado
# vive en un tramo identificable). 28k chars ≈ 8k tokens.
MAX_CHARS = 28_000
HEAD_CHARS = 2_500        # encabezado que se conserva siempre (título + fórmula)

# Presupuesto de salida: 1er intento, reintento, y último recurso (ver _extraer).
MAX_TOKENS = (12_000, 20_000)

MAX_COMPARTIDA = 4        # idénticos a build_texto_index.py — ver docstring
MAX_COMPARTIDA_EXPO = 2

# Vocabulario CERRADO de sectores. Es lo que permite cruzar "a quién le aplica"
# con las empresas vigiladas del perfil del cliente (empresas.py usa estas
# mismas llaves de sector) y con los sectores del pilar Regulatorio. Lo que el
# modelo devuelva fuera de esta lista se descarta del campo `sectores` y queda
# como texto libre en `actividades` — nunca se inventa una llave nueva.
SECTORES = [
    'salud', 'farma', 'financiero', 'seguros', 'pensiones', 'energia', 'mineria',
    'agua', 'telecom', 'tecnologia', 'transporte', 'aviacion', 'logistica',
    'agro', 'alimentos', 'industria', 'construccion', 'retail', 'comercio',
    'consumo', 'educacion', 'turismo', 'juegos', 'medios', 'textil',
    'automotriz', 'seguridad', 'servicios', 'laboral', 'ambiental', 'tributario',
    'contratacion', 'vivienda', 'justicia', 'cultura', 'deporte', 'defensa',
    'territorial', 'multisectorial',
]
_SECTORES = set(SECTORES)

BASES = ('texto_radicado', 'exposicion_motivos', 'ponencia', 'otro_documento', 'titulo')
BASE_LABEL = {
    'texto_radicado': 'texto radicado completo',
    'exposicion_motivos': 'gaceta de exposición de motivos',
    'ponencia': 'gaceta de ponencia',
    'otro_documento': 'gaceta del trámite',
    'titulo': 'solo el título del proyecto',
}


# ----------------------------------------------------------------- prompt
ART_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy el texto de un proyecto de ley o "
    "acto legislativo del Congreso de Colombia. Tu tarea es extraer, de forma "
    "estructurada, QUÉ CAMBIA ese proyecto para quien tiene que cumplirlo.\n"
    "\n"
    "REGLA DURA E INNEGOCIABLE: usa SOLAMENTE lo que dice el texto que te doy. "
    "Si un dato no aparece, el campo va null o lista vacía. NO infieras, NO "
    "completes con conocimiento previo del derecho colombiano, NO escribas "
    "'probablemente' ni 'se entiende que'. Es preferible un campo vacío a un "
    "campo adivinado. Si el texto está incompleto o cortado, extrae solo lo que "
    "alcanzaste a leer.\n"
    "\n"
    "Devuelves SIEMPRE un JSON válido con exactamente estas claves:\n"
    "\n"
    "- resumen: 1 o 2 frases, en lenguaje llano, sobre qué cambia en la práctica. "
    "Nada de repetir el título. null si el texto no alcanza para decirlo.\n"
    "\n"
    "- modifica: lista de las normas vigentes que el proyecto toca. Cada ítem:\n"
    "    {\"norma\": \"Ley 100 de 1993\" | \"Decreto 1072 de 2015\" | \"Código Penal\" | "
    "\"Constitución Política\", \"articulos\": [\"5\",\"12 parágrafo 2\"], "
    "\"efecto\": \"modifica\"|\"adiciona\"|\"deroga\"|\"sustituye\"|\"reglamenta\"}\n"
    "  Lista vacía si el proyecto es norma nueva que no modifica nada anterior. "
    "`articulos` vacío si el texto no precisa cuáles.\n"
    "\n"
    "- obligaciones: obligaciones NUEVAS que el proyecto crea, y sobre quién "
    "recaen. Cada ítem:\n"
    "    {\"obligacion\": \"qué hay que hacer, en una frase\", "
    "\"sobre_quien\": \"a quién se le exige (empleadores, EPS, operadores de "
    "plataformas, entidades públicas…)\", \"plazo\": \"el plazo si el texto lo "
    "fija, si no null\"}\n"
    "  Solo deberes exigibles a alguien concreto. NO metas declaraciones de "
    "principios, definiciones ni objetivos. MÁXIMO " + str(MAX_OBLIGACIONES) +
    ", las más relevantes para "
    "quien tiene que cumplirlas, y cada una en UNA frase de máximo 25 palabras.\n"
    "\n"
    "- aplica_a: a quién le aplica la norma.\n"
    "    {\"sectores\": [llaves de la lista cerrada de abajo],\n"
    "     \"sujetos\": [\"a quién, en las palabras del texto\"],\n"
    "     \"tamano\": \"si el texto distingue por tamaño de empresa (micro, "
    "pymes, grandes contribuyentes…), si no null\",\n"
    "     \"actividades\": [\"actividades económicas concretas que el texto "
    "nombra\"],\n"
    "     \"ambito\": \"nacional\"|\"territorial\"|\"sectorial\"|null}\n"
    "  `sectores` SOLO puede traer llaves de esta lista, y solo las que el texto "
    "toque de verdad: " + ', '.join(SECTORES) + ". "
    "Si el proyecto es de aplicación general, usa 'multisectorial'. Lista vacía "
    "si no se puede determinar.\n"
    "\n"
    "- sanciones: sanciones o multas que el proyecto establece. Cada ítem:\n"
    "    {\"tipo\": \"multa\"|\"suspension\"|\"cancelacion\"|\"penal\"|"
    "\"disciplinaria\"|\"otra\", \"cuantia\": \"tal como la dice el texto (ej "
    "'hasta 500 SMLMV'), null si no la fija\", \"conducta\": \"qué se sanciona\", "
    "\"quien_sanciona\": \"la autoridad, null si no lo dice\"}\n"
    "  Lista vacía si el proyecto no crea sanciones.\n"
    "\n"
    "- vigilancia: entidades a las que el proyecto les asigna vigilar, "
    "reglamentar o administrar. Cada ítem:\n"
    "    {\"entidad\": \"nombre tal como aparece\", \"rol\": \"vigilar\"|"
    "\"reglamentar\"|\"administrar\"|\"sancionar\"|\"certificar\"|\"otro\", "
    "\"plazo\": \"plazo para reglamentar si lo fija, si no null\"}\n"
    "\n"
    "- vigencia: {\"rige_desde\": \"lo que diga el artículo de vigencia (ej 'a "
    "partir de su promulgación', 'seis meses después de su publicación'), null "
    "si no aparece\", \"transiciones\": [\"plazos de adecuación o regímenes de "
    "transición que el texto conceda\"]}\n"
    "\n"
    "- confianza: \"alta\" si leíste el articulado completo; \"media\" si el "
    "texto venía cortado o es una ponencia parcial; \"baja\" si apenas pudiste "
    "leer el título o un fragmento suelto.\n"
)

ART_SYSTEM_TITULO = (
    "Eres analista legislativo de Cauce. NO tengo el texto de este proyecto de "
    "ley colombiano: solo tengo su TÍTULO oficial. Extrae únicamente lo que el "
    "título dice de forma literal.\n"
    "\n"
    "REGLA DURA: el título casi nunca dice obligaciones, sanciones, vigencia ni "
    "quién vigila. Esos campos van VACÍOS salvo que el título los nombre "
    "explícitamente. NO adivines a partir del tema. Es un error grave llenar un "
    "campo que el título no dice.\n"
    "\n"
    "Devuelves el MISMO JSON de siempre, con estas claves: resumen, modifica, "
    "obligaciones, aplica_a, sanciones, vigilancia, vigencia, confianza.\n"
    "En la práctica, de un título solo se puede sacar:\n"
    "  · `modifica`: **SÍ tienes que llenarlo** cuando el título nombre una "
    "norma concreta. Es el único campo que un título casi siempre permite "
    "llenar, y dejarlo vacío cuando el título SÍ nombra la norma también es un "
    "error. Ejemplos:\n"
    "      «Por medio de la cual se adiciona un parágrafo al artículo 3 del "
    "Decreto Ley 893 de 2017…» → [{\"norma\":\"Decreto Ley 893 de 2017\","
    "\"articulos\":[\"3\"],\"efecto\":\"adiciona\"}]\n"
    "      «Por la cual se deroga el impuesto a los productos ultraprocesados "
    "de la Ley 2277 de 2022…» → [{\"norma\":\"Ley 2277 de 2022\","
    "\"articulos\":[],\"efecto\":\"deroga\"}]\n"
    "      «Por la cual se crea la política nacional de X» → [] (no nombra "
    "ninguna norma anterior)\n"
    "  · `aplica_a.sectores`: el sector evidente del tema, de esta lista cerrada: "
    + ', '.join(SECTORES) + ".\n"
    "  · `resumen`: una frase sobre de qué trata, marcando que es a partir del "
    "título.\n"
    "Todo lo demás (obligaciones, sanciones, vigilancia, vigencia): listas "
    "vacías y null, salvo que el título los diga con todas sus letras. "
    "`confianza` siempre 'baja'."
)


# ------------------------------------------------------------------ carga
def _load(name):
    p = DIST / name
    return [json.loads(l) for l in open(p, encoding='utf-8')] if p.exists() else []


_DIARIO = {'radicados-texto': REPO / 'Bases de datos' / 'leyes-senado' / 'diario',
           'radicados-camara-texto': REPO / 'Bases de datos' / 'leyes-senado' / 'diario-camara'}


def _local_de(key):
    """Ruta local del texto del radicado que el cron ya dejó en disco (gratis)."""
    partes = (key or '').split('/')
    if len(partes) != 3 or partes[0] not in _DIARIO:
        return None
    return _DIARIO[partes[0]] / partes[1] / 'textos-txt' / partes[2]


_S3_KEYS_CACHE = OUT / '_s3_gacetas_keys.txt'


def s3_gaceta_keys(refresh=False):
    """Set de gacetas que YA tienen texto en S3 (una sola llamada, cacheada)."""
    if refresh or not _S3_KEYS_CACHE.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(['aws', 's3', 'ls', f's3://{BUCKET}/gacetas-texto/', '--recursive'],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print('! no se pudo listar gacetas-texto:', r.stderr[:200], file=sys.stderr)
            return set()
        keys = [ln.split()[-1] for ln in r.stdout.splitlines() if ln.strip()]
        _S3_KEYS_CACHE.write_text('\n'.join(keys), encoding='utf-8')
    return {ln.strip().split('/')[-1][:-4]
            for ln in _S3_KEYS_CACHE.read_text(encoding='utf-8').splitlines() if ln.strip()}


_RANK_DOC = {'exposicion_motivos': 0, 'ponencia_1': 1, 'ponencia_2': 1,
             'texto_plenaria': 2, 'conciliacion': 3, 'objeciones': 4}
_RANK_BASE = {0: 'exposicion_motivos', 1: 'ponencia', 2: 'otro_documento',
              3: 'otro_documento', 4: 'otro_documento'}


def _texto_por_manifiesto():
    """{token de radicado → key del texto en S3}, leído de los manifiestos del
    rastreo diario.

    `proyectos.jsonl` se regenera en el cron y trae `texto_s3`, pero el texto de
    los radicados entra a S3 varias veces al día: entre una reconstrucción del
    dataset y la siguiente hay proyectos cuyo texto YA está y el dataset todavía
    no lo sabe. Medido: 56 proyectos de la legislatura viva quedaban extraídos
    solo del título teniendo el radicado completo en S3. El manifiesto es la
    fuente más fresca, así que se usa como respaldo — nunca pisa al dataset.
    """
    out = {}
    for nombre in ('pl-radicados-2026-2027.jsonl',
                   'pl-radicados-camara-2026-2027.jsonl'):
        p = DIST / 's3' / nombre
        if not p.exists():
            continue
        for ln in p.read_text(encoding='utf-8').splitlines():
            if not ln.strip():
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if not d.get('s3_txt'):
                continue
            for k in ('numero_senado', 'numero_camara', 'proyecto'):
                t = _num_token(d.get(k))
                if t:
                    out.setdefault(t, d['s3_txt'])
    return out


def _num_token(num):
    m = re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', str(num or ''))
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def construir_plan(refresh_s3=False):
    """[{tok, tb, id, base, fuente, ...}] — de dónde sale el texto de cada
    proyecto. Un solo documento por proyecto: el de mejor base disponible."""
    proyectos = [(r, 'pdly') for r in _load('proyectos.jsonl')]
    proyectos += [(r, 'pal') for r in _load('actos-legis.jsonl')]
    manif = _texto_por_manifiesto()

    # cuántos proyectos referencian cada gaceta (para el umbral de "compartida")
    share, solo_expo = Counter(), {}
    for r, _tb in proyectos:
        for g in r.get('gacetas', []):
            gk = (g.get('gaceta') or '').replace('/', '-')
            if not gk:
                continue
            share[gk] += 1
            solo_expo[gk] = solo_expo.get(gk, True) and g.get('tipo') == 'exposicion_motivos'

    tiene_texto = s3_gaceta_keys(refresh_s3)
    plan = []
    for r, tb in proyectos:
        item = {'tok': f"{tb}:{r['id']}", 'tb': tb, 'id': r['id'],
                'titulo': r.get('titulo', ''),
                'numero': r.get('numero_senado') or r.get('numero_camara') or '',
                'numero_camara': r.get('numero_camara') or '',
                'legislatura': r.get('legislatura', ''),
                'cuatrienio': r.get('cuatrienio', ''),
                'anio': r.get('anio'), 'resultado': r.get('resultado'),
                'comision': r.get('comision', '')}
        txt = r.get('texto_s3')
        if not txt:      # respaldo: el manifiesto va más fresco que el dataset
            for k in ('numero_senado', 'numero_camara'):
                txt = manif.get(_num_token(r.get(k)))
                if txt:
                    break
        if txt:
            item.update(base='texto_radicado', fuente=txt,
                        fuente_txt='texto radicado')
            plan.append(item)
            continue
        mejor = None
        for g in r.get('gacetas', []):
            gk = (g.get('gaceta') or '').replace('/', '-')
            if not gk or gk not in tiene_texto:
                continue
            lim = MAX_COMPARTIDA_EXPO if solo_expo.get(gk) else MAX_COMPARTIDA
            if share[gk] > lim:
                continue          # boletín: atribuirle su contenido sería inventar
            rank = _RANK_DOC.get(g.get('tipo'), 5)
            if mejor is None or rank < mejor[0]:
                mejor = (rank, gk, g.get('tipo'), g.get('gaceta'))
        if mejor:
            item.update(base=_RANK_BASE.get(mejor[0], 'otro_documento'),
                        fuente=f'gacetas-texto/{mejor[1]}.txt',
                        fuente_txt=f'Gaceta {mejor[3]} · {(mejor[2] or "").replace("_", " ")}')
        else:
            item.update(base='titulo', fuente=None, fuente_txt='solo el título')
        plan.append(item)
    return plan


# ------------------------------------------------------------------ texto
def fetch_texto(fuente):
    """Texto del documento. Radicados del disco local del cron si está (gratis),
    si no de S3 por streaming (sin tocar disco: el corpus son ~3 GB)."""
    if not fuente:
        return None
    local = _local_de(fuente)
    if local and local.exists():
        return local.read_text(encoding='utf-8', errors='replace')
    r = subprocess.run(['aws', 's3', 'cp', f's3://{BUCKET}/{fuente}', '-'],
                       capture_output=True, timeout=120)
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', errors='replace')


_DECRETA_RE = re.compile(r'(?i)\b(decreta|acuerda|ordena|resuelve)\s*:?\s*\n')


def _pos_numero(texto, item):
    """Dónde empieza a hablarse de ESTE proyecto dentro de un boletín. Las
    gacetas admitidas están compartidas por ≤4 proyectos, pero aun así conviene
    anclar: el articulado de otro proyecto arriba desviaría la extracción."""
    for num in (item.get('numero'), item.get('numero_camara')):
        if not num:
            continue
        m = re.match(r'0*(\d+)\D+(\d{2,4})', str(num))
        if not m:
            continue
        n, a = m.group(1), m.group(2)[-2:]
        pat = re.compile(r'\b0*%s\s*(?:de|/)\s*(?:20)?%s\b' % (re.escape(n), re.escape(a)))
        mm = pat.search(texto)
        if mm:
            return mm.start()
    return 0


def ventana(texto, item, max_chars=MAX_CHARS):
    """Tramo del documento que se le manda al modelo.

    El articulado es la carga útil; la exposición de motivos puede ocupar el 80%
    del archivo. Se ancla en la fórmula «DECRETA:» (que abre el articulado) más
    cercana a la mención de ESTE proyecto, conservando siempre el encabezado
    para que el modelo sepa de qué proyecto se trata.
    Devuelve (texto_ventana, modo) — `modo` viaja al `_meta` para poder auditar
    después de qué tramo salió cada extracción.
    """
    texto = (texto or '').strip()
    if len(texto) <= max_chars:
        return texto, 'completo'
    ini = _pos_numero(texto, item)
    m = _DECRETA_RE.search(texto, ini)
    if m is None and ini:
        m = _DECRETA_RE.search(texto)          # el número no ancló; prueba desde el inicio
    anchor = m.start() if m else ini
    if anchor <= HEAD_CHARS:
        return texto[:max_chars], 'inicio'
    cuerpo = texto[anchor:anchor + max_chars - HEAD_CHARS]
    return (texto[:HEAD_CHARS] + '\n\n[…]\n\n' + cuerpo,
            'articulado' if m else 'ancla_numero')


# --------------------------------------------------------------- DeepSeek
class Truncado(Exception):
    pass


def _ollama(system, user, max_tokens, timeout=1800):
    """Misma firma que _deepseek, contra el modelo local. `usage` se arma con
    los conteos que Ollama devuelve (prompt_eval_count / eval_count) para que el
    reporte de costo y las stats sigan funcionando (el costo en USD sale 0 de
    verdad: la tarifa es del proveedor, no del backend)."""
    import urllib.request
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'stream': False, 'think': False, 'format': 'json',
        'options': {'temperature': 0.1, 'num_ctx': OLLAMA_NUM_CTX,
                    'num_predict': max_tokens},
    }).encode('utf-8')
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    usage = {'prompt_tokens': d.get('prompt_eval_count', 0),
             'completion_tokens': d.get('eval_count', 0),
             'eval_ms': (d.get('eval_duration') or 0) / 1e6,
             'prompt_ms': (d.get('prompt_eval_duration') or 0) / 1e6}
    fin = 'stop' if d.get('done_reason', 'stop') == 'stop' else 'length'
    return (d.get('message') or {}).get('content', ''), usage, fin


def _llm(system, user, max_tokens, timeout=180):
    if BACKEND == 'ollama':
        return _ollama(system, user, max_tokens)
    return _deepseek(system, user, max_tokens, timeout)


def _deepseek(system, user, max_tokens, timeout=180):
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise RuntimeError(
            'DEEPSEEK_API_KEY no está en el entorno. Léela de la Lambda:\n'
            "  export DEEPSEEK_API_KEY=$(aws lambda get-function-configuration "
            "--function-name caudal-analiza "
            "--query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)")
    import urllib.request
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': 0.1, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    ch = d['choices'][0]
    return ch['message']['content'], (d.get('usage') or {}), ch.get('finish_reason')


def _extraer(system, user, presupuestos=MAX_TOKENS):
    """Una extracción con reintento de presupuesto. Devuelve (dict, usage)."""
    tot = {'prompt_tokens': 0, 'completion_tokens': 0}
    ultimo = None
    for max_tok in presupuestos:
        raw, usage, fin = _llm(system, user, max_tokens=max_tok)
        tot['prompt_tokens'] += usage.get('prompt_tokens', 0)
        tot['completion_tokens'] += usage.get('completion_tokens', 0)
        raw = (raw or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        if fin == 'length' and not raw.endswith('}'):
            ultimo = f'truncado con {max_tok}'
            continue
        if not raw:
            ultimo = f'content vacío con {max_tok} (finish_reason={fin})'
            continue
        return json.loads(raw), tot
    raise Truncado(ultimo or 'sin contenido')


# ------------------------------------------------------------ normalizado
_EFECTOS = {'modifica', 'adiciona', 'deroga', 'sustituye', 'reglamenta'}
_TIPOS_SANCION = {'multa', 'suspension', 'cancelacion', 'penal', 'disciplinaria', 'otra'}
_ROLES = {'vigilar', 'reglamentar', 'administrar', 'sancionar', 'certificar', 'otro'}
_CONFIANZA = {'alta', 'media', 'baja'}


def _s(v, cap=400):
    """Texto limpio o None. Convierte los 'null'/'N/A' textuales del modelo en
    None de verdad — si no, un campo vacío se vería lleno en la ficha."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        v = str(v)
    if not isinstance(v, str):
        return None
    v = re.sub(r'\s+', ' ', v).strip()
    if not v or v.lower() in ('null', 'none', 'n/a', 'na', 'no aplica', 'no especifica',
                              'no se especifica', 'no determinado', '-', '—'):
        return None
    return v[:cap]


def _lista(v):
    return v if isinstance(v, list) else []


def _norm_extraccion(ex, item, base):
    """dict del modelo → esquema estable, con vocabularios cerrados. Todo lo que
    no encaje se descarta (nunca se inventa una llave)."""
    modifica = []
    for x in _lista(ex.get('modifica'))[:12]:
        if not isinstance(x, dict):
            continue
        norma = _s(x.get('norma'), 160)
        if not norma:
            continue
        ef = (_s(x.get('efecto'), 40) or '').lower()
        arts = [a for a in (_s(v, 60) for v in _lista(x.get('articulos'))[:20]) if a]
        modifica.append({'norma': norma, 'articulos': arts,
                         'efecto': ef if ef in _EFECTOS else None})

    obligaciones = []
    for x in _lista(ex.get('obligaciones'))[:MAX_OBLIGACIONES + 4]:
        if not isinstance(x, dict):
            continue
        que = _s(x.get('obligacion'), 320)
        if not que:
            continue
        obligaciones.append({'obligacion': que,
                             'sobre_quien': _s(x.get('sobre_quien'), 160),
                             'plazo': _s(x.get('plazo'), 120)})

    ap = ex.get('aplica_a') if isinstance(ex.get('aplica_a'), dict) else {}
    sectores = [s for s in (str(v).strip().lower() for v in _lista(ap.get('sectores'))[:8])
                if s in _SECTORES]
    ambito = (_s(ap.get('ambito'), 40) or '').lower()
    aplica_a = {
        'sectores': sorted(set(sectores)),
        'sujetos': [s for s in (_s(v, 140) for v in _lista(ap.get('sujetos'))[:10]) if s],
        'tamano': _s(ap.get('tamano'), 140),
        'actividades': [s for s in (_s(v, 140) for v in _lista(ap.get('actividades'))[:10]) if s],
        'ambito': ambito if ambito in ('nacional', 'territorial', 'sectorial') else None,
    }

    sanciones = []
    for x in _lista(ex.get('sanciones'))[:10]:
        if not isinstance(x, dict):
            continue
        conducta = _s(x.get('conducta'), 240)
        tipo = (_s(x.get('tipo'), 40) or '').lower()
        cuantia = _s(x.get('cuantia'), 160)
        if not (conducta or cuantia):
            continue
        sanciones.append({'tipo': tipo if tipo in _TIPOS_SANCION else 'otra',
                          'cuantia': cuantia, 'conducta': conducta,
                          'quien_sanciona': _s(x.get('quien_sanciona'), 140)})

    vigilancia = []
    for x in _lista(ex.get('vigilancia'))[:10]:
        if not isinstance(x, dict):
            continue
        ent = _s(x.get('entidad'), 160)
        if not ent:
            continue
        rol = (_s(x.get('rol'), 40) or '').lower()
        vigilancia.append({'entidad': ent, 'rol': rol if rol in _ROLES else 'otro',
                           'plazo': _s(x.get('plazo'), 120)})

    vg = ex.get('vigencia') if isinstance(ex.get('vigencia'), dict) else {}
    vigencia = {'rige_desde': _s(vg.get('rige_desde'), 240),
                'transiciones': [s for s in (_s(v, 240) for v in _lista(vg.get('transiciones'))[:6]) if s]}

    conf = (_s(ex.get('confianza'), 20) or '').lower()
    if base == 'titulo':
        conf = 'baja'                        # el título nunca da confianza alta
    elif conf not in _CONFIANZA:
        conf = 'media'

    return {
        'tok': item['tok'], 'tb': item['tb'], 'id': item['id'],
        'base': base, 'base_txt': BASE_LABEL.get(base, base),
        'fuente': item.get('fuente'), 'fuente_txt': item.get('fuente_txt'),
        'resumen': _s(ex.get('resumen'), 600),
        'modifica': modifica, 'obligaciones': obligaciones, 'aplica_a': aplica_a,
        'sanciones': sanciones, 'vigilancia': vigilancia, 'vigencia': vigencia,
        'confianza': conf,
    }


CAMPOS = ('resumen', 'modifica', 'obligaciones', 'aplica_a', 'sanciones',
          'vigilancia', 'vigencia')


def _vacios(d):
    """Campos que quedaron vacíos — la métrica honesta de cuánto rindió el
    documento. Se reporta por documento, no se esconde."""
    out = []
    if not d.get('resumen'):
        out.append('resumen')
    for k in ('modifica', 'obligaciones', 'sanciones', 'vigilancia'):
        if not d.get(k):
            out.append(k)
    ap = d.get('aplica_a') or {}
    if not (ap.get('sectores') or ap.get('sujetos')):
        out.append('aplica_a')
    vg = d.get('vigencia') or {}
    if not (vg.get('rige_desde') or vg.get('transiciones')):
        out.append('vigencia')
    return out


# ------------------------------------------------------------------ extract
def _cache_path(tok):
    return EXDIR / (tok.replace(':', '-') + '.json')


# Calidad de la base, de mejor a peor. Sirve para saber si vale la pena volver
# a pedir una extracción que ya está en caché.
_CALIDAD_BASE = {'texto_radicado': 0, 'exposicion_motivos': 1, 'ponencia': 2,
                 'otro_documento': 3, 'titulo': 4}


def _cacheado(tok, base_plan=None):
    p = _cache_path(tok)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None
    # PROMPT_VERSION en la llave de caché: al cambiar el prompt, lo viejo se
    # re-pide solo (no hay que acordarse de borrar nada). Se compara contra la
    # versión de la base que QUEDÓ registrada, no la planeada: un documento sin
    # texto legible se degrada a 'titulo' y su versión válida es la del título.
    if (d.get('_meta') or {}).get('pv') != _pv(d.get('base')):
        return None
    # Y si desde la última corrida APARECIÓ un documento mejor, la extracción
    # vieja deja de servir. Pasaba de verdad y con el peor caso posible: el
    # radicado de la reforma tributaria llegó a S3 después de que la extracción
    # se hiciera solo con el título, y la caché la dejaba congelada en 'según el
    # título, adopta una reforma tributaria' con cero obligaciones. El texto
    # entra a diario por el cron, así que sin este chequeo el corpus envejece
    # justo en los proyectos que más importan — los que llegan con texto tarde.
    #
    # La comparación va contra la base que se INTENTÓ, no contra la que quedó.
    # Un documento ilegible o de dos líneas se degrada a 'titulo' al procesarlo,
    # y comparar contra el resultado haría que el plan pidiera para siempre un
    # texto que ya se probó y no sirve — un bucle que además cuesta plata en
    # cada corrida. Las entradas viejas no traen el campo: ahí se cae al
    # comportamiento anterior, que es no reintentar.
    intentada = (d.get('_meta') or {}).get('base_intentada') or d.get('base')
    if base_plan and (_CALIDAD_BASE.get(base_plan, 9)
                      < _CALIDAD_BASE.get(intentada, 9)):
        return None
    return d


def _procesar(item, guardar_txt=False):
    base = item['base']
    if base == 'titulo':
        system = ART_SYSTEM_TITULO
        user = (f"TÍTULO OFICIAL: {item['titulo']}\n"
                f"Número: {item.get('numero') or '—'} · Legislatura: {item.get('legislatura') or '—'}\n"
                "(No hay texto del articulado disponible para este proyecto.)")
        modo, chars = 'titulo', len(item['titulo'] or '')
    else:
        txt = fetch_texto(item['fuente'])
        if not txt or len(txt.strip()) < 400:
            # el documento existe pero no tiene texto usable (escaneado sin OCR):
            # se degrada a título, DECLARÁNDOLO — nunca se finge que se leyó.
            item = dict(item, base='titulo', fuente=None,
                        fuente_txt='solo el título (el documento no tiene texto legible)')
            return _procesar(item, guardar_txt)
        system = ART_SYSTEM

        def _user_de(max_chars):
            v, m = ventana(txt, item, max_chars)
            return (f"PROYECTO: {item['titulo']}\n"
                    f"Número: {item.get('numero') or '—'}"
                    + (f" (Cámara {item['numero_camara']})" if item.get('numero_camara') else '')
                    + f" · Legislatura: {item.get('legislatura') or '—'}\n"
                    f"DOCUMENTO: {item.get('fuente_txt')}\n"
                    "Si el documento contiene varios proyectos, extrae SOLO el que "
                    "corresponde al número y título de arriba.\n"
                    "----- TEXTO -----\n" + v), m, len(v)

        user, modo, chars = _user_de(MAX_CHARS)
        if guardar_txt:
            TXTCACHE.mkdir(parents=True, exist_ok=True)
            (TXTCACHE / (item['tok'].replace(':', '-') + '.txt')).write_text(
                user, encoding='utf-8')
    try:
        ex, usage = _extraer(system, user)
    except Truncado:
        # El articulado es tan largo que ni con el presupuesto ampliado cabe la
        # respuesta. Último recurso: media ventana. Se extrae menos, pero se
        # extrae — y queda DECLARADO en `modo` y en la confianza, para no vender
        # como completo lo que se leyó a medias.
        if base == 'titulo':
            raise
        user, _m, chars = _user_de(MAX_CHARS // 2)
        ex, usage = _extraer(system, user, presupuestos=(MAX_TOKENS[-1],))
        modo = 'ventana_corta'
        ex['confianza'] = 'media'
    d = _norm_extraccion(ex, item, item['base'])
    d['_meta'] = {'pv': _pv(item['base']), 'model': DEEPSEEK_MODEL, 'modo': modo,
                  # base que se INTENTÓ, que no siempre es la que quedó: un
                  # documento ilegible o vacío se degrada a 'titulo'. Sin este
                  # registro, el chequeo de calidad de `_cacheado` vería
                  # "el plan ofrece texto y la caché dice título" y volvería a
                  # pedirlo en cada corrida, para siempre.
                  'base_intentada': item['base'],
                  'chars': chars,
                  'tok_in': usage['prompt_tokens'], 'tok_out': usage['completion_tokens'],
                  'backend': BACKEND, 'eval_ms': usage.get('eval_ms'), 'prompt_ms': usage.get('prompt_ms'),
                  'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    d['_meta']['vacios'] = _vacios(d)
    return d


def _usd(tin, tout):
    return tin / 1e6 * USD_IN_PER_M + tout / 1e6 * USD_OUT_PER_M


def cmd_extract(args):
    plan = construir_plan()
    sel = plan
    if args.cuatrienio:
        sel = [p for p in sel if p['cuatrienio'] == args.cuatrienio]
    if args.legislatura:
        sel = [p for p in sel if p['legislatura'] == args.legislatura]
    if args.base:
        sel = [p for p in sel if p['base'] in args.base.split(',')]
    if args.sin_titulo:
        sel = [p for p in sel if p['base'] != 'titulo']
    if args.toks:
        quiero = set(args.toks.split(','))
        sel = [p for p in sel if p['tok'] in quiero]
    # los que ya están en caché con el prompt vigente no se vuelven a pedir
    pend = [p for p in sel if not _cacheado(p['tok'], p['base'])]
    # documento primero, título después: el orden en que aporta valor
    pend.sort(key=lambda p: (p['base'] == 'titulo', -(p.get('anio') or 0)))
    # el conteo del caché se toma ANTES de --limit: calculado después, un
    # `--limit 30` sobre 1.176 pendientes reportaba "ya en caché 1146" y hacía
    # creer que el corpus estaba hecho cuando estaba intacto.
    n_cache = len(sel) - len(pend)
    if args.limit:
        pend = pend[:args.limit]
    print(f'· universo {len(sel)} · ya en caché {n_cache}'
          f' · a procesar ahora {len(pend)}')
    if args.dry_run:
        for p in pend[:20]:
            print(f'   {p["tok"]:>12} {p["base"]:<20} {(p["titulo"] or "")[:70]}')
        return
    if not pend:
        print('  nada que hacer')
        return
    EXDIR.mkdir(parents=True, exist_ok=True)

    ok = err = 0
    tin = tout = 0
    vac = Counter()
    t0 = time.time()

    def _run(p):
        return p, _procesar(p, guardar_txt=args.guardar_txt)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_run, p): p for p in pend}
        for i, fut in enumerate(as_completed(futs), 1):
            p = futs[fut]
            try:
                _, d = fut.result()
            except Exception as e:
                err += 1
                print(f'  ! {p["tok"]} ({p["base"]}): {type(e).__name__}: {str(e)[:120]}')
                continue
            _cache_path(p['tok']).write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
            ok += 1
            tin += d['_meta']['tok_in']
            tout += d['_meta']['tok_out']
            for k in d['_meta']['vacios']:
                vac[k] += 1
            if i % 20 == 0 or i == len(pend):
                print(f'  …{i}/{len(pend)} · ok {ok} err {err} · '
                      f'USD {_usd(tin, tout):.4f} · {(time.time()-t0)/60:.1f} min')

    print(f'\n  procesados {ok} · errores {err}')
    if ok:
        print(f'  tokens: in {tin:,} · out {tout:,}')
        print(f'  COSTO real de esta corrida: USD {_usd(tin, tout):.4f} '
              f'→ USD {_usd(tin, tout)/ok:.5f} por documento')
        print('  campos vacíos (de %d docs): %s' % (ok, ', '.join(
            f'{k} {v} ({v/ok:.0%})' for k, v in vac.most_common()) or 'ninguno'))


# -------------------------------------------------------------------- build
def cmd_build(args):
    """Caché por proyecto → artefacto único para S3 (metadata/articulado.json)."""
    plan = {p['tok']: p for p in construir_plan()}
    por_proyecto, por_sector = {}, defaultdict(list)
    bases, conf, vac, modelos = Counter(), Counter(), Counter(), Counter()
    n_camp = Counter()
    tin = tout = 0
    for f in sorted(EXDIR.glob('*.json')):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        tok = d.get('tok')
        if not tok:
            continue
        meta = d.pop('_meta', {})
        tin += meta.get('tok_in', 0)
        tout += meta.get('tok_out', 0)
        # el `pv` viaja al artefacto: la UI puede saber con qué prompt se extrajo
        d['pv'] = meta.get('pv')
        # qué modelo extrajo ESTE documento: el caché es mixto (nube + local) y
        # sin esto el artefacto atribuye todo al modelo de la nube. Si mañana un
        # modelo resulta flojo en algún campo, es lo que dice qué revisar.
        d['modelo'] = meta.get('model') or DEEPSEEK_MODEL
        d['vacios'] = meta.get('vacios', [])
        p = plan.get(tok) or {}
        d['titulo'] = p.get('titulo', '')
        d['anio'] = p.get('anio')
        d['legislatura'] = p.get('legislatura')
        for k in ('tb', 'id'):
            d.setdefault(k, p.get(k))
        por_proyecto[tok] = d
        bases[d.get('base')] += 1
        conf[d.get('confianza')] += 1
        modelos[d['modelo']] += 1
        for k in d['vacios']:
            vac[k] += 1
        for k in CAMPOS:
            if k not in d['vacios']:
                n_camp[k] += 1
        for s in (d.get('aplica_a') or {}).get('sectores', []):
            por_sector[s].append(tok)

    n = len(por_proyecto)
    out = {
        'v': time.strftime('%Y-%m-%d'), 'pv': PROMPT_VERSION,
        'model': modelos.most_common(1)[0][0] if modelos else DEEPSEEK_MODEL,
        'modelos': dict(modelos),
        'n': n,
        'stats': {
            'por_base': dict(bases), 'por_confianza': dict(conf),
            'por_modelo': dict(modelos),
            'campos_llenos': {k: n_camp.get(k, 0) for k in CAMPOS},
            'campos_vacios': dict(vac),
            'por_sector': {k: len(v) for k, v in sorted(por_sector.items(),
                                                        key=lambda x: -len(x[1]))},
            'tokens': {'in': tin, 'out': tout},
            'usd': round(_usd(tin, tout), 4),
        },
        'por_sector': {k: v for k, v in por_sector.items()},
        'por_proyecto': por_proyecto,
    }
    dest = DIST / 's3' / 'articulado.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    mb = dest.stat().st_size / 1024 / 1024
    print(f'→ {dest.relative_to(REPO)} · {n} proyectos · {mb:.2f} MB')
    print('  bases:', dict(bases))
    print('  modelos:', dict(modelos))
    print('  confianza:', dict(conf))
    print('  campos llenos:', {k: f'{v} ({v/max(n,1):.0%})' for k, v in n_camp.items()})
    print('  costo acumulado del corpus extraído: USD %.4f' % _usd(tin, tout))
    print('\n  subir:  aws s3 cp "%s" s3://%s/metadata/articulado.json '
          '--content-type application/json' % (dest, BUCKET))


# -------------------------------------------------------------------- stats
def cmd_plan(args):
    plan = construir_plan(refresh_s3=args.refresh_s3)
    c = Counter(p['base'] for p in plan)
    print(f'{len(plan)} proyectos en el dataset')
    for b in BASES:
        if c.get(b):
            print(f'  {b:<20} {c[b]:>6}')
    print()
    for cua in ('2026-2030', '2022-2026', '2018-2022'):
        sub = [p for p in plan if p['cuatrienio'] == cua]
        cc = Counter(p['base'] for p in sub)
        print(f'  {cua}: {len(sub):>5} → ' + ' · '.join(f'{b} {cc[b]}' for b in BASES if cc.get(b)))


def cmd_stats(args):
    plan = {p['tok']: p for p in construir_plan()}
    hechos = {}
    tin = tout = 0
    vac, bases, conf, modos = Counter(), Counter(), Counter(), Counter()
    for f in EXDIR.glob('*.json'):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        m = d.get('_meta', {})
        hechos[d.get('tok')] = d
        tin += m.get('tok_in', 0)
        tout += m.get('tok_out', 0)
        modos[m.get('modo')] += 1
        bases[d.get('base')] += 1
        conf[d.get('confianza')] += 1
        for k in m.get('vacios', []):
            vac[k] += 1
    n = len(hechos)
    print(f'extracciones en caché: {n} / {len(plan)} del dataset ({n/max(len(plan),1):.1%})')
    if not n:
        return
    print('  por base:', dict(bases))
    print('  por confianza:', dict(conf))
    print('  ventana:', dict(modos))
    print(f'  tokens in {tin:,} · out {tout:,} · USD {_usd(tin, tout):.4f} '
          f'({_usd(tin, tout)/n:.5f}/doc)')
    print('  campos vacíos:')
    for k in CAMPOS:
        v = vac.get(k, 0)
        print(f'    {k:<14} {v:>5} vacíos ({v/n:.0%}) · {n-v} con dato ({(n-v)/n:.0%})')
    for cua in ('2026-2030', '2022-2026'):
        toks = {t for t, p in plan.items() if p['cuatrienio'] == cua}
        hay = len(toks & set(hechos))
        print(f'  cobertura {cua}: {hay}/{len(toks)} ({hay/max(len(toks),1):.0%})')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')

    p = sub.add_parser('plan', help='de dónde saldría el texto de cada proyecto')
    p.add_argument('--refresh-s3', action='store_true', help='re-lista gacetas-texto/')
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser('extract', help='extracción con DeepSeek (resumible)')
    p.add_argument('--cuatrienio', help='p.ej. 2026-2030')
    p.add_argument('--legislatura', help='p.ej. 2026-2027')
    p.add_argument('--base', help='filtra por base: texto_radicado,ponencia,…')
    p.add_argument('--sin-titulo', action='store_true', help='omite los que solo tienen título')
    p.add_argument('--toks', help='coma-separado: solo estos tokens (p.ej. pdly:9981) — para benchmarks')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--guardar-txt', action='store_true', help='guarda la ventana enviada (auditoría)')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser('build', help='caché → dist/s3/articulado.json')
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser('stats', help='cobertura, costo y campos vacíos')
    p.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    if not getattr(args, 'fn', None):
        ap.print_help()
        return
    args.fn(args)


if __name__ == '__main__':
    main()
