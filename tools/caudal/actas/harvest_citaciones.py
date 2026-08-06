#!/usr/bin/env python3
"""
Caudal · CITACIONES DE CONTROL POLÍTICO por congresista.

NO cosecha nada nuevo: lee el MISMO caché de órdenes del día que ya alimenta el
índice de bloqueo (actas/ordenes/ y actas/ordenes-senado/, ~1,3 GB de PDF+TXT).
El control político se agenda ahí igual que los proyectos de ley, y la ficha
viene completa — citante(s), citado, objeto, nº de proposición y fecha:

    Debate Control Político. Citación a la señora Ministra de Minas y Energía,
    doctora MARIA FERNANDA SUAREZ LONDOÑO, [...] con el fin de debatir las
    medidas que ha tomado el sector durante la contingencia [...]
    Según Proposiciones No. 077 y aditiva No. 080. Legislatura 2019-2020,
    suscrita por los H. Representantes RICARDO ALFONSO FERRO LOZANO, [...]

Es foso real: el voto nominal lo tienen otros; quién ejerce control político y
sobre quién, no lo publica nadie.

────────────────────────────────────────────────────────────────────────────
LO QUE ESTE DATO ES — Y LO QUE NO
────────────────────────────────────────────────────────────────────────────
Es la citación AGENDADA en el orden del día, no el debate realizado. Exactamente
el mismo matiz de "agendado vs tratado" del índice de bloqueo, y aquí es la parte
interesante, no un defecto: una citación agendada 6 veces y nunca realizada es la
historia. Por eso cada citación guarda `n` + `fechas` (igual que agendamientos).

NO es moción de censura ni votación: eso vive en las actas, no en la agenda.

────────────────────────────────────────────────────────────────────────────
GOTCHAS MEDIDOS (jul-2026, sobre el caché local · no repetir la investigación)
────────────────────────────────────────────────────────────────────────────
· COBERTURA ASIMÉTRICA entre las dos entidades del registro, y hay que declararla
  por separado porque son muy distintas: Senado trae etiqueta explícita
  `CITANTES:` (81% de sus docs) y nombra al citado en 89%; Cámara usa
  `suscrita por los H. Representantes` (71%) pero solo nombra al citado en 45%.
  Un porcentaje global promediaría dos cosas distintas y mentiría sobre ambas.

· CITANTE y CITADO se extraen POR SEPARADO y tienen cobertura distinta. Muchos
  documentos de Cámara solo citan el nº de proposición y el cargo del citado
  ("aprobado mediante proposiciones N°. 01 al Director de la DIAN"), sin nombrar
  a ningún congresista. Eso NO es un fallo del parser: la fuente no lo trae.

· EL RUIDO SE FILTRA CON EL ROSTER, NO CON EL REGEX. El extractor de nombres
  produce colas de basura ("GACETA PONENCIA PRIMER DEBATE", "CONSTA EN ACTA",
  "SE DICTAN DISPOSICIONES"). Medido: los nombres que NO casan con el roster son
  67% apariciones únicas, mientras los que sí casan son 56% con ≥3 apariciones.
  Esa es la firma sana — se deja que el join decida y NO se afloja el emparejador.

· FUGA DE PRECISIÓN TAPADA: el bloque de citantes a veces arrastra texto del
  citado ("MINISTRO RELACIONES EXTERIORES" salía como si fuera un congresista).
  Se veta por vocabulario de cargo/institución (CARGO_VETO), no por longitud.

· SECCIÓN VACÍA: solo 5 de 1.142 docs traen el encabezado de control político sin
  contenido. Casi todos los que lo mencionan tienen citación real.

· Congresistas reales que el roster no tiene (límite pre-2014 ya documentado)
  quedan con `rk: null` y se cuentan aparte (`n_sin_roster`) en vez de
  descartarse en silencio — si no, se leería como que no citaron.

Uso:
  python3 tools/caudal/actas/harvest_citaciones.py todas
  python3 tools/caudal/actas/harvest_citaciones.py quinta
  python3 tools/caudal/actas/harvest_citaciones.py camara | senado
Es 100% offline (solo lee el caché) → seguro de correr en el cron.
"""
import json, re, sys, hashlib, unicodedata
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_ordenes import (  # noqa: E402
    REPO, SRC, CACHE, DIST, TARGETS as CAM_TARGETS, fecha_sesion,
)
from harvest_ordenes_senado import (  # noqa: E402
    AMBITOS as SEN_AMBITOS, PLENARIA as SEN_PLENARIA, IDX_CACHE, IDX_CACHE_PLEN,
    PLEN_EXCLUIR_RE, es_candidato, ambito_de, fecha_sesion_senado,
)

