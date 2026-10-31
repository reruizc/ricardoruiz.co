#!/usr/bin/env python3
"""¿Responde camara.gov.co? Si no, la corrida no gasta su tiempo esperándola.

El 30 y 31-oct-2026 el servidor dejó de aceptar conexiones (desde el Mac y desde la
EC2, con el DNS bien). Las etapas de Cámara se quedaron esperando timeout tras
timeout hasta agotar el tope de 4 h de la corrida, y por eso se omitieron 40 etapas
que no tienen nada que ver con Cámara, entre ellas todas las de entidades.

    python3 tools/leyes-senado/camara_viva.py      # sale 0 si responde, 1 si no
"""
import subprocess
import sys
import time

URL = 'https://www.camara.gov.co/'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'
ESPERAS = (20, 20, 0)        # 3 intentos: un corte de un minuto no debe saltarse a Cámara
TIMEOUT = 15


def responde():
    r = subprocess.run(['/usr/bin/curl', '-sL', '-A', UA, '--max-time', str(TIMEOUT), '-o', '/dev/null',
                        '-w', '%{http_code}', URL], capture_output=True, text=True)
    return r.stdout.strip()


def main():
    for i, espera in enumerate(ESPERAS, 1):
        code = responde()
        if code.startswith(('2', '3', '4')):      # un 403 también es un servidor vivo
            print(f'  camara.gov.co responde ({code})')
            return 0
        print(f'  intento {i}: sin respuesta (http {code or "000"})')
        time.sleep(espera)
    print(f'  ✗ camara.gov.co no responde: se omiten las etapas de Cámara')
    return 1


if __name__ == '__main__':
    sys.exit(main())
