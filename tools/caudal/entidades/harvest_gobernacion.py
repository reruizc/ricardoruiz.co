#!/usr/bin/env python3
"""
Caudal · Gobernación de Antioquia · decretos y resoluciones por la Gaceta
Departamental (tanda 5, nov-2026).

La Gobernación no tiene buscador de normas: todo sale en la gaceta. Hay una página
Joomla por año con el enlace de cada edición, y cada edición es un PDF de unas 50
páginas (5 a 12 MB), casi siempre solo de decretos o solo de resoluciones.

  listado   /gaceta-departamental-AAAA · el año anterior vive en
            /normatividad/gaceta-departamental. ⚠️ Los nombres de archivo no son
            uniformes («25.973- D», «25.934 - R », «25.842 - R Ord. No. 24 y 25»):
            el número de gaceta sale del nombre y la URL se vuelve a codificar.
  sumario   página 2, digital y exacta: bloques «Número · Fecha · Página». Los
            números de 13 dígitos son el radicado del acto (AAAA07… decreto,
            AAAA06… resolución). Los bloques con número corto son ordenanzas: ya
            entran por la Asamblea y aquí se saltan.
  título    NO está en el sumario: se lee en la primera página de cada acto (OCR).
            ⚠️ Una de cada diez gacetas es un escaneo sin capa de texto. De esas
            quedan número, fecha y PDF, con `sin_texto`: el título se deja vacío,
            no se adivina. Se recuperan con OCR (ver integrar/territorio.md).

La gran mayoría son actos particulares de personal (nombramientos de docentes,
asignaciones salariales): se marcan `administrativo`, no se borran.

Cada edición se baja una sola vez y su lectura queda en `gacetas.json`.

Salida: `Bases de datos/caudal-entidades/raw/gobernacion-antioquia/{gacetas,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_gobernacion.py fetch [--anio 2026] [--max 60]
"""
import argparse
import concurrent.futures
import datetime
import html
import re
import sys
import tempfile
import urllib.parse

import comun as C

ENTIDAD = 'Gobernación de Antioquia'
BASE = 'https://www.antioquia.gov.co'
OUT = C.RAW / 'gobernacion-antioquia'
_MES = '|'.join(k for k in C.MESES)
_TITULO = re.compile(r'(?i)\bP[O0]R\s+(?:MEDIO\s+DE(?:L|\s+LA|\s+LOS|\s+LAS)\s+|(?:LA|EL|LOS|LAS)\s+)CUA[LI1](?:ES)?\b')
_FIRMA = (r'(?:EL|LA|LOS)\s+(?:GOBERNADOR|SECRETARI|SUBSECRETARI|DIRECTOR|GERENTE|JEFE|ASESOR|COORDINADOR|'
          r'L[ÍI]DER|PROFESIONAL|SUPERVISOR|ASAMBLEA|COMIT[ÉE]|COMISI[ÓO]N)')
_FIN = re.compile(rf'(?mi)^\s*{_FIRMA}|\ben\s+uso\s+de\b|\bconferidas?\b|^\s*CONSIDERANDO')
_DEP = re.compile(rf'(?mi)^\s*(?:EL|LA|LOS)\s+((?:GOBERNADOR|SECRETARI|SUBSECRETARI|DIRECTOR|GERENTE|JEFE|ASESOR|COORDINADOR|L[ÍI]DER)[^,\n]{{0,90}})')

# Actos particulares que el `_ADMIN` de comun.py no alcanza: la gaceta los trae por
# cientos (docentes, pensiones, situaciones de personal).
_PARTICULAR = re.compile(
    r'(?i)\b(nombramiento|provisionalidad|per[íi]odo\s+de\s+prueba|asignaci[óo]n\s+salarial|escalaf[óo]n|'
    r'traslados?\s+(?:de\s+)?(?:un|una|unos|unas|docente|educador|directivo|por\s+)|reubic|encargo|renuncia|'
    r'licencia|permiso|comisi[óo]n\s+(?:de\s+)?(?:servicios|estudios)|vacaciones|'
    r'cesant[íi]as|pensi[óo]n|pensional|sustituci[óo]n|prima\s+de|bonificaci[óo]n|auxilio\s+funerario|'
    r'reconoce\s+(?:y\s+ordena\s+)?(?:una?|el|la)\b|docente|educador|'
    r'insubsistencia|retiro|incapacidad|sanci[óo]n\s+disciplinaria|'
    r'revoca\s+(?:un|una)\s+nombramiento|incumplimiento\s+de\s+un\s+cr[ée]dito|novedad(?:es)?\s+en\s+la\s+planta|'
    r'lista\s+de\s+elegibles|acci[óo]n\s+comunal|organismo\s+comunal|personer[íi]a\s+jur[íi]dica|dignatarios|'
    r'contrataci[óo]n\s+directa|contrato\s+interadministrativo|proceso\s+de\s+selecci[óo]n|adjudica|'
    r'comisi[óo]n\s+remunerada|condecoraci[óo]n|escudo\s+de\s+antioquia|desistimiento|comit[ée]s?\s+asesor|'
    r'costos\s+educativos|modalidad\s+de\s+(?:un|contrataci)|programas\s+de\s+formaci[óo]n)')


