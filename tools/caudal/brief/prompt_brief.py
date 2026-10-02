#!/usr/bin/env python3
"""
El prompt del brief — la voz de los briefs escritos a mano, puesta por escrito.

QUÉ ES. Los briefs de Binance y de Cauce del 7-sep-2026 salieron buenos porque
los escribió una persona que sabía quién era el cliente y qué hace con el
documento. Este archivo traduce ese oficio en instrucciones: la estructura, el
orden, las reglas de honestidad y —lo más difícil de transmitir— el criterio de
qué entra y qué no.

NO ES el prompt de la Rosa de los Vientos. La Rosa responde «¿qué se movió hoy
en mis cuatro direcciones?» en dos o tres frases por punto. El brief responde
«¿qué pasó, por qué me importa y qué hago?» en cinco a nueve temas ordenados por
urgencia, con la agenda de lo que viene y una verificación explícita de lo que
NO se movió. Son dos productos con dos formas.

VENTANA. 72 horas. Es corta a propósito, y por eso el brief tiene que ser
riguroso con la diferencia entre lo que se movió, lo que sigue vigente sin
moverse, y lo que no sabemos porque el registro va atrasado. Un brief que
presenta lo viejo como nuevo se quema en la segunda entrega.
"""
import re

# ── el sistema: quién escribe, para quién y con qué reglas ─────────────────
BRIEF_SYSTEM = """Eres el analista de asuntos públicos que le escribe el brief a un cliente de \
Cauce. Escribes en español de Colombia, tuteo neutro de Bogotá: sin voseo, sin \
regionalismos, sin jerga de consultoría.

LOS HECHOS DUROS. Bajo varios titulares vienen frases sacadas del CUERPO de la \
nota, marcadas [CIFRA] o [CITA]. Ahí están los números y las frases textuales \
que hacen creíble un brief — úsalos, con su fuente. Un titular dice «recorte del \
40% al deporte»; el cuerpo dice que pasa de $496.100 millones a $297.700. La \
segunda versión es la que sirve. Cítalos literal: no los redondees ni los \
recalcules.

QUÉ ESTÁS ESCRIBIENDO. Un brief de seguimiento de las últimas 72 horas. No es \
un resumen de prensa ni un listado de proyectos: es el documento con el que tu \
cliente decide qué hacer esta semana. Cada tema tiene que contestar tres cosas \
en este orden: qué pasó (con nombres, cifras y fechas), por qué le importa a ESTE \
cliente, y qué hacer con eso.

LA REGLA QUE NO SE ROMPE. Usa ÚNICAMENTE los hechos de la evidencia que te doy. \
No inventes proyectos, cifras, nombres, fechas, entidades ni titulares. Si un \
dato no está, no lo menciones: no lo estimes, no lo redondees, no lo deduzcas. \
Cada afirmación del brief tiene que poder rastrearse a un ítem de la evidencia. \
Cuando cites una cifra o una fecha, tiene que aparecer literal en la evidencia.

CÓMO SE ELIGE QUÉ ENTRA. Entre cinco y nueve temas, ordenados por lo que exige \
atención primero, no por pilar ni por fuente. Un tema puede juntar señales de \
varios pilares —un proyecto de ley, la prensa que lo cubre y la consulta pública \
que lo reglamenta son UN tema, no tres—. Descarta sin piedad lo que no le mueva \
la aguja a este cliente; el volumen no es virtud. Si algo está marcado como \
ruido declarado por el cliente, no lo subas a tema ni lo pongas de titular.

LO QUE SE MOVIÓ Y LO QUE SOLO ESTÁ. La evidencia separa lo que ocurrió en la \
ventana de lo que sigue vigente sin moverse. Nunca presentes como novedad algo \
que solo está vigente: si lo mencionas, dilo con esas palabras («sigue en \
trámite», «no se ha movido desde…»). Presentar lo viejo como nuevo es la forma \
más rápida de perder a un lector.

LO QUE NO SABEMOS SE DICE. Cada pilar trae hasta qué fecha llega su registro. Un \
pilar sin novedades puede significar dos cosas opuestas: que no pasó nada, o que \
todavía no lo publican. Nunca las confundas y nunca afirmes que «no hubo» algo \
cuando el registro va atrasado: escribe hasta cuándo llega el registro. Esa \
sección es parte del producto, no una disculpa. Y distingue QUIÉN está atrasado: \
si el pilar dice que lo revisamos hoy pero la fuente oficial no ha publicado, el \
hueco es de la fuente (el Senado, la Cámara, el regulador), no nuestro — dilo \
así, porque el lector no puede saberlo y sin esa precisión lo lee como una falla \
de este servicio.

LAS REDES. La sección REDES trae lo que se publicó en X sobre los temas del \
cliente en el último día, ordenado por interacción. Cada publicación es la \
OPINIÓN de quien la escribe, no un hecho: atribúyela siempre a su @usuario, \
nunca uses una cifra o una acusación de un tuit como si estuviera verificada, y \
no la conviertas en tema propio salvo que tenga tracción real o que la prensa o \
el registro oficial digan lo mismo. Sirve para lo que la prensa no da: el tono, \
quién está moviendo la conversación y cuánto eco tiene.

LO QUE ESTÁ FUERA DE ALCANCE. Si el cliente opera en países donde no tenemos \
fuentes, no digas ni insinúes que allá no pasó nada: no lo sabemos, y hay que \
decirlo con esas palabras.

LAS FECHAS. En la agenda escribe la fecha en `iso` (AAAA-MM-DD) y NO escribas el \
día de la semana: lo calcula el sistema. Escribirlo de memoria es el error más \
fácil de cometer y el que más daño hace — un «lunes 15» que en realidad era \
martes pone bajo sospecha todas las fechas del documento.

TONO. Frases cortas, una idea por frase. Cifras y nombres propios, no adjetivos. \
Nada de «es importante destacar», «cabe señalar», «en el marco de». No abras los \
párrafos anunciando lo que vas a decir: dilo. El cliente es experto en lo suyo; \
no le expliques qué es una comisión ni qué es un decreto.

DEVUELVES SIEMPRE UN JSON VÁLIDO con esta forma:
{
  "titular": "una frase que diga lo principal de la ventana, con el hecho \
concreto adentro; no un rótulo temático",
  "bajada": "dos frases: qué cubre este brief y con qué corte",
  "lectura": {
    "titulo": "el hallazgo central en una frase",
    "parrafos": ["2 o 3 párrafos que hilen lo principal"],
    "si_solo_hay_tiempo": "una cosa, con su razón y su plazo si la evidencia lo trae"
  },
  "temas": [
    {
      "rotulo": "área o frente, dos o tres palabras",
      "linea": "la línea de negocio del cliente que toca, si la ficha la trae; si no, cadena vacía",
      "titulo": "el hallazgo del tema en una frase con el hecho adentro",
      "parrafos": ["1 o 2 párrafos con los datos duros: números, nombres, fechas"],
      "por_que": "por qué le importa a ESTE cliente, en sus términos",
      "que_hacer": "la acción concreta, con plazo si la evidencia lo trae",
      "urgencia": "alta | media | baja",
      "seguir": ["3 búsquedas de prensa MUY CORTAS (1 a 3 palabras) para saber \
el viernes cómo terminó el tema: la primera, la sigla o el nombre que más lo \
distingue, solo; las otras, la entidad, la persona o el proyecto. Sin cifras, sin \
nada genérico como «Gobierno» o «economía», sin nombres de medios y sin la \
palabra Colombia"]
    }
  ],
  "agenda": [{"iso": "AAAA-MM-DD de ese día", "cuando": "solo si NO es un día \
puntual (un rango, «esta semana»); si hay iso, déjalo vacío", "que": "qué pasa"}],
  "no_se_movio": [{"fuente": "nombre del pilar o la fuente", "estado": "qué se \
verificó y hasta qué fecha llega su registro"}]
}"""


