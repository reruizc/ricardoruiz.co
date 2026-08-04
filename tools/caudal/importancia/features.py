#!/usr/bin/env python3
"""
Caudal · Importancia — extracción de features del EJE 1 (¿va a avanzar?).

REGLA DURA DE ESTE ARCHIVO: aquí solo entra lo que se sabe EN EL MOMENTO EN QUE
LA ALERTA SE DISPARA (la radicación). Nada de desenlace.

Prohibido como insumo (son la etiqueta, no la evidencia):
  resultado · es_ley · etapa_max · n_debates_aprobados · estado ·
  fecha_primer_debate · dias_a_primer_debate · ponentes · gacetas ·
  murio_por_tiempo · texto_s3

Prohibido además, aunque no lo parezca:
  · veces_presentado / empuje / vitrina_score / max_etapa_cluster
      Los calcula clasificar.py sobre el cluster COMPLETO, incluyendo
      radicaciones FUTURAS y la etapa máxima de todas ellas. Un proyecto de
      2014 "sabe" que en 2022 lo volvieron a radicar. Aquí se reconstruyen
      desde historial_reradicacion filtrando por anio < anio del registro.
  · origen_registro
      'camara' significa "no cruzó a Senado", porque los que cruzan quedan
      deduplicados bajo el registro del Senado. Su tasa de ley es 0,7% contra
      24,9% del Senado: eso NO es el Congreso, es nuestro pipeline. Meterlo
      como feature regala un AUC alto y falso.
  · origen  (la cámara donde nació)
      Parece inocente — se sabe al radicar — pero DENTRO del registro del
      Senado un proyecto con origen 'Cámara de Representantes' es un proyecto
      que YA CRUZÓ de cámara, o sea que ya aprobó los dos primeros debates:
      46,6% de leyes contra 18,6%, etapa máxima media 3,69 contra 1,33. Es
      desenlace disfrazado de metadato. Medido y descartado.
  · 'no tiene comisión asignada'
      Los 114 casos del registro del Senado sin comisión son fichas viejas o
      incompletas (99 ni siquiera tienen año) y ninguno llegó a ley. Eso es el
      scraper, no el Congreso — y en la legislatura viva los 75 sin comisión
      son de Cámara, cuyo listado simplemente no publica ese campo. Convertirlo
      en feature hundiría a todos los proyectos de Cámara por un artefacto. La
      ausencia se trata como dato faltante (todas las com_* en cero), no como
      señal.

Lo que sí entra: quién radica, en qué comisión, de qué tipo es, cuántos firman,
cuándo dentro del cuatrienio, y qué le pasó a los intentos ANTERIORES de la
misma iniciativa.
"""
import re
import unicodedata

# ---------------------------------------------------------------------------
# normalización
# ---------------------------------------------------------------------------


def _n(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s.lower()).strip()


# el registro escribe la misma comisión de cuatro formas ("SEPTIMA", "Séptima",
# "ECÓNOMICAS"). Sin plegar, el one-hot se parte y cada variante aprende su
# propio peso con n minúsculo.
COMISIONES = ['primera', 'segunda', 'tercera', 'cuarta', 'quinta', 'sexta',
              'septima', 'economicas']


def comision_norm(c):
    c = _n(c).replace('comision', '').strip()
    if not c or c == '-':
        return 'sin_comision'
    for k in COMISIONES:
        if c.startswith(k[:5]):
            return k
    if 'econom' in c:
        return 'economicas'
    return 'otra'


# Entidades de control: radican con iniciativa propia y su trámite no se parece
# al del Gobierno ni al de un congresista.
_ENTIDAD_CONTROL = ('fiscal', 'procuradur', 'defensor', 'contralor',
                    'consejo nacional electoral', 'consejo de estado',
                    'corte', 'judicatura')

# Ley aprobatoria de tratado: trámite casi automático (la Comisión Segunda las
# despacha en bloque). Es la feature más potente y la más legítima — se sabe con
# solo leer el título, y no es un atajo al desenlace.
_TRATADO = re.compile(
    r'\b(se aprueba|aprobatoria)\b.{0,80}\b(acuerdo|convenio|tratado|protocolo|'
    r'memorando de entendimiento|canje de notas|enmienda)\b|'
    r'\b(acuerdo|convenio|tratado|protocolo)\b.{0,60}\bsuscrito\b')

