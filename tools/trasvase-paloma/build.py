#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trasvase de Paloma + Traición de la Cámara CD Bogotá. (v2 · EI acotada)

(1) TRASVASE NACIONAL — ¿hacia dónde migraron los ~3.25M de Paloma en la
    Gran Consulta (8-mar) en la 1ª vuelta (31-may)? Inferencia ecológica
    ACOTADA por puesto: base = censo electoral del puesto; fuentes (marzo)
    {Paloma, otros Gran Consulta, resto del electorado} y destinos (mayo)
    {Abelardo, Paloma, Cepeda, Miguel Uribe, Fajardo, otros, blanco,
    abstención}. Se resuelve una matriz de transferencia T con T>=0 y
    filas que suman 1 (mínimos cuadrados con restricciones, SLSQP). Eso
    obliga a que cada votante de Paloma se reparta entre 0 y 100% — el
    método de las cotas de King disciplina la estimación.

(2) TRAICIÓN CÁMARA BOGOTÁ — de los 6 representantes a la Cámara por Bogotá
    del Centro Democrático (lista de Paloma, voto preferente), ¿qué tanto
    de su base electoral votó Abelardo y no a Paloma en 1V? Afinidad
    ecológica por puesto ponderada por los votos de cada representante.

Fuentes:
  Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv
  Bases de datos/output_historicos_puestos/consulta-2026-gran/por-puesto.json
  Bases de datos/censos-puesto-2026.json
  /tmp/cam16_puestos.json  (S3 camara/departamentos/16/puestos.json)

