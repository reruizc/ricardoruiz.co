#!/usr/bin/env python3
"""Chequeo de salud de Caudal: ¿está fresco el dato y responde la Lambda?

Responde las dos preguntas que hay que poder contestarle a un cliente que paga:

  1. ¿Cada archivo de S3 tiene la edad que le corresponde?  (catalogo.py fija
     el umbral por archivo: los del cron a 26 h, los del histórico sin umbral.)
  2. ¿La Lambda responde 200 y con la FORMA esperada?  Un 200 con `{}` adentro
     es una caída silenciosa: la página se ve viva y no muestra nada.

Escribe `Bases de datos/leyes-senado/diario/estado.json` — el archivo que otra
conversación va a leer para alertar. El shape está documentado en
`.claude/notas/caudal-salud.md` y en el README de esta carpeta.

Uso:
    python3 tools/caudal/salud/check.py                 # todo + escribe estado.json
    python3 tools/caudal/salud/check.py --rapido        # sin los pings a terceros
    python3 tools/caudal/salud/check.py --solo s3       # solo frescura
    python3 tools/caudal/salud/check.py --solo lambda   # solo pings
    python3 tools/caudal/salud/check.py --etapas <jsonl>  # + resultado de la corrida
    python3 tools/caudal/salud/check.py --json          # el estado.json por stdout

Códigos de salida (para que el alertador no tenga que parsear nada):
    0 = ok · 1 = aviso (warn) · 2 = error · 3 = el chequeo mismo se rompió

Sin dependencias: stdlib + el `aws` CLI por subprocess (no hay boto3 en este Mac).
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogo  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT_DEFAULT = os.path.join(REPO, 'Bases de datos', 'leyes-senado', 'diario', 'estado.json')

OK, WARN, ERR = 'ok', 'warn', 'error'
_RANK = {OK: 0, WARN: 1, ERR: 2}


def peor(*estados):
    vals = [e for e in estados if e]
    return max(vals, key=lambda e: _RANK.get(e, 0)) if vals else OK


def ahora():
    return dt.datetime.now().astimezone()


def iso(d):
    return d.isoformat(timespec='seconds')


# ───────────────────────────── S3 ─────────────────────────────

def _aws(args, timeout=90):
    """Corre el aws CLI y devuelve (rc, stdout, stderr)."""
    try:
        p = subprocess.run(['aws'] + args, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except FileNotFoundError:
        return 127, '', 'no encontré el binario `aws` en el PATH'
    except subprocess.TimeoutExpired:
        return 124, '', f'aws {args[0]} {args[1] if len(args) > 1 else ""} pasó de {timeout}s'


def listar(bucket, prefijo):
    """{key: (bytes, LastModified aware)} de un prefijo. Pagina solo."""
    out, token = {}, None
    while True:
        args = ['s3api', 'list-objects-v2', '--bucket', bucket, '--prefix', prefijo,
                '--output', 'json']
        if token:
            args += ['--starting-token', token]
        rc, so, se = _aws(args)
        if rc != 0:
            raise RuntimeError(f's3 list {bucket}/{prefijo}: {se.strip()[:200]}')
        d = json.loads(so or '{}')
        for o in d.get('Contents', []):
            lm = o['LastModified']
            if isinstance(lm, str):
                lm = dt.datetime.fromisoformat(lm.replace('Z', '+00:00'))
            out[o['Key']] = (o['Size'], lm)
        token = d.get('NextToken')
        if not token:
            return out


def fecha_interna(bucket, key, campo):
    """Baja el objeto (chico) y le lee el campo de fecha. None si no se puede.

    Sirve para cazar la subida fresca de contenido viejo: LastModified se
    actualiza en cada `aws s3 cp` aunque el archivo traiga el dato de anteayer.
    """
    rc, so, _ = _aws(['s3', 'cp', f's3://{bucket}/{key}', '-'], timeout=60)
    if rc != 0:
        return None
    try:
        v = json.loads(so).get(campo)
    except Exception:
        return None
    if not isinstance(v, str) or not v:
        return None
    try:
        if len(v) == 10:            # 'YYYY-MM-DD' → medianoche local
            d = dt.datetime.fromisoformat(v)
            return d.replace(tzinfo=ahora().tzinfo)
        d = dt.datetime.fromisoformat(v.replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=ahora().tzinfo)
    except Exception:
        return None


def chequear_frescura(leg=None, con_fecha_interna=True):
    items = catalogo.archivos(leg)
    listados, errores = {}, []
    for bucket, prefijo in {(i['bucket'], i['key'].rsplit('/', 1)[0] + '/') for i in items}:
        try:
            listados.setdefault(bucket, {}).update(listar(bucket, prefijo))
        except Exception as e:
            errores.append(f'no pude listar s3://{bucket}/{prefijo}: {e}')

    t0 = ahora()
    filas, estado = [], OK
    for it in items:
        warn_h, err_h = catalogo.UMBRALES[it['clase']]
        f = {'key': it['key'], 'bucket': it['bucket'], 'clase': it['clase'],
             'productor': it['productor'], 'consumidor': it['consumidor'],
             'umbral_aviso_h': warn_h, 'umbral_error_h': err_h}
        if it.get('nota'):
            f['nota'] = it['nota']

        hit = listados.get(it['bucket'], {}).get(it['key'])
        if not hit:
            # Si ni siquiera pudimos listar el bucket, no es "falta el archivo":
            # es que el chequeo no pudo mirar. Decirlo distinto importa.
            ciego = any(it['bucket'] in e for e in errores)
            f.update(estado=ERR, motivo='no pude consultar S3' if ciego else 'FALTA en S3',
                     existe=False)
            filas.append(f)
            estado = ERR
            continue

        size, lm = hit
        edad_h = round((t0 - lm).total_seconds() / 3600, 1)
        f.update(existe=True, bytes=size, min_bytes=it['min_bytes'],
                 modificado=iso(lm.astimezone()), edad_horas=edad_h)

        motivos, e = [], OK
        if size < it['min_bytes']:
            motivos.append(f'truncado: {size} bytes < mínimo {it["min_bytes"]}')
            e = ERR
        if err_h is not None and edad_h > err_h:
            motivos.append(f'vencido: {edad_h} h > {err_h} h')
            e = peor(e, ERR)
        elif warn_h is not None and edad_h > warn_h:
            motivos.append(f'viejo: {edad_h} h > {warn_h} h')
            e = peor(e, WARN)

        campo = it.get('campo_fecha')
        if (con_fecha_interna and campo and size <= catalogo.MAX_BYTES_FECHA_INTERNA):
            fi = fecha_interna(it['bucket'], it['key'], campo)
            if fi:
                ei = round((t0 - fi).total_seconds() / 3600, 1)
                f['fecha_interna'] = iso(fi.astimezone())
                f['edad_interna_horas'] = ei
                if err_h is not None and ei > err_h:
                    motivos.append(f'contenido vencido: el campo `{campo}` es de hace {ei} h')
                    e = peor(e, ERR)
                elif warn_h is not None and ei > warn_h:
                    motivos.append(f'contenido viejo: el campo `{campo}` es de hace {ei} h')
                    e = peor(e, WARN)

        f['estado'] = e
        if motivos:
            f['motivo'] = ' · '.join(motivos)
        filas.append(f)
        estado = peor(estado, e)

    if errores:
        estado = peor(estado, ERR)

    cuenta = {k: sum(1 for f in filas if f['estado'] == k) for k in (OK, WARN, ERR)}
    return {'estado': estado, 'n': len(filas), 'n_ok': cuenta[OK], 'n_aviso': cuenta[WARN],
            'n_error': cuenta[ERR], 'errores_de_consulta': errores, 'archivos': filas}


# ─────────────────────────── Lambda ───────────────────────────

def _post(url, body, timeout):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'caudal-salud/1'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace'), int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')[:400], int((time.time() - t0) * 1000)
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}', int((time.time() - t0) * 1000)


def _ping(p, url):
    r = {'accion': p['accion'], 'desc': p['desc'], 'externa': p.get('externa', False)}
    code, txt, ms = _post(url, p['body'], p.get('timeout', 60))
    r.update(http=code, ms=ms)
    fallo_estado = WARN if p.get('externa') else ERR
    if code != 200:
        r.update(estado=fallo_estado, motivo=f'HTTP {code or "sin respuesta"}: {txt[:180]}')
        return r
    try:
        d = json.loads(txt)
    except Exception:
        r.update(estado=fallo_estado, motivo='la respuesta no es JSON')
        return r
    queja = p['forma'](d)
    # Un 200 con {'error': ...} adentro es el modo de falla más traicionero:
    # el frontend lo pinta como "sin resultados" y nadie se entera.
    if not queja and isinstance(d, dict) and d.get('error'):
        queja = f'200 pero con error adentro: {str(d["error"])[:140]}'
    r.update(estado=fallo_estado if queja else OK)
    if queja:
        r['motivo'] = queja
    else:
        r['muestra'] = _muestra(d)
    r['_data'] = d
    return r


def _muestra(d):
    """Un número que se pueda leer de un vistazo en el log."""
    if not isinstance(d, dict):
        return ''
    for k in ('n', 'total', 'n_proyectos'):
        if isinstance(d.get(k), int):
            return f'{k}={d[k]:,}'.replace(',', '.')
    n = _n(d, 'resumen', 'n_intentos')
    if isinstance(n, int):
        return f'n_intentos={n}'
    for k in ('titulo', 'nombre'):
        if isinstance(d.get(k), str) and d[k]:
            return d[k][:52]
    pos = _n(d, 'p_tratado_por_posicion')
    if isinstance(pos, dict):
        return f'{len(pos)} tramos de posición'
    if isinstance(d.get('resultados'), list):
        return f'resultados={len(d["resultados"])}'
    return ''


def _n(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _corto(key, ancho=46):
    return key if len(key) <= ancho else '…' + key[-(ancho - 1):]


def chequear_lambda(leg=None, rapido=False):
    url = catalogo.LAMBDA_URL
    ps = [p for p in catalogo.pings(leg) if not (rapido and p.get('externa'))]
    t0 = time.time()
    # En paralelo, pero suave: son 11 pings y la Lambda arranca en frío una vez.
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda p: _ping(p, url), ps))

    # La ficha necesita un id real; sale del ping de `buscar`.
    bus = next((r for r in res if r['accion'] == 'buscar'), None)
    hits = ((bus or {}).get('_data') or {}).get('resultados') or []
    if hits and hits[0].get('id') is not None:
        p = dict(catalogo.PING_PROYECTO,
                 body={'action': 'proyecto', 'id': hits[0]['id'], 'tb': hits[0].get('tb', 'pdly')})
        res.append(_ping(p, url))
    else:
        res.append(dict(catalogo.PING_PROYECTO, http=0, ms=0, estado=WARN,
                        motivo='no se pinchó: `buscar` no dio un id para probar',
                        externa=False, desc=catalogo.PING_PROYECTO['desc']))

    for r in res:
        r.pop('_data', None)
        r.pop('forma', None)
        r.pop('body', None)
    estado = peor(*[r['estado'] for r in res]) if res else ERR
    cuenta = {k: sum(1 for r in res if r['estado'] == k) for k in (OK, WARN, ERR)}
    return {'estado': estado, 'endpoint': url, 'n': len(res), 'n_ok': cuenta[OK],
            'n_aviso': cuenta[WARN], 'n_error': cuenta[ERR],
            'ms_total': int((time.time() - t0) * 1000), 'pings': res}


# ─────────────────── la corrida (etapas del cron) ───────────────────

def leer_etapas(path):
    """El JSONL que va dejando `etapa.py` durante la corrida."""
    if not path or not os.path.exists(path):
        return None
    etapas = []
    with open(path, encoding='utf-8') as fh:
        for ln in fh.read().split('\n'):
            ln = ln.strip()
            if not ln:
                continue
            try:
                etapas.append(json.loads(ln))
            except Exception:
                pass
    if not etapas:
        return None

    fallaron = [e['nombre'] for e in etapas if e.get('estado') == ERR]
    avisos = [e['nombre'] for e in etapas if e.get('estado') == WARN]
    omitidas = [e['nombre'] for e in etapas if e.get('estado') == 'omitida']
    ini = min((e['inicio'] for e in etapas if e.get('inicio')), default=None)
    fin = max((e['fin'] for e in etapas if e.get('fin')), default=None)
    dur = None
    if ini and fin:
        try:
            dur = int((dt.datetime.fromisoformat(fin) - dt.datetime.fromisoformat(ini)).total_seconds())
        except Exception:
            dur = None
    return {
        'estado': ERR if fallaron else (WARN if (avisos or omitidas) else OK),
        'inicio': ini, 'fin': fin, 'duracion_s': dur,
        'n': len(etapas), 'n_ok': sum(1 for e in etapas if e.get('estado') == OK),
        'n_fallo': len(fallaron), 'n_omitida': len(omitidas),
        'fallaron': fallaron, 'avisaron': avisos, 'omitidas': omitidas,
        'etapas': etapas,
    }


# ───────────────────────────── salida ─────────────────────────────

def _lista(xs, tope=4):
    """Nombra los primeros y cuenta el resto: un resumen de 24 nombres no se lee."""
    xs = list(xs)
    return ', '.join(xs) if len(xs) <= tope else ', '.join(xs[:tope]) + f' y {len(xs) - tope} más'


def resumir(est):
    p = []
    c = est.get('corrida')
    if c:
        if c['fallaron']:
            p.append('falló ' + _lista(c['fallaron']))
        if c['omitidas']:
            p.append('omitidas ' + _lista(c['omitidas']))
        if not c['fallaron'] and not c['omitidas']:
            p.append(f'corrida completa ({c["n"]} etapas)')
    f = est.get('frescura')
    if f:
        if f.get('errores_de_consulta'):
            # Si no pudimos ni listar el bucket, los 24 archivos "fallan" por la
            # misma razón. Decirlo una vez; enumerarlos sería ruido.
            p.append(f'no pude consultar S3 ({f["errores_de_consulta"][0][:80]})')
        else:
            malos = [a['key'].rsplit('/', 1)[-1] for a in f['archivos'] if a['estado'] != OK]
            p.append('dato viejo o roto: ' + _lista(malos) if malos
                     else f'{f["n"]} archivos frescos')
    l = est.get('lambda')
    if l:
        malos = [x['accion'] for x in l['pings'] if x['estado'] != OK]
        p.append('Lambda: falla ' + ', '.join(malos) if malos else f'Lambda ok ({l["n"]} acciones)')
    return ' · '.join(p) or 'sin chequeos'


def listar_problemas(est):
    """Lista plana y legible — es lo que el alertador manda por mensaje."""
    out = []
    c = est.get('corrida') or {}
    for e in c.get('etapas', []):
        if e.get('estado') in (ERR, WARN, 'omitida'):
            det = e.get('motivo') or f'rc={e.get("rc")}'
            out.append(f'[corrida/{e.get("estado")}] {e["nombre"]}: {det}')
    fr = est.get('frescura') or {}
    ciego = bool(fr.get('errores_de_consulta'))
    for e in fr.get('errores_de_consulta', []):
        out.append(f'[frescura/error] {e}')
    for a in fr.get('archivos', []):
        # Con el bucket ilegible, cada archivo repetiría la misma queja.
        if a['estado'] != OK and not (ciego and a.get('motivo') == 'no pude consultar S3'):
            out.append(f'[frescura/{a["estado"]}] {a["key"]}: {a.get("motivo", "?")}')
    for p in (est.get('lambda') or {}).get('pings', []):
        if p['estado'] != OK:
            out.append(f'[lambda/{p["estado"]}] {p["accion"]}: {p.get("motivo", "?")}')
    return out


ICONO = {OK: '✓', WARN: '!', ERR: '✗', 'omitida': '·'}


def imprimir(est):
    print(f'\n══════ salud de Caudal · {est["generado"]} ══════')
    print(f'  estado: {est["estado"].upper()} — {est["resumen"]}')

    c = est.get('corrida')
    if c:
        d = f' · {c["duracion_s"] // 60} min' if c.get('duracion_s') else ''
        print(f'\n  CORRIDA [{c["estado"]}] {c["n_ok"]}/{c["n"]} etapas ok{d}')
        for e in c['etapas']:
            s = e.get('estado', '?')
            secs = f'{e.get("duracion_s", 0):>5.0f}s' if e.get('duracion_s') is not None else '    —'
            print(f'    {ICONO.get(s, "?")} {e["nombre"]:<26} {secs}  {(e.get("motivo") or "")[:130]}')

    f = est.get('frescura')
    if f:
        print(f'\n  FRESCURA [{f["estado"]}] {f["n_ok"]}/{f["n"]} ok'
              f' · {f["n_aviso"]} aviso · {f["n_error"]} error')
        for a in f['archivos']:
            if a['estado'] == OK and a['clase'] == 'estatico':
                continue          # el histórico solo se nombra cuando molesta
            edad = f'{a.get("edad_horas", 0):>7.1f}h' if a.get('existe') else '      —'
            print(f'    {ICONO.get(a["estado"], "?")} {_corto(a["key"]):<46} {edad}  {a.get("motivo") or ""}')
        ok_est = sum(1 for a in f['archivos'] if a['estado'] == OK and a['clase'] == 'estatico')
        if ok_est:
            print(f'    ✓ ({ok_est} archivos del histórico presentes y con tamaño sano)')
        for e in f['errores_de_consulta']:
            print(f'    ✗ {e}')

    l = est.get('lambda')
    if l:
        print(f'\n  LAMBDA [{l["estado"]}] {l["n_ok"]}/{l["n"]} acciones ok · {l["ms_total"]} ms')
        for p in l['pings']:
            ext = ' (externa)' if p.get('externa') else ''
            det = p.get('motivo') or p.get('muestra') or ''
            print(f'    {ICONO.get(p["estado"], "?")} {p["accion"]:<14} {p.get("http", 0):>3}'
                  f' {p.get("ms", 0):>6} ms  {det}{ext}')
    print()


def main():
    ap = argparse.ArgumentParser(description='Chequeo de salud del pipeline de Caudal')
    ap.add_argument('--etapas', help='JSONL de etapas que dejó la corrida (etapa.py --reg)')
    ap.add_argument('--out', default=OUT_DEFAULT, help='dónde escribir estado.json')
    ap.add_argument('--solo', choices=['s3', 'lambda'], help='correr solo una mitad')
    ap.add_argument('--rapido', action='store_true',
                    help='sin pings a terceros (SECOP/Google News) ni fechas internas')
    ap.add_argument('--legislatura', help="ej '2026-2027' (por defecto se calcula)")
    ap.add_argument('--json', action='store_true', help='volcar estado.json por stdout')
    ap.add_argument('--sin-escribir', action='store_true')
    a = ap.parse_args()

    leg = a.legislatura or catalogo.legislatura_actual()
    est = {'v': 1, 'generado': iso(ahora()), 'generado_utc': iso(dt.datetime.now(dt.timezone.utc)),
           'host': platform.node(), 'legislatura': leg}

    corrida = leer_etapas(a.etapas)
    if corrida is None and os.path.exists(a.out):
        # Corrida standalone: se conserva la última corrida conocida para no
        # borrar historia, marcada para que nadie la confunda con una de ahora.
        try:
            with open(a.out, encoding='utf-8') as fh:
                prev = json.load(fh).get('corrida')
            if prev:
                corrida = dict(prev, arrastrada=True)
        except Exception:
            pass
    if corrida:
        est['corrida'] = corrida

    if a.solo != 'lambda':
        try:
            est['frescura'] = chequear_frescura(leg, con_fecha_interna=not a.rapido)
        except Exception as e:
            est['frescura'] = {'estado': ERR, 'n': 0, 'n_ok': 0, 'n_aviso': 0, 'n_error': 0,
                               'errores_de_consulta': [f'el chequeo de S3 se rompió: {e}'],
                               'archivos': []}
    if a.solo != 's3':
        try:
            est['lambda'] = chequear_lambda(leg, rapido=a.rapido)
        except Exception as e:
            est['lambda'] = {'estado': ERR, 'endpoint': catalogo.LAMBDA_URL, 'n': 0, 'n_ok': 0,
                             'n_aviso': 0, 'n_error': 0, 'ms_total': 0, 'pings': [],
                             'error': f'el chequeo de la Lambda se rompió: {e}'}

    est['estado'] = peor(*[est[k]['estado'] for k in ('corrida', 'frescura', 'lambda') if k in est])
    est['resumen'] = resumir(est)
    est['problemas'] = listar_problemas(est)

    if not a.sin_escribir:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        tmp = a.out + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(est, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, a.out)      # atómico: nadie lee un estado.json a medio escribir

    if a.json:
        print(json.dumps(est, ensure_ascii=False, indent=1))
    else:
        imprimir(est)
        if not a.sin_escribir:
            print(f'  → {a.out}\n')

    return {OK: 0, WARN: 1, ERR: 2}[est['estado']]


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(3)
    except Exception as e:                       # el chequeo nunca tumba la corrida
        print(f'✗ el chequeo de salud se rompió: {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(3)
