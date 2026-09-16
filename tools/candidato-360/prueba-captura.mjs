/* prueba-captura.mjs — la captura de redes, apagada y encendida.
   ------------------------------------------------------------------
   «Lo que se publica en sus cuentas» estaba prometido y no montado. Ahora la
   página sabe pintar una lectura de las cuatro redes —lo que se dice, quién
   amplifica y lo que se siente en los comentarios— con el contrato de
   GET /c360/captura. Pero está APAGADA hasta que se decida encenderla, y eso
   es lo primero que se comprueba: con CAPTURA_ENCENDIDA en false la página no
   pregunta por ella y se ve como hasta hoy.

   Lo que se comprueba:
     · apagada: ninguna petición a /c360/captura y el sello «Captura no conectada»;
     · forzada con ?captura=1: pide la lectura y pinta las cuatro redes;
     · cada red con su estado: X e Instagram con cifras y postura, TikTok
       «sin lectura» con su motivo (cero NO es cero conversación), Facebook
       con sus páginas;
     · las citas acompañan al porcentaje y la nota dice que los comentarios no
       son la localidad;
     · con 404 en la ruta (worker sin desplegar) se queda apagada sin error.

     node tools/candidato-360/prueba-captura.mjs                              */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const CAPTURA = JSON.parse(await readFile('tools/candidato-360/escucha/ejemplo-captura.json', 'utf8'));
const VINCULO = JSON.parse(await readFile('tools/candidato-360/escucha/ejemplo-vinculo.json', 'utf8'));

async function abrir({ query = '', captura = CAPTURA, estadoCaptura = 200 } = {}) {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 1400 } });
  const errores = [], pedidas = []; p.on('pageerror', e => errores.push(e.message));
  const json = x => ({ status: 200, contentType: 'application/json', body: JSON.stringify(x) });
  await p.route('**', route => {
    const u = route.request().url();
    if (u.startsWith('file://')) return route.continue();
    if (u.includes('/c360/me')) return route.fulfill(json({ ok: true, acceso: true, fuente: 'plan', vinculo: VINCULO, email: 'a@b.co', plan: 'c360' }));
    if (u.includes('/c360/captura')) { pedidas.push(u); return estadoCaptura === 200 ? route.fulfill(json(captura)) : route.fulfill({ status: estadoCaptura, body: '' }); }
    return route.fulfill({ status: 404, body: '' });
  });
  await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'a@b.co' })); });
  await p.goto('file://' + process.cwd() + '/candidato-360-escucha.html' + query);
  await p.waitForFunction(() => document.getElementById('captura')?.textContent.trim().length > 0, null, { timeout: 15000 }).catch(() => {});
  await p.waitForTimeout(600);
  const captura_ = await p.evaluate(() => ({ html: document.getElementById('captura').innerHTML, texto: document.getElementById('captura').textContent.replace(/\s+/g, ' '), viva: document.getElementById('captura').classList.contains('viva'),
    redes: [...document.querySelectorAll('#captura .cap-red h5')].map(h => h.firstChild.textContent.trim()), motivos: [...document.querySelectorAll('#captura .cap-motivo')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
    citas: document.querySelectorAll('#captura .cap-cita').length, barras: document.querySelectorAll('#captura .cap-postura').length }));
  return { b, p, errores, pedidas, ...captura_ };
}

const r = {};
{ const t = await abrir(); r.apagada = t; await t.p.screenshot({ path: SP + '/captura-apagada.png', fullPage: true }); await t.b.close(); }
{ const t = await abrir({ query: '?captura=1' }); r.viva = t; await t.p.screenshot({ path: SP + '/captura-encendida.png', fullPage: true }); await t.b.close(); }
{ const t = await abrir({ query: '?captura=1', estadoCaptura: 404 }); r.sinRuta = t; await t.b.close(); }

const pruebas = [
  ['apagada, la página no pregunta por la captura', r.apagada.pedidas.length === 0 && !r.apagada.viva],
  ['y se ve como hasta hoy: «Captura no conectada», con lo que traerá', /Captura no conectada/.test(r.apagada.texto) && /Lo que se siente/.test(r.apagada.texto)],
  ['forzada con ?captura=1, pide la lectura y la pinta', r.viva.pedidas.length === 1 && r.viva.viva && /Escucha encendida/.test(r.viva.texto)],
  ['las cuatro redes, en orden', r.viva.redes.join('|') === 'X|Instagram|TikTok|Facebook'],
  ['X trae cifras: 1 publicó, 3 lo mencionan, 2 amplifican', /1publicó/.test(r.viva.texto.replace(/\s/g, '')) && /3lomencionan/.test(r.viva.texto.replace(/\s/g, '')) && /@vecinatunjuelito ×3/.test(r.viva.texto)],
  ['la postura sale como barra con porcentajes', r.viva.barras === 3 && /en contra 44 %/.test(r.viva.texto) && /a favor 26 %/.test(r.viva.texto)],
  ['y nunca sin sus citas', r.viva.citas >= 5 && /diez años con el mismo cuento/.test(r.viva.texto)],
  ['TikTok sin datos lo dice con su motivo, no con un cero', r.viva.motivos.some(m => /Sin lectura esta vez/.test(m) && /no significa que no haya conversación/.test(m))],
  ['Facebook muestra las páginas que sigue', /AlcaldiaLocalTunjuelito/.test(r.viva.texto) && /CanalCapitalOficial/.test(r.viva.texto)],
  ['la nota advierte que los comentarios no son la localidad', /no son la localidad/.test(r.viva.texto) && /sarcasmo/.test(r.viva.texto)],
  ['y dice cuánto costó la lectura', /costó US\$0\.22/.test(r.viva.texto)],
  ['con la ruta sin desplegar (404) queda apagada, sin error', !r.sinRuta.viva && /Captura no conectada/.test(r.sinRuta.texto) && r.sinRuta.errores.length === 0],
  ['sin errores de JavaScript', r.apagada.errores.length === 0 && r.viva.errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) { console.log(JSON.stringify({ apagada: r.apagada.texto.slice(0, 300), viva: { redes: r.viva.redes, motivos: r.viva.motivos, citas: r.viva.citas, barras: r.viva.barras, pedidas: r.viva.pedidas, errores: r.viva.errores, texto: r.viva.texto.slice(0, 1600) } }, null, 1)); }
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
