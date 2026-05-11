#!/usr/bin/env node
// tools/build-mde-por-barrio.js
//
// Agrega los por-puesto.json de las 14 señales históricas de Medellín a
// nivel de barrio, cruzando con PUESTOS_GEOREF.csv (puesto → barrio). El
// output reemplaza la herencia comuna→barrio de oportunidad.html v1 con
// bias propio por barrio (paquete v2 del módulo Oportunidad).
//
// Uso:
//   node tools/build-mde-por-barrio.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/PUESTOS_GEOREF.csv" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_medellin/por-barrio" \
//     [--alias tools/build-mde-por-barrio.alias.json]
//
// Output: un JSON por señal + _diagnostico.json con barrios que no
// matchean al GeoJSON oficial (lista de alias por curar).
//
// Streaming-friendly por-puesto.json se descargan completos a /tmp para
// reusar entre corridas. Toma ~10s la primera vez, <1s las siguientes.

const fs = require('fs');
const path = require('path');
const https = require('https');

// ── Config ────────────────────────────────────────────────────────────
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com';
const HIST_NAC = `${S3}/ricardoruiz.co/congreso-2026/output/historicos`;
const MDE_LOCAL = `${S3}/ricardoruiz.co/bases+de+datos/output_medellin`;
const CONG_DEP = `${S3}/ricardoruiz.co/congreso-2026/output`;
const GEO_BARRIOS = `${S3}/ricardoruiz.co/bases+de+datos/proyecto-dc/geo/barrios-veredas-medellin.json`;

// Mismas señales que MED_SIGNALS de previa-1v.html, pero apuntando a
// por-puesto.json en vez de por-comuna.json. Cada entrada describe cómo
// leer el JSON (format + identifica los puestos de Medellín).
//
// format:
//   'mde-local'   → key='ZZ-PP', value.{votos_validos, candidatos:[{cod,nombre,partido,votos}]}
//   'nac-pres'    → key='DD-MMM-ZZ-PP', value.{vv, v:{codCan:votos}}; candidatos:{codCan:{nombre,...}}
//   'nac-consulta'→ key='DD-MMM-ZZ-PP', value.{vv, v:{nombre:votos}}; candidatos por nombre
//   'cong-2026'   → array[{dep_cod,mun_cod,zon_cod,pue_cod_raw,votval,partidos:{nombre:votos}}]
const SIGNALS = {
  'pres-2010-mde':              { url: `${HIST_NAC}/pres-2010-v1/por-puesto.json`,         format:'nac-pres',     type:'cands'    },
  'pres-2014-mde':              { url: `${HIST_NAC}/pres-2014-v1/por-puesto.json`,         format:'nac-pres',     type:'cands'    },
  'pres-2018-mde':              { url: `${HIST_NAC}/pres-2018-v1/por-puesto.json`,         format:'nac-pres',     type:'cands'    },
  'pres-2022-mde':              { url: `${HIST_NAC}/pres-2022-v1/por-puesto.json`,         format:'nac-pres',     type:'cands'    },
  'consulta-2025-pacto-mde':    { url: `${HIST_NAC}/consulta-2025-pacto/por-puesto.json`,  format:'nac-consulta', type:'cands'    },
  'consulta-2026-gran-mde':     { url: `${HIST_NAC}/consulta-2026-gran/por-puesto.json`,   format:'nac-consulta', type:'cands'    },
  'consulta-2026-frente-mde':   { url: `${HIST_NAC}/consulta-2026-frente/por-puesto.json`, format:'nac-consulta', type:'cands'    },
  'consulta-2026-soluciones-mde':{url: `${HIST_NAC}/consulta-2026-soluciones/por-puesto.json`,format:'nac-consulta',type:'cands' },
  'alc-2015-mde':               { url: `${MDE_LOCAL}/2015/alcaldia/por-puesto.json`,        format:'mde-local',    type:'cands'    },
  'concejo-2015-mde':           { url: `${MDE_LOCAL}/2015/concejo/por-puesto.json`,         format:'mde-local',    type:'partidos' },
  'alc-2019-mde':               { url: `${MDE_LOCAL}/2019/alcaldia/por-puesto.json`,        format:'mde-local',    type:'cands'    },
  'concejo-2019-mde':           { url: `${MDE_LOCAL}/2019/concejo/por-puesto.json`,         format:'mde-local',    type:'partidos' },
  'alc-2023-mde':               { url: `${MDE_LOCAL}/2023/alcaldia/por-puesto.json`,        format:'mde-local',    type:'cands'    },
  'concejo-2023-mde':           { url: `${MDE_LOCAL}/2023/concejo/por-puesto.json`,         format:'mde-local',    type:'partidos' },
  'senado-2026-mde':            { url: `${CONG_DEP}/senado/departamentos/01/puestos.json`,  format:'cong-2026',    type:'partidos' },
  'camara-2026-mde':            { url: `${CONG_DEP}/camara/departamentos/01/puestos.json`,  format:'cong-2026',    type:'partidos' },
};

