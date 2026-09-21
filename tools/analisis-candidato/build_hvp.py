#!/usr/bin/env python3
"""Hoja de Vida del Puesto (HVP) + censo 2026 → JSON por departamento.

Fuente: «Bases de datos/Divipole_Congreso_CON DATOS.xlsx», dos hojas:

  · `Divipole_2026`        censo OFICIAL: 13.746 puestos, 41.287.084 de potencial
                           y 125.259 mesas. Cuadra al voto con la cifra oficial.
  · `reporte_HVP_27012026` hoja de vida logística: 13.511 puestos × 158 columnas,
                           corte del 27-ene-2026 (planeación del 8 de marzo).

⚠️ El censo sale SIEMPRE de `Divipole_2026`. La HVP trae columnas que se llaman
igual (MUJERES/HOMBRES/MESAS) pero son de un corte viejo: 38.633.570 de potencial
y 118.982 mesas, un 6,4 % por debajo. Quien tome el censo de la hoja equivocada
subestima la abstención y nada falla.

⚠️⚠️ La HVP trae DATOS PERSONALES de terceros: 27.246 nombres, 9.579 celulares y
16.283 correos de rectores, coordinadores y personal de seguridad de los puestos,
más las observaciones en texto libre. NADA de eso sale de este script: las
columnas 139-158 no se leen. El resultado es público; la fuente NO lo es.
"""
import json, os, re, sys, zipfile, collections
from xml.etree.ElementTree import iterparse

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSX = os.path.join(RAIZ, 'Bases de datos', 'Divipole_Congreso_CON DATOS.xlsx')
SALIDA = os.path.join(RAIZ, 'Bases de datos', 'output_hvp')

# Última columna que este script puede mirar. La 139 es «¿Quién abre el puesto?»,
# que responde con un cargo («Rector, gerente o administrador»). De la 140 en
# adelante son nombres, celulares y correos de personas: no se leen ni para
# descartarlas.
CORTE_PII = 139


def _columna(ref):
    n = 0
    for c in re.match(r'([A-Z]+)', ref).group(1):
        n = n * 26 + ord(c) - 64
    return n


def _hoja(z, cadenas, archivo, columnas=None, tope=None):
    """Devuelve filas de una hoja como dict {n_columna: valor}, 1-indexado."""
    with z.open(archivo) as f:
        for _, el in iterparse(f, ('end',)):
            if el.tag != NS + 'row':
                continue
            fila = {}
            for c in el.iter(NS + 'c'):
                v = c.find(NS + 'v')
                if v is None or v.text is None:
                    continue
                i = _columna(c.get('r'))
                if tope and i > tope:
                    continue
                if columnas and i not in columnas:
                    continue
                fila[i] = cadenas[int(v.text)] if c.get('t') == 's' else v.text
            yield int(el.get('r')), fila
            el.clear()


def _cadenas(z):
    out = []
    with z.open('xl/sharedStrings.xml') as f:
        for _, el in iterparse(f, ('end',)):
            if el.tag == NS + 'si':
                out.append(''.join(t.text or '' for t in el.iter(NS + 't')))
                el.clear()
    return out


# Los campos de texto libre los llena a mano cada registrador y se les cuela de
# todo: dos puestos de Chocó traen «n@n.com» en el nombre del barrio. Nada que
# parezca un contacto sale de aquí, aunque haya llegado por un campo que no es
# de contacto.
_CORREO = re.compile(r'\S+@\S+')
_LARGO = re.compile(r'\d{7,}')


def _texto(v, tope):
    s = re.sub(r'\s+', ' ', str(v or '').strip())
    s = _LARGO.sub('', _CORREO.sub('', s)).strip(' -,.')
    return s[:tope]


def _int(v):
    try:
        return int(float(str(v).strip() or 0))
    except ValueError:
        return 0


def _si(v):
    return 1 if str(v).strip().lower() == 'si' else 0


def _num(v):
    try:
        return round(float(str(v).strip()), 6)
    except (ValueError, TypeError):
        return None


# La grafía de comuna llega sucia: «CIUDAD BOLÍVAR» y «CIUDAD BOLIVAR»,
# «Puente Aranda» y «PUENTE ARANDA», dobles espacios. Sin unificar, una misma
# comuna se parte en dos y cada mitad se lleva la mitad de los puestos — el
# mismo estropicio que ya se corrigió en los generadores de 2023.
def _clave_comuna(s):
    s = re.sub(r'\s+', ' ', str(s or '').strip()).upper()
    s = s.translate(str.maketrans('ÁÉÍÓÚÜÑ', 'AEIOUUN'))
    return re.sub(r'^\d+', '', s).strip()


