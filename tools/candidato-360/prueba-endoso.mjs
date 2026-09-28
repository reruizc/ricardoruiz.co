/* prueba-endoso.mjs — el motor del endoso de aliados (candidato-360-endoso.js).
   ------------------------------------------------------------------
   Dos partes:
   1. Casos sintéticos, sin red: una regla por caso (transferencia por puesto,
      misma jornada por mesa, mismo tarjetón, par saturado, sin territorio en
      común, recorte al territorio, tasa escrita, mediana, supuesto, solape).
   2. Casos reales de Bogotá contra S3, con las cifras FIJADAS. Salieron del
      código que vivía dentro de candidato-360.js antes de extraer el motor
      (fase 1 del plan, sep-2026) y se verificaron idénticas: si cambian, o
      cambió el motor o cambiaron los datos, y hay que saber cuál.
      `--sin-red` salta esta parte.

     node tools/candidato-360/prueba-endoso.mjs                                 */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const RAIZ = new URL('../../', import.meta.url);
const ctx = vm.createContext({ fetch: globalThis.fetch, console });
vm.runInContext(await readFile(new URL('candidato-360-endoso.js', RAIZ), 'utf8'), ctx);
const E = ctx.C360Endoso;

let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const cerca = (a, b, eps = 1e-9) => Math.abs(a - b) < eps;

/* ── 1. Sintéticos ─────────────────────────────────────────────────────── */
const M = (pue, mesa, v, extra = {}) => ({ dep: '16', mun: '001', zon: '01', pue, mesa, v, comNom: 'USAQUEN', pueNom: `P${pue}`, ...extra });
const DATOS = {
  aliado2019: [M('01', '001', 100), M('02', '001', 100)],
  apoyado2023: [M('01', '009', 60), M('02', '009', 300)],                     // otra mesa, mismo puesto
  mismaJornada: [M('01', '001', 40), M('02', '001', 500)],
  gigante: [M('01', '001', 900), M('02', '001', 900)],                        // lo supera en todas
  lejos: [{ dep: '01', mun: '001', zon: '01', pue: '01', mesa: '001', v: 800 }],
  conFuera: [M('01', '001', 70), { dep: '01', mun: '001', zon: '01', pue: '01', mesa: '001', v: 30 }],
};
const leer = async url => DATOS[url];
const C = (url, corp) => ({ slug: url, nombre: url, corp, dataUrl: url });
const A19 = C('aliado2019', 'JAL · SUBA · BOGOTÁ D.C. · 2019');

ok(E.clase(A19, C('x', 'CONCEJO · BOGOTÁ D.C. · 2023')) === 'transferencia', 'años distintos → transferencia');
ok(E.clase(C('a', 'JAL · SUBA · 2023'), C('b', 'CONCEJO · BOGOTÁ · 2023')) === 'cota', 'misma jornada, otro tarjetón → cota');
ok(E.clase(C('a', 'CONCEJO · BOGOTÁ · 2023'), C('b', 'CONCEJO · BOGOTÁ · 2023')) === 'mismo', 'mismo tarjetón → mismo');
ok(E.anio({ corp: 'SENADO', source: 'endoso' }) === 2026, 'la fuente endoso no trae año en corp: 2026');

let par = await E.medirPar({ ...A19, apoyo: C('apoyado2023', 'CONCEJO · BOGOTÁ D.C. · 2023') }, { mesasDe: leer });
ok(par.valida && cerca(par.tasa, (60 + 100) / 200), `transferencia compara por PUESTO aunque las mesas no coincidan (${(par.tasa * 100).toFixed(0)} %)`);
par = await E.medirPar({ ...C('aliado2019', 'JAL · SUBA · 2023'), apoyo: C('mismaJornada', 'CONCEJO · BOGOTÁ · 2023') }, { mesasDe: leer });
ok(par.valida && cerca(par.tasa, (40 + 100) / 200), `misma jornada compara por MESA (${(par.tasa * 100).toFixed(0)} %)`);
par = await E.medirPar({ ...C('aliado2019', 'CONCEJO · BOGOTÁ · 2023'), apoyo: C('gigante', 'CONCEJO · BOGOTÁ · 2023') }, { mesasDe: leer });
ok(!par.valida && par.clase === 'mismo', 'mismo tarjetón: no se mide');
par = await E.medirPar({ ...C('aliado2019', 'JAL · SUBA · 2023'), apoyo: C('gigante', 'ALCALDÍA · BOGOTÁ · 2023') }, { mesasDe: leer });
ok(!par.valida && cerca(par.tasa, 1), 'par saturado: da 100 % y se descarta');
par = await E.medirPar({ ...C('aliado2019', 'JAL · SUBA · 2023'), apoyo: C('lejos', 'CONCEJO · MEDELLÍN · 2023') }, { mesasDe: leer });
ok(!par.valida && /no compartieron/.test(par.motivo), 'sin departamento en común: no se mide');

