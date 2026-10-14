"""
gate_tableros.py — aplica la regla de gate de oct-2026 al chasis de los tableros
territoriales (resultados-{jal,concejo,asamblea}-{año}.html):

    HASTA PUESTO PARA TODOS (incluidos anónimos) · MESA SOLO CON CUENTA (gratis)
    · el mapa de barrios sigue en Pro.

Además cambia los rótulos de candado escritos a mano («Pro»/«Premium») por
`gateTag(feat)`, que los deriva de GATE_FEATURES. Es idempotente: una página que
ya trae `gateTag(` se deja igual.

    python3 tools/analisis-candidato/gate_tableros.py resultados-jal-2019.html …
"""
import sys

def rep(s, a, b, n=1):
    c = s.count(a)
    if c != n:
        raise SystemExit(f'esperaba {n} y hay {c}: {a[:90]!r}')
    return s.replace(a, b)

def aplicar(s):
    if 'function gateTag(' in s:
        return s
    s = rep(s, '''    // ─── GATE POR PLAN ────────────────────────────────────────
    // Abierto: mapa de ciudad, grid de comunas y quién ganó (es el dato público).
    // De pago: el desagregado fino (barrio · puesto · mesa), que es el trabajo propio.
    // Un anónimo puede abrir UNA comuna de muestra antes de que le pidamos cuenta.
    window.GATE_FEATURES={
      plan:{ 'drill':'free', 'barrios':'pro', 'puestos':'pro', 'mesas':'premium' },''',
    '''    // ─── GATE POR PLAN ────────────────────────────────────────
    // Regla general (oct-2026): HASTA PUESTO PARA TODOS, incluidos anónimos;
    // MESA SOLO CON CUENTA (gratis). El mapa de barrios sigue en Pro.
    // 'anonymous' es el rango 0 de PlanGate: abierto a cualquiera.
    window.GATE_FEATURES={
      plan:{ 'drill':'anonymous', 'barrios':'pro', 'puestos':'anonymous', 'mesas':'free' },''')
    s = rep(s, '''          desc:`El detalle mesa a mesa —la unidad más fina del escrutinio— está en Premium.` },
      },
    };''', '''          desc:`El detalle mesa a mesa —la unidad más fina del escrutinio— es gratis: solo necesitas una cuenta.` },
      },
    };
    // Rótulo del candado según el plan que pide cada función (sale de GATE_FEATURES,
    // no se escribe a mano: así el rótulo no se queda atrás si cambia la regla).
    function gateTag(feat){
      const p=PlanGate.planFor(feat);
      return p==='premium'?'Premium':p==='pro'?'Pro':'Cuenta gratis';
    }''')
    s = rep(s, '''Puestos${PlanGate.has('puestos')?'':' <span class="pg-lock">Pro</span>'}</button>''',
               '''Puestos${PlanGate.has('puestos')?'':` <span class="pg-lock">${gateTag('puestos')}</span>`}</button>''')
    s = rep(s, '''Mesas${PlanGate.has('mesas')?'':' <span class="pg-lock">Premium</span>'}</button>''',
               '''Mesas${PlanGate.has('mesas')?'':` <span class="pg-lock">${gateTag('mesas')}</span>`}</button>''')
    s = rep(s, '''+(ok?'':` <span class="pg-lock">${v==='mesas'?'Premium':'Pro'}</span>`);''',
               '''+(ok?'':` <span class="pg-lock">${gateTag(v)}</span>`);''')
    s = rep(s, '''<span class="lock-hint"><span class="pg-lock">Pro</span> ${barrios.length} barrios''',
               '''<span class="lock-hint"><span class="pg-lock">${gateTag('barrios')}</span> ${barrios.length} barrios''')
    s = rep(s, '''      const need=PlanGate.planFor(feat)==='premium'?'Premium':'Pro';''',
               '''      const need=gateTag(feat);''')
    s = rep(s, '''<button class="pgc-btn" onclick="PlanGate.open('${feat}')">Desbloquear con ${need}</button>''',
               '''<button class="pgc-btn" onclick="PlanGate.open('${feat}')">${need==='Cuenta gratis'?'Entra o crea tu cuenta gratis':'Desbloquear con '+need}</button>''')
    s = rep(s, '''ver ${p.mesas.length} mesas${PlanGate.has('mesas')?'':' <span class="pg-lock">Premium</span>'}</button>''',
               '''ver ${p.mesas.length} mesas${PlanGate.has('mesas')?'':` <span class="pg-lock">${gateTag('mesas')}</span>`}</button>''')
    s = rep(s, '''      // anónimo: una comuna de muestra y luego cuenta gratis''',
               '''      // 'drill' está abierto a todos (rango anonymous): no gasta muestras''')
    import re
    s, k = re.subn(r"    // Corporación de esta página\. .*\n    // con otro CORP \+ otro hero: si tocas la lógica, tócala en (?:los dos|las tres)\.\n",
        "    // Corporación de esta página. Hay SEIS copias de este chasis:\n"
        "    // resultados-{jal,concejo,asamblea}-{2019,2023}.html. Solo cambian CORP y el\n"
        "    // hero/pie: si tocas la lógica, tócala en las seis.\n", s)
    if k != 1:
        raise SystemExit(f'comentario de CORP: {k} coincidencias')
    return s

if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(aplicar(s))
        print('ok', p)
