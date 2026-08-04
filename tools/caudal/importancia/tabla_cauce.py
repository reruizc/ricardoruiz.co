#!/usr/bin/env python3
"""
Caudal · Importancia — la hoja del top-10 político para la reunión con Cauce.

    python3 tools/caudal/importancia/tabla_cauce.py

POR QUÉ EXISTE. El eje 3 no se puede validar contra un desenlace: no existe un
registro de qué proyecto fue bandera de quién. La única verdad disponible es el
juicio de alguien que conoce el Congreso, así que la validación ES la reunión —
Diego y Pablo miran el top-10 y dicen dónde no les cuadra.

Por eso esta hoja no es un volcado: es una pieza para leer en voz alta, de una
página, con una línea por proyecto que dice POR QUÉ está ahí, y una columna
vacía para marcar el desacuerdo. Lo que salga de ahí se convierte en un ajuste
a POLITICO_PESOS, que es editable justamente para eso.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ejes as E          # noqa: E402
import evaluar as EV      # noqa: E402

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'reportes', 'top10-politico-cauce.md')
TOP = 10


def _corta(s, n):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _titulo_legible(t):
    """Los títulos arrancan con 60 caracteres de fórmula notarial idéntica en
    todos. Quitarla es lo que hace que la tabla se lea de un vistazo. Y el
    registro escribe unos en mayúscula sostenida y otros no: se unifican, si no
    la tabla parece dos tablas."""
    t = ' '.join((t or '').split())
    for pre in ('POR MEDIO DE LA CUAL SE ', 'POR MEDIO DEL CUAL SE ',
                'POR MEDIO DE LA CUAL ', 'POR MEDIO DEL CUAL ',
                'POR LA CUAL SE ', 'POR EL CUAL SE ', 'MEDIANTE LA CUAL SE ',
                'POR LA CUAL ', 'POR EL CUAL ', 'POR MEDIO DE/CUAL SE '):
        if t.upper().startswith(pre):
            t = t[len(pre):]
            break
    letras = [c for c in t if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.85:
        t = t.lower()
        # los nombres propios que el pase a minúscula se lleva por delante
        for w, w2 in (('colombia', 'Colombia'), ('constitución', 'Constitución'),
                      ('estado', 'Estado'), ('congreso', 'Congreso'),
                      ('nación', 'Nación'), ('ley 5', 'Ley 5'),
                      ('sena', 'SENA'), ('dian', 'DIAN'), ('icbf', 'ICBF')):
            t = t.replace(w, w2)
    return t[:1].upper() + t[1:]


def _veces(n):
    return 'una vez' if n == 1 else f'{n} veces'


def _bancada(it):
    coh = it['politico'].get('cohesion') or {}
    if coh.get('calculable'):
        return coh.get('partido_dominante')
    if it['politico']['componentes'].get('agenda_ejecutivo', 0) > 0:
        return 'Gobierno'
    return None


def _razon(it):
    """La señal política de este proyecto, en una línea de lenguaje llano."""
    po = it['politico']
    comp = po['componentes']
    coh = po.get('cohesion') or {}
    partes = []
    if comp.get('agenda_ejecutivo', 0) > 0:
        partes.append('lo radica el Gobierno')
    nf = po.get('n_firmantes') or 0
    if nf >= 10:
        if coh.get('calculable') and coh.get('valor', 0) >= 0.7:
            partes.append(f'{nf} firmas y {coh["partido_dominante"].title()} '
                          f'cierra filas')
        elif coh.get('calculable'):
            partes.append(f'{nf} firmas, {coh["partidos_distintos"]} partidos')
        else:
            partes.append(f'{nf} firmas')
    prev = po.get('radicaciones_previas') or 0
    if prev:
        partes.append(f'ya se radicó {_veces(prev)} y no pasó')
    if comp.get('rango_normativo', 0) >= 10:
        partes.append('toca la Constitución')
    if not partes:
        partes.append('sin señales fuertes de bloque')
    return '; '.join(partes)


def main():
    items, _viva = EV.evaluar_todo()
    res = E.ordenar([dict(x) for x in items], 'politico')
    top = res['ranking'][:TOP]

    L = []
    L.append('# Caudal · ¿qué se está jugando en el Congreso?')
    L.append('')
    L.append('**Top 10 por carga política, legislatura 2026-2027.** Este lente '
             'ordena por lo que un proyecto SIGNIFICA, no por lo que va a pasar: '
             'un proyecto puede ser central y no tener ninguna posibilidad, y esa '
             'es justamente la lectura que interesa acá.')
    L.append('')
    L.append('> **Lo que les pedimos:** marquen la última columna donde no les '
             'cuadre. El eje político es una heurística declarada — no hay forma '
             'de validarla contra un desenlace, porque no existe registro de qué '
             'fue bandera de quién. Su desacuerdo es la validación, y se traduce '
             'directo en un ajuste de los pesos.')
    L.append('')
    L.append('| # | Proyecto | Por qué está acá | ¿Pasa? | ¿Les cuadra? |')
    L.append('|---|---|---|---|---|')
    for i, it in enumerate(top, 1):
        num = it['numero'] or '—'
        tit = _corta(_titulo_legible(it['titulo']), 78)
        banda = it['avance']['banda']['banda']
        L.append(f'| {i} | **{num}** · {tit} | {_razon(it)} | {banda} | |')
    L.append('')

    # --- lo que el propio ranking deja ver y conviene poner sobre la mesa ---
    fuera_pacto = [it for it in res['ranking']
                   if (_bancada(it) or '') and 'PACTO' not in (_bancada(it) or '')]
    n_pacto_top = sum(1 for it in top if 'PACTO' in (_bancada(it) or ''))
    if n_pacto_top >= 8 and fuera_pacto:
        cuantos = ('los 10' if n_pacto_top == 10 else f'{n_pacto_top} de los 10')
        L.append(f'### Lo primero que hay que discutir: {cuantos} son del Pacto')
        L.append('')
        L.append('No es un accidente del corte: en el top 20 son 18. Y tiene dos '
                 'lecturas opuestas, las dos plausibles, que necesitamos que '
                 'ustedes resuelvan.')
        L.append('')
        L.append('1. **Es el Congreso, no el modelo.** El Pacto es la única '
                 'bancada que radica en bloques de 30 a 55 firmas; las demás '
                 'radican de a uno o dos. Si firmar en bloque ES la forma de '
                 'poner una bandera, el ranking está leyendo bien.')
        L.append('2. **Es un punto ciego.** La firma colectiva pesa 28 de 100, '
                 'y si la oposición hace política de otra manera —control '
                 'político, debates, proyectos individuales— el eje no la ve. '
                 'En ese caso el peso está mal puesto y hay que bajarlo.')
        L.append('')
        L.append('Para que puedan compararlo, lo más alto de fuera del Pacto:')
        L.append('')
        L.append('| Puesto real | Proyecto | Bancada | Por qué |')
        L.append('|---|---|---|---|')
        pos = {id(it): i for i, it in enumerate(res['ranking'], 1)}
        for it in fuera_pacto[:5]:
            L.append(f'| #{pos[id(it)]} | {_corta(_titulo_legible(it["titulo"]), 58)} '
                     f'| {(_bancada(it) or "").title()} | {_razon(it)} |')
        L.append('')

    # --- pie técnico, corto a propósito ---
    L.append('---')
    L.append('')
    L.append('### Cómo leer las columnas')
    L.append('')
    L.append('**«Por qué está acá»** — las señales que suman al peso político: '
             'cuántos firman, si son de una sola bancada, cuántas veces han '
             'vuelto a radicar lo mismo sin que pase, si lo radica el Gobierno y '
             'si cambia la Constitución.')
    L.append('')
    L.append('**«¿Pasa?»** — banda de probabilidad de llegar a ley, de un modelo '
             'calibrado contra los 13.660 proyectos de 1990 a 2026 y validado '
             'sobre los años que no vio (AUC 0,745). Va en bandas y no en '
             'porcentaje porque el modelo ordena mejor de lo que calibra. '
             'Históricamente llegó a ley el 51,9% de los que quedan en *alto*, '
             'el 28,6% en *medio*, el 15,2% en *bajo* y el 5,6% en *casi nulo*.')
    L.append('')
    L.append('**Las dos columnas son independientes a propósito.** El fracking '
             'está alto en política y bajo en probabilidad, y las dos cosas son '
             'ciertas al tiempo: es basura para un gremio que gestiona riesgo '
             'regulatorio y es de lo más informativo que hay para leer al bloque '
             'que lo sostiene.')
    L.append('')
    n_no_calc = sum(1 for it in items
                    if not (it['politico'].get('cohesion') or {}).get('calculable'))
    L.append(f'*Cobertura: de los {len(items)} proyectos de la legislatura, en '
             f'{len(items) - n_no_calc} se pudo calcular la cohesión de bancada. '
             f'En los otros {n_no_calc} no se conoce el partido de suficientes '
             f'firmantes; ese componente se excluye del cálculo en vez de contar '
             f'como cero, para no confundir «no se pudo medir» con «firma '
             f'transversal».*')
    L.append('')

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print(f'\n→ {SALIDA}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
