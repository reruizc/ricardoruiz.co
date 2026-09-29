/* prueba-contendientes.mjs — el motor de contendientes (candidato-360-contendientes.js).
   ------------------------------------------------------------------
   Dos partes:
   1. Casos sintéticos, sin red: una regla por caso (afinidad, franjas,
      cercanía y «no sabemos», presión y niveles, persona, congresista,
      fuentes A/B/C, titular no reelegible, escalera abierta/cerrada, mapa).
   2. Casos reales contra S3 con las cifras FIJADAS: la JAL de Barrios Unidos
      y el Concejo de Bogotá, con la misma candidatura de referencia del plan
      (una edilesa de Nuevo Liberalismo, 709 votos en 2023). Salen de la
      medición del plan (PLAN §0); si cambian, cambió el motor o cambiaron los
      datos, y hay que saber cuál. `--sin-red` salta esta parte.

     node tools/candidato-360/prueba-contendientes.mjs                         */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const RAIZ = new URL('../../', import.meta.url);
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
const almacen = new Map();
/* MATRIZ_LOCAL=1 lee la matriz nacional (fase 4) del disco en vez de S3:
   sirve para verificar antes de subirla. */
const MATRIZ_DIR = new URL('Bases de datos/output_matriz_puesto/', RAIZ);
const MATRIZ_BASE = process.env.MATRIZ_LOCAL ? 'http://local-matriz' : null;
const fetchPrueba = async (u, o) => {
  if (String(u).startsWith('http://local-matriz/')) { try { return new Response(await readFile(new URL(String(u).slice(20), MATRIZ_DIR), 'utf8'), { status: 200 }); } catch { return new Response('{}', { status: 404 }); } }
  return globalThis.fetch(u, o);
};
const ctx = vm.createContext({
  fetch: fetchPrueba, console: { log: console.log, warn: () => {}, error: console.error },
  localStorage: { getItem: k => almacen.get(k) ?? null, setItem: (k, v) => almacen.set(k, String(v)) },
  RRData: { publicUrl: p => `${S3.replace(/\/congreso-2026\/output$/, '')}/${p}` },
  /* El Día D pide el código electoral del municipio por nombre, desde la
     cartografía. Los dos casos son Bogotá: 001. */
  C360Electorado: { codigoMunicipio: async () => '001' },
});
/* La URL de cada candidatura sale de la regla del electorado real (sin ella el
   modo por archivos caía a la carpeta del Congreso y daba 404). */
{
  const aux = vm.createContext({ console: { log() {}, warn() {}, error() {} }, fetch: () => Promise.reject(new Error('sin red')), RRData: ctx.RRData });
  aux.window = aux;
  vm.runInContext(await readFile(new URL('candidato-360-electorado.js', RAIZ), 'utf8'), aux, { filename: 'candidato-360-electorado.js' });
  ctx.C360Electorado.urlCandidatura = aux.C360Electorado.urlCandidatura;
}
ctx.window = ctx;
for (const f of ['partidos-bloques.js', 'cand-index.js', 'legislativo-electos.js', 'vote-target.js', 'candidato-360-endoso.js', 'candidato-360-diad.js', 'candidato-360-contendientes.js'])
  vm.runInContext(await readFile(new URL(f, RAIZ), 'utf8'), ctx, { filename: f });
const K = ctx.C360Contendientes, VT = ctx.VoteTarget, EN = ctx.C360Endoso;

let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const cerca = (a, b, eps = .005) => a != null && Math.abs(a - b) < eps;

/* ── 1. Sintéticos ─────────────────────────────────────────────────────── */
const V = new Map([['P1', 1000], ['P2', 1000], ['P3', 1000], ['P4', 1000]]);
ok(K.llaveCand('RAFAEL ANTONIO D´ACUNTI DE LA HOZ', 'X') === K.llaveCand('RAFAEL ANTONIO DACUNTI DE LA HOZ', 'X') && K.llaveCand('DUVAR ALEXIS PAZ ZUÐIGA', 'X') === K.llaveCand('DUVAR ALEXIS PAZ ZUIGA', 'X'), 'la llave de candidato es compacta: los nombres con caracteres rotos del crudo casan con el índice');
const datos = (cands, listas = new Map()) => ({ validos: V, info: new Map(), porCand: new Map(cands.map(c => [K.llaveCand(c.nombre, c.partido), c])), listas, origen: 'matriz' });
const pp = o => new Map(Object.entries(o));
const base = { porPuesto: pp({ P1: 80, P2: 20 }), total: 100, puestos: 2 };
const D0 = datos([]);
ok(cerca(K.afinidad(base, pp({ P1: 25, P2: 25, P3: 25, P4: 25 }), 100, D0), 1), 'un rival parejo en todo el territorio rinde 1 en su base');
ok(cerca(K.afinidad(base, pp({ P1: 100 }), 100, D0), 3.2), 'un rival todo en P1, donde está el 80 % de su base: 3,2');
ok(cerca(K.afinidad(base, pp({ P3: 50, P4: 50 }), 100, D0), 0), 'un rival solo donde usted no está: 0');
ok(K.franja(1.1) === 'mismo-terreno' && K.franja(1.2) === 'alta' && K.franja(.8) === 'baja' && K.franja(null) === 'sin-dato', 'franjas: 0,85–1,15 es «mismo terreno»');

