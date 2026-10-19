/* Motor de gráficos de los módulos de datos del hub de Policía.
   SVG a mano, sin librerías (el resto del hub tampoco las usa).
   Clásico, no módulo: las constantes y funciones quedan en el ámbito global y
   los <script> en línea de cada página las usan directo (lineas, apiladas,
   barrasLineas, barrasH, leyenda, pills, J…). Por eso NO se pueden volver a
   declarar en la página: daría «Identifier has already been declared».
   Depende de legislativo-base.js (esc) y ponal-base.js (PONAL.BASE).
   Se carga después del <body> (crea el tooltip si falta). */
const DATA_V='20260930';
const AMB='#e0a03a', RED='#d1584e', BLU='#3d6fff', GRN='#4ade80', CYA='#22d3ee', VIO='#a78bfa', GRY='rgba(255,255,255,.35)';
const PAL=['#e0a03a','#d1584e','#3d6fff','#22d3ee','#a78bfa','#4ade80','#f472b6','#94a3b8'];
const nf=n=>n==null||isNaN(n)?'—':Math.round(n).toLocaleString('es-CO');
const pf=(n,d=1)=>n==null||isNaN(n)?'—':n.toFixed(d).replace('.',',')+'%';
const nice=s=>String(s||'').toLowerCase().replace(/(^|\s|\/|\()([a-záéíóúñü])/g,(m,a,b)=>a+b.toUpperCase());
const MESES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const ym=s=>{const [a,m]=s.split('-');return MESES[+m-1]+' '+a.slice(2)};

async function J(nombre){
  const r=await fetch(PONAL.BASE+'/'+nombre+'?v='+DATA_V);
  if(!r.ok) throw new Error(nombre+' HTTP '+r.status);
  return r.json();
}

/* ═════════════════════════ tooltip ═════════════════════════ */
/* el tooltip se crea solo si la página no lo trae: así cualquier página del hub
   puede usar estos gráficos sin copiar el <div> */
const TIP=document.getElementById('tip')||(()=>{const d=document.createElement('div');d.className='tip';d.id='tip';document.body.appendChild(d);return d})();
function tipOn(e,html){ TIP.innerHTML=html; TIP.style.display='block'; tipMove(e); }
function tipMove(e){
  const w=TIP.offsetWidth, x=e.clientX+14, y=e.clientY+14;
  TIP.style.left=(x+w>innerWidth-8?e.clientX-w-14:x)+'px'; TIP.style.top=y+'px';
}
function tipOff(){ TIP.style.display='none'; }
/* Cada gráfico registra un array de textos por columna; un solo listener por
   contenedor busca la columna más cercana en X — acertarle a un punto de 3px
   con el mouse es imposible. */
function hoverCols(el,svg,xs,textos){
  const r=()=>svg.getBoundingClientRect();
  const vb=svg.viewBox.baseVal;
  el.onmousemove=e=>{
    const b=r(), xv=(e.clientX-b.left)*vb.width/b.width;
    let k=0,d=1e9; xs.forEach((x,i)=>{const dd=Math.abs(x-xv); if(dd<d){d=dd;k=i}});
    const g=svg.querySelector('.gl'); if(g){g.setAttribute('x1',xs[k]);g.setAttribute('x2',xs[k]);g.style.display='block'}
    tipOn(e,textos[k]);
  };
  el.onmouseleave=()=>{tipOff(); const g=svg.querySelector('.gl'); if(g) g.style.display='none';};
}

/* ═════════════════════════ gráficos SVG ═════════════════════════
   Sin librerías: el resto del hub tampoco las usa y así la página pesa poco. */
function ejeY(max,H,P,W,fmt){
  let s='';
  for(let i=0;i<=4;i++){
    const v=max*i/4, y=P.t+(H-P.t-P.b)*(1-i/4);
    s+=`<line class="gr" x1="${P.l}" x2="${W-P.r}" y1="${y}" y2="${y}"/><text x="${P.l-6}" y="${y+3}" text-anchor="end">${fmt(v)}</text>`;
  }
  return s;
}
function niceMax(v){ if(v<=0) return 1; const p=Math.pow(10,Math.floor(Math.log10(v))); const f=v/p; return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*p; }
const fmtK=v=>v>=1e6?(v/1e6).toFixed(1).replace('.0','').replace('.',',')+' M':v>=1e4?Math.round(v/1e3)+' mil':v>=1e3?(v/1e3).toFixed(1).replace('.0','').replace('.',',')+' mil':Math.round(v);

/* líneas · series:[{name,color,values,dash,w}] · opts:{pct,partialFrom,yMax,H} */
function lineas(id,labels,series,opts={}){
  const el=document.getElementById(id), W=760, H=opts.H||260, P={l:52,r:14,t:12,b:26};
  const vals=series.flatMap(s=>s.values.filter(v=>v!=null));
  const max=opts.yMax||niceMax(Math.max(...vals,opts.pct?1:1));
  const xs=labels.map((_,i)=>P.l+(W-P.l-P.r)*(labels.length>1?i/(labels.length-1):.5));
  const y=v=>P.t+(H-P.t-P.b)*(1-v/max);
  const fy=opts.pct?(v=>Math.round(v)+'%'):fmtK;
  let s=`<svg viewBox="0 0 ${W} ${H}">`+ejeY(max,H,P,W,fy);
  const paso=Math.ceil(labels.length/14);
  labels.forEach((l,i)=>{ if(i%paso===0||i===labels.length-1) s+=`<text x="${xs[i]}" y="${H-8}" text-anchor="middle">${l}</text>`; });
  if(opts.partialFrom!=null){ const i=labels.indexOf(opts.partialFrom); if(i>=0) s+=`<rect x="${xs[i]-(xs[1]-xs[0])/2}" y="${P.t}" width="${W-P.r-xs[i]+(xs[1]-xs[0])/2}" height="${H-P.t-P.b}" fill="rgba(255,255,255,.035)"/>`; }
  s+=`<line class="gl" x1="0" x2="0" y1="${P.t}" y2="${H-P.b}" stroke="rgba(255,255,255,.25)" style="display:none"/>`;
  series.forEach(se=>{
    let d='',on=false;
    se.values.forEach((v,i)=>{ if(v==null){on=false;return} d+=(on?'L':'M')+xs[i].toFixed(1)+','+y(v).toFixed(1); on=true; });
    s+=`<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.w||2.2}" ${se.dash?`stroke-dasharray="${se.dash}"`:''} stroke-linejoin="round" stroke-linecap="round"/>`;
    if(!se.dash && labels.length<=20) se.values.forEach((v,i)=>{ if(v!=null) s+=`<circle cx="${xs[i]}" cy="${y(v)}" r="2.6" fill="${se.color}"/>`; });
  });
  s+='</svg>';
  el.innerHTML=s;
  const tx=labels.map((l,i)=>`<b>${l}</b><br>`+series.map(se=>`<span style="color:${se.color}">●</span> ${se.name}: ${se.values[i]==null?'—':(opts.pct?pf(se.values[i]):nf(se.values[i]))}`).join('<br>'));
  hoverCols(el,el.querySelector('svg'),xs,opts.tips||tx);
}
function leyenda(id,items){ document.getElementById(id).innerHTML=items.map(([n,c,ln])=>`<span><i class="${ln?'ln':''}" style="background:${c}"></i>${n}</span>`).join(''); }

/* barras apiladas por año · series:[{name,color,values}] · pct: normaliza a 100 */
function apiladas(id,labels,series,opts={}){
  const el=document.getElementById(id), W=760, H=opts.H||270, P={l:52,r:14,t:12,b:26};
  const tot=labels.map((_,i)=>series.reduce((a,s)=>a+(s.values[i]||0),0));
  const max=opts.pct?100:niceMax(Math.max(...tot));
  const bw=(W-P.l-P.r)/labels.length, xs=labels.map((_,i)=>P.l+bw*i+bw/2);
  const y=v=>P.t+(H-P.t-P.b)*(1-v/max);
  let s=`<svg viewBox="0 0 ${W} ${H}">`+ejeY(max,H,P,W,opts.pct?(v=>Math.round(v)+'%'):fmtK);
  labels.forEach((l,i)=>{
    let acc=0;
    series.forEach(se=>{
      const v=se.values[i]||0, vv=opts.pct?(tot[i]?100*v/tot[i]:0):v;
      if(vv>0) s+=`<rect x="${(xs[i]-bw*.38).toFixed(1)}" width="${(bw*.76).toFixed(1)}" y="${y(acc+vv).toFixed(1)}" height="${(y(acc)-y(acc+vv)).toFixed(1)}" fill="${se.color}" ${opts.partial&&opts.partial.includes(l)?'opacity=".55"':''}/>`;
      acc+=vv;
    });
    if(i%Math.ceil(labels.length/16)===0||i===labels.length-1) s+=`<text x="${xs[i]}" y="${H-8}" text-anchor="middle">${l}</text>`;
  });
  s+=`<line class="gl" x1="0" x2="0" y1="${P.t}" y2="${H-P.b}" stroke="rgba(255,255,255,.18)" style="display:none"/></svg>`;
  el.innerHTML=s;
  const tx=labels.map((l,i)=>`<b>${l}</b> · total ${nf(tot[i])}<br>`+series.filter(se=>se.values[i]).map(se=>`<span style="color:${se.color}">■</span> ${se.name}: ${nf(se.values[i])} (${pf(tot[i]?100*se.values[i]/tot[i]:0)})`).join('<br>'));
  hoverCols(el,el.querySelector('svg'),xs,tx);
}

/* barras + líneas en % (eje derecho) — el gráfico de armas */
function barrasLineas(id,labels,barras,lineasS,opts={}){
  const el=document.getElementById(id), W=760, H=opts.H||300, P={l:52,r:42,t:14,b:26};
  const max=niceMax(Math.max(...barras.values.filter(v=>v!=null),1));
  const bw=(W-P.l-P.r)/labels.length, xs=labels.map((_,i)=>P.l+bw*i+bw/2);
  const y=v=>P.t+(H-P.t-P.b)*(1-v/max), yp=v=>P.t+(H-P.t-P.b)*(1-v/100);
  let s=`<svg viewBox="0 0 ${W} ${H}">`+ejeY(max,H,P,W,fmtK);
  for(let i=0;i<=4;i++) s+=`<text x="${W-P.r+6}" y="${P.t+(H-P.t-P.b)*(1-i/4)+3}">${i*25}%</text>`;
  labels.forEach((l,i)=>{
    const v=barras.values[i];
    if(v!=null){
      const par=opts.partial&&opts.partial.includes(l);
      s+=`<rect x="${(xs[i]-bw*.36).toFixed(1)}" width="${(bw*.72).toFixed(1)}" y="${y(v).toFixed(1)}" height="${(y(0)-y(v)).toFixed(1)}" fill="${par?'none':barras.color}" stroke="${barras.color}" ${par?'stroke-dasharray="3 2"':''}/>`;
    }
    if(i%Math.ceil(labels.length/17)===0||i===labels.length-1) s+=`<text x="${xs[i]}" y="${H-8}" text-anchor="middle">${l}${opts.partial&&opts.partial.includes(l)?'*':''}</text>`;
  });
  s+=`<line class="gl" x1="0" x2="0" y1="${P.t}" y2="${H-P.b}" stroke="rgba(255,255,255,.2)" style="display:none"/>`;
  lineasS.forEach(se=>{
    let d='',on=false;
    se.values.forEach((v,i)=>{ if(v==null){on=false;return} d+=(on?'L':'M')+xs[i].toFixed(1)+','+yp(v).toFixed(1); on=true; });
    s+=`<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.w||2.4}" ${se.dash?`stroke-dasharray="${se.dash}"`:''}/>`;
    if(!se.dash) se.values.forEach((v,i)=>{ if(v!=null) s+=`<circle cx="${xs[i]}" cy="${yp(v)}" r="2.8" fill="${se.color}"/>`; });
  });
  el.innerHTML=s+'</svg>';
  const tx=labels.map((l,i)=>`<b>${l}</b><br>${barras.name}: ${nf(barras.values[i])}<br>`+lineasS.map(se=>`<span style="color:${se.color}">●</span> ${se.name}: ${pf(se.values[i])}`).join('<br>'));
  hoverCols(el,el.querySelector('svg'),xs,tx);
}

function barrasH(id,items,opts={}){
  const max=Math.max(...items.map(i=>i.v),1);
  document.getElementById(id).innerHTML=items.length?items.map(i=>`<div class="bar-i" title="${esc(i.full||i.l)}"><span class="l">${esc(i.l)}</span><span><span class="t" style="display:block;width:${(100*i.v/max).toFixed(1)}%;background:${i.c||opts.c||AMB}"></span></span><span class="v">${opts.fmt?opts.fmt(i.v):nf(i.v)}</span></div>`).join(''):'<div class="nota">Sin dato para esta selección.</div>';
}

/* ═════════════════════════ ayudas de series ═════════════════════════ */
const rango=(a,b)=>Array.from({length:b-a+1},(_,i)=>String(a+i));
const serie=(obj,anios)=>anios.map(a=>obj&&obj[a]!=null?+obj[a]:null);

function pills(cont,items,get,set){
  const el=document.getElementById(cont);
  el.innerHTML=items.map(([v,n])=>`<button class="pill${get()===v?' on':''}" data-v="${v}">${n}</button>`).join('');
  el.onclick=e=>{const b=e.target.closest('button'); if(!b) return; set(b.dataset.v); el.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));};
}
function grupoPills(sel,attr,set){
  document.querySelectorAll(sel).forEach(b=>b.onclick=()=>{ if(b.disabled) return; document.querySelectorAll(sel).forEach(x=>x.classList.toggle('on',x===b)); set(b.dataset[attr]); });
}
