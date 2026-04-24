#!/usr/bin/env node
// tools/build-consultas-2026.js
//
// Convierte los JSONs pre-agregados de las tres consultas presidenciales
// 2026 (ubicados en Bases de datos/output_agregados/consultas/dep-*.json)
// al formato estándar de históricos para subir a S3.
//
//   output_historicos/consulta-2026-gran/{resumen,por-depto,por-mun}.json
//   output_historicos/consulta-2026-frente/...
//   output_historicos/consulta-2026-soluciones/...
//
// Uso:
//   node tools/build-consultas-2026.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_agregados/consultas" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_historicos"

const fs = require('fs');
const path = require('path');

const CONSULTAS = [
  { clave: 'gran',       nombre: 'La Gran Consulta por Colombia',        ganador: 'PALOMA SUSANA VALENCIA LASERNA' },
  { clave: 'frente',     nombre: 'Frente por la Vida',                   ganador: 'ROY LEONARDO BARRERAS MONTEALEGRE' },
  { clave: 'soluciones', nombre: 'Consulta de Soluciones',               ganador: 'CLAUDIA NAYIBE LOPEZ HERNANDEZ' },
];

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function buildConsulta(inputDir, outBase, cfg){
  const files = fs.readdirSync(inputDir).filter(n => /^dep-\d+\.json$/.test(n));
  if (!files.length) throw new Error(`No se encontraron dep-*.json en ${inputDir}`);

  // Índice por candidato-nombre → cod (1-based, asignado en orden de aparición)
  const candCod = {};
  let nextCod = 1;
  const getCod = (nombreNorm) => {
    if (!candCod[nombreNorm]){ candCod[nombreNorm] = String(nextCod++); }
    return candCod[nombreNorm];
  };

  // Acumuladores
  const nac = {};               // candCod → { nombre, votos }
  let nacTotalVotos = 0;
  const porDepto = {};          // depCod → { votos_validos, candidatos }
  const porMun   = {};          // "depCod-munCod" → { depCod, munCod, votos_validos, candidatos }

  for (const fname of files){
    const dep = JSON.parse(fs.readFileSync(path.join(inputDir, fname), 'utf8'));
    const depCod = String(dep.cod).padStart(2, '0');
    const depBlock = dep[cfg.clave];
    if (!depBlock) continue;

    // Nivel depto
    const depCands = {};
    let depVotos = 0;
    for (const c of depBlock.cands || []){
      const nm = normName(c.nombre);
      const cod = getCod(nm);
      depCands[cod] = { nombre: nm, votos: c.votos };
      depVotos += c.votos;
      if (!nac[cod]) nac[cod] = { nombre: nm, votos: 0 };
      nac[cod].votos += c.votos;
      nacTotalVotos += c.votos;
    }
    // Añadir pct por depto
    for (const cod of Object.keys(depCands)){
      depCands[cod].pct = depVotos > 0 ? +(depCands[cod].votos / depVotos * 100).toFixed(3) : 0;
    }
    porDepto[depCod] = {
      votos_validos: depVotos,
      votos_totales: depVotos,   // no tenemos blancos/nulos segregados por consulta
      especiales: {},
      candidatos: depCands,
    };

    // Nivel mun
    for (const m of dep.municipios || []){
      const munCod = String(m.cod).padStart(3, '0');
      const munBlock = m[cfg.clave];
      if (!munBlock) continue;
      const munCands = {};
      let munVotos = 0;
      for (const c of munBlock.cands || []){
        const nm = normName(c.nombre);
        const cod = getCod(nm);
        munCands[cod] = { nombre: nm, votos: c.votos };
        munVotos += c.votos;
      }
      for (const cod of Object.keys(munCands)){
        munCands[cod].pct = munVotos > 0 ? +(munCands[cod].votos / munVotos * 100).toFixed(3) : 0;
      }
      porMun[`${depCod}-${munCod}`] = {
        depCod, munCod,
        votos_validos: munVotos,
        votos_totales: munVotos,
        especiales: {},
        candidatos: munCands,
      };
    }
  }

  // Resumen nacional con pct
  const nacCands = {};
  for (const [cod, c] of Object.entries(nac)){
    nacCands[cod] = {
      nombre: c.nombre,
      votos: c.votos,
      pct: nacTotalVotos > 0 ? +(c.votos / nacTotalVotos * 100).toFixed(3) : 0,
    };
  }
  const resumen = {
    nombre: cfg.nombre,
    clave: cfg.clave,
    anio: 2026,
    ganador: cfg.ganador,
    generado_en: new Date().toISOString(),
    nacional: {
      votos_validos: nacTotalVotos,
      votos_totales: nacTotalVotos,
      especiales: {},
      candidatos: nacCands,
    },
  };

  const outDir = path.join(outBase, `consulta-2026-${cfg.clave}`);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'resumen.json'),    JSON.stringify(resumen, null, 2));
  fs.writeFileSync(path.join(outDir, 'por-depto.json'),  JSON.stringify(porDepto));
  fs.writeFileSync(path.join(outDir, 'por-mun.json'),    JSON.stringify(porMun));

  // Log
  const kb = p => Math.round(fs.statSync(p).size / 1024) + ' KB';
  console.log(`\n[${cfg.clave}] ${cfg.nombre}`);
  console.log(`  ${Object.keys(nacCands).length} candidatos · ${Object.keys(porDepto).length} deptos · ${Object.keys(porMun).length} muns`);
  console.log(`  nacional votos: ${nacTotalVotos.toLocaleString('es-CO')}`);
  const top = Object.values(nacCands).sort((a,b) => b.votos - a.votos).slice(0, 3);
  for (const c of top){ console.log(`    ${c.nombre.padEnd(42)} ${String(c.votos).padStart(10)} (${c.pct}%)`); }
  console.log(`  → resumen.json ${kb(path.join(outDir,'resumen.json'))}  por-depto ${kb(path.join(outDir,'por-depto.json'))}  por-mun ${kb(path.join(outDir,'por-mun.json'))}`);
}

function main(){
  const [, , inputDir, outBase] = process.argv;
  if (!inputDir || !outBase){
    console.error('Uso: node tools/build-consultas-2026.js <inputDir> <outBase>');
    process.exit(1);
  }
  for (const cfg of CONSULTAS){
    buildConsulta(inputDir, outBase, cfg);
  }
}

main();
