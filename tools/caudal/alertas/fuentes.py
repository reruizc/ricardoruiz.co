#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — lectores de fuente.

Todo lo que entra al motor pasa por acá y sale con la MISMA forma de evento:

    {id, pilar, tipo, fecha, titulo, detalle, url, meta}

`id` es una llave estable derivada del contenido: es lo que permite decir "esto
ya lo mandé ayer" sin depender de que la fuente traiga un identificador (varias
no lo traen).

Ninguna función de este módulo escribe en las fuentes. El rastreo de radicados
(`run_diario.sh`) y los harvesters de supers/ejecutivo son de otras corridas;
acá solo se leen sus salidas ya publicadas. Contra leyes.senado.gov.co no se
hace ni una petición: hay WAF y ese host es de otro proceso.
"""

import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..'))
BASE_DATOS = os.path.join(REPO, 'Bases de datos', 'leyes-senado')

BUCKET = 'caudal-legislativo'
API = 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com'
# Worker rr-auth: de ahí salen los perfiles de cliente (endpoint de servicio).
WORKER = os.environ.get('CAUDAL_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
RUTA_INVENTARIO = '/caudal/alertas/inventario'

TIMEOUT_API = 45


def hash24(*partes):
    """Llave estable de 24 hex a partir del contenido."""
    crudo = '\x1f'.join(str(p or '') for p in partes)
    return hashlib.sha256(crudo.encode('utf-8')).hexdigest()[:24]


# ---------------------------------------------------------------------------
# 1) RADICADOS · novedades del rastreo diario
# ---------------------------------------------------------------------------
# El rastreo ya calculó el diff contra el día anterior y lo dejó en
# novedades-YYYY-MM-DD.json. No se recalcula: se lee.

RUTAS_NOVEDADES = [
    ('senado', os.path.join(BASE_DATOS, 'diario', 'novedades')),
    ('camara', os.path.join(BASE_DATOS, 'diario-camara', 'novedades')),
]


def _numero(p):
    return (p.get('numero_senado') or p.get('numero_camara') or '').strip()


def _comision_de(p):
    """Senado trae 'comision' como texto; Cámara trae 'comisiones' como lista."""
    c = p.get('comision')
    if c:
        return str(c)
    cs = p.get('comisiones') or []
    if isinstance(cs, list):
        return ' · '.join(x.get('nombre', '') for x in cs if isinstance(x, dict))
    return str(cs or '')


def novedades(fecha, camaras=None):
    """Eventos de radicados de una fecha → (eventos, faltantes).

    `faltantes` son las cámaras sin archivo ese día — se reporta, no se asume
    que "no hubo novedades" (un cron caído se ve igual que un día tranquilo, y
    confundirlos es cómo un sistema de alertas pierde la confianza).
    """
    eventos, faltantes = [], []
    for camara, ruta in RUTAS_NOVEDADES:
        if camaras and camara not in camaras:
            continue
        f = os.path.join(ruta, f'{fecha}.json')
        if not os.path.exists(f):
            faltantes.append(camara)
            continue
        try:
            d = json.load(open(f, encoding='utf-8'))
        except (ValueError, OSError) as e:
            faltantes.append(f'{camara} (ilegible: {e})')
            continue

        for p in d.get('nuevos', []):
            num = _numero(p)
            titulo = (p.get('titulo') or p.get('proyecto') or '').strip()
            if not titulo:
                continue
            eventos.append({
                'id': hash24('radicado', camara, num, titulo[:120]),
                'pilar': 'congreso', 'tipo': 'radicado_nuevo',
                'fecha': p.get('fecha_de_presentacion', '').replace('/', '-') or fecha,
                'titulo': titulo,
                'detalle': '',
                'url': p.get('texto_radicado_url') or '',
                'meta': {'camara': camara, 'numero': num,
                         'comision': _comision_de(p),
                         'autor': (p.get('autor') or p.get('otros_autores') or ''),
                         'estado': p.get('estado', '')},
            })

        for c in d.get('cambios', []):
            num = _numero(c)
            titulo = (c.get('titulo') or '').strip()
            eventos.append({
                'id': hash24('tramite', camara, num, fecha),
                'pilar': 'congreso', 'tipo': 'tramite',
                'fecha': fecha,
                'titulo': titulo,
                'detalle': '',
                'url': '',
                'meta': {'camara': camara, 'numero': num,
                         'deltas': c.get('deltas') or {}},
            })
    return eventos, faltantes


def titulo_conocido(numero, camara):
    """Título de un proyecto desde el snapshot del rastreo.

    Los `cambios` a veces llegan con el título en blanco (el registro lo
    vació). Sin esto, una aprobación en segundo debate saldría en el digest
    como un número sin nombre.
    """
    rutas = [os.path.join(BASE_DATOS, 'diario', '2026-2027', 'proyectos.json'),
             os.path.join(BASE_DATOS, 'diario-camara', '2026-2027', 'proyectos.json')]
    for r in rutas:
        if not os.path.exists(r):
            continue
        try:
            d = json.load(open(r, encoding='utf-8'))
        except (ValueError, OSError):
            continue
        registros = d.values() if isinstance(d, dict) else d
        for p in registros:
            if not isinstance(p, dict):
                continue
            if _numero(p) == numero and (p.get('titulo') or p.get('proyecto')):
                return (p.get('titulo') or p.get('proyecto')).strip()
    return ''


# ---------------------------------------------------------------------------
# 2) S3 · sanciones y normativa
# ---------------------------------------------------------------------------

def s3_etag(key):
    """ETag del objeto (para no re-bajar 5 MB que no cambiaron)."""
    try:
        out = subprocess.run(
            ['aws', 's3api', 'head-object', '--bucket', BUCKET, '--key', key,
             '--query', 'ETag', '--output', 'text'],
            capture_output=True, text=True, timeout=60)
        if out.returncode == 0:
            return out.stdout.strip().strip('"')
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def s3_bajar(key, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    out = subprocess.run(['aws', 's3', 'cp', f's3://{BUCKET}/{key}', destino, '--quiet'],
                         capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f'aws s3 cp {key}: {out.stderr.strip()[:300]}')
    return destino


def leer_jsonl(ruta):
    """JSONL tolerante.

    Se parte por '\\n' explícito y NUNCA con splitlines(): estos archivos traen
    texto de sanciones con mojibake de Windows-1252, y U+0085 (NEL) cuenta como
    salto de línea para splitlines aunque no separe registros — parte un
    registro en dos fragmentos inválidos. Es un bug ya medido en build_s3.py.
    """
    filas = []
    with open(ruta, encoding='utf-8') as fh:
        for linea in fh.read().split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            try:
                filas.append(json.loads(linea))
            except ValueError:
                continue
    return filas


def llave_sancion(r):
    return hash24('sancion', r.get('fuente'), r.get('resolucion'),
                  r.get('sancionado'), r.get('fecha'), (r.get('motivo') or '')[:80])


def llave_normativa(r):
    return hash24('normativa', r.get('tipo'), r.get('numero'), r.get('anio'),
                  r.get('fecha'), (r.get('titulo') or '')[:80])


def sanciones(ruta):
    """Actos regulatorios → eventos."""
    out = []
    for r in leer_jsonl(ruta):
        titulo = (r.get('sancionado') or 'Entidad no identificada').strip()
        out.append({
            'id': llave_sancion(r),
            'pilar': 'regulatorio',
            'tipo': (r.get('tipo_acto') or 'sancion'),
            'fecha': r.get('fecha') or '',
            'titulo': titulo,
            'detalle': (r.get('motivo') or r.get('descripcion') or '').strip(),
            'url': r.get('url') or '',
            'meta': {'fuente': r.get('fuente_nombre') or r.get('fuente'),
                     'sector_fuente': r.get('sector') or '',
                     'tipo_sancion': r.get('tipo') or '',
                     'monto': r.get('monto'),
                     'resolucion': r.get('resolucion') or '',
                     'q': r.get('q') or ''},
            '_row': r,
        })
    return out


def normativa(ruta):
    """Normativa del Ejecutivo → eventos."""
    out = []
    for r in leer_jsonl(ruta):
        num = r.get('numero') or ''
        tipo = (r.get('tipo') or '').strip()
        titulo = (r.get('titulo') or f'{tipo} {num}').strip()
        out.append({
            'id': llave_normativa(r),
            'pilar': 'ejecutivo',
            'tipo': 'normativa',
            'fecha': r.get('fecha') or '',
            'titulo': titulo,
            'detalle': (r.get('descripcion') or '').strip(),
            'url': r.get('url') or '',
            'meta': {'tipo_norma': tipo, 'numero': num, 'anio': r.get('anio') or '',
                     'q': r.get('q') or ''},
            '_row': r,
        })
    return out


# ---------------------------------------------------------------------------
# 3) API de la Lambda · SOLO LECTURA
# ---------------------------------------------------------------------------

def api(payload, timeout=TIMEOUT_API):
    """POST a la Lambda de Caudal. Devuelve dict o lanza."""
    datos = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        API, data=datos, method='POST',
        headers={'Content-Type': 'application/json',
                 'User-Agent': 'caudal-alertas/1.0 (+ricardoruiz.co)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def api_seguro(payload, timeout=TIMEOUT_API):
    """api() que no tumba la corrida: (dict|None, error|None).

    Una alerta parcial vale más que ninguna: si la prensa no responde, el
    digest sale igual con Congreso y Regulatorio, y dice qué faltó.
    """
    try:
        return api(payload, timeout), None
    except (urllib.error.URLError, ValueError, OSError, TimeoutError) as e:
        return None, f'{type(e).__name__}: {str(e)[:160]}'


def perfiles_alertas(timeout=25):
    """Perfiles de cliente con alertas ENCENDIDAS → (lista|None, error|None).

    Habla con el worker `rr-auth` por su endpoint de servicio. No es una sesión
    de usuario ni de admin: presenta un secreto en una cabecera propia. El
    secreto vive FUERA del repo, junto a la key de Resend:

        ~/.config/caudal/alertas.env   →  CAUDAL_ALERTAS_TOKEN=...

    Sin secreto no se inventa nada ni se falla: devuelve (None, motivo) y el
    motor sigue con los sectores, que es el fallback de siempre.

    Ojo con el guarda del otro lado: rechaza peticiones con huella de navegador
    (Origin, Sec-Fetch-*, Cookie). urllib no manda ninguna de esas, así que
    esto pasa; un fetch() desde una página, no.
    """
    # Escotilla de pruebas: un archivo con la MISMA forma que devuelve el
    # worker. Sirve para ensayar un perfil sin tocar producción y para correr
    # sin red. Nunca se usa en el cron (la variable no existe allá).
    fixture = (os.environ.get('CAUDAL_PERFILES_FIXTURE') or '').strip()
    if fixture:
        try:
            d = json.load(open(fixture, encoding='utf-8'))
        except (ValueError, OSError) as e:
            return None, f'fixture ilegible ({fixture}): {str(e)[:120]}'
        d.setdefault('ok', True)
        d['_fixture'] = fixture
        return d, None

    token = (os.environ.get('CAUDAL_ALERTAS_TOKEN') or '').strip()
    if not token:
        return None, ('falta CAUDAL_ALERTAS_TOKEN (ver ~/.config/caudal/alertas.env): '
                      'la corrida usa los sectores')
    url = WORKER.rstrip('/') + RUTA_INVENTARIO
    req = urllib.request.Request(
        url, method='GET',
        headers={'X-Caudal-Service': token,
                 'Accept': 'application/json',
                 'User-Agent': 'caudal-alertas/1.0 (+ricardoruiz.co)'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        # 404 acá casi siempre es "el secreto no coincide": el worker responde
        # como si la ruta no existiera, a propósito.
        pista = ' (¿el token del worker y el local son el mismo?)' if e.code == 404 else ''
        return None, f'HTTP {e.code}{pista}'
    except (urllib.error.URLError, ValueError, OSError, TimeoutError) as e:
        return None, f'{type(e).__name__}: {str(e)[:160]}'
    if not d.get('ok'):
        return None, str(d.get('error') or 'respuesta sin ok')
    return d, None


def perfil_a_destino(p):
    """Perfil del worker → destino con la forma que espera reglas.py."""
    return {
        'k': 'cli-' + str(p.get('perfilId') or ''),
        'perfilId': p.get('perfilId') or '',
        'nombre': p.get('nombre') or 'Cliente sin nombre',
        'comision': p.get('comision') or '',
        'sector_sanciones': p.get('sector_sanciones') or '',
        'temas': list(p.get('temas') or []),
        'empresas': list(p.get('empresas') or []),
        'correo': (p.get('correo') or '').strip().lower(),
        'plan': p.get('plan') or 'free',
        'cadencia': p.get('cadencia') or 'semanal',
        'tipo': 'cliente',
    }


def medios_sector(sector_k, temas, dias=2):
    """Titulares recientes del destino → (eventos, errores).

    Se consulta por cada tema del sector (igual que hace la Lambda en su Radar)
    y se dedupea por titular: una sola query genérica trae ruido de otro país,
    y varias específicas traen el sector de verdad.
    """
    eventos, errores, vistos = [], [], set()
    for tema in temas:
        d, err = api_seguro({'action': 'medios', 'query': tema, 'dias': dias})
        if err:
            errores.append(f'{tema}: {err}')
            continue
        for r in (d or {}).get('resultados', []):
            titulo = (r.get('titulo') or '').strip()
            if not titulo:
                continue
            llave = hash24('medios', titulo.lower()[:140])
            if llave in vistos:
                continue
            vistos.add(llave)
            eventos.append({
                'id': llave,
                'pilar': 'medios', 'tipo': 'titular',
                'fecha': r.get('fecha') or '',
                'titulo': titulo,
                'detalle': '',
                'url': r.get('url') or '',
                'meta': {'medio': r.get('medio') or '', 'alcance': r.get('alcance') or '',
                         'sector': sector_k, 'tema': tema},
            })
    return eventos, errores


def contratos_destino(dest):
    """Contratación del destino, vía la acción `cliente` → (eventos, error, kpis).

    Para un sector va `{'sector': k}` (idéntico a antes); para un cliente va su
    perfil, y entonces la Lambda devuelve además los contratos DE SUS VIGILADAS
    marcados con `vigilada`. Se pide sin `lectura`: la síntesis del modelo es
    para la pantalla, no para el correo — acá se pagaría latencia por nada.
    """
    sector_k = dest['k']
    if dest.get('tipo') == 'cliente':
        payload = {'action': 'cliente', 'perfil': {
            'nombre': dest.get('nombre') or '',
            'temas': dest.get('temas') or [],
            'empresas': dest.get('empresas') or [],
            'sector_sanciones': dest.get('sector_sanciones') or '',
            'comision': dest.get('comision') or '',
        }}
    else:
        payload = {'action': 'cliente', 'sector': sector_k}
    d, err = api_seguro(payload)
    if err:
        return [], err, {}
    eventos = []
    for r in (d or {}).get('contratacion', []) or []:
        objeto = (r.get('objeto') or '').strip()
        entidad = (r.get('entidad') or '').strip()
        if not objeto and not entidad:
            continue
        eventos.append({
            'id': hash24('contrato', entidad, (r.get('proveedor') or ''),
                         r.get('valor'), objeto[:100]),
            'pilar': 'contratacion', 'tipo': 'contrato',
            'fecha': r.get('fecha') or '',
            'titulo': f'{entidad} → {r.get("proveedor") or "proveedor no identificado"}',
            'detalle': objeto,
            'url': r.get('url') or '',
            'meta': {'entidad': entidad, 'proveedor': r.get('proveedor') or '',
                     'valor': r.get('valor'), 'sector': sector_k,
                     'objeto': objeto,
                     # la Lambda ya sabe si el contrato es de una vigilada del
                     # perfil; se conserva su veredicto en vez de re-deducirlo.
                     'vigilada': r.get('vigilada') or '',
                     'departamento': r.get('departamento') or ''},
        })
    return eventos, None, (d or {}).get('kpis', {})


def contratos_sector(sector_k):
    """Compatibilidad: contratación de un sector por su llave."""
    return contratos_destino({'k': sector_k, 'tipo': 'sector'})


# ---------------------------------------------------------------------------
# 4) SALUD OPERATIVA · estado.json del chequeo del cron
# ---------------------------------------------------------------------------

RUTA_ESTADO_SALUD = os.path.join(BASE_DATOS, 'diario', 'estado.json')


def estado_operacion(ruta=None):
    """Lee el estado.json del chequeo de salud. None si no existe todavía.

    Lo escribe otra pieza (tools/caudal/salud/check.py) de forma atómica, así
    que nunca se lee a medias. Que no exista es un escenario normal, no un
    error: el motor de alertas no depende de él.
    """
    ruta = ruta or RUTA_ESTADO_SALUD
    if not os.path.exists(ruta):
        return None
    try:
        return json.load(open(ruta, encoding='utf-8'))
    except (ValueError, OSError):
        return None
