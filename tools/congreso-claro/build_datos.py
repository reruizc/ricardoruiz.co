#!/usr/bin/env python3
"""Congreso Claro · datos estáticos para el archivo y las votaciones.

La página vive fuera de ricardoruiz.co y la API de Caudal no admite otros
orígenes, así que lo que necesita del histórico se publica como JSON en S3.

  archivo.json        todos los proyectos de ley y actos legislativos 1990-2026
                      (una fila por proyecto, solo lo que la búsqueda muestra)
  votos/indice.json   congresistas con voto nominal (Senado 2017-2026, Cámara 2014-2026)
  votos/{id}.json     ficha de cada uno: totales + proyectos votados con su título real
  activos.json        proyectos EN TRÁMITE de la legislatura viva, por comisión (lo
                      refresca el cron diario con --solo-activos --subir)

Uso:  python3 tools/congreso-claro/build_datos.py [--subir] [--solo-activos]
"""
import json, re, os, sys, gzip, unicodedata, subprocess, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIST = os.path.join(RAIZ, 'Bases de datos/leyes-senado/dist')
OUT = os.path.join(RAIZ, 'Bases de datos/congreso-claro')
S3 = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/congreso-claro/'

def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9ñ ]', ' ', s)).strip()

STOP = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'h', 's', 'r', 'hs', 'hr'}
def toks(n):
    return [t for t in norm(n).split() if len(t) > 2 and t not in STOP]

def misma(a, b):
    A, B = toks(a), toks(b)
    if len(A) < 2 or len(B) < 2: return False
    c, l = (A, B) if len(A) <= len(B) else (B, A)
    return all(t in l for t in c)

PREF = re.compile(r'^\s*(por\s+(medio\s+)?(de\s+)?(la|el)\s+(cua?l|que)\s+(se\s+)?|mediante\s+(la|el)\s+cual\s+(se\s+)?)', re.I)
def titulo(t):
    s = re.sub(r'\s+', ' ', str(t or '')).strip()
    s = PREF.sub('', s)
    s = re.sub(r'\s*,?\s*y se dictan otras disposiciones\.?\s*$', '', s, flags=re.I).rstrip(' .')
    if s.upper() == s: s = s.lower()
    return (s[:1].upper() + s[1:])[:420]

def numkey(n, cam):
    """«071/92» · «458/2026C» · «200/15» → «71/92S»"""
    m = re.match(r'\s*0*(\d{1,4})\s*/\s*(?:20)?(\d{2})', str(n or ''))
    return f'{int(m.group(1))}/{m.group(2)}{cam}' if m else None

RES = ['LEY', 'ARCHIVADO_TIEMPO', 'ARCHIVADO_OTRO', 'RETIRADO', 'EN_TRAMITE', 'OTRO', 'SIN_DATO']
TIPO = ['ordinaria', 'honores', 'reforma', 'fondos', 'presupuestal']
COMS = ['primera', 'segunda', 'tercera', 'cuarta', 'quinta', 'sexta', 'septima']
def com(c):
    c = norm(c)
    for i, k in enumerate(COMS):
        if k in c: return i + 1
    return 8 if 'econom' in c else 0

def cargar_proyectos():
    L = []
    for f, acto in (('proyectos.jsonl', 0), ('actos-legis.jsonl', 1)):
        for l in open(os.path.join(DIST, f), encoding='utf-8'):
            L.append((json.loads(l), acto))
    return L

def build_archivo(L):
    filas, por_num = [], {}
    for x, acto in L:
        anio = x.get('anio')
        try: anio = int(anio)
        except (TypeError, ValueError): anio = 0
        cam = 'S' if x.get('origen_registro') == 'senado' else 'C'
        ns, nc = (x.get('numero_senado') or '').strip(), (x.get('numero_camara') or '').strip()
        num = ns if cam == 'S' and ns else (nc or ns)
        res = x.get('resultado') or 'SIN_DATO'
        try: veces = int(x.get('veces_presentado') or 1)
        except ValueError: veces = 1
        aut = re.sub(r'^(H\.?\s?[SR]\.?\s*:?\s*|MIN\.?\s*\w+\s*:\s*)', '', str(x.get('autor_principal') or '')).strip()
        try: nf = int(x.get('n_firmantes') or 0)
        except ValueError: nf = 0
        t = titulo(x.get('titulo'))
        fila = [anio, cam, num, t, RES.index(res) if res in RES else 6, com(x.get('comision')),
                TIPO.index(x.get('tipologia')) if x.get('tipologia') in TIPO else 0, veces, acto,
                aut[:60], nf, x.get('legislatura') or '']
        filas.append(fila)
        for n, c in ((ns, 'S'), (nc, 'C')):
            k = numkey(n, c)
            if k: por_num.setdefault(k, (t, res, anio))
    filas.sort(key=lambda r: (-r[0], r[1], r[2]))
    cam_desde = min((r[0] for r in filas if r[1] == 'C' and r[0]), default=0)
    meta = {'v': json.load(open(os.path.join(DIST, 'stats.json'))).get('v'), 'n': len(filas),
            'desde': min(r[0] for r in filas if r[0]), 'hasta': max(r[0] for r in filas),
            'camara_desde': cam_desde,
            'campos': ['anio', 'camara', 'numero', 'titulo', 'resultado', 'comision', 'tipologia',
                       'veces_presentado', 'acto_legislativo', 'autor_principal', 'n_firmantes', 'legislatura'],
            'resultados': RES, 'tipologias': TIPO}
    return {'meta': meta, 'p': filas}, por_num