# ⚠️ El código de puesto NO es todo numérico: 187 puestos (253.897 electores)
# usan letra en los dos últimos dígitos — «0100199A1» en Medellín, y sobre todo
# Nariño (108) y Bogotá (39). Filtrar con isdigit() los borra en silencio y deja
# el censo 253.897 por debajo del oficial. Lo que sí es fijo son los siete
# primeros: departamento (2), municipio (3) y zona (2).
CODIGO = re.compile(r'\d{7}[0-9A-Z]{2}\Z')


# Normalización de «comuna · municipio» COMPARTIDA con vote-target.js
# (`llaveCircunscripcion`): mayúsculas, sin tildes, sin el número de comuna
# pegado al inicio, y todo lo que no sea letra o dígito colapsado a un espacio.
# Si cambia aquí, cambia allá, o las curules dejan de casar en silencio.
def _llave(s):
    s = str(s or '').upper().translate(str.maketrans('ÁÉÍÓÚÜÑ', 'AEIOUUN'))
    s = re.sub(r'^\d+', '', s.strip())
    return re.sub(r'[^A-Z0-9]+', ' ', s).strip()


ACCESO = {'Sin Dificultad': 0, 'Media': 1, 'Alta': 2, 'Extrema': 3}
ESTADO = {'Bueno': 0, 'Regular': 1, 'Malo': 2, 'En Remodelación': 3}


