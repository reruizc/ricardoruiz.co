/* prueba-puntaje.mjs — la estrella de puntuación electoral, sin red.
   ------------------------------------------------------------------
   El puntaje es 100·log10(votos+1)/log10(vmax+1) con vmax = votos del
   presidente electo: la MISMA escala de analisis-candidato.html y del modal de
   Caudal. Acá se comprueba que el presidente quede en 100, que una JAL de 342
   votos no se vaya a cero (que es lo que haría una escala lineal), que el color
   salga del CUARTIL dentro de su propia elección y no del puntaje, y que la ⓘ
   muestre las tres referencias: presidente, alcalde o gobernador, y usted.

   Necesita Leaflet en disco:
     npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz      (deja package/dist/)
     node tools/candidato-360/prueba-puntaje.mjs                                */
/* playwright puede estar local o global; con global basta el NODE_PATH del sistema. */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
import { readFile } from 'node:fs/promises';
/* dist de Leaflet: node_modules, o el `npm pack` desempacado en el cwd. */
const LEAFLET = process.env.LEAFLET_DIST || (await readFile('node_modules/leaflet/dist/leaflet.js', 'utf8').then(() => 'node_modules/leaflet/dist').catch(() => 'package/dist'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';
const leafletJS = await readFile(LEAFLET + '/leaflet.js', 'utf8');
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('leaflet.min.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: leafletJS });
  if (u.includes('index-presidencial.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ vmax: 12950643, personas: [] }) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token','t'); localStorage.setItem('rr-user', JSON.stringify({ email:'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pintarPuntaje === 'function');
await p.waitForTimeout(300);

// Índice de mentiras: una JAL de Teusaquillo con 40 rivales, la Alcaldía de
// Bogotá 2023 y la Gobernación de Boyacá 2023.
await p.evaluate(() => {
  const jal = [];
  for (let i = 0; i < 40; i++) jal.push({ nombre: `RIVAL ${i} APELLIDO UNO DOS`, slug: `j${i}`, corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion: 'BOGOTÁ D.C.', votos: 20 + i * 25, partido: 'X' });
  appendHistorical([...jal,
    { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', slug: 'yo1', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion: 'BOGOTÁ D.C.', votos: 342, partido: 'CAMBIO RADICAL' },
    { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', slug: 'yo2', corp: 'CONCEJO · BOGOTÁ D.C. · 2011', circunscripcion: 'BOGOTÁ D.C.', votos: 120, partido: 'CAMBIO RADICAL' },
    { nombre: 'CARLOS FERNANDO GALAN PACHON', slug: 'alc', corp: 'ALCALDÍA · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', votos: 1512000, partido: 'NUEVO LIBERALISMO' },
    { nombre: 'OTRO CANDIDATO ALCALDIA BOGOTA', slug: 'alc2', corp: 'ALCALDÍA · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', votos: 900000, partido: 'Y' },
    { nombre: 'GOBERNADOR DE BOYACA UNO', slug: 'gob', corp: 'GOBERNACIÓN · BOYACÁ · 2023', circunscripcion: 'BOYACÁ', votos: 320000, partido: 'Z' },
  ]);
});
const r = {};
// 1 · un candidato de cuartil alto (342 votos entre 41 → supera a muchos)
await p.evaluate(async () => {
  const perfil = candidateProfile(historicalIndex.find(c => c.slug === 'yo1'));
  crmCandidate = perfil; CAMPANA_ACTUAL = { departamentoNombre: 'Distrito Capital de Bogotá', corp: 'jal' };
  showScreen('crm');
  document.getElementById('crmName').textContent = perfil.nombre;
  await pintarPuntaje(perfil);
});
r.badge = await p.textContent('#crmPuntaje .puntaje b');
r.clase = await p.getAttribute('#crmPuntaje .puntaje', 'class');
r.estado = await p.evaluate(() => ({ puntaje: PUNTAJE_ACTUAL.puntaje, cuartil: PUNTAJE_ACTUAL.cuartil, votos: PUNTAJE_ACTUAL.votos, corp: PUNTAJE_ACTUAL.candidatura.corp }));
r.escala = await p.evaluate(() => Math.round(100 * Math.log10(12950643 + 1) / SCORE_LOG_MAX));
await p.click('.puntaje-i');
await p.waitForSelector('#introModal.open');
r.titulo = await p.textContent('#introModalTitle');
r.filas = await p.$$eval('.puntaje-escala li', n => n.map(x => x.textContent.replace(/\s+/g,' ').trim()));
r.textoCuartil = (await p.textContent('#introModalText')).replace(/\s+/g,' ');
await p.screenshot({ path: SP + '/puntaje-modal.png' });
await p.click('#introModal button');
await p.screenshot({ path: SP + '/puntaje-badge.png', clip: { x: 0, y: 60, width: 1400, height: 260 } });

// 2 · uno del cuartil superior de esa misma elección
await p.evaluate(async () => {
  const alto = { nombre: 'LA MAS VOTADA DE LA JAL', slug: 'alto', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion: 'BOGOTÁ D.C.', votos: 980 };
  appendHistorical([alto]); crmCandidate = alto; await pintarPuntaje(alto);
});
r.claseAlta = await p.getAttribute('#crmPuntaje .puntaje', 'class');
r.cuartilAlto = await p.evaluate(() => PUNTAJE_ACTUAL.cuartil.cuartil);
// 3 · el mismo candidato pero en el cuartil bajo
await p.evaluate(async () => {
  const bajo = { nombre: 'ALGUIEN MENOS VOTADO AQUI', slug: 'bajo', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', circunscripcion: 'BOGOTÁ D.C.', votos: 30 };
  appendHistorical([bajo]); crmCandidate = bajo; await pintarPuntaje(bajo);
});
r.claseBaja = await p.getAttribute('#crmPuntaje .puntaje', 'class');
// 4 · candidatura nueva: sin estrella
await p.evaluate(async () => { await pintarPuntaje({ nombre: 'NUEVA', votos: 0 }); });
r.sinHistorial = await p.evaluate(() => document.getElementById('crmPuntaje').classList.contains('hidden'));
// 5 · gobernación como referencia cuando no es Bogotá
r.refBoyaca = await p.evaluate(() => { CAMPANA_ACTUAL = { departamentoNombre: 'Boyacá' }; crmCandidate = { circunscripcion: 'BOYACÁ' }; return referenciaEjecutiva(); });
await b.close();

const pruebas = [
  ['la estrella muestra el puntaje', r.badge === String(r.estado.puntaje) && Number(r.badge) > 0],
  ['la escala deja al presidente en 100', r.escala === 100],
  ['342 votos dan un puntaje de dos dígitos, no un cero', r.estado.puntaje >= 30 && r.estado.puntaje <= 50],
  ['el cuartil sale de la misma elección', r.estado.cuartil.rivales === 41],
  ['el cuartil de en medio pinta ámbar', /q2/.test(r.clase) && r.estado.cuartil.cuartil === 2],
  ['el cuartil superior pinta verde', /q4/.test(r.claseAlta) && r.cuartilAlto === 4],
  ['el cuartil inferior pinta coral', /q1/.test(r.claseBaja)],
  ['la ⓘ abre la explicación', /puntuación electoral pasada/i.test(r.titulo)],
  ['la escala muestra al presidente en 100', /^100 · Presidencia/.test(r.filas[0])],
  ['y al alcalde de Bogotá con su puntaje', /Alcaldía de Bogotá/.test(r.filas[1]) && /GALAN/.test(r.filas[1])],
  ['y al final el suyo', /usted, con 342 votos/.test(r.filas[2])],
  ['explica el cuartil con rivales y percentil', /41 candidaturas/.test(r.textoCuartil) && /superó al/.test(r.textoCuartil)],
  ['una candidatura nueva no lleva estrella', r.sinHistorial === true],
  ['fuera de Bogotá la referencia es la gobernación', r.refBoyaca?.cargo?.includes('Gobernación') && r.refBoyaca.votos === 320000],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0,3));
const f = pruebas.filter(([, ok]) => !ok).length;
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
