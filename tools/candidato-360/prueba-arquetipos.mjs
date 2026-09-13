/* prueba-arquetipos.mjs — las dos lecturas del territorio del CRM.
   ------------------------------------------------------------------
   Tres cosas que faltaban:

     · un concejal de Medellín veía el municipio entero como una mancha: el
       mapa por comunas y barrios solo se armaba para la JAL, cuando la
       cartografía es la misma —y el botón «Municipio» dibujaba exactamente lo
       mismo que «Comuna»—;
     · los corregimientos van del 17 al 21 en la Registraduría y del 50 al 90
       en la cartografía del DAP, así que sus votos no caían en ningún
       polígono, y la zona 90 (censo consolidado) se pintaba encima de Santa
       Elena y salía en el desglose como «undefined»;
     · la tarjeta 06 cruza su votación con los arquetipos del Proyecto DC
       (protección, continuidad, supervivencia, castigo, pertenencia) barrio
       por barrio, con la proyección 2027 ajustada por la socia;
     · la tarjeta 07 describe el electorado de sus puestos —sexo del censo y
       peso rural— sin decir jamás quién votó por usted.

   Todo lo remoto va simulado: dos comunas, cuatro barrios, cuatro puestos.

     node tools/candidato-360/prueba-arquetipos.mjs                            */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8'), leafletCSS = await readFile(LEAFLET + '/leaflet.css', 'utf8');

const caja = (props, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: props, geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
const MEDELLIN = { type: 'FeatureCollection', features: [
  caja({ CODIGO: '06', NOMBRE: 'DOCE DE OCTUBRE' }, [-75.58, 6.29, -75.55, 6.32]),
  caja({ CODIGO: '60', NOMBRE: 'SAN CRISTOBAL' },   [-75.75, 6.15, -75.50, 6.45]),
] };
const BARRIOS_MDE = { type: 'FeatureCollection', features: [
  caja({ CODIGO: '0601', NOMBRE: 'El Triunfo', COMUNA: 'Doce de Octubre' }, [-75.58, 6.29, -75.57, 6.30]),
  caja({ CODIGO: '0602', NOMBRE: 'Pedregal',   COMUNA: 'Doce de Octubre' }, [-75.57, 6.29, -75.56, 6.30]),
  caja({ CODIGO: '0603', NOMBRE: 'La Esperanza', COMUNA: 'Doce de Octubre' }, [-75.56, 6.29, -75.55, 6.30]),
  caja({ CODIGO: '6001', NOMBRE: 'La Loma',    COMUNA: 'Corregimiento de San Cristóbal' }, [-75.70, 6.20, -75.69, 6.21]),
] };
const fila = (code, barrio, lat, lng, mujeres, hombres) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = String(lat); r[10] = String(lng); r[13] = String(mujeres); r[14] = String(hombres); return r.join(';'); };
const PUESTOS = ['CABECERA',
  fila('010010601', 'EL TRIUNFO', 6.295, -75.575, 5000, 4000),   /* comuna 06, urbano, 400 votos */
  fila('010010602', 'PEDREGAL',   6.295, -75.565, 3000, 2000),   /* comuna 06, urbano, 200 votos */
  fila('010010603', 'LA ESPERANZA', 6.295, -75.555, 9000, 8000), /* sin votos suyos: solo pesa en el municipio */
  fila('010019901', 'LA LOMA',    6.205, -75.695, 900, 800),     /* zona 99 = rural, 100 votos */
].join('\n');
const MESAS = [
  { dep: '01', mun: '001', zon: '06', pue: '01', com: '06', comNom: '06COMUNA 6 DOCE DE OCTUBRE', munNom: 'MEDELLIN', v: 400 },
  { dep: '01', mun: '001', zon: '06', pue: '02', com: '06', comNom: '06COMUNA 6 DOCE DE OCTUBRE', munNom: 'MEDELLIN', v: 200 },
  { dep: '01', mun: '001', zon: '99', pue: '01', com: '20', comNom: '20CORREGIMIENTO SAN CRISTOBAL', munNom: 'MEDELLIN', v: 100 },
  /* Censo consolidado: zona 90, sin comuna. No es un territorio y no puede
     pintarse como uno —en Medellín el 90 del DAP es Santa Elena—. */
  { dep: '01', mun: '001', zon: '90', pue: '01', com: '000', comNom: 'NACIONAL', munNom: 'MEDELLIN', v: 50 },
];
const familia = (id, color, corto, nombre, evol) => [id, { color, label_corto: corto, orden: 1, base: { id, nombre, emocion: 'e', deseo: `Deseo de ${corto.toLowerCase()}.`, miedo: 'm', sesgo: 's' }, evol: { id: id + '_evol', nombre: evol, emocion: 'e', deseo: 'd', miedo: 'm', sesgo: 's' } }];
const ARQUETIPOS = { familias: ['proteccion', 'castigo', 'pertenencia', 'continuidad'], arquetipos: Object.fromEntries([
  familia('proteccion', '#2563eb', 'Protección', 'Protección y orden cotidiano', 'Protección con resultados'),
  familia('castigo', '#dc2626', 'Castigo', 'Castigo al establecimiento', 'Castigo con alternativa'),
  familia('pertenencia', '#a21caf', 'Pertenencia', 'Pertenencia y arraigo', 'Pertenencia y arraigo'),
  familia('continuidad', '#16a34a', 'Continuidad', 'Esto va bien, que siga', 'Continuidad con gestión'),
]) };
const barrio = (dap, nombre, comuna, a23, a27) => [dap, { dap, comuna, barrio: nombre, arquetipo: { 2015: a23, 2019: a23, 2023: a23 }, proyeccion_2027: { arquetipo_proy: a27, nivel_riesgo: 'Medio', votos_por_arquetipo: { [a27]: 1000 } } }];
const POR_BARRIO = Object.fromEntries([
  barrio('0601', 'El Triunfo', 'Doce de Octubre', 'proteccion', 'proteccion'),
  barrio('0602', 'Pedregal', 'Doce de Octubre', 'castigo', 'castigo'),
  barrio('0603', 'La Esperanza', 'Doce de Octubre', 'proteccion', 'proteccion'),
  barrio('6001', 'La Loma', 'Corregimiento de San Cristóbal', 'pertenencia', 'pertenencia'),
]);
const POR_COMUNA = {
  'Doce de Octubre': { 2023: { dominante: 'proteccion', votos_total: 50000 }, 2027: { dominante: 'proteccion', votos_total: 57000 } },
  'Corregimiento de San Cristóbal': { 2023: { dominante: 'pertenencia', votos_total: 9000 }, 2027: { dominante: 'pertenencia', votos_total: 10000 } },
};
/* El ajuste a mano de la socia: Pedregal pasa de castigo a continuidad en 2027. */
const VOTACION27 = { version: '20260528', barrios: { '0602': { arquetipo_ajustado_2027: 'continuidad' } } };

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1100 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
const json = x => ({ status: 200, contentType: 'application/json', body: JSON.stringify(x) });
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('leaflet.min.css')) return route.fulfill({ status: 200, contentType: 'text/css', body: leafletCSS });
  if (u.includes('tile.openstreetmap.org')) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eee"/></svg>' });
  if (u.includes('MEDELLIN_BARRIOS_OFICIAL')) return route.fulfill(json(BARRIOS_MDE));
  if (u.includes('MEDELLINX.json')) return route.fulfill(json(MEDELLIN));
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.includes('/arquetipos/arquetipos.json')) return route.fulfill(json(ARQUETIPOS));
  if (u.includes('/arquetipos/por-barrio.json')) return route.fulfill(json(POR_BARRIO));
  if (u.includes('/arquetipos/por-comuna.json')) return route.fulfill(json(POR_COMUNA));
  if (u.includes('votacion-2027.json')) return route.fulfill(json(VOTACION27));
  if (u.includes('CENSO_EDAD_PUESTO.json')) return route.fulfill({ status: 403, contentType: 'application/xml', body: '<Error/>' });
  if (u.endsWith('/cand-mde.json')) return route.fulfill(json({ mesas: MESAS }));
  if (u.includes('/c360/')) return route.fulfill(json({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }));
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pintarArquetipos === 'function' && typeof window.L === 'object');

