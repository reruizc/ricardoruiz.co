#!/usr/bin/env python3
"""Paso 3 (robusto · blocs de partido) — ¿a dónde fueron en la presidencial 1V
los votantes de cada representante electo a la Cámara por Bogotá?

La EI identifica la transferencia a nivel de la LISTA/partido (unidad grande y
geográficamente coherente), no del candidato individual de lista abierta (sus
perfiles son casi colineales -> no separables). Por eso se estima por bloc:
  pacto (924k, lista cerrada -> 8 electos) · briceno (262k, individual: domina
  y se identifica) · cd_resto (CD sin Briceño -> 5 electos menores) · verde
  (243k -> 2) · liberal (112k -> 1) · salvacion (188k -> 1).

Estimador: King's EI 2x3 por bloc, regularizada (shrinkage GLOBAL al prior
citywide; estable para fuentes grandes). x_p = votos_bloc(p)/votantes_presi(p);
Y_p = [Cepeda,Abelardo,Resto]/votantes_presi(p). IC95 bootstrap (warm-start) ·
cotas Duncan-Davis · contraste vs ingenuo (turf).
"""
import csv, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RNG = np.random.default_rng(20260616)
B_BOOT = int(os.environ.get('EI_BOOT', 500))
SHRINK = float(os.environ.get('EI_SHRINK', 0.025))   # peso global del prior

# bloc -> (label, partido)
SRCMETA = {
 'pacto':    ('Lista Pacto Histórico', 'Pacto Histórico'),
 'briceno':  ('Daniel Briceño',        'Centro Democrático'),
 'cd_resto': ('Resto Centro Democrático', 'Centro Democrático'),
 'verde':    ('Lista Alianza Verde',   'Alianza Verde'),
 'liberal':  ('Lista Partido Liberal', 'Partido Liberal'),
 'salvacion':('Lista Salvación Nacional', 'Salvación Nacional'),
 # senado
 'sen_pacto':    ('Senado · Pacto Histórico', 'Pacto Histórico'),
 'sen_cd':       ('Senado · Centro Democrático', 'Centro Democrático'),
 'sen_alianza':  ('Senado · Alianza por Colombia', 'Alianza Verde/coalición'),
 'sen_ahora':    ('Senado · Ahora Colombia', 'MIRA · Dignidad'),
 'sen_salvacion':('Senado · Salvación Nacional', 'Salvación Nacional'),
 'sen_liberal':  ('Senado · Partido Liberal', 'Partido Liberal'),
}
SOURCES_CAM = ['pacto','briceno','cd_resto','verde','liberal','salvacion']
SOURCES_SEN = ['sen_pacto','sen_cd','sen_alianza','sen_ahora','sen_salvacion','sen_liberal']
SOURCES = SOURCES_CAM + SOURCES_SEN
# 10 senadores más votados en Bogotá -> su lista
SEN10 = [('Carlos E. Guevara','MIRA · Dignidad','sen_ahora'),
         ('Andrea Padilla','Alianza Verde/coalición','sen_alianza'),
         ('Enrique Gómez','Salvación Nacional','sen_salvacion'),
         ('Sara Castellanos','Salvación Nacional','sen_salvacion'),
         ('Jennifer Pedraza','MIRA · Dignidad','sen_ahora'),
         ('Gersson Vargas','Partido Liberal','sen_liberal'),
         ('Miguel Forero','Alianza Verde/coalición','sen_alianza'),
         ('Jota Pe Hernández','Alianza Verde/coalición','sen_alianza'),
         ('Luis Carlos Rúa','Alianza Verde/coalición','sen_alianza'),
         ('Horacio José Serpa','Partido Liberal','sen_liberal')]
PACTO8 = ['María Fernanda Carrascal Rojas','Daniel Mauricio Monroy Hernández',
          'Laura Daniela Beltrán Palomares','Heráclito Landínez Suárez',
          'María del Mar Pizarro García','Jairo León Vargas',
          'Claudia Teresa Romero Nader','Gabriel Becerra Yañez']
