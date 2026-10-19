#!/usr/bin/env python3
"""Banco de estrategia de Candidato 360 → candidato-360-data/estrategia-banco.json

Lee el banco hecho a mano (anexo A de la primera consultoría: tronco, ramas y
matriz arquetipo × principio) y lo deja en el JSON que lee el motor
`candidato-360-estrategia.js`. El anexo es interno y vive fuera del repo; lo
que sale de aquí es solo la literatura pública:

  · los 8 principios durables (capa A) con sus fichas;
  · las fichas del tronco (T) y de las ramas (R), con referencia, DOI y la
    «modulación por arquetipo»;
  · las ramas, de qué ficha nacen y a qué arquetipos sirven;
  · la matriz en números (2 central · 1 útil · 0 igual · -1 riesgo) y la nota
    de cada celda.

⚠️ Lo que en el anexo es del caso concreto NO pasa: las líneas «Para …», el
Nivel 3 (el caso) y la capa B (formatos, que tiene su propio registro). Al
final se verifica que no quede ningún nombre del caso; si queda, no se escribe.

Además de lo que sale del anexo, el script agrega lo que es criterio del
equipo y va rotulado así: el calendario de 2027 (con su estado: ley,
anunciado o derivado), las fases, la tabla de territorio y las acciones por
fase, cada una con las fichas que la sostienen o «criterio de oficio».

    C360_ESTRATEGIA_ANEXO=<ruta del anexo A> python3 tools/candidato-360/estrategia/build_banco.py
"""
import argparse, json, os, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
# El anexo es interno y la ruta lleva el nombre del cliente: no va escrita en
# este repo (es público). Se pasa con --anexo o con C360_ESTRATEGIA_ANEXO.
ANEXO = os.environ.get('C360_ESTRATEGIA_ANEXO', '')
SALIDA = RAIZ / 'candidato-360-data/estrategia-banco.json'
CODIGOS = ['PRO', 'CON', 'SUP', 'CAS', 'PER', 'CMN', 'PDP', 'NDF', 'BDG', 'PVP', 'CIM',
           # v1 de Bogotá (oct-19-2026): 2 nuevos de Concejo y los 8 de Alcaldía
           'CSD', 'NDO', 'NES', 'NBA', 'CDE', 'CTR', 'CMA', 'PJA', 'BRV', 'SVC']
RE_COD = re.compile(r'\b(' + '|'.join(CODIGOS) + r')\b')
# Lo que delata el caso: si algo de esto sobrevive, el JSON no se escribe. La
# lista vive FUERA del repo (los términos son el nombre del cliente), una por
# línea; sin ella el script no corre: falla cerrado.
PROHIBIDO_TXT = RAIZ / 'Bases de datos/candidato-360/estrategia-prohibido.txt'
# Una frase del tronco que habla del caso sin nombrarlo.
REESCRITURAS = [
    ('difícil para alguien con 22 años en el cargo', 'difícil para un titular con muchos años en el cargo'),
]


def limpio(s):
    s = re.sub(r'\*+', '', s)
    for a, b in REESCRITURAS:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def expandir(lista):
    """«T4-T6, T9 · R1» → ['T4','T5','T6','T9'], ['R1']."""
    fichas, ramas = [], []
    for tok in re.split(r'[,·]', lista):
        tok = tok.strip()
        m = re.fullmatch(r'T(\d+)-T(\d+)', tok)
        if m:
            fichas += [f'T{i}' for i in range(int(m[1]), int(m[2]) + 1)]
        elif re.fullmatch(r'T\d+', tok):
            fichas.append(tok)
        elif re.fullmatch(r'R\d+\.\d+', tok):
            fichas.append(tok)
        elif re.fullmatch(r'R\d+', tok):
            ramas.append(tok)
        # N3.x es del caso: no pasa.
    return fichas, ramas


