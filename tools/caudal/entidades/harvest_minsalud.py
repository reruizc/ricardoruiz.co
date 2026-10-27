#!/usr/bin/env python3
"""
Caudal · Ministerio de Salud y Protección Social por su API de SharePoint.

MinSalud sacó de SUCOP sus borradores de 2026, pero su SharePoint responde
JSON sin sesión (`Accept: application/json;odata=nometadata`):

  proyectos  /Normativa/_api/web/lists/getbytitle('proy-act-adm')/items
             Borradores en consulta, con epígrafe, ventana y correo para
             comentarios. ⚠️ MinSalud BORRA los cerrados: solo quedan los vivos.
             Por eso se acumula — un borrador que ya no está en la lista se
             conserva con `vigente_en_fuente: false`.
  ain        /Normativa/_api/web/lists/getbytitle('consulta-AIN')/items
             Consultas del Análisis de Impacto Normativo (definición del problema).
  normas     /_api/web/GetList('/Normatividad_Nuevo')/items
             El normograma: resoluciones, circulares, decretos, conceptos y
             boletines jurídicos, con PDF de enlace permanente.
  eventos    /_api/web/GetList('/Lists/Calendario')/items
             Calendario oficial: jornadas de socialización («Participación
             Social») y capacitaciones (SIIFA).

Los conceptos jurídicos traen de título solo el número de radicado; el tema
sale del «ASUNTO:» del PDF (se baja una vez y se cachea el texto).

Salida: `Bases de datos/caudal-entidades/raw/minsalud/{proyectos,ain,normas,eventos}.json`.
`build.py` los lleva a los índices genéricos.

Uso:
  python3 tools/caudal/entidades/harvest_minsalud.py fetch
  python3 tools/caudal/entidades/harvest_minsalud.py fetch --conceptos-desde 2024
"""
import argparse
import datetime
import json
import sys
import tempfile
import urllib.parse

import comun as C

ENTIDAD = 'Ministerio de Salud y Protección Social'
BASE = 'https://www.minsalud.gov.co'
ACC = 'application/json;odata=nometadata'
OUT = C.RAW / 'minsalud'
TXT = OUT / 'conceptos-txt'


def _lista(url):
    """Todas las filas de una lista, siguiendo `odata.nextLink`."""
    filas, n = [], 0
    while url and n < 40:
        d = json.loads(C.curl(url, accept=ACC, timeout=90))
        filas += d.get('value', [])
        url = d.get('odata.nextLink')
        n += 1
    return filas


def _url(file_ref):
    return BASE + urllib.parse.quote(file_ref or '') if file_ref else ''


def _fecha(s):
    return (s or '')[:10]


def _fecha_local(s):
    """SharePoint guarda en UTC: «2026-10-26T23:00:00Z» es el 26 a las 6 p.m.
    en Bogotá, pero «2026-10-29T05:00:00Z» es el 29 a medianoche. Se pasa a
    hora de Colombia antes de cortar la fecha."""
    if not s:
        return ''
    try:
        t = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        return (t - datetime.timedelta(hours=5)).date().isoformat()
    except ValueError:
        return s[:10]


