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

# Colores validados con el validador de paleta (dataviz): Alcaldía pasa todos
# los pares; Concejo pasa visión normal y queda en 6,9 de separación para
# daltonismo, legal con apoyo (leyenda, nombre al pasar el cursor, ficha).
COLOR = {
    'figuras': '#2a78d6', 'nombre': '#eda100', 'partido': '#4a3aa7',
    'gestion': '#e34948', 'poco-voto': '#008300', 'movilizada': '#1baf7a',
    'estrategico': '#2a78d6', 'tradicional': '#eda100', 'alineada': '#4a3aa7',
    'decide': '#e87ba4', 'cruce-sur': '#008300',
}

TEXTOS = {
    'nombre': dict(
        lema='Vota a nombres conocidos dentro del electorado de su partido.',
        decide='Elige el partido de siempre y, dentro de la lista, el nombre que más ha visto. Es el voto con menos base propia de la ciudad: aquí casi nadie tiene el barrio amarrado.',
        oficio='La pelea es con los compañeros de lista y la gana el nombre más visible: recordación, medios y redes pesan más que la estructura de barrio.'),
    'partido': dict(
        lema='Se vota la lista, no la persona.',
        decide='El voto a listas cerradas más alto de la ciudad y el electorado más joven. Decide por el partido y su bandera; el nombre del candidato pesa poco.',
        oficio='Con lista abierta, el trabajo es que marquen el número además del logo; con lista cerrada, que salgan a votar. Uno de cada doce tarjetones al Concejo se pierde nulo o sin marcar: la pedagogía del tarjetón rinde.'),
    'figuras': dict(
        lema='Vota nombres conocidos de toda la ciudad y casi no pierde voto.',
        decide='Participa más que el promedio y casi no anula ni deja el tarjetón sin marcar. Se inclina a la derecha más que la ciudad. Su base propia es de redes personales de figuras conocidas, no de gestión de barrio.',
        oficio='Opinión: medios, redes, debate y reconocimiento del nombre. Es un electorado que compara.'),
    'gestion': dict(
        lema='Una parte grande del voto va a quien se conoce en la zona.',
        decide='La base propia más alta de la ciudad, el mayor voto a concejales en ejercicio y un candidato que se lleva una tajada grande del barrio. Se vota a la persona que está, que resuelve, que se conoce.',
        oficio='Es territorio ocupado: el voto de base propia es sobre todo de quien ya lo tiene, y se mantiene entre elecciones. Para una candidatura nueva la entrada es la alianza o el endoso más que la competencia de frente; para quien ya tiene base, cuidarla.'),
    'poco-voto': dict(
        lema='Participa poco, y lo local la moviliza menos que lo nacional.',
        decide='La participación más baja de la ciudad y donde más tarjetones al Concejo salen nulos o sin marcar; cuando vota, más que en otros lados marca solo el logo.',
        oficio='El voto está en movilizar: transporte, acompañamiento y explicar cómo se marca el tarjetón. Es donde más rinde el día de la elección.'),
    'movilizada': dict(
        lema='Sale a votar lo local más que cualquier otro barrio.',
        decide='Conjuntos y ciudadelas de clase media con la participación más alta de la ciudad, y que votan lo local relativamente más que lo nacional. Su voto a la Alcaldía es de los más movedizos.',
        oficio='Electorado que sí vota en lo local y compara propuestas: propuestas concretas de ciudad y de barrio.'),
    'estrategico': dict(
        lema='Concentra el voto en el favorito aunque al Concejo vote otra cosa.',
        decide='La contienda más concentrada de la ciudad. Al Concejo vota a la derecha más que nadie y a la Alcaldía se va con quien puede ganar: vota útil.',
        oficio='Pesa parecer el ganador viable: encuestas, respaldos y la sensación de que el voto no se pierde.'),
    'decide': dict(
        lema='Alta participación y voto que se mueve: aquí se gana la Alcaldía.',
        decide='El voto más movedizo de la ciudad entre 2019 y 2023, y donde el candidato sin partido sacó su mejor resultado. Participa más que el promedio y vota lo local.',
        oficio='Cabe el candidato sin partido. Se convence con propuesta y con la persona, y no se queda con el de la vez pasada.'),
    'cruce-sur': dict(
        lema='Al Concejo vota a las candidaturas de su barrio; a la Alcaldía, a otra cosa.',
        decide='Participación baja. El voto al Concejo va más que en la ciudad a candidaturas de centro con base en el barrio, y el de la Alcaldía a candidatos de opinión. El candidato sin partido sacó aquí su peor resultado.',
        oficio='El concejal o el edil del barrio no trae el voto de la Alcaldía: cada tarjetón se gana por aparte. Movilizar pesa, porque la participación es baja.'),
    'alineada': dict(
        lema='Vota a la Alcaldía como vota al Concejo.',
        decide='El voto cruzado más bajo de la ciudad: la misma familia política en los dos tarjetones. Es la contienda más repartida y el electorado más joven.',
        oficio='Voto de bloque: lo mueven la identidad política y la coherencia entre el candidato y su lista.'),
    'tradicional': dict(
        lema='Estable, con mayoría holgada al ganador.',
        decide='Participación media, poca volatilidad y mayoría clara al favorito. Su electorado es algo mayor que el promedio.',
        oficio='Valora la continuidad y la gestión que se ve; el cambio brusco le cuesta.'),
}

# Lo que el texto de cada arquetipo afirma y no siempre está entre las
# variables que lo definen: se muestra igual, para que se vea medido.
RASGO_EXTRA = {
    'gestion': ['in', 't1'], 'cruce-sur': ['cr'], 'decide': ['vo'], 'estrategico': ['cr', 'der'],
    'alineada': ['j'], 'partido': ['j'], 'tradicional': ['my'], 'figuras': ['der'], 'poco-voto': ['ml'],
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
                **TEXTOS[s],
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
    pub = {
        'v': arq['v'], 'naturaleza': 'lectura observada 2023', 'cortes': list(CORP), 'corporacion': CORP,
        'fuente': arq['fuente'], 'familias': familias, 'orden': orden, 'share': share, 'ciudad': ciudad,
        'variables': {VAR[v][0]: {'t': VAR[v][1], 'f': VAR[v][2]} for v in VAR},
        'metodo': {corp: {k: C['meta'][k] for k in ('silueta', 'barrios', 'nitidos', 'frontera')} for corp, C in arq['corporaciones'].items()},
        'barrios': barrios,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'arquetipos-bogota.json').write_text(json.dumps(pub, ensure_ascii=False, separators=(',', ':')))

    g = gpd.read_file(BD / 'output_pacto_1v_2026' / 'geo' / 'BOG-BARRIOS-CATASTRALES.json')
    g = g[g['loc_codigo'] != '20'].copy()
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
