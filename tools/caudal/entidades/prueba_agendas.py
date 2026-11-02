#!/usr/bin/env python3
"""Pruebas de harvest_agendas.py SIN tocar ninguna fuente ni la línea base real.

Las fotos y los libros son de mentira; cada caso es una forma de mentirle al cliente
que hay que evitar: decir que una norma salió porque el sitio estaba caído, o avisar
como nueva una norma que solo cambió de redacción.

    python3 tools/caudal/entidades/prueba_agendas.py      # sale con 1 si algo falla
"""
import datetime
import hashlib
import io
import json
import stat
import sys
import tempfile
from pathlib import Path

import openpyxl

import comun as C
import harvest_agendas as H

FALLAS = []


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


def fila(clave, nombre='Proyecto de prueba', fecha='2027-03-01', k='minx', tipo='Decreto', tema='Tema', estado='', texto=''):
    return {'clave': clave, 'k': k, 'entidad': k, 'obligada': True, 'anio': '2027', 'nombre': nombre, 'tema': tema, 'tipo_norma': tipo,
            'fecha_prevista': fecha, 'fecha_texto': texto, 'estado': estado, 'url': 'https://x', 'capturado': 'x'}


def foto(filas=(), capturado='2026-11-01T23:00:00-05:00', **agendas):
    """agendas: k=estado. Una `k` con filas y sin estado queda publicada."""
    filas = list(filas)
    ks = dict.fromkeys(f['k'] for f in filas)
    ks.update(agendas)
    ag = []
    for k, estado in ks.items():
        n = sum(1 for f in filas if f['k'] == k)
        a = H._agenda(k, k, True, estado or 'publicada', 'sitio', 'https://x', n_normas=n)
        ag.append(a)
    return {'capturado': capturado, 'sucop_ok': True, 'agendas': ag, 'filas': filas}


