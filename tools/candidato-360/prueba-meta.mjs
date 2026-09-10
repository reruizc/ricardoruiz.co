/* prueba-meta.mjs — la ⓘ que explica de dónde sale la meta de votos.
   ------------------------------------------------------------------
   El CRM mostraba un número grande («6.770 votos objetivo») sin decir por qué.
   Ahora hay una ⓘ al lado del número y otra al lado del mapa. Acá se comprueba
   que lo que cuenta la ficha es EXACTAMENTE el cálculo que hizo VoteTarget:

     · que el desglose reproduzca la meta (referencia × censo × participación ×
       margen, redondeado hacia arriba) — si la ficha y la fórmula se
       desincronizan, la ficha miente con autoridad;
     · que nombre la referencia real de 2023 y no un promedio inventado;
     · que explique también POR QUÉ cae donde cae en el mapa, y que esa frase
       cambie cuando la candidatura salta de corporación;
     · que sin referencia territorial no invente meta ni explicación.

   Todo lo remoto va simulado.

     node tools/candidato-360/prueba-meta.mjs                                  */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

/* Un Concejo de Bogotá de mentiras: 3 listas × 3 candidatos = 3 curules. */
const lista = (partido, votos) => votos.map((v, i) => ({ nombre: `${partido} ${i + 1}`, slug: `${partido}-${i}`, corp: 'CONCEJO · BOGOTÁ D.C. · 2023', circunscripcion: 'BOGOTÁ D.C.', partido, votos: v }));
const INDICE = { candidatos: [...lista('PARTIDO A', [9000, 5000, 1000]), ...lista('PARTIDO B', [6000, 3000, 500]), ...lista('PARTIDO C', [2000, 800, 100])] };
const RESULTADOS = { cities: [{ key: '16-001', name: 'BOGOTÁ', dep: 'BOGOTÁ D.C.', potencial: 100000 }],
  data: { '16-001': { comunas: { '13': { name: 'TEUSAQUILLO', votantes: 20000, validos: 19000, partidos: [['PARTIDO A', 9000]] }, '11': { name: 'SUBA', votantes: 30000, validos: 29000, partidos: [['PARTIDO A', 12000]] } } } } };

/* Cámara 2026 en Bogotá, de mentiras: Salvación Nacional no corrió al Concejo
   en 2023 y su fuerza se estima con esto. */
const CAMARA = { por_circunscripcion: { TERRITORIAL: { votval: 27400, partidos: { 'MOVIMIENTO SALVACIÓN NACIONAL': 5480, 'PARTIDO A': 9000 } } } };

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', async route => {
  const u = route.request().url();
  if (u.startsWith('file://')) return route.continue();
  if (u.includes('index-concejo-2023.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(INDICE) });
  if (u.includes('resultados-concejo-2023.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RESULTADOS) });
  if (u.includes('camara/dep-16.json')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CAMARA) });
  if (u.includes('/c360/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, acceso: true, fuente: 'admin', vinculo: null, email: 'reruizc@gmail.com' }) });
  return route.abort();
});
await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'reruizc@gmail.com' })); });
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.pintarMeta === 'function' && typeof window.VoteTarget === 'object');

const r = {};
r.ocultaAntes = await p.evaluate(() => [...document.querySelectorAll('.meta-i')].map(x => x.classList.contains('hidden')));
r.cuantas = await p.evaluate(() => document.querySelectorAll('.meta-i').length);

