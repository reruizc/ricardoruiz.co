#!/usr/bin/env node
// tools/build-concejo-2023.js
//
// Procesa GCS_2023TER.csv (DES_COR=CONCEJO) y genera agregados
// jerárquicos para concejo-2023.html. Espejo de build-alcaldias-2023.js
// pero con D'Hondt por mun + lista de candidatos preferentes + drill
// hasta mesa.
//
// Output:
//   {outDir}/nacional/resumen.json
//     totales nacionales (votos por partido sumando todos los muns,
//     curules totales repartidas, listado de muns y deptos)
//   {outDir}/nacional/por-depto.json
//     array[{ dep, nombre, muns, censo, votos, partidos[] }]
//     · partidos[i] = { partido, votos, curules_dep, muns_ganados }
//   {outDir}/nacional/por-mun.json
//     array[{ dep, mun, nombre_dep, nombre_mun, censo, curules,
//             votos_validos, votos_totales, partido_top[3] }]
//   {outDir}/departamentos/{dep}/municipios.json
//     array[{ mun, nombre, censo, curules, votos_validos,
//             partidos[{ partido, votos, pct, curules,
//                        tipo_lista, candidatos[], electos[] }] }]
//   {outDir}/departamentos/{dep}/{mun}/puestos.json
//     array[{ zz, pp, votos_validos, votos_totales, partidos_top[6] }]
//   {outDir}/departamentos/{dep}/{mun}/mesas.json
//     array[{ zz, pp, mesa, votos_validos, votos_totales, partidos[] }]
//
// Curules por concejo (Ley 136/1994 art. 22 modificada por Ley 1551/2012)
// Bogotá D.C.: 45 (Constitución, art. 323)
//
// Streaming, sin deps. ~60-90s para 1.96 GB.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SPECIAL_CODES = {
  '996':'blanco', '997':'nulos', '998':'no_marcados', '999':'no_marcados',
};

const COR_NAME = 'CONCEJO';

const COMUNAS_DATA_PATH = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/COMUNAS_DATA.csv';

function normName(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function pad(n, w){ return String(parseInt(n,10) || 0).padStart(w, '0'); }

// ─── Curules por mun ─────────────────────────────────────────
// El CSV usa electoral_id Registraduría (Bogotá=16, Antioquia=01, etc.),
// no códigos DANE. COMUNAS_DATA.csv usa el mismo electoral_id, así que el
// match es directo. Bogotá D.C. tiene 45 curules por Constitución (art. 323).
//
// Tabla por POBLACIÓN proyectada DANE (Ley 136/1994 art. 22 modificada
// por Ley 1551/2012). Como sólo tenemos censo electoral, aproximamos
// población ≈ censo / 0.72.
function curulesParaMun(depCod, munCod, censoElectoral){
  // Bogotá D.C. = 45 por Constitución (art. 323)
  // En el electoral_id del CSV TER 2023, Bogotá = dep 16 mun 001.
  if (depCod === '16' && munCod === '001') return 45;

  const k = `${depCod}-${munCod}`;
  if (MUN_CURULES_OVERRIDE[k]) return MUN_CURULES_OVERRIDE[k];

  // Población aproximada = censo / 0.72
  const pob = Math.round((censoElectoral || 0) / 0.72);
  if (pob <= 5000) return 7;
  if (pob <= 10000) return 9;
  if (pob <= 20000) return 11;
  if (pob <= 50000) return 13;
  if (pob <= 100000) return 15;
  if (pob <= 250000) return 17;
  if (pob <= 1000000) return 19;
  return 21;
}
const MUN_CURULES_OVERRIDE = {
  // Ejemplo: '76-001': 21 (Cali) — añadir si discrepa con la realidad.
};

// ─── D'Hondt ─────────────────────────────────────────────────
// Devuelve { partido: curules } para los partidos con votos > 0.
function dhondt(partidoVotos, seats){
  const items = Object.entries(partidoVotos)
    .filter(([,v]) => v > 0)
    .map(([p, v]) => ({ partido: p, votos: v, curules: 0 }));
  if (!items.length || seats <= 0) return {};
  for (let s = 0; s < seats; s++){
    let best = -1, bestQ = -1;
    for (let i = 0; i < items.length; i++){
      const q = items[i].votos / (items[i].curules + 1);
      if (q > bestQ){ bestQ = q; best = i; }
    }
    items[best].curules++;
  }
  const out = {};
  for (const it of items) out[it.partido] = it.curules;
  return out;
}

// ─── Lookup deptos/muns + censo desde COMUNAS_DATA.csv ──────
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
  const required = ['DES_COR','COD_DDE','COD_MME','COD_ZZ','COD_PP','DES_MS','COD_CAN','DES_CAN','COD_PAR','DES_PAR','NUM_VOT'];
  const missing = required.filter(r => !(r in map));
  if (missing.length) throw new Error(`Header sin columnas: ${missing.join(', ')}`);
  return map;
}