const alcance = { tipo: 'municipio', departamento: '16', municipio: '1' };
const enAlcance = (m, a) => String(Number(m.dep)) === a.departamento && String(Number(m.mun)) === a.municipio;
/* Una tabla de retención de prueba: el motor recibe la suya para que estos
   casos no dependan de lo que salga de calibrar.mjs. [p25, mediana, p75, n] */
const RET = { jal: { 4: [.4, .6, .9, 90], 8: [.2, .5, .8, 60] }, concejo: { 4: [.5, .7, .95, 90] }, _todas: { 4: [.45, .65, .9, 500], 8: [.3, .55, .8, 300], 12: [.2, .45, .85, 100] } };
const base = { alcance, enAlcance, mesasDe: leer, retencion: RET };
let L = await E.evaluar([{ ...C('conFuera', 'JAL · SUBA · 2023'), manual: null }], { ...base, retencion: {} });
ok(L.filas[0].terr === 70 && L.filas[0].total === 100 && L.filas[0].fuente === 'supuesto' && L.total === 21, 'sin tabla de retención: recorte al territorio + supuesto del 30 % (70 × 30 % = 21)');
L = await E.evaluar([{ ...C('conFuera', 'JAL · SUBA · 2023'), manual: null }], base);
ok(L.filas[0].fuente === 'retencion' && L.bajo === 28 && L.total === 42 && L.alto === 63, `sin par: la retención de un edil a 4 años da el rango (${L.bajo} · ${L.total} · ${L.alto})`);
L = await E.evaluar([{ ...C('conFuera', 'JAL · SUBA · 2019'), manual: null }], base);
ok(L.filas[0].ret.medida === 8 && L.total === 35, 'una candidatura de 2019 llega a 2027 con 8 años de desgaste');
L = await E.evaluar([{ ...C('conFuera', 'JAL · SUBA · 2015'), manual: null }], base);
ok(L.filas[0].ret.propia === false && L.filas[0].ret.medida === 12, 'sin casos propios a 12 años: la de todas las corporaciones');
L = await E.evaluar([{ ...C('conFuera', 'PRESIDENCIA · 2022'), manual: null }], base);
ok(L.filas[0].ret.propia === false && L.filas[0].ret.medida === 4, 'presidencia no tiene quien repita: la de todas, a la distancia más cercana');
L = await E.evaluar([
  { ...C('aliado2019', 'JAL · SUBA · 2019'), apoyo: C('apoyado2023', 'CONCEJO · 2023') },
  { ...C('conFuera', 'JAL · SUBA · 2023'), manual: 50 },
  { ...C('mismaJornada', 'JAL · SUBA · 2023') },
], { ...base, propio: DATOS.aliado2019, areaDe: m => m.pueNom });
ok(L.filas.map(f => f.fuente).join() === 'medida,suya,retencion', 'orden de fuentes: medida → escrita → retención');
ok(L.filas[0].tasaBaja === .2 && L.filas[0].tasa === .5 && L.filas[0].tasaAlta === .8, 'con par medido (80 %) el rango lo acota la retención a 8 años: min(80 %, 20 · 50 · 80 %)');
ok(L.filas[1].estBajo === 35 && L.filas[1].estAlto === 35, 'la tasa escrita no tiene rango');
ok(L.total === 100 + 35 + Math.round(540 * .6) && L.bajo === 40 + 35 + Math.round(540 * .4) && L.alto === 160 + 35 + Math.round(540 * .9), `total, bajo y alto = Σ de cada aliado (${L.bajo} · ${L.total} · ${L.alto})`);
ok(cerca(L.filas[2].solape, (40 + 100) / 540), 'solape con el voto propio, por puesto');
ok(L.areas[0].nombre === 'P02', 'dónde se concentra: el área con más endoso primero');
ok(E.corpRetencion({ corp: 'CÁMARA · ANTIOQUIA · 2022' }) === 'camara' && E.corpRetencion({ corp: 'SENADO' }) === 'senado' && E.corpRetencion({ corp: 'CONSULTA · PACTO · 2022' }) === '', 'la corporación de la retención sale del corp');
{
  /* La mediana de las tasas medidas: con un número par, el promedio de las
     dos del medio (antes tomaba la menor). */
  const cuatro = await E.evaluar([0, 1].map(i => ({ ...C('aliado2019', 'JAL · SUBA · 2019'), slug: 'x' + i, apoyo: C(i ? 'mismaJornada' : 'apoyado2023', i ? 'CONCEJO · 2019' : 'CONCEJO · 2023') })), base);
  ok(cerca(cuatro.mediana, (.7 + .8) / 2), `mediana con dos medidas = promedio (${cuatro.mediana})`);
}

