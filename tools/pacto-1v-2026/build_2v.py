#!/usr/bin/env python3
# Modelo de aritmética de 2ª vuelta: cuántos votos necesita Cepeda para ganar.
# Supuestos de trasvase EXPLÍCITOS (escenario base + sensibilidad). Salida:
#   twov_model.json  (modelo nacional + composición para el gráfico de trasvase)
#   y arrays territoriales (municipio + puesto) para el Excel de soporte.
import json
OUT='Bases de datos/output_pacto_1v_2026'

# ── Totales 1ª vuelta 2026 (verificados vs Base nombres corregidos) ──
V=dict(cepeda=9680095, abelardo=10346010, paloma=1637665, fajardo=1007627,
       claudia=225287, botero=206024, lizcano=53828, miguel_uribe=28642,
       macollins=19879, roy=14106, murillo=13264, caicedo=12689, matamoros=5625, blanco=406805)
TOTAL=sum(V.values())
rmin=V['botero']+V['lizcano']+V['miguel_uribe']+V['macollins']+V['matamoros']   # minoritarios derecha
lmin=V['roy']+V['murillo']+V['caicedo']                                          # minoritarios izquierda

# ── Supuestos de trasvase 1V → 2V (escenario BASE, declarados) ──
# Defendibles por bloque ideológico y por el comportamiento 2022 (Petro absorbió
# el centro en 2ª vuelta). El cliente puede mover estos números.
T=dict(paloma_abe=0.85,   # Paloma (CD) endosa a Abelardo; resto se abstiene
       rmin_abe=0.78,     # Botero/Lizcano/M.Uribe/Macollins/Matamoros → Abelardo
       lmin_cep=0.85,     # Roy/Murillo/Caicedo → Cepeda
       faj_cep=0.55, faj_abe=0.30,   # Fajardo (centro): 55% Cepeda, 30% Abelardo, 15% abst
       cla_cep=0.65, cla_abe=0.20)   # Claudia: 65% Cepeda, 20% Abelardo, 15% abst

# Piso de Abelardo (la derecha consolidada) y techo de Cepeda con el centro, SIN
# contar todavía la nueva movilización de 2ª vuelta.
abe_floor = (V['abelardo'] + T['paloma_abe']*V['paloma'] + T['rmin_abe']*rmin
             + T['faj_abe']*V['fajardo'] + T['cla_abe']*V['claudia'])
cep_ceiling = (V['cepeda'] + T['lmin_cep']*lmin
               + T['faj_cep']*V['fajardo'] + T['cla_cep']*V['claudia'])
gap = abe_floor - cep_ceiling                 # lo que falta tras tomar el centro
center_contrib = cep_ceiling - V['cepeda']    # aporte del centro+minoritarios izq
need_over_1v = abe_floor - V['cepeda']         # cuánto debe sumar Cepeda a su 1V para EMPATAR el piso

# Movilización: net = N*(2f-1). Para cerrar 'gap' con fracción f de nuevos votos:
def new_needed(f): return gap/(2*f-1) if f>0.5 else None
mob = {f'{int(f*100)}': round(new_needed(f)) for f in (0.65,0.70,0.75,0.80)}

# Composición para el gráfico de trasvase (de dónde sale cada 2V)
abe_comp=[('Base 1V',V['abelardo']),('+ Paloma',round(T['paloma_abe']*V['paloma'])),
          ('+ Otros derecha',round(T['rmin_abe']*rmin)),
          ('+ Centro (Fajardo/Claudia)',round(T['faj_abe']*V['fajardo']+T['cla_abe']*V['claudia']))]
cep_comp=[('Base 1V',V['cepeda']),
          ('+ Centro (Fajardo/Claudia)',round(T['faj_cep']*V['fajardo']+T['cla_cep']*V['claudia'])),
          ('+ Minoritarios izq',round(T['lmin_cep']*lmin))]

model=dict(total_1v=TOTAL, votos=V, rmin=rmin, lmin=lmin, supuestos=T,
           abe_floor=round(abe_floor), cep_ceiling=round(cep_ceiling), gap=round(gap),
           center_contrib=round(center_contrib), need_over_1v=round(need_over_1v),
           mob_new_needed=mob, abe_comp=abe_comp, cep_comp=cep_comp)

