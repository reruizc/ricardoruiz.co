#!/usr/bin/env node
// tools/bloques-historicos/build.js
//
// Procesa los GCS_*PRES1V.csv (2010, 2014, 2018, 2022) y produce un dataset
// agregado de votación por BLOQUE IDEOLÓGICO por municipio por año.
//
// Bloques:
//   izq   = izquierda
//   ci    = centro-izquierda
//   c     = centro
//   cd    = centro-derecha
//   d     = derecha
//   otros = candidatos minoritarios sin clasificar
//
// Para cada (mun, año) se calcula el % de votos válidos asignado a cada
// bloque. Esto alimenta el rediseño de Veleta (Cepeda / Abelardo / Paloma).
//
// Uso:
//   node tools/bloques-historicos/build.js [GCS_DIR] [OUT_DIR]
//
// Defaults:
//   GCS_DIR = "Bases de datos/FINAL SUBIDA GCS"
//   OUT_DIR = "Bases de datos/output_bloques"
//
// Outputs:
//   por-mun.json    { "depCod-munCod": { depCod, munCod, "2010":{...}, "2014":{...}, ... } }
//   por-depto.json  { "depCod":         { depCod,         "2010":{...}, ... } }
//   nacional.json   { "2010":{...}, ... } + meta
//
// Cada año en cada scope tiene la forma:
//   { vv:int, izq:pct, ci:pct, c:pct, cd:pct, d:pct, otros:pct }
//   donde pct está en 0..100 con 3 decimales, sobre votos válidos.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SPECIAL_CODES = new Set(['996','997','998','999']);
const BLOQUES = ['izq','ci','c','cd','d','otros'];

// ───── Mapping candidato → bloque, por año.
// Match por substring sobre el nombre normalizado (mayúscula sin tildes).
// Patrones elegidos para ser únicos por candidato y robustos a variantes.
// Nota: matching por substring sobre nombre normalizado. Los GCS varían
// el formato del nombre entre años (a veces incluye segundo apellido,
// a veces no). Patrones elegidos para ser únicos al candidato.
const BLOQUE_MAP = {
  2010: {
    izq: ['PETRO'],
    ci:  ['PARDO RUEDA'],
    c:   ['MOCKUS'],
    cd:  ['VARGAS LLERAS'],
    d:   ['JUAN MANUEL SANTOS', 'SANIN POSADA'],
  },
  2014: {
    izq: ['CLARA', 'LOPEZ OBREGON'],     // Clara López, PDA-UP
    ci:  [],
    c:   ['PENALOSA'],                   // Enrique Peñalosa, Verde
    cd:  ['JUAN MANUEL SANTOS'],         // Unidad Nacional, post-Habana
    d:   ['ZULUAGA', 'MARTHA LUCIA RAMIREZ'],
  },
  2018: {
    izq: ['PETRO'],
    ci:  ['DE LA CALLE'],
    c:   ['FAJARDO'],
    cd:  ['VARGAS LLERAS'],
    d:   ['DUQUE', 'VIVIANE MORALES'],
  },
  2022: {
    izq: ['PETRO'],
    ci:  [],
    c:   ['FAJARDO', 'BETANCOURT'],
    cd:  ['RODOLFO HERNANDEZ', 'LUIS PEREZ'],
    d:   ['FEDERICO GUTIERREZ', 'MILTON RODRIGUEZ', 'ENRIQUE GOMEZ'],
  },
};

const FILES = {
  2010: 'GCS_2010PRES1V.csv',
  2014: 'GCS_2014PRES1V.csv',
  2018: 'GCS_2018PRES1V.csv',
  2022: 'GCS_2022PRES1V.csv',
};

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function classifyCandidate(year, name){
  const map = BLOQUE_MAP[year];
  if (!map) return 'otros';
  for (const bloque of ['izq','ci','c','cd','d']){
    for (const pat of map[bloque] || []){
      if (name.includes(pat)) return bloque;
    }
  }
  return 'otros';
}

