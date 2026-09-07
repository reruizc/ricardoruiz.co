"""Lista priorizada de candidatas al diccionario, DERIVADA DEL DATO.
Nunca inventa un nombre: cada fila existe en SECOP (proveedor con NIT) o en el
consolidado de actos regulatorios."""
import json, re, sys, unicodedata
from collections import Counter, defaultdict
sys.path.insert(0,'/Users/ricardoruiz/ricardoruiz.co/tools/caudal')
import os
S = os.environ.get("CAUDAL_DICC_DIR", "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/caudal-diccionario")
import empresas as E

def n(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ', re.sub(r'[^a-z0-9 ]',' ',s)).strip()

# --- entidades PÚBLICAS: no son clientes ni sujetos vigilados, son el Estado
PUB = re.compile(r'\b(municipio|alcaldia|gobernacion|ministerio|departamento administrativo'
 r'|instituto nacional|instituto colombiano|universidad|hospital|e s e|ese\b'
 r'|empresa social del estado|fiscalia|policia|ejercito|armada|fuerza aerea|defensa civil'
 r'|contraloria|procuraduria|personeria|registraduria|agencia nacional|unidad administrativa'
 r'|superintendencia|corporacion autonoma|area metropolitana|imprenta nacional|sena\b'
 r'|escuela superior|colegio mayor|fondo de desarrollo local|secretaria de|concejo de'
 r'|asamblea departamental|rama judicial|consejo superior|comision nacional|junta central'
 r'|direccion nacional|servicio geologico|instituto geografico|inpec|icbf|dian\b'
 r'|congregacion|arquidiocesis|diocesis|parroquia|iglesia)\b')
RUIDO = re.compile(r'\b(no existe|sin dato|prueba|desconocido|proveedor|persona natural|no definido|varios|otros|n a)\b')
CONS = re.compile(r'\b(consorcio|union temporal|u t\b|ut\b|promesa de sociedad)\b')

prov = json.load(open(f"{S}/secop_nit.json"))
cats = json.load(open(f"{S}/secop_cat.json"))
dom = {}
for r in cats:
    dom.setdefault(r['documento_proveedor'], r['codigo_de_categoria_principal'])

# actos regulatorios por razón social
actos = Counter(); fuentes = defaultdict(set)
with open('/Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/supers/dist/sanciones.jsonl') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: r=json.loads(line)
        except Exception: continue
        k=n(r.get('sancionado'))
        if len(k)<6: continue
        actos[k]+=1; fuentes[k].add(r.get('fuente_nombre') or r.get('fuente') or '')

cand={}
for p in prov:
    nm=(p.get('proveedor_adjudicado') or '').strip()
    k=n(nm)
    if len(k)<5 or RUIDO.search(k) or PUB.search(k) or CONS.search(k): continue
    cand[k]={'nombre':nm,'clave':k,'nit':p.get('documento_proveedor'),
             'contratos':int(p['n']),'valor':float(p.get('v') or 0),
             'unspsc':dom.get(p.get('documento_proveedor')),'actos':actos.get(k,0),
             'fuentes':sorted(x for x in fuentes.get(k,()) if x)}
for k,v in actos.items():
    if v<2 or k in cand: continue
    if RUIDO.search(k) or PUB.search(k) or CONS.search(k): continue
    cand[k]={'nombre':k,'clave':k,'nit':None,'contratos':0,'valor':0.0,
             'unspsc':None,'actos':v,'fuentes':sorted(x for x in fuentes[k] if x)}

# quitar las que el diccionario ya cubre
nuevas=[c for c in cand.values() if not E.casa_registro_any(E.EMPRESAS, c['clave'])]
nuevas.sort(key=lambda c: (-(c['actos']*40 + c['contratos']), -c['valor']))
print(f'candidatas totales      : {len(cand)}')
print(f'ya cubiertas            : {len(cand)-len(nuevas)}')
print(f'NUEVAS                  : {len(nuevas)}')
print(f'  con actos regulatorios: {sum(1 for c in nuevas if c["actos"])}')
print(f'  con >=100 contratos   : {sum(1 for c in nuevas if c["contratos"]>=100)}')
json.dump(nuevas, open(f"{S}/candidatas.json",'w'), ensure_ascii=False, indent=1)
print()
for c in nuevas[:25]:
    print(f"  {c['actos']:4d}a {c['contratos']:5d}c  {c['nombre'][:58]}")
