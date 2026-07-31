#!/usr/bin/env python3
"""
Caudal · Fase 3 — harvester de ÓRDENES DEL DÍA de Cámara (agendamientos).

Fuente: API REST WordPress de la Cámara (curl con UA de navegador, sin el portal
JSF de la Imprenta). Cada evento tipo "Orden del día" trae un PDF digital de
descarga directa; dentro van los números de los proyectos agendados esa sesión.

Cubre 15 ámbitos: las 14 comisiones + la PLENARIA (taxonomía "Secretaría
General", id 253 — ahí publica la plenaria su orden del día).

Señal de bloqueo = cuántas veces se AGENDÓ un proyecto (aparece en el orden del
día) contra cuántos DEBATES EFECTIVOS tuvo (ya lo sabemos del dataset). Agendado
muchas veces + pocos/ningún debate = lo estaban dejando caer / bloqueando.

Uso:
  python3 tools/caudal/actas/harvest_ordenes.py primera --limit 150
  python3 tools/caudal/actas/harvest_ordenes.py primera            # todo (600)
  python3 tools/caudal/actas/harvest_ordenes.py plenaria           # solo plenaria
  python3 tools/caudal/actas/harvest_ordenes.py comisiones         # las 14
  python3 tools/caudal/actas/harvest_ordenes.py todas              # 14 + plenaria
  python3 tools/caudal/actas/harvest_ordenes.py todas --offline    # re-parsea el
                                                    # caché, sin tocar la red
Es incremental y resumible: los PDF/TXT se cachean por id de evento, así que una
corrida diaria solo baja las sesiones nuevas (por eso entra al run_diario.sh).
"""
import subprocess, json, re, os, sys, datetime
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
CACHE = SRC / 'actas'
DIST = SRC / 'dist'
API = 'https://www.camara.gov.co/wp-json/wp/v2'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
TIPO_ORDEN = 185
# las 14 comisiones reales de Cámara (7 constitucionales + 7 legales/especiales).
# term ids de la taxonomía comision_evento (excluye salones/Secretaría General).
COMISIONES = {
    'primera': 183, 'segunda': 184, 'tercera': 248, 'cuarta': 249,
    'quinta': 250, 'sexta': 251, 'septima': 252,
    'afro': 272, 'ordenamiento': 260, 'ddhh': 271, 'cuentas': 257,
    'etica': 258, 'mujer': 266, 'electoral': 269,
}
# La PLENARIA de Cámara publica su orden del día bajo la taxonomía "Secretaría
# General" (id 253) — no hay término "Plenaria" en comision_evento. Son ~654
# órdenes del día, otra cola de espera: proyectos que YA pasaron comisión y
# esperan segundo debate. Se cosecha igual pero se agrega aparte (no es una
# comisión y no debe entrar al ranking/estadística de comisiones).
PLENARIA = {'plenaria': 253}
TARGETS = {**COMISIONES, **PLENARIA}
PROJ_RE = re.compile(r'\b(\d{1,4})\s*/\s*(?:20)?(\d{2})\b')
PDF_RE = re.compile(r'(?:href|src)="([^"]+\.pdf)"', re.I)
# bloque del proyecto en el orden del día: número + año + título (entre comillas).
# Tolera 3 variantes reales del PDF (medidas jul-2026 sobre el caché local):
#   (a) año partido por el wrap de columna del PDF ("202 1" en vez de "2021")
#   (b) doble numeración bicameral ("No. 102 de 2025 Cámara, 083 de 2025 Senado")
#   (c) cláusula "Acumulado con el Proyecto de Ley No. NNN de AAAA Cámara" antes de la cita
PROJ_BLOCK_RE = re.compile(
    r'Proyecto de (?:Ley|Acto Legislativo)(?:\s+Org[aá]nica)?[^0-9"“]{0,30}'
    r'(\d{1,4})\s*de\s*(2\s?0\s?\d\s?\d)\s*(?:C[aá]mara|Senado)?'
    r'(?:\s*(?:,|[-–—]|:)?\s*(?:Acumulado con el Proyecto de (?:Ley|Acto Legislativo)[^0-9"“]{0,25})?'
    r'\d{1,4}\s*de\s*(?:20)?\s?\d\s?\d\s*(?:C[aá]mara|Senado)?)?'
    r'[^"“]{0,30}["“](.+?)["”]', re.I | re.S)
