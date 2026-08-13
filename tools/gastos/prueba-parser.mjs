// Pruebas del parser de notificaciones bancarias.
//
//   node tools/gastos/prueba-parser.mjs
//
// Prueba EL archivo que se despliega (rr-auth/src/gastos-parser.js), no una
// copia que se desincroniza. Al aparecer un formato nuevo de banco, el caso se
// agrega ACÁ primero y solo después se toca el parser.
//
// Los casos marcados REAL son mensajes textuales que llegaron al teléfono de
// Ricardo. Son la vara: si uno de esos se rompe, el parser está mal.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// El worker declara "type":"commonjs" en su package.json, así que node se niega
// a leer su .js como ESM. Se copia a un .mjs temporal para probar el archivo
// real sin tocar la configuración del worker.
const FUENTE = path.resolve(import.meta.dirname, '../../../rr-auth/src/gastos-parser.js');
const tmp = path.join(os.tmpdir(), `gastos-parser-${process.pid}.mjs`);
fs.copyFileSync(FUENTE, tmp);
process.on('exit', () => { try { fs.unlinkSync(tmp); } catch {} });
const { parsear, partirMensajes } = await import('file://' + tmp);

const TITULAR = 'Ricardo Esteban Ruiz Castro';

// [mensaje, esperaOk, monto, tipo, banco, comercioContiene]
const SINTETICOS = [
  ["Bancolombia le informa Compra por $52.900 en RAPPI COLOMBIA 15:22. T.Cred *1234", true, 52900, "gasto","bancolombia","RAPPI"],
  ["Bancolombia: Compraste $35.000 en EXITO POBLADO desde tu cuenta *4321", true, 35000,"gasto","bancolombia","EXITO"],
  ["Nequi: Enviaste $50.000 a JUAN PEREZ. Te queda $120.000", true, 50000,"gasto","nequi","JUAN"],
  ["Nequi: Pagaste $15.900 en NETFLIX. Saldo: $84.100", true, 15900,"gasto","nequi","NETFLIX"],
  ["Lulo Bank: Compra aprobada por $128.500 en HOMECENTER CALLE 80", true,128500,"gasto","lulo","HOMECENTER"],
  ["Nu: Compra aprobada de $23.400 en UBER TRIP. Cupo disponible $2.000.000", true, 23400,"gasto","nubank","UBER"],
  ["Bancolombia le informa Retiro por $400.000 en CAJERO EXITO 09/08/2026", true,400000,"gasto","bancolombia",""],
  ["Davivienda: Pago por $1.234.567,89 en DIAN aprobado", true,1234567.89,"gasto","davivienda","DIAN"],
  ["Bancolombia: Te consignaron $8.500.000 de DNP NOMINA en tu cuenta *1234", true,8500000,"ingreso","bancolombia",""],
  ["Nequi: Recibiste $200.000 de MARIA LOPEZ", true,200000,"ingreso","nequi",""],
  ["Bancolombia le informa Compra por $89.900 en D1 y su saldo disponible es $450.000", true,89900,"gasto","bancolombia","D1"],
  ["COP 75000 pagados en TERPEL con tu tarjeta Lulo Bank", true,75000,"gasto","lulo","TERPEL"],
  // No deben entrar
  ["Bancolombia: tu clave dinamica es 483920. No compartas este codigo.", false],
  ["Nu: tu codigo de verificacion es 112233", false],
  ["Bancolombia: Compra por $99.000 en AMAZON fue rechazada por fondos insuficientes", false],
  ["Nequi: Tu saldo actual es $340.000", false],
  ["Bancolombia: tu pago minimo de $150.000 tiene fecha de pago 15/09/2026", false],
  ["Hola, nos vemos manana", false],
];

// REALES · textuales del 85540 (Bancolombia, ago-2026)
const REALES = [
  ["Bancolombia: Compraste COP12.533,00 en CARULLA GALERIAS con tu T.Cred *1519, el 11/08/2026 a las 21:14. Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.",
   true, 12533, "gasto", "bancolombia", "CARULLA GALERIAS"],
  // El `* REFERENCIA` que pega la red de tarjetas no debe quedar en el nombre.
  ["Bancolombia: Compraste COP116.925,04 en APIFY* INVÑ202608120, el 11/08/2026 a las 19:11. Esta compra esta asociada a T.Cred *1519. Si tienes dudas, encuentranos aqui: 01800931987. Siempre contigo.",
   true, 116925.04, "gasto", "bancolombia", "APIFY"],
  // En un ingreso la contraparte va tras "de", no tras "en" (que apunta a TU cuenta).
  ["Bancolombia: Recibiste un pago PROVEEDOR de WOMPI S.A.S. por $13,693.98 en tu cuenta de Ahorros el 11/08/2026 a las 11:46. Si tienes dudas, llamanos al 018000931987. A tu lado siempre.",
   true, 13693.98, "ingreso", "bancolombia", "WOMPI"],
  // Transferencia a uno mismo: NO es ingreso, es traslado entre bolsillos propios.
  ["Bancolombia: Ricardo, recibiste una transferencia de RICARDO ESTEBAN RUIZ CASTRO por $215,000.00 en tu cuenta *0583 conectada a la llave reruizc@gmail.com el 09/08/26 a las 22:06. Con llaves es de una y gratis. Dudas al 018000912345",
   true, 215000, "traslado", "bancolombia", "RICARDO ESTEBAN"],
];


