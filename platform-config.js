/* Public browser configuration: domains and paths only, never credentials. */
(function (global) {
  'use strict';
  const runtime = global.RR_RUNTIME_CONFIG || {};
  const trimSlash = value => String(value || '').replace(/\/+$/, '');
  // La ruta /public-data aún no está desplegada en el hosting estático. Hasta
  // tener el proxy/CloudFront operativo se usa el prefijo público existente;
  // las fuentes privadas siguen pasando únicamente por apiBase.
  const publicDataOrigin = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co';
  const defaultPublicDataBase = publicDataOrigin;
  global.RR_PLATFORM_CONFIG = Object.freeze({
    // Un despliegue puede reemplazarlo por el proxy público sin tocar las páginas.
    publicDataBase: trimSlash(runtime.publicDataBase || defaultPublicDataBase),
    // Private data is authorized server-side through this API origin.
    apiBase: trimSlash(runtime.apiBase || '/api'),
  });
})(window);
