/* prueba-estrategia.mjs — el motor de estrategia (candidato-360-estrategia.js).
   ------------------------------------------------------------------
   Dos partes:
   1. Sin red: el banco (íntegro, sin nada del caso concreto) y una regla por
      caso del motor (fase, cuadrantes, figura o barrio, competencia en la
      lista, orden de los principios, acciones de la fase).
   2. Dos candidaturas reales de Bogotá contra S3, descritas por su papel:
        · un concejal «figura» con arraigo bajo (Concejo 2023, ~11.900 votos);
        · una edilesa de barrio (JAL de Barrios Unidos 2023, 709 votos; la
          misma de la prueba de contendientes).
      Se FIJAN el orden de los ocho principios y la tabla de territorio. Si
      cambian, cambió el motor, el banco o los datos, y hay que saber cuál.
      `--sin-red` salta esta parte.

     node tools/candidato-360/prueba-estrategia.mjs                           */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const RAIZ = new URL('../../', import.meta.url);
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
const banco = JSON.parse(await readFile(new URL('candidato-360-data/estrategia-banco.json', RAIZ), 'utf8'));
const arraigos = JSON.parse(await readFile(new URL('candidato-360-data/arraigo-concejo-bogota-2023.json', RAIZ), 'utf8'));

/* Un contexto con lo que el CRM carga: la lectura de arquetipos pide el
   diccionario puesto → barrio con un <script>; aquí se ejecuta del disco. */
const almacen = new Map();
const ctx = vm.createContext({
  fetch: (u, o) => globalThis.fetch(u, o), console: { log: console.log, warn: () => {}, error: console.error },
  localStorage: { getItem: k => almacen.get(k) ?? null, setItem: (k, v) => almacen.set(k, String(v)) },
  RRData: { publicUrl: p => `${S3.replace(/\/congreso-2026\/output$/, '')}/${p}` },
  C360Electorado: { codigoMunicipio: async () => '001', rotar90: g => g, municipioMayoritario: () => '16001' },
});
ctx.window = ctx;
ctx.document = {
  createElement: () => ({}),
  head: { appendChild: s => { readFile(new URL(s.src.split('?')[0], RAIZ), 'utf8').then(t => { vm.runInContext(t, ctx, { filename: s.src }); s.onload(); }).catch(e => s.onerror(e)); } },
};
{
  const aux = vm.createContext({ console: { log() {}, warn() {}, error() {} }, fetch: () => Promise.reject(new Error('sin red')), RRData: ctx.RRData });
  aux.window = aux;
  vm.runInContext(await readFile(new URL('candidato-360-electorado.js', RAIZ), 'utf8'), aux, { filename: 'candidato-360-electorado.js' });
  ctx.C360Electorado.urlCandidatura = aux.C360Electorado.urlCandidatura;
}
for (const f of ['partidos-bloques.js', 'cand-index.js', 'legislativo-electos.js', 'vote-target.js', 'candidato-360-saliencia.js', 'candidato-360-endoso.js', 'candidato-360-diad.js', 'candidato-360-contendientes.js', 'candidato-360-arq-lectura.js', 'candidato-360-estrategia.js'])
  vm.runInContext(await readFile(new URL(f, RAIZ), 'utf8'), ctx, { filename: f });
const E = ctx.C360Estrategia, A = ctx.C360ArqLectura, K = ctx.C360Contendientes, EN = ctx.C360Endoso, VT = ctx.VoteTarget;

