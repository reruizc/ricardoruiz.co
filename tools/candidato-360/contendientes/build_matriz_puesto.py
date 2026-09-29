#!/usr/bin/env python3
"""build_matriz_puesto.py — votos de TODAS las candidaturas por puesto, por
circunscripción (D1 del plan de contendientes, fase 4).

La tarjeta de contendientes necesita, para cada rival, sus votos puesto a
puesto dentro del territorio de la campaña. Esa matriz ya existía para el
Concejo y la JAL de 2023 en 11 ciudades (`{corp}-2023/comuna/…`, con barrio y
coordenada) y para la Asamblea 2023 por municipio. Para lo demás —el concejo de
los otros 1.090 municipios, las alcaldías, las gobernaciones y 2019— había que
bajar el archivo mesa a mesa de CADA rival: en Bogotá, 2 MB por concejal.

Formato: el MISMO de los archivos por comuna, para que el motor
(`matrizDesdeArchivos` en candidato-360-contendientes.js) lo lea sin cambios:
    {dde, mme, eleccion, fuente, partidos: [[nombre, total]], cands: [[nombre, iPartido]],
     puestos: [{code: "zz-pp", mme?, validos, blanco, v: [[iCand, votos]], l: [[iPartido, votos]]}]}
  · validos = candidatos + voto solo por la lista (COD_CAN 0); SIN el blanco,
    que va aparte (igual que en los archivos por comuna).
  · `l` es el voto de lista, con el índice del PARTIDO (no de una lista aparte:
    medido en los archivos por comuna, ahí apunta a `partidos`).
  · En gobernación y asamblea el archivo es del DEPARTAMENTO y cada puesto
    lleva su `mme`.

Circunscripción: concejo y alcaldía = municipio (`{dde}-{mme}.json`);
gobernación y asamblea = departamento (`{dde}.json`). La JAL NO va acá: su
circunscripción es la comuna, que la Registraduría no trae en la fila (sale del
georef por puesto) y que ya está cubierta en las 11 ciudades.

El código de puesto sigue la hoja de vida: la letra de los 187 puestos que la
llevan se conserva. Un puesto con código raro no se descarta: se escribe tal cual.

Salida: Bases de datos/output_matriz_puesto/{corp}-{año}/{dde}[-{mme}].json

  python3 tools/candidato-360/contendientes/build_matriz_puesto.py 2023TER concejo alcaldia gobernacion
  python3 tools/candidato-360/contendientes/build_matriz_puesto.py 2019TER concejo alcaldia gobernacion asamblea
  python3 tools/candidato-360/contendientes/build_matriz_puesto.py --validar 2023TER concejo

Subir (comprimido, como los índices; el prefijo ya es público). Primero una
copia espejo comprimida y después UNA pasada recursiva — un `aws s3 cp` por
archivo son 4.493 llamadas y más de una hora:
  cd "Bases de datos/output_matriz_puesto" && GZ=<carpeta temporal>
  for d in */; do mkdir -p "$GZ/$d"; done
  find . -name '*.json' -print0 | xargs -0 -P 8 -I{} sh -c 'gzip -9 -c "{}" > "'"$GZ"'/{}"'
  aws s3 cp "$GZ/" "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/matriz-puesto/" \
    --recursive --content-encoding gzip --content-type application/json \
    --cache-control "public, max-age=3600" --only-show-errors
"""
import csv, gzip, importlib.util, json, os, sys, time, urllib.request
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
GCS = os.path.join(ROOT, 'Bases de datos', 'FINAL SUBIDA GCS')
SALIDA = os.path.join(ROOT, 'Bases de datos', 'output_matriz_puesto')
S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'

_spec = importlib.util.spec_from_file_location('terr', os.path.join(ROOT, 'tools', 'analisis-candidato', 'build_territorial_candidatos.py'))
_terr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_terr)
TER, T2011 = _terr.LAYOUT_TER, _terr.LAYOUT_2011

# Los mismos códigos de corporación de build_totales_puesto.py (cambian por año).
ARCHIVOS = {
    '2011TER': (T2011, 2011, {'4': 'gobernacion', '5': 'asamblea', '6': 'alcaldia', '7': 'concejo'}),
    '2015TER': (TER,   2015, {'1': 'gobernacion', '2': 'asamblea', '3': 'alcaldia', '4': 'concejo'}),
    '2019TER': (TER,   2019, {'4': 'gobernacion', '5': 'asamblea', '6': 'alcaldia', '7': 'concejo'}),
    '2023TER': (TER,   2023, {'1': 'gobernacion', '2': 'asamblea', '3': 'alcaldia', '4': 'concejo'}),
}
DEPARTAMENTAL = {'gobernacion', 'asamblea'}
NO_VALIDOS = {'997', '998', '999'}
ZONAS_FUERA = {'90', '98'}   # censo consolidado y cárceles: el motor tampoco los usa