const CAND = { nombre: 'CONCEJAL DE MEDELLIN', corp: 'CONCEJO · MEDELLIN · 2023', circunscripcion: 'MEDELLIN (ANTIOQUIA)', partido: 'PARTIDO X', votos: 700, slug: 'CONC2023-1-1-1-1', dataUrl: 'https://stub.test/cand-mde.json' };
await p.evaluate(c => { crmCandidate = c; CAMPANA_ACTUAL = { corp: 'concejo', partido: 'PARTIDO X' }; showScreen('crm'); document.getElementById('crmVoteNumber').textContent = '2.000'; }, CAND);

/* 1 · El mapa: un concejal de Medellín ve comunas, no el municipio entero. */
await p.evaluate(() => loadHistoricalMap(crmCandidate));
await p.waitForTimeout(1200);
const r = {};
r.mapa = await p.evaluate(() => ({ titulo: document.getElementById('crmMapTitle').textContent, unidad: crmMapState?.config?.title || null, ciudad: crmMapState?.city || null,
  niveles: [...document.querySelectorAll('.crm-map-levels [data-level]')].map(b => b.textContent.trim()),
  activo: document.querySelector('.crm-map-levels .active')?.dataset.level,
  filas: [...document.querySelectorAll('#crmBreakdown .crm-breakdown-item b')].map(x => x.textContent),
  pintadas: Object.keys(crmMapState?.votesByArea || {}) }));

