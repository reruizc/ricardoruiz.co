#!/usr/bin/env python3
"""Corre UNA etapa del pipeline y deja constancia de cómo le fue.

`run_diario.sh` llama a esto en vez de invocar los scripts directo. A cambio de
una línea más larga, cada etapa gana cuatro cosas que en bash pelado no había:

  · timeout de verdad — este Mac no tiene `timeout`/`gtimeout`, así que un
    harvester colgado bloqueaba la corrida entera y, peor, la siguiente.
  · duración y hora de inicio/fin.
  · filtro de salida — antes iba con `| grep`, que se comía el rc real (por eso
    el script tenía que andar rescatándolo con ${PIPESTATUS[0]}).
  · un registro JSONL que `check.py` convierte en el bloque `corrida` de
    estado.json.

Uso:
    python3 tools/caudal/salud/etapa.py --reg /tmp/etapas.jsonl \\
        --nombre senado --desc "radicados del Senado" --timeout 2400 \\
        -- python3 tools/leyes-senado/harvest_diario.py

    # registrar una etapa que NO se corrió, sin ejecutar nada
    python3 tools/caudal/salud/etapa.py --reg ... --nombre secop_up \\
        --omitida "el build falló, no hay qué subir"

Sale con el mismo código que el comando hijo (124 si se pasó del timeout), para
que el shell pueda decidir si sigue.
"""

import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
import threading
import time

TIMEOUT_DEFAULT = 45 * 60


def iso(ts=None):
    return dt.datetime.fromtimestamp(ts or time.time()).astimezone().isoformat(timespec='seconds')


