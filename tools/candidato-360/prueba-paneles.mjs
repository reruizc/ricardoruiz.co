/* prueba-paneles.mjs — los paneles 04 (medios) y 05 (redes), sin red.
   ------------------------------------------------------------------
   Son dos HTML propios que trabajan sobre el vínculo de la cuenta. Acá se
   simula el worker: /c360/me devuelve una candidatura con territorio, la
   acción `medios` del proxy de Caudal devuelve titulares y /c360/redes un
   veredicto. Se comprueba lo que puede romperse de verdad:

     · sin sesión, sin acceso o sin candidatura, cada panel dice qué falta en
       vez de mostrarse vacío,
     · medios consulta la idea ENTRE COMILLAS y con el territorio (sin eso,
       «seguridad» trae el país entero) y ordena por conversación,
     · una idea sin titulares no se esconde: se dice que la agenda está libre,
     · las ideas se guardan aunque la búsqueda se caiga,
     · redes precarga lo ya guardado, valida y guarda el veredicto,
     · «Guardar sin validar» guarda marcado, no en silencio.

     node tools/candidato-360/prueba-paneles.mjs                              */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));

const VINCULO = {
  tipo: 'nuevo',
  nuevo: { nombre: 'Alejandra Palacio Restrepo', nombrePublico: 'La Profe' },
  campana: { corp: 'jal', departamento: '16', departamentoNombre: 'Distrito Capital de Bogotá', municipio: 'BOGOTÁ D.C.', localidad: 'TEUSAQUILLO' },
  escucha: null,
};
const titulares = n => ({ n, por_medio: [{ medio: 'El Espectador' }, { medio: 'Semana' }],
  resultados: Array.from({ length: Math.min(n, 6) }, (_, i) => ({ titulo: `Titular ${i + 1}`, url: 'https://x.co/' + i, medio: 'El Espectador', fecha: '2026-09-0' + (i + 1) })) });

async function abrir(pagina, { sesion = true, acceso = true, vinculo = VINCULO, medios = null, redes = null, alGuardar = null } = {}) {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
  const errores = [], consultas = [], guardados = [];
  p.on('pageerror', e => errores.push(e.message));
  await p.route('**', async route => {
    const u = route.request().url();
    if (u.startsWith('file://')) return route.continue();
    if (u.includes('/c360/me')) return route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ ok: true, acceso, fuente: 'plan', vinculo, email: 'a@b.co', plan: 'c360' }) });
    if (u.includes('/c360/escucha')) {
      const cuerpo = JSON.parse(route.request().postData() || '{}');
      guardados.push(cuerpo);
      if (alGuardar === 'falla') return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ ok: false, error: 'KV caído' }) });
      const v = JSON.parse(JSON.stringify(vinculo || {}));
      v.escucha = Object.assign({}, v.escucha, cuerpo.redes ? { redes: Object.assign({ validado: (cuerpo.redes.perfiles || []).some(x => x.veredicto && x.veredicto !== 'sin_validar') }, cuerpo.redes) } : {}, cuerpo.ideas ? { ideas: cuerpo.ideas } : {});
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, vinculo: v }) });
    }
    if (u.includes('/c360/redes')) return redes
      ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(redes) })
      : route.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ ok: false, error: 'modelo_no_respondio', detalle: 'El modelo no contestó.' }) });
    if (u.includes('/caudal/api')) {
      const cuerpo = JSON.parse(route.request().postData() || '{}');
      consultas.push(cuerpo);
      if (medios === 'falla') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ error: 'la fuente no respondió' }) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(medios ? medios(cuerpo.query) : titulares(0)) });
    }
    return route.abort();
  });
  if (sesion) await p.addInitScript(() => { localStorage.setItem('rr-token', 't'); localStorage.setItem('rr-user', JSON.stringify({ email: 'a@b.co' })); });
  await p.goto('file://' + process.cwd() + '/' + pagina);
  await p.waitForFunction(() => !!window.C360Panel);
  await p.waitForTimeout(400);
  return { b, p, errores, consultas, guardados };
}

const fallos = [];
const revisar = (t, ok) => { console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) fallos.push(t); };

/* ── Los muros ─────────────────────────────────────────────────────────── */
for (const [caso, opts, espera] of [
  ['sin sesión', { sesion: false }, /quién es/],
  ['sin acceso', { acceso: false }, /no tiene acceso/],
  ['sin candidatura', { vinculo: null }, /candidatura abierta/],
]) {
  const { b, p } = await abrir('candidato-360-medios.html', opts);
  const muro = await p.textContent('#panelMuro');
  const cuerpoOculto = await p.$eval('#panelCuerpo', e => e.classList.contains('hidden'));
  revisar(`medios ${caso}: dice qué falta y no muestra el panel`, espera.test(muro) && cuerpoOculto);
  await b.close();
}

