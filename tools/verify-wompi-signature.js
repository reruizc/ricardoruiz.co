#!/usr/bin/env node
/**
 * Verifica el fix del webhook de Wompi sin depender de un reintento.
 *
 * Uso:
 *   WOMPI_EVENTS_KEY=tu_secreto node tools/verify-wompi-signature.js
 *
 * Reproduce los dos caminos (viejo y nuevo) sobre el payload real del
 * webhook de Álvaro (tx 1401350-1778880430-88083) y compara contra el
 * checksum que reportó Wompi. El fix es correcto si el path NUEVO
 * matchea y el VIEJO no.
 */

const crypto = require('crypto');

const KEY = process.env.WOMPI_EVENTS_KEY;
if (!KEY) {
  console.error('Falta WOMPI_EVENTS_KEY. Uso:');
  console.error('  WOMPI_EVENTS_KEY=tu_secreto node tools/verify-wompi-signature.js');
  console.error('\nEl secreto lo configuraste en wrangler en su día. Lo encontrás:');
  console.error('  - En el dashboard de Cloudflare → Workers → rr-auth → Settings → Variables');
  console.error('    (no muestra el valor pero confirma que existe)');
  console.error('  - En el dashboard de Wompi → Integraciones → "Eventos" → "Llave secreta"');
  process.exit(1);
}

// Payload real tal como llegó del webhook fallido de Álvaro
const body = {
  data: {
    transaction: {
      id: '1401350-1778880430-88083',
      status: 'APPROVED',
      amount_in_cents: 12490000,
      // ...el resto de campos no afectan la firma
    },
  },
  signature: {
    checksum: '6b74b225012cef0a51b3e33bb824150f654af94d3c5190c26bbc3fb1e5a1f3f7',
    properties: ['transaction.id', 'transaction.status', 'transaction.amount_in_cents'],
  },
  timestamp: 1778893109,
};

function computeHash(body, startFrom) {
  let toHash = '';
  for (const prop of body.signature.properties) {
    const parts = prop.split('.');
    let val = startFrom;
    for (const p of parts) val = val?.[p];
    toHash += String(val ?? '');
  }
  toHash += body.timestamp;
  toHash += KEY;
  return { input: toHash, hash: crypto.createHash('sha256').update(toHash).digest('hex') };
}

const expected = body.signature.checksum;
const oldWay = computeHash(body, body);      // VIEJO: val = body
const newWay = computeHash(body, body.data); // NUEVO: val = body.data

console.log('\nWompi checksum esperado:');
console.log(' ', expected);
console.log('\n── Lógica VIEJA (let val = body) ──');
console.log('  input: "' + oldWay.input.replace(KEY, '<KEY>') + '"');
console.log('  hash:  ' + oldWay.hash);
console.log('  ' + (oldWay.hash === expected ? '✓ matchea' : '✗ NO matchea (esperado: estaba roto)'));

console.log('\n── Lógica NUEVA (let val = body.data) ──');
console.log('  input: "' + newWay.input.replace(KEY, '<KEY>') + '"');
console.log('  hash:  ' + newWay.hash);
console.log('  ' + (newWay.hash === expected ? '✓ matchea — fix correcto' : '✗ NO matchea — algo sigue mal'));

const ok = newWay.hash === expected && oldWay.hash !== expected;
console.log('\n' + (ok ? '✅ Fix validado.' : '⚠️  Revisar — no cuadra.'));
process.exit(ok ? 0 : 1);
