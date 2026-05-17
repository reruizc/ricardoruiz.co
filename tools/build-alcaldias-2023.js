#!/usr/bin/env node
// tools/build-alcaldias-2023.js
//
// Procesa GCS_2023TER.csv y genera agregados NACIONALES de alcaldías:
//
//   {outDir}/nacional/resumen.json          totales nacionales + ranking de
//                                           partidos por # alcaldías ganadas
//   {outDir}/nacional/por-depto.json        array de 33 deptos
//   {outDir}/nacional/por-mun.json          array de ~1101 muns con ganador
//                                           + top 3 candidatos
//   {outDir}/departamentos/{depCod}/municipios.json   candidatos completos
//                                                     por mun del depto
//   {outDir}/departamentos/{depCod}/puestos.json      por puesto (zz-pp)
//
// Notas:
// - Streaming, sin dependencias. ~30s para procesar el GCS de 1.95 GB.
// - Sólo procesa DES_COR=ALCALDE. El mismo archivo trae GOBERNADOR,
//   ASAMBLEA, CONCEJO — esos van en módulos separados.
// - Códigos Registraduría: dep padStart(2), mun padStart(3).
// - Especiales (996/997/998/999) → blanco/nulos/no_marcados.
// - "CANDIDATOS TOTALES" (fila agregada de la Registraduría) se filtra
//   por nombre por si aparece en alguna fila.
// - Censo + nombres de depto/mun se leen de COMUNAS_DATA.csv (Divipole).

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SPECIAL_CODES = {
  '996':'blanco', '997':'nulos', '998':'no_marcados', '999':'no_marcados',
};

const COR_NAME = 'ALCALDE';   // procesar sólo esta corporación

const COMUNAS_DATA_PATH = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/COMUNAS_DATA.csv';

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function pad(n, w){ return String(parseInt(n,10) || 0).padStart(w, '0'); }

// ─── Lookup deptos/muns + censo desde COMUNAS_DATA.csv ──────
// Output: { depto:{cod:nombre}, mun:{"dep-mun":{nombre, censo, mujeres, hombres}}, capitals:{depCod:munCod} }
function loadDivipole(){
  const raw = fs.readFileSync(COMUNAS_DATA_PATH, 'utf8');
  const lines = raw.split(/\r?\n/);
  const header = lines[0].replace(/^﻿/, '').split(';').map(s => s.trim());
  const idx = (n) => header.indexOf(n);
  const I_DD = idx('dd'), I_MM = idx('mm');
  const I_DEP = idx('departamento'), I_MUN = idx('municipio');
  const I_M = idx('mujeres'), I_H = idx('hombres'), I_T = idx('total');

  const depto = {};
  const mun = {};
  for (let i = 1; i < lines.length; i++){
    const ln = lines[i];
    if (!ln) continue;
    const p = ln.split(';');
    const dd = pad(p[I_DD], 2), mm = pad(p[I_MM], 3);
    if (!dd || dd === '00') continue;
    if (!depto[dd]) depto[dd] = normName(p[I_DEP]);
    const key = `${dd}-${mm}`;
    const mObj = mun[key] || { nombre: normName(p[I_MUN]), censo: 0, mujeres: 0, hombres: 0 };
    mObj.censo    += parseInt(p[I_T] || '0', 10) || 0;
    mObj.mujeres  += parseInt(p[I_M] || '0', 10) || 0;
    mObj.hombres  += parseInt(p[I_H] || '0', 10) || 0;
    if (!mObj.nombre) mObj.nombre = normName(p[I_MUN]);
    mun[key] = mObj;
  }
  // Capital = mun con código '001' en cada depto (convención Registraduría)
  const capitals = {};
  for (const dd of Object.keys(depto)){
    if (mun[`${dd}-001`]) capitals[dd] = '001';
  }
  console.log(`  · Divipole: ${Object.keys(depto).length} deptos, ${Object.keys(mun).length} muns`);
  return { depto, mun, capitals };
}

