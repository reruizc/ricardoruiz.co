#!/usr/bin/env python3
"""Paso 4 — robustez: misma pregunta con la OTRA formulación (base = censo,
abstención de mayo explícita como 4º destino). Confirma que el reparto 3-way
(Cepeda/Abelardo/Resto entre votantes) no depende de la formulación, y recupera
qué % de los votantes de cada lista NO volvió a votar en mayo.

W = [bloc/censo, resto/censo] · Y = [Cepeda, Abelardo, Resto, NoVotóMayo]/censo
"""
import csv, os
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
RNG = np.random.default_rng(7); SHRINK = 0.025; NB = 300
SRC = {'pacto':'Lista Pacto Histórico','briceno':'Daniel Briceño',
       'cd_resto':'Resto Centro Democrático','verde':'Lista Alianza Verde',
       'liberal':'Lista Partido Liberal','salvacion':'Lista Salvación Nacional'}

def proj_simplex_cols(B):
    C = B.shape[0]; u = -np.sort(-B, axis=0); css = np.cumsum(u, axis=0)-1.0
    j = np.arange(1, C+1)[:, None]; cond = u-css/j > 0
    rho = C-1-np.argmax(cond[::-1, :], axis=0)
    tau = css[rho, np.arange(B.shape[1])]/(rho+1)
    return np.maximum(B-tau[None, :], 0.0)

def fit_qp_reg(W, Y, T, B0, lam, iters=6000, tol=1e-12, start=None):
    G = (W*T[:, None]).T@W; H = (Y*T[:, None]).T@W
    eta = 1.0/(2*(np.linalg.eigvalsh(G).max()+lam))
    B = (B0 if start is None else start).copy()
    for _ in range(iters):
        Bn = proj_simplex_cols(B - eta*(2*(B@G-H)+2*lam*(B-B0)))
        if np.abs(Bn-B).max() < tol: return Bn
        B = Bn
    return B

rows = list(csv.DictReader(open(os.path.join(OUT, 'puestos_bogota.csv'))))
g = lambda c: np.array([float(r[c]) for r in rows])
censo, camT, presT = g('censo'), g('cam_turnout'), g('pres_turnout')
cep, abe = g('cepeda'), g('abelardo')
resto = np.maximum(presT-cep-abe, 0)
censo_eff = np.maximum.reduce([censo, camT, presT])
may_abst = np.maximum(censo_eff-presT, 0)
col = {c: g(c) for c in ['pacto_list','briceno','cd','verde','liberal','salvacion']}
V = {'pacto':col['pacto_list'],'briceno':col['briceno'],
     'cd_resto':np.maximum(col['cd']-col['briceno'],0),
     'verde':col['verde'],'liberal':col['liberal'],'salvacion':col['salvacion']}
Y = np.column_stack([cep, abe, resto, may_abst])/censo_eff[:, None]
m = np.array([cep.sum(), abe.sum(), resto.sum(), may_abst.sum()])/censo_eff.sum()
B0 = np.column_stack([m, m]); T = censo_eff; P = len(T)

def fit(v):
    x = np.clip(v/censo_eff, 0, 1); W = np.column_stack([x, 1-x])
    B = fit_qp_reg(W, Y, T, B0, SHRINK*T.sum())
    return B[:, 0]

print("ROBUSTEZ · formulación censo-base con abstención de mayo explícita (shrink 0.025)\n")
print(f"{'Lista':26}{'Cep':>6}{'Abe':>6}{'Res':>6}{'NoVotó':>8}   "
      f"{'-> reparto entre VOTANTES (Cep/Abe/Res)':>40}")
print("-"*96)
for s in SRC:
    B = fit(V[s]); v3 = B[:3]; r3 = v3/v3.sum()*100
    print(f"{SRC[s][:25]:26}{B[0]*100:>5.0f}%{B[1]*100:>5.0f}%{B[2]*100:>5.0f}%{B[3]*100:>7.0f}%"
          f"      {r3[0]:>12.0f} /{r3[1]:>4.0f} /{r3[2]:>4.0f}")
print("\nNoVotó = % de los votantes de marzo de esa lista que NO votó en mayo.")
print("La última columna (reparto entre votantes) debe coincidir con el paso 3.")
