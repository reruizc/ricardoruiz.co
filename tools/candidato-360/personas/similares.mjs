/* similares.mjs — los nombres que se repiten en el índice y qué hace con ellos
   la unificación por persona de candidato-360.js.
   ------------------------------------------------------------------
   El buscador de Candidato 360 muestra UNA tarjeta por persona cuando los
   cuatro componentes del nombre coinciden. Con tres componentes (DANIEL
   CARVALHO MEJIA: Cámara Antioquia 2022, Concejo Medellín 2015 y 2019)
   también, pero solo si todas sus candidaturas territoriales caen en el mismo
   departamento. Este script baja los mismos índices que la web (cand-index.js)
   y saca, para cada nombre de tres componentes con dos o más candidaturas:

     decision      UNIFICA | NO: varios departamentos | NO: solo nacional
     tipo          mismo-municipio | varios-municipios (los que vale la pena
                   mirar: misma persona en dos concejos del mismo departamento
                   o dos personas homónimas)
     departamento, n, municipios, nombres tal como vienen, candidaturas

   Uso:
     node tools/candidato-360/personas/similares.mjs [--salida=DIR] [--cache=DIR]

   Deja similares.csv (todos los grupos) y similares-resumen.md en --salida
   (por defecto tools/candidato-360/personas/salida, ignorado por git).
   Necesita red hacia S3 (en el sandbox: NODE_USE_ENV_PROXY=1 y
   NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt).                              */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const SALIDA = path.resolve(args.salida || path.join(REPO, 'tools/candidato-360/personas/salida'));
const CACHE = path.resolve(args.cache || path.join(homedir(), '.cache', 'rr-indices'));
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co';
await mkdir(SALIDA, { recursive: true }); await mkdir(CACHE, { recursive: true });

/* cand-index.js tal cual lo usa la web, con un fetch que cachea en disco. */
const ctx = { window: { RRData: { publicUrl: p => `${S3}/${p}` } }, console, fetch: async url => {
  const f = path.join(CACHE, url.split('/').slice(-2).join('__'));
  let txt;
  if (existsSync(f)) txt = await readFile(f, 'utf8');
  else { const r = await fetch(url); if (!r.ok) throw new Error(`HTTP ${r.status}`); txt = await r.text(); await writeFile(f, txt); console.error(`  ↓ ${url.split('/').pop()} (${(txt.length / 1e6).toFixed(1)} MB)`); }
  return { ok: true, json: async () => JSON.parse(txt) };
} };
vm.createContext(ctx);
vm.runInContext(await readFile(path.join(REPO, 'cand-index.js'), 'utf8'), ctx);
const CR = ctx.window.CandRegistry;
/* La regla de departamento, sacada de candidato-360.js para no duplicarla. */
const js = await readFile(path.join(REPO, 'candidato-360.js'), 'utf8');
const fn = js.slice(js.indexOf('function departamentoDelSlug('), js.indexOf('function candidateProfile('));
const departamentoDelSlug = new Function(`${fn}; return departamentoDelSlug;`)();
const candidateYear = c => Number(String(c?.corp || '').match(/20\d{2}/)?.[0] || (c?.source === 'endoso' ? 2026 : 0));

console.error('Bajando índices…');
const todo = (await CR.load({ includeParties: false })).concat(await CR.loadLocal({ includeParties: false }));
console.error(`${todo.length.toLocaleString('es-CO')} candidaturas`);

