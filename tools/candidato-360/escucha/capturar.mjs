/* capturar.mjs — una lectura de escucha social, de punta a punta.
   ------------------------------------------------------------------
   Es el motor que hay detrás de «Lo que se publica en sus cuentas» en
   candidato-360-escucha.html. Toma el vínculo, arma el perfil (perfil.mjs),
   raspa las dos capas con Apify (apify.mjs), clasifica postura, tema y tono
   con el modelo y escribe UNA captura con el contrato que consume el panel
   (README · «Contrato · GET /c360/captura»).

   Está APAGADO por diseño hasta que se decida encenderlo: no hay cron, no hay
   token en CI, y sin --gastar solo dice qué haría. Encenderlo es (1) correr
   esto dos veces al día con los secretos puestos y (2) dejar la captura donde
   el worker la sirva; la página ya sabe pintarla.

   Uso:
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json              # ensayo
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json --gastar --salida=captura.json
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json --gastar --sin-modelo   # raspa, no clasifica

   Reglas que sostienen esto:
   · Cero resultados NO es «no hay conversación»: sale como `sin_datos` con
     motivo, nunca como cero conversación.
   · La postura es del modelo y el modelo se equivoca con el sarcasmo: cada
     cifra va con sus citas, para que el candidato lea y corrija.
   · Los comentarios no son la localidad: son quienes comentan. El panel lo
     dice; acá se guarda la muestra para que lo pueda decir.                  */

import { writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REDES, COMENTARIOS, plan, planComentarios, referenciaDePost, perfilDeVinculo, cargarVinculo, norm } from './perfil.mjs';
import { tokenApify, AYUDA_TOKEN, clienteApify } from './apify.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const GASTAR = Boolean(args.gastar), SIN_MODELO = Boolean(args['sin-modelo']);
const TOPE = args.tope ? Number(args.tope) : null;
const { vinculo, ruta: rutaVinculo, esEjemplo } = cargarVinculo(args);
const PERFIL = perfilDeVinculo(vinculo, args);

/* ── El modelo: DeepSeek, el mismo que ya usa el worker para validar cuentas.
   La llave sale del entorno o del .env; el modelo se cambia por variable
   porque el nombre exacto lo fija la cuenta, no este archivo. */
