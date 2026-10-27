#!/usr/bin/env python3
"""
Caudal · Superintendencia Nacional de Salud (fase 2, oct-2026).

Sus sanciones, el registro de actos y los comunicados de intervención ya entran
por el pilar Regulatorio. Esto suma tres cosas, todas por SharePoint anónimo:

  circulares   búsqueda `/_api/search/query` sobre la biblioteca
               docs.supersalud.gov.co/PortalWeb/Juridica/CircularesExterna (solo
               PDF). El asunto viene en la propiedad `DescripcionOWSMTXT` y el
               número en `NumeroOWSTEXT` (no hay que leer el PDF).
  boletín      misma búsqueda sobre Juridica/BoletinJuridico (47 trimestrales).
  consultas    los proyectos de circular para comentarios NO tienen biblioteca:
               se anuncian como noticia («Participe en la consulta pública…»).
               La página de la noticia no trae el cuerpo sin JavaScript; la API
               de la lista sí: `…/Comunicaciones/_api/web/lists/getbytitle('Noticias')/items`
               (campo `Contenido_x0020_para_x0020_Notic0`, con el plazo «hasta el
               3 de noviembre de 2026» y el enlace al proyecto).

Salida: `Bases de datos/caudal-entidades/raw/supersalud/{proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_supersalud.py fetch
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys
import urllib.parse

import comun as C

ACC = 'application/json;odata=nometadata'
BUSCA = 'https://www.supersalud.gov.co/es-co/_api/search/query'
DOCS = 'https://docs.supersalud.gov.co/PortalWeb/Juridica/'
NOTICIAS = "https://wcmportal.supersalud.gov.co/portalweb/Comunicaciones/_api/web/lists/getbytitle('Noticias')/items"
OUT = C.RAW / 'supersalud'
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}


def _buscar(biblioteca, props, maxi=600):
    filas, start = [], 0
    while start < maxi:
        q = urllib.parse.urlencode({
            'querytext': f"'path:\"{DOCS}{biblioteca}\" FileExtension:pdf'",
            'sortlist': "'Write:descending'", 'rowlimit': '100', 'startrow': str(start),
            'selectproperties': "'" + ','.join(props) + "'"})
        d = json.loads(C.curl(f'{BUSCA}?{q}', accept=ACC, timeout=90))
        rel = d['PrimaryQueryResult']['RelevantResults']
        rows = rel['Table']['Rows']
        for r in rows:
            filas.append({c['Key']: c['Value'] for c in r['Cells']})
        start += len(rows)
        if not rows or start >= rel.get('TotalRows', 0):
            break
    return filas


def circulares():
    out = []
    for c in _buscar('CircularesExterna', ['Title', 'Path', 'Write', 'Created', 'NumeroOWSTEXT', 'DescripcionOWSMTXT']):
        t = c.get('Title') or ''
        if not re.match(r'(?i)circular', t):
            continue                           # anexos (tablas de referencia, formatos)
        num = (c.get('NumeroOWSTEXT') or '').strip()
        m = re.search(r'(?i)de\s+(\d{4})', t)
        anio = m.group(1) if m else (c.get('Created') or '')[:4]
        desc = C.limpio(c.get('DescripcionOWSMTXT') or '')
        out.append({'tipo': 'CIRCULARES', 'subtipo': 'Circular externa',
                    'numero': num or (re.search(r'(\d[\d-]{2,})', t) or [None, ''])[1], 'anio': anio,
                    'fecha': (c.get('Created') or '')[:10], 'titulo': C.limpio(t),
                    'descripcion': (desc[:1] + desc[1:].lower()) if desc.isupper() else (desc or C.limpio(t)),
                    'url': c.get('Path') or ''})
    return out


def boletines():
    out = []
    for c in _buscar('BoletinJuridico', ['Title', 'Path', 'Created']):
        t = C.limpio(c.get('Title') or '')
        m = re.search(r'No\.?\s*(\d+)', t)
        out.append({'tipo': 'BOLETINES', 'subtipo': 'Boletín jurídico', 'numero': m.group(1) if m else '',
                    'anio': (c.get('Created') or '')[:4], 'fecha': (c.get('Created') or '')[:10],
                    'titulo': t, 'descripcion': t, 'url': c.get('Path') or ''})
    return out


def _hasta(txt):
    m = re.search(r'(?i)hasta\s+el\s+(?:d[ií]a\s+)?(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de\s+(\d{4}))?', txt or '')
    if not m or m.group(2).lower() not in MESES:
        return ''
    anio = m.group(3) or str(datetime.date.today().year)
    try:
        return datetime.date(int(anio), MESES[m.group(2).lower()], int(m.group(1))).isoformat()
    except ValueError:
        return ''


def consultas(prev):
    q = ("?$select=Id,Title,Resena,Contenido_x0020_para_x0020_Notic0,Created"
         "&$orderby=Created%20desc&$top=300")
    filas = json.loads(C.curl(NOTICIAS + q, accept=ACC, timeout=90)).get('value', [])
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for r in filas:
        tit = C.limpio(r.get('Title') or '')
        if not re.search(r'(?i)consulta p[uú]blica|comentarios|observaciones', tit + ' ' + (r.get('Resena') or '')):
            continue
        cuerpo_html = r.get('Contenido_x0020_para_x0020_Notic0') or ''
        cuerpo = C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', cuerpo_html)))
        if not re.search(r'(?i)proyecto', tit + ' ' + cuerpo):
            continue
        links = [html.unescape(u) for u in re.findall(r'href="([^"]+)"', cuerpo_html)]
        doc = next((u for u in links if re.search(r'(?i)\.(pdf|docx?)$|proyecto', u)), links[0] if links else '')
        mo = re.search(r'(?i)(proyecto de (?:circular externa|resoluci[oó]n|circular)[^.]{0,400})', cuerpo)
        # la misma consulta se anuncia a veces en dos noticias: manda el documento
        k = hashlib.sha1(doc.encode()).hexdigest()[:16] if doc else str(r['Id'])
        if k in vivos:
            continue
        vivos[k] = {'id': k, 'tipo_norma': 'Proyecto de circular externa' if 'circular' in C.fold(tit + cuerpo)
                    else 'Proyecto normativo', 'titulo': (mo.group(1) if mo else tit).strip(' .'),
                    'objeto': C.limpio(r.get('Resena') or '')[:600], 'dependencia': '',
                    'fecha_inicio': (r.get('Created') or '')[:10], 'fecha_fin': _hasta(cuerpo),
                    'comentarios_a': 'formulario de participación ciudadana' if 'formulario' in cuerpo.lower() else '',
                    'url': doc, 'anexos': [u for u in links if u != doc][:3],
                    'creado': (r.get('Created') or '')[:10], 'visto': hoy, 'vigente_en_fuente': True,
                    'noticia': f'https://wcmportal.supersalud.gov.co/portalweb/Comunicaciones/Lists/Noticias/Noticia.aspx?ID={r["Id"]}'}
    out = dict(prev)
    out.update(vivos)
    return out, len(vivos)


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, n = consultas(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': items})
        hoy = datetime.date.today().isoformat()
        print(f'  supersalud · {n} consultas en las noticias recientes · '
              f'{sum(1 for v in items.values() if (v["fecha_fin"] or "") >= hoy)} abiertas · {len(items)} acumuladas')
    except Exception as e:
        ok = False
        print(f'  supersalud · consultas FALLÓ ({e})', file=sys.stderr)
    try:
        ce, bo = circulares(), boletines()
        if len(ce) < 30:
            raise RuntimeError(f'solo {len(ce)} circulares')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': ce + bo})
        print(f'  supersalud · {len(ce)} circulares externas · {len(bo)} boletines jurídicos')
    except Exception as e:
        ok = False
        print(f'  supersalud · normas FALLÓ ({e}) — se conserva el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
