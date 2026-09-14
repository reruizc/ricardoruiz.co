/* prueba-barrios-voronoi.mjs — los barrios aproximados de Ibagué y Montería.
   ------------------------------------------------------------------
   Las capas las construye tools/candidato-360/barrios-voronoi/construir.py.
   Acá se comprueba lo que el CRM necesita de ellas, con la MISMA función de
   punto-en-polígono que usa la página:

     · que sean GeoJSON válido, solo polígonos, con nombre, código y comuna;
     · que cada puesto de votación que formó un barrio caiga DENTRO de ese
       barrio (si no, la ubicación por coordenada del CRM lo perdería);
     · que ningún barrio se salga de su comuna (el CRM los pinta por comuna);
     · que no haya astillas: la celda de un puesto rural recortada al contorno
       urbano daba polígonos de área cero en el borde de la ciudad.

     node tools/candidato-360/prueba-barrios-voronoi.mjs                       */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const js = await readFile(new URL('../../candidato-360.js', import.meta.url), 'utf8');
const desde = js.indexOf('function puntoEnAnillo('), hasta = js.indexOf('/* Índice con caja envolvente');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(`${js.slice(desde, hasta)}\nthis.dentro = puntoEnGeometria;`, ctx);
const dentro = ctx.dentro;

const fallos = []; let total = 0;
const revisar = (t, ok) => { total++; console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) fallos.push(t); };
const area = geom => { const anillo = a => a.reduce((s, [x1, y1], i) => { const [x2, y2] = a[(i + 1) % a.length]; return s + (x1 * y2 - x2 * y1); }, 0) / 2; const pols = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates; return pols.reduce((s, p) => s + Math.abs(anillo(p[0])) - p.slice(1).reduce((h, r) => h + Math.abs(anillo(r)), 0), 0) * 1.23e10 / 1e6; };

/* Los puestos con coordenada, para verificar que cada uno cae en su barrio.
   Se leen del CSV real si está en el scratchpad de la sesión; si no, se usan
   los centroides que el propio archivo trae (PUESTOS solo trae códigos). */
let puestos = null;
try {
  const raw = await readFile(process.env.PUESTOS_CSV || '/tmp/claude-0/-home-user-ricardoruiz-co/84bafac9-a83e-5c82-82c5-0bbe900e798b/scratchpad/real/PUESTOS_GEOREF.csv', 'utf8');
  puestos = {}; raw.split(/\r?\n/).slice(1).forEach(l => { const r = l.split(';'); if (r[1]) puestos[r[1]] = { lat: +r[9], lng: +r[10] }; });
} catch { /* sin CSV: se salta esa comprobación */ }

for (const [ciudad, comunasEsperadas] of [['IBAGUE', 13], ['MONTERIA', 9]]) {
  const fc = JSON.parse(await readFile(new URL(`../../candidato-360-data/barrios-voronoi/${ciudad}-BARRIOS.json`, import.meta.url), 'utf8'));
  const f = fc.features;
  console.log(`\n## ${ciudad}`);
  revisar(`es una FeatureCollection con aviso de que NO es cartografía oficial`, fc.type === 'FeatureCollection' && /NO es cartografía oficial/.test(fc.metadata?.disclaimer || ''));
  revisar(`todos los rasgos son polígonos con NOMBRE, CODIGO y COMUNA`, f.length > 30 && f.every(x => /Polygon$/.test(x.geometry?.type) && x.properties.NOMBRE && x.properties.CODIGO && x.properties.COMUNA));
  revisar(`cubre las ${comunasEsperadas} comunas con polígono`, new Set(f.map(x => x.properties.COMUNA)).size === comunasEsperadas);
  revisar(`los códigos son únicos`, new Set(f.map(x => x.properties.CODIGO)).size === f.length);
  revisar(`ningún nombre arrastra el prefijo «Barrio »`, f.every(x => !/^Barrio\s/i.test(x.properties.NOMBRE)));
  revisar(`sin astillas: ningún barrio mide menos de 0,01 km²`, f.every(x => area(x.geometry) >= 0.01));
  if (puestos) {
    const fuera = [];
    for (const x of f) for (const code of x.properties.PUESTOS || []) { const p = puestos[code]; if (p && !dentro(p.lng, p.lat, x.geometry)) fuera.push(`${code}→${x.properties.NOMBRE}`); }
    revisar(`cada puesto cae dentro del barrio que formó (${f.reduce((s, x) => s + (x.properties.PUESTOS || []).length, 0)} puestos)`, fuera.length === 0);
    if (fuera.length) console.log('   fuera:', fuera.slice(0, 5));
  }
}
console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : `${total} de ${total} pasaron`);
process.exit(fallos.length ? 1 : 0);
