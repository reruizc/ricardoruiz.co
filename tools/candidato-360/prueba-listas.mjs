/* prueba-listas.mjs — el voto de LISTA, las listas cerradas y la curul de
   oposición en el cálculo de la meta.
   ------------------------------------------------------------------------
   El modelo repartía las curules mirando solo el voto PERSONAL de cada
   candidato. Con eso, en el Concejo de Bogotá 2023:

     · el Pacto Histórico —lista cerrada, 376.733 votos y 7 curules— no
       existía, y sus 7 curules se les regalaban a las demás listas;
     · se repartían 45 curules cuando por cifra repartidora van 44 (la otra es
       del segundo de la alcaldía, por el estatuto de oposición);
     · el «corte» resultante era el tercero de LARA con 6.314 votos, cuando el
       concejal que entró con menos votos personales fue el octavo del Nuevo
       Liberalismo con 9.320.

   Acá se comprueba, con datos de mentiras pero con la misma forma que los
   reales, que cada una de esas tres cosas quedó bien, y que sin partido la
   meta ya no es el piso de la corporación (que casi siempre paga el último de
   la lista más grande, que entró de arrastre) sino lo que costó entrar por una
   lista típica, o por una de la familia política de quien pregunta.

     node tools/candidato-360/prueba-listas.mjs                              */
import fs from 'node:fs';
import vm from 'node:vm';

const ctx = { console, URL, setTimeout };
ctx.window = ctx;
/* El sitio sirve el voto de lista de todo el país aparte, mientras los índices
   de S3 no lo traigan. */
ctx.LISTAS_2023_URL = 'listas-de-prueba';
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('partidos-bloques.js', 'utf8'), ctx);
vm.runInContext(fs.readFileSync('vote-target.js', 'utf8'), ctx);

/* Un concejo de mentiras con la forma del de Bogotá: 5 curules (4 por cifra
   repartidora + 1 de oposición). Una lista cerrada de izquierda, dos abiertas.
   Voto personal: GRANDE 30.000 · MEDIANA 12.000 · CERRADA 0.
   Voto de lista:  GRANDE  6.000 · MEDIANA  2.000 · CERRADA 26.000.
   Totales:        GRANDE 36.000 · MEDIANA 14.000 · CERRADA 26.000.
   Cifra repartidora sobre 4 curules: 36.000/1, 26.000/1, 36.000/2 = 18.000 y
   14.000/1 → la cuarta es 14.000. GRANDE 2, CERRADA 1, MEDIANA 1. */
const cand = (partido, votos) => votos.map((v, i) => ({ nombre: `${partido} ${i + 1}`, slug: `${partido}-${i}`, circunscripcion: 'CIUDAD DE PRUEBA', partido, votos: v }));
const CANDIDATOS = [
  ...cand('PARTIDO CONSERVADOR COLOMBIANO', [15000, 9000, 4000, 2000, 0]),   // GRANDE, derecha
  ...cand('PARTIDO ALIANZA VERDE', [7000, 3000, 1500, 500, 0]),              // MEDIANA, centro-izquierda
];
const LISTAS = [
  { circunscripcion: 'CIUDAD DE PRUEBA', partido: 'PARTIDO CONSERVADOR COLOMBIANO', lista: 6000, personal: 30000, total: 36000, cerrada: false },
  { circunscripcion: 'CIUDAD DE PRUEBA', partido: 'PARTIDO ALIANZA VERDE', lista: 2000, personal: 12000, total: 14000, cerrada: false },
  { circunscripcion: 'CIUDAD DE PRUEBA', partido: 'PACTO HISTÓRICO', lista: 26000, personal: 0, total: 26000, cerrada: true },
];
const INDICE = { candidatos: CANDIDATOS, listas: LISTAS };
/* El mismo índice sin `listas`: es el que está hoy en S3. */
const INDICE_VIEJO = { candidatos: CANDIDATOS };
const RESULTADOS = { cities: [{ key: '99-001', name: 'CIUDAD DE PRUEBA', dep: 'PRUEBA', potencial: 200000 }],
  data: { '99-001': { comunas: { '01': { name: 'UNA', votantes: 80000, validos: 76000, blanco: 4000 } } } } };

/* El archivo compacto del sitio: los mismos números, sin los candidatos, con
   los nombres internados. Acá trae la misma ciudad que `LISTAS`, para poder
   comprobar que por los dos caminos se llega al mismo reparto. */
const PAIS = { v: 'prueba', corps: { concejo: {
  circ: ['CIUDAD DE PRUEBA'],
  part: ['PARTIDO CONSERVADOR COLOMBIANO', 'PARTIDO ALIANZA VERDE', 'PACTO HISTÓRICO'],
  listas: [[0, 0, 6000, 30000, 0], [0, 1, 2000, 12000, 0], [0, 2, 26000, 0, 1]],
} } };
ctx.fetch = async url => {
  const body = url === 'listas-de-prueba' ? PAIS
    : url.includes('index-concejo') ? (url.includes('/viejo/') ? INDICE_VIEJO : INDICE)
      : url.includes('resultados-concejo') ? RESULTADOS
        : null;
  return body ? { ok: true, json: async () => body } : { ok: false, status: 404, json: async () => ({}) };
};

