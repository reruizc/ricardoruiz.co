#!/usr/bin/env python3
"""
Caudal · Fase 3 (OCR) — parser de VOTO NOMINAL para las actas de plenaria de
Cámara del formato **DCN-SW** ("Software de Conferencias DCN-SW · Resultados de
votación"), que llegan ESCANEADAS (sin texto nativo) sobre todo en 2014-2017 —
años con CERO cobertura en el pipeline nativo (parse_votaciones_camara.py).

Por qué un parser aparte:
  · El formato DCN-SW no lo reconoce parse_votaciones_camara.py (no es
    consolidado / fragmentado_electronico / manual_tabla).
  · Vienen como imagen → hay que OCR (pymupdf render 300dpi + tesseract spa).

Estructura de un PDF de voto DCN-SW (uno por votación dentro del ZIP de la
sesión, nombrado `NN. P.L.175-2014 (Informe de Conciliacion).pdf`):
  · pág 1: cabecera (Tema, "Nombre", totales Sí/No/No votado, Presente N).
  · pág 2: "Resultados de grupo" (conteo por partido) — se ignora.
  · pág 3..N: "Resultados individuales" — lista NOMINAL seccionada por respuesta
    con encabezados al MARGEN IZQUIERDO ("Yes"/"Sí" · "No" · "No votado" ·
    "Abstención"); cada nombre va INDENTADO en la columna del medio, el partido
    en la columna derecha. La respuesta de cada nombre es la de la sección que
    lo precede.

Clave del parseo: el OCR lineariza y BARAJA el orden de lectura de las columnas,
así que NO se puede confiar en el orden del texto. Se reconstruye por GEOMETRÍA:
se agrupan las palabras en líneas por coordenada-y, se ordena por (página, y), y
un encabezado de sección al margen izquierdo fija la respuesta corriente que
heredan los nombres indentados siguientes.

El número de proyecto sale del NOMBRE DE ARCHIVO (`P.L.175-2014` → token 175/14),
que es más fiable que el OCR de la cabecera; cae al OCR de la pág 1 si el nombre
no trae proyecto.

Uso:
  python3 tools/caudal/actas/parse_dcnsw_camara.py --test 43876   # una acta
  python3 tools/caudal/actas/parse_dcnsw_camara.py --limit 10     # smoke
  python3 tools/caudal/actas/parse_dcnsw_camara.py --workers 6    # todas
"""
import json, re, sys, io, zipfile, unicodedata
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-camara'
RAW_DIR = SRC / 'raw'
IDX = SRC / 'index' / 'indice-completo.json'
PARSED_DIR = SRC / 'parsed-ocr'
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OCR_JSONL = DIST / 'votaciones-camara-nominal-ocr.jsonl'
OCR_STATS = DIST / 'votaciones-camara-ocr-stats.json'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
from normalize_autores import canon_key  # noqa: E402

DPI = 300
# PDFs internos que NO son votos (asistencia / certificación / orden del día…)
SKIP_RE = re.compile(r'asistenc|certi|orden\s*d[ií]a|remisorio|caratula|portada|excusa|oficio', re.I)

# --- proyecto desde el nombre de archivo -----------------------------------
# admite P.L.175-2014 · P.A.L.153-2014 · P.L.E.109-2014 · PL. 178-16 · PL.111-14
FN_PROJ_RE = re.compile(
    r'\bP\.?\s*([AL])?\.?\s*([LAE])?\.?\s*E?\.?\s*(\d{1,4})\s*[-/]\s*((?:20)?\d{2})\b', re.I)
# fallback genérico: primer "NNN-AAAA" o "NNN/AA" del nombre
GEN_PROJ_RE = re.compile(r'\b(\d{1,4})\s*[-/]\s*((?:20)?\d{2})\b')


def norm_proj(n, y):
    y = y[-2:]
    return f'{int(n)}/{y}'


def proj_from_filename(name):
    bn = Path(name).name
    bn = re.sub(r'^\s*\d{1,3}[.\-]\s*', '', bn)   # quita el índice "03. "
    m = FN_PROJ_RE.search(bn)
    if not m:
        m = GEN_PROJ_RE.search(bn)
        if not m:
            return None, ''
        return norm_proj(m.group(1), m.group(2)), _clean_vote_name(bn)
    return norm_proj(m.group(3), m.group(4)), _clean_vote_name(bn)


def _clean_vote_name(bn):
    return re.sub(r'\.pdf$', '', bn, flags=re.I).strip()


