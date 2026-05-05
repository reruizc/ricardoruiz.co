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

// puestos-master.csv es el cruce de las 2 hojas de
// `Divipole_Congreso_CON DATOS.xlsx`: censo y demografía vienen de
// Divipole_2026 (cubre 41,3 M = padrón nacional oficial), las
// coordenadas vienen de reporte_HVP_27012026 (la otra hoja solo
// trae longitud por bug del Excel original). Generado por
// tools/build-puestos-master.py.
//
// Header: dd;mm;zz;pp;codigo;departamento;municipio;nombre_puesto;
//         direccion;comuna;mujeres;hombres;total;mesas;lat;lng
async function readPuestosMaster(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  const out = new Map();
  let header = null;
  for await (const rawLine of rl){
    if (!header){
      header = rawLine.replace(/^﻿/, '').split(';').map(s => s.trim());
      continue;
    }
    if (!rawLine.trim()) continue;
    const parts = rawLine.split(';');
    if (parts.length < 16) continue;
    const dd = parts[0], mm = parts[1], zz = parts[2], pp = parts[3];
    const k = `${dd}-${mm}-${zz}-${pp}`;
    const lat = parts[14] ? parseFloat(parts[14]) : NaN;
    const lng = parts[15] ? parseFloat(parts[15]) : NaN;
    out.set(k, {
      k,
      y: lat,
      x: lng,
      c: parseInt(parts[12], 10) || 0,   // total
      m: parseInt(parts[13], 10) || 0,   // mesas
      n: normName(parts[7]),             // nombre_puesto
      mn: normName(parts[6]),            // municipio
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

// Umbrales del LOD que el frontend espera. Si se modifican aquí, hay
// que sincronizarlos en previa-1v.html (PUE_TIER1_TOP / PUE_TIER2_TOP).
const TIER1_TOP = 500;
const TIER2_TOP = 1700;

function assignTiers(records){
  // Ordena por censo descendente y asigna tier 1 a top TIER1_TOP, tier 2
  // a top TIER2_TOP, tier 3 al resto.
  const sorted = [...records].sort((a, b) => b.c - a.c);
  for (let i = 0; i < sorted.length; i++){
    const r = sorted[i];
    if (i < TIER1_TOP) r.t = 1;
    else if (i < TIER2_TOP) r.t = 2;
    else r.t = 3;
  }
}

async function main(){
  const [, , masterPath, senadoDepsDir, pres22Path, outDir] = process.argv;
  if (!masterPath || !senadoDepsDir || !pres22Path || !outDir){
    console.error('Uso: node tools/build-puestos-nacional-light.js <puestos-master.csv> <senado-deps-dir> <pres-2022-puestos.json> <out-dir>');
    console.error('  El CSV maestro se genera con tools/build-puestos-master.py.');
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  console.log(`\n[build-puestos-nacional-light]`);
  console.log(`  → leyendo CSV maestro de puestos`);
  const t0 = Date.now();
  const master = await readPuestosMaster(masterPath);
  const totalCenso = [...master.values()].reduce((s,r) => s + r.c, 0);
  console.log(`    ${master.size.toLocaleString('es-CO')} puestos · censo total = ${totalCenso.toLocaleString('es-CO')}`);

  console.log(`  → leyendo senado puestos por depto`);
  const sen = loadSenadoWinners(senadoDepsDir);
  console.log(`    ${sen.size.toLocaleString('es-CO')} puestos con ganador senado 2026`);

  console.log(`  → leyendo pres 2022 1V puestos`);
  const pres = loadPres22Winners(pres22Path);
  console.log(`    ${pres.size.toLocaleString('es-CO')} puestos con ganador pres 2022`);

  // Solo entran al mapa los puestos con coordenadas válidas. Los consulares
  // (dep 88) no tienen lat/lng — el frontend no los pinta pero podrían
  // entrar en agregaciones nacionales más adelante si se necesita.
  const records = [];
  let sinCoords = 0, sinCenso = 0;
  for (const r of master.values()){
    if (!Number.isFinite(r.y) || !Number.isFinite(r.x) || (r.y === 0 && r.x === 0)){ sinCoords++; continue; }
    if (r.c <= 0) sinCenso++;
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
  console.log(`    descartados sin coords: ${sinCoords} (consulares y similares)`);
  console.log(`    sin censo en mapa     : ${sinCenso}`);
  console.log(`    con winner pres22: ${records.filter(r => r.p22).length}/${records.length}`);
  console.log(`    con winner sen26:  ${records.filter(r => r.s26).length}/${records.length}`);
  console.log(`    tier 1 (top ${TIER1_TOP}):   ${records.filter(r => r.t === 1).length}`);
  console.log(`    tier 2 (top ${TIER2_TOP}):  ${records.filter(r => r.t === 2).length}`);
  console.log(`    tier 3 (resto):       ${records.filter(r => r.t === 3).length}`);
  console.log(`    tiempo total: ${((Date.now()-t0)/1000).toFixed(1)}s\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
