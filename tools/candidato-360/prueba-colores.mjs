/* prueba-colores.mjs — la rampa del mapa según el partido.
   ------------------------------------------------------------------
   El mapa codifica una MAGNITUD (cuántos votos), así que la rampa es de un
   solo tono, de claro a oscuro. Lo que el partido cambia es el tono. Eso
   impone condiciones que se pueden medir, y acá se miden en OKLab —el mismo
   espacio del validador de la guía de visualización— para las 29 bases
   (los partidos con color propio y los seis bloques ideológicos):

     · la claridad baja paso a paso, sin repuntes: si no, el mapa deja de
       leerse como «más oscuro = más votos»;
     · dos pasos consecutivos se distinguen (ΔE ≥ 8);
     · el paso más claro se distingue del gris de «sin votos» (ΔE ≥ 8): si
       no, «pocos votos» y «ningún voto» se ven igual;
     · el paso más oscuro aguanta texto y bordes blancos encima (≥ 4,5:1).

   Y que la asignación haga lo que promete: el partido de la persona manda,
   una coalición hereda el color de la parte que se reconozca, y un movimiento
   sin color propio toma el de su bloque en vez de un tono inventado.

     node tools/candidato-360/prueba-colores.mjs                               */
import { readFileSync } from 'node:fs';

globalThis.window = {};
eval(readFileSync(new URL('../../partidos-bloques.js', import.meta.url), 'utf8'));
const P = globalThis.window.PartidosBloques;

const aLineal = v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
function oklab(hex) {
  const h = String(hex).replace('#', '');
  const [r, g, b] = [0, 2, 4].map(i => aLineal(parseInt(h.slice(i, i + 2), 16) / 255));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
const dE = (a, b) => { const A = oklab(a), B = oklab(b); return Math.hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2]) * 100; };
const relLum = hex => { const h = String(hex).replace('#', ''); const [r, g, b] = [0, 2, 4].map(i => aLineal(parseInt(h.slice(i, i + 2), 16) / 255)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const contraste = (a, b) => { const [hi, lo] = [relLum(a), relLum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };

const fallos = []; let total = 0;
const revisar = (t, ok, detalle) => { total++; console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) { fallos.push(t); if (detalle) console.log('   ', detalle); } };

const bases = [...new Set(Object.values(P.PARTIDO_COLOR).concat(Object.values(P.BLOQUE_COLOR)))];
const rampas = bases.map(b => [b, P.rampaDeColor(b)]);

const noMonotonas = rampas.filter(([, r]) => r.some((c, i) => i && oklab(c)[0] >= oklab(r[i - 1])[0]));
revisar(`las ${bases.length} rampas bajan de claro a oscuro sin repuntes`, noMonotonas.length === 0, noMonotonas.slice(0, 3).map(([b]) => b).join(' '));

const pasos = rampas.map(([b, r]) => [b, Math.min(...r.slice(0, -1).map((c, i) => dE(c, r[i + 1])))]).sort((a, b) => a[1] - b[1]);
revisar(`dos pasos consecutivos se distinguen (peor ΔE ${pasos[0][1].toFixed(1)} ≥ 8)`, pasos[0][1] >= 8, `${pasos[0][0]} → ${P.rampaDeColor(pasos[0][0]).join(' ')}`);

const vsNeutro = rampas.map(([b, r]) => [b, dE(r[0], P.SIN_VOTOS)]).sort((a, b) => a[1] - b[1]);
revisar(`el paso más claro no se confunde con «sin votos» (peor ΔE ${vsNeutro[0][1].toFixed(1)} ≥ 8)`, vsNeutro[0][1] >= 8, vsNeutro[0][0]);

const conBlanco = rampas.map(([b, r]) => [b, contraste(r[3], '#ffffff')]).sort((a, b) => a[1] - b[1]);
revisar(`el paso más oscuro aguanta blanco encima (peor ${conBlanco[0][1].toFixed(1)}:1 ≥ 4,5)`, conBlanco[0][1] >= 4.5, conBlanco[0][0]);

/* ── La asignación ────────────────────────────────────────────────────── */
revisar('el Liberal es rojo y el Conservador azul', P.colorDePartido('PARTIDO LIBERAL COLOMBIANO') === '#C81E1E' && P.colorDePartido('PARTIDO CONSERVADOR COLOMBIANO') === '#1D4ED8');
revisar('el Pacto NO es rojo: chocaba con el Liberal', P.colorDePartido('MOVIMIENTO POLÍTICO PACTO HISTÓRICO') === '#7C3AED');
revisar('los tres azules se distinguen entre sí (ΔE ≥ 8)',
  Math.min(dE(P.colorDePartido('PARTIDO CONSERVADOR COLOMBIANO'), P.colorDePartido('PARTIDO CENTRO DEMOCRATICO')),
    dE(P.colorDePartido('PARTIDO CENTRO DEMOCRATICO'), P.colorDePartido('MOVIMIENTO SALVACIÓN NACIONAL'))) >= 8);
revisar('una coalición hereda el color de la parte que se reconoce', P.colorDePartido('NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA') === '#B45309' && P.colorDePartido('PARTIDO CAMBIO RADICAL - PARTIDO POLITICO MIRA') === '#D5194E');
revisar('un movimiento sin color propio toma el de su bloque, no un tono inventado', P.colorDePartido('PARTIDO POLITICO LA FUERZA DE LA PAZ') === '#65A30D' && P.colorDePartido('MOVIMIENTO NUEVO Y DESCONOCIDO') === P.BLOQUE_COLOR.sc);
revisar('sin partido no hay color: el mapa se queda con el verde de siempre', P.colorDePartido('') === '' && P.rampaDePartido('') === null);

console.log();
console.log(`Muestra · Liberal ${P.rampaDeColor('#C81E1E').join(' ')}`);
console.log(`         Conservador ${P.rampaDeColor('#1D4ED8').join(' ')}`);
console.log(`         Pacto ${P.rampaDeColor('#7C3AED').join(' ')}`);
console.log(`         Alianza Verde ${P.rampaDeColor('#16A34A').join(' ')}`);
console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : `${total} de ${total} pasaron`);
process.exit(fallos.length ? 1 : 0);