function municipio(c) {
  const m = String(c.circunscripcion || '').match(/^(.+?)\s*\((.+)\)$/); if (m) return m[1].trim();
  if (/^JAL/.test(c.corp)) return String(c.circunscripcion).split('·').slice(-1)[0].trim();
  if (/^(CONCEJO|ALCALD)/.test(c.corp)) return String(c.circunscripcion).trim();
  return '';
}
const grupos = new Map();
for (const c of todo) { const key = CR.personaKey(c.nombre); if (key.split(' ').length !== 3) continue; (grupos.get(key) || grupos.set(key, []).get(key)).push(c); }
const filas = [], resumen = { grupos: 0, unifica: 0, mismoMunicipio: 0, variosMunicipios: 0, variosDepartamentos: 0, soloNacional: 0 };
for (const [key, cs] of grupos) {
  const seen = new Set, hist = cs.filter(c => !seen.has(c.slug) && seen.add(c.slug));
  if (hist.length < 2) continue;
  resumen.grupos++;
  const deps = [...new Set(hist.map(c => departamentoDelSlug(c.slug)).filter(Boolean))];
  const munis = [...new Set(hist.map(municipio).filter(Boolean))];
  const decision = deps.length === 1 ? 'UNIFICA' : deps.length ? 'NO: varios departamentos' : 'NO: solo nacional';
  const tipo = munis.length > 1 ? 'varios-municipios' : 'mismo-municipio';
  if (deps.length === 1) { resumen.unifica++; resumen[tipo === 'mismo-municipio' ? 'mismoMunicipio' : 'variosMunicipios']++; } else if (deps.length) resumen.variosDepartamentos++; else resumen.soloNacional++;
  hist.sort((a, b) => candidateYear(a) - candidateYear(b) || a.corp.localeCompare(b.corp));
  filas.push({ key, decision, tipo, departamentos: deps.join(' / '), n: hist.length, municipios: munis.join(' / '), nombres: [...new Set(hist.map(c => c.nombre))].join(' / '), candidaturas: hist.map(c => `${c.corp} · ${c.partido || 'sin partido'} · ${Number(c.votos || 0).toLocaleString('es-CO')} v`).join(' || ') });
}
const orden = { 'varios-municipios': 0, 'mismo-municipio': 1 }, ordenD = { 'NO: varios departamentos': 0, 'NO: solo nacional': 1, 'UNIFICA': 2 };
filas.sort((a, b) => ordenD[a.decision] - ordenD[b.decision] || orden[a.tipo] - orden[b.tipo] || a.key.localeCompare(b.key));
const csv = v => `"${String(v).replace(/"/g, '""')}"`;
const cols = ['clave', 'decision', 'tipo', 'departamentos', 'n', 'municipios', 'nombres', 'candidaturas'];
await writeFile(path.join(SALIDA, 'similares.csv'), '﻿' + [cols.join(';'), ...filas.map(f => [f.key, f.decision, f.tipo, f.departamentos, f.n, f.municipios, f.nombres, f.candidaturas].map(csv).join(';'))].join('\n'));
await writeFile(path.join(SALIDA, 'similares.json'), JSON.stringify(filas));
const md = `# Nombres de tres componentes que se repiten en el índice

Índice de ${todo.length.toLocaleString('es-CO')} candidaturas · ${new Date().toISOString().slice(0, 10)}.

| | grupos |
|---|---:|
| Nombres de tres componentes con 2+ candidaturas | ${resumen.grupos.toLocaleString('es-CO')} |
| **Se unifican** (un solo departamento) | **${resumen.unifica.toLocaleString('es-CO')}** |
| · todas en el mismo municipio (o departamentales/nacionales) | ${resumen.mismoMunicipio.toLocaleString('es-CO')} |
| · en varios municipios del mismo departamento — los que vale la pena revisar | ${resumen.variosMunicipios.toLocaleString('es-CO')} |
| No se unifican: varios departamentos | ${resumen.variosDepartamentos.toLocaleString('es-CO')} |
| No se unifican: solo candidaturas nacionales | ${resumen.soloNacional.toLocaleString('es-CO')} |

El detalle, grupo por grupo, está en \`similares.csv\` (separador \`;\`, UTF-8 con BOM: abre directo en Excel).
`;
await writeFile(path.join(SALIDA, 'similares-resumen.md'), md);
console.log(md);
console.error(`→ ${SALIDA}/similares.csv`);
