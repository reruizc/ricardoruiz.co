#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — el titular de un acto regulatorio dice el HECHO.

El registro nombra cada acto por su encabezado burocrático: «Por la cual se
declara la pérdida de ejecutoriedad de la Resolución 1029 del 8 de octubre de
2013». Eso no dice a quién le pasó ni qué cambia, y un gremio no lo puede llevar
a una reunión. Acá se arma, desde el propio texto del acto, un renglón con la
forma «{A QUIÉN / SOBRE QUÉ} — {qué pasó}».

Dos reglas, las dos por lo que ya mordió a este proyecto:

1. NO SE INVENTA EL SUJETO. Solo entra (a) la razón social que el build del
   pilar ya extrajo, (b) el producto/proyecto que la fuente escribe textual, o
   (c) el solicitante que la fuente escribe textual después de un guion. Lo que
   no se pueda tomar literal de la fuente no entra: el titular se queda solo
   con el hecho, que sigue siendo mejor que el encabezado. Un nombre de empresa
   equivocado en una alerta regulatoria es lo que hace que el cliente deje de
   confiar.
2. EL HECHO SE DERIVA DEL VERBO DEL ACTO, no se resume. Son ~15 formas
   («se niega», «se otorga», «se autoriza la cesión», «se declara la pérdida
   de ejecutoriedad»…) y cubren casi todo; lo que no casa con ninguna se deja
   con el mismo complemento del original, solo sin el «Por la cual se».

