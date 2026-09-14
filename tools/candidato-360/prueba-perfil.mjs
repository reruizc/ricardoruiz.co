/* prueba-perfil.mjs — la tarjeta 07 y las tres lecturas del electorado.
   ------------------------------------------------------------------
   La tarjeta decía cómo es el electorado donde están sus votos (sexo del censo
   y peso rural). Faltaban las tres que pidió Ricardo y que son las que sirven
   para decidir:

     · el TERRITORIO completo —censo, participación, sexo, rural—, que es el
       tablero en el que juega y no solo su pedazo;
     · cómo VOTA ese territorio por familias políticas, con la Asamblea 2023,
       que es la única elección que baja a todos los municipios del país;
     · la votación que DEBERÍA BUSCAR: los votos que le faltan para la meta no
       se parecen a su base —esos ya los tiene— sino al territorio del que los
       va a sacar, así que el perfil objetivo es el promedio de los dos pesado
       por cuántos votos pone cada uno.

   Todo remoto va simulado: tres puestos, un municipio, tres partidos.

     node tools/candidato-360/prueba-perfil.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const DEPARTAMENTOS = { type: 'FeatureCollection', features: ['Antioquia', 'Distrito Capital de Bogotá'].map(name => ({ type: 'Feature', properties: { name }, geometry: null })) };
const MUNICIPIOS = { '01': { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'LA CEJA', mun_elec: '163', mpio_ccdgo: '376' }, geometry: null }] } };
/* Tres puestos de 1.000 personas cada uno: el municipio queda en 50 % de
   mujeres y 33,3 % de censo rural (la zona 99). */
const fila = (code, barrio, mujeres, hombres) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = '6.02'; r[10] = '-75.43'; r[13] = String(mujeres); r[14] = String(hombres); return r.join(';'); };
const PUESTOS = ['CABECERA',
  fila('011630101', 'CENTRO', 600, 400),
  fila('011630102', 'SAN CAYETANO', 400, 600),
  fila('011639901', 'LA MIEL', 500, 500),
].join('\n');
/* Sus votos: 800 en Centro (60 % mujeres) y 200 en San Cayetano (40 %), nada
   en el puesto rural → 56 % de mujeres y 0 % rural. */
const MESAS = [
  { dep: '01', mun: '163', zon: '01', pue: '01', munNom: 'LA CEJA', v: 800 },
  { dep: '01', mun: '163', zon: '01', pue: '02', munNom: 'LA CEJA', v: 200 },
];
/* La Asamblea 2023 del municipio: derecha 500, izquierda 300 (Pacto 200 +
   Renace 100), centro-derecha 100 (Cambio Radical - MIRA) y 100 sin línea. */
const ASAMBLEA = { key: '01', name: 'ANTIOQUIA', nivel: 'municipio', comunas: { '163': {
  name: 'LA CEJA', validos: 1000, votantes: 1800, potencial: 3000, mesas: 9,
  /* Una coalición (se resuelve por sus partes), un movimiento regional de la
     tabla medida y un aval sin línea: los tres casos que dejaban gris el 22 %
     de los votos del país. */
  partidos: [['PARTIDO CENTRO DEMOCRÁTICO', 500], ['MOVIMIENTO POLÍTICO PACTO HISTÓRICO', 200], ['CAMBIO RADICAL - MIRA', 100], ['RENACE', 100], ['PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"', 100]],
} }, totals: { validos: 1000, potencial: 3000 } };

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1300, height: 1100 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
const json = x => ({ status: 200, contentType: 'application/json', body: JSON.stringify(x) });
await p.route('**', route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('DEPARTAMENTOS2.json')) return route.fulfill(json(DEPARTAMENTOS));
  const mps = u.match(/Departamentos-mps\/(\d+)\.json/);
  if (mps) return MUNICIPIOS[mps[1]] ? route.fulfill(json(MUNICIPIOS[mps[1]])) : route.fulfill({ status: 404, body: '' });
  if (u.includes('asamblea-2023/dep/01.json')) return route.fulfill(json(ASAMBLEA));
  if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
  if (u.includes('stub.test/cand.json')) return route.fulfill(json({ mesas: MESAS }));
  if (u.includes('/c360/')) return route.fulfill(json({ ok: true, acceso: true, fuente: 'admin', vinculo: null }));
  return route.fulfill({ status: 404, body: '' });
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pintarPerfil === 'function');
await p.waitForFunction(() => document.getElementById('department').options.length > 1);

