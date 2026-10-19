#!/usr/bin/env python3
"""Arquetipos de comportamiento electoral de Bogotá, por corporación (borrador v0).

    python3 tools/candidato-360/arquetipos-bogota/arquetipos.py

Lee Bases de datos/arquetipos-bogota/barrios.csv (de medir.py) y agrupa los
barrios DOS veces: por cómo votan el Concejo y por cómo votan la Alcaldía. Cada
corporación tiene su propio juego de variables (estrato y movilización en las
dos, más las que describen el estilo de voto de esa elección).

Método (heurística declarada, ver LEEME.md):
  1. Variables estandarizadas (media 0, desviación 1 entre los barrios).
  2. k-medias con semilla fija; k = 8 en las dos corporaciones (v1, oct-19-2026;
     la v0 tenía 6 y 5, respaldo en respaldo-v6-20261019/).
  3. Cada grupo recibe su nombre comparando su centro con una FIRMA escrita a
     mano (qué variables lo distinguen), con asignación óptima: así el nombre
     no depende del número que k-medias le dé al grupo.
  4. Cada barrio recibe una MEZCLA (suma 1) según su distancia a los centros,
     como en Medellín y Cartagena, y una CONFIANZA: en cuántas de 200
     re-muestras cae en el mismo arquetipo. Un barrio de frontera se dice.

Salida: Bases de datos/arquetipos-bogota/arquetipos-bogota.json
"""
import csv, json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans

RAIZ = Path(__file__).resolve().parents[3]
DIR = RAIZ / 'Bases de datos' / 'arquetipos-bogota'
SEMILLA = 2027
R_BOOT = 200

CORP = {
    'concejo': {
        'k': 8,
        'vars': ['estrato', 'part23', 'mov_local', 'cerrada', 'logo_abierta', 'arraigo', 'desafeccion'],
        # Firma: qué distingue a cada arquetipo (signo esperado en unidades z).
        # v1 (oct-19-2026): de 6 a 8. Con k = 8 la «clase media de nombre» se
        # parte en dos (la que vota poco a nombres de partido y la que vota
        # mucho sin dueño en el barrio) y el norte en dos (opinión y figuras).
        'firmas': {
            'figuras':     {'estrato': 2.5, 'arraigo': 1.5, 'desafeccion': -2, 'cerrada': -2},
            'opinion':     {'estrato': 1.4, 'part23': 1.2, 'cerrada': -1.5, 'arraigo': -0.5, 'desafeccion': -1.4},
            'movilizada':  {'part23': 1.5, 'mov_local': 1.7, 'arraigo': 0.9, 'logo_abierta': -1.3},
            'gestion':     {'arraigo': 1.7, 'logo_abierta': -0.9},
            'poco-voto':   {'desafeccion': 1.4, 'part23': -1.1, 'mov_local': -1.1, 'logo_abierta': 1.8, 'estrato': -1.2},
            'partido':     {'cerrada': 0.9, 'desafeccion': 0.8, 'estrato': -0.6, 'part23': -0.6},
            'sin-dueno':   {'part23': 0.6, 'mov_local': 0.5, 'arraigo': -0.8},
            'nombre':      {},
        },
    },
    'alcaldia': {
        'k': 8,
        'vars': ['estrato', 'part23', 'mov_local', 'cruzado', 'alc_oviedo', 'nec_alc', 'blanco_alc', 'alc_bolivar'],
        'firmas': {
            'estrategico': {'estrato': 2.5, 'cruzado': 2.5, 'nec_alc': -2.9, 'alc_bolivar': -2.4, 'blanco_alc': -2},
            'alternativa': {'estrato': 1.3, 'part23': 1.3, 'alc_oviedo': 1.2, 'nec_alc': -1.2, 'alc_bolivar': -1.6},
            'decide':      {'part23': 1.5, 'mov_local': 1.4, 'alc_oviedo': 1.1, 'cruzado': -0.8},
            'cruce-sur':   {'estrato': -1.5, 'part23': -1.3, 'alc_oviedo': -1.9, 'blanco_alc': 1.2, 'cruzado': 0.9},
            'reparte':     {'estrato': -0.5, 'cruzado': 0.6, 'alc_oviedo': -0.8, 'alc_bolivar': 0.5},
            'alineada':    {'estrato': -0.8, 'part23': -0.7, 'nec_alc': 0.9, 'blanco_alc': 1.2, 'alc_bolivar': 1.0, 'cruzado': -0.6},
            'media-alineada': {'cruzado': -0.8, 'nec_alc': 0.7, 'alc_oviedo': 0.4},
            'tradicional': {},
        },
    },
}

