#!/usr/bin/env python3
"""Atípicas con escrutinio oficial → atipicas/<clave>.json (los lee atipica.html?e=<clave>).

Fuente: los sitios de escrutinio de la Registraduría que siguen en línea para cada atípica
(«Consulta Documentos de Escrutinio»). Publican el MMV (mesa a mesa de votos) y el E-26
(declaratoria) de la comisión que cierra el escrutinio. Copia local en
Bases de datos/atipicas-escrutinio/<clave>/.

  Girón 2026 ........ publicacion-nacional-giron-2026 ......... /docs/MMV/…
  Bucaramanga 2025 .. publicacion-nacional-bucaramanga-2025 ... solo PDF (el CSV ya no está)
  Duitama 2025 ...... escrutinios-duitama-2025 ................ /documentos-atipicas-duitama/MMV/…
  Apartadó 2025 ..... escrutinios-apartado-2025 ............... /documentos-atipicas-apartado/MMV/…
  Vichada 2025 ...... escrutinios-vichada-2025 ................ /documentos-atipicas-vichada/MMV/…

Cada elección se CUADRA AL VOTO contra su E-26 (cifras transcritas abajo, en E26): si el
mesa a mesa no da exactamente lo declarado, el script aborta.

⚠ Apartadó: el MMV es el del escrutinio municipal, donde Héctor Rangel (004) suma 20.100
  votos. La comisión general (E-26 de la comisión 3055) los declaró NO MARCADOS porque su
  inscripción estaba suspendida, y declaró electo a Adolfo Romero. Se aplica ese ajuste
  puesto por puesto (sus votos pasan a no marcados) y se guardan aparte en `tachados`.
⚠ Bucaramanga: el sitio ya no sirve el MMV (devuelve la página de la aplicación). Solo hay
  totales, leídos del E-26 escaneado; el censo por puesto sí está.

Campos opcionales de una elección (hoy solo Duitama):
  'preconteo'  boletín final, transcrito y cuadrado: explica por qué circulan otras cifras.
  'mms'        mesa a mesa de sufragantes: mesas donde sufragantes y votos no coinciden.
  'tarjeton'   PDF de la tarjeta electoral: de ahí salen las fotos de cada candidato.
  'barrios'    capa de polígonos: el puesto va a su barrio por el NOMBRE oficial del georef
               y, si no casa, por punto en polígono. Con coordenadas de 9 m entre dos puestos
               y seis barrios errados, el polígono no puede mandar. Zonas 90 y 98 quedan
               fuera: el puesto censo y la cárcel no le pertenecen a un barrio.
"""
import csv
import json
import math
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BD = RAIZ / 'Bases de datos'
SRC = BD / 'atipicas-escrutinio'
GEOREF = BD / 'PUESTOS_GEOREF.csv'
OUT = RAIZ / 'atipicas'
ESPECIALES = {'996': 'blanco', '997': 'nulos', '998': 'nomarc'}

