const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function fixture(width=390){
 let id=0,now=0;const frames=new Map(),timers=new Map(),images=[],events=[];
 const node=()=>({style:{},hidden:false,setAttribute(){},remove(){this.removed=true;}});
 const motion={matches:false,addEventListener(){},removeEventListener(){}};
 const document={hidden:false,currentScript:{src:'http://localhost/candi-hueso.js'},createElement:node,addEventListener(){},removeEventListener(){}};
 const host={clientWidth:width,append(){},addEventListener(){},removeEventListener(){},dispatchEvent:e=>events.push(e)};
 const mascot={phase:'idle_seated',sprite:node(),pause(){},seek(){this.phase='idle_seated'},idle(){this.phase='idle_seated';return Promise.resolve()}};
 const context={URL,Math,Number,Promise,document,window:{},matchMedia:()=>motion,
  ResizeObserver:class{constructor(fn){this.fn=fn}observe(){}disconnect(){}},
  CustomEvent:class{constructor(type,init){this.type=type;this.detail=init?.detail}},
  Image:class{set src(value){images.push(this)}},
  setTimeout:fn=>{const n=++id;timers.set(n,fn);return n},clearTimeout:n=>timers.delete(n),
  requestAnimationFrame:fn=>{const n=++id;frames.set(n,fn);return n},cancelAnimationFrame:n=>frames.delete(n)};
 vm.runInNewContext(fs.readFileSync(__dirname+'/candi-hueso.js','utf8'),context);
 const seq=new context.window.CandiBoneSequence(host,{mascot});
 const step=()=>{now+=100;const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn(now));};
 return {seq,host,mascot,motion,document,images,events,frames,timers,step};
}
(async()=>{
 const f=fixture();
 for(const width of [280,320,360,390,768,1440,2560]){
  f.host.clientWidth=width;f.seq.times=f.seq.timing();
  for(let t=0;t<=f.seq.times.total;t+=73){f.seq.render(t);const x=parseFloat(f.seq.actor.style.left),s=parseFloat(f.seq.actor.style.width);assert(x>=0);assert(x+s<=width+.001);}
  f.seq.render(f.seq.times.total);assert.equal(f.seq.phase,'resting');assert.equal(f.seq.bone.hidden,true);
 }
 f.host.clientWidth=390;const starting=f.seq.play();assert.equal(f.images.length,4);f.images.forEach(img=>img.onload());await starting;
 assert.equal(f.mascot.sprite.hidden,true);assert.equal(f.seq.actor.hidden,false);
 f.document.hidden=true;f.seq.onVisibility();const before=f.seq.elapsed;f.step();assert.equal(f.seq.elapsed,before);
 f.document.hidden=false;f.seq.onVisibility();for(let n=0;n<180;n++)f.step();
 assert.equal(f.seq.phase,'resting');assert.equal(f.frames.size,0);assert.equal(f.events.filter(e=>e.type==='candi:bone-complete').length,1);
 f.seq.onActivity({target:{closest:()=>null}});assert.equal(f.seq.active,false);assert.equal(f.mascot.sprite.hidden,false);
 f.seq.enable();assert.equal(f.timers.size,1);f.document.hidden=true;f.seq.onVisibility();assert.equal(f.timers.size,0);f.document.hidden=false;f.seq.onVisibility();assert.equal(f.timers.size,1);
 f.seq.destroy();assert.equal(f.frames.size,0);assert.equal(f.timers.size,0);
 const reduced=fixture();reduced.motion.matches=true;await reduced.seq.play();assert.equal(reduced.images.length,0);reduced.seq.enable();assert.equal(reduced.timers.size,0);reduced.seq.destroy();
 const pending=fixture();const promise=pending.seq.play();pending.seq.pause();pending.images.forEach(img=>img.onload());await promise;assert.equal(pending.seq.actor.hidden,true);assert.equal(pending.frames.size,0);pending.seq.destroy();
 console.log('OK: bounds at 7 widths, resting completion, hidden-tab pause, activity wake, timer lifecycle, reduced motion, cancellation during load.');
})().catch(e=>{console.error(e);process.exitCode=1});
