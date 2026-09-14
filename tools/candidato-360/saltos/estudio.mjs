/* estudio.mjs — cuánto arraigo conserva quien salta de corporación.
   ═══════════════════════════════════════════════════════════════════════════
   Pregunta: cuando alguien pasa de la JAL al Concejo, del Concejo a la
   Asamblea o de la Alcaldía a la Gobernación en la elección SIGUIENTE (cuatro
   años después), ¿qué fracción de su nueva votación se queda en el territorio
   donde ya era candidato? Y ¿cuánto crece su votación (el «gap»)?

   Lo que hace, en orden:
     1. Baja los índices de las cinco corporaciones para 2011-2015-2019-2023
        (las mismas fuentes que usa cand-index.js: se cargan de ahí para no
        mantener dos listas).
     2. Para cada salto y cada par de años Y → Y+4, empareja personas por
        `personaKey` (la misma llave que usa la web). Solo cuentan nombres de
        tres o más palabras que aparecen UNA sola vez en cada índice: «JOSE
        LUIS GARCIA» son treinta personas y no se puede saber cuál es cuál.
     3. Baja las mesas de ambas candidaturas y exige que el destino vote en
        el mismo municipio (JAL → Concejo) o departamento (→ Asamblea /
        Gobernación) en al menos el 90 %. Un homónimo de otra ciudad no pasa.
     4. arraigo = votos del destino en el territorio de origen ÷ votos del
        destino en el ámbito. Y, si el partido tiene lista en el destino (una
        entrada de partido en el índice) o hay resultados por área para 2023,
        neutro = lo mismo pero para el partido (o la participación), y
        lift = arraigo ÷ neutro: cuántas veces pesa el origen frente a lo que
        pesa para su partido. Es el número que consume candidato-360.js
        (repartoSalto), porque no depende del tamaño del origen.
     5. gap = votos del destino ÷ votos del origen.
     6. Escribe `saltos-arraigo.json` (medianas por departamento y nacional,
        con n) y `saltos-casos.csv` con cada caso para revisarlos a mano.

   Corre en la Mac con Node 18+ (usa fetch nativo). Cachea todo lo que baja en
   --cache para que la segunda corrida no vuelva a pedir nada.

     node tools/candidato-360/saltos/estudio.mjs
     node tools/candidato-360/saltos/estudio.mjs --salto jal>concejo --limite 40   (ensayo corto)

   Opciones: --salida DIR (default tools/candidato-360/saltos/salida)
             --cache DIR  (default ~/.cache/rr-saltos)
             --salto CLAVE (repetible; default los tres)
             --limite N    (máximo de pares por salto y par de años)
             --concurrencia N (default 8)
             --base URL    (origen de los datos; default el de platform-config.js)
   ═══════════════════════════════════════════════════════════════════════════ */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { homedir } from 'node:os';
import path from 'node:path';
import vm from 'node:vm';