def prueba_comparacion():
    print('comparación')
    a = foto([fila('sucop:1'), fila('sucop:2', fecha='2027-05-10'), fila('sucop:3')])
    r = H.comparar(a, a)
    ok(not any(r['resumen'].values()), 'dos fotos iguales: ningún cambio')

    b = foto([fila('sucop:1'), fila('sucop:2', fecha='2027-08-10'), fila('sucop:4', nombre='Norma nueva')])
    r = H.comparar(a, b)
    ok([x['clave'] for x in r['entran']] == ['sucop:4'] and r['entran'][0]['motivo'] == 'agregada', 'entra la norma nueva')
    ok([x['clave'] for x in r['salen']] == ['sucop:3'], 'sale la que ya no está')
    c = r['cambian_fecha']
    ok(len(c) == 1 and c[0]['de'] == '2027-05-10' and c[0]['a'] == '2027-08-10' and c[0]['dias'] == 92 and c[0]['sentido'] == 'se aplaza', 'cambia de fecha y dice cuánto')
    r = H.comparar(b, a)
    ok(r['cambian_fecha'][0]['sentido'] == 'se adelanta' and r['cambian_fecha'][0]['dias'] == -92, 'también al revés: se adelanta')

    t1 = foto([fila('minx:a', fecha='', texto='Por definir')])
    t2 = foto([fila('minx:a', fecha='2027-06-01')])
    r = H.comparar(t1, t2)
    ok(len(r['cambian_fecha']) == 1 and r['cambian_fecha'][0]['dias'] is None, 'de «por definir» a una fecha cuenta como cambio, sin inventar días')

    e1 = foto([fila('sucop:1', estado='Planeación de la consulta')])
    e2 = foto([fila('sucop:1', estado='En consulta pública')])
    r = H.comparar(e1, e2)
    ok(r['cambian_otro'][0]['campos'] == {'estado': ['Planeación de la consulta', 'En consulta pública']}, 'detecta que la norma abrió consulta')

    print('lo no leído no se inventa')
    a = foto([fila('sucop:1'), fila('sucop:2')])
    r = H.comparar(a, foto(minx='no_leida'))
    ok(not r['salen'] and r['sin_comparar'][0]['normas_desde'] == 2, 'sitio caído en la foto nueva: nada sale, queda sin comparar')
    r = H.comparar(foto(minx='no_leida'), a)
    ok(not r['entran'] and r['sin_comparar'][0]['normas_hasta'] == 2, 'sitio caído en la foto vieja: nada entra')
    r = H.comparar(a, foto(minx='publicada_sin_leer'))
    ok(not r['salen'] and r['sin_comparar'], 'agenda en PDF sin extraer: no es una agenda vacía')
    r = H.comparar(a, foto(minx='no_publicada'))
    ok(not r['salen'] and 'ya no aparece' in r['sin_comparar'][0]['motivo'], 'agenda que desaparece de la fuente: no se dan sus normas por retiradas')
    otra = foto([fila('sucop:9', k='miny')])
    r = H.comparar(a, otra)
    ok(not r['salen'] and any(x['k'] == 'minx' for x in r['sin_comparar']), 'entidad ausente de la foto nueva: queda sin comparar')
    ok(all(x['motivo'] == 'agenda_nueva' for x in r['entran']) and r['agendas_nuevas'] == ['miny'], 'entidad que no estaba: agenda nueva')

    print('agenda que llega tarde')
    r = H.comparar(foto(minx='no_publicada'), a)
    ok(len(r['entran']) == 2 and all(x['motivo'] == 'agenda_nueva' for x in r['entran']) and r['agendas_nuevas'] == ['minx'], 'no publicada → publicada: agenda nueva, sus normas entran')
    r = H.comparar(foto(minx='publicada_sin_normas'), a)
    ok(not r['agendas_nuevas'] and all(x['motivo'] == 'agregada' for x in r['entran']), 'publicada vacía → con filas: agregadas')

    print('misma norma con otra redacción')
    titulo = 'Por el cual se reglamenta el subsidio familiar de vivienda para trabajadores formales del sector rural'
    corregido = 'Por el cual se reglamenta el subsidio familiar de vivienda a trabajadores formales del sector rural'
    r = H.comparar(foto([fila('minx:a', titulo)]), foto([fila('minx:b', corregido)]))
    ok(not r['entran'] and not r['salen'] and len(r['cambian_otro']) == 1, 'hash distinto, mismo título corregido: no es entrada ni salida')
    r = H.comparar(foto([fila('minx:a', titulo, fecha='2027-01-01')]), foto([fila('sucop:7', titulo, fecha='2027-02-01')]))
    ok(not r['entran'] and not r['salen'] and len(r['cambian_fecha']) == 1, 'pasa del sitio a SUCOP: la misma norma, y se ve el cambio de fecha')
    r = H.comparar(foto([fila('minx:a', 'Por la cual se modifica la Resolución 2335 de 2023 sobre etiquetado')]),
                   foto([fila('minx:b', 'Por la cual se modifica la Resolución 1211 de 2023 sobre etiquetado')]))
    ok(len(r['entran']) == 1 and len(r['salen']) == 1, 'cita otra resolución: son dos normas distintas')
    r = H.comparar(foto([fila('sucop:1', titulo)]), foto([fila('sucop:2', titulo)]))
    ok(len(r['entran']) == 1 and len(r['salen']) == 1, 'dos id de SUCOP nunca se emparejan')


def prueba_guarda():
    print('guarda')
    prev = foto([fila(f'sucop:{i}') for i in range(10)])
    caida = foto([fila('sucop:1')])
    H.aplicar_guarda(caida['agendas'], prev)
    ok(not caida['agendas'][0]['leida'] and caida['agendas'][0].get('guarda'), 'de 10 a 1 normas: no cuenta como leída')
    r = H.comparar(prev, caida)
    ok(not r['salen'] and r['sin_comparar'], 'esa caída no se reporta como 9 salidas')
    normal = foto([fila(f'sucop:{i}') for i in range(8)])
    H.aplicar_guarda(normal['agendas'], prev)
    ok(normal['agendas'][0]['leida'], 'de 10 a 8 normas: pasa, puede ser real')
    vacia = foto(minx='publicada_sin_normas')
    H.aplicar_guarda(vacia['agendas'], prev)
    ok(not vacia['agendas'][0]['leida'], 'de 10 a 0 normas: no cuenta como leída')
    siguiente = foto([fila('sucop:1')])
    H.aplicar_guarda(siguiente['agendas'], caida)
    ok(siguiente['agendas'][0]['leida'], 'la corrida siguiente ya no la frena')
    r = H.comparar(prev, siguiente)
    ok(len(r['salen']) == 9, 'y contra la línea base la caída real sí se ve')


