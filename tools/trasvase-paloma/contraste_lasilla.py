#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contraste con La Silla Vacía (8-jun-2026): senado POR PARTIDO → consulta → 1V,
a nivel mesa. Objetivo: (1) reproducir su modelo (restringido directo senado→1V)
para ver si sus cifras (CD→Abelardo 97%, CD→Paloma 1%, Lib→Abe 43%, Cons→Abe 59%,
CR→Abe 82%, U→Abe 38%, APC→Abe 35%) son la esquina degenerada del EI bajo
colinealidad; (2) dar las cifras defendibles: restringido senado→consulta (mismo
día, bien identificado), encadenado vía consulta, cotas duras de King, y Goodman
bivariado (lo que daría una regresión simple).
"""
import csv, json, os, glob
import numpy as np
from scipy.optimize import nnls, minimize

csv.field_size_limit(1 << 24)
ROOT = "/Users/ricardoruiz/ricardoruiz.co"
PRE = os.path.join(ROOT, "Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv")
MMVDIR = os.path.join(ROOT, "Bases de datos/DEPTOS_DECLARADOS")
CENSO = os.path.join(ROOT, "Bases de datos/censos-puesto-2026.json")
OUTDIR = os.path.join(ROOT, "Bases de datos/output_trasvase_cd")

PALOMA = 'PALOMA SUSANA VALENCIA LASERNA'
OVIEDO = 'JUAN DANIEL OVIEDO ARANGO'

# partidos senado a separar (códigos PAR del MMV)
PARTIDOS = {'0011': 'CD', '0002': 'Conservador', '0001': 'Liberal', '0008': 'La U',
            '3003': 'Cambio Radical', '3020': 'Alianza x Col', '3063': 'Pacto',
            '0020': 'Salvación Nal', '3018': 'Frente Amplio'}
PKEYS = list(PARTIDOS.values())

def nz(x):
    x = str(x).strip()
    return str(int(x)) if x.isdigit() else x.upper()

def mk(dep, mun, z, p, m): return f"{dep}-{mun}-{nz(z)}-{nz(p)}-{nz(m)}"

def pp(dep, mun, z, p):
    z = f"{int(z):02d}" if str(z).strip().isdigit() else z
    p = f"{int(p):02d}" if str(p).strip().isdigit() else p
    return f"{dep}-{mun}-{z}-{p}"

pres = {}; nmesas = {}
with open(PRE, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        k = mk(r['cod_departamento'], r['cod_municipio'], r['zona'], r['puesto'], r['num_mesa'])
        ot = sum(int(r[c] or 0) for c in ['Santiago Botero', 'Mauricio Lizcano', 'Sondra Macollins',
                                          'Roy Barreras', 'Carlos Caicedo', 'Gustavo Matamoros',
                                          'Gilberto Murillo', 'Claudia López', 'Miguel Uribe'])
        pres[k] = {'ab': int(r['Abelardo De La Espriella'] or 0), 'pa': int(r['Paloma Valencia'] or 0),
                   'ce': int(r['Iván Cepeda'] or 0), 'sf': int(r['Sergio Fajardo'] or 0),
                   'bl': int(r['votos_blanco'] or 0),
                   'nu': int(r['votos_nulos'] or 0) + int(r['votos_no_marcados'] or 0),
                   'ot': ot, 'urna': int(r['total_votos_urna'] or 0)}
        k2 = pp(r['cod_departamento'], r['cod_municipio'], r['zona'], r['puesto'])
        nmesas[k2] = nmesas.get(k2, 0) + 1

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
                d = sen.setdefault(k, {kk: 0 for kk in PKEYS + ['otros', 'esp']})
                b = PARTIDOS.get(c[13])
                if b:                 d[b] += v
                elif c[13] == '0000': d['esp'] += v
                else:                 d['otros'] += v
            elif cor == '06':
                k = mk(c[0], c[2], c[4], c[5], c[7]); v = int(c[18] or 0)
                d = cons.setdefault(k, {'pal': 0, 'ovi': 0, 'otg': 0, 'otc': 0, 'esp': 0})
                if c[13] == '0200':
                    if c[17] == PALOMA:   d['pal'] += v
                    elif c[17] == OVIEDO: d['ovi'] += v
                    else:                 d['otg'] += v
                elif c[13] in ('0100', '0300'): d['otc'] += v
                elif c[13] == '0000':           d['esp'] += v

censo = json.load(open(CENSO))['porPuesto']
ZC = {'pal': 0, 'ovi': 0, 'otg': 0, 'otc': 0, 'esp': 0}
keys = sorted(set(pres) & set(sen))

SRC = PKEYS + ['Otros senado', 'Blanco/nulo sen', 'No votó marzo']
nS = len(SRC)
cols = {s: [] for s in SRC}
PC=[];OC=[];GC=[];XC=[];MS=[];NM=[]
Ypal=[];Yovi=[];Yotg=[];Yotc=[];Ynoc=[]
AB=[];PA=[];CE=[];SF=[];OT=[];BL=[];NU=[];ABST=[]
W=[]
bounds = {}  # (partido, destino) -> [lo, hi]
tot = {s: 0 for s in SRC}
for k in keys:
    s = sen[k]; c = cons.get(k, ZC); pr = pres[k]
    dep, mun, z, p, m = k.split('-')
    ppk = pp(dep, mun, z, p) if z.isdigit() and p.isdigit() else None
    cens = censo.get(ppk); nm = nmesas.get(ppk, 1) if ppk else 1
    suf_marzo = sum(s[kk] for kk in PKEYS) + s['otros'] + s['esp']
    cons_tot = c['pal'] + c['ovi'] + c['otg'] + c['otc'] + c['esp']
    N = cens / max(nm, 1) if cens else 0.0
    N = max(N, suf_marzo, cons_tot, pr['urna'])
    no_marzo = max(0.0, N - suf_marzo)
    for kk in PKEYS: cols[kk].append(s[kk]);
    cols['Otros senado'].append(s['otros']); cols['Blanco/nulo sen'].append(s['esp'])
    cols['No votó marzo'].append(no_marzo)
    for kk in PKEYS: tot[kk] += s[kk]
    tot['Otros senado'] += s['otros']; tot['Blanco/nulo sen'] += s['esp']; tot['No votó marzo'] += no_marzo
    otras = c['otc'] + c['esp']
    PC.append(c['pal']); OC.append(c['ovi']); GC.append(c['otg']); XC.append(otras)
    MS.append(max(0.0, suf_marzo - cons_tot)); NM.append(no_marzo)
    Ypal.append(c['pal']); Yovi.append(c['ovi']); Yotg.append(c['otg']); Yotc.append(otras)
    Ynoc.append(max(0.0, N - cons_tot))
    AB.append(pr['ab']); PA.append(pr['pa']); CE.append(pr['ce']); SF.append(pr['sf'])
    OT.append(pr['ot']); BL.append(pr['bl']); NU.append(pr['nu']); ABST.append(max(0.0, N - pr['urna']))
    W.append(N)
    # cotas King por partido -> {PalomaC, Abe1V, Pal1V}; universo marzo para C, censal para 1V
    for kk in PKEYS:
        if s[kk] <= 0: continue
        b = bounds.setdefault(kk, {'palC': [0., 0.], 'ab1v': [0., 0.], 'pa1v': [0., 0.]})
        b['palC'][0] += max(0.0, s[kk] + c['pal'] - suf_marzo); b['palC'][1] += min(s[kk], c['pal'])
        b['ab1v'][0] += max(0.0, s[kk] + pr['ab'] - N);          b['ab1v'][1] += min(s[kk], pr['ab'])
        b['pa1v'][0] += max(0.0, s[kk] + pr['pa'] - N);          b['pa1v'][1] += min(s[kk], pr['pa'])

Xsen = np.column_stack([cols[s] for s in SRC]).astype(float)
Xcon = np.column_stack([PC, OC, GC, XC, MS, NM]).astype(float)
print(f"mesas={len(keys):,}")
print("Totales senado (join): " + " · ".join(f"{s} {tot[s]:,.0f}" for s in SRC[:9]))

def restringido(X, Ycols, maxiter=3000):
    Ymat = np.column_stack(Ycols).astype(float)
    A_ = X.T @ X; B_ = X.T @ Ymat; sc = A_.max(); A_ = A_/sc; B_ = B_/sc
    ns, nd = X.shape[1], Ymat.shape[1]
    def fo(x):
        T = x.reshape(ns, nd)
        return sum(T[:, c2] @ A_ @ T[:, c2] - 2*B_[:, c2] @ T[:, c2] for c2 in range(nd))
    def gr(x):
        T = x.reshape(ns, nd); G_ = np.zeros_like(T)
        for c2 in range(nd): G_[:, c2] = 2*(A_ @ T[:, c2] - B_[:, c2])
        return G_.ravel()
    ceq = [{'type': 'eq', 'fun': (lambda x, b=b: x.reshape(ns, nd)[b, :].sum() - 1)} for b in range(ns)]
    res = minimize(fo, np.full(ns*nd, 1/nd), jac=gr, method='SLSQP',
                   bounds=[(0, 1)]*ns*nd, constraints=ceq, options={'maxiter': maxiter, 'ftol': 1e-12})
    return res.x.reshape(ns, nd)

out = {'mesas': len(keys), 'totales': {s: int(tot[s]) for s in SRC}}

# ===== (1) REPRODUCCIÓN del modelo tipo La Silla: restringido directo senado→1V =====
D1 = ['Abelardo', 'Paloma', 'Cepeda', 'Fajardo', 'Otros 1V', 'Blanco', 'Nulo/NM', 'Abstención']
T = restringido(Xsen, [AB, PA, CE, SF, OT, BL, NU, ABST])
print("\n(1) RESTRINGIDO DIRECTO senado→1V (lo que parece haber publicado La Silla):")
out['restringido_directo'] = {}
hdr = "   " + f"{'fuente':<18}" + "".join(f"{d:>11}" for d in D1)
print(hdr)
for i, sn in enumerate(SRC):
    out['restringido_directo'][sn] = {D1[j]: round(100*T[i, j], 1) for j in range(len(D1))}
    print("   " + f"{sn:<18}" + "".join(f"{100*T[i,j]:>10.1f}%" for j in range(len(D1))))

# ===== (2) senado→consulta (mismo día, bien identificado) =====
DC = ['Paloma C', 'Oviedo C', 'Resto Gran', 'Otras consultas', 'No votó consulta']
Tc = restringido(Xsen, [Ypal, Yovi, Yotg, Yotc, Ynoc])
print("\n(2) RESTRINGIDO senado→CONSULTA del mismo día (composición de la Gran Consulta):")
out['senado_a_consulta'] = {}
print("   " + f"{'fuente':<18}" + "".join(f"{d:>17}" for d in DC))
for i, sn in enumerate(SRC):
    out['senado_a_consulta'][sn] = {DC[j]: round(100*Tc[i, j], 1) for j in range(len(DC))}
    print("   " + f"{sn:<18}" + "".join(f"{100*Tc[i,j]:>16.1f}%" for j in range(len(DC))))
# aporte de cada partido al voto de Paloma-consulta (en votos)
print("\n   Aporte estimado a los 3,16 M de Paloma-consulta:")
apal = {sn: Tc[i, 0]*tot[sn] for i, sn in enumerate(SRC)}
spal = sum(apal.values())
out['aporte_a_palomaC'] = {}
for sn in sorted(apal, key=lambda x: -apal[x]):
    if apal[sn]/spal > 0.005:
        out['aporte_a_palomaC'][sn] = {'votos': int(apal[sn]), 'share_pct': round(100*apal[sn]/spal, 1)}
        print(f"      {sn:<18} ~{int(apal[sn]):>9,}  ({100*apal[sn]/spal:4.1f}%)")

# ===== (3) encadenado por partido: senado→consulta × consulta→1V =====
tasas = {}
for dn, Yd in zip(D1, [AB, PA, CE, SF, OT, BL, NU, ABST]):
    cf, _ = nnls(Xcon, np.array(Yd, float))
    tasas[dn] = cf
print("\n(3) ENCADENADO por partido (senado→consulta de (2) × tasas NNLS consulta→1V):")
out['encadenado'] = {}
print("   " + f"{'fuente':<18}" + "".join(f"{d:>11}" for d in ['Abelardo', 'Paloma', 'Cepeda', 'Fajardo']))
for i, sn in enumerate(SRC[:9]):
    fila = [Tc[i, 0], Tc[i, 1], Tc[i, 2], Tc[i, 3], Tc[i, 4]]  # palC,oviC,restoG,otras,noCons->MS
    out['encadenado'][sn] = {}
    vals = []
    for dn in ['Abelardo', 'Paloma', 'Cepeda', 'Fajardo']:
        cf = tasas[dn]
        v = fila[0]*cf[0] + fila[1]*cf[1] + fila[2]*cf[2] + fila[3]*cf[3] + fila[4]*cf[4]
        out['encadenado'][sn][dn] = round(100*v, 1)
        vals.append(v)
    print("   " + f"{sn:<18}" + "".join(f"{100*v:>10.1f}%" for v in vals))

# ===== (4) Goodman bivariado share~share (lo que daría la regresión "simple") =====
print("\n(4) GOODMAN BIVARIADO (pendiente OLS ponderada, share fuente vs share destino):")
Wn = np.array(W, float)
out['goodman_bivariado'] = {}
for i, sn in enumerate(SRC[:9]):
    x = Xsen[:, i]/Wn
    fila = {}
    for dn, Yd in [('Abelardo', AB), ('Paloma', PA), ('PalomaC', Ypal)]:
        y = np.array(Yd, float)/Wn
        xm = np.average(x, weights=Wn); ym = np.average(y, weights=Wn)
        bvar = np.average((x-xm)*(y-ym), weights=Wn)/np.average((x-xm)**2, weights=Wn)
        fila[dn] = round(100*bvar, 1)
    out['goodman_bivariado'][sn] = fila
    print(f"   {sn:<18} →Abelardo1V {fila['Abelardo']:>6.1f}%  →Paloma1V {fila['Paloma']:>6.1f}%  →PalomaC {fila['PalomaC']:>6.1f}%")

# ===== (5) cotas duras King por partido =====
print("\n(5) COTAS DURAS (Duncan-Davis/King) por partido:")
out['cotas'] = {}
for kk in PKEYS:
    b = bounds[kk]; t = tot[kk]
    out['cotas'][kk] = {d: [round(100*b[d][0]/t, 1), round(100*b[d][1]/t, 1)] for d in b}
    print(f"   {kk:<18} →PalomaC [{100*b['palC'][0]/t:4.1f}–{100*b['palC'][1]/t:4.1f}%]"
          f"  →Abelardo1V [{100*b['ab1v'][0]/t:4.1f}–{100*b['ab1v'][1]/t:4.1f}%]"
          f"  →Paloma1V [{100*b['pa1v'][0]/t:4.1f}–{100*b['pa1v'][1]/t:4.1f}%]")

# ===== (6) chequeos aritméticos contra los claims de La Silla =====
print("\n(6) CHEQUEOS ARITMÉTICOS:")
gran_tot = sum(Ypal)+sum(Yovi)+sum(Yotg)
print(f"   Gran Consulta total (join): {int(gran_tot):,} · CD senado: {int(tot['CD']):,}")
print(f"   Si solo 42% del CD votó la consulta (claim LSV), el CD habría puesto "
      f"{int(0.42*tot['CD']):,} de los {int(gran_tot):,} de la Gran (el {100*0.42*tot['CD']/gran_tot:.0f}%).")
print(f"   ¿Quién puso el resto? Conservador+U+CR+APC+MSN suman {int(tot['Conservador']+tot['La U']+tot['Cambio Radical']+tot['Alianza x Col']+tot['Salvación Nal']):,} votos senado.")
suma_p = {dn: sum(out['restringido_directo'][sn][dn]/100*tot[sn] for sn in SRC) for dn in ['Paloma', 'Abelardo']}
print(f"   Reconstrucción restringido directo: Paloma {int(suma_p['Paloma']):,} (real join {sum(PA):,}) · "
      f"Abelardo {int(suma_p['Abelardo']):,} (real {sum(AB):,})")

with open(os.path.join(OUTDIR, "contraste-lasilla.json"), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n→ {OUTDIR}/contraste-lasilla.json")