# variante SIN número/título inline (algunas comisiones desde ~2024): el orden
# del día solo cita la Gaceta de radicación — "Proyecto de Ley: Gaceta del
# Congreso 2048 de 2025". Se resuelve por Gaceta contra nuestro propio dataset
# (ya tenemos el número Cámara/Senado y el título reales, no hace falta parsear
# el PDF para eso) vía load_gaceta_map().
GACETA_REF_RE = re.compile(
    r'Proyecto de (?:Ley|Acto Legislativo)\s*:\s*Gaceta\s*(?:del\s+Congreso|No\.?)?'
    r'\s*(\d{1,4})\s*de\s*(20\d{2})', re.I)
ANUNCIO_RE = re.compile(r'anuncio\s+de\s+proyecto\w*', re.I)
# fecha de la SESIÓN (la agenda es para un día distinto al de publicación del
# evento): plenaria la pone entre paréntesis "(17/06/2026)", las comisiones en
# texto "Orden del día – Junio 17/2026 – …".
FECHA_SLASH_RE = re.compile(r'\((\d{1,2})/(\d{1,2})/(20\d{2})\)')
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
         'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
         'noviembre': 11, 'diciembre': 12}
FECHA_MES_RE = re.compile(r'(' + '|'.join(MESES) + r')\s*(\d{1,2})\s*/\s*(20\d{2})', re.I)


def cut_anuncio(txt):
    """Recorta el 'Anuncio de proyectos' (los que se anuncian para la PRÓXIMA
    sesión) para que la posición medida sea la de la cola de debate de HOY.

    En las comisiones ese encabezado va al final, después de la agenda; en la
    plenaria es la sección III del índice, ARRIBA de las secciones que traen los
    proyectos (informes de conciliación, segundo debate). Por eso no se corta en
    la primera aparición: se corta en la primera que quede DESPUÉS del primer
    proyecto citado. Si el encabezado va antes de todo proyecto, no recorta nada.
    """
    prim = None
    for rx in (PROJ_BLOCK_RE, GACETA_REF_RE):
        m = rx.search(txt)
        if m and (prim is None or m.start() < prim):
            prim = m.start()
    for m in ANUNCIO_RE.finditer(txt):
        if prim is None or m.start() > prim:
            return txt[:m.start()]
    return txt