function emptyAgg(){
  const a = { vv: 0 };
  for (const b of BLOQUES) a[b] = 0;
  return a;
}

async function processYear(year, csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  const muns = new Map();           // 'dep-mun' → { depCod, munCod, agg }
  const deptos = new Map();          // depCod → agg
  const nacional = emptyAgg();

  // Diagnóstico: registrar nombres únicos clasificados por bloque
  const candIndex = new Map();      // normName → { bloque, votos }
  let idx = null;
  let rowsRead = 0;
  let rowsAgg = 0;

  for await (const rawLine of rl){
    if (idx === null){
      const clean = rawLine.replace(/^﻿/, '');
      const cols = clean.split(';').map(s => s.trim());
      idx = {};
      cols.forEach((c, i) => { idx[c] = i; });
      const required = ['COD_DDE','COD_MME','COD_CAN','DES_CAN','NUM_VOT'];
      const missing = required.filter(r => !(r in idx));
      if (missing.length) throw new Error(`Header CSV ${year} sin columnas: ${missing.join(', ')}`);
      continue;
    }
    const line = rawLine.trim();
    if (!line) continue;
    rowsRead++;

    const parts = line.split(';');
    const dep = parts[idx['COD_DDE']];
    const mun = parts[idx['COD_MME']];
    const cod = parts[idx['COD_CAN']];
    const des = normName(parts[idx['DES_CAN']] || '');
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);

    if (!dep || !cod || !Number.isFinite(votos) || votos <= 0) continue;
    if (SPECIAL_CODES.has(cod)) continue;  // blanco/nulo/no_marcados fuera

    const depK = String(parseInt(dep, 10)).padStart(2, '0');
    const munK = `${depK}-${String(parseInt(mun, 10) || 0).padStart(3, '0')}`;
    const bloque = classifyCandidate(year, des);

    // Acumular en mun
    let m = muns.get(munK);
    if (!m){ m = { depCod: depK, munCod: munK.split('-')[1], agg: emptyAgg() }; muns.set(munK, m); }
    m.agg[bloque] += votos;
    m.agg.vv += votos;

    // Acumular en depto
    let d = deptos.get(depK);
    if (!d){ d = emptyAgg(); deptos.set(depK, d); }
    d[bloque] += votos;
    d.vv += votos;

    // Acumular en nacional
    nacional[bloque] += votos;
    nacional.vv += votos;

    // Diagnóstico
    let ci = candIndex.get(des);
    if (!ci){ ci = { bloque, votos: 0 }; candIndex.set(des, ci); }
    ci.votos += votos;

    rowsAgg++;
  }

  // Convertir absolutos a pct sobre vv
  function aggToPct(agg){
    const out = { vv: agg.vv };
    for (const b of BLOQUES){
      out[b] = agg.vv > 0 ? +(agg[b] / agg.vv * 100).toFixed(3) : 0;
    }
    return out;
  }

  const munsOut = {};
  for (const [k, v] of muns) munsOut[k] = { depCod: v.depCod, munCod: v.munCod, ...aggToPct(v.agg) };
  const deptosOut = {};
  for (const [k, v] of deptos) deptosOut[k] = aggToPct(v);
  const nacionalOut = aggToPct(nacional);

  return { munsOut, deptosOut, nacionalOut, rowsRead, rowsAgg, candIndex, year };
}

