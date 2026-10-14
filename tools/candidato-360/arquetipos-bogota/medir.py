#!/usr/bin/env python3
"""Mide, barrio por barrio en Bogotá, las variables de los arquetipos de voto.

    python3 tools/candidato-360/arquetipos-bogota/extraer.py ter2023   (y ter2019, jal2019)
    node    tools/candidato-360/arquetipos-bogota/familias.mjs
    python3 tools/candidato-360/arquetipos-bogota/medir.py

Unidad: barrio catastral (`codigo` de BOG-BARRIOS-CATASTRALES, el mismo de
candidato-360-data/bogota-barrios). Cada puesto va a su barrio con
candidato-360-data/bogota-puesto-barrio.js (la regla del CRM, por coordenada).
Los puestos de las zonas 90 (puesto censo) y 98 (cárceles) se dejan fuera: no
son de ningún barrio.

Salida: Bases de datos/arquetipos-bogota/
    candidatos-concejo-2023.csv   tipo de cada candidatura (figura · arraigo · …)
    barrios.csv                   una fila por barrio con todas las variables
"""
import csv, json, math, re, unicodedata
import numpy as np
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
BD = RAIZ / 'Bases de datos'
RAW = BD / 'arquetipos-bogota' / 'raw'
OUT = BD / 'arquetipos-bogota'
ESPECIALES = {'996': 'blanco', '997': 'nulos', '998': 'no_marcados', '999': 'no_marcados'}
ZONAS_FUERA = {'90', '98'}

# ── Umbrales (heurística declarada; ver LEEME.md) ─────────────────────────
FIGURA_MIN = 8000     # votos en la ciudad para contar como «figura» (tamaño, no estilo)

# Familias: lo que el diccionario general no sabe de los movimientos de Bogotá.
FAMILIA_BOGOTA = {
    'RECONSTRUYAMOS BOGOTA': 'd',          # Diego Molano, aval del Centro Democrático
    'LIDERAZGO AMPLIO DE RENOVACION AVANZADA DE BTA LARA BOGOTA': 'c',  # lista de Rodrigo Lara
    'CON TODA POR BOGOTA': 'c',
    'AVANCEMOS': 'd',                      # Miguel Uribe 2019
    'CLAUDIA ALCALDESA': 'ci',             # Claudia López 2019 (Alianza Verde)
    'BOGOTA PARA LA GENTE': 'ci',          # Galán 2019 (lista al Concejo 2019 de Galán)
}


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', ' ', s)).strip()


def cargar_js(ruta, var):
    t = ruta.read_text(encoding='utf-8')
    i = t.index('=') + 1
    return json.loads(t[i:].rstrip().rstrip(';'))


def bloques():
    fam = json.loads((RAW / 'familias.json').read_text())
    out = {}
    for k, v in fam.items():
        b = FAMILIA_BOGOTA.get(norm(v['nombre']), v['bloque'])
        out[k] = b
    return out


# ── Concentración esperada por azar (para no tomar ruido por arraigo) ──────
_DESP = {}
_RNG = np.random.default_rng(2027)
def d_esperada(n, p, clave):
    """Disimilitud media entre la distribución p de su lista y n votos tirados
    al azar con esa misma distribución. Con pocos votos un candidato «parece»
    concentrado aunque no lo esté; esto es lo que hay que descontar."""
    bin_ = min(int(round(math.log(max(n, 2), 1.12))), 200)
    k = (clave, bin_)
    if k not in _DESP:
        m = max(2, int(round(1.12 ** bin_)))
        draws = _RNG.multinomial(m, p, size=300) / m
        _DESP[k] = float(np.mean(0.5 * np.abs(draws - p).sum(axis=1)))
    return _DESP[k]


def arraigo(dist, n, p, clave):
    """Votos de arraigo de una candidatura a una escala (localidad o barrio).
    dist: votos por unidad (vector) · p: geografía de su lista (vector).
    Devuelve (D, D_azar, votos de arraigo, fracción de arraigo por unidad)."""
    s = dist / n
    D = 0.5 * float(np.abs(s - p).sum())
    Ed = d_esperada(n, p, clave)
    exc = np.maximum(0.0, dist - n * p)
    E = exc.sum()
    A = n * max(0.0, D - Ed)
    f = np.where(dist > 0, (A / E) * exc / np.where(dist > 0, dist, 1), 0.0) if E else np.zeros_like(dist)
    return D, Ed, A, f


