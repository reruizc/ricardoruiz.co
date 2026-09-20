#!/usr/bin/env python3
"""Pruebas de espera_red.py SIN tocar la red (curl y sleep sustituidos).

Simula el caso real: launchd dispara a las 8:00, el Mac está despertando y el
wifi vuelve a los 20 s. Pasó en 8 de 114 corridas (7 %), 6 de ellas de mañana.

    python3 tools/caudal/salud/prueba_espera_red.py     # sale con 1 si algo falla
"""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'er', str(Path(__file__).resolve().parent / 'espera_red.py'))
er = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(er)

FALLAS = []


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


def correr(vuelve_en=None, argv=()):
    """vuelve_en = segundos simulados tras los cuales hay red (None = nunca)."""
    reloj = {'t': 0.0}
    sondeos = []

    def curl_falso(cmd, **kw):
        url = cmd[-1]
        sondeos.append((round(reloj['t']), url))
        hay = vuelve_en is not None and reloj['t'] >= vuelve_en

        class R:
            returncode = 0 if hay else 6      # 6 = no pude resolver el host
        return R()

    real_run, real_sleep, real_time, real_argv = (
        subprocess.run, time.sleep, time.time, sys.argv)
    subprocess.run = curl_falso
    time.sleep = lambda s: reloj.__setitem__('t', reloj['t'] + s)
    time.time = lambda: reloj['t']
    sys.argv = ['espera_red.py', *argv]
    try:
        return er.main(), sondeos, reloj['t']
    finally:
        subprocess.run, time.sleep, time.time, sys.argv = (
            real_run, real_sleep, real_time, real_argv)


print('A · con red desde el principio no se castiga a la corrida sana')
rc, sondeos, t = correr(vuelve_en=0)
ok(rc == 0, 'sale con 0')
ok(t == 0, f'no espera ni un segundo ({t})')
ok(len(sondeos) == 1, f'y le basta UN sondeo, no prueba los dos destinos ({len(sondeos)})')

print('\nB · el Mac despertando: la red vuelve a los 20 s y la corrida sigue')
rc, sondeos, t = correr(vuelve_en=20)
ok(rc == 0, 'sale con 0: la corrida arranca igual')
ok(t >= 20, f'esperó hasta que volvió ({t:.0f} s simulados)')
ok(t <= 60, f'y no de más: {t:.0f} s, no los 245 del peor caso')

print('\nC · sin red nunca: se rinde, pero solo tras agotar las esperas')
rc, sondeos, t = correr(vuelve_en=None)
ok(rc == 1, 'sale con 1 → run_diario aborta antes de correr 60 etapas condenadas')
ok(t == sum(er.ESPERAS), f'agotó las esperas completas ({t:.0f} = {sum(er.ESPERAS)})')
ok(len(sondeos) == (len(er.ESPERAS) + 1) * len(er.DESTINOS),
   f'probó los {len(er.DESTINOS)} destinos en cada uno de los {len(er.ESPERAS) + 1} intentos')

print('\nD · se consulta más de un destino: S3 caído no es "no hay red"')
def solo_s3_caido(cmd, **kw):
    class R:
        returncode = 7 if 's3' in cmd[-1] else 0
    return R()
real = subprocess.run
subprocess.run = solo_s3_caido
try:
    listo, por_donde = er.hay_red()
finally:
    subprocess.run = real
ok(listo and por_donde == 'host neutro',
   'con S3 abajo pero el host neutro arriba → hay red (lo de S3 es asunto de sus etapas)')

print('\nE · el peor caso cabe en el --timeout de la etapa (480 s en run_diario.sh)')
peor = sum(er.ESPERAS) + (len(er.ESPERAS) + 1) * len(er.DESTINOS) * er.TIMEOUT
ok(peor < 480, f'peor caso {peor} s < 480')
run = (Path(__file__).resolve().parents[2] / 'leyes-senado' / 'run_diario.sh').read_text()
ok('--nombre red_lista --critica --timeout 480' in run,
   'y run_diario.sh sigue declarando ese 480 (si cambian las esperas, hay que moverlo)')

print()
if FALLAS:
    print(f'✗ {len(FALLAS)} fallas')
    sys.exit(1)
print('✓ todo bien')
