/* calibrar.mjs — cuánto de su propio voto conserva una candidatura con el tiempo.
   ═══════════════════════════════════════════════════════════════════════════
   Pregunta: cuando la MISMA persona se vuelve a lanzar a la misma corporación
   4, 8 o 12 años después, ¿qué parte de su votación anterior sigue ahí, puesto
   por puesto?

     retención = Σ_puesto min(votos antes, votos después) ÷ Σ votos antes

   Es la misma suma de mínimos del endoso (candidato-360-endoso.js, medirPar),
   medida contra sí misma. Por eso sirve de techo para el endoso de un aliado:
   nadie le pasa a otro más de lo que conservaría si se lanzara él mismo, y el
   aliado cuya última elección fue en 2019 llega a 2027 con ocho años de
   desgaste encima. Reemplaza el 30 % supuesto que tenía el motor.

   Qué hace:
     1. Baja los índices de cada corporación y año (las fuentes de cand-index.js).
     2. Empareja personas entre el año Y y el Y+g por `personaKey` (la llave de
        la web): nombres de tres o más palabras, únicos en cada índice, y el
        segundo tiene que votar ≥ 90 % en el mismo municipio (JAL, Concejo,
        Alcaldía) o departamento (Asamblea, Gobernación, Cámara) que el primero.
        Un homónimo de otra ciudad no pasa. Senado sin filtro de lugar.
     3. Baja las mesas de las dos candidaturas y mide la retención por puesto.
     4. Escribe los cuartiles por corporación y distancia en
        salida/endoso-calibracion.json + salida/endoso-casos.csv, y reescribe
        el bloque RETENCION de candidato-360-endoso.js (entre sus marcas).

   ⚠️ El código de puesto no es estable entre elecciones en todas las ciudades
   (Barranquilla se rezonificó: un código de 2018 puede ser otro lugar en
   2026). Eso BAJA la retención medida ahí. El resumen imprime los
   departamentos para verlo; la tabla es nacional.

     node tools/candidato-360/endoso/calibrar.mjs                 (todo)
     node tools/candidato-360/endoso/calibrar.mjs --limite 40     (ensayo)
     node tools/candidato-360/endoso/calibrar.mjs --no-escribir   (no toca el motor)

   Opciones: --limite N (pares por corporación y par de años; default 400)
             --concurrencia N (default 8) · --cache DIR (default ~/.cache/rr-endoso)
   ═══════════════════════════════════════════════════════════════════════════ */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { homedir } from 'node:os';
import path from 'node:path';
import vm from 'node:vm';

const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i]; if (!a.startsWith('--')) continue;
  const k = a.slice(2), v = process.argv[i + 1];
  if (!v || v.startsWith('--')) args[k] = true; else { args[k] = v; i++; }
}
const AQUI = path.dirname(new URL(import.meta.url).pathname);
const REPO = path.resolve(AQUI, '../../..');
const BASE = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
const SALIDA = path.join(AQUI, 'salida');
const CACHE = path.resolve(args.cache || path.join(homedir(), '.cache', 'rr-endoso'));
const LIMITE = Number(args.limite) || 400;
const CONCURRENCIA = Number(args.concurrencia) || 8;
const MIN_EN_AMBITO = .9;

/* Qué fuentes de cand-index.js son cada corporación y año, y a qué escala se
   exige que la persona compita en el mismo lugar. */
const CORPS = {
  jal:         { ambito: 'mun', anos: { 2011: 'jal2011', 2015: 'jal2015', 2019: 'jal2019', 2023: 'jal' } },
  concejo:     { ambito: 'mun', anos: { 2011: 'conc2011', 2015: 'conc2015', 2019: 'conc2019', 2023: 'concejo' } },
  alcaldia:    { ambito: 'mun', anos: { 2011: 'alc2011', 2015: 'alc2015', 2019: 'alc2019', 2023: 'alc2023' } },
  asamblea:    { ambito: 'dep', anos: { 2011: 'asam2011', 2015: 'asam2015', 2019: 'asam2019', 2023: 'asamblea' } },
  gobernacion: { ambito: 'dep', anos: { 2011: 'gob2011', 2015: 'gob2015', 2019: 'gob2019', 2023: 'gob2023' } },
  /* Cámara y Senado van en el mismo índice; se separan por el corp. */
  camara:      { ambito: 'dep', anos: { 2014: 'con2014', 2018: 'con2018', 2022: 'con2022' }, filtro: c => /^C[AÁ]MARA/i.test(c.corp || '') },
  senado:      { ambito: 'nac', anos: { 2014: 'con2014', 2018: 'con2018', 2022: 'con2022' }, filtro: c => /^SENADO/i.test(c.corp || '') },
};