def corto_autores(texto):
    """«Gerber, Alan S., Donald P. Green y Christopher W. Larimer. 2008. …» → «Gerber et al. 2008»."""
    m = re.match(r'(.+?)\.\s+((?:19|20)\d\d)\b', texto)
    if not m:
        return texto[:40]
    autores, año = m[1], m[2]
    partes = [p.strip() for p in re.split(r',\s*|\s+y\s+', autores) if p.strip()]
    if partes and partes[-1].startswith('comps'):
        partes = partes[:-1]
    if not partes:
        return año
    apellidos = [partes[0]] + [p.split()[-1] for p in partes[2:]]
    if len(apellidos) == 1:
        nombre = apellidos[0]
    elif len(apellidos) == 2:
        nombre = f'{apellidos[0]} y {apellidos[1]}'
    else:
        nombre = f'{apellidos[0]} et al.'
    return f'{nombre} {año}'


def leer_ref(linea):
    """Una línea de referencia: el texto en negrita, el DOI o la URL y las marcas."""
    negritas = re.findall(r'\*\*(.+?)\*\*', linea)
    texto = limpio(negritas[0]) if negritas else limpio(linea)
    doi = re.search(r'https://doi\.org/\S+', linea)
    url = None if doi else re.search(r'https?://\S+', linea)
    marcas = re.findall(r'\[([^\]]+)\]', linea)
    resto = re.sub(r'\*\*(.+?)\*\*', '', linea, count=1)
    resto = re.sub(r'https?://\S+|\[[^\]]+\]', '', resto)
    resto = limpio(resto.replace('DOI comprobado:', '').replace('ficha del editor:', '').replace('Ficha de catálogo:', '').replace('PDF en Harvard DASH:', ''))
    resto = re.sub(r'^(Base|Continuación):\s*|^-\s*', '', resto).strip(' .;·')
    if resto.count(')') > resto.count('('):
        resto = resto.replace(')', '', resto.count(')') - resto.count('('))
    if resto.count('(') > resto.count(')'):
        resto += ')'
    ref = {'texto': texto, 'corto': corto_autores(texto),
           'doi': doi[0].rstrip('.,') if doi else None,
           'url': url[0].rstrip('.,') if url else None,
           'marcas': marcas}
    rol = re.match(r'^(Base|Continuación):', linea)
    if rol:
        ref['rol'] = rol[1].lower()
    if resto and not re.fullmatch(r'(?i)sin doi( \(libro comercial\)| comprobado)?', resto):
        ref['nota'] = resto
    return ref


def tipo_de(marcas):
    m = ' '.join(marcas).lower()
    return 'evidencia' if 'evidencia' in m else 'oficio'


def leer_modulacion(lineas):
    """«  - CMN y NDF: votan a la persona» → {'CMN': '…', 'NDF': '…'}."""
    out = {}
    for ln in lineas:
        m = re.match(r'\s+-\s+(.+?):\s+(.+)$', ln)
        if not m:
            continue
        etiqueta, texto = m[1].strip(), limpio(m[2])
        if etiqueta.lower().startswith('resto'):
            out['resto'] = texto
            continue
        cods = RE_COD.findall(etiqueta)
        if not cods:   # «Para llegar a votantes que no comparten…» trae los códigos entre paréntesis
            continue
        extra = RE_COD.sub('', etiqueta)
        extra = re.sub(r'\s*(,|\by\b)\s*', ' ', extra).strip(' ()')
        for c in cods:
            out[c] = f'{texto}' if not extra else f'({limpio(etiqueta)}) {texto}'
    return out


def bloques(lineas, inicio_re, fin_re):
    out, actual = [], None
    for ln in lineas:
        if inicio_re.match(ln):
            if actual:
                out.append(actual)
            actual = [ln]
        elif actual is not None:
            if fin_re.match(ln):
                out.append(actual)
                actual = None
            else:
                actual.append(ln)
    if actual:
        out.append(actual)
    return out