/* La regresión ecológica, con datos construidos para que la respuesta se
   sepa de antemano: el apoyado saca α + β · (participación del aliado) en
   cada puesto, así que α + β tiene que salir exacto. */
{
  const P = (zon, pue) => ({ dep: '16', mun: '001', zon, pue });
  const TA = {}, TB = {}, mA = [], mB = [];
  for (let i = 0; i < 40; i++) {
    const zon = i < 30 ? '01' : '02', pue = String(i).padStart(2, '0'), x = (i % 10) / 20;   /* participación del aliado: 0 a 45 % */
    const k = E.codigoPuesto(P(zon, pue)); TA[k] = [1000, 1100, 20]; TB[k] = [2000, 2200, 40];
    if (x && zon === '01') mA.push({ ...P(zon, pue), mesa: '1', v: x * 1000 });   /* el edil solo está en el tarjetón de la zona 01 */
    mB.push({ ...P(zon, pue), mesa: '1', v: (.1 + .5 * x) * 2000 });   /* α = 10 %, β = 50 % → τ = 60 % */
  }
  const leerM = async u => u === 'a' ? mA : mB, leerT = async n => n.startsWith('jal') ? TA : TB;
  const Ali = { slug: 'JAL2019-16-1-1-1-aaaaaa', corp: 'JAL · SUBA · 2019', dataUrl: 'a', apoyo: { slug: 'CONC2023-16-1-1-1', corp: 'CONCEJO · BOGOTÁ · 2023', dataUrl: 'b' } };
  const r = await E.regresion(Ali, { mesasDe: leerM, totalesDe: leerT });
  ok(r.valida && cerca(r.tau, .6, 1e-9) && cerca(r.alfa, .1, 1e-9) && r.error < 1e-6, `regresión: recupera α + β exacto (τ ${(r.tau * 100).toFixed(1)} %, α ${(r.alfa * 100).toFixed(1)} %)`);
  ok(r.n === 30, 'regresión: el edil solo cuenta en las zonas donde estaba en el tarjetón (30 de 40 puestos)');
  ok(E.eleccionDe({ slug: 'CON2022-C-16-1-1' }).escala === 'dep' && E.eleccionDe({ slug: 'CON2022-S-1-1' }).totales === 'senado-2022' && E.eleccionDe({ slug: 'CONC2019-5-1-1-1' }).totales === 'concejo-2019' && E.eleccionDe({ slug: 'PRES2022-1V-1-1' }) === null, 'regresión: cada candidatura encuentra sus totales (CONC es concejo y CON es Congreso)');
  ok((await E.regresion({ ...Ali, apoyo: { ...Ali.apoyo, slug: 'PRES2022-1V-1-1' } }, { mesasDe: leerM, totalesDe: leerT })).valida === false, 'regresión: sin totales de esa elección no se inventa');
  ok(await E.regresion({ ...Ali, apoyo: { ...Ali, apoyo: null } }, { mesasDe: leerM, totalesDe: leerT }) === null, 'regresión: el mismo tarjetón no se mide');
  const pocos = { ...Ali, apoyo: { ...Ali.apoyo } }; const TB2 = Object.fromEntries(Object.entries(TB).slice(0, 12));
  ok((await E.regresion(pocos, { mesasDe: leerM, totalesDe: async n => n.startsWith('jal') ? TA : TB2 })).valida === false, 'regresión: con menos de 20 puestos no se estima');
  const L4 = await E.evaluar([Ali], { alcance, enAlcance, mesasDe: leerM, totalesDe: leerT, retencion: RET });
  ok(L4.filas[0].fuente === 'regresion' && cerca(L4.filas[0].tasa, .5) && cerca(L4.filas[0].tasaBaja, .2), 'la regresión entra al rango acotada por la retención (60 % → 50 % a 8 años; piso 20 %)');
}