/* ── Argumentos ──────────────────────────────────────────────────────────── */
const args = { salto: [] };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (!a.startsWith('--')) continue;
  const k = a.slice(2), v = process.argv[i + 1]; i++;
  if (k === 'salto') args.salto.push(v); else args[k] = v;
}
const AQUI = path.dirname(new URL(import.meta.url).pathname);
const REPO = path.resolve(AQUI, '../../..');
const BASE = (args.base || 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output').replace(/\/$/, '');
const SALIDA = path.resolve(args.salida || path.join(AQUI, 'salida'));
const CACHE = path.resolve(args.cache || path.join(homedir(), '.cache', 'rr-saltos'));
const LIMITE = Number(args.limite) || Infinity;
const CONCURRENCIA = Number(args.concurrencia) || 8;
const MIN_ORIGEN_EN_AMBITO = .9;   /* el destino debe votar en el ámbito del origen */
const SALTOS = {
  'jal>concejo':          { origen: 'jal',      destino: 'concejo',     unidad: 'localidad' },
  'concejo>asamblea':     { origen: 'concejo',  destino: 'asamblea',    unidad: 'municipio' },
  'alcaldia>gobernacion': { origen: 'alcaldia', destino: 'gobernacion', unidad: 'municipio' },
};
const CLAVES = args.salto.length ? args.salto : Object.keys(SALTOS);
for (const c of CLAVES) if (!SALTOS[c]) { console.error(`salto desconocido: ${c} (válidos: ${Object.keys(SALTOS).join(', ')})`); process.exit(2); }
const ANOS = [2011, 2015, 2019, 2023];
/* Nombre de la fuente en cand-index.js por corporación y año. */
const FUENTE = {
  jal:         { 2011: 'jal2011',  2015: 'jal2015',  2019: 'jal2019',  2023: 'jal' },
  concejo:     { 2011: 'conc2011', 2015: 'conc2015', 2019: 'conc2019', 2023: 'concejo' },
  asamblea:    { 2011: 'asam2011', 2015: 'asam2015', 2019: 'asam2019', 2023: 'asamblea' },
  alcaldia:    { 2011: 'alc2011',  2015: 'alc2015',  2019: 'alc2019',  2023: 'alc2023' },
  gobernacion: { 2011: 'gob2011',  2015: 'gob2015',  2019: 'gob2019',  2023: 'gob2023' },
};

/* ── El motor de la web, tal cual ────────────────────────────────────────
   El «neutro» contra el que se compara el arraigo tiene que ser EXACTAMENTE
   la base que usa candidato-360.js para repartir (huella del partido → bloque
   → participación). Si acá se midiera contra otra cosa, el lift no sería el
   multiplicador que la web necesita. Por eso se carga la sección 8 ter del
   propio archivo en vez de reescribirla. */
const ctxMotor = { window: {}, console };
vm.createContext(ctxMotor);
vm.runInContext(await readFile(path.join(REPO, 'partidos-bloques.js'), 'utf8'), ctxMotor);
{
  const js = await readFile(path.join(REPO, 'candidato-360.js'), 'utf8');
  const motor = js.slice(js.indexOf('/* ─── 8 ter.'), js.indexOf('/* ── El salto en el CRM'));
  const dv = js.slice(js.indexOf('function distributeVotes('), js.indexOf('function projectedVotesByArea('));
  vm.runInContext(`const PartidosBloques = window.PartidosBloques; ${dv}\n${motor}\nthis.baseDestino = baseDestino;`, ctxMotor);
}
const baseDestino = ctxMotor.baseDestino;

/* ── cand-index.js, tal cual lo usa la web ───────────────────────────────── */
const ctx = { window: { RRData: { publicUrl: p => `${BASE.replace(/\/congreso-2026\/output$/, '')}/${p}` } }, console };
vm.createContext(ctx);
vm.runInContext(await readFile(path.join(REPO, 'cand-index.js'), 'utf8'), ctx);
const CR = ctx.window.CandRegistry;
const fuentes = Object.fromEntries([...CR.SOURCES, ...CR.LOCAL_SOURCES].map(s => [s.name, s]));

/* ── Descarga con caché en disco y concurrencia acotada ─────────────────── */
await mkdir(CACHE, { recursive: true });
async function bajar(url) {
  const f = path.join(CACHE, createHash('sha1').update(url).digest('hex') + '.json');
  if (existsSync(f)) return JSON.parse(await readFile(f, 'utf8'));
  for (let intento = 0; intento < 4; intento++) {
    try {
      const r = await fetch(url);
      if (r.status === 404) { await writeFile(f, 'null'); return null; }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const txt = await r.text();
      await writeFile(f, txt);
      return JSON.parse(txt);
    } catch (e) { if (intento === 3) { console.warn(`  ✗ ${url}: ${e.message}`); return null; } await new Promise(r => setTimeout(r, 500 * 2 ** intento)); }
  }
}
async function enLotes(items, fn, n = CONCURRENCIA) {
  const out = new Array(items.length); let i = 0, hechos = 0;
  const t0 = Date.now();
  async function obrero() { while (i < items.length) { const j = i++; out[j] = await fn(items[j], j); hechos++; if (hechos % 50 === 0) process.stdout.write(`\r    ${hechos}/${items.length} (${((Date.now() - t0) / 1000).toFixed(0)} s)`); } }
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, obrero));
  if (items.length >= 50) process.stdout.write('\n');
  return out;
}

