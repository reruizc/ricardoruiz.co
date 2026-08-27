/* Browser data client. It never contains AWS credentials or signs S3 requests. */
(function (global) {
  'use strict';
  const cfg = global.RR_PLATFORM_CONFIG;
  if (!cfg) throw new Error('Load platform-config.js before data-client.js');
  function path(value) {
    const clean = String(value || '').replace(/^\/+/, '');
    if (!clean || clean.split('/').includes('..')) throw new Error('Invalid data path');
    return clean;
  }
  function publicUrl(value) { return `${cfg.publicDataBase}/${path(value)}`; }
  function apiUrl(value) { return `${cfg.apiBase}/${path(value)}`; }
  async function privateFetch(resource, options) {
    const response = await fetch(apiUrl(resource), Object.assign({
      credentials: 'include', headers: { Accept: 'application/json' },
    }, options || {}));
    if (!response.ok) throw new Error(`Private API: HTTP ${response.status}`);
    return response;
  }
  global.RRData = Object.freeze({ publicUrl, apiUrl, privateFetch });
})(window);
