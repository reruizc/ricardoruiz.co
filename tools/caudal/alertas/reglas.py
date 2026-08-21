#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — reglas de sector y de nivel.

Aquí vive TODO el criterio editorial del motor: qué toca a cada sector, qué es
movimiento real y qué es ruido del registro, y por qué una señal es alta.

Dos principios, heredados del resto de Caudal:

  1. **Nada aparece por magia.** Cada señal viaja con `porque` — la frase que
     explica en lenguaje humano por qué quedó en ese nivel. Una alerta que dice
     "alto" sin decir por qué no se puede defender frente a un cliente.
  2. **Precisión antes que cobertura.** Es preferible callar una señal dudosa
     que mandar tres falsas: un digest con ruido se deja de leer a la semana, y
     un producto push que no se lee no existe.

El vocabulario por sector NO se inventa acá: se hereda de `caudal_core`
(SECTORES_CLIENTE + el tesauro SINONIMOS, ya curados y medidos contra títulos
reales). Este módulo solo los une, les hace higiene y los aplica.
"""

import os
import re
import sys
import unicodedata

_AQUI = os.path.dirname(os.path.abspath(__file__))
_CAUDAL = os.path.dirname(_AQUI)
if _CAUDAL not in sys.path:
    sys.path.insert(0, _CAUDAL)

# --- dependencias blandas de caudal_core -----------------------------------
# Se importan por su valor (un solo lugar donde viven los sectores y el
# tesauro), pero el motor NO puede caerse si el módulo cambia: hay fallback.
try:
    import caudal_core as _CC
    SECTORES_BASE = _CC.SECTORES_CLIENTE
    SINONIMOS = _CC.SINONIMOS
    _CC_OK = True
except Exception:                                             # pragma: no cover
    _CC_OK = False
    SINONIMOS = []
    SECTORES_BASE = [
        {'k': 'salud', 'nombre': 'Salud', 'comision': 'Séptima', 'sector_sanciones': 'salud',
         'temas': ['salud', 'medicamentos', 'aseguramiento en salud']},
        {'k': 'contratacion', 'nombre': 'Contratación e infraestructura', 'comision': 'Primera',
         'sector_sanciones': 'contratacion',
         'temas': ['contratacion', 'obras publicas', 'concesiones viales', 'licitacion']},
        {'k': 'financiero', 'nombre': 'Financiero', 'comision': 'Tercera',
         'sector_sanciones': 'financiero',
         'temas': ['sistema financiero', 'entidades financieras', 'mercado de valores']},
        {'k': 'energia', 'nombre': 'Energía y ambiente', 'comision': 'Quinta', 'sector_sanciones': '',
         'temas': ['energia', 'servicios publicos domiciliarios', 'transicion energetica']},
        {'k': 'educacion', 'nombre': 'Educación', 'comision': 'Sexta', 'sector_sanciones': '',
         'temas': ['educacion', 'universidades', 'instituciones educativas']},
        {'k': 'trabajo', 'nombre': 'Trabajo y pensiones', 'comision': 'Séptima', 'sector_sanciones': '',
         'temas': ['reforma laboral', 'regimen pensional', 'seguridad social']},
    ]

try:
    from clasificar import clasificar_titulo as _clasificar_titulo
except Exception:                                             # pragma: no cover
    def _clasificar_titulo(_t):
        return {'tipologia': 'ordinaria', 'crea_fondo': False,
                'jala_presupuesto_regional': False}

# El articulado ya leído del texto radicado. Es lo que convierte el «por qué» de
# «radicado en la Comisión Séptima» (un dato del registro) en «le crea esta
# obligación, sobre este sujeto, con esta multa detrás» (una razón para actuar).
import articulado as _ART                                    # noqa: E402

# Diccionario de empresas y gremios (388 entradas), en modo LECTURA. Es lo que
# convierte "un contrato grande" en "un contrato de una empresa que le importa
# a este cliente".
try:
    import empresas as _EMP
    EMPRESAS = _EMP.EMPRESAS
    _EMP_OK = True
except Exception:                                             # pragma: no cover
    _EMP_OK = False
    EMPRESAS = []

    class _EmpStub:
        @staticmethod
        def empresas_en(_q):
            return []

        @staticmethod
        def es_razon_social(_n, _e):
            return False

        @staticmethod
        def empieza_por_marca(_n, _e):
            return False
    _EMP = _EmpStub()


# ---------------------------------------------------------------------------
# 1) NORMALIZACIÓN Y MATCH
# ---------------------------------------------------------------------------

def norm(s):
    """Minúsculas sin tildes (misma convención que caudal_core._norm)."""
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return s.lower()


_SUFIJOS = ('idades', 'ciones', 'idad', 'cion', 'mente', 'ico', 'ica',
            'ios', 'ias', 'os', 'as', 'es', 'io', 'ia', 'o', 'a')


def _raiz(w):
    """Raíz conservadora — tolera flexión (medicamentos → medicament)."""
    for suf in _SUFIJOS:
        if w.endswith(suf) and len(w) - len(suf) >= 5:
            return w[:-len(suf)]
    return w


# palabras función que no aportan al match de una frase del vocabulario
_VACIAS = {'de', 'la', 'el', 'los', 'las', 'del', 'en', 'y', 'a', 'por', 'para',
           'con', 'un', 'una', 'al', 'su', 'sus', 'que', 'se', 'o'}

_TOKEN = re.compile(r'[a-z0-9]+')


def palabras_significativas(term):
    """Palabras de un término del vocabulario que DEBEN aparecer en el texto.

    Ojo: el umbral es ≥3 caracteres, no >3 como en caudal_core. Ahí las de 3 se
    descartan porque la búsqueda del usuario prioriza recall; acá descartarlas
    rompe la frase. Medido: 'habilitacion de ips' perdía el 'ips' (3 chars) y
    quedaba reducida a 'habilitacion', cuya raíz 'habilita' hacía match con
    "SE HABILITA LA PARTICIPACIÓN PRIVADA EN EL SISTEMA PENITENCIARIO" — una
    cárcel entrando al digest de salud.
    """
    return [w for w in _TOKEN.findall(norm(term))
            if len(w) >= 3 and w not in _VACIAS]


def casa_palabra(w, texto_norm):
    """La palabra (o su raíz) ARRANCA una palabra del texto.

    Match por inicio de palabra, no substring suelto: si no, 'pension' casa
    dentro de 'suspensión' y 'gas' dentro de 'gasto' (gotchas ya documentados
    en el proyecto).
    """
    return re.search(r'(?<![a-z0-9])' + re.escape(_raiz(w)), texto_norm) is not None


def casa_termino(term, texto_norm):
    """Un término del vocabulario casa si TODAS sus palabras significativas
    aparecen (AND). Es más estricto que la búsqueda libre a propósito: acá
    nadie está mirando la pantalla para descartar un falso positivo."""
    ws = palabras_significativas(term)
    if not ws:
        return False
    return all(casa_palabra(w, texto_norm) for w in ws)


# ---------------------------------------------------------------------------
# 2) VOCABULARIO POR SECTOR
# ---------------------------------------------------------------------------
# Cada sector del Radar hereda su vocabulario de dos fuentes ya curadas:
# sus `temas` (SECTORES_CLIENTE) + los tópicos del tesauro que le corresponden.
# Mapear a tópicos en vez de escribir términos nuevos hace que un cambio de
# vocabulario en el tesauro se herede solo, igual que hace empresas.py.

TOPICOS_POR_SECTOR = {
    'salud': ['salud / EPS e IPS', 'farmaceutico / medicamentos'],
    'contratacion': ['vivienda y construccion', 'puertos y logistica'],
    'financiero': ['sector financiero', 'seguros', 'tributario'],
    'energia': ['energia y servicios publicos', 'ambiental / medio ambiente',
                'mineria e hidrocarburos', 'agua y saneamiento'],
    'educacion': ['educacion superior'],
    'trabajo': ['laboral', 'pensiones y cesantias', 'economia del cuidado'],
}

# Términos que el tesauro trae pero que en un radar por sector generan más
# ruido que señal. Curados contra casos MEDIDOS, no hipótesis:
#   'regalias' → el Sistema General de Regalías es finanzas territoriales; sacó
#   "FORTALECE LA AUTONOMÍA TERRITORIAL … CICLO DE PROYECTOS EN EL SGR" al
#   digest de energía.
TERMINOS_FUERA = {
    'energia': {'regalias'},
}

# Refuerzos propios del radar (lo que el tesauro no cubre porque su foco es la
# búsqueda del usuario, no la vigilancia sectorial).
TERMINOS_EXTRA = {
    'contratacion': ['contratacion estatal', 'contratacion publica', 'pliego de condiciones',
                     'licitacion publica', 'interventoria', 'obra publica',
                     'asociacion publico privada'],
    'salud': ['eps', 'ips', 'supersalud', 'plan de beneficios', 'upc',
              'invima', 'salud mental'],
    'financiero': ['superintendencia financiera', 'sistema pensional privado'],
    'trabajo': ['pension', 'pensional', 'colpensiones', 'cesantias', 'sindical'],
    'educacion': ['icetex', 'sena', 'educacion basica', 'educacion media'],
    'energia': ['creg', 'upme', 'ecopetrol', 'tarifa de energia'],
}

_VOCAB_CACHE = {}


# ---------------------------------------------------------------------------
# 2.b) DESTINOS · el sector es el fallback, el cliente es el producto
# ---------------------------------------------------------------------------
# Un "destino" es a quién se le arma un digest. Hay dos clases y comparten
# exactamente la misma forma, por eso todo el motor las trata igual:
#
#   tipo 'sector'  — los 6 presets. Vocabulario curado, sin dueño, sin correo
#                    propio. Es lo que corre cuando no hay ningún cliente.
#   tipo 'cliente' — un perfil guardado por cuenta (worker rr-auth). Trae SUS
#                    temas, SUS empresas vigiladas y el correo de su dueño.
#
# El vocabulario de un cliente sale de dos fuentes, igual que en el radar de la
# Vista Cliente: sus `temas` tal cual, y los TÓPICOS del tesauro que activan sus
# empresas vigiladas (la cara TEMA del diccionario). Nadie legisla «Uber»,
# legisla «plataformas tecnológicas».
#
# ⚠ El ALIAS de la empresa nunca entra como término de vocabulario: el match va
# por raíz de palabra y «claro» casaría dentro de «declaró». Para el Congreso la
# empresa vale por su tópico; su nombre propio solo se usa en Regulatorio,
# Contratación y Prensa, donde el registro sí la nombra.

def destino_desde_sector(s):
    return {'k': s['k'], 'nombre': s.get('nombre', s['k']),
            'comision': s.get('comision', ''),
            'sector_sanciones': s.get('sector_sanciones', ''),
            'temas': list(s.get('temas', [])), 'empresas': [],
            'tipo': 'sector', 'correo': '', 'plan': '', 'cadencia': 'cada-corrida'}


_DESTINOS = [destino_desde_sector(s) for s in SECTORES_BASE]


def registrar_destinos(lista):
    """Reemplaza los destinos activos. Vaciar la lista vuelve a los 6 sectores."""
    global _DESTINOS
    _DESTINOS = list(lista) if lista else [destino_desde_sector(s) for s in SECTORES_BASE]
    _VOCAB_CACHE.clear()
    _EMPRESAS_CACHE.clear()
    return _DESTINOS


def destinos():
    """[{k, nombre, comision, sector_sanciones, temas, empresas, tipo…}]."""
    return _DESTINOS


def destino(k):
    for d in _DESTINOS:
        if d['k'] == k:
            return d
    return None


# Nombres viejos: el resto del motor y las pruebas los siguen usando y a un
# sector-destino le da igual cómo lo llamen.
sectores = destinos
sector = destino


_EMPRESAS_CACHE = {}
_EMP_POR_K = {e['k']: e for e in EMPRESAS}


def empresas_de(k):
    """Entradas del diccionario que vigila este destino, o None = todas.

    None y [] NO son lo mismo, y la diferencia importa:
      · None (sector) → se mira contra las 388 del diccionario, que es el
        comportamiento histórico: «el proveedor es una empresa conocida».
      · lista (cliente con vigiladas) → solo las suyas.
      · [] (cliente sin vigiladas) → ninguna, y entonces la identidad no
        dispara nada. Un cliente que no declaró vigiladas no quiere alertas
        sobre empresas ajenas: quiere sus temas.
    """
    if k in _EMPRESAS_CACHE:
        return _EMPRESAS_CACHE[k]
    d = destino(k) or {}
    if d.get('tipo') != 'cliente':
        _EMPRESAS_CACHE[k] = None
        return None
    out = [_EMP_POR_K[x] for x in (d.get('empresas') or []) if x in _EMP_POR_K]
    _EMPRESAS_CACHE[k] = out
    return out


def claves_desconocidas(claves):
    """Llaves de empresa que el diccionario NO tiene.

    El worker valida la FORMA de la llave, no que exista: quien vive con el
    diccionario es este lado. Sin esto, un perfil con «nueva eps» (la llave real
    es `nuevaeps`) se quedaría sin vigiladas EN SILENCIO y su dueño creería que
    Caudal la está mirando. Nada aparece por magia — y nada desaparece por magia.
    """
    return [x for x in (claves or []) if x not in _EMP_POR_K]


def topicos_de_empresas(claves):
    """Llaves del tesauro que activan estas empresas (solo su núcleo)."""
    if not _EMP_OK or not claves:
        return []
    emps = [_EMP_POR_K[x] for x in claves if x in _EMP_POR_K]
    try:
        return _EMP.topicos_de(emps)
    except Exception:                                         # pragma: no cover
        return []


def vocabulario(k):
    """Términos del destino, ya con higiene aplicada. Cacheado."""
    if k in _VOCAB_CACHE:
        return _VOCAB_CACHE[k]
    s = destino(k) or {}
    idx = {t['k']: t for t in SINONIMOS}
    terms = list(s.get('temas', []))
    for tk in TOPICOS_POR_SECTOR.get(k, []):
        if tk in idx:
            terms += idx[tk]['terms']
    # cliente: los tópicos de SUS vigiladas entran al vocabulario del Congreso
    for tk in topicos_de_empresas(s.get('empresas')):
        if tk in idx:
            terms += idx[tk]['terms']
    terms += TERMINOS_EXTRA.get(k, [])
    fuera = TERMINOS_FUERA.get(k, set())
    out, visto = [], set()
    for t in terms:
        tn = norm(t).strip()
        if not tn or tn in visto or tn in fuera:
            continue
        if not palabras_significativas(tn):      # término que se anula solo
            continue
        visto.add(tn)
        out.append(tn)
    _VOCAB_CACHE[k] = out
    return out


def hits_distintos(hits):
    """Quita los términos que no agregan evidencia nueva.

    'salud' y 'salud mental' casan sobre el mismo hecho: el segundo contiene
    todas las palabras del primero. Contarlos como dos frentes inflaba el nivel
    (y en pantalla se leía como una repetición: «salud · salud mental»). Se
    conserva el término más corto de cada familia.
    """
    ws = [(t, set(palabras_significativas(t))) for t in hits]
    ws.sort(key=lambda x: len(x[1]))
    out = []
    for t, w in ws:
        if any(prev.issubset(w) for _t, prev in out):
            continue
        out.append((t, w))
    orden = {t: i for i, t in enumerate(hits)}
    return sorted([t for t, _w in out], key=lambda t: orden.get(t, 0))


def destinos_de(texto, minimo=1):
    """Destinos que toca un texto → [(k, [términos que casaron])].

    `minimo` = cuántos términos distintos exige para contar el destino. El motor
    usa 1 para decidir pertenencia y ≥2 como señal de fuerza (ver nivel).
    """
    tn = norm(texto or '')
    if not tn:
        return []
    out = []
    for s in _DESTINOS:
        k = s['k']
        hits = hits_distintos([t for t in vocabulario(k) if casa_termino(t, tn)])
        if len(hits) >= minimo:
            out.append((k, hits))
    return out


sectores_de = destinos_de


# ---------------------------------------------------------------------------
# 3) CONGRESO · qué es movimiento y qué es ruido del registro
# ---------------------------------------------------------------------------
# Medido sobre los `cambios` reales de las novedades diarias (71 deltas):
#   texto_radicado_url 37 · titulo 13 · comision 9 · estado 3 · autor 3 · fechas 6
# El grueso del volumen (URL del PDF y título) es fontanería del registro, no
# trámite. Si entra al digest, entierra las 6 fechas de aprobación que sí
# importan.

CAMPOS_RUIDO = {
    'texto_radicado_url', 'titulo', 'autor', 'conceptos_senado', 'conceptos_camara',
    'exposicion_de_motivos', 'cuatrenio', 'legislatura', 'origen', 'tipo_de_ley',
    '_pdf_local', '_pdf_bytes', '_pdf_capa', '_visto', '_detalle_ok', 'link_web',
}

# campo → (nivel base, etiqueta legible)
CAMPOS_TRAMITE = {
    'estado':                                    ('medio', 'cambio de estado'),
    'comision':                                  ('medio', 'asignación de comisión'),
    'comisiones':                                ('medio', 'asignación de comisión'),
    'fecha_de_envio_comision':                   ('medio', 'enviado a comisión'),
    'ponente_primer_debate':                     ('medio', 'ponente designado · primer debate (Senado)'),
    'ponente_segundo_debate':                    ('medio', 'ponente designado · segundo debate (Senado)'),
    'ponente_primer_debate_camara':              ('medio', 'ponente designado · primer debate (Cámara)'),
    'ponente_segundo_debate_camara':             ('medio', 'ponente designado · segundo debate (Cámara)'),
    'primera_ponencia':                          ('medio', 'ponencia publicada en Gaceta'),
    'segunda_ponencia':                          ('medio', 'ponencia publicada en Gaceta'),
    'fecha_de_aprobacion_primer_debate':         ('alto',  'APROBADO en primer debate (Senado)'),
    'fecha_de_aprobacion_primer_debate_camara':  ('alto',  'APROBADO en primer debate (Cámara)'),
    'fecha_de_aprobacion_segundo_debate':        ('alto',  'APROBADO en segundo debate (Senado)'),
    'fecha_de_aprobacion_segundo_debate_camara': ('alto',  'APROBADO en segundo debate (Cámara)'),
    'conciliador_senado':                        ('alto',  'conciliación (Senado)'),
    'conciliador_camara':                        ('alto',  'conciliación (Cámara)'),
    'fecha_de_conciliacion_senado':              ('alto',  'conciliación (Senado)'),
    'fecha_de_conciliacion_camara':              ('alto',  'conciliación (Cámara)'),
    'conciliacion':                              ('alto',  'texto de conciliación'),
    'texto_plenaria':                            ('alto',  'texto aprobado en plenaria'),
    'objeciones':                                ('alto',  'objeciones del Gobierno'),
    'gacetas':                                   ('bajo',  'nueva gaceta asociada'),
}

# estados que sí son un punto de inflexión (no el relleno del registro)
_ESTADO_DECISIVO = re.compile(
    r'aprobad|sancionad|archivad|retirad|concilia|plenaria|ponencia|debate|'
    r'objetad|constitucional')


def deltas_utiles(deltas):
    """Filtra los deltas de un `cambio` a los que son trámite de verdad.

    Devuelve [{campo, etiqueta, nivel, antes, ahora}] y descarta:
      · campos de fontanería (CAMPOS_RUIDO)
      · vaciados: `ahora` en blanco cuando `antes` tenía valor. Es el registro
        parpadeando — medido: 9 de 71 deltas. El proyecto 083/26 perdió título
        y URL de un día para otro sin que pasara nada en el trámite.
    """
    out = []
    for campo, v in (deltas or {}).items():
        if campo in CAMPOS_RUIDO:
            continue
        antes = str((v or {}).get('antes') or '').strip()
        ahora = str((v or {}).get('ahora') or '').strip()
        if not ahora:
            continue                                   # vaciado = parpadeo
        if antes == ahora:
            continue
        nivel, etiqueta = CAMPOS_TRAMITE.get(campo, ('bajo', campo.replace('_', ' ')))
        if campo == 'estado':
            if not antes:
                # el registro llenó un campo que estaba vacío: es alta del
                # proyecto, no movimiento. Ya se alertó como radicado nuevo.
                nivel, etiqueta = 'bajo', 'estado registrado por primera vez'
            elif _ESTADO_DECISIVO.search(norm(ahora)):
                nivel, etiqueta = 'alto', 'cambio de estado'
        elif not antes and nivel == 'alto':
            # una fecha de aprobación que aparece de la nada SÍ es el evento
            # (el registro no la tenía porque el debate no había ocurrido).
            pass
        out.append({'campo': campo, 'etiqueta': etiqueta, 'nivel': nivel,
                    'antes': antes[:180], 'ahora': ahora[:180]})
    return out


_ORDEN_NIVEL = {'alto': 3, 'medio': 2, 'bajo': 1}


def peor_nivel(niveles):
    """El nivel más alto de una lista (para agregar deltas de un proyecto)."""
    if not niveles:
        return 'bajo'
    return max(niveles, key=lambda n: _ORDEN_NIVEL.get(n, 0))


def orden_nivel(n):
    return _ORDEN_NIVEL.get(n, 0)


# ---------------------------------------------------------------------------
# 4) NIVEL POR PILAR
# ---------------------------------------------------------------------------

UMBRAL_MULTA = 100_000_000           # COP


# --- empresas vigiladas -----------------------------------------------------

# El argumento `empresas` de las tres funciones de abajo es el universo contra
# el que se busca: None = las 388 del diccionario (comportamiento de sector),
# una lista = solo las que vigila ese cliente. Es lo que convierte «alguien
# conocido apareció» en «apareció TU empresa», que es la alerta que se vende.

def empresa_en_texto(texto, empresas=None):
    """Empresa/gremio nombrada en un texto libre (titulares).

    Match por alias como palabra completa — 'claro' no casa dentro de
    'CLAROS MURCIA'. Devuelve la primera o None.
    """
    if not _EMP_OK or not texto:
        return None
    encontradas = _EMP.empresas_en(texto)
    if empresas is not None:
        permitidas = {e['k'] for e in empresas}
        encontradas = [e for e in encontradas if e['k'] in permitidas]
    return encontradas[0] if encontradas else None


def sancionado_vigilado(nombre, empresas=None):
    """¿La entidad destinataria de un acto regulatorio es una vigilada?

    Acá sí sirve `casa_registro` (palabra completa + vetos): el campo
    `sancionado` son decenas de nombres de empresa, no millones de cédulas
    como el proveedor de SECOP. Solo aplica con lista explícita: preguntarlo
    contra las 388 devolvería «es una empresa conocida», que no es noticia.
    """
    if not _EMP_OK or not nombre or not empresas:
        return None
    for e in empresas:
        try:
            if _EMP.casa_registro(e, nombre):
                return e
        except Exception:                                     # pragma: no cover
            continue
    return None


def proveedor_vigilado(nombre, empresas=None):
    """¿El proveedor de un contrato ES una empresa del diccionario?

    Usa `es_razon_social`, la regla ESTRICTA, no el match por alias. En SECOP el
    proveedor son millones de filas dominadas por personas naturales y las
    marcas son apellidos corrientes: medido, 42/42 de los que casaban por alias
    con «uber» eran gente llamada Uber. La regla estricta exige que el nombre
    SEA la empresa, no que la contenga.
    """
    if not _EMP_OK or not nombre:
        return None
    for e in (EMPRESAS if empresas is None else empresas):
        if _EMP.es_razon_social(nombre, e):
            return e
    return None


def entidad_vigilada(nombre, empresas=None):
    """Igual pero para la ENTIDAD contratante, donde la regla puede ser laxa:
    ahí no hay personas naturales y la marca encabeza la dependencia
    ('SENA REGIONAL VALLE …' es el SENA comprando)."""
    if not _EMP_OK or not nombre:
        return None
    for e in (EMPRESAS if empresas is None else empresas):
        if _EMP.empieza_por_marca(nombre, e):
            return e
    return None


# --- categorías de contratación --------------------------------------------
# SECOP no trae UNSPSC en el feed que consume el Radar, así que la categoría se
# deriva del objeto. Es gruesa a propósito: solo tiene que ser lo bastante
# estable para responder "¿esta entidad ya compraba esto?".
CATEGORIAS_CONTRATO = [
    ('obra',            ['obra', 'construccion', 'pavimenta', 'infraestructura',
                         'mantenimiento vial', 'via', 'puente', 'acueducto']),
    ('interventoria',   ['interventoria', 'supervision tecnica']),
    ('tecnologia',      ['software', 'licenciamiento', 'tecnologia', 'informatica',
                         'sistema de informacion', 'plataforma', 'datos', 'nube']),
    ('salud_servicios', ['servicios de salud', 'atencion en salud', 'medicamento',
                         'insumos medicos', 'dispositivo medico', 'hospital']),
    ('dotacion',        ['suministro', 'dotacion', 'adquisicion', 'compra',
                         'insumos', 'equipos']),
    ('consultoria',     ['consultoria', 'estudios', 'diseno', 'asesoria']),
    ('servicios_prof',  ['prestacion de servicios profesionales', 'apoyo a la gestion',
                         'servicios profesionales']),
]


def categoria_contrato(objeto):
    o = norm(objeto or '')
    for cat, claves in CATEGORIAS_CONTRATO:
        if any(casa_palabra(c, o) if ' ' not in c else casa_termino(c, o)
               for c in claves):
            return cat
    return 'otros'


# ---------------------------------------------------------------------------
# 3.b) EL «POR QUÉ» DE UN PROYECTO · lo que dice su articulado
# ---------------------------------------------------------------------------
# El defecto que esto cierra: la razón de casi toda señal alta del Congreso era
# «radicado en la Comisión Séptima». Eso explica por qué el motor la marcó, no
# por qué le importa a quien la lee — un gremio no actúa porque un proyecto haya
# caído en una comisión u otra, actúa porque le aparece una obligación nueva,
# con un plazo, sobre alguien, y a veces con una multa detrás.
#
# Esa lectura ya existe (`articulado.py`), así que la razón sale de ahí siempre
# que el texto se haya leído. Y cuando NO se ha leído se dice, que es
# información honesta: «todavía no hemos leído su texto» le dice al lector
# exactamente cuánto vale lo que está viendo. El genérico disfrazado de razón,
# no.

def _limpio(s, n=None):
    """Espacios colapsados y sin punto final. Sin tocar mayúsculas: bajarle la
    inicial convertía «EPS, IPS y gestores» en «ePS, IPS y gestores». Los
    sujetos van entre comillas, así que no necesitan encajar en la frase."""
    t = re.sub(r'\s+', ' ', str(s or '')).strip().rstrip('.').strip()
    return recorte_palabra(t, n) if n else t


def recorte_palabra(s, n):
    """Corta en frontera de palabra. Un `[:70]` pelado dejaba «…de pacientes c»,
    que no se lee como texto acortado sino como dato roto."""
    s = (s or '').strip()
    if len(s) <= n:
        return s
    corte = s[:n]
    esp = corte.rfind(' ')
    return (corte[:esp] if esp > n * 0.6 else corte).rstrip(' ,;:·') + '…'


# Quién es el obligado cambia por completo qué tiene que hacer el cliente. Si la
# obligación recae en un ministerio, el gremio no tiene nada que cumplir: tiene
# algo que vigilar (la reglamentación). Confundir las dos cosas es prometer
# puntería que no se tiene — medido: en el PL 101/26 las seis obligaciones son
# del Ministerio de Salud, y llamar a la primera «la que lo toca» le diría a una
# EPS que le crearon un deber que no le crearon.
_ES_ESTADO = re.compile(
    r'ministerio|gobierno nacional|presidencia|superintendenc|congreso|'
    r'entidad(es)? estatal|entidades territoriales|departamento administrativo|'
    r'agencia nacional|instituto nacional|unidad administrativa|comision de regulacion|'
    r'alcaldia|gobernacion|defensoria|procuradur|contralor|fiscalia|registradur|'
    r'\bdian\b|\badres\b|\binvima\b|consejo nacional|rama judicial')


def es_obligado_estatal(quien):
    return bool(_ES_ESTADO.search(norm(quien or '')))


def obligacion_pertinente(art, k=None):
    """(obligación, clase) — la que más le toca a ESTE destino, y de quién es.

    Un proyecto puede crear ocho obligaciones y que solo una recaiga sobre el
    cliente. Mandarle la primera del texto es volver a hablar en general. Se
    puntúa `sobre_quien` contra el vocabulario del destino y contra el nombre de
    sus vigiladas, penalizando fuerte al obligado estatal.

    clase ∈ 'propia'  (casó con este destino y el obligado es un particular)
            'estado'  (el obligado es el Estado: hay qué vigilar, no qué cumplir)
            'primera' (nada casó: es la primera del texto y se dice así)
    """
    obs = _ART.obligaciones(art)
    if not obs:
        return None, 'ninguna'

    # El deber que recae sobre un particular SIEMPRE gana al que recae sobre el
    # Estado, aunque el vocabulario del cliente case mejor con el segundo. Es lo
    # que se le vende: qué le toca HACER. Medido en el proyecto que modifica la
    # Ley 80 — el vocabulario de contratación casaba con «Entidad estatal
    # contratante» y no con «Entidad contratista», así que sin esta regla el
    # correo le mostraba al contratista un deber de la entidad que lo contrata.
    privadas = [o for o in obs if not es_obligado_estatal(o.get('sobre_quien'))]
    universo = privadas or obs

    if k:
        vocab = vocabulario(k)
        nombres = [norm(e.get('nombre', '')) for e in (empresas_de(k) or [])]
        mejor, mejor_p = None, 0
        for o in universo:
            qn = norm(o.get('sobre_quien') or '')
            if not qn:
                continue
            p = sum(1 for t in vocab if casa_termino(t, qn))
            p += 2 * sum(1 for n in nombres if n and n in qn)
            if p > mejor_p:
                mejor, mejor_p = o, p
        if mejor is not None:
            return mejor, ('propia' if privadas else 'estado')

    o = universo[0]
    # Sin match de vocabulario no se reclama puntería: es la primera del texto.
    return o, ('primera' if privadas else 'estado')


def razon_articulado(art, k=None):
    """(nivel_sugerido, porque) leídos del articulado. `art` ya viene filtrado.

    El orden no es estético: primero lo que obliga a hacer algo (y a quién),
    después lo que castiga no hacerlo, y de último lo que cambia en el
    ordenamiento. Es el orden en que un jefe jurídico lee un proyecto.
    """
    obs = _ART.obligaciones(art)
    sanc = _ART.sanciones(art)
    mods = _ART.modifica(art)

    def _castigo():
        """Cómo se nombra el castigo. Que exista un régimen sancionatorio ya es
        la señal, aunque el texto no cuantifique la multa."""
        det = _ART.sancion_legible(sanc[0])
        if det:
            return f'régimen sancionatorio ({_limpio(det, 70)})'
        return 'un régimen sancionatorio que el texto no cuantifica'

    if obs:
        o, clase = obligacion_pertinente(art, k)
        quien = _limpio(o.get('sobre_quien'), 90)
        texto = _limpio(o.get('obligacion'), 150)
        n = len(obs)
        cuantas = ('crea una obligación nueva' if n == 1
                   else f'crea {n} obligaciones nuevas')
        # Qué se dice de la obligación elegida depende de a quién obliga: es la
        # diferencia entre «prepárese a cumplir» y «vigile la reglamentación».
        cual = {'propia': 'la que lo toca', 'estado': 'la principal',
                'primera': 'la primera'}.get(clase, 'la primera')
        sobre = f' recae en «{quien}» y' if quien else ''
        frase = f'{cuantas}; {cual}{sobre} dice: «{texto}»'
        if sanc:
            frase += f', con {_castigo()}'
        if clase == 'estado':
            # Un obligado estatal NO es menos importante: es otra jugada. El
            # gremio no tiene qué cumplir, tiene qué incidir antes de que se
            # reglamente. Va de último para que cierre la frase, no la parta.
            frase += (' — ojo: en este texto los obligados son entidades del Estado, '
                      'no el sector; lo que hay es reglamentación por vigilar')
        if sanc:
            return 'alto', frase
        return ('estado' if clase == 'estado' else 'obliga'), frase

    if sanc:
        conducta = _limpio(sanc[0].get('conducta'), 110)
        frase = f'no crea obligaciones nuevas, pero sí {_castigo()}'
        return 'alto', frase + (f' · castiga: «{conducta}»' if conducta else '')

    if mods:
        cual = ' · '.join(_ART.norma_legible(m) for m in mods[:2])
        return 'modifica', (f'no crea obligaciones nuevas, pero cambia norma vigente: '
                            f'{_limpio(cual, 160)}')

    return 'vacio', ('leímos su texto y no crea obligaciones, ni sanciones, ni toca '
                     'una norma vigente')


def razon_sin_articulado(hits, comision, sector_k):
    """Lo honesto cuando no se leyó el texto: decir de dónde sale lo que se dice.

    Nunca «radicado en la Comisión Séptima» a secas. La comisión entra como dato
    de contexto, después de haber advertido que esto sale del título.
    """
    s = sector(sector_k) or {}
    partes = ['todavía no hemos leído su texto: esto sale del título']
    if hits:
        cuales = ' · '.join(f'«{h}»' for h in hits[:3])
        partes.append(f'que toca {cuales}')
    com = str(comision or '').strip()
    if com:
        # Senado manda «SEPTIMA» y Cámara «Comisión Primera Constitucional
        # Permanente»: anteponer «Comisión» a ciegas producía «va a la Comisión
        # Comisión Primera…».
        etiqueta = com.title() if norm(com).startswith('comision') else f'Comisión {com.title()}'
        propia = norm(s.get('comision', ''))
        if propia and propia in norm(com):
            partes.append(f'va a la {etiqueta}, la del sector')
        else:
            partes.append(f'va a la {etiqueta}')
    return ', '.join(partes)


def nivel_radicado(titulo, comision, sector_k, hits, art=None):
    """Nivel de un proyecto recién radicado que toca el sector.

    Un radicado nuevo es la ventana de incidencia clásica: llegar antes de la
    ponencia. Pero no todo radicado es igual — el Congreso produce mucho honor
    y mucho día nacional, y eso no mueve la aguja de ningún gremio.

    Con articulado leído el nivel deja de depender del envase (comisión,
    tipología) y pasa a depender del contenido: obligación + sanción es lo más
    alto que hay, porque es lo único que obliga a alguien a hacer algo distinto
    mañana. Sin articulado el criterio es EXACTAMENTE el de antes — no se toca
    lo que se ve, solo se deja de llamar «razón» a un dato del registro.
    """
    tip = _clasificar_titulo(titulo or {})
    tipologia = tip.get('tipologia', 'ordinaria')
    s = sector(sector_k) or {}
    com_sector = norm(s.get('comision', ''))
    com = norm(comision or '')
    en_comision = bool(com_sector and com_sector in com)

    if tipologia == 'honores':
        return 'bajo', 'proyecto de honores o conmemorativo — sin efecto regulatorio', tipologia

    if art:
        clase, porque = razon_articulado(art, sector_k)
        if clase == 'alto':                       # obligación + sanción, o sanción
            nivel = 'alto'
        elif clase == 'obliga':
            nivel = 'alto' if (tipologia == 'reforma' or en_comision or len(hits) >= 2) else 'medio'
        elif clase == 'estado':
            # Obliga solo al Estado y sin sanciones: hay qué vigilar, no qué
            # cumplir. Alto se reserva para lo que el cliente tiene que hacer.
            nivel = 'alto' if tipologia == 'reforma' else 'medio'
        elif clase == 'modifica':
            nivel = 'alto' if tipologia == 'reforma' else 'medio'
        else:                                      # se leyó y no hay nada que cumplir
            nivel = 'medio'
        return nivel, porque, tipologia

    porque = razon_sin_articulado(hits, comision, sector_k)
    if tipologia == 'reforma':
        return 'alto', 'reforma estructural que toca el sector · ' + porque, tipologia
    if en_comision or len(hits) >= 2:
        return 'alto', porque, tipologia
    return 'medio', porque, tipologia


# ---------------------------------------------------------------------------
# 3.c) DOS SEÑALES CON LA MISMA RAZÓN NO SON DOS RAZONES
# ---------------------------------------------------------------------------
# Mismo criterio que `hits_distintos` aplicado un nivel más arriba: ahí se
# quitaban los términos que no agregaban evidencia nueva, acá se agrega lo que
# hace falta para que dos señales dejen de leerse como la misma.
#
# Un digest donde cinco proyectos dicen «todavía no hemos leído su texto» se lee
# como un error de plantilla, aunque cada frase sea cierta. La salida no es
# inventar diferencias: es bajar al primer hecho que de verdad los separe.

def _facetas(ev):
    """Hechos que pueden distinguir una señal de otra, del más concreto al menos.

    El orden importa: sobre quién recae una obligación distingue mucho más que
    el nombre del autor, y por eso va primero.
    """
    art = (ev.get('meta') or {}).get('articulado') or {}
    out = []

    o = (ev.get('meta') or {}).get('obligacion_clave') or {}
    quien = _limpio(o.get('sobre_quien'))
    if quien:
        out.append((f'recae en «{quien}»', 90))

    mods = _ART.modifica(art)
    if mods:
        out.append(('toca ' + _ART.norma_legible(mods[0]), 120))

    ents = _ART.entidades_vigilantes(art)
    if ents:
        out.append(('lo vigila ' + ents[0], 90))

    sanc = _ART.sanciones(art)
    if sanc:
        castigo = _ART.sancion_legible(sanc[0])
        if castigo:
            out.append(('sanción: ' + castigo, 90))

    hits = (ev.get('meta') or {}).get('hits') or []
    if hits:
        out.append(('toca ' + ' · '.join(f'«{h}»' for h in hits[:2]), 80))

    autor = re.sub(r'\s+', ' ', str((ev.get('meta') or {}).get('autor') or '')).strip()
    if autor:
        out.append(('lo firma ' + autor.rstrip('. ').title()[:60], 70))

    com = str((ev.get('meta') or {}).get('comision') or '').strip()
    if com:
        out.append(('Comisión ' + com.title(), 40))

    estado = _limpio((ev.get('meta') or {}).get('estado'))
    if estado:
        out.append((estado.lower(), 60))
    return out


def distinguir(items):
    """Añade a cada señal lo mínimo que la separa de las que dicen lo mismo.

    Solo actúa sobre grupos que comparten razón, y solo agrega una faceta si
    ESA faceta tiene valores distintos dentro del grupo: repetir «lo vigila la
    Supersalud» en cinco señales no distingue nada y alarga el correo.
    """
    grupos = {}
    for ev in items:
        grupos.setdefault(norm(ev.get('porque') or '')[:160], []).append(ev)

    for grupo in grupos.values():
        if len(grupo) < 2:
            continue
        facetas = [_facetas(ev) for ev in grupo]
        # cuántas señales del grupo comparten cada faceta: la que las comparte
        # TODAS no separa a nadie y solo alargaría el correo.
        veces = {}
        for f in facetas:
            for texto, _tope in f:
                veces[texto] = veces.get(texto, 0) + 1
        for ev, f in zip(grupo, facetas):
            for texto, tope in f:
                if veces.get(texto, 0) < len(grupo):
                    ev['porque'] = ev['porque'].rstrip(' ·') + f' · {texto[:tope]}'
                    break

        # Lo que quede idéntico después de eso es que de verdad está ahí por lo
        # mismo (dos radicados de Cámara el mismo día, sin comisión asignada, sin
        # autor y sin texto leído: no hay un solo dato que los separe). Inventar
        # una diferencia sería peor que repetir; lo que se hace es no repetir la
        # frase larga tres veces, que es lo que se lee como plantilla rota.
        vistas = {}
        for ev in grupo:
            clave = norm(ev.get('porque') or '')
            if clave in vistas:
                ev['porque'] = ('mismo caso que otra señal de este bloque: '
                                + recorte_palabra(vistas[clave], 70))
            else:
                vistas[clave] = ev.get('porque') or ''
    return items


# --- ¿el acto fija una regla, o resuelve un expediente? ----------------------
# `tipo_acto` NO alcanza para saberlo, y creer que sí fue el defecto que inundó
# los digests: la regla anterior marcaba ALTO toda «resolucion» con la frase
# "cambia la regla para todos los vigilados del sector". Eso es cierto en una
# superintendencia (una circular externa instruye a todos sus vigilados) y es
# FALSO en la ANLA, cuya resolución es el instrumento con el que resuelve un
# expediente individual. Medido sobre las 25.426 resoluciones de ANLA: 5 son
# normas generales — el 0,02%. El otro 99,98% eran alertas ALTAS que afirmaban
# algo falso en la línea que debía justificarlas.
#
# Lo que sí discrimina es el VERBO del acto, y vive al principio del texto.

_ENCABEZADO = re.compile(
    r'^por\s+(la\s+cual(es)?|medio\s+de\s+la\s+cual|el\s+cual|las\s+cuales)\s*')

# Coletilla de cierre. Aparece al final de casi todo acto de ANLA y usa los
# mismos verbos que una norma general, así que sin quitarla "se modifica una
# licencia ambiental Y SE ADOPTAN otras determinaciones" —un acto sobre una sola
# empresa— se clasifica como norma que obliga al sector entero. Medido: son 281
# falsos «general» de ANLA, casi el doble de los generales verdaderos.
_COLETILLA = re.compile(
    r'\s*(,)?\s*y\s+se\s+(adoptan?|toman?|dictan?|dispone[n]?)\s+'
    r'(otras|unas|las)?\s*(determinaciones|disposiciones|medidas).*$')

# Resuelve un expediente concreto: le pasa a UN titular, no al sector.
_ACTO_PARTICULAR = (
    'se emite dictamen', 'se emite un dictamen', 'se otorga', 'se niega', 'se autoriza',
    'se aprueba', 'se certifica', 'se acepta', 'se acoge', 'se acredita', 'se evalua',
    'se decide una solicitud', 'se decide sobre', 'se resuelve un recurso',
    'se resuelve el recurso', 'se resuelve una solicitud', 'se levanta', 'se desiste',
    'se declara', 'se decide', 'se tiene en cuenta el cambio', 'se efectua', 'se efectuan',
    'se realiza un ajuste', 'se realiza el ajuste', 'se realizan los ajustes',
    'se ordena', 'se cede', 'se autoriza la cesion', 'se requiere', 'se impone',
    'se formulan cargos', 'se inicia', 'se corrige', 'se aclara', 'se reconoce',
    'se da por terminado', 'se define la responsabilidad', 'se mantiene vigente',
    'se modifica un sistema', 'se modifica una licencia', 'se modifica un dictamen',
    'se modifica un plan', 'se establece un plan de manejo', 'se actualiza un plan',
    'se revoca la resolucion', 'se exceptua', 'se sanciona', 'se concede una prorroga',
    'se decreta', 'desistimiento', 'se resuelven los recursos', 'se ajusta via seguimiento',
    'inicia tramite', 'se inicia tramite', 'se avoca', 'se admite',
    'se define competencia', 'se niegan', 'se otorgan', 'se autorizan', 'se deniega',
)

# Fija una regla nueva: obliga a todo el que esté en el supuesto.
_NORMA_GENERAL = (
    'se establece', 'se establecen', 'se adopta', 'se adoptan', 'se reglamenta',
    'se reglamentan', 'se fija', 'se fijan', 'se dictan disposiciones', 'se actualiza',
    'se actualizan', 'se senalan', 'se determinan los', 'se sustituye', 'se deroga',
    'terminos de referencia', 'metodologia', 'manual', 'precios de referencia',
    'gravamenes', 'derechos correctivos', 'circular reglamentaria', 'circular externa',
    'carta circular', 'valores de la', 'precios del gramo', 'se expide el reglamento',
    'se modifica el decreto', 'se modifica la circular', 'se modifica el reglamento',
)

# Administración interna de la entidad. No regula a nadie de afuera, así que no
# es señal para ningún cliente por más que la fuente sea un regulador.
_ACTO_INTERNO = (
    'trabajo en casa', 'jornada laboral', 'horario de atencion', 'horario de trabajo',
    'horario excepcional', 'se habilita la jornada', 'se habilita temporalmente',
    'planta de personal', 'comision de servicios', 'se nombra', 'se encarga a',
    'vacaciones', 'situacion administrativa', 'se conforma el comite', 'se designa',
)

# Desempatan los verbos ambiguos ("se modifica la…") por el objeto del acto.
_OBJETO_PARTICULAR = (
    'licencia', 'dictamen', 'permiso', 'plan de manejo', 'concesion', 'expediente',
    'autorizacion', 'certificado', 'salvoconducto', 'zoocriadero', 'aprovechamiento forestal',
)
_OBJETO_GENERAL = (
    'circular', 'reglamento', 'manual', 'metodologia', 'tarifa',
    'resolucion externa', 'formulario', 'procedimiento general',
)


def alcance_acto(texto):
    """'general' | 'particular' | 'interno' | 'indeterminado'.

    Mira solo la CABEZA del texto (el verbo del acto). El resto es el expediente
    y contamina: una licencia nombrada al final no vuelve particular a una norma.
    Ante la duda devuelve 'indeterminado' — que río arriba pesa como medio, nunca
    como alto: en un sistema de alertas, la duda no puede ser urgencia.
    """
    t = _COLETILLA.sub('', _ENCABEZADO.sub('', norm(texto)).strip()).strip()
    cabeza = ' '.join(t.split()[:9])
    if not cabeza:
        return 'indeterminado'
    if any(k in cabeza for k in _ACTO_INTERNO):
        return 'interno'
    part = next((k for k in _ACTO_PARTICULAR if k in cabeza), None)
    gen = next((k for k in _NORMA_GENERAL if k in cabeza), None)
    if part and not gen:
        return 'particular'
    if gen and not part:
        return 'general'
    if part and gen:                       # ambos verbos → manda el más específico
        return 'particular' if len(part) >= len(gen) else 'general'
    if any(o in cabeza for o in _OBJETO_PARTICULAR):
        return 'particular'
    if any(o in cabeza for o in _OBJETO_GENERAL):
        return 'general'
    return 'indeterminado'


def nivel_acto_regulatorio(row):
    """Nivel de un acto de un regulador.

    Un acto pesa por lo que OBLIGA, no por cómo se llama:
      · fija una regla nueva            → alto  (obliga a todo el sector)
      · sanción grande                  → alto  (marca el criterio del regulador)
      · abre investigación              → medio
      · resuelve un expediente ajeno    → bajo  (le pasó a un tercero)
      · administración interna          → bajo

    Ojo: que un acto particular caiga en BAJO no es que se pierda. Si recae sobre
    una empresa que el perfil vigila, `motor.clasificar` lo sube a alto por
    IDENTIDAD — que es la señal que de verdad justifica el producto: no llega
    porque el texto mencione su sector, llega porque lo nombra a él.
    """
    tipo = (row.get('tipo_acto') or 'sancion').lower()
    monto = row.get('monto')
    try:
        monto = float(monto) if monto not in (None, '') else None
    except (TypeError, ValueError):
        monto = None

    if monto and monto >= UMBRAL_MULTA:
        return 'alto', f'sanción de {_pesos(monto)}'
    if tipo in ('archivo', 'contribucion_especial'):
        return 'bajo', 'acto procesal o de recaudo, sin efecto regulatorio nuevo'
    if tipo == 'apertura_investigacion':
        return 'medio', 'apertura de investigación'
    # La doctrina (conceptos de la DIAN) no crea una obligación nueva: fija la
    # interpretación oficial de una que ya existe. Importa —y mucho, a un gremio
    # tributario— pero no es lo mismo que una norma nueva, y decir que lo es
    # devuelve el producto al problema que este arreglo vino a resolver.
    if (row.get('fuente') or '') == 'dian-doctrina':
        return 'medio', 'doctrina oficial: fija interpretación, no crea obligación nueva'
    if tipo == 'sancion':
        # 'sancion' es también el valor por defecto de las fuentes que no tipan
        # sus actos (INVIMA, multas de SECOP, SFC), y en todas ellas es correcto.
        if monto:
            return 'medio', f'sanción de {_pesos(monto)}'
        return 'medio', 'sanción en el sector'

    # Resoluciones, circulares y AUTOS. Los autos llegan tipados 'otro' y antes
    # se escurrían hasta el final, saliendo rotulados "sanción en el sector" —
    # un desistimiento tácito no sanciona a nadie. Es la misma afirmación falsa
    # que el defecto grande, en pequeño: lo que no es una sanción se clasifica
    # por lo que obliga, nunca por el cajón donde cayó.
    alcance = alcance_acto(row.get('motivo') or row.get('descripcion') or '')
    if alcance == 'general':
        return 'alto', 'norma nueva: fija una regla para todo el sector'
    if alcance == 'particular':
        return 'bajo', 'resuelve un expediente puntual: no cambia la regla del sector'
    if alcance == 'interno':
        return 'bajo', 'administración interna de la entidad, sin efecto sobre vigilados'
    return 'medio', 'acto del regulador, de alcance no declarado en el texto'


def nivel_normativa(row):
    """Nivel de una norma del Ejecutivo (decretos, resoluciones, circulares)."""
    tipo = norm(row.get('tipo') or '')
    if 'decreto' in tipo:
        return 'alto', 'decreto nuevo: obliga desde su publicación'
    if 'ley' in tipo:
        return 'alto', 'ley sancionada'
    if 'resolucion' in tipo or 'circular' in tipo or 'directiva' in tipo:
        return 'medio', 'acto administrativo del Ejecutivo'
    return 'bajo', 'normativa general'


def nivel_contrato(row, historico_entidad=None, empresas=None, propias=False):
    """Nivel de un contrato: por QUIÉN y por NOVEDAD, nunca por monto.

    El monto no discrimina: la Lambda ya devuelve el top del sector ordenado por
    valor, así que "contrato grande" describe al 100% de lo que llega y un
    umbral solo repartiría la etiqueta «alto» a todos por igual.

    Lo que sí distingue:
      · QUIÉN — el proveedor es una empresa del diccionario (un cliente, un
        competidor suyo, o alguien de su cadena).
      · NOVEDAD — una entidad que aparece comprando en una categoría en la que
        no la habíamos visto. Es la señal de que se abrió un frente nuevo.

    `historico_entidad` = categorías ya vistas de esa entidad, o None si no
    tenemos historia. Sin historia NO se afirma novedad: "nunca lo había visto"
    y "nunca había mirado" no son lo mismo, y confundirlos genera una alerta
    falsa por cada entidad nueva del universo.
    """
    proveedor = row.get('proveedor') or ''
    entidad = row.get('entidad') or ''
    cat = categoria_contrato(row.get('objeto') or row.get('_objeto') or '')

    # `propias` cambia solo la REDACCIÓN, no el criterio: con perfil de cliente
    # la frase tiene que decirle que es SU empresa, no «una empresa conocida».
    de_quien = 'que este perfil vigila' if propias else 'del registro de empresas vigiladas'

    emp = proveedor_vigilado(proveedor, empresas)
    if emp:
        return ('alto', f'el proveedor es {emp["nombre"]}, {de_quien}', cat)

    emp_ent = entidad_vigilada(entidad, empresas)
    if emp_ent:
        return ('medio', f'contrata {emp_ent["nombre"]}, {de_quien}', cat)

    if historico_entidad:
        if cat not in historico_entidad:
            vistas = ', '.join(sorted(historico_entidad)[:3])
            return ('alto',
                    f'categoría nueva para esta entidad: «{cat}» '
                    f'(hasta hoy solo la habíamos visto en {vistas})',
                    cat)
        return 'medio', f'contratación en «{cat}», categoría habitual de esta entidad', cat

    return ('medio',
            'contratación del sector · sin histórico previo de esta entidad, '
            'todavía no se puede afirmar que sea un frente nuevo', cat)


# Verbos y sustantivos de un hecho que TIENDE a terminar en acto del Estado.
# Sin esto la excepción se convierte en la manguera que se acaba de cerrar por
# la otra puerta: medido, «prensa que nombra una empresa vigilada» daba 26
# alertas altas en un solo día del sector financiero, casi todas noticia
# comercial rutinaria (resultados, lanzamientos, nombramientos).
_PRENSA_ACCIONABLE = re.compile(
    r'sancion|multa|investiga|superintendenc|supersalud|superfinanc|supertransp|'
    r'\bsic\b|invima|contralor|procuradur|fiscal|demanda|tutela|condena|'
    r'incumpl|irregular|fraude|corrupc|interven|liquidac|vigilanc|inspecc|'
    r'ordena|requiere|suspende|revoca|cierre|clausura|denuncia|quiebra|'
    r'crisis|falla|riesgo|alerta|querella|pleito|litigio|apela')


def prensa_accionable(titulo):
    """¿El titular describe algo que puede terminar en acto del Estado?"""
    return bool(_PRENSA_ACCIONABLE.search(norm(titulo)))


def nivel_titular_empresa(titulo, emp, propias=False):
    """Prensa que dispara SOLA: nombra una empresa vigilada, describe un hecho
    accionable, y no hay acto del Estado que le corresponda.

    Es la única cobertura que es información y no eco. Si el Estado ya actuó,
    la alerta es el acto y la prensa es su corroboración; si el Estado no ha
    actuado pero la prensa ya reporta una investigación o una orden, esperar al
    registro es llegar tarde.
    """
    quien = f'{emp["nombre"]}, que este perfil vigila' if propias else emp['nombre']
    return ('alto',
            f'la prensa reporta un hecho sobre {quien} que todavía no '
            f'tiene acto del Estado en el registro — puede ir por delante')


# --- la otra puerta: prensa que dispara por TEMA ----------------------------
#
# La identidad no le sirve a todo el mundo. Un cliente cuyo negocio no tiene
# razón social colombiana en el diccionario (Binance) se queda con `empresas_de`
# = [] y entonces NINGÚN titular puede dispararle: medido el 7-ago-2026, su
# corrida revisó 51 titulares y descartó los 51, y entre los descartados iba la
# Resolución 000240 de la DIAN aterrizando en prensa — justo la norma que ese
# cliente tiene clasificada como adversaria. El pilar entero estaba apagado para
# quien solo tiene temas.
#
# Abrirlo por tema NO puede ser bajar la barra: la barra existe porque «prensa
# que nombra una empresa vigilada» ya daba 26 altas en un día en financiero, y
# el corpus temático es peor todavía. Medido sobre los 51 de ese perfil: 40 son
# de «lavado de activos» y hablan de Milei, del caso Lili Pink, de extradiciones
# y de la posesión presidencial — el término del cliente aparece en la consulta,
# no en el hecho.
#
# El discriminador que sí separa es cuál es la NATURALEZA del hecho:
#
#   · una norma o una decisión de una autoridad reguladora, que aplica a una
#     clase entera de actores  → eso ES la frontera regulatoria del cliente;
#   · un caso penal contra un tercero con nombre propio (captura, extradición,
#     imputación) → eso NO es su frontera. Si el tercero fuera su empresa, la
#     puerta de la IDENTIDAD ya lo alerta, y esa puerta sí acepta lo penal.
#
# De ahí las cinco piezas de abajo. Medidas sobre los 1.161 titulares reales de
# los 12 destinos del 8-ago-2026: pasan 23 (2,0%), y las 40 notas de crónica
# roja del perfil de Binance mueren en la primera.

# 1) La autoridad. Dos listas, y la división NO es cosmética: el corpus trae
#    prensa de media región (el 7-ago entraron notas de Argentina, Uruguay,
#    Panamá, Honduras, México e Indonesia). «Corte Suprema» o «Ministerio» sin
#    más disparaban con una nota argentina sobre pensiones; «DIAN» o «Minsalud»
#    no existen fuera de Colombia y se bastan solas.
_AUTORIDAD_CO = re.compile(
    r'\bdian\b|supersalud|superfinanc|supertransp|superservicios|supersociedades|'
    r'superindustria|superintendencia de (industria|salud|servicios|sociedades|transporte|puertos)|'
    r'superintendencia (nacional de salud|financiera)|'
    r'\bsic\b|invima|\banla\b|\bcreg\b|\bupme\b|\bani\b|\bica\b|\badres\b|\buiaf\b|'
    r'\bdnp\b|\bcnsc\b|\bsena\b|\bicbf\b|\bdane\b|aerocivil|aeronautica civil|'
    r'minsalud|minhacienda|mintrabajo|mintic|minenergia|minambiente|minagricultura|'
    r'mineducacion|minjusticia|mincomercio|mintransporte|minminas|mindefensa|'
    r'ministerio de (salud|hacienda|trabajo|minas|ambiente|agricultura|educacion|'
    r'justicia|comercio|transporte|vivienda|igualdad|tecnologias|las tic)|'
    r'ministerio tic|banco de la republica|procuradur|contralor|'
    r'corte constitucional|consejo de estado|comision de regulacion')

# Existen en toda la región: solo cuentan si el titular ancla el país.
_AUTORIDAD_GENERICA = re.compile(
    r'superintendenc|ministerio|corte suprema|agencia nacional|instituto nacional|'
    r'gobierno nacional')

_ANCLA_COLOMBIA = re.compile(
    r'\bcolombia|colombian|\bbogota\b|\bmedellin\b|\bcali\b|\bbarranquilla\b|'
    r'\bcartagena\b|\bpetro\b|espriella')

# 2) Qué HIZO la autoridad. Sin esto entra el ruido de nombramientos, que en el
#    corpus es enorme: «Fabio Arjona Hincapié — Ministerio de Ambiente», «sería
#    designado como el nuevo presidente de la ANLA», «completa la cúpula del
#    Ministerio de Minas». Nombrar a alguien no cambia ninguna obligación.
#    Ojo: esta lista es generosa a propósito y el corte fino lo hace la pieza
#    2.b — hay verbos ('tarifa', 'ordena') que aparecen igual en una decisión y
#    en un informe sobre el sector.
_ACTO_REGULATORIO = re.compile(
    r'resolucion|decreto|circular|reglamenta|normativ|expide|expidio|emitio|'
    r'entra en vigencia|rige a partir|nueva[s]? regla|cambi[ao] las reglas|'
    r'cambian las reglas|sancion|multa|obliga|obligator|exige|prohibe|prohibicion|'
    r'autoriza|luz verde|deja en firme|otorga|adjudica|declara desierta|'
    r'niega (la |el )?(licencia|permiso|registro|solicitud)|'
    r'formula cargos|imputa cargos|abre investigacion|investiga a|'
    r'requisito|licencia|permiso|habilitacion|tarifa|topes? |plazo|'
    r'suspende|revoca|deroga|modifica|aprueba|adopta|ordena|\bfallo\b|sentencia|'
    r'actualiza|incorpora|establece|fija ')

# 2.b) …y lo que solo PARECE un acto. Un diagnóstico del regulador no cambia
#    ninguna obligación: es información sobre el sector, no una decisión sobre
#    él. Sin este corte se colaba «Estudio de la Superservicios revela que la
#    integración vertical no reduce las tarifas» —entró por la palabra 'tarifa'—
#    y en el corpus ese mismo informe venía replicado por 4 medios, o sea que la
#    corroboración lo habría subido a alto por ser eco, que es exactamente lo que
#    este pilar existe para no hacer.
_DIAGNOSTICO = re.compile(
    r'\bestudio\b|\binforme\b|\bbalance\b|revela|estima que|\bencuesta\b|'
    r'segun (el|la) (estudio|informe|reporte)')

# 3) Crónica roja. Es el grueso del ruido temático y NO se pierde nada al
#    sacarlo: si el capturado fuera una vigilada del cliente, la puerta de la
#    identidad lo alerta igual (`_PRENSA_ACCIONABLE` sí acepta lo penal).
_CASO_PENAL = re.compile(
    r'captur|extradit|judicializ|arrest|detenid|detien|allanamiento|incaut|'
    # 'banda' va calificada a propósito: 'banda ancha' es vocabulario de TIC, y
    # a secas mataba las resoluciones del MinTIC sobre conectividad.
    r'\balias\b|bandas? (criminal|delincuencial|narco)|'
    r'narcotrafic|homicid|masacre|secuestr|sicari|atentado|'
    r'declara culpable|condena a \d+|\bcarcel\b|prision|red(es)? de trata|contraband')

# 4) Política, agenda y servicio al lector. No son hechos de Estado: son quién
#    llegó al cargo, quién se reunió con quién, y el «paso a paso» de siempre.
_RUIDO_POLITICO = re.compile(
    r'gabinete|posesion|se posesiona|nombramiento|nombra a|designa|designacion|'
    r'sera el nuevo|asumira|viceminist|cupula|renuncia|escandalo|encuesta|'
    r'entrevista|columna de opinion|\btop \d|paso a paso|conozca |asi funciona|'
    r'asi va |esto es lo que|\bvideo\b|en vivo|se reunio|se encontro|gira |'
    r'ganan influencia|altos cargos|— ministerio|- ministerio')


# Cómo se escribe cada autoridad en el correo. `norm` ya bajó todo a minúscula
# y sin tildes, así que la forma original del titular no se puede recuperar por
# posición (al normalizar se caen las comillas tipográficas y las rayas, y los
# índices dejan de cuadrar). Una tabla corta es más barata y no se equivoca.
_AUTORIDAD_NOMBRE = {
    'dian': 'la DIAN', 'sic': 'la SIC', 'anla': 'la ANLA', 'creg': 'la CREG',
    'upme': 'la UPME', 'ani': 'la ANI', 'ica': 'el ICA', 'adres': 'la ADRES',
    'uiaf': 'la UIAF', 'dnp': 'el DNP', 'cnsc': 'la CNSC', 'sena': 'el SENA',
    'icbf': 'el ICBF', 'dane': 'el DANE', 'aerocivil': 'la Aerocivil',
    'aeronautica civil': 'la Aeronáutica Civil',
    # Ojo: la llave es lo que devuelve `group(0)`, o sea el TROZO que casó. Varias
    # alternativas del patrón son raíces cortadas ('superfinanc', 'supertransp')
    # justamente para tolerar «Superfinanciera»/«Superintendencia Financiera», así
    # que la raíz también tiene que estar acá o el correo diría «la Superfinanc».
    'supersalud': 'la Supersalud', 'superfinanc': 'la Superfinanciera',
    'superfinanciera': 'la Superfinanciera', 'supertransp': 'la Supertransporte',
    'supertransporte': 'la Supertransporte', 'superservicios': 'la Superservicios',
    'comision de regulacion': 'la Comisión de Regulación',
    'supersociedades': 'la Supersociedades', 'superindustria': 'la Superindustria',
    'invima': 'el Invima', 'minsalud': 'Minsalud', 'minhacienda': 'Minhacienda',
    'mintrabajo': 'MinTrabajo', 'mintic': 'MinTIC', 'minenergia': 'MinEnergía',
    'minambiente': 'Minambiente', 'minagricultura': 'Minagricultura',
    'mineducacion': 'Mineducación', 'minjusticia': 'Minjusticia',
    'mincomercio': 'Mincomercio', 'mintransporte': 'MinTransporte',
    'minminas': 'MinMinas', 'mindefensa': 'MinDefensa',
    'ministerio tic': 'el Ministerio TIC',
    'banco de la republica': 'el Banco de la República',
    'corte constitucional': 'la Corte Constitucional',
    'corte suprema': 'la Corte Suprema', 'consejo de estado': 'el Consejo de Estado',
    'gobierno nacional': 'el Gobierno Nacional',
}


def _nombre_autoridad(bruto):
    """Texto crudo del match → cómo se nombra en el correo."""
    b = (bruto or '').strip()
    if b in _AUTORIDAD_NOMBRE:
        return _AUTORIDAD_NOMBRE[b]
    if b.startswith('procuradur'):
        return 'la Procuraduría'
    if b.startswith('contralor'):
        return 'la Contraloría'
    if b.startswith('superintendencia'):
        return 'la ' + b.capitalize()
    if b.startswith('ministerio'):
        return 'el ' + b.capitalize()
    return 'una autoridad' if not b else 'la ' + b.capitalize()


def prensa_normativa(titulo):
    """¿El titular reporta una NORMA o una decisión regulatoria?

    → (bool, motivo, autoridad). `motivo` dice por qué NO pasó cuando no pasa,
    para poder contar el descarte por causa en vez de dejarlo opaco:
    'sin-autoridad' · 'sin-acto' · 'diagnostico' · 'penal' · 'politica'. Cuando
    pasa, `motivo` es 'ok' y `autoridad` es cómo se nombra a quien actuó.
    """
    tn = norm(titulo)
    if not tn:
        return False, 'sin-autoridad', ''
    m = _AUTORIDAD_CO.search(tn)
    if not m:
        # Autoridad genérica: solo si el titular dice de qué país habla.
        m = _AUTORIDAD_GENERICA.search(tn)
        if not (m and _ANCLA_COLOMBIA.search(tn)):
            return False, 'sin-autoridad', ''
    if not _ACTO_REGULATORIO.search(tn):
        return False, 'sin-acto', ''
    if _DIAGNOSTICO.search(tn):
        return False, 'diagnostico', ''
    if _CASO_PENAL.search(tn):
        return False, 'penal', ''
    if _RUIDO_POLITICO.search(tn):
        return False, 'politica', ''
    return True, 'ok', _nombre_autoridad(m.group(0))


def nivel_titular_tema(autoridad, tema, n_medios=1, propias=False):
    """Prensa que dispara por TEMA: una autoridad movió algo en el terreno que
    este destino vigila, y no hay acto en el registro que le corresponda.

    Arranca en `medio`, no en `alto`, y la diferencia es honesta: en la puerta
    de la identidad la nota habla de TU empresa; acá habla de tu terreno. Sube a
    `alto` cuando varios medios reportan el mismo acto, que es el mismo criterio
    de corroboración que ya usa el resto del motor: un acto que la prensa del
    sector persigue en bloque pesa distinto que una nota suelta.

    Se nombra a la autoridad y el término vigilado que trajo la nota. Lo primero
    porque «Minsalud movió algo» es la noticia y «una autoridad movió algo» no
    es nada; lo segundo porque la consulta de prensa es por término y a veces
    devuelve algo de un sector vecino — verlo escrito deja que el lector lo
    descarte de una ojeada en vez de preguntarse por qué le llegó.
    """
    de_quien = 'que este perfil vigila' if propias else 'de este sector'
    base = (f'{autoridad or "una autoridad"} movió algo en «{tema}», {de_quien}, '
            f'y todavía no tiene acto del Estado en el registro')
    if n_medios >= 2:
        return 'alto', f'{base} — y lo reportaron {n_medios} medios'
    return 'medio', base


def _pesos(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if v >= 1_000_000_000_000:
        return f'${v/1_000_000_000_000:.1f} billones'.replace('.', ',')
    if v >= 1_000_000_000:
        return f'${v/1_000_000_000:.1f} mil millones'.replace('.', ',')
    if v >= 1_000_000:
        return f'${v/1_000_000:.0f} millones'
    return f'${v:,.0f}'.replace(',', '.')


pesos = _pesos


# ---------------------------------------------------------------------------
# 5) CORROBORACIÓN CRUZADA
# ---------------------------------------------------------------------------
# Palabras que no distinguen nada entre dos textos del mismo sector.
#
# Las 20 primeras son obvias; el resto es PLANTILLA LEGAL, y son las que de
# verdad hacían daño. Medido contra prensa real: sin ellas, un proyecto sobre
# autismo "corroboraba" una nota sobre aborto porque ambos textos decían
# «garantizar» y «constitucional», y un proyecto de telemedicina casaba con
# cualquier nota que dijera «acceso a servicios». Dos palabras en común solo
# significan algo si ninguna de las dos aparece en el 80% de los títulos del
# Congreso.
_GENERICAS = set("""
proyecto ley leyes articulo articulos nacional nacionales colombia colombiano
gobierno estado congreso senado camara republica sistema general disposiciones
medio cual dictan otras nueva nuevo nuevos nuevas sobre entre para segun anos
ministerio ministro presidente decreto resolucion norma reforma
garantizar garantiza garantia garantias constitucional constitucionales
acceso acceder accesibilidad servicio servicios prestacion prestaciones
atencion integral integrales especial especiales publico publica publicos
publicas medidas mecanismo mecanismos procedimiento procedimientos
fortalecer fortalece fortalecimiento promover promueve promocion
establecer establece establecen implementar implementacion
modifica modifican adiciona adicionan crease creacion
territorial territoriales departamento municipio municipal municipios
personas ciudadanos ciudadania poblacion beneficiarios usuarios
derecho derechos deberes obligaciones condiciones requisitos
""".split())

# Las mismas, ya reducidas a raíz: `tokens_distintivos` compara raíces, así que
# 'servicios'→'servic' tiene que quedar fuera aunque la palabra original no esté
# escrita igual en los dos textos.
_GENERICAS_RAIZ = {_raiz(w) for w in _GENERICAS}


def tokens_distintivos(texto, minimo=6):
    """Palabras largas y no genéricas de un texto — para cruzar dos fuentes."""
    out = set()
    for w in _TOKEN.findall(norm(texto)):
        if len(w) < minimo or w in _GENERICAS:
            continue
        r = _raiz(w)
        if r in _GENERICAS_RAIZ or len(r) < 5:
            continue
        out.add(r)
    return out


def corrobora(titular, eventos_ancla, minimo_comun=2):
    """¿El titular habla de algo que se movió hoy en otra fuente?

    Exige ≥2 palabras distintivas en común. Con una sola, cualquier nota de
    salud "corrobora" cualquier proyecto de salud y el bump pierde sentido.
    Devuelve (bool, evento_ancla, [palabras comunes]).
    """
    tt = tokens_distintivos(titular)
    if len(tt) < minimo_comun:
        return False, None, []
    for ev in eventos_ancla:
        comunes = tt & tokens_distintivos(ev.get('titulo', ''))
        if len(comunes) >= minimo_comun:
            return True, ev, sorted(comunes)
    return False, None, []


# ---------------------------------------------------------------------------
# 6) SALUD OPERATIVA  (Bases de datos/leyes-senado/diario/estado.json)
# ---------------------------------------------------------------------------
# Esto NO va al digest de un cliente: es el canal interno. Si el rastreo se cae,
# los digests sectoriales salen vacíos y "sin novedades" pasa a significar "no
# sé", que es lo peor que puede decir un sistema de alertas sin saber que lo
# está diciendo.
#
# Las tres reglas vienen del handoff de la conversación que escribió estado.json
# (.claude/notas/caudal-salud.md) y están puestas para NO despertar a nadie en
# falso:
#   1. `corrida` puede estar AUSENTE — nunca se lee como "el cron falló".
#   2. `corrida.arrastrada` = el bloque es de una corrida vieja que se conservó
#      para no borrar historia; se juzga por `corrida.fin`, no por su presencia.
#   3. Un ping con `externa: true` (SECOP/Socrata, Google News) que degrada a
#      warn es un tercero caído, no nosotros: se registra, no se alerta.
#   4. Un archivo `clase: "estatico"` (los 14 del histórico 1990-2026) no
#      envejece: de él solo importa que exista y que no se haya truncado.

HORAS_CORRIDA_VIEJA = 30

# Andamiaje de traceback: ubica el error en el código, no lo explica. En un
# correo de operación ocupa el espacio de lo único que importa —la excepción—,
# que además queda cortada por el tope de caracteres.
_RUIDO_TRACEBACK = re.compile(
    r'^\s*(Traceback \(most recent call last\)|File ".*", line \d+|raise |'
    r'\.\.\.|\^+\s*$)')
# La línea de excepción de Python: `modulo.NombreError: mensaje`. Cuando
# aparece, es LA explicación y todo lo anterior es andamiaje.
_LINEA_EXCEPCION = re.compile(
    r'^[A-Za-z_][\w.]*(Error|Exception|Interrupt|Exit|Timeout)\b.*?:')


def cola_legible(lineas, n=2):
    """Últimas líneas de una etapa caída, en forma de frase.

    `salida_cola` trae el final del stderr crudo: sangría de traceback, la línea
    de código que lanzó, y solo al final la excepción. Pegarlo tal cual daba
    «— <30 espacios> output=stdout, stderr=stderr) · subprocess.CalledProcess…»,
    donde lo legible es el andamiaje y lo cortado es el error.

    Dos pasadas: se tira el andamiaje evidente y se colapsa el blanco; y si
    queda una línea de excepción, se devuelve SOLO ella — el fragmento de
    código que la lanzó no le dice nada a quien lee el correo, y quitarlo es lo
    que hace que el mensaje del error entre completo en el tope de caracteres.
    """
    utiles = []
    for ln in (lineas or []):
        ln = ' '.join(str(ln).split())          # colapsa sangría y tabs
        if not ln or _RUIDO_TRACEBACK.match(ln):
            continue
        utiles.append(ln)
    for ln in reversed(utiles):
        if _LINEA_EXCEPCION.match(ln):
            return ln
    return ' · '.join(utiles[-n:])


def problemas_operacion(estado, ahora=None):
    """estado.json → (problemas accionables, contexto no accionable).

    Un problema tiene {nivel, titulo, detalle, porque, origen}. El contexto es
    lo que se vio pero se decidió NO alertar, con el motivo: se muestra al pie
    para que quede claro que se miró y se descartó, no que no se miró.
    """
    import datetime as _dt
    ahora = ahora or _dt.datetime.now()
    problemas, contexto = [], []
    if not estado:
        return problemas, contexto

    # --- corrida ---
    corrida = estado.get('corrida')
    if not corrida:
        contexto.append('El estado no trae bloque `corrida`: el chequeo corrió '
                        'suelto o el cron todavía no ha corrido con el script '
                        'nuevo. No se interpreta como falla.')
    else:
        fin = corrida.get('fin') or ''
        vieja = False
        try:
            d = _dt.datetime.fromisoformat(fin)
            if d.tzinfo is not None:
                d = d.replace(tzinfo=None)
            vieja = (ahora - d).total_seconds() / 3600.0 > HORAS_CORRIDA_VIEJA
        except (ValueError, TypeError):
            vieja = bool(corrida.get('arrastrada'))
        if corrida.get('arrastrada') and vieja:
            contexto.append(f'La última corrida registrada es de {fin or "fecha desconocida"} '
                            f'y viene marcada como arrastrada: no es de hoy, así que '
                            f'sus fallas ya se reportaron en su momento.')
        else:
            for et in corrida.get('etapas', []):
                if et.get('estado') == 'error':
                    cola = cola_legible(et.get('salida_cola'))
                    problemas.append({
                        'nivel': 'alto', 'origen': 'corrida',
                        'titulo': f'Etapa «{et.get("nombre")}» falló (rc={et.get("rc")})',
                        'detalle': (et.get('desc') or '') + (f' — {cola}' if cola else ''),
                        'porque': 'una etapa crítica del rastreo terminó en error: '
                                  'lo que produce esa etapa no se actualizó hoy'
                                  if et.get('critica') else
                                  'una etapa del rastreo terminó en error'})
                elif et.get('estado') == 'omitida':
                    problemas.append({
                        'nivel': 'medio', 'origen': 'corrida',
                        'titulo': f'Etapa «{et.get("nombre")}» omitida',
                        'detalle': et.get('motivo') or '',
                        'porque': 'se saltó por una dependencia que falló antes'})

    # --- frescura ---
    fr = estado.get('frescura') or {}
    for a in fr.get('archivos', []):
        clase = a.get('clase')
        roto = (not a.get('existe')) or (
            a.get('min_bytes') and (a.get('bytes') or 0) < a['min_bytes'])
        if clase == 'estatico':
            if roto:
                problemas.append({
                    'nivel': 'alto', 'origen': 'frescura',
                    'titulo': f'{a.get("key")} falta o está truncado',
                    'detalle': f'{a.get("bytes")} bytes (mínimo {a.get("min_bytes")})',
                    'porque': 'es un archivo del histórico: no envejece, pero si se '
                              'trunca el pilar deja de responder'})
            continue                          # un estático viejo NO es noticia
        if a.get('estado') == 'error' or roto:
            problemas.append({
                'nivel': 'alto', 'origen': 'frescura',
                'titulo': f'{a.get("key")} sin actualizar',
                'detalle': (a.get('motivo') or
                            f'{a.get("edad_horas")} h de antigüedad'),
                'porque': f'lo produce {a.get("productor") or "el rastreo"} y lo consume '
                          f'{a.get("consumidor") or "Caudal"}'})
        elif a.get('estado') in ('warn', 'aviso'):
            problemas.append({
                'nivel': 'medio', 'origen': 'frescura',
                'titulo': f'{a.get("key")} se está enfriando',
                'detalle': a.get('motivo') or '',
                'porque': 'todavía sirve, pero pasó el umbral de aviso'})

    # --- lambda ---
    lam = estado.get('lambda') or {}
    for p in lam.get('pings', []):
        if p.get('estado') == 'error':
            if p.get('externa'):
                contexto.append(f'Ping `{p.get("accion")}` en error, pero depende de un '
                                f'tercero ({p.get("motivo") or "sin detalle"}): no se alerta.')
                continue
            problemas.append({
                'nivel': 'alto', 'origen': 'lambda',
                'titulo': f'La acción `{p.get("accion")}` de la Lambda falla',
                'detalle': p.get('motivo') or f'HTTP {p.get("http")}',
                'porque': 'es una acción propia: si falla, el pilar que la usa está caído'})
        elif p.get('estado') in ('warn', 'aviso'):
            if p.get('externa'):
                contexto.append(f'Ping `{p.get("accion")}` degradado por un tercero '
                                f'({p.get("motivo") or "sin detalle"}): no se alerta.')
            else:
                problemas.append({
                    'nivel': 'medio', 'origen': 'lambda',
                    'titulo': f'La acción `{p.get("accion")}` responde degradada',
                    'detalle': p.get('motivo') or '',
                    'porque': 'responde, pero fuera de lo esperado'})
    return problemas, contexto


if __name__ == '__main__':
    print(f'caudal_core importado: {_CC_OK} · empresas importado: {_EMP_OK}')
    for s in sectores():
        v = vocabulario(s['k'])
        print(f"\n{s['k']:<14} {len(v):>3} términos · comisión {s['comision']}")
        print('   ' + ' · '.join(v[:10]) + (' …' if len(v) > 10 else ''))
