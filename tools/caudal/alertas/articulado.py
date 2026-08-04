#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — el articulado leído, para que el «por qué» diga algo.

Hasta acá el motor sabía decir POR QUÉ marcó una señal ("radicado en la Comisión
Séptima") pero no POR QUÉ IMPORTA. Eso es un dato del registro, no una razón: a
un gremio no le cambia nada que un proyecto haya caído en una comisión u otra.
Lo que le cambia la vida es qué obligación nueva aparece, sobre quién recae, si
trae régimen sancionatorio y qué norma vigente toca.

Eso ya está extraído del texto radicado completo y publicado en
`s3://caudal-legislativo/metadata/articulado.json` (lo produce otro frente). Este
módulo lo lee, decide **de cuáles registros se puede uno fiar**, y los deja
listos para que `reglas.py` redacte la razón.

---------------------------------------------------------------------------
EL FILTRO DE CONFIANZA (lo más importante de este archivo)
---------------------------------------------------------------------------

Medido sobre la publicación del 2026-08-03 (231 proyectos): **55 registros (24%)
son proyectos de CÁMARA cuyo texto se extrajo de un archivo del SENADO**. Es el
trap que el proyecto ya tiene documentado — «el número de radicado NO es
identificador único»: el número se reinicia en cada cámara, así que el 077/26 de
Cámara y el 077/26 de Senado son proyectos distintos, y al cruzarlos por número
el articulado quedó pegado al proyecto equivocado.

No es una sospecha, es verificable a mano:

  pdly:900009  «…GESTORES COMUNITARIOS DEL AGUA Y SANEAMIENTO BÁSICO…»
               resumen: "Crea una ruta de formalización … para el TURISMO RURAL,
               otorga incentivos tributarios … exoneración de IVA al combustible"

  pdly:900010  «…SE REGULA LA INTELIGENCIA ARTIFICIAL EN COLOMBIA…»
               resumen: "Crea la estrategia Rutas de Transporte Sociales y
               Turísticas … beneficios tributarios en tiquetes aéreos"

En cifras: el solape de vocabulario entre el título del proyecto y su propio
resumen es **0.03 en ese grupo contra 0.50-0.54 en el resto** (98% de ellos por
debajo de 0.25). Y el campo `confianza` que trae la fuente NO los detecta: los
dos ejemplos de arriba vienen marcados «media» y «alta».

Un correo que le dice a un gremio de acueductos que su proyecto le crea
obligaciones de registro turístico es peor que el «por qué» genérico que se
quería arreglar: es confiadamente falso. Así que se descartan.

El filtro es estructural, no lexical: **la cámara que implica el id tiene que
coincidir con la cámara del archivo de donde salió el texto** (los ids ≥ 900000
son de Cámara — es el `ID_BASE` del proyecto). Se probó también un filtro por
solape de palabras y se descartó: produce falsos rechazos (un resumen fiel de
«cárceles productivas» habla de «redención de pena por trabajo» y no comparte
casi ninguna palabra con su título).

También queda fuera lo que se extrajo **solo del título** (`base: 'titulo'`, 22
registros): ahí no se leyó ningún texto, así que sus «obligaciones» son
inferidas, no leídas. Decir "todavía no hemos leído su articulado" es exacto.

Quedan **154 de 231 registros utilizables**, y son los que se pueden defender
uno por uno frente a un cliente.
"""

import json
import os
import re
import unicodedata

CLAVE_S3 = 'metadata/articulado.json'

# Los ids de Cámara arrancan en 900.000 para no chocar con los del Senado.
# Es la misma convención de los builders del dataset (`ID_BASE`).
ID_BASE_CAMARA = 900_000


# ---------------------------------------------------------------------------
# NORMALIZACIÓN
# ---------------------------------------------------------------------------

def _norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s.lower())).strip()


def numero_canonico(num):
    """'001/2026C' · '140/26' · 'PL-077-26' → '77/26'. None si no se puede.

    El año se reduce SIEMPRE a dos dígitos y el consecutivo pierde los ceros a la
    izquierda, porque las dos fuentes escriben el mismo número de tres maneras.
    """
    m = re.search(r'(\d{1,4})\s*[/-]\s*(\d{2,4})', str(num or ''))
    if not m:
        return None
    return f'{int(m.group(1))}/{m.group(2)[-2:]}'


# Nombre del archivo de texto radicado: PL-077-26.txt (Senado) ·
# PLC-022-2026C.txt (Cámara).
_RE_ARCHIVO = re.compile(r'/PLC?-?(\d+)-(\d{2,4})C?\.txt$', re.I)


def _camara_de_fuente(fuente):
    """De qué cámara es el archivo del que se extrajo el texto. None si no aplica."""
    f = str(fuente or '')
    if 'radicados-camara-texto' in f:
        return 'camara'
    if 'radicados-texto' in f:
        return 'senado'
    return None                      # gaceta, o sin fuente


def _camara_de_id(pid):
    try:
        return 'camara' if int(pid) >= ID_BASE_CAMARA else 'senado'
    except (TypeError, ValueError):
        return None


def evaluar(reg):
    """(utilizable, motivo). El motivo se muestra: nada se descarta en silencio."""
    base = (reg.get('base') or '').strip()
    if base == 'titulo' or not base:
        return False, 'solo se leyó el título, no el articulado'

    cam_id = _camara_de_id(reg.get('id'))
    cam_fuente = _camara_de_fuente(reg.get('fuente'))
    if cam_id and cam_fuente and cam_id != cam_fuente:
        # El caso de los 55: texto de la otra cámara pegado por número.
        return False, ('el texto extraído es de la otra cámara (el número de '
                       'radicado se repite entre Senado y Cámara)')

    if not (reg.get('resumen') or reg.get('obligaciones') or reg.get('modifica')):
        return False, 'la extracción quedó vacía'
    return True, ''


# ---------------------------------------------------------------------------
# ÍNDICE
# ---------------------------------------------------------------------------

class Indice:
    """Articulado utilizable, indexado por las tres llaves que trae un evento.

    El evento de un radicado del Senado trae `id` y `type` (llave directa); el de
    Cámara no trae ninguno de los dos, así que hay que caer al número — y ahí
    aparece de nuevo el problema de identidad, por eso el índice por número está
    SCOPED por cámara y descarta cualquier número ambiguo en vez de adivinar.
    """

    def __init__(self, datos=None):
        self.v = (datos or {}).get('v') or ''
        self.total = 0
        self.utilizables = 0
        self.descartes = {}
        self.por_tok = {}
        self.por_id = {}
        self.por_num = {}
        self.por_titulo = {}
        self._cargar(datos or {})

    def _cargar(self, datos):
        por_num = {}
        for tok, reg in (datos.get('por_proyecto') or {}).items():
            self.total += 1
            ok, motivo = evaluar(reg)
            if not ok:
                self.descartes[motivo] = self.descartes.get(motivo, 0) + 1
                continue
            self.utilizables += 1
            reg = dict(reg)
            reg['tok'] = tok
            self.por_tok[tok] = reg
            self.por_id[str(reg.get('id'))] = reg

            t = _norm(reg.get('titulo'))
            if t:
                # un título repetido es dos radicaciones distintas del mismo
                # texto: no se puede elegir, así que no se indexa.
                self.por_titulo[t] = None if t in self.por_titulo else reg

            m = _RE_ARCHIVO.search(reg.get('fuente') or '')
            if m:
                clave = (_camara_de_fuente(reg.get('fuente')),
                         f'{int(m.group(1))}/{m.group(2)[-2:]}')
                por_num.setdefault(clave, []).append(reg)

        self.por_num = {k: v[0] for k, v in por_num.items() if len(v) == 1}
        self.por_titulo = {k: v for k, v in self.por_titulo.items() if v}

    def __len__(self):
        return self.utilizables

    def buscar(self, pid=None, tab=None, numero=None, camara=None, titulo=None):
        """El articulado de un proyecto, o None. Por orden de fiabilidad."""
        if pid is not None:
            reg = self.por_tok.get(f'{tab or "pdly"}:{pid}') or self.por_id.get(str(pid))
            if reg:
                return reg
        num = numero_canonico(numero)
        if num and camara:
            reg = self.por_num.get((camara, num))
            if reg:
                return reg
        if titulo:
            reg = self.por_titulo.get(_norm(titulo))
            if reg:
                return reg
        return None


VACIO = Indice({})


def cargar(ruta):
    """Índice desde el JSON ya descargado. Nunca lanza: sin articulado el motor
    sigue corriendo y lo dice, que es justo lo que se le pide al «por qué»."""
    try:
        with open(ruta, encoding='utf-8') as fh:
            return Indice(json.load(fh))
    except (OSError, ValueError):
        return Indice({})


# ---------------------------------------------------------------------------
# LECTURA DE UN REGISTRO
# ---------------------------------------------------------------------------
# Lo que sigue no interpreta: recorta y ordena. La interpretación (qué es alto,
# cómo se redacta) vive en reglas.py, con el resto del criterio editorial.

def obligaciones(reg):
    return [o for o in (reg.get('obligaciones') or []) if isinstance(o, dict)
            and (o.get('obligacion') or '').strip()]


def sanciones(reg):
    return [s for s in (reg.get('sanciones') or []) if isinstance(s, dict)
            and ((s.get('conducta') or '').strip() or (s.get('tipo') or '').strip())]


# Una norma citada tiene número y año, o es un cuerpo con nombre propio. Sin
# esto se colaba la cláusula de derogatoria («disposiciones que le sean
# contrarias»), que aparece en casi todos los proyectos y no dice nada: el
# cliente lee «modifica: disposiciones que le sean contrarias» y no puede hacer
# nada con eso.
_RE_NORMA = re.compile(r'\b(19|20)\d{2}\b|\bn\.?[°º]|\bconstituci|\bcodigo\b|\bcódigo\b|\bestatuto\b',
                       re.I)


def modifica(reg):
    out = []
    for m in (reg.get('modifica') or []):
        if not isinstance(m, dict):
            continue
        norma = (m.get('norma') or '').strip()
        if norma and _RE_NORMA.search(norma):
            out.append(m)
    return out


def vigilancia(reg):
    return [v for v in (reg.get('vigilancia') or []) if isinstance(v, dict)
            and (v.get('entidad') or '').strip()]


def sujetos(reg):
    a = reg.get('aplica_a') or {}
    return [s for s in (a.get('sujetos') or []) if str(s or '').strip()]


def sectores(reg):
    a = reg.get('aplica_a') or {}
    return [s for s in (a.get('sectores') or []) if str(s or '').strip()]


def norma_legible(m):
    """{'norma': 'Ley 100 de 1993', 'articulos': ['156','177']} → texto corto."""
    norma = (m.get('norma') or '').strip()
    arts = [str(a).strip() for a in (m.get('articulos') or []) if str(a).strip()]
    if not arts:
        return norma
    if len(arts) > 3:
        return f'{norma} (arts. {", ".join(arts[:3])} y {len(arts) - 3} más)'
    etiqueta = 'art.' if len(arts) == 1 else 'arts.'
    return f'{norma} ({etiqueta} {", ".join(arts)})'


def sancion_legible(s):
    """QUÉ castigo trae, en una frase. '' si el texto no lo dice.

    Nunca cae a `conducta`: la conducta es lo que se castiga, no la sanción, y
    devolverla ahí producía la línea «Régimen sancionatorio: Solicitar
    autorización previa…», que se lee como si el proyecto sancionara al revés.
    Cuando no hay tipo ni cuantía, quien llama dice que no está cuantificada —
    que es la verdad y se entiende.
    """
    tipo = (s.get('tipo') or '').strip().replace('_', ' ')
    cuantia = (s.get('cuantia') or '').strip() if isinstance(s.get('cuantia'), str) else ''
    if tipo.lower() in ('otra', 'otro', 'n/a', 'ninguna'):
        tipo = ''
    if cuantia and tipo:
        return f'{tipo} de {cuantia}'
    return cuantia or tipo


def entidades_vigilantes(reg):
    """Quién queda a cargo de hacerlo cumplir (sin repetir)."""
    out = []
    for v in vigilancia(reg):
        ent = (v.get('entidad') or '').strip()
        if ent and ent not in out:
            out.append(ent)
    return out
