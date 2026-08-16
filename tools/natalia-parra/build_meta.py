#!/usr/bin/env python3
"""
Meta de votación y perfil demográfico del electorado de Barrios Unidos.

Dos bloques:

1. META — cuántos votos hacen falta para una curul en la JAL, con la aritmética
   real de 2023: umbral, cifra repartidora y el voto del ÚLTIMO elegido de cada
   lista. Escenario pedido: lanzarse por el partido que quedó TERCERO.

   La JAL de Barrios Unidos tiene **9 ediles** (verificado en bogota.gov.co).
   Colombia reparte por **cifra repartidora** (art. 263 CP · Ley 1475 de 2011),
   con umbral del **50% del cuociente electoral** para corporaciones distintas
   al Senado. Con voto preferente el orden dentro de la lista lo deciden los
   votos individuales, así que la meta real no es el umbral del partido sino
   **superar al último de su propia lista que alcanzó curul**.

   ⚠️ Es ARITMÉTICA SOBRE 2023, no un pronóstico de 2027: el censo, la
   participación y las listas cambian. Se publica como escenario, con el rango
   que produce mover la participación, nunca como "necesita exactamente N".

2. PERFIL — quién vota en cada puesto: sexo y edad de los SUFRAGANTES, de la
   Registraduría (`Edadygenero.xlsx`, caché de 2022).

   ⚠️⚠️ **2023 no sirve para esto**: el archivo trae solo 248 mesas de
   Autoridades Locales (incompleto, hay que ignorarlo). Se usa el perfil de
   2022, que cubre 443 mesas de la localidad y cruza con **31 de los 32
   puestos** de 2023. Es la composición de quien fue a votar en 2022, usada
   como aproximación de quién vota en cada puesto — no es el censo de 2023.

   ⚠️ El bloque `ei` es INFERENCIA ECOLÓGICA y va con cotas duras: con 709
   votos repartidos en 31 puestos la señal es débil y sirve para orientar la
   campaña, no para afirmar cómo votó cada grupo. Ver el aviso en la salida.

Salida:  Bases de datos/natalia-parra/nsp-meta.json
Correr:  python3 tools/natalia-parra/build_meta.py
"""
import csv
import json
import math
import os
import random
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = os.path.join(RAIZ, 'Bases de datos')
OUT = os.path.join(BASES, 'natalia-parra')
CACHE_EDAD = os.path.join(BASES, 'output_edad_1v', 'cache', 'p1v-2022.csv')

CURULES = 9            # ediles de la JAL de Barrios Unidos (bogota.gov.co)
LOCALIDAD = 'BARRIOS'  # prefijo del nombre en Edadygenero (Bogotá trae NOMBRE, no código)

BANDAS = [
    ('18 a 20 años', '18-25'), ('21 a 25 años', '18-25'),
    ('26 a 30 años', '26-40'), ('31 a 35 años', '26-40'), ('36 a 40 años', '26-40'),
    ('41 a 45 años', '41-60'), ('46 a 50 años', '41-60'),
    ('51 a 55 años', '41-60'), ('56 a 60 años', '41-60'),
    ('Mayor a 60 años', '61+'),
]
ORDEN_BANDAS = ['18-25', '26-40', '41-60', '61+']


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper().strip()


# ─────────────────────────── 1 · META ───────────────────────────
def cifra_repartidora(votos_por_lista, curules):
    """Cifra repartidora: el mayor de los cocientes v/1, v/2 … v/curules,
    tomado en la posición `curules`. Devuelve (cifra, curules_por_lista)."""
    cocientes = []
    for nombre, v in votos_por_lista.items():
        for k in range(1, curules + 1):
            cocientes.append((v / k, nombre))
    cocientes.sort(key=lambda x: -x[0])
    corte = cocientes[curules - 1][0]
    reparto = {n: 0 for n in votos_por_lista}
    for c, n in cocientes[:curules]:
        reparto[n] += 1
    return corte, reparto


