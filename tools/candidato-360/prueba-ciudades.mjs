/* prueba-ciudades.mjs — el mapa fuera de Bogotá: encuadre, barrios y modales.
   ------------------------------------------------------------------
   Cuatro cosas que se veían mal en Cali y Medellín:

     · el municipio llega hasta los Farallones, así que encuadrar por el
       polígono completo dejaba la ciudad del tamaño de una uña;
     · «Proyectado» seguía titulando «¿Dónde ESTUVO su votación?», que es lo
       contrario de lo que muestra;
     · fuera de Bogotá y Cali no había barrios, solo puntos de puestos;
     · y al abrir una ficha, el mapa se dibujaba ENCIMA del modal (Leaflet pone
       sus paneles en z-index 400-1000 y no los encierra).

   Todo lo remoto va simulado: una Medellín de dos comunas, tres barrios y tres
   puestos de votación con coordenada.

     node tools/candidato-360/prueba-ciudades.mjs                              */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8');
const leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');

const caja = (props, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: props,
  geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });

/* Medellín: comuna 06 (urbana, con votos) y comuna 60 (corregimiento enorme,
   sin votos) — el caso que achicaba el mapa. */
const MEDELLIN = { type: 'FeatureCollection', features: [
  caja({ CODIGO: '06', NOMBRE: 'DOCE DE OCTUBRE' }, [-75.58, 6.29, -75.55, 6.32]),
  caja({ CODIGO: '60', NOMBRE: 'SAN CRISTOBAL' },   [-75.75, 6.15, -75.50, 6.45]),
] };
const BARRIOS_MDE = { type: 'FeatureCollection', features: [
  caja({ CODIGO: '0601', NOMBRE: 'El Triunfo',   COMUNA: 'Doce de Octubre' }, [-75.58, 6.29, -75.57, 6.30]),
  caja({ CODIGO: '0602', NOMBRE: 'Pedregal',     COMUNA: 'Doce de Octubre' }, [-75.57, 6.29, -75.56, 6.30]),
  caja({ CODIGO: '0603', NOMBRE: 'La Esperanza', COMUNA: 'Doce de Octubre' }, [-75.56, 6.29, -75.55, 6.30]),
  caja({ CODIGO: '9901', NOMBRE: 'Otro Lado',    COMUNA: 'San Cristóbal' },   [-75.70, 6.20, -75.69, 6.21]),
] };
/* PUESTOS_GEOREF: 41 columnas; importan la 1 (código), 7 (barrio), 9/10
   (lat/lng), 11/12 (comuna) y 13/14 (censo). */
const fila = (code, barrio, lat, lng, com, comNom, mujeres, hombres) => {
  const r = new Array(16).fill('');
  r[1] = code; r[7] = barrio; r[9] = String(lat); r[10] = String(lng); r[11] = com; r[12] = comNom; r[13] = String(mujeres); r[14] = String(hombres);
  return r.join(';');
};
const PUESTOS = ['CABECERA',
  fila('010010601', 'LA ESPERANZA #2', 6.295, -75.575, '06', '06COMUNA 6', 5000, 4000),   /* El Triunfo */
  fila('010010602', 'PEDREGAL',        6.295, -75.565, '06', '06COMUNA 6', 3000, 2000),   /* Pedregal */
  fila('010010603', 'LA ESPERANZA',    6.295, -75.555, '06', '06COMUNA 6', 9000, 8000),   /* La Esperanza, sin votos suyos */
  fila('010016001', 'VEREDA',          6.205, -75.695, '60', '60SAN CRISTOBAL', 900, 800),
].join('\n');

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('tile.openstreetmap.org')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eee"/></svg>' });
  if (u.includes('MEDELLIN_BARRIOS_OFICIAL')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BARRIOS_MDE) });
  if (u.includes('MEDELLINX.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MEDELLIN) });
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.renderJalCityMap === 'function' && typeof window.L === 'object');

/* Una edil del Doce de Octubre: todos sus votos en la comuna 06. */
await p.evaluate(() => {
  window.datosCandidatura = async () => ({ mesas: [
    { dep: '01', mun: '001', zon: '06', pue: '01', com: '06', comNom: 'COMUNA 6', munNom: 'MEDELLIN', v: 400 },
    { dep: '01', mun: '001', zon: '06', pue: '02', com: '06', comNom: 'COMUNA 6', munNom: 'MEDELLIN', v: 200 },
  ] });
  crmCandidate = { nombre: 'ALGUIEN DE MEDELLIN', corp: 'JAL · COMUNA 6 · MEDELLIN · 2023', circunscripcion: 'MEDELLIN (ANTIOQUIA)', partido: 'PARTIDO X', votos: 600, slug: 'x' };
  showScreen('crm');
  document.getElementById('crmVoteNumber').textContent = '1.800';
});
await p.evaluate(() => renderJalCityMap(crmCandidate));
await p.waitForTimeout(900);

const r = {};
r.encuadre = await p.evaluate(() => {
  const mapa = crmLeafletMap.getBounds();
  const rural = crmMapLayer.getLayers().find(l => l.feature.properties.CODIGO === '60').getBounds();
  return { ruralDentro: mapa.contains(rural), anchoMapa: +(mapa.getEast() - mapa.getWest()).toFixed(3), anchoRural: +(rural.getEast() - rural.getWest()).toFixed(3) };
});
/* El caso que dejaba a Cali diminuta: el mapa se arma mientras el panel
   todavía se acomoda, Leaflet mide de menos y elige un zoom para una caja que
   ya no existe. Acá se simula midiendo con el contenedor encogido. */
r.reencuadre = await p.evaluate(async () => {
  const caja = document.getElementById('crmMap');
  caja.style.height = '90px';
  crmLeafletMap.invalidateSize();
  await renderJalCityMap(crmCandidate);
  caja.style.height = '';                       /* el panel termina de acomodarse */
  await new Promise(r => setTimeout(r, 500));
  const mapa = crmLeafletMap.getBounds(), capa = crmMapLayer.getLayers().find(l => l.feature.properties.CODIGO === '06').getBounds();
  return { veces: +((mapa.getNorth() - mapa.getSouth()) / (capa.getNorth() - capa.getSouth())).toFixed(2) };
});
r.tituloTotal = await p.textContent('#crmMapTitle');
await p.evaluate(() => { crmMapMode = 'proyectado'; refreshCRMMapMode(); });
r.tituloProyectado = await p.textContent('#crmMapTitle');
await p.evaluate(() => { crmMapMode = 'total'; refreshCRMMapMode(); });

/* Barrios de la comuna 6, ubicados por coordenada. */
await p.evaluate(() => renderBarriosForArea('06'));
await p.waitForTimeout(1200);
r.barrios = await p.evaluate(() => ({
  poligonos: crmBarrioLayer ? crmBarrioLayer.getLayers().length : 0,
  esPoligono: Boolean(crmBarrioLayer?.getLayers()[0]?.feature),
  filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
  titulo: document.querySelector('#crmBreakdown h4')?.textContent || '',
}));
await p.screenshot({ path: SP + '/ciudades-barrios.png' });
/* Con la meta y sin votos propios en un barrio, el censo lo reparte. */
r.censo = await p.evaluate(async () => {
  crmMapMode = 'proyectado';
  window.projectedVotesByArea = () => ({ '06': 1800 });
  crmMapState.mesas = [];
  await renderBarriosForArea('06');
  await new Promise(r => setTimeout(r, 700));
  return { filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()), nota: document.getElementById('crmMapNote').textContent };
});