/* ── cand-index.js y el motor del endoso, tal cual los usa la web ─────────── */
const ctx = { window: { RRData: { publicUrl: p => `${BASE.replace(/\/congreso-2026\/output$/, '')}/${p}` } }, console, fetch };
vm.createContext(ctx);
vm.runInContext(await readFile(path.join(REPO, 'cand-index.js'), 'utf8'), ctx);
vm.runInContext(await readFile(path.join(REPO, 'candidato-360-endoso.js'), 'utf8'), ctx);
const CR = ctx.window.CandRegistry, E = ctx.window.C360Endoso;
const fuentes = Object.fromEntries([...CR.SOURCES, ...CR.LOCAL_SOURCES].map(s => [s.name, s]));

/* ── Descarga con caché en disco ───────────────────────────────────────── */
await mkdir(CACHE, { recursive: true });
async function bajar(url) {
  const f = path.join(CACHE, createHash('sha1').update(url).digest('hex') + '.json');
  if (existsSync(f)) return JSON.parse(await readFile(f, 'utf8'));
  for (let intento = 0; intento < 4; intento++) {
    try {
      const r = await fetch(url);
      if (r.status === 404 || r.status === 403) { await writeFile(f, 'null'); return null; }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const txt = await r.text(); await writeFile(f, txt); return JSON.parse(txt);
    } catch (e) { if (intento === 3) { console.warn(`  ✗ ${url}: ${e.message}`); return null; } await new Promise(r => setTimeout(r, 500 * 2 ** intento)); }
  }
}
async function enLotes(items, fn) {
  const out = new Array(items.length); let i = 0, hechos = 0; const t0 = Date.now();
  async function obrero() { while (i < items.length) { const j = i++; out[j] = await fn(items[j]); hechos++; if (hechos % 25 === 0) process.stdout.write(`\r    ${hechos}/${items.length} (${((Date.now() - t0) / 1000).toFixed(0)} s)`); } }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCIA, items.length) }, obrero));
  if (items.length >= 25) process.stdout.write('\n');
  return out;
}

const indices = {};
async function indice(nombre) {
  if (indices[nombre]) return indices[nombre];
  const src = fuentes[nombre]; if (!src) return (indices[nombre] = []);
  const base = `${BASE}/${src.dir}`, raw = await bajar(`${base}/${src.indexFile}`);
  return (indices[nombre] = raw ? src.list(raw).map(c => ({ ...c, dataUrl: `${base}/${c.slug}.json` })) : []);
}
function unicos(lista, filtro) {
  const por = new Map();
  for (const c of lista) {
    if (CR.isPartyEntry(c) || c.tipo === 'partido' || (filtro && !filtro(c))) continue;
    const k = CR.personaKey(c.nombre); if (k.split(' ').length < 3) continue;
    por.set(k, por.has(k) ? null : c);
  }
  return por;
}
/* Orden estable y sin sesgo por nombre: el hash de la llave. Así el ensayo
   con --limite es reproducible. */
const barajar = xs => xs.map(x => [createHash('md5').update(x.k).digest('hex'), x]).sort((a, b) => a[0] < b[0] ? -1 : 1).map(x => x[1]);

const mesasDe = async c => { const d = await bajar(c.dataUrl); return Array.isArray(d?.mesas) ? d.mesas : []; };
const dep2 = m => String(m.dep || '').padStart(2, '0'), munK = m => `${dep2(m)}-${String(m.mun || '').padStart(3, '0')}`;
function mayor(ms, llave) { const s = {}; ms.forEach(m => { const k = llave(m); s[k] = (s[k] || 0) + Number(m.v || 0); }); return Object.entries(s).sort((a, b) => b[1] - a[1])[0]?.[0]; }

function medir(ambito, ma, mb) {
  const totA = E.suma(ma), totB = E.suma(mb); if (!totA || !totB) return null;
  let dep = mayor(ma, dep2), mun = mayor(ma, munK);
  if (ambito !== 'nac') {
    const llave = ambito === 'mun' ? munK : dep2, lugar = ambito === 'mun' ? mun : dep;
    const enLugar = E.suma(mb.filter(m => llave(m) === lugar));
    if (enLugar / totB < MIN_EN_AMBITO) return null;   /* homónimo de otro lugar, o se mudó */
  }
  const A = E.agrupar(ma, E.llavePuesto), B = E.agrupar(mb, E.llavePuesto);
  let sumMin = 0; Object.entries(A).forEach(([k, a]) => { sumMin += Math.min(a, B[k] || 0); });
  return { dep, mun, retencion: sumMin / totA, gap: totB / totA };
}

const casos = [];
for (const [corp, C] of Object.entries(CORPS)) {
  const anos = Object.keys(C.anos).map(Number).sort();
  for (const y of anos) for (const y2 of anos) {
    const g = y2 - y; if (g <= 0) continue;
    process.stdout.write(`${corp} ${y} → ${y2}: `);
    const [ia, ib] = await Promise.all([indice(C.anos[y]), indice(C.anos[y2])]);
    const ua = unicos(ia, C.filtro), ub = unicos(ib, C.filtro);
    let pares = [...ua.entries()].filter(([k, c]) => c && ub.get(k)).map(([k, c]) => ({ k, a: c, b: ub.get(k) }));
    const todos = pares.length; pares = barajar(pares).slice(0, LIMITE);
    console.log(`${todos} personas en los dos, se miden ${pares.length}`);
    const med = await enLotes(pares, async ({ k, a, b }) => {
      const [ma, mb] = await Promise.all([mesasDe(a), mesasDe(b)]);
      const m = medir(C.ambito, ma, mb); if (!m) return null;
      return { corp, anoA: y, anoB: y2, gap_anos: g, persona: k, dep: m.dep, municipio: m.mun, votosA: Number(a.votos) || E.suma(ma), votosB: Number(b.votos) || E.suma(mb), retencion: m.retencion, crecimiento: m.gap };
    });
    const v = med.filter(Boolean); console.log(`    ${v.length} válidos`); casos.push(...v);
  }
}

