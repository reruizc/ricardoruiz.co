#!/usr/bin/env python3
"""Genera articulos.json: los 106 artículos del PL 477 con su página, rótulo y tema.

  python3 tools/ley-rescate/build_articulos.py

Recorre el texto extraído del PDF radicado en secuencia, porque los artículos citan
otros artículos de otras leyes («Artículo 21. El Fondo…») y buscar por número suelto
agarra el que no es.
"""
import bisect
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
TXT = REPO / 'Bases de datos/video-semanal/2026-10-30/pl477.txt'


def rotulo(frag):
    frag = re.sub(r'\s+', ' ', frag).strip()
    m = re.match(r'(Modifíquese|Modifíquense|Adiciónese|Adiciónense|A partir de|Créase|Créese)', frag)
    if m:
        return frag[:150].rstrip(' ,;:') + '…'
    return frag.split('. ')[0][:150]


def main():
    t = TXT.read_text(errors='ignore')
    paginas = t.split('\f')
    ofs, c = [], 0
    for p in paginas:
        ofs.append(c)
        c += len(p) + 1
    temas = json.loads((AQUI / 'temas.json').read_text())
    tema_de = {}
    for x in temas['temas']:
        for a in x['arts']:
            tema_de.setdefault(a, []).append(x['id'])
    pos, out = ofs[213], []
    for n in range(1, 107):
        m = re.compile(r'(?m)^\s*Art[ií]culo\s+%d\s*[\.°ºo]' % n).search(t, pos)
        if not m:
            m = re.compile(r'(?i)art[ií]culo\s+%d\s*[\.°ºo]' % n).search(t, pos)
        pos = m.end()
        out.append({'n': n, 'pag': bisect.bisect_right(ofs, m.start()), 'r': rotulo(t[m.end():m.end() + 260]),
                    'temas': tema_de.get(n, [])})
    assert len(out) == 106
    sin = [a['n'] for a in out if not a['temas']]
    assert set(sin) <= set(temas['sin_tema']), sin
    (AQUI / 'articulos.json').write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print('106 artículos ·', sum(1 for a in out if a['temas']), 'con tema · sin tema:', sin)


if __name__ == '__main__':
    main()
