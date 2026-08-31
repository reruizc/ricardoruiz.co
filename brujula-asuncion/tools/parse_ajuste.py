"""Parsea 'AJUSTE BRUJULA ASUNCIÓN.docx' → JSON con las escalas reformuladas.

El documento reformula las 5 respuestas de los temas 3, 7, 9 y 11 con una escala
ideológica uniforme (1 derecha marcada … 5 izquierda marcada), en las dos versiones
de lenguaje. Las PREGUNTAS no cambian; solo las respuestas.
"""
import json, re, sys, zipfile

VERSIONES = {'VERSIÓN 1': 'informada', 'VERSIÓN 2': 'popular'}
ETIQ = {'DERECHA': 'D', 'NEUTRAL': 'N', 'IZQUIERDA': 'I'}

def texto(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    xml = re.sub(r'</w:p>', '\n', xml)
    plano = re.sub(r'<[^>]+>', '', xml)
    for a, b in (('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),('&#39;',"'")):
        plano = plano.replace(a, b)
    return [l.strip() for l in plano.split('\n')]

def parse(path):
    out, version, cod = {}, None, None
    for linea in texto(path):
        for k, v in VERSIONES.items():
            if linea.startswith(k):
                version = v
        m = re.match(r'^(\d+\.\d+)\.\s+(.+)$', linea)
        if m and version:
            cod, preg = m.group(1), m.group(2)
            out.setdefault(cod, {'codigo': cod, 'pregunta': {}})['pregunta'][version] = preg
            out[cod].setdefault(version, {'escala': [], 'etiq': []})
            continue
        m = re.match(r'^([1-5])\.\s+\[(DERECHA|NEUTRAL|IZQUIERDA)\]\s+(.+)$', linea)
        if m and cod and version:
            n, et, txt = int(m.group(1)), m.group(2), m.group(3)
            d = out[cod][version]
            assert len(d['escala']) == n - 1, f'{cod}/{version}: opción {n} fuera de orden'
            d['escala'].append(txt); d['etiq'].append(ETIQ[et])
    return out

if __name__ == '__main__':
    datos = parse(sys.argv[1])
    esperado = ['D','D','N','I','I']
    problemas = []
    for cod, q in sorted(datos.items()):
        for v in ('informada','popular'):
            d = q.get(v)
            if not d or len(d['escala']) != 5:
                problemas.append(f'{cod}/{v}: {len(d["escala"]) if d else 0} opciones'); continue
            if d['etiq'] != esperado:
                problemas.append(f'{cod}/{v}: etiquetas {"".join(d["etiq"])}')
    print(f'preguntas parseadas: {len(datos)}')
    temas = {}
    for c in datos: temas[c.split('.')[0]] = temas.get(c.split('.')[0], 0) + 1
    print('por tema:', dict(sorted(temas.items(), key=lambda x: int(x[0]))))
    print('problemas de consistencia:', problemas or 'ninguno')
    json.dump(datos, open(sys.argv[2],'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print('→', sys.argv[2])
