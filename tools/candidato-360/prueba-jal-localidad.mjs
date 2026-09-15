/* prueba-jal-localidad.mjs — la JAL se elige por localidad, no por ciudad.
   ------------------------------------------------------------------
   El caso que lo motivó: un edil de Teusaquillo (JAL 2015) simula lanzarse a
   la JAL de Tunjuelito y el modo «Proyectado» le ponía la meta en TEUSAQUILLO.
   El recorte territorial solo bajaba hasta el municipio y las dos localidades
   son el mismo municipio —Bogotá—, así que su historial «seguía en alcance»:
   el CRM le pintaba la meta sobre el territorio que acaba de dejar, donde en
   2027 su votación anterior no cuenta un solo voto.

   Lo que se comprueba acá:

     · el alcance de una JAL es la LOCALIDAD, con su municipio adentro, y una
       mesa de Teusaquillo queda fuera del alcance de Tunjuelito aunque las dos
       sean Bogotá;
     · mudarse de localidad NO es mudarse de ciudad: el mapa sigue siendo el de
       Bogotá por localidades —«Total» tiene que poder mostrar los votos que sí
       existen, los de Teusaquillo— y sus niveles son Localidad y Barrio, nunca
       «Municipio», que en Bogotá no existe;
     · «Proyectado» lleva la meta COMPLETA a Tunjuelito: a una JAL se entra por
       una sola localidad, así que no hay nada que repartir;
     · mudarse de CIUDAD sí cambia el mapa por el territorio nuevo, y ahí el
       primer nivel también se llama por la unidad que se dibuja.

     node tools/candidato-360/prueba-jal-localidad.mjs                        */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8'), leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');

const caja = (id, nom, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: { LocCodigo: id, LocNombre: nom },
  geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
const BOG = { type: 'FeatureCollection', features: [
  caja('13', 'TEUSAQUILLO', [-74.10, 4.60, -74.06, 4.66]),
  caja('06', 'TUNJUELITO',  [-74.16, 4.55, -74.12, 4.59]),
  caja('11', 'SUBA',        [-74.14, 4.66, -74.05, 4.78]),
] };
const BOGOTA_MUN = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'BOGOTÁ, D.C.', mun_elec: '001' }, geometry: { type: 'Polygon', coordinates: [[[-74.2, 4.5], [-74.0, 4.5], [-74.0, 4.8], [-74.2, 4.8], [-74.2, 4.5]]] } }] };
/* COMUNAS_DATA.csv: departamento en la 6, municipio en la 7, localidad en la 11. */
const COMUNAS = ['cabecera'].concat(['TEUSAQUILLO', 'TUNJUELITO', 'SUBA'].map(l =>
  [0, 1, 2, 3, 4, 'BOGOTA D.C.', 'BOGOTÁ, D.C.', 7, 8, 9, l].join(';'))).join('\n');
/* PUESTOS_GEOREF: código en la 2, barrio en la 8, localidad en la 13,
   mujeres y hombres en la 14 y 15. Dos puestos por localidad. */
