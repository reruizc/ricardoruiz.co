#!/usr/bin/env python3
"""
Caudal · Fase 3 SENADO — parser de VOTO NOMINAL desde las actas de plenaria.

A diferencia de Cámara (tabla electrónica), el Senado narra el roll-call en el
acta de la Gaceta:
   Por el Sí: 47  Por el No: 17  TOTAL: 64 Votos
   Votación Nominal a <descripción> …
   Honorables Senadores Por el Sí  <Apellido Apellido Nombre Nombre> …
   Honorables Senadores Por el No  <…>
   26.III.2025           ← marcador de fecha que cierra el bloque

Estrategia (determinista, sin DeepSeek — captura los N votos de una):
  1. limpia pies de página de la Gaceta.
  2. ancla en cada "Honorables Senadores Por el Sí" (= un roll-call real).
  3. por bloque: toma el tally + la descripción previos, y los blobs de nombres
     del Sí y (si hay) del No, acotados hasta el marcador de fecha / "En
     consecuencia" / siguiente votación.
  4. SEGMENTA cada blob de nombres con matching greedy (longest-first) contra el
     roster global (mismo `match_roster` por subconjunto de tokens de Cámara).
  5. vincula la votación a numero_senado del dataset cuando la descripción trae
     "Proyecto de Ley número N de AAAA".

Salida: dist/votaciones-senado-nominal.jsonl (espejo del de Cámara) +
        dist/votaciones-senado-stats.json.

Uso:
  python3 tools/caudal/actas/parse_actas_senado.py            # actas del manifest-lean
  python3 tools/caudal/actas/parse_actas_senado.py 828-2026   # una gaceta puntual
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[3]
GDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'gacetas'
SENDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-senado'
MANIFEST = SENDIR / 'manifest-lean.json'
PARSED_DIR = SENDIR / 'parsed'
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
sys.path.insert(0, str(REPO / 'tools' / 'caudal' / 'actas'))
from normalize_autores import canon_key  # noqa: E402
from parse_votaciones_camara import load_roster, match_roster, _norm_proj  # noqa: E402

# --- regex ------------------------------------------------------------------
FOOTER_RE = re.compile(
    r'P[aá]gina\s+\d+\s+\w+,?\s+\d+\s+de\s+\w+\s+de\s+\d+\s+G\s?aceta\s+del\s+Congreso\s*\d+|'
    r'G\s?aceta\s+del\s+Congreso\s*\d+\s+\w+,?\s+\d+\s+de\s+\w+\s+de\s+\d+\s+P[aá]gina\s+\d+', re.I)
SI_ANCHOR_RE = re.compile(r'Honorables\s+Senadores\s+Por\s+el\s+S[ií]', re.I)
NO_ANCHOR_RE = re.compile(r'Honorables\s+Senadores\s+Por\s+el\s+No', re.I)
TALLY_RE = re.compile(r'Por\s+el\s+S[ií]\s*:?\s*(\d+)\D{0,40}?Por\s+el\s+No\s*:?\s*(\d+)', re.I | re.S)
DESC_RE = re.compile(r'Votaci[oó]n\s+Nominal\s+(.+?)(?=Honorables\s+Senadores|$)', re.I | re.S)
# cierre de un blob de nombres: marcador de fecha "26.III.2025" (día.MesRomano.año),
# "En consecuencia", "Sección Relatoría"  (NO incluye "Votación Nominal": entre el
# bloque del Sí y el del No hay un "Votación Nominal <misma desc>" del mismo voto).
END_INNER_RE = re.compile(
    r'\d{1,2}\s*\.\s*[IVXLC]{1,5}\s*\.\s*\d{4}|En\s+consecuencia|Secci[oó]n\s+Relator', re.I)
PROJ_RE = re.compile(r'n[uú]mero\s+(\d{1,4})\s+de\s+(20\d{2})', re.I)
PROJ_RE2 = re.compile(r'\b(\d{1,4})\s*/\s*(?:20)?(\d{2})(?!\d)')


def _despace_head(page1):
    s = unicodedata.normalize('NFD', page1)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', '', s).upper()


def _clean(txt):
    return FOOTER_RE.sub(' ', txt)


def load_numero_senado_map():
    p = DIST / 'proyectos.jsonl'
    mp = {}
    if not p.exists():
        return mp
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        ns = (r.get('numero_senado') or '').strip()
        m = PROJ_RE2.search(ns)
        if m:
            mp[_norm_proj(m.group(1), m.group(2))] = {
                'id': r.get('id'), 'titulo': r.get('titulo'), 'numero_senado': ns,
                'numero_camara': r.get('numero_camara'),
            }
    return mp


def link_proyecto(desc, proj_map):
    m = PROJ_RE.search(desc or '')
    if not m:
        return None
    return proj_map.get(_norm_proj(m.group(1), m.group(2)))


def segment_names(blob, roster, roster_toks, tok_idx):
    """Greedy longest-first: parte el blob concatenado de nombres en
    (nombre_texto, roster_key) casando spans de 5→2 tokens contra el roster."""
    words = [w for w in re.split(r'\s+', blob) if w]
    out, i, n = [], 0, len(words)
    while i < n:
        hit = None
        for L in range(5, 1, -1):
            if i + L > n:
                continue
            span = ' '.join(words[i:i + L])
            key = canon_key(span)
            if len(key.split()) < 2:
                continue
            _, rkey, via = match_roster(key, roster, roster_toks, tok_idx)
            if rkey and via in ('exacto', 'subset', 'subset-ambiguo'):
                hit = (span, rkey, via, L)
                break
        if hit:
            out.append({'congresista': hit[0], 'roster_key': hit[1], 'match_via': hit[2]})
            i += hit[3]
        else:
            i += 1
    # dedup por roster_key (por si un span solapa)
    seen, ded = set(), []
    for v in out:
        if v['roster_key'] in seen:
            continue
        seen.add(v['roster_key'])
        ded.append(v)
    return ded


def parse_acta(text, roster, roster_toks, tok_idx, proj_map):
    txt = _clean(text)
    anchors = list(SI_ANCHOR_RE.finditer(txt))
    votaciones = []
    for k, a in enumerate(anchors):
        si_start = a.end()
        # cada voto va acotado por el SIGUIENTE ancla de "Por el Sí"
        seg_end = anchors[k + 1].start() if k + 1 < len(anchors) else len(txt)
        # descripción + tally previos: desde el ancla anterior (o 900 chars atrás)
        pre_start = anchors[k - 1].end() if k > 0 else max(0, a.start() - 900)
        pre = txt[pre_start:a.start()]
        tally = TALLY_RE.findall(pre)
        n_si = int(tally[-1][0]) if tally else None
        n_no = int(tally[-1][1]) if tally else None
        dm = list(DESC_RE.finditer(pre + ' Honorables Senadores'))
        desc = re.sub(r'\s+', ' ', dm[-1].group(1)).strip() if dm else ''
        # ancla del No dentro de este voto (puede venir tras el marcador de fecha del Sí)
        no_a = NO_ANCHOR_RE.search(txt, si_start, seg_end)
        # blob del Sí: hasta el marcador de fecha o el ancla del No (lo que venga antes)
        end_si = END_INNER_RE.search(txt, si_start, no_a.start() if no_a else seg_end)
        si_cands = [x.start() for x in (no_a, end_si) if x] + [seg_end]
        si_blob = txt[si_start:min(si_cands)]
        # blob del No
        no_blob = ''
        if no_a:
            no_start = no_a.end()
            end_no = END_INNER_RE.search(txt, no_start, seg_end)
            no_blob = txt[no_start:end_no.start() if end_no else seg_end]
        votos = []
        for v in segment_names(si_blob, roster, roster_toks, tok_idx):
            votos.append({**v, 'respuesta': 'Si'})
        no_keys = {v['roster_key'] for v in votos}
        for v in segment_names(no_blob, roster, roster_toks, tok_idx):
            if v['roster_key'] in no_keys:
                continue
            votos.append({**v, 'respuesta': 'No'})
        proyecto = link_proyecto(desc, proj_map)
        votaciones.append({
            'numero': k + 1, 'descripcion': desc,
            'resumen_reportado': {'Si': n_si, 'No': n_no},
            'proyecto': proyecto, 'votos': votos,
        })
    return votaciones


def _actas_del_manifest():
    if not MANIFEST.exists():
        return []
    return [(m['gaceta'], m['fecha']) for m in json.load(open(MANIFEST, encoding='utf-8'))
            if m.get('tipo') == 'acta_plenaria']


def main():
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    roster, roster_toks, tok_idx = load_roster()
    proj_map = load_numero_senado_map()

    if len(sys.argv) > 1 and re.match(r'\d+-\d{4}', sys.argv[1]):
        num, anio = sys.argv[1].split('-')
        targets = [(num, f'??/??/{anio}')]
    else:
        targets = _actas_del_manifest()
    print(f'{len(targets)} actas de plenaria a parsear\n')

    rows, resumen = [], {'actas': 0, 'votaciones': 0, 'votos': 0, 'con_roster': 0}
    for num, fecha in targets:
        anio = fecha.split('/')[-1]
        pdf = GDIR / f'gaceta_{num}_{anio}.pdf'
        if not pdf.exists():
            print(f'  ⚠ falta {pdf.name}'); continue
        text = '\n'.join((p.extract_text() or '') for p in PdfReader(str(pdf)).pages)
        vots = parse_acta(text, roster, roster_toks, tok_idx, proj_map)
        resumen['actas'] += 1
        outf = PARSED_DIR / f'{num}-{anio}.json'
        json.dump({'gaceta': f'{num}-{anio}', 'votaciones': vots}, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        for v in vots:
            resumen['votaciones'] += 1
            proy = v['proyecto']
            si = sum(1 for x in v['votos'] if x['respuesta'] == 'Si')
            no = sum(1 for x in v['votos'] if x['respuesta'] == 'No')
            rep = v['resumen_reportado']
            print(f"  {num}/{anio} #{v['numero']:>2} · Sí {si}/{rep['Si']} · No {no}/{rep['No']}"
                  f" · proy={proy['numero_senado'] if proy else '—'} · {v['descripcion'][:52]}")
            for x in v['votos']:
                resumen['votos'] += 1
                if x['roster_key']:
                    resumen['con_roster'] += 1
                rows.append({
                    'acta_gaceta': f'{num}-{anio}', 'fecha': fecha, 'votacion_numero': v['numero'],
                    'descripcion': v['descripcion'],
                    'proyecto_numero_senado': proy['numero_senado'] if proy else None,
                    'proyecto_id': proy['id'] if proy else None,
                    'proyecto_titulo': proy['titulo'] if proy else None,
                    **x,
                })
    with open(DIST / 'votaciones-senado-nominal.jsonl', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    resumen['pct_con_roster'] = round(100 * resumen['con_roster'] / resumen['votos'], 1) if resumen['votos'] else 0
    json.dump(resumen, open(DIST / 'votaciones-senado-stats.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n=== resumen ===\n{json.dumps(resumen, ensure_ascii=False, indent=1)}")
    print(f"→ {DIST / 'votaciones-senado-nominal.jsonl'}")


if __name__ == '__main__':
    main()
