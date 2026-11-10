#!/usr/bin/env python3
"""Datos de «Dónde estamos» (clima.html) partidos por ámbito: General · Bogotá · Resto del país.

Lee el mismo banco de titulares que build_clima.py (reusa su cargador y su clasificación de temas),
los delitos de la Policía del proyecto (Bases de datos/output_ponal/) y tres encuestas leídas en su fuente.
Escribe Propuestas/nuevo-liberalismo/datos/clima-ambito.json y .js.

Bogotá en el banco = titular que nombra la ciudad, sus instituciones o una localidad sin ambigüedad.
Se filtra por el TITULAR, no por el resumen: el resumen nombra Bogotá de pasada en notas que no son de Bogotá.
Se dejan fuera localidades con nombre ambiguo (Suba es también un verbo; Santa Fe, La Candelaria y
San Cristóbal existen en otros lugares; Kennedy es también un apellido; Antonio Nariño, un prócer).

Correr: python3 tools/nuevo-liberalismo/build_clima_ambito.py   (después de build_clima.py)
"""
import json, os, re, sys, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import build_clima as BC   # noqa: E402  (no corre main: está protegido)

RAIZ = os.path.join(AQUI, '..', '..')
DAT = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos')
PON = os.path.join(RAIZ, 'Bases de datos', 'output_ponal')

BOG = re.compile(r'\bbogot|\btransmilenio\b|\btransmicable\b|\bconcejo distrital\b|\bpersoneria distrital\b|'
                 r'\balcaldia mayor\b|\bdistrito capital\b|\bcarlos fernando galan\b|\balcalde galan\b|'
                 r'\busaquen\b|\bchapinero\b|\bengativa\b|\bfontibon\b|\bteusaquillo\b|\btunjuelito\b|\bbosa\b|\busme\b|'
                 r'\bciudad bolivar\b|\bbarrios unidos\b|\brafael uribe uribe\b|\bpuente aranda\b|\bsumapaz\b|'
                 r'\blos martires\b|\bpatio bonito\b|\bcorabastos\b|\bmonserrate\b|\bel campin\b|\bmetro de la 80\b|'
                 r'\blocalidad de (suba|kennedy|santa fe|san cristobal|la candelaria|antonio narino)\b')


# carreteras que nombran a Bogotá como destino («vía Medellín-Bogotá»): no son noticia de la ciudad
VIA = re.compile(r'\b(medellin|mosquera|villavicencio|tunja|girardot|la calera|choachi|honda|siberia|ibague|cali|briceno)\s+bogota\b|'
                 r'\bbogota\s+(medellin|villavicencio|tunja|girardot|la calera|choachi|honda|siberia|ibague|briceno)\b')


def es_bog(x):
    t = VIA.sub(' ', re.sub(r'\s+', ' ', BC.norm(x['t'])))
    return bool(BOG.search(t))


def resumen(G, fin, semanas):
    """Peso de cada tema, tono y medios de un subconjunto del banco."""
    G = [x for x in G if BC.INICIO <= x['d'] <= fin]
    pub = [x for x in G if x['tema'] and x['tema'] not in BC.FUERA]
    tm = collections.Counter(x['tema'] for x in pub)
    sent = collections.Counter(x['s'] or 'sin' for x in pub)
    neg_t = collections.Counter(x['tema'] for x in pub if x['s'] == 'negativo')
    med = collections.Counter(x['m'] for x in G)
    idx = {s: i for i, s in enumerate(semanas)}
    sem = [0] * len(semanas); sem_seg = [0] * len(semanas); sem_pub = [0] * len(semanas)
    for x in pub:
        i = idx.get(BC.iso(BC.lunes(x['d'])))
        if i is None: continue
        sem_pub[i] += 1
        if x['tema'] == 'seguridad': sem_seg[i] += 1
    for x in G:
        i = idx.get(BC.iso(BC.lunes(x['d'])))
        if i is not None: sem[i] += 1
    n = len(pub)
    temas = [{'k': k, 'n': v, 'pct': round(v / n, 4), 'neg': round(neg_t[k] / v, 3)} for k, v in tm.most_common()]
    return {'n': len(G), 'n_pub': n, 'temas': temas,
            'tono': {k: round(sent[k] / n, 3) for k in ('negativo', 'neutro', 'positivo')} if n else {},
            'medios': [[m, c] for m, c in med.most_common()],
            'sem': sem, 'sem_pub': sem_pub, 'sem_seg': sem_seg}