const puesto = (code, barrio, localidad, lat, lng) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = String(lat); r[10] = String(lng); r[12] = localidad; r[13] = '900'; r[14] = '800'; return r.join(';'); };
const PUESTOS = ['CABECERA',
  puesto('160011301', 'GALERÍAS', 'TEUSAQUILLO', 4.64, -74.07),
  puesto('160011302', 'PALERMO', 'TEUSAQUILLO', 4.63, -74.08),
  puesto('160010601', 'VENECIA', 'TUNJUELITO', 4.58, -74.14),
  puesto('160010602', 'TUNAL', 'TUNJUELITO', 4.57, -74.13),
].join('\n');
/* Todo su historial de 2015, en Teusaquillo y en ninguna otra parte. */
const MESAS = { mesas: [
  { dep: '16', depNom: 'BOGOTÁ D.C.', mun: '001', munNom: 'BOGOTÁ D.C.', zon: '13', pue: '01', pueNom: 'GALERÍAS', com: '13', comNom: 'TEUSAQUILLO', v: 1200 },
  { dep: '16', depNom: 'BOGOTÁ D.C.', mun: '001', munNom: 'BOGOTÁ D.C.', zon: '13', pue: '02', pueNom: 'PALERMO', com: '13', comNom: 'TEUSAQUILLO', v: 680 },
] };
const META = 2400;

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('tile.openstreetmap.org')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eee"/></svg>' });
  if (u.includes('BOG-LOCALIDADX.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BOG) });
  if (u.includes('Departamentos-mps/16.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BOGOTA_MUN) });
  if (u.includes('COMUNAS_DATA.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: COMUNAS });
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.endsWith('/jal-teusaquillo.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MESAS) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.fulfill({ status: 404, body: '' });
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.loadHistoricalMap === 'function' && typeof window.L === 'object');

await p.evaluate(meta => {
  crmCandidate = { nombre: 'RICARDO RUIZ', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion: 'TEUSAQUILLO · BOGOTÁ D.C.', partido: 'Alianza Verde', votos: 1880, slug: 'JAL2015-16-1-13-1', dataUrl: 'https://stub.test/jal-teusaquillo.json' };
  showScreen('crm'); document.getElementById('crmVoteNumber').textContent = meta.toLocaleString('es-CO');
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true;
  document.getElementById('otherCorporation').value = 'jal';
  document.getElementById('campaignDepartment').innerHTML = '<option value="16">Bogotá D.C.</option>'; document.getElementById('campaignDepartment').value = '16';
}, META);
/* Los municipios se cargan como en la página, para resolver el código electoral. */
await p.evaluate(() => loadCampaignMunicipalities());
await p.waitForTimeout(400);
await p.evaluate(() => { document.getElementById('campaignMunicipality').value = 'BOGOTÁ, D.C.'; return loadCampaignLocalities(); });
await p.waitForTimeout(400);

const r = {};
await p.evaluate(() => { document.getElementById('campaignLocality').value = 'TUNJUELITO'; });
r.alcance = await p.evaluate(() => alcanceObjetivo());
r.mesas = await p.evaluate(() => {
  const a = alcanceObjetivo();
  return { suya: mesaEnAlcance({ dep: '16', mun: '001', comNom: 'TEUSAQUILLO' }, a),
    nueva: mesaEnAlcance({ dep: '16', mun: '001', comNom: 'TUNJUELITO' }, a),
    prefijada: mesaEnAlcance({ dep: '16', mun: '001', comNom: '06LOCALIDAD 06 TUNJUELITO' }, a),
    otroMunicipio: mesaEnAlcance({ dep: '01', mun: '001', comNom: 'TUNJUELITO' }, a) };
});
/* El recorte se mira aparte: dice que su historial no está en Tunjuelito sin
   que eso signifique borrarlo del mapa. */
r.recorte = await p.evaluate(async () => { const rec = (await datosCandidatura(crmCandidate)).recorte; return { sinVotos: rec.sinVotos, fuera: rec.mesasFuera, dentro: rec.votosDentro, lugar: lugarDelAlcance(rec), nota: notaRecorte(rec) }; });

await p.evaluate(() => { datosCandidaturaCache.clear(); return loadHistoricalMap(crmCandidate); });
await p.waitForTimeout(1400);
r.total = await p.evaluate(() => ({
  titulo: document.getElementById('crmMapTitle').textContent, panel: document.getElementById('crmMapPanelNum').textContent,
  niveles: [...document.querySelectorAll('.crm-map-levels [data-level]')].map(x => x.textContent.trim()),
  votos: crmMapState?.votesByArea, desglose: document.getElementById('crmBreakdownTitle')?.textContent,
  filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
  nota: document.getElementById('crmMapNote').textContent, modos: [...document.querySelectorAll('#crmMapToggles [data-mode]')].map(x => x.textContent.trim()),
}));
await p.screenshot({ path: SP + '/jal-total-teusaquillo.png' });
r.proy = await p.evaluate(() => { crmMapMode = 'proyectado'; refreshCRMMapMode(); return {
  reparto: projectedVotesByArea(), desglose: document.getElementById('crmBreakdownTitle')?.textContent,
  filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
  nota: document.getElementById('crmMapNote').textContent }; });
await p.screenshot({ path: SP + '/jal-proyectado-tunjuelito.png' });

/* Control 1: quedarse en Teusaquillo no cambia nada —la meta ya estaba ahí—. */
r.misma = await p.evaluate(async () => { document.getElementById('campaignLocality').value = 'TEUSAQUILLO'; datosCandidaturaCache.clear();
  const rec = (await datosCandidatura(crmCandidate)).recorte; crmMapMode = 'proyectado'; refreshCRMMapMode();
  return { sinVotos: rec.sinVotos, dentro: rec.votosDentro, reparto: projectedVotesByArea() }; });
/* Control 2: mudarse de CIUDAD sí cambia el mapa por el territorio nuevo, y el
   primer nivel se llama por la unidad que se dibuja —en Bogotá, localidad—. */
r.ciudad = await p.evaluate(async () => {
  crmCandidate = { ...crmCandidate, corp: 'CONCEJO · LA CEJA · ANTIOQUIA · 2019', circunscripcion: 'LA CEJA (ANTIOQUIA)' };
  document.getElementById('otherCorporation').value = 'concejo';
  document.getElementById('campaignLocality').value = '';
  datosCandidaturaCache.clear(); window.datosCandidatura = async () => ({ mesas: [{ dep: '01', mun: '021', zon: '01', pue: '01', munNom: 'LA CEJA', v: 900 }], recorte: { sinVotos: true } });
  await loadHistoricalMap(crmCandidate);
  return { titulo: document.getElementById('crmMapTitle').textContent, niveles: [...document.querySelectorAll('.crm-map-levels [data-level]')].map(x => x.textContent.trim()) };
});
await b.close();

const pruebas = [
  ['el alcance de una JAL es la localidad, con su municipio adentro', r.alcance?.tipo === 'localidad' && r.alcance.localidad === 'TUNJUELITO' && r.alcance.municipio === '1' && r.alcance.departamento === '16'],
  ['una mesa de Teusaquillo queda FUERA del alcance de Tunjuelito', r.mesas.suya === false],
  ['y una de Tunjuelito queda dentro, venga pelada o con el código pegado', r.mesas.nueva === true && r.mesas.prefijada === true],
  ['el municipio sigue mandando: Tunjuelito de otro departamento no cuenta', r.mesas.otroMunicipio === false],
  ['el recorte sabe que su historial no está en Tunjuelito', r.recorte.sinVotos === true && r.recorte.fuera === 2 && r.recorte.dentro === 0 && /no tiene mesas en Tunjuelito/.test(r.recorte.nota) && !/Bogot/i.test(r.recorte.lugar)],
  ['pero mudarse de localidad no borra el mapa: sigue siendo Bogotá', /votación en Bogotá/i.test(r.total.titulo) && !/territorio de campaña/i.test(r.total.panel)],
  ['con los niveles de una ciudad: Localidad y Barrio, nunca Municipio', r.total.niveles.join('|') === 'Localidad|Barrio'],
  ['y «Total» muestra los votos que sí existen, los de Teusaquillo', r.total.votos['13'] === 1880 && /Votos por localidad/.test(r.total.desglose) && r.total.filas.some(f => /Teusaquillo\s*1\.880/.test(f))],
  ['«Proyectado» lleva la meta COMPLETA a Tunjuelito', r.proy.reparto['06'] === META && !r.proy.reparto['13']],
  ['y el desglose deja Teusaquillo en cero', /Meta proyectada por localidad/.test(r.proy.desglose) && r.proy.filas.length === 1 && /Tunjuelito\s*2\.400/.test(r.proy.filas[0])],
  ['la nota dice por qué no reparte: a una JAL se entra por una sola', /una sola localidad/.test(r.proy.nota) && /Tunjuelito/.test(r.proy.nota) && !/proporcionalmente/.test(r.proy.nota)],
  ['quedarse en la misma localidad no es mudanza y la meta no se mueve', r.misma.sinVotos === false && r.misma.dentro === 1880 && r.misma.reparto['13'] === META],
  ['mudarse de CIUDAD sí cambia el mapa por el territorio nuevo', /territorio de campaña/i.test(r.ciudad.titulo)],
  ['y ahí el primer nivel también se llama por su unidad, no «Municipio»', r.ciudad.niveles.join('|') === 'Localidad|Puestos'],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2600));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
