/* costos.mjs — qué cuesta escuchar a un candidato, y qué se le puede cobrar.
   ------------------------------------------------------------------
   El precio de venta de Candidato 360 sale de esta cuenta, así que la cuenta
   se escribe y no se hace de memoria.

   El perfil sale del vínculo (perfil.mjs, compartido con el medidor). Los
   precios por red vienen de `precios-medidos.json` si medir.mjs ya corrió
   contra Apify; si no, de los precios de referencia —que sirven para
   dimensionar y NO para fijar tarifa—. La salida dice siempre cuál de los dos
   está usando.

   Dos capas, costeadas aparte porque se cobran aparte:
     1 · POSTS        lo que se dice: búsqueda por palabra, hashtag, páginas
     2 · COMENTARIOS  lo que se siente: las respuestas a los posts con más reacción

     node tools/candidato-360/escucha/costos.mjs
     node tools/candidato-360/escucha/costos.mjs --vinculo=v.json --corridas=1 --trm=3200 */

import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PRECIOS_REFERENCIA, PRECIOS_REFERENCIA_COMENTARIOS, plan, planComentarios, perfilDeVinculo, cargarVinculo } from './perfil.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
/* Las banderas se guardan como texto; lo numérico se convierte donde se usa. */
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const { vinculo, ruta: rutaVinculo, esEjemplo } = cargarVinculo(args);
const PERFIL = perfilDeVinculo(vinculo, args);
const TRM = Number(args.trm) || 3109.30;                  /* Banco de la República · 15-sep-2026 */
const CORRIDAS_DIA = Number(args.corridas) || PERFIL.corridasDia;
const DIAS = Number(args.dias) || PERFIL.dias;
const CORRIDAS = CORRIDAS_DIA * DIAS;

/* DeepSeek V4 Flash, tarifa FUERA DE PICO (US$ por millón de tokens). El pico
   es 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes = 20:00-23:00 y
   01:00-05:00 en Colombia. Corriendo a las 6 a. m. y 6 p. m. hora local
   (11:00 y 23:00 UTC) las dos lecturas caen fuera de pico. Clasificar postura
   y tema de cada ítem añade ~12 tokens de salida por ítem. */
const MODELO = { entrada: 0.15, entradaCache: 0.003, salida: 0.60, sistema: 1500, tokensPorItem: 60, salidaPorItem: 12, salidaPorCorrida: 900 };
const INFRA = 0.10;   /* el worker y el KV ya están y son compartidos; S3 ~30 MB/mes */

/* ── ¿Medido o estimado? ─────────────────────────────────────────────────── */
const rutaMedidos = path.join(AQUI, 'precios-medidos.json');
const MEDIDOS = existsSync(rutaMedidos) ? JSON.parse(readFileSync(rutaMedidos, 'utf8')) : {};
const medidosPosts = MEDIDOS.medidos || {}, medidosCom = MEDIDOS.comentarios || {};

const fmtUSD = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtCOP = n => '$' + Math.round(n).toLocaleString('es-CO');
const pad = (s, n, d = 'izq') => d === 'izq' ? String(s).padEnd(n) : String(s).padStart(n);
const suma = (xs, k) => xs.reduce((s, x) => s + x[k], 0);

/* ── Las dos capas, con el mismo cálculo ─────────────────────────────────── */
function costear(filasPlan, referencia, medidos) {
  return filasPlan.map(f => {
    const mes = f.porCorrida * CORRIDAS, ref = referencia[f.red], med = medidos[f.red];
    const precio = { bajo: ref.bajo, base: med ? med.base : ref.base, alto: ref.alto, medido: Boolean(med) };
    return { ...f, mes, precio, bajo: mes / 1000 * precio.bajo, base: mes / 1000 * precio.base, alto: mes / 1000 * precio.alto };
  });
}
const posts = costear(plan(PERFIL), PRECIOS_REFERENCIA, medidosPosts);
const comentarios = costear(planComentarios(PERFIL), PRECIOS_REFERENCIA_COMENTARIOS, medidosCom);
const itemsMes = suma(posts, 'mes') + suma(comentarios, 'mes');
/* El modelo lee todo lo que llega, de las dos capas; se reparte por ítems. */
const modeloPorItem = (MODELO.tokensPorItem * MODELO.entrada + MODELO.salidaPorItem * MODELO.salida) / 1e6;
const modeloFijo = (MODELO.sistema * MODELO.entradaCache + MODELO.salidaPorCorrida * MODELO.salida) / 1e6 * CORRIDAS;
const modelo = capas => modeloFijo + suma(capas, 'mes') * modeloPorItem;

function tabla(titulo, filas, unidad) {
  console.log(`\n${titulo}`);
  console.log(pad('RED', 11) + pad('CÓMO', 26) + pad(unidad, 10, 'der') + pad('/CORRIDA', 10, 'der') + pad('/MES', 9, 'der') + pad('US$/1K', 9, 'der') + pad('BAJO', 9, 'der') + pad('BASE', 9, 'der') + pad('ALTO', 9, 'der'));
  console.log('─'.repeat(102));
  for (const f of filas) {
    if (f.motivo) { console.log(pad(f.red, 11) + pad(`— ${f.motivo}`, 91)); continue; }
    const cuanto = unidad === 'CONS.×TOPE' ? `${f.consultas.length}×${f.tope}` : `${f.posts}×${f.tope}`;
    console.log(pad(f.red, 11) + pad(f.modo, 26) + pad(cuanto, 10, 'der') + pad(f.porCorrida, 10, 'der') + pad(f.mes.toLocaleString('es-CO'), 9, 'der') + pad((f.precio.medido ? '' : '~') + f.precio.base.toFixed(3), 9, 'der') + pad(fmtUSD(f.bajo), 9, 'der') + pad(fmtUSD(f.base), 9, 'der') + pad(fmtUSD(f.alto), 9, 'der'));
  }
  console.log('─'.repeat(102));
  console.log(pad('APIFY', 47) + pad(suma(filas, 'porCorrida'), 10, 'der') + pad(suma(filas, 'mes').toLocaleString('es-CO'), 9, 'der') + pad('', 9) + pad(fmtUSD(suma(filas, 'bajo')), 9, 'der') + pad(fmtUSD(suma(filas, 'base')), 9, 'der') + pad(fmtUSD(suma(filas, 'alto')), 9, 'der'));
}

