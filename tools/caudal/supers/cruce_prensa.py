#!/usr/bin/env python3
"""
Caudal · sanciones que salen en prensa y no están en el consolidado (nov-2026).

Por qué existe: el 2-nov-2026 un cruce a mano destapó que el pilar Regulatorio
llevaba meses sin refrescar varias fuentes. De 16 sanciones de superintendencias
reportadas en prensa entre junio y octubre, la base tenía 3. Nadie lo notó porque
cada fuente, vista sola, parecía estar bien.

Qué hace: busca en Google News las sanciones de cada superintendencia de los
últimos N días, saca el sancionado del titular con el mismo lector que usan los
comunicados oficiales (`harvest_comunicados.parse_titulo`) y lo busca en
`dist/sanciones.jsonl`. Lo que no aparece va a un reporte en Markdown.

No publica nada ni toca el consolidado: es un chequeo de cobertura. Un titular
sin captura no es error nuestro siempre: puede ser una sanción que la entidad
todavía no publica, o una que solo anuncia por prensa (Supersociedades no tiene
registro de sanciones). El reporte lo dice así.

Lee el consolidado PUBLICADO (`s3://caudal-legislativo/metadata/sanciones.jsonl`), que es
el que ve el cliente; con `--local`, el de `dist/s3/` de esta máquina.

Salida: `Bases de datos/leyes-senado/supers/cruce-prensa/AAAA-MM-DD.md`
Uso:    python3 tools/caudal/supers/cruce_prensa.py [--dias 30] [--local]
"""
import argparse
import tempfile
import datetime
import email.utils
import html
import json
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_comunicados as H          # noqa: E402  (lector de titulares)

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
OUT = BASE / 'cruce-prensa'

# superintendencia → (consultas, fuentes del consolidado que deberían tenerla)
SUPERS = {
    'SIC': (['"Superintendencia de Industria y Comercio" sanciona', 'SIC multa', 'Superindustria sanción'],
            ['sic', 'sic-firme', 'sic-circulares']),
    'Superfinanciera': (['Superfinanciera sanciona', 'Superfinanciera multa'], ['sfc-mercado-valores']),
    'Supersalud': (['Supersalud sanciona', 'Supersalud multa'], ['supersalud', 'supersalud-registro']),
    'Supersociedades': (['Supersociedades multa', 'Supersociedades sanciona'], ['supersociedades']),
    'Supertransporte': (['Supertransporte multa', 'Supertransporte sanciona'], ['supertransporte']),
    'INVIMA': (['Invima sanciona', 'Invima multa'], ['invima']),
}
_STOP = {'sas', 's.a.s', 'sa', 's.a', 'ltda', 'de', 'del', 'la', 'el', 'los', 'las', 'y', 'a', 'al', 'en',
         'colombia', 'empresa', 'compania', 'sociedad', 'grupo', 'por', 'con', 'millones'}


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def tokens(s):
    return [t for t in re.findall(r'[a-z0-9]+', fold(s)) if len(t) >= 3 and t not in _STOP]


def noticias(consulta, dias):
    u = ('https://news.google.com/rss/search?q=' + urllib.parse.quote(f'{consulta} when:{dias}d')
         + '&hl=es-419&gl=CO&ceid=CO:es-419')
    r = subprocess.run(['/usr/bin/curl', '-s', '-L', '-m', '30', '-A', 'Mozilla/5.0', u],
                       capture_output=True, text=True, timeout=45)
    for it in re.findall(r'<item>(.*?)</item>', r.stdout, re.S):
        t = re.search(r'<title>(.*?)</title>', it, re.S)
        d = re.search(r'<pubDate>(.*?)</pubDate>', it)
        m = re.search(r'<source[^>]*>(.*?)</source>', it)
        l = re.search(r'<link>(.*?)</link>', it)
        titulo = html.unescape(re.sub(r'<[^>]+>', '', t.group(1))) if t else ''
        titulo = re.sub(r'\s+-\s+[^-]+$', '', titulo).strip()     # quita « - Medio» del final
        yield {'titulo': titulo, 'medio': html.unescape(m.group(1)) if m else '',
               'fecha': email.utils.parsedate_to_datetime(d.group(1)).date().isoformat() if d else '',
               'url': l.group(1) if l else ''}


