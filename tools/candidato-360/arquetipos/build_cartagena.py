#!/usr/bin/env python3
"""Cartografía emocional de Cartagena (Nury, sep-2026) → un JSON para el CRM.

Lee los tres Excel que entregó Nury y arma `arquetipos-cartagena.json`, que la
tarjeta 05 de candidato-360 cruza con los votos de la candidatura.

    python3 tools/candidato-360/arquetipos/build_cartagena.py [carpeta_insumos]

Por defecto busca los insumos en `Bases de datos/proyecto-dc/arquetipos-cartagena/insumos/`.

Qué NO es igual a Medellín, y por qué importa:
- Cartagena tiene OCHO arquetipos propios, no las cinco familias de Medellín.
  No se homologan: Nury construyó la taxonomía para esta ciudad.
- Cada barrio trae una MEZCLA de los ocho (porcentajes que suman 1), no solo el
  dominante. El frontend reparte los votos de la candidatura con esa mezcla.
- 2015 es el ancla; 2019 y 2023 son proyecciones retrospectivas y 2027 es
  simulación. El JSON lo lleva en `naturaleza` para que la página lo diga.

La llave del barrio es el nombre NORMALIZADO igual que en el frontend (sin
tildes, mayúsculas, solo A-Z0-9 y espacios). Se verificó: los 213 polígonos de
`candidato-360-data/cartagena-barrios/` casan con las filas de Nury; lo único
que sobra es «RURAL / INSULAR FUERA DE LOS BARRIOS URBANOS», que es un agregado
y se emite aparte.
"""
import glob
import json
import re
import sys
import unicodedata
import warnings
from pathlib import Path

import openpyxl

warnings.filterwarnings('ignore')
RAIZ = Path(__file__).resolve().parents[3]
INSUMOS = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'Bases de datos/proyecto-dc/arquetipos-cartagena/insumos'
SALIDA = RAIZ / 'Bases de datos/proyecto-dc/arquetipos-cartagena/arquetipos-cartagena.json'
AÑOS = ['2015', '2019', '2023', '2027']

# Orden de columnas de Nury. El slug es nuestro; el nombre es el de ella.
ARQ = [
    ('guardian-funcional', 'Guardián funcional'),
    ('gestor-vigilante', 'Gestor vigilante'),
    ('pragmatico-servicios', 'Pragmático de servicios'),
    ('protesta-resolutiva', 'Protesta resolutiva'),
    ('defensor-territorial', 'Defensor territorial'),
    ('guardian-insular', 'Guardián insular'),
    ('productivo-pragmatico', 'Productivo-pragmático'),
    ('mediador-comunitario', 'Mediador comunitario'),
]
SLUG = {n: s for s, n in ARQ}

# Lo que traen las tarjetas gráficas de Nury (lema, palancas emocionales 1-5 y
# edades), transcrito de las ocho piezas. El color es nuestro.
TARJETA = {
    'guardian-funcional': dict(color='#2563eb', lema='Resultados para una Cartagena que funciona', edades='30–55',
                               palancas=[['Confianza', 5], ['Exigencia cívica', 4], ['Vigilancia', 4]]),
    'gestor-vigilante': dict(color='#6d28d9', lema='Resultados con control ciudadano', edades='32–60',
                             palancas=[['Vigilancia', 5], ['Confianza selectiva', 4], ['Escepticismo', 4]]),
    'pragmatico-servicios': dict(color='#16a34a', lema='Soluciones que mejoran la vida diaria', edades='28–55',
                                 palancas=[['Urgencia práctica', 5], ['Esperanza cautelosa', 4], ['Fatiga de promesas', 4]]),
    'protesta-resolutiva': dict(color='#dc2626', lema='Malestar con búsqueda de salida', edades='18–40',
                                palancas=[['Indignación', 5], ['Frustración', 5], ['Esperanza', 3]]),
    'defensor-territorial': dict(color='#b45309', lema='Dignidad, reconocimiento y territorio', edades='25–60',
                                 palancas=[['Pertenencia', 5], ['Reivindicación', 5], ['Dignidad', 4]]),
    'guardian-insular': dict(color='#0891b2', lema='Islas visibles en la ciudad', edades='25–60',
                             palancas=[['Dignidad insular', 5], ['Reivindicación', 5], ['Esperanza práctica', 3]]),
    'productivo-pragmatico': dict(color='#ca8a04', lema='Trabajo, estabilidad y ciudad útil', edades='25–55',
                                  palancas=[['Incertidumbre económica', 5], ['Pragmatismo', 4], ['Estabilidad', 4]]),
    'mediador-comunitario': dict(color='#db2777', lema='La fuerza del barrio construye ciudad', edades='35–65',
                                 palancas=[['Reconocimiento', 5], ['Compromiso barrial', 4], ['Confianza relacional', 4]]),
}


