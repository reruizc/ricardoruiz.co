#!/usr/bin/env node
// tools/build-risaralda/build-camara.js
//
// Extrae Cámara 2026 de Risaralda (cod 24) desde el dep-24.json ya
// publicado en S3, con enfoque alternativo (Verde + Pacto + izq). Produce
// métricas por municipio + Pereira por comuna + Pereira por barrio (PIP) +
// drill por puesto (todos los muns). Todo sale de UN solo JSON (los puestos
// vienen anidados por comuna en dep-24.json).
//
// Uso: node tools/build-risaralda/build-camara.js
//
// Salidas en Bases de datos/output_risaralda/:
//   risaralda-camara-2026.json            municipio + Pereira comuna
//   risaralda-camara-2026-puestos.json    drill por puesto × mun
//   risaralda-camara-2026-pereira-barrios.json  Pereira por barrio (PIP)

const fs = require('fs');
const path = require('path');

const ROOT = '/Users/ricardoruiz/ricardoruiz.co';
const DEP24_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/camara/dep-24.json';
const PEREIRA_BARRIOS_GEO = path.join(ROOT, 'Bases de datos/output_pacto_1v_2026/geo/PEREIRA-BARRIOS.json');
const GEOREF = path.join(ROOT, 'Bases de datos/PUESTOS_GEOREF.csv');
const OUT_DIR = path.join(ROOT, 'Bases de datos/output_risaralda');
const PEREIRA_MUN = '001';