# código → (nombre completo, nombre corto, partido, color)
ELECCIONES = {
    'giron-2026': {
        'titulo': 'Alcaldía de Girón', 'depto': 'Santander', 'fecha': '2026-01-18', 'nivel': 'mun', 'dep': '27',
        'censo': (2026, 'ALCALDE GIRÓN - SANTANDER'),
        'mmv': 'giron-2026/MMV_XXX_27_091_XXX_XX_XX_XXX_3001.csv',
        'motivo': 'Se votó porque el Consejo de Estado anuló por doble militancia la elección de Campo Elías Ramírez en 2023. Ramírez volvió a inscribirse y ganó. Quien ganó completa el periodo 2024-2027.',
        'comision': 'escrutinio municipal (comisión 3001)',
        'cands': {
            '001': ('Campo Elías Ramírez Padilla', 'Campo Elías Ramírez', 'Coalición Campo Elías Alcalde', '#f08c00'),
            '005': ('William Mantilla Serrano', 'William Mantilla', 'Partido Conservador Colombiano', '#1c7ed6'),
            '004': ('Diego Armando Moreno Mantilla', 'Diego Moreno', 'Movimiento Político Colombia Humana', '#6B2D8B'),
            '003': ('Óscar Enrique Álvarez Ascanio', 'Óscar Álvarez', 'Por un Girón Diferente', '#2f9e44'),
            '006': ('Misael Luna Domínguez', 'Misael Luna', 'Partido Político La Fuerza', '#e64980'),
            '002': ('Fernando Humberto de Jesús Serrano Reina', 'Fernando Serrano', 'Partido Alianza Social Independiente «ASI»', '#868e96'),
        },
        'e26': {'001': 21367, '002': 60, '003': 655, '004': 1259, '005': 11638, '006': 384,
                'blanco': 1216, 'nulos': 377, 'nomarc': 55},
    },
    'duitama-2025': {
        'titulo': 'Alcaldía de Duitama', 'depto': 'Boyacá', 'fecha': '2025-05-04', 'nivel': 'mun', 'dep': '07',
        'censo': (2025, 'ALCALDE DUITAMA - BOYACÁ'),
        'mmv': 'duitama-2025/MMV_XXX_07_079_XXX_XX_XX_XXX_2453.csv',
        'motivo': 'Se votó porque el Consejo de Estado anuló por doble militancia la elección de José Luis Bohórquez en 2023. Quien ganó completa el periodo 2024-2027.',
        'comision': 'escrutinio municipal (comisión 2453)',
        'cands': {
            '004': ('Ingrith Rocío Bernal Mejía', 'Rocío Bernal', 'Coalición Duitama Nuestra Prioridad', '#a06ee0'),
            '002': ('Fernando Alexander Serrato Fonseca', 'Fernando Serrato', 'Duitama Una Sola Familia', '#f08c00'),
            '003': ('Wilfredy Bonilla Lagos', 'Wilfredy Bonilla', 'Wilfredy Alcalde', '#2f9e44'),
            '007': ('Diego Leonardo Sandoval Cepeda', 'Diego Sandoval', 'Fuerza Duitama', '#e64980'),
            '001': ('Rafael Antonio Pirajón López', 'Rafael Pirajón', 'Partido Centro Democrático', '#1866DF'),
            '005': ('Miguel Alberto Vergara Sandoval', 'Miguel Vergara', 'Nuevas Ideas por Duitama', '#868e96'),
            '006': ('Roberto Mayorga Mayorga', 'Roberto Mayorga', 'Movimiento Alianza Democrática Amplia', '#adb5bd'),
        },
        'e26': {'001': 847, '002': 9581, '003': 2238, '004': 22863, '005': 360, '006': 321, '007': 1883,
                'blanco': 1263, 'nulos': 462, 'nomarc': 23},
        'preconteo': {'boletin': 12, 'hora': '5:02 p. m.', 'archivo': 'Boletin_AL_12_07079.pdf',
                      'votos': {'001': 853, '002': 9547, '003': 2240, '004': 22755, '005': 359, '006': 323,
                                '007': 1867, 'blanco': 1261, 'nulos': 465, 'nomarc': 23}, 'total': 39693},
        'mms': 'duitama-2025/MMS_XXX_07_079_XXX_XX_XX_XXX_2453.csv',
        'tarjeton': {'archivo': 'duitama-2025/tarjeta-electoral-alcalde-duitama.pdf',
                     'pos': {'001': (71, 104), '002': (264, 104), '003': (459, 104), '004': (71, 335),
                             '005': (265, 334), '006': (460, 335), '007': (72, 562)}},
        'barrios': {'archivo': 'duitama-2025/barrios-arcgis.geojson', 'campo': 'BARRIOS'},
    },
    'apartado-2025': {
        'titulo': 'Alcaldía de Apartadó', 'depto': 'Antioquia', 'fecha': '2025-04-06', 'nivel': 'mun', 'dep': '01',
        'censo': (2025, 'ALCALDE APARTADÓ - ANTIOQUIA'),
        'mmv': 'apartado-2025/MMV_XXX_01_035_XXX_XX_XX_XXX_2453.csv',
        'motivo': 'Se votó porque el Consejo de Estado anuló por doble militancia la elección de Héctor Rangel Palacios en 2023. Rangel quedó en el tarjetón por un fallo de un juzgado de Turbo que el Tribunal de Antioquia revocó días antes de la votación. Sacó más votos que nadie, pero la comisión general declaró no marcados sus 20.100 votos y declaró electo a Adolfo Romero, para lo que resta del periodo 2024-2027.',
        'comision': 'escrutinio general (comisión 3055), sobre el mesa a mesa del escrutinio municipal (comisión 2453)',
        'tachados': {'004': 'su inscripción estaba suspendida'},
        'cands': {
            '002': ('Adolfo David Romero Benítez', 'Adolfo Romero', 'Coalición Romero', '#f08c00'),
            '001': ('Luis Gonzalo Giraldo Aguirre', 'Luis Gonzalo Giraldo', 'Partido Verde Oxígeno', '#2f9e44'),
            '003': ('Geritza Yanina Echeverría Quinto', 'Geritza Echeverría', 'Coalición por un Apartadó Diferente', '#e64980'),
            '007': ('Luis Augusto Medina Pulgarín', 'Luis Medina', 'Partido Político Dignidad & Compromiso', '#1c7ed6'),
            '005': ('Eduardo Enrique Zambrano Moreno', 'Eduardo Zambrano', 'Partido Nuevo Liberalismo', '#868e96'),
            '006': ('Raúl Galezo Montes', 'Raúl Galezo', 'Movimiento Salvación Nacional', '#adb5bd'),
            '004': ('Héctor Rangel Palacios Rodríguez', 'Héctor Rangel', 'Coalición Apartadó, Unidos por la Vida', '#495057'),
        },
        'e26': {'001': 1629, '002': 17130, '003': 1021, '004': 0, '005': 329, '006': 106, '007': 381,
                'blanco': 1269, 'nulos': 493, 'nomarc': 20207},
    },
    'vichada-2025': {
        'titulo': 'Gobernación del Vichada', 'depto': 'Vichada', 'fecha': '2025-06-15', 'nivel': 'dep', 'dep': '72',
        'censo': (2025, 'GOBERNADOR VICHADA'),
        'mmv': 'vichada-2025/MMV_XXX_72_000_XXX_XX_XX_XXX_1385.csv',
        'motivo': 'Se votó porque la Corte Suprema confirmó la condena por peculado del gobernador elegido en 2023, Hecson Alexys Benito Castro. Quien ganó completa el periodo hasta el 31 de diciembre de 2027.',
        'comision': 'escrutinio general (comisión 1385)',
        'cands': {
            '002': ('Fulberto Guevara', 'Fulberto Guevara', 'Fulberto', '#2f9e44'),
            '001': ('Juan Carlos Cordero Rojas', 'Juan Carlos Cordero', 'Vichada en Buenas Manos', '#f08c00'),
        },
        'e26': {'001': 14201, '002': 14598, 'blanco': 278, 'nulos': 200, 'nomarc': 171},
    },
    'bucaramanga-2025': {
        'titulo': 'Alcaldía de Bucaramanga', 'depto': 'Santander', 'fecha': '2025-12-14', 'nivel': 'total', 'dep': '27',
        'censo': (2025, 'ALCALDE BUCARAMANGA - SANTANDER'),
        'motivo': 'Se votó porque el Consejo de Estado anuló por doble militancia la elección de Jaime Andrés Beltrán en 2023. Quien ganó completa el periodo 2024-2027.',
        'comision': 'escrutinio municipal (comisión 3001)',
        'cands': {
            '003': ('Cristian Fernando Portilla Pérez', 'Cristian Portilla', 'Coalición con Paso Firme Bucaramanga Avanza', '#f08c00'),
            '005': ('Carlos Enrique Bueno Cadena', 'Carlos Bueno', 'Un Alcalde Bueno', '#1c7ed6'),
            '008': ('Edinson Fabián Oviedo Pinzón', 'Edinson Oviedo', 'Partido Nuevo Liberalismo', '#e64980'),
            '007': ('Humberto Salazar García', 'Humberto Salazar', 'Pacto Histórico', '#6B2D8B'),
            '004': ('Jhan Carlos Alvernia Vergel', 'Jhan Carlos Alvernia', 'Partido Liberal Colombiano', '#e03131'),
            '002': ('Juan Manuel González Bustos', 'Juan Manuel González', 'Partido Demócrata Colombiano', '#868e96'),
            '001': ('Carlos Fernando Pérez Gélvez', 'Carlos Pérez', 'Movimiento Alianza Democrática Amplia', '#adb5bd'),
            '006': ('Rubén Fernando Morales Rey', 'Rubén Morales', 'Partido del Trabajo de Colombia', '#ced4da'),
        },
        # E-26 escaneado, leído a ojo y cuadrado: los candidatos suman 133.541, como dice el acta
        'e26': {'001': 697, '002': 1299, '003': 63646, '004': 5100, '005': 26297, '006': 443, '007': 15356,
                '008': 20703, 'blanco': 5389, 'nulos': 1318, 'nomarc': 125},
    },
}


