#!/usr/bin/env python3
"""
clonar_tableros.py — genera los tableros territoriales de un año viejo a partir
de los de 2023 (tal como están en el último commit), que son la fuente de la lógica:

    resultados-{jal,concejo,asamblea}-2023.html → resultados-{…}-{AÑO}.html
    alcaldias-2023.html                         → alcaldias-{AÑO}.html

    python3 tools/analisis-candidato/clonar_tableros.py 2019

Solo cambia lo que depende del año: el bloque CORP (s3dir · localDir ·
dataFile), título, telón, fecha, pie y los enlaces cruzados. La lógica NO se
toca aquí: si hace falta corregirla, se corrige en las 2023 y se vuelve a clonar
(o se corrige en las seis copias del chasis). La regla de gate de oct-2026 se
aplica con gate_tableros.py si la página de origen todavía no la tiene.

El pie de JAL y Concejo dice, ciudad por ciudad, qué parte del voto quedó fuera
del mapa por comuna. Esas cifras salen del JSON del año (`fuera_mapa`), así que
hay que correr los builders ANTES de clonar.
"""
import glob, json, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(RAIZ, 'Bases de datos')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_tableros import aplicar as aplicar_gate                       # noqa: E402

FECHA = {2019: ('27 oct 2019', '27 Oct 2019'), 2015: ('25 oct 2015', '25 Oct 2015'),
         2011: ('30 oct 2011', '30 Oct 2011')}
NOMBRE = {'jal': 'JAL', 'concejo': 'Concejo', 'asamblea': 'Asamblea'}


# ⚠️ resultados-asamblea-2023.html ganó en oct-2026 el hemiciclo de curules, que trae
# datos FIJOS de 2023 (Decreto 1312 de 2023, contraste con la composición publicada).
# Clonarlo daría curules de otro año, así que Asamblea se clona del chasis anterior al
# hemiciclo hasta que existan las curules del año. Quitar esta línea cuando se porte.
REF = {'resultados-asamblea-2023.html': '69adf2c4^'}


def fuente(nombre):
    """La página 2023 tal como está en el ÚLTIMO COMMIT (o en REF), no en el disco:
    otras sesiones editan esos archivos y un clon no debe arrastrar trabajo a medias."""
    ref = REF.get(nombre, 'HEAD')
    return subprocess.check_output(['git', 'show', f'{ref}:{nombre}'], cwd=RAIZ).decode('utf-8')


def rep(s, a, b, n=1):
    c = s.count(a)
    if c != n:
        raise SystemExit(f'esperaba {n} y hay {c}: {a[:90]!r}')
    return s.replace(a, b)


def fmt(n):
    return f'{n:,}'.replace(',', '.')


def pct(x):
    return f'{x:.1f}'.replace('.', ',')


def aviso_comunas(corp, año):
    with open(os.path.join(BD, f'output_{corp}_{año}', f'resultados-{corp}-{año}.json'), encoding='utf-8') as f:
        d = json.load(f)
    filas = []
    for c in d['cities']:
        fz = c['fuera_mapa']
        p = 100 * fz['votos_sin_ubicar'] / fz['votos_total_csv'] if fz['votos_total_csv'] else 0
        filas.append((p, c['name'].title().replace('D.C.', 'D.C.'), fz['votos_sin_ubicar']))
    filas.sort(reverse=True)
    altas = [f'{n} {pct(p)} % ({fmt(v)} votos)' for p, n, v in filas if p >= 1]
    resto = 'en las demás ciudades, menos del 1 %' if altas else 'en todas las ciudades, menos del 1 %'
    return (f'<b>Ubicación de los puestos de {año}:</b> el código de puesto no es estable entre '
            f'elecciones (en Villavicencio, dos de cada tres códigos de {año} hoy nombran otro lugar), '
            f'así que cada puesto se ubicó por su nombre de {año} contra el georef 2026 y el Divipol 2021. '
            f'Los que no tienen par quedan fuera del mapa por comuna: '
            + ('; '.join(altas) + '; ' if altas else '') + resto + '. ')


def aviso_asamblea(año):
    n = v = 0
    for ruta in glob.glob(os.path.join(BD, f'output_asamblea_{año}', 'mun', '*.json')):
        with open(ruta, encoding='utf-8') as f:
            for p in json.load(f)['puestos']:
                if p.get('barrio'):
                    n += 1; v += p['validos'] + p['blanco'] + p['nulos']
    txt = (f'Los puestos se nombran con el censo electoral de {año}, no con el de hoy: el código '
           f'de puesto no es estable entre elecciones y el nombre actual puede ser otro lugar. ')
    if n:
        txt += f'{fmt(n)} puestos ({fmt(v)} votos) no figuran en ese censo y aparecen marcados. '
    return txt


