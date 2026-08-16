#!/usr/bin/env python3
"""
Meta de votación al CONCEJO DE BOGOTÁ y perfil demográfico del electorado.

⚠️ La candidatura es al **Concejo**, no a la JAL: la circunscripción es TODA la
ciudad (45 curules), no la localidad. Su resultado de 2023 (709 votos en la JAL
de Barrios Unidos) sirve como base territorial, no como escala de la meta.

1. META — aritmética real del Concejo de Bogotá 2023, calculada del GCS:
   umbral (50% del cuociente), cifra repartidora y, como hay voto preferente,
   el voto del ÚLTIMO elegido de cada lista, que es el listón real.

   ⚠️⚠️ **El listón NO crece con la votación de la lista**: en 2023 una lista
   de 216.974 votos con 4 curules exigió 23.733, y otra de 404.399 con 8
   curules solo 9.280. Depende de cuán concentrado esté el voto dentro de la
   lista, así que la meta se publica como RANGO observado, nunca como una cifra
   única.

   ⚠️ El escenario que se pide es "la lista por la que se lance queda TERCERA".
   No se nombra ningún partido: se usa la votación que hizo falta para el tercer
   lugar como referencia de tamaño.

   ⚠️ Una de las listas grandes de 2023 fue CERRADA (voto solo por el logo): ahí
   el orden lo fija el partido y la meta personal no aplica. Se detecta sola
   (voto nominal < 15% del voto de lista) y se declara.

2. ESCALA — cómo se mueve el tamaño del electorado de Bogotá, con las últimas
   tres elecciones de Concejo, Cámara y Senado, para proyectar 2027.

3. PERFIL — edad y sexo de los sufragantes por puesto de la localidad
   (Registraduría, caché de 2022; 2023 solo trae 248 mesas y no sirve).

Salida:  Bases de datos/natalia-parra/nsp-meta.json
Correr:  python3 tools/natalia-parra/build_meta.py        (~4 min la 1ª vez)
"""
import csv
import json
import math
import os
import random
import statistics
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = os.path.join(RAIZ, 'Bases de datos')
OUT = os.path.join(BASES, 'natalia-parra')
RAW = os.path.join(OUT, 'raw')
GCS = os.path.join(BASES, 'FINAL SUBIDA GCS')
CACHE_EDAD = os.path.join(BASES, 'output_edad_1v', 'cache', 'p1v-2022.csv')

CURULES = 45           # Concejo de Bogotá
DEP, MUN = '16', '1'   # Bogotá D.C. (códigos Registraduría)
COR_CONCEJO_2023 = '4'
ESPECIALES = {'996', '997', '998', '999'}

LOCALIDAD = 'BARRIOS'
BANDAS = [
    ('18 a 20 años', '18-25'), ('21 a 25 años', '18-25'),
    ('26 a 30 años', '26-40'), ('31 a 35 años', '26-40'), ('36 a 40 años', '26-40'),
    ('41 a 45 años', '41-60'), ('46 a 50 años', '41-60'),
    ('51 a 55 años', '41-60'), ('56 a 60 años', '41-60'),
    ('Mayor a 60 años', '61+'),
]
ORDEN_BANDAS = ['18-25', '26-40', '41-60', '61+']

# Votación en Bogotá de las últimas tres elecciones de cada corporación.
# Concejo y el Congreso de 2018/2022 salen de los GCS (awk sobre el CSV);
# el Congreso de 2026, de los agregados ya publicados en S3.
SERIES_BOGOTA = {
    'concejo': [
        {'anio': 2015, 'validos': 2104844, 'total': 2716360},
        {'anio': 2019, 'validos': 2348974, 'total': 3141527},
        {'anio': 2023, 'validos': 2437317, 'total': 2982506},
    ],
    'senado': [
        {'anio': 2018, 'validos': 2291796, 'total': 2714213},
        {'anio': 2022, 'validos': 2535440, 'total': 2819276},
        {'anio': 2026, 'validos': 2900376, 'total': 3093090},
    ],
    'camara': [
        {'anio': 2018, 'validos': 2179469, 'total': 2653552},
        {'anio': 2022, 'validos': 2417904, 'total': 2726925},
        {'anio': 2026, 'validos': 2737779, 'total': 2952137},
    ],
}


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper().strip()