# ── el mensaje: la ficha del cliente + la evidencia del barrido ────────────
def _lineas_ficha(p):
    L = []
    if p.get('que_hace'):
        L.append('QUÉ HACE: ' + p['que_hace'])
    if p.get('lector'):
        L.append('QUIÉN LEE ESTE BRIEF Y QUÉ HACE CON ÉL: ' + p['lector'])
    if p.get('decisiones'):
        L.append('DECISIONES QUE TOMA CON ÉL (cada «qué hacer» debe servirle a '
                 'una de estas): ' + ' · '.join(p['decisiones']))
    if p.get('lineas'):
        L.append('LÍNEAS DE NEGOCIO (ubica cada tema en la que toca): '
                 + ' · '.join(f"{l['nombre']}"
                              + (f" (Comisión {l['comision']})" if l.get('comision') else '')
                              for l in p['lineas']))
    if p.get('interlocutores'):
        L.append('SUS INTERLOCUTORES: ' + ', '.join(p['interlocutores']))
    if p.get('relojes'):
        L.append('SUS PLAZOS PROPIOS (mide lo que pasó contra estos relojes): '
                 + ' · '.join(p['relojes']))
    if p.get('no_interesa'):
        L.append('RUIDO DECLARADO (no lo subas a tema ni a titular): '
                 + ', '.join(p['no_interesa']))
    if p.get('fuera_de_alcance'):
        L.append('FUERA DEL ALCANCE DE NUESTRAS FUENTES: el cliente opera en '
                 + ', '.join(p['fuera_de_alcance'])
                 + '. NO tenemos fuentes de esos países: nunca digas ni insinúes '
                   'que allá no pasó nada.')
    return L


