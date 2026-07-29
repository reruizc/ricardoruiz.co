#!/usr/bin/env python3
"""
Une el registro de la CÁMARA (harvest_camara_historico.py) al del SENADO
(harvest.py) sin doble contar, para que build_dataset.py produzca el universo
real de proyectos radicados y no solo la mitad senatorial.

EL PROBLEMA QUE RESUELVE
------------------------
Un proyecto que cruza de cámara tiene DOS números de radicado — p.ej. el mismo
proyecto es 425/2023C en Cámara y 195/2022S en Senado — y por tanto una ficha en
CADA registro. De ahí que:

  suma bruta de los dos registros   3.447  (cuatrienio 2022-2026) ← doble cuenta
  unión deduplicada                 2.798  ← lo real
  solo el registro del Senado       1.496  ← lo que Caudal tenía

La unión correcta NO es una intersección difusa: es
    proyectos de origen Senado  (los trae completos el registro del Senado)
  + proyectos de origen Cámara  (los trae completos el registro de Cámara)
porque todo proyecto aparece siempre en el registro de su cámara de origen.
Aquí se implementa así: se agregan los de Cámara que NO estén ya en el registro
del Senado, cruzando por número+año (`_key`).

Verificado (jul-2026): de los 1.651 proyectos de origen Cámara del cuatrienio
2022-2026, 404 ya estaban en el registro del Senado (cruzaron) y 1.247 no
(murieron en Cámara). De esos 1.247, CERO llegaron a ser ley — coherente, porque
ninguna ley se sanciona sin pasar por el Senado. O sea: el histórico de leyes
nunca estuvo incompleto; lo que faltaba era el cementerio de Cámara, que es
justo donde vive el análisis de mortandad y de bloqueo.

LO QUE EL LISTADO DE CÁMARA NO TRAE
-----------------------------------
Ni fecha de radicación ni fechas de debate (viven en la ficha individual, un GET
por proyecto). Consecuencias, asumidas y marcadas en el dato:
  · fecha_presentacion = None  → sin dias_a_primer_debate
  · la etapa se INFIERE del estado textual (_ETAPA_POR_ESTADO), no de fechas
  · Cámara no dice la CAUSA del archivo → 'Archivado' cae en ARCHIVADO_OTRO y
    nunca en ARCHIVADO_TIEMPO (art. 190). No confundir eso con "no murió por
    tiempo": es "la fuente no lo informa". stats.json lo separa por registro.
"""
import re
import unicodedata

# ---------------------------------------------------------------- llave de cruce
_NUM = re.compile(r'\s*(\d{1,4})\s*[/-]\s*(\d{2,4})')


def _key(numero, camara):
    """'425/2023C' | '195/22' → 'C425-23' | 'S195-22'. None si no hay número."""
    m = _NUM.match(numero or '')
    if not m:
        return None
    return f"{'C' if camara else 'S'}{int(m.group(1))}-{m.group(2)[-2:]}"


# ------------------------------------------- verificación por título del match
# ⚠ EL NÚMERO DE RADICADO NO ES IDENTIFICADOR ÚNICO. Las dos cámaras reinician
# su numeración cada legislatura, pero el número lleva el AÑO CALENDARIO — así
# que "511/2025C" existe DOS veces (legislatura 2024-2025, radicado ene-jun 2025,
# y legislatura 2025-2026, radicado jul-dic 2025) y son proyectos distintos.
# Medido: 387 números de Cámara se repiten en su propio registro, y 276 valores
# de `numero_camara` se repiten dentro del registro del Senado.
#
# Por eso la dedup NO puede ser por número solo: cruza por número Y exige que los
# títulos se parezcan. Sin el chequeo de título, 238 cruces salían mal — y 190 de
# ellos borraban proyectos que Cámara reporta como nunca cruzados al Senado.
# Como ambos registros copian el título del radicado, los del MISMO proyecto se
# parecen mucho (el 86% pasa de 0.6), así que el umbral no es delicado.
_SIM_MIN = 0.45

_STOPWORDS = {
    'MEDIO', 'CUAL', 'CUALES', 'DICTAN', 'OTRAS', 'DISPOSICIONES', 'MODIFICA',
    'ADICIONA', 'ESTABLECEN', 'ESTABLECE', 'NORMAS', 'PROYECTO', 'CONGRESO',
    'REPUBLICA', 'COLOMBIA', 'NACION', 'NACIONAL', 'DEMAS', 'PARA', 'SOBRE',
}


