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
  revision++;$('refresh').disabled=false;
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
    $('profiles').innerHTML=(d.perfiles||[]).map(p=>`<a class="chip" href="caudal.html?perfil=${encodeURIComponent(p.perfilId)}#cliente">${esc(p.nombre)} →</a>`).join('')||'<span class="cob-note" style="margin:0">Aún no has creado un perfil de organización. Puedes hacerlo en el radar.</span>';
  }catch(e){if(account===state)$('profiles').textContent=e.message;}
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