def _fmt_item(pilar, x):
    o = f"  ({x['_origen']})" if x.get('_origen') else ''
    ruido = '  [RUIDO DECLARADO]' if x.get('_ruido') else ''
    if pilar in ('congreso', 'congreso_frente'):
        aut = x.get('autores')
        aut = ', '.join(aut) if isinstance(aut, list) else (aut or '')
        return (f"- [{x.get('estado')}] {x.get('numero')} ({x.get('fecha')}) "
                f"{x.get('titulo', '')[:200]}"
                + (f" · Comisión {x['comision']}" if x.get('comision') else '')
                + (f" · autores: {aut[:90]}" if aut else '') + o + ruido)
    if pilar == 'regulatorio':
        return (f"- {x.get('fecha')} · {x.get('fuente')} · {x.get('tipo_acto')} · "
                f"{x.get('destinatario')}: {x.get('motivo', '')[:220]}"
                + (f" ({x['resolucion']})" if x.get('resolucion') else '') + o + ruido)
    if pilar == 'ejecutivo':
        # el título lleva el NÚMERO («DECRETO No. 1382 DEL 9 DE SEPTIEMBRE…»):
        # sin él el brief solo puede decir «un decreto», que no se puede citar
        do = f" · {x['diario_oficial']}" if x.get('diario_oficial') else ''
        return (f"- {x.get('fecha')} · {x.get('titulo') or x.get('tipo')}: "
                f"{x.get('descripcion') or ''}"[:300] + do + o + ruido)
    if pilar == 'sucop':
        return (f"- {x.get('entidad')}: {x.get('titulo', '')[:180]} · "
                f"CIERRA {x.get('cierra')}" + o + ruido)
    if pilar == 'medios':
        L = [f"- {x.get('fecha')} · {x.get('medio')}: {x.get('titulo', '')[:180]}"
             + o + ruido]
        # Los hechos del CUERPO de la nota, que es donde viven las cifras: solo
        # el 3% de los titulares trae una. Van sangrados bajo su titular para
        # que el modelo sepa de qué nota salió cada uno.
        for h in (x.get('hechos') or []):
            marca = 'CIFRA' if h.get('cifra') else 'CITA'
            L.append(f"      [{marca}] {h['frase'][:250]}")
        if x.get('hechos') and not x.get('cuerpo_delimitado', True):
            L.append("      (⚠ el cuerpo de esta nota no venía delimitado: sus "
                     "datos pueden ser de otra nota de la misma página — "
                     "úsalos solo si encajan con el titular)")
        return '\n'.join(L)
    if pilar == 'redes':
        return (f"- {(x.get('fecha') or '')[:10]} · @{x.get('autor')} "
                f"({x.get('seguidores', 0)} seguidores · {x.get('likes', 0)} me gusta · "
                f"{x.get('rts', 0)} reposts) sobre «{x.get('tema')}»: "
                f"{(x.get('texto') or '').replace(chr(10), ' ')[:260]}")
    if pilar == 'contratacion':
        return (f"- {x.get('fecha')} · {x.get('entidad')} → {x.get('proveedor')}: "
                f"{x.get('objeto', '')[:150]}" + o + ruido)
    if pilar == 'agenda':
        ya = '[YA PASÓ · orden del día, no resultado] ' if x.get('ya_paso') else ''
        return (f"- {ya}{x.get('fecha')} · {x.get('corporacion')} {x.get('ambito')}: "
                + '; '.join(f'{n} {t}' for n, t in (x.get('proyectos') or [])))
    return '- ' + str(x)[:200]


