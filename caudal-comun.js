/* caudal-comun.js — lo que comparten TODAS las páginas de Caudal
   ------------------------------------------------------------------
   Nació al sacar Contratación a su propia página (sep-2026). Hasta
   entonces estas piezas vivían repartidas entre el <script> inline de
   caudal.html (el muro del freemium, `esc`, `fmt`) y caudal-pilares.js
   (`fmtCOP`, el traductor marca→tema), y las tres se resolvían por
   `window` porque ya cruzaban de archivo. Con una segunda página que
   pinta las MISMAS listas detrás del MISMO muro, dejarlas allá obligaba
   a duplicarlas — y el muro es lo que se cobra: dos copias que se
   desincronizan es un fallo comercial, no cosmético.

   Va PRIMERO en el orden de <script> de cada página: todo lo demás lo
   consume. No depende de nada (ni siquiera de caudal-base.js): lee
   `ACCESO`/`HAS_SESSION` al ejecutarse, no al cargarse.

   ⚠️ Al tocar este archivo hay que bumpear su ?v= en las páginas que lo
   cargan (caudal.html · caudal-contratacion.html), o el navegador sirve
   la copia vieja sin dar ningún error. */
(function(){
  'use strict';

  /* ---------- formato ---------- */
  const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const fmt=n=>String(n==null?'—':n).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
  function fmtCOP(n){ if(!n||n<=0) return ''; if(n>=1e12) return '$'+(n/1e12).toFixed(1).replace('.',',')+' B'; if(n>=1e6) return '$'+fmt(Math.round(n/1e6))+' M'; return '$'+fmt(Math.round(n)); }

  /* ---------- muro del freemium ---------- */
  // El corte va DESPUÉS de ejecutar la consulta, no antes. Buscar no cuesta casi
  // nada (19 de las 23 acciones solo leen índices), así que el visitante ve
  // títulos y cifras REALES y choca con el muro justo donde empieza el trabajo:
  // la lectura del analista. Bloquear antes de buscar ahorraría cero y regalaría
  // el argumento — un blur sobre nada se huele en cinco segundos.
  const CONTACTO_MAIL='hola@ricardoruiz.co';
  // A dónde manda el muro a quien ya tiene cuenta: la compra de Caudal (SKU
  // propio, sep-2026), NO pricing.html — ahí todo lo legislativo sale gratis.
  const COMPRA_URL='caudal-pricing.html?comprar=1';
  const CORTE_LIBRE=10;
  // A dónde vuelve quien se registra desde el muro: la página en la que está,
  // no una fija. Con `caudal.html` escrito a mano, quien se registraba desde
  // Contratación aterrizaba en el paraguas y tenía que volver a buscar.
  function volverAqui(){ return (location.pathname.split('/').pop()||'caudal.html'); }
  function mailtoHref(asunto){
    const cuerpo='Hola,\n\nVi Caudal y quiero acceso.\n\nOrganización:\nSector que me interesa:\nQué necesito seguir:\n\n';
    return `mailto:${CONTACTO_MAIL}?subject=${encodeURIComponent('Caudal · '+asunto)}&body=${encodeURIComponent(cuerpo)}`;
  }
  // Devuelve {ver, fuera}: lo que se pinta entero y lo que va detrás del muro.
  function cortar(arr){
    const a=arr||[];
    if(window.ACCESO) return {ver:a, fuera:[]};
    return {ver:a.slice(0,CORTE_LIBRE), fuera:a.slice(CORTE_LIBRE)};
  }
  // `fuera` son los items que sobraron; `render` es la misma función con la que
  // se pintan los visibles, para que lo difuminado sea el contenido de verdad.
  function muroLista(fuera, render, sing, plu, asunto){
    if(!fuera||!fuera.length) return '';
    const n=fuera.length;
    const registrado=window.HAS_SESSION;
    return `<div class="muro">
      <div class="muro-tapa">${fuera.slice(0,4).map(render).join('')}</div>
      <div class="muro-cta">
        <div class="muro-n">y ${fmt(n)} ${n===1?sing:plu} más</div>
        <div class="muro-t">${registrado?'Con acceso a Caudal ves el archivo completo, la lectura del analista y las alertas por perfil.':'Crea una cuenta gratis para ver una muestra de los resultados.'}</div>
        <a class="muro-btn" href="${registrado?COMPRA_URL:'register.html?next='+encodeURIComponent(volverAqui())}">${registrado?'Conseguir acceso →':'Registrarme gratis →'}</a>
      </div></div>`;
  }
  // Envoltorio para las listas de los pilares, que son todas de la misma forma
  // (`d.resultados` + su tarjeta). Los LANDINGS ("lo último publicado") NO se
  // cortan a propósito: son el escaparate, y recortarlos haría que la página se
  // sienta mezquina antes de que el visitante busque nada.
  function listaConMuro(items, card, sing, plu, asunto, vacio){
    const c=cortar(items||[]);
    const cuerpo=c.ver.map(card).join('')||`<div class="err">${vacio}</div>`;
    return `<div class="sanc-list">${cuerpo}</div>`+muroLista(c.fuera, card, sing, plu, asunto);
  }
  function muroLectura(asunto){
    const registrado=window.HAS_SESSION;
    return `<div class="muro-blk">
      <div class="tag">◈ Lectura del analista</div>
      <div class="t">Acá va la lectura: qué patrón siguen estos intentos, por qué se caen y qué predice eso del que está en trámite. Se escribe sobre los mismos datos que acabas de ver, y va con acceso.</div>
      <a class="muro-btn" href="${registrado?COMPRA_URL:'register.html?next='+encodeURIComponent(volverAqui())}">${registrado?'Conseguir acceso →':'Registrarme gratis →'}</a>
    </div>`;
  }

  /* ---------- traductor marca → tema (diccionario de empresas) ---------- */
  /* El usuario buscó «Uber» y le salen proyectos que dicen "plataformas
     tecnológicas": tiene que ver POR QUÉ. Mismo principio que el aviso de
     sinónimos y el de búsqueda flexible — nada aparece por magia.
     `_ampliarEmp` alterna núcleo (preciso, por defecto) ↔ núcleo + contexto.
     Va en `window` porque lo alterna el enlace «ampliar» de acá y lo leen la
     búsqueda universal (caudal.html) y el pilar de contratación (su página). */
  window._ampliarEmp=false;
  function empresaHint(emps, id, modo){
    if(!emps||!emps.length) return '';
    const e=emps[0], esGremio=e.tipo==='gremio';
    // En CONTRATACIÓN el diccionario juega su otra cara: acá la empresa sí
    // aparece con nombre propio (es el proveedor), así que no se traduce a
    // tema — se filtra por identidad. Ampliar = ver todo lo que menciona la
    // marca, con los homónimos que eso arrastra.
    if(modo==='contratacion'){
      const mas=` <span class="bd-link" id="${id}-mas">${window._ampliarEmp?'volver a solo sus contratos':'ampliar: ver todo lo que menciona «'+esc(e.nombre)+'»'} →</span>`;
      return `<div class="broaden" id="${id}"><b>${esc(e.nombre)}</b> ${esGremio?'es un gremio':'es una empresa'} del diccionario de Caudal.
        ${window._ampliarEmp
          ? 'Estás viendo <b>todo lo que menciona su nombre</b> en SECOP — incluye homónimos (en Colombia hay personas que se apellidan así).'
          : 'Se filtró por <b>identidad del proveedor</b>: son los contratos que <b>son de la empresa</b>, no los que nombran la marca.'}${mas}</div>`;
    }
    const nuc=(e.nucleo||[]).map(esc).join(' · ');
    const ctx=(e.contexto||[]);
    const mas=ctx.length
      ? ` <span class="bd-link" id="${id}-mas">${window._ampliarEmp?'volver a lo esencial':'ampliar a: '+ctx.map(esc).join(' · ')} →</span>`
      : '';
    return `<div class="broaden" id="${id}"><b>${esc(e.nombre)}</b> ${esGremio?'es un gremio':'es una empresa'} del diccionario de Caudal.
      El Estado no legisla marcas, legisla actividades — así que se buscó por: <b>${nuc}</b>${window._ampliarEmp&&ctx.length?' · '+ctx.map(esc).join(' · '):''}.${mas}</div>`;
  }
  function wireEmpresaHint(id, rerun){
    const el=document.getElementById(id+'-mas'); if(!el) return;
    el.onclick=()=>{ window._ampliarEmp=!window._ampliarEmp; rerun(); };
  }

  /* ── El cargador de Caudal: un mar con un barco que lo cruza ──────────────
     Pedido de Ricardo (oct-26-2026): las lecturas tardan de 5 a 7 segundos y
     un texto suelto que dice «cargando» se lee como página colgada. El barco
     cruza en ~6,5 s y los tres mensajes rotan cada ~2,2 s, así que en una
     espera normal se alcanza a ver el ciclo completo. Todo en CSS: no hay
     temporizadores que limpiar cuando el contenido real reemplaza al cargador.
     Con «reducir movimiento» queda quieto. Siempre tres mensajes: si llegan
     menos se repite el último, porque la animación está hecha para tres. */
  const MAR_CSS = `
  .cau-mar{display:flex;flex-direction:column;align-items:center;gap:.55rem;padding:1.1rem 0 .6rem;color:var(--ink2,#4d5462)}
  .cau-mar svg{width:min(320px,100%);height:auto;overflow:hidden;border-radius:0 0 10px 10px}
  .cau-mar .cm-ola{fill:var(--teal-soft,rgba(152,192,248,.22));animation:cmOla 3.2s linear infinite}
  .cau-mar .cm-cresta{fill:none;stroke:var(--teal,#3d6eb8);stroke-width:1.4;stroke-linecap:round;animation:cmOla 3.2s linear infinite}
  .cau-mar .cm-ola.o2{fill:var(--teal-dim,rgba(152,192,248,.4));stroke:none;opacity:.55;animation-duration:5.4s;animation-direction:reverse}
  .cau-mar .cm-barco{animation:cmCruza 6.5s linear infinite}
  .cau-mar .cm-bob{animation:cmBob 1.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  .cau-mar .cm-casco{fill:var(--ink,#14161c)} .cau-mar .cm-vela{fill:var(--teal,#3d6eb8)}
  .cau-mar .cm-msgs{position:relative;height:1.3em;width:100%;font-size:.78rem;text-align:center}
  .cau-mar .cm-msgs span{position:absolute;left:0;right:0;opacity:0;animation:cmMsg 6.6s linear infinite}
  .cau-mar .cm-msgs span:nth-child(2){animation-delay:2.2s} .cau-mar .cm-msgs span:nth-child(3){animation-delay:4.4s}
  .cau-mar.mini{flex-direction:row;padding:.2rem 0;gap:.7rem} .cau-mar.mini svg{width:110px}
  .cau-mar.mini .cm-msgs{text-align:left;font-size:.76rem}
  @keyframes cmOla{from{transform:translateX(0)}to{transform:translateX(-80px)}}
  @keyframes cmCruza{from{transform:translateX(-40px)}to{transform:translateX(330px)}}
  @keyframes cmBob{0%,100%{transform:translateY(0) rotate(-4deg)}50%{transform:translateY(3px) rotate(4deg)}}
  @keyframes cmMsg{0%{opacity:0;transform:translateY(4px)}5%,28%{opacity:1;transform:none}33%,100%{opacity:0;transform:translateY(-4px)}}
  @media (prefers-reduced-motion:reduce){.cau-mar *{animation:none!important}.cau-mar .cm-barco{transform:translateX(150px)}.cau-mar .cm-msgs span:first-child{opacity:1}}`;
  function marCss(){
    if(document.getElementById('cau-mar-css')) return;
    const st=document.createElement('style'); st.id='cau-mar-css'; st.textContent=MAR_CSS;
    document.head.appendChild(st);
  }
  function mar(msgs, opt){
    marCss();
    const m=(Array.isArray(msgs)&&msgs.length?msgs:['Cargando…']).slice(0,3);
    while(m.length<3) m.push(m[m.length-1]);
    // una ola de periodo 80: el trazo mide 400 y se corre 80 por ciclo, sin costura
    const cresta=y=>{ let d=`M-80 ${y}`; for(let x=-80;x<400;x+=80) d+=` q20 -7 40 0 t40 0`; return d; };
    const ola=y=>cresta(y)+` V70 H-80 Z`;
    return `<div class="cau-mar${opt&&opt.mini?' mini':''}" role="status" aria-live="polite">
      <svg viewBox="0 0 320 70" aria-hidden="true">
        <path class="cm-ola o2" d="${ola(44)}"/>
        <g class="cm-barco"><g class="cm-bob">
          <path class="cm-vela" d="M14 34 V14 L26 32 Z"/><path class="cm-vela" d="M12 34 V20 L5 33 Z" opacity=".6"/>
          <path class="cm-casco" d="M2 35 H30 L25 41 H7 Z"/></g></g>
        <path class="cm-ola" d="${ola(40)}"/><path class="cm-cresta" d="${cresta(40)}"/>
      </svg>
      <div class="cm-msgs">${m.map(t=>`<span>${esc(t)}</span>`).join('')}</div></div>`;
  }

  /* Todo se publica en `window` porque así es como ya se consumía entre
     archivos: el código de las vistas usa estos nombres como identificador
     suelto (`esc(...)`, `listaConMuro(...)`) y resuelve contra el global. */
  Object.assign(window, {
    esc, fmt, fmtCOP,
    CONTACTO_MAIL, COMPRA_URL, CORTE_LIBRE, mailtoHref, volverAqui,
    cortar, muroLista, listaConMuro, muroLectura,
    empresaHint, wireEmpresaHint, mar,
  });
})();
