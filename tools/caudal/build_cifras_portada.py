#!/usr/bin/env python3
"""
Cifras y fuentes de las diez categorías de Caudal → caudal-cifras.js

La portada (caudal-portada.html, caudal-pronto.html) y el inicio de caudal.html
llevaban cada cifra escrita a mano en un arreglo PILLARS, y se quedaban viejas
sin que nada fallara: el 2-nov-2026 la portada decía 6,03 M contratos cuando la
fuente iba en 5,68 M, 499 providencias cuando eran 10.861 y «9/10 categorías
activas» con las diez marcadas como activas.

Este script mide todo contra el dato y escribe `caudal-cifras.js`
(window.CAUDAL_CIFRAS), que las tres páginas leen encima de su respaldo:

  · La API de Caudal (acciones stats · sanciones · control · ejecutivo · sucop ·
    gacetas · territorial · diario-oficial · contratacion).
  · Los índices locales del Congreso (proyectos y actos legislativos).
  · El catálogo de entidades (`Bases de datos/caudal-entidades/dist/`): qué lee
    Caudal de cada entidad y en qué estado está. Es lo que alimenta la lista de
    fuentes de cada tarjeta.
  · El diccionario de voceros (caudal-voceros.js).

Lo que el público ve de cada entidad es su nombre, su estado y qué se lee; las
notas internas del catálogo no salen de aquí.

Uso:  python3 tools/caudal/build_cifras_portada.py [--dry-run]
"""
import json, os, re, sys, urllib.request
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BD = os.path.join(ROOT, 'Bases de datos')
OUT = os.path.join(ROOT, 'caudal-cifras.js')
API = 'https://rr-auth.reruizc.workers.dev/caudal/api'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) caudal-cifras/1.0'

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']


