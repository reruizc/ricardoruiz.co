#!/usr/bin/env python3
"""consolida_estructura.py — segundo pase: agrupa los elementos extraídos en el
TEST canónico y los ordena como los analiza un juez.

Por qué hace falta: `build_estructura.py` extrae elemento por elemento desde
cada fragmento, así que el mismo requisito llega con nombres distintos
("Capacidad económica" / "Incapacidad económica" / "Falta de capacidad
económica") y queda contado tres veces. La normalización por string no los une
—son palabras distintas, y una es la negación de la otra—, así que la
consolidación la hace el modelo sobre la LISTA de nombres, no sobre el texto.

Lo que produce es el entregable de verdad: el test por etapas, con el orden en
que se verifica, qué exige cada elemento, qué lo prueba y qué sentencias lo
enuncian. Las citas NO las genera el modelo: se arrastran verificadas desde el
paso anterior.

Uso:
  export DEEPSEEK_API_KEY=...
  python3 tools/tutela-analiza/consolida_estructura.py medicamentos
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'tutelas-salud' / 'relatoria'
DEEPSEEK_URL = os.environ.get('DEEPSEEK_URL', 'https://api.deepseek.com/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

SYSTEM = """Eres un abogado constitucionalista colombiano experto en la línea jurisprudencial de salud de la Corte Constitucional.

Recibes una lista de ELEMENTOS extraídos de la parte considerativa de sentencias T (cada uno con cuántas sentencias lo enuncian y qué exige). Muchos son el MISMO requisito con nombres distintos.

Tu tarea: consolidarlos en el TEST que efectivamente aplica un juez, ordenado como lo analiza.

Devuelve JSON estricto:
{
 "etapas": [
   {
     "etapa": "nombre de la etapa (ej: 'Procedibilidad', 'Fondo: el servicio reclamado', 'Pretensiones accesorias')",
     "orden": 1,
     "porque_va_aqui": "por qué el juez analiza esto en este momento, 1 frase",
     "elementos": [
       {
         "nombre": "nombre canónico del elemento",
         "keys": ["key1","key2"],   // las keys de entrada que agrupas aquí — copia EXACTA
         "exige": "qué debe darse, 1-2 frases",
         "prueba": "con qué se acredita en la práctica, 1 frase",
         "si_falla": "qué pasa si no se cumple (rechazo, improcedencia, negativa de esa pretensión), 1 frase"
       }
     ]
   }
 ]
}

