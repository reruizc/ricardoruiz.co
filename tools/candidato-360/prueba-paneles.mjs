/* prueba-paneles.mjs — el panel 04 (escucha social), sin red.
   ------------------------------------------------------------------
   Un HTML propio que trabaja sobre el vínculo de la cuenta y reúne las dos
   mitades de la escucha: la prensa abierta y las cuentas de redes. Acá se
   simula el worker: /c360/me devuelve una candidatura con territorio, la
   acción `medios` del proxy de Caudal devuelve titulares y /c360/redes un
   veredicto. Se comprueba lo que puede romperse de verdad:

     · sin sesión, sin acceso o sin candidatura, el panel dice qué falta en
       vez de mostrarse vacío,
     · al abrir pregunta por las redes, y no lo vuelve a preguntar a quien ya
       contestó —ni a quien tiene cuentas guardadas, ni a quien dijo que no—,
     · decir «todavía no tengo» no cierra la puerta ni frena la prensa,
     · la captura de publicaciones se declara apagada en vez de inventar cifras,
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

async function abrir(pagina, { sesion = true, acceso = true, vinculo = VINCULO, medios = null, redes = null, alGuardar = null, verRedes = false } = {}) {
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
  /* El bloque de cuentas arranca cerrado detrás de la pregunta: quien viene a
     probarlo tiene que contestar que sí, igual que un candidato. */
  if (verRedes && await p.$('#arranqueSi')) {
    await p.click('#arranqueSi');
    await p.waitForSelector('#panelRedes:not(.hidden)');
  }
  return { b, p, errores, consultas, guardados };
}

const fallos = [];
const revisar = (t, ok) => { console.log((ok ? '✓ ' : '✗ ') + t); if (!ok) fallos.push(t); };

/* ── Los muros ─────────────────────────────────────────────────────────── */
for (const [caso, opts, espera, destino] of [
  ['sin sesión', { sesion: false }, /quién es/, /login\.html/],
  ['sin acceso', { acceso: false }, /no tiene acceso/, /comprar=1/],
  /* El botón tiene que llevar a donde se abre una candidatura —la búsqueda—,
     no a la portada: desde ahí parecía que no hubiera hecho nada. */
  ['sin candidatura', { vinculo: null }, /candidatura abierta/, /abrir=1/],
]) {
  const { b, p } = await abrir('candidato-360-escucha.html', opts);
  const muro = await p.textContent('#panelMuro');
  const boton = await p.getAttribute('#panelMuro a.wall-btn', 'href');
  const cuerpoOculto = await p.$eval('#panelCuerpo', e => e.classList.contains('hidden'));
  revisar(`${caso}: dice qué falta y no muestra el panel`, espera.test(muro) && cuerpoOculto);
  revisar(`${caso}: y el botón lleva a donde se resuelve`, destino.test(boton || ''));
  await b.close();
}