/* ── Agregar ─────────────────────────────────────────────────────────────── */
const cuantil = (xs, q) => { const s = xs.filter(Number.isFinite).sort((a, b) => a - b); if (!s.length) return null; const p = (s.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return +(s[lo] + (s[hi] - s[lo]) * (p - lo)).toFixed(3); };
const resumen = cs => ({ n: cs.length, p25: cuantil(cs.map(c => c.retencion), .25), p50: cuantil(cs.map(c => c.retencion), .5), p75: cuantil(cs.map(c => c.retencion), .75) });
/* La distancia hasta 2027 de un aliado: 2023 → 4, 2019 → 8, 2015 → 12. El
   Congreso (2022, 2018) cae a la más cercana. */
const tabla = {};
for (const corp of Object.keys(CORPS)) {
  const cs = casos.filter(c => c.corp === corp); if (!cs.length) continue;
  tabla[corp] = {};
  for (const g of [...new Set(cs.map(c => c.gap_anos))].sort((a, b) => a - b)) tabla[corp][g] = resumen(cs.filter(c => c.gap_anos === g));
}
/* Todas las corporaciones juntas, por distancia: para lo que no tenga casos
   propios suficientes (presidencia, consultas, gobernación). */
tabla._todas = {};
for (const g of [...new Set(casos.map(c => c.gap_anos))].sort((a, b) => a - b)) tabla._todas[g] = resumen(casos.filter(c => c.gap_anos === g));

await mkdir(SALIDA, { recursive: true });
await writeFile(path.join(SALIDA, 'endoso-calibracion.json'), JSON.stringify({ _generado: new Date().toISOString().slice(0, 10), _metodo: 'retención = Σ_puesto min(votos Y, votos Y+g) ÷ Σ votos Y, misma persona y misma corporación; cuartiles por corporación y distancia en años', ...tabla }, null, 1));
const cols = ['corp', 'anoA', 'anoB', 'gap_anos', 'persona', 'dep', 'municipio', 'votosA', 'votosB', 'retencion', 'crecimiento'];
const csv = v => v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
await writeFile(path.join(SALIDA, 'endoso-casos.csv'), [cols.join(','), ...casos.map(c => cols.map(k => csv(typeof c[k] === 'number' ? +c[k].toFixed(4) : c[k])).join(','))].join('\n') + '\n');

console.log('\n═══ Retención (p25 · mediana · p75, n)');
for (const [corp, t] of Object.entries(tabla)) for (const [g, r] of Object.entries(t)) console.log(`  ${corp.padEnd(12)} ${String(g).padStart(2)} años: ${r.p25} · ${r.p50} · ${r.p75}  (n=${r.n})`);
console.log('\n═══ Por departamento (Concejo, 4 años) · mediana y n');
const c4 = casos.filter(c => c.corp === 'concejo' && c.gap_anos === 4);
for (const d of [...new Set(c4.map(c => c.dep))].sort()) { const r = resumen(c4.filter(c => c.dep === d)); if (r.n >= 8) console.log(`  dep ${d}: ${r.p50} (n=${r.n})`); }

/* ── El bloque del motor ──────────────────────────────────────────────── */
if (!args['no-escribir']) {
  const f = path.join(REPO, 'candidato-360-endoso.js'); let js = await readFile(f, 'utf8');
  const i = js.indexOf('/* RETENCION:inicio */'), j = js.indexOf('/* RETENCION:fin */');
  if (i < 0 || j < 0) { console.error('No encontré las marcas RETENCION en candidato-360-endoso.js'); process.exit(1); }
  const compacto = Object.fromEntries(Object.entries(tabla).map(([corp, t]) => [corp, Object.fromEntries(Object.entries(t).map(([g, r]) => [g, [r.p25, r.p50, r.p75, r.n]]))]));
  const bloque = `/* RETENCION:inicio */\n  /* Generado por tools/candidato-360/endoso/calibrar.mjs el ${new Date().toISOString().slice(0, 10)}: [p25, mediana, p75, n] por corporación y años de distancia. No editar a mano: volver a correr el script. */\n  const RETENCION = ${JSON.stringify(compacto)};\n  `;
  js = js.slice(0, i) + bloque + js.slice(j);
  await writeFile(f, js);
  console.log(`\nBloque RETENCION reescrito en candidato-360-endoso.js`);
}
