/* medir.mjs — cuánto cuesta DE VERDAD cada red, preguntándoselo a Apify.
   ------------------------------------------------------------------
   El modelo de costos (costos.mjs) arrancó con precios sacados de páginas de
   terceros porque apify.com no era alcanzable desde donde se escribió. Eso
   sirve para dimensionar y NO para fijar tarifa: cada actor pone su propio
   precio y el catálogo se mueve.

   Esto lo reemplaza por medición. Corre el perfil real UNA vez —las mismas
   consultas que correría en producción—, le pregunta a Apify qué cobró por
   cada corrida y escribe `precios-medidos.json`, que costos.mjs prefiere sobre
   los precios de referencia.

   No adivina el nombre del campo de costo: recorre la respuesta de Apify y
   muestra TODOS los campos en dólares que encuentre. Si Apify cambió el
   esquema, se ve; no se inventa una cifra.

   Uso:
     export APIFY_TOKEN=...                 # nunca en el repo ni en un chat
     node tools/candidato-360/escucha/medir.mjs              # ensayo, no gasta
     node tools/candidato-360/escucha/medir.mjs --gastar --tope=10
     node tools/candidato-360/escucha/medir.mjs --gastar --red=x

   La primera vez conviene `--tope=10`: mide el precio por resultado igual y
   gasta una décima parte. Los topes de producción viven en perfil.mjs.       */

import { writeFile, readFile } from 'node:fs/promises';
import { tokenApify, AYUDA_TOKEN, clienteApify } from './apify.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REDES, COMENTARIOS, plan, planComentarios, referenciaDePost, perfilDeVinculo, cargarVinculo, PRECIOS_REFERENCIA, PRECIOS_REFERENCIA_COMENTARIOS } from './perfil.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const GASTAR = Boolean(args.gastar);
const TOPE = args.tope ? Number(args.tope) : null;      /* null = el de perfil.mjs */
const SOLO = args.red ? String(args.red).split(',') : null;
/* --capa=posts mide solo la 1; --capa=comentarios exige la 1 igual (necesita
   los posts para saber cuáles seguir) pero solo reporta la 2; sin bandera, las dos. */
const CAPA = String(args.capa || 'todo');
const ESPERA_MAX = Number(args.espera || 300) * 1000;   /* 5 minutos por actor */

/* El perfil sale del vínculo: el de --vinculo=archivo.json (la respuesta de
   /c360/me → vinculo, o el mismo JSON que guarda el worker) o, sin él, el de
   ejemplo. --temas y --paginas siguen sirviendo para probar sin editar nada. */
const { vinculo, ruta: rutaVinculo, esEjemplo } = cargarVinculo(args);
const PERFIL = perfilDeVinculo(vinculo, args);

const TOKEN = await tokenApify();
if (GASTAR && !TOKEN) { console.error('\n' + AYUDA_TOKEN + '\n'); process.exit(1); }
const apify = GASTAR ? clienteApify(TOKEN, { esperaMax: ESPERA_MAX }) : null;

const usd = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const pad = (s, n, d = 'izq') => d === 'izq' ? String(s).padEnd(n) : String(s).padStart(n);
const corto = (s, n) => String(s).length <= n ? s : String(s).slice(0, n - 1) + '…';

/* ── Lo que se va a correr ────────────────────────────────────────────────── */
const todas = plan(PERFIL), filas = todas.filter(f => !f.motivo && (!SOLO || SOLO.includes(f.red)));
const filasCom = planComentarios(PERFIL, todas).filter(f => !f.motivo && (!SOLO || SOLO.includes(f.red)));
console.log(`\n═══ MEDICIÓN · ${PERFIL.candidato} ═══`);
console.log(esEjemplo ? `Vínculo de EJEMPLO (${path.relative(process.cwd(), rutaVinculo)}). Para medir a un candidato real: --vinculo=su-vinculo.json`
                      : `Vínculo: ${path.relative(process.cwd(), rutaVinculo)}`);
