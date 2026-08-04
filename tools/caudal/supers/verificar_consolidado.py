#!/usr/bin/env python3
"""Caudal · pilar Regulatorio — ¿el consolidado que está por subir está completo?

Existe por una razón concreta: `harvest_supers.py normalize` consolida las DOCE
fuentes del pilar leyendo `raw/{slug}.json`, y **si un raw falta, lo salta en
silencio**. Eso estaba bien mientras el pilar se regeneraba a mano y alguien
miraba la salida. Desde que ANLA entró al cron, `normalize` + `build_s3` corren
desatendidos 2x/día: un `raw/invima.json` borrado, truncado o a medio escribir
haría que la corrida subiera a producción un `sanciones.jsonl` sin INVIMA, y
nadie se enteraría hasta que un cliente buscara y no encontrara.

Este chequeo va ENTRE `build_s3` y el `aws s3 cp`. Si falla, la subida se omite
y en S3 queda el archivo bueno de ayer: perder un refresco es barato, publicar
un pilar mutilado no.

Qué mira, en orden de cuán probable es que se rompa:

  1. **integridad del JSONL** — que las 61k líneas parseen. Un `aws s3 cp` de un
     archivo cortado a la mitad deja un objeto válido para S3 y roto para la
     Lambda; mejor detectarlo acá.
  2. **piso por fuente** — cada fuente contra el mínimo de abajo. Son registros
     administrativos acumulativos: encogen solo si algo se rompió río arriba.
  3. **piso del total** — la red por si una fuente nueva entra sin piso propio.
  4. **coherencia con los raw** — si `raw/{slug}.json` existe en disco, esa
     fuente TIENE que aparecer en el consolidado. Cubre el caso de un raw que
     quedó bien pero que `normalize` no leyó.

Los pisos van acá y no en un archivo de estado a propósito: viven en git, se
revisan en un diff y sobreviven a un disco nuevo. Están al ~90% de lo medido en
ago-2026, que deja aire para mejoras de dedup sin volverse un adorno.

Uso:
    python3 tools/caudal/supers/verificar_consolidado.py          # rc 0 ok · 1 falla
    python3 tools/caudal/supers/verificar_consolidado.py --verboso
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SUP = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = SUP / 'raw'
S3 = SUP / 'dist' / 's3'

# Piso por fuente ≈ 90% de lo medido el 2026-08-03. Si una baja de acá, la
# subida se cancela y hay que mirar su raw antes que tocar este número.
#   (el valor medido va al lado para que se vea cuánto aire hay)
PISOS = {
    'anla-gaceta':         48_000,   # 54.103 · Gaceta Ambiental
    'invima':               3_300,   # 3.690
    'secop1-multas':        1_500,   # 1.707
    'sfc-mercado-valores':    720,   # 805
    'secop2-multas':          490,   # 544
    'junta-contadores':        76,   # 85
    'sic':                     68,   # 76
    'contraloria-fiscal':      54,   # 60
    'supertransporte':         32,   # 36
    'supersalud-registro':     27,   # 30
    'supersalud':              14,   # 16
}
# `mintrabajo-territorial` queda fuera adrede: su dataset es AGREGADO (conteos
# por territorial, no por entidad) y `normalize` no lo mete al consolidado.
FUERA = {'mintrabajo-territorial'}

PISO_TOTAL = 55_000          # 61.146 medidos
PISO_SANCIONES = 6_500       # 7.229 medidas (es lo que ve el cliente por defecto)


def main():
    verboso = '--verboso' in sys.argv
    quejas = []

    src = S3 / 'sanciones.jsonl'
    if not src.exists():
        print(f'! no existe {src.relative_to(REPO)} — ¿corrió build_s3?')
        return 1

    # 1 · integridad. split('\n') y no splitlines(): hay textos con U+0085 que
    # splitlines() trataría como salto de línea y partirían un registro bueno
    # (ver el comentario largo en build_s3.py).
    recs, malas = [], 0
    for i, ln in enumerate(src.read_text(encoding='utf-8').split('\n'), 1):
        if not ln.strip():
            continue
        try:
            recs.append(json.loads(ln))
        except json.JSONDecodeError:
            malas += 1
            if malas <= 3:
                quejas.append(f'línea {i} no parsea como JSON (archivo truncado o corrupto)')
    if malas > 3:
        quejas.append(f'... y {malas - 3} líneas rotas más')

    por_fuente = Counter(r.get('fuente', '') for r in recs)
    n_sanc = sum(1 for r in recs if r.get('tipo_acto') == 'sancion')

    # 2 · piso por fuente
    for slug, piso in sorted(PISOS.items(), key=lambda kv: -kv[1]):
        n = por_fuente.get(slug, 0)
        if n == 0:
            quejas.append(f'{slug}: DESAPARECIÓ del consolidado (esperaba ≥{piso:,})')
        elif n < piso:
            quejas.append(f'{slug}: {n:,} actos, por debajo del piso {piso:,}')

    # 3 · pisos globales
    if len(recs) < PISO_TOTAL:
        quejas.append(f'total {len(recs):,} actos, por debajo del piso {PISO_TOTAL:,}')
    if n_sanc < PISO_SANCIONES:
        quejas.append(f'{n_sanc:,} sanciones, por debajo del piso {PISO_SANCIONES:,}')

    # 4 · todo raw en disco tiene que haber llegado al consolidado
    for f in sorted(RAW.glob('*.json')):
        slug = f.stem
        if slug in FUERA or slug.endswith('-memo'):
            continue        # -memo es caché interno de harvest_anla, no una fuente
        if slug not in por_fuente:
            quejas.append(f'{slug}: hay raw en disco pero NO salió en el consolidado')

    nuevas = sorted(set(por_fuente) - set(PISOS) - {''})
    if nuevas:
        print(f'· fuentes sin piso declarado (agregar a PISOS): {", ".join(nuevas)}')

    if verboso or quejas:
        print(f'· {len(recs):,} actos · {n_sanc:,} sanciones · {len(por_fuente)} fuentes')
        for slug, n in por_fuente.most_common():
            piso = PISOS.get(slug)
            marca = '' if piso is None else ('  ok' if n >= piso else '  ← BAJO')
            print(f'    {slug:24s} {n:>7,}' + (f'  (piso {piso:,}){marca}' if piso else ''))

    if quejas:
        print('\n! el consolidado NO está para subir:')
        for q in quejas:
            print(f'    · {q}')
        print('\n  Antes de tocar los pisos: mirar si el raw de esa fuente sigue en')
        print(f'  {RAW.relative_to(REPO)} y si `normalize` la listó.')
        return 1

    print(f'consolidado ok: {len(recs):,} actos · {n_sanc:,} sanciones · '
          f'{len(por_fuente)} fuentes, ninguna por debajo de su piso')
    return 0


if __name__ == '__main__':
    sys.exit(main())
