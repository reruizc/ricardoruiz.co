#!/usr/bin/env node
/**
 * Backfill de role/org/consent para usuarios pre-cambio del formulario.
 *
 * Uso:
 *   node tools/backfill-users-role-consent.js              # dry-run
 *   node tools/backfill-users-role-consent.js --apply      # escribe a KV
 *
 * Qué hace:
 *   - Lista todos los `users:*` del KV `RR_STORE`.
 *   - Salta cuentas de test/temporales (set EXCLUDE_TEST).
 *   - Salta usuarios que YA tienen el campo `role` (idempotente).
 *   - Para el resto agrega: role="unknown", org="", tycAcceptedAt=createdAt,
 *     tycVersion="pre-form-implicit" (distinto de "1581-2012-v1" para que
 *     siempre podamos distinguir consent explícito vs retroactivo).
 *   - Preserva todos los demás campos sin tocar.
 *
 * Notas legales:
 *   El formulario viejo ya tenía la línea "Al registrarte aceptas los
 *   Términos de uso y la Política de privacidad" — por eso marcamos
 *   tycAcceptedAt con la fecha de registro original (consent implícito).
 *   El tycVersion distinto deja claro en auditoría que NO fue el checkbox
 *   explícito del formulario nuevo.
 *
 * Sin dependencias externas — usa wrangler vía child_process.
 */

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const NAMESPACE_ID = 'beb24dcb24c74a7399af71870a165c83';
const BATCH = 100; // límite de la API de Cloudflare

const EXCLUDE_TEST = new Set([
  // yopmail
  'bigpayload@yopmail.com', 'bigpayload99@yopmail.com',
  'cmdi1@yopmail.com', 'cmdi2@yopmail.com',
  'massassign_test1@yopmail.com', 'massassign_test2@yopmail.com',
  'massassign_test3@yopmail.com', 'massassign_test4@yopmail.com',
  'ssti1@yopmail.com', 'ssti2@yopmail.com', 'ssti3@yopmail.com',
  'xss_stored1@yopmail.com', 'xss_stored2@yopmail.com',
  // dummies
  'test@test.com', 'pepito@gmail.com',
  // mails temporales
  'cewen70702@izkat.com', 'winoye2791@marvetos.com',
  // typo (no es un email válido)
  'galvisdego@g,mail.com',
]);

// Cuentas internas del dueño — opcional, las marcamos como consultor
// porque sí sabemos qué hacen.
const INTERNAL_AS_CONSULTOR = new Set([
  'reruizc@gmail.com', 'reruizc@unal.edu.co',
  'nuevagemela@gmail.com', 'jdl2018@ricardoruiz.co',
]);

const APPLY = process.argv.includes('--apply');

function wrangler(args, opts = {}) {
  const r = spawnSync('wrangler', args, { encoding: 'utf8', ...opts });
  if (r.status !== 0) {
    process.stderr.write(r.stderr || '');
    throw new Error(`wrangler ${args[0]} ${args[1] || ''} → exit ${r.status}`);
  }
  return r.stdout;
}

// La salida de bulk get viene como JSON + línea "Success!" al final.
function parseBulkGetOutput(txt) {
  return JSON.parse(txt.replace(/\nSuccess!\s*$/m, '').trim());
}

function listAllUserKeys() {
  const raw = wrangler(['kv', 'key', 'list',
    '--namespace-id', NAMESPACE_ID,
    '--prefix', 'users:',
    '--remote',
  ]);
  return JSON.parse(raw).map(k => k.name);
}

function bulkGet(keys) {
  const tmp = path.join(os.tmpdir(), `bf-${Date.now()}-${Math.random()}.json`);
  fs.writeFileSync(tmp, JSON.stringify(keys));
  try {
    const out = wrangler([
      'kv', 'bulk', 'get',
      '--namespace-id', NAMESPACE_ID,
      '--remote',
      tmp,
    ]);
    return parseBulkGetOutput(out);
  } finally { fs.unlinkSync(tmp); }
}

function bulkPut(records) {
  const payload = records.map(({ key, value }) => ({ key, value }));
  const tmp = path.join(os.tmpdir(), `bf-put-${Date.now()}-${Math.random()}.json`);
  fs.writeFileSync(tmp, JSON.stringify(payload));
  try {
    const out = wrangler([
      'kv', 'bulk', 'put',
      '--namespace-id', NAMESPACE_ID,
      '--remote',
      tmp,
    ]);
    process.stdout.write(out);
  } finally { fs.unlinkSync(tmp); }
}

// ─── main ────────────────────────────────────────────────────────────────────
(async function main() {
  console.log(`\n${APPLY ? '🚀 APPLY MODE' : '🔍 DRY-RUN'} — backfill role/org/consent\n`);

  const keys = listAllUserKeys();
  console.log(`Total registros users:* en KV: ${keys.length}`);

  // bulk get en lotes de 100
  const records = {};
  for (let i = 0; i < keys.length; i += BATCH) {
    Object.assign(records, bulkGet(keys.slice(i, i + BATCH)));
  }

  const toUpdate = [];
  const skipped = { hasRole: 0, test: 0, parseErr: 0 };

  for (const [key, valStr] of Object.entries(records)) {
    const email = key.replace(/^users:/, '');
    if (EXCLUDE_TEST.has(email)) { skipped.test++; continue; }

    let u;
    try { u = JSON.parse(valStr); }
    catch { skipped.parseErr++; console.log(`  ⚠️  parse error: ${email}`); continue; }

    if (u.role !== undefined) { skipped.hasRole++; continue; }

    const role = INTERNAL_AS_CONSULTOR.has(email) ? 'consultor' : 'unknown';
    const next = {
      ...u,
      role,
      org: typeof u.org === 'string' ? u.org : '',
      tycAcceptedAt: u.tycAcceptedAt || u.createdAt || Date.now(),
      tycVersion: u.tycVersion || 'pre-form-implicit',
    };
    toUpdate.push({ key, value: JSON.stringify(next), email, role });
  }

  console.log(`\nA tocar:      ${toUpdate.length}`);
  console.log(`  → unknown:    ${toUpdate.filter(r => r.role === 'unknown').length}`);
  console.log(`  → consultor:  ${toUpdate.filter(r => r.role === 'consultor').length}`);
  console.log(`Saltados:`);
  console.log(`  already ok:  ${skipped.hasRole}  (ya tienen role)`);
  console.log(`  test:        ${skipped.test}    (cuentas de prueba)`);
  console.log(`  parse err:   ${skipped.parseErr}`);

  if (!APPLY) {
    console.log(`\nEjemplo de los primeros 5 que cambiarían:`);
    toUpdate.slice(0, 5).forEach(r => {
      console.log(`  ${r.email}  →  role=${r.role}`);
    });
    console.log(`\nDry-run. Para escribir corré:\n  node ${path.basename(__filename)} --apply\n`);
    return;
  }

  // APPLY
  console.log(`\nEscribiendo en lotes de ${BATCH}...`);
  for (let i = 0; i < toUpdate.length; i += BATCH) {
    const lote = toUpdate.slice(i, i + BATCH);
    console.log(`  lote ${i / BATCH + 1}: ${lote.length} registros`);
    bulkPut(lote);
  }
  console.log(`\n✅ Backfill completado: ${toUpdate.length} usuarios actualizados.\n`);
})().catch(e => { console.error(e); process.exit(1); });
