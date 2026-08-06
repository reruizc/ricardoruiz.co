#!/usr/bin/env python3
"""build_ratio.py — extrae la RATIO DECIDENDI estructurada de las decisiones de
instancia desfavorables del corpus de relatoría (rag-pasajes.jsonl.gz).

Es el pre-cómputo que hace barata la Lambda tutela-analiza: en vez de mandar
antecedentes de 14k chars al modelo en cada request, el runtime consume estas
entradas ya comprimidas y VERIFICADAS. Un pase de DeepSeek por sentencia:

  { pretension, resultado_corte,
    ratios: [ { razon (1-2 frases de por qué negó la instancia),
                causa (taxonomía de 8 o 'otra'),
                cita  (frase TEXTUAL del corpus, verificada aquí en build) } ] }

Principios (no romperlos al iterar):
- PRESUPUESTO DURO en USD (default $1.00, piloto aprobado por Ricardo). Se
  estima con tarifas CONSERVADORAS (por encima de las reales de V4 Flash);
  al tocar el techo, el script PARA y deja lo procesado — es resumible.
- Toda `cita` se verifica TEXTUALMENTE (normalizada por espacios/comillas)
  contra el texto fuente de esa sentencia. Cita que no verifica → se descarta
  (queda la razón sin cita). El JSON final reporta el % verificado.
- Resumible: cache por sentencia en relatoria/ratio-cache/{slug}.json con _pv;
  cambiar PROMPT_VERSION invalida y re-pide.
- Gotcha DeepSeek V4: reasoning consume el presupuesto → max_tokens 6000,
  reintento único a 12000 si content llega vacío con finish_reason=length.

Uso:
  export DEEPSEEK_API_KEY=$(aws lambda get-function-configuration \
    --function-name caudal-analiza \
    --query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)
  python3 tools/tutela-analiza/build_ratio.py --limit 10      # validación
  python3 tools/tutela-analiza/build_ratio.py                 # corrida completa (para en $1)
  python3 tools/tutela-analiza/build_ratio.py --budget 2.0    # subir techo
"""
import argparse
import gzip
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'tutelas-salud' / 'relatoria'
RAG = BASE / 'rag-pasajes.jsonl.gz'
CACHE_DIR = BASE / 'ratio-cache'
OUT = BASE / 'ratio-decidendi.json'

PROMPT_VERSION = 'r1-2026-08-05'
DEEPSEEK_URL = os.environ.get('DEEPSEEK_URL', 'https://api.deepseek.com/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-flash')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
HTTP_TIMEOUT = 90

# Tarifas CONSERVADORAS (USD por millón de tokens) para el freno de presupuesto.
# Si las reales de V4 Flash son menores, simplemente procesamos de más margen.
RATE_IN = 0.30
RATE_OUT = 1.20

CAUSAS_VALIDAS = {
    'falta_prueba', 'subsidiariedad', 'sin_orden_medica', 'hecho_superado',
    'no_pbs_sin_prueba', 'inmediatez', 'legitimacion', 'improcedencia_general',
}

SYSTEM = """Eres un abogado constitucionalista colombiano. Recibes los ANTECEDENTES de una sentencia T de la Corte Constitucional (tema salud) y las DECISIONES de instancia que fueron desfavorables al accionante. Tu tarea es extraer, en JSON estricto, la estructura de la petición y la ratio decidendi de cada negativa de instancia.

Devuelve EXACTAMENTE este JSON:
{
 "pretension": "qué pedía la persona, 1 frase concreta (máx 200 caracteres)",
 "resultado_corte": "revoco" | "confirmo" | "parcial" | "otro",
 "ratios": [
   {
     "razon": "por qué el juez de instancia negó o declaró improcedente, 1-2 frases claras en español sencillo (máx 320 caracteres)",
     "causa": "falta_prueba" | "subsidiariedad" | "sin_orden_medica" | "hecho_superado" | "no_pbs_sin_prueba" | "inmediatez" | "legitimacion" | "improcedencia_general" | "otra",
     "cita": "frase COPIADA TEXTUALMENTE, carácter por carácter, del texto que te di (máx 280 caracteres). Si no hay frase que capture la razón, pon null."
   }
 ]
}

Reglas duras:
1. La "cita" debe ser copia LITERAL de un fragmento del texto entregado — sin parafrasear, sin corregir tildes, sin puntos suspensivos agregados. Se verificará por software; una cita alterada se descarta.
2. Un objeto en "ratios" por cada decisión de instancia entregada, en el mismo orden.
3. "causa": elige la que mejor capture la razón central; "otra" solo si ninguna aplica.
4. No inventes nada que no esté en el texto. JSON estricto, sin markdown."""

