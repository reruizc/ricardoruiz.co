#!/usr/bin/env node
// tools/build-consultas-puestos.js
//
// Procesa los CSVs MMV_*.csv de DEPTOS_DECLARADOS (declarados por depto del
// congreso 2026) y emite un agregado a nivel PUESTO de las 3 consultas
// presidenciales 2026 (CORCODIGO=06).
//
// PARNOMBRE / clave consulta:
//   0100 LA CONSULTA DE LAS SOLUCIONES   → soluciones (Claudia López)
//   0200 LA GRAN CONSULTA POR COLOMBIA   → gran        (Paloma Valencia)
//   0300 FRENTE POR LA VIDA              → frente      (Roy Barreras)
//
// Output (un archivo por depto):
//   {outDir}/{depCod}/puestos.json
//   {
//     "dep_cod": "01", "dep_nom": "ANTIOQUIA",
//     "candidatos": {
//       "gran":       { "<COD_CAN>": "<NOMBRE>", ... },
//       "frente":     { ... },
//       "soluciones": { ... }
//     },
//     "puestos": [
//       { "dep_cod","mun_cod","mun_nom","zon_cod","pue_cod","cod","nombre",
//         "consultas": {
//           "gran":       { "vv":N, "vb":N, "vn":N, "vm":N, "v": {"<COD_CAN>":N} },
//           "frente":     { ... },
//           "soluciones": { ... }
//         }
//       }, ...
//     ]
//   }
//
// Uso:
//   node tools/build-consultas-puestos.js <input-dir> <out-dir>
//
// Ejemplo:
//   node tools/build-consultas-puestos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/DEPTOS_DECLARADOS" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_agregados/consultas/departamentos"

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// PARCODIGO → clave corta (la misma que ya usa el agregador deps de consultas)
const CONSULTA_KEY = {
  '0100': 'soluciones',
  '0200': 'gran',
  '0300': 'frente',
};

// COD_CAN especiales (se contabilizan en blanco/nulo/no_marcado)
const SPECIAL_CODES = {
  '996': 'vb',
  '997': 'vn',
  '998': 'vm',
  '999': 'vm',
};

const SPECIAL_NAMES = new Set(['VOTO EN BLANCO', 'VOTOS NULOS', 'NO MARCADOS', 'NO MARCADO', '']);

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function pad(s, n){ return String(parseInt(s, 10) || 0).padStart(n, '0'); }
function pad4(s){ return String(parseInt(s, 10) || 0).padStart(4, '0'); }
function fmtMB(b){ return (b/1024/1024).toFixed(2) + ' MB'; }