def libro():
    wb = openpyxl.Workbook()
    s = wb.active
    s.title = 'Agenda'
    cab = ['Nombre del proyecto normativo ', 'Dependencia técnica ', 'Nombre del responsable técnico', 'Cargo del responsable técnico', 'Entidades participantes',
           'Entidades firmantes', 'Competencia legal', 'Tema u objeto de la reglamentación', 'Norma concreta que se reglamenta o modifica', 'Tipo de instrumento jurídico ',
           'Origen de la iniciativa ', '¿Es un reglamento técnico? ', '¿Tiene costo? ', '¿Adopta o modifica un trámite? ', '¿Deroga? ', 'En caso de que aplique',
           'Fecha de inicio del proceso de consulta pública']

    def f(nombre, tema, tipo, fecha, resp='Fulana de Tal'):
        return [nombre, 'Dirección X', resp, 'Directora', '', '', '', tema, 'Ley 1 de 2020', tipo, 'Ley', 'No', 'No', 'No', 'No', '', fecha]

    s.append(['Información del proyecto a reglamentar'])
    s.append(cab)
    s.append(f('Norma pegada arriba', 'Objeto 1', 'Decreto', datetime.datetime(2027, 2, 1)))     # como MinComercio
    s.append(['Agenda Regulatoria'])
    s.append(['Nombre de la entidad ', 'MINISTERIO DE PRUEBA'])
    s.append(cab)
    s.append([None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, '¿Cuál es la razón para su derogación?'])
    s.append(f('Norma pegada arriba', 'Objeto 1', 'Decreto', datetime.datetime(2027, 2, 1)))
    s.append(f('Misma norma, otro objeto', 'Objeto 2', 'Resolución 2120 de 2019. Texto suelto', 'Por definir por el MSPS'))
    s.append(f('Misma norma, otro objeto', 'Objeto 3', 'Iniciativa propia', '6 de marzo 2026'))
    s.append(f(None, 'Objeto huérfano', 'Decreto', None))
    s.append(f('Bloque pegado sin fecha', 'Objeto 4', 'Resolución', None))              # como MinSalud
    s.append(f('Fechas que no cuadran', 'Objeto 5', 'Resolución', datetime.datetime(2027, 4, 1)))
    s.append(f('Bloque pegado sin fecha', 'Objeto 4', 'Resolución', datetime.datetime(2027, 6, 1)))
    s.append(f('Fechas que no cuadran', 'Objeto 5', 'Resolución', datetime.datetime(2027, 9, 1)))
    s.append(f('Con correo', 'Escribir a alguien@entidad.gov.co', 'Circular.', '15/03/2027'))
    h = wb.create_sheet('Oculta')
    h.sheet_state = 'hidden'
    h.append(cab)
    h.append(f('No debe entrar', 'x', 'Decreto', None))
    v = wb.create_sheet('Listas')
    v.append(['Decreto', 'Resolución'])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def prueba_libro():
    print('lectura del libro')
    crudas, sin_nombre = H.filas_de_libro(libro())
    nombres = [r['nombre'] for r in crudas]
    ok('No debe entrar' not in nombres, 'la hoja oculta no entra')
    ok(sin_nombre == 1, 'la fila sin nombre se cuenta como descartada')
    ok(not any('Fulana' in json.dumps(r, ensure_ascii=False) for r in crudas), 'el responsable técnico no se copia')
    ok(not any('@' in json.dumps(r) for r in crudas), 'los correos se quitan')
    ok(crudas[0]['fecha_prevista'] == '2027-02-01', 'fecha de Excel a ISO')
    por = crudas[2]
    ok(por['tipo_norma'] == 'Resolución' and por['fecha_prevista'] == '' and por['fecha_texto'].startswith('Por definir'), 'texto libre: tipo normalizado y fecha sin inventar')
    ok(crudas[3]['tipo_norma'] == 'No especificado' and crudas[3]['fecha_prevista'] == '2026-03-06', '«Iniciativa propia» no es un tipo; «6 de marzo 2026» sí es fecha')
    ok(crudas[-1]['fecha_prevista'] == '2027-03-15' and crudas[-1]['tipo_norma'] == 'Circular', 'dd/mm/aaaa')

    wb = openpyxl.Workbook()
    wb.active.append(['Otra cosa', 'sin formato'])
    b = io.BytesIO()
    wb.save(b)
    try:
        H.filas_de_libro(b.getvalue())
        ok(False, 'un libro sin el formato debe fallar')
    except ValueError:
        ok(True, 'un libro sin el formato falla: no es una agenda vacía')
    ok(H.libros_de(b'%PDF-1.7 algo') == [], 'un PDF no se toma por libro')
    ok(H.libros_de(b.getvalue()) == [b.getvalue()], 'un XLSX se reconoce aunque sea un ZIP por dentro')


