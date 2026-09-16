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

import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PERFIL, REDES, plan } from './perfil.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const API = 'https://api.apify.com/v2';
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const GASTAR = Boolean(args.gastar);
const TOPE = args.tope ? Number(args.tope) : null;      /* null = el de perfil.mjs */
const SOLO = args.red ? String(args.red).split(',') : null;
const ESPERA_MAX = Number(args.espera || 300) * 1000;   /* 5 minutos por actor */

const TOKEN = process.env.APIFY_TOKEN;
if (GASTAR && !TOKEN) { console.error('Falta APIFY_TOKEN en el entorno. `export APIFY_TOKEN=...` — nunca lo escriba en el repo.'); process.exit(1); }

const usd = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const pad = (s, n, d = 'izq') => d === 'izq' ? String(s).padEnd(n) : String(s).padStart(n);
const dormir = ms => new Promise(r => setTimeout(r, ms));
const corto = (s, n) => String(s).length <= n ? s : String(s).slice(0, n - 1) + '…';

/* Apify identifica al actor con ~ en vez de / en la URL. */
const rutaActor = actor => actor.replace('/', '~');

/* Todo campo numérico cuyo nombre hable de dólares, venga donde venga. No se
   escoge uno de antemano: si Apify renombró el campo, se ve en la tabla. */
function camposUSD(obj, prefijo = '', salida = {}) {
  if (!obj || typeof obj !== 'object') return salida;
  for (const [k, v] of Object.entries(obj)) {
    const ruta = prefijo ? `${prefijo}.${k}` : k;
    if (typeof v === 'number' && /usd/i.test(k)) salida[ruta] = v;
    else if (v && typeof v === 'object' && Object.keys(salida).length < 40) camposUSD(v, ruta, salida);
  }
  return salida;
}

async function api(ruta, opciones = {}) {
  const url = `${API}${ruta}${ruta.includes('?') ? '&' : '?'}token=${encodeURIComponent(TOKEN)}`;
  const r = await fetch(url, { ...opciones, headers: { 'content-type': 'application/json', ...(opciones.headers || {}) } });
  const txt = await r.text();
  let cuerpo; try { cuerpo = JSON.parse(txt); } catch { cuerpo = { crudo: txt.slice(0, 400) }; }
  /* El mensaje de Apify se muestra tal cual: «actor not found» y «insufficient
     credit» piden cosas distintas y confundirlos hace perder una tarde. */
  if (!r.ok) throw new Error(`HTTP ${r.status} · ${cuerpo?.error?.message || cuerpo?.crudo || ruta.split('?')[0]}`);
  return cuerpo.data ?? cuerpo;
}

async function correr(red, entrada) {
  const r = REDES[red];
  const run = await api(`/acts/${rutaActor(r.actor)}/runs`, { method: 'POST', body: JSON.stringify(entrada) });
  const inicio = Date.now();
  let estado = run;
  while (['READY', 'RUNNING'].includes(estado.status)) {
    if (Date.now() - inicio > ESPERA_MAX) { await api(`/actor-runs/${run.id}/abort`, { method: 'POST' }).catch(() => {}); throw new Error(`se pasó de ${ESPERA_MAX / 1000}s y se abortó`); }
    await dormir(4000);
    estado = await api(`/actor-runs/${run.id}`);
  }
  const items = await api(`/datasets/${estado.defaultDatasetId}/items?clean=true&limit=1000`).catch(() => []);
  return { estado, items: Array.isArray(items) ? items : [] };
}

/* ── Lo que se va a correr ────────────────────────────────────────────────── */
const filas = plan(PERFIL).filter(f => !SOLO || SOLO.includes(f.red));
console.log(`\n═══ MEDICIÓN · ${PERFIL.candidato} ═══`);
console.log(`Temas: ${PERFIL.temas.map(t => `«${t}»`).join(' · ')}   Escalas: ${PERFIL.ciudad} y ${PERFIL.localidad}\n`);
console.log(pad('RED', 11) + pad('ACTOR', 58) + pad('CONS.', 7, 'der') + pad('TOPE', 6, 'der') + pad('PEDIDOS', 9, 'der'));
console.log('─'.repeat(91));
for (const f of filas) {
  const tope = TOPE ?? f.tope;
  console.log(pad(f.red, 11) + pad(corto(f.actor, 56), 58) + pad(f.consultas.length, 7, 'der') + pad(tope, 6, 'der') + pad(f.consultas.length * tope, 9, 'der'));
}

