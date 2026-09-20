#!/usr/bin/env python3
"""Pruebas de harvest_banrep.py SIN tocar www.banrep.gov.co.

`curl` está sustituido, así que el WAF de Radware se simula en milisegundos.
Cada caso de acá es una falla que ya ocurrió en producción: entre el 5 y el
19-sep-2026 la etapa pasó de 0 fallos en 42 corridas a 9 en 30.

    python3 tools/caudal/supers/prueba_banrep.py      # sale con 1 si algo falla
"""
import importlib.util
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'hb', str(Path(__file__).resolve().parent / 'harvest_banrep.py'))
hb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hb)

FALLAS = []
CAPTCHA = '<html><head><title>Radware Bot Manager Captcha</title>' + 'x' * 500 + \
          '<script src="https://cdn.perfdrive.com/aperture/aperture.js"></script></html>'


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


class CurlFalso:
    """Reemplaza subprocess.run y va anotando qué banderas pidió cada intento."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)   # 'ok' | 'captcha' | 'timeout'
        self.cmds = []

    def __call__(self, cmd, **kw):
        self.cmds.append(cmd)
        r = self.respuestas.pop(0) if self.respuestas else 'ok'
        if r == 'timeout':
            raise subprocess.TimeoutExpired(cmd, 1)
        cuerpo = CAPTCHA if r == 'captcha' else '<html>' + 'PAGINA REAL ' * 5000 + '</html>'

        class R:
            returncode = 0
            stdout = cuerpo.encode('utf-8')
        return R()


def con_curl(respuestas, jar):
    """Corre hb.curl con subprocess.run y time.sleep sustituidos."""
    falso = CurlFalso(respuestas)
    hb.COOKIES = jar
    real_run, real_sleep = subprocess.run, time.sleep
    subprocess.run, time.sleep = falso, lambda *_: None
    try:
        try:
            return hb.curl('https://x/y'), falso, None
        except RuntimeError as e:
            return None, falso, e
    finally:
        subprocess.run, time.sleep = real_run, real_sleep


print('A · el frasco de cookies va en cada petición')
jar = Path(tempfile.mkdtemp()) / 'ck.txt'
jar.write_text('# cookies\n')
body, falso, err = con_curl(['ok'], jar)
cmd = falso.cmds[0]
ok(body is not None and err is None, 'una respuesta buena vuelve tal cual')
ok('-b' in cmd and cmd[cmd.index('-b') + 1] == str(jar), '-b (leer cookies) siempre')
ok('-c' in cmd and cmd[cmd.index('-c') + 1] == str(jar), '-c (guardar cookies) por defecto')

print('\nB · el captcha se reconoce, y el reintento aprovecha la cookie que trajo')
body, falso, err = con_curl(['captcha', 'ok'], jar)
ok(body is not None and 'PAGINA REAL' in body,
   'captcha y luego ok → devuelve la página: el primer golpe paga la entrada')
ok(len(falso.cmds) == 2, 'le bastaron 2 intentos')
ok(jar.exists(), 'y el frasco sigue ahí')

print('\nC · captcha en los TRES intentos: el frasco está quemado y se tira')
jar.write_text('# cookies\n')
body, falso, err = con_curl(['captcha', 'captcha', 'captcha'], jar)
ok(body is None and 'PerfDrive' in str(err), 'falla y lo dice')
ok(not jar.exists(), 'el frasco se vació: reusar esa identidad mañana repite el bloqueo')

print('\nD · un timeout NO quema el frasco (la cookie no tiene la culpa)')
jar.write_text('# cookies\n')
body, falso, err = con_curl(['timeout', 'timeout', 'timeout'], jar)
ok(body is None and 'timeout' in str(err), 'falla por timeout')
ok(jar.exists(), 'el frasco se conserva: el problema era la red, no la identidad')

print('\nE · en paralelo se leen las cookies pero no se escriben')
jar.write_text('# cookies\n')
falso = CurlFalso(['ok'])
hb.COOKIES = jar
real_run = subprocess.run
subprocess.run = falso
try:
    hb.curl('https://x/y', guarda_cookies=False)
finally:
    subprocess.run = real_run
cmd = falso.cmds[0]
ok('-b' in cmd, 'sigue leyéndolas')
ok('-c' not in cmd, 'pero no las escribe: varios curl a la vez se pisarían el frasco')

print('\nF · una url caída no mata la cosecha si hay copia en disco')
tmp = Path(tempfile.mkdtemp())
copia = tmp / 'compendios.html'
copia.write_text('<html>lo de ayer</html>')
hb.curl = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('WAF: bloqueado por PerfDrive'))
fallos = []
res = hb.baja_a_disco('https://x', copia, 'compendios históricos', fallos)
ok(res is False and len(fallos) == 1, 'anota el fallo')
ok(copia.read_text() == '<html>lo de ayer</html>', 'y NO pisa la copia buena')
try:
    hb.baja_a_disco('https://x', tmp / 'nunca-bajado.html', 'inventado', [])
    ok(False, 'sin copia previa debería propagar')
except RuntimeError:
    ok(True, 'sin copia previa sí se propaga: no hay nada que conservar')

print('\nG · el veredicto: fresco → 0 · conservado → 75 · rancio → 1')
ok(hb.veredicto_cambiario([]) == 0, 'todo refrescado → 0')
ok(hb.veredicto_cambiario([{'que': 'x', 'por': 'WAF', 'dias': 0.4}]) == hb.RC_PARCIAL,
   f'conservado de hace horas → {hb.RC_PARCIAL} (parcial, sin correo)')
ok(hb.veredicto_cambiario([{'que': 'x', 'por': 'WAF', 'dias': hb.DIAS_TOLERADOS + 0.1}]) == 1,
   f'conservado hace más de {hb.DIAS_TOLERADOS} días → 1: el WAF ya es un muro, no un tropiezo')
ok(hb.veredicto_cambiario([{'que': 'a', 'por': 'WAF', 'dias': 1},
                           {'que': 'b', 'por': 'WAF', 'dias': 30}]) == 1,
   'basta con que UNA esté rancia')

print()
if FALLAS:
    print(f'✗ {len(FALLAS)} fallas')
    sys.exit(1)
print('✓ todo bien')