/* 2 · Las dos tarjetas. */
await p.evaluate(() => Promise.all([pintarArquetipos(), pintarPerfil()]));
await p.waitForTimeout(600);
r.arq = await p.evaluate(() => ({ titulo: document.getElementById('crmArqTitulo').textContent, copy: document.getElementById('crmArqCopy').textContent, dato: document.getElementById('crmArqDato').textContent, apagada: document.getElementById('crmArquetipos').classList.contains('module-apagado'), boton: !document.getElementById('crmArqBtn').disabled }));
r.perfil = await p.evaluate(() => ({ titulo: document.getElementById('crmPerfilTitulo').textContent, copy: document.getElementById('crmPerfilCopy').textContent, dato: document.getElementById('crmPerfilDato').textContent, boton: !document.getElementById('crmPerfilBtn').disabled }));
await p.screenshot({ path: SP + '/tarjetas-territorio.png', fullPage: true });

/* 3 · Los modales. */
await p.evaluate(() => mostrarArquetipos());
await p.waitForTimeout(300);
r.modalArq = await p.evaluate(() => ({ titulo: document.getElementById('introModalTitle').textContent, texto: document.getElementById('introModalText').textContent.replace(/\s+/g, ' '), barras: document.querySelectorAll('#introModalText .arq-barra').length, abierto: document.getElementById('introModal').classList.contains('open') }));
await p.screenshot({ path: SP + '/modal-arquetipos.png' });
await p.evaluate(() => { closeIntroModal(); mostrarPerfil(); });
await p.waitForTimeout(300);
r.modalPerfil = await p.evaluate(() => ({ titulo: document.getElementById('introModalTitle').textContent, texto: document.getElementById('introModalText').textContent.replace(/\s+/g, ' ') }));
await p.screenshot({ path: SP + '/modal-perfil.png' });

/* 4 · Fuera de Medellín la tarjeta de arquetipos se apaga y lo dice. */
await p.evaluate(() => { closeIntroModal(); window.datosCandidatura = async () => ({ mesas: [{ dep: '05', mun: '001', zon: '01', pue: '01', munNom: 'TUNJA', v: 500 }] }); crmCandidate = { ...crmCandidate, circunscripcion: 'TUNJA (BOYACA)' }; return pintarArquetipos(); });
await p.waitForTimeout(400);
r.fuera = await p.evaluate(() => ({ titulo: document.getElementById('crmArqTitulo').textContent, apagada: document.getElementById('crmArquetipos').classList.contains('module-apagado'), boton: !document.getElementById('crmArqBtn').disabled }));
await b.close();

/* Sexo: 400×(5000/9000) + 200×(3000/5000) + 100×(900/1700) = 395,2 de 700 = 56,5 %.
   Rural: 100 de 750 = 13,3 % (los 50 del censo consolidado no son ni rural ni urbano). */
const pruebas = [
  ['un concejal de Medellín ve el mapa por comunas, no el municipio entero', r.mapa.unidad === 'comuna' && /Medell/i.test(r.mapa.titulo)],
  ['los niveles son los que cambian el dibujo: sin «Municipio»', r.mapa.niveles.join('|') === 'Comuna|Barrio' && r.mapa.activo === 'localidad'],
  ['un corregimiento (17-21 en la Registraduría) cae en su polígono del DAP', r.mapa.pintadas.includes('60') && r.mapa.filas.some(f => /San Cristobal/.test(f))],
  ['la zona 90 no arma una comuna fantasma ni una fila sin nombre', r.mapa.filas.length === 2 && !r.mapa.filas.some(f => /undefined|^90$/.test(f))],
  ['la tarjeta de arquetipos nombra el arquetipo donde vive su voto', /protección y orden cotidiano/i.test(r.arq.titulo) && r.arq.dato === '57 %' && r.arq.boton && !r.arq.apagada],
  ['y dice en cuántas comunas está', /2 comunas/.test(r.arq.copy)],
  ['el modal reparte sus votos por arquetipo, hoy y en 2027', r.modalArq.barras === 2 && /57 % Protección y orden cotidiano/.test(r.modalArq.texto) && /29 % Castigo/.test(r.modalArq.texto)],
  ['el ajuste a mano de 2027 manda sobre el proyectado tendencial', /Continuidad con gestión/.test(r.modalArq.texto)],
  ['con las comunas y los barrios de su votación', /Doce de Octubre/.test(r.modalArq.texto) && /Pedregal/.test(r.modalArq.texto) && /La Loma/.test(r.modalArq.texto)],
  ['la tarjeta de perfil pondera el censo de sus puestos por sus votos', r.perfil.dato === '56,5 %' && r.perfil.boton],
  ['y compara contra el municipio, no contra el aire', /54,7 %|1,8 %|más mujeres que el promedio del municipio/.test(r.perfil.copy)],
  ['el peso rural sale de la zona 99', /13,3 % de sus votos están en puestos rurales/.test(r.perfil.copy) && /5,2 % del censo del municipio/.test(r.perfil.copy)],
  ['el modal de perfil dice que el voto es secreto y qué falta para la edad', /nadie.{0,40}puede decir quién votó por usted/i.test(r.modalPerfil.texto) && /Edad/.test(r.modalPerfil.texto) && /no está publicado/.test(r.modalPerfil.texto)],
  ['fuera de Medellín la tarjeta se apaga y dice por qué', /solo Medellín/i.test(r.fuera.titulo) && r.fuera.apagada && !r.fuera.boton],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2600));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