# --- respuestas / secciones -------------------------------------------------
def _deaccent(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()


def section_of(text):
    """Devuelve 'Si'|'No'|'Abstencion'|'NoVotado'|None para un encabezado."""
    t = _deaccent(text).strip().lower().rstrip('.:')
    t = re.sub(r'\s+', ' ', t)
    if t in ('yes', 'si', 's'):
        return 'Si'
    if t == 'no':
        return 'No'
    if t.startswith('no votado') or t == 'no votados':
        return 'NoVotado'
    if t.startswith('absten'):
        return 'Abstencion'
    return None


NAME_TOK_RE = re.compile(r'[A-Za-zÁÉÍÓÚÑÜáéíóúñü.\-]{2,}')
# boilerplate del reporte que cae en la columna del medio y NO es un nombre
NAME_STOP = re.compile(
    r'resultado|votaci|software|conferencia|p[aá]gina|impreso|congreso|rep[uú]blica|'
    r'c[aá]mara|representant|reuni[oó]n|plenaria|dcn|individual|asistencia|n[uú]mero|'
    r'tema|nombre|tipo|inicio|fin\b|total|respuesta|grupo|presente', re.I)


# --- OCR + reconstrucción por geometría -------------------------------------
def _ocr_lines(img):
    """Devuelve líneas [{y, xL, xR, W, words:[(x,text)]}] agrupadas por
    coordenada-y (robusto al barajado de columnas del OCR)."""
    import pytesseract
    from pytesseract import Output
    d = pytesseract.image_to_data(img, lang='spa', output_type=Output.DICT)
    W, H = img.size
    words = []
    n = len(d['text'])
    for i in range(n):
        t = (d['text'][i] or '').strip()
        try:
            conf = float(d['conf'][i])
        except Exception:
            conf = -1
        if not t or conf < 30:
            continue
        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
        words.append({'x': x, 'y': y + h / 2, 'h': h, 't': t})
    words.sort(key=lambda z: (z['y'], z['x']))
    lines, cur = [], []
    tol = 14 * (DPI / 300)   # tolerancia vertical (px) para misma fila
    for wd in words:
        if cur and abs(wd['y'] - cur[-1]['y']) <= tol:
            cur.append(wd)
        else:
            if cur:
                lines.append(cur)
            cur = [wd]
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        ln.sort(key=lambda z: z['x'])
        out.append({'y': ln[0]['y'], 'W': W, 'words': [(z['x'], z['t']) for z in ln]})
    return out


def _parse_header_totals(page1_text):
    """Cabecera DCN-SW pág 1: 'Presente en la votación N', y bajo 'Respuestas'
    los conteos Sí/No/Abstención/No votado. Cada uno con su propio regex."""
    t = page1_text
    tot = {}
    m = re.search(r'Presente\s+en\s+la\s+votaci[oó]n\s+(\d{1,3})', t, re.I)
    if m:
        tot['Presente'] = int(m.group(1))
    # a partir de "Respuestas" para no chocar con los conteos por-partido
    resp = t[t.lower().rfind('respuesta'):] if 'respuesta' in t.lower() else t
    for lbl, key, rx in [
        ('Si', 'Si', r'\bS[ií]\s+(\d{1,3})\b'),
        ('No votado', 'NoVotado', r'\bNo\s+votado\s+(\d{1,3})\b'),
        ('No', 'No', r'\bNo\s+(\d{1,3})\b'),
        ('Abstencion', 'Abstencion', r'\bAbstenci[oó]n\s+(\d{1,3})\b'),
    ]:
        mm = re.search(rx, resp, re.I)
        if mm:
            tot[key] = int(mm.group(1))
    return tot


def parse_vote_pdf(data, filename):
    """OCR de un PDF de voto DCN-SW. Devuelve la lista ORDENADA de nombres con su
    sección-por-geometría + los totales de cabecera. La asignación final de
    respuesta la hace finalize_vote() reconciliando ambas señales."""
    import fitz
    from PIL import Image
    try:
        doc = fitz.open(stream=data, filetype='pdf')
    except Exception:
        return None
    all_lines = []
    page1_text = ''
    for pi in range(doc.page_count):
        try:
            pix = doc[pi].get_pixmap(dpi=DPI)
            img = Image.open(io.BytesIO(pix.tobytes('png')))
        except Exception:
            continue
        lns = _ocr_lines(img)
        if pi == 0:
            page1_text = ' '.join(w for ln in lns for _, w in ln['words'])
        for ln in lns:
            all_lines.append((pi, ln))

    full = ' '.join(' '.join(w for _, w in ln['words']) for _, ln in all_lines)
    if 'DCN' not in full.upper() and 'Resultados de votaci' not in full and 'individuales' not in full.lower():
        return None

    # lista ORDENADA de (nombre, sección_geom). La sección-por-geometría usa el
    # orden fijo de DCN-SW: default 'Si' al entrar (encabezado "Yes" gris que el
    # OCR pierde), y cambia con los encabezados oscuros No/No votado/Abstención.
    names = []            # [(name, geom_sec)]  geom_sec ∈ Si|No|Abstencion|NoVotado
    in_indiv = False
    cur = None
    for pi, ln in all_lines:
        W = ln['W']
        joined = ' '.join(w for _, w in ln['words'])
        low = _deaccent(joined).lower()
        if not in_indiv:
            if 'individuales' in low:
                in_indiv = True
                cur = 'Si'
            continue
        xL = ln['words'][0][0]
        if xL / W < 0.25:                       # posible encabezado de sección
            sec = section_of(joined) or section_of(ln['words'][0][1])
            if sec:
                cur = sec
            continue
        name_words = [w for x, w in ln['words'] if 0.22 <= x / W < 0.60]
        if not name_words:
            continue
        name = re.sub(r'\s+', ' ', ' '.join(name_words)).strip(' .')
        if 'partido' in _deaccent(name).lower() or NAME_STOP.search(name):
            continue
        toks = [t for t in NAME_TOK_RE.findall(name) if len(t) >= 2]
        if len(toks) < 2 or len(name) < 6 or len(name) > 70:
            continue
        names.append((name, cur))

    if not names:
        return None
    proj, vname = proj_from_filename(filename)
    return {'nombre': vname, 'proyecto_tok': proj, 'fuente': 'ocr_dcnsw',
            'names_ordered': names, 'totales_cabecera': _parse_header_totals(page1_text)}


def finalize_vote(v):
    """Reconcilia sección-por-geometría vs totales de cabecera y asigna la
    respuesta final por nombre, con un flag de confianza:
      · 'alta'  el tally de geometría == cabecera (o la posición cuadra exacto)
      · 'media' se reasignó por posición (cabecera fiable, encabezado perdido)
      · 'baja'  no reconcilia con la cabecera / sin cabecera para validar
    Los 'NoVotado' (presente sin votar) NO se emiten como voto."""
    names = v['names_ordered']
    tc = v['totales_cabecera'] or {}
    geom = [(n, s) for n, s in names]
    geom_tally = {}
    for _, s in geom:
        geom_tally[s] = geom_tally.get(s, 0) + 1
    hSi, hNo = tc.get('Si'), tc.get('No')
    hAb, hNv = tc.get('Abstencion', 0), tc.get('NoVotado', 0)
    n_names = len(names)
    gSi, gNo, gAb = geom_tally.get('Si', 0), geom_tally.get('No', 0), geom_tally.get('Abstencion', 0)
    # ¿el OCR VIO explícitamente una sección distinta de Sí? (No/Abst/No votado)
    struct_confirmada = bool({'No', 'Abstencion', 'NoVotado'} & set(geom_tally))

    def emit(pairs, conf):
        votos = [(n, s) for n, s in pairs if s in ('Si', 'No', 'Abstencion')]
        resumen = {}
        for _, s in votos:
            resumen[s] = resumen.get(s, 0) + 1
        return {'nombre': v['nombre'], 'proyecto_tok': v['proyecto_tok'],
                'fuente': 'ocr_dcnsw', 'confianza': conf, 'totales_cabecera': tc,
                'resumen': resumen, 'votos': votos}

    # 1) cabecera Sí/No presente y coincide con la geometría → ALTA
    if hSi is not None and hNo is not None:
        tol = max(1, round(0.03 * (hSi + hNo)))
        if abs(gSi - hSi) <= tol and abs(gNo - hNo) <= tol and abs(gAb - hAb) <= max(1, tol):
            return emit(geom, 'alta')
        # 2) cabecera fiable (suma ≈ nº nombres) → reasignar POR POSICIÓN
        #    (recupera encabezados No/Abstención que el OCR perdió). Orden fijo
        #    DCN-SW: Sí · No · Abstención · No votado.
        hsum = hSi + hNo + hAb + hNv
        if hsum and abs(hsum - n_names) <= max(2, round(0.06 * hsum)):
            seq = (['Si'] * hSi + ['No'] * hNo + ['Abstencion'] * hAb + ['NoVotado'] * hNv)
            seq = (seq + ['NoVotado'] * n_names)[:n_names]
            return emit([(names[i][0], seq[i]) for i in range(n_names)], 'media')
        # cabecera contradice y no cuadra por posición → geometría, baja
        return emit(geom, 'baja')

    # 3) sin cabecera numérica utilizable (el nº de la derecha no lo capta el OCR
    #    en muchos escaneos). La geometría es la fuente: fiable si el OCR CONFIRMÓ
    #    la estructura (vio una sección No/Abst) o si es una plenaria llena
    #    (>=40 presentes, patrón de voto casi-unánime real). Riesgo residual: una
    #    sección "No" chica cuyo encabezado el OCR no vio → todo queda Sí; por eso
    #    va como 'media', nunca 'alta', y todo lleva fuente:'ocr'.
    if struct_confirmada or n_names >= 40:
        return emit(geom, 'media')
    return emit(geom, 'baja')


def vote_pdfs_of(path):
    if path.suffix.lower() == '.pdf':
        return [(path.name, path.read_bytes())]
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith('.pdf') and not n.startswith('__MACOSX') and not SKIP_RE.search(Path(n).name):
                    try:
                        out.append((n, z.read(n)))
                    except Exception:
                        pass
    except Exception:
        return []
    return out


def process_acta(aid, meta):
    """Worker: OCR+parse de todas las votaciones DCN-SW de una acta."""
    raws = list(RAW_DIR.glob(f'{aid}.*'))
    if not raws or raws[0].suffix.lower() not in ('.zip', '.pdf'):
        return aid, None
    vps = vote_pdfs_of(raws[0])
    votaciones = []
    for name, data in vps:
        raw = parse_vote_pdf(data, name)
        if not raw:
            continue
        v = finalize_vote(raw)
        if not v['votos']:
            continue
        v['archivo'] = Path(name).name
        votaciones.append(v)
    if not votaciones:
        return aid, {'ok': False, 'n_vote_pdfs': len(vps)}
    return aid, {'ok': True, 'meta': meta, 'votaciones': votaciones}


# --- roster ------------------------------------------------------------------
def load_roster():
    d = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))
    roster = d['roster']
    toks = {k: frozenset(k.split()) for k in roster}
    idx = {}
    for k, ts in toks.items():
        for t in ts:
            idx.setdefault(t, set()).add(k)
    return roster, toks, idx