console.log(`\n═══ ESCUCHA SOCIAL · costo por candidato y mes ═══`);
console.log(`${PERFIL.candidato} · ${PERFIL.temas.length} temas · ${PERFIL.escalas.join(' + ')} · ${CORRIDAS_DIA} lecturas/día × ${DIAS} días = ${CORRIDAS} corridas`);
if (esEjemplo) console.log(`Vínculo de EJEMPLO (${path.relative(process.cwd(), rutaVinculo)}); para un candidato real, --vinculo=su-vinculo.json`);
const nMed = Object.keys(medidosPosts).length + Object.keys(medidosCom).length;
console.log(nMed ? `Precios MEDIDOS contra Apify en ${nMed} filas (sin ~); el resto, de referencia.` : `⚠ Precios DE REFERENCIA (páginas de terceros, sep-2026). Corra medir.mjs antes de fijar tarifa.`);

tabla('CAPA 1 · POSTS — lo que se dice', posts, 'CONS.×TOPE');
tabla('CAPA 2 · COMENTARIOS — lo que se siente', comentarios, 'POSTS×TOPE');

console.log(`\nModelo (DeepSeek V4 Flash, fuera de pico)   solo posts ${fmtUSD(modelo(posts))}   ·   con comentarios ${fmtUSD(modelo([...posts, ...comentarios]))}`);
console.log(`Infraestructura (marginal)                  ${fmtUSD(INFRA)}   worker y KV ya están; S3 ~30 MB/mes`);

/* ── Costo marginal por escalón ──────────────────────────────────────────── */
const costo = (capas, k = 'base') => suma(capas, k) + modelo(capas) + INFRA;
console.log(`\n═══ COSTO MARGINAL POR CLIENTE ═══`);
console.log(pad('', 34) + pad('BAJO', 12, 'der') + pad('BASE', 12, 'der') + pad('ALTO', 12, 'der') + pad('BASE COP', 14, 'der'));
console.log('─'.repeat(84));
const escalones = [
  ...posts.filter(f => !f.motivo).map(f => [`${f.etiqueta} · solo posts`, [f]]),
  ['Las 4 redes · solo posts', posts],
  ...posts.filter(f => !f.motivo).map((f, i) => [`${f.etiqueta} · posts + comentarios`, [f, comentarios[posts.indexOf(f)]]]),
  ['Las 4 redes · posts + comentarios', [...posts, ...comentarios]],
];
for (const [nombre, capas] of escalones) console.log(pad(nombre, 34) + pad(fmtUSD(costo(capas, 'bajo')), 12, 'der') + pad(fmtUSD(costo(capas)), 12, 'der') + pad(fmtUSD(costo(capas, 'alto')), 12, 'der') + pad(fmtCOP(costo(capas) * TRM), 14, 'der'));

/* ── El escalón del plan ─────────────────────────────────────────────────── */
const apifyBase = suma(posts, 'base') + suma(comentarios, 'base');
console.log(`\n═══ EL ESCALÓN DE APIFY ═══   (el plan no es cuota: es crédito prepago que el uso consume)`);
for (const [plan_, precio, credito] of [['Starter', 29, 29], ['Scale', 199, 199], ['Business', 999, 999]])
  console.log(`  ${pad(plan_, 10)} ${pad(fmtUSD(precio) + '/mes', 12, 'der')}  crédito ${pad(fmtUSD(credito), 9, 'der')}  →  ${pad(Math.floor(credito / suma(posts, 'base')), 3, 'der')} clientes solo posts · ${pad(Math.floor(credito / apifyBase), 3, 'der')} con comentarios`);

/* ── Precio de venta ─────────────────────────────────────────────────────── */
console.log(`\n═══ QUÉ COBRAR ═══  (TRM ${fmtCOP(TRM)} · costo base)`);
console.log(pad('', 40) + pad('COSTO', 12, 'der') + pad('PRECIO', 12, 'der') + pad('MARGEN', 12, 'der') + pad('MÚLT.', 8, 'der'));
console.log('─'.repeat(84));
const solo = red => posts.find(f => f.red === red);
const con = red => [solo(red), comentarios.find(f => f.red === red)];
const oferta = [
  ['Una red, solo posts (X)', 59000, costo([solo('x')])],
  ['Una red, posts + comentarios (X)', 99000, costo(con('x'))],
  ['Escucha completa, solo posts', 149000, costo(posts)],
  ['Escucha completa + comentarios', 219000, costo([...posts, ...comentarios])],
  ['C360 + escucha completa, 1 lectura/día', 249000, costo(posts) / 2 + INFRA / 2],
  ['C360 + escucha completa, 2 lecturas/día', 299000, costo(posts)],
  ['C360 + escucha + comentarios, 2/día', 379000, costo([...posts, ...comentarios])],
];
for (const [nombre, cop, usd] of oferta) { const c = usd * TRM; console.log(pad(nombre, 40) + pad(fmtCOP(c), 12, 'der') + pad(fmtCOP(cop), 12, 'der') + pad(fmtCOP(cop - c), 12, 'der') + pad((cop / c).toFixed(1) + '×', 8, 'der')); }
console.log('');
