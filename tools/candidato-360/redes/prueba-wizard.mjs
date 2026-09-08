/* prueba-wizard.mjs — recorre el paso 2 de candidato-360.html sin red.
   ------------------------------------------------------------------
   Levanta la página con file://, corta TODO lo externo (S3, cdnjs, fuentes) y
   stubbea el worker: `/c360/me` contesta como cuenta de administración y
   `/c360/redes` devuelve una validación de mentiras con un perfil confirmado y
   otro inexistente. Con eso comprueba, sin gastar un token de DeepSeek:

     · el modo pruebas se enciende y levanta la restricción de «un candidato»,
     · las tres redes se marcan y el usuario se limpia (URL pegada → handle),
     · «Siguiente» pide validar UNA vez y a la segunda deja pasar,
     · los veredictos se pintan con su sello,
     · editar un usuario después de validar borra el veredicto,
     · al cerrar el wizard NO sale ningún POST a /c360/vinculo ni /c360/campana.

   Correr desde la raíz del repo (playwright global, Chromium ya instalado):
     node tools/candidato-360/redes/prueba-wizard.mjs                          */
/* playwright puede estar local o global; con global basta el NODE_PATH del sistema. */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const b = await chromium.launch();
const p = await b.newPage();
const errores = [];
p.on('pageerror', e => errores.push('PAGEERROR: ' + e.message));
p.on('console', m => { if (m.type() === 'error') errores.push('CONSOLE: ' + m.text().slice(0,120)); });

// La red externa está bloqueada en este sandbox: se corta todo lo remoto para
// que la página no se quede esperando, y se stubbea el worker.
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('/c360/redes')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    ok: true, modelo: 'deepseek-v4-flash', generado_en: '2026-09-08T04:00:00+00:00', cache_hit: false,
    resumen: 'La identidad pública que vamos a escuchar es @laprofe en TikTok.',
    riesgo_homonimo: 'Hay una periodista con el mismo nombre en Medellín.',
    alertas: ['Confirme el usuario de X: la cuenta no existe.'],
    titulares: [{ titulo: 'La Profe lidera veeduría', medio: 'El Espectador', link: 'https://x.co/1' }],
    perfiles: [
      { red: 'tiktok', handle: 'laprofe', url: 'https://www.tiktok.com/@laprofe', veredicto: 'confirmado', confianza: 88, existe: true, sondeo: 'ok', nombre_perfil: 'Alejandra Palacio', seguidores: null, motivo: 'El nombre del perfil coincide con el de la candidatura.' },
      { red: 'x', handle: 'noexiste123', url: 'https://x.com/noexiste123', veredicto: 'no_encontrado', confianza: 0, existe: false, sondeo: 'no_encontrado', motivo: 'X respondió que ese usuario no tiene cuenta.' }
    ] }) });
  if (u.includes('/c360/me') || u.includes('/c360/planes')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com', plan: 'premium', soporte: 'hola@ricardoruiz.co' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com', plan: 'premium' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.montarRedes === 'function');
await p.waitForTimeout(600);

