/* construir.mjs — el manifiesto de logos de partido de una ciudad.
   ------------------------------------------------------------------
   Candidato 360 muestra el logo del partido al lado de su nombre cuando el
   archivo existe, y nada cuando no: por eso el `index.json` lista SOLO los
   logos que están en la carpeta. Se corre después de agregar archivos y el
   frontend se entera solo.

   Uso:
     node tools/candidato-360/logos/construir.mjs 16        # Bogotá D.C.
     node tools/candidato-360/logos/construir.mjs 16 --encargo

   El catálogo de organizaciones sale de candidato-360-data/partidos/<dep>.js
   (el mismo que sugiere el campo «¿con qué partido se va a lanzar?»), sin las
   coaliciones —que no se ofrecen al elegir—. Con --encargo imprime la lista de
   archivos que faltan, lista para pegarle a quien los vaya a hacer.          */
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const args = process.argv.slice(2);
const DEP = String(args.find(a => /^\d{1,2}$/.test(a)) || '16').padStart(2, '0');
const ENCARGO = args.includes('--encargo');
const DIR = path.join(REPO, 'candidato-360-data/logos-partidos', DEP);

/* candidato-360-data/partidos/<dep>.js es un script de navegador: se lee el
   arreglo sin ejecutarlo como módulo. */
const fuente = await readFile(path.join(REPO, 'candidato-360-data/partidos', `${DEP}.js`), 'utf8');
const lista = JSON.parse(fuente.slice(fuente.indexOf('=[', fuente.indexOf('Candidato360Partidos[')) + 1).replace(/;\s*$/, ''));
const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
/* El slug es el nombre en minúsculas, sin tildes ni signos, con guiones. Es el
   nombre del archivo y no cambia aunque cambie el orden del catálogo. */
const slug = s => norm(s).toLowerCase().replace(/\s+/g, '-');
const partidos = lista.filter(x => x[3] !== 1).map(([nombre, cand, votos]) => ({ nombre, slug: slug(nombre), cand, votos }))
  .sort((a, b) => (b.votos || 0) - (a.votos || 0) || (b.cand || 0) - (a.cand || 0));

await mkdir(DIR, { recursive: true });
const archivos = new Set((await readdir(DIR).catch(() => [])).filter(f => /\.(png|svg|webp)$/i.test(f)));
const tiene = p => [...archivos].find(f => f.replace(/\.\w+$/, '') === p.slug) || '';
const logos = partidos.filter(p => tiene(p)).map(p => ({ nombre: p.nombre, archivo: tiene(p) }));
const faltan = partidos.filter(p => !tiene(p));

await writeFile(path.join(DIR, 'index.json'), JSON.stringify({
  version: new Date().toISOString().slice(0, 10),
  departamento: DEP,
  nota: 'Solo los logos que existen en la carpeta. Lo produce tools/candidato-360/logos/construir.mjs; no se edita a mano.',
  logos
}, null, 1) + '\n');

console.log(`${DEP} · ${partidos.length} organizaciones · ${logos.length} con logo · ${faltan.length} sin logo`);
if (!ENCARGO) process.exit(0);
console.log(`\nFaltan estos archivos en candidato-360-data/logos-partidos/${DEP}/ (PNG, 512×512, fondo transparente):\n`);
faltan.forEach(p => console.log(`  ${(p.slug + '.png').padEnd(58)} ${p.nombre}`));
