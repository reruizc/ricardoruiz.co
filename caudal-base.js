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

  /* ---------- cursor ---------- */
  const cur=document.getElementById('cur'), ring=document.getElementById('curRing');
  // Sin los dos nodos no hay cursor propio que mover; sin la guarda, el listener
  // reventaría en cada movimiento del mouse y se llevaría por delante lo demás.
  if(cur&&ring){
  addEventListener('mousemove',e=>{cur.style.left=ring.style.left=e.clientX+'px'; cur.style.top=ring.style.top=e.clientY+'px';});
  addEventListener('mouseover',e=>{const h=e.target.closest('button,a,.chip,.tl-item,input,select,.modal-close,.info-i,.pcard.live,.pcard.data,.pill-back,.sec-card,.pf-sug div,.chip .x'); ring.style.opacity=h?'1':'.5'; ring.style.transform=`translate(-50%,-50%) scale(${h?1.4:1})`;});
  }
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
  const user=uRaw?JSON.parse(uRaw):null;
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
      nl.innerHTML='<a href="portada-caudal.html" class="e-btn-back" id="navBack">← Caudal</a>'
                 + '<a href="login.html" class="e-btn-logout nav-login" style="text-decoration:none">Iniciar sesión</a>';
      pintarBack();
      return;
    }
    // La entrada de Caudal siempre es su propia portada; el dashboard no debe
    // interrumpir la navegación entre la explicación del producto y el panel.
    nl.innerHTML='<a href="portada-caudal.html" class="e-btn-back" id="navBack">← Caudal</a>'
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
  function pintarBack(){
    const nb=document.getElementById('navBack'); if(!nb) return;
    if(_view==='cliente'){
      nb.hidden=false; nb.textContent='← Volver a Caudal';
      nb.onclick=e=>{ e.preventDefault(); showView('home'); };
      return;
    }
    const prev=_navStack[_navStack.length-1];
    if(prev){
      nb.hidden=false; nb.textContent='← Volver';
      nb.onclick=e=>{ e.preventDefault(); irAtras(); };
      return;
    }
    // pila vacía: el enlace hace lo suyo (dashboard o el sitio) según la nav.
    // El invitado no tiene a dónde salir, así que ahí el botón se esconde.
    nb.onclick=null;
    nb.hidden=!!IS_GUEST;
    if(!IS_GUEST) nb.textContent='← Caudal';
  }
  function irAtras(){
    const prev=_navStack.pop();
    if(prev) showView(prev,{atras:true});
  }

  // Pila de vistas: «atrás» devuelve al sitio DE DONDE VINIMOS, no a la portada.
  // Antes, entrar por la búsqueda universal a un pilar y darle atrás te sacaba a
  // la portada y te hacía repetir la consulta.
  let _navStack=[];
  function showView(v,opt){
    if(_view && _view!==v && !(opt&&opt.atras)){
      _navStack.push(_view);
      if(_navStack.length>24) _navStack.shift();   // tope: es historial, no un log
    }
    _view=v;
    ['home','buscar','congreso','control','regulatorio','ejecutivo','sucop','contratacion','cliente','medios','radicados','bancadas','coaliciones'].forEach(n=>{ const el=document.getElementById('view-'+n); if(el) el.hidden=(v!==n); });
    window.scrollTo(0,0);
    pintarBack();
    if(v==='congreso') requestAnimationFrame(()=>document.querySelectorAll('#view-congreso .mort-bar').forEach(x=>x.style.height=x.dataset.h+'%'));
    if(v==='regulatorio') hook('regLoadStats');
    if(v==='ejecutivo') hook('ejeLoadStats');
    // SUCOP se recarga en CADA entrada, no solo la primera: su landing es una
    // cuenta regresiva y un caché de sesión la dejaría mintiendo.
    if(v==='sucop') hook('sucLoadStats');
    if(v==='contratacion') hook('conLoadStats');
    if(v==='medios') hook('medLoadLanding');
    if(v==='control') hook('controlLoad');
    if(v==='radicados') hook('radLoad');
    if(v==='bancadas') hook('bancLoad');
    if(v==='coaliciones') hook('coaLoad');
  }

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