def proyeccion_censo():
    """Censo electoral de la localidad en 2018 · 2022 · 2026 y proyección a 2027.

    ⚠️⚠️ El censo NACIONAL crece sin pausa (36,8M → 41,3M entre 2018 y 2026,
    +12%), pero **Barrios Unidos no**: 146.662 → 154.760 → 149.054, o sea que
    se CONTRAJO 3,7% desde 2022 mientras Bogotá crecía 1,4%. Es una localidad
    céntrica y envejecida (22% del electorado pasa de 60 años). Aplicarle el
    crecimiento nacional inflaría la meta sin razón, así que la proyección usa
    la tendencia LOCAL de largo plazo (2018-2026), más estable que el último
    tramo, y se declara el rango.
    """
    dirs = os.path.join(BASES, 'censos-puesto-%d.json')
    pref = '16-001-12-'
    c = {}
    for y in (2018, 2022, 2026):
        ruta = dirs % y
        if not os.path.exists(ruta):
            return None
        pp = json.load(open(ruta, encoding='utf-8'))['porPuesto']
        c[y] = sum(v for k, v in pp.items() if k.startswith(pref))

    tasa_larga = (c[2026] / c[2018]) ** (1 / 8) - 1     # 2018→2026
    tasa_corta = (c[2026] / c[2022]) ** (1 / 4) - 1     # 2022→2026 (negativa)
    # El año de la elección (2023) se interpola entre los dos censos que lo rodean.
    c2023 = c[2022] + (c[2026] - c[2022]) * (1 / 4)
    c2027 = c[2026] * (1 + tasa_larga)
    c2027_baja = c[2026] * (1 + tasa_corta)
    return {
        'c2018': c[2018], 'c2022': c[2022], 'c2026': c[2026],
        'c2023': int(round(c2023)), 'c2027': int(round(c2027)),
        'c2027_baja': int(round(c2027_baja)),
        'tasa_larga': round(100 * tasa_larga, 2),
        'tasa_corta': round(100 * tasa_corta, 2),
        'var_2022_2026': round(100 * (c[2026] / c[2022] - 1), 2),
        'nota': ('El censo nacional crece sin pausa, pero el de la localidad se contrajo '
                 '3,7% entre 2022 y 2026. La proyección usa la tendencia local de largo '
                 'plazo (2018-2026), no la nacional: usar la nacional inflaría la meta.'),
    }


def votos_por_candidato():
    """Votos de CADA candidato y su lista, sumados de los puestos del JSON de
    comuna (el `cands` de ahí solo trae [nombre, índice_de_partido])."""
    com = json.load(open(os.path.join(OUT, 'raw', 'comuna-16-001-12.json'), encoding='utf-8'))
    tot = {}
    for p in com['puestos']:
        for i, v in p['v']:
            tot[i] = tot.get(i, 0) + v
    out = []
    for i, (nombre, par) in enumerate(com['cands']):
        out.append({'nombre': nombre, 'partido': com['partidos'][par][0],
                    'votos': tot.get(i, 0)})
    out.sort(key=lambda c: -c['votos'])
    return out


