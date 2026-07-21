#!/usr/bin/env python3
"""
Caudal · Fase 3 (piloto) — harvester de ÓRDENES DEL DÍA por comisión (agendamientos).

Fuente: API REST WordPress de la Cámara (curl con UA de navegador, sin el portal
JSF de la Imprenta). Cada evento tipo "Orden del día" trae un PDF digital de
descarga directa; dentro van los números de los proyectos agendados esa sesión.

Señal de bloqueo = cuántas veces se AGENDÓ un proyecto (aparece en el orden del
día) contra cuántos DEBATES EFECTIVOS tuvo (ya lo sabemos del dataset). Agendado
muchas veces + pocos/ningún debate = lo estaban dejando caer / bloqueando.

Uso:
  python3 tools/caudal/actas/harvest_ordenes.py primera --limit 150
  python3 tools/caudal/actas/harvest_ordenes.py primera            # todo (600)
"""
import subprocess, json, re, os, sys
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


def run(com, limit=None):
    com_id = COMISIONES[com]
    outdir = CACHE / 'ordenes' / com
    outdir.mkdir(parents=True, exist_ok=True)

    print(f'· órdenes del día de Comisión {com.title()} (id {com_id})…')
    eventos = fetch_eventos(com_id)
    if limit:
        eventos = eventos[:limit]
    print(f'  {len(eventos)} sesiones')
    gaceta_map = load_gaceta_map()

    agend = defaultdict(list)          # token → [{fecha, pos, n_dia}]
    titulos = {}                       # token → título (del propio orden del día)
    n_pdf, n_ok = 0, 0
    for i, ev in enumerate(eventos):
        url = pdf_url(ev)
        if not url:
            continue
        fecha = (ev.get('date') or '')[:10]
        fn = outdir / f"{ev['id']}.pdf"
        tf = outdir / f"{ev['id']}.txt"
        if tf.exists():
            txt = tf.read_text(encoding='utf-8')
        else:
            if not fn.exists() or fn.stat().st_size < 500:
                curl(url, str(fn))
            head = open(fn, 'rb').read(5) if fn.exists() else b''
            if head[:1] == b'<':       # llegó HTML (404/redirect), no PDF
                tf.write_text('', encoding='utf-8'); continue
            txt = extract_text(str(fn))
            tf.write_text(txt, encoding='utf-8')
            n_pdf += 1
        # el orden del día trae 2 listas: la AGENDA de debate (arriba) y el
        # "Anuncio de proyectos" (abajo, para la próxima sesión). Para la posición
        # real en la cola de debate, cortamos en el anuncio.
        body = re.split(r'anuncio\s+de\s+proyecto', txt, maxsplit=1, flags=re.I)[0]
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

    # índice de agendamientos por proyecto
    index = {}
    for tok, evs in agend.items():
        evs.sort(key=lambda e: e['fecha'])
        index[tok] = {
            'titulo': titulos.get(tok, ''), 'n': len(evs),
            'primera': evs[0]['fecha'], 'ultima': evs[-1]['fecha'],
            'fechas': [e['fecha'] for e in evs],
            'posiciones': [e['pos'] for e in evs],
        }
    rows = sorted(index.items(), key=lambda kv: -kv[1]['n'])

    out = {'comision': com, 'com_id': com_id, 'n_sesiones': len(eventos),
           'n_sesiones_con_proyectos': n_ok,
           'n_proyectos_agendados': len(index), 'agendamientos': index}
    outf = CACHE / f'agendamientos-{com}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n  {n_pdf} PDFs nuevos · {n_ok} sesiones con proyectos · '
          f'{len(index)} proyectos distintos · {len(titulos)} con título')
    print(f'  → {outf.relative_to(REPO)}')
    print('\n  Proyectos más AGENDADOS (nº veces en orden del día):')
    for tok, info in rows[:15]:
        print(f'  {info["n"]:>3}×  [{info["primera"]}→{info["ultima"]}]  {tok:>8}  {info["titulo"][:52]}')


if __name__ == '__main__':
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'primera'
    coms = list(COMISIONES) if arg == 'todas' else [arg]
    for c in coms:
        run(c, limit)