def fecha_sesion(titulo, pub):
    """Fecha de la SESIÓN desde el título del evento; cae a la de publicación.

    La agenda se publica días antes de la sesión (plenaria: casi siempre 1 día;
    comisión: hasta una semana), así que la fecha del título es la buena. Solo
    ~8% de los títulos de comisión la traen (formato nuevo, 2026) contra casi
    todos los de plenaria; el resto se queda con la de publicación.
    Se acepta únicamente si cae en una ventana sana alrededor de la publicación
    — la Cámara reusa títulos con el año viejo (visto: publicado 2026-03-13 con
    título "Marzo 18/2025"), y ese ruido movería la sesión un año entero.
    """
    t = re.sub(r'<[^>]+>', ' ', titulo or '')
    cand = None
    m = FECHA_SLASH_RE.search(t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= d <= 31 and 1 <= mo <= 12:
            cand = f'{y}-{mo:02d}-{d:02d}'
    if cand is None:
        m = FECHA_MES_RE.search(t)
        if m:
            mo, d, y = MESES[m.group(1).lower()], int(m.group(2)), m.group(3)
            if 1 <= d <= 31:
                cand = f'{y}-{mo:02d}-{d:02d}'
    if cand and pub:
        try:
            dif = (datetime.date.fromisoformat(cand) - datetime.date.fromisoformat(pub)).days
        except ValueError:
            return pub, False
        if -1 <= dif <= 14:
            return cand, True
    return pub, False


def curl(url, out=None):
    a = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', '60', url]
    if out:
        a += ['-o', out]
    return subprocess.run(a, capture_output=True).stdout


def fetch_eventos(com_id, tipo=TIPO_ORDEN):
    """Todos los eventos (paginado) de una comisión y tipo."""
    out, page = [], 1
    while True:
        raw = curl(f'{API}/evento?comision_evento={com_id}&evento_tipo={tipo}'
                   f'&per_page=100&page={page}&_fields=id,date,slug,title,content')
        try:
            batch = json.loads(raw)
        except Exception:
            break
        if not isinstance(batch, list) or not batch:
            break
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def eventos_de(name, offline=False):
    """Eventos del ámbito, cacheados en ordenes/{name}/_eventos.json. Con
    --offline se lee solo el caché (re-parseo sin red, para regresión)."""
    cf = CACHE / 'ordenes' / name / '_eventos.json'
    if offline:
        if not cf.exists():
            print(f'  ! sin caché de eventos para {name} (corre online una vez)')
            return []
        return json.load(open(cf, encoding='utf-8'))
    evs = fetch_eventos(TARGETS[name])
    if evs:                              # solo pisa el caché si la red respondió
        cf.parent.mkdir(parents=True, exist_ok=True)
        json.dump(evs, open(cf, 'w', encoding='utf-8'), ensure_ascii=False)
    elif cf.exists():
        print(f'  ! la API no respondió; sigo con el caché de {name}')
        return json.load(open(cf, encoding='utf-8'))
    return evs


def pdf_url(ev):
    m = PDF_RE.search((ev.get('content') or {}).get('rendered', '') or '')
    return m.group(1) if m else None


def norm(n, y):
    return f'{int(n)}/{y}'


def extract_text(path):
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        return ' '.join((p.extract_text() or '') for p in r.pages)
    except Exception as e:
        return f'[pdf-err {str(e)[:40]}]'


def load_numero_camara_map():
    """token 'NNN/YY' (número Cámara) → registro del dataset (para cruzar)."""
    p = DIST / 'proyectos.jsonl'
    if not p.exists():
        return {}
    mp = {}
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        nc = (r.get('numero_camara') or '').strip()
        m = PROJ_RE.search(nc)
        if m:
            mp[norm(m.group(1), m.group(2))] = r
    return mp


def load_gaceta_map():
    """gaceta 'NNNN/AAAA' → (tok 'NNN/YY' número Cámara, título) — resuelve los
    agendamientos formato GACETA_REF_RE (sin número/título inline) contra
    nuestro propio dataset en vez de parsear el PDF."""
    p = DIST / 'proyectos.jsonl'
    if not p.exists():
        return {}
    mp = {}
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        nc = (r.get('numero_camara') or '').strip()
        m = PROJ_RE.search(nc)
        if not m:
            continue
        tok = norm(m.group(1), m.group(2))
        for g in r.get('gacetas', []):
            gk = g.get('gaceta')
            if gk and gk not in mp:
                mp[gk] = (tok, r.get('titulo', ''))
    return mp


_GMAP = None
_NMAP = None


def gaceta_map_cached():
    """proyectos.jsonl son 28 MB: se lee una vez por corrida, no una por ámbito."""
    global _GMAP
    if _GMAP is None:
        _GMAP = load_gaceta_map()
    return _GMAP


def num_map_cached():
    global _NMAP
    if _NMAP is None:
        _NMAP = load_numero_camara_map()
    return _NMAP


def run(com, limit=None, offline=False):
    com_id = TARGETS[com]
    outdir = CACHE / 'ordenes' / com
    outdir.mkdir(parents=True, exist_ok=True)

    rot = 'Plenaria (Secretaría General)' if com == 'plenaria' else f'Comisión {com.title()}'
    print(f'· órdenes del día de {rot} (id {com_id}){" · offline" if offline else ""}…')
    eventos = eventos_de(com, offline=offline)
    if limit:
        eventos = eventos[:limit]
    print(f'  {len(eventos)} sesiones')
    gaceta_map = gaceta_map_cached()

    agend = defaultdict(list)          # token → [{fecha, pos, n_dia}]
    titulos = {}                       # token → título (del propio orden del día)
    n_pdf, n_ok, n_fs = 0, 0, 0
    for i, ev in enumerate(eventos):
        url = pdf_url(ev)
        if not url:
            continue
        pub = (ev.get('date') or '')[:10]
        fecha, es_sesion = fecha_sesion((ev.get('title') or {}).get('rendered', ''), pub)
        n_fs += es_sesion
        fn = outdir / f"{ev['id']}.pdf"
        tf = outdir / f"{ev['id']}.txt"
        if tf.exists():
            txt = tf.read_text(encoding='utf-8')
        elif offline:
            continue                   # sin caché de texto y sin red: se salta
        else:
            if not fn.exists() or fn.stat().st_size < 500:
                curl(url, str(fn))
            head = open(fn, 'rb').read(5) if fn.exists() else b''
            if head[:1] == b'<':       # llegó HTML (404/redirect), no PDF
                tf.write_text('', encoding='utf-8'); continue
            txt = extract_text(str(fn))
            tf.write_text(txt, encoding='utf-8')
            n_pdf += 1
        # el orden del día trae 2 listas: la AGENDA de debate y el "Anuncio de
        # proyectos" (los de la próxima sesión). Para que la posición sea la de la
        # cola de debate, se recorta el anuncio (ver cut_anuncio: en comisión va al
        # final, en plenaria es la sección III del índice).
        body = cut_anuncio(txt)
        # lista ordenada de proyectos únicos (por 1ª aparición) → posición
        orden, seen = [], set()
        for m in PROJ_BLOCK_RE.finditer(body):
            anio = m.group(2).replace(' ', '')   # año puede venir partido por el wrap del PDF ("202 1")
            tok = norm(m.group(1), anio[-2:])
            t = re.sub(r'\s+', ' ', m.group(3)).strip(' "“”«»')
            if 12 <= len(t) <= 180 and tok not in titulos:
                titulos[tok] = t
            if tok not in seen:
                seen.add(tok); orden.append(tok)
        # variante sin número/título inline — resuelve por Gaceta contra el dataset
        for m in GACETA_REF_RE.finditer(body):
            gk = f'{int(m.group(1))}/{m.group(2)}'
            hit = gaceta_map.get(gk)
            if not hit:
                continue
            tok, tit = hit
            if tit and tok not in titulos:
                titulos[tok] = tit
            if tok not in seen:
                seen.add(tok); orden.append(tok)
        if orden:
            n_ok += 1
        n_dia = len(orden)
        for pos, tok in enumerate(orden, 1):
            agend[tok].append({'fecha': fecha, 'pos': pos, 'n_dia': n_dia})
        if (i + 1) % 50 == 0:
            print(f'  …{i + 1}/{len(eventos)}')

    # índice de agendamientos por proyecto. Una SESIÓN = un agendamiento: la
    # Cámara republica el orden del día corregido para el mismo día (…-2.pdf),
    # así que se colapsa por fecha de sesión y se guarda la mejor posición.
    index = {}
    for tok, evs in agend.items():
        por_fecha = {}
        for e in evs:
            prev = por_fecha.get(e['fecha'])
            if prev is None or e['pos'] < prev['pos']:
                por_fecha[e['fecha']] = e
        evs = sorted(por_fecha.values(), key=lambda e: e['fecha'])
        index[tok] = {
            'titulo': titulos.get(tok, ''), 'n': len(evs),
            'primera': evs[0]['fecha'], 'ultima': evs[-1]['fecha'],
            'fechas': [e['fecha'] for e in evs],
            'posiciones': [e['pos'] for e in evs],
        }
    rows = sorted(index.items(), key=lambda kv: -kv[1]['n'])

    # Relleno de títulos desde el propio dataset — mismo patrón que
    # harvest_ordenes_senado.py: ~29%/40% de las citas en el orden del día no
    # traen título usable en el PDF (número solo, o título sin comillas y solo
    # el apodo entre comillas). Como ya tenemos numero_camara→titulo en
    # proyectos.jsonl, se completa de ahí en vez de dejar la fila en blanco en
    # la UI. Solo rellena lo que falta; NO pisa el título leído del documento.
    nmap = num_map_cached()
    n_titulo_dataset = 0
    for tok in index:
        if not (index[tok].get('titulo') or '').strip():
            r = nmap.get(tok)
            t = (r.get('titulo') or '').strip() if r else ''
            if t:
                index[tok]['titulo'] = t
                n_titulo_dataset += 1

    out = {'comision': com, 'com_id': com_id, 'ambito': 'plenaria' if com == 'plenaria' else 'comision',
           'n_sesiones': len(eventos), 'n_sesiones_con_proyectos': n_ok,
           'n_con_fecha_sesion': n_fs, 'n_titulo_desde_dataset': n_titulo_dataset,
           'n_proyectos_agendados': len(index), 'agendamientos': index}
    outf = CACHE / f'agendamientos-{com}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    n_con_titulo = sum(1 for i in index.values() if (i.get('titulo') or '').strip())
    print(f'\n  {n_pdf} PDFs nuevos · {n_ok} sesiones con proyectos · '
          f'{len(index)} proyectos distintos · {n_con_titulo} con título '
          f'(+{n_titulo_dataset} rellenados desde el dataset)')
    print(f'  → {outf.relative_to(REPO)}')
    print('\n  Proyectos más AGENDADOS (nº veces en orden del día):')
    for tok, info in rows[:15]:
        print(f'  {info["n"]:>3}×  [{info["primera"]}→{info["ultima"]}]  {tok:>8}  {info["titulo"][:52]}')


if __name__ == '__main__':
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    offline = '--offline' in sys.argv
    arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'primera'
    if arg == 'todas':
        coms = list(TARGETS)
    elif arg == 'comisiones':
        coms = list(COMISIONES)
    else:
        coms = [arg]
    desconocidas = [c for c in coms if c not in TARGETS]
    if desconocidas:
        sys.exit(f'ámbito desconocido: {", ".join(desconocidas)}\n'
                 f'válidos: {", ".join(TARGETS)} · todas · comisiones')
    for c in coms:
        run(c, limit, offline=offline)
