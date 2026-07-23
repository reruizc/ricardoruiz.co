#!/usr/bin/env python3
"""
Rastreo DIARIO de proyectos de ley del Senado (leyes.senado.gov.co).

Complementa a harvest.py (que baja el histórico 1990-hoy por enumeración de
IDs). Este script mira SOLO la legislatura viva, todos los días, y responde
"¿qué se radicó / qué se movió desde ayer?":

  1. lista    POST api/search_pdly.php  con {legislatura}   → N proyectos
  2. detalle  GET  api/get_detalle_pdly.php?id=N            → encabezado completo
                                                             + data-link del PDF
  3. pdf      GET  https://leyes.senado.gov.co/p-ley/{leg}/{archivo}.pdf
  4. texto    pypdf → .txt (los radicados 2026 traen capa de texto, sin OCR)
  5. diff     compara contra el snapshot de la corrida anterior y emite
              novedades-YYYY-MM-DD.{json,md} (nuevos + campos que cambiaron)

Notas de campo (2026-07-22):
  · El botón "Texto Radicado" del modal NO es un <a href>: es un <button
    id="textoRadicadoBtn" data-link="…"> que app.js abre con window.open.
    El data-link viene dentro del HTML del detalle → se saca por regex.
  · La URL del PDF trae espacios sin codificar; hay que quote() antes de curl.
  · El servidor (IIS) devuelve una página de error HTML con HTTP 200 o 404
    de forma intermitente aunque el archivo exista → reintentar y validar
    los magic bytes %PDF (no confiar en el código HTTP).
  · La lista se actualiza en vivo: durante una sesión de ~30 min pasó de 22
    a 25 proyectos. Correr una vez al día es el piso, no el techo.
  · ⚠ HAY WAF CON BAN TEMPORAL. Tras una ráfaga (~30 peticiones seguidas,
    varias de ellas PDFs de MBs) el servidor deja de responder a curl:
    cierra la conexión sin cuerpo (curl exit 52, "Empty reply"), a TODO —
    home, API y PDFs. NO es bloqueo de IP: durante el ban, Chrome desde la
    misma máquina seguía respondiendo 200. Es fingerprint del cliente (JA3)
    + volumen; cambiar User-Agent, headers o versión de HTTP no lo evade.
    Dura ~10 minutos y se levanta solo. Por eso los defaults son lentos
    (DELAY_META=3 s, DELAY_PDF=6 s, MAX_PDF_POR_CORRIDA=20) y en el uso
    diario real casi no se notan: solo se bajan los PDFs nuevos del día.
    Si algún día hay que bajar mucho de golpe, instalar `curl-cffi` (curl
    que imita el handshake TLS de Chrome) en vez de subir la velocidad.
  · Los PDFs son ESCANEOS (productor "PFUPDF Engine" = Fujitsu ScanSnap:
    el Senado escanea el radicado firmado en papel) pero ya vienen con capa
    OCR embebida por el escáner → pypdf saca el texto sin que nosotros
    corramos OCR. Calidad: el articulado se lee bien; firmas, membretes y
    logos salen sucios ("ANA PA LO GARCÍA"), y a veces se pierden espacios
    ("laRepública"). Para nombres usar SIEMPRE el campo `autor` del
    encabezado, nunca el OCR.

Uso:
  python3 tools/leyes-senado/harvest_diario.py                      # legislatura por defecto
  python3 tools/leyes-senado/harvest_diario.py --legislatura 2025-2026
  python3 tools/leyes-senado/harvest_diario.py --no-pdf             # solo metadatos
  python3 tools/leyes-senado/harvest_diario.py --repdf              # re-baja PDFs existentes
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest import parse_detalle  # noqa: E402  (mismo parser del histórico)

BASE = 'https://leyes.senado.gov.co'
API = f'{BASE}/api'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'diario'

LEG_DEFAULT = '2026-2027'

# ritmo: el WAF banea ~10 min ante ráfagas (ver nota de campo arriba)
DELAY_META = 3.0      # s entre detalles
DELAY_PDF = 6.0       # s entre descargas de PDF
MAX_PDF_POR_CORRIDA = 20

# <button ... id='textoRadicadoBtn' data-link='https://…pdf'>  (comillas simples en el HTML)
RE_TEXTO_RADICADO = re.compile(
    r"""id=['"]textoRadicadoBtn['"][^>]*?data-link=['"]([^'"]*)['"]""", re.I | re.S)

# campos cuyo cambio es noticia (lo demás es ruido de formato)
CAMPOS_VIGILADOS = [
    'titulo', 'numero_senado', 'numero_camara', 'comision', 'estado',
    'autor', 'ponente_primer_debate', 'fecha_de_aprobacion_primer_debate',
    'ponente_segundo_debate', 'fecha_de_aprobacion_segundo_debate',
    'ponente_primer_debate_camara', 'fecha_de_aprobacion_primer_debate_camara',
    'ponente_segundo_debate_camara', 'fecha_de_aprobacion_segundo_debate_camara',
    'conciliador_senado', 'conciliador_camara', 'fecha_de_envio_comision',
    'exposicion_de_motivos', 'primera_ponencia', 'segunda_ponencia',
    'texto_plenaria', 'conciliacion', 'objeciones', 'texto_radicado_url',
]


# ------------------------------------------------------------------ red
def curl(url, post=None, timeout=60, binary=False, retries=3, delay=1.5):
    """curl por subprocess (mismo patrón de harvest.py / scrape_cne.py)."""
    cmd = ['/usr/bin/curl', '-sL', '-A', UA, '--max-time', str(timeout), url]
    if post:
        cmd = cmd[:1] + ['-X', 'POST'] + cmd[1:]
        for k, v in post.items():
            cmd += ['--data-urlencode', f'{k}={v}']
    for intento in range(retries):
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout if binary else r.stdout.decode('utf-8', errors='replace')
        time.sleep(delay * (intento + 1))
    return b'' if binary else ''


def slug(txt):
    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', txt).strip('-').upper()


# --------------------------------------------------------------- fases
def fetch_lista(legislatura):
    body = curl(f'{API}/search_pdly.php', post={'legislatura': legislatura})
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f'  ! respuesta no-JSON de search_pdly ({len(body)} bytes)', file=sys.stderr)
        return []
    return data.get('data') or []


