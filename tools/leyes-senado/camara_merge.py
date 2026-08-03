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

LO QUE EL LISTADO DE CÁMARA NO TRAE — y de dónde sale ahora
-----------------------------------------------------------
El listado AJAX no trae fecha de radicación ni fechas de debate. Eso hacía que
los 4.080 proyectos de Cámara entraran al dataset con fecha_presentacion=None, y
por eso el embudo se calculaba solo sobre el Senado.

Desde jul-2026 esas fechas SÍ entran: harvest_camara_fichas.py cosecha la ficha
individual (GET /{link_web}) y deja fichas.jsonl, que este módulo lee y vuelca
sobre el registro crudo — fecha de radicación, fechas de aprobación por debate,
comisión y las gacetas del trámite. Ver `cargar_fichas` y `_aplicar_ficha`.

Lo que sigue SIN venir de ninguna fuente, y por tanto NO se inventa:
  · la CAUSA del archivo. Se buscó en fichas archivadas de 2015, 2019, 2023 y
    2025: la ficha dice "Archivado" y nada más. Así que sus archivados caen en
    ARCHIVADO_OTRO y nunca en ARCHIVADO_TIEMPO (art. 190). Eso no es "no murió
    por tiempo": es "la fuente no lo informa", y stats.json lo expone aparte
    (archivado_causa_no_informada). Derivarlo de las fechas sería estimarlo.
  · la fecha de los proyectos cuya ficha no responde o no la trae — quedan en
    None y se cuentan aparte, nunca se rellenan.