def prueba_desde_archivo():
    print('archivo de un sitio')
    original, bajar = H._bajar, H.ORIGINALES
    with tempfile.TemporaryDirectory() as t:
        H.ORIGINALES = Path(t)
        try:
            H._bajar = lambda url: libro()
            ob = dict(k='minx', nombre='Ministerio X')
            a, fs = H.desde_archivo(ob, 'https://x/a.xlsx', 'https://x', 'hoy')
            ok(a['estado'] == 'publicada' and a['descartes'] == {'sin_nombre': 1, 'repetidas': 3, 'fecha_de_la_repetida': 1, 'fechas_en_conflicto': 1},
               'declara repetidas, sin nombre y conflictos')
            ok(a['n_normas'] == 6 and len({f['clave'] for f in fs}) == 6, 'mismo título con otro objeto son dos normas, con claves distintas')
            g = {f['nombre']: f for f in fs}
            ok(g['Bloque pegado sin fecha']['fecha_prevista'] == '2027-06-01', 'bloque pegado dos veces: la fecha sale de la copia que la trae')
            ok(g['Fechas que no cuadran']['fecha_prevista'] == '2027-04-01' and g['Fechas que no cuadran']['fecha_alterna'] == '2027-09-01', 'dos fechas distintas: se conservan ambas')
            H._bajar = lambda url: b'%PDF-1.7'
            a, fs = H.desde_archivo(ob, 'https://x/a.pdf', 'https://x', 'hoy')
            ok(a['estado'] == 'publicada_sin_leer' and not a['leida'] and a['publicada'] and not fs, 'un PDF: publicada, no leída y sin filas')
        finally:
            H._bajar, H.ORIGINALES = original, bajar


def prueba_fotos():
    print('fotos inmutables')
    viejos = H.FOTOS, H.BASE, H.VISTA
    with tempfile.TemporaryDirectory() as t:
        H.FOTOS, H.BASE, H.VISTA = Path(t) / 'fotos', Path(t) / 'linea-base.json', Path(t) / 'agendas.json'
        try:
            caida = {**foto([fila('sucop:1')]), 'sucop_ok': False}
            n0 = H.guardar_foto(caida)
            ok(not caida['linea_base'] and not H.BASE.exists(), 'con SUCOP caído la foto no puede ser línea base')
            uno = foto([fila('sucop:1')], capturado='2026-11-01T23:30:00-05:00')
            n1 = H.guardar_foto(uno)
            ok(uno['linea_base'] and C.leer(H.BASE)['foto'] == n1, 'la primera foto buena queda como línea base')
            modo = stat.S_IMODE((H.FOTOS / n1).stat().st_mode)
            ok(modo == 0o444, 'la foto queda en solo lectura')
            dos = foto([fila('sucop:1'), fila('sucop:2')], capturado='2026-11-02T06:00:00-05:00')
            n2 = H.guardar_foto(dos)
            ok(not dos['linea_base'] and C.leer(H.BASE)['foto'] == n1, 'la segunda no le quita el lugar')
            try:
                H.guardar_foto(foto(capturado='2026-11-02T06:00:00-05:00'))
                ok(False, 'una foto no se reescribe')
            except FileExistsError:
                ok(True, 'una foto no se reescribe: misma marca de tiempo, error')
            base = H.cargar_base()
            ok(base['capturado'] == uno['capturado'], 'la línea base se carga y su sha256 coincide')
            v = H.armar_vista(dos, n2, base, uno, None)
            ok(v['vs_linea_base']['resumen']['entran'] == 1 and next(f for f in v['filas'] if f['clave'] == 'sucop:2')['novedad'] == 'agregada', 'la vista marca lo agregado')
            tres = foto(capturado='2026-11-03T06:00:00-05:00', minx='no_leida')
            v2 = H.armar_vista(tres, 'n3', base, dos, v)
            ok(len(v2['filas']) == 2 and all(f.get('conservada') for f in v2['filas']), 'sitio caído: la vista conserva sus filas, marcadas')
            (H.FOTOS / n1).chmod(0o644)
            (H.FOTOS / n1).write_text('{}')
            try:
                H.cargar_base()
                ok(False, 'una línea base alterada debe detectarse')
            except RuntimeError:
                ok(True, 'si alguien altera la línea base, se detecta')
            ok(n0 < n1 < n2, 'los nombres ordenan por fecha')
        finally:
            H.FOTOS, H.BASE, H.VISTA = viejos


if __name__ == '__main__':
    prueba_comparacion()
    prueba_guarda()
    prueba_libro()
    prueba_desde_archivo()
    prueba_fotos()
    print(f'\n{len(FALLAS)} fallas' if FALLAS else '\ntodo bien')
    sys.exit(1 if FALLAS else 0)
