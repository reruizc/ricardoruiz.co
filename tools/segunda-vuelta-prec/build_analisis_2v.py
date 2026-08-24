#!/usr/bin/env python3
# Capas analiticas del documento 2V (sobre el master unificado):
#   A) Evaluacion de las 3 estrategias de Cepeda (Centro/Recuperacion/Abstencion) vs resultado real
#   B) Participacion 1V->2V: donde crecio, donde cayo, y a quien favorecio (movilizacion por zona)
#   C) Top municipios con comportamiento ATIPICO 1V->2V (residual del modelo de trasvases)
# -> Bases de datos/output_2v/analisis_2v.json
import json, csv, collections, numpy as np
OUT='Bases de datos/output_2v'; B='Bases de datos'
M=json.load(open(f'{OUT}/master_unificado_puesto.json'))
TR=json.load(open(f'{OUT}/trasvases.json'))
DEPN={'01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas','11':'Cauca','12':'Cesar',
'13':'Córdoba','15':'Cundinamarca','16':'Bogotá','17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño',
'24':'Risaralda','25':'N. Santander','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima','31':'Valle',
'40':'Arauca','44':'Caquetá','46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare',
'56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada','88':'Exterior'}
cla_mun=collections.defaultdict(int)
with open(f'{B}/nuevos archivos 1v 2026/Base nombres corregidos primera vuelta 2026.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if 'CLAUDIA' in (r['Candidato'] or '').upper():
            code=str(r['cod_departamento'] or '').zfill(2)+str(r['cod_municipio'] or '').zfill(3); cla_mun[code]+=int(r['Suma de Votos'] or 0)

# agrega por municipio (excluye exterior)
MUN=collections.OrderedDict()
NAME={}
for r in M:
    if r['cod5'][:2]=='88' or r['cep2'] is None: continue
    m=MUN.setdefault(r['cod5'],collections.defaultdict(float))
    for c in ('cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe','macollins','matamoros','roy','murillo','caicedo'):
        m[c]+=r['v1'][c]
    m['cep2']+=r['cep2']; m['abe2']+=r['abe2']; m['urna1']+=r['urna1']; m['urna2']+=r['urna2']; m['pot']+=r['pot']
    if r['techo']: m['techo']+=r['techo']
    if r['recuperar']: m['recuperar']+=r['recuperar']
    if r['share_p2v'] is not None:
        base=r['cep1']+r['abe1']+r['faj']+max(r['v1']['paloma'],0)
        m['_shn']+=r['share_p2v']*max(base,1); m['_shd']+=max(base,1)
    NAME[r['cod5']]=(DEPN.get(r['cod5'][:2],r['cod5'][:2]), r.get('ciudad') or r['cod5'])
for code,m in MUN.items():
    m['claudia']=cla_mun.get(code,0)
    m['share_p2v']=(m['_shn']/m['_shd']) if m['_shd'] else None

def muni_label(code):
    # nombre legible: ciudad si la tenemos, si no el codigo + depto
    dep,city=NAME.get(code,('',code)); return city if isinstance(city,str) and not city.isdigit() else code

# nombres de municipio desde GEOREF para los que no son ciudad
GEON={}
with open(f'{B}/PUESTOS_GEOREF.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f,delimiter=';'):
        cc=(r['CÓDIGO COMPLETO'] or '').strip()
        if len(cc)>=5: GEON.setdefault(cc[:5],(r['MUNICIPIO'] or '').title())
def mname(code): return GEON.get(code, muni_label(code))

# ════════ A) ESTRATEGIAS ════════
# Centro: target 0.55F+0.65C ; Recuperacion: max(0,techo-cep1) ; Abstencion: max(0,abst1*(2sh-1))
res={'estrategias':{},'participacion':{},'extranos':{}}
centro_tot=sum(0.55*m['fajardo']+0.65*m['claudia'] for m in MUN.values())
rec_tot=sum(m['recuperar'] for m in MUN.values())
# abstencion neto (recalculado del master)
abst_rows=[]
for code,m in MUN.items():
    sh=m['share_p2v']
    if sh is None: continue
    ab1=m['pot']-m['urna1']
    if ab1<=0: continue
    neto=max(0, ab1*(2*sh-1))
    abst_rows.append((code,neto,ab1,sh))
abst_tot=sum(r[1] for r in abst_rows)

# ¿cuajo? -> resultado real vs target, por municipio
cep_inc_tot=sum(m['cep2']-m['cepeda'] for m in MUN.values())
# Centro: el trasvase real estima centro->81% Cepeda. Materializado:
centro_real=TR['abs_cep'][1]  # centro a Cepeda (votos)
# Recuperacion: cuanto del techo alcanzo Cepeda en 2V (zonas con recuperar>0)
rec_zonas=[m for m in MUN.values() if m['recuperar']>0]
rec_techo=sum(m['techo'] for m in rec_zonas); rec_cep2=sum(m['cep2'] for m in rec_zonas); rec_cep1=sum(m['cepeda'] for m in rec_zonas)
rec_logrado=rec_cep2-rec_cep1   # cuanto crecio Cepeda en las zonas de recuperacion
rec_pct=100*min(1,rec_logrado/rec_tot) if rec_tot else 0
# Abstencion: participacion y rendimiento en los municipios objetivo (los que suman 1.9M)
abst_rows.sort(key=lambda r:-r[1]); ABST_TARGET=1_915_513
acc=0; target_codes=set()
for code,neto,ab1,sh in abst_rows:
    acc+=neto; target_codes.add(code)
    if acc>=ABST_TARGET: break
# en municipios objetivo: ¿subio la participacion? ¿rindio?
tg=[MUN[c] for c in target_codes]
tg_dpart=sum(m['urna2']-m['urna1'] for m in tg); tg_dcep=sum(m['cep2']-m['cepeda'] for m in tg); tg_dabe=sum(m['abe2']-m['abelardo'] for m in tg)
tg_part1=sum(m['urna1'] for m in tg)/sum(m['pot'] for m in tg); tg_part2=sum(m['urna2'] for m in tg)/sum(m['pot'] for m in tg)
rest=[MUN[c] for c in MUN if c not in target_codes]
rest_part1=sum(m['urna1'] for m in rest)/sum(m['pot'] for m in rest); rest_part2=sum(m['urna2'] for m in rest)/sum(m['pot'] for m in rest)
res['estrategias']={
 'centro':{'target':round(centro_tot),'real_a_cepeda':round(centro_real),'tasa_real':TR['a_cep'][1],'veredicto':'cuajó' if centro_real>=centro_tot*0.8 else 'parcial'},
 'recuperacion':{'target':round(rec_tot),'logrado':round(rec_logrado),'pct':round(rec_pct),'techo_zonas':round(rec_techo),'cep1_zonas':round(rec_cep1),'cep2_zonas':round(rec_cep2)},
 'abstencion':{'target':ABST_TARGET,'n_muni':len(target_codes),'dpart_target':round(tg_dpart),'dcep_target':round(tg_dcep),'dabe_target':round(tg_dabe),
   'part1_target':round(100*tg_part1,1),'part2_target':round(100*tg_part2,1),'part1_resto':round(100*rest_part1,1),'part2_resto':round(100*rest_part2,1),'neto_disp':round(abst_tot)},
}
print('A) ESTRATEGIAS')
print(f'  CENTRO (persuasión): target {centro_tot:,.0f} -> real a Cepeda {centro_real:,.0f}  ({100*centro_real/centro_tot:.0f}% del target) · tasa real {100*TR["a_cep"][1]:.0f}%')
print(f'  RECUPERACIÓN (zonas duras): target techo {rec_tot:,.0f} -> Cepeda creció {rec_logrado:,.0f} en esas zonas ({rec_pct:.0f}% del techo)')
print(f'  ABSTENCIÓN (GOTV): {len(target_codes)} munis objetivo · participación {100*tg_part1:.1f}%->{100*tg_part2:.1f}% (resto {100*rest_part1:.1f}%->{100*rest_part2:.1f}%)')
print(f'     en objetivo: +{tg_dpart:,.0f} votantes -> Cepeda +{tg_dcep:,.0f} / Abelardo +{tg_dabe:,.0f}  (neto Cep {tg_dcep-tg_dabe:+,.0f})')

# ════════ B) PARTICIPACION ════════
part=[]
for code,m in MUN.items():
    if m['pot']<=0: continue
    p1=m['urna1']/m['pot']; p2=m['urna2']/m['pot']
    part.append({'code':code,'dep':NAME[code][0],'mun':mname(code),'pot':m['pot'],'p1':p1,'p2':p2,'dpp':100*(p2-p1),
                 'dvot':m['urna2']-m['urna1'],'dcep':m['cep2']-m['cepeda'],'dabe':m['abe2']-m['abelardo']})
tot_pot=sum(m['pot'] for m in MUN.values()); tot_u1=sum(m['urna1'] for m in MUN.values()); tot_u2=sum(m['urna2'] for m in MUN.values())
# zona izq vs der (1V head-to-head)
zizq=[m for c,m in MUN.items() if m['cepeda']>=m['abelardo']]; zder=[m for c,m in MUN.items() if m['abelardo']>m['cepeda']]
def zagg(z):
    dv=sum(m['urna2']-m['urna1'] for m in z); dc=sum(m['cep2']-m['cepeda'] for m in z); da=sum(m['abe2']-m['abelardo'] for m in z)
    return dict(n=len(z),dvot=round(dv),dcep=round(dc),dabe=round(da))
res['participacion']={'nac_part1':round(100*tot_u1/tot_pot,1),'nac_part2':round(100*tot_u2/tot_pot,1),'dvot_nac':round(tot_u2-tot_u1),
  'subieron':sum(1 for p in part if p['dpp']>0),'cayeron':sum(1 for p in part if p['dpp']<0),
  'top_sube':sorted(part,key=lambda p:-p['dpp'])[:8],'top_cae':sorted(part,key=lambda p:p['dpp'])[:8],
  'zona_izq':zagg(zizq),'zona_der':zagg(zder)}
print('\nB) PARTICIPACIÓN')
print(f'  nacional {100*tot_u1/tot_pot:.1f}% -> {100*tot_u2/tot_pot:.1f}%  (+{tot_u2-tot_u1:,.0f} votantes)')
print(f'  municipios donde SUBIÓ: {res["participacion"]["subieron"]}  · donde CAYÓ: {res["participacion"]["cayeron"]}')
zi,zd=zagg(zizq),zagg(zder)
print(f'  zonas izq (Cep ganó 1V, n={zi["n"]}): +{zi["dvot"]:,} votantes -> Cep +{zi["dcep"]:,} / Abe +{zi["dabe"]:,}')
print(f'  zonas der (Abe ganó 1V, n={zd["n"]}): +{zd["dvot"]:,} votantes -> Cep +{zd["dcep"]:,} / Abe +{zd["dabe"]:,}')
print(f'  top caída participación:', [(p['mun'],round(p['dpp'],1)) for p in res['participacion']['top_cae'][:5]])

# ════════ C) MUNICIPIOS EXTRAÑOS (residual del modelo de trasvases) ════════
a=TR['a_cep']; b=TR['b_abe']
def predict(m):
    der=m['paloma']+m['miguel_uribe']+m['botero']+m['lizcano']+m['macollins']+m['matamoros']
    cen=m['fajardo']+m['claudia']; izq=m['roy']+m['murillo']+m['caicedo']; nv=m['urna2']-m['urna1']
    src=[der,cen,izq,nv]
    return sum(a[j]*src[j] for j in range(4)), sum(b[j]*src[j] for j in range(4))
ex=[]
for code,m in MUN.items():
    if m['pot']<5000: continue   # municipios con masa para que el atipico sea senal, no ruido
    pc,pa=predict(m); rc=(m['cep2']-m['cepeda'])-pc; ra=(m['abe2']-m['abelardo'])-pa
    base=m['cep2']+m['abe2']
    # rareza: residual combinado normalizado por tamaño
    rare=(abs(rc)+abs(ra))/max(base,1)
    ex.append({'code':code,'dep':NAME[code][0],'mun':mname(code),'base':round(base),'pot':round(m['pot']),
       'resid_cep':round(rc),'resid_abe':round(ra),'rare':rare,
       'cep1':round(m['cepeda']),'cep2':round(m['cep2']),'abe1':round(m['abelardo']),'abe2':round(m['abe2']),
       'p1':round(100*m['urna1']/m['pot'],1),'p2':round(100*m['urna2']/m['pot'],1),
       'cep_cayo':m['cep2']<m['cepeda'],'abe_cayo':m['abe2']<m['abelardo']})
ex.sort(key=lambda r:-r['rare'])
res['extranos']={'top':ex[:40],
  'pro_abe':sorted([r for r in ex if r['base']>=4000 and r['resid_abe']>0],key=lambda r:-(r['resid_abe']/r['base']))[:6],
  'pro_cep':sorted([r for r in ex if r['base']>=4000 and r['resid_cep']>0],key=lambda r:-(r['resid_cep']/r['base']))[:6]}
print('\nC) MUNICIPIOS ATÍPICOS (mayor residual vs patrón nacional de trasvase):')
for r in ex[:8]:
    flag=' [Cepeda CAYÓ]' if r['cep_cayo'] else (' [Abelardo CAYÓ]' if r['abe_cayo'] else '')
    print(f'  {r["mun"][:22]:22s} {r["dep"][:12]:12s} resCep {r["resid_cep"]:+7,} resAbe {r["resid_abe"]:+7,} '
          f'part {r["p1"]}->{r["p2"]}{flag}')

json.dump(res, open(f'{OUT}/analisis_2v.json','w'), ensure_ascii=False, indent=1)
print(f'\n-> {OUT}/analisis_2v.json')
