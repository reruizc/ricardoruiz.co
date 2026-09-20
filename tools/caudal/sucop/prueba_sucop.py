#!/usr/bin/env python3
"""Pruebas de harvest_sucop.py SIN tocar www.sucop.gov.co.

`subprocess.run` y `time.sleep` están sustituidos, así que los reintentos y sus
esperas de 5/15/45 s se prueban en milisegundos. Cada caso es una falla real de
producción: los tres rc=1 de sep-2026 fueron transitorios y de tres clases
distintas, y cada uno abortó la cosecha entera al primer golpe porque este era
el único harvester del pilar sin reintentos.

    python3 tools/caudal/sucop/prueba_sucop.py      # sale con 1 si algo falla
"""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'hs', str(Path(__file__).resolve().parent / 'harvest_sucop.py'))
hs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hs)

FALLAS = []


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


class CurlFalso:
    """respuestas: 'ok' | 'timeout' | rc entero | texto crudo que no es JSON."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.n = 0

    def __call__(self, cmd, **kw):
        self.n += 1
        r = self.respuestas.pop(0) if self.respuestas else 'ok'
        if r == 'timeout':
            raise subprocess.TimeoutExpired(cmd, 1)

        class R:
            returncode = r if isinstance(r, int) else 0
            stdout = (json.dumps({'value': [{'Name': 'x'}]}).encode() if r == 'ok'
                      else (r.encode() if isinstance(r, str) else b''))
        return R()


def con(respuestas):
    falso = CurlFalso(respuestas)
    real_run, real_sleep = subprocess.run, time.sleep
    dormido = []
    subprocess.run, time.sleep = falso, lambda s: dormido.append(s)
    try:
        return hs.curl_json('https://x/y') + (falso, dormido)
    finally:
        subprocess.run, time.sleep = real_run, real_sleep


print('A · lo que antes mataba la cosecha al primer golpe, ahora se reintenta')
d, err, f, dormido = con([28, 'ok'])
ok(err is None and d is not None, 'timeout y luego ok → devuelve el dato')
ok(f.n == 2, 'le bastaron 2 intentos')
ok(dormido == [5], f'esperó 5 s entre medio (backoff), no 0: {dormido}')

d, err, f, dormido = con([6, 6, 'ok'])
ok(err is None and f.n == 3, 'DNS caído dos veces y a la tercera pasa (el Mac despertando)')
ok(dormido == [5, 15], f'las esperas crecen: {dormido}')

d, err, f, dormido = con(['<html>error 500</html>', 'ok'])
ok(err is None, 'una respuesta que no es JSON también se reintenta')

d, err, f, dormido = con(['timeout', 'timeout', 'timeout', 'ok'])
ok(err is None and f.n == 4, 'aguanta 3 fallos seguidos y salva la corrida al 4º')
ok(dormido == [5, 15, 45], f'y usa las tres esperas: {dormido}')

print('\nB · pero no se reintenta eternamente ni por gusto')
d, err, f, dormido = con([28, 28, 28, 28])
ok(d is None and err is not None, 'si fallan los 4 intentos, falla de verdad')
ok(f.n == 4, f'y son 4, no más ({f.n})')

# Un error de la propia API no se reintenta: la petición está mal hecha y va a
# estar igual de mal dentro de 45 s. Se cuenta cuántas veces se llamó de verdad.
llamadas = []
antes, antes_sleep = hs._una_vez, time.sleep
hs._una_vez = lambda u, t: (llamadas.append(1), (None, 'sharepoint: el campo X no existe'))[1]
time.sleep = lambda *_: None
try:
    d, err = hs.curl_json('https://x/y')
finally:
    hs._una_vez, time.sleep = antes, antes_sleep
ok(len(llamadas) == 1, f'un error `sharepoint:` se intenta UNA vez, no 4 ({len(llamadas)})')
ok(d is None and 'sharepoint:' in err, 'y devuelve el error tal cual')

print('\nC · el error dice de quién fue la culpa')
d, err, f, _ = con([6, 6, 6, 6])
ok('DNS' in err and 'ESTA máquina' in err, f'rc=6 se traduce: {err[:70]}')
d, err, f, _ = con([28, 28, 28, 28])
ok('no respondió a tiempo' in err, f'rc=28 se traduce: {err[:60]}')
d, err, f, _ = con(['<html>nope</html>'] * 4)
ok('bytes que empiezan por' in err, f'json inválido muestra qué llegó: {err[:75]}')

print('\nD · el reintento no se traga un fallo real')
ok(hs.ESPERAS == (5, 15, 45), f'las esperas siguen siendo las documentadas: {hs.ESPERAS}')
ok(6 in hs.CURL_RC and 28 in hs.CURL_RC, 'los rc que se vieron en producción están traducidos')

print()
if FALLAS:
    print(f'✗ {len(FALLAS)} fallas')
    sys.exit(1)
print('✓ todo bien')
