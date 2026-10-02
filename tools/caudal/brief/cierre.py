#!/usr/bin/env python3
"""
El brief de CIERRE de la semana · lo que necesita y que el del lunes no.

QUÉ ES. El brief del lunes abre la semana: qué se movió en 72 horas y qué hacer.
El del viernes la cierra, y responde otras tres preguntas (decisión de Ricardo,
2-oct-2026):

  1. ¿Cómo terminaron los dos o tres temas grandes del lunes?
  2. ¿Qué más pasó en la semana?
  3. ¿Qué viene la próxima semana y en qué hay que enfocarse el lunes?

La primera es la que obliga a cambiar el motor. Sin el brief del lunes a la mano,
el modelo no sabe qué se le prometió al lector, y un barrido derivado solo de la
ficha trae lo que dice la ficha, no el desenlace de lo que se dijo. Por eso este
módulo:

  · encuentra el brief anterior (local o en S3),
  · arma consultas de prensa A LA MEDIDA de cada tema del lunes, y
  · fija la ventana del lunes al viernes, no las 72 horas.

LO QUE SE DIJO EL LUNES NO LO REESCRIBE EL MODELO. Se guarda literal en
`_meta.anterior` y el documento lo cita de ahí. El modelo solo escribe cómo
terminó. Si el modelo parafraseara lo del lunes, el lector no podría comparar.
"""
import datetime
import json
import os
import re
import subprocess
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(AQUI, '..', '..', '..', 'Bases de datos', 'caudal-briefs')
S3_BRIEFS = 's3://caudal-legislativo/metadata/briefs'

# Cuántos temas del lunes se siguen. «Dos o tres» (Ricardo): el resto del lunes
# no se pierde, entra a la evidencia general de la semana si se movió.
N_SEGUIMIENTO = 3
# Consultas de prensa por tema. Con una sola, «Presupuesto 2027» traía las notas
# del presupuesto en general y no la del recorte a la JEP, que era el ángulo.
CONSULTAS_POR_TEMA = 3

# Los estados posibles de un tema del lunes al cierre de la semana. Lista
# CERRADA a propósito: un estado libre («en evolución», «abierto») no le dice
# nada al lector, y el render pinta un color por estado.
ESTADOS = {
    'resuelto': 'Se resolvió',
    'avanzo': 'Avanzó',
    'complicado': 'Se complicó',
    'igual': 'Quedó igual',
    'sin_dato': 'Sin dato verificable',
}