def fetch_detalle(rec_id):
    html = curl(f'{API}/get_detalle_pdly.php?id={rec_id}')
    if not html:
        return None
    det = parse_detalle(html, 'pdly', rec_id)
    m = RE_TEXTO_RADICADO.search(html)
    det['texto_radicado_url'] = m.group(1).strip() if m else ''
    return det


def descargar_pdf(url, dst, retries=4):
    """Baja el PDF validando magic bytes. El IIS del Senado devuelve páginas
    de error con HTTP 200, así que el código de estado no sirve de garantía."""
    safe = urllib.parse.quote(url, safe=':/?=&%')
    for intento in range(retries):
        blob = curl(safe, timeout=180, binary=True, retries=1)
        if blob[:4] == b'%PDF':
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(blob)
            return True, len(blob)
        time.sleep(2 * (intento + 1))
    return False, 0


def extraer_texto(pdf_path, txt_path):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(pdf_path))
        texto = '\n'.join((p.extract_text() or '') for p in reader.pages)
    except Exception as e:                                   # PDF truncado/corrupto
        return f'ERR: {type(e).__name__}'
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(texto, encoding='utf-8')
    # Son escaneos con OCR embebido del escáner del Senado. Si la densidad
    # cae por debajo de ~300 chars/página, ese OCR no existe o falló → ahí sí
    # tocaría pasarle Tesseract (ver tools/caudal/actas/ocr_pilot.py).
    n = max(1, len(reader.pages))
    return 'ocr-embebido' if len(texto) / n > 300 else 'SIN-TEXTO-necesita-OCR'


