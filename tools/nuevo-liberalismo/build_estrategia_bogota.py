#!/usr/bin/env python3
"""Estrategia para Bogotá (Nuevo Liberalismo 2027). Arma datos/estrategia-bogota.json y .js,
valida que cada ficha exista en el banco de Candidato 360 y cuenta palabras."""
import json, re, sys, os

RAIZ = '/Users/ricardoruiz/ricardoruiz.co'
BANCO = json.load(open(f'{RAIZ}/candidato-360-data/estrategia-banco.json', encoding='utf-8'))
FICHAS = {f['id']: f for f in BANCO['fichas']}
PRINC = {p['id'] for p in BANCO['principios']}
OUT = f'{RAIZ}/Propuestas/nuevo-liberalismo/datos'

E = {
 "v": "2026-11-10",
 "ambito": "bogota",
 "frase": "La bancada que le hace las cuentas a Bogotá",
 "idea": "Una lista con identidad propia: concejales y ediles que muestran resultados localidad por localidad y hacen control con cifras a cualquier gobierno, también al que avaló el partido. Legalidad como tema propio. En seguridad y movilidad compite por credibilidad, no por dureza.",
 "nota_eje": "Es la versión de Bogotá del eje general, independencia que cumple. Aquí la independencia se prueba frente a la administración distrital: defender lo que funciona, exigir lo que falta y decirlo con cifras. La idea no cambia hasta octubre de 2027. Lo que cambia cada semana son las acciones.",

 "por_que": [
  {"t": "El voto de 2023 llegó con el tarjetón de alcaldía",
   "x": "En 2023 la lista al Concejo compitió el mismo día en que el partido ganaba la Alcaldía. En 2026, sola y a la Cámara, sacó la cuarta parte. Lo que se fue no es el norte: Chapinero conservó casi la mitad de su peso y Bosa la quinta parte. La lista de 2027 no hereda ese voto. Tiene que ganárselo con nombre propio.",
   "dato": "Concejo 2023: 404.399 votos, 14,4 % del voto válido. Cámara 2026: 105.616 votos, 3,7 %. Peso que conservó cada localidad entre las dos: Chapinero 46 %, Usaquén 26 %, Suba y Kennedy 23 %, Bosa 20 %.",
   "mod": "escenarios"},
  {"t": "Rinde más arriba, pero los votos están en el medio",
   "x": "El partido pesa más mientras más alto es el estrato, y ahí está su núcleo de opinión. Pero ese núcleo es pequeño. En 2023 la mayor parte de sus votos salió de barrios de clase media y populares, donde rindió igual o menos que en el resto de la ciudad. Con solo el norte se queda en el piso. Las curules que faltan están en estrato 3.",
   "dato": "Cámara 2026: 6,7 % de las listas en estrato 6 y 2,8 % en estrato 1; aun así 37 % de sus votos viene de estrato 3 y 30 % de estratos 1 y 2. Concejo 2023, sobre votos por listas y por tipo de barrio: 21,9 % y 20,4 % en los dos tipos del norte y 16,6 % en la ciudad; pero 65 % de su voto salió de tres tipos de barrio de clase media y popular.",
   "mod": "tablero"},
  {"t": "La seguridad se le cobra a quien gobierna",
   "x": "La percepción de inseguridad es la más alta desde 2008 y la aprobación de la gestión distrital cayó, aunque la imagen del alcalde aguanta. La Policía no da una sola lectura: los homicidios siguen por encima de 2022 y el hurto a personas baja desde 2023. El votante juzga por su cuadra y la lista del partido que avaló esa administración puede recibir la cuenta sin él en el tarjetón.",
   "dato": "Bogotá Cómo Vamos, diciembre de 2025: 62 % se siente inseguro; aprobación de la gestión distrital 26 % (42 % en 2024); imagen favorable del alcalde 55 %. Guarumo, abril de 2026: aprobación 53,3 %. Policía: homicidios 1.014 en 2022 y 1.186 en 2025; hurto a personas 147.564 en 2023 y 123.017 en 2025.",
   "mod": "encuesta"},
  {"t": "Hay estructura, pero es de personas",
   "x": "El partido tiene ocho concejales y ediles en casi todas las localidades: una red que cubre la ciudad. Pero dos de cada tres votos de la lista fueron al nombre de un candidato, no al logo. Con voto preferente cada concejal cuida su propia votación y su rival más cercano está en su misma lista. Sin una idea común, la campaña son ocho campañas.",
   "dato": "Concejo 2023: 276.694 votos a candidatos y 127.705 al logo, 8 curules en lista con En Marcha. Ediles: 31 de 184 en 19 de 20 localidades, 348.458 votos; 11 en siete listas propias y 20 en doce listas de coalición.",
   "mod": "inventario"}
 ],

 "lugar": {
  "x": "En Bogotá hay dos lugares ocupados: el de la mano dura, que es de la derecha, y el de la oposición al modelo de ciudad, que es de la izquierda. El lugar libre es el de quien hace las cuentas: la bancada que dice con cifras qué se cumplió y qué falta, sin deberle nada a ningún gobierno. Ese lugar solo es creíble si el control incluye a la administración que el partido avaló. Callar por cercanía lo deja sin lugar.",
  "propios": [
   {"tema": "Legalidad y contratación limpia",
    "x": "Es el tema del partido en el país y en Bogotá casi nadie lo trabaja con constancia. Control político con documento, también cuando toca al Distrito.",
    "dato": "En la prensa de Bogotá la corrupción es 1,2 % de los titulares de asuntos públicos (23 de 1.967) y 87 % son negativos. El partido aparece en 5 de 67.654 titulares del banco."},
   {"tema": "Resultados por localidad",
    "x": "Lo que la bancada y los ediles consiguen, contado barrio por barrio y con prueba. Es el lenguaje que premian los barrios donde se vota a quien resuelve.",
    "dato": "31 ediles en 19 de 20 localidades y 8 concejales con 276.694 votos personales."}
  ],
  "consenso": [
   {"tema": "Seguridad",
    "x": "Todos quieren lo mismo. No se gana prometiendo más dureza sino mostrando qué mejora y qué empeora en cada localidad, y qué va a vigilar la bancada.",
    "dato": "31,2 % de los titulares de asuntos públicos de Bogotá; 62 % se siente inseguro en la ciudad y 43 % en su barrio."},
   {"tema": "Movilidad",
    "x": "Es el segundo tema de la ciudad y el de tono menos negativo entre los grandes. Hay obras con fecha: ahí se puede reclamar crédito y exigir plazos.",
    "dato": "18,7 % de los titulares de Bogotá, 33,5 % negativos. En TransMilenio, 63,7 % menciona los robos dentro del sistema (Bogotá Cómo Vamos)."},
   {"tema": "Salud",
    "x": "Es lo que más pide la gente en el país y pesa poco en la prensa de la ciudad. Hay espacio para hacer control a la red pública del Distrito.",
    "dato": "Invamer, mayo de 2026: 71,9 % la pone entre lo más urgente. En la prensa de Bogotá es 6,2 % de los titulares."}
  ],
  "ceder": [
   {"tema": "La mano dura",
    "x": "Ese lugar ya tiene dueño. Competir ahí es ser una copia menor y contradice el registro de un partido de legalidad."},
   {"tema": "La pelea entre el gobierno nacional y la oposición",
    "x": "El partido se declaró independiente. En Bogotá esa pelea no le suma votos y lo saca de los temas de ciudad."}
  ],
  "refs": ["T1", "T2", "R3.4"]
 },

 "pilares": [
  {"t": "Identidad propia de la lista: las cuentas, también al Distrito",
   "x": "La lista no puede ser ni la defensa de la administración ni su oposición. Su lugar es el de quien mide: reconoce lo que funciona, dice con fecha lo que falta y explica qué depende del Concejo y qué no. El votante juzga por los servicios que ve, aunque no dependan del concejal. Por eso la explicación hace parte del mensaje.",
   "como": [
    "Un tablero público de la bancada con los compromisos del Plan de Desarrollo por localidad, actualizado cada trimestre con la fuente de cada cifra.",
    "Cada concejal asume un tema de control y vuelve a él todos los meses con un dato nuevo.",
    "Una regla escrita para la bancada: cuando el dato es malo para el Distrito, se dice igual, con la propuesta al lado."
   ],
   "principio": "A1", "refs": ["T1", "T2", "R3.4", "T20"], "oficio": False},
  {"t": "Seguridad: credibilidad con cifras, no dureza",
   "x": "La seguridad es un tema en el que todos quieren lo mismo, y ahí se compite por quién es creíble. El partido no gana ofreciendo más fuerza. Gana si muestra, localidad por localidad, qué delitos bajan y cuáles suben, y si junta autoridad con cuidado. El registro de orden funciona cuando es tranquilo y no busca culpables fáciles.",
   "como": [
    "Un informe de seguridad por localidad cada dos meses con las dos medidas: lo que registra la Policía y lo que la gente dice sentir.",
    "Tres compromisos medibles por localidad, con responsable y fecha de revisión, acordados en reuniones con vecinos.",
    "Reconocer en público lo que mejora, como el hurto a personas, y pedir cuentas por lo que sigue por encima de 2022, como los homicidios."
   ],
   "principio": "A2", "refs": ["T2", "T4", "R1.1", "R1.2", "T11"], "oficio": False},
  {"t": "Los ediles como red: crédito frecuente y cara conocida",
   "x": "Treinta y un ediles son la presencia del partido en el barrio. Los ciudadanos premian más cuántas veces se muestra un logro que su tamaño, y premian a quien está. La red sirve si cada edil rinde cuentas en su localidad y si el partido mide, por puesto, qué produce cada liderazgo antes de repartir renglones.",
   "como": [
    "Una pieza de crédito por semana y por localidad: un arreglo, una respuesta de una entidad, una proposición, con fecha y prueba.",
    "Un encuentro mensual de rendición de cuentas por localidad, con propuesta concreta y compromiso que se pueda verificar. No un mitin.",
    "Línea de base por puesto de 2023 y 2026 para medir después qué movió cada edil y cada concejal."
   ],
   "principio": "A7", "refs": ["T20", "T21", "R3.1", "R3.2", "R3.3"], "oficio": False},
  {"t": "Ensanchar al medio antes de la campaña",
   "x": "El voto que decide las curules cinco a ocho está en la clase media que vota mucho y no le debe el voto a nadie, y en la que marca el nombre que más ha oído. Ese votante casi no se mueve con el contacto de campaña. Se gana temprano, con un lugar claro en los temas de ciudad y con nombres que ya suenen cuando empiece la propaganda.",
   "como": [
    "Tomar posición pública en un tema de ciudad cada mes, con un dato que nadie más tenga, antes de marzo de 2027.",
    "Hacer conocer a quienes van a encabezar en Engativá, Kennedy, Suba y Fontibón desde ahora, con el mismo mensaje de la bancada.",
    "Decir cada tema en dos claves: control y transparencia para el norte, tiempo, plata y tranquilidad para la clase media."
   ],
   "principio": "A5", "refs": ["T14", "T1", "T6", "T10"], "oficio": False},
  {"t": "Decidir el vehículo y las reglas antes de que empiece la pelea interna",
   "x": "Con voto preferente el rival de cada candidato está en su propia lista. Si no hay reglas, la competencia interna se come el mensaje común. Hay que decidir pronto el tipo de lista, si se repite la coalición, cómo se reparte el territorio y qué papel juega la lista frente a la alcaldía, que tendrá segunda vuelta y no tendrá al alcalde actual en el tarjetón.",
   "como": [
    "Definir antes de marzo de 2027 lista abierta o cerrada, coalición o lista propia y criterio para los renglones.",
    "Un acuerdo de territorio entre candidatos, medido por puesto, para que no compitan por las mismas cuadras.",
    "Decidir qué hace la lista en la alcaldía: candidatura propia, coalición o apoyo, y qué pasa si hay segunda vuelta."
   ],
   "principio": "A1", "refs": ["T3"], "oficio": True}
 ],

 "audiencias": [
  {"quien": "El norte de opinión y de figuras",
   "donde": "Usaquén, Chapinero, Teusaquillo, Barrios Unidos y el norte de Suba; estratos 4 a 6",
   "cuadrante": "retener-crecer",
   "decir": "Posición clara y control con hechos en los temas de ciudad. Se decide por lo que lee, no por quién lo visita. Aquí el partido rinde por encima de la ciudad, y Chapinero fue la localidad que más peso conservó en 2026.",
   "refs": ["T20", "T22", "T6"]},
  {"quien": "La clase media que vota mucho y no tiene dueño",
   "donde": "Barrios de clase media, estratos 2 y 3, en Engativá, Fontibón, Kennedy y Suba",
   "cuadrante": "conocer",
   "decir": "Una propuesta clara y temprana de movilidad y seguridad, con cifras de su localidad. Es el voto que está en juego y de donde salió la cuarta parte de la votación de 2023.",
   "refs": ["T1", "T14"]},
  {"quien": "La clase media que vota por el nombre que conoce",
   "donde": "Engativá, Kennedy, Suba, Fontibón, Puente Aranda, Antonio Nariño",
   "cuadrante": "conocer",
   "decir": "El nombre del candidato junto a un resultado que se vea en el barrio. Frases cortas y repetidas. La pelea es por reconocimiento, no por ideas.",
   "refs": ["T3", "T10", "T20"]},
  {"quien": "La periferia que marca el logo",
   "donde": "Bosa, Kennedy, Ciudad Bolívar, Usme y el occidente de Suba; estrato 2",
   "cuadrante": "movilizar",
   "decir": "El edil como cara del partido y cómo se marca el tarjetón: logo y número. En 2023 aquí un tercio del voto de la lista fue al logo y fue donde más se cayó en 2026.",
   "refs": ["T13", "R2.2", "R3.3"]},
  {"quien": "Barrios con dueño y barrios que casi no votan al Concejo",
   "donde": "Centro y suroriente tradicional; estrato 1 de Ciudad Bolívar, Usme y San Cristóbal",
   "cuadrante": "no-gastar",
   "decir": "Solo donde un edil del partido ya tiene base propia: ahí se cuida. En el resto, el contacto de campaña casi no persuade y no es donde se ganan las curules.",
   "refs": ["T14"]}
 ],

 "relato": {
  "yo": "Somos un partido que no le debe el voto a ningún gobierno ni a ningún bando. Por eso puede hacer las cuentas en voz alta, también las de la administración que ayudó a elegir.",
  "nosotros": "Quien paga impuestos, espera el bus y quiere caminar tranquilo por su barrio pide lo mismo: que le cumplan y que le digan la verdad con cifras. Lo pide igual quien vive en Usaquén que quien vive en Bosa.",
  "ahora": "En 2027 la ciudad cambia de alcalde. Antes de escoger hay que saber qué se cumplió, qué falta y quién va a vigilar al que llegue. Esa es la tarea de esta lista.",
  "refs": ["T8", "T7"]
 },

 "contraste": [
  {"frente": "A quienes ofrecen mano dura",
   "x": "Con la cifra de cada localidad y un compromiso con fecha. La diferencia no es quién es más fuerte sino quién muestra resultados y los deja revisar."},
  {"frente": "A la oposición al modelo de ciudad",
   "x": "Con el detalle: qué obra, qué contrato, qué plazo. El partido no discute si la ciudad va bien o mal en bloque. Mide tema por tema."},
  {"frente": "A la lista que compite por el mismo votante de opinión",
   "x": "Con el tema propio, legalidad y control, y con la red de ediles: opinión con presencia en el barrio. Sin ataque: no rinde más y se devuelve."},
  {"frente": "A la administración distrital",
   "x": "No es contraste, son cuentas. Se reconoce lo que mejora con la misma cifra con que se exige lo que falta. Ni defensa cerrada ni ruptura."}
 ],

 "fases": [
  {"fase": "Posicionamiento", "desde": "2026-11-10", "hasta": "2027-02-28",
   "foco": "Ocupar el lugar antes de la campaña: la bancada que hace las cuentas. La persuasión se hace ahora; después casi no mueve a nadie.",
   "acciones": [
    "Publicar el tablero de compromisos por localidad y el primer informe de seguridad.",
    "Una pieza de crédito por semana por localidad y una toma de posición de ciudad por mes.",
    "Armar la línea de base por puesto con los resultados de 2023 y 2026.",
    "Leer en público la próxima encuesta de percepción ciudadana, con lo bueno y lo malo."
   ]},
  {"fase": "Precampaña", "desde": "2027-03-01", "hasta": "2027-07-30",
   "foco": "Cerrar el vehículo y las reglas, e inscribir, sin dejar de rendir cuentas.",
   "acciones": [
    "Decidir tipo de lista, coalición y renglones, y firmar el acuerdo de territorio entre candidatos.",
    "Definir el papel de la lista frente a la alcaldía.",
    "Rendición de cuentas mensual por localidad y red de hogares que van a movilizar en octubre.",
    "Inscribir la lista entre el 30 de junio y el 31 de julio."
   ]},
  {"fase": "Campaña", "desde": "2027-07-31", "hasta": "2027-10-23",
   "foco": "Movilizar a quien ya prefiere al partido y mantener la elección sobre los temas propios.",
   "acciones": [
    "Contacto cara a cara en los hogares de las localidades donde ya es fuerte.",
    "Crédito frecuente: muchos logros pequeños, cada uno con su prueba.",
    "Guardar la pauta para las últimas semanas y enseñar cómo se marca logo y número."
   ]},
  {"fase": "Día D", "desde": "2027-10-24", "hasta": "2027-10-31",
   "foco": "Sacar a votar y cuidar el voto.",
   "acciones": [
    "Recordatorio por hogar y transporte donde la lista depende del logo.",
    "Testigos en los puestos donde están los votos del partido."
   ]},
  {"fase": "Segunda vuelta de alcaldía, si la hay", "desde": "2027-11-01", "hasta": "2027-11-21",
   "foco": "La bancada elegida decide con qué condiciones acompaña o vigila. La fecha sale de la norma; la Registraduría no la ha fijado.",
   "acciones": [
    "Publicar las condiciones de la bancada antes de cualquier apoyo.",
    "Seguir el escrutinio y guardar los resultados por puesto."
   ]}
 ],

 "agenda": [
  {"si": "Cuando la prensa de Bogotá esté en seguridad",
   "haz": "Entra con la cifra de la localidad afectada y un compromiso que se pueda revisar. Di qué depende del Distrito, qué de la Policía y qué de la justicia.",
   "no": "No compitas en dureza ni salgas a defender o a atacar a la administración en bloque.",
   "dato": "Es 31,2 % de los titulares de asuntos públicos de Bogotá y 61 % son negativos."},
  {"si": "Cuando esté en movilidad, TransMilenio o el metro",
   "haz": "Reclama crédito por lo que la bancada consiguió y exige plazo por lo que está atrasado, con fecha.",
   "no": "No prometas lo que no depende del Concejo.",
   "dato": "Es 18,7 % de los titulares de Bogotá y el tema grande con menos tono negativo, 33,5 %."},
  {"si": "Cuando salga un caso de corrupción o de contratación en el Distrito",
   "haz": "Sé el primero, con documento y con propuesta. Es el tema propio: hay que estar siempre, también si el caso toca a la administración.",
   "no": "No calles por cercanía. El silencio aquí cuesta el lugar entero.",
   "dato": "Solo 23 de 1.967 titulares de Bogotá son de corrupción, y 87 % son negativos."},
  {"si": "Cuando sea un escándalo nacional o una pelea entre el gobierno y la oposición",
   "haz": "Una línea de posición y de vuelta a Bogotá.",
   "no": "No gastes la semana ahí: la historia se apaga sola.",
   "dato": "La historia típica dura 3 días y solo 11 % pasa de una semana."},
  {"si": "Cuando salga una encuesta o un balance de la administración",
   "haz": "Léela por localidad, reconoce el dato tal como viene y anuncia qué va a vigilar la bancada.",
   "no": "No discutas la encuesta ni la celebres como propia.",
   "dato": "La última: 26 % aprueba la gestión distrital y 55 % tiene imagen favorable del alcalde. Son preguntas distintas."},
  {"si": "Cuando esté en salud",
   "haz": "Control a la red pública del Distrito con datos de espera y de atención.",
   "no": "No prometas lo que es del gobierno nacional.",
   "dato": "Es 6,2 % de los titulares de Bogotá, 58 % negativos; en el país 71,9 % la pone entre lo más urgente."}
 ],

 "riesgos": [
  {"r": "Que la elección al Concejo se lea como un sí o un no a la administración.",
   "manejo": "Construir desde ya la identidad de la lista como la que hace las cuentas. Ni romper ni esconderse: reconocer y exigir con la misma cifra."},
  {"r": "Que la competencia por el voto preferente rompa el mensaje común.",
   "manejo": "Reglas de territorio y de trato firmadas antes de la inscripción, y medición por puesto."},
  {"r": "Quedarse en el norte.",
   "manejo": "Metas por localidad en estrato 3 y candidatos con nombre ahí. Con solo el voto de opinión el escenario es el piso: 2 curules."},
  {"r": "Depender del logo en la periferia, que en 2023 vino con el tarjetón de alcaldía.",
   "manejo": "Los ediles como cara del partido y enseñar a marcar logo y número."},
  {"r": "Hablar de cifras de seguridad que la gente no siente.",
   "manejo": "Mostrar siempre las dos medidas, registro y percepción, y explicar qué controla el Concejo."},
  {"r": "Llegar tarde a la decisión de coalición.",
   "manejo": "Decidir con la aritmética a la vista: cada curul cuesta cerca de 1,7 puntos del voto válido."}
 ],

 "medir": [
  {"que": "Curules a la vista",
   "como": "El porcentaje del voto válido contra la escalera de 2023: 3,4 % da 2 curules, 8,6 % da 5 y 13,7 % da 8."},
  {"que": "Si la presencia mueve votos",
   "como": "Participación y votación por puesto donde trabajó un edil o un concejal, contra los puestos donde no, con 2023 y 2026 como base."},
  {"que": "Si el partido ya ocupa su lugar en la prensa",
   "como": "Titulares de Bogotá que nombran a la bancada en control, legalidad o seguridad. Hoy el partido aparece en 5 de 67.654."},
  {"que": "Ritmo de crédito",
   "como": "Piezas con prueba por localidad y por mes, y encuentros de rendición de cuentas hechos."},
  {"que": "El clima de la ciudad",
   "como": "Percepción de inseguridad y aprobación de la gestión en cada encuesta nueva, al lado del registro de la Policía por localidad."}
 ],

 "refs": [],
 "advertencias": []
}

