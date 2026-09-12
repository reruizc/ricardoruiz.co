/* prueba-vitrina.mjs — qué ve un visitante SIN cuenta en candidato-360.html.
   ------------------------------------------------------------------
   La regla del producto (sep-2026): el índice electoral es la vitrina. Un
   visitante sin acceso busca su nombre, lo ve, entra a su candidatura y ve su
   historial; el muro cae en el CRM, que es lo que se cobra. Antes el muro
   tapaba la búsqueda entera y no se veía ni un nombre — una vitrina borrosa
   no vende nada.

   Corre sin red: el índice viene de S3, así que acá se siembran tres
   candidaturas a mano con appendHistorical() y se busca sobre esas.

     node tools/candidato-360/prueba-vitrina.mjs                            */
/* playwright puede estar local o global; con global basta el NODE_PATH del sistema. */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 950 } });
const errores = [];
p.on('pageerror', e => errores.push('PAGEERROR: ' + e.message));
await p.route('**', r => r.request().url().startsWith('file://') ? r.continue() : r.abort());
// Sin token: visitante no registrado, como en la captura de Ricardo.
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.aplicarGateExistente === 'function');
await p.waitForTimeout(300);
await p.evaluate(() => { SESSION.listo = true; SESSION.acceso = false; aplicarGate(); });
await p.click('#intro .choice-panel button:nth-of-type(1)');
// El índice viene de S3 (bloqueado acá): se siembran tres candidaturas reales de forma.
await p.evaluate(() => {
  appendHistorical([
    { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', slug: 'r1', corp: 'CONCEJO · TUNJA · 2023', partido: 'Partido Verde', votos: 1420, circunscripcion: 'TUNJA', source: 'concejo' },
    { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', slug: 'r2', corp: 'JAL · TUNJA · 2019', partido: 'Partido Verde', votos: 610, circunscripcion: 'TUNJA', source: 'jal' },
    { nombre: 'RICARDO ANDRÉS RUIZ MEJÍA', slug: 'r3', corp: 'ASAMBLEA · BOYACÁ · 2023', partido: 'Centro Democrático', votos: 8300, circunscripcion: 'BOYACÁ', source: 'asamblea' },
  ]);
  searchCandidate('Ricardo Esteban Ruiz', true);
});
await p.waitForSelector('#searchResults .result');
const r = {};
r.resultados = await p.$$eval('#searchResults .result b', n => n.map(x => x.textContent));
r.nitidos = await p.$$eval('#searchResults .result', n => n.every(x => {
  const s = getComputedStyle(x);
  return s.filter === 'none' && s.pointerEvents !== 'none' && s.visibility === 'visible';
}));
r.sinMuroEncima = await p.$$eval('#existing .c360-wall', n => n.length === 0);
r.avisoVitrina = (await p.textContent('#existing .c360-vitrina p')).slice(0, 70);
await p.screenshot({ path: '/tmp/c360-anon-busqueda.png' });
// Seleccionar un candidato: debe ENTRAR, no rebotar contra el modal
await p.locator('#searchResults .result').first().click();
await p.waitForTimeout(600);            /* la tarjeta brinca 320 ms antes de abrir */
r.pantalla = await p.evaluate(() => [...document.querySelectorAll('.screen')].filter(s => !s.classList.contains('hidden')).map(s => s.id));
r.paywallAbierto = await p.evaluate(() => document.getElementById('c360Paywall').classList.contains('open'));
r.nombreEnPantalla = await p.textContent('#routeName');
r.historialEnPantalla = await p.textContent('#routeHistory');
r.avisoRuta = (await p.textContent('#candidateRoute .c360-vitrina p')).slice(0, 60);
/* La ruta se responde de a una pregunta: el botón del CRM aparece con la primera. */
r.botonAntesDeResponder = await p.evaluate(() => document.getElementById('abrirCRM').classList.contains('hidden'));
await p.evaluate(() => { document.querySelector('input[name="corporationRoute"][value="same"]').checked = true; toggleCorporationChoice({ animar: true }); });
await p.waitForTimeout(400);
r.botonCRM = await p.textContent('#candidateRoute button.next');
await p.screenshot({ path: '/tmp/c360-anon-candidato.png' });
// Abrir el CRM sí topa con el muro
await p.click('#candidateRoute button.next');
await p.waitForTimeout(300);
r.muroAlAbrirCRM = await p.evaluate(() => document.getElementById('c360Paywall').classList.contains('open'));
r.noEntroAlCRM = await p.evaluate(() => document.getElementById('crm').classList.contains('hidden'));
await b.close();

const pruebas = [
  ['la búsqueda muestra los nombres', r.resultados.length >= 1 && /RICARDO ESTEBAN RUIZ/.test(r.resultados[0])],
  ['los resultados están nítidos y son clicables', r.nitidos === true],
  ['ya no hay muro encima de la búsqueda', r.sinMuroEncima === true],
  ['la vitrina explica qué falta sin tapar nada', /Búsquese/.test(r.avisoVitrina)],
  ['seleccionar un candidato entra a su pantalla', JSON.stringify(r.pantalla) === '["candidateRoute"]'],
  ['seleccionar no dispara el muro', r.paywallAbierto === false],
  ['se ve su nombre y su historial', /RICARDO ESTEBAN RUIZ/.test(r.nombreEnPantalla) && /2 candidaturas/.test(r.historialEnPantalla)],
  ['la pantalla avisa que el CRM pide acceso', /hasta acá puede llegar sin cuenta/.test(r.avisoRuta)],
  ['el botón dice lo que va a pasar', r.botonCRM.includes('Activar')],
  ['y no aparece hasta responder a qué corporación se lanza', r.botonAntesDeResponder === true],
  ['abrir el CRM sí topa con el muro', r.muroAlAbrirCRM === true],
  ['y no se entra al CRM', r.noEntroAlCRM === true],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const fallos = pruebas.filter(([, ok]) => !ok).length;
console.log(fallos ? `\n${fallos} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(fallos ? 1 : 0);