const PB = ctx.PartidosBloques;
ok(K.familia('PARTIDO ALIANZA VERDE').bloque === 'ci' && K.familia('PARTIDO ALIANZA VERDE').sabemos, 'Alianza Verde es centro-izquierda');
ok(!K.familia('PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"').sabemos, 'ASI es aval amplio: «no sabemos», aunque su partido sea ci');
ok(K.cercania('ci', K.familia('PARTIDO ALIANZA VERDE')) === 1 && K.cercania('ci', K.familia('PARTIDO LIBERAL COLOMBIANO')) === .6 && K.cercania('ci', K.familia('PARTIDO CENTRO DEMOCRATICO')) === .1, 'cercanía por pasos: 0 → 1 · 1 → 0,6 · 3 → 0,1');
ok(K.cercania('ci', K.familia('MOVIMIENTO INVENTADO XYZ')) === .4, '«no sabemos» vale 0,4: ni cerca ni lejos');
ok(K.familiaCampana({ avales: 'firmas', espectro: 'cd' }) === 'cd' && K.familiaCampana({ avales: 'partido', partido: 'PARTIDO ALIANZA VERDE' }) === 'ci' && K.familiaCampana({ avales: 'partido', partido: 'PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"' }) === '', 'familia de la campaña: espectro por firmas, partido con aval, vacío con aval amplio');

ok(cerca(K.presion({ cercania: 1, afinidad: 2, votos: 1000, meta: 1000 }), .5), 'presión = cercanía × afinidad/2 × votos/(votos+meta): 1 × 1 × 0,5');
ok(K.presion({ cercania: 1, afinidad: 1, votos: 50000, meta: 1000 }) < 1 && K.presion({ cercania: 1, afinidad: 1, votos: 50000, meta: 1000 }) > K.presion({ cercania: 1, afinidad: 1, votos: 20000, meta: 1000 }), 'el tamaño no se satura: 50.000 pesa más que 20.000 aunque los dos pasen la meta');
ok(cerca(K.presion({ cercania: 1, afinidad: 5, votos: 1, meta: 1 }), .5), 'la afinidad se acota en 2');
ok(K.presion({ cercania: 1, afinidad: null, votos: 1000, meta: 1000 }) === K.presion({ cercania: 1, afinidad: 1, votos: 1000, meta: 1000 }), 'sin afinidad medida la presión usa la neutra (1), no el tope');

ok(K.llavePersona({ nombre: 'JUAN CARLOS PEREZ GOMEZ', slug: 'a' }) === K.llavePersona({ nombre: 'Juan Carlos Pérez Gómez', slug: 'b' }), 'cuatro componentes con tildes distintas: la misma persona');
ok(K.llavePersona({ nombre: 'JUAN PEREZ', slug: 'a' }) !== K.llavePersona({ nombre: 'JUAN PEREZ', slug: 'b' }), 'dos componentes no se funden (hay miles de «Juan Pérez»)');
ok(K.esCongresista('DANIEL FELIPE BRICENO MONTES', ['DANIEL FELIPE BRICEÑO MONTES']) && !K.esCongresista('GUSTAVO MIGUEL OSORIO PETRO', ['GUSTAVO PETRO URREGO']), 'congresista por nombre completo, no por un apellido suelto');

