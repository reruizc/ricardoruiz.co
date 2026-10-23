/* recolectar.mjs — la escucha de redes de Mi Congreso, para quien la tenga encendida.
   ------------------------------------------------------------------
   Reusa el motor de Candidato 360 (tools/candidato-360/escucha/captura.mjs:
   Apify para las cuatro redes + DeepSeek para postura, tema y tono) con un
   «vínculo» armado desde cuentas.json en vez del vínculo de una campaña. La
   diferencia con el recolector de Candidato 360 es dónde vive la salida: acá no
   hay cuenta ni worker, Mi Congreso es público y elige a la persona en el
   navegador, así que la lectura se escribe como JSON en el repo
   (mi-congreso-data/escucha/<slug>.json) y GitHub Pages la sirve. La tarjeta y
   la página de redes aparecen SOLO para quien tenga ese archivo.

     node tools/mi-congreso/escucha/recolectar.mjs --dry-run        # plan, sin gastar
     node tools/mi-congreso/escucha/recolectar.mjs                  # corrida real
     node tools/mi-congreso/escucha/recolectar.mjs --solo=maria-lucia-villalba-gomez --forzar
     node tools/mi-congreso/escucha/recolectar.mjs --tope=5         # input de prueba, gasta poco

   Secretos (entorno o .env de la raíz): APIFY_TOKEN, DEEPSEEK_API_KEY.

   Frenos, los mismos del recolector de Candidato 360: una lectura cada ~20 h
   (re-correr el workflow no cobra doble), tope por persona y mes (el gasto va
   dentro del JSON, `gastoMes`), y una lectura VACÍA no pisa la anterior.      */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { capturar, capturaVacia, planDe, llaveModelo, tokenApify } from '../../candidato-360/escucha/captura.mjs';
import { lecturaDe } from './lectura.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(AQUI, '../../..');
const SALIDA = path.join(REPO, 'mi-congreso-data', 'escucha');
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const SECO = Boolean(args['dry-run']), FORZAR = Boolean(args.forzar);
/* --solo-lectura: no raspa nada; vuelve a escribir la lectura sobre la captura
   que ya está en disco (para cambiar el prompt sin pagar Apify). */
const SOLO_LECTURA = Boolean(args['solo-lectura']);
const TOPE = args.tope ? Number(args.tope) : null;
const TOPE_MES = Number(args['tope-mes'] || process.env.MC_ESCUCHA_TOPE_MES_USD || 40);
const HORAS_MIN = Number(args['horas-min'] || 20);
const usd = x => `US$${Number(x || 0).toFixed(2)}`;
const horasDesde = iso => iso ? (Date.now() - new Date(iso).getTime()) / 36e5 : Infinity;
const mesDe = iso => String(iso || '').slice(0, 7);
const espera = ms => new Promise(r => setTimeout(r, ms));

/* El vínculo con la forma que espera perfil.mjs, pero con el territorio ya
   armado: un congresista no tiene campaña de la que derivarlo. `escalas`
   vacías a propósito: para una curul nacional X busca el tema a secas y el
   hashtag #colombia no es conversación de nadie. */
function vinculoDe(nombreElectos, c) {
  const corpLabel = c.corp === 'SENADO' ? 'Senado de la República' : 'Cámara de Representantes';
  return {
    tipo: 'mi-congreso',
    candidato: { nombre: c.nombre || nombreElectos, corp: corpLabel },
    territorio: { corp: c.corp === 'SENADO' ? 'senado' : 'camara', corpLabel, etiqueta: 'Colombia', base: 'Colombia', loc: '', munLimpio: '',
      escalas: Array.isArray(c.escalas) ? c.escalas : [], paginas: Array.isArray(c.paginas) ? c.paginas : [], rol: c.rol || '' },
    escucha: { ideas: c.temas || [], redes: { perfiles: Object.entries(c.cuentas || {}).filter(([, h]) => h).map(([red, handle]) => ({ red, handle, veredicto: 'confirmado', confianza: 100 })) } },
  };
}

const cfg = JSON.parse(await readFile(path.join(AQUI, 'cuentas.json'), 'utf8'));
const entradas = Object.entries(cfg.congresistas || {}).filter(([, c]) => !args.solo || c.slug === String(args.solo));
console.log(`\n═══ ESCUCHA DE REDES · MI CONGRESO · ${new Date().toISOString().slice(0, 16)} ═══`);
console.log(`${entradas.length} con escucha encendida · tope ${usd(TOPE_MES)} por persona al mes${SECO ? ' · ENSAYO (no gasta)' : ''}${TOPE ? ` · tope de prueba ${TOPE} por consulta` : ''}\n`);
if (!entradas.length) { console.log('Nadie en cuentas.json (o el --solo no casa con ningún slug).'); process.exit(0); }

let token = null, llave = null;
if (!SECO) {
  token = await tokenApify(); llave = await llaveModelo();
  if (!token && !SOLO_LECTURA) { console.error('Falta APIFY_TOKEN'); process.exit(1); }
  if (!llave) { console.error('Falta DEEPSEEK_API_KEY'); process.exit(1); }
}
await mkdir(SALIDA, { recursive: true });

