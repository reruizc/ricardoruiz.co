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
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()

    base = {'nombre': a.nombre, 'desc': a.desc, 'critica': a.critica}

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

    # Si hay deadline, el timeout de la etapa nunca puede pasarse de él.
    tope = a.timeout
    if a.deadline:
        tope = max(60, min(tope, int(a.deadline - time.time())))

    t0 = time.time()
    print(f'--- {a.nombre}: {a.desc or " ".join(cmd)} ---', flush=True)
    rx = re.compile(a.filtro) if a.filtro else None
    cola, rc, motivo = collections.deque(maxlen=8), None, ''
    colgada = []
    try:
        # Popen y no run(): la salida se imprime EN VIVO. Si el Mac se duerme o
        # se reinicia a mitad de corrida, en el log queda lo que alcanzó a hacer;
        # con capture_output esa etapa no habría dejado ni una línea.
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, errors='replace', bufsize=1)

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
    if rc != 0 and not motivo:
        motivo = f'terminó con código {rc}'
        if cola:
            motivo += f' · última línea: {cola[-1][:200]}'
    registrar(a.reg, dict(base, estado='ok' if rc == 0 else 'error', rc=rc,
                          motivo=motivo or None, inicio=iso(t0), fin=iso(),
                          duracion_s=dur, timeout_s=tope,
                          salida_cola=cola if rc != 0 else None))
    print(f'--- {a.nombre}: rc={rc} · {dur:.0f}s ---', flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
