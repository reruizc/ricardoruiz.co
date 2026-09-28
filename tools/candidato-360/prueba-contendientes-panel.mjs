/* prueba-contendientes-panel.mjs — el panel 10 (candidato-360-contendientes.html)
   y la tarjeta 10 del CRM, con TODO lo remoto simulado.
   ------------------------------------------------------------------
   Una JAL de juguete con la forma de los archivos reales: cuatro listas, tres
   curules, cuatro puestos, una candidata de referencia que fue 3.ª de su
   lista y una rival de 2019 (fuente C). Se comprueba:
     · el panel: plano con la columna «usted», escalera a N votos del último
       elegido, tabla ordenable, ficha con historial y la meta de su lista,
       sin la palabra «amenaza», sin desborde a 375 px, muro sin acceso;
     · la campaña de «la misma corporación» llega SIN territorio (así la
       guarda el CRM) y aun así se lee la matriz del territorio;
     · la tarjeta del CRM en vitrina: solo 3 nombres en el plano, los demás
       borrosos y sin texto, y el MISMO conteo que el panel.

     node tools/candidato-360/prueba-contendientes-panel.mjs
     (PLAYWRIGHT_PATH=/opt/homebrew/lib/node_modules/playwright/index.mjs si
     Playwright está instalado de forma global)                              */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));

const NL = 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', VERDE = 'PARTIDO ALIANZA VERDE', CD = 'PARTIDO CENTRO DEMOCRÁTICO', ASI = 'PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"';
const CIRC = 'BARRIOS UNIDOS · BOGOTÁ D.C.', CORP = `JAL · ${CIRC} · 2023`;
const USTED = 'USTED CANDIDATA DE PRUEBA', SLUG = 'JAL2023-16-1-7523-82-aaa111';
/* [nombre, partido, votos por puesto P1..P4, slug] */
const CANDS = [
  ['ANA MARIA RUIZ SOTO', NL, [400, 300, 100, 100], 'JAL2023-16-1-7523-81-a01'],
  ['LUIS JOSE PAZ ROA', NL, [100, 100, 300, 300], 'JAL2023-16-1-7523-83-a02'],
  [USTED, NL, [300, 150, 30, 20], SLUG],
  ['MARIO LUIS DIAZ RIOS', NL, [25, 25, 25, 25], 'JAL2023-16-1-7523-84-a04'],
  ['VERA LUCIA MORA PAZ', VERDE, [250, 250, 250, 250], 'JAL2023-16-1-4-81-v01'],
  ['VICTOR HUGO LEON RUA', VERDE, [75, 75, 75, 75], 'JAL2023-16-1-4-82-v02'],
  ['DIEGO ANDRES GIL LARA', CD, [100, 100, 500, 500], 'JAL2023-16-1-11-81-d01'],
  ['DORA ELENA SUAREZ VEGA', CD, [100, 100, 100, 100], 'JAL2023-16-1-11-82-d02'],
  ['SAUL ANTONIO PEREZ CRUZ', ASI, [300, 50, 50, 50], 'JAL2023-16-1-3-81-s01'],
];
const LISTA = { [NL]: [50, 50, 50, 50], [VERDE]: [25, 25, 25, 25] };
const PARTIDOS = [NL, VERDE, CD, ASI];
const suma = a => a.reduce((x, y) => x + y, 0);
const totalPartido = p => suma(CANDS.filter(c => c[1] === p).map(c => suma(c[2]))) + suma(LISTA[p] || [0]);
const INDICE = {
  candidatos: CANDS.map(([nombre, partido, v, slug]) => ({ slug, nombre, corp: CORP, circunscripcion: CIRC, partido, votos: suma(v) })),
  listas: Object.entries(LISTA).map(([partido, l]) => ({ circunscripcion: CIRC, partido, lista: suma(l), personal: totalPartido(partido) - suma(l), total: totalPartido(partido), cerrada: false })),
};
const MATRIZ = { dde: '16', mme: '001', comuna: '12', name: 'COMUNA 12', has_barrio_map: false,
  partidos: PARTIDOS.map(p => [p, totalPartido(p)]), cands: CANDS.map(c => [c[0], PARTIDOS.indexOf(c[1])]),
  puestos: [0, 1, 2, 3].map(i => ({ code: `12-0${i + 1}`, nombre: `PUESTO ${i + 1}`, barrio: `Barrio ${i + 1}`, lat: 4.66 + i / 200, lon: -74.07, validos: 2000, blanco: 0, nulos: 0,
    v: CANDS.map((c, k) => [k, c[2][i]]).filter(x => x[1]), l: Object.entries(LISTA).map(([p, l]) => [PARTIDOS.indexOf(p), l[i]]) })) };
