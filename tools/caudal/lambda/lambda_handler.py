#!/usr/bin/env python3
"""
Caudal · Lambda `caudal-analiza` (módulo de Cauce · inteligencia legislativa).

Envuelve el motor de consulta (caudal_core) sobre el dataset del bucket privado
`caudal-legislativo` y le añade una capa de síntesis por LLM. Patrón calcado de
`test-presidencial-explica`: handler + LLM por HTTP + cache S3 hash24 + CORS.

Acciones (POST JSON):
  {"action":"tema","query":"feminicidio","lectura":true}
      → resumen de supervivencia del tema (embudo, línea de intentos, autores)
        + `lectura`: síntesis LLM opcional (cacheada), tuteo neutro.
  {"action":"proyecto","id":4177}
      → ficha del proyecto + punteros de gaceta (para la fase DeepSeek de texto).
  {"action":"buscar","query":"agua","limit":25,"anio_min":2010}
      → lista cruda de coincidencias del índice.
  {"action":"bancadas"}  ·  {"action":"bancadas","camara":"senado"}
      → disciplina de bancada: cohesión (índice de Rice), % de votaciones en
        bloque, alineación con el gobierno y mayores disidentes, POR CÁMARA.
        Las dos cámaras nunca se promedian (ver `meta.no_comparable`).
  {"action":"medios","query":"reforma pensional","dias":30}
      → pilar Medios: titulares de prensa nacional y regional vía Google News RSS
        (gratis, sin key). Sin `query` → landing con el pulso político nacional.
  {"action":"cliente","perfil":{…},"lectura":true}  ·  {"action":"cliente","sector":"salud"}
      → Vista Cliente (SKU A): radar SIGA cruzando los pilares. SIEMPRE rápido:
        nunca espera al modelo. `lectura:true` ya no significa "espérame la
        síntesis" sino "prepárala": devuelve `lectura_key` para recogerla
        aparte, y ya la `lectura` si ese mismo radar se leyó antes.
  {"action":"cliente-lectura","key":"<lectura_key>"[,"solo_cache":true]}
      → el briefing del analista sobre ese radar. Sin `solo_cache` arranca la
        generación (20-51 s, se pasa del gateway a propósito); con `solo_cache`
        es un sondeo barato que responde 'lista' o 'pendiente'.
  {"action":"sucop","query":"minería","estado":"abiertas"}
      → pilar SUCOP: borradores de norma en consulta pública (DNP). El único
        pilar cuyo dato caduca: `estado_consulta` y `dias_restantes` se
        recalculan contra HOY en cada request, nunca se sirven los del JSONL.
        Sin filtros → landing con la ventana en vivo + los agregados
        estructurales precalculados.
  {"action":"contratacion","query":"comando conjunto caribe","departamento":"Atlántico"}

POR QUÉ IMPORTA · tres coordenadas (avance · impacto · político), un lente por
cliente. El eje 1 va en BANDAS, no en porcentaje: ordena mejor de lo que calibra.
  {"action":"importancia"}                                  → modelo, lentes, bandas
  {"action":"importancia","id":9934,"tb":"pdly"}             → coordenadas de uno
  {"action":"importancia","lente":"riesgo","perfil":{…}}     → ranking
      → pilar Datos abiertos y contratación: búsqueda EN VIVO sobre SECOP II
        (5,87 M contratos, Socrata $q) + total real + desglose. Sin query ni
        filtros → landing con los agregados precomputados de secop-stats.json.

MODELO POR PASO (el switch a Claude es cambiar env vars, sin tocar código):
  CAUDAL_SINTESIS_PROVIDER  deepseek | anthropic     (default deepseek)
  CAUDAL_SINTESIS_MODEL     deepseek-v4-flash | claude-sonnet-5 | …
Secretos:
  DEEPSEEK_API_KEY   (mismo secreto que las otras Lambdas)
  ANTHROPIC_API_KEY  (solo si el paso usa provider=anthropic)
  SERPER_API_KEY     (rastreo de medios · https://serper.dev, resultados Google)
Bucket:
  CAUDAL_BUCKET      default 'caudal-legislativo'
"""
import json
import unicodedata as _unicodedata
import os
import sys
import hashlib
import re
import threading
import socket
import time as _time
import urllib.request
import urllib.error
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

import boto3
import caudal_core
import empresas                        # ④ diccionario marca → tema/identidad


def _empresas_payload(emps):
    """Traducción marca → tema que la UI muestra. El usuario TIENE que ver por
    qué le salió un proyecto que no dice 'Uber' — mismo principio del aviso de
    sinónimos: nada de resultados que aparecen por magia."""
    if not emps:
        return None
    return [{'k': e['k'], 'nombre': e['nombre'], 'tipo': e['tipo'],
             'sector': e['sector'], 'nucleo': e['nucleo'],
             'contexto': e['contexto'], 'identidad': e['entidad']} for e in emps]


def _vocab_empresa(emps, ampliar=False):
    """Términos del tesauro del núcleo de estas empresas, para los pilares que
    filtran por substring sobre su blob `q`.
    OJO: el blob `q` de sanciones/normativa viene en minúsculas pero CON tildes
    ("minería"), y los términos del tesauro van sin ellas ("mineria") → hay que
    comparar los dos lados plegados con empresas._n, o no casa nunca."""
    if not emps:
        return []
    idx = {t['k']: t for t in caudal_core.SINONIMOS}
    out = []
    for k in empresas.topicos_de(emps, ampliar):
        for term in idx.get(k, {}).get('terms', []):
            t = empresas._n(term)
            if t and t not in out:
                out.append(t)
    return out

BUCKET = os.environ.get('CAUDAL_BUCKET', 'caudal-legislativo')
PROMPT_VERSION = 'v9'            # bumpear para invalidar cache de síntesis
CACHE_PREFIX = 'analisis-cache/'
HTTP_TIMEOUT = 55

_s3 = boto3.client('s3')

# --- modelo por paso (override por env var → switch sin código) -------------
STEP_MODELS = {
    'sintesis': {
        'provider': os.environ.get('CAUDAL_SINTESIS_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_SINTESIS_MODEL', 'deepseek-v4-flash'),
    },
    # la extracción de texto de gaceta (fase 3) usará este paso
    'extraccion': {
        'provider': os.environ.get('CAUDAL_EXTRACCION_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_EXTRACCION_MODEL', 'deepseek-v4-flash'),
    },
    # rastreo de medios: interpreta titulares → controversia/impopularidad
    'contexto': {
        'provider': os.environ.get('CAUDAL_CONTEXTO_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_CONTEXTO_MODEL', 'deepseek-v4-flash'),
    },
}

# --- carga de datos (cache por contenedor warm) -----------------------------
_CAUDAL = None
_FULL = None


def _get_json(key):
    obj = _s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj['Body'].read())


def _get_jsonl(key, tb):
    """Devuelve {"tb:id": registro} — pdly y pal comparten espacio de ids."""
    obj = _s3.get_object(Bucket=BUCKET, Key=key)
    out = {}
    for line in obj['Body'].read().decode('utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            out[f"{tb}:{r['id']}"] = r
    return out


def _caudal():
    """Motor con índice + roster autor→partido + índice de texto (lazy, cache warm)."""
    global _CAUDAL
    if _CAUDAL is None:
        indice = _get_json('metadata/indice.json')['proyectos']
        try:
            ap = _get_json('metadata/autor-partido.json')['autor_partido']
        except Exception:
            ap = {}
        ti, tids = {}, []
        try:
            d = _get_json('metadata/texto-index.json')
            ti, tids = d.get('index', {}), d.get('ids', [])
        except Exception:
            pass
        _CAUDAL = caudal_core.Caudal(indice=indice, autor_partido=ap, texto_index=ti, texto_ids=tids)
    return _CAUDAL


def _full():
    """Registros completos por 'tb:id' (lazy — solo cuando se pide un proyecto)."""
    global _FULL
    if _FULL is None:
        _FULL = _get_jsonl('metadata/proyectos.jsonl', 'pdly')
        _FULL.update(_get_jsonl('metadata/actos-legis.jsonl', 'pal'))
    return _FULL


# --- radicados de la legislatura viva (rastreo diario) ----------------------
# Cache warm CON TTL: el cron sube manifiestos nuevos varias veces al día, así
# que un contenedor de larga vida que cacheara para siempre se quedaría sirviendo
# radicados viejos (bug real: la vitrina mostraba 33 cuando S3 ya tenía 76).
# Guardamos (epoch, filas) por llave y re-leemos si el cache supera _RADICADOS_TTL;
# sigue evitando el hit a S3 en cada request.
_RADICADOS = {}                 # key -> (loaded_epoch, rows)
_RADICADOS_TTL = 300            # s


def _radicados_manifest(key):
    """Lee un manifiesto jsonl de radicados de S3 (cache warm con TTL). [] si no
    existe. .split('\n') y NO .splitlines(): el OCR puede meter U+0085 (NEL), que
    splitlines trata como salto de línea y parte un registro."""
    cached = _RADICADOS.get(key)
    if cached and (_time.time() - cached[0]) < _RADICADOS_TTL:
        return cached[1]
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key=key)
        rows = [json.loads(x) for x in obj['Body'].read().decode('utf-8').split('\n') if x.strip()]
    except Exception:
        # si la re-lectura falla pero ya teníamos filas, conserva lo viejo antes
        # que devolver [] (mejor rezagado que vacío).
        if cached:
            return cached[1]
        rows = []
    _RADICADOS[key] = (_time.time(), rows)
    return rows


def _radicados(leg):
    """Proyectos radicados del Senado (harvest_diario + build_diario_s3)."""
    return _radicados_manifest(f'metadata/pl-radicados-{leg}.jsonl')


def _radicados_camara(leg):
    """Proyectos radicados de la Cámara (harvest_camara + build_diario_camara_s3).
    El texto radicado es la Gaceta (born-digital); s3_pdf/s3_txt None mientras la
    Imprenta no la publica (gaceta_pendiente=true)."""
    return _radicados_manifest(f'metadata/pl-radicados-camara-{leg}.jsonl')


def _presign(key, filename=None, expires=3600):
    """URL firmada (SigV4) de vida corta para descargar UN objeto privado.
    El bucket es privado; esto le da al navegador acceso temporal sin abrirlo.
    filename fuerza el nombre de descarga (Content-Disposition)."""
    if not key:
        return None
    params = {'Bucket': BUCKET, 'Key': key}
    if filename:
        params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
    try:
        return _s3.generate_presigned_url('get_object', Params=params, ExpiresIn=expires)
    except Exception:
        return None


_BLOQUEO = None


def _bloqueo():
    """Índice de bloqueo (órdenes del día por comisión). Cache warm."""
    global _BLOQUEO
    if _BLOQUEO is None:
        try:
            _BLOQUEO = _get_json('metadata/bloqueo.json')
        except Exception:
            _BLOQUEO = {'sistema': {}, 'por_proyecto': {}}
    return _BLOQUEO


_BANCADAS = None


def _bancadas():
    """Disciplina de bancada: cohesión (Rice), alineación, disidentes y serie,
    por cámara. Chico (~14 KB), se carga entero. Cache warm."""
    global _BANCADAS
    if _BANCADAS is None:
        try:
            _BANCADAS = _get_json('metadata/bancadas.json')
        except Exception:
            _BANCADAS = {'meta': {}, 'camara': {}, 'senado': {}}
    return _BANCADAS


_ARTICULADO = None


def _articulado():
    """QUÉ DICE el articulado: extracción estructurada del texto del proyecto
    (tools/caudal/analisis/extraer_articulado.py). Cache warm.

    El índice de texto contesta "qué proyectos mencionan X"; esto contesta "qué
    cambia este proyecto": norma que modifica, obligaciones nuevas y sobre quién,
    a quién le aplica, sanciones, quién vigila y desde cuándo rige. Cada entrada
    declara su `base` (de qué documento salió) — sin eso, el dato no se muestra.
    """
    global _ARTICULADO
    if _ARTICULADO is None:
        try:
            _ARTICULADO = _get_json('metadata/articulado.json')
        except Exception:
            _ARTICULADO = {'n': 0, 'por_proyecto': {}, 'por_sector': {}, 'stats': {}}
    return _ARTICULADO


def _articulado_de(tb, pid):
    """Extracción de un proyecto, o None. La llave es la misma de _full()."""
    try:
        return _articulado().get('por_proyecto', {}).get(f'{tb}:{int(pid)}')
    except (TypeError, ValueError):
        return None


# --- POR QUÉ IMPORTA · las tres coordenadas --------------------------------
# El módulo vive en tools/caudal/importancia y viaja completo en el ZIP. Los
# submódulos usan imports planos, así que el directorio entra al path igual que
# lo hacen ellos entre sí.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'importancia'))
try:
    import ejes as _ejes                      # noqa: E402
    import features as _feat                  # noqa: E402
    from modelo import Logistica as _Logistica  # noqa: E402
except Exception:                             # pragma: no cover
    _ejes = _feat = _Logistica = None

IMPORTANCIA_LEG = '2026-2027'
_IMP = None
_VIVA = None


def _importancia():
    """Modelo del eje 1 + trayectoria de firmantes + partidos. Cache warm."""
    global _IMP
    if _IMP is None:
        if _ejes is None:
            return None
        m = _Logistica.de_dict(_get_json('metadata/importancia-modelo.json'))
        try:
            aut = _get_json('metadata/importancia-autores.json')
        except Exception:
            aut = None
        try:
            part = _get_json('metadata/autor-partido.json').get('autor_partido', {})
        except Exception:
            part = {}
        try:
            # antecedentes por parecido de título: el cluster exacto no agrupa
            # los títulos genéricos, que son los de las reformas grandes
            antec = _get_json('metadata/importancia-antecedentes.json').get('por_proyecto', {})
        except Exception:
            antec = {}
        _IMP = {'modelo': m, 'autores': aut, 'partidos': part,
                'antec': antec, 'ref': None}
    return _IMP


def _viva_recs():
    """Los proyectos de la legislatura en curso, desde el dataset completo."""
    global _VIVA
    if _VIVA is None:
        _VIVA = [r for r in _full().values()
                 if r.get('legislatura') == IMPORTANCIA_LEG]
    return _VIVA


def _imp_ref(imp):
    """Media de features de la legislatura viva: la explicación compara contra
    los pares, no contra 36 años de histórico (si no, el 'por qué' de cada
    señal termina siendo siempre el mismo)."""
    if imp.get('ref') is None:
        imp['ref'] = _feat.referencia(_viva_recs(), imp['autores'])
    return imp['ref']


def _imp_bloqueo(rec):
    """Agendamientos del proyecto. Cámara contra el índice de Cámara y Senado
    contra el de Senado: el número se reinicia por cámara y hay más de mil
    tokens que existen en los dos para proyectos distintos."""
    bl = _bloqueo()
    t = _num_token(rec.get('numero_camara'))
    if t:
        b = (bl.get('por_proyecto') or {}).get(t)
        if b:
            return b
    t = _num_token(rec.get('numero_senado'))
    if t:
        b = ((bl.get('senado') or {}).get('por_proyecto') or {}).get(t)
        if b:
            return b
    return None


def _coords_de(rec, imp, perfil=None):
    tok = f"{rec.get('tabla', 'pdly')}:{rec.get('id')}"
    return _ejes.coordenadas(rec, imp['modelo'], imp['autores'],
                             _articulado().get('por_proyecto', {}).get(tok),
                             imp['partidos'], _imp_bloqueo(rec), perfil,
                             _imp_ref(imp), imp['antec'])


def _articulado_compacto(art):
    """Lo que el Radar necesita de una extracción: suficiente para decidir si
    hay que actuar, sin arrastrar la ficha entera a cada señal."""
    if not art:
        return None
    ap = art.get('aplica_a') or {}
    obl, sanc = art.get('obligaciones') or [], art.get('sanciones') or []
    vg = art.get('vigencia') or {}
    return {
        'resumen': art.get('resumen'), 'base': art.get('base'),
        'base_txt': art.get('base_txt'), 'confianza': art.get('confianza'),
        'n_obligaciones': len(obl), 'obligaciones': obl[:2],
        'n_sanciones': len(sanc), 'sanciones': sanc[:1],
        'sectores': ap.get('sectores') or [], 'sujetos': (ap.get('sujetos') or [])[:2],
        'modifica': (art.get('modifica') or [])[:2],
        'vigilancia': (art.get('vigilancia') or [])[:2],
        'rige_desde': vg.get('rige_desde'),
    }


# El preset de sector del cliente y el vocabulario de `aplica_a.sectores` no son
# la misma lista (uno es comercial, el otro descriptivo del articulado) → puente
# explícito. Solo se mapea lo que de verdad se solapa; lo que no está aquí
# simplemente no cruza (mejor no cruzar que cruzar mal).
_SECTOR_CLIENTE_A_ARTICULADO = {
    'salud': ['salud', 'farma'],
    'contratacion': ['contratacion'],
    'financiero': ['financiero', 'seguros', 'pensiones'],
    # energía y ambiente dejaron de compartir preset: la energía se queda con su
    # cadena (incluye hidrocarburos, que el articulado etiqueta 'mineria') y el
    # expediente ambiental es su propio sector.
    'energia': ['energia', 'mineria', 'agua'],
    'ambiente': ['ambiental'],
    'educacion': ['educacion'],
    'trabajo': ['laboral', 'pensiones'],
    'consumo': ['consumo', 'retail', 'comercio'],
    'transporte': ['transporte', 'aviacion', 'logistica'],
    'agro': ['agro', 'alimentos'],
    'tic': ['tecnologia', 'telecom'],
    # 'pymes' NO entra a propósito: es un tamaño de empresa, no una actividad.
    # Puentearlo a algún sector del articulado haría que "te aplica" se
    # encendiera en todo, que es justo lo contrario de lo que el cruce sirve.
}


def _sectores_del_cliente(s, emps_vig):
    """Sectores de articulado que le importan a ESTE cliente: los de sus
    empresas vigiladas (empresas.py usa las mismas llaves) más el puente desde
    su sector comercial. Devuelve (set_sectores, {sector: [nombres vigiladas]})."""
    sect, quien = set(), {}
    for e in emps_vig or []:
        for k in _SECTOR_CLIENTE_A_ARTICULADO.get(e.get('sector'), [e.get('sector')]):
            if k:
                sect.add(k)
                quien.setdefault(k, [])
                if e['nombre'] not in quien[k]:
                    quien[k].append(e['nombre'])
    for base in (s.get('k'), s.get('sector_sanciones')):
        for k in _SECTOR_CLIENTE_A_ARTICULADO.get(base, []):
            sect.add(k)
    return sect, quien


def _enriquecer_senales_congreso(senales, sect_cliente, quien_vigila):
    """Le pega a cada señal del Congreso lo que dice su articulado, y marca las
    que le APLICAN al cliente (cruce sector del articulado × vigiladas/sector
    del perfil). Ahí está el valor: no en la ficha suelta, sino en el cruce."""
    n_art = n_aplica = 0
    for sg in senales:
        art = _articulado_de(sg.get('tb', 'pdly'), sg.get('id'))
        if not art:
            continue
        comp = _articulado_compacto(art)
        sg['articulado'] = comp
        n_art += 1
        inter = sorted(set(comp['sectores']) & sect_cliente)
        if not inter:
            continue
        n_aplica += 1
        vig = sorted({n for k in inter for n in quien_vigila.get(k, [])})
        sg['te_aplica'] = {'sectores': inter, 'vigiladas': vig}
        # la acción se re-redacta SOLO con lo que el articulado dice de verdad
        # (conteos y sujeto textual). Nada de inferir alcance.
        piezas = []
        if comp['n_obligaciones']:
            sujeto = (comp['obligaciones'][0].get('sobre_quien') or '').strip()
            piezas.append(f"crea {comp['n_obligaciones']} obligación(es) nueva(s)"
                          + (f' sobre {sujeto}' if sujeto else ''))
        if comp['n_sanciones']:
            piezas.append(f"establece {comp['n_sanciones']} sanción(es)")
        if piezas:
            det = ' y '.join(piezas)
            if sg.get('resultado') == 'EN_TRAMITE':
                sg['accion'] = (f'Te aplica y está vivo: {det}. '
                                + (sg.get('accion') or ''))[:300]
            else:
                sg['accion'] = f'Te aplica: {det}. ' + (sg.get('accion') or '')
    return n_art, n_aplica


def _num_token(num):
    """'397/2024' | '022/91' → '397/24' (llave del índice de bloqueo)."""
    import re as _re
    m = _re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', num or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


_VOTAC = None


def _votaciones():
    """Capa de outcome (Congreso Visible): debates/aplazamientos/votos. Cache warm."""
    global _VOTAC
    if _VOTAC is None:
        try:
            _VOTAC = _get_json('metadata/votaciones.json')
        except Exception:
            _VOTAC = {'por_proyecto': {}}
    return _VOTAC


_VOTAC_NOM = None


def _votaciones_nominal():
    """Voto NOMINAL de la plenaria de Cámara (por proyecto: tally + por bancada
    + lista nominal). Distinto de _votaciones() (tally de Congreso Visible).
    Cache warm."""
    global _VOTAC_NOM
    if _VOTAC_NOM is None:
        try:
            _VOTAC_NOM = _get_json('metadata/votaciones-camara-nominal.json')
        except Exception:
            _VOTAC_NOM = {'por_proyecto': {}}
    return _VOTAC_NOM


_VOTAC_CONG = None
_VOTAC_CONG_IDX = None
_VOTAC_SEN_NOM = None
_VOTAC_SEN_CONG = None
_CITAC = None


def _votaciones_senado_nominal():
    """Voto NOMINAL de la plenaria de SENADO por proyecto (API pública
    app.senado.gov.co, 2017-2026). Gemelo de _votaciones_nominal (Cámara).
    Cache warm."""
    global _VOTAC_SEN_NOM
    if _VOTAC_SEN_NOM is None:
        try:
            _VOTAC_SEN_NOM = _get_json('metadata/votaciones-senado-nominal.json')
        except Exception:
            _VOTAC_SEN_NOM = {'por_proyecto': {}}
    return _VOTAC_SEN_NOM


def _senadores():
    """Récord de voto POR SENADOR. Mismo shape que _congresistas (Cámara)."""
    global _VOTAC_SEN_CONG
    if _VOTAC_SEN_CONG is None:
        try:
            _VOTAC_SEN_CONG = _get_json('metadata/votaciones-senado-congresista.json')
        except Exception:
            _VOTAC_SEN_CONG = {'por_congresista': {}}
    return _VOTAC_SEN_CONG


def _citaciones():
    """CITACIONES DE CONTROL POLÍTICO por congresista (misma roster_key que el
    récord de voto). Fuente: órdenes del día. Cache warm."""
    global _CITAC
    if _CITAC is None:
        try:
            _CITAC = _get_json('metadata/citaciones.json')
        except Exception:
            _CITAC = {'por_congresista': {}, 'por_citado': {}, 'sistema': {}, 'meta': {}}
    return _CITAC


def _congresistas():
    """Récord de voto POR CONGRESISTA (keyed por roster_key), Cámara + Senado.
    El índice de nombres cubre las dos cámaras para que un nombre tecleado
    resuelva sin importar dónde votó la persona. Cache warm."""
    global _VOTAC_CONG, _VOTAC_CONG_IDX
    if _VOTAC_CONG is None:
        try:
            _VOTAC_CONG = _get_json('metadata/votaciones-camara-congresista.json')
        except Exception:
            _VOTAC_CONG = {'por_congresista': {}}
        # índice token → keys (para resolver un nombre tecleado/clickeado);
        # incluye las keys de Senado para que también sean resolubles.
        _VOTAC_CONG_IDX = {}
        keys = set(_VOTAC_CONG.get('por_congresista', {}))
        keys |= set(_senadores().get('por_congresista', {}))
        # …y las de citaciones: hay quien ejerce control político sin récord de
        # voto en nuestro rango (el nominal de Senado arranca en 2017). Sin esto
        # su nombre no resolvería y la ficha diría "sin datos" teniéndolos.
        keys |= set(_citaciones().get('por_congresista', {}))
        for k in keys:
            for t in k.split():
                _VOTAC_CONG_IDX.setdefault(t, set()).add(k)
    return _VOTAC_CONG


def _canon_tokens(s):
    import re as _re, unicodedata as _u
    s = _u.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return frozenset(t for t in _re.split(r'[^A-Z0-9]+', s) if len(t) > 1)


# Erratas de la fuente que rompen el match por tokens. Se listan una por una,
# con el nombre COMPLETO como llave (frozenset de tokens), nunca por apellido:
# aflojar el emparejador general le atribuiría el récord de Karina Espinosa
# Oliver a Héctor Olimpo Espinosa Oliver, o el de Eduardo Enrique Pulgar Daza a
# Yessid Enrique Pulgar Daza — personas distintas que comparten apellidos.
_ALIAS_CONGRESISTA = {
    # la API del Senado escribe "SCAF"; censo electoral y prensa, "SCAFF"
    'Nadya Georgette Blel Scaff': 'BLEL SCAF NADYA GEORGETTE',
}
_ALIAS_TOKENS = None


def _rec_congresista(key):
    """Récord de una persona fusionando las dos cámaras. Devuelve el registro de
    donde más votó como base y anexa el de la otra en `otra_camara` (hay quien fue
    representante y luego senador). None si no está en ninguna."""
    c = _congresistas().get('por_congresista', {}).get(key)
    s = _senadores().get('por_congresista', {}).get(key)
    if c and not c.get('camara'):
        c = dict(c, camara='Cámara')
    if c and s:
        base, otra = (c, s) if c.get('n_votos', 0) >= s.get('n_votos', 0) else (s, c)
        rec = dict(base, otra_camara=otra)
    else:
        rec = c or s
    # control político: aditivo. Puede existir sin récord de voto, así que
    # también sirve de base cuando no hay ninguno de los dos.
    cit = _citaciones().get('por_congresista', {}).get(key)
    if cit:
        rec = dict(rec or {'nombre': cit.get('nombre'), 'bancada': cit.get('bancada')},
                   citaciones=cit)
    return rec


