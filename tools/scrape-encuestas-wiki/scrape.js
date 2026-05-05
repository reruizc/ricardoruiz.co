#!/usr/bin/env node
/**
 * scrape-encuestas-wiki — extrae las encuestas presidenciales 1ra vuelta
 * desde la tabla de Wikipedia (sección "Oficialización de candidaturas").
 *
 * Uso:
 *   node scrape.js                 → JSON a stdout
 *   node scrape.js --csv           → filas a stdout en formato encuestas_porcentajes.csv
 *   node scrape.js --diff          → reporta encuestas que NO están en
 *                                    Bases de datos/encuestas_porcentajes.csv
 *   node scrape.js --diff --csv    → imprime SÓLO las filas CSV nuevas
 *                                    (listas para append)
 *
 * Sin dependencias externas — corre con `node` (>= 18 por fetch nativo).
 *
 * Diseño:
 *   1. Pide el wikitext crudo vía MediaWiki action API (no parsing HTML).
 *   2. Recorta a la subsección "Oficialización de candidaturas" donde
 *      vive la tabla canónica post-13 mar 2026.
 *   3. Parte la tabla por separador `|-` y mapea cada celda al header de
 *      candidatos hardcoded (el orden de columnas de Wikipedia es estable
 *      mientras no agreguen un nuevo aspirante a esa tabla).
 *   4. Para cada fila parsea pollster (con <ref>), fecha (último día del
 *      rango "X-Y Mes 2026") y muestra (n_muestra). Las celdas inválidas
 *      ({{celda|N/A}}, vacías) → null.
 *   5. Output: array de polls. Cada poll tiene { id, firma, fecha_fin, n,
 *      cands: { Cepeda: …, … } }.
 */

const WIKI_PAGE = 'Anexo:Sondeos_de_intención_de_voto_para_las_elecciones_presidenciales_de_Colombia_de_2026';
const API_URL = `https://es.wikipedia.org/w/api.php?action=parse&page=${encodeURIComponent(WIKI_PAGE)}&prop=wikitext&format=json&formatversion=2`;

// Orden literal de columnas de candidatos en la tabla de Wikipedia
// "Oficialización de candidaturas". Si Wikipedia reordena la tabla habrá
// que actualizar este array (y el script imprimirá una advertencia si el
// número de cells no coincide).
const COL_CAND = [
  'Barreras',
  'Botero',
  'Caicedo',
  'Cepeda',
  'De la Espriella',
  'Fajardo',
  'Macollins',         // "Garvin" en wiki, Sondra Macollins Garvin
  'Lizcano',
  'Claudia López',
  'Clara López',
  'Matamoros',
  'Murillo',
  'Uribe Londoño',
  'Valencia',
];
const COL_AGG = ['Otros', 'Blanco', 'Ninguno', 'NS-NR', 'Margen'];

// Meses del año en español (los que aparecen en wikitext)
const MES = {
  ene: 1, enero: 1,
  feb: 2, febrero: 2,
  mar: 3, marzo: 3,
  abr: 4, abril: 4,
  may: 5, mayo: 5,
  jun: 6, junio: 6,
  jul: 7, julio: 7,
  ago: 8, agosto: 8,
  sep: 9, sept: 9, septiembre: 9,
  oct: 10, octubre: 10,
  nov: 11, noviembre: 11,
  dic: 12, diciembre: 12,
};

async function fetchWikitext() {
  const res = await fetch(API_URL, { headers: { 'User-Agent': 'ricardoruiz.co/scrape-encuestas-wiki' } });
  if (!res.ok) throw new Error(`Wikipedia API ${res.status}`);
  const j = await res.json();
  return j.parse.wikitext;
}

// Recorta el bloque "Oficialización de candidaturas" — la tabla canónica.
// Empieza después del propio heading y termina justo antes del siguiente
// heading de tercer nivel ("=== Antes de la oficialización…" u otro).
function pickSection(wt) {
  const head = '=== Oficialización de candidaturas ===';
  const i = wt.indexOf(head);
  if (i < 0) throw new Error('No encontró "Oficialización de candidaturas"');
  const start = i + head.length;
  // Buscamos el siguiente heading nivel 3 a partir de `start`. Wikipedia
  // mezcla "=== Heading ===" y "===Heading===" en este artículo, así
  // que aceptamos ambas formas.
  const re = /\n=== ?\S/g;
  re.lastIndex = start;
  const m = re.exec(wt);
  const end = m ? m.index : wt.length;
  return wt.slice(start, end);
}

