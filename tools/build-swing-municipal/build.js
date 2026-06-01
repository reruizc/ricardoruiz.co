#!/usr/bin/env node
// build-swing-municipal — calcula el giro de la izquierda por municipio:
//   swing = Cepeda 2026 (% válidos+blanco) − Petro 2022 (% válidos, 1ª vuelta)
//
// Por qué un script y no el navegador: rankear el top nacional exige el % de
// Cepeda en TODOS los ~1.100 municipios, y el mapagan solo trae el ganador.
// Hay que barrer municipio por municipio (≈1.100 fetches). Eso se hace UNA vez
// aquí (no desde cada navegador) y se publica un JSON estático que la página lee.
//
// Fuentes:
//   - 2026 en vivo: worker registraduria-proxy /presidente/{dep} (lista de muns +
//     nombres) y /presidente/{amb} (votos por candidato del municipio).
//   - 2022: histórico por-mun.json en S3 (Petro por municipio).
//
// Uso:   node tools/build-swing-municipal/build.js
// Salida: Bases de datos/output_swing/swing-municipal.json
// Subir:  aws s3 cp "Bases de datos/output_swing/swing-municipal.json" \
//           "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/swing/swing-municipal.json" \
//           --content-type application/json --cache-control "public, max-age=300"

const fs = require('fs');
const path = require('path');

const WORKER = 'https://registraduria-proxy.reruizc.workers.dev';
const HIST22_MUN = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/historicos/pres-2022-v1/por-mun.json';
const HIST22_DEPTO = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/historicos/pres-2022-v1/por-depto.json';
const CEPEDA_CODPAR = '7';
const CONCURRENCY = 8;
const OUT = path.join(__dirname, '..', '..', 'Bases de datos', 'output_swing', 'swing-municipal.json');

