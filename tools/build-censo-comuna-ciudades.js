#!/usr/bin/env node
// tools/build-censo-comuna-ciudades.js
//
// Agrega el censo electoral por comuna política para las 14 ciudades del
// módulo Oportunidad. Cruza puesto-level censo (COMUNAS_DATA.csv) con el
// código de comuna que viene en el mismo CSV (campo `comuna`).
//
// Uso:
//   node tools/build-censo-comuna-ciudades.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/COMUNAS_DATA.csv" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_ciudades"
//
// Output: 14 archivos `<out-dir>/<city>/censo-comuna.json` con shape:
//   { por_comuna: { "01": { comCod, nombre, censo, mujeres, hombres, n_puestos } }, ciudad_total: N }
//
// Luego subir a S3 bajo bases+de+datos/output_ciudades/<city>/.

const fs = require('fs');
const path = require('path');

// Misma lista de CITIES que oportunidad.html. Code/mun electoral.
const CITIES = {
  medellin:      { depCod:'01', munCod:'001' },
  bogota:        { depCod:'16', munCod:'001' },
  cali:          { depCod:'31', munCod:'001' },
  barranquilla:  { depCod:'03', munCod:'001' },
  ibague:        { depCod:'29', munCod:'001' },
  manizales:     { depCod:'09', munCod:'001' },
  pereira:       { depCod:'24', munCod:'001' },
  monteria:      { depCod:'13', munCod:'001' },
  bucaramanga:   { depCod:'27', munCod:'001' },
  cucuta:        { depCod:'25', munCod:'001' },
  neiva:         { depCod:'19', munCod:'001' },
  popayan:       { depCod:'11', munCod:'001' },
  sincelejo:     { depCod:'28', munCod:'001' },
  villavicencio: { depCod:'52', munCod:'001' },
};

function pad2(s){ return String(s||'').padStart(2,'0'); }
function pad3(s){ return String(s||'').padStart(3,'0'); }

// El campo `comuna` viene como "01COMUNA 1 POPULAR" o "01LOCALIDAD 1 USAQUEN"
// o "06COMUNA  6 CENTRO" (con doble espacio). Extrae el código 2-char y el
// nombre normalizado (espacios colapsados, sin prefijo redundante).
function parseComuna(raw){
  if (!raw) return null;
  const m = String(raw).match(/^\s*(\d{2})\s*(.*)$/);
  if (!m) return null;
  const cod = m[1];
  let nombre = m[2].trim().replace(/\s+/g,' ');
  return { cod, nombre };
}

function main(){
  const [csvPath, outDir] = process.argv.slice(2);
  if (!csvPath || !outDir){
    console.error('Uso: node build-censo-comuna-ciudades.js <COMUNAS_DATA.csv> <out-dir>');
    process.exit(1);
  }
  const raw = fs.readFileSync(csvPath,'utf8');
  const lines = raw.split(/\r?\n/);
  const header = lines[0].replace(/^﻿/,'').split(';');
  const idx = (name) => header.findIndex(h => h.trim().toLowerCase() === name.toLowerCase());
  const iDd = idx('dd'), iMm = idx('mm'), iComuna = idx('comuna'),
        iMuj = idx('mujeres'), iHom = idx('hombres'), iTot = idx('total');
  if ([iDd,iMm,iComuna,iTot].some(x => x < 0)){
    throw new Error('Faltan columnas. Header: '+header.join('|'));
  }

  // city -> comCod -> { nombre, censo, mujeres, hombres, n_puestos }
  const result = {};
  for (const k of Object.keys(CITIES)){
    result[k] = { city: CITIES[k], byCom: {}, ciudad_total: 0 };
  }

  for (let i=1;i<lines.length;i++){
    const ln = lines[i]; if (!ln) continue;
    const c = ln.split(';');
    const dd = pad2(c[iDd]), mm = pad3(c[iMm]);
    // ¿es alguna de las 14 ciudades?
    const cityKey = Object.keys(CITIES).find(k => CITIES[k].depCod === dd && CITIES[k].munCod === mm);
    if (!cityKey) continue;
    const parsed = parseComuna(c[iComuna]);
    if (!parsed) continue;
    const muj = parseInt(c[iMuj]||0,10) || 0;
    const hom = parseInt(c[iHom]||0,10) || 0;
    const tot = parseInt(c[iTot]||0,10) || 0;
    if (tot <= 0) continue;

    const bucket = result[cityKey].byCom;
    if (!bucket[parsed.cod]){
      bucket[parsed.cod] = { comCod: parsed.cod, nombre: parsed.nombre, censo: 0, mujeres: 0, hombres: 0, n_puestos: 0 };
    }
    const b = bucket[parsed.cod];
    b.censo += tot;
    b.mujeres += muj;
    b.hombres += hom;
    b.n_puestos += 1;
    result[cityKey].ciudad_total += tot;
  }

  fs.mkdirSync(outDir, { recursive: true });
  for (const [cityKey, r] of Object.entries(result)){
    const cods = Object.keys(r.byCom).sort();
    if (!cods.length){
      console.warn(`[skip] ${cityKey} sin filas en COMUNAS_DATA — ¿códigos correctos?`);
      continue;
    }
    const cityDir = path.join(outDir, cityKey);
    fs.mkdirSync(cityDir, { recursive: true });
    const out = {
      city: cityKey,
      depCod: r.city.depCod,
      munCod: r.city.munCod,
      ciudad_total: r.ciudad_total,
      n_comunas: cods.length,
      generado_en: new Date().toISOString(),
      por_comuna: r.byCom,
    };
    const fp = path.join(cityDir, 'censo-comuna.json');
    fs.writeFileSync(fp, JSON.stringify(out));
    console.log(`✓ ${cityKey.padEnd(14)} ${String(cods.length).padStart(3)} comunas · censo total ${r.ciudad_total.toLocaleString('es-CO')}`);
  }
}

main();