def _resolver_congresista(q):
    """Devuelve (key exacto|None, [candidatos]) resolviendo q por subconjunto de
    tokens sobre las dos cámaras."""
    _congresistas()   # asegura el índice construido (Cámara + Senado)
    if _rec_congresista(q):
        return q, []
    atoks = _canon_tokens(q)
    if not atoks:
        return None, []
    global _ALIAS_TOKENS
    if _ALIAS_TOKENS is None:
        _ALIAS_TOKENS = {_canon_tokens(k): v for k, v in _ALIAS_CONGRESISTA.items()}
    ali = _ALIAS_TOKENS.get(atoks)
    if ali and _rec_congresista(ali):
        return ali, []
    cand = None
    for t in atoks:
        s = _VOTAC_CONG_IDX.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    keys = sorted(cand or [], key=lambda k: -((_rec_congresista(k) or {}).get('n_votos', 0)))
    if len(keys) == 1:
        return keys[0], []
    return None, keys[:12]


# --- pilar Regulatorio · sanciones de superintendencias ---------------------
_SANC = None
_SANC_STATS = None


def _sanciones_stats():
    """Agregados chicos precalculados para el landing del pilar. Cache warm."""
    global _SANC_STATS
    if _SANC_STATS is None:
        try:
            _SANC_STATS = _get_json('metadata/sanciones-stats.json')
        except Exception:
            _SANC_STATS = {'total': 0, 'por_sector': [], 'por_fuente': [],
                           'por_tipo': [], 'recientes': [], 'monto': {}}
    return _SANC_STATS


def _sanciones():
    """Lista slim de sanciones (lazy — solo cuando se busca). Cache warm."""
    global _SANC
    if _SANC is None:
        try:
            obj = _s3.get_object(Bucket=BUCKET, Key='metadata/sanciones.jsonl')
            # split('\n') literal — NO .splitlines(): un texto con U+0085/U+2028/
            # U+2029 partiría el JSONL en el lugar equivocado (mismo fix que
            # build_s3.py; ver mojibake de Superfinanciera).
            _SANC = [json.loads(l) for l in obj['Body'].read().decode('utf-8').split('\n') if l.strip()]
        except Exception:
            _SANC = []
    return _SANC


_EJEC = None
_EJEC_STATS = None


def _ejecutivo_stats():
    """Agregados del pilar Ejecutivo (decretos/normativa Presidencia). Cache warm."""
    global _EJEC_STATS
    if _EJEC_STATS is None:
        try:
            _EJEC_STATS = _get_json('metadata/normativa-stats.json')
        except Exception:
            _EJEC_STATS = {'total': 0, 'por_tipo': [], 'por_anio': {},
                           'recientes': [], 'rango_fechas': ['', ''], 'fuente': {}}
    return _EJEC_STATS


def _ejecutivo():
    """Lista slim de normativa del Ejecutivo (lazy — solo al buscar). Cache warm."""
    global _EJEC
    if _EJEC is None:
        try:
            obj = _s3.get_object(Bucket=BUCKET, Key='metadata/normativa.jsonl')
            _EJEC = [json.loads(l) for l in obj['Body'].read().decode('utf-8').split('\n') if l.strip()]
        except Exception:
            _EJEC = []
    return _EJEC


# --- pilar SUCOP (borradores de norma en consulta pública · DNP) ------------
# El único pilar de Caudal cuyo dato CADUCA. Todo lo demás acá es histórico y no
# envejece; un borrador cuya ventana de comentarios cerró es arqueología, y uno
# que cierra en cinco días es lo más urgente que Caudal produce.
#
# De ahí las dos decisiones de este bloque, que lo apartan del patrón de los
# otros pilares:
#   · `estado_consulta` y `dias_restantes` se RECALCULAN en cada request contra
#     la fecha de hoy. Los del JSONL son del día en que corrió el harvester y
#     mienten por definición al día siguiente. `fecha_inicio`/`fecha_fin` viajan
#     crudas justamente para que esto sea posible (ver sucop/README.md).
#   · el landing NO sale entero de stats.json. Los agregados estructurales
#     (por_tipo, por_entidad, por_sector, por_anio) no envejecen y se sirven
#     precalculados; pero la VENTANA — cuántas abiertas, cuántas cierran ya — se
#     recuenta en vivo sobre el JSONL. Servir ahí un `abiertos_ahora` de hace una
#     semana sería publicar el bug en la portada del pilar.
import datetime

SUCOP_DIAS_CIERRA_PRONTO = 7          # mismo umbral del harvester
# Colombia no tiene horario de verano, así que un offset fijo es exacto y no
# depende de que la imagen de Lambda traiga tzdata. En UTC puro, entre las 00:00
# y las 05:00 el pilar adelantaría el vencimiento de una consulta medio día.
SUCOP_TZ = datetime.timezone(datetime.timedelta(hours=-5))
# Lo que el usuario puede pedir. 'abiertas' es un atajo (abierta + cierra_pronto)
# porque "lo que todavía puedo comentar" es la pregunta real del cliente.
SUCOP_ESTADOS = ('abierta', 'cierra_pronto', 'cerrada', 'por_abrir',
                 'planeacion', 'cancelada', 'sin_fechas')

_SUCOP = None
_SUCOP_STATS = None


def _sucop_hoy():
    return datetime.datetime.now(SUCOP_TZ).date()


def _sucop_estado_consulta(ini, fin, estado, hoy):
    """¿Todavía se puede comentar? Puerto literal de `estado_consulta_de` de
    tools/caudal/sucop/harvest_sucop.py — si cambia allá, cambia acá.

    Decide por la FECHA (que es el hecho); el estado que declara la fuente solo
    desempata cuando no hay ventana publicada. Devuelve (estado, dias_restantes).
    """
    if (estado or '').strip().lower() == 'cancelada':      # desistida: no abre
        return 'cancelada', None
    if fin:
        try:
            dias = (datetime.date.fromisoformat(fin) - hoy).days
        except ValueError:
            return 'sin_fechas', None
        if dias < 0:
            return 'cerrada', dias
        try:
            arranca = bool(ini) and datetime.date.fromisoformat(ini) > hoy
        except ValueError:
            arranca = False
        if arranca:
            return 'por_abrir', dias
        return ('cierra_pronto' if dias <= SUCOP_DIAS_CIERRA_PRONTO else 'abierta'), dias
    if estado in ('Planeación de la consulta', 'Aprobación de la consulta pública'):
        return 'planeacion', None
    return 'sin_fechas', None


def _sucop_stats():
    """Agregados estructurales del pilar (los que NO caducan). Cache warm."""
    global _SUCOP_STATS
    if _SUCOP_STATS is None:
        try:
            _SUCOP_STATS = _get_json('metadata/sucop-stats.json')
        except Exception:
            _SUCOP_STATS = {'total': 0, 'por_tipo': {}, 'por_tipo_norma': [],
                            'por_sector': [], 'por_entidad': [], 'por_anio': {},
                            'rango_fechas': ['', ''], 'fuente': {}}
    return _SUCOP_STATS


def _sucop():
    """Procesos de SUCOP, con la ventana ya recalculada a HOY. Cache warm.

    El recálculo va acá y no en cada acción para que ninguna ruta pueda leer por
    descuido el `estado_consulta` viejo del JSONL. El caché se invalida solo al
    cambiar de día: un contenedor warm que sobreviva a la medianoche serviría un
    'cierra_pronto' vencido, que es exactamente el error que este pilar no puede
    cometer.
    """
    global _SUCOP
    hoy = _sucop_hoy()
    if _SUCOP is not None and _SUCOP[0] == hoy:
        return _SUCOP[1]
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key='metadata/sucop.jsonl')
        recs = [json.loads(l) for l in obj['Body'].read().decode('utf-8').split('\n') if l.strip()]
    except Exception:
        recs = []
    for r in recs:
        ec, dias = _sucop_estado_consulta(r.get('fecha_inicio'), r.get('fecha_fin'),
                                          r.get('estado'), hoy)
        r['estado_consulta'] = ec
        r['dias_restantes'] = dias
    _SUCOP = (hoy, recs)
    return recs


def _sucop_dias_desde_epoca(f):
    """'2026-08-19' -> entero comparable. 0 si no hay fecha."""
    try:
        return datetime.date.fromisoformat(f).toordinal()
    except (TypeError, ValueError):
        return 0


def _sucop_orden(r):
    """Lo urgente primero: lo que sigue abierto, ordenado por lo que menos tiempo
    le queda. Después lo que aún no abre, y de último lo cerrado por recencia —
    una consulta vencida es archivo, no una alerta."""
    ec = r.get('estado_consulta')
    dias = r.get('dias_restantes')
    if ec in ('cierra_pronto', 'abierta'):
        return (0, dias if dias is not None else 9999)
    if ec == 'por_abrir':
        return (1, dias if dias is not None else 9999)
    # el resto (cerrada, planeación, sin fechas): lo más nuevo arriba
    return (2, -_sucop_dias_desde_epoca(r.get('fecha_fin') or r.get('creado')))


def _sucop_ventana(recs):
    """El recuento que caduca, contado en vivo."""
    c = Counter(r.get('estado_consulta') for r in recs)
    return {
        'abiertas': c.get('abierta', 0) + c.get('cierra_pronto', 0),
        'cierran_en_7_dias': c.get('cierra_pronto', 0),
        'por_abrir': c.get('por_abrir', 0),
        'cerradas': c.get('cerrada', 0),
        'en_planeacion': c.get('planeacion', 0),
        'por_estado': {k: c.get(k, 0) for k in SUCOP_ESTADOS if c.get(k, 0)},
    }


def _sucop_card(r):
    """Registro para la UI, sin el blob de búsqueda."""
    return {k: v for k, v in r.items() if k != 'q'}


# --- pilar Datos abiertos y contratación (SECOP II · búsqueda en vivo) ------
# Este pilar NO carga su dataset en memoria como los otros: SECOP II son 5,87 M
# filas. El landing sale de agregados precomputados (metadata/secop-stats.json,
# que emite tools/caudal/secop/harvest_secop.py 1x/día) y la búsqueda va EN VIVO
# contra Socrata. Frontera medida (ver tools/caudal/secop/README.md):
#   $q   → índice full-text: admite agregar (count/sum/group)   ~1-3 s
#   like → escaneo de las 5,87 M filas: NUNCA con agregados     >65 s (timeout)
SECOP_RESOURCE = os.environ.get('SECOP_RESOURCE', 'jbjy-vk9h')
SECOP_URL = f'https://www.datos.gov.co/resource/{SECOP_RESOURCE}.json'
SECOP_TIMEOUT = 25
SECOP_STATS_KEY = 'metadata/secop-stats.json'

# filtros exactos → columna. Solo dimensiones CERRADAS (las mismas de los chips)
# más entidad/nit, que son los filtros que de verdad se piden. Nada de texto libre.
SECOP_FILTROS = {
    'departamento': 'departamento',
    'estado': 'estado_contrato',
    'modalidad': 'modalidad_de_contratacion',
    'tipo': 'tipo_de_contrato',
    'sector': 'sector',
    'orden_entidad': 'orden',
    'entidad': 'nombre_entidad',
    'nit': 'nit_entidad',
}
# Columnas de display + probe del badge "matchea por". Las columnas PII del
# dataset (cédulas, domicilio del representante legal, supervisor, cuenta
# bancaria — ver `columnas_pii_excluidas` del stats) NO van acá: $q las matchea
# igual, pero mostrarlas es otra cosa (mismo criterio del slim de supers).
SECOP_SELECT = [
    'id_contrato', 'nombre_entidad', 'nit_entidad', 'proveedor_adjudicado',
    'objeto_del_contrato', 'descripcion_del_proceso', 'valor_del_contrato',
    'departamento', 'ciudad', 'estado_contrato', 'modalidad_de_contratacion',
    'tipo_de_contrato', 'sector', 'rama', 'orden', 'descripcion_documentos_tipo',
    'referencia_del_contrato', 'codigo_de_categoria_principal',
    'fecha_de_firma', 'fecha_de_fin_del_contrato', 'urlproceso',
]
SECOP_ORDENES = {'reciente': 'fecha_de_firma DESC', 'valor': 'valor_del_contrato DESC'}
SECOP_MATCH_FALLBACK = [
    {'campo': 'objeto_del_contrato', 'etiqueta': 'Objeto'},
    {'campo': 'nombre_entidad', 'etiqueta': 'Entidad'},
    {'campo': 'proveedor_adjudicado', 'etiqueta': 'Proveedor'},
]

_SECOP_STATS = None


def _secop_stats():
    """Agregados del pilar (landing + chips + columnas_match). Cache warm."""
    global _SECOP_STATS
    if _SECOP_STATS is None:
        try:
            _SECOP_STATS = _get_json(SECOP_STATS_KEY)
        except Exception:
            _SECOP_STATS = {'total': {}, 'por_anio': [], 'por_departamento': [],
                            'por_sector': [], 'por_modalidad': [], 'por_tipo': [],
                            'por_estado': [], 'chips': [], 'columnas_match': [],
                            'top_entidades_valor': [], 'top_entidades_n': [],
                            'top_categorias': [], 'fuente': {}}
    return _SECOP_STATS


def _secop_get(params, timeout=SECOP_TIMEOUT):
    url = SECOP_URL + '?' + urllib.parse.urlencode(params)
    headers = {'Accept': 'application/json'}
    tok = os.environ.get('SOCRATA_APP_TOKEN', '')
    if tok:
        headers['X-App-Token'] = tok       # sube el rate limit (evita throttling)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _secop_norm(s):
    s = (s or '').lower()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n')):
        s = s.replace(a, b)
    return ' '.join(s.split())


def _secop_lit(v):
    return str(v).replace("'", "''")           # escape SoQL


def _secop_where(filtros):
    conds = []
    for k, col in SECOP_FILTROS.items():
        v = (filtros.get(k) or '').strip()
        if v:
            conds.append(f"{col}='{_secop_lit(v)}'")
    anio = str(filtros.get('anio') or '').strip()
    if anio.isdigit():
        conds.append(f'date_extract_y(fecha_de_firma)={int(anio)}')
    return ' AND '.join(conds)


def _secop_row(r, terms, cols):
    url = r.get('urlproceso')
    if isinstance(url, dict):
        url = url.get('url')
    try:
        valor = round(float(r.get('valor_del_contrato') or 0))
    except Exception:
        valor = 0
    # badge "matchea por": la PRIMERA columna de columnas_match (orden de
    # prioridad) cuya celda contiene el término. Explica por qué $q trajo esta
    # fila aunque el objeto no diga nada del término buscado.
    match = None
    if terms:
        for c in cols:
            cell = _secop_norm(r.get(c['campo']))
            if cell and all(t in cell for t in terms):
                match = c['etiqueta']
                break
    return {
        'id': r.get('id_contrato'),
        # ② el número que el cliente tecleó: si buscó por radicado tiene que
        # poder confirmar que la fila que ve es la suya.
        'referencia': r.get('referencia_del_contrato'),
        'entidad': r.get('nombre_entidad'), 'nit': r.get('nit_entidad'),
        'proveedor': r.get('proveedor_adjudicado'),
        'objeto': ' '.join((r.get('objeto_del_contrato') or '').split()),
        'valor': valor,
        'departamento': r.get('departamento'), 'ciudad': r.get('ciudad'),
        'estado': r.get('estado_contrato'), 'modalidad': r.get('modalidad_de_contratacion'),
        'tipo': r.get('tipo_de_contrato'), 'sector': r.get('sector'),
        'categoria': r.get('codigo_de_categoria_principal'),
        'fecha': (r.get('fecha_de_firma') or '')[:10],
        'fecha_fin': (r.get('fecha_de_fin_del_contrato') or '')[:10],
        'url': url, 'match': match,
    }


def _secop_chips(query, k=3):
    """Chips de dimensión que matchean lo que el usuario escribió: ofrecen el
    filtro EXACTO (sin ruido) antes de mandar todo a $q. Sin queries extra."""
    q = _secop_norm(query)
    if not q or len(q) < 3:
        return []
    hits = [c for c in (_secop_stats().get('chips') or [])
            if q in c.get('norm', '') or c.get('norm', '') in q]
    hits.sort(key=lambda c: c.get('n', 0), reverse=True)
    return hits[:k]


# ④ identidad de empresa en SECOP · el puente del diccionario a este pilar.
# En Congreso y Ejecutivo el diccionario traduce marca → TEMA (el Estado legisla
# actividades). En Contratación aplica la otra cara: acá la empresa SÍ aparece
# con nombre propio, como PROVEEDOR. Pero `$q=uber` trae 210 contratos de gente
# que se llama Uber, y filtrar las filas con `casa_registro` no arregla nada
# (medido: 42/42 falsos). Ver la nota larga de `es_razon_social` en empresas.py.
#
# El camino, en dos pasos y SIN `like` en ninguno (restricción dura del pilar):
#   1. DESCUBRIR nombres: group-by sobre $q (indexado, ~1 s) por proveedor y por
#      entidad, para la consulta y sus alias — '$q=comcel' encuentra la razón
#      social de Claro que '$q=claro' hunde entre 1.859 apellidos.
#   2. FILTRAR por igualdad: $where con `in (…)` sobre los nombres que pasaron
#      el gate. Es un filtro exacto sobre columna indexada → rápido, y da el
#      TOTAL REAL de la empresa (no el universo ruidoso de $q).
SECOP_DESC_LIMIT = 2000        # nombres distintos que revisa el descubrimiento
SECOP_DESC_TERMS = 3           # consulta + 2 alias (cada término = 2 queries)
SECOP_IN_MAX = 40              # nombres por lado en el `in (…)` (tope de URL)


def _secop_descubrir(query, emps, terms=None):
    """Nombres de proveedor/entidad del universo $q que SON la empresa.

    `terms` explícito lo usa el Radar del perfil de cliente, que descubre las
    razones sociales de VARIAS vigiladas en una sola ronda (un alias por
    empresa) en vez de una ronda por empresa — el gate (`razon_social_any`) ya
    recibe la lista completa, así que la precisión no cambia.
    """
    if terms is None:
        terms = [query]
        for e in emps:
            for a in e['alias'] + e['entidad']:
                if a not in terms and len(terms) < SECOP_DESC_TERMS:
                    terms.append(a)
    cols = ('proveedor_adjudicado', 'nombre_entidad')
    vistos = {c: {} for c in cols}
    jobs = [(t, c) for t in terms for c in cols]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_secop_get, {'$q': t, '$select': f'{c},count(1) as n',
                                         '$group': c, '$order': 'n DESC',
                                         '$limit': SECOP_DESC_LIMIT}): c
                for t, c in jobs}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                filas = fut.result()
            except Exception as e:
                print(f'[secop] descubrimiento {c} FAIL: {type(e).__name__}: {e}')
                continue
            for r in filas:
                nm = (r.get(c) or '').strip()
                if nm:
                    vistos[c][nm] = max(vistos[c].get(nm, 0), int(r.get('n') or 0))
    # proveedor: gate ESTRICTO (acá viven las personas naturales).
    # entidad: gate por prefijo (entidades públicas; 'SENA REGIONAL VALLE …' es
    # el SENA comprando, y sobre esta columna no hay cédulas que se cuelen).
    prov = sorted(((n, c) for n, c in vistos['proveedor_adjudicado'].items()
                   if empresas.razon_social_any(emps, n)), key=lambda x: -x[1])
    ent = sorted(((n, c) for n, c in vistos['nombre_entidad'].items()
                  if empresas.marca_lidera_any(emps, n)), key=lambda x: -x[1])
    # lo que el gate tumbó, para que se pueda auditar sin adivinar
    desc = sorted(((n, c) for n, c in vistos['proveedor_adjudicado'].items()
                   if empresas.casa_registro_any(emps, n)
                   and not empresas.razon_social_any(emps, n)), key=lambda x: -x[1])
    return prov, ent, desc


def _secop_in(col, nombres):
    lit = ','.join("'" + _secop_lit(n) + "'" for n, _ in nombres[:SECOP_IN_MAX])
    return f'{col} in ({lit})'


def _contratacion_empresa(body, query, emps, filtros, where_base):
    """Búsqueda por IDENTIDAD de empresa: los contratos que son DE la empresa,
    no los que mencionan su nombre. Devuelve None si el diccionario no encuentra
    ninguna razón social → el caller cae a la búsqueda normal por $q."""
    prov, ent, descartados = _secop_descubrir(query, emps)
    if not prov and not ent:
        # ⚠️ Sin razón social del lado CONTRATO puede haber procesos igual: una
        # entidad puede casi no contratar por SECOP II y sí publicar procesos
        # (Findeter, 5.089). Por eso viajan las listas vacías, no un corte seco.
        return {'sin_contratos': True, 'descartados': descartados,
                '_prov': prov, '_ent': ent,
                'empresas': _empresas_payload(emps)}
    conds = []
    if prov:
        conds.append(_secop_in('proveedor_adjudicado', prov))
    if ent:
        conds.append(_secop_in('nombre_entidad', ent))
    w = '(' + ' OR '.join(conds) + ')'
    if where_base:
        w += ' AND ' + where_base
    limit = max(1, min(int(body.get('limit') or 50), 200))
    orden = SECOP_ORDENES.get(body.get('orden') or 'reciente', SECOP_ORDENES['reciente'])
    p_filas = {'$select': ','.join(SECOP_SELECT), '$order': orden, '$limit': limit,
               '$where': w + (' AND fecha_de_firma IS NOT NULL'
                              if orden.startswith('fecha_de_firma') else '')}
    p_total = {'$select': 'count(1) as n,sum(valor_del_contrato) as v', '$where': w}
    p_dep = {'$where': w, '$select': 'departamento,count(1) as n',
             '$group': 'departamento', '$order': 'n DESC', '$limit': 12}
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_filas, f_total, f_dep = (pool.submit(_secop_get, p)
                                   for p in (p_filas, p_total, p_dep))
        try:
            filas = f_filas.result()
        except Exception as e:
            print(f'[secop] empresa/filas FAIL: {type(e).__name__}: {e}')
            return {'error_transitorio': True}
        total = dep = None
        for fut, name in ((f_total, 'total'), (f_dep, 'dep')):
            try:
                r = fut.result()
            except Exception as e:
                print(f'[secop] empresa/{name} FAIL: {type(e).__name__}: {e}')
                continue
            total, dep = (r, dep) if name == 'total' else (total, r)
    tot = None
    if total:
        try:
            tot = {'contratos': int(total[0].get('n') or 0),
                   'valor_cop': round(float(total[0].get('v') or 0))}
        except Exception:
            tot = None
    cols = _secop_stats().get('columnas_match') or SECOP_MATCH_FALLBACK
    return {
        'proveedores': [{'nombre': n, 'n': c} for n, c in prov[:SECOP_IN_MAX]],
        'entidades': [{'nombre': n, 'n': c} for n, c in ent[:SECOP_IN_MAX]],
        'descartados': [{'nombre': n, 'n': c} for n, c in descartados[:12]],
        'n_descartados': len(descartados),
        'truncado': len(prov) > SECOP_IN_MAX or len(ent) > SECOP_IN_MAX,
        'empresas': _empresas_payload(emps),
        'total': tot, 'filas': filas, 'dep': dep, 'cols': cols,
        '_prov': prov, '_ent': ent,
    }


# --- ② búsqueda por IDENTIFICADOR · ③ el campo `adjudicado` ------------------
# Aprendizaje del caso PAF-MENIES-O-134-2024 (ago-2026), todo medido contra
# Socrata, no supuesto:
#
#  (a) Este pilar solo consulta CONTRATOS (jbjy-vk9h, 5,97 M filas). Los
#      PROCESOS (p6dx-8zbt, 9,02 M) son la otra mitad del universo y llegan
#      ANTES: en ese caso el proceso se publicó el 13-nov-2024 y el contrato se
#      firmó el 24-ene-2025 — 72 días en los que todavía se podía incidir. Y hay
#      contratos que NUNCA existen como contrato electrónico: los de régimen
#      especial de patrimonios autónomos (Findeter, Fiduprevisora, Fiduagraria)
#      viven solo como proceso. Régimen especial son 3,67 M procesos contra
#      849 K contratos de esa modalidad. Corolario para la UI: un `$q` sin
#      resultados NO significa "no existe", significa "no está en ESTE dataset".
#
#  (b) El cliente llega con un NÚMERO en la mano ("¿qué pasó con este
#      contrato?") y hasta acá todo iba por `$q` full-text, que depende de cómo
#      tokenice un identificador con guiones. Las sondas por igualdad son
#      baratas (medido: 0,50-0,63 s cada una) y corren en paralelo, así que esto
#      es ADITIVO: si no encuentra nada no cuesta nada ni toca la búsqueda
#      normal, y por eso el detector puede ser permisivo sin riesgo.
#
# ⚠️⚠️ La llave de join proceso→contrato es `id_del_portafolio` (CO1.BDOS.*) →
#      `proceso_de_compra`. NO es `id_del_proceso` (CO1.REQ.*): usar esa
#      devuelve vacío SIEMPRE y hace creer que el contrato no existe.
# ⚠️ `referencia_del_contrato` NO es única — medido: 'CPS-3548-2022' son dos
#      contratos de entidades distintas. Por eso se devuelven todas las
#      coincidencias con bandera `ambiguo`, nunca "el" contrato.
SECOP_PROC_RESOURCE = os.environ.get('SECOP_PROC_RESOURCE', 'p6dx-8zbt')
SECOP_PROC_URL = f'https://www.datos.gov.co/resource/{SECOP_PROC_RESOURCE}.json'
SECOP_IDENT_TIMEOUT = 10
SECOP_IDENT_MAX = 12               # filas por sonda (una referencia repetida)
SECOP_ADJ_MAX = 3                  # procesos a los que se les resuelve el cruce

SECOP_NOTICE_RE = re.compile(r'(CO1\.NTC\.\d+)', re.I)
SECOP_ID_RE = re.compile(r'^CO1\.[A-Z]{2,8}\.?\s?\d+$', re.I)
SECOP_REF_DE_RE = re.compile(r'^\d{1,6}\s+DE\s+\d{4}$', re.I)
SECOP_NOTICE_BASE = ('https://community.secop.gov.co/Public/Tendering/'
                     'OpportunityDetail/Index?noticeUID=')
SECOP_NOTICE_SUF = '&isFromPublicArea=True&isModal=true&asPopupView=true'

SECOP_PROC_SELECT = [
    'id_del_proceso', 'id_del_portafolio', 'referencia_del_proceso', 'entidad',
    'nit_entidad', 'nombre_del_procedimiento', 'descripci_n_del_procedimiento',
    'precio_base', 'modalidad_de_contratacion', 'fase', 'estado_del_procedimiento',
    'fecha_de_publicacion_del', 'departamento_entidad', 'ciudad_entidad',
    'duracion', 'unidad_de_duracion', 'adjudicado', 'nombre_del_proveedor',
    'valor_total_adjudicacion', 'tipo_de_contrato', 'urlproceso',
]

