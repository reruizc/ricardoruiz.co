/* recolectar.mjs — la escucha de redes, sola, para todas las cuentas.
   ------------------------------------------------------------------
   Corre en GitHub Actions (`candidato-360-escucha.yml`, una vez al día). Pide al
   worker las cuentas con el módulo de escucha vigente, corre UNA lectura por
   cuenta (captura.mjs, el mismo código del ensayo a mano) y la devuelve al
   worker, que la sirve en GET /c360/captura. Nadie sube nada a mano.

     node tools/candidato-360/escucha/recolectar.mjs --dry-run         # inventario y plan, sin gastar
     node tools/candidato-360/escucha/recolectar.mjs                   # corrida real
     node tools/candidato-360/escucha/recolectar.mjs --solo=correo@x.co --forzar
     node tools/candidato-360/escucha/recolectar.mjs --inventario=inv.json --dry-run   # sin worker

   Secretos (entorno o .env): CAUDAL_ALERTAS_TOKEN (servicio del worker),
   APIFY_TOKEN, DEEPSEEK_API_KEY.

   Frenos, porque cada lectura cuesta plata (~US$0,8 con las 4 redes):
   · Una lectura por cuenta cada ~20 h: re-correr el workflow no cobra doble.
   · Tope por cuenta y por mes (--tope-mes, US$40): el gasto lo lleva el worker
     dentro de la captura (`gastoMes`).
   · Tope por corrida (--tope-corrida, US$25): si la suma estimada lo pasa, las
     cuentas que faltan quedan para mañana y se dice.
   · Una lectura que no trajo NADA (red caída, token vencido) se reintenta una
     vez y, si sigue vacía, NO se guarda: no pisa la última buena.          */

import { readFile, appendFile } from 'node:fs/promises';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { capturar, capturaVacia, planDe, llaveModelo, tokenApify } from './captura.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const SECO = Boolean(args['dry-run']), FORZAR = Boolean(args.forzar);
const WORKER = String(args.worker || process.env.C360_WORKER_URL || 'https://rr-auth.reruizc.workers.dev').replace(/\/$/, '');
const TOPE_MES = Number(args['tope-mes'] || process.env.C360_ESCUCHA_TOPE_MES_USD || 40);
const TOPE_CORRIDA = Number(args['tope-corrida'] || process.env.C360_ESCUCHA_TOPE_CORRIDA_USD || 25);
const HORAS_MIN = Number(args['horas-min'] || 20);
const COSTO_SUPUESTO = 1.0;            // sin lectura previa, se presupuesta US$1
const UA = 'candidato-360-escucha/1.0 (+ricardoruiz.co)';   // a python/node sin UA el bot fight responde 403

async function deEnv(nombre) {
  if (process.env[nombre]) return process.env[nombre];
  try { const t = await readFile(path.join(AQUI, '..', '..', '..', '.env'), 'utf8'); return (t.match(new RegExp(`^\\s*${nombre}\\s*=\\s*["']?([^"'\\s#]+)`, 'm')) || [])[1] || null; } catch { return null; }
}

/* ⚠️ Con el worker NO se usa fetch: el fetch de Node manda `Sec-Fetch-Mode`, la
   huella de navegador que el guarda de servicio rechaza a propósito (y
   responde 404 como si la ruta no existiera). node:http(s) no la pone. */
function pedir(url, { metodo = 'GET', cabeceras = {}, cuerpo = null } = {}) {
  return new Promise((ok, no) => {
    const u = new URL(url), mod = u.protocol === 'http:' ? http : https;
    const datos = cuerpo ? Buffer.from(cuerpo) : null;
    const req = mod.request(u, { method: metodo, headers: { ...cabeceras, ...(datos ? { 'Content-Length': datos.length } : {}) }, timeout: 120000 }, res => {
      const trozos = []; res.on('data', t => trozos.push(t));
      res.on('end', () => ok({ status: res.statusCode, texto: Buffer.concat(trozos).toString('utf8') }));
    });
    req.on('timeout', () => req.destroy(new Error('el worker no respondió en 120 s')));
    req.on('error', no);
    if (datos) req.write(datos);
    req.end();
  });
}

async function worker(ruta, cuerpo) {
  const token = await deEnv('CAUDAL_ALERTAS_TOKEN');
  if (!token || token.length < 24) throw new Error('Falta CAUDAL_ALERTAS_TOKEN (secreto de servicio del worker)');
  const r = await pedir(WORKER + ruta, { metodo: cuerpo ? 'POST' : 'GET', cuerpo: cuerpo ? JSON.stringify(cuerpo) : null,
    cabeceras: { 'X-Caudal-Service': token, 'User-Agent': UA, ...(cuerpo ? { 'Content-Type': 'application/json' } : {}) } });
  let d = {}; try { d = JSON.parse(r.texto); } catch {}
  /* 404 sin detalle = el worker no reconoció el secreto (responde igual que una
     ruta inexistente a propósito) o todavía no tiene la ruta desplegada. */
  if (r.status < 200 || r.status >= 300) throw new Error(`worker ${ruta} HTTP ${r.status}${d.error && r.status !== 404 ? ' · ' + d.error : r.status === 404 ? ' · ¿secreto distinto o ruta sin desplegar?' : ''}`);
  return d;
}

const usd = x => `US$${Number(x || 0).toFixed(2)}`;
const horasDesde = iso => iso ? (Date.now() - new Date(iso).getTime()) / 36e5 : Infinity;
const espera = ms => new Promise(r => setTimeout(r, ms));