def proyectos(previos):
    filas = _lista(f"{BASE}/Normativa/_api/web/lists/getbytitle('proy-act-adm')/items"
                   "?$select=*,FileRef&$orderby=Modified%20desc&$top=500")
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for r in filas:
        epi = C.limpio(r.get('Ep_x00ed_grafe') or '').strip('"“” ')
        envio = r.get('Envio_x0020_de_x0020_Comentarios') or {}
        anexos = [a.strip() for a in (r.get('Anexos') or '').split('\n') if a.strip().startswith('http')]
        vivos[r['GUID']] = {
            'id': r['GUID'], 'tipo_norma': r.get('Tipo_x0020_de_x0020_Proyecto') or 'Proyecto',
            'titulo': epi or C.limpio(r.get('Title')), 'nombre_archivo': C.limpio(r.get('Title')),
            'dependencia': C.limpio(r.get('Dependencia_x0020_Responsable')),
            'fecha_inicio': _fecha_local(r.get('Inicio_x0020_de_x0020_Consulta')),
            'fecha_fin': _fecha_local(r.get('Fin_x0020_de_x0020_Consulta_x0020_de_x0020_Consulta')),
            'comentarios_a': (envio.get('Description') or '').strip(),
            'url': _url(r.get('FileRef')), 'anexos': anexos,
            'creado': _fecha(r.get('Created')), 'visto': hoy, 'vigente_en_fuente': True,
        }
    out = dict(previos)
    for k, v in out.items():                      # lo que MinSalud ya borró
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def ain(previos):
    filas = _lista(f"{BASE}/Normativa/_api/web/lists/getbytitle('consulta-AIN')/items"
                   "?$select=*,FileRef&$top=500")
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for r in filas:
        vivos[r['GUID']] = {
            'id': r['GUID'], 'tipo_norma': 'Análisis de Impacto Normativo',
            'titulo': C.limpio(r.get('Documento_x0020_en_x0020_Consulta') or r.get('Title')),
            'dependencia': C.limpio(r.get('Nombre_x0020_del_x0020_Proyecto')),
            'fecha_inicio': _fecha_local(r.get('Inicio_x0020_de_x0020_Consulta_x0020_P_x00fa_blica')),
            'fecha_fin': _fecha_local(r.get('Fin_x0020_de_x0020_Consu_x00f1_ta_x0020_P_x00fa_blica')),
            'comentarios_a': C.limpio(r.get('Datos_x0020_para_x0020_envio_x0020_de_x0020_comentarios')),
            'url': _url(r.get('FileRef')), 'anexos': [],
            'creado': _fecha(r.get('Created')), 'visto': hoy, 'vigente_en_fuente': True,
        }
    out = dict(previos)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


_ASUNTO = __import__('re').compile(r'(?is)\bASUNTO\s*:\s*(.+?)(?:Radicado\s+No|Respetad|Apreciad|Se[ñn]or|Cordial|\n\s*\n)')


def asunto_concepto(file_ref):
    """«ASUNTO:» del concepto, del texto cacheado o bajando el PDF una vez."""
    import re
    nombre = re.sub(r'[^\w.-]+', '_', file_ref.rsplit('/', 1)[-1])
    cache = TXT / (nombre + '.txt')
    if cache.exists():
        texto = cache.read_text(encoding='utf-8')
    else:
        import pymupdf
        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
            C.curl(_url(file_ref), salida=tmp.name, timeout=120)
            with pymupdf.open(tmp.name) as d:
                texto = '\n'.join(p.get_text() for p in list(d)[:3])
        TXT.mkdir(parents=True, exist_ok=True)
        cache.write_text(texto, encoding='utf-8')
    m = _ASUNTO.search(texto)
    return C.limpio(m.group(1)).rstrip(' .–-')[:500] if m else ''


_NUM = __import__('re').compile(
    r'(?i)(?:resoluci[oó]n|circular|decreto|acuerdo|ley|nota\s+externa|concepto(?:\s+jur[ií]dico)?)'
    r'(?:\s+(?:externa|conjunta|cres|cnsss))*\s*(?:No\.?|N[°º]\.?|n[uú]mero)?\s*0*(\d{1,20})')


def numero_de(titulo):
    m = _NUM.search(titulo or '')
    return m.group(1) if m else ''


TIPOS = {'Resolución': 'RESOLUCIONES', 'Circular': 'CIRCULARES', 'Decreto': 'DECRETOS',
         'Concepto': 'CONCEPTOS', 'Boletines Jurídicos': 'BOLETINES', 'Ley': 'LEYES',
         'Acuerdo': 'ACUERDOS', 'Directiva': 'DIRECTIVAS'}