/* Sin contar dos veces (fase 5): la unión por puesto con números conocidos. */
{
  const M2 = (pue, v) => ({ dep: '16', mun: '001', zon: '01', pue, mesa: '1', v, pueNom: 'P' + pue, comNom: '01USAQUEN' });
  const D = { a: [M2('01', 300), M2('02', 200)], b: [M2('01', 300)], c: [M2('03', 100)] };
  const den = { [E.codigoPuesto(M2('01'))]: [1000, 1100, 10], [E.codigoPuesto(M2('02'))]: [1000, 1100, 10] };
  const al = u => ({ slug: u, nombre: u, corp: 'JAL · 2023', dataUrl: u, manual: 100 });
  const opts = { alcance, enAlcance, mesasDe: async u => D[u], totalesDe: async () => den, corpCampana: 'concejo', areaDe: m => m.pueNom };
  const U = await E.evaluar([al('a'), al('b'), al('c')], opts);
  const p1 = U.puestos.find(p => p.nombre === 'P01');
  ok(cerca(p1.total, 1000 * (1 - .7 * .7)) && p1.aliados === 2, `dos aliados de 300 en un puesto de 1.000 votantes: 510, no 600 (${p1.total})`);
  ok(U.total === 510 + 200 + 100 && U.suma.total === 900 && U.dobleConteo === 90, `el puesto de un solo aliado suma completo; el doble conteo evitado es 90 (${U.total} de ${U.suma.total})`);
  ok(U.sinDenominador.puestos === 0 && U.denominador === 'concejo-2023', 'el electorado sale de los válidos 2023 de la corporación de la campaña');
  ok(U.siSeRepiten === 300 + 200 + 100, 'si los votantes se repitieran en cada puesto, solo cuenta el aliado más fuerte de cada uno (600)');
  ok(cerca(Object.values(p1.porAliado).reduce((t, x) => t + x, 0), p1.total), 'lo de cada aliado en un puesto suma la unión (para el mapa)');
  ok(U.areas[0].nombre === 'P01' && U.areas[0].v === 510, 'dónde se concentra, ya sin doble conteo');
  const S = await E.evaluar([al('a'), al('b'), al('c')], { ...opts, totalesDe: async () => ({}) });
  ok(S.total === 900 && S.sinDenominador.puestos === 1, 'sin el electorado del puesto se suma, y se cuenta cuántos puestos quedaron así');
  const sol = E.solapes(U);
  ok(sol[0].i === 0 && sol[0].j === 1 && cerca(sol[0].coincidencia, 1) && sol.find(x => x.j === 2).coincidencia === 0, 'solape: el aliado b vive entero dentro de la huella de a; c no comparte puestos');
}