Salida: Bases de datos/output_trasvase/trasvase-paloma.json
"""
import csv, json, os, sys
import numpy as np
from scipy.optimize import minimize

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
PRECONTEO = os.path.join(ROOT, "Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
CONSULTA  = os.path.join(ROOT, "Bases de datos/output_historicos_puestos/consulta-2026-gran/por-puesto.json")
CENSO     = os.path.join(ROOT, "Bases de datos/censos-puesto-2026.json")
CAM16     = "/tmp/cam16_puestos.json"
OUT       = os.path.join(ROOT, "Bases de datos/output_trasvase/trasvase-paloma.json")

PRES_CANDS = ['Iván Cepeda','Santiago Botero','Abelardo De La Espriella','Mauricio Lizcano',
              'Miguel Uribe','Sondra Macollins','Roy Barreras','Carlos Caicedo',
              'Gustavo Matamoros','Paloma Valencia','Sergio Fajardo','Gilberto Murillo','Claudia López']
GRAN = {
    'PALOMA SUSANA VALENCIA LASERNA':'Paloma Valencia',
    'MAURICIO CARDENAS SANTAMARIA':'Mauricio Cárdenas',
    'DAVID ANDRES LUNA SANCHEZ':'David Luna',
    'VICTORIA EUGENIA DAVILA HOYOS':'Vicky Dávila',
    'JUAN MANUEL GALAN PACHON':'Juan Manuel Galán',
    'JUAN CARLOS PINZON BUENO':'Juan Carlos Pinzón',
    'ANIBAL GAVIRIA CORREA':'Aníbal Gaviria',
    'ENRIQUE PENALOSA LONDONO':'Enrique Peñalosa',
    'JUAN DANIEL OVIEDO ARANGO':'Juan Daniel Oviedo',
}

def load_presidencial():
    pres = {}
    with open(PRECONTEO, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            k = f"{row['cod_departamento']}-{row['cod_municipio']}-{row['zona']}-{row['puesto']}"
            d = pres.get(k)
            if d is None:
                d = pres[k] = {c:0 for c in PRES_CANDS}; d['_blanco']=0; d['_urna']=0
            for c in PRES_CANDS: d[c]+=int(row[c] or 0)
            d['_blanco']+=int(row['votos_blanco'] or 0)
            d['_urna']  +=int(row['total_votos_urna'] or 0)
    return pres

def load_consulta():
    cons = json.load(open(CONSULTA))['puestos']; out={}
    for k,p in cons.items():
        v=p.get('v',{})
        rec={GRAN[n]:v.get(n,0) for n in GRAN}
        out[k]=rec
    return out

def load_censo():
    return json.load(open(CENSO))['porPuesto']

# ============================================================
# ANÁLISIS 1 — TRASVASE NACIONAL (EI acotada con censo)
# ============================================================
def analisis_trasvase(pres, cons, censo):
    keys = sorted(set(pres) & set(cons))
    DEST = ['Abelardo De La Espriella','Paloma Valencia','Iván Cepeda',
            'Miguel Uribe','Sergio Fajardo','_otros','_blanco','_abst']
    SRC  = ['Paloma','OtrosGran','Resto']
    rows_s=[]; rows_d=[]
    tot_paloma=0
    for k in keys:
        c=cons[k]; pr=pres[k]
        paloma = c['Paloma Valencia']
        otros_gran = sum(c[GRAN[n]] for n in GRAN if GRAN[n]!='Paloma Valencia')
        cand_pres = sum(pr[cc] for cc in PRES_CANDS) + pr['_blanco']
        N = max(int(censo.get(k,0)), cand_pres, paloma+otros_gran)
        resto = max(0, N - paloma - otros_gran)
        # destinos
        otros = sum(pr[cc] for cc in PRES_CANDS
                    if cc not in ('Abelardo De La Espriella','Paloma Valencia','Iván Cepeda','Miguel Uribe','Sergio Fajardo'))
        abst  = max(0, N - cand_pres)
        d=[pr['Abelardo De La Espriella'],pr['Paloma Valencia'],pr['Iván Cepeda'],
           pr['Miguel Uribe'],pr['Sergio Fajardo'],otros,pr['_blanco'],abst]
        rows_s.append([paloma,otros_gran,resto]); rows_d.append(d)
        tot_paloma+=paloma
    S=np.array(rows_s,float); D=np.array(rows_d,float)   # (n,3) (n,8)
    nS,nD=3,len(DEST)
    # precompute A = S^T S (3x3), Bc = S^T D[:,c]  → B (3 x 8)
    A=S.T@S; B=S.T@D
    scale=A.max()
    A/=scale; B/=scale
    def f(x):
        T=x.reshape(nS,nD); val=0.0
        for c in range(nD):
            tc=T[:,c]; val+= tc@A@tc - 2*(B[:,c]@tc)
        return val
    def g(x):
        T=x.reshape(nS,nD); G=np.zeros_like(T)
        for c in range(nD):
            G[:,c]=2*(A@T[:,c]-B[:,c])
        return G.ravel()
    # restricciones: cada fuente suma 1
    cons_eq=[]
    for b in range(nS):
        def mk(b):
            return lambda x: np.sum(x.reshape(nS,nD)[b,:])-1.0
        cons_eq.append({'type':'eq','fun':mk(b)})
    x0=np.full(nS*nD,1.0/nD)
    res=minimize(f,x0,jac=g,method='SLSQP',bounds=[(0,1)]*(nS*nD),
                 constraints=cons_eq,options={'maxiter':500,'ftol':1e-10})
    T=res.x.reshape(nS,nD)
    paloma_row=T[0,:]
    labels={'Abelardo De La Espriella':'Abelardo De La Espriella',
            'Paloma Valencia':'Se quedó con Paloma','Iván Cepeda':'Iván Cepeda',
            'Miguel Uribe':'Miguel Uribe','Sergio Fajardo':'Sergio Fajardo',
            '_otros':'Otros candidatos','_blanco':'Voto en blanco',
            '_abst':'Abstención / no votó 1V'}
    flujos=[]
    for i,d in enumerate(DEST):
        frac=max(0.0,float(paloma_row[i]))
        flujos.append({'destino':labels[d],'key':d,'frac':frac,
                       'pct':round(100*frac,1),'votos_est':int(round(frac*tot_paloma))})
    flujos.sort(key=lambda x:-x['frac'])

    # cross-check descriptivo honesto: bastiones de Paloma (voto del PUESTO completo)
    bast=[]
    for k in keys:
        c=cons[k]; gran=sum(c[GRAN[n]] for n in GRAN)
        if gran<50: continue
        bast.append((c['Paloma Valencia']/gran,k))
    bast.sort(reverse=True)
    top=[k for sh,k in bast if sh>=0.60]
    A2=P2=CE2=tot2=0
    for k in top:
        pr=pres[k]; A2+=pr['Abelardo De La Espriella']; P2+=pr['Paloma Valencia']; CE2+=pr['Iván Cepeda']; tot2+=pr['_urna']
    cross={'n_puestos':len(top),'nota':'voto del puesto completo en 1V donde Paloma ganó ≥60% de la Gran Consulta',
           'abelardo_pct':round(100*A2/tot2,1),'paloma_pct':round(100*P2/tot2,1),
           'cepeda_pct':round(100*CE2/tot2,1)}
    return {'paloma_consulta_total':tot_paloma,'n_puestos':len(keys),
            'flujos':flujos,'bastiones':cross,'fit_residual':float(res.fun)}

# ============================================================
# ANÁLISIS 2 — TRAICIÓN CÁMARA CD BOGOTÁ
# ============================================================
def analisis_traicion(pres):
    cam=json.load(open(CAM16)); PARTIDO='PARTIDO CENTRO DEMOCRÁTICO'
    cand_tot={}; cand_pue={}
    for p in cam:
        k=f"{p['dep_cod']}-{p['mun_cod']}-{p['zon_cod']}-{p['pue_cod_raw']}"
        for cc in p['candidatos'].get(PARTIDO,[]):
            nm=cc['nombre']; v=cc['votos']
            cand_tot[nm]=cand_tot.get(nm,0)+v
            cand_pue.setdefault(nm,{})[k]=cand_pue.get(nm,{}).get(k,0)+v
    elected=set(nm for nm,_ in sorted(cand_tot.items(),key=lambda x:-x[1])[:6])  # 6 curules
    # baseline Bogotá
    bog=[k for k in pres if k.startswith('16-')]
    A_b=sum(pres[k]['Abelardo De La Espriella'] for k in bog)
    P_b=sum(pres[k]['Paloma Valencia'] for k in bog)
    lean_bog=A_b/(A_b+P_b)
    ranked=[]
    for nm,total in cand_tot.items():
        if total<3000: continue
        wA=wP=wC=wAll=0.0
        for k,w in cand_pue[nm].items():
            pr=pres.get(k)
            if not pr: continue
            wA+=w*pr['Abelardo De La Espriella']; wP+=w*pr['Paloma Valencia']
            wC+=w*pr['Iván Cepeda']; wAll+=w*pr['_urna']
        if wA+wP<=0: continue
        lean=wA/(wA+wP)
        ranked.append({'nombre':nm,'votos_camara':total,'electo':nm in elected,
            'lean_abelardo':round(100*lean,1),'lean_paloma':round(100*(1-lean),1),
            'traicion':round(100*(lean-lean_bog),1),
            'base_abelardo_pct':round(100*wA/wAll,1) if wAll else 0,
            'base_paloma_pct':round(100*wP/wAll,1) if wAll else 0,
            'base_cepeda_pct':round(100*wC/wAll,1) if wAll else 0})
    ranked.sort(key=lambda x:-x['lean_abelardo'])
    return {'partido':PARTIDO,'curules':6,
            'baseline_bogota_abelardo_pct':round(100*lean_bog,1),
            'baseline_bogota_paloma_pct':round(100*(1-lean_bog),1),
            'baseline_abelardo':A_b,'baseline_paloma':P_b,'candidatos':ranked}

def main():
    print("Cargando…",file=sys.stderr)
    pres=load_presidencial(); cons=load_consulta(); censo=load_censo()
    print(f"  pres {len(pres)} · cons {len(cons)} · censo {len(censo)} puestos",file=sys.stderr)
    print("Trasvase (EI acotada SLSQP)…",file=sys.stderr)
    tr=analisis_trasvase(pres,cons,censo)
    print("Traición CD Bogotá…",file=sys.stderr)
    tc=analisis_traicion(pres)
    json.dump({'v':'2026-06-01','trasvase':tr,'traicion':tc},open(OUT,'w'),ensure_ascii=False,indent=1)
    print(f"✓ {OUT}\n",file=sys.stderr)

    print("="*66)
    print("TRASVASE DE PALOMA — Gran Consulta (8-mar) → 1ª vuelta (31-may)")
    print("="*66)
    print(f"Votos de Paloma en la Gran Consulta: {tr['paloma_consulta_total']:,}  ·  {tr['n_puestos']:,} puestos\n")
    print("¿Hacia dónde migraron? (EI acotada por puesto, base censal)")
    for fl in tr['flujos']:
        print(f"  {fl['destino']:<28} {fl['pct']:>5.1f}%  ~{fl['votos_est']:>9,}  {'█'*int(fl['pct']/2)}")
    b=tr['bastiones']
    print(f"\nContexto · {b['n_puestos']} bastiones ({b['nota']}):")
    print(f"  Abelardo {b['abelardo_pct']}% | Paloma {b['paloma_pct']}% | Cepeda {b['cepeda_pct']}%")

    print("\n"+"="*66)
    print("TRAICIÓN — Cámara Bogotá Centro Democrático (lista de Paloma, 6 curules)")
    print("="*66)
    print(f"Bogotá presidencial, duelo Abelardo vs Paloma: Abelardo {tc['baseline_bogota_abelardo_pct']}% | Paloma {tc['baseline_bogota_paloma_pct']}%")
    print(f"  (Abelardo {tc['baseline_abelardo']:,} vs Paloma {tc['baseline_paloma']:,})\n")
    print(f"  {'Representante':<33}{'el':>3}{'votos':>9}  {'→Abel':>6}{'→Palo':>6}  {'base:Ab/Pa/Ce':>16}")
    for c in tc['candidatos']:
        e='★' if c['electo'] else ' '
        print(f"  {c['nombre'][:32]:<33}{e:>3}{c['votos_camara']:>9,}  {c['lean_abelardo']:>5.1f}%{c['lean_paloma']:>5.1f}%  "
              f"{c['base_abelardo_pct']:>4.0f}/{c['base_paloma_pct']:>3.0f}/{c['base_cepeda_pct']:>3.0f}")
    print("\n★ = representante electo (top-6 voto preferente)")

if __name__=='__main__': main()
