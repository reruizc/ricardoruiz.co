#!/usr/bin/env python3
"""
Caudal · pilar «Diarios y gacetas oficiales» — índice de la Gaceta del Congreso
para la Lambda (metadata/gacetas.json).

Une tres cosas que ya existían por separado:
  · gacetas-index.jsonl   las 31k gacetas enumeradas del portal de la Imprenta
                          (num · entidad · fecha), con el año de 2 dígitos ya
                          corregido al leer.
  · proyectos.jsonl +     qué proyecto cita cada gaceta y como qué documento
    actos-legis.jsonl     (exposición de motivos, ponencia, texto de plenaria…).
  · gacetas-texto/ en S3  cuáles ya tienen el texto extraído (para decir
                          "se puede leer en Caudal" sin adivinar).

Salida compacta (una gaceta = una lista, sin llaves repetidas 31k veces):
  items: [num, anio, fecha, ent('S'|'C'), texto(0|1), [[tb(0 pdly|1 pal), id, tipo_doc]…]]

Uso:
  aws s3 ls s3://caudal-legislativo/gacetas-texto/ | awk '{print $4}' > /tmp/gacetas_texto_keys.txt
  python3 tools/caudal/gacetas/build_gacetas_s3.py [--keys /tmp/gacetas_texto_keys.txt]
  aws s3 cp "Bases de datos/leyes-senado/dist/s3/gacetas.json" s3://caudal-legislativo/metadata/gacetas.json
"""
import json, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LS = REPO / 'Bases de datos' / 'leyes-senado'
IDX = LS / 'actas' / 'gacetas-index.jsonl'
DIST = LS / 'dist'
OUT = DIST / 's3' / 'gacetas.json'
KEYS = Path(sys.argv[sys.argv.index('--keys') + 1]) if '--keys' in sys.argv else Path('/tmp/gacetas_texto_keys.txt')

TIPO_DOC = {'exposicion_motivos': 'em', 'ponencia_1': 'p1', 'ponencia_2': 'p2', 'ponencia_3': 'p3',
            'ponencia_4': 'p4', 'texto_plenaria': 'tp', 'texto_aprobado': 'ta', 'conciliacion': 'co',
            'objeciones': 'ob', 'texto_definitivo': 'td'}

def fecha_ok(f):
    """El índice guardó 2 filas con año de 2 dígitos como '0009-…'. Se corrigen
    al leer; lo que no sea una fecha 2001-2030 se descarta y se cuenta."""
    m = re.match(r'^(\d{1,4})-(\d{2})-(\d{2})$', f or '')
    if not m:
        return None
    y = int(m.group(1))
    if y < 100:
        y += 2000
    if not (2000 <= y <= 2030):
        return None
    return f'{y:04d}-{m.group(2)}-{m.group(3)}'

def main():
    gac, descartadas = {}, 0
    for line in open(IDX, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        f = fecha_ok(r.get('fecha'))
        if not f:
            descartadas += 1
            continue
        num, anio = int(r['num']), int(f[:4])
        ent = 'C' if 'mara' in (r.get('entidad') or '').lower() else 'S'
        k = (num, anio)
        # la numeración es UNA por año (Senado+Cámara comparten): si el portal
        # lista la misma gaceta dos veces, gana la fecha más antigua (publicación)
        if k not in gac or f < gac[k]['fecha']:
            gac[k] = {'num': num, 'anio': anio, 'fecha': f, 'ent': ent}

    # texto disponible en S3: {num}-{anio}.txt
    con_texto = set()
    if KEYS.exists():
        for line in open(KEYS, encoding='utf-8'):
            m = re.match(r'^(\d+)-(\d{4})\.txt$', line.strip())
            if m:
                con_texto.add((int(m.group(1)), int(m.group(2))))
    else:
        print(f'  ! sin {KEYS}: todas las gacetas salen sin texto', file=sys.stderr)

    # proyectos que citan cada gaceta
    citas = defaultdict(list)
    tipos = Counter()
    for tb, fn in ((0, 'proyectos.jsonl'), (1, 'actos-legis.jsonl')):
        for line in open(DIST / fn, encoding='utf-8'):
            if not line.strip():
                continue
            p = json.loads(line)
            for g in p.get('gacetas') or []:
                m = re.match(r'^(\d+)/(\d{2,4})$', str(g.get('gaceta') or ''))
                if not m:
                    continue
                num, y = int(m.group(1)), int(m.group(2))
                if y < 100:
                    y += 1900 if y >= 90 else 2000
                td = TIPO_DOC.get(g.get('tipo'), g.get('tipo') or '')
                tipos[td] += 1
                citas[(num, y)].append([tb, int(p['id']), td])

    # gacetas citadas por el dataset que el enumerador no trae (pre-2001 o hueco)
    solo_citadas = 0
    for k, lst in citas.items():
        if k not in gac:
            solo_citadas += 1
            gac[k] = {'num': k[0], 'anio': k[1], 'fecha': '', 'ent': ''}

    items = []
    for k, g in gac.items():
        items.append([g['num'], g['anio'], g['fecha'], g['ent'],
                      1 if k in con_texto else 0, citas.get(k, [])])
    items.sort(key=lambda x: (x[2] or f"{x[1]:04d}-00-00", x[0]), reverse=True)

    fechas = [x[2] for x in items if x[2]]
    por_anio = Counter(x[1] for x in items)
    out = {
        'v': time.strftime('%Y-%m-%d'),
        'n': len(items),
        'n_enumeradas': len(fechas),
        'n_solo_citadas': solo_citadas,
        'descartadas_fecha': descartadas,
        'rango': [min(fechas), max(fechas)] if fechas else ['', ''],
        'con_texto': sum(1 for x in items if x[4]),
        'con_proyectos': sum(1 for x in items if x[5]),
        'por_anio': {str(a): por_anio[a] for a in sorted(por_anio)},
        'tipos_doc': dict(tipos),
        'fuente': {'nombre': 'Gaceta del Congreso · Imprenta Nacional',
                   'url': 'https://svrpubindc.imprenta.gov.co/senado/'},
        'items': items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"ok {OUT.name}: {out['n']:,} gacetas ({out['n_enumeradas']:,} con fecha · {solo_citadas} solo citadas · "
          f"{descartadas} descartadas por fecha) · {out['con_texto']:,} con texto · {out['con_proyectos']:,} con proyectos · "
          f"{OUT.stat().st_size/1e6:.1f} MB · rango {out['rango']}")
    print('  tipos_doc:', dict(tipos))

if __name__ == '__main__':
    main()