# ── Sensibilidad por tema de agenda (para la escucha de medios y redes) ──
# Las llaves son los temas que clasifica candidato-360-saliencia.js (TEMAS).
# Sale de las «palancas temáticas (1-5)» que Nury escribió para cada arquetipo
# en el INTEGRADO (sección 5), traducidas a esos temas:
#   seguridad → seguridad · transparencia → corrupcion · empleo, turismo,
#   costo de vida → empleo · agua, servicios públicos, conectividad → servicios ·
#   movilidad, transporte (también marítimo), vías → movilidad ·
#   salud/educación → salud_educacion · cumplimiento, derechos territoriales,
#   presencia → participacion · identidad, juventud → cultura · ambiente → ambiente ·
#   vivienda, espacio público, gestión administrativa, POT → vivienda.
# Lo que Nury NO calificó se completa en 2-3 leyendo su ficha (rasgos, sesgos,
# cómo decide). `SENS_NURY` marca qué temas son literalmente de ella, para que la
# página pueda distinguir el dato de la inferencia. Si Nury corrige una palanca,
# se corrige aquí.
SENS = {
    # Seguridad 5 · Movilidad 5 · Servicios 4 · Turismo/espacio público 4 · Transparencia 3
    'guardian-funcional': dict(seguridad=5, movilidad=5, servicios=4, vivienda=4, corrupcion=3,
                               empleo=3, cultura=3, salud_educacion=2, participacion=2, ambiente=2),
    # Transparencia 5 · Gestión administrativa 5 · Seguridad 4 · Movilidad 4 · Servicios 4
    'gestor-vigilante': dict(corrupcion=5, vivienda=4, seguridad=4, movilidad=4, servicios=4,
                             participacion=3, empleo=3, salud_educacion=3, cultura=2, ambiente=2),
    # Servicios 5 · Seguridad 5 · Transporte 4 · Empleo 4 · Vivienda 4
    'pragmatico-servicios': dict(servicios=5, seguridad=5, movilidad=4, empleo=4, vivienda=4,
                                 salud_educacion=3, participacion=3, corrupcion=2, cultura=2, ambiente=2),
    # Empleo 5 · Seguridad 5 · Vivienda 4 · Transparencia 4 · Servicios 4
    'protesta-resolutiva': dict(empleo=5, seguridad=5, vivienda=4, corrupcion=4, servicios=4,
                                movilidad=3, salud_educacion=3, participacion=3, cultura=3, ambiente=2),
    # Agua 5 · Derechos territoriales 5 · Ambiente 5 · Empleo local 4 · Turismo inclusivo 4
    'defensor-territorial': dict(servicios=5, vivienda=5, ambiente=5, empleo=4, participacion=4,
                                 cultura=4, salud_educacion=3, seguridad=2, corrupcion=2, movilidad=2),
    # Agua 5 · Transporte marítimo 5 · Salud/educación 4 · Turismo 4 · Conectividad 4
    'guardian-insular': dict(servicios=5, movilidad=5, salud_educacion=4, empleo=4,
                             participacion=4, cultura=4, ambiente=3, corrupcion=3, vivienda=3, seguridad=2),
    # Empleo 5 · Movilidad 4 · Seguridad 4 · Ambiente 4 · Servicios 3
    'productivo-pragmatico': dict(empleo=5, movilidad=4, seguridad=4, ambiente=4, servicios=3,
                                  salud_educacion=3, vivienda=3, corrupcion=2, participacion=2, cultura=2),
    # Cumplimiento 5 · Seguridad 4 · Vías barriales 4 · Servicios 4 · Oportunidades juveniles 4
    'mediador-comunitario': dict(participacion=5, seguridad=4, movilidad=4, servicios=4, cultura=4,
                                 empleo=3, corrupcion=3, salud_educacion=3, vivienda=3, ambiente=2),
}
SENS_NURY = {
    'guardian-funcional': ['seguridad', 'movilidad', 'servicios', 'vivienda', 'corrupcion'],
    'gestor-vigilante': ['corrupcion', 'vivienda', 'seguridad', 'movilidad', 'servicios'],
    'pragmatico-servicios': ['servicios', 'seguridad', 'movilidad', 'empleo', 'vivienda'],
    'protesta-resolutiva': ['empleo', 'seguridad', 'vivienda', 'corrupcion', 'servicios'],
    'defensor-territorial': ['servicios', 'vivienda', 'ambiente', 'empleo'],
    'guardian-insular': ['servicios', 'movilidad', 'salud_educacion', 'empleo'],
    'productivo-pragmatico': ['empleo', 'movilidad', 'seguridad', 'ambiente', 'servicios'],
    'mediador-comunitario': ['participacion', 'seguridad', 'movilidad', 'servicios', 'cultura'],
}
TEMAS_VALIDOS = {'seguridad', 'corrupcion', 'empleo', 'servicios', 'movilidad', 'salud_educacion',
                 'participacion', 'cultura', 'ambiente', 'vivienda'}