CD5 = ['José Jaime Uscátegui','David Cote','Nelly Patricia Mosquera',
       'Jesús Salim Lorduy','Luz Marina Gordillo']

def proj_simplex_cols(B):
    C = B.shape[0]
    u = -np.sort(-B, axis=0); css = np.cumsum(u, axis=0) - 1.0
    j = np.arange(1, C + 1)[:, None]; cond = u - css / j > 0
    rho = C - 1 - np.argmax(cond[::-1, :], axis=0)
    tau = css[rho, np.arange(B.shape[1])] / (rho + 1)
    return np.maximum(B - tau[None, :], 0.0)

def fit_qp_reg(W, Y, T, B0, lam, iters=6000, tol=1e-12, start=None):
    G = (W * T[:, None]).T @ W; H = (Y * T[:, None]).T @ W
    eta = 1.0 / (2 * (np.linalg.eigvalsh(G).max() + lam))
    B = (B0 if start is None else start).copy()
    for _ in range(iters):
        Bn = proj_simplex_cols(B - eta * (2*(B @ G - H) + 2*lam*(B - B0)))
        if np.abs(Bn - B).max() < tol:
            return Bn
        B = Bn
    return B

def duncan_davis(W, Y, T):
    n_a = W * T[:, None]; V = Y * T[:, None]
    C, A = Y.shape[1], W.shape[1]
    lo = np.zeros((C, A)); hi = np.zeros((C, A))
    for a in range(A):
        rest = T - n_a[:, a]
        for c in range(C):
            lo[c, a] = np.maximum(0.0, V[:, c] - rest).sum()
            hi[c, a] = np.minimum(V[:, c], n_a[:, a]).sum()
    tot = n_a.sum(axis=0)
    return lo / tot, hi / tot

# ---------- datos por puesto ----------
rows = list(csv.DictReader(open(os.path.join(OUT, 'puestos_bogota.csv'))))
g = lambda c: np.array([float(r[c]) for r in rows])
presT, cep, abe = g('pres_turnout'), g('cepeda'), g('abelardo')
resto = np.maximum(presT - cep - abe, 0)
ok = presT > 0
presT, cep, abe, resto = presT[ok], cep[ok], abe[ok], resto[ok]
_scols = ['pacto_list','briceno','cd','verde','liberal','salvacion',
          'sen_pacto','sen_cd','sen_alianza','sen_ahora','sen_salvacion','sen_liberal']
col = {c: g(c)[ok] for c in _scols}
V = {'pacto': col['pacto_list'], 'briceno': col['briceno'],
     'cd_resto': np.maximum(col['cd'] - col['briceno'], 0),
     'verde': col['verde'], 'liberal': col['liberal'], 'salvacion': col['salvacion']}
for s in SOURCES_SEN:
    V[s] = col[s]
P = len(presT)
Y = np.column_stack([cep, abe, resto]) / presT[:, None]
m = np.array([cep.sum(), abe.sum(), resto.sum()]) / presT.sum()
B0 = np.column_stack([m, m])

def naive(v):
    s = v.sum()
    return np.array([(v*cep/presT).sum(), (v*abe/presT).sum(),
                     (v*resto/presT).sum()]) / s

def fit_src(v, nb=B_BOOT):
    x = np.clip(v / presT, 0, 1)
    W = np.column_stack([x, 1 - x])
    lam = SHRINK * presT.sum()
    B = fit_qp_reg(W, Y, presT, B0, lam)
    dd_lo, dd_hi = duncan_davis(W, Y, presT)
    boots = np.empty((nb, 3))
    for b in range(nb):
        idx = RNG.integers(0, P, P)
        boots[b] = fit_qp_reg(W[idx], Y[idx], presT[idx], B0,
                              SHRINK*presT[idx].sum(), start=B)[:, 0]
    return (B[:, 0], np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0),
            (dd_lo[:, 0], dd_hi[:, 0]), naive(v))

