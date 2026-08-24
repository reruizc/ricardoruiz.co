#!/usr/bin/env python3
# MASTER UNIFICADO 1V + 2V por puesto — fundación del documento extenso de 2V.
# Une:
#   - master_2026_puesto.json  (1V: 13 cands, censo pot, participacion urna1, barrio/comuna/lat/lon)
#   - XLSX preconteo 2V por mesa -> agregado por puesto (cep2, abe2, urna2)
#   - twov_territorial.json     (techo Petro-2V 2022 + recuperar por puesto)
#   - master_2022_puesto.json   (share Petro-2V por puesto, para abstencion neta)
# Emite:
#   output_2v/master_unificado_puesto.json
#   output_2v/agg_municipio.json   (1V+2V+participacion+targets por municipio)
#   output_2v/agg_ciudad_barrio.json (por ciudad/comuna/barrio, solo ciudades principales)
import json, csv, unicodedata, collections, openpyxl

OUT='Bases de datos/output_2v'; PACTO='Bases de datos/output_pacto_1v_2026'; B='Bases de datos'
norm=lambda s:''.join(c for c in unicodedata.normalize('NFD',str(s or '').upper().strip()) if unicodedata.category(c)!='Mn')
def z(x,n):
    try: return str(int(x)).zfill(n)
    except: return str(x).strip().zfill(n)

# ── 1) mapa (nombre_dep,nombre_mun) -> cod5: GEOREF + divipola, normalizacion fuerte ──
def normm(s):  # norm + quita parentesis/puntos + colapsa espacios (TIQUISIO (PTO. RICO) == TIQUISIO PTO. RICO)
    s=norm(s).replace('(',' ').replace(')',' ').replace('.',' ')
    return ' '.join(s.split())
