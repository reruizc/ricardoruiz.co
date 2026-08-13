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
const { parsear } = await import('file://' + tmp);

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
          + correr(REALES, "mensajes REALES (85540)")
          + correrSubstrings();

const total = SINTETICOS.length + REALES.length + 4;
console.log(mal ? `\n${mal} de ${total} FALLAN` : `\nlos ${total} casos pasan`);
process.exit(mal ? 1 : 0);
