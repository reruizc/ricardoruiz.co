#!/usr/bin/env python3
"""
Ritmo de radicación: cuántos proyectos de ley entran por día al arrancar cada
legislatura, comparando la que corre con las dos anteriores.

Alimenta el monitor que va al lado del título en legislativo.html. Emite un
JSON diminuto (~2 KB) porque el hub no puede pagar los 540 KB que pesa la
respuesta cruda de `radicados`.

POR QUÉ SOLO EL REGISTRO DEL SENADO
  Las tres series salen de leyes.senado.gov.co y nada más. No es un descuido:
  el listado de Cámara **no publica fecha de radicación** (ver la nota de
  `harvest_camara_historico` en CLAUDE.md), así que meterlo dejaría a 2026 con
  un dato que 2018 y 2022 no tienen y la comparación mentiría a favor del año
  nuevo. Medido en el dataset: los radicados de jul-ago de 2018 (161) y 2022
  (189) son 100% del registro del Senado.

VENTANA — RODANTE, no fija, y SOLO DÍAS HÁBILES
  Las ÚLTIMAS dos semanas hasta hoy, mapeadas a las mismas fechas calendario
  de hace 4 y 8 años (el calendario legislativo se repite: instalación el 20
  de julio, mismas legislaturas, mismos recesos). Una ventana fija en el
  arranque se habría quedado mostrando julio para siempre; esta acompaña la
  legislatura todo el año. La serie de la legislatura viva solo existe desde
  el 20-jul-2026 (el rastreo diario empieza ahí), así que días anteriores a
  esa fecha se recortan de las TRES series para no comparar chueco.

  Se descartan sábados y domingos: en el Congreso no se radica los fines de
  semana, así que sus ceros no son actividad baja sino ausencia de calendario
  — dejarlos hundía la línea al piso cada cinco puntos y ensuciaba la lectura.
  Un tramo de 14 días corridos trae SIEMPRE 10 hábiles, así que las tres
  series quedan del mismo largo y alinean por posición (hábil 1..10) aunque
  cada año arranque en un día distinto de la semana (2026 lunes, 2022
  miércoles, 2018 viernes). NO se descuentan festivos: eso exigiría el
  calendario oficial de cada año y la ganancia es marginal.

Fuentes:
  · 2018 y 2022 → Bases de datos/leyes-senado/dist/proyectos.jsonl (histórico Caudal)
  · legislatura viva → acción `radicados` de la Lambda caudal-analiza (el
    rastreo diario, que es lo único que tiene la legislatura en curso)

Uso:
  python3 tools/leyes-senado/build_ritmo.py            # escribe el staging local
  python3 tools/leyes-senado/build_ritmo.py --upload   # + sube a S3
"""
import argparse
import collections
import datetime as dt
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist' / 'proyectos.jsonl'
STAGE = REPO / 'Bases de datos' / 'leyes-senado' / 'en-vivo'
OUT = STAGE / 'ritmo-legislaturas.json'

API = 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com'
S3_BUCKET = 'elecciones-2026'
S3_PREFIX = 'ricardoruiz.co/congreso-2026/output/legislativo'

ANIOS = [2026, 2022, 2018]      # la viva primero
DIAS = 14                        # las últimas dos semanas
INSTALACION = dt.date(2026, 7, 20)


def habiles(dias):
    return [d for d in dias if d.weekday() < 5]        # 5=sáb, 6=dom


def ventana_hoy():
    """Últimos DIAS días corridos hasta hoy (sin bajar del 20-jul-2026), ya
    filtrados a días hábiles."""
    hoy = dt.date.today()
    dias = [hoy - dt.timedelta(days=i) for i in range(DIAS - 1, -1, -1)]
    return habiles([d for d in dias if d >= INSTALACION])


def equivalente(fecha, anio):
    """La misma fecha calendario en la legislatura de `anio` (−4/−8 años).
    El 29-feb sin equivalente cae al 28."""
    try:
        return fecha.replace(year=fecha.year - (2026 - anio))
    except ValueError:
        return fecha.replace(year=fecha.year - (2026 - anio), day=28)


