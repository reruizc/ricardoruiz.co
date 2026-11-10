#!/usr/bin/env python3
"""Estrategia para las regiones (resto del país, sin Bogotá) · módulo 05 de la presentación del Nuevo Liberalismo.

El TEXTO está escrito a mano aquí; las CIFRAS se leen de los datos de la presentación
(inventario.json, escenarios.json, tablero.json, clima.json, clima-ambito.json) y las referencias
del banco de estrategia de Candidato 360 (candidato-360-data/estrategia-banco.json).
Valida que cada ficha citada exista en el banco y el largo de cada texto.
Salida: datos/estrategia-resto.json + .js   (correr después de los builders de los módulos 01-04).
"""
import json, os, re, sys, collections

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
D = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos')
L = lambda n: json.load(open(os.path.join(D, n + '.json'), encoding='utf-8'))
inv, esc, tab, cli, amb = L('inventario'), L('escenarios'), L('tablero'), L('clima'), L('clima-ambito')
banco = json.load(open(os.path.join(RAIZ, 'candidato-360-data', 'estrategia-banco.json'), encoding='utf-8'))

# ── formato ──────────────────────────────────────────────────────────────────
def n(x): return f'{int(round(x)):,}'.replace(',', '.')
def tc(s):   # MARÍA LA BAJA → María la Baja
    return re.sub(r'\b(De|Del|La|Las|Los|Y)\b', lambda m: m.group(0).lower(), s.title()).replace('ñO', 'ño')
def votos(k): return '1 voto' if k == 1 else f'{n(k)} votos'
def p(x, d=0): return f'{x * 100:.{d}f}'.replace('.', ',') + ' %'

# ── cifras: inventario (concejos, alcaldías, asambleas fuera de Bogotá) ──────
nl = inv['nl']
conc = [c for c in nl['concejales'] if c['k'] != '16001']
CUR = sum(c['cur'] for c in conc); MUN = len(conc)
PROPIA = sum(c['cur'] for c in conc if not c['coal']); COAL = CUR - PROPIA
UNA = sum(1 for c in conc if c['cur'] == 1)
PREF = sum(1 for c in conc if not c['cerrada'])
dep = collections.defaultdict(lambda: {'cur': 0, 'mun': 0, 'uno': 0})
for c in conc:
    x = dep[c['dep']]; x['cur'] += c['cur']; x['mun'] += 1; x['uno'] += c['cur'] == 1
CARIBE = ['CÓRDOBA', 'BOLÍVAR', 'SUCRE', 'MAGDALENA', 'ATLÁNTICO', 'CESAR', 'LA GUAJIRA']
ANDES = ['SANTANDER', 'ANTIOQUIA', 'BOYACÁ']
CUR_CAR = sum(dep[d]['cur'] for d in CARIBE); CUR_AND = sum(dep[d]['cur'] for d in ANDES)
alc = [a for a in nl['alcaldes'] if a['k'] != '16001']
ALC = len(alc); ALC_PROPIA = sum(1 for a in alc if not a['coal'])
DIP = sum(x['cur'] for x in nl['diputados']); DIP_DEP = len(nl['diputados'])
DIP_PROPIA = sum(x['cur'] for x in nl['diputados'] if not x['coal'])
dip_propia_dep = [tc(x['dep']) for x in nl['diputados'] if not x['coal']]
assert (CUR, MUN, PROPIA, COAL, UNA) == (246, 185, 233, 13, 134), (CUR, MUN, PROPIA, COAL, UNA)
assert (ALC, ALC_PROPIA, DIP, DIP_DEP, DIP_PROPIA) == (10, 8, 7, 6, 3)

