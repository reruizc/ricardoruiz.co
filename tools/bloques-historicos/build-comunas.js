#!/usr/bin/env node
// tools/bloques-historicos/build-comunas.js
//
// Procesa los por-comuna.json históricos de las 13 ciudades en
// Bases de datos/output_ciudades/{ciudad}/historicos-comuna/pres-{año}/
// y produce bloques por comuna por año, con el mismo mapping
// candidato→bloque que el script nacional (build.js).
//
// Output (gitignored):
//   Bases de datos/output_bloques/ciudades/{ciudad}.json
//
// Schema por archivo de ciudad:
//   {
//     ciudad: "bogota",
//     meta: { ... },
//     comunas: {
//       "10": {
//         cod: "10", nombre: "ENGATIVÁ",
//         "2010": { vv, izq, ci, c, cd, d, otros },
//         "2014": {...}, "2018": {...}, "2022": {...}
//       },
//       ...
//     }
//   }

const fs = require('fs');
const path = require('path');

const BASE = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos';
const IN_DIR = `${BASE}/output_ciudades`;
const OUT_DIR = `${BASE}/output_bloques/ciudades`;

const BLOQUES = ['izq','ci','c','cd','d','otros'];

// Mismo mapping que tools/bloques-historicos/build.js. Mantener sincronizado.
const BLOQUE_MAP = {
  2010: {
    izq: ['PETRO'],
    ci:  ['PARDO RUEDA'],
    c:   ['MOCKUS'],
    cd:  ['VARGAS LLERAS'],
    d:   ['JUAN MANUEL SANTOS', 'SANIN POSADA'],
  },
  2014: {
    izq: ['CLARA', 'LOPEZ OBREGON'],
    ci:  [],
    c:   ['PENALOSA'],
    cd:  ['JUAN MANUEL SANTOS'],
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

function processComuna(comunaData, year){
  // Schema: { cod, nombre, votos_validos, candidatos: [{nombre, partido, votos, pct}] }
  const agg = { vv: 0 };
  for (const b of BLOQUES) agg[b] = 0;
  for (const c of (comunaData.candidatos || [])){
    const name = normName(c.nombre);
    const votos = c.votos || 0;
    if (votos <= 0) continue;
    const bloque = classifyCandidate(year, name);
    agg[bloque] += votos;
    agg.vv += votos;
  }
  // Convertir a pct sobre vv
  const out = { vv: agg.vv };
  for (const b of BLOQUES){
    out[b] = agg.vv > 0 ? +(agg[b] / agg.vv * 100).toFixed(3) : 0;
  }
  return out;
}

function processCity(cityKey){
  const cityDir = path.join(IN_DIR, cityKey, 'historicos-comuna');
  if (!fs.existsSync(cityDir)) return null;

  const years = [2010, 2014, 2018, 2022];
  const comunas = {};

  for (const year of years){
    const fp = path.join(cityDir, `pres-${year}`, 'por-comuna.json');
    if (!fs.existsSync(fp)){ console.warn(`  [${cityKey}] falta ${fp}`); continue; }
    const j = JSON.parse(fs.readFileSync(fp, 'utf8'));
    const porComuna = j.por_comuna || {};
    for (const [cod, c] of Object.entries(porComuna)){
      if (!comunas[cod]){
        comunas[cod] = { cod: c.cod || cod, nombre: c.nombre || '' };
      }
      // Actualizar nombre si está vacío
      if (!comunas[cod].nombre && c.nombre) comunas[cod].nombre = c.nombre;
      comunas[cod][year] = processComuna(c, year);
    }
  }

  return {
    ciudad: cityKey,
    meta: {
      generado_en: new Date().toISOString(),
      años: years,
      fuente: `output_ciudades/${cityKey}/historicos-comuna/`,
      metodo: 'Mismo mapping candidato→bloque que build.js nacional. Pcts sobre votos válidos por comuna.',
      n_comunas: Object.keys(comunas).length,
    },
    comunas,
  };
}

function fmtKB(b){ return (b/1024).toFixed(1) + ' KB'; }

function main(){
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const cities = fs.readdirSync(IN_DIR)
    .filter(f => fs.statSync(path.join(IN_DIR, f)).isDirectory())
    .filter(f => fs.existsSync(path.join(IN_DIR, f, 'historicos-comuna')));

  console.log(`[bloques-comunas] procesando ${cities.length} ciudades`);
  let total = 0;
  for (const city of cities){
    const out = processCity(city);
    if (!out){ console.log(`  ${city}: sin datos`); continue; }
    const fp = path.join(OUT_DIR, `${city}.json`);
    fs.writeFileSync(fp, JSON.stringify(out));
    const size = fs.statSync(fp).size;
    const nC = Object.keys(out.comunas).length;
    total += nC;
    // Sanity por ciudad: top de izq en 2022
    const arr = Object.values(out.comunas)
      .filter(c => c['2022'])
      .sort((a,b)=>b['2022'].izq - a['2022'].izq);
    const top = arr[0], bot = arr[arr.length-1];
    console.log(`  ${city.padEnd(14)} ${nC.toString().padStart(3)} comunas · ${fmtKB(size).padStart(8)} · ` +
      `izq22 top: ${(top.nombre||top.cod).slice(0,18).padEnd(18)} ${top['2022'].izq.toFixed(1)}% · ` +
      `bot: ${(bot.nombre||bot.cod).slice(0,18).padEnd(18)} ${bot['2022'].izq.toFixed(1)}%`);
  }
  console.log(`\n[bloques-comunas] ${total} comunas procesadas en ${cities.length} ciudades`);
}

main();
