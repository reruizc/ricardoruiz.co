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

# ── el sistema: quién escribe, para quién y con qué reglas ─────────────────
BRIEF_SYSTEM = """Eres el analista de asuntos públicos que le escribe el brief a un cliente de \
Cauce. Escribes en español de Colombia, tuteo neutro de Bogotá: sin voseo, sin \
regionalismos, sin jerga de consultoría.

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
sección es parte del producto, no una disculpa.

LO QUE ESTÁ FUERA DE ALCANCE. Si el cliente opera en países donde no tenemos \
fuentes, no digas ni insinúes que allá no pasó nada: no lo sabemos, y hay que \
decirlo con esas palabras.

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
      "urgencia": "alta | media | baja"
    }
  ],
  "agenda": [{"cuando": "fecha o día", "que": "qué pasa ese día"}],
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
        return (f"- {x.get('fecha')} · {x.get('tipo')}: "
                f"{x.get('descripcion') or x.get('titulo', '')}"[:240] + o + ruido)
    if pilar == 'sucop':
        return (f"- {x.get('entidad')}: {x.get('titulo', '')[:180]} · "
                f"CIERRA {x.get('cierra')}" + o + ruido)
    if pilar == 'medios':
        return (f"- {x.get('fecha')} · {x.get('medio')}: {x.get('titulo', '')[:180]}"
                + o + ruido)
    if pilar == 'contratacion':
        return (f"- {x.get('fecha')} · {x.get('entidad')} → {x.get('proveedor')}: "
                f"{x.get('objeto', '')[:150]}" + o + ruido)
    if pilar == 'agenda':
        return (f"- {x.get('fecha')} · {x.get('corporacion')} {x.get('ambito')}: "
                + '; '.join(f'{n} {t}' for n, t in (x.get('proyectos') or [])))
    return '- ' + str(x)[:200]


# Cuánto de cada pilar entra al mensaje. El frente vigente va corto a propósito:
# es contexto, no noticia, y dejarlo crecer haría que el brief hablara de 2012.
TOPES = {'congreso': 30, 'congreso_frente': 14, 'regulatorio': 25,
         'ejecutivo': 20, 'sucop': 20, 'medios': 70, 'contratacion': 12,
         'agenda': 12}

TITULOS = {
    'congreso': 'CONGRESO · lo que se movió en la ventana',
    'congreso_frente': 'CONGRESO · vigente pero SIN movimiento en la ventana '
                       '(contexto, NO es novedad)',
    'regulatorio': 'REGULADORES · actos en la ventana',
    'ejecutivo': 'EJECUTIVO · normativa en la ventana',
    'sucop': 'CONSULTA PÚBLICA DE NORMAS · abiertas, con su fecha de cierre',
    'medios': 'PRENSA · titulares de la ventana',
    'contratacion': 'CONTRATACIÓN · contratos de sus vigiladas',
    'agenda': 'AGENDA · lo que viene (órdenes del día ya publicadas)',
}


def armar_mensaje(b):
    """Barrido → el mensaje de usuario que se le manda al modelo."""
    p, v, ev = b['perfil'], b['ventana'], b['evidencia']
    cob = b.get('cobertura') or {}
    L = [f"CLIENTE: {p.get('nombre')}"]
    L += ['  · ' + x for x in _lineas_ficha(p)]
    L.append(f"\nVENTANA DEL BRIEF: últimas {v.get('dias_prensa', 3) * 24} horas "
             f"({v['desde']} → {v['hasta']}).")

    k = b.get('kpis') or {}
    if k:
        L.append(f"El radar priorizó {k.get('n_radar', 0)} señales "
                 f"({k.get('alto', 0)} de prioridad alta) y hay "
                 f"{k.get('en_tramite', 0)} proyectos de ley en trámite activo "
                 f"sobre sus temas.")

    L.append("\nHASTA DÓNDE LLEGA CADA REGISTRO (úsalo para «qué no se movió»; "
             "un pilar vacío con registro atrasado NO es lo mismo que quietud):")
    for pilar, f in sorted(cob.items()):
        L.append(f"  · {pilar}: el registro llega hasta {f}")

    for pilar, titulo in TITULOS.items():
        xs = ev.get(pilar) or []
        L.append(f"\n### {titulo} · {len(xs)}")
        if not xs:
            f = cob.get(pilar)
            L.append("  (sin ítems en la ventana"
                     + (f"; el registro llega hasta {f})" if f else ")"))
            continue
        for x in xs[:TOPES.get(pilar, 20)]:
            L.append('  ' + _fmt_item(pilar, x))
        if len(xs) > TOPES.get(pilar, 20):
            L.append(f"  … y {len(xs) - TOPES.get(pilar, 20)} más del mismo pilar")

    if ev.get('errores'):
        L.append("\n### CONSULTAS QUE FALLARON (no asumas que están vacías)")
        for e in ev['errores'][:8]:
            L.append(f"  - {e['consulta']}: {e['error']}")

    L.append("\nEscribe el brief en JSON, siguiendo la forma que te di.")
    return '\n'.join(L)
