#!/usr/bin/env node
// tools/build-historicos.js
//
// Procesa un archivo GCS (Gran Consolidado Seccional) de la Registraduría
// y produce 3 JSONs agregados listos para subir a S3:
//
//   {outDir}/resumen.json     (nacional por candidato)
//   {outDir}/por-depto.json   (depto → candidatos)
//   {outDir}/por-mun.json     (depto-mun → candidatos)
//
// Uso:
//   node tools/build-historicos.js <archivo.csv> <out-dir> [--meta anio=2022,vuelta=1]
//
// Ejemplo:
//   node tools/build-historicos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES1V.csv" \
//     ./out/pres-2022-v1 \
//     --meta anio=2022,vuelta=1,nombre=Presidencial2022V1
//
// Notas:
//  - Parser streaming: maneja archivos de 100 MB sin cargar todo en RAM.
//  - Normaliza nombres (mayúsculas, sin acentos) para facilitar match.
//  - COD_CAN especiales 996 (blanco), 997 (nulos), 998/999 (no marcados)
//    se contabilizan aparte en `especiales` y NO entran en votos_validos.
//  - El porcentaje de cada candidato se calcula sobre votos_validos.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// COD_CAN con significado especial en los CSV de la Registraduría.
const SPECIAL_CODES = {
  '996': 'blanco',
  '997': 'nulos',
  '998': 'no_marcados',
  '999': 'no_marcados',
};

// Mayúsculas sin acentos, trim.
function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

// Lee la primera línea (header) y construye map colName → índice.
function parseHeaderLine(line){
  const clean = line.replace(/^\uFEFF/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  // Verifica columnas mínimas
  const required = ['COD_DDE', 'COD_MME', 'COD_CAN', 'DES_CAN', 'NUM_VOT'];
  const missing = required.filter(r => !(r in map));
  if (missing.length){
    throw new Error(`Header CSV sin columnas requeridas: ${missing.join(', ')}. Header leído: ${cols.join(';')}`);
  }
  return map;
}

// Parsea CLI args: [csvPath, outDir, (--meta k=v,k=v)]
function parseArgs(argv){
  const [, , csvPath, outDir, ...rest] = argv;
  const meta = {};
  for (let i = 0; i < rest.length; i++){
    if (rest[i] === '--meta' && rest[i+1]){
      for (const pair of rest[i+1].split(',')){
        const [k, v] = pair.split('=');
        if (k && v != null) meta[k.trim()] = v.trim();
      }
    }
  }
  return { csvPath, outDir, meta };
}

async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;    // col → index map
  let rowsRead = 0;
  let rowsAgg = 0;

  // Agregadores: tres niveles (nacional, depto, mun)
  //   cands: Map<cod, { nombre, partido, votos }>
  //   especiales: Map<categoría, votos>
  const nacional = { cands: new Map(), especiales: new Map() };
  const deptos   = new Map();  // depCod (2-dig) → { cands, especiales }
  const muns     = new Map();  // "depCod-munCod" (2-3 dig) → { cands, especiales }

  function ensureScope(map, key){
    let s = map.get(key);
    if (!s){ s = { cands: new Map(), especiales: new Map() }; map.set(key, s); }
    return s;
  }

  function accum(scope, candCod, candNombre, candPartido, votos){
    const special = SPECIAL_CODES[candCod];
    if (special){
      scope.especiales.set(special, (scope.especiales.get(special) || 0) + votos);
    } else {
      let c = scope.cands.get(candCod);
      if (!c){
        c = { nombre: candNombre, partido: candPartido, votos: 0 };
        scope.cands.set(candCod, c);
      }
      c.votos += votos;
      // El nombre/partido se queda con la primera fila (luego se puede
      // sobrescribir si viene más completo). Para simplicidad, mantenemos
      // el primero no vacío.
      if (!c.nombre && candNombre) c.nombre = candNombre;
      if (!c.partido && candPartido) c.partido = candPartido;
    }
  }

  for await (const rawLine of rl){
    if (idx === null){
      idx = parseHeaderLine(rawLine);
      continue;
    }
    const line = rawLine.trim();
    if (!line) continue;
    rowsRead++;

    const parts = line.split(';');
    const dep   = parts[idx['COD_DDE']];
    const mun   = parts[idx['COD_MME']];
    const cod   = parts[idx['COD_CAN']];
    const des   = parts[idx['DES_CAN']] || '';
    const par   = idx['DES_PAR'] != null ? (parts[idx['DES_PAR']] || '') : '';
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);

    if (!dep || !cod || !Number.isFinite(votos) || votos <= 0) continue;

    const depK = String(parseInt(dep, 10)).padStart(2, '0');
    const munK = `${depK}-${String(parseInt(mun, 10) || 0).padStart(3, '0')}`;
    const candNombre  = normName(des);
    const candPartido = normName(par);

    accum(nacional,               cod, candNombre, candPartido, votos);
    accum(ensureScope(deptos, depK), cod, candNombre, candPartido, votos);
    accum(ensureScope(muns, munK),   cod, candNombre, candPartido, votos);
    rowsAgg++;
  }

  return { nacional, deptos, muns, rowsRead, rowsAgg };
}

