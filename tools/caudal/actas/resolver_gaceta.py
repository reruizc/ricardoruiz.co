#!/usr/bin/env python3
"""
Caudal · resolver un NÚMERO de gaceta → (entidad, fecha exacta).

La ficha de Cámara cita "Gaceta No. N del AAAA" (número + año), pero
`descargar_gaceta.py` necesita la FECHA exacta (el deep-link de la Imprenta la
hornea en el ViewState — con fecha inventada devuelve XML, no PDF). Este módulo
cierra el hueco: filtra el datatable JSF de la Imprenta por Número Gaceta y lee
la entidad + fecha de la fila.

⚠️ Los ids de los campos de filtro (j_idtNN) SE CORREN entre versiones del
portal (medido: j_idt13→j_idt11 el número, j_idt22→j_idt20 el documento). Por
eso NO se hardcodean: se descubren del HTML en cada corrida (los dos inputs
`...:filter` en orden de DOM → [Número, Documento]).

Uso:
  python3 tools/caudal/actas/resolver_gaceta.py 854
  → 854  Cámara de Representantes  15/07/2026  (iso 2026-07-15)

⚠️ Los números de gaceta SE REPITEN cada año (854 existe en 2016, 2017 … 2026).
El filtro devuelve una fila por año → hay que PAGINAR todos los matches y quedarse
con el del año pedido. Pasar `anio` cuando se conoce (la ficha de Cámara lo trae).

API:  resolver_gaceta(num, anio=None) -> [{'num','entidad','ent_arg','fecha','fecha_iso'}]
"""
import re
import subprocess
import sys

BASE = 'http://svrpubindc.imprenta.gov.co/senado'
DT = 'formResumen:dataTableResumen'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
CK = '/tmp/_caudal_resolver_ck.txt'


def _curl(args):
    return subprocess.run(['/usr/bin/curl', '-s', '-A', UA] + args,
                          capture_output=True, timeout=120).stdout.decode('utf-8', 'replace')


def _discover(html):
    """(viewstate, id_filtro_numero, id_input_entidad, id_filtro_doc)."""
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', html)
    filtros = re.findall(rf'name="{re.escape(DT)}:(j_idt\d+):filter"', html)
    entidad = re.search(rf'name="{re.escape(DT)}:(j_idt\d+)_input"', html)
    return (vs.group(1) if vs else None,
            filtros[0] if filtros else None,      # 1ª columna = Número Gaceta
            entidad.group(1) if entidad else None,
            filtros[-1] if len(filtros) > 1 else None)


# fila: <label>NUM</label></td> <td><label>ENTIDAD</label></td> <td><label>FECHA</label>
ROW_RE = re.compile(
    r'<label[^>]*>(\d+)</label></td>\s*<td[^>]*>\s*<label[^>]*>([^<]+?)</label>'
    r'</td>\s*<td[^>]*>\s*<label[^>]*>(\d{1,2}/\d{1,2}/\d{4})</label>', re.S)

ENT_ARG = {'senado': 'Senado', 'cámara': 'Camara', 'camara': 'Camara'}


def _ent_arg(entidad):
    e = entidad.lower()
    return 'Camara' if 'mara' in e else 'Senado'


def _base_data(vs, id_num, id_ent, id_doc, num):
    return [
        ('javax.faces.partial.ajax', 'true'),
        ('javax.faces.source', DT),
        ('javax.faces.partial.execute', DT),
        ('javax.faces.partial.render', DT),
        (DT, DT),
        (f'{DT}:{id_num}:filter', num),                 # Número Gaceta = num (se conserva al paginar)
        (f'{DT}:{id_ent}_input', ''),                   # Entidad = cualquiera
        (f'{DT}:calFechaGaceta_input', ''),
        (f'{DT}:{id_doc}:filter', '') if id_doc else ('_', ''),
        ('formResumen', 'formResumen'),
        ('javax.faces.ViewState', vs),
    ]


def _post(args_data):
    args = ['-b', CK, '-X', 'POST', f'{BASE}/index.xhtml',
            '-H', 'Faces-Request: partial/ajax',
            '-H', 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8']
    for k, v in args_data:
        args += ['--data-urlencode', f'{k}={v}']
    return _curl(args)


def resolver_gaceta(num, anio=None):
    num, anio = str(num), (str(anio) if anio else None)
    idx = _curl(['-c', CK, f'{BASE}/index.xhtml'])
    vs, id_num, id_ent, id_doc = _discover(idx)
    if not vs or not id_num:
        return []
    base = _base_data(vs, id_num, id_ent, id_doc, num)
    # aplicar filtro por número
    _post(base + [(f'{DT}_filtering', 'true'), (f'{DT}_encodeFeature', 'true')])
    # paginar TODOS los matches (el mismo número existe una vez por año)
    out, vis, first = [], set(), 0
    while first <= 400:                                  # backstop (>30 años imposible)
        html = _post(base + [(f'{DT}_pagination', 'true'), (f'{DT}_first', str(first)),
                             (f'{DT}_rows', '10'), (f'{DT}_encodeFeature', 'true')])
        filas = ROW_RE.findall(html)
        if not filas:
            break
        nuevo = False
        for n, ent, dmy in filas:
            if n != num:
                continue
            d, m, y = dmy.split('/')
            k = (n, y, m, d)
            if k in vis:
                continue
            vis.add(k); nuevo = True
            out.append({'num': n, 'entidad': ent.strip(), 'ent_arg': _ent_arg(ent),
                        'fecha': f'{int(d)}-{int(m)}-{y}', 'fecha_iso': f'{y}-{m.zfill(2)}-{d.zfill(2)}'})
        if not nuevo:
            break
        first += 10
    if anio:
        out = [r for r in out if r['fecha_iso'][:4] == anio]
    out.sort(key=lambda r: r['fecha_iso'], reverse=True)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('uso: resolver_gaceta.py <num> [anio]'); sys.exit(1)
    anio = sys.argv[2] if len(sys.argv) > 2 else None
    res = resolver_gaceta(sys.argv[1], anio)
    if not res:
        print('  (sin resultados)')
    for r in res:
        print(f"  {r['num']}  {r['entidad']}  {r['fecha']}  (iso {r['fecha_iso']}, ent_arg {r['ent_arg']})")
