#!/usr/bin/env python3
"""
Actores curados a mano para el esquema de fuerzas EXTERNAS de la Ley de Rescate
(PL 477 de 2026 Cámara) → mi-congreso-data/fuerzas-externas/C-477-26.json (lo sirve GitHub Pages; la página lo funde encima del JSON automático de S3).

Por qué a mano: el builder automático busca la prensa con las palabras del
título («rescate económico propósito estabilizar finanzas») y trae 2 titulares;
la conversación real de esta ley vive en el seguimiento de ley-de-rescate-avance
(ley-rescate-data/estado.json → `voces`, declaraciones verificadas una por una)
y en notas que leímos para la reunión del 6-nov-2026 con la senadora Villalba.

Dos fuentes:
  · `voces` de estado.json, solo las de FUERA del Congreso (g != 'con'):
    p a → +1 · r → −1 · m → −0,5 (o +0,5 cuando es apoyo con ajustes, lista
    APOYA_CON_AJUSTES) · i → null. El peso es `men` (menciones en el corpus).
  · REGIONALES y otros actores leídos a mano (cita verificada en la nota
    original el 6-nov-2026), con `region` para que Fuerzas los agrupe como
    «en tu territorio» cuando la nota del congresista trae esa región.

`manual: true` en cada actor; el builder los funde encima de lo automático
(mismo nombre normalizado → gana el manual).

  python3 tools/mi-congreso/fuerzas-externas-manual/build_477.py
"""
import json
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ESTADO = REPO / 'ley-rescate-data' / 'estado.json'
OUT = REPO / 'mi-congreso-data' / 'fuerzas-externas' / 'C-477-26.json'


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(s.split())


# voces que NO entran al plano: son internos (congresistas), medios, o personas
# cuya organización ya entra como entidad
FUERA = {'vicky davila', 'jose manuel restrepo', 'miguel gomez martinez', 'presidencia de la republica',
         'ministerio de hacienda', 'juan sebastian betancur', 'efrain cepeda', 'andres julian rendon'}
APOYA_CON_AJUSTES = {'fenalco', 'consejo gremial', 'maria claudia lacouture', 'jose antonio ocampo',
                     'jairo nunez mendez', 'lisandro junco'}
TIPO = {'Gremios': 'gremio', 'Sindicatos': 'organizacion', 'Expertos': 'persona', 'Regiones': 'entidad',
        'Organismos': 'entidad', 'Cajas de compensación': 'gremio', 'Automotor': 'gremio', 'Agro': 'gremio',
        'Industria textil': 'gremio', 'Gobierno': 'entidad', 'Conservador': 'persona', 'Medios': 'persona'}
ORG_TIPO = {'fedesarrollo': 'academia', 'anif': 'academia', 'banco de la republica': 'entidad',
            'fondo monetario internacional': 'entidad', 'asocapitales': 'entidad', 'citi research': 'empresa',
            'corficolombiana': 'empresa', 'camara de comercio electronico': 'gremio'}
SECTOR = {'federacion de cafeteros': 'agro', 'gonzalo moreno': 'agro', 'andres valencia': 'agro', 'fenalco': 'comercio',
          'asocajas': 'cajas de compensacion', 'cgt': 'trabajo', 'fabio arias': 'trabajo', 'pedro nel quijano': 'automotor',
          'asobancaria': 'financiero', 'fecoljuegos': 'juegos de azar', 'guillermo criado': 'textil',
          'camara de comercio electronico': 'comercio digital', 'andi': 'industria', 'consejo gremial': 'gremios'}
# nombre de exhibición cuando la voz es una persona que habla por su gremio
NOMBRE = {'gonzalo moreno': 'Fenavi', 'pedro nel quijano': 'Aconauto', 'guillermo criado': 'Cámara Colombiana de la Confección',
          'maria claudia lacouture': 'AmCham Colombia', 'fabio arias': 'CUT', 'federacion de cafeteros': 'Federación Nacional de Cafeteros',
          'consejo gremial': 'Consejo Gremial Nacional', 'camara de comercio electronico': 'Cámara Colombiana de Comercio Electrónico'}
