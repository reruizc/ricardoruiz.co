/* prueba-indeciso.mjs — «No me he decidido»: familia política ahora, partido después.
   ------------------------------------------------------------------
   Queda más de un año de campaña y mucha gente no tiene partido todavía. En
   el paso del aval hay una tercera opción, para cualquier corporación: elegir
   dónde se siente mejor ideológicamente en el mismo espectro de cinco puntos
   de las firmas. Con esa familia se calcula todo —bloque, frase, electorado—
   y en el CRM queda el botón «Ya tengo partido político» para ponerlo cuando
   lo tenga. Las firmas siguen siendo solo de los cargos uninominales.

     node tools/candidato-360/prueba-indeciso.mjs                             */

const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const DEPARTAMENTOS = { type: 'FeatureCollection', features: ['Antioquia', 'Distrito Capital de Bogotá'].map(name => ({ type: 'Feature', properties: { name }, geometry: null })) };
const MUNICIPIOS = {
  '16': { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'BOGOTÁ, D.C.', mun_elec: '001' }, geometry: null }] },
  /* Antioquia trae un municipio de los otros: los que NO tienen resultados por
     comuna, que son el 95 % del país. */
  '01': { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'LA CEJA', mun_elec: '163' }, geometry: null }] },
};
/* Concejo de Bogotá 2023 por localidad: dos partidos de centro-izquierda y uno
   de derecha, repartidos distinto entre dos localidades. */
const CONCEJO = { data: { '16-001': { comunas: {
  '11': { nombre: 'SUBA', votantes: 300000, partidos: [['PARTIDO ALIANZA VERDE', 40000], ['PARTIDO CENTRO DEMOCRÁTICO', 30000]] },
  '19': { nombre: 'CIUDAD BOLIVAR', votantes: 200000, partidos: [['PARTIDO ALIANZA VERDE', 10000], ['PARTIDO CENTRO DEMOCRÁTICO', 8000]] },
} } } };
/* PUESTOS_GEOREF: censo por puesto, que es de donde sale el requisito legal. */
const fila = (code, barrio, mujeres, hombres) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = '4.7'; r[10] = '-74.07'; r[13] = String(mujeres); r[14] = String(hombres); return r.join(';'); };
const PUESTOS = ['CABECERA', fila('160010101', 'SUBA', 60000, 55000), fila('160010102', 'CIUDAD BOLIVAR', 45000, 40000),
  /* La Ceja: 30.000 de censo repartido en tres puestos, uno de ellos sin barrio. */
  fila('011630101', 'CENTRO', 9000, 6000), fila('011630102', 'SAN CAYETANO', 5000, 5000), fila('011639901', 'NO APLICA', 3000, 2000)].join('\n');

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1300, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
const json = x => ({ status: 200, contentType: 'application/json', body: JSON.stringify(x) });
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('DEPARTAMENTOS2.json')) return route.fulfill(json(DEPARTAMENTOS));
  const mps = u.match(/Departamentos-mps\/(\d+)\.json/);
  if (mps) return MUNICIPIOS[mps[1]] ? route.fulfill(json(MUNICIPIOS[mps[1]])) : route.fulfill({ status: 404, body: '' });
  if (u.includes('resultados-concejo-2023.json')) return route.fulfill(json(CONCEJO));
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.endsWith('/cand.json')) return route.fulfill(json({ mesas: [{ dep: '16', mun: '001', zon: '11', pue: '01', com: '11', comNom: '11SUBA', munNom: 'BOGOTÁ, D.C.', v: 500 }] }));
  if (u.includes('/c360/')) return route.fulfill(json({ ok: true, acceso: true, fuente: 'admin', vinculo: null }));
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pintarFirmas === 'function');
await p.waitForFunction(() => document.getElementById('department').options.length > 1);

const CAND = { nombre: 'ALGUIEN DE BOGOTÁ', slug: 'CONC2023-16-1-1-1', corp: 'CONCEJO · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', partido: 'PARTIDO ALIANZA VERDE', votos: 9000, dataUrl: 'https://stub.test/cand.json' };
const r = {};
await p.evaluate(c => abrirRutaCandidato(c), CAND);
/* Concejo: por lista, sin firmas; pero «no me he decidido» sí aparece. */
await p.evaluate(() => { document.querySelector('input[name="corporationRoute"][value="other"]').checked = true; toggleCorporationChoice(); document.getElementById('otherCorporation').value = 'concejo'; updateCampaignTerritory(); irAPaso('partido'); });
await p.waitForTimeout(400);
r.concejo = await p.evaluate(() => ({ opciones: !document.getElementById('avalOpciones').classList.contains('hidden'), firmas: !document.querySelector('.route-option[data-aval="firmas"]').classList.contains('hidden'), indeciso: !document.querySelector('.route-option[data-aval="indeciso"]').classList.contains('hidden') }));
await p.evaluate(() => { document.querySelector('input[name="avalRuta"][value="indeciso"]').checked = true; elegirAval({ animar: true }); });
await p.waitForTimeout(400);
r.indeciso = await p.evaluate(() => ({ espectro: !document.getElementById('espectroField').classList.contains('hidden'), partido: !document.getElementById('campaignPartyField').classList.contains('hidden'), titulo: document.getElementById('rutaTitulo').textContent, deshabilitado: document.getElementById('abrirCRM').disabled }));
await p.evaluate(() => document.querySelector('#espectro [data-bloque="cd"]').click());
await p.waitForTimeout(200);
r.conEspectro = await p.evaluate(() => ({ deshabilitado: document.getElementById('abrirCRM').disabled, campana: campanaActual('concejo'), bloque: bloqueVigente() }));
r.frase = await p.evaluate(() => fraseDePartida({ candidate: crmCandidate, corpKey: 'concejo', territory: 'Medellín', campana: campanaActual('concejo') }));
/* Al CRM: el botón para definir el partido está, la tarjeta de firmas no. La
   ruta «otra corporación» exige territorio, como en la vida real. */