# El título dice que toca una norma viva (más peso institucional que crear una
# figura nueva desde cero).
_TOCA_NORMA = re.compile(
    r'\b(ley \d|decreto[ -]ley|codigo|estatuto|constitucion politica|'
    r'articulo \d|acto legislativo \d)\b')

_ORDEN_PUBLICO = re.compile(
    r'\b(presupuesto general|plan nacional de desarrollo|adiciona el presupuesto|'
    r'rentas y recursos de capital|apropiaciones para la vigencia)\b')


def _mes_legislativo(fecha, legislatura):
    """Meses transcurridos desde el 20 de julio de apertura.

    Radicar en julio da dos legislaturas de reloj; radicar en mayo deja el
    proyecto contra el cierre. Es el mismo argumento del 'año 4 muere más', pero
    dentro del año.
    """
    if not fecha or not legislatura:
        return None
    try:
        y, m, _d = str(fecha)[:10].split('-')
        y, m = int(y), int(m)
        y0 = int(str(legislatura).split('-')[0])
    except Exception:
        return None
    off = (y - y0) * 12 + (m - 7)
    return off if 0 <= off <= 13 else None


def anio_cuatrienio(rec):
    """1..4 dentro del periodo constitucional."""
    c, a = rec.get('cuatrienio'), rec.get('anio')
    if not c or not a:
        return None
    try:
        y0 = int(str(c).split('-')[0])
    except Exception:
        return None
    return min(max(a - y0 + 1, 1), 4)


def antecedentes(rec):
    """Intentos ANTERIORES de la misma iniciativa. Sin fuga: corta por año.

    Devuelve {n_previos, max_etapa_previa (-1 si no hay), previo_fue_ley,
              anios_desde_ultimo}.

    El corte es estricto (anio < anio del registro) y por eso es conservador:
    dos radicaciones del mismo año calendario no se cuentan como antecedente
    porque en ese momento el desenlace de la hermana todavía podía no conocerse.
    """
    a = rec.get('anio') or 0
    prev = [h for h in (rec.get('historial_reradicacion') or [])
            if (h.get('anio') or 0) < a]
    if not prev:
        return {'n_previos': 0, 'max_etapa_previa': -1,
                'previo_fue_ley': False, 'anios_desde_ultimo': None}
    etapas = [h.get('etapa') or 0 for h in prev]
    ult = max(h.get('anio') or 0 for h in prev)
    return {
        'n_previos': len(prev),
        'max_etapa_previa': max(etapas),
        'previo_fue_ley': any((h.get('res') or '') == 'LEY' for h in prev),
        'anios_desde_ultimo': a - ult,
    }


# ---------------------------------------------------------------------------
# vector de features
# ---------------------------------------------------------------------------
# Orden fijo y explícito: es el contrato con el modelo serializado. Agregar una
# feature en medio invalida los pesos guardados — se agregan AL FINAL y se
# re-calibra.
FEATURES = [
    'gobierno',              # el Ejecutivo radica: no es un backbencher
    'entidad_control',
    'es_tratado',
    'es_acto_legislativo',
    'tipo_honores',
    'tipo_fondos',
    'tipo_reforma',
    'tipo_presupuestal',
    'crea_fondo',
    'jala_presupuesto_regional',
    'toca_norma_viva',
    'orden_publico_fiscal',  # presupuesto / PND: trámite obligado
    'com_primera', 'com_segunda', 'com_tercera', 'com_cuarta',
    'com_quinta', 'com_sexta', 'com_septima', 'com_economicas',
    'firmas_1', 'firmas_2_4', 'firmas_5_9', 'firmas_10mas',
    'previos_1', 'previos_2', 'previos_3mas',
    'previo_llego_lejos',    # algún intento anterior pasó de 2º debate
    'previo_fue_ley',
    'anio_c1', 'anio_c2', 'anio_c4',   # c3 = base
    'radica_temprano',       # jul-sep: le queda reloj
    'radica_tarde',          # abr-jun: contra el cierre
    'titulo_largo',
    # trayectoria del firmante ANTES de este proyecto (ver trayectoria_autores)
    'autor_novato',          # sin nada radicado en años anteriores
    'autor_veterano',        # ≥15 proyectos previos: maneja la agenda
    'autor_con_leyes',       # ya le aprobaron al menos una
    'autor_muchas_leyes',    # ≥4: sabe sacar leyes, no solo radicarlas
]


