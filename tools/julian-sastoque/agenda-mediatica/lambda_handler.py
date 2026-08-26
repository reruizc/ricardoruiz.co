#!/usr/bin/env python3
"""Monitor horario Bogotá → S3 + guía de vocería DeepSeek para Julián.

Trigger: EventBridge cada hora. Publica un único JSON que consume el frontend:
  s3://elecciones-2026/ricardoruiz.co/julian-rodriguez-sastoque/agenda/monitor.json

No expone la llave de DeepSeek: la llave es un secret de la Lambda. Google News
es solo el índice de titulares; cada tarjeta conserva el enlace al medio original.
"""
import html, json, os, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BUCKET=os.getenv('AGENDA_S3_BUCKET','elecciones-2026')
KEY=os.getenv('AGENDA_S3_KEY','ricardoruiz.co/julian-rodriguez-sastoque/agenda/monitor.json')
API_KEY=os.getenv('DEEPSEEK_API_KEY','')
MODEL=os.getenv('DEEPSEEK_MODEL','deepseek-chat')
TIMEOUT=45
# Consultas deliberadamente separadas: agenda de ciudad + mención directa.
QUERIES=[
 ('bogota','Bogotá when:1d'),
 ('julian','"Julián Rodríguez Sastoque" when:7d'),
]

SYSTEM='''Eres asesor de comunicaciones de un concejal de Bogotá. Analiza titulares públicos recientes.
Devuelve JSON estricto: {"prioridad":"máximo 10 palabras","lectura":"máximo 70 palabras", "postura":"máximo 30 palabras", "mensaje_sugerido":"máximo 45 palabras", "acciones":["una acción concreta"], "evitar":["un riesgo concreto"]}.
No inventes hechos, cifras, posiciones de Julián ni apoyos. Distingue un hecho reportado de una alegación. Tono: útil, sobrio, territorial y no partidista. Si el paquete no da evidencia suficiente para intervenir, dilo explícitamente en postura y recomienda escuchar/verificar.'''

def clean(s): return re.sub(r'\s+',' ',re.sub('<[^>]+>','',html.unescape(s or ''))).strip()
def fetch_rss(query):
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'es-419','gl':'CO','ceid':'CO:es-419'})
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
 root=ET.fromstring(urllib.request.urlopen(req,timeout=TIMEOUT).read())
 out=[]
 for item in root.findall('.//item')[:12]:
  title=clean(item.findtext('title'))
  # Google News añade " - Medio"; source es más fiable cuando viene incluido.
  source=item.find('source'); medio=clean(source.text if source is not None else title.rsplit(' - ',1)[-1])
  if ' - ' in title: title=title.rsplit(' - ',1)[0]
  out.append({'titulo':title,'url':clean(item.findtext('link')),'medio':medio,
              'fecha_pub':clean(item.findtext('pubDate')),'tema':'Agenda distrital'})
 return out
def dedupe(items):
 seen=set(); out=[]
 for x in items:
  k=re.sub(r'[^a-z0-9]','',x['titulo'].lower())[:120]
  if k and k not in seen: seen.add(k); out.append(x)
 return out
def call_ai(top,items):
 if not API_KEY: return {'prioridad':'Pendiente de análisis IA','lectura':'La captura está disponible, pero DeepSeek aún no está configurado.','postura':'Verificar la noticia antes de intervenir.','acciones':['Revisar la fuente original y definir vocería.'],'evitar':['No publicar una postura automática sin revisión humana.']}
 paquete='\n'.join(f"{i+1}. {x['titulo']} ({x['medio']})" for i,x in enumerate(items[:12]))
 prompt=f"NOTICIA DOMINANTE: {top['titulo']} ({top['medio']})\n\nTITULARES DE CONTEXTO:\n{paquete}"
 body=json.dumps({'model':MODEL,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}], 'temperature':.2,'response_format':{'type':'json_object'},'max_tokens':600}).encode()
 req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=body,headers={'Authorization':'Bearer '+API_KEY,'Content-Type':'application/json'})
 response=json.loads(urllib.request.urlopen(req,timeout=TIMEOUT).read())
 return json.loads(response['choices'][0]['message']['content'])
def handler(event,context):
 # La Function URL sirve la última captura sin volver a llamar a DeepSeek.
 if (event or {}).get('requestContext',{}).get('http',{}).get('method')=='GET':
  import boto3
  obj=boto3.client('s3').get_object(Bucket=BUCKET,Key=KEY)
  return {'statusCode':200,'headers':{'content-type':'application/json; charset=utf-8','cache-control':'public, max-age=300'},'body':obj['Body'].read().decode()}
 items=[]
 for _,query in QUERIES:
  try: items.extend(fetch_rss(query))
  except Exception as exc: print('feed failed',query,type(exc).__name__,exc)
 items=dedupe(items)
 if not items: raise RuntimeError('No se obtuvieron titulares')
 # Prioriza menciones directas; si no las hay, el primer resultado de agenda Bogotá.
 direct=[x for x in items if 'rodríguez sastoque' in x['titulo'].lower() or 'rodriguez sastoque' in x['titulo'].lower()]
 top=(direct or items)[0]
 payload={'generado_en':datetime.now(timezone.utc).isoformat(),'ventana':'24 h (agenda) · 7 d (mención directa)',
          'n_titulares':len(items),'noticia_dominante':top,'titulares':items,'recomendacion':call_ai(top,items),'modelo':MODEL}
 import boto3
 boto3.client('s3').put_object(Bucket=BUCKET,Key=KEY,Body=json.dumps(payload,ensure_ascii=False).encode(),ContentType='application/json',CacheControl='public, max-age=300')
 return {'ok':True,'key':KEY,'n_titulares':len(items)}
if __name__=='__main__': print(handler({},None))
