#!/usr/bin/env python3
"""
Enriquece el crudo de harvest.py (pdly/lys/pal/actos .jsonl) al dataset que
consume el producto Cauce. Deriva campos que el frontend/Lambda necesitan y
que sería caro recalcular en cada request:

  - fechas parseadas + validadas (descarta typos con años imposibles)
  - resultado normalizado: LEY | ARCHIVADO_TIEMPO | ARCHIVADO_OTRO | RETIRADO
                           | EN_TRAMITE | OTRO
  - es_ley, murio_por_tiempo (Art. 190)
  - etapa_max: hasta dónde llegó en el trámite (0 presentado … 5 ley)
  - dias_a_primer_debate
  - autores: lista separada + n_autores (para el futuro join autor→partido)
  - gacetas: lista estructurada [{tipo, numero, url}] desde las 6 filas de docs

Salidas (en Bases de datos/leyes-senado/dist/, listo para S3 privado):
  proyectos.jsonl   pdly enriquecido, 1 registro/línea  (backend/Lambda)
  leyes.jsonl       lys enriquecido
  actos-legis.jsonl pal + actos enriquecido
  indice.json       índice compacto de TODO (búsqueda rápida en memoria)
  stats.json        agregados precalculados (embudo, resultados por año/comisión)

Uso: python3 tools/leyes-senado/build_dataset.py
"""
import json
import re
import sys
import datetime
from pathlib import Path
from collections import Counter, defaultdict

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
DIST = SRC / 'dist'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalize_autores as na  # noqa: E402
import clasificar as cl  # noqa: E402
import camara_merge as cam  # noqa: E402

# registro de Cámara (harvest_camara_historico.py). Si no existe, el dataset sale
# solo con el Senado — que es como vivió Caudal hasta jul-2026.
CAMARA_JSONL = SRC / 'camara' / 'camara.jsonl'

# Radicados de la LEGISLATURA EN CURSO, que el cron diario (run_diario.sh) baja
# 2x/día. Sin esto la legislatura viva no existe en el dataset: harvest.py (el
# histórico) se corre a mano cada tanto, y medido el 2026-08-02 pdly.jsonl se
# cortaba en el id 9923 con CERO proyectos de 2026-2027 mientras el cron ya
# tenía 139 de Senado y 71 de Cámara — justo los proyectos que le importan a un
# cliente que paga hoy. El shape del diario de Senado ES el crudo de
# parse_detalle, así que entra al pipeline como uno más, sin volver a la red.
DIARIO_SEN = SRC / 'diario'
DIARIO_CAM = SRC / 'diario-camara'

# registro global de autores (clave→display); se llena en main() antes de enrich
AUTOR_REG = {}

MESES = 366 * 250  # sanity cap irrelevante; placeholder