/* ── Índices ─────────────────────────────────────────────────────────────── */
const indices = {};
async function indice(corp, ano) {
  const nombre = FUENTE[corp]?.[ano]; const src = fuentes[nombre];
  if (!src) return null;
  const k = `${corp}:${ano}`;
  if (indices[k]) return indices[k];
  const base = `${BASE}/${src.dir}`;
  const raw = await bajar(`${base}/${src.indexFile}`);
  const lista = raw ? src.list(raw).map(c => ({ ...c, dataUrl: `${base}/${c.slug}.json` })) : [];
  indices[k] = lista;
  return lista;
}

const normPartido = s => CR.normPersona(String(s || '').replace(/^(PARTIDO|MOVIMIENTO|COALICION)\s+/i, ''));

/* ── Geografía de las mesas ─────────────────────────────────────────────── */
const dep2 = m => String(m.dep || '').padStart(2, '0');
const mun3 = m => String(m.mun || '').padStart(3, '0');
const munKey = m => `${dep2(m)}-${mun3(m)}`;
const locKey = m => String(m.com || m.zon || '').padStart(2, '0');
function sumaPor(mesas, llave) {
  const s = {}; for (const m of mesas) { const k = llave(m); if (!k) continue; s[k] = (s[k] || 0) + (Number(m.v) || 0); } return s;
}
const total = o => Object.values(o).reduce((a, b) => a + b, 0);
const mayor = o => Object.entries(o).sort((a, b) => b[1] - a[1])[0]?.[0];
async function mesasDe(c) { const d = await bajar(c.dataUrl); return Array.isArray(d?.mesas) ? d.mesas : Array.isArray(d) ? d : []; }

/* El territorio de origen y la fracción del destino que cae en él. */
function medir(unidad, mesasOrigen, mesasDestino) {
  const porMun = sumaPor(mesasOrigen, munKey); if (!total(porMun)) return null;
  const munOrigen = mayor(porMun), depOrigen = munOrigen.slice(0, 2);
  const ambitoDe = unidad === 'localidad' ? munKey : dep2;
  const ambitoOrigen = unidad === 'localidad' ? munOrigen : depOrigen;
  const destinoAmbito = mesasDestino.filter(m => ambitoDe(m) === ambitoOrigen);
  const vDestino = total(sumaPor(mesasDestino, ambitoDe)), vAmbito = total(sumaPor(destinoAmbito, ambitoDe));
  if (!vDestino || vAmbito / vDestino < MIN_ORIGEN_EN_AMBITO) return { descartado: 'el destino vota fuera del ámbito del origen', vDestino, vAmbito };
  let origenKey, enOrigen;
  if (unidad === 'localidad') {
    const porLoc = sumaPor(mesasOrigen.filter(m => munKey(m) === munOrigen), locKey);
    origenKey = mayor(porLoc); if (!origenKey) return null;
    enOrigen = total(sumaPor(destinoAmbito.filter(m => locKey(m) === origenKey), locKey));
  } else {
    origenKey = munOrigen;
    enOrigen = total(sumaPor(destinoAmbito.filter(m => munKey(m) === munOrigen), munKey));
  }
  return { dep: depOrigen, mun: munOrigen, origenKey, ambitoOrigen, vDestino, vAmbito, enOrigen, arraigo: enOrigen / vAmbito };
}
/* El NEUTRO: qué peso tendría el territorio de origen si esa candidatura
   repartiera como reparte la web —la huella de su partido en la corporación
   de destino (2023), o su bloque, o la participación—. Solo existe para
   destinos 2023: los resultados por área son de esa elección. */