await p.evaluate(async () => { document.getElementById('campaignDepartment').value = '01'; await loadCampaignMunicipalities(); document.getElementById('campaignMunicipality').value = 'LA CEJA'; });
await p.evaluate(async () => { PRUEBAS = true; SESSION.acceso = true; await launchCRM(); });
await p.waitForTimeout(600);
r.crm = await p.evaluate(() => ({ pantalla: !document.getElementById('crm').classList.contains('hidden'), boton: !document.getElementById('crmPartidoPendiente').classList.contains('hidden'), firmas: document.getElementById('crmFirmas').classList.contains('hidden'), avales: CAMPANA_ACTUAL?.avales, bloque: bloqueVigente(), partidoVigente: partidoVigente(), contexto: document.getElementById('crmContext').textContent }));
await p.evaluate(() => definirPartido());
await p.waitForTimeout(400);
r.definir = await p.evaluate(() => ({ pantalla: !document.getElementById('candidateRoute').classList.contains('hidden'), aval: avalVigente(), partido: !document.getElementById('campaignPartyField').classList.contains('hidden'), espectro: document.getElementById('espectroField').classList.contains('hidden') }));
/* Al volver con la campaña guardada, el espectro viene puesto. */
await p.evaluate(async () => { await precargarCampana({ corp: 'concejo', avales: 'indeciso', espectro: 'ci', ruta: 'other', departamento: '01', departamentoNombre: 'Antioquia', municipio: 'MEDELLÍN', localidad: '' }); });
await p.waitForTimeout(500);
r.precarga = await p.evaluate(() => ({ aval: avalVigente(), espectro: espectroVigente() }));
/* Alcaldía: las tres opciones. */
await p.evaluate(() => { document.getElementById('otherCorporation').value = 'alcaldia'; updateCampaignTerritory(); irAPaso('partido'); });
await p.waitForTimeout(300);
r.alcaldia = await p.evaluate(() => ({ firmas: !document.querySelector('.route-option[data-aval="firmas"]').classList.contains('hidden'), indeciso: !document.querySelector('.route-option[data-aval="indeciso"]').classList.contains('hidden') }));
await b.close();

const pruebas = [
  ['en un concejo no hay firmas, pero «no me he decidido» sí', r.concejo.opciones && !r.concejo.firmas && r.concejo.indeciso],
  ['elegirlo abre el espectro, quita el partido y cambia la pregunta', r.indeciso.espectro && !r.indeciso.partido && /ideológicamente/.test(r.indeciso.titulo) && r.indeciso.deshabilitado],
  ['con el espectro puesto se puede seguir, y la campaña lo guarda', !r.conEspectro.deshabilitado && r.conEspectro.campana.avales === 'indeciso' && r.conEspectro.campana.espectro === 'cd' && r.conEspectro.campana.partido === ''],
  ['el bloque vigente es el del espectro', r.conEspectro.bloque === 'cd'],
  ['la frase de partida lo dice sin inventarle partido', /no tiene partido/.test(r.frase) && /centro-derecha/.test(r.frase) && /CRM/.test(r.frase)],
  /* Ya con la campaña guardada no hay partido vigente: antes de abrir el CRM,
     partidoVigente() cae al histórico por diseño, igual que con firmas. */
  ['en el CRM está «Ya tengo partido político», no la tarjeta de firmas, y ningún partido vigente', r.crm.pantalla && r.crm.boton && r.crm.firmas && r.crm.avales === 'indeciso' && r.crm.bloque === 'cd' && r.crm.partidoVigente === ''],
  ['el botón vuelve al paso del partido con «con un partido» marcado', r.definir.pantalla && r.definir.aval === 'partido' && r.definir.partido && r.definir.espectro],
  ['al volver con la campaña guardada el espectro viene puesto', r.precarga.aval === 'indeciso' && r.precarga.espectro === 'ci'],
  ['en la alcaldía están las tres opciones', r.alcaldia.firmas && r.alcaldia.indeciso],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
