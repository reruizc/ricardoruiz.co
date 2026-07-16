#!/usr/bin/env python3
"""
Caudal · Fase 3 — parser de VOTO NOMINAL desde las actas de plenaria de Cámara.

Lee lo que bajó harvest_actas_plenaria_camara.py (ZIP/PDF por acta) y extrae,
por votación, el resultado nominal (congresista → Sí/No/Abstención) desde el
texto NATIVO del PDF (sin OCR — pypdf).

Tres formatos con texto extraíble (auto-detectados por CONTENIDO, no por
fecha — el mismo tipo de documento aparece a veces como texto nativo y a
veces como imagen escaneada en años vecinos, sin un corte limpio):

  · consolidado (~oct-2022 en adelante): 1 PDF "Registro ... Asistencia y
    Votación Electrónica" con TODAS las votaciones de la sesión, bloques
    "VOTACION N" + tabla nominal con nombre completo (Apellidos Nombres).
    Alta confianza.

  · fragmentado_electronico (~ago-2021 a ~sep-2022): 1 PDF por votación.
    Trae DOS secciones — (a) voto ELECTRÓNICO: filas identificadas por email
    (nombre.apellido@camara.gov.co) con Sí/No/Abstención como texto explícito
    → se parsea; (b) voto MANUAL (ver abajo, mismo formato manual_tabla).

  · manual_tabla (intermitente ~2011-2020, y también la porción manual de
    fragmentado_electronico): "REGISTRO MANUAL PARA VOTACIONES", tabla
    No./Nombre/Circunscripción/Partido/SI/NO con una "X" bajo la columna que
    corresponde — POSICIÓN espacial, no texto explícito. pypdf pierde esa
    posición (linealiza el texto); `pdfplumber.extract_table()` sí la
    resuelve reconstruyendo filas/columnas por coordenadas. Confianza media.

Todo lo demás (imágenes escaneadas sin texto extraíble, y los ZIP/RAR/DOCX
de 2011-2014 en formatos no soportados): requiere OCR, no se procesa aquí.

Uso:
  python3 tools/caudal/actas/parse_votaciones_camara.py            # todas las actas descargadas
  python3 tools/caudal/actas/parse_votaciones_camara.py --limit 20 # smoke test
"""
import json, re, sys, zipfile, io, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-camara'
RAW_DIR = SRC / 'raw'
PARSED_DIR = SRC / 'parsed'
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
from normalize_autores import canon_key  # noqa: E402

# --- regex ------------------------------------------------------------------
VOTACION_HDR_RE = re.compile(r'VOTACION\s+(\d+)')
NOMBRE_VOT_RE = re.compile(r'Nombre de la votaci[oó]n:\s*(.+?)\s*(?:\n|Inicio de la votaci[oó]n)', re.I | re.S)
INICIO_RE = re.compile(r'Inicio de la votaci[oó]n:\s*([\d/: apm.]+)', re.I)
RESUMEN_RE = re.compile(r'\b(S[ií]|No|Abstenci[oó]n)\s+(\d+)\s+([\d,]+)%')
NOMINAL_RE = re.compile(r'(\d{1,3})\.\s*(.+?)\s+(S[ií]|No|Abstenci[oó]n)\b', re.S)
EMAIL_ROW_RE = re.compile(
    r'(\d{1,3})\.\s*[\d]{1,2}\s+\w+\s+\d{4}[\d: ]*'
    r'([a-z0-9._-]+)@camara\.gov\.co'
    r'(.+?)\s+(SI|S[ÍI]|NO|ABSTENCI[OÓ]N)\b', re.I | re.S)
# matchea "446/25" (numero_camara del dataset) y "PL.416/24" / "PL.166/23C"
# (nombre de la votación). El cierre es `(?!\d)` en vez de `\b` a propósito: los
# nombres traen sufijo de cámara pegado ("166/23C", "115/17S") y un `\b` final
# fallaría contra la letra ("23C" no tiene boundary) → se perdía casi todo el
# linking. Con lookahead de dígito, "23C" matchea (C no es dígito).
PROJ_RE = re.compile(r'\b(\d{1,4})\s*/\s*(?:20)?(\d{2})(?!\d)')
UUID_STRIP_RE = re.compile(r'^\[[0-9a-f-]{20,40}\]\s*', re.M)
MANUAL_TABLA_RE = re.compile(r'REGISTRO\s+MANUAL\s+PARA\s+VOTACIONES', re.I)
TEMA_RE = re.compile(r'TEMA\s+A\s+VOTAR:\s*(.+?)(?:\n|SESI[OÓ]N\s+PLENARIA)', re.I | re.S)

RESP_NORM = {
    'SI': 'Si', 'SÍ': 'Si', 'SI.': 'Si',
    'NO': 'No',
    'ABSTENCION': 'Abstencion', 'ABSTENCIÓN': 'Abstencion',
}