console.log(`Temas: ${PERFIL.temas.length ? PERFIL.temas.map(t => `«${t}»`).join(' · ') : '— (el candidato no los ha escrito)'}   Escalas: ${PERFIL.escalas.join(' y ')}`);
for (const f of todas.filter(f => f.motivo)) console.log(`  · ${f.etiqueta} no se mide: ${f.motivo}`);
console.log('');
console.log('CAPA 1 · POSTS');
console.log(pad('RED', 11) + pad('ACTOR', 58) + pad('CONS.', 7, 'der') + pad('TOPE', 6, 'der') + pad('PEDIDOS', 9, 'der'));
console.log('─'.repeat(91));
for (const f of filas) {
  const tope = TOPE ?? f.tope;
  console.log(pad(f.red, 11) + pad(corto(f.actor, 56), 58) + pad(f.consultas.length, 7, 'der') + pad(tope, 6, 'der') + pad(f.consultas.length * tope, 9, 'der'));
}
if (CAPA !== 'posts') {
  console.log('\nCAPA 2 · COMENTARIOS  (de los posts con más reacción que traiga la capa 1)');
  console.log(pad('RED', 11) + pad('ACTOR', 58) + pad('POSTS', 7, 'der') + pad('TOPE', 6, 'der') + pad('PEDIDOS', 9, 'der'));
  console.log('─'.repeat(91));
  for (const f of filasCom) {
    const tope = TOPE ? Math.min(TOPE, f.tope) : f.tope;
    console.log(pad(f.red, 11) + pad(corto(f.actor, 56), 58) + pad(f.posts, 7, 'der') + pad(tope, 6, 'der') + pad(f.posts * tope, 9, 'der'));
  }
}

if (!GASTAR) {
  /* Lo que de verdad se va a preguntar, palabra por palabra. Una URL de
     Facebook mal escrita NO falla: el actor corre, no encuentra nada y cobra
     igual. Por eso se leen antes de gastar y no después. */
  console.log('\nLas consultas, tal como saldrían:');
  for (const f of filas) {
    console.log(`\n  ${f.etiqueta} · ${f.modo}`);
    for (const q of f.consultas) console.log(`    ${q}`);
  }
  console.log(`\nEnsayo: no se llamó a Apify y no se gastó un peso.`);
  console.log(`\n  Cambiar los temas sin tocar código:`);
  console.log(`    node ${path.relative(process.cwd(), fileURLToPath(import.meta.url))} --temas="hurto al comercio|Portal Tunal"`);
  console.log(`\n  Medir de verdad (empiece por --tope=10: mide igual y gasta la décima parte):`);
  console.log(`    node ${path.relative(process.cwd(), fileURLToPath(import.meta.url))} --gastar --tope=10\n`);
  process.exit(0);
}

/* ── Medir ───────────────────────────────────────────────────────────────── */
/* Una corrida medida: qué cobró Apify, cuántos ítems y qué campos traen. Los
   campos se imprimen porque son lo que decide si de un actor salen métricas,
   comentarios o solo texto —y eso no se adivina, se mira. */
async function medirUna({ capa, red, etiqueta, actor, entrada, pedidos }) {
  process.stdout.write(`\n▸ ${etiqueta} · ${capa} (${actor})… `);
  try {
    /* El total que cobra Apify por la corrida: el campo más completo que
       exista. Si ninguno existe, se dice, no se estima. */
    const { estado, items, costos, cobrado: total } = await apify.correr(actor, entrada);
    const n = items.length, porMil = n ? total / n * 1000 : null;
    console.log(`${estado.status} · ${n} de ${pedidos} pedidos · ${usd(total)}`);
    for (const [k, v] of Object.entries(costos)) console.log(`     ${pad(k, 34)} ${usd(v)}`);
    if (n) console.log(`     campos: ${Object.keys(items[0]).slice(0, 24).join(', ')}${Object.keys(items[0]).length > 24 ? ', …' : ''}`);
    else console.log(`     ⚠ cero resultados NO es «no hay conversación»: puede ser el actor caído, el input con otro nombre de campo o la consulta vacía. Revise antes de concluir.`);
    return { capa, red, etiqueta, actor, n, total, porMil, estado: estado.status, items };
  } catch (e) {
    console.log(`FALLÓ · ${e.message}`);
    return { capa, red, etiqueta, actor, error: e.message, items: [] };
  }
}

const medidos = {}, medidosCom = {}, detalle = [];
const sello = (r, medida) => { if (r.porMil != null) medida[r.red] = { base: Number(r.porMil.toFixed(4)), medidoEn: new Date().toISOString(), actor: r.actor, muestra: r.n, cobrado: r.total }; };

