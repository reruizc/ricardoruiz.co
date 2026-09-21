/* Secuencia decorativa opcional: 24 caminar + 24 recoger + 22 echarse. */
(() => {
  const base=new URL('.',document.currentScript.src);
  const assets={walk:'candi-hueso-caminar-v1.webp',pickup:'candi-hueso-recoger-v1.webp',lie:'candi-hueso-echarse-v1.webp',bone:'candi-hueso-rosado-v1.webp'};
  const registration={"walk":{"tops":[0,256,512,768],"heights":[256,256,256,256],"bottoms":[255,255,255,256,255,255,239,240,239,237,240,238,222,221,220,222,224,224,211,211,214,215,215,214],"width":1536,"height":1024,"cell":256},"pickup":{"tops":[0,256,512,768],"heights":[256,256,256,256],"bottoms":[235,234,234,234,234,234,228,228,228,228,228,228,220,220,221,221,221,221,213,214,215,215,214,215],"width":1536,"height":1024,"cell":256},"lie":{"tops":[0,290,535,770],"heights":[290,245,235,254],"bottoms":[282,282,282,283,284,285,228,228,228,229,229,229,207,207,208,208,207,207,193,194,194,194],"width":1536,"height":1024,"cell":256}};
  class CandiBoneSequence {
    constructor(host,{mascot=null,inactivityMs=45000,activityTarget=document}={}){
      this.host=host;this.mascot=mascot;this.delay=Math.max(1000,inactivityMs);this.activityTarget=activityTarget;
      this.active=false;this.enabled=false;this.destroyed=false;this.token=0;this.elapsed=0;this.phase='';
      this.actor=document.createElement('div');this.actor.className='candi-bone-actor';this.actor.setAttribute('aria-hidden','true');
      this.bone=document.createElement('img');this.bone.className='candi-bone-toy';this.bone.alt='';this.bone.setAttribute('aria-hidden','true');
      this.actor.hidden=true;this.bone.hidden=true;host.append(this.bone,this.actor);
      this.motion=matchMedia('(prefers-reduced-motion: reduce)');
      this.onActivity=e=>{if(e.target?.closest?.("[data-candi-bone-controls]"))return;if(this.active)this.wake();else this.arm();};
      this.onVisibility=()=>{this.previous=null;clearTimeout(this.timer);if(!document.hidden&&!this.active)this.arm();};
      this.onMotion=()=>{if(this.motion.matches)this.wake();else this.arm();};
      this.onMascotState=e=>{if(e.detail.state!=='idle_seated')clearTimeout(this.timer);else this.arm();};
      for(const type of ['pointerdown','pointermove','keydown','wheel','input'])activityTarget.addEventListener(type,this.onActivity,{passive:true});
      document.addEventListener('visibilitychange',this.onVisibility);this.motion.addEventListener('change',this.onMotion);host.addEventListener('candi:state',this.onMascotState);
      this.resize=new ResizeObserver(()=>{if(this.active)this.render(this.elapsed);});this.resize.observe(host);
    }
    enable(value=true){this.enabled=Boolean(value);if(!this.enabled)this.wake();else this.arm();}
    arm(){
      clearTimeout(this.timer);
      if(!this.enabled||this.active||this.destroyed||document.hidden||this.motion.matches)return;
      this.timer=setTimeout(()=>{
        if(this.mascot&&this.mascot.phase!=='idle_seated'){this.arm();return;}
        this.play().catch(error=>this.host.dispatchEvent(new CustomEvent('candi:bone-error',{detail:{message:error.message}})));
      },this.delay);
    }
    load(){
      if(!this.loading)this.loading=Promise.all(Object.values(assets).map(file=>new Promise((resolve,reject)=>{
        const img=new Image();img.onload=resolve;img.onerror=()=>reject(new Error('No se pudo cargar '+file));img.src=new URL(file,base).href;
      }))).catch(error=>{this.loading=null;throw error;});
      return this.loading;
    }
    layout(){
      const width=this.host.clientWidth;
      const size=Math.min(210,Math.max(100,width*.34),Math.max(1,width-24));
      const margin=Math.min(18,width*.04);
      return {width,size,start:Math.max(margin,width-size-margin),end:margin,margin};
    }
    timing(){
      const g=this.layout();
      // A larger screen needs more walking time; it never changes frame count.
      const travel=Math.round(Math.max(1400,Math.min(8000,(g.start-g.end)/140*1000)));
      const walk=800+travel+400;
      return {walk,pickup:2400,lie:2200,total:walk+4600,travel};
    }
    render(ms){
      const g=this.layout(),t=this.times||this.timing();this.elapsed=Math.max(0,Math.min(t.total,ms));
      let clip,frame,x=g.end;
      if(this.elapsed<t.walk){
        clip='walk';
        if(this.elapsed<800){frame=Math.min(7,Math.floor(this.elapsed/100));x=g.start;}
        else if(this.elapsed<800+t.travel){
          const progress=(this.elapsed-800)/t.travel;
          frame=8+Math.floor((this.elapsed-800)/90)%12;x=g.start+(g.end-g.start)*progress;
        }else frame=20+Math.min(3,Math.floor((this.elapsed-800-t.travel)/100));
      }else if(this.elapsed<t.walk+t.pickup){clip='pickup';frame=Math.min(23,Math.floor((this.elapsed-t.walk)/100));}
      else {clip='lie';frame=Math.min(21,Math.floor((this.elapsed-t.walk-t.pickup)/100));}
      const reg=registration[clip],row=Math.floor(frame/6),height=reg.heights[row];
      this.actor.style.width=g.size+'px';this.actor.style.height=(g.size*height/reg.cell)+'px';this.actor.style.left=x+'px';
      this.actor.style.transform=`translateY(${(height-reg.bottoms[frame])*g.size/reg.cell}px)`;
      this.actor.style.backgroundImage=`url("${new URL(assets[clip],base).href}")`;
      this.actor.style.clipPath=clip==='pickup'?'inset(0 1% 0 7%)':'none';
      this.actor.style.backgroundSize=`600% ${reg.height/height*100}%`;this.actor.style.backgroundPosition=`${frame%6*20}% ${reg.tops[row]/(reg.height-height)*100}%`;
      this.bone.hidden=clip!=='walk';this.bone.src=new URL(assets.bone,base).href;
      this.bone.style.width=g.size*.26+'px';this.bone.style.height=g.size*.13+'px';
      this.bone.style.left=(g.end+g.size*.02)+'px';this.bone.style.bottom='10px';
      const phase=this.elapsed>=t.total?'resting':clip;
      if(phase!==this.phase){this.phase=phase;this.host.dispatchEvent(new CustomEvent('candi:bone-state',{detail:{state:phase}}));}
      this.host.dispatchEvent(new CustomEvent('candi:bone-frame',{detail:{time:this.elapsed,duration:t.total,clip,frame,x,size:g.size,width:g.width}}));
    }
    async play(){
      if(this.destroyed||this.motion.matches||this.host.clientWidth<1)return;
      this.stop(false);clearTimeout(this.timer);const token=this.token;this.active=true;
      try{await this.load();}catch(error){if(token===this.token)this.wake();throw error;}
      if(this.destroyed||token!==this.token)return;
      this.mascot?.pause();if(this.mascot)this.mascot.sprite.hidden=true;
      this.actor.hidden=false;this.phase='';this.times=this.timing();this.elapsed=0;this.previous=null;this.render(0);
      const tick=now=>{
        if(token!==this.token)return;
        if(!document.hidden){const dt=this.previous===null?0:Math.min(100,now-this.previous);this.previous=now;this.render(this.elapsed+dt);}else this.previous=null;
        if(this.elapsed<this.times.total)this.raf=requestAnimationFrame(tick);
        else{this.raf=null;this.host.dispatchEvent(new CustomEvent('candi:bone-complete'));}
      };this.raf=requestAnimationFrame(tick);
    }
    pause(){this.token++;cancelAnimationFrame(this.raf);this.raf=null;this.previous=null;}
    stop(restore=true){
      this.token++;this.pause();this.active=false;this.actor.hidden=true;this.bone.hidden=true;
      if(restore&&this.mascot){this.mascot.sprite.hidden=false;this.mascot.seek(4800);}
    }
    wake(){
      const wasActive=this.active;this.stop();if(wasActive&&this.mascot&&!this.destroyed)this.mascot.idle().catch(()=>{});
      if(wasActive)this.host.dispatchEvent(new CustomEvent('candi:bone-state',{detail:{state:'awake'}}));
      this.arm();
    }
    destroy(){
      this.destroyed=true;this.enabled=false;clearTimeout(this.timer);this.stop();
      for(const type of ['pointerdown','pointermove','keydown','wheel','input'])this.activityTarget.removeEventListener(type,this.onActivity);
      document.removeEventListener('visibilitychange',this.onVisibility);this.motion.removeEventListener('change',this.onMotion);this.host.removeEventListener('candi:state',this.onMascotState);this.resize.disconnect();this.actor.remove();this.bone.remove();
    }
  }
  window.CandiBoneSequence=CandiBoneSequence;
})();
