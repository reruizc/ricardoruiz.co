#!/usr/bin/env python3
"""
Lector de correos de banco → /gastos/ingest.

Complementa al Atajo de iOS: ese cubre los SMS (Nequi, Bancolombia), este los
correos (Bancolombia, Nubank, Lulo, Davivienda). Los dos escriben en el MISMO
endpoint, así que el parser y la deduplicación son los mismos.

Stdlib pura (imaplib + email + urllib), como el resto de los pipelines del
repo. Pensado para colgarse del cron que ya corre en el Mac.

Configuración en ~/.config/gastos/gastos.env (chmod 600):
    GASTOS_TOKEN=...            # el mismo secreto del worker
    GASTOS_IMAP_USER=tucorreo@gmail.com
    GASTOS_IMAP_PASS=...        # CONTRASEÑA DE APLICACIÓN de Google, no la real
    GASTOS_API=https://rr-auth.reruizc.workers.dev

Uso:
    python3 tools/gastos/correos.py            # lee lo nuevo y lo envía
    python3 tools/gastos/correos.py --dry-run  # muestra qué enviaría, sin enviar
    python3 tools/gastos/correos.py --dias 7   # relee una ventana más amplia
"""
import argparse
import email
import email.header
import html
import imaplib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

CONFIG = pathlib.Path.home() / ".config" / "gastos" / "gastos.env"
ESTADO = pathlib.Path.home() / ".config" / "gastos" / "estado.json"

# Remitentes de banco. El filtro va por dominio, no por nombre para mostrar:
# el nombre lo puede poner cualquiera, el dominio no.
DOMINIOS = [
    "bancolombia.com.co", "bancolombia.com",
    "nequi.com.co", "nequi.com",
    "nu.com.co", "nubank.com.br", "nu.com",
    "lulobank.com",
    "davivienda.com", "daviplata.com",
    "bbva.com", "bbva.com.co",
    "scotiabankcolpatria.com",
    "bancodebogota.com.co", "bancodeoccidente.com.co",
    "avvillas.com.co", "bancopopular.com.co",
    "itau.co", "bancofalabella.com.co",
]

# Asuntos que nunca son un movimiento. El parser del worker también filtra,
# pero descartarlos acá ahorra peticiones.
ASUNTO_IGNORAR = re.compile(
    r"extracto|estado de cuenta|newsletter|bolet[ií]n|promoci[oó]n|"
    r"encuesta|t[eé]rminos y condiciones|actualiza tus datos|"
    r"c[oó]digo de (?:seguridad|verificaci[oó]n)|clave din[aá]mica",
    re.I,
)


