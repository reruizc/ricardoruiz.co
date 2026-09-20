#!/usr/bin/env python3
"""Pruebas de etapa.py. No tocan la red ni el pipeline: corren comandos de juguete.

Existe porque etapa.py es quien JUZGA cada etapa de la corrida, y de su veredicto
cuelga el correo del vigilante. Hasta el 19-sep-2026 colapsaba todo rc != 0 a
«error», así que la corrida parcial del harvester del Senado —degradación
prevista, con el dato conservado— mandaba una alarma cada 12 horas.

    python3 tools/caudal/salud/prueba_etapa.py      # sale con 1 si algo falla
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ETAPA = str(Path(__file__).resolve().parent / 'etapa.py')
FALLAS = []


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


def corre(*args, cmd=('python3', '-c', 'pass')):
    """Corre una etapa y devuelve (rc, registro JSONL)."""
    reg = Path(tempfile.mkdtemp(prefix='etapa-prueba-')) / 'etapas.jsonl'
    r = subprocess.run(['python3', ETAPA, '--reg', str(reg), '--nombre', 'prueba',
                        *args, '--', *cmd], capture_output=True, text=True)
    filas = [json.loads(l) for l in reg.read_text(encoding='utf-8').split('\n') if l.strip()]
    return r.returncode, (filas[-1] if filas else {}), r.stdout


print('A · el veredicto según el código de salida')
rc, f, _ = corre()
ok(rc == 0 and f['estado'] == 'ok', 'rc 0 → ok')

rc, f, _ = corre(cmd=('python3', '-c', 'raise SystemExit(75)'))
ok(rc == 75 and f['estado'] == 'error', 'rc 75 SIN declararlo → error (comportamiento de siempre)')

rc, f, _ = corre('--rc-aviso', '75', cmd=('python3', '-c', 'raise SystemExit(75)'))
ok(rc == 75 and f['estado'] == 'warn', 'rc 75 declarado en --rc-aviso → warn, no error')
ok((f.get('motivo') or '').startswith('parcial · '), 'y el motivo lo dice: ' + str(f.get('motivo'))[:40])

rc, f, _ = corre('--rc-aviso', '75', cmd=('python3', '-c', 'raise SystemExit(1)'))
ok(rc == 1 and f['estado'] == 'error', 'un rc NO declarado sigue siendo error aunque haya --rc-aviso')

rc, f, _ = corre('--rc-aviso', '75, 12 ,x', cmd=('python3', '-c', 'raise SystemExit(12)'))
ok(f['estado'] == 'warn', 'la lista admite comas, espacios y basura sin romperse')

print('\nB · una etapa COLGADA nunca es un aviso, aunque su rc esté declarado')
rc, f, _ = corre('--timeout', '1', '--rc-aviso', '124',
                 cmd=('python3', '-c', 'import time; time.sleep(30)'))
ok(f['estado'] == 'error' and f['rc'] == 124,
   'la mata el timeout → error: 124 no lo eligió el script, se lo pusimos nosotros')

print('\nC · --reserva: la etapa no se come lo que necesitan las siguientes')
ahora = int(time.time())
_, f, _ = corre('--timeout', '9000', '--deadline', str(ahora + 3600))
ok(3500 <= f['timeout_s'] <= 3600, f'sin reserva usa todo el deadline ({f["timeout_s"]} s)')
_, f, _ = corre('--timeout', '9000', '--deadline', str(ahora + 3600), '--reserva', '1200')
ok(2300 <= f['timeout_s'] <= 2400, f'con reserva de 1200 s le quedan {f["timeout_s"]}')
_, f, _ = corre('--timeout', '600', '--deadline', str(ahora + 3600), '--reserva', '1200')
ok(f['timeout_s'] == 600, 'si el --timeout propio es menor, manda él')
_, f, _ = corre('--timeout', '9000', '--deadline', str(ahora + 100), '--reserva', '1200')
ok(f['timeout_s'] == 60, 'corrida que va tardísimo: piso de 60 s, no un tope negativo')

print('\nE · --minimo: un resto ridículo se omite, no se malgasta')
rc, f, _ = corre('--timeout', '9000', '--deadline', str(ahora + 100), '--reserva', '1200',
                 '--minimo', '2100', cmd=('python3', '-c', 'print("NO DEBERIA CORRER")'))
ok(f['estado'] == 'omitida' and rc == 0, 'sin tiempo útil → omitida (y la corrida sigue)')
ok('necesita al menos 2100' in (f.get('motivo') or ''), 'y dice por qué: ' + str(f.get('motivo'))[:60])
rc, f, salida = corre('--timeout', '9000', '--deadline', str(ahora + 6000), '--reserva', '1200',
                      '--minimo', '2100', cmd=('python3', '-c', 'print("SI CORRE")'))
ok(f['estado'] == 'ok' and 'SI CORRE' in salida, 'con tiempo de sobra corre normal')

print('\nD · el hijo recibe su tope real por el entorno')
_, f, salida = corre('--timeout', '4242',
                     cmd=('python3', '-c',
                          'import os; print("TOPE=" + os.environ["CAUDAL_ETAPA_TOPE_S"])'))
ok('TOPE=4242' in salida, 'CAUDAL_ETAPA_TOPE_S llega al comando hijo')
_, f, salida = corre('--timeout', '9000', '--deadline', str(int(time.time()) + 3600),
                     '--reserva', '1200',
                     cmd=('python3', '-c',
                          'import os; print("TOPE=" + os.environ["CAUDAL_ETAPA_TOPE_S"])'))
tope = int(salida.rsplit('TOPE=', 1)[1].split()[0])
ok(2300 <= tope <= 2400, f'y llega YA recortado por deadline y reserva ({tope} s)')

print()
if FALLAS:
    print(f'✗ {len(FALLAS)} fallas')
    sys.exit(1)
print('✓ todo bien')
