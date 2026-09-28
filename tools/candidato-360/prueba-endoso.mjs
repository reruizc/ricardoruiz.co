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
  } catch (e) {
    ok(false, `real · no se pudo leer S3 (${e.message}); correr con --sin-red para solo la lógica`);
  }
}

console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en orden.');
process.exit(fallas ? 1 : 0);