# ③ El texto que acompaña SIEMPRE a un proceso. No es un disclaimer decorativo:
# es la diferencia entre informar y afirmar algo falso.
SECOP_ADJ_NOTA = (
    'El campo `adjudicado` del dataset de procesos no es confiable en régimen '
    'especial. Medido ago-2026 sobre 200 procesos marcados «No» con más de un '
    'año de publicados: el 38% SÍ tenía contrato firmado. Findeter reporta 0 '
    'adjudicaciones en sus 5.089 procesos y Fiduprevisora 2,3%. Por eso acá el '
    'estado se resuelve cruzando contra el dataset de contratos, y cuando ese '
    'cruce no encuentra nada se dice «la fuente no lo informa», nunca «no '
    'adjudicado».')

SECOP_ADJ_ETIQUETA = {
    'adjudicado': 'Adjudicado · hay contrato firmado',
    'adjudicado_sin_contrato': 'Adjudicado según la fuente · sin contrato electrónico publicado',
    'no_informa': 'La fuente no lo informa',
}


# ⚠️ Socrata ANÓNIMO castiga las ráfagas. Medido ago-2026 desde una sola IP:
# 4, 8 y 16 consultas en paralelo devolvieron 100% de error, y la IP se
# recupera sola al esperar ~20 s. Al sumar los procesos, una búsqueda por
# empresa pasó de 9 a 16 consultas → el pilar entero se volvía frágil.
# El tope no es una optimización: es lo que hace que la respuesta exista.
# Con `SOCRATA_APP_TOKEN` seteada (pendiente, ver README) se puede subir.
SECOP_MAX_PARALELO = int(os.environ.get('SECOP_MAX_PARALELO', '6'))
_SECOP_SEM = threading.Semaphore(SECOP_MAX_PARALELO)
SECOP_REINTENTO_ESPERA = 1.2


def _secop_get_res(resource, params, timeout=SECOP_TIMEOUT):
    """`_secop_get` para cualquier dataset (contratos o procesos).

    El semáforo se toma SOLO durante la llamada HTTP, nunca mientras se espera
    a otras tareas: por eso los pools anidados de este módulo no se traban."""
    url = f'https://www.datos.gov.co/resource/{resource}.json?' + urllib.parse.urlencode(params)
    headers = {'Accept': 'application/json'}
    tok = os.environ.get('SOCRATA_APP_TOKEN', '')
    if tok:
        headers['X-App-Token'] = tok
    req = urllib.request.Request(url, headers=headers)
    for intento in (0, 1):
        try:
            with _SECOP_SEM:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # Socrata presenta el throttle de varias formas — medido en
            # CloudWatch ago-2026: 429, 403 y también 500/503 en ráfaga. Todos
            # son transitorios y se reintentan UNA vez; el resto sube tal cual.
            if intento == 0 and e.code in (429, 403, 500, 502, 503, 504):
                _time.sleep(SECOP_REINTENTO_ESPERA)
                continue
            raise
        except (TimeoutError, socket.timeout) as e:
            if intento == 0:
                continue                   # un timeout suelto también se reintenta
            raise


def _secop_es_identificador(q):
    """¿La consulta parece un radicado y no una frase? Permisivo a propósito:
    un falso positivo cuesta una sonda de 0,6 s que devuelve vacío."""
    q = (q or '').strip()
    if not (4 <= len(q) <= 120) or len(q.split()) > 6:
        return False
    if not any(c.isdigit() for c in q):
        return False                       # 'reforma pensional' no es un radicado
    if SECOP_NOTICE_RE.search(q) or SECOP_ID_RE.match(q) or SECOP_REF_DE_RE.match(q):
        return True
    # un radicado trae separador pegado: PAF-MENIES-O-134-2024 · CPS-3548-2022
    return bool(re.search(r'\w[-/.]\w', q))


def _secop_ident_sondas(q):
    """(dataset, columna, valor) a probar por IGUALDAD. Máximo 4."""
    q = (q or '').strip()
    sondas = []

    def add(res, col, val):
        t = (res, col, val)
        if val and t not in sondas:
            sondas.append(t)

    m = SECOP_NOTICE_RE.search(q)
    if m:                                  # URL de SECOP pegada, o noticeUID suelto
        base = SECOP_NOTICE_BASE + m.group(1).upper()
        add(SECOP_PROC_RESOURCE, 'urlproceso.url', base)
        add(SECOP_RESOURCE, 'urlproceso.url', base + SECOP_NOTICE_SUF)
        return sondas
    if SECOP_ID_RE.match(q):               # un CO1.* nunca es una referencia
        u = q.upper()
        add(SECOP_RESOURCE, 'id_contrato', u)
        add(SECOP_RESOURCE, 'proceso_de_compra', u)
        add(SECOP_PROC_RESOURCE, 'id_del_proceso', u)
        add(SECOP_PROC_RESOURCE, 'id_del_portafolio', u)
        return sondas
    for v in (q, q.upper()):               # la referencia se escribe en mayúsculas
        add(SECOP_RESOURCE, 'referencia_del_contrato', v)
        add(SECOP_PROC_RESOURCE, 'referencia_del_proceso', v)
    return sondas


def _secop_proc_row(r):
    url = r.get('urlproceso')
    if isinstance(url, dict):
        url = url.get('url')
    try:
        base = round(float(r.get('precio_base') or 0))
    except Exception:
        base = 0
    dur = ' '.join(x for x in (str(r.get('duracion') or '').strip(),
                               (r.get('unidad_de_duracion') or '').strip()) if x)
    return {
        'id': r.get('id_del_proceso'), 'portafolio': r.get('id_del_portafolio'),
        'referencia': r.get('referencia_del_proceso'),
        'entidad': r.get('entidad'), 'nit': r.get('nit_entidad'),
        'objeto': ' '.join((r.get('nombre_del_procedimiento')
                            or r.get('descripci_n_del_procedimiento') or '').split()),
        'valor_base': base, 'modalidad': r.get('modalidad_de_contratacion'),
        'fase': r.get('fase'), 'estado': r.get('estado_del_procedimiento'),
        'fecha_publicacion': (r.get('fecha_de_publicacion_del') or '')[:10],
        'departamento': r.get('departamento_entidad'), 'ciudad': r.get('ciudad_entidad'),
        'duracion': dur or None, 'tipo': r.get('tipo_de_contrato'), 'url': url,
        # el proveedor explica por qué salió la fila cuando la búsqueda es por
        # empresa (la entidad es el comprador). 'No Definido' es el marcador de
        # nulo de la fuente en el 88,9% de las filas → se omite, no se muestra.
        'proveedor': (None if (r.get('nombre_del_proveedor') or '').strip() in
                      ('', SECOP_PROC_PROV_NULO) else r.get('nombre_del_proveedor')),
        '_campo_adjudicado': r.get('adjudicado'),
    }


def _secop_adjudicacion(proc):
    """③ Resuelve el estado real cruzando por `id_del_portafolio` →
    `proceso_de_compra`. NUNCA repite el campo `adjudicado` como si fuera
    verdad: si el cruce no encuentra contrato, el estado es 'no_informa'."""
    campo = (proc.get('_campo_adjudicado') or '').strip() or None
    out = {'campo_fuente': campo, 'contratos': [], 'n_contratos': 0,
           'campo_desmentido': False, 'nota': SECOP_ADJ_NOTA}
    port = proc.get('portafolio')
    if not port:
        out['estado'] = 'no_informa'
        out['etiqueta'] = SECOP_ADJ_ETIQUETA['no_informa']
        return out
    try:
        filas = _secop_get_res(SECOP_RESOURCE, {
            '$select': ','.join(SECOP_SELECT),
            '$where': f"proceso_de_compra='{_secop_lit(port)}'",
            '$order': 'fecha_de_firma DESC', '$limit': SECOP_IDENT_MAX,
        }, timeout=SECOP_IDENT_TIMEOUT)
    except Exception as e:
        print(f'[secop] cruce adjudicacion {port} FAIL: {type(e).__name__}: {e}')
        out['estado'] = 'no_informa'
        out['etiqueta'] = SECOP_ADJ_ETIQUETA['no_informa']
        out['cruce_fallo'] = True
        return out
    if filas:
        out['estado'] = 'adjudicado'
        out['contratos'] = [_secop_row(r, [], []) for r in filas]
        out['n_contratos'] = len(filas)
        # el caso PAF-MENIES: la fuente dice 'No' y hay contrato firmado
        out['campo_desmentido'] = (campo or '').lower().startswith('n')
    elif (campo or '').lower().startswith('s'):
        out['estado'] = 'adjudicado_sin_contrato'
    else:
        out['estado'] = 'no_informa'
    out['etiqueta'] = SECOP_ADJ_ETIQUETA[out['estado']]
    return out


def _secop_identificador(query):
    """② Camino explícito por radicado. Devuelve None si la consulta no parece
    un identificador o si ninguna sonda encontró nada — nunca estorba."""
    if not _secop_es_identificador(query):
        return None
    sondas = _secop_ident_sondas(query)
    if not sondas:
        return None
    contratos, procesos, vistos_c, vistos_p = [], [], set(), set()
    with ThreadPoolExecutor(max_workers=len(sondas)) as pool:
        futs = {}
        for res, col, val in sondas:
            sel = SECOP_SELECT if res == SECOP_RESOURCE else SECOP_PROC_SELECT
            p = {'$select': ','.join(sel), '$limit': SECOP_IDENT_MAX,
                 '$where': f"{col}='{_secop_lit(val)}'"}
            futs[pool.submit(_secop_get_res, res, p, SECOP_IDENT_TIMEOUT)] = (res, col)
        for fut in as_completed(futs):
            res, col = futs[fut]
            try:
                filas = fut.result()
            except Exception as e:
                print(f'[secop] sonda {res}.{col} FAIL: {type(e).__name__}: {e}')
                continue
            for r in filas:
                if res == SECOP_RESOURCE:
                    row = _secop_row(r, [], [])
                    k = row.get('id') or json.dumps(row, sort_keys=True)
                    if k not in vistos_c:
                        vistos_c.add(k)
                        contratos.append(row)
                else:
                    row = _secop_proc_row(r)
                    k = row.get('id') or json.dumps(row, sort_keys=True)
                    if k not in vistos_p:
                        vistos_p.add(k)
                        procesos.append(row)
    if not contratos and not procesos:
        return None
    for p in procesos[:SECOP_ADJ_MAX]:     # ③ solo a los que se muestran arriba
        p['adjudicacion'] = _secop_adjudicacion(p)
    for p in procesos:
        p.pop('_campo_adjudicado', None)
    return {
        'consulta': query,
        'contratos': contratos, 'procesos': procesos,
        'n_contratos': len(contratos), 'n_procesos': len(procesos),
        'encontrado_en': ([['contratos'], []][not contratos]
                          + [['procesos'], []][not procesos]),
        # una referencia repetida en varias entidades no es "el" contrato
        'ambiguo': (len(contratos) + len(procesos)) > 1,
        'nota_adjudicado': SECOP_ADJ_NOTA if procesos else None,
        'solo_proceso': bool(procesos) and not contratos,
    }


# --- procesos (p6dx-8zbt) en la búsqueda general -----------------------------
# El pilar nació mirando solo CONTRATOS. Los PROCESOS son la otra mitad del
# universo (9,02 M contra 5,97 M) y llegan ANTES: es donde el cliente todavía
# puede incidir. Ver el bloque de arriba para las cifras medidas.
#
# ⚠️ NO se fusionan en una sola lista, a propósito: un proceso y el contrato que
# sale de él son la MISMA contratación, así que sumarlos duplicaría el conteo, y
# sus campos no son comparables (precio base ≠ valor firmado, fecha de
# publicación ≠ fecha de firma). Van en dos pestañas con su propio total.
SECOP_PROC_FILTROS = {
    'departamento': 'departamento_entidad',
    'entidad': 'entidad',
    'nit': 'nit_entidad',
    'modalidad': 'modalidad_de_contratacion',
    'tipo': 'tipo_de_contrato',
    'orden_entidad': 'ordenentidad',
}
# `estado` (estado_contrato) y `sector` no existen del lado proceso. NO se
# aplican en silencio: se reportan en `filtros_ignorados` y la UI los muestra —
# un filtro que el usuario cree activo y no lo está es peor que no ofrecerlo.
SECOP_PROC_SIN_EQUIV = ('estado', 'sector')
SECOP_PROC_ORDENES = {'reciente': 'fecha_de_publicacion_del DESC',
                      'valor': 'precio_base DESC'}
SECOP_PROC_IN_MAX = 40
# ⚠️ Los procesos son ADITIVOS: si no alcanzan, la respuesta sale igual con los
# contratos y un aviso. Sin este tope, una ráfaga throttleada llevó la búsqueda
# de 'sena' (243k contratos · 193k procesos) a 50 s — el gateway corta a 30.
SECOP_PROC_BUDGET = float(os.environ.get('SECOP_PROC_BUDGET', '9'))
# ⚠️⚠️ Plazo GLOBAL de la acción. El presupuesto de arriba no basta: medido en
# producción (CloudWatch, ago-2026), el descubrimiento del lado CONTRATO ya
# estaba al borde para un término tan grande como 'sena' —
# `descubrimiento nombre_entidad FAIL: TimeoutError` a los 25 s— y sumarle los
# procesos llevó la invocación a 50 s. Si lo ya gastado no deja margen, los
# procesos NO se piden: el gateway corta a 30 s y una respuesta con contratos
# vale infinitamente más que un 503.
SECOP_DEADLINE = float(os.environ.get('SECOP_DEADLINE', '22'))
# timeout HTTP propio, más corto que el de contratos: un proceso abandonado por
# presupuesto sigue ocupando su cupo del semáforo hasta que su socket muere.
SECOP_PROC_HTTP_TIMEOUT = float(os.environ.get('SECOP_PROC_HTTP_TIMEOUT', '8'))


def _secop_presupuesto(t0):
    """Segundos que quedan para los procesos sin arriesgar el techo del gateway."""
    return min(SECOP_PROC_BUDGET, SECOP_DEADLINE - (_time.time() - t0))

# Medido ago-2026: `nombre_del_proveedor` viene 'No Definido' en 8.024.084 de
# 9.023.386 filas (88,9%) — el dataset de procesos casi no publica a quién se le
# adjudicó. Por eso, del lado empresa, los procesos se encuentran sobre todo por
# ENTIDAD contratante, y la cobertura por proveedor es parcial y se declara.
SECOP_PROC_PROV_NULO = 'No Definido'
SECOP_PROC_NOTA_PROV = (
    'En el dataset de procesos el proveedor viene sin definir en el 88,9% de '
    'las filas: un proceso publica a quién CONTRATA mucho después de abrirse, '
    'o nunca. Por eso los procesos de una empresa se encuentran sobre todo '
    'cuando ella es la entidad contratante; como proveedora, la cobertura es '
    'parcial.')
SECOP_PROC_NOTA_ADJ = (
    'El estado de cada proceso sale de cruzarlo contra el dataset de contratos '
    'por `id_del_portafolio`, no del campo `adjudicado` de la fuente — que en '
    'régimen especial no es confiable (38% de falsos «No» medidos).')


def _secop_proc_where(filtros):
    """(where, ignorados). Los filtros sin equivalente NO se aplican en silencio."""
    conds, ign = [], []
    for k, col in SECOP_PROC_FILTROS.items():
        v = (filtros.get(k) or '').strip()
        if v:
            conds.append(f"{col}='{_secop_lit(v)}'")
    for k in SECOP_PROC_SIN_EQUIV:
        if (filtros.get(k) or '').strip():
            ign.append(k)
    anio = str(filtros.get('anio') or '').strip()
    if anio.isdigit():
        conds.append(f'date_extract_y(fecha_de_publicacion_del)={int(anio)}')
    return ' AND '.join(conds), ign


def _secop_adjudicado_bulk(portafolios):
    """③ en lote: qué portafolios YA tienen contrato firmado. Una sola consulta
    para toda la página (medido: 40 portafolios en 0,59 s), en vez de una por
    fila. Sin esto habría que mostrar el campo `adjudicado` crudo, que miente."""
    ids = [p for p in dict.fromkeys(portafolios) if p][:SECOP_PROC_IN_MAX]
    if not ids:
        return set()
    inl = ','.join("'" + _secop_lit(x) + "'" for x in ids)
    try:
        filas = _secop_get_res(SECOP_RESOURCE, {
            '$select': 'proceso_de_compra', '$group': 'proceso_de_compra',
            '$where': f'proceso_de_compra in({inl})', '$limit': str(len(ids) * 2)},
            timeout=SECOP_IDENT_TIMEOUT)
        return {r.get('proceso_de_compra') for r in filas if r.get('proceso_de_compra')}
    except Exception as e:
        print(f'[secop] cruce adjudicacion lote FAIL: {type(e).__name__}: {e}')
        return None                        # None = no se pudo, ≠ conjunto vacío


def _secop_proc_lista(filas):
    """Filas de proceso para la lista, con el estado resuelto por cruce."""
    rows = [_secop_proc_row(r) for r in filas]
    con = _secop_adjudicado_bulk([r.get('portafolio') for r in rows])
    for r in rows:
        campo = (r.pop('_campo_adjudicado', '') or '').strip() or None
        if con is None:                    # el cruce falló: no se afirma nada
            r['adjudicacion'] = {'estado': 'sin_verificar', 'campo_fuente': campo,
                                 'etiqueta': 'Estado sin verificar', 'campo_desmentido': False}
            continue
        hay = r.get('portafolio') in con
        r['adjudicacion'] = {
            'estado': 'adjudicado' if hay else 'no_informa',
            'etiqueta': (SECOP_ADJ_ETIQUETA['adjudicado'] if hay
                         else SECOP_ADJ_ETIQUETA['no_informa']),
            'campo_fuente': campo,
            'campo_desmentido': bool(hay and (campo or '').lower().startswith('n')),
        }
    return rows


def _contratacion_procesos(query, filtros, limit, orden_key, where_extra=None):
    """Búsqueda en vivo sobre p6dx-8zbt. Misma frontera que contratos: `$q`
    indexado y agregados sobre `$q`; nunca `like`."""
    where, ign = _secop_proc_where(filtros)
    if where_extra:
        where = (where + ' AND ' if where else '') + where_extra
    base = {}
    if query:
        base['$q'] = query
    if where:
        base['$where'] = where
    if not base:
        return None
    orden = SECOP_PROC_ORDENES.get(orden_key or 'reciente', SECOP_PROC_ORDENES['reciente'])
    p_filas = dict(base, **{'$select': ','.join(SECOP_PROC_SELECT),
                            '$order': orden, '$limit': limit})
    if orden.startswith('fecha_de_publicacion_del'):
        # mismo defecto que del lado contrato: las filas SIN fecha encabezan la
        # lista con $order DESC. Se excluyen SOLO de lo mostrado, jamás del
        # total — el conteo debe seguir siendo el universo real.
        p_filas['$where'] = ((where + ' AND ') if where else '') + \
                            'fecha_de_publicacion_del IS NOT NULL'
    p_total = dict(base, **{'$select': 'count(1) as n'})
    p_dep = dict(base, **{'$select': 'departamento_entidad,count(1) as n',
                          '$group': 'departamento_entidad', '$order': 'n DESC', '$limit': 12})
    filas = total = dep = None
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(_secop_get_res, SECOP_PROC_RESOURCE, p,
                            SECOP_PROC_HTTP_TIMEOUT): k
                for p, k in ((p_filas, 'filas'), (p_total, 'total'), (p_dep, 'dep'))}
        for fut in as_completed(futs):
            k = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                print(f'[secop] procesos/{k} FAIL: {type(e).__name__}: {e}')
                continue
            if k == 'filas':
                filas = r
            elif k == 'total':
                total = r
            else:
                dep = r
    if filas is None:
        return None                        # sin filas no hay pestaña que pintar
    n_tot = None
    try:
        n_tot = int(total[0].get('n') or 0)
    except Exception:
        pass
    return {
        'n': len(filas), 'total': n_tot,
        'resultados': _secop_proc_lista(filas),
        'por_departamento': [{'departamento': d.get('departamento_entidad') or '—',
                              'n': int(d.get('n') or 0)} for d in (dep or [])],
        'filtros_ignorados': ign,
        'nota_adjudicado': SECOP_PROC_NOTA_ADJ,
    }


def _secop_descubrir_proc(emps, terms):
    """Entidades del universo de PROCESOS que SON la empresa. Existe porque hay
    entidades que casi no aparecen del lado contrato: Findeter tiene 5.089
    procesos, y su razón social ('FINANCIERA DE DESARROLLO TERRITORIAL S.A.')
    NO contiene la marca — el mismo problema de identidad de COMCEL/Claro."""
    vistos = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        # 1 término, no 3: cada consulta extra sale del presupuesto de ráfaga
        # (ver SECOP_MAX_PARALELO) y los alias casi no aportan entidades que el
        # término principal no traiga ya.
        futs = [pool.submit(_secop_get_res, SECOP_PROC_RESOURCE,
                            {'$q': t, '$select': 'entidad,count(1) as n',
                             '$group': 'entidad', '$order': 'n DESC',
                             '$limit': SECOP_DESC_LIMIT}, SECOP_PROC_HTTP_TIMEOUT)
                for t in terms[:1]]
        for fut in as_completed(futs):
            try:
                filas = fut.result()
            except Exception as e:
                print(f'[secop] descubrimiento proc FAIL: {type(e).__name__}: {e}')
                continue
            for r in filas:
                nm = (r.get('entidad') or '').strip()
                if nm:
                    vistos[nm] = max(vistos.get(nm, 0), int(r.get('n') or 0))
    return sorted(((n, c) for n, c in vistos.items()
                   if empresas.marca_lidera_any(emps, n)), key=lambda x: -x[1])


def _procesos_con_presupuesto(t0, fn, *args):
    """Corre el bloque de procesos con tope de tiempo. Devuelve (dato, tarde).

    ⚠️⚠️ El pool NO va en `with`: su `__exit__` hace `shutdown(wait=True)` y
    espera igual al hilo que acabamos de abandonar, con lo que el tope de tiempo
    no ahorra NADA (medido: una consulta de 1,5 s se fue a 30 s). Rendirse de
    verdad es `shutdown(wait=False)`; el hilo huérfano muere solo con su timeout
    HTTP corto."""
    resto = _secop_presupuesto(t0)
    if resto < 1.0:                        # sin margen: ni se piden
        print('[secop] procesos: sin margen en el plazo global, se omiten')
        return None, True
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        fut = pool.submit(fn, *args)
        try:
            return fut.result(timeout=resto), False
        except FuturesTimeoutError:
            print('[secop] procesos (empresa): fuera de presupuesto, se omiten')
            return None, True
        except Exception as e:
            print(f'[secop] procesos (empresa) FAIL: {type(e).__name__}: {e}')
            return None, False
    finally:
        pool.shutdown(wait=False)


def _contratacion_procesos_empresa(emps, query, prov, ent, filtros, limit, orden_key):
    """Procesos de UNA empresa: por identidad, igual que los contratos. Reusa
    las razones sociales ya descubiertas del lado contrato (no cuesta consulta)
    y suma las entidades que solo existen del lado proceso."""
    ent_proc = _secop_descubrir_proc(emps, [query] + [a for e in emps for a in e['alias']])
    ents = list(dict.fromkeys([n for n, _ in ent] + [n for n, _ in ent_proc]))
    provs = [n for n, _ in prov if n != SECOP_PROC_PROV_NULO]
    ors = []
    if provs:
        ors.append('nombre_del_proveedor in (' +
                   ','.join("'" + _secop_lit(n) + "'" for n in provs[:SECOP_PROC_IN_MAX]) + ')')
    if ents:
        ors.append('entidad in (' +
                   ','.join("'" + _secop_lit(n) + "'" for n in ents[:SECOP_PROC_IN_MAX]) + ')')
    if not ors:
        return None
    out = _contratacion_procesos(None, filtros, limit, orden_key,
                                 where_extra='(' + ' OR '.join(ors) + ')')
    if out is not None:
        out['por_identidad'] = True
        out['entidades'] = [{'nombre': n, 'n': c} for n, c in ent_proc[:12]]
        out['nota_proveedor'] = SECOP_PROC_NOTA_PROV
    return out


