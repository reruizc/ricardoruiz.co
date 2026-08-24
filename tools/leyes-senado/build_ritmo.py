#!/usr/bin/env python3
"""
Ritmo de radicación: cuántos proyectos de ley entran por día al arrancar cada
legislatura, comparando la que corre con las dos anteriores.

Alimenta el monitor que va al lado del título en legislativo.html. Emite un
JSON diminuto (~3 KB) porque el hub no puede pagar los 540 KB que pesa la
respuesta cruda de `radicados`.

LAS DOS CÁMARAS, NO SOLO SENADO  (cambió ago-2026)
  Hasta ago-2026 las tres series salían solo de leyes.senado.gov.co, con esta
  justificación: «el listado de Cámara no publica fecha de radicación, así que
  incluirlo le daría a 2026 un dato que 2018 y 2022 no tienen». Eso quedó
  OBSOLETO cuando `harvest_camara_fichas.py` empezó a cosechar la ficha
  individual de cada proyecto — el LISTADO no trae la fecha, pero la FICHA sí, y
  hoy la tienen 4.106 de 4.146 proyectos de Cámara (99,0%), con cobertura de
  95-100% en TODAS las legislaturas. Medido en la ventana 20→28 de julio:

      año   Senado  Cámara  TOTAL
      2018      73      34    107
      2022      87      59    146
      2026     120     100    220

  O sea que el monitor viejo publicaba ~2/3 del universo. Y la conclusión no
  solo sobrevive: 2026 vs 2022 pasa de +38% (solo Senado) a +51% (completo).

  No hay doble conteo: `build_dataset` deduplica, y el set de origen_registro
  'camara' EXCLUYE por construcción lo que ya está en el registro del Senado
  (ver `camara_merge`). Sí queda un subconteo residual —un proyecto radicado en
  Cámara que después cruza al Senado se cuenta bajo el Senado, con la fecha que
  el Senado registre— pero ese sesgo YA EXISTÍA en la versión solo-Senado; sumar
  Cámara no lo introduce, lo reduce.

VENTANA — CONSOLIDADA, y el rezago SE MIDE SOLO
  ⚠️⚠️ EL LISTADO DE CÁMARA PUBLICA CON REZAGO, y es IRREGULAR. Un proyecto
  radicado hoy no aparece hoy en camara.gov.co: aparece días después. Medido
  sobre los 60 proyectos de la legislatura viva de los que tenemos registro de
  primera aparición — **min 0 · p50 7 · p90 12 · máx 13 días** — o sea que no es
  una tubería de N días sino publicación a golpes (el 29-jul salió uno el MISMO
  día que se radicó, y ese mismo día salieron otros radicados 8 días antes).

  Por eso la ventana NO llega hasta hoy: termina en `hoy − lag`, donde el dato
  de Cámara ya está completo. Si llegara hasta hoy, la cola de la serie viva
  saldría con la Cámara a medias y treparía retroactivamente cada día — un sesgo
  CONTRA la legislatura nueva, invisible para quien mira el gráfico y peor que
  el que la versión vieja quería evitar.

  ⚠️ OJO: el rezago NO es un problema de fecha, es de EXISTENCIA. La ficha de
  camara.gov.co sí trae "Fecha de Radicación" (es la que cosechamos); lo que
  pasa es que el proyecto todavía no está en el listado, así que no hay fila que
  leer. Ningún campo de fecha lo arregla — solo esperar a que lo publiquen.

  EL LAG NO ES UNA CONSTANTE A OJO: lo calcula `lag_observado()` en cada corrida,
  cruzando cuándo vio el rastreo cada proyecto por primera vez
  (`diario-camara/novedades/*.json`) contra su fecha de radicación real (la
  ficha). Se toma el MÁXIMO observado + 1 día de margen, acotado a
  [LAG_MIN, LAG_MAX]. Así, si el rezago de julio-2026 era cola del arranque y
  Cámara se pone al día, la ventana se acerca sola a hoy; y si se atrasa más, se
  aleja sola. Sin historial utilizable cae a LAG_MAX, que es el lado seguro.
  (Un cron caído infla el lag observado — el proyecto se "ve" tarde — así que el
  error empuja hacia la ventana más conservadora, nunca hacia publicar de más.)

  El cuadro se llama "El arranque", así que la ventana es ACUMULADA desde la
  instalación (20-jul) hasta el último día cerrado (ayer), mapeada a las mismas
  fechas de hace 4 y 8 años. Los días más recientes pueden crecer cuando Cámara
  publique su rezago: se marcan como provisionales en vez de ocultar tres
  semanas y dejar el gráfico congelado en julio.

  SOLO DÍAS HÁBILES: en el Congreso no se radica los fines de semana, así que
  sus ceros no son actividad baja sino ausencia de calendario — dejarlos hundía
  la línea al piso cada cinco puntos. Ojo, el filtro va sobre el calendario DE
  CADA AÑO (el equivalente de un lunes de 2026 puede caer sábado en 2018), así
  que las tres series pueden quedar de largo distinto mientras la ventana está
  recortada por el piso del 20-jul; por eso al final se TRUNCAN todas al largo
  de la más corta — si no, se compararían totales de 5 días contra 4. NO se
  descuentan festivos: exigiría el calendario oficial de cada año.

FUENTE ÚNICA: el dataset
  Las tres series salen de `dist/proyectos.jsonl`, que desde ago-2026 ya incluye
  la legislatura viva (Senado y Cámara). Antes la serie viva tenía que pedirse a
  la Lambda porque el dataset no la tenía; eso se cayó con el fix de `pdate` en
  build_dataset (el manifiesto diario escribe la fecha como '2026/07/20' —año
  primero— y el parser solo aceptaba día primero, así que los 154 radicados del
  Senado vivo perdían la fecha en silencio). Una fuente en vez de dos = un modo
  de falla menos y tres series construidas exactamente igual.

  Por eso esta etapa DEPENDE de `dataset_build` y en el cron va después de él.

Cuenta proyectos de ley (`proyectos.jsonl`). Los actos legislativos van aparte y
no entran: son otro trámite, con otro reloj.

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
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
DIST = SRC / 'dist' / 'proyectos.jsonl'
NOVEDADES_CAM = SRC / 'diario-camara' / 'novedades'
FICHAS_CAM = SRC / 'camara' / 'fichas.jsonl'
STAGE = SRC / 'en-vivo'
OUT = STAGE / 'ritmo-legislaturas.json'

S3_BUCKET = 'elecciones-2026'
S3_PREFIX = 'ricardoruiz.co/congreso-2026/output/legislativo'

ANIOS = [2026, 2022, 2018]      # la viva primero
LAG_MIN, LAG_MAX = 3, 21         # cotas del rezago de publicación de Cámara
INSTALACION = dt.date(2026, 7, 20)
REGISTROS = ('senado', 'camara')


def habiles(dias):
    return [d for d in dias if d.weekday() < 5]        # 5=sáb, 6=dom


def lag_observado():
    """Cuántos días tarda Cámara en publicar lo que ya radicó, medido con
    nuestros propios datos → (lag_a_usar, detalle).

    Cruza la primera vez que el rastreo diario vio cada proyecto (el archivo de
    novedades donde aparece) contra su fecha de radicación real (la ficha). Los
    proyectos que ya estaban ahí cuando arrancó el rastreo no tienen primera
    aparición y quedan fuera: de esos no sabemos el rezago y suponerlo sería
    inventarlo.

    Se usa el MÁXIMO + 1 de margen, no la mediana: la ventana promete estar
    consolidada, y con una mediana se publicaría a medias la mitad de las veces.
    Acotado a [LAG_MIN, LAG_MAX] para que ni un outlier mande el gráfico a un mes
    atrás ni una racha buena lo pegue a hoy."""
    fallback = (LAG_MAX, {'fuente': 'cota (sin historial utilizable)', 'n': 0})
    if not (NOVEDADES_CAM.is_dir() and FICHAS_CAM.exists()):
        return fallback
    try:
        radicacion = {}
        with FICHAS_CAM.open(encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                o = json.loads(line)
                nro, f = (o.get('nro_camara') or '').strip(), o.get('fecha_radicacion_camara')
                if nro and f:
                    radicacion[nro] = f
        visto = {}
        for p in sorted(NOVEDADES_CAM.glob('*.json')):
            d = json.loads(p.read_text(encoding='utf-8'))
            dia = d.get('fecha')
            for x in (d.get('nuevos') or []):
                k = (x.get('numero_camara') or '').strip()
                if k and dia and k not in visto:      # sorted() ⇒ el primero es el primero
                    visto[k] = dia
        lags = []
        for k, dia in visto.items():
            f = radicacion.get(k)
            if not f:
                continue
            try:
                lags.append((dt.date.fromisoformat(dia) - dt.date.fromisoformat(f)).days)
            except ValueError:
                continue
        lags = [x for x in lags if x >= 0]            # una fecha rara no baja la guardia
        if not lags:
            return fallback
        lags.sort()
        crudo = lags[-1] + 1
        return max(LAG_MIN, min(LAG_MAX, crudo)), {
            'fuente': 'medido', 'n': len(lags), 'max': lags[-1],
            'p50': lags[len(lags) // 2], 'p90': lags[int(.9 * (len(lags) - 1))],
            'crudo': crudo, 'acotado': not (LAG_MIN <= crudo <= LAG_MAX),
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return fallback                                # el monitor no se cae por esto


def ventana():
    """Arranque acumulado desde la instalación hasta el último día cerrado.

    Hoy queda fuera: la corrida de la mañana no debe comparar un día 2026 aún
    abierto contra días históricos completos. El filtro de hábiles se aplica
    después sobre el calendario de cada legislatura.
    """
    cierre = dt.date.today() - dt.timedelta(days=1)
    if cierre < INSTALACION:
        return []
    return [INSTALACION + dt.timedelta(days=i)
            for i in range((cierre - INSTALACION).days + 1)]


def equivalente(fecha, anio):
    """La misma fecha calendario en la legislatura de `anio` (−4/−8 años).
    El 29-feb sin equivalente cae al 28."""
    try:
        return fecha.replace(year=fecha.year - (2026 - anio))
    except ValueError:
        return fecha.replace(year=fecha.year - (2026 - anio), day=28)


def cargar(corrida):
    """Una pasada por el dataset → {fecha_iso: {'senado': n, 'camara': n}}.

    Solo se guardan los días que alguna de las tres series va a pedir, así que
    el dict queda en unas decenas de entradas por más que el archivo tenga 14k
    proyectos."""
    if not DIST.exists():
        sys.exit(f'  ! falta {DIST} (¿corrió build_dataset?); no se reescribe el JSON')
    quiero = set()
    for d in corrida:
        for a in ANIOS:
            quiero.add(equivalente(d, a).isoformat())
    acum = collections.defaultdict(collections.Counter)
    with DIST.open(encoding='utf-8') as fh:
        for line in fh:
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            f = str(p.get('fecha_presentacion') or '')[:10]
            if f not in quiero:
                continue
            reg = p.get('origen_registro')
            if reg in REGISTROS:
                acum[f][reg] += 1
    return acum


def build(upload=False):
    lag, lag_info = lag_observado()
    corrida = ventana()
    if not corrida:
        sys.exit('la ventana quedó vacía (¿fecha del sistema anterior a la instalación?)')
    acum = cargar(corrida)

    # cada año filtra hábiles sobre SU calendario, así que los largos pueden
    # diferir mientras la ventana esté recortada por el piso del 20-jul
    dias_por_anio = {a: habiles([equivalente(d, a) for d in corrida]) for a in ANIOS}
    n = min(len(v) for v in dias_por_anio.values())
    if not n:
        sys.exit('  ! ningún día hábil en la ventana; no se reescribe el JSON')
    # se truncan por la COLA: los días recortados son los del final, así las tres
    # series siguen arrancando en el mismo punto del calendario
    dias_por_anio = {a: v[:n] for a, v in dias_por_anio.items()}

    series = {}
    for a in ANIOS:
        ds = dias_por_anio[a]
        filas = []
        for d in ds:
            c = acum.get(d.isoformat(), {})
            s, cam = c.get('senado', 0), c.get('camara', 0)
            filas.append({'d': d.strftime('%m-%d'), 'n': s + cam, 's': s, 'c': cam})
        series[str(a)] = {
            'dias': filas,
            'total': sum(x['n'] for x in filas),
            'total_senado': sum(x['s'] for x in filas),
            'total_camara': sum(x['c'] for x in filas),
            'n_dias': len(filas),
        }

    vivo = series[str(max(ANIOS))]
    # dos guardas: publicar un cero pinta un desplome falso, y publicar la serie
    # viva sin Cámara mientras las viejas sí la traen es justo el sesgo invisible
    # que la ventana consolidada existe para evitar
    if not vivo['total']:
        sys.exit('  ! la legislatura viva quedó en cero; no se reescribe el JSON '
                 '(revisar dataset_build / el rastreo diario)')
    if not vivo['total_camara'] and any(series[str(a)]['total_camara']
                                        for a in ANIOS if a != max(ANIOS)):
        sys.exit('  ! la serie viva no trae Cámara y las históricas sí: el dato de '
                 'Cámara está rezagado (¿corrió camara_fichas?). No se reescribe '
                 'el JSON para no publicar una comparación sesgada.')

    hoy = dt.date.today()
    d0, d1 = dias_por_anio[max(ANIOS)][0], dias_por_anio[max(ANIOS)][-1]
    out = {
        'v': hoy.isoformat(),
        'ventana': {
            'desde': d0.strftime('%m-%d'), 'hasta': d1.strftime('%m-%d'),
            'dias': n, 'solo_habiles': True,
            'acumulada': True, 'hasta_ultimo_dia_cerrado': True,
            'consolidada': False, 'lag_dias': lag, 'lag': lag_info,
            'consolidada_hasta': (hoy - dt.timedelta(days=lag)).isoformat(),
            'provisional_desde': (hoy - dt.timedelta(days=lag - 1)).isoformat(),
        },
        'registros': list(REGISTROS),
        'series': series,
        'fuente': ('Registro de proyectos de ley del Senado (leyes.senado.gov.co) y de '
                   'la Cámara de Representantes (camara.gov.co), deduplicados: un '
                   'proyecto que cruza de cámara se cuenta una sola vez. La fecha de '
                   'radicación de Cámara sale de la ficha de cada proyecto, no del '
                   'listado. La ventana acumula desde el 20 de julio hasta el último '
                   f'día cerrado; los últimos {lag} días son provisionales porque el '
                   'listado de Cámara publica con rezago y pueden crecer en corridas '
                   'posteriores. Se excluyen fines de semana; no se descuentan festivos.'),
    }
    STAGE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    det = (f"medido sobre {lag_info['n']} proyectos: máx {lag_info['max']} · "
           f"p90 {lag_info['p90']} · p50 {lag_info['p50']}"
           if lag_info.get('fuente') == 'medido' else lag_info.get('fuente'))
    print(f'· rezago de Cámara → {lag} días ({det})'
          + ('  [acotado]' if lag_info.get('acotado') else ''))
    print(f'· arranque acumulado {d0.isoformat()} → {d1.isoformat()} '
          f'({n} días hábiles · últimos {lag} días provisionales para Cámara)')
    for a in ANIOS:
        s = series[str(a)]
        print(f'· {a}: {s["total"]:>4} proyectos  (Senado {s["total_senado"]:>3} · '
              f'Cámara {s["total_camara"]:>3})  '
              f'[{", ".join(str(x["n"]) for x in s["dias"])}]')
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
