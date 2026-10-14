"""
puestos_historicos.py — ubica en el mapa de comunas los puestos de una elección
VIEJA (2019, 2015…) cuando el georef que tenemos es el de 2026.

⚠️⚠️ El código de puesto NO es estable entre elecciones. Medido sobre el censo
2019 por puesto (tipo AUTORIDADES TERRITORIALES), ponderado por potencial:

    ciudad          mismo nombre en 2026   mismo nombre en Divipol 2021
    Villavicencio          33 %                     99,5 %
    Ibagué                 50 %                     57 %
    Manizales              83 %                     95 %
    Bogotá                 92 %                     99,5 %
    resto                ≥ 88 %                   ≥ 92 %

Cruzar 2019 contra el georef 2026 por código pone los votos de un puesto en la
comuna de OTRO lugar, y no falla. Por eso se resuelve con nombre, en cascada:

  B  mismo código en 2026 y nombre equivalente → comuna del georef 2026
  A  mismo código en el Divipol 2021 y nombre equivalente → comuna de 2021
     · NO en Montería (renumeró sus comunas entre 2021 y 2026: 36 de 63 casan)
     · NO en zona 99 (los corregimientos cambiaron de número)
     · NO donde la comuna sale de un archivo externo (las UCG de Cartagena
       para Concejo están definidas sobre códigos 2026)
  C  el puesto 2026 del municipio con el mismo nombre (casi idéntico y sin
     rival cercano, o el único equivalente) → su comuna
  —  nada de lo anterior → el puesto queda fuera del mapa y se cuenta

Los nombres de cada año salen de
  Bases de datos/censos-registraduria/{año}_datos_censo-electoral-min.json
y el Divipol de
  Bases de datos/Divipol 23.09.2021.xlsx   (comuna = «01COMUNA 1 POPULAR»).

Un puesto que el censo del año no nombra (no hay con qué verificar) no se ubica.

    from puestos_historicos import resolver
    R = resolver(2019, ciudades, com26, externas)
    R[pcode_viejo] → (comC, code26 | None, nombre_del_año, regla)
"""
import json, os, re, unicodedata
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(ROOT, 'Bases de datos')
DIVIPOL_2021 = os.path.join(BD, 'Divipol 23.09.2021.xlsx')
SIN_NUMERACION_2021 = {('13', '001')}       # Montería: numeración de comunas distinta
TIPO = 'AUTORIDADES TERRITORIALES'

# Palabras que no distinguen un puesto de otro.
STOP = {'I', 'E', 'IE', 'INST', 'INSTITUCION', 'INSTITUTO', 'EDUCATIVA', 'EDUC', 'COLEGIO',
        'COL', 'ESC', 'ESCUELA', 'SEC', 'SECC', 'SEDE', 'SD', 'CENTRO', 'DE', 'DEL', 'LA',
        'EL', 'LOS', 'LAS', 'Y', 'NO', 'N', 'C', 'CONCENTRACION', 'ESCOLAR', 'PUESTO',
        'DISTRITAL', 'MUNICIPAL', 'NACIONAL', 'TECNICO', 'TECNICA', 'IED', 'JARDIN', 'CDI',
        'ED', 'EDUCATIVO', 'SAN', 'SANTA', 'COLEG', 'UNIDAD', 'NRO', 'CED', 'CE', 'IEM',
        'A', 'B', 'PRINCIPAL'}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    # «S E N A» (de «S.E.N.A.») → «SENA»
    s = re.sub(r'\b(?:[A-Z] )+[A-Z]\b', lambda m: m.group(0).replace(' ', ''), s)
    return s.strip()


def toks(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 1}


def equiv(a, b):
    ta, tb = toks(a), toks(b)
    if ta and tb and len(ta & tb) / min(len(ta), len(tb)) >= 0.5:
        return True
    return SequenceMatcher(None, norm(a), norm(b)).ratio() >= 0.8


def _nombres_del_año(año, ciudades):
    ruta = os.path.join(BD, 'censos-registraduria', f'{año}_datos_censo-electoral-min.json')
    with open(ruta, encoding='utf-8') as f:
        data = json.load(f)['data']
    out = {}
    for r in data:
        if r.get('tipo_eleccion') != TIPO:
            continue
        if (r['cod_depto'], r['cod_mun']) not in ciudades:
            continue
        out[f"{r['cod_depto']}{r['cod_mun']}{r['zona']}{r['cod_puesto']}"] = r.get('puesto_votacion') or ''
    return out


def _divipol_2021(ciudades):
    import openpyxl
    wb = openpyxl.load_workbook(DIVIPOL_2021, read_only=True)
    out = {}
    for i, r in enumerate(wb[wb.sheetnames[0]].iter_rows(values_only=True)):
        if i < 5 or not r or not r[0]:
            continue
        dd, mm, zz, pp = (str(x).strip() for x in r[:4])
        if (dd, mm) not in ciudades:
            continue
        m = re.match(r'\s*(\d+)', str(r[11] or ''))
        out[f'{dd}{mm}{zz}{pp}'] = (r[6] or '', m.group(1).zfill(2) if m else 'ND')
    return out


def resolver(año, ciudades, com26, nombres26, externas=()):
    """
    año        elección vieja (2019…)
    ciudades   {(dd,mm)} a resolver
    com26      {code26: comC} tal como lo arma el builder (ya con archivo externo)
    nombres26  {code26: nombre del puesto en el georef 2026}
    externas   {(dd,mm)} cuya comuna sale de archivo externo → sin regla A
    → {pcode_viejo: (comC, code26|None, nombre_viejo, regla)}  · regla ∈ B A C
      (los no resueltos NO están en el dict; el builder los cuenta)
    """
    viejos = _nombres_del_año(año, ciudades)
    d21 = _divipol_2021(ciudades)
    por_mun = {}
    for c, n in nombres26.items():
        por_mun.setdefault(c[:5], []).append((c, n))

    def unico_2026(nombre, mun):
        """El puesto 2026 del municipio que ES este, o None si hay duda.
        Primero el casi idéntico (≥ 0,9) que además le saca ventaja al segundo:
        el comparador flexible solo hace que «IE SALADO SEDE 1» case con tres
        sedes distintas y no decida aunque el nombre exacto exista."""
        lista = por_mun.get(mun, [])
        nn = norm(nombre)
        r = sorted(((SequenceMatcher(None, nn, norm(n)).ratio(), c) for c, n in lista), reverse=True)
        if r and r[0][0] >= 0.9 and (len(r) == 1 or r[0][0] - r[1][0] >= 0.08):
            return r[0][1]
        hits = [c for c, n in lista if equiv(nombre, n)]
        return hits[0] if len(hits) == 1 else None

    out = {}
    for code, nombre in viejos.items():
        keyc = (code[:2], code[2:5])
        if code in nombres26 and equiv(nombre, nombres26[code]):
            out[code] = (com26.get(code, 'ND'), code, nombre, 'B')
            continue
        c26 = unico_2026(nombre, code[:5])
        if (code in d21 and code[5:7] != '99' and keyc not in SIN_NUMERACION_2021
                and keyc not in externas and equiv(nombre, d21[code][0])):
            out[code] = (d21[code][1], c26, nombre, 'A')
            continue
        if c26:
            out[code] = (com26.get(c26, 'ND'), c26, nombre, 'C')
    return out
