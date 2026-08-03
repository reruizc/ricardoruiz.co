#!/usr/bin/env python3
"""Pilar Redes de Caudal · harvester de cuentas oficiales y voceros (X/Twitter).

CONECTADO EN PAUSA (decisión Ricardo, ago-2026): la fuente queda cableada pero
NO se le paga a la API hasta la salida al público. Dos candados, y los dos son
deliberados:

  1. Sin ``APIFY_TOKEN`` (env o ``~/.config/caudal/redes.env``) el script hace
     dry-run: valida cuentas.json, reporta qué correría y sale con rc=0. NUNCA
     falla por falta de token — así puede vivir en un cron sin hacer ruido.
  2. La cadencia es MENSUAL (plist ``co.ricardoruiz.caudal-redes.plist``, día 1
     a las 10:00 — se instala aparte, NO va en run_diario.sh a propósito: es
     otro ciclo y otro costo).

Costo cuando se encienda: Apify ``apidojo~tweet-scraper`` cobra por resultado
(~$0.25-0.40 por 1.000 tweets). Con MAX_POR_CUENTA=40 y ~12 cuentas, un corte
mensual son ~500 items ≈ centavos de USD. El techo duro es MAX_POR_CUENTA — no
subirlo sin mirar la factura de Apify primero.

Uso:
  python3 tools/caudal/redes/harvest_redes.py            # corte (dry-run sin token)
  python3 tools/caudal/redes/harvest_redes.py --dry-run  # forzar dry-run aun con token

Salidas (gitignored): Bases de datos/leyes-senado/redes/
  raw/corte-YYYY-MM.json    respuesta cruda de Apify (un archivo por corte)
  dist/redes.jsonl          consolidado normalizado (append por corte, dedup por id)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / 'Bases de datos' / 'leyes-senado' / 'redes'
CUENTAS = Path(__file__).with_name('cuentas.json')
ENV_FILE = Path.home() / '.config' / 'caudal' / 'redes.env'

ACTOR = 'apidojo~tweet-scraper'
MAX_POR_CUENTA = 40          # techo de costo — ver docstring antes de subirlo
TIMEOUT = 300


def _token():
    t = os.environ.get('APIFY_TOKEN', '').strip()
    if t:
        return t
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith('APIFY_TOKEN='):
                return line.split('=', 1)[1].strip().strip('"')
    return ''


def _cuentas():
    data = json.loads(CUENTAS.read_text())
    out = []
    for grupo in ('entidades', 'voceros'):
        for c in data.get(grupo, []):
            h = (c.get('handle') or '').strip().lstrip('@')
            if h and not h.startswith('_'):
                out.append({'handle': h, 'nombre': c.get('nombre', h), 'grupo': grupo})
    return out


def _norm(item, cuentas_by_handle):
    """Tweet crudo de Apify → registro plano de Caudal."""
    autor = ((item.get('author') or {}).get('userName') or '').lstrip('@')
    meta = cuentas_by_handle.get(autor.lower(), {})
    return {
        'id': item.get('id') or item.get('url'),
        'fuente': 'x',
        'handle': autor,
        'entidad': meta.get('nombre', autor),
        'grupo': meta.get('grupo', ''),
        'fecha': item.get('createdAt'),
        'texto': (item.get('text') or '').strip(),
        'url': item.get('url'),
        'rt': item.get('retweetCount'), 'likes': item.get('likeCount'),
    }


def run(dry_run=False):
    cuentas = _cuentas()
    token = _token()
    print(f"[redes] {len(cuentas)} cuentas en cuentas.json · tope {MAX_POR_CUENTA} items/cuenta")
    if not token or dry_run:
        motivo = 'dry-run pedido' if (dry_run and token) else 'sin APIFY_TOKEN (fuente conectada en pausa)'
        print(f"[redes] {motivo} — no se llama a la API, no se gasta. rc=0")
        for c in cuentas:
            print(f"  · @{c['handle']:<18} {c['nombre']}")
        return 0

    corte = time.strftime('%Y-%m')
    raw_dir = BASE / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f'corte-{corte}.json'
    if raw_path.exists():
        print(f"[redes] corte {corte} ya existe ({raw_path.name}) — no se repite el gasto. rc=0")
        return 0

    payload = json.dumps({
        'twitterHandles': [c['handle'] for c in cuentas],
        'maxItems': MAX_POR_CUENTA * len(cuentas),
        'sort': 'Latest',
    })
    url = f'https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?token={token}&timeout={TIMEOUT}'
    print(f"[redes] corte {corte} · llamando Apify ({ACTOR})…")
    r = subprocess.run(['curl', '-sS', '--max-time', str(TIMEOUT + 30), '-X', 'POST',
                        '-H', 'Content-Type: application/json', '-d', payload, url],
                       capture_output=True)
    if r.returncode != 0:
        print(f"[redes] ERROR curl rc={r.returncode}: {r.stderr.decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        return 1
    try:
        items = json.loads(r.stdout.decode('utf-8', 'replace'))
        assert isinstance(items, list)
    except Exception as e:
        print(f"[redes] ERROR respuesta no-JSON de Apify: {e} · {r.stdout[:200]!r}", file=sys.stderr)
        return 1

    raw_path.write_text(json.dumps(items, ensure_ascii=False))
    by_handle = {c['handle'].lower(): c for c in cuentas}
    dist = BASE / 'dist'
    dist.mkdir(parents=True, exist_ok=True)
    out_path = dist / 'redes.jsonl'
    vistos = set()
    if out_path.exists():
        # dedup contra cortes previos — leer con split('\n'), nunca splitlines()
        # (regla del proyecto: U+0085 en texto libre parte registros).
        for line in out_path.read_text(encoding='utf-8').split('\n'):
            if line.strip():
                try:
                    vistos.add(json.loads(line).get('id'))
                except Exception:
                    pass
    nuevos = 0
    with out_path.open('a', encoding='utf-8') as f:
        for it in items:
            rec = _norm(it, by_handle)
            if rec['id'] and rec['id'] not in vistos:
                vistos.add(rec['id'])
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                nuevos += 1
    print(f"[redes] corte {corte}: {len(items)} items de Apify · {nuevos} nuevos en dist/redes.jsonl")
    return 0


if __name__ == '__main__':
    sys.exit(run(dry_run='--dry-run' in sys.argv))