# Nombre, color y una lectura de una línea por arquetipo. Los colores no
# repiten los de la familia política (rojo/azul) para que no se lean como bloque.
FICHA = {
    'concejo': {
        'gestion':    ('Barrio de gestión', '#c2410c', 'Una parte grande del voto va a candidaturas con base propia en la zona: el que se conoce, el que resuelve.'),
        'partido':    ('Periferia de partido', '#7c3aed', 'Se vota la lista, no la persona: alto voto a listas cerradas, electorado joven.'),
        'poco-voto':  ('Periferia que vota poco', '#64748b', 'Participación baja, y el voto local se moviliza menos que el nacional; muchos tarjetones nulos o sin marcar.'),
        'movilizada': ('Ciudadela movilizada', '#0d9488', 'La participación más alta de la ciudad y, sobre todo, sale a votar lo local más que el promedio.'),
        'figuras':    ('Norte de figuras', '#1d4ed8', 'Estrato alto, casi sin voto perdido y con redes personales de figuras conocidas.'),
        'opinion':    ('Norte de opinión', '#0e7490', 'Estrato alto, participa mucho y no vota listas cerradas: se decide por opinión, no por estructura.'),
        'sin-dueno':  ('Clase media sin dueño', '#be185d', 'Vota más que el promedio y casi nadie tiene el barrio amarrado: el voto está libre.'),
        'nombre':     ('Clase media de nombre', '#ca8a04', 'El grueso de Bogotá: vota a nombres conocidos dentro del electorado de su partido.'),
    },
    'alcaldia': {
        'estrategico': ('Norte estratégico', '#1d4ed8', 'Concentra el voto en el favorito aunque al Concejo vote otra cosa.'),
        'alternativa': ('Norte que busca alternativa', '#0e7490', 'Clase media alta que participa mucho y probó al candidato sin partido.'),
        'decide':      ('Clase media que decide', '#0d9488', 'Alta participación y voto que se mueve: fue de Claudia en 2019 y se partió entre Galán y Oviedo en 2023.'),
        'cruce-sur':   ('Sur popular de voto cruzado', '#c2410c', 'Al Concejo vota a las maquinarias de su barrio; a la Alcaldía, a otra cosa.'),
        'reparte':     ('Barrio popular que reparte el voto', '#9a3412', 'Vota distinto en los dos tarjetones, sin irse a los extremos.'),
        'alineada':    ('Periferia joven alineada', '#7c3aed', 'Vota a la Alcaldía como vota al Concejo; la contienda más repartida.'),
        'media-alineada': ('Clase media alineada', '#be185d', 'Clase media que vota a la Alcaldía igual que al Concejo.'),
        'tradicional': ('Clase media tradicional', '#ca8a04', 'Estable entre elecciones, mayoría holgada al ganador, participación media.'),
    },
}

ETIQ = {
    'estrato': 'Estrato medio', 'part23': 'Participación 2023', 'mov_local': 'Movilización local / nacional',
    'cerrada': 'Voto a listas cerradas', 'logo_abierta': 'Voto al logo en listas abiertas', 'arraigo': 'Voto con base propia (arraigo)',
    'desafeccion': 'Blanco + nulo + no marcado', 'cruzado': 'Voto cruzado Alcaldía–Concejo', 'alc_oviedo': 'Voto a Oviedo (sin lista al Concejo)',
    'nec_alc': 'Candidatos efectivos a la Alcaldía', 'blanco_alc': 'Voto en blanco a la Alcaldía', 'alc_bolivar': 'Voto a Bolívar',
}


