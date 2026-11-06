#!/usr/bin/env python3
"""Titulares de prensa de cada reforma tributaria anterior, por actor (Google News con rango de fechas).

Salida: Bases de datos/ley-rescate/historia/prensa.json  {reforma: [{t, f, fecha, url, actores}]}
Se queda solo con titulares que nombran literal a un actor. Caché por consulta en historia/cache/."""
import json, re, sys, time, hashlib, html, urllib.parse, urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from actores import REFORMAS, ACTORES, actores_en

BASE = Path(__file__).resolve().parents[3] / 'Bases de datos' / 'ley-rescate' / 'historia'
CACHE = BASE / 'cache'; CACHE.mkdir(parents=True, exist_ok=True)
TEMA = re.compile(r'tributari|\bIVA\b|impuest|reforma|financiamiento|\bDian\b|DIAN|recaudo|\brenta\b|canasta|grava|gravá|gravam', re.I)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'

def rss(q):
    k = CACHE / (hashlib.sha1(q.encode()).hexdigest()[:16] + '.xml')
    if k.exists(): return k.read_text()
    u = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(q) + '&hl=es-419&gl=CO&ceid=CO:es-419'
    for i in range(3):
        try:
            x = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=30).read().decode('utf-8', 'replace')
            k.write_text(x); time.sleep(1.2); return x
        except Exception as e:
            time.sleep(5 * (i + 1))
    return ''

def items(x):
    for it in re.findall(r'<item>(.*?)</item>', x, re.S):
        g = lambda t: (re.search(rf'<{t}[^>]*>(.*?)</{t}>', it, re.S) or [None, ''])[1]
        tit = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', g('title'))).strip()
        src = html.unescape(g('source')).strip()
        if src and tit.endswith(' - ' + src): tit = tit[:-len(src) - 3].strip()
        try: fecha = parsedate_to_datetime(g('pubDate')).date().isoformat()
        except Exception: fecha = ''
        yield {'t': tit, 'f': src, 'fecha': fecha, 'url': html.unescape(g('link')).strip()}

def main():
    out = {}
    for rid, nom, terms, desde, hasta in REFORMAS:
        vistos = {}
        for a in ACTORES:
          # La consulta con el nombre de la reforma rinde poco antes de 2021 (Google Noticias guarda poco de esos años):
          # se suman consultas más amplias, y el clasificador marca «n» lo que no sea de la reforma.
          for j, q in enumerate([f'({" OR ".join(terms)}) {a[4]} after:{desde} before:{hasta}'] + [f'{a[4]} {x} after:{desde} before:{hasta}' for x in ('tributaria', 'IVA', 'impuestos')]):
            for it in items(rss(q)):
                if not (desde <= it['fecha'] <= hasta): continue
                if j and not TEMA.search(it['t']): continue  # en las consultas amplias, el titular tiene que ser de impuestos
                acts = actores_en(it['t'])
                if not acts: continue
                key = re.sub(r'\W+', '', it['t'].lower())[:90]
                if key in vistos: vistos[key]['actores'] = sorted(set(vistos[key]['actores']) | set(acts)); continue
                vistos[key] = {**it, 'actores': acts}
        out[rid] = sorted(vistos.values(), key=lambda x: x['fecha'])
        print(rid, len(out[rid]), 'titulares', flush=True)
    (BASE / 'prensa.json').write_text(json.dumps(out, ensure_ascii=False, indent=0))

if __name__ == '__main__':
    main()