OUTDIR = CACHE

# ── secciones ───────────────────────────────────────────────────────────────
# El encabezado de la SECCIÓN, no cualquier mención de la frase. Debe ir al
# arranque de línea (con o sin numeral romano). Buscar la frase suelta trae dos
# falsos positivos MEDIDOS que no son citaciones (ver docstring):
#   (a) el pie de página con el correo de la comisión ("Para proposiciones de
#       debates de control político … comision.primera@camara.gov.co")
#   (b) el TÍTULO de un proyecto de ley que habla del tema ("…Control Político
#       del Congreso de la República"), que además arrastraba los AUTORES del
#       proyecto como si fueran citantes.
CP_RE = re.compile(
    r'^[ \t]*(?:[IVX]{1,6}[ \t]*[.\-)]?[ \t]*)?'
    r'(?:DEBATE[S]?[ \t]+(?:DE[ \t]+)?)?CONTROL[ \t]+POL[IÍ]TICO', re.I | re.M)
# Segundo anclaje: la fórmula imperativa. Hace falta porque NO todas las
# comisiones titulan la sección — la Cuarta del Senado la encabeza "Citación." y
# mete la frase "control político" a mitad de la oración ("…a un debate de
# Control Político, con el objeto de…"), así que exigir encabezado de línea la
# dejaba en 15 de 103 documentos. El bloque igual debe mencionar control
# político para entrar (CP_TXT_RE), y así no se cuelan invitaciones ordinarias.
CITESE_RE = re.compile(
    r'\bC[ií]t(?:ese|ar)\s+(?:a|al)\b|\bCitaci[oó]n\s*[.:]?\s*(?:a|al)\b', re.I)
CP_TXT_RE = re.compile(r'control\s+pol[ií]tico', re.I)
# Vetos de contexto para descartar (a) y (b) sin depender de la longitud.
BOILER_RE = re.compile(
    r'para\s+proposiciones\s+de\s+debates?\s+de\s+control|@[\w.]*(?:camara|senado)\.gov\.co', re.I)
TITULO_PROY_RE = re.compile(r'["“»]|proyecto\s+de\s+(?:ley|acto)', re.I)
PROY_LIN_RE = re.compile(r'proyecto\s+de\s+(?:ley|acto)', re.I)
# Fin de la sección: siguiente encabezado del orden del día. Se listan los
# marcadores reales vistos en las dos cámaras; el numeral romano solo cuenta si
# está SOLO en su línea (si no, "VI" partiría dentro de cualquier palabra).
SEC_FIN_RE = re.compile(
    r'\n\s*(?:'
    r'[IVX]{1,5}\s*[.\-)]?\s*\n'
    r'|ANUNCIO\s+DE\s+PROYECTO'
    r'|LO\s+QUE\s+PROPONGAN'
    r'|NEGOCIOS\s+SUSTANCIADO'
    r'|LECTURA\s+DE\s+PONENCIA'
    r'|LLAMADO\s+A\s+LISTA'
    r'|LEVANTAMIENTO\s+DE\s+LA\s+SESI[OÓ]N'
    r'|CITACI[OÓ]N\s+PARA\s+LA\s+PR[OÓ]XIMA'
    r')', re.I)