/* El líder de zona (fase 6): la candidatura que apoyó saca 10 % en su
   comuna y 30 % en los dos puestos del líder → 400 votos de más. */
{
  const TB = {}, mB = [], comuna = {};
  for (let i = 0; i < 40; i++) {
    const zon = i < 20 ? '01' : '02', pue = String(i).padStart(2, '0'), k = E.codigoPuesto({ dep: '16', mun: '001', zon, pue });
    TB[k] = [1000, 1100, 10]; comuna[k] = zon;
    mB.push({ dep: '16', mun: '001', zon, pue, mesa: '1', v: (i === 0 || i === 1) ? 300 : 100 });
  }
  const zona = ['00', '01'].map(pue => ({ code: E.codigoPuesto({ dep: '16', mun: '001', zon: '01', pue }), nombre: 'Colegio ' + pue, comNom: 'USAQUEN' }));
  const apoyo = { slug: 'CONC2023-16-1-9-9', nombre: 'APOYADO', corp: 'CONCEJO · BOGOTÁ · 2023', dataUrl: 'B' };
  const lider = { tipo: 'lider', id: 'l1', nombre: 'Doña Rosa', zona, apoyo, declarado: null, manual: null };
  const o = { mesasDe: async () => mB, totalesDe: async () => TB, comunaDe: k => comuna[k] };
  const m = await E.medirLider(lider, o);
  ok(m.valida && cerca(m.efecto, 400) && m.base === 'comuna' && m.nComparacion === 18 && cerca(m.error, 0), `líder: 600 votos donde se esperaban 200 → efecto de 400, comparando con su comuna (${m.efecto})`);
  ok((await E.medirLider(lider, { ...o, comunaDe: null })).base === 'municipio', 'líder: sin comunas, se compara con el municipio');
  const L6 = await E.evaluar([lider], { alcance, enAlcance, ...o, retencion: RET, corpCampana: 'concejo' });
  const f6 = L6.filas[0];
  ok(f6.fuente === 'lider' && f6.terr === 400 && f6.est === 260 && f6.estAlto === 360 && f6.ret.medida === 4, `líder: el efecto se desgasta como cualquier base a 4 años (${f6.estBajo} · ${f6.est} · ${f6.estAlto})`);
  ok(L6.puestos.length === 2 && cerca(L6.puestos.reduce((t, p) => t + p.total, 0), 260), 'líder: su endoso se reparte en sus puestos y pasa por la unión');
  const dec = { ...lider, apoyo: null, declarado: 500 };
  const L7 = await E.evaluar([dec], { alcance, enAlcance, ...o, retencion: RET, corpCampana: 'concejo' });
  ok(L7.filas[0].fuente === 'declarado' && L7.total === 500 && cerca(L7.filas[0].declaradoParte, .25), 'líder que solo declara 500: entra rotulado y es el 25 % de los que votaron en sus puestos');
  const L8 = await E.evaluar([{ ...lider, apoyo: null }], { alcance, enAlcance, ...o, retencion: RET });
  ok(L8.filas[0].fuente === 'sin-dato' && L8.total === 0, 'líder sin apoyo ni cifra: no se inventa nada');
  const mB2 = mB.map(x => ({ ...x, v: 100 }));
  const L9 = await E.evaluar([lider], { alcance, enAlcance, ...o, mesasDe: async () => mB2, retencion: RET });
  ok(L9.filas[0].fuente === 'lider' && L9.filas[0].lider.efecto === 0 && L9.total === 0, 'líder medido sin efecto: cero, y se dice');
}

/* El territorio desde la campaña guardada (lo que usa el panel). */
const codigo = async (dep, nombre) => ({ 'BOGOTÁ, D.C.': '001', 'LA CEJA': '021' }[nombre] || '');
let al = await E.alcanceDe({ campana: { corp: 'asamblea', ruta: 'other', departamento: '01', departamentoNombre: 'Antioquia' } });
ok(al.tipo === 'departamento' && al.departamento === '1', 'asamblea → departamento, sin ceros a la izquierda');
al = await E.alcanceDe({ campana: { corp: 'jal', ruta: 'other', departamento: '16', municipio: 'BOGOTÁ, D.C.', localidad: 'SUBA' }, codigoMunicipio: codigo });
ok(al.tipo === 'localidad' && al.municipio === '1' && al.nombre === 'SUBA', 'JAL → localidad, municipio por código electoral');
al = await E.alcanceDe({ campana: { corp: 'concejo', ruta: 'other', departamento: '01', municipio: 'LA CEJA' }, codigoMunicipio: codigo });
ok(al.tipo === 'municipio' && al.municipio === '21', 'concejo → municipio por código');
al = await E.alcanceDe({ campana: { corp: 'concejo', ruta: 'same' }, corpHistorica: 'jal', mesasPropias: [M('01', '001', 5, { comNom: '11SUBA' }), M('02', '001', 50, { comNom: '13TEUSAQUILLO' })] });
ok(al.tipo === 'municipio' && al.departamento === '16' && al.municipio === '1', '«la misma corporación» → el municipio donde tiene más votos');
al = await E.alcanceDe({ campana: {}, corpHistorica: 'jal', mesasPropias: [M('01', '001', 5, { comNom: '11SUBA' }), M('02', '001', 50, { comNom: '13TEUSAQUILLO' })] });
ok(al.tipo === 'localidad' && al.localidad === '13TEUSAQUILLO' && al.nombre === 'TEUSAQUILLO', 'JAL sin campaña → la localidad donde tiene más votos');
ok(await E.alcanceDe({ campana: {} }) === null, 'sin campaña ni votos → sin recorte');
ok(E.enAlcance(M('01', '001', 1, { comNom: '13TEUSAQUILLO' }), { tipo: 'localidad', departamento: '16', municipio: '1', localidad: 'TEUSAQUILLO' }) && !E.enAlcance(M('01', '001', 1, { comNom: '11SUBA' }), { tipo: 'localidad', departamento: '16', municipio: '1', localidad: 'TEUSAQUILLO' }), 'recorte por localidad, por el nombre pelado');
ok(E.codigoPuesto({ dep: '1', mun: '1', zon: '99', pue: 'a1' }) === '0100199A1', 'código de puesto: la letra se conserva');
ok(E.candidaturaId({ tipo: 'nuevo', nuevo: { nombre: 'Ana Pérez' } }) === 'nuevo-ANAPEREZ' && E.candidaturaId({ tipo: 'historial', candidato: { id: 'persona-x' } }) === 'persona-x', 'la llave de la lista es la misma del CRM');
const pp = E.porPuesto(L);
ok(Math.abs(pp.reduce((s, p) => s + p.total, 0) - L.filas.reduce((s, f) => s + f.terr * f.tasa, 0)) < 1e-6, 'por puesto: reparte exactamente lo estimado');

