#!/usr/bin/env python3
"""build_estructura.py — destila la ESTRUCTURA del razonamiento judicial (la ratio
decidendi propiamente dicha) por tipo de caso, desde la parte considerativa del corpus.

POR QUÉ EXISTE (la corrección a build_ratio.py):
`build_ratio.py` extrae, de cada sentencia, POR QUÉ se cayó ESE caso — una
descripción episódica que luego se etiqueta con una taxonomía de 8 motivos. Eso
sirve para citar precedente, pero NO es la ratio decidendi: no dice qué regla
aplica el juez, qué elementos exige, en qué orden los analiza, ni qué prueba
satisface cada elemento. Sin esa estructura, 573 sentencias son 573 anécdotas.

Este script va a la PARTE CONSIDERATIVA, donde la Corte enuncia las reglas
(patrón canónico de la jurisprudencia colombiana: enumeraciones "(i)… (ii)… (iii)"
introducidas por lenguaje de regla), y destila:

  elemento del test · nivel (procedibilidad|fondo|pretensión accesoria) ·
  qué exige · qué lo prueba · sentencias que lo enuncian

Dos filtros que importan (medidos, no supuestos):
- ALEGATOS DE PARTE: el mismo patrón "(i)…(ii)…" lo usan la EPS y el accionante
  para listar sus argumentos ("La EPS se opuso… debido a que (i) hecho superado…").
  Eso NO es regla. Se descarta por marcadores de parte.
- PRETENSIONES ACCESORIAS: en casos de "medicamentos", solo el 10% de las
  negativas versa sobre el medicamento; el resto es transporte, cuidador,
  pañales y tratamiento integral, y CADA UNA tiene su propio test. La estructura
  tiene que separarlas o mezcla reglas que no se aplican al mismo objeto.

Uso:
  export DEEPSEEK_API_KEY=...
  python3 tools/tutela-analiza/build_estructura.py medicamentos
  python3 tools/tutela-analiza/build_estructura.py medicamentos --limit 40   # prueba
"""
import argparse
import gzip
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'tutelas-salud' / 'relatoria'
CORPUS = BASE / 'corpus-salud.jsonl.gz'
OUT_TPL = 'estructura-{caso}.json'