# ── citantes ────────────────────────────────────────────────────────────────
CITANTE_RE = re.compile(
    r'(?:'
    r'CITANTES?\s*:'                                     # Senado (etiqueta)
    r'|suscrit[ao]s?\s+por'                              # Cámara (clásica)
    r'|presentad[ao]s?\s+por'
    r'|radicad[ao]s?\s+por'
    r'|a\s+solicitud\s+de(?:l)?'
    # OJO: "Autores:" NO entra. En un orden del día ese rótulo son SIEMPRE los
    # autores de un proyecto de ley, no los citantes de una citación (medido: un
    # solo documento de Primera metía 87 firmantes de proyectos por esa vía).
    r')'
    r'\s*(?:l[oa]s?\s+)?(?:H+\.?\s*)?'
    r'(?:Representantes?|Senador[ae]s?|Congresistas?)?\s*[:.]?\s*'
    r'(.{3,700}?)'
    r'(?=\n\s*\n|\n\s*[IVX]{1,5}\s*\n|CITAD|TEMA\s*:|OBJET|$)', re.I | re.S)

# ── citados ─────────────────────────────────────────────────────────────────
CARGOS = (r'Ministr[oa]|Viceministr[oa]|Superintendente|Director[a]?|Presidente|'
          r'Gerente|Fiscal\s+General|Procurador[a]?|Contralor[a]?|Defensor[a]?\s+del\s+Pueblo|'
          r'Comandante|Registrador[a]?|Alcalde|Gobernador[a]?|Secretari[oa]\s+General')
CITADO_RE = re.compile(
    r'\b(' + CARGOS + r')\b'
    r'(?P<ent>[^,.;\n]{0,90}?)'
    r'\s*,?\s*(?:doctor[a]?|Dr[a]?\.|se[ñn]or[a]?)\s*'
    r'(?P<nom>(?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]*\s+){1,5}[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]*)',
    re.I)
# variante sin "doctor/señor": "cítese a la Ministra de Agricultura, Jhenifer Mojica Flórez"
CITADO_SIMPLE_RE = re.compile(r'\b(' + CARGOS + r')\b(?P<ent>[^,.;\n]{0,90})', re.I)

PROPOSICION_RE = re.compile(
    r'proposici[oó]n(?:es)?\s*(?:N[°ºo]?\.?|No\.?|Nro\.?|número)?\s*(\d{1,4})', re.I)
LEGISLATURA_RE = re.compile(r'legislatura\s*(20\d{2})\s*[-–/]\s*(20\d{2})', re.I)
# El objeto del debate. Los verbos llevan sufijo abierto (`explique\w*`) porque
# sin él "expliquen" partía la captura a mitad de palabra y el tema arrancaba en
# "n las medidas…". No se ancla en "sobre la": es demasiado común y engancha
# cualquier oración del documento.
TEMA_RE = re.compile(
    r'(?:TEMA\s*:|(?:con\s+el|el)\s+(?:fin|objeto|objetivo|prop[oó]sito)\s+(?:de|es)|'
    r'para\s+que\s+(?:se\s+)?(?:rinda\w*|sirva\w*|informe\w*|explique\w*|expong\w*))\s*'
    r'(?:que\s+)?(.{15,400}?)'
    r'(?=\n\s*\n|CITANTE|Lo\s+anterior|Seg[uú]n\s+[Pp]roposici|de\s+conformidad|$)',
    re.I | re.S)

# ── limpieza de nombres ─────────────────────────────────────────────────────
NOISE = re.compile(
    r'^(y|e|o|de|del|la|el|los|las|al|a|h|hh|hr|hs|dr|dra|doctor|doctora|honorable|'
    r'honorables|representante|representantes|senador|senadora|senadores|senadoras|'
    r'otros|otras|mediante|segun|proposicion|proposiciones|no|nro|num|numero|'
    r'legislatura|aditiva|fecha|acta|gaceta|congreso|dia|dias)$', re.I)
