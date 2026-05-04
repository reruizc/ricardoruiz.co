#!/usr/bin/env node
// tools/build-puestos-nacional-light.js
//
// Cruza:
//   - PUESTOS_GEOREF.csv (lat/lng, censo, mesas, nombre puesto)
//   - senado/departamentos/{dep}/puestos.json (partido ganador 2026)
//   - pres-2022-v1/por-puesto.json (ganador presidencial 2022)
//
// y emite un único archivo ligero para vista nacional con LOD:
//
//   {outDir}/puestos-nacional-light.json
//
// Esquema (array compacto):
//   [
//     {
//       "k": "01-001-01-01",         // depCod-munCod-zonaCod-puestoCod
//       "y": 6.291167, "x": -75.541105,
//       "c": 12859,                  // censo electoral (mujeres+hombres)
//       "m": 39,                     // # mesas
//       "n": "I.E. PROCESA DELGADO", // nombre del puesto
//       "mn": "MEDELLIN",            // nombre del municipio
//       "t": 1,                      // tier por censo (1=top300, 2=top1500, 3=resto)
//       "p22": "petro",              // ganador pres 2022 1V (id corto, ver MAP_PRES22)
//       "s26": "PH"                  // partido ganador senado 2026 (id corto)
//     }, ...
//   ]
//
// El frontend filtra por tier según el zoom de Leaflet.
//
// Uso:
//   node tools/build-puestos-nacional-light.js \
//     <georef.csv> <senado-deps-dir> <pres-2022-puestos.json> <out-dir>

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Mapeos cortos para reducir el tamaño del JSON
// (un id de 2-3 chars vs un nombre largo)
const MAP_PRES22 = {
  // Por COD_CAN del archivo 2022 — mapeamos al id corto que el front entiende
  // (los nombres reales vivieron en candidatos del JSON puesto, hacemos el match
  // por NOMBRE en runtime para no acoplar codes que pueden cambiar entre años)
};
const PRES22_KEYS = {
  'GUSTAVO PETRO':         'petro',
  'RODOLFO HERNANDEZ':     'rodolfo',
  'FEDERICO GUTIERREZ':    'fico',
  'SERGIO FAJARDO':        'fajardo',
  'JOHNMILTON RODRIGUEZ':  'rodriguez',
  'INGRID BETANCOURT PULECIO': 'ingrid',
  'ENRIQUE GOMEZ MARTINEZ': 'gomez',
  'JOHN MILTON RODRIGUEZ': 'rodriguez',
  'LUIS PEREZ': 'perez',
};

// Partidos senado 2026 → id corto (los principales; otros se quedan con prefijo)
const PARTIDO_SHORT = {
  'PACTO HISTÓRICO SENADO': 'PH',
  'PARTIDO CENTRO DEMOCRÁTICO': 'CD',
  'PARTIDO LIBERAL COLOMBIANO': 'LIB',
  'PARTIDO CONSERVADOR COLOMBIANO': 'CON',
  'PARTIDO DE LA UNIÓN POR LA GENTE - PARTIDO DE LA U': 'U',
  'PARTIDO POLÍTICO OXÍGENO': 'OXI',
  'COALICIÓN CAMBIO RADICAL - ALMA': 'CR',
  'CREEMOS': 'CRE',
  'AHORA COLOMBIA': 'AHO',
  'ALIANZA VERDE': 'AV',
  'PARTIDO ALIANZA VERDE': 'AV',
  'COLOMBIA SEGURA Y PRÓSPERA': 'CSP',
  'LA LISTA DE OVIEDO - CON TODA POR COLOMBIA': 'OVI',
  'COALICIÓN FUERZA CIUDADANA': 'FC',
  'MOVIMIENTO SALVACIÓN NACIONAL': 'MSN',
  'FRENTE AMPLIO UNITARIO': 'FAU',
  'PATRIOTAS': 'PAT',
};

function pad(s, n){ return String(parseInt(s, 10) || 0).padStart(n, '0'); }
function fmtKB(b){ return Math.round(b/1024) + ' KB'; }
function fmtMB(b){ return (b/1024/1024).toFixed(2) + ' MB'; }
function normName(s){ return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }

async function readGeoref(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  const out = new Map();
  let header = null;
  for await (const rawLine of rl){
    if (!header){
      header = rawLine.replace(/^﻿/, '').split(';').map(s => s.trim());
      continue;
    }
    const parts = rawLine.split(';');
    const codComp = parts[1];   // "010010101"
    if (!codComp || codComp.length !== 9) continue;
    const dep = codComp.slice(0,2);
    const mun = codComp.slice(2,5);
    const zon = codComp.slice(5,7);
    const pue = codComp.slice(7,9);
    const lat = parseFloat(parts[9]);
    const lng = parseFloat(parts[10]);
    const muj = parseInt(parts[13] || '0', 10) || 0;
    const hom = parseInt(parts[14] || '0', 10) || 0;
    const mesas = parseInt(parts[15] || '0', 10) || 0;
    const nombre = parts[18] || '';
    const munNom = parts[3] || '';
    const k = `${dep}-${mun}-${zon}-${pue}`;
    out.set(k, {
      k, y: lat, x: lng, c: muj + hom, m: mesas,
      n: normName(nombre), mn: normName(munNom),
    });
  }
  return out;
}

