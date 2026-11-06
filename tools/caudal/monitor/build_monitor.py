#!/usr/bin/env python3
"""Monitoreo del Congreso · arma el JSON que lee `caudal-monitor.html`.

Junta tres cosas que ya produce el rastreo diario, sin consultar nada nuevo:
  · proyectos   la legislatura viva de las dos cámaras, con su estado y etapa
                (diario/2026-2027/proyectos.jsonl + diario-camara/…/proyectos.jsonl)
  · movimientos lo que cambió en los últimos N días (diario*/novedades/*.json),
                filtrado a lo que es trámite: aprobaciones, ponencias, ponentes,
                pasos a plenaria o a sanción, archivos y radicados nuevos
  · tesauro     los tópicos de caudal_core.SINONIMOS, para que la página cruce
                los temas de un cliente con los títulos sin llamar a la Lambda

La agenda (órdenes del día) NO va aquí: la página la lee de
`legislativo/ordenes-vigentes.json`, que ya es público y se refresca en su etapa.

Todo es información pública del Congreso (títulos, estados, fechas). No lleva
nombres de clientes: el cruce con un cliente lo hace el navegador con los temas
que le entrega `perfil_meta`.

  python3 tools/caudal/monitor/build_monitor.py            # escribe local
  python3 tools/caudal/monitor/build_monitor.py --subir    # y sube a S3 (gzip)
"""
import argparse
import datetime as dt
import glob
import gzip
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / 'Bases de datos' / 'leyes-senado'
LEG = '2026-2027'
OUT = BASE / 'dist' / 'monitor-congreso.json'
S3 = ('s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/'
      'monitor-congreso.json')

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
import caudal_core  # noqa: E402  (solo para el tesauro)


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s.lower()).strip()


def clave(num, cam):
    """'477/2026C' · '328/26' · '296/2026S' → 'C477-26' / 'S328-26'."""
    m = re.match(r'\s*0*(\d{1,4})\s*/\s*(?:20)?(\d{2})\s*([CS])?', str(num or ''), re.I)
    if not m:
        return None
    c = (m.group(3) or cam).upper()
    return f'{c}{int(m.group(1))}-{m.group(2)}'


# Etapa 1-6 desde el estado oficial: la misma escala de Mi Congreso
# (mi-congreso-base.js · etapaDe), para que las dos páginas digan lo mismo.
ETAPAS = ['Radicado', 'En comisión', 'En primer debate', 'Aprobado en primer debate',
          'En segundo debate', 'Pasa a la otra cámara']


def etapa(estado, rec=None):
    s = norm(estado)
    if re.search(r'archivad|retirad', s):
        return {'fin': 'Archivado o retirado'}
    if 'acumulad' in s:
        return {'fin': 'Acumulado a otro proyecto'}
    if 'sancion' in s:
        return {'fin': 'Pasa a sanción presidencial'}
    n = 1
    if 'enviar a comision' in s:
        n = 1
    elif 'segundo debate' in s:
        n = 5 if 'discutir' in s else 4
    elif re.search(r'discutir ponencia|debate de comision', s):
        n = 3
    elif 'tramite en plenaria' in s:
        n = 4
    elif re.search(r'ponen|tramite en comision', s):
        n = 2
    if rec:  # el Senado registra fechas de aprobación: mandan sobre el texto
        if rec.get('fecha_de_aprobacion_primer_debate_camara') or rec.get('fecha_de_aprobacion_segundo_debate'):
            n = max(n, 6)
        elif rec.get('fecha_de_aprobacion_primer_debate'):
            n = max(n, 4)
    return {'n': n}