def main():
    if not os.path.exists(XLSX):
        sys.exit('no encuentro ' + XLSX)
    z = zipfile.ZipFile(XLSX)
    cadenas = _cadenas(z)

    # ── 1. Censo oficial (hoja Divipole_2026, sheet2) ──────────────────────
    censo = {}
    for r, f in _hoja(z, cadenas, 'xl/worksheets/sheet2.xml',
                      columnas={5, 13, 14, 15, 16}):
        if r == 1:
            continue
        cod = str(f.get(5, '')).strip().upper()
        if not CODIGO.match(cod):
            continue
        censo[cod] = {'m': _int(f.get(13)), 'h': _int(f.get(14)),
                      'ce': _int(f.get(15)), 'me': _int(f.get(16))}

    total = sum(v['ce'] for v in censo.values())
    mesas = sum(v['me'] for v in censo.values())
    print(f'censo 2026: {len(censo):,} puestos · {total:,} de potencial · {mesas:,} mesas')
    if total != 41_287_084 or mesas != 125_259:
        sys.exit(f'✗ el censo no cuadra con el oficial (41.287.084 / 125.259). '
                 f'Salió {total:,} / {mesas:,}: revise que no esté leyendo la hoja HVP.')
    print('  ✓ cuadra al voto con la cifra oficial')

    # ── 2. Hoja de vida del puesto (sheet1), recortada antes de la PII ─────
    hvp = {}
    for r, f in _hoja(z, cadenas, 'xl/worksheets/sheet1.xml', tope=CORTE_PII):
        if r == 1:
            continue
        cod = str(f.get(2, '')).strip().upper()
        if not CODIGO.match(cod):
            continue
        hvp[cod] = f
    print(f'HVP: {len(hvp):,} puestos con hoja de vida')

    # ── 3. Armado por departamento ─────────────────────────────────────────
    deps = collections.defaultdict(dict)
    agg = collections.defaultdict(collections.Counter)
    sin_hvp = 0
    for cod, c in censo.items():
        dep = cod[:2]
        f = hvp.get(cod)
        p = {'me': c['me'], 'ce': c['ce'], 'm': c['m'], 'h': c['h']}
        if not f:
            sin_hvp += 1
            p['hvp'] = 0
            deps[dep][cod] = p
            continue
        p.update({
            'n': _texto(f.get(19), 70),
            'd': _texto(f.get(9), 90),
            'la': _num(f.get(10)), 'lo': _num(f.get(11)),
            'cap': _int(f.get(98)),          # capacidad de mesas del puesto
            'acc': ACCESO.get(str(f.get(40, '')).strip(), 0),
            'est': ESTADO.get(str(f.get(41, '')).strip(), 0),
            'net': _si(f.get(89)),           # internet en el puesto
            'mov': _si(f.get(57)),           # comunicación móvil permanente
            'e14': _si(f.get(52)),           # lugar para publicar el E-14
            'tx':  _si(f.get(51)),           # lugar para transmisión de datos
            'dis': _si(f.get(47)),           # accesible para discapacidad
            'ram': _si(f.get(49)),           # rampas o ascensor
            'pis': _si(f.get(48)),           # mesas en varios pisos
            'tch': _si(f.get(43)),           # todas las mesas bajo techo
            'bio': _si(f.get(61)),           # biometría e infovotantes
            'agu': _si(f.get(70)), 'luz': _si(f.get(71)),
            'ban': _int(f.get(76)),          # cantidad de baños
            'ord': _si(f.get(102)),          # riesgo de orden público
            'rur': 1 if str(f.get(5, '')).strip() == '99' else 0,
            'ops': _texto(f.get(95), 40),
            'abr': _texto(f.get(139), 40),   # quién abre (cargo, no nombre)
        })
        barrio = _texto(f.get(8), 60)
        if barrio and barrio.lower().replace('.', '') not in ('no aplica', 'n/a', 'na'):
            p['b'] = barrio
        com = _clave_comuna(f.get(13))
        if com and com != 'NULL':
            p['co'] = com
        deps[dep][cod] = p

        a = agg[dep]
        a['puestos'] += 1
        a['mesas'] += c['me']
        for k in ('ord', 'net', 'dis', 'e14', 'tx', 'mov'):
            a[k] += p[k]
        if p['acc'] >= 2:
            a['acc_dificil'] += 1
        if p['est'] >= 1:
            a['mal_estado'] += 1

    os.makedirs(os.path.join(SALIDA, 'dep'), exist_ok=True)
    for dep, p in deps.items():
        with open(os.path.join(SALIDA, 'dep', f'{dep}.json'), 'w', encoding='utf-8') as fh:
            json.dump({'v': '2026-01-27', 'dep': dep, 'p': p}, fh,
                      ensure_ascii=False, separators=(',', ':'))

    # ── Curules OFICIALES de cada JAL ────────────────────────────────────
    # La HVP trae, por puesto, las curules de la Junta de su comuna o
    # corregimiento (col 23) y el acuerdo que las fija. vote-target.js las
    # INFERÍA por la lista más larga inscrita, que falla donde ningún partido
    # inscribe la lista completa: en Bogotá, Sumapaz daba 5 en vez de 7 y
    # Rafael Uribe Uribe 10 en vez de 11. Llave = la misma normalización que usa
    # vote-target.js sobre «COMUNA · MUNICIPIO» del índice de JAL.
    votos_cur = collections.defaultdict(collections.Counter)
    for cod, f in hvp.items():
        c = _int(f.get(23))
        if c <= 0:
            continue
        # ⚠️ En Bogotá el georef guarda la LOCALIDAD en la columna MUNICIPIO:
        # sin forzarlo, la llave salía «SUBA|SUBA» y no casaba con ninguna de
        # sus 20 Juntas. Mismo gotcha que build_jal_2023.py.
        mun = 'BOGOTA D.C.' if cod[:5] == '16001' else f.get(4)
        clave = f'{_llave(f.get(13))}|{_llave(mun)}'
        if clave != '|':
            votos_cur[clave][c] += 1
    curules_jal, ambiguas = {}, []
    for clave, cnt in votos_cur.items():
        (val, n), *resto = cnt.most_common()
        # Un municipio homónimo en otro departamento, o una comuna con dos
        # cifras, no se resuelve adivinando: se omite y cae a la inferencia.
        if resto and resto[0][1] * 3 > n:
            ambiguas.append(clave); continue
        curules_jal[clave] = val
    with open(os.path.join(SALIDA, 'curules-jal.json'), 'w', encoding='utf-8') as fh:
        json.dump({'v': '2026-01-27', 'fuente': 'RNEC · hoja de vida del puesto',
                   'curules': curules_jal}, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'curules de JAL: {len(curules_jal)} juntas · {len(ambiguas)} ambiguas omitidas')

    indice = {'v': '2026-01-27',
              'fuente': 'RNEC · Divipole 2026 + hoja de vida del puesto al 27-ene-2026',
              'puestos': len(censo), 'con_hvp': len(censo) - sin_hvp,
              'censo': total, 'mesas': mesas,
              'dep': {d: dict(a) for d, a in agg.items()}}
    with open(os.path.join(SALIDA, 'indice.json'), 'w', encoding='utf-8') as fh:
        json.dump(indice, fh, ensure_ascii=False, separators=(',', ':'))

    pesos = sorted(((os.path.getsize(os.path.join(SALIDA, 'dep', f'{d}.json')), d)
                    for d in deps), reverse=True)
    print(f'\nescritos {len(deps)} departamentos en {SALIDA}/dep/')
    print(f'  sin hoja de vida: {sin_hvp} puestos (se emiten solo con censo)')
    print(f'  más pesado: {pesos[0][1]} · {pesos[0][0]/1024:.0f} KB · '
          f'total {sum(p for p, _ in pesos)/1024/1024:.1f} MB')


if __name__ == '__main__':
    main()