def particular(titulo):
    return C.es_administrativo(titulo) or bool(_PARTICULAR.search((titulo or '')[:300]))


def paginas(ruta):
    """Texto de todas las páginas de un PDF. La EC2 solo trae pypdf."""
    try:
        import pymupdf
        with pymupdf.open(ruta) as d:
            return [p.get_text() for p in d]
    except ImportError:
        from pypdf import PdfReader
        return [(p.extract_text() or '') for p in PdfReader(ruta).pages]


def listado(anio):
    """{'25.998': url} de un año. ⚠️ Los href traen espacios y comas sin codificar."""
    for ruta in (f'/gaceta-departamental-{anio}', '/normatividad/gaceta-departamental'):
        try:
            h = C.curl(BASE + ruta, timeout=90)
        except RuntimeError:
            continue
        out = {}
        for href in re.findall(rf'href="(/images/gaceta/{anio}/\d\d/[^"]+?\.pdf)"', h):
            href = urllib.parse.unquote(html.unescape(href))
            m = re.search(r'(\d{2}\.\d{3})', href)
            if m:
                out.setdefault(m.group(1), BASE + urllib.parse.quote(href, safe='/.-_'))
        if out:
            return out
    return {}


def sumario(pp):
    """[(numero, mes, dia, pagina, titulo)] de los bloques con radicado de 13 dígitos.
    El título solo viene en el sumario de las ediciones de un acto."""
    out, saltados = [], 0
    for t in pp[1:5]:
        if not re.search(r'N[úu]mero', t):
            break
        for b in re.split(r'N[úu]mero', t)[1:]:
            pa = re.search(r'P[áa]gina', b)
            if not pa:                # edición de un solo acto: «Número · Descripción»
                u = re.search(r'\b(20\d{11})\b', b)
                f = re.search(rf'(?i)Sumario[^\n]*?({_MES})\s+(\d{{1,2}})\s+de\s+\d{{4}}', t)
                d = re.search(r'Descripci[óo]n\s*(.*?)\s*(?:Sumario|\n\s*,)', b, re.S)
                if u and f:
                    out.append((u.group(1), C.fold(f.group(1)), int(f.group(2)), 3, C.limpio(d.group(1)) if d else ''))
                continue
            nums = re.findall(r'(?<![\d.])\d{1,14}(?![\d.])', b[:b.find('Fecha')] if 'Fecha' in b else b[:pa.start()])
            # ⚠️ un dígito de más en el sumario (20260700016611 en la 25.641): van seguidos
            nums = [str(int(nums[i - 1]) + 1) if len(n) == 14 and i else n for i, n in enumerate(nums)]
            fechas = re.findall(rf'(?i)\b({_MES})\s+(\d{{1,2}})\b', b[:pa.start()])
            pags = re.findall(r'(?<![\d.])\d{1,3}(?![\d.])', b[pa.end():])[:len(nums)]
            if not nums or not all(len(n) == 13 for n in nums):
                saltados += len(nums)
                continue
            if len(fechas) != len(nums) or len(pags) != len(nums):
                raise ValueError(f'sumario descuadrado: {len(nums)} números, {len(fechas)} fechas, {len(pags)} páginas')
            out += [(n, C.fold(f[0]), int(f[1]), int(p), '') for n, f, p in zip(nums, fechas, pags)]
    return out, saltados


def titulo_de(t):
    """Epígrafe en MAYÚSCULAS de la primera página del acto; dependencia que lo firma."""
    m = _TITULO.search(t)
    if not m:
        return '', ''
    resto = t[m.start():]
    f = _FIN.search(resto, 10)
    tit = C.limpio(resto[:f.start() if f else 500])[:500].strip(' .,"“”\'')
    d = _DEP.search(resto, f.start()) if f else None
    dep = re.split(r'(?i),|\s+en\s+uso\b', C.limpio(d.group(1)))[0] if d else ''
    return (tit[:1].upper() + tit[1:].lower() if tit.isupper() else tit), dep[:90]