def _norm_resp(s):
    k = unicodedata.normalize('NFD', s.upper()).encode('ascii', 'ignore').decode()
    return RESP_NORM.get(k, s.strip().title())


def _norm_proj(n, y):
    return f'{int(n)}/{y[-2:]}'   # año a 2 dígitos ("2022"→"22") para casar el índice


# --- extracción de texto -----------------------------------------------------
def _pdf_text(data):
    import pypdf
    try:
        r = pypdf.PdfReader(io.BytesIO(data))
        parts = []
        for p in r.pages:
            try:
                parts.append(p.extract_text() or '')
            except Exception:
                parts.append('')
        return UUID_STRIP_RE.sub('', '\n'.join(parts))
    except Exception:
        return ''


def _iter_pdfs_in_file(path):
    """Devuelve [(nombre, texto, bytes), ...] — de un .zip (todos los PDF dentro)
    o de un .pdf suelto. Se guardan los bytes crudos porque el formato
    `manual_tabla` necesita re-abrir el PDF con pdfplumber (pypdf no resuelve
    columnas espaciales)."""
    out = []
    if path.suffix.lower() == '.zip':
        try:
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.lower().endswith('.pdf') and not name.startswith('__MACOSX'):
                        try:
                            data = z.read(name)
                        except Exception:
                            continue
                        out.append((name, _pdf_text(data), data))
        except zipfile.BadZipFile:
            return []
    elif path.suffix.lower() == '.pdf':
        data = path.read_bytes()
        out.append((path.name, _pdf_text(data), data))
    return out


# --- formato consolidado -----------------------------------------------------
def parse_consolidado(text):
    """→ [{numero, nombre, inicio, resumen:{Si,No,Abstencion}, votos:[(nombre,resp)]}]"""
    marks = list(VOTACION_HDR_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        chunk = text[start:end]
        nm = NOMBRE_VOT_RE.search(chunk)
        im = INICIO_RE.search(chunk)
        resumen = {_norm_resp(r): int(c) for r, c, _ in RESUMEN_RE.findall(chunk)}
        votos = []
        for numstr, nombre, resp in NOMINAL_RE.findall(chunk):
            nombre = re.sub(r'\s+', ' ', nombre).strip(' .')
            if len(nombre) < 5 or len(nombre) > 80:
                continue
            votos.append((nombre, _norm_resp(resp)))
        out.append({
            'numero': int(m.group(1)),
            'nombre': re.sub(r'\s+', ' ', nm.group(1)).strip() if nm else '',
            'inicio': im.group(1).strip() if im else '',
            'resumen': resumen,
            'votos': votos,
            'fuente': 'consolidado',
        })
    return out


# --- formato fragmentado (1 pdf = 1 votación, porción electrónica) ----------
def parse_fragmentado_electronico(text, nombre_archivo):
    votos, resp_set = [], set()
    for numstr, email_local, _mid, resp in EMAIL_ROW_RE.findall(text):
        votos.append((email_local.lower(), _norm_resp(resp)))
        resp_set.add(_norm_resp(resp))
    if not votos:
        return None
    resumen = {}
    for r, _ in [(v[1], None) for v in votos]:
        resumen[r] = resumen.get(r, 0) + 1
    return {
        'numero': None,
        'nombre': re.sub(r'\.pdf$', '', nombre_archivo, flags=re.I),
        'inicio': '',
        'resumen': resumen,
        'votos': votos,
        'fuente': 'fragmentado_electronico',
        'votos_son_email': True,
    }


def parse_manual_tabla(data, text):
    """Formato viejo (~2011-2020, intermitente): 'REGISTRO MANUAL PARA
    VOTACIONES', tabla No./Nombre/Circunscripción/Partido/SI/NO con una "X"
    posicional bajo la columna que corresponde. pypdf no resuelve la
    columna (texto plano pierde la posición) → pdfplumber.extract_table()
    sí, porque reconstruye filas/columnas por coordenadas."""
    import pdfplumber
    tm = TEMA_RE.search(text)
    tema = re.sub(r'\s+', ' ', tm.group(1)).strip(' :') if tm else ''
    votos = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                tbl = page.extract_table()
                if not tbl:
                    continue
                header_row = None
                for row in tbl:
                    cells = [(c or '').strip() for c in row]
                    if not header_row and 'NOMBRE' in [c.upper() for c in cells]:
                        header_row = cells
                        continue
                    if not header_row:
                        continue
                    if len(cells) < 3:
                        continue
                    nombre = cells[1] if len(cells) > 1 else ''
                    nombre = re.sub(r'\s+', ' ', nombre).strip()
                    if len(nombre) < 5:
                        continue
                    # las 2 últimas columnas no vacías son SI/NO (a veces hay
                    # una col extra None por celdas fusionadas del pdf)
                    tail = [c.strip().upper() for c in cells[-2:]]
                    if 'X' in tail:
                        voto = 'Si' if tail[0] == 'X' else 'No'
                        votos.append((nombre, voto))
    except Exception:
        return None
    if not votos:
        return None
    resumen = {}
    for _, v in votos:
        resumen[v] = resumen.get(v, 0) + 1
    return {
        'numero': None, 'nombre': tema or 'REGISTRO MANUAL PARA VOTACIONES',
        'inicio': '', 'resumen': resumen, 'votos': votos, 'fuente': 'manual_tabla',
    }


def detect_and_parse(nombre_pdf, text, data=None):
    if not text or len(text) < 80:
        return None, 'sin-texto'
    if VOTACION_HDR_RE.search(text):
        vs = parse_consolidado(text)
        return vs, 'consolidado' if vs else 'consolidado-vacio'
    if '@camara.gov.co' in text and re.search(r'Nombre\s+Votaci[oó]n', text, re.I):
        v = parse_fragmentado_electronico(text, nombre_pdf)
        return ([v] if v else []), ('fragmentado_electronico' if v else 'fragmentado-sin-filas')
    if MANUAL_TABLA_RE.search(text) and data is not None:
        v = parse_manual_tabla(data, text)
        return ([v] if v else []), ('manual_tabla' if v else 'manual_tabla-sin-filas')
    return None, 'formato-desconocido'


# --- roster: congresista → partido (matching por subconjunto de tokens) -----
def load_roster():
    d = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))
    roster = d['roster']
    toks = {k: frozenset(k.split()) for k in roster}
    idx = {}
    for k, ts in toks.items():
        for t in ts:
            idx.setdefault(t, set()).add(k)
    return roster, toks, idx