# ── cifras: escenarios (qué tan cerca quedó cada lista) ──────────────────────
F = esc['fuera']['filas']; RF = esc['fuera']['resumen']
LISTAS = RF['listas']; SIN = sum(1 for x in F if not x['k'])
cerca = sorted([x for x in F if not x['k'] and x['falta'] is not None and x['falta'] <= 300], key=lambda x: x['falta'])
CERCA = len(cerca); assert CERCA == RF['sin_curul_a_300'] == 99
con = [x for x in F if x['k']]
COL300 = sum(1 for x in con if x['colchon'] is not None and x['colchon'] <= 300)
COL100 = sum(1 for x in con if x['colchon'] is not None and x['colchon'] <= 100)
POB_MED = sorted(x['pob'] or 0 for x in con)[len(con) // 2]
NO_UMBRAL = sum(1 for x in F if not x['pasa'])
fuerte = [x for x in F if x['pct'] >= .10 and x['votos'] / x['pct'] >= 5000]
FUERTE = len(fuerte); assert FUERTE == 55 and all(x['k'] for x in fuerte)
def depn(s):   # «La Hormiga) (Putumayo» → Putumayo
    return re.sub(r'^.*\(', '', s).strip() or 'Sin departamento'
fu_dep = collections.Counter(tc(depn(x['dep'])) for x in fuerte)
ce_dep = collections.Counter(tc(depn(x['dep'])) for x in cerca if depn(x['dep']) != 'Sin departamento')
DEPS_LISTA = {tc(depn(x['dep'])) for x in F}; assert 'Amazonas' not in DEPS_LISTA and 'Vaupés' not in DEPS_LISTA
assert sum(1 for x in F if depn(x['dep']) == 'Meta') == 7 and not any(x['k'] for x in F if depn(x['dep']) == 'Meta')
M = {x['mun']: x for x in F}
def cap(m): x = M[m]; return x
VOT_SIN = sum(x['votos'] for x in F if not x['k'])

# ── cifras: tablero (cómo se movió cada electorado fuera de Bogotá) ──────────
R = tab['territorios']['Resto del país']; s1 = R['s1']
def pc(Mx, r, c): return Mx['flujo'][Mx['filas'].index(r)][Mx['cols'].index(c)] / Mx['tot_filas'][Mx['filas'].index(r)]
def margen(Mx, r, c): i, j = Mx['filas'].index(r), Mx['cols'].index(c); return Mx['lo'][i][j], Mx['hi'][i][j]
LIB = pc(s1, 'liberal', 'novoto'); LIB_LO, LIB_HI = margen(s1, 'liberal', 'novoto')
CON = pc(s1, 'conservador', 'novoto'); UU = pc(s1, 'u', 'novoto')
PAC = pc(s1, 'pacto', 'cepeda'); CDA = pc(s1, 'cd', 'abelardo')
pcar = tab['participacion']['Caribe']; CAR_SEN = pcar['senado'] / pcar['censo']; CAR_V1 = pcar['v1'] / pcar['censo']
AHORA = s1['tot_filas'][s1['filas'].index('ahora')]

# ── cifras: clima (agenda de prensa) ─────────────────────────────────────────
tr = {t['k']: t for t in amb['resto']['temas']}
SEG, SAL, COR, COR_NEG = tr['seguridad']['pct'], tr['salud']['pct'], tr['corrupcion']['pct'], tr['corrupcion']['neg']
VIAS = tr['movilidad']['pct'] + tr['infraestructura']['pct']
camb = {c['tema']: c for c in cli['agenda']['cambio']}
JUS_INI, JUS_FIN = camb['justicia']['ini'], camb['justicia']['fin']
ECO_INI, ECO_FIN = camb['empleo_economia']['ini'], camb['empleo_economia']['fin']
SEM = len(cli['agenda']['semanas']); SEM_SEG = camb['seguridad']['sem_lider']
ep = cli['episodios']; EP_MED = ep['todos']['mediana']; EP_MAS7 = ep['todos']['mas7']; EP_SEG = ep['por_tema']['seguridad']['mediana']
EP_TERR = next(e['dur'] for e in ep['lista'] if (e.get('titulo') or '').startswith('Terremoto'))
fz = {g['k']: g['total'] for g in cli['fuerzas']['lista']}; TIT = cli['cobertura']['unicos']; NL_TIT = fz['nl']
CRI = cli['crisis']
iv = amb['encuestas']['invamer']; INV_SAL = dict(iv['urgentes'])['Salud']; INV_SEG = dict(iv['urgentes'])['Inseguridad']; INV_EST = iv['estado_perdio_presencia']

def lugares_dep(ds):
    return [f"{tc(d)}: {dep[d]['cur']} curules en {dep[d]['mun']} municipios" for d in ds]

E = {
 'v': '2026-11-10', 'ambito': 'resto',
 'frase': 'La red de concejales que cumple y rinde cuentas',
 'idea': 'Fuera de Bogotá el partido se gana municipio a municipio, no por opinión. La estrategia es volver una red a sus concejales sueltos, con un mismo sello: no le deben la curul a nadie, muestran logros pequeños con prueba y rinden cuentas cada mes.',
 'nota_eje': 'Es la versión regional de «independencia que cumple». En un municipio la independencia no se declara frente a un polo nacional: se demuestra frente a las estructuras locales, con las cuentas a la vista.',
 'por_que': [
  {'t': 'Es una presencia de personas, no de marca',
   'x': f'Fuera de Bogotá el partido tiene curul en {MUN} municipios y en {UNA} de ellos hay un solo concejal. Casi todas las listas fueron con voto preferente ({PREF} de {MUN}), así que cada curul la ganó alguien con votos propios. Hoy eso es una suma de trayectorias individuales: lo único que las une es el aval.',
   'dato': f'{CUR} curules de concejo estimadas en {MUN} municipios; {UNA} con una sola; {PROPIA} en lista propia y {COAL} en coalición.', 'mod': 'inventario'},
  {'t': 'El mapa real no es el de la marca',
   'x': f'El partido se piensa urbano y de opinión, pero su fuerza regional está en municipios medianos y pequeños: la mitad de los que tienen curul no pasa de {n(POB_MED)} habitantes. Pesa en el Caribe ({CUR_CAR} curules) y en Santander, Antioquia y Boyacá ({CUR_AND}). En las capitales grandes casi no existe: Cali {p(cap("Cali")["pct"],1)}, Cúcuta {p(cap("Cucuta")["pct"],1)}, Bucaramanga {p(cap("Bucaramanga")["pct"],1)}.',
   'dato': f'Caribe {CUR_CAR} y Santander, Antioquia y Boyacá {CUR_AND} de las {CUR} curules. Sin lista al concejo en 2023 en Medellín, Barranquilla, Pereira, Armenia, Neiva, Santa Marta, Valledupar y Tunja.', 'mod': 'escenarios'},
  {'t': 'Todo se decide por pocos votos',
   'x': f'En {CERCA} municipios la lista se quedó a menos de 300 votos de su primera curul. Y en {COL300} de los {MUN} donde sí eligió, la última curul se sostiene con 300 votos o menos de ventaja. Con márgenes así el resultado no depende de la conversación nacional: depende de organización, de candidatos con arraigo y de quién sale a votar.',
   'dato': f'{CERCA} municipios sin curul a menos de 300 votos de la primera; {COL300} con curul y ventaja de 300 votos o menos ({COL100} con 100 o menos). Curules estimadas, no la declaratoria.', 'mod': 'escenarios'},
  {'t': 'El votante de octubre no es el de la presidencial',
   'x': f'En las territoriales vuelve a votar gente que en la presidencial se quedó en casa. Fuera de Bogotá, {p(LIB)} del voto liberal de marzo no votó en primera vuelta, y pasó algo parecido con el conservador ({p(CON)}) y el de la U ({p(UU)}). En el Caribe votó más gente al Senado que a la presidencia. A ese votante lo mueven estructuras locales, no los polos.',
   'dato': f'Voto liberal al Senado fuera de Bogotá que no votó en primera vuelta: {p(LIB)} (margen de {p(LIB_LO)} a {p(LIB_HI)}, estimación del modelo). Caribe: votó {p(CAR_SEN,1)} del censo al Senado y {p(CAR_V1,1)} en primera vuelta.', 'mod': 'tablero'},
 ],
 'lugar': {
  'x': f'En un municipio el partido no compite por ideología: compite por confianza. El lugar que puede ocupar es simple y hoy está libre: el concejal que no le debe la curul a ninguna casa política y por eso puede mostrar sus cuentas. Es la independencia nacional llevada a escala local. La marca casi no llega por la prensa ({NL_TIT} de {n(TIT)} titulares), así que ese lugar lo construye cada elegido en su territorio y el partido lo vuelve sello común.',
  'propios': [
   {'tema': 'Cuentas claras del municipio',
    'x': 'Legalidad y anticorrupción en versión local: contratos, obras inconclusas y plata de regalías, siempre con el documento en la mano. Es un terreno con poca competencia y mucho rechazo ciudadano.',
    'dato': f'La corrupción es {p(COR,1)} de los titulares de asuntos públicos fuera de Bogotá y {p(COR_NEG)} de ellos tiene tono negativo.'},
   {'tema': 'Control político que se ve',
    'x': 'El concejal que cita, pregunta y publica la respuesta. Tomar posición con un dato propio es la forma de existir sin presupuesto ni pauta.',
    'dato': f'La justicia pasó de {p(JUS_INI,1)} a {p(JUS_FIN,1)} de la agenda entre el primer y el último tercio del semestre: los temas de instituciones van subiendo.'},
  ],
  'consenso': [
   {'tema': 'Seguridad',
    'x': 'Todos la quieren y el gobierno nacional la reclama. El partido entra por la presencia del Estado y la legalidad en el municipio (policía, alumbrado, inspección, justicia cercana), no por la mano dura.',
    'dato': f'Primer tema de la prensa en {SEM_SEG} de {SEM} semanas. {p(INV_EST,1)} cree que el Estado perdió presencia en zonas con grupos ilegales (Invamer, mayo de 2026).'},
   {'tema': 'Salud',
    'x': 'Es lo más urgente para la gente y casi nadie lo trabaja desde lo local. El concejal puede vigilar el hospital, el puesto de salud y la ambulancia, y decir con claridad qué depende del municipio y qué no.',
    'dato': f'{p(INV_SAL,1)} la pone entre lo más urgente (Invamer); en la prensa pesa {p(SAL,1)} de los titulares.'},
   {'tema': 'Vías y servicios públicos',
    'x': 'El tema de cada departamento es distinto (el agua, la vía, la tarifa) y ahí se mide al concejal. No hace falta una línea nacional: hace falta estar en el tema del municipio con una gestión que se pueda probar. Criterio de oficio.',
    'dato': f'Movilidad e infraestructura suman {p(VIAS,1)} de los titulares fuera de Bogotá.'},
  ],
  'ceder': [
   {'tema': 'La pelea entre gobierno y oposición',
    'x': f'Los dos polos no se movieron y tienen dueño: fuera de Bogotá, {p(PAC)} del voto del Pacto fue con Cepeda y {p(CDA)} del Centro Democrático con De la Espriella. Entrar ahí le quita al candidato local su único activo, que es no deberle nada a nadie.'},
   {'tema': 'La mano dura',
    'x': 'Es el tema del gobierno nacional y de la derecha. Competir ahí es jugar en cancha ajena y con las reglas de otro.'},
  ],
  'refs': ['T1', 'T2', 'T3'],
 },
 'pilares': [
  {'t': f'Una red, no {CUR} curules sueltas',
   'x': 'Cada concejal ya está en campaña permanente desde su curul; falta que se note y que sume. El sello común son tres hábitos: logros pequeños anunciados uno por uno, una rendición de cuentas al mes en su territorio y una posición pública con dato propio. El partido los recoge y los muestra como red. Así la marca nacional le sirve al candidato local, y no al revés.',
   'como': ['Una pieza de crédito por semana por concejal: un logro con fecha y prueba. Cuenta más cuántas veces que el tamaño.',
            'Un encuentro mensual de rendición de cuentas en el municipio, con un compromiso que se pueda verificar. No un mitin.',
            'Un tablero regional del partido que junte esos logros por departamento y los publique con el mismo formato.'],
   'principio': 'A7', 'refs': ['T19', 'T20', 'T21', 'R3.1', 'R3.2'], 'oficio': False},
  {'t': 'Concentrar: retener primero, crecer después',
   'x': f'En 2023 el partido presentó {LISTAS} listas fuera de Bogotá y {SIN} no eligieron a nadie. Con recursos escasos el orden importa: primero cuidar las curules que penden de pocos votos, luego ir por los municipios que se quedaron a un paso y solo después abrir plaza nueva. El contacto de campaña casi no persuade a quien no conoce al candidato, así que no rinde gastar donde no hay base.',
   'como': [f'Plan de defensa, municipio por municipio, de las {COL300} curules que se sostienen con 300 votos o menos.',
            f'Candidato y equipo definidos antes de marzo de 2027 en los {CERCA} municipios que quedaron a menos de 300 votos.',
            'Línea de base por puesto de votación en cada municipio foco, para medir después qué movió la presencia.'],
   'principio': 'A6', 'refs': ['T14', 'T17', 'T18'], 'oficio': False},
  {'t': 'Candidatos con voto propio y una sola regla para las listas',
   'x': 'Con voto preferente la curul la gana la persona, y el rival más cercano suele estar en la misma lista. El aval va a quien tenga arraigo medible y acepte el sello de cuentas claras. Para escoger entre lista propia y coalición, la misma regla en todos los departamentos: lista propia donde el partido ya pasa el umbral solo; coalición solo donde no lo pasa, con su nombre en la lista y la curul acordada por escrito.',
   'como': ['Medir por puesto lo que rinde cada aspirante y cada líder antes de entregar el aval.',
            'Revisar en cada municipio y departamento si la suma con el aliado cabe en el 15 % que permite la ley para coaliciones.',
            'Buscar desde ya a las candidatas: la cuota del 30 % aplica a todos los concejos y una lista que no la cumple se cae.'],
   'principio': 'A1', 'refs': ['T3', 'R3.3'], 'oficio': True},
  {'t': 'Movilizar al votante local, casa por casa',
   'x': f'En un municipio de {n(POB_MED)} habitantes la elección la define quién sale a votar. Lo que rinde es el contacto personal de alguien conocido, que además llega a todo el hogar. La pauta casi no mueve preferencias y su efecto dura pocos días. La campaña regional es una red de hogares por puesto de votación, no una campaña de medios.',
   'como': ['Ubicar desde ahora los hogares y las comunidades donde ya votan por el concejal: son la base de octubre.',
            'Visita cara a cara en campaña: cómo se marca el voto preferente en el tarjetón y cómo llegar al puesto.',
            'Guardar la pauta para las últimas semanas y usar las redes para que la base reparta lo que ya se hizo.'],
   'principio': 'A5', 'refs': ['T13', 'T15', 'T16', 'T24', 'R2.2'], 'oficio': False},
  {'t': 'Alcaldías y asambleas como ancla',
   'x': f'Fuera de Bogotá el partido tiene {ALC} alcaldes y {DIP} diputados. Son su vitrina: el votante juzga por lo que ve, y una alcaldía bien contada vale más que cualquier mensaje. Los alcaldes no pueden repetir, así que lo que se hereda es la gestión. La asamblea da escala donde hay densidad: en {", ".join(dip_propia_dep[:-1])} y {dip_propia_dep[-1]} eligió diputado con lista propia.',
   'como': ['Cada alcaldía con un balance público de lo cumplido, que diga qué dependía del municipio y qué no.',
            'Lista propia a la asamblea donde hay concejales en muchos municipios; en el resto, la misma regla de coalición.',
            'Los diputados como enlace de la red: llevan a la asamblea lo que un concejal no puede resolver solo.'],
   'principio': 'A7', 'refs': ['R3.4', 'T19', 'T20'], 'oficio': True},
 ],
 'audiencias': [
  {'quien': 'Quien ya vota por el concejal del partido',
   'donde': f'Los {MUN} municipios con curul; sobre todo Antioquia, Santander, Córdoba y Bolívar',
   'cuadrante': 'retener',
   'decir': 'Esto conseguí, esto falta y esto no depende de mí. Todavía no se pide el voto: se rinden cuentas.',
   'refs': ['T14', 'T21', 'R3.1']},
  {'quien': 'Los municipios donde la lista ya es una fuerza',
   'donde': f'{FUERTE} municipios donde pasó el 10 %: ' + ', '.join(f'{d} ({c})' for d, c in fu_dep.most_common(6)),
   'cuadrante': 'retener-crecer',
   'decir': 'Ya somos parte del concejo. El paso que sigue es la alcaldía o la asamblea, con las mismas cuentas claras.',
   'refs': ['T21', 'R3.2']},
  {'quien': 'El votante de las estructuras tradicionales',
   'donde': 'El Caribe y los municipios donde el Senado se vota más que la presidencia',
   'cuadrante': 'conocer',
   'decir': 'No se le pide cambiar de bando. Se le muestra lo que puede perder si nadie vigila la plata del municipio, en reuniones pequeñas y con una propuesta concreta.',
   'refs': ['R3.2', 'R3.5', 'T6']},
  {'quien': 'El votante de opinión de las capitales intermedias',
   'donde': 'Montería, Manizales, Sincelejo, Popayán, Pasto, Ibagué y Cartagena, donde ya hay curul',
   'cuadrante': 'conocer',
   'decir': 'Un tema de ciudad con un dato que nadie más tiene. Aquí la marca del partido sí suma.',
   'refs': ['T1', 'T2', 'T20']},
  {'quien': 'Las grandes capitales sin base',
   'donde': 'Cali, Cúcuta, Medellín y Barranquilla',
   'cuadrante': 'no-gastar',
   'decir': 'Nada por ahora. Sin un candidato con votos propios ya medidos, el esfuerzo rinde más en otra parte.',
   'refs': ['T14']},
 ],
 'relato': {
  'yo': 'A mí me eligieron sin deberle la curul a ninguna casa política. Por eso puedo mostrar en qué voté, qué pedí y qué conseguí.',
  'nosotros': 'Somos los municipios donde las cosas se deciden lejos y se pagan cerca: la vía, el puesto de salud, el agua. Aquí todos sabemos quién cumple y quién aparece cada cuatro años.',
  'ahora': 'En octubre de 2027 se eligen los concejos que van a vigilar cuatro años de plata del municipio. Es el momento de poner ahí a alguien que rinda cuentas.',
  'refs': ['T8', 'T7'],
 },
 'contraste': [
  {'frente': 'Las estructuras tradicionales del municipio',
   'x': 'Con un hecho que cualquiera pueda comprobar: nuestras cuentas están publicadas, pidan las de los demás. Sin nombres propios ni acusaciones sin documento: el ataque no rinde más y se devuelve.'},
  {'frente': 'Los dos polos nacionales',
   'x': 'No se contrasta: se declina la pelea. El concejal responde por su municipio; del gobierno nacional apoya lo que sirve aquí y vigila lo que no.'},
  {'frente': 'Los aliados de coalición',
   'x': 'Sin pelea y con reglas: el nombre del partido visible en la lista y en la publicidad, y el reparto de la curul escrito antes de inscribir.'},
  {'frente': 'Los rivales de la propia lista',
   'x': 'Con voto preferente se compite adentro. El contraste es el trabajo hecho, con fechas; nunca contra el compañero de lista.'},
 ],
 'fases': [
  {'fase': 'Posicionamiento', 'desde': '2026-11-10', 'hasta': '2027-02-28',
   'foco': 'Armar la red y decidir dónde se juega. La persuasión se hace ahora; en campaña casi no mueve a nadie.',
   'acciones': ['Censo real de concejales, alcaldes y diputados, para reemplazar la estimación de esta presentación.',
                'Mapa por departamento: qué se retiene, dónde se crece, dónde se abre y dónde no se gasta.',
                'Arranca el sello: crédito semanal y rendición de cuentas mensual de cada elegido.',
                'Línea de base por puesto de votación en los municipios foco.']},
  {'fase': 'Precampaña', 'desde': '2027-03-01', 'hasta': '2027-07-30',
   'foco': 'Cerrar candidatos, listas y coaliciones con la misma regla en todo el país.',
   'acciones': ['Avales con medición por puesto y filtro de antecedentes.',
                'Decisión de lista propia o coalición, departamento por departamento.',
                'Listas completas y con cuota de género, inscritas entre el 30 de junio y el 30 de julio de 2027.',
                'Red de hogares que van a movilizar en octubre.']},
  {'fase': 'Campaña', 'desde': '2027-07-31', 'hasta': '2027-10-23',
   'foco': 'Movilizar a quien ya prefiere al candidato y sostener los temas propios.',
   'acciones': ['Contacto cara a cara en los hogares donde ya hay voto.',
                'Crédito frecuente: muchos logros pequeños, cada uno con su prueba.',
                'La pauta, solo en las últimas semanas.']},
  {'fase': 'Día D', 'desde': '2027-10-24', 'hasta': '2027-10-31',
   'foco': 'Sacar a votar y cuidar cada voto: aquí se gana o se pierde por decenas.',
   'acciones': ['Transporte y recordatorio por hogar, sin revelar nunca quién votó.',
                'Enseñar a marcar el tarjetón: logo del partido y número del candidato.',
                f'Testigos primero en los municipios de margen corto: {COL100} curules con 100 votos o menos de ventaja y {CERCA} a menos de 300 de la primera.']},
 ],
 'agenda': [
  {'si': 'Cuando la agenda regional esté en seguridad y orden público',
   'haz': 'Entra por la presencia del Estado en el municipio: qué pidió el concejal (policía, alumbrado, inspección), a quién y en qué fecha.',
   'no': 'No compitas en mano dura ni comentes cada hecho.',
   'dato': f'Es {p(SEG,1)} de los titulares fuera de Bogotá, pero una historia de seguridad dura {EP_SEG} días en la mediana.'},
  {'si': 'Cuando salte un caso de corrupción local o departamental',
   'haz': 'Es el terreno propio: hay que estar siempre. Pide el contrato, publica el dato y propón el control. El concejal del partido habla primero.',
   'no': 'No acuses a personas sin documento ni lo vuelvas pelea entre partidos.',
   'dato': f'{p(COR_NEG)} de los titulares de corrupción tiene tono negativo, y en el banco ninguno nombra al partido.'},
  {'si': 'Cuando el tema sea la salud: el hospital, la EPS, la ambulancia',
   'haz': 'Debate de control en el concejo, visita al puesto de salud y un compromiso con fecha. Explica qué controla el municipio.',
   'no': 'No prometas lo que depende de la Nación.',
   'dato': f'{p(INV_SAL,1)} la pone entre lo más urgente (Invamer) y solo pesa {p(SAL,1)} de los titulares: hay demanda y poco dueño.'},
  {'si': 'Cuando estalle un escándalo nacional, del gobierno o de la oposición',
   'haz': 'Una frase de independencia y de vuelta al tema del municipio.',
   'no': 'No gastes la semana ni te alinees con un polo.',
   'dato': f'La historia típica dura {EP_MED} días y solo {p(EP_MAS7)} pasa de una semana. La crisis del entorno de Petro estuvo en titulares {CRI["semanas_con"]} de {SEM} semanas porque un caso releva al otro: nunca termina, y no es del partido.'},
  {'si': 'Cuando haya una emergencia: invierno, sequía, un sismo, una vía caída',
   'haz': 'Presencia y gestión: el concejal como enlace con la alcaldía y la gobernación, y después el crédito por cada gestión cumplida.',
   'no': 'No aparezcas sin una gestión que mostrar.',
   'dato': f'Las emergencias son las historias que más duran: la del terremoto de agosto estuvo {EP_TERR} días en titulares, contra {EP_MED} de la historia típica.'},
  {'si': 'Cuando el tema sea el bolsillo: empleo, tarifas, el precio de la cosecha',
   'haz': 'Toma posición con una cifra del municipio y una propuesta que el concejo sí pueda aprobar.',
   'no': 'No hables de la economía como algo que nadie decide: señala quién responde.',
   'dato': f'Economía y empleo pasó de {p(ECO_INI,1)} a {p(ECO_FIN,1)} de la agenda entre el primer y el último tercio del semestre.'},
 ],
 'riesgos': [
  {'r': 'El elegido con voto propio se va con su voto, o no aspira.',
   'manejo': 'Aval temprano y reglas de renglón claras. El plazo para renunciar a la curul y cambiar de partido venció el 30 de junio de 2026: quien hoy es concejal del partido ya no puede inscribirse por otro, y quien tiene curul de otro partido tampoco puede llegar.'},
  {'r': 'La coalición borra la marca.',
   'manejo': f'En 2023 solo {COAL} de {CUR} curules de concejo salieron de coalición, pero {DIP - DIP_PROPIA} de {DIP} diputados sí. La regla: nombre visible, curul acordada por escrito y coalición solo donde el partido no pasa el umbral.'},
  {'r': 'Un aval a quien trae votos pero no cumple el sello daña el tema propio.',
   'manejo': 'Filtro de antecedentes antes del aval y compromiso firmado de rendir cuentas. Un solo caso basta para vaciar el discurso de cuentas claras. Criterio de oficio.'},
  {'r': 'La dispersión: muchas listas y pocos votos por lista.',
   'manejo': f'En 2023, {SIN} de {LISTAS} listas no eligieron y {NO_UMBRAL} no pasaron el umbral. Menos listas, mejor escogidas, salvo donde una lista corta ayude a un candidato a alcaldía.'},
  {'r': 'Decidir con cifras estimadas.',
   'manejo': f'Las curules de esta presentación salen de aplicar la regla al consolidado, no de la declaratoria; {RF["con_dudas"]} municipios tienen dudas de tamaño del concejo. Antes de asignar recursos se verifica con el censo real del partido.'},
  {'r': 'La marca nacional no ayuda porque no se ve.',
   'manejo': f'El partido aparece en {NL_TIT} de {n(TIT)} titulares. No se resuelve con pauta: se resuelve con la red contando lo que hace cada semana.'},
 ],
 'medir': [
  {'que': 'Curules de margen corto que se sostienen', 'como': f'De las {COL300} con 300 votos o menos de ventaja, cuántas tienen candidato y equipo en marzo de 2027 y cuántas se conservan en octubre.'},
  {'que': 'Municipios a un paso que cruzan', 'como': f'De los {CERCA} a menos de 300 votos, cuántos inscriben lista con candidato medido y cuántos eligen.'},
  {'que': 'El sello funcionando', 'como': 'Rendiciones de cuentas hechas por mes y piezas de crédito publicadas por concejal, contadas en el tablero regional.'},
  {'que': 'La marca en las listas', 'como': f'Proporción de curules en lista propia (en 2023: {PROPIA} de {CUR}) y coaliciones con el nombre del partido visible.'},
  {'que': 'Movilización', 'como': 'Participación por puesto en los municipios foco frente a 2023, comparando puestos con y sin trabajo de campaña.'},
  {'que': 'Presencia en la conversación regional', 'como': f'Titulares que nombran al partido o a sus elegidos en medios regionales. Hoy: {NL_TIT} de {n(TIT)}.'},
 ],
 'territorios': [
  {'grupo': 'Retener',
   'x': 'Departamentos donde el partido ya es una presencia densa. Aquí se defiende lo ganado y se pide más: alcaldías y asamblea.',
   'lugares': lugares_dep(['ANTIOQUIA', 'SANTANDER', 'CÓRDOBA', 'BOLÍVAR', 'BOYACÁ', 'CALDAS', 'SUCRE', 'CASANARE', 'MAGDALENA']) + [
     f'Montería: {cap("Monteria")["k"]} de {cap("Monteria")["n"]} curules con {p(cap("Monteria")["pct"],1)}',
     f'Manizales: {cap("Manizales")["k"]} de {cap("Manizales")["n"]} con {p(cap("Manizales")["pct"],1)}',
     'Alcaldías: ' + ', '.join(tc(a['mun']) for a in alc)]},
  {'grupo': 'Crecer',
   'x': 'Municipios donde la lista se quedó a menos de 300 votos de su primera curul. Es donde menos votos separan al partido de tener concejal.',
   'lugares': [f'{d}: {c} municipios' for d, c in ce_dep.most_common(9)] + [
     f'{m}: a {votos(cap(k)["falta"])}' for m, k in [('Salamina (Caldas)', 'Salamina'), ('Socorro (Santander)', 'Socorro'), ('Segovia (Antioquia)', 'Segovia'),
                                                  ('El Carmen de Viboral (Antioquia)', 'Carmen De Viboral'), ('Lebrija (Santander)', 'Lebrija'),
                                                  ('Sabaneta (Antioquia)', 'Sabaneta'), ('La Dorada (Caldas)', 'La Dorada')]] + [
     f'Yopal (Casanare): a {votos(cap("Yopal")["falta"])} de la segunda curul']},
  {'grupo': 'Abrir',
   'x': 'Capitales donde ya hay una curul o una base que pasó el umbral, y donde un tema de ciudad puede rendir. Se entra con candidato medido, no con lista de relleno.',
   'lugares': [f'{nm}: {cap(k)["k"]} curul con {p(cap(k)["pct"],1)}' for nm, k in [('Sincelejo', 'Sincelejo'), ('Popayán', 'Popayan'), ('Riohacha', 'Riohacha'), ('Quibdó', 'Quibdo'),
                                                                               ('Pasto', 'Pasto'), ('Ibagué', 'Ibague'), ('Cartagena', 'Cartagena')]] + [
     f'Bucaramanga: sin curul, {p(cap("Bucaramanga")["pct"],1)}, a {n(cap("Bucaramanga")["falta"])} votos; es la capital del departamento con más municipios del partido',
     'Meta: 7 listas en 2023 y ninguna curul; 2 municipios a menos de 300 votos']},
  {'grupo': 'No gastar',
   'x': 'Plazas grandes donde el partido no pasó el umbral o no tuvo lista. Sin un candidato con votos propios ya medidos, el esfuerzo rinde más en otra parte.',
   'lugares': [f'Cali: {p(cap("Cali")["pct"],1)}, a {n(cap("Cali")["falta"])} votos de una curul',
               f'Cúcuta: {p(cap("Cucuta")["pct"],1)}, a {n(cap("Cucuta")["falta"])} votos',
               f'Villavicencio: {p(cap("Villavicencio")["pct"],1)}, a {n(cap("Villavicencio")["falta"])} votos',
               'Sin lista al concejo en 2023: Medellín, Barranquilla, Pereira, Armenia, Neiva, Santa Marta, Valledupar y Tunja',
               'Sin ninguna lista al concejo en 2023: Amazonas y Vaupés']},
 ],
}

# ── referencias: solo fichas del banco ───────────────────────────────────────
FICHAS = {f['id']: f for f in banco['fichas']}; PRINC = {x['id'] for x in banco['principios']}
usadas = []
def junta(ids):
    for i in ids:
        if i not in FICHAS: sys.exit(f'ficha inexistente en el banco: {i}')
        if i not in usadas: usadas.append(i)
junta(E['lugar']['refs']); junta(E['relato']['refs'])
for x in E['pilares']:
    if x['principio'] not in PRINC: sys.exit('principio inexistente: ' + x['principio'])
    junta(x['refs'])
for x in E['audiencias']: junta(x['refs'])
orden = [f['id'] for f in banco['fichas']]
E['refs'] = [{'id': i, 'corto': FICHAS[i]['corto'], 'texto': ' / '.join(r['texto'] for r in FICHAS[i]['refs']),
              'doi': next((r['doi'] for r in FICHAS[i]['refs'] if r.get('doi')), None)} for i in sorted(usadas, key=orden.index)]
A = banco['advertencias']
E['advertencias'] = [A[1], A[2], A[4]]

# ── validación de forma ──────────────────────────────────────────────────────
pal = lambda s: len(s.split())
err = []
if pal(E['frase']) > 10: err.append('frase larga')
if pal(E['idea']) > 45: err.append(f'idea {pal(E["idea"])} palabras')
for x in E['por_que']:
    if not 40 <= pal(x['x']) <= 70: err.append(f'por_que «{x["t"]}»: {pal(x["x"])}')
if not 60 <= pal(E['lugar']['x']) <= 90: err.append(f'lugar.x: {pal(E["lugar"]["x"])}')
for x in E['pilares']:
    if not 50 <= pal(x['x']) <= 80: err.append(f'pilar «{x["t"]}»: {pal(x["x"])}')
    if len(x['como']) != 3: err.append('como != 3')
CUAD = set(banco['cuadrantes'])
for x in E['audiencias']:
    if x['cuadrante'] not in CUAD: err.append('cuadrante ' + x['cuadrante'])
txt = json.dumps(E, ensure_ascii=False)
if '—' in txt: err.append('hay guion largo')
if err: sys.exit('REVISAR:\n  ' + '\n  '.join(err))

out = os.path.join(D, 'estrategia-resto.json')
json.dump(E, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
t = open(out, encoding='utf-8').read().strip(); json.loads(t)
open(os.path.join(D, 'estrategia-resto.js'), 'w', encoding='utf-8').write("window.NLD=window.NLD||{};window.NLD['estrategia-resto']=" + t + ';\n')
print('ok ·', len(E['refs']), 'fichas ·', round(len(t) / 1024), 'KB')
print('idea', pal(E['idea']), '· por_que', [pal(x['x']) for x in E['por_que']], '· lugar', pal(E['lugar']['x']), '· pilares', [pal(x['x']) for x in E['pilares']])
