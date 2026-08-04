#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — Gaceta Ambiental de la ANLA (vía 2).

La ANLA publica TODOS sus actos administrativos (autos, resoluciones, permisos,
certificados) en su Gaceta: https://gaceta.anla.gov.co:8443/Consultar-gaceta.
El buscador habla con un endpoint sin auth ni token que devuelve fragmentos
HTML paginados de a 20:

    GET /Consultar-gaceta/consultar?pagina=N
        &buscar_documento=...            (texto libre sobre la descripción)
        &buscar_tipo_documento=...       (AUTO|RESOLUCIÓN|PERMISO|CONTRATO|CERTIFICADO)
        &buscar_desde_fecha_documento=YYYY-MM-DD   (fecha de PUBLICACIÓN)
        &buscar_hasta_fecha_documento=YYYY-MM-DD

Cada card trae: tipo de documento, título ("RESOLUCIÓN 1481 DEL 30 DE JULIO DE
2010" → número + fecha del ACTO), fecha de publicación, nombre de proyecto,
ubicación, DESCRIPCIÓN completa (el "Por la cual se…", que es donde aparece la
razón social del destinatario) y el id del PDF (descargar?q=ID → descarga
directa, sin postback).

Medido ago-2026: 57.778 actos (28.253 AUTO · 28.451 RESOLUCIÓN · 955
CERTIFICADO · 118 PERMISO · 1 CONTRATO), publicados 2010→hoy (fecha del acto
llega hasta ~1993). ~42 registros no caen en ningún slice de fecha de
publicación (sin fecha) — hueco declarado, no recuperable por este filtro.

El harvest va POR SLICES de fecha de publicación (pre-2016 + un slice por año):
así el caché es resumible por slice y el refresco diario solo re-baja el año
en curso (~180 páginas, 1-2 min). Dedup global por id del documento.

tipo_acto se clasifica AQUÍ por regex sobre la descripción (whitelist del
pilar, nunca se inventa un valor): sanción → 'sancion' · inicio de
sancionatorio / pliego de cargos → 'apertura_investigacion' · archivo /
cesación / exoneración / revocatoria → 'archivo' · medida preventiva → 'otro'
(rótulo "Medida preventiva") · RESOLUCIÓN/PERMISO restantes → 'resolucion' ·
AUTO/CERTIFICADO/CONTRATO restantes → 'otro'. La especificidad (licencia
otorgada/negada/modificada, plan de manejo…) va en `tipo_sancion` (el rótulo
que el frontend pinta como badge).

`sancionado` (semántica del pilar: entidad DESTINATARIA del acto) se extrae de
la descripción por heurística de razón social EN MAYÚSCULAS con sufijo
societario (S.A. · S.A.S. · LTDA · LIMITED · LTD · LLC · E.S.P. …). Si no hay
match no se inventa: queda null y la búsqueda igual funciona porque la
descripción completa entra al blob `q` de build_s3.

Comandos:
  python3 tools/caudal/supers/harvest_anla.py test                  # 1 página, parsea, imprime
  python3 tools/caudal/supers/harvest_anla.py fetch [--workers N]   # baja slices faltantes + refresca el año en curso
  python3 tools/caudal/supers/harvest_anla.py build                 # caché -> raw/anla-gaceta.json (normalizado)
  python3 tools/caudal/supers/harvest_anla.py stats
"""
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SUP = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = SUP / 'raw'
PAGES = RAW / 'anla-gaceta-pages'

BASE = 'https://gaceta.anla.gov.co:8443/Consultar-gaceta/consultar'
DL = 'https://gaceta.anla.gov.co:8443/Consultar-gaceta/descargar?q={}'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PER_PAGE = 20          # fijo del lado del servidor (probado: ignora por_pagina/limit)
ANIO_INICIO = 2016     # antes de esto todo va en el slice pre2016 (10.345 actos)

TIPOS_ACTO = ('sancion', 'apertura_investigacion', 'archivo',
              'contribucion_especial', 'resolucion', 'circular', 'otro')

MESES = {'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5,
         'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9,
         'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
         'SETIEMBRE': 9}


# ------------------------------------------------------------------ http
def _curl(url, timeout=60):
    r = subprocess.run(
        ['/usr/bin/curl', '-sk', '-m', str(timeout), '-A', UA, url],
        capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f'curl rc={r.returncode}')
    return r.stdout.decode('utf-8', errors='replace').lstrip('﻿')


def _fetch_page(slice_name, desde, hasta, pagina, retries=3):
    url = (f'{BASE}?pagina={pagina}'
           f'&buscar_desde_fecha_documento={desde}'
           f'&buscar_hasta_fecha_documento={hasta}')
    last = None
    for i in range(retries):
        try:
            h = _curl(url)
            # una página válida trae el contador o al menos el layout de cards
            if 'encontrado(s)' in h:
                return h
            last = RuntimeError('respuesta sin contador')
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def _total_de(h):
    m = re.search(r'de\s+([\d.]+)\s+encontrado', h)
    return int(m.group(1).replace('.', '')) if m else 0


# ------------------------------------------------------------------ slices
def _slices():
    hoy = date.today()
    out = [('pre2016', '1900-01-01', '2015-12-31')]
    for y in range(ANIO_INICIO, hoy.year + 1):
        out.append((str(y), f'{y}-01-01', f'{y}-12-31'))
    return out


def cmd_fetch(workers=4):
    hoy_anio = str(date.today().year)
    for name, desde, hasta in _slices():
        sdir = PAGES / name
        sdir.mkdir(parents=True, exist_ok=True)
        done = sdir / '_done'
        # el año en curso se re-baja SIEMPRE (entran publicaciones nuevas);
        # los slices cerrados con marker _done se saltan.
        if done.exists() and name != hoy_anio:
            continue
        if name == hoy_anio:
            for p in sdir.glob('p*.html'):
                p.unlink()
            done.unlink(missing_ok=True)

        p1 = _fetch_page(name, desde, hasta, 1)
        total = _total_de(p1)
        npag = max(1, -(-total // PER_PAGE))
        (sdir / 'p0001.html').write_text(p1, encoding='utf-8')
        print(f'[{name}] {total} actos · {npag} páginas')

        pendientes = [n for n in range(2, npag + 1)
                      if not (sdir / f'p{n:04d}.html').exists()]
        fails = []

        def one(n):
            h = _fetch_page(name, desde, hasta, n)
            (sdir / f'p{n:04d}.html').write_text(h, encoding='utf-8')
            time.sleep(0.25)
            return n

        if pendientes:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(one, n): n for n in pendientes}
                hechos = 0
                for f in as_completed(futs):
                    n = futs[f]
                    try:
                        f.result()
                    except Exception as e:
                        fails.append(n)
                        print(f'  ! p{n}: {str(e)[:80]}')
                    hechos += 1
                    if hechos % 100 == 0:
                        print(f'  ... {hechos}/{len(pendientes)}')
        if fails:
            print(f'[{name}] ⚠ {len(fails)} páginas fallaron — re-correr fetch para reintentar')
        else:
            done.write_text(f'{total}\n', encoding='utf-8')
            print(f'[{name}] completo ✓')


# ------------------------------------------------------------------ parse
CARD_SPLIT = re.compile(r'<div class="col-lg-3 col-md-6 d-flex')
RE_ID = re.compile(r'descargar\((\d+)\)')
RE_TIPO = re.compile(r'<span class="mon">\s*([^<]+?)\s*</span>')
RE_TIT = re.compile(r'<h5>([^<]+)</h5>')
RE_PUB = re.compile(r'Publicado el:\s*([^<]+)')
RE_PROY = re.compile(r'Nombre de proyecto:</strong>\s*([^<]+)')
RE_UBI = re.compile(r'Ubicaci[oó]n:</strong>\s*([^<]+)')
RE_DESC_T = re.compile(r'item-box-blog-text"\s+title="([^"]*)"')
RE_DESC_P = re.compile(r'<strong>Descripci[oó]n : </strong>([^<]*)')
# variantes reales del título: "1481 DEL 30 DE JULIO DE 2010" · "NO. 003141
# DEL 25 DE NOVIEMBRE DE 2025" · "003661 DEL 05 MAYO DE 2026" (sin el DE)
RE_FECHA_TIT = re.compile(r'(\d{1,6})\s+DEL?\s+(\d{1,2})\s+(?:DE\s+)?([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})')
RE_FECHA_PUB = re.compile(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})', re.I)


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def parse_cards(h):
    out = []
    for c in CARD_SPLIT.split(h)[1:]:
        did = RE_ID.search(c)
        if not did:
            continue
        tit = RE_TIT.search(c)
        desc = RE_DESC_T.search(c) or RE_DESC_P.search(c)
        row = {
            'id': did.group(1),
            'tipo_doc': html.unescape((RE_TIPO.search(c) or [None, '']).group(1)).strip(),
            'titulo': html.unescape(tit.group(1)).strip() if tit else '',
            'publicado': html.unescape((RE_PUB.search(c) or [None, '']).group(1)).strip(),
            'proyecto': html.unescape((RE_PROY.search(c) or [None, '']).group(1)).strip(),
            'ubicacion': html.unescape((RE_UBI.search(c) or [None, '']).group(1)).strip(),
            # algunas descripciones vienen envueltas en comillas tipográficas
            'descripcion': html.unescape(desc.group(1)).strip().strip('“”"‘’') if desc else '',
        }
        out.append(row)
    return out


def _fecha_acto(titulo):
    m = RE_FECHA_TIT.search(titulo.upper())
    if not m:
        return None
    _, d, mes, a = m.groups()
    mm = MESES.get(mes)
    if not mm:
        return None
    try:
        return f'{int(a):04d}-{mm:02d}-{int(d):02d}'
    except ValueError:
        return None


def _fecha_pub(pub):
    m = RE_FECHA_PUB.search(pub)
    if not m:
        return None
    d, mes, a = m.groups()
    mm = MESES.get(mes.upper())
    return f'{int(a):04d}-{mm:02d}-{int(d):02d}' if mm else None


def _resolucion(titulo):
    m = RE_FECHA_TIT.search(titulo.upper())
    if m:
        return f'{m.group(1)} de {m.group(4)}'
    m = re.search(r'(\d+)', titulo)
    return m.group(1) if m else None


# --- razón social del destinatario: run de tokens EN MAYÚSCULAS que termina
# --- en sufijo societario. Conservador: sin match → None (nunca se inventa).
SUFIJOS = {'S.A.', 'S.A', 'SA', 'S.A.S.', 'S.A.S', 'SAS', 'LTDA', 'LTDA.',
           'LIMITED', 'LTD', 'LTD.', 'LLC', 'LLC.', 'E.S.P.', 'E.S.P', 'ESP',
           'S.C.A.', 'S.C.A', 'INC', 'INC.', 'CORP', 'CORP.', 'B.I.C.',
           'BIC', 'S.A.E.S.P.', 'CO.', 'COMPANY'}
CONECTORES = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', '&', 'E'}
# donde el nombre se corta al caminar hacia atrás. Incluye las palabras de
# frase que aparecen cuando la descripción viene TODA en mayúsculas ("POR EL
# CUAL SE VINCULA A ECOPETROL S.A.") — sin esto la heurística se tragaba la
# oración entera. EL/LA/LAS/LOS quedan como conectores a propósito: hay
# razones sociales reales que los llevan ("AGUAS DE LA GUAJIRA S.A. E.S.P.").
PARA_TOKENS = {'EMPRESA', 'SOCIEDAD', 'FIRMA', 'COMPAÑIA', 'COMPAÑÍA',
               'SEÑOR', 'SEÑORA', 'SEÑORES', 'CONTRA', 'FAVOR', 'RESOLUCION',
               'RESOLUCIÓN', 'AUTO', 'LICENCIA', 'AMBIENTAL', 'PROYECTO',
               'POR', 'CUAL', 'SE', 'QUE', 'A', 'AL', 'EN', 'UN', 'UNA',
               'COMO', 'MEDIANTE', 'DENTRO', 'SU', 'NO', 'LE', 'LES',
               'VINCULA', 'VINCULAN', 'ORDENA', 'IMPONE', 'IMPONEN',
               'DECLARA', 'DECLARAN', 'RESUELVE', 'INICIA', 'INICIAR',
               'EFECTUA', 'EFECTÚA', 'ADELANTA', 'OTORGA', 'NIEGA',
               'MODIFICA', 'MODIFICAN', 'CEDE', 'LEVANTA', 'AUTORIZA',
               'APRUEBA', 'ACEPTA', 'REQUIERE', 'SANCIONA', 'ARCHIVA',
               'INVESTIGADA', 'INVESTIGADAS', 'INVESTIGADO', 'INVESTIGADOS',
               'PRESENTADA', 'PRESENTADO', 'SOLICITADA', 'SOLICITADO',
               'TITULAR', 'NOMBRE', 'REPRESENTANTE'}


def _es_mayuscula(tok):
    letras = [c for c in tok if c.isalpha()]
    return bool(letras) and all(c.upper() == c for c in letras)


def extraer_empresa(desc):
    toks = desc.split()
    for i, raw in enumerate(toks):
        t = raw.strip(',;:()"“”')
        tu = t.upper()
        if (tu not in SUFIJOS and tu.rstrip('.') not in SUFIJOS) or i == 0:
            continue
        nombre = [t]
        j = i - 1
        while j >= 0 and len(nombre) < 9:
            prev_raw = toks[j]
            prev = prev_raw.strip('()"“”')
            core = prev.strip(',;:.')
            up = core.upper()
            if not core:
                break
            if up in PARA_TOKENS:
                break
            if not (_es_mayuscula(core) or up in CONECTORES):
                break
            nombre.insert(0, core)
            # una coma/punto AL INICIO del token previo (raro) o al final del
            # anterior corta el nombre: no se cruza puntuación hacia atrás.
            if prev.endswith((',', ';', ':', '.')) and up not in SUFIJOS \
               and not re.match(r'^[A-ZÁÉÍÓÚÑÜ]\.$', prev):
                break
            j -= 1
        # quitar conectores colgantes al inicio
        while nombre and nombre[0].upper() in CONECTORES:
            nombre.pop(0)
        # ≥1 token real que no sea otro sufijo: sin esto, una razón social en
        # minúsculas mixtas dejaba huérfanos tipo "S.A E.S.P." como nombre.
        reales = [x for x in nombre[:-1]
                  if _es_mayuscula(x) and len(x) > 1
                  and x.upper() not in SUFIJOS
                  and x.upper().rstrip('.') not in SUFIJOS]
        if reales:
            return ' '.join(nombre)
    return None


# ------------------------------------------------------------- clasificar
RE_SANCION = re.compile(
    r'impone[rn]?\s+(una\s+)?(sancion|multa)|declara[rn]?\s+responsable'
    r'|confirma[rn]?\s+(la\s+|una\s+)?(sancion|multa)|se\s+sanciona')
RE_APERTURA = re.compile(
    r'(inicia[rn]?|inicio|ordena[rn]?\s+el\s+inicio|apertura)\s+(de\s+)?(un\s+|el\s+|una\s+)?'
    r'(procedimiento|proceso|tramite|investigacion|indagacion)?[^.]{0,40}?sancionatori'
    r'|apertura\s+de\s+(una\s+)?investigacion|formula[rn]?\s+(un\s+)?(cargo|pliego)'
    r'|pliego\s+de\s+cargos|indagacion\s+preliminar'
    r'|inicia[rn]?\s+(una\s+)?investigacion\s+ambiental')
RE_ARCHIVO = re.compile(
    r'\barchiv(a|o|an|ar)\b|cesacion\s+de(l)?\s+(procedimiento|proceso)'
    r'|cesa[rn]?\s+(el\s+)?procedimiento|exonera|revoca[rn]?\s+(el\s+|la\s+|los\s+)?'
    r'(cargo|sancion|multa|medida)')
RE_MEDIDA = re.compile(r'medida\s+preventiva')
RE_LEVANTA = re.compile(r'levanta[rn]?\s+(la\s+|las\s+)?medida')

# decisión de fondo del sancionatorio: puede sancionar O exonerar — sin leer
# el PDF no se sabe el sentido, así que NO se marca 'sancion' (sería inventar);
# va como 'resolucion' con rótulo propio para que el cliente la distinga.
RE_DEFINE = re.compile(r'define\s+la\s+responsabilidad')
# vincular una sociedad/persona al sancionatorio = suma un investigado
RE_VINCULA = re.compile(r'vincula[^.]{0,80}sancionator')

RE_LIC_OTORGA = re.compile(r'otorga[rn]?\s+(una\s+)?licencia')
RE_LIC_NIEGA = re.compile(r'niega[rn]?\s+(una\s+)?licencia')
RE_LIC_MODIF = re.compile(r'modifica[rn]?\s+(la\s+|una\s+)?licencia')
RE_PMA = re.compile(r'plan\s+de\s+manejo\s+ambiental')


def clasificar(tipo_doc, desc):
    """→ (tipo_acto, rótulo legible). Whitelist dura: nunca inventa un tipo."""
    d = _fold(desc)
    if RE_SANCION.search(d):
        return 'sancion', ('Multa' if 'multa' in d else 'Sanción ambiental')
    if RE_APERTURA.search(d):
        return 'apertura_investigacion', 'Inicio de sancionatorio'
    if RE_VINCULA.search(d):
        return 'apertura_investigacion', 'Vinculación a sancionatorio'
    if RE_DEFINE.search(d):
        return 'resolucion', 'Decisión de sancionatorio'
    if RE_MEDIDA.search(d):
        # la medida preventiva no está en la whitelist → 'otro', la
        # especificidad va en el rótulo (decisión del reencuadre).
        if RE_LEVANTA.search(d):
            return 'otro', 'Levantamiento de medida preventiva'
        return 'otro', 'Medida preventiva'
    if RE_ARCHIVO.search(d):
        return 'archivo', 'Archivo / cesación'
    td = _fold(tipo_doc)
    if 'resoluci' in td or 'permiso' in td:
        if RE_LIC_OTORGA.search(d):
            return 'resolucion', 'Licencia ambiental otorgada'
        if RE_LIC_NIEGA.search(d):
            return 'resolucion', 'Licencia ambiental negada'
        if RE_LIC_MODIF.search(d):
            return 'resolucion', 'Licencia ambiental modificada'
        if RE_PMA.search(d):
            return 'resolucion', 'Plan de manejo ambiental'
        return 'resolucion', ('Permiso ambiental' if 'permiso' in td else 'Resolución')
    if 'certificado' in td:
        return 'otro', 'Certificado'
    if 'contrato' in td:
        return 'otro', 'Contrato'
    return 'otro', 'Auto de trámite'


# --- fallback de identidad con el diccionario de empresas (solo LECTURA de
# --- tools/caudal/empresas.py — propiedad de otro frente, acá solo se importa).
# La Lambda filtra el pilar Regulatorio por IDENTIDAD contra `sancionado` para
# las empresas del diccionario (diseño ④): si el destinatario solo aparece en
# el proyecto/descripción y no como razón social en MAYÚSCULAS, la búsqueda de
# esa empresa devolvía 0 (medido con Cerrejón: 30 actos, todos vía proyecto).
# Fallback: si extraer_empresa no sacó nada y el texto casa con EXACTAMENTE UNA
# empresa del diccionario (palabra completa + vetos `excluir`), `sancionado`
# toma su nombre curado. Ambiguo (2+) o gremio → no se asigna nada.
# Vetos LOCALES del fallback (falsos positivos MEDIDOS sobre este corpus, no
# hipótesis — mismo criterio que el campo `excluir` del diccionario, pero sin
# tocar empresas.py, que es de otro frente):
#   · Porvenir — 50/50 falsos: topónimo de oleoductos (Cusiana–El Porvenir,
#     Apiay–El Porvenir); la AFP no tiene nada que hacer en la ANLA.
#   · Compensar — 3/3 falsos: "ÁREA A COMPENSAR" (el verbo, no la caja).
#   · Seguros SURA — atribución errada medida: un sancionatorio de
#     "SURAMERICANA DE BATERÍAS S.A.S" (otra empresa) le caía a Sura.
NO_DICT = {'Porvenir', 'Compensar', 'Seguros SURA'}
# Vetos por CONTEXTO (el nombre casa pero el texto delata que es otra cosa):
#   · Cerro Matoso: la SUBESTACIÓN eléctrica homónima (Refuerzo Costa Caribe,
#     "línea de transmisión Cerromatoso–Chinú") no es la mina — 11/30 medidos.
#   · Claro: el POZO petrolero "Claro Sur" del Bloque La Miel (topónimo, como
#     el río Claro) casaba el alias — 1/3 medido; las repetidoras de Comcel
#     en Farallones (las legítimas) no traen "pozo".
VETO_CONTEXTO = {'Cerro Matoso (South32)': ('transmision',),
                 'Claro (Comcel)': ('pozo',)}


def _empresas_dict():
    try:
        sys.path.insert(0, str(HERE.parent))
        import empresas as _e
        return [e for e in _e.EMPRESAS if e['tipo'] == 'empresa'], _e.casa_registro
    except Exception as exn:            # el harvester sigue sirviendo sin el dict
        print(f'  (diccionario de empresas no disponible: {exn})')
        return [], None


# ------------------------------------------------------------------ build
def cmd_build():
    vistos = {}
    npag = 0
    for sdir in sorted(PAGES.iterdir()) if PAGES.exists() else []:
        if not sdir.is_dir():
            continue
        for pf in sorted(sdir.glob('p*.html')):
            npag += 1
            for row in parse_cards(pf.read_text(encoding='utf-8')):
                vistos.setdefault(row['id'], row)   # dedup global por id
    emps, casa = _empresas_dict()
    n_dict = 0
    rows = []
    for r in vistos.values():
        desc = r['descripcion']
        tipo_acto, rotulo = clasificar(r['tipo_doc'], desc)
        proy = r['proyecto'] if r['proyecto'] and r['proyecto'] != 'Sin proyecto' else ''
        ubi = r['ubicacion'] if r['ubicacion'] and r['ubicacion'] != 'Sin Ubicación' else ''
        extra = ' · '.join(x for x in (proy, ubi) if x)
        sanc = extraer_empresa(desc)
        if not sanc and casa:
            m = [e for e in emps if casa(e, f'{desc} {proy}')]
            if len(m) == 1 and m[0]['nombre'] not in NO_DICT:
                vetos = VETO_CONTEXTO.get(m[0]['nombre'], ())
                txt_f = _fold(f'{desc} {proy}')
                if not any(v in txt_f for v in vetos):
                    sanc = m[0]['nombre']
                    n_dict += 1
        rows.append({
            'sancionado': sanc,
            'identificacion': None,
            'tipo_acto': tipo_acto,
            'tipo_sancion': rotulo,
            'motivo': desc or None,
            'monto': None,
            'resolucion': f"{r['tipo_doc'].title()} {_resolucion(r['titulo']) or ''}".strip(),
            'fecha_firmeza': _fecha_acto(r['titulo']) or _fecha_pub(r['publicado']),
            'estado': None,
            'descripcion': extra or r['tipo_doc'].title(),
            'url': DL.format(r['id']),
            '_id': f"anla-{r['id']}",
        })
    rows.sort(key=lambda x: x['fecha_firmeza'] or '', reverse=True)
    out = RAW / 'anla-gaceta.json'
    out.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    tipos = Counter(x['tipo_acto'] for x in rows)
    con_emp = sum(1 for x in rows if x['sancionado'])
    fechas = sorted(x['fecha_firmeza'] for x in rows if x['fecha_firmeza'])
    print(f'build: {len(rows)} actos (de {npag} páginas cacheadas) → {out.relative_to(REPO)}')
    for t, n in tipos.most_common():
        print(f'  {t:24s} {n:>6d}')
    print(f'  con destinatario: {con_emp} ({con_emp * 100 // max(len(rows), 1)}%) '
          f'· {n_dict} vía diccionario de empresas')
    if fechas:
        print(f'  rango fecha del acto: {fechas[0]} → {fechas[-1]}')


def cmd_test():
    h = _fetch_page('test', '2026-01-01', '2026-12-31', 1)
    print('total 2026:', _total_de(h))
    for r in parse_cards(h)[:4]:
        ta, rot = clasificar(r['tipo_doc'], r['descripcion'])
        print(f"- [{r['id']}] {r['titulo']} · pub {r['publicado']}")
        print(f"  {ta} / {rot} · empresa: {extraer_empresa(r['descripcion'])}")
        print(f"  {r['descripcion'][:140]}")


def cmd_stats():
    out = RAW / 'anla-gaceta.json'
    if not out.exists():
        print('sin build todavía'); return
    rows = json.loads(out.read_text(encoding='utf-8'))
    print(f'{len(rows)} actos')
    for t, n in Counter(r['tipo_acto'] for r in rows).most_common():
        print(f'  {t:24s} {n:>6d}')


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    cmd = args[0]
    if cmd == 'fetch':
        w = 4
        if '--workers' in args:
            w = int(args[args.index('--workers') + 1])
        cmd_fetch(workers=w)
    elif cmd == 'build':
        cmd_build()
    elif cmd == 'test':
        cmd_test()
    elif cmd == 'stats':
        cmd_stats()
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
