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

Notas de campo (2026-09-17 · cuatro corridas seguidas muertas por timeout):
  · ⚠⚠ EL BAN DE CADA CORRIDA NOS LO PROVOCÁBAMOS NOSOTROS. El radicado de
    119/26 (Sistema General de Participaciones) pesa **218 MB**. A los ~0,5 MB/s
    que da el servidor no cabe en `--max-time 180`: curl lo cortaba a medio
    bajar, se reintentaba 4 veces, y esos ~100 MB tirados disparaban el ban por
    VOLUMEN. Pasó en 76 corridas seguidas (31-jul → 17-sep): la ficha siguiente
    a 119/26 era siempre la primera «sin respuesta», y las 42 de después
    (120/26-161/26) solo se refrescaban la rara corrida sin ban (1 de las
    últimas 45). Por eso `MAX_PDF_MB`: se pregunta el tamaño antes de bajar.
  · HEAD no sirve para preguntar el tamaño: el WAF responde 403 a HEAD sobre
    CUALQUIER PDF, exista o no. Un GET con `Range: 0-0` sí responde 206 y trae
    el total en Content-Range.
  · El ban cambió de forma: antes cerraba la conexión al instante (exit 52);
    ahora la retiene ~11 s antes de cerrarla. Con 3 intentos por ficha son
    ~45 s por ficha fallida, no ~12 → el mismo ban que antes costaba 8 min de
    reloj ahora cuesta 18, y la corrida dejó de caber en los 2700 s de la etapa.
  · El 15-sep la lista pasó a venir DESCENDENTE (lo más nuevo primero).
  · Una corrida matada por timeout NO guardaba nada: el snapshot se escribía
    solo al final. Y como `cambio_url` compara contra ese snapshot congelado,
    cada corrida re-bajaba los mismos PDFs → mismo ban → misma muerte. No se
    curaba solo. Por eso ahora hay PRESUPUESTO interno: antes de que la etapa
    la mate, deja de pedir, conserva lo que no alcanzó y ESCRIBE lo avanzado.
  · Ante un ban ya no se sigue golpeando ficha por ficha (eran 60-120
    peticiones inútiles contra un WAF que ya nos había cerrado la puerta): a la
    segunda ficha seguida sin respuesta se espera `BAN_ESPERA` y se retoma
    desde la primera que falló. Menos peticiones y las fichas sí se traen.

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

# Tope de tamaño de un PDF. Con --max-time 180 y los ~0,5 MB/s medidos (25,1 MB
# en 47 s) el techo físico ronda los 90 MB; lo más grande que ha bajado entero
# son 77,3 MB (126/26). Los 218 MB de 119/26 no bajaron en 76 corridas ×
# 4 intentos, y cada intento era un ban. Lo que pase del tope se anota y se
# baja a mano UNA vez, desde un navegador (el WAF no banea a Chrome).
MAX_PDF_MB = 100

# La etapa del cron mata a los 2700 s. Se deja de pedir a los 2400: los 300 de
# margen cubren la peor petición en vuelo (un detalle son 3 × 60 s + 9 s de
# pausas = 189 s) más escribir snapshot y reporte.
PRESUPUESTO_S = 2400
MARGEN_S = 120

# Ban: a la 2ª ficha SEGUIDA sin respuesta se deja de insistir. Una sola puede
# ser el parpadeo normal del IIS (medido: una respuesta vacía aislada y la
# siguiente petición bien). El ban dura ~10 min según la nota de arriba y hasta
# 18 medidos el 16-sep; 600 s × 2 esperas cubre ambos y cabe en el presupuesto
# (247 fichas × ~3,5 s ≈ 865 s + 1200 s = 2065 s < 2400 s).
RACHA_BAN = 2
BAN_ESPERA = 600
MAX_ESPERAS = 2

# rc de «corrida parcial»: escribió el snapshot pero dejó fichas sin refrescar.
# Distinto de 0 a propósito: el vigilante tiene que enterarse, y distinto de 1
# para que en el log no se confunda con un traceback. 75 = EX_TEMPFAIL.
RC_PARCIAL = 75
MAX_FALLIDOS_OK = 5

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


def tamano_remoto(url):
    """Bytes del archivo según el servidor, o None si no lo dice.

    GET de UN byte (`Range: 0-0`) y se lee el total del Content-Range. No es
    HEAD porque el WAF responde 403 a HEAD sobre cualquier PDF (ver notas)."""
    safe = urllib.parse.quote(url, safe=':/?=&%')
    r = subprocess.run(['/usr/bin/curl', '-s', '-A', UA, '-r', '0-0', '--max-time', '30',
                        '-o', '/dev/null', '-D', '-', safe], capture_output=True)
    m = re.search(rb'content-range:\s*bytes\s+\d+-\d+/(\d+)', r.stdout or b'', re.I)
    return int(m.group(1)) if m else None