def match_roster(name_key, roster, roster_toks, tok_idx):
    if name_key in roster:
        return roster[name_key]['partido_principal'], name_key, 'exacto'
    atoks = frozenset(name_key.split())
    if len(atoks) < 2:
        return None, None, None
    cand = None
    for t in atoks:
        s = tok_idx.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    supers = [k for k in (cand or ()) if atoks <= roster_toks[k]]
    if len(supers) == 1:
        return roster[supers[0]]['partido_principal'], supers[0], 'subset'
    if len(supers) > 1:
        partidos = {roster[k]['partido_principal'] for k in supers}
        if len(partidos) == 1:
            best = max(supers, key=lambda k: roster[k]['anio_ultimo'])
            return roster[best]['partido_principal'], best, 'subset-ambiguo'
    return None, None, 'ambiguo'


def load_proj_map():
    p = DIST / 'proyectos.jsonl'
    mp = {}
    if not p.exists():
        return mp
    pr = re.compile(r'\b(\d{1,4})\s*/\s*(?:20)?(\d{2})(?!\d)')
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        nc = (r.get('numero_camara') or '').strip()
        m = pr.search(nc)
        if m:
            mp[f'{int(m.group(1))}/{m.group(2)}'] = {
                'id': r.get('id'), 'titulo': r.get('titulo'), 'numero_camara': nc}
    return mp


