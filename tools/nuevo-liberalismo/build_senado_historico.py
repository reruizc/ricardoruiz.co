#!/usr/bin/env python3
"""Senado 2014 · 2018 · 2022 · 2026 — votos por partido encadenados en LINAJES.

Entrada (oficial, ya validada contra el escrutinio):
  Bases de datos/output_congreso_escr/senado-{2014,2018,2022}/resumen.json
  Bases de datos/nuevo-liberalismo/senado-2026-resumen.json   (S3 · ajustado con el E-26 del CNE)
Salida: Propuestas/nuevo-liberalismo/datos/senado-historico.json

⚠️ Los vínculos entre elecciones son LINAJE DE PARTIDO (quién sucede a quién), no trasvase de
votantes: no hay datos individuales. Cuando varios partidos se funden en uno, el nodo destino se
reparte entre sus antecedentes en proporción a los votos que ellos sacaron antes (aritmética).
"""
import json, os, re, sys
RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
BD = os.path.join(RAIZ, 'Bases de datos')
OUT = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos')
os.makedirs(OUT, exist_ok=True)

FUENTE = {
    2014: os.path.join(BD, 'output_congreso_escr', 'senado-2014', 'resumen.json'),
    2018: os.path.join(BD, 'output_congreso_escr', 'senado-2018', 'resumen.json'),
    2022: os.path.join(BD, 'output_congreso_escr', 'senado-2022', 'resumen.json'),
    2026: os.path.join(BD, 'nuevo-liberalismo', 'senado-2026-resumen.json'),
}

