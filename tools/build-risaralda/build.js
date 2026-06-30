#!/usr/bin/env node
// tools/build-risaralda/build.js
//
// Procesa un GCS Territorial (2019/2023) y genera los JSON de Risaralda
// (COD_DDE=24, 14 municipios) para las 4 corporaciones: Gobernación,
// Asamblea, Alcaldía y Concejo. Enfoque "alternativo" (Verde + Pacto +
// izquierda histórica) calculado por municipio para el heatmap.
//
// Uso:
//   node tools/build-risaralda/build.js <archivo.csv> <year>
//   node tools/build-risaralda/build.js "Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv" 2023
//
// Salidas en Bases de datos/output_risaralda/:
//   risaralda-<year>.json            principal (depto + por-municipio, 4 corps)
//   risaralda-<year>-puestos.json    drill por puesto (zz-pp) × corp × mun
//   risaralda-<year>-pereira-barrios.json  Pereira por barrio (PIP)
//   risaralda-<year>-clasificacion.csv     reporte de partidos alt/no-alt
//
// Streaming, sin dependencias externas.

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { esAlternativo, norm } = require('./clasificador.js');

// ─── CONFIG ───────────────────────────────────────────────────────────
const ROOT = '/Users/ricardoruiz/ricardoruiz.co';
const DEP = 24;                          // Risaralda (estable 2019↔2023)
const DEP_NOMBRE = 'RISARALDA';
const GEOREF = path.join(ROOT, 'Bases de datos/PUESTOS_GEOREF.csv');
const PEREIRA_BARRIOS_GEO = path.join(ROOT, 'Bases de datos/output_pacto_1v_2026/geo/PEREIRA-BARRIOS.json');
const OUT_DIR = path.join(ROOT, 'Bases de datos/output_risaralda');
const PEREIRA_MUN = 1;

const MUNS = {
  1:'PEREIRA', 8:'APIA', 13:'BALBOA', 21:'BELEN DE UMBRIA', 25:'DOSQUEBRADAS',
  29:'GUATICA', 38:'LA CELIA', 46:'LA VIRGINIA', 54:'MARSELLA', 62:'MISTRATO',
  70:'PUEBLO RICO', 78:'QUINCHIA', 86:'SANTA ROSA DE CABAL', 94:'SANTUARIO',
};

const SPECIAL_CODES = { '996':'blanco', '997':'nulos', '998':'no_marcados', '999':'no_marcados' };

// Nombre de corporación (DES_COR varía por año).
const COR_DES_TO_NAME = {
  'GOBERNADOR':'gobernacion', 'GOBERNACION':'gobernacion',
  'ASAMBLEA':'asamblea',
  'ALCALDE':'alcaldia', 'ALCALDIA':'alcaldia',
  'CONCEJO':'concejo',
};

// Asamblea de Risaralda: 12 diputados (estable). Concejos por municipio
// (Ley 136/1994 + 2200/2022 por población · APROXIMADO, revisar). Sólo
// afectan D'Hondt de curules; la métrica del heatmap es por voto.
const CURULES_ASAMBLEA = 12;
const CURULES_CONCEJO = {
  1:19, 25:19, 86:15, 46:13, 21:13, 78:15, 8:11, 13:11, 29:13, 38:11,
  54:13, 62:13, 70:13, 94:11,
};

// ─── HELPERS ──────────────────────────────────────────────────────────
function unquote(s){
  let v = String(s == null ? '' : s).trim();
  if (v.length >= 2 && v[0] === '"' && v[v.length-1] === '"') v = v.slice(1,-1).replace(/""/g,'"');
  return v;
}
function pad2(v){ return String(parseInt(v||'0',10)).padStart(2,'0'); }
function pad3(v){ return String(parseInt(v||'0',10)).padStart(3,'0'); }

function dhondt(parties, seats){
  const arr = parties.map(p => ({ ...p, curules:0 }));
  for (let i=0;i<seats;i++){
    let bi=-1, bq=-1;
    for (let j=0;j<arr.length;j++){ const q=arr[j].votos/(arr[j].curules+1); if(q>bq){bq=q;bi=j;} }
    if (bi>=0) arr[bi].curules++;
  }
  return arr;
}