function parseHeaderLine(line){
  const clean = line.replace(/^﻿/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['DES_COR','COD_DDE','COD_MME','COD_ZZ','COD_PP','DES_MS','COD_CAN','DES_CAN','DES_PAR','NUM_VOT'];
  const missing = required.filter(r => !(r in map));
  if (missing.length) throw new Error(`Header sin columnas: ${missing.join(', ')}`);
  return map;
}

function emptyScope(){ return { cands: new Map(), especiales: new Map() }; }
function ensure(m, k){ let s = m.get(k); if (!s){ s = emptyScope(); m.set(k, s); } return s; }
function accum(scope, candCod, candNombre, candPartido, votos){
  const sp = SPECIAL_CODES[candCod];
  if (sp){
    scope.especiales.set(sp, (scope.especiales.get(sp) || 0) + votos);
    return;
  }
  let c = scope.cands.get(candCod);
  if (!c){
    c = { cod: candCod, nombre: candNombre, partido: candPartido, votos: 0 };
    scope.cands.set(candCod, c);
  }
  c.votos += votos;
  if (!c.nombre && candNombre) c.nombre = candNombre;
  if (!c.partido && candPartido) c.partido = candPartido;
}

function serializeScope(scope, topN){
  const cands = [];
  let validos = 0;
  for (const c of scope.cands.values()){
    cands.push({ cod: c.cod, nombre: c.nombre, partido: c.partido, votos: c.votos });
    validos += c.votos;
  }
  cands.sort((a,b) => b.votos - a.votos);
  for (const c of cands){
    c.pct = validos > 0 ? +(c.votos / validos * 100).toFixed(3) : 0;
  }
  const especiales = {};
  for (const [k,v] of scope.especiales) especiales[k] = v;
  const totalEsp = Object.values(especiales).reduce((s,v) => s+v, 0);
  return {
    votos_validos: validos,
    votos_totales: validos + totalEsp,
    especiales,
    candidatos: topN ? cands.slice(0, topN) : cands,
  };
}

async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;
  let rowsRead = 0, rowsKept = 0, rowsSkipTotal = 0;

  // Estructuras
  const nacional = emptyScope();                        // total nacional
  const porDepto = new Map();                           // depCod → scope
  const porMun = new Map();                             // "dep-mun" → scope
  // Puestos: por depto, key "mun-zz-pp"
  const porPuestoByDep = new Map();                     // depCod → Map(key → scope)

  for await (const rawLine of rl){
    if (idx === null){ idx = parseHeaderLine(rawLine); continue; }
    const line = rawLine.trim();
    if (!line) continue;
    rowsRead++;

    const parts = line.split(';');
    const corDes = String(parts[idx['DES_COR']] || '').trim().toUpperCase();
    if (corDes !== COR_NAME) continue;

    const dep = pad(parts[idx['COD_DDE']], 2);
    const mun = pad(parts[idx['COD_MME']], 3);
    const zz  = pad(parts[idx['COD_ZZ']], 2);
    const pp  = pad(parts[idx['COD_PP']], 2);

    const cod   = parts[idx['COD_CAN']];
    const des   = parts[idx['DES_CAN']] || '';
    const par   = parts[idx['DES_PAR']] || '';
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);
    if (!cod || !Number.isFinite(votos) || votos <= 0) continue;

    const candNombre = normName(des);
    const candPartido = normName(par);

    // Filtro: "CANDIDATOS TOTALES" es la fila agregada de la Registraduría
    if (candNombre === 'CANDIDATOS TOTALES' || candPartido === 'CANDIDATOS TOTALES'){
      rowsSkipTotal++;
      continue;
    }

    const munKey = `${dep}-${mun}`;
    accum(nacional, cod, candNombre, candPartido, votos);
    accum(ensure(porDepto, dep), cod, candNombre, candPartido, votos);
    accum(ensure(porMun, munKey), cod, candNombre, candPartido, votos);

    // Por puesto (anidado por depto)
    let depPuestos = porPuestoByDep.get(dep);
    if (!depPuestos){ depPuestos = new Map(); porPuestoByDep.set(dep, depPuestos); }
    accum(ensure(depPuestos, `${mun}-${zz}-${pp}`), cod, candNombre, candPartido, votos);

    rowsKept++;
  }

  return { nacional, porDepto, porMun, porPuestoByDep, rowsRead, rowsKept, rowsSkipTotal };
}

function writeJson(filePath, obj){
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(obj));
}

function fmtMB(b){ return (b/1024/1024).toFixed(2) + ' MB'; }
function fmtKB(b){ return Math.round(b/1024) + ' KB'; }