def ejemplos(G, fin, k=12):
    G = sorted([x for x in G if BC.INICIO <= x['d'] <= fin and x['tema'] and x['tema'] not in BC.FUERA],
               key=lambda x: -x['d'].toordinal())
    por = collections.defaultdict(list)
    for x in G:
        if len(por[x['tema']]) < 3: por[x['tema']].append(x)
    fmt = lambda x: {'t': x['t'], 'm': x['m'], 'd': BC.iso(x['d']), 'u': x['u'], 's': x['s'], 'tema': x['tema']}
    return {'recientes': [fmt(x) for x in G[:k]], 'por_tema': {t: [fmt(x) for x in v] for t, v in por.items()}}


def policia():
    meta = json.load(open(os.path.join(PON, 'meta.json'), encoding='utf-8'))
    mun = json.load(open(os.path.join(PON, 'municipios.json'), encoding='utf-8'))
    nac = json.load(open(os.path.join(PON, 'nacional.json'), encoding='utf-8'))
    mes = json.load(open(os.path.join(PON, 'ciudades-mes', '11001.json'), encoding='utf-8'))
    anios = mun['anios']; bog = mun['muns']['11001']['d']
    lbl = {d['id']: d['label'] for d in meta['delitos']}
    # delitos con año completo en la fuente (amenazas y delitos sexuales tienen ~50 % de hechos sin año: fuera)
    DEL = ['homicidios', 'hurto_personas', 'hurto_celulares', 'lesiones', 'extorsiones', 'hurto_residencias', 'hurto_motos', 'hurto_autos']
    i18 = anios.index(2018); i25 = anios.index(2025)
    serie = {d: {'n': lbl.get(d, d), 'bog': bog[d]['y'][i18:i25 + 1],
                 'nac': nac['por_anio'][d][i18:i25 + 1] if d in nac['por_anio'] else None} for d in DEL if d in bog}
    # año corrido ene-ago 2025 vs ene-ago 2026 en Bogotá (SIEDCO mensual; la ciudad entera, no por localidad)
    M = mes['meses']; c = mes['ciudad']
    i_a = [M.index(f'2025-{m:02d}') for m in range(1, 9)]; i_b = [M.index(f'2026-{m:02d}') for m in range(1, 9)]
    ytd = {d: {'n': lbl.get(d, d), 'a': sum(c[d][i] for i in i_a), 'b': sum(c[d][i] for i in i_b)} for d in DEL if d in c}
    ytd_nac = {d: {'a': nac['ytd']['por_delito'][d][anios.index(2025)], 'b': nac['ytd']['por_delito'][d][anios.index(2026)]}
               for d in DEL if d in nac['ytd']['por_delito']}
    return {'anios': list(range(2018, 2026)), 'serie': serie, 'ytd': ytd, 'ytd_nac': ytd_nac,
            'fuente': meta['fuente'], 'corte': meta['anio_parcial'],
            'nota': 'Hechos registrados por la Policía (denuncias y casos de oficio), no victimización. '
                    'El hurto depende de que la gente denuncie. Amenazas y delitos sexuales quedan fuera: '
                    'cerca de la mitad de sus registros llega sin año.'}