// scope acumula candidatos (keyed COD_PAR|COD_CAN) + especiales.
function emptyScope(){ return { cands:new Map(), especiales:{} }; }
function ensure(map, key){ let s=map.get(key); if(!s){s=emptyScope();map.set(key,s);} return s; }
function accum(scope, key, cod, nombre, partido, alt, votos){
  const sp = SPECIAL_CODES[cod];
  if (sp){ scope.especiales[sp]=(scope.especiales[sp]||0)+votos; return; }
  let c = scope.cands.get(key);
  if (!c){ c={ nombre, partido, alt, votos:0 }; scope.cands.set(key,c); }
  c.votos += votos;
  if (!c.nombre && nombre) c.nombre = nombre;
}

// Serializa un scope. mode: 'cand' (alcaldía/gobernación, candidatos) o
// 'lista' (asamblea/concejo, agrega por partido + D'Hondt).
function serialize(scope, { mode='cand', curules=0, topN=0 } = {}){
  let validos = 0, altVotos = 0;
  const cands = [];
  for (const c of scope.cands.values()){
    validos += c.votos;
    if (c.alt) altVotos += c.votos;
    cands.push({ nombre:c.nombre, partido:c.partido, votos:c.votos, alt:!!c.alt });
  }
  cands.sort((a,b)=>b.votos-a.votos);
  for (const c of cands) c.pct = validos>0 ? +(c.votos/validos*100).toFixed(2) : 0;

  // Agregado por partido/lista
  const aggP = new Map();
  for (const c of cands){
    const p = c.partido || '(SIN PARTIDO)';
    let e = aggP.get(p); if(!e){ e={partido:p, votos:0, alt:c.alt}; aggP.set(p,e);} e.votos += c.votos;
  }
  let partidos = Array.from(aggP.values()).sort((a,b)=>b.votos-a.votos)
    .map(p=>({ ...p, pct: validos>0 ? +(p.votos/validos*100).toFixed(2):0 }));

  let curulesArr = null, altCurules = 0;
  if (curules>0){
    curulesArr = dhondt(partidos.map(p=>({partido:p.partido,votos:p.votos,alt:p.alt})), curules)
      .filter(p=>p.curules>0).sort((a,b)=>b.curules-a.curules||b.votos-a.votos);
    altCurules = curulesArr.filter(p=>p.alt).reduce((s,p)=>s+p.curules,0);
  }

  const esp = Object.values(scope.especiales).reduce((a,b)=>a+b,0);
  const out = {
    validos,
    votantes: validos + esp,            // sufragantes = válidos + blanco/nulos/no_marcados
    alt_votos: altVotos,
    alt_pct: validos>0 ? +(altVotos/validos*100).toFixed(2) : 0,
    especiales: scope.especiales,
  };
  // Líder: por lista en asamblea/concejo, por candidato en alcaldía/gobernación.
  if (mode === 'lista'){
    out.lider = partidos[0] ? { partido:partidos[0].partido, votos:partidos[0].votos, pct:partidos[0].pct, alt:!!partidos[0].alt } : null;
    if (curulesArr){ out.curules = curulesArr; out.alt_curules = altCurules; }
  } else {
    const top = cands[0];
    out.lider = top ? { nombre:top.nombre, partido:top.partido, votos:top.votos, pct:top.pct, alt:!!top.alt } : null;
  }
  // SIEMPRE incluimos listas + candidatos completos (con votos) para el
  // detalle scrollable "ver cada candidato". Cap defensivo de 400.
  out.partidos = partidos;
  out.candidatos = cands.slice(0, 400);
  return out;
}