/* Capa 1 · posts */
const postsPorRed = {};
for (const f of filas) {
  const tope = TOPE ?? f.tope;
  const r = await medirUna({ capa: 'posts', red: f.red, etiqueta: f.etiqueta, actor: f.actor, entrada: REDES[f.red].input(f.consultas, tope), pedidos: f.consultas.length * tope });
  postsPorRed[f.red] = r.items; if (CAPA !== 'comentarios') { sello(r, medidos); detalle.push(r); }
}

/* Capa 2 · comentarios, de los posts con más reacción de la capa 1. Si ningún
   ítem trae URL con un nombre de campo conocido, no hay cómo seguirlos y se
   dice con los campos que sí vinieron, para añadir el nombre a referenciaDePost. */
if (CAPA !== 'posts') for (const f of filasCom) {
  const refs = (postsPorRed[f.red] || []).map(referenciaDePost).filter(Boolean).sort((a, b) => b.reaccion - a.reaccion);
  const elegidos = refs.slice(0, f.posts);
  if (!elegidos.length) {
    const muestra = (postsPorRed[f.red] || [])[0];
    console.log(`\n▸ ${f.etiqueta} · comentarios: sin posts que seguir${muestra ? ` (ningún campo de URL conocido; vinieron: ${Object.keys(muestra).slice(0, 12).join(', ')})` : ' (la capa 1 no trajo nada)'}`);
    detalle.push({ capa: 'comentarios', red: f.red, etiqueta: f.etiqueta, actor: f.actor, error: 'sin posts que seguir' });
    continue;
  }
  const tope = TOPE ? Math.min(TOPE, f.tope) : f.tope;
  const r = await medirUna({ capa: 'comentarios', red: f.red, etiqueta: f.etiqueta, actor: f.actor, entrada: COMENTARIOS[f.red].input(elegidos, tope), pedidos: elegidos.length * tope });
  sello(r, medidosCom); detalle.push(r);
}

/* ── Resultado ───────────────────────────────────────────────────────────── */
console.log(`\n═══ PRECIO REAL POR RED Y CAPA ═══`);
console.log(pad('CAPA', 13) + pad('RED', 12) + pad('RESULTADOS', 12, 'der') + pad('COBRADO', 12, 'der') + pad('US$/1.000', 12, 'der') + pad('vs REFERENCIA', 16, 'der'));
console.log('─'.repeat(77));
for (const d of detalle) {
  if (d.error) { console.log(pad(d.capa, 13) + pad(d.red, 12) + pad('—', 12, 'der') + pad('—', 12, 'der') + pad('—', 12, 'der') + pad(d.error.slice(0, 15), 16, 'der')); continue; }
  const ref = (d.capa === 'comentarios' ? PRECIOS_REFERENCIA_COMENTARIOS : PRECIOS_REFERENCIA)[d.red]?.base;
  const dif = d.porMil != null && ref ? `${d.porMil > ref ? '+' : ''}${Math.round((d.porMil / ref - 1) * 100)} %` : '—';
  console.log(pad(d.capa, 13) + pad(d.red, 12) + pad(d.n, 12, 'der') + pad(usd(d.total), 12, 'der') + pad(d.porMil != null ? usd(d.porMil) : '—', 12, 'der') + pad(dif, 16, 'der'));
}

/* Se conserva lo ya medido en otras corridas: medir solo Facebook hoy no
   borra lo que X midió ayer. */
if (Object.keys(medidos).length || Object.keys(medidosCom).length) {
  const destino = path.join(AQUI, 'precios-medidos.json');
  let previo = {}; try { previo = JSON.parse(await readFile(destino, 'utf8')); } catch {}
  await writeFile(destino, JSON.stringify({
    _doc: 'US$ por 1.000 resultados, MEDIDOS contra Apify. Lo escribe medir.mjs y lo prefiere costos.mjs sobre los precios de referencia. `medidos` es la capa de posts; `comentarios`, la de comentarios.',
    medidos: { ...(previo.medidos || {}), ...medidos }, comentarios: { ...(previo.comentarios || {}), ...medidosCom },
  }, null, 2));
  console.log(`\nEscrito ${path.relative(process.cwd(), destino)} · ahora corra:  node tools/candidato-360/escucha/costos.mjs`);
}
console.log(`\nOjo: esto midió UNA corrida. El mes son ${PERFIL.corridasDia * PERFIL.dias}.\n`);