cod5={}
with open(f'{B}/PUESTOS_GEOREF.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter=';'):
        cc=(r['CÓDIGO COMPLETO'] or '').strip()
        if len(cc)>=5:
            cod5.setdefault((normm(r['DEPARTAMENTO']),normm(r['MUNICIPIO'])), cc[:5])
DV=json.load(open(f'{B}/test-presidencial/divipola.json'))   # fallback: muns que GEOREF nombra distinto
for dep in DV['deptos']:
    for m in dep['muns']:
        cod5.setdefault((normm(dep['nombre']),normm(m['nombre'])), dep['cod']+m['cod'])
def cod5_of(dep,mun):
    nd,nm=normm(dep),normm(mun)
    if nd.startswith('BOGOTA') or nm.startswith('BOGOTA'): return '16001'
    return cod5.get((nd,nm))

# ── 2) XLSX 2V -> agregado por codigo de puesto 9 dig ──
wb=openpyxl.load_workbook(f'{OUT}/detalle_nacional_presidencia_mesas.xlsx', read_only=True, data_only=True)
ws=wb.worksheets[0]
def ni(v):
    try: return int(v)
    except: return 0
v2=collections.defaultdict(lambda:{'cep':0,'abe':0,'blanco':0,'nulos':0,'nomarc':0,'mesas':0})
nomatch=collections.Counter(); n_rows=0
for i,row in enumerate(ws.iter_rows(values_only=True)):
    if i==0: continue
    n_rows+=1
    c5=cod5_of(row[1],row[2])
    if not c5:
        nomatch[(row[1],row[2])]+=1; continue
    code=c5+z(row[3],2)+z(row[4],2)
    a=v2[code]
    a['blanco']+=ni(row[7]); a['nomarc']+=ni(row[8]); a['nulos']+=ni(row[9])
    a['cep']+=ni(row[10]); a['abe']+=ni(row[11]); a['mesas']+=1
for code,a in v2.items():
    a['urna2']=a['cep']+a['abe']+a['blanco']+a['nulos']+a['nomarc']
print(f'XLSX filas: {n_rows:,}  puestos 2V con codigo: {len(v2):,}')
if nomatch:
    tot_nm=sum(nomatch.values())
    print(f'  filas sin cod5 (exterior/especiales): {tot_nm:,} en {len(nomatch)} (dep,mun)  ej:',
          list(nomatch.items())[:3])

# ── 3) master 1V + techo + share Petro-2V ──
M26=json.load(open(f'{PACTO}/master_2026_puesto.json'))
def pc(p):
    try: return f"{int(p['dep']):02d}{int(p['mun']):03d}{int(p['zona']):02d}{int(p['puesto']):02d}"
    except: return None
# recuperar/techo por puesto
TER=json.load(open(f'{PACTO}/twov_territorial.json'))
rec_by={r['pcode']:r for r in TER['puesto']}
# share Petro-2V 2022 por puesto
M22=json.load(open(f'{PACTO}/master_2022_puesto.json'))
share22={}
for p in (M22 if isinstance(M22,list) else M22.values()):
    k=pc(p)
    if k and p.get('base2v'): share22[k]=(p['petro2v']/p['base2v']) if p['base2v'] else None

CITIES={'16001':'Bogotá','01001':'Medellín','31001':'Cali','03001':'Barranquilla','05001':'Cartagena',
        '25001':'Cúcuta','27001':'Bucaramanga','03052':'Soledad','15247':'Soacha','29001':'Ibagué',
        '24001':'Pereira','09001':'Manizales','23001':'Pasto','52001':'Villavicencio','21001':'Santa Marta',
        '13001':'Montería','11001':'Popayán','08001':'Valledupar','41001':'Neiva'}
CAND1V=['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe','macollins','roy','murillo','caicedo','matamoros','claudia']

# ── 4) une y arma master unificado ──
master=[]; sin2v=0
for p in M26:
    code=pc(p)
    a=v2.get(code)
    v1={c:int(p.get(c,0) or 0) for c in CAND1V}   # 13 candidatos 1V
    cep1=v1['cepeda']; abe1=v1['abelardo']; faj=v1['fajardo']; cla=v1['claudia']
    urna1=int(p.get('total_votos_urna',0) or 0); pot=int(p.get('pot',0) or 0)
    blanco1=int(p.get('votos_blanco',0) or 0)
    rec=rec_by.get(code,{})
    sh=share22.get(code)
    rd={
        'pcode':code,'dep':p['dep'],'mun':p['mun'],'cod5':z(p['dep'],2)+z(p['mun'],3),
        'zona':p['zona'],'puesto':p['puesto'],'ciudad':CITIES.get(z(p['dep'],2)+z(p['mun'],3)),
        'comuna':p.get('comuna',''),'barrio':(p.get('barrio') or '').strip(),
        'lat':p.get('lat'),'lon':p.get('lon'),'pot':pot,
        'v1':v1,'cep1':cep1,'abe1':abe1,'faj':faj,'cla':cla,'blanco1':blanco1,'urna1':urna1,
        'techo':rec.get('techo'),'recuperar':rec.get('recuperar'),'share_p2v':sh,
    }
    if a:
        rd.update({'cep2':a['cep'],'abe2':a['abe'],'urna2':a['urna2'],'mesas2':a['mesas']})
    else:
        rd.update({'cep2':None,'abe2':None,'urna2':None,'mesas2':0}); sin2v+=1
    master.append(rd)

# ── validacion ──
c2=sum(r['cep2'] for r in master if r['cep2'] is not None)
a2=sum(r['abe2'] for r in master if r['abe2'] is not None)
c1=sum(r['cep1'] for r in master); a1=sum(r['abe1'] for r in master)
con2=sum(1 for r in master if r['cep2'] is not None)
print(f'\npuestos master: {len(master):,}  con 2V: {con2:,}  sin 2V: {sin2v:,}')
print(f'1V (master): Cepeda {c1:,}  Abelardo {a1:,}')
print(f'2V (unido) : Cepeda {c2:,}  Abelardo {a2:,}   (control feed: 12.708.712 / 12.959.542)')
print(f'  cobertura 2V vs feed: Cep {100*c2/12708712:.2f}%  Abe {100*a2/12959542:.2f}%')

# ── 5) agregado por municipio ──
agg=collections.OrderedDict()
for r in master:
    k=r['cod5']
    m=agg.setdefault(k,{'cod5':k,'dep':r['dep'],'mun':r['mun'],'ciudad':r['ciudad'],
        'pot':0,'cep1':0,'abe1':0,'faj':0,'cla':0,'urna1':0,'cep2':0,'abe2':0,'urna2':0,
        'recuperar':0,'techo':0,'_sh_num':0,'_sh_den':0,'has2v':False})
    for f in ('pot','cep1','abe1','faj','cla','urna1'): m[f]+=r[f]
    if r['cep2'] is not None:
        m['cep2']+=r['cep2']; m['abe2']+=r['abe2']; m['urna2']+=r['urna2']; m['has2v']=True
    if r['recuperar']: m['recuperar']+=r['recuperar']
    if r['techo']: m['techo']+=r['techo']
    if r['share_p2v'] is not None:
        base=r['cep1']+r['abe1']+r['faj']+r['cla']  # proxy de tamaño para ponderar share
        m['_sh_num']+=r['share_p2v']*max(base,1); m['_sh_den']+=max(base,1)
for m in agg.values():
    m['share_p2v']=(m['_sh_num']/m['_sh_den']) if m['_sh_den'] else None
    del m['_sh_num']; del m['_sh_den']
json.dump(list(agg.values()), open(f'{OUT}/agg_municipio.json','w'), ensure_ascii=False)
json.dump(master, open(f'{OUT}/master_unificado_puesto.json','w'), ensure_ascii=False)
print(f'\n-> {OUT}/master_unificado_puesto.json ({len(master):,} puestos)')
print(f'-> {OUT}/agg_municipio.json ({len(agg):,} municipios)')