def normas(conceptos_desde):
    import re
    filas = _lista(f"{BASE}/_api/web/GetList('/Normatividad_Nuevo')/items"
                   "?$select=Id,Title,Descripci_x00f3_n,Tipo_x0020_de_x0020_Norma,A_x00f1_o,"
                   "Subtema,Publicaci_x00f3_n,Created,FileRef&$top=5000")
    out, fallidos = [], 0
    for r in filas:
        tn = (r.get('Tipo_x0020_de_x0020_Norma') or '').strip()
        if tn.startswith('Proyecto'):
            continue                      # el archivo de borradores viejos: no es norma
        tipo = TIPOS.get(tn, (tn or 'OTRAS').upper())
        titulo = C.limpio(r.get('Title'))
        desc = C.limpio(r.get('Descripci_x00f3_n'))
        anio = str(r.get('A_x00f1_o') or '')[:4]
        numero = numero_de(titulo)
        if not anio:
            ma = re.search(r'\b(19|20)\d{2}\b', titulo)
            anio = ma.group(0) if ma else ''
        if tipo == 'CONCEPTOS' and (desc == titulo or not desc) and anio >= str(conceptos_desde):
            try:
                a = asunto_concepto(r.get('FileRef'))
                if a:
                    desc = a
            except Exception as e:        # un PDF que no baja no tumba el resto
                fallidos += 1
                print(f'  ! concepto {titulo}: {e}', file=sys.stderr)
        out.append({'id': r.get('Id'), 'tipo': tipo, 'subtipo': tn, 'numero': numero, 'anio': anio,
                    'fecha': _fecha_local(r.get('Publicaci_x00f3_n')) or _fecha(r.get('Created')),
                    'titulo': titulo, 'descripcion': desc if desc != titulo else '',
                    'subtema': C.limpio(r.get('Subtema')), 'url': _url(r.get('FileRef'))})
    return out, fallidos


def eventos():
    filas = _lista(f"{BASE}/_api/web/GetList('/Lists/Calendario')/items"
                   "?$orderby=EventDate%20desc&$top=1000")
    out = []
    for r in filas:
        u = (r.get('UrlEvento') or {}).get('Url') or ''
        out.append({'id': r.get('Id'), 'titulo': C.limpio(r.get('Title')),
                    'fecha_inicio': r.get('EventDate') or '', 'fecha_fin': r.get('EndDate') or '',
                    'dia': _fecha_local(r.get('EventDate')),
                    'lugar': C.limpio(r.get('Location')), 'descripcion': C.limpio(r.get('Description'))[:800],
                    'categorias': r.get('Category') or [], 'url': u})
    return out


def fetch(conceptos_desde):
    OUT.mkdir(parents=True, exist_ok=True)
    resumen, ok = {}, True
    for nombre, fn in (('proyectos', proyectos), ('ain', ain)):
        prev = (C.leer(OUT / f'{nombre}.json', {}) or {}).get('items', {})
        try:
            items, vivos = fn(prev)
            C.escribir(OUT / f'{nombre}.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                                                'entidad': ENTIDAD, 'items': items})
            resumen[nombre] = f'{vivos} vivos · {len(items)} acumulados'
        except Exception as e:
            ok = False
            resumen[nombre] = f'FALLÓ ({e}) — se conserva el archivo anterior'
    try:
        ns, fallidos = normas(conceptos_desde)
        if len(ns) < 1000:
            raise RuntimeError(f'solo {len(ns)} normas: el normograma tiene más de 6.000')
        C.escribir(OUT / 'normas.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                                         'entidad': ENTIDAD, 'items': ns})
        resumen['normas'] = f'{len(ns)} normas · {fallidos} conceptos sin leer'
    except Exception as e:
        ok = False
        resumen['normas'] = f'FALLÓ ({e}) — se conserva el archivo anterior'
    try:
        ev = eventos()
        C.escribir(OUT / 'eventos.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                                          'entidad': ENTIDAD, 'items': ev})
        resumen['eventos'] = f'{len(ev)} eventos'
    except Exception as e:
        ok = False
        resumen['eventos'] = f'FALLÓ ({e}) — se conserva el archivo anterior'
    for k, v in resumen.items():
        print(f'  minsalud · {k}: {v}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--conceptos-desde', type=int, default=2025)
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.conceptos_desde) else 1)


if __name__ == '__main__':
    main()