// Convierte un scope a JSON: { votos_validos, votos_totales, especiales, candidatos }
function serializeScope(scope){
  const cands = {};
  const especiales = {};
  let validos = 0;
  for (const [cod, c] of scope.cands){
    cands[cod] = { nombre: c.nombre, partido: c.partido, votos: c.votos };
    validos += c.votos;
  }
  for (const [k, v] of scope.especiales){
    especiales[k] = v;
  }
  for (const cod of Object.keys(cands)){
    cands[cod].pct = validos > 0 ? +(cands[cod].votos / validos * 100).toFixed(3) : 0;
  }
  const total = validos + Object.values(especiales).reduce((s, v) => s + v, 0);
  return {
    votos_validos: validos,
    votos_totales: total,
    especiales,
    candidatos: cands,
  };
}

function fmtKB(bytes){ return Math.round(bytes/1024) + ' KB'; }
function fmtMB(bytes){ return (bytes/1024/1024).toFixed(2) + ' MB'; }

async function main(){
  const { csvPath, outDir, meta } = parseArgs(process.argv);
  if (!csvPath || !outDir){
    console.error('Uso: node tools/build-historicos.js <archivo.csv> <out-dir> [--meta k=v,k=v]');
    process.exit(1);
  }
  if (!fs.existsSync(csvPath)){
    console.error(`No existe el archivo: ${csvPath}`);
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  console.log(`\n[build-historicos] procesando ${path.basename(csvPath)}`);
  const t0 = Date.now();
  const { nacional, deptos, muns, rowsRead, rowsAgg } = await processCsv(csvPath);
  const dt = ((Date.now() - t0) / 1000).toFixed(1);

  console.log(`  ${rowsRead.toLocaleString('es-CO')} filas leídas (${rowsAgg.toLocaleString('es-CO')} agregadas) en ${dt}s`);
  console.log(`  ${deptos.size} deptos · ${muns.size} muns · ${nacional.cands.size} candidatos nacionales`);

  const resumenSerial = serializeScope(nacional);
  const resumen = {
    ...meta,
    archivo_origen: path.basename(csvPath),
    rows_leidas: rowsRead,
    rows_agregadas: rowsAgg,
    generado_en: new Date().toISOString(),
    nacional: resumenSerial,
  };

  const porDepto = {};
  for (const [cod, scope] of deptos){
    porDepto[cod] = serializeScope(scope);
  }

  const porMun = {};
  for (const [cod, scope] of muns){
    const [d, m] = cod.split('-');
    porMun[cod] = { depCod: d, munCod: m, ...serializeScope(scope) };
  }

  const rp = path.join(outDir, 'resumen.json');
  const dp = path.join(outDir, 'por-depto.json');
  const mp = path.join(outDir, 'por-mun.json');
  fs.writeFileSync(rp, JSON.stringify(resumen, null, 2));
  fs.writeFileSync(dp, JSON.stringify(porDepto));
  fs.writeFileSync(mp, JSON.stringify(porMun));

  console.log(`  ✓ resumen.json     ${fmtKB(fs.statSync(rp).size)}`);
  console.log(`  ✓ por-depto.json   ${fmtKB(fs.statSync(dp).size)}`);
  console.log(`  ✓ por-mun.json     ${fmtMB(fs.statSync(mp).size)}`);

  // Sanity: top 5 candidatos nacionales
  console.log(`  top 5 nacional:`);
  const top = Object.entries(resumenSerial.candidatos)
    .sort((a,b) => b[1].votos - a[1].votos).slice(0, 5);
  for (const [cod, c] of top){
    console.log(`    ${c.nombre.padEnd(40)} ${String(c.votos).padStart(12)} (${c.pct}%)`);
  }
  const total = resumenSerial.votos_validos + Object.values(resumenSerial.especiales).reduce((s,v)=>s+v,0);
  console.log(`  total mesas: válidos ${resumenSerial.votos_validos.toLocaleString('es-CO')} + especiales ${Object.values(resumenSerial.especiales).reduce((s,v)=>s+v,0).toLocaleString('es-CO')} = ${total.toLocaleString('es-CO')}\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