const estimar = (extra = {}) => ctx.VoteTarget.estimate(Object.assign({ corp: 'concejo', territory: 'CIUDAD DE PRUEBA', baseUrl: 'https://stub/output' }, extra));

const sinPartido = await estimar();
const conCerrada = await estimar({ partido: 'PACTO HISTÓRICO' });
const conGrande = await estimar({ partido: 'PARTIDO CONSERVADOR COLOMBIANO' });
const conMediana = await estimar({ partido: 'PARTIDO ALIANZA VERDE' });
const famDerecha = await estimar({ bloque: 'cd' });
const famCentroIzq = await estimar({ bloque: 'ci' });
/* El mismo cálculo contra el índice de hoy (sin `listas`), que es el que cae al
   archivo del sitio. Va por otra URL porque VoteTarget memoiza cada fuente por
   su dirección. */
const porElArchivo = await estimar({ baseUrl: 'https://stub/viejo/output' });

const R = sinPartido.detalle.referencia, rep = sinPartido.detalle.reparto;
const cerradaRef = conCerrada.detalle.partido, archivoRep = porElArchivo.detalle.reparto;
const listasDe = r => (r.detalle.reparto.listas || []).map(l => `${l.partido}=${l.votos}(${l.k})`).sort().join(' ');

const pruebas = [
  ['el voto de lista cuenta: la lista cerrada aparece en el reparto con sus curules',
    rep.cerradas.length === 1 && rep.cerradas[0].partido === 'PACTO HISTÓRICO' && rep.cerradas[0].k === 1 && rep.cerradas[0].total === 26000],
  ['y el índice dice que trae el voto de lista', rep.conListas === true],
  ['una curul es del estatuto de oposición: se reparten 4 de 5',
    rep.curules === 5 && rep.porRepartidora === 4 && rep.oposicion === 1],
  ['la cifra repartidora es la del cuarto cociente (14.000)', rep.cifra === 14000],
  ['las curules quedan 2 GRANDE · 1 MEDIANA · 1 CERRADA',
    listasDe(sinPartido) === 'PARTIDO ALIANZA VERDE=7000(1) PARTIDO CONSERVADOR COLOMBIANO=9000(2)' && rep.cerradas[0].k === 1],
  ['sin partido la meta NO es el piso (7.000) sino la lista típica: mediana de 9.000 y 7.000',
    R.tipo === 'mediana-listas' && R.votos === 8000 && R.piso === 7000 && R.listas === 2],
  ['y la frase lo dice, con el piso aparte',
    /lista típica en 2023/.test(sinPartido.formula) && /es solo el piso/.test(sinPartido.formula)],
  ['con familia política, la referencia es la de las listas de esa familia (centro-derecha: 9.000)',
    famDerecha.detalle.referencia.tipo === 'mediana-bloque' && famDerecha.detalle.referencia.votos === 9000 && famDerecha.detalle.referencia.listas === 1],
  ['y el centro-izquierda tiene la suya (7.000), más barata',
    famCentroIzq.detalle.referencia.tipo === 'mediana-bloque' && famCentroIzq.detalle.referencia.votos === 7000 && famCentroIzq.target < famDerecha.target],
  ['por una lista CERRADA no se compite con votos personales: se dice y no se inventa un corte',
    cerradaRef.tipo === 'lista-cerrada' && cerradaRef.k === 1 && cerradaRef.porCurul === 14000 && /lista CERRADA/.test(conCerrada.formula) && /renglón/.test(conCerrada.formula)],
  ['por la lista grande hay que entrar de 2: 9.000', conGrande.detalle.partido.tipo === 'lista-con-curul' && conGrande.detalle.partido.k === 2 && conGrande.detalle.referencia.votos === 9000],
  ['por la mediana hay que ser primero: 7.000', conMediana.detalle.partido.k === 1 && conMediana.detalle.referencia.votos === 7000],
  ['el voto en blanco cuenta para el umbral del 50 % del cuociente', rep.umbral === Math.round((36000 + 14000 + 26000 + 4000) / 5 / 2)],
  ['sin `listas` en el índice, el voto de lista se toma del archivo del sitio',
    archivoRep.conListas === true && archivoRep.cerradas.length === 1 && archivoRep.cerradas[0].partido === 'PACTO HISTÓRICO'],
  ['y por ese camino el reparto es el mismo que con el índice completo',
    listasDe(porElArchivo) === listasDe(sinPartido) && porElArchivo.target === sinPartido.target],
];

for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify({ R, rep, cerradaRef, archivoRep, famDerecha: famDerecha.detalle.referencia, famCentroIzq: famCentroIzq.detalle.referencia }, null, 1).slice(0, 2000));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