# ───────────────────── CONCEJO DE BOGOTÁ 2023 ─────────────────────
def concejo_2023():
    """Votos por lista y por candidato del Concejo de Bogotá 2023.

    ⚠️ `COD_CAN == '0'` es el VOTO POR LA LISTA (el logo). Sin contarlo, el
    total se queda en 1,70 M en vez de 2,44 M y las listas cerradas desaparecen
    del todo — fue exactamente lo que pasó al intentar armarlo desde el detalle
    por comuna, que solo agrega candidatos.
    """
    cache = os.path.join(RAW, 'concejo-bogota-2023.json')
    if os.path.exists(cache):
        return json.load(open(cache, encoding='utf-8'))
    csv.field_size_limit(10 ** 7)
    part, cand, esp = {}, {}, {}
    with open(os.path.join(GCS, 'GCS_2023TER.csv'), encoding='utf-8-sig') as f:
        r = csv.reader(f, delimiter=';')
        next(r)
        for row in r:
            if len(row) < 16 or row[2] != COR_CONCEJO_2023 or row[6] != DEP or row[7] != MUN:
                continue
            dpar, can, dcan = row[12], row[13], row[14]
            try:
                v = int(row[15])
            except ValueError:
                continue
            if can in ESPECIALES:
                esp[dcan] = esp.get(dcan, 0) + v
                continue
            part[dpar] = part.get(dpar, 0) + v
            if can != '0':
                cand[f'{dcan}||{dpar}'] = cand.get(f'{dcan}||{dpar}', 0) + v
    datos = {'part': part, 'cand': cand, 'esp': esp, 'validos': sum(part.values())}
    os.makedirs(RAW, exist_ok=True)
    json.dump(datos, open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    return datos


def cifra_repartidora(votos, curules):
    co = []
    for n, v in votos.items():
        for k in range(1, curules + 1):
            co.append((v / k, n))
    co.sort(key=lambda x: -x[0])
    rep = {n: 0 for n in votos}
    for _, n in co[:curules]:
        rep[n] += 1
    return co[curules - 1][0], rep


def bloque_meta():
    d = concejo_2023()
    part, validos = d['part'], d['validos']
    cuociente = validos / CURULES
    umbral = cuociente * 0.5
    pasan = {n: v for n, v in part.items() if v >= umbral}
    cifra, reparto = cifra_repartidora(pasan, CURULES)

    por_lista = {}
    for k, v in d['cand'].items():
        nm, pa = k.split('||')
        por_lista.setdefault(pa, []).append({'nombre': nm, 'votos': v})
    for L in por_lista.values():
        L.sort(key=lambda c: -c['votos'])

    orden = sorted(part.items(), key=lambda x: -x[1])
    listas, listones = [], []
    for i, (nombre, v) in enumerate(orden):
        cur = reparto.get(nombre, 0)
        L = por_lista.get(nombre, [])
        nominal = sum(c['votos'] for c in L)
        cerrada = nominal < 0.15 * v
        ue = L[cur - 1] if (cur and len(L) >= cur and not cerrada) else None
        if ue:
            listones.append({'curules': cur, 'votos_lista': v, 'ultimo': ue['votos']})
        listas.append({
            'orden': i + 1, 'nombre': nombre, 'votos': v,
            'pct': round(100 * v / validos, 2),
            'pasa_umbral': v >= umbral, 'curules': cur,
            'lista_cerrada': cerrada,
            'ultimo_elegido': ue['votos'] if ue else None,
            'primer_no_elegido': L[cur]['votos'] if (len(L) > cur and not cerrada) else None,
        })

    tercero = listas[2]
    ult = sorted(x['ultimo'] for x in listones)
    liston = {
        'min': ult[0], 'max': ult[-1],
        'mediana': int(statistics.median(ult)),
        'n': len(ult),
        'detalle': sorted(listones, key=lambda x: -x['votos_lista']),
    }
    return {
        'curules': CURULES, 'validos': validos,
        'blanco': d['esp'].get('VOTOS EN BLANCO', 0),
        'cuociente': round(cuociente, 1), 'umbral': round(umbral, 1),
        'cifra_repartidora': round(cifra, 1),
        'listas': listas,
        'tercero': {'votos': tercero['votos'], 'curules': tercero['curules'],
                    'pct': tercero['pct'], 'cerrada': tercero['lista_cerrada']},
        'liston': liston,
        'nota': ('Cifra repartidora sobre 45 curules con el resultado de 2023. El umbral es el '
                 '50% del cuociente electoral (art. 263 de la Constitución y Ley 1475 de 2011). '
                 'Con voto preferente, entrar no depende del umbral de la lista sino de quedar '
                 'entre los primeros de ella.'),
        'aviso_liston': ('El listón no crece con el tamaño de la lista: depende de cómo se '
                         'reparta el voto por dentro. En 2023 una lista de 216.974 votos exigió '
                         '23.733 para la última curul, y otra de 404.399 solo 9.280. Por eso la '
                         'meta se da como rango y no como una cifra exacta.'),
    }


# ───────────────────── ESCALA DEL ELECTORADO ─────────────────────
def bloque_escala(meta):
    censo = {}
    for y in (2018, 2022, 2026):
        ruta = os.path.join(BASES, f'censos-puesto-{y}.json')
        if os.path.exists(ruta):
            pp = json.load(open(ruta, encoding='utf-8'))['porPuesto']
            censo[y] = sum(v for k, v in pp.items() if k.startswith('16-001-'))

    def var(serie, campo='validos'):
        return [{'de': serie[i]['anio'], 'a': serie[i+1]['anio'],
                 'pct': round(100 * (serie[i+1][campo] / serie[i][campo] - 1), 1)}
                for i in range(len(serie) - 1)]

    conc = SERIES_BOGOTA['concejo']
    # El Concejo se proyecta con SU propia serie: la participación local y la
    # nacional no son comparables (el Congreso mueve más gente en Bogotá).
    ult = var(conc)[-1]['pct'] / 100
    proy = int(round(conc[-1]['validos'] * (1 + ult)))
    return {
        'censo_bogota': censo,
        'censo_var': [
            {'de': 2018, 'a': 2022, 'pct': round(100 * (censo[2022]/censo[2018] - 1), 1)},
            {'de': 2022, 'a': 2026, 'pct': round(100 * (censo[2026]/censo[2022] - 1), 1)},
        ] if len(censo) == 3 else [],
        'series': SERIES_BOGOTA,
        'variaciones': {k: var(v) for k, v in SERIES_BOGOTA.items()},
        'proyeccion_concejo_2027': proy,
        'factor_2027': round(1 + ult, 4),
        'nota': ('El voto al Congreso en Bogotá crece con fuerza (Senado +10,6% y luego +14,4%; '
                 'Cámara +10,9% y +13,2%), pero el del Concejo se desaceleró: +11,6% entre 2015 '
                 'y 2019 y solo +3,8% entre 2019 y 2023. La proyección de 2027 usa la serie del '
                 'propio Concejo, porque las elecciones locales y las nacionales no movilizan '
                 'igual: en 2026 el Senado ya sacó en Bogotá más votos válidos que el Concejo '
                 'de 2023.'),
    }


# ───────────────────── PERFIL DEMOGRÁFICO ─────────────────────
def perfil_puestos():
    agg = {}
    with open(CACHE_EDAD, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not norm(row['Cód. Comuna / Localidad']).startswith(LOCALIDAD):
                continue
            k = str(row['Cód. Puesto de Votación']).strip().lstrip('0') or '0'
            a = agg.setdefault(k, {'suf': 0, 'h': 0, 'm': 0, **{b: 0 for b in ORDEN_BANDAS}})
            a['suf'] += int(row['Cantidad de Sufragantes'] or 0)
            a['h'] += int(row['Cantidad Hombres'] or 0)
            a['m'] += int(row['Cantidad de Mujeres'] or 0)
            for col, banda in BANDAS:
                a[banda] += int(row[col] or 0)
    return agg


def duncan_davis(p, x):
    if x <= 0:
        return (0.0, 1.0)
    return (max(0.0, (p - (1 - x)) / x), min(1.0, p / x))


def goodman(xs, ys, pesos):
    sw = sum(pesos)
    if sw <= 0:
        return None
    mx = sum(w*x for w, x in zip(pesos, xs)) / sw
    my = sum(w*y for w, y in zip(pesos, ys)) / sw
    sxx = sum(w*(x-mx)**2 for w, x in zip(pesos, xs))
    if sxx <= 0:
        return None
    b = sum(w*(x-mx)*(y-my) for w, x, y in zip(pesos, xs, ys)) / sxx
    return (my - b*mx, my - b*mx + b)


def bloque_ei(elec, perfil):
    puestos = []
    for p in elec['puestos']:
        k = p['code'].split('-')[1].lstrip('0') or '0'
        d = perfil.get(k)
        if not d or not d['suf'] or not p['validos']:
            continue
        base = d['h'] + d['m']
        if base <= 0:
            continue
        puestos.append({
            'code': p['code'], 'nombre': p['nombre'], 'barrio': p['barrio'],
            'v': p['v'], 'validos': p['validos'], 'share': p['v']/p['validos'],
            'suf22': d['suf'], 'pct_mujeres': round(100*d['m']/base, 1),
            'edad': {b: round(100*d[b]/d['suf'], 1) for b in ORDEN_BANDAS},
            '_x_muj': d['m']/base,
            '_x_edad': {b: d[b]/d['suf'] for b in ORDEN_BANDAS},
        })
    if not puestos:
        return None
    p_global = sum(p['v'] for p in puestos) / sum(p['validos'] for p in puestos)
    pesos = [p['validos'] for p in puestos]
    ys = [p['share'] for p in puestos]

    def estimar(xs, comp, grupo):
        g = goodman(xs, ys, pesos)
        rnd = random.Random(20260816)
        muestras, n = [], len(xs)
        for _ in range(400):
            idx = [rnd.randrange(n) for _ in range(n)]
            gg = goodman([xs[i] for i in idx], [ys[i] for i in idx], [pesos[i] for i in idx])
            if gg:
                muestras.append(gg)
        def ic(j):
            vals = sorted(m[j] for m in muestras)
            return [round(100*vals[int(.025*len(vals))], 2),
                    round(100*vals[min(len(vals)-1, int(.975*len(vals)))], 2)] if vals else [None, None]
        x_medio = sum(w*x for w, x in zip(pesos, xs)) / sum(pesos)
        cb, ca = duncan_davis(p_global, x_medio), duncan_davis(p_global, 1-x_medio)
        def clip(v, cota):
            if v is None:
                return None, False
            c = min(max(v, cota[0]), cota[1])
            return round(100*c, 2), abs(c-v) > 1e-9
        est_b, borde_b = clip(g[1] if g else None, cb)
        est_a, _ = clip(g[0] if g else None, ca)
        ref = 100*p_global
        lect = None
        if est_b is not None:
            lect = ('por encima de su promedio' if est_b > ref*1.25
                    else 'por debajo de su promedio' if est_b < ref*0.75 else 'en línea con su promedio')
        return {'grupo': grupo, 'complemento': comp, 'peso_grupo': round(100*x_medio, 1),
                'est_grupo': est_b, 'est_complemento': est_a, 'en_borde': borde_b,
                'lectura': lect, 'ic_grupo': ic(1), 'ic_complemento': ic(0),
                'cota_grupo': [round(100*cb[0], 2), round(100*cb[1], 2)]}

    def corr(xs):
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        sx = math.sqrt(sum((x-mx)**2 for x in xs))
        sy = math.sqrt(sum((y-my)**2 for y in ys))
        return round(sum((x-mx)*(y-my) for x, y in zip(xs, ys))/(sx*sy), 2) if sx and sy else None

    return {
        'n_puestos': len(puestos), 'anio_perfil': 2022,
        'share_global': round(100*p_global, 3),
        'sexo': estimar([p['_x_muj'] for p in puestos], 'Hombres', 'Mujeres'),
        'edad': [estimar([p['_x_edad'][b] for p in puestos], 'Resto', b) for b in ORDEN_BANDAS],
        'correlaciones': {'mujeres': corr([p['_x_muj'] for p in puestos]),
                          **{b: corr([p['_x_edad'][b] for p in puestos]) for b in ORDEN_BANDAS}},
        'puestos': [{k: v for k, v in p.items() if not k.startswith('_')} for p in puestos],
        'aviso': ('Inferencia ecológica: estima cómo votó cada grupo cruzando la composición de '
                  'cada puesto con su votación, no votos individuales (el voto es secreto). Con '
                  '709 votos en 31 puestos la señal es débil: el intervalo es ancho y sirve para '
                  'orientar la campaña, no para afirmar cómo votó un grupo. Las cotas son el '
                  'rango que la agregación permite sin ningún supuesto (Duncan-Davis).'),
        'aviso_perfil': ('El perfil de edad y sexo es de los sufragantes de 2022: el archivo de '
                         'la Registraduría solo trae 248 mesas de las locales de 2023, una '
                         'muestra incompleta. Describe quién vota en cada puesto de la localidad.'),
    }


def main():
    elec = json.load(open(os.path.join(OUT, 'nsp-electoral.json'), encoding='utf-8'))
    meta = bloque_meta()
    escala = bloque_escala(meta)
    ei = bloque_ei(elec, perfil_puestos())

    lst = meta['liston']
    f = escala['factor_2027']
    meta['meta_2027'] = {
        'min': int(round(lst['min'] * f)),
        'mediana': int(round(lst['mediana'] * f)),
        'max': int(round(lst['max'] * f)),
        'factor': f,
        'base_local': elec['meta']['votos'],
    }

    datos = {'v': '2026-08-16', 'corporacion': 'CONCEJO DE BOGOTÁ',
             'meta_electoral': meta, 'escala': escala, 'demografia': ei}
    ruta = os.path.join(OUT, 'nsp-meta.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"  nsp-meta.json  {os.path.getsize(ruta)/1024:.0f} KB")

    print(f"\n  CONCEJO DE BOGOTÁ · {CURULES} curules · válidos {meta['validos']:,}")
    print(f"  cuociente {meta['cuociente']:,.0f} · umbral {meta['umbral']:,.0f} · "
          f"cifra repartidora {meta['cifra_repartidora']:,.0f}")
    for l in meta['listas'][:9]:
        cierre = ('[lista cerrada]' if l['lista_cerrada']
                  else (f"cierra {l['ultimo_elegido']:>7,}" if l['ultimo_elegido'] else ''))
        print(f"   {l['orden']:2}. {l['nombre'][:42]:44} {l['votos']:>9,} {l['curules']:>2}c  {cierre}")
    t = meta['tercero']
    print(f"\n  TERCER LUGAR: {t['votos']:,} votos → {t['curules']} curules")
    print(f"  Listón observado: {lst['min']:,} a {lst['max']:,} (mediana {lst['mediana']:,}) en {lst['n']} listas abiertas")
    m = meta['meta_2027']
    print(f"  META 2027 (×{f}): {m['min']:,} a {m['max']:,} · mediana {m['mediana']:,}")
    print(f"  Su base actual: {m['base_local']:,} votos (JAL de una localidad)")
    print(f"\n  Bogotá · válidos por corporación:")
    for k, s in SERIES_BOGOTA.items():
        print(f"    {k:8} " + ' · '.join(f"{x['anio']}: {x['validos']:,}" for x in s))
    print(f"    censo    " + ' · '.join(f"{y}: {v:,}" for y, v in escala['censo_bogota'].items()))


if __name__ == '__main__':
    main()