def censo_por_puesto(anio, tipo):
    d = json.load(open(BD / 'censos-registraduria' / f'{anio}_datos_censo-electoral-min.json'))
    out = {}
    for r in next(iter(d.values())):
        if r['tipo_eleccion'] != tipo:
            continue
        k = (r['cod_mun'].zfill(3), r['zona'].zfill(2), r['cod_puesto'].zfill(2))
        out[k] = {'nombre': r['puesto_votacion'].strip(), 'mun': r['municipio'].strip(),
                  'censo': r['potencial_electoral'], 'm': r['sexo']['mujeres'], 'h': r['sexo']['hombres']}
    if not out:
        raise SystemExit(f'sin censo para {tipo} ({anio})')
    return out


def georef(dep):
    pos = {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            c = r['CÓDIGO COMPLETO']
            if c[:2] != dep:
                continue
            try:
                pos[(c[2:5], c[5:7], c[7:9])] = (round(float(r['LATITUD']), 6), round(float(r['LONGITUD']), 6))
            except ValueError:
                pass
    return pos


def clave_nombre(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return ' '.join(s.split())


def barrio_georef(dep):
    out = {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            c = r['CÓDIGO COMPLETO']
            if c[:2] == dep:
                out[(c[2:5], c[5:7], c[7:9])] = (r['BARRIO'] or '').strip()
    return out


def poligonos(geom):
    return [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']


def en_anillo(x, y, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][:2]
        xj, yj = anillo[j][:2]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def en_poligono(x, y, geom):
    return any(en_anillo(x, y, p[0]) and not any(en_anillo(x, y, h) for h in p[1:]) for p in poligonos(geom))


def centro(geom):
    pts = [c for p in poligonos(geom) for c in p[0]]
    return sum(c[0] for c in pts) / len(pts), sum(c[1] for c in pts) / len(pts)


def redondear(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [redondear(c) for c in coords]


def construir_barrios(clave, cfg, puestos):
    """Capa de barrios con el puesto que cae en cada uno. El barrio sin puesto hereda, solo para
    pintar, el del barrio con puesto más cercano (`de`); nunca suma a un total."""
    capa = json.load(open(SRC / cfg['barrios']['archivo'], encoding='utf-8'))
    campo = cfg['barrios']['campo']
    feats = capa['features']
    por_nombre = {clave_nombre(f['properties'][campo]): f for f in feats}
    georef_b = barrio_georef(cfg['dep'])
    asignados = defaultdict(list)
    fuera = []
    for p in puestos:
        cod = p['zona'] + p['pue']
        if p['zona'] in ('90', '98'):
            fuera.append(cod)
            continue
        f = por_nombre.get(clave_nombre(georef_b.get((p['mun'], p['zona'], p['pue']))))
        if f is None and p.get('ll'):
            f = next((g for g in feats if en_poligono(p['ll'][1], p['ll'][0], g['geometry'])), None)
        if f is None:
            fuera.append(cod)
            continue
        asignados[f['properties'][campo]].append(cod)
    con_dato = [f for f in feats if f['properties'][campo] in asignados]
    salida = []
    for f in feats:
        n = f['properties'][campo]
        props = {'n': nice(n)}
        if n in asignados:
            props['pu'] = asignados[n]
        else:
            cx, cy = centro(f['geometry'])
            cerca = min(con_dato, key=lambda g: math.hypot(centro(g['geometry'])[0] - cx, centro(g['geometry'])[1] - cy))
            props['de'] = cerca['properties'][campo]
        salida.append({'type': 'Feature', 'properties': props,
                       'geometry': {'type': f['geometry']['type'], 'coordinates': redondear(f['geometry']['coordinates'])}})
    for f in salida:
        if 'de' in f['properties']:
            f['properties']['de'] = nice(f['properties']['de'])
    (OUT / 'geo').mkdir(exist_ok=True)
    (OUT / 'geo' / f'{clave}-barrios.json').write_text(
        json.dumps({'type': 'FeatureCollection', 'features': salida}, ensure_ascii=False, separators=(',', ':')))
    return {'con_dato': len(con_dato), 'total': len(feats), 'puestos_fuera': fuera}


def extraer_fotos(clave, cfg):
    """Las fotos de la tarjeta electoral, por la posición de cada casilla en el PDF."""
    import pymupdf
    pdf = pymupdf.open(SRC / cfg['tarjeton']['archivo'])
    pagina = pdf[0]
    fotos = []
    for im in pagina.get_images(full=True):
        if (im[2], im[3]) == (354, 472):
            r = pagina.get_image_rects(im[0])[0]
            fotos.append((r.x0, r.y0, im[0], im[1]))
    dest = OUT / 'fotos' / clave
    dest.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for cod, (x, y) in cfg['tarjeton']['pos'].items():
        fx, fy, xref, smask = min(fotos, key=lambda f: math.hypot(f[0] - x, f[1] - y))
        if math.hypot(fx - x, fy - y) > 3:
            raise SystemExit(f'{clave}: no hay foto en la casilla de {cod}')
        px = pymupdf.Pixmap(pdf, xref)
        if px.alpha or px.colorspace.n != 3:
            px = pymupdf.Pixmap(pymupdf.csRGB, px)
        if smask:
            px = pymupdf.Pixmap(px, pymupdf.Pixmap(pdf, smask))
            lienzo = pymupdf.open()
            hoja = lienzo.new_page(width=px.width, height=px.height)
            hoja.insert_image(hoja.rect, pixmap=px)
            px = hoja.get_pixmap(alpha=False)
        (dest / f'{cod}.jpg').write_bytes(px.tobytes('jpeg', jpg_quality=86))
        rutas[cod] = f'atipicas/fotos/{clave}/{cod}.jpg'
    return rutas


def cotejo_mms(cfg, votos_mesa):
    filas = list(filas_mmv(SRC / cfg['mms']))
    distintas = []
    for r in filas:
        k = (r['ZONA'], r['PUESTO'], r['MESA'])
        suf = int(r['SUFRAGANTES'] or 0)
        if suf != votos_mesa.get(k, 0):
            distintas.append({'puesto': r['PUESNOMBRE'].strip(), 'zona': r['ZONA'], 'mesa': r['MESA'],
                              'sufragantes': suf, 'votos': votos_mesa.get(k, 0)})
    return {'mesas': len(filas), 'sufragantes': sum(int(r['SUFRAGANTES'] or 0) for r in filas),
            'recontadas_jurados': sum(r['RECUENTOJURADOS'] == 'SI' for r in filas),
            'modificadas': sum(r['MODIFICADA'] == 'SI' for r in filas),
            'excluidas': sum(r['EXCLUIDA'] == 'SI' for r in filas), 'distintas': distintas}


def filas_mmv(path):
    t = path.read_text(encoding='utf-8-sig')
    i = t.find('DEP;DEPNOMBRE')
    if i < 0:
        raise SystemExit(f'sin encabezado: {path}')
    return csv.DictReader(t[i:].splitlines(), delimiter=';')


def nice(s):
    minus = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'EL', 'EN'}
    return ' '.join(w.lower() if i and w in minus else w.capitalize() for i, w in enumerate(s.split()))


def construir(clave, cfg):
    orden = list(cfg['cands'])
    cands = [{'cod': c, 'nombre': n, 'corto': k, 'partido': p, 'color': col}
             for c, (n, k, p, col) in cfg['cands'].items()]
    tach = cfg.get('tachados', {})
    for c in cands:
        if c['cod'] in tach:
            c['tachado'] = tach[c['cod']]
    censo = censo_por_puesto(*cfg['censo'])
    res = {'clave': clave, 'eleccion': cfg['titulo'], 'depto': cfg['depto'], 'fecha': cfg['fecha'],
           'nivel': cfg['nivel'], 'dep': cfg['dep'], 'motivo': cfg['motivo'],
           'fuente': f"Registraduría Nacional · {cfg['comision']}", 'candidatos': cands,
           'censo_total': sum(p['censo'] for p in censo.values())}
    e26 = cfg['e26']

    pre = cfg.get('preconteo')
    if pre:
        suma = sum(pre['votos'].values())
        if suma != pre['total']:
            raise SystemExit(f'{clave}: el boletín no suma {pre["total"]} → {suma}')
        res['preconteo'] = {'boletin': pre['boletin'], 'hora': pre['hora'], 'total': pre['total'],
                            'v': [pre['votos'][c] for c in orden], 'blanco': pre['votos']['blanco'],
                            'nulos': pre['votos']['nulos'], 'nomarc': pre['votos']['nomarc']}

    if cfg['nivel'] == 'total':
        res['totales'] = {'v': [e26[c] for c in orden], 'blanco': e26['blanco'], 'nulos': e26['nulos'],
                          'nomarc': e26['nomarc'], 'censo': res['censo_total'], 'puestos': len(censo)}
        return res

    votos = defaultdict(lambda: defaultdict(int))
    mesas = defaultdict(set)
    nombres = {}
    muns = {}
    comunas = {}
    votos_mesa = defaultdict(int)
    for r in filas_mmv(SRC / cfg['mmv']):
        if not (r.get('VOTOS') or '').strip().isdigit():
            continue
        k = (r['MUN'].zfill(3), r['ZONA'].zfill(2), r['PUESTO'].zfill(2))
        can = r['CAN'].strip()
        if can not in ESPECIALES and can not in cfg['cands']:
            raise SystemExit(f'{clave}: candidato {can} {r["CANNOMBRE"]} no está en la configuración')
        votos[k][ESPECIALES.get(can, can)] += int(r['VOTOS'])
        votos_mesa[(r['ZONA'], r['PUESTO'], r['MESA'])] += int(r['VOTOS'])
        mesas[k].add(r['MESA'])
        comunas.setdefault(k, (r['COMUCODIGO'].strip(), r['COMUNOMBRE'].strip()))
        nombres.setdefault(k, r['PUESNOMBRE'].strip())
        muns.setdefault(k[0], nice(r['MUNNOMBRE'].strip()))

    # votos declarados no marcados por la comisión general (Apartadó)
    tachados = defaultdict(dict)
    for k, v in votos.items():
        for c in tach:
            if v.get(c):
                tachados[k][c] = v[c]
                v['nomarc'] += v[c]
                v[c] = 0

    # cuadre al voto contra el E-26
    tot = defaultdict(int)
    for v in votos.values():
        for x, n in v.items():
            tot[x] += n
    malos = {x: (tot.get(x, 0), n) for x, n in e26.items() if tot.get(x, 0) != n}
    if malos:
        raise SystemExit(f'{clave}: el mesa a mesa no cuadra con el E-26 → {malos}')

    pos = georef(cfg['dep'])
    puestos = []
    for k in sorted(votos):
        p = censo.get(k, {})
        ll = pos.get(k)
        fila = {'mun': k[0], 'zona': k[1], 'pue': k[2], 'nombre': p.get('nombre') or nombres[k],
                'censo': p.get('censo'), 'm': p.get('m'), 'h': p.get('h'), 'mesas': len(mesas[k]),
                'v': [votos[k].get(c, 0) for c in orden],
                'blanco': votos[k]['blanco'], 'nulos': votos[k]['nulos'], 'nomarc': votos[k]['nomarc']}
        if comunas.get(k):
            fila['com'], fila['comn'] = comunas[k][0], nice(comunas[k][1])
        if ll:
            fila['ll'] = ll
        if k in tachados:
            fila['tachados'] = [tachados[k].get(c, 0) for c in orden]
        puestos.append(fila)
    res['municipios'] = muns
    res['puestos'] = puestos
    res['puestos_sin_censo'] = sum(1 for k in votos if k not in censo)
    res['puestos_sin_ubicacion'] = sum(1 for p in puestos if 'll' not in p)
    if cfg.get('mms'):
        res['mms'] = cotejo_mms(cfg, votos_mesa)
    if cfg.get('tarjeton'):
        fotos = extraer_fotos(clave, cfg)
        for c in cands:
            c['foto'] = fotos[c['cod']]
    if cfg.get('barrios'):
        res['barrios'] = construir_barrios(clave, cfg, puestos)
    return res


def main():
    OUT.mkdir(exist_ok=True)
    for clave, cfg in ELECCIONES.items():
        r = construir(clave, cfg)
        (OUT / f'{clave}.json').write_text(json.dumps(r, ensure_ascii=False, separators=(',', ':')))
        e26 = cfg['e26']
        vot = sum(v for v in e26.values())
        extra = '' if r['nivel'] == 'total' else (
            f" · {len(r['puestos'])} puestos ({r['puestos_sin_censo']} sin censo, {r['puestos_sin_ubicacion']} sin ubicación)")
        print(f"{clave:18s} cuadra con el E-26 · votantes {vot:,} · censo {r['censo_total']:,} · "
              f"participación {vot / r['censo_total']:.1%}{extra}")


if __name__ == '__main__':
    main()
