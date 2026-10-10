/* Enlaces de pago de Wompi por plan y facturación. Única fuente para
   pricing.html y login.html, para que no vuelvan a divergir.
   OJO: cada enlace de aquí debe existir también en LINK_PLAN_MAP del worker
   rr-auth. Si un enlace no está en ese mapa, el webhook responde
   unknown_link_id y el pago NO activa el plan. Al rotar un enlace, cámbialo
   primero en el worker y después aquí. */
(function (global) {
  'use strict';
  global.RR_WOMPI_LINKS = Object.freeze({
    pro:     Object.freeze({ mensual: 'https://checkout.wompi.co/l/Ds08zS', anual: 'https://checkout.wompi.co/l/2Kdoxx' }),
    premium: Object.freeze({ mensual: 'https://checkout.wompi.co/l/E1ZVCn', anual: 'https://checkout.wompi.co/l/XWAdkz' }),
  });
})(window);