def trayectoria_autores(rows):
    """Índice autor → [(anio, llegó_a_ley)] con TODO el histórico.

    Quién firma no vale igual: un congresista con cuatro leyes aprobadas mueve
    la agenda de otra manera que un novato, y eso se sabe el día que radica.
    El corte temporal lo aplica `_traj()` al consultar, no este índice.
    """
    datos = {}
    for r in rows:
        a = r.get('anio')
        if not a:
            continue
        ley = bool(r.get('es_ley'))
        for k in (r.get('autores_keys') or [])[:3]:   # firmante principal + 2
            datos.setdefault(k, []).append((a, ley))
    for k in datos:
        datos[k].sort()
    return {'tipo': 'serie', 'datos': datos}


def trayectoria_acumulada(idx, corte):
    """Aplana el índice a {autor: [n_proyectos, n_leyes]} contando solo lo
    anterior a `corte`. Es lo que viaja a la Lambda: para puntuar la
    legislatura viva basta el acumulado hasta el año pasado, y así el JSON
    ocupa una fracción de la serie completa."""
    out = {}
    for k, serie in idx['datos'].items():
        prev = [x for x in serie if x[0] < corte]
        if prev:
            out[k] = [len(prev), sum(1 for _, l in prev if l)]
    return {'tipo': 'acum', 'corte': corte, 'datos': out}


def _traj(rec, idx):
    """Proyectos y leyes previas de los firmantes. Corta por año: solo cuenta
    lo que ya había pasado cuando se radicó este."""
    if not idx:
        return None
    ks = (rec.get('autores_keys') or [])[:3]
    if not ks:
        return None
    d = idx['datos']
    if idx['tipo'] == 'acum':
        # el acumulado ya viene cortado; solo vale si el proyecto es posterior
        if (rec.get('anio') or 0) < idx['corte']:
            return None
        n = sum(d[k][0] for k in ks if k in d)
        return {'n': n, 'leyes': sum(d[k][1] for k in ks if k in d)}
    a = rec.get('anio') or 0
    prev = [x for k in ks for x in d.get(k, []) if x[0] < a]
    return {'n': len(prev), 'leyes': sum(1 for _, l in prev if l)}


def vector(rec, autores_idx=None):
    """rec (fila de proyectos.jsonl / actos-legis.jsonl) → lista float.

    `autores_idx` es el índice de trayectoria (opcional). Si no viene, las
    cuatro features del firmante quedan en cero, que es el vector de "no se
    sabe" — no de "es novato".
    """
    tip = rec.get('tipologia') or 'ordinaria'
    com = comision_norm(rec.get('comision'))
    ent = _n(rec.get('entidad'))
    nf = rec.get('n_firmantes') or 0
    ant = antecedentes(rec)
    np_ = ant['n_previos']
    ac = anio_cuatrienio(rec)
    ml = _mes_legislativo(rec.get('fecha_presentacion'), rec.get('legislatura'))
    t = _n(rec.get('titulo'))
    tabla = rec.get('tabla') or 'pdly'
    inst = (rec.get('autor_tipo') == 'institucional')

    f = {
        'gobierno': inst and 'gobierno' in ent,
        'entidad_control': inst and any(k in ent for k in _ENTIDAD_CONTROL),
        'es_tratado': bool(_TRATADO.search(t)),
        'es_acto_legislativo': tabla == 'pal',
        'tipo_honores': tip == 'honores',
        'tipo_fondos': tip == 'fondos',
        'tipo_reforma': tip == 'reforma',
        'tipo_presupuestal': tip == 'presupuestal',
        'crea_fondo': bool(rec.get('crea_fondo')),
        'jala_presupuesto_regional': bool(rec.get('jala_presupuesto_regional')),
        'toca_norma_viva': bool(_TOCA_NORMA.search(t)),
        'orden_publico_fiscal': bool(_ORDEN_PUBLICO.search(t)),
        'firmas_1': nf == 1,
        'firmas_2_4': 2 <= nf <= 4,
        'firmas_5_9': 5 <= nf <= 9,
        'firmas_10mas': nf >= 10,
        'previos_1': np_ == 1,
        'previos_2': np_ == 2,
        'previos_3mas': np_ >= 3,
        'previo_llego_lejos': ant['max_etapa_previa'] >= 3,
        'previo_fue_ley': ant['previo_fue_ley'],
        'anio_c1': ac == 1,
        'anio_c2': ac == 2,
        'anio_c4': ac == 4,
        'radica_temprano': ml is not None and ml <= 2,
        'radica_tarde': ml is not None and ml >= 9,
        'titulo_largo': len(t) > 220,
    }
    tr = _traj(rec, autores_idx)
    if tr is not None:
        f['autor_novato'] = tr['n'] == 0
        f['autor_veterano'] = tr['n'] >= 15
        f['autor_con_leyes'] = tr['leyes'] >= 1
        f['autor_muchas_leyes'] = tr['leyes'] >= 4
    # 'sin_comision' y 'otra' no tienen columna: quedan como el vector cero de
    # este bloque, que es la forma correcta de decir "no se sabe".
    for k in COMISIONES:
        f['com_' + k] = (com == k)
    return [1.0 if f.get(k) else 0.0 for k in FEATURES]


