/* prueba-salto-crm.mjs — el salto de corporación dentro del CRM, sin red.
   ------------------------------------------------------------------
   El caso que lo motivó: una edil de Teusaquillo (JAL 2019) se lanza al
   Concejo de Bogotá y el modo «Proyectado» le ponía TODA la meta en
   Teusaquillo, como si el Concejo se eligiera por localidad. Acá se abre el
   CRM con una Bogotá de tres localidades, resultados del Concejo 2023 de
   mentiras y se comprueba:

     · sin estudio publicado, la meta sale de Teusaquillo hacia donde votó su
       partido (Suba pesa más que Sumapaz), y la nota lo dice;
     · con estudio (lift), el origen pesa lo que midió el estudio;
     · «Total» sigue mostrando el historial tal cual (el salto no lo toca).

   Necesita Leaflet en disco, igual que prueba-mapa.mjs:
     npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz
     node tools/candidato-360/prueba-salto-crm.mjs                            */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8');
const leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');

const caja = (id, nom, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: { LocCodigo: id, LocNombre: nom },
  geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
const BOG = { type: 'FeatureCollection', features: [
  caja('13', 'TEUSAQUILLO', [-74.10, 4.60, -74.06, 4.66]),
  caja('11', 'SUBA',        [-74.14, 4.66, -74.05, 4.78]),
  caja('20', 'SUMAPAZ',     [-74.35, 3.72, -74.00, 4.50]),
] };
/* Concejo de Bogotá 2023, de mentiras: el Nuevo Liberalismo votó sobre todo
   en Suba, algo en Teusaquillo y nada en Sumapaz. */
const NL = 'PARTIDO NUEVO LIBERALISMO', PH = 'PACTO HISTORICO';
const RESULTADOS = { data: { '16-001': { comunas: {
  '13': { name: 'TEUSAQUILLO', validos: 80000,  votantes: 85000,  partidos: [[NL, 8000],  [PH, 9000]] },
  '11': { name: 'SUBA',        validos: 500000, votantes: 520000, partidos: [[NL, 32000], [PH, 90000]] },
  '20': { name: 'SUMAPAZ',     validos: 3000,   votantes: 3200,   partidos: [[NL, 0],     [PH, 900]] },
} } } };
let tablaArraigo = null;   /* primero sin estudio; después con lift */

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('BOG-LOCALIDADX')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BOG) });
  if (u.includes('resultados-concejo-2023.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RESULTADOS) });
  if (u.includes('saltos-arraigo.json')) return tablaArraigo ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(tablaArraigo) }) : route.fulfill({ status: 404, body: '' });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.renderBogotaCampaignMap === 'function' && typeof window.L === 'object' && typeof window.PartidosBloques === 'object');
await p.waitForTimeout(300);

/* La edil: todo su historial en Teusaquillo. */
await p.evaluate(() => {
  window.datosCandidatura = async () => ({ mesas: [
    { dep: '16', mun: '001', zon: '13', pue: '01', com: '13', comNom: 'TEUSAQUILLO', v: 709 },
  ] });
  crmCandidate = { nombre: 'NATALIA SOPHIA PARRA ROJAS', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2019', circunscripcion: 'BOGOTÁ D.C.', partido: 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', votos: 709, slug: 'x' };
  showScreen('crm');
  document.getElementById('crmVoteNumber').textContent = '6.770';
});
async function proyectar() {
  await p.evaluate(() => renderBogotaCampaignMap(crmCandidate));
  await p.waitForTimeout(800);
  await p.evaluate(async () => { saltosArraigoPromise = null; await prepararSalto('concejo', { departamento: '16', departamentoNombre: 'BOGOTÁ D.C.' }); crmMapMode = 'proyectado'; refreshCRMMapMode(); });
  await p.waitForTimeout(300);
  return p.evaluate(() => ({
    reparto: projectedVotesByArea(), nota: document.getElementById('crmMapNote').textContent,
    salto: SALTO_ACTUAL && { clave: SALTO_ACTUAL.tipo.clave, capa: SALTO_ACTUAL.base?.capa, arraigo: SALTO_ACTUAL.arraigo },
    filas: [...document.querySelectorAll('#crmMapBreakdown [data-key], #crmMapBreakdown li, #crmMapBreakdown tr')].length,
  }));
}
const r = {};
r.sin = await proyectar();
await p.screenshot({ path: SP + '/salto-sin-estudio.png' });
tablaArraigo = { 'jal>concejo': { '16': { n: 14, arraigo_mediana: .31, lift_mediana: 2, lift_n: 12 }, _nacional: { n: 60, arraigo_mediana: .3, lift_mediana: 1.8, lift_n: 50 } } };
r.con = await proyectar();
await p.screenshot({ path: SP + '/salto-con-estudio.png' });
r.total = await p.evaluate(() => { crmMapMode = 'total'; refreshCRMMapMode(); return { nota: document.getElementById('crmMapNote').textContent, votos: crmMapState.votesByArea }; });
/* Sin salto (Concejo → Concejo) nada cambia: el reparto proporcional de siempre. */
r.mismo = await p.evaluate(async () => { crmCandidate.corp = 'CONCEJO · BOGOTÁ D.C. · 2019'; saltosArraigoPromise = null; await prepararSalto('concejo', { departamento: '16' }); crmMapMode = 'proyectado'; refreshCRMMapMode(); return { salto: SALTO_ACTUAL, reparto: projectedVotesByArea(), nota: document.getElementById('crmMapNote').textContent }; });
await b.close();

const suma = o => Object.values(o).reduce((s, v) => s + v, 0);
const META = 6770, pesoTeusaquillo = 8000 / 40000;   /* peso del NL en Teusaquillo dentro de su huella */
const pruebas = [
  ['JAL → Concejo se reconoce como salto a escala de localidad', r.sin.salto?.clave === 'jal>concejo'],
  ['la base es la huella del partido (el NL corrió en 2 de 3 localidades con masa)', r.sin.salto?.capa === 'partido'],
  ['la meta ya no cae toda en Teusaquillo', r.sin.reparto['13'] < META * .5],
  ['sin estudio, Teusaquillo pesa lo que pesa en la huella (cero bono)', Math.abs(r.sin.reparto['13'] / META - pesoTeusaquillo) < .003],
  ['el resto va donde votó el partido: Suba sí, Sumapaz no', r.sin.reparto['11'] > r.sin.reparto['13'] && (r.sin.reparto['20'] || 0) === 0],
  ['la suma es exactamente la meta', suma(r.sin.reparto) === META],
  ['la nota dice que es un salto y que reparte por la huella del partido', /Salto de Junta administradora local a Concejo/.test(r.sin.nota) && /huella de/.test(r.sin.nota) && /no lleva bono/.test(r.sin.nota)],
  ['con estudio, el departamento manda y trae el lift', r.con.salto?.arraigo?.ambito === 'departamento' && r.con.salto.arraigo.lift === 2],
  ['y Teusaquillo pesa lift × su peso en la huella', Math.abs(r.con.reparto['13'] / META - 2 * pesoTeusaquillo) < .003],
  ['la nota cuenta el estudio (14 candidaturas, en este departamento)', /2 veces/.test(r.con.nota) && /14 candidaturas/.test(r.con.nota) && /en este departamento/.test(r.con.nota)],
  ['«Total» sigue mostrando el historial sin tocar', r.total.votos['13'] === 709 && /Votación total histórica/.test(r.total.nota)],
  ['Concejo → Concejo no es salto: reparto proporcional de siempre', r.mismo.salto === null && r.mismo.reparto['13'] === META && /proporcionalmente/.test(r.mismo.nota)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 1500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
