// Script Node para calcular bias_mun_medellin usando la misma lógica de
// previa-1v.html (precomputeBiasMun para munKey='01-001'). Usa los JSONs
// públicos de S3.
const https = require('https');

const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
const norm = s => String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').trim().toUpperCase();

const HISTORICO_KEYS = [
  'pres-2010-v1', 'pres-2014-v1', 'pres-2018-v1', 'pres-2022-v1',
  'consulta-2025-pacto',
  'consulta-2026-gran', 'consulta-2026-frente', 'consulta-2026-soluciones',
];

// EQUIVALENCIAS national (mismo que previa-1v.html)
const EQUIVALENCIAS = {
  'ic': {
    'consulta-2025-pacto':    { cands: ['IVAN CEPEDA CASTRO'], peso: 0.38 },
    'senado-2026':            { partidos: ['PACTO HISTÓRICO SENADO'], peso: 0.18 },
    'pres-2022-v1':           { cands: ['GUSTAVO PETRO'], peso: 0.17 },
    'pres-2018-v1':           { cands: ['GUSTAVO PETRO'], peso: 0.10 },
    'pres-2014-v1':           { cands: ['CLARA LOPEZ'], peso: 0.05 },
    'pres-2010-v1':           { cands: ['GUSTAVO FRANCISCO PETRO URREGO', 'AURELIJUS RUTENIS ANTANAS MOCKUS SIVICKAS'], peso: 0.02 },
  },
  'ae': {
    'senado-2026':  { partidos: ['MOVIMIENTO SALVACIÓN NACIONAL'], peso: 0.30 },
    'pres-2022-v1': { cands: ['FEDERICO GUTIERREZ', 'RODOLFO HERNANDEZ'], peso: 0.25 },
    'pres-2018-v1': { cands: ['IVAN DUQUE'], peso: 0.15 },
    'pres-2014-v1': { cands: ['OSCAR IVAN ZULUAGA'], peso: 0.10 },
    'pres-2010-v1': { cands: ['JUAN MANUEL SANTOS CALDERON'], peso: 0.05 },
  },
  'pv': {
    'consulta-2026-gran': { cands: ['PALOMA SUSANA VALENCIA LASERNA'], peso: 0.40 },
    'senado-2026':  { partidos: ['PARTIDO CENTRO DEMOCRÁTICO'], peso: 0.20 },
    'pres-2022-v1': { cands: ['FEDERICO GUTIERREZ'], peso: 0.18 },
    'pres-2018-v1': { cands: ['IVAN DUQUE'], peso: 0.10 },
    'pres-2014-v1': { cands: ['OSCAR IVAN ZULUAGA'], peso: 0.04 },
  },
  'sf': {
    'pres-2022-v1': { cands: ['SERGIO FAJARDO'], peso: 0.30 },
    'pres-2018-v1': { cands: ['SERGIO FAJARDO'], peso: 0.25 },
    'senado-2026':  { partidos: ['ALIANZA POR COLOMBIA', 'AHORA COLOMBIA'], peso: 0.15 },
    'pres-2014-v1': { cands: ['ENRIQUE PENALOSA', 'MARTHA LUCIA RAMIREZ'], peso: 0.07 },
    'pres-2010-v1': { cands: ['AURELIJUS RUTENIS ANTANAS MOCKUS SIVICKAS'], peso: 0.05 },
  },
  'cl': {
    'consulta-2026-soluciones': { cands: ['CLAUDIA NAYIBE LOPEZ HERNANDEZ'], peso: 0.35 },
    'senado-2026':  { partidos: ['AHORA COLOMBIA'], peso: 0.15 },
    'pres-2022-v1': { cands: ['SERGIO FAJARDO'], peso: 0.18 },
    'pres-2018-v1': { cands: ['SERGIO FAJARDO'], peso: 0.08 },
    'pres-2014-v1': { cands: ['ENRIQUE PENALOSA'], peso: 0.04 },
  },
  'rb': {
    'consulta-2026-frente': { cands: ['ROY LEONARDO BARRERAS MONTEALEGRE'], peso: 0.40 },
    'senado-2026':  { partidos: ['FRENTE AMPLIO UNITARIO'], peso: 0.20 },
    'pres-2022-v1': { cands: ['GUSTAVO PETRO'], peso: 0.15 },
    'pres-2018-v1': { cands: ['HUMBERTO DE LA CALLE'], peso: 0.08 },
  },
  'lm': {
    'senado-2026':  { partidos: ['PACTO HISTÓRICO SENADO'], peso: 0.15 },
    'pres-2022-v1': { cands: ['SERGIO FAJARDO', 'GUSTAVO PETRO'], peso: 0.20 },
    'pres-2018-v1': { cands: ['HUMBERTO DE LA CALLE'], peso: 0.10 },
  },
};

