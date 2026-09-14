/* construir.mjs — el catálogo de partidos POR DEPARTAMENTO.
   ═══════════════════════════════════════════════════════════════════════════
   A nivel nacional hay más de mil organizaciones inscritas en las
   territoriales de 2023, y muchas se repiten con el mismo nombre en distinto
   orden entre un departamento y otro («MOVIMIENTO X - PARTIDO Y» acá,
   «PARTIDO Y - MOVIMIENTO X» allá). Un desplegable nacional con esa lista es
   inservible: nadie encuentra su partido y quien lo encuentra suele elegir el
   homónimo de otro departamento.

   Este script baja los cinco índices territoriales de 2023 (Concejo, JAL,
   Asamblea, Alcaldía, Gobernación) y arma, para cada departamento, la lista de
   organizaciones que efectivamente inscribieron candidatura allí, con cuántas
   inscribieron. El código de departamento sale del slug: el segundo segmento
   (ASAM2023-31-8-51 → 31 = Valle) es el código ELECTORAL, el mismo que usa el
   resto de la plataforma.

   Y le suma la CÁMARA DE 2026, que es lo que dice qué partidos están vivos
   HOY: Salvación Nacional no existía en 2023 y sacó 190.113 votos en Bogotá.
   De cada `camara/dep-XX.json` se toma `por_circunscripcion.TERRITORIAL`, no
   el total: las listas de las circunscripciones especiales (consejos
   comunitarios, indígenas) no son organizaciones que avalen una candidatura
   territorial de 2027. Cuando una organización está en las dos fuentes, la
   etiqueta que se muestra es la de 2026: es su nombre vigente.

   Escribe un archivo por departamento en `candidato-360-data/partidos/`, que la
   página carga bajo demanda: Bogotá son 3 KB, no los 196 KB del país entero.
   Va en el repo y no en S3 porque pesa poco y porque es catálogo de interfaz:
   si no carga, no hay autocompletado y el campo queda en texto libre.

     node tools/candidato-360/partidos/construir.mjs
     node tools/candidato-360/partidos/construir.mjs --salida otra/carpeta
   ═══════════════════════════════════════════════════════════════════════════ */
import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const args = {};
for (let i = 2; i < process.argv.length; i++) if (process.argv[i].startsWith('--')) args[process.argv[i].slice(2)] = process.argv[++i];
const AQUI = path.dirname(new URL(import.meta.url).pathname);
const REPO = path.resolve(AQUI, '../../..');
const BASE = (args.base || 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output').replace(/\/$/, '');
const SALIDA = path.resolve(args.salida || path.join(REPO, 'candidato-360-data/partidos'));

const FUENTES = [
  { dir: 'concejo-2023',     archivo: 'index-concejo-2023.json',     corp: 'concejo' },
  { dir: 'jal-2023',         archivo: 'index-jal-2023.json',         corp: 'jal' },
  { dir: 'asamblea-2023',    archivo: 'index-asamblea-2023.json',    corp: 'asamblea' },
  { dir: 'alcaldia-2023',    archivo: 'index-alcaldia-2023.json',    corp: 'alcaldia' },
  { dir: 'gobernacion-2023', archivo: 'index-gobernacion-2023.json', corp: 'gobernacion' },
];

/* El nombre se guarda TAL CUAL viene de la Registraduría (es lo que la persona
   reconoce), pero se deduplica por una llave normalizada: sin tildes, sin
   puntuación y con las palabras ordenadas. Así «PARTIDO A - MOVIMIENTO B» y
   «MOVIMIENTO B - PARTIDO A» son la misma organización, que es el problema que
   motivó todo esto. Gana como etiqueta la forma más frecuente. */
const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9ÑÜ ]+/g, ' ').replace(/\s+/g, ' ').trim();
/* Se quitan SOLO las palabras estructurales. «COALICIÓN», «ALIANZA» o «POR» se
   conservan: en los movimientos locales cargan significado y quitarlas fundía
   organizaciones distintas («COALICIÓN POR BOGOTÁ» con «MOVIMIENTO BOGOTÁ»). */