const RESULTADOS = { cities: [{ key: '16-001', name: 'BOGOTÁ D.C.', dep: 'BOGOTÁ D.C.', potencial: 100000 }],
  data: { '16-001': { comunas: { '12': { name: 'BARRIOS UNIDOS', potencial: 20000, votantes: 7000, blanco: 0 } } } } };
const mesas = (v, extra = {}) => v.map((x, i) => ({ dep: '16', depNom: 'BOGOTÁ D.C.', mun: '001', munNom: 'BOGOTÁ D.C.', zon: '12', pue: `0${i + 1}`, pueNom: `PUESTO ${i + 1}`, mesa: '001', com: '12', comNom: 'BARRIOS UNIDOS', v: x, ...extra })).filter(m => m.v);
const ROSA = { slug: 'JAL2019-16-1-4-83-bbb222', nombre: 'ROSA INES CANO MEJIA', corp: 'JAL · BARRIOS UNIDOS · BOGOTÁ D.C. · 2019', circunscripcion: CIRC, partido: VERDE, votos: 700 };
const ANA19 = { slug: 'JAL2019-16-1-7523-81-ccc333', nombre: 'ANA MARÍA RUIZ SOTO', corp: 'JAL · BARRIOS UNIDOS · BOGOTÁ D.C. · 2019', circunscripcion: CIRC, partido: 'PARTIDO NUEVO LIBERALISMO', votos: 650 };
const ARCHIVOS = {
  'jal-2023/index-jal-2023.json': INDICE,
  'jal-2023/resultados-jal-2023.json': RESULTADOS,
  'hvp/curules-jal.json': { curules: { 'BARRIOS UNIDOS|BOGOTA D C': 3 } },
  'jal-2023/comuna/16-001-12.json': MATRIZ,
  'mapas-2026/Departamentos-mps/16.json': { features: [{ properties: { mpio_cnmbr: 'BOGOTÁ, D.C.', mun_elec: '001' } }] },
  [`jal-2023/${SLUG}.json`]: { nombre: USTED, corp: CORP, circunscripcion: CIRC, partido: NL, votos: 500, mesas: mesas([300, 150, 30, 20]) },
  'jal-2019/index-jal-2019.json': { candidatos: [ROSA, ANA19] },
  [`jal-2019/${ROSA.slug}.json`]: { ...ROSA, mesas: mesas([500, 200, 0, 0]) },
  'jal-2015/index-jal-2015.json': { candidatos: [] },
};
const VINCULO = { tipo: 'historial', candidato: { nombre: USTED, slugs: [SLUG], corp: CORP, id: 'persona-usted' },
  campana: { corp: 'jal', ruta: 'same', avales: 'partido', partido: NL, departamento: '', municipio: '', localidad: '' } };

let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const pedidos = [];
async function montar(page, { acceso = true } = {}) {
  await page.addInitScript(() => { localStorage.setItem('rr-token', 't-prueba'); localStorage.setItem('rr-user', JSON.stringify({ email: 'prueba@ejemplo.co', plan: 'c360' })); });
  await page.route('**', async route => {
    const u = route.request().url();
    if (u.startsWith('file://')) return route.continue();
    if (u.includes('/c360/me')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(acceso ? { ok: true, acceso: true, fuente: 'plan', vinculo: VINCULO, email: 'prueba@ejemplo.co', plan: 'c360' } : { ok: true, acceso: false, fuente: 'ninguno', vinculo: null }) });
    const k = Object.keys(ARCHIVOS).find(x => u.split('?')[0].endsWith(x));
    if (k) { pedidos.push(k); return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ARCHIVOS[k]) }); }
    if (/amazonaws\.com|workers\.dev/.test(u)) return route.fulfill({ status: 404, body: '{}' });
    return route.abort();
  });
}