# linaje -> {año: (nombre mostrado, regex sobre el nombre oficial de la lista)}
# La llave de color es la de NL.PARTIDOS en base.js.
L = {
    'pacto': dict(color='pacto', familia='izquierda', y={
        2022: ('Pacto Histórico', r'^PACTO HIST'),
        2026: ('Pacto Histórico', r'^PACTO HIST')}),
    'polo': dict(color='polo', familia='izquierda', y={
        2014: ('Polo Democrático', r'POLO DEMOCRATICO'),
        2018: ('Polo Democrático', r'POLO DEMOCR')}),
    'decencia': dict(color='up', familia='izquierda', y={
        2018: ('Lista de la Decencia (ASI, UP, MAIS)', r'LISTA DE LA DECENCIA')}),
    'verde': dict(color='verde', familia='centro', y={
        2014: ('Alianza Verde', r'^PARTIDO ALIANZA VERDE'),
        2018: ('Alianza Verde', r'^PARTIDO ALIANZA VERDE'),
        2022: ('Alianza Verde + Centro Esperanza', r'ALIANZA VERDE Y CENTRO ESPERANZA'),
        2026: ('Alianza por Colombia (Verde, En Marcha y aliados)', r'^ALIANZA POR COLOMBIA')}),
    'liberal': dict(color='liberal', familia='centro', y={
        y: ('Partido Liberal', r'LIBERAL COLOMBIANO') for y in (2014, 2018, 2022, 2026)}),
    'u': dict(color='u', familia='derecha', y={
        2014: ('Partido de la U', r'^PARTIDO DE LA U'),
        2018: ('Partido de la U', r'PARTIDO DE LA U'),
        2022: ('Partido de la U', r'PARTIDO DE LA U'),
        2026: ('Partido de la U', r'PARTIDO DE LA U')}),
    'conservador': dict(color='conservador', familia='derecha', y={
        y: ('Partido Conservador', r'CONSERVADOR COLOMBIANO') for y in (2014, 2018, 2022, 2026)}),
    'cd': dict(color='cd', familia='derecha', y={
        2014: ('Centro Democrático', r'CENTRO DEMOCR'),
        2018: ('Centro Democrático', r'CENTRO DEMOCR'),
        2022: ('Centro Democrático', r'CENTRO DEMOCR'),
        2026: ('Centro Democrático', r'CENTRO DEMOCR')}),
    'cr': dict(color='cr', familia='derecha', y={
        2014: ('Cambio Radical', r'CAMBIO RADICAL'),
        2018: ('Cambio Radical', r'CAMBIO RADICAL'),
        2022: ('Cambio Radical', r'CAMBIO RADICAL'),
        2026: ('Cambio Radical (coalición con ALMA)', r'CAMBIO RADICAL')}),
    'mira': dict(color='mira', familia='cristiana', y={
        2014: ('MIRA', r'MIRA'),
        2018: ('MIRA', r'PARTIDO POL.TICO MIRA'),
        2022: ('MIRA + Colombia Justa Libres', r'MIRA\s*-\s*COLOMBIA JUSTA')}),
    'cjl': dict(color='justa', familia='cristiana', y={
        2018: ('Colombia Justa Libres', r'COLOMBIA JUSTA LIBRES')}),
    'nl': dict(color='nl', familia='centro', y={
        2022: ('Nuevo Liberalismo', r'NUEVO LIBERALISMO')}),
    'ahora': dict(color='ahora', familia='centro', y={
        2026: ('Ahora Colombia (MIRA, Nuevo Liberalismo y Dignidad)', r'^AHORA COLOMBIA')}),
    'opcion': dict(color='asi', familia='otros', y={
        2014: ('Opción Ciudadana', r'OPCION CIUDADANA'),
        2018: ('Opción Ciudadana', r'OPCI.N CIUDADANA')}),
    'fuerza': dict(color='fuerza', familia='centro', y={
        2022: ('Fuerza Ciudadana', r'FUERZA CIUDADANA'),
        2026: ('Fuerza Ciudadana (coalición)', r'FUERZA CIUDADANA')}),
    'salvacion': dict(color='salvacion', familia='derecha', y={
        2022: ('Salvación Nacional', r'SALVACI.N NACIONAL'),
        2026: ('Salvación Nacional', r'SALVACI.N NACIONAL')}),
    'frente': dict(color='frente', familia='izquierda', y={
        2026: ('Frente Amplio Unitario', r'FRENTE AMPLIO UNITARIO')}),
    'creemos': dict(color='creemos', familia='derecha', y={
        2026: ('Creemos', r'^CREEMOS')}),
    'oviedo': dict(color='miradig', familia='centro', y={
        2026: ('Lista de Oviedo', r'LISTA DE OVIEDO')}),
}
# Sucesiones (de linaje a linaje, entre años consecutivos). Todo lo que no aparezca aquí y exista en
# ambos años con el mismo linaje se encadena solo; esto añade fusiones y escisiones.
SUCESION = {
    (2018, 2022): [('polo', 'pacto'), ('decencia', 'pacto'), ('mira', 'mira'), ('cjl', 'mira')],
    (2022, 2026): [('mira', 'ahora'), ('nl', 'ahora')],
}
NOTAS = {
    'pacto': 'El Pacto Histórico nace en 2022 (Colombia Humana, UP, Polo y otros). Sus antecedentes aquí son el Polo y la Lista de la Decencia de 2018; el salto de 2022 es mucho mayor que la suma de los dos.',
    'verde': 'En 2022 va en coalición con Centro Esperanza; en 2026, como Alianza por Colombia con En Marcha, Colombia Renaciente, ASI y Demócrata.',
    'ahora': 'En 2026 el Nuevo Liberalismo va en la lista Ahora Colombia con MIRA y Dignidad y Compromiso. El voto del Senado no se puede separar por partido: es una sola lista.',
    'nl': 'En 2022 el Nuevo Liberalismo fue solo y no alcanzó el umbral (368.345 votos, ninguna curul).',
    'mira': 'En 2018 MIRA y Colombia Justa Libres compiten separados; en 2022 van en una sola coalición.',
    'opcion': 'No pasó el umbral en 2018 y no vuelve a aparecer con lista al Senado en 2022 ni 2026.',
}

def carga(y):
    d = json.load(open(FUENTE[y]))
    return d, d['partidos']

