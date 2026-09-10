/* prueba-medios-nacional.mjs — el panel 04 con el país arriba y la ciudad abajo.
   ------------------------------------------------------------------
   La página completa, sin red: prensa simulada, vínculo simulado. Comprueba el
   orden de los tres bloques, que el top del país tenga tres historias y diga
   cuántos medios cubrió cada una, que un titular local no se cuele arriba, y
   que la cuenta de administración pueda soltar la candidatura desde acá — que
   es de donde salían los residuos de una candidatura vieja.

     node tools/candidato-360/prueba-medios-nacional.mjs                       */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

const nota = (titulo, medio, fecha = '2026-09-10') => ({ titulo, medio, fecha, url: 'https://ej/' + encodeURIComponent(medio) });
const NACIONAL = [
  nota('Petro sanciona la reforma pensional en la Casa de Nariño', 'EL TIEMPO'),
  nota('Presidente Petro sancionó la reforma pensional', 'EL ESPECTADOR'),
  nota('Reforma pensional sancionada: qué cambia para los cotizantes', 'SEMANA', '2026-09-11'),
  nota('Corte Constitucional tumbó el decreto de conmoción interior', 'BLU RADIO'),
  nota('Cayó el decreto de conmoción interior en la Corte', 'W RADIO'),
  nota('Paro camionero completa cinco días de bloqueos en vías del país', 'LA FM'),
  nota('Un solo medio cuenta esta historia sin importancia nacional', 'PORTAL X'),
];
const LOCAL = [
  nota('Concejo de Bogotá aprobó el presupuesto distrital para 2027', 'EL TIEMPO'),
  nota('Alcaldía de Bogotá anuncia obras en la Avenida 68', 'CITY TV'),
];
const PERSONAL = [nota('Ana Lucía Vargas Peña lanza su candidatura al Concejo', 'EL NUEVO SIGLO')];

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 1400 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
p.on('dialog', d => d.accept());
let vinculoBorrado = false;
await p.route('**', async route => {
  const u = route.request().url(), m = route.request().method();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('/c360/admin/vinculo') && m === 'DELETE') { vinculoBorrado = true; return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true,"borrado":true}' }); }
  if (u.includes('/c360/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', email: 'reruizc@gmail.com',
    vinculo: { tipo: 'historial', candidato: { nombre: 'ANA LUCIA VARGAS PEÑA' }, campana: { corp: 'concejo', municipio: 'BOGOTÁ, D.C.', departamentoNombre: 'Bogotá D.C.', departamento: '16' } } }) });
  if (u.includes('/caudal/api')) {
    const q = JSON.parse(route.request().postData() || '{}').query || '';
    const esNacional = /Colombia|Gobierno Nacional|Congreso de la Rep/i.test(q);
    const esNombre = /VARGAS/i.test(q);
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ resultados: esNacional ? NACIONAL : esNombre ? PERSONAL : LOCAL }) });
  }
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360-medios.html');
await p.waitForSelector('#territorioLectura .tema', { timeout: 20000 });
await p.waitForTimeout(500);

const r = await p.evaluate(() => ({
  titulos: [...document.querySelectorAll('#territorioLectura .tema h3')].map(x => x.textContent),
  pais: [...document.querySelectorAll('#territorioLectura .tema')].map(t => ({ h: t.querySelector('h3').textContent, filas: [...t.querySelectorAll('li')].map(li => li.textContent) })),
  panelTitulo: document.getElementById('territorioTitulo').textContent,
  escala: document.getElementById('territorioEscala').textContent,
  cabecera: document.getElementById('panelCandidatura').textContent,
  soltar: !!document.querySelector('#panelCandidatura .soltar-vinculo'),
}));
await p.screenshot({ path: SP + '/medios-nacional.png', fullPage: false });
await p.click('#panelCandidatura .soltar-vinculo');
await p.waitForTimeout(500);
await b.close();

const paisBloque = r.pais.find(x => /habla el país/i.test(x.h)) || { filas: [] };
const ciudad = r.pais.find(x => /Lo que pasa en/i.test(x.h)) || { filas: [] };
const pruebas = [
  ['los bloques van: usted, el país, la ciudad', /nombra a usted/i.test(r.titulos[0] || '') && /habla el país/i.test(r.titulos[1] || '') && /Lo que pasa en/i.test(r.titulos[2] || '')],
  ['el top del país trae tres historias', paisBloque.filas.length === 3],
  ['la más cubierta va primero y dice cuántos medios', /reforma pensional/i.test(paisBloque.filas[0] || '') && /3 medios lo publicaron/.test(paisBloque.filas[0] || '')],
  ['una historia de un solo medio lo dice, no infla el número', paisBloque.filas.some(f => /un solo medio/.test(f)) === false || !/PORTAL X/.test(paisBloque.filas[0] || '')],
  ['lo local no se cuela en el bloque del país', !paisBloque.filas.some(f => /Concejo de Bogotá|Avenida 68/i.test(f))],
  ['y lo local sigue en su bloque', ciudad.filas.some(f => /Concejo de Bogotá/i.test(f))],
  ['el titular que la nombra a ella no aparece en el país', !paisBloque.filas.some(f => /VARGAS/i.test(f))],
  ['el panel ya no promete solo el territorio', /De qué se está hablando/i.test(r.panelTitulo) && /agenda del país/i.test(r.escala)],
  ['la cabecera deja soltar la candidatura (cuenta de administración)', r.soltar === true && /ANA LUCIA VARGAS/.test(r.cabecera)],
  ['y soltarla llama a la ruta de soporte', vinculoBorrado === true],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 2200));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