def bloque_meta(elec):
    partidos = {p['nombre']: p['votos'] for p in elec['partidos']}
    validos = elec['meta']['validos_localidad']

    cuociente = validos / CURULES
    umbral = cuociente * 0.5          # 50% del cuociente (art. 263 CP)
    pasan = {n: v for n, v in partidos.items() if v >= umbral}
    cifra, reparto = cifra_repartidora(pasan, CURULES)

    cands = votos_por_candidato()
    por_lista = {}
    for c in cands:
        por_lista.setdefault(c['partido'], []).append(c)

    orden = sorted(partidos.items(), key=lambda x: -x[1])
    tercero = orden[2][0] if len(orden) > 2 else orden[-1][0]

    listas = []
    for i, (nombre, v) in enumerate(orden):
        cur = reparto.get(nombre, 0)
        lista = por_lista.get(nombre, [])
        nominal = sum(c['votos'] for c in lista)
        # Con voto preferente el orden lo dan los votos individuales: el que
        # cierra la curul es el candidato en la posición `cur`. Si la lista es
        # CERRADA el voto nominal es ~0 y el orden lo fijó el partido: ahí la
        # meta personal no aplica y se declara.
        cerrada = nominal < 0.15 * v
        ultimo = lista[cur - 1] if (cur and len(lista) >= cur and not cerrada) else None
        siguiente = lista[cur] if (len(lista) > cur and not cerrada) else None
        listas.append({
            'nombre': nombre,
            'votos': v,
            'pct': round(100 * v / validos, 2),
            'pasa_umbral': v >= umbral,
            'curules': cur,
            'orden': i + 1,
            'lista_cerrada': cerrada,
            'voto_nominal': nominal,
            'ultimo_elegido': ultimo,
            'primer_no_elegido': siguiente,
            'top': lista[:6],
        })

    l3 = next(l for l in listas if l['nombre'] == tercero)
    ella = elec['meta']['nombre']
    su_lista = next(l for l in listas if l['nombre'] == elec['meta']['partido'])
    su_ultimo = su_lista['ultimo_elegido']

    meta_base = (l3['ultimo_elegido']['votos'] + 1) if l3['ultimo_elegido'] else None
    censo = proyeccion_censo()
    escenarios = None
    if meta_base and censo:
        # El listón escala con los VOTANTES, no con el censo a secas: censo
        # proyectado × participación. Barrios Unidos se contrajo desde 2022,
        # así que el censo empuja la meta hacia ABAJO; lo que la sube es la
        # participación.
        votantes_2023 = elec['meta']['validos_localidad'] + elec['meta']['blanco_localidad'] + elec['meta']['nulos_localidad']
        part_2023 = votantes_2023 / censo['c2023']
        def meta_con(part, censo_27):
            return int(round(meta_base * (censo_27 * part) / votantes_2023))
        escenarios = [
            {'nombre': 'Censo proyectado', 'votos': meta_con(part_2023, censo['c2027']),
             'desc': f"Con el censo que se proyecta para 2027 ({censo['c2027']:,}) y la misma "
                     f"participación de 2023 ({part_2023*100:.1f}%)."},
            {'nombre': 'Participación +5 pp', 'votos': meta_con(part_2023 + 0.05, censo['c2027']),
             'desc': 'Si vota una porción mayor del censo, el listón sube en la misma proporción.'},
            {'nombre': 'Margen de seguridad', 'votos': int(round(meta_con(part_2023 + 0.05, censo['c2027']) * 1.15)),
             'desc': 'Un 15% por encima del peor caso, para no depender de que la lista repita su tamaño.'},
        ]

    return {
        'curules': CURULES,
        'validos': validos,
        'cuociente': round(cuociente, 1),
        'umbral': round(umbral, 1),
        'cifra_repartidora': round(cifra, 1),
        'listas': listas,
        'partido_tercero': tercero,
        'curules_tercero': l3['curules'],
        'meta_base': meta_base,
        'ultimo_tercero': l3['ultimo_elegido']['votos'] if l3['ultimo_elegido'] else None,
        'escenarios': escenarios,
        'censo': censo,
        'su_votacion': elec['meta']['votos'],
        'su_partido': elec['meta']['partido'],
        'su_ultimo_elegido': su_ultimo,
        'brecha_2023': (su_ultimo['votos'] - elec['meta']['votos']) if su_ultimo else None,
        'nombre': ella,
        'nota': ('Cifra repartidora con 9 curules sobre los resultados de 2023. El umbral '
                 'es el 50% del cuociente electoral (art. 263 de la Constitución y Ley 1475 '
                 'de 2011). Con voto preferente, la meta personal no es el umbral del '
                 'partido sino superar al último de la propia lista que alcanza curul.'),
        'aviso': ('Es aritmética sobre 2023, no un pronóstico de 2027: el censo, la '
                  'participación y la composición de las listas cambian. Sirve para '
                  'dimensionar el esfuerzo, no como cifra exacta.'),
    }