def leer_tronco(lineas):
    fichas = []
    for b in bloques(lineas, re.compile(r'^### T\d+\.'), re.compile(r'^(#|---)')):
        m = re.match(r'^### (T\d+)\.\s+(.+?)\s+·\s+(.+)$', b[0])
        fid, autores, tema = m[1], limpio(m[2]), limpio(m[3])
        refs, idea, mod, ramas, notas = [], '', {}, [], []
        i = 1
        while i < len(b):
            ln = b[i]
            if re.match(r'^(Base|Continuación):\s*\*\*', ln) or ln.startswith('**'):
                refs.append(leer_ref(ln))
            elif ln.startswith('- **Principio:**'):
                idea = limpio(ln.split('**Principio:**', 1)[1])
            elif ln.startswith('- **Modulación por arquetipo:**'):
                cola = limpio(ln.split('**Modulación por arquetipo:**', 1)[1])
                if cola:
                    mod = {'todos': cola}
                else:
                    sub = []
                    while i + 1 < len(b) and re.match(r'^\s+-\s', b[i + 1]):
                        i += 1
                        sub.append(b[i])
                    mod = leer_modulacion(sub)
            elif re.match(r'^- \*\*Rama (R\d)\*\*', ln) or re.match(r'^- \*\*Rama', ln):
                ramas += re.findall(r'R\d', ln)
            elif ln.startswith('- **Para '):
                pass   # el caso: no pasa
            elif ln.startswith('- **'):
                ramas += re.findall(r'\*\*Rama (R\d)\*\*', ln)
                nota = limpio(re.sub(r'\*\*Rama R\d\*\* nace aquí\.?', '', ln[2:]))
                if nota:
                    notas.append(nota)
            i += 1
        if not refs:
            sys.exit(f'{fid}: sin referencia')
        # El año va en la referencia; si no está ahí (T12: el año está en
        # duda entre dos ediciones), en la nota, y se dicen los dos.
        años = re.findall(r'(?:19|20)\d\d', refs[0]['texto']) or sorted(set(re.findall(r'\b(?:19|20)\d\d\b', refs[0].get('nota', ''))))
        fichas.append({'id': fid, 'nivel': 'tronco', 'corto': f"{autores} {años[0] if len(años) == 1 or re.search(r'(?:19|20)\d\d', refs[0]['texto']) else ' o '.join(años) if años else 's. f.'}",
                       'tema': tema, 'refs': refs, 'tipo': tipo_de(refs[0]['marcas']), 'lectura': 'ficha',
                       'idea': idea, 'modula': mod, 'ramas': sorted(set(ramas)), 'notas': notas})
    return fichas


def leer_ramas(lineas):
    ramas, fichas = [], []
    for b in bloques(lineas, re.compile(r'^## Rama R\d'), re.compile(r'^(# |---)')):
        m = re.match(r'^## Rama (R\d) · (.+?) — nace de (.+)$', b[0])
        rid, nombre, nace = m[1], limpio(m[2]), m[3]
        conv = next((limpio(x.split(':', 1)[1]) for x in b if x.startswith('Convergencia:')), '')
        rama = {'id': rid, 'nombre': nombre, 'nace_de': re.findall(r'T\d+', nace),
                'arquetipos': RE_COD.findall(nombre), 'convergencia': conv, 'fichas': []}
        for fb in bloques(b[1:], re.compile(r'^\*\*R\d\.\d\.'), re.compile(r'^(## |---)')):
            fid = re.match(r'^\*\*(R\d\.\d)\.', fb[0])[1]
            cab = fb[0].replace(f'**{fid}. ', '**', 1)
            refs, idea, en_rama = [], '', ''
            if re.search(r'(?:19|20)\d\d', re.findall(r'\*\*(.+?)\*\*', cab)[0]):
                refs.append(leer_ref(cab))
                marcas = refs[0]['marcas']
            else:   # R3.4 y R3.5: la cabecera es el arquetipo y las referencias van en viñetas
                marcas = re.findall(r'\[([^\]]+)\]', cab)
            for ln in fb[1:]:
                if re.match(r'^(Continuación|Base):\s*\*\*', ln) or re.match(r'^- \*\*[A-ZÁÉÍÓÚ][^*]+\. (?:19|20)\d\d\.', ln):
                    refs.append(leer_ref(ln))
                elif ln.startswith('- **En la rama:**'):
                    en_rama = limpio(ln.split('**En la rama:**', 1)[1])
                elif ln.startswith('- ') and not idea:
                    idea = limpio(ln[2:])
            if not refs:
                sys.exit(f'{fid}: sin referencia')
            fichas.append({'id': fid, 'nivel': 'rama', 'rama': rid, 'corto': '; '.join(r['corto'] for r in refs),
                           'refs': refs, 'tipo': tipo_de(marcas), 'lectura': 'ficha', 'idea': idea, 'en_rama': en_rama,
                           'sirve_tambien': RE_COD.findall(re.search(r'También sirve a ([^.]+)', en_rama)[1]) if 'También sirve a' in en_rama else []})
            rama['fichas'].append(fid)
        ramas.append(rama)
    return ramas, fichas