/* ── Medios · la conversación del territorio (sin escribir nada) ────────── */
{
  /* La consulta que se le hace a la prensa depende de la CORPORACIÓN: es lo que
     decide si se lee una localidad, un municipio o un departamento. */
  const casos = [
    ['JAL de Teusaquillo', { corp: 'jal', departamentoNombre: 'Distrito Capital de Bogotá', municipio: 'BOGOTÁ, D.C.', localidad: 'TEUSAQUILLO' },
      { escala: /localidad/, etiqueta: /Teusaquillo/, consultas: [/"Teusaquillo" Bogotá/, /"Alcaldía de Bogotá"/, /"Concejo de Bogotá"/] }],
    ['Concejo de Tunja', { corp: 'concejo', departamentoNombre: 'Boyacá', municipio: 'TUNJA' },
      { escala: /municipio/, etiqueta: /Tunja/, consultas: [/"Alcaldía de Tunja"/, /"Concejo de Tunja"/, /"Tunja"/] }],
    ['Gobernación de Boyacá', { corp: 'gobernacion', departamentoNombre: 'Boyacá' },
      { escala: /departamento/, etiqueta: /Boyacá/, consultas: [/"Boyacá"/, /"Gobernación de Boyacá"/, /"Asamblea de Boyacá"/] }],
  ];
  for (const [titulo, campana, espera] of casos) {
    const v = Object.assign(JSON.parse(JSON.stringify(VINCULO)), { campana });
    const { b, p, consultas } = await abrir('candidato-360-escucha.html', { vinculo: v, medios: () => titulares(6) });
    await p.waitForSelector('#territorioLectura .tema');
    const qs = consultas.map(c => c.query);
    revisar(`${titulo}: se lee a la escala correcta`,
      espera.escala.test(await p.textContent('#territorioEscala')) && espera.etiqueta.test(await p.textContent('#territorioTitulo')));
    revisar(`${titulo}: consulta el lugar y a quien lo gobierna`, espera.consultas.every(re => qs.some(q => re.test(q))));
    await b.close();
  }
}
{
  /* El puntaje del briefing: el ruido se cae y lo institucional sube. */
  const conRuido = () => ({ n: 4, por_medio: [], resultados: [
    { titulo: 'El clima en Tunja para este fin de semana', url: 'https://x.co/a', medio: 'Medio', fecha: '2026-09-09' },
    { titulo: 'Resultados de la lotería de Boyacá', url: 'https://x.co/b', medio: 'Medio', fecha: '2026-09-09' },
    { titulo: 'Nada que ver con el territorio', url: 'https://x.co/c', medio: 'Medio', fecha: '2026-09-09' },
    { titulo: 'El Concejo de Tunja aprobó el presupuesto de 2027', url: 'https://x.co/d', medio: 'El Tiempo', fecha: '2026-09-08' },
    { titulo: 'Obra de acueducto avanza en Tunja', url: 'https://x.co/e', medio: 'Boyacá 7 Días', fecha: '2026-09-07' },
    { titulo: 'Alejandra Palacio Restrepo lanza su candidatura', url: 'https://x.co/f', medio: 'Semana', fecha: '2026-09-06' },
  ] });
  const v = Object.assign(JSON.parse(JSON.stringify(VINCULO)), { campana: { corp: 'concejo', departamentoNombre: 'Boyacá', municipio: 'TUNJA' } });
  const { b, p, errores } = await abrir('candidato-360-escucha.html', { vinculo: v, medios: conRuido });
  await p.waitForSelector('#territorioLectura .tema');
  const titulares_ = await p.$$eval('#territorioLectura .tema-titulares li a', n => n.map(x => x.textContent));
  revisar('el clima, la lotería y lo ajeno al territorio no entran',
    !titulares_.some(t => /clima|lotería|Nada que ver/i.test(t)));
  /* Dentro del bloque del territorio (el de «lo nombra a usted» va aparte y antes). */
  const delTerritorio = await p.$$eval('#territorioLectura .tema:last-child .tema-titulares li a', n => n.map(x => x.textContent));
  revisar('lo institucional del municipio sí entra y va de primero', /Concejo de Tunja/.test(delTerritorio[0] || ''));
  const bloques = await p.$$eval('#territorioLectura .tema h3', n => n.map(x => x.textContent));
  revisar('un titular que lo nombra va en su propio bloque, antes del territorio',
    /nombra a usted/.test(bloques[0] || '') && /Tunja/.test(bloques[1] || ''));
  revisar('territorio sin errores de JavaScript', errores.length === 0);
  await p.screenshot({ path: (process.env.SALIDA_PRUEBA || '/tmp') + '/panel-escucha-territorio.png', fullPage: true });
  await b.close();
}
{
  const v = Object.assign(JSON.parse(JSON.stringify(VINCULO)), { campana: { corp: 'concejo', departamentoNombre: 'Boyacá', municipio: 'TUNJA' } });
  const { b, p } = await abrir('candidato-360-escucha.html', { vinculo: v, medios: () => titulares(0) });
  await p.waitForSelector('#territorioLectura .tema.vacio');
  revisar('sin titulares se explica por qué, en vez de dejar el bloque vacío',
    /no publicó nada/.test(await p.textContent('#territorioLectura .tema.vacio')));
  await b.close();
}

