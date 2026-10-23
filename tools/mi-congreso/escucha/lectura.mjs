/* lectura.mjs — la lectura escrita de una captura de redes, con el modelo.
   ------------------------------------------------------------------
   La captura trae cifras y citas (captura.mjs clasifica cada comentario),
   pero nadie dice qué significan juntas. Esto le pide a DeepSeek tres
   párrafos y unas señales, con la regla dura de que solo puede citar y contar
   lo que está en el resumen que se le pasa: nada de actores inventados ni de
   cifras que no estén. Corre en el recolector, no en el navegador: la llave
   no se expone y la página no paga latencia. Si el modelo falla, la captura
   sale sin `lectura` y la página pinta el resumen en cifras que calcula sola.

   Mismo patrón de explica_en_vivo.py (leyes en vivo) y del copiloto del Lab. */

const MODELO = process.env.DEEPSEEK_MODEL || 'deepseek-v4-flash';
const MODELO_URL = process.env.DEEPSEEK_URL || 'https://api.deepseek.com/chat/completions';
export const LECTURA_VERSION = 'v1';

const NOMBRE_RED = { x: 'X', instagram: 'Instagram', tiktok: 'TikTok', facebook: 'Facebook' };
const corta = (s, n) => { const a = Array.from(String(s || '').replace(/\s+/g, ' ').trim()); return a.length > n ? a.slice(0, n - 1).join('') + '…' : a.join(''); };
const sumaPostura = (...cs) => cs.filter(Boolean).reduce((a, c) => { for (const k of ['a_favor', 'en_contra', 'neutro', 'ataque']) a[k] += (c.postura || {})[k] || 0; a.n += c.n || 0; return a; }, { n: 0, a_favor: 0, en_contra: 0, neutro: 0, ataque: 0 });

/* Totales que sirven para decir qué cambió contra la lectura anterior. */
export function totalesDe(cap) {
  const R = cap?.redes || {}; const t = { publicados: 0, menciones: 0, comentarios: 0, postura: { a_favor: 0, en_contra: 0, neutro: 0, ataque: 0 }, reaccionMax: 0 };
  for (const r of Object.values(R)) {
    t.publicados += (r.publicados || []).length; t.menciones += (r.menciones || []).length;
    for (const c of [r.comentarios, r.comentarios_propios]) if (c && c.n) { t.comentarios += c.n; for (const k in t.postura) t.postura[k] += (c.postura || {})[k] || 0; }
    for (const p of r.publicados || []) t.reaccionMax = Math.max(t.reaccionMax, Number(p.reaccion) || 0);
  }
  return t;
}

/* El resumen que lee el modelo: lo justo para escribir, sin el JSON entero. */
export function resumenDe(cap, previa) {
  const L = [];
  for (const [k, r] of Object.entries(cap.redes || {})) {
    const nom = NOMBRE_RED[k] || k;
    if ((r.estado !== 'ok') && !(r.publicados || []).length) { L.push(`## ${nom}: SIN LECTURA (${r.motivo || r.propias?.motivo || 'sin datos'})`); continue; }
    L.push(`## ${nom}${r.handle ? ` · cuenta @${r.handle}` : ''}`);
    const pub = (r.publicados || []).slice(0, 6);
    if (pub.length) { L.push(`Publicaciones suyas con más reacción (${(r.publicados || []).length} leídas):`); pub.forEach((p, i) => L.push(`  P${i + 1}. [${p.reaccion || 0} reacciones${p.comentarios != null ? `, ${p.comentarios} comentarios` : ''}${p.fecha ? `, ${String(p.fecha).slice(0, 16)}` : ''}] «${corta(p.texto, 220)}»`)); }
    const cp = r.comentarios_propios;
    if (cp && cp.n) { L.push(`Comentarios bajo sus publicaciones: ${cp.n} (a favor ${cp.postura?.a_favor || 0} · en contra ${cp.postura?.en_contra || 0} · neutro ${cp.postura?.neutro || 0} · ataque ${cp.postura?.ataque || 0}; tono: ${Object.entries(cp.tono || {}).map(([a, b]) => `${a} ${b}`).join(', ') || '—'})`); (cp.citas || []).forEach(q => L.push(`  cita (${q.postura}): «${corta(q.texto, 200)}»`)); }
    const men = (r.menciones || []).slice(0, 6);
    if (men.length) { L.push(`Publicaciones de otros sobre sus temas (${(r.menciones || []).length} leídas; menciones por tema: ${Object.entries(r.temas || {}).map(([a, b]) => `«${a}» ${b}`).join(', ') || '—'}):`); men.forEach((m, i) => L.push(`  M${i + 1}. [@${m.autor || '?'}, ${m.reaccion || 0} reacciones] «${corta(m.texto, 200)}»`)); }
    if ((r.amplifican || []).length) L.push(`Cuentas que más mueven esa conversación: ${r.amplifican.slice(0, 5).map(a => `@${a.autor} (${a.veces} publicaciones, ${a.alcance} reacciones)`).join(' · ')}`);
    const c = r.comentarios;
    if (c && c.n) { L.push(`Comentarios en la conversación de sus temas: ${c.n} (a favor ${c.postura?.a_favor || 0} · en contra ${c.postura?.en_contra || 0} · neutro ${c.postura?.neutro || 0} · ataque ${c.postura?.ataque || 0})`); (c.citas || []).forEach(q => L.push(`  cita (${q.postura}): «${corta(q.texto, 200)}»`)); }
  }
  const t = totalesDe(cap);
  L.push(`## Totales de esta lectura: ${t.publicados} publicaciones suyas · ${t.menciones} de otros · ${t.comentarios} comentarios (a favor ${t.postura.a_favor} · en contra ${t.postura.en_contra} · neutro ${t.postura.neutro} · ataque ${t.postura.ataque})`);
  if (previa?.generadoEn && previa.redes) { const p = totalesDe(previa); L.push(`## Lectura anterior (${String(previa.generadoEn).slice(0, 10)}): ${p.publicados} publicaciones suyas · ${p.menciones} de otros · ${p.comentarios} comentarios (a favor ${p.postura.a_favor} · en contra ${p.postura.en_contra} · neutro ${p.postura.neutro} · ataque ${p.postura.ataque})`); }
  return L.join('\n');
}

