/* prueba-frases.mjs — el punto de partida, dicho como se dice.
   ------------------------------------------------------------------
   «Partimos de JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015 y PARTIDO CAMBIO
   RADICAL» era un registro leído en voz alta. Ahora la tarjeta saluda con lo
   que vio: cuánto hace, a qué se lanzó, a dónde va y con quién, y el tramo
   del partido cambia según el bloque ideológico. Se prueba la función sola,
   con combinaciones reales, y que la frase no cambie entre recargas.

     node tools/candidato-360/prueba-frases.mjs                               */
const { chromium } = await import('playwright')
  .catch(() => import(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright/index.mjs'));
const b = await chromium.launch();
const p = await b.newPage();
const errores = []; p.on('pageerror', e => errores.push(e.message));
await p.route('**', r => r.request().url().startsWith('file://') ? r.continue() : r.abort());
await p.goto('file://' + process.cwd() + '/candidato-360.html');
await p.waitForFunction(() => typeof window.fraseDePartida === 'function');

const frase = args => p.evaluate(a => fraseDePartida(a), args);
const r = {};
r.ricardo = await frase({ candidate: { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', partido: 'PARTIDO CAMBIO RADICAL' }, corpKey: 'concejo', territory: 'BOGOTÁ, D.C. · Bogotá D.C.', campana: { partido: 'PARTIDO CAMBIO RADICAL' } });
r.misma = await frase({ candidate: { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', partido: 'PARTIDO CAMBIO RADICAL' }, corpKey: 'jal', territory: '', campana: { partido: 'PARTIDO CAMBIO RADICAL' } });
r.izquierda = await frase({ candidate: { nombre: 'ALGUIEN', corp: 'CONCEJO · MEDELLIN · 2023', partido: 'PARTIDO ALIANZA VERDE' }, corpKey: 'alcaldia', territory: 'MEDELLÍN · Antioquia', campana: { partido: 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO' } });
r.derecha = await frase({ candidate: { nombre: 'OTRA PERSONA', corp: 'CONCEJO · MEDELLIN · 2023', partido: 'PARTIDO CENTRO DEMOCRÁTICO' }, corpKey: 'alcaldia', territory: 'MEDELLÍN · Antioquia', campana: { partido: 'PARTIDO CENTRO DEMOCRÁTICO' } });
r.congreso = await frase({ candidate: { nombre: 'DANIEL CARVALHO MEJIA', corp: 'CÁMARA · ANTIOQUIA · 2022', partido: 'COALICIÓN CENTRO ESPERANZA', history: [{ corp: 'CÁMARA · ANTIOQUIA · 2022' }, { corp: 'CONCEJO · MEDELLIN · 2019' }, { corp: 'CONCEJO · MEDELLIN · 2015' }] }, corpKey: 'concejo', territory: 'BOGOTÁ, D.C. · Bogotá D.C.', campana: { partido: 'PARTIDO ALIANZA VERDE' } });
/* El caso que lo delató: de una JAL de Bogotá a un concejo de Amazonas. La
   frase no puede hablar de «la ciudad entera» ni hacer como si no se hubiera
   mudado. */
r.mudanza = await frase({ candidate: { nombre: 'RICARDO ESTEBAN RUIZ CASTRO', corp: 'JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015', partido: 'PARTIDO CAMBIO RADICAL' }, corpKey: 'concejo', territory: 'LETICIA · Amazonas', campana: { partido: 'PARTIDO ALIANZA VERDE' } });
r.mismaCorpOtroLugar = await frase({ candidate: { nombre: 'OTRA', corp: 'CONCEJO · MEDELLIN · 2023', partido: 'CREEMOS' }, corpKey: 'concejo', territory: 'CALI · Valle del Cauca', campana: { partido: 'CREEMOS' } });
r.senado = await frase({ candidate: { nombre: 'X', corp: 'SENADO · 2026', partido: 'PARTIDO LIBERAL COLOMBIANO' }, corpKey: 'gobernacion', territory: 'Antioquia', campana: { partido: 'PARTIDO LIBERAL COLOMBIANO' } });
r.estable = (await frase({ candidate: { nombre: 'ALGUIEN', corp: 'CONCEJO · MEDELLIN · 2023', partido: 'PARTIDO ALIANZA VERDE' }, corpKey: 'concejo', territory: '', campana: { partido: 'PARTIDO ALIANZA VERDE' } })) === (await frase({ candidate: { nombre: 'ALGUIEN', corp: 'CONCEJO · MEDELLIN · 2023', partido: 'PARTIDO ALIANZA VERDE' }, corpKey: 'concejo', territory: '', campana: { partido: 'PARTIDO ALIANZA VERDE' } }));
await b.close();

const pruebas = [
  ['dice cuánto hace y a qué se lanzó, sin leer la base de datos', /Vimos que se lanzó a la JAL de Teusaquillo hace 12 años!/.test(r.ricardo) && !/JAL · TEUSAQUILLO/.test(r.ricardo)],
  ['habla en español: «al Concejo», no «a el Concejo», y sin puntos dobles', /se lanzó al Concejo de Medellin/.test(r.mismaCorpOtroLugar) && !/ a el /.test(r.congreso) && !/\.\./.test(r.congreso)],
  ['y a dónde va ahora, con el lugar bonito', /Ahora vamos por el Concejo de Bogotá, D\.C\./.test(r.ricardo)],
  ['el salto de la JAL al Concejo tiene su frase', /De la localidad a la ciudad entera/.test(r.ricardo)],
  ['repetir corporación tiene la suya', /Repetir es la forma más barata/.test(r.misma) && /Ahora vamos por la JAL de Teusaquillo/.test(r.misma)],
  ['el tramo del partido cambia con el bloque: izquierda', /derechos y de barrio|en la calle y en la organización/.test(r.izquierda) && /Pacto Histórico/.test(r.izquierda)],
  ['…y derecha', /orden y resultados|firmeza y con obra/.test(r.derecha) && /Centro Democrático/.test(r.derecha)],
  ['un aval nuevo se nota', /aval nuevo/.test(r.izquierda) && !/aval nuevo/.test(r.derecha)],
  ['con varias candidaturas cuenta cuántas y parte de la última', /3 candidaturas en el historial \(2015, 2019, 2022\)/.test(r.congreso) && /la Cámara por Antioquia hace 5 años/.test(r.congreso) && /Del Congreso al territorio/.test(r.congreso)],
  ['el Senado del año pasado', /al Senado el año pasado/.test(r.senado) && /Gobernación de Antioquia/.test(r.senado)],
  ['de Bogotá a Leticia no habla de «la ciudad entera»', /De una localidad a todo Leticia/.test(r.mudanza) && !/ciudad entera/.test(r.mudanza)],
  ['y dice a dónde va, que es otro municipio', /Ahora vamos por el Concejo de Leticia/.test(r.mudanza)],
  ['repetir corporación en otra ciudad se cuenta como mudanza', /se muda: de Medellin a Cali/.test(r.mismaCorpOtroLugar) && !/forma más barata/.test(r.mismaCorpOtroLugar)],
  ['la frase no cambia entre recargas', r.estable === true],
  ['sin errores de JavaScript', errores.length === 0],
];
for (const [t, ok] of pruebas) console.log(`${ok ? '✓' : '✗'} ${t}`);
const f = pruebas.filter(([, ok]) => !ok).length;
if (f) console.log(JSON.stringify(r, null, 1));
console.log(f ? `\n${f} fallaron` : `\n${pruebas.length} de ${pruebas.length} pasaron`);
process.exit(f ? 1 : 0);
