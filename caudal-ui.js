/* Transiciones progresivas: el contenido sigue visible si JS o la animación fallan. */
(function(){
  'use strict';
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const animations=new Set();
  const stopped=()=>reduced.matches||document.body.classList.contains('motion-paused');
  const stop=()=>{animations.forEach(a=>a.finish());animations.clear();};
  function enter(el,delay=0){
    if(stopped()||!el.animate) return;
    const a=el.animate([{opacity:0,transform:'translateY(22px)'},{opacity:1,transform:'translateY(0)'}],
      {duration:650,delay,easing:'cubic-bezier(.22,1,.36,1)',fill:'backwards'});
    animations.add(a); a.onfinish=()=>animations.delete(a); a.oncancel=()=>animations.delete(a);
  }
  reduced.addEventListener('change',()=>{if(reduced.matches)stop();});
  const toggle=document.getElementById('motion-toggle');
  if(toggle){
    const sync=()=>{toggle.disabled=reduced.matches;toggle.textContent=reduced.matches?'Movimiento reducido':stopped()?'Reanudar movimiento':'Pausar movimiento';toggle.setAttribute('aria-pressed',String(stopped()));};
    toggle.addEventListener('click',()=>{document.body.classList.toggle('motion-paused');if(stopped())stop();sync();});
    reduced.addEventListener('change',()=>{if(reduced.matches)stop();sync();}); sync();
  }
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      const visible=entries.filter(e=>e.isIntersecting);
      visible.forEach((entry,i)=>{enter(entry.target,Math.min(i,3)*65);observer.unobserve(entry.target);});
    },{threshold:.08});
    document.querySelectorAll('.caudal-landing .hero-copy,.caudal-landing .hero-visual,.sec-head,.qcard,.feat,.diff,.acc-card,.acc-side,.final,#view-home .home-hero,#view-home .radar-cta,.pcard').forEach(el=>observer.observe(el));
  }
  document.addEventListener('caudal:view',e=>{
    const el=document.getElementById('view-'+e.detail);
    if(el) enter(el);
  });
})();