const RUIDO = new Set(['PARTIDO', 'MOVIMIENTO', 'POLITICO', 'POLITICA', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'Y']);
function llave(nombre) {
  const palabras = norm(nombre).split(' ').filter(w => w && !RUIDO.has(w));
  return (palabras.length ? palabras : norm(nombre).split(' ')).sort().join(' ');
}

const porDep = new Map();        /* dep → Map(llave → {formas, n, votos2026, corps}) */
const nacional = new Map();
const DEPS = ['01', '03', '05', '07', '09', '11', '12', '13', '15', '16', '17', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '40', '44', '46', '48', '50', '52', '54', '56', '60', '64', '68', '72'];
const nombreDep = new Map();     /* dep → nombre, para reconocer la variante regional */

async function baja(url) {
  for (let i = 0; i < 4; i++) {
    try { const r = await fetch(url); if (!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
    catch (e) { if (i === 3) { console.warn(`  ✗ ${url}: ${e.message}`); return null; } await new Promise(r => setTimeout(r, 600 * 2 ** i)); }
  }
}
function anota(mapa, nombre, corp) {
  const k = llave(nombre); if (!k) return null;
  if (!mapa.has(k)) mapa.set(k, { formas: new Map(), n: 0, votos2026: 0, etiqueta2026: '', corps: new Set() });
  const e = mapa.get(k);
  e.formas.set(nombre, (e.formas.get(nombre) || 0) + 1);
  e.n++; e.corps.add(corp);
  return e;
}

for (const f of FUENTES) {
  process.stdout.write(`· ${f.dir} … `);
  const raw = await baja(`${BASE}/${f.dir}/${f.archivo}`);
  const lista = raw?.candidatos || (Array.isArray(raw) ? raw : []);
  let usados = 0;
  for (const c of lista) {
    const partido = String(c.partido || '').trim(); if (!partido) continue;
    const dep = String(c.slug || '').split('-')[1];        /* código ELECTORAL */
    if (!dep || !/^\d+$/.test(dep)) continue;
    const clave = String(Number(dep));
    if (!porDep.has(clave)) porDep.set(clave, new Map());
    anota(porDep.get(clave), partido, f.corp);
    anota(nacional, partido, f.corp);
    usados++;
  }
  console.log(`${lista.length} candidaturas, ${usados} con partido y departamento`);
}

/* La Cámara de 2026, por departamento: quién está vivo hoy y con cuánto. */
for (const dep of DEPS) {
  const d = await baja(`${BASE}/camara/dep-${dep}.json`);
  const partidos = d?.por_circunscripcion?.TERRITORIAL?.partidos || d?.partidos;
  if (!partidos) { console.log(`· cámara 2026 dep ${dep}: sin datos`); continue; }
  const clave = String(Number(dep));
  nombreDep.set(clave, d.nombre || '');
  if (!porDep.has(clave)) porDep.set(clave, new Map());
  for (const [nombre, votos] of Object.entries(partidos)) {
    for (const mapa of [porDep.get(clave), nacional]) {
      const e = anota(mapa, nombre, 'camara2026');
      if (!e) continue;
      e.n--;                                   /* la Cámara no es una candidatura territorial: no infla el conteo de 2023 */
      e.votos2026 += Number(votos) || 0;
      e.etiqueta2026 = nombre;                 /* el nombre vigente manda sobre el de 2023 */
    }
  }
}
console.log(`· cámara 2026 · ${DEPS.length} departamentos`);

/* ── La sucursal regional de un partido nacional ─────────────────────────────
   En 2023 el Pacto se inscribió en Bogotá como «PACTO HISTÓRICO BOGOTÁ» y en
   2026 la lista se llama «MOVIMIENTO POLÍTICO PACTO HISTÓRICO»: es la misma
   organización y quedaban como dos.

   La regla se aplica SOLO si al quitar el nombre del departamento queda un
   nombre que YA EXISTE en ese mismo departamento. Sin esa condición, quitar
   «Bogotá» a diestra y siniestra fundiría movimientos que no son sucursal de
   nada: «BOGOTÁ ENTRE TODOS» y «BOGOTÁ MÁS FUERTE» son ellos mismos, y su
   nombre ES la ciudad.

   Y lo que queda tiene que tener DOS palabras o más. Con una sola, cualquier
   movimiento regional cae en un genérico: «FUERZA TOLIMA» aterrizaba en «LA
   FUERZA» y «ALMA DEL HUILA» en «ALMA», que no son sus casas matrices. */
function fundirVariantesRegionales(mapa, nombre, etiqueta) {
  const tokens = new Set(norm(nombre).split(' ').filter(w => w.length > 2 && !RUIDO.has(w)));
  if (!tokens.size) return [];
  const hechas = [];
  for (const [k, e] of [...mapa.entries()]) {
    const palabras = k.split(' '), sinDep = palabras.filter(w => !tokens.has(w));
    if (sinDep.length === palabras.length || sinDep.length < 2) continue;
    const destino = mapa.get(sinDep.join(' '));
    if (!destino || destino === e) continue;
    for (const [forma, n] of e.formas) destino.formas.set(forma, (destino.formas.get(forma) || 0) + n);
    destino.n += e.n; destino.votos2026 += e.votos2026;
    destino.etiqueta2026 = destino.etiqueta2026 || e.etiqueta2026;
    e.corps.forEach(c => destino.corps.add(c));
    mapa.delete(k);
    hechas.push(`${etiqueta}: ${[...e.formas.keys()].join(' / ')} → ${destino.etiqueta2026 || [...destino.formas.keys()][0]}`);
  }
  return hechas;
}
const fundidas = [];
for (const [dep, mapa] of porDep) {
  const nombre = nombreDep.get(dep); if (!nombre) continue;
  fundidas.push(...fundirVariantesRegionales(mapa, nombre, nombre));
  fundirVariantesRegionales(nacional, nombre, nombre);
}
console.log(`· ${fundidas.length} variantes regionales fundidas con su partido nacional`);
for (const f of fundidas.slice(0, 10)) console.log(`    ${f}`);

/* ── Coaliciones ─────────────────────────────────────────────────────────────
   «PARTIDO CAMBIO RADICAL - PARTIDO POLITICO MIRA» es una lista de coalición,
   no una organización con la que alguien «se lanza». Se marcan para que la
   página no las ofrezca en la selección, pero se quedan en el catálogo: sí
   sirven para medir la huella de cada partido en el territorio.

   Es coalición si empieza por «COALICIÓN» o si, partida por sus separadores
   (guion, «y», «+»), DOS o más de sus partes existen por sí solas como
   organización en el país. La condición de las dos partes es lo que salva a
   «PARTIDO DE LA UNIÓN POR LA GENTE - PARTIDO DE LA U», que lleva guion y es
   un solo partido. */
const partesDe = n => String(n).normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/^COALICION\s+/, '').replace(/^PARTIDOS\s+/, '').split(/\s*[-+\/|,]\s*|\s+Y\s+/).map(x => x.trim()).filter(x => x.length >= 2);
/* Partidos conocidos: los que aparecen solos en algún índice, más el
   diccionario curado de partidos-bloques.js (el mismo de alcaldias-2023),
   que trae las formas cortas que en los índices solo salen dentro de una
   coalición: «PARTIDO DE LA U», «PARTIDO CONSERVADOR». */
const solas = new Set();
{
  const vm = await import('node:vm');
  const ctx = { window: {} }; vm.createContext(ctx);
  vm.runInContext(await (await import('node:fs/promises')).readFile(path.join(REPO, 'partidos-bloques.js'), 'utf8'), ctx);
  for (const nombre of Object.keys(ctx.window.PartidosBloques?.PARTIDO_BLOQUE || {})) solas.add(llave(nombre));
}
for (const e of nacional.values()) for (const forma of e.formas.keys()) if (partesDe(forma).length === 1 && !/^COALICI/.test(norm(forma))) solas.add(llave(forma));
/* Una parte es un partido conocido si su llave existe tal cual, o si todas sus
   palabras caben en la llave de uno conocido: «PARTIDO CONSERVADOR» ⊂
   «PARTIDO CONSERVADOR COLOMBIANO». Sin esto, la mitad de las coaliciones del
   conservatismo —que la Registraduría escribe de veinte formas— se colaban. */
const solasPalabras = [...solas].map(k => new Set(k.split(' ')));
const conocida = parte => { const k = llave(parte); if (solas.has(k)) return true; const w = k.split(' ').filter(Boolean); return w.length > 0 && w.every(x => x.length >= 4) && solasPalabras.some(set => w.every(x => set.has(x))); };
const esCoalicion = nombre => /^COALICI/.test(norm(nombre)) || partesDe(nombre).filter(conocida).length >= 2;

/* [nombre, candidaturas 2023, votos a Cámara 2026, coalición]. Se recortan
   los ceros del final para que el archivo no cargue con datos que no dicen
   nada; la marca de coalición solo va cuando es 1. */
const ordenar = mapa => [...mapa.values()]
  .map(e => ({
    nombre: e.etiqueta2026 || [...e.formas.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'es'))[0][0],
    n: e.n, votos2026: e.votos2026,
  }))
  .sort((a, b) => b.votos2026 - a.votos2026 || b.n - a.n || a.nombre.localeCompare(b.nombre, 'es'))
  .map(e => { const fila = e.votos2026 ? [e.nombre, e.n, e.votos2026] : [e.nombre, e.n]; if (esCoalicion(e.nombre)) { while (fila.length < 3) fila.push(0); fila.push(1); } return fila; });

