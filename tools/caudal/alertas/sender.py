#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — envío del digest.

Hay DOS caminos hasta la bandeja del cliente, y el motor escoge solo:

  · DIRECTO — este proceso habla con Resend con su propia RESEND_API_KEY.
  · WORKER  — este proceso le pasa el correo ya renderizado al worker rr-auth
              (`POST /caudal/alertas/enviar`, mismo secreto de servicio que ya
              usa para leer los perfiles) y el worker lo despacha con SU key.

El segundo existe por un problema real: la key local resultó ser de otra cuenta
de Resend, donde ricardoruiz.co no está verificado, así que todo envío moría en
403 y el digest se encolaba. El worker, en cambio, lleva meses mandando correo
verificado desde ese dominio (verificaciones de cuenta, invitaciones del Lab).
La casa ya tenía una llave buena; esto solo la usa.

La elección NO es una preferencia escrita a mano: se decide por CAPACIDAD (ver
`transporte()`), preguntándole a Resend si la key local puede mandar desde el
remitente. Si mañana aparece una key buena en el entorno, el motor vuelve solo
al camino directo sin tocar una línea. `--diagnostico` dice cuál va a usar hoy.

Si no sirve ninguno, el motor NO falla y NO se calla: escribe el digest en disco
y deja una COLA (`pendientes.json`) con lo que habría mandado:

    python3 sender.py --pendientes tools/caudal/alertas/datos/digests/2026-08-02

Eso importa porque el estado del motor ya avanzó: si un correo se pierde, esas
señales no vuelven a aparecer mañana.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

RESEND_URL = 'https://api.resend.com/emails'
RESEND_DOMINIOS_URL = 'https://api.resend.com/domains'
REMITENTE = os.environ.get('CAUDAL_ALERTAS_FROM', 'Caudal <contacto@ricardoruiz.co>')
RESPONDER_A = os.environ.get('CAUDAL_ALERTAS_REPLY_TO', 'contacto@ricardoruiz.co')
ARCHIVO_COLA = 'pendientes.json'

# Worker rr-auth: el mismo destino y el mismo secreto que usa fuentes.py para
# leer los perfiles de cliente. Se repiten aquí (en vez de importar fuentes)
# para que sender.py siga corriendo solo, que es como se vacía una cola.
WORKER = os.environ.get('CAUDAL_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
RUTA_ENVIO = '/caudal/alertas/enviar'
UA = 'caudal-alertas/1.0 (+ricardoruiz.co)'


def hay_key():
    return bool(os.environ.get('RESEND_API_KEY', '').strip())


def hay_token_worker():
    return bool(os.environ.get('CAUDAL_ALERTAS_TOKEN', '').strip())


def _post(payload, key, timeout=30):
    req = urllib.request.Request(
        RESEND_URL, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Authorization': f'Bearer {key}',
                 'Content-Type': 'application/json',
                 'User-Agent': 'caudal-alertas/1.0 (+ricardoruiz.co)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8') or '{}')


def dominio_de(remitente):
    """`Caudal <contacto@ricardoruiz.co>` → `ricardoruiz.co`."""
    m = re.search(r'@([A-Za-z0-9.\-]+)', remitente or '')
    return m.group(1).lower() if m else ''


# ── ¿por dónde se puede mandar hoy? ────────────────────────────────────────
# El sondeo se hace UNA vez por proceso: una corrida manda ~7 digests y no
# tiene sentido preguntarle a Resend lo mismo siete veces.
_CAPACIDAD = {}


