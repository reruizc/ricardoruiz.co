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
   · Las PREGUNTAS escritas van al worker (POST /c360/candi), que llama a
     DeepSeek con la clave del servidor. Si no hay sesión, cuota o clave, se
     dice exactamente eso: nunca se inventa una respuesta y se le atribuye al
     modelo.

   La animación (assets/candidato-360/candi/candi-saludo.js) se reproduce UNA
   vez por apertura del asistente. No se repite con cada respuesta, con cada
   render del CRM ni al cambiar de pestaña del navegador.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const BASE = 'assets/candidato-360/candi/';
  const ATLAS = BASE + 'candi-saludo-atlas-v2-20.webp';   /* 561 KB contra 2,0 MB del PNG; ver candi-saludo.js */
  const API = (() => { try { return AUTH_API; } catch { return 'https://rr-auth.reruizc.workers.dev'; } })();

  /* Estados de animación que existen HOY. El worker valida contra su propia
     copia; ésta es la del cliente. `saludo` es la entrada y solo la dispara la
     apertura del panel, así que un `saludo` pedido por el modelo se ignora:
     la regla «una vez por apertura» manda sobre lo que pida el modelo.
     Cuando existan los clips, acá entran `sit_down` e `idle_seated`. */
  const ESTADOS = { saludo: { clip: 'enter_greet', soloAlAbrir: true } };

  /* ─── La guía por vista ──────────────────────────────────────────────────
     Una entrada por pantalla de candidato-360.html. `chips` son preguntas
     sugeridas: rellenan el campo, no se envían solas. */
  const VISTAS = {
    intro: {
      titulo: 'Está en la portada',
      texto: 'Acá se decide por dónde entrar: si ya fue candidato, buscamos su historial electoral y lo conectamos con la campaña de 2027; si es su primera candidatura, armamos el punto de partida desde el territorio.',
      chips: ['¿Qué diferencia hay entre las dos rutas?', '¿Qué necesito para empezar?']
    },
    existing: {
      titulo: 'Búsqueda de su historial',
      texto: 'Escriba su nombre completo. Buscamos en todas las elecciones que tenemos cargadas —Congreso, asambleas, concejos, JAL, alcaldías y gobernaciones— y le mostramos cada candidatura con su votación. Si aparece varias veces, es la misma persona en años distintos.',
      chips: ['No me encuentro, ¿qué hago?', '¿Qué elecciones tienen cargadas?']
    },
    candidateRoute: {
      titulo: 'Su campaña de 2027',
      texto: 'Acá define a qué corporación se lanza y dónde. Si cambia de corporación, el territorio cambia con ella: su meta y su mapa se recalculan con esa nueva escala, no con la de su elección anterior.',
      chips: ['¿Puedo cambiar de corporación?', '¿Qué pasa si todavía no tengo partido?']
    },
    new: {
      titulo: 'Candidatura nueva',
      texto: 'Sin historial propio, el punto de partida es el territorio: tomamos los resultados de 2023 en el lugar al que aspira y sobre eso se calcula la meta. Puede dejar el partido pendiente y elegir por ahora su familia política.',
      chips: ['¿Por qué me piden las redes?', '¿Puedo seguir sin partido?']
    },
    crm: {
      titulo: 'Su CRM de campaña',
      texto: 'Arriba, el mapa de dónde estuvo su votación y la meta que necesita. Abajo, los módulos: briefing cada tres días, escucha social, arquetipos del territorio, perfil del votante, endoso de aliados y el plan del día de la elección.',
      chips: ['¿De dónde sale mi meta de votos?', '¿Qué hace el briefing?', '¿Para qué sirve el día de la elección?']
    }
  };
  const SIN_SESION = 'Para preguntarme por escrito necesito que inicie sesión; así sé de qué campaña estamos hablando. La guía de esta pantalla no depende de eso.';
  const SIN_VISTA = { titulo: 'Candidato 360', texto: 'Le voy diciendo qué hace cada parte de la plataforma. Pregúnteme por lo que esté mirando.', chips: [] };

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

  /* ─── Andamiaje ──────────────────────────────────────────────────────── */
  const esc = s => String(s == null ? '' : s).replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  let dock, panel, escena, launcher, log, input, enviar, guia, chips, mascota = null;
  let abierto = false, saludoHecho = false, enVuelo = false, vistaPintada = '';
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
            <p>Su guía de la plataforma. Le digo qué hace cada parte y dónde está cada cosa.</p>
          </div>
          <button type="button" class="candi-min" id="candiMin" aria-label="Minimizar a Candi">–</button>
        </header>
        <div class="candi-cuerpo">
          <div class="candi-guia" id="candiGuia"></div>
          <div class="candi-chips" id="candiChips"></div>
          <div class="candi-log" id="candiLog" role="log" aria-live="polite" aria-label="Conversación con Candi"></div>
        </div>
        <div class="candi-pie">
          <form class="candi-form" id="candiForm">
            <label class="hidden" for="candiInput">Pregúntele a Candi</label>
            <input id="candiInput" type="text" autocomplete="off" maxlength="400" placeholder="¿Qué quiere saber de esta pantalla?">
            <button type="submit" id="candiEnviar">Enviar</button>
          </form>
          <p class="candi-nota" id="candiNota">Candi explica la plataforma. Las cifras de su campaña salen de la página, no de ella.</p>
        </div>
      </section>
      <div class="candi-stage candi-escena" id="candiEscena" aria-hidden="true" hidden></div>
      <button type="button" class="candi-launcher" id="candiLauncher" aria-expanded="false" aria-controls="candiPanel" aria-label="Abrir a Candi, su guía de la plataforma" title="Candi, su guía">
        <span class="candi-cara" aria-hidden="true"></span><span class="candi-aviso" aria-hidden="true"></span>
      </button>`;
    document.body.append(dock);
    panel = dock.querySelector('#candiPanel'); escena = dock.querySelector('#candiEscena');
    launcher = dock.querySelector('#candiLauncher'); log = dock.querySelector('#candiLog');
    input = dock.querySelector('#candiInput'); enviar = dock.querySelector('#candiEnviar');
    guia = dock.querySelector('#candiGuia'); chips = dock.querySelector('#candiChips');

    launcher.addEventListener('click', () => abierto ? cerrar() : abrir());
    dock.querySelector('#candiMin').addEventListener('click', () => cerrar({ foco: true }));
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
    input.placeholder = hay ? '¿Qué quiere saber de esta pantalla?' : 'Inicie sesión para preguntarme';
    nota.innerHTML = hay
      ? 'Candi explica la plataforma. Las cifras de su campaña salen de la página, no de ella.'
      : 'La guía de arriba funciona siempre. Para preguntas escritas, <a href="login.html?next=candidato-360.html">inicie sesión</a>.';
  }

  /* ─── Abrir, cerrar, desmontar ───────────────────────────────────────── */
  function abrir() {
    abierto = true;
    dock.classList.add('abierto'); panel.hidden = false; escena.hidden = false;
    launcher.setAttribute('aria-expanded', 'true');
    launcher.setAttribute('aria-label', 'Minimizar a Candi');
    pintarGuia();
    pintarPie();
    reproducirSaludo();
    setTimeout(() => input.focus({ preventScroll: true }), 60);
  }
  function cerrar({ foco = false } = {}) {
    abierto = false;
    dock.classList.remove('abierto'); panel.hidden = true; escena.hidden = true;
    launcher.setAttribute('aria-expanded', 'false');
    launcher.setAttribute('aria-label', 'Abrir a Candi, su guía de la plataforma');
    mascota?.pause();                                   /* el asistente oculto no consume cuadros */
    saludoHecho = false;                                /* «una vez por apertura»: la próxima vez vuelve a entrar */
    if (foco) launcher.focus();
  }
  function destruir() { mascota?.destroy(); mascota = null; }

  /* Una instancia, un saludo por apertura. La escena ya está visible cuando se
     llama: el reproductor mide el ancho del sprite para el recorrido. */
  function reproducirSaludo() {
    if (typeof CandiSaludo !== 'function') return fallarAtlas('No se pudo cargar la animación de Candi.');
    if (!mascota) mascota = new CandiSaludo(escena);
    if (saludoHecho) return;                            /* ya saludó en esta apertura del panel */
    saludoHecho = true;
    mascota.play().catch(e => fallarAtlas(e && e.message));
  }
  /* La mascota es decorativa: si su imagen falla, el panel sigue completo. */
  function fallarAtlas(msg) {
    escena.hidden = true; launcher.classList.add('sin-atlas');
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
        headers: Object.assign({ 'Content-Type': 'application/json' }, token ? { Authorization: `Bearer ${token}` } : {}),
        body: JSON.stringify({ pregunta: q, contexto: contexto(), historial: historial.slice(-6) })
      });
      let data = null; try { data = await r.json(); } catch {}
      esperando.remove();
      if (r.status === 401) return sinRespuesta(SIN_SESION, `<a href="login.html?next=candidato-360.html">Iniciar sesión</a>`);
      if (r.status === 404) return sinRespuesta('Todavía no puedo responder preguntas escritas: falta desplegar mi conexión con el modelo. La guía de cada pantalla sí funciona.');
      if (r.status === 429) return sinRespuesta(data?.error || 'Por hoy se acabaron las preguntas de esta cuenta. La guía de cada pantalla sigue disponible.');
      if (!r.ok || !data || data.ok === false || !data.respuesta) return sinRespuesta(data?.error || `No pude responder (HTTP ${r.status}). La guía de cada pantalla sigue disponible.`);
      burbuja('ella', parrafos(data.respuesta) + '<span class="candi-fuente">Respuesta generada · DeepSeek</span>');
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
     se ignora lo que no exista o lo que rompa la regla de «saludar una vez». */
  function aplicarEstado(estado) {
    if (!estado) return;
    const e = ESTADOS[estado];
    if (!e) return console.warn('[Candi] estado no permitido:', estado);
    if (e.soloAlAbrir) return;                          /* pendiente: sit_down / idle_seated */
  }

  /* ─── Arranque ───────────────────────────────────────────────────────────
     Candi entra cuando la pantalla de carga ya se fue: con el preload puesto
     no hay nada que guiar. */
  function arrancar() {
    montar();
    const preload = document.getElementById('preload');
    const mostrar = () => { dock.hidden = false; };
    if (!preload || !preload.classList.contains('active')) return mostrar();
    const obs = new MutationObserver(() => { if (!preload.classList.contains('active')) { obs.disconnect(); mostrar(); } });
    obs.observe(preload, { attributes: true, attributeFilter: ['class'] });
    setTimeout(() => { obs.disconnect(); mostrar(); }, 8000);   /* red de seguridad */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar, { once: true });
  else arrancar();

  /* Para depurar desde la consola; no es API pública. */
  window.Candi = { abrir, cerrar, get mascota() { return mascota; }, contexto };
})();
