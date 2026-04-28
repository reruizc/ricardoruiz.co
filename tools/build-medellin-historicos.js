#!/usr/bin/env node
// tools/build-medellin-historicos.js
//
// Procesa un archivo GCS Territorial (2015/2019/2023) y genera JSONs
// agregados SOLO de Medellín (depto=1, mun=1 código Registraduría) para
// alcaldía y concejo. Dejados en disco — el usuario los sube a S3.
//
// Uso:
//   node tools/build-medellin-historicos.js <archivo.csv> <out-dir>
//
// Ejemplo:
//   node tools/build-medellin-historicos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_medellin/2023"
//
// Salida (4 archivos por corporación):
//   {outDir}/alcaldia/resumen.json       ciudad — top candidatos, especiales, total
//   {outDir}/alcaldia/por-comuna.json    zz → candidatos+especiales+total
//   {outDir}/alcaldia/por-puesto.json    zz-pp → candidatos+especiales+total
//   {outDir}/alcaldia/por-mesa.json      zz-pp-ms → candidatos+especiales+total
//   (idem para concejo/)
//
// Notas:
// - Streaming, sin dependencias externas. Recorre el CSV una sola vez.
// - Para Medellín 2023 alcaldía hay ~59k filas → segundos de procesamiento.
// - Nombres normalizados (UPPER + sin tildes).
// - COD_CAN especiales 996/997/998/999 → blanco/nulos/no_marcados.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SPECIAL_CODES = {
  '996': 'blanco',
  '997': 'nulos',
  '998': 'no_marcados',
  '999': 'no_marcados',
};

// COD_DDE / COD_MME del archivo (Registraduría) que corresponden a Medellín
const FILTRO_DEPTO = 1;
const FILTRO_MUN   = 1;

// COD_COR cambia entre años (2019: 6/7; 2023: 3/4). DES_COR también
// varía: 2015 usa "ALCALDIA"/"GOBERNACION", 2019/2023 usan "ALCALDE"/
// "GOBERNADOR". Aceptamos ambas formas.
const COR_DES_TO_NAME = {
  'ALCALDE': 'alcaldia',
  'ALCALDIA': 'alcaldia',
  'CONCEJO': 'concejo',
};

// Curules de concejo en Medellín (D'Hondt)
const CURULES_CONCEJO = 21;

// Mapeo Zona Electoral (COD_ZZ) → comuna política. Derivado de
// PUESTOS_GEOREF.csv (col ZONA → CÓDIGO COMUNA). En el GeoJSON
// (mapas-2026/Ciudades-COM-LOC/MEDELLINX.json) los corregimientos
// usan CODIGO 50/60/70/80/90 — los traduzco aquí. La zona 99 agrupa
// los 5 corregimientos; para desagregar dentro de 99 hay que usar
// COD_PP (pendiente para v1).
const ZZ_TO_COMUNA = {
  '01':'01','02':'01',                  // C1 Popular
  '03':'02','04':'02',                  // C2 Santa Cruz
  '05':'03','06':'03',                  // C3 Manrique
  '07':'04','08':'04',                  // C4 Aranjuez
  '09':'05','10':'05',                  // C5 Castilla
  '11':'06','12':'06',                  // C6 Doce de Octubre
  '13':'07','14':'07',                  // C7 Robledo
  '15':'08','16':'08',                  // C8 Villa Hermosa
  '17':'09','18':'09',                  // C9 Buenos Aires
  '19':'10','20':'10',                  // C10 La Candelaria
  '21':'11','22':'11',                  // C11 Laureles Estadio
  '23':'12','24':'12',                  // C12 La América
  '25':'13','26':'13',                  // C13 San Javier
  '27':'14','28':'14',                  // C14 El Poblado
  '29':'15',                            // C15 Guayabal
  '30':'16','31':'16','32':'16',        // C16 Belén
  '99':'CORR',                          // Corregimientos (agregados)
  '90':'OTROS','98':'OTROS',            // Otros / consular / desconocido
};

