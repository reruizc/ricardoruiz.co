/* prueba-indeciso-nuevo.mjs — «No me he decidido» también en la candidatura nueva.
   ------------------------------------------------------------------
   El wizard preguntaba un partido existente o uno por constituir. Ahora hay
   una tercera respuesta: ninguno todavía, y entonces el espectro de cinco
   puntos, obligatorio para seguir. Con esa familia se calcula todo; en el CRM
   queda «Ya tengo partido político», que vuelve al paso del partido del
   wizard —rellenado desde lo guardado— y al crear de nuevo la campaña queda
   con el partido.

     node tools/candidato-360/prueba-indeciso-nuevo.mjs                       */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));

const DEPARTAMENTOS = { type: 'FeatureCollection', features:
  ['Antioquia', 'Amazonas', 'Boyacá', 'Distrito Capital de Bogotá', 'Vichada'].map(name => ({ type: 'Feature', properties: { name }, geometry: null })) };
const muns = nombres => ({ type: 'FeatureCollection', features: nombres.map(mpio_cnmbr => ({ type: 'Feature', properties: { mpio_cnmbr }, geometry: null })) });
const MUNICIPIOS = { '16': muns(['BOGOTÁ, D.C.']), '01': muns(['MEDELLÍN', 'ENVIGADO', 'BELLO']) };
/* COMUNAS_DATA.csv: dep en la columna 5, municipio en la 6, localidad en la 10 */
const CSV = ['cabecera'].concat(['TEUSAQUILLO', 'CHAPINERO', 'SUBA'].map(l =>
  [0, 1, 2, 3, 4, 'BOGOTA D.C.', 'BOGOTÁ, D.C.', 7, 8, 9, l].join(';'))).join('\n');

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('DEPARTAMENTOS2.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEPARTAMENTOS) });
  const mps = u.match(/Departamentos-mps\/(\d+)\.json/);
  if (mps) return MUNICIPIOS[mps[1]]
    ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MUNICIPIOS[mps[1]]) })
    : route.fulfill({ status: 404, body: '' });
  if (u.includes('COMUNAS_DATA.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: CSV });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.municipioImplicito === 'function');
await p.waitForFunction(() => document.getElementById('department').options.length > 2);

const r = {};
await p.click('#paisPaso [data-pais="co"]'); await p.click('#rutaNueva');
/* El wizard mueve cada campo a su paso y solo el paso activo se ve: el
   departamento vive en el 3. */
await p.evaluate(() => { document.getElementById('newName').value = 'ALGUIEN NUEVO'; document.getElementById('election').value = 'concejo'; updateTerritory(); showNewWizardStep(3); });
await p.selectOption('#department', { label: 'Antioquia' }); await p.waitForTimeout(500);
await p.evaluate(() => { document.getElementById('municipality').value = 'MEDELLÍN'; showNewWizardStep(4); });
await p.evaluate(() => { document.getElementById('partyMode').value = 'indeciso'; toggleParty(); });
await p.waitForTimeout(200);
r.paso = await p.evaluate(() => ({ espectro: !document.getElementById('partyEspectro').classList.contains('hidden'), existente: document.getElementById('partyExisting').classList.contains('hidden'), nuevo: document.getElementById('partyNew').classList.contains('hidden'), opciones: document.querySelectorAll('#espectroNuevo [data-bloque]').length, partidoRequerido: document.getElementById('party').required }));
/* Sin espectro no se crea: se queda en el paso del partido. */
await p.evaluate(async () => { PRUEBAS = true; SESSION.acceso = true; await createNew({ preventDefault() {} }); });
await p.waitForTimeout(300);
r.sinEspectro = await p.evaluate(() => ({ crm: !document.getElementById('crm').classList.contains('hidden'), pasoActivo: [...document.querySelectorAll('.new-wizard-step')].findIndex(s => s.classList.contains('active')) }));
await p.evaluate(() => document.querySelector('#espectroNuevo [data-bloque="izq"]').click());
await p.evaluate(async () => { await createNew({ preventDefault() {} }); });
await p.waitForTimeout(600);
r.crm = await p.evaluate(() => ({ crm: !document.getElementById('crm').classList.contains('hidden'), avales: CAMPANA_ACTUAL?.avales, espectro: CAMPANA_ACTUAL?.espectro, partido: CAMPANA_ACTUAL?.partido, bloque: bloqueVigente(), partidoVigente: partidoVigente(), boton: !document.getElementById('crmPartidoPendiente').classList.contains('hidden'), contexto: document.getElementById('crmContext').textContent }));
/* «Ya tengo partido político» vuelve al wizard, en el paso del partido y con el nombre puesto. */
await p.evaluate(async () => { document.getElementById('newName').value = ''; await definirPartido(); });
await p.waitForTimeout(500);
r.definir = await p.evaluate(() => ({ wizard: !document.getElementById('new').classList.contains('hidden'), pasoActivo: [...document.querySelectorAll('.new-wizard-step')].findIndex(s => s.classList.contains('active')), modo: document.getElementById('partyMode').value, nombre: document.getElementById('newName').value, existente: !document.getElementById('partyExisting').classList.contains('hidden') }));
await p.evaluate(async () => { document.getElementById('party').value = 'PARTIDO ALIANZA VERDE'; await createNew({ preventDefault() {} }); });
await p.waitForTimeout(600);
r.conPartido = await p.evaluate(() => ({ avales: CAMPANA_ACTUAL?.avales, partido: CAMPANA_ACTUAL?.partido, boton: !document.getElementById('crmPartidoPendiente').classList.contains('hidden'), contexto: document.getElementById('crmContext').textContent }));
await b.close();

const pruebas = [
  ['«No me he decidido» abre el espectro y esconde los dos campos de partido', r.paso.espectro && r.paso.existente && r.paso.nuevo && r.paso.opciones === 5 && !r.paso.partidoRequerido],
  ['sin espectro no se crea la candidatura: se queda en el paso del partido', !r.sinEspectro.crm && r.sinEspectro.pasoActivo === 4],
  ['con espectro se crea, sin partido y con la familia puesta', r.crm.crm && r.crm.avales === 'indeciso' && r.crm.espectro === 'izq' && r.crm.partido === '' && r.crm.bloque === 'izq' && r.crm.partidoVigente === ''],
  ['el CRM lo dice y ofrece «Ya tengo partido político»', r.crm.boton && /sin partido/.test(r.crm.contexto) && /la izquierda/.test(r.crm.contexto)],
  ['el botón vuelve al paso del partido del wizard, rellenado', r.definir.wizard && r.definir.pasoActivo === 4 && r.definir.modo === 'existing' && r.definir.existente && r.definir.nombre === 'ALGUIEN NUEVO'],
  ['y al crear de nuevo la campaña queda con el partido, sin el botón', r.conPartido.avales === 'partido' && r.conPartido.partido === 'PARTIDO ALIANZA VERDE' && !r.conPartido.boton && /con PARTIDO ALIANZA VERDE/.test(r.conPartido.contexto)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
