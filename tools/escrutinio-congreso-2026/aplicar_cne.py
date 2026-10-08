#!/usr/bin/env python3
"""Lleva el Senado y la Cámara 2026 a las cifras que declaró el CNE.

Por qué hace falta: nuestros JSON salen del mesa a mesa de las comisiones generales
(DEPTOS_DECLARADOS, abril 2026), que cuadra AL VOTO con los 34 E-26 departamentales.
Después el CNE hizo el escrutinio nacional del Senado (Res. E-3328, 13-jul-2026) y
rehízo el de Cámara en Chocó, Cundinamarca y la circunscripción Afro, y movió votos
(Juan Felipe Lemos −616, por ejemplo) sin cambiar a ningún elegido. El CNE no
publicó ese ajuste mesa a mesa, así que se aplica al nivel donde existe:

  Senado    resumen.json + circunscripciones.json  (nacional e indígena)
  Cámara    dep-15.json, dep-17.json, departamentos.json y resumen.json

El nivel municipio / puesto / mesa sigue siendo el de las comisiones.

Cada voto se toma del E-26 del CNE leído por OCR (leer_e26_cne.py) y solo entra si
la cifra y las letras coinciden, o si una de las dos queda a menos de la tolerancia
del valor que ya teníamos. Lo que no pasa se queda con el valor de la comisión y va
al informe. Al final se exige que cada partido concilie: voto de lista + candidatos
= total del partido en el E-26.

Uso:
  python3 aplicar_cne.py --cne DIR_OCR --entrada DIR_JSON --salida DIR_SALIDA
    DIR_OCR     los .txt del OCR (E26_SEN_NAC.txt, E26_SEN_IND.txt, E26_CAM_*.txt)
    DIR_JSON    copia de lo que hoy está en S3 (senado/… y camara/…)
"""
import argparse
import copy
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from leer_e26_cne import leer  # noqa: E402

FUENTE = {
    'senado': 'CNE · Resolución E-3328 de 2026 (13-jul-2026) · E-26 SEN nacional e indígena',
    'camara': 'CNE · E-26 CAM Chocó (14-jul-2026) y Cundinamarca (17-jul-2026) · Res. E-3401 de 2026 (Afro)',
}


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').upper())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z0-9 ]', ' ', s).split()


