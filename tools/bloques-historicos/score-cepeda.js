#!/usr/bin/env node
// tools/bloques-historicos/score-cepeda.js
//
// Computa el score "Modo Cepeda" por municipio para Veleta v2:
// muns donde más le sirve a Cepeda voltear votos para ganar la 1V (>50%).
//
// Inputs:
//   Bases de datos/output_bloques/por-mun.json       (Fase 1)
//   Bases de datos/output_bloques/nacional.json
//   Bases de datos/output_puestos_light/puestos-censos-agg.json
//   Bases de datos/output_ponderador/ponderador-actual.json
//
// Methodology:
//   1. Proyección Cepeda en cada mun = izq_2022_mun × (Cepeda_nac_2026 / izq_nac_2022)
//      (escala el voto Petro 2022 al nivel nacional Cepeda 2026)
//   2. Techo captable = proyCepeda + (c_2018_mun / 3)
//      (1/3 del voto Fajardo 2018 se reparte a Cepeda, según intuición ricardoruiz)
//   3. gap_to_50 = max(0, 50 - proyCepeda)
//   4. plausibleGain = min(captable, 10)
//   5. score = combinación de proximidad al 50% + plausibilidad del techo
//
// Uso:
//   node tools/bloques-historicos/score-cepeda.js

const fs = require('fs');
const path = require('path');

const BASE = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos';

const bloques  = JSON.parse(fs.readFileSync(`${BASE}/output_bloques/por-mun.json`, 'utf8'));
const nacional = JSON.parse(fs.readFileSync(`${BASE}/output_bloques/nacional.json`, 'utf8')).nacional;
const censos   = JSON.parse(fs.readFileSync(`${BASE}/output_puestos_light/puestos-censos-agg.json`, 'utf8'));
const pond     = JSON.parse(fs.readFileSync(`${BASE}/output_ponderador/ponderador-actual.json`, 'utf8'));

// ──── Baseline nacional 2026
const cepedaNac   = pond.candidatos['Cepeda'].pct;       // 38.67
const izqNac22    = nacional['2022'].izq;                // 41.05
const scaleIzq    = cepedaNac / izqNac22;                // ~0.942

console.log(`[score-cepeda] baseline nacional`);
console.log(`  Cepeda 2026 (ponderador) ${cepedaNac.toFixed(2)}%`);
console.log(`  izq 2022 (Petro 1V)      ${izqNac22.toFixed(2)}%`);
console.log(`  factor escala            ${scaleIzq.toFixed(3)}`);
console.log(``);

// ──── Carga GeoJSON de muns para resolver nombres? No tenemos catálogo aquí.
// Cargar índice de deptos para sacar nombres (best effort).
let depIndex = {};
try {
  const idx = JSON.parse(fs.readFileSync(`${BASE}/output_geo/dep-index.json`, 'utf8'));
  if (idx.departamentos){
    for (const d of idx.departamentos){
      depIndex[String(d.dep_electoral).padStart(2,'0')] = d.nombre;
    }
  }
} catch (e){ /* opcional */ }

// ──── Score por mun
const records = [];
for (const [key, m] of Object.entries(bloques)){
  const b22 = m['2022']; const b18 = m['2018']; const b14 = m['2014']; const b10 = m['2010'];
  if (!b22 || b22.vv < 100) continue;  // ignora muns con muy pocos votos

  const izq22 = b22.izq;
  const c18   = b18 ? b18.c : 0;
  const techoIzq = Math.max(
    b10 ? b10.izq : 0,
    b14 ? b14.izq : 0,
    b18 ? b18.izq : 0,
    izq22
  );

  // Proyección Cepeda 2026
  const proyCepeda  = izq22 * scaleIzq;
  // Techo captable: proyección + 1/3 voto centro 2018 (Fajardo)
  const captableRaw = proyCepeda + (c18 / 3);
  // Cap al techo histórico izq también escalado + tercio captable (sanity)
  const techoCap    = techoIzq * scaleIzq + (c18 / 3);
  const techoCepeda = Math.min(captableRaw, techoCap);

  const gapTo50      = Math.max(0, 50 - proyCepeda);
  const captable     = Math.max(0, techoCepeda - proyCepeda);
  const plausibleGain = Math.min(captable, 10);

  // Score
  let score;
  if (proyCepeda >= 50){
    score = 35;                                                  // ya ganado en 1V
  } else {
    const proximity    = Math.max(0, 1 - gapTo50 / 15);          // 1 si proyCepeda ≥ 35
    const plausibility = Math.min(1, plausibleGain / Math.max(gapTo50, 1));
    score = (proximity * 0.6 + plausibility * 0.4) * 100;
  }

  const censo = censos.porMun[key] || 0;

  records.push({
    key, depCod: m.depCod, munCod: m.munCod,
    censo,
    izq22: +izq22.toFixed(2),
    c18:   +c18.toFixed(2),
    techoIzq: +techoIzq.toFixed(2),
    proyCepeda: +proyCepeda.toFixed(2),
    techoCepeda: +techoCepeda.toFixed(2),
    gapTo50: +gapTo50.toFixed(2),
    plausibleGain: +plausibleGain.toFixed(2),
    score: +score.toFixed(1),
  });
}

