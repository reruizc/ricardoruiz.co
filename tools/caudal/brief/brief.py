#!/usr/bin/env python3
"""
El brief, de punta a punta: barrido → Claude Fable 5.1 → JSON → PDF.

  python3 tools/caudal/brief/brief.py cauce                  # barre y escribe
  python3 tools/caudal/brief/brief.py cauce --barrido b.json # reusa un barrido
  python3 tools/caudal/brief/brief.py cauce --solo-prompt    # imprime y no gasta
  python3 tools/caudal/brief/brief.py cauce --modelo claude-sonnet-5

MODELO. Claude Fable 5.1 por defecto (decisión de Ricardo, 16-sep-2026): el brief
es bajo volumen y alto valor, y es lo que el cliente ve; una sola corrección de
analista cuesta más que la diferencia de modelo. La extracción de hechos —que sí
es volumen— se queda en el modelo barato. Medido el 16-sep sobre el barrido real
de Cauce: 14.109 tokens de entrada y 12.748 de salida (3.961 de razonamiento, que
se cobra como salida) = USD 0,78 ≈ 2.335 pesos por brief, ~17.800 al mes por
cuenta a siete briefs y medio. El mismo brief con Claude Opus 5 costó la mitad
(USD 0,38) y tardó casi el doble (4:50 contra 2:40).

CREDENCIAL. `ANTHROPIC_API_KEY`, buscada en este orden: el entorno y, si no
está, `~/.config/caudal/anthropic.env` (chmod 600, fuera del repo — el mismo
patrón del motor de alertas). ⚠️ Una llave de API NUNCA va al repo, que es
público, ni a un archivo del proyecto. La Lambda de Caudal tiene su
propio switch de modelo por variable de entorno y no se toca desde acá: este
generador corre fuera, como el motor de alertas, porque una generación de brief
no cabe en los 30 segundos del API Gateway y no tiene por qué caber.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import barrido as barrido_mod                                    # noqa: E402
import caudal_core                                               # noqa: E402
from prompt_brief import BRIEF_SYSTEM, armar_mensaje             # noqa: E402

MODELO = 'claude-fable-5-1'
# ⚠️ El techo cubre el TEXTO y el RAZONAMIENTO previo, que también es salida.
# Con 16.000 el brief de Cauce del 16-sep se cortó a mitad del JSON en cuanto la
# evidencia sumó las redes (medido antes: 12.748 de salida, 3.961 de razonar).
# 32.000 deja el doble de margen; sin streaming la petición sigue por debajo del
# timeout de 600 s (medido: 2 min 40 s).
MAX_TOKENS = 32000
# Tarifas Anthropic al 13-sep-2026, USD por millón de tokens, y la tasa que usa
# la propuesta comercial. Sirve para reportar el costo real de cada corrida.
PRECIO = {'claude-opus-5': (5.0, 25.0), 'claude-sonnet-5': (2.0, 10.0),
          'claude-fable-5-1': (10.0, 50.0)}
COP_USD = 3000


ENV_FILE = os.path.expanduser('~/.config/caudal/anthropic.env')


def llave():
    """La llave, del entorno o del archivo de configuración. Nunca del repo."""
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if key:
        return key
    if os.path.exists(ENV_FILE):
        for linea in open(ENV_FILE, encoding='utf-8'):
            linea = linea.strip()
            if linea.startswith('#') or '=' not in linea:
                continue
            k, v = linea.split('=', 1)
            if k.strip() == 'ANTHROPIC_API_KEY':
                return v.strip().strip('"').strip("'")
    sys.exit(f'falta ANTHROPIC_API_KEY: ponla en el entorno o en {ENV_FILE}')


def generar(system, user, modelo=MODELO, max_tokens=MAX_TOKENS):
    """Una llamada a la API de Anthropic. Devuelve (json, uso)."""
    key = llave()
    body = json.dumps({
        'model': modelo, 'max_tokens': max_tokens, 'system': system,
        # Pensar antes de escribir es justo lo que este trabajo necesita: el
        # brief exige elegir qué entra y qué no, no solo redactar.
        'thinking': {'type': 'adaptive'},
        'output_config': {'effort': 'high'},
        'messages': [{'role': 'user', 'content': user}],
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=body,
        headers={'Content-Type': 'application/json', 'x-api-key': key,
                 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    if d.get('stop_reason') == 'max_tokens':
        u = d.get('usage', {})
        sys.exit(f"el modelo llegó al techo de {max_tokens} tokens antes de cerrar el JSON "
                 f"(salida {u.get('output_tokens')}): súbelo en MAX_TOKENS o recorta la evidencia")
    if d.get('stop_reason') == 'refusal':
        sys.exit('el modelo declinó la petición: '
                 + json.dumps(d.get('stop_details') or {}, ensure_ascii=False))
    txt = ''.join(b.get('text', '') for b in d.get('content', [])
                  if b.get('type') == 'text').strip()
    if txt.startswith('```'):
        txt = txt.split('```')[1].lstrip('json').strip()
    return json.loads(txt), d.get('usage', {})


def costo(uso, modelo):
    ent, sal = PRECIO.get(modelo, PRECIO[MODELO])
    usd = (uso.get('input_tokens', 0) / 1e6 * ent
           + uso.get('output_tokens', 0) / 1e6 * sal)
    return usd, usd * COP_USD


def probar(modelo=MODELO):
    """Verifica credencial, modelo y tarifa con la llamada más barata posible."""
    key = llave()
    print(f'llave: {key[:11]}…{key[-4:]} · {len(key)} caracteres')
    body = json.dumps({'model': modelo, 'max_tokens': 16,
                       'messages': [{'role': 'user', 'content': 'Responde OK.'}]}).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=body,
        headers={'Content-Type': 'application/json', 'x-api-key': key,
                 'anthropic-version': '2023-06-01'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode('utf-8', 'replace')[:400]
        sys.exit(f'HTTP {e.code} — {detalle}')
    uso = d.get('usage', {})
    usd, cop = costo(uso, modelo)
    txt = ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')
    print(f"modelo {d.get('model')} · respondió: {txt.strip()[:40]!r}")
    print(f"entrada {uso.get('input_tokens', 0)} · salida {uso.get('output_tokens', 0)}"
          f" · USD {usd:.5f} · COP {cop:.1f}")
    print('listo: la llave sirve y el modelo responde.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sector', nargs='?', help='preset (cauce, binance, didi…)')
    ap.add_argument('--perfil', help='archivo JSON con un perfil guardado')
    ap.add_argument('--barrido', help='reusar un barrido ya corrido')
    ap.add_argument('--dias', type=int, default=3, help='ventana (default 72 h)')
    ap.add_argument('--modelo', default=MODELO)
    ap.add_argument('--solo-prompt', action='store_true',
                    help='imprime el mensaje y no llama al modelo')
    ap.add_argument('--probar', action='store_true',
                    help='una llamada mínima para verificar la llave y el modelo')
    ap.add_argument('--out', help='guardar el JSON del brief acá')
    a = ap.parse_args()

    if a.probar:
        return probar(a.modelo)

    if a.barrido:
        b = json.load(open(a.barrido, encoding='utf-8'))
    else:
        if a.perfil:
            p = caudal_core.normalizar_perfil(
                json.load(open(a.perfil, encoding='utf-8')))
        elif a.sector:
            p = caudal_core.perfil_desde_sector(a.sector)
            if not p:
                sys.exit(f'no existe el preset «{a.sector}»')
        else:
            sys.exit('dame un preset, --perfil o --barrido')
        desde = (datetime.date.today()
                 - datetime.timedelta(days=a.dias)).isoformat()
        b = barrido_mod.barrer(p, a.dias, desde)

    user = armar_mensaje(b)
    if a.solo_prompt:
        print(user)
        print(f'\n[{len(user):,} caracteres · ~{len(user)//4:,} tokens de entrada]'
              .replace(',', '.'))
        return

    brief, uso = generar(BRIEF_SYSTEM, user, a.modelo)
    brief['_meta'] = {
        'cliente': b['perfil'].get('nombre'), 'ventana': b['ventana'],
        'modelo': a.modelo, 'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'uso': uso, 'cobertura': b.get('cobertura'),
    }
    out = a.out or f"brief-{(b['perfil'].get('nombre') or 'cliente').lower()}-{b['ventana']['hasta']}.json"
    json.dump(brief, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    usd, cop = costo(uso, a.modelo)
    print(f"{brief.get('titular', '')}\n")
    print(f"{len(brief.get('temas', []))} temas · {len(brief.get('agenda', []))} "
          f"en agenda · {len(brief.get('no_se_movio', []))} verificaciones")
    print(f"entrada {uso.get('input_tokens', 0):,} tokens · salida "
          f"{uso.get('output_tokens', 0):,} · USD {usd:.4f} · COP {cop:,.0f}"
          .replace(',', '.'))
    print(f"[brief → {out}]")


if __name__ == '__main__':
    main()
