#!/usr/bin/env python3
"""
Caudal · motor de consulta del histórico legislativo (módulo de Cauce).

Lógica pura de búsqueda + análisis de supervivencia sobre el dataset
enriquecido de build_dataset.py. Sin dependencias AWS: lee local (dist/) para
desarrollo; la Lambda inyecta los mismos JSON desde S3. Esta separación deja
probar y demostrar Caudal antes de montar el bucket.

CLI de prueba:
  python3 tools/caudal/caudal_core.py buscar "feminicidio"
  python3 tools/caudal/caudal_core.py tema "paridad de género"
  python3 tools/caudal/caudal_core.py proyecto 4177
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

DIST = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'leyes-senado' / 'dist'

ETAPA_LABEL = ['presentado', '1er debate Senado', '2º debate Senado',
               '1er debate Cámara', '2º debate Cámara', 'ley']
RES_LABEL = {
    'LEY': 'convertido en ley', 'ARCHIVADO_TIEMPO': 'archivado por tiempo (Art. 190)',
    'ARCHIVADO_OTRO': 'archivado', 'RETIRADO': 'retirado por el autor',
    'EN_TRAMITE': 'en trámite', 'OTRO': 'otro', 'SIN_DATO': 'sin dato',
}
# F1 · lectura de intención
EMPUJE_LABEL = {
    'exitoso': 'llegó a ley', 'empujado': 'lo empujaron (llegó a 2º debate)',
    'vitrina': 'proyecto de vitrina (re-radicado sin empujar)',
    'un_debate': 'un solo debate', 'sin_traccion': 'sin tracción (1 intento, sin debate)',
}
TIPOLOGIA_LABEL = {
    'honores': 'honores / conmemoración', 'fondos': 'crea un fondo',
    'reforma': 'reforma / código', 'presupuestal': 'presupuestal regional',
    'ordinaria': 'ordinaria',
}


def _norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return s.lower()


# fold 1:1 (preserva offsets, a diferencia de _norm que puede cambiar longitud con
# NFD): minúsculas sin tildes por traducción char→char. Se usa para buscar un
# término dentro del texto crudo de una gaceta sin descuadrar las posiciones del
# recorte del snippet.
_FOLD_MAP = str.maketrans(
    'áàäâãéèëêíìïîóòöôõúùüûñçÁÀÄÂÃÉÈËÊÍÌÏÎÓÒÖÔÕÚÙÜÛÑÇ',
    'aaaaaeeeeiiiiooooouuuuncAAAAAEEEEIIIIOOOOOUUUUNC')


def _fold(s):
    return (s or '').translate(_FOLD_MAP).lower()


# sufijos que trima el stemmer ligero (más largos primero) para tolerar
# erratas/flexiones del propio sistema del Congreso ("feminicido" sin la 2ª i)
_SUFIJOS = ('idades', 'ciones', 'idad', 'cion', 'mente', 'ico', 'ica', 'ios',
            'ias', 'ios', 'os', 'as', 'es', 'io', 'ia', 'o', 'a')


def _stem(term):
    """Raíz conservadora: recorta un sufijo común si deja ≥5 chars."""
    for suf in _SUFIJOS:
        if term.endswith(suf) and len(term) - len(suf) >= 5:
            return term[:-len(suf)]
    return term


def _term_match(term, texto_norm):
    """El término (o su raíz) aparece como substring en el texto normalizado."""
    return term in texto_norm or _stem(term) in texto_norm


# --- capa de sinónimos (tesauro curado) -------------------------------------
# El índice usa stemmer, no tesauro: 'aborto' NO recupera títulos que dicen
# 'interrupción voluntaria del embarazo'. Cuando la consulta cae en un tópico
# curado, la búsqueda pasa de AND-de-palabras a OR sobre TODO el vocabulario del
# tópico (sube el recall). Cada término es una palabra (≥4 chars, match por
# substring/raíz) o una frase (todas sus palabras >3 deben aparecer). Curado
# conservador para no meter ruido; extensible. Todo normalizado (sin tildes,
# minúsculas). Para agregar un tópico: una entrada {k, terms}.
SINONIMOS = [
    {'k': 'aborto / derechos reproductivos', 'terms': [
        'aborto', 'interrupcion voluntaria del embarazo', 'reproductiva',
        'reproductivos', 'salud reproductiva']},
    {'k': 'eutanasia', 'terms': ['eutanasia', 'muerte digna', 'muerte asistida']},
    {'k': 'paridad de genero', 'terms': ['paridad', 'cuota de genero',
                                         'participacion politica de las mujeres']},
    {'k': 'feminicidio', 'terms': ['feminicidio', 'femicidio']},
    {'k': 'violencia de genero', 'terms': ['violencia contra la mujer',
                                           'violencia de genero', 'violencia basada en genero']},
    {'k': 'acoso', 'terms': ['acoso sexual', 'acoso laboral']},
    {'k': 'trata de personas', 'terms': ['trata de personas', 'explotacion sexual']},
    {'k': 'cannabis', 'terms': ['cannabis', 'marihuana', 'cannabis medicinal']},
    {'k': 'dosis minima', 'terms': ['dosis minima', 'dosis personal', 'porte de estupefacientes']},
    {'k': 'licencia de maternidad', 'terms': ['licencia de maternidad',
                                              'licencia de paternidad', 'licencia parental']},
    {'k': 'economia del cuidado', 'terms': ['economia del cuidado',
                                            'trabajo de cuidado', 'sistema nacional de cuidado']},
    {'k': 'teletrabajo', 'terms': ['teletrabajo', 'trabajo en casa', 'trabajo remoto']},
    {'k': 'cambio climatico', 'terms': ['cambio climatico', 'crisis climatica',
                                        'transicion energetica']},
    {'k': 'proteccion animal', 'terms': ['proteccion animal', 'maltrato animal',
                                         'bienestar animal']},
    {'k': 'victimas del conflicto', 'terms': ['victimas del conflicto',
                                              'reparacion de victimas']},
    # --- vocabulario empresarial / sectorial (② · respaldo determinista de la
    # expansión IA de la Lambda). El cliente busca con la palabra del gremio, pero
    # el título formal usa otra: 'etiquetado' → 'entornos alimentarios saludables'
    # (Ley 2120/2021). Validado contra el vocabulario REAL de los títulos; se evitan
    # palabras que colisionan por substring/stem ('seguros'→'segur'≈seguridad,
    # 'gas'≤3 chars queda solo 'natural', 'chatarra'≈chatarrización). Las frases
    # (todas sus palabras >3 deben aparecer) son disparadores seguros: solo activan
    # el tópico si TODAS están en la consulta.
    {'k': 'alimentos / etiquetado', 'terms': [
        'etiquetado', 'rotulado nutricional', 'rotulado', 'sellos de advertencia',
        'entornos alimentarios saludables', 'alimentacion saludable']},
    {'k': 'transporte por plataformas', 'terms': [
        'plataformas digitales', 'plataformas tecnologicas', 'transporte por aplicaciones',
        'aplicaciones de transporte', 'economia colaborativa', 'trabajo en plataformas']},
    {'k': 'asbesto', 'terms': ['asbesto', 'amianto']},
    {'k': 'farmaceutico / medicamentos', 'terms': [
        'medicamentos', 'farmaceutico', 'industria farmaceutica', 'dispositivos medicos',
        'precios de medicamentos']},
    {'k': 'sector financiero', 'terms': [
        'sistema financiero', 'entidades financieras', 'establecimientos de credito',
        'mercado de valores', 'tasa de usura', 'inclusion financiera', 'habeas financiero']},
    {'k': 'energia y servicios publicos', 'terms': [
        'transicion energetica', 'energias renovables', 'servicios publicos domiciliarios',
        'eficiencia energetica', 'energia electrica']},
    {'k': 'telecomunicaciones', 'terms': [
        'telecomunicaciones', 'espectro radioelectrico', 'servicios de comunicaciones',
        'conectividad', 'banda ancha', 'internet']},
    {'k': 'ambiental / medio ambiente', 'terms': [
        'proteccion del medio ambiente', 'licencia ambiental', 'delitos ambientales',
        'deforestacion', 'recursos naturales', 'contaminacion']},
    {'k': 'datos personales / habeas data', 'terms': [
        'datos personales', 'habeas data', 'proteccion de datos', 'tratamiento de datos']},
    {'k': 'mineria e hidrocarburos', 'terms': [
        'mineria', 'hidrocarburos', 'explotacion minera', 'actividad minera', 'regalias']},
    {'k': 'sector agropecuario', 'terms': [
        'agropecuario', 'reforma agraria', 'desarrollo rural', 'produccion agropecuaria']},
    {'k': 'licores y tabaco', 'terms': [
        'bebidas alcoholicas', 'licores', 'tabaco', 'cigarrillo', 'productos de tabaco']},
    {'k': 'propiedad intelectual', 'terms': [
        'propiedad intelectual', 'derechos de autor', 'patentes', 'marcas registradas']},
]


def _phrase_match(term, texto_norm):
    """term = palabra o frase; frase casa si todas sus palabras (>3) aparecen."""
    words = [w for w in term.split() if len(w) > 3]
    if not words:                       # término corto: substring directo
        return term in texto_norm
    return all(_term_match(w, texto_norm) for w in words)


def _topicos(query):
    """Tópicos del tesauro que activa la consulta (por sus propios términos)."""
    qn = _norm(query or '')
    if not qn:
        return []
    return [t for t in SINONIMOS if any(_phrase_match(term, qn) for term in t['terms'])]


# --- Radar del cliente (Vista Cliente · lente SIGA sobre los pilares) --------
# Cada sector define los temas que se buscan en el Congreso + el sector de
# sanciones del pilar Regulatorio + la comisión de referencia para las acciones.
REF_YEAR = 2026    # horizonte del dataset (para calcular "reciente")

# temas curados para PRECISIÓN: palabra sola solo si es distintiva (salud,
# educacion, energia); si el término corto colisiona por substring
# (seguros→seguridad, credito, pension→suspension, banca), se usa frase (AND).
SECTORES_CLIENTE = [
    {'k': 'salud', 'nombre': 'Salud', 'comision': 'Séptima', 'sector_sanciones': 'salud',
     'temas': ['salud', 'medicamentos', 'aseguramiento en salud', 'habilitacion de ips']},
    {'k': 'contratacion', 'nombre': 'Contratación e infraestructura', 'comision': 'Primera',
     'sector_sanciones': 'contratacion',
     'temas': ['contratacion', 'obras publicas', 'concesiones viales', 'licitacion']},
    {'k': 'financiero', 'nombre': 'Financiero', 'comision': 'Tercera', 'sector_sanciones': 'financiero',
     'temas': ['sistema financiero', 'entidades financieras', 'mercado de valores',
               'establecimientos de credito']},
    {'k': 'energia', 'nombre': 'Energía y ambiente', 'comision': 'Quinta', 'sector_sanciones': '',
     'temas': ['energia', 'servicios publicos domiciliarios', 'transicion energetica', 'gas natural']},
    {'k': 'educacion', 'nombre': 'Educación', 'comision': 'Sexta', 'sector_sanciones': '',
     'temas': ['educacion', 'universidades', 'instituciones educativas']},
    {'k': 'trabajo', 'nombre': 'Trabajo y pensiones', 'comision': 'Séptima', 'sector_sanciones': '',
     'temas': ['reforma laboral', 'regimen pensional', 'seguridad social', 'salario minimo']},
]


def sector_cliente(k):
    for s in SECTORES_CLIENTE:
        if s['k'] == k:
            return s
    return None


class Caudal:
    def __init__(self, indice=None, proyectos=None, autor_partido=None,
                 texto_index=None, texto_ids=None):
        self.indice = indice or []
        self._full = proyectos            # dict id→registro completo (lazy)
        self.ap = autor_partido or {}     # canon_key autor → {partido, via, ...}
        # palabra(stem) → [posiciones enteras en texto_ids] — enteros en vez de
        # 'pdly:1234' repetido miles de veces para que el JSON no sea gigante
        # (build_texto_index.py). texto_ids[i] = 'tb:id'.
        self.texto_index = texto_index or {}
        self.texto_ids = texto_ids or []
        self._tn_cache = None             # [(it, título_norm, 'tb:id')] — lazy

    @classmethod
    def from_local(cls):
        indice = json.load(open(DIST / 'indice.json', encoding='utf-8'))['proyectos']
        ap = {}
        p = DIST / 'autor-partido.json'
        if p.exists():
            ap = json.load(open(p, encoding='utf-8'))['autor_partido']
        ti, tids = {}, []
        p = DIST / 'texto-index.json'
        if p.exists():
            d = json.load(open(p, encoding='utf-8'))
            ti, tids = d.get('index', {}), d.get('ids', [])
        return cls(indice=indice, autor_partido=ap, texto_index=ti, texto_ids=tids)

    def _load_full(self):
        # keyed por "tb:id" — pdly y pal comparten el espacio de ids (ambos
        # arrancan en 1), así que un id pelado colisiona entre tablas.
        if self._full is None:
            self._full = {}
            for fn, tb in [('proyectos.jsonl', 'pdly'), ('actos-legis.jsonl', 'pal')]:
                p = DIST / fn
                if not p.exists():
                    continue
                for line in open(p, encoding='utf-8'):
                    r = json.loads(line)
                    self._full[f"{tb}:{r['id']}"] = r
        return self._full

    def _titulos_norm(self):
        """[(it, título_normalizado, 'tb:id')] cacheado — el índice es estático, así
        se normaliza una sola vez por contenedor (antes cada buscar re-normalizaba
        los ~10k títulos; el Radar del cliente llama a buscar ~24 veces por request).
        También sirve para calcular la frecuencia por palabra en la búsqueda relajada."""
        if self._tn_cache is None:
            self._tn_cache = [
                (it, _norm(it['t'] + (' ' + it['ta'] if it.get('ta') else '')),
                 f"{it.get('tb', 'pdly')}:{it['id']}")
                for it in self.indice]
        return self._tn_cache

    def _match_texto(self, query):
        """ids ('tb:id') cuyas gacetas mencionan TODAS las palabras
        significativas de la consulta — capa sobre el título/alias que cubre
        términos que solo aparecen DENTRO de la ponencia/acta, no en el título
        formal (build_texto_index.py, cobertura 2020+ mientras avanza el
        harvest). AND de palabras, mismo criterio que el match de título."""
        if not self.texto_index or not self.texto_ids:
            return set()
        words = [_stem(_norm(w)) for w in (query or '').split() if len(w) > 3]
        if not words:
            return set()
        sets = [set(self.texto_index.get(w, [])) for w in words]   # sets de POSICIONES (int)
        if any(not s for s in sets):
            return set()
        result = sets[0]
        for s in sets[1:]:
            result = result & s
        n = len(self.texto_ids)
        return {self.texto_ids[i] for i in result if 0 <= i < n}

    # -------- búsqueda ------------------------------------------------
    def buscar(self, query, anio_min=None, anio_max=None, comision=None,
               resultado=None, tipologia=None, empuje=None, limit=None, expandir=True,
               extra_terms=None, relajar=False, with_meta=False):
        """Match por keyword(s) en el título O en el texto de sus gacetas.
        Filtros F1: tipologia (honores/fondos/…) y empuje (vitrina/empujado/…).
        `expandir`: si la consulta cae en un tópico del tesauro, matchea por OR
        sobre su vocabulario (capa de sinónimos); si no, AND de palabras (literal).
        `extra_terms`: vocabulario adicional inyectado desde fuera (expansión IA
        de la consulta, ver _expandir_query en la Lambda). Entra al MISMO OR que
        el tesauro curado, así que cubre el desajuste de vocabulario cuando el
        título formal no usa la palabra del usuario ('etiquetado' vs 'entornos
        alimentarios saludables'). La consulta original entra siempre como una
        opción más del OR, para no perder el match literal.
        `relajar` (③ · SOLO la búsqueda del usuario, NO el Radar): cuando la consulta
        es de varias palabras y NO cayó en tópico ni trae expansión IA, en vez de
        exigir TODAS las palabras (AND, que colapsa 'prohibición de asbesto' a 1),
        ancla al término más ESPECÍFICO (el de menor frecuencia = el 'tema'; las
        otras suelen ser calificadores como 'prohibición de', 'regulación de') y
        rankea por cuántas palabras coincide cada título. Reproduce
        'prohibición de asbesto'→37 (=='asbesto') sin inundar con el ruido del
        calificador común. El Radar del cliente deja relajar=False para conservar
        la precisión del AND en sus frases curadas.
        `with_meta`: si True devuelve (lista, {'relajado': ...}) para que la UI
        muestre el aviso de búsqueda flexible."""
        topicos = _topicos(query) if (query and expandir) else []
        or_terms = [term for t in topicos for term in t['terms']]
        if query and extra_terms:
            seen = set(or_terms)
            for t in [query] + list(extra_terms):
                tn = _norm(t or '').strip()
                if len(tn) >= 4 and tn not in seen:
                    seen.add(tn)
                    or_terms.append(tn)
        titn = self._titulos_norm()
        base = [_norm(w) for w in query.split() if len(w) > 2] if query else []
        nbase = len(base)
        relajado = None
        anchor = None
        # ancla = término(s) más específico(s) de la consulta (menor frecuencia en
        # títulos = el "tema"; las demás palabras suelen ser calificadores como
        # 'prohibición de', 'regulación de'). Solo se calcula cuando se necesita
        # (búsqueda del usuario: tópico/IA o relajación) — el Radar la salta.
        need_anchor = bool(base) and (bool(or_terms) or (relajar and nbase >= 2))
        if need_anchor:
            dfw = {w: sum(1 for (_i, t, _x) in titn if _term_match(w, t)) for w in base}
            min_df = min(dfw.values())
            anchor = [w for w in base if dfw[w] == min_df]
        if or_terms:
            def _match(titulo):
                return 1 if any(_phrase_match(term, titulo) for term in or_terms) else 0
        elif relajar and nbase >= 2:
            # rankea por nº de palabras que coincide; incluye si toca el ancla.
            def _match(titulo):
                if not any(_term_match(w, titulo) for w in anchor):
                    return 0
                return sum(1 for w in base if _term_match(w, titulo))   # ≥1
            relajado = {'base': base, 'anchor': anchor}
        elif base:
            def _match(titulo):
                return 1 if all(_term_match(w, titulo) for w in base) else 0
        else:
            _match = None
        # texto de gaceta anclado al término específico (tópico/IA y relajado): un
        # calificador común no debe restringir el texto —'prohibición de asbesto'
        # perdía las 32 menciones de 'asbesto' en ponencias/actas y daba 5 en vez de
        # 37 (agregar palabras encogía). El Radar (base literal, expandir=False)
        # mantiene AND de la frase curada por precisión.
        if not query:
            texto_ids = set()
        elif anchor:
            texto_ids = set()
            for w in anchor:
                texto_ids |= self._match_texto(w)
        else:
            texto_ids = self._match_texto(query)
        out = []
        n_estricto = 0
        for it, t, tid in titn:
            # 't' ya trae título vigente + alias 'ta' normalizados (_titulos_norm),
            # así "clonación" encuentra el proyecto aunque hoy se llame distinto.
            if _match is not None:
                mc = _match(t)
                match_titulo = mc > 0
                match_texto = tid in texto_ids
                if not match_titulo and not match_texto:
                    continue
            else:
                mc, match_titulo, match_texto = 0, True, False
            if anio_min and (it['a'] or 0) < anio_min:
                continue
            if anio_max and (it['a'] or 9999) > anio_max:
                continue
            if comision and _norm(comision) not in _norm(it['com']):
                continue
            if resultado and it['res'] != resultado:
                continue
            if tipologia and it.get('tip') != tipologia:
                continue
            if empuje and it.get('emp') != empuje:
                continue
            if relajado and match_titulo and mc == nbase:
                n_estricto += 1
            if match_texto and not match_titulo:
                rec = {**it, 'mt': True}
            elif relajado:
                rec = {**it, '_mc': mc, '_nw': nbase}
            else:
                rec = it
            out.append(rec)
        if relajado:
            relajado['n_estricto'] = n_estricto
            relajado['n_total'] = len(out)
            # ranking por nº de coincidencias desc (luego año) — para la LISTA de la
            # acción 'buscar'. El timeline del tema re-ordena por año en resumen_tema.
            out.sort(key=lambda x: (-(x.get('_mc') or 0), -(x['a'] or 0)))
        else:
            out.sort(key=lambda x: (x['a'] or 0))
        result = out[:limit] if limit else out
        return (result, {'relajado': relajado}) if with_meta else result

    # -------- análisis de un tema (survival / embudo) -----------------
    def resumen_tema(self, query, **filtros):
        extra_terms = filtros.get('extra_terms') or []
        # relajar=True: la búsqueda del usuario nunca colapsa por AND (③). El
        # Radar del cliente llama a buscar aparte con relajar=False (precisión).
        hits, meta = self.buscar(query, relajar=True, with_meta=True, **filtros)
        n = len(hits)
        leyes = [h for h in hits if h['ley']]
        tiempo = [h for h in hits if h['res'] == 'ARCHIVADO_TIEMPO']
        caidos = [h for h in hits if h['res'] in ('ARCHIVADO_TIEMPO', 'ARCHIVADO_OTRO', 'RETIRADO')]
        embudo = {ETAPA_LABEL[i]: sum(1 for h in hits if h['et'] >= i) for i in range(6)}
        anios = [h['a'] for h in hits if h['a']]
        # autores que más radican en el tema
        autores = {}
        for h in hits:
            for a in h.get('aut', []):
                autores[a] = autores.get(a, 0) + 1
        top_autores = sorted(autores.items(), key=lambda x: -x[1])[:8]
        # bancadas que impulsan el tema (por partido de los autores) + cobertura
        bancadas, con_p, sin_p = {}, 0, 0
        for h in hits:
            partidos_h = set()
            for k in h.get('ak', []):
                e = self.ap.get(k)
                if e:
                    partidos_h.add(e['partido'])
            if partidos_h:
                con_p += 1
                for p in partidos_h:
                    bancadas[p] = bancadas.get(p, 0) + 1
            else:
                sin_p += 1
        top_bancadas = sorted(bancadas.items(), key=lambda x: -x[1])[:8]
        # F1 · lectura de intención del tema
        tipologia = {}
        empuje = {}
        for h in hits:
            tipologia[h.get('tip', 'ordinaria')] = tipologia.get(h.get('tip', 'ordinaria'), 0) + 1
            empuje[h.get('emp', 'sin_traccion')] = empuje.get(h.get('emp', 'sin_traccion'), 0) + 1
        n_vitrina = empuje.get('vitrina', 0)
        n_honores = tipologia.get('honores', 0)
        topicos = _topicos(query)
        # ③ búsqueda flexible: si la consulta multi-palabra se relajó (ancló al
        # término más específico en vez de exigir todas), el aviso explica por qué
        # salieron más resultados que las coincidencias exactas. Reemplaza el viejo
        # 'broaden', que pedía un segundo clic para ampliar a un solo término.
        flexible = None
        rel = (meta or {}).get('relajado')
        if rel and rel.get('n_total', 0) > rel.get('n_estricto', 0):
            flexible = {'anchor': rel['anchor'], 'base': rel['base'],
                        'n_estricto': rel['n_estricto'], 'n_total': rel['n_total']}
        sinonimos = None
        if topicos:
            incluye = []
            for t in topicos:
                for term in t['terms']:
                    if term not in incluye:
                        incluye.append(term)
            sinonimos = {'topicos': [t['k'] for t in topicos], 'incluye': incluye}
        # expansión IA: se reporta aparte para que la UI pueda decir con qué
        # vocabulario se buscó (el usuario debe ver por qué salió un título que
        # no contiene su palabra).
        expansion = {'terminos': list(extra_terms)} if extra_terms else None
        return {
            'query': query, 'n_intentos': n,
            'n_leyes': len(leyes), 'n_caidos': len(caidos),
            'n_muerte_por_tiempo': len(tiempo),
            'pct_exito': round(100 * len(leyes) / n, 1) if n else 0,
            'periodo': [min(anios), max(anios)] if anios else None,
            'embudo': embudo,
            'top_autores': top_autores,
            'bancadas': top_bancadas,
            'cobertura_partido': {'con': con_p, 'sin': sin_p},
            # --- intención ---
            'tipologia': dict(sorted(tipologia.items(), key=lambda x: -x[1])),
            'empuje': dict(sorted(empuje.items(), key=lambda x: -x[1])),
            'n_vitrina': n_vitrina, 'n_honores': n_honores,
            'pct_vitrina': round(100 * n_vitrina / n, 1) if n else 0,
            'flexible': flexible,
            'sinonimos': sinonimos,
            'expansion': expansion,
            # timeline en orden cronológico (buscar puede devolver por ranking cuando
            # relaja); 'mc'/'nw' = palabras coincididas / total, para el toggle
            # cliente-side "solo exactas".
            'intentos': [{
                'id': h['id'], 'tb': h.get('tb', 'pdly'), 'anio': h['a'], 'leg': h['leg'],
                'titulo': h['t'], 'resultado': h['res'],
                'resultado_txt': RES_LABEL.get(h['res'], h['res']),
                'autores': h.get('aut', []), 'autor_principal': h.get('ap'),
                'comision': h.get('com', ''),
                'tipologia': h.get('tip'), 'empuje': h.get('emp'),
                'empuje_txt': EMPUJE_LABEL.get(h.get('emp'), h.get('emp')),
                'vitrina_score': h.get('vs', 0), 'veces_presentado': h.get('vp', 1),
                'crea_fondo': h.get('cf', False), 'jala_presupuesto': h.get('jp', False),
                'etapa_max': h.get('et', 0),
                'mc': h.get('_mc'), 'nw': h.get('_nw'),
                'match_texto': h.get('mt', False),   # matcheó por el texto de su gaceta, no por título
            } for h in sorted(hits, key=lambda h: (h.get('a') or 0))],
        }

    # -------- candidatos para profundizar un tema con texto de gaceta --
    def candidatos_gaceta(self, resumen, k=10):
        """De los intentos de un tema, rankea cuáles vale más la pena leerles
        la gaceta de verdad (no solo su metadata): prioriza los MÁS RECIENTES
        (solo 2020+ tiene texto subido) y los que llegaron MÁS LEJOS en el
        trámite (más etapas = ponencia/acta más informativa sobre por qué pasó
        o se cayó). No garantiza que el texto exista en S3 — eso lo intenta el
        llamador (Lambda) en orden, y salta al siguiente si falta."""
        cand = [it for it in resumen.get('intentos', []) if (it.get('anio') or 0) >= 2019]
        cand.sort(key=lambda it: (it.get('etapa_max', 0), it.get('anio') or 0), reverse=True)
        return cand[:k]

    # -------- snippet del cuerpo de gaceta (para los match ◈ "en el texto") --
    def snippet_terms(self, query):
        """Términos a buscar/resaltar en el fragmento: el vocabulario del tópico si
        la consulta cayó en uno (así 'eutanasia' también encuentra 'muerte digna'
        en el texto), si no las palabras de la consulta (>3 chars)."""
        topicos = _topicos(query)
        if topicos:
            terms, seen = [], set()
            for t in topicos:
                for term in t['terms']:
                    if term not in seen:
                        seen.add(term)
                        terms.append(term)
            return terms
        return [_norm(w) for w in (query or '').split() if len(w) > 3]

    def make_snippet(self, text, terms, ctx=110):
        """Primer fragmento del texto (crudo) donde aparece alguno de los términos,
        con ±ctx chars de contexto y espacios colapsados. Devuelve
        {'snippet','match'} (match = el fragmento tal como aparece, para resaltar)
        o None. Búsqueda sin tildes/mayúsculas preservando offsets (fold 1:1)."""
        if not text:
            return None
        folded = _fold(text)
        best = None                       # (pos, largo del término)
        for term in terms:
            ft = _fold(term)
            if len(ft) < 3:
                continue
            # \b al inicio: 'pension' NO debe pegar dentro de 'suspensión'; sí en
            # 'pensional'/'pensiones' (arranca palabra). Frases ('muerte digna')
            # matchean textual con espacio en medio.
            m = re.search(r'\b' + re.escape(ft), folded)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), len(ft))
        if best is None:
            return None
        i, ln = best
        # extiende hasta el fin de la palabra para resaltar la palabra completa
        # (pension → pensional), no solo el prefijo del término
        j = i + ln
        while j < len(folded) and folded[j].isalpha():
            j += 1
        match = text[i:j]
        a, b = max(0, i - ctx), min(len(text), j + ctx)
        frag = re.sub(r'\s+', ' ', text[a:b]).strip()
        return {'snippet': ('…' if a > 0 else '') + frag + ('…' if b < len(text) else ''),
                'match': match}

    # -------- Radar del cliente · señales legislativas -----------------
    def radar_congreso(self, sector_key=None, temas=None, comision_lbl='', cap=10):
        """Proyectos que tocan los temas del cliente, priorizados por
        accionabilidad (en trámite > caído reciente > ley > antecedente)."""
        if temas is None:
            s = sector_cliente(sector_key) or {}
            temas = s.get('temas', [])
            comision_lbl = comision_lbl or s.get('comision', '')
        seen = {}
        for t in temas:
            # expandir=False + relajar=False: los temas del Radar son frases curadas
            # para PRECISIÓN (AND literal); el tesauro/relajación es solo de la
            # búsqueda libre del usuario, no del Radar.
            for h in self.buscar(t, expandir=False):
                seen.setdefault((h.get('tb', 'pdly'), h['id']), h)
        hits = list(seen.values())

        def _score(h):
            res, a = h.get('res'), (h.get('a') or 0)
            if res == 'EN_TRAMITE':
                base = 3
            elif res in ('ARCHIVADO_TIEMPO', 'ARCHIVADO_OTRO') and a >= REF_YEAR - 2:
                base = 2
            elif res == 'LEY' and a >= REF_YEAR - 3:
                base = 2
            elif res == 'LEY':
                base = 1
            else:
                base = 0
            return (base, a)

        hits.sort(key=_score, reverse=True)
        senales = [self._senal_congreso(h, comision_lbl) for h in hits[:cap]]
        return {'n_tocados': len(hits), 'n_mostrados': len(senales), 'senales': senales}

    def _senal_congreso(self, h, comision_lbl):
        res, a = h.get('res'), (h.get('a') or 0)
        com = (h.get('com', '') or comision_lbl).title()   # comisión REAL del proyecto
        if res == 'EN_TRAMITE':
            nivel = 'alto'
            accion = f'Ventana de incidencia abierta — preparar concepto para la Comisión {com}'.strip()
        elif res in ('ARCHIVADO_TIEMPO', 'ARCHIVADO_OTRO') and a >= REF_YEAR - 2:
            nivel, accion = 'medio', 'Cayó reciente (probable re-radicación) — vigilar el orden del día'
        elif res == 'LEY':
            nivel = 'medio' if a >= REF_YEAR - 3 else 'bajo'
            accion = 'Ya es ley — revisar reglamentación y cumplimiento'
        else:
            nivel, accion = 'bajo', 'Antecedente histórico — monitoreo pasivo'
        return {'tipo': 'congreso', 'id': h['id'], 'tb': h.get('tb', 'pdly'),
                'anio': a, 'titulo': h['t'], 'comision': h.get('com', ''),
                'resultado': res, 'resultado_txt': RES_LABEL.get(res, res),
                'empuje': h.get('emp'), 'nivel': nivel, 'accion': accion}

    # -------- ficha de un proyecto ------------------------------------
    def proyecto(self, pid, tb='pdly'):
        full = self._load_full()
        r = full.get(f"{tb}:{int(pid)}") or full.get(f"pdly:{int(pid)}") or full.get(f"pal:{int(pid)}")
        if not r:
            return None
        keys = r.get('autores_keys', [])
        principal = r.get('autor_principal')
        autores = [{'nombre': n, 'partido': (self.ap.get(k) or {}).get('partido'),
                    'principal': (n == principal)}
                   for n, k in zip(r.get('autores', []), keys)]
        et = r.get('etapa_max')
        emp = r.get('empuje')
        return {
            'id': r['id'], 'tabla': r.get('tabla', tb), 'titulo': r.get('titulo', ''),
            'titulos_alt': r.get('titulos_alt', []),
            'numero_senado': r.get('numero_senado', ''), 'numero_camara': r.get('numero_camara', ''),
            'legislatura': r.get('legislatura', ''), 'comision': r.get('comision', ''),
            'autores': autores,
            # --- F1: autoría real ---
            'autor_principal': principal,
            'coautores': r.get('coautores', []),
            'n_firmantes': r.get('n_firmantes', len(autores)),
            'autoria_colectiva': r.get('autoria_colectiva', False),
            'autor_tipo': r.get('autor_tipo'), 'entidad': r.get('entidad'),
            # --- F1: tipología + intención ---
            'tipologia': r.get('tipologia'),
            'tipologia_txt': TIPOLOGIA_LABEL.get(r.get('tipologia')),
            'crea_fondo': r.get('crea_fondo', False),
            'jala_presupuesto_regional': r.get('jala_presupuesto_regional', False),
            'empuje': emp, 'empuje_txt': EMPUJE_LABEL.get(emp, emp),
            'vitrina_score': r.get('vitrina_score', 0),
            'veces_presentado': r.get('veces_presentado', 1),
            'historial_reradicacion': r.get('historial_reradicacion', []),
            'reloj': r.get('reloj'),
            'resultado': r.get('resultado'), 'resultado_txt': RES_LABEL.get(r.get('resultado')),
            'etapa_max': ETAPA_LABEL[et] if isinstance(et, int) and 0 <= et < len(ETAPA_LABEL) else None,
            'fecha_presentacion': r.get('fecha_presentacion'),
            'dias_a_primer_debate': r.get('dias_a_primer_debate'),
            'gacetas': r.get('gacetas', []),   # ← punteros para la fase DeepSeek
        }


def _cli():
    caudal = Caudal.from_local()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'tema'
    arg = sys.argv[2] if len(sys.argv) > 2 else 'feminicidio'
    if cmd == 'buscar':
        for h in caudal.buscar(arg, limit=25):
            print(f"  [{h['a']}] {RES_LABEL.get(h['res'],h['res']):<28} {h['t'][:64]}")
    elif cmd == 'proyecto':
        print(json.dumps(caudal.proyecto(arg), ensure_ascii=False, indent=1))
    else:
        r = caudal.resumen_tema(arg)
        print(f"\nTEMA: «{arg}»  ·  {r['n_intentos']} intentos  ·  "
              f"{r['n_leyes']} leyes ({r['pct_exito']}%)  ·  "
              f"{r['n_caidos']} caídos ({r['n_muerte_por_tiempo']} por tiempo)  ·  "
              f"periodo {r['periodo']}")
        print(f"\nIntención:  {r['n_vitrina']} de vitrina ({r['pct_vitrina']}%)  ·  "
              f"{r['n_honores']} de honores")
        print('  empuje:  ' + '  '.join(f"{v}×{EMPUJE_LABEL.get(k,k).split('(')[0].strip()}" for k, v in r['empuje'].items()))
        print('  tipo:    ' + '  '.join(f"{v}×{k}" for k, v in r['tipologia'].items()))
        print('\nEmbudo:')
        for et, n in r['embudo'].items():
            print(f"  {n:4}  {et}")
        print('\nQuién más lo intenta:')
        for a, c in r['top_autores']:
            print(f"  {c}×  {a}")
        print('\nLínea de intentos:')
        for it in r['intentos']:
            print(f"  [{it['anio']}] {it['resultado_txt']:<30} {it['titulo'][:56]}")


if __name__ == '__main__':
    _cli()
