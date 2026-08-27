/* Public browser configuration: domains and paths only, never credentials. */
(function (global) {
  'use strict';
  const runtime = global.RR_RUNTIME_CONFIG || {};
  const trimSlash = value => String(value || '').replace(/\/+$/, '');
  // Abrir un HTML directamente desde Finder no tiene servidor que resuelva
  // /public-data. Este origen es solo para la vista local mientras la base
  // electoral histórica siga siendo pública; producción siempre usa el proxy.
  const localPreviewDataBase = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co';
  const defaultPublicDataBase = location.protocol === 'file:' ? localPreviewDataBase : '/public-data';
  global.RR_PLATFORM_CONFIG = Object.freeze({
    // CloudFront publishes only prefixes that have been approved as public.
    publicDataBase: trimSlash(runtime.publicDataBase || defaultPublicDataBase),
    // Private data is authorized server-side through this API origin.
    apiBase: trimSlash(runtime.apiBase || '/api'),
  });
})(window);