def descargar_pdf(url, dst, retries=4, limite=None):
    """Baja el PDF validando magic bytes. El IIS del Senado devuelve páginas
    de error con HTTP 200, así que el código de estado no sirve de garantía.
    `limite` (epoch): pasado ese instante no se intenta más, y ningún intento
    puede durar más de lo que falta."""
    safe = urllib.parse.quote(url, safe=':/?=&%')
    for intento in range(retries):
        falta = (limite - time.time()) if limite else 180
        if falta < 30:
            break
        blob = curl(safe, timeout=int(min(180, falta)), binary=True, retries=1)
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
        if old.get('_detalle_ok') is False and not old.get('fecha_de_presentacion'):
            continue     # la versión anterior es SOLO la fila de la lista (el
                         # detalle nunca llegó): llenarla es reparación del
                         # dato, no movimiento real. OJO: si trae
                         # fecha_de_presentacion es una ficha completa que se
                         # CONSERVÓ durante un ban — vieja, pero entera — y lo
                         # que cambió desde entonces sí es movimiento. Sin esta
                         # distinción, el trámite de las 42 fichas que el ban
                         # congelaba a diario se perdía sin dejar rastro.
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
    ap.add_argument('--max-pdf-mb', type=float, default=MAX_PDF_MB,
                    help='un PDF más pesado que esto no se baja: se anota para bajarlo a mano')
    ap.add_argument('--presupuesto', type=int, default=PRESUPUESTO_S,
                    help='segundos tras los cuales deja de pedir y escribe lo avanzado')
    args = ap.parse_args()

    # Con la salida entubada (etapa.py) Python la guarda en bloque: si la etapa
    # moría, las líneas de stdout se perdían y las de stderr salían antes que
    # ellas. Al leer el log no había forma de reconstruir el orden.
    sys.stdout.reconfigure(line_buffering=True)

    t0 = time.time()
    limite = t0 + args.presupuesto
    hora = lambda: time.strftime('%H:%M:%S')             # noqa: E731

    leg = args.legislatura
    hoy = dt.date.today().isoformat()
    base = OUT / leg
    snap_path = base / 'proyectos.json'
    prev = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.exists() else {}

    print(f'· legislatura {leg} — snapshot previo: {len(prev)} proyectos')
    lista = fetch_lista(leg)
    print(f'· lista: {len(lista)} proyectos')
    if not lista:
        if prev:
            # Antes salía con 0 y «nada que hacer»: una corrida sin red (el Mac
            # despertando) o en pleno ban quedaba registrada como exitosa.
            print(f'  ✗ la lista llegó vacía y ya había {len(prev)} proyectos: eso es '
                  f'red o WAF, no una legislatura sin radicados', file=sys.stderr)
            return 1
        print('  nada que hacer (¿la legislatura aún no arranca?)')
        return 0

    # La lista llega de lo más nuevo a lo más viejo y el presupuesto puede
    # cortarla antes del final (17-sep-2026: el servidor a ~9,5 s por ficha
    # dejó 88 sin refrescar). Si siempre se arranca por arriba, las que sobran
    # hoy son las mismas que sobran mañana. Por eso van primero las que la
    # corrida anterior no alcanzó o no le respondieron, y después el resto en
    # el orden del registro (lo nuevo primero). Una ficha que se quedó sin
    # refrescar dos veces seguidas es señal de algo más que el presupuesto.
    pendientes = [r for r in lista if prev.get(str(r['id']), {}).get('_detalle_ok') is False]
    if pendientes:
        vistos = {str(r['id']) for r in pendientes}
        lista = pendientes + [r for r in lista if str(r['id']) not in vistos]
        print(f'· {len(pendientes)} fichas sin refrescar en la corrida anterior van primero')

    cur, nota = {}, {}          # nota[pid] = banderas para el resumen final
    t_det, n_det = 0.0, 0       # para reportar cuánto tarda el servidor por ficha
    pdf_bajados = 0

    def conservar(r, motivo):
        """Sin detalle fresco: se queda lo que había (o la fila de la lista)."""
        pid = str(r['id'])
        anterior = prev.get(pid, {})
        det = dict(anterior) if anterior else dict(r)
        det.setdefault('texto_radicado_url', '')
        det['_detalle_ok'] = False
        det['_id'] = pid
        det['_visto'] = hoy                  # sí vino en la lista de hoy
        for k in ('numero_senado', 'numero_camara', 'comision', 'estado', 'autor'):
            det.setdefault(k, r.get(k, ''))
        cur[pid] = det
        nota[pid] = {'fallido': motivo, 'num': det.get('numero_senado', pid)}
        _marcar_sin_pdf(pid, det)

    def _rutas(det, pid):
        nombre = f"PL-{slug(det.get('numero_senado','') or pid)}"
        return base / 'textos' / f'{nombre}.pdf', base / 'textos-txt' / f'{nombre}.txt'

    def _marcar_sin_pdf(pid, det):
        pdf_path, _ = _rutas(det, pid)
        hay = pdf_path.exists() and pdf_path.stat().st_size > 1000
        # "sin PDF" = no hay archivo local utilizable (independiente de por qué)
        nota[pid]['sin_pdf'] = not hay and not det.get('_pdf_local')

    def procesar(i, r):
        """Una ficha: detalle + (si toca) PDF. Devuelve False si no hubo detalle."""
        nonlocal pdf_bajados
        pid = str(r['id'])
        anterior = prev.get(pid, {})
        nonlocal t_det, n_det
        t1 = time.time()
        det = fetch_detalle(pid)
        t_det += time.time() - t1
        n_det += 1
        if det is None:
            # El WAF nos cortó o el detalle no respondió. NO pisar lo que ya
            # teníamos con un registro vacío (eso generaría deltas falsos
            # mañana); se conserva el anterior y se reintenta en la próxima.
            # Tampoco se intenta el PDF: si el detalle no responde, el PDF
            # tampoco, y son hasta 4 peticiones más contra un WAF ya cerrado.
            print(f'  ! {hora()} detalle {pid} sin respuesta — conservo lo anterior',
                  file=sys.stderr)
            conservar(r, 'sin respuesta')
            return False
        det['_detalle_ok'] = True
        det['_id'] = pid
        det['_visto'] = hoy
        for k in ('numero_senado', 'numero_camara', 'comision', 'estado', 'autor'):
            det.setdefault(k, r.get(k, ''))
        nota[pid] = {'num': det.get('numero_senado', pid)}
        tag = f'  [{i + 1:>3}/{len(lista)}] {det.get("numero_senado","?"):>8}  '

        # PDF del texto radicado
        url = det.get('texto_radicado_url') or ''
        pdf_path, txt_path = _rutas(det, pid)
        hay = pdf_path.exists() and pdf_path.stat().st_size > 1000
        if url and not args.no_pdf:
            # OJO: solo cuenta como "cambió la URL" si YA teníamos un registro
            # previo. Sin esta guarda, la primera corrida (prev vacío) creía que
            # los 25 PDFs habían cambiado y los re-bajaba todos → ráfaga → ban.
            cambio_url = bool(anterior) and url != (anterior.get('texto_radicado_url') or '')
            toca = args.repdf or not hay or cambio_url
            grande = anterior.get('_pdf_grande_mb') if not cambio_url else None
            if toca and grande and not args.repdf:
                # ya se sabe que no cabe: ni una petición más por este archivo
                det['_pdf_grande_mb'] = grande
                nota[pid]['grande'] = grande
            elif toca and pdf_bajados >= args.max_pdf:
                # tope anti-ban: lo que sobra se baja en la corrida siguiente
                nota[pid]['pospuesto'] = True
            elif toca and time.time() > limite - MARGEN_S:
                nota[pid]['pospuesto'] = True            # sin tiempo: mañana
            elif toca:
                if pdf_bajados:
                    time.sleep(DELAY_PDF)
                pdf_bajados += 1
                size_remoto = tamano_remoto(url)
                if size_remoto and size_remoto > args.max_pdf_mb * 1e6:
                    mb = round(size_remoto / 1e6, 1)
                    det['_pdf_grande_mb'] = mb
                    nota[pid]['grande'] = mb
                    print(f'{tag}PDF de {mb} MB: pasa el tope de {args.max_pdf_mb:g} MB, '
                          f'NO se baja (bajarlo a mano)', file=sys.stderr)
                else:
                    time.sleep(1.5)                      # respiro tras la sonda de tamaño
                    ok, size = descargar_pdf(url, pdf_path, limite=limite + MARGEN_S)
                    if ok:
                        capa = extraer_texto(pdf_path, txt_path)
                        det['_pdf_local'] = str(pdf_path.relative_to(REPO))
                        det['_pdf_bytes'] = size
                        det['_pdf_capa'] = capa
                        print(f'{tag}PDF {size/1e6:.1f} MB · {capa}')
                    else:
                        print(f'{tag}PDF FALLÓ tras reintentos ({hora()})', file=sys.stderr)
            elif hay:
                det['_pdf_local'] = anterior.get('_pdf_local', str(pdf_path.relative_to(REPO)))
                det['_pdf_bytes'] = anterior.get('_pdf_bytes', pdf_path.stat().st_size)
                det['_pdf_capa'] = anterior.get('_pdf_capa', '')
                if not (txt_path.exists() and txt_path.stat().st_size):
                    det['_pdf_capa'] = extraer_texto(pdf_path, txt_path)

        cur[pid] = det
        _marcar_sin_pdf(pid, det)
        return True

    i, racha, esperas, corte = 0, [], 0, ''
    while i < len(lista):
        if time.time() > limite:
            corte = f'se acabó el presupuesto de {args.presupuesto} s'
            break
        if procesar(i, lista[i]):
            racha = []
        else:
            racha.append(i)
            if len(racha) >= RACHA_BAN:
                cabe = limite - time.time() > BAN_ESPERA + MARGEN_S
                if esperas < MAX_ESPERAS and cabe:
                    esperas += 1
                    print(f'  ‖ {hora()} {len(racha)} fichas seguidas sin respuesta: es el ban. '
                          f'Espero {BAN_ESPERA} s sin tocar el servidor y retomo desde '
                          f'{lista[racha[0]].get("numero_senado", "?")} '
                          f'(espera {esperas}/{MAX_ESPERAS})', file=sys.stderr)
                    time.sleep(BAN_ESPERA)
                    i, racha = racha[0], []
                    continue
                corte = ('el ban sigue tras las esperas' if esperas >= MAX_ESPERAS
                         else 'ban sin tiempo para esperarlo')
                i += 1
                break
        i += 1
        time.sleep(args.delay)

    if corte:
        print(f'  ‖ {hora()} corto acá: {corte}. Conservo las {len(lista) - i} fichas que no '
              f'alcancé y escribo lo avanzado', file=sys.stderr)
        for r in lista[i:]:
            conservar(r, 'no alcancé')

    nuevos, cambios = diff(prev, cur)

    base.mkdir(parents=True, exist_ok=True)
    tmp = snap_path.with_suffix('.json.tmp')             # escritura atómica: si nos
    tmp.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(snap_path)                               # matan acá, queda el anterior
    with (base / 'proyectos.jsonl').open('w', encoding='utf-8') as fh:
        for pid in sorted(cur, key=lambda x: int(x)):
            fh.write(json.dumps(cur[pid], ensure_ascii=False) + '\n')

    nov = OUT / 'novedades'
    escribir_reporte(nov / f'{hoy}.md', nov / f'{hoy}.json',
                     leg, nuevos, cambios, len(cur), hoy)

    de = lambda clave: [n['num'] for n in nota.values() if n.get(clave)]   # noqa: E731
    fallidos, pospuestos, sin_pdf = de('fallido'), de('pospuesto'), de('sin_pdf')
    grandes = [f"{n['num']} ({n['grande']} MB)" for n in nota.values() if n.get('grande')]

    print(f'\n· nuevos: {len(nuevos)} · con movimiento: {len(cambios)} · total: {len(cur)}')
    print(f'· PDFs bajados en esta corrida: {pdf_bajados} · esperas por ban: {esperas} · '
          f'{time.time() - t0:.0f} s · el servidor tardó {t_det / max(1, n_det):.1f} s por ficha')
    if fallidos:
        print(f'· fichas sin refrescar (reintentar): {", ".join(fallidos)}')
    if pospuestos:
        print(f'· PDF pospuestos (tope de {args.max_pdf} o de tiempo): {", ".join(pospuestos)}')
    if grandes:
        print(f'· PDF demasiado grandes, bajar A MANO: {", ".join(grandes)}')
    if sin_pdf:
        print(f'· sin PDF: {", ".join(sin_pdf)}')
    print(f'· snapshot  → {snap_path.relative_to(REPO)}')
    print(f'· novedades → {(nov / f"{hoy}.md").relative_to(REPO)}')

    if corte or len(fallidos) > MAX_FALLIDOS_OK:
        print(f'  ✗ corrida PARCIAL: {len(fallidos)} de {len(lista)} fichas sin refrescar'
              f'{" · " + corte if corte else ""}. Lo avanzado quedó escrito.', file=sys.stderr)
        return RC_PARCIAL
    return 0


if __name__ == '__main__':
    sys.exit(main())