# ── Territorial: votos por recuperar (hasta el techo Petro 2V) + centro disponible ──
BF=json.load(open(f'{OUT}/blocks_full.json'))['muni']
def muni_rows():
    out=[]
    for code,v in BF.items():
        if v['dep']=='Exterior': continue
        base=v.get('base') or 0
        if not base or v.get('petro2v') is None or v.get('cep26') is None: continue
        cep_now=round(v['cep26']/100*base)
        techo=round(v['petro2v']/100*base)
        recuperar=max(0,techo-cep_now)
        centro=round((v.get('centro26') or 0)/100*base*T['faj_cep'])  # ~55% del centro local
        objetivo=cep_now+recuperar
        out.append(dict(cod=code,dep=v['dep'],muni=v['muni'],cep_now=cep_now,techo=techo,
                        recuperar=recuperar,centro=centro,base=base,
                        abst=round(100-(v.get('part26') or 0),1)))
    out.sort(key=lambda r:-r['recuperar'])
    return out
MUNI=muni_rows()

def puesto_rows():
    d26=json.load(open(f'{OUT}/master_2026_puesto.json'))
    d22=json.load(open(f'{OUT}/master_2022_puesto.json'))
    CAND=['cepeda','abelardo','paloma','fajardo','claudia','miguel_uribe','roy','lizcano','botero','caicedo','murillo','macollins','matamoros']
    def pc(p):
        try: return f"{int(p['dep']):02d}{int(p['mun']):03d}{int(p['zona']):02d}{int(p['puesto']):02d}"
        except: return None
    p22={}
    for p in (d22 if isinstance(d22,list) else d22.values()):
        k=pc(p)
        if k and p.get('base2v'): p22[k]=(p['petro2v']/p['base2v']*100) if p['base2v'] else None
    out=[]
    for p in d26:
        zona=str(p.get('zona','')).zfill(2); dep=str(p.get('dep','')).zfill(2)
        if zona in ('90','98') or dep=='88': continue   # zona 90 puesto-censo, 98 cárceles, 88 exterior: ruido geográfico
        k=pc(p)
        if not k or k not in p22 or p22[k] is None: continue
        base=sum(int(p.get(c,0) or 0) for c in CAND)+int(p.get('votos_blanco',0) or 0)
        if base<50: continue
        cep_now=int(p.get('cepeda',0) or 0)
        techo=round(p22[k]/100*base)
        rec=max(0,techo-cep_now)
        mk=dep+str(p.get('mun','')).zfill(3); info=BF.get(mk,{})
        out.append(dict(pcode=k,dep=dep,mun=str(p.get('mun','')).zfill(3),
                        dep_nombre=info.get('dep',''),mun_nombre=info.get('muni',''),
                        barrio=p.get('barrio',''),comuna=p.get('comuna',''),
                        cep_now=cep_now,techo=techo,recuperar=rec,base=base))
    out.sort(key=lambda r:-r['recuperar'])
    return out
PUESTO=puesto_rows()

json.dump(model, open(f'{OUT}/twov_model.json','w'), ensure_ascii=False, indent=1)
json.dump({'muni':MUNI,'puesto':PUESTO}, open(f'{OUT}/twov_territorial.json','w'), ensure_ascii=False)

print('=== MODELO 2ª VUELTA (escenario base) ===')
print(f"Piso de Abelardo (derecha consolidada): {model['abe_floor']:,}")
print(f"Techo de Cepeda con el centro:          {model['cep_ceiling']:,}")
print(f"Brecha tras tomar el centro:            {model['gap']:,}")
print(f"Cepeda debe sumar a su 1V (a empatar):  {model['need_over_1v']:,}  (centro {model['center_contrib']:,} + movilización {model['gap']:,})")
print(f"Nuevos votos netos necesarios por fracción a Cepeda: {model['mob_new_needed']}")
print(f"\nMunicipios: {len(MUNI)} · Puestos: {len(PUESTO)} · recuperar nacional (muni): {sum(r['recuperar'] for r in MUNI):,}")
print('Top 5 muni por recuperar:', [(r['muni'],r['recuperar']) for r in MUNI[:5]])
