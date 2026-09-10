/* prueba-salto.mjs — el reparto de la meta en un salto de corporación, sin mapa.
   ------------------------------------------------------------------
   El motor (candidato-360.js · sección 8 ter) es puro: entra un objeto, sale
   un objeto. Acá se extrae tal cual del archivo y se prueba con una Bogotá de
   cinco localidades. Lo que puede doler:

     · que un salto reparta TODO en el origen (el bug que motivó esto),
     · que sin estudio empírico el origen cobre un bono que nadie midió,
     · que con estudio el origen cobre dos veces (arraigo + su peso en la base),
     · que la cascada partido → bloque → participación caiga donde debe,
     · que la suma dé exactamente la meta.

     node tools/candidato-360/prueba-salto.mjs                                */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const js = await readFile(new URL('../../candidato-360.js', import.meta.url), 'utf8');
const desde = js.indexOf('/* ─── 8 ter.'), hasta = js.indexOf('/* ── El salto en el CRM');
const motor = js.slice(desde, hasta);
const dv = js.slice(js.indexOf('function distributeVotes('), js.indexOf('function projectedVotesByArea('));
const ctx = { window: {}, console };
vm.createContext(ctx);
vm.runInContext(await readFile(new URL('../../partidos-bloques.js', import.meta.url), 'utf8'), ctx);
/* normPalabras vive en la sección 6 bis (partidos); se trae esa línea sola. */
const normPalabrasSrc = js.match(/^const normPalabras = .*$/m)[0];
vm.runInContext(`const PartidosBloques = window.PartidosBloques; ${normPalabrasSrc}\n${dv}\n${motor}\nthis.M = { tipoSalto, proporciones, baseDestino, arraigoEmpirico, repartoSalto, huellaPartido };`, ctx);
const M = ctx.M;

const fallos = [];
const revisar = (t, ok) => { console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) fallos.push(t); };
const suma = o => Object.values(o).reduce((s, v) => s + v, 0);

/* Bogotá de mentiras: 5 localidades, resultados del Concejo 2023 por partido. */
const NL = 'PARTIDO NUEVO LIBERALISMO', PV = 'PARTIDO ALIANZA VERDE', PH = 'PACTO HISTORICO', CD = 'PARTIDO CENTRO DEMOCRATICO';
const porArea = {
  '12': { name: 'BARRIOS UNIDOS', votantes: 60000, partidos: [[NL, 3000], [PV, 4000], [PH, 6000], [CD, 5000]] },
  '02': { name: 'CHAPINERO',      votantes: 70000, partidos: [[NL, 6000], [PV, 8000], [PH, 5000], [CD, 9000]] },
  '11': { name: 'SUBA',           votantes: 400000, partidos: [[NL, 9000], [PV, 20000], [PH, 40000], [CD, 30000]] },
  '08': { name: 'KENNEDY',        votantes: 380000, partidos: [[NL, 2000], [PV, 12000], [PH, 60000], [CD, 20000]] },
  '19': { name: 'CIUDAD BOLIVAR', votantes: 250000, partidos: [[NL, 0],    [PV, 5000],  [PH, 50000], [CD, 8000]] },
};
const propio = { '12': 709 };            /* su JAL: todo en Barrios Unidos */
const meta = 6770;

revisar('JAL → Concejo es un salto a escala de localidad', M.tipoSalto('jal', 'concejo')?.unidad === 'localidad');
revisar('Concejo → Concejo no es salto', M.tipoSalto('concejo', 'concejo') === null);

/* ── La cascada de la base ────────────────────────────────────────────── */
let base = M.baseDestino({ porArea, partido: 'NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', nombreCandidato: 'NATALIA SOPHIA PARRA ROJAS' });
revisar('una coalición se parte y su huella se suma: capa PARTIDO', base.capa === 'partido' && /NUEVO LIBERALISMO/.test(base.etiqueta));
revisar('la huella del partido es donde ese partido votó, no donde vota la gente',
  base.proporciones['02'] > base.proporciones['08'] && base.proporciones['19'] === 0);

base = M.baseDestino({ porArea, partido: 'MOVIMIENTO NUEVO E INEXISTENTE', nombreCandidato: 'ALGUIEN' });
revisar('un partido sin huella cae a PARTICIPACIÓN (no tiene bloque)', base.capa === 'participacion');

const sinNL = Object.fromEntries(Object.entries(porArea).map(([k, d]) => [k, { ...d, partidos: d.partidos.filter(([p]) => p !== NL) }]));
base = M.baseDestino({ porArea: sinNL, partido: 'PARTIDO NUEVO LIBERALISMO', nombreCandidato: 'X' });
revisar('un partido de centro-izquierda que no corrió cae al BLOQUE (verdes)', base.capa === 'bloque' && base.bloque === 'ci');

/* Una lista de coalición cuenta para el partido que la integra: si la persona
   eligió «PARTIDO NUEVO LIBERALISMO», los votos de «NUEVO LIBERALISMO-
   AGRUPACION POLITICA EN MARCHA» son su huella aunque no diga «PARTIDO». */
