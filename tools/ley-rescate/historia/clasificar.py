#!/usr/bin/env python3
"""Clasifica con el modelo local la postura de cada actor nombrado en los titulares de prensa histórica.

Entrada: historia/prensa.json · Salida: historia/prensa-clas.json {clave: {actor: 'a'|'m'|'r'|'n'}}
'n' = el titular nombra al actor pero no dice su postura frente a ESA reforma (o es de otro tema).
Caché por titular: re-correr solo clasifica lo nuevo. Uso: ollama serve · python3 …/clasificar.py"""
import json, re, sys, time, urllib.request, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from actores import REFORMAS, ACTORES

BASE = Path(__file__).resolve().parents[3] / 'Bases de datos' / 'ley-rescate' / 'historia'
MODELO = 'qwen3.8:27b'
NOM = {a[0]: a[1] for a in ACTORES}
RN = {r[0]: r[1] for r in REFORMAS}
SYS = ('Clasificas titulares de prensa colombiana sobre una reforma tributaria. Para cada titular y cada actor indicado, '
       'di qué postura frente a ESA reforma expresa el titular sobre ese actor: '
       '"a" apoya o la defiende; "m" apoya con reparos, pide cambios a partes o advierte efectos sin rechazarla entera; '
       '"r" la rechaza, se opone o anuncia voto en contra; "n" el titular no dice la postura de ese actor o habla de otro tema. '
       'Solo cuenta lo que dice el titular. Si el actor solo es nombrado por otros, es "n". '
       'Responde solo JSON: {"r":[{"i":número,"actor":"id","p":"a|m|r|n"}]}')

def clave(rid, t): return rid + ':' + hashlib.sha1(t.encode()).hexdigest()[:12]

def llm(rid, lote):
    user = f'Reforma: {RN[rid]}\n' + '\n'.join(f'{k}. «{x["t"]}» — actores: ' + ', '.join(f'{a} ({NOM[a]})' for a in x['actores']) for k, x in enumerate(lote))
    body = {'model': MODELO, 'stream': False, 'format': 'json', 'options': {'num_ctx': 8192, 'temperature': 0},
            'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}]}
    r = urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', data=json.dumps(body).encode(),
                                headers={'Content-Type': 'application/json'}), timeout=3600)
    return json.loads(json.load(r)['message']['content']).get('r', [])

def main():
    P = json.loads((BASE / 'prensa.json').read_text())
    sal = BASE / 'prensa-clas.json'
    C = json.loads(sal.read_text()) if sal.exists() else {}
    for rid, L in P.items():
        falta = [x for x in L if clave(rid, x['t']) not in C]
        for i in range(0, len(falta), 20):
            lote = falta[i:i + 20]; t0 = time.time()
            for z in llm(rid, lote):
                try: x = lote[int(z['i'])]
                except Exception: continue
                if z.get('actor') in x['actores'] and z.get('p') in ('a', 'm', 'r', 'n'):
                    C.setdefault(clave(rid, x['t']), {})[z['actor']] = z['p']
            for x in lote: C.setdefault(clave(rid, x['t']), {})
            sal.write_text(json.dumps(C, ensure_ascii=False))
            print(rid, i + len(lote), '/', len(falta), f'{time.time()-t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
