#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — motor de push.

Convierte Caudal de pull a push: corre después del cron diario, compara el
estado de hoy contra el de ayer sobre las fuentes YA publicadas, clasifica lo
nuevo y arma un digest por DESTINO.

Un destino es a quién se le manda el correo, y hay dos clases:

  · CLIENTE — un perfil guardado en la cuenta de alguien (worker rr-auth), con
    SUS temas y SUS empresas vigiladas. Es el producto: la alerta llega al
    correo del dueño del perfil y habla de lo suyo.
  · SECTOR  — los 6 presets. Es el FALLBACK: corre cuando no hay ningún perfil
    con alertas encendidas, o cuando el worker no responde. Nunca desaparece,
    porque un motor que se queda mudo si falla una petición no es un motor.

    python3 motor.py                       corrida normal (hoy)
    python3 motor.py --baseline            sella el estado sin enviar nada
    python3 motor.py --dry-run             calcula y escribe, no envía ni guarda estado
    python3 motor.py --fecha 2026-08-02    una fecha concreta
    python3 motor.py --sin-perfiles        ignora los perfiles: solo sectores
    python3 motor.py --solo-perfiles       solo clientes, sin el fallback de sectores
    python3 motor.py --sectores salud,trabajo    (también acepta llaves cli-<perfilId>)
    python3 motor.py --momento manana|noche      cuál de las dos corridas es
    python3 motor.py --sin-api             sin prensa ni contratación (offline)
    python3 motor.py --estado              qué sabe el motor hasta ahora

