/* clasificar-locales.mjs — de qué familia política es un movimiento regional.
   ------------------------------------------------------------------
   `partidos-bloques.js` clasifica los partidos nacionales. Con eso, el 22,3 %
   de los votos de la Asamblea 2023 quedaba «sin clasificar»: coaliciones
   («CAMBIO RADICAL - MIRA»), movimientos regionales cuyo nombre no dice nada
   («Córdoba Florece», «Renace») y partidos que prestan el aval (ASI, MAIS,
   AICO). Un 22 % gris en la lectura ideológica de un territorio no es un
   matiz: es no haber leído.

   Las coaliciones las resuelve el propio diccionario por sus partes. Para los
   movimientos regionales no hay tabla que consultar, así que el bloque no se
   adivina: se MIDE. La pregunta es «¿de dónde vienen los que se lanzaron con
   ese aval?»:

     1. se toman los candidatos de 2023 de esa organización;
     2. se buscan esas MISMAS personas en las otras elecciones del índice
        (asamblea, concejo, JAL, alcaldía y gobernación, 2011-2023);
     3. de cada persona se toma el bloque más repetido entre sus otros avales
        —solo los ya clasificados—;
     4. la organización entra a la tabla si al menos MIN_PERSONAS dejan rastro
        y MIN_ACUERDO de ellas apuntan al mismo bloque.

   Lo que no pasa el corte se queda sin bloque, y eso también es un resultado:
   de las 848 personas con rastro que se lanzaron con ASI en 2023, el bloque
   más repetido reúne el 35 % —MAIS 31 %, AICO 34 %—, o sea que sus candidatos
   vienen de todos lados. Esos avales no tienen línea y la interfaz lo dice
   así, en vez de fingir que no los hemos mirado.

   Uso:
     NODE_USE_ENV_PROXY=1 node tools/candidato-360/partidos/clasificar-locales.mjs
     [--min-personas=5] [--min-acuerdo=0.6] [--min-votos=5000] [--cache=DIR]

   Imprime la tabla lista para pegar en MOVIMIENTO_LOCAL y, aparte, la medición
   de los avales sin línea. Necesita red hacia S3 (la primera vez baja ~65 MB de
   índices y los deja en caché).                                              */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const MIN_PERSONAS = Number(args['min-personas'] || 5);
const MIN_ACUERDO = Number(args['min-acuerdo'] || .6);
const MIN_VOTOS = Number(args['min-votos'] || 5000);
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const CACHE = path.resolve(args.cache || path.join(homedir(), '.cache', 'rr-indices'));
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
await mkdir(CACHE, { recursive: true });

/* El MISMO diccionario que usa la web: dos tablas serían dos opiniones. */
const PB = (() => { const ctx = { window: {} }; vm.createContext(ctx); vm.runInContext(readFileSync(path.join(REPO, 'partidos-bloques.js'), 'utf8'), ctx); return ctx.window.PartidosBloques; })();