def leer_jsonl(p):
    out = []
    if not Path(p).exists():
        return out
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def proyectos():
    por_k, lista = {}, []
    for r in leer_jsonl(BASE / 'diario' / LEG / 'proyectos.jsonl'):
        ks = [k for k in (clave(r.get('numero_senado'), 'S'), clave(r.get('numero_camara'), 'C')) if k]
        if not ks or not r.get('titulo'):
            continue
        x = {'ks': ks, 'ns': r.get('numero_senado') or '', 'nc': r.get('numero_camara') or '',
             't': r['titulo'].strip(), 'est': (r.get('estado') or '').strip(),
             'com': r.get('comision') or '', 'fp': (r.get('fecha_de_presentacion') or '').replace('/', '-')[:10],
             'tipo': r.get('tipo_de_ley') or '', 'cam': 'Senado',
             'url': r.get('texto_radicado_url') or ''}
        x['etapa'] = etapa(x['est'], r)
        lista.append(x)
        for k in ks:
            por_k[k] = x
    for r in leer_jsonl(BASE / 'diario-camara' / LEG / 'proyectos.jsonl'):
        kc = clave(r.get('numero_camara'), 'C')
        ks_ = clave(r.get('numero_senado'), 'S')
        if not kc or not r.get('titulo'):
            continue
        prev = por_k.get(kc) or (por_k.get(ks_) if ks_ else None)
        com = ', '.join(c.get('nombre', '') for c in (r.get('comisiones') or []) if isinstance(c, dict))
        if prev:  # ya vino del Senado: se completa, no se duplica
            if kc not in prev['ks']:
                prev['ks'].append(kc)
            prev['nc'] = prev['nc'] or r.get('numero_camara')
            prev['est_c'] = r.get('estado') or ''
            continue
        x = {'ks': [k for k in (kc, ks_) if k], 'nc': r.get('numero_camara') or '',
             'ns': r.get('numero_senado') or '', 't': re.sub(r'\s+', ' ', r['titulo']).strip(' “”"'),
             'est': (r.get('estado') or '').strip(), 'com': com, 'fp': '',
             'tipo': r.get('tipo') or '', 'cam': 'Cámara',
             'url': f"https://www.camara.gov.co/{r['link_web']}" if r.get('link_web') else ''}
        x['etapa'] = etapa(x['est'])
        lista.append(x)
        for k in x['ks']:
            por_k[k] = x
    return lista, por_k


# Campos del registro del Senado que son TRÁMITE (lo demás —título, autor, URL—
# cambia por arreglos de la fuente y es ruido para un monitor).
APROB = {
    'fecha_de_aprobacion_primer_debate': ('aprobado', 'Aprobado en primer debate en el Senado'),
    'fecha_de_aprobacion_segundo_debate': ('aprobado', 'Aprobado en segundo debate en el Senado'),
    'fecha_de_aprobacion_primer_debate_camara': ('aprobado', 'Aprobado en primer debate en la Cámara'),
    'fecha_de_aprobacion_segundo_debate_camara': ('aprobado', 'Aprobado en segundo debate en la Cámara'),
    'fecha_de_conciliacion_senado': ('aprobado', 'Conciliado en el Senado'),
    'fecha_de_conciliacion_camara': ('aprobado', 'Conciliado en la Cámara'),
}
PONENTES = {'ponente_primer_debate': 'primer debate (Senado)', 'ponente_segundo_debate': 'segundo debate (Senado)',
            'ponente_primer_debate_camara': 'primer debate (Cámara)', 'ponente_segundo_debate_camara': 'segundo debate (Cámara)'}
PONENCIA = {'primera_ponencia': 'primer debate', 'segunda_ponencia': 'segundo debate'}
NIVEL = {'aprobado': 3, 'sancion': 3, 'archivado': 3, 'plenaria': 2, 'ponencia': 2,
         'ponentes': 2, 'comision': 1, 'radicado': 1, 'estado': 1, 'gaceta': 0}


def _tipo_estado(ahora):
    s = norm(ahora)
    if re.search(r'archivad|retirad', s):
        return 'archivado'
    if 'sancion' in s:
        return 'sancion'
    if 'plenaria' in s or 'segundo debate' in s:
        return 'plenaria'
    return 'estado'


