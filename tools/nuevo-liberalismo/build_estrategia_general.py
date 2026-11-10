#!/usr/bin/env python3
"""Estrategia GENERAL del Nuevo Liberalismo para las territoriales de 2027 (módulo 05).
El texto es redacción propia; las cifras se leen de los datos de la presentación y las referencias
se copian del banco de estrategia de Candidato 360 (candidato-360-data/estrategia-banco.json).
Escribe datos/estrategia-general.json y .js. Valida: ids de fichas y principios, longitudes y sin rayas.
Correr después de build_tablero / build_inventario / build_clima / build_clima_ambito / build_escenarios."""
import json, os, re, sys

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
D = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos')
L = lambda n: json.load(open(os.path.join(D, n + '.json'), encoding='utf-8'))
BANCO = json.load(open(os.path.join(RAIZ, 'candidato-360-data', 'estrategia-banco.json'), encoding='utf-8'))
T, INV, CL, AMB, ES, SH = L('tablero'), L('inventario'), L('clima'), L('clima-ambito'), L('escenarios'), L('senado-historico')

# ── formato ──────────────────────────────────────────────────────────────────
def p(x, d=1): return f'{x * 100:.{d}f}'.replace('.', ',') + '%'
def n(x): return f'{int(round(x)):,}'.replace(',', '.')

# ── cifras (todas de los datos; nada de memoria) ─────────────────────────────
s1, v12 = T['territorios']['Colombia']['s1'], T['territorios']['Colombia']['v12']
pc = lambda M, r, c: M['flujo'][M['filas'].index(r)][M['cols'].index(c)] / M['tot_filas'][M['filas'].index(r)]
c1 = T['bogota_camara']['c1']; jp = c1['cols'].index('paloma')
nl_pal, nl_lo, nl_hi, nl_cam = c1['flujo'][0][jp] / c1['tot_filas'][0], c1['lo'][0][jp], c1['hi'][0][jp], c1['tot_filas'][0]

R = INV['resumen']; NL = INV['nl']
conc_coal = sum(x['cur'] for x in NL['concejales'] if x['coal'])
fuera = [x for x in NL['concejales'] if x['k'] != '16001']
fuera_uno = sum(1 for x in fuera if x['cur'] == 1)
alc_prop = R['alcaldes'] - R['alcaldes_coal']
RF = ES['fuera']['resumen']
bog_votos = ES['escenarios']['techo']['votos']
bog_peso = bog_votos / (bog_votos + RF['votos'])

nodo = lambda anio, lin: next(x for c in SH['columnas'] if c['anio'] == anio for x in c['nodos'] if x['linaje'] == lin)
nl22, ah26 = nodo(2022, 'nl'), nodo(2026, 'ahora')

cob = CL['cobertura']; ag = CL['agenda']
cam = {c['tema']: c for c in ag['cambio']}
pub = cob['publico']; peso = {k: sum(v) / pub for k, v in ag['conteo'].items()}
orden_pub = sorted([k for k in ag['part']], key=lambda k: -peso[k])
puesto_salud = orden_pub.index('salud') + 1
jc_ini, jc_fin = cam['justicia']['ini'] + cam['corrupcion']['ini'], cam['justicia']['fin'] + cam['corrupcion']['fin']
tono = {t['tema']: t for t in CL['tono']}
ep, ept = CL['episodios']['todos'], CL['episodios']['por_tema']
fz = {g['k']: g for g in CL['fuerzas']['lista']}
nl_tit = fz['nl']['total']; nl_temas = dict(fz['nl']['temas'])
assert nl_temas.get('justicia', 0) == 0 and nl_temas.get('corrupcion', 0) == 0
cr = CL['crisis']
n_medios = len(cob['medios']); n_reg = sum(1 for m in cob['medios'] if not m['nacional'])
inv_ = AMB['encuestas']['invamer']; urg = dict(inv_['urgentes'])
ordinal = {1: 'primer', 2: 'segundo', 3: 'tercer', 4: 'cuarto', 5: 'quinto', 6: 'sexto', 7: 'séptimo', 8: 'octavo', 9: 'noveno'}
sem_seg = cam['seguridad']['sem_lider']; n_sem = len(ag['semanas'])

