#!/usr/bin/env python3
"""
Caudal · Fase 3 — capa de OUTCOME (interina) desde Congreso Visible.

Congreso Visible (Uniandes) publica las votaciones ya estructuradas en el JSON
server-rendered (__NEXT_DATA__) de su web. Una sola request con rows grande trae
las ~10.205 votaciones (2006 → nov-2022; el cuatrienio actual esperará al parse
de gacetas). Cada votación linkea a proyecto por numero_senado/numero_camara.

Da los DEBATES EFECTIVOS + APLAZAMIENTOS + VOTO que faltaban para completar el
índice de bloqueo (agendado vs debatido). El voto nominal por congresista está
en el detalle /votaciones/{id}/ (bajo demanda, no aquí).

Uso: python3 tools/caudal/actas/harvest_votaciones.py
"""
import subprocess, json, re, sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / 'Bases de datos' / 'leyes-senado' / 'actas'
RAW = CACHE / '_cv_votaciones_raw.json'
OUT = CACHE / 'votaciones.json'
URL = 'https://congresovisible.uniandes.edu.co/votaciones/?rows=10300'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'


def fetch_raw():
    if RAW.exists():
        return json.load(open(RAW, encoding='utf-8'))
    print('· bajando Congreso Visible (~87MB, ~40s)…')
    html = subprocess.run(['/usr/bin/curl', '-s', '-A', UA, '--max-time', '120', URL],
                          capture_output=True).stdout.decode('utf-8', 'replace')
    m = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', html, re.S)
    data = json.loads(m.group(1))['props']['pageProps']['VotacionesData']['listVotaciones']['data']
    json.dump(data, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False)
    return data


def num_tok(n):
    m = re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', n or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def strip_html(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def clasif_motivo(motivo, obs):
    t = (motivo + ' ' + obs).lower()
    if 'aplaz' in t:
        return 'aplazamiento'
    if 'archiv' in t:
        return 'archivo'
    if 'negad' in t or 'no aprob' in t or 'hundid' in t:
        return 'negado'
    if 'aprob' in t:
        return 'aprobado'
    return 'otro'


def main():
    data = fetch_raw()
    print(f'  {len(data)} votaciones')
    por_num = defaultdict(list)
    for r in data:
        pl = r.get('proyecto_de_ley') or {}
        obs = strip_html(r.get('observaciones'))
        com = ((r.get('votacion_comision') or {}).get('comision') or {}).get('nombre') \
            or ('Plenaria' if r.get('esPlenaria') else '')
        v = {
            'id': r['id'], 'fecha': r.get('fecha'),
            'donde': com, 'es_comision': bool(r.get('esComision')),
            'motivo': r.get('motivo'), 'tipo': clasif_motivo(r.get('motivo') or '', obs),
            'favor': r.get('votosFavor'), 'contra': r.get('votosContra'),
            'abstencion': r.get('votosAbstencion'), 'asistencia': r.get('numero_asistencias'),
            'acta': r.get('acta'), 'gaceta': r.get('urlGaceta'),
            'obs': obs[:400] if obs else '',
            'titulo': pl.get('titulo', ''),
        }
        for key in {num_tok(pl.get('numero_senado')), num_tok(pl.get('numero_camara'))}:
            if key:
                por_num[key].append(v)

    # por proyecto: resume debates efectivos + aplazamientos + resultado
    index = {}
    for tok, vs in por_num.items():
        vs.sort(key=lambda x: x['fecha'] or '')
        index[tok] = {
            'n_votaciones': len(vs),
            'aplazamientos': sum(1 for x in vs if x['tipo'] == 'aplazamiento'),
            'archivos': sum(1 for x in vs if x['tipo'] == 'archivo'),
            'aprobados': sum(1 for x in vs if x['tipo'] == 'aprobado'),
            'titulo': next((x['titulo'] for x in vs if x['titulo']), ''),
            'votaciones': vs,
        }

    out = {'v': '2026-07-11', 'fuente': 'Congreso Visible · Uniandes',
           'cobertura': '2006 → nov-2022', 'n_votaciones': len(data),
           'n_proyectos': len(index), 'por_proyecto': index}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    ap = sum(v['aplazamientos'] for v in index.values())
    print(f'  {len(index)} proyectos con votación · {ap} aplazamientos detectados')
    print(f'  → {OUT.relative_to(REPO)} ({OUT.stat().st_size/1024/1024:.1f} MB)')
    # muestra: proyectos con más aplazamientos
    top = sorted(index.items(), key=lambda kv: -kv[1]['aplazamientos'])[:8]
    print('\n  Proyectos con más APLAZAMIENTOS votados:')
    for tok, info in top:
        if info['aplazamientos']:
            print(f"   {info['aplazamientos']}× aplazado · {tok:>8} · {info['titulo'][:52]}")


if __name__ == '__main__':
    main()
