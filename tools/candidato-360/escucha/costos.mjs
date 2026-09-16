/* costos.mjs — qué cuesta escuchar a un candidato, y qué se le puede cobrar.
   ------------------------------------------------------------------
   El precio de venta de Candidato 360 sale de esta cuenta, así que la cuenta
   se escribe y no se hace de memoria.

   El perfil vive en perfil.mjs, compartido con el medidor. Los precios por red
   salen de `precios-medidos.json` si medir.mjs ya corrió contra Apify; si no,
   de los precios de referencia —que sirven para dimensionar y NO para fijar
   tarifa—. La salida dice siempre cuál de los dos está usando, porque una
   tarifa puesta sobre estimaciones de terceros es una tarifa inventada.

     node tools/candidato-360/escucha/costos.mjs
     node tools/candidato-360/escucha/costos.mjs --corridas=1 --trm=3200       */

import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PERFIL, PRECIOS_REFERENCIA, plan } from './perfil.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], Number(m[2])] : [a.replace(/^--/, ''), true]; }));
const TRM = args.trm || 3109.30;                          /* Banco de la República · 15-sep-2026 */
const CORRIDAS_DIA = args.corridas || PERFIL.corridasDia;
const DIAS = args.dias || PERFIL.dias;
const CORRIDAS = CORRIDAS_DIA * DIAS;

/* DeepSeek V4 Flash, tarifa FUERA DE PICO (US$ por millón de tokens). El pico
   es 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes = 20:00-23:00 y
   01:00-05:00 en Colombia. Corriendo a las 6 a. m. y 6 p. m. hora local
   (11:00 y 23:00 UTC) las dos lecturas caen fuera de pico: la mitad de tarifa
   por no hacer nada. */
const MODELO = { entrada: 0.15, entradaCache: 0.003, salida: 0.60, sistema: 1500, tokensPorItem: 60, salidaPorCorrida: 900 };
const INFRA = 0.10;   /* el worker y el KV ya están y son compartidos; S3 ~30 MB/mes */

/* ── ¿Medido o estimado? ─────────────────────────────────────────────────── */
const rutaMedidos = path.join(AQUI, 'precios-medidos.json');
const MEDIDOS = existsSync(rutaMedidos) ? (JSON.parse(readFileSync(rutaMedidos, 'utf8')).medidos || {}) : {};
const hayMedidos = Object.keys(MEDIDOS).length > 0;

const fmtUSD = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtCOP = n => '$' + Math.round(n).toLocaleString('es-CO');
const pad = (s, n, d = 'izq') => d === 'izq' ? String(s).padEnd(n) : String(s).padStart(n);

/* ── Volumen y costo ─────────────────────────────────────────────────────── */
const filas = plan(PERFIL).map(f => {
  const mes = f.porCorrida * CORRIDAS, ref = PRECIOS_REFERENCIA[f.red], med = MEDIDOS[f.red];
  const precio = { bajo: ref.bajo, base: med ? med.base : ref.base, alto: ref.alto, medido: Boolean(med) };
  return { ...f, mes, precio, bajo: mes / 1000 * precio.bajo, base: mes / 1000 * precio.base, alto: mes / 1000 * precio.alto };
});
const itemsCorrida = filas.reduce((s, f) => s + f.porCorrida, 0), itemsMes = itemsCorrida * CORRIDAS;
const apify = ['bajo', 'base', 'alto'].reduce((o, k) => (o[k] = filas.reduce((s, f) => s + f[k], 0), o), {});
const costoModelo = (itemsMes * MODELO.tokensPorItem) / 1e6 * MODELO.entrada
  + (MODELO.sistema * CORRIDAS) / 1e6 * MODELO.entradaCache
  + (MODELO.salidaPorCorrida * CORRIDAS) / 1e6 * MODELO.salida;

console.log(`\n═══ ESCUCHA SOCIAL · costo por candidato y mes ═══`);
console.log(`${PERFIL.candidato} · ${PERFIL.temas.length} temas · ${PERFIL.ciudad} + ${PERFIL.localidad} · ${CORRIDAS_DIA} lecturas/día × ${DIAS} días = ${CORRIDAS} corridas`);
console.log(hayMedidos
  ? `Precios MEDIDOS contra Apify (${Object.keys(MEDIDOS).join(', ')}); el resto, de referencia.\n`
  : `⚠ Precios DE REFERENCIA (páginas de terceros, sep-2026). Corra medir.mjs antes de fijar tarifa.\n`);