function fetchJSON(url){
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch(e){ reject(e); }
      });
    }).on('error', reject);
  });
}

async function main(){
  const HISTORICOS = {};

  // Cargar por-mun y por-depto para cada signal
  for (const key of HISTORICO_KEYS){
    console.error(`Cargando ${key}…`);
    const [mun, dep] = await Promise.all([
      fetchJSON(`${S3}/historicos/${key}/por-mun.json`).catch(() => null),
      fetchJSON(`${S3}/historicos/${key}/por-depto.json`).catch(() => null),
    ]);
    if (!mun || !dep) { console.error(`  skip (no data)`); continue; }
    // Index por-depto: pct nacional por candidato (agregado)
    const nacCounts = {};
    let nacValidos = 0;
    for (const dCod of Object.keys(dep)){
      const d = dep[dCod];
      const valids = d.votos_validos || 0;
      nacValidos += valids;
      for (const c of Object.values(d.candidatos || {})){
        const k = norm(c.nombre);
        nacCounts[k] = (nacCounts[k] || 0) + (c.votos || 0);
      }
    }
    const nacional = {};
    for (const [k,v] of Object.entries(nacCounts)) nacional[k] = nacValidos > 0 ? v / nacValidos : 0;

    // Index por-mun: pct municipal Medellín '01-001'
    const med = mun['01-001'];
    const mdeByName = {};
    if (med){
      const valids = med.votos_validos || 0;
      for (const c of Object.values(med.candidatos || {})){
        mdeByName[norm(c.nombre)] = valids > 0 ? (c.votos || 0) / valids : 0;
      }
    }
    HISTORICOS[key] = { nacional, medellin: mdeByName };
  }

  // Senado 2026 (departamentos.json contiene partidos × deptos)
  console.error(`Cargando senado-2026…`);
  const senDeps = await fetchJSON(`${S3}/senado/departamentos.json`);
  const senPartNac = {}; let senValNac = 0;
  let senMedellin = null;
  for (const s of senDeps){
    senValNac += s.votval || 0;
    for (const [partido, votos] of Object.entries(s.partidos || {})){
      const k = norm(partido);
      senPartNac[k] = (senPartNac[k] || 0) + votos;
    }
  }
  const senNac = {};
  for (const [p,v] of Object.entries(senPartNac)) senNac[p] = senValNac > 0 ? v/senValNac : 0;
  // Medellín-mun senado: necesitamos puestos.json o municipios.json
  // Mejor: usar el bucket bases+de+datos/output_medellin/2026/senado/resumen.json
  const senMed = await fetchJSON('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/output_medellin/2026/senado/resumen.json');
  const senMedByPart = {};
  if (senMed && senMed.partidos){
    const valids = senMed.votos_validos || 0;
    for (const p of senMed.partidos){
      senMedByPart[norm(p.nombre)] = valids > 0 ? p.votos / valids : 0;
    }
  }
  HISTORICOS['senado-2026'] = { nacional: senNac, medellin: senMedByPart };

  // Computar bias_mun_medellin para cada candidato
  const result = {};
  for (const [candId, equiv] of Object.entries(EQUIVALENCIAS)){
    let num = 0, den = 0;
    const debug = [];
    for (const [sig, spec] of Object.entries(equiv)){
      const data = HISTORICOS[sig]; if (!data){ debug.push(`${sig}=NO_DATA`); continue; }
      const keys = (spec.cands || spec.partidos || []).map(k => norm(k));
      const pctMed = keys.reduce((s,k) => s + (data.medellin[k] || 0), 0);
      const pctNac = keys.reduce((s,k) => s + (data.nacional[k] || 0), 0);
      if (pctNac <= 0){ debug.push(`${sig}=NO_NAC`); continue; }
      const ratio = pctMed / pctNac;
      num += spec.peso * ratio;
      den += spec.peso;
      debug.push(`${sig}=${ratio.toFixed(2)} (med ${(pctMed*100).toFixed(2)}%, nac ${(pctNac*100).toFixed(2)}%)`);
    }
    if (den > 0){
      const bias = Math.max(0.15, Math.min(3.50, num / den));
      result[candId] = bias;
      console.error(`\n${candId}: bias=${bias.toFixed(3)}`);
      debug.forEach(d => console.error(`  ${d}`));
    }
  }
  result['otros'] = 1.0;
  result['nd'] = 1.0;
  console.error('\n\n--- RESULT (paste in module) ---');
  console.log('const BIAS_MUN_MEDELLIN = ' + JSON.stringify(result, null, 2) + ';');
}

main().catch(e => { console.error('FATAL:', e); process.exit(1); });