# ----------------------------------------------------------------- diff
def diff(prev, cur):
    nuevos, cambios = [], []
    for pid, rec in cur.items():
        old = prev.get(pid)
        if old is None:
            nuevos.append(rec)
            continue
        if old.get('_detalle_ok') is False:
            continue     # la versión anterior quedó incompleta por un corte:
                         # esto es reparación del dato, no movimiento real
        deltas = {c: {'antes': old.get(c, ''), 'ahora': rec.get(c, '')}
                  for c in CAMPOS_VIGILADOS
                  if (old.get(c) or '') != (rec.get(c) or '')}
        if deltas:
            cambios.append({'id': pid, 'numero_senado': rec.get('numero_senado', ''),
                            'titulo': rec.get('titulo', ''), 'deltas': deltas})
    return nuevos, cambios


def escribir_reporte(dest_md, dest_json, leg, nuevos, cambios, total, fecha):
    payload = {'fecha': fecha, 'legislatura': leg, 'total_en_legislatura': total,
               'nuevos': nuevos, 'cambios': cambios}
    dest_json.parent.mkdir(parents=True, exist_ok=True)
    dest_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')

    L = [f'# Rastreo legislativo · {fecha}', '',
         f'Legislatura **{leg}** · {total} proyectos de ley acumulados', '',
         f'- Nuevos hoy: **{len(nuevos)}**', f'- Con movimiento: **{len(cambios)}**', '']
    if nuevos:
        L += ['## Radicados nuevos', '']
        for r in nuevos:
            L += [f"### {r.get('numero_senado','?')} · {r.get('comision','')} · {r.get('fecha_de_presentacion','')}",
                  f"**{r.get('titulo','')}**", '',
                  f"- Autor: {r.get('autor','') or '—'}",
                  f"- Estado: {r.get('estado','') or '—'}",
                  f"- Tipo: {r.get('tipo_de_ley','') or '—'} · Origen: {r.get('origen','') or '—'}",
                  f"- Texto radicado: {r.get('texto_radicado_url','') or '(sin PDF publicado)'}",
                  f"- PDF local: {r.get('_pdf_local','') or '—'}", '']
    if cambios:
        L += ['## Movimiento en proyectos ya radicados', '']
        for c in cambios:
            L += [f"### {c['numero_senado']} — {c['titulo'][:90]}"]
            for campo, d in c['deltas'].items():
                L.append(f"- `{campo}`: «{d['antes'] or '—'}» → «{d['ahora'] or '—'}»")
            L.append('')
    if not nuevos and not cambios:
        L += ['_Sin novedades._', '']
    dest_md.write_text('\n'.join(L), encoding='utf-8')


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legislatura', default=LEG_DEFAULT)
    ap.add_argument('--no-pdf', action='store_true', help='solo metadatos')
    ap.add_argument('--repdf', action='store_true', help='re-descarga PDFs ya bajados')
    ap.add_argument('--delay', type=float, default=DELAY_META, help='pausa entre detalles (s)')
    ap.add_argument('--max-pdf', type=int, default=MAX_PDF_POR_CORRIDA,
                    help='tope de PDFs por corrida (el resto queda para mañana)')
    args = ap.parse_args()

    leg = args.legislatura
    hoy = dt.date.today().isoformat()
    base = OUT / leg
    snap_path = base / 'proyectos.json'
    prev = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.exists() else {}

    print(f'· legislatura {leg} — snapshot previo: {len(prev)} proyectos')
    lista = fetch_lista(leg)
    print(f'· lista: {len(lista)} proyectos')
    if not lista:
        print('  nada que hacer (¿la legislatura aún no arranca?)')
        return

    cur, sin_pdf, pdf_bajados, pospuestos, fallidos = {}, [], 0, [], []
    for i, r in enumerate(lista, 1):
        pid = str(r['id'])
        anterior = prev.get(pid, {})
        det = fetch_detalle(pid)
        if det is None:
            # El WAF nos cortó o el detalle no respondió. NO pisar lo que ya
            # teníamos con un registro vacío (eso generaría deltas falsos
            # mañana); se conserva el anterior y se reintenta en la próxima.
            fallidos.append(r.get('numero_senado', pid))
            print(f'  ! detalle {pid} sin respuesta — conservo lo anterior', file=sys.stderr)
            det = dict(anterior) if anterior else dict(r)
            det.setdefault('texto_radicado_url', '')
            det['_detalle_ok'] = False
        else:
            det['_detalle_ok'] = True
        det['_id'] = pid
        det['_visto'] = hoy
        for k in ('numero_senado', 'numero_camara', 'comision', 'estado', 'autor'):
            det.setdefault(k, r.get(k, ''))

        # PDF del texto radicado
        url = det.get('texto_radicado_url') or ''
        nombre = f"PL-{slug(det.get('numero_senado','') or pid)}"
        pdf_path = base / 'textos' / f'{nombre}.pdf'
        txt_path = base / 'textos-txt' / f'{nombre}.txt'
        hay = pdf_path.exists() and pdf_path.stat().st_size > 1000
        if url and not args.no_pdf:
            # OJO: solo cuenta como "cambió la URL" si YA teníamos un registro
            # previo. Sin esta guarda, la primera corrida (prev vacío) creía que
            # los 25 PDFs habían cambiado y los re-bajaba todos → ráfaga → ban.
            cambio_url = bool(anterior) and url != (anterior.get('texto_radicado_url') or '')
            if (args.repdf or not hay or cambio_url) and pdf_bajados >= args.max_pdf:
                # tope anti-ban: lo que sobra se baja en la corrida siguiente
                pospuestos.append(det.get('numero_senado', pid))
            elif args.repdf or not hay or cambio_url:
                if pdf_bajados:
                    time.sleep(DELAY_PDF)
                ok, size = descargar_pdf(url, pdf_path)
                pdf_bajados += 1
                if ok:
                    capa = extraer_texto(pdf_path, txt_path)
                    det['_pdf_local'] = str(pdf_path.relative_to(REPO))
                    det['_pdf_bytes'] = size
                    det['_pdf_capa'] = capa
                    print(f'  [{i:>3}/{len(lista)}] {det.get("numero_senado","?"):>8}  '
                          f'PDF {size/1e6:.1f} MB · {capa}')
                else:
                    print(f'  [{i:>3}/{len(lista)}] {det.get("numero_senado","?"):>8}  '
                          f'PDF FALLÓ tras reintentos', file=sys.stderr)
            elif hay:
                det['_pdf_local'] = anterior.get('_pdf_local', str(pdf_path.relative_to(REPO)))
                det['_pdf_bytes'] = anterior.get('_pdf_bytes', pdf_path.stat().st_size)
                det['_pdf_capa'] = anterior.get('_pdf_capa', '')
                if not (txt_path.exists() and txt_path.stat().st_size):
                    det['_pdf_capa'] = extraer_texto(pdf_path, txt_path)

        # "sin PDF" = no hay archivo local utilizable (independiente de por qué)
        if not hay and not det.get('_pdf_local'):
            sin_pdf.append(det.get('numero_senado', pid))

        cur[pid] = det
        time.sleep(args.delay)

    nuevos, cambios = diff(prev, cur)

    base.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding='utf-8')
    with (base / 'proyectos.jsonl').open('w', encoding='utf-8') as fh:
        for pid in sorted(cur, key=lambda x: int(x)):
            fh.write(json.dumps(cur[pid], ensure_ascii=False) + '\n')

    nov = OUT / 'novedades'
    escribir_reporte(nov / f'{hoy}.md', nov / f'{hoy}.json',
                     leg, nuevos, cambios, len(cur), hoy)

    print(f'\n· nuevos: {len(nuevos)} · con movimiento: {len(cambios)} · total: {len(cur)}')
    print(f'· PDFs bajados en esta corrida: {pdf_bajados}')
    if fallidos:
        print(f'· detalle sin respuesta (reintentar): {", ".join(fallidos)}')
    if pospuestos:
        print(f'· pospuestos por el tope anti-ban ({args.max_pdf}): {", ".join(pospuestos)}')
    if sin_pdf:
        print(f'· sin PDF: {", ".join(sin_pdf)}')
    print(f'· snapshot  → {snap_path.relative_to(REPO)}')
    print(f'· novedades → {(nov / f"{hoy}.md").relative_to(REPO)}')


if __name__ == '__main__':
    main()
