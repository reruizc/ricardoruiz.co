/* prueba-ruta.mjs — la ruta se responde de a una pregunta.
   ------------------------------------------------------------------
   El paso 2 mostraba todo a la vez: corporación, territorio y partido, con la
   mitad de los campos deshabilitados esperando a que alguien adivinara el
   orden. Ahora cada respuesta abre la siguiente pregunta —y solo la
   siguiente—, y lo que se acaba de elegir brinca dos veces para acusar recibo.

     misma corporación  → partido
     otra corporación   → nueva corporación → dónde será → partido

   El estado manda: si se borra el municipio, la pregunta del partido se
   vuelve a cerrar. Y quien vuelve con una campaña guardada la ve completa,
   sin volver a responder.

     node tools/candidato-360/prueba-ruta.mjs                                 */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const DEPARTAMENTOS = { type: 'FeatureCollection', features: ['Antioquia', 'Distrito Capital de Bogotá'].map(name => ({ type: 'Feature', properties: { name }, geometry: null })) };
const muns = nombres => ({ type: 'FeatureCollection', features: nombres.map(mpio_cnmbr => ({ type: 'Feature', properties: { mpio_cnmbr }, geometry: null })) });
const MUNICIPIOS = { '16': muns(['BOGOTÁ, D.C.']), '01': muns(['MEDELLÍN', 'ENVIGADO', 'BELLO']) };
const CSV = ['cabecera'].concat(['TEUSAQUILLO', 'SUBA'].map(l => [0, 1, 2, 3, 4, 'BOGOTA D.C.', 'BOGOTÁ, D.C.', 7, 8, 9, l].join(';'))).join('\n');

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 1100 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('DEPARTAMENTOS2.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEPARTAMENTOS) });
  const mps = u.match(/Departamentos-mps\/(\d+)\.json/);
  if (mps) return MUNICIPIOS[mps[1]] ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MUNICIPIOS[mps[1]]) }) : route.fulfill({ status: 404, body: '' });
  if (u.includes('COMUNAS_DATA.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: CSV });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pasosRuta === 'function');
await p.waitForFunction(() => document.getElementById('department').options.length > 1);

const estado = () => p.evaluate(() => {
  const oculto = id => document.getElementById(id).classList.contains('hidden');
  return {
    ruta: document.querySelector('input[name="corporationRoute"]:checked')?.value || null,
    corporacion: !historicCorporationPicker.classList.contains('hidden'),
    lugar: !oculto('campaignPlace'),
    partido: !oculto('campaignPartyField'),
    boton: !oculto('abrirCRM'),
  };
});
const elegirRuta = async valor => { await p.evaluate(v => { document.querySelector(`input[name="corporationRoute"][value="${v}"]`).checked = true; toggleCorporationChoice({ animar: true }); }, valor); await p.waitForTimeout(250); };
const CONCEJAL = { nombre: 'ALGUIEN CON HISTORIAL', slug: 'CONC2023-16-1-1-1', corp: 'CONCEJO · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', partido: 'PARTIDO X', votos: 900 };

const r = {};
/* 1 · Al abrir, una sola pregunta. */
await p.evaluate(c => abrirRutaCandidato(c), CONCEJAL);
await p.waitForTimeout(300);
r.alAbrir = await estado();

/* 2 · «La misma corporación» salta a la pregunta del partido. */
await elegirRuta('same');
r.misma = await estado();
r.saltoEnLaOpcion = await p.evaluate(() => {
  document.querySelector('input[name="corporationRoute"][value="same"]').checked = true;
  toggleCorporationChoice({ animar: true });
  return document.querySelector('.route-option[data-route="same"]').classList.contains('salta');
});

/* 3 · «Otra corporación» abre SOLO la nueva corporación. */
await elegirRuta('other');
r.otra = await estado();

/* 4 · Elegida la corporación, aparece el territorio; el partido espera. */
await p.evaluate(() => historicCorporationPicker.querySelector('[data-corporation="concejo"]').click());
await p.waitForTimeout(300);
r.conCorporacion = await estado();
r.saltoEnLaTarjeta = await p.evaluate(() => { const c = historicCorporationPicker.querySelector('[data-corporation="alcaldia"]'); c.click(); return c.classList.contains('salta'); });
await p.evaluate(() => historicCorporationPicker.querySelector('[data-corporation="concejo"]').click());
await p.waitForTimeout(200);

await p.locator('#candidateRoute .flow-grid').screenshot({ path: SP + '/ruta-pasos.png' });
/* 5 · Departamento y municipio completan el territorio y abren el partido. */
await p.selectOption('#campaignDepartment', '01');
await p.waitForTimeout(400);
r.conDepartamento = await estado();
await p.selectOption('#campaignMunicipality', 'MEDELLÍN');
await p.waitForTimeout(400);
r.conMunicipio = await estado();

/* 6 · Y si se borra el municipio, la pregunta del partido se vuelve a cerrar. */
await p.evaluate(() => { document.getElementById('campaignMunicipality').value = ''; loadCampaignLocalities(); });
await p.waitForTimeout(300);
r.sinMunicipio = await estado();

/* 7 · La JAL además exige comuna o localidad. */
await p.evaluate(() => historicCorporationPicker.querySelector('[data-corporation="jal"]').click());
await p.waitForTimeout(200);
await p.selectOption('#campaignDepartment', '16');
await p.waitForTimeout(600);
r.jalSinLocalidad = await estado();
await p.evaluate(() => { const s = document.getElementById('campaignLocality'); s.value = s.options[1]?.value || ''; pasosRuta({ animar: true }); });
await p.waitForTimeout(300);
r.jalConLocalidad = await estado();

/* 8 · Sin historial territorial (Senado) la única ruta se marca sola. */
await p.evaluate(() => abrirRutaCandidato({ nombre: 'SENADOR SIN TERRITORIO', slug: 'CON2022-S-11-1', corp: 'SENADO · 2022', circunscripcion: 'NACIONAL', partido: 'PARTIDO Y', votos: 40000 }));
await p.waitForTimeout(300);
r.senador = await estado();
r.opcionMismaOculta = await p.evaluate(() => document.querySelector('.route-option[data-route="same"]').classList.contains('hidden'));

/* 9 · Quien vuelve con campaña guardada la ve completa, sin re-responder. */
await p.evaluate(async c => { abrirRutaCandidato(c); await precargarCampana({ corp: 'concejo', ruta: 'other', departamento: '01', municipio: 'MEDELLÍN', partido: 'PARTIDO Z' }); }, CONCEJAL);
await p.waitForTimeout(700);
r.precargada = await estado();
await b.close();

const pruebas = [
  ['al abrir la ruta solo está la primera pregunta', !r.alAbrir.ruta && !r.alAbrir.corporacion && !r.alAbrir.lugar && !r.alAbrir.partido && !r.alAbrir.boton],
  ['«la misma corporación» abre el partido, y nada de territorio', r.misma.partido && r.misma.boton && !r.misma.lugar && !r.misma.corporacion],
  ['la opción elegida brinca', r.saltoEnLaOpcion === true],
  ['«otra corporación» abre SOLO la nueva corporación', r.otra.corporacion && !r.otra.lugar && !r.otra.partido && !r.otra.boton],
  ['elegir la corporación abre el territorio, no el partido', r.conCorporacion.lugar && !r.conCorporacion.partido],
  ['la tarjeta de corporación también brinca', r.saltoEnLaTarjeta === true],
  ['con departamento pero sin municipio el partido sigue cerrado', r.conDepartamento.lugar && !r.conDepartamento.partido],
  ['completo el territorio, aparecen partido y botón', r.conMunicipio.partido && r.conMunicipio.boton],
  ['si se borra el municipio, el partido se vuelve a cerrar', !r.sinMunicipio.partido && !r.sinMunicipio.boton],
  ['la JAL espera a la comuna o localidad', !r.jalSinLocalidad.partido && r.jalConLocalidad.partido],
  ['sin historial territorial, «otra corporación» viene marcada', r.senador.ruta === 'other' && r.senador.corporacion && r.opcionMismaOculta],
  ['quien vuelve con campaña guardada la ve completa', r.precargada.corporacion && r.precargada.lugar && r.precargada.partido && r.precargada.boton],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2200));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
