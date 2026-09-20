#!/usr/bin/env python3
"""¿Hay red? Si no, espera un rato antes de rendirse.

launchd dispara la corrida a las 8:00 mientras el Mac todavía está despertando, y
el wifi tarda en volver. Medido sobre 114 corridas del cron.log: **8 (7 %)
arrancaron sin red, y 6 de esas 8 son de la mañana**. La peor —11-sep— dejó 38
«Could not connect to the endpoint URL» y tumbó la corrida entera.

El problema es que eso se reportaba fuente por fuente, como si el Estado
colombiano se hubiera caído a la vez: `sucop_fetch` con `curl rc=6`,
`secop_upload` sin poder hablar con S3, los manifiestos sin subir. Tres correos
distintos para una sola causa, que además se arregla sola en un par de minutos.

Se consulta más de un destino a propósito: si S3 no responde pero el host neutro
sí, hay red y el problema es de S3 — eso no es asunto de este chequeo, y las
etapas que usen S3 lo reportarán por su cuenta. Acá solo se pregunta si esta
máquina puede hablar con el mundo.

    python3 tools/caudal/salud/espera_red.py            # sale 0 si hay red, 1 si no
    python3 tools/caudal/salud/espera_red.py --esperas 5,10   # para probar
"""
import argparse
import subprocess
import sys
import time

DESTINOS = [
    ('S3', 'https://s3.us-east-1.amazonaws.com'),
    ('host neutro', 'https://www.google.com/generate_204'),
]
# Arranca corto porque lo normal es que ya haya red y no hay que castigar a la
# corrida sana; se estira porque un Mac recién despierto puede tardar. Más de
# 4 min ya no es «despertando», es que no hay internet.
#   esperas          245 s
#   + 8 intentos × 2 destinos × 8 s de curl en el peor caso   128 s
#   = 373 s, que es lo que tiene que caber en el --timeout de la etapa (480).
# Si se tocan estas esperas, revisar ese timeout en run_diario.sh.
ESPERAS = (5, 10, 20, 30, 60, 60, 60)
TIMEOUT = 8


def alcanzable(url, timeout=TIMEOUT):
    """¿Responde algo? Cualquier HTTP sirve: un 403 de S3 prueba que hay red."""
    try:
        r = subprocess.run(
            ['/usr/bin/curl', '-s', '-o', '/dev/null', '--max-time', str(timeout), url],
            capture_output=True, timeout=timeout + 10)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def hay_red(destinos=DESTINOS):
    for nombre, url in destinos:
        if alcanzable(url):
            return True, nombre
    return False, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--esperas', help='lista en segundos, separada por comas (para pruebas)')
    a = ap.parse_args()
    esperas = ([int(x) for x in a.esperas.split(',') if x.strip().isdigit()]
               if a.esperas else list(ESPERAS))

    t0 = time.time()
    for i, espera in enumerate([0] + esperas):
        if espera:
            print(f'  · sin red todavía, espero {espera} s '
                  f'(intento {i + 1}/{len(esperas) + 1})', flush=True)
            time.sleep(espera)
        listo, por_donde = hay_red()
        if listo:
            tardó = time.time() - t0
            if i == 0:
                print(f'  · hay red ({por_donde})')
            else:
                print(f'  · la red volvió tras {tardó:.0f} s ({por_donde}). '
                      f'El Mac estaba despertando.')
            return 0

    print(f'  ✗ sigo sin red después de {time.time() - t0:.0f} s. No arranco la corrida: '
          f'sin red las 60 etapas fallan una por una y llenan el estado de ruido '
          f'que no dice lo único cierto, que es que esta máquina está incomunicada.',
          file=sys.stderr)
    print('  ✗ nadie va a recibir un correo por esto AHORA (sin red tampoco se puede '
          'publicar el latido); si la corrida siguiente también falla, el latido pasa '
          'de 26 h y el vigilante avisa. Eso es lo que hay que mirar.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
