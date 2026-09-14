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
  $('company').hidden=!paid;$('upgrade').hidden=paid;
  loadSector();if(paid) loadProfiles();
}
async function loadProfiles(){
  const account=state;$('profiles').textContent='Cargando tus perfiles…';
  try{
    const d=await api('/caudal/perfil/list');if(account!==state)return;
    const lista=d.perfiles||[];
    $('profiles').innerHTML=lista.map(p=>`<a class="chip" href="caudal.html?perfil=${encodeURIComponent(p.perfilId)}#cliente">${esc(p.nombre)} →</a>`).join('')||'<span class="cob-note" style="margin:0">Aún no has creado un perfil de organización. Puedes hacerlo en el radar.</span>';
    // «Hoy para ti»: el último cliente trabajado, o el único que tenga. Con
    // varios y ninguno marcado NO se elige por el usuario — abrir el radar del
    // cliente equivocado es peor que pedirle que escoja (mismo criterio que
    // pfAutoAbrir en caudal-cliente.js).
    if(lista.length){
      const ult=ultimoPerfil();
      const cual=lista.some(p=>p.perfilId===ult)?ult:(lista.length===1?lista[0].perfilId:'');
      hoyChips(lista, cual);
      if(cual) loadHoy(cual);
      else { $('hoy').hidden=false; $('hoy-cliente').textContent='tu cliente';
             $('hoy-estado').textContent='Escoge abajo el cliente con el que vas a trabajar hoy. Caudal recuerda el último y la próxima vez abre directo en él.'; }
    }
  }catch(e){if(account===state)$('profiles').textContent=e.message;}
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
function hoyChips(lista, activo){
  const box=$('hoy-clientes'); if(!box) return;
  // con un solo cliente no hay nada que escoger
  box.innerHTML=lista.length>1
    ? '<span class="pf-lbl" style="margin-right:.2rem">Cambiar de cliente</span>'
      + lista.map(p=>`<button type="button" class="chip${p.perfilId===activo?' on':''}" data-hoy="${esc(p.perfilId)}">${esc(p.nombre)}</button>`).join('')
    : '';
  box.querySelectorAll('[data-hoy]').forEach(b=>{ b.onclick=()=>loadHoy(b.dataset.hoy); });
}
function hoyRumbos(k){
  const cc=(k&&k.cardinales)||{}, md=(k&&k.mov_dias)||3;
  $('hoy-rumbos').innerHTML=HOY_RUMBOS.map(([key,let_,nom,que])=>{
    const c=cc[key]||{}, mov=c.mov||0, tot=c.total||0;
    // el sello dice de un vistazo si ese rumbo trajo noticia o está quieto
    const txt=mov?`${mov} en ${md*24} h`:(tot?`${tot} vigente${tot>1?'s':''}`:'sin señales');
    return `<div class="hoy-r${mov?' mov':''}" title="${esc(nom)}: ${esc(que)}">`
      + `<div class="hoy-r-l"><span class="hoy-r-let">${let_}</span><span class="hoy-r-nom">${esc(nom)}</span></div>`
      + `<div class="hoy-r-n">${esc(txt)}</div></div>`;
  }).join('');
}
function hoySenales(d){
  const grupos=[['Congreso',d.congreso],['Regulatorio',d.regulatorio],['Medios',d.medios],['Contratación',d.contratacion]];
  const todas=grupos.flatMap(([src,items])=>(Array.isArray(items)?items:[]).map(x=>({...x,source:src})));
  // Lo que se movió y pesa. Si nada se movió, se dice — y se muestra lo más
  // alto que siga vigente, en vez de dejar el bloque en blanco.
  const movidas=todas.filter(x=>x.mov&&x.nivel==='alto');
  const lista=(movidas.length?movidas:todas.filter(x=>x.nivel==='alto')).slice(0,3);
  const nota=movidas.length?'' :
    '<div class="cob-note" style="margin:0 0 .5rem">Nada de alta prioridad se movió en las últimas 72 horas. Esto es lo que sigue vigente.</div>';
  $('hoy-senales').innerHTML = lista.length
    ? nota+'<div class="sig-list">'+lista.map(x=>{
        const url=safeUrl(x.url), t=esc(x.titulo||x.objeto||x.motivo||x.descripcion||'Señal');
        return `<div class="sig alto"><span class="sig-lvl">alta</span><div class="sig-body">`
          + `<div class="sig-title">${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${t}</a>`:t}</div>`
          + `<div class="sig-tags"><span>${esc(x.source)}</span>${x.fecha?`<span>· ${esc(String(x.fecha).slice(0,10))}</span>`:''}</div>`
          + `${x.accion?`<div class="sig-action">${esc(x.accion)}</div>`:''}</div></div>`;
      }).join('')+'</div>'
    : '<div class="cob-note" style="margin:0">Sin señales de alta prioridad en este radar.</div>';
}
function hoyTitular(l){
  // El titular de la lectura. Si el modelo no lo trajo, se usa el Norte, que
  // es la lectura del contexto — nunca se inventa una frase.
  const t=(l&&(l.titular||l.norte||l.lo_que_importa)||'').trim();
  $('hoy-lectura').innerHTML=t?`<div class="hoy-titular">${esc(t)}</div>`:'';
  $('hoy-estado').textContent='';
}
async function loadHoy(perfilId){
  const mine=++hoyRev; hoyStop();
  hoyPerfil=perfilId;
  try{ localStorage.setItem('caudal-perfil-ult:'+((JSON.parse(localStorage.getItem('rr-user')||'null')||{}).email||'anon'), perfilId); }catch(e){}
  $('hoy').hidden=false;
  // el chip activo se mueve con el cliente: sin esto, cambiar de cliente dejaba
  // resaltado al anterior y la pantalla decía dos cosas distintas a la vez
  document.querySelectorAll('#hoy-clientes [data-hoy]').forEach(b=>b.classList.toggle('on', b.dataset.hoy===perfilId));
  $('hoy-rosa').href='caudal.html?perfil='+encodeURIComponent(perfilId)+'#cliente';
  $('hoy-estado').textContent='Cruzando el Estado, la competencia y la conversación…';
  $('hoy-lectura').replaceChildren(); $('hoy-rumbos').replaceChildren(); $('hoy-senales').replaceChildren();
  let perfil;
  try{ perfil=(await api('/caudal/perfil/load?perfilId='+encodeURIComponent(perfilId))).perfil; }
  catch(e){ if(mine===hoyRev) $('hoy-estado').textContent=e.message; return; }
  if(mine!==hoyRev) return;
  $('hoy-cliente').textContent=perfil.nombre||'tu cliente';
  // La ficha completa: sin ella la lectura se escribe sin saber quién es el
  // cliente (defecto medido en sep-2026).
  const req={action:'cliente',lectura:true,perfil:{
    nombre:perfil.nombre,descripcion:perfil.descripcion||'',temas:perfil.temas||[],
    empresas:perfil.empresas||[],sector_sanciones:perfil.sector_sanciones||'',
    comision:perfil.comision||'',tipo:perfil.tipo||'',lineas:perfil.lineas||[],
    competencia:perfil.competencia||[],que_hace:perfil.que_hace||'',lector:perfil.lector||'',
    decisiones:perfil.decisiones||[],jurisdicciones:perfil.jurisdicciones||[],
    interlocutores:perfil.interlocutores||[],relojes:perfil.relojes||[],no_interesa:perfil.no_interesa||[]}};
  let d;
  try{ d=await call(req); }catch(e){ if(mine===hoyRev) $('hoy-estado').textContent='No se pudo armar el radar de este cliente.'; return; }
  if(mine!==hoyRev) return;
  if(d&&d.error){ $('hoy-estado').textContent=d.error; return; }
  // 1 · lo que no depende del modelo, ya
  hoyRumbos(d.kpis||{}); hoySenales(d);
  // 2 · el titular
  if(d.lectura&&!d.lectura.error) return hoyTitular(d.lectura);
  if(!d.lectura_key){ $('hoy-estado').textContent='Abre la Rosa completa para la lectura del analista.'; return; }
  $('hoy-estado').textContent='Escribiendo la lectura del analista…';
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
    $('topics').innerHTML=(d.cliente.temas||[]).slice(0,4).map(t=>`<a class="chip" href="caudal.html?tema=${encodeURIComponent(t)}">${esc(t)} →</a>`).join('');
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
$('edit').onclick=()=>form(true);$('cancel').onclick=workspace;$('refresh').onclick=loadSector;$('retry').onclick=init;
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