# ── referencias: solo las usadas, copiadas del banco ──
usadas = []
def junta(ids):
    for i in ids:
        if i not in usadas: usadas.append(i)
junta(E['lugar']['refs'])
for p in E['pilares']: junta(p['refs'])
for a in E['audiencias']: junta(a['refs'])
junta(E['relato']['refs'])
# fichas que respaldan las fases y la lectura de la agenda
junta(['T15', 'T16', 'T17', 'T18'])
malas = [i for i in usadas if i not in FICHAS]
assert not malas, malas
for p in E['pilares']: assert p['principio'] in PRINC, p['principio']
for i in usadas:
    f = FICHAS[i]
    E['refs'].append({"id": i, "corto": f['corto'],
                      "texto": " · ".join(r['texto'] for r in f['refs']),
                      "doi": next((r.get('doi') for r in f['refs'] if r.get('doi')), None)})
adv = BANCO['advertencias']
E['advertencias'] = [a for a in adv if 'Cartagena' not in a]

# ── chequeos de forma ──
pal = lambda s: len(re.findall(r'\S+', s))
CUAD = {'retener', 'retener-crecer', 'conocer', 'movilizar', 'no-gastar'}
err = []
if pal(E['frase']) > 10: err.append(('frase', pal(E['frase'])))
if pal(E['idea']) > 45: err.append(('idea', pal(E['idea'])))
for p in E['por_que']:
    n = pal(p['x'])
    if not 40 <= n <= 70: err.append(('por_que', p['t'], n))
    assert p['mod'] in ('inventario', 'tablero', 'clima', 'escenarios', 'encuesta')