// ─── Estructuras de acumulación ──────────────────────────────
// Por mun: { partidos: Map<partido, { votos_lista, votos_pref,
//          candidatos: Map<codCan, { cod, nombre, votos }> }>,
//          especiales: Map<tipo, votos>, votos_validos }
function emptyMunScope(){
  return { partidos: new Map(), especiales: new Map(), votos_validos: 0 };
}
function ensurePartido(scope, partido){
  let p = scope.partidos.get(partido);
  if (!p){
    p = { partido, votos_lista: 0, votos_pref: 0, candidatos: new Map() };
    scope.partidos.set(partido, p);
  }
  return p;
}
function accumMun(scope, codCan, candNombre, candPartido, votos){
  const sp = SPECIAL_CODES[codCan];
  if (sp){
    if (votos > 0) scope.especiales.set(sp, (scope.especiales.get(sp) || 0) + votos);
    return;
  }
  if (!candPartido) return;
  if (votos > 0) scope.votos_validos += votos;
  const p = ensurePartido(scope, candPartido);
  if (codCan === '0' || codCan === 0){
    if (votos > 0) p.votos_lista += votos;
  } else {
    if (votos > 0) p.votos_pref += votos;
    // Registrar siempre el candidato (aunque votos=0) — clave para
    // listas cerradas donde los preferentes existen pero acumulan 0.
    let c = p.candidatos.get(codCan);
    if (!c){
      c = { cod: codCan, nombre: candNombre, votos: 0 };
      p.candidatos.set(codCan, c);
    }
    if (votos > 0) c.votos += votos;
    if (!c.nombre && candNombre) c.nombre = candNombre;
  }
}

// Scope simple (votos por partido) para puestos/mesas/depto/nacional
function emptySimpleScope(){
  return { partidos: new Map(), especiales: new Map(), votos_validos: 0 };
}
function accumSimple(scope, codCan, candPartido, votos){
  const sp = SPECIAL_CODES[codCan];
  if (sp){
    scope.especiales.set(sp, (scope.especiales.get(sp) || 0) + votos);
    return;
  }
  if (!candPartido) return;
  scope.votos_validos += votos;
  scope.partidos.set(candPartido, (scope.partidos.get(candPartido) || 0) + votos);
}

// Serialización
function partidosFromMunScope(munScope, dhondtSeats){
  const partidos = [];
  for (const p of munScope.partidos.values()){
    const cands = Array.from(p.candidatos.values()).sort((a,b) => b.votos - a.votos);
    const votos_total = p.votos_lista + p.votos_pref;
    const pct = munScope.votos_validos > 0 ? +(votos_total / munScope.votos_validos * 100).toFixed(3) : 0;
    const tipo_lista = p.votos_pref > p.votos_lista * 0.1 ? 'abierta' : 'cerrada';
    partidos.push({
      partido: p.partido,
      votos_total,
      votos_lista: p.votos_lista,
      votos_pref: p.votos_pref,
      pct,
      tipo_lista,
      candidatos: cands,
      curules: 0,
    });
  }
  // D'Hondt sobre votos_total por partido
  const map = {};
  for (const p of partidos) map[p.partido] = p.votos_total;
  const cur = dhondt(map, dhondtSeats);
  for (const p of partidos) p.curules = cur[p.partido] || 0;
  // Electos: para partidos con curules, top-K candidatos
  //   · lista abierta → ordenados por voto preferente desc
  //   · lista cerrada → ordenados por COD_CAN asc (orden de inscripción
  //     aproximado; la Registraduría asigna cod 1..N siguiendo el
  //     formulario E-6, que es el orden inscrito)
  for (const p of partidos){
    if (p.curules <= 0){ p.electos = []; continue; }
    if (p.tipo_lista === 'abierta'){
      p.electos = p.candidatos.slice(0, p.curules).map(c => ({
        cod: c.cod, nombre: c.nombre, votos: c.votos,
      }));
    } else {
      const ordenInscripcion = [...p.candidatos].sort((a, b) => {
        const ai = parseInt(a.cod, 10) || 0;
        const bi = parseInt(b.cod, 10) || 0;
        return ai - bi;
      });
      p.electos = ordenInscripcion.slice(0, p.curules).map(c => ({
        cod: c.cod, nombre: c.nombre, votos: c.votos,
      }));
      p.orden_cerrada = true;
    }
  }
  partidos.sort((a,b) => b.votos_total - a.votos_total);
  return partidos;
}