/* ⚠️ El motor lleva un puerto de mesaEnAlcance del CRM: si alguien cambia una
   sin la otra, la tarjeta y el panel dejan de coincidir. Se comparan las dos
   sobre mesas de verdad y varios alcances. */
{
  const src = await readFile(new URL('candidato-360.js', RAIZ), 'utf8');
  const trozo = nombre => { const i = src.indexOf(`function ${nombre}(`); let d = 0; for (let k = src.indexOf('{', i); k < src.length; k++) { if (src[k] === '{') d++; else if (src[k] === '}' && !--d) return src.slice(i, k + 1); } };
  const crm = vm.createContext({});
  vm.runInContext(`const COM_NOM_NULO = new Set(['NACIONAL', 'NULL', 'SN', '']);\n${['normalizedText', 'nombreLocal', 'nombreLocalidad', 'cortoLocal', 'mesaEnAlcance'].map(trozo).join('\n')}\nglobalThis.f = mesaEnAlcance;`, crm);
  globalThis.__mesasPrueba = [M('01', '001', 1, { comNom: '13LOCALIDAD 13 TEUSAQUILLO' }), M('01', '001', 1, { comNom: 'NACIONAL' }), M('02', '001', 1, { comNom: '14COMUNA 14 EL POBLADO', dep: '01', mun: '001' }), { dep: '05', mun: '001', munNom: 'CARTAGENA', depNom: 'BOLÍVAR', v: 1 }];
  const alcances = [{ tipo: 'departamento', departamento: '16' }, { tipo: 'departamento', departamentoNombre: 'BOLIVAR' }, { tipo: 'municipio', departamento: '5', municipio: '1' }, { tipo: 'municipio', departamento: '5', municipio: '', municipioNombre: 'CARTAGENA' }, { tipo: 'localidad', departamento: '16', municipio: '1', localidad: 'TEUSAQUILLO' }, { tipo: 'localidad', departamento: '1', municipio: '1', localidad: 'EL POBLADO' }];
  let distintos = 0;
  for (const a of alcances) for (const m of globalThis.__mesasPrueba) if (crm.f(m, a) !== E.enAlcance(m, a)) distintos++;
  globalThis.__crmEnAlcance = crm.f;
  ok(distintos === 0, `el recorte del motor es el mismo del CRM (${alcances.length * globalThis.__mesasPrueba.length} casos)`);
}

