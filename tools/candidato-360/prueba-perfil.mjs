/* prueba-perfil.mjs — el electorado de una candidatura, en su propia página.
   ------------------------------------------------------------------
   La tarjeta 07 del CRM resume («su voto es urbano: 56 % de mujeres») y el
   análisis vive en candidato-360-electorado.html, que tiene sitio para las
   figuras y las cinco lecturas:

     01 sexo · 02 edad · 03 campo y ciudad · 04 familias políticas ·
     05 la votación que debería buscar

   Las cuentas las hace candidato-360-electorado.js, compartido con el CRM: si
   la página y la tarjeta dieran números distintos, ninguna serviría.

   Lo que se comprueba acá:
     · el perfil es el del CENSO de sus puestos, ponderado por sus votos, y se
       compara con el territorio entero;
     · sin el archivo de edad publicado la sección lo dice en vez de estimar;
     · las familias políticas resuelven coaliciones y movimientos regionales, y
       lo que queda sin línea sale con nombre propio;
     · el objetivo separa lo que ya tiene de lo que le falta y mezcla los dos
       perfiles, pesados por sus votos;
     · sin meta guardada, la página lo dice y no se rompe.

   Todo lo remoto va simulado: tres puestos, un municipio, cinco organizaciones.

     node tools/candidato-360/prueba-perfil.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const SP = process.env.SALIDA_PRUEBA || '/tmp';

/* Tres puestos de 1.000 personas: el municipio queda en 50 % de mujeres y
   33,3 % de censo rural (la zona 99). */
const fila = (code, barrio, mujeres, hombres) => { const r = new Array(16).fill(''); r[1] = code; r[7] = barrio; r[9] = '6.02'; r[10] = '-75.43'; r[13] = String(mujeres); r[14] = String(hombres); return r.join(';'); };
const PUESTOS = ['CABECERA', fila('011630101', 'CENTRO', 600, 400), fila('011630102', 'SAN CAYETANO', 400, 600), fila('011639901', 'LA MIEL', 500, 500)].join('\n');
/* Sus votos: 800 en Centro (60 % mujeres) y 200 en San Cayetano (40 %), nada
   en el puesto rural → 56 % de mujeres y 0 % rural. */
const MESAS = { mesas: [
  { dep: '01', mun: '163', zon: '01', pue: '01', munNom: 'LA CEJA', v: 800 },
  { dep: '01', mun: '163', zon: '01', pue: '02', munNom: 'LA CEJA', v: 200 },
] };
/* La Asamblea 2023 del municipio: derecha 500, izquierda 300 (Pacto 200 +
   Renace 100, que es de la tabla medida), centro-derecha 100 (una coalición
   que se resuelve por sus partes) y centro-izquierda 100 de la ASI, que tiene
   familia como partido pero presta su aval: eso se advierte aparte. */
const ASAMBLEA = { key: '01', name: 'ANTIOQUIA', nivel: 'municipio', comunas: { '163': {
  name: 'LA CEJA', validos: 1000, votantes: 1800, potencial: 3000, mesas: 9,
  partidos: [['PARTIDO CENTRO DEMOCRÁTICO', 500], ['MOVIMIENTO POLÍTICO PACTO HISTÓRICO', 200], ['CAMBIO RADICAL - MIRA', 100], ['RENACE', 100], ['PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"', 100]],
} }, totals: { validos: 1000, potencial: 3000 } };
const MUNICIPIOS = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { mpio_cnmbr: 'LA CEJA', mun_elec: '163' }, geometry: null }] };
const CAMPANA = { corp: 'alcaldia', avales: 'firmas', espectro: 'd', departamento: '01', departamentoNombre: 'Antioquia', municipio: 'LA CEJA', meta: 5000 };
const VINCULO = { tipo: 'historial', candidato: { nombre: 'CARLOS MARIO BEDOYA MORENO', slugs: ['ALC2023-01-163-1'], partido: 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO' }, campana: CAMPANA };

async function abrir({ vinculo = VINCULO, acceso = true } = {}) {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 1200 } });
  const errores = []; p.on('pageerror', e => errores.push(e.message));
  const json = x => ({ status: 200, contentType: 'application/json', body: JSON.stringify(x) });
  await p.route('**', route => {
    const u = route.request().url();
    if (u.startsWith('file://')) return route.continue();
    if (u.includes('/c360/me')) return route.fulfill(json({ ok: true, acceso, fuente: 'plan', vinculo, email: 'a@b.co', plan: 'c360' }));
    if (u.includes('PUESTOS_GEOREF.csv')) return route.fulfill({ status: 200, contentType: 'text/csv', body: PUESTOS });
    if (u.includes('CENSO_EDAD_PUESTO.json')) return route.fulfill({ status: 404, body: '' });
    if (u.includes('asamblea-2023/dep/01.json')) return route.fulfill(json(ASAMBLEA));
    if (u.includes('Departamentos-mps/01.json')) return route.fulfill(json(MUNICIPIOS));
    if (u.includes('alcaldia-2023/ALC2023-01-163-1.json')) return route.fulfill(json(MESAS));
    return route.fulfill({ status: 404, body: '' });
  });
  await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'a@b.co' })); });
  await p.goto('file://' + process.cwd() + '/candidato-360-electorado.html');
  await p.waitForFunction(() => !document.getElementById('elecAnalisis').classList.contains('hidden') || !document.getElementById('panelMuro').classList.contains('hidden'), null, { timeout: 15000 }).catch(() => {});
  return { b, p, errores };
}