def parecido(a, b):
    """Fracción de palabras del nombre más corto que aparecen en el otro."""
    ta, tb = set(norm(a)), set(norm(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def bloques(filas, validos=None):
    """Agrupa las filas del E-26 en partidos {cod: {lista, cands[], total, nombre}}.

    validos = códigos de partido que existen en nuestros datos. Si el OCR no leyó la
    fila de encabezado de un partido, sus candidatos igual abren su bloque; solo un
    código que no existe (00003 por 00008) se atribuye al bloque en curso."""
    partidos, orden, actual = {}, [], None
    validos = validos or set()
    especiales = {}
    for f in filas:
        if f['tipo'] == 'candidato' and not f['can']:
            cod = f['cod']
            if cod in partidos and (partidos[cod]['lista'] is not None or partidos[cod]['total'] is not None):
                partidos[cod].setdefault('total_resumen', f)   # la página de resumen repite partido + total
                continue
            if cod in partidos:            # el bloque ya existía por sus candidatos: esta es su fila de lista
                partidos[cod]['lista'] = f
                partidos[cod]['nombre'] = f['nombre']
                actual = cod
                continue
            partidos[cod] = {'nombre': f['nombre'], 'lista': f, 'cands': [], 'total': None}
            orden.append(cod)
            actual = cod
        elif f['tipo'] == 'candidato':
            cod = f['cod']
            if cod not in partidos and cod in validos:
                partidos[cod] = {'nombre': '', 'lista': None, 'cands': [], 'total': None}
                orden.append(cod)
            elif cod not in partidos:
                if actual is None:
                    continue
                cod = actual   # el OCR leyó mal el código (00003-006 por 00008-006): manda el bloque en curso
            partidos[cod]['cands'].append(f)
            actual = cod
        else:
            nom = ' '.join(norm(f['nombre']))
            if nom.startswith('POR PARTIDOS'):
                especiales['partidos'] = f
            elif nom.startswith('EN BLANCO'):
                especiales['blanco'] = f
            elif nom.startswith('VALIDOS') or nom.startswith('V LIDOS'):
                especiales['validos'] = f
            elif nom.startswith('NULOS'):
                especiales['nulos'] = f
            elif nom.startswith('NO MARCADOS'):
                especiales['nomarc'] = f
            elif actual and partidos[actual]['total'] is None:
                partidos[actual]['total'] = f
    return partidos, orden, especiales


def buscar_linea(raw, nombre):
    """Último recurso: la línea del OCR que lleva el nombre del candidato, aunque no traiga
    un código legible. Devuelve una fila con cifra/letras validadas como las demás."""
    from leer_e26_cne import cifra_a_num, letras_a_num
    clave = ' '.join(norm(nombre))
    for linea in raw.splitlines():
        if clave and clave in ' '.join(norm(linea)):
            m = re.search(r'\s([\d][\d.,]{0,10})[|\s]+([A-ZÁÉÍÓÚÑ_][A-ZÁÉÍÓÚÑ ]{2,})\s*$', linea)
            if not m:
                return None
            c, l = cifra_a_num(m.group(1)), letras_a_num(m.group(2).lstrip('_'))
            fuente = 'ok' if c is not None and c == l else 'letras' if l is not None else 'cifra' if c is not None else 'ninguno'
            v = c if fuente in ('ok', 'cifra') else l
            return {'votos': v, 'fuente': fuente, 'cifra': c, 'letras': l, 'nombre': nombre}
    return None


MANUAL = {}   # (corp, nombre) -> votos leídos a ojo en el PDF; se cargan de manual_cne.json


def elegir(f, ref, tol_abs=150, tol_rel=0.03):
    """Devuelve (valor, motivo). ref = valor que ya teníamos (o None)."""
    if f is None:
        return None, 'sin fila'
    if f['fuente'] == 'ok':
        return f['votos'], 'ok'
    cands = [v for v in (f['cifra'], f['letras']) if v is not None]
    if ref is not None and cands:
        mejor = min(cands, key=lambda v: abs(v - ref))
        if abs(mejor - ref) <= max(tol_abs, tol_rel * ref):
            return mejor, 'cercano'
    return None, 'dudoso'


def total_validado(f, ref=None):
    v, _ = elegir(f, ref, tol_abs=5000, tol_rel=0.01)
    return v


def numero(txt, patron):
    m = re.search(patron, txt)
    return int(re.sub(r'\D', '', m.group(1))) if m else None


# ───────────────────────────── Senado ─────────────────────────────

def aplicar_senado(resumen, txt_nac, txt_ind, informe):
    out = copy.deepcopy(resumen)
    raw_nac = Path(txt_nac).read_text()
    ofic = {
        'validos': numero(raw_nac, r'TOTAL VOTOS VALIDOS\s+(\d{6,})'),
        'umbral': numero(raw_nac, r'UMBRAL\s+(\d{5,})'),
        'cifra': numero(raw_nac, r'CIFRA REPARTIDORA ES:\s*(\d{4,})'),
    }
    # La tabla «PARTIDOS QUE SUPERAN EL UMBRAL» trae el total en enteros sin puntos ni
    # letras: es la lectura más limpia del documento y manda sobre la del bloque.
    tabla_umbral = {}
    sec = raw_nac.split('PARTIDOS QUE SUPERAN EL UMBRAL', 1)
    if len(sec) == 2:
        for m in re.finditer(r'^[|\[\s]*(\d{5})\s+\|?(.+?)\s+(\d{5,8})\s*$', sec[1].split('CIFRA REPARTIDORA')[0], re.M):
            tabla_umbral[m.group(1)] = int(m.group(3))
    informe['tabla_umbral'] = tabla_umbral
    for circ, txt in (('NACIONAL', txt_nac), ('INDIGENAS', txt_ind)):
        por_cod, duplicados = {}, []
        for p0 in out['partidos']:
            k0 = p0['codigo'].zfill(5)
            if k0 in por_cod:
                duplicados.append((k0, p0))     # mismo código con dos grafías (CABILDO INDÉGENA / INDÍGENA TEVIS)
            else:
                por_cod[k0] = p0
        partidos, orden, esp = bloques(leer(txt), set(por_cod))
        circ_info = out['por_circunscripcion'][circ]
        suma_part = 0
        for cod in orden:
            bloque = partidos[cod]
            p = por_cod.get(cod)
            if p is None:
                informe['avisos'].append(f'Senado {circ}: partido {cod} {bloque["nombre"]} no está en nuestros datos')
                continue
            tot_ref = p['votos']
            # ojo: un total de 0 es válido (TEVIS), así que nada de encadenar con `or`
            tot = tabla_umbral.get(cod) if circ == 'NACIONAL' else None
            for fila in (bloque['total'], bloque.get('total_resumen')):
                if tot is None:
                    tot = total_validado(fila, tot_ref)
            if tot is None:
                informe['avisos'].append(f'Senado {circ}: sin total legible para {p["partido"]}; queda {tot_ref}')
                tot = tot_ref
            # candidatos
            nuestros = p.get('candidatos') or []
            usados = set()
            suma_c, cambios, dudosos = 0, 0, []
            for c in nuestros:
                cand_cne = [f for f in bloque['cands'] if (f['can'] or '').zfill(3) == str(c.get('codigo', '')).zfill(3)]
                cand_cne = [f for f in cand_cne if parecido(f['nombre'], c['nombre']) >= 0.5] or \
                           [f for f in bloque['cands'] if parecido(f['nombre'], c['nombre']) >= 0.75]
                cand_cne = [f for f in cand_cne if id(f) not in usados]
                f = max(cand_cne, key=lambda f: parecido(f['nombre'], c['nombre'])) if cand_cne else None
                v, motivo = elegir(f, c['votos'])
                if f is not None:
                    usados.add(id(f))
                if v is None and ('SENADO', c['nombre']) in MANUAL:
                    v, motivo = MANUAL[('SENADO', c['nombre'])], 'manual'
                if v is None:
                    v, motivo = elegir(buscar_linea(Path(txt).read_text(), c['nombre']), c['votos'])
                    motivo = 'linea' if v is not None else motivo
                if v is None:
                    dudosos.append(c['nombre'])
                    v = c['votos']
                elif v != c['votos']:
                    informe['cambios_candidato'].append(
                        {'corp': 'SENADO', 'circ': circ, 'partido': p['partido'], 'candidato': c['nombre'],
                         'antes': c['votos'], 'cne': v, 'delta': v - c['votos'], 'lectura': motivo})
                    cambios += 1
                c['votos'] = v
                suma_c += v
            lista_ref = tot_ref - sum(c0['votos'] for c0 in (resumen_partido(resumen, cod) or {}).get('candidatos', []) or [])
            lista = elegir(bloque['lista'], lista_ref)[0] if bloque['lista'] else None
            if not nuestros:            # lista cerrada: todo el voto va al partido
                lista = tot
            deducida = lista is None
            if not deducida and len(dudosos) == 1:
                # un solo candidato sin leer: su voto es lo que falta para el total del E-26
                c1 = next(c0 for c0 in nuestros if c0['nombre'] == dudosos[0])
                v1 = tot - lista - (suma_c - c1['votos'])
                if abs(v1 - c1['votos']) <= max(150, 0.03 * c1['votos']):
                    informe['cambios_candidato'].append(
                        {'corp': 'SENADO', 'circ': circ, 'partido': p['partido'], 'candidato': c1['nombre'],
                         'antes': c1['votos'], 'cne': v1, 'delta': v1 - c1['votos'], 'lectura': 'por resta'})
                    suma_c += v1 - c1['votos']
                    c1['votos'] = v1
                    dudosos = []
            if deducida:
                lista = tot - suma_c
            concilia = (lista + suma_c == tot) and (not deducida or abs(lista - lista_ref) <= max(150, 0.03 * lista_ref))
            informe['partidos'].append({
                'corp': 'SENADO', 'circ': circ, 'partido': p['partido'], 'antes': tot_ref, 'cne': tot,
                'delta': tot - tot_ref, 'candidatos_cambiados': cambios, 'sin_leer': dudosos,
                'concilia': concilia, 'lista': lista, 'suma_candidatos': suma_c})
            p['votos'] = tot
            suma_part += tot
            for k0, p0 in duplicados:            # el total del código ya quedó en la primera grafía
                if k0 == cod and p0 is not p:
                    informe['avisos'].append(f'Senado {circ}: {p0["partido"]} comparte código {cod}; queda en 0 (antes {p0["votos"]})')
                    p0['votos'] = 0
                    for c0 in p0.get('candidatos') or []:
                        c0['votos'] = 0
        # totales de la circunscripción
        validos = total_validado(esp.get('validos'))
        partes = total_validado(esp.get('partidos'), suma_part)
        nulos = total_validado(esp.get('nulos'), circ_info['votnul'])
        nomarc = total_validado(esp.get('nomarc'), circ_info['votnma'])
        if circ == 'NACIONAL':
            validos = validos or ofic['validos']
        blanco = total_validado(esp.get('blanco'), circ_info['votblan'])
        if partes is None:
            partes = suma_part
        if blanco is None and validos:
            blanco = validos - partes
        informe['totales'].append({'corp': 'SENADO', 'circ': circ, 'partidos_cne': partes, 'suma_partidos': suma_part,
                                   'blanco': blanco, 'nulos': nulos, 'nomarc': nomarc, 'validos': validos})
        if partes != suma_part:
            informe['avisos'].append(f'Senado {circ}: la suma de partidos ({suma_part}) no da el total del E-26 ({partes})')
        circ_info.update({'votval': partes, 'votblan': blanco, 'votnul': nulos, 'votnma': nomarc,
                          'votant': partes + blanco + nulos + nomarc})
        if circ == 'NACIONAL':
            circ_info['umbral'] = ofic['umbral']
            circ_info['cifra'] = ofic['cifra']
            circ_info['validos_con_blanco'] = validos
    nac = out['por_circunscripcion']['NACIONAL']
    for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant', 'cifra', 'umbral', 'validos_con_blanco'):
        out[k] = nac[k]
    out['fuente_nacional'] = FUENTE['senado']
    out['nota_territorial'] = ('Departamento, municipio, puesto y mesa: escrutinio de las comisiones generales '
                               '(abril 2026). El CNE no publicó su ajuste mesa a mesa.')
    out['actualizado_cne'] = datetime.now(timezone.utc).isoformat()
    return out


_RESUMEN_ORIG = {}


def resumen_partido(resumen, cod):
    if not _RESUMEN_ORIG:
        for p in resumen['partidos']:
            _RESUMEN_ORIG[p['codigo'].zfill(5)] = p
    return _RESUMEN_ORIG.get(cod)


def dhondt(votos, curules):
    cocientes = sorted(((v / d, n) for n, v in votos.items() for d in range(1, curules + 1)), reverse=True)[:curules]
    res = {n: 0 for n in votos}
    for _, n in cocientes:
        res[n] += 1
    return res, cocientes[-1][0]


# ───────────────────────────── Cámara ─────────────────────────────

def emparejar_partido(nombre_cne, nombres):
    n = ' '.join(norm(nombre_cne))
    mejor = max(nombres, key=lambda x: parecido(x, nombre_cne), default=None)
    if mejor and parecido(mejor, nombre_cne) >= 0.8:
        return mejor
    for x in nombres:
        if ' '.join(norm(x)).startswith(n[:25]):
            return x
    return None


def aplicar_camara_circ(circ_blob, txt, etiqueta, informe):
    """circ_blob = {'votval','votblan','votnul','votnma','votant','partidos':{nom:v},'candidatos':{nom:[...]}}.
    Devuelve deltas por partido {nombre: delta} y por candidato {(partido, nombre): delta}."""
    partidos, orden, esp = bloques(leer(txt))
    d_part, d_cand = {}, {}
    suma = 0
    for cod in orden:
        b = partidos[cod]
        nombre_cne = b['nombre'] or (b['total'] or {}).get('nombre', '')
        nom = emparejar_partido(nombre_cne, list(circ_blob['partidos'].keys()))
        if nom is None:
            informe['avisos'].append(f'Cámara {etiqueta}: partido {cod} {nombre_cne} no casa con nuestros datos')
            continue
        ref = circ_blob['partidos'][nom]
        tot = total_validado(b['total'], ref)
        if tot is None:
            informe['avisos'].append(f'Cámara {etiqueta}: sin total legible para {nom}; queda {ref}')
            tot = ref
        cambios, dudosos, suma_c = 0, [], 0
        usados = set()
        for c in circ_blob.get('candidatos', {}).get(nom, []):
            opts = [f for f in b['cands'] if (f['can'] or '').zfill(3) == str(c.get('codigo', '')).zfill(3)
                    and parecido(f['nombre'], c['nombre']) >= 0.5 and id(f) not in usados] or \
                   [f for f in b['cands'] if parecido(f['nombre'], c['nombre']) >= 0.75 and id(f) not in usados]
            f = max(opts, key=lambda f: parecido(f['nombre'], c['nombre'])) if opts else None
            v, motivo = elegir(f, c['votos'])
            if f is not None:
                usados.add(id(f))
            if v is None and ('CAMARA', c['nombre']) in MANUAL:
                v, motivo = MANUAL[('CAMARA', c['nombre'])], 'manual'
            if v is None:
                v, motivo = elegir(buscar_linea(Path(txt).read_text(), c['nombre']), c['votos'])
                motivo = 'linea' if v is not None else motivo
            if v is None:
                dudosos.append(c['nombre']); v = c['votos']
            elif v != c['votos']:
                informe['cambios_candidato'].append({'corp': 'CAMARA', 'circ': etiqueta, 'partido': nom,
                                                     'candidato': c['nombre'], 'antes': c['votos'], 'cne': v,
                                                     'delta': v - c['votos'], 'lectura': motivo})
                d_cand[(nom, c['nombre'])] = v - c['votos']
                cambios += 1
                c['votos'] = v
            suma_c += v
        lista = elegir(b['lista'], None)[0] if b['lista'] else 0
        if lista is not None and len(dudosos) == 1:
            c1 = next(c0 for c0 in circ_blob['candidatos'][nom] if c0['nombre'] == dudosos[0])
            v1 = tot - lista - (suma_c - c1['votos'])
            if abs(v1 - c1['votos']) <= max(150, 0.03 * c1['votos']):
                informe['cambios_candidato'].append({'corp': 'CAMARA', 'circ': etiqueta, 'partido': nom,
                                                     'candidato': c1['nombre'], 'antes': c1['votos'], 'cne': v1,
                                                     'delta': v1 - c1['votos'], 'lectura': 'por resta'})
                if v1 != c1['votos']:
                    d_cand[(nom, c1['nombre'])] = v1 - c1['votos']
                suma_c += v1 - c1['votos']
                c1['votos'] = v1
                dudosos = []
        concilia = lista is not None and lista + suma_c == tot
        informe['partidos'].append({'corp': 'CAMARA', 'circ': etiqueta, 'partido': nom, 'antes': ref, 'cne': tot,
                                    'delta': tot - ref, 'candidatos_cambiados': cambios, 'sin_leer': dudosos,
                                    'concilia': concilia, 'lista': lista, 'suma_candidatos': suma_c})
        if tot != ref:
            d_part[nom] = tot - ref
            circ_blob['partidos'][nom] = tot
        suma += tot
    partes = total_validado(esp.get('partidos'), suma)
    blanco = total_validado(esp.get('blanco'), circ_blob['votblan'])
    validos = total_validado(esp.get('validos'))
    if blanco is None and validos and partes:
        blanco = validos - partes
    nulos = total_validado(esp.get('nulos'), circ_blob['votnul'])
    nomarc = total_validado(esp.get('nomarc'), circ_blob['votnma'])
    if partes != suma:
        informe['avisos'].append(f'Cámara {etiqueta}: la suma de partidos ({suma}) no da el total del E-26 ({partes})')
    antes = {k: circ_blob[k] for k in ('votval', 'votblan', 'votnul', 'votnma')}
    circ_blob.update({'votval': partes, 'votblan': blanco, 'votnul': nulos, 'votnma': nomarc,
                      'votant': partes + blanco + nulos + nomarc})
    informe['totales'].append({'corp': 'CAMARA', 'circ': etiqueta, 'antes': antes,
                               'cne': {k: circ_blob[k] for k in ('votval', 'votblan', 'votnul', 'votnma')}})
    return d_part, d_cand, {k: circ_blob[k] - antes[k] for k in antes}


def sumar_deltas(blob, d_part, d_cand, d_tot):
    for k, v in d_tot.items():
        if k in blob and blob[k] is not None:
            blob[k] += v
    if 'votant' in blob:
        blob['votant'] = blob['votval'] + blob['votblan'] + blob['votnul'] + blob['votnma']
    parts = blob.get('partidos')
    if isinstance(parts, dict):
        for n, d in d_part.items():
            if n in parts:
                parts[n] += d
    cands = blob.get('candidatos')
    if isinstance(cands, dict):
        for (pn, cn), d in d_cand.items():
            for c in cands.get(pn, []):
                if c['nombre'] == cn:
                    c['votos'] += d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cne', required=True)
    ap.add_argument('--entrada', required=True)
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    cne, ent, sal = Path(a.cne), Path(a.entrada), Path(a.salida)
    man = Path(__file__).with_name('manual_cne.json')
    if man.exists():
        for corp, filas in json.loads(man.read_text()).items():
            if corp.startswith('_'):
                continue
            for nombre, votos in filas.items():
                MANUAL[(corp, nombre)] = votos
    informe = {'partidos': [], 'cambios_candidato': [], 'totales': [], 'avisos': [], 'curules': {}}

    # Senado
    sres = json.loads((ent / 'senado/resumen.json').read_text())
    nuevo = aplicar_senado(sres, cne / 'E26_SEN_NAC.txt', cne / 'E26_SEN_IND.txt', informe)
    nac_votos = {p['partido']: p['votos'] for p in nuevo['partidos']
                 if p['codigo'] not in ('0012', '0005') and p['votos'] >= nuevo['umbral']}
    asign, cifra = dhondt(nac_votos, 100)
    antes = {p['partido']: p.get('curules', 0) for p in sres['partidos']}
    informe['curules']['senado_nacional'] = {n: (antes.get(n), c) for n, c in asign.items() if antes.get(n) != c}
    informe['curules']['senado_cifra_calculada'] = int(cifra)
    (sal / 'senado').mkdir(parents=True, exist_ok=True)
    (sal / 'senado/resumen.json').write_text(json.dumps(nuevo, ensure_ascii=False))
    circ_path = ent / 'senado/circunscripciones.json'
    if circ_path.exists():
        circ = json.loads(circ_path.read_text())
        items = circ if isinstance(circ, list) else circ.get('circunscripciones', [])
        for c in items:
            nom = (c.get('nombre') or '').upper()
            src = nuevo['por_circunscripcion'].get('NACIONAL' if nom.startswith('NAC') else 'INDIGENAS' if nom.startswith('IND') else '')
            if src:
                for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant', 'cifra', 'umbral'):
                    if k in c and k in src:
                        c[k] = src[k]
        (sal / 'senado/circunscripciones.json').write_text(json.dumps(circ, ensure_ascii=False))

    # Cámara
    cres = json.loads((ent / 'camara/resumen.json').read_text())
    cdeps = json.loads((ent / 'camara/departamentos.json').read_text())
    (sal / 'camara').mkdir(parents=True, exist_ok=True)
    for dep, txt, nombre in (('17', 'E26_CAM_CHOCO.txt', 'Chocó'), ('15', 'E26_CAM_CUND.txt', 'Cundinamarca')):
        dj = json.loads((ent / f'camara/dep-{dep}.json').read_text())
        terr = dj['por_circunscripcion']['TERRITORIAL']
        d_part, d_cand, d_tot = aplicar_camara_circ(terr, cne / txt, f'TERRITORIAL {nombre}', informe)
        sumar_deltas(dj, d_part, d_cand, d_tot)                      # totales del departamento (todas las circ.)
        for e in cdeps:
            if e.get('cod') == dep and e.get('circ_nom') == 'TERRITORIAL':
                sumar_deltas(e, d_part, d_cand, d_tot)
        sumar_deltas(cres['por_circunscripcion']['TERRITORIAL'], {}, {}, d_tot)
        for k in ('votval', 'votblan', 'votnul', 'votnma'):
            cres[k] += d_tot[k]
        cres['votant'] = cres['votval'] + cres['votblan'] + cres['votnul'] + cres['votnma']
        for p in cres['partidos']:
            if p['partido'] in d_part:
                p['votos'] += d_part[p['partido']]
            for c in p.get('candidatos') or []:
                dd = d_cand.get((p['partido'], c['nombre']))
                if dd:
                    c['votos'] += dd
        # curules del departamento con votos CNE
        terr_umbral = {'17': 0.30, '15': 0.50}[dep]
        seats = {'17': 2, '15': 7}[dep]
        validos = terr['votval'] + terr['votblan']
        votos = {n: v for n, v in terr['partidos'].items() if v >= validos / seats * terr_umbral}
        if seats <= 2:   # circunscripciones de 2 curules: cuociente electoral y mayores residuos
            cuoc = validos / seats
            enteros = {n: int(v // cuoc) for n, v in votos.items()}
            resto = sorted(votos, key=lambda n: -(votos[n] / cuoc - enteros[n]))
            for n in resto[:seats - sum(enteros.values())]:
                enteros[n] += 1
            informe['curules'][f'camara_{nombre}'] = {n: c for n, c in enteros.items() if c}
        else:
            informe['curules'][f'camara_{nombre}'] = {n: c for n, c in dhondt(votos, seats)[0].items() if c}
        dj['fuente_nacional'] = FUENTE['camara']
        (sal / f'camara/dep-{dep}.json').write_text(json.dumps(dj, ensure_ascii=False))
    # Afro (Res. E-3401): el CNE confirmó los mismos totales que ya teníamos (468.961 por
    # partidos, 57.142 en blanco). Se verifica aparte, partido por partido, contra el MMV.
    cres['fuente_nacional'] = FUENTE['camara']
    cres['nota_territorial'] = ('Chocó y Cundinamarca: totales del departamento llevados al E-26 del CNE; '
                                'municipio, puesto y mesa siguen siendo el escrutinio de la comisión.')
    (sal / 'camara/resumen.json').write_text(json.dumps(cres, ensure_ascii=False))
    (sal / 'camara/departamentos.json').write_text(json.dumps(cdeps, ensure_ascii=False))
    (sal / 'informe.json').write_text(json.dumps(informe, ensure_ascii=False, indent=1, default=str))

    # resumen en consola
    for t in informe['totales']:
        print('TOTALES', t)
    no_conc = [p for p in informe['partidos'] if not p['concilia']]
    print(f"partidos: {len(informe['partidos'])} · no concilian: {len(no_conc)}")
    for p in no_conc:
        print('  ', p['corp'], p['circ'], p['partido'], 'cne', p['cne'], 'lista', p['lista'],
              'cands', p['suma_candidatos'], 'sin leer', len(p['sin_leer']))
    print('candidatos cambiados:', len(informe['cambios_candidato']))
    print('curules:', json.dumps(informe['curules'], ensure_ascii=False, default=str))
    for x in informe['avisos']:
        print('AVISO', x)


if __name__ == '__main__':
    main()