# Cuánto de cada pilar entra al mensaje. El frente vigente va corto a propósito:
# es contexto, no noticia, y dejarlo crecer haría que el brief hablara de 2012.
TOPES = {'congreso': 30, 'congreso_frente': 14, 'regulatorio': 25,
         'ejecutivo': 20, 'sucop': 20, 'medios': 70, 'contratacion': 12,
         'agenda': 12, 'redes': 24}

# ⚠️⚠️ El recorte de prensa NO puede ser «los primeros N»: solo el 3% de los
# titulares trae una cifra (medido sobre los 152 del barrido de Cauce), así que
# tomar por orden de llegada bota justo lo poco que tiene dato duro. Pasó y se
# midió: el titular con los «$634,9 billones» del Presupuesto —LA cifra de ese
# frente, y una de las que sostienen el brief del 7 de septiembre— quedó en la
# posición 105 de 152 y nunca llegó al modelo. El brief salió con una sola cifra
# en todo el documento contra las trece del escrito a mano.
_CIFRA = re.compile(r'\$\s?[\d.,]+|\b\d{1,3}(?:\.\d{3})+\b|\b\d+(?:,\d+)?\s?%')


def _valor_titular(x):
    """Cuánto aporta un titular. Mayor es mejor; se ordena descendente.

    No reordena la lista final —la cronología se conserva— sino que decide QUÉ
    sobrevive al recorte cuando hay más titulares que cupo.
    """
    t = x.get('titulo') or ''
    v = 0
    if _CIFRA.search(t):
        v += 3                      # una cifra es lo más escaso y lo más útil
    if '«' in t or '"' in t or '“' in t:
        v += 2                      # una cita textual da la frase que se repite
    if x.get('_origen', '').startswith('interlocutor'):
        v += 2                      # lo que dijo su supervisor pesa más
    if x.get('_origen', '').startswith('empresa'):
        v += 2                      # y lo que se dice de una vigilada, también
    if x.get('_ruido'):
        v -= 4                      # ruido declarado por el cliente
    return v


def _recorte(pilar, xs, tope):
    """Los `tope` ítems más útiles, devueltos en su orden original."""
    if len(xs) <= tope:
        return xs
    if pilar != 'medios':
        return xs[:tope]
    orden = sorted(range(len(xs)),
                   key=lambda i: (-_valor_titular(xs[i]), i))[:tope]
    return [xs[i] for i in sorted(orden)]

TITULOS = {
    'congreso': 'CONGRESO · lo que se movió en la ventana',
    'congreso_frente': 'CONGRESO · vigente pero SIN movimiento en la ventana '
                       '(contexto, NO es novedad)',
    'regulatorio': 'REGULADORES · actos en la ventana',
    'ejecutivo': 'EJECUTIVO · normativa en la ventana',
    'sucop': 'CONSULTA PÚBLICA DE NORMAS · abiertas, con su fecha de cierre',
    'medios': 'PRENSA · titulares de la ventana',
    'redes': 'REDES · lo más movido en X sobre sus temas en el último día '
             '(opinión de quien publica, NO hechos verificados)',
    'contratacion': 'CONTRATACIÓN · contratos de sus vigiladas',
    'agenda': 'AGENDA · lo que viene (órdenes del día ya publicadas)',
}


def _cabecera(b):
    """El cliente y su ficha: la misma para el brief del lunes y el del viernes."""
    p = b['perfil']
    L = [f"CLIENTE: {p.get('nombre')}"]
    L += ['  · ' + x for x in _lineas_ficha(p)]
    return L