function simpleScopeSerialize(scope, topN){
  const arr = [];
  for (const [partido, votos] of scope.partidos){
    arr.push({ partido, votos });
  }
  arr.sort((a,b) => b.votos - a.votos);
  for (const p of arr){
    p.pct = scope.votos_validos > 0 ? +(p.votos / scope.votos_validos * 100).toFixed(3) : 0;
  }
  const especiales = {};
  let totalEsp = 0;
  for (const [k,v] of scope.especiales){ especiales[k] = v; totalEsp += v; }
  return {
    votos_validos: scope.votos_validos,
    votos_totales: scope.votos_validos + totalEsp,
    especiales,
    partidos: topN ? arr.slice(0, topN) : arr,
  };
}

async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;
  let rowsRead = 0, rowsKept = 0, rowsSkipTotal = 0;

  // porMun: "dep-mun" → munScope (con partidos+candidatos)
  const porMun = new Map();
  // porDepto: dep → simpleScope (votos por partido a nivel depto)
  const porDepto = new Map();
  // nacional: simpleScope
  const nacional = emptySimpleScope();
  // porPuestoByMun: "dep-mun" → Map("zz-pp" → simpleScope)
  const porPuestoByMun = new Map();
  // porMesaByMun:   "dep-mun" → Map("zz-pp-mesa" → simpleScope)
  const porMesaByMun  = new Map();

  for await (const rawLine of rl){
    if (idx === null){ idx = parseHeaderLine(rawLine); continue; }
    const line = rawLine.trim();
    if (!line) continue;
    rowsRead++;

    const parts = line.split(';');
    const corDes = String(parts[idx['DES_COR']] || '').trim().toUpperCase();
    if (corDes !== COR_NAME) continue;

    const dep  = pad(parts[idx['COD_DDE']], 2);
    const mun  = pad(parts[idx['COD_MME']], 3);
    const zz   = pad(parts[idx['COD_ZZ']],  2);
    const pp   = pad(parts[idx['COD_PP']],  2);
    const mesa = String(parts[idx['DES_MS']] || '').trim();

    const cod   = String(parts[idx['COD_CAN']]).trim();
    const des   = parts[idx['DES_CAN']] || '';
    const par   = parts[idx['DES_PAR']] || '';
    const votos = parseInt(parts[idx['NUM_VOT']] || '0', 10);
    if (!cod || !Number.isFinite(votos) || votos < 0) continue;
    // Filas con votos=0 sólo aportan registro de candidato (clave para
    // listas cerradas). Las pasamos a accumMun, pero saltamos los demás
    // niveles (puesto/mesa/depto/nacional) porque no aportan info.
    const skipAggregations = (votos === 0);

    const candNombre = normName(des);
    const candPartido = normName(par);

    if (candNombre === 'CANDIDATOS TOTALES' || candPartido === 'CANDIDATOS TOTALES'){
      rowsSkipTotal++;
      continue;
    }

    const munKey = `${dep}-${mun}`;

    // Acumular por mun (full detail: partido + candidatos).
    // Siempre lo hacemos para registrar nombres de listas cerradas.
    let munScope = porMun.get(munKey);
    if (!munScope){ munScope = emptyMunScope(); porMun.set(munKey, munScope); }
    accumMun(munScope, cod, candNombre, candPartido, votos);

    if (skipAggregations){ rowsKept++; continue; }

    // Acumular por depto (simple)
    let depScope = porDepto.get(dep);
    if (!depScope){ depScope = emptySimpleScope(); porDepto.set(dep, depScope); }
    accumSimple(depScope, cod, candPartido, votos);

    // Acumular nacional
    accumSimple(nacional, cod, candPartido, votos);

    // Acumular por puesto del mun
    let puMap = porPuestoByMun.get(munKey);
    if (!puMap){ puMap = new Map(); porPuestoByMun.set(munKey, puMap); }
    const puKey = `${zz}-${pp}`;
    let puScope = puMap.get(puKey);
    if (!puScope){ puScope = emptySimpleScope(); puMap.set(puKey, puScope); }
    accumSimple(puScope, cod, candPartido, votos);

    // Acumular por mesa del mun
    let meMap = porMesaByMun.get(munKey);
    if (!meMap){ meMap = new Map(); porMesaByMun.set(munKey, meMap); }
    const meKey = `${zz}-${pp}-${mesa || '0'}`;
    let meScope = meMap.get(meKey);
    if (!meScope){ meScope = emptySimpleScope(); meMap.set(meKey, meScope); }
    accumSimple(meScope, cod, candPartido, votos);

    rowsKept++;
  }

  return { nacional, porDepto, porMun, porPuestoByMun, porMesaByMun, rowsRead, rowsKept, rowsSkipTotal };
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
    console.error('Uso: node tools/build-concejo-2023.js <archivo.csv> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(csvPath)){ console.error(`No existe: ${csvPath}`); process.exit(1); }

  console.log(`\n[concejo-2023] procesando ${path.basename(csvPath)}`);
  const t0 = Date.now();
  const divipole = loadDivipole();
  const {
    nacional, porDepto, porMun, porPuestoByMun, porMesaByMun,
    rowsRead, rowsKept, rowsSkipTotal,
  } = await processCsv(csvPath);
  const dt = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`  ${rowsRead.toLocaleString('es-CO')} filas leídas · ${rowsKept.toLocaleString('es-CO')} CONCEJO en ${dt}s`);
  if (rowsSkipTotal) console.log(`  · filtradas CANDIDATOS TOTALES: ${rowsSkipTotal}`);

  // ─── Procesar cada mun: D'Hondt + partidos + candidatos ──────
  const munRows = [];                         // por-mun.json (compacto)
  const munFullByDep = new Map();             // dep → array de muns con detalle
  const partidoCurulesNac = new Map();        // partido → curules nacionales
  const partidoCurulesByDep = new Map();      // dep → Map(partido → curules)

  for (const [munKey, munScope] of porMun){
    const [dep, mun] = munKey.split('-');
    const munInfo = divipole.mun[munKey] || { nombre: '', censo: 0, mujeres: 0, hombres: 0 };
    const curules = curulesParaMun(dep, mun, munInfo.censo);
    const partidos = partidosFromMunScope(munScope, curules);

    // Top 3 partidos para por-mun.json
    const top3 = partidos.slice(0, 3).map(p => ({
      partido: p.partido, votos: p.votos_total, pct: p.pct, curules: p.curules,
    }));
    const ganadorPartido = top3[0] ? top3[0].partido : null;
    const especiales = {};
    let totalEsp = 0;
    for (const [k,v] of munScope.especiales){ especiales[k] = v; totalEsp += v; }
    munRows.push({
      dep, mun,
      nombre_dep: divipole.depto[dep] || '',
      nombre_mun: munInfo.nombre,
      censo: munInfo.censo,
      es_capital: divipole.capitals[dep] === mun,
      curules,
      votos_validos: munScope.votos_validos,
      votos_totales: munScope.votos_validos + totalEsp,
      especiales,
      partido_top: top3,
      ganador_partido: ganadorPartido,
    });

    // Full por depto
    let arr = munFullByDep.get(dep);
    if (!arr){ arr = []; munFullByDep.set(dep, arr); }
    arr.push({
      mun, nombre: munInfo.nombre, censo: munInfo.censo,
      mujeres: munInfo.mujeres, hombres: munInfo.hombres,
      es_capital: divipole.capitals[dep] === mun,
      curules,
      votos_validos: munScope.votos_validos,
      votos_totales: munScope.votos_validos + totalEsp,
      especiales,
      partidos,
    });

    // Acumular curules nacionales / por depto
    for (const p of partidos){
      if (p.curules > 0){
        partidoCurulesNac.set(p.partido, (partidoCurulesNac.get(p.partido) || 0) + p.curules);
        let m = partidoCurulesByDep.get(dep);
        if (!m){ m = new Map(); partidoCurulesByDep.set(dep, m); }
        m.set(p.partido, (m.get(p.partido) || 0) + p.curules);
      }
    }
  }
  console.log(`  · muns procesados: ${munRows.length}`);

  // ─── nacional/resumen.json ──────
  const nacSer = simpleScopeSerialize(nacional);
  // Agregar curules
  for (const p of nacSer.partidos) p.curules = partidoCurulesNac.get(p.partido) || 0;
  const totalCurules = Array.from(partidoCurulesNac.values()).reduce((s,v) => s+v, 0);
  const resumen = {
    elecciones: 'Concejos Municipales y Distritales · 2023',
    fecha: '2023-10-29',
    total_muns: munRows.length,
    total_deptos: porDepto.size,
    total_curules: totalCurules,
    votos_validos: nacSer.votos_validos,
    votos_totales: nacSer.votos_totales,
    especiales: nacSer.especiales,
    partidos: nacSer.partidos.sort((a,b) => b.curules - a.curules || b.votos - a.votos),
  };
  writeJson(path.join(outDir, 'nacional', 'resumen.json'), resumen);
  const sz1 = fs.statSync(path.join(outDir, 'nacional', 'resumen.json')).size;
  console.log(`  · nacional/resumen.json (${fmtKB(sz1)})`);

  // ─── nacional/por-depto.json ──────
  const deptos = [];
  for (const [dep, scope] of porDepto){
    const ser = simpleScopeSerialize(scope);
    const curMap = partidoCurulesByDep.get(dep) || new Map();
    for (const p of ser.partidos) p.curules = curMap.get(p.partido) || 0;
    const munsInDep = munRows.filter(m => m.dep === dep);
    deptos.push({
      dep,
      nombre: divipole.depto[dep] || '',
      municipios: munsInDep.length,
      curules: munsInDep.reduce((s,m) => s + m.curules, 0),
      censo: munsInDep.reduce((s,m) => s + (m.censo || 0), 0),
      votos_validos: ser.votos_validos,
      votos_totales: ser.votos_totales,
      especiales: ser.especiales,
      partidos: ser.partidos.sort((a,b) => b.curules - a.curules || b.votos - a.votos),
    });
  }
  deptos.sort((a,b) => parseInt(a.dep,10) - parseInt(b.dep,10));
  writeJson(path.join(outDir, 'nacional', 'por-depto.json'), deptos);
  const sz2 = fs.statSync(path.join(outDir, 'nacional', 'por-depto.json')).size;
  console.log(`  · nacional/por-depto.json (${fmtKB(sz2)}, ${deptos.length} deptos)`);

  // ─── nacional/por-mun.json ──────
  munRows.sort((a,b) => (a.dep === b.dep ? a.mun.localeCompare(b.mun) : a.dep.localeCompare(b.dep)));
  writeJson(path.join(outDir, 'nacional', 'por-mun.json'), munRows);
  const sz3 = fs.statSync(path.join(outDir, 'nacional', 'por-mun.json')).size;
  console.log(`  · nacional/por-mun.json (${fmtMB(sz3)}, ${munRows.length} muns)`);

  // ─── departamentos/{dep}/municipios.json (full por depto) ──────
  let totalMunsBytes = 0;
  for (const [dep, arr] of munFullByDep){
    arr.sort((a,b) => a.mun.localeCompare(b.mun));
    const fp = path.join(outDir, 'departamentos', dep, 'municipios.json');
    writeJson(fp, arr);
    totalMunsBytes += fs.statSync(fp).size;
  }
  console.log(`  · departamentos/*/municipios.json: ${fmtMB(totalMunsBytes)} totales`);

  // ─── departamentos/{dep}/{mun}/puestos.json + mesas.json ──────
  let totalPuesBytes = 0, totalMesaBytes = 0;
  for (const [munKey, puMap] of porPuestoByMun){
    const [dep, mun] = munKey.split('-');
    const puestos = [];
    for (const [puKey, scope] of puMap){
      const [zz, pp] = puKey.split('-');
      const ser = simpleScopeSerialize(scope, 6);
      puestos.push({
        zz, pp,
        votos_validos: ser.votos_validos,
        votos_totales: ser.votos_totales,
        especiales: ser.especiales,
        partidos_top: ser.partidos,
      });
    }
    puestos.sort((a,b) => a.zz.localeCompare(b.zz) || a.pp.localeCompare(b.pp));
    const fp = path.join(outDir, 'departamentos', dep, mun, 'puestos.json');
    writeJson(fp, puestos);
    totalPuesBytes += fs.statSync(fp).size;
  }
  for (const [munKey, meMap] of porMesaByMun){
    const [dep, mun] = munKey.split('-');
    const mesas = [];
    for (const [meKey, scope] of meMap){
      const [zz, pp, mesa] = meKey.split('-');
      const ser = simpleScopeSerialize(scope, 6);
      mesas.push({
        zz, pp, mesa,
        votos_validos: ser.votos_validos,
        votos_totales: ser.votos_totales,
        especiales: ser.especiales,
        partidos_top: ser.partidos,
      });
    }
    mesas.sort((a,b) =>
      a.zz.localeCompare(b.zz) || a.pp.localeCompare(b.pp) || a.mesa.localeCompare(b.mesa));
    const fp = path.join(outDir, 'departamentos', dep, mun, 'mesas.json');
    writeJson(fp, mesas);
    totalMesaBytes += fs.statSync(fp).size;
  }
  console.log(`  · departamentos/*/*/puestos.json: ${fmtMB(totalPuesBytes)} totales`);
  console.log(`  · departamentos/*/*/mesas.json:   ${fmtMB(totalMesaBytes)} totales`);

  console.log(`\n[ok] ${((Date.now() - t0) / 1000).toFixed(1)}s totales\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