# Vocabulario que delata que el "nombre" es en realidad un cargo, una entidad o
# boilerplate del documento — la fuga de precisión medida (ver docstring).
CARGO_VETO = re.compile(
    r'\b(MINISTR|VICEMINISTR|SUPERINTEND|DIRECTOR|DIRECTORA|GERENTE|PRESIDENT|'
    r'FISCAL|PROCURADOR|CONTRALOR|DEFENSOR|COMANDANTE|REGISTRADOR|ALCALDE|'
    r'GOBERNADOR|SECRETARI|COMISION|CAMARA|SENADO|REPUBLICA|COLOMBIA|NACIONAL|'
    r'MINISTERIO|AGENCIA|INSTITUTO|DEPARTAMENTO|SUPERINTENDENCIA|ENTIDAD|'
    r'GACETA|PONENCIA|DEBATE|ACTA|DISPOSICIONES|CREDITO|PUBLICO|PROYECTO|'
    r'ARTICULO|DECRETO|SESION|PLENARIA|MESA|DIRECTIVA|ORDEN|APROBAD|CUALES|'
    r'INFORME|ESTUDIO|SISTEMA|GENERAL|PUEBLO|ESTADO|GOBIERNO)\b')


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z ]', ' ', s.upper())


def limpiar_nombre(p):
    toks = [t for t in norm(p).split() if len(t) > 1 and not NOISE.match(t)]
    if not (2 <= len(toks) <= 6):
        return None
    nom = ' '.join(toks)
    if CARGO_VETO.search(nom):
        return None
    return nom


def split_nombres(blob):
    blob = re.sub(r'\s+', ' ', blob)
    blob = re.sub(r'\b(H+\.?\s*R+\.?|H+\.?\s*S+\.?|HH\.?|Dr[a]?\.?|Doctor[a]?|'
                  r'Honorables?|Representantes?|Senador[ae]s?|Congresistas?)\b',
                  ',', blob, flags=re.I)
    out = []
    for p in re.split(r'[,;]|\sy\s|\se\s|\n', blob):
        n = limpiar_nombre(p)
        if n and n not in out:
            out.append(n)
    return out


# ── roster ──────────────────────────────────────────────────────────────────
_ROSTER_IDX = None


def roster_idx():
    """frozenset(tokens) → roster_key. Mismo criterio de subconjunto que
    build_roster.py / la Lambda: exacto primero, luego subconjunto ÚNICO. Si dos
    keys son compatibles NO se adivina (dos personas comparten apellidos)."""
    global _ROSTER_IDX
    if _ROSTER_IDX is None:
        _ROSTER_IDX = {}
        p = DIST / 'roster-autores.json'
        if p.exists():
            for k in json.load(open(p, encoding='utf-8'))['roster']:
                toks = frozenset(t for t in norm(k).split() if len(t) > 1)
                if len(toks) >= 2:
                    _ROSTER_IDX.setdefault(toks, k)
    return _ROSTER_IDX


def match_roster(nombre):
    idx = roster_idx()
    toks = frozenset(t for t in norm(nombre).split() if len(t) > 1)
    if toks in idx:
        return idx[toks]
    best = None
    for k, v in idx.items():
        if toks <= k or k <= toks:
            if best is not None:
                return None          # ambiguo → no se adivina
            best = v
    return best


