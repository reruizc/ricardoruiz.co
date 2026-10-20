/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · el ciclo de 3 días (tarjeta 03 del CRM · oct-19-2026)
   ───────────────────────────────────────────────────────────────────────────
   El briefing manda cada tres días lo que pasó; esta lectura dice QUÉ HACER con
   eso. Junta cuatro cosas que el CRM ya tiene a mano:

     1. La prensa del territorio en los últimos 3 días (el mismo proxy de Caudal
        y las mismas consultas que el briefing y la escucha: C360Panel).
     2. Lo que se movió en sus redes, si la cuenta ya tiene lectura guardada
        (GET /c360/captura).
     3. Los arquetipos de la ciudad y su sensibilidad por tema: la agenda de
        estos días «activa» más a unos que a otros (C360Saliencia.TEMAS).
     4. Su afinidad con cada arquetipo (C360ArqLectura.afinidad).

   De ahí sale una prioridad por barrio, que se suma por localidad o comuna:

       relevancia(arquetipo) = e^(1,2 · (activación − media)) × afinidad acotada
       prioridad(barrio)     = Σ mezcla del barrio × relevancia × electorado
                               × castigo si ya lo visitó

   Las visitas se marcan tocando un barrio en el mapa y se guardan en el
   worker (/c360/visitas), con copia en este dispositivo. Una visita de los últimos 7 días baja la
   prioridad del barrio al 35 %; de 8 a 21 días, al 60 %. Pasado eso cuenta
   como no visitado: el barrio vuelve a necesitarlo.

   ⚠️ Es una lectura del territorio, no de personas: describe dónde viven los
   arquetipos que la agenda de estos días mueve, nunca quién vota por quién.
   La sensibilidad por tema de Bogotá es criterio del equipo y se dice.

   API: window.C360Ciclo.pintar(ctx) · ctx = { token, vinculo, ciudad, corp,
   mesas, slug }. La tarjeta pone el DOM; este archivo trae su propio CSS.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const VENTANA = 3;
  const AUTH_API = (global.RR_RUNTIME_CONFIG && global.RR_RUNTIME_CONFIG.authBase) || 'https://rr-auth.reruizc.workers.dev';
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const num = n => Number(n || 0).toLocaleString('es-CO');
  const pct = x => `${Math.round((x || 0) * 100)} %`;
  /* Los nombres llegan en mayúscula y a veces sin tilde («ENGATIVA»): en
     pantalla van en tipo título, con la tilde de las localidades de Bogotá y
     los números romanos de los barrios («Bochica II»). */
  const TILDES = { ENGATIVA: 'Engativá', FONTIBON: 'Fontibón', USAQUEN: 'Usaquén', 'CIUDAD BOLIVAR': 'Ciudad Bolívar', 'SAN CRISTOBAL': 'San Cristóbal', 'LOS MARTIRES': 'Los Mártires', MARTIRES: 'Los Mártires', 'ANTONIO NARINO': 'Antonio Nariño' };
  const titulo = s => {
    const k = String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();
    if (TILDES[k]) return TILDES[k];
    return String(s || '').toLowerCase().replace(/(^|[\s(\-])([a-záéíóúñü])/g, (m, a, b) => a + b.toUpperCase())
      .replace(/\b(De|Del|La|Las|Los|Y|El|En)\b/g, w => w.toLowerCase()).replace(/^(\w)/, c => c.toUpperCase())
      .replace(/\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|Xi|Xii)\b/g, w => w.toUpperCase());
  };
  const lista = xs => xs.length <= 1 ? (xs[0] || '') : `${xs.slice(0, -1).join(', ')} y ${xs[xs.length - 1]}`;

  /* ── Visitas ─────────────────────────────────────────────────────────────── */
  const claveVisitas = slug => `c360-visitas:${slug || 'sin-candidatura'}`;
  function leerVisitas(slug) { try { return JSON.parse(localStorage.getItem(claveVisitas(slug)) || '{}') || {}; } catch { return {}; } }
  function guardarVisitas(slug, v) { try { localStorage.setItem(claveVisitas(slug), JSON.stringify(v)); } catch {} }
  const diasDesde = iso => Math.floor((Date.now() - new Date(iso).getTime()) / 864e5);
  /* Las visitas viven en el worker (GET/POST /c360/visitas): las ve todo el
     equipo y las lee el briefing por correo. La copia local es el respaldo si
     el worker no responde. La primera vez, lo que ya estaba marcado en este
     dispositivo se sube. */
  async function visitasServidor(token, slug) {
    if (!token) return null;
    try {
      const r = await fetch(`${AUTH_API}/c360/visitas`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      if (!r.ok || !d?.visitas) return null;
      const local = leerVisitas(slug);
      if (!Object.keys(d.visitas).length && Object.keys(local).length) {
        Object.entries(local).forEach(([code, v]) => marcarServidor(token, code, v));
        return local;
      }
      guardarVisitas(slug, d.visitas);
      return d.visitas;
    } catch { return null; }
  }
  function marcarServidor(token, code, v) {
    if (!token) return;
    fetch(`${AUTH_API}/c360/visitas`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(v ? { code, nombre: v.nombre || '', fecha: v.fecha } : { code, quitar: true }) }).catch(() => {});
  }
  function castigo(iso) {
    if (!iso) return 1;
    const d = diasDesde(iso);
    return d <= 7 ? 0.35 : d <= 21 ? 0.6 : 1;
  }

  /* ── 1. Prensa ───────────────────────────────────────────────────────────
     Se cachea por hora en la pestaña: el CRM se abre y se cierra mucho, y el
     proxy de Caudal tiene límite por minuto. */
  async function prensa(P, t) {
    const k = `c360-ciclo-prensa:${t.etiqueta}:${new Date().toISOString().slice(0, 13)}`;
    try { const c = sessionStorage.getItem(k); if (c) return JSON.parse(c); } catch {}
    const consultas = P.consultasTerritorio(t);
    const nombres = [P.nombreCandidatura(), P.nombrePublico()].filter(n => P.toks(n, 3).length >= 2).map(n => `"${n}"`);
    const rs = await Promise.all(consultas.concat(nombres).map(q => P.caudal({ action: 'medios', query: q, dias: VENTANA }).catch(() => null)));
    const locales = P.terminosLocales(t), personas = P.terminosPersona(), vistos = new Set(), items = [];
    let fallos = 0;
    rs.forEach((d, i) => {
      if (!d) { fallos++; return; }
      const esNombre = i >= consultas.length;
      for (const r of d.resultados || []) {
        const tit = r.titulo || '', key = P.norm(tit).slice(0, 90);
        if (!key || vistos.has(key)) continue;
        const local = P.puntajeLocal(tit, t, locales) > 0, suyo = P.mencionaPersona(tit, personas);
        if (!(esNombre ? suyo : (local || suyo))) continue;
        vistos.add(key);
        items.push({ titulo: tit, medio: r.medio || '', url: r.url || '', fecha: r.fecha || '', suyo });
      }
    });
    const out = { items, fallos, consultas: rs.length };
    if (fallos < rs.length) { try { sessionStorage.setItem(k, JSON.stringify(out)); } catch {} }
    return out;
  }

  /* ── 2. Redes ─────────────────────────────────────────────────────────── */
  /* La lectura de redes se guarda por CUENTA, pero una cuenta puede probar otra
     candidatura (vínculo local, o un vínculo que soporte cambió). Solo se pinta
     si es de la candidatura abierta: si no, otra persona vería las cuentas de
     alguien más (pasó: probando una candidatura propia salían las de otro). */
  const _tokNombre = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z ]+/g, ' ').split(/\s+/).filter(w => w.length >= 3);
  function capturaEsDe(cap, nombre) {
    const a = _tokNombre(cap?.vinculo?.nombre), b = _tokNombre(nombre);
    if (!a.length) return true;                 /* lecturas viejas sin nombre */
    if (!b.length) return false;
    const sa = new Set(a), sb = new Set(b);
    return a.every(w => sb.has(w)) || b.every(w => sa.has(w));
  }
  async function redes(token, nombre) {
    if (!token) return null;
    try {
      const r = await fetch(`${AUTH_API}/c360/captura`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      return d?.encendida && capturaEsDe(d, nombre) ? d : null;
    } catch { return null; }
  }
  const NOMBRE_RED = { x: 'X', instagram: 'Instagram', tiktok: 'TikTok', facebook: 'Facebook' };
  /* Los temas de la captura son las IDEAS del candidato («seguridad en
     TransMilenio»); se llevan a los temas de agenda con el mismo diccionario
     de la saliencia, para poder sumarlos con la prensa. */
  function leerRedes(cap, S) {
    if (!cap?.redes) return null;
    const porTema = {}, porIdea = {}, postura = { a_favor: 0, en_contra: 0, ataque: 0, neutro: 0 }, porRed = [];
    let total = 0;
    Object.entries(cap.redes).forEach(([red, R]) => {
      if (!R || R.estado !== 'ok') return;
      Object.entries(R.temas || {}).forEach(([idea, n]) => {
        n = Number(n) || 0; if (!n) return;
        porIdea[idea] = (porIdea[idea] || 0) + n;
        const ts = S.temasDe(S.norm(idea));
        ts.forEach(id => { porTema[id] = (porTema[id] || 0) + n / ts.length; });
        if (ts.length) total += n;
      });
      const p = R.comentarios_propios?.postura || {};
      Object.keys(postura).forEach(k => { postura[k] += Number(p[k] || 0); });
      const hostil = Number(p.en_contra || 0) + Number(p.ataque || 0), aFavor = Number(p.a_favor || 0), n = Number(R.comentarios_propios?.n || 0);
      if (n) porRed.push({ red, nombre: NOMBRE_RED[red] || red, n, hostil, aFavor });
    });
    const ideas = Object.entries(porIdea).sort((a, b) => b[1] - a[1]);
    return { porTema, total, ideas, postura, porRed, fecha: cap.generadoEn || '' };
  }

  /* ── 3. Pesos de la agenda por tema ───────────────────────────────────────
     Prensa y redes pesan lo mismo cuando están las dos: una mide lo que se
     publica, la otra lo que se comenta donde está el candidato. */
  function pesosAgenda(a, R) {
    const w = {};
    (a?.temas || []).forEach(t => { w[t.id] = (w[t.id] || 0) + t.pct * (R?.total ? 0.5 : 1); });
    if (R?.total) Object.entries(R.porTema).forEach(([id, n]) => { w[id] = (w[id] || 0) + (n / R.total) * (a?.N ? 0.5 : 1); });
    return w;
  }

  /* ── 4. Arquetipos: sensibilidad y relevancia ─────────────────────────── */
  function sensDe(L, id) {
    const f = L.ficha?.(id);
    if (f?.sens && Object.keys(f.sens).length) return f.sens;
    const fam = (global.C360Arquetipos?.FAMILIAS || []).find(x => String(id).startsWith(x.slug) || f?.familia === x.slug);
    return fam?.sens || null;
  }
  function relevancias(L, Lp, w) {
    const corte = L.cortes?.[0];
    const ids = (L.idsDe ? L.idsDe(corte) : L.ids) || [];
    const afin = {};
    if (Lp?.conVotos) global.C360ArqLectura.afinidad(Lp, L, corte, { minimo: 0 }).forEach(x => { afin[x.id] = x.ratio; });
    const temasConPeso = Object.entries(w).filter(([, v]) => v > 0);
    const filas = ids.map(id => {
      const s = sensDe(L, id);
      let suma = 0, peso = 0, mejor = null;
      if (s) temasConPeso.forEach(([t, v]) => { if (s[t] != null) { suma += s[t] * v; peso += v; if (!mejor || s[t] * v > mejor.x) mejor = { t, x: s[t] * v }; } });
      return { id, nombre: L.nombreDe(id), color: L.colorDe(id), act: peso ? suma / peso : null, tema: mejor?.t || null, afin: afin[id] ?? null };
    });
    const conAct = filas.filter(f => f.act != null), media = conAct.length ? conAct.reduce((s, f) => s + f.act, 0) / conAct.length : 0;
    filas.forEach(f => {
      const empuje = f.act != null ? Math.exp(1.2 * (f.act - media)) : 1;
      const a = f.afin == null ? 1 : Math.min(2, Math.max(0.5, f.afin));
      f.rel = empuje * a; f.empuje = empuje;
    });
    return filas.sort((a, b) => b.rel - a.rel);
  }

  /* ── 5. Prioridad por barrio y por unidad ─────────────────────────────── */
  function prioridades(L, rel, visitas) {
    const corte = L.cortes?.[0], R = Object.fromEntries(rel.map(r => [r.id, r.rel]));
    const info = Object.fromEntries((L.filasBarrio || []).map(f => [f.code, f]));
    const barrios = {};
    Object.entries(L.pesos || {}).forEach(([code, w]) => {
      if (!w) return;
      const m = L.mezclaDe(code, corte) || (L.dominanteDe(code, corte) ? { [L.dominanteDe(code, corte)]: 1 } : null);
      if (!m) return;
      let r = 0; Object.entries(m).forEach(([id, p]) => { r += p * (R[id] || 0); });
      const top = Object.entries(m).sort((a, b) => b[1] - a[1])[0]?.[0];
      const c = castigo(visitas[code]?.fecha);
      barrios[code] = { code, nombre: info[code]?.nombre || code, unidad: info[code]?.comuna || '', w, r, valor: r * w * c, bruto: r * w, castigo: c, top, visita: visitas[code] || null };
    });
    const unidades = {};
    Object.values(barrios).forEach(b => {
      if (!b.unidad) return;
      const u = unidades[b.unidad] || (unidades[b.unidad] = { nombre: b.unidad, valor: 0, bruto: 0, w: 0, barrios: [], visitados: 0 });
      u.valor += b.valor; u.bruto += b.bruto; u.w += b.w; u.barrios.push(b);
      if (b.castigo < 1) u.visitados++;
    });
    const total = Object.values(unidades).reduce((s, u) => s + u.valor, 0) || 1;
    const orden = Object.values(unidades).map(u => ({ ...u, share: u.valor / total, barrios: u.barrios.sort((a, b) => b.valor - a.valor) })).sort((a, b) => b.valor - a.valor);
    /* Índice del barrio contra el promedio de la ciudad, para el color. */
    const vals = Object.values(barrios), media = vals.reduce((s, b) => s + b.r * b.castigo, 0) / (vals.length || 1);
    vals.forEach(b => { b.indice = media ? (b.r * b.castigo) / media : 1; });
    return { barrios, unidades: orden };
  }

  /* ── El texto ─────────────────────────────────────────────────────────── */
  function nombreTema(S, id) { const t = S.TEMAS.find(x => x.id === id); return t ? (t.corto || t.nombre.toLowerCase()) : id; }
  function resumen(ctx) {
    const { S, a, R, rel, P, L, unidades, t } = ctx;
    const partes = [];
    if (a?.N) {
      const t1 = a.temas[0], t2 = a.temas[1];
      const suyos = a.filas.filter(f => f.suyo).length;
      partes.push(`En los últimos ${VENTANA} días salieron <b>${num(a.N)} titulares</b> sobre ${esc(t.etiqueta)}${t1 ? `; manda <b>${esc(t1.corto)}</b> (${pct(t1.pct)})${t2 ? ` y le sigue ${esc(t2.corto)} (${pct(t2.pct)})` : ''}` : ''}.${suyos ? ` <b>${num(suyos)}</b> ${suyos === 1 ? 'lo nombra' : 'lo nombran'} a usted.` : ''}`);
    } else partes.push(`En los últimos ${VENTANA} días la prensa casi no habló de ${esc(t.etiqueta)}: la agenda la está poniendo la conversación de redes, no los medios.`);
    if (R?.ideas?.length) {
      const [idea, n] = R.ideas.find(([i]) => S.temasDe(S.norm(i)).length) || R.ideas[0];
      partes.push(`En redes, de sus ideas la que más se mueve es <b>«${esc(idea)}»</b> (${num(n)} publicaciones).`);
    }
    if (L && rel.length) {
      const top = rel.filter(r => r.act != null).slice(0, 2);
      if (top.length) {
        const conecta = top.filter(r => (r.afin || 0) >= 1).length;
        partes.push(`Esa agenda le habla sobre todo a ${lista(top.map(r => `<b>«${esc(r.nombre)}»</b>`))}${top[0].tema ? `, que se mueve${top.length > 1 ? 'n' : ''} por ${esc(nombreTema(S, top[0].tema))}` : ''}${conecta === top.length && top[0].afin != null ? ', y con los dos usted rinde por encima de la ciudad' : conecta ? ', y con el primero usted rinde por encima de la ciudad' : ''}.`);
      }
    }
    if (unidades?.length) {
      const u3 = unidades.slice(0, 3).map(u => titulo(u.nombre));
      partes.push(`Por eso esta semana conviene estar en <b>${esc(lista(u3))}</b>.`);
    }
    return partes.join(' ');
  }
  function bloqueRedes(R) {
    if (!R?.porRed?.length) return '';
    const p = R.postura, hostil = p.en_contra + p.ataque, total = hostil + p.a_favor + p.neutro;
    const peor = R.porRed.slice().sort((x, y) => (y.hostil / y.n) - (x.hostil / x.n))[0];
    const mejor = R.porRed.slice().sort((x, y) => (y.aFavor / y.n) - (x.aFavor / x.n) || (x.hostil / x.n) - (y.hostil / y.n))[0];
    return `<p class="ciclo-redes">En lo que le comentan en sus publicaciones (${num(total)} comentarios leídos): <b>${pct(hostil / (total || 1))}</b> en contra o en ataque y <b>${pct(p.a_favor / (total || 1))}</b> a favor.${peor && peor.hostil ? ` La red más dura es <b>${esc(peor.nombre)}</b>` : ''}${mejor && mejor !== peor ? `; la más amable, <b>${esc(mejor.nombre)}</b>.` : '.'} <a href="candidato-360-escucha.html">Ver la escucha →</a></p>`;
  }

  /* ── El mapa ──────────────────────────────────────────────────────────── */
  let MAPA = null, CAPA = null;
  const RAMPA = ['#e7e2d6', '#f3d9a4', '#f0b45f', '#e07b39', '#b9431f'];
  /* Quintiles de la prioridad entre los barrios de la ciudad: con cortes fijos
     casi todo caía en los dos tonos claros y el mapa no decía nada. */
  let CORTES = [.75, 1, 1.25, 1.6];
  function colorDe(ind) { let i = 0; while (i < CORTES.length && ind >= CORTES[i]) i++; return RAMPA[i]; }
  function fijarCortes(pr) {
    const v = Object.values(pr.barrios).map(b => b.indice).sort((x, y) => x - y);
    if (v.length >= 10) CORTES = [.2, .4, .6, .8].map(q => v[Math.floor(q * (v.length - 1))]);
  }
  function pintarMapa(el, L, pr, alTocar) {
    if (!global.L || !L.geo) { el.classList.add('hidden'); return; }
    fijarCortes(pr);
    el.classList.remove('hidden');
    if (!MAPA) {
      MAPA = global.L.map(el, { zoomControl: true, attributionControl: false, scrollWheelZoom: false, zoomSnap: 0.25 });
      MAPA.setView([4.65, -74.1], 11);
    }
    if (CAPA) MAPA.removeLayer(CAPA);
    CAPA = global.L.geoJSON(L.geo, {
      style: f => {
        const b = pr.barrios[L.codeDe(f.properties || {})];
        if (!b) return { weight: .3, color: '#c9c2b2', fillColor: '#f4f0e8', fillOpacity: .5 };
        return { weight: b.castigo < 1 ? 1.6 : .4, color: b.castigo < 1 ? '#1d4d3a' : '#fff', dashArray: b.castigo < 1 ? '3 2' : null, fillColor: colorDe(b.indice), fillOpacity: b.castigo < 1 ? .45 : .85 };
      },
      onEachFeature: (f, lay) => {
        const code = L.codeDe(f.properties || {}), b = pr.barrios[code];
        const nom = b?.nombre || L.nombreGeo(f.properties || {});
        lay.bindTooltip(b
          ? `<b>${esc(titulo(nom))}</b>${b.unidad ? ` · ${esc(titulo(b.unidad))}` : ''}<br>Prioridad ${b.indice.toFixed(2).replace('.', ',')} × la ciudad<br>Pesa «${esc(L.nombreDe(b.top))}»<br>${b.visita ? `Visitado hace ${diasDesde(b.visita.fecha)} días · toque para quitar` : 'Toque si ya lo visitó'}`
          : esc(titulo(nom)), { sticky: true, className: 'ciclo-tip' });
        if (b) lay.on('click', () => alTocar(code, nom));
      },
    }).addTo(MAPA);
    setTimeout(reencuadrar, 0);
  }

  /* ── CSS ──────────────────────────────────────────────────────────────── */
  /* Encuadra el mapa de zonas. También lo llama el plan por fases al abrir
     una fase: si el mapa se armó con la portada encima, midió una caja de 0×0. */
  function reencuadrar() {
    if (!MAPA || !CAPA) return;
    const ajustar = () => {
      MAPA.invalidateSize();
      try { const bb = CAPA.getBounds(); if (bb.isValid()) { const z = MAPA.getBoundsZoom(bb); MAPA.fitBounds(bb, { padding: [6, 6], animate: false, maxZoom: Number.isFinite(z) ? Math.max(z, 10) : 11 }); } } catch {}
    };
    ajustar(); setTimeout(ajustar, 60); setTimeout(ajustar, 260);
  }

  function estilos() {
    if ($('c360CicloCss')) return;
    const s = document.createElement('style'); s.id = 'c360CicloCss';
    s.textContent = `
/* Con lectura, la tarjeta 03 ocupa el ancho entero y baja a la segunda fila:
   02 y 04 quedan arriba lado a lado y nada deja huecos en la grilla. */
.crm-grid:has(#crmBriefing.crm-ciclo-on)>*{order:2}
.crm-grid:has(#crmBriefing.crm-ciclo-on)>.crm-vote-target,.crm-grid:has(#crmBriefing.crm-ciclo-on)>#crmEscucha{order:0}
#crmBriefing.crm-ciclo-on{order:1;grid-column:1/-1}
.ciclo-cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:22px;align-items:start}
@media(max-width:850px){.ciclo-cols{grid-template-columns:1fr}}
.ciclo{margin:14px 0 4px;border-top:1px solid rgba(255,255,255,.14);padding-top:12px}
.ciclo-kicker{font:500 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:#87c79f;margin:0 0 6px}
.ciclo-txt{font-size:13.5px;line-height:1.5;margin:0 0 10px}
.ciclo-mapa{height:380px;background:#f4f0e8;border:1px solid rgba(255,255,255,.14);position:relative;z-index:0;isolation:isolate}
.ciclo-mapa .leaflet-container{background:#f4f0e8}
.ciclo-ley{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font:10px var(--mono);opacity:.75;margin:6px 0 10px}
.ciclo-ley i{display:inline-block;width:12px;height:9px;margin-right:3px;vertical-align:middle}
.ciclo-ley .vis{border:1.5px dashed #87c79f;width:10px;height:7px}
.ciclo-top{list-style:none;padding:0;margin:0 0 8px;counter-reset:z}
.ciclo-top li{counter-increment:z;padding:8px 0;border-top:1px solid rgba(255,255,255,.12);font-size:13px}
.ciclo-top li:first-child{border-top:0}
.ciclo-top li::before{content:counter(z);font:700 11px var(--mono);color:#fff;background:#b9431f;display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;margin-right:8px}
.ciclo-top small{display:block;opacity:.72;margin:3px 0 0 26px}
.ciclo-decir{background:rgba(255,255,255,.07);border-left:3px solid #87c79f;padding:8px 10px;font-size:12.5px;margin:6px 0 10px}
.ciclo-redes{font-size:12.5px;opacity:.85;margin:6px 0 10px}
.ciclo a{color:#9fd8b5}
.ciclo-nota{font-size:11px;opacity:.65;margin:6px 0 0}
.ciclo-tip{font-size:12px}
.ciclo-cargando{font-size:12.5px;opacity:.7}
.ciclo-tip{color:#14161f}`;
    document.head.appendChild(s);
  }

  /* ── Pintar ───────────────────────────────────────────────────────────── */
  let TURNO = 0, ULTIMO = null;
  async function pintar(ctx) {
    const caja = $('crmCiclo'), card = $('crmBriefing');
    const P = global.C360Panel, S = global.C360Saliencia, A = global.C360ArqLectura;
    if (!caja || !P || !S || !ctx?.token || !ctx?.vinculo) { caja?.classList.add('hidden'); card?.classList.remove('crm-ciclo-on'); return; }
    estilos();
    const turno = ++TURNO;
    P.SESION.token = ctx.token; P.SESION.vinculo = ctx.vinculo;
    const t = P.territorioDe(ctx.vinculo);
    if (!P.consultasTerritorio(t).length) { caja.classList.add('hidden'); return; }
    caja.classList.remove('hidden'); card.classList.add('crm-ciclo-on');
    caja.innerHTML = `<p class="ciclo-kicker">Qué sugiere este ciclo · ${VENTANA} días</p><p class="ciclo-cargando">Leyendo la prensa de ${esc(t.etiqueta)}, sus redes y sus arquetipos…</p>`;
    try {
      const lecturaArq = ctx.ciudad
        ? Promise.all([A.leer(ctx.ciudad, [], { corp: ctx.corp }), A.leer(ctx.ciudad, ctx.mesas || [], { corp: ctx.corp })]).catch(() => [null, null])
        : Promise.resolve([null, null]);
      const [pz, cap, [L, Lp]] = await Promise.all([prensa(P, t), redes(ctx.token, P.nombreCandidatura(ctx.vinculo)), lecturaArq, visitasServidor(ctx.token, ctx.slug)]);
      if (turno !== TURNO) return;
      const a = pz.items.length ? S.analizar(pz.items, { locales: P.terminosLocales(t), persona: P.terminosPersona(), ventana: VENTANA, anclas: [t.entidad, t.cuerpo] }) : null;
      if (a) a.filas.forEach((f, i) => { f.suyo = pz.items[i]?.suyo; });
      const R = leerRedes(cap, S);
      const w = pesosAgenda(a, R);
      ULTIMO = { ctx, P, S, A, t, a, R, w, L, Lp };
      render();
    } catch (e) {
      if (turno !== TURNO) return;
      caja.innerHTML = `<p class="ciclo-kicker">Qué sugiere este ciclo</p><p class="ciclo-cargando">No pudimos leer la prensa ni las redes de estos días. Vuelva a abrir el CRM en un momento.</p>`;
    }
  }
  function render() {
    const U = ULTIMO; if (!U) return;
    const { ctx, S, t, a, R, w, L, Lp } = U, caja = $('crmCiclo');
    const visitas = leerVisitas(ctx.slug);
    const rel = L ? relevancias(L, Lp, w) : [];
    const pr = L ? prioridades(L, rel, visitas) : { barrios: {}, unidades: [] };
    const txt = resumen({ S, a, R, rel, L, unidades: pr.unidades, t });
    const top = pr.unidades.slice(0, 3);
    const lis = top.map(u => {
      const libres = u.barrios.filter(b => b.castigo === 1).slice(0, 3).map(b => titulo(b.nombre));
      return `<li><b>${esc(titulo(u.nombre))}</b> · ${pct(u.share)} de la prioridad<small>${libres.length ? `Barrios por visitar: ${esc(lista(libres))}.` : 'Ya visitó sus barrios clave.'}${u.visitados ? ` ${num(u.visitados)} visitado${u.visitados === 1 ? '' : 's'} hace poco.` : ''}</small></li>`;
    }).join('');
    const arq = rel.find(r => r.act != null) || rel[0];
    const f = arq && L ? L.ficha(arq.id) : null;
    const decir = f?.oficio ? `<div class="ciclo-decir"><b>Qué llevar a esas zonas.</b> ${esc(f.oficio)}${arq.tema ? ` Hoy el tema que lo abre es ${esc(nombreTema(S, arq.tema))}.` : ''}</div>` : '';
    const nVis = Object.values(visitas).filter(v => diasDesde(v.fecha) <= 21).length;
    caja.innerHTML = `<p class="ciclo-kicker">Qué sugiere este ciclo · ${VENTANA} días</p>
      <div class="ciclo-cols"><div>
      <p class="ciclo-txt">${txt}</p>
      ${bloqueRedes(R)}
      ${L ? `<ol class="ciclo-top">${lis}</ol>${decir}</div><div>
      <div class="ciclo-mapa" id="crmCicloMapa"></div>
      <div class="ciclo-ley"><span>prioridad</span>${RAMPA.map(c => `<i style="background:${c};margin:0"></i>`).join('')}<span>de menos a más</span><span><i class="vis"></i>visitado (${num(nVis)})</span></div>
      </div></div>` : `</div></div><p class="ciclo-nota">Cuando su ciudad tenga arquetipos por barrio (hoy Bogotá, Medellín y Cartagena), acá aparece el mapa de zonas a priorizar.</p>`}
      <p class="ciclo-nota">La prioridad junta tres cosas: dónde viven los arquetipos que la agenda de estos días mueve, cuánto rinde usted con cada uno y si ya visitó el barrio (toque un barrio en el mapa para marcarlo; lo ve todo su equipo y lo usa el briefing por correo). Describe el territorio, no a las personas.${L?.ciudad === 'bogota' ? ' En Bogotá, qué tema mueve a cada arquetipo es criterio del equipo.' : ''}${R?.fecha ? ` Redes leídas el ${esc(new Date(R.fecha).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }))}.` : ''}</p>`;
    if (L) {
      MAPA = null; CAPA = null;
      pintarMapa($('crmCicloMapa'), L, pr, (code, nom) => {
        const v = leerVisitas(ctx.slug);
        if (v[code] && diasDesde(v[code].fecha) <= 21) { delete v[code]; marcarServidor(ctx.token, code, null); }
        else { v[code] = { fecha: new Date().toISOString().slice(0, 10), nombre: nom }; marcarServidor(ctx.token, code, v[code]); }
        guardarVisitas(ctx.slug, v);
        render();
      });
    }
  }

  global.C360Ciclo = { pintar, reencuadrar, VENTANA, _relevancias: relevancias, _prioridades: prioridades, _leerRedes: leerRedes };
})(window);
