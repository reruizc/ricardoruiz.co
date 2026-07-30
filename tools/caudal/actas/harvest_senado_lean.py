#!/usr/bin/env python3
"""
Caudal · Fase 3 Senado — PRIMER CORTE LEAN del voto nominal de plenaria.

Toma la lista de candidatos que produjo `harvest_actas_plenaria_senado.py index`
(gacetas de Senado que el filtro fuzzy de la Imprenta devolvió), las descarga,
y **clasifica por CONTENIDO** (masthead de la página 1) — porque el filtro es
inservible: mezcla actas de plenaria con leyes sancionadas y ponencias
(verificado: gaceta 857/2026 = Ley 2588, NO es acta).

Por cada gaceta:
  - descarga el PDF (si no está) vía descargar_gaceta.descargar
  - lee el masthead de la pág. 1 → tipo ∈ {acta_plenaria, ley_sancionada,
    ponencia, acta_comision, otro}
  - si es acta_plenaria: cuenta "Votación Nominal" + tallies "Por el Sí/No"
    (para saber cuántos roll-calls trae antes de gastar DeepSeek)

Escribe un manifiesto a actas/plenaria-senado/manifest-lean.json con, por gaceta:
  {gaceta, fecha, tipo, paginas, acta_num, sesion_fecha, n_votaciones_nominales}
El siguiente paso (subir texto a S3 + correr la acción `gaceta`) solo toca las
que salgan tipo=acta_plenaria con n_votaciones_nominales>0.

Uso:
  python3 tools/caudal/actas/harvest_senado_lean.py
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from descargar_gaceta import descargar, GDIR  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

REPO = Path(__file__).resolve().parents[3]
IDX = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-senado' / 'index' / 'index-senado-acta de plenaria.json'
OUTDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-senado'
MANIFEST = OUTDIR / 'manifest-lean.json'

# El masthead de la Gaceta va con LETTER-SPACING ("A C T A S  D E  P L E N A R I A")
# → pypdf lo extrae con espacios entre cada letra. Se detecta despaciando (quitar
# TODOS los espacios) el encabezado de la pág.1 y buscando tokens sin espacios ni
# tildes. Orden = prioridad (el masthead real gana al "proyecto de ley" del cuerpo).
MASTHEAD_TOKENS = [
    ('acta_plenaria', ('ACTASDEPLENARIA', 'ACTADEPLENARIA')),
    ('ley_sancionada', ('LEYESSANCIONADAS', 'LEYSANCIONADA')),
    ('acta_comision', ('ACTASDECOMISION', 'ACTADECOMISION')),
    ('ponencia', ('INFORMEDEPONENCIA', 'PONENCIAPARA')),
    ('proyecto', ('PROYECTODELEY', 'PROYECTODEACTO')),
]


def _despace(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')  # sin tildes
    return re.sub(r'\s+', '', s).upper()


def _clasif_masthead(page1_text):
    head = _despace(page1_text)[:4500]   # encabezado despaciado de la pág.1
    # prioridad por orden de la lista (el masthead real gana al "proyecto de ley" del cuerpo)
    for name, toks in MASTHEAD_TOKENS:
        if any(t in head for t in toks):
            return name
    return 'otro'
NOMINAL_RE = re.compile(r'Votaci[oó]n\s+Nominal', re.I)
RESULT_RE = re.compile(r'Por\s+el\s+S[ií]\s*:?\s*(\d+).{0,40}?Por\s+el\s+No\s*:?\s*(\d+)', re.I | re.S)
ACTA_NUM_RE = re.compile(r'Acta\s+n[uú]mero\s+(\d+)', re.I)
SESION_RE = re.compile(r'sesi[oó]n\s+plenaria[^0-9]{0,40}(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', re.I)


def _dmy_to_arg(dmy):
    d, m, y = dmy.split('/')
    return f'{int(d)}-{int(m)}-{y}'


def clasificar(path):
    r = PdfReader(str(path))
    npag = len(r.pages)
    page1 = r.pages[0].extract_text() or ''
    tipo = _clasif_masthead(page1)
    head = re.sub(r'\s+', ' ', ' '.join((r.pages[i].extract_text() or '') for i in range(min(2, npag))))
    acta_num = (ACTA_NUM_RE.search(head) or [None, None])[1]
    ses = SESION_RE.search(head)
    info = {'tipo': tipo, 'paginas': npag, 'acta_num': acta_num,
            'sesion': ses.group(1) if ses else None}
    if tipo == 'acta_plenaria':
        full = '\n'.join((pg.extract_text() or '') for pg in r.pages)
        info['n_votaciones_nominales'] = len(NOMINAL_RE.findall(full))
        info['n_tallies'] = len(RESULT_RE.findall(full))
    return info


def main():
    cands = json.load(open(IDX, encoding='utf-8'))
    print(f'{len(cands)} candidatos del índice\n')
    manifest = []
    for c in cands:
        num, dmy = c['gaceta'], c['fecha']
        anio = dmy.split('/')[-1]
        dest = GDIR / f'gaceta_{num}_{anio}.pdf'
        if not dest.exists():
            print(f'· bajando {num}/{anio} ({dmy})…')
            if not descargar('Senado', _dmy_to_arg(dmy), num):
                manifest.append({'gaceta': num, 'fecha': dmy, 'tipo': 'ERROR_DESCARGA'})
                continue
        info = clasificar(dest)
        row = {'gaceta': num, 'fecha': dmy, **info}
        manifest.append(row)
        extra = ''
        if info['tipo'] == 'acta_plenaria':
            extra = f" · acta {info.get('acta_num')} · sesión {info.get('sesion')} · {info.get('n_votaciones_nominales')} votaciones nominales"
        print(f"  {num}/{anio}  {info['tipo']:15s} {info['paginas']:>3}p{extra}")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    actas = [m for m in manifest if m.get('tipo') == 'acta_plenaria']
    tot_vot = sum(m.get('n_votaciones_nominales', 0) for m in actas)
    print(f'\n=== RESUMEN ===')
    print(f'  {len(actas)}/{len(manifest)} son actas de plenaria reales')
    print(f'  {tot_vot} votaciones nominales en total (candidatas a extraer)')
    print(f'  otros tipos: {dict((t, sum(1 for m in manifest if m.get("tipo")==t)) for t in set(m.get("tipo") for m in manifest) if t!="acta_plenaria")}')
    print(f'  → {MANIFEST.relative_to(REPO)}')


if __name__ == '__main__':
    main()