const r = {};
r.modoPruebas = await p.evaluate(() => PRUEBAS);
r.avisoPruebas = (await p.textContent('#introVinculo')).slice(0, 60);
await p.click('#intro .choice-panel button:nth-of-type(2)');
await p.fill('#newName', 'Alejandra Palacio Restrepo');
await p.click('.new-wizard-step[data-step="0"] .wizard-next');
await p.check('#publicFigure');
await p.fill('#publicName', 'La Profe');
r.tituloPaso2 = await p.textContent('.new-wizard-step[data-step="1"] h3');
r.filas = await p.$$eval('.red-row', n => n.map(x => x.dataset.red));
r.inputBloqueado = await p.$eval('#red-tiktok', i => i.disabled);
await p.click('.red-row[data-red="tiktok"] .red-chip');
r.inputAbierto = await p.$eval('#red-tiktok', i => !i.disabled);
await p.fill('#red-tiktok', 'https://www.tiktok.com/@laprofe?lang=es');
await p.click('.red-row[data-red="x"] .red-chip');
await p.fill('#red-x', '@noexiste123');
r.elegidas = await p.evaluate(() => redesElegidas());
r.estadoAntes = await p.textContent('#redesEstado');
// «Siguiente» sin validar: pide validar la primera vez, pasa la segunda
await p.click('.new-wizard-step[data-step="1"] .wizard-next');
r.pidioValidar = (await p.textContent('#redesResultado')).includes('sin validar');
r.siguePaso2 = await p.$eval('.new-wizard-step[data-step="1"]', e => e.classList.contains('active'));
await p.click('#redesBuscar');
try { await p.waitForSelector('.red-ficha', { timeout: 8000 }); } catch (e) {
  console.log('SIN FICHAS · html:', (await p.innerHTML('#redesResultado')).slice(0, 500));
  console.log('estado:', await p.textContent('#redesEstado'), '· disabled:', await p.$eval('#redesBuscar', b => b.disabled));
  console.log('errores:', errores.slice(0, 8)); await b.close(); process.exit(1);
}
r.sellos = await p.$$eval('.red-sello', n => n.map(x => x.textContent));
r.homonimo = (await p.textContent('.redes-homonimo')).slice(0, 40);
r.estadoDespues = await p.textContent('#redesEstado');
r.guardado = await p.evaluate(() => redesParaGuardar());
// Editar un usuario invalida el veredicto
await p.fill('#red-tiktok', 'otro.usuario');
r.trasEditar = await p.evaluate(() => ({ validacion: REDES_VALIDACION, estado: document.getElementById('redesEstado').textContent }));
r.pasaSegunda = await p.evaluate(() => {
  showNewWizardStep(1);
  const next = document.querySelector('.new-wizard-step[data-step="1"] .wizard-next');
  next.click();   // pide validar
  const pidio = document.querySelector('.new-wizard-step[data-step="1"]').classList.contains('active');
  next.click();   // insiste: pasa
  return { pidioOtraVez: pidio, avanzo: document.querySelector('.new-wizard-step[data-step="2"]').classList.contains('active') };
});
// Cerrar el wizard en modo pruebas: no puede haber POST /c360/vinculo
const escrituras = [];
p.on('request', q => { if (/\/c360\/(vinculo|campana)/.test(q.url())) escrituras.push(q.method() + ' ' + q.url()); });
await p.evaluate(() => {
  const dep = document.getElementById('department');
  dep.innerHTML = '<option value="16">Bogotá D.C.</option>'; dep.value = '16';
  document.getElementById('election').value = 'concejo';
  const party = document.getElementById('party');
  party.innerHTML = '<option value="Partido Verde">Partido Verde</option>'; party.value = 'Partido Verde';
  document.querySelector('#new form').requestSubmit();
});
await p.waitForTimeout(1200);
r.pantallaFinal = await p.evaluate(() => [...document.querySelectorAll('.screen')].filter(s => !s.classList.contains('hidden')).map(s => s.id));
r.escriturasAlWorker = escrituras;
r.vinculoLocal = await p.evaluate(() => SESSION.vinculo && { local: SESSION.vinculo.local, tipo: SESSION.vinculo.tipo, redes: SESSION.vinculo.nuevo?.redes?.validado });
r.contextoCRM = (await p.textContent('#crmContext')).slice(-160);
await b.close();

const limpios = errores.filter(e => !/net::ERR|Failed to load|preload/.test(e));
const pruebas = [
  ['modo pruebas encendido para la cuenta de administración', r.modoPruebas === true],
  ['la portada avisa que nada se guarda', /Modo pruebas/.test(r.avisoPruebas)],
  ['el paso 2 pregunta por la identidad y las redes', r.tituloPaso2 === '¿Dónde puede encontrarlo la gente?'],
  ['están las tres redes', JSON.stringify(r.filas) === '["x","tiktok","instagram"]'],
  ['el usuario solo se escribe con la red marcada', r.inputBloqueado === true && r.inputAbierto === true],
  ['una URL pegada queda en handle', r.elegidas.some(x => x.red === 'tiktok' && x.handle === 'laprofe')],
  ['«Siguiente» sin validar pide validar y no avanza', r.pidioValidar === true && r.siguePaso2 === true],
  ['cada red trae su sello', JSON.stringify(r.sellos) === '["Confirmado · 88%","Sin cuenta"]'],
  ['el riesgo de homónimo se muestra', /homónimo/.test(r.homonimo)],
  ['la validación se guarda con el vínculo', r.guardado.validado === true && r.guardado.perfiles.length === 2],
  ['editar un usuario borra el veredicto', r.trasEditar.validacion === null && /sin validar/.test(r.trasEditar.estado)],
  ['a la segunda insistida el wizard deja pasar', r.pasaSegunda.pidioOtraVez === true && r.pasaSegunda.avanzo === true],
  ['el CRM abre', JSON.stringify(r.pantallaFinal) === '["crm"]'],
  ['en modo pruebas NO se escribe en el worker', r.escriturasAlWorker.length === 0],
  ['el vínculo queda solo en memoria', r.vinculoLocal?.local === true],
  ['el CRM dice con qué identidad va a escuchar', /Escucharemos/.test(r.contextoCRM)],
  ['sin errores de JavaScript', limpios.length === 0],
];
for (const [titulo, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${titulo}`);
if (limpios.length) console.log('errores:', limpios.slice(0, 6));
const fallos = pruebas.filter(([, ok]) => !ok).length;
console.log(fallos ? `\n${fallos} de ${pruebas.length} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(fallos ? 1 : 0);