const conCoalicion = { '12': { votantes: 1, partidos: [['NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA', 700], [PH, 100]] }, '02': { votantes: 1, partidos: [['PARTIDO CAMBIO RADICAL - PARTIDO POLITICO MIRA', 300], [PH, 100]] } };
const hNL = M.huellaPartido(conCoalicion, ['PARTIDO NUEVO LIBERALISMO']);
revisar('la lista de coalición cuenta para el partido que la integra (por sus palabras)', hNL.huella['12'] === 700 && hNL.huella['02'] === 0);
const hCR = M.huellaPartido(conCoalicion, ['PARTIDO CAMBIO RADICAL']);
revisar('y Cambio Radical recoge la lista «Cambio Radical - MIRA»', hCR.huella['02'] === 300 && hCR.huella['12'] === 0);
revisar('pero un partido ajeno no recoge nada', M.huellaPartido(conCoalicion, ['PARTIDO LIBERAL COLOMBIANO']).votos === 0);

/* ── El reparto ───────────────────────────────────────────────────────── */
base = M.baseDestino({ porArea, partido: NL, nombreCandidato: 'X' });
const sinEstudio = M.repartoSalto({ meta, propio, origen: ['12'], base, arraigo: null });
revisar('la suma es exactamente la meta', suma(sinEstudio) === meta);
revisar('ya NO cae todo en el origen', sinEstudio['12'] < meta * .5);
const pesoOrigen = base.proporciones['12'];
revisar('sin estudio el origen pesa lo que pesa en la base: cero bono',
  Math.abs(sinEstudio['12'] / meta - pesoOrigen) < .002);
revisar('y el resto sigue la huella del partido', sinEstudio['11'] > sinEstudio['02'] && sinEstudio['02'] > sinEstudio['08'] && sinEstudio['19'] === 0);

const conEstudio = M.repartoSalto({ meta, propio, origen: ['12'], base, arraigo: .35 });
revisar('con estudio el origen recibe exactamente la fracción medida', Math.abs(conEstudio['12'] / meta - .35) < .002);
revisar('y el resto se reparte fuera, re-normalizado (el origen no cobra dos veces)',
  suma(conEstudio) === meta && Math.abs((conEstudio['11'] / (meta * .65)) - base.proporciones['11'] / (1 - pesoOrigen)) < .002);

/* Origen con varias áreas (Concejo de Tunja → Asamblea: el origen es un
   municipio, pero en JAL→Concejo el origen puede traer dos localidades). */
const propioDoble = { '12': 500, '02': 209 };
const doble = M.repartoSalto({ meta, propio: propioDoble, origen: ['12', '02'], base, arraigo: .4 });
revisar('con dos áreas de origen, la forma interna la pone su huella propia',
  Math.abs((doble['12'] + doble['02']) / meta - .4) < .002 && doble['12'] > doble['02']);

/* ── El arraigo empírico y su mínimo ──────────────────────────────────── */
const tabla = { 'jal>concejo': { '16': { n: 12, arraigo_mediana: .31 }, '5': { n: 2, arraigo_mediana: .9 }, _nacional: { n: 40, arraigo_mediana: .28 } } };
revisar('el departamento manda si tiene casos', M.arraigoEmpirico(tabla, 'jal>concejo', '16')?.valor === .31);
revisar('con pocos casos se cae al nacional', M.arraigoEmpirico(tabla, 'jal>concejo', '05')?.ambito === 'nacional');
revisar('sin estudio para ese salto → null (y el reparto queda sin bono)', M.arraigoEmpirico(tabla, 'concejo>asamblea', '16') === null);

/* ── El lift: el origen pesa X veces su peso en la huella ─────────────── */
const tablaLift = { 'jal>concejo': { _nacional: { n: 40, arraigo_mediana: .28, lift_mediana: 2.5, lift_n: 30 } } };
const ae = M.arraigoEmpirico(tablaLift, 'jal>concejo', '16');
revisar('con suficientes casos el estudio entrega el lift', ae?.lift === 2.5 && ae.ambito === 'nacional');
const conLift = M.repartoSalto({ meta, propio, origen: ['12'], base, arraigo: ae });
revisar('con lift el origen pesa lift × su peso en la huella', Math.abs(conLift['12'] / meta - Math.min(.95, 2.5 * pesoOrigen)) < .002 && suma(conLift) === meta);
revisar('el lift se acota: nunca más del 95 % en el origen', M.repartoSalto({ meta, propio, origen: ['12'], base, arraigo: { valor: .3, lift: 900 } })['12'] / meta <= .951);
revisar('con pocos casos de lift se cae a la fracción cruda',
  M.arraigoEmpirico({ 'jal>concejo': { _nacional: { n: 40, arraigo_mediana: .28, lift_mediana: 2.5, lift_n: 3 } } }, 'jal>concejo', '16')?.lift === null);

/* ── La tabla que viaja con el sitio ──────────────────────────────────── */
const real = JSON.parse(await readFile(new URL('../../candidato-360-data/saltos-arraigo.json', import.meta.url), 'utf8'));
revisar('la tabla publicada trae los tres saltos', ['jal>concejo', 'concejo>asamblea', 'alcaldia>gobernacion'].every(k => real[k]?._nacional?.n > 0));
const bog = M.arraigoEmpirico(real, 'jal>concejo', '16');
revisar('Bogotá tiene casos propios de JAL → Concejo y trae lift', bog?.ambito === 'departamento' && bog.lift > 1);
revisar('cada arraigo publicado es una fracción y cada lift un múltiplo sensato',
  Object.entries(real).filter(([k]) => !k.startsWith('_')).every(([, t]) => Object.values(t).every(r =>
    r.arraigo_mediana >= 0 && r.arraigo_mediana <= 1 && (r.lift_mediana == null || (r.lift_mediana > 0 && r.lift_mediana < 50)))));

console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : 'todas pasaron');
process.exit(fallos.length ? 1 : 0);