const resultadosCache = {};
async function neutroBase(unidad, medida, candidatoDestino) {
  const url = unidad === 'localidad' ? `${BASE}/concejo-2023/resultados-concejo-2023.json` : `${BASE}/asamblea-2023/dep/${medida.dep}.json`;
  if (!(url in resultadosCache)) resultadosCache[url] = await bajar(url);
  const r = resultadosCache[url]; if (!r) return null;
  const porArea = unidad === 'localidad' ? r?.data?.[medida.mun]?.comunas : r?.comunas;
  if (!porArea || Object.keys(porArea).length < 2) return null;
  const base = baseDestino({ porArea, partido: candidatoDestino.partido, nombreCandidato: candidatoDestino.nombre });
  if (!base) return null;
  const llave = unidad === 'localidad' ? medida.origenKey : medida.mun.slice(3);
  const peso = base.proporciones[llave] ?? base.proporciones[String(Number(llave))];
  return peso == null ? null : { peso, capa: base.capa, etiqueta: base.etiqueta };
}

/* ── Emparejar personas Y → Y+4 ─────────────────────────────────────────── */
function unicos(lista) {
  const por = new Map();
  for (const c of lista) {
    if (CR.isPartyEntry(c) || c.tipo === 'partido') continue;
    const k = CR.personaKey(c.nombre); if (k.split(' ').length < 3) continue;
    por.set(k, por.has(k) ? null : c);
  }
  return por;
}

const casos = [];
for (const clave of CLAVES) {
  const S = SALTOS[clave];
  console.log(`\n═══ ${clave} (${S.unidad})`);
  for (const y of ANOS) {
    const y2 = y + 4; if (!ANOS.includes(y2)) continue;
    process.stdout.write(`  ${y} → ${y2}: índices… `);
    const [io, id] = await Promise.all([indice(S.origen, y), indice(S.destino, y2)]);
    if (!io?.length || !id?.length) { console.log('sin datos'); continue; }
    const uo = unicos(io), ud = unicos(id);
    let pares = [...uo.entries()].filter(([k, c]) => c && ud.get(k)).map(([k, c]) => ({ k, a: c, b: ud.get(k) }));
    if (pares.length > LIMITE) pares = pares.sort(() => Math.random() - .5).slice(0, LIMITE);
    console.log(`${io.length} y ${id.length} candidaturas, ${pares.length} nombres únicos en ambos`);
    const medidas = await enLotes(pares, async ({ k, a, b }) => {
      const [ma, mb] = await Promise.all([mesasDe(a), mesasDe(b)]);
      if (!ma.length || !mb.length) return null;
      const m = medir(S.unidad, ma, mb); if (!m || m.descartado) return null;
      const nb = y2 === 2023 ? await neutroBase(S.unidad, m, b) : null;
      const neutro = nb?.peso ?? null, neutroFuente = nb?.capa || '';
      const va = Number(a.votos) || 0, vb = Number(b.votos) || 0;
      return { salto: clave, anoOrigen: y, anoDestino: y2, persona: k, nombre: b.nombre, dep: m.dep, municipio: m.mun, origen: m.origenKey,
        partidoOrigen: a.partido || '', partidoDestino: b.partido || '', mismoPartido: normPartido(a.partido) === normPartido(b.partido),
        votosOrigen: va, votosDestino: vb, gap: va > 0 && vb > 0 ? vb / va : null,
        votosDestinoAmbito: m.vAmbito, votosDestinoEnOrigen: m.enOrigen, arraigo: m.arraigo, neutro, neutroFuente, lift: neutro > 0 ? m.arraigo / neutro : null };
    });
    const validos = medidas.filter(Boolean);
    console.log(`    ${validos.length} casos válidos (con neutro: ${validos.filter(c => c.neutro != null).length})`);
    casos.push(...validos);
  }
}

