#!/usr/bin/env python3
"""Posturas de gremios y organizaciones en las ponencias de las reformas anteriores, con el modelo local.

Fuente: textos de la Gaceta del Congreso que ya están en s3://caudal-legislativo/gacetas-texto/.
Solo las ponencias de 2016 (foros regionales) y 2018 (audiencia pública) resumen lo que dijo cada
organización. Las de 2021, 2022 y 2024 solo listan quién asistió: de esas se saca la asistencia.
La frase de cada postura tiene que aparecer literal en la gaceta (sin contar espacios) o se descarta.

Uso: ollama serve  ·  python3 tools/ley-rescate/historia/gacetas.py   (≈ 20-30 min, gratis)"""
import json, re, sys, subprocess, urllib.request, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from actores import actores_en

BASE = Path(__file__).resolve().parents[3] / 'Bases de datos' / 'ley-rescate' / 'historia'
GAC = BASE / 'gacetas'; GAC.mkdir(parents=True, exist_ok=True)
MODELO = 'qwen3.8:27b'
# reforma, gaceta, desde, hasta (caracteres del texto), qué se saca, cómo se llama el espacio
SECCIONES = [
    ('r2016', '1090-2016', 3000, 42000, 'posturas', 'foros regionales sobre la reforma (oct-nov 2016)'),
    ('r2018', '1048-2018', 20000, 47000, 'posturas', 'audiencia pública del 20-nov-2018'),
    ('r2021b', '1068-2021', 4000, 12000, 'asistencia', 'foro de las comisiones económicas (mayo-jun 2021)'),
    ('r2022', '1200-2022', 6000, 22000, 'asistencia', 'audiencia pública del 31-ago-2022'),
    ('r2024', '2193-2024', 37000, 46000, 'asistencia', 'foro en la Comisión Tercera de Cámara (21-nov-2024)'),
]
SYS = ('Lees el resumen oficial (Gaceta del Congreso) de un foro o audiencia pública sobre una reforma tributaria en Colombia. '
       'Extrae SOLO las intervenciones atribuidas a una organización o persona NOMBRADA (no «varios intervinientes»). '
       'Para cada una devuelve: actor (organización, tal como aparece), persona (si aparece, si no ""), '
       'postura frente al proyecto: "apoya", "apoya con reparos", "reparos" o "rechaza"; '
       'temas: lista corta de lo que pide cambiar o defiende; frase: un fragmento COPIADO LITERALMENTE del texto, '
       'de 8 a 30 palabras, que sustente la postura. No inventes nada. Si no hay ninguna, devuelve lista vacía. '
       'Responde solo JSON: {"intervenciones":[...]}')

def texto(g):
    p = GAC / f'{g}.txt'
    if not p.exists():
        subprocess.run(['aws', 's3', 'cp', f's3://caudal-legislativo/gacetas-texto/{g}.txt', str(p), '--only-show-errors'], check=True)
    return p.read_text()

def llm(seg):
    body = {'model': MODELO, 'stream': False, 'format': 'json', 'options': {'num_ctx': 16384, 'temperature': 0},
            'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': seg}]}
    r = urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', data=json.dumps(body).encode(),
                                headers={'Content-Type': 'application/json'}), timeout=3600)
    return json.loads(json.load(r)['message']['content']).get('intervenciones', [])

sin_esp = lambda s: re.sub(r'[\s\-–—]+', '', s).lower()

def trozos(s, n=9000):
    out, i = [], 0
    while i < len(s):
        j = min(len(s), i + n)
        if j < len(s):
            k = s.rfind('\n', i + n - 1500, j)  # cortar en un salto de línea
            j = k if k > i else j
        out.append(s[i:j]); i = j
    return out

def main():
    cache = BASE / 'gacetas.json'
    res = json.loads(cache.read_text()) if cache.exists() else {}
    for rid, g, a, b, modo, esp in SECCIONES:
        t = texto(g); seg = t[a:b]
        num, anio = g.split('-')
        r = {'gaceta': f'Gaceta del Congreso {num} de {anio}', 'espacio': esp, 'asistentes': sorted(set(actores_en(seg))), 'posturas': []}
        if modo == 'posturas':
            if rid in res and res[rid].get('posturas'):
                r['posturas'] = res[rid]['posturas']
            else:
                plano = sin_esp(t)
                for k, tr in enumerate(trozos(seg)):
                    t0 = time.time()
                    for x in llm(tr):
                        f = (x.get('frase') or '').strip()
                        x['verificada'] = bool(f) and sin_esp(f)[:80] in plano
                        x['actores'] = actores_en(f'{x.get("actor","")} {x.get("persona","")}')
                        r['posturas'].append(x)
                    print(rid, 'trozo', k + 1, f'{time.time()-t0:.0f}s', len(r['posturas']), flush=True)
        res[rid] = r
        cache.write_text(json.dumps(res, ensure_ascii=False, indent=0))
        print(rid, 'asistentes:', ', '.join(r['asistentes']), '· posturas:', len(r['posturas']), flush=True)

if __name__ == '__main__':
    main()