/* Un concejo de juguete: 2 listas, 3 curules, y un rival de 2019 (fuente C). */
const row = (nombre, partido, votos, slug) => ({ nombre, partido, votos, slug, corp: 'CONCEJO · X · 2023' });
const REP = { label: 'X', uninominal: false, seats: 3, cifra: 500,
  rows: [row('ANA MARIA RUIZ SOTO', 'PARTIDO ALIANZA VERDE', 900, 'a1'), row('LUIS JOSE PAZ ROA', 'PARTIDO ALIANZA VERDE', 400, 'a2'), row('USTED CANDIDATA DE PRUEBA', 'PARTIDO ALIANZA VERDE', 300, 'u1'), row('MARIO LUIS DIAZ RIOS', 'PARTIDO ALIANZA VERDE', 100, 'a4'),
    row('PEDRO PABLO GIL LARA', 'PARTIDO CENTRO DEMOCRATICO', 800, 'c1'), row('SARA ELENA MORA VEGA', 'PARTIDO CENTRO DEMOCRATICO', 150, 'c2')],
  ultimos: [{ partido: 'PARTIDO ALIANZA VERDE', votos: 400 }, { partido: 'PARTIDO CENTRO DEMOCRATICO', votos: 800 }],
  electos: [row('LUIS JOSE PAZ ROA', 'PARTIDO ALIANZA VERDE', 400, 'a2'), row('PEDRO PABLO GIL LARA', 'PARTIDO CENTRO DEMOCRATICO', 800, 'c1'), row('ANA MARIA RUIZ SOTO', 'PARTIDO ALIANZA VERDE', 900, 'a1')],
  allocations: new Map([['PARTIDO ALIANZA VERDE', 2], ['PARTIDO CENTRO DEMOCRATICO', 1]]) };
REP.parties = [{ name: 'PARTIDO ALIANZA VERDE', candidates: REP.rows.slice(0, 4), votes: 1700, cerrada: false }, { name: 'PARTIDO CENTRO DEMOCRATICO', candidates: REP.rows.slice(4), votes: 950, cerrada: false }];
const F = K.fuentesDelReparto(REP);
ok(F.porSlug.get('a1')?.[0] === 'A' && F.porSlug.get('u1')?.[0] === 'B' && !F.porSlug.has('a4') && !F.porSlug.has('c2'), 'A = elegidos; B = ≥ 50 % del último elegido de SU lista (300 ≥ 200 sí, 100 no; 150 < 400 del CD)');
const cand = (r, o) => ({ nombre: r.nombre, partido: r.partido, porPuesto: pp(o), total: Object.values(o).reduce((a, b) => a + b, 0) });
const DT = datos(REP.rows.map((r, i) => cand(r, [{ P1: 500, P2: 400 }, { P3: 400 }, { P1: 200, P2: 100 }, { P4: 100 }, { P1: 400, P3: 400 }, { P2: 150 }][i])), new Map([['PARTIDO ALIANZA VERDE', pp({ P1: 100 })]]));
const bU = K.baseDesdeMesas([{ dep: 'x' }], DT, null);
ok(bU.total === 0, 'una mesa fuera de los puestos del territorio no entra a la base');
const baseU = { porPuesto: pp({ P1: 200, P2: 100 }), total: 300, puestos: 2, fuera: 0 };
const otra = { entrada: { nombre: 'ROSA INES CANO MEJIA', partido: 'PARTIDO ALIANZA VERDE', votos: 700, slug: 'o1', corp: 'CONCEJO · X · 2019' }, porPuesto: pp({ P1: 700 }), total: 700 };
const otraMisma = { entrada: { nombre: 'ANA MARÍA RUIZ SOTO', partido: 'PARTIDO LIBERAL COLOMBIANO', votos: 600, slug: 'o2', corp: 'CONCEJO · X · 2019' }, porPuesto: pp({ P1: 600 }), total: 600 };
const L = K.evaluar({ reparto: REP, datos: DT, base: baseU, baseModo: 'propio', familiaUsuario: 'ci', partidoCampana: 'PARTIDO ALIANZA VERDE',
  usuario: { nombre: 'USTED CANDIDATA DE PRUEBA', slugs: ['u1'] }, meta: 400, otras: [otra, otraMisma], congresistas: ['PEDRO PABLO GIL LARA'] });
const por = n => L.rivales.find(r => r.nombre.startsWith(n));
ok(!L.rivales.some(r => r.slug === 'u1'), 'usted no es su propio rival');
ok(por('ROSA')?.fuentes.join() === 'C', 'fuente C: 700 votos de 2019 ≥ 50 % de la mediana de los últimos elegidos');
ok(por('ANA')?.fuentes.join() === 'A,C' && por('ANA').anio === 2023 && por('ANA').marcas.includes('cambio-de-partido'), 'la misma persona en 2019 y 2023 es un rival, manda 2023 y se marca el cambio de partido');
ok(por('PEDRO')?.marcas.includes('congresista-2026') && !por('PEDRO').enIndice, 'congresista 2026: queda en la lista, fuera del índice');
ok(L.resumen.niveles.alta + L.resumen.niveles.media + L.resumen.niveles.baja === L.resumen.enIndice, 'los tres niveles cubren a todos los del índice');
ok(L.plano.every(r => r.enIndice) && L.vitrina.length === Math.min(3, L.resumen.enIndice), 'plano y vitrina solo con los del índice');
ok(L.escalera.estado === 'abierta' && L.escalera.usted?.puesto === 3 && L.escalera.distancia === 100 && L.escalera.k === 2, 'escalera: usted 3.ª, a 100 votos del último elegido (400)');
const rc = { ...REP, parties: [{ ...REP.parties[0], cerrada: true }] };
ok(K.escalera(rc, 'PARTIDO ALIANZA VERDE', {}).estado === 'cerrada', 'lista cerrada: sin escalera');
ok(K.escalera({ uninominal: true }, 'X', {}).estado === 'uninominal' && K.escalera(REP, 'PARTIDO INEXISTENTE', {}).estado === 'sin-lista', 'alcaldía sin escalera; partido sin lista en 2023 lo dice');
ok(L.mapa.conteo.disputa + L.mapa.conteo.fortaleza + L.mapa.conteo['terreno-rivales'] + L.mapa.conteo['terreno-ajeno'] + L.mapa.conteo['sin-base'] + L.mapa.conteo.poco === 4, 'el mapa clasifica todos los puestos del territorio');

