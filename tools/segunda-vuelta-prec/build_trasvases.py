#!/usr/bin/env python3
# TRASVASES REALES 1V -> 2V por inferencia ecologica (1.189 municipios).
# La EI no separa fuentes colineales (Paloma vs derecha menor votan los mismos
# territorios) -> se estima por BLOQUE, donde la identificacion es estable, y se
# atribuye la tasa del bloque a cada candidato (con salvedad). Bloques:
#   DERECHA (Paloma + minoritarios derecha) · CENTRO (Fajardo + Claudia) ·
#   IZQ MENOR (Roy+Caicedo+Murillo) · NUEVOS VOTANTES (cambio de participacion).
# Solver lsq_linear (bvls, bounds [0,1]) por destino + restriccion conjunta a+b<=1
# por proyeccion. Bootstrap municipios B=400 -> IC95. Compara vs supuestos del modelo.
import json, csv, collections, numpy as np
from scipy.optimize import lsq_linear

OUT='Bases de datos/output_2v'; B='Bases de datos'
M=json.load(open(f'{OUT}/master_unificado_puesto.json'))
cla_mun=collections.defaultdict(int)
with open(f'{B}/nuevos archivos 1v 2026/Base nombres corregidos primera vuelta 2026.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if 'CLAUDIA' in (r['Candidato'] or '').upper():
            code=str(r['cod_departamento'] or '').zfill(2)+str(r['cod_municipio'] or '').zfill(3)
            cla_mun[code]+=int(r['Suma de Votos'] or 0)

MUN=collections.OrderedDict()
for r in M:
    if r['cod5'][:2]=='88' or r['cep2'] is None: continue
    m=MUN.setdefault(r['cod5'],collections.defaultdict(float)); v1=r['v1']
    for c in ('cepeda','abelardo','paloma','fajardo','botero','lizcano',
              'miguel_uribe','macollins','matamoros','roy','murillo','caicedo'):
        m[c]+=v1[c]
    m['cep2']+=r['cep2']; m['abe2']+=r['abe2']; m['urna1']+=r['urna1']; m['urna2']+=r['urna2']
for code,m in MUN.items(): m['claudia']=cla_mun.get(code,0)

# bloques + composicion (que candidato pesa dentro de cada bloque). Nuevos votantes
# en una sola columna -> "nuevos" total no es colineal con "derecha" (los nuevos estan
# en todo el pais), asi el modelo identifica bien las tasas. La heterogeneidad regional
# de la movilizacion (en bastiones de Abelardo los nuevos fueron a el) se documenta
# aparte, descriptivamente, en el modulo de participacion.
BLOCKS=['Derecha (Paloma+)','Centro (Fajardo+Claudia)','Izquierda menor','Nuevos votantes']
def blockvec(m):
    der=m['paloma']+m['miguel_uribe']+m['botero']+m['lizcano']+m['macollins']+m['matamoros']
    cen=m['fajardo']+m['claudia']; izq=m['roy']+m['murillo']+m['caicedo']
    return [der,cen,izq,m['urna2']-m['urna1']]
rows=[blockvec(m) for m in MUN.values()]
ycep=np.array([m['cep2']-m['cepeda'] for m in MUN.values()],float)
yabe=np.array([m['abe2']-m['abelardo'] for m in MUN.values()],float)
A=np.array(rows,float); J=len(BLOCKS); SC=1e4

# composicion de los bloques (para atribuir a candidatos)
TOT=collections.defaultdict(float)
for m in MUN.values():
    for c in ('paloma','miguel_uribe','botero','lizcano','macollins','matamoros','fajardo','claudia','roy','murillo','caicedo'):
        TOT[c]+=m[c]
der_tot=sum(TOT[c] for c in ('paloma','miguel_uribe','botero','lizcano','macollins','matamoros'))
cen_tot=TOT['fajardo']+TOT['claudia']

def solve(Am,yc,ya):
    a=lsq_linear(Am,yc/SC,bounds=(0,1),method='bvls').x
    b=lsq_linear(Am,ya/SC,bounds=(0,1),method='bvls').x
    over=a+b-1; over=np.clip(over,0,None)        # proyecta a+b<=1 conservando proporcion
    a=a-over*a/np.clip(a+b,1e-9,None); b=b-over*b/np.clip(a+b,1e-9,None)
    return a,b
a_hat,b_hat=solve(A/SC,ycep,yabe)
rng=np.random.default_rng(20260622); n=len(A); BA=[];BB=[]
for _ in range(400):
    idx=rng.integers(0,n,n); a,b=solve(A[idx]/SC,ycep[idx],yabe[idx]); BA.append(a);BB.append(b)
BA=np.array(BA);BB=np.array(BB)
ci=lambda arr,j:(float(np.percentile(arr[:,j],2.5)),float(np.percentile(arr[:,j],97.5)))
src_tot=A.sum(axis=0); pred_cep=float((A@a_hat).sum()); pred_abe=float((A@b_hat).sum())
real_cep=float(ycep.sum()); real_abe=float(yabe.sum())
ss_res=float(np.sum((ycep-A@a_hat)**2)+np.sum((yabe-A@b_hat)**2))
ss_tot=float(np.sum((ycep-ycep.mean())**2)+np.sum((yabe-yabe.mean())**2))

print('='*92)
print('TRASVASES REALES 1V -> 2V por BLOQUE (inferencia ecologica, 1.189 municipios, IC95)')
print('='*92)
print(f'{"Bloque":26s}{"total":>11s} | {"a Cepeda":>18s} | {"a Abelardo":>18s} | {"resto":>6s}')
for j,s in enumerate(BLOCKS):
    lc,hc=ci(BA,j); la,ha=ci(BB,j); resto=max(0,1-a_hat[j]-b_hat[j])
    print(f'{s:26s}{src_tot[j]:>11,.0f} | {100*a_hat[j]:>5.1f}% [{100*lc:>3.0f}-{100*hc:>3.0f}] | '
          f'{100*b_hat[j]:>5.1f}% [{100*la:>3.0f}-{100*ha:>3.0f}] | {100*resto:>4.0f}%')
print(f'\nComposicion bloques: Derecha = Paloma {100*TOT["paloma"]/der_tot:.0f}% (resto minoritarios). '
      f'Centro = Fajardo {100*TOT["fajardo"]/cen_tot:.0f}% / Claudia {100*TOT["claudia"]/cen_tot:.0f}%.')
print(f'\nIncremento Cepeda  : real {real_cep:>11,.0f}  pred {pred_cep:>11,.0f} ({100*pred_cep/real_cep:.0f}%)')
print(f'Incremento Abelardo: real {real_abe:>11,.0f}  pred {pred_abe:>11,.0f} ({100*pred_abe/real_abe:.0f}%)')
print(f'R2 conjunto: {1-ss_res/ss_tot:.3f}')
print('\nVOTOS por destino:')
for j,s in enumerate(BLOCKS):
    print(f'  {s:26s} Cepeda {a_hat[j]*src_tot[j]:>10,.0f}  Abelardo {b_hat[j]*src_tot[j]:>10,.0f}')

out={'blocks':BLOCKS,'a_cep':a_hat.tolist(),'b_abe':b_hat.tolist(),
     'ci_cep':[ci(BA,j) for j in range(J)],'ci_abe':[ci(BB,j) for j in range(J)],
     'src_total':src_tot.tolist(),'abs_cep':[float(a_hat[j]*src_tot[j]) for j in range(J)],
     'abs_abe':[float(b_hat[j]*src_tot[j]) for j in range(J)],
     'comp':{'paloma_in_der':TOT['paloma']/der_tot,'fajardo_in_cen':TOT['fajardo']/cen_tot,
             'claudia_in_cen':TOT['claudia']/cen_tot,'der_tot':der_tot,'cen_tot':cen_tot,
             'paloma_tot':TOT['paloma'],'fajardo_tot':TOT['fajardo'],'claudia_tot':TOT['claudia']},
     'real_inc_cep':real_cep,'real_inc_abe':real_abe,'pred_inc_cep':pred_cep,'pred_inc_abe':pred_abe,
     'r2':1-ss_res/ss_tot,
     'sup':{'paloma_abe':0.85,'fajardo_cep':0.55,'claudia_cep':0.65,'der_menor_abe':0.78,'izq_menor_cep':0.85}}
json.dump(out,open(f'{OUT}/trasvases.json','w'),ensure_ascii=False,indent=1)
print(f'\n-> {OUT}/trasvases.json')
