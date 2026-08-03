"""Catálogo de lo que Caudal promete tener fresco, y de lo que la Lambda promete responder.

Este archivo es la parte OPINABLE del chequeo de salud: cada umbral está aquí,
con el razonamiento al lado, para que se discuta un número y no haya que leer
código. `check.py` no decide nada — solo aplica esto.

Tres clases de archivo, porque no todos envejecen igual:

  · diario   — los refresca `run_diario.sh` (launchd 2x/día, 08:00 y 19:30).
               La ventana más larga entre corridas es la nocturna: subida a las
               19:30 → siguiente a las 08:00 = 12,5 h. Un archivo con 26 h ya se
               saltó UNA corrida completa (aviso); con 50 h se saltó un día
               entero (error, el cliente está viendo dato viejo).
  · mensual  — la fuente misma publica una vez al mes (normativa de Presidencia).
               Pedirle frescura diaria sería inventarse una alarma.
  · manual   — se regenera cuando se cosecha (supers). No hay cron; el umbral es
               laxo y sirve para acordarse, no para despertar a nadie.
  · estatico — histórico cerrado (1990-2026). NO tiene umbral de edad: que
               `proyectos.jsonl` sea de hace tres meses es lo correcto. De estos
               solo se verifica que EXISTAN y que no lleguen truncados.

`min_bytes` es el guardarraíl contra la subida truncada: un `aws s3 cp` que se
corta a la mitad deja un objeto válido para S3 y roto para la Lambda. Los valores
son ~40-50% del tamaño real de agosto-2026, así que aguantan crecimiento y
recortes normales sin dar falso positivo.
"""

import datetime as _dt

BUCKET_PRIV = 'caudal-legislativo'          # privado · lo lee la Lambda
BUCKET_PUB = 'elecciones-2026'              # público · lo lee legislativo.html
PREFIJO_PUB = 'ricardoruiz.co/congreso-2026/output/legislativo'

LAMBDA_URL = 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com'

# Umbrales por clase, en horas. (aviso, error)
UMBRALES = {
    'diario':   (26, 50),
    'mensual':  (45 * 24, 90 * 24),
    'manual':   (120 * 24, 240 * 24),
    'estatico': (None, None),
}

# Solo se baja el archivo para leerle la fecha interna si pesa menos que esto.
# Un chequeo que se baja 27 MB de proyectos.jsonl para mirar un campo no es un
# chequeo, es tráfico. Los grandes se juzgan por LastModified de S3.
MAX_BYTES_FECHA_INTERNA = 256 * 1024


def legislatura_actual(hoy=None):
    """'2026-2027'. La legislatura se instala el 20 de julio.

    Ojo: los harvesters (`build_diario_s3.py --legislatura`) traen '2026-2027'
    HARDCODEADO como default. El 20-jul-2027 este cálculo va a pedir un archivo
    que el cron todavía no está produciendo, y el chequeo lo va a reportar como
    FALTANTE. Es el comportamiento correcto: avisa de que hay que mover el
    default del harvester, en vez de callarse.
    """
    d = hoy or _dt.date.today()
    ini = d.year if (d.month, d.day) >= (7, 20) else d.year - 1
    return f'{ini}-{ini + 1}'