"""
import json
import re
import unicodedata
from pathlib import Path

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


# ------------------------------------------------- ficha individual (fechas)
FICHAS_JSONL = (Path(__file__).resolve().parents[2] /
                'Bases de datos' / 'leyes-senado' / 'camara' / 'fichas.jsonl')


def cargar_fichas(path=None):
    """link_web → ficha parseada (harvest_camara_fichas.py). {} si no se ha
    cosechado: el dataset sale como antes, sin fechas de Cámara."""
    p = Path(path) if path else FICHAS_JSONL
    if not p.exists():
        return {}
    out = {}
    for line in p.open(encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            out[r['link_web']] = r
    return out


# El nombre del acordeón de la ficha → el campo de fecha del shape crudo del
# Senado. Ojo: "Primer Debate X" es el de COMISIÓN y "Segundo Debate X" el de
# PLENARIA de esa misma cámara; el orden real del trámite depende del origen
# (un proyecto de Cámara debate primero allá), y por eso etapa_max se calcula
# contando debates y no por la posición del campo. Ver build_dataset.
_DEBATE_A_CAMPO = {
    'primer debate camara': 'fecha_de_aprobacion_primer_debate_camara',
    'segundo debate camara': 'fecha_de_aprobacion_segundo_debate_camara',
    'primer debate senado': 'fecha_de_aprobacion_primer_debate',
    'segundo debate senado': 'fecha_de_aprobacion_segundo_debate',
}
# orden real del trámite de un proyecto de origen Cámara: comisión y plenaria de
# Cámara primero, luego Senado. Lo usa _evidencia_aprobacion para saber cuál es
# "el debate siguiente".
_ORDEN_DEBATE = {'primer debate camara': 0, 'segundo debate camara': 1,
                 'primer debate senado': 2, 'segundo debate senado': 3}

_DEBATE_A_PONENTE = {
    'primer debate camara': 'ponente_primer_debate_camara',
    'segundo debate camara': 'ponente_segundo_debate_camara',
    'primer debate senado': 'ponente_primer_debate',
    'segundo debate senado': 'ponente_segundo_debate',
}
# la publicación de la ponencia de ese debate → campo de gaceta que lee
# build_dataset.extract_gacetas
_DEBATE_A_GACETA = {
    'primer debate camara': 'primera_ponencia',
    'primer debate senado': 'primera_ponencia',
    'segundo debate camara': 'segunda_ponencia',
    'segundo debate senado': 'segunda_ponencia',
}


def _fecha_aprobacion(pubs):
    """Fecha de APROBACIÓN del debate, solo si la ficha la declara como tal.

    Distingue cosas que conviven en la misma lista y que es fácil confundir:
      · "Acta y Fecha de aprobación Comisión Acta 20 del 4 de junio de 2014" ✓
      · "ACTA DE PLENARIA 66 DEL 10 DE JUNIO DE 2015"                        ✓
      · "ACTA DE COMISIÓN 013 DEL 10 DE JUNIO DE 2015"                       ✓
      · "...(anuncio)..." y "Ponencia Primer Debate Mayo 20 2014"            ✗
    El anuncio es la sesión PREVIA (art. 8 del acto legislativo 01/2003) y la
    ponencia es el documento, no la votación. Contar cualquiera de esos dos como
    aprobación inflaría el embudo justo en el escalón que más importa."""
    for p in pubs:
        txt = _sin_tildes(p.get('texto') or '').lower()
        if not p.get('fecha') or 'anuncio' in txt:
            continue
        if ('aprobacion' in txt or 'acta de plenaria' in txt
                or 'acta de comision' in txt):
            return p['fecha']
    return None


def _evidencia_aprobacion(debates):
    """¿Qué debates aprobó el proyecto, y con qué respaldo?

    La fecha del acta es el respaldo ideal, pero la ficha la publica en pocos
    casos: de 4.080 fichas, solo 85 debates traen fecha de aprobación fechada,
    mientras 589 traen el texto aprobado y 471 más tienen ponencia del debate
    SIGUIENTE. Quedarse solo con la fecha daba 98,3% de muertes antes del primer
    debate en Cámara — implausible al lado del 58,9% del Senado, y falso: era el
    parser, no el Congreso.

    Así que el HITO (¿aprobó?) y la FECHA (¿cuándo?) se separan. El hito admite
    tres respaldos, y cada debate guarda cuál lo sostiene para que nadie tenga
    que confiar a ciegas:
      · fecha_acta          el acta de aprobación, con su fecha        (el mejor)
      · texto_aprobado      "Texto Definitivo/Aprobado en Comisión"    (documental)
      · ponencia_siguiente  hay ponencia del debate siguiente          (inferencia)
    La tercera es inferencia procedimental, no dato: no existe ponencia para
    segundo debate sin que el primero se haya aprobado. Es sólida, pero por eso
    va etiquetada y se reporta aparte en stats.json.

    Devuelve {nombre_debate: evidencia}."""
    ev, presentes = {}, []
    for db in debates or []:
        nombre = _sin_tildes(db.get('nombre') or '').lower().strip()
        if nombre not in _DEBATE_A_CAMPO:
            continue
        presentes.append(nombre)
        marca = None
        for p in db.get('publicaciones') or []:
            txt = _sin_tildes(p.get('texto') or '').lower()
            if 'anuncio' in txt:
                continue
            if p.get('fecha') and ('aprobacion' in txt or 'acta de plenaria' in txt
                                   or 'acta de comision' in txt):
                marca = 'fecha_acta'
                break
            if ('texto definitivo' in txt or 'texto aprobado' in txt
                    or 'aprobado en comision' in txt):
                marca = marca or 'texto_aprobado'
        ev[nombre] = marca

    # ponencia del debate siguiente ⇒ el anterior se aprobó
    tiene_ponencia = {
        _sin_tildes(db.get('nombre') or '').lower().strip():
            any('ponencia' in _sin_tildes(p.get('texto') or '').lower()
                for p in db.get('publicaciones') or [])
        for db in debates or []}
    orden = sorted(presentes, key=lambda n: _ORDEN_DEBATE[n])
    for i, n in enumerate(orden[:-1]):
        if ev.get(n) is None and tiene_ponencia.get(orden[i + 1]):
            ev[n] = 'ponencia_siguiente'
    return {n: e for n, e in ev.items() if e}


def _aplicar_ficha(rec, ficha):
    """Vuelca sobre el registro crudo lo que la ficha aporta. No pisa nada que
    ya venga con valor: el listado y la ficha coinciden, pero si difirieran, lo
    que ya estaba manda."""
    if not ficha:
        return rec
    rec['_ficha_ok'] = True
    if ficha.get('fecha_radicacion_camara'):
        rec['fecha_de_presentacion'] = ficha['fecha_radicacion_camara']
    if ficha.get('fecha_radicacion_senado'):
        rec['_fecha_radicacion_senado'] = ficha['fecha_radicacion_senado']
    if ficha.get('comision') and not rec.get('comision'):
        rec['comision'] = ficha['comision']
    if ficha.get('pdf_url'):
        # texto del radicado, un PDF por proyecto (no un boletín). Sin cosechar
        # todavía — anotado para el harvest de texto de Cámara.
        rec['_pdf_radicado_url'] = ficha['pdf_url']
    if ficha.get('gaceta_radicacion'):
        rec['exposicion_de_motivos'] = f"Gaceta {ficha['gaceta_radicacion']}"
    if ficha.get('gaceta_radicacion_deep'):
        rec['_gaceta_radicacion_deep'] = ficha['gaceta_radicacion_deep']

    n_fechas = 0
    for db in ficha.get('debates') or []:
        nombre = _sin_tildes(db.get('nombre') or '').lower().strip()
        campo = _DEBATE_A_CAMPO.get(nombre)
        if not campo:
            continue
        f = _fecha_aprobacion(db.get('publicaciones') or [])
        if f:
            rec[campo] = f
            n_fechas += 1
        if db.get('ponentes'):
            rec[_DEBATE_A_PONENTE[nombre]] = ', '.join(db['ponentes'])
        gac = next((p['gaceta'] for p in db.get('publicaciones') or []
                    if p.get('gaceta') and 'ponencia' in _sin_tildes(p.get('texto') or '').lower()),
                   None)
        if gac:
            rec[_DEBATE_A_GACETA[nombre]] = f'Gaceta {gac}'

    # HITO vs FECHA (ver _evidencia_aprobacion): el embudo cuenta debates
    # aprobados con cualquiera de los tres respaldos; los días al primer debate
    # solo pueden usar los que además traen fecha.
    ev = _evidencia_aprobacion(ficha.get('debates'))
    rec['_debates_evidencia'] = ev
    rec['_n_debates_ficha'] = len(ev)
    rec['_n_debates_fechados'] = n_fechas
    return rec


# ------------------------------------------------------------------ merge
ID_BASE = 900000  # los ids del Senado llegan a ~10.100 (pdly) y ~820 (pal)


def _a_raw(it, nid, ficha=None):
    """Item del listado de Cámara → el shape crudo que espera enrich_pdly/pal,
    enriquecido con la ficha individual si se cosechó."""
    estado_txt, etapa = _ETAPA_POR_ESTADO.get(it.get('estado') or '', ('', 0))
    leg = it.get('legislatura', '')
    rec = {
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
        '_ficha_ok': False,
    }
    # llave del texto del radicado, cuando el cron diario ya lo bajó
    for k in ('_texto_s3', '_texto_local'):
        if it.get(k):
            rec[k] = it[k]
    return _aplicar_ficha(rec, ficha)


def merge(raw_pdly, raw_pal, camara_rows, fichas=None):
    """Devuelve (extra_pdly, extra_pal, info) con los de Cámara que faltaban.

    Solo entran los de ORIGEN Cámara que no estén ya en el registro del Senado.
    Los de origen Senado del listado de Cámara se descartan siempre: son los
    mismos que el Senado ya reporta (y son justo los que producen el doble
    conteo si uno suma los dos registros a lo bobo).

    `fichas` es el dict de cargar_fichas() — con él los registros salen con
    fecha de radicación y fechas de debate; sin él, como antes de jul-2026.
    """
    fichas = fichas or {}
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
        destino.append(_a_raw(it, ID_BASE + len(destino),
                              fichas.get(it.get('link_web') or '')))

    todos = extra_pdly + extra_pal
    info = {'n_camara_leidos': len(camara_rows),
            'n_agregados_pdly': len(extra_pdly),
            'n_agregados_pal': len(extra_pal),
            'n_con_ficha': sum(1 for r in todos if r.get('_ficha_ok')),
            'n_con_fecha': sum(1 for r in todos if r.get('fecha_de_presentacion')),
            'n_sin_fecha': sum(1 for r in todos if not r.get('fecha_de_presentacion')),
            **desc}
    return extra_pdly, extra_pal, info