// ─── PIP (ray casting) para Pereira por barrio ────────────────────────
function pointInRing(x, y, ring){
  let inside = false;
  for (let i=0, j=ring.length-1; i<ring.length; j=i++){
    const xi=ring[i][0], yi=ring[i][1], xj=ring[j][0], yj=ring[j][1];
    const hit = ((yi>y)!==(yj>y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi);
    if (hit) inside = !inside;
  }
  return inside;
}
function pointInPolygon(x, y, poly){
  // poly = array de rings; [0]=outer, resto=holes
  if (!pointInRing(x,y,poly[0])) return false;
  for (let k=1;k<poly.length;k++){ if (pointInRing(x,y,poly[k])) return false; }
  return true;
}
function loadPereiraBarrios(){
  if (!fs.existsSync(PEREIRA_BARRIOS_GEO)){
    console.warn('  ! PEREIRA-BARRIOS.json no encontrado — sin nivel barrio');
    return null;
  }
  const gj = JSON.parse(fs.readFileSync(PEREIRA_BARRIOS_GEO,'utf8'));
  const feats = (gj.features||[]).map((f,i)=>{
    const props = f.props || f.properties || {};
    const nombre = props.NOMBRE || props.nombre || props.BARRIO || props.barrio || `Barrio ${i}`;
    const g = f.geometry || {};
    let polys = [];
    if (g.type==='Polygon') polys=[g.coordinates];
    else if (g.type==='MultiPolygon') polys=g.coordinates;
    return { id:String(i), nombre:String(nombre).toUpperCase().trim(), polys };
  });
  console.log(`  · PEREIRA-BARRIOS: ${feats.length} polígonos`);
  return feats;
}
function findBarrio(lat, lon, feats){
  for (const f of feats){
    for (const poly of f.polys){ if (pointInPolygon(lon, lat, poly)) return f; }
  }
  return null;
}

// ─── GEOREF: mun-zz-pp → {lat,lon,barrioId,barrioNombre} para dep 24 ───
function loadGeoref(pereiraFeats){
  const raw = fs.readFileSync(GEOREF,'utf8');
  const lines = raw.split(/\r?\n/);
  const H = lines[0].replace(/^﻿/,'').split(';').map(s=>s.trim());
  const ix = n=>H.indexOf(n);
  const I_COD=ix('CÓDIGO COMPLETO'), I_LAT=ix('LATITUD'), I_LON=ix('LONGITUD'),
        I_BAR=ix('BARRIO'), I_COMN=ix('NOMBRE COMUNA'), I_MUJ=ix('MUJERES'), I_HOM=ix('HOMBRES');
  const map = new Map();   // `${mun}-${zz}-${pp}` → meta
  const censoByMun = {};   // mun(int) → censo electoral (mujeres+hombres)
  let nPer=0, nBar=0;
  for (let i=1;i<lines.length;i++){
    const ln=lines[i]; if(!ln) continue;
    const p = ln.split(';');
    const code = (p[I_COD]||'').replace(/"/g,'');
    if (code.length<9) continue;
    if (parseInt(code.slice(0,2),10)!==DEP) continue;
    const mun = parseInt(code.slice(2,5),10);
    const zz = pad2(code.slice(5,7)), pp = pad2(code.slice(7,9));
    const lat=parseFloat(p[I_LAT]), lon=parseFloat(p[I_LON]);
    const meta = { lat, lon, comuna:(p[I_COMN]||'').replace(/"/g,'').trim(), barrioCsv:(p[I_BAR]||'').replace(/"/g,'').trim() };
    const censo = (parseInt(p[I_MUJ]||'0',10)||0) + (parseInt(p[I_HOM]||'0',10)||0);
    censoByMun[mun] = (censoByMun[mun]||0) + censo;
    // Pereira: PIP a barrio oficial
    if (mun===PEREIRA_MUN && pereiraFeats && Number.isFinite(lat) && Number.isFinite(lon)){
      const b = findBarrio(lat, lon, pereiraFeats);
      if (b){ meta.barrioId=b.id; meta.barrioNombre=b.nombre; nBar++; }
      nPer++;
    }
    map.set(`${mun}-${zz}-${pp}`, meta);
  }
  console.log(`  · georef Risaralda: ${map.size} puestos · Pereira PIP ${nBar}/${nPer}`);
  if (process.env.DBG){
    const ej=[...map].filter(([k,m])=>m.barrioId).slice(0,8).map(([k])=>k);
    console.log('  DBG keys con barrioId:', ej.join(' '));
  }
  return { map, censoByMun };
}

// ─── MAIN ─────────────────────────────────────────────────────────────
async function main(){
  const csvPath = process.argv[2];
  const year = process.argv[3];
  if (!csvPath || !year){ console.error('uso: build.js <csv> <year>'); process.exit(1); }
  fs.mkdirSync(OUT_DIR, { recursive:true });

  console.log(`▶ Risaralda ${year}`);
  const pereiraFeats = loadPereiraBarrios();
  const { map:georef, censoByMun } = loadGeoref(pereiraFeats);
  const censoDep = Object.values(censoByMun).reduce((a,b)=>a+b,0);

  // Estructuras: por corporación
  //  gobernacion/asamblea: dep scope + por_mun scopes
  //  alcaldia/concejo: por_mun scopes (cada mun su carrera)
  const dep = { gobernacion:emptyScope(), asamblea:emptyScope() };
  const porMun = { gobernacion:new Map(), asamblea:new Map(), alcaldia:new Map(), concejo:new Map() };
  // Drill: corp → mun → `zz-pp` scope
  const porPuesto = { gobernacion:new Map(), asamblea:new Map(), alcaldia:new Map(), concejo:new Map() };
  // Pereira barrio: corp → barrioId scope (+ meta)
  const porBarrio = { gobernacion:new Map(), asamblea:new Map(), alcaldia:new Map(), concejo:new Map() };
  const barrioMeta = new Map();   // barrioId → {nombre, latSum, lonSum, w}
  // Reporte clasificación: partido → {alt, votos}
  const clasif = new Map();

  const stream = fs.createReadStream(csvPath, { encoding:'utf8' });
  const rl = readline.createInterface({ input:stream, crlfDelay:Infinity });
  let idx=null, kept=0;

  for await (const rawLine of rl){
    if (idx===null){
      const cols = rawLine.replace(/^﻿/,'').split(';').map(s=>s.trim());
      idx={}; cols.forEach((c,i)=>idx[c]=i);
      continue;
    }
    const line = rawLine; if(!line.trim()) continue;
    const p = line.split(';');
    if (parseInt(p[idx['COD_DDE']]||'0',10)!==DEP) continue;
    const mun = parseInt(p[idx['COD_MME']]||'0',10);
    if (!MUNS[mun]) continue;
    const corName = COR_DES_TO_NAME[String(p[idx['DES_COR']]||'').trim().toUpperCase()];
    if (!corName) continue;
    const votos = parseInt(p[idx['NUM_VOT']]||'0',10);
    const cod = p[idx['COD_CAN']];
    if (!cod || !Number.isFinite(votos) || votos<=0) continue;

    const nombre = norm(unquote(p[idx['DES_CAN']]||''));
    const partidoRaw = unquote(p[idx['DES_PAR']]||'');
    const partido = norm(partidoRaw);
    const codpar = (idx['COD_PAR']!=null) ? String(p[idx['COD_PAR']]||'').trim() : '';
    const isSpecial = !!SPECIAL_CODES[cod];
    const alt = isSpecial ? false : esAlternativo(partidoRaw, codpar);
    const key = `${codpar||partido}|${cod}`;

    if (!isSpecial){
      let cl = clasif.get(partido); if(!cl){ cl={alt, votos:0, codpar}; clasif.set(partido,cl);} cl.votos+=votos;
    }

    const zz = pad2(p[idx['COD_ZZ']]||'0'), pp = pad2(p[idx['COD_PP']]||'0');

    if (corName==='gobernacion' || corName==='asamblea'){
      accum(dep[corName], key, cod, nombre, partido, alt, votos);
    }
    accum(ensure(porMun[corName], mun), key, cod, nombre, partido, alt, votos);
    accum(ensure(porPuesto[corName], `${mun}::${zz}-${pp}`), key, cod, nombre, partido, alt, votos);

    // Pereira barrio
    if (mun===PEREIRA_MUN){
      const g = georef.get(`${mun}-${zz}-${pp}`);
      if (g && g.barrioId){
        accum(ensure(porBarrio[corName], g.barrioId), key, cod, nombre, partido, alt, votos);
        let m = barrioMeta.get(g.barrioId);
        if (!m){ m={nombre:g.barrioNombre, latSum:0, lonSum:0, w:0}; barrioMeta.set(g.barrioId,m); }
        m.latSum += g.lat*votos; m.lonSum += g.lon*votos; m.w += votos;
      }
    }
    kept++;
  }
  console.log(`  · filas usadas: ${kept}`);

  // ─── SERIALIZAR PRINCIPAL ───────────────────────────────────────────
  const out = {
    year:+year, depcod:String(DEP), dep:DEP_NOMBRE,
    generated:new Date().toISOString().slice(0,10),
    alt_definicion:'Verde + Pacto Histórico + izquierda histórica (Polo, Colombia Humana, UP, MAIS, ADA, Comunes)',
    censo: censoDep,
    muns: Object.fromEntries(Object.entries(MUNS).map(([k,v])=>[k,{nombre:v, censo:censoByMun[+k]||0}])),
    corporaciones:{},
  };

  // gobernación (cand) y asamblea (lista) tienen depto + por_mun
  out.corporaciones.gobernacion = {
    dep: serialize(dep.gobernacion, { mode:'cand', topN:0 }),
    por_mun: Object.fromEntries([...porMun.gobernacion].map(([m,s])=>[m, serialize(s,{mode:'cand', topN:12})])),
  };
  out.corporaciones.asamblea = {
    dep: serialize(dep.asamblea, { mode:'lista', curules:CURULES_ASAMBLEA, topN:0 }),
    por_mun: Object.fromEntries([...porMun.asamblea].map(([m,s])=>[m, serialize(s,{mode:'lista', topN:15})])),
  };
  // alcaldía (cand) y concejo (lista) sólo por_mun
  out.corporaciones.alcaldia = {
    por_mun: Object.fromEntries([...porMun.alcaldia].map(([m,s])=>[m, serialize(s,{mode:'cand', topN:0})])),
  };
  out.corporaciones.concejo = {
    por_mun: Object.fromEntries([...porMun.concejo].map(([m,s])=>[m, serialize(s,{mode:'lista', curules:CURULES_CONCEJO[m]||0, topN:25})])),
  };

  const mainPath = path.join(OUT_DIR, `risaralda-${year}.json`);
  fs.writeFileSync(mainPath, JSON.stringify(out));
  console.log(`  ✓ ${path.basename(mainPath)} (${(fs.statSync(mainPath).size/1024).toFixed(0)} KB)`);

  // ─── DRILL POR PUESTO (compacto: lider partido + alt_pct) ───────────
  const puestosOut = {};
  for (const corp of Object.keys(porPuesto)){
    puestosOut[corp] = {};
    for (const [k, s] of porPuesto[corp]){
      const [m, zzpp] = k.split('::');
      const ser = serialize(s, { mode:'cand', topN:0 });
      const g = georef.get(`${m}-${zzpp}`);
      (puestosOut[corp][m] ||= {})[zzpp] = {
        validos:ser.validos, alt_votos:ser.alt_votos, alt_pct:ser.alt_pct,
        lider: ser.lider ? { partido:ser.lider.partido, pct:ser.lider.pct, alt:!!ser.lider.alt } : null,
        lat: g&&Number.isFinite(g.lat)?+g.lat.toFixed(5):null, lon: g&&Number.isFinite(g.lon)?+g.lon.toFixed(5):null,
      };
    }
  }
  const pPath = path.join(OUT_DIR, `risaralda-${year}-puestos.json`);
  fs.writeFileSync(pPath, JSON.stringify(puestosOut));
  console.log(`  ✓ ${path.basename(pPath)} (${(fs.statSync(pPath).size/1024).toFixed(0)} KB)`);

  // ─── PEREIRA POR BARRIO ─────────────────────────────────────────────
  const barriosOut = { _meta:{} };
  for (const [bid, m] of barrioMeta){
    barriosOut._meta[bid] = { nombre:m.nombre, lat:m.w?+(m.latSum/m.w).toFixed(6):null, lon:m.w?+(m.lonSum/m.w).toFixed(6):null };
  }
  for (const corp of Object.keys(porBarrio)){
    barriosOut[corp] = {};
    for (const [bid, s] of porBarrio[corp]){
      const ser = serialize(s, { mode:'cand', topN:6 });
      barriosOut[corp][bid] = {
        validos:ser.validos, alt_votos:ser.alt_votos, alt_pct:ser.alt_pct,
        lider: ser.lider ? { partido:ser.lider.partido, nombre:ser.lider.nombre, pct:ser.lider.pct, alt:!!ser.lider.alt } : null,
      };
    }
  }
  const bPath = path.join(OUT_DIR, `risaralda-${year}-pereira-barrios.json`);
  fs.writeFileSync(bPath, JSON.stringify(barriosOut));
  console.log(`  ✓ ${path.basename(bPath)} · ${barrioMeta.size} barrios con dato`);

  // ─── REPORTE CLASIFICACIÓN (CSV revisable) ──────────────────────────
  const rows = [['alt','codpar','partido','votos_total']];
  for (const [p, c] of [...clasif].sort((a,b)=>b[1].votos-a[1].votos)){
    rows.push([c.alt?'ALT':'', c.codpar, `"${p}"`, c.votos]);
  }
  const cPath = path.join(OUT_DIR, `risaralda-${year}-clasificacion.csv`);
  fs.writeFileSync(cPath, rows.map(r=>r.join(',')).join('\n'));
  const nAlt = [...clasif.values()].filter(c=>c.alt).length;
  console.log(`  ✓ clasificacion.csv · ${nAlt}/${clasif.size} partidos marcados ALT`);
}

main().catch(e=>{ console.error(e); process.exit(1); });