def archivos(leg=None):
    """Catálogo completo. `leg` permite fijar la legislatura (tests/backfill)."""
    leg = leg or legislatura_actual()
    return [
        # ─────────── refrescados por el cron, 2x/día ───────────
        dict(bucket=BUCKET_PRIV, key='metadata/bloqueo.json', clase='diario',
             min_bytes=500_000, campo_fecha=None,
             productor='run_diario.sh · build_bloqueo_s3.py + aws s3 cp',
             consumidor='acción `bloqueo` + panel de la ficha de proyecto',
             nota='1,4 MB: no se baja para leer su campo `v`; basta LastModified.'),
        dict(bucket=BUCKET_PRIV, key=f'metadata/pl-radicados-{leg}.jsonl', clase='diario',
             min_bytes=2_000, campo_fecha=None,
             productor='run_diario.sh · harvest_diario.py + build_diario_s3.py --upload',
             consumidor='acción `radicados` (Senado) · vista "Lo último radicado"',
             nota='min_bytes bajo a propósito: al instalarse una legislatura el archivo arranca casi vacío.'),
        dict(bucket=BUCKET_PRIV, key=f'metadata/pl-radicados-camara-{leg}.jsonl', clase='diario',
             min_bytes=2_000, campo_fecha=None,
             productor='run_diario.sh · harvest_camara.py + build_diario_camara_s3.py --upload',
             consumidor='acción `radicados` (Cámara)'),
        dict(bucket=BUCKET_PRIV, key='metadata/secop-stats.json', clase='diario',
             min_bytes=15_000, campo_fecha='generado',
             productor='run_diario.sh · harvest_secop.py fetch+build + aws s3 cp',
             consumidor='acción `contratacion` (landing del pilar SECOP)',
             nota='`generado` es la hora de CÓMPUTO: delata una subida fresca de contenido viejo.'),

        # ─────────── feeds públicos que también salen del cron ───────────
        # No están en metadata/ pero los produce la misma corrida y los consume
        # una página pública (legislativo.html). Si se caen, el cliente lo ve.
        dict(bucket=BUCKET_PUB, key=f'{PREFIJO_PUB}/en-vivo.json', clase='diario',
             min_bytes=5_000, campo_fecha='actualizado',
             productor='run_diario.sh · leyes_en_vivo.py --upload (y la Lambda leyes-en-vivo)',
             consumidor='legislativo-en-vivo.html · feed "En vivo"',
             nota='Lo escriben DOS sitios (cron del Mac y Lambda). Fresco aquí no prueba que el cron corrió.'),
        dict(bucket=BUCKET_PUB, key=f'{PREFIJO_PUB}/ritmo-legislaturas.json', clase='diario',
             min_bytes=500, campo_fecha='v',
             productor='run_diario.sh · build_ritmo.py --upload',
             consumidor='legislativo.html · monitor de ritmo de radicación',
             nota='`v` es solo fecha (YYYY-MM-DD): la edad interna se mide contra su medianoche.'),

        # ─────────── periódicos, sin cron ───────────
        dict(bucket=BUCKET_PRIV, key='metadata/normativa.jsonl', clase='mensual',
             min_bytes=3_000_000,
             productor='harvest_decretos.py (manual)',
             consumidor='acción `ejecutivo`',
             nota='La fuente (Presidencia en datos.gov.co) publica MENSUAL. 45 días = ya se saltó un ciclo.'),
        dict(bucket=BUCKET_PRIV, key='metadata/normativa-stats.json', clase='mensual',
             min_bytes=3_000, campo_fecha=None,
             productor='harvest_decretos.py build (manual)',
             consumidor='acción `ejecutivo` (landing)'),
        dict(bucket=BUCKET_PRIV, key='metadata/sanciones.jsonl', clase='manual',
             min_bytes=2_000_000,
             productor='harvest_supers.py normalize + build_s3.py (manual)',
             consumidor='acción `sanciones` · pilar Regulatorio · radar del cliente'),
        dict(bucket=BUCKET_PRIV, key='metadata/sanciones-stats.json', clase='manual',
             min_bytes=4_000, campo_fecha=None,
             productor='build_s3.py (manual)',
             consumidor='acción `sanciones` (landing)'),

        # ─────────── histórico cerrado · sin umbral de edad ───────────
        dict(bucket=BUCKET_PRIV, key='metadata/proyectos.jsonl', clase='estatico',
             min_bytes=12_000_000, productor='build_dataset.py',
             consumidor='ficha de proyecto · acciones `proyecto`/`snippets`'),
        dict(bucket=BUCKET_PRIV, key='metadata/actos-legis.jsonl', clase='estatico',
             min_bytes=1_000_000, productor='build_dataset.py', consumidor='ficha de acto legislativo'),
        dict(bucket=BUCKET_PRIV, key='metadata/leyes.jsonl', clase='estatico',
             min_bytes=400_000, productor='build_dataset.py', consumidor='cruce proyecto→ley'),
        dict(bucket=BUCKET_PRIV, key='metadata/indice.json', clase='estatico',
             min_bytes=4_000_000, productor='build_dataset.py',
             consumidor='TODA búsqueda (`buscar`, `tema`, radar del cliente)'),
        dict(bucket=BUCKET_PRIV, key='metadata/stats.json', clase='estatico',
             min_bytes=2_000, productor='build_dataset.py', consumidor='acción `stats` · landing del pilar Congreso'),
        dict(bucket=BUCKET_PRIV, key='metadata/autores.json', clase='estatico',
             min_bytes=400_000, productor='normalize_autores.py', consumidor='autoría en la ficha'),
        dict(bucket=BUCKET_PRIV, key='metadata/autor-partido.json', clase='estatico',
             min_bytes=150_000, productor='build_roster.py', consumidor='bancadas por tema'),
        dict(bucket=BUCKET_PRIV, key='metadata/texto-index.json', clase='estatico',
             min_bytes=10_000_000, productor='build_texto_index.py',
             consumidor='match ◈ "en el texto" de la búsqueda'),
        dict(bucket=BUCKET_PRIV, key='metadata/bancadas.json', clase='estatico',
             min_bytes=5_000, productor='build_bancadas_s3.py', consumidor='acción `bancadas`'),
        dict(bucket=BUCKET_PRIV, key='metadata/votaciones.json', clase='estatico',
             min_bytes=5_000_000, productor='harvest_votaciones.py (Congreso Visible)',
             consumidor='aplazamientos y tally en la ficha'),
        dict(bucket=BUCKET_PRIV, key='metadata/votaciones-camara-nominal.json', clase='estatico',
             min_bytes=8_000_000, productor='build_votaciones_camara_s3.py',
             consumidor='voto nominal por proyecto (Cámara)'),
        dict(bucket=BUCKET_PRIV, key='metadata/votaciones-camara-congresista.json', clase='estatico',
             min_bytes=3_000_000, productor='build_congresista_s3.py',
             consumidor='acción `congresista` (Cámara)'),
        dict(bucket=BUCKET_PRIV, key='metadata/votaciones-senado-nominal.json', clase='estatico',
             min_bytes=5_000_000, productor='build_votaciones_senado_s3.py',
             consumidor='voto nominal por proyecto (Senado)'),
        dict(bucket=BUCKET_PRIV, key='metadata/votaciones-senado-congresista.json', clase='estatico',
             min_bytes=1_000_000, productor='build_votaciones_senado_s3.py',
             consumidor='acción `congresista` (Senado)'),
    ]


