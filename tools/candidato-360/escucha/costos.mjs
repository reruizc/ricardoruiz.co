/* costos.mjs — qué cuesta escuchar a un candidato, y qué se le puede cobrar.
   ------------------------------------------------------------------
   El perfil que lo motivó: un aspirante a la JAL de Tunjuelito con DOS temas
   de campaña, escucha en X, Instagram, TikTok y Facebook, dos lecturas al día,
   a escala de Bogotá y de su localidad.

   La cuenta no se hace de memoria porque el precio de venta sale de acá. Los
   topes de abajo son la ÚNICA palanca real: Apify cobra por resultado
   entregado, así que el costo es `tope × consultas × corridas`, no «lo que
   traiga». Súbalos y el margen se va; bájelos y la escucha se vuelve ciega.

   ⚠️ Los precios por actor son de septiembre de 2026 y hay que confirmarlos en
   la consola de Apify antes de fijar tarifa: el catálogo se mueve y cada actor
   pone su propio precio. Las fuentes están en PRECIOS.

     node tools/candidato-360/escucha/costos.mjs
     node tools/candidato-360/escucha/costos.mjs --corridas=1 --trm=3200        */

const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], Number(m[2])] : [a.replace(/^--/, ''), true]; }));
const TRM = args.trm || 3109.30;          /* Banco de la República · 15-sep-2026 */
const CORRIDAS_DIA = args.corridas || 2;  /* «dos veces al día» */
const DIAS = args.dias || 30;
const CORRIDAS = CORRIDAS_DIA * DIAS;
const TEMAS = args.temas || 2;            /* sus dos intereses de campaña */
const ESCALAS = 2;                        /* Bogotá y Tunjuelito */

/* ── Qué se pide en CADA corrida ─────────────────────────────────────────────
   Solo X tiene búsqueda por palabra de verdad. En Instagram y TikTok se busca
   por hashtag —que no es lo mismo— y en Facebook por página. Eso no cambia el
   costo pero sí lo que se puede prometer, y va dicho en la salida.            */
const RED = {
  x:         { consultas: TEMAS * ESCALAS + 1, tope: 50, propio: 20, modo: 'búsqueda por palabra' },
  instagram: { consultas: TEMAS + ESCALAS,     tope: 20, propio: 12, modo: 'hashtag' },
  tiktok:    { consultas: TEMAS + ESCALAS,     tope: 15, propio: 10, modo: 'hashtag' },
  facebook:  { consultas: 6,                   tope: 15, propio: 10, modo: 'páginas seguidas' },
};
/* US$ por 1.000 resultados entregados. bajo = el actor más barato que vimos;
   base = el que ya usamos o el de precio mediano; alto = el de marca. */
const PRECIOS = {
  x:         { bajo: 0.15, base: 0.25, alto: 0.40, nota: 'igolaizola/scrape.badger 0,15 · kaitoeasyapi 0,25 (el que ya usa radar-mujer) · apidojo/tweet-scraper 0,40' },
  instagram: { bajo: 0.30, base: 0.50, alto: 0.80, nota: 'apidojo/instagram-scraper y similares, ~0,50/1K posts' },
  tiktok:    { bajo: 0.30, base: 0.50, alto: 0.80, nota: 'clockworks/tiktok-scraper y similares, ~0,50/1K posts' },
  facebook:  { bajo: 0.70, base: 0.89, alto: 2.00, nota: 'dami_studio/seemuapps 0,70 · getanyapi 0,89 · alfalfa 2,00' },
};
/* DeepSeek V4 Flash, tarifa FUERA DE PICO (US$ por millón de tokens).
   El pico es 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes = 20:00-23:00 y
   01:00-05:00 en Colombia. Corriendo a las 6 a. m. y 6 p. m. hora local
   (11:00 y 23:00 UTC) las dos lecturas caen fuera de pico: la tarifa es la
   mitad por no hacer nada. */
const MODELO = { entrada: 0.15, entradaCache: 0.003, salida: 0.60, sistema: 1500, tokensPorItem: 60, salidaPorCorrida: 900 };

const fmtUSD = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtCOP = n => '$' + Math.round(n).toLocaleString('es-CO');
const pad = (s, n, dir = 'izq') => dir === 'izq' ? String(s).padEnd(n) : String(s).padStart(n);

/* ── Volumen ─────────────────────────────────────────────────────────────── */
const filas = Object.entries(RED).map(([red, r]) => {
  const porCorrida = r.consultas * r.tope + r.propio;
  const mes = porCorrida * CORRIDAS;
  const p = PRECIOS[red];
  return { red, modo: r.modo, consultas: r.consultas, tope: r.tope, porCorrida, mes,
    bajo: mes / 1000 * p.bajo, base: mes / 1000 * p.base, alto: mes / 1000 * p.alto };
});
const itemsCorrida = filas.reduce((s, f) => s + f.porCorrida, 0);
const itemsMes = itemsCorrida * CORRIDAS;
const apify = ['bajo', 'base', 'alto'].reduce((o, k) => (o[k] = filas.reduce((s, f) => s + f[k], 0), o), {});