async function main(){
  const gcsDir = process.argv[2] || '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS';
  const outDir = process.argv[3] || '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_bloques';
  if (!fs.existsSync(gcsDir)){ console.error(`No existe GCS dir: ${gcsDir}`); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });

  const years = Object.keys(FILES).map(Number).sort();
  const porMun = {};                  // 'dep-mun' → { depCod, munCod, '2010':..., '2014':..., ... }
  const porDepto = {};                // depCod → { depCod, '2010':..., ... }
  const nacional = {};                // '2010':..., '2014':..., ...

  for (const year of years){
    const csvPath = path.join(gcsDir, FILES[year]);
    if (!fs.existsSync(csvPath)){ console.error(`Falta ${csvPath}`); process.exit(1); }
    console.log(`\n[bloques] ${year} · ${path.basename(csvPath)}`);
    const t0 = Date.now();
    const res = await processYear(year, csvPath);
    const dt = ((Date.now()-t0)/1000).toFixed(1);
    console.log(`  ${res.rowsRead.toLocaleString('es-CO')} filas (${res.rowsAgg.toLocaleString('es-CO')} agregadas) en ${dt}s`);
    console.log(`  ${Object.keys(res.munsOut).length} muns · ${Object.keys(res.deptosOut).length} deptos · vv nacional ${res.nacionalOut.vv.toLocaleString('es-CO')}`);

    // Sanity check: top candidatos por bloque
    const byBloque = { izq:[],ci:[],c:[],cd:[],d:[],otros:[] };
    for (const [name, info] of res.candIndex) byBloque[info.bloque].push({ name, votos: info.votos });
    for (const b of BLOQUES){
      const top = byBloque[b].sort((a,b)=>b.votos-a.votos).slice(0,4);
      const pct = (res.nacionalOut[b]).toFixed(2);
      console.log(`    ${b.padEnd(5)} ${pct.padStart(6)}%  ${top.map(t=>`${t.name.split(' ').slice(0,3).join(' ')}(${(t.votos/1e6).toFixed(2)}M)`).join('  ')}`);
    }

    // Mergear en estructura cross-year
    for (const [k, v] of Object.entries(res.munsOut)){
      if (!porMun[k]) porMun[k] = { depCod: v.depCod, munCod: v.munCod };
      const { depCod, munCod, ...payload } = v;
      porMun[k][year] = payload;
    }
    for (const [k, v] of Object.entries(res.deptosOut)){
      if (!porDepto[k]) porDepto[k] = { depCod: k };
      porDepto[k][year] = v;
    }
    nacional[year] = res.nacionalOut;
  }

  const meta = {
    generado_en: new Date().toISOString(),
    años: years,
    bloques: BLOQUES,
    fuente: 'Registraduría Nacional del Estado Civil — GCS_*PRES1V.csv',
    metodo: 'Suma directa de votos por candidato → bloque ideológico, sobre votos válidos (excluye blanco, nulos, no_marcados).',
    nacional,
  };

  const pMun = path.join(outDir, 'por-mun.json');
  const pDep = path.join(outDir, 'por-depto.json');
  const pNac = path.join(outDir, 'nacional.json');
  fs.writeFileSync(pMun, JSON.stringify(porMun));
  fs.writeFileSync(pDep, JSON.stringify(porDepto));
  fs.writeFileSync(pNac, JSON.stringify(meta, null, 2));

  function fmt(b){ return (b/1024 < 1024) ? `${(b/1024).toFixed(1)} KB` : `${(b/1024/1024).toFixed(2)} MB`; }
  console.log(`\n[bloques] outputs en ${outDir}`);
  console.log(`  por-mun.json   ${fmt(fs.statSync(pMun).size)}`);
  console.log(`  por-depto.json ${fmt(fs.statSync(pDep).size)}`);
  console.log(`  nacional.json  ${fmt(fs.statSync(pNac).size)}`);

  // Sanity nacional: bloques en 4 años (debería verse el corrimiento)
  console.log(`\n[bloques] evolución nacional (% sobre votos válidos)`);
  console.log(`  ${'año'.padEnd(6)} ${BLOQUES.map(b=>b.padStart(7)).join(' ')}`);
  for (const y of years){
    const row = nacional[y];
    console.log(`  ${String(y).padEnd(6)} ${BLOQUES.map(b=>row[b].toFixed(2).padStart(7)).join(' ')}`);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
