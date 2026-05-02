#!/usr/bin/env node
// tools/build-medellin-comuna-pres.js
//
// Procesa un archivo GCS Presidencial 1V (2010/2014/2018/2022) o
// la Consulta Pacto Histórico 2025 y genera agregados por comuna
// política de Medellín (16 + CORR + OTROS). Filtro: COD_DDE=1, COD_MME=1.
//
// Uso:
//   node tools/build-medellin-comuna-pres.js <archivo.csv> <out-dir>
//
// Ejemplo:
//   node tools/build-medellin-comuna-pres.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS/GCS_2018PRES1V.csv" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_medellin/historicos-comuna/pres-2018"
//
// Salida:
//   {outDir}/resumen.json     ciudad — candidatos[] con votos+pct
//   {outDir}/por-comuna.json  comuna → candidatos+especiales+totales
//
// Notas:
// - Nivel de candidato (DES_CAN), no de partido. Para presidenciales 1V cada
//   COD_CAN es un candidato; para la consulta 2025 también.
// - Especiales: COD_CAN ∈ {996,997,998,999} → blanco/nulos/no_marcados.
// - Misma tabla ZZ → comuna que tools/build-medellin-historicos.js.
// - parseHeaderLine reconoce columnas por nombre, no por posición, así que
//   funciona aunque el orden cambie entre 2010 y 2014/2018/2022/2025.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const FILTRO_DEPTO = 1;
const FILTRO_MUN = 1;

const SPECIAL_CODES = {
  '996': 'blanco',
  '997': 'nulos',
  '998': 'no_marcados',
  '999': 'no_marcados',
};

const ZZ_TO_COMUNA = {
  '01':'01','02':'01',
  '03':'02','04':'02',
  '05':'03','06':'03',
  '07':'04','08':'04',
  '09':'05','10':'05',
  '11':'06','12':'06',
  '13':'07','14':'07',
  '15':'08','16':'08',
  '17':'09','18':'09',
  '19':'10','20':'10',
  '21':'11','22':'11',
  '23':'12','24':'12',
  '25':'13','26':'13',
  '27':'14','28':'14',
  '29':'15',
  '30':'16','31':'16','32':'16',
  '99':'CORR',
  '90':'OTROS','98':'OTROS',
  '00':'OTROS','0':'OTROS',
};

const COMUNA_NOMBRE = {
  '01':'Popular','02':'Santa Cruz','03':'Manrique','04':'Aranjuez',
  '05':'Castilla','06':'Doce de Octubre','07':'Robledo','08':'Villa Hermosa',
  '09':'Buenos Aires','10':'La Candelaria','11':'Laureles Estadio',
  '12':'La América','13':'San Javier','14':'El Poblado','15':'Guayabal','16':'Belén',
  'CORR':'Corregimientos','OTROS':'Otros / Exterior',
};

const COMUNA_ORDER = ['01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','CORR','OTROS'];

