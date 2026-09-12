/* prueba-firmas.mjs — a la Alcaldía y a la Gobernación también se llega por firmas.
   ------------------------------------------------------------------
   La página solo sabía preguntar por el partido, y quien se inscribe como
   grupo significativo de ciudadanos tenía que escribir algo que no existe.
   Ahora, en los cargos uninominales, se pregunta el aval: con partido o por
   firmas. Por firmas no hay huella de partido que seguir, así que se pregunta
   lo único que orienta la recolección —dónde se ubica en el espectro— y con
   eso: el reparto de la meta usa la huella de ese bloque, el mapa toma su
   color, y la tarjeta 08 dice cuántas firmas y en qué comunas cuesta menos
   recogerlas.

     node tools/candidato-360/prueba-firmas.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const DEPARTAMENTOS = { type: 'FeatureCollection', features: ['Antioquia', 'Distrito Capital de Bogotá'].map(name => ({ type: 'Feature', properties: { name }, geometry: null })) };
const MUNICIPIOS = { '16': { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'BOGOTÁ, D.C.', mun_elec: '001' }, geometry: null }] } };
/* Concejo de Bogotá 2023 por localidad: dos partidos de centro-izquierda y uno
   de derecha, repartidos distinto entre dos localidades. */
const CONCEJO = { data: { '16-001': { comunas: {
  '11': { nombre: 'SUBA', votantes: 300000, partidos: [['PARTIDO ALIANZA VERDE', 40000], ['PARTIDO CENTRO DEMOCRÁTICO', 30000]] },
  '19': { nombre: 'CIUDAD BOLIVAR', votantes: 200000, partidos: [['PARTIDO ALIANZA VERDE', 10000], ['PARTIDO CENTRO DEMOCRÁTICO', 8000]] },
} } } };
/* PUESTOS_GEOREF: censo por puesto, que es de donde sale el requisito legal. */
const fila = (code, barrio, mujeres, hombres) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = '4.7'; r[10] = '-74.07'; r[13] = String(mujeres); r[14] = String(hombres); return r.join(';'); };
const PUESTOS = ['CABECERA', fila('160010101', 'SUBA', 60000, 55000), fila('160010102', 'CIUDAD BOLIVAR', 45000, 40000)].join('\n');

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
/* ── 1 · La pregunta del aval solo aparece en los cargos uninominales ─────── */
await p.evaluate(c => abrirRutaCandidato(c), CAND);
await p.evaluate(() => { document.querySelector('input[name="corporationRoute"][value="other"]').checked = true; toggleCorporationChoice(); document.getElementById('otherCorporation').value = 'concejo'; updateCampaignTerritory(); irAPaso('partido'); });
await p.waitForTimeout(500);
r.concejo = await p.evaluate(() => !document.getElementById('avalOpciones').classList.contains('hidden'));
await p.evaluate(() => { document.getElementById('otherCorporation').value = 'alcaldia'; updateCampaignTerritory(); irAPaso('partido'); });
await p.waitForTimeout(500);
r.alcaldia = await p.evaluate(() => !document.getElementById('avalOpciones').classList.contains('hidden'));

/* ── 2 · Por firmas: espectro obligatorio, sin campo de partido ───────────── */
await p.evaluate(() => { document.querySelector('input[name="avalRuta"][value="firmas"]').checked = true; elegirAval({ animar: true }); });
await p.waitForTimeout(500);
r.firmas = await p.evaluate(() => ({
  espectro: !document.getElementById('espectroField').classList.contains('hidden'),
  opciones: [...document.querySelectorAll('.espectro-op b')].map(x => x.textContent),
  campoPartido: !document.getElementById('campaignPartyField').classList.contains('hidden'),
  bloqueado: document.getElementById('abrirCRM').disabled,
  titulo: document.getElementById('rutaTitulo').textContent,
}));
await p.evaluate(() => document.querySelector('.espectro-op[data-bloque="ci"]').click());
await p.waitForTimeout(400);
r.conEspectro = await p.evaluate(() => ({ elegido: espectroVigente(), boton: document.getElementById('abrirCRM').disabled, campana: campanaActual('alcaldia') }));