def _tokens(t):
    plano = ''.join(c for c in unicodedata.normalize('NFD', t or '')
                    if unicodedata.category(c) != 'Mn').upper()
    return {w for w in re.findall(r'[A-Z0-9]+', plano) if len(w) > 3} - _STOPWORDS


def _similares(a, b):
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= _SIM_MIN


def _indice_senado(raw_pdly, raw_pal):
    """(por nº de Senado, por nº de Cámara) → lista de registros, porque el
    número se repite (ver nota de arriba) y hay que desempatar por título."""
    por_s, por_c = {}, {}
    for r in raw_pdly + raw_pal:
        k = _key(r.get('numero_senado'), False)
        if k:
            por_s.setdefault(k, []).append(r)
        k = _key(r.get('numero_camara'), True)
        if k:
            por_c.setdefault(k, []).append(r)
    return por_s, por_c


def _ya_en_senado(it, por_s, por_c):
    """¿Este item de Cámara es un proyecto que el registro del Senado ya tiene?

    Cruza por cualquiera de los dos números Y exige título parecido. Un item sin
    número de Senado normalmente ni cruzó — pero igual se chequea contra el nº de
    Cámara, porque hay casos en que Cámara no registró el número del Senado y el
    proyecto sí había cruzado."""
    titulo = it.get('titulo')
    for k, idx in ((_key(it.get('nro_senado'), False), por_s),
                   (_key(it.get('nro_camara'), True), por_c)):
        if k and any(_similares(titulo, r.get('titulo')) for r in idx.get(k, ())):
            return True
    return False


# ------------------------------------------------------------- mapeos de campos
# estado de Cámara → (texto tipo-Senado para norm_resultado, etapa inferida)
# La etapa es "cuántos debates alcanzó" en la misma escala 0-5 de ETAPAS
# (0 radicado … 4 cuarto debate/trámite final, 5 ley).
_ETAPA_POR_ESTADO = {
    'Ley':                              ('LEY', 5),
    'Acto Legislativo':                 ('ACTO LEGISLATIVO', 5),
    'Sanción Presidencial':             ('SANCIÓN PRESIDENCIAL', 4),
    'Revisión corte constitucional':    ('CORTE CONSTITUCIONAL', 4),
    'Trámite objeciones presidenciales': ('OBJETADO', 4),
    'Trámite conciliación':             ('CONCILIACIÓN', 4),
    'Trámite en Senado':                ('PENDIENTE TRAMITE EN SENADO', 2),
    'Trámite en Plenaria':              ('PENDIENTE TRAMITE EN PLENARIA', 1),
    'Debate de Plenaria':               ('PENDIENTE DEBATE EN PLENARIA', 1),
    'Pendiente ponencia segundo debate': ('PENDIENTE PONENCIA SEGUNDO DEBATE', 1),
    'Trámite en Comisión':              ('PENDIENTE TRAMITE EN COMISION', 0),
    'Debate de Comisión':               ('PENDIENTE DEBATE EN COMISION', 0),
    'Pendiente ponencia primer debate': ('PENDIENTE PONENCIA PRIMER DEBATE', 0),
    'Pendiente por designar ponentes':  ('PENDIENTE DESIGNAR PONENTES', 0),
    'Solicitud de Audiencia Pública':   ('PENDIENTE AUDIENCIA PUBLICA', 0),
    'Archivado':                        ('ARCHIVADO', 0),
    'Retirado':                         ('RETIRADO POR EL AUTOR', 0),
    'Acumulado':                        ('ACUMULADO', 0),
    'Otro':                             ('', 0),
}

_TIPO = {'Ley Ordinaria': 'ORDINARIA', 'Ley Estatutaria': 'ESTATUTARIA',
         'Ley Orgánica': 'ORGÁNICA', 'Acto Legislativo': ''}

_ORDINALES = ('Primera', 'Segunda', 'Tercera', 'Cuarta', 'Quinta', 'Sexta', 'Séptima')


def _sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn')


