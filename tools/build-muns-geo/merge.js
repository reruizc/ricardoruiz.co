#!/usr/bin/env node
// merge — fusiona los 33 GeoJSON de municipios (Departamentos-mps/{cod}.json) en un
// solo archivo nacional minimizado (solo dep_electoral + mun_elec + mpio_cnmbr +
// geometry), para la vista "todos los municipios" del mapa. Se hace UNA vez.
//
// Uso:   node tools/build-muns-geo/merge.js
// Salida: Bases de datos/output_swing/muns-nacional.geojson
// Subir:  aws s3 cp "Bases de datos/output_swing/muns-nacional.geojson" \
//           "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/mapas-2026/MUNICIPIOS-NACIONAL.json" \
//           --content-type application/json --content-encoding gzip ... (ver abajo)

const fs = require('fs');
const path = require('path');

const BASE = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Departamentos-mps/';
const CODES = ['60','01','40','56','03','16','05','07','09','44','46','11','12','17','13','15','50','54','19','48','21','52','23','25','64','24','26','27','28','29','31','68','72'];
const OUT = path.join(__dirname, '..', '..', 'Bases de datos', 'output_swing', 'muns-nacional.geojson');

const round = (n) => Math.round(n * 1e4) / 1e4;   // 4 decimales (~11 m) — reduce tamaño sin romper polígonos
function thinCoords(c){ return (typeof c[0] === 'number') ? [round(c[0]), round(c[1])] : c.map(thinCoords); }

async function getJSON(url, tries = 3){
  for (let t = 0; t < tries; t++){
    try { const r = await fetch(url, { headers:{ 'User-Agent':'node' } }); if (!r.ok) throw new Error('HTTP '+r.status); return await r.json(); }
    catch(e){ if (t === tries-1) throw e; await new Promise(x=>setTimeout(x, 400)); }
  }
}

(async () => {
  const feats = [];
  for (const cod of CODES){
    try {
      const g = await getJSON(BASE + cod + '.json');
      for (const f of (g.features||[])){
        const p = f.properties || {};
        feats.push({ type:'Feature',
          properties: { d: p.dep_electoral || cod, m: p.mun_elec || p.mun_electoral || '', n: p.mpio_cnmbr || '' },
          geometry: f.geometry ? { type:f.geometry.type, coordinates: thinCoords(f.geometry.coordinates) } : null });
      }
      console.log('  ', cod, (g.features||[]).length, 'muns');
    } catch(e){ console.log('  ', cod, 'FAIL', e.message); }
  }
  const out = { type:'FeatureCollection', features: feats };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out));
  const kb = Math.round(fs.statSync(OUT).size/1024);
  console.log(`\n✓ ${feats.length} municipios → ${OUT} (${kb} KB)`);
})();