const DANE_DEP = {
  '60':'Amazonas','01':'Antioquia','40':'Arauca','56':'San Andrés','03':'Atlántico',
  '16':'Bogotá D.C.','05':'Bolívar','07':'Boyacá','09':'Caldas','44':'Caquetá','46':'Casanare',
  '11':'Cauca','12':'Cesar','17':'Chocó','13':'Córdoba','15':'Cundinamarca','50':'Guainía',
  '54':'Guaviare','19':'Huila','48':'La Guajira','21':'Magdalena','52':'Meta','23':'Nariño',
  '25':'Norte de Santander','64':'Putumayo','24':'Risaralda','26':'Quindío','27':'Santander',
  '28':'Sucre','29':'Tolima','31':'Valle del Cauca','68':'Vaupés','72':'Vichada',
};

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const norm = s => (s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().trim();

async function getJSON(url, tries = 3){
  for (let t = 0; t < tries; t++){
    try {
      const res = await fetch(url + (url.includes('?')?'&':'?') + 't=' + Date.now(), {
        headers: { 'User-Agent': UA, 'Accept': 'application/json' },
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return await res.json();
    } catch (e) { if (t === tries-1) throw e; await new Promise(r=>setTimeout(r, 400*(t+1))); }
  }
}

// Petro 2022 (%) desde un bloque del histórico.
function petroPctFromBlk(blk){
  if (!blk || !blk.candidatos) return null;
  const p = Object.values(blk.candidatos).find(c => /petro/.test(norm(c.nombre)));
  return p ? p.pct : null;
}
function petro22Pct(hist, amb){ return petroPctFromBlk(hist[amb.slice(0,2) + '-' + amb.slice(2)]); }
function petro22Dep(histDep, cod){ return petroPctFromBlk(histDep[cod] || histDep[String(parseInt(cod,10))]); }

// Nombre del ganador (mayor vot) de un partotabla act.
function winnerName(a){
  const cantos = (a.cantotabla || []).filter(c => !/solo por la lista/i.test(c.nomcan||''));
  const top = cantos.slice().sort((x,y)=>(parseInt(y.vot)||0)-(parseInt(x.vot)||0))[0];
  return top ? `${top.nomcan||''} ${top.apecan||''}`.trim() : (a.nompar || ('cod '+a.codpar));
}
// Stats de un ámbito (depto o municipio): Cepeda 2026 (% válidos+blanco), tamaño y ganador.
function statsFrom(ds){
  const cam = (ds.camaras || []).find(c => c && (c.partotabla||[]).length);
  if (!cam) return null;
  let sum = 0, cep = 0, winA = null, winV = -1;
  for (const p of cam.partotabla){ const a = p.act || p; const v = parseInt(a.vot) || 0; sum += v;
    if (String(a.codpar) === CEPEDA_CODPAR) cep = v;
    if (v > winV){ winV = v; winA = a; } }
  const t = (ds.totales && ds.totales.act) || {};
  const blanco = parseInt(t.votblan || t.votbla) || 0;
  const base = sum + blanco;
  if (base <= 0) return null;
  return { cep26: cep/base*100, val26: base, mesesc: parseInt(t.mesesc)||0,
    win: winA ? { n: winnerName(winA), pct: winV/base*100 } : null };
}

async function pool(items, fn){
  const out = []; let i = 0;
  async function w(){ while (i < items.length){ const idx = i++; out[idx] = await fn(items[idx], idx); } }
  await Promise.all(Array.from({length:CONCURRENCY}, w));
  return out;
}

(async () => {
  console.log('1) histórico 2022 (municipio + departamento)…');
  const [hist, histDep] = await Promise.all([getJSON(HIST22_MUN), getJSON(HIST22_DEPTO)]);
  console.log('   muns 2022:', Object.keys(hist).length, '· deptos 2022:', Object.keys(histDep).length);

  console.log('2) municipios + stats por departamento 2026…');
  const deps = Object.keys(DANE_DEP);
  let boletin = null;
  const munList = [], depStats = {};
  try { const nac = await getJSON(`${WORKER}/presidente`); if (nac.numact != null) boletin = nac.numact; } catch(_){}   // boletín NACIONAL (no el contador por depto)
  await pool(deps, async (dep) => {
    try {
      const ds = await getJSON(`${WORKER}/presidente/${dep}`);
      depStats[dep] = statsFrom(ds);   // Cepeda 2026 + ganador del depto
      const mg = ds.camaras && ds.camaras[0] && ds.camaras[0].mapagan;
      if (Array.isArray(mg)) for (const e of mg){ const amb = String(e.amb||''); if (amb.length===5) munList.push({ amb, mun: e.nombre || amb, dep: DANE_DEP[dep] }); }
    } catch(e){ console.log('   dep', dep, 'fail:', e.message); }
  });
  console.log('   municipios 2026:', munList.length);

  // deps[]: swing + ganador por departamento
  const depsOut = [];
  for (const dep of deps){ if (dep === '88') continue; const s = depStats[dep]; if (!s || s.cep26 == null) continue;
    const pet = petro22Dep(histDep, dep); if (pet == null) continue;
    depsOut.push({ cod:dep, dep:DANE_DEP[dep], cep26:+s.cep26.toFixed(1), petro22:+pet.toFixed(1), swing:+(s.cep26-pet).toFixed(1),
      win: s.win ? { n:s.win.n, pct:+s.win.pct.toFixed(1) } : null });
  }
  depsOut.sort((a,b) => b.swing - a.swing);

  console.log(`3) barrido de ${munList.length} municipios (Cepeda 2026)… [~varios min]`);
  let done = 0, ok = 0;
  await pool(munList, async (m) => {
    try {
      const ds = await getJSON(`${WORKER}/presidente/${m.amb}`);
      const c = statsFrom(ds);
      if (c){ m.cep26 = c.cep26; m.val26 = c.val26; m.mesesc = c.mesesc; m.win = c.win; ok++; }
    } catch(_){}
    if (++done % 100 === 0) console.log(`   ${done}/${munList.length} (ok ${ok})`);
  });

  console.log('4) cruce con Petro 2022 + swing…');
  const rows = [];
  for (const m of munList){
    if (m.cep26 == null) continue;
    const pet = petro22Pct(hist, m.amb);
    if (pet == null) continue;
    rows.push({ amb:m.amb, mun:m.mun, dep:m.dep, cep26:+m.cep26.toFixed(1), petro22:+pet.toFixed(1), swing:+(m.cep26 - pet).toFixed(1), val26:m.val26,
      win: m.win ? { n:m.win.n, pct:+m.win.pct.toFixed(1) } : null });
  }
  rows.sort((a,b) => b.swing - a.swing);

  const out = { v: new Date().toISOString(), boletin, total: rows.length, muns: rows, deps: depsOut };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out));
  console.log(`\n✓ ${rows.length} municipios con swing → ${OUT}`);
  console.log('  Top +5:', rows.slice(0,5).map(r=>`${r.mun}(${r.dep}) +${r.swing}`).join(' · '));
  console.log('  Top −5:', rows.slice(-5).reverse().map(r=>`${r.mun}(${r.dep}) ${r.swing}`).join(' · '));
})();
