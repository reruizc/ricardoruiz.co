/* prueba-partido.mjs — el partido se escribe, se sugiere por departamento y se
   puede cambiar.
   ------------------------------------------------------------------
   Dos supuestos que la página daba por buenos y no lo son:

     · que quien tiene historial repite aval. La mitad de las candidaturas
       territoriales cambia de partido entre una elección y la siguiente, y el
       reparto de la meta en un salto de corporación sigue la huella del
       partido: con el partido viejo, reparte mal.
     · que un desplegable nacional sirve. En 2023 se inscribieron 2.258
       organizaciones distintas en el país; en Bogotá 43. Y muchas se repiten
       con las mismas palabras en otro orden entre departamentos.

   Acá se comprueba que el campo sugiere lo del departamento elegido, que
   acepta lo que no está en el catálogo, y que lo escrito es lo que manda en el
   reparto de la meta.

     node tools/candidato-360/prueba-partido.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const DEPARTAMENTOS = { type: 'FeatureCollection', features: [
  { type: 'Feature', properties: { name: 'Distrito Capital de Bogotá' }, geometry: null },
  { type: 'Feature', properties: { name: 'Antioquia' }, geometry: null },
  { type: 'Feature', properties: { name: 'Valle del Cauca' }, geometry: null },
] };

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
const pedidos = [];
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) { if (u.includes('/partidos/')) pedidos.push(u.split('/').pop()); return route.continue(); }
  if (u.includes('DEPARTAMENTOS2.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEPARTAMENTOS) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.montarCampoPartido === 'function');
await p.waitForTimeout(300);

const r = {};
/* ── La ruta de quien ya tiene historial ─────────────────────────────────── */
await p.evaluate(() => abrirRutaCandidato({
  nombre: 'NATALIA SOPHIA PARRA ROJAS', slug: 'JAL2023-16-1-11-81-abc', corp: 'JAL · BARRIOS UNIDOS · BOGOTÁ D.C. · 2023',
  circunscripcion: 'BARRIOS UNIDOS · BOGOTÁ D.C.', partido: 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', votos: 709,
}));
await p.waitForTimeout(500);
r.precargado = await p.inputValue('#campaignParty');
r.hayCampo = await p.evaluate(() => !!document.getElementById('campaignParty') && !document.querySelector('#campaignPartyField select'));
r.depDeducido = await p.evaluate(() => departamentoDeCampana());

/* Escribir sugiere, y sugiere lo de Bogotá. */
await p.fill('#campaignParty', '');
await p.click('#campaignParty');
await p.type('#campaignParty', 'alian');
await p.waitForTimeout(450);
r.sugerencias = await p.evaluate(() => [...document.querySelectorAll('#campaignPartyLista .sugerencia b')].map(x => x.textContent));
/* Que se VEAN: .field trae z-index:1 y el botón de enviar las tapaba. */
r.sugerenciaVisible = await p.evaluate(() => {
  const s = document.querySelector('#campaignPartyLista .sugerencia'), c = s.getBoundingClientRect();
  const encima = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2);
  return Boolean(encima && s.contains(encima));
});
r.conCuantas = await p.evaluate(() => document.querySelector('#campaignPartyLista .sugerencia small')?.textContent || '');
await p.locator('#candidateRoute form').screenshot({ path: SP + '/partido-sugerencias.png' });
await p.evaluate(() => document.querySelectorAll('#campaignPartyLista .sugerencia')[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true })));
await p.waitForTimeout(250);
r.elegido = await p.inputValue('#campaignParty');
r.notaCatalogo = await p.textContent('#campaignPartyStatus');

/* Una organización que no está en 2023 se acepta igual. */
await p.fill('#campaignParty', 'COALICIÓN QUE NACE EN 2027');
await p.waitForTimeout(400);
r.notaLibre = await p.textContent('#campaignPartyStatus');