def cargar_config():
    cfg = {}
    if CONFIG.exists():
        for linea in CONFIG.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            cfg[k.strip()] = v.strip()
    # El entorno manda sobre el archivo.
    for k in ("GASTOS_TOKEN", "GASTOS_IMAP_USER", "GASTOS_IMAP_PASS", "GASTOS_API"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    cfg.setdefault("GASTOS_API", "https://rr-auth.reruizc.workers.dev")
    return cfg


def cargar_estado():
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return {"vistos": []}


def guardar_estado(est):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    # Solo los últimos 800: el archivo no debe crecer sin freno.
    est["vistos"] = est.get("vistos", [])[-800:]
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(est, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ESTADO)   # escritura atómica: un corte no deja el estado a medias


def decodificar(valor):
    if not valor:
        return ""
    partes = email.header.decode_header(valor)
    out = []
    for texto, enc in partes:
        if isinstance(texto, bytes):
            try:
                out.append(texto.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                out.append(texto.decode("utf-8", errors="replace"))
        else:
            out.append(texto)
    return "".join(out)


_TAG = re.compile(r"<[^>]+>")
_ESPACIO = re.compile(r"\s+")


def a_texto(msg):
    """Cuerpo del correo como texto plano. Prefiere text/plain; si el banco solo
    manda HTML, lo desmaqueta (los correos de banco son tablas simples, no
    hace falta un parser de verdad)."""
    plano, htm = "", ""
    if msg.is_multipart():
        for parte in msg.walk():
            if parte.get_content_maintype() == "multipart":
                continue
            if parte.get_filename():
                continue
            ct = parte.get_content_type()
            try:
                crudo = parte.get_payload(decode=True) or b""
                txt = crudo.decode(parte.get_content_charset() or "utf-8", errors="replace")
            except Exception:
                continue
            if ct == "text/plain" and not plano:
                plano = txt
            elif ct == "text/html" and not htm:
                htm = txt
    else:
        crudo = msg.get_payload(decode=True) or b""
        txt = crudo.decode(msg.get_content_charset() or "utf-8", errors="replace")
        if msg.get_content_type() == "text/html":
            htm = txt
        else:
            plano = txt

    cuerpo = plano
    if not cuerpo.strip() and htm:
        limpio = re.sub(r"(?is)<(script|style).*?</\1>", " ", htm)
        limpio = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</div>", "\n", limpio)
        cuerpo = html.unescape(_TAG.sub(" ", limpio))
    return _ESPACIO.sub(" ", cuerpo).strip()


def enviar(cfg, texto, remitente, dry):
    if dry:
        print(f"  [dry-run] enviaría: {texto[:110]}")
        return {"guardado": None}
    datos = json.dumps({"texto": texto, "metodo": "email", "remitente": remitente}).encode("utf-8")
    req = urllib.request.Request(
        cfg["GASTOS_API"].rstrip("/") + "/gastos/ingest",
        data=datos,
        headers={"Content-Type": "application/json", "X-Gastos-Token": cfg["GASTOS_TOKEN"]},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no envía nada")
    ap.add_argument("--dias", type=int, default=3, help="ventana a revisar (default 3)")
    args = ap.parse_args()

    cfg = cargar_config()
    faltan = [k for k in ("GASTOS_TOKEN", "GASTOS_IMAP_USER", "GASTOS_IMAP_PASS")
              if not cfg.get(k)]
    if faltan and not args.dry_run:
        print(f"Faltan en {CONFIG}: {', '.join(faltan)}", file=sys.stderr)
        return 2
    if faltan:
        print(f"Faltan {', '.join(faltan)} — sin credenciales no hay nada que leer.", file=sys.stderr)
        return 2

    est = cargar_estado()
    vistos = set(est.get("vistos", []))

    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com")
        M.login(cfg["GASTOS_IMAP_USER"], cfg["GASTOS_IMAP_PASS"])
    except imaplib.IMAP4.error as e:
        print(f"No entró a la cuenta: {e}\n"
              f"Recuerda que la contraseña debe ser una CONTRASEÑA DE APLICACIÓN "
              f"de Google, no la del correo.", file=sys.stderr)
        return 3

    desde = (datetime.now() - timedelta(days=args.dias)).strftime("%d-%b-%Y")
    total = enviados = ignorados = 0
    try:
        M.select("INBOX", readonly=True)   # readonly: no marca como leído tu correo
        for dominio in DOMINIOS:
            typ, datos = M.search(None, f'(SINCE {desde} FROM "{dominio}")')
            if typ != "OK" or not datos or not datos[0]:
                continue
            for num in datos[0].split():
                typ, cruda = M.fetch(num, "(RFC822)")
                if typ != "OK" or not cruda or not cruda[0]:
                    continue
                msg = email.message_from_bytes(cruda[0][1])
                mid = decodificar(msg.get("Message-ID") or "") or f"{dominio}:{num.decode()}"
                if mid in vistos:
                    continue
                total += 1
                asunto = decodificar(msg.get("Subject"))
                remitente = decodificar(msg.get("From"))
                if ASUNTO_IGNORAR.search(asunto or ""):
                    vistos.add(mid); ignorados += 1
                    continue

                cuerpo = a_texto(msg)
                # El asunto suele traer el monto; se antepone porque a veces es
                # lo único con la cifra.
                texto = f"{asunto}. {cuerpo}"[:2000]
                try:
                    r = enviar(cfg, texto, remitente, args.dry_run)
                except (urllib.error.URLError, TimeoutError) as e:
                    print(f"  red falló ({e}) — se reintenta en la próxima corrida", file=sys.stderr)
                    continue   # NO se marca visto: se reintenta

                vistos.add(mid)
                if r.get("guardado"):
                    enviados += 1
                    print(f"  + {r.get('comercio','?')} · ${r.get('monto',0):,.0f} · {r.get('categoria','')}")
                elif r.get("guardado") is False:
                    ignorados += 1
    finally:
        try:
            M.logout()
        except Exception:
            pass

    est["vistos"] = sorted(vistos)
    est["ultima_corrida"] = datetime.now().isoformat(timespec="seconds")
    if not args.dry_run:
        guardar_estado(est)

    print(f"correos revisados: {total} · movimientos nuevos: {enviados} · descartados: {ignorados}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