# --- run ---------------------------------------------------------------------
def run(ids=None, limit=None, workers=6, test_id=None):
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    idx = json.load(open(IDX, encoding='utf-8'))
    meta_by_id = {it['id']: it for it in idx}
    diag_path = Path('/tmp/diag_pending.json')
    if ids is None:
        if diag_path.exists():
            diag = json.load(open(diag_path, encoding='utf-8'))
            ids = [r['id'] for r in diag if r.get('status') == 'sin-texto-OCR']
        else:
            ids = [it['id'] for it in idx]
    if test_id:
        ids = [test_id]
    if limit:
        ids = ids[:limit]

    roster, rtoks, tidx = load_roster()
    proj_map = load_proj_map()

    results = {}
    if test_id or workers <= 1:
        for aid in ids:
            results[aid] = process_acta(aid, meta_by_id.get(aid, {}))[1]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process_acta, aid, meta_by_id.get(aid, {})): aid for aid in ids}
            done = 0
            for fut in as_completed(futs):
                aid, res = fut.result()
                results[aid] = res
                done += 1
                if done % 20 == 0:
                    nok = sum(1 for r in results.values() if r and r.get('ok'))
                    print(f'  …{done}/{len(ids)} · actas con voto: {nok}', flush=True)

    # consolidar → jsonl + parsed-ocr/{aid}.json + stats
    rows = []
    stats = {'n_actas': len(ids), 'actas_ok': 0, 'n_votaciones': 0, 'n_votos': 0,
             'n_matched': 0, 'n_linked_votac': 0,
             'conf_alta': 0, 'conf_media': 0, 'conf_baja': 0}
    for aid, res in results.items():
        if not res or not res.get('ok'):
            continue
        stats['actas_ok'] += 1
        meta = res['meta']
        acta_out = {'acta_id': aid, 'numero_acta': meta.get('numero'),
                    'fecha_iso': meta.get('fecha_iso'), 'fuente': 'ocr_dcnsw', 'votaciones': []}
        for v in res['votaciones']:
            stats['n_votaciones'] += 1
            conf = v.get('confianza', 'baja')
            stats['conf_' + conf] = stats.get('conf_' + conf, 0) + 1
            tok = v['proyecto_tok']
            proyecto = proj_map.get(tok) if tok else None
            if proyecto:
                stats['n_linked_votac'] += 1
            tc = v.get('totales_cabecera') or {}
            votos_out = []
            for nombre, resp in v['votos']:
                stats['n_votos'] += 1
                key = canon_key(nombre)
                partido, rkey, via = match_roster(key, roster, rtoks, tidx)
                if partido:
                    stats['n_matched'] += 1
                votos_out.append({'congresista': nombre, 'respuesta': resp,
                                  'partido': partido, 'roster_key': rkey, 'match_via': via})
            acta_out['votaciones'].append({
                'numero': None, 'nombre_votacion': v['nombre'],
                'archivo': v['archivo'], 'resumen': v['resumen'],
                'totales_cabecera': tc, 'fuente': 'ocr_dcnsw', 'confianza': conf,
                'proyecto_numero_camara': proyecto['numero_camara'] if proyecto else None,
                'proyecto_id': proyecto['id'] if proyecto else None,
                'proyecto_titulo': proyecto['titulo'] if proyecto else None,
                'votos': votos_out,
            })
            for vo in votos_out:
                rows.append({'acta_id': aid, 'fecha': meta.get('fecha_iso'),
                             'votacion_numero': None, 'votacion_nombre': v['nombre'],
                             'archivo': v['archivo'],
                             'proyecto_numero_camara': proyecto['numero_camara'] if proyecto else None,
                             'fuente': 'ocr_dcnsw', 'confianza': conf, **vo})
        json.dump(acta_out, open(PARSED_DIR / f'{aid}.json', 'w', encoding='utf-8'), ensure_ascii=False)

    DIST.mkdir(parents=True, exist_ok=True)
    with open(OCR_JSONL, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    stats['pct_votos_con_partido'] = round(100 * stats['n_matched'] / stats['n_votos'], 1) if stats['n_votos'] else 0
    json.dump(stats, open(OCR_STATS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n=== resumen OCR DCN-SW ===')
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f'→ {OCR_JSONL}')
    return stats, results


if __name__ == '__main__':
    a = sys.argv
    if '--test' in a:
        tid = a[a.index('--test') + 1]
        _, results = run(test_id=tid)
        res = results.get(tid)
        if res and res.get('ok'):
            for v in res['votaciones']:
                print(f"\n· {v['archivo']}  [{v['confianza']}]")
                print(f"  proyecto_tok={v['proyecto_tok']} · resumen={v['resumen']} · cabecera={v['totales_cabecera']}")
                print(f"  primeros votos: {v['votos'][:3]}")
    else:
        limit = int(a[a.index('--limit') + 1]) if '--limit' in a else None
        workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 6
        run(limit=limit, workers=workers)