def main():
    fam = bloques()
    pb = cargar_js(RAIZ / 'candidato-360-data' / 'bogota-puesto-barrio.js', 'x')
    geo = json.loads((BD / 'output_pacto_1v_2026' / 'geo' / 'BOG-BARRIOS-CATASTRALES.json').read_text())
    est = json.loads((BD / 'estrato-ciudades' / 'estrato-barrio.json').read_text())['bogota']
    barrio = {}
    for i, f in enumerate(geo['features']):
        p = f['properties']
        e = est.get(str(i)) or {}
        barrio[p['codigo']] = {'nombre': p['nombre'], 'loc': p['loc_codigo'], 'loc_nombre': p['loc_nombre'],
                               'estrato': e.get('media'), 'estrato_moda': e.get('moda')}

    t23 = json.loads((RAW / 'ter2023.json').read_text())
    t19 = json.loads((RAW / 'ter2019.json').read_text())
    j19 = json.loads((RAW / 'jal2019.json').read_text())

    # ── Censo 2023 (territoriales) y 2026 (presidencial), por puesto ───────
    def censo(anio, tipo):
        out = {}
        for r in json.loads((BD / 'censos-registraduria' / f'{anio}_datos_censo-electoral-min.json').read_text())['data']:
            if r['cod_depto'] != '16' or r['cod_mun'] != '001' or r['tipo_eleccion'] != tipo:
                continue
            out[f"{r['zona']}-{r['cod_puesto']}"] = r
        return out
    c23 = censo(2023, 'AUTORIDADES TERRITORIALES')
    c26 = censo(2026, 'PRESIDENTE DE LA REPÚBLICA')
    m26 = {}
    for r in json.loads((BD / 'output_2v' / 'master_unificado_puesto.json').read_text()):
        if r.get('dep') == '16' and r.get('mun') == '001':
            m26[f"{r['zona']}-{r['puesto']}"] = r

    conc, alc = t23['conc'], t23['alc']
    nombres_lista = defaultdict(int)
    for d in conc.values():
        for k, v in d.items():
            par, can = k.split('|')
            if can not in ESPECIALES and can != '0':
                nombres_lista[par] += v
    CERRADAS = {k.split('|')[1] for k in t23['_partidos'] if k.startswith('conc|') and nombres_lista[k.split('|')[1]] == 0 and k.split('|')[1] != '0'}
    print('listas cerradas al Concejo 2023:', [t23['_partidos'][f'conc|{p}'] for p in CERRADAS])

    # ── 1. Votos de arraigo de cada candidatura al Concejo 2023 ────────────
    # Dos escalas: localidad (20 unidades, poco ruido) y barrio (522, capta al
    # que manda en tres barrios de una localidad de un millón de habitantes).
    def unidad(p, escala):
        zz = p.split('-')[0]
        if zz in ZONAS_FUERA or not zz.isdigit() or int(zz) > 20:
            return None
        return zz if escala == 'loc' else pb.get(p)
    ESC = {}
    for escala in ('loc', 'bar'):
        units = sorted({u for p in conc if (u := unidad(p, escala))})
        ix = {u: i for i, u in enumerate(units)}
        vc = defaultdict(lambda: np.zeros(len(units)))
        vp = defaultdict(lambda: np.zeros(len(units)))
        for p, d in conc.items():
            u = unidad(p, escala)
            if u is None:
                continue
            for k, v in d.items():
                par, can = k.split('|')
                if can in ESPECIALES:
                    continue
                vp[par][ix[u]] += v
                if can != '0':
                    vc[k][ix[u]] += v
        ESC[escala] = {'units': units, 'ix': ix, 'vc': vc, 'vp': vp}
    VT = {L: 0 for L in ESC['loc']['units']}
    for par, vec in ESC['loc']['vp'].items():
        for L, i in ESC['loc']['ix'].items():
            VT[L] += vec[i]
    tot = sum(VT.values())
    S = {L: VT[L] / tot for L in VT}

    # trayectoria: ex candidaturas a JAL 2019 y al Concejo 2019 (por nombre)
    jal19 = {norm(n) for k, n in j19['_nombres'].items() if not k.endswith(('|0', '|996', '|997', '|998', '|999'))}
    conc19_tot = defaultdict(int)
    for d in t19['conc'].values():
        for k, v in d.items():
            conc19_tot[k] += v
    conc19 = {norm(t19['_nombres'][f'conc|{k}']): v for k, v in conc19_tot.items() if k.split('|')[1] not in ESPECIALES and k.split('|')[1] != '0'}
    electos19 = curules_2019(t19, conc19_tot)

    cand = {}
    L_ix = ESC['loc']['ix']
    for k, dl in ESC['loc']['vc'].items():
        par = k.split('|')[0]
        n = float(dl.sum())
        pl = ESC['loc']['vp'][par] / ESC['loc']['vp'][par].sum()
        D, Ed, A_loc, f_loc = arraigo(dl, n, pl, ('loc', par))
        db = ESC['bar']['vc'][k]
        nb = float(db.sum())
        pbv = ESC['bar']['vp'][par] / ESC['bar']['vp'][par].sum()
        Db, Edb, A_bar, f_bar = arraigo(db, nb, pbv, ('bar', par)) if nb else (0, 0, 0, np.zeros_like(db))
        s_ = {L: dl[i] / n for L, i in L_ix.items()}
        lq = {L: (s_[L] / pl[i]) if pl[i] else 0 for L, i in L_ix.items()}
        top = max(L_ix, key=lambda L: (lq[L] if s_[L] >= 0.05 else 0))
        nombre = t23['_nombres'][f'conc|{k}']
        nn = norm(nombre)
        cand[k] = {
            'k': k, 'nombre': nombre, 'partido': t23['_partidos'][f'conc|{par}'],
            'familia': fam.get(f'ter2023|conc|{par}', 'sc'),
            'votos': int(n), 'D': D, 'D_azar': Ed, 'D_bar': Db, 'D_azar_bar': Edb,
            'A_loc': A_loc, 'A_bar': A_bar,
            'f_loc': {L: float(f_loc[i]) for L, i in L_ix.items()},
            'f_bar': {u: float(f_bar[i]) for u, i in ESC['bar']['ix'].items() if db[i]},
            'loc_top': top, 'pct_loc_top': s_[top], 'lq_top': lq[top],
            'pct_lista': n / ESC['loc']['vp'][par].sum(),
            'D_ciudad': 0.5 * sum(abs(s_[L] - S[L]) for L in S),
            'ex_jal19': nn in jal19, 'conc19': nn in conc19, 'electo19': nn in electos19,
            'clase': 'figura' if n >= FIGURA_MIN else 'media' if n >= 2000 else 'pequena',
        }

    with open(OUT / 'candidatos-concejo-2023.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['candidato', 'partido', 'familia', 'votos', 'pct_de_su_lista', 'clase', 'arraigo_localidad', 'arraigo_barrio', 'D_loc', 'D_loc_azar', 'D_bar', 'D_bar_azar', 'D_vs_ciudad', 'localidad_top', 'pct_localidad_top', 'lq_vs_lista_top', 'ex_jal_2019', 'candidato_concejo_2019', 'concejal_electo_2019'])
        for c in sorted(cand.values(), key=lambda c: -c['votos']):
            w.writerow([c['nombre'], c['partido'], c['familia'], c['votos'], f"{c['pct_lista']:.3f}", c['clase'], f"{c['A_loc']/c['votos']:.3f}", f"{c['A_bar']/c['votos']:.3f}",
                        f"{c['D']:.3f}", f"{c['D_azar']:.3f}", f"{c['D_bar']:.3f}", f"{c['D_azar_bar']:.3f}", f"{c['D_ciudad']:.3f}",
                        barrio_loc_nombre(barrio, c['loc_top']), f"{c['pct_loc_top']:.3f}", f"{c['lq_top']:.2f}",
                        int(c['ex_jal19']), int(c['conc19']), int(c['electo19'])])

    # ── 2. Por puesto → barrio ──────────────────────────────────────────────
    B = defaultdict(lambda: defaultdict(float))
    sin_barrio = defaultdict(int)
    for p in set(conc) | set(alc):
        zz = p.split('-')[0]
        if zz in ZONAS_FUERA:
            continue
        cod = pb.get(p)
        dc, da = conc.get(p, {}), alc.get(p, {})
        if not cod or cod not in barrio:
            sin_barrio['puestos'] += 1
            sin_barrio['votos'] += sum(dc.values())
            continue
        b = B[cod]
        b['puestos'] += 1
        # Concejo
        for k, v in dc.items():
            par, can = k.split('|')
            b['conc_tot'] += v
            if can in ESPECIALES:
                b['conc_' + ESPECIALES[can]] += v
                continue
            b['conc_val'] += v
            b['fam_conc_' + fam.get(f'ter2023|conc|{par}', 'sc')] += v
            b[f'lista_{par}'] += v
            if can == '0':
                b['conc_logo'] += v
                # El voto al logo de una lista CERRADA no es una elección del
                # votante (no hay nombres que marcar): se separa del logo abierto.
                b['conc_logo_cerrada' if par in CERRADAS else 'conc_logo_abierta'] += v
                continue
            b['conc_nombres_abierta'] += v
            c = cand[k]
            b['conc_nombres'] += v
            # el arraigo de barrio y el de localidad se solapan: se toma el mayor
            fa = max(c['f_loc'].get(zz, 0.0), c['f_bar'].get(cod, 0.0))
            b['conc_arraigo'] += v * fa
            b['conc_arraigo_loc'] += v * c['f_loc'].get(zz, 0.0)
            b['conc_arraigo_bar'] += v * c['f_bar'].get(cod, 0.0)
            b['conc_sigue_lista'] += v * (1 - fa)
            b['conc_' + c['clase']] += v
            if c['electo19']:
                b['conc_incumbente'] += v
            if c['ex_jal19']:
                b['conc_exedil'] += v
            b[f'cand_{k}'] += v
        # Alcaldía
        for k, v in da.items():
            par, can = k.split('|')
            b['alc_tot'] += v
            if can in ESPECIALES:
                b['alc_' + ESPECIALES[can]] += v
                continue
            b['alc_val'] += v
            b['fam_alc_' + fam.get(f'ter2023|alc|{par}', 'sc')] += v
            b[f'alc_{par}'] += v
        # Censo y edad
        r = c23.get(p)
        if r:
            b['censo23'] += r['potencial_electoral']
            re_ = r['rango_etario']
            b['e18_30'] += re_['18-20'] + re_['21-25'] + re_['26-30']
            b['e61'] += re_['mas de 60']
            b['mujeres'] += r['sexo']['mujeres']
        r26 = c26.get(p)
        if r26 and p in m26:
            b['censo26'] += r26['potencial_electoral']
            b['urna26'] += m26[p]['urna1']

    # ── 3. Concejo 2019 por barrio (para la volatilidad) ────────────────────
    v19 = concejo_2019_por_barrio(geo, fam)
    a19 = alcaldia_2019_por_barrio(geo, t19, fam)

    # ── 4. Ratios por barrio ────────────────────────────────────────────────
    filas = []
    ciudad = defaultdict(float)
    for b in B.values():
        for k in ('alc_tot', 'censo23', 'urna26', 'censo26'):
            ciudad[k] += b[k]
    part23_c = ciudad['alc_tot'] / ciudad['censo23']
    part26_c = ciudad['urna26'] / ciudad['censo26']
    FAMS = ['izq', 'ci', 'c', 'cd', 'd', 'sc']
    for cod, b in B.items():
        info = barrio[cod]
        if b['conc_val'] < 300 or not b['censo23']:
            continue
        cv, av = b['conc_val'], b['alc_val']
        listas = [v for k, v in b.items() if k.startswith('lista_')]
        nep = 1 / sum((v / cv) ** 2 for v in listas)
        cands = sorted((v for k, v in b.items() if k.startswith('cand_')), reverse=True)
        fc = {f: b[f'fam_conc_{f}'] / cv for f in FAMS}
        fa = {f: b[f'fam_alc_{f}'] / av for f in FAMS} if av else {}
        cruzado = 0.5 * sum(abs(fa.get(f, 0) - fc[f]) for f in FAMS) if av else None
        alc_cands = sorted(((k[4:], v) for k, v in b.items() if k.startswith('alc_') and k[4:].isdigit()), key=lambda x: -x[1])
        part23 = b['alc_tot'] / b['censo23']
        part26 = b['urna26'] / b['censo26'] if b['censo26'] else None
        mov_local = (part23 / part26) / (part23_c / part26_c) if part26 else None
        vol = None
        if cod in v19:
            f19 = v19[cod]
            vol = 0.5 * sum(abs(fc[f] - f19.get(f, 0)) for f in FAMS)
        fila = {
            'codigo': cod, 'barrio': info['nombre'], 'localidad': info['loc_nombre'], 'loc': info['loc'],
            'estrato': info['estrato'], 'estrato_moda': info['estrato_moda'], 'puestos': int(b['puestos']),
            'censo23': int(b['censo23']), 'votantes23': int(b['alc_tot']),
            'part23': part23, 'part26': part26, 'mov_local': mov_local,
            'conc_val': int(cv),
            'logo': b['conc_logo'] / cv,
            'cerrada': b['conc_logo_cerrada'] / cv,
            'logo_abierta': b['conc_logo_abierta'] / max(1, b['conc_logo_abierta'] + b['conc_nombres_abierta']),
            'desafeccion': (b['conc_blanco'] + b['conc_nulos'] + b['conc_no_marcados']) / b['conc_tot'], 'arraigo': b['conc_arraigo'] / cv,
            'arraigo_loc': b['conc_arraigo_loc'] / cv, 'arraigo_bar': b['conc_arraigo_bar'] / cv, 'sigue_lista': b['conc_sigue_lista'] / cv,
            'figura': b['conc_figura'] / cv, 'media': b['conc_media'] / cv, 'pequena': b['conc_pequena'] / cv,
            'incumbente': b['conc_incumbente'] / cv, 'exedil': b['conc_exedil'] / cv,
            'top1_cand': (cands[0] / cv) if cands else 0, 'top5_cand': sum(cands[:5]) / cv,
            'nep_listas': nep,
            'blanco_conc': b['conc_blanco'] / b['conc_tot'],
            'nulo_nm_conc': (b['conc_nulos'] + b['conc_no_marcados']) / b['conc_tot'],
            'blanco_alc': b['alc_blanco'] / b['alc_tot'] if b['alc_tot'] else None,
            'cruzado': cruzado, 'vol_19_23': vol,
            'nec_alc': (1 / sum((v / av) ** 2 for _, v in alc_cands)) if av else None,
            'vol_alc_19_23': (0.5 * sum(abs(fa.get(f, 0) - a19[cod]['fam'].get(f, 0)) for f in FAMS)) if cod in a19 and av else None,
            'alc19_claudia': a19.get(cod, {}).get('cand', {}).get('claudia'),
            'alc19_galan': a19.get(cod, {}).get('cand', {}).get('galan'),
            'alc19_morris': a19.get(cod, {}).get('cand', {}).get('morris'),
            'alc19_uribe': a19.get(cod, {}).get('cand', {}).get('uribe'),
            'alc_gana': t23['_nombres'].get(f"alc|{alc_cands[0][0]}|", '') if False else (alc_nombre(t23, alc_cands[0][0]) if alc_cands else ''),
            'alc_gana_pct': alc_cands[0][1] / av if alc_cands and av else None,
            'alc_margen': (alc_cands[0][1] - alc_cands[1][1]) / av if len(alc_cands) > 1 and av else None,
            'joven': b['e18_30'] / b['censo23'], 'mayor': b['e61'] / b['censo23'],
            'mujeres': b['mujeres'] / b['censo23'],
        }
        for f in FAMS:
            fila[f'conc_{f}'] = fc[f]
            fila[f'alc_{f}'] = fa.get(f, 0)
        for par, nom in (('19', 'galan'), ('1503', 'oviedo'), ('7001', 'bolivar'), ('5033', 'molano'), ('5137', 'lara')):
            fila[f'alc_{nom}'] = b[f'alc_{par}'] / av if av else 0
        filas.append(fila)

    claves = list(filas[0].keys())
    with open(OUT / 'barrios.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        for f in sorted(filas, key=lambda f: f['codigo']):
            w.writerow({k: (f'{v:.4f}' if isinstance(v, float) else v) for k, v in f.items()})
    tot_conc = sum(sum(v for k, v in d.items() if k.split('|')[1] not in ESPECIALES) for p, d in conc.items() if p.split('-')[0] not in ZONAS_FUERA)
    ubic = sum(f['conc_val'] for f in filas)
    print(f'barrios con dato: {len(filas)} · puestos sin barrio: {sin_barrio["puestos"]} ({sin_barrio["votos"]:,} votos)')
    print(f'cobertura voto válido Concejo: {ubic:,} de {tot_conc:,} ({ubic/tot_conc:.1%})')
    print(f'participación ciudad 2023 {part23_c:.1%} · 1V 2026 {part26_c:.1%}')
    cl = defaultdict(int)
    for c in cand.values():
        cl[c['clase']] += c['votos']
    print('voto a nombres por tamaño de candidatura:', {k: f'{v:,}' for k, v in cl.items()})
    nom = sum(c['votos'] for c in cand.values())
    for e in ('loc', 'bar'):
        A = sum(c['A_' + e] for c in cand.values())
        print(f'votos de arraigo escala {e}: {A:,.0f} = {A/nom:.1%} del voto a nombres')


def barrio_loc_nombre(barrio, L):
    for b in barrio.values():
        if b['loc'] == L:
            return b['loc_nombre']
    return L


def alc_nombre(t23, par):
    for k, n in t23['_nombres'].items():
        if k.startswith(f'alc|{par}|'):
            return n
    return par


def curules_2019(t19, tot):
    """Concejales electos en 2019 (45 curules): umbral del 50 % del cuociente
    sobre válidos con blanco, cifra repartidora, y dentro de cada lista abierta
    los más votados. Las listas cerradas no traen nombres en el GCS."""
    listas = defaultdict(int)
    blanco = 0
    for k, v in tot.items():
        par, can = k.split('|')
        if can == '996':
            blanco += v
        elif can not in ESPECIALES:
            listas[par] += v
    val = sum(listas.values()) + blanco
    umbral = 0.5 * val / 45
    ok = {p: v for p, v in listas.items() if v >= umbral}
    cocs = sorted(((v / d, p) for p, v in ok.items() for d in range(1, 46)), reverse=True)[:45]
    cur = defaultdict(int)
    for _, p in cocs:
        cur[p] += 1
    electos = set()
    for p, n in cur.items():
        cs = sorted(((v, k) for k, v in tot.items() if k.startswith(p + '|') and k.split('|')[1] not in ESPECIALES and k.split('|')[1] != '0'), reverse=True)
        for v, k in cs[:n]:
            electos.add(norm(t19['_nombres'][f'conc|{k}']))
    return electos


def mapa_puestos_2019(geo):
    """Código de puesto de 2019 → barrio catastral, desde el detalle por comuna
    de 2019 (ya resuelto por nombre: el código de 2019 no siempre es el mismo
    lugar en 2026)."""
    idx = {i: f['properties']['codigo'] for i, f in enumerate(geo['features'])}
    out = {}
    for ruta in sorted((BD / 'output_concejo_2019' / 'comuna').glob('16-001-*.json')):
        d = json.loads(ruta.read_text())
        feat = {b['name']: b.get('feat') for b in d['barrios']}
        for p in d['puestos']:
            f = feat.get(p.get('barrio'))
            if f is not None:
                out[p['code']] = idx[f]
    return out


def alcaldia_2019_por_barrio(geo, t19, fam):
    m = mapa_puestos_2019(geo)
    NOM = {'3464': 'claudia', '376': 'galan', '4293': 'morris', '4005': 'uribe'}
    acc = defaultdict(lambda: defaultdict(float))
    for p, d in t19['alc'].items():
        cod = m.get(p)
        if not cod:
            continue
        for k, v in d.items():
            par, can = k.split('|')
            if can in ESPECIALES:
                continue
            acc[cod]['_val'] += v
            acc[cod]['f_' + fam.get(f'ter2019|alc|{par}', 'sc')] += v
            if par in NOM:
                acc[cod]['c_' + NOM[par]] += v
    out = {}
    for cod, a in acc.items():
        t = a['_val']
        if t < 300:
            continue
        out[cod] = {'fam': {k[2:]: v / t for k, v in a.items() if k.startswith('f_')},
                    'cand': {k[2:]: v / t for k, v in a.items() if k.startswith('c_')}}
    return out


def concejo_2019_por_barrio(geo, fam):
    """Familias del Concejo 2019 por barrio, desde el detalle por comuna ya
    resuelto (los códigos de puesto de 2019 no son siempre el mismo lugar en
    2026: ese detalle los ubicó por nombre)."""
    idx = {i: f['properties']['codigo'] for i, f in enumerate(geo['features'])}
    out = {}
    for ruta in sorted((BD / 'output_concejo_2019' / 'comuna').glob('16-001-*.json')):
        d = json.loads(ruta.read_text())
        partidos = [norm(p[0]) for p in d['partidos']]
        fam19 = {}
        famn = json.loads((RAW / 'familias.json').read_text())
        for k, v in famn.items():
            if k.startswith('ter2019|conc|'):
                fam19[norm(v['nombre'])] = FAMILIA_BOGOTA.get(norm(v['nombre']), v['bloque'])
        cand_par = [c[1] for c in d['cands']]
        for b in d['barrios']:
            if b.get('feat') is None:
                continue
            acc = defaultdict(float)
            for ci, v in b['v']:
                acc[fam19.get(partidos[cand_par[ci]], 'sc')] += v
            for pi, v in b.get('l', []):
                acc[fam19.get(partidos[pi], 'sc')] += v
            t = sum(acc.values())
            if t >= 300:
                out[idx[b['feat']]] = {f: v / t for f, v in acc.items()}
    return out


if __name__ == '__main__':
    main()