res = {s: fit_src(V[s]) for s in SOURCES}

# ---------- mapeo a los 18 ----------
electos18 = [(n, 'Pacto Histórico', 'pacto') for n in PACTO8]
electos18 += [('Daniel Briceño', 'Centro Democrático', 'briceno')]
electos18 += [(n, 'Centro Democrático', 'cd_resto') for n in CD5]
electos18 += [('Catherine Juvinao', 'Alianza Verde', 'verde'),
              ('Mauricio Toro', 'Alianza Verde', 'verde'),
              ('Bleidy Pérez Ballestas', 'Partido Liberal', 'liberal'),
              ('Carol Borda', 'Salvación Nacional', 'salvacion')]

# ---------- reporte ----------
L = []
tot = presT.sum()
L.append("="*98)
L.append("DESTINO EN LA PRESIDENCIAL 1V (31-may) DE LOS VOTANTES DE CADA LISTA QUE ELIGIÓ")
L.append("REPRESENTANTE A LA CÁMARA POR BOGOTÁ (8-mar) — inferencia ecológica regularizada")
L.append("="*98)
L.append(f"{P} puestos · {tot:,.0f} votantes presidenciales · Bogotá: Cepeda "
         f"{cep.sum()/tot*100:.1f}% · Abelardo {abe.sum()/tot*100:.1f}% · Resto {resto.sum()/tot*100:.1f}%")
L.append(f"shrink global al prior = {SHRINK}\n")
L.append("% de los votantes de cada lista que en mayo votaron por… (entre quienes volvieron a votar)")
L.append("IC95% bootstrap en paréntesis · ordenado por afinidad con Cepeda\n")
h = f"{'Lista (Cámara)':28}{'votos':>9}   {'→ Cepeda':>15}{'→ Abelardo':>15}{'→ Resto':>14}"
L.append(h); L.append("-"*len(h))
order = sorted(SOURCES_CAM, key=lambda s: -res[s][0][0])
for s in order:
    B, lo, hi, dd, nv = res[s]
    def c(i): return f"{B[i]*100:4.0f} ({lo[i]*100:3.0f}-{hi[i]*100:3.0f})"
    L.append(f"{SRCMETA[s][0][:27]:28}{int(V[s].sum()):>9,}   {c(0):>15}{c(1):>15}{c(2):>14}")
L.append("\n'Resto' = demás candidatos presidenciales + voto en blanco/nulo.")
L.append("\nEI vs INGENUO (turf = cómo votó en mayo el electorado donde la lista es fuerte) Cep/Abe/Res:")
for s in order:
    B, *_, nv = res[s]
    L.append(f"  {SRCMETA[s][0][:26]:28}  EI {B[0]*100:3.0f}/{B[1]*100:3.0f}/{B[2]*100:3.0f}"
             f"   ingenuo {nv[0]*100:3.0f}/{nv[1]*100:3.0f}/{nv[2]*100:3.0f}")
L.append("\nCotas Duncan-Davis (rango lógicamente posible) Cepeda / Abelardo:")
for s in order:
    _,_,_, dd, _ = res[s]
    L.append(f"  {SRCMETA[s][0][:26]:28}  Cep [{dd[0][0]*100:3.0f}-{dd[1][0]*100:3.0f}]"
             f"  Abe [{dd[0][1]*100:3.0f}-{dd[1][1]*100:3.0f}]")

L.append("\n" + "="*98)
L.append("LOS 18 ELECTOS — % de sus votantes que en mayo votó Cepeda / Abelardo / Resto")
L.append("(Pacto: 8 comparten lista cerrada · 5 CD menores: perfil del 'resto CD' · Verde: 2 comparten)")
L.append("-"*98)
L.append(f"{'#':>2} {'Representante':33}{'Partido':20}{'Cepeda':>8}{'Abelardo':>10}{'Resto':>8}")
for i, (nm, part, src) in enumerate(electos18, 1):
    B = res[src][0]
    L.append(f"{i:>2} {nm[:32]:33}{part[:19]:20}{B[0]*100:>7.0f}%{B[1]*100:>9.0f}%{B[2]*100:>7.0f}%")