const UNI = { uninominal: true, label: 'X', rows: [row('ALCALDE GANADOR UNO', 'PARTIDO LIBERAL COLOMBIANO', 1000, 'g'), row('SEGUNDO FUERTE DOS', 'PARTIDO ALIANZA VERDE', 300, 's'), row('TERCERO DEBIL TRES', 'PARTIDO ALIANZA VERDE', 100, 't')] };
UNI.ganador = UNI.rows[0]; UNI.electos = [UNI.ganador];
const LU = K.evaluar({ reparto: UNI, datos: D0, base: null, familiaUsuario: 'ci', usuario: {}, meta: 1000 });
ok(LU.rivales.find(r => r.slug === 'g')?.marcas.includes('titular-no-reelegible') && !LU.rivales.find(r => r.slug === 'g').enIndice, 'alcaldía: el titular no puede reelegirse (C.P. art. 314): fuera del índice');
ok(LU.rivales.some(r => r.slug === 's') && !LU.rivales.some(r => r.slug === 't'), 'uninominal: B = ≥ 20 % del ganador');

const M = (pue, v) => ({ dep: '16', mun: '001', zon: '12', pue, mesa: '001', v, comNom: 'BARRIOS UNIDOS', pueNom: 'P' });
const DM = K.matrizDesdeMesas([{ entrada: { nombre: 'A B C', partido: 'X' }, mesas: [M('01', 5), M('01', 7), M('02', 3), { ...M('03', 9), zon: '90' }] }], { '160011201': [500], '160011202': [300] }, null);
ok(DM.porCand.get(K.llaveCand('A B C', 'X')).total === 15 && DM.validos.get('160011201') === 500 && DM.origen === 'archivos', 'sin matriz: se arma desde los archivos, sin la zona 90, con los válidos de totales-puesto');

const cc = K.completarCampana({ corp: 'jal', ruta: 'same' }, { tipo: 'localidad', departamento: '16', municipio: '1', localidad: 'BARRIOS UNIDOS' }, [M('01', 5)].map(m => ({ ...m, munNom: 'BOGOTÁ D.C.', depNom: 'BOGOTÁ D.C.' })));
ok(cc.departamento === '16' && cc.municipio === 'BOGOTÁ D.C.' && cc.localidad === 'BARRIOS UNIDOS' && cc.ruta === 'same', '«la misma corporación» sin territorio: se completa desde el alcance y el nombre de sus mesas');
ok(K.completarCampana({ corp: 'concejo', departamento: '05', municipio: 'X' }, { departamento: '16' }, []).departamento === '05', 'con territorio guardado no se toca');
const svgV = K.planoSVG(L, { vitrina: true }), svgT = K.planoSVG(L, {});
const nombres = svg => (svg.match(/class="k-nombre"/g) || []).length, titulos = svg => (svg.match(/<title>/g) || []).length;
ok(nombres(svgV) === L.vitrina.length && titulos(svgV) === L.vitrina.length && /vitrina-blur/.test(svgV), `vitrina: solo ${L.vitrina.length} nombres y ${L.vitrina.length} títulos en el SVG; los demás, borrosos y sin texto`);
ok(!L.rivales.filter(r => !L.vitrina.includes(r.key)).some(r => svgV.includes(K.corto(r.nombre))), 'vitrina: el nombre de los demás no está en el texto del SVG');
ok(nombres(svgT) === Math.min(K.TOP_PLANO, L.plano.length) && !/vitrina-blur/.test(svgT), 'con acceso: nombres de los del plano, nada borroso');
ok(!/amenaza/i.test(svgT + Object.values(K.AVISO_TXT).join(' ') + Object.values(K.NIVEL_TXT).join(' ') + Object.values(K.MARCA_TXT).join(' ')), 'la palabra «amenaza» no aparece en ningún texto del motor');

