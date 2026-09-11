/* prueba-puestos.mjs — donde no hay barrios, hay puestos.
   ------------------------------------------------------------------
   En un municipio sin capa de comunas —La Ceja, Sabaneta, el 90 % del país—
   el mapa mostraba el polígono del municipio y nada más: ni niveles ni forma
   de bajar. Ahora el mapa trae «Municipio | Puestos»: los puestos de votación
   en su coordenada, agrupados por el barrio que les asigna la Registraduría,
   con el tamaño del punto como votación.

   Y en las ciudades con comunas, el tercer nivel se llama por lo que hay:
   «Barrio» donde hay cartografía, «Puestos» donde no.

   De paso: si la campaña nueva es en Bogotá y el historial no tiene un solo
   voto allá (Daniel Carvalho: Cámara Antioquia → Concejo de Bogotá), el mapa
   no puede ser un Bogotá vacío; se queda donde estuvo la votación.

     node tools/candidato-360/prueba-puestos.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8'), leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');

/* Antioquia con un solo municipio: La Ceja (electoral 01-021), una caja. */
const ANTIOQUIA = { type: 'FeatureCollection', features: [
  { type: 'Feature', properties: { mpio_cnmbr: 'LA CEJA', mun_elec: '021' }, geometry: { type: 'Polygon', coordinates: [[[-75.47, 5.98], [-75.40, 5.98], [-75.40, 6.05], [-75.47, 6.05], [-75.47, 5.98]]] } },
] };
const fila = (code, barrio, lat, lng) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = String(lat); r[10] = String(lng); r[13] = '900'; r[14] = '800'; return r.join(';'); };
const PUESTOS = ['CABECERA', fila('010210101', 'CENTRO', 6.03, -75.43), fila('010210102', 'SAN CAYETANO', 6.02, -75.44), fila('010210103', 'FATIMA', 6.01, -75.42)].join('\n');
const MESAS = [
  { dep: '01', mun: '021', zon: '01', pue: '01', com: '', comNom: '', munNom: 'LA CEJA', pueNom: 'CENTRO', v: 5000 },
  { dep: '01', mun: '021', zon: '01', pue: '02', com: '', comNom: '', munNom: 'LA CEJA', pueNom: 'SAN CAYETANO', v: 2000 },
  { dep: '01', mun: '021', zon: '01', pue: '03', com: '', comNom: '', munNom: 'LA CEJA', pueNom: 'FATIMA', v: 1440 },
];

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('tile.openstreetmap.org')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eee"/></svg>' });
  if (u.includes('Departamentos-mps/01.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ANTIOQUIA) });
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.endsWith('/cand-la-ceja.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mesas: MESAS }) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.loadHistoricalMap === 'function' && typeof window.L === 'object');

await p.evaluate(() => {
  crmCandidate = { nombre: 'ALGUIEN DE LA CEJA', corp: 'ALCALDÍA · LA CEJA · 2023', circunscripcion: 'LA CEJA (ANTIOQUIA)', partido: 'MOVIMIENTO SALVACIÓN NACIONAL', votos: 8440, slug: 'ALC2023-1-21-1', dataUrl: 'https://stub.test/cand-la-ceja.json' };
  CAMPANA_ACTUAL = { corp: 'alcaldia', partido: 'MOVIMIENTO SALVACIÓN NACIONAL', departamento: '01' };
  showScreen('crm'); document.getElementById('crmVoteNumber').textContent = '9.000';
});
await p.evaluate(() => loadHistoricalMap(crmCandidate));
await p.waitForTimeout(1200);

const r = {};
r.niveles = await p.evaluate(() => [...document.querySelectorAll('.crm-map-levels [data-level]')].map(b => b.textContent.trim()));
r.activo = await p.evaluate(() => document.querySelector('.crm-map-levels .active')?.dataset.level);
await p.evaluate(() => document.querySelector('.crm-map-levels [data-level="puestos"]').click());
await p.waitForTimeout(900);
r.puestos = await p.evaluate(() => ({
  puntos: crmBarrioLayer ? crmBarrioLayer.getLayers().length : 0,
  radios: crmBarrioLayer ? crmBarrioLayer.getLayers().map(l => l.getRadius()).sort((a, b) => b - a) : [],
  filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
  titulo: document.querySelector('#crmBreakdown h4')?.textContent || '',
  nota: document.getElementById('crmMapNote').textContent,
  callejero: !!crmTileLayer,
  activo: document.querySelector('.crm-map-levels .active')?.dataset.level,
}));
await p.screenshot({ path: SP + '/puestos-la-ceja.png' });
await p.evaluate(() => document.querySelector('.crm-map-levels [data-level="municipio"]').click());
await p.waitForTimeout(500);
r.vuelta = await p.evaluate(() => ({ puntos: crmBarrioLayer, activo: document.querySelector('.crm-map-levels .active')?.dataset.level, poligono: crmLeafletMap.hasLayer(crmMapLayer) }));
/* La etiqueta del tercer nivel en las ciudades con comunas. */
r.etiquetas = await p.evaluate(() => ({ pereira: ciudadTieneBarrios({ city: 'PEREIRA' }), ibague: ciudadTieneBarrios({ city: 'IBAGUE' }), bogota: ciudadTieneBarrios({ city: 'BOGOTA' }), otra: ciudadTieneBarrios({ city: 'SINCELEJO' }) }));
/* La campaña nueva en el Concejo de Bogotá, sin un voto histórico allá. */
await p.evaluate(() => {
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true;
  document.getElementById('otherCorporation').value = 'concejo';
  document.getElementById('campaignDepartment').innerHTML = '<option value="16">BOGOTÁ D.C.</option>'; document.getElementById('campaignDepartment').value = '16';
  document.getElementById('campaignMunicipality').innerHTML = '<option value="BOGOTÁ, D.C.">BOGOTÁ, D.C.</option>'; document.getElementById('campaignMunicipality').value = 'BOGOTÁ, D.C.';
});
await p.evaluate(() => loadHistoricalMap(crmCandidate));
await p.waitForTimeout(1200);
r.bogota = await p.evaluate(() => ({ titulo: document.getElementById('crmMapTitle').textContent, nota: document.getElementById('crmMapNote').textContent, votos: document.getElementById('crmMapVotes').textContent, niveles: [...document.querySelectorAll('.crm-map-levels [data-level]')].map(b => b.textContent.trim()), recorte: recorteActivo && { sinVotos: recorteActivo.sinVotos, fuera: recorteActivo.mesasFuera } }));
await p.screenshot({ path: SP + '/puestos-bogota-sin-votos.png' });
await b.close();

const pruebas = [
  ['un municipio sin comunas trae los niveles Municipio y Puestos', r.niveles.join('|') === 'Municipio|Puestos' && r.activo === 'municipio'],
  ['«Puestos» pinta cada puesto en su coordenada', r.puestos.puntos === 3 && r.puestos.activo === 'puestos'],
  ['el tamaño del punto es la votación', r.puestos.radios[0] > r.puestos.radios[1] && r.puestos.radios[1] > r.puestos.radios[2]],
  ['el desglose lista los puestos por barrio, de mayor a menor', /CENTRO/.test(r.puestos.filas[0] || '') && /5.000/.test(r.puestos.filas[0] || '') && r.puestos.filas.length === 3 && /puesto de votación/i.test(r.puestos.titulo)],
  ['con callejero debajo, que a esa escala hace falta', r.puestos.callejero === true],
  ['y la nota dice que son puestos y no barrios', /Puestos de votación de LA CEJA/.test(r.puestos.nota) && /tamaño del punto/i.test(r.puestos.nota)],
  ['«Municipio» devuelve el polígono y quita los puntos', r.vuelta.puntos === null && r.vuelta.activo === 'municipio' && r.vuelta.poligono === true],
  ['en las ciudades con comunas la etiqueta va según haya cartografía', r.etiquetas.pereira && r.etiquetas.ibague && r.etiquetas.bogota && !r.etiquetas.otra],
  ['si la campaña es en Bogotá pero no hay votos allá, el mapa se queda en La Ceja', /LA CEJA/.test(r.bogota.titulo) && r.bogota.votos === '8.440 votos' && r.bogota.niveles.join('|') === 'Municipio|Puestos'],
  ['y la nota lo dice, en vez de «quedaron por fuera 8.440 votos»', /no tiene mesas en BOGOTÁ, D\.C\./.test(r.bogota.nota) && !/quedaron por fuera/.test(r.bogota.nota) && r.bogota.recorte?.sinVotos === true],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 1800));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
