/* Luna de cumpleaños · reproductor de los tres atlas de Astra (v1, sep-2026).
 *
 * Los atlas vienen con encuadre irregular: en llegada y celebra la perrita se sale
 * de su celda y en fiesta cada fila tiene el piso a otra altura. En vez de esperar
 * atlas corregidos, cada pose lleva su caja medida (bboxes-v1.json, alfa > 200) y
 * el reproductor la desplaza para que las patas queden siempre en la misma línea.
 * Los WebP v2 salen de limpiar-atlas.py sobre los PNG v1 de Astra: quita de cada celda
 * los pedazos de la perrita vecina (42 fragmentos) y recalcula el piso de cada pose.
 * Si un día Astra entrega atlas alineados, basta con vaciar BB.
 */
(() => {
  const base = new URL('.', document.currentScript.src);
  const CLIPS = {
    llegada: { file: 'luna-cumple-llegada-v2.webp', cols: 5, rows: 4, n: 20, ms: 160 },
    fiesta:  { file: 'luna-cumple-fiesta-v2.webp',  cols: 4, rows: 4, n: 16, ms: 275 },
    celebra: { file: 'luna-cumple-celebra-v2.webp', cols: 6, rows: 4, n: 24, ms: 200 },
  };
  // Borde inferior de la figura en cada pose (fracción de la celda). Medido.
  const BB = {
    llegada: [0.996,0.996,0.996,0.996,0.996,0.961,0.968,0.964,0.975,0.972,0.929,0.932,0.929,0.932,0.936,0.879,0.883,0.89,0.893,0.893],
    fiesta: [0.971,0.971,0.971,0.971,0.946,0.946,0.946,0.946,0.901,0.901,0.901,0.901,0.857,0.857,0.857,0.857],
    celebra: [0.977,0.977,0.977,0.973,0.977,0.973,0.945,0.945,0.949,0.945,0.973,0.965,0.871,0.871,0.875,0.871,0.875,0.879,0.863,0.863,0.863,0.863,0.863,0.863],
  };
  const PISO = .97; // a dónde se llevan las patas

  class LunaCumple {
    constructor(host) {
      this.host = host; this.token = 0; this.state = '';
      this.sprite = document.createElement('div'); this.sprite.className = 'luna-sprite';
      this.sprite.setAttribute('role', 'img'); this.sprite.setAttribute('aria-label', 'Luna con gorro de fiesta');
      host.append(this.sprite);
      this.reduce = matchMedia('(prefers-reduced-motion: reduce)');
      this.loads = {};
      this.ready = this.load('fiesta').then(() => this.paint('fiesta', 0));
    }
    load(name) {
      if (!this.loads[name]) this.loads[name] = new Promise((ok, no) => {
        const im = new Image(); im.onload = () => ok(); im.onerror = () => { delete this.loads[name]; no(new Error('No cargó ' + name)); };
        im.src = new URL(CLIPS[name].file, base).href;
      });
      return this.loads[name];
    }
    paint(name, frame, dx = 0) {
      const c = CLIPS[name], s = this.sprite.style;
      s.backgroundImage = `url("${new URL(c.file, base).href}")`;
      s.backgroundSize = `${c.cols * 100}% ${c.rows * 100}%`;
      s.backgroundPosition = `${(frame % c.cols) * 100 / (c.cols - 1)}% ${Math.floor(frame / c.cols) * 100 / (c.rows - 1)}%`;
      const bajar = (PISO - (BB[name] ? BB[name][frame] : PISO)) * this.sprite.offsetHeight;
      s.transform = `translate(${dx}px, ${bajar.toFixed(1)}px)`;
      // Los atlas v2 ya van sin los fragmentos de las celdas vecinas (limpiar-atlas.py);
      // queda un recorte fino por el antialias del borde.
      s.clipPath = 'inset(1% 2%)';
    }
    emit(state) { if (state !== this.state) { this.state = state; this.host.dispatchEvent(new CustomEvent('luna:state', { detail: { state } })); } }
    stop() { this.token++; cancelAnimationFrame(this.raf); }
    // Corre `frames` (lista de índices) a `ms` por pose; resuelve al terminar. Con `loop` no termina.
    run(name, frames, ms, { loop = false, dx } = {}) {
      this.stop(); const token = this.token; let i = 0, prev = null, acc = 0;
      return new Promise(res => {
        const tick = now => {
          if (token !== this.token) return res(false);
          if (!document.hidden) { if (prev !== null) acc += Math.min(120, now - prev); prev = now; } else prev = null;
          while (acc >= ms) { acc -= ms; i++; }
          if (i >= frames.length) { if (!loop) { this.paint(name, frames[frames.length - 1], dx ? dx(1) : 0); return res(true); } i = 0; }
          this.paint(name, frames[i], dx ? dx(Math.min(1, (i * ms + acc) / (frames.length * ms))) : 0);
          this.raf = requestAnimationFrame(tick);
        };
        this.raf = requestAnimationFrame(tick);
      });
    }
    // Entra trotando desde la derecha (poses 1-10 en bucle mientras se desplaza), frena y saluda (11-20).
    async llegar() {
      await this.ready;
      if (this.reduce.matches) { this.emit('saluda'); return this.reposo(); }
      try { await this.load('llegada'); } catch { return this.reposo(); }
      this.emit('llega');
      const ancho = this.sprite.offsetWidth + 40, tok = this.token + 1;
      const trote = [...Array(10).keys()];
      // 3 s de trote: 2 vueltas y media al ciclo, desplazándose de +ancho a 0.
      const vueltas = 3; const seq = []; for (let k = 0; k < vueltas; k++) seq.push(...trote);
      const t0 = performance.now(), dur = seq.length * CLIPS.llegada.ms;
      const ok = await this.run('llegada', seq, CLIPS.llegada.ms, { dx: p => ancho * (1 - p) });
      if (!ok) return;
      this.emit('saluda');
      await this.run('llegada', [10, 11, 12, 13, 14, 15, 16, 17, 18, 19], CLIPS.llegada.ms);
      await new Promise(r => setTimeout(r, 900));
      return this.reposo();
    }
    // Sentada, cola en bucle (1-8); cada 3-4 vueltas sopla el espanta suegras (9-16).
    async reposo() {
      await this.ready; this.stop(); this.emit('fiesta');
      const tok = this.token;
      for (;;) {
        const vueltas = 3 + Math.floor(Math.random() * 2);
        for (let k = 0; k < vueltas; k++) { if (!await this.run('fiesta', [0,1,2,3,4,5,6,7], 275)) return; if (tok !== this.token) return; }
        if (this.reduce.matches) continue;
        if (!await this.run('fiesta', [8,9,10,11,12,13,14,15], 200)) return;
      }
    }
    // Mete el tarjetón en la urna, salta y vuelve al reposo.
    async celebrar() {
      await this.ready;
      if (this.reduce.matches) return;
      try { await this.load('celebra'); } catch { return; }
      this.emit('celebra');
      const ok = await this.run('celebra', [...Array(24).keys()], 200);
      if (ok) return this.reposo();
    }
    destroy() { this.stop(); this.sprite.remove(); }
  }
  window.LunaCumple = LunaCumple;
})();
