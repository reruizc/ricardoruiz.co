#!/usr/bin/env python3
"""Arma los dos archivos que lee el panel 05 de Candidato 360 para Bogotá.

    python3 tools/candidato-360/arquetipos-bogota/publicar.py

Lee arquetipos-bogota.json (de arquetipos.py) y emite en
Bases de datos/arquetipos-bogota/publicar/:

  arquetipos-bogota.json   familias (nombre, color, lectura, rasgos medidos),
                           orden por corporación, promedio de la ciudad y, por
                           barrio, arquetipo dominante + mezcla + confianza en
                           Concejo y en Alcaldía, más sus variables.
  barrios-bogota.json      la cartografía catastral SIMPLIFICADA (~4 m) con
                           `codigo`, `nombre`, `loc`: el mapa del panel no
                           necesita los 6,5 MB del catastral completo.

Subir (comprimidos; el navegador los descomprime solo):
    gzip -9 -c X.json > X.json.gz
    aws s3 cp X.json.gz s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/arquetipos-bogota/X.json \
      --content-type application/json --content-encoding gzip --cache-control "public, max-age=3600"

Los textos de cada arquetipo viven acá (TEXTOS). «decide» describe lo
MEDIDO; «oficio» es criterio de campaña y el panel lo rotula así.
"""
import json
from pathlib import Path

import geopandas as gpd

RAIZ = Path(__file__).resolve().parents[3]
BD = RAIZ / 'Bases de datos'
DIR = BD / 'arquetipos-bogota'
OUT = DIR / 'publicar'

CORP = {'concejo': 'Concejo', 'alcaldia': 'Alcaldía'}

# v1 (oct-19-2026): 8 arquetipos por corporación. Los 6+5 de la v0 conservan
# su color; los nuevos toman tonos que no chocan con sus vecinos de mapa.
COLOR = {
    # Concejo
    'figuras': '#2a78d6', 'opinion': '#0e7490', 'nombre': '#eda100', 'sin-dueno': '#c026d3',
    'partido': '#4a3aa7', 'gestion': '#e34948', 'poco-voto': '#008300', 'movilizada': '#1baf7a',
    # Alcaldía
    'estrategico': '#2a78d6', 'alternativa': '#0e7490', 'tradicional': '#eda100', 'media-alineada': '#c026d3',
    'alineada': '#4a3aa7', 'decide': '#e87ba4', 'cruce-sur': '#008300', 'reparte': '#9a3412',
}