/* La meta real, calculada por VoteTarget con esos datos. */
r.estimate = await p.evaluate(async () => {
  crmCandidate = { nombre: 'NATALIA SOPHIA PARRA ROJAS', corp: 'CONCEJO · BOGOTÁ D.C. · 2019', circunscripcion: 'BOGOTÁ D.C.', partido: 'PARTIDO A', votos: 709, slug: 'x' };
  showScreen('crm');
  const e = await VoteTarget.estimate({ corp: 'concejo', territory: 'BOGOTÁ D.C.', baseUrl: 'https://stub/output' });
  pintarMeta(e);
  return e;
});
r.visibleDespues = await p.evaluate(() => [...document.querySelectorAll('.meta-i')].map(x => !x.classList.contains('hidden')));
await p.locator('.crm-vote-target').screenshot({ path: SP + '/meta-boton.png' });
await p.evaluate(() => { document.getElementById('crmMapVotes').textContent = '5.330 votos · meta'; });
await p.locator('#crm .panel .panel-head').first().screenshot({ path: SP + '/meta-boton-mapa.png' });
await p.evaluate(() => document.querySelector('.metric-linea .meta-i').click());
r.ficha = await p.evaluate(() => ({ abierta: document.getElementById('introModal').classList.contains('open'), titulo: document.getElementById('introModalTitle').textContent, texto: document.getElementById('introModalText').textContent }));
await p.screenshot({ path: SP + '/meta-ficha.png' });

/* ── La meta según el partido ────────────────────────────────────────── */
/* No cuesta lo mismo entrar de segundo en la lista A (5.000) que arrastrar la
   lista C, que no ganó curul (a su cabeza le tocan 6.600). */
r.porPartido = {};
for (const partido of ['PARTIDO A', 'PARTIDO C', 'MOVIMIENTO SALVACIÓN NACIONAL', 'PARTIDO INEXISTENTE']) {
  r.porPartido[partido] = await p.evaluate(async partido => {
    const e = await VoteTarget.estimate({ corp: 'concejo', territory: 'BOGOTÁ D.C.', baseUrl: 'https://stub/output', partido, departamento: '16' });
    pintarMeta(e); mostrarMetaInfo();
    return { target: e.target, ref: e.detalle.referencia, tipo: e.detalle.partido?.tipo, k: e.detalle.partido?.k, texto: document.getElementById('introModalText').textContent, formula: e.formula };
  }, partido);
}
await p.screenshot({ path: SP + '/meta-partido.png' });

/* Con salto de corporación, la explicación del reparto cambia. */
r.conSalto = await p.evaluate(() => {
  SALTO_ACTUAL = { tipo: { clave: 'jal>concejo', unidad: 'localidad' }, corpOrigen: 'jal', corpDestino: 'concejo', arraigo: { valor: .31, lift: 2.4, n: 36, ambito: 'departamento' },
    base: { capa: 'partido', etiqueta: 'NUEVO LIBERALISMO', proporciones: {} } };
  mostrarMetaInfo();
  return document.getElementById('introModalText').textContent;
});
/* Y sin referencia territorial no hay meta ni ficha inventada. */
r.sinMeta = await p.evaluate(async () => {
  SALTO_ACTUAL = null;
  const e = await VoteTarget.estimate({ corp: 'gobernacion', territory: 'UN LUGAR QUE NO EXISTE', baseUrl: 'https://stub/output' });
  pintarMeta(e);
  mostrarMetaInfo();
  return { numero: document.getElementById('crmVoteNumber').textContent, ocultas: [...document.querySelectorAll('.meta-i')].every(x => x.classList.contains('hidden')), titulo: document.getElementById('introModalTitle').textContent, texto: document.getElementById('introModalText').textContent };
});
await b.close();

