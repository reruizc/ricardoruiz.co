#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — envío por Resend.

El dominio ricardoruiz.co ya está verificado en Resend, así que se envía desde
contacto@ricardoruiz.co. La API key NO vive en el repo: se lee de la variable
de entorno RESEND_API_KEY.

Sin la key el motor NO falla y NO se calla: escribe el digest en disco y deja
una COLA (`pendientes.json`) con lo que habría mandado. Cuando la key exista,
un solo comando la vacía:

    RESEND_API_KEY=... python3 sender.py --pendientes tools/caudal/alertas/datos/digests/2026-08-02

Eso importa porque el estado del motor ya avanzó: si un correo se pierde
porque faltaba la key, esas señales no vuelven a aparecer mañana.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

RESEND_URL = 'https://api.resend.com/emails'
REMITENTE = os.environ.get('CAUDAL_ALERTAS_FROM', 'Caudal <contacto@ricardoruiz.co>')
RESPONDER_A = os.environ.get('CAUDAL_ALERTAS_REPLY_TO', 'contacto@ricardoruiz.co')
ARCHIVO_COLA = 'pendientes.json'


def hay_key():
    return bool(os.environ.get('RESEND_API_KEY', '').strip())


def _post(payload, key, timeout=30):
    req = urllib.request.Request(
        RESEND_URL, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Authorization': f'Bearer {key}',
                 'Content-Type': 'application/json',
                 'User-Agent': 'caudal-alertas/1.0 (+ricardoruiz.co)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8') or '{}')


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


def enviar(asunto, html, texto, para, etiqueta='', dir_salida=None):
    """Manda un digest. Devuelve {estado, etiqueta, para, detalle}.

    estado ∈ enviado · sin_key · sin_destinatarios · error
    """
    para = [p for p in (para or []) if p and '@' in p]
    base = {'etiqueta': etiqueta, 'para': para, 'asunto': asunto}

    if not para:
        return dict(base, estado='sin_destinatarios',
                    detalle='No hay correos configurados para este sector '
                            '(ver destinatarios.json).')

    key = os.environ.get('RESEND_API_KEY', '').strip()
    if not key:
        _encolar(dir_salida, dict(base, estado='pendiente'))
        return dict(base, estado='sin_key',
                    detalle='RESEND_API_KEY no está en el entorno. El digest quedó '
                            'en disco y encolado en pendientes.json.')

    payload = {'from': REMITENTE, 'to': para, 'subject': asunto,
               'html': html, 'text': texto, 'reply_to': RESPONDER_A}
    try:
        r = _post(payload, key)
        return dict(base, estado='enviado', detalle=r.get('id', ''))
    except urllib.error.HTTPError as ex:
        cuerpo = ''
        try:
            cuerpo = ex.read().decode('utf-8')[:300]
        except OSError:
            pass
        _encolar(dir_salida, dict(base, estado='pendiente'))
        return dict(base, estado='error', detalle=f'HTTP {ex.code}: {cuerpo}')
    except (urllib.error.URLError, OSError, ValueError) as ex:
        _encolar(dir_salida, dict(base, estado='pendiente'))
        return dict(base, estado='error', detalle=f'{type(ex).__name__}: {str(ex)[:200]}')


def reportar(resultados):
    if not resultados:
        return
    print('\nEnvío:')
    for r in resultados:
        destino = ', '.join(r.get('para') or []) or '—'
        print(f"  [{r['estado']:<19}] {r.get('etiqueta', ''):<24} → {destino}")
        if r.get('detalle') and r['estado'] != 'enviado':
            print(f"      {r['detalle']}")
    if any(r['estado'] == 'sin_key' for r in resultados):
        print('\n  ⚠ Falta RESEND_API_KEY. Los digests están en disco y encolados.')
        print('    Para vaciar la cola cuando exista la key:')
        print('    RESEND_API_KEY=... python3 tools/caudal/alertas/sender.py '
              '--pendientes <carpeta-del-digest>')


def vaciar_cola(dir_digest):
    """Reenvía lo que quedó pendiente en una carpeta de digest."""
    ruta = os.path.join(dir_digest, ARCHIVO_COLA)
    if not os.path.exists(ruta):
        print(f'No hay cola en {ruta}')
        return 0
    cola = json.load(open(ruta, encoding='utf-8'))
    if not hay_key():
        print('RESEND_API_KEY sigue sin estar en el entorno. No se envió nada.')
        return 1
    quedan, enviados = [], 0
    for c in cola:
        sector = (c.get('etiqueta') or '').split('-')[-1]
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
    a = ap.parse_args()
    if a.pendientes:
        sys.exit(vaciar_cola(a.pendientes))
    if a.probar:
        r = enviar('Caudal · prueba de envío',
                   '<p style="font-family:Helvetica,Arial">Prueba del motor de '
                   'alertas de Caudal. Si llegó esto, Resend está bien cableado.</p>',
                   'Prueba del motor de alertas de Caudal.', [a.probar], 'prueba')
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r['estado'] == 'enviado' else 1)
    print(f'RESEND_API_KEY presente: {hay_key()}')
    print(f'remitente: {REMITENTE}')