def _contratacion(body):
    """Modo A (sin query ni filtros) → agregados del landing. Modo B → búsqueda
    en vivo contra Socrata: filas + total real + desglose por departamento."""
    t0 = _time.time()
    query = (body.get('query') or '').strip()
    filtros = {k: body.get(k) for k in list(SECOP_FILTROS) + ['anio']}
    solo_objeto = bool(body.get('solo_objeto')) and bool(query)
    where = _secop_where(filtros)
    if not query and not where:
        return dict(_secop_stats(), mode='stats')

    limit = max(1, min(int(body.get('limit') or 50), 200))
    orden = SECOP_ORDENES.get(body.get('orden') or 'reciente', SECOP_ORDENES['reciente'])
    # ④ ¿la consulta nombra una empresa del diccionario? Entonces el usuario no
    # quiere "contratos que dicen Uber", quiere "los contratos de Uber".
    # `ampliar_empresa` (el mismo toggle de los otros pilares) apaga el filtro y
    # devuelve el universo $q crudo — ampliar es perder precisión, acá también.
    emps = empresas.empresas_en(query) if query else []
    por_identidad = bool(emps) and not body.get('ampliar_empresa')
    ck = ('contratacion-' + _hash24(json.dumps(
        ['v3-proc', query, where, limit, orden, solo_objeto, por_identidad],
        ensure_ascii=False, sort_keys=True))
        + f'-{_medios_cache_bucket(3)}')
    cached = _cache_get(ck)
    if cached:
        return cached

    # ② El camino por radicado corre SIEMPRE que la consulta parezca un
    # identificador, en paralelo con lo demás y sin condicionarlo: si no
    # encuentra nada devuelve None y la respuesta queda igual que antes.
    ident = _secop_identificador(query) if query else None

    if por_identidad:
        emp = _contratacion_empresa(body, query, emps, filtros, where)
        if emp.get('error_transitorio'):
            return {'error': 'SECOP no respondió a tiempo. Es intermitente: '
                             'vuelve a buscar en unos segundos.',
                    'reintentable': True, 'mode': 'search', 'query': query}
        if emp.get('sin_contratos'):
            # honesto: la empresa existe en el diccionario pero no le vende al
            # Estado (verificado: Uber y Ecopetrol no tienen contratos en SECOP
            # II). No se cae a $q en silencio — eso devolvería homónimos.
            procs, procs_tarde = _procesos_con_presupuesto(
                t0, _contratacion_procesos_empresa, emps, query,
                emp.get('_prov') or [], emp.get('_ent') or [],
                filtros, limit, body.get('orden'))
            out = {'mode': 'search', 'query': query, 'identidad_empresa': True,
                   'identificador': ident, 'procesos': procs,
                   'procesos_tarde': procs_tarde,
                   'sin_contratos': True, 'n': 0, 'total': {'contratos': 0, 'valor_cop': 0},
                   'filtros': {k: v for k, v in filtros.items() if v},
                   'orden': body.get('orden') or 'reciente',
                   'empresas': emp['empresas'], 'resultados': [], 'por_departamento': [],
                   'descartados': [{'nombre': n, 'n': c} for n, c in emp['descartados'][:12]],
                   'n_descartados': len(emp['descartados']),
                   'chips': _secop_chips(query),
                   'fuente': _secop_stats().get('fuente', {}),
                   'nota': _secop_stats().get('nota', '')}
            _cache_put(ck, out)
            return out
        procs, procs_tarde = _procesos_con_presupuesto(
            t0, _contratacion_procesos_empresa, emps, query,
            emp.get('_prov') or [], emp.get('_ent') or [],
            filtros, limit, body.get('orden'))
        out = {
            'mode': 'search', 'query': query, 'identidad_empresa': True,
            'identificador': ident, 'procesos': procs,
            'procesos_tarde': procs_tarde,
            'solo_objeto': False, 'revisadas': None,
            'filtros': {k: v for k, v in filtros.items() if v},
            'orden': body.get('orden') or 'reciente',
            'n': len(emp['filas']), 'total': emp['total'],
            'por_departamento': [{'departamento': d.get('departamento') or '—',
                                  'n': int(d.get('n') or 0)} for d in (emp['dep'] or [])],
            'chips': _secop_chips(query),
            'empresas': emp['empresas'],
            'proveedores': emp['proveedores'], 'entidades': emp['entidades'],
            'descartados': emp['descartados'], 'n_descartados': emp['n_descartados'],
            'truncado': emp['truncado'],
            'resultados': [_secop_row(r, [], emp['cols']) for r in emp['filas']],
            'fuente': _secop_stats().get('fuente', {}),
            'nota': _secop_stats().get('nota', ''),
        }
        _cache_put(ck, out)
        return out

    base = {}
    if query:
        base['$q'] = query                  # indexado (nunca `like`, ver abajo)
    if where:
        base['$where'] = where
    # "solo en el objeto" NO se hace con `like`: medido jul-2026, un
    # `like` sobre objeto_del_contrato tarda 31 s sin `$order` y >70 s con él —
    # por encima del techo de 30 s de API Gateway. Se resuelve trayendo más filas
    # por $q (indexado, ~1-3 s) y filtrando la frase acá. Cuesta cobertura (solo
    # filtra lo traído), no el conteo: el total del universo $q se conserva.
    n_pedir = min(200, limit * 4) if solo_objeto else limit
    p_filas = dict(base, **{'$select': ','.join(SECOP_SELECT),
                            '$order': orden, '$limit': n_pedir})
    if orden.startswith('fecha_de_firma'):
        # 421k contratos del dataset vienen SIN fecha de firma y con `$order`
        # por fecha encabezan la lista (filas "No definido", valor 0). Se
        # excluyen SOLO de las filas mostradas, no de los agregados: el `total`
        # debe seguir siendo el universo real de la búsqueda.
        p_filas['$where'] = ((where + ' AND ') if where else '') + 'fecha_de_firma IS NOT NULL'
    p_total = dict(base, **{'$select': 'count(1) as n,sum(valor_del_contrato) as v'})
    p_dep = dict(base, **{'$select': 'departamento,count(1) as n',
                          '$group': 'departamento', '$order': 'n DESC', '$limit': 12})

    # el pool de procesos va APARTE y sin `with`: si se pasa del presupuesto hay
    # que poder soltarlo sin que nadie lo espere (ver _procesos_con_presupuesto).
    proc_pool = ThreadPoolExecutor(max_workers=1)
    f_proc = proc_pool.submit(_contratacion_procesos, query, filtros, limit,
                              body.get('orden'))
    proc_pool.shutdown(wait=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_filas = pool.submit(_secop_get, p_filas)
        f_total = pool.submit(_secop_get, p_total)
        f_dep = pool.submit(_secop_get, p_dep)
        try:
            filas = f_filas.result()
        except Exception as e:
            # antes esto subía y el gateway devolvía 502. Un 503 de Socrata es
            # transitorio: se dice con palabras y el cliente reintenta.
            print(f'[secop] filas FAIL: {type(e).__name__}: {e}')
            return {'error': 'SECOP no respondió a tiempo. Es intermitente: '
                             'vuelve a buscar en unos segundos.',
                    'reintentable': True, 'mode': 'search', 'query': query}
        total = dep = None
        for fut, name in ((f_total, 'total'), (f_dep, 'dep')):
            try:
                r = fut.result()
            except Exception as e:
                print(f'[secop] agregado {name} FAIL: {type(e).__name__}: {e}')
                continue
            if name == 'total':
                total = r
            else:
                dep = r

    procs, procs_tarde = None, False
    try:
        procs = f_proc.result(timeout=max(0.5, _secop_presupuesto(t0)))
    except FuturesTimeoutError:
        procs_tarde = True                  # se declara, no se esconde
        print('[secop] procesos: fuera de presupuesto, se omiten')
    except Exception as e:
        print(f'[secop] procesos FAIL: {type(e).__name__}: {e}')

    cols = _secop_stats().get('columnas_match') or SECOP_MATCH_FALLBACK
    terms = [t for t in _secop_norm(query).split() if t]
    n_traidas = len(filas)
    if solo_objeto:
        frase = _secop_norm(query)
        filas = [r for r in filas if frase in _secop_norm(r.get('objeto_del_contrato'))][:limit]
    tot = None
    if total:
        try:
            tot = {'contratos': int(total[0].get('n') or 0),
                   'valor_cop': round(float(total[0].get('v') or 0))}
        except Exception:
            tot = None
    out = {
        'mode': 'search', 'query': query, 'solo_objeto': solo_objeto,
        'identificador': ident,
        # `empresas` viaja también acá: es el caso "ampliar" (el usuario pidió
        # ver todo lo que menciona la marca) y el aviso tiene que seguir visible
        # para poder volver a lo preciso.
        'empresas': _empresas_payload(emps), 'identidad_empresa': False,
        'procesos': procs, 'procesos_tarde': procs_tarde,
        'revisadas': n_traidas if solo_objeto else None,
        'filtros': {k: v for k, v in filtros.items() if v},
        'orden': body.get('orden') or 'reciente',
        'n': len(filas), 'total': tot,
        'por_departamento': [{'departamento': d.get('departamento') or '—',
                              'n': int(d.get('n') or 0)} for d in (dep or [])],
        'chips': _secop_chips(query),
        'resultados': [_secop_row(r, terms, cols) for r in filas],
        'fuente': _secop_stats().get('fuente', {}),
        'nota': _secop_stats().get('nota', ''),
    }
    _cache_put(ck, out)
    return out


# --- LLM (ruteo por paso) ---------------------------------------------------
def _hash24(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:24]


def _cache_get(key):
    try:
        return _get_json(CACHE_PREFIX + key + '.json')
    except _s3.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def _cache_put(key, data):
    try:
        _s3.put_object(Bucket=BUCKET, Key=CACHE_PREFIX + key + '.json',
                       Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                       ContentType='application/json')
    except Exception:
        pass


def _call_deepseek(model, system, user, max_tokens):
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': 0.4, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/chat/completions', data=body,
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        d = json.loads(r.read())
    return d['choices'][0]['message']['content']


def _call_anthropic(model, system, user, max_tokens):
    # switch de calidad para la síntesis (Sonnet 5 / Opus 4.8). Sin thinking
    # config: Sonnet 5 corre adaptive por defecto al omitirlo.
    body = json.dumps({
        'model': model, 'max_tokens': max_tokens, 'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=body,
        headers={'Content-Type': 'application/json',
                 'x-api-key': os.environ['ANTHROPIC_API_KEY'],
                 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        d = json.loads(r.read())
    return ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')


def _call_llm(step, system, user, max_tokens=1200):
    cfg = STEP_MODELS[step]
    if cfg['provider'] == 'anthropic':
        return _call_anthropic(cfg['model'], system, user, max_tokens)
    return _call_deepseek(cfg['model'], system, user, max_tokens)


# --- síntesis de tema (lectura interpretativa del resumen) ------------------
SINT_SYSTEM = (
    "Eres analista legislativo de Cauce. Escribes en español, tuteo neutro de "
    "Bogotá (sin voseo, sin regionalismos). Analizas trámite legislativo del "
    "Congreso de Colombia. REGLA DURA: solo usas los datos del resumen que se "
    "te entrega; NO inventas cifras, nombres ni hechos que no estén ahí. Si un "
    "dato no está, no lo menciones. Devuelves SIEMPRE un JSON válido con las "
    "claves: titular, hallazgo, por_que_caen, quien_propone, veredicto."
)


QEXP_SYSTEM = """Eres experto en técnica legislativa colombiana. El usuario busca un tema con
SUS palabras (lenguaje común o empresarial), pero los títulos de los proyectos de ley usan
lenguaje formal y a menudo NO contienen esa palabra. Ejemplo real: la ley de sellos de
advertencia se titula "por medio de la cual se adoptan medidas para fomentar ENTORNOS
ALIMENTARIOS SALUDABLES" — la palabra "etiquetado" no aparece nunca.

Devuelve el vocabulario que REALMENTE aparece en los títulos de proyectos de ley del Congreso
de Colombia sobre ese tema, para poder recuperarlos.

Reglas:
1. Entre 6 y 12 términos. Cada uno es una palabra o una frase corta (2-4 palabras).
2. OBLIGATORIO: si sobre el tema ya se aprobó una ley en Colombia, incluye la frase con la que
   se TITULÓ esa ley, aunque no contenga la palabra del usuario. Piensa "¿cómo se llamó la ley
   que quedó?" — es el término más valioso, porque es el que el título sí contiene.
3. Incluye además sinónimos formales, el nombre técnico y como el Congreso nombra el asunto.
4. NO incluyas palabras genéricas que traerían ruido: ley, norma, nacional, sistema, servicio,
   medidas, disposiciones, política, general, colombiano, territorio, fomento.
5. Cada término debe ser DISTINTIVO del tema: si al leerlo suelto no se sabe de qué trata, va fuera.
6. Prefiere precisión sobre cantidad. Ante la duda, omite el término.
7. Sin tildes, en minúsculas.

Ejemplo (tema "etiquetado alimentos") → debe incluir "entornos alimentarios saludables" (así se
tituló la Ley 2120 de 2021), además de "sellos de advertencia", "rotulado nutricional", etc.

Responde SOLO JSON: {"terminos": ["...", "..."]}"""

QEXP_VERSION = 'v2'   # versión propia: cambiarla invalida SOLO el cache de expansión


def _expandir_query(query, solo_cache=False):
    """Vocabulario legislativo equivalente a la consulta del usuario (expansión
    de consulta con IA). Resuelve el desajuste de vocabulario: el usuario busca
    'etiquetado' y el título dice 'entornos alimentarios saludables'. Cacheado
    por consulta normalizada; best-effort (si falla, [] y la búsqueda sigue
    como antes — nunca rompe la ruta).

    `solo_cache=True` sirve lo ya calculado y NUNCA llama al modelo. Es el modo
    del visitante sin acceso: la expansión es justo lo que hace buena la
    búsqueda gratis, así que no se le quita — pero generarla a demanda sería un
    grifo abierto (una consulta nueva por petición, y el atacante las inventa
    infinitas). Como las consultas reales se repiten mucho, el visitante acaba
    recibiendo casi siempre la expansión que ya pagó alguien con acceso, y la
    cobertura mejora sola con el uso."""
    q = (query or '').strip()
    if len(q) < 3:
        return []
    ck = 'qexp-' + _hash24(QEXP_VERSION + '|qexp|' + q.lower())
    cached = _cache_get(ck)
    if cached is not None:
        return cached.get('terminos', [])
    if solo_cache:
        return []
    try:
        raw = _call_llm('sintesis', QEXP_SYSTEM,
                        f'Tema buscado por el usuario: "{q}"\n\nJSON:',
                        max_tokens=2500).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
        terms, seen = [], set()
        for t in (data.get('terminos') or [])[:10]:
            t = str(t or '').strip().lower()
            # descarta lo muy corto/genérico y los duplicados
            if 4 <= len(t) <= 48 and t not in seen:
                seen.add(t)
                terms.append(t)
    except Exception:
        terms = []
    _cache_put(ck, {'terminos': terms})
    return terms


def _sintesis_tema(resumen, casos=None):
    """Arma el prompt de la lectura de un tema. Devuelve (key, user) — NO genera.
    La generación vive en _tema_lectura_generar (ver por qué en _tema_lectura_pedir)."""
    casos_hash = _hash24('|'.join(sorted(c['gaceta'] for c in (casos or []))))
    key = _hash24(PROMPT_VERSION + '|tema|' + resumen['query'] + '|' +
                  str(resumen['n_intentos']) + '|' + str(resumen['n_leyes']) +
                  '|' + str(resumen.get('n_vitrina', 0)) + '|' + casos_hash)
    # (el early-return del caché vive ahora en _tema_lectura_pedir: esta función
    #  solo ARMA el prompt y devuelve (key, user) — no llama al modelo)
    intentos_txt = '\n'.join(
        f"- [{it['anio']}] {it['resultado_txt']} · {it.get('empuje_txt','')}: {it['titulo'][:85]}"
        for it in resumen['intentos'][:20])
    casos_txt = ''
    if casos:
        def _fmt_caso(c):
            partes = [f"- [{c['anio']}] {c['titulo'][:80]} (Gaceta {c['gaceta']}, {c['tipo_doc'] or 'documento'}): "
                     f"sentido {c['sentido'] or 'desconocido'}"]
            if c.get('sentido_detalle'):
                partes.append(f' — {c["sentido_detalle"]}')
            if c.get('ponentes'):
                partes.append(f". Ponente(s): {', '.join(c['ponentes'][:3])}.")
            if c.get('argumentos'):
                partes.append(f" Argumentos centrales: {'; '.join(c['argumentos'][:3])}.")
            if c.get('en_contra'):
                partes.append(f" Oposición/archivo: {c['en_contra']}")
            return ''.join(partes)
        casos_txt = ('\n\nEVIDENCIA REAL leída de la Gaceta del Congreso (no es metadata, es lo que '
                    'DICE el documento — úsala, es más fuerte que la estadística sola) para algunos '
                    'de estos intentos:\n' + '\n'.join(_fmt_caso(c) for c in casos))
    autores_txt = ', '.join(f"{a} ({n})" for a, n in resumen['top_autores'][:6])
    bancadas_txt = ', '.join(f"{p} ({n} proyectos)" for p, n in resumen.get('bancadas', [])[:6]) or 'sin dato'
    cob = resumen.get('cobertura_partido', {})
    emp = resumen.get('empuje', {})
    user = (
        f"Tema consultado: «{resumen['query']}»\n"
        f"Intentos totales: {resumen['n_intentos']} · convertidos en ley: "
        f"{resumen['n_leyes']} ({resumen['pct_exito']}%) · caídos: "
        f"{resumen['n_caidos']} (de esos, {resumen['n_muerte_por_tiempo']} "
        f"murieron por vencimiento de términos, Art. 190 Ley 5ª).\n"
        f"Periodo: {resumen.get('periodo')}\n"
        f"Embudo del trámite: {json.dumps(resumen['embudo'], ensure_ascii=False)}\n"
        f"LECTURA DE INTENCIÓN (metadata): {resumen.get('n_vitrina',0)} intentos "
        f"({resumen.get('pct_vitrina',0)}%) son de VITRINA (re-radicados sin superar "
        f"el 1er debate — se radican para figurar, no para empujar). "
        f"{resumen.get('n_honores',0)} son de honores/conmemoración. "
        f"Desglose de empuje: {json.dumps(emp, ensure_ascii=False)}.\n"
        f"Quiénes más lo intentan: {autores_txt}\n"
        f"Bancadas que lo impulsan (por partido de los autores, "
        f"cobertura {cob.get('con')}/{cob.get('con',0)+cob.get('sin',0)} intentos): {bancadas_txt}\n"
        f"Línea de intentos:\n{intentos_txt}"
        f"{casos_txt}\n\n"
        "Escribe el análisis en JSON. `titular`: una frase potente y precisa. "
        "`hallazgo`: 2-3 frases con el patrón central; si hay proporción alta de "
        "vitrina o de honores, dilo sin rodeos (distingue quién de verdad empujó el "
        "tema de quién solo lo radicó para figurar). `por_que_caen`: la causa "
        "de muerte dominante (si mueren por tiempo, dilo claro: se hunden en el "
        "orden del día, no por votación). `quien_propone`: usa las BANCADAS para "
        "decir qué partidos empujan el tema (¿transversal o de un solo bloque?); "
        "si la cobertura de partido es parcial, acláralo. `veredicto`: cierre de "
        "1-2 frases.\nSi te di EVIDENCIA REAL de gaceta arriba, úsala: nombra el "
        "proyecto concreto, el ponente o el sentido en `hallazgo` y/o `por_que_caen` "
        "— eso es lo que distingue este análisis de un conteo genérico. NO inventes "
        "nada que no esté en esa evidencia. Si no te di evidencia, trabaja solo con "
        "la metadata y no la menciones.")
    return key, user


def _tema_lectura_pedir(resumen, casos=None):
    """Deja el prompt listo en caché y devuelve (key, lectura_hecha_o_None).

    ⚠️ Por qué esto NO genera acá: la síntesis tarda entre 20 y 51 s —la varianza
    es del modelo, no del prompt— y el API Gateway corta a los 30 s. Medido
    ago-2026: `tema` con lectura devolvía HTTP 503 a los 30,7 s en la primera
    consulta de un tema nuevo, aunque la Lambda terminara y dejara la respuesta
    cacheada; el reintento la traía en 1,6 s. O sea, el primero que buscaba un
    tema nuevo veía un error. Es el mismo problema que ya se resolvió en el radar
    del cliente, y esto porta el mismo patrón: preparar → disparar → sondear."""
    key, user = _sintesis_tema(resumen, casos)
    hecha = _cache_get(key)
    if hecha:
        return key, hecha
    _cache_put('tema-in-' + key, {'user': user, 'casos': casos or []})
    return key, None


def _tema_lectura_generar(key):
    """Genera la lectura de un tema ya preparado y la deja en el caché."""
    prompt = _cache_get('tema-in-' + key)
    if not prompt or not prompt.get('user'):
        # el resumen que la originó ya no está en caché (otra versión de prompt,
        # o el objeto caducó): que el frontend vuelva a pedir el tema.
        return {'estado': 'sin_tema'}
    lock = _cache_get('tema-lock-' + key)
    if lock and _time.time() - float(lock.get('t') or 0) < LECTURA_LOCK_TTL:
        # ya hay una generación en vuelo. Sin el candado, cada reintento del
        # navegador arrancaba otra llamada de 50 s al modelo en paralelo.
        return {'estado': 'generando'}
    _cache_put('tema-lock-' + key, {'t': _time.time()})
    casos = prompt.get('casos') or []
    try:
        # max_tokens alto: DeepSeek V4 gasta tokens en reasoning y con presupuesto
        # bajo deja content vacío (finish_reason=length) — gotcha documentado.
        raw = _call_llm('sintesis', SINT_SYSTEM, prompt['user'], max_tokens=6000)
        raw = raw.strip()
        if raw.startswith('```'):                    # por si envuelve en fences
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'titular': '', 'hallazgo': '', 'por_que_caen': '',
                'quien_propone': '', 'veredicto': '', 'error': str(e)[:200]}
    data['_model'] = STEP_MODELS['sintesis']['model']
    data['casos_evidencia'] = casos   # trazabilidad: qué gacetas sustentan la lectura
    if 'error' not in data:          # no cachear fallos
        _cache_put(key, data)
    return {'estado': 'lista', 'lectura': data}


def _gaceta_decisiva(full):
    """Última gaceta con número real del trámite de un proyecto — la más
    avanzada (ponencia/acta más cercana a la decisión final), y por tanto la
    más informativa sobre por qué pasó o se cayó."""
    gacetas = [g for g in (full.get('gacetas') or []) if g.get('gaceta')]
    if not gacetas:
        return None
    g = gacetas[-1]
    return g['gaceta'].replace('/', '-'), (g.get('tipo') or '')


def _profundizar_tema(caudal, resumen, k_objetivo=2, k_candidatos=6, presupuesto_s=11):
    """Trae evidencia REAL de gaceta (ponente/sentido/argumentos, no solo
    metadata) para los proyectos más relevantes de un tema. Cobertura de texto
    es solo 2020+ (harvest en curso) — prueba candidatos en paralelo y se queda
    con los que sí tengan texto en S3, hasta juntar k_objetivo casos.
    PARALELO a propósito: API Gateway (HTTP API) tiene un tope DURO de 30s de
    integración que no se puede subir — encadenar 4+ llamadas a DeepSeek
    secuenciales (una por candidato + la síntesis final) lo revienta seguro.
    `presupuesto_s` corta la espera de candidatos lentos para dejarle tiempo a
    la síntesis final, aunque junte menos de k_objetivo casos."""
    caudal._full = _full()   # sin esto, caudal.proyecto() intenta leer un path
                              # local que no existe en la Lambda y devuelve None
                              # para TODO — mismo patrón que la acción 'proyecto'

    def _intento(c):
        full = caudal.proyecto(c['id'], c['tb'])
        if not full:
            return None
        dec = _gaceta_decisiva(full)
        if not dec:
            return None
        key, tipo = dec
        numero = full.get('numero_camara') or full.get('numero_senado') or ''
        contexto = f"Proyecto de ley {numero} · {full.get('titulo', '')}"
        ext = _extraer_gaceta(key, contexto)
        if 'error' in ext:
            return None
        return {
            'id': c['id'], 'tb': c['tb'], 'titulo': full.get('titulo', ''),
            'anio': c.get('anio'), 'resultado_txt': c.get('resultado_txt', ''),
            'numero': numero, 'gaceta': key, 'tipo_doc': ext.get('tipo_documento', tipo),
            'ponentes': ext.get('ponentes', []), 'sentido': ext.get('sentido'),
            'sentido_detalle': ext.get('sentido_detalle'),
            'argumentos': ext.get('argumentos', []), 'en_contra': ext.get('en_contra'),
        }

    candidatos = caudal.candidatos_gaceta(resumen, k=k_candidatos)
    if not candidatos:
        return []
    casos, t0 = [], _time.time()
    with ThreadPoolExecutor(max_workers=min(6, len(candidatos))) as ex:
        futs = [ex.submit(_intento, c) for c in candidatos]
        try:
            for fut in as_completed(futs, timeout=presupuesto_s):
                r = fut.result()
                if r:
                    casos.append(r)
                if len(casos) >= k_objetivo or _time.time() - t0 > presupuesto_s:
                    break
        except FuturesTimeoutError:
            pass
    return casos[:k_objetivo]


# --- Radar del cliente · lectura interpretada (SKU A · Vista Cliente) --------
CLIENTE_SYSTEM = (
    "Eres analista de asuntos públicos de Cauce. Escribes en español, tuteo "
    "neutro de Bogotá (sin voseo, sin regionalismos). Te doy el RADAR DE HOY de "
    "un cliente: los proyectos de ley activos en el Congreso, las sanciones "
    "recientes de las superintendencias, la contratación del Estado y la prensa "
    "reciente que tocan sus temas, ya filtradas y con su nivel de prioridad. "
    "Algunas señales van marcadas VIGILADA DEL CLIENTE: son sobre una empresa "
    "que él sigue de cerca — priorízalas y nómbralas explícitamente. Esto es un "
    "BRIEFING de seguimiento, NO un archivo histórico — escribe como si le "
    "contaras a tu cliente qué pasó y qué viene, no como quien resume un "
    "expediente de 36 años. Precisión sobre volumen. REGLA DURA: usa SOLO las "
    "señales que te doy; NO inventes proyectos, cifras, entidades, sanciones "
    "ni titulares de prensa. Si algo no está, no lo menciones. Devuelves "
    "SIEMPRE un JSON válido.\n\n"
    "El briefing se organiza en CUATRO DIRECCIONES, y cada una responde una "
    "pregunta distinta. Las señales te llegan ya repartidas y marcadas "
    "[MOVIMIENTO] (ocurrió en las últimas 72 horas: es noticia) o [ESTADO] "
    "(situación vigente, no pasó hoy). Esa diferencia es la clave del briefing: "
    "NUNCA presentes como novedad algo marcado ESTADO.\n"
    "  · norte  — la OPORTUNIDAD. Qué se está abriendo para este cliente. Es la "
    "única dirección donde INTERPRETAS en vez de reportar: cruza lo que ves en "
    "las otras tres y di qué ventana se abre o se cierra. Si el trámite va bien "
    "pero el ambiente está caldeado, dilo; si algo se ve muerto y hay ventana, "
    "dilo. No inventes hechos: interpreta los que te di.\n"
    "  · este   — la CONVERSACIÓN. Qué se está diciendo en la prensa, en qué "
    "tono y quién lo dice.\n"
    "  · sur    — la COMPETENCIA. Qué les está pasando a las empresas que el "
    "cliente vigila. Nómbralas.\n"
    "  · oeste  — el ESTADO. Qué está produciendo el Congreso y las "
    "superintendencias sobre sus temas.\n\n"
    "REGLA DE HONESTIDAD: si una dirección no trajo NADA en 72 horas, dilo "
    "explícitamente («sin movimiento en 72 horas») y describe en una frase cómo "
    "está el frente. NO rellenes, NO estires, NO presentes algo viejo como "
    "nuevo. Un punto cardinal quieto es información, no un hueco.\n\n"
    "Campos del JSON: titular (una frase potente y precisa de lo principal de "
    "hoy), norte, este, sur, oeste (2-3 frases cada uno, citando ítems "
    "concretos por nombre), acciones (lista de 2-4 acciones concretas) y "
    "horizonte (1-2 frases sobre qué ventana se abre próximamente).")


# cuántas señales entran al briefing. Es un tope de COSTO y de foco, no de
# cobertura: el radar completo se le muestra al usuario en pantalla.
LECTURA_MAX_SENALES = 26

# ── los cuatro puntos ────────────────────────────────────────────────────────
# El producto dejó de ser un listado por FUENTE y pasa a orientar en cuatro
# direcciones. El mapeo no es cosmético: cambia qué pregunta responde cada
# bloque.
#   Norte  · qué se abre  → contratación (el Estado comprando) + la lectura de
#                           contexto, que es lo único que no sale de un feed
#   Este   · qué se dice  → prensa
#   Sur    · la competencia → CUALQUIER señal sobre una vigilada, venga del
#                           pilar que venga: si sancionan a tu competidor eso es
#                           noticia de competencia, no "regulatorio" a secas
#   Oeste  · el Estado    → Congreso y superintendencias sobre TU tema
CARD_POR_TIPO = {'contratacion': 'norte', 'medios': 'este',
                 'congreso': 'oeste', 'regulatorio': 'oeste'}
CARD_LBL = {'norte': 'NORTE · oportunidad', 'este': 'ESTE · conversación',
            'sur': 'SUR · competencia',    'oeste': 'OESTE · Estado'}

# Ventana de "se movió". 72 h es lo que pidió el cliente y es la ventana correcta
# para un brief diario, PERO medido contra producción (ago-2026) solo la prensa
# tiene volumen diario: regulatorio y contratación traen 0 señales en ≤3 días la
# mayoría de los días. Por eso el radar NO filtra por esta ventana — la usa para
# SEPARAR: lo de ≤3 días es movimiento (noticia), lo demás es estado del frente
# (situación vigente). Un filtro duro dejaría tres de los cuatro puntos vacíos y
# convertiría el producto en un servicio de recortes de prensa.
MOV_DIAS = 3


def _es_movimiento(x):
    """¿La señal cayó dentro de la ventana de movimiento?

    ⚠️ Las señales del Congreso NO traen fecha: el índice guarda solo el año
    (`a`), la fecha de radicación vive en proyectos.jsonl y no se sube al
    índice. Así que un proyecto nunca cuenta como "movimiento" — y eso es
    correcto de todas formas: un proyecto en trámite es una situación vigente,
    no una noticia de hoy. Para poder decir "esto se radicó anteayer" habría que
    llevar la fecha al índice (ver el pendiente en CLAUDE.md)."""
    f = (x.get('fecha') or '')[:10]
    if len(f) != 10:
        return False
    try:
        d = datetime.date(int(f[:4]), int(f[5:7]), int(f[8:10]))
    except (ValueError, TypeError):
        return False
    return 0 <= (datetime.date.today() - d).days <= MOV_DIAS


def _anotar_cardinales(senales):
    """Marca cada señal con su punto (`card`) y si es movimiento (`mov`).

    La vigilada gana sobre el tipo: una sanción a un competidor es Sur, no
    Oeste. Devuelve el conteo por punto para los KPI."""
    cuenta = {c: {'total': 0, 'mov': 0} for c in ('norte', 'este', 'sur', 'oeste')}
    for x in senales:
        card = 'sur' if x.get('vigilada') else CARD_POR_TIPO.get(x.get('tipo'), 'oeste')
        mov = _es_movimiento(x)
        x['card'], x['mov'] = card, mov
        cuenta[card]['total'] += 1
        cuenta[card]['mov'] += 1 if mov else 0
    return cuenta
# vida del candado que evita dos generaciones simultáneas de la misma lectura.
# Un poco más que el timeout de la Lambda: si la que tenía el candado murió,
# la siguiente petición puede volver a intentarlo.
LECTURA_LOCK_TTL = 70


def _lectura_cliente_key(s, kpis):
    """Firma de la lectura: mismo perfil + mismo radar = misma lectura.

    Incluye temas y vigiladas porque con un perfil por cliente `s['k']` es
    siempre 'perfil' y dos gremios distintos compartirían el briefing.
    """
    firma = '|'.join([s.get('k', ''), s.get('nombre', ''),
                      ','.join(sorted(s.get('temas', []))),
                      ','.join(sorted(s.get('empresas_keys', []))),
                      s.get('sector_sanciones', '')])
    return _hash24(PROMPT_VERSION + '|cliente|' + firma + '|' + str(kpis['n_radar'])
                   + '|' + str(kpis['alto']) + '|' + str(kpis['en_tramite']))


def _lectura_cliente_prompt(s, senales, kpis):
    """El mensaje de usuario del briefing, ya armado.

    Se separa del envío para poder GUARDARLO: la lectura se genera en una
    petición aparte y no puede volver a calcular el radar (es lo que hacía que
    cada reintento pagara de nuevo los pilares y otra llamada al modelo).
    """
    lines = []
    # El slice tiene que cubrir todos los pilares: si se corta por el final, el
    # último en concatenarse (contratación) nunca llega al modelo. Ver hallazgo
    # jul-2026: con [:14] nunca llegaba prensa. Pero con perfil de cliente los
    # pilares suman hasta 42 (cada uno con sus cupos de vigiladas) y mandarlas
    # todas encarece la generación sin agregar foco. Así que se PRIORIZA en vez
    # de truncar: primero todo lo que es sobre una vigilada, después lo de alta
    # prioridad, después el resto.
    orden = {'alto': 0, 'medio': 1, 'bajo': 2}
    # Lo que se movió en 72 h entra ANTES que lo alto-y-viejo: el briefing es de
    # hoy, y si el recorte deja fuera el único movimiento del día el modelo no
    # puede escribir la dirección que importa.
    top = sorted(senales, key=lambda x: (0 if x.get('mov') else 1,
                                         0 if x.get('vigilada') else 1,
                                         orden.get(x.get('nivel'), 3)))[:LECTURA_MAX_SENALES]
    # agrupadas por punto cardinal, que es como se va a escribir el briefing
    top.sort(key=lambda x: (('norte', 'este', 'sur', 'oeste').index(x.get('card', 'oeste')),
                            0 if x.get('mov') else 1))
    _card_actual = [None]
    for x in top:
        if x.get('card') != _card_actual[0]:
            _card_actual[0] = x.get('card')
            lines.append(f"\n### {CARD_LBL.get(_card_actual[0], _card_actual[0])}")
        x = dict(x, nivel=('[MOVIMIENTO ≤72h] ' if x.get('mov') else '[ESTADO] ') + str(x.get('nivel')))
        vig = f" · VIGILADA DEL CLIENTE: {x['vigilada']}" if x.get('vigilada') else ''
        if x['tipo'] == 'congreso':
            lines.append(f"- [LEGISLATIVO · prioridad {x['nivel']}] ({x['anio']}, "
                         f"{x.get('resultado_txt', x.get('resultado'))}) {x['titulo'][:95]}")
        elif x['tipo'] == 'medios':
            lines.append(f"- [PRENSA · prioridad {x['nivel']}{vig}] {x.get('fecha', '')} "
                         f"{x.get('medio', '')}: {x['titulo'][:90]}")
        elif x['tipo'] == 'contratacion':
            lines.append(f"- [CONTRATACIÓN · prioridad {x['nivel']}{vig}] {x.get('fecha', '')} "
                         f"{x.get('entidad', '')} → {x.get('proveedor', '')}: "
                         f"{(x.get('objeto') or '')[:80]}")
        else:
            lines.append(f"- [REGULATORIO · prioridad {x['nivel']}{vig}] {x.get('fecha', '')} "
                         f"{x.get('fuente', '')}: {x.get('sancionado', '')} — {x.get('motivo', '')[:75]}")
    vigiladas = ', '.join(e['nombre'] for e in s.get('empresas', []))
    quien = (f"Cliente: {s['nombre']}" if s.get('k') == 'perfil'
             else f"Cliente: sector {s['nombre']}")
    user = (quien
            + (f" (sus proyectos suelen ir a la Comisión {s['comision']})" if s.get('comision') else '')
            + ".\n"
            + (f"Temas que vigila: {', '.join(s.get('temas', []))}.\n" if s.get('temas') else '')
            + (f"Empresas que vigila: {vigiladas}. Las señales marcadas VIGILADA DEL "
               f"CLIENTE son sobre ellas — son las más importantes del briefing.\n"
               if vigiladas else '')
            + f"Radar de hoy: {kpis['n_radar']} señales priorizadas ({kpis['alto']} alta · "
            f"{kpis.get('medio', 0)} media prioridad) · {kpis['en_tramite']} proyectos de "
            f"ley EN TRÁMITE ACTIVO"
            + (f" · {kpis['n_sanciones_sector']} sanciones registradas del sector"
               if kpis.get('n_sanciones_sector') else '')
            + (f" · {kpis['n_medios_sector']} titulares de prensa recientes del sector"
               if kpis.get('n_medios_sector') else '') + ".\n\n"
            # Sin este recuento el modelo no puede distinguir "esta dirección no
            # trajo nada" de "no me la mandaste", y termina callándose el punto
            # en vez de reportar la quietud, que es justo lo que hay que decir.
            + "ESTADO DE LAS CUATRO DIRECCIONES (cuenta sobre TODO el radar, no "
              "solo lo que te mando abajo):\n"
            + '\n'.join(
                f"  · {CARD_LBL[c]}: {sum(1 for x in senales if x.get('card') == c)} señales, "
                f"{sum(1 for x in senales if x.get('card') == c and x.get('mov'))} de ellas "
                f"con movimiento en las últimas {MOV_DIAS*24} horas"
                + ("  ← SIN MOVIMIENTO: dilo explícito y describe cómo está el frente"
                   if not any(x.get('card') == c and x.get('mov') for x in senales) else '')
                for c in ('norte', 'este', 'sur', 'oeste')) + "\n\n"
            f"SEÑALES DEL RADAR (las priorizadas, no el histórico completo):\n"
            + '\n'.join(lines) + "\n\nEscribe el briefing en JSON.")
    return user


def _lectura_cliente_generar(key):
    """Genera la lectura de un radar ya calculado y la deja en el caché.

    Es lo ÚNICO lento del flujo del cliente: medido contra producción, la
    generación tarda entre 20 s y 51 s — la varianza es del modelo (1.3k vs
    3.7k tokens de razonamiento con el mismo prompt), así que no hay recorte de
    prompt que la meta bajo los 30 s del API Gateway de forma confiable. Por
    eso vive fuera de la acción `cliente` y se recoge por caché.
    """
    prompt = _cache_get('cliente-in-' + key)
    if not prompt or not prompt.get('user'):
        # el radar que la originó ya no está en caché (otra versión de prompt,
        # o el objeto se borró): que el frontend vuelva a pedir el radar.
        return {'estado': 'sin_radar'}
    lock = _cache_get('cliente-lock-' + key)
    if lock and _time.time() - float(lock.get('t') or 0) < LECTURA_LOCK_TTL:
        # ya hay una generación en vuelo. Sin este candado, cada reintento del
        # navegador arrancaba otra llamada de 50 s al modelo en paralelo.
        return {'estado': 'generando'}
    _cache_put('cliente-lock-' + key, {'t': _time.time()})
    try:
        raw = _call_llm('sintesis', CLIENTE_SYSTEM, prompt['user'], max_tokens=6000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'titular': '', 'lo_que_importa': '', 'acciones': [],
                'horizonte': '', 'error': str(e)[:200]}
    data['_model'] = STEP_MODELS['sintesis']['model']
    if 'error' not in data:
        _cache_put('cliente-' + key, data)
    return {'estado': 'lista', 'lectura': data}


# --- fase 3 · extracción del texto de una gaceta ----------------------------
GACETA_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy el TEXTO de una Gaceta del "
    "Congreso de Colombia (un boletín que puede traer varios documentos). "
    "Enfócate SOLO en el documento del proyecto indicado en el contexto. "
    "REGLA DURA: extrae únicamente lo que está en el texto; NO inventes nombres, "
    "fechas ni argumentos. Si algo no aparece, ponlo en null o lista vacía. "
    "Devuelves SIEMPRE un JSON válido con estas claves: tipo_documento (p.ej. "
    "'ponencia', 'acta de comisión', 'acta de plenaria'), "
    "ponentes (lista de nombres que firman), sentido (uno de: 'favorable', "
    "'archivo', 'mixto', 'desconocido' — ¿recomienda dar debate o archivar?), "
    "sentido_detalle (frase que lo justifica), argumentos (lista de 3-6 bullets "
    "con los argumentos centrales), en_contra (texto si hay ponencia de archivo "
    "u oposición explícita, si no null). SI EL DOCUMENTO ES UN ACTA de sesión, "
    "agrega además: aplazamiento (objeto {hubo: true/false, propuesto_por: nombre "
    "de quien propuso aplazar o null, detalle: frase}), y votacion (objeto "
    "{hubo: true/false, motivo: qué se votó, favor: nº, contra: nº, abstencion: "
    "nº, nominal: lista de {nombre, voto} SOLO si el acta trae el listado nominal "
    "de cada congresista, si no lista vacía}). Si no es acta o no hay votación/"
    "aplazamiento, esos objetos van con hubo:false."
)


def _ventana(texto, contexto, size=60000):
    """Actas de plenaria largas: el roll-call nominal vive DESPUÉS del preámbulo
    (asistencia/quórum), lejos de los primeros 60k. En vez de cortar por el
    inicio, centra la ventana en la votación relevante — ancla en las palabras
    distintivas del contexto y, si no, en la primera 'votación nominal'."""
    if len(texto) <= size:
        return texto
    low = texto.lower()
    anchor = -1
    # ancla SOLO en palabras distintivas (≥7 chars) — NO en números sueltos: un
    # número del contexto (nº de proyecto) aparece en cualquier parte del acta y
    # manda la ventana a un lugar sin votación.
    for tok in re.findall(r'[a-záéíóúñ]{8,}', (contexto or '').lower())[:8]:
        if tok in ('proyecto', 'senado', 'camara', 'plenaria', 'congreso', 'republica'):
            continue                     # palabras ubicuas en toda acta → no anclan
        p = low.find(tok)
        if p > size // 2:                # solo salta si el ancla está lejos del inicio
            anchor = p
            break
    if anchor < 0:
        for kw in ('votación nominal', 'votacion nominal', 'por el sí', 'por el si'):
            p = low.find(kw)
            if p >= 0:
                anchor = p
                break
    if anchor < 0:
        return texto[:size]
    start = max(0, anchor - 2500)        # un poco de contexto antes del voto
    return texto[start:start + size]


def _extraer_gaceta(key, contexto):
    """Lee gacetas-texto/{key}.txt de S3 y saca la estructura vía LLM (cache)."""
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key=f'gacetas-texto/{key}.txt')
        texto = obj['Body'].read().decode('utf-8', errors='replace')
    except Exception as e:
        return {'error': f'no hay texto de la gaceta {key} en S3: {str(e)[:120]}'}
    ck = _hash24(PROMPT_VERSION + '|gaceta|' + key + '|' + (contexto or ''))
    cached = _cache_get('gaceta-' + ck)
    if cached:
        return cached
    # el texto puede ser largo; recorta a ~60k chars (≈ una gaceta grande)
    user = (f"Contexto (proyecto de interés): {contexto or 'el proyecto principal del documento'}\n\n"
            f"TEXTO DE LA GACETA {key}:\n{_ventana(texto, contexto)}")
    try:
        raw = _call_llm('extraccion', GACETA_SYSTEM, user, max_tokens=6000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        return {'error': f'extracción falló: {str(e)[:160]}'}
    data['_model'] = STEP_MODELS['extraccion']['model']
    data['gaceta'] = key
    _cache_put('gaceta-' + ck, data)
    return data


# --- rastreo de medios (Serper/Google → controversia/impopularidad) ---------
import re

_TITULO_PREF = re.compile(
    r'^\s*por\s+(?:medio\s+de\s+|el\s+medio\s+de\s+)?(?:la|el|los|las)?\s*cual(?:es)?\s+se\s+',
    re.I)


def _query_medios(titulo, autor, anio, numero):
    """Arma una query de prensa desde la ficha (limpia el formulismo legal)."""
    t = _TITULO_PREF.sub('', titulo or '').strip()
    t = re.sub(r'\s+', ' ', t)[:90]
    partes = ['proyecto de ley', t]
    if numero:
        partes.append(str(numero))
    if anio:
        partes.append(str(anio))
    if autor:
        partes.append(autor.split()[0] if ' ' in autor else autor)
    partes.append('Colombia')
    return ' '.join(p for p in partes if p)


def _serper(q, num=10):
    key = os.environ.get('SERPER_API_KEY')
    if not key:
        raise RuntimeError('SERPER_API_KEY no configurada')
    body = json.dumps({'q': q, 'gl': 'co', 'hl': 'es', 'num': num}).encode('utf-8')
    req = urllib.request.Request('https://google.serper.dev/search', data=body,
                                 headers={'X-API-KEY': key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    out = []
    for o in d.get('organic', [])[:num]:
        out.append({'titulo': o.get('title', ''), 'url': o.get('link', ''),
                    'fuente': (o.get('link', '').split('/')[2] if '://' in o.get('link', '') else ''),
                    'fecha': o.get('date', ''), 'snippet': o.get('snippet', '')})
    return out


CTX_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy TITULARES DE PRENSA sobre un "
    "proyecto de ley/acto legislativo del Congreso de Colombia. Tu tarea: decir "
    "si el proyecto tuvo controversia, oposición pública o impopularidad que "
    "ayude a explicar su trámite (muchos se dejan caer por tiempo cuando se "
    "vuelven impopulares o un gremio los frena). Escribes en tuteo neutro de "
    "Bogotá. REGLA DURA: usa SOLO lo que dicen los titulares; si no hay señal "
    "clara, dilo (no inventes controversia). Devuelves SIEMPRE un JSON válido con "
    "las claves: tuvo_controversia ('si'|'no'|'sin_senal'), nivel "
    "('alta'|'media'|'baja'|'sin_senal'), resumen (2-4 frases), quien_se_opuso "
    "(lista de gremios/sectores/actores que aparezcan, o vacía), "
    "murio_por_impopularidad ('probable'|'poco_probable'|'sin_senal'), "
    "veredicto (1-2 frases). NO inventes URLs ni fechas: esas van aparte.")


def _contexto_medios(payload):
    titulo = payload.get('titulo', '')
    q = _query_medios(titulo, payload.get('autor'), payload.get('anio'),
                      payload.get('numero'))
    ck = _hash24(PROMPT_VERSION + '|contexto|' + str(payload.get('id')) + '|' +
                 str(payload.get('tb')) + '|' + titulo[:60])
    cached = _cache_get('contexto-' + ck)
    if cached:
        return cached
    try:
        fuentes = _serper(q)
    except Exception as e:
        return {'error': f'búsqueda no disponible: {str(e)[:140]}', 'query': q}
    if not fuentes:
        return {'query': q, 'tuvo_controversia': 'sin_senal', 'nivel': 'sin_senal',
                'resumen': 'No se encontró cobertura de prensa localizable para este '
                           'proyecto (frecuente en iniciativas anteriores a ~2010).',
                'quien_se_opuso': [], 'murio_por_impopularidad': 'sin_senal',
                'veredicto': '', 'fuentes': []}
    titulares_txt = '\n'.join(
        f"- [{f.get('fecha') or 's/f'}] {f.get('fuente')}: {f.get('titulo')} — {f.get('snippet','')[:160]}"
        for f in fuentes)
    user = (f"Proyecto: «{titulo}»\n"
            f"Resultado del trámite: {payload.get('resultado') or 's/d'}\n\n"
            f"TITULARES ENCONTRADOS:\n{titulares_txt}\n\n"
            "Analiza SOLO con base en estos titulares. Devuelve el JSON pedido.")
    try:
        raw = _call_llm('contexto', CTX_SYSTEM, user, max_tokens=3000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'tuvo_controversia': 'sin_senal', 'nivel': 'sin_senal', 'resumen': '',
                'quien_se_opuso': [], 'murio_por_impopularidad': 'sin_senal',
                'veredicto': '', 'error': str(e)[:160]}
    data['query'] = q
    data['fuentes'] = fuentes           # URLs/fechas REALES (no del LLM)
    data['_model'] = STEP_MODELS['contexto']['model']
    if 'error' not in data:
        _cache_put('contexto-' + ck, data)
    return data


# --- pilar Medios · prensa nacional y regional (Google News RSS · gratis) ---
# Mismo mecanismo que tools/radar-mujer-medios/collect.py (monitor de medios de
# Radar Mujer/MxD): Google News RSS es gratis, sin API key, y cubre TODO el
# ecosistema de prensa colombiano (nacional + regional) por query temática, sin
# mantener un conector por medio. Aquí se reusa para el pilar Medios de Caudal.
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import time as _time
from datetime import timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

MEDIOS_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# consultas amplias para el landing (sin tema puntual): pulso político/legislativo
# nacional. Se amplía fácil agregando más queries — cada una ya trae el ecosistema
# completo de medios que cubrió ese ángulo, gratis.
MEDIOS_LANDING_Q = [
    'Congreso de la República Colombia',
    'Gobierno Nacional Colombia',
    'Corte Constitucional Colombia',
    'reforma Colombia',
]

# medios regionales conocidos (forma "compacta": sin tildes/espacios/puntos) —
# match por substring sobre el nombre del medio que trae Google News. Lo que NO
# matchea cae a 'nacional' (la mayoría de la prensa digital colombiana es de
# alcance nacional) — no pretende ser exhaustivo, solo dar un desglose útil.
_MEDIOS_REGIONALES = [
    'elcolombiano', 'elmundo', 'minuto30', 'minuto60', 'vivirenelpoblado',
    'telemedellin', 'teleantioquia', 'elpais', 'qhubo', 'extra',
    'elheraldo', 'elmeridianodecordoba', 'diariolalibertad', 'eluniversal',
    'vanguardia', 'laopinion', 'lapatria', 'cronicadelquindio', 'elquindiano',
    'elnuevodia', 'diariodelhuila', 'llano7dias', 'elpilon',
    'hoydiariodelmagdalena', 'diariodelnorte', 'proclamadelcauca', 'latarde',
    'diariodelotun', 'diariodelcauca', 'telecaribe', 'telepacifico', 'citytv',
    'notipacifico', 'primiciadiario', 'hsbnoticias',
]

# plataformas sociales que Google News a veces manda como <source> cuando el
# resultado es un post/caption compartido, no una nota editorial (ej. un post
# de Facebook con texto largo). Se descartan ANTES de agregar — es justo el
# tipo de ruido que Caudal promete filtrar, no sumarlo junto a medios reales.
_MEDIOS_FUENTES_EXCLUIR = {
    'facebookcom', 'facebook', 'twittercom', 'twitter', 'xcom',
    'instagramcom', 'instagram', 'tiktokcom', 'tiktok', 'youtubecom',
    'youtube', 'threadsnet', 'threads', 'linkedincom', 'linkedin',
    'redditcom', 'reddit', 'tme', 'telegram', 'whatsappcom', 'whatsapp',
    'tco',
}

# TLDs comunes a recortar cuando Google News manda el dominio en vez de la
# marca como <source> (ver _medios_group_key). Ordenados de más largo a más
# corto para que '.com.co' se pruebe antes que '.co'.
_DOMAIN_TLDS_SORTED = sorted(
    ('com.co', 'com.mx', 'com.ar', 'com.ve', 'com.pe', 'com.ec', 'com',
     'co', 'net', 'org', 'info', 'tv', 'la', 'news'),
    key=len, reverse=True)

# fuentes institucionales (gobierno, entes de control, academia pública):
# Google News las trae como si fueran prensa independiente, pero un comunicado
# oficial no es "cobertura mediática" — mezclarlo con Infobae/El Tiempo infla
# la sensación de que hay ruido de prensa cuando en realidad es la propia
# entidad hablando de sí misma. Heurística no exhaustiva, mismo criterio que
# _MEDIOS_REGIONALES: palabra-raíz institucional sobre el nombre COMPACTO
# (sin puntos/espacios); el dominio .gov.co/.edu.co se chequea aparte, sobre
# el string crudo, porque _medios_compact() se come los puntos.
_MEDIOS_INSTITUCIONAL_RE = re.compile(
    r'gobernacion|alcaldia|ministerio|universidad|camaradecomercio'
    r'|personeria|contraloria|procuraduria|defensoria|^concejo|^asamblea'
    r'|^sena$|^dian$|presidenciadelarepublica|^super(intendencia|salud'
    r'|financiera|sociedades|transporte|servicios)|policianacional'
    r'|ejercitonacional|unidadnacional|agencianacional|registraduria')


def _medios_es_institucional(medio):
    if not medio:
        return False
    low = _medios_strip_accents(medio.lower())
    if low.endswith('.gov.co') or low.endswith('.edu.co'):
        return True
    return bool(_MEDIOS_INSTITUCIONAL_RE.search(_medios_compact(medio)))


def _medios_strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def _medios_norm(s):
    return re.sub(r'\s+', ' ', _medios_strip_accents((s or '').lower())).strip()


def _medios_compact(s):
    return re.sub(r'[^a-z0-9]', '', _medios_strip_accents((s or '').lower()))


def _medios_es_fuente_social(medio):
    return _medios_compact(medio) in _MEDIOS_FUENTES_EXCLUIR


def _medios_looks_domain(medio):
    return bool(medio) and '.' in medio and ' ' not in medio


def _medios_domain_slug(medio):
    """'elpais.com.co' -> 'elpais'; 'ElUniversal.com.co' -> 'eluniversal'."""
    s = medio.lower()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s)
    for tld in _DOMAIN_TLDS_SORTED:
        suf = '.' + tld
        if s.endswith(suf):
            return s[:-len(suf)]
    return s


def _medios_group_key(medio):
    """Llave de agrupación agnóstica de la FORMA en que llega el medio: Google
    News manda a veces el dominio ('elpais.com.co') y a veces la marca ('El
    País') como <source> para el MISMO periódico — sin esto, 'por_medio' infla
    el conteo de medios distintos con el mismo medio contado dos veces."""
    base = _medios_domain_slug(medio) if _medios_looks_domain(medio) else medio
    return _medios_compact(base)


def _medios_alcance(medio):
    c = _medios_compact(medio)
    return 'regional' if any(t in c for t in _MEDIOS_REGIONALES) else 'nacional'


_GN_SUFFIX_RE = re.compile(r'\s+-\s+([^-]+)$')


def _medios_split_title(title, source):
    """Título de Google News = 'Titular real - Nombre del Medio'."""
    if source:
        m = _GN_SUFFIX_RE.search(title)
        if m and _medios_norm(m.group(1)) == _medios_norm(source):
            return title[:m.start()].strip(), source
        return title, source
    m = _GN_SUFFIX_RE.search(title)
    if m:
        return title[:m.start()].strip(), m.group(1).strip()
    return title, None


def _medios_parse_date(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw.strip())
    except Exception:
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _medios_gn_url(q, dias):
    # `gl=CO` solo SESGA el resultado a Colombia, no lo restringe — términos
    # genéricos (p.ej. "sistema financiero", "salario minimo") matchean prensa
    # de cualquier país hispanohablante. Forzar "Colombia" en la query (si el
    # término no la trae ya) lo vuelve un AND real, sin tocar búsquedas ya
    # específicas ("seguridad Catatumbo", "reforma pensional Colombia"...).
    if 'colombia' not in q.lower():
        q = f'{q} Colombia'
    qq = f'{q} when:{dias}d' if dias else q
    qs = urllib.parse.urlencode({'q': qq, 'hl': 'es-419', 'gl': 'CO', 'ceid': 'CO:es'})
    return f'https://news.google.com/rss/search?{qs}'


def _medios_fetch_xml(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': MEDIOS_UA,
        'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
        'Accept-Language': 'es-CO,es;q=0.9'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def _medios_parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ch = root.find('channel')
    items = ch.findall('item') if ch is not None else root.findall('.//item')
    out = []
    for it in items:
        link = (it.findtext('link') or '').strip()
        if not link:
            continue
        src_el = it.find('source')
        source = src_el.text.strip() if src_el is not None and src_el.text else None
        out.append({'link': link, 'title': (it.findtext('title') or '').strip(),
                    'fecha_pub': _medios_parse_date(it.findtext('pubDate')), 'source': source})
    return out


def _medios_query_events(query, dias):
    try:
        items = _medios_parse_feed(_medios_fetch_xml(_medios_gn_url(query, dias)))
    except Exception as e:
        print(f'[medios] FAIL "{query}": {type(e).__name__}: {e}')
        return []
    events = []
    for it in items:
        titulo, medio = _medios_split_title(it['title'], it['source'])
        if not medio or _medios_es_fuente_social(medio) or _medios_es_institucional(medio):
            continue
        events.append({'medio': medio, 'alcance': _medios_alcance(medio), 'titulo': titulo,
                       'url': it['link'], 'fecha': (it['fecha_pub'] or '')[:10],
                       '_fp': it['fecha_pub'] or ''})
    return events


def _medios_aggregate(events, cap):
    # dedup por (titulo normalizado, LLAVE de medio) — no por el string crudo
    # del medio, que puede venir en dos formas distintas para el mismo outlet.
    seen, dedup = set(), []
    for e in events:
        e['_gk'] = _medios_group_key(e['medio'])
        k = (_medios_norm(e['titulo']), e['_gk'])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(e)
    dedup.sort(key=lambda e: e['_fp'], reverse=True)

    # nombre canónico por grupo: preferir la forma que NO parece dominio (la
    # marca real, 'El País') sobre 'elpais.com.co'; si todas las variantes del
    # grupo parecen dominio, usar la más frecuente tal cual.
    variantes = {}
    for e in dedup:
        variantes.setdefault(e['_gk'], Counter())[e['medio']] += 1
    canon = {}
    for gk, vc in variantes.items():
        marca = {m: n for m, n in vc.items() if not _medios_looks_domain(m)}
        pool = marca or vc
        canon[gk] = max(pool.items(), key=lambda kv: kv[1])[0]
    for e in dedup:
        e['medio'] = canon[e['_gk']]

    por_medio = Counter(e['medio'] for e in dedup)
    por_alcance = Counter(e['alcance'] for e in dedup)
    return {
        'n': len(dedup), 'n_medios': len(por_medio),
        'por_medio': [{'medio': m, 'n': n} for m, n in por_medio.most_common(20)],
        'por_alcance': [{'alcance': a, 'n': n} for a, n in por_alcance.most_common()],
        'resultados': [{k: v for k, v in e.items() if k not in ('_fp', '_gk')} for e in dedup[:cap]],
    }


def _medios_cache_bucket(hours=3):
    return int(_time.time() // (hours * 3600))


def _medios_landing():
    ck = f'medios-landing-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    events = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(_medios_query_events, q, 3) for q in MEDIOS_LANDING_Q]):
            events.extend(fut.result())
    out = dict(_medios_aggregate(events, cap=24), mode='landing')
    _cache_put(ck, out)
    return out


def _medios_buscar(query, dias):
    dias = dias or 30
    ck = f'medios-q-{_hash24(_medios_norm(query))}-{dias}-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    out = dict(_medios_aggregate(_medios_query_events(query, dias), cap=60),
               mode='search', query=query, dias=dias)
    _cache_put(ck, out)
    return out


def _medios_para_sector(temas, dias=14, cap=6):
    """Pulso de prensa para el Radar del cliente (Vista Cliente · SKU A): una
    query de Google News por cada tema del sector, en paralelo, con el mismo
    filtro de ruido y dedup del pilar Medios. Cache de 3h por combinación de
    temas (mismo criterio que _medios_landing/_medios_buscar)."""
    if not temas:
        return {'n': 0, 'resultados': []}
    ck = f'medios-sector-{_hash24("|".join(sorted(temas)))}-{dias}-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    events = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(_medios_query_events, t, dias) for t in temas]):
            events.extend(fut.result())
    out = _medios_aggregate(events, cap=cap)
    _cache_put(ck, out)
    return out


# --- bloque Regulatorio del Radar ------------------------------------------
# El pilar Regulatorio dejó de ser "sanciones" y pasó a ser "actos regulatorios"
# (`tipo_acto`), pero el Radar seguía mirando solo las sanciones. Con las supers
# clásicas eso daba igual —INVIMA, ANCP, Superfinanciera y Supertransporte casi
# solo publican sanciones, con nombre y fecha fresca— y con la ANLA se rompe:
# de sus 54.105 actos apenas 210 son 'sancion', SOLO 10 traen empresa (la última
# de 2010) y las otras 200 son "POR LA CUAL SE IMPONE UNA SANCIÓN AMBIENTAL" sin
# destinatario. La vida del expediente está en los otros 53.895: resoluciones,
# aperturas y archivos de 2026 contra Cerro Matoso, Chevron, Prodeco, Biomax.
# Llenar los 6 cupos solo con sanciones le habría mostrado al cliente minero
# seis tarjetas tituladas «—».
#
# Regla: seis señales, las más recientes primero, y SIEMPRE con destinatario —
# una tarjeta cuyo título entero es «—» no le dice nada a nadie. Las sanciones
# de los últimos 3 años mandan; si no llenan, entran los demás actos del sector;
# y solo al final las sanciones viejas. Para las 5 fuentes que ya funcionaban el
# resultado es el mismo de antes (verificado): sus sanciones recientes con
# nombre llenan los seis cupos y el resto de la cadena nunca se toca.
_REG_ACTO_LBL = {
    'sancion': 'Sanción', 'apertura_investigacion': 'Investigación abierta',
    'archivo': 'Archivo', 'resolucion': 'Resolución',
    'contribucion_especial': 'Contribución especial', 'otro': 'Acto administrativo',
}
_REG_ACCION = {
    'apertura_investigacion': ('Investigación abierta en tu sector — revisar si el hecho '
                               'imputado se parece a tu operación'),
    'archivo': ('Archivo del expediente — sirve de precedente sobre qué defensa le '
                'funcionó a otro en tu sector'),
    'resolucion': ('Acto de trámite del regulador en tu sector — revisar qué le exigió '
                   'y con qué plazo'),
    'contribucion_especial': 'Liquidación de la contribución del sector — verificar tu base',
    'otro': 'Actuación del regulador en tu sector — seguimiento',
}


def _reg_con_nombre(r):
    return (r.get('sancionado') or '').strip() not in ('', '—', '-', 'N/A')


def _bloque_regulatorio(dels, vig_keys, cap=6):
    """Las `cap` señales regulatorias del sector, ya priorizadas y redactadas."""
    corte = str(caudal_core.REF_YEAR - 3)
    es_sanc = lambda r: (r.get('tipo_acto') or 'sancion') == 'sancion'
    # El filtro de nombre aplica SOLO a las sanciones: una sanción sin
    # sancionado no sirve para nada. Un acto NORMATIVO —una circular, una
    # resolución de la UIAF— no tiene destinatario individual por definición, y
    # exigirle uno lo borraba del radar. Medido ago-2026: con las seis fuentes
    # normativas adentro, el perfil de Binance sumaba 798 actos al conteo y
    # mostraba CERO, porque todos traen `sancionado='—'`. El guion es el
    # marcador de ausencia de la fuente, no un nombre — y es truthy, así que un
    # `or` no lo atrapa (mismo tropiezo que ya había costado caro en alertas).
    utiles = [r for r in dels
              if (_reg_con_nombre(r) or not es_sanc(r))
              and (r.get('sancionado'), r.get('fecha'), r.get('resolucion'),
                   r.get('fuente')) not in vig_keys]
    utiles.sort(key=lambda r: r.get('fecha') or '', reverse=True)
    sanc_rec = [r for r in utiles if es_sanc(r) and (r.get('fecha') or '')[:4] >= corte]
    otros = [r for r in utiles if not es_sanc(r)]
    sanc_old = [r for r in utiles if es_sanc(r) and (r.get('fecha') or '')[:4] < corte]
    # Reparto: hasta la mitad del cupo para sanciones recientes y el resto para
    # la norma. Sin esto las sanciones —que son muchas y frescas— se comen el
    # bloque entero y la circular que le CREA la obligación al cliente no cabe.
    # Para un cliente vale más la norma que le habla a él que la multa que le
    # pusieron a un tercero de su sector.
    mitad = max(1, cap // 2)
    orden = sanc_rec[:mitad] + otros[:cap - mitad]
    orden += [r for r in (sanc_rec[mitad:] + otros[cap - mitad:] + sanc_old)
              if r not in orden]
    out = []
    for r in orden[:cap]:
        acto = r.get('tipo_acto') or 'sancion'
        yr = (r.get('fecha') or '')[:4]
        reciente = yr.isdigit() and int(yr) >= caudal_core.REF_YEAR - 1
        if acto == 'sancion':
            accion = ('Sanción reciente en tu sector — revisar exposición y activar '
                      'cumplimiento') if reciente else \
                     'Antecedente sancionatorio — referencia de riesgo del sector'
            # una sanción firme siempre pesa; los actos de trámite solo cuando
            # están frescos (un archivo de 2019 es doctrina, no alerta).
            nivel = 'alto' if reciente else 'medio'
        else:
            accion = _REG_ACCION.get(acto, _REG_ACCION['otro'])
            nivel = 'alto' if (reciente and acto == 'apertura_investigacion') else 'medio'
        # Sin destinatario real, el titular es el ACTO. Devolver un guion deja
        # una tarjeta en blanco en la pantalla del cliente, que es peor que no
        # mostrarla: parece un error nuestro.
        quien = r.get('sancionado') if _reg_con_nombre(r) else None
        out.append({'tipo': 'regulatorio', 'sancionado': quien,
                    'fuente': r.get('fuente_nombre'), 'tipo_sancion': r.get('tipo'),
                    'acto': acto, 'acto_lbl': _REG_ACTO_LBL.get(acto, _REG_ACTO_LBL['otro']),
                    'motivo': (r.get('motivo') or '')[:170], 'fecha': r.get('fecha'),
                    'monto': r.get('monto'), 'nivel': nivel, 'accion': accion})
    return out


SECOP_SECTOR_DIAS = 180


def _secop_para_sector(temas, cap=5):
    """Contratación del sector para el Radar del cliente (Vista Cliente · SKU A),
    espejo de `_medios_para_sector`: una búsqueda $q por tema, en paralelo.
    Solo filas (sin los agregados de total/departamento): acá interesa "qué se
    está contratando", no el universo.

    Ordena por VALOR dentro de una ventana reciente, no por fecha. Medido: con
    `$order=fecha DESC` lo que sale son las últimas prestaciones de servicios
    profesionales firmadas ese día — ruido para un cliente; con valor dentro de
    los últimos 180 días salen los contratos que mueven la aguja (p. ej. en
    salud, suministros de medicamentos de decenas de miles de millones).
    Cache de 3h por combinación de temas."""
    if not temas:
        return {'n': 0, 'resultados': []}
    temas = temas[:4]
    desde = _time.strftime('%Y-%m-%d',
                           _time.gmtime(_time.time() - SECOP_SECTOR_DIAS * 86400))
    ck = (f'secop-sector-{_hash24("|".join(sorted(temas)))}-{cap}'
          f'-{SECOP_SECTOR_DIAS}-{_medios_cache_bucket()}')
    cached = _cache_get(ck)
    if cached:
        return cached
    filas = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(_secop_get, {
            '$q': t, '$select': ','.join(SECOP_SELECT),
            '$where': f"fecha_de_firma > '{desde}'",
            '$order': 'valor_del_contrato DESC', '$limit': 5}, 14): t for t in temas}
        for fut in as_completed(futs):
            try:
                filas.extend(fut.result())
            except Exception as e:
                print(f'[secop] sector/{futs[fut]} FAIL: {type(e).__name__}: {e}')
    # dedup por contrato Y por (entidad, objeto, valor): una misma contratación
    # se publica repetida cuando son varios contratistas con el mismo objeto.
    vistos, out = set(), []
    for r in sorted(filas, key=lambda r: -float(r.get('valor_del_contrato') or 0)):
        k = (r.get('id_contrato'), r.get('nombre_entidad'),
             _secop_norm(r.get('objeto_del_contrato'))[:90], r.get('valor_del_contrato'))
        if k[0] in vistos or k[1:] in vistos:
            continue
        vistos.add(k[0])
        vistos.add(k[1:])
        out.append(_secop_row(r, [], SECOP_MATCH_FALLBACK))
    res = {'n': len(out), 'resultados': out[:cap], 'dias': SECOP_SECTOR_DIAS}
    _cache_put(ck, res)
    return res


# --- Perfil de cliente · la cara de IDENTIDAD sobre las empresas vigiladas ----
# El sector responde "qué se mueve alrededor de mi cliente"; las vigiladas
# responden "qué le está pasando a mi cliente (o a su competencia directa)".
# Son la señal más cara del radar, así que van en cupos propios y no compiten
# con las del sector.
PERFIL_EMP_SECOP   = 6     # empresas cuya razón social se descubre en SECOP
PERFIL_EMP_MEDIOS  = 5     # empresas que se buscan por nombre en prensa
PERFIL_MEDIOS_DIAS = 21    # prensa de vigiladas: ventana más larga que la del sector


def _regulatorio_para_empresas(emps, cap=6):
    """Sanciones cuyo destinatario ES una de las vigiladas (identidad, no tema).
    Filtro por palabra completa + vetos del diccionario — el mismo gate que usa
    el pilar Regulatorio, así que hereda su precisión medida."""
    if not emps:
        return []
    por_emp = {}
    for r in _sanciones():
        nombre = r.get('sancionado') or ''
        if not nombre:
            continue
        for e in emps:
            if empresas.casa_registro(e, nombre):
                por_emp.setdefault(e['nombre'], []).append(r)
                break
    for v in por_emp.values():
        v.sort(key=lambda r: r.get('fecha', '') or '', reverse=True)
    # round-robin: una vigilada con 40 sanciones no puede acaparar el panel y
    # dejar sin ver a las otras. Se muestra la más reciente de cada una, luego
    # la segunda de cada una, y así.
    out, i = [], 0
    while len(out) < cap and any(len(v) > i for v in por_emp.values()):
        for quien, v in por_emp.items():
            if i < len(v) and len(out) < cap:
                out.append((quien, v[i]))
        i += 1
    return out


def _medios_para_empresas(emps, cap=5):
    """Prensa que nombra a las vigiladas. Ventana más larga que la del sector:
    que salga tu empresa en un titular es raro y sigue siendo noticia a 3
    semanas. Devuelve [(nombre_vigilada, evento)]."""
    emps = emps[:PERFIL_EMP_MEDIOS]
    if not emps:
        return []
    nombres = [e['nombre'] for e in emps]
    agg = _medios_para_sector(nombres, dias=PERFIL_MEDIOS_DIAS, cap=cap * 4)
    out, vistos = [], set()
    for r in agg.get('resultados', []):
        titulo = r.get('titulo') or ''
        hit = next((e['nombre'] for e in emps if empresas.casa_registro(e, titulo)), None)
        # sin hit el titular salió por la búsqueda pero no nombra a la vigilada
        # como palabra completa → es homónimo o ruido; no se cuela como "tu empresa".
        if not hit:
            continue
        # el dedup del pilar Medios es por (título, medio) — a propósito, ahí
        # interesa cuántos medios lo cubren. Acá no: la misma nota replicada por
        # 4 outlets es UNA señal para el cliente, no cuatro.
        k = _medios_norm(titulo)[:90]
        if k in vistos:
            continue
        vistos.add(k)
        out.append((hit, r))
        if len(out) >= cap:
            break
    return out


def _secop_para_empresas(emps, cap=5):
    """Contratos que SON de las vigiladas (proveedor o entidad), por identidad.

    Una sola ronda de descubrimiento para todas (un alias por empresa) y un
    único `in (…)` — hacer una ronda por empresa serían ~6 llamadas a Socrata
    cada una y no cabe en el techo de 30 s de API Gateway.
    """
    emps = emps[:PERFIL_EMP_SECOP]
    if not emps:
        return {'n': 0, 'resultados': []}
    terms = []
    for e in emps:
        a = min(e['alias'], key=len) if e['alias'] else e['k']
        if a not in terms:
            terms.append(a)
    ck = (f'secop-vigiladas-{_hash24("|".join(sorted(terms)))}-{cap}'
          f'-{_medios_cache_bucket()}')
    cached = _cache_get(ck)
    if cached:
        return cached
    prov, ent, _desc = _secop_descubrir('', emps, terms=terms)
    if not prov and not ent:
        # honesto: las vigiladas existen en el diccionario pero no le venden al
        # Estado. No se cae a $q en silencio — eso devolvería homónimos.
        res = {'n': 0, 'resultados': [], 'sin_contratos': True}
        _cache_put(ck, res)
        return res
    conds = []
    if prov:
        conds.append(_secop_in('proveedor_adjudicado', prov))
    if ent:
        conds.append(_secop_in('nombre_entidad', ent))
    w = '(' + ' OR '.join(conds) + ')'
    filas = _secop_get({'$select': ','.join(SECOP_SELECT),
                        '$where': w + ' AND fecha_de_firma IS NOT NULL',
                        '$order': 'fecha_de_firma DESC', '$limit': cap}, 14)
    tot = 0
    try:
        t = _secop_get({'$select': 'count(1) as n', '$where': w}, 14)
        tot = int((t[0] if t else {}).get('n') or 0)
    except Exception as e:
        print(f'[secop] vigiladas/total FAIL: {type(e).__name__}: {e}')
    out = []
    for r in filas:
        row = _secop_row(r, [], SECOP_MATCH_FALLBACK)
        quien = next((e['nombre'] for e in emps
                      if empresas.casa_registro(e, row.get('proveedor') or '')
                      or empresas.casa_registro(e, row.get('entidad') or '')), None)
        out.append((quien, row))
    res = {'n': tot or len(out), 'resultados': out}
    _cache_put(ck, res)
    return res


# --- handler ----------------------------------------------------------------
CORS = {'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'}



def _fold_q(s):
    """Minúsculas y sin tildes — la MISMA regla con la que build_s3 y los
    harvesters construyen el blob `q`. Si las dos mitades no coinciden, la
    búsqueda miente: medido ago-2026, «régimen cambiario» devolvía 3.764 actos
    y «regimen cambiario» devolvía cero, y el cliente escribe sin tildes.

    Se pliega la CONSULTA (una cadena) y no los blobs (81k): plegar los blobs en
    caliente cuesta 2,87 s por petición."""
    return ''.join(c for c in _unicodedata.normalize('NFD', (s or '').strip().lower())
                   if _unicodedata.category(c) != 'Mn')

def _resp(code, payload):
    return {'statusCode': code, 'headers': CORS,
            'body': json.dumps(payload, ensure_ascii=False)}


# ── La puerta de las acciones que cuestan plata ───────────────────────────────
# De las 23 acciones, 19 solo leen índices de S3: cuestan centavos y son la parte
# que Caudal REGALA (buscar, conteos, embudo, bloqueo, sectores, autocompletar).
# Las otras cuatro llaman al modelo —síntesis del tema, lectura del radar,
# lectura de gaceta— o a Serper —rastreo de medios, con cupo de 2.500 consultas
# gratis al mes—. Esas viven del lado del muro.
#
# ⚠️ Hasta ago-2026 esta Lambda no validaba NADA y su URL está escrita en
# caudal.html, que vive en un repo público: cualquiera podía quemar DeepSeek y
# Serper. Peor, `tema` traía `lectura` en True por defecto, así que una sola
# petición anónima disparaba dos llamadas al modelo. El gate de caudal.html
# nunca protegió la API — solo escondía la página.
#
# La credencial la pone el worker de Cloudflare (ruta `/caudal/api`), que es
# quien sabe si el visitante tiene acceso. Un navegador NO puede falsificarla:
# un header propio dispara preflight y CORS aquí solo admite Content-Type.
# Contra un cliente que no sea navegador, lo que protege es el secreto.
ORIGEN_HEADER  = 'x-caudal-origin'
ACCIONES_CARAS = frozenset({'gaceta', 'contexto', 'cliente-lectura', 'tema-lectura'})


def _con_credencial(event):
    """True si la petición trae el secreto compartido con el worker.

    ⚠️ Sin `CAUDAL_ORIGIN_SECRET` en el entorno devuelve True a propósito: así
    desplegar el código y sembrar el secreto pueden ir en corridas distintas sin
    dejar la Lambda muerta en el intermedio. La puerta se cierra sola al sembrar
    el secreto — si nunca se siembra, esto no protege nada."""
    esperado = os.environ.get('CAUDAL_ORIGIN_SECRET', '')
    if not esperado:
        return True
    # API Gateway entrega los headers en minúsculas, pero no depender de eso
    # sale gratis.
    dado = ''
    for k, v in (event.get('headers') or {}).items():
        if str(k).lower() == ORIGEN_HEADER:
            dado = str(v or '')
            break
    from hmac import compare_digest
    return bool(dado) and compare_digest(dado, esperado)


def handler(event, context):
    if (event.get('requestContext', {}).get('http', {}).get('method')
            or event.get('httpMethod')) == 'OPTIONS':
        return {'statusCode': 204, 'headers': CORS, 'body': ''}
    try:
        body = json.loads(event.get('body') or '{}')
    except Exception:
        return _resp(400, {'error': 'body no es JSON'})

    action = body.get('action', 'tema')
    # El rechazo va ANTES de _caudal(): decir que no no debe costar cargar los
    # ~80 MB de índices en un arranque en frío.
    autorizado = _con_credencial(event)
    if action in ACCIONES_CARAS and not autorizado:
        return _resp(403, {'error': 'accion_restringida', 'accion': action,
                           'detalle': 'Esta lectura pertenece a la versión con acceso.'})
    caudal = _caudal()

    if action == 'buscar':
        q = body.get('query', '')
        # expansión IA opt-in aquí (la vista de lista se usa también para
        # filtros internos, donde el literal es lo que se espera).
        extra = (_expandir_query(q, solo_cache=not autorizado)
                 if body.get('expandir_ia') else [])
        # relajar=True (③): consultas de varias palabras no colapsan por AND; anclan
        # al término más específico y rankean por nº de coincidencias.
        hits, meta = caudal.buscar(q, anio_min=body.get('anio_min'),
                                   anio_max=body.get('anio_max'),
                                   comision=body.get('comision'),
                                   resultado=body.get('resultado'),
                                   tipologia=body.get('tipologia'),
                                   empuje=body.get('empuje'),
                                   limit=body.get('limit', 50),
                                   extra_terms=extra, relajar=True, with_meta=True)
        rel = (meta or {}).get('relajado')
        flex = None
        if rel and rel.get('n_total', 0) > rel.get('n_estricto', 0):
            flex = {'anchor': rel['anchor'], 'n_estricto': rel['n_estricto'],
                    'n_total': rel['n_total']}
        return _resp(200, {'query': q, 'n': len(hits), 'resultados': hits,
                           'expansion': {'terminos': extra} if extra else None,
                           'flexible': flex})

    if action == 'snippets':
        # fragmento del cuerpo de gaceta donde aparece la palabra, para los match
        # ◈ "en el texto" — le deja al usuario chequear si el proyecto le sirve sin
        # abrir la ficha. Lazy: el frontend lo pide solo para los que muestra.
        q = body.get('query', '')
        items = (body.get('ids') or [])[:body.get('max', 50)]
        terms = caudal.snippet_terms(q)
        full = _full()

        def _one(item):
            tb, pid = item.get('tb', 'pdly'), item.get('id')
            base = {'id': pid, 'tb': tb}
            rec = full.get(f"{tb}:{pid}")
            if not rec or not terms:
                return {**base, 'snippet': None}
            for g in rec.get('gacetas', []):
                gk = g.get('gaceta')
                if not gk or g.get('tipo') == 'exposicion_motivos':
                    continue
                try:
                    obj = _s3.get_object(Bucket=BUCKET, Key=f"gacetas-texto/{gk.replace('/', '-')}.txt")
                    txt = obj['Body'].read().decode('utf-8', 'replace')
                except Exception:
                    continue
                sn = caudal.make_snippet(txt, terms)
                if sn:
                    return {**base, 'gaceta': gk, 'tipo': g.get('tipo'), **sn}
            return {**base, 'snippet': None}

        with ThreadPoolExecutor(max_workers=8) as ex:
            out = list(ex.map(_one, items))
        return _resp(200, {'snippets': out})

    if action == 'stats':          # agregados globales precalculados (para gráficas)
        try:
            return _resp(200, _get_json('metadata/stats.json'))
        except Exception as e:
            return _resp(500, {'error': f'no se pudo leer stats: {str(e)[:120]}'})

    if action == 'articulado':
        # QUÉ DICE el articulado. Sin `id` devuelve la cobertura (cuántos
        # proyectos tienen el texto leído, de qué base salió y qué campos
        # rindieron) — el dato honesto de hasta dónde llega la extracción.
        pid = body.get('id')
        if pid is not None:
            art = _articulado_de(body.get('tb', 'pdly'), pid)
            if not art:
                return _resp(404, {'error': 'sin extracción para este proyecto',
                                   'extraido': False})
            return _resp(200, dict(art, extraido=True))
        d = _articulado()
        return _resp(200, {'v': d.get('v'), 'pv': d.get('pv'), 'model': d.get('model'),
                           'n': d.get('n', 0), 'stats': d.get('stats', {}),
                           'por_sector': {k: len(v) for k, v in (d.get('por_sector') or {}).items()}})

    if action == 'importancia':
        # POR QUÉ IMPORTA — tres coordenadas, no un score. Ver
        # tools/caudal/importancia/README.md.
        #   {action:'importancia'}                       → metadatos del modelo
        #   {action:'importancia', id:9934, tb:'pdly'}   → coordenadas de uno
        #   {action:'importancia', lente:'riesgo', perfil:{…}} → ranking
        try:
            imp = _importancia()
        except Exception as e:
            return _resp(503, {'error': f'modelo de importancia no disponible: {str(e)[:120]}'})
        if imp is None:
            return _resp(503, {'error': 'modelo de importancia no cargado'})

        lentes = {k: dict(v) for k, v in _ejes.LENTES.items()}
        pid = body.get('id')
        if pid is not None:
            rec = _full().get(f"{body.get('tb', 'pdly')}:{int(pid)}")
            if not rec:
                return _resp(404, {'error': 'proyecto no encontrado'})
            return _resp(200, {'coordenadas': _coords_de(rec, imp, body.get('perfil')),
                               'modelo': imp['modelo'].meta, 'lentes': lentes})

        lente = str(body.get('lente') or '').strip()
        if not lente:
            return _resp(200, {
                'modelo': imp['modelo'].meta, 'lentes': lentes,
                'pesos_impacto': _ejes.IMPACTO_PESOS,
                'pesos_politico': _ejes.POLITICO_PESOS,
                'legislatura': IMPORTANCIA_LEG,
                'n_evaluables': len(_viva_recs()),
                # La salida pública del eje 1 es la BANDA. El modelo ordena
                # mejor de lo que calibra (decil alto: predice 0,69 y observa
                # 0,57) y la isotónica no lo endereza, solo mueve el error de
                # sitio. Cada banda viaja con la tasa REAL que tuvo en el test
                # out-of-time, que es lo que sí se sostiene.
                'bandas': [{'banda': n, 'desde': c, 'llegaron_a_ley_pct': o}
                           for c, n, o in _ejes.BANDAS],
                'nota_bandas': ('use la banda, no el porcentaje: los porcentajes '
                                'de cada banda son la tasa observada 2015-2024')})
        if lente not in lentes:
            return _resp(400, {'error': f'lente desconocido: {lente}',
                               'lentes': sorted(lentes)})
        perfil = body.get('perfil') or None
        items = [_coords_de(r, imp, perfil) for r in _viva_recs()]
        res = _ejes.ordenar(items, lente)
        lim = max(1, min(int(body.get('limit') or 20), 100))
        return _resp(200, {
            'lente': lente, 'meta': lentes[lente],
            'legislatura': IMPORTANCIA_LEG,
            'ranking': res['ranking'][:lim],
            # los tres bloques viajan siempre: un lente no puede desaparecer
            # proyectos en silencio, y "no lo hemos leído" no es "no te toca"
            'pendientes': res['pendientes'][:lim],
            'n_pendientes': len(res['pendientes']),
            'n_fuera': len(res['fuera']),
            'nota_pendientes': ('de estos solo tenemos el título: su impacto sería '
                                'un piso, no una medida, así que van aparte'),
            'modelo': imp['modelo'].meta})

    if action == 'bloqueo':        # sistema de bloqueo (posición, hazard, comisiones)
        _bl = _bloqueo()
        out = dict(_bl.get('sistema', {}))
        # Bloque de SENADO (aditivo): va anidado, NO fusionado con el de Cámara.
        # Son dos colas distintas y su numeración de proyectos se repite entre
        # cámaras, así que mezclarlas sumaría proyectos que no tienen relación.
        sen = _bl.get('senado')
        if sen:
            out['senado'] = {'sistema': sen.get('sistema', {}),
                             'fuente': sen.get('fuente', ''),
                             'alcance': sen.get('alcance', '')}
        return _resp(200, out)

    if action == 'bancadas':       # disciplina de bancada (cohesión · alineación · disidentes)
        # Las dos cámaras van SEPARADAS a propósito: cubren periodos distintos,
        # el Senado no registra abstención y su volumen de votaciones
        # contestadas es un orden de magnitud menor. Promediarlas mentiría.
        d = _bancadas()
        cam = body.get('camara')
        if cam in ('camara', 'senado'):
            return _resp(200, {'meta': d.get('meta', {}), cam: d.get(cam, {})})
        return _resp(200, d)

    if action == 'proyecto':
        pid = body.get('id')
        caudal._full = _full()          # inyecta registros completos (keyed tb:id)
        ficha = caudal.proyecto(pid, body.get('tb', 'pdly'))
        if not ficha:
            return _resp(404, {'error': f'proyecto {pid} no encontrado'})
        # bloqueo por número Cámara (órdenes del día de comisión + plenaria:
        # la entrada trae `plen` cuando también estuvo en la cola de plenaria)
        tok_c = _num_token(ficha.get('numero_camara'))
        if tok_c:
            bl = _bloqueo().get('por_proyecto', {}).get(tok_c)
            if bl:
                ficha['bloqueo'] = bl
        # bloqueo en SENADO (aditivo, campo aparte): se busca por el número de
        # SENADO contra el índice de Senado. Nunca contra `por_proyecto` de
        # Cámara: el mismo token existe en ambas cámaras para proyectos
        # distintos (1.012 casos medidos), así que cruzarlos daría un dato falso.
        tok_sen = _num_token(ficha.get('numero_senado'))
        if tok_sen:
            bls = (_bloqueo().get('senado', {}).get('por_proyecto', {}) or {}).get(tok_sen)
            if bls:
                ficha['bloqueo_senado'] = bls
        # outcome (Congreso Visible): match por número Senado o Cámara
        vp = _votaciones().get('por_proyecto', {})
        for tk in (_num_token(ficha.get('numero_senado')), tok_c):
            if tk and tk in vp:
                ficha['votaciones'] = vp[tk]
                break
        # voto NOMINAL de plenaria Cámara (aditivo): match por número Cámara
        if tok_c:
            vn = _votaciones_nominal().get('por_proyecto', {}).get(tok_c)
            if vn:
                ficha['voto_nominal'] = vn
        # voto NOMINAL de plenaria SENADO (aditivo · API app.senado.gov.co):
        # match por número Senado. Un proyecto puede traer los dos.
        tok_s = _num_token(ficha.get('numero_senado'))
        if tok_s:
            vs = _votaciones_senado_nominal().get('por_proyecto', {}).get(tok_s)
            if vs:
                ficha['voto_nominal_senado'] = vs
        # QUÉ CAMBIA esta ley (aditivo): extracción del articulado. Si el
        # proyecto todavía no está extraído, el campo no viaja y la ficha lo
        # dice — nunca se rellena con inferencia del título.
        art = _articulado_de(ficha.get('tabla', 'pdly'), ficha['id'])
        if art:
            ficha['articulado'] = art
        return _resp(200, ficha)

    if action == 'congresista':
        # récord de voto de una persona. {key} exacto (click-through) o {q}/{nombre}
        # (nombre tecleado o clickeado, resuelto por subconjunto de tokens).
        q = (body.get('key') or body.get('q') or body.get('nombre') or '').strip()
        if not q:
            return _resp(400, {'error': 'falta key/q/nombre del congresista'})
        key, cands = _resolver_congresista(q)
        if key:
            rec = _rec_congresista(key) or {}
            return _resp(200, dict(rec, key=key, encontrado=True))
        if cands:   # ambiguo: devolver candidatos para desambiguar
            out = []
            for k in cands:
                r = _rec_congresista(k) or {}
                out.append({'key': k, 'nombre': r.get('nombre', k.title()),
                            'bancada': r.get('bancada'), 'camara': r.get('camara'),
                            'n_votos': r.get('n_votos')})
            return _resp(200, {'encontrado': False, 'candidatos': out})
        return _resp(404, {'encontrado': False, 'error': f'sin récord de voto para «{q}»'})

    if action == 'citaciones':
        # control político: quién cita, a quién y sobre qué. Sin `q` devuelve el
        # panorama (cobertura declarada + rankings); con `q` filtra por citado o
        # por tema. La cobertura viaja siempre: hay comisiones que no publican
        # control político en su agenda y "0" no puede leerse como "no citó".
        d = _citaciones()
        sis = d.get('sistema', {})
        q = (body.get('q') or '').strip()
        if not q:
            return _resp(200, {'meta': d.get('meta', {}), 'sistema': sis})
        ql = _secop_norm(q)
        hits, vistos = [], set()
        for rk, p in d.get('por_congresista', {}).items():
            for c in p.get('citaciones', []):
                if c['k'] in vistos:
                    continue
                blob = _secop_norm(' '.join(
                    [c.get('tema') or ''] +
                    [(x.get('nombre') or '') + ' ' + (x.get('cargo') or '')
                     for x in c.get('citados', [])]))
                if ql in blob:
                    vistos.add(c['k'])
                    hits.append(dict(c, citantes=[]))
        por_k = {}
        for rk, p in d.get('por_congresista', {}).items():
            for c in p.get('citaciones', []):
                if c['k'] in vistos:
                    por_k.setdefault(c['k'], []).append(
                        {'rk': rk, 'nombre': p.get('nombre'), 'bancada': p.get('bancada')})
        for h in hits:
            h['citantes'] = por_k.get(h['k'], [])
        hits.sort(key=lambda h: (h.get('primera') or ''), reverse=True)
        return _resp(200, {'meta': d.get('meta', {}), 'q': q,
                           'n': len(hits), 'citaciones': hits[:80],
                           'cobertura': sis.get('cobertura', [])})

    if action == 'radicados':
        # proyectos recién radicados de la legislatura viva + descarga (PDF/texto).
        # Fuente: rastreo diario de leyes.senado.gov.co (harvest_diario). Cada
        # proyecto trae encabezado + tipología + intentos previos + URLs firmadas.
        leg = body.get('legislatura', '2026-2027')
        rows = _radicados(leg)
        out = []
        for r in rows:
            num = r.get('numero_senado', '') or ''
            fname = f"PL {num.replace('/', '-')} - texto radicado.pdf" if num else 'texto-radicado.pdf'
            out.append({
                'numero_senado': num,
                'numero_camara': r.get('numero_camara', ''),
                'comision': r.get('comision', ''),
                'fecha': r.get('fecha_de_presentacion', ''),
                'titulo': r.get('titulo', ''),
                'autor': r.get('autor', ''),
                'estado': r.get('estado', ''),
                'tipo_de_ley': r.get('tipo_de_ley', ''),
                'origen': r.get('origen', ''),
                'tipologia': r.get('tipologia'),
                'crea_fondo': r.get('crea_fondo', False),
                'intentos_previos': r.get('intentos_previos', 0),
                'intentos_previos_detalle': r.get('intentos_previos_detalle', []),
                'pdf_url': _presign(r.get('s3_pdf'), fname),
                'txt_url': _presign(r.get('s3_txt')),
                'fuente_url': r.get('texto_radicado_url', ''),
            })
        # lo más nuevo primero (número de senado desc)
        out.sort(key=lambda x: int((x['numero_senado'] or '0/0').split('/')[0]), reverse=True)

        # Cámara (Gaceta como texto radicado; s3_* None si aún no publicada)
        cam = []
        for r in _radicados_camara(leg):
            num = r.get('numero_camara', '') or ''
            autores = r.get('autores') or []
            comis = r.get('comisiones') or []
            gac = (r.get('gacetas') or [{}])[0]
            fname = f"PLC {num.replace('/', '-')} - texto radicado.pdf" if num else 'texto-radicado.pdf'
            cam.append({
                'camara': True,
                'numero_camara': num,
                'numero_senado': r.get('numero_senado', '') or '',
                'comision': (comis[0].get('nombre') if comis else '') or '',
                'titulo': r.get('titulo', ''),
                'autor': ', '.join(a.get('nombre', '') for a in autores) if autores else '',
                'estado': r.get('estado', ''),
                'tipo_de_ley': r.get('tipo', ''),
                'origen': r.get('origen', ''),
                'gaceta': r.get('gaceta_radicado') or gac.get('key', ''),
                'gaceta_pendiente': r.get('gaceta_pendiente', False),
                'pdf_url': _presign(r.get('s3_pdf'), fname),
                'txt_url': _presign(r.get('s3_txt')),
                'fuente_url': f"https://www.camara.gov.co/{r.get('link_web','')}" if r.get('link_web') else '',
            })
        cam.sort(key=lambda x: int((x['numero_camara'] or '0/0').split('/')[0]), reverse=True)

        return _resp(200, {'legislatura': leg, 'n': len(out), 'radicados': out,
                           'n_camara': len(cam), 'radicados_camara': cam})

    if action == 'gaceta':
        key = body.get('key')          # ej '857-2013'
        if not key:
            return _resp(400, {'error': 'falta key de gaceta (num-año)'})
        return _resp(200, _extraer_gaceta(key, body.get('contexto', '')))

    if action == 'contexto':           # rastreo de medios de un proyecto
        if not body.get('titulo'):
            return _resp(400, {'error': 'falta titulo del proyecto'})
        return _resp(200, _contexto_medios(body))

    if action == 'sanciones':      # pilar Regulatorio · actos de superintendencias
        q = _fold_q(body.get('query'))   # misma regla que el blob: sin tildes
        sector = body.get('sector') or ''
        # reencuadre jul-2026: el pilar cubre TODOS los actos regulatorios, pero
        # la vista por defecto sigue siendo solo sanciones — meter aperturas y
        # contribuciones sin pedirlo diluiría lo que hoy ve el cliente.
        # tipo_acto: '' → sanciones · 'todo' → universo · un tipo concreto → ese.
        tipo_acto = (body.get('tipo_acto') or '').strip().lower() or 'sancion'
        if not q and not sector and tipo_acto == 'sancion':
            return _resp(200, dict(_sanciones_stats(), mode='stats'))
        recs = _sanciones()
        if tipo_acto != 'todo':
            # los registros viejos (pre-reencuadre) no traen tipo_acto → sanción
            recs = [r for r in recs if (r.get('tipo_acto') or 'sancion') == tipo_acto]
        # ④ si la consulta nombra una empresa, el match NO puede ser el substring
        # sobre el blob `q`: 'uber' así trae "UBERNETH URANGO" y "YUBER CALIXTO",
        # 'claro' trae "PESQUERA RIO CLARO". Se matchea la IDENTIDAD (razón social
        # + alias) por palabra completa y SOLO contra el campo `sancionado`, que
        # es donde vive la entidad (el blob incluye el motivo y mete ruido).
        emps = empresas.empresas_en(body.get('query') or '')
        hits = [r for r in recs
                if (not sector or r.get('sector') == sector)
                and (not q
                     or (empresas.casa_registro_any(emps, r.get('sancionado', ''))
                         if emps else q in r.get('q', '')))]
        secc = Counter(r.get('sector', '') for r in hits)
        fuc = Counter(r.get('fuente_nombre', '') for r in hits)
        tac = Counter((r.get('tipo_acto') or 'sancion') for r in hits)
        montos = [r['monto'] for r in hits if r.get('monto')]
        hits_sorted = sorted(hits, key=lambda r: r.get('fecha', ''), reverse=True)
        out = [{k: v for k, v in r.items() if k != 'q'} for r in hits_sorted[:120]]
        # cuántos actos NO-sanción quedaron fuera con el filtro por defecto: el
        # frontend lo usa para ofrecer el toggle sin mentir sobre el universo.
        otros = 0
        if tipo_acto == 'sancion':
            otros = sum(1 for r in _sanciones()
                        if (r.get('tipo_acto') or 'sancion') != 'sancion'
                        and (not sector or r.get('sector') == sector)
                        and (not q
                             or (empresas.casa_registro_any(emps, r.get('sancionado', ''))
                                 if emps else q in r.get('q', ''))))
        return _resp(200, {
            'mode': 'search', 'query': body.get('query', ''), 'sector': sector,
            'tipo_acto': tipo_acto,
            'n': len(hits), 'mostrados': len(out),
            'otros_actos': otros,
            'por_sector': [{'sector': s, 'n': n} for s, n in secc.most_common()],
            'por_fuente': [{'fuente': f, 'n': n} for f, n in fuc.most_common()],
            'por_tipo_acto': [{'tipo_acto': t, 'n': n} for t, n in tac.most_common()],
            'monto_total_cop': round(sum(montos)) if montos else 0,
            'con_monto': len(montos),
            'empresas': _empresas_payload(emps),
            'resultados': out,
        })

    if action == 'ejecutivo':      # pilar Ejecutivo Nacional · decretos y normativa de Presidencia
        q = _fold_q(body.get('query'))   # misma regla que el blob: sin tildes
        tipo = (body.get('tipo') or '').strip().upper()
        if not q and not tipo:                 # landing: agregados precalculados (rápido)
            return _resp(200, dict(_ejecutivo_stats(), mode='stats'))
        recs = _ejecutivo()
        # ④ el Ejecutivo tampoco nombra marcas: regula la actividad. Si la
        # consulta es una empresa, se busca su vocabulario de núcleo (OR) además
        # del nombre literal — que igual puede aparecer en un decreto puntual.
        emps = empresas.empresas_en(body.get('query') or '')
        vocab = _vocab_empresa(emps, bool(body.get('ampliar_empresa')))
        hits = [r for r in recs
                if (not tipo or (r.get('tipo') or '').upper() == tipo)
                and (not q
                     or q in r.get('q', '')
                     or (vocab and any(v in empresas._n(r.get('q', '')) for v in vocab)))]
        tic = Counter((r.get('tipo') or '—') for r in hits)
        hits_sorted = sorted(hits, key=lambda r: r.get('fecha', ''), reverse=True)
        out = [{k: v for k, v in r.items() if k != 'q'} for r in hits_sorted[:120]]
        return _resp(200, {
            'mode': 'search', 'query': body.get('query', ''), 'tipo': tipo,
            'n': len(hits), 'mostrados': len(out),
            'por_tipo': [{'tipo': t, 'n': n} for t, n in tic.most_common()],
            'empresas': _empresas_payload(emps),
            'resultados': out,
        })

    if action == 'sucop':          # pilar SUCOP · borradores de norma en consulta pública
        q = _fold_q(body.get('query'))   # misma regla que el blob: sin tildes
        estado = (body.get('estado') or '').strip().lower()
        entidad = (body.get('entidad') or '').strip().lower()
        sector = (body.get('sector') or '').strip().lower()
        tipo = (body.get('tipo') or '').strip().lower()      # norma | agenda
        if estado and estado not in SUCOP_ESTADOS and estado != 'abiertas':
            return _resp(400, {'error': f'estado no válido: {estado}',
                               'validos': list(SUCOP_ESTADOS) + ['abiertas']})

        recs = _sucop()                       # ventana ya recalculada a hoy
        hoy = _sucop_hoy().isoformat()
        stats = _sucop_stats()
        ventana = _sucop_ventana(recs)

        if not (q or estado or entidad or sector or tipo):
            # Landing. Los agregados estructurales salen precalculados (no
            # caducan); la ventana se recuenta en vivo (sí caduca) y se declara
            # de cuándo es cada cosa, para que nadie lea un dato viejo como nuevo.
            urgentes = sorted([r for r in recs
                               if r.get('estado_consulta') in ('cierra_pronto', 'abierta')],
                              key=_sucop_orden)
            nuevos = sorted(recs, key=lambda r: r.get('creado') or '', reverse=True)[:12]
            return _resp(200, {
                'mode': 'stats', 'hoy': hoy,
                'total': stats.get('total', len(recs)),
                'ventana': ventana,
                'por_tipo': stats.get('por_tipo', {}),
                'por_tipo_norma': stats.get('por_tipo_norma', []),
                'por_sector': stats.get('por_sector', []),
                'por_entidad': stats.get('por_entidad', []),
                'por_anio': stats.get('por_anio', {}),
                'por_topico': stats.get('por_topico', []),
                'rango_fechas': stats.get('rango_fechas', ['', '']),
                'fuente': stats.get('fuente', {}),
                'cosechado_a': stats.get('calculado_a') or stats.get('generado', ''),
                'abiertos': [_sucop_card(r) for r in urgentes[:40]],
                'recientes': [_sucop_card(r) for r in nuevos],
            })

        # ④ el borrador tampoco nombra marcas: regula la ACTIVIDAD. Acá el puente
        # marca→tema no re-matchea texto: el harvester ya etiquetó cada proceso
        # con las llaves del tesauro que toca (`topicos`), así que basta cruzar
        # llaves. El nombre literal se sigue buscando en `q` por si un borrador
        # puntual sí lo menciona.
        emps = empresas.empresas_en(body.get('query') or '')
        tops = set(empresas.topicos_de(emps, bool(body.get('ampliar_empresa')))) if emps else set()

        def _pasa(r):
            if tipo and (r.get('tipo') or '') != tipo:
                return False
            ec = r.get('estado_consulta')
            if estado == 'abiertas':
                if ec not in ('abierta', 'cierra_pronto'):
                    return False
            elif estado and ec != estado:
                return False
            if entidad and entidad not in (r.get('entidad') or '').lower():
                return False
            if sector and sector not in (r.get('sector') or '').lower():
                return False
            if not q:
                return True
            return (q in (r.get('q') or '')
                    or (tops and tops.intersection(r.get('topicos') or [])))

        hits = [r for r in recs if _pasa(r)]
        hits_sorted = sorted(hits, key=_sucop_orden)
        out = [_sucop_card(r) for r in hits_sorted[:120]]
        # el desglose del subconjunto: cuántas de ESTAS todavía se pueden comentar
        return _resp(200, {
            'mode': 'search', 'hoy': hoy,
            'query': body.get('query', ''), 'estado': estado,
            'entidad': body.get('entidad', ''), 'sector': body.get('sector', ''),
            'tipo': tipo,
            'n': len(hits), 'mostrados': len(out),
            'ventana': _sucop_ventana(hits),
            'ventana_global': ventana,
            'por_entidad': [{'entidad': e, 'n': n} for e, n in
                            Counter((r.get('entidad') or '—') for r in hits).most_common(12)],
            'empresas': _empresas_payload(emps),
            'resultados': out,
        })

    if action == 'contratacion':   # pilar Datos abiertos y contratación · SECOP II en vivo
        try:
            return _resp(200, _contratacion(body))
        except urllib.error.HTTPError as e:
            return _resp(502, {'error': f'SECOP respondió {e.code}', 'detalle': str(e)})
        except Exception as e:
            return _resp(502, {'error': 'no se pudo consultar SECOP',
                               'detalle': f'{type(e).__name__}: {e}'})

    if action == 'medios':      # pilar Medios · prensa nacional y regional (Google News RSS)
        q = (body.get('query') or '').strip()
        if not q:
            return _resp(200, _medios_landing())
        try:
            dias = int(body.get('dias')) if body.get('dias') else None
        except Exception:
            dias = None
        return _resp(200, _medios_buscar(q, dias))

    if action == 'perfil_meta':
        # catálogo para el editor de perfil: plantillas de arranque (los presets),
        # sectores de sanciones CON su conteo real (para no ofrecer un sector que
        # está vacío como si tuviera datos) y comisiones de referencia.
        # dos conteos, porque no dicen lo mismo: `n` son las sanciones y
        # `n_actos` todo el expediente. En la ANLA la diferencia es el sector
        # entero (210 vs 54.105) y enseñar solo el primero haría ver como
        # marginal a la fuente más grande del pilar.
        por_sector, actos_sector = {}, {}
        for r in _sanciones():
            sec = r.get('sector', '')
            actos_sector[sec] = actos_sector.get(sec, 0) + 1
            if (r.get('tipo_acto') or 'sancion') == 'sancion':
                por_sector[sec] = por_sector.get(sec, 0) + 1
        return _resp(200, {
            'plantillas': [caudal_core.perfil_desde_sector(x['k'])
                           for x in caudal_core.SECTORES_CLIENTE],
            'sectores_sanciones': [{'k': k, 'nombre': n, 'n': por_sector.get(k, 0),
                                    'n_actos': actos_sector.get(k, 0)}
                                   for k, n in caudal_core.SANCION_SECTORES],
            'comisiones': caudal_core.COMISIONES_REF,
            'limites': {'temas': caudal_core.PERFIL_MAX_TEMAS,
                        'empresas': caudal_core.PERFIL_MAX_EMPRESAS}})

    if action == 'empresas':
        # autocompletado del diccionario (④) para elegir empresas vigiladas
        return _resp(200, {'empresas': caudal_core.buscar_empresas(body.get('query', ''))})


    if action == 'tablero':
        # ── EL EXPEDIENTE DEL CLIENTE ──────────────────────────────────────
        # El radar responde «¿qué se movió esta semana?». Esto responde la otra
        # mitad, que es la que el cliente lleva a mano en un Excel: «¿cómo va
        # CADA frente que me toca, se haya movido o no?».
        #
        # Por qué hace falta las dos cosas: un tablero de estado se desactualiza
        # solo. En la matriz real de un cliente (ago-2026) el proyecto de
        # circular de SAGRILAFT figuraba «en consulta» cuando ya se había
        # expedido, y el proyecto de ley de PSAV «pendiente de segundo debate»
        # cuando estaba archivado. Ninguna de las dos cosas es descuido: es que
        # mantener siete frentes a mano no escala.
        #
        # Se agrupa por URGENCIA y no por fuente, que es lo que el Excel no
        # puede hacer: primero lo que tiene plazo corriendo, al final lo cerrado.
        sk = body.get('sector')
        perfil_in = body.get('perfil')
        if isinstance(perfil_in, dict):
            s = caudal_core.normalizar_perfil(perfil_in)
            if not s['temas'] and not s['empresas_keys']:
                return _resp(400, {'error': 'el perfil necesita al menos un tema '
                                            'o una empresa vigilada'})
        else:
            s = caudal_core.sector_cliente(sk)
            if not s:
                return _resp(400, {'error': f'sector desconocido: {sk}'})

        temas = [_fold_q(t) for t in (s.get('temas') or []) if len(_fold_q(t)) >= 4]
        for t in caudal_core.temas_de_empresas(s.get('empresas_keys')):
            tf = _fold_q(t)
            if len(tf) >= 4 and tf not in temas:
                temas.append(tf)
        casa = lambda blob: any(t in (blob or '') for t in temas)
        hoy = _time.strftime('%Y-%m-%d', _time.gmtime())
        corte = str(int(hoy[:4]) - 2)          # ventana de dos años para lo cerrado

        consulta, tramite, vigente, cerrado = [], [], [], []
        solo_texto = 0

        # 1 · consulta pública — lo único con reloj corriendo
        try:
            for r in _sucop():
                if r.get('estado_consulta') not in ('abierta', 'cierra_pronto'):
                    continue
                if not casa(r.get('q')):
                    continue
                consulta.append({
                    'ref': r.get('codigo') or '—', 'titulo': (r.get('titulo') or '')[:200],
                    'tipo': (r.get('tipo_norma') or 'Proyecto de norma'),
                    'entidad': r.get('entidad') or '—', 'estado': 'En consulta',
                    'cierra': r.get('fecha_fin') or '', 'fecha': r.get('fecha_inicio') or '',
                    'fuente': 'Consulta pública', 'url': r.get('url') or ''})
        except Exception as e:
            print(f'[tablero] sucop FAIL: {type(e).__name__}: {e}')

        # 2 · Congreso — vivo y cerrado, con su comisión
        try:
            rc = caudal.radar_congreso(temas=s.get('temas', []),
                                       comision_lbl=s.get('comision', ''), cap=90,
                                       empresas_keys=s.get('empresas_keys'))
            # El tablero exige que el tema esté en el TÍTULO. `radar_congreso`
            # también acepta la coincidencia dentro del articulado, que para
            # descubrir es justo lo que se busca pero para un registro es ruido:
            # medido con el perfil de Binance, 9 de 14 proyectos entraban solo
            # por el texto — uno sobre el STUNT como disciplina deportiva que
            # menciona «lavado de activos» de pasada, otro de honores a un
            # centenario. Ninguno es un frente suyo.
            #
            # Y es autocorregible: lo que se cae queda contado en
            # `solo_en_texto`, así que si un tema importa de verdad —la reforma
            # tributaria, por ejemplo— se agrega al perfil y entra por título.
            for x in rc.get('senales', []):
                if not casa(_fold_q(x.get('titulo'))):
                    solo_texto += 1
                    continue
                # el id del Congreso llega como entero; el frontend lo trata
                # como texto igual que las demás referencias
                fila = {'ref': x.get('num') or f"id {x.get('id')}",
                        'titulo': (x.get('titulo') or '')[:200],
                        'tipo': 'Proyecto de ley',
                        'entidad': ('Congreso · Comisión ' + x['comision'].title())
                                   if x.get('comision') else 'Congreso',
                        'estado': x.get('resultado_txt') or '—', 'cierra': '',
                        'fecha': str(x.get('anio') or ''), 'fuente': 'Congreso', 'url': ''}
                (tramite if x.get('resultado') == 'EN_TRAMITE' else cerrado).append(fila)
        except Exception as e:
            print(f'[tablero] congreso FAIL: {type(e).__name__}: {e}')

        # 3 · norma expedida — superintendencias y Ejecutivo
        try:
            for r in _sanciones():
                if (r.get('tipo_acto') or '') not in ('circular', 'resolucion'):
                    continue
                if (r.get('fecha') or '')[:4] < corte or not casa(r.get('q')):
                    continue
                vigente.append({
                    'ref': (r.get('resolucion') or '—')[:60],
                    'titulo': (r.get('motivo') or r.get('descripcion') or '')[:200],
                    'tipo': (r.get('tipo') or 'Acto administrativo'),
                    'entidad': r.get('fuente_nombre') or '—', 'estado': 'Expedida',
                    'cierra': '', 'fecha': r.get('fecha') or '',
                    'fuente': 'Superintendencias', 'url': r.get('url') or ''})
        except Exception as e:
            print(f'[tablero] regulatorio FAIL: {type(e).__name__}: {e}')
        try:
            for r in _ejecutivo():
                if (r.get('fecha') or '')[:4] < corte or not casa(r.get('q')):
                    continue
                vigente.append({
                    'ref': (r.get('numero') or '—'), 'titulo': (r.get('titulo') or '')[:200],
                    'tipo': (r.get('tipo') or 'Norma').title(), 'entidad': 'Presidencia',
                    'estado': 'Expedida', 'cierra': '', 'fecha': r.get('fecha') or '',
                    'fuente': 'Ejecutivo', 'url': r.get('url') or ''})
        except Exception as e:
            print(f'[tablero] ejecutivo FAIL: {type(e).__name__}: {e}')

        _rec = lambda xs: sorted(xs, key=lambda r: (r.get('cierra') or r.get('fecha') or ''),
                                 reverse=not bool(xs and xs[0].get('cierra')))
        consulta.sort(key=lambda r: r.get('cierra') or '9999')      # el que cierra antes, primero
        for g in (tramite, vigente, cerrado):
            g.sort(key=lambda r: r.get('fecha') or '', reverse=True)

        TOPE = 40
        grupos = [
            {'k': 'consulta', 'nombre': 'En consulta pública',
             'nota': 'Tiene plazo corriendo: es lo único donde todavía se puede comentar.',
             'n': len(consulta), 'items': consulta[:TOPE]},
            {'k': 'tramite', 'nombre': 'En trámite en el Congreso',
             'nota': 'Vivo. Puede moverse en cualquier sesión.',
             'n': len(tramite), 'items': tramite[:TOPE]},
            {'k': 'vigente', 'nombre': 'Norma expedida y vigente',
             'nota': 'Ya obliga. Acá se mira cumplimiento, no incidencia.',
             'n': len(vigente), 'items': vigente[:TOPE]},
            {'k': 'cerrado', 'nombre': 'Cerrado o archivado',
             'nota': 'Sin trámite. Queda como antecedente de lo que ya se intentó.',
             'n': len(cerrado), 'items': cerrado[:TOPE]},
        ]
        return _resp(200, {
            'cliente': {'nombre': s.get('nombre', ''), 'temas': s.get('temas', []),
                        'empresas': s.get('empresas', [])},
            'hoy': hoy, 'tope_por_grupo': TOPE,
            # proyectos que casaban solo dentro del articulado y no en el
            # título: es la pista de que al perfil le falta un tema
            'solo_en_texto': solo_texto,
            'kpis': {'total': len(consulta) + len(tramite) + len(vigente) + len(cerrado),
                     'consulta': len(consulta), 'tramite': len(tramite),
                     'vigente': len(vigente), 'cerrado': len(cerrado)},
            'grupos': grupos})

    if action == 'cliente':        # Vista Cliente · radar SIGA sobre los pilares
        # Dos entradas: `perfil` (los temas y las vigiladas DEL cliente, que el
        # frontend trae del KV del worker) o `sector` (uno de los 6 presets, que
        # se quedan como demo y como plantilla de arranque).
        sk = body.get('sector')
        perfil_in = body.get('perfil')
        sectores = [{'k': x['k'], 'nombre': x['nombre'],
                     'regulatorio': bool(x.get('sector_sanciones'))}
                    for x in caudal_core.SECTORES_CLIENTE]
        if isinstance(perfil_in, dict):
            s = caudal_core.normalizar_perfil(perfil_in)
            if not s['temas'] and not s['empresas_keys']:
                return _resp(400, {'error': 'el perfil necesita al menos un tema '
                                            'o una empresa vigilada',
                                   'perfil': s, 'sectores': sectores})
        else:
            s = caudal_core.sector_cliente(sk)
            if not s:
                return _resp(400, {'error': f'sector desconocido: {sk}', 'sectores': sectores})
        emps_vig = [e for e in empresas.EMPRESAS if e['k'] in set(s.get('empresas_keys') or [])]
        rc = caudal.radar_congreso(temas=s.get('temas', []),
                                   comision_lbl=s.get('comision', ''),
                                   empresas_keys=s.get('empresas_keys'))
        # --- qué DICE cada proyecto, y si le aplica a este cliente ----------
        # El radar sin esto dice "hay un proyecto sobre tu tema". Con esto dice
        # "crea N obligaciones sobre tus vigiladas y está vivo".
        _sect_cli, _quien_vig = _sectores_del_cliente(s, emps_vig)
        try:
            n_art, n_aplica = _enriquecer_senales_congreso(rc['senales'], _sect_cli, _quien_vig)
        except Exception as e:
            print(f'[cliente] articulado FAIL: {type(e).__name__}: {e}')
            n_art = n_aplica = 0
        # --- vigiladas · identidad (perfil) --------------------------------
        # Se resuelven ANTES que el sector para poder descontar duplicados: una
        # sanción a Bancolombia es a la vez "del sector financiero" y "de tu
        # vigilada", y mostrarla dos veces infla el radar.
        reg_vig, vig_keys = [], set()
        for quien, r in _regulatorio_para_empresas(emps_vig):
            yr = (r.get('fecha') or '')[:4]
            reciente = yr.isdigit() and int(yr) >= caudal_core.REF_YEAR - 1
            vig_keys.add((r.get('sancionado'), r.get('fecha'), r.get('resolucion'),
                          r.get('fuente')))
            # el acto de la vigilada tampoco es siempre una sanción: desde que
            # entró la ANLA, lo que aparece contra una minera suele ser una
            # resolución de seguimiento o una investigación abierta. Se nombra
            # por lo que es — llamarle "sanción" a un archivo es un error caro.
            acto = r.get('tipo_acto') or 'sancion'
            lbl = _REG_ACTO_LBL.get(acto, _REG_ACTO_LBL['otro'])
            reg_vig.append({'tipo': 'regulatorio', 'vigilada': quien,
                            'sancionado': r.get('sancionado'),
                            'fuente': r.get('fuente_nombre'), 'tipo_sancion': r.get('tipo'),
                            'acto': acto, 'acto_lbl': lbl,
                            'motivo': (r.get('motivo') or '')[:170], 'fecha': r.get('fecha'),
                            'monto': r.get('monto'),
                            # acá el nivel NO depende de la clase de acto: que el
                            # regulador se haya movido este año contra la empresa
                            # que el cliente vigila es alta prioridad aunque sea
                            # una resolución de trámite. En el bloque de SECTOR sí
                            # se distingue, porque ahí el acto es de un tercero.
                            'nivel': 'alto' if reciente else 'medio',
                            'accion': (f'{lbl} contra {quien}, empresa que vigilas — '
                                       'documentar el caso y su exposición') if reciente else
                                      f'Antecedente regulatorio de {quien} ({lbl.lower()})'})
        reg, n_sanc, n_otros = [], 0, 0
        # El sector del perfil es UNO solo, y desde ago-2026 eso se quedó corto:
        # a un exchange de criptoactivos le pega la UIAF (financiero), la
        # Supersociedades (societario) y la DIAN (tributario) a la vez, y el
        # campo solo admite un sector. Verificado con el perfil de Binance: con
        # `sector_sanciones='consumo'` su obligación de reporte ante la UIAF
        # —que es su frontera de cumplimiento más cara— no aparecía nunca.
        #
        # Por eso el pilar se mira por DOS vías y se unen sin repetir:
        #   · por SECTOR, como siempre (lo que le pasa a otros de su gremio);
        #   · por TEMA, contra el blob de búsqueda (la norma que le habla a él,
        #     la emita quien la emita).
        # La vía temática es la que trae la norma, que para un cliente vale más
        # que la multa que le pusieron a un tercero.
        dels, vistos = [], set()
        if s.get('sector_sanciones'):
            for r in _sanciones():
                if r.get('sector') == s['sector_sanciones']:
                    dels.append(r)
                    vistos.add(id(r))
        temas_reg = [_fold_q(t) for t in (s.get('temas') or []) if len(_fold_q(t)) >= 4]
        if temas_reg:
            for r in _sanciones():
                if id(r) in vistos:
                    continue
                blob = r.get('q') or ''
                if any(t in blob for t in temas_reg):
                    dels.append(r)
                    vistos.add(id(r))
        if dels:
            sanc = [r for r in dels if (r.get('tipo_acto') or 'sancion') == 'sancion']
            n_sanc, n_otros = len(sanc), len(dels) - len(sanc)
            reg = _bloque_regulatorio(dels, vig_keys)
        med, n_med = [], 0
        cutoff = _time.strftime('%Y-%m-%d', _time.gmtime(_time.time() - 5 * 86400))
        med_vig, vig_urls = [], set()
        try:
            for quien, r in _medios_para_empresas(emps_vig):
                vig_urls.add(r.get('url'))
                reciente = (r.get('fecha') or '') >= cutoff
                med_vig.append({'tipo': 'medios', 'vigilada': quien, 'medio': r.get('medio'),
                                'titulo': r.get('titulo'), 'url': r.get('url'),
                                'fecha': r.get('fecha'), 'alcance': r.get('alcance'),
                                'nivel': 'alto' if reciente else 'medio',
                                'accion': (f'{quien} en prensa — evaluar respuesta o vocería'
                                           if reciente else
                                           f'Cobertura de {quien} — seguimiento')})
        except Exception as e:
            print(f'[cliente] medios vigiladas FAIL: {type(e).__name__}: {e}')
        # el sector se busca aunque el perfil no tenga temas propios (puede ser
        # un perfil de puras vigiladas): ahí el bloque de sector queda vacío y
        # el radar vive de la identidad, que es lo correcto.
        med_agg = _medios_para_sector(s.get('temas', [])[:4])
        n_med = med_agg['n']
        for r in med_agg['resultados']:
            if len(med) >= 5:
                break
            if r.get('url') in vig_urls:
                continue
            reciente = (r.get('fecha') or '') >= cutoff
            med.append({'tipo': 'medios', 'medio': r.get('medio'), 'titulo': r.get('titulo'),
                        'url': r.get('url'), 'fecha': r.get('fecha'), 'alcance': r.get('alcance'),
                        'nivel': 'alto' if reciente else 'medio',
                        'accion': ('Cobertura reciente — revisar si necesita respuesta o vocería'
                                   if reciente else
                                   'Tema en el radar de prensa — monitoreo pasivo')})
        # Contratación · qué está comprando el Estado en el sector. Un contrato
        # no es una "alerta" como una sanción: es plata ya comprometida, así que
        # el nivel lo da la frescura de la firma (90 días ≈ el ciclo en que
        # todavía se puede incidir en la ejecución o competir por el siguiente).
        con, n_con = [], 0
        corte_con = _time.strftime('%Y-%m-%d', _time.gmtime(_time.time() - 90 * 86400))
        # vigiladas: contratos que SON de la empresa (identidad), no los que la
        # mencionan. Es la pregunta directa "¿mi vigilada le vende al Estado?".
        con_vig, vig_cids, n_con_vig, con_vig_vacio = [], set(), 0, False
        try:
            cv = _secop_para_empresas(emps_vig)
            n_con_vig = cv.get('n', 0)
            con_vig_vacio = bool(cv.get('sin_contratos'))
            for quien, r in cv.get('resultados', []):
                vig_cids.add(r.get('id'))
                reciente = (r.get('fecha') or '') >= corte_con
                con_vig.append({'tipo': 'contratacion', 'vigilada': quien,
                                'entidad': r.get('entidad'), 'proveedor': r.get('proveedor'),
                                'objeto': (r.get('objeto') or '')[:170], 'valor': r.get('valor'),
                                'departamento': r.get('departamento'), 'fecha': r.get('fecha'),
                                'url': r.get('url'), 'nivel': 'alto' if reciente else 'medio',
                                'accion': (f'Contrato reciente de {quien} — revisar objeto, '
                                           'entidad y ejecución') if reciente else
                                          f'Antecedente de contratación de {quien}'})
        except Exception as e:
            print(f'[cliente] secop vigiladas FAIL: {type(e).__name__}: {e}')
        try:
            con_agg = _secop_para_sector(s.get('temas', []))
        except Exception as e:
            print(f'[cliente] secop FAIL: {type(e).__name__}: {e}')
            con_agg = {'n': 0, 'resultados': []}
        n_con = con_agg['n']
        # La contratación GENÉRICA del sector se calla para un perfil de cliente.
        # Medido con Binance: sin vender un peso al Estado, su radar traía cinco
        # contratos de servicios profesionales de la Secretaría de Integración
        # Social — ruido con apariencia de señal, y encima marcado 'alto'. Para
        # un cliente temático SECOP no aporta: no existe la contratación pública
        # de criptoactivos. Lo que SÍ se conserva es la contratación de sus
        # VIGILADAS (con_vig, que va por identidad y arriba en el bloque) y el
        # conteo `n_contratos_sector`, para que el dato no desaparezca: se deja
        # de mostrar, no se esconde.
        # Los 6 presets de sector siguen igual — son demo y ahí el sector ES el
        # cliente.
        con_generica_muda = s.get('k') == 'perfil'
        for r in ([] if con_generica_muda else con_agg['resultados']):
            if r.get('id') in vig_cids:
                continue
            reciente = (r.get('fecha') or '') >= corte_con
            con.append({'tipo': 'contratacion', 'entidad': r.get('entidad'),
                        'proveedor': r.get('proveedor'), 'objeto': (r.get('objeto') or '')[:170],
                        'valor': r.get('valor'), 'departamento': r.get('departamento'),
                        'fecha': r.get('fecha'), 'url': r.get('url'),
                        'nivel': 'alto' if reciente else 'medio',
                        'accion': ('Contrato reciente en tu sector — revisar quién ganó y con qué '
                                   'objeto antes del próximo proceso') if reciente else
                                  'Antecedente de contratación — referencia de precios y proveedores'})
        # las de identidad van primero DENTRO de su pilar: en la lista del
        # cliente, "sancionaron a tu vigilada" tiene que leerse antes que
        # "sancionaron a alguien de tu sector".
        reg, med, con = reg_vig + reg, med_vig + med, con_vig + con
        senales = rc['senales'] + reg + med + con
        n_vig = sum(1 for x in senales if x.get('vigilada'))
        kpis = {'n_radar': len(senales),
                'alto': sum(1 for x in senales if x['nivel'] == 'alto'),
                'medio': sum(1 for x in senales if x['nivel'] == 'medio'),
                'bajo': sum(1 for x in senales if x['nivel'] == 'bajo'),
                'en_tramite': sum(1 for x in rc['senales'] if x['resultado'] == 'EN_TRAMITE'),
                'n_proyectos_sector': rc['n_tocados'], 'n_sanciones_sector': n_sanc,
                'n_otros_actos_sector': n_otros,
                'n_medios_sector': n_med, 'n_contratos_sector': n_con,
                'n_vigiladas': len(emps_vig), 'n_senales_vigiladas': n_vig,
                'n_contratos_vigiladas': n_con_vig,
                # articulado: cuántas señales del Congreso traen "qué cambia" y
                # cuántas de ésas le aplican al sector/vigiladas del cliente
                'n_con_articulado': n_art, 'n_te_aplica': n_aplica}
        # Cada señal sabe a qué punto pertenece y si se movió en 72 h. Va sobre
        # `senales` (la lista unificada) y sobre los bloques por pilar, que son
        # los mismos objetos: el frontend lee `card`/`mov` de cualquiera de las dos.
        cards = _anotar_cardinales(senales)
        kpis['cardinales'] = cards
        kpis['mov_dias'] = MOV_DIAS
        out = {'cliente': {'sector': sk, 'nombre': s['nombre'], 'comision': s.get('comision', ''),
                           'sector_sanciones': s.get('sector_sanciones', ''),
                           'temas': s.get('temas', []),
                           'es_perfil': s.get('k') == 'perfil',
                           'descripcion': s.get('descripcion', ''),
                           # Un perfil guardado trae `empresas` ya resueltas; un
                           # preset solo trae las llaves. Sin este fallback la
                           # ficha decía «Competencia (6):» y no nombraba a
                           # ninguna, que es peor que no mostrar el bloque.
                           'empresas': s.get('empresas') or [
                               {'k': e['k'], 'nombre': e['nombre'], 'tipo': e['tipo']}
                               for e in emps_vig],
                           'temas_usados': rc.get('temas_usados', []),
                           # empresa vs gremio: cambia qué se le pregunta y qué
                           # significa "vigilada" (competencia vs afiliadas)
                           'tipo': s.get('tipo', ''),
                           # una empresa multi-negocio no tiene UNA comisión
                           'lineas': s.get('lineas', []),
                           'competencia': s.get('competencia', []),
                           # países que el cliente sigue y Caudal NO cubre: se
                           # declara en pantalla en vez de dejarlo asumir
                           'fuera_de_alcance': s.get('fuera_de_alcance', []),
                           # honesto: las vigiladas están en el diccionario pero
                           # no le venden al Estado (verificado con Uber/Ecopetrol)
                           'vigiladas_sin_contratos': con_vig_vacio,
                           # por qué el bloque de contratación puede venir vacío
                           # aunque `n_contratos_sector` no sea cero
                           'contratacion_generica_omitida': con_generica_muda,
                           'descartes': s.get('descartes', [])},
               'congreso': rc['senales'], 'regulatorio': reg, 'medios': med,
               'contratacion': con, 'kpis': kpis, 'sectores': sectores}
        out['cliente']['avisos'] = s.get('avisos', [])
        # `lectura:true` YA NO significa "espérame la síntesis": significa
        # "prepárala". El radar tiene que salir siempre rápido (medido:
        # 0,7-3,8 s) y la síntesis tarda 20-51 s — pedirlas en la misma
        # respuesta era lo que hacía que un perfil nuevo diera 503 a los 30,5 s.
        # Acá solo se deja el prompt listo en el caché; el frontend recoge la
        # lectura por `cliente-lectura`, igual que test-presidencial-2026 pinta
        # el resultado primero y trae la lectura del modelo después.
        if body.get('lectura', False):
            lkey = _lectura_cliente_key(s, kpis)
            out['lectura_key'] = lkey
            lista = _cache_get('cliente-' + lkey)
            if lista:
                out['lectura'] = lista       # radar ya visto antes: sale de una
            else:
                _cache_put('cliente-in-' + lkey,
                           {'user': _lectura_cliente_prompt(s, senales, kpis)})
        return _resp(200, out)

    if action == 'cliente-lectura':
        # el briefing del radar, aparte. Dos modos:
        #   solo_cache:true  → sondeo barato (un GET a S3): lista o pendiente.
        #   sin solo_cache   → arranca la generación. Esta petición SE PASA de
        #                      los 30 s del gateway a menudo; el navegador la
        #                      abandona y recoge el resultado sondeando, pero
        #                      la Lambda (60 s) termina y deja la lectura hecha.
        key = str(body.get('key') or '').strip()
        if not key or not key.isalnum():
            return _resp(400, {'error': 'falta la llave de la lectura (lectura_key)'})
        lista = _cache_get('cliente-' + key)
        if lista:
            return _resp(200, {'estado': 'lista', 'lectura': lista, 'key': key})
        if body.get('solo_cache'):
            return _resp(200, {'estado': 'pendiente', 'key': key})
        r = _lectura_cliente_generar(key)
        r['key'] = key
        return _resp(200, r)

    if action == 'tema':
        q = body.get('query', '')
        if not q.strip():
            return _resp(400, {'error': 'falta query'})
        # expansión de consulta con IA (ON por defecto): cubre el desajuste de
        # vocabulario usuario↔título formal. `expandir_ia:false` la apaga.
        # ④ si la consulta es una EMPRESA del diccionario, se salta: la
        # traducción curada ya cubre el desajuste, es determinista (misma
        # consulta, misma respuesta), no cuesta una llamada al modelo y no le
        # mete al OR términos que el modelo se invente.
        emps = empresas.empresas_en(q)
        extra = [] if emps else (_expandir_query(q, solo_cache=not autorizado)
                                 if body.get('expandir_ia', True) else [])
        resumen = caudal.resumen_tema(
            q, anio_min=body.get('anio_min'), anio_max=body.get('anio_max'),
            comision=body.get('comision'), extra_terms=extra,
            ampliar_empresa=bool(body.get('ampliar_empresa')))
        out = {'query': q, 'resumen': resumen,
               'model_info': {'sintesis': STEP_MODELS['sintesis']}}
        if body.get('lectura', True) and resumen['n_intentos'] > 0:
            if not autorizado:
                # Degrada, no rechaza. El visitante sin acceso se lleva el
                # resumen COMPLETO —que es real, y es lo que convence— y el
                # frontend pinta el muro encima de la lectura. Cero llamadas al
                # modelo. Un blur sobre un resumen vacío se huele en cinco
                # segundos; sobre cifras reales, vende.
                out['lectura_bloqueada'] = True
            else:
                casos = None
                if body.get('profundo'):    # opt-in: más lento/costoso, lee gacetas de verdad
                    casos = _profundizar_tema(caudal, resumen)
                # NO se genera acá: se prepara y se devuelve la llave. Si ya
                # estaba hecha viene en la misma respuesta y el frontend no
                # sondea nada. Ver _tema_lectura_pedir para el porqué.
                key, hecha = _tema_lectura_pedir(resumen, casos)
                out['lectura_key'] = key
                if hecha:
                    out['lectura'] = hecha
        return _resp(200, out)

    if action == 'tema-lectura':
        # gemela de `cliente-lectura`. Dos modos:
        #   solo_cache:true  → sondeo barato (un GET a S3): lista o pendiente.
        #   sin solo_cache   → arranca la generación. Esta petición SE PASA de
        #                      los 30 s del gateway a menudo; el navegador la
        #                      abandona y recoge el resultado sondeando, pero
        #                      la Lambda (60 s) termina y deja la lectura hecha.
        key = str(body.get('key') or '').strip()
        if not key or not key.isalnum():
            return _resp(400, {'error': 'falta la llave de la lectura (lectura_key)'})
        lista = _cache_get(key)
        if lista:
            return _resp(200, {'estado': 'lista', 'lectura': lista, 'key': key})
        if body.get('solo_cache'):
            return _resp(200, {'estado': 'pendiente', 'key': key})
        r = _tema_lectura_generar(key)
        r['key'] = key
        return _resp(200, r)

    return _resp(400, {'error': f'action desconocida: {action}'})