Medido en ANLA (ago-2026): la empresa está en el texto del acto en el 4% de los
casos (2.209 de 57.949) y en esos ya viene en `sancionado`. Lo que sí trae el
registro, en `descripcion`, es el PROYECTO o el PRODUCTO («Aeropuerto
Internacional Palonegro», «producto BULLET», «Campo Desarrollo Puli C»), y eso
es lo que el cliente reconoce.
"""

import re
import unicodedata

# --------------------------------------------------------------------- texto

# Siglas que deben seguir en mayúscula cuando se baja un texto GRITADO.
SIGLAS = {'pma', 'cepd', 'dta', 'fncer', 'anla', 'psma', 'upme', 'anh', 'ani',
          'ungrd', 'ideam', 'minambiente', 'car', 'cdmb', 'corpoboyaca', 'esp',
          'e.s.p.', 's.a.', 's.a.s.', 'sas', 'ltda', 'eds', 'pgirs', 'raee',
          'ii', 'iii', 'iv', 'pr', 'kv', 'mw', 'ha', 'lla', 'cso', 'pda',
          'pmrra', 'ica', 'invima', 'eia', 'dapre', 'ppii', 'cvc', 'sig'}
_RX_SIGLA = re.compile(r'\b(' + '|'.join(re.escape(s) for s in sorted(SIGLAS, key=len, reverse=True)) + r')\b')


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn').lower()


def _gritado(t):
    letras = [c for c in t if c.isalpha()]
    return bool(letras) and sum(1 for c in letras if c.isupper()) / len(letras) >= 0.6


def frase(t):
    """MAYÚSCULA SOSTENIDA → frase con siglas; lo ya escrito en frase no se toca."""
    t = (t or '').strip()
    if not _gritado(t):
        return t
    s = t.lower()
    s = _RX_SIGLA.sub(lambda m: m.group(1).upper(), s)
    # Códigos tipo "PULI C" o "LLA-71" vuelven a mayúscula: una letra suelta.
    s = re.sub(r'\b([b-df-hj-np-tv-xz])\b', lambda m: m.group(1).upper(), s)
    # Lo entrecomillado es un nombre propio («PUERTO NUEVO», «EL QUIMBO»).
    s = re.sub(r'([“"])([^”"]{2,60})([”"])',
               lambda m: m.group(1) + nombre(m.group(2).upper()) + m.group(3), s)
    return s[:1].upper() + s[1:]


_CONECTORES = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'o', 'u', 'a',
               'en', 'por', 'para', 'con', 'sin', 'al', 'sus', 'su'}


def nombre(t):
    """NOMBRE PROPIO GRITADO → Nombre Propio (conectores en minúscula, siglas).

    Es para sujetos —empresas, municipios, proyectos—, donde `frase` dejaría
    «Municipio de la estrella». Lo que ya viene en mixtas no se toca.
    """
    t = (t or '').strip()
    if not _gritado(t):
        return t
    out = []
    for i, w in enumerate(t.split()):
        wl = w.lower()
        if i and wl in _CONECTORES:
            out.append(wl)
        elif wl in SIGLAS or re.fullmatch(r'[a-z](?:\.[a-z])*\.?', wl) and len(wl) <= 6 \
                or re.search(r'\d', wl) and len(wl) <= 6:
            out.append(w.upper())
        else:
            out.append(wl[:1].upper() + wl[1:])
    return ' '.join(out)


def capitalizar(t):
    t = (t or '').strip()
    return t[:1].upper() + t[1:] if t else t


def recortar_palabra(s, n):
    s = (s or '').strip()
    if len(s) <= n:
        return s
    corte = s[:n]
    esp = corte.rfind(' ')
    if esp > n * 0.6:
        corte = corte[:esp]
    return corte.rstrip(' ,;:.-·(') + '…'


# --------------------------------------------------------------------- hecho

# El encabezado del acto. Admite "Por la cual", "Por el cual", "Por medio de la
# cual", "Por medio del cual", con o sin mayúscula sostenida.
_RX_ENCABEZADO = re.compile(
    r'^\s*por\s+(?:medio\s+)?(?:de\s+)?(?:la|el|del)\s+cual\s+se\s+', re.I)

# La cola de relleno que casi todos traen.
_RX_COLA = re.compile(
    r'[,;]?\s*(?:y\s+)?se\s*(?:toman?|adoptan?|dictan?|ordenan?)\s+'
    r'(?:otras?|unas?|algunas?)\s+(?:determinaci[oó]n(?:es)?|disposici[oó]n(?:es)?'
    r'|decisi[oó]n(?:es)?|medidas?)\s*\.?\s*$', re.I)

_RX_PRESENTADA = re.compile(
    r',?\s+(?:presentad[oa]s?|solicitad[oa]s?|interpuest[oa]s?|radicad[oa]s?)\s+por\s+'
    r'(?:la\s+|el\s+)?(?:sociedad|empresa|señora?|señores|firma|se[ñn]or)?\b.*$', re.I)

# Formas específicas primero: la traducción es de la FRASE, no del verbo. Cada
# patrón corre contra el texto plegado (sin tildes, minúsculas) y el reemplazo
# se aplica sobre el ORIGINAL (para conservar nombres, números y siglas) vía el
# mismo span. `\1` etc. apuntan al original.
_FORMAS = [
    # decaimiento / vigencia
    (r'^declaran?\s+la\s+perdida\s+de\s+(?:fuerza\s+)?ejecutori(?:a|edad)\s+de\s+(la\s+|el\s+|del\s+)?',
     r'Queda sin efecto \1'),
    (r'^declaran?\s+la\s+perdida\s+de\s+vigencia\s+de(?:l)?\s+(la\s+|el\s+)?',
     r'Pierde vigencia \1'),
    (r'^declaran?\s+(?:la\s+)?cesacion\s+de\s+(?:un\s+|el\s+)?procedimiento\s+sancionatorio\s+ambiental',
     'Cierran sin sanción un procedimiento sancionatorio ambiental'),
    # sancionatorio
    (r'^ordenan?\s+el\s+inicio\s+de\s+(?:un\s+)?procedimiento\s+sancionatorio\s+ambiental',
     'Abren investigación sancionatoria ambiental'),
    (r'^inician?\s+(?:un\s+|el\s+)?procedimiento\s+sancionatorio\s+ambiental',
     'Abren investigación sancionatoria ambiental'),
    (r'^definen?\s+la\s+responsabilidad\s+(?:en|dentro\s+de)\s+(?:un\s+|el\s+)?procedimiento\s+sancionatorio\s+ambiental',
     'Fallan un procedimiento sancionatorio ambiental (sanción o exoneración)'),
    (r'^formulan?\s+(?:un\s+)?(?:pliego\s+de\s+)?cargos',
     'Formulan cargos'),
    (r'^imponen?\s+(?:una\s+)?multa',
     'Imponen multa'),
    (r'^imponen?\s+(?:una\s+)?sancion',
     'Imponen sanción'),
    (r'^imponen?\s+(?:una\s+)?medida\s+preventiva',
     'Imponen medida preventiva'),
    (r'^levantan?\s+(?:la\s+|las\s+|una\s+)?medidas?\s+preventivas?',
     'Levantan medida preventiva'),
    (r'^vinculan?\s+',
     'Vinculan a un sancionatorio: '),
    # seguimiento
    (r'^(?:efectuan?|realizan?)\s+(?:un(?:os)?\s+)?ajustes?\s+via\s+seguimiento\s+(?:a|de)\s+',
     'Ajustan por seguimiento '),
    (r'^(?:efectuan?|realizan?)\s+(?:un(?:os)?\s+)?ajustes?\s+via\s+seguimiento',
     'Ajustan por seguimiento'),
    (r'^ajustan?\s+via\s+seguimiento\s+',
     'Ajustan por seguimiento '),
    (r'^(?:efectuan?|realizan?)\s+(?:un\s+)?seguimiento\s+(?:ambiental\s+)?a\s+',
     'Hacen seguimiento a '),
    (r'^imponen?\s+(?:unas?\s+)?obligaciones?\s+adicional(?:es)?',
     'Imponen obligaciones adicionales'),
    # archivo / desistimiento / trámite
    (r'^ordenan?\s+el\s+archivo\s+de\s+(?:un\s+|el\s+)?expediente',
     'Archivan el expediente'),
    (r'^ordenan?\s+el\s+archivo\s+de\s+',
     'Archivan '),
    (r'^decretan?\s+el\s+desistimiento\s+tacito\s+de\s+(?:una\s+)?(?:actuacion\s+administrativa|solicitud)',
     'Dan por desistida la solicitud (desistimiento tácito)'),
    (r'^aceptan?\s+el\s+desistimiento\s+(?:expreso\s+)?de\s+(?:una\s+)?(?:actuacion\s+administrativa|solicitud)',
     'Aceptan el desistimiento de la solicitud'),
    (r'^ordenan?\s+no\s+dar\s+tramite\s+a\s+(?:la\s+|una\s+)?solicitud\s+de(?:l)?\s+',
     'No dan trámite a la solicitud de '),
    (r'^inician?\s+(?:el\s+)?tramite\s+administrativo\s+(?:ambiental\s+)?(?:de|para)\s+(?:la\s+)?',
     'Inician trámite de '),
    (r'^inician?\s+(?:un\s+)?tramite\s+',
     'Inician trámite '),
    # recursos
    (r'^resuelven?\s+(?:un\s+|el\s+)?recurso\s+de\s+reposicion\s+(?:interpuesto\s+)?(?:en\s+)?contra\s+(?:de\s+)?(?:la\s+|el\s+)?',
     'Resuelven recurso contra '),
    (r'^resuelven?\s+(?:un\s+|el\s+)?recurso\s+de\s+(?:reposicion|apelacion)',
     'Resuelven un recurso'),
    # cesiones / titularidad
    (r'^autorizan?\s+la\s+cesion\s+(total|parcial)\s+de\s+(?:los\s+)?derechos\s+y\s+obligaciones\s+(?:derivad[oa]s\s+)?(?:de|del)\s+(?:la\s+|el\s+|un\s+|una\s+)?',
     r'Autorizan cesión \1 de '),
    (r'^autorizan?\s+la\s+cesion\s+(?:total|parcial)?\s*de\s+',
     'Autorizan cesión de '),
    (r'^tienen?\s+en\s+cuenta\s+el\s+cambio\s+de\s+razon\s+social\s+(?:del\s+titular\s+)?(?:de\s+)?(?:la\s+|el\s+)?',
     'Registran cambio de razón social del titular de '),
    # dictámenes / certificaciones
    (r'^emiten?\s+(?:un\s+)?dictamen\s+tecnico\s+ambiental\s+para\s+(?:el\s+)?',
     'Emiten dictamen técnico ambiental para '),
    (r'^deciden?\s+(?:una\s+|la\s+)?solicitud\s+de\s+dictamen\s+tecnico\s+ambiental',
     'Deciden una solicitud de dictamen técnico ambiental'),
    (r'^expiden?\s+(?:una\s+)?certificacion\s+de\s+beneficio\s+ambiental',
     'Certifican beneficio ambiental'),
    (r'^certifican?\s+que\s+',
     'Certifican que '),
    # licencias / permisos
    (r'^otorgan?\s+(?:una\s+|la\s+)?licencia\s+ambiental',
     'Otorgan licencia ambiental'),
    (r'^niegan?\s+(?:una\s+|la\s+)?licencia\s+ambiental',
     'Niegan licencia ambiental'),
    (r'^modifican?\s+(?:una\s+|la\s+)?licencia\s+ambiental',
     'Modifican licencia ambiental'),
    (r'^niegan?\s+(?:una\s+|la\s+)?(?:solicitud\s+de\s+)?(?:autorizacion|permiso)\s+(?:para|de)\s+',
     'Niegan permiso de '),
    (r'^otorgan?\s+(?:una\s+|un\s+|la\s+|el\s+)?(?:autorizacion|permiso)\s+(?:para|de)\s+',
     'Otorgan permiso de '),
    (r'^niegan?\s+(?:una\s+|la\s+)?solicitud\s+de(?:l)?\s+',
     'Niegan la solicitud de '),
    (r'^niegan?\s+(?:un\s+|una\s+|el\s+|la\s+)?cupo\s+de\s+',
     'Niegan cupo de '),
    (r'^(?:otorgan?|asignan?)\s+(?:un\s+|una\s+|el\s+|la\s+)?cupo\s+de\s+',
     'Asignan cupo de '),
]
_FORMAS_C = [(re.compile(p), r) for p, r in _FORMAS]

# Verbo suelto → forma de titular (tercera plural impersonal, como titula la
# prensa: «Niegan», «Otorgan»). Lo que siga queda tal cual.
_VERBOS = {
    'niega': 'Niegan', 'otorga': 'Otorgan', 'autoriza': 'Autorizan',
    'modifica': 'Modifican', 'aclara': 'Aclaran', 'acepta': 'Aceptan',
    'aprueba': 'Aprueban', 'rechaza': 'Rechazan', 'levanta': 'Levantan',
    'impone': 'Imponen', 'imponen': 'Imponen', 'certifica': 'Certifican',
    'asigna': 'Asignan', 'mantiene': 'Mantienen', 'evalua': 'Evalúan',
    'emite': 'Emiten', 'expide': 'Expiden', 'reconoce': 'Reconocen',
    'suspende': 'Suspenden', 'revoca': 'Revocan', 'sanciona': 'Sancionan',
    'archiva': 'Archivan', 'requiere': 'Requieren', 'prorroga': 'Prorrogan',
    'renueva': 'Renuevan', 'corrige': 'Corrigen', 'adiciona': 'Adicionan',
    'establece': 'Establecen', 'declara': 'Declaran', 'resuelve': 'Resuelven',
    'decide': 'Deciden', 'decreta': 'Decretan', 'inicia': 'Inician',
    'ordena': 'Ordenan', 'efectua': 'Efectúan', 'realiza': 'Realizan',
    'ajusta': 'Ajustan', 'define': 'Definen', 'vincula': 'Vinculan',
    'da': 'Dan', 'tiene': 'Tienen', 'fija': 'Fijan', 'amplia': 'Amplían',
    'concede': 'Conceden', 'impone_': 'Imponen', 'exonera': 'Exoneran',
    'cesa': 'Cesan', 'termina': 'Terminan', 'abre': 'Abren', 'cierra': 'Cierran',
    'reglamenta': 'Reglamentan', 'adopta': 'Adoptan', 'dicta': 'Dictan',
    'actualiza': 'Actualizan', 'incluye': 'Incluyen', 'excluye': 'Excluyen',
    'inscribe': 'Inscriben', 'cancela': 'Cancelan', 'acoge': 'Acogen',
    'unifica': 'Unifican', 'traslada': 'Trasladan', 'designa': 'Designan',
    'crea': 'Crean', 'delega': 'Delegan', 'habilita': 'Habilitan',
    'prescribe': 'Prescriben', 'deroga': 'Derogan', 'sustituye': 'Sustituyen',
    'prohibe': 'Prohíben', 'exige': 'Exigen', 'precisa': 'Precisan',
    'imparte': 'Imparten', 'señala': 'Señalan', 'senala': 'Señalan',
    'determina': 'Determinan', 'convoca': 'Convocan', 'liquida': 'Liquidan',
    'compila': 'Compilan', 'complementa': 'Complementan', 'acredita': 'Acreditan',
    'aprueban': 'Aprueban', 'autorizan': 'Autorizan', 'niegan': 'Niegan',
}


def hecho(motivo):
    """«Por la cual se niega cupo…» → «Niegan cupo…». None si no es encabezado.

    Devolver None (y no el texto original) es lo que le dice al llamador que
    este motivo NO es un encabezado de acto —INVIMA, SFC y SECOP traen ahí la
    conducta sancionada— y que la tarjeta debe seguir como estaba.
    """
    m = _RX_ENCABEZADO.match(motivo or '')
    if not m:
        return None
    resto = motivo[m.end():].strip()
    resto = _RX_COLA.sub('', resto).strip().rstrip('.;,')
    # «…presentada por la sociedad X S.A.S.» / «…presentada por JUAN PÉREZ»: el
    # solicitante ya va como sujeto cuando es empresa, y cuando es una persona
    # natural no se titula con su nombre. Queda en el detalle (texto formal).
    resto = _RX_PRESENTADA.sub('', resto).strip().rstrip('.;,')
    if not resto:
        return None
    # Un encabezado GRITADO se baja a frase antes: si no, lo que quede después
    # del verbo traducido sale a gritos («cesión de UNA LICENCIA AMBIENTAL»).
    if _gritado(resto):
        resto = frase(resto)
        resto = resto[:1].lower() + resto[1:]
    # Frase primero; el patrón corre sobre el plegado y el span se aplica al
    # original, que conserva tildes, siglas y números.
    plano = _fold(resto)
    for rx, rep in _FORMAS_C:
        mm = rx.match(plano)
        if mm:
            cabeza = mm.expand(rep) if '\\' in rep else rep
            # los grupos capturados vienen del texto PLEGADO: si era «del», el
            # sustantivo que sigue pide «el».
            cabeza = re.sub(r'\s+del\s*$', ' el ', cabeza)
            cabeza = re.sub(r'\s+$', ' ', cabeza)
            return capitalizar((cabeza + resto[mm.end():]).strip())
    # Verbo suelto.
    mv = re.match(r'^(\w+)\b\s*', plano)
    if mv:
        v = mv.group(1)
        forma = _VERBOS.get(v) or (_VERBOS.get(v[:-1]) if v.endswith('n') else None)
        if forma:
            return capitalizar(forma + ' ' + resto[mv.end():].lstrip())
    return capitalizar('Se ' + resto)


# -------------------------------------------------------------------- sujeto

# Producto (plaguicidas, DTA): la fuente lo escribe en mayúscula dentro del
# encabezado. Se toma lo que está entre «producto (formulado)» y la coma, el
# «con (base en el) ingrediente» o el «a partir de». Siempre literal.
_RX_PRODUCTO = re.compile(
    r'producto\s+(?:formulado\s+|plaguicida\s+)?'
    r'([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9®™%\-\./ ]{1,40}?)'
    r'(?=\s*[,;(]|\s+con\b|\s+a\s+partir\b|\s+y\s+se\b|\s+cuyo\b|\s*$)')

# Primer segmento de `descripcion` que NO es un proyecto (el campo trae
# proyecto · ubicación, pero cuando no hay proyecto trae el tipo de documento o
# el grupo interno de la ANLA).
_GENERICOS = (
    'auto', 'resolucion', 'resoluciòn', 'grupo de', 'sin proyecto',
    'prueba din', 'certificado de emisiones', 'notificaci', 'comunicado',
    'solicitud dta', 'solicitud de dta', 'dictamen tecnico ambiental',
    'solicitud dictamen', 'traslado solicitud', 'permiso recoleccion',
    'permiso marco', 'plan de gestion', 'desistimiento', 'autorizacion',
    'autorizaciòn', 'licencia ambiental actividad', 'recurso', 'derecho de',
    'pqrs', 'consulta', 'oficio', 'memorando', 'radicado', 'expediente',
    'tramite', 'cesion', 'modificacion', 'otro', 'permiso', 'solicitud',
    'licencia', 'establecimiento', 'enviar', 'queja', 'respuesta', 'informe',
    'acta', 'concepto', 'requerimiento', 'certificacion', 'seguimiento',
    'evaluacion', 'visita', 'entrega', 'documento', 'anexo', 'formulario',
    'por la cual', 'por el cual', 'por medio', 'solicita', 'se ', 'el ', 'la ',
    'recoleccion de especimenes', 'estudio para la recoleccion', 'aprovechamiento forestal',
    'ocupacion de cauce', 'levantamiento parcial de veda', 'levantamiento de veda',
    'emisiones atmosfericas', 'vertimiento', 'concesion', 'consentimiento',
    'especies silvestres', 'especimenes', 'importacion de', 'exportacion de',
    'movimiento transfronterizo',
)
# Prefijos de TRÁMITE que envuelven el nombre del proyecto: «Solicitud de
# licencia ambiental para el área de interés exploratorio Noelia» → el proyecto
# es «Área de interés exploratorio Noelia». Se quita solo el envoltorio; el
# resto sigue siendo literal de la fuente.
_RX_PREFIJO_TRAMITE = re.compile(
    r'^(?:solicitud\s+de\s+|modificaci[oó]n\s+(?:de\s+)?(?:la\s+)?|establecimiento\s+(?:de\s+)?(?:un\s+)?)?'
    r'(?:licencia\s+ambiental|plan\s+de\s+manejo\s+ambiental|estudio\s+de\s+impacto\s+ambiental'
    r'|diagn[oó]stico\s+ambiental\s+de\s+alternativas|permiso\s+de\s+\w+(?:\s+de\s+\w+)?)'
    r'\s+(?:para|del?|global\s+para)\s+(?:el\s+|la\s+|los\s+|las\s+)?(?:proyecto\s+(?!de\b))?(?:denominad[oa]\s+)?',
    re.I)

# Un código de expediente («Pda1086-00-2026», «LAV0009-00-2024») no es un nombre.
_RX_CODIGO = re.compile(r'^[A-Za-z]{0,5}\d[\w\-/]*$')

# «Permiso de Ocupación de Cauce-MUNICIPIO DE LA ESTRELLA»: el solicitante va
# textual, en mayúsculas, tras el guion. Se exige ≥2 palabras reales y que el
# segmento no venga cortado por el slim (120 chars), porque un nombre cortado
# («GESTION FORESTAL Y ASESORIAS A») es peor que ninguno.
_RX_SOLICITANTE = re.compile(
    r'^(?:Permiso|Autorizaci[oó]n|Prospecci[oó]n|Licencia|Concesi[oó]n|Registro|'
    r'Certificaci[oó]n|Aprovechamiento|Ocupaci[oó]n|Plan)[^-]{3,70}-\s*'
    r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9&\.\s]{5,90})$')
_LARGO_SLIM = 118


def _es_generico(seg):
    f = _fold(seg).strip()
    if (not f) or len(f) < 4 or _RX_CODIGO.match(f):
        return True
    # El solicitante tras guion («Permiso de Ocupación de Cauce-MUNICIPIO…»)
    # se evalúa aparte: acá solo se descarta el segmento como PROYECTO.
    return any(f.startswith(g) for g in _GENERICOS)


def _segmento_proyecto(descripcion):
    seg = (descripcion or '').split(' · ')[0].strip()
    if not seg:
        return None, None
    # Solicitante tras guion (solo si el campo no viene truncado).
    if len((descripcion or '').strip()) < _LARGO_SLIM:
        ms = _RX_SOLICITANTE.match(seg)
        if ms:
            nom = ms.group(1).strip(' .')
            if len(nom.split()) >= 2 and _gritado(nom) and not _es_generico(nom):
                return 'solicitante', nom
    # «Licencia Ambiental “Construcción de la Variante de Ipiales” (tramo 1)»:
    # lo entrecomillado ES el nombre.
    mq = re.search(r'[“"]([^”"]{10,90})[”"]', seg)
    if mq and not _es_generico(mq.group(1)):
        return 'proyecto', mq.group(1).strip()
    pelado = _RX_PREFIJO_TRAMITE.sub('', seg, count=1).strip(' "“”.,')
    if pelado != seg and len(pelado) >= 10 and not _es_generico(pelado):
        return 'proyecto', pelado[:1].upper() + pelado[1:]
    if _es_generico(seg):
        return None, None
    return 'proyecto', seg


FUENTES_CON_PROYECTO = {'anla-gaceta'}


def sujeto(row):
    """→ (tipo, texto) con tipo ∈ {entidad, producto, solicitante, proyecto} o (None, None)."""
    ent = str(row.get('sancionado') or '').strip()
    if ent and ent.lower() not in {'', '-', '—', '–', 'n/a', 'na', 'null', 'none', 'no aplica'}:
        return 'entidad', ent
    motivo = row.get('motivo') or ''
    mp = _RX_PRODUCTO.search(motivo)
    if mp:
        prod = mp.group(1).strip(' .-/')
        if len(prod) >= 2 and not _fold(prod).startswith(('formulado', 'con ')):
            return 'producto', prod
    # De aquí para abajo se lee `descripcion`, y su significado depende de la
    # fuente: en ANLA es «proyecto · ubicación»; en UIAF o SIC es la entidad
    # que EMITE el acto. Solo ANLA está medida → solo ANLA pasa.
    if (row.get('fuente') or '') not in FUENTES_CON_PROYECTO:
        return None, None
    md = _RX_PRODUCTO.search(row.get('descripcion') or '')
    if md:
        prod = md.group(1).strip(' .-/')
        if len(prod) >= 2:
            return 'producto', prod
    tipo, seg = _segmento_proyecto(row.get('descripcion') or '')
    if seg:
        if tipo == 'proyecto':
            # «…, ubicado en jurisdicción de…» es ubicación, no nombre.
            seg = re.split(r',?\s+(?:ubicad[oa]s?|localizad[oa]s?)\s+en\b', seg, maxsplit=1)[0].strip(' ,')
            # «NOMBRE DEL PROYECTO - CESIÓN PARCIAL PMA»: lo de antes del guion
            # es el nombre; lo de después, el trámite. Solo si queda un nombre.
            cab = re.split(r'\s+[-–—]\s+', seg, maxsplit=1)[0].strip()
            if len(cab) >= 15:
                seg = cab
            # «Proyecto X Auto 2920 del 27 de julio…»: el acto pegado al nombre.
            seg = re.split(r'\s+(?:(?:Auto|Resoluci[oó]n|Expediente|Exp\.?)\s+(?:No\.?\s*)?)?\d{2,6}\s+del?\s+\d{1,2}\s+de\s+\w+'
                           r'|\s+(?:Auto|Resoluci[oó]n|Expediente|Exp\.?)\s+(?:No\.?\s*)?\d'
                           r'|\s+concepto\s+t[eé]cnico\b', seg, maxsplit=1, flags=re.I)[0].strip(' ,.-')
            seg = nombre(seg)            # antes del recorte: «KV Y…» no es una sigla
            # Un proyecto largo se corta en palabra; uno cortado por el slim
            # también, y el «…» lo declara.
            seg = recortar_palabra(seg, 72)
        return tipo, seg
    return None, None


# ------------------------------------------------------------------- titular

def titular(row):
    """→ (titulo, detalle, info) o None si no aplica (motivo sin encabezado).

    `info` dice cómo se armó: {'sujeto': tipo|None, 'hecho': bool}. Sirve para
    medir y para que el render no tenga que adivinar.
    """
    motivo = (row.get('motivo') or '').strip()
    h = hecho(motivo)
    tipo, suj = sujeto(row)
    if h is None and tipo != 'entidad':
        return None
    if h is None:
        # Entidad con un motivo que no es encabezado: se conserva la forma de
        # siempre (entidad arriba, motivo abajo).
        return None
    h = frase(h)
    if suj and tipo in ('proyecto', 'solicitante'):
        nucleo = _fold(suj.rstrip('…'))[:28].strip()
        pos = _fold(h).find(nucleo) if nucleo else -1
        if pos >= 0:
            # «…con cargo a la inversión del 1% del proyecto construcción y
            # operación del puerto…»: el proyecto ya va de sujeto, así que el
            # hecho se corta donde empieza a repetirlo.
            mm = re.search(r'\s+(?:del|para\s+el|de\s+la|en\s+el|al)\s+(?:proyecto|licencia|campo|bloque|area|área)\b[^,;]*$',
                           h[:pos + len(nucleo) + 8], re.I)
            if mm and mm.start() > 15:
                h = h[:mm.start()].rstrip(' ,;:')
            elif pos < 40:
                # «Inician trámite de Permiso X» con sujeto «Permiso X»: el
                # sujeto va primero en el hecho, repetirlo no informa.
                suj = None
    if suj:
        pref = nombre(suj) if tipo != 'producto' else suj
        if tipo == 'producto':
            pref = f'Producto {pref}'
        titulo = f'{pref} — {h}'
    else:
        titulo = h
    # El detalle conserva el nombre formal del acto: es lo que se cita en una
    # reunión, y la razón de que el titular pueda ser llano sin perder nada.
    # Sin sujeto, el titular YA es ese texto y repetirlo abajo no suma: queda
    # vacío para que el llamador ponga el expediente.
    detalle = frase(motivo) if suj else ''
    return titulo, detalle, {'sujeto': tipo if suj else None, 'hecho': True}


if __name__ == '__main__':        # prueba rápida con casos reales del digest
    CASOS = [
        {'fuente': 'anla-gaceta', 'motivo': 'Por la cual se declara la pérdida de ejecutoriedad de la Resolución 1029 del 8 de octubre de 2013',
         'descripcion': 'Dictamen Técnico Ambiental para el producto BULLET con ingrediente activo FENPROPIMORPH.', 'sancionado': '—'},
        {'fuente': 'anla-gaceta', 'motivo': 'POR LA CUAL SE EFECTÚAN UNOS AJUSTES VÍA SEGUIMIENTO Y SE ADOPTAN OTRAS DETERMINACIONES',
         'descripcion': 'OPERACIÓN Y FUNCIONAMIENTO DEL AEROPUERTO INTERNACIONAL PALONEGRO - CESIÓN PARCIAL PMA · Grupo de Medio Magdalena', 'sancionado': '—'},
        {'fuente': 'anla-gaceta', 'motivo': 'Por la cual se niega una autorización para ocupación de cauce y se toman otras determinaciones',
         'descripcion': 'Permiso de Ocupación de Cauce-MUNICIPIO DE LA ESTRELLA', 'sancionado': '—'},
        {'fuente': 'anla-gaceta', 'motivo': 'POR EL CUAL SE ORDENA EL INICIO DE UN PROCEDIMIENTO SANCIONATORIO AMBIENTAL Y SE ADOPTAN OTRAS DETERMINACIONES',
         'descripcion': 'Área De Perforación Exploratoria Lla-71, ubicado en jurisdicción de los municipios de Maní y Orocué, en el dep', 'sancionado': '—'},
        {'motivo': 'Por medio de la cual se tiene en cuenta el cambio de razón social del titular de la Licencia Ambiental otorgada mediante Resolución 1795 de 2010',
         'descripcion': 'Resolución', 'sancionado': 'ECOPETROL S.A.'},
    ]
    for c in CASOS:
        print(titular(c))