# ───────────────────── 2 · PERFIL DEMOGRÁFICO ─────────────────────
def perfil_puestos():
    """Sufragantes 2022 por puesto de Barrios Unidos: sexo y bandas de edad."""
    agg = {}
    with open(CACHE_EDAD, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not norm(row['Cód. Comuna / Localidad']).startswith(LOCALIDAD):
                continue
            k = str(row['Cód. Puesto de Votación']).strip().lstrip('0') or '0'
            a = agg.setdefault(k, {'suf': 0, 'h': 0, 'm': 0,
                                   **{b: 0 for b in ORDEN_BANDAS}})
            a['suf'] += int(row['Cantidad de Sufragantes'] or 0)
            a['h'] += int(row['Cantidad Hombres'] or 0)
            a['m'] += int(row['Cantidad de Mujeres'] or 0)
            for col, banda in BANDAS:
                a[banda] += int(row[col] or 0)
    return agg


def duncan_davis(p, x):
    """Cotas duras del voto del grupo: lo que la agregación permite sin
    supuestos. p = share global del candidato, x = peso del grupo."""
    if x <= 0:
        return (0.0, 1.0)
    lo = max(0.0, (p - (1 - x)) / x)
    hi = min(1.0, p / x)
    return (lo, hi)


def goodman(xs, ys, pesos):
    """Regresión ecológica de Goodman ponderada: y = a + b·x, con
    a = voto del grupo ausente y a+b = voto del grupo. Devuelve (a, a+b)."""
    sw = sum(pesos)
    if sw <= 0:
        return None
    mx = sum(w * x for w, x in zip(pesos, xs)) / sw
    my = sum(w * y for w, y in zip(pesos, ys)) / sw
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(pesos, xs))
    sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(pesos, xs, ys))
    if sxx <= 0:
        return None
    b = sxy / sxx
    a = my - b * mx
    return (a, a + b)


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
            'v': p['v'], 'validos': p['validos'],
            'share': p['v'] / p['validos'],
            'suf22': d['suf'],
            'pct_mujeres': round(100 * d['m'] / base, 1),
            'edad': {b: round(100 * d[b] / d['suf'], 1) if d['suf'] else 0 for b in ORDEN_BANDAS},
            '_x_muj': d['m'] / base,
            '_x_edad': {b: (d[b] / d['suf'] if d['suf'] else 0) for b in ORDEN_BANDAS},
        })
    if not puestos:
        return None

    tot_v = sum(p['v'] for p in puestos)
    tot_val = sum(p['validos'] for p in puestos)
    p_global = tot_v / tot_val

    pesos = [p['validos'] for p in puestos]
    ys = [p['share'] for p in puestos]

    def estimar(xs, etiqueta_a, etiqueta_b):
        g = goodman(xs, ys, pesos)
        # Bootstrap sobre puestos: mide cuánto se mueve la estimación al
        # cambiar la muestra. Con 31 puestos el intervalo sale ancho, y eso
        # es exactamente lo que hay que mostrar.
        rnd = random.Random(20260816)
        muestras = []
        n = len(xs)
        for _ in range(400):
            idx = [rnd.randrange(n) for _ in range(n)]
            gg = goodman([xs[i] for i in idx], [ys[i] for i in idx], [pesos[i] for i in idx])
            if gg:
                muestras.append(gg)
        def ic(j):
            vals = sorted(m[j] for m in muestras)
            if not vals:
                return [None, None]
            return [round(100 * vals[int(.025 * len(vals))], 2),
                    round(100 * vals[min(len(vals) - 1, int(.975 * len(vals)))], 2)]
        x_medio = sum(w * x for w, x in zip(pesos, xs)) / sum(pesos)
        cota_b = duncan_davis(p_global, x_medio)
        cota_a = duncan_davis(p_global, 1 - x_medio)
        # Goodman no está restringido y con señal débil devuelve valores fuera
        # de [0, 1] — acá salieron negativos en dos bandas. Un "-1,85% votó por
        # ella" no significa nada: se acota al rango que la agregación permite
        # (Duncan-Davis) y se marca que la estimación tocó el borde.
        def clip(v, cota):
            if v is None:
                return None, False
            c = min(max(v, cota[0]), cota[1])
            return round(100 * c, 2), abs(c - v) > 1e-9
        est_b, borde_b = clip(g[1] if g else None, cota_b)
        est_a, borde_a = clip(g[0] if g else None, cota_a)
        ref = 100 * p_global
        lectura = None
        if est_b is not None:
            if est_b > ref * 1.25:
                lectura = 'por encima de su promedio'
            elif est_b < ref * 0.75:
                lectura = 'por debajo de su promedio'
            else:
                lectura = 'en línea con su promedio'
        return {
            'grupo': etiqueta_b, 'complemento': etiqueta_a,
            'peso_grupo': round(100 * x_medio, 1),
            'est_grupo': est_b, 'est_complemento': est_a,
            'en_borde': borde_b, 'lectura': lectura,
            'ic_grupo': ic(1), 'ic_complemento': ic(0),
            'cota_grupo': [round(100 * cota_b[0], 2), round(100 * cota_b[1], 2)],
            'cota_complemento': [round(100 * cota_a[0], 2), round(100 * cota_a[1], 2)],
        }

    sexo = estimar([p['_x_muj'] for p in puestos], 'Hombres', 'Mujeres')
    edad = [estimar([p['_x_edad'][b] for p in puestos], 'Resto', b) for b in ORDEN_BANDAS]

    # Correlación simple share ↔ demografía: más legible que el coeficiente
    # crudo y suficiente para orientar dónde está su voto.
    def corr(xs):
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        sy = math.sqrt(sum((y - my) ** 2 for y in ys))
        if sx == 0 or sy == 0:
            return None
        return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 2)

    return {
        'n_puestos': len(puestos),
        'anio_perfil': 2022,
        'share_global': round(100 * p_global, 3),
        'sexo': sexo,
        'edad': edad,
        'correlaciones': {
            'mujeres': corr([p['_x_muj'] for p in puestos]),
            **{b: corr([p['_x_edad'][b] for p in puestos]) for b in ORDEN_BANDAS},
        },
        'puestos': [{k: v for k, v in p.items() if not k.startswith('_')} for p in puestos],
        'aviso': ('Inferencia ecológica: se estima cómo votó cada grupo a partir de la '
                  'relación entre la composición de cada puesto y su votación, no de votos '
                  'individuales (el voto es secreto). Con 709 votos repartidos en 31 puestos '
                  'la señal es débil: el intervalo es ancho y sirve para orientar la campaña, '
                  'no para afirmar cómo votó un grupo. Las cotas son el rango que la '
                  'agregación permite sin ningún supuesto (Duncan-Davis).'),
        'aviso_perfil': ('El perfil de edad y sexo es de los sufragantes de 2022: el archivo '
                         'de la Registraduría solo trae 248 mesas de las locales de 2023, que '
                         'es una muestra incompleta. Describe quién vota en cada puesto, no el '
                         'censo de 2023.'),
    }