let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/* ── 1a. El banco ──────────────────────────────────────────────────────── */
const texto = JSON.stringify(banco);
/* Los términos del caso viven fuera del repo (son el nombre del cliente). */
const prohibido = await readFile(new URL('Bases de datos/candidato-360/estrategia-prohibido.txt', RAIZ), 'utf8').then(t => t.split('\n').map(s => s.trim()).filter(Boolean)).catch(() => null);
if (prohibido) ok(!prohibido.some(t => texto.toLowerCase().includes(t.toLowerCase())), 'el banco no trae nada del caso concreto (ni el nombre ni sus líneas «Para …»)');
else console.log('· sin la lista de términos del caso (vive fuera del repo): se salta esa comprobación');
ok(!banco.fichas.some(f => Object.values(f.modula || {}).some(v => /^Para /.test(v)) || (f.notas || []).some(n => /^Para /.test(n))), 'ninguna línea «Para …» del caso pasa a las fichas');
ok(banco.principios.length === 8 && banco.principios.every((p, i) => p.id === `A${i + 1}`), 'ocho principios, A1 a A8');
const ids = new Set(banco.fichas.map(f => f.id));
ok(banco.fichas.filter(f => f.nivel === 'tronco').length === 25 && banco.fichas.filter(f => f.nivel === 'rama').length === 14, `25 fichas de tronco y 14 de rama (${banco.fichas.length})`);
ok(banco.principios.every(p => p.fichas.every(f => ids.has(f))) && banco.acciones.every(a => a.fichas.every(f => ids.has(f))) && Object.values(banco.cuadrantes).every(c => c.fichas.every(f => ids.has(f))), 'toda ficha citada por un principio, una acción o un cuadrante existe');
ok(!banco.fichas.some(f => f.id.startsWith('N3')) && !banco.principios.some(p => p.fichas.some(f => f.startsWith('N3'))), 'el Nivel 3 (el caso) no pasa al banco');
ok(Object.keys(banco.matriz).length === 11 && Object.values(banco.matriz).every(f => Object.keys(f).length === 8 && Object.values(f).every(v => [-1, 0, 1, 2].includes(v))), 'matriz de 11 arquetipos × 8 principios, en 2 · 1 · 0 · −1');
ok(banco.matriz.CIM.A1 === 2 && banco.matriz.CIM.A5 === -1 && banco.matriz.PVP.A5 === 2 && banco.matriz.PVP.A7 === -1 && banco.matriz.CAS.A4 === -1, 'celdas de control: CIM A1 central y A5 riesgo · PVP A5 central y A7 riesgo · CAS A4 riesgo');
ok(banco.fichas.every(f => f.refs.every(r => !r.doi || /^https:\/\/doi\.org\/10\./.test(r.doi))), 'cada DOI es un enlace a doi.org');
ok(banco.fichas.find(f => f.id === 'T13').modula.PVP === 'principio central: ya lo prefiere, no sale.', 'la modulación por arquetipo pasa tal cual (T13 · PVP)');
ok(banco.fichas.find(f => f.id === 'T1').modula.CAS.includes('un titular con muchos años en el cargo'), 'la línea del tronco que hablaba del caso quedó en general (T1 · CAS)');

/* ── 1b. Fase ──────────────────────────────────────────────────────────── */
ok(E.fase(banco, '2026-10-19').id === 'posicionamiento' && E.fase(banco, '2026-10-19').proximo.id === 'cedulas' && E.fase(banco, '2026-10-19').proximo.dias === 12, 'el 19-oct-2026 es posicionamiento y faltan 12 días para la inscripción de cédulas');
ok(E.fase(banco, '2027-03-01').id === 'precampana' && E.fase(banco, '2027-07-31').id === 'campana' && E.fase(banco, '2027-10-25').id === 'diad' && E.fase(banco, '2027-11-02').id === 'despues', 'precampaña desde marzo · campaña con la propaganda (31-jul) · Día D la última semana · después');
ok(E.fase(banco, '2027-10-24').eleccion.dias === 7, 'a una semana de la elección dice 7 días');
ok(E.hoyISO(new Date('2027-03-01T03:00:00Z')) === '2027-02-28', 'la fecha se lee en hora de Bogotá (las 10 p. m. del 28 de febrero siguen siendo febrero)');

/* ── 1c. Cuadrantes ────────────────────────────────────────────────────── */
const q = (o, med = .2) => E.cuadrante({ participacion: .55, participacionRef: .55, ...o }, med);
ok(q({ territorio: .4, ratio: 1.3 }) === 'retener' && q({ territorio: .05, ratio: 1.3 }) === 'retener-crecer' && q({ territorio: .4, ratio: .9 }) === 'conocer' && q({ territorio: .05, ratio: .9 }) === 'no-gastar', 'los cuatro cuadrantes: retener · retener y crecer · hacerse conocer · no gastar');
ok(q({ territorio: .05, ratio: 1.3, participacion: .46 }) === 'movilizar' && q({ territorio: .4, ratio: .9, participacion: .5 }) === 'movilizar', 'baja participación (4 pp o más por debajo) y afín o grande: movilizar');
ok(q({ territorio: .05, ratio: .9, participacion: .46 }) === 'no-gastar', 'baja participación, chico y sin afinidad: no gastar (movilizarlo ayuda a otro)');
ok(q({ territorio: .4, ratio: 1.04 }) === 'conocer' && q({ territorio: .4, ratio: 1.05 }) === 'retener', 'afinidad alta desde ×1,05, el umbral del panel 05');
ok(E.cuadrante({ territorio: .4, ratio: null }, .2) === null, 'sin votos propios no hay afinidad medida: sin cuadrante');