const COMUNA_NOMBRE = {
  '01':'Popular','02':'Santa Cruz','03':'Manrique','04':'Aranjuez',
  '05':'Castilla','06':'Doce de Octubre','07':'Robledo','08':'Villa Hermosa',
  '09':'Buenos Aires','10':'La Candelaria','11':'Laureles Estadio',
  '12':'La América','13':'San Javier','14':'El Poblado','15':'Guayabal','16':'Belén',
  'CORR':'Corregimientos','OTROS':'Otros / Exterior',
};

function mapZZ(zz){ return ZZ_TO_COMUNA[zz] || 'OTROS'; }

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function parseHeaderLine(line){
  const clean = line.replace(/^\uFEFF/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['DES_COR','COD_DDE','COD_MME','COD_ZZ','COD_PP','DES_MS','COD_CAN','DES_CAN','DES_PAR','NUM_VOT'];
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

function dhondt(parties, seats){
  // parties: [{ partido, votos }] — devuelve mismo array con .curules
  const arr = parties.map(p => ({ ...p, curules: 0 }));
  for (let i = 0; i < seats; i++){
    let bestIdx = -1, bestQ = -1;
    for (let j = 0; j < arr.length; j++){
      const q = arr[j].votos / (arr[j].curules + 1);
      if (q > bestQ){ bestQ = q; bestIdx = j; }
    }
    if (bestIdx >= 0) arr[bestIdx].curules++;
  }
  return arr;
}

function serializeScope(scope, opts = {}){
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

  // D'Hondt por partido para concejo
  let curulesPorPartido = null;
  if (opts.curules && opts.curules > 0){
    const aggPartido = new Map();
    for (const c of cands){
      const p = c.partido || '(SIN PARTIDO)';
      aggPartido.set(p, (aggPartido.get(p) || 0) + c.votos);
    }
    const partidos = Array.from(aggPartido, ([partido, votos]) => ({ partido, votos }));
    curulesPorPartido = dhondt(partidos, opts.curules)
      .filter(p => p.curules > 0)
      .sort((a,b) => b.curules - a.curules || b.votos - a.votos);
  }

  return {
    votos_validos: validos,
    votos_totales: validos + totalEsp,
    especiales,
    candidatos: cands,
    ...(curulesPorPartido ? { curules_por_partido: curulesPorPartido } : {}),
  };
}

async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;
  let rowsRead = 0, rowsKept = 0;

  // 5 niveles × 2 corporaciones:
  //   ciudad        - todo Medellín
  //   comunaPol     - 16 comunas + CORR + OTROS (mapeo ZZ→comuna política)
  //   zona          - zonas electorales (1-32, 90, 98, 99)
  //   puesto        - zona-puesto
  //   mesa          - zona-puesto-mesa
  const data = {
    alcaldia: { ciudad: emptyScope(), comunaPol: new Map(), zona: new Map(), puesto: new Map(), mesa: new Map() },
    concejo:  { ciudad: emptyScope(), comunaPol: new Map(), zona: new Map(), puesto: new Map(), mesa: new Map() },
  };

  for await (const rawLine of rl){
    if (idx === null){
      idx = parseHeaderLine(rawLine);
      continue;
    }
    const line = rawLine.trim();
    if (!line) continue;
    rowsRead++;

    const parts = line.split(';');
    const dep = parseInt(parts[idx['COD_DDE']] || '0', 10);
    const mun = parseInt(parts[idx['COD_MME']] || '0', 10);
    if (dep !== FILTRO_DEPTO || mun !== FILTRO_MUN) continue;

    const corDes = String(parts[idx['DES_COR']] || '').trim().toUpperCase();
    const corName = COR_DES_TO_NAME[corDes];
    if (!corName) continue;

    const zz = String(parseInt(parts[idx['COD_ZZ']] || '0', 10)).padStart(2, '0');
    const pp = String(parseInt(parts[idx['COD_PP']] || '0', 10)).padStart(2, '0');
    const ms = String(parts[idx['DES_MS']] || '0').trim();
    const cod   = parts[idx['COD_CAN']];
    const des   = parts[idx['DES_CAN']] || '';
    const par   = parts[idx['DES_PAR']] || '';
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);

    if (!cod || !Number.isFinite(votos) || votos <= 0) continue;

    const candNombre  = normName(des);
    const candPartido = normName(par);

    const tgt = data[corName];
    const cp  = mapZZ(zz);
    accum(tgt.ciudad, cod, candNombre, candPartido, votos);
    accum(ensure(tgt.comunaPol, cp), cod, candNombre, candPartido, votos);
    accum(ensure(tgt.zona, zz), cod, candNombre, candPartido, votos);
    accum(ensure(tgt.puesto, `${zz}-${pp}`), cod, candNombre, candPartido, votos);
    accum(ensure(tgt.mesa,   `${zz}-${pp}-${ms}`), cod, candNombre, candPartido, votos);
    rowsKept++;
  }

  return { data, rowsRead, rowsKept };
}

