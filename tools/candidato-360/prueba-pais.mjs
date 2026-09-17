/* prueba-pais.mjs — el país es el primer paso del cuadro «Comencemos».
   ------------------------------------------------------------------
   El cuadro pregunta primero «Seleccione su país» —Colombia, Ecuador o
   Paraguay, con su bandera— y solo después «¿Cuál es su punto de partida?»,
   que es igual para los tres: los módulos son los mismos. La elección se
   recuerda por dispositivo y ?pais= manda sobre lo recordado.

     node tools/candidato-360/prueba-pais.mjs                                 */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', route => route.request().url().startsWith('file://') ? route.continue() : route.fulfill({ status: 404, body: '' }));
const url = 'file://' + process.cwd() + '/candidato-360.html';
const listo = async () => { await p.waitForFunction(() => typeof window.elegirPais === 'function'); await p.waitForTimeout(300); };
const estado = () => p.evaluate(() => ({
  paso1: !document.getElementById('paisPaso').classList.contains('hidden'),
  paso2: !document.getElementById('partidaPaso').classList.contains('hidden'),
  tarjetas: [...document.querySelectorAll('#paisPaso .pais-card')].map(x => x.querySelector('b').textContent + ' ' + x.querySelector('.pais-bandera').textContent),
  elegido: document.getElementById('paisNombre').textContent,
  rutas: [...document.querySelectorAll('#partidaPaso .choice')].map(x => x.getAttribute('onclick')),
}));
const r = {};
await p.goto(url); await listo(); r.inicio = await estado();
await p.click('#paisPaso [data-pais="ec"]'); r.ecuador = await estado();
await p.screenshot({ path: SP + '/pais-paso2.png' });
await p.reload(); await listo(); r.recordado = await estado();
await p.goto(url + '?pais=py'); await listo(); r.paraguay = await estado();
await p.click('#partidaPaso .enlace-boton'); r.cambiar = await estado();
await p.goto(url); await listo(); await p.screenshot({ path: SP + '/pais-paso1.png' });
await b.close();
const pruebas = [
  ['arranca pidiendo el país: tres tarjetas con bandera, el punto de partida escondido', r.inicio.paso1 && !r.inicio.paso2 && r.inicio.tarjetas.join('|') === 'Colombia 🇨🇴|Ecuador 🇪🇨|Paraguay 🇵🇾'],
  ['elegir Ecuador pasa al punto de partida, con el país puesto', !r.ecuador.paso1 && r.ecuador.paso2 && r.ecuador.elegido === 'Ecuador'],
  ['y las rutas son las de siempre, iguales para todos', r.ecuador.rutas.join('|') === "beginHistorical()|showScreen('new')"],
  ['la elección se recuerda al volver', r.recordado.paso2 && r.recordado.elegido === 'Ecuador'],
  ['?pais=py manda sobre lo recordado', r.paraguay.paso2 && r.paraguay.elegido === 'Paraguay'],
  ['«cambiar país» vuelve al primer paso', r.cambiar.paso1 && !r.cambiar.paso2],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 1500));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
