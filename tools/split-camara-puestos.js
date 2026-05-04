#!/usr/bin/env node
// tools/split-camara-puestos.js
//
// Toma el JSON nacional de puestos de cámara 2026 (~102 MB) ya generado en
// `output_agregados/camara/puestos.json` y lo parte en N archivos por depto:
//
//   {outDir}/{depCod}/puestos.json   (uno por depto, padding 2 dígitos)
//
// Estructura del input: array plano con cada puesto como objeto
// (mismo schema que `senado/departamentos/{cod}/puestos.json`).
//
// Uso:
//   node tools/split-camara-puestos.js <input.json> <out-dir>
//
// Ejemplo:
//   node tools/split-camara-puestos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_agregados/camara/puestos.json" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_agregados/camara/departamentos"

const fs = require('fs');
const path = require('path');

function fmtMB(b){ return (b/1024/1024).toFixed(2) + ' MB'; }

function main(){
  const [, , inputPath, outDir] = process.argv;
  if (!inputPath || !outDir){
    console.error('Uso: node tools/split-camara-puestos.js <input.json> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(inputPath)){
    console.error(`No existe: ${inputPath}`);
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  console.log(`\n[split-camara-puestos] leyendo ${path.basename(inputPath)} (${fmtMB(fs.statSync(inputPath).size)})…`);
  const t0 = Date.now();
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  if (!Array.isArray(data)) throw new Error('Esperaba array de puestos en el input');
  console.log(`  ${data.length.toLocaleString('es-CO')} puestos cargados en ${((Date.now()-t0)/1000).toFixed(1)}s`);

  // Agrupa por dep_cod
  const byDep = new Map();
  for (const p of data){
    const dep = String(p.dep_cod || '').padStart(2, '0');
    if (!byDep.has(dep)) byDep.set(dep, []);
    byDep.get(dep).push(p);
  }
  console.log(`  ${byDep.size} deptos detectados`);

  // Escribe un archivo por depto
  let totalBytes = 0;
  for (const [dep, list] of [...byDep.entries()].sort()){
    const subDir = path.join(outDir, dep);
    fs.mkdirSync(subDir, { recursive: true });
    const outFile = path.join(subDir, 'puestos.json');
    const json = JSON.stringify(list);
    fs.writeFileSync(outFile, json);
    const sz = fs.statSync(outFile).size;
    totalBytes += sz;
    console.log(`  ✓ ${dep}/puestos.json   ${list.length.toString().padStart(5)} puestos · ${fmtMB(sz)}`);
  }
  console.log(`  total: ${fmtMB(totalBytes)} en ${byDep.size} archivos\n`);
}

main();
