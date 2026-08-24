#!/usr/bin/env python3
"""Foco Juvinao (centro de la noticia): (1) su proporción individual Cep/Abe/Resto
(EI condicional por puesto, su voto preferente propio), (2) perfil demográfico de
su TURF: % mujeres (censo), % jóvenes 18-35 / mayores 61+ (proyección edad 2026).
Comparado con el promedio de Bogotá."""
import csv, os
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"out")
BD="/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
RNG=np.random.default_rng(7); SHRINK=0.02
def n2(s):
    s=(s or '').strip().upper(); return f"{int(s):02d}" if s.isdigit() else s

# puestos_bogota: juvinao + presi
rows=list(csv.DictReader(open(os.path.join(OUT,'puestos_bogota.csv'))))
key=lambda r:(n2(r['zz']),n2(r['pp']))
juv={key(r):float(r['juvinao']) for r in rows}
cep={key(r):float(r['cepeda']) for r in rows}; abe={key(r):float(r['abelardo']) for r in rows}
presT={key(r):float(r['pres_turnout']) for r in rows}

# género por puesto (COMUNAS_DATA, censo 2026)
gen={}
with open(os.path.join(BD,'COMUNAS_DATA.csv'),encoding='utf-8',errors='replace') as f:
    r=csv.reader(f,delimiter=';'); next(r)
    for row in r:
        if row[0]=='16': gen[(n2(row[2]),n2(row[3]))]={'muj':int(row[12]),'tot':int(row[14])}

# edad proyectada 2026 por puesto (w26): jóvenes b0-b3, adultos b4-b8, mayores b9
age={}
with open(os.path.join(BD,'output_edad_1v','w26-puesto.csv')) as f:
    for row in csv.DictReader(f):
        if not row['pcode'].startswith('16-001'): continue
        p=row['pcode'].split('-'); k=(n2(p[2]),n2(p[3]))
        b=[float(row[f'b{i}']) for i in range(10)]; tot=sum(b) or 1
        age[k]={'joven':sum(b[0:4])/tot,'adulto':sum(b[4:9])/tot,'mayor':b[9]/tot,'tot':tot}

K=[k for k in juv if k in gen and k in age and presT[k]>0]
jv=np.array([juv[k] for k in K]); pt=np.array([presT[k] for k in K])
ce=np.array([cep[k] for k in K]); ab=np.array([abe[k] for k in K]); rs=np.maximum(pt-ce-ab,0)

# ---- (1) proporción individual de Juvinao (EI condicional, regularizada) ----
Y=np.column_stack([ce,ab,rs])/pt[:,None]; m=np.array([ce.sum(),ab.sum(),rs.sum()])/pt.sum()
B0=np.column_stack([m,m]); P=len(K)
def proj(B):
    C=B.shape[0]; u=-np.sort(-B,0); css=np.cumsum(u,0)-1; j=np.arange(1,C+1)[:,None]
    rho=C-1-np.argmax((u-css/j>0)[::-1],0); tau=css[rho,np.arange(B.shape[1])]/(rho+1)
    return np.maximum(B-tau[None,:],0)
def fit(W,T,lam,it=6000):
    G=(W*T[:,None]).T@W; H=(Y*T[:,None]).T@W; eta=1/(2*(np.linalg.eigvalsh(G).max()+lam)); B=B0.copy()
    for _ in range(it):
        Bn=proj(B-eta*(2*(B@G-H)+2*lam*(B-B0)))
        if np.abs(Bn-B).max()<1e-12: return Bn
        B=Bn
    return B
x=np.clip(jv/pt,0,1); W=np.column_stack([x,1-x]); B=fit(W,pt,SHRINK*pt.sum())[:,0]
bs=np.array([fit(np.column_stack([(lambda s:(np.clip(jv[s]/pt[s],0,1)))(idx),1-np.clip(jv[idx]/pt[idx],0,1)]),pt[idx],SHRINK*pt[idx].sum(),it=3000)[:,0]
             for idx in [RNG.integers(0,P,P) for _ in range(200)]])
lo,hi=np.percentile(bs,2.5,0),np.percentile(bs,97.5,0)

# ---- (2) demografía del TURF (ponderado por voto de Juvinao) vs Bogotá ----
def wavg(vals,w): return float((np.array(vals)*w).sum()/w.sum())
muj=np.array([gen[k]['muj'] for k in K]); tot=np.array([gen[k]['tot'] for k in K])
jo=np.array([age[k]['joven'] for k in K]); ma=np.array([age[k]['mayor'] for k in K]); ad=np.array([age[k]['adulto'] for k in K])
# turf Juvinao (peso = sus votos) vs Bogotá (peso = censo/electorado)
muj_share=muj/tot
print("="*70)
print("JUVINAO · proporción individual (EI condicional por puesto):")
print(f"  Cepeda {B[0]*100:.0f}% ({lo[0]*100:.0f}-{hi[0]*100:.0f}) · "
      f"Abelardo {B[1]*100:.0f}% ({lo[1]*100:.0f}-{hi[1]*100:.0f}) · "
      f"Resto {B[2]*100:.0f}% ({lo[2]*100:.0f}-{hi[2]*100:.0f})")
print(f"  (votos preferente Juvinao en muestra: {jv.sum():,.0f})")
print("\nDEMOGRAFÍA DEL TURF (ponderada por el voto de Juvinao) vs Bogotá:")
print(f"  % mujeres (registradas):   turf {wavg(muj_share,jv)*100:.1f}%   Bogotá {muj.sum()/tot.sum()*100:.1f}%")
print(f"  % jóvenes 18-35 (proy):    turf {wavg(jo,jv)*100:.1f}%   Bogotá {wavg(jo,tot)*100:.1f}%")
print(f"  % adultos 36-60 (proy):    turf {wavg(ad,jv)*100:.1f}%   Bogotá {wavg(ad,tot)*100:.1f}%")
print(f"  % mayores 61+ (proy):      turf {wavg(ma,jv)*100:.1f}%   Bogotá {wavg(ma,tot)*100:.1f}%")
print("="*70)
print("NOTA: 'turf' = composición de los puestos donde Juvinao saca su voto, no el")
print("perfil causal de SUS votantes. Género: solo registrado por puesto (el método")
print("robusto mesa-EF necesita género por mesa, no disponible para 2026).")
