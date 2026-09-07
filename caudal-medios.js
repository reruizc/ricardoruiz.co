/* caudal-medios.js — pilar MEDIOS de Caudal, como página propia.
   ------------------------------------------------------------------
   Por qué existe aparte de `caudal.html`: la vista vieja (`view-medios`)
   era un listado de titulares, y eso lo da mejor una búsqueda de Google.
   Lo que aquí se agrega es lo que Google NO puede dar: la cobertura de
   prensa CONTRA el trámite real del Estado en los otros pilares, y las
   propiedades de esa cobertura (temperatura, concentración, quién es
   nombrado, dónde se cubre y dónde no).

   Todo corre contra acciones que YA existen en la Lambda — este archivo
   no pide backend nuevo. Cuando exista una acción de análisis dedicada,
   `temperatura()` es lo primero que debería mudarse a ella.

   ⚠️ Al tocar este archivo hay que bumpear su ?v= en caudal-medios.html,
   o el navegador sirve la copia vieja sin dar ningún error. */
(function(){
'use strict';

const API='https://rr-auth.reruizc.workers.dev/caudal/api';
const S3='https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
const GEO_DEP=S3+'/mapas-2026/DEPARTAMENTOS2.json';

/* El token de invitado viaja en el CUERPO, no en una cabecera: una cabecera
   propia dispararía preflight y el worker solo admite Content-Type y
   Authorization. Mismo contrato que caudal-base.js. */
const GUEST=(new URLSearchParams(location.search).get('acceso')||'').trim();
async function call(payload){
  const h={'Content-Type':'application/json'};
  const t=localStorage.getItem('rr-token'); if(t) h.Authorization='Bearer '+t;
  const body=GUEST?Object.assign({},payload,{_guest:GUEST}):payload;
  const r=await fetch(API,{method:'POST',headers:h,body:JSON.stringify(body)});
  if(r.status===429) throw new Error('429');
  return r.json();
}
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(n==null||isNaN(n))?'—':Number(n).toLocaleString('es-CO');
const $=id=>document.getElementById(id);
const V=x=>x&&x.status==='fulfilled'&&x.value&&!x.value.error?x.value:null;

/* ══ 1 · TEMPERATURA ══════════════════════════════════════════════════
   ⚠️⚠️ El RSS de Google News devuelve COMO MÁXIMO 100 ítems por consulta.
   Medido (sep-2026): «reforma pensional» da 100 tanto en `when:30d` como
   en `when:90d` — un cociente 30/90 sería exactamente 1,0 y no diría nada.
   Por eso: (a) las ventanas grandes que llegan al tope se declaran «≥» y
   NO entran a ningún cálculo de ritmo, y (b) la serie no se arma con las
   fechas de los titulares que devuelve una sola consulta (esa lista viene
   recortada), sino RESTANDO ventanas anidadas, que sí es exacto mientras
   ninguna sature. */
const VENTANAS=[1,3,7,14,30];
const TOPE=88;   // `n` es post-dedup; el tope crudo de 100 aterriza cerca de acá

async function temperatura(q){
  const rs=await Promise.allSettled(VENTANAS.map(d=>call({action:'medios',query:q,dias:d})));
  const acum=rs.map(r=>{ const d=V(r); return d?{n:d.n||0, ok:true, sat:(d.n||0)>=TOPE, med:d.por_medio||[], res:d.resultados||[]}:{n:0,ok:false,sat:false,med:[],res:[]}; });
  if(!acum.some(a=>a.ok)) return null;
  // tramos: [desde, hasta) en días, con su volumen y su ritmo diario
  const tramos=[];
  for(let i=0;i<VENTANAS.length;i++){
    const hasta=VENTANAS[i], desde=i?VENTANAS[i-1]:0, dias=hasta-desde;
    const a=acum[i], prev=i?acum[i-1]:{n:0,ok:true,sat:false};
    // La resta puede dar negativo si Google no es perfectamente monótono entre
    // ventanas; se recorta a 0 en vez de pintar una barra imposible.
    const vol=Math.max(0,(a.n||0)-(prev.n||0));
    tramos.push({desde,hasta,dias,vol,ritmo:vol/dias,
                 fiable:a.ok&&prev.ok&&!a.sat&&!prev.sat});
  }
  const rec=tramos[0].fiable&&tramos[1].fiable
    ? (tramos[0].vol+tramos[1].vol)/3 : null;          // titulares/día, últimos 3 días
  /* La base es el ritmo «normal» contra el que se compara. La ideal es el tramo
     14-30 d, pero en un tema caliente esa ventana SIEMPRE toca el tope de la
     fuente y quedarse ahí dejaba sin veredicto justo a los temas que la gente
     busca. Se retrocede al tramo fiable más largo disponible y se DICE cuál se
     usó: una base de 4 días es una comparación más corta, no una inválida. */
  const cand=[[4,'las semanas 2 a 4'],[3,'los días 7 a 14'],[2,'los días 3 a 7']];
  let base=null, baseLab=null;
  for(const [i,lab] of cand){ if(tramos[i].fiable&&tramos[i].ritmo>0){ base=tramos[i].ritmo; baseLab=lab; break; } }
  const acel=(rec!=null&&base!=null&&base>0)?rec/base:null;
  const total30=acum[4].ok?acum[4].n:null;
  return {tramos, rec, base, baseLab, acel, total30, sat30:acum[4].sat,
          por_medio:(acum[4].med.length?acum[4]:acum[2]).med,
          resultados:(acum[4].res.length?acum[4]:acum[2]).res,
          n_medios:new Set(((acum[4].med.length?acum[4]:acum[2]).med||[]).map(m=>m.medio)).size};
}

function pintarTemperatura(t,q){
  const el=$('mx-temp'); if(!el) return;
  if(!t){ el.innerHTML='<div class="err">No se pudo medir el ritmo de cobertura. Reintenta.</div>'; return; }
  const max=Math.max(...t.tramos.map(x=>x.ritmo),0.001);
  const lab=x=>x.desde===0?'Últimas 24 h':`Días ${x.desde}–${x.hasta}`;
  /* ⚠️ Un tramo truncado con volumen 0 NO es «cero titulares»: es «la fuente ya
     había llenado su cupo antes de llegar hasta acá y no sabemos cuántos hubo».
     Pintarlo como 0.0 hacía leer «hace tres semanas nadie hablaba de esto»,
     que es lo contrario de la verdad en un tema caliente. Sin dato se dice sin
     dato: barra rayada completa y guion. */
  const cifra=x=>x.ritmo>=10?String(Math.round(x.ritmo)):x.ritmo.toFixed(1);
  const barras=t.tramos.map(x=>{
    const sinDato=!x.fiable&&x.ritmo<=0;
    const w=sinDato?100:Math.max(2,100*x.ritmo/max);
    return `<div class="mx-bar-row">
      <div class="mx-bar-lab">${lab(x)}</div>
      <div class="mx-bar-track"><div class="mx-bar-fill${x.fiable?'':' mx-bar-trunc'}" style="width:${w.toFixed(1)}%"></div></div>
      <div class="mx-bar-n">${sinDato?'<span class="mx-nd">sin dato</span>':(x.fiable?'':'≥&nbsp;')+cifra(x)}</div>
    </div>`;}).join('');
  let veredicto, tono;
  const ref=t.baseLab?` frente a ${t.baseLab}`:'';
  if(t.acel==null){ veredicto='No se puede comparar el ritmo: todas las ventanas de comparación llegaron al tope de 100 que devuelve la fuente, y un conteo truncado no se puede dividir.'; tono='mx-neutro'; }
  else if(t.acel>=2){ veredicto=`Se está calentando: ${t.acel.toFixed(1)}× el ritmo${ref}.`; tono='mx-sube'; }
  else if(t.acel>=1.25){ veredicto=`Sube moderadamente: ${t.acel.toFixed(1)}× el ritmo${ref}.`; tono='mx-sube'; }
  else if(t.acel>=0.75){ veredicto=`Estable: cubre a un ritmo parecido al${ref?' de'+ref:' de las últimas semanas'}.`; tono='mx-neutro'; }
  else { veredicto=`Se está enfriando: ${t.acel.toFixed(2)}× el ritmo${ref}. El pico ya pasó y la prensa está soltando el tema.`; tono='mx-baja'; }
  el.innerHTML=`
    <div class="panel">
      <h3>Temperatura de la cobertura</h3>
      <div class="mx-kpis">
        <div class="kpi"><div class="n">${t.rec==null?'—':(t.rec>=10?Math.round(t.rec):t.rec.toFixed(1))}</div><div class="l">Titulares/día · últimos 3 días</div></div>
        <div class="kpi"><div class="n">${t.base==null?'—':(t.base>=10?Math.round(t.base):t.base.toFixed(1))}</div><div class="l">Titulares/día · ${esc(t.baseLab||'semanas 2 a 4')}</div></div>
        <div class="kpi"><div class="n">${t.total30==null?'—':(t.sat30?'≥':'')+fmt(t.total30)}</div><div class="l">Titulares en 30 días</div></div>
      </div>
      <div class="mx-bars">${barras}</div>
      <div class="mx-verdict ${tono}">${esc(veredicto)}</div>
      <div class="cob-note">Cada barra es el promedio de titulares por día en ese tramo, calculado
        restando ventanas anidadas de la fuente — no contando fechas de una sola consulta, que
        vuelve recortada. Un tramo marcado «≥» tocó el tope de 100 ítems que devuelve Google News
        y su ritmo es un piso, no una medición.</div>
    </div>`;
}

/* ══ 2 · CRUCE CON EL ESTADO ══════════════════════════════════════════
   El foso: la misma pregunta contra los cinco pilares. Lo que importa no
   es cada cifra sino el DESFASE entre lo que la prensa cuenta y lo que el
   Estado está tramitando. Se consultan las acciones que ya existen, en
   paralelo y con `lectura:false` (la lectura del analista es cara y acá
   no se necesita). Un rechazo de red NO es un cero: se declara aparte. */
const PILARES=[
  ['congreso','Congreso','Proyectos que tocan el tema'],
  ['regulatorio','Regulatorio','Actos de superintendencias y ANLA'],
  ['ejecutivo','Ejecutivo','Decretos y resoluciones'],
  ['sucop','Consulta pública','Borradores de norma abiertos'],
  ['contratacion','Contratación','Contratos en SECOP II'],
];

async function cruce(q){
  const [cong,reg,eje,suc,con]=await Promise.allSettled([
    call({action:'tema',query:q,lectura:false}),
    call({action:'sanciones',query:q}),
    call({action:'ejecutivo',query:q}),
    call({action:'sucop',query:q}),
    call({action:'contratacion',query:q,limit:1}),
  ]);
  const cD=V(cong),rD=V(reg),eD=V(eje),sD=V(suc),oD=V(con);
  const cR=cD&&cD.resumen;
  return {
    congreso: cD?((cR&&cR.intentos||[]).filter(i=>!i.match_texto).length):null,
    regulatorio: rD?(rD.n||0):null,
    ejecutivo: eD?(eD.n||0):null,
    sucop: sD?(sD.n||0):null,
    contratacion: oD?((oD.total&&oD.total.contratos)||oD.n||0):null,
    empresas:(cR&&cR.empresas)||(rD&&rD.empresas)||null,
    vivos: cD?((cR&&cR.intentos||[]).filter(i=>!i.match_texto&&i.resultado==='EN_TRAMITE').length):null,
  };
}

/* La lectura del desfase es DETERMINISTA — umbrales, no modelo. En una
   página que se vende como inteligencia, una frase generada tiene que
   poder auditarse; esta se puede leer del propio dato de al lado. */
function lecturaDesfase(prensa,c){
  if(prensa==null) return null;
  const cong=c.congreso, reg=c.regulatorio, vivos=c.vivos;
  const nada=[cong,reg,c.ejecutivo].every(x=>x===0||x==null);
  if(nada) return {t:'mx-neutro',s:'Sin rastro en el Estado',
    d:'La prensa lo está contando, pero en las fuentes de Caudal no aparece ni un proyecto, ni un acto regulatorio, ni normativa del Ejecutivo. O el asunto todavía no llegó al Estado, o se está tramitando con otro vocabulario del que usa la prensa.'};
  if(prensa>=25&&(vivos!=null&&vivos===0)) return {t:'mx-sube',s:'Ruido sin trámite vivo',
    d:`Hay ${fmt(prensa)} titulares en 30 días y ningún proyecto en trámite ahora mismo. El debate público va por delante del Congreso: lo que se decide hoy sobre este tema no se está decidiendo por ley.`};
  if(prensa<=8&&(reg||0)>=40) return {t:'mx-baja',s:'Se está regulando en silencio',
    d:`Apenas ${fmt(prensa)} titulares en 30 días frente a ${fmt(reg)} actos regulatorios. La regulación avanza sin cobertura de prensa — es el escenario en que una empresa se entera tarde.`};
  if(prensa<=8&&(vivos||0)>=3) return {t:'mx-baja',s:'Trámite sin cobertura',
    d:`${fmt(vivos)} proyectos vivos en el Congreso y solo ${fmt(prensa)} titulares en 30 días. Se está legislando sin que nadie lo cuente.`};
  if(prensa>=25&&(vivos||0)>=3) return {t:'mx-sube',s:'Caliente en los dos frentes',
    d:`${fmt(prensa)} titulares y ${fmt(vivos)} proyectos vivos. Prensa y Congreso están sobre el mismo tema al mismo tiempo: es cuando el trámite se mueve más rápido y menos avisado.`};
  return {t:'mx-neutro',s:'Cobertura y trámite en proporción',
    d:'La atención de la prensa y la actividad del Estado van a escalas parecidas. No hay un desfase que destacar.'};
}

/* ⚠️ Cuando la consulta nombra una empresa del diccionario de Caudal, el
   Congreso y el Ejecutivo NO se buscan por la marca sino por su vocabulario
   legislativo: nadie legisla «Ecopetrol», se legisla sobre hidrocarburos. Sin
   decirlo, «285 proyectos» se lee como 285 proyectos sobre esa empresa, que es
   falso. Mismo aviso que la búsqueda general de caudal.html. */
function empresaNota(emps){
  if(!emps||!emps.length) return '';
  const e=emps[0];
  const t=(e.nucleo||[]).concat(e.contexto&&e.contexto.length?[]:[]).slice(0,6);
  return `<div class="cob-note mx-emp"><b>${esc(e.nombre)}</b> es una empresa del diccionario de Caudal.
    En Regulatorio y Contratación se busca por su identidad (razón social); en Congreso y Ejecutivo,
    por el vocabulario de su actividad${t.length?': '+t.map(esc).join(' · '):''}. Esas cifras son de
    la actividad, no de la empresa.</div>`;
}

function pintarCruce(c,prensa,q){
  const el=$('mx-cruce'); if(!el) return;
  const fallidos=PILARES.filter(([k])=>c[k]===null).length;
  const L=lecturaDesfase(prensa,c);
  el.innerHTML=`
    <div class="panel">
      <h3>Lo que cuenta la prensa contra lo que hace el Estado</h3>
      <div class="mx-cross">
        <div class="mx-cross-card mx-cross-press"><span class="mx-cc-n">${prensa==null?'—':fmt(prensa)}</span><span class="mx-cc-l">Titulares de prensa</span><span class="mx-cc-s">últimos 30 días</span></div>
        ${PILARES.map(([k,n,s])=>{
          // El Congreso se cuenta dos veces a propósito: el histórico dice si el
          // tema tiene recorrido, y los vivos dicen si HOY hay algo que mover. El
          // veredicto habla de los vivos, así que la tarjeta tiene que mostrarlos
          // o las dos cifras se leen como una contradicción.
          const sub=c[k]==null?'fuente no disponible'
            :(k==='congreso'&&c.vivos!=null)?`${esc(s)} · ${fmt(c.vivos)} en trámite hoy`:esc(s);
          return `<div class="mx-cross-card"><span class="mx-cc-n">${c[k]==null?'—':fmt(c[k])}</span><span class="mx-cc-l">${n}</span><span class="mx-cc-s">${sub}</span></div>`;
        }).join('')}
      </div>
      ${empresaNota(c.empresas)}
      ${L?`<div class="mx-verdict ${L.t}"><b>${esc(L.s)}.</b> ${esc(L.d)}</div>`:''}
      ${fallidos?`<div class="cob-note">${fallidos} de ${PILARES.length} fuentes no respondieron; sus casillas quedan en «—», que no es un cero.</div>`:''}
      <div class="cob-note">Cada cifra abre en Caudal la fuente completa:
        <a href="caudal.html#buscar" class="mx-link" id="mx-ir-caudal">ver «${esc(q)}» en las seis fuentes →</a></div>
    </div>`;
  const ir=$('mx-ir-caudal');
  if(ir) ir.onclick=e=>{ e.preventDefault(); location.href='caudal.html?tema='+encodeURIComponent(q); };
}

/* ══ 3 · CONCENTRACIÓN ════════════════════════════════════════════════
   40 titulares de 3 medios y 40 de 30 medios significan cosas opuestas: el
   primero es un medio empujando, el segundo es el ecosistema. Se mide con
   el índice Herfindahl sobre la participación de cada medio. */
function concentracion(porMedio){
  const tot=porMedio.reduce((a,m)=>a+m.n,0);
  if(!tot) return null;
  const hhi=porMedio.reduce((a,m)=>a+Math.pow(m.n/tot,2),0);
  const top3=porMedio.slice(0,3).reduce((a,m)=>a+m.n,0)/tot;
  return {hhi, top3, tot, n_medios:porMedio.length,
          // El top 20 es lo que devuelve la fuente: si hay más medios, el HHI
          // real es MENOR que este. Se declara para no vender precisión falsa.
          parcial:porMedio.length>=20};
}
function pintarConcentracion(k,porMedio){
  const el=$('mx-conc'); if(!el||!k) return;
  const lect=k.hhi>=0.25?{t:'mx-baja',s:'Cobertura concentrada',
      d:'Pocos medios están sosteniendo el tema. Conviene mirar quiénes son antes de leerlo como un clima de opinión.'}
    :k.hhi>=0.12?{t:'mx-neutro',s:'Cobertura repartida',
      d:'Varios medios lo cubren sin que ninguno domine.'}
    :{t:'mx-sube',s:'Cobertura de ecosistema',
      d:'El tema está distribuido en muchos medios a la vez: no lo empuja una sala de redacción, lo está cubriendo la prensa como conjunto.'};
  const max=porMedio[0]?porMedio[0].n:1;
  el.innerHTML=`
    <div class="panel">
      <h3>Quién sostiene la cobertura</h3>
      <div class="mx-kpis">
        <div class="kpi"><div class="n">${k.n_medios}${k.parcial?'+':''}</div><div class="l">Medios distintos</div></div>
        <div class="kpi"><div class="n">${Math.round(k.top3*100)}%</div><div class="l">Lo publican los 3 primeros</div></div>
        <div class="kpi"><div class="n">${k.hhi.toFixed(2)}</div><div class="l">Índice de concentración</div></div>
      </div>
      <div class="mx-bars">${porMedio.slice(0,10).map(m=>`
        <div class="mx-bar-row"><div class="mx-bar-lab">${esc(m.medio)}</div>
        <div class="mx-bar-track"><div class="mx-bar-fill" style="width:${Math.max(3,100*m.n/max).toFixed(1)}%"></div></div>
        <div class="mx-bar-n">${m.n}</div></div>`).join('')}</div>
      <div class="mx-verdict ${lect.t}"><b>${lect.s}.</b> ${lect.d}</div>
      ${k.parcial?'<div class="cob-note">La fuente devuelve los 20 medios más activos: si hay más, la concentración real es menor que la de arriba.</div>':''}
    </div>`;
}

/* ══ 4 · ACTORES INSTITUCIONALES ══════════════════════════════════════
   Cruce de los titulares contra el diccionario de voceros (94 entidades
   con su cargo, ya curado y verificado contra el sitio oficial de cada
   una). Se busca por PALABRA COMPLETA sobre el titular normalizado: el
   mismo criterio del diccionario de empresas, y por la misma razón —
   «SIC» dentro de «física» o «ANI» dentro de «compañía» sería ruido. */
const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
function aliasVocero(v){
  const out=[norm(v.nombre)];
  // La forma corta por la que la prensa realmente los nombra YA es el `id` del
  // diccionario («minsalud», «supersalud», «anla»). No se derivan más alias a
  // mano: «Ministerio de Salud» -> «salud» convertiría cualquier titular sobre
  // salud en una mención de la entidad.
  if(v.id&&v.id.length>=4&&!/^[0-9]+$/.test(v.id)) out.push(norm(v.id));
  return [...new Set(out)].filter(x=>x.length>=5);
}
function actores(resultados,voceros){
  if(!voceros||!voceros.items) return [];
  const hits=new Map();
  const cache=voceros.items.map(v=>({v,rx:aliasVocero(v).map(a=>new RegExp('(?<![a-z0-9])'+a.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?![a-z0-9])'))}));
  resultados.forEach(r=>{
    const t=norm(r.titulo);
    cache.forEach(({v,rx})=>{ if(rx.some(x=>x.test(t))){
      const e=hits.get(v.id)||{v,n:0,ej:null}; e.n++; if(!e.ej) e.ej=r; hits.set(v.id,e); } });
  });
  return [...hits.values()].sort((a,b)=>b.n-a.n);
}
function pintarActores(list,total){
  const el=$('mx-actores'); if(!el) return;
  if(!list.length){ el.innerHTML=`<div class="panel"><h3>Quién es nombrado</h3>
    <div class="cob-note">Ninguna de las 94 entidades del diccionario de voceros aparece en los
    titulares de esta consulta. Eso no significa que no estén involucradas: significa que la
    prensa no las está nombrando en el titular.</div></div>`; return; }
  el.innerHTML=`
    <div class="panel">
      <h3>Quién es nombrado</h3>
      <div class="mx-act">${list.slice(0,10).map(a=>`
        <div class="mx-act-row">
          <div><b>${esc(a.v.nombre)}</b><span class="mx-act-cargo">${esc(a.v.cargo||'')}${a.v.vocero?' · '+esc(a.v.vocero):''}</span></div>
          <div class="mx-act-n">${a.n}</div>
        </div>`).join('')}</div>
      <div class="cob-note">Entidades del diccionario de voceros de Caudal nombradas en el titular
        de ${fmt(total)} notas. Se busca por palabra completa; una entidad mencionada solo en el
        cuerpo de la nota no cuenta, porque de la nota solo tenemos el titular.</div>
    </div>`;
}

/* ══ 5 · MAPA TERRITORIAL ═════════════════════════════════════════════
   Dónde se está cubriendo el tema y, sobre todo, dónde NO. Tres estados,
   y la distinción entre los dos últimos es el punto:
     · cobertura      — medios de ese departamento publicaron
     · silencio       — tenemos medios mapeados ahí y publicaron cero
     · punto ciego    — no tenemos ningún medio de ese departamento
   Llamar «silencio» a un punto ciego sería atribuirle al departamento un
   vacío que es nuestro. */
const MEDIO_DEPTO={
  elcolombiano:'Antioquia', minuto30:'Antioquia', minuto60:'Antioquia',
  vivirenelpoblado:'Antioquia', telemedellin:'Antioquia', teleantioquia:'Antioquia',
  alertapaisa:'Antioquia', elpalpitar:'Antioquia',
  elheraldo:'Atlántico', diariolalibertad:'Atlántico', zonacero:'Atlántico',
  eluniversal:'Bolívar',
  vanguardia:'Santander', elfrente:'Santander',
  laopinion:'Norte de Santander',
  lapatria:'Caldas',
  cronicadelquindio:'Quindío', elquindiano:'Quindío',
  latarde:'Risaralda', diariodelotun:'Risaralda',
  elnuevodia:'Tolima',
  diariodelhuila:'Huila', opanoticias:'Huila', lanacion:'Huila',
  llano7dias:'Meta',
  elpilon:'Cesar',
  hoydiariodelmagdalena:'Magdalena', elinformador:'Magdalena', seguimiento:'Magdalena',
  diariodelnorte:'La Guajira', laguajirahoy:'La Guajira',
  elmeridianodecordoba:'Córdoba', elmeridiano:'Córdoba',
  proclamadelcauca:'Cauca',
  diariodelsur:'Nariño',
  citytv:'Distrito Capital de Bogotá', primiciadiario:'Distrito Capital de Bogotá',
};
/* Deliberadamente FUERA por ambiguos: «El País» (Cali y España), «Q'Hubo» y
   «Extra» (varias ciudades), Telecaribe y Telepacífico (varios departamentos),
   «El Mundo» (Medellín y España), «Diario del Cauca» (se edita en Cali). Un
   medio mal atribuido pinta un departamento entero de un color falso. */
const compact=s=>norm(s).replace(/[^a-z0-9]/g,'');
const DEPTOS_OBSERVABLES=new Set(Object.values(MEDIO_DEPTO));
function porDepto(porMedio){
  const d={};
  porMedio.forEach(m=>{ const c=compact(m.medio);
    // exacto primero: recortar el TLD antes convertiría «telepacifico» en
    // «telepacifi» y podría casar con una llave equivocada.
    const k=MEDIO_DEPTO[c]||MEDIO_DEPTO[c.replace(/(comco|com|co)$/,'')];
    if(k) d[k]=(d[k]||0)+m.n; });
  return d;
}
let _mapa=null, _capa=null;
async function pintarMapa(porMedio){
  const el=$('mx-mapa'); if(!el) return;
  const datos=porDepto(porMedio);
  const conDato=Object.keys(datos).length;
  const silencio=[...DEPTOS_OBSERVABLES].filter(d=>!datos[d]);
  el.innerHTML=`
    <div class="panel">
      <h3>Dónde se cubre, y dónde no</h3>
      <div class="mx-kpis">
        <div class="kpi"><div class="n">${conDato}</div><div class="l">Departamentos con cobertura propia</div></div>
        <div class="kpi"><div class="n">${silencio.length}</div><div class="l">Con prensa mapeada y cero titulares</div></div>
        <div class="kpi"><div class="n">${33-DEPTOS_OBSERVABLES.size}</div><div class="l">Sin prensa regional mapeada</div></div>
      </div>
      <div id="mx-map"></div>
      <div class="mx-leyenda">
        <span><i class="mx-sw mx-sw-3"></i>Cobertura alta</span>
        <span><i class="mx-sw mx-sw-1"></i>Cobertura baja</span>
        <span><i class="mx-sw mx-sw-0"></i>Silencio · hay prensa local y no publicó</span>
        <span><i class="mx-sw mx-sw-x"></i>Punto ciego · no tenemos prensa de ahí</span>
      </div>
      <div class="cob-note">⚠️ Tres límites que conviene tener presentes. El mapa dice dónde está
        el MEDIO que publicó, no dónde ocurrió el hecho: un diario de Antioquia cubriendo un tema
        nacional cuenta como Antioquia. Se arma con los <b>20 medios más activos</b> que devuelve la
        fuente, así que un diario regional con una sola nota puede quedar por fuera y su
        departamento verse en silencio sin estarlo. Y el «punto ciego» es un límite nuestro, no del
        departamento — son los ${33-DEPTOS_OBSERVABLES.size} departamentos para los que todavía no
        tenemos identificado ningún medio regional.</div>
    </div>`;
  try{
    const geo=await (await fetch(GEO_DEP)).json();
    const cont=$('mx-map'); if(!cont||!window.L) return;
    // Leaflet cachea el tamaño del contenedor al crearse; si nace oculto o a 0
    // de ancho, encuadra sobre nada. Por eso se crea DESPUÉS de insertar el
    // panel y se reencuadra en un setTimeout (no rAF, que se congela con la
    // pestaña de fondo).
    _mapa=L.map(cont,{zoomControl:false,attributionControl:false,dragging:false,
                      scrollWheelZoom:false,doubleClickZoom:false,boxZoom:false,keyboard:false});
    const max=Math.max(...Object.values(datos),1);
    _capa=L.geoJSON(geo,{style:f=>{
      const n=f.properties&&f.properties.name, v=datos[n]||0;
      if(v>0){ const t=Math.min(1,v/max);
        return {color:'#fff',weight:1,fillOpacity:.28+.62*t,fillColor:'#3d6eb8'}; }
      if(DEPTOS_OBSERVABLES.has(n)) return {color:'#fff',weight:1,fillOpacity:.55,fillColor:'#b4322a'};
      return {color:'#fff',weight:1,fillOpacity:.13,fillColor:'#6b7b87'};
    },onEachFeature:(f,l)=>{
      const n=f.properties&&f.properties.name, v=datos[n]||0;
      const est=v>0?`${v} titular${v===1?'':'es'} de prensa local`
        :DEPTOS_OBSERVABLES.has(n)?'Silencio: hay prensa local mapeada y no publicó'
        :'Punto ciego: no tenemos prensa regional de este departamento';
      l.bindTooltip(`<b>${esc(n)}</b><br>${est}`,{sticky:true});
    }}).addTo(_mapa);
    setTimeout(()=>{ try{ _mapa.invalidateSize();
      const b=_capa.getBounds(); if(b.isValid()) _mapa.fitBounds(b,{padding:[8,8],animate:false});
    }catch(e){} },0);
  }catch(e){ const c=$('mx-map'); if(c) c.innerHTML='<div class="cob-note">No se pudo cargar el mapa de departamentos.</div>'; }
}

/* ══ 6 · ATENCIÓN PÚBLICA (Wikipedia) ═════════════════════════════════
   ⚠️ Google Trends quedó FUERA y no por pereza: medido (sep-2026) responde
   1 de cada 4 veces desde una IP residencial colombiana —429 en las otras
   tres— y desde la Lambda, con IP de datacenter, sería peor. No hay API
   oficial. La de Wikimedia sí lo es, no pide llave, tiene CORS y respondió
   al primer intento; mide atención sobre ENTIDADES, no sobre temas, y eso
   se dice en la propia tarjeta. */
async function atencion(q){
  const el=$('mx-atencion'); if(!el) return;
  try{
    const s=await (await fetch(`https://es.wikipedia.org/w/api.php?action=opensearch&limit=5&namespace=0&format=json&origin=*&search=${encodeURIComponent(q)}`)).json();
    /* ⚠️⚠️ El buscador de Wikipedia SIEMPRE devuelve algo, y lo que devuelve
       puede no tener nada que ver. Medido: «reforma pensional» enganchaba
       «Reforma de las pensiones en España en 2011» —cero visitas— y la página
       lo presentaba como atención pública colombiana. Dos filtros duros:
         · todas las palabras significativas de la consulta deben estar en el
           título (así «pensional» descarta el artículo español), y
         · el título no puede nombrar otro país.
       Si ninguno de los cinco candidatos pasa, el bloque no se pinta. Es un
       complemento: es mejor que falte a que mienta. */
    const OTRO_PAIS=/\b(espana|mexico|argentina|chile|peru|ecuador|venezuela|bolivia|uruguay|paraguay|brasil|estados unidos|panama|costa rica)\b/;
    const pal=norm(q).split(/\s+/).filter(w=>w.length>=4);
    const titulo=((s&&s[1])||[]).find(t=>{
      const tn=norm(t);
      return pal.length&&pal.every(w=>tn.includes(w))&&!OTRO_PAIS.test(tn);
    });
    if(!titulo){ el.innerHTML=''; return; }
    const hoy=new Date(), ini=new Date(hoy-30*864e5);
    const f=d=>d.toISOString().slice(0,10).replace(/-/g,'');
    const pv=await (await fetch(`https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/es.wikipedia/all-access/user/${encodeURIComponent(titulo.replace(/ /g,'_'))}/daily/${f(ini)}/${f(hoy)}`)).json();
    const it=(pv&&pv.items)||[]; if(it.length<7){ el.innerHTML=''; return; }
    const vals=it.map(x=>x.views), max=Math.max(...vals,1);
    const ult=vals.slice(-7).reduce((a,b)=>a+b,0)/7;
    // Un artículo que nadie visita no mide atención: mide que el artículo existe.
    if(ult<1){ el.innerHTML=''; return; }
    const prev=vals.slice(0,-7); const base=prev.length?prev.reduce((a,b)=>a+b,0)/prev.length:0;
    const r=base>0?ult/base:null;
    el.innerHTML=`
      <div class="panel">
        <h3>Atención del público</h3>
        <div class="mx-spark">${vals.map(v=>`<i style="height:${Math.max(3,100*v/max).toFixed(0)}%" title="${v}"></i>`).join('')}</div>
        <div class="mx-kpis">
          <div class="kpi"><div class="n">${fmt(Math.round(ult))}</div><div class="l">Consultas/día · última semana</div></div>
          <div class="kpi"><div class="n">${r==null?'—':r.toFixed(2)+'×'}</div><div class="l">Frente al resto del mes</div></div>
        </div>
        <div class="cob-note">Visitas diarias al artículo <b>«${esc(titulo)}»</b> de Wikipedia en
          español (API oficial de Wikimedia). Mide interés del público por una ENTIDAD, no por un
          tema: sirve para «Ecopetrol» o un nombre propio, y no existe para «reforma pensional»,
          que no tiene artículo. No se usa Google Trends: sin API oficial, responde 1 de cada 4
          intentos y no es una fuente que se pueda sostener.</div>
      </div>`;
  }catch(e){ el.innerHTML=''; }
}

/* ══ ORQUESTACIÓN ═════════════════════════════════════════════════════
   Cada bloque se pinta EN CUANTO llega y falla por su cuenta: si el cruce
   con el Estado se cae, la temperatura ya está en pantalla. Progresivo, no
   un `await` gigante que deja la página en blanco 20 segundos. */
let VOCEROS=null, _seq=0;
async function analizar(q){
  q=(q||'').trim(); if(!q) return;
  const mine=++_seq;
  history.replaceState(null,'',location.pathname+'?q='+encodeURIComponent(q));
  const inp=$('mq'); if(inp) inp.value=q;
  $('mx-intro').hidden=true;
  $('mx-out').hidden=false;
  $('mx-titulo').innerHTML=`Cobertura de <em>${esc(q)}</em>`;
  ['mx-temp','mx-cruce','mx-conc','mx-actores','mx-mapa','mx-atencion','mx-lista']
    .forEach(id=>{ const e=$(id); if(e) e.innerHTML=''; });
  $('mx-temp').innerHTML='<div class="panel mx-load">Midiendo el ritmo de la cobertura…</div>';
  $('mx-cruce').innerHTML='<div class="panel mx-load">Cruzando con las cinco fuentes del Estado…</div>';

  /* Los dos bloques pesados salen A LA VEZ. El cruce NECESITA el volumen de
     prensa para leer el desfase, pero no para existir: se pinta apenas llega
     con la casilla de prensa en «—» y se repinta —ya con veredicto— cuando la
     temperatura aterriza. Encadenarlos sumaba las dos esperas, y con la caché
     de la fuente fría eso son más de quince segundos mirando un «cargando…». */
  let T=null, C=null;
  const pT=temperatura(q), pC=cruce(q);
  pC.then(c=>{ if(mine!==_seq) return; C=c; pintarCruce(c, T&&T.total30, q); })
    .catch(()=>{ if(mine!==_seq) return; const e=$('mx-cruce'); if(e) e.innerHTML='<div class="err">No se pudo cruzar con las fuentes del Estado.</div>'; });
  pT.then(t=>{
    if(mine!==_seq) return;
    T=t;
    pintarTemperatura(t,q);
    if(C) pintarCruce(C, t&&t.total30, q);   // ahora sí con el dato de prensa
    if(!t) return;
    const k=concentracion(t.por_medio||[]);
    pintarConcentracion(k,t.por_medio||[]);
    pintarMapa(t.por_medio||[]);
    pintarActores(actores(t.resultados||[],VOCEROS),(t.resultados||[]).length);
    pintarLista(t.resultados||[]);
  }).catch(err=>{
    if(mine!==_seq) return;
    $('mx-temp').innerHTML=String(err&&err.message)==='429'
      ? '<div class="err">Demasiadas consultas seguidas desde esta conexión. Espera un momento y reintenta.</div>'
      : '<div class="err">No se pudo consultar la prensa. Reintenta.</div>';
    // el cruce puede haber llegado bien: no se borra por un fallo de la prensa
  });
  atencion(q);
}

function pintarLista(res){
  const el=$('mx-lista'); if(!el) return;
  el.innerHTML=`
    <div class="panel">
      <h3>Los titulares</h3>
      <div class="sanc-list">${res.slice(0,40).map(r=>`
        <div class="sanc"><div class="sanc-t"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.titulo)}</a></div>
        <div class="sanc-tags"><span class="doc-badge">${esc(r.medio)}</span>${r.alcance==='regional'?'<span class="doc-badge pal">Regional</span>':'<span class="doc-badge">Nacional</span>'}<span class="mx-fecha">${esc(r.fecha||'')}</span></div></div>`).join('')
        ||'<div class="cob-note">Sin titulares en la ventana.</div>'}</div>
    </div>`;
}

const EJEMPLOS=['reforma pensional','reforma a la salud','licencia ambiental','Ecopetrol',
                'asbesto','plataformas tecnológicas','presupuesto general','tarifas de energía'];

function init(){
  const inp=$('mq'), btn=$('mgo'), chips=$('mchips');
  const go=()=>analizar(inp&&inp.value);
  if(btn) btn.onclick=go;
  if(inp) inp.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
  if(chips) EJEMPLOS.forEach(t=>{ const c=document.createElement('button');
    c.type='button'; c.className='chip'; c.textContent=t;
    c.onclick=()=>{ if(inp) inp.value=t; analizar(t); }; chips.appendChild(c); });
  // El diccionario de voceros es un <script> aparte; si no cargó, el bloque de
  // actores lo dice en vez de quedarse vacío en silencio.
  VOCEROS=window.CAUDAL_VOCEROS||null;
  const q=(new URLSearchParams(location.search).get('q')||'').trim();
  if(q) analizar(q);
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
