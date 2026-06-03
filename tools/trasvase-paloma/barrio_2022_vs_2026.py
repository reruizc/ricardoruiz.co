import csv, json
p2b=json.load(open('Bases de datos/output_ciudades/bogota/bog-puesto-to-barrio.json'))
geo=json.load(open('/tmp/bogbar.json'))
bmeta={f['properties']['codigo']:(f['properties']['nombre'],f['properties'].get('loc_nombre','')) for f in geo['features']}
def pkey(z,p):
    try: return f"{int(z):02d}-{int(p):02d}"
    except: return None
# ---- 2026 por barrio (preconteo) ----
C26=[('Abelardo De La Espriella','ab'),('Iván Cepeda','ce'),('Paloma Valencia','pa'),('Sergio Fajardo','sf'),
('Santiago Botero','bo'),('Mauricio Lizcano','li'),('Miguel Uribe','mu'),('Sondra Macollins','ma'),
('Roy Barreras','ro'),('Gilberto Murillo','gm'),('Carlos Caicedo','ca'),('Gustavo Matamoros','mt')]
a26={}
with open('Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['cod_departamento']!='16': continue
        bc=p2b.get(pkey(r['zona'],r['puesto']))
        if not bc: continue
        d=a26.setdefault(bc,{k:0 for _,k in C26}|{'val':0})
        for col,k in C26: d[k]+=int(r[col]or 0)
        d['val']+=sum(int(r[col]or 0) for col,_ in C26)+int(r['votos_blanco']or 0)
# ---- 2022 por barrio (GCS) ----
a22={}
with open('Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES1V.csv',encoding='utf-8-sig',errors='replace') as f:
    rd=csv.reader(f,delimiter=';'); h=next(rd)
    ix={c.strip():i for i,c in enumerate(h)}
    iD,iZ,iP,iC,iN=ix['COD_DDE'],ix['COD_ZZ'],ix['COD_PP'],ix['DES_CAN'],ix['NUM_VOT']
    for row in rd:
        if len(row)<=iN or row[iD]!='16': continue
        bc=p2b.get(pkey(row[iZ],row[iP]))
        if not bc: continue
        nm=row[iC].upper(); v=int(row[iN] or 0)
        d=a22.setdefault(bc,{'petro':0,'fico':0,'rodolfo':0,'fajardo':0,'otros':0,'val':0})
        if 'PETRO' in nm: d['petro']+=v
        elif 'FEDERICO GUTIERREZ' in nm: d['fico']+=v
        elif 'RODOLFO' in nm: d['rodolfo']+=v
        elif 'FAJARDO' in nm: d['fajardo']+=v
        elif 'VOTO' in nm or 'NULO' in nm or 'NO MARC' in nm: pass
        else: d['otros']+=v
        if not('NULO' in nm or 'NO MARC' in nm): d['val']+=v  # validos = cand + blanco
# join
both=[bc for bc in a26 if bc in a22 and a26[bc]['val']>200 and a22[bc]['val']>200]
v26=sum(a26[bc]['val'] for bc in both); v22=sum(a22[bc]['val'] for bc in both)
print(f"Barrios comparables: {len(both)} | votos 2026 {v26:,} · 2022 {v22:,}")
# nacional-ciudad sobre barrios comparables
P22=sum(a22[bc]['petro'] for bc in both); CE26=sum(a26[bc]['ce'] for bc in both)
print(f"IZQUIERDA: Petro 2022 {100*P22/v22:.1f}% → Cepeda 2026 {100*CE26/v26:.1f}%  (Δ {100*CE26/v26-100*P22/v22:+.1f}pp)")
def top(metric,n=6,minv=400):
    rows=[(metric(bc),bmeta.get(bc,('?',''))[0],bmeta.get(bc,('','?'))[1],bc) for bc in both if a26[bc]['val']>=minv]
    return sorted(rows,reverse=True)[:n]
print("\nTOP Abelardo 2026 (% válidos):")
for s,n,l,bc in top(lambda b:a26[b]['ab']/a26[b]['val']): print(f"  {100*s:5.1f}%  {n} · {l}")
print("TOP Cepeda 2026:")
for s,n,l,bc in top(lambda b:a26[b]['ce']/a26[b]['val']): print(f"  {100*s:5.1f}%  {n} · {l}")
print("TOP Paloma 2026 (3ª en Bogotá):")
for s,n,l,bc in top(lambda b:a26[b]['pa']/a26[b]['val']): print(f"  {100*s:5.1f}%  {n} · {l}")
# swing izquierda Petro->Cepeda
print("\nMAYOR CAÍDA de la izquierda (Petro22 → Cepeda26, pp):")
sw=[(a26[bc]['ce']/a26[bc]['val']-a22[bc]['petro']/a22[bc]['val'],bmeta.get(bc,('?',''))[0],bmeta.get(bc,('','?'))[1],100*a22[bc]['petro']/a22[bc]['val'],100*a26[bc]['ce']/a26[bc]['val']) for bc in both]
for d,n,l,p,c in sorted(sw)[:6]: print(f"  {d*100:+5.1f}pp  {n} · {l}  (Petro {p:.0f}% → Cepeda {c:.0f}%)")
print("MAYOR AGUANTE/SUBIDA de la izquierda:")
for d,n,l,p,c in sorted(sw,reverse=True)[:6]: print(f"  {d*100:+5.1f}pp  {n} · {l}  (Petro {p:.0f}% → Cepeda {c:.0f}%)")
# flips: Petro ganó 2022, Abelardo ganó 2026
flips=[]
for bc in both:
    w22='Petro' if a22[bc]['petro']>=max(a22[bc]['fico'],a22[bc]['rodolfo']) else ('Fico' if a22[bc]['fico']>=a22[bc]['rodolfo'] else 'Rodolfo')
    w26='Abelardo' if a26[bc]['ab']>=a26[bc]['ce'] else 'Cepeda'
    if w22=='Petro' and w26=='Abelardo': flips.append(bmeta.get(bc,('?',''))[0]+' · '+bmeta.get(bc,('','?'))[1])
print(f"\nBarrios que pasaron de PETRO (2022) a ABELARDO (2026): {len(flips)}")
for x in flips[:12]: print("  -",x)