async function bajar(ruta) {
  const f = path.join(CACHE, ruta.replace(/\//g, '__'));
  if (existsSync(f)) return JSON.parse(await readFile(f, 'utf8'));
  const r = await fetch(`${S3}/${ruta}`, { headers: { 'accept-encoding': 'identity' } });
  if (!r.ok) throw new Error(`HTTP ${r.status} · ${ruta}`);
  const txt = await r.text();
  await writeFile(f, txt);
  console.error(`  ↓ ${ruta.split('/').pop()} (${(txt.length / 1e6).toFixed(1)} MB)`);
  return JSON.parse(txt);
}

/* Los índices de candidaturas: el rastro de cada persona. */
const INDICES = [
  'asamblea-2023/index-asamblea-2023.json', 'asamblea-2019/index-asamblea-2019.json', 'asamblea-2015/index-asamblea-2015.json', 'asamblea-2011/index-asamblea-2011.json',
  'concejo-2023/index-concejo-2023.json', 'concejo-2019/index-concejo-2019.json', 'concejo-2015/index-concejo-2015.json',
  'jal-2023/index-jal-2023.json', 'jal-2019/index-jal-2019.json',
  'alcaldia-2023/index-alcaldia-2023.json', 'alcaldia-2019/index-alcaldia-2019.json',
  'gobernacion-2023/index-gobernacion-2023.json', 'gobernacion-2019/index-gobernacion-2019.json', 'gobernacion-2015/index-gobernacion-2015.json',
];
/* Y los resultados, para pesar cada organización por votos de verdad. */
const DEPS = ['01', '03', '05', '07', '09', '11', '12', '13', '15', '17', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '40', '44', '46', '48', '50', '52', '54', '56', '60', '64', '68', '72'];

const clave = n => String(n || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z ]/g, ' ').split(/\s+/).filter(Boolean).join(' ');
const porPersona = new Map(), candidatos2023 = new Map();
for (const ruta of INDICES) {
  let d; try { d = await bajar(ruta); } catch (e) { console.error(`  · sin ${ruta.split('/').pop()}: ${e.message}`); continue; }
  const año = (ruta.match(/(\d{4})/) || [])[1];
  for (const c of (d.candidatos || d)) {
    const k = clave(c.nombre); if (!k || k.split(' ').length < 3) continue;
    const b = PB.bloqueDeOrganizacion(c.partido);
    if (!porPersona.has(k)) porPersona.set(k, []);
    porPersona.get(k).push(b);
    if (año === '2023' && b === 'sc') { const o = PB.norm(c.partido); if (!candidatos2023.has(o)) candidatos2023.set(o, new Set()); candidatos2023.get(o).add(k); }
  }
}
const votos = {};
for (const dep of DEPS) {
  let d; try { d = await bajar(`asamblea-2023/dep/${dep}.json`); } catch (e) { continue; }
  for (const a of Object.values(d.comunas || {})) for (const [n, v] of (a.partidos || [])) votos[PB.norm(n)] = (votos[PB.norm(n)] || 0) + (Number(v) || 0);
}

const filas = [];
for (const [org, personas] of candidatos2023) {
  const cuenta = {}; let conRastro = 0;
  for (const k of personas) {
    const otros = (porPersona.get(k) || []).filter(b => b !== 'sc');
    if (!otros.length) continue;
    conRastro++;
    const c = {}; otros.forEach(b => { c[b] = (c[b] || 0) + 1; });
    const dom = Object.entries(c).sort((a, b) => b[1] - a[1])[0][0];
    cuenta[dom] = (cuenta[dom] || 0) + 1;
  }
  const orden = Object.entries(cuenta).sort((a, b) => b[1] - a[1]);
  filas.push({ org, personas: personas.size, conRastro, bloque: orden[0]?.[0] || '', acuerdo: orden[0] ? orden[0][1] / conRastro : 0, votos: votos[PB.norm(org)] || 0 });
}
filas.sort((a, b) => b.votos - a.votos);

const pasan = filas.filter(f => f.votos >= MIN_VOTOS && f.conRastro >= MIN_PERSONAS && f.acuerdo >= MIN_ACUERDO && !PB.esAvalAmplio(f.org));
console.log(`\n/* Para MOVIMIENTO_LOCAL (≥${MIN_VOTOS} votos, ≥${MIN_PERSONAS} personas con rastro, ≥${Math.round(MIN_ACUERDO * 100)} % de acuerdo) */`);
for (const f of pasan) console.log(`  '${f.org}': '${f.bloque}',`.padEnd(56) + `// ${f.votos.toLocaleString('es-CO')} votos · ${Math.round(f.acuerdo * 100)} % de ${f.conRastro}`);

console.log('\nAvales sin línea (mucho rastro, ningún bloque dominante):');
for (const f of filas.filter(x => x.conRastro >= 100).slice(0, 8)) console.log(`  ${String(f.votos).padStart(8)} votos · el bloque más repetido reúne ${Math.round(f.acuerdo * 100)} % de ${f.conRastro} personas · ${f.org}`);

const sinBloque = filas.filter(f => f.votos >= MIN_VOTOS && !pasan.includes(f));
const totalSin = sinBloque.reduce((s, f) => s + f.votos, 0);
console.log(`\nQuedan sin bloque ${sinBloque.length} organizaciones con ${totalSin.toLocaleString('es-CO')} votos. Las diez más grandes:`);
for (const f of sinBloque.slice(0, 10)) console.log(`  ${String(f.votos).padStart(8)} · rastro ${String(f.conRastro).padStart(3)} · acuerdo ${Math.round(f.acuerdo * 100)} % · ${f.org}`);
