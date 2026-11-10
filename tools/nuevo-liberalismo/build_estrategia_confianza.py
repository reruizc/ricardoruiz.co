#!/usr/bin/env python3
"""Bloque «La confianza» de la estrategia (módulo 05), por ámbito: general · bogota · resto.

Pedido de Ricardo (10-nov-2026): el partido se identifica con una familia política y hay mucha
desconfianza hacia los políticos; en 2026 ganó quien se presentó como alguien de fuera de la
política tradicional. ¿Cómo genera confianza el partido?

Fuentes leídas en el original (no de memoria):
  · Invamer, Colombia Opina #21 (campo 15-24 abr 2026, 3.800 encuestas), p. 39: opinión favorable
    de instituciones. PDF publicado por La Silla Vacía.
  · OCDE, Encuesta sobre los determinantes de la confianza en las instituciones públicas de América
    Latina y el Caribe, resultados 2025 (10 países, Colombia entre ellos): promedios regionales.
  · El Espectador, perfil del presidente electo como «outsider» (jun-2026).
Las fichas T* son del banco de estrategia de Candidato 360; lo demás va como criterio de oficio.
Nada sobre la relación entre los hermanos Galán.
Escribe Propuestas/nuevo-liberalismo/datos/estrategia-confianza.json y .js."""
import json, os, re

R = os.path.join(os.path.dirname(__file__), '..', '..')
D = os.path.join(R, 'Propuestas', 'nuevo-liberalismo', 'datos')
banco = json.load(open(os.path.join(R, 'candidato-360-data', 'estrategia-banco.json'), encoding='utf-8'))
FICHAS = {f['id']: f for f in banco['fichas']}

INV = 'https://www.lasillavacia.com/wp-content/uploads/2026/04/2026-04-Invamer-Colombia-Opina-21.pdf'
OCDE = ('https://www.oecd.org/content/dam/oecd/es/publications/reports/2025/11/oecd-survey-on-drivers-of-trust-in-public-'
        'institutions-in-latin-america-and-the-caribbean-2025-results_698c3d98/b4dea13c-es.pdf')
ESP = ('https://www.elespectador.com/politica/elecciones-colombia-2026/abelardo-de-la-espriella-es-el-nuevo-presidente-de-'
       'colombia-esta-es-su-historia-noticias-hoy-elecciones-2026/')

DATOS = [
    {'cifra': '26,5 %', 'dato': 'tiene opinión favorable de los partidos políticos; 65,1 % desfavorable. Es la institución peor vista después del ELN.',
     'fuente': 'Invamer, abril de 2026', 'url': INV},
    {'cifra': '37,8 %', 'dato': 'tiene opinión favorable del Congreso, frente a 65,8 % de los empresarios y 81,4 % de las Fuerzas Militares.',
     'fuente': 'Invamer, abril de 2026', 'url': INV},
    {'cifra': '66 % y 21 %', 'dato': 'confía en el gobierno entre quienes sienten que «gente como ellos» tiene voz, y entre quienes sienten que no la tiene.',
     'fuente': 'OCDE 2025, promedio de América Latina', 'url': OCDE},
    {'cifra': '31 %', 'dato': 'confía en que un funcionario rechace un soborno; 43 % cree que un servicio mejora si la gente se queja.',
     'fuente': 'OCDE 2025, promedio de América Latina', 'url': OCDE},
]