# Los textos van en lenguaje de campaña, para un político y no para un
# analista (pedido de Ricardo, oct-19-2026):
#   lema   · una frase que se recuerda
#   quien  · quién vive y vota ahí
#   decide · cómo vota (lo MEDIDO, dicho simple)
#   oficio · cómo ganárselo (criterio de oficio, el panel lo rotula así)
TEXTOS = {
    # ── Concejo ──
    'nombre': dict(
        lema='Vota por el nombre que más ha oído.',
        quien='Barrios de clase media de estrato 3, el grueso de Bogotá: Engativá, Kennedy, Suba, Fontibón.',
        decide='Escoge el partido de siempre y, dentro de la lista, al candidato que más le suena. Casi nadie tiene el barrio amarrado.',
        oficio='Hágase conocer: aquí gana el nombre que más se ve. Su pelea es con los compañeros de su propia lista.'),
    'sin-dueno': dict(
        lema='Vota mucho y nadie lo tiene amarrado.',
        quien='Clase media que sale a votar más que el promedio de la ciudad.',
        decide='Participa más que casi todos, pero no le debe el voto a ningún concejal del barrio: es el voto más libre de Bogotá.',
        oficio='Es el voto que está en juego. Llegue con propuestas claras y hágase conocer antes que los demás.'),
    'partido': dict(
        lema='Vota por el partido, no por la persona.',
        quien='Barrios populares de estrato 2 con mucha gente joven: Bosa, Kennedy, Ciudad Bolívar, Suba.',
        decide='Marca el logo de su partido y el nombre del candidato le pesa poco. Es donde más se vota por listas cerradas.',
        oficio='Si su lista es abierta, enséñele a marcar su número además del logo. Uno de cada doce tarjetones se pierde nulo o sin marcar.'),
    'opinion': dict(
        lema='Se decide por lo que opina, no por quién lo visita.',
        quien='Barrios de estrato alto que votan mucho: Usaquén, Chapinero, Teusaquillo, el norte de Suba.',
        decide='Casi no vota listas cerradas ni pierde votos. Elige al candidato por sus posiciones y por lo que ve en medios y redes.',
        oficio='Tome posición clara en los temas de ciudad y aparezca en medios. Aquí no se gana puerta a puerta.'),
    'poco-voto': dict(
        lema='Vota poco, y cuando vota, a veces se le pierde el voto.',
        quien='Barrios populares de estrato 1 y 2: Ciudad Bolívar, Usme, Kennedy, San Cristóbal.',
        decide='Es el que menos sale a votar al Concejo; sale más para la Presidencia. Muchos tarjetones quedan nulos o sin marcar.',
        oficio='Aquí no hay que convencer, hay que movilizar: transporte, acompañamiento y explicar cómo se marca el tarjetón.'),
    'figuras': dict(
        lema='Vota por figuras conocidas y casi nunca pierde el voto.',
        quien='Los barrios más ricos de la ciudad, estrato 5 y 6.',
        decide='Vota más a la derecha que la ciudad y casi no anula. Sigue a figuras conocidas que tienen redes propias en la zona.',
        oficio='Pesa el reconocimiento y quién lo respalda. Una figura conocida a su lado abre más puertas que un volante.'),
    'gestion': dict(
        lema='Vota por quien le resolvió algo.',
        quien='Barrios tradicionales del centro y el sur oriente: San Cristóbal, Rafael Uribe, Santa Fe, Los Mártires.',
        decide='Es el barrio con más voto propio de los concejales: se vota a la persona que conoce, que está y que resuelve.',
        oficio='Ya tiene dueño. Si usted es ese dueño, cuídelo; si no, entre de la mano de un aliado del barrio, no de frente.'),
    'movilizada': dict(
        lema='Sale a votar por lo de su barrio.',
        quien='Conjuntos y ciudadelas de clase media: Ciudad Salitre, Muzú, Puente Aranda, Tibabuyes.',
        decide='Es el que más vota de la ciudad y el que más se moviliza por lo local. Compara propuestas antes de decidir.',
        oficio='Llegue con propuestas concretas para su conjunto y su sector, y rinda cuentas de lo que hizo.'),
    # ── Alcaldía ──
    'estrategico': dict(
        lema='Vota por el que puede ganar.',
        quien='Los barrios más ricos de la ciudad, estrato 5 y 6.',
        decide='Concentra el voto en el favorito aunque al Concejo vote distinto: no quiere botar el voto.',
        oficio='Hay que parecer el ganador: encuestas, respaldos y la sensación de que el voto no se pierde.'),
    'alternativa': dict(
        lema='Busca una opción distinta a las de siempre.',
        quien='Barrios de estrato 4 que votan mucho.',
        decide='Vota mucho y fue donde mejor le fue al candidato sin partido en 2023. Se fija en la persona más que en la etiqueta.',
        oficio='Cabe el candidato nuevo o independiente, si se muestra preparado y sin padrinos.'),
    'decide': dict(
        lema='Aquí se gana la Alcaldía.',
        quien='Clase media que vota mucho: Engativá, Kennedy, Fontibón.',
        decide='Es el voto que más se mueve: fue de Claudia López en 2019 y en 2023 se partió entre Galán y Oviedo.',
        oficio='No se queda con el de la vez pasada. Se convence con propuesta y con la persona.'),
    'tradicional': dict(
        lema='Vota estable y por el favorito.',
        quien='Clase media de estrato 3, con un electorado algo mayor que el promedio.',
        decide='Cambia poco de una elección a otra y le da una mayoría clara al ganador.',
        oficio='Valora la continuidad y lo que se ve hecho. El cambio brusco le cuesta.'),
    'media-alineada': dict(
        lema='Vota igual a la Alcaldía y al Concejo.',
        quien='Clase media de estrato 2 y 3.',
        decide='Elige la misma línea política en los dos tarjetones y reparte su voto entre varios candidatos.',
        oficio='Lo mueve la coherencia: que el candidato a la Alcaldía y su lista al Concejo digan lo mismo.'),
    'alineada': dict(
        lema='Vota por su bando en los dos tarjetones.',
        quien='Barrios populares con mucha gente joven: Bosa, Kennedy, Usme.',
        decide='Vota a la Alcaldía como vota al Concejo, más a la izquierda que la ciudad, y en una contienda muy repartida.',
        oficio='Voto de identidad política: se le habla desde su lado y con coherencia entre candidato y lista.'),
    'reparte': dict(
        lema='Vota distinto en cada tarjetón.',
        quien='Barrios populares de estrato 2.',
        decide='Al Concejo vota por unos y a la Alcaldía por otros, sin irse a ningún extremo.',
        oficio='El concejal del barrio no le trae el voto de la Alcaldía, ni al revés: cada tarjetón se gana por aparte.'),
    'cruce-sur': dict(
        lema='Vota al conocido para el Concejo y a otro para la Alcaldía.',
        quien='Barrios populares de estrato 1 del sur: Ciudad Bolívar, Usme, San Cristóbal.',
        decide='Vota poco. Al Concejo, a los candidatos de su barrio; a la Alcaldía, a otra cosa. El candidato sin partido sacó aquí su peor resultado.',
        oficio='Hay que movilizar, porque sale poco a votar, y ganarse cada tarjetón por separado.'),
}

