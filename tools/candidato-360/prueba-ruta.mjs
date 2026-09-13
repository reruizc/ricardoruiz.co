/* prueba-ruta.mjs — la ruta hace una pregunta por tarjeta.
   ------------------------------------------------------------------
   El paso 2 mostraba todo a la vez: corporación, territorio y partido, con la
   mitad de los campos deshabilitados esperando a que alguien adivinara el
   orden. Ahora funciona como la búsqueda del nombre: la tarjeta hace UNA
   pregunta y al responderla cambia por la siguiente; lo elegido brinca dos
   veces antes del cambio y el nombre de la persona se queda arriba.

     misma corporación  →  partido
     otra corporación   →  cuál  →  dónde será  →  partido

   Hay «← Atrás», el copy de la izquierda dice en qué paso va, y quien vuelve
   con campaña guardada cae en la última pregunta, ya respondida.

     node tools/candidato-360/prueba-ruta.mjs                                 */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

/* Dos departamentos con geometría de verdad (cajas): el mapita tiene que
   dibujarlos y encender el elegido. */
const caja = (name, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: { name }, geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
const DEPARTAMENTOS = { type: 'FeatureCollection', features: [caja('Antioquia', [-77, 5.4, -74, 8.9]), caja('Distrito Capital de Bogotá', [-74.3, 3.7, -73.9, 4.9])] };
/* Y los municipios de cada uno con geometría y código Divipola: el mapa hace
   drill down (la silueta del departamento y el municipio encendido) y la
   capital —código 001— encabeza el desplegable. */
const muni = (nombre, mpio_ccdgo, [x0, y0, x1, y1]) => ({ type: 'Feature', properties: { mpio_cnmbr: nombre, mpio_ccdgo }, geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
const coleccion = features => ({ type: 'FeatureCollection', features });
const MUNICIPIOS = {
  '16': coleccion([muni('BOGOTÁ, D.C.', '001', [-74.3, 3.7, -73.9, 4.9])]),
  '01': coleccion([muni('BELLO', '088', [-75.6, 6.3, -75.4, 6.5]), muni('ENVIGADO', '266', [-75.6, 6.0, -75.4, 6.2]), muni('MEDELLÍN', '001', [-75.7, 6.2, -75.5, 6.4])]),
};
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
await p.waitForFunction(() => typeof window.irAPaso === 'function');
await p.waitForFunction(() => document.getElementById('department').options.length > 1);

/* Qué tarjeta se ve: exactamente un paso visible, cuál es, y el copy de la izquierda. */
const estado = () => p.evaluate(() => {
  const visibles = [...document.querySelectorAll('#candidateRoute .paso')].filter(el => !el.classList.contains('hidden')).map(el => el.dataset.paso);
  const cont = document.getElementById('continuarLugar');
  return { visibles, paso: pasoRuta, atras: !document.getElementById('pasoAtras').classList.contains('hidden'), titulo: document.getElementById('rutaTitulo').textContent, nombre: document.getElementById('routeName').textContent, ruta: document.querySelector('input[name="corporationRoute"]:checked')?.value || null,
    continuar: cont.classList.contains('hidden') ? null : !cont.disabled,
    municipio: !document.getElementById('campaignMunicipalityField').classList.contains('hidden'),
    mapa: !document.getElementById('mapaDepto').classList.contains('hidden') && document.querySelectorAll('#mapaDeptoLienzo path').length,
    encendidos: document.querySelectorAll('#mapaDeptoLienzo .depto-elegido').length };
});
const mapaDepto = () => p.evaluate(() => ({ visible: !document.getElementById('mapaDepto').classList.contains('hidden'), elegidos: document.querySelectorAll('#mapaDeptoLienzo .depto-elegido').length, total: document.querySelectorAll('#mapaDeptoLienzo path').length, pie: document.getElementById('mapaDeptoPie').textContent, dibujado: (document.querySelector('#mapaDeptoLienzo .depto-elegido')?.getAttribute('d') || '').length }));
const elegirRuta = async valor => { await p.evaluate(v => { document.querySelector(`input[name="corporationRoute"][value="${v}"]`).checked = true; toggleCorporationChoice({ animar: true }); }, valor); await p.waitForTimeout(700); };
const CONCEJAL = { nombre: 'ALGUIEN CON HISTORIAL', slug: 'CONC2023-16-1-1-1', corp: 'CONCEJO · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', partido: 'PARTIDO X', votos: 900 };

const r = {};
/* 1 · Al abrir, la tarjeta hace una sola pregunta. */
await p.evaluate(c => abrirRutaCandidato(c), CONCEJAL);
await p.waitForTimeout(300);
r.alAbrir = await estado();

/* 2 · «La misma corporación»: brinca y la tarjeta CAMBIA a la del partido. */
r.saltoEnLaOpcion = await p.evaluate(() => { document.querySelector('input[name="corporationRoute"][value="same"]').checked = true; toggleCorporationChoice({ animar: true }); return document.querySelector('.route-option[data-route="same"]').classList.contains('salta'); });
r.antesDelCambio = await estado();          /* con el brinco todavía a la vista, sigue la pregunta */
await p.waitForTimeout(700);
r.misma = await estado();

/* 3 · «← Atrás» vuelve a la pregunta de la ruta. */
await p.click('#pasoAtras'); await p.waitForTimeout(400);
r.atras = await estado();

/* 4 · «Otra corporación»: la tarjeta pasa a «¿a cuál se lanza?». */
await elegirRuta('other');
r.otra = await estado();
await p.locator('#candidateRoute .flow-grid').screenshot({ path: SP + '/ruta-corporacion.png' });

/* 5 · Elegida la corporación, la tarjeta pasa al territorio. */
await p.evaluate(() => historicCorporationPicker.querySelector('[data-corporation="concejo"]').click());
await p.waitForTimeout(700);
r.conCorporacion = await estado();

/* 6 · Departamento + municipio completan el territorio y la tarjeta pasa al partido. */
await p.selectOption('#campaignDepartment', '01'); await p.waitForTimeout(600);
r.conDepartamento = await estado();
r.mapa = await mapaDepto();
r.ordenMunicipios = await p.$$eval('#campaignMunicipality option', os => os.map(o => o.value));
/* El valor es la llave contra la Divipola y se queda como viene; lo que cambia
   es la etiqueta, para no leer «Antioquia» al lado de «MEDELLÍN». */
r.etiquetaMunicipio = await p.$$eval('#campaignMunicipality option', os => os.slice(1, 2).map(o => [o.value, o.textContent])[0]);
await p.selectOption('#campaignMunicipality', 'MEDELLÍN'); await p.waitForTimeout(600);
r.mapaMunicipio = await mapaDepto();
r.listoParaContinuar = await estado();      /* completo el territorio, pero no salta solo */
await p.click('#continuarLugar'); await p.waitForTimeout(500);
r.conMunicipio = await estado();
r.botonVisible = await p.$eval('#abrirCRM', el => el.offsetParent !== null);
await p.mouse.move(0, 0);          /* el ratón queda sobre «Atrás» tras el clic y el hover cambia el color */
r.pieJuntos = await p.evaluate(() => {
  const a = document.getElementById('pasoAtras'), b = document.getElementById('abrirCRM');
  /* El salmón de la casa, sea cual sea su hex: lo que importa es que NO sea el
     mismo azul del botón de seguir. */
  const hex = getComputedStyle(document.documentElement).getPropertyValue('--coral').trim();
  const aColor = getComputedStyle(a).backgroundColor, bColor = getComputedStyle(b).backgroundColor;
  const d = document.createElement('div'); d.style.color = hex; document.body.append(d);
  const salmon = getComputedStyle(d).color; d.remove();
  return { juntos: a.parentElement === b.parentElement, visible: a.offsetParent !== null, esSalmon: aColor === salmon, distintoDelAzul: aColor !== bColor };
});
r.mapaFuera = await p.evaluate(() => document.getElementById('mapaDepto').classList.contains('hidden'));

/* 7 · Atrás desde el partido devuelve al territorio, con lo elegido intacto. */
await p.click('#pasoAtras'); await p.waitForTimeout(400);
r.atrasDesdePartido = await estado();
r.municipioIntacto = await p.inputValue('#campaignMunicipality');

/* 8 · La JAL además exige comuna o localidad antes de pasar. */
await p.evaluate(() => { pasoRuta = 'corporacion'; historicCorporationPicker.querySelector('[data-corporation="jal"]').click(); });
await p.waitForTimeout(500);
await p.selectOption('#campaignDepartment', '16'); await p.waitForTimeout(900);
r.jalSinLocalidad = await estado();
r.etiquetasLocalidad = await p.$$eval('#campaignLocality option', os => os.slice(1).map(o => [o.value, o.textContent]));
await p.evaluate(() => { const s = document.getElementById('campaignLocality'); s.value = s.options[1]?.value || ''; territorioResuelto(); });
await p.waitForTimeout(400);
r.jalListo = await estado();
await p.click('#continuarLugar'); await p.waitForTimeout(500);
r.jalConLocalidad = await estado();

/* 9 · Sin historial territorial (Senado) se entra directo a «¿a cuál se lanza?», sin «Atrás» hacia una pregunta que no se hizo. */
await p.evaluate(() => abrirRutaCandidato({ nombre: 'SENADOR SIN TERRITORIO', slug: 'CON2022-S-11-1', corp: 'SENADO · 2022', circunscripcion: 'NACIONAL', partido: 'PARTIDO Y', votos: 40000 }));
await p.waitForTimeout(300);
r.senador = await estado();

/* 10 · Quien vuelve con campaña guardada cae en la última pregunta. */
await p.evaluate(async c => { abrirRutaCandidato(c); await precargarCampana({ corp: 'concejo', ruta: 'other', departamento: '01', municipio: 'MEDELLÍN', partido: 'PARTIDO Z' }); }, CONCEJAL);
await p.waitForTimeout(800);
r.precargada = await estado();
r.precargadaMunicipio = await p.inputValue('#campaignMunicipality');

/* 11 · Tocar un municipio en el mapa es responder el desplegable. */
await p.evaluate(() => irAPaso('lugar')); await p.waitForTimeout(500);
await p.evaluate(() => document.querySelector('#mapaDeptoLienzo path[data-parte="BELLO"]').dispatchEvent(new MouseEvent('click', { bubbles: true })));
await p.waitForTimeout(500);
r.tocado = await p.inputValue('#campaignMunicipality');
r.mapaTocado = await mapaDepto();
await p.locator('#candidateRoute .flow-grid').screenshot({ path: SP + '/ruta-lugar-mapa.png' });
await b.close();

const solo = (e, paso) => e.visibles.length === 1 && e.visibles[0] === paso && e.paso === paso;
const pruebas = [
  ['al abrir, la tarjeta hace una sola pregunta: la corporación', solo(r.alAbrir, 'ruta') && !r.alAbrir.atras && !r.alAbrir.ruta],
  ['la opción elegida brinca y, mientras brinca, la tarjeta sigue ahí', r.saltoEnLaOpcion === true && solo(r.antesDelCambio, 'ruta')],
  ['«la misma corporación» cambia la tarjeta por la del partido', solo(r.misma, 'partido') && /partido/i.test(r.misma.titulo)],
  ['el nombre de la persona se queda arriba', r.misma.nombre === 'ALGUIEN CON HISTORIAL'],
  ['«← Atrás» vuelve a la pregunta anterior', solo(r.atras, 'ruta')],
  ['«otra corporación» cambia a «¿a cuál se lanza?»', solo(r.otra, 'corporacion') && r.otra.atras && /cuál/i.test(r.otra.titulo)],
  ['elegida la corporación, la tarjeta pasa al territorio', solo(r.conCorporacion, 'lugar') && /dónde/i.test(r.conCorporacion.titulo)],
  ['con departamento pero sin municipio se queda en el territorio', solo(r.conDepartamento, 'lugar')],
  ['«Continuar» lleva a la pregunta del partido, con el botón del CRM', solo(r.conMunicipio, 'partido') && r.botonVisible],
  ['el mapa está desde que se abre la pregunta, todavía sin departamento', r.conCorporacion.mapa === 2 && r.conCorporacion.encendidos === 0],
  ['y no se pregunta el municipio antes que el departamento', r.conCorporacion.municipio === false],
  ['al elegir departamento el mapa pasa a la silueta de ese departamento', r.mapa.visible && r.mapa.total === 3 && r.mapa.elegidos === 3 && r.mapa.dibujado > 20 && /Antioquia/i.test(r.mapa.pie)],
  ['al elegir el municipio la luz se queda en uno solo', r.mapaMunicipio.total === 3 && r.mapaMunicipio.elegidos === 1 && /MEDELL/i.test(r.mapaMunicipio.pie) && /Antioquia/i.test(r.mapaMunicipio.pie)],
  ['la capital del departamento encabeza el desplegable de municipios', r.ordenMunicipios[1] === 'MEDELLÍN'],
  ['los municipios se muestran en tipo oración, pero el valor no cambia', JSON.stringify(r.etiquetaMunicipio) === '["MEDELLÍN","Medellín"]'],
  ['y las comunas o localidades también', JSON.stringify(r.etiquetasLocalidad) === '[["SUBA","Suba"],["TEUSAQUILLO","Teusaquillo"]]'],
  ['tocar un municipio en el mapa lo elige', r.tocado === 'BELLO' && r.mapaTocado.elegidos === 1 && /BELLO/i.test(r.mapaTocado.pie)],
  ['ahí sí aparece el municipio, y «Continuar» espera a que esté completo', r.conDepartamento.municipio === true && r.conDepartamento.continuar === false],
  ['con el territorio completo el botón se habilita, pero no salta solo', r.listoParaContinuar.continuar === true && solo(r.listoParaContinuar, 'lugar')],
  ['«Atrás» y «Abrir CRM» viven juntos en el pie, y Atrás va en salmón', r.pieJuntos.juntos && r.pieJuntos.visible && r.pieJuntos.esSalmon && r.pieJuntos.distintoDelAzul],
  ['el mapa no se queda colgado en las otras tarjetas', r.mapaFuera === true],
  ['atrás desde el partido devuelve al territorio sin perder lo elegido', solo(r.atrasDesdePartido, 'lugar') && r.municipioIntacto === 'MEDELLÍN'],
  ['la JAL espera a la comuna o localidad para dejar continuar', r.jalSinLocalidad.continuar === false && r.jalListo.continuar === true && solo(r.jalConLocalidad, 'partido')],
  ['sin historial territorial se entra directo a «¿a cuál se lanza?», sin Atrás', solo(r.senador, 'corporacion') && !r.senador.atras && r.senador.ruta === 'other'],
  ['quien vuelve con campaña guardada cae en la última pregunta, respondida', solo(r.precargada, 'partido') && r.precargadaMunicipio === 'MEDELLÍN'],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2600));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
