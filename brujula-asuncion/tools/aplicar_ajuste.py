"""Aplica el ajuste ideológico al banco: reescribe las escalas de los temas 3, 7, 9 y 11
(las dos versiones de lenguaje) y reubica las posiciones de los candidatos.

⚠️ El mapeo de posiciones NO es automático y no puede serlo: la escala nueva no es la vieja
invertida — en varias preguntas es OTRO eje (3.3 pasa de "mantenimiento vs obra nueva" a
"austeridad vs inversión pública"). MAPEO se armó leyendo las 40 preguntas y comparando el
CONTENIDO de la opción que ocupaba cada candidato con las opciones nuevas; la etiqueta
ideológica del documento no interviene, porque la afinidad se calcula sobre contenido.
Donde el contenido viejo no tiene equivalente claro en la escala nueva, la posición queda
en conf 'B' (pendiente): el motor la excluye del cálculo y la declara.

Uso: python3 tools/aplicar_ajuste.py /tmp/ajuste.json banco.js
"""
import json, re, sys

B = 'B'  # pendiente: sin equivalente claro en la escala nueva
# codigo: (camilo, soledad) · int = posición nueva · B = pendiente
MAPEO = {
 # tema 3 · desagües
 '3.1': (3, 3),   '3.2': (4, 5),   '3.3': (1, 2),   '3.4': (3, 5),   '3.5': (B, B),
 '3.6': (4, 5),   '3.7': (4, 4),   '3.8': (4, 5),   '3.9': (4, 5),   '3.10': (3, 5),
 # tema 7 · plazas y áreas verdes
 '7.1': (3, 5),   '7.2': (3, 5),   '7.3': (3, 4),   '7.4': (3, 3),   '7.5': (B, B),
 '7.6': (3, 5),   '7.7': (5, 5),   '7.8': (4, 5),   '7.9': (3, 5),   '7.10': (B, B),
 # tema 9 · desarrollo inmobiliario
 '9.1': (1, 3),   '9.2': (1, 3),   '9.3': (1, 2),   '9.4': (2, 4),   '9.5': (3, 5),
 '9.6': (3, 5),   '9.7': (2, 5),   '9.8': (4, 4),   '9.9': (1, B),   '9.10': (2, 4),
 # tema 11 · empleo
 '11.1': (4, 5),  '11.2': (2, 4),  '11.3': (3, 4),  '11.4': (3, 3),  '11.5': (4, 5),
 '11.6': (2, 2),  '11.7': (B, B),  '11.8': (2, 4),  '11.9': (3, 5),  '11.10': (3, 4),
}
NOTA_B = 'Posición pendiente: la escala de esta pregunta se reformuló sobre otro eje y la posición anterior no tiene equivalente claro. No entra al cálculo de afinidad.'

def main(ajuste_path, banco_path):
    ajuste = json.load(open(ajuste_path, encoding='utf-8'))
    src = open(banco_path, encoding='utf-8').read()
    m = re.match(r'^window\.BRUJULA_BANCO = (.+?);?\s*$', src, re.S)
    banco = json.loads(m.group(1))
    por_cod = {q['codigo']: q for q in banco}

    faltan = set(ajuste) - set(MAPEO)
    assert not faltan, f'sin mapeo: {sorted(faltan)}'
    n_esc = n_pend = n_mov = 0
    for cod, nuevo in ajuste.items():
        q = por_cod[cod]
        q['texto'] = nuevo['pregunta']['informada']
        q['escala'] = nuevo['informada']['escala']
        q['popular'] = {'texto': nuevo['pregunta']['popular'], 'escala': nuevo['popular']['escala']}
        q['ideo'] = nuevo['informada']['etiq']      # D/N/I por opción, para el pentágono
        n_esc += 1
        for cand, destino in zip(('camilo', 'soledad'), MAPEO[cod]):
            p = q['pos'][cand]
            if destino == B:
                p.update(pos=3, conf='B', nota=NOTA_B); n_pend += 1
            else:
                if p['pos'] != destino: n_mov += 1
                p['pos'] = destino
                p.pop('nota', None)
    open(banco_path, 'w', encoding='utf-8').write(
        'window.BRUJULA_BANCO = ' + json.dumps(banco, ensure_ascii=False) + ';\n')
    print(f'escalas reescritas: {n_esc} · posiciones movidas: {n_mov} · pendientes: {n_pend}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
