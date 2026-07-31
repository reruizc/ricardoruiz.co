#!/usr/bin/env python3
"""
analiza_duplicados.py — mide (NO modifica nada) cuántas personas del registro de
candidatos están partidas en varias fichas por variantes del nombre.

El caso disparador: "GUSTAVO PETRO" y "GUSTAVO FRANCISCO PETRO URREGO" son la
misma persona, pero `agruparPersonas` de analisis-candidato.html colapsa por
nombre EXACTO normalizado, así que quedan como dos fichas.

⚠️ HALLAZGO CENTRAL (por eso el script separa en dos grupos): la regla ingenua
"el nombre corto es subsecuencia del largo" produce FALSOS POSITIVOS graves,
porque en Colombia el apellido de una persona puede ser el SEGUNDO apellido de
otra:
    GUSTAVO PETRO      ⊄ GUSTAVO MIGUEL OSORIO PETRO   (personas distintas)
    RODOLFO HERNANDEZ  ⊄ RODOLFO ENRIQUE MORALES HERNANDEZ
    LUIS EDUARDO GARZON⊄ LUIS EDUARDO PINTO GARZON
Fusionar por esa regla habría pegado a Petro con un concejal de 253 votos.

Lo que SÍ distingue a la misma persona es que coincidan **los DOS apellidos** y
que el largo solo agregue nombres de pila en la mitad:
    ADALBERTO [EMILIO] LLINAS DELGADO · ROGER [JOSE] CARRILLO CAMPO
    SOLEDAD [MAGDALENA] TAMAYO TAMAYO · ROCIO [DE JESUS] PINEDA GARCIA

Grupos que reporta:
  A · APELLIDOS COMPLETOS  — mismo 1er nombre + los MISMOS 2 apellidos finales,
      el largo solo intercala nombres de pila. Alta precisión → fusionable.
  B · APELLIDO FALTANTE    — el corto soltó el último apellido (caso Petro:
      corto termina en PETRO, largo lo tiene como penúltimo). Es donde viven
      los personajes conocidos, pero también donde el apellido puede coincidir
      por azar → NO fusionar solo; sirve como lista de revisión.
Dentro de cada grupo se marca AMBIGUO si más de un nombre largo compite.

Uso:  python3 tools/analisis-candidato/analiza_duplicados.py [--csv salida.csv]
"""
import csv, json, os, sys, unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(ROOT, 'Bases de datos')
SC = os.environ.get('IDX_DIR', '/private/tmp/claude-501/'
    '-Users-ricardoruiz-ricardoruiz-co/9350b593-0e4b-4382-9e4e-6881b758fa4d/scratchpad/idx')

FUENTES_LOCALES = [
    ('asam2011', 'output_asamblea_2011/index-asamblea-2011.json'),
    ('asam2015', 'output_asamblea_2015/index-asamblea-2015.json'),
    ('asam2019', 'output_asamblea_2019/index-asamblea-2019.json'),
    ('conc2011', 'output_concejo_2011/index-concejo-2011.json'),
    ('conc2015', 'output_concejo_2015/index-concejo-2015.json'),
    ('conc2019', 'output_concejo_2019/index-concejo-2019.json'),
    ('jal2011',  'output_jal_2011/index-jal-2011.json'),
    ('jal2015',  'output_jal_2015/index-jal-2015.json'),
    ('jal2019',  'output_jal_2019/index-jal-2019.json'),
    ('pres2010', 'output_pres_2010/index-pres-2010.json'),
    ('pres2014', 'output_pres_2014/index-pres-2014.json'),
    ('pres2018', 'output_pres_2018/index-pres-2018.json'),
    ('pres2022', 'output_pres_2022/index-pres-2022.json'),
    ('consu2022','output_consu_2022/index-consu-2022.json'),
]
FUENTES_S3 = [
    ('endoso',   'endoso_index.json'),
    ('con2014',  'congreso-2014_index-congreso-2014.json'),
    ('con2018',  'congreso-2018_index-congreso-2018.json'),
    ('con2022',  'congreso-2022_index-congreso-2022.json'),
    ('asamblea', 'asamblea-2023_index-asamblea-2023.json'),
    ('concejo',  'concejo-2023_index-concejo-2023.json'),
    ('jal',      'jal-2023_index-jal-2023.json'),
]

PARTIDO_RE = ('PARTIDO', 'MOVIMIENTO', 'COALICION', 'ALIANZA', 'LISTA', 'PACTO',
              'GSC', 'GRUPO', 'CONSULTA', 'VOTO', 'TARJETON', 'CANDIDATO')
# Partículas que no cuentan como apellido propio ("de", "del", "de la"…).
PARTICULAS = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'DA', 'DI', 'VAN', 'SAN'}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return ' '.join(s.upper().split())


def es_partido(nombre, partido):
    n = norm(nombre)
    if not n:
        return True
    if n == norm(partido):
        return True
    return n.split()[0] in PARTIDO_RE


def sin_particulas(toks):
    """Quita partículas para comparar apellidos: CASADO DE LOPEZ ≈ CASADO LOPEZ."""
    return [t for t in toks if t not in PARTICULAS]


def es_subsecuencia(cortos, largos):
    it = iter(largos)
    return all(t in it for t in cortos)


def cargar():
    reg = []
    for etq, rel in FUENTES_LOCALES:
        p = os.path.join(BD, rel)
        if not os.path.exists(p):
            print(f'  · falta {rel} (se omite)', file=sys.stderr); continue
        for c in json.load(open(p, encoding='utf-8')).get('candidatos', []):
            reg.append((etq, c))
    for etq, fn in FUENTES_S3:
        p = os.path.join(SC, fn)
        if not os.path.exists(p):
            print(f'  · falta {fn} (se omite)', file=sys.stderr); continue
        d = json.load(open(p, encoding='utf-8'))
        for c in (d if isinstance(d, list) else d.get('candidatos', [])):
            reg.append((etq, c))
    return reg