/* ── Modelo ──────────────────────────────────────────────────────────────── */
const entradaMes = itemsMes * MODELO.tokensPorItem;
const sistemaMes = MODELO.sistema * CORRIDAS;
const salidaMes = MODELO.salidaPorCorrida * CORRIDAS;
const costoModelo = entradaMes / 1e6 * MODELO.entrada + sistemaMes / 1e6 * MODELO.entradaCache + salidaMes / 1e6 * MODELO.salida;
/* Cloudflare Workers de pago ya está y es compartido con Caudal, el Lab y
   Gastos: el cron y el KV de un candidato más no suben la factura. S3 guarda
   unos 30 MB al mes por candidato, que son centavos. */
const infra = 0.10;

console.log(`\n═══ ESCUCHA SOCIAL · costo por candidato y mes ═══`);
console.log(`Perfil: JAL de Tunjuelito · ${TEMAS} temas · Bogotá + localidad · ${CORRIDAS_DIA} lecturas/día × ${DIAS} días = ${CORRIDAS} corridas\n`);

console.log(pad('RED', 11) + pad('CÓMO BUSCA', 22) + pad('CONS.', 7, 'der') + pad('TOPE', 7, 'der') + pad('/CORRIDA', 10, 'der') + pad('/MES', 9, 'der') + pad('BAJO', 10, 'der') + pad('BASE', 10, 'der') + pad('ALTO', 10, 'der'));
console.log('─'.repeat(96));
for (const f of filas) console.log(pad(f.red, 11) + pad(f.modo, 22) + pad(f.consultas, 7, 'der') + pad(f.tope, 7, 'der') + pad(f.porCorrida, 10, 'der') + pad(f.mes.toLocaleString('es-CO'), 9, 'der') + pad(fmtUSD(f.bajo), 10, 'der') + pad(fmtUSD(f.base), 10, 'der') + pad(fmtUSD(f.alto), 10, 'der'));
console.log('─'.repeat(96));
console.log(pad('APIFY', 40) + pad('', 7) + pad(itemsCorrida, 10, 'der') + pad(itemsMes.toLocaleString('es-CO'), 9, 'der') + pad(fmtUSD(apify.bajo), 10, 'der') + pad(fmtUSD(apify.base), 10, 'der') + pad(fmtUSD(apify.alto), 10, 'der'));

console.log(`\nDeepSeek V4 Flash, fuera de pico  ${pad(fmtUSD(costoModelo), 10, 'der')}   (${(entradaMes / 1e6).toFixed(1)} M tokens de entrada, ${(salidaMes / 1e3).toFixed(0)} k de salida)`);
console.log(`Infraestructura (marginal)        ${pad(fmtUSD(infra), 10, 'der')}   worker y KV ya están; S3 ~30 MB/mes`);

for (const k of ['bajo', 'base', 'alto']) {
  const total = apify[k] + costoModelo + infra;
  console.log(`\n▸ COSTO MARGINAL (${k.padEnd(4)})  ${fmtUSD(total)} /mes  =  ${fmtCOP(total * TRM)} COP   ·   por lectura: ${fmtUSD(total / CORRIDAS)}`);
}

/* ── El escalón del plan ─────────────────────────────────────────────────── */
console.log(`\n═══ EL ESCALÓN DE APIFY ═══`);
console.log('El plan no es una cuota aparte: es crédito prepago que el uso consume.');
for (const [plan, precio, credito] of [['Free', 0, 5], ['Starter', 29, 29], ['Scale', 199, 199], ['Business', 999, 999]]) {
  const caben = Math.floor(credito / apify.base);
  console.log(`  ${pad(plan, 10)} ${pad(fmtUSD(precio) + '/mes', 12, 'der')}  crédito ${pad(fmtUSD(credito), 9, 'der')}  →  ${pad(caben, 3, 'der')} candidatos antes del sobrecosto`);
}

/* ── Precio de venta ─────────────────────────────────────────────────────── */
console.log(`\n═══ QUÉ COBRAR ═══  (TRM ${fmtCOP(TRM)})`);
console.log(pad('', 34) + pad('COSTO', 12, 'der') + pad('PRECIO', 14, 'der') + pad('MARGEN', 10, 'der') + pad('MÚLTIPLO', 10, 'der'));
console.log('─'.repeat(80));
const costoBase = apify.base + costoModelo + infra;
for (const [nombre, copPrecio, costoUSD] of [
  ['Escucha sola (add-on)', 89000, costoBase],
  ['C360 + escucha, 1 lectura/día', 249000, (apify.base / 2) + (costoModelo / 2) + infra],
  ['C360 + escucha, 2 lecturas/día', 299000, costoBase],
  ['Campaña (3 temas, sin topes)', 449000, costoBase * 2.2],
]) {
  const costoCOP = costoUSD * TRM, margen = copPrecio - costoCOP;
  console.log(pad(nombre, 34) + pad(fmtCOP(costoCOP), 12, 'der') + pad(fmtCOP(copPrecio), 14, 'der') + pad(fmtCOP(margen), 10, 'der') + pad((copPrecio / costoCOP).toFixed(1) + '×', 10, 'der'));
}
console.log('');