/* ── Agregar ─────────────────────────────────────────────────────────────── */
const cuantil = (xs, q) => { const s = xs.filter(x => Number.isFinite(x)).sort((a, b) => a - b); if (!s.length) return null; const p = (s.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return +(s[lo] + (s[hi] - s[lo]) * (p - lo)).toFixed(4); };
function resumen(cs) {
  /* El lift es lo que multiplica repartoSalto: el origen pesa lift × su peso
     en la base. Se mide contra la MISMA base que usa la web, así que entran
     todos los casos que tuvieron neutro, sea cual sea la capa. */
  const lifts = cs.map(c => c.lift).filter(x => Number.isFinite(x));
  const gaps = cs.map(c => c.gap).filter(x => Number.isFinite(x));
  return { n: cs.length, arraigo_mediana: cuantil(cs.map(c => c.arraigo), .5), arraigo_p25: cuantil(cs.map(c => c.arraigo), .25), arraigo_p75: cuantil(cs.map(c => c.arraigo), .75),
    lift_n: lifts.length, lift_mediana: cuantil(lifts, .5), lift_p25: cuantil(lifts, .25), lift_p75: cuantil(lifts, .75),
    gap_n: gaps.length, gap_mediana: cuantil(gaps, .5), gap_p25: cuantil(gaps, .25), gap_p75: cuantil(gaps, .75) };
}
const tabla = { _generado: new Date().toISOString().slice(0, 10), _metodo: 'mediana por candidatura; arraigo = fracción de la votación de destino que cae en el territorio de origen; lift = arraigo ÷ el peso del origen en la base con que reparte la web (huella del partido → bloque → participación, 2023); gap = votos destino ÷ votos origen; solo saltos Y→Y+4' };
for (const clave of CLAVES) {
  const cs = casos.filter(c => c.salto === clave); if (!cs.length) continue;
  const t = { _nacional: resumen(cs) };
  for (const dep of new Set(cs.map(c => c.dep))) t[String(Number(dep))] = resumen(cs.filter(c => c.dep === dep));
  tabla[clave] = t;
}
await mkdir(SALIDA, { recursive: true });
await writeFile(path.join(SALIDA, 'saltos-arraigo.json'), JSON.stringify(tabla, null, 1));
const cols = ['salto', 'anoOrigen', 'anoDestino', 'persona', 'nombre', 'dep', 'municipio', 'origen', 'partidoOrigen', 'partidoDestino', 'mismoPartido', 'votosOrigen', 'votosDestino', 'gap', 'votosDestinoAmbito', 'votosDestinoEnOrigen', 'arraigo', 'neutro', 'neutroFuente', 'lift'];
const csv = v => v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
await writeFile(path.join(SALIDA, 'saltos-casos.csv'), [cols.join(','), ...casos.map(c => cols.map(k => csv(typeof c[k] === 'number' ? +c[k].toFixed(4) : c[k])).join(','))].join('\n') + '\n');

console.log('\n═══ Resumen');
for (const clave of CLAVES) {
  const t = tabla[clave]; if (!t) { console.log(`  ${clave}: sin casos`); continue; }
  const n = t._nacional;
  console.log(`  ${clave}: n=${n.n} · arraigo mediana ${n.arraigo_mediana} [${n.arraigo_p25}–${n.arraigo_p75}] · lift mediana ${n.lift_mediana ?? '—'} (n=${n.lift_n}) · gap mediana ${n.gap_mediana ?? '—'}`);
  const deps = Object.entries(t).filter(([k]) => k !== '_nacional').sort((a, b) => b[1].n - a[1].n).slice(0, 8);
  for (const [d, r] of deps) console.log(`      dep ${d.padStart(2, '0')}: n=${r.n} · arraigo ${r.arraigo_mediana} · lift ${r.lift_mediana ?? '—'} (n=${r.lift_n}) · gap ${r.gap_mediana ?? '—'}`);
}
console.log(`\nEscrito ${path.join(SALIDA, 'saltos-arraigo.json')} y saltos-casos.csv`);
console.log(`Para publicarlo:\n  aws s3 cp "${path.join(SALIDA, 'saltos-arraigo.json')}" s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/candidato-360/saltos-arraigo.json --content-type application/json --cache-control max-age=3600`);
