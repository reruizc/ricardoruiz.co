#!/usr/bin/env python3
"""
Caudal · voto nominal de SENADO desde la API pública de app.senado.gov.co.

Cierra el hueco que dimos por imposible: el Senado NO tiene export electrónico
tipo Bosch/DCN-SW (a diferencia de Cámara) y sus votos solo vivían en el acta
narrativa de la Gaceta — así que teníamos 391 votos de UN día, extraídos a mano.
Esta API (cortesía de Pablo Bernal / La Silla Vacía, jul-2026) entrega el voto
nominal por senador de 2017 a hoy en un solo CSV.

Endpoints (públicos, sin auth):
  /backend/api/public/v1/votes?format=csv   → 1 fila por (senador, votación)
      cols: Fecha de la Plenaria · ID Senador · Nombre del Senador ·
            ID Proyecto · Proyecto de ley · Resultado
  /backend/api/public/v1/senators?format=json → 103 senadores ACTUALES con
      party_name (partido oficial) + redes. Sus `id` NO casan con el
      `ID Senador` de los votos (ese cubre 212 personas de varios períodos)
      → el join es por NOMBRE, igual que el resto del proyecto.

LÍMITES de la fuente (verificados, van al `meta` de la salida):
  · Solo registra Sí/No — NO hay abstención ni "no votó" (Cámara sí los trae).
  · La llave (fecha, ID Proyecto) AGRUPA varias votaciones del mismo día sobre
    el mismo proyecto (se midió una con 231 votantes, con ~108 senadores) → no
    se puede separar cuál votación fue cuál. Para "cómo votó X en el proyecto Y"
    da igual; para un tally exacto por votación, no alcanza.
  · Arranca en 2017 (no cubre 1990-2016).

Uso:
  python3 tools/caudal/harvest_senado_api.py            # baja y procesa
  python3 tools/caudal/harvest_senado_api.py --cache    # reusa el CSV ya bajado
"""
import argparse
import collections
import csv
import io
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
RAW = REPO / 'Bases de datos' / 'leyes-senado' / 'senado-api'
API = 'https://app.senado.gov.co/backend/api/public/v1'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')

# el texto del proyecto trae el número; se ancla a "Senado" para no capturar el
# de Cámara ("002 de 2016 Senado, 004 de 2016 Cámara" → 2/16, no 4/16)
PROJ_SEN = re.compile(r'(\d{1,4})\s*(?:de|/|-)\s*(\d{2,4})\s*Senado', re.I)


def _curl(url, out):
    subprocess.run(['/usr/bin/curl', '-s', '-m', '180', '-A', UA, url, '-o', str(out)],
                   check=True)


def canon(nombre):
    """Clave canónica: sin tildes, MAYÚSCULAS, solo alfanum — el MISMO criterio
    de normalize_autores/build_roster, para que el join al roster funcione."""
    s = unicodedata.normalize('NFD', nombre or '').encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^A-Za-z0-9 ]', ' ', s).upper().split())


def load_roster():
    d = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))
    roster = d['roster']
    toks = {k: frozenset(k.split()) for k in roster}
    idx = {}
    for k, ts in toks.items():
        for t in ts:
            idx.setdefault(t, set()).add(k)
    return roster, toks, idx