if (!GASTAR) {
  console.log(`\nEnsayo: no se llamó a Apify y no se gastó un peso.`);
  console.log(`Para medir de verdad:  APIFY_TOKEN=... node ${path.relative(process.cwd(), fileURLToPath(import.meta.url))} --gastar --tope=10`);
  console.log(`Revise antes las páginas de Facebook en perfil.mjs: si una no existe, ese actor cobra por nada.\n`);
  process.exit(0);
}

/* ── Medir ───────────────────────────────────────────────────────────────── */
const medidos = {}, detalle = [];
for (const f of filas) {
  const tope = TOPE ?? f.tope;
  const entrada = REDES[f.red].input(f.consultas, tope);
  process.stdout.write(`\n▸ ${f.etiqueta} (${f.actor})… `);
  try {
    const { estado, items } = await correr(f.red, entrada);
    const costos = camposUSD(estado);
    /* El total que cobra Apify por la corrida: el campo más completo que
       exista. Si ninguno existe, se dice, no se estima. */
    const total = costos.usageTotalUsd ?? costos['stats.usageTotalUsd'] ?? Math.max(0, ...Object.values(costos));
    const n = items.length;
    const porMil = n ? total / n * 1000 : null;
    console.log(`${estado.status} · ${n} resultados · ${usd(total)}`);
    for (const [k, v] of Object.entries(costos)) console.log(`     ${pad(k, 34)} ${usd(v)}`);
    if (!n) console.log(`     ⚠ cero resultados NO es «no hay conversación»: puede ser el actor caído, el input con otro nombre de campo o la consulta vacía. Revise antes de concluir.`);
    if (porMil != null) medidos[f.red] = { base: Number(porMil.toFixed(4)), medidoEn: new Date().toISOString(), actor: f.actor, muestra: n, cobrado: total };
    detalle.push({ red: f.red, etiqueta: f.etiqueta, actor: f.actor, n, total, porMil, estado: estado.status, consultas: f.consultas.length, tope });
  } catch (e) {
    console.log(`FALLÓ · ${e.message}`);
    detalle.push({ red: f.red, etiqueta: f.etiqueta, actor: f.actor, error: e.message });
  }
}

/* ── Resultado ───────────────────────────────────────────────────────────── */
console.log(`\n═══ PRECIO REAL POR RED ═══`);
console.log(pad('RED', 12) + pad('RESULTADOS', 12, 'der') + pad('COBRADO', 12, 'der') + pad('US$/1.000', 12, 'der') + pad('vs REFERENCIA', 16, 'der'));
console.log('─'.repeat(64));
const { PRECIOS_REFERENCIA } = await import('./perfil.mjs');
for (const d of detalle) {
  if (d.error) { console.log(pad(d.red, 12) + pad('—', 12, 'der') + pad('—', 12, 'der') + pad('—', 12, 'der') + pad(d.error.slice(0, 15), 16, 'der')); continue; }
  const ref = PRECIOS_REFERENCIA[d.red]?.base;
  const dif = d.porMil != null && ref ? `${d.porMil > ref ? '+' : ''}${Math.round((d.porMil / ref - 1) * 100)} %` : '—';
  console.log(pad(d.red, 12) + pad(d.n, 12, 'der') + pad(usd(d.total), 12, 'der') + pad(d.porMil != null ? usd(d.porMil) : '—', 12, 'der') + pad(dif, 16, 'der'));
}

if (Object.keys(medidos).length) {
  const destino = path.join(AQUI, 'precios-medidos.json');
  await writeFile(destino, JSON.stringify({ _doc: 'US$ por 1.000 resultados, MEDIDOS contra Apify. Lo escribe medir.mjs y lo prefiere costos.mjs sobre los precios de referencia.', medidos }, null, 2));
  console.log(`\nEscrito ${path.relative(process.cwd(), destino)} · ahora corra:  node tools/candidato-360/escucha/costos.mjs`);
}
console.log(`\nOjo: esto midió UNA corrida. El mes son ${PERFIL.corridasDia * PERFIL.dias}.\n`);