def slug(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def _fecha_de(nombre):
    m = re.search(r'(\d{4}-\d{2}-\d{2})\.json$', nombre)
    return m.group(1) if m else ''


def _candidatos_locales(cliente):
    carpeta = os.path.join(LOCAL, slug(cliente))
    try:
        return [(_fecha_de(x), os.path.join(carpeta, x))
                for x in os.listdir(carpeta) if _fecha_de(x)]
    except OSError:
        return []


def _candidatos_s3(cliente):
    try:
        r = subprocess.run(['aws', 's3', 'ls', f'{S3_BRIEFS}/{slug(cliente)}/'],
                           capture_output=True, text=True, timeout=60)
    except Exception:                                            # noqa: BLE001
        return []
    if r.returncode != 0:
        return []
    out = []
    for linea in r.stdout.splitlines():
        nombre = linea.split()[-1] if linea.split() else ''
        if _fecha_de(nombre):
            out.append((_fecha_de(nombre), f'{S3_BRIEFS}/{slug(cliente)}/{nombre}'))
    return out


def _leer(ruta):
    if ruta.startswith('s3://'):
        r = subprocess.run(['aws', 's3', 'cp', ruta, '-'],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[:200])
        return json.loads(r.stdout)
    return json.load(open(ruta, encoding='utf-8'))


def buscar_anterior(cliente, hoy=None, dias_max=6):
    """El brief que ABRIÓ esta semana: el más reciente de los últimos `dias_max`
    días, anterior a hoy y que no sea a su vez un cierre.

    Prefiere el lunes: si alguien corrió un brief a mano un miércoles, el viernes
    igual tiene que cerrar lo que se prometió el lunes, que es lo que leyó el
    cliente. Busca primero en la copia local y después en S3 (en GitHub Actions
    no hay copia local). Devuelve (brief, ruta) o (None, motivo).
    """
    hoy = hoy or datetime.date.today()
    piso = (hoy - datetime.timedelta(days=dias_max)).isoformat()
    techo = hoy.isoformat()
    vistos = {}
    for fecha, ruta in _candidatos_locales(cliente) + _candidatos_s3(cliente):
        if piso <= fecha < techo:
            vistos.setdefault(fecha, ruta)       # local primero: no gasta red
    if not vistos:
        return None, (f'no hay brief de {cliente} entre el {piso} y ayer '
                      f'(ni en {LOCAL} ni en {S3_BRIEFS})')
    orden = sorted(vistos, key=lambda f: (
        datetime.date.fromisoformat(f).isoweekday() == 1, f), reverse=True)
    for fecha in orden:
        try:
            b = _leer(vistos[fecha])
        except Exception as e:                                   # noqa: BLE001
            print(f'[cierre] no pude leer {vistos[fecha]}: {e}')
            continue
        if (b.get('_meta') or {}).get('tipo') == 'cierre':
            continue
        return b, vistos[fecha]
    return None, 'los briefs de la semana son todos de cierre o no se pudieron leer'


def temas_a_seguir(anterior, n=N_SEGUIMIENTO):
    """Los temas del lunes que se siguen: los primeros `n`, que el brief del lunes
    ya ordenó por urgencia. Se guardan con sus textos LITERALES."""
    out = []
    for i, t in enumerate((anterior.get('temas') or [])[:n], 1):
        out.append({'n': i, 'rotulo': t.get('rotulo', ''), 'titulo': t.get('titulo', ''),
                    'que_hacer': t.get('que_hacer', ''), 'urgencia': t.get('urgencia', ''),
                    'seguir': list(t.get('seguir') or [])})
    return out


# ── consultas de seguimiento ───────────────────────────────────────────────
CONSULTAS_SYSTEM = """Armas búsquedas de prensa colombiana (Google News) para saber \
cómo terminó, cinco días después, un tema de asuntos públicos. Para cada tema \
devuelves 3 búsquedas MUY CORTAS, de 1 a 3 palabras: el buscador exige todas las \
palabras, así que cada palabra de más esconde notas. La primera es la palabra o \
sigla que más distingue el tema, sola («FMI», «Colpensiones», «JEP»). Las otras \
dos cubren otros ángulos del mismo tema, también con nombres propios: la entidad, \
la persona, el proyecto. Nunca cifras ni signos de pesos (los titulares escriben \
la misma cifra de diez maneras), nunca nada genérico («Gobierno», «Congreso», \
«economía»), nunca nombres de medios, y sin la palabra Colombia: el buscador ya \
la agrega. Devuelves SOLO un JSON válido: \
{"temas": [{"n": 1, "consultas": ["…", "…", "…"]}]}"""


def _consultas_modelo(temas, generar, modelo):
    """Una llamada barata: búsquedas a la medida para los temas del lunes que no
    traen `seguir` (los briefs anteriores al 2-oct-2026 no lo traían)."""
    L = []
    for t in temas:
        L.append(f"TEMA {t['n']} · {t['rotulo']}\n  {t['titulo']}\n  Qué se recomendó: {t['que_hacer']}")
    d, uso = generar(CONSULTAS_SYSTEM, '\n\n'.join(L), modelo=modelo, max_tokens=1500,
                     pensar=False)
    out = {}
    for x in (d.get('temas') or []):
        qs = [str(q).strip() for q in (x.get('consultas') or []) if str(q).strip()]
        if qs:
            out[int(x.get('n') or 0)] = qs[:CONSULTAS_POR_TEMA]
    return out, uso


_SIGLA = re.compile(r'\b[A-ZÁÉÍÓÚÑ]{2,6}\b')
_NO_SIGLA = {'COP', 'US', 'UTL', 'USD', 'EE', 'UU'}


def _consultas_respaldo(t):
    """Si el modelo no responde: el rótulo del tema y sus siglas. Pobre pero
    honesto: nunca inventa términos que el brief del lunes no traía."""
    qs = [t['rotulo']] if t.get('rotulo') else []
    for s in _SIGLA.findall(t.get('titulo', '')):
        if s not in _NO_SIGLA and s not in qs:
            qs.append(s)
    return qs[:CONSULTAS_POR_TEMA]


def armar_consultas(temas, generar, modelo='claude-sonnet-5'):
    """Rellena `consultas` en cada tema. Devuelve el uso de la llamada al modelo
    (o None si no hubo que llamarlo)."""
    faltan = [t for t in temas if not t.get('seguir')]
    uso, del_modelo = None, {}
    if faltan:
        try:
            del_modelo, uso = _consultas_modelo(faltan, generar, modelo)
        except SystemExit as e:
            print(f'[cierre] el modelo no armó las consultas ({e}); uso el respaldo')
        except Exception as e:                                   # noqa: BLE001
            print(f'[cierre] el modelo no armó las consultas ({str(e)[:120]}); uso el respaldo')
    for t in temas:
        qs = list((t.get('seguir') or del_modelo.get(t['n'])
                   or _consultas_respaldo(t))[:CONSULTAS_POR_TEMA])
        # El rótulo del tema va SIEMPRE, además de las del modelo: es la búsqueda
        # amplia. Medido el 2-oct: las tres del modelo para «Presupuesto 2027»
        # salieron todas sobre la JEP, y la nota del techo de $634,9 billones
        # entró por casualidad, por otra consulta.
        # ⚠️ Igualdad, no «contiene»: «JEP presupuesto 2027» contiene «presupuesto
        # 2027» y es justo la búsqueda estrecha que esta línea existe para abrir.
        rot = (t.get('rotulo') or '').strip()
        if rot and rot.lower() not in (q.lower() for q in qs):
            qs.append(rot)
        t['consultas'] = qs
    return uso


def jobs_seguimiento(temas, dias):
    """Las consultas como jobs del barrido. La clave lleva el número del tema del
    lunes, que es lo que permite agrupar la evidencia por tema en el prompt."""
    jobs = []
    for t in temas:
        for q in t.get('consultas') or []:
            jobs.append((f"medios::seguimiento::{t['n']}::{q}",
                         {'action': 'medios', 'query': q, 'dias': dias}))
    return jobs


def ventana(anterior, hoy=None):
    """Del día del brief anterior a hoy, ambos incluidos.

    Arranca el MISMO día del lunes, no el siguiente: el brief del lunes cortó a
    media mañana, y lo que se publicó esa tarde —la reacción, la primera
    precisión oficial— es justo lo que el viernes tiene que contar.
    """
    hoy = hoy or datetime.date.today()
    desde = ((anterior.get('_meta') or {}).get('ventana') or {}).get('hasta') \
        or (hoy - datetime.timedelta(days=4)).isoformat()
    dias = (hoy - datetime.date.fromisoformat(desde)).days + 1
    return desde, max(dias, 1)