# Sensibilidad por tema (1-5) para el simulador. ⚠️ HEURÍSTICA DEL EQUIPO: en
# Bogotá no hay estudio emocional (en Medellín y Cartagena sí). Sale de leer
# lo medido de cada arquetipo (estrato, participación, voto por persona o por
# partido, ideología) y el panel lo dice. Temas = llaves de PALANCAS en
# candidato-360-arq-modos.js.
TEMAS = ['seguridad', 'empleo', 'servicios', 'movilidad', 'vivienda', 'corrupcion', 'ambiente', 'salud_educacion', 'participacion', 'cultura']
SENS = {
    'nombre':         [4, 3, 3, 4, 2, 3, 2, 3, 2, 2],
    'sin-dueno':      [4, 3, 3, 5, 2, 4, 3, 4, 3, 2],
    'partido':        [3, 5, 4, 4, 4, 3, 3, 4, 3, 4],
    'opinion':        [4, 2, 2, 4, 2, 5, 4, 3, 2, 2],
    'poco-voto':      [4, 5, 5, 3, 4, 2, 4, 4, 4, 3],
    'figuras':        [5, 2, 1, 3, 2, 4, 3, 2, 1, 2],
    'gestion':        [4, 3, 4, 3, 4, 2, 3, 3, 5, 4],
    'movilizada':     [4, 3, 3, 4, 3, 4, 3, 4, 4, 3],
    'estrategico':    [5, 2, 1, 4, 2, 4, 3, 2, 1, 2],
    'alternativa':    [4, 2, 2, 4, 2, 5, 4, 3, 2, 2],
    'decide':         [4, 3, 3, 5, 2, 4, 3, 4, 3, 2],
    'tradicional':    [4, 3, 3, 3, 2, 3, 2, 3, 2, 2],
    'media-alineada': [3, 4, 3, 4, 3, 3, 3, 4, 3, 3],
    'reparte':        [4, 4, 4, 3, 3, 2, 3, 3, 4, 3],
    'alineada':       [3, 5, 4, 4, 4, 3, 3, 5, 3, 4],
    'cruce-sur':      [4, 5, 5, 3, 4, 2, 4, 4, 4, 3],
}
# Los barrios sin puesto de votación propio toman el arquetipo del barrio con
# dato más cercano (centroide), hasta esta distancia. No suman a nada.
RELLENO_MAX_KM = 2.0
# Imagen de cada arquetipo (la dibuja quien hace lo gráfico, §10 de
# candidato-360.md). Si no existe, el panel la omite.
IMAGEN = 'assets/candidato-360/arquetipos-bogota/{}.webp'

# Lo que el texto de cada arquetipo afirma y no siempre está entre las
# variables que lo definen: se muestra igual, para que se vea medido.
RASGO_EXTRA = {
    'gestion': ['in', 't1'], 'cruce-sur': ['cr'], 'decide': ['vo'], 'estrategico': ['cr', 'der'],
    'alineada': ['j'], 'partido': ['j'], 'tradicional': ['my'], 'figuras': ['der'], 'poco-voto': ['ml'],
    'opinion': ['der'], 'sin-dueno': ['p'], 'alternativa': ['ov'], 'reparte': ['cr'], 'media-alineada': ['cr'],
}