# a quién lo nombra o le impone algo el texto (cerca 1), con lo que le exige
TEXTO = {
    'asocajas': ('obliga', ['Girar a la ADRES uno de los cuatro puntos de los aportes a las cajas (art. 22)',
                            'Destinar por cinco años los saldos del FOSFEC a sanear pasivos en salud (art. 23)']),
    'asobancaria': ('obliga', ['Cinco puntos adicionales de renta para las entidades financieras hasta 2030 (art. 57)']),
    'federacion de cafeteros': ('nombrado', ['Café en grano sin tostar pasa de excluido a 19 % y el café tostado de 5 % a 19 % desde 2028 (arts. 42, 46 y 106)']),
    'gonzalo moreno': ('nombrado', ['Insumos agropecuarios (abonos, plaguicidas, concentrados) pasan a 19 % desde 2028 (art. 42)']),
    'fecoljuegos': ('obliga', ['Ganancia en loterías, rifas y apuestas pasa a pagar 30 % e IVA a juegos por internet (arts. 41 y 52)']),
    'pedro nel quijano': ('nombrado', ['Híbridos y eléctricos pierden el 5 % desde la vigencia de la ley (art. 106)']),
    'fenalco': ('nombrado', ['Impuesto a bebidas ultraprocesadas rediseñado (art. 56) e IVA a compras de bajo valor en plataformas']),
    'guillermo criado': ('nombrado', ['IVA a las importaciones de bajo valor por plataformas']),
    'asocapitales': ('nombrado', ['Cambian el cálculo de endeudamiento, vigencias futuras y uso del FONPET de los entes territoriales (arts. 58-65)']),
    'cgt': ('nombrado', ['Un punto de los aportes a las cajas pasa a salud (art. 22) y sube la cotización a salud del trabajador (art. 21)']),
    'fabio arias': ('nombrado', ['Sube la cotización a salud del trabajador por tramos (art. 21) y la renta empieza desde unos $5,5 M (art. 47)']),
}


def de_voces():
    d = json.loads(ESTADO.read_text())
    out = []
    for v in d['voces']:
        if v.get('g') == 'con':
            continue
        k = norm(v['q'])
        if k in FUERA:
            continue
        p = {'a': 1.0, 'r': -1.0, 'm': -0.5, 'i': None}[v['p']]
        if k in APOYA_CON_AJUSTES:
            p = 0.5
        tipo = ORG_TIPO.get(k) or (TIPO.get(v['b'], 'organizacion') if v.get('org') or v['b'] in ('Gremios', 'Sindicatos', 'Regiones', 'Organismos', 'Cajas de compensación', 'Automotor', 'Agro', 'Industria textil') else 'persona')
        if v.get('org') is None and v['b'] in ('Expertos',):
            tipo = 'persona'
        cerca_por, exige = TEXTO.get(k, ('prensa', []))
        cerca = 1.0 if cerca_por in ('obliga', 'nombrado') else (.6 if tipo in ('gremio',) else .25)
        if cerca_por == 'prensa' and tipo == 'gremio':
            cerca_por = 'sector'
        nombre = NOMBRE.get(k) or v['q']
        cita = None
        if v.get('u'):
            cita = {'titulo': v['x'], 'medio': v['f'], 'url': v['u']}
        out.append({'n': nombre, 'tipo': tipo, 'sector': SECTOR.get(k), 'postura': p, 'cita': cita,
                    'peso': max(1, int(v.get('men') or 0)), 'cerca': cerca, 'cerca_por': cerca_por, 'exige': exige,
                    'quien': f"{v['q']} · {v['c']}" if nombre != v['q'] else v['c'], 'manual': True})
    return out