def leer_principios(texto):
    principios = []
    for m in re.finditer(r'^\| \*\*(A\d)\*\* \| (.+?) \| (.+?) \|$', texto, re.M):
        fichas, ramas = expandir(m[3])
        principios.append({'id': m[1], 'texto': limpio(m[2]), 'fichas': fichas, 'ramas': ramas})
    cortos = dict(re.findall(r'(A\d) ([^\[·]+?) \[', re.search(r'^\*\*Principios:\*\* (.+)$', texto, re.M)[1]))
    for p in principios:
        p['corto'] = cortos[p['id']].strip()
    return principios


VALOR = {'●●': 2, '●': 1, '○': 0, '✕': -1}


def leer_matriz(texto):
    tabla = texto.split('# MATRIZ', 1)[1].split('###', 1)[0]
    cab = next(l for l in tabla.splitlines() if l.startswith('| Arquetipo'))
    ids = re.findall(r'A\d', cab)
    matriz, notas = {}, {}
    for l in tabla.splitlines():
        m = re.match(r'^\| \*\*([A-Z]{3})\*\* \|(.+)\|$', l)
        if not m:
            continue
        celdas = [c.strip() for c in m[2].split('|')]
        fila, nota = {}, {}
        for pid, c in zip(ids, celdas):
            simbolo = next(s for s in ('●●', '●', '○', '✕') if c.startswith(s))
            fila[pid] = VALOR[simbolo]
            resto = limpio(c[len(simbolo):])
            if resto:
                nota[pid] = resto
        matriz[m[1]] = fila
        notas[m[1]] = nota
    return matriz, notas


def leer_arquetipos(texto):
    out = {}
    for m in re.finditer(r'\*\*([A-Z]{3})\*\* \| ([^|]+?) \|', texto.split('### Códigos de arquetipo', 1)[1].split('###', 1)[0]):
        out[m[1]] = {'nombre': limpio(m[2])}
    return out


# ── Lo que pone el equipo (no sale del anexo) ─────────────────────────────
# Qué id de cada lectura de arquetipos corresponde a cada código de la matriz.
# Los 5 emocionales son los de la cartografía de Medellín; los de Bogotá son las
# dos tipologías v1 (8 de Concejo y 8 de Alcaldía, oct-19-2026). Cartagena (8
# propios) todavía no tiene fila: el motor dice «todavía no».
EQUIVALENCIAS = {
    'PRO': ('emocional', 'medellin', '2023', 'proteccion'),
    'CON': ('emocional', 'medellin', '2023', 'continuidad'),
    'SUP': ('emocional', 'medellin', '2023', 'supervivencia'),
    'CAS': ('emocional', 'medellin', '2023', 'castigo'),
    'PER': ('emocional', 'medellin', '2023', 'pertenencia'),
    'CMN': ('bogota-concejo', 'bogota', 'concejo', 'nombre'),
    'PDP': ('bogota-concejo', 'bogota', 'concejo', 'partido'),
    'NDF': ('bogota-concejo', 'bogota', 'concejo', 'figuras'),
    'BDG': ('bogota-concejo', 'bogota', 'concejo', 'gestion'),
    'PVP': ('bogota-concejo', 'bogota', 'concejo', 'poco-voto'),
    'CIM': ('bogota-concejo', 'bogota', 'concejo', 'movilizada'),
    'CSD': ('bogota-concejo', 'bogota', 'concejo', 'sin-dueno'),
    'NDO': ('bogota-concejo', 'bogota', 'concejo', 'opinion'),
    'NES': ('bogota-alcaldia', 'bogota', 'alcaldia', 'estrategico'),
    'NBA': ('bogota-alcaldia', 'bogota', 'alcaldia', 'alternativa'),
    'CDE': ('bogota-alcaldia', 'bogota', 'alcaldia', 'decide'),
    'CTR': ('bogota-alcaldia', 'bogota', 'alcaldia', 'tradicional'),
    'CMA': ('bogota-alcaldia', 'bogota', 'alcaldia', 'media-alineada'),
    'PJA': ('bogota-alcaldia', 'bogota', 'alcaldia', 'alineada'),
    'BRV': ('bogota-alcaldia', 'bogota', 'alcaldia', 'reparte'),
    'SVC': ('bogota-alcaldia', 'bogota', 'alcaldia', 'cruce-sur'),
}