function parseHeaderLine(line){
  const clean = line.replace(/^﻿/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['DEP','DEPNOMBRE','MUN','MUNNOMBRE','ZONA','PUESTO','PUESNOMBRE','CORCODIGO','PAR','CAN','CANNOMBRE','VOTOS'];
  const missing = required.filter(r => !(r in map));
  if (missing.length){
    throw new Error(`Header sin columnas: ${missing.join(', ')}`);
  }
  return map;
}

async function processFile(filePath, accum){
  const stream = fs.createReadStream(filePath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  let idx = null;
  let rows = 0;
  for await (const rawLine of rl){
    if (idx === null){ idx = parseHeaderLine(rawLine); continue; }
    const line = rawLine.trim();
    if (!line) continue;
    const parts = line.split(';');
    const cor = parts[idx['CORCODIGO']];
    if (cor !== '06') continue;  // sólo consultas

    const par = pad4(parts[idx['PAR']]);
    const consultaKey = CONSULTA_KEY[par];
    if (!consultaKey) continue;  // PAR=0000 (totales) u otro

    const dep    = pad(parts[idx['DEP']], 2);
    const mun    = pad(parts[idx['MUN']], 3);
    const munNom = parts[idx['MUNNOMBRE']];
    const depNom = parts[idx['DEPNOMBRE']];
    const zon    = pad(parts[idx['ZONA']], 2);
    const pue    = pad(parts[idx['PUESTO']], 2);
    const pueNom = parts[idx['PUESNOMBRE']];
    const can    = pad4(parts[idx['CAN']]);
    const canNom = parts[idx['CANNOMBRE']] || '';
    const votos  = parseInt(parts[idx['VOTOS']] || '0', 10);
    if (!Number.isFinite(votos) || votos <= 0) continue;

    const depBucket = accum.byDep.get(dep) || {
      dep_cod: dep, dep_nom: normName(depNom),
      candidatos: { gran:{}, frente:{}, soluciones:{} },
      puestos: new Map(),
    };
    if (!accum.byDep.has(dep)) accum.byDep.set(dep, depBucket);

    const puKey = `${mun}-${zon}-${pue}`;
    let pu = depBucket.puestos.get(puKey);
    if (!pu){
      pu = {
        dep_cod: dep, mun_cod: mun, mun_nom: normName(munNom),
        zon_cod: zon, pue_cod: pue, cod: puKey, nombre: normName(pueNom),
        consultas: { gran: null, frente: null, soluciones: null },
      };
      depBucket.puestos.set(puKey, pu);
    }
    let bucket = pu.consultas[consultaKey];
    if (!bucket){ bucket = { vv: 0, vb: 0, vn: 0, vm: 0, v: {} }; pu.consultas[consultaKey] = bucket; }

    // Detección de blanco/nulo/no marcado: por COD_CAN o por nombre
    const upper = normName(canNom);
    const special =
      SPECIAL_CODES[can] ||
      (upper === 'VOTO EN BLANCO' ? 'vb' : null) ||
      (upper === 'VOTOS NULOS' ? 'vn' : null) ||
      (upper === 'NO MARCADOS' || upper === 'NO MARCADO' ? 'vm' : null);

    if (special){
      bucket[special] += votos;
    } else {
      bucket.v[can] = (bucket.v[can] || 0) + votos;
      bucket.vv += votos;
      // Catálogo de nombres de candidatos por consulta (primera ocurrencia)
      if (!depBucket.candidatos[consultaKey][can]) depBucket.candidatos[consultaKey][can] = normName(canNom);
    }
    rows++;
  }
  return rows;
}

async function main(){
  const [, , inDir, outDir] = process.argv;
  if (!inDir || !outDir){
    console.error('Uso: node tools/build-consultas-puestos.js <input-dir-DEPTOS_DECLARADOS> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(inDir)){ console.error(`No existe: ${inDir}`); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });

  const files = fs.readdirSync(inDir)
    .filter(f => /^MMV_.*\.csv$/i.test(f))
    .map(f => path.join(inDir, f));

  console.log(`\n[build-consultas-puestos] ${files.length} archivos MMV en ${inDir}`);

  const accum = { byDep: new Map() };
  const t0 = Date.now();
  let totalRows = 0;

  for (const fp of files){
    const r = await processFile(fp, accum);
    totalRows += r;
  }

  console.log(`  ${totalRows.toLocaleString('es-CO')} filas de consulta procesadas en ${((Date.now()-t0)/1000).toFixed(1)}s`);
  console.log(`  ${accum.byDep.size} deptos con consultas`);

  let totalBytes = 0;
  for (const [dep, bucket] of [...accum.byDep.entries()].sort()){
    const puestosArr = [...bucket.puestos.values()];
    const out = {
      dep_cod: bucket.dep_cod,
      dep_nom: bucket.dep_nom,
      candidatos: bucket.candidatos,
      puestos: puestosArr,
    };
    const subDir = path.join(outDir, dep);
    fs.mkdirSync(subDir, { recursive: true });
    const outFile = path.join(subDir, 'puestos.json');
    fs.writeFileSync(outFile, JSON.stringify(out));
    const sz = fs.statSync(outFile).size;
    totalBytes += sz;
    console.log(`  ✓ ${dep}/puestos.json   ${puestosArr.length.toString().padStart(5)} puestos · ${fmtMB(sz)}`);
  }
  console.log(`  total: ${fmtMB(totalBytes)} en ${accum.byDep.size} archivos\n`);

  // Sanity: nacional por consulta (primer ganador)
  const nat = { gran: {}, frente: {}, soluciones: {} };
  for (const bucket of accum.byDep.values()){
    for (const pu of bucket.puestos.values()){
      for (const [k, c] of Object.entries(pu.consultas)){
        if (!c) continue;
        for (const [cod, votos] of Object.entries(c.v)){
          nat[k][cod] = (nat[k][cod] || 0) + votos;
        }
      }
    }
  }
  for (const [k, byCod] of Object.entries(nat)){
    const top = Object.entries(byCod).sort((a,b)=>b[1]-a[1]).slice(0,3);
    if (!top.length) continue;
    const total = Object.values(byCod).reduce((s,v)=>s+v,0);
    console.log(`  consulta ${k} · top 3:`);
    for (const [cod, v] of top){
      // buscar nombre en cualquier depto que tenga ese cod
      let name = cod;
      for (const b of accum.byDep.values()){
        if (b.candidatos[k][cod]){ name = b.candidatos[k][cod]; break; }
      }
      console.log(`    ${name.padEnd(40)} ${String(v).padStart(10)} (${(v/total*100).toFixed(2)}%)`);
    }
  }
}

main().catch(e => { console.error(e); process.exit(1); });
