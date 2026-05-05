#!/usr/bin/env node
// tools/build-consultas-2026-historicos.js
//
// Convierte el agregado consultas/departamentos/{cod}/puestos.json (formato
// nuestro: anidado por consulta dentro de cada puesto) a 3 archivos en el
// formato `por-puesto.json` que consume loadHistoricosPue() del frontend:
//
//   {outDir}/consulta-2026-gran/por-puesto.json
//   {outDir}/consulta-2026-frente/por-puesto.json
//   {outDir}/consulta-2026-soluciones/por-puesto.json
//
// Nota: el código del candidato (COD_CAN 0001/0002/...) cambia entre
// departamentos para el mismo nombre. Para que el catálogo global del
// archivo sea consistente, uso el NOMBRE normalizado como "code". El
// frontend hace `codeToName[cod] = norm(cand.nombre)`, así que al usar
// nombre==code la igualdad se mantiene.
//
// Uso:
//   node tools/build-consultas-2026-historicos.js <input-dir> <out-dir>
//
// Ejemplo:
//   node tools/build-consultas-2026-historicos.js \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_agregados/consultas/departamentos" \
//     "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_historicos_puestos"

const fs = require('fs');
const path = require('path');

const CONSULTA_KEYS = ['gran', 'frente', 'soluciones'];

function norm(s){
  return String(s || '').trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function fmtKB(b){ return Math.round(b/1024) + ' KB'; }

function main(){
  const [, , inDir, outDir] = process.argv;
  if (!inDir || !outDir){
    console.error('Uso: node tools/build-consultas-2026-historicos.js <input-dir> <out-dir>');
    process.exit(1);
  }
  if (!fs.existsSync(inDir)){ console.error(`No existe: ${inDir}`); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });

  // Por consulta acumulamos: cands{nombreNorm: {nombre, votos}} y pues{key: {vv,vb,vn,vm,v:{nombreNorm:votos}}}
  const acc = {};
  for (const k of CONSULTA_KEYS) acc[k] = { cands: {}, pues: {} };

  const files = fs.readdirSync(inDir)
    .filter(d => /^\d{2}$/.test(d))
    .map(d => path.join(inDir, d, 'puestos.json'))
    .filter(fs.existsSync);

  console.log(`\n[build-consultas-2026-historicos] ${files.length} departamentos`);
  let totalPuestos = 0;

  for (const fp of files){
    const data = JSON.parse(fs.readFileSync(fp, 'utf8'));
    // Catálogo COD → nombre por consulta dentro de este depto
    const codToName = {};
    for (const ck of CONSULTA_KEYS){
      codToName[ck] = {};
      for (const [cod, nombre] of Object.entries(data.candidatos?.[ck] || {})){
        codToName[ck][cod] = norm(nombre || '');
      }
    }
    for (const p of (data.puestos || [])){
      // Key compacta global "<dep>-<mun>-<zon>-<pue>"
      const key = `${p.dep_cod}-${p.mun_cod}-${p.zon_cod}-${p.pue_cod}`;
      for (const ck of CONSULTA_KEYS){
        const c = p.consultas?.[ck];
        if (!c || !c.vv) continue;
        const v = {};
        for (const [cod, votos] of Object.entries(c.v || {})){
          const name = codToName[ck][cod];
          if (!name) continue;
          v[name] = (v[name] || 0) + votos;
          // Catálogo global: acumula votos por candidato
          if (!acc[ck].cands[name]){ acc[ck].cands[name] = { nombre: name, votos: 0 }; }
          acc[ck].cands[name].votos += votos;
        }
        // Si el puesto ya existe (no debería, pero por seguridad), suma
        const existing = acc[ck].pues[key];
        if (existing){
          existing.vv += c.vv; existing.vb += c.vb||0; existing.vn += c.vn||0; existing.vm += c.vm||0;
          for (const [n, votos] of Object.entries(v)) existing.v[n] = (existing.v[n] || 0) + votos;
        } else {
          acc[ck].pues[key] = { vv: c.vv, vb: c.vb||0, vn: c.vn||0, vm: c.vm||0, v };
        }
      }
      totalPuestos++;
    }
  }
  console.log(`  ${totalPuestos.toLocaleString('es-CO')} puestos procesados`);

  for (const ck of CONSULTA_KEYS){
    const subDir = path.join(outDir, `consulta-2026-${ck}`);
    fs.mkdirSync(subDir, { recursive: true });
    const out = {
      nombre: `Consulta 2026 · ${ck}`,
      anio: 2026,
      n_puestos: Object.keys(acc[ck].pues).length,
      generado_en: new Date().toISOString(),
      candidatos: acc[ck].cands,
      puestos: acc[ck].pues,
    };
    const outFile = path.join(subDir, 'por-puesto.json');
    fs.writeFileSync(outFile, JSON.stringify(out));
    const sz = fs.statSync(outFile).size;
    const top = Object.entries(acc[ck].cands).sort((a,b)=>b[1].votos - a[1].votos).slice(0,3);
    const totalV = Object.values(acc[ck].cands).reduce((s,c)=>s+c.votos,0);
    console.log(`  ✓ consulta-2026-${ck}/por-puesto.json   ${out.n_puestos} puestos · ${fmtKB(sz)}`);
    for (const [name, c] of top){
      console.log(`      ${name.padEnd(40)} ${String(c.votos).padStart(10)} (${(c.votos/totalV*100).toFixed(2)}%)`);
    }
  }
  console.log('');
}

main();