def match_roster(nombre_tokens_key, roster, roster_toks, tok_idx):
    if nombre_tokens_key in roster:
        return roster[nombre_tokens_key]['partido_principal'], nombre_tokens_key, 'exacto'
    atoks = frozenset(nombre_tokens_key.split())
    if len(atoks) < 2:
        return None, None, None
    cand = None
    for t in atoks:
        s = tok_idx.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    supersets = [k for k in (cand or ()) if atoks <= roster_toks[k]]
    if not supersets:
        return None, None, None
    if len(supersets) == 1:
        k = supersets[0]
        return roster[k]['partido_principal'], k, 'subset'
    # ambiguo entre varios roster keys — solo aceptar si todos son la misma persona en la práctica
    partidos = {roster[k]['partido_principal'] for k in supersets}
    if len(partidos) == 1:
        best = max(supersets, key=lambda k: roster[k]['anio_ultimo'])
        return roster[best]['partido_principal'], best, 'subset-ambiguo'
    return None, None, 'ambiguo'


def match_email(email_local, roster, roster_toks, tok_idx):
    """'norma.hurtado' -> tokens {'NORMA','HURTADO'} -> subset match."""
    parts = [p for p in re.split(r'[._-]+', email_local) if p]
    if len(parts) < 2:
        return None, None, None
    atoks = frozenset(canon_key(' '.join(parts)).split())
    cand = None
    for t in atoks:
        s = tok_idx.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    supersets = [k for k in (cand or ()) if atoks <= roster_toks[k]]
    if len(supersets) == 1:
        k = supersets[0]
        return roster[k]['partido_principal'], k, 'email-subset'
    if len(supersets) > 1:
        partidos = {roster[k]['partido_principal'] for k in supersets}
        if len(partidos) == 1:
            best = max(supersets, key=lambda k: roster[k]['anio_ultimo'])
            return roster[best]['partido_principal'], best, 'email-subset-ambiguo'
    return None, None, None


# --- vincular votación → numero_camara del dataset --------------------------
def load_numero_camara_map():
    p = DIST / 'proyectos.jsonl'
    mp = {}
    if not p.exists():
        return mp
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        nc = (r.get('numero_camara') or '').strip()
        m = PROJ_RE.search(nc)
        if m:
            mp[_norm_proj(m.group(1), m.group(2))] = {
                'id': r.get('id'), 'titulo': r.get('titulo'), 'numero_camara': nc,
                'numero_senado': r.get('numero_senado'),
            }
    return mp


# variante con guion y año de 4 dígitos ("P.L.118-2022"): el guion solo se
# acepta con año 20YY completo, para NO falsear con listas de artículos ("24-25")
PROJ_DASH_RE = re.compile(r'\b(\d{1,4})\s*-\s*(20\d{2})(?!\d)')


def link_proyecto(nombre_votacion, proj_map):
    nombre = nombre_votacion or ''
    m = PROJ_RE.search(nombre)
    if not m:
        m = PROJ_DASH_RE.search(nombre)   # formato "118-2022"
    if not m:
        return None
    tok = _norm_proj(m.group(1), m.group(2))
    return proj_map.get(tok)


