/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · el plan de campaña por fases (portada del CRM · oct-20-2026)
   ───────────────────────────────────────────────────────────────────────────
   Antes de los once módulos, el CRM saluda («¡Hola, Emel! Esta es tu hoja de ruta»), muestra el aviso de las cinco etapas y muestra el plan en
   cinco fases: Planeación · Posicionamiento · Campaña · Remate · Día de la
   elección. Cada fase abre solo los módulos que le sirven; en las dos
   primeras, 11 · Estrategia va de primera.

   Hoy están abiertas Planeación y Posicionamiento. Las otras tres se ven con
   su fecha y lo que van a traer (el Día de la elección trae 09), y DESDE EL
   22-OCT TAMBIÉN SE PUEDEN ABRIR: se entra, se ven sus módulos en gris y sin
   responder al clic, con un aviso de cuándo se abre la fase (pedido de
   Ricardo: que se pueda mirar qué hay adentro, no solo el rótulo). Las fechas
   salen del calendario del banco de estrategia (estrategia-banco.json): el
   posicionamiento hasta el 28-feb-2027, la inscripción en junio y julio, la
   propaganda desde el 31-jul y la última semana para el Día D.

   API: window.C360Plan.mostrar() al abrir el CRM; .abrir(id) abre una fase.
   No toca el cálculo de ningún módulo: solo muestra u oculta tarjetas.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const MESES = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split(' ');
  const fecha = iso => { const [a, m, d] = iso.split('-').map(Number); return `${d} de ${MESES[m - 1]} de ${a}`; };

  /* Qué módulo es cada pieza del CRM. Las de arriba (mapa y punto de partida)
     no viven en la rejilla de módulos. */
  const PIEZAS = {
    estrategia: () => $('crmEstrategia'), mapa: () => $('crmMap')?.closest('article'), partida: () => $('crmContext')?.closest('.panel'),
    meta: () => document.querySelector('#crm .crm-vote-target'), briefing: () => $('crmBriefing'), escucha: () => $('crmEscucha'),
    arquetipos: () => $('crmArquetipos'), perfil: () => $('crmPerfil'), firmas: () => $('crmFirmas'), endoso: () => $('crmEndoso'),
    diad: () => $('crmDiaD'), contendientes: () => $('crmContendientes'), territorio: () => $('crmTerritorio'),
  };
  const NOMBRE_MODULO = { estrategia: '11 · Estrategia', mapa: '01 · Mapa de historial', meta: '02 · Objetivo de votos', briefing: '03 · Briefing', escucha: '04 · Escucha social',
    arquetipos: '05 · Arquetipos', perfil: '06 · Perfil del votante', firmas: '07 · Firmas', endoso: '08 · Endoso de aliados', diad: '09 · El día de la elección', contendientes: '10 · Contendientes', territorio: '12 · Su territorio' };

  const FASES = [
    { id: 'planeacion', nombre: 'Planeación', activa: true, cuando: 'Ahora',
      que: 'De dónde parte: su historial, la meta de votos, el territorio, sus rivales y la estrategia.',
      parrafo: 'Antes de salir a la calle hay que saber de dónde parte: dónde estuvieron sus votos, cuántos necesita, cómo vota cada barrio y contra quién compite. Con eso se escoge una estrategia, y la estrategia ordena todo lo demás. Esta fase no se cierra: se vuelve a ella cada vez que cambie algo grande, como el aval, la lista o un rival.',
      modulos: ['estrategia', 'partida', 'meta', 'arquetipos', 'perfil', 'contendientes', 'endoso', 'firmas', 'territorio', 'mapa'] },
    { id: 'posicionamiento', nombre: 'Posicionamiento', activa: true, cuando: 'Ahora · hasta el 28 de febrero de 2027',
      que: 'El lugar que ocupa antes de la campaña: qué dice, a quién le habla y dónde se deja ver. La persuasión se hace temprano.',
      parrafo: 'Hasta el 28 de febrero de 2027 se construye el lugar que usted ocupa en la cabeza del votante, antes de que empiece el ruido de la campaña. Lo que la gente piense de usted en marzo es, en buena parte, lo que pensará en octubre: en las últimas semanas la persuasión casi no mueve a nadie. Aquí se decide qué dice, a quién le habla primero y en qué barrios se deja ver; la escucha y el briefing le dicen si está funcionando.',
      modulos: ['estrategia', 'briefing', 'escucha', 'territorio', 'arquetipos', 'contendientes'] },
    { id: 'campana', nombre: 'Campaña', activa: false, abre: '2027-03-01', cuando: '1 de marzo al 24 de septiembre de 2027',
      que: 'Cerrar el aval y la lista, inscribirse (junio y julio) y movilizar a quien ya lo prefiere.',
      modulos: ['estrategia', 'briefing', 'escucha', 'territorio', 'endoso', 'contendientes'] },
    { id: 'remate', nombre: 'Remate', activa: false, abre: '2027-09-25', cuando: '25 de septiembre al 23 de octubre de 2027',
      que: 'Concentrar la pauta y la presencia donde rinden: su efecto dura pocos días.',
      modulos: ['estrategia', 'briefing', 'escucha'] },
    { id: 'dia', nombre: 'Día de la elección', activa: false, abre: '2027-10-24', cuando: '24 al 31 de octubre de 2027',
      que: 'Sacar a votar y cuidar el voto: testigos en los puestos que más pesan.',
      modulos: ['diad'] },
  ];

  let FASE = null;
  const AVISO_KEY = 'c360-plan-etapas-vistas';
  /* Ilustraciones de las fases: pictogramas planos y serios (figuras tipo
     señalética), generados en Canva el 22-oct-2026. Reemplazaron a las
     isométricas estilo Monument Valley, que no gustaron. */
  const IMG = id => `assets/candidato-360/fases/${id}.webp?v=20261022`;

  function estilos() {
    if ($('c360PlanCss')) return;
    const s = document.createElement('style'); s.id = 'c360PlanCss';
    s.textContent = `
#crm.plan-portada:not(.crm-en-estrategia)>*:not(.flow-top):not(#crmPlan){display:none!important}
#crm.plan-fase{display:flex;flex-direction:column}
#crm.plan-fase>.flow-top{order:0}#crm.plan-fase>#crmPlan{order:1}#crm.plan-fase>.dash-head{order:2}
#crm.plan-fase>.panel{order:3}#crm.plan-fase>.crm-grid{order:4;margin-bottom:14px}#crm.plan-fase>article.panel{order:5}#crm.plan-fase>.estr-vista{order:6}
#crm.plan-fase .plan-fuera{display:none!important}
#crm.plan-fase.plan-cerrada .crm-grid>*:not(.plan-fuera),#crm.plan-fase.plan-cerrada>.panel,#crm.plan-fase.plan-cerrada>article.panel,#crm.plan-fase.plan-cerrada>.estr-vista,#crm.plan-fase.plan-cerrada>.dash-head{opacity:.45;filter:grayscale(1);pointer-events:none;user-select:none}
#crm.plan-fase.plan-cerrada .plan-intro{border-style:dashed}
.plan-aviso{display:flex;gap:12px;align-items:center;margin:-10px 0 22px;padding:12px 16px;background:var(--cream);border:1px dashed var(--line);border-left:3px solid var(--coral);font-size:14px;color:var(--ink)}
.plan-aviso b{color:var(--coral)}.plan-aviso span{color:var(--muted)}
#crm.plan-fase .crm-grid>#crmEstrategia{order:-5}
.plan-hola{margin:8px 0 26px}.plan-hola h2{font-size:clamp(36px,5vw,62px);line-height:.98;margin:6px 0 10px}.plan-hola p{color:var(--muted);max-width:640px;margin:0;font-size:17px}.plan-hola .plan-por-que{max-width:920px;margin-top:16px;font-size:17.5px;line-height:1.6;color:var(--ink);border-left:3px solid var(--green);padding-left:14px}
.plan-hola{margin:8px 0 22px}
.plan-etapas-aviso{max-width:980px;padding:30px 34px 28px;background:var(--cream);border:1px solid var(--line);border-left:5px solid var(--coral);box-shadow:14px 14px 0 var(--mint);animation:planAviso .35s ease}
.plan-etapas-aviso p{margin:0 0 16px;font-size:clamp(19px,1.9vw,24px);line-height:1.5;color:var(--ink)}
.plan-etapas-aviso .plan-etapas-cierre{font-weight:800;color:var(--green)}
.plan-etapas-ok{margin-top:8px;min-width:240px;min-height:54px;padding:14px 28px;border:0;background:var(--ink);color:#fff;font:800 15px var(--sans);letter-spacing:.18em;text-transform:uppercase;cursor:pointer;transition:background .2s}
.plan-etapas-ok:hover,.plan-etapas-ok:focus{background:var(--green);outline:none}
.plan-etapas-cuerpo{animation:planAviso .35s ease}
.plan-sub{display:flex;flex-wrap:wrap;gap:12px 22px;align-items:center;justify-content:space-between;margin:0 0 18px}
.plan-sub p{margin:0;color:var(--muted);font-size:17px;max-width:680px}
.plan-etapas-ver{border:1px solid var(--ink);background:transparent;color:var(--ink);padding:10px 14px;font:700 12px var(--sans);letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
.plan-etapas-ver:hover{background:var(--ink);color:#fff}
@keyframes planAviso{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media(max-width:700px){.plan-etapas-aviso{padding:22px 18px;box-shadow:8px 8px 0 var(--mint)}.plan-etapas-ok{width:100%}}
@media(prefers-reduced-motion:reduce){.plan-etapas-aviso,.plan-etapas-cuerpo{animation:none}}
.plan-fases{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;counter-reset:fase}
.plan-card{counter-increment:fase;position:relative;display:flex;flex-direction:column;gap:8px;padding:20px 18px;min-height:250px;background:var(--cream);border:1px solid var(--line);text-align:left;font:inherit;color:inherit}
.plan-card .plan-num{font:500 11px var(--mono);color:var(--green);letter-spacing:.1em}.plan-card.cerrada .plan-num{color:var(--muted)}
.plan-card h3{font-size:22px;margin:0}.plan-card p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.45}
.plan-card .plan-cuando{font:500 12.5px/1.45 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--green)}
.plan-card .plan-trae{margin-top:auto;font-size:12px;color:var(--muted)}.plan-card .plan-trae b{color:var(--ink)}
.plan-card.activa{cursor:pointer;transition:.2s}.plan-card.activa:hover,.plan-card.activa:focus{border-color:var(--green);transform:translateY(-3px);outline:none}
.plan-card.activa .plan-ir{font:700 13px var(--sans);color:var(--green)}
.plan-card.cerrada{background:transparent;border-style:dashed;opacity:.8;cursor:pointer;transition:.2s}.plan-card.cerrada:hover,.plan-card.cerrada:focus{opacity:1;border-color:var(--muted);transform:translateY(-3px);outline:none}.plan-card.cerrada .plan-ir{font:700 13px var(--sans);color:var(--muted)}.plan-card.cerrada .plan-cuando{color:var(--muted)}
.plan-card .plan-sello{position:absolute;top:16px;right:16px;font:500 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;padding:3px 7px;border:1px solid currentColor}
.plan-card.activa .plan-sello{color:var(--green)}.plan-card.cerrada .plan-sello{color:var(--muted)}
.plan-card{overflow:hidden}.plan-card .plan-img{display:block;width:calc(100% + 36px);max-width:none;margin:-20px -18px 4px;height:auto;aspect-ratio:3/2;object-fit:cover;background:#f3ebe0}
.plan-card.cerrada .plan-img{filter:saturate(.75)}.plan-card .plan-sello{background:rgba(255,253,248,.92)}
.plan-intro{display:grid;grid-template-columns:minmax(0,300px) 1fr;gap:24px;align-items:center;margin:0 0 24px;padding:18px;background:var(--cream);border:1px solid var(--line)}
.plan-intro img{width:100%;height:auto;aspect-ratio:3/2;object-fit:cover;display:block}.plan-intro h2{font-size:clamp(28px,3.4vw,42px);margin:6px 0 10px;line-height:1}.plan-intro p{margin:0;color:var(--muted);font-size:16px;max-width:760px}
@media(max-width:700px){.plan-intro{grid-template-columns:1fr}}
.plan-card .plan-trae{display:flex;flex-direction:column;align-items:stretch;gap:10px;font-size:13.5px}
.plan-card .plan-ir{display:flex;align-items:center;justify-content:center;min-height:46px;padding:12px 16px;font:700 13px var(--sans)!important;letter-spacing:.16em;text-transform:uppercase}
.plan-card.activa .plan-ir{background:var(--ink);border:1px solid var(--ink);color:#fff!important;transition:background .2s}
.plan-card.activa:hover .plan-ir,.plan-card.activa:focus .plan-ir{background:var(--green);border-color:var(--green)}
.plan-card.cerrada .plan-ir{border:1px solid var(--muted);background:transparent;color:var(--muted)!important}
.plan-card.cerrada:hover .plan-ir,.plan-card.cerrada:focus .plan-ir{border-color:var(--ink);color:var(--ink)!important}
@media(max-width:1100px){.plan-fases{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.plan-fases{grid-template-columns:1fr}.plan-card{min-height:0}}`;
    document.head.appendChild(s);
  }

  function nombreCorto() {
    const n = ($('crmName')?.textContent || '').trim();
    const w = n.split(/\s+/)[0] || '';
    return w ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : '';
  }

  function portada() {
    const caja = $('crmPlan'), crm = $('crm'); if (!caja || !crm) return;
    estilos(); FASE = null;
    crm.classList.add('plan-portada'); crm.classList.remove('plan-fase', 'plan-cerrada');
    limpiarFiltro();
    const nombre = nombreCorto();
    caja.classList.remove('hidden');
    /* Primero el aviso de las cinco etapas, en grande; con «Siguiente» se
       despliegan las cinco cajas (pedido de Ricardo, 26-oct-2026). Se ve una
       vez por pestaña y se reabre con «Cómo funcionan las cinco etapas». */
    const vista = (() => { try { return sessionStorage.getItem(AVISO_KEY) === '1'; } catch { return false; } })();
    caja.innerHTML = `<div class="plan-hola"><div class="kicker">Plan de campaña · 2027</div><h2>¡Hola${nombre ? `, ${esc(nombre)}` : ''}! Esta es tu hoja de ruta.</h2></div>
      <div class="plan-etapas-aviso${vista ? ' hidden' : ''}" role="region" aria-label="Las cinco etapas de una campaña">
        <p>Tienes cinco etapas que desarrollar en una campaña. No es una sola carrera lineal. Primero se planea, en donde la estrategia es el corazón de la campaña, lo cual depende de dónde te lanzas, tu ideología política y tu arquetipo. Después debes posicionarte, pues esto reduce costos de campaña para que el votante te conozca. Luego viene la campaña: aval, lista, inscripción y propaganda ¡a toda! Por último, el remate es el último mes, cuando la pauta pesa pero su efecto dura pocos días; ahí es donde están las mayores inversiones. Luego, el día de la elección se gana con logística: sacar a votar y cuidar el voto.</p>
        <p class="plan-etapas-cierre">Es muy importante seguir estos pasos si quieres ganar y que la campaña no te salga tan costosa.</p>
        <button type="button" class="plan-etapas-ok">Siguiente</button>
      </div>
      <div class="plan-etapas-cuerpo${vista ? '' : ' hidden'}">
      <div class="plan-sub"><p>Cinco etapas hasta el 31 de octubre de 2027. Cada una abre las herramientas que sirven en ese momento; hoy están abiertas las dos primeras.</p><button type="button" class="plan-etapas-ver">Cómo funcionan las cinco etapas</button></div>
      <div class="plan-fases">${FASES.map(f => {
        /* Las cerradas también se abren: adentro los módulos van en gris. Lo que
           trae cada una se ve al abrirla, no en la tarjeta (oct-26-2026). */
        return `<button type="button" class="plan-card ${f.activa ? 'activa' : 'cerrada'}" data-fase="${f.id}">
          <img class="plan-img" src="${IMG(f.id)}" alt="" width="600" height="400" loading="lazy" onerror="this.remove()">
          <span class="plan-sello">${f.activa ? 'Abierta' : 'Próximamente'}</span>
          <span class="plan-num">${String(FASES.indexOf(f) + 1).padStart(2, '0')}</span><h3>${esc(f.nombre)}</h3><span class="plan-cuando">${esc(f.cuando)}</span><p>${esc(f.que)}</p>
          <span class="plan-trae">${f.activa ? `<span class="plan-ir">Abrir</span>` : `<span class="plan-abre">Se abre el ${esc(fecha(f.abre))}.</span><span class="plan-ir">Ver</span>`}</span>
        </button>`;
      }).join('')}</div></div>`;
    caja.querySelectorAll('.plan-card').forEach(b => b.onclick = () => abrir(b.dataset.fase));
    const aviso = caja.querySelector('.plan-etapas-aviso'), cuerpo = caja.querySelector('.plan-etapas-cuerpo');
    caja.querySelector('.plan-etapas-ok').onclick = () => {
      try { sessionStorage.setItem(AVISO_KEY, '1'); } catch {}
      aviso.classList.add('hidden'); cuerpo.classList.remove('hidden');
      cuerpo.querySelector('.plan-card')?.focus({ preventScroll: true });
    };
    caja.querySelector('.plan-etapas-ver').onclick = () => {
      cuerpo.classList.add('hidden'); aviso.classList.remove('hidden');
      aviso.querySelector('.plan-etapas-ok').focus({ preventScroll: true });
    };
  }

  function limpiarFiltro() {
    Object.values(PIEZAS).forEach(p => p()?.classList.remove('plan-fuera'));
  }

  function abrir(id) {
    const f = FASES.find(x => x.id === id); if (!f) return;
    const caja = $('crmPlan'), crm = $('crm'); if (!caja || !crm) return;
    estilos(); FASE = id;
    crm.classList.remove('plan-portada'); crm.classList.add('plan-fase'); crm.classList.toggle('plan-cerrada', !f.activa);
    limpiarFiltro();
    Object.entries(PIEZAS).forEach(([k, p]) => { if (!f.modulos.includes(k)) p()?.classList.add('plan-fuera'); });
    /* Sin barra de navegación: para volver a las fases está «Volver» arriba. */
    const n = String(FASES.indexOf(f) + 1).padStart(2, '0');
    const trae = f.modulos.filter(m => NOMBRE_MODULO[m]).map(m => NOMBRE_MODULO[m]);
    caja.innerHTML = `<div class="plan-intro"><img src="${IMG(f.id)}" alt="" width="600" height="400" onerror="this.remove()"><div><span class="kicker">Fase ${n} · ${esc(f.cuando)}</span><h2>${esc(f.nombre)}</h2><p>${esc(f.parrafo || f.que)}</p></div></div>`
      + (f.activa ? '' : `<div class="plan-aviso" role="status"><b>Todavía no se abre.</b><span>Esta fase se abre el ${esc(fecha(f.abre))}. Lo que ve abajo es lo que va a traer${trae.length ? ` (${esc(trae.join(' · '))})` : ''}: por ahora no responde al clic.</span></div>`);
    window.scrollTo({ top: 0, behavior: 'instant' });
    /* El mapa de Leaflet mide su caja al crearse: si estuvo oculto, se le avisa. */
    setTimeout(() => { window.dispatchEvent(new Event('resize')); window.reencuadrarMapas?.(); }, 0);
  }

  function mostrar() { portada(); }

  global.C360Plan = { mostrar, abrir, portada, FASES, get fase() { return FASE; } };
})(window);
