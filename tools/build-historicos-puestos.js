#!/usr/bin/env node
// tools/build-historicos-puestos.js
//
// Procesa un archivo GCS (Gran Consolidado Seccional) de la Registraduría
// y emite UN solo agregado a nivel de PUESTO de votación:
//
//   {outDir}/por-puesto.json
//
// Estructura compacta:
//   {
//     "meta": { archivo_origen, generado_en, anio, vuelta, ... },
//     "candidatos": {
//       "<COD_CAN>": { "nombre": "...", "partido": "..." }
//     },
//     "puestos": {
//       "<depCod>-<munCod>-<zonaCod>-<puestoCod>": {
//         "vv": <votos_validos>,
//         "vb": <blancos>, "vn": <nulos>, "vm": <no_marcados>,
//         "v":  { "<COD_CAN>": votos, ... }
//       }
//     }
//   }
//
// Notas de diseño:
//  - Dejamos el catálogo de candidatos en su propio bloque para no repetir
//    nombres en cada puesto (ahorra ~40-50% del tamaño final).
//  - `v` solo lista los COD_CAN con votos > 0 en ese puesto.
//  - El frontend reconstruye %, ganador, etc.
//  - Padding: depCod 2, munCod 3, zonaCod 2, puestoCod 2 (para uniformidad
//    con el resto del pipeline y permitir lookups O(1) por key).
//
// Uso:
//   node tools/build-historicos-puestos.js <archivo.csv> <out-dir> [--meta k=v,k=v]
//
// Ejemplo:
//   node tools/build-historicos-puestos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES1V.csv" \
//     "./out/pres-2022-v1" \
//     --meta anio=2022,vuelta=1,nombre=Presidencial2022V1

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SPECIAL_CODES = {
  '996': 'vb',  // blanco
  '997': 'vn',  // nulo
  '998': 'vm',  // no marcado
  '999': 'vm',
};

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function pad(s, n){ return String(parseInt(s, 10) || 0).padStart(n, '0'); }

function parseHeaderLine(line){
  const clean = line.replace(/^﻿/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['COD_DDE', 'COD_MME', 'COD_ZZ', 'COD_PP', 'COD_CAN', 'DES_CAN', 'NUM_VOT'];
  const missing = required.filter(r => !(r in map));
  if (missing.length){
    throw new Error(`Header CSV sin columnas requeridas: ${missing.join(', ')}. Header leído: ${cols.join(';')}`);
  }
  return map;
}

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

  let idx = null;
  let rowsRead = 0, rowsAgg = 0;

  const candidatos = new Map();   // cod → { nombre, partido, votos }
  const puestos    = new Map();   // key → { vv, vb, vn, vm, v: Map<cod, votos> }

  function ensurePuesto(key){
    let p = puestos.get(key);
    if (!p){
      p = { vv: 0, vb: 0, vn: 0, vm: 0, v: new Map() };
      puestos.set(key, p);
    }
    return p;
  }

  function ensureCand(cod, nombre, partido){
    let c = candidatos.get(cod);
    if (!c){
      c = { nombre, partido, votos: 0 };
      candidatos.set(cod, c);
    } else {
      if (!c.nombre && nombre) c.nombre = nombre;
      if (!c.partido && partido) c.partido = partido;
    }
    return c;
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
    const zon   = parts[idx['COD_ZZ']];
    const pue   = parts[idx['COD_PP']];
    const cod   = parts[idx['COD_CAN']];
    const des   = parts[idx['DES_CAN']] || '';
    const par   = idx['DES_PAR'] != null ? (parts[idx['DES_PAR']] || '') : '';
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);

    if (!dep || !cod || !Number.isFinite(votos) || votos <= 0) continue;

    const key = `${pad(dep, 2)}-${pad(mun, 3)}-${pad(zon, 2)}-${pad(pue, 2)}`;
    const p = ensurePuesto(key);

    const special = SPECIAL_CODES[cod];
    if (special){
      p[special] += votos;
    } else {
      ensureCand(cod, normName(des), normName(par)).votos += votos;
      p.v.set(cod, (p.v.get(cod) || 0) + votos);
      p.vv += votos;
    }
    rowsAgg++;
  }

  return { candidatos, puestos, rowsRead, rowsAgg };
}

function fmtMB(bytes){ return (bytes/1024/1024).toFixed(2) + ' MB'; }

async function main(){
  const { csvPath, outDir, meta } = parseArgs(process.argv);
  if (!csvPath || !outDir){
    console.error('Uso: node tools/build-historicos-puestos.js <archivo.csv> <out-dir> [--meta k=v,k=v]');
    process.exit(1);
  }
  if (!fs.existsSync(csvPath)){
    console.error(`No existe el archivo: ${csvPath}`);
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  console.log(`\n[build-historicos-puestos] procesando ${path.basename(csvPath)}`);
  const t0 = Date.now();
  const { candidatos, puestos, rowsRead, rowsAgg } = await processCsv(csvPath);
  const dt = ((Date.now() - t0) / 1000).toFixed(1);

  console.log(`  ${rowsRead.toLocaleString('es-CO')} filas leídas (${rowsAgg.toLocaleString('es-CO')} agregadas) en ${dt}s`);
  console.log(`  ${puestos.size.toLocaleString('es-CO')} puestos · ${candidatos.size} candidatos`);

  // Catálogo de candidatos
  const candOut = {};
  for (const [cod, c] of candidatos){
    candOut[cod] = { nombre: c.nombre, partido: c.partido, votos: c.votos };
  }

  // Puestos compactos (Map → Object plano para JSON)
  const pueOut = {};
  for (const [key, p] of puestos){
    const v = {};
    for (const [cod, votos] of p.v) v[cod] = votos;
    pueOut[key] = { vv: p.vv, vb: p.vb, vn: p.vn, vm: p.vm, v };
  }

  const out = {
    ...meta,
    archivo_origen: path.basename(csvPath),
    rows_leidas: rowsRead,
    rows_agregadas: rowsAgg,
    n_puestos: puestos.size,
    generado_en: new Date().toISOString(),
    candidatos: candOut,
    puestos: pueOut,
  };

  const op = path.join(outDir, 'por-puesto.json');
  fs.writeFileSync(op, JSON.stringify(out));
  console.log(`  ✓ por-puesto.json   ${fmtMB(fs.statSync(op).size)}`);

  // Sanity: top 5 candidatos
  console.log(`  top 5 nacional:`);
  const top = Object.entries(candOut)
    .sort((a,b) => b[1].votos - a[1].votos).slice(0, 5);
  for (const [cod, c] of top){
    const pctTotal = Object.values(candOut).reduce((s, x) => s + x.votos, 0);
    const pct = pctTotal > 0 ? (c.votos / pctTotal * 100).toFixed(2) : '0.00';
    console.log(`    ${(c.nombre || '?').padEnd(40)} ${String(c.votos).padStart(12)} (${pct}%)`);
  }
  console.log('');
}

main().catch(e => { console.error(e); process.exit(1); });