def movimientos(dias, hoy, por_k):
    desde = hoy - dt.timedelta(days=dias)
    out = []

    def add(fecha, cam, ks, titulo, tipo, txt, antes='', ahora=''):
        ks = [k for k in ks if k]
        p = next((por_k[k] for k in ks if k in por_k), None)
        out.append({'f': fecha, 'cam': cam, 'ks': p['ks'] if p else ks,
                    't': (p['t'] if p else re.sub(r'\s+', ' ', titulo or '').strip()),
                    'tipo': tipo, 'txt': txt, 'n': NIVEL.get(tipo, 1),
                    'antes': str(antes or '')[:160], 'ahora': str(ahora or '')[:160]})

    for f in sorted(glob.glob(str(BASE / 'diario' / 'novedades' / '*.json'))):
        fecha = Path(f).stem
        try:
            if dt.date.fromisoformat(fecha) < desde:
                continue
            d = json.load(open(f, encoding='utf-8'))
        except (ValueError, OSError):
            continue
        for r in d.get('nuevos') or []:
            add(fecha, 'Senado', [clave(r.get('numero_senado'), 'S'), clave(r.get('numero_camara'), 'C')],
                r.get('titulo'), 'radicado', 'Radicado en el Senado')
        for c in d.get('cambios') or []:
            ks = [clave(c.get('numero_senado'), 'S'), clave(c.get('numero_camara'), 'C')]
            de = c.get('deltas') or {}
            for campo, v in de.items():
                antes, ahora = (v or {}).get('antes') or '', (v or {}).get('ahora') or ''
                if not str(ahora).strip():
                    continue  # la fuente vació el campo un día: es ruido, no trámite
                if campo in APROB and not antes:
                    tipo, txt = APROB[campo]
                    add(fecha, 'Senado', ks, c.get('titulo'), tipo, txt, antes, ahora)
                elif campo == 'estado' and antes:
                    tipo = _tipo_estado(ahora)
                    add(fecha, 'Senado', ks, c.get('titulo'), tipo, ahora.capitalize(), antes, ahora)
                elif campo in PONENTES and not antes and 'gaceta' not in norm(ahora):
                    add(fecha, 'Senado', ks, c.get('titulo'), 'ponentes',
                        f'Ponentes para {PONENTES[campo]}: {ahora}', antes, ahora)
                elif campo in PONENCIA and 'pendiente' not in norm(ahora) and norm(ahora) != norm(antes):
                    archivo = 'archivo' in norm(ahora)
                    add(fecha, 'Senado', ks, c.get('titulo'), 'ponencia',
                        f"Ponencia {'de ARCHIVO ' if archivo else ''}para {PONENCIA[campo]} · {ahora}", antes, ahora)
                elif campo == 'comision' and not antes:
                    add(fecha, 'Senado', ks, c.get('titulo'), 'comision', f'Enviado a la Comisión {ahora.title()}', antes, ahora)
                elif campo in ('objeciones', 'texto_plenaria', 'conciliacion') and not antes:
                    add(fecha, 'Senado', ks, c.get('titulo'), 'estado', f'{campo.replace("_", " ").capitalize()}: {ahora}', antes, ahora)

    for f in sorted(glob.glob(str(BASE / 'diario-camara' / 'novedades' / '*.json'))):
        fecha = Path(f).stem
        try:
            if dt.date.fromisoformat(fecha) < desde:
                continue
            d = json.load(open(f, encoding='utf-8'))
        except (ValueError, OSError):
            continue
        for r in d.get('nuevos') or []:
            add(fecha, 'Cámara', [clave(r.get('numero_camara'), 'C'), clave(r.get('numero_senado'), 'S')],
                r.get('titulo'), 'radicado', 'Radicado en la Cámara')
        for c in d.get('cambios') or []:
            ks = [clave(c.get('numero_camara'), 'C'), clave(c.get('numero_senado'), 'S')]
            de = c.get('deltas') or {}
            v = de.get('estado')
            if v and v.get('antes') and v.get('ahora') and norm(v['ahora']) != 'otro':
                add(fecha, 'Cámara', ks, c.get('titulo'), _tipo_estado(v['ahora']), v['ahora'], v['antes'], v['ahora'])
            g = de.get('gacetas')
            if g and isinstance(g.get('ahora'), list) and len(g['ahora']) > len(g.get('antes') or []):
                nuevas = [x.get('key') or x.get('num') for x in g['ahora'][len(g.get('antes') or []):] if isinstance(x, dict)]
                add(fecha, 'Cámara', ks, c.get('titulo'), 'gaceta', 'Publicado en Gaceta ' + ', '.join(map(str, nuevas)))

    # mismo proyecto, mismo día, mismo tipo → una sola fila
    vistos, unicos = set(), []
    for m in sorted(out, key=lambda m: (m['f'], m['n']), reverse=True):
        k = (m['f'], tuple(m['ks'][:1]), m['tipo'], m['txt'])
        if k in vistos:
            continue
        vistos.add(k)
        unicos.append(m)
    return unicos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=21)
    ap.add_argument('--subir', action='store_true')
    a = ap.parse_args()
    hoy = dt.date.today()
    lista, por_k = proyectos()
    movs = movimientos(a.dias, hoy, por_k)
    data = {
        'v': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'legislatura': LEG, 'ventana_dias': a.dias, 'etapas': ETAPAS,
        'n_proyectos': len(lista), 'proyectos': lista,
        'n_movimientos': len(movs), 'movimientos': movs,
        'tesauro': [{'k': s['k'], 'terms': s['terms']} for s in caudal_core.SINONIMOS],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
    OUT.write_bytes(raw)
    tipos = {}
    for m in movs:
        tipos[m['tipo']] = tipos.get(m['tipo'], 0) + 1
    print(f'[monitor] {len(lista)} proyectos · {len(movs)} movimientos en {a.dias} días · {tipos} · '
          f'{len(raw)//1024} KB → {OUT}')
    if a.subir:
        gz = OUT.with_suffix('.json.gz')
        gz.write_bytes(gzip.compress(raw, 9))
        r = subprocess.run(['aws', 's3', 'cp', str(gz), S3, '--content-type', 'application/json',
                            '--content-encoding', 'gzip', '--cache-control', 'public, max-age=600'])
        if r.returncode:
            sys.exit('[monitor] falló la subida a S3')
        print(f'[monitor] subido · {gz.stat().st_size//1024} KB gzip → {S3}')


if __name__ == '__main__':
    main()
