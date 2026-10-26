/* caudal-ctx.js — la empresa activa viaja a los módulos
   ------------------------------------------------------------------
   Pedido de Ricardo (oct-26-2026): cuando alguien entra a un módulo desde Mi
   Caudal leyendo para una empresa (Cauce, Comfama…), el módulo no debe buscar
   «Comfama»; debe saber para quién lee y CONECTAR cada resultado con sus
   intereses. Mi Caudal deja la ficha en sessionStorage['caudal-ctx'] al abrir
   un módulo; este script:
     1 · pinta arriba «Estás leyendo para Comfama» (con Quitar),
     2 · marca cada tarjeta de resultado que toca sus temas, su nombre, su
         competencia o las entidades que sigue, con el motivo,
     3 · expone window.CAUDAL_CTX para que la búsqueda universal pida su
         lectura con esa ficha (perfilId o cliente_k).
   Marca, no filtra: lo demás sigue a la vista. Funciona en cualquier página
   que lo cargue, porque mira las clases de tarjeta comunes (.sanc · .tl-item ·
   .vc) en vez de engancharse a cada render. Va por sesión (la pestaña): abrir
   Caudal en otra pestaña empieza sin contexto. */
(function(){
  'use strict';
  const KEY='caudal-ctx';
  let C=null;
  try{ C=JSON.parse(sessionStorage.getItem(KEY)||'null'); }catch(e){}
  if(new URLSearchParams(location.search).get('ctx')==='no'){ try{ sessionStorage.removeItem(KEY); }catch(e){} C=null; }
  if(!C||!C.nombre){ window.CAUDAL_CTX=null; return; }
  window.CAUDAL_CTX=C;

  const fold=t=>String(t||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim();
  const VACIAS=new Set(['de','del','la','las','los','el','y','en','para','por','con','sobre','nacional','general','publica','publico']);
  // Tema: todas sus palabras con cuerpo, por raíz de 6 letras (subsidio → subsid).
  const temas=(C.temas||[]).map(t=>({t, r:fold(t).split(' ').filter(w=>w.length>3&&!VACIAS.has(w)).map(w=>w.slice(0,6))})).filter(x=>x.r.length);
  // Nombres (la empresa y su competencia): palabra completa.
  const nombres=(C.nombres||[]).filter(n=>fold(n).length>=4).map(n=>({n, re:new RegExp('(^| )'+fold(n).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'( |$)')}));
  // Entidades que sigue: frase completa («ministerio del trabajo»).
  const entidades=(C.entidades||[]).map(e=>({e, f:fold(e)})).filter(x=>x.f.length>=6);

  function motivo(txt){
    const f=' '+fold(txt)+' ';
    for(const x of nombres) if(x.re.test(f)) return x.n;
    for(const x of entidades) if(f.includes(' '+x.f+' ')) return x.e;
    for(const x of temas) if(x.r.every(r=>f.includes(' '+r))) return x.t;
    return '';
  }

  const CSS=`.ctx-bar{display:flex;align-items:center;justify-content:space-between;gap:.8rem;flex-wrap:wrap;margin:0 auto 1rem;max-width:1080px;box-sizing:border-box;
      padding:.7rem 1rem;border:1px solid var(--teal-dim,rgba(152,192,248,.4));border-left:3px solid var(--teal,#3d6eb8);border-radius:8px;background:var(--card,#fff);font-size:.82rem;color:var(--ink2,#4d5462)}
    .ctx-bar b{color:var(--ink,#14161c)} .ctx-bar em{font-style:normal;color:var(--teal,#3d6eb8);font-weight:700}
    .ctx-bar .ctx-acts{display:flex;gap:.5rem}
    .ctx-bar a,.ctx-bar button{font:inherit;font-size:.74rem;padding:.3rem .65rem;border-radius:6px;border:1px solid var(--border2,#ccd);background:none;color:var(--ink2,#4d5462);text-decoration:none;cursor:pointer}
    .ctx-toca{box-shadow:inset 3px 0 0 var(--teal,#3d6eb8)}
    .ctx-badge{display:inline-block;margin-top:.35rem;font-size:.6rem;letter-spacing:.06em;text-transform:uppercase;font-weight:700;
      color:var(--teal,#3d6eb8);background:var(--teal-soft,rgba(152,192,248,.22));padding:.14rem .45rem;border-radius:4px}`;
  const st=document.createElement('style'); st.textContent=CSS; document.head.appendChild(st);

  let bar=null, nToca=0;
  function pintarBarra(){
    if(!bar){
      bar=document.createElement('div'); bar.className='ctx-bar'; bar.setAttribute('role','status');
      // dentro de <main> si la página lo tiene; si no, antes del primer bloque
      // de contenido (.wrap). Nunca antes de la nav: ahí queda tapada.
      const main=document.querySelector('main'), wrap=document.querySelector('.wrap');
      if(main) main.insertBefore(bar, main.firstChild);
      else if(wrap) { wrap.insertBefore(bar, wrap.firstChild); }
      else document.body.appendChild(bar);
    }
    bar.innerHTML=`<span>◈ Estás leyendo para <em>${String(C.nombre).replace(/</g,'&lt;')}</em>. Lo que toca sus temas, su nombre, su competencia o las entidades que sigue queda marcado${nToca?` · <b>${nToca}</b> en pantalla`:''}.</span>
      <span class="ctx-acts"><a href="caudal-mi.html${C.tipo==='empresa'?'?empresa='+encodeURIComponent(C.id):''}">Volver a Mi Caudal</a><button type="button" data-ctx-quitar>Quitar</button></span>`;
    bar.querySelector('[data-ctx-quitar]').onclick=()=>{ try{ sessionStorage.removeItem(KEY); }catch(e){} location.reload(); };
  }
  const SEL='.sanc,.tl-item,.vc';
  let t=null;
  function marcar(){
    t=null; let nuevos=0;
    document.querySelectorAll(SEL).forEach(el=>{
      if(el.dataset.ctx) return;
      el.dataset.ctx='1';
      const m=motivo(el.innerText||el.textContent||'');
      if(!m) return;
      el.dataset.ctx='toca'; el.classList.add('ctx-toca'); nuevos++;
      const b=document.createElement('span'); b.className='ctx-badge';
      b.textContent='Le toca a '+C.nombre+' · '+m;
      el.appendChild(b);
    });
    const n=document.querySelectorAll('[data-ctx="toca"]').length;
    if(nuevos||n!==nToca){ nToca=n; pintarBarra(); }
  }
  function arrancar(){
    pintarBarra(); marcar();
    new MutationObserver(()=>{ if(!t) t=setTimeout(marcar,180); }).observe(document.body,{childList:true,subtree:true});
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',arrancar); else arrancar();
})();