function norm(s){ return String(s||'').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/"+/g,'').replace(/\s+/g,' ').trim(); }

// ─── CLASIFICADOR ALTERNATIVO · CÁMARA 2026 (explícito) ───────────────
// En Cámara, "PACTO POR RISARALDA" (lista cerrada, 74.6k, la más votada)
// ES el Pacto Histórico → alternativo. OJO: distinto de territorial, donde
// "PACTO POR X" eran movimientos locales. "POR RISARALDA" (sin PACTO) NO es
// del bloque.
const ALT_EXACT = new Set([
  'PACTO POR RISARALDA',
]);
const ALT_TOKEN = [
  'ALIANZA VERDE',
  'ALTERNATIVO INDIGENA Y SOCIAL', 'MAIS',
  'UNIDAD EN MINGA',
  'FRENTE AMPLIO RISARALDA',
  'COLOMBIA HUMANA', 'UNION PATRIOTICA',
];
function esAltCamara(nombre){
  const n = norm(nombre);
  if (ALT_EXACT.has(n)) return true;
  if (n === 'POR RISARALDA') return false;          // movimiento regional, no bloque
  if (n.includes('ECOLOGISTA')) return false;
  return ALT_TOKEN.some(t => n.includes(t));
}

// ─── PIP + georef (igual que build.js) ────────────────────────────────
function pointInRing(x,y,r){let i,j,inside=false;for(i=0,j=r.length-1;i<r.length;j=i++){const xi=r[i][0],yi=r[i][1],xj=r[j][0],yj=r[j][1];if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))inside=!inside;}return inside;}
function pointInPolygon(x,y,poly){if(!pointInRing(x,y,poly[0]))return false;for(let k=1;k<poly.length;k++)if(pointInRing(x,y,poly[k]))return false;return true;}
function loadPereiraBarrios(){
  const gj=JSON.parse(fs.readFileSync(PEREIRA_BARRIOS_GEO,'utf8'));
  return (gj.features||[]).map((f,i)=>{const p=f.properties||{};const nm=p.NOMBRE||p.nombre||`Barrio ${i}`;const g=f.geometry||{};let polys=[];if(g.type==='Polygon')polys=[g.coordinates];else if(g.type==='MultiPolygon')polys=g.coordinates;return {id:String(i),nombre:String(nm).toUpperCase().trim(),polys};});
}
function findBarrio(lat,lon,feats){for(const f of feats)for(const poly of f.polys)if(pointInPolygon(lon,lat,poly))return f;return null;}
function pad2(v){return String(parseInt(v||'0',10)).padStart(2,'0');}
// Censo electoral por municipio (dep 24) desde PUESTOS_GEOREF (mujeres+hombres).
function loadCensoByMun(){
  const lines=fs.readFileSync(GEOREF,'utf8').split(/\r?\n/);
  const H=lines[0].replace(/^﻿/,'').split(';').map(s=>s.trim());
  const I=n=>H.indexOf(n);
  const I_COD=I('CÓDIGO COMPLETO'),I_MUJ=I('MUJERES'),I_HOM=I('HOMBRES');
  const byMun={};
  for(let i=1;i<lines.length;i++){const p=lines[i].split(';');const code=(p[I_COD]||'').replace(/"/g,'');if(code.length<9)continue;if(code.slice(0,2)!=='24')continue;const mun=String(parseInt(code.slice(2,5),10));byMun[mun]=(byMun[mun]||0)+(parseInt(p[I_MUJ]||'0',10)||0)+(parseInt(p[I_HOM]||'0',10)||0);}
  return byMun;
}
// Lat/lon por puesto (dep 24) → `${mun}-${zz}-${pp}`.
function loadGerefAll(){
  const lines=fs.readFileSync(GEOREF,'utf8').split(/\r?\n/);
  const H=lines[0].replace(/^﻿/,'').split(';').map(s=>s.trim());
  const I=n=>H.indexOf(n);
  const I_COD=I('CÓDIGO COMPLETO'),I_LAT=I('LATITUD'),I_LON=I('LONGITUD'),I_NOMP=I('NOMBRE PUESTO');
  const map=new Map();
  for(let i=1;i<lines.length;i++){const p=lines[i].split(';');const code=(p[I_COD]||'').replace(/"/g,'');if(code.length<9)continue;if(code.slice(0,2)!=='24')continue;const mun=String(parseInt(code.slice(2,5),10));const zz=pad2(code.slice(5,7)),pp=pad2(code.slice(7,9));map.set(`${mun}-${zz}-${pp}`,{lat:parseFloat(p[I_LAT]),lon:parseFloat(p[I_LON]),nombre:(I_NOMP>=0?(p[I_NOMP]||''):'').replace(/"/g,'').trim()});}
  return map;
}
// Cifra repartidora (D'Hondt) sobre listas que superan el umbral.
// Cámara Risaralda: 4 curules. Umbral = 50% del cuociente (elige >2).
function curulesCamara(partidos, validos, seats){
  const cuociente = validos/seats, umbral = cuociente*0.5;
  let elegibles = partidos.filter(p=>p.votos>=umbral);
  if (!elegibles.length) elegibles = partidos.slice();
  const arr = elegibles.map(p=>({partido:p.nombre, votos:p.votos, alt:p.alt, curules:0}));
  for(let i=0;i<seats;i++){ let bi=-1,bq=-1; for(let j=0;j<arr.length;j++){const q=arr[j].votos/(arr[j].curules+1); if(q>bq){bq=q;bi=j;}} if(bi>=0)arr[bi].curules++; }
  return arr.filter(p=>p.curules>0).sort((a,b)=>b.curules-a.curules||b.votos-a.votos);
}
function loadGeorefPereira(feats){
  const lines=fs.readFileSync(GEOREF,'utf8').split(/\r?\n/);
  const H=lines[0].replace(/^﻿/,'').split(';').map(s=>s.trim());
  const I=n=>H.indexOf(n);
  const I_COD=I('CÓDIGO COMPLETO'),I_LAT=I('LATITUD'),I_LON=I('LONGITUD');
  const map=new Map(); let nb=0,np=0;
  for(let i=1;i<lines.length;i++){const p=lines[i].split(';');const code=(p[I_COD]||'').replace(/"/g,'');if(code.length<9)continue;if(code.slice(0,5)!=='24001')continue;const zz=pad2(code.slice(5,7)),pp=pad2(code.slice(7,9));const lat=parseFloat(p[I_LAT]),lon=parseFloat(p[I_LON]);np++;let bid=null,bnom=null;if(feats&&Number.isFinite(lat)&&Number.isFinite(lon)){const b=findBarrio(lat,lon,feats);if(b){bid=b.id;bnom=b.nombre;nb++;}}map.set(`${zz}-${pp}`,{lat,lon,bid,bnom});}
  console.log(`  · georef Pereira: ${map.size} puestos · PIP ${nb}/${np}`);
  return map;
}

// Agrega un dict {partido:votos} a un acumulador de scope.
function addPartidos(acc, partidos){
  for (const [nombre, votos] of Object.entries(partidos||{})){
    if (!votos) continue;
    let e = acc.get(nombre); if(!e){ e={nombre, votos:0, alt:esAltCamara(nombre)}; acc.set(nombre,e); }
    e.votos += votos;
  }
}
// Aplana el dict candidatos {partido:[{nombre,votos}]} → lista ordenada.
// Las listas cerradas (Pacto) no traen candidatos individuales → sólo
// aparecen en `partidos`.
function flattenCands(candDict, validos){
  const arr=[];
  for (const [partido, list] of Object.entries(candDict||{})){
    for (const c of (list||[])){ arr.push({ nombre:c.nombre, partido, votos:c.votos||0, alt:esAltCamara(partido) }); }
  }
  arr.sort((a,b)=>b.votos-a.votos);
  for (const c of arr) c.pct = validos>0 ? +(c.votos/validos*100).toFixed(2):0;
  return arr.slice(0,400);
}
function summarize(acc){
  const arr=[...acc.values()].sort((a,b)=>b.votos-a.votos);
  let val=0,alt=0; for(const p of arr){ val+=p.votos; if(p.alt)alt+=p.votos; }
  for(const p of arr) p.pct = val>0 ? +(p.votos/val*100).toFixed(2) : 0;
  const lider = arr[0]||null;
  return { validos:val, alt_votos:alt, alt_pct: val>0?+(alt/val*100).toFixed(2):0,
           lider: lider?{partido:lider.nombre,votos:lider.votos,pct:lider.pct,alt:lider.alt}:null,
           partidos: arr };
}

async function main(){
  fs.mkdirSync(OUT_DIR,{recursive:true});
  console.log('▶ Cámara 2026 · Risaralda');
  const feats = loadPereiraBarrios();
  const georef = loadGeorefPereira(feats);
  const censoByMun = loadCensoByMun();
  const gerefAll = loadGerefAll();

  let d;
  try { const r = await fetch(DEP24_URL); d = await r.json(); }
  catch(e){ console.error('No pude bajar dep-24.json:', e.message); process.exit(1); }

  const MUNS = {};
  const out = {
    eleccion:'camara-2026', depcod:'24', dep:'RISARALDA',
    generated:new Date().toISOString().slice(0,10),
    alt_definicion:'Verde + Pacto (PACTO POR RISARALDA) + MAIS + Frente Amplio + Unidad en Minga',
    muns:{}, dep_resumen:null, por_mun:{}, pereira_comunas:{},
  };

  // Depto
  out.dep_resumen = summarize((()=>{const a=new Map(); addPartidos(a,d.partidos); return a;})());
  out.dep_resumen.candidatos = flattenCands(d.candidatos, out.dep_resumen.validos);
  out.dep_resumen.votantes = d.votant||0;
  out.censo = Object.values(censoByMun).reduce((a,b)=>a+b,0);
  // Curules de Cámara (Risaralda elige 4) por cifra repartidora.
  out.dep_resumen.curules = curulesCamara(out.dep_resumen.partidos, out.dep_resumen.validos, 4);
  out.dep_resumen.alt_curules = out.dep_resumen.curules.filter(c=>c.alt).reduce((s,c)=>s+c.curules,0);
  out.dep_resumen.seats = 4;

  const porPuesto = {};    // mun(int) → 'zz-pp' → metric
  const barrioAcc = {};    // bid → Map partido
  const barrioMeta = new Map();

  for (const m of d.municipios){
    const munCod = m.cod;                    // '001','008'...
    const munInt = String(parseInt(munCod,10));
    MUNS[munInt] = m.nombre;
    out.muns[munInt] = { nombre:m.nombre, censo:censoByMun[munInt]||0 };
    // municipio
    const accM=new Map(); addPartidos(accM,m.partidos);
    out.por_mun[munInt] = summarize(accM);
    out.por_mun[munInt].candidatos = flattenCands(m.candidatos, out.por_mun[munInt].validos);
    out.por_mun[munInt].votantes = m.votant||0;

    // comunas → puestos
    porPuesto[munInt] = {};
    for (const c of (m.comunas||[])){
      // Pereira: comuna-level summary
      if (munCod===PEREIRA_MUN){
        const accC=new Map(); addPartidos(accC,c.partidos);
        const comName = c.nombre || c.com_nom || c.com_cod;
        out.pereira_comunas[c.com_cod||c.cod] = { nombre:comName, ...summarize(accC) };
      }
      for (const pu of (c.puestos||[])){
        const zz=pad2(pu.zon_cod), pp=pad2(pu.pue_cod_raw||(pu.pue_cod||'').split('-').pop());
        const accP=new Map(); addPartidos(accP,pu.partidos);
        const s=summarize(accP);
        const ga=gerefAll.get(`${munInt}-${zz}-${pp}`);
        porPuesto[munInt][`${zz}-${pp}`] = { validos:s.validos, alt_votos:s.alt_votos, alt_pct:s.alt_pct,
          lider: s.lider?{partido:s.lider.partido,pct:s.lider.pct,alt:s.lider.alt}:null,
          lat: ga&&Number.isFinite(ga.lat)?+ga.lat.toFixed(5):null, lon: ga&&Number.isFinite(ga.lon)?+ga.lon.toFixed(5):null,
          nombre: ga&&ga.nombre?ga.nombre:null };
        // Pereira barrio
        if (munCod===PEREIRA_MUN){
          const g=georef.get(`${zz}-${pp}`);
          if (g && g.bid){
            const acc = barrioAcc[g.bid] ||= new Map(); addPartidos(acc, pu.partidos);
            let meta=barrioMeta.get(g.bid); if(!meta){meta={nombre:g.bnom,latSum:0,lonSum:0,w:0};barrioMeta.set(g.bid,meta);}
            const w=pu.votval||0; meta.latSum+=g.lat*w; meta.lonSum+=g.lon*w; meta.w+=w;
          }
        }
      }
    }
    // recortar partidos por_mun a top 12 para tamaño
    out.por_mun[munInt].partidos = out.por_mun[munInt].partidos.slice(0,14);
  }
  out.dep_resumen.partidos = out.dep_resumen.partidos.slice(0,16);
  for (const k in out.pereira_comunas) out.pereira_comunas[k].partidos = out.pereira_comunas[k].partidos.slice(0,10);

  fs.writeFileSync(path.join(OUT_DIR,'risaralda-camara-2026.json'), JSON.stringify(out));
  fs.writeFileSync(path.join(OUT_DIR,'risaralda-camara-2026-puestos.json'), JSON.stringify(porPuesto));

  const bo={_meta:{}};
  for(const [bid,m] of barrioMeta) bo._meta[bid]={nombre:m.nombre,lat:m.w?+(m.latSum/m.w).toFixed(6):null,lon:m.w?+(m.lonSum/m.w).toFixed(6):null};
  bo.camara={};
  for(const [bid,acc] of Object.entries(barrioAcc)){ const s=summarize(acc); bo.camara[bid]={validos:s.validos,alt_votos:s.alt_votos,alt_pct:s.alt_pct,lider:s.lider}; }
  fs.writeFileSync(path.join(OUT_DIR,'risaralda-camara-2026-pereira-barrios.json'), JSON.stringify(bo));

  console.log(`  ✓ risaralda-camara-2026.json · dep alt ${out.dep_resumen.alt_pct}% · lider ${out.dep_resumen.lider.partido}`);
  console.log(`  ✓ puestos.json · ✓ pereira-barrios.json · ${barrioMeta.size} barrios`);
}
main().catch(e=>{console.error(e);process.exit(1);});
