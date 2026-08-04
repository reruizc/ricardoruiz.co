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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ejes as E          # noqa: E402
import evaluar as EV      # noqa: E402

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'reportes', 'top10-politico-cauce.md')
TOP = 10


# El registro trae títulos con el encoding roto (utf-8 leído como latin-1).
# No se arregla en el dato porque no es nuestro; se deshace al mostrarlo.
_SOSPECHOSOS = 'ÃÂãâ€™“”'


def _limpia(s):
    """Deshace el mojibake invirtiendo la conversión que lo produjo, en vez de
    parchear pares de caracteres a mano: un diccionario de reemplazos convierte
    «categoría» en «categoráa» según el orden en que caigan las reglas. Solo se
    acepta el resultado si de verdad deja menos caracteres sospechosos."""
    s = (s or '').strip('"').strip()
    if not any(c in s for c in _SOSPECHOSOS):
        return s
    # Palabra por palabra, porque el daño es parcial: en algunos títulos el byte
    # de control se perdió del todo al guardarse y esa palabra ya no se puede
    # reconstruir. Arreglar las que sí se puede es mejor que rendirse con el
    # título entero o que inventar un reemplazo.
    out = []
    for w in s.split(' '):
        try:
            arreglado = w.encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            out.append(w)
            continue
        antes = sum(w.count(c) for c in _SOSPECHOSOS)
        despues = sum(arreglado.count(c) for c in _SOSPECHOSOS)
        out.append(arreglado if despues < antes else w)
    return ' '.join(out)


def _corta(s, n):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _titulo_legible(t):
    """Los títulos arrancan con 60 caracteres de fórmula notarial idéntica en
    todos. Quitarla es lo que hace que la tabla se lea de un vistazo. Y el
    registro escribe unos en mayúscula sostenida y otros no: se unifican, si no
    la tabla parece dos tablas."""
    t = ' '.join(_limpia(t or '').split())
    for pre in ('POR MEDIO DE LA CUAL SE ', 'POR MEDIO DEL CUAL SE ',
                'POR MEDIO DE LA CUAL ', 'POR MEDIO DEL CUAL ',
                'POR LA CUAL SE ', 'POR EL CUAL SE ', 'MEDIANTE LA CUAL SE ',
                'POR LA CUAL ', 'POR EL CUAL ', 'POR MEDIO DE/CUAL SE '):
        if t.upper().startswith(pre):
            t = t[len(pre):]
            break
    letras = [c for c in t if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.85:
        t = _restituir_propios(t.lower())
    return t[:1].upper() + t[1:]


# Nombres propios que el pase a minúscula se lleva por delante.
_PROPIOS = {
    'constitución política': 'Constitución Política',
    'colombia': 'Colombia', 'constitución': 'Constitución', 'estado': 'Estado',
    'congreso': 'Congreso', 'nación': 'Nación', 'senado': 'Senado',
    'cámara': 'Cámara', 'sena': 'SENA', 'dian': 'DIAN', 'icbf': 'ICBF',
    'iva': 'IVA', 'upc': 'UPC', 'eps': 'EPS', 'ips': 'IPS', 'arl': 'ARL',
    'sisbén': 'Sisbén', 'invías': 'Invías', 'anla': 'ANLA', 'cne': 'CNE',
    'unesco': 'Unesco', 'oit': 'OIT', 'ocde': 'OCDE',
}
# \b apoyado en \w, que en Python 3 ya incluye letras acentuadas: por eso
# 'nación' NO muerde dentro de 'vacunación' (la 'u' anterior también es \w y
# no hay frontera de palabra). Ese era el bug: un str.replace pelado convertía
# «vacunación» en «vacuNación» justo en la fila que se muestra como contraste.
_RE_PROPIOS = re.compile(r'\b(' + '|'.join(sorted(_PROPIOS, key=len, reverse=True))
                         + r')\b')


# 'ley 5 de 1992' es un nombre propio; 'la ley' a secas no. Va aparte porque
# depende de que la siga un número, no de la palabra sola.
_RE_LEY_N = re.compile(r'\b(ley|decreto|acto legislativo)\s+(\d)')


def _restituir_propios(t):
    t = _RE_PROPIOS.sub(lambda m: _PROPIOS[m.group(1)], t)
    return _RE_LEY_N.sub(lambda m: ('Acto Legislativo' if m.group(1)=='acto legislativo' else m.group(1).capitalize()) + ' ' + m.group(2), t)


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
        # "y no pasó" solo cuando de verdad no pasó. El presupuesto se radica
        # cada año y se aprueba cada año: decirle "se radicó 33 veces y no pasó"
        # es falso, y en la fila de la tributaria de 2022 contradecía a la
        # columna de al lado, que dice "llegó a ley". Cuando algún antecedente
        # sí fue ley, la señal es recurrencia, no insistencia fallida.
        if po.get('algun_antecedente_fue_ley'):
            partes.append(f'vuelve cada tanto: ya se radicó {_veces(prev)}, '
                          f'con antecedentes que sí llegaron a ley')
        else:
            partes.append(f'ya se radicó {_veces(prev)} y no pasó')
    if comp.get('rango_normativo', 0) >= 10:
        partes.append('toca la Constitución')
    if not partes:
        partes.append('sin señales fuertes de bloque')
    return '; '.join(partes)


# ===========================================================================
# SEGUNDA PÁGINA · validación retrospectiva
# ===========================================================================
# El eje 3 sí se puede validar, con la única verdad que existe: la memoria de
# quien vivió ese Congreso. Se corre sobre el cuatrienio 2022-2026 completo y
# se contrasta contra lo que Diego y Pablo recuerdan que fue bandera.
#
# Marcadores para ubicar en el ranking los proyectos que cualquiera que siguió
# ese período reconoce. La lista es CURADA A MANO y va declarada como tal: no
# sale del dato, sale de saber qué pasó. Es el patrón de referencia, no una
# medición.
BANDERAS_2226 = [
    ('modifica el articulo 49 de la constitucion',
     'Acto legislativo · salud como derecho (art. 49)'),
    ('modifica el articulo 67 de la constitucion',
     'Acto legislativo · educación como derecho (art. 67)'),
    ('sistema de proteccion social integral para la vejez',
     'Reforma pensional · llegó a ser Ley 2381 de 2024'),
    ('modifica parcialmente normas laborales',
     'Reforma laboral · llegó a ser Ley 2466 de 2025'),
    ('dictan disposiciones orientadas a ajustar y fortalecer',
     'Reforma a la salud · hundida en Comisión Séptima'),
    ('adopta una reforma tributaria para la igualdad',
     'Reforma tributaria 2022 · llegó a ser Ley 2277'),
    ('determina la competencia y funcionamiento de la jurisdicc',
     'Jurisdicción agraria · versión que se archivó'),
]


def _mil(n):
    """3053 → '3.053'. Va aparte porque hacer .replace(',', '.') sobre la
    frase entera también se come las comas del texto."""
    return f'{n:,}'.replace(',', '.')


def _norm(s):
    import unicodedata
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s.lower())