def build_activos(L, legislatura):
    """Proyectos EN TRÁMITE de la legislatura viva, por comisión y cámara de origen."""
    out = {k.upper(): {'senado': [], 'camara': []} for k in COMS}
    out['SIN_COMISION'] = {'senado': [], 'camara': []}
    for x, acto in L:
        if x.get('legislatura') != legislatura or x.get('resultado') != 'EN_TRAMITE':
            continue
        cam = 'senado' if x.get('origen_registro') == 'senado' else 'camara'
        c = com(x.get('comision'))
        k = COMS[c - 1].upper() if 1 <= c <= 7 else 'SIN_COMISION'
        num = (x.get('numero_senado') if cam == 'senado' else x.get('numero_camara')) or x.get('numero_camara') or x.get('numero_senado') or ''
        try: nf = int(x.get('n_firmantes') or 0)
        except ValueError: nf = 0
        aut = re.sub(r'^(H\.?\s?[SR]\.?\s*:?\s*)', '', str(x.get('autor_principal') or '')).strip()
        out[k][cam].append([num.strip(), titulo(x.get('titulo')), x.get('estado') or '', (x.get('fecha_presentacion') or '')[:10],
                            'acto' if acto else (x.get('tipo_de_ley') or '').lower(), nf, aut[:60]])
    for v in out.values():
        for lst in v.values():
            lst.sort(key=lambda r: r[3], reverse=True)
    n = sum(len(l) for v in out.values() for l in v.values())
    return {'v': json.load(open(os.path.join(DIST, 'stats.json'))).get('v'), 'generado': __import__('datetime').date.today().isoformat(),
            'legislatura': legislatura, 'n': n,
            'campos': ['numero', 'titulo', 'estado', 'fecha', 'tipo', 'n_firmantes', 'autor_principal'], 'comisiones': out}

def electos():
    src = open(os.path.join(RAIZ, 'legislativo-electos.js'), encoding='utf-8').read()
    raw = json.loads(re.search(r'ELECTOS_RAW=(\[.*?\]);', src, re.S).group(1))
    return [{'corp': 'Senado' if r[0] == 'S' else 'Cámara', 'nombre': r[1], 'partido': r[2], 'dep': r[3]} for r in raw]

def nice(n):
    n = str(n or '').strip()
    return n.lower().title() if n.upper() == n else n

def slug(n):
    return re.sub(r'-+', '-', norm(n).replace(' ', '-'))[:70]

def build_votos(por_num):
    E = electos()
    personas = []
    for f, cam, letra in (('votaciones-senado-congresista.json', 'Senado', 'S'),
                          ('votaciones-camara-congresista.json', 'Cámara', 'C')):
        d = json.load(open(os.path.join(DIST, 's3', f), encoding='utf-8'))['por_congresista']
        for v in d.values():
            proys = []
            for p in v.get('por_proyecto') or []:
                num = p.get('numero_senado') if letra == 'S' else p.get('numero_camara')
                k = numkey(num or p.get('tk'), letra)
                t, res, anio = por_num.get(k, (None, None, None))
                if not t:
                    t = titulo(p.get('titulo')) or f'Proyecto {num}'
                r = p.get('r') or {}
                pos = (p.get('pos') or {}).get('pos') if letra == 'C' else None
                proys.append([t, f'{num} {cam}' if num else '', anio or 0, res or '', r.get('Si', 0),
                              r.get('No', 0), r.get('Abstencion', 0) + r.get('Abst', 0), pos or '', p.get('n', 0)])
            proys.sort(key=lambda q: (-q[8], -q[2]))
            fechas = sorted(x.get('f') for p in v.get('por_proyecto') or [] for x in p.get('v') or [] if x.get('f'))
            res = v.get('resumen') or {}
            personas.append({'nombre': v.get('nombre'), 'bancada': v.get('bancada') or '', 'camara': cam,
                             'n_votos': v.get('n_votos', 0), 'n_proyectos': v.get('n_proyectos', 0),
                             'si': res.get('Si', 0), 'no': res.get('No', 0),
                             'otros': sum(n for k, n in res.items() if k not in ('Si', 'No')),
                             'alin': v.get('alineacion_gob'), 'n_cont': v.get('n_contestadas', 0),
                             'posiciones': v.get('posiciones'), 'desde': fechas[0][:4] if fechas else None,
                             'proyectos': proys[:120], 'n_proy_total': len(proys)})
    # una persona puede tener récord en las dos cámaras
    grupos = []
    for p in personas:
        g = next((g for g in grupos if misma(g[0]['nombre'], p['nombre'])), None)
        (g.append(p) if g else grupos.append([p]))
    indice, fichas = [], {}
    usados = set()
    for g in grupos:
        e = next((e for e in E if any(misma(e['nombre'], p['nombre']) for p in g)), None)
        nombre = nice(e['nombre']) if e else nice(max(g, key=lambda p: p['n_votos'])['nombre'])
        if not e:  # el registro de Senado viene apellido-primero: se deja tal cual, en Title Case
            pass
        i = slug(nombre); base = i; k = 2
        while i in usados: i = f'{base}-{k}'; k += 1
        usados.add(i)
        g.sort(key=lambda p: -p['n_votos'])
        nv = sum(p['n_votos'] for p in g)
        indice.append({'id': i, 'n': nombre, 'b': g[0]['bancada'], 'c': '+'.join(p['camara'] for p in g),
                       'v': nv, 'e': ({'corp': e['corp'], 'partido': e['partido'], 'dep': e['dep']} if e else None)})
        fichas[i] = {'id': i, 'nombre': nombre, 'actual': indice[-1]['e'], 'bloques': g}
    indice.sort(key=lambda x: -x['v'])
    sin = [e for e in E if not any(x['e'] and misma(e['nombre'], x['n']) for x in indice)]
    meta = {'v': '2026-10-23', 'n': len(indice), 'electos_con_record': sum(1 for x in indice if x['e']),
            'electos_total': len(E), 'electos_sin_record': len(sin),
            'fuentes': {'Senado': 'API pública app.senado.gov.co · 2017-2026 · solo Sí/No',
                        'Cámara': 'actas de plenaria de la Cámara · 2014-2026 · voto electrónico'},
            'alineacion': 'coincidencia con la bancada del Pacto Histórico (gobierno 2022-2026) en votaciones disputadas, donde al menos 15 % votó distinto'}
    return {'meta': meta, 'c': indice}, fichas

