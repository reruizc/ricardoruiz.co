"""Manda el brief de cliente por correo: PDF para leer y Word para reescribir.

Lo usa el workflow que programa el brief, que vive en un repo PRIVADO
(`reruizc/caudal-briefs`). Este archivo está en el repo público y por eso no
lleva nada de ningún cliente: los destinatarios y el token entran por el entorno.

    CAUDAL_BRIEFS_TOKEN=… BRIEF_PARA=a@x.co,b@y.co \\
      python3 tools/caudal/brief/enviar_brief.py brief.json Brief.pdf Brief.docx

El envío pasa por el worker rr-auth (`/caudal/briefs/enviar`), no por Resend
directo: el worker ya manda desde el dominio verificado y SOLO a gente con acceso
a Caudal. Así el brief de un cliente no puede salir hacia afuera ni aunque el
token se filtre o alguien escriba mal un destinatario.

⚠️ El destinatario es el EQUIPO, nunca el cliente final. El pie del brief promete
«revisión humana antes de enviar»; mandárselo directo al cliente lo desmentiría.

⚠️ Lleva User-Agent propio: el worker está detrás de la protección contra bots de
Cloudflare y a `Python-urllib/3.x` le responde 403, que se lee como token malo.
"""
import argparse
import base64
import html
import json
import os
import sys
import urllib.error
import urllib.request

WORKER = os.environ.get('CAUDAL_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
RUTA = '/caudal/briefs/enviar'
UA = 'caudal-briefs/1.0 (+ricardoruiz.co)'


def cuerpo_html(b):
    """El correo lleva lo mínimo para decidir si abrir ya: titular, la acción de
    «si solo hay tiempo para una cosa» y el recordatorio de que es un borrador."""
    meta = b.get('_meta') or {}
    v = meta.get('ventana') or {}
    lec = b.get('lectura') or {}
    una = lec.get('si_solo_hay_tiempo') or ''
    e = lambda s: html.escape(str(s or ''))
    return f"""<div style="font-family:Arial,sans-serif;max-width:620px;color:#0b0d11;line-height:1.5">
<p style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#5a6070;margin:0 0 6px">
Brief de {e(meta.get('cliente'))} · {e(v.get('desde'))} a {e(v.get('hasta'))}</p>
<h2 style="font-size:19px;margin:0 0 14px">{e(b.get('titular'))}</h2>
{f'<p style="margin:0 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#2b5672"><b>Si solo hay tiempo para una cosa</b></p><p style="margin:0 0 16px">{e(una)}</p>' if una else ''}
<p style="margin:0 0 6px">Adjuntos: el <b>PDF</b> para leerlo y el <b>Word</b> para reescribirlo.</p>
<p style="margin:16px 0 0;padding:10px 12px;background:#fbf9f2;border-left:3px solid #8a6d1c;font-size:13px">
Es un <b>borrador para revisión</b>. Revísalo antes de mandarlo al cliente:
lo escribió un modelo sobre el barrido de Caudal.</p>
</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json', help='el brief en JSON (de brief.py)')
    ap.add_argument('archivos', nargs='+', help='los .pdf y .docx a adjuntar')
    ap.add_argument('--para', default=os.environ.get('BRIEF_PARA', ''),
                    help='destinatarios separados por coma (o BRIEF_PARA)')
    a = ap.parse_args()

    token = os.environ.get('CAUDAL_BRIEFS_TOKEN', '').strip()
    if not token:
        sys.exit('falta CAUDAL_BRIEFS_TOKEN en el entorno')
    para = [x.strip() for x in a.para.split(',') if x.strip()]
    if not para:
        sys.exit('falta destinatario: --para o BRIEF_PARA')

    b = json.load(open(a.json, encoding='utf-8'))
    meta = b.get('_meta') or {}
    adjuntos = []
    for ruta in a.archivos:
        with open(ruta, 'rb') as fh:
            adjuntos.append({'nombre': os.path.basename(ruta),
                             'base64': base64.b64encode(fh.read()).decode('ascii')})

    hasta = (meta.get('ventana') or {}).get('hasta', '')
    payload = {
        'asunto': f"Caudal · Brief de 72 horas · {meta.get('cliente', 'cliente')} · {hasta}",
        'html': cuerpo_html(b),
        'para': para,
        'etiqueta': f"brief-{(meta.get('cliente') or 'cliente').lower()}-{hasta}",
        'adjuntos': adjuntos,
    }
    req = urllib.request.Request(
        WORKER + RUTA, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': UA,
                 'X-Caudal-Briefs': token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as err:
        cuerpo = err.read().decode('utf-8', 'replace')[:400]
        # 404 sin más detalle = la ruta no reconoció el token (o el worker no
        # tiene el secreto): responde igual que una ruta inexistente a propósito.
        pista = (' · el worker no reconoce el token: revisar CAUDAL_BRIEFS_TOKEN '
                 'en el repo y en Cloudflare' if err.code == 404 else '')
        sys.exit(f'el worker respondió {err.code}: {cuerpo}{pista}')

    if not d.get('ok'):
        sys.exit(f"no se mandó: {d.get('error')} · rechazados: {d.get('rechazados')}")
    print(f"mandado a {len(d.get('entregado') or [])} · "
          f"{len(adjuntos)} adjuntos · id {d.get('id')}")
    for r in d.get('rechazados') or []:
        # no es un fallo: el worker solo entrega a quien tiene acceso a Caudal
        print(f"  rechazado {r.get('correo')}: {r.get('motivo')}")


if __name__ == '__main__':
    main()