/* El modal por encima del mapa. */
await p.evaluate(() => {
  PUNTAJE_ACTUAL = { candidatura: { corp: 'JAL · COMUNA 6 · MEDELLIN · 2023', votos: 600 }, votos: 600, puntaje: 40, cuartil: null };
  mostrarPuntajeInfo();
});
await p.waitForTimeout(600);          /* la tarjeta entra con una animación de .28 s */
r.modal = await p.evaluate(() => {
  const card = document.querySelector('#introModal .intro-modal-card'), c = card.getBoundingClientRect();
  const mapa = document.getElementById('crmMap').getBoundingClientRect();
  /* Un punto de la tarjeta que caiga ENCIMA del mapa: es donde se veía el
     mapa a través del modal. */
  const y = Math.min(c.bottom - 20, Math.max(c.top + 20, mapa.top + 40));
  const encima = document.elementFromPoint(c.left + c.width / 2, y);
  return { abierto: document.getElementById('introModal').classList.contains('open'), sobreMapa: y > mapa.top && y < mapa.bottom,
    tapa: Boolean(encima && (card.contains(encima) || encima === card)), quien: encima?.className || '', opacidad: getComputedStyle(card).opacity };
});
await p.screenshot({ path: SP + '/ciudades-modal.png' });
await b.close();

const pruebas = [
  ['el encuadre deja fuera el corregimiento sin votos', r.encuadre.ruralDentro === false && r.encuadre.anchoMapa < r.encuadre.anchoRural],
  ['si el panel se acomoda después, el mapa se vuelve a encuadrar', r.reencuadre.veces < 3],
  ['en TOTAL el título pregunta dónde estuvo la votación', /¿Dónde estuvo su votación en MEDELLIN\?/.test(r.tituloTotal)],
  ['en PROYECTADO pregunta dónde debería estar', /¿Dónde debería estar su votación en MEDELLIN\?/.test(r.tituloProyectado)],
  ['Medellín ya tiene barrios de verdad, no puntos de puestos', r.barrios.poligonos === 3 && r.barrios.esPoligono === true],
  ['cada puesto cayó en su barrio por coordenada', /El Triunfo/.test(r.barrios.filas[0] || '') && /400/.test(r.barrios.filas[0] || '') && /Pedregal/.test(r.barrios.filas[1] || '')],
  ['sin votos propios, el censo reparte la meta entre los tres barrios', r.censo.filas.length === 3 && /La Esperanza/.test(r.censo.filas[0] || '')],
  ['y la nota avisa que eso es censo', /censo electoral/i.test(r.censo.nota)],
  ['el modal se dibuja POR ENCIMA del mapa', r.modal.abierto === true && r.modal.sobreMapa === true && r.modal.tapa === true && Number(r.modal.opacidad) === 1],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 1800));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