/* ── 1d. Figura o barrio ───────────────────────────────────────────────── */
ok(E.figura({ arraigo: { valor: .07, referencia: .142 } }).lectura === 'figura' && E.figura({ arraigo: { valor: .2, referencia: .142 } }).lectura === 'barrio' && E.figura({ arraigo: { valor: .14, referencia: .142 } }).lectura === 'mixto', 'figura bajo ×0,75 del arraigo de la ciudad · barrio sobre ×1,25 · mixto entre los dos');
ok(E.figura({ arraigo: null, corp: 'jal' }).lectura === 'barrio' && E.figura({ arraigo: null, corp: 'jal' }).oficio, 'JAL sin arraigo medido: barrio, rotulado como criterio de oficio');
ok(E.figura({ arraigo: null, corp: 'alcaldia' }).lectura === 'sin-medida', 'sin arraigo medido y fuera de JAL: no se inclina');
ok(E.arraigoDe(arraigos, ['X', 'CONC2023-16-1-5443-2']).valor === .07, 'el arraigo se busca por slug en todo el historial');
ok(!JSON.stringify(arraigos).match(/[A-Z]{3,} [A-Z]{3,}/), 'el archivo de arraigo no trae nombres, solo slugs');

/* ── 1e. Competencia en la lista ───────────────────────────────────────── */
const filas = [{ nombre: 'A', votos: 900, puesto: 1, elegido: true }, { nombre: 'B', votos: 600, puesto: 2, elegido: true }, { nombre: 'U', votos: 500, puesto: 3, elegido: false, usted: true }, { nombre: 'C', votos: 100, puesto: 4, elegido: false }];
const ca = E.competencia({ estado: 'abierta', lista: 'P', k: 2, filas, usted: filas[2], ultimo: filas[1], distancia: 100 }, [{ nombre: 'B', partido: 'P', nivel: 'alta', votos: 600 }, { nombre: 'Z', partido: 'Q', nivel: 'alta', votos: 900 }]);
ok(ca.principal.nombre === 'B' && ca.presion.length === 1 && ca.presion[0].nombre === 'B', 'lista abierta, fuera de la curul: el rival principal es el de arriba más cercano, y la presión es solo de su lista');
const fE = filas.map(f => f.nombre === 'U' ? { ...f, votos: 700, puesto: 2, elegido: true } : f.nombre === 'B' ? { ...f, puesto: 3, elegido: false } : f);
ok(E.competencia({ estado: 'abierta', lista: 'P', k: 2, filas: fE, usted: fE[2], ultimo: fE[2], distancia: null }).principal.nombre === 'B', 'si ya entra, el rival principal es el de abajo más cercano');
ok(E.competencia({ estado: 'cerrada', lista: 'P', k: 3 }).texto.startsWith('Lista cerrada') && E.competencia(null).estado === 'sin-dato', 'lista cerrada y sin dato se dicen distinto');

/* ── 1f. Principios y acciones con arquetipos sintéticos ───────────────── */
const arq = (codigo, share, territorio, ratio) => ({ codigo, id: codigo, nombre: codigo, share, territorio, ratio });
const solo = c => E.principios(banco, [arq(c, 1, 1, 1)]).map(p => p.id);
ok(igual(solo('PVP').slice(0, 2), ['A5', 'A6']) && solo('PVP').slice(-3).sort().join() === 'A1,A7,A8', 'un territorio todo PVP: movilizar y datos primero; posicionamiento, legislativo y digital al final');
const mitad = E.principios(banco, [arq('CMN', .5, .5, 1), arq('PVP', .5, .5, 1)]);
ok(igual(mitad.slice(0, 2).map(p => [p.id, p.puntaje]), [['A5', 1], ['A6', 1]]), 'mitad CMN, mitad PVP: A5 y A6 empatan arriba y el empate se rompe por el id, siempre igual');
const conAfin = E.principios(banco, [arq('CMN', .4, .5, .8), arq('CIM', .1, .05, 2)]);
const sinAfin = E.principios(banco, [arq('CMN', .4, .5, 1), arq('CIM', .1, .05, 1)]);
ok(conAfin.find(p => p.id === 'A5').puntaje < sinAfin.find(p => p.id === 'A5').puntaje, 'la afinidad pesa: si rinde el doble en CIM (que castiga movilizar), A5 baja');
ok(E.pesos([arq('X', .1, .1, 9), arq('Y', .1, .1, 1)]).X === 2 / 3, 'la afinidad se acota en ×2');
/* Un arquetipo sin fila en la matriz (los de Bogotá pasaron a 8 el 19-oct y la
   matriz tiene 6): cuenta como «igual», no se descarta ni revienta. */
