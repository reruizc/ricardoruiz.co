#!/usr/bin/env node
// tools/build-puestos-censos-agg.js
//
// Lee puestos-master.csv y emite un archivo MUY chico con censos
// agregados por scope (dep, mun, nacional). Lo carga el frontend al
// boot para alimentar _censoByDepCod / _censoByMunKey / _censoNacional
// SIN tener que descargar el archivo light completo (1.9 MB).
//
// Esto desbloquea la métrica corregida de SESGADAS_POR_UNIVERSO en
// precomputeBias y precomputeBiasMun (que se ejecutan al boot, antes
// de que el usuario active Puestos).
//
// Uso:
//   node tools/build-puestos-censos-agg.js <puestos-master.csv> <out-dir>
//
// Genera: {out-dir}/puestos-censos-agg.json (~20 KB)

const fs = require('fs');
const path = require('path');
const readline = require('readline');

async function main(){
  const [, , masterPath, outDir] = process.argv;
  if (!masterPath || !outDir){
    console.error('Uso: node tools/build-puestos-censos-agg.js <puestos-master.csv> <out-dir>');
    process.exit(1);
  }
  fs.mkdirSync(outDir, { recursive: true });

  const stream = fs.createReadStream(masterPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  const porDep = {}, porMun = {};
  let nacional = 0;
  let isHeader = true;
  for await (const rawLine of rl){
    if (isHeader){ isHeader = false; continue; }
    if (!rawLine.trim()) continue;
    const c = rawLine.split(';');
    if (c.length < 13) continue;
    const dd = c[0], mm = c[1];
    const total = parseInt(c[12], 10) || 0;
    if (total <= 0) continue;
    porDep[dd] = (porDep[dd] || 0) + total;
    const munKey = `${dd}-${mm}`;
    porMun[munKey] = (porMun[munKey] || 0) + total;
    nacional += total;
  }

  const out = {
    generado_en: new Date().toISOString(),
    fuente: 'puestos-master.csv (cruce Divipole_2026 + reporte_HVP_27012026)',
    nacional,
    porDep,
    porMun,
  };
  const outFile = path.join(outDir, 'puestos-censos-agg.json');
  fs.writeFileSync(outFile, JSON.stringify(out));
  const sz = fs.statSync(outFile).size;

  console.log(`\n[build-puestos-censos-agg]`);
  console.log(`  ✓ ${path.basename(outFile)}   ${(sz/1024).toFixed(1)} KB`);
  console.log(`    nacional: ${nacional.toLocaleString('es-CO')}`);
  console.log(`    deptos  : ${Object.keys(porDep).length} (incluye exterior)`);
  console.log(`    muns    : ${Object.keys(porMun).length}`);
  console.log('');
}

main().catch(e => { console.error(e); process.exit(1); });