def pad(v, n):
    d = ''.join(c for c in (v or '') if c.isdigit())
    return d.zfill(n)


# ⚠️ La identidad es el CÓDIGO (partido + candidato), no el nombre: en el
# crudo de 2019 la misma candidatura aparece con nombres distintos en filas
# distintas (medido: el candidato 1 del Centro Democrático en Santa Marta sale
# como «LEDA MARINA MACIAS SIERRA» en unas filas y con otro nombre en otras), y
# el índice oficial la cuenta una vez por código. El nombre que se escribe es la
# variante con más votos.
def partido_de(C, r, v):
    L = C['L']; cod = r[L['PAR']].strip()
    if cod not in C['partidos']:
        C['partidos'][cod] = len(C['partidos'])
    C['nomPar'][cod][r[L['DESPAR']].strip()] += v
    return C['partidos'][cod]


def cand_de(C, r, ip, can, v):
    L = C['L']; cod = f"{r[L['PAR']].strip()}-{can}"
    if cod not in C['cands']:
        C['cands'][cod] = (len(C['cands']), ip)
    C['nomCan'][cod][r[L['DESCAN']].strip()] += v
    return C['cands'][cod][0]


def procesar(nombre, corps):
    L, ano, cors = ARCHIVOS[nombre]
    quiero = {k: v for k, v in cors.items() if v in corps}
    if not quiero:
        sys.exit(f'{nombre} no trae ninguna de: {", ".join(corps)}')
    ruta = os.path.join(GCS, f'GCS_{nombre}.csv')
    t0 = time.time()
    # circ → {'cands': {(nombre, partido): i}, 'partidos': {nombre: i}, 'puestos': {(mme, code): {...}}}
    circs = {c: {} for c in quiero.values()}
    filas = 0
    with open(ruta, encoding='utf-8-sig', errors='replace', newline='') as f:
        lector = csv.reader(f, delimiter=';')
        next(lector, None)
        for r in lector:
            if len(r) < L['NCOL']:
                continue
            corp = quiero.get(r[L['COR']].strip())
            if corp is None:
                continue
            try:
                v = int(r[L['VOT']] or 0)
            except ValueError:
                continue
            if v <= 0:
                continue
            zz = pad(r[L['ZZ']], 2)
            dde, mme = pad(r[L['DDE']], 2), pad(r[L['MME']], 3)
            clave = dde if corp in DEPARTAMENTAL else f'{dde}-{mme}'
            C = circs[corp].get(clave)
            if C is None:
                C = circs[corp][clave] = {'L': L, 'dde': dde, 'mme': mme, 'cands': {}, 'partidos': {}, 'tot': defaultdict(int), 'puestos': {}, 'fuera': defaultdict(int),
                                          'nomPar': defaultdict(lambda: defaultdict(int)), 'nomCan': defaultdict(lambda: defaultdict(int))}
            can = r[L['CAN']].strip()
            if zz in ZONAS_FUERA:
                # Los votos del puesto censo y de las cárceles no van a ningún
                # puesto del mapa, pero se guardan por candidato: con ellos la
                # matriz cuadra al voto con el índice y lo omitido se declara.
                if can not in NO_VALIDOS and can not in ('996', '0'):
                    ip = partido_de(C, r, v)
                    C['fuera'][cand_de(C, r, ip, can, v)] += v
                continue
            code = zz + '-' + (r[L['PP']] or '').strip().upper().zfill(2)
            P = C['puestos'].get((mme, code))
            if P is None:
                P = C['puestos'][(mme, code)] = {'validos': 0, 'blanco': 0, 'v': defaultdict(int), 'l': defaultdict(int)}
            if can in NO_VALIDOS:
                continue
            if can == '996':
                P['blanco'] += v
                continue
            filas += 1
            ip = partido_de(C, r, v)
            C['tot'][ip] += v
            P['validos'] += v
            if can == '0':
                P['l'][ip] += v
                continue
            P['v'][cand_de(C, r, ip, can, v)] += v
    print(f'· {nombre}: {filas:,} filas útiles en {time.time() - t0:.0f} s')
    for corp, porCirc in circs.items():
        dir_ = os.path.join(SALIDA, f'{corp}-{ano}')
        os.makedirs(dir_, exist_ok=True)
        bytes_ = 0
        for clave, C in sorted(porCirc.items()):
            mejor = lambda d: max(d.items(), key=lambda x: x[1])[0] if d else ''
            partidos = sorted(C['partidos'].items(), key=lambda x: x[1])          # [(codPar, i)]
            cands = sorted(C['cands'].items(), key=lambda x: x[1][0])             # [(codPar-codCan, (i, ip))]
            puestos = []
            for (mme, code), P in sorted(C['puestos'].items()):
                if not P['validos'] and not P['blanco']:
                    continue
                p = {'code': code, 'validos': P['validos'], 'blanco': P['blanco'],
                     'v': sorted(([i, n] for i, n in P['v'].items()), key=lambda x: -x[1]),
                     'l': sorted(([i, n] for i, n in P['l'].items()), key=lambda x: -x[1])}
                if corp in DEPARTAMENTAL:
                    p['mme'] = mme
                puestos.append(p)
            datos = {'dde': C['dde'], **({} if corp in DEPARTAMENTAL else {'mme': C['mme']}),
                     'eleccion': f'{corp} {ano}', 'fuente': f'GCS_{nombre}.csv', 'v': time.strftime('%Y-%m-%d'),
                     # partidos: [nombre, total, código]; cands: [nombre, iPartido, "codPar-codCan"] (el código casa con el slug del índice)
                     'partidos': [[mejor(C['nomPar'][cod]), C['tot'][i], cod] for cod, i in partidos],
                     'cands': [[mejor(C['nomCan'][cod]), ip, cod] for cod, (i, ip) in cands],
                     'puestos': puestos,
                     # Votos por candidato en las zonas 90 (puesto censo) y 98 (cárceles): fuera del mapa.
                     'fuera9098': sorted(([i, n] for i, n in C['fuera'].items()), key=lambda x: -x[1])}
            salida = os.path.join(dir_, f'{clave}.json')
            with open(salida, 'w') as g:
                json.dump(datos, g, separators=(',', ':'), ensure_ascii=False)
            bytes_ += os.path.getsize(salida)
        print(f'    {corp}-{ano}: {len(porCirc):,} archivos · {bytes_ / 1e6:.1f} MB en claro')