# Cómo se dice cada factor en voz alta: (cuando está, cuando falta). Un cliente
# no lee 'com_tercera'. Y la forma negativa importa tanto como la positiva —
# "no lo radica el Gobierno" explica de verdad por qué algo no se mueve.
GLOSA = {
    'gobierno': ('lo radica el Gobierno Nacional', 'no es iniciativa del Gobierno'),
    'entidad_control': ('lo radica un órgano de control', None),
    'es_tratado': ('es ley aprobatoria de un tratado (trámite expedito)', None),
    'es_acto_legislativo': ('es acto legislativo: ocho debates en un solo año', None),
    'tipo_honores': ('es honores o conmemoración, de trámite liviano', None),
    'tipo_fondos': ('crea un fondo', None),
    'tipo_reforma': ('es una reforma de fondo', None),
    'tipo_presupuestal': ('mueve apropiaciones', None),
    'crea_fondo': ('crea un fondo con recursos', None),
    'jala_presupuesto_regional': ('arrastra recursos a una región', None),
    'toca_norma_viva': ('modifica una norma vigente, no crea una figura nueva', None),
    'orden_publico_fiscal': ('es presupuesto o plan de desarrollo: trámite obligado', None),
    'com_primera': ('está en Primera, la comisión más congestionada', None),
    'com_segunda': ('está en Segunda, que despacha tratados en bloque', None),
    'com_tercera': ('está en Tercera (hacienda), de alta tasa de aprobación', None),
    'com_cuarta': ('está en Cuarta (presupuesto)', None),
    'com_quinta': ('está en Quinta (ambiente y minas)', None),
    'com_sexta': ('está en Sexta, de baja tasa de aprobación', None),
    'com_septima': ('está en Séptima (salud y trabajo)', None),
    'com_economicas': ('va a comisiones económicas conjuntas', None),
    'firmas_1': ('lo firma una sola persona', None),
    'firmas_2_4': ('lo firman entre dos y cuatro', None),
    'firmas_5_9': ('lo firman entre cinco y nueve', None),
    'firmas_10mas': ('lo firman diez o más', None),
    'previos_1': ('ya se había radicado una vez', None),
    'previos_2': ('ya se había radicado dos veces', None),
    'previos_3mas': ('ya se había radicado tres veces o más', None),
    'previo_llego_lejos': ('un intento anterior pasó del segundo debate', None),
    'previo_fue_ley': ('una versión anterior llegó a ser ley', None),
    'anio_c1': ('primer año del cuatrienio, con reloj de sobra', None),
    'anio_c2': ('segundo año del cuatrienio', None),
    'anio_c4': ('último año del cuatrienio, donde más proyectos mueren', None),
    'radica_temprano': ('radicado al abrir la legislatura', None),
    'radica_tarde': ('radicado contra el cierre de la legislatura', None),
    'titulo_largo': ('título largo, señal de proyecto extenso', None),
    'autor_novato': ('lo firma alguien sin proyectos previos', None),
    'autor_veterano': ('lo firma alguien que radica mucho (y por eso le aprueban '
                       'una fracción menor)', None),
    'autor_con_leyes': ('el firmante ya tiene leyes aprobadas', None),
    'autor_muchas_leyes': ('el firmante tiene cuatro o más leyes aprobadas',
                           'al firmante nunca le han aprobado cuatro leyes'),
}