# El calendario de 2027. ⚠️ La Registraduría no ha expedido la resolución:
# lo «derivado» sale de la ley y se corrige cuando salga.
CALENDARIO = {
    'v': '2026-10-19',
    'eleccion': '2027-10-31',
    'nota': 'La resolución con el calendario de 2027 todavía no se expide: las fechas marcadas como derivadas salen de la ley y cambian cuando salga.',
    'hitos': [
        {'id': 'cedulas', 'nombre': 'Abre la inscripción de cédulas', 'fecha': '2026-10-31', 'estado': 'anunciado', 'fuente': 'Registraduría, anuncio del 15-oct-2026'},
        {'id': 'inscripcion', 'nombre': 'Inscripción de candidaturas y listas', 'fecha': '2027-06-30', 'hasta': '2027-07-30', 'estado': 'derivado', 'fuente': 'Ley 1475 de 2011, art. 30 (un mes, cuatro meses antes)'},
        {'id': 'propaganda', 'nombre': 'Empieza la propaganda electoral', 'fecha': '2027-07-31', 'estado': 'derivado', 'fuente': 'Ley 1475 de 2011, art. 35 (tres meses antes)'},
        {'id': 'cierre-cedulas', 'nombre': 'Cierra la inscripción de cédulas', 'fecha': '2027-08-31', 'estado': 'derivado', 'fuente': 'Ley 1475 de 2011, art. 49 (dos meses antes)'},
        {'id': 'eleccion', 'nombre': 'Elección territorial', 'fecha': '2027-10-31', 'estado': 'ley', 'fuente': 'Ley 163 de 1994, art. 1 (último domingo de octubre)'},
    ],
    # El corte entre posicionamiento y precampaña es criterio de oficio: el aval,
    # el renglón y el tipo de lista se cierran unos cuatro meses antes de inscribir.
    'fases': [
        {'id': 'posicionamiento', 'nombre': 'Posicionamiento', 'hasta': '2027-02-28',
         'que': 'Construir el lugar que ocupa antes de la campaña: la persuasión se hace temprano y en campaña casi no mueve a nadie.',
         'fichas': ['T14', 'T1', 'T20'], 'corte': 'criterio de oficio'},
        {'id': 'precampana', 'nombre': 'Precampaña', 'desde': '2027-03-01', 'hasta': '2027-07-30',
         'que': 'Cerrar el vehículo (aval, renglón, tipo de lista) e inscribirse, sin dejar de rendir cuentas.',
         'fichas': ['T3', 'T21'], 'corte': 'criterio de oficio hasta la inscripción; derivado de la ley después'},
        {'id': 'campana', 'nombre': 'Campaña', 'desde': '2027-07-31', 'hasta': '2027-10-24',
         'que': 'Movilizar a quien ya lo prefiere y concentrar la pauta cerca del día: su efecto dura pocos días.',
         'fichas': ['T13', 'T15'], 'corte': 'derivado (propaganda permitida tres meses antes)'},
        {'id': 'diad', 'nombre': 'Día D', 'desde': '2027-10-25', 'hasta': '2027-10-31',
         'que': 'Sacar a votar y cuidar el voto: hogares, transporte, tarjetón y testigos.',
         'fichas': ['T13', 'R2.2'], 'corte': 'criterio de oficio (la última semana)'},
        {'id': 'despues', 'nombre': 'Después de la elección', 'desde': '2027-11-01',
         'que': 'Escrutinio y, si ganó, la campaña permanente empieza con el cargo.', 'fichas': ['T19'], 'corte': 'ley'},
    ],
}