/* ── Medios ────────────────────────────────────────────────────────────── */
{
  const porIdea = q => titulares(/acueducto/.test(q) ? 12 : /seguridad/.test(q) ? 40 : 0);
  const { b, p, errores, consultas, guardados } = await abrir('candidato-360-medios.html', { medios: porIdea });
  revisar('medios muestra la candidatura y su territorio', /Alejandra Palacio/.test(await p.textContent('#panelCandidatura')) && /TEUSAQUILLO/.test(await p.textContent('#panelCandidatura')));
  await p.fill('#idea-0', 'acueducto veredal');
  await p.fill('#idea-1', 'seguridad en el comercio');
  await p.fill('#idea-2', 'parque de la 45');
  await p.click('#btnLeer');
  await p.waitForSelector('.tema');
  revisar('consulta cada idea entre comillas y con el territorio',
    consultas.length === 3 && consultas.every(c => c.action === 'medios' && /^"/.test(c.query) && c.query.includes('TEUSAQUILLO')));
  const orden = await p.$$eval('.tema h3', n => n.map(x => x.textContent));
  revisar('ordena por conversación: primero la idea con más titulares', orden[0] === 'seguridad en el comercio' && orden[2] === 'parque de la 45');
  revisar('marca cuál es la de más conversación', (await p.$$('.tema-orden')).length === 1);
  revisar('la idea sin titulares no se esconde: dice que la agenda está libre',
    /no está en la agenda/.test(await p.textContent('.tema.vacio')));
  revisar('las ideas se guardan', guardados.some(g => JSON.stringify(g.ideas) === '["acueducto veredal","seguridad en el comercio","parque de la 45"]'));
  revisar('cita la fuente y su ventana', /Google News/.test(await p.textContent('.panel-nota')) && /30 días/.test(await p.textContent('.panel-nota')));
  revisar('medios sin errores de JavaScript', errores.length === 0);
  await p.screenshot({ path: (process.env.SALIDA_PRUEBA || '/tmp') + '/panel-medios.png', fullPage: true });
  await b.close();
}
{
  const { b, p, guardados } = await abrir('candidato-360-medios.html', { medios: 'falla' });
  await p.fill('#idea-0', 'acueducto veredal');
  await p.click('#btnLeer');
  await p.waitForSelector('.panel-error');
  revisar('si la prensa se cae, se dice y las ideas quedan guardadas igual',
    /no respondió/.test(await p.textContent('.panel-error')) && guardados.some(g => g.ideas?.length === 1));
  await b.close();
}

/* ── Redes ─────────────────────────────────────────────────────────────── */
{
  const validacion = { ok: true, modelo: 'deepseek-v4-flash', generado_en: '2026-09-08T04:00:00Z', cache_hit: false,
    resumen: 'La identidad que vamos a escuchar es @laprofe en TikTok.', riesgo_homonimo: '', alertas: [], titulares: [],
    perfiles: [{ red: 'tiktok', handle: 'laprofe', url: 'https://www.tiktok.com/@laprofe', veredicto: 'confirmado', confianza: 88, sondeo: 'ok', nombre_perfil: 'Alejandra Palacio', motivo: 'El nombre coincide.' }] };
  const { b, p, errores, guardados } = await abrir('candidato-360-redes.html', { redes: validacion });
  await p.click('.red-row[data-red="tiktok"] .red-chip');
  await p.fill('#red-tiktok', 'https://www.tiktok.com/@laprofe?lang=es');
  await p.click('#redesBuscar');
  await p.waitForSelector('.red-ficha');
  revisar('redes limpia la URL pegada antes de validar', (await p.inputValue('#red-tiktok')) === 'laprofe');
  revisar('pinta el veredicto con su sello', /Confirmado/.test(await p.textContent('.red-sello')));
  revisar('guarda el veredicto en la candidatura',
    guardados.some(g => g.redes?.perfiles?.[0]?.veredicto === 'confirmado' && g.redes.modelo === 'deepseek-v4-flash'));
  revisar('y lo dice', /Guardado/.test(await p.textContent('#redesGuardado')));
  revisar('redes sin errores de JavaScript', errores.length === 0);
  await p.screenshot({ path: (process.env.SALIDA_PRUEBA || '/tmp') + '/panel-redes.png', fullPage: true });
  await b.close();
}
{
  const { b, p, guardados } = await abrir('candidato-360-redes.html');   // /c360/redes caído
  await p.click('.red-row[data-red="x"] .red-chip');
  await p.fill('#red-x', '@apalacio');
  await p.click('#redesBuscar');
  await p.waitForSelector('.redes-fallo');
  revisar('si la validación falla, se ofrece guardar sin validar', /sin validar/.test(await p.textContent('.redes-fallo')));
  await p.click('#redesGuardar');
  await p.waitForTimeout(300);
  revisar('guardar sin validar queda marcado como tal',
    guardados.some(g => g.redes?.perfiles?.[0]?.veredicto === 'sin_validar') && /no validadas/.test(await p.textContent('#redesGuardado')));
  await b.close();
}
{
  const conRedes = JSON.parse(JSON.stringify(VINCULO));
  conRedes.escucha = { redes: { validado: true, validadoEn: '2026-09-01T00:00:00Z', perfiles: [{ red: 'instagram', handle: 'la.profe', veredicto: 'probable', confianza: 70 }] }, ideas: ['acueducto veredal'] };
  const { b, p } = await abrir('candidato-360-redes.html', { vinculo: conRedes });
  revisar('redes precarga lo que ya estaba guardado',
    (await p.inputValue('#red-instagram')) === 'la.profe' && (await p.$eval('.red-row[data-red="instagram"]', e => e.classList.contains('on'))));
  revisar('y lo dice con su fecha', /2026-09-01/.test(await p.textContent('#redesGuardado')));
  await b.close();
}
{
  const conIdeas = JSON.parse(JSON.stringify(VINCULO));
  conIdeas.escucha = { ideas: ['acueducto veredal', 'seguridad'] };
  const { b, p } = await abrir('candidato-360-medios.html', { vinculo: conIdeas, medios: () => titulares(5) });
  await p.waitForSelector('.tema');
  revisar('medios precarga las ideas guardadas y lee de una', (await p.inputValue('#idea-0')) === 'acueducto veredal' && (await p.$$('.tema')).length === 2);
  await b.close();
}

console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : 'todas pasaron');
process.exit(fallos.length ? 1 : 0);