/* Fase 3 · el mapa por unidad: se suman los puestos y se clasifica la suma. */
const tot = { B: 300, RT: 1000, VAL: 4000 };
ok(K.categoria({ b: 150, r: 300, val: 1000 }, tot).cat === 'disputa' && K.categoria({ b: 150, r: 100, val: 1000 }, tot).cat === 'fortaleza'
  && K.categoria({ b: 20, r: 300, val: 1000 }, tot).cat === 'terreno-rivales' && K.categoria({ b: 20, r: 100, val: 1000 }, tot).cat === 'terreno-ajeno', 'las cuatro categorías de la regla');
ok(K.categoria({ b: 150, r: 300, val: 150 }, tot).cat === 'poco' && K.categoria({ b: 3, r: 300, val: 1000 }, tot).cat === 'poco' && K.categoria({ b: 0, r: 300, val: 1000 }, tot).cat === 'sin-base', 'puesto chico o con pocos votos suyos: «poco»; sin votos suyos: «sin base»');
ok(K.bandaRivales(1.2) === 'fuerte' && K.bandaRivales(1) === 'parejo' && K.bandaRivales(.5) === 'flojo' && K.bandaRivales(null) === 'sin-dato', 'la segunda capa: tres bandas con la franja del plano');
const mapaS = { puestos: [{ code: 'P1', votos: 3, rivales: 40, validos: 150 }, { code: 'P2', votos: 4, rivales: 60, validos: 150 }, { code: 'P3', votos: 90, rivales: 100, validos: 1000 }, { code: 'P4', votos: 5, rivales: 5, validos: 500 }],
  totales: { B: 102, RT: 205, VAL: 1800 }, umbral: true };
const U = K.disputaPorUnidad(mapaS, p => ({ P1: 'A', P2: 'A', P3: 'B' })[p.code] || '', k => `Barrio ${k}`);
const uA = U.unidades.find(u => u.key === 'A');
ok(uA.votos === 7 && uA.validos === 300 && uA.puestos === 2 && uA.cat !== 'poco', 'dos puestos chicos se leen juntos en su barrio: 7 votos y 300 válidos ya no son «poco»');
ok(U.fuera === 5 && U.unidades.length === 2, 'el puesto sin barrio queda por fuera y se cuenta, no se inventa');
const cuadro = (x, y) => ({ type: 'Feature', properties: { b: `${x},${y}` }, geometry: { type: 'Polygon', coordinates: [[[x, y], [x + .001, y], [x + .001, y + .001], [x, y + .001], [x, y]]] } });
const F3 = [cuadro(-74, 4.6), cuadro(-74.01, 4.6), cuadro(-74.2, 4.6)];
const R3 = K.rellenos(F3, p => p.b, p => p.b, new Set(['-74,4.6']));
ok(R3.get('-74.01,4.6')?.de === '-74,4.6' && !R3.has('-74.2,4.6'), 'relleno: el barrio sin dato toma al vecino a ~1 km; a más de 3 km queda sin dato');