/* ── Medios ────────────────────────────────────────────────────────────── */
{
  const porIdea = q => titulares(/acueducto/.test(q) ? 12 : /seguridad/.test(q) ? 40 : 0);
  const { b, p, errores, consultas, guardados } = await abrir('candidato-360-escucha.html', { medios: porIdea });
  revisar('la escucha muestra la candidatura y su territorio', /Alejandra Palacio/.test(await p.textContent('#panelCandidatura')) && /Teusaquillo/.test(await p.textContent('#panelCandidatura')));
  await p.fill('#idea-0', 'acueducto veredal');
  await p.fill('#idea-1', 'seguridad en el comercio');
  await p.fill('#idea-2', 'parque de la 45');
  await p.click('#btnLeer');
  /* `.tema` a secas ya lo satisfacen las tarjetas del territorio: hay que
     esperar las de la lectura de ideas o el assert corre contra una lista
     vacía. */
  await p.waitForSelector('#lectura .tema');
  const deIdeas = consultas.filter(c => /acueducto|seguridad en el comercio|parque de la 45/i.test(c.query));
  revisar('consulta cada idea entre comillas y con el territorio',
    deIdeas.length === 3 && deIdeas.every(c => c.action === 'medios' && /^"/.test(c.query) && c.query.includes('TEUSAQUILLO')));
  const orden = await p.$$eval('#lectura .tema h3', n => n.map(x => x.textContent));
  revisar('ordena por conversación: primero la idea con más titulares', orden[0] === 'seguridad en el comercio' && orden[2] === 'parque de la 45');
  revisar('marca cuál es la de más conversación', (await p.$$('.tema-orden')).length === 1);
  revisar('la idea sin titulares no se esconde: dice que la agenda está libre',
    /no está en la agenda/.test(await p.textContent('#lectura .tema.vacio')));
  revisar('las ideas se guardan', guardados.some(g => JSON.stringify(g.ideas) === '["acueducto veredal","seguridad en el comercio","parque de la 45"]'));
  revisar('cita la fuente y su ventana', /Google News/.test(await p.textContent('.panel-nota')) && /30 días/.test(await p.textContent('.panel-nota')));
  revisar('la prensa sin errores de JavaScript', errores.length === 0);
  await p.screenshot({ path: (process.env.SALIDA_PRUEBA || '/tmp') + '/panel-escucha-prensa.png', fullPage: true });
  await b.close();
}
{
  const { b, p, guardados } = await abrir('candidato-360-escucha.html', { medios: 'falla' });
  await p.fill('#idea-0', 'acueducto veredal');
  await p.click('#btnLeer');
  await p.waitForSelector('#lectura .panel-error');
  revisar('si la prensa se cae, se dice y las ideas quedan guardadas igual',
    /no respondió/.test(await p.textContent('.panel-error')) && guardados.some(g => g.ideas?.length === 1));
  await b.close();
}

/* ── El arranque: la pregunta de redes ─────────────────────────────────── */
{
  const { b, p } = await abrir('candidato-360-escucha.html', { medios: () => titulares(4) });
  revisar('al abrir, pregunta si tiene perfiles en redes',
    /perfiles en redes sociales/.test(await p.textContent('#arranque')) && await p.$eval('#panelRedes', e => e.classList.contains('hidden')));
  revisar('la pregunta nombra las tres redes', /X/.test(await p.textContent('.arranque-redes')) && /TikTok/.test(await p.textContent('.arranque-redes')) && /Instagram/.test(await p.textContent('.arranque-redes')));
  /* La prensa es la mitad que funciona sin configurar nada: no puede quedarse
     esperando a que conteste lo de las redes. */
  await p.waitForSelector('#territorioLectura .tema');
  revisar('la prensa no espera a que conteste lo de las redes', (await p.$$('#territorioLectura .tema')).length > 0);
  await p.click('#arranqueSi');
  await p.waitForSelector('#panelRedes:not(.hidden)');
  revisar('decir que sí abre el bloque de cuentas', (await p.$$('.red-row')).length === 3);
  await b.close();
}
{
  const { b, p } = await abrir('candidato-360-escucha.html');
  await p.click('#arranqueNo');
  await p.waitForSelector('#arranqueAbrir');
  revisar('decir que no deja el bloque cerrado pero no cierra la puerta',
    await p.$eval('#panelRedes', e => e.classList.contains('hidden')) && /Conectar mis redes/.test(await p.textContent('#arranqueAbrir')));
  await p.reload();
  await p.waitForFunction(() => !!window.C360Panel);
  await p.waitForTimeout(400);
  revisar('y no se lo vuelve a preguntar', !(await p.$('#arranqueSi')) && !!(await p.$('#arranqueAbrir')));
  await p.click('#arranqueAbrir');
  await p.waitForSelector('#panelRedes:not(.hidden)');
  revisar('pero puede conectarlas cuando quiera', (await p.$$('.red-row')).length === 3);
  await b.close();
}
{
  const conRedes = JSON.parse(JSON.stringify(VINCULO));
  conRedes.escucha = { redes: { validado: true, validadoEn: '2026-09-01T00:00:00Z', perfiles: [{ red: 'x', handle: 'apalacio', veredicto: 'confirmado', confianza: 90 }] } };
  const { b, p } = await abrir('candidato-360-escucha.html', { vinculo: conRedes });
  revisar('a quien ya tiene cuentas no se le pregunta nada',
    await p.$eval('#arranque', e => e.classList.contains('hidden')) && !(await p.$eval('#panelRedes', e => e.classList.contains('hidden'))));
  revisar('y el estado no dice «sin validar» sobre cuentas ya validadas', /validadas/.test(await p.textContent('#redesEstado')));
  /* Lo que no está conectado se declara: una cifra inventada acá decide qué
     dice la campaña y por dónde. */
  revisar('la captura de publicaciones se declara apagada',
    /Captura no conectada/.test(await p.textContent('#captura')) && /todavía no está montada/.test(await p.textContent('#captura')));
  const cifras = (await p.textContent('#captura')).match(/\d[\d.,]*\s*(publicaciones|menciones|seguidores|interacciones)/i);
  revisar('y no inventa ninguna métrica de redes', cifras === null);
  await b.close();
}
{
  const { b, p } = await abrir('candidato-360-escucha.html', { verRedes: true });
  revisar('sin cuentas, la captura dice que no hay de dónde escuchar',
    /Sin cuentas/.test(await p.textContent('#captura')) && /empieza por saber cuáles son sus cuentas/.test(await p.textContent('#captura')));
  await b.close();
}

/* ── Redes ─────────────────────────────────────────────────────────────── */
{
  const validacion = { ok: true, modelo: 'deepseek-v4-flash', generado_en: '2026-09-08T04:00:00Z', cache_hit: false,
    resumen: 'La identidad que vamos a escuchar es @laprofe en TikTok.', riesgo_homonimo: '', alertas: [], titulares: [],
    perfiles: [{ red: 'tiktok', handle: 'laprofe', url: 'https://www.tiktok.com/@laprofe', veredicto: 'confirmado', confianza: 88, sondeo: 'ok', nombre_perfil: 'Alejandra Palacio', motivo: 'El nombre coincide.' }] };
  const { b, p, errores, guardados } = await abrir('candidato-360-escucha.html', { redes: validacion, verRedes: true });
  await p.click('.red-row[data-red="tiktok"] .red-chip');
  await p.fill('#red-tiktok', 'https://www.tiktok.com/@laprofe?lang=es');
  await p.click('#redesBuscar');
  await p.waitForSelector('.red-ficha');
  revisar('limpia la URL pegada antes de validar', (await p.inputValue('#red-tiktok')) === 'laprofe');
  revisar('pinta el veredicto con su sello', /Confirmado/.test(await p.textContent('.red-sello')));
  revisar('guarda el veredicto en la candidatura',
    guardados.some(g => g.redes?.perfiles?.[0]?.veredicto === 'confirmado' && g.redes.modelo === 'deepseek-v4-flash'));
  revisar('y lo dice', /Guardado/.test(await p.textContent('#redesGuardado')));
  revisar('las redes sin errores de JavaScript', errores.length === 0);
  await p.screenshot({ path: (process.env.SALIDA_PRUEBA || '/tmp') + '/panel-escucha-redes.png', fullPage: true });
  await b.close();
}
{
  const { b, p, guardados } = await abrir('candidato-360-escucha.html', { verRedes: true });   // /c360/redes caído
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
  const { b, p } = await abrir('candidato-360-escucha.html', { vinculo: conRedes });
  revisar('precarga las cuentas ya guardadas',
    (await p.inputValue('#red-instagram')) === 'la.profe' && (await p.$eval('.red-row[data-red="instagram"]', e => e.classList.contains('on'))));
  revisar('y lo dice con su fecha', /2026-09-01/.test(await p.textContent('#redesGuardado')));
  await b.close();
}
{
  const conIdeas = JSON.parse(JSON.stringify(VINCULO));
  conIdeas.escucha = { ideas: ['acueducto veredal', 'seguridad'] };
  const { b, p } = await abrir('candidato-360-escucha.html', { vinculo: conIdeas, medios: () => titulares(5) });
  await p.waitForSelector('#lectura .tema');
  revisar('precarga las ideas guardadas y lee de una', (await p.inputValue('#idea-0')) === 'acueducto veredal' && (await p.$$('#lectura .tema')).length === 2);
  await b.close();
}

console.log();
console.log(fallos.length ? `${fallos.length} fallaron: ${fallos.join(' · ')}` : 'todas pasaron');
process.exit(fallos.length ? 1 : 0);
