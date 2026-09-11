/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · chasis de los paneles (medios y redes)
   ───────────────────────────────────────────────────────────────────────────
   Lo que candidato-360-medios.html y candidato-360-redes.html necesitan por
   igual y no pertenece a ninguna de las dos: sesión, acceso, el vínculo de la
   cuenta (de ahí salen el nombre y el territorio de la campaña), el helper
   contra el worker y el encabezado.

   Cada panel es su propio HTML a propósito. Son dos preguntas distintas —«qué
   dice la prensa de lo suyo» y «cuáles son sus cuentas»— con su propio ritmo:
   una se abre para leer y la otra para configurar. Meterlas en el CRM las
   habría convertido en dos acordeones más de una página que ya es larga.

   ⚠️ Al tocar este archivo hay que bumpear su ?v= en los dos HTML, o el
   navegador sirve la copia vieja sin dar ningún error.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const AUTH_API = (global.RR_RUNTIME_CONFIG && global.RR_RUNTIME_CONFIG.authBase) || 'https://rr-auth.reruizc.workers.dev';
  const CAUDAL_API = `${AUTH_API}/caudal/api`;
  const SOPORTE_POR_DEFECTO = 'hola@ricardoruiz.co';

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const num = n => Number(n || 0).toLocaleString('es-CO');

  const SESION = { token: null, user: null, acceso: false, fuente: 'ninguno', vinculo: null, soporte: SOPORTE_POR_DEFECTO, error: null };

  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (SESION.token) headers.Authorization = `Bearer ${SESION.token}`;
    const r = await fetch(`${AUTH_API}${path}`, Object.assign({}, opts, { headers }));
    let data = null; try { data = await r.json(); } catch {}
    return { status: r.status, ok: r.ok && data?.ok !== false, data: data || {} };
  }
  /* La lectura de prensa pasa por el mismo proxy de Caudal: es la fuente que ya
     alimenta el briefing (Google News RSS del lado del servidor). */
  async function caudal(payload) {
    const headers = { 'Content-Type': 'application/json' };
    if (SESION.token) headers.Authorization = `Bearer ${SESION.token}`;
    const r = await fetch(CAUDAL_API, { method: 'POST', headers, body: JSON.stringify(payload) });
    if (r.status === 429) throw new Error('Demasiadas consultas seguidas. Espere un minuto.');
    const d = await r.json();
    if (d?.error) throw new Error(String(d.error));
    return d;
  }

  /* El territorio se arma con lo que el vínculo guardó de la campaña: es lo que
     hace que la lectura sea de SU municipio y no del país entero. */
  function territorio(v = SESION.vinculo) {
    const c = v?.campana; if (!c) return { texto: '', partes: [] };
    const partes = [c.localidad, c.municipio, c.departamentoNombre].filter(Boolean);
    return { texto: partes.join(' · '), partes, municipio: c.municipio || c.departamentoNombre || '', localidad: c.localidad || '' };
  }
  function nombreCandidatura(v = SESION.vinculo) {
    if (!v) return '';
    return v.tipo === 'nuevo' ? (v.nuevo?.nombre || 'su candidatura') : (v.candidato?.nombre || 'su candidatura');
  }
  function nombrePublico(v = SESION.vinculo) { return v?.tipo === 'nuevo' ? (v.nuevo?.nombrePublico || '') : ''; }


  /* ═══ El territorio de la candidatura ═════════════════════════════════════
     PUERTO FIEL de tools/candidato-360/briefing/motor.py (funciones
     `territorio_de`, `prensa`, `puntaje_local`). Esa es la fuente de verdad: si
     allá cambian las reglas, hay que cambiarlas acá — y al revés.

     Se duplica a propósito. El briefing corre en Python en GitHub Actions y este
     panel corre en el navegador; unificarlos hoy significaría reescribir el
     motor del briefing, que funciona. Lo que sí se gana duplicando con
     fidelidad: lo que el candidato ve en pantalla es EXACTAMENTE lo que le va a
     llegar al correo cada tres días. Una lectura que contradiga al briefing
     valdría menos que no tenerla.

     La escala la manda la corporación, que es la pregunta de fondo:
       · JAL          → su localidad, dentro de la ciudad
       · Concejo      → su municipio (o Bogotá)
       · Alcaldía     → su municipio (o Bogotá)
       · Asamblea     → su departamento
       · Gobernación  → su departamento                                        */
  const CORP_LABEL = { jal: 'Junta Administradora Local', concejo: 'Concejo', alcaldia: 'Alcaldía', asamblea: 'Asamblea Departamental', gobernacion: 'Gobernación' };
  const CORP_DEPARTAMENTAL = new Set(['asamblea', 'gobernacion']);
  const RUIDO_TOK = new Set(['PARA', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'MUNICIPIO', 'DISTRITO', 'CAPITAL', 'SANTA', 'SAN', 'JOSE', 'MARIA', 'LOCALIDAD', 'COMUNA', 'BOGOTA', 'CIUDAD', 'CANDIDATO', 'CANDIDATA']);
  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase();
  const toks = (s, min = 4) => norm(s).split(' ').filter(t => t.length >= min && !RUIDO_TOK.has(t));
  /* La RNEC y el SECOP escriben en MAYÚSCULA SOSTENIDA; en pantalla es un grito. */
  function oracion(s) {
    const t = String(s ?? '').replace(/\s+/g, ' ').trim();
    const letras = [...t].filter(c => /[a-zá-úñ]/i.test(c));
    if (!letras.length || letras.filter(c => c === c.toUpperCase()).length / letras.length < .7) return t;
    return t.slice(0, 1).toUpperCase() + t.slice(1).toLowerCase();
  }

  function territorioDe(v = SESION.vinculo) {
    const c = v?.campana || {};
    let corp = String(c.corp || '').toLowerCase();
    let depNombre = c.departamentoNombre || '', mun = c.municipio || '', loc = c.localidad || '';
    /* Ruta «misma corporación»: la campaña no trae territorio y se deriva del
       corp del historial ("JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015"). */
    if (!mun && !depNombre && v?.candidato) {
      const corpHist = String(v.candidato.corp || '');
      corp = corp || Object.keys(CORP_LABEL).find(k => norm(corpHist).toLowerCase().includes(k)) || '';
      const partes = corpHist.split('·').map(p => p.trim()).filter(p => p && !/^20\d\d$/.test(p));
      if (CORP_DEPARTAMENTAL.has(corp)) depNombre = partes[1] || '';
      else if (corp === 'jal') { loc = loc || partes[1] || ''; mun = partes[2] || ''; }
      else mun = partes[1] || '';
      if (!depNombre && norm(mun).includes('BOGOTA')) depNombre = 'Bogotá D.C.';
    }
    const munLimpio = mun.replace(/,?\s*D\.?\s*C\.?$/i, '').trim();
    const esBogota = norm(mun).includes('BOGOTA') || norm(depNombre).includes('BOGOTA');
    const departamental = CORP_DEPARTAMENTAL.has(corp);
    const base = departamental ? depNombre : (esBogota ? 'Bogotá' : oracion(munLimpio));
    return {
      corp, corpLabel: CORP_LABEL[corp] || 'Candidatura', depNombre, mun, munLimpio, loc, esBogota, departamental, base,
      etiqueta: departamental ? depNombre : ((corp === 'jal' && loc ? `${oracion(loc)} · ` : '') + base),
      entidad: departamental ? `Gobernación de ${depNombre}` : `Alcaldía de ${base}`,
      cuerpo: departamental ? `Asamblea de ${depNombre}` : `Concejo de ${base}`,
    };
  }

  /* Las consultas del territorio: el lugar y quienes lo gobiernan. Entre
     comillas, porque sin ellas «Concejo de Tunja» trae concejos de todo el país. */
  function consultasTerritorio(t) {
    const q = [];
    if (t.departamental) q.push(`"${t.depNombre}"`, `"${t.entidad}"`, `"${t.cuerpo}"`);
    else {
      if (t.corp === 'jal' && t.loc) q.push(`"${oracion(t.loc)}" ${t.base}`);
      q.push(`"${t.entidad}"`, `"${t.cuerpo}"`);
      if (!t.esBogota) q.push(`"${t.base}"`);
    }
    return q;
  }
  /* ── Lo que habla todo el mundo ─────────────────────────────────────────
     No hay un «top» que pedir: Google News entrega titulares por consulta, no
     un ranking. Así que se pregunta por los anclajes más anchos de la agenda
     nacional —el país y las dos ramas que la ocupan— y el ranking se CALCULA:
     una historia importa cuando la publican muchos medios distintos. Esa es la
     definición operativa de «de la que habla todo el mundo», y es medida, no
     declarada. */
  const CONSULTAS_NACIONALES = ['"Colombia"', '"Gobierno Nacional"', '"Congreso de la República"'];
  function consultasNacionales() { return CONSULTAS_NACIONALES.slice(); }

  const VACIAS = new Set(['PARA', 'POR', 'CON', 'LOS', 'LAS', 'DEL', 'QUE', 'UNA', 'UNO', 'SUS', 'ESTE', 'ESTA', 'ESTOS', 'ESTAS', 'COMO', 'MAS', 'PERO', 'SOBRE', 'ENTRE', 'DESDE', 'HASTA', 'TRAS', 'ANTE', 'SEGUN', 'SOLO', 'YA', 'HOY', 'ASI', 'FUE', 'SER', 'SON', 'HAY', 'VA', 'VAN', 'TIENE', 'TRAS']);
  /* Las palabras se cortan a seis letras: cada medio conjuga el mismo hecho a
     su manera —«sanciona», «sancionó», «sancionada»— y sin el corte la misma
     historia se parte en tres. */
  const clave = titulo => new Set(toks(titulo, 5).filter(w => !VACIAS.has(w)).map(w => w.slice(0, 6)));
  const parecido = (a, b) => { if (!a.size || !b.size) return 0; let comunes = 0; for (const w of a) if (b.has(w)) comunes++; return comunes / Math.min(a.size, b.size); };
  /* Agrupa titulares que cuentan la MISMA historia y ordena por cuántos medios
     distintos la publicaron. Sin el conteo por medio, un solo portal que
     repite la nota cinco veces se llevaría el primer puesto.

     ⚠️ Se compara contra CADA titular del grupo, no contra la unión de sus
     palabras: la unión crece con cada titular que entra y el parecido se
     diluye, así que el cuarto medio que cuenta la misma historia se quedaba
     por fuera. */
  function agruparPorCobertura(items, umbral = 0.45) {
    const grupos = [];
    for (const it of items) {
      const k = clave(it.titulo);
      if (k.size < 2) continue;
      const g = grupos.find(x => x.claves.some(c => parecido(c, k) >= umbral));
      if (g) { g.items.push(it); g.claves.push(k); }
      else grupos.push({ claves: [k], items: [it] });
    }
    return grupos.map(g => {
      const medios = new Set(g.items.map(x => norm(x.medio)).filter(Boolean));
      const ordenados = g.items.slice().sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
      return { titular: ordenados[0], medios: medios.size, titulares: g.items.length, otros: ordenados.slice(1, 4) };
    }).sort((a, b) => (b.medios - a.medios) || (b.titulares - a.titulares) || String(b.titular.fecha).localeCompare(String(a.titular.fecha)));
  }

  function terminosLocales(t) {
    const base = t.departamental ? toks(t.depNombre)
      : (t.esBogota ? ['BOGOTA'] : toks(t.munLimpio)).concat(t.corp === 'jal' && t.loc ? toks(t.loc) : []);
    return base.filter(Boolean);
  }

  const INSTITUCIONAL = ['ALCALD', 'CONCEJO', 'CONCEJAL', 'GOBERN', 'ASAMBLEA', 'DIPUTAD', 'DISTRIT', 'SECRETAR', 'EDIL', ' JAL', 'PLAN DE DESARROLLO',
    'PRESUPUESTO', 'CONTRAT', 'LICITA', 'PERSONER', 'CONTRALOR', 'OBRA', 'VIA ', 'VIAS ', 'TRANSMILENIO', 'METRO', 'ACUEDUCTO', 'HOSPITAL',
    'COLEGIO', 'SEGURIDAD', 'HOMICID', 'HURTO', 'PROTESTA', 'PARO', 'ELECCI', 'CANDIDAT', 'CAMPAÑA', 'CAMPANA', 'PARTIDO '];
  const RUIDO_TITULAR = /\b(CLIMA|LOTER|HOROSCOP|CORTES? DE LUZ|PICO Y PLACA|SORTEO|BALOTO|VACANTES|PRONOSTICO|TEMPERATURA|CHANCE|MILLONARIOS VS|VS MILLONARIOS)\b/;
  const CIUDADES_GRANDES = new Set(['MEDELLIN', 'CALI', 'BARRANQUILLA', 'CARTAGENA']);

  /* Cuánto le importa el titular a ESTE territorio. 0 = no cuenta.
     En Bogotá, Medellín o Cali el nombre de la ciudad aparece en cualquier cosa
     —el clima, una vacante, un partido—, así que ahí se exige la localidad o un
     actor institucional; en un municipio pequeño basta el nombre. */
  function puntajeLocal(titulo, t, locales) {
    const n = ' ' + norm(titulo) + ' ';
    if (RUIDO_TITULAR.test(n)) return 0;
    if (!locales.some(x => n.includes(x))) return 0;
    let p = 0;
    if (t.corp === 'jal' && t.loc && toks(t.loc).some(x => n.includes(x))) p += 3;
    if (INSTITUCIONAL.some(k => n.includes(k))) p += 2;
    if (locales.some(x => n.includes(x))) p += 1;
    const grande = t.esBogota || CIUDADES_GRANDES.has(norm(t.munLimpio));
    return (p >= 2 || !grande) ? p : 0;
  }
  /* Un titular «lo nombra» si trae nombre + apellido (o los dos apellidos). */
  function terminosPersona(v = SESION.vinculo) {
    return [nombreCandidatura(v), nombrePublico(v)].map(n => toks(n, 3)).filter(tk => tk.length >= 2);
  }
  function mencionaPersona(titulo, personas) {
    const n = norm(titulo);
    return personas.some(tk => tk.filter(x => n.includes(x)).length >= 2);
  }

  function pintarNav(pagina) {
    const nav = $('navAuth'); if (!nav) return;
    const next = encodeURIComponent(pagina);
    if (!SESION.token || !SESION.user) {
      nav.innerHTML = `<a class="nav-login" href="login.html?next=${next}">Iniciar sesión</a><a class="nav-register" href="register.html?next=${next}">Registrarse</a>`;
      return;
    }
    /* El «← CRM» ya está a la izquierda de la barra: acá solo el plan y el perfil. */
    nav.innerHTML = `<span class="nav-plan${SESION.acceso ? ' ok' : ''}">${SESION.acceso ? 'Candidato 360' : esc(SESION.user.plan || 'free')}</span><a class="nav-login" href="dashboard.html">Mi perfil</a>`;
  }

  /* Un panel sin vínculo no tiene de quién hablar. En vez de una página vacía,
     se dice qué falta y se manda al sitio donde se resuelve. */
  function muro(motivo, accion) {
    const caja = $('panelMuro'); if (!caja) return;
    caja.innerHTML = `<div class="c360-vitrina"><p>${motivo}</p>${accion}</div>`;
    caja.classList.remove('hidden');
    $('panelCuerpo')?.classList.add('hidden');
  }

  const ADMIN = ['reruizc@gmail.com', 'nuevagemela@gmail.com'];
  function esAdmin() { return SESION.fuente === 'admin' || ADMIN.includes(String(SESION.user?.email || '').toLowerCase().trim()); }
  /* Desata la cuenta de la candidatura actual con la ruta de soporte que ya
     existe. Deja copia 400 días del lado del worker. Solo administración. */
  async function soltarVinculo() {
    if (!esAdmin() || !SESION.user?.email) return;
    if (!confirm(`¿Soltar la candidatura ${nombreCandidatura()} de esta cuenta? Queda copia en soporte.`)) return;
    const r = await api(`/c360/admin/vinculo?email=${encodeURIComponent(SESION.user.email)}&motivo=${encodeURIComponent('pruebas: cuenta de administración')}`, { method: 'DELETE' });
    if (!r.ok) { alert(`No se pudo soltar: ${r.data?.error || r.status}`); return; }
    location.reload();
  }
  async function arrancar(pagina) {
    try { SESION.token = localStorage.getItem('rr-token') || null; SESION.user = JSON.parse(localStorage.getItem('rr-user') || 'null'); } catch {}
    if (SESION.token) {
      try {
        const r = await api('/c360/me');
        if (r.status === 401) { localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user'); SESION.token = null; SESION.user = null; }
        else if (r.ok) {
          SESION.acceso = !!r.data.acceso; SESION.fuente = r.data.fuente || 'ninguno';
          SESION.vinculo = r.data.vinculo || null;
          if (r.data.soporte) SESION.soporte = r.data.soporte;
          if (r.data.email) SESION.user = Object.assign({}, SESION.user || {}, { email: r.data.email, plan: r.data.plan });
        } else SESION.error = r.data?.error || `HTTP ${r.status}`;
      } catch (e) { SESION.error = String(e); }
    }
    pintarNav(pagina);
    const next = encodeURIComponent(pagina);
    if (!SESION.token) return muro('Este panel trabaja sobre <b>su</b> candidatura, así que primero hay que saber quién es.', `<a class="wall-btn primary" href="login.html?next=${next}">Iniciar sesión</a>`), false;
    if (!SESION.acceso) return muro('Su cuenta todavía no tiene acceso a Candidato 360.', `<a class="wall-btn primary" href="candidato-360.html?comprar=1">Ver qué incluye</a>`), false;
    if (!SESION.vinculo) return muro('Su cuenta todavía no tiene una candidatura abierta: los paneles se arman sobre su territorio y su nombre.', `<a class="wall-btn primary" href="candidato-360.html">Abrir mi candidatura</a>`), false;
    const cab = $('panelCandidatura');
    if (cab) {
      const t = territorio();
      /* Los paneles leen el vínculo del SERVIDOR, así que el modo pruebas de
         candidato-360.html no los afecta: si la cuenta de administración quedó
         atada a una candidatura vieja, es la que se ve acá. Por eso el botón
         para soltarla vive también en esta cabecera. */
      cab.innerHTML = `<b>${esc(nombreCandidatura())}</b>${t.texto ? ` · ${esc(t.texto)}` : ''}` +
        (esAdmin() ? ` <button type="button" class="soltar-vinculo" onclick="C360Panel.soltarVinculo()">soltar</button>` : '');
    }
    return true;
  }

  async function guardarEscucha(datos) {
    const r = await api('/c360/escucha', { method: 'POST', body: JSON.stringify(datos) });
    if (r.ok && r.data?.vinculo) SESION.vinculo = r.data.vinculo;
    return r;
  }

  global.C360Panel = { SESION, api, caudal, arrancar, guardarEscucha, territorio, nombreCandidatura, nombrePublico, muro, $, esc, num,
    territorioDe, consultasTerritorio, consultasNacionales, agruparPorCobertura, terminosLocales, esAdmin, soltarVinculo, terminosPersona, puntajeLocal, mencionaPersona, oracion, norm, toks };
})(window);
