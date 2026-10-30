#!/usr/bin/env python3
"""Recorta la grabación cruda del video 1 de la Ley de Rescate: quita el silencio del inicio y del
final, acorta las pausas largas entre frases y acelera a 1,15 (voz y video juntos, sin cambiar el tono).

  python3 cortar.py [ruta-del-crudo]

Entrada: por defecto Bases de datos/30-oct-v1.mov. Salida: assets/base.mp4 en calidad alta
(CRF 14), porque la composición la vuelve a escalar y cada pasada con poca calidad se nota.
"""
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
CRUDO = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else RAIZ / 'Bases de datos' / '30-oct-v1.mov'
SALIDA = AQUI / 'assets' / 'base.mp4'
VEL = 1.15
PAUSA_MIN = 0.45   # pausas más largas que esto se acortan
DEJAR = 0.16       # segundos de aire que se dejan a cada lado de la pausa

dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                            str(CRUDO)], capture_output=True, text=True).stdout)
log = subprocess.run(['ffmpeg', '-i', str(CRUDO), '-af', 'silencedetect=n=-32dB:d=0.3', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
ini = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
fin = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
if len(fin) < len(ini):
    fin.append(dur)
sil = sorted(zip(ini, fin))

# Inicio y final: el primer y el último tramo con voz de verdad (>0,5 s seguidos).
voz = []
t = 0.0
for a, b in sil:
    if a - t > 0.5:
        voz.append((t, a))
    t = b
if dur - t > 0.5:
    voz.append((t, dur))
arranque, cierre = voz[0][0] - 0.12, voz[-1][1] + 0.35

partes, t = [], arranque
for a, b in sil:
    if a <= arranque + DEJAR or b >= cierre - DEJAR or b - a < PAUSA_MIN:
        continue
    partes.append((t, a + DEJAR))
    t = b - DEJAR
partes.append((t, cierre))
partes = [(a, b) for a, b in partes if b - a > 0.08]

f = ''.join(f'[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,'
            f'afade=t=in:d=0.02,afade=t=out:st={b - a - 0.02:.3f}:d=0.02[a{i}];' for i, (a, b) in enumerate(partes))
f += ''.join(f'[v{i}][a{i}]' for i in range(len(partes)))
f += f'concat=n={len(partes)}:v=1:a=1[vc][ac];[vc]setpts=PTS/{VEL}[v];[ac]atempo={VEL}[a]'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(CRUDO), '-filter_complex', f, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', '30',
                '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', str(SALIDA)], check=True)
quedo = sum(b - a for a, b in partes)
print(f'✓ {len(partes)} tramos · {dur:.1f} s crudo → {quedo:.1f} s sin pausas → {quedo / VEL:.1f} s a {VEL}')