# ───────────────────────── pings a la Lambda ─────────────────────────
# Cada ping declara qué manda y qué tiene que traer de vuelta. `forma` recibe el
# JSON ya parseado y devuelve '' si está bien o el motivo de la queja.
#
# REGLA DURA: ningún ping puede costar plata. Las acciones que llaman a DeepSeek
# (`contexto`, `gaceta`, `cliente` con lectura, `tema` con lectura/expansión) van
# con la IA apagada explícitamente o no van. `tema` trae `lectura:true` y
# `expandir_ia:true` POR DEFECTO — hay que apagarlos a mano.
#
# `externa=True` marca los pings cuyo resultado depende de un tercero en vivo
# (Socrata para SECOP, Google News para medios). Si fallan, es aviso y no error:
# el pipeline nuestro puede estar perfecto y el tercero caído.

def _n(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def pings(leg=None):
    leg = leg or legislatura_actual()
    return [
        dict(accion='stats', body={'action': 'stats'}, externa=False,
             desc='agregados del histórico (landing del pilar Congreso)',
             forma=lambda d: '' if isinstance(_n(d, 'n_proyectos'), int) and _n(d, 'embudo')
             else 'falta n_proyectos/embudo'),

        dict(accion='bloqueo', body={'action': 'bloqueo'}, externa=False,
             desc='índice de bloqueo (Cámara + Senado)',
             forma=lambda d: '' if _n(d, 'p_tratado_por_posicion') and _n(d, 'senado', 'sistema')
             else 'falta p_tratado_por_posicion o el bloque senado'),

        dict(accion='radicados', body={'action': 'radicados', 'legislatura': leg}, externa=False,
             desc='lo último radicado (lo que produce el cron)',
             forma=lambda d: '' if isinstance(_n(d, 'radicados'), list) and isinstance(_n(d, 'n_camara'), int)
             else 'falta radicados[]/n_camara'),

        dict(accion='buscar', body={'action': 'buscar', 'query': 'feminicidio', 'limit': 5},
             externa=False, desc='búsqueda en el índice',
             forma=lambda d: '' if _n(d, 'n') and isinstance(_n(d, 'resultados'), list) and d['resultados']
             else 'la búsqueda de control no devolvió resultados'),

        # `tema` sin IA: ejercita caudal_core entero (embudo, supervivencia,
        # bancadas, tipología) sin gastar un peso en DeepSeek.
        dict(accion='tema', body={'action': 'tema', 'query': 'feminicidio',
                                  'lectura': False, 'expandir_ia': False},
             externa=False, desc='resumen de tema (sin lectura LLM)',
             forma=lambda d: '' if _n(d, 'resumen', 'n_intentos') else 'resumen sin n_intentos'),

        dict(accion='sanciones', body={'action': 'sanciones'}, externa=False,
             desc='pilar Regulatorio (landing)',
             forma=lambda d: '' if _n(d, 'mode') == 'stats' and _n(d, 'total')
             else 'no devolvió mode=stats con total'),

        dict(accion='ejecutivo', body={'action': 'ejecutivo'}, externa=False,
             desc='pilar Ejecutivo (landing)',
             forma=lambda d: '' if _n(d, 'mode') == 'stats' and _n(d, 'total')
             else 'no devolvió mode=stats con total'),

        dict(accion='bancadas', body={'action': 'bancadas'}, externa=False,
             desc='disciplina de bancada',
             forma=lambda d: '' if _n(d, 'camara') and _n(d, 'senado') else 'falta camara/senado'),

        dict(accion='congresista', body={'action': 'congresista', 'q': 'barguil'}, externa=False,
             desc='récord de voto de una persona',
             forma=lambda d: '' if 'encontrado' in (d or {}) else 'respuesta sin campo encontrado'),

        dict(accion='medios', body={'action': 'medios'}, externa=True, timeout=75,
             desc='pilar Medios (Google News en vivo)',
             forma=lambda d: '' if isinstance(_n(d, 'resultados'), list) else 'falta resultados[]'),

        dict(accion='contratacion', body={'action': 'contratacion', 'query': 'acueducto', 'limit': 5},
             externa=True, timeout=75, desc='pilar SECOP (Socrata en vivo)',
             forma=lambda d: '' if isinstance(_n(d, 'resultados'), list) else 'falta resultados[]'),
    ]


# La ficha de proyecto se pinchea aparte: necesita un id real, que sale del ping
# de `buscar`. Fijar un id a mano lo volvería frágil si se regenera el dataset.
PING_PROYECTO = dict(accion='proyecto', externa=False,
                     desc='ficha completa de un proyecto (id tomado de `buscar`)',
                     forma=lambda d: '' if _n(d, 'titulo') else 'ficha sin titulo')