La PRIMERA corrida es siempre baseline: sin estado previo, todo el universo
(7.019 sanciones, 11.000 normas) contaría como "nuevo" y el primer correo
llegaría con miles de items. Se sella el estado y se avisa.
"""

import argparse
import datetime as dt
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import articulado as ART                                       # noqa: E402
import fuentes as F                                            # noqa: E402
import reglas as R                                             # noqa: E402
import render                                                  # noqa: E402
import sender                                                  # noqa: E402

# Datos generados. Viven bajo tools/ porque es el único árbol que esta corrida
# tiene permitido escribir; el .gitignore de al lado los mantiene fuera de git.
# Para moverlos a "Bases de datos/leyes-senado/alertas/" (que es donde el
# proyecto guarda datos) basta cambiar CAUDAL_ALERTAS_DIR.
DIR_DATOS = os.environ.get('CAUDAL_ALERTAS_DIR', os.path.join(AQUI, 'datos'))
DIR_ESTADO = os.path.join(DIR_DATOS, 'estado')
DIR_DIGESTS = os.path.join(DIR_DATOS, 'digests')
DIR_CACHE = os.path.join(DIR_DATOS, 'cache')
RUTA_ESTADO = os.path.join(DIR_ESTADO, 'estado.json')
RUTA_DESTINATARIOS = os.path.join(AQUI, 'destinatarios.json')

# Días hacia atrás que se releen de novedades. Si el motor no corrió ayer (Mac
# dormido), la corrida de hoy recupera lo de ayer sola; el estado evita repetir.
DIAS_NOVEDADES = 3

# Ventana de frescura por pilar. Protege contra el backfill: si un harvester
# reconstruye su archivo y mete filas viejas, éstas son nuevas PARA EL ESTADO
# pero no son noticia. Se marcan como vistas y se cuentan aparte.
VENTANAS = {
    'congreso': 45,
    'regulatorio': 60,
    'ejecutivo': 60,
    'contratacion': 200,     # la Lambda ya acota a 180 días por valor
    'medios': 10,
}

# Tope por pilar dentro de cada sector. Lo que sobra NO se esconde: se cuenta.
TOPE_POR_PILAR = 6

# Cuántos titulares de corroboración se cuelgan de una señal antes de resumir.
TOPE_COBERTURA = 4

# Tope de alertas de prensa-sobre-empresa por sector. Es la única prensa que
# dispara sola, así que conviene que no pueda dominar el digest ni en un día raro.
TOPE_EMPRESA_SUELTA = 5

# Un digest solo sale si tiene al menos una señal de este nivel. Ver
# `hay_algo_que_decir`: el silencio es una salida legítima del motor.
NIVEL_MINIMO_ENVIO = 'medio'

# Techos del buzón de un cliente que todavía no toca enviar (ver `_acumular`).
# Sin tope, un cliente semanal con muchos temas acumularía sin límite; con
# tope, lo que sobra se cuenta y se dice en el digest, no se esconde.
BUZON_MAX_ITEMS = 60          # por pilar
BUZON_MAX_DIAS = 45


# ---------------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------------

def cargar_estado():
    if os.path.exists(RUTA_ESTADO):
        try:
            return json.load(open(RUTA_ESTADO, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {'v': 1, 'creado': None, 'ultima_corrida': None, 'corridas': 0,
            'vistos': {}, 'etags': {}}


def guardar_estado(estado):
    os.makedirs(DIR_ESTADO, exist_ok=True)
    tmp = RUTA_ESTADO + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(estado, fh, ensure_ascii=False)
    os.replace(tmp, RUTA_ESTADO)          # atómico: nunca un estado a medias


def podar_estado(estado, dias=120):
    """Los pilares que churnean (prensa, contratos) no necesitan memoria eterna."""
    corte = (dt.date.today() - dt.timedelta(days=dias)).isoformat()
    for pilar in ('medios', 'contratacion'):
        v = estado['vistos'].get(pilar) or {}
        estado['vistos'][pilar] = {k: f for k, f in v.items() if f >= corte}
    return estado


# ---------------------------------------------------------------------------
# RECOLECCIÓN
# ---------------------------------------------------------------------------

def cargar_destinos(usar_perfiles=True, con_sectores=True, avisos=None):
    """Los destinos de esta corrida: clientes primero, sectores como fallback.

    Un cliente NO es un sector con otro nombre: trae su propio vocabulario, su
    propia lista de vigiladas y su propio correo. Pero comparte la forma, así
    que todo el resto del motor los procesa igual.
    """
    avisos = avisos if avisos is not None else []
    clientes = []
    if usar_perfiles:
        inv, err = F.perfiles_alertas()
        if err:
            avisos.append({'tipo': 'perfiles', 'pilar': 'perfiles',
                           'texto': f'No se pudieron leer los perfiles de cliente ({err}). '
                                    f'Esta corrida usa los sectores.'})
        else:
            clientes = [F.perfil_a_destino(p) for p in (inv.get('perfiles') or [])]
            res = inv.get('resumen') or {}
            avisos.append({'tipo': 'perfiles', 'pilar': 'perfiles',
                           'texto': f'Perfiles de cliente: {res.get("activos", len(clientes))} '
                                    f'con alertas encendidas de {res.get("total", "?")} '
                                    f'guardados ({res.get("apagados", "?")} apagados).'})
            # Un perfil sin temas ni vigiladas no tiene con qué armar un radar.
            vivos = []
            for c in clientes:
                # Llaves de empresa que el diccionario no conoce. Se dicen: si
                # no, el perfil se queda sin vigiladas sin que nadie se entere.
                muertas = R.claves_desconocidas(c['empresas'])
                if muertas:
                    avisos.append({'tipo': 'perfiles', 'pilar': 'perfiles',
                                   'texto': f'«{c["nombre"]}» vigila {len(muertas)} empresa(s) que '
                                            f'no están en el diccionario y NO se están mirando: '
                                            + ', '.join(muertas[:5])})
                    c['empresas'] = [x for x in c['empresas'] if x not in set(muertas)]
                if c['temas'] or c['empresas']:
                    vivos.append(c)
                else:
                    avisos.append({'tipo': 'perfiles', 'pilar': 'perfiles',
                                   'texto': f'«{c["nombre"]}» tiene las alertas encendidas pero '
                                            f'ni temas ni empresas vigiladas utilizables: '
                                            f'no se le arma digest.'})
            clientes = vivos

    base = [R.destino_desde_sector(s) for s in R.SECTORES_BASE] if con_sectores else []
    # Cuando hay clientes, los sectores dejan de ser el producto y pasan a ser
    # el canal genérico (interno). Se conservan a propósito: son el fallback si
    # mañana el worker no responde, y siguen sirviendo de demostración.
    return clientes + base


def cargar_articulado(avisos):
    """Baja (si cambió) el articulado y arma su índice. No es una fuente de
    señales: es de dónde sale el «por qué» de las señales del Congreso."""
    global ARTICULADO
    destino = os.path.join(DIR_CACHE, 'articulado.json')
    key = ART.CLAVE_S3
    try:
        etag = F.s3_etag(key)
        if not os.path.exists(destino) or not etag or etag != ESTADO_ETAGS.get(key):
            F.s3_bajar(key, destino)
            ESTADO_ETAGS[key] = etag
    except (RuntimeError, OSError, ValueError) as e:
        if not os.path.exists(destino):
            avisos.append({'tipo': 'fuente_error', 'pilar': 'congreso',
                           'texto': f'No se pudo leer {key} ({str(e)[:120]}): las señales '
                                    f'del Congreso van sin la lectura de su articulado.'})
            ARTICULADO = ART.VACIO
            return ARTICULADO
        avisos.append({'tipo': 'fuente_error', 'pilar': 'congreso',
                       'texto': f'No se pudo refrescar {key} ({str(e)[:120]}): se usa la '
                                f'copia local, que puede estar desactualizada.'})
    ARTICULADO = ART.cargar(destino)
    if not len(ARTICULADO):
        avisos.append({'tipo': 'fuente_error', 'pilar': 'congreso',
                       'texto': 'El articulado quedó vacío: las señales del Congreso van '
                                'sin la lectura de su texto.'})
    return ARTICULADO


def articulado_de(ev):
    """El articulado de un evento del Congreso, o None si no se ha leído."""
    m = ev.get('meta') or {}
    return ARTICULADO.buscar(pid=m.get('pid'), tab=m.get('tab'),
                             numero=m.get('numero'), camara=m.get('camara'),
                             titulo=ev.get('titulo'))


def recolectar(fecha, destinos_activos, usar_api=True, avisos=None):
    """Todos los eventos crudos del día, de las 5 fuentes."""
    avisos = avisos if avisos is not None else []
    eventos = []

    # --- 1. Radicados (el diff ya lo hizo el rastreo diario) ---------------
    hoy = dt.date.fromisoformat(fecha)
    faltantes_hoy = None
    for i in range(DIAS_NOVEDADES):
        f = (hoy - dt.timedelta(days=i)).isoformat()
        ev, faltantes = F.novedades(f)
        eventos += ev
        if i == 0:
            faltantes_hoy = faltantes
    if faltantes_hoy:
        avisos.append({'tipo': 'fuente_sin_datos', 'pilar': 'congreso',
                       'texto': 'Sin archivo de novedades hoy para: '
                                + ', '.join(faltantes_hoy)
                                + '. Puede ser un día sin sesión o el rastreo caído.'})

    # --- 2. S3: sanciones + normativa --------------------------------------
    for key, lector, pilar in (
            ('metadata/sanciones.jsonl', F.sanciones, 'regulatorio'),
            ('metadata/normativa.jsonl', F.normativa, 'ejecutivo')):
        destino = os.path.join(DIR_CACHE, os.path.basename(key))
        try:
            etag = F.s3_etag(key)
            if not os.path.exists(destino) or not etag or \
                    etag != (ESTADO_ETAGS.get(key)):
                F.s3_bajar(key, destino)
                ESTADO_ETAGS[key] = etag
            eventos += lector(destino)
        except (RuntimeError, OSError, ValueError) as e:
            avisos.append({'tipo': 'fuente_error', 'pilar': pilar,
                           'texto': f'No se pudo leer {key}: {str(e)[:200]}'})

    # --- 2.b El articulado leído (no es una fuente de señales: es el «por qué»)
    cargar_articulado(avisos)

    # --- 3. API: prensa y contratación por destino --------------------------
    if usar_api:
        for d in destinos_activos:
            k = d['k']
            # Los temas del cliente son SU consulta de prensa. Se cortan a 3
            # como en los sectores: cada tema es una petición a Google News y
            # más de tres traen eco del mismo hecho, no cobertura nueva.
            ev, errs = F.medios_sector(k, (d.get('temas') or [])[:3], dias=2)
            eventos += ev
            for e in errs:
                avisos.append({'tipo': 'api_error', 'pilar': 'medios',
                               'texto': f'prensa · {d.get("nombre", k)} · {e}'})
            ev, err, _kpis = F.contratos_destino(d)
            eventos += ev
            if err:
                avisos.append({'tipo': 'api_error', 'pilar': 'contratacion',
                               'texto': f'contratación · {d.get("nombre", k)} · {err}'})
    else:
        avisos.append({'tipo': 'omitido', 'pilar': 'medios',
                       'texto': 'Corrida sin API: no se consultó prensa ni contratación.'})
    return eventos


ESTADO_ETAGS = {}
# entidad normalizada → categorías de contratación ya vistas. Es la memoria que
# permite decir "categoría nueva para esta entidad" sin inventarlo: arranca
# vacía y se llena con cada corrida.
HISTORICO_ENTIDAD = {}

# El articulado leído del texto radicado. Se carga una vez por corrida; si no se
# puede bajar, queda vacío y el motor lo DICE en los avisos en vez de volver
# calladamente al «por qué» genérico.
ARTICULADO = ART.VACIO


# ---------------------------------------------------------------------------
# CLASIFICACIÓN
# ---------------------------------------------------------------------------

def clasificar(ev):
    """Evento crudo → lista de (sector, nivel, porque). Vacío = no interesa."""
    pilar = ev['pilar']

    if pilar == 'congreso':
        return _clasificar_congreso(ev)

    if pilar == 'regulatorio':
        row = ev.get('_row', {})
        nivel, porque = R.nivel_acto_regulatorio(row)
        texto = ' '.join([ev['titulo'], ev.get('detalle', ''),
                          row.get('descripcion') or ''])
        out = {k: (nivel, porque) for k, _h in R.destinos_de(texto)}

        fuente_sec = (row.get('sector') or '').strip()
        sancionado = row.get('sancionado') or ev.get('titulo') or ''
        for d in R.destinos():
            k = d['k']
            # 1) el sector que la propia fuente ya declaró. Antes esto era un
            #    dict fijo de tres llaves; ahora sale del `sector_sanciones` que
            #    cada destino declara, que es el mismo campo que ya elegía el
            #    consultor en el perfil. Para los 6 presets da idéntico.
            if fuente_sec and d.get('sector_sanciones') == fuente_sec:
                out.setdefault(k, (nivel, porque))
            # 2) IDENTIDAD: ¿la sancionada es una vigilada de ESTE cliente? Es
            #    la señal que justifica el producto — no llega porque el texto
            #    mencione su sector, llega porque lo nombra a él. Siempre entra,
            #    aunque el vocabulario no haya casado, y siempre en alto.
            emp = R.sancionado_vigilado(sancionado, R.empresas_de(k))
            if emp:
                out[k] = ('alto', f'acto de la Superintendencia sobre {emp["nombre"]}, '
                                  f'que este perfil vigila')
        return [(k, n, p) for k, (n, p) in out.items()]

    if pilar == 'ejecutivo':
        nivel, porque = R.nivel_normativa(ev.get('_row', {}))
        texto = ev['titulo'] + ' ' + ev.get('detalle', '')
        return [(k, nivel, porque) for k, _h in R.destinos_de(texto)]

    if pilar == 'contratacion':
        meta = ev.get('meta', {})
        k = meta.get('sector')
        d = R.destino(k) or {}
        propias = d.get('tipo') == 'cliente'
        hist = HISTORICO_ENTIDAD.get(R.norm(meta.get('entidad', '')))
        nivel, porque, cat = R.nivel_contrato(
            meta, historico_entidad=hist, empresas=R.empresas_de(k), propias=propias)
        meta['categoria'] = cat
        # La Lambda ya marcó los contratos de las vigiladas del perfil. Se
        # respeta su veredicto: sabe cosas del proveedor que acá no llegan.
        if propias and meta.get('vigilada') and nivel != 'alto':
            nivel = 'alto'
            porque = (f'contrato de {meta["vigilada"]}, que este perfil vigila '
                      f'· {porque}')
        return [(k, nivel, porque)]

    # La prensa NO se clasifica como señal propia. Entra por otra puerta:
    # `colgar_cobertura` la pega a la señal del acto estatal que corrobora, y
    # solo si nombra una empresa vigilada sin acto detrás dispara sola.
    return []


def _extra_congreso(art, k):
    """Lo que la señal lleva encima del «por qué» para que el correo lo muestre.

    `obligacion_clave` es POR DESTINO: la obligación que toca a este cliente no
    tiene por qué ser la que toca al de al lado, y mandarle siempre la primera
    del texto es volver a hablar en general.
    """
    if not art:
        return {'articulado': None}
    o, clase = R.obligacion_pertinente(art, k)
    return {'articulado': art, 'obligacion_clave': o, 'obligacion_clase': clase}


def _clasificar_congreso(ev):
    art = articulado_de(ev)

    if ev['tipo'] == 'radicado_nuevo':
        out = []
        for k, hits in R.sectores_de(ev['titulo']):
            nivel, porque, tipologia = R.nivel_radicado(
                ev['titulo'], ev['meta'].get('comision', ''), k, hits, art=art)
            ev['meta']['tipologia'] = tipologia
            extra = _extra_congreso(art, k)
            extra['hits'] = hits
            out.append((k, nivel, porque, extra))
        return out

    # trámite: primero se limpia el ruido del registro, después se mira sector
    deltas = R.deltas_utiles(ev['meta'].get('deltas'))
    if not deltas:
        return []
    ev['meta']['deltas_utiles'] = deltas
    titulo = ev['titulo'] or F.titulo_conocido(ev['meta'].get('numero', ''),
                                               ev['meta'].get('camara', ''))
    if titulo and not ev['titulo']:
        ev['titulo'] = titulo
        art = art or articulado_de(ev)          # el título recuperado abre la 3ª llave
    if not titulo:
        return []
    nivel = R.peor_nivel([d['nivel'] for d in deltas])
    etiquetas = ' · '.join(dict.fromkeys(d['etiqueta'] for d in deltas))

    out = []
    for k, hits in R.sectores_de(titulo):
        # El trámite dice QUÉ pasó hoy (aprobado en primer debate); el articulado
        # dice qué es lo que se aprobó. Las dos mitades hacen la razón completa:
        # sin la segunda, «APROBADO en primer debate» tampoco explica por qué
        # hay que hacer algo al respecto.
        if art:
            _clase, lectura = R.razon_articulado(art, k)
            porque = f'{etiquetas} — y el texto {lectura}'
        else:
            porque = (f'{etiquetas} · todavía no hemos leído su texto, así que esto '
                      f'es el movimiento del trámite, no lo que dice el articulado')
        extra = _extra_congreso(art, k)
        extra['hits'] = hits
        out.append((k, nivel, porque, extra))
    return out


def colgar_cobertura(pilares, titulares, empresas=None, propias=False):
    """La prensa se cuelga de la señal que corrobora; no dispara sola.

    Un digest en el que la prensa dispara alertas es un lector de RSS: medido,
    la prensa metía 79 de 84 señales en salud y enterraba lo que sí importaba.
    Un titular no es un hecho nuevo del Estado — es el eco de uno. Así que:

      · Si un titular habla de algo que HOY se movió en el Congreso, en un
        regulador o en el Ejecutivo, se cuelga de esa señal como cobertura
        («esto ya lo reportaron N medios»). Eso le sube el nivel a la señal:
        un proyecto que además tiene prensa encima se mueve distinto.
      · Excepción, y es la única que dispara sola: un titular que nombra una
        EMPRESA VIGILADA y no tiene acto del Estado que le corresponda. Ahí la
        prensa va por delante del registro, y esperar al acto es llegar tarde.
      · Todo lo demás se descarta y se cuenta.

    Devuelve las cifras de lo que entró y lo que se descartó, para que el digest
    pueda decirlo en vez de que el lector suponga.
    """
    # Solo los actos NORMATIVOS anclan cobertura. La contratación queda fuera a
    # propósito: un contrato no es algo que la prensa cubra, así que cruzarlo
    # con titulares solo produce coincidencias de vocabulario administrativo.
    # Medido: un contrato de vigilancia del IDIPRON en Bogotá "corroboraba" con
    # notas de México, España e Indonesia porque todas decían «seguridad social»
    # y «protección». Además el bump medio→alto contradecía su propio «por qué»,
    # que decía que aún no había histórico para afirmar novedad.
    anclas = [e for p in ('congreso', 'regulatorio', 'ejecutivo')
              for e in pilares.get(p, [])]
    usados = set()
    for ancla in anclas:
        cobertura = []
        for t in titulares:
            if id(t) in usados:
                continue
            ok, _a, comunes = R.corrobora(t['titulo'], [ancla])
            if ok:
                usados.add(id(t))
                cobertura.append({'titulo': t['titulo'], 'medio': (t.get('meta') or {}).get('medio', ''),
                                  'url': t.get('url', ''), 'comunes': comunes})
        if cobertura:
            # el conteo de medios se hace sobre TODA la cobertura, no sobre las
            # 4 que se alcanzan a mostrar: si no, el texto dice 6 y la lista 3.
            medios = len({c['medio'] for c in cobertura if c['medio']})
            ancla['cobertura'] = cobertura[:TOPE_COBERTURA]
            ancla['cobertura_total'] = len(cobertura)
            ancla['cobertura_medios'] = medios
            if ancla['nivel'] == 'medio':
                ancla['nivel'] = 'alto'
                ancla['porque'] += f' — y ya lo reportaron {medios} medios'
            else:
                ancla['porque'] += f' · lo reportaron {medios} medios'

    # Excepción: prensa sobre empresa vigilada, con hecho accionable, y sin acto
    # del Estado detrás. Los dos filtros son necesarios: solo "nombra empresa"
    # deja pasar la noticia comercial rutinaria (26 alertas altas en un día en
    # financiero, medido); solo "hecho accionable" deja pasar la crisis genérica
    # del sector, que no es de nadie en particular.
    n_cobertura = len(usados)
    sueltos, descartados_empresa = [], 0
    for t in titulares:
        if id(t) in usados:
            continue
        # Con perfil, `empresas` son SOLO las vigiladas del cliente: la prensa
        # sobre una empresa que no le importa deja de existir para él. Es el
        # filtro que más sube la precisión de este pilar.
        emp = R.empresa_en_texto(t['titulo'], empresas)
        if not emp:
            continue
        if not R.prensa_accionable(t['titulo']):
            descartados_empresa += 1
            continue
        nivel, porque = R.nivel_titular_empresa(t['titulo'], emp, propias=propias)
        t['nivel'] = nivel
        t['porque'] = porque
        t['empresa'] = emp['nombre']
        usados.add(id(t))
        sueltos.append(t)

    if sueltos:
        pilares.setdefault('medios', []).extend(sueltos[:TOPE_EMPRESA_SUELTA])

    return {'total': len(titulares), 'cobertura': n_cobertura,
            'sueltos': len(sueltos[:TOPE_EMPRESA_SUELTA]),
            'sueltos_omitidos': max(0, len(sueltos) - TOPE_EMPRESA_SUELTA),
            'empresa_sin_hecho': descartados_empresa,
            'descartados': len(titulares) - len(usados)}


def _fresco(ev, hoy):
    """¿La fecha del evento cae dentro de la ventana de su pilar?"""
    f = (ev.get('fecha') or '').strip()[:10]
    if not f:
        return True                       # sin fecha no se descarta en silencio
    try:
        d = dt.date.fromisoformat(f)
    except ValueError:
        return True
    if d > hoy + dt.timedelta(days=2):
        return False                      # fecha futura = error de captura
    return (hoy - d).days <= VENTANAS.get(ev['pilar'], 60)


# ---------------------------------------------------------------------------
# CADENCIA Y BUZÓN
# ---------------------------------------------------------------------------
# El plan del cliente decide cada cuánto le llega el correo. Pero el estado del
# motor es GLOBAL: en cuanto una señal se marca como vista, no vuelve a
# aparecer mañana. Si un cliente semanal simplemente se saltara seis corridas,
# perdería seis días de señales sin que nadie se enterara.
#
# Por eso lo que no toca enviar no se descarta: se ACUMULA en su buzón, y sale
# completo el día que le corresponde. La cadencia cambia cuándo llega el
# correo, nunca qué trae.

def momento_de(ahora=None):
    """'manana' o 'noche'. Las dos corridas son 08:45 y 20:15."""
    ahora = ahora or dt.datetime.now()
    return 'manana' if ahora.hour < 14 else 'noche'


def toca_enviar(dest, fecha, momento):
    """(bool, motivo). Los sectores no tienen plan: van en cada corrida."""
    if dest.get('tipo') != 'cliente':
        return True, ''
    cad = dest.get('cadencia') or 'cada-corrida'
    plan = dest.get('plan') or 'free'
    if cad == 'diaria':
        return (momento == 'manana'), f'cadencia diaria (plan {plan}) · se acumula hasta la mañana'
    if cad == 'semanal':
        try:
            es_lunes = dt.date.fromisoformat(fecha).weekday() == 0
        except ValueError:
            es_lunes = True
        return (momento == 'manana' and es_lunes), \
               f'cadencia semanal (plan {plan}) · se acumula hasta el lunes'
    return True, ''                      # 'cada-corrida' y cualquier valor raro


def _acumular(buzon, k, pilares, prensa_stats, fecha):
    """Guarda en el buzón del destino lo que hoy no toca enviar."""
    b = buzon.setdefault(k, {'desde': fecha, 'pilares': {}, 'prensa': {}, 'omitidos': 0})
    corte = (dt.date.fromisoformat(fecha) - dt.timedelta(days=BUZON_MAX_DIAS)).isoformat()
    for pilar, items in (pilares or {}).items():
        acum = b['pilares'].setdefault(pilar, [])
        vistos = {e.get('id') for e in acum}
        for e in items:
            if e.get('id') in vistos:
                continue
            e = dict(e)
            e['_buzon'] = fecha            # cuándo entró, para poder envejecerlo
            acum.append(e)
            vistos.add(e.get('id'))
        # se envejece y se recorta, quedándose con lo más grave y reciente
        acum = [e for e in acum if (e.get('_buzon') or fecha) >= corte]
        if len(acum) > BUZON_MAX_ITEMS:
            acum.sort(key=lambda e: (-R.orden_nivel(e.get('nivel', 'bajo')),
                                     e.get('_buzon') or '', e.get('fecha') or ''),
                      reverse=False)
            b['omitidos'] += len(acum) - BUZON_MAX_ITEMS
            acum = acum[:BUZON_MAX_ITEMS]
        b['pilares'][pilar] = acum
    for campo, valor in (prensa_stats or {}).items():
        if isinstance(valor, int):
            b['prensa'][campo] = b['prensa'].get(campo, 0) + valor
    return b


def _fusionar(pilares_hoy, guardado):
    """Buzón + lo de hoy, sin repetir. Lo guardado ya trae su propia cobertura."""
    if not guardado:
        return pilares_hoy, {}
    out = {}
    for pilar in set(list(pilares_hoy.keys()) + list((guardado.get('pilares') or {}).keys())):
        previos = list((guardado.get('pilares') or {}).get(pilar) or [])
        vistos = {e.get('id') for e in previos}
        out[pilar] = previos + [e for e in pilares_hoy.get(pilar, [])
                                if e.get('id') not in vistos]
    return out, (guardado.get('prensa') or {})


# ---------------------------------------------------------------------------
# ARMADO DEL DIGEST
# ---------------------------------------------------------------------------

def construir(fecha, destinos_activos, usar_api=True, baseline=False, momento=None):
    hoy = dt.date.fromisoformat(fecha)
    momento = momento or momento_de()
    avisos = []
    estado = cargar_estado()
    ESTADO_ETAGS.update(estado.get('etags') or {})
    HISTORICO_ENTIDAD.update(estado.get('historico_entidad') or {})
    primera_vez = not estado.get('vistos')
    sectores_activos = [d['k'] for d in destinos_activos]

    crudos = recolectar(fecha, destinos_activos, usar_api=usar_api, avisos=avisos)

    vistos = estado.setdefault('vistos', {})
    nuevos, suprimidos = [], {}
    for ev in crudos:
        cubo = vistos.setdefault(ev['pilar'], {})
        if ev['id'] in cubo:
            continue
        cubo[ev['id']] = fecha
        if not _fresco(ev, hoy):
            suprimidos[ev['pilar']] = suprimidos.get(ev['pilar'], 0) + 1
            continue
        nuevos.append(ev)

    for pilar, n in sorted(suprimidos.items()):
        avisos.append({'tipo': 'backfill', 'pilar': pilar,
                       'texto': f'{n} registros nuevos para el estado pero fuera de la '
                                f'ventana de {VENTANAS.get(pilar, 60)} días '
                                f'(backfill de la fuente): no se alertan.'})

    if primera_vez or baseline:
        estado['creado'] = estado.get('creado') or dt.datetime.now().isoformat(timespec='seconds')
        estado['ultima_corrida'] = dt.datetime.now().isoformat(timespec='seconds')
        estado['corridas'] = estado.get('corridas', 0) + 1
        estado['etags'] = dict(ESTADO_ETAGS)
        return {'fecha': fecha, 'baseline': True,
                'motivo': 'primera corrida' if primera_vez else 'baseline pedido',
                'sellados': sum(len(v) for v in vistos.values()),
                'avisos': avisos, 'sectores': {}, 'total': 0}, estado

    # --- por sector --------------------------------------------------------
    por_sector = {k: {} for k in sectores_activos}
    prensa = {k: [] for k in sectores_activos}
    for ev in nuevos:
        if ev['pilar'] == 'medios':
            k = (ev.get('meta') or {}).get('sector')
            if k in prensa:
                prensa[k].append(dict(ev))
            continue
        # El Congreso devuelve un cuarto elemento (el articulado y la obligación
        # que toca a ESE destino); los demás pilares no lo usan.
        for k, nivel, porque, *resto in clasificar(ev):
            if k not in por_sector:
                continue
            item = dict(ev)
            item.pop('_row', None)
            item['nivel'] = nivel
            item['porque'] = porque
            extra = resto[0] if resto else None
            if extra:
                # meta se copia por destino: la obligación pertinente es de este
                # cliente, no del que sigue.
                item['meta'] = dict(ev.get('meta') or {})
                item['meta'].update(extra)
            por_sector[k].setdefault(ev['pilar'], []).append(item)

    prensa_stats = {}
    for d in destinos_activos:
        k = d['k']
        prensa_stats[k] = colgar_cobertura(
            por_sector.setdefault(k, {}), prensa.get(k) or [],
            empresas=R.empresas_de(k), propias=(d.get('tipo') == 'cliente'))

    buzon = estado.setdefault('buzon', {})
    salida, en_espera = {}, []
    for d in destinos_activos:
        k = d['k']
        enviar_hoy, motivo = toca_enviar(d, fecha, momento)
        hoy_items = por_sector.get(k) or {}

        if not enviar_hoy:
            # No se pierde nada: se guarda y sale completo el día que toque.
            b = _acumular(buzon, k, hoy_items, prensa_stats.get(k, {}), fecha)
            n = sum(len(v) for v in b['pilares'].values())
            if n:
                en_espera.append({'k': k, 'nombre': d.get('nombre', k), 'acumuladas': n,
                                  'desde': b.get('desde', fecha), 'motivo': motivo})
            continue

        guardado = buzon.pop(k, None)
        # Lo que el buzón tuvo que recortar por tope se DICE. Un tope callado se
        # lee como «no pasó nada más», que es justo lo contrario de lo que pasó.
        if guardado and guardado.get('omitidos'):
            avisos.append({'tipo': 'buzon', 'pilar': 'perfiles',
                           'texto': f'«{d.get("nombre", k)}»: {guardado["omitidos"]} señales '
                                    f'quedaron por fuera del buzón (tope de {BUZON_MAX_ITEMS} '
                                    f'por pilar) mientras esperaba su día de envío.'})
        fusion, prensa_acum = _fusionar(hoy_items, guardado)
        stats = dict(prensa_stats.get(k, {}))
        for campo, valor in prensa_acum.items():          # suma de las corridas calladas
            if isinstance(valor, int):
                stats[campo] = stats.get(campo, 0) + valor

        pilares, omitidos, total, altos, bajos = {}, {}, 0, 0, 0
        for pilar, items in fusion.items():
            visibles = [e for e in items if R.orden_nivel(e['nivel']) >= 2]
            bajos += len(items) - len(visibles)
            if not visibles:
                continue
            visibles.sort(key=lambda e: (-R.orden_nivel(e['nivel']), e.get('fecha') or ''))
            total += len(visibles)
            altos += sum(1 for e in visibles if e['nivel'] == 'alto')
            if len(visibles) > TOPE_POR_PILAR:
                omitidos[pilar] = len(visibles) - TOPE_POR_PILAR
            # Dos señales que dicen lo mismo se leen como una plantilla rota,
            # aunque cada frase sea cierta: se les baja a lo que las separa.
            pilares[pilar] = R.distinguir(visibles[:TOPE_POR_PILAR])
        if total:
            salida[k] = {'k': k, 'nombre': d.get('nombre', k),
                         'comision': d.get('comision', ''),
                         'tipo': d.get('tipo', 'sector'),
                         'correo': d.get('correo', ''),
                         'plan': d.get('plan', ''),
                         'cadencia': d.get('cadencia', ''),
                         'total': total, 'altos': altos, 'bajos': bajos,
                         'prensa': stats,
                         'pilares': pilares, 'omitidos': omitidos}

    # histórico de contratación: se aprende de lo visto hoy, para que la
    # detección de "categoría nueva" tenga contra qué comparar mañana.
    for k in sectores_activos:
        for ev in (por_sector.get(k) or {}).get('contratacion', []):
            m = ev.get('meta') or {}
            ent = R.norm(m.get('entidad', ''))
            if not ent or not m.get('categoria'):
                continue
            cats = HISTORICO_ENTIDAD.setdefault(ent, [])
            if m['categoria'] not in cats:
                cats.append(m['categoria'])

    # --- salud operativa (canal interno, no va a clientes) -----------------
    operacion = None
    est_salud = F.estado_operacion()
    if est_salud:
        problemas, ctx = R.problemas_operacion(est_salud)
        operacion = {
            'estado': est_salud.get('estado'),
            'resumen': est_salud.get('resumen', ''),
            'generado': est_salud.get('generado', ''),
            'problemas': problemas, 'contexto': ctx,
            'altos': sum(1 for p in problemas if p['nivel'] == 'alto'),
        }
    else:
        avisos.append({'tipo': 'sin_estado_salud', 'pilar': 'operacion',
                       'texto': 'No hay estado.json del chequeo de salud: esta corrida '
                                'no puede distinguir «no hubo novedades» de «el '
                                'rastreo no corrió».'})

    estado['ultima_corrida'] = dt.datetime.now().isoformat(timespec='seconds')
    estado['corridas'] = estado.get('corridas', 0) + 1
    estado['etags'] = dict(ESTADO_ETAGS)
    estado['historico_entidad'] = HISTORICO_ENTIDAD
    estado = podar_estado(estado)

    digest = {'fecha': fecha, 'baseline': False, 'momento': momento,
              'generado': dt.datetime.now().isoformat(timespec='seconds'),
              'articulado': {'v': ARTICULADO.v, 'total': ARTICULADO.total,
                             'utilizables': ARTICULADO.utilizables,
                             'descartes': ARTICULADO.descartes},
              'avisos': avisos, 'sectores': salida, 'operacion': operacion,
              'en_espera': en_espera,
              'clientes': sum(1 for d in destinos_activos if d.get('tipo') == 'cliente'),
              'total': sum(s['total'] for s in salida.values()),
              'altos': sum(s['altos'] for s in salida.values()),
              'evaluados': len(nuevos)}
    return digest, estado


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def destinatarios():
    if os.path.exists(RUTA_DESTINATARIOS):
        try:
            return json.load(open(RUTA_DESTINATARIOS, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {}


def para_de(s, conf):
    """A quién le llega este digest.

    Un cliente tiene correo propio —el del dueño del perfil— y ese correo es el
    único que se usa: no cae al `_todos` de destinatarios.json, porque ese es el
    canal interno y mandarle ahí un digest de cliente sería filtrarlo. Los
    sectores siguen con el mapa de siempre.
    """
    if s.get('tipo') == 'cliente':
        correo = (s.get('correo') or '').strip()
        return [correo] if '@' in correo else []
    return conf.get(s['k']) or conf.get('_todos') or []


def main():
    ap = argparse.ArgumentParser(description='Caudal · motor de alertas')
    ap.add_argument('--fecha', default=dt.date.today().isoformat())
    ap.add_argument('--sectores', default='',
                    help='coma-separado; por defecto todos (acepta cli-<perfilId>)')
    ap.add_argument('--sin-perfiles', action='store_true',
                    help='ignora los perfiles de cliente: corre solo los sectores')
    ap.add_argument('--solo-perfiles', action='store_true',
                    help='solo clientes, sin el fallback de sectores')
    ap.add_argument('--momento', choices=('manana', 'noche'), default=None,
                    help='cuál de las dos corridas es (por defecto, según la hora)')
    ap.add_argument('--baseline', action='store_true',
                    help='sella el estado sin enviar nada')
    ap.add_argument('--dry-run', action='store_true',
                    help='calcula y escribe el digest, no envía ni guarda estado')
    ap.add_argument('--sin-api', action='store_true',
                    help='no consulta la Lambda (sin prensa ni contratación)')
    ap.add_argument('--estado', action='store_true', help='qué sabe el motor')
    args = ap.parse_args()

    if args.estado:
        e = cargar_estado()
        print(f"estado: {RUTA_ESTADO}")
        print(f"  corridas       {e.get('corridas', 0)}")
        print(f"  creado         {e.get('creado')}")
        print(f"  última corrida {e.get('ultima_corrida')}")
        for pilar, v in sorted((e.get('vistos') or {}).items()):
            print(f"  {pilar:<14} {len(v):>7} llaves vistas")
        for k, b in sorted((e.get('buzon') or {}).items()):
            n = sum(len(v) for v in (b.get('pilares') or {}).values())
            print(f"  buzón {k:<20} {n:>4} señales esperando desde {b.get('desde')}")
        return 0

    momento = args.momento or momento_de()
    avisos_destinos = []
    destinos = cargar_destinos(usar_perfiles=not args.sin_perfiles,
                               con_sectores=not args.solo_perfiles,
                               avisos=avisos_destinos)
    pedidos = [s.strip() for s in args.sectores.split(',') if s.strip()]
    if pedidos:
        destinos = [d for d in destinos if d['k'] in pedidos]
    R.registrar_destinos(destinos)
    if not destinos:
        print('Sin destinos: no hay perfiles con alertas encendidas ni sectores '
              'activos. Nada que hacer.')
        return 0
    n_cli = sum(1 for d in destinos if d.get('tipo') == 'cliente')
    print(f"Destinos: {n_cli} cliente(s) + {len(destinos) - n_cli} sector(es) "
          f"· corrida de la {'mañana' if momento == 'manana' else 'noche'}")

    digest, estado = construir(args.fecha, destinos, usar_api=not args.sin_api,
                               baseline=args.baseline, momento=momento)
    digest['avisos'] = avisos_destinos + digest.get('avisos', [])

    dest_dir = os.path.join(DIR_DIGESTS, args.fecha)
    os.makedirs(dest_dir, exist_ok=True)
    with open(os.path.join(dest_dir, 'digest.json'), 'w', encoding='utf-8') as fh:
        json.dump(digest, fh, ensure_ascii=False, indent=1)

    if digest.get('baseline'):
        print(f"BASELINE ({digest['motivo']}): {digest['sellados']} llaves selladas.")
        print("No se envía nada. La próxima corrida ya alerta solo lo nuevo.")
        for a in digest['avisos']:
            print(f"  aviso · {a['pilar']}: {a['texto']}")
        if not args.dry_run:
            guardar_estado(estado)
        return 0

    print(f"Digest {digest['fecha']}: {digest['total']} señales "
          f"({digest['altos']} altas) en {len(digest['sectores'])} destinos "
          f"· {digest['evaluados']} eventos nuevos evaluados")
    for a in digest['avisos']:
        print(f"  aviso · {a['pilar']}: {a['texto']}")
    for w in digest.get('en_espera') or []:
        print(f"  en espera · {w['nombre']}: {w['acumuladas']} señales guardadas "
              f"desde {w['desde']} — {w['motivo']}")

    op = digest.get('operacion') or {}
    hay_operacion = bool(op.get('problemas'))

    # --- SILENCIO LEGÍTIMO -------------------------------------------------
    # Un día sin nada que decir es el caso normal, no una falla. Mandar un
    # correo vacío para "demostrar que el sistema vive" es cómo un canal de
    # alertas se vuelve ruido de fondo y deja de abrirse: a la tercera semana
    # de digests vacíos, el que importa tampoco se lee. Si el rastreo se cayó,
    # eso NO es silencio — sale por el canal de operación.
    if not digest['sectores'] and not hay_operacion:
        print('\nSin novedades de nivel suficiente. No se envía correo '
              '(el silencio es una salida válida del motor).')
        if not args.dry_run:
            guardar_estado(estado)
        return 0

    conf = destinatarios()
    resultados = []
    for k, s in digest['sectores'].items():
        html = render.digest_html(digest, s)
        txt = render.digest_texto(digest, s)
        with open(os.path.join(dest_dir, f'{k}.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        with open(os.path.join(dest_dir, f'{k}.txt'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        pr = s.get('prensa') or {}
        extra = (f" · prensa: {pr.get('cobertura', 0)} como cobertura, "
                 f"{pr.get('sueltos', 0)} sueltas, {pr.get('descartados', 0)} descartadas"
                 if pr.get('total') else '')
        quien = f" → {s['correo']}" if s.get('tipo') == 'cliente' else ''
        print(f"  · {s['nombre']:<32} {s['total']:>3} señales ({s['altos']} altas)"
              f"{quien}{extra}")
        para = para_de(s, conf)
        if s.get('tipo') == 'cliente' and not para:
            print(f'      ⚠ perfil sin correo utilizable: el digest queda en disco.')
        if not args.dry_run:
            resultados.append(sender.enviar(
                asunto=render.asunto(digest, s), html=html, texto=txt,
                para=para, etiqueta=f"{args.fecha}-{k}", dir_salida=dest_dir))

    if hay_operacion:
        html = render.operacion_html(digest)
        txt = render.operacion_texto(digest)
        with open(os.path.join(dest_dir, 'operacion.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        with open(os.path.join(dest_dir, 'operacion.txt'), 'w', encoding='utf-8') as fh:
            fh.write(txt)
        print(f"  · {'OPERACIÓN (interno)':<32} {len(op['problemas']):>3} problemas "
              f"({op['altos']} críticos)")
        if not args.dry_run:
            para = conf.get('_operacion') or conf.get('_todos') or []
            resultados.append(sender.enviar(
                asunto=render.asunto_operacion(digest), html=html, texto=txt,
                para=para, etiqueta=f"{args.fecha}-operacion", dir_salida=dest_dir))

    if args.dry_run:
        print(f"\n--dry-run: escrito en {dest_dir}, sin enviar y sin guardar estado.")
        return 0

    guardar_estado(estado)
    sender.reportar(resultados)
    print(f"\nArtefactos en {dest_dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