const nuevo = { codigo: null, sinFila: true, id: 'nuevo', nombre: 'nuevo', share: .5, territorio: .5, ratio: 1 };
const conNuevo = E.principios(banco, [arq('PVP', .5, .5, 1), nuevo]);
ok(igual(conNuevo.map(p => p.id), solo('PVP')) && conNuevo.find(p => p.id === 'A5').puntaje === 1, 'un arquetipo sin fila cuenta como «igual»: diluye el puntaje (A5 pasa de 2 a 1) pero no cambia el orden');
ok(E.territorio(banco, [arq('PVP', .5, .5, 1.2), nuevo]).find(t => t.id === 'nuevo').centrales.length === 0, 'en la tabla de territorio el sin fila sale, con su cuadrante y sin celdas de la matriz');
const acc = E.acciones(banco, 'posicionamiento', E.principios(banco, [arq('BDG', 1, 1, 1)]), { lectura: 'barrio' }, { estado: 'abierta' });
ok(acc[0].principio === 'A6' && acc.every(a => a.fase === 'posicionamiento') && !acc.some(a => a.lectura === 'figura'), 'las acciones salen de la fase, en el orden de los principios, y las de figura no salen para un trabajo de barrio');
ok(E.acciones(banco, 'precampana', E.principios(banco, [arq('CMN', 1, 1, 1)]), {}, { estado: 'cerrada' }).filter(a => a.principio === 'A1').every(a => a.lista === 'cerrada'), 'en precampaña, lista cerrada: la acción de A1 es la del renglón, no la del voto preferente');
ok(E.evaluar({ banco, ciudad: null, corp: 'concejo' }).estado === 'todavia-no' && E.evaluar({ banco, ciudad: 'bogota', corp: 'asamblea', L: { total: 1 } }).estado === 'todavia-no', 'una ciudad sin arquetipos y una asamblea dicen «todavía no»');
/* Cartagena (oct-20-2026): sus 8 tipologías tienen fila, del equipo y sin validar. */
const ctg = Object.values(banco.arquetipos).filter(a => a.ciudad === 'cartagena');
ok(ctg.length === 8 && ctg.every(a => a.corte === '2023' && a.fuente === 'equipo-sin-validar'), 'Cartagena: las 8 tipologías tienen fila, marcada como criterio del equipo sin validar');
ok(solo('QMI').at(-1) === 'A8', 'un territorio todo «Que Miren la Isla»: lo digital va al final (la conectividad no llega)');
ok(/Alcaldía de Bogotá/.test(E.evaluar({ banco, ciudad: 'bogota', corp: 'alcaldia', L: { total: 1, cortes: ['alcaldia', 'concejo'] } }).motivo), 'la Alcaldía de Bogotá dice «todavía no» con su razón (la matriz arrancó con los seis de Concejo)');

