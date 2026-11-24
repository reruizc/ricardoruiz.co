#!/usr/bin/env python3
"""Junta transcripcion.md (tramos de 2 min) con oradores.tsv (rótulo leído por OCR).
Uso: python3 unir.py <carpeta>  → transcripcion-con-oradores.md
Cada tramo queda encabezado por quién(es) estaba(n) en el rótulo durante esos 2 minutos.
"""
import sys, re, pathlib
d = pathlib.Path(sys.argv[1])
import unicodedata
def sin_tilde(x):
    return ''.join(c for c in unicodedata.normalize('NFD', x.upper()) if unicodedata.category(c) != 'Mn')
def mins(hhmm):
    h, m = hhmm.split(':')[:2]; return int(h) * 60 + int(m)
oradores = []  # (minuto, hora, nombre, org)
for ln in sorted((d / 'oradores.tsv').read_text().splitlines(), key=lambda l: int(l.split('\t')[0]) if l.split('\t')[0].isdigit() else 0) if (d / 'oradores.tsv').exists() else []:
    p = ln.split('\t')
    # descartar lecturas sin letras (el OCR leyó solo el cronómetro) y repeticiones
    # del mismo nombre con o sin tilde
    if len(p) >= 3 and re.search(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]', p[2]):
        if oradores and sin_tilde(oradores[-1][2]) == sin_tilde(p[2]):
            continue
        oradores.append((mins(p[1]) + int(p[1].split(':')[2]) / 60, p[1], p[2], p[3] if len(p) > 3 else ''))
txt = (d / 'transcripcion.md').read_text()
tramos = re.findall(r'^## (\d\d:\d\d)\n(.*?)(?=^## |\Z)', txt, re.M | re.S)
# los tramos recuperados después de un corte se anexan al final: ordenar por hora
tramos.sort(key=lambda t: mins(t[0]))
# un tramo recuperado y el del vivo pueden caer en el mismo minuto: dejar el más largo
_u = {}
for h, c in tramos:
    if h not in _u or len(c) > len(_u[h]): _u[h] = c
tramos = sorted(_u.items(), key=lambda t: mins(t[0]))
out = ['# Audiencia con oradores (rótulo del Canal Congreso por OCR + Whisper)', '']
previo = None
for hora, cuerpo in tramos:
    a = mins(hora); b = a + 2
    # quien estaba al empezar el tramo + quienes entraron durante él
    antes = [o for o in oradores if o[0] <= a]
    dentro = [o for o in oradores if a < o[0] < b]
    quien = ([antes[-1]] if antes else []) + dentro
    nombres = ' → '.join(f'{o[2]} ({o[3]})' if o[3] else o[2] for o in quien) or 'sin rótulo'
    if nombres != previo:
        out.append(f'### {nombres}')
        previo = nombres
    out.append(f'**{hora}** {cuerpo.strip()}')
    out.append('')
(d / 'transcripcion-con-oradores.md').write_text('\n'.join(out))
print(f'{len(tramos)} tramos · {len(oradores)} cambios de orador')