# ── extracción ──────────────────────────────────────────────────────────────
def seccion_cp(txt):
    """Bloques de texto de las secciones de control político, ya descartando los
    dos falsos positivos medidos (pie de página con el correo de la comisión y
    título de proyecto de ley que habla del tema)."""
    anclas = ([(m.start(), m.end(), 'hdr') for m in CP_RE.finditer(txt)]
              + [(m.start(), m.end(), 'cit') for m in CITESE_RE.finditer(txt)])
    anclas.sort()
    out, fin_prev = [], -1
    for ini, end, tipo in anclas:
        if ini < fin_prev:            # ya cubierto por el bloque anterior
            continue
        nl = txt.find('\n', ini)
        lin = txt[ini:nl if nl > 0 else ini + 200]
        if BOILER_RE.search(txt[max(0, ini - 160):ini + 200]):
            continue                  # pie de página con el correo de la comisión
        # El veto de comillas aplica SOLO al encabezado: ahí una comilla delata el
        # título de un proyecto que habla del tema. En el anclaje imperativo las
        # comillas son normales — el objeto del debate suele ir entrecomillado.
        if TITULO_PROY_RE.search(lin) if tipo == 'hdr' else PROY_LIN_RE.search(lin):
            continue
        f = SEC_FIN_RE.search(txt, end)
        fin_prev = f.start() if f else min(len(txt), ini + 2500)
        bloque = txt[ini:fin_prev]
        if len(bloque.strip()) > 60 and CP_TXT_RE.search(bloque):
            out.append(bloque)
    return out


def citados_de(bloque):
    vistos, out = set(), []
    for m in CITADO_RE.finditer(bloque):
        nom = limpiar_nombre(m.group('nom'))
        if not nom or nom in vistos:
            continue
        vistos.add(nom)
        cargo = re.sub(r'\s+', ' ', (m.group(1) + ' ' + (m.group('ent') or ''))).strip(' ,.;')
        out.append({'nombre': nom.title(), 'cargo': cargo[:90]})
    if out:
        return out
    # sin nombre propio: al menos se registra el cargo citado (el caso Cámara,
    # que nombra al citado solo en 45% de sus documentos)
    for m in CITADO_SIMPLE_RE.finditer(bloque):
        cargo = re.sub(r'\s+', ' ', m.group(0)).strip(' ,.;')
        if len(cargo) > 8 and cargo.lower() not in vistos:
            vistos.add(cargo.lower())
            out.append({'nombre': None, 'cargo': cargo[:90]})
        if len(out) >= 6:
            break
    return out


def citantes_de(bloque):
    noms = []
    for blob in CITANTE_RE.findall(bloque):
        for n in split_nombres(blob):
            if n not in noms:
                noms.append(n)
    return noms


def tema_de(bloque):
    m = TEMA_RE.search(bloque)
    if not m:
        return ''
    t = re.sub(r'\s+', ' ', m.group(1)).strip(' .,;:')
    return t[:300]


def legislatura_de(fecha):
    """Legislatura a la que pertenece una fecha. Arranca el 20 de julio."""
    if not fecha or len(fecha) < 10:
        return None
    y, m, d = int(fecha[:4]), int(fecha[5:7]), int(fecha[8:10])
    return f'{y}-{y + 1}' if (m > 7 or (m == 7 and d >= 20)) else f'{y - 1}-{y}'


def clave(bloque, citados, prop, ambito, fecha, doc_id):
    """Identidad de la citación, para colapsar re-agendamientos de la MISMA
    citación en distintas sesiones.

    ⚠️ EL Nº DE PROPOSICIÓN NO ES IDENTIFICADOR ÚNICO: se reinicia cada
    legislatura, así que la proposición 01 de 2023 y la 01 de 2019 son cosas
    distintas. Keyear solo por el número fundía citaciones de años distintos en
    una sola (medido: 73 documentos de la Primera colapsaban en 1 registro).
    Por eso la llave lleva SIEMPRE la legislatura, tomada del texto si la
    declara y si no derivada de la fecha de sesión — misma clase de trampa que
    el número de radicado en el dataset de proyectos.

    Sin proposición se usa la huella del citado + objeto (el texto del orden del
    día se reproduce casi literal entre sesiones). Si no hay NINGÚN rasgo
    distintivo no se colapsa nada: la llave queda por documento, porque fundir
    registros vacíos no es deduplicar, es perder datos.
    """
    leg = prop.split('/')[1] if (prop and '/' in prop) else legislatura_de(fecha)
    if prop:
        return f'{ambito}:P{prop.split("/")[0]}:{leg or "?"}'
    base = '|'.join(sorted((c['nombre'] or c['cargo'] or '') for c in citados))
    tema = tema_de(bloque)[:80]
    if not base and not tema:
        return f'{ambito}:D{doc_id}'
    return f'{ambito}:H' + hashlib.md5(norm(base + '|' + tema + '|' + (leg or '')).encode()).hexdigest()[:10]