def leer_integrado():
    """Las fichas 2027 de la sección 5 del INTEGRADO: perfil, cómo decide,
    sesgos, cinco palancas emocionales, cinco temáticas y barrios representativos."""
    import zipfile
    m = sorted(glob.glob(str(INSUMOS / 'INTEGRADO CARTAGENA.docx')))
    if not m:
        print('  ⚠ sin INTEGRADO: las fichas salen sin cómo decide ni palancas temáticas')
        return {}
    x = zipfile.ZipFile(m[0]).read('word/document.xml').decode('utf-8')
    ps = [p for p in (re.sub(r'<[^>]+>', '', q).strip() for q in re.findall(r'<w:p[ >].*?</w:p>', x, flags=re.S)) if p]
    campos = {'Cómo decide el voto': 'decide', 'Sesgos emocionales y cognitivos': 'sesgos',
              'Palancas emocionales (1–5)': 'palancas', 'Palancas temáticas (1–5)': 'tematicas',
              'Barrios más representativos': 'representativos', 'Edades dominantes': 'edades'}
    out = {}
    for i, p in enumerate(ps):
        mm = re.match(r'^5\.\d+\.\s+(.+)$', p)
        if not mm or mm.group(1) not in SLUG:
            continue
        slug, f = SLUG[mm.group(1)], {}
        sint = re.sub(r'^Síntesis del arquetipo\.\s*', '', ps[i + 1])
        corte = re.search(r'\s(?!Cartagena\b)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b', sint[1:])
        f['perfil'] = sint[corte.start() + 2:].strip() if corte else ''
        for j in range(i + 2, min(i + 40, len(ps) - 1)):
            if re.match(r'^5\.\d+\.', ps[j]):
                break
            if ps[j] in campos:
                f[campos[ps[j]]] = ps[j + 1]
        for k in ('palancas', 'tematicas'):
            f[k] = [[n.strip(), int(v)] for n, v in re.findall(r'([^·]+?)\s+(\d)/5', f.get(k, ''))]
        f['edades'] = re.sub(r'\s*años$', '', f.get('edades', ''))
        out[slug] = f
    return out


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z0-9 ]+', ' ', s)).strip().upper()


def filas(ws, desde):
    return [r for r in list(ws.iter_rows(values_only=True))[desde:] if r and r[0]]


def r4(x):
    return round(float(x), 3) if isinstance(x, (int, float)) else None


def abrir(patron):
    m = sorted(glob.glob(str(INSUMOS / patron)))
    if not m:
        sys.exit(f'No encuentro {patron} en {INSUMOS}')
    return openpyxl.load_workbook(m[0], read_only=True, data_only=True)


