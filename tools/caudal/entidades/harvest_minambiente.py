#!/usr/bin/env python3
"""
Caudal · Ministerio de Ambiente y Desarrollo Sostenible (tanda 3, nov-2026).

  borradores  POST /wp-admin/admin-ajax.php  action=consultas_paginacion-load-posts   (12 por página)
  normas      /normativa/{resoluciones,circulares,decretos}/  + action=normativa_paginacion-load-posts
  noticias    /feed/  (RSS de WordPress, 12 por página)
  eventos     /?mec-ical-feed=1  (iCal del plugin MEC)

⚠️ Desde 2025 no publica borradores en SUCOP (allí quedan 22 viejos): esta es la única vía.
⚠️ La lista de consultas no va por fecha (un plazo de dic-2025 cae entre los de julio
de 2026): se corta cuando una página entera ya es anterior a DESDE, no en la primera vieja.
⚠️ La lista mezcla normas con el esquema de publicación y el programa de transparencia,
que no son borradores (`_INSTITUCIONAL`). Políticas, guías y AIN sí entran.
⚠️ El borrador viene en un .zip o .7z, no en un PDF: la tarjeta enlaza a la descarga.
⚠️ Las normas van en una tarjeta por año y el id de cada año (`area2`) se inventa al
crearla: 2026 es 1049. Se descubre en la página, nunca se fija acá.
⚠️ Buena parte de las resoluciones liquidan contratos o resuelven casos de una sola
persona: se marcan `administrativo`, no se borran (`_PARTICULAR`).
⚠️ Los decretos ya entran por Presidencia: solo quedan los que `normativa.jsonl` no trae.
⚠️ Su calendario está parado: `/agenda/` dice «¡No hay eventos!» y el iCal termina el
7-jul-2026. Se sigue leyendo porque es la fuente oficial; el catálogo lo dice.
⚠️ La API `/wp-json/wp/v2/mec-events` responde 401.

Salida: `Bases de datos/caudal-entidades/raw/minambiente/{proyectos,normas,noticias,eventos}.json`.
Uso: python3 tools/caudal/entidades/harvest_minambiente.py fetch
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse

import comun as C

BASE = 'https://www.minambiente.gov.co'
AJAX = f'{BASE}/wp-admin/admin-ajax.php'
OUT = C.RAW / 'minambiente'
DESDE = '2025-01-01'
CAIDA = .5          # una corrida con menos de la mitad de la anterior no se publica
TOPE = 40           # páginas de consultas: de sobra, y evita un bucle si el sitio se enreda
CLASES = {'resoluciones': ('RESOLUCIONES', 'Resolución'), 'circulares': ('CIRCULARES', 'Circular'),
          'decretos': ('DECRETOS', 'Decreto')}
_INSTITUCIONAL = re.compile(r'(?i)esquema de publicaci|programa de transparencia|plan anticorrupci|'
                            r'participaci[oó]n ciudadana|plan de acci[oó]n institucional|agenda regulatoria')
_PARTICULAR = re.compile(r'(?i)\bcontrato\b|liquida(?:ci[oó]n)? unilateral|se liquida|cumplimiento de (?:un )?fallo|'
                         r'sentencia|se resuelve|recurso|delega|tutela|plan anual de|manual de funciones|'
                         r'modifica la planta|ordena (?:el|un) pago|reconoce(?:n)? (?:y ordena|un|una|el|la)\b|'
                         r'sancionatorio|medida preventiva|sustracci[oó]n|fuerza ejecutoria|bienes muebles|'
                         r'presupuesto|negociaci[oó]n colectiva|planta de personal|parqueaderos|desistimiento|'
                         r'revoca directamente')
_NUM = re.compile(r'(?i)(?:resoluci[oó]n|res\.|decreto|circular)\s*(?:externa|interna|conjunta)?\s*(?:no\.?|n[°º.]*|nro\.?)?\s*0*(\d+(?:E\d+)?)')
_MES_DIA = re.compile(r'([a-záéíóú]+)\s+(\d{1,2}),\s*(20\d{2})')


def _guarda(nombre, leidos, previo):
    """Mide lo que dio la fuente, no lo acumulado: si cae a menos de la mitad
    de la corrida anterior, o a cero, se conserva el archivo que había."""
    antes = (previo or {}).get('leidos') or 0
    if not leidos or leidos < antes * CAIDA:
        raise RuntimeError(f'guarda: {nombre} trae {leidos} contra {antes} de la corrida anterior')


def _post(datos, intentos=3):
    cmd = ['/usr/bin/curl', '-s', '-L', '--max-time', '90', '-A', C.UA, '-w', '%{http_code}',
           '--data', urllib.parse.urlencode(datos), AJAX]
    ultimo = ''
    for i in range(intentos):
        r = subprocess.run(cmd, capture_output=True, timeout=110)
        out = r.stdout.decode('utf-8', 'replace')
        if r.returncode == 0 and out[-3:] == '200':
            return out[:-3]
        ultimo = f'rc={r.returncode} http={out[-3:]}'
        time.sleep(3 * (i + 1))
    raise RuntimeError(f'{ultimo} en {datos.get("action")} p.{datos.get("page")}')


def _dmy(s):
    m = re.search(r'(\d{2})-(\d{2})-(\d{4})', s or '')
    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else ''


def _campo(b, rotulo):
    m = re.search(rf'{rotulo}:? *</span>\s*<span>(.*?)</span>', b, re.S)
    return C.limpio(html.unescape(m.group(1))) if m else ''


def _clase(titulo, archivo):
    """Qué es el borrador: lo dice el título o el archivo, y si no, el género de «por el/la cual»."""
    t = C.fold(titulo)
    a = C.fold(archivo)
    if t.startswith('decreto') or 'decreto' in a:
        return 'Proyecto de Decreto'
    if t.startswith('resolucion') or 'resolucion' in a:
        return 'Proyecto de Resolución'
    if 'por el cual' in t:
        return 'Proyecto de Decreto'
    if 'por la cual' in t or 'por medio de la cual' in t:
        return 'Proyecto de Resolución'
    if 'analisis de impacto normativo' in t:
        return 'Análisis de impacto normativo'
    if t.startswith('politica') or ' politica nacional' in t:
        return 'Proyecto de Política'
    return 'Documento en consulta'


def _consultas(n):
    return _post({'action': 'consultas_paginacion-load-posts', 'page': n, 'categoria': 0, 'area': 0, 'fecha': 0})


def proyectos(prev):
    previos = prev.get('items', {})
    hoy = datetime.date.today().isoformat()
    vivos, leidos = {}, 0
    for n in range(1, TOPE):
        h = _consultas(n)
        bloques = re.split(r'class="consulta-std', h)[1:]
        if not bloques:
            break
        leidos += len(bloques)
        finales = []
        for b in bloques:
            titulo = _campo(b, 'Nombre del proyecto').strip(' "“”')
            fin = _dmy(_campo(b, r'Hasta'))
            finales.append(fin)
            if fin and fin < DESDE or not titulo or _INSTITUCIONAL.search(titulo):
                continue
            d = re.search(r'href="([^"]+)"[^>]*><button class="[^"]*btn-descargar', b)
            r = re.search(r'href="(https?://[^"]+)"[^>]*><button class="[^"]*btn-respuesta', b)
            url = html.unescape(d.group(1)) if d else ''
            k = hashlib.sha1((url or titulo).encode()).hexdigest()[:16]
            ini = _dmy(_campo(b, r'Desde'))
            vivos[k] = {'id': k, 'tipo_norma': _clase(titulo, url.rsplit('/', 1)[-1]), 'titulo': titulo[:400],
                        'dependencia': _campo(b, 'Dependencia'), 'fecha_inicio': ini, 'fecha_fin': fin,
                        'comentarios_a': _campo(b, 'Contacto'), 'url': url, 'anexos': [html.unescape(r.group(1))] if r else [],
                        'creado': ini, 'visto': hoy, 'vigente_en_fuente': True}
        if all(f and f < DESDE for f in finales):
            break
    _guarda('borradores', leidos, prev)
    out = dict(previos)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, leidos


def _fecha_norma(titulo, publicado):
    f = C.fecha_larga(titulo.lower())
    if f:
        return f
    m = _MES_DIA.search((publicado or '').lower())
    return C.fecha_larga(f'{m.group(2)} de {m.group(1)} de {m.group(3)}') if m else ''


def _filas(h, tipo, subtipo, anio):
    out = []
    for a in re.split(r'(?=<a class="documento-normativa")', h)[1:]:
        u = re.search(r'href="([^"]+)"', a)
        t = re.search(r'title="([^"]*)"', a)
        if not u:
            continue
        titulo = C.limpio(html.unescape(t.group(1) if t else ''))
        d = re.search(r'class="descripcion-archivo">(.*?)</p>', a, re.S)
        desc = C.limpio(html.unescape(d.group(1))).strip(' "“”') if d else ''
        p = re.search(r'Publicado:\s*([^<]+)', a)
        fecha = _fecha_norma(titulo, p.group(1) if p else '')
        n = _NUM.search(titulo)
        particular = not desc or C.es_administrativo(desc) or bool(_PARTICULAR.search(desc))
        rotulo = re.findall(r'\b(20\d{2})\b', titulo)   # hay una de 2026 dentro de la tarjeta de 2025
        out.append({'tipo': tipo, 'subtipo': subtipo, 'numero': n.group(1) if n else '', 'anio': rotulo[-1] if rotulo else anio,
                    'fecha': fecha, 'titulo': titulo, 'descripcion': desc or titulo, 'administrativo': particular,
                    'url': html.unescape(u.group(1))})
    return out


def _tarjetas(clase):
    """{año: datos del POST} de las tarjetas de /normativa/<clase>/."""
    h = C.curl(f'{BASE}/normativa/{clase}/', timeout=120)
    t = re.sub(r'\s+', ' ', h)
    fn = {i: dict(zip(('areaActivador', 'area1', 'area2', 'categoria'), v)) for i, *v in re.findall(
        r'function mads_cargar_normativa_(\d+)\(page\)\{.*?areaActivador = (\d+); var \$area1 = (\d+); '
        r'var \$area2 = (\d+); var \$cat = (\d+);', t)}
    return {a: fn[i] for a, i in re.findall(r'<span class="title">(\d{4})</span>.*?mads-paginacion_container_normativa_(\d+)"', h, re.S)
            if i in fn}


def _en_presidencia():
    """(año, número) de los decretos que ya trae el pilar Ejecutivo. Si S3 no
    responde se sigue sin filtrar: un repetido estorba menos que uno perdido."""
    try:
        r = subprocess.run(['aws', 's3', 'cp', 's3://caudal-legislativo/metadata/normativa.jsonl', '-'],
                           capture_output=True, check=True, timeout=120)
        filas = [json.loads(x) for x in r.stdout.decode().splitlines()]
    except Exception as e:
        print(f'  minambiente · no se leyó normativa.jsonl ({e}): van todos los decretos', file=sys.stderr)
        return set()
    return {(str(x.get('anio')), str(x.get('numero')).lstrip('0')) for x in filas if x.get('tipo') == 'DECRETOS'}


def normas(prev):
    anio = datetime.date.today().year
    out, leidos = {}, 0
    for clase, (tipo, subtipo) in CLASES.items():
        tarjetas = _tarjetas(clase)
        for a in (str(anio - 1), str(anio)):
            datos = tarjetas.get(a)
            if not datos:                # en enero la tarjeta del año nuevo aún no existe
                print(f'  minambiente · {clase} sin tarjeta de {a}', file=sys.stderr)
                continue
            n = 1
            while n < TOPE:
                h = _post({**datos, 'page': n, 'action': 'normativa_paginacion-load-posts'})
                filas = _filas(h, tipo, subtipo, a)
                if not filas:
                    break
                leidos += len(filas)
                for f in filas:                  # algunas están subidas dos veces, con distinto archivo
                    out[(f['tipo'], f['numero'], f['anio']) if f['numero'] else f['url']] = f
                if not re.search(rf"<li p='{n + 1}'", h):
                    break
                n += 1
    _guarda('normas', leidos, prev)
    ya = _en_presidencia()
    decretos = sum(1 for x in out.values() if x['tipo'] == 'DECRETOS')
    xs = [x for x in out.values() if x['tipo'] != 'DECRETOS' or (x['anio'], x['numero'].lstrip('0')) not in ya]
    return xs, leidos, decretos


def noticias(prev):
    out = {x['url']: x for x in prev.get('items', [])}
    filas = C.rss(f'{BASE}/feed/')
    _guarda('noticias', len(filas), prev)
    primera = not out
    for p in (range(2, 11) if primera else ()):          # primera carga: 120 noticias, el feed solo da 12
        try:
            filas += C.rss(f'{BASE}/feed/?paged={p}')
        except RuntimeError:
            break
    for r in filas:
        out[r['url']] = C.comunicado(r['titulo'], r['fecha'], r['url'], r['resumen'])
    return list(out.values()), (12 if primera else len(filas))


def eventos(prev):
    ics = C.curl(f'{BASE}/?mec-ical-feed=1', timeout=90)
    bloques = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics, re.S)
    _guarda('eventos', len(bloques), prev)
    out = []
    for blk in bloques:
        blk = re.sub(r'\r?\n[ \t]', '', blk)          # líneas plegadas del ICS
        g = lambda k: (re.search(rf'^{k}[^:\n]*:(.*)$', blk, re.M) or [None, ''])[1].strip()
        ini = g('DTSTART')
        dia = f'{ini[:4]}-{ini[4:6]}-{ini[6:8]}' if len(ini) >= 8 else ''
        if dia < DESDE:
            continue
        esc = lambda s: s.replace('\\n', ' ').replace('\\,', ',').replace(chr(92) + ';', ';')
        desc = re.sub(r'\(\s*https?://\S+\s*\)', ' ', esc(g('DESCRIPTION')))
        url = g('URL')
        out.append({'id': g('UID'), 'titulo': esc(g('SUMMARY')), 'fecha_inicio': ini, 'fecha_fin': g('DTEND'), 'dia': dia,
                    'lugar': esc(g('LOCATION')), 'descripcion': C.limpio(desc)[:800], 'categorias': esc(g('CATEGORIES')).split(',') if g('CATEGORIES') else [],
                    'url': url})
    return out, len(bloques)


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    hoy = datetime.date.today().isoformat()
    ok = True

    def etapa(nombre, archivo, fn, resumen):
        nonlocal ok
        try:
            xs, leidos = fn(C.leer(OUT / archivo, {}) or {})
            C.escribir(OUT / archivo, {'generado': gen, 'leidos': leidos, 'items': xs})
            print(f'  minambiente · {nombre}: {resumen(xs, leidos)}')
        except Exception as e:
            ok = False
            print(f'  minambiente · {nombre} FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)

    etapa('borradores', 'proyectos.json', proyectos,
          lambda xs, n: f"{n} en la lista · {len(xs)} desde {DESDE} · {sum(1 for v in xs.values() if v['fecha_fin'] >= hoy)} abiertos")
    try:
        prev = C.leer(OUT / 'normas.json', {}) or {}
        xs, leidos, dec = normas(prev)
        C.escribir(OUT / 'normas.json', {'generado': gen, 'leidos': leidos, 'items': xs})
        print(f"  minambiente · normas: {leidos} leídas · {len(xs)} quedan · {dec} decretos, "
              f"{sum(1 for x in xs if x['tipo'] == 'DECRETOS')} que Presidencia no trae · "
              f"{sum(1 for x in xs if x['administrativo'])} administrativas")
    except Exception as e:
        ok = False
        print(f'  minambiente · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    etapa('noticias', 'noticias.json', noticias, lambda xs, n: f'{len(xs)} acumuladas')
    etapa('eventos', 'eventos.json', eventos,
          lambda xs, n: f"{n} en el iCal · {len(xs)} desde {DESDE} · {sum(1 for e in xs if e['dia'] >= hoy)} por venir"
                        f" · último {max((e['dia'] for e in xs), default='—')}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