# La tabla de territorio (PLAN §4.3): dos ejes, cuatro cuadrantes, y la
# excepción de la baja participación (rama R2: el que ya lo prefiere y no sale).
CUADRANTES = {
    'retener': {'nombre': 'Retener', 'que': 'Ya lo prefiere y pesa mucho: cuidarlo con crédito visible y rendición de cuentas; no gastar en persuadirlo.', 'fichas': ['T14', 'T21', 'R3.1']},
    'retener-crecer': {'nombre': 'Retener y crecer', 'que': 'Es su nicho: rinde por encima del territorio aunque pese poco. Presencia y propuesta verificable para ensancharlo.', 'fichas': ['T21', 'R3.2']},
    'conocer': {'nombre': 'Hacerse conocer', 'que': 'Pesa mucho y ahí su votación no rinde por encima del territorio: es un problema de reconocimiento más que de afinidad.', 'fichas': ['T1', 'T20']},
    'movilizar': {'nombre': 'Movilizar', 'que': 'Vota poco: lo que rinde es el contacto cara a cara en el hogar y enseñar el tarjetón, no persuadir.', 'fichas': ['T13', 'R2.1', 'R2.2']},
    'no-gastar': {'nombre': 'No gastar ahí', 'que': 'Pesa poco y ahí su votación no rinde por encima del territorio: el contacto de campaña casi no persuade, así que no es donde se gana.', 'fichas': ['T14']},
}

