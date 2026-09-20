/* Candi v2: atlas de 20 poses; sin dependencias ni llamadas al modelo. */
(() => {
  /* WebP, no el PNG: el mismo atlas pesa 561 KB en vez de 2,0 MB y se baja en
     CADA carga de candidato-360 (el botón de Candi usa su pose final). Medido a
     tamaño de pantalla, la diferencia contra el PNG es de 3,8/255 por píxel:
     invisible. El PNG queda en la carpeta como fuente; para regenerarlo:
     cwebp -q 90 -alpha_q 100 -m 6 candi-saludo-atlas-v2-20.png -o candi-saludo-atlas-v2-20.webp */
  const atlas = new URL('candi-saludo-atlas-v2-20.webp', document.currentScript.src).href;
  class CandiSaludo {
    constructor(host) {
      this.host = host;
      this.sprite = document.createElement('div');
      this.sprite.className = 'candi-sprite';
      this.sprite.setAttribute('role', 'img');
      this.sprite.setAttribute('aria-label', 'Candi, una perrita, saluda levantando la pata');
      this.sprite.style.backgroundImage = `url("${atlas}")`;
      host.append(this.sprite);
      this.motion = matchMedia('(prefers-reduced-motion: reduce)');
      this.onVisibility = () => { this.previous = null; };
      document.addEventListener('visibilitychange', this.onVisibility);
      this.ready = new Promise((resolve, reject) => {
        const image = new Image(); image.onload = resolve;
        image.onerror = () => reject(new Error('No se pudo cargar el atlas de Candi.'));
        image.src = atlas;
      });
      this.seek(3200);
    }
    seek(ms) {
      this.time = Math.max(0, Math.min(3200, ms));
      const t = this.time;
      const steps = [[1120,8],[1240,9],[1380,10],[1530,11],[1700,12],[1840,13],[1980,14],[2140,15],[2340,16],[2540,17],[2740,18],[2960,19]];
      let frame = t < 1120 ? Math.min(7, Math.floor(t / 140)) : 19;
      for (const [at, index] of steps) if (t >= at) frame = index;
      // El atlas generado desplaza las filas inferiores: compensar el recorte
      // para conservar las cabezas completas sin modificar la imagen original.
      const rowY = [0, 280.5, 550, 813];
      const cell = 1402 / 5;
      this.sprite.style.backgroundPosition = `${(frame % 5) * 25}% ${rowY[Math.floor(frame / 5)] / (1122 - cell) * 100}%`;
      const distance = this.sprite.offsetWidth + 32;
      // Desacelerar durante los dos apoyos de frenada, sin deslizar al saludar.
      const progress = Math.min(t / 1380, 1);
      const travel = progress < .8 ? progress : .8 + .2 * (1 - Math.pow((1 - progress) / .2, 2));
      this.sprite.style.transform = `translateX(${distance * (1 - travel)}px)`;
      this.host.dispatchEvent(new CustomEvent('candi:frame', {detail:{time:t,frame}}));
    }
    async play({speed = 1} = {}) {
      this.pause();
      const run = this.run;
      await this.ready;
      if (run !== this.run) return;
      if (this.motion.matches) { this.seek(3200); this.host.dispatchEvent(new CustomEvent('candi:complete')); return; }
      this.seek(0); this.previous = null;
      const tick = now => {
        if (run !== this.run) return;
        if (!document.hidden) {
          const dt = this.previous === null ? 0 : Math.min(now - this.previous, 80);
          this.seek(this.time + dt * Math.max(.1, speed));
          this.previous = now;
        } else this.previous = null;
        if (this.time < 3200) this.raf = requestAnimationFrame(tick);
        else { this.raf = null; this.host.dispatchEvent(new CustomEvent('candi:complete')); }
      };
      this.raf = requestAnimationFrame(tick);
    }
    pause() { this.run = (this.run || 0) + 1; cancelAnimationFrame(this.raf); this.raf = null; }
    destroy() { this.pause(); document.removeEventListener('visibilitychange', this.onVisibility); this.sprite.remove(); }
  }
  window.CandiSaludo = CandiSaludo;
})();