def main():
    elec = json.load(open(os.path.join(OUT, 'nsp-electoral.json'), encoding='utf-8'))
    meta = bloque_meta(elec)
    perfil = perfil_puestos()
    ei = bloque_ei(elec, perfil)

    datos = {'v': '2026-08-16', 'meta_electoral': meta, 'demografia': ei}
    ruta = os.path.join(OUT, 'nsp-meta.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    print(f"  nsp-meta.json  {os.path.getsize(ruta)/1024:.0f} KB")
    print(f"\n  {CURULES} curules · válidos {meta['validos']:,}")
    print(f"  cuociente {meta['cuociente']:,.0f} · umbral {meta['umbral']:,.0f} · "
          f"cifra repartidora {meta['cifra_repartidora']:,.0f}")
    for l in meta['listas']:
        marca = '←' if l['nombre'] == meta['partido_tercero'] else ' '
        ue = l['ultimo_elegido']
        cierre = f" · cierra con {ue['votos']:,} ({ue['nombre'][:26]})" if ue else ''
        print(f"   {l['orden']}. {l['nombre'][:40]:42} {l['votos']:6,}  "
              f"{'✗' if not l['pasa_umbral'] else ' '} {l['curules']}c {marca}{cierre}")
    print(f"\n  META por el tercero ({meta['partido_tercero']}): {meta['meta_base']:,} votos")
    for e in meta['escenarios'] or []:
        print(f"    {e['nombre']:26} {e['votos']:6,}")
    print(f"  Ella tuvo {meta['su_votacion']:,}; el que cerró su lista sacó "
          f"{meta['su_ultimo_elegido']['votos']:,} (brecha {meta['brecha_2023']:,})")
    if ei:
        print(f"\n  perfil: {ei['n_puestos']} puestos · mujeres {ei['sexo']['peso_grupo']}% del electorado")
        print(f"  correlación share↔%mujeres: {ei['correlaciones']['mujeres']}")
        for e in ei['edad']:
            print(f"    {e['grupo']:6} peso {e['peso_grupo']:5}% · est {e['est_grupo']}% "
                  f"IC {e['ic_grupo']} · cota {e['cota_grupo']}")


if __name__ == '__main__':
    main()