def pdate(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            d = datetime.datetime.strptime(s[:10], fmt).date()
            if 1985 <= d.year <= 2027:
                return d
        except ValueError:
            pass
    return None


def norm_resultado(estado):
    e = (estado or '').upper()
    if e.startswith('LEY') or 'SANCION' in e:
        return 'LEY'
    if 'RETIR' in e:
        return 'RETIRADO'
    if 'ARCHIV' in e and '190' in e:
        return 'ARCHIVADO_TIEMPO'
    if 'ARCHIV' in e:
        return 'ARCHIVADO_OTRO'
    if any(k in e for k in ('PENDIENTE', 'TRAMITE', 'PONENCIA', 'DEBATE', 'DISCUTIR')):
        return 'EN_TRAMITE'
    return 'OTRO' if e else 'SIN_DATO'


# separa "H.S. NOMBRE UNO, NOMBRE DOS, H.R. NOMBRE TRES." en nombres individuales
AUTOR_PREF = re.compile(r'\b(H\.?\s?[SR]\.?|HONORABLE|SENADOR(?:A)?|REPRESENTANTE|MIN(?:ISTRO|ISTERIO)?(?:\s+DE[^,]*)?)\.?\s*', re.I)


def split_autores(autor):
    if not autor:
        return []
    txt = autor.strip().rstrip('.')
    # corta por coma o " Y " pero deja nombres compuestos razonables
    partes = re.split(r'\s*,\s*|\s+Y\s+(?=[A-ZÁÉÍÓÚÑ])', txt)
    out = []
    for p in partes:
        p = AUTOR_PREF.sub('', p).strip(' .')
        p = re.sub(r'\s+', ' ', p)
        if len(p) >= 4 and not p.isdigit():
            out.append(p.title())
    # dedup preservando orden
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


DOC_FIELDS = [
    ('exposicion_de_motivos', 'exposicion_motivos'),
    ('primera_ponencia', 'ponencia_1'),
    ('segunda_ponencia', 'ponencia_2'),
    ('texto_plenaria', 'texto_plenaria'),
    ('conciliacion', 'conciliacion'),
    ('objeciones', 'objeciones'),
]
GACETA_RE = re.compile(r'(\d{1,4})\s*/\s*(\d{2,4})')


def extract_gacetas(rec):
    out = []
    for field, tipo in DOC_FIELDS:
        val = (rec.get(field) or '').strip()
        if not val:
            continue
        m = GACETA_RE.search(val)
        numero = None
        if m:
            yy = m.group(2)
            anio = ('20' if int(yy) <= 27 else '19') + yy if len(yy) == 2 else yy
            numero = f'{int(m.group(1))}/{anio}'
        out.append({'tipo': tipo, 'gaceta': numero, 'texto': val,
                    'url': rec.get(f'{field}_url', '')})
    return out


def _autores_canon(raw):
    """Campo autor crudo → autores canónicos + keys + tipo, usando AUTOR_REG."""
    p = na.procesar_campo(raw)
    if p['tipo'] == 'institucional':
        return {'autor_tipo': 'institucional', 'entidad': p['entidad'],
                'autores': [], 'autores_keys': []}
    disp = [AUTOR_REG.get(k, {}).get('display', d) for k, d in p['personas']]
    return {'autor_tipo': 'persona', 'entidad': None,
            'autores': disp, 'autores_keys': [k for k, _ in p['personas']]}


ETAPAS = [
    ('presentado', 'fecha_de_presentacion'),
    ('1er_debate_senado', 'fecha_de_aprobacion_primer_debate'),
    ('2do_debate_senado', 'fecha_de_aprobacion_segundo_debate'),
    ('1er_debate_camara', 'fecha_de_aprobacion_primer_debate_camara'),
    ('2do_debate_camara', 'fecha_de_aprobacion_segundo_debate_camara'),
]


def enrich_pdly(rec):
    res = norm_resultado(rec.get('estado', ''))
    fpres = pdate(rec.get('fecha_de_presentacion', ''))
    es_camara = rec.get('_origen_registro') == 'camara'
    # nº de debates con fecha de aprobación, sin importar en qué cámara — es la
    # medida que vale para los DOS orígenes. Para un proyecto de Cámara el
    # primer debate ocurre en Cámara, así que leer la posición del campo (como
    # hace `etapas` abajo, que asume el orden Senado→Cámara) le daría etapa 3
    # por haber pasado UN debate.
    n_debates = sum(1 for _, k in ETAPAS[1:] if pdate(rec.get(k, '')))
    if es_camara:
        # en Cámara el hito de aprobación casi nunca viene fechado; se cuenta por
        # evidencia (acta fechada, texto aprobado o ponencia del debate
        # siguiente). Ver camara_merge._evidencia_aprobacion: contar solo fechas
        # daba 98,3% de muertes antes del primer debate, que era el parser.
        n_debates = max(n_debates, rec.get('_n_debates_ficha', 0))
    # primer debate en el orden real de SU trámite
    orden = (['fecha_de_aprobacion_primer_debate_camara',
              'fecha_de_aprobacion_segundo_debate_camara',
              'fecha_de_aprobacion_primer_debate',
              'fecha_de_aprobacion_segundo_debate'] if es_camara else
             [k for _, k in ETAPAS[1:]])
    f1 = next((pdate(rec.get(k, '')) for k in orden if pdate(rec.get(k, ''))), None)

    etapa_max = 0
    for idx, (_, k) in enumerate(ETAPAS):
        if pdate(rec.get(k, '')):
            etapa_max = idx
    if es_camara:
        etapa_max = n_debates
    if res == 'LEY':
        etapa_max = 5
    # piso: lo que el estado textual declara (para los de Cámara sin fechas de
    # debate en la ficha — ver camara_merge._ETAPA_POR_ESTADO)
    etapa_max = max(etapa_max, rec.get('_etapa_hint', 0))
    leg = rec.get('legislatura', '')
    anio = int(leg[:4]) if leg[:4].isdigit() else (fpres.year if fpres else None)
    canon = _autores_canon(rec.get('autor', ''))
    titulo = rec.get('titulo', '')
    return {
        'id': rec['id'],
        'tabla': 'pdly',
        'titulo': titulo,
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'legislatura': leg,
        'cuatrienio': rec.get('cuatrenio', ''),
        'anio': anio,
        'origen': rec.get('origen', ''),
        'origen_registro': rec.get('_origen_registro', 'senado'),
        'tipo_de_ley': rec.get('tipo_de_ley', ''),
        'comision': rec.get('comision', ''),
        'autor_raw': rec.get('autor', ''),
        **canon,
        **cl.autoria('pdly', canon['autores'], canon['autor_tipo']),
        **cl.clasificar_titulo(titulo),
        'reloj': cl.reloj_de('pdly'),
        'estado': rec.get('estado', ''),
        'resultado': res,
        'es_ley': res == 'LEY',
        'murio_por_tiempo': res == 'ARCHIVADO_TIEMPO',
        'etapa_max': etapa_max,
        'n_debates_aprobados': n_debates,
        # con qué se sostiene cada aprobación (solo Cámara; en Senado siempre es
        # la fecha del registro). {debate: fecha_acta|texto_aprobado|ponencia_siguiente}
        'debates_evidencia': rec.get('_debates_evidencia') or {},
        # 'senado' | 'camara_ficha' | None. Declara de dónde salió la fecha, para
        # que nadie tenga que adivinar si un None es "no pasó" o "no se sabe".
        'fecha_fuente': ('senado' if not es_camara else
                         ('camara_ficha' if rec.get('_ficha_ok') else None)) if fpres else None,
        'texto_s3': rec.get('_texto_s3'),
        'fecha_presentacion': fpres.isoformat() if fpres else None,
        'fecha_primer_debate': f1.isoformat() if f1 else None,
        'dias_a_primer_debate': (f1 - fpres).days if (fpres and f1 and f1 >= fpres) else None,
        'ponentes': [rec.get(k, '') for k in
                     ('ponente_primer_debate', 'ponente_segundo_debate',
                      'ponente_primer_debate_camara', 'ponente_segundo_debate_camara')
                     if rec.get(k, '').strip()],
        'gacetas': extract_gacetas(rec),
    }


def enrich_pal(rec):
    """Proyectos de acto legislativo (reformas constitucionales, doble vuelta).
    Enriquecido más liviano que pdly — comparten título/autor/estado."""
    res = norm_resultado(rec.get('estado', ''))
    leg = rec.get('legislatura', '')
    anio = int(leg[:4]) if leg[:4].isdigit() else None
    # etapa_max de un acto legislativo = nº de debates aprobados (hasta 8, doble
    # vuelta). Es la señal que pide el experto para el AL "radicado cada semestre
    # con 1 o 0 debates" (vitrina). Cuenta cualquier fecha_de_aprobacion_* válida.
    n_debates = sum(1 for k, v in rec.items()
                    if k.startswith('fecha_de_aprobacion') and pdate(v))
    etapa_max = 5 if res == 'LEY' else min(n_debates, 5)
    etapa_max = max(etapa_max, rec.get('_etapa_hint', 0))  # ver enrich_pdly
    canon = _autores_canon(rec.get('autor', ''))
    titulo = rec.get('titulo', '')
    return {
        'id': rec['id'], 'tabla': 'pal',
        'titulo': titulo,
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'legislatura': leg, 'cuatrienio': rec.get('cuatrenio', ''), 'anio': anio,
        'origen': rec.get('origen', ''),
        'origen_registro': rec.get('_origen_registro', 'senado'),
        'comision': rec.get('comision', ''),
        'autor_raw': rec.get('autor', ''),
        **canon,
        **cl.autoria('pal', canon['autores'], canon['autor_tipo']),
        **cl.clasificar_titulo(titulo),
        'reloj': cl.reloj_de('pal'),
        'estado': rec.get('estado', ''),
        'resultado': res, 'es_ley': res == 'LEY',
        'murio_por_tiempo': res == 'ARCHIVADO_TIEMPO',
        'etapa_max': etapa_max, 'n_debates_aprobados': n_debates,
        'fecha_fuente': ('camara_ficha' if rec.get('_ficha_ok') else 'senado')
                        if rec.get('fecha_de_presentacion') else None,
        'texto_s3': rec.get('_texto_s3'),
        'fecha_presentacion': (pdate(rec.get('fecha_de_presentacion', '')) or '')
                              and pdate(rec.get('fecha_de_presentacion', '')).isoformat(),
        'gacetas': extract_gacetas(rec),
    }


def enrich_lys(rec):
    return {
        'id': rec['id'], 'tipo': 'ley_sancionada',
        'titulo': rec.get('titulo', ''),
        'numero_ley': rec.get('numero_ley', ''),
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'origen': rec.get('origen', ''),
        'fecha_sancion': (pdate(rec.get('fecha_de_sancion', '')) or '') and
                         pdate(rec.get('fecha_de_sancion', '')).isoformat(),
        'presidente_congreso': rec.get('presidente_del_congreso', ''),
        'proyecto_ref_id': rec.get('numero_senado_ref_id') or rec.get('numero_camara_ref_id'),
    }


def load(name):
    p = SRC / f'{name}.jsonl'
    return [json.loads(l) for l in open(p, encoding='utf-8')] if p.exists() else []


# ------------------------------------------------- legislatura en curso (cron)

def _slug_num(txt):
    """'001/26' → '001-26' (misma normalización que build_diario_s3.slug, que es
    la que nombró los objetos ya subidos a S3)."""
    import unicodedata as _u
    t = _u.normalize('NFKD', txt or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', t).strip('-').upper()


def cargar_vivos_senado():
    """Radicados de la legislatura viva ya cosechados por harvest_diario.py.

    Vienen con el mismo shape crudo que pdly.jsonl, más la llave del texto del
    radicado (que el cron ya subió a s3://caudal-legislativo/radicados-texto/).
    Esa llave viaja hasta el proyecto enriquecido como `texto_s3` para que
    build_texto_index no tenga que adivinar nombres de archivo."""
    out = []
    for p in sorted(DIARIO_SEN.glob('*/proyectos.jsonl')):
        leg = p.parent.name
        for line in p.open(encoding='utf-8'):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get('tabla', 'pdly') != 'pdly':
                continue
            nombre = f"PL-{_slug_num(r.get('numero_senado', ''))}"
            if (p.parent / 'textos-txt' / f'{nombre}.txt').exists():
                r['_texto_s3'] = f'radicados-texto/{leg}/{nombre}.txt'
                r['_texto_local'] = str(p.parent / 'textos-txt' / f'{nombre}.txt')
            r['_origen_registro'] = 'senado'
            r['_vivo'] = True
            out.append(r)
    return out


def cargar_vivos_camara():
    """Ídem para Cámara. El shape del cron es el del listado AJAX pero con los
    campos ya desempacados (autores/comisiones como listas), así que se re-arma
    el 'pack' que espera camara_merge en vez de duplicar su lógica de mapeo."""
    out = []
    for p in sorted(DIARIO_CAM.glob('*/proyectos.jsonl')):
        leg = p.parent.name
        for line in p.open(encoding='utf-8'):
            if not line.strip():
                continue
            r = json.loads(line)
            aut = r.get('autores') or []
            com = r.get('comisiones') or []
            it = {
                'nro_camara': r.get('numero_camara'), 'nro_senado': r.get('numero_senado'),
                'titulo': r.get('titulo'), 'tipo': r.get('tipo'), 'estado': r.get('estado'),
                'origen': r.get('origen'), 'link_web': r.get('link_web'),
                'legislatura': r.get('legislatura') or leg,
                'otros_autores': r.get('otros_autores'),
                'autores_pack': '::'.join(
                    f"{a.get('id','')}||{a.get('nombre','')}||{a.get('ref','')}"
                    for a in aut if isinstance(a, dict)),
                'comisiones_pack': '::'.join(
                    f"||{c}||" if isinstance(c, str)
                    else f"{c.get('id','')}||{c.get('nombre','')}||" for c in com),
            }
            nombre = f"PLC-{_slug_num(r.get('numero_camara', ''))}"
            if (p.parent / 'textos-txt' / f'{nombre}.txt').exists():
                it['_texto_s3'] = f'radicados-camara-texto/{leg}/{nombre}.txt'
                it['_texto_local'] = str(p.parent / 'textos-txt' / f'{nombre}.txt')
            out.append(it)
    return out


def _titulo_cambio(a, b):
    """¿b (título de sanción) es un nombre distinto de a (título de radicación)?
    Reusa la firma de titulo_signature (tokens significativos, sin boilerplate
    legal) y compara solapamiento Jaccard — no una comparación de string cruda,
    porque 'por la cual' vs 'por medio de la cual' no debe contar como cambio."""
    sa, sb = cl.titulo_signature(a), cl.titulo_signature(b)
    if not sa or not sb:
        return False
    jac = len(sa & sb) / len(sa | sb)
    return jac < 0.45


def _link_titulos_alt(pdly, lys):
    """Un proyecto puede sancionarse con un título distinto al de radicación
    (frecuente tras ponencia/conciliación en 2º-3er debate). lys.proyecto_ref_id
    ya cruza cada ley con el pdly que le dio origen — de ahí sale el alias, sin
    scrapear nada nuevo. Guarda 'titulos_alt' en el pdly para que la búsqueda lo
    encuentre por cualquiera de los dos nombres."""
    by_id = {r['id']: r for r in pdly}
    for l in lys:
        ref = l.get('proyecto_ref_id')
        p = by_id.get(ref)
        if not p or not l.get('titulo'):
            continue
        if _titulo_cambio(p['titulo'], l['titulo']):
            p.setdefault('titulos_alt', []).append({
                'titulo': l['titulo'], 'motivo': 'nombre de sanción (Ley)',
                'numero_ley': l.get('numero_ley', '')})
    for r in pdly:
        r.setdefault('titulos_alt', [])


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    raw_pdly, raw_pal = load('pdly'), load('pal')

    # 0) une el registro de CÁMARA (los que nunca cruzaron al Senado). Va ANTES
    #    del registro de autores y de los clusters para que todo el pipeline
    #    (canon de autores, re-radicación, tipología) los vea. Ver camara_merge.
    # 0a) legislatura EN CURSO desde el cron diario, ANTES del merge de Cámara
    #     (para que la dedup por número+título los vea como cualquier otro).
    vivos_sen = cargar_vivos_senado()
    ya = {r['id'] for r in raw_pdly}
    nuevos_sen = [r for r in vivos_sen if r['id'] not in ya]
    raw_pdly += nuevos_sen
    print(f'· legislatura viva (Senado): +{len(nuevos_sen)} radicados del cron '
          f'({len(vivos_sen) - len(nuevos_sen)} ya estaban en el histórico)')

    cam_info = None
    cam_rows = []
    if CAMARA_JSONL.exists():
        cam_rows = [json.loads(l) for l in open(CAMARA_JSONL, encoding='utf-8') if l.strip()]
    vivos_cam = cargar_vivos_camara()
    if vivos_cam:
        # el listado histórico se cachea por legislatura, así que la viva se le
        # queda corta; el cron la mantiene al día. La dedup de cam.merge (número
        # + título) evita que un proyecto entre dos veces.
        vistos = {(r.get('nro_camara'), r.get('legislatura')) for r in cam_rows}
        extra = [it for it in vivos_cam
                 if (it.get('nro_camara'), it.get('legislatura')) not in vistos]
        # la llave del texto se aplica a TODOS los vivos, no solo a los nuevos:
        # un proyecto que el listado histórico ya tenía cacheado igual tiene su
        # .txt bajado por el cron, y si solo se enriqueciera a los `extra` se
        # perdería (medido: los 12 de Cámara con texto quedaban fuera).
        textos = {(it['nro_camara'], it['legislatura']): it
                  for it in vivos_cam if it.get('_texto_s3')}
        for r in cam_rows:
            src = textos.get((r.get('nro_camara'), r.get('legislatura')))
            if src:
                r['_texto_s3'] = src['_texto_s3']
        cam_rows += extra
        n_txt = sum(1 for r in cam_rows if r.get('_texto_s3'))
        print(f'· legislatura viva (Cámara): +{len(extra)} del cron '
              f'(de {len(vivos_cam)} que trae el rastreo) · {n_txt} con texto de radicado')
    if cam_rows:
        fichas = cam.cargar_fichas()
        ex_pdly, ex_pal, cam_info = cam.merge(raw_pdly, raw_pal, cam_rows, fichas)
        raw_pdly += ex_pdly
        raw_pal += ex_pal
        print(f"· Cámara: +{cam_info['n_agregados_pdly']} PL  +{cam_info['n_agregados_pal']} AL"
              f"   (descartados: {cam_info['ya_en_senado']} ya en el Senado, "
              f"{cam_info['origen_senado']} de origen Senado)")
        print(f"  fichas individuales: {cam_info['n_con_ficha']} · "
              f"con fecha de radicación: {cam_info['n_con_fecha']} · "
              f"sin fecha: {cam_info['n_sin_fecha']}"
              + ('' if fichas else '  ← corre harvest_camara_fichas.py'))
    else:
        print('· Cámara: sin camara.jsonl → dataset SOLO Senado '
              '(corre harvest_camara_historico.py)')

    # 1) registro global de autores (dedup por clave canónica) ANTES de enrich
    global AUTOR_REG
    AUTOR_REG = na.construir_registro(raw_pdly + raw_pal)

    pdly = [enrich_pdly(r) for r in raw_pdly]
    pal = [enrich_pal(r) for r in raw_pal]
    lys = [enrich_lys(r) for r in load('lys')]

    # 1b) título alternativo: el nombre con el que se sancionó, si cambió
    #     respecto al de radicación (ver _link_titulos_alt / _titulo_cambio)
    _link_titulos_alt(pdly, lys)

    # 2) clusters de re-radicación (misma iniciativa en varios términos) →
    #    veces_presentado + empuje/vitrina. Corre sobre pdly + pal juntos, pero
    #    clasificar.py agrupa dentro de cada tabla.
    clusters = cl.construir_clusters(pdly + pal)
    for r in pdly + pal:
        c = clusters.get((r['tabla'], r['id']), {})
        r['veces_presentado'] = c.get('veces_presentado', 1)
        r['empuje'] = c.get('empuje', 'sin_traccion')
        r['vitrina_score'] = c.get('vitrina_score', 0)
        r['cluster_id'] = c.get('cluster_id')
        r['historial_reradicacion'] = c.get('historial', [])

    # registro de autores como salida propia (para el join autor→partido)
    autores_out = sorted(
        ({'key': k, 'display': v['display'], 'tipo': v['tipo'],
          'n_proyectos': v['n_proyectos'], 'n_variantes': v['n_variantes']}
         for k, v in AUTOR_REG.items()),
        key=lambda x: -x['n_proyectos'])
    json.dump({'v': '2026-07-11', 'n': len(autores_out), 'autores': autores_out},
              open(DIST / 'autores.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # proyectos enriquecidos
    with open(DIST / 'proyectos.jsonl', 'w', encoding='utf-8') as f:
        for r in pdly:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(DIST / 'actos-legis.jsonl', 'w', encoding='utf-8') as f:
        for r in pal:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(DIST / 'leyes.jsonl', 'w', encoding='utf-8') as f:
        for r in lys:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # índice compacto (búsqueda en memoria · frontend/Lambda) — pdly + pal
    def _ix(r, tb):
        alt = r.get('titulos_alt') or []
        return {
            'id': r['id'], 'tb': tb, 't': r['titulo'], 'a': r['anio'],
            **({'ta': ' · '.join(a['titulo'] for a in alt)} if alt else {}),
            'leg': r['legislatura'], 'com': r.get('comision', ''),
            'res': r['resultado'], 'ley': r['es_ley'], 'et': r['etapa_max'],
            'aut': r['autores'][:6], 'ak': r['autores_keys'][:6],
            'ng': len(r['gacetas']),
            # --- F1 (intención) ---
            'tip': r['tipologia'], 'cf': r['crea_fondo'], 'jp': r['jala_presupuesto_regional'],
            'emp': r['empuje'], 'vs': r['vitrina_score'], 'vp': r['veces_presentado'],
            'ap': r.get('autor_principal'),
            # 'oc':1 = viene del registro de Cámara (nunca cruzó al Senado) →
            # sin fechas de debate ni causa de archivo. Se omite si es del Senado
            # para no engordar el índice, que se carga entero en memoria.
            **({'oc': 1} if r.get('origen_registro') == 'camara' else {}),
        }
    indice = [_ix(r, 'pdly') for r in pdly] + [_ix(r, 'pal') for r in pal]
    json.dump({'v': '2026-07-11', 'n': len(indice), 'proyectos': indice},
              open(DIST / 'indice.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # stats precalculadas
    res_count = Counter(r['resultado'] for r in pdly)
    por_anio = defaultdict(lambda: Counter())
    for r in pdly:
        if r['anio']:
            por_anio[r['anio']][r['resultado']] += 1
    por_comision = defaultdict(lambda: {'total': 0, 'ley': 0})
    for r in pdly:
        c = (r['comision'] or 'SIN COMISIÓN').upper().strip()
        por_comision[c]['total'] += 1
        por_comision[c]['ley'] += r['es_ley']
    # ---------------------------------------------------------------- embudo
    # Hasta jul-2026 el embudo se calculaba SOLO sobre el registro del Senado
    # porque los 4.080 proyectos de Cámara (27% del universo) llegaban sin una
    # sola fecha. Con las fichas individuales ya cosechadas, el embudo se calcula
    # sobre TODO el que tenga fecha de radicación, y el alcance se declara con el
    # número exacto de lo que queda fuera en vez de con una etiqueta.
    #
    # `embudo` (el viejo, solo Senado) se conserva tal cual para no romper a
    # quien ya lo lee; `embudo_universo` es el bueno. La escala es la misma en
    # ambos: cuántos alcanzaron al menos N debates aprobados.
    pdly_sen = [r for r in pdly if r.get('origen_registro') == 'senado']
    embudo = {name: sum(1 for r in pdly_sen if r['etapa_max'] >= idx)
              for idx, (name, _) in enumerate(ETAPAS)}
    embudo['ley'] = sum(1 for r in pdly_sen if r['es_ley'])

    con_fecha = [r for r in pdly if r['fecha_presentacion']]
    sin_fecha = [r for r in pdly if not r['fecha_presentacion']]
    ESCALONES = ['radicado', '1er_debate', '2do_debate', '3er_debate', '4to_debate']
    embudo_uni = {name: sum(1 for r in con_fecha if r['n_debates_aprobados'] >= idx)
                  for idx, name in enumerate(ESCALONES)}
    embudo_uni['ley'] = sum(1 for r in con_fecha if r['es_ley'])
    # días al primer debate: sobre el universo con fecha, en el orden real de
    # trámite de cada proyecto (ver enrich_pdly)
    dias = sorted(r['dias_a_primer_debate'] for r in con_fecha
                  if r['dias_a_primer_debate'] is not None)
    dias_sen = sorted(r['dias_a_primer_debate'] for r in pdly_sen
                      if r['dias_a_primer_debate'] is not None)
    # Cámara no informa la CAUSA del archivo → sus archivados caen en
    # ARCHIVADO_OTRO y nunca en ARCHIVADO_TIEMPO. No es "no murió por tiempo":
    # es "la fuente no lo dice". Se expone aparte para no leer mal la mortandad.
    n_causa_nd = sum(1 for r in pdly if r.get('origen_registro') == 'camara'
                     and r['resultado'] == 'ARCHIVADO_OTRO')

    # --- F1: tipología, empuje, mortandad por año dentro del cuatrienio ---
    tip_count = Counter(r['tipologia'] for r in pdly)
    emp_count = Counter(r['empuje'] for r in pdly)
    n_fondos = sum(1 for r in pdly if r['crea_fondo'])
    n_jala = sum(1 for r in pdly if r['jala_presupuesto_regional'])

    def anio_en_cuatrienio(r):
        cu, lg = r.get('cuatrienio', ''), r.get('legislatura', '')
        if cu[:4].isdigit() and lg[:4].isdigit():
            k = int(lg[:4]) - int(cu[:4]) + 1
            return k if 1 <= k <= 4 else None
        return None

    mort = defaultdict(lambda: {'total': 0, 'archivado_tiempo': 0, 'ley': 0})
    for r in pdly:
        k = anio_en_cuatrienio(r)
        if k:
            mort[k]['total'] += 1
            mort[k]['archivado_tiempo'] += r['murio_por_tiempo']
            mort[k]['ley'] += r['es_ley']
    mortandad = {str(k): {**v,
                          'pct_muerte_tiempo': round(100 * v['archivado_tiempo'] / v['total'], 1) if v['total'] else 0,
                          'pct_ley': round(100 * v['ley'] / v['total'], 1) if v['total'] else 0}
                 for k, v in sorted(mort.items())}

    stats = {
        'v': '2026-07-29', 'n_proyectos': len(pdly), 'n_actos': len(pal),
        'n_leyes': len(lys),
        # de qué registro salió cada cosa (jul-2026: se unió Cámara al Senado)
        'por_registro': {
            'proyectos': dict(Counter(r.get('origen_registro', 'senado') for r in pdly)),
            'actos': dict(Counter(r.get('origen_registro', 'senado') for r in pal)),
        },
        'archivado_causa_no_informada': n_causa_nd,
        'embudo_alcance': 'registro_senado',
        'resultados': dict(res_count),
        'embudo': embudo,
        # el embudo bueno: universo completo (Senado + Cámara), sobre los que
        # tienen fecha de radicación. `alcance` dice exactamente qué queda fuera.
        'embudo_universo': embudo_uni,
        'embudo_universo_alcance': {
            'base': 'proyectos de ley con fecha de radicación (Senado + Cámara)',
            'n_con_fecha': len(con_fecha),
            'n_sin_fecha': len(sin_fecha),
            'n_total': len(pdly),
            'pct_cubierto': round(100 * len(con_fecha) / max(len(pdly), 1), 1),
            'sin_fecha_por_registro': dict(Counter(
                r.get('origen_registro', 'senado') for r in sin_fecha)),
            'fecha_fuente': dict(Counter(r.get('fecha_fuente') or 'sin_fecha'
                                         for r in pdly)),
            # con qué se sostiene cada escalón del embudo. En el Senado siempre
            # es la fecha del registro; en Cámara la ficha rara vez fecha la
            # aprobación, así que se admiten dos respaldos más — el último es
            # inferencia procedimental (no hay ponencia de segundo debate sin
            # primero aprobado) y por eso se cuenta aparte.
            'evidencia_debates': dict(Counter(
                e for r in pdly for e in (r.get('debates_evidencia') or {}).values())),
            'nota': ('los sin fecha son proyectos cuya ficha no la publica o no '
                     'respondió; NO se estima ninguna. La causa del archivo '
                     'sigue sin venir del registro de Cámara (ver '
                     'archivado_causa_no_informada).'),
        },
        'dias_a_primer_debate': {
            'n': len(dias),
            'mediana': dias[len(dias) // 2] if dias else None,
            'p25': dias[len(dias) // 4] if dias else None,
            'p75': dias[3 * len(dias) // 4] if dias else None,
            'alcance': 'universo con fecha (Senado + Cámara)',
            'solo_senado': {
                'n': len(dias_sen),
                'mediana': dias_sen[len(dias_sen) // 2] if dias_sen else None,
            },
        },
        'por_comision': {k: v for k, v in sorted(
            por_comision.items(), key=lambda x: -x[1]['total'])},
        'por_anio': {str(a): dict(c) for a, c in sorted(por_anio.items())},
        # --- F1 (intención) ---
        'tipologia': dict(tip_count),
        'empuje': dict(emp_count),
        'n_crea_fondo': n_fondos,
        'n_jala_presupuesto_regional': n_jala,
        'mortandad_por_anio_cuatrienio': mortandad,
    }
    json.dump(stats, open(DIST / 'stats.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    n_pers = sum(1 for a in autores_out if a['tipo'] == 'persona')
    print(f'proyectos.jsonl : {len(pdly)} enriquecidos')
    print(f'leyes.jsonl     : {len(lys)}')
    print(f'indice.json     : {len(indice)} (compacto)')
    print(f'autores.json    : {n_pers} personas canónicas + {len(autores_out)-n_pers} entidades')
    print(f'stats.json      : embudo + {len(por_comision)} comisiones + {len(por_anio)} años')
    for k in ('proyectos.jsonl', 'leyes.jsonl', 'indice.json', 'autores.json', 'stats.json'):
        sz = (DIST / k).stat().st_size
        print(f'  {k:16} {sz/1024:7.1f} KB')


if __name__ == '__main__':
    main()
