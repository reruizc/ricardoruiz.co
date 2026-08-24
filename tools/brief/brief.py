#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brief matutino personal de Ricardo.

NO es un monitor nuevo: lee lo que los crons existentes ya producen y lo
convierte en tres respuestas, cada mañana:

  1. ¿Algo está roto?      → estado.json del chequeo de salud del pipeline
  2. ¿Qué se movió?        → último digest de alertas de Caudal + radicados en vivo
  3. ¿Cuál es LA tarea?    → criterio fijo de prioridades (editable abajo)

Salida: Markdown en `Bases de datos/brief/brief-YYYY-MM-DD.md` (gitignored)
+ correo vía el transporte de alertas (sender.py decide Resend directo o
worker rr-auth; si ninguno sirve, el brief queda en disco igual).

Deliberadamente sin LLM y sin fuentes nuevas: v1 es determinista.
Correr a mano: python3 tools/brief/brief.py [--sin-correo]
"""

import argparse
import datetime as dt
import html as html_mod
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ESTADO = os.path.join(REPO, 'Bases de datos', 'leyes-senado', 'diario', 'estado.json')
EN_VIVO = os.path.join(REPO, 'Bases de datos', 'leyes-senado', 'en-vivo', 'en-vivo.json')
DIGESTS = os.path.join(REPO, 'tools', 'caudal', 'alertas', 'datos', 'digests')
SALIDA = os.path.join(REPO, 'Bases de datos', 'brief')
DESTINATARIO = 'hola@ricardoruiz.co'

# ---------------------------------------------------------------------------
# EL CRITERIO — esto es lo que Ricardo edita cuando cambie la situación.
# Regla de fondo: ¿factura en 90 días o alimenta algo que factura?
# ---------------------------------------------------------------------------
PRIORIDADES = [
    ('DNP', 'Único ingreso. Entregables del contrato primero, sin culpa.'),
    ('Caudal · acceso comercial', 'Bloqueador #1: cablear planes/pagos al gate '
     '(hoy son 3 correos hardcodeados). Es lo que convierte la plataforma en factura.'),
    ('Marketing / contenido', 'Contralor, legislativo público, videos, redes: '
     'tiempo ACOTADO — máximo medio día a la semana en total.'),
]
RECORDATORIO = ('Antes de abrir un frente nuevo hoy: ¿factura en 90 días '
                'o alimenta algo que factura? Si no, va a la lista de "después".')

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _carga(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'_error': f'{type(e).__name__}: {e}'}


def _horas_desde(iso):
    """Horas desde un timestamp ISO (tolerante con tz)."""
    if not iso:
        return None
    try:
        t = dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        ahora = dt.datetime.now(t.tzinfo) if t.tzinfo else dt.datetime.now()
        return (ahora - t).total_seconds() / 3600.0
    except Exception:
        return None


def seccion_salud(estado):
    """1. ¿Algo está roto?  → (lineas, hay_problemas, tareas_urgentes)"""
    if '_error' in estado:
        return ([f'No pude leer estado.json ({estado["_error"]}) — '
                 'el chequeo de salud mismo puede estar caído.'], True,
                ['Revisar por qué no existe/lee estado.json (¿cron caído?)'])
    lineas, urgentes = [], []
    glob = estado.get('estado', '?')
    h = _horas_desde(estado.get('generado'))
    edad = f'hace {h:.0f} h' if h is not None else 'sin fecha'
    problemas = estado.get('problemas') or []
    corrida = estado.get('corrida') or {}
    if glob == 'ok' and not problemas:
        dur = corrida.get('duracion_s')
        dur_txt = f' · corrida completa en {dur // 60} min' if dur else ''
        lineas.append(f'Todo en verde ({edad}){dur_txt}.')
    else:
        lineas.append(f'Estado global: {glob.upper()} ({edad}).')
        for p in problemas:
            txt = p if isinstance(p, str) else json.dumps(p, ensure_ascii=False)
            lineas.append(f'⚠ {txt}')
            urgentes.append(txt)
    for et in corrida.get('fallaron') or []:
        lineas.append(f'⚠ Etapa fallida anoche: {et}')
        urgentes.append(f'Etapa fallida: {et}')
    avisaron = corrida.get('avisaron') or []
    if avisaron:
        lineas.append(f'Avisos (no urgentes): {", ".join(str(a) for a in avisaron[:5])}')
    if h is not None and h > 26:
        lineas.append('⚠ La última corrida del rastreo tiene más de 26 h — '
                      'puede que el Mac estuviera dormido o el cron caído.')
        urgentes.append('Rastreo diario atrasado (>26 h)')
    return lineas, bool(urgentes), urgentes


def _ultimo_digest():
    try:
        dias = sorted(d for d in os.listdir(DIGESTS)
                      if os.path.isdir(os.path.join(DIGESTS, d)))
    except FileNotFoundError:
        return None, None
    for d in reversed(dias):
        p = os.path.join(DIGESTS, d, 'digest.json')
        if os.path.exists(p):
            return d, _carga(p)
    return None, None


def seccion_movimiento(en_vivo):
    """2. ¿Qué se movió?"""
    lineas = []
    fecha_dig, dig = _ultimo_digest()
    if dig and '_error' not in dig:
        total, altos = dig.get('total'), dig.get('altos')
        if total is not None:
            lineas.append(f'Alertas de Caudal (digest del {fecha_dig}): '
                          f'{total} señales, {altos or 0} altas.')
        sect = dig.get('sectores') or {}
        con_altos = sorted(((v.get('nombre', k), v.get('altos', 0), v.get('total', 0))
                            for k, v in sect.items() if v.get('altos')),
                           key=lambda x: -x[1])[:4]
        for nom, a, t in con_altos:
            lineas.append(f'  · {nom}: {a} altas de {t}')
        for av in (dig.get('avisos') or [])[:3]:
            txt = av.get('texto') if isinstance(av, dict) else str(av)
            if txt:
                lineas.append(f'  · aviso: {txt}')
    else:
        lineas.append('Sin digest de alertas legible (el motor corre lunes y viernes).')

    if en_vivo and '_error' not in en_vivo:
        h = _horas_desde(en_vivo.get('actualizado'))
        edad = f'hace {h:.0f} h' if h is not None else ''
        lineas.append(f'Radicados en vivo ({edad}):')
        for cam, rot in (('senado', 'Senado'), ('camara', 'Cámara')):
            for it in (en_vivo.get(cam) or [])[:2]:
                tit = (it.get('titulo') or '').strip()
                if len(tit) > 110:
                    tit = tit[:110].rsplit(' ', 1)[0] + '…'
                lineas.append(f'  · {rot} {it.get("numero", "?")} ({it.get("fecha", "")}): {tit}')
    return lineas


def seccion_tarea(hay_problemas, urgentes):
    """3. La tarea del día."""
    lineas = []
    if hay_problemas:
        lineas.append('PRIMERO (antes de cualquier plan): la operación está rota — '
                      'arreglar y solo después seguir con el día:')
        for u in urgentes[:5]:
            lineas.append(f'  · {u}')
        lineas.append('')
    for i, (titulo, detalle) in enumerate(PRIORIDADES, 1):
        lineas.append(f'{i}. {titulo} — {detalle}')
    lineas.append('')
    lineas.append(RECORDATORIO)
    return lineas


def construir():
    hoy = dt.date.today()
    fecha_larga = f'{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}'
    estado = _carga(ESTADO)
    en_vivo = _carga(EN_VIVO)

    s1, hay_prob, urgentes = seccion_salud(estado)
    s2 = seccion_movimiento(en_vivo)
    s3 = seccion_tarea(hay_prob, urgentes)

    md = [f'# Brief · {fecha_larga}', '']
    md += ['## 1 · ¿Algo roto?', ''] + [f'- {l}' if not l.startswith(' ') else l for l in s1]
    md += ['', '## 2 · ¿Qué se movió?', ''] + [f'- {l}' if not l.startswith(' ') else l for l in s2]
    md += ['', '## 3 · La tarea del día', ''] + s3
    md += ['', '---', '_Generado por tools/brief/brief.py — edita PRIORIDADES ahí '
           'cuando cambie el criterio._']
    markdown = '\n'.join(md) + '\n'

    # HTML sencillo para el correo (clientes de correo, no el sistema visual v2)
    def esc(t):
        return html_mod.escape(t)

    def bloque(titulo, lineas):
        items = ''.join(f'<li style="margin:.25em 0">{esc(l)}</li>' for l in lineas if l.strip())
        return (f'<h3 style="margin:1.2em 0 .3em;color:#0047FF">{esc(titulo)}</h3>'
                f'<ul style="margin:0;padding-left:1.2em;color:#1a1a2e">{items}</ul>')

    html = (f'<div style="font-family:-apple-system,Helvetica,Arial,sans-serif;'
            f'max-width:640px;font-size:15px;line-height:1.45">'
            f'<h2 style="margin:0 0 .2em">Brief · {esc(fecha_larga)}</h2>'
            + bloque('1 · ¿Algo roto?', s1)
            + bloque('2 · ¿Qué se movió?', s2)
            + bloque('3 · La tarea del día', s3)
            + '<p style="color:#888;font-size:12px;margin-top:1.5em">'
              'tools/brief/brief.py · edita PRIORIDADES ahí cuando cambie el criterio.</p>'
            '</div>')

    asunto = f'Caudal · Brief matutino · {hoy.day} {MESES[hoy.month - 1][:3]}'
    return hoy, asunto, markdown, html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sin-correo', action='store_true',
                    help='solo escribe el .md, no envía')
    args = ap.parse_args()

    hoy, asunto, markdown, html = construir()
    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, f'brief-{hoy.isoformat()}.md')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f'brief escrito: {ruta}')

    if args.sin_correo:
        return 0

    # Reusar el transporte de alertas (decide Resend directo vs worker rr-auth)
    sys.path.insert(0, os.path.join(REPO, 'tools', 'caudal', 'alertas'))
    try:
        import sender  # noqa: E402
        res = sender.enviar(asunto, html, markdown, [DESTINATARIO],
                            etiqueta='brief', dir_salida=SALIDA)
        print(f'envío: {res}')
    except Exception as e:
        print(f'no se pudo enviar ({type(e).__name__}: {e}) — el brief queda en disco')
        return 0  # el brief en disco ya es éxito; el correo es el extra
    return 0


if __name__ == '__main__':
    sys.exit(main())
