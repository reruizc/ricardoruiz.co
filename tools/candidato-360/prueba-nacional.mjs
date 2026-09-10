/* prueba-nacional.mjs — el top del país en la lectura de noticias.
   ------------------------------------------------------------------
   El panel abría con «lo que pasa en Bogotá». Faltaba lo de antes: la agenda
   nacional, la que todo el mundo comenta. No hay un «top» que pedirle a nadie
   —Google News entrega titulares por consulta, no un ranking—, así que se
   CALCULA: una historia importa cuando la publican muchos medios distintos.

   Acá se comprueba el cálculo, que es lo que puede mentir:
     · que agrupe los titulares que cuentan la misma historia aunque estén
       escritos distinto, y separe los que no;
     · que ordene por MEDIOS distintos y no por número de titulares: un portal
       que repite su nota cinco veces no es «de lo que habla todo el mundo»;
     · que lo que ya salió como suyo o como local no se repita arriba.

     node tools/candidato-360/prueba-nacional.mjs                              */
import { readFileSync } from 'node:fs';

globalThis.window = {};
globalThis.localStorage = { getItem: () => null, removeItem() {}, setItem() {} };
globalThis.document = { getElementById: () => null, querySelector: () => null, addEventListener() {} };
globalThis.location = { href: '', search: '' };
eval(readFileSync(new URL('../../candidato-360-panel.js', import.meta.url), 'utf8'));
const P = globalThis.window.C360Panel;

const fallos = []; let total = 0;
const revisar = (t, ok, d) => { total++; console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) { fallos.push(t); if (d) console.log('   ', d); } };

const it = (titulo, medio, fecha = '2026-09-10') => ({ titulo, medio, fecha, url: 'https://x/' + medio });
/* Una historia con mucha cobertura, otra con poca, y un portal que repite. */
const titulares = [
  it('Petro sanciona la reforma pensional en un acto en la Casa de Nariño', 'EL TIEMPO'),
  it('Presidente Petro sancionó la reforma pensional este miércoles', 'EL ESPECTADOR'),
  it('Reforma pensional sancionada por Petro: qué cambia para los cotizantes', 'SEMANA', '2026-09-11'),
  it('La reforma pensional quedó sancionada: los puntos clave', 'LA REPÚBLICA'),
  it('Selección Colombia venció a Perú en el estadio Metropolitano', 'GOL CARACOL'),
  it('Selección Colombia ganó a Perú: así quedó la tabla', 'GOL CARACOL', '2026-09-09'),
  it('Selección Colombia derrotó a Perú en Barranquilla', 'GOL CARACOL', '2026-09-08'),
  it('Selección Colombia y Perú: resumen del partido', 'GOL CARACOL', '2026-09-07'),
  it('Corte Constitucional tumbó el decreto de conmoción interior', 'BLU RADIO'),
  it('Cayó el decreto de conmoción interior en la Corte Constitucional', 'W RADIO'),
];
const g = P.agruparPorCobertura(titulares);
revisar('agrupa los titulares que cuentan la misma historia', g.length === 3, g.map(x => `${x.medios} medios · ${x.titulares} titulares · ${x.titular.titulo.slice(0, 40)}`).join(' | '));
revisar('la historia de cuatro medios va primero', g[0].medios === 4 && /reforma pensional/i.test(g[0].titular.titulo));
revisar('y manda el número de MEDIOS, no el de titulares: el portal que repite queda de último',
  g[1].medios === 2 && g[2].medios === 1 && g[2].titulares === 4, g.map(x => `${x.medios}/${x.titulares}`).join(' '));
revisar('de cada historia se muestra el titular más reciente', /qué cambia para los cotizantes/i.test(g[0].titular.titulo));
revisar('y guarda algunos de los otros para dar contexto', g[0].otros.length >= 2);
revisar('un titular sin palabras con sustancia no forma historia', P.agruparPorCobertura([it('Ya', 'X'), it('Hoy no', 'Y')]).length === 0);

/* Las consultas: anchas y del país, no de un tema que nosotros escojamos. */
const q = P.consultasNacionales();
revisar('las consultas nacionales son anchas y son tres', q.length === 3 && q.every(x => /^"/.test(x)));
revisar('preguntan por el país y sus ramas, no por un tema nuestro', q.join(' ').includes('Colombia') && q.join(' ').includes('Congreso'));

console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : `${total} de ${total} pasaron`);
process.exit(fallos.length ? 1 : 0);
