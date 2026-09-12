/* prueba-partido.mjs — el partido se escribe, se sugiere por departamento y se
   puede cambiar.
   ------------------------------------------------------------------
   Dos supuestos que la página daba por buenos y no lo son:

     · que quien tiene historial repite aval. La mitad de las candidaturas
       territoriales cambia de partido entre una elección y la siguiente, y el
       reparto de la meta en un salto de corporación sigue la huella del
       partido: con el partido viejo, reparte mal.
     · que un desplegable nacional sirve. Entre las territoriales de 2023 y la
       Cámara de 2026 hay 2.338 organizaciones distintas en el país; en Bogotá
       52. Y muchas se repiten con las mismas palabras en otro orden entre
       departamentos.
     · que con 2023 basta. Salvación Nacional no existía entonces y sacó
       190.113 votos a Cámara en Bogotá en 2026: si el catálogo solo mira
       atrás, el partido de quien se lanza hoy no aparece.

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
/* La ruta va por tarjetas: la primera pregunta la corporación y hasta
   responderla no hay campo de partido. Se responde «la misma» y sigue. */
r.partidoOculto = await p.evaluate(() => document.getElementById('campaignParty').offsetParent === null);
await p.evaluate(() => { document.querySelector('input[name="corporationRoute"][value="same"]').checked = true; toggleCorporationChoice(); });
await p.waitForTimeout(400);
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

/* Un partido que NO existía en 2023 pero sí en la Cámara de 2026. */
r.nueva = await p.evaluate(async () => {
  const caja = document.getElementById('campaignParty');
  caja.value = 'salva'; caja.dispatchEvent(new Event('input'));
  await new Promise(r => setTimeout(r, 350));
  const primera = document.querySelector('#campaignPartyLista .sugerencia');
  return { nombre: primera?.querySelector('b')?.textContent || '', respaldo: primera?.querySelector('small')?.textContent || '' };
});
/* Y que el tamaño de 2026 pese: escribir «partido» en Bogotá debe traer
   primero a los grandes de hoy, no al movimiento local con más inscritos. */
r.orden = await p.evaluate(async () => {
  const caja = document.getElementById('campaignParty');
  caja.value = ''; caja.dispatchEvent(new Event('input'));
  await new Promise(r => setTimeout(r, 350));
  return [...document.querySelectorAll('#campaignPartyLista .sugerencia b')].map(x => x.textContent).slice(0, 3);
});

/* Las coaliciones no se ofrecen: uno se lanza «con Cambio Radical», no «con
   Cambio Radical - MIRA - La U». En el catálogo siguen (miden la huella). */
r.coaliciones = await p.evaluate(async () => {
  const caja = document.getElementById('campaignParty');
  caja.value = 'cambio'; caja.dispatchEvent(new Event('input'));
  await new Promise(r => setTimeout(r, 350));
  const ofrecidas = [...document.querySelectorAll('#campaignPartyLista .sugerencia b')].map(x => x.textContent);
  const cat = await cargarPartidos('16');
  return { ofrecidas, enCatalogo: cat.filter(([n]) => /CAMBIO RADICAL/i.test(n)).length, marcadas: cat.filter(e => /CAMBIO RADICAL/i.test(e[0]) && e[3] === 1).length };
});

/* La sucursal regional de un partido nacional es UNA sola entrada, y los
   movimientos que llevan la ciudad en el nombre siguen siendo ellos mismos. */
r.fusion = await p.evaluate(async () => {
  const cat = await cargarPartidos('16');
  const pacto = cat.filter(([n]) => /PACTO HIST/i.test(n));
  return { cuantos: pacto.length, entrada: pacto[0] || null, propios: cat.filter(([n]) => /^BOGOTÁ (ENTRE TODOS|MÁS FUERTE)/i.test(n)).length };
});

/* Una organización que no está en ninguna de las dos se acepta igual. */
await p.fill('#campaignParty', 'COALICIÓN QUE NACE EN 2027');
await p.waitForTimeout(400);
r.notaLibre = await p.textContent('#campaignPartyStatus');

/* Y es lo escrito, no el histórico, lo que manda en el reparto de la meta. */
r.vigente = await p.evaluate(() => partidoVigente());
r.campana = await p.evaluate(() => campanaActual('concejo'));