cal = {h['h']: h for h in ES['calendario']['hitos']}
f_abre = cal['Abre la inscripción de candidatos y listas']['f']; f_cierra = cal['Cierra la inscripción de candidatos']['f']
f_ced = cal['Cierra la inscripción de cédulas']['f']; f_elec = cal['Elección']['f']
assert (f_abre, f_cierra, f_ced, f_elec) == ('2027-06-30', '2027-07-31', '2027-08-31', '2027-10-31')
fases_b = {f['id']: f for f in BANCO['calendario']['fases']}

E = {
 'v': '2026-11-10', 'ambito': 'general',
 'frase': 'Independencia que cumple: sin deudas con nadie, con resultados locales',
 'idea': 'En un país dividido en dos bandos, el Nuevo Liberalismo es el partido que no le debe nada a ninguno: por eso puede exigirles a los dos. Su tema es la legalidad y su prueba es local: resultados que cualquiera puede verificar, municipio por municipio.',
 'nota_eje': 'Se conserva el eje propuesto con dos precisiones. Primera: el lugar se define por una vara (legalidad y cumplimiento) y no por una posición entre izquierda y derecha, porque en ese eje el partido tiene la etiqueta en un lado y a su votante de 2026 en el otro. Segunda: la independencia sola dice contra qué se está; para que no se lea como tibieza necesita reglas escritas de cuándo apoya y cuándo exige, y pruebas locales que la respalden.',
 'por_que': [
  {'t': 'Dos bandos firmes y un centro suelto',
   'x': 'La presidencial de 2026 dejó dos electorados que casi no se mueven y, en medio, votantes sin casa fija. El votante liberal del Senado se partió por igual entre los dos candidatos y más de un tercio no salió. Ahí hay espacio, pero no se llena con una posición intermedia: se llena con una razón propia para votar.',
   'dato': f"{p(pc(s1, 'pacto', 'cepeda'))} del voto del Pacto al Senado fue con Cepeda y {p(pc(s1, 'cd', 'abelardo'))} del Centro Democrático con De la Espriella. Del voto liberal, {p(pc(s1, 'liberal', 'cepeda'))} fue con Cepeda, {p(pc(s1, 'liberal', 'abelardo'))} con De la Espriella y {p(pc(s1, 'liberal', 'novoto'))} no votó en la primera vuelta (estimación del modelo).",
   'mod': 'tablero'},
  {'t': 'La etiqueta dice una cosa y el votante de 2026 otra',
   'x': 'En el diccionario de familias políticas que usa este trabajo el partido figura en el centro-izquierda. En marzo de 2026 avaló a Paloma Valencia y su votante de Bogotá lo siguió; en septiembre se declaró independiente del gobierno. Definirse entre izquierda y derecha lo obliga a perder a una de sus dos mitades. Le conviene un lugar que no dependa de ese eje.',
   'dato': f"{p(nl_pal)} de los {n(nl_cam)} votos de su lista a la Cámara por Bogotá fue con Paloma Valencia en la primera vuelta (margen de {p(nl_lo, 0)} a {p(nl_hi, 0)}; estimación del modelo).",
   'mod': 'tablero'},
  {'t': 'Su fuerza comprobada es local y con nombre propio',
   'x': 'Al Senado, solo, no pasó el umbral en 2022; en 2026 entró en una lista compartida donde su voto no se distingue del de sus aliados. En lo local es al revés: casi todas sus curules de concejo salieron de listas con su nombre. La marca rinde donde hay una persona conocida que responde por ella en su municipio.',
   'dato': f"{n(R['concejales'])} curules de concejo estimadas en {n(R['concejales_muns'])} municipios en 2023: {n(R['concejales_propias'])} en lista propia y {n(conc_coal)} en coalición. Senado 2022: {n(nl22['votos'])} votos ({p(nl22['pct'])}) y ninguna curul. Senado 2026: dentro de Ahora Colombia ({n(ah26['votos'])} votos, {ah26['curules']} curules).",
   'mod': 'inventario'},
  {'t': 'La agenda abre un terreno donde hoy no está',
   'x': 'Justicia y corrupción ganan peso en la prensa y casi todo lo que se publica de corrupción es negativo, pero el partido no aparece en esas notas. La gente pide salud y seguridad; la prensa cubre mucha seguridad y poca salud. Hay un tema propio sin vocero y un tema de consenso sin dueño.',
   'dato': f"Justicia y corrupción pasaron de {p(jc_ini)} a {p(jc_fin)} de los titulares de asuntos públicos entre el primer y el último tercio del semestre. El partido sale en {nl_tit} de {n(cob['unicos'])} titulares y en ninguno de esos dos temas. Salud: {p(urg['Salud'])} la pone entre lo más urgente (Invamer, mayo de 2026) y ocupa {p(peso['salud'])} de los titulares.",
   'mod': 'clima'},
 ],
 'lugar': {
  'x': 'El lugar es el del partido que no le debe nada al gobierno ni a la oposición y que por eso puede exigirles a los dos con el mismo criterio. No es un punto medio: es una vara. Es defendible porque el partido ya tomó esa decisión en público, porque el legado de Galán la respalda y porque se puede probar en lo local, donde gobierna y hace control con nombre propio.',
  'propios': [
   {'tema': 'Legalidad y cuentas claras',
    'x': 'Es el tema que el partido puede reclamar como suyo: cuidar la plata pública y cumplir la regla, empezando por la propia casa. Sube en la agenda y no tiene un vocero que no sea de alguno de los dos bandos.',
    'dato': f"Corrupción: {n(tono['corrupcion']['n'])} titulares en el semestre, {p(tono['corrupcion']['neg'], 0)} negativos; pasó de {p(cam['corrupcion']['ini'])} a {p(cam['corrupcion']['fin'])} de la agenda de asuntos públicos."},
   {'tema': 'Instituciones y control político',
    'x': 'Hacer control a quien gobierne, sea quien sea. Es lo que la independencia permite y lo que un partido de gobierno o de oposición no puede hacer con el mismo criterio para los dos lados.',
    'dato': f"Justicia pasó de {p(cam['justicia']['ini'])} a {p(cam['justicia']['fin'])} de los titulares de asuntos públicos. El partido se declaró en independencia el 4 de septiembre de 2026."},
  ],
  'consenso': [
   {'tema': 'Seguridad',
    'x': 'Todos la quieren: se compite por credibilidad y resultados, no por dureza. El partido entra por la legalidad y por lo que sus cargos pueden mostrar con una cifra.',
    'dato': f"Primer tema de la prensa en {sem_seg} de {n_sem} semanas, con {p(peso['seguridad'])} de los titulares de asuntos públicos; {p(urg['Inseguridad'])} la pone entre lo más urgente (Invamer)."},
   {'tema': 'Salud',
    'x': 'Es lo que más pide la gente y de lo que menos habla la prensa. Se gana credibilidad hablando solo de lo que depende del municipio o del departamento, con casos y cifras de ahí.',
    'dato': f"{p(urg['Salud'])} la pone entre lo más urgente (Invamer, mayo de 2026); en la prensa es el {ordinal[puesto_salud]} tema, con {p(peso['salud'])} de los titulares."},
   {'tema': 'Empleo y costo de vida',
    'x': 'Crece en la agenda. Se entra con crédito local: lo que se consiguió para el municipio, con fecha y prueba.',
    'dato': f"Economía y empleo pasó de {p(cam['empleo_economia']['ini'])} a {p(cam['empleo_economia']['fin'])} de los titulares de asuntos públicos."},
  ],
  'ceder': [
   {'tema': 'La pelea entre gobierno y oposición', 'x': 'Tiene dueños con electorados que no se mueven. Entrar ahí es escoger bando y perder la independencia.'},
   {'tema': 'La dureza en seguridad', 'x': 'Ese lugar ya está ocupado. Competir por quién es más duro deja al partido de segundo.'},
   {'tema': 'La política internacional', 'x': 'Pesa en la prensa y no decide un concejo, una alcaldía ni una asamblea.'},
  ],
  'refs': ['T1', 'T2'],
 },
 'pilares': [
  {'t': 'Un solo lugar, dicho igual en todas partes',
   'x': 'La mente del votante guarda pocos lugares y el partido hoy casi no ocupa ninguno en la prensa. Antes de pedir el voto hay que fijar una frase y repetirla: no le debe a nadie, les exige a todos, cumple en lo local. El lugar se define por una vara y no por una posición entre izquierda y derecha, porque en ese eje el partido pierde a la mitad de los suyos.',
   'como': ['Una frase y tres pruebas que todo vocero, concejal y alcalde repite igual.',
            'En cada aparición, el tema propio y un tema de consenso al que siempre se vuelve.',
            'Ante la pregunta «¿con el gobierno o con la oposición?», contestar con el criterio: se apoya lo que cumple y se exige lo que falta.'],
   'dato': f"El partido aparece en {nl_tit} de {n(cob['unicos'])} titulares del semestre; el Pacto en {n(fz['pacto']['total'])} y el Centro Democrático en {n(fz['cd']['total'])}.",
   'principio': 'A1', 'refs': ['T1', 'T2'], 'oficio': False},
  {'t': 'Legalidad, primero en casa',
   'x': 'El tema propio solo es creíble si el partido se lo aplica a sí mismo antes que a los demás. El contraste con el gobierno y con la oposición se hace con hechos, datos y fechas, nunca con adjetivos: el ataque no suma votantes nuevos y se devuelve. La misma idea se dice en dos claves: orden y regla para unos, justicia y cuidado de lo público para otros.',
   'como': ['Un estándar escrito de avales y de rendición de cuentas, publicado antes de marzo de 2027 (criterio de oficio).',
            'Cada posición frente al gobierno o a la oposición lleva un dato, una propuesta y una fecha para revisarla.',
            'El mismo criterio cuando el caso toca a un aliado o a un cargo propio.'],
   'dato': f"{p(tono['corrupcion']['neg'], 0)} de los titulares de corrupción son negativos. Los casos del entorno del gobierno anterior suman {n(cr['total'])} titulares y aparecen en {cr['semanas_con']} de {n_sem} semanas.",
   'principio': 'A4', 'refs': ['T11', 'T2', 'T5', 'T6'], 'oficio': False},
  {'t': 'La prueba es local: crédito frecuente y verificable',
   'x': 'El partido tiene cargos en muchos municipios y casi ninguno aparece en la prensa. Quien ocupa un cargo está en campaña todo el tiempo: su comunicación es rendir cuentas. Rinde más contar muchos logros pequeños, cada uno con su prueba, que uno grande. La suma de esos créditos es lo que vuelve cierta la palabra «cumple» y lo que une a concejales que hoy trabajan sueltos.',
   'como': ['Una pieza de crédito por semana por cada cargo: un logro pequeño, con fecha y prueba.',
            'Una rendición de cuentas al mes en el territorio, con una propuesta y un compromiso que se pueda verificar; no un mitin.',
            'Un tablero nacional que junte esos créditos bajo la marca del partido (criterio de oficio).'],
   'dato': f"{n(R['concejales'])} curules de concejo estimadas en {n(R['concejales_muns'])} municipios, {R['alcaldes']} alcaldes, {R['diputados']} diputados y {R['ediles']} ediles en Bogotá. Fuera de Bogotá, en {n(fuera_uno)} de {n(len(fuera))} municipios hay una sola curul.",
   'principio': 'A7', 'refs': ['T20', 'T21', 'T19', 'R3.1', 'R3.2'], 'oficio': False},
  {'t': 'Voto personal dentro de una marca visible',
   'x': 'Con lista abierta cada candidato compite con su nombre y su rival principal está en su propia lista. El partido pone la marca y el tema; el candidato, la reputación en su territorio. De ahí sale la regla de coaliciones, que es criterio de oficio: lista propia donde el partido ya eligió o quedó cerca; coalición solo donde solo no alcanza, y siempre con el nombre a la vista.',
   'como': ['Decidir municipio por municipio, antes de marzo de 2027, si va lista propia o coalición, con la votación de 2023 en la mano.',
            'En toda coalición, el nombre del partido en la lista y un acuerdo escrito sobre el tema común.',
            'Preferir candidatos con arraigo medible en su territorio a figuras sin votos propios.'],
   'dato': f"{n(R['concejales_propias'])} de {n(R['concejales'])} curules de concejo salieron de listas propias. Fuera de Bogotá, {n(RF['solas'])} de {n(RF['listas'])} listas fueron solas. En el Senado de 2026, dentro de una coalición, el voto del partido no se puede separar.",
   'principio': 'A1', 'refs': ['T3'], 'oficio': False},
  {'t': 'Persuadir temprano, movilizar al final y medir siempre',
   'x': 'El contacto de campaña casi no cambia preferencias: lo que se va a persuadir se persuade ahora, lejos de la elección. En campaña lo que rinde es sacar a votar a quien ya prefiere al partido, cara a cara y en su hogar. La pauta se guarda para los últimos días y las redes sirven para que la base reparta lo que el partido hace, no para convencer a quien no lo sigue.',
   'como': ['Línea de base por puesto de votación en cada municipio con lista: participación y votos de 2023.',
            'Ubicar desde ya los hogares y las comunidades donde el partido ya tiene votos: son la red de octubre.',
            'Después de la elección, comparar los puestos con trabajo y sin trabajo contra 2023.'],
   'dato': f"En {n(RF['sin_curul_a_300'])} municipios la lista de 2023 quedó a menos de 300 votos de su primera curul.",
   'principio': 'A5', 'refs': ['T14', 'T13', 'T15', 'T16', 'T17', 'T18', 'T24'], 'oficio': False},
 ],
 'audiencias': [
  {'quien': 'Quien ya votó por una lista del partido en 2023',
   'donde': f"Bogotá y los {n(len(fuera))} municipios con concejal fuera de la capital",
   'cuadrante': 'retener',
   'decir': 'Esto se hizo con tu voto: el logro, la fecha y la prueba. No se gasta en convencerlo; se le rinde cuentas.',
   'refs': ['T14', 'T21', 'R3.1']},
  {'quien': 'Quien votó por la lista y se quedó sin concejal por pocos votos',
   'donde': f"Los {n(RF['sin_curul_a_300'])} municipios donde faltaron menos de 300 votos para la primera curul",
   'cuadrante': 'movilizar',
   'decir': 'Faltó poco. Visita al hogar, cómo se marca el tarjetón y quién es el candidato del municipio.',
   'refs': ['T13', 'R2.1', 'R2.2']},
  {'quien': 'El votante urbano que en 2026 siguió al partido cuando avaló a Paloma Valencia',
   'donde': 'Las ciudades, y sobre todo Bogotá',
   'cuadrante': 'retener-crecer',
   'decir': 'Orden y regla, con resultados que se pueden revisar. No se le pide cambiar de bando: se le pide mirar lo local.',
   'refs': ['T21', 'R3.2', 'T6']},
  {'quien': 'El votante de los partidos tradicionales que votó al Senado y no a la presidencial',
   'donde': 'Municipios medianos y pequeños',
   'cuadrante': 'conocer',
   'decir': 'Crédito y no posición: qué consiguió el concejal o el alcalde para el municipio. Primero, que conozca el nombre.',
   'dato': f"No votaron en la primera vuelta {p(pc(s1, 'liberal', 'novoto'))} de los votantes liberales del Senado, {p(pc(s1, 'u', 'novoto'))} de los de La U y {p(pc(s1, 'conservador', 'novoto'))} de los conservadores (estimación del modelo).",
   'refs': ['T1', 'T20', 'T22']},
  {'quien': 'El votante firme de los dos bandos',
   'donde': 'Todo el país',
   'cuadrante': 'no-gastar',
   'decir': 'Nada dirigido. Ni se le ataca ni se le corteja: el contacto de campaña casi no lo mueve.',
   'refs': ['T14']},
 ],
 'relato': {
  'yo': 'Heredamos una idea sencilla: la política se puede hacer sin deberle nada a nadie. Por eso el partido se declaró independiente: para poder decirle a quien gobierne, sea quien sea, qué está bien y qué falta.',
  'nosotros': 'Somos la gente que no cabe en la pelea de los dos bandos y que quiere algo más simple: que el barrio y el municipio funcionen y que la plata pública se cuide.',
  'ahora': 'En octubre de 2027 no se elige presidente. Se elige a quien responde por la calle, el centro de salud y la seguridad del barrio. Es la elección donde se puede comprobar quién cumple.',
  'refs': ['T8', 'T7']},
 'contraste': [
  {'frente': 'El gobierno nacional',
   'x': 'Independencia declarada el 4 de septiembre de 2026. Se acompaña lo que funcione con el dato en la mano y se exige lo que falte con una fecha. Nunca desde el adjetivo.'},
  {'frente': 'El Pacto Histórico y la oposición',
   'x': f"Los casos del entorno del gobierno anterior ya están en la prensa {cr['semanas_con']} de {n_sem} semanas: no hace falta atacarlos. El contraste es el estándar propio de cuentas claras."},
  {'frente': 'Los partidos tradicionales en lo local',
   'x': 'Se contrasta con lo verificable: listas con aval publicado y cargos que rinden cuentas cada mes. Se compara gestión con gestión, no personas.'},
  {'frente': 'Los aliados de coalición',
   'x': 'No hay contraste, hay distinción: que el nombre del partido se vea en la lista y que el votante sepa qué puso cada uno.'},
 ],
 'nota_fases': f"Las fases y sus cortes son criterio de oficio, tomados del calendario del banco de estrategia. Las fechas de inscripción, cédulas y elección salen de la {ES['calendario']['resolucion']}, leída en notas de prensa. La fecha de las consultas de los partidos para 2027 no está fijada.",
 'fases': [
  {'fase': 'Posicionamiento', 'desde': '2026-11-10', 'hasta': fases_b['posicionamiento']['hasta'],
   'foco': 'Fijar el lugar y el estándar antes de que empiece la campaña: lo que se va a persuadir se persuade ahora.',
   'acciones': ['Aprobar la frase, las tres pruebas y el estándar de avales y rendición de cuentas.',
                'Poner a cada cargo a publicar una pieza de crédito por semana.',
                'Armar la línea de base por puesto y el mapa de lista propia o coalición, municipio por municipio.',
                'Tomar una posición pública al mes en el tema propio, con un dato que nadie más tenga.']},
  {'fase': 'Precampaña', 'desde': fases_b['precampana']['desde'], 'hasta': f_cierra,
   'foco': 'Cerrar el vehículo: avales, listas y coaliciones, sin dejar de rendir cuentas.',
   'acciones': ['Cerrar coaliciones con el nombre del partido visible y el tema común por escrito.',
                'Dar los avales con el estándar publicado: la inscripción abre el 30 de junio y cierra el 31 de julio de 2027.',
                'Seguir la rendición de cuentas mensual, primero donde el partido ya es fuerte.',
                'Armar la red de hogares y comunidades que va a movilizar en octubre.']},
  {'fase': 'Campaña', 'desde': '2027-08-01', 'hasta': fases_b['campana']['hasta'],
   'foco': 'Movilizar a quien ya prefiere al partido y sostener el tema propio.',
   'acciones': ['Contacto cara a cara en los hogares donde ya hay votos.',
                'Crédito frecuente: muchos logros pequeños, cada uno con su prueba.',
                'Avisar a quien cambió de residencia: la inscripción de cédulas cierra el 31 de agosto de 2027.',
                'Guardar la pauta para las últimas semanas.']},
  {'fase': 'Día D', 'desde': fases_b['diad']['desde'], 'hasta': f_elec,
   'foco': 'Sacar a votar y cuidar el voto.',
   'acciones': ['Recordatorio por hogar, transporte y cómo se marca el tarjetón.',
                'Testigos en los puestos donde están los votos del partido.',
                'Nunca revelar quién votó.']},
  {'fase': 'Después de la elección', 'desde': fases_b['despues']['desde'], 'hasta': '2027-12-31',
   'foco': 'Cuidar el escrutinio y dejar la línea de base de la siguiente.',
   'acciones': ['Seguir los escrutinios desde la noche de la elección.',
                'Guardar los resultados por puesto y comparar los puestos con trabajo y sin trabajo.',
                'Los elegidos empiezan a rendir cuentas desde el primer mes del cargo.']},
 ],
 'agenda': [
  {'si': 'Cuando la prensa esté en seguridad',
   'haz': 'Entrar por la legalidad y por un resultado medible del municipio: qué se hizo, con qué cifra y qué falta. Una sola vocería por territorio.',
   'no': 'Competir en dureza ni comentar cada hecho de sangre.',
   'dato': f"Es el primer tema en {sem_seg} de {n_sem} semanas ({p(peso['seguridad'])} de los titulares de asuntos públicos), pero cada historia de seguridad dura {ept['seguridad']['mediana']} días.",
   'refs': ['T2']},
  {'si': 'Cuando la prensa esté en corrupción o justicia',
   'haz': 'Estar siempre: es el terreno propio. Una posición, una propuesta y el estándar del partido aplicado igual al gobierno, a la oposición y a los propios.',
   'no': 'Celebrar el escándalo ajeno ni callar el de casa.',
   'dato': f"Los dos temas pasaron de {p(jc_ini)} a {p(jc_fin)} de la agenda; {p(tono['corrupcion']['neg'], 0)} de los titulares de corrupción son negativos y el partido no aparece en ninguno.",
   'refs': ['T2', 'T11']},
  {'si': 'Cuando la prensa esté en salud',
   'haz': 'Llevar el tema a lo local, con casos y cifras del municipio y lo que puede hacer un concejo, una alcaldía o una asamblea.',
   'no': 'Prometer lo que depende de la Nación.',
   'dato': f"{p(urg['Salud'])} la pone entre lo más urgente (Invamer, mayo de 2026); en la prensa es el {ordinal[puesto_salud]} tema, con {p(peso['salud'])} de los titulares.",
   'refs': ['T2', 'T6']},
  {'si': 'Cuando estalle una crisis nacional entre gobierno y oposición',
   'haz': 'Una sola declaración si toca el tema propio, con el criterio de siempre, y volver a lo local.',
   'no': 'Gastar la semana en una historia que se apaga sola ni escoger bando.',
   'dato': f"La historia típica dura {ep['mediana']} días y solo {p(ep['mas7'], 0)} pasa de una semana. Los casos del entorno del gobierno anterior suman {n(cr['total'])} titulares en {cr['dias_con']} de {cr['dias']} días: es un goteo constante, no una historia que haya que seguir cada día.",
   'refs': ['T14']},
  {'si': 'Cuando la prensa esté en empleo, costo de vida u obras',
   'haz': 'Reclamar crédito local: qué se consiguió para el municipio, con fecha y prueba. Muchas piezas pequeñas.',
   'no': 'Opinar de la economía nacional sin un hecho propio que mostrar.',
   'dato': f"Economía y empleo pasó de {p(cam['empleo_economia']['ini'])} a {p(cam['empleo_economia']['fin'])} de los titulares, y {p(tono['empleo_economia']['pos'])} de sus notas son positivas.",
   'refs': ['T20', 'T22', 'R3.1']},
  {'si': 'Cuando nadie esté hablando del partido',
   'haz': 'Producir el hecho: un debate de control, una cifra propia o una rendición de cuentas, primero en medios locales.',
   'no': 'Esperar a que la prensa nacional llegue ni llenar el silencio con opinión.',
   'dato': f"El partido aparece en {nl_tit} de {n(cob['unicos'])} titulares en {cob['dias']} días.",
   'refs': ['T20', 'T1']},
 ],
 'riesgos': [
  {'r': 'Que la independencia se lea como tibieza o como cambio de rumbo: en 2026 el partido avaló una candidatura en marzo, dejó en libertad a su militancia en junio y se declaró independiente en septiembre.',
   'manejo': 'Reglas escritas y públicas de cuándo acompaña y cuándo exige, por tema y no por persona, y aplicarlas igual a los dos lados.'},
  {'r': 'Que la etiqueta y el votante no coincidan: figura en el centro-izquierda y su votante de Bogotá fue con Paloma Valencia.',
   'manejo': 'No definirse entre izquierda y derecha. Hablar del tema propio en dos claves: orden y regla, y justicia y cuidado de lo público.'},
  {'r': 'Que la marca se diluya en coaliciones, como pasó en el Senado de 2026.',
   'manejo': 'Lista propia donde ya eligió o quedó cerca; en coalición, el nombre del partido en la lista y un acuerdo escrito.'},
  {'r': f"Que el resultado dependa de una sola ciudad: Bogotá puso {p(bog_peso, 0)} del voto del partido a concejos en 2023.",
   'manejo': 'Tratar a Bogotá y a las regiones como dos estrategias con las mismas reglas, y juzgar cada cargo por lo que puede probar.'},
  {'r': 'Que el tema propio ya tenga voceros más ruidosos en los dos bandos.',
   'manejo': 'Diferenciarse por el criterio: aplicarlo primero en casa y a los dos lados por igual.'},
  {'r': f"Que la lectura de prensa engañe: {n_reg} de los {n_medios} medios del banco de titulares son de Medellín y Antioquia, y mide cobertura, no opinión.",
   'manejo': 'Leer el banco como tendencia de agenda y contrastarlo con encuestas antes de decidir un mensaje.'},
  {'r': 'Que la evidencia no se traslade: casi todos los estudios citados son de Estados Unidos.',
   'manejo': 'Tomar los principios y no los guiones, y medir en puestos propios qué funcionó.'},
 ],
 'medir': [
  {'que': 'Si el partido entra a la conversación de su tema',
   'como': f"Titulares que lo nombran en justicia y corrupción, cada mes. Punto de partida: {nl_tit} titulares en total y ninguno en esos temas."},
  {'que': 'Si la prueba local existe',
   'como': f"Cuántos de los cargos del partido publican al menos una pieza de crédito por semana y una rendición de cuentas al mes."},
  {'que': 'Si la marca va a estar en el tarjetón',
   'como': f"Listas propias y coaliciones inscritas al 31 de julio de 2027, contra las de 2023: fuera de Bogotá hubo {n(RF['listas'])} listas, {n(RF['solas'])} solas y {n(RF['coalicion'])} en coalición."},
  {'que': 'Si el trabajo de territorio mueve algo',
   'como': 'Participación y votos por puesto de votación en 2027 contra 2023, comparando puestos con trabajo y sin trabajo.'},
  {'que': 'Si la agenda cambió',
   'como': 'El peso semanal de seguridad, justicia, corrupción y salud en el banco de titulares, y la siguiente medición de Invamer.'},
 ],
}