def _comision(pack):
    """'1||Comisión Primera Constitucional Permanente||url' → 'Primera'
    (el vocabulario que usa el registro del Senado, para no fragmentar stats)."""
    nombre = ''
    for chunk in (pack or '').split('::'):
        partes = chunk.split('||')
        if len(partes) >= 2 and partes[1].strip():
            nombre = partes[1]
            break
    plano = _sin_tildes(nombre).lower()
    for o in _ORDINALES:
        if _sin_tildes(o).lower() in plano:
            return o
    return ''


def _autores(pack, otros):
    """autores_pack + otros_autores → cadena tipo campo `autor` del Senado.

    ⚠ El separador entre autores es '::', NO ';;'. (harvest_camara.py asumía ';;'
    en su _unpack y por eso se comía los coautores.)"""
    nombres = []
    for chunk in (pack or '').split('::'):
        partes = chunk.split('||')
        if len(partes) >= 2 and partes[1].strip():
            nombres.append(partes[1].strip())
    extra = (otros or '').strip()
    if extra:
        nombres.append(extra)
    # dedup preservando orden
    visto = set()
    return ', '.join(n for n in nombres if not (n in visto or visto.add(n)))


def _cuatrienio(leg):
    """'2023-2024' → '2022-2026' (los cuatrienios arrancan en 1990 + 4k)."""
    if not leg[:4].isdigit():
        return ''
    y = int(leg[:4])
    ini = 1990 + 4 * ((y - 1990) // 4)
    return f'{ini}-{ini + 4}'


# ------------------------------------------------------------------ merge
ID_BASE = 900000  # los ids del Senado llegan a ~10.100 (pdly) y ~820 (pal)


def _a_raw(it, nid):
    """Item del listado de Cámara → el shape crudo que espera enrich_pdly/pal."""
    estado_txt, etapa = _ETAPA_POR_ESTADO.get(it.get('estado') or '', ('', 0))
    leg = it.get('legislatura', '')
    return {
        'id': nid,
        'titulo': it.get('titulo') or '',
        'numero_senado': (it.get('nro_senado') or '').replace('S', '').strip(),
        'numero_camara': (it.get('nro_camara') or '').replace('C', '').strip(),
        'legislatura': leg,
        'cuatrenio': _cuatrienio(leg),          # sic: el crudo del Senado trae este typo
        'origen': 'CÁMARA DE REPRESENTANTES',
        'tipo_de_ley': _TIPO.get(it.get('tipo') or '', ''),
        'comision': _comision(it.get('comisiones_pack')),
        'autor': _autores(it.get('autores_pack'), it.get('otros_autores')),
        'estado': estado_txt,
        '_origen_registro': 'camara',
        '_etapa_hint': etapa,
        '_link_web': it.get('link_web') or '',
    }


def merge(raw_pdly, raw_pal, camara_rows):
    """Devuelve (extra_pdly, extra_pal, info) con los de Cámara que faltaban.

    Solo entran los de ORIGEN Cámara que no estén ya en el registro del Senado.
    Los de origen Senado del listado de Cámara se descartan siempre: son los
    mismos que el Senado ya reporta (y son justo los que producen el doble
    conteo si uno suma los dos registros a lo bobo).
    """
    por_s, por_c = _indice_senado(raw_pdly, raw_pal)
    extra_pdly, extra_pal = [], []
    desc = {'origen_senado': 0, 'ya_en_senado': 0, 'sin_numero': 0}

    for it in camara_rows:
        # El campo `origen` de Cámara no es de fiar (se le miden etiquetas
        # erradas), pero da igual: la dedup por número decide, y este filtro solo
        # evita meter dos veces lo que el Senado ya reporta como suyo.
        if (it.get('origen') or '') != 'Cámara':
            desc['origen_senado'] += 1
            continue
        if _key(it.get('nro_camara'), True) is None and _key(it.get('nro_senado'), False) is None:
            desc['sin_numero'] += 1
            continue
        if _ya_en_senado(it, por_s, por_c):
            desc['ya_en_senado'] += 1
            continue
        destino = extra_pal if (it.get('tipo') == 'Acto Legislativo') else extra_pdly
        destino.append(_a_raw(it, ID_BASE + len(destino)))

    info = {'n_camara_leidos': len(camara_rows),
            'n_agregados_pdly': len(extra_pdly),
            'n_agregados_pal': len(extra_pal),
            **desc}
    return extra_pdly, extra_pal, info