// REALES · 85784 (tarjeta de crédito Bancolombia) y 890789 (Lulo), ago-2026
const REALES_2 = [
  // Pagar la tarjeta NO es un gasto nuevo: cubre compras ya contadas.
  ["Bancolombia: Pagaste $600,000 en la tarjeta de credito *1519 desde la cuenta *0583, el 02/08/2026 14:16. ¿Dudas? Llamanos al 018000912345. Estamos cerca.",
   true, 600000, "traslado", "bancolombia", "Pago tarjeta *1519"],
  ["Bancolombia: Pagaste $2,000,000 en la tarjeta de credito *1519 desde la cuenta *0583, el 01/08/2026 16:36. ¿Dudas? Llamanos al 018000912345. Estamos cerca.",
   true, 2000000, "traslado", "bancolombia", "Pago tarjeta *1519"],
  // procesador * COMERCIO → queda lo de después
  ["Bancolombia: Compraste COP16.872,00 en PAYU*UBER con tu T.Cred *1519, el 19/06/2026 a las 14:00. Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.",
   true, 16872, "gasto", "bancolombia", "UBER"],
  ["Bancolombia: Compraste COP200.382,00 en EMILIA GRACE con tu T.Cred *1519, el 19/06/2026 a las 16:08. Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.",
   true, 200382, "gasto", "bancolombia", "EMILIA GRACE"],
  ["Lulo Bank: Realizaste una compra recurrente por $41,900.00 con tu tarjeta • 1603 en DLO*GOOGLE YouTubePrem. Fecha 29 de julio de 2026. Hora 11:23 a.m.",
   true, 41900, "gasto", "lulo", "GOOGLE YouTubePrem"],
  ["Lulo Bank: Realizaste una compra recurrente por $3,049.00 con tu tarjeta • 1603 en GOOGLE *Workspace_rica. Fecha 1 de agosto de 2026. Hora 8:17 a.m.",
   true, 3049, "gasto", "lulo", "GOOGLE Workspace_rica"],
  // El # de referencia no puede llevarse el nombre del comercio por delante.
  ["Lulo Bank: Realizaste una compra recurrente por $113,771.40 con tu tarjeta • 1603 en DNH*GODADDY#4088755116. Fecha 14 de mayo de 2026. Hora 8:47 p.m.",
   true, 113771.40, "gasto", "lulo", "GODADDY"],
];

// Las tres compras recurrentes de Lulo deben quedar marcadas como gasto fijo.
function correrRecurrentes() {
  console.log(`\n── marca de gasto recurrente ──`);
  let mal = 0;
  for (const [msg, , , , , com] of REALES_2) {
    const esperado = /recurrente/i.test(msg);
    const r = parsear(msg, { titular: TITULAR });
    const tiene = !!(r.ok && r.mov.recurrente);
    const bien = tiene === esperado;
    if (!bien) mal++;
    console.log(`${bien ? "ok   " : "FALLA"} ${String(com).padEnd(24)} recurrente=${tiene}${bien ? "" : `  ← esperado ${esperado}`}`);
  }
  return mal;
}


// La fecha del mensaje manda sobre la de llegada. Sin esto, importar el
// historial metería veinte mensajes viejos en el día de la importación.
function correrFechas() {
  console.log(`\n── fecha leída del mensaje ──`);
  const fmt = ts => { const d = new Date(ts - 5*3600000);
    return `${String(d.getUTCDate()).padStart(2,'0')}/${String(d.getUTCMonth()+1).padStart(2,'0')}/${d.getUTCFullYear()} ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`; };
  const casos = [
    [REALES[0][0],   "11/08/2026 21:14", "dd/mm/aaaa con 'a las'"],
    [REALES_2[0][0], "02/08/2026 14:16", "dd/mm/aaaa sin 'a las'"],
    [REALES[3][0],   "09/08/2026 22:06", "año de dos dígitos"],
    [REALES_2[4][0], "29/07/2026 11:23", "'29 de julio de 2026' + a.m."],
    [REALES_2[6][0], "14/05/2026 20:47", "p.m. → 24 h"],
    ["Nequi: Pagaste $15.900 en NETFLIX. Saldo: $84.100", null, "sin fecha → hora de llegada"],
  ];
  let mal = 0;
  for (const [msg, esp, que] of casos) {
    const r = parsear(msg, { titular: TITULAR });
    const leyo = r.ok && r.mov.fecha_fuente === "mensaje";
    const got = leyo ? fmt(r.mov.ts) : null;
    const bien = got === esp;
    if (!bien) mal++;
    console.log(`${bien ? "ok   " : "FALLA"} ${que.padEnd(30)} ${got || "(llegada)"}${bien ? "" : "  ← esperado " + (esp || "(llegada)")}`);
  }
  return mal;
}