// Filtros para señales nacionales y congreso. Para nacionales (DANE),
// Medellín = 05-001. Para senado/cámara 2026 (electoral), Medellín = 01-001.
const PFX_NAC = '05-001-';
const ELEC_DEP = '01', ELEC_MUN = '001';

// ── Helpers ───────────────────────────────────────────────────────────
const pad2 = (s) => String(parseInt(s,10)||0).padStart(2,'0');
const pad3 = (s) => String(parseInt(s,10)||0).padStart(3,'0');

// Normaliza nombre de barrio para usar como clave de match.
// uppercase, sin tildes, "No 2" → "NO 2", "#2" → "NO 2", colapsa espacios.
function normBarrio(s){
  if(!s) return '';
  let t = String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase();
  t = t.replace(/[#°ºª]/g,' NO ');
  t = t.replace(/\bNO\.?\b/g,'NO');           // "No." / "N°" / "No" → "NO"
  t = t.replace(/[^A-Z0-9 ]+/g,' ');          // quita puntuación restante
  t = t.replace(/\s+/g,' ').trim();
  // Colapsa "NO 1" / "NO 2" / "NO 3" → "NO1" para que "AURES NO 1" y
  // "AURES NO1" (GeoJSON) matcheen igual. Aplicado al final para que
  // funcione sobre cualquier orden de transformación previa.
  t = t.replace(/\bNO (\d+)\b/g,'NO$1');
  return t;
}

function fetchCached(url){
  const fname = '/tmp/mde-pb-' + url.replace(/[^a-zA-Z0-9]+/g,'_') + '.json';
  if(fs.existsSync(fname) && fs.statSync(fname).size > 100){
    return Promise.resolve(JSON.parse(fs.readFileSync(fname,'utf8')));
  }
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if(res.statusCode !== 200){ reject(new Error(`HTTP ${res.statusCode} on ${url}`)); return; }
      const chunks=[]; res.on('data',c=>chunks.push(c));
      res.on('end',()=>{
        const buf = Buffer.concat(chunks).toString('utf8');
        fs.writeFileSync(fname, buf);
        try { resolve(JSON.parse(buf)); } catch(e){ reject(e); }
      });
    }).on('error', reject);
  });
}

// ── 1) PUESTOS_GEOREF.csv → puesto_lookup ─────────────────────────────
// puesto_lookup: { 'ZZ-PP': { barrioRaw, barrioNorm, comuna } }
function loadPuestoLookup(csvPath){
  const raw = fs.readFileSync(csvPath, 'utf8');
  const lines = raw.split(/\r?\n/);
  const header = lines[0].replace(/^﻿/,'').split(';');
  const idx = (name) => header.findIndex(h => h.trim().toUpperCase() === name.toUpperCase());
  const iDep = idx('DEPARTAMENTO'), iMun = idx('MUNICIPIO');
  const iZon = idx('ZONA'),         iPue = idx('PUESTO');
  const iBar = idx('BARRIO'),       iComCod = idx('CÓDIGO COMUNA');
  if([iDep,iMun,iZon,iPue,iBar,iComCod].some(x=>x<0)){
    throw new Error('Columnas faltantes en PUESTOS_GEOREF. Encontradas: '+header.join('|'));
  }
  const lookup = {};
  let nMde = 0, nNoBarrio = 0;
  for(let i=1;i<lines.length;i++){
    const ln = lines[i]; if(!ln) continue;
    const c = ln.split(';');
    const dep = (c[iDep]||'').toUpperCase();
    const mun = (c[iMun]||'').toUpperCase();
    if(!dep.includes('ANTIOQUIA') || !mun.includes('MEDELL')) continue;
    nMde++;
    const zz = pad2(c[iZon]);
    const pp = pad2(c[iPue]);
    const key = `${zz}-${pp}`;
    const barrioRaw = (c[iBar]||'').trim();
    const comuna = pad2(c[iComCod]);
    if(!barrioRaw) nNoBarrio++;
    lookup[key] = { barrioRaw, barrioNorm: normBarrio(barrioRaw), comuna };
  }
  console.log(`[geo] PUESTOS_GEOREF: ${nMde} puestos de Medellín, ${nNoBarrio} sin BARRIO`);
  return lookup;
}