# Cómo se muestra cada variable: llave corta, etiqueta y formato.
VAR = {
    'estrato': ('e', 'Estrato medio', 'dec'), 'part23': ('p', 'Participación 2023', 'pct'),
    'mov_local': ('ml', 'Movilización local frente a la nacional', 'idx'),
    'cerrada': ('ce', 'Voto a listas cerradas', 'pct'), 'logo_abierta': ('la', 'Voto al logo en listas abiertas', 'pct'),
    'arraigo': ('ar', 'Voto con base propia', 'pct'), 'desafeccion': ('de', 'Blanco, nulo y sin marcar', 'pct'),
    'cruzado': ('cr', 'Voto cruzado Alcaldía–Concejo', 'pct'), 'alc_oviedo': ('ov', 'Voto a Oviedo (sin lista al Concejo)', 'pct'),
    'nec_alc': ('na', 'Candidatos efectivos a la Alcaldía', 'dec'), 'blanco_alc': ('ba', 'Voto en blanco a la Alcaldía', 'pct'),
    'alc_bolivar': ('bo', 'Voto a Bolívar', 'pct'),
    # solo descriptivas (no definen el arquetipo)
    'incumbente': ('in', 'Voto a concejales en ejercicio', 'pct'), 'top1_cand': ('t1', 'El candidato más votado del barrio', 'pct'),
    'alc_galan': ('ga', 'Voto a Galán', 'pct'), 'vol_alc_19_23': ('vo', 'Cambio de voto a la Alcaldía 2019–2023', 'pct'),
    'vol_19_23': ('vc', 'Cambio de voto al Concejo 2019–2023', 'pct'),
    'conc_izq': ('iz', 'Concejo · izquierda', 'pct'), 'conc_d': ('der', 'Concejo · derecha', 'pct'),
    'joven': ('j', 'Censo de 18 a 30 años', 'pct'), 'mayor': ('my', 'Censo de 61 años o más', 'pct'),
}


def perfil(B, corp, s):
    """Todas las variables del arquetipo (promedio de sus barrios, ponderado por
    votantes), para poder decir «46 % contra 55 % de la ciudad»."""
    out = {}
    for v, (k, _, _) in VAR.items():
        num = den = 0.0
        for b in B.values():
            if b.get(corp, {}).get('dom') != s:
                continue
            x, w = (b['vars'].get(v) if v != 'estrato' else b.get('estrato')), b['vars']['votantes23'] or 0
            if x is None or not w:
                continue
            num += x * w
            den += w
        out[k] = round(num / den, 4) if den else None
    return out


