#!/usr/bin/env python3
# Capa base 2026 1V: normaliza PRECONTEO (mesa) -> agrega a puesto -> une a PUESTOS_GEOREF
# (barrio, comuna, localidad, potencial). Remapea las columnas barajadas a candidato real.
import csv,json,os
BASE='Bases de datos'
PRE=f'{BASE}/nuevos archivos 1v 2026/PRECONTEO_REGIS_1780270247.csv'
GEO=f'{BASE}/PUESTOS_GEOREF.csv'
OUT=f'{BASE}/output_pacto_1v_2026'

# columna PRECONTEO -> candidato canónico (verificado cuadrando totales vs oficial)
COL2CAND={'ivan':'cepeda','abelardo':'abelardo','gustavo':'paloma','paloma':'fajardo',
 'claudia':'botero','raul':'lizcano','oscar':'miguel_uribe','miguel':'macollins',
 'sondra':'roy','sergio':'murillo','roy':'caicedo','carlos':'matamoros','luis':'claudia'}
CANDS=list(dict.fromkeys(COL2CAND.values()))
EXTRA=['votos_blanco','votos_nulos','votos_no_marcados','total_votos_urna']

def pcode(dep,mun,zon,pue):
    return f"{int(dep):02d}{int(mun):03d}{int(zon):02d}{int(pue):02d}"

# 1) georef -> dict por código de puesto
geo={}
with open(GEO,newline='',encoding='utf-8',errors='ignore') as f:
    r=csv.DictReader(f,delimiter=';')
    for row in r:
        cc=(row.get('CÓDIGO COMPLETO') or '').strip()
        if len(cc)<9: continue
        comuna=(row.get('NOMBRE COMUNA') or '').strip()
        geo[cc]={'barrio':(row.get('BARRIO') or '').strip(),
                 'comuna':comuna,'cod_comuna':(row.get('CÓDIGO COMUNA') or '').strip(),
                 'lat':row.get('LATITUD'),'lon':row.get('LONGITUD'),
                 'pot':(int(row.get('MUJERES') or 0)+int(row.get('HOMBRES') or 0))}
print('georef puestos:',len(geo))

# 2) PRECONTEO mesa -> agrega a puesto
pue={}
with open(PRE,newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        try: code=pcode(row['cod_departamento'],row['cod_municipio'],row['zona'],row['puesto'])
        except: continue
        d=pue.setdefault(code,{c:0 for c in CANDS+EXTRA}|{'dep':row['cod_departamento'],'mun':row['cod_municipio'],'zona':row['zona'],'puesto':row['puesto'],'mesas':0})
        d['mesas']+=1
        for col,cand in COL2CAND.items(): d[cand]+=int(row.get(col) or 0)
        for e in EXTRA: d[e]+=int(row.get(e) or 0)
print('puestos 2026:',len(pue))

# 3) join + cobertura
matched=0; vtot=0; vmatch=0
for code,d in pue.items():
    g=geo.get(code)
    vt=sum(d[c] for c in CANDS)+d['votos_blanco']
    vtot+=vt
    if g:
        matched+=1; vmatch+=vt
        d.update({'barrio':g['barrio'],'comuna':g['comuna'],'cod_comuna':g['cod_comuna'],'lat':g['lat'],'lon':g['lon'],'pot':g['pot']})
    else:
        d.update({'barrio':'','comuna':'','cod_comuna':'','lat':'','lon':'','pot':0})
print(f'join: {matched}/{len(pue)} puestos con georef ({matched/len(pue)*100:.1f}%) · votos cubiertos {vmatch/vtot*100:.1f}%')

# 4) verificación totales nacionales
nac={c:sum(d[c] for d in pue.values()) for c in CANDS}
print('\nTotales nacionales (capa base):')
for c,v in sorted(nac.items(),key=lambda x:-x[1]): print(f'  {c:<13}{v:>12,}')

# 5) guarda master puesto-level
os.makedirs(OUT,exist_ok=True)
json.dump(list(pue.values()),open(f'{OUT}/master_2026_puesto.json','w'))
print(f'\n✓ {OUT}/master_2026_puesto.json ({len(pue)} puestos)')