const SISTEMA = `Eres analista de conversación pública en Colombia y escribes para la oficina de un congresista (el congresista y su UTL). Recibes el resumen de una lectura diaria de sus redes: sus publicaciones, los comentarios que le dejan, y la conversación de otros sobre los temas de sus proyectos. Escribes en español de Colombia, tuteo neutro, dirigido al congresista («tu publicación», «te dicen»), sin voseo ni regionalismos.

REGLAS, en este orden:
1. Solo puedes afirmar lo que está en el resumen. Ninguna cifra que no esté. Ningún actor, medio, partido o hecho que no esté. Si algo no se puede saber con el resumen, no lo digas.
2. Cuando cites, cita TEXTUAL entre comillas latinas «» un fragmento que esté en el resumen, recortado si hace falta, nunca reescrito.
3. La conversación «de sus temas» es de todo el país (y a veces de otros países): no la atribuyas al congresista ni digas que hablan de él salvo que el texto lo nombre.
4. La postura la puso un modelo y se equivoca con el sarcasmo: habla de «lo clasificado como», no de «lo que piensa la gente». Nunca digas «la opinión pública».
5. Una red SIN LECTURA es un fallo de lectura, no ausencia de conversación. Dilo así si la nombras.
6. Nada de recomendaciones de campaña electoral ni de ataques: las señales son de comunicación y de agenda legislativa.

Responde SOLO un objeto JSON, sin texto alrededor, con esta forma:
{"titular": "una frase de máximo 14 palabras que resuma la lectura",
 "lectura": ["párrafo 1: qué publicó y qué rindió más (60-90 palabras)", "párrafo 2: qué le dicen debajo de sus publicaciones y qué se clasificó ahí (60-90 palabras)", "párrafo 3: la conversación de sus temas, quién la mueve y qué tono tiene (60-90 palabras)"],
 "senales": ["2 a 4 frases cortas: qué mirar o qué hacer esta semana en comunicación o agenda, cada una anclada en algo del resumen"],
 "cambio": "una frase sobre qué cambió contra la lectura anterior, o null si no hay lectura anterior"}`;

export async function lecturaDe(cap, previa, llave, { log = () => {} } = {}) {
  if (!llave) throw new Error('sin llave del modelo');
  const resumen = resumenDe(cap, previa);
  const quien = cap.vinculo?.nombre || cap.congresista?.nombre || 'el congresista';
  const user = `Congresista: ${quien}${cap.congresista?.corp ? ` (${cap.congresista.corp === 'SENADO' ? 'Senado' : 'Cámara'})` : ''}. Temas de sus proyectos: ${(cap.vinculo?.temas || []).map(t => `«${t}»`).join(', ') || '—'}. Lectura del ${String(cap.generadoEn).slice(0, 10)}.\n\n${resumen}`;
  log(`▸ lectura con ${MODELO} (${resumen.length} caracteres de resumen)… `);
  const r = await fetch(MODELO_URL, { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${llave}` },
    /* ⚠️ V4 devuelve content VACÍO con finish_reason=length si el techo es corto: el razonamiento se lo come. */
    body: JSON.stringify({ model: MODELO, temperature: 0.3, max_tokens: 8000, messages: [{ role: 'system', content: SISTEMA }, { role: 'user', content: user }] }) });
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`modelo HTTP ${r.status} · ${cuerpo?.error?.message || ''}`);
  const crudo = String(cuerpo.choices?.[0]?.message?.content || '').replace(/^```json\s*|```\s*$/g, '').trim();
  let j = null; try { j = JSON.parse(crudo); } catch { throw new Error(`el modelo no devolvió JSON (${cuerpo.choices?.[0]?.finish_reason || '?'}): ${crudo.slice(0, 120)}`); }
  if (!j || !Array.isArray(j.lectura) || !j.lectura.length || !j.titular) throw new Error('el modelo devolvió un JSON sin lectura');
  const uso = cuerpo.usage || {};
  const usd = ((uso.prompt_tokens || 0) * 0.15 + (uso.completion_tokens || 0) * 0.60) / 1e6;
  log(`${j.lectura.length} párrafos · $${usd.toFixed(4)}\n`);
  return { version: LECTURA_VERSION, modelo: MODELO, generadoEn: new Date().toISOString(), usd,
    titular: String(j.titular).trim(), lectura: j.lectura.map(p => String(p).trim()).filter(Boolean).slice(0, 4),
    senales: (Array.isArray(j.senales) ? j.senales : []).map(s => String(s).trim()).filter(Boolean).slice(0, 5),
    cambio: j.cambio && j.cambio !== 'null' ? String(j.cambio).trim() : null,
    anterior: previa?.generadoEn ? { generadoEn: previa.generadoEn, totales: totalesDe(previa) } : null };
}