/* ── 2. Casos reales ───────────────────────────────────────────────────── */
if (!process.argv.includes('--sin-red')) {
  try {
    const json = async u => { const r = await fetch(u); if (!r.ok) throw new Error(`${r.status} ${u}`); return r.json(); };
    const txt = await readFile(new URL('legislativo-electos.js', RAIZ), 'utf8');
    const congresistas = JSON.parse(txt.match(/ELECTOS_RAW=(\[.*?\]\]);/s)[1]).map(r => r[1]);
    const LC = await A.leer('bogota', [], { corp: 'concejo' });
    const pinta = R => R.territorio.map(t => `${t.codigo || t.id} ${(t.share * 100).toFixed(1)}/${(t.territorio * 100).toFixed(1)} ×${t.ratio?.toFixed(2)} ${t.cuadrante}`).join(' · ');

    /* 2a · Un concejal «figura» de Bogotá con arraigo bajo. Se relanza al
       Concejo con su lista de 2023. */
    {
      const SLUG = 'CONC2023-16-1-5443-2';
      const mesas = (await json(`${S3}/concejo-2023/${SLUG}.json`)).mesas;
      const L = await A.leer('bogota', mesas, { corp: 'concejo' });
      const campana = { corp: 'concejo', ruta: 'same', avales: 'partido', partido: 'BOGOTÁ MÁS FUERTE', departamento: '16', municipio: 'BOGOTÁ D.C.' };
      const alcance = await EN.alcanceDe({ campana, corpHistorica: 'concejo', mesasPropias: mesas });
      const KL = await K.leer({ campana, slugs: [SLUG], mesasPropias: mesas, alcance, meta: 0, usuario: { slugs: [SLUG] }, baseUrl: S3, congresistas });
      const R = E.evaluar({ banco, fecha: '2026-10-19', ciudad: 'bogota', corp: 'concejo', L, LT: LC, lente: 'propio', arraigo: E.arraigoDe(arraigos, [SLUG]), escalera: KL.escalera, plano: KL.plano });
      console.log(`  figura · principios ${R.principios.map(p => `${p.id} ${p.puntaje}`).join(' · ')}`);
      console.log(`  figura · territorio ${pinta(R)}`);
      console.log(`  figura · lugar «${R.lugar}» · acción: ${R.accion?.texto}`);
      console.log(`  figura · competencia ${R.competencia.estado} · ${R.competencia.lista} · usted ${JSON.stringify(R.competencia.usted)} · principal ${JSON.stringify(R.competencia.principal)}`);
      const cim = R.territorio.find(t => t.codigo === 'CIM');
      console.log(`  figura · CIM fuertes ${cim.fuertes.map(b => `${b.nombre} ×${b.idx}`).join(', ')} · huecos ${cim.huecos.map(b => `${b.nombre} ×${b.idx}`).join(', ')}`);
      ok(R.estado === 'ok' && R.lente === 'propio' && R.corte === 'concejo', 'figura · lee sus votos con la tipología de Concejo');
      ok(Math.abs(L.total - 11586) <= 5, `figura · ${L.total} votos ubicados en barrios (el caso de referencia: 11.586)`);
      /* ⚠️ El caso hecho a mano decía ×1,76 (9,9 % contra 5,6 %): asignó cada
         barrio entero a su arquetipo DOMINANTE. El panel 05 —y por eso este
         motor— reparte con la MEZCLA de cada barrio, que aplana los cocientes:
         ×1,20 (9,7 % contra 8,1 %). Mismo dato, dos reglas; la del producto es
         la del panel. */
      /* Re-fijado el 19-oct-2026: los arquetipos de Bogotá pasaron de 6 a 8 por
         corporación. Con 6 daba ×1,20 (9,7 % contra 8,1 %) y el orden
         A7 A1 A6 A8 A5 A2 A3 A4. Los dos nuevos («sin-dueno» y «opinion») aún
         no tienen fila en la matriz y se llevan el 39 % de su votación: cuentan
         como «igual», y por eso A5 sube. */
      ok(Math.abs(cim.ratio - 1.25) < .01 && Math.abs(cim.share - .046) < .001 && Math.abs(cim.territorio - .037) < .001, `figura · afinidad con «Ciudadela movilizada» ×${cim.ratio.toFixed(2)} (4,6 % contra 3,7 %): la del panel 05, con la mezcla de cada barrio`);
      ok(Math.abs(R.sinFila.share - .393) < .002, `figura · ${(R.sinFila.share * 100).toFixed(1)} % de su votación en arquetipos sin fila en la matriz (${R.sinFila.nombres.join(', ')})`);
      ok(igual(R.principios.map(p => p.id), ['A7', 'A6', 'A5', 'A1', 'A8', 'A2', 'A3', 'A4']), `figura · orden de los principios FIJADO: ${R.principios.map(p => p.id).join(' ')}`);
      ok(igual(R.territorio.map(t => [t.codigo || t.id, t.cuadrante]), [['sin-dueno', 'retener'], ['PDP', 'movilizar'], ['CMN', 'conocer'], ['opinion', 'retener'], ['PVP', 'no-gastar'], ['BDG', 'no-gastar'], ['NDF', 'no-gastar'], ['CIM', 'retener-crecer']]),
        'figura · tabla de territorio FIJADA (8 arquetipos): retener clase media sin dueño y norte de opinión, movilizar periferia de partido, hacerse conocer en clase media de nombre, retener y crecer en ciudadela movilizada');
      ok(R.accion?.lectura === 'figura' && R.accion.principio === 'A7', 'figura · la acción de la semana es la de toma de posición (figura de ciudad, A7)');
      ok(R.competencia.estado === 'abierta' && R.competencia.usted?.puesto === 1 && R.competencia.usted.elegido && R.competencia.principal?.puesto === 2, 'figura · lista abierta, encabezó su lista: el rival principal es el segundo de la misma lista');
      ok(R.figura.lectura === 'figura' && R.figura.valor === .07, `figura · arraigo 7 % contra ${(R.figura.referencia * 100).toFixed(1)} % de la ciudad: figura de ciudad`);
      ok(/^Figura de ciudad, con su mejor terreno en «Norte de opinión»/.test(R.lugar), 'figura · el lugar dice figura de ciudad y su mejor terreno (el más afín con al menos 8 % de su votación)');
    }

    /* 2b · Una edilesa de barrio: se relanza a la JAL de Barrios Unidos. El
       territorio es su localidad, no la ciudad. */
    {
      const SLUG = 'JAL2023-16-1-7523-82-59d0dd';
      const mesas = (await json(`${S3}/jal-2023/${SLUG}.json`)).mesas;
      const L = await A.leer('bogota', mesas, { corp: 'jal' });
      const LT = A.recortar(LC, 'BARRIOS UNIDOS');
      const campana = { corp: 'jal', ruta: 'same', avales: 'partido', partido: 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', departamento: '', municipio: '', localidad: '' };
      const alcance = await EN.alcanceDe({ campana, corpHistorica: 'jal', mesasPropias: mesas });
      const KL = await K.leer({ campana, slugs: [SLUG], mesasPropias: mesas, alcance, meta: 0, usuario: { slugs: [SLUG] }, baseUrl: S3, congresistas });
      const R = E.evaluar({ banco, fecha: '2026-10-19', ciudad: 'bogota', corp: 'jal', L, LT, lente: 'propio', arraigo: E.arraigoDe(arraigos, [SLUG]), escalera: KL.escalera, plano: KL.plano });
      console.log(`  edilesa · principios ${R.principios.map(p => `${p.id} ${p.puntaje}`).join(' · ')}`);
      console.log(`  edilesa · territorio ${pinta(R)}`);
      console.log(`  edilesa · lugar «${R.lugar}» · acción: ${R.accion?.texto}`);
      console.log(`  edilesa · competencia ${R.competencia.estado} · usted ${JSON.stringify(R.competencia.usted)} · principal ${JSON.stringify(R.competencia.principal)}`);
      ok(R.estado === 'ok' && R.recorte === 'BARRIOS UNIDOS' && L.total === 709, `edilesa · sus 709 votos, contra su localidad (${L.total})`);
      ok(R.figura.lectura === 'barrio' && R.figura.oficio, 'edilesa · trabajo de barrio, rotulado como criterio de oficio (sin arraigo medido para JAL)');
      ok(R.competencia.estado === 'abierta' && R.competencia.usted?.puesto === 3 && R.competencia.distancia === 910, `edilesa · 3.ª de su lista, a 910 votos del último elegido (${R.competencia.usted?.puesto}, ${R.competencia.distancia})`);
      ok(R.competencia.principal?.puesto === 2 && R.competencia.principal.elegido, 'edilesa · el rival principal es el último elegido de su propia lista');
      ok(igual(R.principios.map(p => p.id), ['A7', 'A1', 'A8', 'A6', 'A2', 'A3', 'A4', 'A5']), `edilesa · orden de los principios FIJADO: ${R.principios.map(p => p.id).join(' ')}`);
      ok(igual(R.territorio.map(t => [t.codigo || t.id, t.cuadrante]), [['opinion', 'retener'], ['CMN', 'conocer'], ['sin-dueno', 'retener'], ['CIM', 'conocer'], ['BDG', 'no-gastar'], ['PDP', 'no-gastar'], ['NDF', 'retener-crecer'], ['PVP', 'no-gastar']]),
        'edilesa · tabla de territorio FIJADA (8 arquetipos, contra su localidad): retener norte de opinión y clase media sin dueño, hacerse conocer en clase media de nombre y ciudadela movilizada');
      ok(R.accion?.lectura === 'barrio' && R.accion.principio === 'A7', 'edilesa · la acción de la semana es la de rendición de cuentas por sector (trabajo de barrio, A7)');
    }
  } catch (e) {
    ok(false, `real · no se pudo leer S3 (${e.message}); correr con --sin-red para solo la lógica`);
  }
}
console.log(fallas ? `\n${fallas} fallas` : '\ntodo bien');
process.exit(fallas ? 1 : 0);