function loadSenadoWinners(depsDir){
  // Cada archivo: senado/departamentos/{dep}/puestos.json (array)
  const winners = new Map();  // key → partido_short
  if (!fs.existsSync(depsDir)) return winners;
  const subs = fs.readdirSync(depsDir).filter(s => /^\d+$/.test(s));
  for (const dep of subs){
    const fp = path.join(depsDir, dep, 'puestos.json');
    if (!fs.existsSync(fp)) continue;
    const arr = JSON.parse(fs.readFileSync(fp, 'utf8'));
    for (const p of arr){
      const dCod = pad(p.dep_cod || dep, 2);
      const mCod = pad(p.mun_cod || '0', 3);
      // El cod interno es "com-zon-pue" (com_cod + zon_cod + pue_cod_raw)
      const zCod = pad(p.zon_cod || '0', 2);
      const pCod = pad(p.pue_cod_raw || (p.pue_cod || '').split('-').pop() || '0', 2);
      const k = `${dCod}-${mCod}-${zCod}-${pCod}`;
      const partidos = p.partidos || {};
      let topName = null, topV = 0;
      for (const [name, v] of Object.entries(partidos)){
        if (v > topV){ topV = v; topName = name; }
      }
      if (topName){
        const short = PARTIDO_SHORT[topName] || topName.split(/\s+/).slice(0,2).map(w => w[0]).join('').toUpperCase().slice(0,3);
        winners.set(k, short);
      }
    }
  }
  return winners;
}

function loadPres22Winners(jsonPath){
  // Esquema generado por build-historicos-puestos.js:
  //   { candidatos: { COD: {nombre,...} }, puestos: { key: {v: {COD: votos}, ...} } }
  const winners = new Map();   // key → short id
  if (!fs.existsSync(jsonPath)) return winners;
  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  const cands = data.candidatos || {};
  const codShort = {};
  for (const [cod, c] of Object.entries(cands)){
    codShort[cod] = PRES22_KEYS[c.nombre] || c.nombre.split(/\s+/)[0].toLowerCase();
  }
  for (const [key, p] of Object.entries(data.puestos || {})){
    let topCod = null, topV = 0;
    for (const [cod, v] of Object.entries(p.v || {})){
      if (v > topV){ topV = v; topCod = cod; }
    }
    if (topCod) winners.set(key, codShort[topCod] || topCod);
  }
  return winners;
}

function assignTiers(records){
  // Ordena por censo descendente y asigna tier 1 a top-300, tier 2 a top-1500, tier 3 al resto.
  const sorted = [...records].sort((a, b) => b.c - a.c);
  for (let i = 0; i < sorted.length; i++){
    const r = sorted[i];
    if (i < 300) r.t = 1;
    else if (i < 1500) r.t = 2;
    else r.t = 3;
  }
}

async function main(){
  const [, , georefPath, senadoDepsDir, pres22Path, outDir] = process.argv;
  if (!georefPath || !senadoDepsDir || !pres22Path || !outDir){
    console.error('Uso: node tools/build-puestos-nacional-light.js <georef.csv> <senado-deps-dir> <pres-2022-puestos.json> <out-dir>');
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  console.log(`\n[build-puestos-nacional-light]`);
  console.log(`  → leyendo GEOREF`);
  const t0 = Date.now();
  const georef = await readGeoref(georefPath);
  console.log(`    ${georef.size.toLocaleString('es-CO')} puestos georeferenciados`);

  console.log(`  → leyendo senado puestos por depto`);
  const sen = loadSenadoWinners(senadoDepsDir);
  console.log(`    ${sen.size.toLocaleString('es-CO')} puestos con ganador senado 2026`);

  console.log(`  → leyendo pres 2022 1V puestos`);
  const pres = loadPres22Winners(pres22Path);
  console.log(`    ${pres.size.toLocaleString('es-CO')} puestos con ganador pres 2022`);

  // Construye registros, descartando puestos sin geo válida
  const records = [];
  let geoNull = 0, censoNull = 0;
  for (const r of georef.values()){
    if (!Number.isFinite(r.y) || !Number.isFinite(r.x) || (r.y === 0 && r.x === 0)){ geoNull++; continue; }
    if (r.c <= 0) censoNull++;
    const out = { ...r };
    const p22 = pres.get(r.k);  if (p22) out.p22 = p22;
    const s26 = sen.get(r.k);   if (s26) out.s26 = s26;
    records.push(out);
  }

  assignTiers(records);

  const outFile = path.join(outDir, 'puestos-nacional-light.json');
  fs.writeFileSync(outFile, JSON.stringify(records));
  const sz = fs.statSync(outFile).size;

  console.log(`\n  ✓ ${path.basename(outFile)}   ${fmtKB(sz)} (${sz.toLocaleString('es-CO')} bytes)`);
  console.log(`    descartados: ${geoNull} sin coords · ${censoNull} sin censo`);
  console.log(`    con winner pres22: ${records.filter(r => r.p22).length}/${records.length}`);
  console.log(`    con winner sen26:  ${records.filter(r => r.s26).length}/${records.length}`);
  console.log(`    tier 1 (top 300):   ${records.filter(r => r.t === 1).length}`);
  console.log(`    tier 2 (top 1500):  ${records.filter(r => r.t === 2).length}`);
  console.log(`    tier 3 (resto):     ${records.filter(r => r.t === 3).length}`);
  console.log(`    tiempo total: ${((Date.now()-t0)/1000).toFixed(1)}s\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