def escribir(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    b = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    open(ruta, 'wb').write(b)
    open(ruta + '.gz', 'wb').write(gzip.compress(b, 9))
    return len(b)

def main():
    L = cargar_proyectos()
    # «Fast-Track» también es una legislatura en el registro: solo cuentan las de años
    leg = max(l for l in ((x.get('legislatura') or '') for x, _ in L) if re.match(r'^\d{4}-\d{4}$', l))
    activos = build_activos(L, leg)
    escribir(os.path.join(OUT, 'activos.json'), activos)
    print(f"activos.json · {activos['n']} proyectos en trámite de la legislatura {leg}")
    if '--solo-activos' in sys.argv:
        if '--subir' in sys.argv:
            subprocess.run(['aws', 's3', 'cp', os.path.join(OUT, 'activos.json.gz'), S3 + 'activos.json',
                            '--content-type', 'application/json', '--content-encoding', 'gzip',
                            '--cache-control', 'public, max-age=900', '--only-show-errors'], check=True)
            print('subido', S3 + 'activos.json')
        return
    archivo, por_num = build_archivo(L)
    n = escribir(os.path.join(OUT, 'archivo.json'), archivo)
    print(f"archivo.json · {archivo['meta']['n']} proyectos · {n/1e6:.2f} MB · gzip {os.path.getsize(os.path.join(OUT,'archivo.json.gz'))/1e6:.2f} MB")
    indice, fichas = build_votos(por_num)
    escribir(os.path.join(OUT, 'votos/indice.json'), indice)
    tam = [escribir(os.path.join(OUT, 'votos', f'{i}.json'), f) for i, f in fichas.items()]
    print(f"votos · {len(fichas)} congresistas · electos 2026 con récord {indice['meta']['electos_con_record']} de {indice['meta']['electos_total']} · ficha p50 {sorted(tam)[len(tam)//2]/1e3:.0f} KB · máx {max(tam)/1e3:.0f} KB")
    sin_t = sum(1 for f in fichas.values() for b in f['bloques'] for p in b['proyectos'] if p[0].startswith('Proyecto '))
    tot = sum(len(b['proyectos']) for f in fichas.values() for b in f['bloques'])
    print(f"proyectos votados sin título del archivo: {sin_t} de {tot}")
    if '--subir' in sys.argv:
        stage = os.path.join(OUT, '_gz')
        subprocess.run(['rm', '-rf', stage], check=True)
        for raiz, _, fs in os.walk(OUT):
            if raiz.startswith(stage): continue
            for f in fs:
                if f.endswith('.json.gz'):
                    rel = os.path.relpath(os.path.join(raiz, f), OUT)[:-3]
                    os.makedirs(os.path.dirname(os.path.join(stage, rel)), exist_ok=True)
                    os.replace(os.path.join(raiz, f), os.path.join(stage, rel))
        subprocess.run(['aws', 's3', 'cp', stage + '/', S3, '--recursive', '--content-type', 'application/json',
                        '--content-encoding', 'gzip', '--cache-control', 'public, max-age=3600', '--only-show-errors'], check=True)
        print('subido a', S3)

if __name__ == '__main__':
    main()