/* Un archivo por departamento: la página carga solo el suyo. */
await mkdir(SALIDA, { recursive: true });
const { statSync } = await import('node:fs');
const cabecera = dep => `/* Partidos y movimientos vivos en el departamento ${dep} (código ELECTORAL):
   los que inscribieron candidatura en las territoriales de 2023 y los que
   sacaron votos a la Cámara en 2026. Cada entrada es
   [nombre, candidaturas de 2023, votos a Cámara 2026]. Lo construye
   tools/candidato-360/partidos/construir.mjs — no se edita a mano.
   Un cuarto campo en 1 marca una COALICIÓN: no se ofrece al elegir, pero
   cuenta para la huella del partido. */\n`;
let total = 0, bytes = 0;
for (const [dep, mapa] of [...porDep.entries()].sort((a, b) => Number(a[0]) - Number(b[0]))) {
  const lista = ordenar(mapa), archivo = path.join(SALIDA, `${dep.padStart(2, '0')}.js`);
  await writeFile(archivo, `${cabecera(dep.padStart(2, '0'))}window.Candidato360Partidos=window.Candidato360Partidos||{};window.Candidato360Partidos["${dep.padStart(2, '0')}"]=${JSON.stringify(lista)};\n`);
  total++; bytes += statSync(archivo).size;
}
console.log(`\n${total} departamentos · ${nacional.size} organizaciones distintas en el país · ${(bytes / 1024).toFixed(0)} KB en total`);
for (const [dep, mapa] of [...porDep.entries()].sort((a, b) => Number(a[0]) - Number(b[0]))) {
  if (!['16', '1', '31', '15'].includes(dep)) continue;
  const lista = ordenar(mapa);
  const soloCamara = lista.filter(e => e[2] && !e[1]).length, coaliciones = lista.filter(e => e[3] === 1).length;
  console.log(`  dep ${dep.padStart(2, '0')}: ${lista.length} organizaciones (${soloCamara} solo en Cámara 2026, ${coaliciones} coaliciones que no se ofrecen) · ${(statSync(path.join(SALIDA, `${dep.padStart(2, '0')}.js`)).size / 1024).toFixed(1)} KB · top: ${lista.slice(0, 3).map(([n, c, v]) => `${n} (${v ? v.toLocaleString('es-CO') + ' votos 2026' : c + ' candidaturas 2023'})`).join(' · ')}`);
}
/* Las fusiones, para poder auditarlas: si dos organizaciones distintas caen en
   la misma llave, acá se ve. */
const fusiones = [...nacional.entries()].filter(([, e]) => e.formas.size > 1).sort((a, b) => b[1].formas.size - a[1].formas.size).slice(0, 12);
console.log(`\n${[...nacional.values()].filter(e => e.formas.size > 1).length} organizaciones tenían el nombre escrito de más de una forma. Las mayores:`);
for (const [, e] of fusiones) console.log(`  · ${[...e.formas.keys()].join('  |  ')}`);
console.log(`\nEscrito ${SALIDA}/`);