def serie_historica(anio, dias):
    """Cuenta por día en el histórico, solo registro del Senado.
    `dias` ya viene en el calendario de `anio`."""
    if not DIST.exists():
        print(f'  ! falta {DIST}', file=sys.stderr)
        return {}
    fechas = {d.isoformat() for d in dias}
    c = collections.Counter()
    with DIST.open(encoding='utf-8') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get('origen_registro') != 'senado':
                continue
            f = str(d.get('fecha_presentacion') or '')[:10]
            if len(f) != 10:
                continue
            try:
                fecha = dt.date.fromisoformat(f)
            except ValueError:
                continue
            if f in fechas:
                c[f] += 1
    return c


def serie_viva(dias):
    """La legislatura en curso no está en el histórico (su corte es jul-2026):
    sale del rastreo diario vía la Lambda."""
    try:
        req = urllib.request.Request(
            API, data=json.dumps({'action': 'radicados'}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read())
    except Exception as e:                                  # noqa: BLE001
        print(f'  ! no pude leer radicados: {e}', file=sys.stderr)
        return None                                          # ≠ Counter vacío: falló la fuente
    fechas = {x.isoformat() for x in dias}
    c = collections.Counter()
    for r in d.get('radicados') or []:                      # solo Senado, ver docstring
        f = str(r.get('fecha') or '').replace('/', '-')[:10]
        if f in fechas:
            c[f] += 1
    return c


def build(upload=False):
    hoy = dt.date.today()
    dias = ventana_hoy()
    if not dias:
        sys.exit('la ventana quedó vacía (¿fecha del sistema anterior a la instalación?)')
    viva = serie_viva(dias)
    if viva is None:
        # sin la serie de la legislatura viva el monitor mentiría con un cero
        # gigante: mejor no tocar el JSON publicado y que el frontend siga
        # mostrando el de la última corrida buena
        sys.exit('  ! sin datos de la legislatura viva; no se reescribe el JSON')
    series = {}
    for a in ANIOS:
        if a == max(ANIOS):
            c, ds = viva, dias
        else:
            # se mapea la ventana CORRIDA (no la hábil) y se vuelve a filtrar:
            # el equivalente de un lunes de 2026 puede caer en sábado de 2018
            corrida = [dias[0] - dt.timedelta(days=k) for k in range(DIAS)][::-1]
            corrida = [d for d in corrida if d >= dias[0] - dt.timedelta(days=DIAS)]
            ds = habiles([equivalente(d, a) for d in
                          [dias[0] + dt.timedelta(days=k) for k in range(DIAS)]])
            c = serie_historica(a, ds)
        series[str(a)] = {
            'dias': [{'d': d.strftime('%m-%d'), 'n': c.get(d.isoformat(), 0)} for d in ds],
            'total': sum(c.get(d.isoformat(), 0) for d in ds),
            'n_dias': len(ds),
        }
    out = {
        'v': hoy.isoformat(),
        'ventana': {'desde': dias[0].strftime('%m-%d'), 'hasta': dias[-1].strftime('%m-%d'),
                    'dias': len(dias), 'solo_habiles': True},
        'series': series,
        'fuente': ('Registro de proyectos de ley del Senado (leyes.senado.gov.co). '
                   'Solo esa fuente: el listado de Cámara no publica fecha de radicación, '
                   'así que incluirla haría incomparables los tres periodos. '
                   'Solo días hábiles: los fines de semana no hay radicación.'),
    }
    STAGE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for a in ANIOS:
        s = series[str(a)]
        print(f'· {a}: {s["total"]:>4} proyectos en {s["n_dias"]} días '
              f'({", ".join(str(x["n"]) for x in s["dias"])})')
    if upload:
        cmd = ['aws', 's3', 'cp', str(OUT), f's3://{S3_BUCKET}/{S3_PREFIX}/ritmo-legislaturas.json',
               '--content-type', 'application/json', '--cache-control', 'public, max-age=600']
        ok = subprocess.run(cmd).returncode == 0
        print('· subido a S3' if ok else '  ! no se pudo subir', file=sys.stderr if not ok else sys.stdout)
    else:
        print(f'· staging → {OUT.relative_to(REPO)}')
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--upload', action='store_true')
    build(upload=ap.parse_args().upload)
