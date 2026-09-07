#!/usr/bin/env python3
"""Compara dos cachés de extracción del articulado (p.ej. DeepSeek vs modelo
local) sobre los proyectos que AMBOS leyeron. Mide, por campo, cuánto encuentra
cada uno y cuánto coincide — no quién "tiene razón": sin etiqueta humana, la
referencia es la nube (ya validada a mano en el caso 058/26).

  python3 tools/caudal/analisis/comparar_backends.py <dir_ref> <dir_local> [--n 20]
"""
import json, re, sys, unicodedata
from pathlib import Path


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', s).strip()


def toks(s):
    return {w for w in norm(s).split() if len(w) > 3}


def parecido(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / max(1, len(ta | tb))


def casan(lista_a, lista_b, campo, umbral=0.35):
    """Cuántos ítems de A tienen un par en B (Jaccard de tokens sobre `campo`)."""
    usados, n = set(), 0
    for a in lista_a:
        for j, b in enumerate(lista_b):
            if j in usados:
                continue
            if parecido(a.get(campo), b.get(campo)) >= umbral:
                usados.add(j); n += 1; break
    return n


CAMPOS = [('obligaciones', 'obligacion'), ('sanciones', 'conducta'),
          ('modifica', 'norma'), ('vigilancia', 'entidad')]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    n_max = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 10**9
    ref, loc = Path(args[0]), Path(args[1])
    comunes = sorted({p.name for p in ref.glob('*.json')} & {p.name for p in loc.glob('*.json')})[:n_max]
    if not comunes:
        print('sin proyectos en común'); return
    tot = {c: [0, 0, 0] for c, _ in CAMPOS}   # [ref encontró, local encontró, local casó con ref]
    conf = {'ref': {}, 'loc': {}}
    vac = {'ref': 0, 'loc': 0}
    sect_ok = 0
    tk = {'ref': [0, 0], 'loc': [0, 0]}
    ms = 0.0
    for nombre in comunes:
        a = json.load(open(ref / nombre, encoding='utf-8'))
        b = json.load(open(loc / nombre, encoding='utf-8'))
        for c, campo in CAMPOS:
            la, lb = a.get(c) or [], b.get(c) or []
            tot[c][0] += len(la); tot[c][1] += len(lb); tot[c][2] += casan(la, lb, campo)
        for k, d in (('ref', a), ('loc', b)):
            conf[k][d.get('confianza')] = conf[k].get(d.get('confianza'), 0) + 1
            if not d.get('resumen'):
                vac[k] += 1
            m = d.get('_meta') or {}
            tk[k][0] += m.get('tok_in', 0); tk[k][1] += m.get('tok_out', 0)
        sa = set((a.get('aplica_a') or {}).get('sectores') or [])
        sb = set((b.get('aplica_a') or {}).get('sectores') or [])
        if sa and sb and (sa & sb):
            sect_ok += 1
        ms += ((b.get('_meta') or {}).get('eval_ms') or 0) + ((b.get('_meta') or {}).get('prompt_ms') or 0)
    n = len(comunes)
    print(f'{n} proyectos leídos por los dos\n')
    print(f'{"campo":<14}{"ref":>8}{"local":>8}{"local≈ref":>11}  {"cobertura":>10}')
    for c, _ in CAMPOS:
        r, l, m = tot[c]
        print(f'{c:<14}{r:>8}{l:>8}{m:>11}  {m/max(1,r):>9.0%}')
    print(f'\nsectores con al menos uno en común: {sect_ok}/{n}')
    print(f'sin resumen: ref {vac["ref"]} · local {vac["loc"]}')
    print(f'confianza ref {conf["ref"]} · local {conf["loc"]}')
    print(f'tokens ref in/out {tk["ref"][0]:,}/{tk["ref"][1]:,} · local {tk["loc"][0]:,}/{tk["loc"][1]:,}')
    if ms:
        print(f'tiempo local: {ms/1000/n:.0f} s por documento (solo inferencia)')


if __name__ == '__main__':
    main()