/* ── 3 · El CRM: la tarjeta de firmas, el reparto y el color ──────────────── */
await p.evaluate(() => { document.getElementById('campaignDepartment').value = '16'; return loadCampaignMunicipalities(); });
await p.waitForTimeout(600);
await p.evaluate(() => { CAMPANA_ACTUAL = campanaActual('alcaldia'); return pintarFirmas(); });
await p.waitForTimeout(1200);
r.tarjeta = await p.evaluate(() => ({
  visible: !document.getElementById('crmFirmas').classList.contains('hidden'),
  titulo: document.getElementById('crmFirmasTitulo').textContent,
  copy: document.getElementById('crmFirmasCopy').textContent,
  dato: document.getElementById('crmFirmasDato').textContent,
  boton: !document.getElementById('crmFirmasBtn').disabled,
}));
await p.evaluate(() => mostrarFirmas());
await p.waitForTimeout(300);
r.modal = await p.evaluate(() => ({ titulo: document.getElementById('introModalTitle').textContent, texto: document.getElementById('introModalText').textContent.replace(/\s+/g, ' ') }));
await p.screenshot({ path: SP + '/firmas-modal.png' });
r.color = await p.evaluate(() => { closeIntroModal(); fijarRampaMapa(partidoVigente(), crmCandidate?.nombre); return { rampa: RAMPA_MAPA[2], bloque: bloqueVigente(), partido: partidoVigente() }; });

/* ── 4 · Con partido, la tarjeta de firmas no existe ──────────────────────── */
r.conPartido = await p.evaluate(async () => {
  document.querySelector('input[name="avalRuta"][value="partido"]').checked = true; elegirAval();
  CAMPANA_ACTUAL = campanaActual('alcaldia');
  await pintarFirmas();
  return { oculta: document.getElementById('crmFirmas').classList.contains('hidden'), partido: partidoVigente(), bloque: bloqueVigente() };
});
await b.close();

/* Censo del stub: 115.000 + 85.000 = 200.000 → 20 % = 40.000 firmas (bajo el tope).
   Huella de centro-izquierda (Alianza Verde): Suba 40.000 · Ciudad Bolívar 10.000
   → 4 de cada 5 firmas en Suba: 32.000 y 8.000, que es lo que revisa el modal. */
const pruebas = [
  ['a un concejo no se le pregunta el aval: las listas siempre tienen partido', r.concejo === false],
  ['a la alcaldía sí: con partido o por firmas', r.alcaldia === true],
  ['por firmas se pregunta el espectro, no el partido', r.firmas.espectro && !r.firmas.campoPartido && r.firmas.opciones.join('|') === 'Izquierda|Centro-izquierda|Centro|Centro-derecha|Derecha'],
  ['y el título de la izquierda deja de hablar de partidos', /Dónde se ubica/i.test(r.firmas.titulo)],
  ['sin espectro no se puede abrir el CRM', r.firmas.bloqueado === true && r.conEspectro.boton === false],
  ['la campaña guarda el aval y el espectro, y se queda sin partido', r.conEspectro.campana.avales === 'firmas' && r.conEspectro.campana.espectro === 'ci' && r.conEspectro.campana.partido === ''],
  ['la tarjeta 08 estima las firmas con el 20 % del censo del territorio', r.tarjeta.visible && /40.000 firmas/.test(r.tarjeta.titulo) && r.tarjeta.dato === '40.000' && r.tarjeta.boton],
  ['y las reparte por donde vota esa familia política', /SUBA/i.test(r.tarjeta.copy) && /concentran \d+ % de la meta/.test(r.tarjeta.copy)],
  ['el modal muestra el censo, la regla y el reparto comuna por comuna', /200.000 personas en el censo/.test(r.modal.texto) && /Ley 130 de 1994/.test(r.modal.texto) && /32.000 SUBA/.test(r.modal.texto)],
  ['y dice que es una estimación, no la cifra de la Registraduría', /estimación/i.test(r.modal.texto) && /Registradur/.test(r.modal.texto)],
  ['el mapa toma el color del bloque elegido, no el de un partido', r.color.bloque === 'ci' && r.color.partido === '' && /^#/.test(r.color.rampa)],
  ['con partido, la tarjeta de firmas desaparece', r.conPartido.oculta === true && r.conPartido.bloque === '' && /ALIANZA VERDE/.test(r.conPartido.partido)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2400));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