# ── iteradores de documentos (leen SOLO el caché) ───────────────────────────
def docs_camara(ambito):
    d = CACHE / 'ordenes' / ambito
    ef = d / '_eventos.json'
    if not ef.exists():
        return
    for ev in json.load(open(ef, encoding='utf-8')):
        tf = d / f"{ev['id']}.txt"
        if not tf.exists():
            continue
        txt = tf.read_text(encoding='utf-8')
        if len(txt.strip()) < 50:
            continue
        pub = (ev.get('date') or '')[:10]
        fecha, _ = fecha_sesion((ev.get('title') or {}).get('rendered', ''), pub)
        yield ev['id'], fecha, txt


def docs_senado(ambito):
    d = SRC / 'actas' / 'ordenes-senado' / ambito
    if ambito == SEN_PLENARIA:
        idx = IDX_CACHE_PLEN
        filtro = lambda doc: not PLEN_EXCLUIR_RE.search(doc.get('title') or '')
    else:
        idx = IDX_CACHE
        filtro = lambda doc: es_candidato(doc) and ambito_de(doc) == ambito
    if not idx.exists():
        return
    for doc in json.load(open(idx, encoding='utf-8')):
        if not filtro(doc):
            continue
        tf = d / f"{doc['id']}.txt"
        of = d / f"{doc['id']}.ocr.txt"
        txt = ''
        if tf.exists():
            txt = tf.read_text(encoding='utf-8')
        if len(txt.strip()) < 50 and of.exists():
            txt = of.read_text(encoding='utf-8')
        if len(txt.strip()) < 50:
            continue
        pub = (doc.get('publish_date') or '')[:10]
        fecha, _ = fecha_sesion_senado(doc.get('title'), txt, pub,
                                       titulo_flex=(ambito == SEN_PLENARIA))
        yield doc['id'], fecha, txt