# leídos a mano el 6-nov-2026 (cita en la nota original)
REGIONALES = [
    {'n': 'Caficultores del Huila', 'tipo': 'grupo', 'sector': 'agro', 'postura': None, 'region': 'Huila',
     'cerca': 1.0, 'cerca_por': 'nombrado', 'peso': 3,
     'exige': ['El café en grano sale de los excluidos y los abonos, plaguicidas y tractores pasan a 19 % desde 2028 (art. 42): quien no es responsable de IVA no lo descuenta'],
     'cita': {'titulo': 'El cinturón que termina apretando en el cafetal: 88.011 familias, 103.700 fincas, 19,65 % de la cosecha nacional; unos $74.000 de impuesto nuevo por carga', 'medio': 'Diario del Huila · 4-nov', 'url': 'https://diariodelhuila.com/el-cinturon-que-termina-apretando-en-el-cafetal/'},
     'quien': 'Sector sin vocero único · cifras de la Gobernación y la Cámara de Comercio del Huila', 'manual': True},
    {'n': 'Comité de Cafeteros del Huila', 'tipo': 'gremio', 'sector': 'agro', 'postura': None, 'region': 'Huila',
     'cerca': .6, 'cerca_por': 'sector', 'peso': 1, 'exige': [],
     'cita': {'titulo': 'Sin pronunciamiento propio encontrado; Sebastián Rivera Saab asumió la dirección encargada el 29-oct', 'medio': 'Diario del Huila · 29-oct', 'url': 'https://diariodelhuila.com/sebastian-rivera-saab-asume-la-direccion-del-comite-de-cafeteros-del-huila/'},
     'quien': 'Comité Departamental · habla la Federación por él', 'manual': True},
    {'n': 'Gobernación del Huila', 'tipo': 'entidad', 'sector': 'territorial', 'postura': None, 'region': 'Huila',
     'cerca': 1.0, 'cerca_por': 'nombrado', 'peso': 1,
     'exige': ['Cambian el cálculo de endeudamiento, las vigencias futuras y el uso de excedentes del FONPET de los departamentos (arts. 58-65)'],
     'cita': None, 'quien': 'Sin pronunciamiento sobre la ley encontrado al 6-nov', 'manual': True},
    {'n': 'Comfamiliar Huila', 'tipo': 'organizacion', 'sector': 'cajas de compensacion', 'postura': None, 'region': 'Huila',
     'cerca': 1.0, 'cerca_por': 'obliga', 'peso': 1,
     'exige': ['Girar a la ADRES uno de los cuatro puntos de sus aportes (art. 22): de ahí sale también el subsidio de vivienda'],
     'cita': None, 'quien': 'Caja de compensación del Huila · Asocajas habla por el gremio', 'manual': True},
    {'n': 'Cámara de Comercio del Huila', 'tipo': 'gremio', 'sector': 'comercio', 'postura': None, 'region': 'Huila',
     'cerca': .25, 'cerca_por': 'prensa', 'peso': 1, 'exige': [], 'cita': None,
     'quien': 'Sin pronunciamiento encontrado al 6-nov', 'manual': True},
    {'n': 'Asoexport', 'tipo': 'gremio', 'sector': 'agro', 'postura': -0.5,
     'cerca': 1.0, 'cerca_por': 'nombrado', 'peso': 2,
     'exige': ['El café verde pasa a 19 %: los exportadores pagan y piden devolución; Asoexport calcula USD 708 millones inmovilizados'],
     'cita': {'titulo': 'Exportadores de café alertan por propuesta de IVA del 19 % al café verde y sus empaques', 'medio': 'Semana · 5-nov', 'url': 'https://www.semana.com/economia/macroeconomia/articulo/exportadores-de-cafe-alertan-por-propuesta-de-iva-del-19-al-cafe-verde-y-sus-empaques/202607/'},
     'quien': 'Gustavo Gómez Montero, presidente', 'manual': True},
    {'n': 'Pequeños productores agropecuarios', 'tipo': 'grupo', 'sector': 'agro', 'postura': None,
     'cerca': 1.0, 'cerca_por': 'nombrado', 'peso': 2,
     'exige': ['Abonos, plaguicidas, semillas y tractores pasan a 19 % (art. 42); quien vende bienes excluidos no recupera ese IVA'],
     'cita': {'titulo': 'Los productos que la Ley de Rescate llevaría al 19 % de IVA: café, frutas, azúcar, aceites, fertilizantes y más', 'medio': 'Portafolio · 30-oct', 'url': 'https://www.portafolio.co/economia/impuestos/los-productos-que-la-ley-de-rescate-llevaria-al-19-de-iva-cafe-frutas-azucar-aceites-fertilizantes-y-mas-505419'},
     'quien': 'Sector sin vocero único', 'manual': True},
    {'n': 'Gobierno nacional', 'tipo': 'entidad', 'sector': None, 'postura': 1.0,
     'cerca': 1.0, 'cerca_por': 'obliga', 'peso': 82,
     'exige': ['Bajar 20 % el gasto de personal en 2028 (art. 16) y 50 % los contratos de prestación de servicios en 2027 (art. 17)',
               'Pagar la devolución EfectIVA en ciclos de máximo 15 días y fijar cada año su tope (art. 38)',
               'Suprimir, fusionar o escindir entidades con facultades por seis meses (art. 7)'],
     'cita': {'titulo': 'Restrepo y Gómez defienden la ley: sin ella, default en 2027; debe aprobarse antes de fin de año', 'medio': 'Infobae · 1-nov', 'url': 'https://www.infobae.com/colombia/2026/11/01/vicepresidente-jose-manuel-restrepo-y-el-ministro-de-hacienda-defendieron-la-ley-de-rescate-fiscal-y-advirtieron-que-pasaria-si-no-avanza-en-el-congreso-estamos-dispuestos/'},
     'quien': 'Autor del proyecto · MinHacienda y Vicepresidencia', 'manual': True},
]
# la Federación va con la cita directa de Infobae (la de voces es un enlace de Google News)
FNC_CITA = {'titulo': '«Compartimos la necesidad de recomponer las maltrechas finanzas públicas heredadas, pero gravar aún más el café no es un camino» · Germán Bahamón', 'medio': 'Infobae · 5-nov',
            'url': 'https://www.infobae.com/colombia/2026/11/05/iva-del-19-al-cafe-colombiano-que-propone-el-gobierno-haria-que-los-exportadores-del-pais-dejen-de-mover-mas-de-700-millones-de-dolares/'}


def main():
    A = {norm(a['n']): a for a in de_voces()}
    if 'federacion nacional de cafeteros' in A:
        A['federacion nacional de cafeteros']['cita'] = FNC_CITA
        A['federacion nacional de cafeteros']['peso'] = max(A['federacion nacional de cafeteros']['peso'], 8)
    for r in REGIONALES:
        A[norm(r['n'])] = r
    out = sorted(A.values(), key=lambda a: (-(a['postura'] is not None), -a['cerca'], -a['peso'], a['n']))
    doc = {'v': '2026-11-06', 'tok': 'C-477-26',
           'nota': 'Actores curados a mano el 6-nov-2026 desde las declaraciones verificadas del seguimiento de la Ley de Rescate (ley-de-rescate-avance.html) y notas leídas en su fuente original. Los actores del Huila entran por el electorado de la senadora Villalba; donde no hay pronunciamiento se dice.',
           'actores': out}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    conp = sum(1 for a in out if a['postura'] is not None)
    print(f'{len(out)} actores · {conp} con postura · {sum(1 for a in out if a.get("region"))} regionales → {OUT}')


if __name__ == '__main__':
    main()
