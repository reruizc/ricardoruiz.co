/* prueba-vinculo-admin.mjs — la cuenta de administración se puede desvincular.
   ------------------------------------------------------------------
   El modo pruebas levanta la restricción de «un candidato por cuenta», pero
   el vínculo REAL de la cuenta sigue en el servidor y las páginas de medios y
   redes lo leen de ahí: quedaban residuos de un candidato viejo por más que
   acá se abriera otro. La intro del modo pruebas ofrece borrarlo, con la ruta
   de soporte que ya existía (DELETE /c360/admin/vinculo).

     node tools/candidato-360/prueba-vinculo-admin.mjs                        */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
const borrados = [];
p.on('dialog', d => d.accept());
await p.route('**', async route => {
  const u = route.request().url(), m = route.request().method();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('/c360/admin/vinculo') && m === 'DELETE') { borrados.push(u); return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, email: 'reruizc@gmail.com', borrado: true }) }); }
  if (u.includes('/c360/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', email: 'reruizc@gmail.com', vinculo: { tipo: 'historial', candidato: { nombre: 'ALEJANDRO PALACIO', corp: 'CONCEJO · BOGOTÁ D.C. · 2023' }, campana: { corp: 'concejo' } } }) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
/* PRUEBAS y SESSION son let/const de nivel superior: se leen por nombre, no por window. */
await p.waitForFunction(() => typeof window.borrarVinculoPropio === 'function' && PRUEBAS === true && !!SESSION.vinculo);
await p.waitForTimeout(300);

const r = {};
r.intro = await p.evaluate(() => document.getElementById('introVinculo')?.textContent || '');
r.boton = await p.evaluate(() => !!document.querySelector('.enlace-boton[onclick*="borrarVinculoPropio"]'));
await p.evaluate(() => borrarVinculoPropio());
await p.waitForTimeout(400);
r.despues = await p.evaluate(() => ({ vinculo: SESSION.vinculo, texto: document.getElementById('introVinculo')?.textContent || '' }));
await b.close();

const pruebas = [
  ['la intro del modo pruebas nombra el vínculo real que sigue en la cuenta', /ALEJANDRO PALACIO/.test(r.intro)],
  ['y ofrece borrarlo', r.boton === true],
  ['borrarlo llama a la ruta de soporte con el correo propio y un motivo', borrados.length === 1 && /email=reruizc%40gmail.com/.test(borrados[0]) && /motivo=/.test(borrados[0])],
  ['y la cuenta queda sin vínculo', r.despues.vinculo === null && !/ALEJANDRO PALACIO/.test(r.despues.texto)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 1200), borrados);
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