def main():
    reg = cargar()
    por_nombre = defaultdict(list)
    for etq, c in reg:
        nom = c.get('nombre') or ''
        if es_partido(nom, c.get('partido', '')):
            continue
        n = norm(nom)
        if len(n.split()) < 2:
            continue
        por_nombre[n].append((etq, c))

    print(f'{len(reg):,} candidaturas · {len(por_nombre):,} nombres distintos (sin partidos)\n')

    nombres = list(por_nombre)
    # Índices para no comparar todo contra todo.
    por_ape2 = defaultdict(list)   # (1er nombre, 2 apellidos finales) → nombres
    por_penul = defaultdict(list)  # (1er nombre, PENÚLTIMO token)     → nombres largos
    for n in nombres:
        t = sin_particulas(n.split())
        if len(t) < 2:
            continue
        if len(t) >= 3:
            por_ape2[(t[0], t[-2], t[-1])].append(n)
            por_penul[(t[0], t[-2])].append(n)

    grupoA, grupoB = defaultdict(list), defaultdict(list)
    for n in nombres:
        t = sin_particulas(n.split())
        if len(t) < 2:
            continue
        # A · mismo 1er nombre y MISMOS 2 apellidos; el largo solo intercala nombres
        if len(t) >= 3:
            for m in por_ape2[(t[0], t[-2], t[-1])]:
                tm = sin_particulas(m.split())
                if len(tm) > len(t) and es_subsecuencia(t, tm):
                    grupoA[n].append(m)
        # B · el corto soltó el último apellido: su último token es el PENÚLTIMO del largo
        for m in por_penul[(t[0], t[-1])]:
            tm = sin_particulas(m.split())
            if len(tm) > len(t) and es_subsecuencia(t, tm):
                grupoB[n].append(m)

    def deps(nom):
        return {norm(c.get('circunscripcion', '')).split('(')[0].strip()
                for _, c in por_nombre[nom]}

    def partidos(nom):
        return {norm(c.get('partido', '')) for _, c in por_nombre[nom]}

    def votos(nom):
        return sum(c.get('votos', 0) for _, c in por_nombre[nom])

    def resumen(g, etiqueta):
        uni = {k: v[0] for k, v in g.items() if len(v) == 1}
        amb = {k: v for k, v in g.items() if len(v) > 1}
        con_dep = [k for k, v in uni.items() if deps(k) & deps(v)]
        con_par = [k for k, v in uni.items() if partidos(k) & partidos(v)]
        ambos = [k for k in uni if (deps(k) & deps(uni[k])) and (partidos(k) & partidos(uni[k]))]
        print(f'{etiqueta}')
        print(f'   un solo candidato largo : {len(uni):,}')
        print(f'       + mismo departamento: {len(con_dep):,}')
        print(f'       + mismo partido     : {len(con_par):,}')
        print(f'       + AMBOS             : {len(ambos):,}')
        print(f'   ambiguos (varios largos): {len(amb):,}\n')
        return uni, amb

    uniA, ambA = resumen(grupoA, 'A · APELLIDOS COMPLETOS (mismo 1er nombre + los 2 apellidos)')
    uniB, ambB = resumen(grupoB, 'B · APELLIDO FALTANTE (el corto soltó el último apellido)')

    print('=== A · 20 ejemplos por votos (candidatos a fusión automática) ===')
    for k in sorted(uniA, key=lambda k: -(votos(k) + votos(uniA[k])))[:20]:
        d = 'dep✓' if deps(k) & deps(uniA[k]) else 'dep✗'
        p = 'par✓' if partidos(k) & partidos(uniA[k]) else 'par✗'
        print(f'  [{d} {p}] {k} ({votos(k):,})  ⊂  {uniA[k]} ({votos(uniA[k]):,})')

    print('\n=== B · 20 ejemplos por votos (lista de revisión, NO automática) ===')
    for k in sorted(uniB, key=lambda k: -(votos(k) + votos(uniB[k])))[:20]:
        d = 'dep✓' if deps(k) & deps(uniB[k]) else 'dep✗'
        p = 'par✓' if partidos(k) & partidos(uniB[k]) else 'par✗'
        print(f'  [{d} {p}] {k} ({votos(k):,})  ⊂  {uniB[k]} ({votos(uniB[k]):,})')

    if '--csv' in sys.argv:
        out = sys.argv[sys.argv.index('--csv') + 1]
        with open(out, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['grupo', 'estado', 'nombre_corto', 'votos_corto', 'nombre_largo',
                        'votos_largo', 'mismo_depto', 'mismo_partido', 'n_opciones'])
            for g, uni, amb in (('A', uniA, ambA), ('B', uniB, ambB)):
                for k, v in sorted(uni.items(), key=lambda kv: -(votos(kv[0]) + votos(kv[1]))):
                    w.writerow([g, 'UNICO', k, votos(k), v, votos(v),
                                int(bool(deps(k) & deps(v))), int(bool(partidos(k) & partidos(v))), 1])
                for k, vs in amb.items():
                    for v in vs:
                        w.writerow([g, 'AMBIGUO', k, votos(k), v, votos(v),
                                    int(bool(deps(k) & deps(v))), int(bool(partidos(k) & partidos(v))), len(vs)])
        print(f'\n→ CSV: {out}')


if __name__ == '__main__':
    main()
