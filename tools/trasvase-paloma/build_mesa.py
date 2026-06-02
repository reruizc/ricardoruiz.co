#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trasvase de Paloma + Traición Cámara CD Bogotá — A NIVEL MESA (v3).

A nivel mesa (~110k unidades cruzadas, ~270 votantes c/u) la inferencia
ecológica SÍ se identifica: el método de las cotas de King da un intervalo
estrecho porque en cada mesa el solapamiento entre los votos de Paloma
(consulta, mar) y los de Abelardo/Paloma (1V, may) está acotado.

Fuentes (todas mesa-level):
  preconteo presidencial 1V  → PRECONTEO_1V_2026_MESA_nombres_corregidos.csv
  escrutinio congreso+consulta 8-mar → DEPTOS_DECLARADOS/MMV_XXX_*.csv (42)
  censo por puesto 2026      → censos-puesto-2026.json (para base de la cota inferior)

Llave de mesa = dep-mun-zona-puesto-mesa (zona/puesto/mesa normalizados a int;
mesas alfanuméricas del exterior se conservan como string).

Salida: Bases de datos/output_trasvase/trasvase-paloma-mesa.json
"""
import csv, json, os, sys, glob
import numpy as np
from scipy.optimize import minimize, nnls

csv.field_size_limit(1 << 24)
ROOT = "/Users/ricardoruiz/ricardoruiz.co"
PRECONTEO = os.path.join(ROOT, "Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
MMV_DIR   = os.path.join(ROOT, "Bases de datos/DEPTOS_DECLARADOS")
MMV_BOG   = os.path.join(MMV_DIR, "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")
CENSO     = os.path.join(ROOT, "Bases de datos/censos-puesto-2026.json")
OUT       = os.path.join(ROOT, "Bases de datos/output_trasvase/trasvase-paloma-mesa.json")

PRES_CANDS = ['Iván Cepeda','Santiago Botero','Abelardo De La Espriella','Mauricio Lizcano',
              'Miguel Uribe','Sondra Macollins','Roy Barreras','Carlos Caicedo',
              'Gustavo Matamoros','Paloma Valencia','Sergio Fajardo','Gilberto Murillo','Claudia López']
PALOMA_GRAN = 'PALOMA SUSANA VALENCIA LASERNA'

def nz(x):
    x=str(x).strip()
    return str(int(x)) if x.isdigit() else x.upper()
def mkey(dep,mun,zona,pue,mesa):
    return f"{dep}-{mun}-{nz(zona)}-{nz(pue)}-{nz(mesa)}"
def pkey_pad(dep,mun,zona,pue):
    z = f"{int(zona):02d}" if str(zona).strip().isdigit() else str(zona).strip()
    p = f"{int(pue):02d}" if str(pue).strip().isdigit() else str(pue).strip()
    return f"{dep}-{mun}-{z}-{p}"

# ---------- presidencial (mesa) ----------
def load_pres_mesa():
    pres={}; nmesas={}
    with open(PRECONTEO, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            dep=row['cod_departamento']; mun=row['cod_municipio']
            zona=row['zona']; pue=row['puesto']; mesa=row['num_mesa']
            k=mkey(dep,mun,zona,pue,mesa)
            ab=int(row['Abelardo De La Espriella']or 0); pa=int(row['Paloma Valencia']or 0)
            ce=int(row['Iván Cepeda']or 0); mu=int(row['Miguel Uribe']or 0)
            sf=int(row['Sergio Fajardo']or 0); bl=int(row['votos_blanco']or 0)
            urna=int(row['total_votos_urna']or 0)
            otros=sum(int(row[c]or 0) for c in PRES_CANDS
                      if c not in ('Abelardo De La Espriella','Paloma Valencia','Iván Cepeda','Miguel Uribe','Sergio Fajardo'))
            pres[k]={'ab':ab,'pa':pa,'ce':ce,'mu':mu,'sf':sf,'bl':bl,'ot':otros,'urna':urna}
            pp=pkey_pad(dep,mun,zona,pue); nmesas[pp]=nmesas.get(pp,0)+1
    return pres, nmesas

# ---------- gran consulta nacional (mesa) ----------
def load_gran_mesa():
    cons={}
    files=[f for f in glob.glob(os.path.join(MMV_DIR,"MMV_XXX_*.csv")) if "CITREP" not in f]
    for fp in sorted(files):
        with open(fp, encoding='utf-8-sig', newline='') as f:
            rd=csv.reader(f, delimiter=';')
            next(rd, None)
            for c in rd:
                if len(c)<19: continue
                if c[10]!='06' or c[13]!='0200': continue   # CORCODIGO consultas, PAR gran
                k=mkey(c[0],c[2],c[4],c[5],c[7])
                v=int(c[18] or 0)
                d=cons.get(k)
                if d is None: d=cons[k]={'pal':0,'otg':0}
                if c[17]==PALOMA_GRAN: d['pal']+=v
                else: d['otg']+=v
        print(f"  · {os.path.basename(fp)}", file=sys.stderr)
    return cons

# ---------- cámara CD Bogotá (mesa) ----------
def load_cam_cd_bogota():
    cand_tot={}; cand_mesa={}
    with open(MMV_BOG, encoding='utf-8-sig', newline='') as f:
        rd=csv.reader(f, delimiter=';')
        next(rd, None)
        for c in rd:
            if len(c)<19: continue
            if c[10]!='02': continue                       # CAMARA
            if 'CENTRO DEMOCR' not in c[14].upper(): continue  # PARNOMBRE = CD
            if c[15]=='000': continue                       # saltar voto por la lista
            nm=c[17]; v=int(c[18] or 0)
            k=mkey(c[0],c[2],c[4],c[5],c[7])
            cand_tot[nm]=cand_tot.get(nm,0)+v
            cand_mesa.setdefault(nm,{})[k]=cand_mesa.get(nm,{}).get(k,0)+v
    return cand_tot, cand_mesa

# ============================================================
# TRASVASE — método de cotas + regresión (mesa)
# ============================================================
def trasvase(pres, cons, nmesas, censo):
    keys=sorted(set(pres)&set(cons))
    # base censal por mesa
    def mesa_censo(k):
        dep,mun,z,p,m=k.split('-')
        pp=pkey_pad(dep,mun,z,p) if z.isdigit() and p.isdigit() else None
        c=censo.get(pp) if pp else None
        nm=nmesas.get(pp,1) if pp else 1
        if c: return c/max(nm,1)
        return None
    tot_pal=0
    # acumuladores de cotas para destinos clave
    DST={'ab':'Abelardo De La Espriella','pa':'Se quedó con Paloma','ce':'Iván Cepeda','mu':'Miguel Uribe','sf':'Sergio Fajardo'}
    lo={d:0.0 for d in DST}; hi={d:0.0 for d in DST}
    # diseño regresión
    Sx=[];AB=[];PA=[];CE=[];MU=[];SF=[];OT=[];BL=[];ABST=[]
    cov_lo=0; n_lo=0
    for k in keys:
        c=cons[k]; pr=pres[k]
        P=c['pal']
        if P<=0:
            # aún sirve para la regresión como fuente OtrosGran/Resto
            pass
        tot_pal+=P
        N=mesa_censo(k)
        cand_pres=pr['ab']+pr['pa']+pr['ce']+pr['mu']+pr['sf']+pr['ot']+pr['bl']
        if N is None or N< max(cand_pres, P+c['otg']):
            N=max(cand_pres, P+c['otg'])
        # cotas para Paloma→destino
        if P>0 and N:
            for d,col in [('ab','ab'),('pa','pa'),('ce','ce'),('mu','mu'),('sf','sf')]:
                A=pr[col]
                lo[d]+= max(0.0, P + A - N)
                hi[d]+= min(P, A)
            n_lo+=1
        # regresión: fuentes [Paloma, OtrosGran, Resto]
        resto=max(0.0, N - P - c['otg'])
        Sx.append([P, c['otg'], resto])
        AB.append(pr['ab']);PA.append(pr['pa']);CE.append(pr['ce']);MU.append(pr['mu'])
        SF.append(pr['sf']);OT.append(pr['ot']);BL.append(pr['bl'])
        ABST.append(max(0.0, N - cand_pres))
    bounds={}
    for d in DST:
        bounds[d]={'destino':DST[d],
                   'lo':round(100*lo[d]/tot_pal,1),'hi':round(100*hi[d]/tot_pal,1)}

    # regresión acotada SLSQP (suma de filas=1)
    S=np.array(Sx,float)
    Ymat=np.column_stack([AB,PA,CE,MU,SF,OT,BL,ABST]).astype(float)
    A=S.T@S; B=S.T@Ymat; sc=A.max(); A/=sc; B/=sc
    nS,nD=3,8
    def f(x):
        T=x.reshape(nS,nD); return sum(T[:,c]@A@T[:,c]-2*B[:,c]@T[:,c] for c in range(nD))
    def g(x):
        T=x.reshape(nS,nD); G=np.zeros_like(T)
        for c in range(nD): G[:,c]=2*(A@T[:,c]-B[:,c])
        return G.ravel()
    conseq=[{'type':'eq','fun':(lambda x,b=b: x.reshape(nS,nD)[b,:].sum()-1)} for b in range(nS)]
    res=minimize(f,np.full(nS*nD,1/nD),jac=g,method='SLSQP',bounds=[(0,1)]*nS*nD,
                 constraints=conseq,options={'maxiter':800,'ftol':1e-11})
    prow=res.x.reshape(nS,nD)[0]
    reg_labels=['Abelardo De La Espriella','Se quedó con Paloma','Iván Cepeda','Miguel Uribe','Sergio Fajardo','Otros','Voto en blanco','Abstención/no votó']
    reg=[{'destino':reg_labels[i],'pct':round(100*max(0,prow[i]),1),
          'votos_est':int(round(max(0,prow[i])*tot_pal))} for i in range(nD)]
    reg.sort(key=lambda x:-x['pct'])

    # contexto bastiones (descriptivo)
    bast=[]
    for k in keys:
        c=cons[k]; g_=c['pal']+c['otg']
        if g_<30: continue
        bast.append((c['pal']/g_,k))
    bast.sort(reverse=True)
    topk=[k for sh,k in bast if sh>=0.60]
    A2=P2=CE2=tot2=0
    for k in topk:
        pr=pres[k];A2+=pr['ab'];P2+=pr['pa'];CE2+=pr['ce'];tot2+=pr['urna']
    cross={'n_mesas':len(topk),'abelardo_pct':round(100*A2/tot2,1),
           'paloma_pct':round(100*P2/tot2,1),'cepeda_pct':round(100*CE2/tot2,1)}

    return {'paloma_consulta_total':tot_pal,'n_mesas':len(keys),'n_mesas_cota':n_lo,
            'cotas':bounds,'regresion':reg,'bastiones':cross}

# ============================================================
# TRAICIÓN — Cámara CD Bogotá (mesa)
# ============================================================
def traicion(pres, cand_tot, cand_mesa):
    elected=set(nm for nm,_ in sorted(cand_tot.items(),key=lambda x:-x[1])[:6])
    bog=[k for k in pres if k.startswith('16-')]
    A_b=sum(pres[k]['ab'] for k in bog); P_b=sum(pres[k]['pa'] for k in bog)
    lean_bog=A_b/(A_b+P_b)
    out=[]
    for nm,total in cand_tot.items():
        if total<3000: continue
        wA=wP=wC=wU=0.0
        for k,w in cand_mesa[nm].items():
            pr=pres.get(k)
            if not pr: continue
            wA+=w*pr['ab']; wP+=w*pr['pa']; wC+=w*pr['ce']; wU+=w*pr['urna']
        if wA+wP<=0: continue
        lean=wA/(wA+wP)
        out.append({'nombre':nm,'votos_camara':total,'electo':nm in elected,
            'lean_abelardo':round(100*lean,1),'lean_paloma':round(100*(1-lean),1),
            'traicion':round(100*(lean-lean_bog),1),
            'base_abelardo_pct':round(100*wA/wU,1) if wU else 0,
            'base_paloma_pct':round(100*wP/wU,1) if wU else 0,
            'base_cepeda_pct':round(100*wC/wU,1) if wU else 0})
    out.sort(key=lambda x:-x['lean_abelardo'])
    return {'curules':6,'baseline_abelardo_pct':round(100*lean_bog,1),
            'baseline_paloma_pct':round(100*(1-lean_bog),1),
            'baseline_abelardo':A_b,'baseline_paloma':P_b,'candidatos':out}

def main():
    print("Presidencial mesa…",file=sys.stderr)
    pres,nmesas=load_pres_mesa(); print(f"  {len(pres):,} mesas",file=sys.stderr)
    censo=json.load(open(CENSO))['porPuesto']
    print("Gran consulta mesa (42 MMV)…",file=sys.stderr)
    cons=load_gran_mesa(); print(f"  {len(cons):,} mesas con gran consulta",file=sys.stderr)
    print("Trasvase mesa…",file=sys.stderr)
    tr=trasvase(pres,cons,nmesas,censo)
    print("Cámara CD Bogotá mesa…",file=sys.stderr)
    ct,cm=load_cam_cd_bogota()
    tc=traicion(pres,ct,cm)
    json.dump({'v':'2026-06-01-mesa','trasvase':tr,'traicion':tc},open(OUT,'w'),ensure_ascii=False,indent=1)
    print(f"✓ {OUT}\n",file=sys.stderr)

    print("="*70)
    print(f"TRASVASE PALOMA (MESA) — consulta {tr['paloma_consulta_total']:,} votos · {tr['n_mesas']:,} mesas cruzadas")
    print("="*70)
    print("Cotas de King (mín–máx defendible) + punto de regresión:")
    reg={r['destino']:r for r in tr['regresion']}
    for d,b in tr['cotas'].items():
        nm=b['destino']; pt=reg.get(nm,{}).get('pct','—')
        print(f"  {nm:<26} cota [{b['lo']:>5.1f}% – {b['hi']:>5.1f}%]   punto ~{pt}%")
    print("\n  Regresión completa (punto):")
    for r in tr['regresion']:
        print(f"    {r['destino']:<24}{r['pct']:>5.1f}%  ~{r['votos_est']:>9,}")
    b=tr['bastiones']
    print(f"\n  Bastiones (Paloma ≥60% gran consulta, {b['n_mesas']} mesas): voto 1V del puesto → Abelardo {b['abelardo_pct']}% · Paloma {b['paloma_pct']}% · Cepeda {b['cepeda_pct']}%")

    print("\n"+"="*70)
    print("TRAICIÓN CD BOGOTÁ (MESA) — Abelardo "
          f"{tc['baseline_abelardo_pct']}% vs Paloma {tc['baseline_paloma_pct']}% (duelo Bogotá)")
    print("="*70)
    print(f"  {'Representante':<33}{'el':>3}{'votos':>9}{'→Abel':>8}{'→Palo':>7}  base Ab/Pa/Ce")
    for c in tc['candidatos']:
        e='★' if c['electo'] else ' '
        print(f"  {c['nombre'][:32]:<33}{e:>3}{c['votos_camara']:>9,}{c['lean_abelardo']:>7.1f}%{c['lean_paloma']:>6.1f}%  {c['base_abelardo_pct']:>4.0f}/{c['base_paloma_pct']:>2.0f}/{c['base_cepeda_pct']:>3.0f}")
    print("  ★ = electo (top-6 preferente)")

if __name__=='__main__': main()