def capacidad_directa(timeout=20):
    """¿La RESEND_API_KEY local puede mandar desde REMITENTE?

    → (estado, detalle, dominios) con estado ∈
      ok · sin_key · sin_dominios · no_autorizada · key_rechazada · indeterminado

    Existe por un fallo real y caro de depurar: la key configurada era válida
    —Resend la aceptaba— pero pertenecía a OTRA cuenta, donde ricardoruiz.co no
    está verificado. El motor solo veía «HTTP 403: domain is not verified», que
    se lee como «hay que verificar el dominio» cuando lo que pasaba era «esta
    key es de otra cuenta». Preguntar por /domains distingue los dos casos en un
    segundo, y esa distinción decide por dónde sale el correo.
    """
    if _CAPACIDAD:
        return _CAPACIDAD['r']

    key = os.environ.get('RESEND_API_KEY', '').strip()
    dom = dominio_de(REMITENTE)
    if not key:
        r = ('sin_key', 'RESEND_API_KEY no está en el entorno', [])
        _CAPACIDAD['r'] = r
        return r
    try:
        req = urllib.request.Request(
            RESEND_DOMINIOS_URL, method='GET',
            headers={'Authorization': f'Bearer {key}', 'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            datos = json.loads(resp.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as ex:
        r = ('key_rechazada', f'Resend rechazó la key: HTTP {ex.code}. ¿Está revocada?', [])
        _CAPACIDAD['r'] = r
        return r
    except (urllib.error.URLError, OSError, ValueError) as ex:
        # No se pudo preguntar. NO se concluye que la key esté mal: puede ser la
        # red. Se marca indeterminado y el envío se intenta igual.
        r = ('indeterminado', f'No se pudo consultar Resend: {type(ex).__name__}: {ex}', [])
        _CAPACIDAD['r'] = r
        return r

    dominios = [(d.get('name') or '', d.get('status') or '') for d in (datos.get('data') or [])]
    if not dominios:
        r = ('sin_dominios', 'La cuenta de esta key no tiene ningún dominio verificado', [])
    elif any(n.lower() == dom and s == 'verified' for n, s in dominios):
        r = ('ok', f'{dom} está verificado en la cuenta de esta key', dominios)
    else:
        r = ('no_autorizada',
             f'{dom} NO está verificado en la cuenta de esta key '
             f'(esa cuenta tiene: {", ".join(n for n, _ in dominios) or "nada"})',
             dominios)
    _CAPACIDAD['r'] = r
    return r


def transporte():
    """Por dónde sale el correo → (nombre, motivo). nombre ∈ directo·worker·ninguno.

    La regla es de CAPACIDAD, no de preferencia: gana el camino directo cuando
    de verdad puede mandar, y el worker es la red de seguridad. Así, el día que
    aparezca una key buena en el entorno, el motor vuelve solo a mandar directo
    sin que nadie cambie configuración.

    `CAUDAL_ALERTAS_TRANSPORTE=directo|worker` fuerza uno (para depurar).
    """
    forzado = (os.environ.get('CAUDAL_ALERTAS_TRANSPORTE') or '').strip().lower()
    if forzado == 'worker':
        return ('worker', 'forzado por CAUDAL_ALERTAS_TRANSPORTE') if hay_token_worker() \
            else ('ninguno', 'CAUDAL_ALERTAS_TRANSPORTE=worker pero falta CAUDAL_ALERTAS_TOKEN')
    if forzado == 'directo':
        return ('directo', 'forzado por CAUDAL_ALERTAS_TRANSPORTE') if hay_key() \
            else ('ninguno', 'CAUDAL_ALERTAS_TRANSPORTE=directo pero falta RESEND_API_KEY')

    estado, detalle, _ = capacidad_directa()
    if estado == 'ok':
        return 'directo', detalle
    # La key local no sirve (o no se sabe): el worker manda con la suya.
    if hay_token_worker():
        if estado == 'indeterminado':
            # Duda razonable: se intenta directo igual y, si falla, `enviar`
            # cae al worker. Enrutar por una caída de red sería precipitado.
            return 'directo', f'{detalle} — se intenta directo; si falla, sale por el worker'
        return 'worker', f'la key local no sirve ({estado}: {detalle})'
    if hay_key():
        # Sin worker no hay alternativa: se intenta y, si falla, se encola.
        return 'directo', f'{detalle} — sin worker de respaldo'
    return 'ninguno', 'no hay RESEND_API_KEY ni CAUDAL_ALERTAS_TOKEN'


def diagnostico():
    """Imprime por dónde va a salir el correo y por qué. Devuelve rc."""
    dom = dominio_de(REMITENTE)
    print(f'remitente : {REMITENTE}   (dominio: {dom or "?"})')
    print(f'RESEND_API_KEY      : {"presente" if hay_key() else "AUSENTE"}')
    print(f'CAUDAL_ALERTAS_TOKEN: {"presente" if hay_token_worker() else "AUSENTE"}')

    estado, detalle, dominios = capacidad_directa()
    print(f'\ncamino directo → {estado}: {detalle}')
    for n, s in dominios:
        print(f'  · {n}  [{s}]')

    via, motivo = transporte()
    print(f'\nVA A USAR: {via.upper()}')
    print(f'  {motivo}')
    if via == 'worker':
        print(f'  El worker ({WORKER}{RUTA_ENVIO}) despacha con SU propia key de')
        print('  Resend, la que ya manda verificaciones e invitaciones del Lab.')
        print('  Para volver al camino directo basta poner en')
        print(f'  ~/.config/caudal/alertas.env una key de la cuenta donde {dom}')
        print('  SÍ está verificado: el motor lo detecta solo.')
    elif via == 'ninguno':
        print('  Los digests quedan en disco y encolados en pendientes.json.')
    return 0 if via != 'ninguno' else 1


def _enviar_por_worker(asunto, html, texto, para, etiqueta=''):
    """Le pasa el correo ya renderizado al worker rr-auth. → (ok, detalle).

    El worker fija remitente y reply-to, exige que el asunto lleve la marca
    «Caudal ·» y solo acepta destinatarios que ya tienen acceso a Caudal. Todo
    eso es del otro lado a propósito: aunque este token se filtre, no sirve para
    mandarle cualquier cosa a cualquiera desde nuestro dominio.
    """
    token = (os.environ.get('CAUDAL_ALERTAS_TOKEN') or '').strip()
    if not token:
        return False, 'falta CAUDAL_ALERTAS_TOKEN (ver ~/.config/caudal/alertas.env)'
    cuerpo = json.dumps({'asunto': asunto, 'html': html, 'texto': texto,
                         'para': para, 'etiqueta': etiqueta}).encode('utf-8')
    req = urllib.request.Request(
        WORKER.rstrip('/') + RUTA_ENVIO, data=cuerpo, method='POST',
        headers={'X-Caudal-Service': token, 'Content-Type': 'application/json',
                 'Accept': 'application/json', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as ex:
        det = ''
        try:
            det = ex.read().decode('utf-8')[:300]
        except OSError:
            pass
        # El worker responde 404 «Ruta no encontrada» cuando el secreto no
        # coincide: la ruta finge no existir. Sin esta pista se busca en el
        # lugar equivocado.
        pista = ' (¿el token del worker y el local son el mismo? ¿está desplegada la ruta?)' \
            if ex.code == 404 else ''
        return False, f'worker HTTP {ex.code}: {det}{pista}'
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as ex:
        return False, f'worker {type(ex).__name__}: {str(ex)[:200]}'

    if not d.get('ok'):
        return False, f"worker rechazó: {d.get('error') or 'sin motivo'}"
    # Un destinatario descartado NO puede pasar en silencio: es un cliente que
    # no va a recibir su digest.
    aviso = ''
    for x in (d.get('rechazados') or []):
        aviso += f" · SIN ENVIAR a {x.get('correo')}: {x.get('motivo')}"
    return True, f"{d.get('id', '')} [worker]{aviso}"


def _encolar(dir_salida, registro):
    if not dir_salida:
        return
    ruta = os.path.join(dir_salida, ARCHIVO_COLA)
    cola = []
    if os.path.exists(ruta):
        try:
            cola = json.load(open(ruta, encoding='utf-8'))
        except (ValueError, OSError):
            cola = []
    cola = [c for c in cola if c.get('etiqueta') != registro.get('etiqueta')]
    cola.append(registro)
    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(cola, fh, ensure_ascii=False, indent=1)


def _enviar_directo(asunto, html, texto, para):
    """Resend con la key de este proceso. → (ok, detalle)."""
    key = os.environ.get('RESEND_API_KEY', '').strip()
    if not key:
        return False, 'RESEND_API_KEY no está en el entorno'
    payload = {'from': REMITENTE, 'to': para, 'subject': asunto,
               'html': html, 'text': texto, 'reply_to': RESPONDER_A}
    try:
        r = _post(payload, key)
        return True, r.get('id', '')
    except urllib.error.HTTPError as ex:
        cuerpo = ''
        try:
            cuerpo = ex.read().decode('utf-8')[:300]
        except OSError:
            pass
        pista = ''
        if ex.code == 403 and 'not verified' in cuerpo:
            # Resend dice «verificá el dominio», pero la causa frecuente es otra:
            # la key es de una cuenta distinta a aquella donde el dominio ya está
            # verificado. Sin esta pista se pierde el tiempo en el panel equivocado.
            pista = (f' ← el dominio del remitente ({dominio_de(REMITENTE)}) no está '
                     f'verificado EN LA CUENTA DE ESTA KEY. Correr: '
                     f'python3 sender.py --diagnostico')
        return False, f'HTTP {ex.code}: {cuerpo}{pista}'
    except (urllib.error.URLError, OSError, ValueError) as ex:
        return False, f'{type(ex).__name__}: {str(ex)[:200]}'


def enviar(asunto, html, texto, para, etiqueta='', dir_salida=None):
    """Manda un digest por el transporte que sirva. → {estado, etiqueta, para, detalle}.

    estado ∈ enviado · sin_transporte · sin_destinatarios · error

    Si el camino elegido falla y el otro está disponible, se intenta el otro
    ANTES de encolar: el objetivo es que el correo llegue, no defender un
    transporte. Solo si fallan los dos queda en la cola.
    """
    para = [p for p in (para or []) if p and '@' in p]
    base = {'etiqueta': etiqueta, 'para': para, 'asunto': asunto}

    if not para:
        return dict(base, estado='sin_destinatarios',
                    detalle='No hay correos configurados para este sector '
                            '(ver destinatarios.json).')

    via, motivo = transporte()
    if via == 'ninguno':
        _encolar(dir_salida, dict(base, estado='pendiente'))
        return dict(base, estado='sin_transporte',
                    detalle=f'{motivo}. El digest quedó en disco y encolado en '
                            f'pendientes.json.')

    intentos = [via] + [otro for otro in ('worker', 'directo') if otro != via]
    fallos = []
    for i, v in enumerate(intentos):
        if v == 'worker' and not hay_token_worker():
            continue
        if v == 'directo' and not hay_key():
            continue
        if v == 'worker':
            ok, detalle = _enviar_por_worker(asunto, html, texto, para, etiqueta)
        else:
            ok, detalle = _enviar_directo(asunto, html, texto, para)
        if ok:
            # Si hubo que cambiar de transporte, se dice: es información de
            # operación (algo dejó de funcionar), no ruido.
            respaldo = f' (tras fallar {intentos[0]}: {fallos[0]})' if i and fallos else ''
            return dict(base, estado='enviado', via=v, detalle=f'{detalle}{respaldo}')
        fallos.append(f'{v}: {detalle}')

    _encolar(dir_salida, dict(base, estado='pendiente'))
    return dict(base, estado='error', detalle=' | '.join(fallos))


def reportar(resultados):
    if not resultados:
        return
    print('\nEnvío:')
    for r in resultados:
        destino = ', '.join(r.get('para') or []) or '—'
        via = f" via {r['via']}" if r.get('via') else ''
        print(f"  [{r['estado']}{via:<12}] {r.get('etiqueta', ''):<24} → {destino}")
        if r.get('detalle') and r['estado'] != 'enviado':
            print(f"      {r['detalle']}")
        elif r.get('via') == 'worker' and 'SIN ENVIAR' in (r.get('detalle') or ''):
            print(f"      {r['detalle']}")
    if any(r['estado'] in ('sin_transporte', 'error') for r in resultados):
        print('\n  ⚠ Hay digests sin entregar. Están en disco y encolados.')
        print('    Ver por dónde puede salir el correo:')
        print('    python3 tools/caudal/alertas/sender.py --diagnostico')
        print('    Y para vaciar la cola:')
        print('    python3 tools/caudal/alertas/sender.py --pendientes <carpeta-del-digest>')


def _sector_de(etiqueta):
    """`2026-08-03-cli-ee55ff66` → `cli-ee55ff66` (el nombre del archivo).

    La etiqueta es `{fecha ISO}-{sector}` y la fecha mide 10 caracteres. Partir
    por el último guion parece equivalente y no lo es: con los digests de
    cliente (`cli-<id>`) devuelve solo el trozo final del id, no encuentra el
    HTML y el correo de un cliente se queda en la cola para siempre.
    """
    e = etiqueta or ''
    return e[11:] if len(e) > 11 and e[10] == '-' else e.split('-')[-1]


def vaciar_cola(dir_digest):
    """Reenvía lo que quedó pendiente en una carpeta de digest."""
    ruta = os.path.join(dir_digest, ARCHIVO_COLA)
    if not os.path.exists(ruta):
        print(f'No hay cola en {ruta}')
        return 0
    cola = json.load(open(ruta, encoding='utf-8'))
    via, motivo = transporte()
    if via == 'ninguno':
        print(f'Sigue sin haber por dónde mandar ({motivo}). No se envió nada.')
        return 1
    print(f'Transporte: {via} — {motivo}')
    quedan, enviados = [], 0
    for c in cola:
        sector = _sector_de(c.get('etiqueta'))
        fhtml = os.path.join(dir_digest, f'{sector}.html')
        ftxt = os.path.join(dir_digest, f'{sector}.txt')
        if not os.path.exists(fhtml):
            print(f"  falta {fhtml} — se conserva en la cola")
            quedan.append(c)
            continue
        r = enviar(asunto=c['asunto'],
                   html=open(fhtml, encoding='utf-8').read(),
                   texto=open(ftxt, encoding='utf-8').read() if os.path.exists(ftxt) else '',
                   para=c.get('para'), etiqueta=c.get('etiqueta'))
        print(f"  [{r['estado']}] {c.get('etiqueta')} {r.get('detalle','')}")
        if r['estado'] == 'enviado':
            enviados += 1
        else:
            quedan.append(c)
    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(quedan, fh, ensure_ascii=False, indent=1)
    print(f'Enviados {enviados} · quedan {len(quedan)}')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Caudal · envío de alertas')
    ap.add_argument('--pendientes', help='carpeta de digest cuya cola se vacía')
    ap.add_argument('--probar', help='manda un correo de prueba a esta dirección')
    ap.add_argument('--diagnostico', action='store_true',
                    help='por dónde va a salir el correo y por qué (no envía nada)')
    a = ap.parse_args()
    if a.diagnostico:
        sys.exit(diagnostico())
    if a.pendientes:
        sys.exit(vaciar_cola(a.pendientes))
    if a.probar:
        r = enviar('Caudal · prueba de envío',
                   '<p style="font-family:Helvetica,Arial">Prueba del motor de '
                   'alertas de Caudal. Si llegó esto, el envío está bien cableado.</p>',
                   'Prueba del motor de alertas de Caudal.', [a.probar], 'prueba')
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r['estado'] == 'enviado' else 1)
    sys.exit(diagnostico())