/* ── 2. Casos reales ───────────────────────────────────────────────────── */
if (!process.argv.includes('--sin-red')) {
  try {
    const json = async u => { const r = await fetch(u); if (!r.ok) throw new Error(`${r.status} ${u}`); return r.json(); };
    const SLUG = 'JAL2023-16-1-7523-82-59d0dd', NOMBRE = 'NATALIA SOPHIA PARRA ROJAS';
    const propias = (await json(`${S3}/jal-2023/${SLUG}.json`)).mesas;
    const txt = await readFile(new URL('legislativo-electos.js', RAIZ), 'utf8');
    const congresistas = JSON.parse(txt.match(/ELECTOS_RAW=(\[.*?\]\]);/s)[1]).map(r => r[1]);
    const registro = async (dir, file) => (await json(`${S3}/${dir}/${file}`)).candidatos.map(c => ({ ...c, dataUrl: `${S3}/${dir}/${c.slug}.json` }));
    const usuario = { nombre: NOMBRE, slugs: [SLUG] };
    const conPartido = c => Array.from(c.porCand.values());

    /* 2a · JAL de Barrios Unidos, se relanza. «La misma corporación»: la
       campaña guardada NO trae territorio (así la deja el CRM) y `leer` lo
       completa desde sus mesas. Los congresistas los lee de ELECTOS, como en
       la página. */
    const cJ = { corp: 'jal', ruta: 'same', avales: 'partido', partido: 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', departamento: '', municipio: '', localidad: '' };
    const aJ = await EN.alcanceDe({ campana: cJ, corpHistorica: 'jal', mesasPropias: propias });
    const metaJ = (await VT.estimate({ corp: 'jal', territory: 'BARRIOS UNIDOS · BOGOTÁ D.C.', baseUrl: S3, partido: cJ.partido, codigo: { dep: '16', mun: '1' } })).target;
    const LJ = await K.leer({ campana: cJ, slugs: [SLUG], mesasPropias: propias, alcance: aJ, meta: metaJ, usuario, baseUrl: S3, matrizBase: MATRIZ_BASE });
    const J = { datos: LJ.datos, base: LJ.baseDatos, baseModo: LJ.baseModo, reparto: LJ.repartoCompleto };
    ok(LJ.campana.departamento === '16' && LJ.campana.localidad === 'BARRIOS UNIDOS' && /BOGOT/.test(LJ.campana.municipio), `JAL · la campaña sin territorio se completa desde sus mesas (${LJ.campana.departamento} · ${LJ.campana.municipio} · ${LJ.campana.localidad})`);
    ok(aJ.tipo === 'localidad' && J.datos.origen === 'matriz' && J.datos.validos.size === 32, `JAL · territorio = localidad, matriz de 32 puestos (${J.datos.validos.size})`);
    ok(J.baseModo === 'propio' && J.base.total === 709, `JAL · base propia: sus 709 votos (${J.base?.total})`);
    const repJ = Object.fromEntries(J.reparto.allocations);
    ok(J.reparto.seats === 9 && repJ['PARTIDO LIBERAL COLOMBIANO'] === 2 && repJ['PARTIDO CENTRO DEMOCRÁTICO'] === 2 && repJ['NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA'] === 2 && repJ['PARTIDO ALIANZA VERDE'] === 1 && repJ['PACTO HISTORICO'] === 1, `JAL · reparto H8: ${JSON.stringify(repJ)}`);
    /* §0 · H1: la afinidad (sin redondear: el plan redondeaba a dos decimales y
       por eso decía 119/175 en el Concejo) de TODOS los rivales con ≥ 50 votos, con la misma función. */
    const VALJ = [...J.datos.validos.values()].reduce((a, b) => a + b, 0);
    const afJ = conPartido(J.datos).filter(x => x.nombre !== NOMBRE && x.total >= 50).map(x => K.afinidad(J.base, x.porPuesto, x.total, J.datos, VALJ));
    ok(afJ.length === 67 && cerca(Math.min(...afJ), .76, .01) && cerca(Math.max(...afJ), 1.11, .01), `JAL · H1: 67 rivales, afinidad ${Math.min(...afJ).toFixed(2)}–${Math.max(...afJ).toFixed(2)}`);
    ok(afJ.filter(a => K.franja(a) === 'mismo-terreno').length === 65, `JAL · H1: 65 de 67 en «mismo terreno» (${afJ.filter(a => K.franja(a) === 'mismo-terreno').length})`);
    ok(LJ.avisos.includes('territorio-parejo'), 'JAL · la tarjeta avisa que el territorio es parejo');
    ok(LJ.escalera.estado === 'abierta' && LJ.escalera.usted?.puesto === 3 && LJ.escalera.distancia === 910, `JAL · H3: 3.ª de su lista, a 910 votos del último elegido (${LJ.escalera.usted?.puesto}, ${LJ.escalera.distancia})`);
    const top2 = LJ.plano.slice(0, 2).map(r => r.partido);
    ok(top2.every(p => p === cJ.partido), `JAL · H3: los dos de más presión son de su propia lista (${top2.join(' · ')})`);
    /* §0: el mapa como se midió (sin umbral, sin voto de lista). */
    const fu = 'ci', sinListas = { ...J.datos, listas: new Map() };
    const cerc = conPartido(J.datos).filter(x => x.nombre !== NOMBRE && K.cercania(fu, K.familia(x.partido, x.nombre)) >= K.CERCANO).map(x => x.porPuesto);
    const m0 = K.disputa(J.base, sinListas, cerc, { umbral: false }).conteo;
    ok(m0.fortaleza === 10 && m0.disputa === 1 && m0['terreno-rivales'] === 12 && m0['terreno-ajeno'] === 8 && m0['sin-base'] === 1, `JAL · mapa como en el plan: ${JSON.stringify(m0)}`);
    console.log(`  JAL · mapa del motor (con umbral y voto de lista): ${JSON.stringify(LJ.mapa.conteo)} · meta ${metaJ} · rivales ${LJ.resumen.rivales} (${LJ.resumen.enIndice} en el índice) · niveles ${JSON.stringify(LJ.resumen.niveles)}`);

    /* 2b · Concejo de Bogotá, salta desde la JAL. */
    const cC = { corp: 'concejo', ruta: 'other', departamento: '16', departamentoNombre: 'Bogotá D.C.', municipio: 'BOGOTÁ D.C.', avales: 'partido', partido: 'NUEVO LIBERALISMO EN MARCHA' };
    const aC = await EN.alcanceDe({ campana: cC, corpHistorica: 'jal', mesasPropias: propias, codigoMunicipio: async () => '001' });
    const regC = [...await registro('concejo-2019', 'index-concejo-2019.json'), ...await registro('alcaldia-2023', 'index-alcaldia-2023.json'), ...await registro('jal-2023', 'index-jal-2023.json')];
    const estC = await VT.estimate({ corp: 'concejo', territory: 'BOGOTÁ D.C.', baseUrl: S3, partido: cC.partido, codigo: { dep: '16', mun: '1' } });
    const C = await K.cargar(cC, { baseUrl: S3, alcance: aC, mesasPropias: propias, slugsPropios: [SLUG], registro: regC, matrizBase: MATRIZ_BASE });
    const LC = K.evaluar({ ...C, familiaUsuario: K.familiaCampana(cC), partidoCampana: cC.partido, usuario, meta: estC.target, congresistas });
    ok(C.datos.origen === 'matriz' && C.datos.validos.size === 943 && C.baseModo === 'salto', `Concejo · matriz de 943 puestos, base = su JAL (${C.datos.validos.size}, ${C.baseModo})`);
    const repC = Object.fromEntries(C.reparto.allocations);
    ok(C.reparto.seats === 45 && repC['PARTIDO ALIANZA VERDE'] === 8 && repC['NUEVO LIBERALISMO EN MARCHA'] === 8 && repC['PACTO HISTORICO'] === 7 && repC['PARTIDO CENTRO DEMOCRÁTICO'] === 7 && repC['PARTIDO LIBERAL COLOMBIANO'] === 6, `Concejo · reparto H8 (el cabildo real): ${JSON.stringify(repC)}`);
    ok(estC.detalle.reparto && estC.detalle.reparto.curules === C.reparto.seats && estC.detalle.reparto.cifra === Math.round(C.reparto.cifra), 'Concejo · el reparto de la tarjeta es el mismo de la meta (curules y cifra)');
    const VALC = [...C.datos.validos.values()].reduce((a, b) => a + b, 0);
    const todosC = conPartido(C.datos).filter(x => x.total >= 50);
    const afC = todosC.map(x => K.afinidad(C.base, x.porPuesto, x.total, C.datos, VALC));
    const fr = { alta: afC.filter(a => a >= 1.15).length, medio: afC.filter(a => a >= .85 && a < 1.15).length, baja: afC.filter(a => a < .85).length };
    ok(todosC.length === 434 && fr.alta === 118 && fr.medio === 140 && fr.baja === 176 && cerca(Math.max(...afC), 10.6, .05), `Concejo · H2: 434 rivales, ${fr.alta}/${fr.medio}/${fr.baja}, máx ${Math.max(...afC).toFixed(2)}`);
    const sb = todosC.filter(x => !K.familia(x.partido, x.nombre).sabemos);
    ok(sb.length === 72 && sb.reduce((s, x) => s + x.total, 0) === 171499, `Concejo · H9: 72 sin bloque o aval amplio, 171.499 votos (${sb.length}, ${sb.reduce((s, x) => s + x.total, 0)})`);
    ok(LC.escalera.estado === 'abierta' && LC.escalera.k === 8 && LC.escalera.ultimo?.votos === 9280 && !LC.escalera.usted, `Concejo · escalera de NL: 8 curules, último elegido 9.280 (el índice oficial; la matriz por comuna da 9.153), usted no está en ella (${LC.escalera.ultimo?.votos})`);
    ok(LC.rivales.some(r => r.marcas.includes('congresista-2026') && r.partido.includes('CENTRO DEMOCR')), 'Concejo · H10: un concejal de 2023 hoy es representante, marcado');
    if (process.env.DEPURA) LC.plano.slice(0, 14).forEach((r, i) => console.log('   ', i + 1, r.familia.bloque, r.fuentes.join(''), r.corp, r.partido.slice(0, 30), r.votos, r.afinidad?.toFixed(2), r.presion.toFixed(3)));
    const alc = LC.rivales.filter(r => r.marcas.includes('voto-uninominal'));
    ok(alc.length > 0 && alc.every(r => !r.enIndice) && alc.filter(r => r.marcas.includes('en-ejercicio')).length === 1 && alc.find(r => r.marcas.includes('en-ejercicio')).votos > 1e6, `Concejo · quien viene de la alcaldía queda fuera del índice y el alcalde en ejercicio se marca (${alc.length} de alcaldía)`);
    /* H4, corregido en la fase 2: sin los votos de alcaldía en el índice, entra
       un concejal liberal (un paso, afinidad ×1,71). Lo que el hallazgo afirma
       es que mandan la familia y las vecinas, y que los 9 primeros son de la suya. */
    const top12 = LC.plano.slice(0, 12);
    ok(top12.slice(0, 9).every(r => r.familia.bloque === 'ci') && top12.every(r => r.pasos != null && r.pasos <= 1), `Concejo · H4: los 9 primeros del plano son de centro-izquierda y los 12, a un paso o menos (${top12.map(r => r.familia.bloque).join(' ')})`);
    const cercC = todosC.filter(x => K.cercania('ci', K.familia(x.partido, x.nombre)) >= K.CERCANO).map(x => x.porPuesto);
    const m0C = K.disputa(C.base, { ...C.datos, listas: new Map() }, cercC, { umbral: false }).conteo;
    ok(m0C.fortaleza === 7 && m0C.disputa === 24 && m0C['sin-base'] === 912, `Concejo · mapa como en el plan: ${JSON.stringify(m0C)}`);
    ok(LC.mapa.dosCapas && !LJ.mapa.dosCapas, 'la segunda capa del mapa se ofrece en el salto y no en la JAL');
    console.log(`  Concejo · mapa del motor: ${JSON.stringify(LC.mapa.conteo)} · meta ${estC.target} · rivales ${LC.resumen.rivales} (${LC.resumen.enIndice} en el índice, fuente C: ${LC.rivales.filter(r => r.fuentes.includes('C')).length}) · niveles ${JSON.stringify(LC.resumen.niveles)}`);

    /* 2c · Fase 4: la matriz nacional. Tunja no tiene archivos por comuna; su
       concejo, su alcaldía y la gobernación del Quindío salen de la matriz, con
       el voto de lista, y los rivales de 2019 del Concejo de Bogotá se leen de
       la matriz de 2019 en vez de bajar el archivo de cada uno. */
    const DIR = { CONC2023: 'concejo-2023', ASAM2023: 'asamblea-2023' };
    const caso = async (slug, partido, corp, corpHist, extra = {}) => {
      const ms = (await json(`${S3}/${DIR[slug.split('-')[0]]}/${slug}.json`)).mesas;
      const camp = Object.assign({ corp, ruta: 'same', avales: 'partido', partido, departamento: '', municipio: '', localidad: '' }, extra);
      const al = await EN.alcanceDe({ campana: camp, corpHistorica: corpHist, mesasPropias: ms, codigoMunicipio: async () => '001' });
      return K.leer({ campana: camp, slugs: [slug], mesasPropias: ms, alcance: al, meta: 0, usuario: { slugs: [slug] }, baseUrl: S3, matrizBase: MATRIZ_BASE });
    };
    const T = await caso('CONC2023-7-1-4-6', 'PARTIDO ALIANZA VERDE', 'concejo', 'concejo');
    ok(T.resumen.puestos === 24, `Tunja · concejo: sus 24 puestos (${T.datos.nacional ? 'matriz nacional' : 'archivo por candidata'})`);
    if (!T.datos.nacional) console.log('  (la matriz nacional no está en S3: los casos de la fase 4 corren por el modo de respaldo; MATRIZ_LOCAL=1 los corre con la matriz del disco)');
    else ok(T.datos.listas.size > 0 && !T.avisos.includes('sin-voto-de-lista'), 'Tunja · la matriz nacional trae el voto de lista');
    const TA = await caso('CONC2023-7-1-4-6', 'PARTIDO ALIANZA VERDE', 'alcaldia', 'concejo', { ruta: 'other', departamento: '07', municipio: 'TUNJA' });
    ok(TA.rivales.length > 0 && TA.rivales.every(r => r.afinidad != null), `Tunja · alcaldía: los ${TA.rivales.length} rivales con afinidad medida`);
    const Q = await caso('ASAM2023-26-5334-51', 'PARTIDO CAMBIO RADICAL', 'gobernacion', 'asamblea', { ruta: 'other', departamento: '26', departamentoNombre: 'QUINDÍO' });
    ok(Q.resumen.puestos > 100 && new Set([...Q.datos.validos.keys()].map(k => k.slice(2, 5))).size === 12, `Quindío · gobernación: el archivo del departamento trae los 12 municipios (${Q.resumen.puestos} puestos)`);
    const conAf = LC.rivales.filter(r => r.fuentes.includes('C') && r.afinidad != null && /2019/.test(r.corp)).length;
    console.log(`  Concejo de Bogotá · rivales de 2019 con afinidad medida: ${conAf}`);
    if (T.datos.nacional) ok(conAf >= 20, `Concejo de Bogotá · ${conAf} rivales de 2019 con afinidad, leídos de la matriz de 2019 sin bajar su archivo`);
  } catch (e) {
    ok(false, `real · no se pudo leer S3 (${e.message}); correr con --sin-red para solo la lógica`);
    console.error(e);
  }
}

console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en orden');
process.exit(fallas ? 1 : 0);
