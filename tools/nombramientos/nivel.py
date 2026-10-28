"""Nivel del servicio contratado, leído del OBJETO del contrato (no de la persona).

SECOP no publica la formación del contratista. Lo que sí trae el objeto es cómo la
entidad tipificó el servicio, y esa tipificación es la que fija la tabla de honorarios
(asesor > profesional especializado > profesional > técnico > apoyo/asistencial).
Orden de las reglas: gana la primera que casa, de la más específica a la más general.
  · «OFICINA ASESORA» o «DIRECCIÓN DE ASESORÍA» no es un asesor: es el nombre de una dependencia o una
    actividad. Asesor solo cuando el objeto contrata a la persona COMO asesor o consultor, o asesor
    jurídico/experto/del despacho. Medido: con «asesor» suelto, la mediana del honorario de esa
    categoría quedaba POR DEBAJO de la de profesional, señal de que casaba lo que no era.
  · «servicios profesionales y de apoyo a la gestión COMO TÉCNICO» es técnico: manda el «como».
"""
import re

NIVELES = ['Asesor o consultor', 'Profesional especializado', 'Profesional', 'Técnico o tecnólogo',
           'Apoyo a la gestión o asistencial', 'Sin nivel en el objeto']
_R = [
    ('Técnico o tecnólogo', re.compile(r'\bCOMO\s+(UN\s+|UNA\s+)?(T[EÉ]CNIC|TECN[OÓ]LOG|AUXILIAR)|T[EÉ]CNICO\s+AUXILIAR', re.I)),
    ('Asesor o consultor', re.compile(r'\bCOMO\s+(UN\s+|UNA\s+)?(ASESOR|CONSULTOR|EXPERTO|EXPERTA)\b|(?<!OFICINA )(?<!OFICINAS )\bASESOR(A)?\s+(JUR[IÍ]DIC|EXPERT|SENIOR|S[EÉ]NIOR|DEL\s+DESPACHO|DE\s+DESPACHO)|'
                                       r'SERVICIOS\s+(PROFESIONALES\s+)?DE\s+(ASESOR[IÍ]A|CONSULTOR[IÍ]A)\s+(ESPECIALIZAD|JUR[IÍ]DIC|EXPERT|AL\s+DESPACHO|A\s+LA\s+DIRECCI)|\bCONSULTOR\s+(EXPERT|SENIOR|S[EÉ]NIOR)', re.I)),
    ('Profesional especializado', re.compile(r'ESPECIALIZAD|ESPECIALISTA|\bMAG[IÍ]STER\b|\bMAESTR[IÍ]A\b', re.I)),
    ('Profesional', re.compile(r'PROFESIONAL', re.I)),
    ('Técnico o tecnólogo', re.compile(r'T[EÉ]CNIC[OA]S?\b|TECN[OÓ]LOG[OA]|SERVICIOS\s+T[EÉ]CNICOS', re.I)),
    ('Apoyo a la gestión o asistencial', re.compile(r'APOYO|ASISTENCIAL|AUXILIAR|OPERATIV|LOG[IÍ]STIC|ASISTENTE|CONDUCTOR|MENSAJER|SERVICIOS\s+GENERALES', re.I)),
]


def nivel(objeto):
    o = re.sub(r'\s+', ' ', objeto or '')
    for n, rx in _R:
        if rx.search(o):
            return n
    return 'Sin nivel en el objeto'