function mapZZ(zz){
  const k = String(zz || '').padStart(2, '0');
  return ZZ_TO_COMUNA[k] || 'OTROS';
}

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function parseHeaderLine(line){
  const clean = line.replace(/^\uFEFF/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['COD_DDE','COD_MME','COD_ZZ','COD_PP','COD_CAN','DES_CAN','DES_PAR','NUM_VOT'];
  const missing = required.filter(r => !(r in map));
  if (missing.length){
    throw new Error(`Header sin columnas requeridas: ${missing.join(', ')}`);
  }
  return map;
}

function emptyScope(){
  return { cands: new Map(), especiales: new Map() };
}

function ensure(map, key){
  let s = map.get(key);
  if (!s){ s = emptyScope(); map.set(key, s); }
  return s;
}

function accum(scope, candCod, candNombre, candPartido, votos){
  const sp = SPECIAL_CODES[candCod];
  if (sp){
    scope.especiales.set(sp, (scope.especiales.get(sp) || 0) + votos);
    return;
  }
  let c = scope.cands.get(candCod);
  if (!c){
    c = { cod: candCod, nombre: candNombre, partido: candPartido, votos: 0 };
    scope.cands.set(candCod, c);
  }
  c.votos += votos;
  if (!c.nombre && candNombre) c.nombre = candNombre;
  if (!c.partido && candPartido) c.partido = candPartido;
}

function serializeScope(scope){
  const cands = [];
  let validos = 0;
  for (const c of scope.cands.values()){
    cands.push({ cod: c.cod, nombre: c.nombre, partido: c.partido, votos: c.votos });
    validos += c.votos;
  }
  cands.sort((a,b) => b.votos - a.votos);
  for (const c of cands){
    c.pct = validos > 0 ? +(c.votos / validos * 100).toFixed(3) : 0;
  }
  const especiales = {};
  for (const [k,v] of scope.especiales) especiales[k] = v;
  const totalEsp = Object.values(especiales).reduce((s,v) => s+v, 0);
  return {
    votos_validos: validos,
    votos_totales: validos + totalEsp,
    especiales,
    candidatos: cands,
  };
}

async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;
  let rowsRead = 0, rowsKept = 0;

  const ciudad = emptyScope();
  const porComuna = new Map();

  for await (const line of rl){
    if (!line) continue;
    if (idx === null){
      idx = parseHeaderLine(line);
      continue;
    }
    rowsRead++;
    const cols = line.split(';');
    const dde = parseInt(cols[idx.COD_DDE] || '0', 10);
    const mme = parseInt(cols[idx.COD_MME] || '0', 10);
    if (dde !== FILTRO_DEPTO || mme !== FILTRO_MUN) continue;

    const zz = (cols[idx.COD_ZZ] || '').trim();
    const comuna = mapZZ(zz);
    const candCod = String(cols[idx.COD_CAN] || '').trim();
    const candNombre = normName(cols[idx.DES_CAN] || '');
    const candPartido = normName(cols[idx.DES_PAR] || '');
    const votos = parseInt(cols[idx.NUM_VOT] || '0', 10) || 0;
    if (votos === 0) continue;
    rowsKept++;

    accum(ciudad, candCod, candNombre, candPartido, votos);
    accum(ensure(porComuna, comuna), candCod, candNombre, candPartido, votos);
  }

  return { ciudad, porComuna, rowsRead, rowsKept };
}

function writeJSON(filePath, obj){
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
}

function buildPorComuna(map){
  const out = {};
  for (const k of COMUNA_ORDER){
    if (!map.has(k)) continue;
    out[k] = {
      cod: k,
      nombre: COMUNA_NOMBRE[k] || k,
      ...serializeScope(map.get(k)),
    };
  }
  return out;
}

async function main(){
  const args = process.argv.slice(2);
  if (args.length < 2){
    console.error('Uso: node tools/build-medellin-comuna-pres.js <archivo.csv> <out-dir>');
    process.exit(1);
  }
  const [csvPath, outDir] = args;
  if (!fs.existsSync(csvPath)){
    console.error(`No existe el archivo: ${csvPath}`);
    process.exit(1);
  }

  const t0 = Date.now();
  console.log(`Leyendo ${csvPath} ...`);
  const { ciudad, porComuna, rowsRead, rowsKept } = await processCsv(csvPath);
  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`Procesadas ${rowsRead.toLocaleString()} filas, conservadas ${rowsKept.toLocaleString()} (Medellín) en ${elapsed}s.`);

  writeJSON(path.join(outDir, 'resumen.json'), {
    meta: {
      fuente: path.basename(csvPath),
      filtro: { dde: FILTRO_DEPTO, mme: FILTRO_MUN },
      generado: new Date().toISOString(),
    },
    ...serializeScope(ciudad),
  });
  writeJSON(path.join(outDir, 'por-comuna.json'), {
    meta: {
      fuente: path.basename(csvPath),
      generado: new Date().toISOString(),
    },
    por_comuna: buildPorComuna(porComuna),
  });

  console.log(`\nArchivos generados en ${outDir}:`);
  for (const f of ['resumen.json', 'por-comuna.json']){
    const p = path.join(outDir, f);
    const sz = (fs.statSync(p).size / 1024).toFixed(1);
    console.log(`  ${p}  (${sz} KB)`);
  }

  const top = serializeScope(ciudad).candidatos.slice(0, 6);
  console.log(`\nTop 6 candidatos Medellín ciudad:`);
  for (const c of top){
    console.log(`  ${c.pct.toFixed(2).padStart(6)}%  ${c.votos.toLocaleString().padStart(8)}  ${c.nombre}`);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