const d = r.estimate.detalle || {};
const rehecho = d.referencia && Math.ceil(d.referencia.votos * d.censo.factor * d.participacion.factor * (1 + d.margen) / 10) * 10;
const num = s => (s.match(/[\d.]+/g) || []).map(x => Number(x.replace(/\./g, '')));
const pruebas = [
  ['hay una ⓘ junto al número y otra junto al mapa', r.cuantas === 2],
  ['ninguna aparece antes de que haya meta', r.ocultaAntes.every(Boolean)],
  ['las dos aparecen cuando la meta se calcula', r.visibleDespues.every(Boolean)],
  ['VoteTarget entrega el desglose además de la frase', !!d.referencia && !!d.censo && !!d.participacion],
  ['el desglose rehace exactamente la meta que se muestra', rehecho === r.estimate.target],
  ['la ficha se abre y titula con la meta', r.ficha.abierta && r.ficha.titulo.includes(r.estimate.target.toLocaleString('es-CO'))],
  ['dice que no es un pronóstico sino cuántos votos hacen falta', /no es un pronóstico/i.test(r.ficha.texto) && /hacen falta/i.test(r.ficha.texto)],
  ['el artículo concuerda con la corporación (al Concejo, no «a la Concejo»)', /entrar al Concejo/.test(r.ficha.texto) && !/la Concejo/.test(r.ficha.texto)],
  ['nombra la referencia de 2023 con su número', r.ficha.texto.includes('2023') && num(r.ficha.texto).includes(d.referencia.votos)],
  ['explica el censo, la participación y el margen competitivo', /censo electoral/i.test(r.ficha.texto) && /participación/i.test(r.ficha.texto) && /margen competitivo/i.test(r.ficha.texto)],
  ['dice que redondea hacia arriba y por qué', /redondeamos hacia arriba/i.test(r.ficha.texto)],
  ['explica por qué la meta cae donde cae en el mapa', /misma proporción en que ya votaron por usted/i.test(r.ficha.texto)],
  ['con partido, la meta es la de SU lista: entrar de 2 en la lista A cuesta 5.000, no el piso',
    r.porPartido['PARTIDO A'].tipo === 'lista-con-curul' && r.porPartido['PARTIDO A'].k === 2 && r.porPartido['PARTIDO A'].ref.votos === 5000 && r.porPartido['PARTIDO A'].ref.piso === 5000],
  ['y la ficha lo cuenta: entrar de 2 en la lista, y el piso de la corporación aparte',
    /entrar de 2 en la lista de PARTIDO A/.test(r.porPartido['PARTIDO A'].texto) && /piso de la corporación/.test(r.porPartido['PARTIDO A'].texto)],
  ['una lista sin curul tiene que jalarse hasta la cifra repartidora: 6.600 para la C',
    r.porPartido['PARTIDO C'].tipo === 'lista-sin-curul' && r.porPartido['PARTIDO C'].ref.votos === 6600 && r.porPartido['PARTIDO C'].target === Math.ceil(6600 * d.censo.factor * d.participacion.factor * (1 + d.margen) / 10) * 10 && /jalar la lista/i.test(r.porPartido['PARTIDO C'].texto) && /cifra repartidora fue 7.500/.test(r.porPartido['PARTIDO C'].texto)],
  ['un partido sin lista en 2023 se estima con su Cámara de 2026',
    r.porPartido['MOVIMIENTO SALVACIÓN NACIONAL'].tipo === 'proxy-camara' && r.porPartido['MOVIMIENTO SALVACIÓN NACIONAL'].ref.votos > 5000 && /Cámara de 2026/.test(r.porPartido['MOVIMIENTO SALVACIÓN NACIONAL'].texto)],
  ['y uno sin ningún dato cae al piso de la corporación, diciéndolo',
    r.porPartido['PARTIDO INEXISTENTE'].tipo === 'sin-dato' && r.porPartido['PARTIDO INEXISTENTE'].target === r.estimate.target && /no hay lista en esta corporación en 2023 ni votación a Cámara/.test(r.porPartido['PARTIDO INEXISTENTE'].texto)],
  ['la frase corta de la meta también nombra el partido', /con PARTIDO C: llevar a la lista/.test(r.porPartido['PARTIDO C'].formula)],
  ['con salto, esa explicación pasa a ser la del salto', /Salto de Junta administradora local a Concejo/.test(r.conSalto) && /2,4 veces/.test(r.conSalto)],
  ['sin referencia no hay número', r.sinMeta.numero === '—'],
  ['ni ⓘ que prometa una explicación', r.sinMeta.ocultas === true],
  ['y si se abre a la fuerza, dice que no hay meta y por qué', /Todavía no hay meta/.test(r.sinMeta.titulo) && /una meta inventada es peor que ninguna/i.test(r.sinMeta.texto)],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (errores.length) console.log(errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify({ estimate: r.estimate, rehecho, ficha: r.ficha }, null, 1).slice(0, 1800));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
