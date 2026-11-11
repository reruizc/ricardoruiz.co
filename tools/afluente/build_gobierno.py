#!/usr/bin/env python3
"""Afluente · «El Gobierno»: decretos y borradores en consulta pública, en abierto.

Lee tres archivos PRIVADOS de Caudal (s3://caudal-legislativo/metadata/) y publica
un JSON abierto con lo que de todos modos es información oficial pública:

  · normativa.jsonl            decretos, leyes, resoluciones, directivas y circulares
                               de Presidencia (Socrata + Diario Oficial)
  · sucop.jsonl                borradores en consulta pública en SUCOP
  · entidades-borradores.jsonl borradores que las entidades publican por fuera de SUCOP

La raya entre lo abierto y Caudal: aquí va el listado oficial (título, entidad,
plazo, enlace a la fuente). Se queda en Caudal todo lo que es análisis: el radar
por sector, las agendas regulatorias, superintendencias, contratación y briefs.

Salida: Bases de datos/afluente/gobierno.json
  --subir   lo sube comprimido a congreso-2026/output/legislativo/afluente/ y lo relee
            por la URL pública para comprobar que quedó bien.
  --local DIR  lee los tres .jsonl de DIR en vez de S3 (pruebas).

Sale con 1, sin escribir ni subir, si los decretos o las consultas vienen vacíos:
en S3 queda la copia anterior. Una página que de pronto dice «no hay decretos»
es peor que una página con el dato de ayer.
"""
import argparse, datetime as dt, gzip, io, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(REPO, 'Bases de datos', 'afluente', 'gobierno.json')
PRIV = 's3://caudal-legislativo/metadata/'
PUB_KEY = 'ricardoruiz.co/congreso-2026/output/legislativo/afluente/gobierno.json'
PUB_S3 = 's3://elecciones-2026/' + PUB_KEY
PUB_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/' + PUB_KEY
ARCHIVOS = ['normativa.jsonl', 'sucop.jsonl', 'entidades-borradores.jsonl']

DIAS_NORMAS = 60          # ventana de normas expedidas que se publican
TIPOS_NORMA = {'DECRETOS': 'Decreto', 'LEYES': 'Ley', 'RESOLUCIONES': 'Resolución',
               'DIRECTIVAS': 'Directiva', 'CIRCULARES': 'Circular',
               'ACTOS LEGISLATIVOS': 'Acto legislativo'}   # fuera: AGENDA REGULATORIA (es de Caudal)

# Decretos de personal (nombramientos, renuncias, encargos, extradiciones…): son
# la mitad de los decretos y no le cambian nada a nadie fuera de la entidad.
# Misma regla que _es_decreto_personal de la Lambda de Caudal: se busca el
# SUSTANTIVO de personal, no el verbo («se retira la subpartida» no es personal).
PERSONAL_RE = re.compile(
    r'^\W*por (?:medio )?(?:del|de la|el|la|e.) (?:cua.? )?se .{0,45}?'
    r'(nombramiento|nornbramiento|nompramiento|\bnombra\b|renuncia|encargo|\bencarga\b'
    r'|\bdesigna\b|designacion|designan|traslad|ascien|ascenso|insubsisten|extradicion|vacaciones|vinculacion'
    r'|comision de servicios|retiro del servicio|retira del servicio|condecora|\bposesion\b|licencia ordinaria)')
NO_PERSONAL_RE = re.compile(r'presupuest|arancel|subpartida|regimen|reglament|tarifa|liquidacion de|punto focal|centro nacional')


def sin_tildes(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def es_personal(desc):
    d = sin_tildes((desc or '')[:220])
    return bool(PERSONAL_RE.search(d)) and not NO_PERSONAL_RE.search(d)


def clave_titulo(s):
    return re.sub(r'[^a-z0-9]+', ' ', sin_tildes(s)).strip()[:90]


def hoy_bogota():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=5)).date()


def leer_jsonl(ruta):
    # split('\n') literal: un texto con U+2028 partiría el JSONL con splitlines().
    with open(ruta, encoding='utf-8') as f:
        return [json.loads(l) for l in f.read().split('\n') if l.strip()]


