"""
Caudal · qué se votó, y si el Sí favorece o frena el proyecto.

Una plenaria vota MUCHAS cosas sobre el mismo proyecto y no todas dicen lo
mismo: un Sí al informe de ponencia lo empuja, un Sí a la proposición de
aplazamiento lo frena, y un Sí a los impedimentos de un representante no es
posición sobre nada. Sumarlas en un solo contador Sí/No por proyecto (lo que
hacía la ficha del congresista) produce cifras sin sentido — un Pacto con
40 Sí · 36 No en la reforma a la salud.

`clasificar(nombre)` → (tipo, sentido)
  sentido +1 · el Sí empuja el proyecto (ponencia positiva, articulado,
              título, conciliación, proposiciones avaladas)
  sentido -1 · el Sí lo frena (aplazamiento, archivo/ponencia negativa,
              eliminación, proposiciones NO avaladas, sustitutivas)
  sentido  0 · procedimiento sin posición (impedimentos, orden del día,
              suspensión) o tipo que no se sabe leer sin el acta (objeciones,
              otro)

Tipos DE FONDO (los que se usan para decir «votó a favor / en contra del
proyecto»): ponencia · articulado · titulo · conciliacion · aplazamiento ·
archivo. Las proposiciones sobre artículos sueltos (avalada / no_avalada /
eliminacion / sustitutiva) son posición sobre un TEXTO, no sobre el proyecto,
y quedan fuera del veredicto aunque se muestren.
"""
import re, unicodedata

TIPO_TXT = {
    'ponencia': 'Informe de ponencia', 'articulado': 'Articulado',
    'titulo': 'Título y pregunta', 'conciliacion': 'Conciliación',
    'aplazamiento': 'Proposición de aplazamiento', 'archivo': 'Archivo / ponencia negativa',
    'eliminacion': 'Proposición de eliminación', 'no_avalada': 'Proposición no avalada',
    'sustitutiva': 'Proposición sustitutiva', 'avalada': 'Proposición avalada',
    'impedimento': 'Impedimento', 'orden': 'Orden del día / trámite',
    'objeciones': 'Objeciones presidenciales', 'otro': 'Otra votación',
    'informe': 'Informe (ponencia o conciliación · nombre truncado en el acta)',
    'proposicion': 'Proposición de un congresista (sin aval indicado)',
}
FONDO = {'ponencia', 'articulado', 'titulo', 'conciliacion', 'aplazamiento', 'archivo'}