def match_roster(key, roster, rtoks, tidx):
    """Exacto, si no subconjunto de tokens (el padrón usa el nombre legal completo
    y el Senado lo escribe 'Apellido1 Apellido2 Nombre1 Nombre2' — el frozenset
    hace el match orden-independiente)."""
    if key in roster:
        return roster[key]['partido_principal'], key, 'exacto'
    atoks = frozenset(key.split())
    if len(atoks) < 2:
        return None, None, None
    cand = None
    for t in atoks:
        s = tidx.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    sup = [k for k in (cand or ()) if atoks <= rtoks[k]]
    if not sup:
        return None, None, None
    if len(sup) == 1:
        return roster[sup[0]]['partido_principal'], sup[0], 'subset'
    partidos = {roster[k]['partido_principal'] for k in sup}
    if len(partidos) == 1:
        best = max(sup, key=lambda k: roster[k]['anio_ultimo'])
        return roster[best]['partido_principal'], best, 'subset-ambiguo'
    return None, None, 'ambiguo'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', action='store_true', help='reusa lo ya bajado en senado-api/')
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    fv, fs = RAW / 'votes.csv', RAW / 'senators.json'

    if not args.cache or not fv.exists():
        print('· bajando /votes?format=csv …')
        _curl(f'{API}/votes?format=csv', fv)
    if not args.cache or not fs.exists():
        print('· bajando /senators?format=json …')
        _curl(f'{API}/senators?format=json', fs)
    print(f'  votes.csv {fv.stat().st_size/1e6:.1f} MB · senators.json {fs.stat().st_size/1024:.0f} KB')

    rows = list(csv.DictReader(open(fv, encoding='utf-8-sig')))
    senators = json.load(open(fs, encoding='utf-8'))
    # partido OFICIAL de los senadores actuales (por nombre canónico)
    oficial = {canon(s['name']): s.get('party_name') for s in senators if s.get('name')}

    roster, rtoks, tidx = load_roster()
    cache, stats = {}, collections.Counter()
    out_rows = []
    for r in rows:
        nombre = (r.get('Nombre del Senador') or '').strip()
        resp = (r.get('Resultado') or '').strip()
        if not nombre or resp not in ('Sí', 'Si', 'No'):
            stats['descartado_sin_voto'] += 1
            continue
        key = canon(nombre)
        if key not in cache:
            partido, rk, via = match_roster(key, roster, rtoks, tidx)
            # el partido oficial de /senators manda para los senadores ACTUALES
            # (es la fuente primaria); el roster cubre los de períodos pasados.
            if oficial.get(key):
                partido, via = oficial[key], (via or '') + '+oficial' if via else 'oficial'
            cache[key] = (partido, rk, via)
        partido, rk, via = cache[key]
        stats['con_partido' if partido else 'sin_partido'] += 1
        texto = r.get('Proyecto de ley') or ''
        m = PROJ_SEN.search(texto)
        num_sen = f'{int(m.group(1))}/{m.group(2)[-2:]}' if m else None
        if num_sen:
            stats['con_proyecto'] += 1
        out_rows.append({
            'fecha': r.get('Fecha de la Plenaria'),
            'votacion_id': f"{r.get('Fecha de la Plenaria')}|{r.get('ID Proyecto')}",
            'senado_proyecto_id': r.get('ID Proyecto'),
            'proyecto_numero_senado': num_sen,
            'proyecto_titulo': re.sub(r'\s+', ' ', texto).strip()[:200],
            'senador_id': r.get('ID Senador'),
            'congresista': nombre,
            'roster_key': rk,
            'partido': partido,
            'match_via': via,
            'respuesta': 'Si' if resp in ('Sí', 'Si') else 'No',
        })

    outf = DIST / 'votaciones-senado-api.jsonl'
    with open(outf, 'w', encoding='utf-8') as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    personas = {r['congresista'] for r in out_rows}
    con_rk = {r['congresista'] for r in out_rows if r['roster_key']}
    votac = {r['votacion_id'] for r in out_rows}
    proys = {r['proyecto_numero_senado'] for r in out_rows if r['proyecto_numero_senado']}
    fechas = [r['fecha'] for r in out_rows if r['fecha']]
    st = {
        'v': '2026-07-28', 'fuente': 'app.senado.gov.co/backend/api/public/v1/votes',
        'votos': len(out_rows), 'votaciones': len(votac), 'senadores': len(personas),
        'proyectos': len(proys),
        'rango': [min(fechas), max(fechas)] if fechas else None,
        'con_partido': stats['con_partido'], 'sin_partido': stats['sin_partido'],
        'pct_con_partido': round(100 * stats['con_partido'] / max(len(out_rows), 1), 1),
        'senadores_con_roster': len(con_rk), 'senadores_total': len(personas),
        'limites': ['solo Sí/No (sin abstención ni no-votó)',
                    'la llave (fecha, proyecto) agrupa varias votaciones del mismo día',
                    'arranca en 2017'],
    }
    json.dump(st, open(DIST / 'votaciones-senado-api-stats.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\n{st['votos']:,} votos · {st['votaciones']:,} votaciones · {st['senadores']} senadores "
          f"· {st['proyectos']} proyectos · {st['rango'][0]} → {st['rango'][1]}")
    print(f"  partido asignado: {st['pct_con_partido']}%  ·  senadores con roster_key: "
          f"{st['senadores_con_roster']}/{st['senadores_total']}")
    print(f"→ {outf.relative_to(REPO)}")


if __name__ == '__main__':
    main()