def baja(url):
    req = urllib.request.Request(url, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'Mozilla/5.0 (candidato-360 matriz)'})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return json.loads(data)


def norm(s):
    import unicodedata
    s = unicodedata.normalize('NFD', s or '')
    # Compacta, como `llaveCand` del motor: sin espacios ni signos (ver «ZUÐIGA»).
    return ''.join(ch for ch in ''.join(c for c in s if not unicodedata.combining(c)).upper() if ch.isascii() and ch.isalnum())


def validar(nombre, corps):
    """Cada candidatura del índice oficial tiene que sumar EXACTAMENTE sus votos
    en la matriz: los de los puestos más los de las zonas 90 y 98 (`fuera9098`)."""
    L, ano, cors = ARCHIVOS[nombre]
    for corp in corps:
        idx = baja(f'{S3}/{corp}-{ano}/index-{corp}-{ano}.json')
        filas = idx['candidatos'] if isinstance(idx, dict) else idx
        dir_ = os.path.join(SALIDA, f'{corp}-{ano}')
        suma = {}
        for fn in os.listdir(dir_):
            d = json.load(open(os.path.join(dir_, fn)))
            clave = fn[:-5]
            for i, v in [x for p in d['puestos'] for x in p['v']] + d.get('fuera9098', []):
                k = (clave, d['cands'][i][2])
                suma[k] = suma.get(k, 0) + v
        exactos = cerca = falta = 0
        peores = []
        for c in filas:
            s = c['slug'].split('-')
            clave = f'{int(s[1]):02d}' if corp in DEPARTAMENTAL else f'{int(s[1]):02d}-{int(s[2]):03d}'
            m = suma.get((clave, '-'.join(s[-2:] if corp in DEPARTAMENTAL else s[3:5])))
            if m is None:
                falta += 1; continue
            if m == c['votos']:
                exactos += 1
            else:
                cerca += 1
                peores.append((abs(c['votos'] - m) / max(1, c['votos']), c['nombre'], c['votos'], m))
        peores.sort(reverse=True)
        print(f'  {corp}-{ano}: {len(filas):,} en el índice · {exactos:,} exactos · {cerca:,} distintos · {falta:,} sin casar')
        for x in peores[:3]:
            print(f'      {x[1]}: índice {x[2]:,} · matriz {x[3]:,} ({x[0]:.1%} menos)')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or args[0] not in ARCHIVOS:
        sys.exit(f'uso: build_matriz_puesto.py [--validar] <{"|".join(ARCHIVOS)}> <corporaciones…>')
    corps = args[1:] or ['concejo', 'alcaldia', 'gobernacion']
    if '--validar' in sys.argv:
        validar(args[0], corps)
    else:
        procesar(args[0], corps)