def _kpis(b):
    k = b.get('kpis') or {}
    if not k:
        return []
    return [f"El radar priorizó {k.get('n_radar', 0)} señales "
            f"({k.get('alto', 0)} de prioridad alta) y hay "
            f"{k.get('en_tramite', 0)} proyectos de ley en trámite activo "
            f"sobre sus temas."]


def _registros(b):
    """Hasta dónde llega cada registro, con quién es el responsable del hueco."""
    v = b['ventana']
    cob = b.get('cobertura') or {}
    rev = b.get('revision') or {}
    L = ["\nHASTA DÓNDE LLEGA CADA REGISTRO (úsalo para «qué no se movió»; "
         "un pilar vacío con registro atrasado NO es lo mismo que quietud):"]
    for pilar, f in sorted(cob.items()):
        if f and f < v['desde'] and rev.get(pilar, '') >= v['hasta']:
            # Revisamos hoy y la FUENTE no ha publicado nada después: el hueco
            # es del Senado/Cámara, no nuestro, y el brief tiene que decirlo así.
            L.append(f"  · {pilar}: REVISADO el {rev[pilar]}, pero Senado y Cámara no han "
                     f"publicado radicados posteriores al {f}. El retraso es de la fuente "
                     f"oficial, NO de nuestro registro: di que las fuentes oficiales no han "
                     f"publicado radicaciones desde el {f} y que lo radicado después (si lo "
                     f"reporta la prensa) aún no aparece en el registro oficial. Nunca "
                     f"escribas «nuestros registros llegan hasta…» ni «los registros de "
                     f"Congreso llegan solo hasta…». Tampoco digas que no hubo movimiento.")
        elif f and f < v['desde']:
            L.append(f"  · {pilar}: el registro llega solo hasta {f} — ATRASADO, no cubre "
                     f"la ventana. Prohibido decir que no hubo movimiento en este pilar: "
                     f"di que el registro llega hasta {f} y que lo posterior no está verificado.")
        else:
            L.append(f"  · {pilar}: el registro llega hasta {f}")
    return L


def _pilares(b, titulos=None, topes=None):
    """La evidencia pilar por pilar, recortada y con el estado de cada vacío."""
    v, ev = b['ventana'], b['evidencia']
    cob = b.get('cobertura') or {}
    rev = b.get('revision') or {}
    topes = topes or TOPES
    L = []
    for pilar, titulo in (titulos or TITULOS).items():
        xs = ev.get(pilar) or []
        L.append(f"\n### {titulo} · {len(xs)}")
        if not xs:
            f = cob.get(pilar)
            if f and f < v['desde'] and rev.get(pilar, '') >= v['hasta']:
                L.append(f"  (SIN RADICADOS PUBLICADOS: revisado el {rev[pilar]}; las "
                         f"fuentes oficiales no publican radicaciones desde el {f}. No "
                         f"significa que no se haya radicado nada: significa que el "
                         f"Senado y la Cámara no lo han publicado)")
            elif f and f < v['desde']:
                L.append(f"  (SIN DATO: el registro llega solo hasta {f}, antes de que "
                         f"empiece la ventana. Esto NO significa que no haya habido "
                         f"movimiento: significa que no lo sabemos)")
            elif f:
                # ⚠️ Decir solo «el registro llega hasta F» dejaba al modelo
                # creer que no había NADA publicado: el cierre del 2-oct escribió
                # «la última radicación oficial sigue siendo del 23» con radicados
                # publicados hasta el 30, ninguno de los temas del cliente.
                L.append(f"  (ningún ítem de la ventana toca sus temas. El registro de "
                         f"este pilar SÍ cubre la ventana: tiene publicaciones hasta {f}, "
                         f"solo que ninguna es de sus temas. No digas que la fuente "
                         f"dejó de publicar)")
            else:
                L.append("  (sin ítems en la ventana)")
            continue
        tope = topes.get(pilar, 20)
        for x in _recorte(pilar, xs, tope):
            L.append('  ' + _fmt_item(pilar, x))
        if len(xs) > tope:
            L.append(f"  … y {len(xs) - tope} más del mismo pilar")
    return L


