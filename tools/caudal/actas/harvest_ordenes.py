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
COMISIONES = {'primera': 183, 'segunda': 184, 'tercera': 248, 'cuarta': 249,
              'quinta': 250, 'sexta': 251, 'septima': 252, 'mujer': 266}
PROJ_RE = re.compile(r'\b(\d{1,4})\s*/\s*(?:20)?(\d{2})\b')
PDF_RE = re.compile(r'(?:href|src)="([^"]+\.pdf)"', re.I)
# bloque del proyecto en el orden del día: número + año + título (entre comillas)
PROJ_BLOCK_RE = re.compile(
    r'Proyecto de (?:Ley|Acto Legislativo)(?:\s+Org[aá]nica)?[^0-9"“]{0,25}'
    r'(\d{1,4})\s*de\s*(20\d{2})[^"“]{0,18}["“](.+?)["”]', re.I | re.S)


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


def main():
    com = sys.argv[1] if len(sys.argv) > 1 else 'primera'
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    com_id = COMISIONES[com]
    outdir = CACHE / 'ordenes' / com
    outdir.mkdir(parents=True, exist_ok=True)

    print(f'· órdenes del día de Comisión {com.title()} (id {com_id})…')
    eventos = fetch_eventos(com_id)
    if limit:
        eventos = eventos[:limit]
    print(f'  {len(eventos)} sesiones')

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
            tok = norm(m.group(1), m.group(2)[-2:])
            t = re.sub(r'\s+', ' ', m.group(3)).strip(' "“”«»')
            if 12 <= len(t) <= 180 and tok not in titulos:
                titulos[tok] = t
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
    main()