def clonar_resultados(corp, año):
    s = fuente(f'resultados-{corp}-2023.html')
    s = aplicar_gate(s)
    X = NOMBRE[corp]
    s = rep(s, f'<title>Resultados {X} 2023 · Ricardo Ruiz</title>', f'<title>Resultados {X} {año} · Ricardo Ruiz</title>')
    s = rep(s, '<span class="curtain-word from-right blue">2023</span>', f'<span class="curtain-word from-right blue">{año}</span>')
    s = rep(s, 'Elecciones Territoriales · 29 oct 2023', f'Elecciones Territoriales · {FECHA[año][0]}')
    s = rep(s, f"s3dir:'{corp}-2023', localDir:'output_{corp}_2023',\n      dataFile:'resultados-{corp}-2023.json',",
               f"s3dir:'{corp}-{año}', localDir:'output_{corp}_{año}',\n      dataFile:'resultados-{corp}-{año}.json',")
    # Pie: año de la fuente y del censo + aviso de ubicación + enlaces del año.
    s = rep(s, 'Fuente: Registraduría Nacional (GCS 2023).', f'Fuente: Registraduría Nacional (GCS {año}).')
    s = rep(s, 'no el censo exacto de 2023.', f'no el de {año}.')
    aviso = aviso_asamblea(año) if corp == 'asamblea' else aviso_comunas(corp, año)
    marca = 'Comunas rurales/corregimientos sin polígono' if corp != 'asamblea' else 'Los municipios sin polígono'
    s = rep(s, marca, aviso + marca)
    s = rep(s, '<a href="electoral.html">Resultados 2023</a>', f'<a href="electoral.html">Resultados {año}</a>')
    if corp == 'concejo':
        s = rep(s, '<a href="concejo-2023.html">Escrutinio y curules</a>', '<a href="analisis-candidato.html">Análisis por candidato</a>')
        s = rep(s, '<a href="resultados-jal-2023.html">Resultados JAL</a>', f'<a href="resultados-jal-{año}.html">Resultados JAL</a>')
    if corp == 'asamblea':
        s = rep(s, '<a href="resultados-concejo-2023.html">Resultados Concejo</a>', f'<a href="resultados-concejo-{año}.html">Resultados Concejo</a>')
    if '2023' in re.sub(r'<!--.*?-->|\{2019,2023\}', '', s):
        resto = sorted(set(re.findall(r'.{30}2023.{20}', s)))
        raise SystemExit(f'{corp}: quedó «2023» en la página:\n  ' + '\n  '.join(resto))
    out = os.path.join(RAIZ, f'resultados-{corp}-{año}.html')
    open(out, 'w', encoding='utf-8').write(s)
    print('ok', os.path.basename(out))


def clonar_alcaldias(año):
    s = fuente('alcaldias-2023.html')
    # Todo «2023» de esta página es el año (título, ruta de datos, nombres de CSV);
    # el reemplazo global va PRIMERO para no comerse el texto que se agrega abajo.
    s = s.replace('2023', str(año))
    s = s.replace(f"'29 Oct {año}'", f"'{FECHA[año][1]}'")
    s = rep(s, f"const BASE = `${{S3}}/bases+de+datos/output_alcaldias_{año}`;",
               "const BASE = new URLSearchParams(location.search).has('local')\n"
               f"    ? 'Bases de datos/output_alcaldias_{año}'     // ?local=1 → verificación antes de subir\n"
               f"    : `${{S3}}/bases+de+datos/output_alcaldias_{año}`;")
    s = rep(s, '''          académica ni un juicio político; es un mapa de lectura rápida.''',
               f'''          académica ni un juicio político; es un mapa de lectura rápida.
          <b style="color:var(--blue)">Ojo en {año}:</b> la curaduría manual de ganadores
          se hizo para 2023 y la filiación del partido es la de 2022-2026, no la de {año}:
          los ganadores de {año} por coalición quedan casi todos en "sin clasificar".''')
    s = rep(s, '<span class="footer-brand">Datos: Registraduría</span>',
               f'<span class="footer-brand">Datos: Registraduría (GCS {año}) · censo: Divipole actual, no el de {año}</span>')
    out = os.path.join(RAIZ, f'alcaldias-{año}.html')
    open(out, 'w', encoding='utf-8').write(s)
    print('ok', os.path.basename(out))


if __name__ == '__main__':
    año = int(sys.argv[1])
    for corp in ('jal', 'concejo', 'asamblea'):
        clonar_resultados(corp, año)
    clonar_alcaldias(año)