cols = []
for y in (2014, 2018, 2022, 2026):
    d, ps = carga(y)
    votval = d['votval']
    usados = set(); nodos = []
    for lid, cfg in L.items():
        if y not in cfg['y']: continue
        nombre, rx = cfg['y'][y]
        hit = [p for i, p in enumerate(ps) if i not in usados and re.search(rx, p['partido'].upper() if lid != 'x' else p['partido'])]
        # una regex puede casar listas ajenas (p. ej. 'MIRA' dentro de otra); pedimos coincidencia única salvo excepciones declaradas
        if not hit:
            print(f'⚠ {y}: sin lista para {lid} ({rx})', file=sys.stderr); continue
        for p in hit: usados.add(ps.index(p))
        nodos.append({'id': f'{lid}-{y}', 'linaje': lid, 'nombre': nombre, 'color': cfg['color'], 'familia': cfg['familia'],
                      'votos': sum(p['votos'] for p in hit), 'curules': sum(p.get('curules', 0) for p in hit),
                      'listas': [p['partido'] for p in hit]})
    resto = [p for i, p in enumerate(ps) if i not in usados]
    otros_v = sum(p['votos'] for p in resto)
    nodos.append({'id': f'otros-{y}', 'linaje': 'otros', 'nombre': 'Otros partidos y listas', 'color': 'otros', 'familia': 'otros',
                  'votos': otros_v, 'curules': sum(p.get('curules', 0) for p in resto), 'listas': [p['partido'] for p in resto]})
    tot = sum(n['votos'] for n in nodos)
    assert abs(tot - sum(p['votos'] for p in ps)) < 2, (y, tot)
    cols.append({'anio': y, 'votos_listas': tot, 'votval': votval, 'blanco': d['votblan'], 'nulos': d['votnul'], 'no_marcados': d['votnma'],
                 'votantes': d['votant'], 'umbral': d['umbral'], 'cifra': d['cifra'], 'nodos': nodos,
                 'curules': sum(n['curules'] for n in nodos)})
    print(y, 'listas', tot, 'votval', votval, 'curules', cols[-1]['curules'], file=sys.stderr)

idx = {n['id']: n for c in cols for n in c['nodos']}
enlaces = []
for a, b in zip(cols, cols[1:]):
    ya, yb = a['anio'], b['anio']
    pares = set(SUCESION.get((ya, yb), []))
    for n in a['nodos']:
        if n['linaje'] == 'otros': continue
        if f"{n['linaje']}-{yb}" in idx: pares.add((n['linaje'], n['linaje']))
    # fuente por destino -> reparto proporcional a los votos de los antecedentes
    destinos = {}
    for (s, t) in pares:
        sid, tid = f'{s}-{ya}', f'{t}-{yb}'
        if sid in idx and tid in idx: destinos.setdefault(tid, []).append(sid)
    for tid, srcs in destinos.items():
        tv = sum(idx[s]['votos'] for s in srcs)
        for s in srcs:
            enlaces.append({'de': s, 'a': tid, 'peso_origen': 1.0, 'peso_destino': round(idx[s]['votos'] / tv, 6),
                            'tipo': 'continuidad' if len(srcs) == 1 else 'fusion'})
    # "otros" encadena con "otros"
    enlaces.append({'de': f'otros-{ya}', 'a': f'otros-{yb}', 'peso_origen': 1.0, 'peso_destino': 1.0, 'tipo': 'continuidad'})

# marcas útiles para el frontend
for c in cols:
    for n in c['nodos']:
        n['pct'] = round(n['votos'] / c['votos_listas'], 5)
        n['antecedentes'] = [e['de'] for e in enlaces if e['a'] == n['id']]
        n['nota'] = NOTAS.get(n['linaje']) if n['linaje'] in NOTAS else None
        n['nuevo'] = (c['anio'] != 2014 and not n['antecedentes'] and n['linaje'] != 'otros')

salida = {'v': '2026-11-09', 'columnas': cols, 'enlaces': enlaces,
          'fuente': 'Registraduría · escrutinio consolidado (GCS) 2014, 2018, 2022; 2026 con el E-26 del CNE (Res. E-3328 de 2026).',
          'aviso': 'Los vínculos son linaje de partido, no trasvase de votantes. Las curules incluyen la circunscripción indígena.'}
json.dump(salida, open(os.path.join(OUT, 'senado-historico.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('enlaces', len(enlaces), '· bytes', os.path.getsize(os.path.join(OUT, 'senado-historico.json')), file=sys.stderr)
for c in cols:
    print(f"\n{c['anio']}: listas {c['votos_listas']:,} · curules {c['curules']}")
    for n in sorted(c['nodos'], key=lambda x: -x['votos']):
        print(f"   {n['votos']:>10,} {100 * n['pct']:5.1f}%  {n['curules']:>2}  {n['nombre']}" + ('   ← nuevo' if n['nuevo'] else '') + f"   [{', '.join(n['antecedentes'])}]")
