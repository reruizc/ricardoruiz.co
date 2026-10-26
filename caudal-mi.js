/* Mi Caudal · el espacio personal de la cuenta.

   La organización declarada se guarda, pero NO se envía al radar sectorial:
   el gratuito ve el contexto de su sector, no un análisis de su empresa. El
   worker resuelve el acceso, nunca `rr-user.plan`.

   Corre sobre el chasis compartido: `esc`/`fmt` vienen de caudal-comun.js y
   `call()` de caudal-base.js, que ya lleva el token de sesión, el token de
   invitado y la cabecera de cuota. Acá solo queda `api()` para las dos rutas
   del worker que viven fuera de /caudal/api.
   ⚠️ Al tocar este archivo hay que bumpear su ?v= en caudal-mi.html. */
(function(){
'use strict';
const API='https://rr-auth.reruizc.workers.dev', $=id=>document.getElementById(id);
let state=null, revision=0;
const safeUrl=value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:'';}catch{return '';}};
async function api(path,body){
  const token=localStorage.getItem('rr-token');
  const r=await fetch(API+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})});
  let d;try{d=await r.json();}catch{throw new Error('No pudimos leer la respuesta. Intenta de nuevo.');}
  if(!r.ok||d.error){const e=new Error(d.detalle||d.error||'No pudimos consultar Caudal.');e.status=r.status;throw e;}
  return d;
}
function organization(){const required=$('tipo').value==='organizacion';$('org-field').hidden=!required;$('organizacion').required=required;}
function form(edit=false){
  revision++;hoyStop();$('refresh').disabled=false;
  $('workspace').hidden=true;$('setup').hidden=false;$('status').textContent='';
  $('setup-title').textContent=edit?'Tu contexto, actualizado.':'Empecemos por ti.';
  const c=state.cuenta||state.sugerido||{};
  $('tipo').value=c.tipo||'organizacion';$('organizacion').value=c.organizacion||'';
  $('sector').innerHTML='<option value="">Selecciona tu sector</option>'+Object.entries(state.sectores).map(([k,v])=>`<option value="${esc(k)}">${esc(v)}</option>`).join('');
  $('sector').value=c.sector||'';$('rol').value=c.rol||'';$('cancel').hidden=!state.cuenta;
  $('form-error').textContent='';organization();
}
function workspace(){
  const c=state.cuenta, paid=state.acceso;
  $('setup').hidden=true;$('workspace').hidden=false;$('status').textContent='';
  // sin acceso no hay clientes que mirar: el bloque no existe para esa cuenta
  hoyStop(); $('hoy').hidden=true;
  $('level').textContent=paid?'ACCESO PERSONALIZADO':'CUENTA GRATUITA · CONTEXTO SECTORIAL';
  $('context-title').textContent=state.sectores[c.sector]||c.sector;
  $('context-copy').textContent=[c.organizacion||(c.tipo==='independiente'?'Independiente':'Sin organización'),c.rol].join(' · ')+(paid?'. Tus perfiles empresariales están disponibles abajo.':'. Estás viendo el contexto de tu sector, no un análisis específico de tu organización.');
  // Con acceso, la ficha «Acceso personalizado» sobra: el resumen de arriba ya
  // dice para quién es. «Editar mis datos» pasa a la cabecera del sector.
  $('mi-ctx').hidden=!!paid;$('edit2').hidden=!paid;$('upgrade').hidden=paid;
  $('explorar').hidden=!paid;
  loadSector();if(paid){ loadProfiles(); loadEmpresas(); }
}
let PERFILES=[], EMP_LISTO=false;
const normTxt=t=>String(t||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().trim();
async function loadProfiles(){
  const account=state;
  try{
    const d=await api('/caudal/perfil/list');if(account!==state)return;
    PERFILES=d.perfiles||[];
    // la URL pide una empresa (?empresa=): el resumen es de ella, no de la cuenta
    if(EMP_ACTIVA||(empresaUrl()&&!EMP_LISTO)) return;
    hoyPerfilPorDefecto();
  }catch(e){ if(account===state){ $('hoy').hidden=false; $('hoy-estado').textContent=e.message; } }
}
/* El resumen abre en el perfil de la organización de la cuenta (Cauce para
   Cauce); si no hay uno con ese nombre, el último trabajado, y si no el
   primero. Ya no se ofrece «cambiar de cliente»: las empresas se abren desde
   «Empresas disponibles». */
function hoyPerfilPorDefecto(){
  if(!PERFILES.length) return;
  const org=normTxt(state&&state.cuenta&&state.cuenta.organizacion), ult=ultimoPerfil();
  const p=PERFILES.find(x=>org&&normTxt(x.nombre)===org)||PERFILES.find(x=>x.perfilId===ult)||PERFILES[0];
  loadHoy(p.perfilId);
}
/* ══ Empresas disponibles ═══════════════════════════════════════════════
   Los perfiles de cliente REAL del motor (DiDi · Binance · Comfama…), que
   `perfil_meta` entrega como plantillas con la marca `cliente`. Solo los ve
   el equipo (llave 'caudal-equipo' de /auth/me, la misma que usa la Rosa
   para sus chips): son prospectos con nombre y un usuario nuevo no tiene por
   qué saber quién está en conversaciones con Cauce. La ficha se despliega acá
   mismo; el radar vive en la Rosa y se abre con ?sector=<k>#cliente. */
const LOGOS='https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/caudal/logos/';
function esEquipo(){
  try{ const u=JSON.parse(localStorage.getItem('rr-user')||'null'); return !!(u&&Array.isArray(u.accesos)&&u.accesos.includes('caudal-equipo')); }
  catch(e){ return false; }
}
let EMP_LIST=[], EMP_OPEN='', EMP_ACTIVA='';
function empLogo(p){
  const ini=(p.nombre||'?').split(/\s+/).map(w=>w[0]).join('').slice(0,2).toUpperCase();
  // si el logo no existe se cae a las iniciales, nunca a una imagen rota
  return `<span class="mi-emp-logo"><img src="${LOGOS}${encodeURIComponent(p.k)}.png" alt="" loading="lazy"
    onerror="this.parentNode.classList.add('ini');this.replaceWith(document.createTextNode('${esc(ini)}'))"></span>`;
}
function empFicha(p){
  const li=a=>(a||[]).map(x=>`<li>${esc(typeof x==='string'?x:(x&&x.nombre)||'')}</li>`).join('');
  const lineas=(p.lineas||[]).map(l=>`<span>${esc(l.nombre)}${l.comision?` · <b>${esc(l.comision)}</b>`:''}</span>`).join('');
  const comp=(p.competencia||[]).map(x=>typeof x==='string'?x:(x&&x.nombre)||'').filter(Boolean);
  return `<div class="mi-emp-ficha" id="emp-ficha">
    ${p.que_hace?`<h4>Qué hace</h4><p>${esc(p.que_hace)}</p>`:''}
    ${lineas?`<h4>Líneas de negocio y su comisión</h4><div class="mi-emp-lineas">${lineas}</div>`:''}
    <div class="mi-emp-cols">
      <div>
        ${p.decisiones&&p.decisiones.length?`<h4>Qué decide con esto</h4><ul>${li(p.decisiones)}</ul>`:''}
        ${p.relojes&&p.relojes.length?`<h4>Sus relojes</h4><ul>${li(p.relojes)}</ul>`:''}
      </div>
      <div>
        ${p.interlocutores&&p.interlocutores.length?`<h4>Interlocutores</h4><ul>${li(p.interlocutores)}</ul>`:''}
        ${comp.length?`<h4>Competencia vigilada</h4><ul>${comp.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}
        ${p.lector?`<h4>Quién lee el brief</h4><p>${esc(p.lector)}</p>`:''}
      </div>
    </div>
    <div class="mi-emp-acts">
      ${p.k===EMP_ACTIVA?'':`<button type="button" class="btn-t" data-emp-ir="${esc(p.k)}">Ir a ${esc(p.nombre)}</button>`}
      <button type="button" class="btn-g" data-emp-cerrar>Cerrar ficha</button>
    </div>
  </div>`;
}
function empRender(){
  const box=$('empresas-grid'); if(!box) return;
  box.innerHTML=EMP_LIST.map(p=>`<button type="button" class="mi-emp${p.k===EMP_OPEN||p.k===EMP_ACTIVA?' on':''}" data-emp="${esc(p.k)}" aria-expanded="${p.k===EMP_OPEN}">
      ${empLogo(p)}
      <span><span class="mi-emp-n">${esc(p.nombre)}</span>
        <span class="mi-emp-d">${esc(p.descripcion||'')}</span>
        <span class="mi-emp-m">${(p.lineas||[]).length} líneas · ${(p.temas||[]).length} temas${p.comision?` · ${esc(p.comision)}`:''}</span></span>
    </button>`).join('');
  const abierta=EMP_LIST.find(p=>p.k===EMP_OPEN);
  if(abierta) box.insertAdjacentHTML('beforeend', empFicha(abierta));
  box.querySelectorAll('[data-emp]').forEach(b=>b.onclick=()=>{ EMP_OPEN=EMP_OPEN===b.dataset.emp?'':b.dataset.emp; empRender();
    if(EMP_OPEN){ const f=$('emp-ficha'); if(f) f.scrollIntoView({behavior:'smooth',block:'nearest'}); } });
  const c=box.querySelector('[data-emp-cerrar]'); if(c) c.onclick=()=>{ EMP_OPEN=''; empRender(); };
  const ir=box.querySelector('[data-emp-ir]'); if(ir) ir.onclick=()=>irEmpresa(ir.dataset.empIr);
}
/* ══ Modo empresa ═══════════════════════════════════════════════════════
   «Ir a Comfama» convierte la página en el resumen de esa empresa: el título
   pasa a su logo y su nombre, y el bloque de arriba dice «Hoy para Comfama»
   con sus cuatro rumbos. Va en la URL (?empresa=) para que recargar o
   compartir el enlace conserve la vista, y el atrás del navegador vuelve. */
function empresaUrl(){ return (new URLSearchParams(location.search).get('empresa')||'').trim(); }
function irEmpresa(k){
  const u=new URL(location.href);
  if(k) u.searchParams.set('empresa',k); else u.searchParams.delete('empresa');
  history.pushState({mi:1},'',u.pathname+u.search);
  EMP_OPEN=''; modoEmpresa(k);
  window.scrollTo({top:0,behavior:'smooth'});
}
function modoEmpresa(k){
  const p=EMP_LIST.find(x=>x.k===k);
  if(!p) k='';
  EMP_ACTIVA=k;
  const h1=$('mi-h1'); h1.classList.toggle('con-logo',!!p);
  h1.innerHTML=p
    ? `<span class="mi-h1-logo"><img src="${LOGOS}${encodeURIComponent(p.k)}.png" alt="" onerror="this.parentNode.remove()"></span><span><em>${esc(p.nombre)}</em></span>`
    : 'Mi <em>Caudal</em>.';
  $('mi-volver').hidden=!p;
  // el sector de la cuenta no es el de la empresa abierta: se esconde
  const sec=$('mi-sector'); if(sec) sec.hidden=!!p;
  document.title=p?`${p.nombre} · Mi Caudal`:'Mi Caudal · tu contexto';
  empRender();
  if(p) hoyCargar({empresa:p}); else hoyPerfilPorDefecto();
}
addEventListener('popstate',()=>{ if(state&&state.acceso) { EMP_OPEN=''; modoEmpresa(empresaUrl()); } });
async function loadEmpresas(){
  const sec=$('empresas'); if(!sec) return;
  if(!esEquipo()){ sec.hidden=true; EMP_LISTO=true; if(empresaUrl()&&!HOY_CTX) hoyPerfilPorDefecto(); return; }
  const account=state;
  try{
    const m=await call({action:'perfil_meta'}); if(account!==state) return;
    // Cauce es la casa (su brief es para los socios), no una empresa disponible
    EMP_LIST=(m&&m.plantillas||[]).filter(p=>p&&p.cliente&&p.k!=='cauce');
  }catch(e){ EMP_LIST=[]; }
  sec.hidden=!EMP_LIST.length;
  EMP_LISTO=true;
  if(empresaUrl()) modoEmpresa(empresaUrl()); else empRender();
}
/* ══ «Hoy para ti» ═══════════════════════════════════════════════════════
   Lo primero que ve quien tiene un cliente abierto: qué se movió en 72 h.

   ⚠️ SE PINTA EN DOS TIEMPOS, y esa es toda la gracia. El RADAR tarda 1-4 s y
   ya trae `kpis.cardinales` —el conteo por rumbo de lo que se movió— porque lo
   calcula la Lambda sin pasar por el modelo. La LECTURA tarda 20-150 s (la
   varianza es del modelo) y se pasa del techo de 30 s del gateway. Así que se
   pinta el conteo y las señales enseguida, y el titular llega después.

   El disparo puede morir en el gateway: no importa, la Lambda termina igual y
   deja la lectura en caché, que es lo que pesca el sondeo. Si el usuario ya
   abrió la Rosa hoy, el radar no cambió, la llave es la misma y viene de una. */
const HOY_RUMBOS=[['norte','N','Norte','oportunidades'],['este','E','Oriente','conversación'],
                  ['sur','S','Sur','competencia'],['oeste','W','Occidente','Estado']];
const HOY_POLL=3500, HOY_MAX=150000;
/* ⚠️ Contador PROPIO, no el de loadSector: los dos corren en paralelo desde
   workspace() y compartirlo hacía que el sector nunca se pintara —loadHoy
   incrementaba el contador y la respuesta del sector llegaba "obsoleta". */
let hoyPerfil=null, hoyTimer=null, hoyRev=0;
function hoyStop(){ if(hoyTimer){ clearTimeout(hoyTimer); hoyTimer=null; } }
function ultimoPerfil(){
  let em=''; try{ em=(JSON.parse(localStorage.getItem('rr-user')||'null')||{}).email||''; }catch(e){}
  // misma llave que caudal-cliente.js: los dos recuerdan el mismo cliente
  try{ return localStorage.getItem('caudal-perfil-ult:'+(em||'anon'))||''; }catch(e){ return ''; }
}
let HOY_CTX=null, HOY_D=null, HOY_RUMBO='', HOY_ACT=0, HOY_L=null, HOY_VER=false, HOY_PERFIL=null;
function hoyRumbos(){
  const k=(HOY_D&&HOY_D.kpis)||{}, cc=k.cardinales||{}, md=k.mov_dias||3;
  $('hoy-rumbos').innerHTML=HOY_RUMBOS.map(([key,let_,nom,que])=>{
    const c=cc[key]||{}, mov=c.mov||0, tot=c.total||0;
    // el sello dice de un vistazo si ese rumbo trajo noticia o está quieto
    const txt=mov?`${mov} en ${md*24} h`:(tot?`${tot} vigente${tot>1?'s':''}`:'sin señales');
    return `<div class="hoy-r${mov?' mov':''}${HOY_RUMBO===key?' on':''}" role="button" tabindex="0" data-rumbo="${key}" aria-pressed="${HOY_RUMBO===key}" title="${esc(nom)}: ${esc(que)}">`
      + `<div class="hoy-r-l"><span class="hoy-r-let">${let_}</span><span class="hoy-r-nom">${esc(nom)}</span></div>`
      + `<div class="hoy-r-n">${esc(txt)}</div>`
      + (tot?'':`<button type="button" class="hoy-r-act" data-hoy-act>Actualizar</button>`)
      + `</div>`;
  }).join('');
  $('hoy-rumbos').querySelectorAll('[data-rumbo]').forEach(el=>{
    const sel=()=>{ HOY_RUMBO=HOY_RUMBO===el.dataset.rumbo?'':el.dataset.rumbo; HOY_VER=false; hoyRumbos(); hoySenales(); };
    el.onclick=e=>{ if(e.target.closest('[data-hoy-act]')) return; sel(); };
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); sel(); } };
  });
  $('hoy-rumbos').querySelectorAll('[data-hoy-act]').forEach(b=>b.onclick=e=>{
    e.stopPropagation(); HOY_RUMBO=b.closest('[data-rumbo]').dataset.rumbo; hoyActualizar(); });
}
/* ══ Explorar módulos ════════════════════════════════════════════════════
   Al lado de «Abrir la Rosa completa»: los diez pilares de Caudal, para quien
   quiere ir directo a uno (el Congreso, SUCOP, la contratación…). La empresa
   NO es el término de búsqueda (decisión de Ricardo, oct-26): es el contexto.
   Al abrir un módulo se deja su ficha en sessionStorage['caudal-ctx'] y
   caudal-ctx.js marca allá lo que le toca y personaliza la lectura. Si se
   escribe un tema arriba, la tarjeta abre con esa búsqueda hecha. */
const MODULOS=[
  {id:'congreso',    n:'Congreso y órgano legislativo',      s:'Proyectos, leyes y quién los empuja',   q:t=>t?'caudal.html?q='+t+'#congreso':'caudal.html#congreso'},
  {id:'regulatorio', n:'Superintendencias y comisiones',     s:'Actos y sanciones de los reguladores',  q:t=>t?'caudal.html?q='+t+'#regulatorio':'caudal.html#regulatorio'},
  {id:'medios',      n:'Medios nacionales y regionales',     s:'Ritmo y focos de la cobertura',          q:t=>t?'caudal-medios.html?q='+t:'caudal-medios.html'},
  {id:'datos',       n:'Datos abiertos y contratación',      s:'SECOP II en vivo',                       q:t=>t?'caudal-contratacion.html?q='+t:'caudal-contratacion.html'},
  {id:'control',     n:'Órganos de control y altas cortes',  s:'Providencias que cambian la norma',      q:t=>t?'caudal.html?q='+t+'#control':'caudal.html#control'},
  {id:'ejecutivo',   n:'Ejecutivo nacional · Presidencia',   s:'Decretos con su texto oficial',          q:t=>t?'caudal.html?q='+t+'#ejecutivo':'caudal.html#ejecutivo'},
  {id:'sucop',       n:'Consulta pública de normas · SUCOP', s:'Borradores que aún se pueden comentar', q:t=>t?'caudal.html?q='+t+'#sucop':'caudal.html#sucop'},
  {id:'gacetas',     n:'Diarios y gacetas oficiales',        s:'El texto completo del trámite',          q:t=>t?'caudal.html?q='+t+'#gacetas':'caudal.html#gacetas'},
  {id:'territorial', n:'Entidades territoriales',            s:'En construcción · ver el avance',        q:()=>'caudal.html#territorial'},
  {id:'redes',       n:'Redes sociales oficiales y voceros', s:'Cuentas y voceros verificados',          q:t=>t?'caudal-voceros.html?q='+t:'caudal-voceros.html'},
];
function modsPintar(){
  const box=$('hoy-modulos'); if(!box) return;
  const inp=$('hoy-mod-in'), v=(inp&&inp.value||'').trim(), t=encodeURIComponent(v);
  const grid=$('hoy-mod-grid'); if(!grid) return;
  grid.innerHTML=MODULOS.map(m=>`<a class="hoy-mod" data-mod="${m.id}" href="${m.q(t)}" style="background-image:url('imagenes/caudal-${m.id}.jpg')">
    <span class="hoy-mod-n">${esc(m.n)}</span><span class="hoy-mod-s">${v&&m.id!=='territorial'?'Buscar «'+esc(v)+'»':esc(m.s)}</span></a>`).join('');
  grid.querySelectorAll('[data-mod]').forEach(a=>a.addEventListener('click',ctxGuardar));
}
/* La ficha que viaja: temas, nombres que la identifican (las empresas del
   diccionario y su competencia, nunca el nombre suelto de la organización:
   «Cauce» casaría con «el cauce del río») y las entidades que sigue. */
function ctxGuardar(){
  const cl=(HOY_D&&HOY_D.cliente)||{};
  const pre=EMP_LIST.find(x=>x.k===EMP_ACTIVA);
  const fuente=pre||HOY_PERFIL||{};
  const nom=x=>typeof x==='string'?x:(x&&x.nombre)||'';
  const nombres=[...new Set([].concat(cl.empresas||[],cl.competencia||[],fuente.competencia||[]).map(nom).filter(n=>n&&n.length>=4))];
  const ctx={tipo:EMP_ACTIVA?'empresa':'perfil', id:EMP_ACTIVA||(HOY_CTX&&HOY_CTX.perfil)||'',
    nombre:cl.nombre||fuente.nombre||$('hoy-cliente').textContent||'tu cliente',
    temas:(cl.temas&&cl.temas.length?cl.temas:fuente.temas)||[], nombres, entidades:fuente.interlocutores||[]};
  try{ sessionStorage.setItem('caudal-ctx',JSON.stringify(ctx)); }catch(e){}
}
function modsToggle(abrir){
  const box=$('hoy-modulos'), b=$('hoy-mods'); if(!box||!b) return;
  const on=typeof abrir==='boolean'?abrir:box.hidden;
  box.hidden=!on; b.setAttribute('aria-expanded',String(on));
  if(on&&!box.dataset.listo){
    box.dataset.listo='1';
    box.innerHTML=`<div class="hoy-mod-q"><label for="hoy-mod-in">Abrir con un tema</label>
      <input id="hoy-mod-in" type="text" autocomplete="off" placeholder="Opcional: un tema para abrir el módulo ya buscado"></div>
      <div class="hoy-mod-grid" id="hoy-mod-grid"></div>`;
    $('hoy-mod-in').addEventListener('input',modsPintar);
  }
  if(on) modsPintar();
}
/* ══ Competidores del Sur ═════════════════════════════════════════════════
   Un perfil sin competencia deja el Sur vacío para siempre. Dos puertas: a
   mano (diccionario, o un nombre libre que se sigue por prensa) o «Explora
   competidores por mí», que le pide tres a DeepSeek (acción `competidores`
   de la Lambda) y deja al usuario decidir. Solo para un perfil GUARDADO: se
   escribe en su `competencia` con /caudal/perfil/save, que reemplaza la ficha
   entera, así que se manda el perfil completo y solo cambia esa lista. */
let COMP_SUG=[], COMP_MSG='', COMP_DICC=null;
const compSlug=t=>normTxt(t).replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim().slice(0,40);
function compHTML(n){
  const sug=COMP_SUG.map((c,i)=>`<label class="comp-sug"><input type="checkbox" data-comp-i="${i}" ${c.on?'checked':''}>
      <span><b>${esc(c.nombre)}</b> <span class="comp-tag">${c.en_diccionario?'en el diccionario':'se sigue por su nombre'}</span>
      ${c.razon?`<span class="comp-razon">${esc(c.razon)}</span>`:''}</span></label>`).join('');
  return `<div class="comp-box"><div class="hoy-ana-t">${n?'Sumar competidores':'Elige a quién seguir'}</div>
    <div class="comp-acts"><button type="button" class="btn-t" data-comp-ia>Explora competidores por mí</button>
      <span class="comp-man"><input id="comp-in" list="comp-dl" placeholder="o escribe un nombre: Compensar, LLYC…" autocomplete="off"><datalist id="comp-dl"></datalist>
      <button type="button" class="btn-g" data-comp-add>Agregar</button></span></div>
    ${sug?`<div class="comp-list">${sug}</div><button type="button" class="btn-t" data-comp-seguir>Seguir a los seleccionados</button>`:''}
    ${COMP_MSG?`<div class="cob-note" style="margin-top:.6rem">${esc(COMP_MSG)}</div>`:''}</div>`;
}
async function compDicc(){
  if(COMP_DICC) return COMP_DICC;
  try{ const d=await (await fetch('caudal-empresas.json?v=20261026')).json(); COMP_DICC=d.empresas||[]; }catch(e){ COMP_DICC=[]; }
  return COMP_DICC;
}
function compWire(){
  const box=$('hoy-senales');
  box.querySelectorAll('[data-comp-i]').forEach(c=>c.onchange=()=>{ COMP_SUG[+c.dataset.compI].on=c.checked; });
  const ia=box.querySelector('[data-comp-ia]');
  if(ia) ia.onclick=async()=>{
    ia.disabled=true; ia.textContent='Buscando competidores…'; COMP_MSG='';
    const p=HOY_PERFIL||{};
    let d; try{ d=await call({action:'competidores',perfil:{nombre:p.nombre,tipo:p.tipo||'',que_hace:p.que_hace||'',
      descripcion:p.descripcion||'',temas:p.temas||[],empresas:p.empresas||[],competencia:p.competencia||[]}}); }catch(e){ d={error:'No pudimos proponer competidores ahora.'}; }
    if(d&&d.error) COMP_MSG=d.error;
    (d&&d.competidores||[]).forEach(c=>{ if(!COMP_SUG.some(x=>x.k===c.k)) COMP_SUG.push({...c,on:true}); });
    if(d&&!d.error&&!(d.competidores||[]).length) COMP_MSG='El modelo no encontró competidores claros para este perfil. Agrégalos a mano.';
    hoySenales();
  };
  const inp=$('comp-in');
  if(inp){ compDicc().then(l=>{ const dl=$('comp-dl'); if(dl) dl.innerHTML=l.slice(0,2100).map(e=>`<option value="${esc(e.n)}">`).join(''); }); }
  const add=box.querySelector('[data-comp-add]');
  if(add) add.onclick=async()=>{
    const v=(inp&&inp.value||'').trim(); if(v.length<3) return;
    const l=await compDicc(), vn=normTxt(v);
    const e=l.find(x=>normTxt(x.n)===vn||(x.a||[]).some(a=>normTxt(a)===vn));
    const c=e?{k:e.k,nombre:e.n,en_diccionario:true,razon:'',on:true}:{k:compSlug(v),nombre:v,en_diccionario:false,razon:'',on:true};
    if(c.k.length<4){ COMP_MSG='Ese nombre es muy corto para seguirlo con precisión.'; return hoySenales(); }
    if(!COMP_SUG.some(x=>x.k===c.k)) COMP_SUG.push(c);
    COMP_MSG=''; hoySenales();
  };
  const seg=box.querySelector('[data-comp-seguir]');
  if(seg) seg.onclick=async()=>{
    const elegidos=COMP_SUG.filter(c=>c.on); if(!elegidos.length) return;
    seg.disabled=true; seg.textContent='Guardando…';
    try{
      const pid=HOY_CTX&&HOY_CTX.perfil;
      const actual=(await api('/caudal/perfil/load?perfilId='+encodeURIComponent(pid))).perfil||{};
      const prev=(actual.competencia||[]).map(c=>typeof c==='string'?c:(c&&c.k)||'').filter(Boolean);
      const comp=[...new Set(prev.concat(elegidos.map(c=>c.k)))];
      await api('/caudal/perfil/save',Object.assign({},actual,{perfilId:pid,competencia:comp}));
      COMP_SUG=[]; COMP_MSG=`Ahora sigues a ${elegidos.map(c=>c.nombre).join(', ')}. El Sur se está actualizando.`;
      hoyActualizar();
    }catch(e){ COMP_MSG=e.message||'No se pudo guardar.'; seg.disabled=false; seg.textContent='Seguir a los seleccionados'; hoySenales(); }
  };
}
/* «Actualizar» vuelve a correr el radar entero: prensa (Google News), SECOP,
   Congreso y reguladores se consultan en vivo en cada llamada, no hay caché
   que vaciar. La escucha de redes (Apify) NO se dispara desde acá: es un
   módulo de pago aparte y cada corrida cuesta. */
function hoyActualizar(){
  if(!HOY_CTX) return;
  document.querySelectorAll('[data-hoy-act]').forEach(b=>{ b.disabled=true; b.textContent='Actualizando…'; });
  hoyCargar(HOY_CTX,{mantener:true}).then(()=>{ HOY_ACT=Date.now(); hoySenales(); });
}
const HOY_NIV={alto:'alta',medio:'media',bajo:'baja'};
function hoySig(x){
  const url=safeUrl(x.url), t=esc(x.titulo||x.objeto||x.motivo||x.descripcion||x.texto||'Señal');
  const niv=HOY_NIV[x.nivel]?x.nivel:'bajo';
  return `<div class="sig ${niv}"><span class="sig-lvl">${HOY_NIV[niv]}</span><div class="sig-body">`
    + `<div class="sig-title">${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${t}</a>`:t}</div>`
    + `<div class="sig-tags"><span>${esc(x.source)}</span>${x.fecha?`<span>· ${esc(String(x.fecha).slice(0,10))}</span>`:''}</div>`
    + `${x.accion?`<div class="sig-action">${esc(x.accion)}</div>`:''}</div></div>`;
}
// Por qué un rumbo puede venir vacío. Dicho con el dato, no con un «sin datos».
function hoyPorQue(r,k){
  if(r==='norte') return 'Ningún proceso de contratación, consulta pública abierta ni evento del sector cruza hoy con los temas de este perfil.';
  if(r==='este') return 'No hay cobertura de prensa sobre sus temas en las últimas dos semanas.'
    +(k.redes_estado==='sin_escucha'?' La escucha de redes sociales no está activa para este perfil.':'');
  if(r==='sur') return k.n_vigiladas
    ? `Ninguna de las ${k.n_vigiladas} empresas vigiladas tuvo señales en las fuentes de Caudal.`
    : 'Este perfil todavía no sigue a ningún competidor. Agrégalos a mano o deja que Caudal te proponga tres.';
  return 'Ni el Congreso ni los reguladores tienen señales sobre sus temas.';
}
function hoySenales(){
  const d=HOY_D||{}, k=d.kpis||{};
  const grupos=[['Congreso',d.congreso],['Regulatorio',d.regulatorio],['Medios',d.medios],['Contratación',d.contratacion],['Consulta pública',d.sucop],['Evento',d.eventos],['Redes',d.redes]];
  const todas=grupos.flatMap(([src,items])=>(Array.isArray(items)?items:[]).map(x=>({...x,source:src})));
  const ORD={alto:0,medio:1,bajo:2};
  if(HOY_RUMBO){
    const r=HOY_RUMBOS.find(x=>x[0]===HOY_RUMBO)||[HOY_RUMBO,'',HOY_RUMBO,''];
    const lista=todas.filter(x=>x.card===HOY_RUMBO)
      .sort((a,b)=>(b.mov?1:0)-(a.mov?1:0)||(ORD[a.nivel]??3)-(ORD[b.nivel]??3));
    const cab=`<div class="hoy-sel"><span class="hoy-sel-t">${esc(r[2])} · ${esc(r[3])} · ${lista.length} señal${lista.length===1?'':'es'}</span>`
      + `<button type="button" class="btn-g" data-hoy-todo>Ver el resumen</button></div>`;
    const hora=HOY_ACT?`<div class="cob-note" style="margin:.5rem 0 0">Consultado de nuevo a las ${new Date(HOY_ACT).toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})}</div>`:'';
    // 1 · lo que dice el analista sobre este rumbo (la lectura ya trae un
    // párrafo por punto cardinal); 2 · la lista, detrás de «Ver todas».
    const txt=(HOY_L&&(HOY_L[HOY_RUMBO]||'')).trim();
    const ana=txt
      ? `<div class="hoy-ana"><div class="hoy-ana-t">Lo que dice el analista</div><p>${esc(txt)}</p></div>`
      : (lista.length?(HOY_L?'<div class="hoy-ana pend"><p>La lectura no trajo un análisis para este rumbo.</p></div>'
          :'<div class="hoy-ana pend">'+mar(['El analista está leyendo este rumbo…','Cruzando las señales con la ficha…','Mientras tanto, la lista está abajo.'],{mini:true})+'</div>'):'');
    const ver=lista.length
      ? (HOY_VER||!txt
          ? '<div class="sig-list">'+lista.slice(0,10).map(hoySig).join('')+'</div>'
            +(lista.length>10?`<div class="cob-note">Y ${lista.length-10} más en la Rosa completa.</div>`:'')
            +(txt?'<button type="button" class="btn-g hoy-ver" data-hoy-ver>Ocultar la lista</button>':'')
          : `<button type="button" class="btn-g hoy-ver" data-hoy-ver>Ver todas las señales (${lista.length})</button>`)
      : `<div class="hoy-vacio">${esc(hoyPorQue(HOY_RUMBO,k))}<br><button type="button" class="btn-t" data-hoy-act2>Actualizar</button>${hora}</div>`;
    const comp=(HOY_RUMBO==='sur'&&HOY_CTX&&HOY_CTX.perfil)?compHTML(lista.length):'';
    $('hoy-senales').innerHTML = cab + ana + ver + comp;
    const t=$('hoy-senales').querySelector('[data-hoy-todo]'); if(t) t.onclick=()=>{ HOY_RUMBO=''; HOY_VER=false; hoyRumbos(); hoySenales(); };
    const a=$('hoy-senales').querySelector('[data-hoy-act2]'); if(a) a.onclick=()=>{ a.disabled=true; a.textContent='Actualizando…'; hoyActualizar(); };
    const v=$('hoy-senales').querySelector('[data-hoy-ver]'); if(v) v.onclick=()=>{ HOY_VER=!HOY_VER; hoySenales(); };
    if(comp) compWire();
    return;
  }
  // Lo que se movió y pesa. Si nada se movió, se dice — y se muestra lo más
  // alto que siga vigente, en vez de dejar el bloque en blanco.
  const movidas=todas.filter(x=>x.mov&&x.nivel==='alto');
  const lista=(movidas.length?movidas:todas.filter(x=>x.nivel==='alto')).slice(0,3);
  const nota=movidas.length?'' :
    '<div class="cob-note" style="margin:0 0 .5rem">Nada de alta prioridad se movió en las últimas 72 horas. Esto es lo que sigue vigente.</div>';
  $('hoy-senales').innerHTML = lista.length
    ? nota+'<div class="sig-list">'+lista.map(hoySig).join('')+'</div>'
    : '<div class="cob-note" style="margin:0">Sin señales de alta prioridad en este radar. Toca un rumbo para ver todo lo que trae.</div>';
}
function hoyTitular(l){
  // El titular de la lectura. Si el modelo no lo trajo, se usa el Norte, que
  // es la lectura del contexto — nunca se inventa una frase.
  HOY_L=l||null;
  if(HOY_RUMBO) hoySenales();   // el párrafo del rumbo abierto llega con la lectura
  const t=(l&&(l.titular||l.norte||l.lo_que_importa)||'').trim();
  $('hoy-lectura').innerHTML=t?`<div class="hoy-titular">${esc(t)}</div>`:'';
  $('hoy-estado').textContent='';
}
function loadHoy(perfilId){ return hoyCargar({perfil:perfilId}); }
async function hoyCargar(ctx, opt={}){
  const mine=++hoyRev; hoyStop();
  HOY_CTX=ctx; HOY_L=null; if(!opt.mantener){ HOY_RUMBO=''; HOY_ACT=0; HOY_VER=false; }
  $('hoy').hidden=false;
  $('hoy-estado').textContent='';
  if(!opt.mantener){ $('hoy-lectura').replaceChildren(); $('hoy-rumbos').replaceChildren();
    $('hoy-senales').innerHTML=mar(['Leyendo el Congreso y los reguladores…','Escuchando la prensa y las redes…','Buscando consultas abiertas y eventos…']); }
  let req;
  if(ctx.empresa){
    const p=ctx.empresa;
    $('hoy-cliente').textContent=p.nombre;
    $('hoy-rosa').href='caudal.html?sector='+encodeURIComponent(p.k)+'#cliente';
    // el preset ya trae la ficha completa en el motor: basta la llave
    req={action:'cliente',lectura:true,sector:p.k};
  }else{
    const perfilId=ctx.perfil;
    try{ localStorage.setItem('caudal-perfil-ult:'+((JSON.parse(localStorage.getItem('rr-user')||'null')||{}).email||'anon'), perfilId); }catch(e){}
    $('hoy-rosa').href='caudal.html?perfil='+encodeURIComponent(perfilId)+'#cliente';
    let perfil;
    try{ perfil=(await api('/caudal/perfil/load?perfilId='+encodeURIComponent(perfilId))).perfil; }
    catch(e){ if(mine===hoyRev) $('hoy-estado').textContent=e.message; return; }
    if(mine!==hoyRev) return;
    HOY_PERFIL=Object.assign({perfilId},perfil);
    $('hoy-cliente').textContent=perfil.nombre||'tu cliente';
    // La ficha completa: sin ella la lectura se escribe sin saber quién es el
    // cliente (defecto medido en sep-2026).
    req={action:'cliente',lectura:true,perfil:{
      nombre:perfil.nombre,descripcion:perfil.descripcion||'',temas:perfil.temas||[],
      empresas:perfil.empresas||[],sector_sanciones:perfil.sector_sanciones||'',
      comision:perfil.comision||'',tipo:perfil.tipo||'',lineas:perfil.lineas||[],
      competencia:perfil.competencia||[],que_hace:perfil.que_hace||'',lector:perfil.lector||'',
      decisiones:perfil.decisiones||[],jurisdicciones:perfil.jurisdicciones||[],
      interlocutores:perfil.interlocutores||[],relojes:perfil.relojes||[],no_interesa:perfil.no_interesa||[]}};
  }
  let d;
  try{ d=await call(req); }catch(e){ if(mine===hoyRev) $('hoy-estado').textContent='No se pudo armar el radar de este cliente.'; return; }
  if(mine!==hoyRev) return;
  if(d&&d.error){ $('hoy-estado').textContent=d.error; return; }
  // 1 · lo que no depende del modelo, ya
  HOY_D=d; hoyRumbos(); hoySenales();
  // 2 · el titular
  if(d.lectura&&!d.lectura.error) return hoyTitular(d.lectura);
  if(!d.lectura_key){ $('hoy-estado').textContent='Abre la Rosa completa para la lectura del analista.'; return; }
  $('hoy-estado').innerHTML=mar(['Escribiendo la lectura del analista…','Leyendo cada rumbo de la Rosa…','Ordenando lo que mueve la aguja…'],{mini:true});
  hoySondear(d.lectura_key, mine);
}
function hoySondear(key, mine){
  const t0=Date.now(); let disparos=0;
  const listo=x=>{ if(mine!==hoyRev||!x||x.estado!=='lista'||!x.lectura||x.lectura.error) return false;
                   hoyStop(); hoyTitular(x.lectura); return true; };
  const disparar=()=>{ disparos++; call({action:'cliente-lectura',key}).then(x=>{ if(mine===hoyRev) listo(x); }).catch(()=>{}); };
  const tick=()=>{
    if(mine!==hoyRev) return hoyStop();
    if(Date.now()-t0>HOY_MAX){ hoyStop(); $('hoy-estado').textContent='La lectura tardó más de lo normal. Está en la Rosa completa.'; return; }
    call({action:'cliente-lectura',key,solo_cache:true}).then(x=>{
      if(listo(x)) return;
      // el servidor avisa con `reintentar` cuando la generación se cayó y no
      // hay ninguna en vuelo; sin esto el sondeo giraría en vano
      if(x&&x.reintentar&&disparos<3) disparar();
      hoyTimer=setTimeout(tick,HOY_POLL);
    }).catch(()=>{ if(mine===hoyRev) hoyTimer=setTimeout(tick,HOY_POLL); });
  };
  disparar(); hoyTimer=setTimeout(tick,HOY_POLL);
}
async function loadSector(){
  const mine=++revision,c=state.cuenta;
  $('sector-title').textContent='Tu sector: '+(state.sectores[c.sector]||c.sector);
  $('sector-status').textContent='Consultando las señales de tu sector…';$('refresh').disabled=true;
  $('metrics').replaceChildren();$('signals').replaceChildren();$('topics').replaceChildren();
  try{
    // No mandar organización, rol ni ficha a esta consulta, incluso en pago.
    const d=await call({action:'cliente',sector:c.sector,lectura:false});
    if(mine!==revision)return;
    // `call()` no lanza en error: el worker responde el motivo en el cuerpo
    // (p. ej. «Regístrate para consultar el contexto de tu sector»).
    if(d&&d.error) throw new Error(d.error);
    if(!d.kpis||!d.cliente)throw new Error('El contexto no llegó completo. Vuelve a intentarlo.');
    const k=d.kpis;
    const metrics=[[k.n_radar,'señales en el radar'],[k.alto,'de alta prioridad'],[k.en_tramite,'proyectos en trámite']];
    $('metrics').innerHTML=metrics.map(([n,t])=>`<div class="kpi"><div class="n">${Number.isFinite(n)?fmt(n):'—'}</div><div class="l">${esc(t)}</div></div>`).join('');
    const warnings=d.cliente.avisos||[];
    $('sector-status').textContent='Consultado a las '+new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})+' · Se muestran señales del radar; no todas son novedades de hoy.'+(warnings.length?' '+warnings.filter(x=>typeof x==='string').join(' '):'');
    const groups=[['Congreso',d.congreso],['Regulatorio',d.regulatorio],['Medios',d.medios],['Contratación',d.contratacion]];
    const signals=groups.flatMap(([source,items])=>(Array.isArray(items)?items:[]).map(x=>({...x,source})));
    signals.sort((a,b)=>({alto:0,medio:1,bajo:2}[a.nivel]??3)-({alto:0,medio:1,bajo:2}[b.nivel]??3));
    // Mismo componente que usa la Rosa de los Vientos: nivel a la izquierda,
    // título, procedencia y la acción sugerida debajo.
    const NIV={alto:'alta',medio:'media',bajo:'baja'};
    $('signals').innerHTML=signals.slice(0,6).map(x=>{
      const url=safeUrl(x.url), title=esc(x.titulo||x.objeto||x.motivo||x.descripcion||'Señal del sector');
      const niv=NIV[x.nivel]?x.nivel:'bajo';
      return `<div class="sig ${niv}"><span class="sig-lvl">${esc(NIV[niv])}</span><div class="sig-body">`
        + `<div class="sig-title">${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`:title}</div>`
        + `<div class="sig-tags"><span>${esc(x.source)}</span>${x.fecha?`<span>· ${esc(String(x.fecha).slice(0,10))}</span>`:''}</div>`
        + `${x.accion?`<div class="sig-action">${esc(x.accion)}</div>`:''}</div></div>`;
    }).join('')||'<div class="cli-empty">No hay señales disponibles en esta consulta. Esto no implica que no existan movimientos en el sector.</div>';
    $('topics').innerHTML=(d.cliente.temas||[]).slice(0,4).map(t=>`<a class="chip" href="caudal.html?tema=${encodeURIComponent(t)}">${esc(t)}</a>`).join('');
  }catch(e){if(mine===revision)$('sector-status').textContent=e.message;}
  finally{if(mine===revision)$('refresh').disabled=false;}
}
async function init(){
  $('retry').hidden=true;$('welcome').hidden=true;$('setup').hidden=true;$('workspace').hidden=true;
  if(!localStorage.getItem('rr-token')){$('status').textContent='';$('welcome').hidden=false;return;}
  $('status').textContent='Cargando tu contexto…';
  try{state=await api('/caudal/cuenta');if(!state.ok||!state.sectores)throw new Error('No pudimos cargar tu contexto.');state.cuenta?workspace():form();}
  catch(e){$('status').textContent=e.status===401?'Inicia sesión para recuperar tu espacio.':e.message;$('welcome').hidden=e.status!==401;$('retry').hidden=e.status===401;}
}
$('tipo').addEventListener('change',organization);
$('edit').onclick=()=>form(true);$('hoy-mods').onclick=()=>modsToggle();$('edit2').onclick=()=>form(true);$('mi-volver').onclick=()=>irEmpresa('');$('cancel').onclick=workspace;$('refresh').onclick=loadSector;$('retry').onclick=init;
$('context-form').addEventListener('submit',async e=>{
  e.preventDefault();$('save').disabled=true;$('form-error').textContent='';
  try{state=await api('/caudal/cuenta',{tipo:$('tipo').value,organizacion:$('organizacion').value,sector:$('sector').value,rol:$('rol').value});workspace();$('context-title').tabIndex=-1;$('context-title').focus();}
  catch(e){$('form-error').textContent=e.message;}
  finally{$('save').disabled=false;}
});
/* Lo arranca `initHome` desde caudal-mi.html, cuando el shell ya reveló la
   página. Llamarlo acá pintaría sobre un #app todavía oculto. */
window.miInit=init;
})();