n = pal(E['lugar']['x'])
if not 60 <= n <= 90: err.append(('lugar', n))
for p in E['pilares']:
    n = pal(p['x'])
    if not 50 <= n <= 80: err.append(('pilar', p['t'], n))
    assert len(p['como']) == 3
for a in E['audiencias']: assert a['cuadrante'] in CUAD
txt = json.dumps(E, ensure_ascii=False)
if '—' in txt: err.append('guion largo')
print('palabras: frase', pal(E['frase']), 'idea', pal(E['idea']), 'lugar', pal(E['lugar']['x']),
      'por_que', [pal(p['x']) for p in E['por_que']], 'pilares', [pal(p['x']) for p in E['pilares']])
print('fichas usadas', len(usadas), usadas)
if err:
    print('AJUSTAR', err); sys.exit(1)

s = json.dumps(E, ensure_ascii=False, indent=1)
open(os.path.join(OUT, 'estrategia-bogota.json'), 'w', encoding='utf-8').write(s + '\n')
open(os.path.join(OUT, 'estrategia-bogota.js'), 'w', encoding='utf-8').write(
    "window.NLD=window.NLD||{};window.NLD['estrategia-bogota']=" + json.dumps(E, ensure_ascii=False) + ";\n")
json.load(open(os.path.join(OUT, 'estrategia-bogota.json'), encoding='utf-8'))
print('ok', len(s) // 1024, 'KB')
