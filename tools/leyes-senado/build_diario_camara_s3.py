#!/usr/bin/env python3
"""
Empaqueta el rastreo diario de CÁMARA para Caudal (S3) — camino completo.

A diferencia del Senado (que aloja un escaneo del radicado), Cámara CITA el
número de Gaceta del Congreso. Este script cierra el "camino 2" (el que pidió
Ricardo): por cada proyecto con gaceta, resuelve número → (entidad, fecha)
[resolver_gaceta], baja el PDF de la Imprenta [descargar_gaceta] y extrae el
texto (born-digital, limpio — muy superior al escaneo del Senado). Produce:

  1. metadata/pl-radicados-camara-{leg}.jsonl   ← lo LEE la Lambda.
  2. radicados-camara-pdf/{leg}/PLC-NNN-YYYY.pdf     (descarga del usuario)
     radicados-camara-texto/{leg}/PLC-NNN-YYYY.txt   (búsqueda + análisis IA)

Idempotente: cachea la gaceta bajada (gacetas/gaceta_{num}_{año}.pdf) y no
re-resuelve/re-baja lo que ya tiene. Un proyecto SIN gaceta aún (recién
radicado) o cuya gaceta la Imprenta no ha publicado todavía entra al manifiesto
como `gaceta_pendiente` (sin llaves de descarga) y se completa solo cuando salga.

Por defecto DRY-RUN. Con --upload sube a producción.

Uso:
  python3 tools/leyes-senado/build_diario_camara_s3.py               # dry-run
  python3 tools/leyes-senado/build_diario_camara_s3.py --upload
  python3 tools/leyes-senado/build_diario_camara_s3.py --legislatura 2025-2026 --max 3
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIARIO = REPO / 'Bases de datos' / 'leyes-senado' / 'diario-camara'
GACETAS = REPO / 'Bases de datos' / 'leyes-senado' / 'gacetas'
BUCKET = 'caudal-legislativo'

sys.path.insert(0, str(REPO / 'tools' / 'caudal' / 'actas'))
from resolver_gaceta import resolver_gaceta   # noqa: E402
from descargar_gaceta import descargar        # noqa: E402


def slug(txt):
    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', txt).strip('-').upper()


def extraer_texto(pdf_path, txt_path):
    try:
        from pypdf import PdfReader
        r = PdfReader(str(pdf_path))
        t = '\n'.join((p.extract_text() or '') for p in r.pages)
    except Exception as e:
        return None, f'ERR {type(e).__name__}'
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(t, encoding='utf-8')
    n = max(1, len(r.pages))
    return len(t), ('digital' if len(t) / n > 200 else 'escaso')


def resolver_y_bajar(gaceta):
    """gaceta {num, anio} → Path del PDF en cache (o None si no publicada aún)."""
    num, anio = gaceta['num'], gaceta['anio']
    cache = GACETAS / f'gaceta_{num}_{anio}.pdf'
    if cache.exists() and cache.stat().st_size > 1000 and cache.read_bytes()[:4] == b'%PDF':
        return cache
    matches = resolver_gaceta(num, anio)
    if not matches:
        return None                        # la Imprenta no la ha publicado todavía
    m = matches[0]
    return descargar(m['ent_arg'], m['fecha'], num)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legislatura', default='2026-2027')
    ap.add_argument('--upload', action='store_true')
    ap.add_argument('--max', type=int, default=0)
    args = ap.parse_args()
    leg = args.legislatura

    base = DIARIO / leg
    snap_path = base / 'proyectos.json'
    if not snap_path.exists():
        print(f'no hay snapshot de Cámara para {leg} (corre harvest_camara.py primero)')
        return
    snap = json.loads(snap_path.read_text(encoding='utf-8'))
    items = list(snap.values())
    if args.max:
        items = items[:args.max]

    (base / 'textos').mkdir(parents=True, exist_ok=True)
    (base / 'textos-txt').mkdir(parents=True, exist_ok=True)

    recs, con_texto, pendientes, pdf_bytes = [], 0, [], 0
    for v in items:
        num_c = v.get('numero_camara', '')
        nombre = f'PLC-{slug(num_c)}'
        rec = dict(v)
        rec['legislatura'] = leg
        rec['camara'] = True
        rec['s3_pdf'] = None
        rec['s3_txt'] = None
        rec['gaceta_pendiente'] = False

        gacetas = v.get('gacetas') or []
        if not gacetas:
            rec['gaceta_pendiente'] = True       # radicado sin gaceta aún
            pendientes.append(num_c)
        else:
            g = gacetas[0]                        # la 1ª citada = radicación
            rec['gaceta_radicado'] = g['key']
            pdf = resolver_y_bajar(g)
            if pdf is None:
                rec['gaceta_pendiente'] = True    # gaceta citada pero no publicada
                pendientes.append(f"{num_c} (gaceta {g['key']} sin publicar)")
            else:
                pdf_dest = base / 'textos' / f'{nombre}.pdf'
                txt_dest = base / 'textos-txt' / f'{nombre}.txt'
                if pdf.resolve() != pdf_dest.resolve():
                    shutil.copy2(pdf, pdf_dest)
                nchars, capa = extraer_texto(pdf_dest, txt_dest)
                rec['s3_pdf'] = f'radicados-camara-pdf/{leg}/{nombre}.pdf'
                rec['s3_txt'] = f'radicados-camara-texto/{leg}/{nombre}.txt'
                rec['pdf_capa'] = capa
                pdf_bytes += pdf_dest.stat().st_size
                con_texto += 1
                print(f'  {num_c:>10}  gaceta {g["key"]:>10}  → {capa} ({pdf_dest.stat().st_size/1e6:.1f} MB)')
        recs.append(rec)

    recs.sort(key=lambda r: int((r.get('numero_camara') or '0/0').split('/')[0]))
    dist = REPO / 'Bases de datos' / 'leyes-senado' / 'dist' / 's3'
    dist.mkdir(parents=True, exist_ok=True)
    meta_path = dist / f'pl-radicados-camara-{leg}.jsonl'
    with meta_path.open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    cmds = [
        f'aws s3 cp "{meta_path}" "s3://{BUCKET}/metadata/pl-radicados-camara-{leg}.jsonl" '
        f'--content-type application/x-ndjson',
        f'aws s3 sync "{base / "textos"}/" "s3://{BUCKET}/radicados-camara-pdf/{leg}/" '
        f'--content-type application/pdf --exclude "*" --include "*.pdf"',
        f'aws s3 sync "{base / "textos-txt"}/" "s3://{BUCKET}/radicados-camara-texto/{leg}/" '
        f'--content-type "text/plain; charset=utf-8" --exclude "*" --include "*.txt"',
    ]

    print(f'\n· legislatura {leg} (Cámara)')
    print(f'· registros en metadata : {len(recs)}')
    print(f'· con texto (gaceta)    : {con_texto} ({pdf_bytes/1e6:.1f} MB)')
    print(f'· pendientes de gaceta  : {len(pendientes)}')
    if pendientes:
        print(f'    {", ".join(pendientes[:8])}{" …" if len(pendientes) > 8 else ""}')
    print(f'· metadata local        : {meta_path.relative_to(REPO)}\n')

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
