#!/usr/bin/env node
// tools/build-medellin-comuna-congreso.js
//
// Procesa un archivo MMV (formato DEPTOS_DECLARADOS, Registraduría 2026) de
// Antioquia y produce agregados a nivel comuna política de Medellín (16 + CORR
// + OTROS) para tres corporaciones del 2026:
//   - Senado (CORCODIGO=01)
//   - Cámara (CORCODIGO=02)
//   - Consultas presidenciales marzo 2026 (CORCODIGO=06):
//       PAR=0100 Consulta de las Soluciones (Claudia López ganó)
//       PAR=0200 La Gran Consulta por Colombia (Paloma Valencia ganó)
//       PAR=0300 Frente por la Vida (Roy Barreras ganó; Quintero compitió)
//
// Filtro: DEP=01, MUN=001 (Medellín, códigos Registraduría).
//
// Uso:
//   node tools/build-medellin-comuna-congreso.js <archivo.csv> <out-dir>
//
// Salida:
//   {outDir}/senado/{resumen,por-comuna}.json     (partidos, sin candidato)
//   {outDir}/camara/{resumen,por-comuna}.json     (partidos)
//   {outDir}/consultas/{resumen,por-comuna}.json  (3 consultas × candidatos)
//
// Notas:
// - CAN=000 = voto solo-logo del partido. CAN=001..099 = candidatos preferentes.
//   Para Senado/Cámara sumamos TODO dentro del PAR. Para consultas agregamos
//   por candidato (CAN), porque la señal directa es por nombre.
// - PAR=0000 + CAN ∈ {996,997,998,999} = especiales nacionales (blanco, nulos,
//   no marcados) — se cuentan aparte y NO se incluyen en votos válidos.
// - ZONA→comuna política viene del mapeo derivado de PUESTOS_GEOREF.csv,
//   idéntico al usado por tools/build-medellin-historicos.js.

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const FILTRO_DEP = '01';
const FILTRO_MUN = '001';

const COR_TO_KEY = {
  'SENADO': 'senado',
  'CAMARA': 'camara',
  'CAMARA DE REPRESENTANTES': 'camara',
  'CÁMARA DE REPRESENTANTES': 'camara',
  'CONSULTAS': 'consultas',
};

const SPECIAL_CODES = {
  '996': 'blanco',
  '997': 'nulos',
  '998': 'no_marcados',
  '999': 'no_marcados',
};

const ZZ_TO_COMUNA = {
  '01':'01','02':'01',
  '03':'02','04':'02',
  '05':'03','06':'03',
  '07':'04','08':'04',
  '09':'05','10':'05',
  '11':'06','12':'06',
  '13':'07','14':'07',
  '15':'08','16':'08',
  '17':'09','18':'09',
  '19':'10','20':'10',
  '21':'11','22':'11',
  '23':'12','24':'12',
  '25':'13','26':'13',
  '27':'14','28':'14',
  '29':'15',
  '30':'16','31':'16','32':'16',
  '99':'CORR',
  '90':'OTROS','98':'OTROS',
};

const COMUNA_NOMBRE = {
  '01':'Popular','02':'Santa Cruz','03':'Manrique','04':'Aranjuez',
  '05':'Castilla','06':'Doce de Octubre','07':'Robledo','08':'Villa Hermosa',
  '09':'Buenos Aires','10':'La Candelaria','11':'Laureles Estadio',
  '12':'La América','13':'San Javier','14':'El Poblado','15':'Guayabal','16':'Belén',
  'CORR':'Corregimientos','OTROS':'Otros / Exterior',
};

const COMUNA_ORDER = ['01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','CORR','OTROS'];

const CONSULTA_NOMBRE_CORTO = {
  '0100': 'soluciones',
  '0200': 'gran',
  '0300': 'frente',
};
const CONSULTA_NOMBRE_LARGO = {
  '0100': 'Consulta de las Soluciones (centro · Claudia López)',
  '0200': 'La Gran Consulta por Colombia (derecha · Paloma Valencia)',
  '0300': 'Frente por la Vida (centro-izq · Roy Barreras / Quintero)',
};