# ── referencias: solo las usadas, copiadas del banco ─────────────────────────
FICHAS = {f['id']: f for f in BANCO['fichas']}; PRINC = {x['id'] for x in BANCO['principios']}
usadas = []
def junta(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'refs': [usadas.append(i) for i in v if i not in usadas]
            else: junta(v)
    elif isinstance(o, list):
        for v in o: junta(v)
junta(E)
malas = [i for i in usadas if i not in FICHAS]
assert not malas, f'fichas que no existen en el banco: {malas}'
assert all(x['principio'] in PRINC for x in E['pilares'])
orden = [f['id'] for f in BANCO['fichas']]
E['refs'] = []
for i in sorted(usadas, key=orden.index):
    f = FICHAS[i]
    E['refs'].append({'id': i, 'corto': f['corto'], 'texto': ' · '.join(r['texto'] for r in f['refs']),
                      'doi': next((r['doi'] for r in f['refs'] if r.get('doi')), None),
                      'tipo': f.get('tipo'), 'idea': f.get('idea')})
E['principios'] = [{'id': x['id'], 'corto': x['corto'], 'texto': x['texto']} for x in BANCO['principios'] if x['id'] in {q['principio'] for q in E['pilares']}]
ADV = BANCO['advertencias']
E['advertencias'] = [a for a in ADV if a.startswith('Las referencias están verificadas') or a.startswith('Casi toda la evidencia') or a.startswith('Los anuncios movieron poco')]
assert len(E['advertencias']) == 3

# ── validación ───────────────────────────────────────────────────────────────
pal = lambda s: len(re.findall(r'\S+', s))
err = []
def chk(c, msg):
    if not c: err.append(msg)
chk(pal(E['frase']) <= 10, f"frase {pal(E['frase'])} palabras")
chk(pal(E['idea']) <= 45, f"idea {pal(E['idea'])} palabras")
chk(len(E['por_que']) == 4, 'por_que debe tener 4')
for x in E['por_que']: chk(40 <= pal(x['x']) <= 70, f"por_que «{x['t']}» {pal(x['x'])} palabras"); chk(x['mod'] in ('inventario', 'tablero', 'clima', 'escenarios', 'encuesta'), 'mod')
chk(60 <= pal(E['lugar']['x']) <= 90, f"lugar {pal(E['lugar']['x'])} palabras")
chk(4 <= len(E['pilares']) <= 5, 'pilares 4 o 5')
for x in E['pilares']: chk(50 <= pal(x['x']) <= 80, f"pilar «{x['t']}» {pal(x['x'])} palabras"); chk(len(x['como']) == 3, 'como 3')
chk(3 <= len(E['audiencias']) <= 5, 'audiencias 3-5')
for x in E['audiencias']: chk(x['cuadrante'] in BANCO['cuadrantes'], f"cuadrante {x['cuadrante']}")
chk(5 <= len(E['agenda']) <= 6, 'agenda 5-6')
for x in E['fases']: chk(2 <= len(x['acciones']) <= 4, 'acciones 2-4'); chk(x['desde'] <= x['hasta'], 'fechas')
for a, b in zip(E['fases'], E['fases'][1:]): chk(a['hasta'] < b['desde'], f"fases se pisan: {a['fase']} / {b['fase']}")
txt = json.dumps(E, ensure_ascii=False)
chk('—' not in txt and '–' not in txt, 'hay rayas largas')
for mala in ('Carlos Fernando', 'Juan Manuel', 'hermano'): chk(mala not in txt, f'menciona {mala}')
if err: sys.exit('VALIDACIÓN:\n  ' + '\n  '.join(err))

json.dump(E, open(os.path.join(D, 'estrategia-general.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(D, 'estrategia-general.js'), 'w', encoding='utf-8').write(
    "window.NLD=window.NLD||{};window.NLD['estrategia-general']=" + json.dumps(E, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('ok ·', len(E['refs']), 'fichas citadas:', ' '.join(r['id'] for r in E['refs']))
print('frase', pal(E['frase']), '· idea', pal(E['idea']), '· lugar', pal(E['lugar']['x']),
      '· por_que', [pal(x['x']) for x in E['por_que']], '· pilares', [pal(x['x']) for x in E['pilares']])