# Acciones por fase. Cada una dice de qué fichas sale; sin fichas = «criterio
# de oficio». `lectura` las prefiere para una figura de ciudad o un trabajo de
# barrio; `lista` para lista abierta o cerrada.
ACCIONES = [
    {'fase': 'posicionamiento', 'principio': 'A7', 'texto': 'Una pieza de crédito por semana: un logro pequeño con fecha y prueba (una respuesta de una entidad, un arreglo, una proposición aprobada). Cuenta más cuántas veces que el tamaño.', 'fichas': ['R3.1', 'T20']},
    {'fase': 'posicionamiento', 'principio': 'A7', 'lectura': 'figura', 'texto': 'Tome posición pública en un tema de ciudad cada mes, con un debate o una proposición y un dato que nadie más tenga.', 'fichas': ['T20', 'T22']},
    {'fase': 'posicionamiento', 'principio': 'A7', 'lectura': 'barrio', 'texto': 'Un encuentro de rendición de cuentas por mes en un sector donde ya es fuerte, con una propuesta concreta y un compromiso que se pueda verificar; no un mitin.', 'fichas': ['T21', 'R3.2']},
    {'fase': 'posicionamiento', 'principio': 'A1', 'texto': 'Escoja un tema de consenso donde pueda competir por credibilidad y vuelva a él en cada aparición; los temas que dividen lo encierran en su nicho.', 'fichas': ['T2', 'T1']},
    {'fase': 'posicionamiento', 'principio': 'A6', 'texto': 'Arme la línea de base por puesto: participación y votación de la última elección donde va a trabajar, para medir después si su presencia movió algo.', 'fichas': ['T17', 'T18']},
    {'fase': 'posicionamiento', 'principio': 'A2', 'texto': 'Diga su tema en dos claves: la de su base y la de quien no comparte su agenda (cuidado, eficiencia).', 'fichas': ['T6', 'T5']},
    {'fase': 'posicionamiento', 'principio': 'A3', 'texto': 'Cuente cada propuesta como historia: por qué le importa a usted, a quién le pasa y qué hay que hacer ya.', 'fichas': ['T8', 'T7']},
    {'fase': 'posicionamiento', 'principio': 'A4', 'texto': 'Si contrasta, que sea con un dato, una propuesta y una fecha para revisarla; el ataque no rinde más y se devuelve.', 'fichas': ['T11']},
    {'fase': 'posicionamiento', 'principio': 'A5', 'texto': 'Ubique los hogares y las comunidades donde ya lo prefieren: son la base de la movilización de octubre.', 'fichas': ['T13', 'R2.2']},
    {'fase': 'posicionamiento', 'principio': 'A8', 'texto': 'Use las redes para que su base reparta lo que ya hace, no para convencer a quien no lo sigue.', 'fichas': ['T16', 'T24']},
    {'fase': 'precampana', 'principio': 'A1', 'lista': 'abierta', 'texto': 'Negocie el renglón y que la lista sea abierta antes de inscribirse: con voto preferente el rival principal está en su propia lista.', 'fichas': ['T3']},
    {'fase': 'precampana', 'principio': 'A1', 'lista': 'cerrada', 'texto': 'En lista cerrada la curul la decide el renglón: negocie el puesto antes de inscribirse, porque el voto personal no lo mueve.', 'fichas': ['T3']},
    {'fase': 'precampana', 'principio': 'A7', 'texto': 'Siga con la rendición de cuentas por sector, una por mes, primero donde ya es fuerte.', 'fichas': ['T21', 'R3.2']},
    {'fase': 'precampana', 'principio': 'A6', 'texto': 'Mida por puesto lo que rinde cada líder que lo acompaña antes de prometerle algo.', 'fichas': ['R3.3']},
    {'fase': 'precampana', 'principio': 'A5', 'texto': 'Arme la red de hogares y comunidades que van a movilizar en octubre: una persona del entorno pesa más que cualquier pieza.', 'fichas': ['T13', 'R2.1']},
    {'fase': 'campana', 'principio': 'A5', 'texto': 'Contacto cara a cara en los hogares donde ya lo prefieren; la visita resuelve la logística de votar y llega a todo el hogar.', 'fichas': ['T13', 'R2.2']},
    {'fase': 'campana', 'principio': 'A7', 'texto': 'Crédito frecuente: muchos logros pequeños anunciados por separado, cada uno con su prueba.', 'fichas': ['R3.1']},
    {'fase': 'campana', 'principio': 'A8', 'texto': 'Guarde la pauta para las últimas semanas: su efecto se esfuma en pocos días.', 'fichas': ['T15', 'T16']},
    {'fase': 'campana', 'principio': 'A1', 'texto': 'Mantenga los temas propios: la elección se gana cuando gira sobre los suyos.', 'fichas': ['T2']},
    {'fase': 'campana', 'principio': 'A6', 'texto': 'Compare la participación de los puestos con y sin trabajo de campaña contra la elección anterior.', 'fichas': ['T17']},
    {'fase': 'diad', 'principio': 'A5', 'texto': 'Movilización del día: transporte, recordatorio por hogar y cómo se marca el tarjetón donde más se pierden votos. Nunca revelar quién votó.', 'fichas': ['T13', 'R2.1']},
    {'fase': 'diad', 'principio': 'A6', 'texto': 'Testigos en los puestos donde están sus votos (el plan del día de la elección).', 'fichas': []},
    {'fase': 'despues', 'principio': 'A6', 'texto': 'Siga el escrutinio y guarde los resultados por puesto: son la línea de base de la siguiente.', 'fichas': ['T19']},
]