def leer():
    filas = list(csv.DictReader(open(DIR / 'barrios.csv')))
    for f in filas:
        for k, v in f.items():
            if k in ('codigo', 'barrio', 'localidad', 'loc', 'alc_gana'):
                continue
            try:
                f[k] = float(v) if v not in ('', 'None') else None
            except ValueError:
                pass
    return filas


def nombrar(centros_z, vars_, firmas):
    slugs = list(firmas)
    M = np.zeros((len(centros_z), len(slugs)))
    for j, s in enumerate(slugs):
        w = np.array([firmas[s].get(v, 0.0) for v in vars_])
        for i, c in enumerate(centros_z):
            # coseno contra la firma; la firma vacía es «el del medio»: el centro más cercano a cero
            M[i, j] = (c @ w) / (np.linalg.norm(c) * np.linalg.norm(w) + 1e-9) if w.any() else -np.linalg.norm(c) / 3
    fila, col = linear_sum_assignment(-M)
    return {int(i): slugs[j] for i, j in zip(fila, col)}


def mezcla(Xz, centros, T):
    d2 = ((Xz[:, None, :] - centros[None, :, :]) ** 2).sum(axis=2)
    e = np.exp(-(d2 - d2.min(axis=1, keepdims=True)) / T)
    return e / e.sum(axis=1, keepdims=True)


def tipologia(filas, corp):
    cfg = CORP[corp]
    vars_ = cfg['vars']
    ok = [f for f in filas if all(f.get(v) is not None for v in vars_)]
    X = np.array([[f[v] for v in vars_] for f in ok])
    mu, sd = X.mean(axis=0), X.std(axis=0)
    Xz = (X - mu) / sd
    km = KMeans(cfg['k'], n_init=200, random_state=SEMILLA).fit(Xz)
    nom = nombrar(km.cluster_centers_, vars_, cfg['firmas'])
    centros = km.cluster_centers_
    orden = [nom[i] for i in range(cfg['k'])]
    # Temperatura de la mezcla: la mitad de la distancia² típica al centro propio.
    d2own = ((Xz - centros[km.labels_]) ** 2).sum(axis=1)
    T = float(np.median(d2own))
    MZ = mezcla(Xz, centros, T)

    # Confianza: re-muestreo de barrios, se reajusta y se mapea cada grupo nuevo
    # al centro de referencia más cercano.
    rng = np.random.default_rng(SEMILLA)
    igual = np.zeros(len(ok))
    for _ in range(R_BOOT):
        idx = rng.integers(0, len(ok), len(ok))
        kb = KMeans(cfg['k'], n_init=8, random_state=int(rng.integers(1e9))).fit(Xz[idx])
        cost = ((kb.cluster_centers_[:, None, :] - centros[None, :, :]) ** 2).sum(axis=2)
        r, c = linear_sum_assignment(cost)
        mapa = dict(zip(r, c))
        lab = np.array([mapa[l] for l in kb.predict(Xz)])
        igual += (lab == km.labels_)
    conf = igual / R_BOOT

    arq = {}
    for i in range(cfg['k']):
        s = nom[i]
        miembros = [f for f, l in zip(ok, km.labels_) if l == i]
        votos = sum(f['votantes23'] for f in miembros)
        cen = {v: float(np.average([f[v] for f in miembros], weights=[f['votantes23'] for f in miembros])) for v in vars_}
        z = {v: float(centros[i][j]) for j, v in enumerate(vars_)}
        ejemplos = sorted(miembros, key=lambda f: -f['votantes23'] * (conf[ok.index(f)] >= .8))[:8]
        nombre, color, lectura = FICHA[corp][s]
        arq[s] = {'nombre': nombre, 'color': color, 'lectura': lectura, 'barrios': len(miembros), 'votantes': int(votos),
                  'centro': cen, 'z': z, 'ejemplos': [f"{f['barrio']} ({f['localidad'].title()})" for f in ejemplos]}
    asign = {}
    for j, f in enumerate(ok):
        m = {orden[i]: round(float(MZ[j, i]), 3) for i in range(cfg['k'])}
        asign[f['codigo']] = {'dom': nom[int(km.labels_[j])], 'mez': m, 'conf': round(float(conf[j]), 2)}
    from sklearn.metrics import silhouette_score
    meta = {'vars': vars_, 'etiquetas': {v: ETIQ[v] for v in vars_}, 'media': dict(zip(vars_, mu.round(4).tolist())),
            'desv': dict(zip(vars_, sd.round(4).tolist())), 'k': cfg['k'], 'T': T,
            'silueta': round(float(silhouette_score(Xz, km.labels_)), 3), 'barrios': len(ok),
            'nitidos': int((conf >= .8).sum()), 'frontera': int((conf < .6).sum())}
    return arq, asign, meta