C = {
 'general': {
  'titulo': 'La confianza: el problema de fondo',
  'diagnostico': ('La gente no desconfía de que alguien resuelva; desconfía de los políticos y de los partidos. Los partidos son la '
                  'institución peor vista después del ELN y los empresarios están casi 40 puntos por encima. En 2026 ganó la presidencia '
                  'quien se presentó como alguien de fuera de la política tradicional. Para el Nuevo Liberalismo esto pesa doble: es un partido y '
                  'se le identifica con una familia política.'),
  'outsider': {'x': 'El presidente electo se presentó como «outsider». La prensa lo describió así al día siguiente de la elección.',
               'fuente': 'El Espectador, junio de 2026', 'url': ESP},
  'familia': {
   'activo': ('El apellido Galán está asociado a la lucha contra la corrupción y el narcotráfico, que es justo el tema propio de la '
              'estrategia. Es un capital que pocos partidos tienen.'),
   'riesgo': ('Para quien desconfía de los políticos, un partido identificado con una familia confirma la sospecha: que la política es un '
              'oficio que se hereda. Y el votante joven no vivió el legado: para él es un apellido, no una historia.'),
   'regla': ('La marca es la conducta, no el apellido. El legado se cuenta por lo que el partido hace hoy y por las personas nuevas que '
             'lleva, no se invoca como argumento.'),
  },
  'palancas': [
   {'t': 'Caras que no vienen de la política', 'x': ('Listas con gente que trae un oficio, un barrio o una organización detrás, que se pueda '
     'presentar por lo que ha hecho fuera de la política. El partido pone la regla y la marca; la cara la pone alguien en quien el vecino ya confía.'),
    'como': ['Una convocatoria abierta y pública para candidaturas, con requisitos escritos.',
             'Cuota de primeras candidaturas en cada lista: gente que nunca ha tenido un cargo de elección.',
             'Cada candidato se presenta con su oficio y su trayectoria antes que con el partido.'],
    'refs': ['T3'], 'oficio': True, 'dato': 'Empresarios 65,8 % de opinión favorable; partidos 26,5 % (Invamer, abr-2026).'},
   {'t': 'Reglas que se ven', 'x': ('La confianza no se pide: se prueba con reglas que cualquiera puede revisar. Un partido que dice que su tema '
     'es la legalidad tiene que ser el primero en publicar cómo escoge a sus candidatos y qué les exige.'),
    'como': ['Estándar de avales publicado: sin condenas, sin investigaciones abiertas por corrupción, con bienes e intereses declarados.',
             'Publicar quién aspira, quién decide y por qué en cada aval.',
             'Retirar el aval con el mismo criterio cuando el caso es propio.'],
    'refs': ['T2'], 'oficio': True, 'dato': 'Solo 31 % confía en que un funcionario rechace un soborno (OCDE 2025).'},
   {'t': 'Responder lo pequeño', 'x': ('La confianza se gana en las interacciones de todos los días: un reclamo que se atiende, un hueco que se tapa, '
     'una respuesta con fecha. Muchos logros pequeños con prueba pesan más que una promesa grande.'),
    'como': ['Cada cargo del partido atiende y responde reclamos con fecha y lo cuenta.',
             'Una pieza de crédito por semana: un logro pequeño, con prueba.',
             'Decir también lo que no se pudo y por qué.'],
    'refs': ['T20', 'T21'], 'oficio': False, 'dato': '43 % cree que un servicio mejora si la gente se queja (OCDE 2025).'},
   {'t': 'Dar voz antes de pedir el voto', 'x': ('Quien siente que tiene voz confía tres veces más. Antes de presentar propuestas, el partido '
     'escucha y deja que la gente escoja una prioridad por barrio o municipio. Lo que se escoge allí se vuelve compromiso público.'),
    'como': ['Asambleas abiertas por localidad o municipio en el primer semestre de 2027.',
             'Cada asamblea escoge una prioridad, que entra al programa con su nombre.',
             'Volver a rendir cuentas en el mismo lugar.'],
    'refs': ['T21'], 'oficio': True, 'dato': '66 % confía si siente que tiene voz; 21 % si no (OCDE 2025).'},
   {'t': 'Hablar como quien resuelve', 'x': ('Menos sigla y más nombre, problema y resultado. El votante desconfiado escucha «partido» y se '
     'aleja; escucha «arreglamos esto, aquí está la prueba» y presta atención.'),
    'como': ['En cada pieza, primero el problema y el resultado; el logo al final.',
             'Nada de lenguaje de partido ni de cargos: vecino, barrio, cuenta, prueba.',
             'Voceros con oficio, no solo dirigentes.'],
    'refs': ['T1'], 'oficio': False, 'dato': ''},
  ],
  'no': ['Esconder el apellido o el partido: se nota, y confirma la sospecha.',
         'Competir por ser más «de afuera» que quienes ya ocupan ese lugar.',
         'Usar el legado como argumento principal en vez de mostrar conducta.',
         'Avalar a cualquiera con votos: un solo caso de corrupción tumba la marca de legalidad.'],
 },
 'bogota': {
  'titulo': 'La confianza en Bogotá',
  'diagnostico': ('En Bogotá la desconfianza hacia los políticos se cruza con la evaluación de una administración elegida con el aval del '
                  'partido: la aprobación de la gestión distrital bajó a 26 %. La lista al Concejo no tiene al alcalde en el tarjetón, pero '
                  'carga con su apellido. La confianza tiene que construirla la lista con sus propios nombres.'),
  'familia': {
   'activo': 'El apellido abre puertas en los sectores que ya votan por el partido, sobre todo en el norte.',
   'riesgo': 'Hace que la elección del Concejo se lea como un sí o un no a la administración, y eso no lo controla la lista.',
   'regla': 'La lista se presenta por sus nombres, sus ediles y sus cuentas por localidad; no por el apellido del alcalde.',
  },
  'palancas': [
   {'t': 'El edil como cara de confianza', 'x': ('Los 31 ediles son vecinos conocidos en su localidad. En una ciudad que desconfía, la cara que la '
     'gente ve en su barrio pesa más que la marca.'),
    'como': ['Cada edil rinde cuentas cada mes en su localidad, con lo que consiguió y lo que no.',
             'Las piezas del partido muestran ediles y concejales, no dirigentes.'],
    'refs': ['T20', 'T21'], 'oficio': False, 'dato': '31 ediles en 19 localidades (inventario).'},
   {'t': 'Candidatos nuevos en el medio y la periferia', 'x': ('Donde el partido perdió peso entre 2023 y 2026, las caras conocidas del partido no '
     'alcanzan. Hace falta gente del barrio, con oficio, que no venga de la política.'),
    'como': ['Convocatoria abierta por localidad para la lista del Concejo.',
             'Al menos un nombre nuevo con arraigo en cada zona de estrato 2 y 3.'],
    'refs': ['T3'], 'oficio': True, 'dato': ''},
   {'t': 'Cuentas que se pueden revisar', 'x': ('Publicar por localidad lo que hace el concejal y lo que hace la administración, con la cifra, '
     'para que nadie tenga que creer en la palabra de nadie.'),
    'como': ['Un tablero público por localidad, actualizado cada mes.',
             'Reconocer lo que mejora y exigir lo que falta con la misma cifra.'],
    'refs': ['T19'], 'oficio': False, 'dato': 'Aprobación de la gestión distrital 26 % (Bogotá Cómo Vamos, dic-2025).'},
  ],
  'no': ['Defender la administración en bloque o romper con ella para ganar confianza: las dos se leen como cálculo.',
         'Llenar la lista con nombres de la política de siempre.'],
 },
 'resto': {
  'titulo': 'La confianza en las regiones',
  'diagnostico': ('Fuera de Bogotá la confianza no es en el partido sino en la persona. Un concejal conocido y que responde vale más que cualquier '
                  'marca nacional. El riesgo es el contrario: que la marca de legalidad se use para avalar a quien tiene votos y no conducta.'),
  'familia': {
   'activo': 'La marca nacional asociada a la legalidad le da a un candidato local una razón para distinguirse de la política de siempre.',
   'riesgo': 'Si el aval se entrega a la política tradicional del municipio, el partido se vuelve una sigla más.',
   'regla': 'El aval es un sello de conducta: se da a quien cumple el estándar y se retira a quien no.',
  },
  'palancas': [
   {'t': 'Gente con arraigo y oficio', 'x': ('El candidato regional confiable es el que la gente conoce por su trabajo: la profesora, el líder de la '
     'junta, la comerciante. El partido le da la regla, la marca y la red; el arraigo lo trae ella.'),
    'como': ['Buscar candidatos en juntas de acción comunal, gremios y organizaciones del municipio.',
             'Primeras candidaturas en cada lista, con su oficio por delante.'],
    'refs': ['T3'], 'oficio': True, 'dato': '233 de 246 curules fuera de Bogotá salieron de listas propias (inventario).'},
   {'t': 'El sello del partido como garantía', 'x': ('Que el votante sepa qué significa el aval: sin condenas, con cuentas cada mes y con un '
     'compromiso público. El sello vale si se cumple en todos los municipios por igual.'),
    'como': ['El mismo estándar de avales en todos los departamentos, publicado.',
             'Retirar el aval con el mismo criterio cuando falla un candidato propio.'],
    'refs': ['T2'], 'oficio': True, 'dato': ''},
   {'t': 'Rendir cuentas donde la gente vive', 'x': ('En municipios pequeños el contacto es directo. Una rendición de cuentas al mes en la vereda o en '
     'el barrio construye más confianza que cualquier pauta.'),
    'como': ['Cada concejal del partido rinde cuentas cada mes en un lugar distinto del municipio.',
             'Cada logro con fecha y prueba, contado por el concejal y no por el partido.'],
    'refs': ['T20', 'T21'], 'oficio': False, 'dato': 'En 134 municipios el partido tiene un solo concejal (inventario).'},
  ],
  'no': ['Avalar al cacique local porque trae votos.',
         'Hablar desde Bogotá: la cara es local o no es.'],
 },
}

