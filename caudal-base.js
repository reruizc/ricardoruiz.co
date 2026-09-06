/* caudal-base.js — el «shell» de caudal.html
   ------------------------------------------------------------------
   Lo que NO pertenece a ninguna vista en particular: acceso y sesión,
   cursor propio, el helper `call()` contra el worker y el router de
   vistas. La lógica de las 13 vistas sigue en el <script> inline de
   caudal.html; este archivo solo le presta el chasis.

   Es un IIFE: lo que la página necesita se publica al final con
   Object.assign(window, {...}), y a la inversa este archivo llama por
   `window` a los hooks de las vistas (initHome, loadStats, regLoadStats
   y compañía) — siempre con guarda de `typeof`, porque una vista que
   todavía no se ha definido no puede tumbar el shell entero.

   ⚠️ Al tocar este archivo hay que bumpear el ?v= del <script> que lo
   carga en caudal.html, o el navegador sirve la copia vieja. */
(function(){
  'use strict';
  /* La API se consume por el worker, no contra la Lambda directamente. El worker
     limita por IP (el throttle de API Gateway es global al stage y no distingue
     un scraper de un cliente), decide quién tiene acceso y se lo dice a la
     Lambda con un secreto compartido, y de paso deja de publicar la URL de la
     Lambda en un repo abierto. Ver rr-auth · ruta /caudal/api. */
  const API = 'https://rr-auth.reruizc.workers.dev/caudal/api';
  /* Lista de EMERGENCIA, no la whitelist. Quién entra a Caudal lo decide el
     worker (`/caudal/acceso/me`, llaves `caudal:acceso:<correo>` en KV), que se
     otorga y revoca con tools/caudal/acceso/ sin tocar código. Esta lista solo
     se usa si el worker NO responde: sin ella, una caída dejaría a Ricardo y a
     los socios por fuera de su propia plataforma; con ella, nadie nuevo entra
     durante la caída. Agregar gente ACÁ ya no sirve — hay que otorgar por CLI. */
  const EMERGENCIA = ['reruizc@gmail.com', 'nuevagemela@gmail.com', 'diego@cauce.co'];

  // tooltips ⓘ: toggle al click; cierra al clickear afuera
  addEventListener('click',e=>{
    const i=e.target.closest('.info-i');
    document.querySelectorAll('.info-i.open').forEach(x=>{ if(x!==i) x.classList.remove('open'); });
    if(i){ i.classList.toggle('open'); e.stopPropagation(); }
  });

  /* ---------- acceso temporal por link (sin registro, para socios) ---------- */
  // El token NO vive aquí: se pasa por query string (?acceso=...) y se valida
  // contra el worker (`/caudal/guest`), que lo busca en KV. Así el HTML público
  // no expone ningún secreto y el acceso se revoca borrando la llave del KV
  // (o dejando que expire su TTL) — sin tocar ni redesplegar esta página.
  // Sembrar/revocar: ver CLAUDE.md · sección "acceso de invitado a Caudal".
  // Se guarda para que `call()` lo reenvíe: el worker necesita reconocer al
  // invitado en CADA petición, no solo al abrir la página.
  let GUEST_TOKEN='';
  async function checkShareAccess(){
    const p=(new URLSearchParams(location.search).get('acceso')||'').trim();
    if(!p) return false;
    try{
      const r=await fetch(`https://rr-auth.reruizc.workers.dev/caudal/guest?token=${encodeURIComponent(p)}`);
      const d=await r.json();
      const val=!!(d && d.ok && d.valid);
      if(val) GUEST_TOKEN=p;
      return val;
    }catch(e){ return false; }
  }

  /* ---------- acceso (esto YA NO es un gate: la página es pública) ---------- */
  // Caudal se abre al público. El acceso dejó de decidir SI entras y ahora decide
  // QUÉ ves: el dato es de todos, lo que se cobra es la lectura. Por eso la página
  // revela DE UNA y la autorización se resuelve en segundo plano — dejar al
  // visitante frente a una pantalla de "verificando" mientras responde el worker
  // es la versión educada del "contáctenos" de la competencia.
  const token=localStorage.getItem('rr-token'); const uRaw=localStorage.getItem('rr-user');
  let user=null; try{user=uRaw?JSON.parse(uRaw):null;}catch(e){}
  const enEmergencia=em=>!!em&&EMERGENCIA.includes(String(em).toLowerCase().trim());
  const toLogin=()=>{localStorage.removeItem('rr-token');localStorage.removeItem('rr-user');location.replace('login.html');};
  // ACCESO decide el muro · IS_GUEST es invitado por link (sin cuenta → no puede
  // guardar perfiles, el worker exige sesión) · HAS_SESSION es "hay cuenta".
  // Van en `window` (y no en un `let` del closure) porque las vistas, que
  // siguen en el <script> inline de la página, los leen como identificador
  // suelto: `cortar()` mira ACCESO y `muroLista()` mira HAS_SESSION.
  window.ACCESO=false; window.IS_GUEST=false; window.HAS_SESSION=!!(token&&user);

  (async()=>{
    if(await checkShareAccess()) return setAcceso(true,{guest:true});
    if(!HAS_SESSION) return;          // visitante: se queda con la versión abierta
    const H={Authorization:`Bearer ${token}`};
    const B='https://rr-auth.reruizc.workers.dev';
    let meRes, acRes;
    try{
      [meRes, acRes]=await Promise.all([
        fetch(`${B}/auth/me`,{headers:H}),
        fetch(`${B}/caudal/acceso/me`,{headers:H}),
      ]);
    }catch(e){
      // worker inalcanzable: la lista de emergencia evita que una caída deje a
      // Ricardo y a los socios en la versión gratis de su propia plataforma.
      return setAcceso(enEmergencia(user.email));
    }
    if(meRes.status===401||acRes.status===401){
      // sesión vencida: se limpia para que la nav ofrezca entrar de nuevo, pero
      // NO se le echa de la página — se queda viendo la versión abierta.
      localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user');
      HAS_SESSION=false; return setAcceso(false);
    }
    try{
      const d=await meRes.json();
      if(d&&d.ok&&d.user) localStorage.setItem('rr-user',JSON.stringify(Object.assign({},user,d.user)));
    }catch(e){ /* el refresco del perfil no decide el acceso */ }
    let ac=null;
    try{ ac=await acRes.json(); }catch(e){ /* cae a emergencia abajo */ }
    if(ac&&ac.ok&&typeof ac.acceso==='boolean') return setAcceso(ac.acceso);
    return setAcceso(enEmergencia(user.email));
  })();

  function reveal(){
    const g=document.getElementById('gate'); if(g) g.remove();
    // Siempre presente: el muro (CSS y render) se cuelga de este atributo, y el
    // visitante sin sesión no pasa por setAcceso(). Sin esto quedaría en
    // `undefined` y el blur no sabría a qué lado está.
    document.body.dataset.acceso='0';
    const nav=document.getElementById('topNav'); if(nav) nav.hidden=false;
    const app=document.getElementById('app'); if(app) app.hidden=false;
    pintarNav();
    hook('initHome');
    hook('loadStats');
  }

  // Llega ~medio segundo después de revelar. Repinta lo que depende del acceso;
  // los resultados consultan ACCESO al pintarse, y para entonces ya está resuelto
  // (el visitante todavía no ha alcanzado a buscar nada).
  function setAcceso(v,opt){
    ACCESO=!!v; IS_GUEST=!!(opt&&opt.guest);
    document.body.dataset.acceso=ACCESO?'1':'0';
    pintarNav();
    if(ACCESO && !IS_GUEST && HAS_SESSION){
      hook('pfLoadList'); call({action:'perfil_meta'}).then(m=>{window.PF_META=m;}).catch(()=>{});
      // ENTRAR POR EL CLIENTE, no por la portada de pilares: quien tiene acceso
      // abre Caudal en el radar de su cliente («el i-ching del día», pedido de
      // Pablo). Va acá y no en initHome porque ahí el acceso aún no se ha
      // resuelto. Solo si la URL no pide otra cosa y el usuario no navegó ya.
      const sinDestino=!location.hash && !(new URLSearchParams(location.search).get('tema'));
      const enHome=!document.getElementById('view-home').hidden;
      if(sinDestino && enHome){ window.CLI_AUTO_PERFIL=true; showView('cliente'); }
    }
  }

  function pintarNav(){
    const nl=document.querySelector('.e-nav-left'); if(!nl) return;
    if(IS_GUEST){
      // el invitado no tiene a dónde salir, pero sí navega entre vistas: se le
      // deja el atrás (sin href — solo actúa cuando hay pila).
      nl.innerHTML='<a class="e-btn-back" id="navBack" href="#">← Volver</a>'
                 + '<span class="priv-badge">Vista de invitado</span>';
      pintarBack();
      return;
    }
    if(!HAS_SESSION){
      // La entrada pública de esta plataforma es su portada, no la página raíz.
      nl.innerHTML='<a href="caudal-portada.html" class="e-btn-back" id="navBack">← Caudal</a>'
                 + '<a href="login.html?next=caudal.html" class="e-btn-logout nav-login" style="text-decoration:none">Iniciar sesión</a>';
      pintarBack();
      return;
    }
    // La entrada de Caudal siempre es su propia portada; el dashboard no debe
    // interrumpir la navegación entre la explicación del producto y el panel.
    nl.innerHTML='<a href="caudal-portada.html" class="e-btn-back" id="navBack">← Caudal</a>'
               + (ACCESO?'<span class="priv-badge">Cliente</span>':'')
               + '<button class="e-btn-logout" id="navLogout" type="button">Salir</button>';
    const lo=document.getElementById('navLogout'); if(lo) lo.onclick=toLogin;
    pintarBack();
  }

  async function call(payload){
    // La sesión va en cada petición: es lo que el worker usa para saber si quien
    // llama tiene acceso y, con eso, si le pone la credencial a la Lambda. Sin
    // ella la consulta igual responde — con el resumen real y sin la lectura.
    const h={'Content-Type':'application/json'};
    const t=localStorage.getItem('rr-token');
    if(t) h.Authorization=`Bearer ${t}`;
    // El invitado por link no tiene sesión; su token viaja en el cuerpo porque
    // una cabecera propia dispararía preflight (ver la ruta en el worker).
    const body=GUEST_TOKEN?Object.assign({},payload,{_guest:GUEST_TOKEN}):payload;
    const r=await fetch(API,{method:'POST',headers:h,body:JSON.stringify(body)});
    return r.json();
  }

  let _view='home';
  // Pinta el botón «atrás» según la pila. Se llama desde showView Y desde
  // pintarNav, porque pintarNav REHACE el botón con innerHTML: sin volver a
  // cablear aquí, el enlace se queda con su href y saca al usuario del producto.
  const VIEW_NAMES={home:'Explorar Caudal',buscar:'Resultados de búsqueda',congreso:'Congreso',control:'Órganos de control',regulatorio:'Regulatorio',ejecutivo:'Ejecutivo',sucop:'Consulta pública',gacetas:'Gacetas',contratacion:'Contratación',cliente:'Radar',medios:'Medios',radicados:'Últimos radicados',bancadas:'Disciplina de bancada',coaliciones:'Coaliciones'};
  const VIEW_PARENT={radicados:'congreso',bancadas:'congreso',coaliciones:'bancadas'};
  let _navStack=[];
  function pintarBack(){
    const nb=document.getElementById('navBack'); if(!nb) return;
    nb.hidden=false;
    if(_view==='home'){
      nb.textContent='← Qué es Caudal'; nb.href='caudal-portada.html'+(GUEST_TOKEN?'?acceso='+encodeURIComponent(GUEST_TOKEN):''); nb.onclick=null;
      return;
    }
    const prev=_navStack[_navStack.length-1]||VIEW_PARENT[_view]||'home';
    nb.textContent='← '+VIEW_NAMES[prev]; nb.href='#'+prev;
    nb.onclick=e=>{if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;e.preventDefault();irAtras();};
  }
  function irAtras(){
    if(_navStack.length){history.back();return;}
    showView(VIEW_PARENT[_view]||'home',{atras:true});
  }
  function showView(v,opt={}){
    if(!Object.prototype.hasOwnProperty.call(VIEW_NAMES,v)) return;
    const changed=_view!==v;
    if(changed && !opt.initial && !opt.history){
      _navStack.push(_view||'home');
      if(_navStack.length>24)_navStack.shift();
      history.pushState({caudal:true,stack:_navStack.slice()},'',location.pathname+location.search+'#'+v);
    }else if(opt.initial){
      _navStack=[];
      history.replaceState({caudal:true,stack:[]},'',location.pathname+location.search+'#'+v);
    }
    _view=v;
    Object.keys(VIEW_NAMES).forEach(n=>{const el=document.getElementById('view-'+n);if(el)el.hidden=(v!==n);});
    window.scrollTo({top:0,behavior:'instant'});
    pintarBack();
    if(changed){
      document.dispatchEvent(new CustomEvent('caudal:view',{detail:v}));
      const target=document.querySelector('#view-'+v+' h1, #view-'+v+' input');
      if(target&&!opt.initial){if(target.tagName==='H1')target.setAttribute('tabindex','-1');target.focus({preventScroll:true});}
    }
    if(v==='congreso') requestAnimationFrame(()=>document.querySelectorAll('#view-congreso .mort-bar').forEach(x=>x.style.height=x.dataset.h+'%'));
    if(v==='regulatorio') hook('regLoadStats');
    if(v==='ejecutivo') hook('ejeLoadStats');
    if(v==='sucop') hook('sucLoadStats');
    if(v==='gacetas') hook('gacLoadStats');
    if(v==='contratacion') hook('conLoadStats');
    if(v==='medios') hook('medLoadLanding');
    if(v==='control') hook('controlLoad');
    if(v==='radicados') hook('radLoad');
    if(v==='bancadas') hook('bancLoad');
    if(v==='coaliciones') hook('coaLoad');
  }
  addEventListener('popstate',e=>{
    const raw=location.hash.slice(1)||'home';
    const v=raw==='sextante'?'cliente':raw;
    if(!Object.prototype.hasOwnProperty.call(VIEW_NAMES,v)) return;
    _navStack=e.state&&e.state.caudal?e.state.stack||[]:[];
    showView(v,{history:true});
  });

  /* ---------- hooks de las vistas ----------
     Viven en el <script> inline de caudal.html y se publican en `window` al
     final de ese script. Se llaman con guarda porque el shell corre ANTES:
     si algo no está definido todavía (o desaparece de la página), el router
     sigue funcionando en vez de reventar. */
  /* El puente hacia las vistas, que viven en los otros archivos y se cargan
     después. La guarda de `typeof` es lo que hace que el orden de los
     <script> no importe, pero cambia el modo de falla: sin el warn, un
     loader renombrado —o un módulo que no cargó— deja la vista vacía y NO
     dice nada. El aviso es lo único que separa "no hay datos" de "está
     roto". */
  function hook(n,...a){
    const f=window[n];
    if(typeof f==='function') return f(...a);
    console.warn(`[caudal] hook «${n}» no está definido: la vista va a quedar `
      +`vacía. ¿Se renombró la función, o no cargó su archivo?`);
  }

  /* Lo que el <script> inline de caudal.html necesita de acá. Los nombres se
     conservan tal cual: el código de las vistas los usa como identificador
     suelto y resolverían igual contra `window`. */
  Object.assign(window, {
    call, showView, reveal, setAcceso, pintarNav, pintarBack, irAtras, toLogin,
  });
})();