# ── run ─────────────────────────────────────────────────────────────────────
def run(camara, ambito):
    it = docs_camara(ambito) if camara == 'camara' else docs_senado(ambito)
    cit = {}
    n_docs = n_cp = n_vacia = n_con_citante = n_con_citado = 0
    sin_roster = Counter()

    for _id, fecha, txt in it:
        n_docs += 1
        bloques = seccion_cp(txt)
        if not bloques:
            continue
        n_cp += 1
        hay_citante = hay_citado = False
        for b in bloques:
            citados = citados_de(b)
            citantes = citantes_de(b)
            if not citados and not citantes:
                n_vacia += 1
                continue
            hay_citado |= bool(citados)
            hay_citante |= bool(citantes)
            mp = PROPOSICION_RE.search(b)
            prop = mp.group(1).lstrip('0') or '0' if mp else None
            ml = LEGISLATURA_RE.search(b)
            if prop and ml:
                prop = f'{prop}/{ml.group(1)}-{ml.group(2)}'
            k = clave(b, citados, prop, ambito, fecha, _id)
            rec = cit.setdefault(k, {
                'proposicion': prop, 'tema': tema_de(b),
                'citados': citados, 'citantes': [], 'citantes_sin_roster': [],
                '_vistos': set(), 'fechas': [],
            })
            if not rec['tema']:
                rec['tema'] = tema_de(b)
            if len(citados) > len(rec['citados']):
                rec['citados'] = citados
            for n in citantes:
                # dedup contra el nombre CRUDO (mayúsculas). Compararlo contra el
                # ya pasado a title-case no acierta nunca y los citantes se
                # repetían una vez por re-agendamiento (medido: 10 personas
                # contadas 80 veces en una citación agendada 8 sesiones).
                if n in rec['_vistos']:
                    continue
                rec['_vistos'].add(n)
                rk = match_roster(n)
                if rk is None:
                    # No se descarta en silencio: aquí conviven la cola de basura
                    # del PDF y congresistas reales que el roster no tiene (su
                    # límite pre-2014). Van en lista aparte para que el consumidor
                    # use los confirmados sin que se pierda el rastro de los otros.
                    sin_roster[n] += 1
                    rec['citantes_sin_roster'].append(n.title())
                else:
                    rec['citantes'].append({'nombre': n.title(), 'rk': rk})
            if fecha and fecha not in rec['fechas']:
                rec['fechas'].append(fecha)
        n_con_citante += hay_citante
        n_con_citado += hay_citado

    for k, r in cit.items():
        r.pop('_vistos', None)
        r['fechas'].sort()
        r['n'] = len(r['fechas'])
        r['primera'] = r['fechas'][0] if r['fechas'] else None
        r['ultima'] = r['fechas'][-1] if r['fechas'] else None

    n_rk = sum(len(r['citantes']) for r in cit.values())
    n_tot = n_rk + sum(len(r['citantes_sin_roster']) for r in cit.values())
    out = {
        'camara': camara, 'ambito': ambito,
        'n_docs': n_docs, 'n_docs_cp': n_cp, 'n_secciones_sin_dato': n_vacia,
        'n_docs_con_citante': n_con_citante, 'n_docs_con_citado': n_con_citado,
        'n_citaciones': len(cit),
        'n_citantes_menciones': n_tot, 'n_citantes_con_roster': n_rk,
        'n_sin_roster': len(sin_roster),
        'citaciones': cit,
    }
    outf = OUTDIR / f'citaciones-{camara}-{ambito}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  {camara}/{ambito:12s} docs={n_docs:4d} cp={n_cp:4d} '
          f'citaciones={len(cit):4d} citantes={n_tot:5d} (roster {n_rk}) '
          f'→ {outf.name}')
    return out


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else 'todas'
    tareas = []
    if arg in ('todas', 'camara'):
        tareas += [('camara', a) for a in CAM_TARGETS]
    if arg in ('todas', 'senado'):
        tareas += [('senado', a) for a in list(SEN_AMBITOS) + [SEN_PLENARIA]]
    if not tareas:
        for cam, ams in (('camara', CAM_TARGETS),
                         ('senado', list(SEN_AMBITOS) + [SEN_PLENARIA])):
            if arg in ams:
                tareas.append((cam, arg))
    if not tareas:
        sys.exit(f'ámbito desconocido: {arg}\n'
                 f'válidos: todas · camara · senado · {", ".join(CAM_TARGETS)}')

    print('· citaciones de control político (offline, sobre el caché de órdenes del día)')
    tot = Counter()
    for cam, am in tareas:
        try:
            o = run(cam, am)
        except Exception as e:
            print(f'  ! {cam}/{am}: {type(e).__name__}: {str(e)[:80]}')
            continue
        for k in ('n_docs', 'n_docs_cp', 'n_citaciones',
                  'n_citantes_menciones', 'n_citantes_con_roster'):
            tot[k] += o[k]
    print(f'\n  TOTAL docs={tot["n_docs"]} · con control político={tot["n_docs_cp"]} · '
          f'citaciones={tot["n_citaciones"]} · menciones de citante={tot["n_citantes_menciones"]} '
          f'(casan con roster {tot["n_citantes_con_roster"]})')


if __name__ == '__main__':
    main()