_lock = threading.Lock()
_spent = {'in': 0, 'out': 0, 'usd': 0.0, 'calls': 0}

# El resolver de macOS se satura con ráfagas de resoluciones concurrentes y
# empieza a fallar con "nodename nor servname provided". Memoizamos la
# resolución: un solo lookup por host para toda la corrida.
import socket
_dns_cache = {}
_getaddrinfo0 = socket.getaddrinfo

def _getaddrinfo_cached(host, *a, **k):
    key = (host,) + a
    if key not in _dns_cache:
        _dns_cache[key] = _getaddrinfo0(host, *a, **k)
    return _dns_cache[key]

socket.getaddrinfo = _getaddrinfo_cached


def norm(s):
    """Normaliza para verificación textual: espacios colapsados, comillas y guiones unificados."""
    if not s:
        return ''
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    s = s.replace('–', '-').replace('—', '-').replace(' ', ' ')
    return re.sub(r'\s+', ' ', s).strip().lower()


def slug(sent):
    return sent.replace('/', '-')


def call_deepseek(user_msg, max_tokens=6000):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
        'max_tokens': max_tokens,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        data = json.loads(r.read().decode('utf-8'))
    choice = data['choices'][0]
    content = choice['message'].get('content') or ''
    usage = data.get('usage', {})
    with _lock:
        _spent['in'] += usage.get('prompt_tokens', 0)
        _spent['out'] += usage.get('completion_tokens', 0)
        _spent['usd'] = _spent['in'] / 1e6 * RATE_IN + _spent['out'] / 1e6 * RATE_OUT
        _spent['calls'] += 1
    if not content:
        raise ValueError(f"content vacío (finish_reason={choice.get('finish_reason')})")
    return json.loads(content)