_SUPER_RX = re.compile(r'(?i)\b(superintendencia|superindustria|supersalud|superfinanciera|supersociedades|'
                       r'supertransporte|invima|sic|sfc|financiera|sociedades|industria|comercio|salud|transporte)\b')


def nombres_del_titulo(titulo):
    """Respaldo cuando el lector no saca el sancionado: las palabras con mayúscula
    del titular que no son la superintendencia."""
    ws = re.findall(r'\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.]{2,}', titulo)
    return ' '.join(w for w in ws[1:] if not _SUPER_RX.fullmatch(w))


def capturada(sancionado, filas):
    """¿Algún registro de esas fuentes nombra al sancionado? Exige 2 palabras
    distintivas en común (1 si el nombre solo tiene una), para no casar por
    palabras sueltas como «Colombia» o «hospital»."""
    tk = set(tokens(sancionado))
    if not tk:
        return None
    pide = 1 if len(tk) == 1 else 2
    for r in filas:
        if len(tk & r['_tk']) >= pide:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=30)
    ap.add_argument('--local', action='store_true', help='usa dist/s3 de esta máquina, no lo publicado en S3')
    a = ap.parse_args()
    if a.local:
        fuente_jsonl = BASE / 'dist' / 's3' / 'sanciones.jsonl'
    else:
        fuente_jsonl = Path(tempfile.mkdtemp()) / 'sanciones.jsonl'
        r = subprocess.run(['aws', 's3', 'cp', 's3://caudal-legislativo/metadata/sanciones.jsonl', str(fuente_jsonl),
                            '--only-show-errors'], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'  cruce con prensa · no pude bajar el consolidado de S3: {r.stderr.strip()[:200]}')
    hoy = datetime.date.today()
    desde = (hoy - datetime.timedelta(days=a.dias + 730)).isoformat()   # la prensa también reporta confirmaciones de sanciones viejas
    por_fuente = {}
    with fuente_jsonl.open(encoding='utf-8') as fh:
        for l in fh:
            r = json.loads(l)
            if (r.get('fecha') or '') >= desde:
                r['_tk'] = set(tokens(f"{r.get('sancionado')} {r.get('motivo')}"))
                por_fuente.setdefault(r['fuente'], []).append(r)
    filas_md, n_total, n_falta = [], 0, 0
    for sup, (consultas, fuentes) in SUPERS.items():
        filas = [r for f in fuentes for r in por_fuente.get(f, [])]
        vistos = set()
        for q in consultas:
            for n in noticias(q, a.dias):
                if not H.es_sancion(n['titulo']):
                    continue
                s = (H.parse_titulo(n['titulo']).get('sancionado') or '').strip() or nombres_del_titulo(n['titulo'])
                clave = ' '.join(sorted(tokens(s))) or n['titulo'][:60]
                if clave in vistos:
                    continue
                vistos.add(clave)
                n_total += 1
                hit = capturada(s, filas) if s else None
                if not hit:
                    n_falta += 1
                filas_md.append((sup, n, s, hit))
    filas_md.sort(key=lambda x: (x[0], bool(x[3]), x[1]['fecha']))
    OUT.mkdir(parents=True, exist_ok=True)
    md = [f'# Sanciones en prensa contra el consolidado · {hoy.isoformat()}', '',
          f'Últimos {a.dias} días. {n_total} sanciones distintas en prensa; **{n_falta} sin captura** '
          '(o sin sancionado legible en el titular). Que falte no siempre es error: la entidad puede no '
          'haberla publicado todavía, y Supersociedades no tiene registro de sanciones.', '',
          '| Superintendencia | Fecha | En la base | Sancionado | Titular | Medio |', '|---|---|---|---|---|---|']
    for sup, n, s, hit in filas_md:
        base = f"sí · {hit['fuente']} {hit.get('fecha') or ''}" if hit else ('no' if s else 'sin sancionado legible')
        md.append(f"| {sup} | {n['fecha']} | {base} | {s or '—'} | [{n['titulo'][:110]}]({n['url']}) | {n['medio']} |")
    (OUT / f'{hoy.isoformat()}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'  cruce con prensa · {n_total} sanciones en {a.dias} días · {n_falta} sin captura → '
          f'cruce-prensa/{hoy.isoformat()}.md')


if __name__ == '__main__':
    main()