// ── 2) Por cada señal: leer JSON, agregar por barrio ──────────────────
function iterPuestos(json, format){
  // → genera [{ zzpp, vv, votos: { displayKey: votos } }]
  const out = [];
  if(format === 'mde-local'){
    for(const [k, v] of Object.entries(json)){
      const [zz, pp] = k.split('-');
      if(zz==='99' || zz==='98' || zz==='90' || pp==='00') {
        // 99/98/90 con pp=00 son agregados — skip
        if(pp==='00') continue;
      }
      const votos = {};
      for(const c of (v.candidatos||[])){
        if(!c || !c.nombre) continue;
        votos[c.nombre] = (votos[c.nombre]||0) + (c.votos||0);
      }
      out.push({ zzpp:`${pad2(zz)}-${pad2(pp)}`, vv: v.votos_validos||0, votos });
    }
  } else if(format === 'nac-pres'){
    const cands = json.candidatos || {};
    for(const [k, v] of Object.entries(json.puestos || {})){
      if(!k.startsWith(PFX_NAC)) continue;
      const parts = k.split('-');           // ['05','001','ZZ','PP']
      const zzpp = `${pad2(parts[2])}-${pad2(parts[3])}`;
      const votos = {};
      for(const [cod, n] of Object.entries(v.v||{})){
        const nombre = cands[cod] && cands[cod].nombre;
        if(!nombre) continue;
        votos[nombre] = (votos[nombre]||0) + (n||0);
      }
      out.push({ zzpp, vv: v.vv||0, votos });
    }
  } else if(format === 'nac-consulta'){
    for(const [k, v] of Object.entries(json.puestos || {})){
      if(!k.startsWith(PFX_NAC)) continue;
      const parts = k.split('-');
      const zzpp = `${pad2(parts[2])}-${pad2(parts[3])}`;
      const votos = {};
      for(const [nombre, n] of Object.entries(v.v||{})){
        votos[nombre] = (votos[nombre]||0) + (n||0);
      }
      out.push({ zzpp, vv: v.vv||0, votos });
    }
  } else if(format === 'cong-2026'){
    for(const p of (json||[])){
      if(p.dep_cod !== ELEC_DEP || p.mun_cod !== ELEC_MUN) continue;
      const zzpp = `${pad2(p.zon_cod)}-${pad2(p.pue_cod_raw)}`;
      const votos = {};
      for(const [k, n] of Object.entries(p.partidos||{})){
        if(/^99[6-9]$/.test(k)) continue; // 996/997/998 = blanco/nulos/no_marcados
        votos[k] = (votos[k]||0) + (n||0);
      }
      out.push({ zzpp, vv: p.votval||0, votos });
    }
  } else {
    throw new Error('Format desconocido: '+format);
  }
  return out;
}

function aggregateSignal(puestos, lookup){
  // → { barriosMap: { barrioNorm: {nombre, comuna, votos_validos, votos:{}} },
  //     diag: { puestosTotal, puestosSinLookup, puestosSinBarrio } }
  const barrios = {};
  let total=0, sinLookup=0, sinBarrio=0;
  for(const e of puestos){
    total++;
    const h = lookup[e.zzpp];
    if(!h){ sinLookup++; continue; }
    if(!h.barrioNorm){ sinBarrio++; continue; }
    let b = barrios[h.barrioNorm];
    if(!b){ b = barrios[h.barrioNorm] = { nombre: h.barrioRaw, comuna: h.comuna, votos_validos:0, votos:{} }; }
    b.votos_validos += e.vv;
    for(const [k,n] of Object.entries(e.votos)){
      b.votos[k] = (b.votos[k]||0) + n;
    }
  }
  return { barrios, diag:{ puestosTotal: total, puestosSinLookup: sinLookup, puestosSinBarrio: sinBarrio } };
}

function shapeSignalOutput(agg, sig){
  const cfg = SIGNALS[sig];
  const barriosOut = {};
  for(const [norm, b] of Object.entries(agg.barrios)){
    const entries = Object.entries(b.votos)
      .map(([nombre, votos]) => ({ nombre, votos, pct: b.votos_validos>0 ? +(100*votos/b.votos_validos).toFixed(3) : 0 }))
      .sort((a,b)=>b.votos-a.votos);
    barriosOut[norm] = {
      nombre: b.nombre,
      comuna: b.comuna,
      votos_validos: b.votos_validos,
      [cfg.type === 'partidos' ? 'partidos' : 'cands']: entries,
    };
  }
  return {
    fuente: sig,
    type: cfg.type,
    n_barrios: Object.keys(barriosOut).length,
    puestos_total: agg.diag.puestosTotal,
    puestos_sin_lookup: agg.diag.puestosSinLookup,
    puestos_sin_barrio: agg.diag.puestosSinBarrio,
    generado_en: new Date().toISOString(),
    barrios: barriosOut,
  };
}