def main():
    carto = abrir('CARTOGRAF*EMOCIONAL CARTAGENA.xlsx')
    simu = abrir('SIMULACI*ARQUETIPOS 2027.xlsx')
    sens = abrir('SENSIBILIDAD POBLACIONAL CARTAGENA.xlsx')

    # ── fichas ──
    familias = {}
    for r in filas(carto['03_Fichas_Arquetipos'], 4):
        slug = SLUG.get(r[0])
        if not slug:
            continue
        familias[slug] = dict(nombre=r[0], familia_fuente=r[1], emocion=r[2], rasgos=r[3],
                              sube=r[4], baja=r[5], **TARJETA[slug])
    assert len(familias) == 8, familias.keys()
    integ = leer_integrado()
    for slug, f in familias.items():
        extra = integ.get(slug, {})
        if extra.get('palancas'):
            f['palancas'] = extra['palancas']      # las cinco del informe; la tarjeta muestra tres
        for k in ('perfil', 'decide', 'sesgos', 'tematicas', 'representativos'):
            if extra.get(k):
                f[k] = extra[k]
        if extra.get('edades') and extra['edades'] != f['edades']:
            print(f'  ⚠ {slug}: edades de la tarjeta {f["edades"]} ≠ informe {extra["edades"]}')
        assert set(SENS[slug]) <= TEMAS_VALIDOS, slug
        f['sens'] = SENS[slug]
        f['sens_nury'] = SENS_NURY[slug]
    print(f'  fichas con informe integrado: {sum(1 for f in familias.values() if f.get("decide"))} de 8')

    # ── ciudad ──
    ciudad = {a: {} for a in AÑOS}
    dominantes = {a: {} for a in AÑOS}
    for r in filas(carto['05_Dashboard'], 4):
        slug = SLUG.get(r[0])
        if not slug:
            continue
        for i, a in enumerate(AÑOS):
            ciudad[a][slug] = r4(r[1 + i])
            dominantes[a][slug] = int(r[8 + i] or 0)

    # ── volumen por año (votos válidos territoriales que Nury usó) ──
    vol = {}
    for hoja, año in [('07_Distribucion_2015', '2015'), ('08_Proyeccion_2019', '2019'),
                      ('09_Proyeccion_2023', '2023'), ('10_Simulacion_2027', '2027')]:
        for r in filas(carto[hoja], 4):
            vol.setdefault(norm(r[0]), {})[año] = round(float(r[2] or 0))

    # ── volumen 2027 (escenario base) y sensibilidad ──
    eq27 = {norm(r[0]): round(float(r[12] or 0)) for r in filas(simu['03_Proyeccion_2027'], 1)}
    sensi = {}
    for r in filas(sens['01_Sensibilidad_Barrio'], 1):
        sensi[norm(r[0])] = dict(indice=r4(r[13]), nivel=r[14], tendencia=r[15], lectura=r[16])

    # ── barrios ──
    hdr = list(carto['01_Cartografia_Emocional'].iter_rows(values_only=True))[3]
    col = {h: i for i, h in enumerate(hdr)}
    barrios, agregados = {}, {}
    for r in filas(carto['01_Cartografia_Emocional'], 4):
        k = norm(r[0])
        mezcla = {}
        for a in AÑOS:
            mezcla[a] = {s: r4(r[col[f'% {a} {n}']]) for s, n in ARQ}
            tot = sum(mezcla[a].values())
            assert abs(tot - 1) < 0.01, (k, a, tot)
        b = dict(
            nombre=r[0], localidad=r[1], tipo=r[2], confianza=r[3],
            emocion={'2015': r[col['Emoción 2015']], '2019': r[col['Emoción 2019']], '2023': r[col['Emoción 2023']]},
            dominante={a: SLUG.get(r[col[f'Dominante {a}']]) for a in AÑOS},
            mezcla=mezcla,
            volatilidad=dict(media=r4(r[col['Volatilidad media']]), nivel=r[col['Nivel volatilidad']],
                             cambios=int(r[col['Cambios dominante']] or 0)),
            volumen={**vol.get(k, {}), '2027_base': eq27.get(k)},
            sensibilidad=sensi.get(k),
        )
        (agregados if r[2] == 'Agregado sin barrio' else barrios)[k] = b

    # ── verificación contra la capa de barrios del CRM ──
    capa = set()
    for f in glob.glob(str(RAIZ / 'candidato-360-data/cartagena-barrios/*.js')):
        t = open(f, encoding='utf-8').read()
        j = json.loads(t[t.index('={"type"') + 1:].rstrip(';\n'))
        capa.update(norm(ft['properties']['barrio']) for ft in j['features'])
    faltan = sorted(capa - set(barrios))
    sobran = sorted(set(barrios) - capa)
    print(f'barrios Nury {len(barrios)} · capa {len(capa)} · capa sin Nury {len(faltan)} · Nury sin capa {len(sobran)}')
    if faltan:
        print('  ⚠ sin arquetipo:', faltan)

    out = dict(
        v='2026-09-27',
        ciudad='Cartagena',
        fuente='Nury Astrid · cartografía emocional de Cartagena 2015-2027 (sep-2026)',
        naturaleza={'2015': 'ancla histórica', '2019': 'proyección retrospectiva',
                    '2023': 'proyección retrospectiva', '2027': 'simulación'},
        orden=[s for s, _ in ARQ],
        familias=familias,
        ciudad_share=ciudad,
        dominantes=dominantes,
        barrios=barrios,
        agregados=agregados,
        advertencia='Los arquetipos son inferencias territoriales agregadas: dicen en qué clase de barrio '
                    'está un voto, no qué siente cada persona ni por quién va a votar.',
    )
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'→ {SALIDA} ({SALIDA.stat().st_size // 1024} KB)')
    for a in AÑOS:
        top = max(ciudad[a].items(), key=lambda x: x[1])
        print(f'  {a}: más pesado {familias[top[0]]["nombre"]} {top[1]*100:.1f} %')


if __name__ == '__main__':
    main()