/* Y es lo escrito, no el histórico, lo que manda en el reparto de la meta. */
r.vigente = await p.evaluate(() => partidoVigente());
r.campana = await p.evaluate(() => campanaActual('concejo'));

/* ── El departamento filtra de verdad ────────────────────────────────────── */
r.antioquia = await p.evaluate(async () => {
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true;
  toggleCorporationChoice();
  document.getElementById('otherCorporation').value = 'asamblea';
  document.getElementById('campaignDepartment').value = '01';
  await loadCampaignMunicipalities().catch(() => {});
  await new Promise(r => setTimeout(r, 400));
  const cat = await cargarPartidos(departamentoDeCampana());
  return { dep: departamentoDeCampana(), cuantas: cat.length, nota: document.getElementById('campaignPartyStatus').textContent };
});
r.bogota = await p.evaluate(async () => {
  document.getElementById('campaignDepartment').value = '16';
  await loadCampaignMunicipalities().catch(() => {});
  await new Promise(r => setTimeout(r, 300));
  const cat = await cargarPartidos(departamentoDeCampana());
  return { cuantas: cat.length, nota: document.getElementById('campaignPartyStatus').textContent };
});

/* ── El wizard de candidatura nueva usa el mismo campo ───────────────────── */
r.wizard = await p.evaluate(async () => {
  showScreen('new');
  document.getElementById('department').value = '31';
  updateTerritory();
  await new Promise(r => setTimeout(r, 400));
  const caja = document.getElementById('party');
  caja.value = 'cambio'; caja.dispatchEvent(new Event('input'));
  await new Promise(r => setTimeout(r, 350));
  return { esInput: caja.tagName, sugerencias: [...document.querySelectorAll('#partyLista .sugerencia b')].map(x => x.textContent), nota: document.getElementById('partyStatus').textContent };
});
await p.screenshot({ path: SP + '/partido-wizard.png' });
await b.close();

const pruebas = [
  ['el partido de la ruta es un campo de escribir, no un desplegable', r.hayCampo === true],
  ['viene precargado con el de su última elección', /NUEVO LIBERALISMO/.test(r.precargado)],
  ['pero se puede cambiar: el departamento sale del historial', r.depDeducido === '16'],
  ['al escribir sugiere organizaciones de ese departamento', r.sugerencias.length > 0 && r.sugerencias.some(x => /ALIANZA VERDE/i.test(x))],
  ['y dice cuántas candidaturas inscribió cada una en 2023', /candidaturas? en 2023/.test(r.conCuantas)],
  ['las sugerencias quedan por encima del formulario, no debajo del botón', r.sugerenciaVisible === true],
  ['elegir una la escribe en el campo', /ALIANZA VERDE/i.test(r.elegido)],
  ['la nota cuenta el tamaño del catálogo del departamento', /organizaciones inscribieron candidatura en Bogotá/i.test(r.notaCatalogo)],
  ['una organización que no existía en 2023 se acepta igual', /No aparece en Bogotá/i.test(r.notaLibre)],
  ['y es lo escrito, no el historial, lo que manda', r.vigente === 'COALICIÓN QUE NACE EN 2027' && r.campana.partido === 'COALICIÓN QUE NACE EN 2027'],
  ['Antioquia y Bogotá NO tienen el mismo catálogo', r.antioquia.cuantas > 200 && r.bogota.cuantas < 60 && r.antioquia.cuantas !== r.bogota.cuantas],
  ['cambiar de departamento cambia la nota', /Antioquia/.test(r.antioquia.nota) && /Bogotá/.test(r.bogota.nota)],
  ['solo se descarga el archivo del departamento que se necesita', pedidos.length && pedidos.every(f => ['16.js', '01.js', '31.js'].includes(f))],
  ['el wizard de candidatura nueva usa el mismo campo', r.wizard.esInput === 'INPUT' && r.wizard.sugerencias.some(x => /CAMBIO RADICAL/i.test(x))],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2000), '\npedidos:', pedidos);
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