let fallos = 0, escritos = 0;
for (const [nombreElectos, c] of entradas) {
  if (!c.slug) { console.log(`· ${nombreElectos}: sin slug, se salta`); continue; }
  const archivo = path.join(SALIDA, `${c.slug}.json`);
  let previa = null; try { previa = JSON.parse(await readFile(archivo, 'utf8')); } catch {}
  const vinculo = vinculoDe(nombreElectos, c);
  const { PERFIL, filasPosts, filasCom } = planDe(vinculo);
  console.log(`· ${PERFIL.nombre} · ${PERFIL.candidato} · cuentas: ${Object.entries(PERFIL.cuentas).map(([r, h]) => `${r} @${h}`).join(', ') || 'ninguna'}`);
  console.log(`  temas: ${PERFIL.temas.map(t => `«${t}»`).join(' · ') || '—'}`);
  for (const f of filasPosts) console.log(`  ${f.etiqueta.padEnd(10)} ${f.motivo ? '— ' + f.motivo : `${f.consultas.length} consultas × ${TOPE ?? f.tope}${f.propio ? ` + ${f.propio} propias` : ''} + comentarios de ${filasCom.find(x => x.red === f.red)?.posts || 0} posts`}`);
  const gastoMes = previa?.gastoMes && previa.gastoMes.mes === mesDe(new Date().toISOString()) ? previa.gastoMes : { mes: mesDe(new Date().toISOString()), usd: 0, lecturas: 0 };
  if (SOLO_LECTURA) {
    if (!previa) { console.log('  no hay captura en disco sobre la cual escribir\n'); continue; }
    try {
      previa.lectura = await lecturaDe(previa, previa.lectura?.anterior ? { generadoEn: previa.lectura.anterior.generadoEn, redes: null } : null, llave, { log: s => process.stdout.write('  ' + s) });
      gastoMes.usd += previa.lectura.usd; previa.gastoMes = gastoMes;
      await writeFile(archivo, JSON.stringify(previa)); escritos++;
      console.log(`  ✓ lectura reescrita en ${path.relative(REPO, archivo)} · «${previa.lectura.titular}»\n`);
    } catch (e) { fallos++; console.log(`  ✗ la lectura falló: ${e.message}\n`); }
    continue;
  }
  if (!FORZAR && horasDesde(previa?.generadoEn) < HORAS_MIN) { console.log(`  ya tiene lectura de hace ${horasDesde(previa.generadoEn).toFixed(1)} h: se salta\n`); continue; }
  const estimado = previa?.costo ? Number(previa.costo.apifyUsd || 0) + Number(previa.costo.modeloUsd || 0) : 1.0;
  if (gastoMes.usd + estimado > TOPE_MES) { console.log(`  tope del mes: lleva ${usd(gastoMes.usd)} de ${usd(TOPE_MES)}\n`); continue; }
  if (SECO) { console.log(`  [ensayo] gastaría ~${usd(estimado)} · lleva ${usd(gastoMes.usd)} este mes\n`); continue; }

  let cap = null;
  for (let intento = 1; intento <= 2 && !(cap && !capturaVacia(cap)); intento++) {
    try {
      cap = await capturar(vinculo, { token, llave, tope: TOPE, log: s => process.stdout.write('  ' + s.replace(/\n(?=.)/g, '\n  ')) });
      gastoMes.usd += cap.costo.apifyUsd + cap.costo.modeloUsd; gastoMes.lecturas++;
      if (capturaVacia(cap)) { console.log(`\n  la lectura vino vacía (intento ${intento})`); if (intento < 2) await espera(60000); }
    } catch (e) { console.log(`\n  falló (intento ${intento}): ${e.message}`); cap = null; if (intento < 2) await espera(60000); }
  }
  if (!cap || capturaVacia(cap)) {
    fallos++; console.log('  ✗ sin lectura útil: se conserva la anterior\n');
    if (previa) { previa.gastoMes = gastoMes; await writeFile(archivo, JSON.stringify(previa)); }
    continue;
  }
  /* Lo que la página necesita para saber de quién es y no pintarle a nadie
     las cuentas de otra persona. `automatica` lo dice el pie de la página. */
  cap.congresista = { nombre: nombreElectos, corp: c.corp, slug: c.slug, cuentas: c.cuentas, verificadas: c.verificadas || '' };
  cap.automatica = Boolean(process.env.GITHUB_ACTIONS);
  /* La lectura escrita: si el modelo falla, la captura sale sin ella y la
     página pinta el resumen en cifras que calcula sola. */
  try { cap.lectura = await lecturaDe(cap, previa, llave, { log: s => process.stdout.write('  ' + s) }); gastoMes.usd += cap.lectura.usd; }
  catch (e) { console.log(`\n  la lectura escrita falló (${e.message}); la captura sale sin ella`); }
  cap.gastoMes = gastoMes;
  await writeFile(archivo, JSON.stringify(cap));
  escritos++;
  console.log(`\n  ✓ ${path.relative(REPO, archivo)} · Apify ${usd(cap.costo.apifyUsd)} · modelo ${usd(cap.costo.modeloUsd)} · ${usd(gastoMes.usd)} en el mes\n`);
}
console.log(`${escritos} lectura${escritos === 1 ? '' : 's'} escrita${escritos === 1 ? '' : 's'}${fallos ? ` · ${fallos} sin lectura útil` : ''}`);
process.exit(fallos && !escritos ? 1 : 0);
