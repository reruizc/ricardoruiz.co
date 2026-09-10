/* prueba-mapa.mjs — el mapa del CRM sin red: Sumapaz y el callejero barrial.
   ------------------------------------------------------------------
   Comprueba las dos reglas del mapa de Bogotá:
     · Sumapaz SE DIBUJA (es la localidad 20, el 42% de la ciudad) pero NO
       encuadra: si entra al fitBounds, la Bogotá urbana queda del tamaño de
       una uña. Se desborda del marco y el contenedor la recorta.
     · A escala de barrio entra el callejero de OpenStreetMap en gris y
       atenuado —la gente necesita las calles para ubicarse— y se retira la
       capa de localidades, que va rotada 90° y contradice cada calle.

   Todo lo remoto va simulado: Leaflet desde el paquete npm, los tiles como una
   rejilla SVG (para VER si se leen por debajo del color) y una Bogotá de tres
   localidades. Los polígonos de barrio sí son los reales del repo.

   Necesita Leaflet en disco:
     npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz      (deja package/dist/)
     node tools/candidato-360/prueba-mapa.mjs                                  */
/* playwright puede estar local o global; con global basta el NODE_PATH del sistema. */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
/* dist de Leaflet: node_modules, o el `npm pack` desempacado en el cwd. */
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8');
const leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');
// Un "callejero" de mentiras: rejilla de calles para ver si se lee por debajo.
const tile = `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#f2efe9"/><g stroke="#d4cfc4" stroke-width="7">${
  [32,96,160,224].map(v=>`<line x1="0" y1="${v}" x2="256" y2="${v}"/><line x1="${v}" y1="0" x2="${v}" y2="256"/>`).join('')}</g><g stroke="#c9b9a0" stroke-width="11"><line x1="0" y1="128" x2="256" y2="128"/><line x1="128" y1="0" x2="128" y2="256"/></g></svg>`;

// Bogotá de mentiras: dos localidades urbanas al norte y Sumapaz, enorme, al sur.
const caja = (id, nom, [x0,y0,x1,y1]) => ({ type:'Feature', properties:{ LocCodigo:id, LocNombre:nom },
  geometry:{ type:'Polygon', coordinates:[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]] } });
const BOG = { type:'FeatureCollection', features:[
  caja('13','TEUSAQUILLO', [-74.10,4.60,-74.06,4.66]),
  caja('11','SUBA',        [-74.14,4.66,-74.05,4.78]),
  caja('20','SUMAPAZ',     [-74.35,3.72,-74.00,4.50]),   // el 42% de la ciudad, al sur
]};

/* Censo por puesto de votación: 41 columnas, de las que importan la 1 (código
   completo), la 7 (barrio) y la 13/14 (mujeres/hombres). Dos puestos de
   Teusaquillo con censos muy distintos, para ver si el reparto los distingue. */
const filaPuesto = (code, barrio, mujeres, hombres) => [ '1', code, 'BOGOTA D.C.', 'BOGOTA', code.slice(5,7), code.slice(7,9), '', barrio, '', '4.63', '-74.08', '', '', String(mujeres), String(hombres), '10' ].join(';');
/* 13-01 cae en el barrio 007203 (Chapinero Occidental) y 13-03 en el 007206
   (Belalcázar), según el mapa puesto→barrio del repo. Censos muy distintos. */
const PUESTOS = ['CABECERA', filaPuesto('160010101', 'OTRA LOCALIDAD', 1, 1), filaPuesto('160011301', 'CHAPINERO OCCIDENTAL', 20000, 18000), filaPuesto('160011303', 'BELALCAZAR', 3000, 2000)].join('\n');

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('tile.openstreetmap.org')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: tile });
  if (u.includes('BOG-LOCALIDADX')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BOG) });
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok:true, acceso:true, fuente:'admin', vinculo:null, email:'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token','t'); localStorage.setItem('rr-user', JSON.stringify({email:'reruizc@gmail.com'})); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.renderBogotaCampaignMap === 'function' && typeof window.L === 'object');
await p.waitForTimeout(400);