const inv = args.inventario ? JSON.parse(await readFile(String(args.inventario), 'utf8')) : await worker('/c360/captura/inventario');
const cuentas = (inv.cuentas || []).filter(c => !args.solo || c.email === String(args.solo).toLowerCase());
const R = inv.resumen || {};
console.log(`\n═══ ESCUCHA AUTOMÁTICA · ${new Date().toISOString().slice(0, 16)} ═══`);
console.log(`Vínculos ${R.total ?? '?'} · con escucha ${R.activas ?? cuentas.length} · sin acceso ${R.sinAcceso ?? 0} · sin el módulo ${R.sinModulo ?? 0} · sin nada que escuchar ${R.sinQueEscuchar ?? 0}`);
console.log(`Topes: ${usd(TOPE_MES)} por cuenta al mes · ${usd(TOPE_CORRIDA)} por corrida${SECO ? ' · ENSAYO (no gasta)' : ''}\n`);

let token = null, llave = null;
if (!SECO) {
  token = await tokenApify();
  llave = await llaveModelo();
  if (!token) { console.error('Falta APIFY_TOKEN'); process.exit(1); }
  if (!llave) { console.error('Falta DEEPSEEK_API_KEY'); process.exit(1); }
}

const filas = [];
let gastado = 0, fallos = 0;
for (const c of cuentas) {
  const estimado = c.ultima?.costo ? Number(c.ultima.costo.apifyUsd || 0) + Number(c.ultima.costo.modeloUsd || 0) : COSTO_SUPUESTO;
  const { PERFIL, filasPosts } = planDe(c.vinculo);
  const redes = filasPosts.filter(f => !f.motivo).map(f => f.etiqueta).join(', ') || 'solo cuentas propias';
  const fila = { email: c.email, quien: PERFIL.candidato, nombre: PERFIL.nombre };
  console.log(`· ${c.email} → ${PERFIL.nombre || '?'} · ${PERFIL.candidato} · ${redes}`);
  if (!FORZAR && horasDesde(c.ultima?.generadoEn) < HORAS_MIN) { console.log(`   ya tiene lectura de hace ${horasDesde(c.ultima.generadoEn).toFixed(1)} h: se salta`); filas.push({ ...fila, estado: 'al día' }); continue; }
  if (c.gastoMes + estimado > TOPE_MES) { console.log(`   tope del mes: lleva ${usd(c.gastoMes)} de ${usd(TOPE_MES)}`); filas.push({ ...fila, estado: 'tope del mes' }); continue; }
  if (gastado + estimado > TOPE_CORRIDA) { console.log(`   tope de la corrida (${usd(gastado)} gastados): queda para mañana`); filas.push({ ...fila, estado: 'tope de la corrida' }); continue; }
  if (SECO) { console.log(`   [ensayo] gastaría ~${usd(estimado)} · lleva ${usd(c.gastoMes)} este mes`); filas.push({ ...fila, estado: 'ensayo', usd: estimado }); continue; }

  let cap = null, intento = 0;
  while (intento < 2) {
    intento++;
    try {
      cap = await capturar(c.vinculo, { token, llave, log: s => process.stdout.write('   ' + s.replace(/\n(?=.)/g, '\n   ')) });
      gastado += cap.costo.apifyUsd + cap.costo.modeloUsd;
      if (!capturaVacia(cap)) break;
      console.log(`\n   la lectura vino vacía (intento ${intento})`);
    } catch (e) { console.log(`\n   falló (intento ${intento}): ${e.message}`); cap = null; }
    if (intento < 2) await espera(60000);
  }
  if (!cap || capturaVacia(cap)) { fallos++; console.log('   ✗ sin lectura útil: se conserva la anterior'); filas.push({ ...fila, estado: 'falló', usd: cap ? cap.costo.apifyUsd + cap.costo.modeloUsd : 0 }); continue; }
  try {
    const r = await worker('/c360/captura/guardar', { email: c.email, captura: cap });
    const costo = cap.costo.apifyUsd + cap.costo.modeloUsd;
    console.log(`\n   ✓ guardada · ${usd(costo)} · en el mes ${usd(r.gastoMes?.usd)} (${r.gastoMes?.lecturas} lecturas)`);
    filas.push({ ...fila, estado: 'guardada', usd: costo, mes: r.gastoMes?.usd });
  } catch (e) { fallos++; console.log(`\n   ✗ no se pudo guardar: ${e.message}`); filas.push({ ...fila, estado: 'no se guardó' }); }
}

console.log(`\nCorrida: ${filas.filter(f => f.estado === 'guardada').length} guardadas · ${fallos} con fallo · ${usd(gastado)} gastados\n`);
if (process.env.GITHUB_STEP_SUMMARY) {
  const md = [`### Escucha automática · ${new Date().toISOString().slice(0, 10)}`, '', `${usd(gastado)} gastados en esta corrida.`, '',
    '| Cuenta | Candidatura | Estado | Costo | En el mes |', '|---|---|---|---|---|',
    ...filas.map(f => `| ${f.email} | ${f.nombre || ''} · ${f.quien} | ${f.estado} | ${f.usd != null ? usd(f.usd) : '—'} | ${f.mes != null ? usd(f.mes) : '—'} |`)].join('\n');
  await appendFile(process.env.GITHUB_STEP_SUMMARY, md + '\n');
}
process.exit(fallos ? 1 : 0);