const b = await chromium.launch();
try {
  /* ── El panel, con acceso ─────────────────────────────────────────────── */
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errores = []; p.on('pageerror', e => errores.push(e.message));
  await montar(p);
  await p.goto('file://' + process.cwd() + '/candidato-360-contendientes.html');
  await p.waitForFunction(() => window.C360ContendientesPagina?.lectura() || /No pudimos/.test(document.getElementById('kEstado')?.textContent || ''), null, { timeout: 30000 });
  const L = await p.evaluate(() => { const L = C360ContendientesPagina.lectura(); return L && { n: L.resumen.enIndice, niveles: L.resumen.niveles, rivales: L.rivales.map(r => ({ nombre: r.nombre, fuentes: r.fuentes, enIndice: r.enIndice, nivel: r.nivel })), esc: L.escalera && { estado: L.escalera.estado, puesto: L.escalera.usted?.puesto, distancia: L.escalera.distancia, k: L.escalera.k }, origen: L.resumen.origen, campana: L.campana }; });
  ok(!!L, `el panel lee la candidatura (${await p.textContent('#kEstado')})`);
  ok(L?.origen === 'matriz' && pedidos.includes('jal-2023/comuna/16-001-12.json') && L.campana.localidad === 'BARRIOS UNIDOS', 'la campaña de «la misma corporación» llega sin territorio y aun así se lee la matriz de su localidad');
  const nombres = (L?.rivales || []).map(r => r.nombre).sort().join(' | ');
  ok(nombres === ['ANA MARIA RUIZ SOTO', 'DIEGO ANDRES GIL LARA', 'LUIS JOSE PAZ ROA', 'ROSA INES CANO MEJIA', 'VERA LUCIA MORA PAZ'].join(' | '), `rivales: los 3 elegidos, el de su lista con ≥ 50 % del último elegido y la de 2019 (${nombres})`);
  ok(L?.rivales.find(r => r.nombre === 'ANA MARIA RUIZ SOTO')?.fuentes.join() === 'A,C', 'la elegida de 2023 que también compitió en 2019 es una sola persona, sin bajar su archivo viejo');
  ok(!pedidos.some(x => x.includes('ccc333')), 'no se bajó el archivo de 2019 de quien ya es rival por 2023');
  ok(!L?.rivales.some(r => r.nombre.startsWith('SAUL')), 'el de ASI (450 < 500) no pasa el umbral');
  ok(L?.esc?.estado === 'abierta' && L.esc.puesto === 3 && L.esc.distancia === 400 && L.esc.k === 1, `escalera: 3.ª de su lista, a 400 votos del último elegido (${JSON.stringify(L?.esc)})`);
  ok(await p.$eval('#kPlano svg', s => s.querySelectorAll('circle.k-punto').length) === L?.rivales.length, 'el plano pinta un punto por rival');
  ok(await p.$eval('#kPlano svg', s => !!s.querySelector('.k-usted') && /usted/.test(s.textContent)), 'la columna de su familia va marcada «usted»');
  ok(/3\.º, a 400 votos/.test(await p.textContent('#kEscaleraCopy')), 'la escalera lo dice en texto');
  ok(await p.$$eval('#kFilas tr', t => t.length) === L?.rivales.length, 'la tabla trae a todos los rivales');
  await p.click('.k-tabla th[data-orden="nombre"]');
  const primero = await p.$eval('#kFilas tr b', x => x.textContent);
  ok(/^Ana/i.test(primero), `ordenar por nombre (${primero})`);
  await p.click('#kPlano circle[data-key]');
  await p.waitForFunction(() => !document.getElementById('kFichaSec').classList.contains('hidden'));
  const ficha = await p.textContent('#kFicha');
  ok(/Historial electoral/.test(ficha) && /Frente a usted/.test(ficha), 'la ficha abre con historial y la lectura frente a usted');
  await p.click('#kFilas tr[data-key]');   /* orden por nombre: la primera es Ana, fuente A */
  await p.waitForFunction(() => /meta de su lista/i.test(document.getElementById('kFichaMeta').textContent), null, { timeout: 15000 }).catch(() => {});
  ok(/meta de su lista/i.test(await p.textContent('#kFichaMeta')), 'la ficha de una elegida trae la meta de su lista, con la misma cuenta de la meta propia');
  ok(!/amenaza/i.test(await p.textContent('body')), 'la palabra «amenaza» no aparece en la página');
  ok(/Rivales probables, no inscritos/.test(await p.textContent('#kNota')), 'la nota dice que son rivales probables y de dónde salen');
  await p.setViewportSize({ width: 375, height: 800 });
  await p.waitForTimeout(150);
  ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'sin desborde horizontal a 375 px');
  ok(!errores.length, `sin errores de página${errores.length ? `: ${errores.join(' · ')}` : ''}`);
  await p.close();

  /* ── Sin acceso: el muro ──────────────────────────────────────────────── */
  const q = await b.newPage();
  await montar(q, { acceso: false });
  await q.goto('file://' + process.cwd() + '/candidato-360-contendientes.html');
  await q.waitForSelector('#panelMuro:not(.hidden)');
  ok(/no tiene acceso/.test(await q.textContent('#panelMuro')) && !(await q.$('#kPlano svg')), 'sin acceso: el muro, y el plano no se pinta');
  await q.close();

  /* ── La tarjeta 10 en el CRM, en vitrina ───────────────────────────────── */
  const c = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await montar(c, { acceso: false });
  await c.goto('file://' + process.cwd() + '/candidato-360.html');
  await c.waitForFunction(() => typeof window.pintarContendientes === 'function' || typeof pintarContendientes === 'function');
  await c.evaluate(async ({ SLUG, USTED, NL, CORP, campana }) => {
    const url = C360Electorado.urlCandidatura(SLUG);
    crmCandidate = { nombre: USTED, slug: SLUG, dataUrl: url, corp: CORP, partido: NL, history: [{ nombre: USTED, slug: SLUG, dataUrl: url, corp: CORP, partido: NL }] };
    CAMPANA_ACTUAL = campana; META_ACTUAL = null; CRM_VITRINA = true;
    await pintarContendientes();
  }, { SLUG, USTED, NL, CORP, campana: VINCULO.campana });
  const dato = await c.textContent('#crmContDato');
  ok(dato === String(L?.n), `la tarjeta y el panel dan el mismo conteo (${dato} y ${L?.n})`);
  const sub = await c.textContent('#crmContSub');
  ok(sub.includes(`alta ${L?.niveles.alta}`) && sub.includes(`baja ${L?.niveles.baja}`), `y los mismos niveles (${sub})`);
  const vit = await c.$eval('#crmContPlano svg', s => ({ nombres: s.querySelectorAll('.k-nombre').length, borrosos: s.querySelectorAll('.vitrina-blur').length, titulos: s.querySelectorAll('title').length, texto: s.textContent }));
  ok(vit.nombres === 3 && vit.titulos === 3 && vit.borrosos === (L?.rivales.length || 0) - 3, `vitrina: 3 nombres nítidos y ${vit.borrosos} puntos borrosos sin texto`);
  const ocultos = (L?.rivales || []).map(r => r.nombre).filter(n => !/^(ANA|LUIS|VERA|DIEGO|ROSA)/.test(n));
  ok(!ocultos.some(n => vit.texto.includes(n)), 'el nombre de los borrosos no está en el DOM');
  const bloqueado = await c.evaluate(() => { const ev = new MouseEvent('click', { bubbles: true, cancelable: true }); document.getElementById('crmContBtn').dispatchEvent(ev); return ev.defaultPrevented; });
  ok(bloqueado && c.url().endsWith('candidato-360.html'), 'en vitrina el botón del módulo no abre el panel (lo intercepta el paywall)');
  await c.close();
} finally {
  await b.close();
}
console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en orden');
process.exit(fallas ? 1 : 0);
