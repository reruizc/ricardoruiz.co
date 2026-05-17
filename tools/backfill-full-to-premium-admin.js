#!/usr/bin/env node
/**
 * Backfill: plan 'full' → 'premium' + role 'admin' para reruizc@gmail.com.
 *
 * Uso:
 *   node tools/backfill-full-to-premium-admin.js              # dry-run
 *   node tools/backfill-full-to-premium-admin.js --apply      # escribe a KV
 *
 * Qué hace:
 *   - Lista users:* de RR_STORE.
 *   - Para todo usuario con plan === 'full' → plan = 'premium' (conserva
 *     billingCycle, planExpiresAt, planLinkId, lastTxId — solo cambia el
 *     label del plan; downloads pasan de 999 a 10/mes, ver dashboard).
 *   - Para reruizc@gmail.com → role = 'admin' (independiente del plan).
 *   - Idempotente: si ya está migrado lo salta.
 *
 * Sin dependencias externas — wrangler vía child_process.
 */

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const NAMESPACE_ID = 'beb24dcb24c74a7399af71870a165c83';
const BATCH = 100;
const ADMIN_EMAIL = 'reruizc@gmail.com';

const APPLY = process.argv.includes('--apply');

function wrangler(args) {
  const r = spawnSync('wrangler', args, { encoding: 'utf8' });
  if (r.status !== 0) {
    process.stderr.write(r.stderr || '');
    throw new Error(`wrangler ${args.slice(0, 2).join(' ')} → exit ${r.status}`);
  }
  return r.stdout;
}

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

(async function main() {
  console.log(`\n${APPLY ? '🚀 APPLY MODE' : '🔍 DRY-RUN'} — full→premium + admin role\n`);

  const keys = listAllUserKeys();
  console.log(`Total registros users:* en KV: ${keys.length}`);

  const records = {};
  for (let i = 0; i < keys.length; i += BATCH) {
    Object.assign(records, bulkGet(keys.slice(i, i + BATCH)));
  }

  const toUpdate = [];
  const stats = { fullToPremium: 0, adminSet: 0, skipped: 0, parseErr: 0 };

  for (const [key, valStr] of Object.entries(records)) {
    const email = key.replace(/^users:/, '');

    let u;
    try { u = JSON.parse(valStr); }
    catch { stats.parseErr++; console.log(`  ⚠️  parse error: ${email}`); continue; }

    let changed = false;
    const next = { ...u };

    if (u.plan === 'full') {
      next.plan = 'premium';
      next.planUpdatedAt = Date.now();
      changed = true;
      stats.fullToPremium++;
    }

    if (email === ADMIN_EMAIL && u.role !== 'admin') {
      next.role = 'admin';
      changed = true;
      stats.adminSet++;
    }

    if (changed) {
      const ops = [];
      if (u.plan === 'full') ops.push(`plan: full→premium`);
      if (email === ADMIN_EMAIL && u.role !== 'admin') ops.push(`role: ${u.role || '∅'}→admin`);
      toUpdate.push({ key, value: JSON.stringify(next), email, ops: ops.join(' · ') });
    } else {
      stats.skipped++;
    }
  }

  console.log(`\nA tocar:        ${toUpdate.length}`);
  console.log(`  full→premium:  ${stats.fullToPremium}`);
  console.log(`  admin role:    ${stats.adminSet}`);
  console.log(`Saltados:        ${stats.skipped}  (sin cambios)`);
  console.log(`Parse errors:    ${stats.parseErr}`);

  if (toUpdate.length) {
    console.log(`\nDetalle:`);
    toUpdate.forEach(r => console.log(`  ${r.email.padEnd(40)}  ${r.ops}`));
  }

  if (!APPLY) {
    console.log(`\nDry-run. Para escribir:\n  node ${path.basename(__filename)} --apply\n`);
    return;
  }

  if (!toUpdate.length) {
    console.log(`\n✅ Nada que migrar. Todo está al día.\n`);
    return;
  }

  console.log(`\nEscribiendo en lotes de ${BATCH}...`);
  for (let i = 0; i < toUpdate.length; i += BATCH) {
    const lote = toUpdate.slice(i, i + BATCH);
    console.log(`  lote ${i / BATCH + 1}: ${lote.length} registros`);
    bulkPut(lote);
  }
  console.log(`\n✅ Migración completada: ${toUpdate.length} usuarios actualizados.\n`);
})().catch(e => { console.error(e); process.exit(1); });
