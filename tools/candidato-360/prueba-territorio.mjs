/* prueba-territorio.mjs — dónde se lanza la candidatura, sin red.
   ------------------------------------------------------------------
   Dos reglas de la pregunta territorial:

     · Bogotá D.C. encabeza el desplegable de departamentos y el resto sigue
       alfabético. En una lista de 33, «Distrito Capital» quedaba enterrado
       en la D.
     · Un departamento con UN SOLO municipio no se pregunta. Al escoger
       Concejo, Alcaldía o JAL de Bogotá, «municipio o distrito» es un paso
       vacío: ya lo dijo el departamento. El valor se fija igual —el mapa, la
       meta y el briefing lo necesitan—; lo que se ahorra es la pregunta, y en
       su lugar queda una línea que dice por qué no está.

   La regla se decide con el dato (cuántos municipios trae la fuente), así que
   acá se simulan dos departamentos: Bogotá con uno y Antioquia con tres.

     node tools/candidato-360/prueba-territorio.mjs                           */
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

const fallos = [];
const revisar = (t, ok) => { console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) fallos.push(t); };
const oculto = id => p.$eval(id, e => e.classList.contains('hidden'));

/* ── El orden del desplegable ───────────────────────────────────────────── */
const orden = await p.$$eval('#department option', n => n.map(o => o.textContent));
revisar('Bogotá encabeza la lista de departamentos', orden[1] === 'Bogotá D.C.');
revisar('el resto sigue alfabético', JSON.stringify(orden.slice(2)) === JSON.stringify(['Amazonas', 'Antioquia', 'Boyacá', 'Vichada']));

/* ── Wizard de candidatura nueva ────────────────────────────────────────── */
await p.click('#intro .choice-panel button:nth-of-type(2)');
await p.evaluate(() => showNewWizardStep(3));
await p.evaluate(() => { document.getElementById('election').value = 'concejo'; updateTerritory(); });
await p.selectOption('#department', { label: 'Bogotá D.C.' });
await p.evaluate(() => updateTerritory());
await p.waitForFunction(() => document.getElementById('municipalityField').classList.contains('hidden'));
revisar('Concejo de Bogotá: no se pregunta el municipio', await oculto('#municipalityField'));
revisar('pero el municipio queda fijado', (await p.inputValue('#municipality')) === 'BOGOTÁ, D.C.');
revisar('y se dice por qué no se pregunta', !(await oculto('#municipalityNota')) && /único municipio/.test(await p.textContent('#municipalityNota')));

await p.evaluate(() => { document.getElementById('election').value = 'alcaldia'; updateTerritory(); });
await p.waitForTimeout(300);
revisar('Alcaldía de Bogotá: tampoco', await oculto('#municipalityField'));

await p.evaluate(() => { document.getElementById('election').value = 'jal'; updateTerritory(); });
await p.waitForFunction(() => document.getElementById('locality').options.length > 1);
revisar('JAL de Bogotá: sin municipio pero CON localidad',
  (await oculto('#municipalityField')) && !(await oculto('#localityField')) &&
  JSON.stringify(await p.$$eval('#locality option', n => n.slice(1).map(o => o.textContent))) === '["CHAPINERO","SUBA","TEUSAQUILLO"]');

await p.selectOption('#department', { label: 'Antioquia' });
await p.evaluate(() => { document.getElementById('election').value = 'concejo'; updateTerritory(); });
await p.waitForFunction(() => !document.getElementById('municipalityField').classList.contains('hidden'));
revisar('un departamento con varios municipios sí pregunta', !(await oculto('#municipalityField')) && (await oculto('#municipalityNota')));
revisar('y la lista llega completa', (await p.$$eval('#municipality option', n => n.length)) === 4);

await p.evaluate(() => { document.getElementById('election').value = 'gobernacion'; updateTerritory(); });
revisar('una gobernación no deja la nota colgada', await oculto('#municipalityNota'));

/* ── Ruta del candidato con historial ───────────────────────────────────── */
await p.evaluate(() => {
  appendHistorical([{ nombre: 'RICARDO ESTEBAN RUIZ CASTRO', slug: 'r1', corp: 'CONCEJO · TUNJA · 2023', circunscripcion: 'TUNJA', votos: 900, partido: 'X' }]);
  abrirRutaCandidato(historicalIndex.find(c => c.slug === 'r1'));
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true;
  toggleCorporationChoice();
  document.getElementById('otherCorporation').value = 'alcaldia';
  updateCampaignTerritory();
});
await p.selectOption('#campaignDepartment', { label: 'Bogotá D.C.' });
await p.evaluate(() => loadCampaignMunicipalities());
await p.waitForFunction(() => document.getElementById('campaignMunicipalityField').classList.contains('hidden'));
revisar('en la ruta con historial pasa lo mismo',
  (await oculto('#campaignMunicipalityField')) && (await p.inputValue('#campaignMunicipality')) === 'BOGOTÁ, D.C.');
/* El territorio se guarda igual aunque no se haya preguntado; y no queda
   «BOGOTÁ, D.C. · Bogotá D.C.» porque campaignTerritory ya deduplicaba por
   nombre normalizado — el distrito es municipio y departamento a la vez. */
revisar('el territorio se guarda igual, y sin repetir Bogotá',
  (await p.evaluate(() => campaignTerritory('alcaldia'))) === 'BOGOTÁ, D.C.');
await p.selectOption('#campaignDepartment', { label: 'Antioquia' });
await p.evaluate(() => loadCampaignMunicipalities());
await p.waitForFunction(() => !document.getElementById('campaignMunicipalityField').classList.contains('hidden'));
revisar('y al cambiar de departamento la pregunta vuelve', !(await oculto('#campaignMunicipalityField')));
revisar('sin errores de JavaScript', errores.length === 0);

/* Dos capturas para revisar a ojo: la pregunta con Bogotá y con Antioquia. */
const SALIDA = process.env.SALIDA_PRUEBA || '/tmp';
await p.selectOption('#campaignDepartment', { label: 'Bogotá D.C.' });
await p.evaluate(() => loadCampaignMunicipalities());
await p.waitForFunction(() => document.getElementById('campaignMunicipalityField').classList.contains('hidden'));
await p.locator('#campaignPlace').screenshot({ path: SALIDA + '/territorio-bogota.png' });
await p.selectOption('#campaignDepartment', { label: 'Antioquia' });
await p.evaluate(() => loadCampaignMunicipalities());
await p.waitForFunction(() => !document.getElementById('campaignMunicipalityField').classList.contains('hidden'));
await p.locator('#campaignPlace').screenshot({ path: SALIDA + '/territorio-antioquia.png' });
await b.close();
console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : `${'todas pasaron'}`);
process.exit(fallos.length ? 1 : 0);