def glosa(factor, presente):
    """None cuando la ausencia no se puede decir en voz alta sin sonar raro.

    'no lo radica el Gobierno' explica algo; 'no lo firma una sola persona' no
    dice nada útil, así que ese factor se omite en vez de rellenar con ruido.
    """
    g = GLOSA.get(factor)
    if not g:
        return factor if presente else None
    return g[0] if presente else g[1]


def referencia(recs, autores_idx=None):
    """Media de features del conjunto contra el que se compara.

    Sin esto la explicación compara contra los 36 años de histórico y termina
    diciendo lo mismo en todas las señales — "el firmante es veterano" cuando
    en la legislatura viva casi todos lo son. Lo que hay que responder es por
    qué ESTE proyecto y no los otros 213 de al lado.
    """
    if not recs:
        return None
    V = [vector(r, autores_idx) for r in recs]
    n = len(V)
    return [sum(v[j] for v in V) / n for j in range(len(FEATURES))]


def explicacion(rec, modelo, autores_idx=None, k=4, ref=None):
    """Los k factores que más SEPARAN a este proyecto de sus pares.

    `ref` es la media del conjunto comparado (ver `referencia`). Si no viene,
    se cae a la media del universo de entrenamiento, que sirve para una ficha
    suelta pero no para explicar un ranking.

    Deliberadamente NO devuelve los pesos más grandes: devuelve las
    contribuciones CENTRADAS, w_j·(x_j−μ_j)/σ_j, que es el término real del
    modelo. La diferencia importa. Ordenar por peso crudo hace que el porqué
    sea siempre el mismo, porque las características que comparte casi todo el
    mundo dominan la lista y no explican nada — ese es justo el defecto que
    reportó el motor de alertas ('radicado en la Comisión Séptima' en cada
    señal). Centrando, una característica que tiene el 90% de los proyectos
    aporta poco cuando está presente y MUCHO cuando falta, que es la lectura
    correcta: lo informativo es la desviación, no el nivel.

    Por eso también entran las ausencias: "no lo radica el Gobierno" es una
    explicación legítima de por qué algo no va a avanzar.
    """
    v = vector(rec, autores_idx)
    base = ref if ref is not None else modelo.mu
    contrib = []
    for i, f in enumerate(FEATURES):
        w = modelo.w[i]
        if abs(w) < 1e-6 or modelo.sd[i] <= 0:
            continue
        z = (v[i] - base[i]) / modelo.sd[i]
        contrib.append((f, w * z, bool(v[i])))
    contrib.sort(key=lambda t: -abs(t[1]))
    out = []
    for f, e, p in contrib:
        g = glosa(f, p)
        if not g:
            continue
        out.append({'factor': f, 'dice': g, 'efecto': round(e, 3),
                    'presente': p,
                    'sentido': 'a favor' if e > 0 else 'en contra'})
        if len(out) >= k:
            break
    return out


# ---------------------------------------------------------------------------
# etiqueta y elegibilidad (para calibrar)
# ---------------------------------------------------------------------------
# Desenlaces que NO se pueden usar como etiqueta: el proyecto sigue vivo o el
# registro nunca lo cerró.
_ABIERTO = {'EN_TRAMITE', 'SIN_DATO'}


def etiqueta(rec, legislaturas_vivas):
    """1 = llegó a ley · 0 = no · None = todavía no se sabe (no entrenar con él).

    Un 'EN_TRAMITE' de una legislatura vencida es de facto muerto: el registro
    simplemente no lo cerró (2.479 archivados sin causa informada). Se cuenta
    como 0. Un 'EN_TRAMITE' de la legislatura viva es incógnita y se descarta:
    contarlo como 0 enseñaría que lo reciente nunca pasa.
    """
    if rec.get('es_ley'):
        return 1
    if (rec.get('resultado') in _ABIERTO
            and rec.get('legislatura') in legislaturas_vivas):
        return None
    if rec.get('resultado') == 'SIN_DATO':
        return None
    return 0