function mapZZ(zz){ return ZZ_TO_COMUNA[zz] || 'OTROS'; }

function parseHeaderLine(line){
  const clean = line.replace(/^\uFEFF/, '');
  const cols = clean.split(';').map(s => s.trim());
  const map = {};
  cols.forEach((c, i) => { map[c] = i; });
  const required = ['DEP','MUN','ZONA','PUESTO','MESA','CORNOMBRE','PAR','PARNOMBRE','CAN','CANNOMBRE','VOTOS'];
  const missing = required.filter(r => !(r in map));
  if (missing.length){
    throw new Error(`Header sin columnas requeridas: ${missing.join(', ')}`);
  }
  return map;
}

// ---------- Senado / Cámara ----------
function emptyPartidoScope(){ return { partidos: new Map(), especiales: new Map() }; }

function accumPartido(scope, parCode, parNombre, canCode, votos){
  const sp = SPECIAL_CODES[canCode];
  if (sp){
    scope.especiales.set(sp, (scope.especiales.get(sp) || 0) + votos);
    return;
  }
  let p = scope.partidos.get(parCode);
  if (!p){
    p = { cod: parCode, nombre: parNombre, votos: 0 };
    scope.partidos.set(parCode, p);
  }
  p.votos += votos;
  if (!p.nombre && parNombre) p.nombre = parNombre;
}

function serializePartidoScope(scope){
  const partidos = [];
  let validos = 0;
  for (const p of scope.partidos.values()){
    partidos.push({ cod: p.cod, nombre: p.nombre, votos: p.votos });
    validos += p.votos;
  }
  partidos.sort((a,b) => b.votos - a.votos);
  for (const p of partidos){
    p.pct = validos > 0 ? +(p.votos / validos * 100).toFixed(3) : 0;
  }
  const especiales = {};
  for (const [k,v] of scope.especiales) especiales[k] = v;
  const totalEsp = Object.values(especiales).reduce((s,v) => s+v, 0);
  return {
    votos_validos: validos,
    votos_totales: validos + totalEsp,
    especiales,
    partidos,
  };
}

// ---------- Consultas (por candidato dentro de cada consulta) ----------
function emptyConsultaScope(){
  return { consultas: new Map() }; // PAR → { nombre, cands: Map<canCode,{nombre,votos}>, especiales: Map }
}

function ensureConsulta(scope, parCode, parNombre){
  let c = scope.consultas.get(parCode);
  if (!c){
    c = { cod: parCode, nombre: parNombre, cands: new Map(), especiales: new Map() };
    scope.consultas.set(parCode, c);
  }
  if (!c.nombre && parNombre) c.nombre = parNombre;
  return c;
}

function accumConsulta(scope, parCode, parNombre, canCode, canNombre, votos){
  // Especiales de consulta vienen con PAR=0000 (CANDIDATOS TOTALES) y CAN ∈ blanco/nulos/no_marcados.
  // Los acumulamos en un slot 'totales' aparte.
  if (parCode === '0000'){
    let c = ensureConsulta(scope, '0000', 'TOTALES CONSULTA');
    const sp = SPECIAL_CODES[canCode] || 'otros';
    c.especiales.set(sp, (c.especiales.get(sp) || 0) + votos);
    return;
  }
  const c = ensureConsulta(scope, parCode, parNombre);
  // CAN=000 (voto sólo logo de la consulta) lo ignoramos: en consultas el voto
  // de interés es por candidato. Si quisiéramos podríamos guardarlo bajo cod 000.
  if (canCode === '000') return;
  let cd = c.cands.get(canCode);
  if (!cd){
    cd = { cod: canCode, nombre: canNombre, votos: 0 };
    c.cands.set(canCode, cd);
  }
  cd.votos += votos;
  if (!cd.nombre && canNombre) cd.nombre = canNombre;
}