ENCUESTAS = {
    'invamer': {'nombre': 'Invamer · Colombia Opina', 'para': 'Noticias Caracol y Blu Radio', 'campo': '13 al 20 de mayo de 2026',
                'muestra': '3.800 encuestas en 152 municipios', 'url': 'https://www.infobae.com/colombia/2026/05/24/encuesta-invamer-marca-el-pulso-electoral-en-colombia-la-violencia-lidera-las-preocupaciones-rumbo-a-las-presidenciales/',
                'urgentes': [['Salud', 0.719], ['Inseguridad', 0.618]],
                'principal_orden_publico': 0.408, 'estado_perdio_presencia': 0.738, 'mal_camino': 0.522,
                'nota': 'Asuntos más urgentes para el próximo gobierno: respuesta múltiple, por eso no suma 100. '
                        'Como principal problema, una sola respuesta, el orden público queda primero con 40,8 %.'},
    'bcv': {'nombre': 'Bogotá Cómo Vamos · Encuesta de Percepción Ciudadana 2025', 'publicada': '4 de diciembre de 2025',
            'muestra': '1.500 entrevistas presenciales',
            'url': 'https://bogotacomovamos.org/la-percepcion-de-inseguridad-aumenta-en-bogota-mientras-los-jovenes-lideran-el-optimismo-ciudadano-revela-la-encuesta-de-percepcion-ciudadana-2025/',
            'inseg_ciudad': 0.62, 'inseg_barrio': 0.43, 'gestion': 0.26, 'gestion_prev': 0.42, 'imagen': 0.55, 'imagen_prev': 0.61,
            'confianza': 0.177, 'confianza_prev': 0.123, 'satisfaccion': 0.61, 'tm_robos': 0.637},
    'guarumo': {'nombre': 'Guarumo y EcoAnalítica', 'campo': '22 al 29 de abril de 2026', 'muestra': '664 entrevistas en Bogotá (margen 4,5 %)',
                'url': 'https://www.eltiempo.com/politica/partidos-politicos/encuesta-guarumo-de-abril-2026-alejandro-char-federico-gutierrez-y-carlos-galan-los-alcaldes-con-mayor-aprobacion-3552168',
                'aprob': 0.533, 'desaprob': 0.393},
}


def main():
    D, _, _ = BC.cargar()
    clima = json.load(open(os.path.join(DAT, 'clima.json'), encoding='utf-8'))
    fin = BC.dt.date.fromisoformat(clima['cobertura']['fin'])
    semanas = clima['agenda']['semanas']
    bog = [x for x in D if es_bog(x)]
    resto = [x for x in D if not es_bog(x)]
    out = {'v': '2026-11-10', 'fin': BC.iso(fin), 'semanas': semanas,
           'filtro': 'Titular que nombra Bogotá, TransMilenio, instituciones del Distrito, al alcalde Carlos Fernando Galán o una localidad de nombre inequívoco.',
           'general': resumen(D, fin, semanas), 'bogota': resumen(bog, fin, semanas), 'resto': resumen(resto, fin, semanas),
           'ej_bogota': ejemplos(bog, fin), 'policia': policia(), 'encuestas': ENCUESTAS,
           'nacionales': sorted(BC.NACIONALES)}
    p = os.path.join(DAT, 'clima-ambito.json')
    txt = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    open(p, 'w', encoding='utf-8').write(txt)
    open(os.path.join(DAT, 'clima-ambito.js'), 'w', encoding='utf-8').write(f"window.NLD=window.NLD||{{}};window.NLD['clima-ambito']={txt};\n")
    for k in ('general', 'bogota', 'resto'):
        r = out[k]; print(k, r['n'], 'públicos', r['n_pub'], [(t['k'], round(t['pct'] * 100, 1)) for t in r['temas'][:6]], r['tono'])
    print('medios Bogotá', out['bogota']['medios'][:6])
    pol = out['policia']; print('homicidios Bogotá', pol['serie']['homicidios']['bog'], 'ytd', pol['ytd']['homicidios'])
    print('hurto personas', pol['serie']['hurto_personas']['bog'], 'ytd', pol['ytd']['hurto_personas'])
    print(round(len(txt) / 1024), 'KB')


if __name__ == '__main__':
    main()
