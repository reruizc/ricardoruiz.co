/* apify.mjs — el cliente de Apify, compartido por el medidor y el recolector.
   ------------------------------------------------------------------
   Una sola forma de hablar con Apify: el token sale del entorno o de un .env
   que ya está en .gitignore y NUNCA se imprime; los errores llegan con el
   mensaje de Apify tal cual («actor not found» y «insufficient credit» piden
   cosas distintas); y el costo de una corrida se lee recorriendo la respuesta
   en busca de campos en dólares, no adivinando un nombre.                    */

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const API = 'https://api.apify.com/v2';

export async function tokenApify() {
  if (process.env.APIFY_TOKEN) return process.env.APIFY_TOKEN;
  try {
    const txt = await readFile(path.join(AQUI, '..', '..', '..', '.env'), 'utf8');
    return (txt.match(/^\s*APIFY_TOKEN\s*=\s*["']?([^"'\s#]+)/m) || [])[1] || null;
  } catch { return null; }
}
export const AYUDA_TOKEN = `Falta el token de Apify. Dos formas, las dos en SU terminal (nunca en el repo ni en un chat):

  1) para esta sesión:      export APIFY_TOKEN=apify_api_xxx
  2) para que quede puesto:  echo 'APIFY_TOKEN=apify_api_xxx' >> .env      (.env ya está en .gitignore)

El token se saca en Apify → Settings → API & Integrations → Personal API token.`;

/* Apify identifica al actor con ~ en vez de / en la URL. */
export const rutaActor = actor => actor.replace('/', '~');
const dormir = ms => new Promise(r => setTimeout(r, ms));

/* Todo campo numérico cuyo nombre hable de dólares, venga donde venga. */
export function camposUSD(obj, prefijo = '', salida = {}) {
  if (!obj || typeof obj !== 'object') return salida;
  for (const [k, v] of Object.entries(obj)) {
    const ruta = prefijo ? `${prefijo}.${k}` : k;
    if (typeof v === 'number' && /usd/i.test(k)) salida[ruta] = v;
    else if (v && typeof v === 'object' && Object.keys(salida).length < 40) camposUSD(v, ruta, salida);
  }
  return salida;
}

export function clienteApify(token, { esperaMax = 300000 } = {}) {
  if (!token) throw new Error('sin token');
  async function api(ruta, opciones = {}) {
    const url = `${API}${ruta}${ruta.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
    const r = await fetch(url, { ...opciones, headers: { 'content-type': 'application/json', ...(opciones.headers || {}) } });
    const txt = await r.text();
    let cuerpo; try { cuerpo = JSON.parse(txt); } catch { cuerpo = { crudo: txt.slice(0, 400) }; }
    if (!r.ok) throw new Error(`HTTP ${r.status} · ${cuerpo?.error?.message || cuerpo?.crudo || ruta.split('?')[0]}`);
    return cuerpo.data ?? cuerpo;
  }
  /* Arranca un actor, espera a que termine y trae su dataset. Se aborta si se
     pasa del tiempo: un actor colgado también cobra. */
  async function correr(actor, entrada) {
    const run = await api(`/acts/${rutaActor(actor)}/runs`, { method: 'POST', body: JSON.stringify(entrada) });
    const inicio = Date.now();
    let estado = run;
    while (['READY', 'RUNNING'].includes(estado.status)) {
      if (Date.now() - inicio > esperaMax) { await api(`/actor-runs/${run.id}/abort`, { method: 'POST' }).catch(() => {}); throw new Error(`se pasó de ${esperaMax / 1000}s y se abortó`); }
      await dormir(4000);
      estado = await api(`/actor-runs/${run.id}`);
    }
    const items = await api(`/datasets/${estado.defaultDatasetId}/items?clean=true&limit=1000`).catch(() => []);
    const costos = camposUSD(estado);
    const cobrado = costos.usageTotalUsd ?? costos['stats.usageTotalUsd'] ?? Math.max(0, ...Object.values(costos));
    return { estado, items: Array.isArray(items) ? items : [], costos, cobrado };
  }
  return { api, correr };
}