// Limpia una celda: quita refs <ref>...</ref>, plantillas {{x|N/A}}, bgcolor,
// negritas '''…''', y comprime espacios.
function cleanCell(s) {
  if (s == null) return null;
  let t = s;
  t = t.replace(/<ref[^>]*\/>/g, '');               // refs auto-cerrados
  t = t.replace(/<ref[^>]*>[\s\S]*?<\/ref>/g, '');  // refs con cuerpo
  t = t.replace(/\{\{[Cc]elda\|[^}]*\}\}/g, 'N/A');
  t = t.replace(/\{\{[Aa]breviatura\|([^|}]+)\|[^}]*\}\}/g, '$1');
  t = t.replace(/\{\{refn[^}]*\}\}/g, '');
  t = t.replace(/bgcolor="?#[0-9a-fA-F]{3,6}"?/g, '');
  t = t.replace(/\bstyle="[^"]*"/g, '');
  t = t.replace(/'''/g, '');
  t = t.replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, '$1'); // [[A|B]] → B
  t = t.replace(/<small>|<\/small>/g, '');
  t = t.replace(/<br\s*\/?>/g, ' ');
  t = t.replace(/\s+/g, ' ').trim();
  return t || null;
}

// Convierte "23-30 Abr 2026" o "15 - 24 de abril" → "2026-04-30"
// Toma siempre el final del rango (fecha_fin).
function parseDate(raw) {
  if (!raw) return null;
  const s = raw.toLowerCase()
              .replace(/[–—]/g, '-')
              .replace(/\s+de\s+/g, ' ')
              .replace(/\s+/g, ' ')
              .trim();
  // Ejemplos esperados: "23-30 abr 2026", "20-22 abr 2026", "abr 2026",
  // "15 - 24 de abril" → ya transformado a "15 - 24 abril".
  const mRange = s.match(/(\d{1,2})\s*-\s*(\d{1,2})\s*([a-záéíóú]+)\s*(\d{4})?/i);
  if (mRange) {
    const dEnd = +mRange[2];
    const mon = MES[mRange[3].slice(0,4)] || MES[mRange[3].slice(0,3)] || null;
    const yr = +(mRange[4] || 2026);
    if (mon) return `${yr}-${String(mon).padStart(2,'0')}-${String(dEnd).padStart(2,'0')}`;
  }
  // Fecha única: "8 mar 2026"
  const mOne = s.match(/(\d{1,2})\s+([a-záéíóú]+)\s*(\d{4})?/i);
  if (mOne) {
    const d = +mOne[1];
    const mon = MES[mOne[2].slice(0,4)] || MES[mOne[2].slice(0,3)] || null;
    const yr = +(mOne[3] || 2026);
    if (mon) return `${yr}-${String(mon).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
  }
  // "Abr 2026" — fecha vaga, devolvemos día 15 como aproximación
  const mMonth = s.match(/^([a-záéíóú]+)\s+(\d{4})$/i);
  if (mMonth) {
    const mon = MES[mMonth[1].slice(0,4)] || MES[mMonth[1].slice(0,3)] || null;
    if (mon) return `${mMonth[2]}-${String(mon).padStart(2,'0')}-15`;
  }
  return null;
}

// "37.2%" → 37.2 ; "N/A" / null / vacío → null
function parsePct(raw) {
  if (!raw) return null;
  const t = raw.replace(',', '.').replace('%', '').trim();
  if (!t || /^N\/A$/i.test(t)) return null;
  const n = parseFloat(t);
  return Number.isFinite(n) ? n : null;
}

// "2 157" / "2.157" / "2157" → 2157
function parseN(raw) {
  if (!raw) return null;
  const t = raw.replace(/[\s.,]/g, '');
  const n = parseInt(t, 10);
  return Number.isFinite(n) ? n : null;
}

// Aliases de firma para que "CNC", "Centro Nacional de Consultoría",
// "AtlasIntel"/"Atlas Intel", "Guarumo - EcoAnalítica"/"Guarumo/EcoAnalítica"
// se normalicen al mismo bucket. Importa para evitar falsos positivos en
// el modo --diff cuando la misma encuesta aparece con ortografías
// distintas en Wikipedia y en el CSV local.
const FIRMA_ALIAS = {
  'centro nacional de consultoria': 'cnc',
  'cnc': 'cnc',
  'atlas intel': 'atlas-intel',
  'atlasintel': 'atlas-intel',
  'guarumo': 'guarumo',
  'guarumo ecoanalitica': 'guarumo',
  'invamer': 'invamer',
  'gad3': 'gad3',
  'yanhaas': 'yanhaas',
  'genesis crea': 'genesis-crea',
  'celag': 'celag',
};

function canonFirma(firma) {
  if (!firma) return 'desconocida';
  const k = firma.toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
  return FIRMA_ALIAS[k] || k.replace(/\s+/g, '-');
}

// Genera un slug de id desde firma + fecha (con día). Para el diff
// comparamos sólo firma+yyyy-mm con tolerancia ±5d, no este slug
// estricto.
function slugify(firma, fecha) {
  return `${canonFirma(firma)}-${fecha || 'sf'}`;
}

// Parsea una fila de la tabla. Recibe el bloque de texto entre dos `|-`.
// Devuelve null si no es una fila de datos válida.
function parseRow(block) {
  // Una fila válida arranca con `|<algo>` y NO con `!` (header), y NO
  // contiene "[[Archivo:" (header con foto), ni "colspan=" (separador).
  const firstLine = block.split('\n').find(l => l.trim().length > 0) || '';
  if (firstLine.startsWith('!')) return null;
  if (block.includes('[[Archivo:')) return null;
  if (block.includes('colspan="3"') && /declina|renuncia/i.test(block)) return null;

  // Las celdas se separan por `|` al inicio de línea. Cell-spans como
  // "rowspan=2|" marcan la primera celda del bloque y se mantienen.
  // Estrategia: extraer cada `|<contenido>` como una cell. El primer `|`
  // de cada línea es separador; lo de antes es vacío.
  const cells = [];
  for (const line of block.split('\n')) {
    if (!line.startsWith('|')) continue;
    // Una línea puede tener múltiples cells separadas por `||`
    // (poco común aquí, pero defensivo).
    const parts = line.replace(/^\|/, '').split(/\s*\|\|\s*/);
    for (const p of parts) cells.push(p);
  }
  if (cells.length < 4) return null;

  // Filtra atributos de celda (rowspan/colspan/bgcolor/style/etc) cuando
  // la celda llega como "attr1=val1 attr2=val2 |contenido". OJO: NO se
  // puede usar la heurística simple "head tiene =" porque celdas con
  // <ref name="...">{{Cita web|url=...|título=...}}</ref> también
  // contienen `=` y `|` y no son attrs de tabla. Pattern estricto: el
  // head tiene que ser sólo k="v" / k='v' / k=tok separados por espacios.
  const ATTR_RE = /^\s*(?:[\w-]+\s*=\s*(?:"[^"]*"|'[^']*'|[\w#.%/-]+)\s*)+\|/;
  const stripPrefix = c => {
    const m = c.match(ATTR_RE);
    if (!m) return c;
    return c.slice(m[0].length);
  };
  const cleaned = cells.map(stripPrefix).map(cleanCell);

  const firma = cleaned[0];
  if (!firma) return null;
  const fecha = parseDate(cleaned[1]);
  const n = parseN(cleaned[2]);

  // Sanidad: necesitamos al menos 14 celdas de candidatos después de las
  // 3 iniciales (firma, fecha, n).
  if (cleaned.length < 3 + COL_CAND.length) return null;

  const cands = {};
  for (let i = 0; i < COL_CAND.length; i++) {
    cands[COL_CAND[i]] = parsePct(cleaned[3 + i]);
  }
  // Categorías agregadas (Otros, Blanco, Ninguno, NS-NR, Margen)
  const agg = {};
  for (let i = 0; i < COL_AGG.length; i++) {
    agg[COL_AGG[i]] = parsePct(cleaned[3 + COL_CAND.length + i]);
  }

  return {
    id: slugify(firma, fecha),
    firma,
    fecha_fin: fecha,
    n,
    cands,
    agg,
    // Suma sanity check
    suma_pct: Object.values({ ...cands, ...agg }).filter(v => Number.isFinite(v))
                 .reduce((s,v) => s+v, 0),
  };
}

function parseTable(section) {
  // Cortamos por separadores `|-`. El primer chunk es el preámbulo + header.
  const chunks = section.split(/\n\|-/);
  const polls = [];
  for (const ch of chunks) {
    const p = parseRow(ch);
    if (p && p.firma && p.fecha_fin && p.n) polls.push(p);
  }
  return polls;
}

// Lee encuestas_porcentajes.csv y devuelve un Set de "buckets" únicos
// — firma_canon + fecha redondeada a 5d — para hacer match tolerante
// (Wikipedia suele reportar el ÚLTIMO día del trabajo de campo, el CSV
// puede tener la fecha de publicación, que difiere por 1-3 días).
function readKnownPolls(csvPath) {
  const fs = require('node:fs');
  const text = fs.readFileSync(csvPath, 'utf-8');
  const lines = text.split('\n').slice(1);
  const known = new Set();
  for (const line of lines) {
    if (!line.trim()) continue;
    const [, , , encuestadora, fecha_fin] = line.split(',');
    if (!encuestadora || !fecha_fin) continue;
    known.add(pollBucket(encuestadora, fecha_fin));
  }
  return known;
}

// "bucket" = firma_canon + año-mes-(día//5). Con ventana de 5 días, dos
// encuestas de la misma firma a menos de ~5 días caen al mismo bucket.
function pollBucket(firma, fecha) {
  if (!fecha) return `${canonFirma(firma)}-?`;
  const [y, m, d] = fecha.split('-').map(Number);
  const bin = Math.floor((d - 1) / 5);
  return `${canonFirma(firma)}-${y}-${String(m).padStart(2,'0')}-b${bin}`;
}

function toCsvRows(poll) {
  // Una fila por candidato encontrado (pct no nulo) + agregados.
  const rows = [];
  const baseEid = poll.id;
  const meta = [poll.firma, poll.fecha_fin, '', poll.n, 'presidencial_nacional'];
  // CSV columns: encuesta_id,consulta,candidato,encuestadora,fecha_fin,modo,n_muestra,categoria,pct,notas
  const push = (cand, pct) => {
    if (pct == null) return;
    rows.push([
      baseEid,
      'primera_vuelta',
      cand,
      poll.firma,
      poll.fecha_fin,
      '',                       // modo: Wikipedia no lo trae por columna
      poll.n,
      'presidencial_nacional',
      String(pct),
      'Wikipedia (scraped)',
    ].join(','));
  };
  for (const [k, v] of Object.entries(poll.cands)) push(k, v);
  for (const k of ['Otros', 'Blanco', 'Ninguno', 'NS-NR']) push(k, poll.agg[k]);
  return rows;
}

async function main() {
  const flags = new Set(process.argv.slice(2));
  const wantCsv = flags.has('--csv');
  const wantDiff = flags.has('--diff');

  const wt = await fetchWikitext();
  const sec = pickSection(wt);
  const polls = parseTable(sec);

  let toReport = polls;
  if (wantDiff) {
    const csvPath = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/encuestas_porcentajes.csv';
    const known = readKnownPolls(csvPath);
    toReport = polls.filter(p => !known.has(pollBucket(p.firma, p.fecha_fin)));
    if (!wantCsv) {
      process.stderr.write(
        `[scrape] Wikipedia → ${polls.length} encuestas | local → ${known.size} conocidas | nuevas → ${toReport.length}\n`
      );
    }
  }

  if (wantCsv) {
    if (!wantDiff) console.log('encuesta_id,consulta,candidato,encuestadora,fecha_fin,modo,n_muestra,categoria,pct,notas');
    for (const p of toReport) for (const r of toCsvRows(p)) console.log(r);
  } else {
    console.log(JSON.stringify(toReport, null, 2));
  }
}

main().catch(err => { console.error(err); process.exit(1); });
