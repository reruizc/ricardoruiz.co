#!/usr/bin/env python3
"""El latido de Caudal: la versión PÚBLICA y reducida de estado.json.

`run_diario.sh` lo llama al final de cada corrida, después del chequeo de salud.
Sirve a un solo lector: el vigilante que vive FUERA de la máquina que corre el
cron (el cron trigger del worker `rr-auth`). Ese vigilante no tiene credenciales
de AWS, así que no puede leer el bucket privado; lee esto, que va al prefijo
público, y grita si el latido envejece o trae error.

Por qué un archivo aparte y no el estado.json entero en público: estado.json
lleva las llaves del bucket privado, el endpoint de la Lambda, el host y el
detalle de cada acción que se pinchó. Nada de eso le hace falta al vigilante.
Acá van solo conteos y los NOMBRES de las etapas que fallaron — nombres que ya
están en el repo, que es público.

    {"v":1, "ts":"…Z", "estado":"ok|warn|error", "motivo":"…",
     "rc_salud":2, "corrida_inicio":"…Z", "estado_generado":"…Z",
     "estado_de_esta_corrida":true, "etapas_fallidas":[…], "n_etapas":46,
     "n_fallo":1, "n_omitida":0, "frescura":{…}, "lambda":{…}}

`ts` es cuándo la corrida LLEGÓ AL FINAL y publicó. Es la señal de vida: si la
máquina se cae, el cron no corre o la corrida muere antes de este paso, `ts` deja
de moverse y el vigilante lo ve por la edad, aunque no llegue nada.

Salida: 0 = estado.json es de esta corrida (se suben los dos) · 10 = estado.json
es viejo o no existe (el chequeo no lo escribió: se sube solo el latido, que ya
lo dice como error) · cualquier otro = este script se rompió (el shell publica un
latido de emergencia).
"""

import argparse
import datetime as dt
import json
import os
import sys

RC_SALUD = {'0': 'ok', '1': 'warn', '2': 'error', '3': 'error'}


def utc(s):
    if not s:
        return None
    d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)


def z(d):
    return d.strftime('%Y-%m-%dT%H:%M:%SZ') if d else None


def etapas_del_registro(path):
    """Si estado.json no sirve, el registro de etapas igual dice qué falló."""
    out = []
    try:
        for ln in open(path, encoding='utf-8').read().split('\n'):
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estado', required=True)
    ap.add_argument('--etapas', required=True, help='el .etapas.jsonl de la corrida')
    ap.add_argument('--inicio', required=True, help='inicio de la corrida, ISO UTC')
    ap.add_argument('--rc-salud', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    ahora = dt.datetime.now(dt.timezone.utc)
    inicio = utc(a.inicio)

    est = None
    try:
        with open(a.estado, encoding='utf-8') as fh:
            est = json.load(fh)
    except Exception:
        est = None
    generado = utc((est or {}).get('generado_utc') or (est or {}).get('generado')) if est else None
    de_esta = bool(generado and inicio and generado >= inicio)

    lat = {'v': 1, 'ts': z(ahora), 'corrida_inicio': z(inicio),
           'estado_generado': z(generado), 'estado_de_esta_corrida': de_esta,
           'rc_salud': int(a.rc_salud) if str(a.rc_salud).lstrip('-').isdigit() else None}

    if de_esta:
        c = est.get('corrida') or {}
        fr = est.get('frescura') or {}
        la = est.get('lambda') or {}
        lat.update(
            estado=est.get('estado', 'error'),
            etapas_fallidas=list(c.get('fallaron') or []),
            etapas_parciales=list(c.get('avisaron') or []),
            n_etapas=c.get('n'), n_fallo=c.get('n_fallo'), n_omitida=c.get('n_omitida'),
            frescura={k: fr.get(k) for k in ('estado', 'n', 'n_aviso', 'n_error')},
            **{'lambda': {k: la.get(k) for k in ('estado', 'n', 'n_aviso', 'n_error')}},
        )
        partes = []
        if lat['etapas_fallidas']:
            partes.append('falló ' + ', '.join(lat['etapas_fallidas'][:6]))
        # Una etapa parcial NO dispara correo (el vigilante solo mira `estado ==
        # "error"`), pero tiene que quedar dicha: si no, el latido de una corrida
        # a medias se leía igual que el de una corrida redonda.
        if lat['etapas_parciales']:
            partes.append('parcial en ' + ', '.join(lat['etapas_parciales'][:6]))
        if fr.get('n_error'):
            partes.append(f'{fr["n_error"]} archivo(s) de S3 viejos o rotos')
        if fr.get('errores_de_consulta'):
            partes.append('el chequeo no pudo consultar S3')
        if la.get('n_error') or la.get('error'):
            partes.append(f'la Lambda falla en {la.get("n_error") or "?"} acción(es)')
        lat['motivo'] = ' · '.join(partes) or ('todo en orden' if lat['estado'] == 'ok' else 'avisos menores')
    else:
        # El chequeo no dejó estado.json de ESTA corrida (se rompió, rc=3, o lo
        # mató el tope). No se publica el viejo como si fuera de hoy: el latido
        # sale como error y con lo que sí se sabe, que es el registro de etapas.
        et = etapas_del_registro(a.etapas)
        fall = [e.get('nombre', '?') for e in et if e.get('estado') == 'error']
        lat.update(
            estado='error', etapas_fallidas=fall, n_etapas=len(et) or None,
            n_fallo=len(fall), n_omitida=sum(1 for e in et if e.get('estado') == 'omitida'),
            motivo=(f'el chequeo de salud no escribió estado.json (rc={a.rc_salud})'
                    + (' · falló ' + ', '.join(fall[:6]) if fall else '')),
        )

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(lat, fh, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, a.out)
    print(f'latido {lat["estado"]} · {lat["motivo"]} → {a.out}')
    return 0 if de_esta else 10


if __name__ == '__main__':
    sys.exit(main())