console.log(pad('RED', 11) + pad('CÓMO BUSCA', 22) + pad('CONS.', 6, 'der') + pad('TOPE', 6, 'der') + pad('/CORRIDA', 10, 'der') + pad('/MES', 9, 'der') + pad('US$/1K', 9, 'der') + pad('BAJO', 9, 'der') + pad('BASE', 9, 'der') + pad('ALTO', 9, 'der'));
console.log('─'.repeat(100));
for (const f of filas) console.log(pad(f.red, 11) + pad(f.modo, 22) + pad(f.consultas.length, 6, 'der') + pad(f.tope, 6, 'der') + pad(f.porCorrida, 10, 'der') + pad(f.mes.toLocaleString('es-CO'), 9, 'der') + pad((f.precio.medido ? '' : '~') + f.precio.base.toFixed(3), 9, 'der') + pad(fmtUSD(f.bajo), 9, 'der') + pad(fmtUSD(f.base), 9, 'der') + pad(fmtUSD(f.alto), 9, 'der'));
console.log('─'.repeat(100));
console.log(pad('APIFY', 45) + pad(itemsCorrida, 10, 'der') + pad(itemsMes.toLocaleString('es-CO'), 9, 'der') + pad('', 9) + pad(fmtUSD(apify.bajo), 9, 'der') + pad(fmtUSD(apify.base), 9, 'der') + pad(fmtUSD(apify.alto), 9, 'der'));
console.log(`\nDeepSeek V4 Flash, fuera de pico  ${pad(fmtUSD(costoModelo), 9, 'der')}`);
console.log(`Infraestructura (marginal)        ${pad(fmtUSD(INFRA), 9, 'der')}`);

for (const k of ['bajo', 'base', 'alto']) {
  const t = apify[k] + costoModelo + INFRA;
  console.log(`\n▸ COSTO MARGINAL (${k.padEnd(4)})  ${fmtUSD(t)} /mes  =  ${fmtCOP(t * TRM)} COP   ·   por lectura: ${fmtUSD(t / CORRIDAS)}`);
}

console.log(`\n═══ EL ESCALÓN DE APIFY ═══   (el plan no es cuota: es crédito prepago que el uso consume)`);
for (const [plan_, precio, credito] of [['Free', 0, 5], ['Starter', 29, 29], ['Scale', 199, 199], ['Business', 999, 999]])
  console.log(`  ${pad(plan_, 10)} ${pad(fmtUSD(precio) + '/mes', 12, 'der')}  crédito ${pad(fmtUSD(credito), 9, 'der')}  →  ${pad(Math.floor(credito / apify.base), 3, 'der')} candidatos antes del sobrecosto`);

console.log(`\n═══ QUÉ COBRAR ═══  (TRM ${fmtCOP(TRM)})`);
console.log(pad('', 34) + pad('COSTO', 12, 'der') + pad('PRECIO', 14, 'der') + pad('MARGEN', 12, 'der') + pad('MÚLTIPLO', 10, 'der'));
console.log('─'.repeat(82));
const costoBase = apify.base + costoModelo + INFRA;
for (const [nombre, cop, costoUSD] of [
  ['Escucha sola (add-on)', 89000, costoBase],
  ['C360 + escucha, 1 lectura/día', 249000, apify.base / 2 + costoModelo / 2 + INFRA],
  ['C360 + escucha, 2 lecturas/día', 299000, costoBase],
  ['Campaña (3 temas, sin topes)', 449000, costoBase * 2.2],
]) {
  const c = costoUSD * TRM;
  console.log(pad(nombre, 34) + pad(fmtCOP(c), 12, 'der') + pad(fmtCOP(cop), 14, 'der') + pad(fmtCOP(cop - c), 12, 'der') + pad((cop / c).toFixed(1) + '×', 10, 'der'));
}
console.log('');