def _errores(b):
    ev = b['evidencia']
    if not ev.get('errores'):
        return []
    L = ["\n### CONSULTAS QUE FALLARON (no asumas que están vacías)"]
    for e in ev['errores'][:8]:
        L.append(f"  - {e['consulta']}: {e['error']}")
    return L


def armar_mensaje(b):
    """Barrido → el mensaje de usuario que se le manda al modelo."""
    v = b['ventana']
    L = _cabecera(b)
    L.append(f"\nVENTANA DEL BRIEF: últimas {v.get('dias_prensa', 3) * 24} horas "
             f"({v['desde']} → {v['hasta']}).")
    L += _kpis(b)
    L += _registros(b)
    L += _pilares(b)
    L += _errores(b)
    L.append("\nEscribe el brief en JSON, siguiendo la forma que te di.")
    return '\n'.join(L)


# ════════════════════════════════════════════════════════════════════════════
# EL BRIEF DE CIERRE DE LA SEMANA (viernes · 2-oct-2026)
#
# Responde tres preguntas que el del lunes no: cómo terminaron sus temas grandes,
# qué más pasó en la semana, y en qué enfocarse el lunes. Ver cierre.py.
#
# Las reglas de honestidad, las de redes, fechas y tono NO se copian: se toman
# del prompt del lunes por su encabezado. Si una regla se afina allá, el viernes
# la hereda; con dos copias, una envejece y los dos briefs dejan de obedecer lo
# mismo sin que nadie lo note.
# ════════════════════════════════════════════════════════════════════════════
def _parrafo(texto, encabezado):
    for p in texto.split('\n\n'):
        if p.startswith(encabezado):
            return p
    raise KeyError(f'el prompt del lunes ya no trae el párrafo «{encabezado}»')


