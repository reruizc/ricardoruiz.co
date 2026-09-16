#!/usr/bin/env python3
"""Publica el brief de Fable para que lo descargue el botón de la Rosa.

  python3 tools/caudal/brief/publicar_brief.py                 # genera y publica los perfiles configurados
  python3 tools/caudal/brief/publicar_brief.py --solo cauce    # uno solo
  python3 tools/caudal/brief/publicar_brief.py --preset cauce \\
      --desde brief.json Brief.pdf Brief.docx                  # publica uno YA generado, sin gastar

QUÉ DEJA. En `s3://caudal-legislativo/metadata/briefs/<slug>/` el JSON, el PDF y
el Word con la fecha en el nombre, y actualiza `metadata/briefs/index.json`, que
dice qué brief le toca a cada perfil. La Lambda (acción `brief-perfil`) lee ese
índice y le da al navegador un enlace firmado de vida corta. El bucket es
privado: sin enlace firmado no se descarga nada.

QUIÉN LO RECIBE. Solo los perfiles cuyo id está en la configuración. El id de un
perfil es aleatorio (64 bits) y solo lo conoce el navegador de su dueño, así que
funciona como llave: nadie pide el brief de Cauce escribiendo «Cauce». Por eso
los ids NO van en este archivo, que está en un repo público:

  ~/.config/caudal/briefs.env   (chmod 600)
    BRIEF_PERFILES="cauce=9af8…,70ad…,aeb2…"      # preset=ids separados por coma; varios clientes con ;

⚠️ La acción es de las CARAS de la Lambda: solo responde a peticiones que llegan
por el worker con acceso a Caudal. El id es la segunda llave, no la única.

⚠️ Si la generación falla NO se toca lo publicado: el botón sigue entregando el
último brief bueno, con su fecha a la vista, en vez de un error o un documento
a medias.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[2]
ENV_FILE = Path.home() / '.config' / 'caudal' / 'briefs.env'
S3 = 's3://caudal-legislativo/metadata/briefs'
LOCAL = REPO / 'Bases de datos' / 'caudal-briefs'
ID_RE = re.compile(r'^[a-f0-9]{8,32}$')


def slug(s):
    t = unicodedata.normalize('NFD', str(s or '').lower())
    return re.sub(r'[^a-z0-9]+', '-', ''.join(c for c in t if unicodedata.category(c) != 'Mn')).strip('-')


def config():
    raw = os.environ.get('BRIEF_PERFILES', '')
    if not raw and ENV_FILE.exists():
        for linea in ENV_FILE.read_text().splitlines():
            if linea.strip().startswith('BRIEF_PERFILES='):
                raw = linea.split('=', 1)[1].strip().strip('"').strip("'")
    out = {}
    for bloque in filter(None, (b.strip() for b in raw.split(';'))):
        preset, _, ids = bloque.partition('=')
        ids = [i.strip() for i in ids.split(',') if ID_RE.match(i.strip())]
        if preset.strip() and ids:
            out[preset.strip()] = ids
    return out


def aws(*args, entrada=None):
    return subprocess.run(['aws', 's3', *args], input=entrada, capture_output=True, text=True)


def subir(local, key, tipo):
    r = aws('cp', str(local), f'{S3}/{key}', '--content-type', tipo,
            '--cache-control', 'private, max-age=60', '--only-show-errors')
    if r.returncode != 0:
        raise RuntimeError(f'no se pudo subir {key}: {r.stderr.strip()[:200]}')


def generar(preset, carpeta):
    """brief.py + render_brief.py --docx. Devuelve (json, pdf, docx)."""
    js = carpeta / 'brief.json'
    r = subprocess.run([sys.executable, str(AQUI / 'brief.py'), preset, '--out', str(js)],
                       capture_output=True, text=True, timeout=1500)
    print(r.stdout.strip()[-600:])
    if r.returncode != 0 or not js.exists():
        raise RuntimeError(f'brief.py falló: {(r.stderr or r.stdout).strip()[-400:]}')
    pdf = carpeta / 'brief.pdf'
    r = subprocess.run([sys.executable, str(AQUI / 'render_brief.py'), str(js), '--out', str(pdf), '--docx'],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not pdf.exists():
        raise RuntimeError(f'render_brief.py falló: {(r.stderr or r.stdout).strip()[-400:]}')
    return js, pdf, pdf.with_suffix('.docx')


def publicar(preset, ids, js, pdf, docx):
    b = json.load(open(js, encoding='utf-8'))
    meta = b.get('_meta') or {}
    nombre = meta.get('cliente') or preset
    s = slug(nombre)
    fecha = (meta.get('ventana') or {}).get('hasta') or datetime.date.today().isoformat()
    base = f'{s}/Brief-{nombre.replace(" ", "-")}-{fecha}'
    for local, ext, tipo in ((js, 'json', 'application/json'), (pdf, 'pdf', 'application/pdf'),
                             (docx, 'docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')):
        if not Path(local).exists():
            raise RuntimeError(f'falta el {ext}: {local}')
        head = Path(local).read_bytes()[:4]
        if (ext == 'pdf' and head != b'%PDF') or (ext == 'docx' and head[:2] != b'PK'):
            raise RuntimeError(f'el {ext} no tiene la firma de un {ext}')
        subir(local, f'{base}.{ext}', tipo)
    # copia local para auditar lo que se entregó
    dest = LOCAL / s
    dest.mkdir(parents=True, exist_ok=True)
    for local, ext in ((js, 'json'), (pdf, 'pdf'), (docx, 'docx')):
        (dest / f'{Path(base).name}.{ext}').write_bytes(Path(local).read_bytes())

    r = aws('cp', f'{S3}/index.json', '-')
    indice = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {'v': 1, 'perfiles': {}}
    entrada = {'slug': s, 'cliente': nombre, 'fecha': fecha,
               'corte': (meta.get('ventana') or {}).get('corte') or '',
               'generado': meta.get('generado'), 'modelo': meta.get('modelo'),
               'titular': (b.get('titular') or '')[:220],
               'pdf': f'{base}.pdf', 'docx': f'{base}.docx', 'json': f'{base}.json'}
    for i in ids:
        indice.setdefault('perfiles', {})[i] = entrada
    indice['actualizado'] = datetime.datetime.now().isoformat(timespec='seconds')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(indice, f, ensure_ascii=False)
    subir(f.name, 'index.json', 'application/json')
    os.unlink(f.name)
    print(f'[publicar] {nombre} {fecha} → {len(ids)} perfil(es) · {S3}/{base}.pdf')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', help='un preset de la configuración')
    ap.add_argument('--preset', help='con --desde: a qué preset pertenece el brief')
    ap.add_argument('--desde', nargs=3, metavar=('JSON', 'PDF', 'DOCX'), help='publicar uno ya generado')
    a = ap.parse_args()
    cfg = config()
    if not cfg:
        sys.exit(f'sin perfiles configurados: BRIEF_PERFILES en el entorno o en {ENV_FILE}')
    if a.desde:
        if not a.preset or a.preset not in cfg:
            sys.exit(f'--desde necesita --preset de la configuración ({", ".join(cfg)})')
        publicar(a.preset, cfg[a.preset], *a.desde)
        return 0
    rc = 0
    for preset, ids in cfg.items():
        if a.solo and preset != a.solo:
            continue
        try:
            with tempfile.TemporaryDirectory() as tmp:
                publicar(preset, ids, *generar(preset, Path(tmp)))
        except Exception as e:                                  # noqa: BLE001
            print(f'[publicar] {preset}: NO se publicó ({e}); queda el último brief bueno')
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