/* ── El logo del partido ─────────────────────────────────────────────────────
   El manifiesto se pide por HTTP y esta prueba corre sobre file://: lo que
   importa es el pintado, así que el catálogo se siembra a mano con UN logo que
   carga (un PNG en línea) y otro que no existe. El que no existe se borra solo
   —de eso se trata el onerror—, y así nunca hay un cuadro roto. */
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
await p.evaluate(png => LOGOS_PARTIDOS.set('16', new Map([
  [normalizedText('PARTIDO ALIANZA VERDE'), png],
  [normalizedText('PARTIDO LIBERAL COLOMBIANO'), 'candidato-360-data/logos-partidos/16/no-existe-todavia.png'],
])), PNG);
await p.fill('#campaignParty', 'partido');
await p.waitForTimeout(600);
r.logos = await p.evaluate(() => ({
  sugerencias: [...document.querySelectorAll('#campaignPartyLista .sugerencia')].map(s => ({ nombre: s.querySelector('b').textContent, logo: Boolean(s.querySelector('img.logo-partido')) })),
  rotos: document.querySelectorAll('#campaignPartyLista img.logo-partido:not([src^="data:"])').length,
}));
await p.fill('#campaignParty', 'PARTIDO ALIANZA VERDE');
await p.waitForTimeout(600);
r.logos.enLaNota = await p.evaluate(() => Boolean(document.querySelector('#campaignPartyStatus img.logo-partido')));

/* ── El departamento filtra de verdad ────────────────────────────────────── */
r.antioquia = await p.evaluate(async () => {
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true;
  toggleCorporationChoice();
  document.getElementById('otherCorporation').value = 'asamblea';
  irAPaso('lugar');
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
  ['el partido no se pregunta antes que la corporación', r.partidoOculto === true],
  ['la sugerencia lleva el logo del partido que sí lo tiene', r.logos.sugerencias.some(x => /ALIANZA VERDE/.test(x.nombre) && x.logo)],
  ['y no inventa uno para los que no', r.logos.sugerencias.some(x => !/ALIANZA VERDE/.test(x.nombre) && !x.logo)],
  ['el partido escrito muestra su logo en la nota', r.logos.enLaNota === true],
  ['un archivo que todavía no exista se borra solo: nunca un cuadro roto', r.logos.rotos === 0 && r.logos.sugerencias.some(x => /LIBERAL/.test(x.nombre) && !x.logo)],
  ['viene precargado con el de su última elección', /NUEVO LIBERALISMO/.test(r.precargado)],
  ['pero se puede cambiar: el departamento sale del historial', r.depDeducido === '16'],
  ['al escribir sugiere organizaciones de ese departamento', r.sugerencias.length > 0 && r.sugerencias.some(x => /ALIANZA VERDE/i.test(x))],
  ['y dice por qué está en la lista, con lo más reciente primero',
    /votos a Cámara en 2026/.test(r.conCuantas) && /candidaturas territoriales en 2023/.test(r.conCuantas)],
  ['las sugerencias quedan por encima del formulario, no debajo del botón', r.sugerenciaVisible === true],
  ['elegir una la escribe en el campo', /ALIANZA VERDE/i.test(r.elegido)],
  ['la nota cuenta el tamaño del catálogo del departamento y de dónde sale', /organizaciones con votación en Bogotá/i.test(r.notaCatalogo) && /Cámara en 2026/.test(r.notaCatalogo)],
  ['un partido nuevo, que no corrió en 2023, igual se sugiere',
    /SALVACIÓN NACIONAL/i.test(r.nueva.nombre) && /190.113 votos a Cámara en 2026/.test(r.nueva.respaldo) && !/2023/.test(r.nueva.respaldo)],
  ['y los grandes de hoy encabezan la lista', /PACTO HISTÓRICO/i.test(r.orden[0] || '')],
  ['«PACTO HISTÓRICO BOGOTÁ» de 2023 y la lista de 2026 son UNA entrada, con las dos cifras',
    r.fusion.cuantos === 1 && r.fusion.entrada[1] >= 1 && r.fusion.entrada[2] === 932728],
  ['pero un movimiento que se llama por la ciudad NO se funde con nadie', r.fusion.propios === 2],
  ['al escribir «cambio» en Bogotá se ofrece Cambio Radical UNA vez, sin sus coaliciones',
    r.coaliciones.ofrecidas.filter(x => /CAMBIO RADICAL/i.test(x)).length === 1 && r.coaliciones.ofrecidas.every(x => !/MIRA|DE LA U/i.test(x))],
  ['y las coaliciones siguen en el catálogo, marcadas, para medir la huella', r.coaliciones.enCatalogo >= 4 && r.coaliciones.marcadas >= 3],
  ['una organización que no está en ninguna de las dos se acepta igual', /No aparece en Bogotá/i.test(r.notaLibre)],
  ['y es lo escrito, no el historial, lo que manda', r.vigente === 'COALICIÓN QUE NACE EN 2027' && r.campana.partido === 'COALICIÓN QUE NACE EN 2027'],
  ['Antioquia y Bogotá NO tienen el mismo catálogo', r.antioquia.cuantas > 200 && r.bogota.cuantas < 70 && r.antioquia.cuantas !== r.bogota.cuantas],
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