// ──── Output: top 30 por score puro + top 30 por score × log(censo)
records.sort((a,b) => b.score - a.score);
const top30 = records.slice(0, 30);

console.log(`[score-cepeda] top 30 por score (sin ponderar censo)`);
console.log(`  ${'mun key'.padEnd(7)} ${'censo'.padStart(9)}  ${'izq22'.padStart(6)}  ${'c18'.padStart(5)}  ${'techo'.padStart(6)}  ${'proy'.padStart(6)}  ${'gap50'.padStart(6)}  ${'cap10'.padStart(6)}  ${'score'.padStart(6)}`);
for (const r of top30){
  console.log(`  ${r.key.padEnd(7)} ${r.censo.toString().padStart(9)}  ${r.izq22.toFixed(2).padStart(6)}  ${r.c18.toFixed(2).padStart(5)}  ${r.techoIzq.toFixed(2).padStart(6)}  ${r.proyCepeda.toFixed(2).padStart(6)}  ${r.gapTo50.toFixed(2).padStart(6)}  ${r.plausibleGain.toFixed(2).padStart(6)}  ${r.score.toFixed(1).padStart(6)}`);
}

// ──── Ranking ponderado por peso del mun
const logMaxCenso = Math.log(Math.max(...records.map(r=>r.censo || 1)));
for (const r of records){
  const w = r.censo > 0 ? Math.log(r.censo) / logMaxCenso : 0;
  r.scoreWeighted = +(r.score * w).toFixed(1);
}
records.sort((a,b) => b.scoreWeighted - a.scoreWeighted);

console.log(`\n[score-cepeda] top 30 por score ponderado log(censo)`);
console.log(`  ${'mun key'.padEnd(7)} ${'censo'.padStart(9)}  ${'izq22'.padStart(6)}  ${'proy'.padStart(6)}  ${'gap50'.padStart(6)}  ${'cap10'.padStart(6)}  ${'score'.padStart(6)}  ${'sc·w'.padStart(6)}`);
for (const r of records.slice(0,30)){
  console.log(`  ${r.key.padEnd(7)} ${r.censo.toString().padStart(9)}  ${r.izq22.toFixed(2).padStart(6)}  ${r.proyCepeda.toFixed(2).padStart(6)}  ${r.gapTo50.toFixed(2).padStart(6)}  ${r.plausibleGain.toFixed(2).padStart(6)}  ${r.score.toFixed(1).padStart(6)}  ${r.scoreWeighted.toFixed(1).padStart(6)}`);
}

// ──── Muns de control (ciudades conocidas)
// Códigos Registraduría/Senado (NO DANE): 01=Antioquia, 31=Valle, etc.
const CONTROL = {
  '16-001': 'Bogotá',
  '01-001': 'Medellín',
  '31-001': 'Cali',
  '03-001': 'Barranquilla',
  '05-001': 'Cartagena',
  '15-247': 'Soacha',
  '09-001': 'Manizales',
  '25-001': 'Cúcuta',
  '27-001': 'Bucaramanga',
  '13-001': 'Montería',
  '23-001': 'Pasto',
  '11-001': 'Popayán',
  '52-001': 'Villavicencio',
  '24-001': 'Pereira',
  '29-001': 'Ibagué',
  '12-001': 'Valledupar',
  '21-001': 'Santa Marta',
  '17-001': 'Quibdó',
};
console.log(`\n[score-cepeda] muns de control`);
console.log(`  ${'nombre'.padEnd(15)} ${'key'.padEnd(7)} ${'censo'.padStart(9)}  ${'izq22'.padStart(6)}  ${'c18'.padStart(6)}  ${'proy'.padStart(6)}  ${'techo'.padStart(6)}  ${'gap50'.padStart(6)}  ${'cap10'.padStart(6)}  ${'score'.padStart(6)}`);
for (const [k, name] of Object.entries(CONTROL)){
  const r = records.find(x => x.key === k);
  if (!r){ console.log(`  ${name.padEnd(15)} ${k.padEnd(7)} (no encontrado)`); continue; }
  console.log(`  ${name.padEnd(15)} ${r.key.padEnd(7)} ${r.censo.toString().padStart(9)}  ${r.izq22.toFixed(2).padStart(6)}  ${r.c18.toFixed(2).padStart(6)}  ${r.proyCepeda.toFixed(2).padStart(6)}  ${r.techoCepeda.toFixed(2).padStart(6)}  ${r.gapTo50.toFixed(2).padStart(6)}  ${r.plausibleGain.toFixed(2).padStart(6)}  ${r.score.toFixed(1).padStart(6)}`);
}

// ──── Stats overall
console.log(`\n[score-cepeda] distribución de score`);
const buckets = [0,20,40,60,80,100];
for (let i=0;i<buckets.length-1;i++){
  const lo = buckets[i], hi = buckets[i+1];
  const n = records.filter(r => r.score >= lo && r.score < hi).length;
  console.log(`  [${lo}-${hi})  ${n.toString().padStart(4)} muns`);
}
const n100 = records.filter(r => r.score === 100).length;
console.log(`  exactly 100  ${n100} muns`);
console.log(`  total       ${records.length}`);
