/* ═══════════════════════════════════════════════════════════════════════════
   CANDI · la guía de Candidato 360 (20-sep-2026)
   ───────────────────────────────────────────────────────────────────────────
   Candi es la perrita del usuario (Luna) convertida en guía de la plataforma.
   NO es un chat de datos electorales: sabe en qué vista está el usuario y
   explica QUÉ es y QUÉ hacer ahí. Las cifras las da la página, no ella.

   Dos capas, a propósito separadas:

   · La GUÍA (VISTAS, más abajo) es texto nuestro, determinista. Está siempre
     —sin sesión, sin red y sin modelo— y es la versión accesible de lo que
     dice la mascota. La mascota es decorativa: si el atlas no carga, no se
     pierde ni una palabra.
   · Las PREGUNTAS escritas van al worker (POST /c360/candi), que llama al
     modelo con la clave del servidor. Si no hay sesión, cuota o clave, se dice
     exactamente eso: nunca se inventa una respuesta y se la atribuye a nadie.

   Candi ENTRA SOLA al cargar la página (una vez): llega, saluda, se sienta y
   se queda atenta con la cola en un bucle suave (v3 atlética). Abrir o cerrar
   el panel no la hace saludar otra vez: ya está ahí.

   Habla de TÚ. El resto del producto habla de usted a propósito —es la voz
   seria de la plataforma— y ella es la voz cercana; son dos cosas distintas.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const BASE = 'assets/candidato-360/candi/';
  /* La miniatura del botón: la pose SENTADA de la v3 atlética. Las
     coordenadas de la v2 no sirven — es otro atlas y otra grilla. Índice 8 de
     una grilla 4×4 = columna 0, fila 2 → posición 0% 66,6667%. */
  const ATLAS = BASE + 'candi-sentarse-atenta-v3.webp';
  const API = (() => { try { return AUTH_API; } catch { return 'https://rr-auth.reruizc.workers.dev'; } })();

  /* Estados que el MODELO puede pedir. El worker valida contra su propia copia;
     ésta es la del cliente. `saludo` es la entrada y solo la dispara la carga
     de la página, así que un `saludo` pedido por el modelo se ignora.
     `sit_down` e `idle_seated` ya existen, pero son la secuencia local de la
     entrada y no se le piden al modelo: por eso no están acá. La reacción
     `curious` tampoco — está pendiente de documentar y no se conecta aún. */
  const ESTADOS = { saludo: { clip: 'enter_greet', soloAlEntrar: true } };

  /* ─── La guía por vista ──────────────────────────────────────────────────
     Una entrada por pantalla de candidato-360.html. `chips` son preguntas
     sugeridas: rellenan el campo, no se envían solas. */
  const VISTAS = {
    intro: {
      titulo: 'Estás en la portada',
      texto: 'Acá se decide por dónde entrar: si ya fuiste candidato, buscamos tu historial electoral y lo conectamos con la campaña de 2027; si es tu primera candidatura, armamos el punto de partida desde el territorio.',
      chips: ['¿Qué diferencia hay entre las dos rutas?', '¿Qué necesito para empezar?']
    },
    existing: {
      titulo: 'Búsqueda de tu historial',
      texto: 'Escribe tu nombre completo. Buscamos en todas las elecciones que tenemos cargadas —Congreso, asambleas, concejos, JAL, alcaldías y gobernaciones— y te mostramos cada candidatura con su votación. Si apareces varias veces, es la misma persona en años distintos.',
      chips: ['No me encuentro, ¿qué hago?', '¿Qué elecciones tienen cargadas?']
    },
    candidateRoute: {
      titulo: 'Tu campaña de 2027',
      texto: 'Acá defines a qué corporación te lanzas y dónde. Si cambias de corporación, el territorio cambia con ella: tu meta y tu mapa se recalculan con esa nueva escala, no con la de tu elección anterior.',
      chips: ['¿Puedo cambiar de corporación?', '¿Qué pasa si todavía no tengo partido?']
    },
    new: {
      titulo: 'Candidatura nueva',
      texto: 'Sin historial propio, el punto de partida es el territorio: tomamos los resultados de 2023 en el lugar al que aspiras y sobre eso se calcula la meta. Puedes dejar el partido pendiente y elegir por ahora tu familia política.',
      chips: ['¿Por qué me piden las redes?', '¿Puedo seguir sin partido?']
    },
    crm: {
      titulo: 'Tu CRM de campaña',
      texto: 'Arriba, el mapa de dónde estuvo tu votación y la meta que necesitas. Abajo, los módulos: briefing cada tres días, escucha social, arquetipos del territorio, perfil del votante, endoso de aliados y el plan del día de la elección.',
      chips: ['¿De dónde sale mi meta de votos?', '¿Qué hace el briefing?', '¿Para qué sirve el día de la elección?']
    }
  };
  const SIN_VISTA = { titulo: 'Candidato 360', texto: 'Te voy diciendo qué hace cada parte de la plataforma. Pregúntame por lo que estés mirando.', chips: [] };
  const SIN_SESION = 'Para preguntarme por escrito necesito que inicies sesión; así sé de qué campaña estamos hablando. La guía de esta pantalla no depende de eso.';

  /* ─── Lo que Candi sabe de la vista: se lee del DOM, no del estado interno.
     Así nunca le dice al usuario algo distinto de lo que tiene en pantalla. */
  function contexto() {
    const pantalla = document.querySelector('.screen:not(.hidden)');
    const vista = pantalla?.id || '';
    const ctx = { vista };
    const txt = id => document.getElementById(id)?.textContent?.trim() || '';
    if (vista === 'crm') {
      ctx.campana = txt('crmTarget');                                  /* «Candidatura 2027 · Concejo … · Bogotá» */
      const meta = txt('crmVoteNumber'); if (meta && meta !== '—' && meta !== '…') ctx.meta = meta;
      ctx.vitrina = document.getElementById('crm')?.classList.contains('en-vitrina') || false;
    }
    const paso = pantalla?.querySelector('.paso:not(.hidden)[data-paso]');
    if (paso) ctx.paso = paso.dataset.paso;
    try { ctx.sesion = Boolean(SESSION && SESSION.token); ctx.acceso = Boolean(SESSION && SESSION.acceso); } catch { ctx.sesion = false; ctx.acceso = false; }
    return ctx;
  }

  /* El primer nombre, SOLO para saludar en el navegador: no viaja al modelo.
     Se busca donde ya esté (candidatura abierta, wizard, vínculo de la cuenta);
     si no hay ninguno, el saludo va sin nombre y ya. */
  function primerNombre() {
    let n = '';
    try { n = crmCandidate?.nombre || ''; } catch {}
    if (!n) { try { n = NUEVO?.nombre || ''; } catch {} }
    if (!n) { try { n = SESSION?.vinculo?.candidato?.nombre || SESSION?.vinculo?.nuevo?.nombre || ''; } catch {} }
    const p = String(n).trim().split(/\s+/)[0] || '';
    if (p.length < 2 || /\d/.test(p)) return '';
    /* El índice electoral guarda los nombres en MAYÚSCULAS. */
    try { return NOMBRE_BONITO(p); } catch { return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase(); }
  }

  /* ─── Andamiaje ──────────────────────────────────────────────────────── */
  const esc = s => String(s == null ? '' : s).replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  let dock, panel, escena, launcher, globo, log, input, enviar, guia, chips, mascota = null;
  let abierto = false, entroYa = false, enVuelo = false, vistaPintada = '';
  const historial = [];                                    /* {rol, texto} — se manda recortado */

  function montar() {
    dock = document.createElement('div');
    dock.className = 'candi-dock'; dock.id = 'candiDock'; dock.hidden = true;
    dock.style.setProperty('--candi-atlas', `url("${ATLAS}")`);
    dock.innerHTML = `
      <section class="candi-panel" id="candiPanel" role="dialog" aria-labelledby="candiTitulo" hidden>
        <header class="candi-head">
          <div>
            <div class="kicker">Candidato 360</div>
            <h2 id="candiTitulo">Candi</h2>
            <p>Tu guía de la plataforma. Te digo qué hace cada parte y dónde está cada cosa.</p>
          </div>
          <button type="button" class="candi-min" id="candiMin" aria-label="Cerrar el panel de Candi">–</button>
        </header>
        <div class="candi-cuerpo">
          <div class="candi-guia" id="candiGuia"></div>
          <div class="candi-chips" id="candiChips"></div>
          <div class="candi-log" id="candiLog" role="log" aria-live="polite" aria-label="Conversación con Candi"></div>
        </div>
        <div class="candi-pie">
          <form class="candi-form" id="candiForm">
            <label class="hidden" for="candiInput">Pregúntale a Candi</label>
            <input id="candiInput" type="text" autocomplete="off" maxlength="400" placeholder="¿Qué quieres saber de esta pantalla?">
            <button type="submit" id="candiEnviar">Enviar</button>
          </form>
          <p class="candi-nota" id="candiNota"></p>
        </div>
      </section>
      <div class="candi-globo" id="candiGlobo" role="status" hidden>
        <p id="candiGloboTexto"></p>
        <button type="button" class="candi-globo-x" id="candiGloboX" aria-label="Cerrar el saludo de Candi">×</button>
      </div>
      <div class="candi-stage candi-escena" id="candiEscena" aria-hidden="true"></div>
      <button type="button" class="candi-launcher" id="candiLauncher" aria-expanded="false" aria-controls="candiPanel">
        <span class="candi-cara" aria-hidden="true"></span><span class="candi-launcher-txt">Pregúntame</span>
      </button>`;
    document.body.append(dock);
    panel = dock.querySelector('#candiPanel'); escena = dock.querySelector('#candiEscena');
    launcher = dock.querySelector('#candiLauncher'); log = dock.querySelector('#candiLog');
    input = dock.querySelector('#candiInput'); enviar = dock.querySelector('#candiEnviar');
    guia = dock.querySelector('#candiGuia'); chips = dock.querySelector('#candiChips');
    globo = dock.querySelector('#candiGlobo');

    launcher.addEventListener('click', () => abierto ? cerrar({ foco: true }) : abrir());
    dock.querySelector('#candiMin').addEventListener('click', () => cerrar({ foco: true }));
    globo.querySelector('p').addEventListener('click', abrir);
    globo.querySelector('#candiGloboX').addEventListener('click', e => { e.stopPropagation(); ocultarGlobo(); });
    dock.querySelector('#candiForm').addEventListener('submit', e => { e.preventDefault(); preguntar(input.value); });
    /* Escape cierra, pero solo si el foco está adentro: si hay un modal del
       CRM encima, la tecla es suya. */
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || !abierto || !dock.contains(document.activeElement)) return;
      e.stopPropagation(); cerrar({ foco: true });
    });
    /* La guía se repinta al cambiar de pantalla; la animación NO se repite.
       Se observan las cinco pantallas y nada más: dentro del CRM, Leaflet
       cambia clases sin parar y un observador con subtree se dispararía
       miles de veces por sesión. */
    const obsVista = new MutationObserver(() => { if (abierto) pintarGuia(); });
    document.querySelectorAll('.screen').forEach(s => obsVista.observe(s, { attributes: true, attributeFilter: ['class'] }));
    window.addEventListener('pagehide', destruir, { once: true });
  }

  function pintarGuia() {
    const v = contexto().vista;
    if (v === vistaPintada) return;
    vistaPintada = v;
    const g = VISTAS[v] || SIN_VISTA;
    guia.innerHTML = `<h3>${esc(g.titulo)}</h3><p>${esc(g.texto)}</p>`;
    chips.innerHTML = (g.chips || []).map(c => `<button type="button" class="candi-chip">${esc(c)}</button>`).join('');
    chips.querySelectorAll('.candi-chip').forEach(b => b.addEventListener('click', () => { input.value = b.textContent; input.focus(); }));
  }

  /* El pie no promete lo que no hay: sin sesión, solo la guía escrita. */
  function pintarPie() {
    const nota = dock.querySelector('#candiNota');
    let hay = false; try { hay = Boolean(SESSION && SESSION.token); } catch {}
    input.placeholder = hay ? '¿Qué quieres saber de esta pantalla?' : 'Inicia sesión para preguntarme';
    nota.innerHTML = hay
      ? 'Mis respuestas escritas las redacta un modelo. Explico la plataforma; las cifras de tu campaña salen de la página, no de mí.'
      : 'La guía de arriba funciona siempre. Para preguntas escritas, <a href="login.html?next=candidato-360.html">inicia sesión</a>.';
  }

  /* ─── La entrada: una sola vez por carga de la página ────────────────────
     Llega, saluda, se sienta y queda atenta con la cola en bucle suave
     (CandiAtletica, v3). El globo aparece al TERMINAR EL SALUDO, igual que con
     la v2 — y ojo, eso ya no es `candi:complete`: en la v3 ese evento llega a
     los 4,8 s, cuando ya se sentó, así que colgarse de él retrasaba el globo
     1,6 s sin que nadie lo decidiera. El fin del saludo es el paso a
     `sit_down`. Si la animación no avanza (atlas caído, pestaña que nunca se
     mostró), el globo entra igual a los 5 s. */
  function entrar() {
    if (entroYa) return; entroYa = true;
    if (typeof CandiAtletica !== 'function') { fallarAtlas('falta candi-atletica.js'); return mostrarGlobo(); }
    mascota = new CandiAtletica(escena);
    /* Dos señales, y gana la primera. Con animación, `sit_down` (3,2 s) llega
       antes que `candi:complete` (4,8 s). Con MOVIMIENTO REDUCIDO el reproductor
       salta directo al reposo y emite `candi:complete` sin pasar nunca por
       `sit_down`: colgarse solo de `sit_down` dejaba el globo esperando los 5 s
       del respaldo justo a quien no tiene ninguna animación que esperar. */
    let listo = false;
    const red = setTimeout(() => presentarse(), 5000);
    const alEstado = e => { if (e.detail?.state === 'sit_down') presentarse(); };
    function presentarse() {
      if (listo) return; listo = true;
      clearTimeout(red);
      escena.removeEventListener('candi:state', alEstado);
      escena.removeEventListener('candi:complete', presentarse);
      mostrarGlobo();
    }
    escena.addEventListener('candi:state', alEstado);
    escena.addEventListener('candi:state', e => { escena.dataset.estado = e.detail?.state || ''; });
    escena.addEventListener('candi:complete', () => { escena.dataset.estado = 'idle_seated'; });
    escena.addEventListener('candi:reaction-complete', () => { escena.dataset.estado = 'idle_seated'; });
    escena.addEventListener('candi:complete', presentarse);
    escena.addEventListener('candi:complete', montarDescanso, { once: true });
    mascota.play().catch(e => { fallarAtlas(e && e.message); presentarse(); });
  }

  /* ─── El descanso con el hueso rosado ────────────────────────────────────
     Tras 20 s sin actividad, estando atenta, Candi baja del dock, cruza la
     pantalla, recoge su hueso con la boca y se echa (CandiBoneSequence, de
     Astra). Corre en una TIRA del ancho de la ventana, no en el dock: el dock
     mide 250 px y el recorrido tiene que ser de lado a lado. La tira es
     transparente a los clics.
     · Una sola perrita visible: el reproductor oculta la del dock mientras
       camina, y al despertar se queda SENTADA Y ATENTA DONDE ESTÉ (una segunda
       CandiAtletica en la tira), con la del dock escondida. Vuelve al dock al
       abrir el panel o cuando tiene que reaccionar (pensar).
     · No hay clip de regreso: si el siguiente descanso la encuentra ya junto
       al hueso, salta directo a recogerlo; si quedó a mitad de camino, el
       recorrido vuelve a empezar desde el dock.
     · Con el panel abierto no descansa (se está leyendo una respuesta), ni con
       la pantalla tan baja que el dock esconde la escena.
     · La espera, la pestaña oculta, el movimiento reducido y la actividad los
       maneja el propio reproductor; acá solo se limpia lo que se crea. */
  const DESCANSO_MS = 20000;
  const bajito = matchMedia('(max-height:520px)');
  let tira = null, descanso = null, rincon = null;

  function montarDescanso() {
    if (descanso || !mascota || typeof CandiBoneSequence !== 'function') return;
    tira = document.createElement('div');
    tira.className = 'candi-bone-strip'; tira.setAttribute('aria-hidden', 'true');
    document.body.append(tira);
    ajustarSuelo();
    descanso = new CandiBoneSequence(tira, { mascot: mascota, inactivityMs: DESCANSO_MS, activityTarget: document });
    /* Arranca donde está la Candi del dock y con un tamaño parecido, para que
       no se note el cambio de reproductor. El resto del encuadre (registro
       vertical, recortes) es el de Astra, intacto. */
    const layoutBase = descanso.layout.bind(descanso);
    descanso.layout = () => {
      const g = layoutBase();
      const cs = getComputedStyle(mascota.sprite);
      const sw = parseFloat(cs.width) || g.size, der = parseFloat(cs.right) || 0;
      const size = Math.min(210, Math.max(100, sw * 1.1), Math.max(1, g.width - 24));
      const izq = escena.getBoundingClientRect().right - der - sw - tira.getBoundingClientRect().left;
      const start = Math.max(g.margin, Math.min(g.width - size - g.margin, izq + (sw - size) / 2));
      return { ...g, size, start };
    };
    /* El reproductor escucha `candi:state` en SU escenario; la mascota lo emite en el dock. */
    escena.addEventListener('candi:state', reenviarEstado);
    tira.addEventListener('candi:bone-state', alDescanso);
    tira.addEventListener('candi:bone-error', e => console.warn('[Candi] hueso:', e.detail?.message));
    bajito.addEventListener('change', alCambiarAlto);
    addEventListener('resize', alRedimensionar);
    habilitarDescanso();
  }
  const reenviarEstado = e => tira?.dispatchEvent(new CustomEvent('candi:state', { detail: e.detail }));
  function habilitarDescanso() { descanso?.enable(!abierto && !bajito.matches); }
  function alCambiarAlto() { if (bajito.matches) volverAlDock(); habilitarDescanso(); ajustarSuelo(); }

  /* La tira se apoya en la misma línea de suelo que la escena del dock. */
  function ajustarSuelo() {
    if (!tira || escena.hidden) return;
    const r = escena.getBoundingClientRect();
    if (!r.height) return;
    tira.style.setProperty('--candi-suelo', Math.max(0, innerHeight - r.bottom) + 'px');
  }
  function alRedimensionar() {
    ajustarSuelo();
    if (!rincon) return;
    const g = descanso.layout();                   /* girar el teléfono no la deja fuera */
    rincon.x = Math.max(g.margin, Math.min(rincon.x, g.width - g.size - g.margin));
    Object.assign(rincon.el.style, { left: rincon.x + 'px', width: g.size + 'px', height: g.size + 'px' });
  }

  function alDescanso(e) {
    const st = e.detail?.state;
    if (st === 'awake') return despertarDonde();
    if (st === 'walk' && rincon) {
      const g = descanso.layout(), junto = rincon.x <= g.end + 24;
      quitarRincon();
      if (junto) descanso.render(descanso.times.walk);   /* ya está junto al hueso: a recogerlo */
    }
  }
  /* Al despertar, el reproductor devuelve la Candi del dock. Si ya se había
     ido de su sitio, se sienta atenta ahí mismo y la del dock se esconde. */
  function despertarDonde() {
    const x = parseFloat(descanso.actor.style.left), size = parseFloat(descanso.actor.style.width);
    if (!Number.isFinite(x) || !Number.isFinite(size) || abierto || bajito.matches) return;
    if (Math.abs(x - descanso.layout().start) < 24) return;   /* no alcanzó a irse */
    mascota.pause(); mascota.sprite.hidden = true;
    const el = document.createElement('div');
    el.className = 'candi-bone-atenta';
    Object.assign(el.style, { left: x + 'px', width: size + 'px', height: size + 'px' });
    tira.append(el);
    rincon = { el, x, m: new CandiAtletica(el) };
    rincon.m.idle().catch(() => {});
  }
  function quitarRincon() { if (!rincon) return; rincon.m.destroy(); rincon.el.remove(); rincon = null; }
  function volverAlDock() {
    if (descanso?.active) descanso.wake();
    if (!rincon) return;
    quitarRincon();
    if (mascota) { mascota.sprite.hidden = false; mascota.idle().catch(() => {}); }
  }
  function mostrarGlobo() {
    presentada = true;
    if (abierto || globo.dataset.visto === '1') { if (calculando) avisarCalculo(); return; }
    const nombre = primerNombre();
    /* Si la meta todavía se está calculando, el saludo lo dice de una vez: dos
       globos seguidos se leerían como Candi hablando sola. */
    globo.querySelector('#candiGloboTexto').textContent =
      `${nombre ? `¡Hola, ${nombre}!` : '¡Hola!'} Soy Candi, tu estratega de campaña. ` +
      (calculando ? AVISO_CALCULO : 'Pregúntame lo que quieras de la pantalla en la que estés.');
    globo.dataset.aviso = calculando ? 'calculo' : '';
    globo.hidden = false;
    if (calculando) pensarYa();
    clearTimeout(mostrarGlobo._t);
    mostrarGlobo._t = setTimeout(ocultarGlobo, 12000);   /* se presenta y se quita sola */
  }
  function ocultarGlobo() { globo.dataset.visto = '1'; globo.dataset.aviso = ''; globo.hidden = true; clearTimeout(mostrarGlobo._t); }

  /* ─── Mientras se calcula la meta de votos ───────────────────────────────
     La meta tarda (baja índices y reparte curules) y la tarjeta se queda en
     «…». Candi piensa y avisa que se puede seguir explorando, para que la
     espera no se lea como página colgada. Durante la entrada NO interrumpe:
     el aviso va dentro del saludo. Con el panel abierto va como mensaje. El
     clip de pensar es de 6 s y no se repite en bucle (sacaría y guardaría las
     gafas en cada vuelta); el aviso sí se queda hasta que la meta aterriza. */
  const AVISO_CALCULO = '¡Estamos calculando el número de votos! Ve explorando el resto de la página.';
  let calculando = false, presentada = false;
  function avisarCalculo() {
    if (abierto) { burbuja('ella', `<p>${esc(AVISO_CALCULO)}</p>`); pensarYa(); return; }
    globo.querySelector('#candiGloboTexto').textContent = AVISO_CALCULO;
    globo.dataset.aviso = 'calculo';
    globo.hidden = false;
    clearTimeout(mostrarGlobo._t);
    pensarYa();
  }
  function calculo(activo) {
    activo = !!activo;
    if (activo === calculando) return;
    calculando = activo;
    if (activo) { if (presentada) avisarCalculo(); return; }   /* si aún entra, lo dice el saludo */
    if (globo && globo.dataset.aviso === 'calculo') {
      globo.dataset.aviso = '';
      clearTimeout(mostrarGlobo._t);
      mostrarGlobo._t = setTimeout(ocultarGlobo, 1200);       /* lo alcanza a leer y se va */
    }
  }

  /* ─── Abrir, cerrar, desmontar ───────────────────────────────────────── */
  function abrir() {
    abierto = true; ocultarGlobo();
    habilitarDescanso(); volverAlDock();
    dock.classList.add('abierto'); panel.hidden = false;
    launcher.setAttribute('aria-expanded', 'true');
    pintarGuia();
    pintarPie();
    setTimeout(() => input.focus({ preventScroll: true }), 60);
  }
  function cerrar({ foco = false } = {}) {
    abierto = false;
    dock.classList.remove('abierto'); panel.hidden = true;
    launcher.setAttribute('aria-expanded', 'false');
    if (foco) launcher.focus();
    habilitarDescanso();
    /* Ojo: NO se llama pause() acá. Candi vive en la pantalla aunque el panel
       esté cerrado, y el reproductor ya deja de avanzar cuando la pestaña se
       oculta. Pausar acá congelaba la entrada a mitad de camino. */
  }
  function destruir() {
    descanso?.destroy(); descanso = null; quitarRincon(); tira?.remove(); tira = null;
    escena?.removeEventListener('candi:state', reenviarEstado);
    bajito.removeEventListener('change', alCambiarAlto); removeEventListener('resize', alRedimensionar);
    mascota?.destroy(); mascota = null;
  }

  /* La mascota es decorativa: si su imagen falla, el panel sigue completo. */
  function fallarAtlas(msg) {
    escena.hidden = true; dock.classList.add('sin-atlas');
    console.warn('[Candi]', msg || 'atlas no disponible');
  }

  /* ─── Las preguntas escritas ─────────────────────────────────────────── */
  function burbuja(clase, html) {
    const d = document.createElement('div');
    d.className = 'candi-msg ' + clase; d.innerHTML = html;
    log.append(d); d.scrollIntoView({ block: 'nearest' });
    return d;
  }
  const parrafos = t => String(t).split(/\n{2,}/).map(p => `<p>${esc(p.trim()).replace(/\n/g, '<br>')}</p>`).join('');

  async function preguntar(texto) {
    const q = String(texto || '').trim();
    if (!q || enVuelo) return;
    let token = null; try { token = SESSION?.token || null; } catch {}
    input.value = '';
    burbuja('yo', parrafos(q));
    /* Sin sesión no hay a quién cobrarle la pregunta: se dice acá y no se
       gasta un viaje al worker para que él responda lo mismo con un 401. */
    if (!token) return sinRespuesta(SIN_SESION, `<a href="login.html?next=candidato-360.html">Iniciar sesión</a>`);
    enVuelo = true; enviar.disabled = true;
    const esperando = burbuja('ella', '<span class="candi-puntos" role="status" aria-label="Candi está pensando"><i></i><i></i><i></i></span>');
    try {
      const r = await fetch(`${API}/c360/candi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ pregunta: q, contexto: contexto(), historial: historial.slice(-6) })
      });
      let data = null; try { data = await r.json(); } catch {}
      esperando.remove();
      if (r.status === 401) return sinRespuesta(SIN_SESION, `<a href="login.html?next=candidato-360.html">Iniciar sesión</a>`);
      if (r.status === 404) return sinRespuesta('Todavía no puedo responder preguntas escritas: falta desplegar mi conexión. La guía de cada pantalla sí funciona.');
      if (r.status === 429) return sinRespuesta(data?.error || 'Por hoy se acabaron las preguntas de esta cuenta. La guía de cada pantalla sigue disponible.');
      if (!r.ok || !data || data.ok === false || !data.respuesta) return sinRespuesta(data?.error || `No pude responder (HTTP ${r.status}). La guía de cada pantalla sigue disponible.`);
      burbuja('ella', parrafos(data.respuesta));
      historial.push({ rol: 'usuario', texto: q }, { rol: 'candi', texto: data.respuesta });
      aplicarEstado(data.estado);
    } catch (e) {
      esperando.remove();
      sinRespuesta('No pude conectarme para responder eso. La guía de cada pantalla sigue disponible aquí arriba.');
    } finally { enVuelo = false; enviar.disabled = false; input.focus({ preventScroll: true }); }
  }
  /* Nunca se rellena el hueco con una respuesta inventada: se dice qué falta. */
  function sinRespuesta(motivo, extra) { burbuja('falla', `<p>${esc(motivo)}</p>${extra ? `<p>${extra}</p>` : ''}`); }

  /* El modelo puede pedir un estado de animación; se valida contra ESTADOS y
     se ignora lo que no exista o lo que rompa la regla de entrar una sola vez. */
  function aplicarEstado(estado) {
    if (!estado) return;
    const e = ESTADOS[estado];
    if (!e) return console.warn('[Candi] estado no permitido:', estado);
    if (e.soloAlEntrar) return;                         /* pendiente: sit_down / idle_seated */
  }

  /* ─── Arranque ───────────────────────────────────────────────────────────
     Candi entra cuando la pantalla de carga ya se fue: con el preload puesto
     no hay nada que guiar, y su saludo se perdería detrás. */
  function arrancar() {
    montar();
    const preload = document.getElementById('preload');
    const mostrar = () => { dock.hidden = false; entrar(); };
    if (!preload || !preload.classList.contains('active')) return mostrar();
    const obs = new MutationObserver(() => { if (!preload.classList.contains('active')) { obs.disconnect(); mostrar(); } });
    obs.observe(preload, { attributes: true, attributeFilter: ['class'] });
    setTimeout(() => { obs.disconnect(); mostrar(); }, 8000);   /* red de seguridad */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar, { once: true });
  else arrancar();

  /* Para depurar desde la consola; no es API pública. */
  /* ─── Pensando: al abrir un módulo que calcula ───────────────────────────
     Saca las gafas, mira arriba, se le prende el bombillo y vuelve a quedar
     atenta (6 s, v3). Solo con los módulos que abren su cálculo EN la página
     —arquetipos, firmas, endoso y el «por qué» de la meta—: los que llevan a
     otra página la cortarían a la mitad. Nunca durante la entrada, y como
     mucho una vez cada 20 s: una mascota que piensa a cada clic deja de decir
     algo. `curious` sigue sin conectar: no está decidido cuándo va. */
  const PIENSA_EN = '#crmArqBtn, #crmFirmasBtn, #crmEndosoBtn, .meta-i';
  let ultimaVez = 0;
  function pensar() {
    const ahora = Date.now(); if (ahora - ultimaVez < 20000) return;
    pensarYa();
  }
  /* Sin el tope de 20 s: lo usa el aviso de cálculo, que es un hecho y no un clic. */
  function pensarYa() {
    if (!mascota || typeof mascota.thinking !== 'function') return;
    volverAlDock();                               /* para reaccionar vuelve a su sitio */
    const estado = escena.dataset.estado;
    if (estado === 'thinking') return;                             /* ya está en eso */
    if (estado !== 'idle_seated') {                                /* no interrumpe la entrada */
      if (!pensarYa._espera) {
        pensarYa._espera = true;
        escena.addEventListener('candi:complete', () => { pensarYa._espera = false; if (calculando) pensarYa(); }, { once: true });
      }
      return;
    }
    ultimaVez = Date.now();
    mascota.thinking().catch(e => console.warn('[Candi] pensando:', e && e.message));
  }
  document.addEventListener('click', e => { if (e.target.closest?.(PIENSA_EN)) pensar(); });

  window.Candi = { abrir, cerrar, entrar, pensar, calculo, get mascota() { return mascota; }, get descanso() { return descanso; }, contexto, primerNombre };
})();
