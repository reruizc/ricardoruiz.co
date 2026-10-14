/* ── Rayado para los barrios sin puesto de votación propio ──────────────────
   Un barrio sin puesto no tiene votos ni censo propios: quienes viven ahí votan
   en puestos de barrios vecinos. Antes se pintaba con el color del vecino más
   cercano, punteado y translúcido, y cuando ese vecino tenía 0 votos el barrio
   quedaba casi blanco, como si fuera un cero suyo. El rayado dice otra cosa:
   «aquí no se vota, mire el barrio de al lado». Las rayas llevan el color del
   vecino; si el vecino no tiene valor, van en gris.

   Leaflet (renderer SVG) escribe `fillColor` tal cual en el atributo `fill`
   del path, así que basta con pasarle `url(#patron)`. Los patrones viven en un
   <svg> propio de 0×0 pegado al body —sin `display:none`, que en algunos
   navegadores apaga los patrones— y se crean uno por color, a demanda.

   Lo usan el mapa de barrios del CRM (candidato-360.js) y el del perfil del
   votante (candidato-360-electorado.html). */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const GRIS = '#8a96a3';
  let defs = null;
  const hechos = new Map();
  function asegurarDefs() {
    if (defs && defs.isConnected) return defs;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.setAttribute('aria-hidden', 'true');
    svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none';
    defs = document.createElementNS(NS, 'defs');
    svg.append(defs); document.body.append(svg);
    hechos.clear();
    return defs;
  }
  /* `color` vacío o nulo = el vecino no tiene valor: rayas grises. */
  function franja(color) {
    const c = String(color || GRIS);
    let id = hechos.get(c);
    if (id && document.getElementById(id)) return `url(#${id})`;
    id = 'c360-franja-' + hechos.size;
    const p = document.createElementNS(NS, 'pattern');
    p.setAttribute('id', id);
    p.setAttribute('patternUnits', 'userSpaceOnUse');
    p.setAttribute('width', '6'); p.setAttribute('height', '6');
    p.setAttribute('patternTransform', 'rotate(45)');
    const raya = document.createElementNS(NS, 'rect');
    raya.setAttribute('width', '2.5'); raya.setAttribute('height', '6'); raya.setAttribute('fill', c);
    p.append(raya);
    asegurarDefs().append(p);
    hechos.set(c, id);
    return `url(#${id})`;
  }
  /* «564 m» o «1,4 km», para los globos y las fichas. */
  function distancia(km) {
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1).replace('.', ',')} km`;
  }
  window.C360Franjas = { franja, distancia, GRIS };
})();