def api(action, **kw):
    body = json.dumps({'action': action, **kw}).encode()
    req = urllib.request.Request(API, data=body, headers={
        'Content-Type': 'application/json', 'Origin': 'https://ricardoruiz.co', 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    if isinstance(d, dict) and d.get('error'):
        raise RuntimeError(f'{action}: {d["error"]}')
    return d


def contar(path):
    with open(path, encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())


def mil(n):
    return f'{int(n):,}'.replace(',', '.')


def millones(n):
    return f'{n / 1e6:.2f}'.replace('.', ',') + ' M'


def fecha_larga(iso):
    a, m, d = (int(x) for x in iso[:10].split('-'))
    return f'{d} de {MESES[m - 1]} de {a}'


# ── Catálogo de entidades ─────────────────────────────────────────────────────
CAT_DIR = os.path.join(BD, 'caudal-entidades', 'dist')
CAT = {e['k']: e for e in json.load(open(os.path.join(CAT_DIR, 'entidades-catalogo.json')))['entidades']}
EST = json.load(open(os.path.join(CAT_DIR, 'entidades-stats.json')))
AGENDA = json.load(open(os.path.join(CAT_DIR, 'agenda-regulatoria-stats.json')))

CORTO = {
    'ssf': 'Supersubsidio', 'supersalud': 'Supersalud', 'sic': 'SIC', 'supervigilancia': 'Supervigilancia',
    'supersociedades': 'Supersociedades', 'superfinanciera': 'Superfinanciera', 'ugpp': 'UGPP',
    'mintrabajo': 'MinTrabajo', 'minvivienda': 'MinVivienda', 'minsalud': 'MinSalud',
    'mineducacion': 'MinEducación', 'mincultura': 'MinCulturas', 'mincomercio': 'MinComercio',
    'minagricultura': 'MinAgricultura', 'minambiente': 'MinAmbiente', 'mindeporte': 'MinDeporte',
    'minhacienda': 'MinHacienda', 'dnp': 'DNP', 'funcionpublica': 'Función Pública',
    'spe': 'Servicio Público de Empleo', 'sena': 'SENA', 'cce': 'Colombia Compra Eficiente',
    'presidencia': 'Presidencia', 'dian': 'DIAN', 'mininterior': 'MinInterior',
    'mintransporte': 'MinTransporte', 'supertransporte': 'Supertransporte', 'uiaf': 'UIAF',
    'banrep': 'Banco de la República', 'corte-constitucional': 'Corte Constitucional',
    'consejo-estado': 'Consejo de Estado', 'contraloria': 'Contraloría',
    'asamblea-antioquia': 'Asamblea de Antioquia', 'concejo-medellin': 'Concejo de Medellín',
    'gobernacion-antioquia': 'Gobernación de Antioquia', 'alcaldia-medellin': 'Alcaldía de Medellín',
    'alcaldias': 'Otras alcaldías y gobernaciones',
}
# lo común a todas no se repite en cada entidad: va como fuente propia de su tarjeta
COMUN = re.compile(r'^(Diario Oficial|Agenda regulatoria 2027|Borradores en SUCOP)', re.I)


def ent(k, lee=None):
    e = CAT[k]
    cubre = [c for c in (e.get('cubre') or []) if not COMUN.match(c)]
    txt = lee or ' · '.join(cubre[:3])
    if e['estado'] != 'conectada' and e.get('falta'):
        f = e['falta'][0].split(':')[0].strip()
        txt = (txt + '. ' if txt else '') + 'Falta: ' + f[0].lower() + f[1:]
    return {'n': CORTO.get(k, e['nombre']), 'e': e['estado'], 'l': txt}


def fuente(n, l, e='conectada'):
    return {'n': n, 'e': e, 'l': l}


def main(dry=False):
    hoy = date.today().isoformat()
    sanc, ctrl, ejec = api('sanciones'), api('control'), api('ejecutivo')
    sucop, gac, terr = api('sucop'), api('gacetas'), api('territorial')
    dof, secop = api('diario-oficial'), api('contratacion')

    LS = os.path.join(BD, 'leyes-senado', 'dist')
    n_pl, n_al = contar(os.path.join(LS, 'proyectos.jsonl')), contar(os.path.join(LS, 'actos-legis.jsonl'))
    n_cong = n_pl + n_al
    anio0 = min(int(json.loads(l)['anio']) for l in open(os.path.join(LS, 'proyectos.jsonl'))
                if l.strip() and str(json.loads(l).get('anio', '')).isdigit())

    vtxt = open(os.path.join(ROOT, 'caudal-voceros.js'), encoding='utf-8').read()
    voc = json.loads(vtxt.split('=', 1)[1].strip().rstrip(';'))['meta']

    pf = EST['por_fuente']
    ministerios = ['mintrabajo', 'minvivienda', 'minsalud', 'mineducacion', 'mincultura', 'mincomercio',
                   'minagricultura', 'minambiente', 'mindeporte', 'minhacienda', 'mininterior', 'mintransporte']
    otras_ejec = ['dnp', 'funcionpublica', 'sena', 'spe']
    n_norm_min = sum(pf.get(k, {}).get('normas', 0) for k in ministerios + otras_ejec)
    con_borr = [k for k, v in pf.items() if isinstance(v, dict) and v.get('borradores')]
    n_borr_prop = sum(pf[k]['borradores'] for k in con_borr)

    n_sucop_norma = sucop['por_tipo'].get('norma', sucop['total'])
    anio_sucop = sucop['rango_fechas'][0][:4]
    terr_corp = {c['corporacion']: c for c in terr['por_corporacion']}
    gtd = pf['gacetas_territoriales']
    n_secop = secop['total']['contratos']
    n_ejec, n_decr = ejec['total'], next((t['n'] for t in ejec['por_tipo'] if t['tipo'] == 'DECRETOS'), 0)
    anio_ejec = min(int(a) for a, n in ejec['por_anio'].items() if n >= 100)

    # Actos de los reguladores: los nombres de las fuentes del registro tal como la API los publica
    reg_fuentes = sanc['fuentes']

    P = {}
    P['congreso'] = {
        'n': mil(n_cong), 'unit': f'registros · {anio0}–{hoy[:4]}',
        'desc': f'{mil(n_pl)} proyectos de ley y {mil(n_al)} actos legislativos desde {anio0}, con su trámite, '
                'sus ponentes y el voto nominal de cada congresista. Cuántas veces se intentó, por qué se cae, quién lo empuja.',
        'fuentes': [
            fuente('Senado · registro de proyectos', 'Todos los proyectos de ley y actos legislativos desde 1991, con su estado'),
            fuente('Cámara · fichas de proyectos', 'Fecha de radicación, ponentes y trámite de cada proyecto'),
            fuente('Votaciones nominales', 'API del Senado y actas de plenaria de la Cámara: cómo votó cada congresista'),
            fuente('Órdenes del día', 'Comisiones y plenarias de las dos cámaras, leídas dos veces al día'),
        ]}
    P['regulatorio'] = {
        'n': mil(sanc['total_actos']), 'unit': f'actos · {len(reg_fuentes)} fuentes',
        'desc': f'Resoluciones, circulares, conceptos y sanciones de las superintendencias y los reguladores '
                f'—{mil(sanc["total"])} de ellos sanciones—, más lo que cada superintendencia publica en su propio sitio. '
                'Cada acto cita su resolución o comunicado.',
        'fuentes': [ent(k) for k in ['ssf', 'supersalud', 'sic', 'supersociedades', 'superfinanciera',
                                     'supervigilancia', 'supertransporte', 'ugpp', 'dian', 'uiaf', 'banrep']] + [
            fuente('ANLA', 'Gaceta Ambiental: licencias, sanciones y archivos'),
            fuente('INVIMA', 'Sanciones sanitarias por sector'),
            fuente('SECOP I y II', 'Multas y sanciones contractuales impuestas por cada entidad'),
            fuente('Junta Central de Contadores', 'Sanciones disciplinarias'),
        ]}
    P['medios'] = {
        'n': '+1.800', 'unit': 'medios rastreables · en vivo',
        'desc': 'No es un listado de titulares: mide a qué ritmo crece la cobertura de un tema, quién la sostiene, en qué departamentos no se cubre — y lo contrasta con lo que el Estado está tramitando en ese mismo momento. Cualquier medio indexado en Google News Colombia (más de 1.800 observados hasta hoy), sin un conector por medio.',
        'fuentes': [
            fuente('Google News Colombia', 'Prensa nacional y regional por tema, con medio, alcance y departamento'),
            fuente('Salas de prensa oficiales', 'Comunicados de ministerios, superintendencias y Presidencia, leídos en su sitio'),
        ]}
    P['datos'] = {
        'n': millones(n_secop), 'unit': 'contratos · SECOP II',
        'desc': 'Todos los contratos electrónicos del Estado y los procesos que los preceden, consultados en vivo y '
                'actualizados a diario, más la doctrina de Colombia Compra Eficiente. Cada uno enlaza su expediente en SECOP.',
        'fuentes': [
            fuente('SECOP II · contratos', f'{mil(n_secop)} contratos electrónicos, con entidad, valor y modalidad'),
            fuente('SECOP II · procesos', 'Licitaciones y procesos abiertos antes de adjudicarse'),
            ent('cce', 'Conceptos de su relatoría, circulares y convocatorias de participación'),
        ]}
    P['control'] = {
        'n': mil(ctrl['total']), 'unit': f'providencias · Corte Constitucional desde {ctrl["cobertura"]["desde"][:4]}',
        'desc': 'Sentencias y autos de la Corte Constitucional que cambian la lectura de la norma en contratación, '
                'salud, pensiones, ambiente y elecciones, más los fallos de responsabilidad fiscal de la Contraloría. '
                'Consejo de Estado y Corte Suprema entran en el siguiente corte.',
        'fuentes': [ent('corte-constitucional', 'Sentencias y autos, con su enlace oficial'),
                    ent('contraloria'), ent('consejo-estado'),
                    fuente('Corte Suprema de Justicia', 'Sin conectar todavía', 'sin_fuente'),
                    fuente('Procuraduría', 'Sin conectar todavía', 'sin_fuente')]}
    P['ejecutivo'] = {
        'n': mil(n_ejec), 'unit': f'normas de Presidencia · desde {anio_ejec}',
        'desc': f'Decretos —{mil(n_decr)}—, leyes, directivas y circulares de la Presidencia, más las resoluciones, '
                f'conceptos y borradores que publican en su propio sitio los ministerios y departamentos '
                f'({mil(n_norm_min)} normas más) y sus agendas regulatorias 2027. Cada norma enlaza su texto oficial.',
        'fuentes': [ent('presidencia', 'Decretos, leyes y directivas del Diario Oficial y de datos.gov.co')] +
                   [ent(k) for k in ministerios + otras_ejec] + [
            fuente('Agendas regulatorias 2027', f'{mil(AGENDA["n"])} normas anunciadas por {AGENDA["agendas"]} entidades, con sus cambios día a día')]}
    P['sucop'] = {
        'n': mil(n_sucop_norma), 'unit': f'borradores · desde {anio_sucop}',
        'desc': 'Proyectos de decreto y resolución abiertos a comentarios antes de expedirse: la señal más temprana '
                f'de Caudal. Además de SUCOP, se leen los borradores que {len(con_borr)} entidades publican solo en su sitio.',
        'fuentes': [
            fuente('SUCOP · DNP', f'{mil(n_sucop_norma)} borradores desde {anio_sucop}; hoy {sucop["ventana"]["abiertas"]} abiertos a comentarios'),
            fuente('Sitios propios de las entidades',
                   f'{mil(n_borr_prop)} borradores de ' + ', '.join(CORTO.get(k, k) for k in con_borr)
                   + ', incluidos los que no pasan por SUCOP'),
        ]}
    P['gacetas'] = {
        'n': mil(gac['total']), 'unit': f'gacetas del Congreso · desde 2000',
        'desc': 'La Gaceta del Congreso enumerada y cruzada con el trámite: qué proyecto cita cada una y como qué '
                f'documento. El Diario Oficial completo —{mil(dof["total"])} actos de {dof["n_entidades"]} entidades este año— '
                'y las gacetas de Antioquia y Medellín.',
        'fuentes': [
            fuente('Gaceta del Congreso', f'{mil(gac["total"])} gacetas: exposiciones de motivos, ponencias, textos aprobados y conciliaciones'),
            fuente('Diario Oficial', f'Resoluciones, circulares y acuerdos de {dof["n_entidades"]} entidades, leídos a diario'),
            fuente('Gaceta Departamental de Antioquia', 'Decretos y resoluciones de la Gobernación'),
            fuente('Gaceta Oficial de Medellín', 'Decretos, resoluciones y circulares de la Alcaldía'),
        ]}
    P['territorial'] = {
        'n': mil(terr['n']), 'unit': 'registros · Antioquia y Medellín',
        'desc': 'La Asamblea de Antioquia y el Concejo de Medellín: proyectos con su estado, ordenanzas y acuerdos, '
                'control político y sesiones programadas; y los decretos de la Gobernación y la Alcaldía por sus gacetas. '
                'Otras gobernaciones y concejos entran después.',
        'fuentes': [ent(k) for k in ['asamblea-antioquia', 'concejo-medellin', 'gobernacion-antioquia',
                                     'alcaldia-medellin']] + [
            fuente('Otras gobernaciones y concejos', 'Se suman una a una', 'sin_fuente')]}
    P['redes'] = {
        'n': mil(voc['n']), 'unit': 'entidades y gremios · cuentas verificadas',
        'desc': 'Diccionario de cuentas oficiales del Estado, reguladores, cortes, Congreso y gremios, con el cargo que '
                'habla por cada uno. Las cuentas se leen del sitio oficial, no de memoria.',
        'fuentes': [
            fuente('Sitio oficial de cada entidad', f'{voc["verificados_sitio"]} de {voc["n"]} con las cuentas leídas de su pie de página'),
            fuente('Verificación manual', f'{voc["manual"]} entidades cuyo sitio no publica sus cuentas', 'parcial'),
        ]}

    # las fichas genéricas del catálogo («Superintendencias en general», «Alcaldías»,
    # un gremio) no son una entidad leída: no entran a la cuenta
    cat = [e for k, e in CAT.items() if k not in ('superintendencias', 'alcaldias', 'asocajas')]
    est = {s: sum(1 for e in cat if e['estado'] == s) for s in ('conectada', 'parcial', 'sin_fuente', 'no_aplica')}
    out = {
        'corte': hoy, 'corte_txt': fecha_larga(hoy),
        'hero': {'congreso': mil(n_cong), 'congreso_l': f'registros del Congreso · {anio0}–{hoy[:4]}',
                 'actos': mil(sanc['total_actos']), 'actos_l': f'actos regulatorios · {len(reg_fuentes)} fuentes',
                 'entidades': est['conectada'] + est['parcial'],
                 'entidades_l': f'entidades del Estado leídas en su fuente · {est["parcial"]} en parte'},
        'entidades': est,
        'pilares': P,
    }
    js = ('/* Generado por tools/caudal/build_cifras_portada.py — NO editar a mano: cada cifra\n'
          '   sale de la API de Caudal y del catálogo de entidades. Volver a correrlo antes de\n'
          '   presentar Caudal. */\nwindow.CAUDAL_CIFRAS = ' + json.dumps(out, ensure_ascii=False, indent=1) + ';\n')
    for k, p in P.items():
        print(f'{k:12} {p["n"]:>10}  {p["unit"]:45} {len(p["fuentes"])} fuentes')
    print('entidades', est)
    if not dry:
        open(OUT, 'w', encoding='utf-8').write(js)
        print('→', OUT)


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