def _n(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', s).strip()


_R = [  # (tipo, sentido, regex) — el ORDEN importa: lo más específico primero
    ('impedimento', 0, r'IMPEDIMENT|RECUSACI|\bIMP\.? ?(HR|H\.R|DE|[A-Z]+ [A-Z]+)'),
    ('orden', 0, r'ORDEN DEL DIA|SESION (PERMANENTE|INFORMAL)|SUSPENDID|LEVANTAR|MOCION DE (ORDEN|PROCED)|VERIFICACION DEL QUORUM|CITACION|SUFICIENTE ILU|REAPERTURA|COMISION ACCIDENTAL|FE DE ERRATAS'),
    ('aplazamiento', -1, r'APLAZA'),
    ('archivo', -1, r'ARCHIV|PONENCIA NEGATIVA|NEGATIVA|PON\.? ?NEG'),
    ('conciliacion', +1, r'INF\.? ?DE CONC'),
    ('objeciones', 0, r'INF\.? ?DE OBJ'),
    ('no_avalada', -1, r'NO AVALAD|SIN AVAL'),
    ('eliminacion', -1, r'ELIMINA|SUPRIM|SUPRESI'),
    ('sustitutiva', -1, r'SUSTITUT'),
    ('objeciones', 0, r'OBJECION'),
    ('conciliacion', +1, r'CONCILIA'),
    ('ponencia', +1, r'INFORME DE PONENCIA|PROPOSICION CON (QUE|LA QUE) TERMINA|TERMINA (EL|LA) (INFORME|PONENCIA)|PROP\.? ?(CON QUE|FINAL)|DAR (PRIMER|SEGUNDO) DEBATE|PONENCIA'),
    ('ponencia', +1, r'INF\.? ?(DE )?TERM|INFORME COMO TERMINA|INF\.? ?TER\b'),
    ('titulo', +1, r'TITULO|PREGUNTA'),
    ('avalada', +1, r'AVALAD'),
    ('informe', +1, r'^INFORME( DE)?$'),
    ('proposicion', 0, r'^PROPOSICION(ES)?( DE| NO)?$|PROP(OSICION(ES)?|\.)? ?(HR|H\.R)|ART(ICULO)?\.? ?NUEVO|MODIFICAT'),
    ('articulado', +1, r'ARTICULADO|ARTICULO|\bARTS?\.?\b|BLOQ|COMO VIENE|ENMIENDA|TEXTO'),
]
_RC = [(t, s, re.compile(rx)) for t, s, rx in _R]


def nombre_corto(nombre, archivo=None):
    """Lo que se votó, sin la cabecera «PL.312/24 REFORMA A LA SALUD - »."""
    txt = _n(nombre) or _n(archivo)
    return _cola(re.sub(r'\.PDF$', '', txt))[:70]


def _cola(txt):
    """Quita la cabecera del proyecto. El separador viene como « - », «- » o
    «–» y a veces pegado al título («SALUD- IMPEDIMENTOS»); se toma la ÚLTIMA
    aparición de guion+espacio, que es donde arranca lo que se votó."""
    m = list(re.finditer(r'[-–]\s+', txt))
    if m:
        c = txt[m[-1].end():].strip(' -–')
        if len(c) >= 4:
            return c
    return re.sub(r'^P\.?A?\.?L\.?[EO]?\.?\s*\d+\s*[-/]\s*\d+\s*C?\s*', '', txt).strip(' -–')


def clasificar(nombre, archivo=None):
    """Devuelve (tipo, sentido). Si `nombre` viene vacío (OCR) usa `archivo`."""
    txt = _n(nombre) or _n(archivo)
    # quitar la cabecera "PL.312/24 REFORMA A LA SALUD - " para no leer el título
    # del proyecto como si fuera la votación (un proyecto sobre «eliminación de
    # trámites» no es una proposición de eliminación)
    cola = _cola(txt)
    for t, s, rx in _RC:
        if rx.search(cola):
            return t, s
    for t, s, rx in _RC:   # segunda pasada sobre el texto entero (sin guion)
        if rx.search(txt):
            return t, s
    return 'otro', 0


def posicion(votos):
    """votos = iterable de (respuesta, tipo, sentido) de UNA persona en UN
    proyecto → dict con pro/contra/proc/fondo y la etiqueta de posición."""
    pro = contra = abst = proc = 0
    fpro = fcontra = 0
    for r, t, s in votos:
        if s == 0:
            proc += 1; continue
        if r == 'Abstencion':
            abst += 1; continue
        apoya = (r == 'Si') == (s > 0)
        if apoya: pro += 1
        else: contra += 1
        if t in FONDO:
            if apoya: fpro += 1
            else: fcontra += 1
    nf = fpro + fcontra
    if nf == 0:
        lab = 'sin_fondo'
    elif fpro >= 0.8 * nf:
        lab = 'a_favor'
    elif fcontra >= 0.8 * nf:
        lab = 'en_contra'
    else:
        lab = 'dividido'
    return {'pro': pro, 'contra': contra, 'abst': abst, 'proc': proc,
            'fondo_pro': fpro, 'fondo_contra': fcontra, 'pos': lab}


if __name__ == '__main__':
    import json, collections, sys
    from pathlib import Path
    DIST = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'leyes-senado' / 'dist'
    c = collections.Counter(); ej = collections.defaultdict(set)
    for fn in ('votaciones-camara-nominal.jsonl', 'votaciones-camara-nominal-ocr.jsonl'):
        for l in open(DIST / fn):
            r = json.loads(l)
            if not r.get('proyecto_numero_camara'): continue
            t, s = clasificar(r.get('votacion_nombre'), r.get('archivo'))
            c[t] += 1
            if len(ej[t]) < 6: ej[t].add((r.get('votacion_nombre') or r.get('archivo'))[:80])
    tot = sum(c.values())
    for t, n in c.most_common():
        print(f'{n:7d} {100*n/tot:5.1f}%  {t}')
        for e in sorted(ej[t]): print('           ', e)