function serializeConsultaScope(scope){
  const out = {};
  for (const [par, c] of scope.consultas){
    if (par === '0000') continue; // los totales/especiales se exponen aparte
    const cands = Array.from(c.cands.values()).sort((a,b) => b.votos - a.votos);
    const validos = cands.reduce((s,c) => s+c.votos, 0);
    for (const cd of cands){
      cd.pct = validos > 0 ? +(cd.votos / validos * 100).toFixed(3) : 0;
    }
    out[par] = {
      cod: par,
      nombre: c.nombre,
      slug: CONSULTA_NOMBRE_CORTO[par] || null,
      votos_validos: validos,
      candidatos: cands,
    };
  }
  // Totales / especiales de consultas (suma de blanco/nulos/no_marcados)
  const totales = scope.consultas.get('0000');
  if (totales){
    const especiales = {};
    for (const [k,v] of totales.especiales) especiales[k] = v;
    out._especiales = especiales;
  }
  return out;
}

// ---------- Procesamiento principal ----------
async function processCsv(csvPath){
  const stream = fs.createReadStream(csvPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  let idx = null;
  let rowsRead = 0, rowsKept = 0;

  const ciudad = {
    senado: emptyPartidoScope(),
    camara: emptyPartidoScope(),
    consultas: emptyConsultaScope(),
  };
  const porComuna = {
    senado: new Map(),     // comuna → emptyPartidoScope
    camara: new Map(),
    consultas: new Map(),  // comuna → emptyConsultaScope
  };

  function ensureCom(map, key, factory){
    let v = map.get(key);
    if (!v){ v = factory(); map.set(key, v); }
    return v;
  }

  for await (const line of rl){
    if (!line) continue;
    if (idx === null){
      idx = parseHeaderLine(line);
      continue;
    }
    rowsRead++;
    const cols = line.split(';');
    const dep = (cols[idx.DEP] || '').trim();
    const mun = (cols[idx.MUN] || '').trim();
    if (dep !== FILTRO_DEP || mun !== FILTRO_MUN) continue;

    const corNombre = (cols[idx.CORNOMBRE] || '').trim().toUpperCase();
    const corKey = COR_TO_KEY[corNombre];
    if (!corKey) continue;

    const zz = (cols[idx.ZONA] || '').trim().padStart(2, '0');
    const comuna = mapZZ(zz);
    const parCode = (cols[idx.PAR] || '').trim();
    const parNombre = (cols[idx.PARNOMBRE] || '').trim();
    const canCode = (cols[idx.CAN] || '').trim();
    const canNombre = (cols[idx.CANNOMBRE] || '').trim();
    const votos = parseInt(cols[idx.VOTOS] || '0', 10) || 0;
    if (votos === 0) continue;
    rowsKept++;

    if (corKey === 'consultas'){
      accumConsulta(ciudad.consultas, parCode, parNombre, canCode, canNombre, votos);
      const cs = ensureCom(porComuna.consultas, comuna, emptyConsultaScope);
      accumConsulta(cs, parCode, parNombre, canCode, canNombre, votos);
    } else {
      accumPartido(ciudad[corKey], parCode, parNombre, canCode, votos);
      const cs = ensureCom(porComuna[corKey], comuna, emptyPartidoScope);
      accumPartido(cs, parCode, parNombre, canCode, votos);
    }
  }

  return { ciudad, porComuna, rowsRead, rowsKept };
}

function writeJSON(filePath, obj){
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
}

function buildPorComunaPartido(map){
  const out = {};
  for (const k of COMUNA_ORDER){
    if (!map.has(k)) continue;
    out[k] = {
      cod: k,
      nombre: COMUNA_NOMBRE[k] || k,
      ...serializePartidoScope(map.get(k)),
    };
  }
  return out;
}

function buildPorComunaConsulta(map){
  const out = {};
  for (const k of COMUNA_ORDER){
    if (!map.has(k)) continue;
    out[k] = {
      cod: k,
      nombre: COMUNA_NOMBRE[k] || k,
      consultas: serializeConsultaScope(map.get(k)),
    };
  }
  return out;
}

async function main(){
  const args = process.argv.slice(2);
  if (args.length < 2){
    console.error('Uso: node tools/build-medellin-comuna-congreso.js <archivo.csv> <out-dir>');
    process.exit(1);
  }
  const [csvPath, outDir] = args;
  if (!fs.existsSync(csvPath)){
    console.error(`No existe el archivo: ${csvPath}`);
    process.exit(1);
  }

  const t0 = Date.now();
  console.log(`Leyendo ${csvPath} ...`);
  const { ciudad, porComuna, rowsRead, rowsKept } = await processCsv(csvPath);
  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`Procesadas ${rowsRead.toLocaleString()} filas, conservadas ${rowsKept.toLocaleString()} (Medellín) en ${elapsed}s.`);

  // Senado y Cámara
  for (const corp of ['senado', 'camara']){
    writeJSON(path.join(outDir, corp, 'resumen.json'), {
      meta: { fuente: path.basename(csvPath), filtro: { dep: FILTRO_DEP, mun: FILTRO_MUN }, corporacion: corp, generado: new Date().toISOString() },
      ...serializePartidoScope(ciudad[corp]),
    });
    writeJSON(path.join(outDir, corp, 'por-comuna.json'), {
      meta: { fuente: path.basename(csvPath), corporacion: corp, generado: new Date().toISOString() },
      por_comuna: buildPorComunaPartido(porComuna[corp]),
    });
  }

  // Consultas
  writeJSON(path.join(outDir, 'consultas', 'resumen.json'), {
    meta: { fuente: path.basename(csvPath), filtro: { dep: FILTRO_DEP, mun: FILTRO_MUN }, corporacion: 'consultas', generado: new Date().toISOString() },
    consultas: serializeConsultaScope(ciudad.consultas),
  });
  writeJSON(path.join(outDir, 'consultas', 'por-comuna.json'), {
    meta: { fuente: path.basename(csvPath), corporacion: 'consultas', generado: new Date().toISOString(), nombres: CONSULTA_NOMBRE_LARGO },
    por_comuna: buildPorComunaConsulta(porComuna.consultas),
  });

  // Reporte
  console.log(`\nArchivos generados en ${outDir}:`);
  for (const corp of ['senado', 'camara', 'consultas']){
    for (const f of ['resumen.json', 'por-comuna.json']){
      const p = path.join(outDir, corp, f);
      const sz = (fs.statSync(p).size / 1024).toFixed(1);
      console.log(`  ${p}  (${sz} KB)`);
    }
  }

  console.log(`\nTop 5 partidos Senado Medellín ciudad:`);
  const topS = serializePartidoScope(ciudad.senado).partidos.slice(0, 5);
  for (const p of topS){
    console.log(`  ${p.pct.toFixed(2).padStart(6)}%  ${p.votos.toLocaleString().padStart(8)}  ${p.nombre}`);
  }
  console.log(`\nTop 5 partidos Cámara Medellín ciudad:`);
  const topC = serializePartidoScope(ciudad.camara).partidos.slice(0, 5);
  for (const p of topC){
    console.log(`  ${p.pct.toFixed(2).padStart(6)}%  ${p.votos.toLocaleString().padStart(8)}  ${p.nombre}`);
  }
  console.log(`\nGanador en cada consulta marzo 2026 (Medellín ciudad):`);
  const consSer = serializeConsultaScope(ciudad.consultas);
  for (const par of ['0100','0200','0300']){
    const c = consSer[par];
    if (!c) continue;
    const top = c.candidatos[0];
    console.log(`  ${c.slug.padEnd(10)}  ${top.nombre.padEnd(40)}  ${top.votos.toLocaleString().padStart(8)} (${top.pct.toFixed(2)}%)  · total válidos ${c.votos_validos.toLocaleString()}`);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