def procesar(p, budget):
    """Procesa una sentencia del rag. Devuelve la entrada de ratio o None."""
    sent = p['sentencia']
    cpath = CACHE_DIR / (slug(sent) + '.json')
    if cpath.exists():
        try:
            cached = json.loads(cpath.read_text(encoding='utf-8'))
            if cached.get('_pv') == PROMPT_VERSION:
                return cached
        except Exception:
            pass
    with _lock:
        if _spent['usd'] >= budget:
            return None

    decisiones = p.get('instancia') or []
    if not decisiones:
        return None
    ant = (p.get('antecedentes') or '')[:5500]
    dec_txt = '\n'.join(
        f"DECISIÓN {i+1}: {d.get('decision','')[:900]}" +
        (f"\nMOTIVO {i+1}: {d.get('motivo','')[:500]}" if d.get('motivo') else '')
        for i, d in enumerate(decisiones)
    )
    resuelve = (p.get('resuelve') or '')[:900]
    user = (f"SENTENCIA: {sent} ({p.get('fecha','')})\n\nANTECEDENTES:\n{ant}\n\n"
            f"DECISIONES DE INSTANCIA DESFAVORABLES:\n{dec_txt}\n\nRESUELVE (Corte):\n{resuelve}")

    out = None
    for intento in range(4):
        try:
            try:
                out = call_deepseek(user, 6000)
            except ValueError:
                out = call_deepseek(user, 12000)  # gotcha V4: reasoning se comió el presupuesto
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # el resolver de macOS se satura con ráfagas → backoff y reintento
            if intento == 3:
                print(f"  [!] {sent}: {e}", file=sys.stderr)
                return None
            time.sleep(3 * (intento + 1))
        except Exception as e:
            print(f"  [!] {sent}: {e}", file=sys.stderr)
            return None
    if out is None:
        return None

    # Verificación textual de citas contra TODO el texto fuente de la sentencia
    fuente = norm(' '.join([p.get('antecedentes') or ''] +
                           [f"{d.get('decision','')} {d.get('motivo','') or ''}" for d in decisiones] +
                           [p.get('resuelve') or '']))
    ratios = []
    for r in (out.get('ratios') or [])[:len(decisiones)]:
        if not isinstance(r, dict):
            continue
        causa = r.get('causa') if r.get('causa') in CAUSAS_VALIDAS else 'otra'
        cita = r.get('cita')
        verificada = False
        if isinstance(cita, str) and len(cita.strip()) >= 25:
            verificada = norm(cita) in fuente
        if not verificada:
            cita = None
        ratios.append({
            'razon': (r.get('razon') or '')[:320],
            'causa': causa,
            'cita': cita.strip()[:280] if cita else None,
        })
    if not ratios:
        return None

    rc = out.get('resultado_corte')
    entry = {
        '_pv': PROMPT_VERSION,
        'sentencia': sent,
        'fecha': p.get('fecha', ''),
        'ano': p.get('ano', ''),
        'url': p.get('url', ''),
        'casos': p.get('casos', []),
        'pretension': (out.get('pretension') or '')[:200],
        'resultado_corte': rc if rc in ('revoco', 'confirmo', 'parcial', 'otro') else 'otro',
        'ratios': ratios,
    }
    cpath.write_text(json.dumps(entry, ensure_ascii=False), encoding='utf-8')
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--budget', type=float, default=1.0, help='techo USD del piloto')
    ap.add_argument('--limit', type=int, default=0, help='procesar solo N sentencias (validación)')
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    if not DEEPSEEK_API_KEY:
        sys.exit('Falta DEEPSEEK_API_KEY en el entorno (léela de la config de caudal-analiza).')

    CACHE_DIR.mkdir(exist_ok=True)
    pasajes = []
    with gzip.open(RAG, 'rt', encoding='utf-8') as f:
        for line in f:
            pasajes.append(json.loads(line))
    # Validación de tildes (el HTML original era windows-1252; si esto falla, el corpus está roto)
    muestra = ' '.join((p.get('antecedentes') or '')[:2000] for p in pasajes[:50])
    if 'ó' not in muestra and 'í' not in muestra:
        sys.exit('El corpus no trae tildes — decodificación rota, NO seguir.')

    # Recientes primero: si el presupuesto corta, queda la jurisprudencia más útil
    pasajes.sort(key=lambda p: p.get('fecha') or '', reverse=True)
    if args.limit:
        pasajes = pasajes[:args.limit]

    t0 = time.time()
    entradas = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(procesar, p, args.budget): p['sentencia'] for p in pasajes}
        done = 0
        for fut in as_completed(futs):
            done += 1
            e = fut.result()
            if e:
                entradas.append(e)
            if done % 25 == 0 or done == len(futs):
                print(f"  {done}/{len(futs)} · ${_spent['usd']:.3f} · {len(entradas)} entradas", flush=True)

    entradas.sort(key=lambda e: e.get('fecha') or '', reverse=True)
    n_ratios = sum(len(e['ratios']) for e in entradas)
    n_citas = sum(1 for e in entradas for r in e['ratios'] if r['cita'])
    por_causa = {}
    for e in entradas:
        for r in e['ratios']:
            por_causa[r['causa']] = por_causa.get(r['causa'], 0) + 1

    out = {
        'v': PROMPT_VERSION,
        'generado': time.strftime('%Y-%m-%d'),
        'modelo': DEEPSEEK_MODEL,
        'fuente': 'Corte Constitucional · relatoría · sentencias T de salud 2016-2026',
        'costo': {'usd_estimado': round(_spent['usd'], 4), 'llamadas': _spent['calls'],
                  'tokens_in': _spent['in'], 'tokens_out': _spent['out'],
                  'tarifas_conservadoras': {'in_M': RATE_IN, 'out_M': RATE_OUT}},
        'cobertura': {'sentencias_corpus': len(pasajes), 'sentencias_con_ratio': len(entradas),
                      'ratios': n_ratios, 'citas_verificadas': n_citas,
                      'pct_citas_verificadas': round(n_citas / n_ratios * 100, 1) if n_ratios else 0},
        'por_causa': dict(sorted(por_causa.items(), key=lambda kv: -kv[1])),
        'entradas': entradas,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    kb = OUT.stat().st_size / 1024
    print(f"\n✔ {OUT.name}: {len(entradas)} sentencias · {n_ratios} ratios · "
          f"{n_citas} citas verificadas ({out['cobertura']['pct_citas_verificadas']}%) · "
          f"{kb:.0f} KB · ${_spent['usd']:.3f} · {time.time()-t0:.0f}s")
    print(f"  por causa: {out['por_causa']}")


if __name__ == '__main__':
    main()