// Mesas de mentiras en Teusaquillo (zona 13) y Suba (11), y a la pantalla del CRM.
await p.evaluate(() => {
  window.datosCandidatura = async () => ({ mesas: [
    { dep:'16', mun:'001', zon:'13', pue:'01', com:'13', comNom:'TEUSAQUILLO', v:342 },
    { dep:'16', mun:'001', zon:'11', pue:'02', com:'11', comNom:'SUBA', v:120 },
  ]});
  crmCandidate = { nombre:'RICARDO ESTEBAN RUIZ CASTRO', corp:'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion:'BOGOTÁ D.C.', votos:462, slug:'x' };
  showScreen('crm');
  document.getElementById('crmVoteNumber').textContent = '900';
});
await p.evaluate(() => renderBogotaCampaignMap(crmCandidate));
await p.waitForTimeout(900);
await p.evaluate(() => refreshMapLevels());
const r = {};
r.sumapazDibujada = await p.evaluate(() => crmMapLayer.getLayers().some(l => String(l.feature.properties.LocCodigo) === '20'));
r.encuadre = await p.evaluate(() => {
  const b = crmLeafletMap.getBounds(), s = crmMapLayer.getLayers().find(l => String(l.feature.properties.LocCodigo) === '20').getBounds();
  return { mapaSur: +b.getSouth().toFixed(3), sumapazSur: +s.getSouth().toFixed(3), sumapazDentro: b.contains(s) };
});
r.sinTilesEnCiudad = await p.evaluate(() => crmTileLayer === null);
await p.screenshot({ path: SP + '/mapa-bogota.png', clip: { x: 0, y: 0, width: 1280, height: 900 } });

// Bajar a barrio (Teusaquillo = 13, hay polígonos locales en el repo)
await p.evaluate(() => renderBarriosForArea('13'));
await p.waitForTimeout(1500);
r.callejero = await p.evaluate(() => {
  const c = crmTileLayer?.getContainer();
  return { hay: !!crmTileLayer, clase: c?.className || '', opacidad: c ? Number(getComputedStyle(c).opacity).toFixed(2) : null, filtro: c ? getComputedStyle(c).filter : null };
});
r.localidadesFuera = await p.evaluate(() => !crmLeafletMap.hasLayer(crmMapLayer));
r.barriosPintados = await p.evaluate(() => crmBarrioLayer ? crmBarrioLayer.getLayers().length : 0);
r.dondeCaenLosBarrios = await p.evaluate(() => { const b = crmBarrioLayer.getBounds(); return { w:+b.getWest().toFixed(4), e:+b.getEast().toFixed(4), s:+b.getSouth().toFixed(4), n:+b.getNorth().toFixed(4) }; });
r.rellenoBarrio = await p.evaluate(() => {
  const l = crmBarrioLayer.getLayers().find(x => x.options.fillOpacity > .3);
  return l ? l.options.fillOpacity : null;
});
await p.screenshot({ path: SP + '/mapa-barrio.png' });

/* La meta por barrio en una localidad donde nunca sacó un voto: sin censo esto
   quedaba en «no hay votos desagregados» y el mapa se veía vacío. */
r.censo = await p.evaluate(async () => {
  crmMapMode = 'proyectado';
  crmMapState.votesByArea = { '13': 0, '11': 120 };
  window.projectedVotesByArea = () => ({ '13': 900, '11': 0 });
  /* Sus mesas siguen en Suba: en Teusaquillo nunca sacó un voto, que es el caso
     que trae un salto de corporación (la meta cae en media ciudad). */
  crmMapState.mesas = [{ dep:'16', mun:'001', zon:'11', pue:'02', com:'11', comNom:'SUBA', v:120 }];
  await renderBarriosForArea('13');
  await new Promise(r => setTimeout(r, 600));
  const filas = [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item')].map(x => x.textContent);
  return { titulo: document.querySelector('#crmBreakdown h4')?.textContent || '', filas, nota: document.getElementById('crmMapNote').textContent,
    pintados: crmBarrioLayer.getLayers().filter(l => l.options.fillOpacity > .3).length };
});

// Y volver a localidad restituye todo
await p.evaluate(() => document.querySelector('.crm-map-levels [data-level="localidad"]').click());
await p.waitForTimeout(700);
r.vuelta = await p.evaluate(() => ({ localidades: crmLeafletMap.hasLayer(crmMapLayer), tiles: crmTileLayer === null, barrios: crmBarrioLayer === null }));
await b.close();

const pruebas = [
  ['Sumapaz se dibuja', r.sumapazDibujada === true],
  ['pero el encuadre no baja hasta Sumapaz', r.encuadre.sumapazDentro === false && r.encuadre.mapaSur > r.encuadre.sumapazSur],
  ['la ciudad rotada sigue sin callejero', r.sinTilesEnCiudad === true],
  ['a nivel barrio aparece el callejero', r.callejero.hay === true],
  ['y va atenuado y en gris', r.callejero.clase.includes('tenue') && Number(r.callejero.opacidad) < .7 && r.callejero.filtro.includes('grayscale')],
  ['las localidades rotadas se quitan mientras dura el barrio', r.localidadesFuera === true],
  ['los barrios se pintan', r.barriosPintados > 10],
  /* Teusaquillo de verdad está en -74,11…-74,06 × 4,61…4,67. Rotados 90° sobre
     (-74,08 · 4,65) se irían a los cerros orientales: la silueta se ve bien y
     no coincide con una sola calle del callejero que está debajo. */
  ['y caen sobre el Teusaquillo real, no sobre su reflejo rotado',
    r.dondeCaenLosBarrios.w > -74.12 && r.dondeCaenLosBarrios.e < -74.06 && r.dondeCaenLosBarrios.s > 4.60 && r.dondeCaenLosBarrios.n < 4.68],
  ['con relleno que deja ver las calles', r.rellenoBarrio !== null && r.rellenoBarrio <= .65],
  ['volver a localidad restituye la ciudad', r.vuelta.localidades === true && r.vuelta.tiles === true && r.vuelta.barrios === true],
  ['sin meta propia, la meta se reparte por censo y el mapa deja de estar vacío',
    r.censo.pintados >= 2 && r.censo.filas.length >= 2],
  ['el reparto sigue el tamaño del censo (Chapinero Occidental pesa más que Belalcázar)',
    /Chapinero Occidental/i.test(r.censo.filas[0] || '') && /Belalcazar/i.test(r.censo.filas[1] || '')],
  ['y la nota avisa que eso es censo, no apoyo', /censo electoral/i.test(r.censo.nota) && /no dónde ya votaron por usted/i.test(r.censo.nota)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify({ censo: r.censo, barrios: r.dondeCaenLosBarrios }, null, 1).slice(0, 1500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