BRIEF_CIERRE_SYSTEM = '\n\n'.join([
    BRIEF_SYSTEM.split('\n\n')[0],          # quién escribe y en qué español
    """QUÉ ESTÁS ESCRIBIENDO. El brief de CIERRE de la semana: va del lunes al \
viernes y se lee el viernes, para cerrar la semana y llegar preparado al lunes. \
No es otro brief de 72 horas: es el balance de la semana. Responde tres \
preguntas, en este orden: cómo terminaron los temas grandes del brief del lunes; \
qué más pasó en la semana que le importe a este cliente; y qué viene la próxima \
semana y en qué tiene que enfocarse el lunes.""",
    _parrafo(BRIEF_SYSTEM, 'LOS HECHOS DUROS.'),
    _parrafo(BRIEF_SYSTEM, 'LA REGLA QUE NO SE ROMPE.'),
    _parrafo(BRIEF_SYSTEM, 'LO QUE SE MOVIÓ Y LO QUE SOLO ESTÁ.'),
    """LOS TEMAS DEL LUNES. Te paso, literal, los temas que el brief del lunes puso \
arriba y lo que recomendó hacer. Para CADA uno escribes cómo terminó la semana, \
con la evidencia de SEGUIMIENTO de ese tema y con la del resto de la semana. Su \
estado sale de esta lista cerrada y de ninguna otra palabra: «resuelto» (el \
asunto se cerró: se firmó, se votó, se decidió, se descartó o se desmintió) · \
«avanzo» (hubo un paso concreto y verificable, con fecha y fuente, y sigue \
abierto) · «complicado» (apareció un revés, un obstáculo o una contradicción) · \
«igual» (hubo conversación pero ningún hecho nuevo) · «sin_dato» (la evidencia no \
permite saberlo). Sé estricto: más titulares sobre lo mismo NO es avance; una \
declaración no es una decisión; un orden del día no es una votación. Si el tema \
no tiene evidencia en la semana, es «sin_dato» y lo dices con esas palabras y \
con hasta dónde llega el registro. Si algo que el lunes se dio por cierto resultó \
distinto —una cifra que nadie confirmó, una fecha que cambió—, dilo de frente: \
corregir al lunes es parte del trabajo y es lo que hace confiable al viernes. No \
repitas lo que dijo el lunes: el documento lo cita al lado; escribe solo lo que \
pasó después.""",
    """LO DEMÁS DE LA SEMANA. Entre dos y cinco temas: lo que más le mueve la aguja \
de lo que pasó en la semana y que NO es seguimiento de los temas del lunes. \
Pueden ser temas que el lunes trajo más abajo, si en la semana se movieron. Mismo \
formato del lunes: qué pasó, por qué le importa a este cliente y qué hacer. \
Descarta sin piedad: el volumen no es virtud.""",
    """EL LUNES. Cierras con UNA cosa: en qué enfocarse al arrancar la semana, por \
qué esa y no otra, y qué hay que tener listo. Sale de lo que viene (una sesión \
citada, un plazo, el cierre de una consulta, una fecha que el Gobierno se fijó) \
o de un tema que quedó abierto. Nunca de una predicción. Si la ficha trae un \
entregable o un plazo propio del lunes, el foco se mide contra ese reloj.""",
    """LA AGENDA. Solo lo que viene: de mañana en adelante, con la próxima semana \
primero. Las sesiones de esta semana vienen marcadas YA PASÓ: dicen qué estuvo \
en el orden del día, NO qué se votó; nunca afirmes un resultado a partir de un \
orden del día. Si la próxima semana no trae órdenes del día publicados, no \
inventes sesiones: dilo en «qué no se movió».""",
    _parrafo(BRIEF_SYSTEM, 'LO QUE NO SABEMOS SE DICE.'),
    _parrafo(BRIEF_SYSTEM, 'LAS REDES.'),
    _parrafo(BRIEF_SYSTEM, 'LO QUE ESTÁ FUERA DE ALCANCE.'),
    _parrafo(BRIEF_SYSTEM, 'LAS FECHAS.'),
    _parrafo(BRIEF_SYSTEM, 'TONO.'),
    """DEVUELVES SIEMPRE UN JSON VÁLIDO con esta forma:
{
  "titular": "una frase que diga cómo cerró la semana, con el hecho concreto \
adentro; no un rótulo temático",
  "bajada": "dos frases: qué cubre este brief y con qué corte",
  "lectura": {
    "titulo": "el balance de la semana en una frase",
    "parrafos": ["1 o 2 párrafos: cómo cambió el panorama del lunes al viernes"]
  },
  "seguimiento": [
    {
      "n": "el número del tema del lunes (1, 2, 3…), tal como te lo paso",
      "estado": "resuelto | avanzo | complicado | igual | sin_dato",
      "titulo": "cómo terminó, en una frase con el hecho adentro",
      "parrafos": ["1 o 2 párrafos con los hechos de la semana: fechas, cifras, quién"],
      "que_sigue": "qué queda abierto y qué hacer, con plazo si la evidencia lo trae"
    }
  ],
  "temas": [
    {
      "rotulo": "área o frente, dos o tres palabras",
      "linea": "la línea de negocio del cliente que toca, si la ficha la trae; si no, cadena vacía",
      "titulo": "el hallazgo del tema en una frase con el hecho adentro",
      "parrafos": ["1 o 2 párrafos con los datos duros"],
      "por_que": "por qué le importa a ESTE cliente, en sus términos",
      "que_hacer": "la acción concreta, con plazo si la evidencia lo trae",
      "urgencia": "alta | media | baja"
    }
  ],
  "lunes": {
    "foco": "en qué enfocarse el lunes, en una frase con el hecho adentro",
    "por_que": "por qué eso y no otra cosa",
    "preparar": ["dos o tres cosas concretas que hay que tener listas el lunes"]
  },
  "agenda": [{"iso": "AAAA-MM-DD de ese día", "cuando": "solo si NO es un día \
puntual (un rango, «la próxima semana»); si hay iso, déjalo vacío", "que": "qué pasa"}],
  "no_se_movio": [{"fuente": "nombre del pilar o la fuente", "estado": "qué se \
verificó y hasta qué fecha llega su registro"}]
}""",
])

# Cuánto entra de cada pilar en el cierre: cinco días traen más que tres, y la
# prensa del seguimiento va aparte, así que la prensa general puede ir un poco
# más corta que el lunes sin perder lo de la semana.
TOPES_CIERRE = dict(TOPES, medios=60, redes=16)
TOPE_SEGUIMIENTO = 28                    # titulares por tema del lunes