/* ── 2. Reales (S3) ────────────────────────────────────────────────────── */
if (!process.argv.includes('--sin-red')) {
  const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const R = (dir, slug, corp) => ({ slug, nombre: slug, corp, dataUrl: `${S3}/${dir}/${slug}.json` });
  const ROJAS = R('jal-2019', 'JAL2019-16-1-4-81-853b56', 'JAL · SUBA · BOGOTÁ D.C. · 2019');
  const BAENA = R('concejo-2023', 'CONC2023-16-1-7751-1', 'CONCEJO · BOGOTÁ D.C. · 2023');
  const RAMIREZ = R('jal-2023', 'JAL2023-16-1-7523-81-714c42', 'JAL · SUBA · BOGOTÁ D.C. · 2023');
  const ABIS = R('concejo-2023', 'CONC2023-16-1-1-1', 'CONCEJO · BOGOTÁ D.C. · 2023');
  const GALAN = R('alcaldia-2023', 'ALC2023-16-1-19-5', 'ALCALDÍA · BOGOTÁ D.C. · 2023');
  const FORERO = R('concejo-2023', 'CONC2023-16-1-7457-7', 'CONCEJO · BOGOTÁ D.C. · 2023');
  const SEPUL = R('jal-2023', 'JAL2023-16-1-11-81-9c5768', 'JAL · SUBA · BOGOTÁ D.C. · 2023');
  const BRICENO = R('concejo-2023', 'CONC2023-16-1-11-45', 'CONCEJO · BOGOTÁ D.C. · 2023');
  try {
    const propio = await E.mesas(FORERO.dataUrl);
    const Lr = await E.evaluar([
      { ...ROJAS, apoyo: BAENA }, { ...RAMIREZ, apoyo: BAENA }, { ...ABIS, apoyo: GALAN },
      { ...FORERO, apoyo: ABIS }, { ...SEPUL, manual: 12 }, { ...BRICENO },
    ], { alcance: { tipo: 'municipio', departamento: '16', municipio: '1' }, enAlcance, propio, corpCampana: 'concejo' });
    const f = Lr.filas;
    ok(Lr.bajo === 67581 && Lr.total === 115331 && Lr.alto === 164590 && Lr.suma.total === 116819 && Lr.dobleConteo === 1488, `real · sin doble conteo: entre 67.581 y 164.590, punto medio 115.331 (sumados eran 116.819) (${Lr.bajo} · ${Lr.total} · ${Lr.alto})`);
    ok(Lr.denominador === 'concejo-2023' && Lr.sinDenominador.puestos === 0 && Lr.puestos.length === 950, 'real · el electorado de los 950 puestos sale del Concejo 2023');
    const sol = E.solapes(Lr);
    ok(sol[0].i === 1 && sol[0].j === 4 && Math.abs(sol[0].coincidencia - .941) < .001, 'real · los dos ediles de Suba 2023 son el par que más se pisa (94 %)');
    ok(f[0].fuente === 'regresion' && f[0].reg.n === 86 && f[0].estAlto === 8117 && f[0].est === 5670, 'real · JAL Suba 2019 → Concejo 2023: la regresión (89 %) queda acotada por la retención de un edil a 8 años; techo Σ min');
    ok(f[1].fuente === 'regresion' && Math.abs(f[1].reg.tau - .425) < .001 && f[1].est === 5168 && f[1].estAlto === 8291, 'real · JAL Suba 2023 → Concejo 2023: la regresión da 42,5 % (Σ min decía 68 %)');
    ok(!f[2].par.valida && f[2].fuente === 'regresion' && Math.abs(f[2].reg.tau - .377) < .001 && f[2].reg.alfa > f[2].reg.tau, 'real · concejal → Galán: Σ min saturado, pero la regresión sí mide (38 %, y el resto de Bogotá votó más por Galán que sus votantes)');
    ok(!f[3].par.valida && f[3].par.clase === 'mismo', 'real · concejal → concejal: mismo tarjetón');
    ok(f[4].fuente === 'suya' && f[4].est === 1273 && f[4].estBajo === 1273, 'real · tasa escrita 12 % → 1.273, sin rango');
    const suba = { tipo: 'localidad', departamento: '16', municipio: '1', localidad: 'SUBA' }, reales = (await E.mesas(BRICENO.dataUrl)).concat(propio);
    ok(reales.every(m => globalThis.__crmEnAlcance(m, suba) === E.enAlcance(m, suba)), `real · recorte a Suba idéntico al del CRM en ${reales.length.toLocaleString('es-CO')} mesas`);
    const Ls = await E.evaluar([{ ...BRICENO }], { alcance: suba, enAlcance: E.enAlcance, mesasDe: E.mesas });
    ok(Ls.filas[0].terr === 11237, `real · el concejal Briceño tiene 11.237 votos en Suba (${Ls.filas[0].terr})`);
  } catch (e) {
    ok(false, `real · no se pudo leer S3 (${e.message}); correr con --sin-red para solo la lógica`);
  }
}

console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en orden.');
process.exit(fallas ? 1 : 0);