def bajar(dest):
    for a in ARCHIVOS:
        r = subprocess.run(['aws', 's3', 'cp', '--only-show-errors', PRIV + a, os.path.join(dest, a)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode:
            sys.exit(f'✗ no pude bajar {a}: {r.stderr.strip()}')


def normas(N, hoy):
    desde = (hoy - dt.timedelta(days=DIAS_NORMAS)).isoformat()
    out, personal = [], 0
    for x in N:
        tipo = TIPOS_NORMA.get(x.get('tipo'))
        f = str(x.get('fecha') or '')[:10]
        if not tipo or f < desde or f > hoy.isoformat():
            continue
        if tipo == 'Decreto' and es_personal(x.get('descripcion')):
            personal += 1
            continue
        pub = x.get('publicacion') or {}
        r = {'tipo': tipo, 'n': str(x.get('numero') or ''), 'a': str(x.get('anio') or ''), 'f': f,
             'd': (x.get('descripcion') or '').strip()}
        if x.get('url'):
            r['url'] = x['url']
        if pub.get('edicion'):
            r['do'] = pub['edicion']
            if pub.get('pagina'):
                r['pg'] = pub['pagina']
        if x.get('legislativo'):
            r['leg'] = True
        out.append(r)
    out.sort(key=lambda r: (r['f'], r['n'].zfill(6)), reverse=True)
    return out, personal


def consultas(S, B, hoy):
    h = hoy.isoformat()
    out, vistos = [], set()

    def fila(x, fuente):
        fin = str(x.get('fecha_fin') or '')[:10]
        if not fin or fin < h:
            return None
        return {'t': (x.get('titulo') or '').strip(), 'o': (x.get('objeto') or '').strip(),
                'e': (x.get('entidad') or '').strip(), 's': (x.get('sector') or '').strip(),
                'tn': '' if x.get('tipo_norma') in (None, '', 'No especificado') else x['tipo_norma'],
                'ini': str(x.get('fecha_inicio') or '')[:10], 'fin': fin,
                'com': int(x.get('comentarios') or 0), 'url': x.get('url') or '', 'src': fuente}

    for x in S:
        if x.get('tipo') != 'norma' or x.get('estado_consulta') not in ('abierta', 'cierra_pronto'):
            continue
        r = fila(x, 'sucop')
        if r:
            out.append(r)
            vistos.add(clave_titulo(r['t']))
    # Por fuera de SUCOP: solo las activas con plazo conocido. Si el título ya
    # está en SUCOP, manda SUCOP (misma regla que _sucop() de la Lambda).
    for x in B:
        if x.get('estado') != 'Activa' or x.get('sin_texto') or clave_titulo(x.get('titulo')) in vistos:
            continue
        r = fila(x, 'entidad')
        if r:
            out.append(r)
    out.sort(key=lambda r: (r['fin'], r['e']))
    return out


def agendas(S, hoy):
    """Agendas regulatorias del año siguiente que están en consulta pública.
    Solo la entidad, el plazo y el enlace a SUCOP: lo que trae cada agenda
    (qué piensa regular la entidad y cuándo) es el radar de Caudal."""
    h = hoy.isoformat()
    out = []
    for x in S:
        fin = str(x.get('fecha_fin') or '')[:10]
        if x.get('tipo') != 'agenda' or x.get('estado_consulta') not in ('abierta', 'cierra_pronto') or not fin or fin < h:
            continue
        out.append({'e': (x.get('entidad') or '').strip(), 'a': str(x.get('anio') or ''), 'fin': fin,
                    'url': x.get('url') or ''})
    out.sort(key=lambda r: (r['fin'], r['e']))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subir', action='store_true')
    ap.add_argument('--local')
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        src = a.local or tmp
        if not a.local:
            bajar(tmp)
        N, S, B = (leer_jsonl(os.path.join(src, f)) for f in ARCHIVOS)

    hoy = hoy_bogota()
    nor, personal = normas(N, hoy)
    con = consultas(S, B, hoy)
    age = agendas(S, hoy)
    if not nor:
        sys.exit(f'✗ cero normas en los últimos {DIAS_NORMAS} días: no se publica (en S3 queda la anterior)')
    if not con:
        # Puede pasar de verdad (un puente festivo), pero SUCOP nunca ha bajado de 20
        # consultas abiertas: cero es mucho más probable un harvest roto.
        sys.exit('✗ cero consultas abiertas: no se publica (en S3 queda la anterior)')

    doc = {
        'v': 1, 'generado': dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + 'Z',
        'hoy': hoy.isoformat(),
        'cobertura': {'normas_hasta': max(r['f'] for r in nor), 'dias_normas': DIAS_NORMAS},
        'n': {'normas': len(nor), 'decretos_personal_omitidos': personal, 'consultas': len(con),
              'consultas_fuera_sucop': sum(1 for r in con if r['src'] == 'entidad'), 'agendas': len(age)},
        'consultas': con,
        'agendas': age,
        'normas': nor,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    raw = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with open(OUT, 'wb') as f:
        f.write(raw)
    print(f'· {OUT}: {len(nor)} normas (sin {personal} decretos de personal) · '
          f'{len(con)} consultas abiertas ({doc["n"]["consultas_fuera_sucop"]} por fuera de SUCOP) · {len(age)} agendas · {len(raw)//1024} KB')

    if a.subir:
        gz = os.path.join(os.path.dirname(OUT), 'gobierno.json.gz')
        with gzip.open(gz, 'wb', compresslevel=9) as f:
            f.write(raw)
        r = subprocess.run(['aws', 's3', 'cp', '--only-show-errors', gz, PUB_S3,
                            '--content-type', 'application/json', '--content-encoding', 'gzip',
                            '--cache-control', 'public, max-age=300'],
                           capture_output=True, text=True, timeout=300)
        if r.returncode:
            sys.exit(f'✗ no pude subir: {r.stderr.strip()}')
        # Releer por la URL pública: si la política del bucket no cubre el
        # prefijo, la página quedaría con 403 y nada avisaría.
        req = urllib.request.Request(PUB_URL + '?nc=' + doc['generado'],
                                     headers={'User-Agent': 'afluente-build/1', 'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            if resp.headers.get('Content-Encoding') == 'gzip' or body[:2] == b'\x1f\x8b':
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
        if body != raw:
            sys.exit('✗ lo publicado no coincide con lo generado')
        print(f'· subido y verificado: {PUB_URL}')


if __name__ == '__main__':
    main()
