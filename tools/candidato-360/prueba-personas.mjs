/* prueba-personas.mjs — una tarjeta por persona también con tres nombres.
   ------------------------------------------------------------------
   Daniel Carvalho Mejía salía tres veces en el buscador: Cámara Antioquia
   2022, Concejo Medellín 2015 y 2019. Tres componentes de nombre y la regla
   solo unificaba cuatro. Ahora tres también, si todas sus candidaturas
   territoriales caen en el mismo departamento; un «Juan Carlos López» de
   Bogotá y otro de Antioquia siguen siendo dos tarjetas, y dos senadores
   homónimos sin territorio tampoco se juntan.

     node tools/candidato-360/prueba-personas.mjs                            */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 950 } });
const errores = [];
p.on('pageerror', e => errores.push('PAGEERROR: ' + e.message));
await p.route('**', r => r.request().url().startsWith('file://') ? r.continue() : r.abort());
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.aplicarGateExistente === 'function');
await p.waitForTimeout(300);
await p.evaluate(() => { SESSION.listo = true; SESSION.acceso = true; aplicarGate(); });
await p.click('#intro .choice-panel button:nth-of-type(1)');
await p.evaluate(() => {
  appendHistorical([
    { nombre: 'DANIEL CARVALHO MEJIA', slug: 'CON2022-C-1-203-109', corp: 'CÁMARA · ANTIOQUIA · 2022', partido: 'COALICIÓN CENTRO ESPERANZA', votos: 37111, circunscripcion: 'ANTIOQUIA', source: 'con2022' },
    { nombre: 'DANIEL CARVALHO MEJIA', slug: 'CONC2019-1-1-24-1', corp: 'CONCEJO · MEDELLIN · 2019', partido: 'TODOS JUNTOS', votos: 5298, circunscripcion: 'MEDELLIN (ANTIOQUIA)', source: 'conc2019' },
    { nombre: 'DANIEL CARVALHO MEJIA', slug: 'CONC2015-1-1-78-10', corp: 'CONCEJO · MEDELLIN · 2015', partido: 'CREEMOS', votos: 6132, circunscripcion: 'MEDELLIN (ANTIOQUIA)', source: 'conc2015' },
    { nombre: 'JUAN CARLOS LOPEZ', slug: 'CONC2023-16-1-7457-7', corp: 'CONCEJO · BOGOTÁ D.C. · 2023', partido: 'PARTIDO LIBERAL', votos: 900, circunscripcion: 'BOGOTÁ D.C.', source: 'concejo' },
    { nombre: 'JUAN CARLOS LOPEZ', slug: 'CONC2023-1-259-15-5', corp: 'CONCEJO · SEGOVIA · 2023', partido: 'PARTIDO LIBERAL', votos: 120, circunscripcion: 'SEGOVIA (ANTIOQUIA)', source: 'concejo' },
    { nombre: 'MARIA JOSE PEREZ', slug: 'CON2018-S-12-40', corp: 'SENADO · 2018', partido: 'PARTIDO VERDE', votos: 3000, circunscripcion: 'NACIONAL', source: 'con2018' },
    { nombre: 'MARIA JOSE PEREZ', slug: 'CON2022-S-11-40', corp: 'SENADO · 2022', partido: 'PARTIDO VERDE', votos: 3100, circunscripcion: 'NACIONAL', source: 'con2022' },
    { nombre: 'PEDRO PABLO GOMEZ RIOS', slug: 'CONC2023-31-1-2-2', corp: 'CONCEJO · CALI · 2023', partido: 'PARTIDO DE LA U', votos: 700, circunscripcion: 'CALI (VALLE DEL CAUCA)', source: 'concejo' },
    { nombre: 'PEDRO PABLO GOMEZ RIOS', slug: 'CONC2019-16-1-2-2', corp: 'CONCEJO · BOGOTÁ D.C. · 2019', partido: 'PARTIDO DE LA U', votos: 800, circunscripcion: 'BOGOTÁ D.C.', source: 'conc2019' },
  ]);
});
const busca = async q => { await p.evaluate(q => searchCandidate(q, true), q); await p.waitForSelector('#searchResults .result'); return p.$$eval('#searchResults .result', n => n.map(x => ({ nombre: x.querySelector('b').textContent, detalle: x.querySelector('small').textContent }))); };
const r = {};
r.daniel = await busca('daniel carva');
r.juan = await busca('juan carlos lopez');
r.maria = await busca('maria jose perez');
r.pedro = await busca('pedro pablo gomez');
r.slugs = await p.evaluate(() => ['CON2022-C-1-203-109', 'CONC2019-16-1-1-1', 'ASAM2023-31-8-51', 'GOB2023-1-5003-10', 'ALC2023-16-1-19-5', 'JAL2023-16-1-7523-81-714c42', 'CON2022-S-11-1', 'CON2022-CT-3-1', 'PRES2022-2V-1235-2'].map(departamentoDelSlug));
/* Abrir la tarjeta unificada: el historial trae las tres y la última manda. */
await busca('daniel carva');
await p.locator('#searchResults .result').first().click();
await p.waitForTimeout(200);
r.ruta = await p.evaluate(() => ({ nombre: document.getElementById('routeName').textContent, historial: document.getElementById('routeHistory').textContent, corp: crmCandidate.corp, n: crmCandidate.history?.length }));
await b.close();

const pruebas = [
  ['Daniel Carvalho Mejía es UNA tarjeta con sus tres candidaturas', r.daniel.length === 1 && /3 candidaturas registradas · 2015, 2019, 2022/.test(r.daniel[0].detalle)],
  ['al abrirla, parte de la última (Cámara 2022) con el historial completo', r.ruta.corp === 'CÁMARA · ANTIOQUIA · 2022' && r.ruta.n === 3 && /3 candidaturas/.test(r.ruta.historial)],
  ['un nombre de tres componentes en dos departamentos sigue siendo dos personas', r.juan.length === 2],
  ['dos senadores homónimos sin territorio no se juntan', r.maria.length === 2],
  ['con cuatro componentes se unifica como antes, aunque cambie de departamento', r.pedro.length === 1 && /2 candidaturas/.test(r.pedro[0].detalle)],
  ['el departamento sale del slug en todas las fuentes territoriales', r.slugs.join('|') === '1|16|31|1|16|16|||'],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
