#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dos preguntas nuevas, a nivel MESA (dep-mun-zz-pp-mesa), misma metodología
que oviedo_y_composicion.py (regresión ecológica NNLS + restringida SLSQP +
cotas duras de Duncan-Davis/King):

(a) Votantes del CENTRO DEMOCRÁTICO al SENADO (8-mar):
    a1. ¿cuántos votaron a Paloma en la Gran Consulta (mismo día)?
    a2. ¿cuántos fueron a Paloma / Abelardo / otros en la 1V (31-may)?

(b) El 1,64M de Paloma en 1V, ¿cómo se compone?:
    Paloma-consulta / Oviedo / resto Gran Consulta / otras consultas /
    votó en marzo sin consulta / NO votó en marzo (nuevos votantes).

Fuentes: MMV declarados (escrutinio mesa: senado corp 01 + consultas corp 06),
preconteo 1V por mesa (0247 con Claudia recuperada), censo por puesto 2026.
"""
import csv, json, os, glob
import numpy as np
from scipy.optimize import nnls, minimize

csv.field_size_limit(1 << 24)
ROOT = "/Users/ricardoruiz/ricardoruiz.co"
PRE   = os.path.join(ROOT, "Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv")
MMVDIR = os.path.join(ROOT, "Bases de datos/DEPTOS_DECLARADOS")
CENSO = os.path.join(ROOT, "Bases de datos/censos-puesto-2026.json")
OUTDIR = os.path.join(ROOT, "Bases de datos/output_trasvase_cd")
os.makedirs(OUTDIR, exist_ok=True)

PALOMA = 'PALOMA SUSANA VALENCIA LASERNA'
OVIEDO = 'JUAN DANIEL OVIEDO ARANGO'
PAL_TOTAL_1V = 1_637_665   # total oficial preconteo 0247

def nz(x):
    x = str(x).strip()
    return str(int(x)) if x.isdigit() else x.upper()

def mk(dep, mun, z, p, m): return f"{dep}-{mun}-{nz(z)}-{nz(p)}-{nz(m)}"

def pp(dep, mun, z, p):
    z = f"{int(z):02d}" if str(z).strip().isdigit() else z
    p = f"{int(p):02d}" if str(p).strip().isdigit() else p
    return f"{dep}-{mun}-{z}-{p}"

# ---------- 1V preconteo (con Claudia recuperada por mesa) ----------
pres = {}; nmesas = {}
with open(PRE, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        k = mk(r['cod_departamento'], r['cod_municipio'], r['zona'], r['puesto'], r['num_mesa'])
        ot = sum(int(r[c] or 0) for c in ['Santiago Botero', 'Mauricio Lizcano', 'Sondra Macollins',
                                          'Roy Barreras', 'Carlos Caicedo', 'Gustavo Matamoros',
                                          'Gilberto Murillo', 'Claudia López'])
        pres[k] = {'ab': int(r['Abelardo De La Espriella'] or 0), 'pa': int(r['Paloma Valencia'] or 0),
                   'ce': int(r['Iván Cepeda'] or 0), 'mu': int(r['Miguel Uribe'] or 0),
                   'sf': int(r['Sergio Fajardo'] or 0), 'bl': int(r['votos_blanco'] or 0),
                   'nu': int(r['votos_nulos'] or 0) + int(r['votos_no_marcados'] or 0),
                   'ot': ot, 'urna': int(r['total_votos_urna'] or 0)}
        k2 = pp(r['cod_departamento'], r['cod_municipio'], r['zona'], r['puesto'])
        nmesas[k2] = nmesas.get(k2, 0) + 1

# ---------- MMV: senado (corp 01) + consultas (corp 06) por mesa ----------
sen = {}; cons = {}
for fp in sorted(glob.glob(os.path.join(MMVDIR, "MMV_XXX_*.csv"))):
    if "CITREP" in fp: continue
    with open(fp, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f, delimiter=';'); next(rd, None)
        for c in rd:
            if len(c) < 19: continue
            cor = c[10]
            if cor == '01':
                k = mk(c[0], c[2], c[4], c[5], c[7]); v = int(c[18] or 0)
                d = sen.setdefault(k, {'cd': 0, 'val': 0, 'esp': 0})
                if c[13] == '0011':   d['cd'] += v          # Centro Democrático (lista cerrada)
                elif c[13] == '0000': d['esp'] += v          # blanco/nulos/no marcados (nac+ind)
                else:                 d['val'] += v          # resto válidos senado
            elif cor == '06':
                k = mk(c[0], c[2], c[4], c[5], c[7]); v = int(c[18] or 0)
                d = cons.setdefault(k, {'pal': 0, 'ovi': 0, 'otg': 0, 'otc': 0, 'esp': 0})
                if c[13] == '0200':
                    if c[17] == PALOMA:   d['pal'] += v
                    elif c[17] == OVIEDO: d['ovi'] += v
                    else:                 d['otg'] += v       # resto Gran Consulta (7 cands)
                elif c[13] in ('0100', '0300'):
                    d['otc'] += v                             # Soluciones + Frente por la Vida
                elif c[13] == '0000':
                    d['esp'] += v                             # nulos/no marcados consulta

censo = json.load(open(CENSO))['porPuesto']

# join: mesa presente en preconteo 1V y en senado MMV (consulta faltante => 0)
keys = sorted(set(pres) & set(sen))
Z = {'pal': 0, 'ovi': 0, 'otg': 0, 'otc': 0, 'esp': 0}

def build(filtrar_especiales):
    """matrices por mesa; filtrar_especiales=True excluye zona 90/98 y dep 88"""
    rows = []
    for k in keys:
        dep, mun, z, p, m = k.split('-')
        if filtrar_especiales and (dep == '88' or z in ('90', '98')): continue
        s = sen[k]; c = cons.get(k, Z); pr = pres[k]
        ppk = pp(dep, mun, z, p) if z.isdigit() and p.isdigit() else None
        cens = censo.get(ppk); nm = nmesas.get(ppk, 1) if ppk else 1
        suf_marzo = s['cd'] + s['val'] + s['esp']
        cons_tot = c['pal'] + c['ovi'] + c['otg'] + c['otc'] + c['esp']
        N = cens / max(nm, 1) if cens else 0.0
        N = max(N, suf_marzo, cons_tot, pr['urna'])
        rows.append((k, s, c, pr, suf_marzo, cons_tot, N))
    return rows

def run(rows, label):
    # ---- fuentes marzo-senado (particionan N): CD / resto válidos / esp senado / no votó marzo
    CD = []; RV = []; ES = []; NV = []
    # ---- fuentes consulta (particionan N): paloma / oviedo / resto gran / otras+esp / marzo sin consulta / no votó marzo
    PC = []; OC = []; GC = []; XC = []; MS = []; NM = []
    # ---- destinos consulta
    Ypal = []; Yovi = []; Yotg = []; Yotc = []; Ynoc = []
    # ---- destinos 1V
    AB = []; PA = []; CE = []; SF = []; MU = []; OT = []; BL = []; NU = []; ABST = []
    # cotas duras
    bnd = {kk: [0.0, 0.0] for kk in ('cd_palC', 'cd_pa1v', 'cd_ab1v', 'palC_pa1v', 'oviC_pa1v')}
    tot = {'cd': 0, 'pal': 0, 'ovi': 0, 'otg': 0, 'otc': 0, 'suf_marzo': 0, 'pa1v': 0, 'ab1v': 0}
    for k, s, c, pr, suf_marzo, cons_tot, N in rows:
        no_marzo = max(0.0, N - suf_marzo)
        CD.append(s['cd']); RV.append(s['val']); ES.append(s['esp']); NV.append(no_marzo)
        otras = c['otc'] + c['esp']
        ms = max(0.0, suf_marzo - cons_tot)
        PC.append(c['pal']); OC.append(c['ovi']); GC.append(c['otg']); XC.append(otras)
        MS.append(ms); NM.append(no_marzo)
        Ypal.append(c['pal']); Yovi.append(c['ovi']); Yotg.append(c['otg']); Yotc.append(otras)
        Ynoc.append(max(0.0, N - cons_tot))
        AB.append(pr['ab']); PA.append(pr['pa']); CE.append(pr['ce']); SF.append(pr['sf'])
        MU.append(pr['mu']); OT.append(pr['ot']); BL.append(pr['bl']); NU.append(pr['nu'])
        ABST.append(max(0.0, N - pr['urna']))
        tot['cd'] += s['cd']; tot['pal'] += c['pal']; tot['ovi'] += c['ovi']
        tot['otg'] += c['otg']; tot['otc'] += otras; tot['suf_marzo'] += suf_marzo
        tot['pa1v'] += pr['pa']; tot['ab1v'] += pr['ab']
        # cotas duras (Duncan-Davis): universo marzo para mismo-día, censal para 1V
        if s['cd'] > 0:
            bnd['cd_palC'][0] += max(0.0, s['cd'] + c['pal'] - suf_marzo); bnd['cd_palC'][1] += min(s['cd'], c['pal'])
            bnd['cd_pa1v'][0] += max(0.0, s['cd'] + pr['pa'] - N);          bnd['cd_pa1v'][1] += min(s['cd'], pr['pa'])
            bnd['cd_ab1v'][0] += max(0.0, s['cd'] + pr['ab'] - N);          bnd['cd_ab1v'][1] += min(s['cd'], pr['ab'])
        if c['pal'] > 0:
            bnd['palC_pa1v'][0] += max(0.0, c['pal'] + pr['pa'] - N);       bnd['palC_pa1v'][1] += min(c['pal'], pr['pa'])
        if c['ovi'] > 0:
            bnd['oviC_pa1v'][0] += max(0.0, c['ovi'] + pr['pa'] - N);       bnd['oviC_pa1v'][1] += min(c['ovi'], pr['pa'])

    out = {'label': label, 'mesas': len(rows), 'totales_join': dict(tot), 'bounds_pct': {}}
    out['totales_join']['marzo_sin_consulta'] = int(sum(MS))
    out['totales_join']['no_marzo'] = int(sum(NM))
    print(f"\n{'='*78}\n  UNIVERSO: {label} · mesas={len(rows):,}")
    print(f"  CD senado {tot['cd']:,} | Paloma C {tot['pal']:,} | Oviedo C {tot['ovi']:,} | "
          f"resto Gran {tot['otg']:,} | Paloma 1V {tot['pa1v']:,} | Abelardo 1V {tot['ab1v']:,}\n{'='*78}")

    Xsen = np.column_stack([CD, RV, ES, NV]).astype(float)
    SRC_SEN = ['CD senado', 'Resto válidos senado', 'Blanco/nulo senado', 'No votó marzo']

    def restringido(X, Ycols, dnames):
        Ymat = np.column_stack(Ycols).astype(float)
        A_ = X.T @ X; B_ = X.T @ Ymat; sc = A_.max(); A_ = A_/sc; B_ = B_/sc
        nS, nD = X.shape[1], Ymat.shape[1]
        def fo(x):
            T = x.reshape(nS, nD)
            return sum(T[:, c2] @ A_ @ T[:, c2] - 2*B_[:, c2] @ T[:, c2] for c2 in range(nD))
        def gr(x):
            T = x.reshape(nS, nD); G_ = np.zeros_like(T)
            for c2 in range(nD): G_[:, c2] = 2*(A_ @ T[:, c2] - B_[:, c2])
            return G_.ravel()
        ceq = [{'type': 'eq', 'fun': (lambda x, b=b: x.reshape(nS, nD)[b, :].sum() - 1)} for b in range(nS)]
        res = minimize(fo, np.full(nS*nD, 1/nD), jac=gr, method='SLSQP',
                       bounds=[(0, 1)]*nS*nD, constraints=ceq, options={'maxiter': 2000, 'ftol': 1e-12})
        return res.x.reshape(nS, nD)

    # ============ (a1) CD senado -> consulta (mismo día) ============
    DC = ['Paloma C', 'Oviedo C', 'Resto Gran C', 'Otras consultas', 'No votó consulta']
    T1 = restringido(Xsen, [Ypal, Yovi, Yotg, Yotc, Ynoc], DC)
    print("\n(a1) Votantes CD-SENADO → ¿qué hicieron en la consulta del mismo día?  (filas=100%)")
    out['a1_cd_to_consulta'] = {}
    for j, dn in enumerate(DC):
        v = T1[0, j]
        out['a1_cd_to_consulta'][dn] = {'pct': round(100*v, 2), 'votos': int(v*tot['cd'])}
        print(f"   CD → {dn:<18} {100*v:5.1f}%   (~{int(v*tot['cd']):>9,})")
    nnls_pal, _ = nnls(Xsen, np.array(Ypal, float))
    print(f"   [NNLS libre: CD→PalomaC {100*nnls_pal[0]:.1f}% · placebo no-votó-marzo→PalomaC {100*nnls_pal[3]:.2f}%]")
    out['a1_nnls_cd_palC_pct'] = round(100*nnls_pal[0], 2)
    out['a1_placebo_nomarzo_palC_pct'] = round(100*nnls_pal[3], 2)
    lo, hi = bnd['cd_palC']
    print(f"   Cota dura CD→PalomaC: [{100*lo/tot['cd']:.1f}% – {100*hi/tot['cd']:.1f}%]")
    out['bounds_pct']['cd_palC'] = [round(100*lo/tot['cd'], 2), round(100*hi/tot['cd'], 2)]

    # ============ (a2) CD senado -> 1V ============
    D1 = ['Abelardo', 'Paloma', 'Cepeda', 'Fajardo', 'M. Uribe', 'Otros 1V', 'Blanco', 'Nulo/NM', 'Abstención']
    T2 = restringido(Xsen, [AB, PA, CE, SF, MU, OT, BL, NU, ABST], D1)
    print("\n(a2) Votantes CD-SENADO → 1ª VUELTA  (filas=100%)")
    out['a2_cd_to_1v'] = {}
    for j, dn in enumerate(D1):
        v = T2[0, j]
        out['a2_cd_to_1v'][dn] = {'pct': round(100*v, 2), 'votos': int(v*tot['cd'])}
        if v > 0.002: print(f"   CD → {dn:<12} {100*v:5.1f}%   (~{int(v*tot['cd']):>9,})")
    out['a2_cd_to_1v_nnls'] = {}
    print("   [NNLS libre por destino, tasa de la fuente CD]:")
    for dn, Yd in [('Abelardo', AB), ('Paloma', PA), ('Cepeda', CE), ('Fajardo', SF),
                   ('M. Uribe', MU), ('Otros 1V', OT), ('Blanco', BL)]:
        cf, _ = nnls(Xsen, np.array(Yd, float))
        out['a2_cd_to_1v_nnls'][dn] = round(100*cf[0], 2)
        if cf[0] > 0.001: print(f"      CD→{dn:<10} {100*cf[0]:5.1f}%")
    for key2, nm2 in [('cd_pa1v', 'CD→Paloma 1V'), ('cd_ab1v', 'CD→Abelardo 1V')]:
        lo, hi = bnd[key2]
        print(f"   Cota dura {nm2}: [{100*lo/tot['cd']:.1f}% – {100*hi/tot['cd']:.1f}%]")
        out['bounds_pct'][key2] = [round(100*lo/tot['cd'], 2), round(100*hi/tot['cd'], 2)]

    # ============ (b) composición Paloma 1V ============
    Xcon = np.column_stack([PC, OC, GC, XC, MS, NM]).astype(float)
    SRC_C = ['Paloma consulta', 'Oviedo consulta', 'Resto Gran Consulta',
             'Otras consultas/esp', 'Marzo sin consulta', 'No votó marzo (nuevos)']
    totsC = [tot['pal'], tot['ovi'], tot['otg'], tot['otc'], sum(MS), sum(NM)]
    coefB, _ = nnls(Xcon, np.array(PA, float))
    attrib = [coefB[i]*totsC[i] for i in range(6)]; sB = sum(attrib)
    print("\n(b) ¿DE DÓNDE SALE EL VOTO DE PALOMA EN 1V?  (NNLS libre, conteos por mesa)")
    out['b_composicion_nnls'] = {}
    for i in range(6):
        share = attrib[i]/sB
        out['b_composicion_nnls'][SRC_C[i]] = {
            'tasa_pct': round(100*coefB[i], 2), 'votos_join': int(attrib[i]),
            'share_pct': round(100*share, 2), 'votos_escalados': int(share*PAL_TOTAL_1V)}
        print(f"   desde {SRC_C[i]:<24} tasa {100*coefB[i]:5.1f}%  → ~{int(attrib[i]):>9,}"
              f"  ({100*share:4.1f}% del voto Paloma 1V)")
    print(f"   TOTAL atribuido ≈ {int(sB):,}  (Paloma 1V en join: {tot['pa1v']:,} · nacional {PAL_TOTAL_1V:,})")

    # restringido: las 6 fuentes de consulta → 9 destinos 1V (split limpio por fuente)
    T3 = restringido(Xcon, [AB, PA, CE, SF, MU, OT, BL, NU, ABST], D1)
    print("\n    Versión restringida (cada fuente reparte su 100% entre destinos de 1V):")
    out['b_restringido'] = {}
    for i, sn in enumerate(SRC_C):
        out['b_restringido'][sn] = {D1[j]: round(100*T3[i, j], 2) for j in range(len(D1))}
        tops = sorted(range(len(D1)), key=lambda j: -T3[i, j])
        line = " · ".join(f"{D1[j]} {100*T3[i,j]:.1f}%" for j in tops if T3[i, j] > 0.02)
        print(f"      {sn:<24} → {line}")
    # composición implícita del restringido (consistencia)
    att3 = [T3[i, 1]*totsC[i] for i in range(6)]; s3 = sum(att3)
    out['b_composicion_restringida'] = {SRC_C[i]: {'votos_join': int(att3[i]),
                                        'share_pct': round(100*att3[i]/s3, 2),
                                        'votos_escalados': int(att3[i]/s3*PAL_TOTAL_1V)} for i in range(6)}
    print(f"\n    Composición implícita (restringido): " +
          " · ".join(f"{SRC_C[i].split(' (')[0]} {100*att3[i]/s3:.1f}%" for i in range(6) if att3[i]/s3 > 0.005) +
          f"  (suma {int(s3):,})")
    for key2, nm2, tt in [('palC_pa1v', 'PalomaC→Paloma1V', tot['pal']), ('oviC_pa1v', 'OviedoC→Paloma1V', tot['ovi'])]:
        lo, hi = bnd[key2]
        print(f"    Cota dura {nm2}: [{100*lo/tt:.1f}% – {100*hi/tt:.1f}%]")
        out['bounds_pct'][key2] = [round(100*lo/tt, 2), round(100*hi/tt, 2)]

    # estimador ENCADENADO para (a2): CD→consulta (a1, bien identificado) ×
    # tasas NNLS consulta→1V. Mapeo: noConsulta del CD ≡ fuente 'marzo sin consulta'.
    tasas = {}
    for dn, Yd in [('Abelardo', AB), ('Paloma', PA), ('Cepeda', CE), ('Fajardo', SF),
                   ('M. Uribe', MU), ('Otros 1V', OT), ('Blanco', BL), ('Nulo/NM', NU), ('Abstención', ABST)]:
        cf, _ = nnls(Xcon, np.array(Yd, float))
        tasas[dn] = cf  # [PC, OC, GC, XC, MS, NM]
    fila_cd = [T1[0, 0], T1[0, 1], T1[0, 2], T1[0, 3], T1[0, 4]]  # PalC,OviC,restoG,otras,noCons
    print("\n(a2-bis) ENCADENADO CD→1V  (CD→consulta de a1 × tasas NNLS consulta→1V):")
    out['a2_cd_to_1v_encadenado'] = {}
    enc_sum = 0.0
    for dn in ['Abelardo', 'Paloma', 'Cepeda', 'Fajardo', 'M. Uribe', 'Otros 1V', 'Blanco', 'Nulo/NM', 'Abstención']:
        cf = tasas[dn]
        v = sum(fila_cd[i]*cf[i] for i in range(4)) + fila_cd[4]*cf[4]
        enc_sum += v
        out['a2_cd_to_1v_encadenado'][dn] = {'pct': round(100*v, 2), 'votos': int(v*tot['cd'])}
        if v > 0.003: print(f"   CD → {dn:<12} {100*v:5.1f}%   (~{int(v*tot['cd']):>9,})")
    print(f"   (suma fila encadenada: {100*enc_sum:.1f}%)")

    # modelo AGRUPADO (rompe colinealidad interna de la Gran Consulta):
    # fuentes = Gran C total / otras consultas / marzo sin consulta / no votó marzo
    GT = (np.array(PC) + np.array(OC) + np.array(GC)).astype(float)
    Xg = np.column_stack([GT, XC, MS, NM])
    SRC_G = ['Gran Consulta (toda)', 'Otras consultas/esp', 'Marzo sin consulta', 'No votó marzo (nuevos)']
    totsG = [tot['pal']+tot['ovi']+tot['otg'], tot['otc'], sum(MS), sum(NM)]
    Tg = restringido(Xg, [AB, PA, CE, SF, MU, OT, BL, NU, ABST], D1)
    print("\n    Modelo AGRUPADO (Gran Consulta como un solo bloque · filas=100%):")
    out['b_agrupado'] = {}
    for i, sn in enumerate(SRC_G):
        out['b_agrupado'][sn] = {D1[j]: round(100*Tg[i, j], 2) for j in range(len(D1))}
        tops = sorted(range(len(D1)), key=lambda j: -Tg[i, j])
        line = " · ".join(f"{D1[j]} {100*Tg[i,j]:.1f}%" for j in tops if Tg[i, j] > 0.02)
        print(f"      {sn:<24} → {line}")
    attg = [Tg[i, 1]*totsG[i] for i in range(4)]; sg = sum(attg)
    out['b_composicion_agrupada'] = {SRC_G[i]: {'votos_join': int(attg[i]),
                                     'share_pct': round(100*attg[i]/sg, 2),
                                     'votos_escalados': int(attg[i]/sg*PAL_TOTAL_1V)} for i in range(4)}
    print("      Composición Paloma 1V (agrupado): " +
          " · ".join(f"{SRC_G[i]} {100*attg[i]/sg:.1f}%" for i in range(4) if attg[i]/sg > 0.003) +
          f"  (suma {int(sg):,})")
    return out

def descriptivos(rows):
    """Respaldo no-paramétrico: quintiles de mesas por share CD-senado."""
    import numpy as _np
    M = []
    for k, s, c, pr, suf_marzo, cons_tot, N in rows:
        if suf_marzo < 50 or pr['urna'] < 50: continue
        M.append((s['cd']/suf_marzo, c['pal']/suf_marzo, (c['pal']+c['ovi']+c['otg'])/suf_marzo,
                  pr['pa']/pr['urna'], pr['ab']/pr['urna'], suf_marzo))
    M = _np.array(M)
    qs = _np.quantile(M[:, 0], [0.2, 0.4, 0.6, 0.8])
    print("\nRESPALDO DESCRIPTIVO · quintiles de mesas por share CD-senado (promedios ponderados):")
    print(f"   {'quintil CD':<22}{'PalomaC/suf':>12}{'GranC/suf':>11}{'Pal 1V':>9}{'Abe 1V':>9}{'mesas':>9}")
    lo = -1e9
    labels = [f"Q{i+1}" for i in range(5)]
    corr = _np.corrcoef(_np.vstack([M[:, 0], M[:, 1], M[:, 3], M[:, 4]]))
    for i, hi in enumerate(list(qs)+[1e9]):
        sel = (M[:, 0] > lo) & (M[:, 0] <= hi); w = M[sel, 5]
        f_ = lambda col: 100*_np.average(M[sel, col], weights=w)
        rng = f"({100*max(0,lo):.0f}–{100*min(1,hi if hi<1e9 else M[:,0].max()):.0f}% CD)"
        print(f"   {labels[i]+' '+rng:<22}{f_(1):>11.1f}%{f_(2):>10.1f}%{f_(3):>8.1f}%{f_(4):>8.1f}%{sel.sum():>9,}")
        lo = hi
    print(f"   r mesa a mesa: CD↔PalomaC {corr[0,1]:+.2f} · CD↔Paloma1V {corr[0,2]:+.2f} · "
          f"CD↔Abelardo1V {corr[0,3]:+.2f} · PalomaC↔Paloma1V {corr[1,2]:+.2f}")

def nnls_b_region(rows, label):
    """solo composición NNLS de Paloma 1V, para chequear estabilidad territorial"""
    PC=[];OC=[];GC=[];XC=[];MS=[];NM=[];PA=[]
    for k, s, c, pr, suf_marzo, cons_tot, N in rows:
        PC.append(c['pal']); OC.append(c['ovi']); GC.append(c['otg'])
        XC.append(c['otc']+c['esp']); MS.append(max(0.0, suf_marzo-cons_tot))
        NM.append(max(0.0, N-suf_marzo)); PA.append(pr['pa'])
    X = np.column_stack([PC, OC, GC, XC, MS, NM]).astype(float)
    cf, _ = nnls(X, np.array(PA, float))
    tots = [sum(PC), sum(OC), sum(GC), sum(XC), sum(MS), sum(NM)]
    att = [cf[i]*tots[i] for i in range(6)]; s = sum(att) or 1.0
    nm_ = ['PalC', 'OviC', 'RestoG', 'OtrasC', 'MarzoSC', 'Nuevos']
    print(f"   {label:<26} " + " · ".join(f"{nm_[i]} {100*att[i]/s:4.1f}%" for i in range(6)) +
          f"   (PalomaC tasa {100*cf[0]:.1f}% · n={len(rows):,})")
    return {nm_[i]: round(100*att[i]/s, 2) for i in range(6)}

rows_all = build(False)
res_all = run(rows_all, "TODAS las mesas del join (incl. zona 90/98 y exterior)")
descriptivos(rows_all)
print("\nROBUSTEZ TERRITORIAL · composición NNLS de Paloma 1V por región:")
COSTA = {'03', '05', '12', '13', '21', '28', '48'}
res_all['b_por_region'] = {
    'bogota':    nnls_b_region([r for r in rows_all if r[0].startswith('16-')], 'Bogotá (16)'),
    'antioquia': nnls_b_region([r for r in rows_all if r[0].startswith('01-')], 'Antioquia (01)'),
    'costa':     nnls_b_region([r for r in rows_all if r[0].split('-')[0] in COSTA], 'Costa Atlántica'),
    'resto':     nnls_b_region([r for r in rows_all if r[0].split('-')[0] not in COSTA | {'16', '01', '88'}], 'Resto del país'),
}
rows_cl = build(True)
res_cl = run(rows_cl, "SIN zona 90/98 ni dep 88 (robustez)")

with open(os.path.join(OUTDIR, "cd-senado-y-composicion-paloma.json"), 'w', encoding='utf-8') as f:
    json.dump({'principal': res_all, 'robustez_sin_especiales': res_cl}, f, ensure_ascii=False, indent=2)
print(f"\n→ JSON: {OUTDIR}/cd-senado-y-composicion-paloma.json")
