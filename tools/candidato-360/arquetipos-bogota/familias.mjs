// Clasifica por familia política (partidos-bloques.js, el mismo diccionario del
// CRM) los partidos y candidaturas de Bogotá que salen de extraer.py.
//   node tools/candidato-360/arquetipos-bogota/familias.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
await import(path.join(RAIZ, 'partidos-bloques.js'));
const PB = globalThis.PartidosBloques;
const RAW = path.join(RAIZ, 'Bases de datos/arquetipos-bogota/raw');
const out = {};
for (const clave of ['ter2023', 'ter2019', 'jal2023', 'jal2019']) {
  const d = JSON.parse(fs.readFileSync(path.join(RAW, clave + '.json'), 'utf8'));
  for (const [k, nombre] of Object.entries(d._partidos)) {
    const [corp, par] = k.split('|');
    if (par === '0') continue;
    const cand = corp === 'alc' ? Object.entries(d._nombres).find(([kk]) => kk.startsWith(`alc|${par}|`) && !kk.endsWith('|0'))?.[1] : '';
    const b = corp === 'alc' ? PB.bloqueDeCandidatura(nombre, cand || '') : PB.bloqueDeOrganizacion(nombre);
    out[`${clave}|${k}`] = { nombre, bloque: b, amplio: PB.esAvalAmplio(nombre) };
  }
}
fs.writeFileSync(path.join(RAW, 'familias.json'), JSON.stringify(out, null, 0));
for (const [k, v] of Object.entries(out)) if (/ter20(23|19)\|(alc|conc)/.test(k)) console.log(k.padEnd(22), v.bloque.padEnd(4), v.amplio ? 'AMPLIO' : '', v.nombre);