// Un pegado con varios SMS se parte por el nombre del banco, no por salto de
// línea: un solo mensaje ocupa varias líneas (Lulo pone la fecha aparte).
function correrPartir() {
  console.log(`\n── partir un pegado en mensajes ──`);
  const pegado = [REALES[0][0], REALES[1][0], "", REALES_2[0][0],
    "Lulo Bank: Realizaste una compra recurrente por $113,771.40 con tu tarjeta • 1603 en DNH*GODADDY#4088755116.\nFecha 14 de mayo de 2026. Hora 8:47 p.m.",
    REALES[2][0], "Bancolombia: tu clave dinamica es 483920. No compartas este codigo."].join("\n");
  const piezas = partirMensajes(pegado);
  const movs = piezas.map(x => parsear(x, { titular: TITULAR })).filter(r => r.ok);
  const pruebas = [
    ["parte en 6 piezas", piezas.length === 6, piezas.length],
    ["5 son movimientos", movs.length === 5, movs.length],
    ["la clave se descarta", movs.every(r => !/clave/i.test(r.mov.crudo)), true],
    ["Lulo de 2 líneas se une", movs.some(r => r.mov.comercio === "GODADDY"), true],
    ["cada uno con su fecha", new Set(movs.map(r => new Date(r.mov.ts).toDateString())).size >= 3, true],
  ];
  let mal = 0;
  for (const [que, ok, val] of pruebas) {
    if (!ok) mal++;
    console.log(`${ok ? "ok   " : "FALLA"} ${que.padEnd(30)} ${val}`);
  }
  return mal;
}

function correr(casos, etiqueta) {
  console.log(`\n── ${etiqueta} ──`);
  let mal = 0;
  for (const [msg, ok, monto, tipo, banco, com] of casos) {
    const r = parsear(msg, { titular: TITULAR });
    let bien = r.ok === ok;
    let det = "";
    if (r.ok) {
      const m = r.mov;
      det = `$${m.monto} ${m.tipo}/${m.banco} · "${m.comercio}" · ${m.categoria} · ${m.confianza}`;
      if (ok) {
        if (m.monto !== monto) { bien = false; det += `  ← monto esperado ${monto}`; }
        if (m.tipo !== tipo)   { bien = false; det += `  ← tipo esperado ${tipo}`; }
        if (m.banco !== banco) { bien = false; det += `  ← banco esperado ${banco}`; }
        if (com && !m.comercio.toUpperCase().includes(com.toUpperCase())) {
          bien = false; det += `  ← comercio esperado ${com}`;
        }
      }
    } else det = `rechazado: ${r.motivo}`;
    if (!bien) mal++;
    console.log(`${bien ? "ok   " : "FALLA"} ${msg.slice(0, 52).padEnd(54)} ${det}`);
  }
  return mal;
}

// Falsos positivos por substring: la trampa que ya costó `tigo` dentro de
// "Siempre contigo" y `ara` dentro de "compra para ti".
function correrSubstrings() {
  console.log(`\n── el diccionario no debe casar dentro de otra palabra ──`);
  const trampas = [
    ["Bancolombia: Compraste $10.000 en LA TIENDA. Siempre contigo.", "servicios", "contigo→tigo"],
    ["Bancolombia: Compraste $10.000 en LA TIENDA para ti", "mercado", "para→ara"],
    ["Bancolombia: Compra por $10.000 en LA TIENDA, transaccion exitosa", "mercado", "exitosa→exito"],
    ["Bancolombia: Compraste $10.000 en TRAMITE gubernamental", "transporte", "gubernamental→uber"],
  ];
  let mal = 0;
  for (const [msg, catProhibida, porque] of trampas) {
    const r = parsear(msg, { titular: TITULAR });
    const cat = r.ok ? r.mov.categoria : "(rechazado)";
    const bien = cat !== catProhibida;
    if (!bien) mal++;
    console.log(`${bien ? "ok   " : "FALLA"} ${porque.padEnd(24)} categoría=${cat}${bien ? "" : `  ← NO debe ser ${catProhibida}`}`);
  }
  return mal;
}

const mal = correr(SINTETICOS, "casos sintéticos")
          + correr(REALES, "mensajes REALES (85540 · débito e ingresos)")
          + correr(REALES_2, "mensajes REALES (85784 tarjeta · 890789 Lulo)")
          + correrSubstrings()
          + correrRecurrentes()
          + correrFechas()
          + correrPartir();

const total = SINTETICOS.length + REALES.length + REALES_2.length + 4 + REALES_2.length + 6 + 5;
console.log(mal ? `\n${mal} de ${total} FALLAN` : `\nlos ${total} casos pasan`);
process.exit(mal ? 1 : 0);