Reglas duras:
1. Agrupa sin piedad los sinónimos y las negaciones del mismo requisito ("capacidad económica", "incapacidad económica", "falta de capacidad de pago" son UN elemento).
2. Cada "key" de entrada debe aparecer en a lo sumo un elemento. No inventes keys: cópialas tal cual.
3. Descarta elementos que no sean requisitos del test (temas generales como "derecho a la salud", enunciados de contexto).
4. Ordena las etapas como las recorre el juez: primero lo que puede tumbar la tutela sin entrar al fondo.
5. Separa en su propia etapa las pretensiones ACCESORIAS (transporte, cuidador, tratamiento integral, insumos): tienen test propio.
6. No inventes requisitos que no estén en la lista. JSON estricto, sin markdown."""


def call(user, max_tokens=8000):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
        'temperature': 0.1, 'response_format': {'type': 'json_object'}, 'max_tokens': max_tokens,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode('utf-8'))
    ch = d['choices'][0]
    c = ch['message'].get('content') or ''
    if not c:
        raise ValueError(f"content vacío (finish={ch.get('finish_reason')})")
    return json.loads(c), d.get('usage', {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('caso')
    ap.add_argument('--min-sent', type=int, default=1,
                    help='descarta elementos enunciados en menos de N sentencias')
    args = ap.parse_args()
    if not DEEPSEEK_API_KEY:
        sys.exit('Falta DEEPSEEK_API_KEY.')

    src = BASE / f'estructura-{args.caso}.json'
    doc = json.loads(src.read_text(encoding='utf-8'))
    els = [e for e in doc['elementos'] if e['n_sentencias'] >= args.min_sent]
    idx = {e['key']: e for e in els}
    print(f"entrada: {len(els)} elementos únicos ({doc['universo']['sentencias']} sentencias)")

    lista = '\n'.join(
        f"- key={e['key']} · nombre=\"{e['elemento']}\" · nivel={e['nivel']} · objeto={e['objeto']} · "
        f"{e['n_sentencias']} sentencias · exige: {e['exige'][:180]}"
        for e in els)
    user = (f"CASO: tutelas por {doc['objeto']}\n\n"
            f"ELEMENTOS EXTRAÍDOS ({len(els)}):\n{lista}\n\n"
            "Consolida en el test por etapas. Recuerda: cada key en un solo elemento, copiadas tal cual.")

    out, usage = call(user)
    print(f"usage: {usage.get('total_tokens')} tokens")

    # rehidratar: conteos reales y citas VERIFICADAS del paso anterior
    usadas, etapas = set(), []
    for et in out.get('etapas', []):
        elems = []
        for e in et.get('elementos', []):
            keys = [k for k in (e.get('keys') or []) if k in idx and k not in usadas]
            usadas.update(keys)
            if not keys:
                continue
            fuentes = [idx[k] for k in keys]
            citas, sents = [], set()
            for f in fuentes:
                citas.extend(f['citas'])
                sents.update(f['sentencias'])
            vistas, uniq = set(), []
            for c in sorted(citas, key=lambda c: c['ano'], reverse=True):
                if c['sentencia'] in vistas:
                    continue
                vistas.add(c['sentencia'])
                uniq.append(c)
            elems.append({
                'nombre': str(e.get('nombre') or '')[:80],
                'exige': str(e.get('exige') or '')[:400],
                'prueba': str(e.get('prueba') or '')[:300],
                'si_falla': str(e.get('si_falla') or '')[:300],
                'n_sentencias': len(sents),
                'n_menciones': sum(f['n_menciones'] for f in fuentes),
                'agrupa': [idx[k]['elemento'] for k in keys],
                'citas': uniq[:4],
            })
        # Poda: al test publicable solo entra lo que tiene respaldo. Sin esto queda
        # una cola larga de "elementos" que no son requisitos verificables sino
        # temas doctrinales ("principios del SGSSS", "obligaciones del Estado").
        elems = [e for e in elems if e['n_sentencias'] >= 3 or e['citas']]
        if elems:
            elems.sort(key=lambda e: -e['n_sentencias'])
            etapas.append({'etapa': str(et.get('etapa') or '')[:80],
                           'orden': int(et.get('orden') or len(etapas) + 1),
                           'porque_va_aqui': str(et.get('porque_va_aqui') or '')[:300],
                           'elementos': elems})
    etapas.sort(key=lambda e: e['orden'])

    huerfanas = [k for k in idx if k not in usadas]
    doc_out = {
        'v': doc['v'], 'caso': doc['caso'], 'objeto': doc['objeto'],
        'generado': doc['generado'], 'fuente': doc['fuente'],
        'universo': doc['universo'],
        'consolidacion': {'elementos_entrada': len(els),
                          'elementos_consolidados': sum(len(e['elementos']) for e in etapas),
                          'descartados': len(huerfanas),
                          'poda': 'solo entran elementos con >=3 sentencias o >=1 cita normativa'},
        'etapas': etapas,
    }
    out_p = BASE / f'test-{args.caso}.json'
    out_p.write_text(json.dumps(doc_out, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"\n✔ {out_p.name}: {len(etapas)} etapas · "
          f"{doc_out['consolidacion']['elementos_consolidados']} elementos "
          f"(de {len(els)}; {len(huerfanas)} descartados)\n")
    for et in etapas:
        print(f"━━ {et['orden']}. {et['etapa'].upper()}")
        for e in et['elementos']:
            print(f"   • {e['nombre'][:52]:52s} {e['n_sentencias']:3d} sent · {len(e['citas'])} citas")


if __name__ == '__main__':
    main()