const r = {};
{
  const { b, p, errores } = await abrir();
  r.errores = errores;
  r.texto = (await p.textContent('#elecAnalisis')).replace(/\s+/g, ' ');
  r.nota = (await p.textContent('#elecNota')).replace(/\s+/g, ' ');
  r.secciones = await p.$$eval('#elecAnalisis .panel-num', n => n.map(x => x.textContent.trim()));
  r.figuras = await p.$$eval('#elecAnalisis .figura svg use', n => n.map(x => x.getAttribute('href')));
  r.familias = await p.$$eval('#elecAnalisis .familia-fila', n => n.map(x => x.textContent.replace(/\s+/g, ' ').trim()));
  /* Las mismas cuentas que hace el CRM, pedidas directamente al módulo. */
  r.cuentas = await p.evaluate(async () => {
    const E = window.C360Electorado;
    const perfil = await E.perfil([{ dep: '01', mun: '163', zon: '01', pue: '01', v: 800 }, { dep: '01', mun: '163', zon: '01', pue: '02', v: 200 }]);
    return { mujeres: perfil.mujeres, rural: perfil.rural, mujeresMunicipio: perfil.mujeresMunicipio, ruralMunicipio: perfil.ruralMunicipio,
      objetivo: E.objetivo(perfil, 5000, { mismoTerritorio: true }),
      urlAlcaldia: E.urlCandidatura('ALC2023-01-163-1'), urlConcejo: E.urlCandidatura('CONC2023-16-1-1-1'), urlCongreso: E.urlCandidatura('CON2022-C-11-1') };
  });
  await p.screenshot({ path: SP + '/electorado.png', fullPage: true });
  await b.close();
}
{ /* Sin meta guardada la página lo dice, no se cae. */
  const { b, p } = await abrir({ vinculo: { ...VINCULO, campana: { ...CAMPANA, meta: 0 } } });
  r.sinMeta = (await p.textContent('#elecAnalisis')).replace(/\s+/g, ' ');
  await b.close();
}
{ /* Sin candidatura abierta, el panel pide abrirla en vez de mostrarse vacío. */
  const { b, p } = await abrir({ vinculo: null });
  r.sinVinculo = (await p.textContent('#panelMuro')).replace(/\s+/g, ' ');
  await b.close();
}

const casi = (a, b, t = .002) => Math.abs(a - b) < t;
const pruebas = [
  ['la página arma las cinco lecturas', r.secciones.join(' | ') === '01 · Sexo | 02 · Edad | 03 · Campo y ciudad | 04 · Familias políticas | 05 · La votación que debería buscar'],
  ['el perfil es el del censo de sus puestos, ponderado por sus votos', casi(r.cuentas.mujeres, .56) && casi(r.cuentas.rural, 0)],
  ['y se compara con el territorio entero', casi(r.cuentas.mujeresMunicipio, .5) && casi(r.cuentas.ruralMunicipio, 1 / 3)],
  ['el sexo sale con sus dos figuras', r.figuras.includes('#ico-mujer') && r.figuras.includes('#ico-hombre') && /56,0 %/.test(r.texto)],
  ['campo y ciudad también', r.figuras.includes('#ico-ciudad') && r.figuras.includes('#ico-campo') && /33,3 %/.test(r.texto)],
  ['sin el archivo de edad publicado, se dice en vez de estimar', /Todavía no/.test(r.texto) && /no está publicado/.test(r.texto)],
  ['las familias resuelven coalición y movimiento regional', r.familias.some(f => /Derecha.*su familia.*50,0 %/.test(f)) && r.familias.some(f => /Centro-derecha 10,0 %/.test(f)) && r.familias.some(f => /Izquierda.*su aval anterior.*30,0 %/.test(f))],
  ['los étnicos entran por la línea del partido', r.familias.some(f => /Centro-izquierda 10,0 %/.test(f))],
  ['pero se advierte que ese aval se presta', /Aval prestado: Partido Alianza Social Independiente "ASI" \(100, Centro-izquierda\)/.test(r.texto) && /35 %/.test(r.texto)],
  ['el objetivo separa lo que tiene de lo que le falta', r.cuentas.objetivo.base === 1000 && r.cuentas.objetivo.faltan === 4000 && /4\.000\s*votos por conseguir/.test(r.texto)],
  ['y mezcla los dos perfiles pesados por sus votos', casi(r.cuentas.objetivo.mujeres, (1000 * .56 + 4000 * .5) / 5000) && casi(r.cuentas.objetivo.rural, (4000 / 3) / 5000)],
  ['dice si su familia política alcanza para lo que falta', /Derecha sumó 500 votos acá en 2023: no alcanza sola/.test(r.texto)],
  ['el JSON de cada candidatura se resuelve por el slug, sin bajar los índices', /alcaldia-2023\/ALC2023-01-163-1\.json$/.test(r.cuentas.urlAlcaldia) && /concejo-2023\//.test(r.cuentas.urlConcejo) && /congreso-2022\//.test(r.cuentas.urlCongreso)],
  ['la nota dice de dónde sale todo y qué parte cubre', /PUESTOS_GEOREF/.test(r.nota) && /Asamblea 2023/.test(r.nota) && /100,0 %/.test(r.nota)],
  ['sin meta guardada lo dice y no se rompe', /Falta la meta/.test(r.sinMeta) && /Sexo/.test(r.sinMeta)],
  ['sin candidatura abierta, el panel pide abrirla', /candidatura/.test(r.sinVinculo)],
  ['sin errores de JavaScript', r.errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
if (r.errores.length) console.log(r.errores.slice(0, 3));
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1).slice(0, 3000));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