const CAND = { nombre: 'CARLOS MARIO BEDOYA MORENO', corp: 'ALCALDÍA · LA CEJA · 2023', circunscripcion: 'LA CEJA (ANTIOQUIA)',
  partido: 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO', votos: 1000, slug: 'ALC2023-1-163-1', dataUrl: 'https://stub.test/cand.json' };
const r = {};
/* La campaña: alcaldía de La Ceja, por firmas, ubicado en la derecha. */
await p.evaluate(c => abrirRutaCandidato(c), CAND);
await p.evaluate(async () => {
  document.querySelector('input[name="corporationRoute"][value="other"]').checked = true; toggleCorporationChoice();
  document.getElementById('otherCorporation').value = 'alcaldia'; updateCampaignTerritory();
  document.getElementById('campaignDepartment').value = '01';
  await loadCampaignMunicipalities();
  document.getElementById('campaignMunicipality').value = 'LA CEJA';
  irAPaso('partido');
  document.querySelector('input[name="avalRuta"][value="firmas"]').checked = true; elegirAval();
  document.querySelector('.espectro-op[data-bloque="d"]').click();
});
await p.waitForTimeout(400);
r.bloques = await p.evaluate(() => ({ renace: PartidosBloques.bloqueDeOrganizacion('RENACE'), cordoba: PartidosBloques.bloqueDeOrganizacion('CORDOBA FLORECE'), coalicion: PartidosBloques.bloqueDeOrganizacion('CAMBIO RADICAL - MIRA'), asi: PartidosBloques.bloqueDeOrganizacion('PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"') }));
r.ideologia = await p.evaluate(async () => {
  const i = await ideologiaDelTerritorio({ corp: 'alcaldia', departamento: '01' }, '01163');
  return { nombre: i.nombre, potencial: i.potencial, votantes: i.votantes, total: i.total, porBloque: i.porBloque, ambito: i.ambito, sinLinea: i.sinLinea };
});
await p.evaluate(async () => {
  crmCandidate = { nombre: 'CARLOS MARIO BEDOYA MORENO', corp: 'ALCALDÍA · LA CEJA · 2023', partido: 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO', dataUrl: 'https://stub.test/cand.json' };
  CAMPANA_ACTUAL = campanaActual('alcaldia');
  META_ACTUAL = { target: 5000 };
  await pintarPerfil();
});
await p.waitForTimeout(600);
r.tarjeta = await p.evaluate(() => ({ titulo: document.getElementById('crmPerfilTitulo').textContent, dato: document.getElementById('crmPerfilDato').textContent, boton: !document.getElementById('crmPerfilBtn').disabled }));
r.perfil = await p.evaluate(() => ({ mujeres: PERFIL_ACTUAL.mujeres, rural: PERFIL_ACTUAL.rural, mujeresMunicipio: PERFIL_ACTUAL.mujeresMunicipio, ruralMunicipio: PERFIL_ACTUAL.ruralMunicipio, familia: PERFIL_ACTUAL.familia, familiaPrevia: PERFIL_ACTUAL.familiaPrevia }));
r.objetivo = await p.evaluate(() => objetivoDelPerfil(PERFIL_ACTUAL, 5000, CAMPANA_ACTUAL));
await p.evaluate(() => mostrarPerfil());
await p.waitForTimeout(300);
r.modal = await p.evaluate(() => document.getElementById('introModalText').textContent.replace(/\s+/g, ' '));
await p.locator('#introModal').screenshot({ path: SP + '/perfil-territorio.png' });
/* Sin meta todavía —las tarjetas se pintan antes que la estimación— la ficha
   no puede quedar rota: simplemente no muestra el objetivo. */
r.sinMeta = await p.evaluate(() => { META_ACTUAL = null; const html = territorioYFamilia(PERFIL_ACTUAL); return { html, tieneTerritorio: /El territorio/.test(html), tieneObjetivo: /debería buscar/.test(html) }; });
await b.close();

const casi = (a, b, t = .002) => Math.abs(a - b) < t;
const pruebas = [
  ['la ideología del territorio sale de la Asamblea 2023 del municipio', r.ideologia.ambito === 'municipio' && r.ideologia.nombre === 'La Ceja' && r.ideologia.total === 1000],
  ['y agrupa los partidos en familias políticas', r.ideologia.porBloque.d === 500 && r.ideologia.porBloque.izq === 300],
  ['una coalición vale lo que valen sus partes', r.ideologia.porBloque.cd === 100],
  ['un movimiento regional entra por el rastro de sus candidatos', r.bloques.renace === 'izq' && r.bloques.cordoba === 'c'],
  ['y un aval que se presta a todos se queda sin línea, con nombre propio', r.ideologia.porBloque.sc === 100 && r.ideologia.sinLinea[0].aval === true && /ASI/i.test(r.ideologia.sinLinea[0].nombre)],
  ['la ficha dice cuáles son y por qué no tienen familia', /Sin línea nacional/.test(r.modal) && /prestan aval/.test(r.modal) && /36 %|35 %/.test(r.modal)],
  ['el perfil de sus votos sigue siendo el de sus puestos', casi(r.perfil.mujeres, .56) && casi(r.perfil.rural, 0)],
  ['y el del municipio, el de TODOS sus puestos', casi(r.perfil.mujeresMunicipio, .5) && casi(r.perfil.ruralMunicipio, 1 / 3)],
  ['la familia es la que eligió en el espectro, no la de su aval anterior', r.perfil.familia === 'd' && r.perfil.familiaPrevia === 'izq'],
  ['el objetivo separa lo que ya tiene de lo que le falta', r.objetivo.meta === 5000 && r.objetivo.base === 1000 && r.objetivo.faltan === 4000 && r.objetivo.mismoTerritorio],
  ['y mezcla los dos perfiles pesados por sus votos', casi(r.objetivo.mujeres, (1000 * .56 + 4000 * .5) / 5000) && casi(r.objetivo.rural, (4000 / 3) / 5000)],
  ['la ficha muestra el censo del territorio y su participación', /3.000 personas habilitadas en La Ceja/.test(r.modal) && /1.800/.test(r.modal) && /60,0 % de participación/.test(r.modal)],
  ['y cómo vota, con su familia marcada', /Cómo vota La Ceja/.test(r.modal) && /50,0 % Derecha · su familia/.test(r.modal) && /30,0 % Izquierda · su aval anterior/.test(r.modal)],
  ['y qué votación debería buscar, con la cuenta a la vista', /debería buscar/.test(r.modal) && /le faltan 4.000/.test(r.modal) && /no alcanza sola/.test(r.modal)],
  ['sin meta todavía, la ficha no se rompe: muestra el territorio y calla el objetivo', r.sinMeta.tieneTerritorio && !r.sinMeta.tieneObjetivo],
  ['la tarjeta sigue resumiendo el perfil de sus puestos', /56,0 %/.test(r.tarjeta.dato) && r.tarjeta.boton],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2800));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