def main():
    arq = json.loads((DIR / 'arquetipos-bogota.json').read_text())
    B = arq['barrios']
    # promedio de la ciudad, ponderado por votantes
    ciudad = {}
    for v in VAR:
        num = den = 0.0
        for b in B.values():
            x, w = (b['vars'].get(v) if v != 'estrato' else b.get('estrato')), b['vars']['votantes23'] or 0
            if x is None or not w:
                continue
            num += x * w
            den += w
        ciudad[VAR[v][0]] = round(num / den, 4) if den else None
    familias, orden, share = {}, {}, {}
    for corp, C in arq['corporaciones'].items():
        meta = C['meta']
        orden[corp] = sorted(C['arquetipos'], key=lambda s: -C['arquetipos'][s]['votantes'])
        tot = sum(a['votantes'] for a in C['arquetipos'].values())
        share[corp] = {s: round(a['votantes'] / tot, 4) for s, a in C['arquetipos'].items()}
        for s, a in C['arquetipos'].items():
            # rasgos: las variables que más lo separan de la ciudad (|z|)
            # (al menos dos, y solo las que se apartan de verdad: |z| ≥ 0,35)
            z = sorted(meta['vars'], key=lambda v: -abs(a['z'][v]))
            z = [v for v in z if abs(a['z'][v]) >= .35][:4] or z[:2]
            if len(z) < 2:
                z = sorted(meta['vars'], key=lambda v: -abs(a['z'][v]))[:2]
            familias[s] = {
                'corp': corp, 'nombre': a['nombre'], 'color': COLOR[s], 'barrios': a['barrios'], 'votantes': a['votantes'],
                **TEXTOS[s], 'imagen': IMAGEN.format(s),
                'sens': dict(zip(TEMAS, SENS[s])), 'sens_heuristica': True,
                # llaves; el valor sale de `perfil` y se compara con `ciudad`
                'rasgos': [VAR[v][0] for v in z] + [k for k in RASGO_EXTRA.get(s, []) if k not in [VAR[v][0] for v in z]],
                'ejemplos': a['ejemplos'][:6],
                'perfil': perfil(B, corp, s),
            }
    barrios = {}
    for cod, b in B.items():
        if 'concejo' not in b and 'alcaldia' not in b:
            continue
        x = {VAR[v][0]: (round(b['vars'][v], 4) if b['vars'].get(v) is not None else None) for v in VAR if v != 'estrato'}
        out = {'n': b['nombre'], 'l': b['localidad'], 'e': b.get('estrato'), 'w': int(b['vars']['votantes23'] or 0), 'x': x}
        for corp in CORP:
            if corp in b:
                c = b[corp]
                out[corp[0]] = {'d': c['dom'], 'k': c['conf'], 'm': {i: p for i, p in c['mez'].items() if p >= .01}}
        barrios[cod] = out
    # ── Relleno de vecino: los barrios sin puesto de votación propio toman el
    # arquetipo del barrio con dato más cercano. Van marcados (`r`), con peso
    # 0: se pintan, no suman a ningún total ni entran a ninguna tabla.
    g = gpd.read_file(BD / 'output_pacto_1v_2026' / 'geo' / 'BOG-BARRIOS-CATASTRALES.json')
    g = g[g['loc_codigo'] != '20'].copy()
    cen = g.to_crs(3116).geometry.centroid
    pos = {str(c): (p.x, p.y) for c, p in zip(g['codigo'], cen)}
    loc_nombre = {}
    for c, l in zip(g['codigo'], g['loc_codigo']):
        if str(c) in barrios:
            loc_nombre.setdefault(l, barrios[str(c)]['l'])
    con = [(c, pos[c]) for c in barrios if c in pos]
    rellenos = 0
    for c, l, nom in zip(g['codigo'], g['loc_codigo'], g['nombre']):
        c = str(c)
        if c in barrios or c not in pos:
            continue
        x0, y0 = pos[c]
        de, d2 = min(((k, (x - x0) ** 2 + (y - y0) ** 2) for k, (x, y) in con), key=lambda z: z[1])
        km = d2 ** .5 / 1000
        if km > RELLENO_MAX_KM:
            continue
        v = barrios[de]
        barrios[c] = {'n': nom, 'l': loc_nombre.get(l, v['l']), 'e': None, 'w': 0, 'x': {},
                      'r': {'de': de, 'km': round(km, 2)}, **{k: v[k] for k in ('c', 'a') if k in v}}
        rellenos += 1
    print('barrios rellenados con su vecino:', rellenos)
    pub = {
        'v': arq['v'], 'naturaleza': 'lectura observada 2023', 'relleno_max_km': RELLENO_MAX_KM, 'cortes': list(CORP), 'corporacion': CORP,
        'fuente': arq['fuente'], 'familias': familias, 'orden': orden, 'share': share, 'ciudad': ciudad,
        'variables': {VAR[v][0]: {'t': VAR[v][1], 'f': VAR[v][2]} for v in VAR},
        'metodo': {corp: {k: C['meta'][k] for k in ('silueta', 'barrios', 'nitidos', 'frontera')} for corp, C in arq['corporaciones'].items()},
        'barrios': barrios,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'arquetipos-bogota.json').write_text(json.dumps(pub, ensure_ascii=False, separators=(',', ':')))

    g['geometry'] = g.geometry.simplify(0.00004, preserve_topology=True)
    g = g.rename(columns={'loc_codigo': 'loc'})[['codigo', 'nombre', 'loc', 'geometry']]
    gj = json.loads(g.to_json(drop_id=True))
    def redondear(c):
        return [round(c[0], 5), round(c[1], 5)] if isinstance(c[0], float) else [redondear(x) for x in c]
    for f in gj['features']:
        f['geometry']['coordinates'] = redondear(f['geometry']['coordinates'])
    (OUT / 'barrios-bogota.json').write_text(json.dumps(gj, ensure_ascii=False, separators=(',', ':')))
    for n in ('arquetipos-bogota.json', 'barrios-bogota.json'):
        print(n, (OUT / n).stat().st_size // 1024, 'KB')
    print('barrios publicados:', len(barrios), '· familias:', len(familias))


if __name__ == '__main__':
    main()
