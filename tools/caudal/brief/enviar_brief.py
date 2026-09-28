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
import re
import os
import sys
import urllib.error
import urllib.request

WORKER = os.environ.get('CAUDAL_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
RUTA = '/caudal/briefs/enviar'
UA = 'caudal-briefs/1.0 (+ricardoruiz.co)'


MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')
# Colores del PDF, para que el correo y el adjunto se lean como la misma pieza.
TINTA, GRIS, AZUL, PAPEL, LINEA = '#0b0d11', '#5a6070', '#2b5672', '#fbfaf8', '#e2e5ea'
URGENCIA = {'alta': ('#d9480f', 'Urgente'), 'media': ('#2b5672', 'Atento'),
            'baja': ('#6b7280', 'Para saber')}


def _fecha_larga(iso, relativa=False):
    """«28 de septiembre», o «hoy» / «ayer» / «mañana» con `relativa`.

    Lo relativo se calcula contra el día en que SE MANDA el correo, no contra la
    fecha del brief: el lunes se revisa y puede salir el martes, y un «hoy»
    atado a la fecha del brief ya sería mentira.
    """
    import datetime
    try:
        f = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso or '')
    if relativa:
        dif = (f - datetime.date.today()).days
        if dif in (-1, 0, 1):
            return ('ayer', 'hoy', 'mañana')[dif + 1]
    return f"{f.day} de {MESES[f.month - 1]}"


_ISO = re.compile(r'(\(?)\b(?:([Ee]l|[Dd]el|[Aa]l)\s+)?(\d{4}-\d{2}-\d{2})\b(\)?)')


def _fechas_en_texto(txt):
    """El brief escribe «El 2026-09-28 el presidente…», que en el PDF se audita
    pero en un correo se lee como un formulario. Pasa a «Hoy el presidente…»."""
    def cambiar(m):
        par, art, iso, cierre = m.groups()
        # Con «del»/«al» la fecha va escrita: «antes del 27» pasado a relativo
        # daría «antes de ayer», que en español significa anteayer.
        relativa = not (art and art.lower() in ('del', 'al'))
        fecha = _fecha_larga(iso, relativa=relativa)
        if fecha in ('hoy', 'ayer', 'mañana'):
            if art and art[0].isupper():
                fecha = fecha[0].upper() + fecha[1:]
            return f"{par}{fecha}{cierre}"
        return f"{par}{art + ' ' if art else ''}{fecha}{cierre}"
    return _ISO.sub(cambiar, str(txt or ''))


def momento(iso):
    """«Inicio de la semana» el lunes, «Cierre de la semana» el viernes."""
    import datetime
    try:
        dia = datetime.date.fromisoformat(str(iso)[:10]).isoweekday()
    except ValueError:
        return 'Lo de estos días'
    return {1: 'Inicio de la semana', 5: 'Cierre de la semana'}.get(dia, 'Lo de estos días')


def asunto(b):
    meta = b.get('_meta') or {}
    hasta = (meta.get('ventana') or {}).get('hasta', '')
    return f"Caudal · {momento(hasta)} · {meta.get('cliente', 'cliente')} · {_fecha_larga(hasta)}"