async function llaveModelo() {
  if (process.env.DEEPSEEK_API_KEY) return process.env.DEEPSEEK_API_KEY;
  try { const t = await readFile(path.join(AQUI, '..', '..', '..', '.env'), 'utf8'); return (t.match(/^\s*DEEPSEEK_API_KEY\s*=\s*["']?([^"'\s#]+)/m) || [])[1] || null; } catch { return null; }
}
const MODELO = process.env.DEEPSEEK_MODEL || 'deepseek-v4-flash';
const MODELO_URL = process.env.DEEPSEEK_URL || 'https://api.deepseek.com/chat/completions';

/* ── Qué texto tiene un ítem, venga del actor que venga ──────────────────── */
const texto = it => String(it.text || it.caption || it.desc || it.description || it.message || it.content || '').replace(/\s+/g, ' ').trim();
const autor = it => String(it.author?.userName || it.author?.username || it.ownerUsername || it.authorMeta?.name || it.user?.username || it.pageName || it.author || it.username || '').replace(/^@/, '');
const fecha = it => it.createdAt || it.timestamp || it.createTimeISO || it.time || it.date || null;
const propio = (it, handle) => Boolean(handle) && norm(autor(it)) === norm(handle);
const ficha = it => { const r = referenciaDePost(it) || {}; return { texto: texto(it).slice(0, 280), autor: autor(it), fecha: fecha(it), url: r.url || '', reaccion: r.reaccion || 0, comentarios: r.comentarios ?? null }; };

/* Cuántas veces aparece cada tema en un texto, por palabra pelada. Es un
   conteo de menciones, no una clasificación: el modelo hace lo fino. */
function temaDe(t, temas) { const n = norm(t); return temas.filter(tema => n.includes(norm(tema))); }

/* ── Clasificar con el modelo: postura, tema y tono, en lote ──────────────── */
async function clasificar(items, llave, contexto) {
  if (!items.length) return { filas: [], usd: 0 };
  const lote = items.map((it, i) => `${i}\t${it.texto.slice(0, 220)}`).join('\n');
  const sistema = `Eres analista de conversación pública en Colombia. Recibes comentarios y publicaciones de redes sociales sobre la candidatura de ${contexto.nombre || 'un candidato'} a ${contexto.candidato}. Temas de campaña: ${contexto.temas.map(t => `«${t}»`).join(', ') || 'ninguno declarado'}.
Para CADA línea devuelve un objeto JSON con: i (el número), postura (a_favor | en_contra | neutro | ataque — «ataque» es agresión personal, no crítica), tema (uno de los temas de campaña, u "otro"), tono (queja | propuesta | burla | denuncia | apoyo | informativo).
Si no puedes decidir, postura "neutro". El sarcasmo bogotano existe: ante la duda, neutro. Responde SOLO un arreglo JSON, sin texto alrededor.`;
  const r = await fetch(MODELO_URL, { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${llave}` },
    body: JSON.stringify({ model: MODELO, temperature: 0, messages: [{ role: 'system', content: sistema }, { role: 'user', content: lote }] }) });
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`modelo HTTP ${r.status} · ${cuerpo?.error?.message || ''}`);
  const crudo = cuerpo.choices?.[0]?.message?.content || '[]';
  let filas = []; try { filas = JSON.parse(crudo.replace(/^```json|```$/g, '').trim()); } catch { filas = []; }
  const uso = cuerpo.usage || {};
  /* Fuera de pico: 0,15 entrada · 0,60 salida por millón (costos.mjs). */
  const usd = ((uso.prompt_tokens || 0) * 0.15 + (uso.completion_tokens || 0) * 0.60) / 1e6;
  return { filas: Array.isArray(filas) ? filas : [], usd };
}

/* ── La captura ──────────────────────────────────────────────────────────── */
const captura = { ok: true, encendida: true, generadoEn: new Date().toISOString(), modelo: SIN_MODELO ? null : MODELO,
  vinculo: { candidato: PERFIL.candidato, nombre: PERFIL.nombre, temas: PERFIL.temas, escalas: PERFIL.escalas },
  costo: { apifyUsd: 0, modeloUsd: 0 }, redes: {} };

const filasPosts = plan(PERFIL), filasCom = planComentarios(PERFIL, filasPosts);
console.log(`\n═══ CAPTURA · ${PERFIL.candidato} ═══`);
console.log(esEjemplo ? `Vínculo de EJEMPLO (${path.relative(process.cwd(), rutaVinculo)})` : `Vínculo: ${path.relative(process.cwd(), rutaVinculo)}`);
console.log(`Temas: ${PERFIL.temas.map(t => `«${t}»`).join(' · ') || '—'}   Escalas: ${PERFIL.escalas.join(' y ')}`);
for (const f of filasPosts) console.log(`  ${f.etiqueta.padEnd(10)} ${f.motivo ? '— ' + f.motivo : `${f.consultas.length} consultas × ${TOPE ?? f.tope} + comentarios de ${filasCom.find(c => c.red === f.red)?.posts || 0} posts`}`);

if (!GASTAR) { console.log(`\nEnsayo: no se llamó a Apify ni al modelo. Con --gastar se produce la captura completa.\n`); process.exit(0); }

const token = await tokenApify(); if (!token) { console.error('\n' + AYUDA_TOKEN + '\n'); process.exit(1); }
const llave = SIN_MODELO ? null : await llaveModelo();
if (!SIN_MODELO && !llave) { console.error('\nFalta DEEPSEEK_API_KEY (en el entorno o en .env). Para raspar sin clasificar: --sin-modelo\n'); process.exit(1); }
const apify = clienteApify(token);

for (const f of filasPosts) {
  const red = { estado: 'ok', motivo: '', modo: f.modo, handle: PERFIL.cuentas[f.red] || '', paginas: f.red === 'facebook' ? f.consultas : undefined,
    publicados: [], menciones: [], amplifican: [], temas: {}, comentarios: null };
  captura.redes[f.red] = red;
  if (f.motivo) { red.estado = f.red === 'facebook' || PERFIL.temas.length ? 'sin_datos' : 'sin_temas'; red.motivo = f.motivo; continue; }
  process.stdout.write(`\n▸ ${f.etiqueta} · posts… `);
  let items = [];
  try {
    const r = await apify.correr(f.actor, REDES[f.red].input(f.consultas, TOPE ?? f.tope));
    captura.costo.apifyUsd += r.cobrado; items = r.items;
    console.log(`${r.items.length} ítems · $${r.cobrado.toFixed(4)}`);
  } catch (e) { red.estado = 'error'; red.motivo = e.message; console.log(`FALLÓ · ${e.message}`); continue; }
  if (!items.length) { red.estado = 'sin_datos'; red.motivo = 'el actor no devolvió nada: puede ser la red bloqueada o el input con otro nombre de campo, no ausencia de conversación'; continue; }

  const fichas = items.map(ficha).filter(x => x.texto);
  red.publicados = fichas.filter(x => propio(x, red.handle)).sort((a, b) => b.reaccion - a.reaccion).slice(0, 10);
  red.menciones = fichas.filter(x => !propio(x, red.handle)).sort((a, b) => b.reaccion - a.reaccion).slice(0, 30);
  const porAutor = {}; for (const m of red.menciones) if (m.autor) { porAutor[m.autor] = porAutor[m.autor] || { autor: m.autor, veces: 0, alcance: 0 }; porAutor[m.autor].veces++; porAutor[m.autor].alcance += m.reaccion; }
  red.amplifican = Object.values(porAutor).sort((a, b) => b.alcance - a.alcance || b.veces - a.veces).slice(0, 8);
  for (const x of fichas) for (const t of temaDe(x.texto, PERFIL.temas)) red.temas[t] = (red.temas[t] || 0) + 1;

  /* Capa 2: los comentarios de los posts con más reacción, clasificados. */
  const fc = filasCom.find(c => c.red === f.red); if (!fc || fc.motivo) continue;
  const elegidos = items.map(referenciaDePost).filter(Boolean).sort((a, b) => b.reaccion - a.reaccion).slice(0, fc.posts);
  if (!elegidos.length) { red.comentarios = { n: 0, motivo: 'ningún post trajo URL con nombre de campo conocido' }; continue; }
  process.stdout.write(`▸ ${f.etiqueta} · comentarios de ${elegidos.length} posts… `);
  try {
    const r = await apify.correr(fc.actor, COMENTARIOS[f.red].input(elegidos, TOPE ? Math.min(TOPE, fc.tope) : fc.tope));
    captura.costo.apifyUsd += r.cobrado;
    const coms = r.items.map(ficha).filter(x => x.texto);
    console.log(`${coms.length} comentarios · $${r.cobrado.toFixed(4)}`);
    const postura = { a_favor: 0, en_contra: 0, neutro: 0, ataque: 0 }, tono = {}, temas = {};
    if (!SIN_MODELO && coms.length) {
      const { filas, usd } = await clasificar(coms, llave, PERFIL);
      captura.costo.modeloUsd += usd;
      for (const fila of filas) { const c = coms[fila.i]; if (!c) continue; c.postura = fila.postura; c.tema = fila.tema; c.tono = fila.tono; if (postura[fila.postura] != null) postura[fila.postura]++; if (fila.tono) tono[fila.tono] = (tono[fila.tono] || 0) + 1; if (fila.tema) temas[fila.tema] = (temas[fila.tema] || 0) + 1; }
    }
    /* Tres citas, una por postura cuando la hay: la cifra nunca sale sola. */
    const citas = ['en_contra', 'a_favor', 'ataque', 'neutro'].map(p => coms.find(c => c.postura === p)).filter(Boolean).slice(0, 3).map(c => ({ texto: c.texto, postura: c.postura, autor: c.autor, url: c.url }));
    red.comentarios = { n: coms.length, posts: elegidos.length, clasificados: SIN_MODELO ? 0 : coms.filter(c => c.postura).length, postura, tono, temas, citas };
  } catch (e) { red.comentarios = { n: 0, motivo: e.message }; console.log(`FALLÓ · ${e.message}`); }
}

const salida = args.salida ? path.resolve(String(args.salida)) : path.join(AQUI, 'captura.json');
await writeFile(salida, JSON.stringify(captura, null, 2));
console.log(`\nCaptura escrita en ${path.relative(process.cwd(), salida)} · Apify $${captura.costo.apifyUsd.toFixed(4)} · modelo $${captura.costo.modeloUsd.toFixed(4)}\n`);
