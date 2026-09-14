/* construir-edad.mjs — el archivo que le falta a la tarjeta «Perfil del votante».
   ------------------------------------------------------------------
   La tarjeta 07 de Candidato 360 describe el electorado de los puestos donde
   están los votos de la persona: sexo y peso rural salen de fuentes que YA
   están publicadas (PUESTOS_GEOREF y la zona electoral de cada mesa). La edad
   no: vive en `Bases de datos/output_edad_1v/w26-puesto.csv`, que es local.

   Este script la convierte en un JSON compacto y publicable. En cuanto el
   archivo esté en

       congreso-2026/output/mapas-2026/CENSO_EDAD_PUESTO.json

   la tarjeta lo lee sola y muestra la edad; mientras no esté, el modal dice
   que falta en vez de estimarla.

   Uso:
     node tools/candidato-360/perfil/construir-edad.mjs \
       --w26="Bases de datos/output_edad_1v/w26-puesto.csv" \
       --salida=CENSO_EDAD_PUESTO.json

   Entrada  (w26-puesto.csv): pcode (dep-mun-zona-puesto), b0..b9 = votantes
     proyectados 2026 por banda [18-20, 21-25, 26-30, 31-35, 36-40, 41-45,
     46-50, 51-55, 56-60, 61+].
   Salida: { bandas, fuente, puestos: { "010010101": [a,b,c,d] } } con las diez
     bandas agrupadas en cuatro que sirven para una campaña: 18-25, 26-40,
     41-60 y 61+. Se redondea a entero: el archivo pasa de 2,4 MB a ~700 KB y
     la tarjeta solo usa proporciones.                                        */
import { readFile, writeFile } from 'node:fs/promises';

const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const ENTRADA = args.w26 || 'Bases de datos/output_edad_1v/w26-puesto.csv';
const SALIDA = args.salida || 'CENSO_EDAD_PUESTO.json';
const GRUPOS = [['18-25', [0, 1]], ['26-40', [2, 3, 4]], ['41-60', [5, 6, 7, 8]], ['61+', [9]]];

const texto = await readFile(ENTRADA, 'utf8');
const lineas = texto.split(/\r?\n/).filter(Boolean);
const cols = lineas[0].split(',').map(c => c.trim());
const iP = cols.indexOf('pcode'), iB = [...Array(10)].map((_, i) => cols.indexOf(`b${i}`));
if (iP < 0 || iB.some(i => i < 0)) throw new Error(`${ENTRADA} no tiene pcode y b0..b9`);

const puestos = {};
let leidos = 0, vacios = 0;
for (const linea of lineas.slice(1)) {
  const r = linea.split(',');
  /* pcode viene como dep-mun-zona-puesto; el código que usa la web es el de
     PUESTOS_GEOREF: dep(2)+mun(3)+zona(2)+puesto(2), sin guiones. */
  const partes = String(r[iP] || '').split('-');
  if (partes.length !== 4) { vacios++; continue; }
  const code = partes[0].padStart(2, '0') + partes[1].padStart(3, '0') + partes[2].padStart(2, '0') + partes[3].padStart(2, '0');
  const bandas = iB.map(i => Number(r[i]) || 0);
  const total = bandas.reduce((s, x) => s + x, 0);
  if (!total) { vacios++; continue; }
  puestos[code] = GRUPOS.map(([, idx]) => Math.round(idx.reduce((s, i) => s + bandas[i], 0)));
  leidos++;
}
const salida = {
  version: new Date().toISOString().slice(0, 10),
  bandas: GRUPOS.map(([nombre]) => nombre),
  fuente: 'Composición etaria proyectada 2026 del electorado de cada puesto (perfil local 2022 de la Registraduría + deriva demográfica DANE, raking a votantes reales).',
  puestos
};
await writeFile(SALIDA, JSON.stringify(salida));
console.log(`${leidos.toLocaleString('es-CO')} puestos escritos (${vacios.toLocaleString('es-CO')} sin datos) → ${SALIDA}`);
console.log('Súbalo a congreso-2026/output/mapas-2026/CENSO_EDAD_PUESTO.json y la tarjeta 07 muestra la edad sin tocar código.');