ADVERTENCIAS = [
    'La «modulación por arquetipo» y la matriz son hipótesis del equipo, no hallazgos de los autores: ninguno de estos textos estudió nuestros arquetipos.',
    'Las referencias están verificadas por ficha (autor, año, título y DOI), no por lectura completa: antes de citar una cifra frente a alguien, se abre la fuente.',
    'Casi toda la evidencia experimental es de Estados Unidos, donde es público quién votó. En Colombia no lo es: se trasladan principios, no guiones.',
    'Los anuncios movieron poco las preferencias sin importar a quién iban dirigidos (Coppock, Hill y Vavreck 2020): la modulación por arquetipo pesa en el contacto personal y en la agenda, no en la pauta.',
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anexo', default=str(ANEXO))
    a = ap.parse_args()
    if not a.anexo:
        sys.exit('falta el anexo: --anexo RUTA o C360_ESTRATEGIA_ANEXO')
    if not PROHIBIDO_TXT.exists():
        sys.exit(f'falta {PROHIBIDO_TXT.relative_to(RAIZ)} (los términos del caso que no pueden pasar al banco)')
    terminos = [t.strip() for t in PROHIBIDO_TXT.read_text(encoding='utf-8').splitlines() if t.strip()]
    PROHIBIDO = re.compile('|'.join(map(re.escape, terminos)), re.I)
    texto = Path(a.anexo).read_text(encoding='utf-8')
    # Solo la capa A, tronco y ramas: el caso (Nivel 3) y la capa B no pasan.
    capa_a = texto.split('# NIVEL 3', 1)[0]
    lineas = capa_a.splitlines()
    principios = leer_principios(texto)
    tronco = leer_tronco(lineas)
    ramas, fichas_rama = leer_ramas(lineas)
    matriz, notas = leer_matriz(texto)
    arquetipos = leer_arquetipos(texto)
    for c, (fam, ciudad, corte, aid) in EQUIVALENCIAS.items():
        arquetipos[c].update({'familia': fam, 'ciudad': ciudad, 'corte': corte, 'id': aid})

    fichas = tronco + fichas_rama
    ids = {f['id'] for f in fichas}
    # Cada ficha de un principio y de una acción tiene que existir.
    for p in principios:
        faltan = [f for f in p['fichas'] if f not in ids]
        if faltan:
            sys.exit(f'{p["id"]}: fichas que no existen {faltan}')
    for x in ACCIONES + list(CUADRANTES.values()) + CALENDARIO['fases']:
        faltan = [f for f in x.get('fichas', []) if f not in ids]
        if faltan:
            sys.exit(f'acción o fase con fichas que no existen: {faltan}')
    # El principio al que pertenece cada ficha del tronco (el de su sección).
    for p in principios:
        for f in fichas:
            if f['id'] in p['fichas'] and f['nivel'] == 'tronco':
                f['principio'] = p['id']
    for f in fichas_rama:
        f['principio'] = next((p['id'] for p in principios if f['rama'] in p['ramas'] or f['id'] in p['fichas']), None)
    if set(matriz) != set(CODIGOS) or any(len(v) != 8 for v in matriz.values()):
        sys.exit(f'la matriz no trae las {len(CODIGOS)} filas × 8 principios')

    banco = {
        'v': '2026-10-19',
        'que': 'Banco de estrategia de Candidato 360: capa A (principios durables) del árbol de literatura. Literatura pública; ningún candidato real.',
        'escala': {'2': 'central', '1': 'útil', '0': 'igual que el principio general', '-1': 'riesgo o contraproducente'},
        'advertencias': ADVERTENCIAS,
        'principios': principios,
        'fichas': fichas,
        'ramas': ramas,
        'arquetipos': arquetipos,
        'matriz': matriz,
        'notas_matriz': notas,
        'cuadrantes': CUADRANTES,
        'acciones': ACCIONES,
        'calendario': CALENDARIO,
    }
    salida = json.dumps(banco, ensure_ascii=False, indent=1)
    if PROHIBIDO.search(salida):
        sys.exit('⚠️ el banco trae algo del caso: ' + PROHIBIDO.search(salida)[0])
    SALIDA.write_text(salida + '\n', encoding='utf-8')
    print(f'{SALIDA.relative_to(RAIZ)}: {len(principios)} principios · {len(tronco)} fichas de tronco · '
          f'{len(fichas_rama)} de rama · {len(ramas)} ramas · {len(matriz)} filas de matriz · {len(salida) // 1024} KB')


if __name__ == '__main__':
    main()