def registrar(path, rec):
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f'  ! no pude registrar la etapa {rec.get("nombre")}: {e}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--reg', help='JSONL donde acumular el resultado de cada etapa')
    ap.add_argument('--nombre', required=True)
    ap.add_argument('--desc', default='')
    ap.add_argument('--timeout', type=int, default=TIMEOUT_DEFAULT)
    ap.add_argument('--filtro', help='regex: solo se imprimen las líneas que casen')
    ap.add_argument('--critica', action='store_true',
                    help='marca la etapa como crítica (el alertador la trata distinto)')
    ap.add_argument('--omitida', help='no ejecuta nada; registra por qué se saltó')
    ap.add_argument('--deadline', type=int, default=0,
                    help='epoch: pasada esa hora la etapa se omite sola (tope global de la corrida)')
    ap.add_argument('--reserva', type=int, default=0,
                    help='segundos que hay que dejarle a las etapas SIGUIENTES: el tope de '
                         'esta etapa se recorta para no comerse el deadline global')
    ap.add_argument('--minimo', type=int, default=0,
                    help='si tras recortar por deadline y reserva le queda menos que esto, '
                         'la etapa se omite en vez de correr un rato inútil')
    ap.add_argument('--rc-aviso', default='',
                    help='códigos de salida que NO son falla sino degradación prevista '
                         '(ej. 75 = el harvester del Senado guardó lo avanzado). Se '
                         'registran como «warn»: check.py los cuenta aparte y el '
                         'vigilante no manda correo por ellos.')
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()

    base = {'nombre': a.nombre, 'desc': a.desc, 'critica': a.critica}
    rc_aviso = {int(x) for x in re.split(r'[,\s]+', a.rc_aviso or '') if x.strip().isdigit()}

    if a.omitida:
        registrar(a.reg, dict(base, estado='omitida', rc=None, motivo=a.omitida,
                              inicio=iso(), fin=iso(), duracion_s=0))
        print(f'  · omitida ({a.nombre}): {a.omitida}')
        return 0

    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == '--' else a.cmd
    if not cmd:
        print('etapa.py: falta el comando después de --', file=sys.stderr)
        return 2

    if a.deadline and time.time() > a.deadline:
        motivo = 'la corrida pasó su tope de tiempo global'
        registrar(a.reg, dict(base, estado='omitida', rc=None, motivo=motivo,
                              inicio=iso(), fin=iso(), duracion_s=0))
        print(f'  · omitida ({a.nombre}): {motivo}')
        return 0

    # Si hay deadline, el timeout de la etapa nunca puede pasarse de él. Y con
    # --reserva tampoco puede comerse lo que necesitan las etapas siguientes:
    # sin eso, una etapa larga y primera en la fila (senado_radicados) podía
    # estirarse hasta el deadline y dejar sin correr a las otras 59.
    tope = a.timeout
    if a.deadline:
        disponible = int(a.deadline - time.time() - a.reserva)
        # Con --minimo, un resto ridículo no se aprovecha: se omite. Correr un
        # harvester 60 s es peor que no correrlo — gasta peticiones contra un WAF
        # que cobra por ráfaga, y deja una cosecha tan incompleta que el propio
        # script la reporta como grave. Una alarma falsa por ir tarde.
        if a.minimo and disponible < a.minimo:
            motivo = (f'quedan {max(0, disponible)} s antes del tope global de la corrida '
                      f'(reserva {a.reserva} s) y necesita al menos {a.minimo}')
            registrar(a.reg, dict(base, estado='omitida', rc=None, motivo=motivo,
                                  inicio=iso(), fin=iso(), duracion_s=0))
            print(f'  · omitida ({a.nombre}): {motivo}')
            return 0
        tope = max(60, min(tope, disponible))

    t0 = time.time()
    print(f'--- {a.nombre}: {a.desc or " ".join(cmd)} ---', flush=True)
    rx = re.compile(a.filtro) if a.filtro else None
    cola, rc, motivo = collections.deque(maxlen=8), None, ''
    colgada = []
    try:
        # Popen y no run(): la salida se imprime EN VIVO. Si el Mac se duerme o
        # se reinicia a mitad de corrida, en el log queda lo que alcanzó a hacer;
        # con capture_output esa etapa no habría dejado ni una línea.
        # El hijo recibe su tope real: un harvester con presupuesto interno (el del
        # Senado) puede así ajustarlo al tiempo que de verdad tiene, en vez de
        # llevar una constante escrita a mano que se desactualiza sola.
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, errors='replace', bufsize=1,
                             env=dict(os.environ, CAUDAL_ETAPA_TOPE_S=str(tope)))

        def matar():
            colgada.append(True)
            for f in (p.terminate, p.kill):     # SIGTERM y, si no cede, SIGKILL
                try:
                    f()
                    time.sleep(2)
                    if p.poll() is not None:
                        return
                except Exception:
                    return

        reloj = threading.Timer(tope, matar)    # el timeout no depende de que el hijo hable
        reloj.start()
        try:
            for ln in p.stdout:
                ln = ln.rstrip('\n')
                if ln.strip():
                    cola.append(ln)
                if rx is None or rx.search(ln):
                    print(ln, flush=True)
            rc = p.wait()
        finally:
            reloj.cancel()
        if colgada:
            rc, motivo = 124, f'colgada: pasó de {tope}s y la maté'
            print(f'  ! {a.nombre}: {motivo}', flush=True)
        elif rc != 0 and rx is not None:
            # Si falló y estábamos filtrando, el motivo casi seguro quedó fuera
            # del filtro. Se imprime la cola cruda: un rc suelto no sirve de nada.
            print('  ! salida final de la etapa fallida:')
            for l in cola:
                print(f'    {l[:300]}')
    except FileNotFoundError as e:
        rc, motivo = 127, f'no encontré el ejecutable: {e}'
        print(f'  ! {a.nombre}: {motivo}')
    except Exception as e:
        rc, motivo = 126, f'{type(e).__name__}: {e}'
        print(f'  ! {a.nombre}: {motivo}')
    cola = list(cola)

    dur = round(time.time() - t0, 1)
    # Un rc declarado en --rc-aviso es degradación PREVISTA, no falla: el script
    # hizo su trabajo y dejó dicho que quedó a medias. Colapsarlo a «error» (lo
    # que se hacía hasta el 19-sep-2026) mandaba un correo de alarma cada corrida
    # por algo que el propio harvester ya había resuelto conservando el dato.
    aviso = rc in rc_aviso and not colgada
    if rc != 0 and not motivo:
        motivo = f'terminó con código {rc}'
        if cola:
            motivo += f' · última línea: {cola[-1][:200]}'
    if aviso and motivo:
        motivo = 'parcial · ' + motivo
    registrar(a.reg, dict(base, estado='ok' if rc == 0 else ('warn' if aviso else 'error'),
                          rc=rc, motivo=motivo or None, inicio=iso(t0), fin=iso(),
                          duracion_s=dur, timeout_s=tope,
                          salida_cola=cola if rc != 0 else None))
    print(f'--- {a.nombre}: rc={rc}{" (parcial, no es falla)" if aviso else ""} · '
          f'{dur:.0f}s ---', flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
