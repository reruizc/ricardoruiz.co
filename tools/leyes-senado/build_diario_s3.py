#!/usr/bin/env python3
"""
Empaqueta el rastreo diario de proyectos de ley para subirlo a Caudal (S3).

Toma el snapshot de harvest_diario.py + los PDFs/TXT locales y produce:

  1. metadata/pl-radicados-{leg}.jsonl   ← lo LEE la Lambda. Cada registro trae
     los 34 campos del encabezado + tipología (clasificar.py) + intentos_previos
     (cruce contra el histórico pdly) + las DOS llaves de descarga (pdf y txt).
  2. staging para dos prefijos de objeto:
       radicados-pdf/{leg}/PL-NNN-YY.pdf     ← descarga del usuario (presigned)
       radicados-texto/{leg}/PL-NNN-YY.txt   ← búsqueda de texto + análisis IA

El bucket `caudal-legislativo` es PRIVADO (Block Public Access ON). El usuario
NO baja del bucket directo: la Lambda le entrega una URL firmada (SigV4) de vida
corta por objeto. Los radicados son documentos públicos → sin problema legal;
guardar copia propia = resiliencia contra el WAF y los renombres del Senado.

Por defecto hace DRY-RUN (construye local + imprime los comandos). Con --upload
ejecuta el sync a producción.

Uso:
  python3 tools/leyes-senado/build_diario_s3.py                 # dry-run
  python3 tools/leyes-senado/build_diario_s3.py --upload        # sube a S3
  python3 tools/leyes-senado/build_diario_s3.py --legislatura 2026-2027
"""
import argparse
import json
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIARIO = REPO / 'Bases de datos' / 'leyes-senado' / 'diario'
HIST = REPO / 'Bases de datos' / 'leyes-senado' / 'pdly.jsonl'
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist' / 's3'
BUCKET = 'caudal-legislativo'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
import clasificar as C  # noqa: E402


def slug(txt):
    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode()
    import re
    return re.sub(r'[^A-Za-z0-9]+', '-', txt).strip('-').upper()


def cargar_indice_historico(leg_actual):
    """firma de título → nº de intentos previos ARCHIVADOS/muertos (otra legislatura)."""
    idx = defaultdict(list)
    if not HIST.exists():
        return idx
    for line in HIST.open(encoding='utf-8'):
        r = json.loads(line)
        sig = C.titulo_signature(r.get('titulo', ''))
        if sig:
            idx[sig].append(r)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legislatura', default='2026-2027')
    ap.add_argument('--upload', action='store_true')
    args = ap.parse_args()
    leg = args.legislatura

    base = DIARIO / leg
    snap = json.loads((base / 'proyectos.json').read_text(encoding='utf-8'))
    idx_hist = cargar_indice_historico(leg)
    DIST.mkdir(parents=True, exist_ok=True)

    recs, pdf_bytes, txt_bytes, sin_pdf = [], 0, 0, []
    for pid, v in snap.items():
        num = v.get('numero_senado', '') or pid
        nombre = f'PL-{slug(num)}'
        pdf_local = base / 'textos' / f'{nombre}.pdf'
        txt_local = base / 'textos-txt' / f'{nombre}.txt'

        sig = C.titulo_signature(v.get('titulo', ''))
        prev = [p for p in idx_hist.get(sig, []) if p.get('legislatura') != leg]
        tip = C.clasificar_titulo(v.get('titulo', ''))

        rec = dict(v)
        rec['legislatura'] = leg
        rec['tipologia'] = tip.get('tipologia')
        rec['crea_fondo'] = tip.get('crea_fondo')
        rec['intentos_previos'] = len(prev)
        rec['intentos_previos_detalle'] = [
            {'legislatura': p.get('legislatura'), 'estado': p.get('estado')} for p in prev]
        # llaves de descarga (las presigna la Lambda; None si aún no hay PDF)
        rec['s3_pdf'] = f'radicados-pdf/{leg}/{nombre}.pdf' if pdf_local.exists() else None
        rec['s3_txt'] = f'radicados-texto/{leg}/{nombre}.txt' if txt_local.exists() else None
        recs.append(rec)

        if pdf_local.exists():
            pdf_bytes += pdf_local.stat().st_size
        else:
            sin_pdf.append(num)
        if txt_local.exists():
            txt_bytes += txt_local.stat().st_size

    recs.sort(key=lambda r: int((r.get('numero_senado') or '0/0').split('/')[0]))
    meta_path = DIST / f'pl-radicados-{leg}.jsonl'
    with meta_path.open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    cmds = [
        f'aws s3 cp "{meta_path}" '
        f'"s3://{BUCKET}/metadata/pl-radicados-{leg}.jsonl" '
        f'--content-type application/x-ndjson',
        f'aws s3 sync "{base / "textos"}/" '
        f'"s3://{BUCKET}/radicados-pdf/{leg}/" '
        f'--content-type application/pdf --exclude "*" --include "*.pdf"',
        f'aws s3 sync "{base / "textos-txt"}/" '
        f'"s3://{BUCKET}/radicados-texto/{leg}/" '
        f'--content-type "text/plain; charset=utf-8" --exclude "*" --include "*.txt"',
    ]

    print(f'· legislatura {leg}')
    print(f'· registros en metadata : {len(recs)}')
    print(f'· PDFs                  : {sum(1 for r in recs if r["s3_pdf"])} '
          f'({pdf_bytes/1e6:.1f} MB)')
    print(f'· TXT                   : {sum(1 for r in recs if r["s3_txt"])} '
          f'({txt_bytes/1e6:.2f} MB)')
    print(f'· con re-radicación     : {sum(1 for r in recs if r["intentos_previos"])}')
    if sin_pdf:
        print(f'· sin PDF (aún)         : {", ".join(sin_pdf)}')
    print(f'· metadata local        : {meta_path.relative_to(REPO)}')
    print()

    if not args.upload:
        print('DRY-RUN — comandos que ejecutaría con --upload:\n')
        for c in cmds:
            print('  ' + c)
        return
    for c in cmds:
        print('› ' + c)
        subprocess.run(c, shell=True, check=True)
    print('\n✓ subido a s3://' + BUCKET)


if __name__ == '__main__':
    main()