# ---------- SENADO ----------
L.append("\n" + "="*98)
L.append("SENADO · DESTINO EN 1V DE LOS VOTANTES DE CADA LISTA (6 listas) · % entre votantes de mayo")
L.append("-"*98)
ho = f"{'Lista (Senado)':30}{'votos':>9}   {'→ Cepeda':>15}{'→ Abelardo':>15}{'→ Resto':>14}"
L.append(ho); L.append("-"*len(ho))
for s in sorted(SOURCES_SEN, key=lambda s: -res[s][0][0]):
    B, lo, hi, dd, nv = res[s]
    def c(i): return f"{B[i]*100:4.0f} ({lo[i]*100:3.0f}-{hi[i]*100:3.0f})"
    L.append(f"{SRCMETA[s][0][:29]:30}{int(V[s].sum()):>9,}   {c(0):>15}{c(1):>15}{c(2):>14}")
L.append("\nLOS 10 SENADORES MÁS VOTADOS EN BOGOTÁ — perfil de su lista (no separables individualmente):")
L.append(f"{'#':>2} {'Senador/a':24}{'Lista':26}{'Cepeda':>8}{'Abelardo':>10}{'Resto':>8}")
for i, (nm, part, src) in enumerate(SEN10, 1):
    B = res[src][0]
    L.append(f"{i:>2} {nm[:23]:24}{part[:25]:26}{B[0]*100:>7.0f}%{B[1]*100:>9.0f}%{B[2]*100:>7.0f}%")
rep = "\n".join(L); print(rep)
open(os.path.join(OUT, 'ei_reporte.txt'), 'w').write(rep)

out = []
for i, (nm, part, src) in enumerate(electos18, 1):
    B, lo, hi, dd, nv = res[src]
    nota = {'pacto':'lista cerrada · perfil compartido (8 electos)',
            'cd_resto':'bloque resto-CD · no separable individualmente',
            'verde':'lista Verde · perfil compartido (2 electos)'}.get(src, '')
    out.append(dict(rank=i, nombre=nm, partido=part, fuente=src,
        cepeda_pct=round(B[0]*100,1), cepeda_ic=f"{lo[0]*100:.0f}-{hi[0]*100:.0f}",
        abelardo_pct=round(B[1]*100,1), abelardo_ic=f"{lo[1]*100:.0f}-{hi[1]*100:.0f}",
        resto_pct=round(B[2]*100,1), resto_ic=f"{lo[2]*100:.0f}-{hi[2]*100:.0f}",
        naive_cep=round(nv[0]*100,1), naive_abe=round(nv[1]*100,1), naive_res=round(nv[2]*100,1),
        votos_lista=int(V[src].sum()), nota=nota))
with open(os.path.join(OUT, 'ei_resultados.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

souts = []
for i, (nm, part, src) in enumerate(SEN10, 1):
    B, lo, hi, dd, nv = res[src]
    souts.append(dict(rank=i, senador=nm, lista=SRCMETA[src][0], partido=part,
        cepeda_pct=round(B[0]*100,1), cepeda_ic=f"{lo[0]*100:.0f}-{hi[0]*100:.0f}",
        abelardo_pct=round(B[1]*100,1), abelardo_ic=f"{lo[1]*100:.0f}-{hi[1]*100:.0f}",
        resto_pct=round(B[2]*100,1), resto_ic=f"{lo[2]*100:.0f}-{hi[2]*100:.0f}",
        votos_lista_senado=int(V[src].sum())))
with open(os.path.join(OUT, 'ei_senado.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(souts[0].keys())); w.writeheader(); w.writerows(souts)
print(f"\n[out/ei_resultados.csv · {len(out)} electos | out/ei_senado.csv · {len(souts)} senadores · shrink={SHRINK}]")
