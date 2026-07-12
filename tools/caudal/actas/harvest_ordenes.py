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
# bloque completo del proyecto en el orden del día: número + año + título
PROJ_TITLE_RE = re.compile(
    r'Proyecto de (?:Ley|Acto Legislativo)\s*(?:Org[áa]nica\s*)?(?:No\.?|N[°º]\.?)?\s*'
    r'(\d{1,4})\s*de\s*(20\d{2})\s*C[áa]mara\s*[“"«]?\s*(.+?)\s*[”"»]?\s*'
    r'(?:Autor|Ponente|Comisi|Proyecto de)', re.I | re.S)


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

    agend = defaultdict(list)          # token proyecto → [fechas de sesión]
    titulos = {}                       # token → título (del propio orden del día)
    n_pdf = 0
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
        # un mismo proyecto puede repetirse en la misma sesión → set por sesión
        seen = set()
        for m in PROJ_RE.finditer(txt):
            tok = norm(m.group(1), m.group(2))
            if tok not in seen:
                agend[tok].append(fecha); seen.add(tok)
        for m in PROJ_TITLE_RE.finditer(txt):
            tok = norm(m.group(1), m.group(2)[-2:])
            t = re.sub(r'\s+', ' ', m.group(3)).strip(' "“”«»')
            if tok not in titulos and 12 <= len(t) <= 160:
                titulos[tok] = t
        if (i + 1) % 50 == 0:
            print(f'  …{i + 1}/{len(eventos)}')

    # índice de agendamientos
    index = {tok: {'n': len(set(f)), 'fechas': sorted(set(f))}
             for tok, f in agend.items()}
    # cruce con debates efectivos del dataset
    camara = load_numero_camara_map()
    ETAPA = ['presentado', '1er debate Senado', '2º debate Senado',
             '1er debate Cámara', '2º debate Cámara', 'ley']
    rows = []
    for tok, info in index.items():
        r = camara.get(tok)
        titulo = (r.get('titulo') if r else None) or titulos.get(tok) or '(sin título)'
        rows.append({
            'num_camara': tok, 'agendado': info['n'],
            'primera': info['fechas'][0], 'ultima': info['fechas'][-1],
            'titulo': titulo[:75],
            'etapa_max': (r or {}).get('etapa_max'),
            'etapa_txt': ETAPA[r['etapa_max']] if r and isinstance(r.get('etapa_max'), int) else '—',
            'resultado': (r or {}).get('resultado') if r else None,
            'en_dataset': bool(r),
        })
    rows.sort(key=lambda x: -x['agendado'])

    out = {'comision': com, 'com_id': com_id, 'n_sesiones': len(eventos),
           'n_proyectos_agendados': len(index), 'agendamientos': index,
           'cruce': rows}
    outf = CACHE / f'agendamientos-{com}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n  {n_pdf} PDFs nuevos · {len(index)} proyectos distintos agendados · {len(titulos)} con título')
    print(f'  → {outf.relative_to(REPO)}')
    print('\n  BLOQUEO · proyectos más AGENDADOS en Comisión Primera:')
    for r in rows[:15]:
        print(f'  {r["agendado"]:>3}×  {r["num_camara"]:>9}  {r["titulo"][:66]}')


if __name__ == '__main__':
    main()