def cuerpo_html(b):
    """El correo que acompaña al brief, con el formato de un boletín: saludo,
    portada con la lectura de la ventana, las cifras en un vistazo, los temas en
    una línea cada uno y lo que viene. Lo largo va en los adjuntos.

    ⚠️ Solo tablas y estilos en línea: Gmail y Outlook ignoran <style>, flexbox y
    grid, y un correo que se ve roto en el teléfono del cliente no se lee. Sin
    imágenes: no hay dónde alojarlas con URL pública desde el workflow, y una
    imagen rota arriba de todo es peor que ninguna.
    """
    meta = b.get('_meta') or {}
    v = meta.get('ventana') or {}
    cliente = meta.get('cliente') or 'equipo'
    lec = b.get('lectura') or {}
    temas_todos = b.get('temas') or []
    temas = temas_todos[:3]     # los tres primeros: el resto está en el PDF
    agenda = [x for x in (b.get('agenda') or []) if x.get('que')][:4]
    una = lec.get('si_solo_hay_tiempo') or ''
    e = lambda x: html.escape(_fechas_en_texto(x))
    n_alta = sum(1 for t in temas_todos if t.get('urgencia') == 'alta')
    img = meta.get('imagen') or {}

    def cifra(n, rotulo, color=AZUL):
        return (f'<td align="center" width="33%" style="padding:0 6px">'
                f'<div style="background:{color};color:#fff;border-radius:10px;'
                f'padding:10px 4px;font-size:22px;font-weight:bold">{n}</div>'
                f'<div style="font-size:12px;color:{GRIS};padding-top:6px">{rotulo}</div></td>')

    cifras = (cifra(len(temas_todos), 'temas') + cifra(n_alta, 'urgentes', '#d9480f')
              + cifra(len(b.get('agenda') or []), 'fechas por venir'))

    filas_temas = ''
    for t in temas:
        color, rot = URGENCIA.get(t.get('urgencia'), URGENCIA['baja'])
        filas_temas += (
            f'<tr><td style="padding:10px 0;border-top:1px solid {LINEA}">'
            f'<span style="font-size:11px;font-weight:bold;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{color}">{e(rot)} · {e(t.get("rotulo"))}</span><br>'
            f'<span style="font-size:15px;color:{TINTA}">{e(t.get("titulo"))}</span></td></tr>')

    filas_agenda = ''.join(
        f'<tr><td style="padding:6px 12px 6px 0;font-size:13px;font-weight:bold;'
        f'color:{AZUL};white-space:nowrap;vertical-align:top">{e(_fecha_larga(x.get("iso"), relativa=True).capitalize())}</td>'
        f'<td style="padding:6px 0;font-size:14px;color:{TINTA}">{e(x.get("que"))}</td></tr>'
        for x in agenda)

    parrafo = (lec.get('parrafos') or [''])[0]
    # La foto va ENLAZADA desde el servidor del medio, no copiada, con su
    # crédito debajo. Ver imagen_prensa.py sobre derechos.
    foto = credito = ''
    if img.get('src'):
        foto = (f'<tr><td style="padding:0;font-size:0;line-height:0">'
                f'<img src="{html.escape(img["src"])}" width="564" alt="{html.escape(img.get("titulo", ""))}" '
                f'style="display:block;width:100%;max-width:564px;height:auto;border-radius:12px 12px 0 0">'
                f'</td></tr>')
        credito = (f'<div style="font-size:11px;color:{GRIS};padding-top:6px">Foto: '
                   f'{html.escape(img.get("medio", ""))} · <a href="{html.escape(img.get("enlace", ""))}" '
                   f'style="color:{GRIS}">{html.escape((img.get("titulo") or "")[:90])}</a></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:0;background:#f1f2f4">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f2f4">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:#ffffff;border-radius:14px;font-family:Helvetica,Arial,sans-serif;color:{TINTA};line-height:1.5">

<tr><td style="padding:26px 28px 6px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:{GRIS}">
<b style="color:{TINTA}">Caudal</b> &nbsp;×&nbsp; {e(cliente)}</td></tr>

<tr><td style="padding:4px 28px 0">
<div style="font-size:30px;font-weight:bold;color:{TINTA}">¡Hola, {e(cliente)}!</div>
<div style="font-size:17px;font-style:italic;color:{AZUL};padding-top:2px">{e(momento(v.get('hasta')))}</div>
</td></tr>

<tr><td style="padding:18px 28px 0">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{TINTA};border-radius:12px">
{foto}<tr><td style="padding:22px 24px 24px">
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#9fb6c8">
Del {e(_fecha_larga(v.get('desde')))} al {e(_fecha_larga(v.get('hasta')))}</div>
<div style="font-size:22px;font-weight:bold;color:#ffffff;line-height:1.3;padding-top:8px">{e(lec.get('titulo') or b.get('titular'))}</div>
</td></tr></table>{credito}</td></tr>

<tr><td style="padding:22px 22px 4px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{cifras}</tr></table></td></tr>

{f'<tr><td style="padding:18px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPEL};border-left:4px solid {AZUL};border-radius:6px"><tr><td style="padding:14px 16px"><div style="font-size:11px;font-weight:bold;letter-spacing:.08em;text-transform:uppercase;color:{AZUL}">Si solo tienes tiempo para una cosa</div><div style="font-size:15px;padding-top:4px">{e(una)}</div></td></tr></table></td></tr>' if una else ''}

<tr><td style="padding:18px 28px 0;font-size:15px">{e(parrafo)}</td></tr>

<tr><td style="padding:26px 28px 0;font-size:19px;font-weight:bold">Los temas de la semana</td></tr>
<tr><td style="padding:6px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_temas}</table></td></tr>

{f'<tr><td style="padding:24px 28px 0;font-size:19px;font-weight:bold">Lo que viene</td></tr><tr><td style="padding:6px 28px 0"><table role="presentation" cellpadding="0" cellspacing="0">{filas_agenda}</table></td></tr>' if filas_agenda else ''}

<tr><td style="padding:24px 28px 0;font-size:14px;color:{GRIS}">
El brief completo va adjunto: el <b style="color:{TINTA}">PDF</b> para leerlo y el
<b style="color:{TINTA}">Word</b> para reescribirlo.</td></tr>

<tr><td style="padding:16px 28px 28px">
<div style="padding:10px 12px;background:#fbf9f2;border-left:3px solid #8a6d1c;font-size:12px;color:{GRIS}">
Es un <b>borrador para revisión</b>: lo escribió un modelo sobre el barrido de Caudal.
Revísalo antes de mandarlo a un cliente.</div></td></tr>

</table></td></tr></table></body></html>"""


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
        'asunto': asunto(b),
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