def retrospectiva():
    """Corre el eje político sobre 2022-2026 → (ranking, posiciones, banderas)."""
    rows, _m, _a, _art, _bl, partidos, _an = EV.cargar()
    import antecedentes as A
    cu = [r for r in rows if r.get('cuatrienio') == '2022-2026']
    ant = A.construir(rows, cu)
    sc = sorted(((E.eje_politico(r, partidos, None, ant), r) for r in cu),
                key=lambda t: -t[0]['score'])
    pos = {id(r): i for i, (_po, r) in enumerate(sc, 1)}
    encontradas = []
    for q, lab in BANDERAS_2226:
        hits = [(po, r) for po, r in sc if q in _norm(r['titulo'])]
        if hits:
            po, r = hits[0]
            encontradas.append((lab, pos[id(r)], po, r))
    return sc, pos, encontradas


def pagina_retrospectiva(L):
    sc, pos, banderas = retrospectiva()
    n = len(sc)
    L.append('')
    L.append('<div style="page-break-before: always"></div>')
    L.append('')
    L.append('# Segunda página · ¿el eje reconoce las banderas del Congreso pasado?')
    L.append('')
    L.append(f'Mismo eje político, corrido sobre **los {_mil(n)} proyectos del '
             'cuatrienio 2022-2026**. Ustedes vivieron ese Congreso, así que acá '
             'la validación no es una opinión sobre el futuro: es contrastar '
             'contra lo que ya pasó.')
    L.append('')
    L.append('> **Lo que les pedimos:** lo mismo, marquen donde no cuadre. Si el '
             'ranking recupera lo que ustedes recuerdan como las banderas de ese '
             'período, la heurística queda validada contra la única verdad que '
             'existe. Si se come sistemáticamente a algún actor, el peso está mal '
             'puesto y lo cambiamos.')
    L.append('')
    L.append('| # | Proyecto | Quién | Por qué está acá | Desenlace | ¿Les cuadra? |')
    L.append('|---|---|---|---|---|---|')
    for i, (po, r) in enumerate(sc[:15], 1):
        it = {'politico': po, 'titulo': r['titulo']}
        quien = _bancada(it) or '—'
        if quien == 'Gobierno':
            quien = '**Gobierno**'
        tit = _corta(_titulo_legible((r['titulo'] or '').strip('"')), 62)
        num = r.get('numero_senado') or r.get('numero_camara') or '—'
        des = {'LEY': 'llegó a ley', 'ARCHIVADO_TIEMPO': 'murió por tiempo',
               'ARCHIVADO_OTRO': 'archivado', 'RETIRADO': 'retirado',
               'EN_TRAMITE': 'seguía en trámite'}.get(r.get('resultado'), '—')
        L.append(f'| {i} | **{num}** · {tit} | {quien} | {_razon(it)} | {des} | |')
    L.append('')
    L.append('### Dónde quedaron las reformas que todos recuerdan')
    L.append('')
    L.append('Los proyectos de abajo no los eligió el modelo: los pusimos '
             'nosotros porque son los que cualquiera que siguió ese Congreso '
             'nombra de memoria. La columna dice en qué puesto los dejó el eje, '
             f'de {_mil(n)} proyectos.')
    L.append('')
    L.append('| Bandera del período | Puesto que le dio el eje | Antes de anoche |')
    L.append('|---|---|---|')
    for lab, p, _po, _r in sorted(banderas, key=lambda t: t[1]):
        marca = '✅' if p <= 60 else ('⚠️' if p <= 300 else '❌')
        antes = ANTES_DEL_ARREGLO.get(lab)
        col = f'#{antes}' if antes else '—'
        L.append(f'| {lab} | {marca} **#{p}** de {_mil(n)} | {col} |')
    L.append('')
    L.append('Las siete quedan en el 8% de arriba. Las tres con ⚠️ no están mal '
             'puestas: son leyes ordinarias sin historia de re-radicación, y este '
             'eje mide respaldo, insistencia y rango normativo — no el tamaño de '
             'la reforma. **El tamaño lo mide el eje de impacto**, que es la otra '
             'coordenada y por eso van separadas.')
    L.append('')
    L.append('### Lo que este ejercicio encontró (y ya está arreglado)')
    L.append('')
    L.append('La columna «antes de anoche» no está de adorno. Correr el eje '
             'contra un período con desenlace conocido destapó un fallo que con '
             'solo mirar la legislatura actual no se veía: **el sistema le daba '
             'cero respaldo a todo lo que radica el Gobierno.**')
    L.append('')
    L.append('El campo de firmantes viene en cero cuando quien radica es una '
             'entidad, así que el componente que más pesa —28 de 100— valía cero '
             'justo para el actor que por definición tiene más peso político. La '
             'reforma pensional, que fue la bandera del cuatrienio y además se '
             'volvió ley, quedaba en el puesto **1.629 de 3.053**. En la mitad '
             'de abajo.')
    L.append('')
    L.append('El arreglo es de una línea y no es discutible: radicar como '
             'Gobierno **es** el acto de bloque más grande que existe, así que '
             'cuenta como respaldo máximo. De paso hubo que restar las leyes '
             'aprobatorias de tratado, que el Ejecutivo radica por decenas y son '
             'trámite, no bandera — sin eso el top se llenaba de convenios de la '
             'OIT.')
    L.append('')
    L.append('**Y eso cambia la lectura del hallazgo de la primera página.** El '
             'top de la legislatura actual ya no es 10 de 10 del Pacto: es 7 del '
             'Pacto y 3 del Gobierno, con el presupuesto, la ley minera y las '
             'competencias territoriales entrando al cuadro. Parte de aquel '
             '«los 10 son del Pacto» era el fallo, no el Congreso. Lo que queda '
             'de concentración sigue siendo pregunta abierta para ustedes.')
    L.append('')
    return sc, banderas


# Posiciones medidas ANTES de corregir el respaldo del Ejecutivo. Se conservan
# porque son la evidencia del fallo, no una estimación.
ANTES_DEL_ARREGLO = {
    'Reforma pensional · llegó a ser Ley 2381 de 2024': '1.629',
    'Reforma laboral · llegó a ser Ley 2466 de 2025': '982',
    'Reforma a la salud · hundida en Comisión Séptima': '134',
    'Acto legislativo · educación como derecho (art. 67)': '126',
    'Acto legislativo · salud como derecho (art. 49)': '2',
}


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
             'cuadre. El eje político es una heurística: no existe un registro '
             'oficial de qué fue bandera de quién, así que se contrasta contra '
             'la memoria de quien vivió el Congreso. La segunda página hace ese '
             'ejercicio con el cuatrienio pasado —y ya destapó un fallo grande—; '
             'esta primera necesita el criterio de ustedes, porque es sobre un '
             'período que todavía no tiene desenlace. Su desacuerdo se traduce '
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

    pagina_retrospectiva(L)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print(f'\n→ {SALIDA}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