# validación: fichas existen, sin guiones largos, sin nombres vetados
usadas = set()
for a, b in C.items():
    for p in b['palancas']:
        for r in p['refs']:
            assert r in FICHAS, (a, r)
            usadas.add(r)
txt = json.dumps(C, ensure_ascii=False)
assert '—' not in txt and '–' not in txt, 'guion largo'
for v in ('Juan Manuel', 'Carlos Fernando', 'hermano'):
    assert v not in txt, v

refs = []
for r in sorted(usadas):
    f = FICHAS[r]; ref = (f.get('refs') or [{}])[0]
    refs.append({'id': r, 'corto': f.get('corto'), 'texto': ref.get('texto'), 'doi': ref.get('doi')})

out = {'v': '2026-11-10', 'datos': DATOS, 'ambitos': C, 'refs': refs}
s = json.dumps(out, ensure_ascii=False, indent=1)
open(os.path.join(D, 'estrategia-confianza.json'), 'w', encoding='utf-8').write(s)
open(os.path.join(D, 'estrategia-confianza.js'), 'w', encoding='utf-8').write(
    "window.NLD=window.NLD||{};window.NLD['estrategia-confianza']=" + json.dumps(out, ensure_ascii=False) + ';\n')
print('ok ·', ', '.join(sorted(usadas)), '·', round(len(s) / 1024), 'KB')
