# Ruta `/geo` para el worker `rr-auth`

Cloudflare entrega geolocalización gratis a cualquier Worker via
`request.cf.{city, region, country, latitude, longitude, postalCode, timezone}`.
Sólo hay que exponerla como un endpoint público con CORS abierto.

## Pasos

1. Abre el dashboard de Cloudflare → Workers & Pages → `rr-auth` → **Edit code**.
2. Pega el handler de abajo dentro del router del worker, **antes** de
   cualquier handler que devuelva 404. Si tu worker usa `export default { fetch }`,
   añade el bloque dentro del `fetch(request, env, ctx)`.
3. **Save & Deploy**.
4. Verifica con `curl https://rr-auth.reruizc.workers.dev/geo` — debe
   devolver un JSON con tu ciudad, lat, lon.

## Snippet a pegar

```js
// ─── /geo ───────────────────────────────────────────────────────────────
// Devuelve la geolocalización aproximada del cliente (ciudad + lat/lon)
// usando los headers que Cloudflare añade automáticamente. Sin costo.
// CORS abierto para que el test (incluso embebido en otros sitios) pueda
// llamarlo desde el browser.
if (url.pathname === '/geo') {
  // Preflight CORS
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin':  '*',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Access-Control-Allow-Headers': 'content-type',
        'Access-Control-Max-Age':       '86400',
      },
    });
  }
  if (request.method !== 'GET') {
    return new Response('Method Not Allowed', { status: 405 });
  }
  const cf = request.cf || {};
  const body = {
    city:        cf.city        || null,
    region:      cf.region      || null,   // ej: "Cundinamarca"
    regionCode:  cf.regionCode  || null,   // ej: "CUN"
    country:     cf.country     || null,   // ej: "CO"
    lat:         cf.latitude    ? Number(cf.latitude)  : null,
    lon:         cf.longitude   ? Number(cf.longitude) : null,
    postal:      cf.postalCode  || null,
    timezone:    cf.timezone    || null,
    asn:         cf.asn         || null,   // útil para detectar VPN/datacenter
    asOrg:       cf.asOrganization || null,
  };
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      'Content-Type':                'application/json; charset=utf-8',
      'Cache-Control':               'no-store',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
```

## Notas

- **Precisión**: ciudad y lat/lon a nivel ciudad (centroide aproximado).
  Para Bogotá, Medellín, Cali, Barranquilla y municipios grandes funciona
  bien; en municipios pequeños puede caer al centroide del depto.
- **VPN / datacenter**: si `asOrg` contiene "Cloudflare", "AWS", "Google",
  "Microsoft", "Digital Ocean", probablemente es VPN/proxy y la geo no
  representa al usuario real. El frontend puede mostrar un fallback.
- **Privacidad**: no se loguea ni se persiste nada en el worker. La IP
  nunca sale del request.
- **Costo**: $0. Cloudflare ya entrega estos campos en cualquier request.