# --- run ----------------------------------------------------------------------
def run(limit=None):
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    items = json.load(open(SRC / 'index' / 'indice-completo.json', encoding='utf-8'))
    if limit:
        items = items[:limit]
    roster, roster_toks, tok_idx = load_roster()
    proj_map = load_numero_camara_map()

    stats = {}
    n_votaciones, n_votos, n_matched = 0, 0, 0
    consolidated_rows = []   # para dist/votaciones-camara-nominal.jsonl

    for i, it in enumerate(items):
        aid = it['id']
        outf = PARSED_DIR / f'{aid}.json'
        raws = list(RAW_DIR.glob(f'{aid}.*'))
        if not raws:
            stats['sin-archivo'] = stats.get('sin-archivo', 0) + 1
            continue
        raw = raws[0]
        if raw.suffix.lower() not in ('.zip', '.pdf'):
            stats[f'formato-no-soportado-{raw.suffix}'] = stats.get(f'formato-no-soportado-{raw.suffix}', 0) + 1
            continue

        pdfs = _iter_pdfs_in_file(raw)
        if not pdfs:
            stats['zip-vacio-o-corrupto'] = stats.get('zip-vacio-o-corrupto', 0) + 1
            continue

        acta_votaciones, mejor_status = [], 'sin-texto'
        for nombre_pdf, text, data in pdfs:
            vs, status = detect_and_parse(nombre_pdf, text, data)
            if vs:
                acta_votaciones += vs
                mejor_status = status if mejor_status == 'sin-texto' else mejor_status
        status_final = 'ok' if acta_votaciones else mejor_status
        stats[status_final] = stats.get(status_final, 0) + 1

        if not acta_votaciones:
            continue

        acta_out = {
            'acta_id': aid, 'numero_acta': it.get('numero'), 'fecha_iso': it.get('fecha_iso'),
            'gaceta_numero': it.get('gaceta_numero'), 'gaceta_anio': it.get('gaceta_anio'),
            'votaciones': [],
        }
        for v in acta_votaciones:
            n_votaciones += 1
            proyecto = link_proyecto(v['nombre'], proj_map)
            votos_out = []
            for nombre_o_email, resp in v['votos']:
                n_votos += 1
                if v.get('votos_son_email'):
                    partido, rkey, via = match_email(nombre_o_email, roster, roster_toks, tok_idx)
                    votos_out.append({'email': nombre_o_email, 'respuesta': resp,
                                       'partido': partido, 'roster_key': rkey, 'match_via': via})
                else:
                    key = canon_key(nombre_o_email)
                    partido, rkey, via = match_roster(key, roster, roster_toks, tok_idx)
                    votos_out.append({'congresista': nombre_o_email, 'respuesta': resp,
                                       'partido': partido, 'roster_key': rkey, 'match_via': via})
                if partido:
                    n_matched += 1
            acta_out['votaciones'].append({
                'numero': v['numero'], 'nombre_votacion': v['nombre'], 'inicio': v['inicio'],
                'resumen': v['resumen'], 'fuente': v['fuente'],
                'proyecto_numero_camara': proyecto['numero_camara'] if proyecto else None,
                'proyecto_id': proyecto['id'] if proyecto else None,
                'proyecto_titulo': proyecto['titulo'] if proyecto else None,
                'votos': votos_out,
            })
            for vo in votos_out:
                consolidated_rows.append({
                    'acta_id': aid, 'fecha': it.get('fecha_iso'), 'votacion_numero': v['numero'],
                    'votacion_nombre': v['nombre'], 'proyecto_numero_camara': proyecto['numero_camara'] if proyecto else None,
                    **{k: vv for k, vv in vo.items()},
                })
        json.dump(acta_out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)

        if (i + 1) % 100 == 0:
            print(f'  …{i + 1}/{len(items)}  {stats}')

    DIST.mkdir(parents=True, exist_ok=True)
    with open(DIST / 'votaciones-camara-nominal.jsonl', 'w', encoding='utf-8') as f:
        for row in consolidated_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    summary = {
        'n_actas_procesadas': len(items), 'n_actas_con_voto_nominal': stats.get('ok', 0),
        'stats_por_status': stats, 'n_votaciones': n_votaciones, 'n_votos': n_votos,
        'n_votos_con_partido': n_matched,
        'pct_votos_con_partido': round(100 * n_matched / n_votos, 1) if n_votos else 0,
    }
    json.dump(summary, open(DIST / 'votaciones-camara-stats.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('\n=== resumen ===')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f'\n→ {DIST / "votaciones-camara-nominal.jsonl"}')
    print(f'→ {DIST / "votaciones-camara-stats.json"}')


if __name__ == '__main__':
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    run(limit=limit)