PROMPT_VERSION = 'e1-2026-08-06'
DEEPSEEK_URL = os.environ.get('DEEPSEEK_URL', 'https://api.deepseek.com/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
HTTP_TIMEOUT = 90
RATE_IN, RATE_OUT = 0.30, 1.20  # USD/M conservador, para el freno de presupuesto

# El resolver de macOS se satura con ráfagas concurrentes (ver build_ratio.py)
_dns = {}
_gai0 = socket.getaddrinfo
socket.getaddrinfo = lambda h, *a, **k: _dns.setdefault((h,) + a, _gai0(h, *a, **k))

# ── extracción de bloques de regla ──
ENUM = re.compile(r'[^.]{0,300}?\(i\)(?:(?!\(i\)).){80,1400}?\(iii\).{0,300}?[.]', re.S)
# lenguaje de REGLA (la Corte enunciando doctrina)
REGLA = re.compile(r'requisit|regla|subregla|sub-regla|procedencia|criterio|exig|'
                   r'deber[aá]|proceder[aá]|jurisprudencia|esta Corte|esta Corporaci|'
                   r'ha establecido|ha se[ñn]alado|ha reiterado', re.I)
# ALEGATO de parte (mismo patrón sintáctico, no es regla) — filtro medido
PARTE = re.compile(r'\b(la EPS|la entidad|la accionada|el accionante|la accionante|'
                   r'el actor|la actora|el demandante)\b[^.]{0,120}?\b(se opuso|solicit|'
                   r'argument|aleg|manifest|contest|indic[oó] que|afirm)', re.I)
# ENUNCIADO NORMATIVO: sin esto la "cita" es una etiqueta temática, no una regla.
# Medido en la 1ª corrida: sin el filtro, el 83% de las citas eran solo el nombre
# del tema ("legitimación en la causa por activa"), textuales pero inservibles.
NORMATIVA = re.compile(r'\b(debe|deber[aá]n?|procede|proceder[aá]|requiere|requisit|exig|'
                       r'corresponde|no podr|solo cuando|siempre que|es necesario|'
                       r'tendr[aá]|habr[aá] de|est[aá] obligad)\b|\(i\)|\(ii\)', re.I)
CITA_MIN = 60

CASO_OBJ = {
    'medicamentos': 'la entrega de medicamentos o insumos ya formulados',
    'citas': 'la asignación oportuna de citas o consultas médicas',
    'procedimientos': 'la práctica oportuna de un procedimiento ya ordenado',
}

SYSTEM = """Eres un abogado constitucionalista colombiano experto en la línea jurisprudencial de salud de la Corte Constitucional. Recibes FRAGMENTOS de la parte considerativa de sentencias T, donde la Corte enuncia reglas y requisitos.

Tu tarea NO es resumir el caso. Es extraer la ESTRUCTURA DEL TEST: qué elementos debe verificar el juez, qué exige cada uno y qué lo prueba.

Devuelve JSON estricto:
{
 "elementos": [
   {
     "elemento": "nombre corto y estándar del elemento (ej: 'Orden del médico tratante', 'Subsidiariedad', 'Capacidad económica')",
     "nivel": "procedibilidad" | "fondo" | "accesoria",
     "objeto": "a qué pretensión aplica: 'general' | 'medicamento' | 'tratamiento integral' | 'transporte' | 'cuidador o enfermería' | 'insumos o pañales'",
     "exige": "qué tiene que darse para que el elemento se cumpla, 1-2 frases precisas",
     "prueba": "con qué se acredita en la práctica (documento, hecho), 1 frase; null si el fragmento no lo dice",
     "cita": "frase COPIADA TEXTUALMENTE del fragmento que ENUNCIA LA REGLA (máx 300 caracteres); null si el fragmento no la enuncia"
   }
 ]
}

QUÉ CUENTA COMO "cita" (esto es lo que más se hace mal):
La cita tiene que ser el ENUNCIADO NORMATIVO — la frase donde la Corte dice qué se
debe cumplir. Debe contener un verbo de deber o de procedencia (debe, deberá, procede,
requiere, exige, corresponde, solo cuando, siempre que) o una enumeración de requisitos.
  SIRVE:    "para la procedencia del transporte se requiere que (i) el tratamiento sea
             imprescindible... (ii) el paciente carezca de recursos"
  NO SIRVE: "legitimación en la causa por activa"  ← es el NOMBRE del tema, no la regla
  NO SIRVE: "el fenómeno de la carencia actual de objeto"  ← etiqueta temática
Si en el fragmento solo aparece el nombre del tema y no su enunciado, pon cita: null.
Una cita nula es correcta; una etiqueta disfrazada de cita no.

Reglas duras:
1. Solo extrae elementos que el fragmento ENUNCIE COMO REGLA GENERAL. Si el fragmento narra lo que pasó en un caso concreto o lo que alegó una parte, devuelve "elementos": [].
2. "nivel": procedibilidad = requisitos para que la tutela sea estudiable (legitimación, subsidiariedad, inmediatez, carencia de objeto). fondo = requisitos del derecho reclamado. accesoria = reglas propias de una pretensión distinta del servicio principal (transporte, cuidador, tratamiento integral, insumos).
3. La "cita" debe ser copia LITERAL del fragmento, se verificará por software.
4. Nombra el elemento de forma ESTÁNDAR y reutilizable, no pegado al caso: 'Orden del médico tratante', no 'la orden de la Dra. Pérez'.
5. Máximo 5 elementos por fragmento. JSON estricto, sin markdown."""

_lock = threading.Lock()
_spent = {'in': 0, 'out': 0, 'usd': 0.0, 'calls': 0}


def norm(s):
    if not s:
        return ''
    s = (s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
          .replace('–', '-').replace('—', '-').replace(' ', ' '))
    return re.sub(r'\s+', ' ', s).strip().lower()


def call_llm(user, max_tokens=4000):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
        'temperature': 0.1, 'response_format': {'type': 'json_object'}, 'max_tokens': max_tokens,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        data = json.loads(r.read().decode('utf-8'))
    ch = data['choices'][0]
    content = ch['message'].get('content') or ''
    u = data.get('usage', {})
    with _lock:
        _spent['in'] += u.get('prompt_tokens', 0)
        _spent['out'] += u.get('completion_tokens', 0)
        _spent['usd'] = _spent['in'] / 1e6 * RATE_IN + _spent['out'] / 1e6 * RATE_OUT
        _spent['calls'] += 1
    if not content:
        raise ValueError(f"content vacío (finish_reason={ch.get('finish_reason')})")
    return json.loads(content)


def extraer_bloques(caso):
    """Bloques de enunciación de regla, ya filtrados de alegatos de parte."""
    bloques, n_sent, n_alegato = [], 0, 0
    with gzip.open(CORPUS, 'rt', encoding='utf-8') as f:
        for line in f:
            p = json.loads(line)
            if caso not in (p.get('casos') or []):
                continue
            n_sent += 1
            vistos = set()
            for m in ENUM.finditer(p['texto']):
                t = re.sub(r'\s+', ' ', m.group(0)).strip()
                if len(t) > 1800 or not REGLA.search(t[:400]):
                    continue
                if PARTE.search(t[:300]):       # alegato de parte, no regla
                    n_alegato += 1
                    continue
                k = norm(t)[:120]
                if k in vistos:
                    continue
                vistos.add(k)
                bloques.append({'sentencia': p['sentencia'], 'ano': p['ano'],
                                'url': p.get('url', ''), 'texto': t})
    return bloques, n_sent, n_alegato


def procesar(b, budget):
    with _lock:
        if _spent['usd'] >= budget:
            return None
    user = f"SENTENCIA {b['sentencia']} ({b['ano']})\n\nFRAGMENTO:\n{b['texto']}"
    out = None
    for intento in range(4):
        try:
            try:
                out = call_llm(user)
            except ValueError:
                out = call_llm(user, 8000)
            break
        except (urllib.error.URLError, TimeoutError, OSError):
            if intento == 3:
                return None
            time.sleep(3 * (intento + 1))
        except Exception as e:
            print(f"  [!] {b['sentencia']}: {e}", file=sys.stderr)
            return None
    if not out:
        return None
    fuente = norm(b['texto'])
    els = []
    for e in (out.get('elementos') or [])[:5]:
        if not isinstance(e, dict) or not e.get('elemento'):
            continue
        # doble filtro: (1) textual verificada contra el fragmento fuente,
        # (2) que ENUNCIE una regla y no sea el nombre del tema
        cita = e.get('cita')
        if not (isinstance(cita, str) and len(cita.strip()) >= CITA_MIN
                and NORMATIVA.search(cita) and norm(cita) in fuente):
            cita = None
        els.append({
            'elemento': str(e['elemento'])[:80].strip(),
            'nivel': e.get('nivel') if e.get('nivel') in ('procedibilidad', 'fondo', 'accesoria') else 'fondo',
            'objeto': str(e.get('objeto') or 'general')[:40],
            'exige': str(e.get('exige') or '')[:400],
            'prueba': (str(e['prueba'])[:250] if e.get('prueba') else None),
            'cita': cita.strip()[:300] if cita else None,
            'sentencia': b['sentencia'], 'ano': b['ano'], 'url': b['url'],
        })
    return els


def clave(nombre):
    """Normaliza el nombre del elemento para agrupar variantes."""
    s = norm(nombre)
    s = re.sub(r'^(el|la|los|las|de|del)\s+', '', s)
    s = re.sub(r'[^a-záéíóúñ ]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('caso', choices=list(CASO_OBJ))
    ap.add_argument('--budget', type=float, default=0.50)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    if not DEEPSEEK_API_KEY:
        sys.exit('Falta DEEPSEEK_API_KEY.')

    bloques, n_sent, n_alegato = extraer_bloques(args.caso)
    print(f"{args.caso}: {n_sent} sentencias · {len(bloques)} bloques de regla "
          f"({n_alegato} descartados por ser alegato de parte)")
    if args.limit:
        bloques = bloques[:args.limit]

    t0 = time.time()
    todos = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(procesar, b, args.budget) for b in bloques]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r:
                todos.extend(r)
            if i % 40 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} · ${_spent['usd']:.3f} · {len(todos)} elementos", flush=True)

    # consolidar por elemento normalizado
    grupos = {}
    for e in todos:
        k = clave(e['elemento'])
        g = grupos.setdefault(k, {'elemento': e['elemento'], 'niveles': {}, 'objetos': {},
                                  'exige': [], 'prueba': [], 'citas': [], 'sentencias': set()})
        g['niveles'][e['nivel']] = g['niveles'].get(e['nivel'], 0) + 1
        g['objetos'][e['objeto']] = g['objetos'].get(e['objeto'], 0) + 1
        g['exige'].append(e['exige'])
        if e['prueba']:
            g['prueba'].append(e['prueba'])
        if e['cita']:
            g['citas'].append({'sentencia': e['sentencia'], 'ano': e['ano'],
                               'url': e['url'], 'cita': e['cita']})
        g['sentencias'].add(e['sentencia'])

    salida = []
    for k, g in grupos.items():
        nivel = max(g['niveles'].items(), key=lambda kv: kv[1])[0]
        objeto = max(g['objetos'].items(), key=lambda kv: kv[1])[0]
        g['citas'].sort(key=lambda c: c['ano'], reverse=True)
        salida.append({
            'key': k, 'elemento': g['elemento'], 'nivel': nivel, 'objeto': objeto,
            'n_menciones': len(g['exige']), 'n_sentencias': len(g['sentencias']),
            'exige': sorted(g['exige'], key=len, reverse=True)[0],
            'exige_variantes': sorted(set(g['exige']), key=len, reverse=True)[:4],
            'prueba': sorted(g['prueba'], key=len, reverse=True)[0] if g['prueba'] else None,
            'citas': g['citas'][:5],
            'sentencias': sorted(g['sentencias'], reverse=True)[:12],
        })
    salida.sort(key=lambda e: -e['n_sentencias'])

    doc = {
        'v': PROMPT_VERSION, 'caso': args.caso, 'objeto': CASO_OBJ[args.caso],
        'generado': time.strftime('%Y-%m-%d'), 'modelo': DEEPSEEK_MODEL,
        'fuente': 'Corte Constitucional · parte considerativa de sentencias T de salud',
        'universo': {'sentencias': n_sent, 'bloques_regla': len(bloques),
                     'bloques_descartados_alegato': n_alegato,
                     'elementos_extraidos': len(todos), 'elementos_unicos': len(salida)},
        'costo': {'usd_estimado': round(_spent['usd'], 4), 'llamadas': _spent['calls']},
        'elementos': salida,
    }
    out = BASE / OUT_TPL.format(caso=args.caso)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"\n✔ {out.name}: {len(salida)} elementos únicos de {len(todos)} extracciones · "
          f"${_spent['usd']:.3f} · {time.time()-t0:.0f}s")
    for e in salida[:12]:
        print(f"  [{e['nivel'][:4]}·{e['objeto'][:12]:12s}] {e['elemento'][:48]:48s} "
              f"{e['n_sentencias']:3d} sent · {len(e['citas'])} citas")


if __name__ == '__main__':
    main()