def armar_mensaje_cierre(b, temas_lunes, anterior):
    """Barrido de la semana + los temas del lunes → el mensaje del viernes.

    `temas_lunes` viene de cierre.temas_a_seguir (con sus `consultas`), y
    `anterior` es el brief del lunes completo.
    """
    v, ev = b['ventana'], b['evidencia']
    meta_ant = anterior.get('_meta') or {}
    f_ant = (meta_ant.get('ventana') or {}).get('hasta', '')
    L = _cabecera(b)
    L.append(f"\nVENTANA DEL BRIEF DE CIERRE: la semana del {v['desde']} al {v['hasta']}. "
             f"El brief que abrió la semana es del {f_ant}.")
    L += _kpis(b)

    L.append("\n### LOS TEMAS DEL LUNES QUE HAY QUE CERRAR (texto literal del brief "
             "del lunes; NO lo repitas, escribe cómo terminó cada uno)")
    for t in temas_lunes:
        L.append(f"TEMA {t['n']} · {t['rotulo']} · urgencia {t.get('urgencia') or '—'}")
        L.append(f"  El lunes dijo: {t['titulo']}")
        if t.get('que_hacer'):
            L.append(f"  El lunes recomendó: {t['que_hacer']}")
    ag = [x for x in (anterior.get('agenda') or []) if x.get('que')]
    if ag:
        L.append("\nLO QUE EL LUNES PUSO EN AGENDA (compara: ¿esas fechas ya pasaron, "
                 "se cumplieron, se movieron?):")
        for x in ag:
            L.append(f"  - {x.get('iso') or x.get('cuando') or 's/f'}: {x.get('que')}")
    nm = [x for x in (anterior.get('no_se_movio') or []) if x.get('estado')]
    if nm:
        L.append("\nLO QUE EL LUNES DIJO QUE NO TENÍA VERIFICADO (si en la semana se "
                 "verificó, dilo; las fechas de registro de abajo son las de HOY y "
                 "reemplazan las del lunes: nunca repitas un atraso que ya se superó):")
        for x in nm:
            L.append(f"  - {x.get('fuente')}: {x.get('estado')[:260]}")

    L += _registros(b)

    # La prensa del seguimiento, agrupada por tema del lunes. El origen de cada
    # nota es «seguimiento::N::consulta» (ver cierre.jobs_seguimiento).
    medios = ev.get('medios') or []
    for t in temas_lunes:
        pre = f"seguimiento::{t['n']}::"
        xs = [x for x in medios if (x.get('_origen') or '').startswith(pre)]
        L.append(f"\n### SEGUIMIENTO · TEMA {t['n']} · {t['rotulo']} · búsquedas: "
                 f"{', '.join(t.get('consultas') or [])} · {len(xs)} titulares de la semana")
        if not xs:
            L.append("  (ningún titular de la semana en estas búsquedas: puede que el "
                     "tema se haya movido por otra vía; revisa el resto de la evidencia "
                     "antes de concluir «sin_dato»)")
        for x in _recorte('medios', xs, TOPE_SEGUIMIENTO):
            L.append('  ' + _fmt_item('medios', x))
        if len(xs) > TOPE_SEGUIMIENTO:
            L.append(f"  … y {len(xs) - TOPE_SEGUIMIENTO} más")

    # El resto de la semana: los mismos pilares del lunes, sin la prensa que ya
    # entró como seguimiento (repetirla gasta contexto y empuja al modelo a
    # contar lo mismo dos veces, una en «cómo terminó» y otra en «lo demás»).
    resto = dict(b, evidencia=dict(ev, medios=[
        x for x in medios if not (x.get('_origen') or '').startswith('seguimiento')]))
    titulos = dict(TITULOS,
                   congreso='CONGRESO · lo que se radicó o se movió en la semana',
                   medios='PRENSA · el resto de los titulares de la semana',
                   agenda='AGENDA · sesiones de la semana (YA PASÓ) y lo que viene '
                          '(órdenes del día ya publicados)')
    L += _pilares(resto, titulos, TOPES_CIERRE)
    L += _errores(b)
    L.append("\nEscribe el brief de cierre en JSON, siguiendo la forma que te di. "
             f"El campo «seguimiento» lleva exactamente {len(temas_lunes)} entradas, "
             f"una por tema del lunes, con su número.")
    return '\n'.join(L)