def main():
    filas = leer()
    out = {'v': '2026-10-19', 'ciudad': 'Bogotá', 'naturaleza': 'lectura observada 2023 (v1, 8 arquetipos)',
           'fuente': 'Registraduría: Alcaldía y Concejo 2019 y 2023, presidencial 2026 1V; censo electoral 2023 y 2026; estrato SDP/IDECA',
           'corporaciones': {}, 'barrios': {}}
    for corp in CORP:
        arq, asign, meta = tipologia(filas, corp)
        out['corporaciones'][corp] = {'meta': meta, 'arquetipos': arq}
        for cod, a in asign.items():
            out['barrios'].setdefault(cod, {})[corp] = a
        print(f"\n{corp.upper()}  silueta {meta['silueta']} · {meta['barrios']} barrios · nítidos {meta['nitidos']} · frontera {meta['frontera']}")
        for s, a in sorted(arq.items(), key=lambda x: -x[1]['votantes']):
            print(f"  {a['nombre']:30} {a['barrios']:4} barrios {a['votantes']:>9,} votantes | " +
                  ' · '.join(f"{v}={a['centro'][v]:.3f}" for v in meta['vars']))
            print('      ', ', '.join(a['ejemplos'][:5]))
    for f in filas:
        if f['codigo'] in out['barrios']:
            b = out['barrios'][f['codigo']]
            b.update({'nombre': f['barrio'], 'localidad': f['localidad'], 'estrato': f['estrato'],
                      'vars': {k: (round(f[k], 4) if isinstance(f[k], float) else f[k]) for k in
                               ('part23', 'part26', 'mov_local', 'logo', 'cerrada', 'logo_abierta', 'arraigo', 'sigue_lista',
                                'desafeccion', 'incumbente', 'top1_cand', 'cruzado', 'alc_galan', 'alc_oviedo', 'alc_bolivar',
                                'nec_alc', 'blanco_alc', 'vol_alc_19_23', 'vol_19_23', 'conc_izq', 'conc_ci', 'conc_c', 'conc_cd', 'conc_d',
                                'joven', 'mayor', 'votantes23', 'censo23')}})
    # cruce Concejo × Alcaldía
    cruce = {}
    for b in out['barrios'].values():
        if 'concejo' in b and 'alcaldia' in b:
            k = (b['concejo']['dom'], b['alcaldia']['dom'])
            cruce[k] = cruce.get(k, 0) + (b['vars']['votantes23'] or 0)
    out['cruce'] = [{'concejo': a, 'alcaldia': b, 'votantes': int(v)} for (a, b), v in sorted(cruce.items(), key=lambda x: -x[1])]
    (DIR / 'arquetipos-bogota.json').write_text(json.dumps(out, ensure_ascii=False))
    print('\nCRUCE (votantes):')
    for c in out['cruce'][:12]:
        print(f"  {FICHA['concejo'][c['concejo']][0]:28} × {FICHA['alcaldia'][c['alcaldia']][0]:30} {c['votantes']:>9,}")


if __name__ == '__main__':
    main()
