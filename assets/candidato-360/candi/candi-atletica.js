/* Candi atlética v3. Reproductor independiente; no modifica el chat existente. */
(() => {
  const base = new URL('.', document.currentScript.src);
  const clips = {
    greeting: {file:'candi-saludo-atletica-v3.webp',cols:5,rows:4},
    seated: {file:'candi-sentarse-atenta-v3.webp',cols:4,rows:4},
    curious: {file:'candi-curiosa-atletica-v3.webp',cols:4,rows:3},
    thinking: {file:'candi-pensando-atletica-v3.webp',cols:6,rows:5}
  };
  class CandiAtletica {
    constructor(host) {
      this.host=host; this.time=0; this.token=0; this.phase=''; this.destroyed=false;
      this.sprite=document.createElement('div'); this.sprite.className='candi-sprite';
      this.sprite.setAttribute('role','img'); this.sprite.setAttribute('aria-label','Candi sentada y atenta'); host.append(this.sprite);
      this.motion=matchMedia('(prefers-reduced-motion: reduce)');
      this.visibility=()=>{this.previous=null;};
      this.reduce=()=>{if(this.motion.matches){this.pause();this.seek(4800);}};
      document.addEventListener('visibilitychange',this.visibility);this.motion.addEventListener('change',this.reduce);
      this.ready=Promise.all([clips.greeting,clips.seated].map(clip=>new Promise((resolve,reject)=>{
        const img=new Image();img.onload=()=>resolve();img.onerror=()=>reject(new Error('No se pudo cargar '+clip.file));img.src=new URL(clip.file,base).href;
      })));
      this.seek(4800);
    }
    paint(clipName,frame,offset=0) {
      const clip=clips[clipName];
      this.sprite.style.backgroundImage=`url("${new URL(clip.file,base).href}")`;
      this.sprite.style.backgroundSize=`${clip.cols*100}% ${clip.rows*100}%`;
      this.sprite.style.backgroundPosition=`${frame%clip.cols*100/(clip.cols-1)}% ${Math.floor(frame/clip.cols)*100/(clip.rows-1)}%`;
      if(clipName==='thinking'){
        // Filas generadas con alturas diferentes: incluir bombillo y patas enteras.
        const row=Math.floor(frame/6),starts=[0,226,445,690,936],heights=[226,219,245,246,209];
        this.sprite.style.backgroundSize=`600% ${1145/heights[row]*100}%`;
        this.sprite.style.backgroundPosition=`${frame%6*20}% ${starts[row]/(1145-heights[row])*100}%`;
      }
      this.sprite.style.transform=`translateX(${offset}px)`;
      this.sprite.style.clipPath=clipName==='greeting'?'inset(1.5%)':'none';
    }
    seek(ms) {
      this.time=Math.max(0,Number(ms)||0); const t=this.time; let frame,phase;
      if(t<3200){
        phase='enter_greet';
        const boundaries=[0,140,280,420,560,700,840,980,1120,1240,1380,1530,1700,1840,1980,2140,2340,2540,2740,2960];
        frame=0;for(let i=1;i<20;i++)if(t>=boundaries[i])frame=i;
        const p=Math.min(t/1380,1); const easing=1-Math.pow(1-p,1.25);
        this.paint('greeting',frame===19?18:frame,(this.sprite.offsetWidth+32)*(1-easing));
      } else if(t<4800){phase='sit_down';frame=Math.min(7,Math.floor((t-3200)/200));this.paint('seated',frame);}
      else {
        phase='idle_seated';
        // Cola suave en ciclos de 4 s: pequeña pausa y ocho poses, sin paseo.
        const cycle=(t-4800)%4000;
        const tailFrames=[8,13,14,15,14,13,8,8];
        frame=this.motion.matches || cycle<1800 ? 8 : tailFrames[Math.min(7,Math.floor((cycle-1800)/275))];
        this.paint('seated',frame);
      }
      if(phase!==this.phase){this.phase=phase;this.sprite.setAttribute('aria-label',phase==='idle_seated'?'Candi sentada y atenta':phase==='sit_down'?'Candi se sienta':'Candi llega y saluda');this.host.dispatchEvent(new CustomEvent('candi:state',{detail:{state:phase}}));}
      this.host.dispatchEvent(new CustomEvent('candi:frame',{detail:{time:t,frame,state:phase}}));
    }
    async play({speed=1,from=0}={}){
      if(this.destroyed)return;
      this.pause();const token=this.token;await this.ready;if(token!==this.token||this.destroyed)return;
      this.seek(this.motion.matches?4800:from);
      if(this.motion.matches){this.host.dispatchEvent(new CustomEvent('candi:complete'));return;}
      const rate=Number.isFinite(speed)&&speed>0?speed:1;
      let complete=from>=4800;this.previous=null;
      const tick=now=>{
        if(token!==this.token)return;
        if(!document.hidden){const dt=this.previous===null?0:Math.min(100,now-this.previous);this.previous=now;this.seek(this.time+dt*rate);
          if(!complete&&this.time>=4800){complete=true;this.host.dispatchEvent(new CustomEvent('candi:complete'));}
        }else this.previous=null;
        this.raf=requestAnimationFrame(tick);
      };this.raf=requestAnimationFrame(tick);
    }
    reactionFrame(kind,ms) {
      const poses=kind==='curious'?[0,1,2,3,4,5,6,6,6,7,8,9,10,11]:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,19,19,19,19,24,25,26,27,28,29];
      const duration=kind==='curious'?2800:6000;
      const elapsed=Math.max(0,Math.min(duration,Number(ms)||0));
      const frame=poses[Math.min(poses.length-1,Math.floor(elapsed/200))];
      this.paint(kind,frame);
      this.host.dispatchEvent(new CustomEvent('candi:frame',{detail:{time:elapsed,frame,state:kind,duration}}));
    }
    async reaction(kind,{speed=1}={}) {
      if(this.destroyed)return;
      if(!['curious','thinking'].includes(kind))throw new Error('Reacción desconocida');
      this.pause();const token=this.token;
      if(this.motion.matches){this.seek(4800);return;}
      this.reactionLoads ||= {};
      if(!this.reactionLoads[kind])this.reactionLoads[kind]=new Promise((resolve,reject)=>{
        const img=new Image();img.onload=resolve;img.onerror=()=>{delete this.reactionLoads[kind];reject(new Error('No se pudo cargar '+kind));};
        img.src=new URL(clips[kind].file,base).href;
      });
      await this.reactionLoads[kind];if(token!==this.token||this.destroyed)return;
      this.phase=kind;this.sprite.setAttribute('aria-label',kind==='curious'?'Candi inclina la cabeza con curiosidad':'Candi se pone gafas y un bombillo se ilumina');
      this.host.dispatchEvent(new CustomEvent('candi:state',{detail:{state:kind}}));
      let elapsed=0;this.previous=null;const rate=Number.isFinite(speed)&&speed>0?speed:1;
      const duration=kind==='curious'?2800:6000;
      const tick=now=>{
        if(token!==this.token)return;
        if(!document.hidden){elapsed+=(this.previous===null?0:Math.min(100,now-this.previous))*rate;this.previous=now;}else this.previous=null;
        this.reactionFrame(kind,elapsed);
        if(elapsed<duration)this.raf=requestAnimationFrame(tick);
        else {
          this.host.dispatchEvent(new CustomEvent('candi:reaction-complete',{detail:{state:kind}}));
          // A listener may have started another animation; do not override it.
          if(token===this.token)this.idle().catch(()=>{if(!this.destroyed)this.seek(4800);});
        }
      };this.raf=requestAnimationFrame(tick);
    }
    curious(options={}){return this.reaction('curious',options);}
    thinking(options={}){return this.reaction('thinking',options);}
    idle(options={}){return this.play({...options,from:4800});}
    pause(){this.token++;cancelAnimationFrame(this.raf);this.previous=null;}
    destroy(){this.destroyed=true;this.pause();document.removeEventListener('visibilitychange',this.visibility);this.motion.removeEventListener('change',this.reduce);this.sprite.remove();}
  }
  window.CandiAtletica=CandiAtletica;
})();