async function main(){
  const [, , csvPath, outDir] = process.argv;
  if (!csvPath || !outDir){
    console.error('Uso: node tools/build-alcaldias-2023.js <archivo.csv> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(csvPath)){ console.error(`No existe: ${csvPath}`); process.exit(1); }

  console.log(`\n[alcaldias-2023] procesando ${path.basename(csvPath)}`);
  const t0 = Date.now();
  const divipole = loadDivipole();
  const { nacional, porDepto, porMun, porPuestoByDep, rowsRead, rowsKept, rowsSkipTotal } = await processCsv(csvPath);
  const dt = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`  ${rowsRead.toLocaleString('es-CO')} filas leídas · ${rowsKept.toLocaleString('es-CO')} ALCALDE en ${dt}s`);
  if (rowsSkipTotal) console.log(`  · filtradas CANDIDATOS TOTALES: ${rowsSkipTotal}`);

  // ─── Ganador por mun + agregaciones nacionales por partido ─────
  const munWinners = [];    // [{dep, mun, nombreDep, nombreMun, censo, ganador, votos, partido, pct, ...}]
  const partidoStats = new Map();   // partido → { muns: 0, capitales: 0, votos_totales: 0, censo: 0 }

  for (const [munKey, scope] of porMun){
    const [dep, mun] = munKey.split('-');
    const ser = serializeScope(scope, 6);   // top-6 por mun en por-mun.json
    const top = ser.candidatos[0];
    if (!top) continue;

    const munInfo = divipole.mun[munKey] || { nombre: '', censo: 0 };
    const depInfo = divipole.depto[dep] || '';
    const isCapital = divipole.capitals[dep] === mun;

    munWinners.push({
      dep, mun,
      nombre_dep: depInfo,
      nombre_mun: munInfo.nombre,
      censo: munInfo.censo,
      es_capital: isCapital,
      votos_validos: ser.votos_validos,
      votos_totales: ser.votos_totales,
      especiales: ser.especiales,
      ganador: {
        cod: top.cod, nombre: top.nombre, partido: top.partido,
        votos: top.votos, pct: top.pct,
      },
      top: ser.candidatos.map(c => ({ nombre: c.nombre, partido: c.partido, votos: c.votos, pct: c.pct })),
    });

    const p = top.partido || '(SIN PARTIDO)';
    let ps = partidoStats.get(p);
    if (!ps){ ps = { muns: 0, capitales: 0, votos: 0, censo: 0 }; partidoStats.set(p, ps); }
    ps.muns++;
    if (isCapital) ps.capitales++;
    ps.votos += top.votos;
    ps.censo += munInfo.censo;
  }
  console.log(`  · municipios con ganador: ${munWinners.length}`);
  console.log(`  · partidos/movimientos únicos en ganadores: ${partidoStats.size}`);

  // ─── nacional/resumen.json ──────
  const nacSer = serializeScope(nacional);
  // En la tabla nacional, agregar también por partido (sumando todos los candidatos)
  // y devolver TOP N partidos por votos totales nacionales
  const aggPartidoNacional = new Map();
  for (const c of nacSer.candidatos){
    const p = c.partido || '(SIN PARTIDO)';
    aggPartidoNacional.set(p, (aggPartidoNacional.get(p) || 0) + c.votos);
  }
  const partidosNacional = Array.from(aggPartidoNacional, ([partido, votos]) => ({ partido, votos }))
    .sort((a,b) => b.votos - a.votos);
  const totalVotosNac = nacSer.votos_validos;
  for (const p of partidosNacional){
    p.pct = totalVotosNac > 0 ? +(p.votos / totalVotosNac * 100).toFixed(3) : 0;
    const ps = partidoStats.get(p.partido) || { muns: 0, capitales: 0, censo: 0 };
    p.muns_ganados = ps.muns;
    p.capitales_ganadas = ps.capitales;
    p.censo_gobernado = ps.censo;
  }

  // Resumen total
  const totalCenso = munWinners.reduce((s,m) => s + (m.censo || 0), 0);
  const resumen = {
    eleccion: 'alcaldias-2023',
    fecha: '2023-10-29',
    deptos: Object.keys(divipole.depto).length,
    municipios: munWinners.length,
    votos_validos: nacSer.votos_validos,
    votos_totales: nacSer.votos_totales,
    especiales: nacSer.especiales,
    censo_total: totalCenso,
    partidos: partidosNacional,    // ordenado por votos; con muns_ganados, capitales, censo
  };
  writeJson(path.join(outDir, 'nacional', 'resumen.json'), resumen);
  const sz1 = fs.statSync(path.join(outDir, 'nacional', 'resumen.json')).size;
  console.log(`  · nacional/resumen.json (${fmtKB(sz1)})`);

  // ─── nacional/por-depto.json ──────
  const deptos = [];
  for (const [dep, scope] of porDepto){
    const ser = serializeScope(scope, 6);
    const top = ser.candidatos[0];
    const munsInDep = munWinners.filter(m => m.dep === dep);
    const censoDep = munsInDep.reduce((s,m) => s + (m.censo || 0), 0);
    // Ranking de partidos en el depto: # de muns ganados por partido
    const pStats = new Map();
    for (const m of munsInDep){
      const p = m.ganador.partido || '(SIN PARTIDO)';
      let s = pStats.get(p);
      if (!s){ s = { partido: p, muns: 0, votos_totales: 0, censo: 0 }; pStats.set(p, s); }
      s.muns++;
      s.votos_totales += m.ganador.votos;
      s.censo += m.censo || 0;
    }
    const partidos = Array.from(pStats.values()).sort((a,b) => b.muns - a.muns || b.votos_totales - a.votos_totales);

    deptos.push({
      dep,
      nombre: divipole.depto[dep] || '',
      municipios: munsInDep.length,
      censo: censoDep,
      votos_validos: ser.votos_validos,
      votos_totales: ser.votos_totales,
      especiales: ser.especiales,
      top_candidatos: ser.candidatos.map(c => ({ nombre: c.nombre, partido: c.partido, votos: c.votos, pct: c.pct })),
      partidos,
    });
  }
  deptos.sort((a,b) => parseInt(a.dep,10) - parseInt(b.dep,10));
  writeJson(path.join(outDir, 'nacional', 'por-depto.json'), deptos);
  const sz2 = fs.statSync(path.join(outDir, 'nacional', 'por-depto.json')).size;
  console.log(`  · nacional/por-depto.json (${fmtKB(sz2)}, ${deptos.length} deptos)`);

  // ─── nacional/por-mun.json ──────
  munWinners.sort((a,b) => (a.dep === b.dep ? a.mun.localeCompare(b.mun) : a.dep.localeCompare(b.dep)));
  writeJson(path.join(outDir, 'nacional', 'por-mun.json'), munWinners);
  const sz3 = fs.statSync(path.join(outDir, 'nacional', 'por-mun.json')).size;
  console.log(`  · nacional/por-mun.json (${fmtMB(sz3)}, ${munWinners.length} muns)`);

  // ─── departamentos/{depCod}/municipios.json ──────
  // Para cada depto, lista de muns con candidatos completos (TODOS, no top-N)
  let totalMunsBytes = 0, totalPuesBytes = 0;
  for (const [dep, scope] of porDepto){
    const munsDep = [];
    for (const [munKey, mscope] of porMun){
      if (!munKey.startsWith(`${dep}-`)) continue;
      const [, munC] = munKey.split('-');
      const ser = serializeScope(mscope);   // TODOS los candidatos
      const munInfo = divipole.mun[munKey] || { nombre: '', censo: 0, mujeres: 0, hombres: 0 };
      munsDep.push({
        mun: munC,
        nombre: munInfo.nombre,
        censo: munInfo.censo,
        mujeres: munInfo.mujeres,
        hombres: munInfo.hombres,
        es_capital: divipole.capitals[dep] === munC,
        votos_validos: ser.votos_validos,
        votos_totales: ser.votos_totales,
        especiales: ser.especiales,
        candidatos: ser.candidatos,
      });
    }
    munsDep.sort((a,b) => a.mun.localeCompare(b.mun));
    const fp = path.join(outDir, 'departamentos', dep, 'municipios.json');
    writeJson(fp, munsDep);
    totalMunsBytes += fs.statSync(fp).size;

    // Puestos del depto
    const puestos = [];
    const depPuestos = porPuestoByDep.get(dep);
    if (depPuestos){
      for (const [pkey, pscope] of depPuestos){
        const [munC, zz, pp] = pkey.split('-');
        const ser = serializeScope(pscope, 6);   // top-6 por puesto (peso)
        puestos.push({
          mun: munC, zz, pp,
          votos_validos: ser.votos_validos,
          votos_totales: ser.votos_totales,
          especiales: ser.especiales,
          top: ser.candidatos,
        });
      }
      puestos.sort((a,b) => a.mun.localeCompare(b.mun) || a.zz.localeCompare(b.zz) || a.pp.localeCompare(b.pp));
    }
    const fpp = path.join(outDir, 'departamentos', dep, 'puestos.json');
    writeJson(fpp, puestos);
    totalPuesBytes += fs.statSync(fpp).size;
  }
  console.log(`  · departamentos/*/municipios.json: ${fmtMB(totalMunsBytes)} totales`);
  console.log(`  · departamentos/*/puestos.json:    ${fmtMB(totalPuesBytes)} totales`);

  console.log(`\n[ok] ${((Date.now() - t0) / 1000).toFixed(1)}s totales\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