function fmtKB(b){ return Math.round(b/1024) + ' KB'; }
function fmtMB(b){ return (b/1024/1024).toFixed(2) + ' MB'; }

function writeJson(filePath, obj){
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(obj));
}

function writeJsonPretty(filePath, obj){
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
}

async function main(){
  const [, , csvPath, outDir] = process.argv;
  if (!csvPath || !outDir){
    console.error('Uso: node tools/build-medellin-historicos.js <archivo.csv> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(csvPath)){
    console.error(`No existe: ${csvPath}`);
    process.exit(1);
  }

  console.log(`\n[medellin-historicos] procesando ${path.basename(csvPath)}`);
  const t0 = Date.now();
  const { data, rowsRead, rowsKept } = await processCsv(csvPath);
  const dt = ((Date.now() - t0) / 1000).toFixed(1);

  console.log(`  ${rowsRead.toLocaleString('es-CO')} filas leídas · ${rowsKept.toLocaleString('es-CO')} de Medellín en ${dt}s`);

  for (const corp of ['alcaldia','concejo']){
    const d = data[corp];
    const opts = corp === 'concejo' ? { curules: CURULES_CONCEJO } : {};

    const resumen = {
      corporacion: corp,
      archivo_origen: path.basename(csvPath),
      generado_en: new Date().toISOString(),
      filtro: { depto: FILTRO_DEPTO, mun: FILTRO_MUN, ciudad: 'MEDELLIN' },
      ...serializeScope(d.ciudad, opts),
    };

    const porComuna = {};
    for (const [k, scope] of d.comunaPol){
      porComuna[k] = { nombre: COMUNA_NOMBRE[k] || k, ...serializeScope(scope, opts) };
    }

    const porZona = {};
    for (const [k, scope] of d.zona) porZona[k] = serializeScope(scope);

    const porPuesto = {};
    for (const [k, scope] of d.puesto) porPuesto[k] = serializeScope(scope);

    const porMesa = {};
    for (const [k, scope] of d.mesa) porMesa[k] = serializeScope(scope);

    const rp = path.join(outDir, corp, 'resumen.json');
    const cp = path.join(outDir, corp, 'por-comuna.json');
    const zp = path.join(outDir, corp, 'por-zona.json');
    const pp = path.join(outDir, corp, 'por-puesto.json');
    const mp = path.join(outDir, corp, 'por-mesa.json');

    writeJsonPretty(rp, resumen);
    writeJson(cp, porComuna);
    writeJson(zp, porZona);
    writeJson(pp, porPuesto);
    writeJson(mp, porMesa);

    console.log(`  ${corp.padEnd(9)} · resumen ${fmtKB(fs.statSync(rp).size)} · comuna ${fmtKB(fs.statSync(cp).size)} · zona ${fmtKB(fs.statSync(zp).size)} · puesto ${fmtKB(fs.statSync(pp).size)} · mesa ${fmtMB(fs.statSync(mp).size)}`);

    // Sanity
    const top = resumen.candidatos.slice(0, 3);
    console.log(`    top: ${top.map(c => `${c.nombre.slice(0,28)} (${c.votos.toLocaleString('es-CO')} · ${c.pct}%)`).join(' | ')}`);
    console.log(`    total ${resumen.votos_validos.toLocaleString('es-CO')} válidos + ${(resumen.votos_totales - resumen.votos_validos).toLocaleString('es-CO')} especiales · ${Object.keys(porComuna).length} comunas · ${Object.keys(porZona).length} zonas · ${Object.keys(porPuesto).length} puestos · ${Object.keys(porMesa).length} mesas`);
  }
  console.log();
}

main().catch(e => { console.error(e); process.exit(1); });