def leer_gaceta(num, url):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        C.curl(url, salida=tmp.name, timeout=180)
        pp = paginas(tmp.name)
    cab = pp[0] if pp else ''
    f = re.search(rf'(?i)Medell[íi]n,\s*({_MES})\s+(\d{{1,2}})\s+de\s+(\d{{4}})', cab)
    fecha = C.fecha_larga(f'{f.group(2)} de {f.group(1)} de {f.group(3)}') if f else ''
    filas, ord_saltadas = sumario(pp)
    mes_g = int(fecha[5:7]) if fecha else 12
    anio_g = int(fecha[:4]) if fecha else int(url.split('/gaceta/')[1][:4])
    actos = []
    for n, mes, dia, p, tit_sum in filas:
        m = C.MESES[mes]
        fa = datetime.date(anio_g - (1 if m > mes_g else 0), m, dia).isoformat()
        t = pp[p - 1] if p <= len(pp) else ''
        sin_texto = len(t.strip()) < 60
        tit, dep = ('', '') if sin_texto else titulo_de(t)
        tit = tit or tit_sum
        actos.append({'numero': n, 'clase': 'Decreto' if n[4:6] == '07' else 'Resolución', 'fecha': fa, 'pagina': p,
                      'titulo': tit, 'dependencia': dep, 'sin_texto': sin_texto,
                      'radicado_en_pagina': n in re.sub(r'\s', '', t)})
    return {'gaceta': num, 'url': url, 'fecha': fecha, 'paginas': len(pp), 'actos': actos,
            'ordenanzas_saltadas': ord_saltadas}


def norma(g, a):
    clase = a['clase']
    tit = a['titulo']
    desc = tit or f'{clase} {a["numero"]}: gaceta escaneada, sin texto legible'
    return {'tipo': 'DECRETOS' if clase == 'Decreto' else 'RESOLUCIONES', 'subtipo': clase, 'numero': a['numero'],
            'anio': a['fecha'][:4], 'fecha': a['fecha'], 'titulo': tit, 'descripcion': desc,
            'dependencia': re.split(r'(?i)\s+en\s+uso\b', a['dependencia'])[0], 'gaceta': g['gaceta'], 'publicado': g['fecha'],
            'sin_texto': a['sin_texto'], 'administrativo': particular(tit),
            'url': f"{g['url']}#page={a['pagina']}"}


def fetch(anio, maximo):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    cache = C.leer(OUT / 'gacetas.json', {}) or {}
    previo = (C.leer(OUT / 'normas.json', {}) or {}).get('items', [])
    gs = cache.setdefault('gacetas', {})
    try:
        lista = listado(anio)
        conocidas = sum(1 for g in gs.values() if f'/gaceta/{anio}/' in g['url'])
        if len(lista) < conocidas * 0.8 or not lista:
            raise RuntimeError(f'{len(lista)} gacetas en el listado de {anio}, teníamos {conocidas}')
        faltan = sorted(n for n in lista if n not in gs)
        lote = faltan[-maximo:] if maximo else faltan
        fallas, rotas = {}, []
        with concurrent.futures.ThreadPoolExecutor(3) as ex:
            fut = {ex.submit(leer_gaceta, n, lista[n]): n for n in lote}
            for i, f in enumerate(concurrent.futures.as_completed(fut), 1):
                try:
                    r = f.result()
                    if r['actos'] or r['ordenanzas_saltadas'] or 'Convocatoria' in r['url']:
                        gs[r['gaceta']] = r
                    else:
                        fallas[fut[f]] = 'sin sumario'
                except Exception as e:
                    if 'http=404' in str(e):      # el listado enlaza un archivo que no subieron
                        rotas.append(fut[f])
                    else:
                        fallas[fut[f]] = str(e)[:120]
                if i % 25 == 0:
                    C.escribir(OUT / 'gacetas.json', {'generado': gen, 'gacetas': gs})
                    print(f'    … {i}/{len(lote)}', flush=True)
        if len(lote) >= 10 and len(fallas) > len(lote) * 0.3:
            raise RuntimeError(f'{len(fallas)} de {len(lote)} gacetas sin leer: ¿cambió el formato? {list(fallas.items())[:3]}')
        C.escribir(OUT / 'gacetas.json', {'generado': gen, 'gacetas': gs})
        vistos, items = set(), []
        for g in sorted(gs.values(), key=lambda g: g['gaceta']):
            for a in g['actos']:
                if a['numero'] not in vistos:           # un acto puede salir republicado
                    vistos.add(a['numero'])
                    items.append(norma(g, a))
        items.sort(key=lambda x: (x['fecha'], x['numero']), reverse=True)
        if len(items) < len(previo) * 0.8:
            raise RuntimeError(f'{len(items)} actos contra {len(previo)} de la corrida anterior')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': items})
        ult = max((g['fecha'] for g in gs.values() if g['fecha']), default='')
        print(f"  gobernación · {len(gs)} gacetas (última {ult}) · {len(items)} actos · "
              f"{sum(1 for x in items if not x['administrativo'] and not x['sin_texto'])} de alcance general · "
              f"{sum(1 for x in items if x['sin_texto'])} sin texto · {len(rotas)} enlaces rotos "
              f"{sorted(rotas)} · faltan {len(faltan) - len(lote) + len(fallas)} gacetas")
        for n, e in list(fallas.items())[:8]:
            print(f'    ! {n}: {e}', file=sys.stderr)
        return not fallas
    except Exception as e:
        print(f'  gobernación · FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--anio', type=int, default=datetime.date.today().year)
    f.add_argument('--max', type=int, default=60, help='Gacetas nuevas por corrida; 0 = todas')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.anio, a.max) else 1)


if __name__ == '__main__':
    main()