// ── 3) Diagnóstico: barrios del CSV que NO existen en el GeoJSON ──────
async function buildGeoDiag(allBarriosNorm){
  const geo = await fetchCached(GEO_BARRIOS);
  // Construye índice del GeoJSON por nombre normalizado
  const geoNorm = new Map();
  for(const f of geo.features){
    const nombreBar = f.properties.nombre_bar || '';
    const norm = normBarrio(nombreBar);
    if(norm) geoNorm.set(norm, { nombre: nombreBar, comuna: f.properties.comuna, codigo: f.properties.codigo });
  }
  // Set de barrios CSV
  const csvNorms = [...new Set(allBarriosNorm)].sort();
  const matched = [];
  const unmatched = [];
  for(const n of csvNorms){
    if(geoNorm.has(n)) matched.push(n);
    else unmatched.push(n);
  }
  // GeoJSON barrios sin datos del CSV (probablemente nombres que el CSV no usa)
  const geoNorms = [...geoNorm.keys()].sort();
  const geoSinCsv = geoNorms.filter(n => !csvNorms.includes(n));
  return {
    csv_total: csvNorms.length,
    geo_total: geoNorms.length,
    matched: matched.length,
    unmatched_csv: unmatched,         // barrios CSV que no aparecen en GeoJSON
    geo_sin_csv: geoSinCsv,           // features GeoJSON que el CSV no nombra igual
    geo_index: Object.fromEntries([...geoNorm.entries()]),
  };
}

// ── 4) Main ───────────────────────────────────────────────────────────
async function main(){
  const argv = process.argv.slice(2);
  if(argv.length < 2){
    console.error('Uso: node build-mde-por-barrio.js <PUESTOS_GEOREF.csv> <out-dir> [--alias <path>]');
    process.exit(1);
  }
  const csvPath = argv[0];
  const outDir = argv[1];
  let aliasIdx = argv.indexOf('--alias');
  const aliasPath = aliasIdx > 0 ? argv[aliasIdx+1] : null;
  const aliasMap = aliasPath && fs.existsSync(aliasPath) ? JSON.parse(fs.readFileSync(aliasPath,'utf8')) : {};
  if(aliasPath) console.log(`[alias] ${Object.keys(aliasMap).length} entradas desde ${aliasPath}`);

  fs.mkdirSync(outDir, { recursive: true });
  const lookup = loadPuestoLookup(csvPath);

  // Aplica alias: barrioNorm del CSV → nombre canónico del GeoJSON
  // (sustituye barrioNorm para que el join con el GeoJSON cuadre).
  if(aliasMap && Object.keys(aliasMap).length){
    for(const k of Object.keys(lookup)){
      const cur = lookup[k].barrioNorm;
      if(aliasMap[cur]){
        lookup[k].barrioNorm = normBarrio(aliasMap[cur]);
      }
    }
  }

  const allBarriosNorm = [];
  for(const v of Object.values(lookup)){
    if(v.barrioNorm) allBarriosNorm.push(v.barrioNorm);
  }

  // Procesa cada señal en paralelo (descargas son lentas, agregación es ms)
  const signals = Object.keys(SIGNALS);
  console.log(`[run] procesando ${signals.length} señales…`);
  const results = await Promise.all(signals.map(async sig => {
    const cfg = SIGNALS[sig];
    let j;
    try { j = await fetchCached(cfg.url); }
    catch(e){ console.error(`[err] ${sig}: ${e.message}`); return { sig, ok:false }; }
    const puestos = iterPuestos(j, cfg.format);
    const agg = aggregateSignal(puestos, lookup);
    const out = shapeSignalOutput(agg, sig);
    const fp = path.join(outDir, `${sig}.json`);
    fs.writeFileSync(fp, JSON.stringify(out));
    console.log(`  ✓ ${sig.padEnd(34)} ${String(out.n_barrios).padStart(3)} barrios · ${String(out.puestos_total).padStart(4)} puestos · ${out.puestos_sin_lookup} sin lookup`);
    return { sig, ok:true, n_barrios: out.n_barrios };
  }));

  // Diagnóstico geo
  const diag = await buildGeoDiag(allBarriosNorm);
  fs.writeFileSync(path.join(outDir, '_diagnostico.json'), JSON.stringify({
    generado_en: new Date().toISOString(),
    csv_total_barrios: diag.csv_total,
    geo_total_features: diag.geo_total,
    matched: diag.matched,
    unmatched_csv: diag.unmatched_csv,
    geo_sin_csv: diag.geo_sin_csv,
    nota: 'unmatched_csv = barrios del CSV que NO matchean al GeoJSON. Curar el alias.json con: { "NOMBRE CSV NORMALIZADO": "Nombre Canónico GeoJSON" }',
  }, null, 2));
  console.log(`\n[diag] CSV: ${diag.csv_total} · GeoJSON: ${diag.geo_total} · match: ${diag.matched} (${(100*diag.matched/diag.csv_total).toFixed(0)}%) · unmatched: ${diag.unmatched_csv.length}`);
  console.log(`[out]  ${outDir}/`);
}

main().catch(e => { console.error(e); process.exit(1); });
