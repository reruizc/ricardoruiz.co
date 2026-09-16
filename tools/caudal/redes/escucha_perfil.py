#!/usr/bin/env python3
"""Escucha de redes por PERFIL de cliente · Caudal · X vía Apify.

Distinto de `harvest_redes.py`, que sigue CUENTAS oficiales una vez al mes: esto
escucha lo que se dice en X sobre los TEMAS de un cliente, una vez al día, y lo
deja listo para el rumbo Oriente de la Rosa de los Vientos y para el brief.

  python3 tools/caudal/redes/escucha_perfil.py cauce                 # ensayo: consultas y costo, no gasta
  python3 tools/caudal/redes/escucha_perfil.py cauce --gastar --tope 10    # medición chica
  python3 tools/caudal/redes/escucha_perfil.py cauce --gastar --subir      # la corrida diaria

TOKEN. `APIFY_TOKEN` del entorno o de `~/.config/caudal/redes.env` (chmod 600,
fuera del repo) — el mismo archivo que ya espera `harvest_redes.py`. Sin token
NUNCA falla: hace ensayo y sale con rc=0, así puede vivir en un cron.

COSTO. Actor `kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest`.
⚠️⚠️ MEDIDO el 16-sep sobre Cauce: `maxItems` es POR CONSULTA, no por corrida, y
tiene piso de ~60 por página. Con maxItems=80 trajo 513 (~64 por tema); con 320 se
disparó y el freno la cortó en 956. Por eso se manda el tope por tema.
Costo real US$0,113 = US$0,22 por 1.000, no los 0,18 del catálogo. Con 8 temas son
~US$0,11 al día y ~US$3,40 al mes por cliente. Por eso hay un FRENO: durante la
corrida se mira cuántos ítems lleva el dataset y se aborta al pasar TOPE_DURO. El
costo REAL de cada corrida se lee de Apify y queda en el JSON.

TRES COSAS QUE NO HAY QUE OLVIDAR
- Cero resultados no es «nadie habla del tema»: puede ser el actor caído o un
  input con otro nombre de campo. Con cero, no se sube nada y se dice por qué.
- X solo busca por palabra: esto escucha la conversación sobre los temas, no la
  localidad ni la marca de un tercero que no se nombre.
- La ficha escribe los temas sin tildes («presupuesto general de la nacion»).
  La búsqueda de X no garantiza igualarlos, así que cada tema viaja con su
  variante acentuada (-cion → -ción, -sion → -sión) en la misma consulta.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
import caudal_core  # noqa: E402

ENV_FILE = Path.home() / '.config' / 'caudal' / 'redes.env'
SALIDA = REPO / 'Bases de datos' / 'leyes-senado' / 'redes' / 'escucha'
S3_PREFIJO = 's3://caudal-legislativo/metadata/escucha'

API = 'https://api.apify.com/v2'
ACTOR = 'kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest'
PRECIO_1K = 0.22              # USD por 1.000 publicaciones · MEDIDO 16-sep (catálogo dice 0,18)
POR_CONSULTA = 64             # piso medido: lo que trae por consulta aunque se pida menos
TOPE_DURO = 900               # ítems en el dataset: al pasarlo se aborta la corrida
TOPE_POR_TEMA = 40            # se pide por consulta; el actor no baja de ~60
TOPE_TOTAL = 400              # techo duro por corrida, pase lo que pase con los temas
ESPERA_MAX = 420              # segundos; un actor colgado también cobra
TOP_POR_TEMA = 8              # cuántas publicaciones por tema quedan en el JSON

# Señales de país. Solo se usan si el perfil declara Colombia como su única
# jurisdicción: una publicación de otro país sobre «reforma pensional» es ruido
# para un cliente colombiano, pero no para uno que opera en seis países.
CO = ('colombia', 'bogota', 'medellin', 'cali', 'barranquilla', 'cartagena', 'bucaramanga',
      'cucuta', 'pereira', 'manizales', 'ibague', 'santa marta', 'villavicencio', 'pasto',
      'monteria', 'neiva', 'armenia', 'popayan', 'sincelejo', 'valledupar', 'tunja', 'antioquia',
      'cundinamarca', 'valle del cauca', 'atlantico', 'santander', 'petro', 'congreso de colombia',
      'minhacienda', 'senado de colombia', 'camara de representantes', '🇨🇴')
OTRO = ('argentina', 'buenos aires', 'mexico', 'cdmx', 'españa', 'espana', 'madrid', 'barcelona',
        'chile', 'santiago de chile', 'peru', 'lima', 'venezuela', 'caracas', 'ecuador', 'quito',
        'guayaquil', 'bolivia', 'uruguay', 'montevideo', 'paraguay', 'guatemala', 'honduras',
        'el salvador', 'costa rica', 'panama', 'republica dominicana', 'puerto rico', 'cuba',
        'milei', 'sheinbaum', 'boric', 'bukele', 'la libertad avanza', 'ficha limpia', 'kirchner',
        'kicillof', 'evo morales', 'luis arce', 'amlo', 'psoe', 'ayuso', 'bolsonaro', 'noboa',
        'boluarte', 'senado de la nacion argentina', 'diputados de la nacion', 'congreso de la union',
        'evoespueblo', 'bolivia', '🇦🇷', '🇲🇽', '🇪🇸', '🇨🇱', '🇵🇪', '🇻🇪', '🇪🇨')


def fold(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', fold(s)).strip('-') or 'perfil'


def token():
    t = os.environ.get('APIFY_TOKEN', '').strip()
    if t:
        return t
    if ENV_FILE.exists():
        for linea in ENV_FILE.read_text().splitlines():
            linea = linea.strip()
            if linea.startswith('APIFY_TOKEN='):
                return linea.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


def acentuada(tema):
    """«presupuesto general de la nacion» → «presupuesto general de la nación»."""
    return re.sub(r'(?<=[a-z])(c|s)ion\b', lambda m: m.group(1) + 'ión', tema)


def consultas(perfil, desde):
    out = []
    for tema in perfil.get('temas') or []:
        tema = tema.strip()
        if len(tema) < 4:
            continue
        variantes = [tema] + ([acentuada(tema)] if acentuada(tema) != tema else [])
        terminos = ' OR '.join(f'"{v}"' for v in variantes)
        out.append({'tema': tema, 'q': f'({terminos}) lang:es -filter:retweets since:{desde}'})
    for emp in (perfil.get('empresas') or []) + (perfil.get('competencia') or []):
        nombre = (emp.get('nombre') if isinstance(emp, dict) else emp) or ''
        if len(nombre.strip()) >= 4:
            out.append({'tema': nombre.strip(), 'q': f'"{nombre.strip()}" lang:es -filter:retweets since:{desde}',
                        'identidad': True})
    return out


# ── Apify ────────────────────────────────────────────────────────────────────
def api(ruta, tok, metodo='GET', cuerpo=None, timeout=90):
    url = f"{API}{ruta}{'&' if '?' in ruta else '?'}token={tok}"
    data = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=data, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        cuerpo_err = e.read().decode('utf-8', 'replace')
        try:
            msg = json.loads(cuerpo_err).get('error', {}).get('message', cuerpo_err[:300])
        except ValueError:
            msg = cuerpo_err[:300]
        raise RuntimeError(f'Apify HTTP {e.code}: {msg}') from None
    return d.get('data', d) if isinstance(d, dict) else d


def correr(tok, entrada):
    run = api(f"/acts/{ACTOR.replace('/', '~')}/runs", tok, 'POST', entrada)
    inicio, estado = time.time(), run
    while estado.get('status') in ('READY', 'RUNNING'):
        if time.time() - inicio > ESPERA_MAX:
            try:
                api(f"/actor-runs/{run['id']}/abort", tok, 'POST', {})
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(f'el actor pasó de {ESPERA_MAX}s y se abortó')
        time.sleep(5)
        estado = api(f"/actor-runs/{run['id']}", tok)
        try:
            ds = api(f"/datasets/{estado['defaultDatasetId']}", tok)
            if (ds.get('itemCount') or 0) > TOPE_DURO:
                api(f"/actor-runs/{run['id']}/abort", tok, 'POST', {})
                print(f"[escucha] FRENO: el dataset pasó de {TOPE_DURO} ítems y se abortó la corrida")
                estado = api(f"/actor-runs/{run['id']}", tok)
                break
        except Exception:  # noqa: BLE001
            pass
    if estado.get('status') not in ('SUCCEEDED', 'ABORTED', 'ABORTING'):
        raise RuntimeError(f"el actor terminó en {estado.get('status')}")
    items = api(f"/datasets/{estado['defaultDatasetId']}/items?clean=true&limit=5000", tok, timeout=120)
    usd = estado.get('usageTotalUsd')
    if usd is None:
        usd = (estado.get('stats') or {}).get('usageTotalUsd')
    return (items if isinstance(items, list) else []), usd, estado.get('id')


# ── Normalización ────────────────────────────────────────────────────────────
def dig(obj, *rutas, defecto=None):
    for ruta in rutas:
        cur = obj
        for k in ruta.split('.'):
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur not in (None, ''):
            return cur
    return defecto


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def fecha_iso(v):
    if not v:
        return ''
    for fmt in ('%a %b %d %H:%M:%S %z %Y', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.datetime.strptime(str(v), fmt).strftime('%Y-%m-%dT%H:%M')
        except ValueError:
            continue
    return str(v)[:16]


def pais(item, texto):
    lugar = fold(dig(item, 'author.location', 'user.location', defecto=''))
    blob = lugar + ' ' + fold(texto)
    if any(x in lugar for x in OTRO) or (not any(x in blob for x in CO) and any(x in fold(texto) for x in OTRO)):
        return 'otro'
    return 'co' if any(x in blob for x in CO) else 'sin_dato'


def normalizar(items, qs, solo_colombia):
    vistos, pubs = set(), []
    descartes = {'duplicado': 0, 'retuit': 0, 'otro_pais': 0, 'sin_tema': 0, 'vacio': 0}
    for it in items:
        if not isinstance(it, dict) or it.get('noResults') or it.get('type') == 'mock_tweet':
            descartes['vacio'] += 1
            continue
        pid = str(dig(it, 'id', 'id_str', 'tweetId', defecto=''))
        texto = dig(it, 'text', 'fullText', 'full_text', defecto='')
        if not pid or not texto:
            descartes['vacio'] += 1
            continue
        if pid in vistos:
            descartes['duplicado'] += 1
            continue
        vistos.add(pid)
        if texto.startswith('RT @') or it.get('isRetweet') or it.get('retweeted_tweet'):
            descartes['retuit'] += 1
            continue
        donde = pais(it, texto)
        if solo_colombia and donde == 'otro':
            descartes['otro_pais'] += 1
            continue
        ft = fold(texto)
        idx = it.get('searchTermIndex')
        temas = []
        if isinstance(idx, int) and 0 <= idx < len(qs):
            temas.append(qs[idx]['tema'])       # la consulta que la trajo manda
        temas += [c['tema'] for c in qs if c['tema'] not in temas and fold(c['tema']) in ft]
        if not temas:
            descartes['sin_tema'] += 1
            continue
        autor = dig(it, 'author.userName', 'author.screen_name', 'user.screen_name', defecto='')
        m = {'likes': num(dig(it, 'likeCount', 'favorite_count')), 'rts': num(dig(it, 'retweetCount', 'retweet_count')),
             'respuestas': num(dig(it, 'replyCount', 'reply_count')), 'citas': num(dig(it, 'quoteCount', 'quote_count')),
             'vistas': num(dig(it, 'viewCount', 'views'))}
        pubs.append({
            'id': pid, 'url': dig(it, 'url', 'twitterUrl', defecto=f'https://x.com/{autor}/status/{pid}'),
            'texto': texto[:600], 'fecha': fecha_iso(dig(it, 'createdAt', 'created_at')),
            'autor': autor, 'nombre': dig(it, 'author.name', 'user.name', defecto=''),
            'seguidores': num(dig(it, 'author.followers', 'author.followersCount', 'user.followers_count')),
            'verificada': bool(dig(it, 'author.isBlueVerified', 'author.isVerified', defecto=False)),
            'pais': donde, 'temas': temas, **m,
            'interaccion': m['likes'] + 2 * m['rts'] + m['respuestas'] + m['citas'],
        })
    return pubs, descartes


def resumir(pubs, qs):
    por_tema = {}
    for c in qs:
        del_tema = [p for p in pubs if c['tema'] in p['temas']]
        # Lo que se sabe colombiano va primero: una publicación sin ubicación puede
        # ser de cualquier país hispanohablante, y en el top es donde se lee.
        del_tema.sort(key=lambda p: (p['pais'] != 'co', -p['interaccion'], -p['seguidores']))
        por_tema[c['tema']] = {'n': len(del_tema), 'n_colombia': sum(p['pais'] == 'co' for p in del_tema),
                               'interaccion': sum(p['interaccion'] for p in del_tema),
                               'identidad': bool(c.get('identidad')), 'top': del_tema[:TOP_POR_TEMA]}
    voces = {}
    for p in pubs:
        v = voces.setdefault(p['autor'], {'autor': p['autor'], 'nombre': p['nombre'], 'seguidores': p['seguidores'],
                                          'verificada': p['verificada'], 'publicaciones': 0, 'interaccion': 0})
        v['publicaciones'] += 1
        v['interaccion'] += p['interaccion']
    voces = sorted(voces.values(), key=lambda v: (-v['interaccion'], -v['seguidores']))[:12]
    return por_tema, voces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sector', nargs='?', help='preset de Caudal (cauce, binance, didi…)')
    ap.add_argument('--perfil', help='archivo JSON con un perfil guardado')
    ap.add_argument('--dias', type=int, default=1, help='ventana hacia atrás (default 1 día)')
    ap.add_argument('--tope', type=int, default=TOPE_POR_TEMA, help='publicaciones por tema')
    ap.add_argument('--gastar', action='store_true', help='llamar a Apify (sin esto, ensayo)')
    ap.add_argument('--subir', action='store_true', help='subir el resultado a S3 para la Rosa')
    a = ap.parse_args()

    if a.perfil:
        perfil = caudal_core.normalizar_perfil(json.load(open(a.perfil, encoding='utf-8')))
    elif a.sector:
        perfil = caudal_core.perfil_desde_sector(a.sector)
        if not perfil:
            sys.exit(f'no existe el preset «{a.sector}»')
    else:
        sys.exit('dame un preset o --perfil')

    nombre = perfil.get('nombre') or a.sector
    hoy = datetime.date.today()
    desde = (hoy - datetime.timedelta(days=a.dias)).isoformat()
    qs = consultas(perfil, desde)
    if not qs:
        print(f'[escucha] {nombre}: el perfil no tiene temas ni empresas que escuchar')
        return 0
    por_consulta = max(a.tope, POR_CONSULTA)
    tope_total = min(TOPE_TOTAL, a.tope * len(qs))
    estimado = por_consulta * len(qs) * PRECIO_1K / 1000
    juris = [fold(j) for j in (perfil.get('jurisdicciones') or [])]
    solo_colombia = (not juris) or juris == ['colombia']

    print(f'[escucha] {nombre} · {len(qs)} consultas · {a.tope} por consulta (llegan ~{por_consulta}) · '
          f'estimado US${estimado:.3f} por corrida (~US${estimado * 30:.2f} al mes) · freno en {TOPE_DURO}')
    for c in qs:
        print(f'   · {c["q"]}')

    tok = token()
    if not a.gastar or not tok:
        motivo = 'sin --gastar' if tok else f'sin APIFY_TOKEN (entorno o {ENV_FILE})'
        print(f'[escucha] ensayo ({motivo}): no se llamó a Apify')
        return 0

    entrada = {'searchTerms': [c['q'] for c in qs], 'maxItems': max(20, a.tope), 'sort': 'Latest'}
    t0 = time.time()
    items, usd, run_id = correr(tok, entrada)
    pubs, descartes = normalizar(items, qs, solo_colombia)
    por_tema, voces = resumir(pubs, qs)
    usd_real = usd if isinstance(usd, (int, float)) else None

    out = {
        'v': 1, 'perfil': nombre, 'slug': slug(nombre), 'red': 'x', 'actor': ACTOR,
        'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'ventana': {'desde': desde, 'hasta': hoy.isoformat(), 'dias': a.dias},
        'consultas': qs, 'solo_colombia': solo_colombia,
        'n_bruto': len(items), 'n': len(pubs), 'descartes': descartes,
        'costo': {'apify_usd': usd_real, 'estimado_usd': round(len(items) * PRECIO_1K / 1000, 4),
                  'run_id': run_id, 'segundos': round(time.time() - t0)},
        'por_tema': por_tema, 'voces': voces,
        'campos_crudos': sorted(items[0].keys()) if items and isinstance(items[0], dict) else [],
    }
    destino = SALIDA / out['slug'] / f'{hoy.isoformat()}.json'
    destino.parent.mkdir(parents=True, exist_ok=True)
    crudo = SALIDA / out['slug'] / 'raw' / f'{hoy.isoformat()}.json'
    crudo.parent.mkdir(parents=True, exist_ok=True)
    crudo.write_text(json.dumps({'consultas': qs, 'items': items}, ensure_ascii=False))
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    costo_txt = f'US${usd_real:.4f}' if usd_real is not None else f'~US${out["costo"]["estimado_usd"]:.4f} (Apify no reportó uso)'
    print(f'[escucha] {len(items)} crudas → {len(pubs)} útiles · descartes {descartes} · {costo_txt} · '
          f'{out["costo"]["segundos"]} s')
    for tema, t in por_tema.items():
        print(f'   {t["n"]:>4}  ({t["n_colombia"]:>3} de Colombia)  {tema}')
    print(f'[escucha] → {destino}')

    if not pubs:
        # Un cero no se sube: dejaría a la Rosa diciendo «nadie habla» cuando lo
        # más probable es que el actor haya fallado o cambiado de formato.
        print('[escucha] cero publicaciones útiles: NO se sube. Revisar campos_crudos del JSON.')
        return 1
    if a.subir:
        s3 = f'{S3_PREFIJO}/{out["slug"]}.json'
        r = subprocess.run(['aws', 's3', 'cp', str(destino), s3, '--content-type', 'application/json',
                            '--cache-control', 'private, max-age=300', '--only-show-errors'],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f'[escucha] subida FALLÓ: {r.stderr.strip()[:300]}')
            return 1
        print(f'[escucha] subido → {s3}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
