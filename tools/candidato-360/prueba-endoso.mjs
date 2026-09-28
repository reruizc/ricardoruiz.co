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
let L = await E.evaluar([{ ...C('conFuera', 'JAL · SUBA · 2023'), manual: null }], { alcance, enAlcance, mesasDe: leer });
ok(L.filas[0].terr === 70 && L.filas[0].total === 100 && L.filas[0].fuente === 'supuesto' && L.total === 21, 'recorte al territorio + supuesto del 30 % (70 × 30 % = 21)');
L = await E.evaluar([
  { ...C('aliado2019', 'JAL · SUBA · 2019'), apoyo: C('apoyado2023', 'CONCEJO · 2023') },
  { ...C('conFuera', 'JAL · SUBA · 2023'), manual: 50 },
  { ...C('mismaJornada', 'JAL · SUBA · 2023') },
], { alcance, enAlcance, mesasDe: leer, propio: DATOS.aliado2019, areaDe: m => m.pueNom });
ok(L.filas.map(f => f.fuente).join() === 'medida,suya,mediana', 'orden de fuentes: medida → escrita → mediana');
ok(L.total === Math.round(200 * .8) + 35 + Math.round(540 * .8), `total = Σ estimados (${L.total})`);
ok(cerca(L.filas[2].solape, (40 + 100) / 540), 'solape con el voto propio, por puesto');
ok(L.areas[0].nombre === 'P02', 'dónde se concentra: el área con más endoso primero');

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
    ], { alcance: { tipo: 'municipio', departamento: '16', municipio: '1' }, enAlcance, propio });
    const f = Lr.filas;
    ok(Lr.total === 135894 && Lr.techo === 207208, `real · total 135.894 de 207.208 (${Lr.total} de ${Lr.techo})`);
    ok(f[0].fuente === 'medida' && f[0].par.clase === 'transferencia' && f[0].est === 8117, 'real · JAL Suba 2019 → Concejo 2023: transferencia medida, 8.117');
    ok(f[1].fuente === 'medida' && f[1].par.clase === 'cota' && f[1].est === 8291, 'real · JAL Suba 2023 → Concejo 2023: cota medida, 8.291');
    ok(!f[2].par.valida && f[2].par.clase === 'cota' && f[2].fuente === 'mediana', 'real · concejal → Galán: saturado, cae a la mediana');
    ok(!f[3].par.valida && f[3].par.clase === 'mismo', 'real · concejal → concejal: mismo tarjetón');
    ok(f[4].fuente === 'suya' && f[4].est === 1273, 'real · tasa escrita 12 % → 1.273');
    ok(cerca(Lr.mediana, f[1].par.tasa), 'real · la mediana de dos medidas es la menor (convención del motor)');
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
