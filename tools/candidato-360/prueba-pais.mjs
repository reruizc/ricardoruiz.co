/* prueba-pais.mjs — el selector de país en la portada.
   ------------------------------------------------------------------
   Antes del cuadro «¿Cuál es su punto de partida?» se elige el país: Colombia,
   Ecuador o Paraguay. Colombia es el producto y deja las dos rutas de siempre;
   Ecuador y Paraguay quitan las rutas —una búsqueda que no encontraría a
   nadie— y dicen qué viene y cuándo, con la fecha de su elección. La elección
   se recuerda por dispositivo y viaja en ?pais=.

     node tools/candidato-360/prueba-pais.mjs                                 */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
const p = await ctx.newPage();
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('/c360/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: false, fuente: 'ninguno', vinculo: null, soporte: 'soporte@ejemplo.co' }) });
  return route.fulfill({ status: 404, body: '' });
});
const url = 'file://' + process.cwd() + '/candidato-360.html';
const estado = () => p.evaluate(() => ({
  elegido: document.querySelector('#paisSelector [aria-pressed="true"]')?.dataset.pais,
  rutasVisibles: [...document.querySelectorAll('#choicePanel .choice')].filter(x => !x.classList.contains('hidden')).length,
  titulo: document.getElementById('choiceTitulo').textContent,
  aviso: document.getElementById('paisAviso').classList.contains('hidden') ? '' : document.getElementById('paisAviso').textContent.replace(/\s+/g, ' ').trim(),
  cta: document.querySelector('#paisAviso a')?.getAttribute('href') || '',
  selectorAntes: Boolean(document.getElementById('paisSelector').compareDocumentPosition(document.getElementById('choicePanel')) & Node.DOCUMENT_POSITION_FOLLOWING),
}));

const r = {};
await p.goto(url); await p.waitForFunction(() => typeof window.elegirPais === 'function'); await p.waitForTimeout(600);
r.defecto = await estado();
await p.click('#paisSelector [data-pais="ec"]'); r.ecuador = await estado();
await p.screenshot({ path: SP + '/pais-ecuador.png' });
await p.reload(); await p.waitForFunction(() => typeof window.elegirPais === 'function'); await p.waitForTimeout(600);
r.recordado = await estado();
await p.goto(url + '?pais=py'); await p.waitForFunction(() => typeof window.elegirPais === 'function'); await p.waitForTimeout(600);
r.paraguay = await estado();
await p.click('#paisSelector [data-pais="co"]'); r.vuelta = await estado();
await b.close();

const pruebas = [
  ['el selector va antes del cuadro y arranca en Colombia', r.defecto.selectorAntes && r.defecto.elegido === 'co' && r.defecto.rutasVisibles === 2 && /punto de partida/.test(r.defecto.titulo)],
  ['Ecuador quita las rutas y dice qué viene y cuándo', r.ecuador.elegido === 'ec' && r.ecuador.rutasVisibles === 0 && /llega a Ecuador/.test(r.ecuador.titulo) && /29 de noviembre de 2026/.test(r.ecuador.aviso) && /CNE/.test(r.ecuador.aviso)],
  ['con un botón para escribir, al correo de soporte', /^mailto:soporte@ejemplo\.co/.test(r.ecuador.cta) && /Ecuador/.test(decodeURIComponent(r.ecuador.cta))],
  ['la elección se recuerda al volver', r.recordado.elegido === 'ec' && r.recordado.rutasVisibles === 0],
  ['?pais=py manda sobre lo recordado: Paraguay, 4 de octubre', r.paraguay.elegido === 'py' && /4 de octubre de 2026/.test(r.paraguay.aviso) && /TSJE/.test(r.paraguay.aviso) && /262 distritos/.test(r.paraguay.aviso)],
  ['volver a Colombia devuelve las dos rutas y el título de siempre', r.vuelta.elegido === 'co' && r.vuelta.rutasVisibles === 2 && !r.vuelta.aviso && /punto de partida/.test(r.vuelta.titulo)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2000));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
