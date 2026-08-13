// Pruebas del parser de notificaciones bancarias.
//
//   node tools/gastos/prueba-parser.mjs
//
// El .mjs importa desde rr-auth/src (fuera de este repo) a propósito: se prueba
// EL archivo que se despliega, no una copia que se desincroniza.
// Al aparecer un formato nuevo de banco, se agrega el caso acá primero.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// El worker declara "type":"commonjs" en su package.json, así que node se niega
// a leer su .js como ESM. Se copia a un .mjs temporal para probar EL archivo
// que se despliega, sin tocar la configuración del worker.
const FUENTE = path.resolve(import.meta.dirname, '../../../rr-auth/src/gastos-parser.js');
const tmp = path.join(os.tmpdir(), `gastos-parser-${process.pid}.mjs`);
fs.copyFileSync(FUENTE, tmp);
process.on('exit', () => { try { fs.unlinkSync(tmp); } catch {} });
const { parsear } = await import('file://' + tmp);
const C = [
 // [mensaje, esperaOk, monto, tipo, banco, comercioContiene]
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
 // Los que NO deben entrar
 ["Bancolombia: tu clave dinamica es 483920. No compartas este codigo.", false],
 ["Nu: tu codigo de verificacion es 112233", false],
 ["Bancolombia: Compra por $99.000 en AMAZON fue rechazada por fondos insuficientes", false],
 ["Nequi: Tu saldo actual es $340.000", false],
 ["Bancolombia: tu pago minimo de $150.000 tiene fecha de pago 15/09/2026", false],
 ["Hola, nos vemos manana", false],
];
let mal=0;
for (const [msg, ok, monto, tipo, banco, com] of C) {
  const r = parsear(msg);
  let bien = r.ok === ok;
  let det = "";
  if (r.ok) {
    const m = r.mov;
    det = `$${m.monto} ${m.tipo}/${m.banco} · "${m.comercio}" · ${m.categoria} · ${m.confianza}`;
    if (ok) {
      if (m.monto !== monto) { bien=false; det += `  ← monto esperado ${monto}`; }
      if (m.tipo !== tipo)   { bien=false; det += `  ← tipo esperado ${tipo}`; }
      if (m.banco !== banco) { bien=false; det += `  ← banco esperado ${banco}`; }
      if (com && !m.comercio.toUpperCase().includes(com.toUpperCase())) { bien=false; det += `  ← comercio esperado ${com}`; }
    }
  } else det = `rechazado: ${r.motivo}`;
  if(!bien) mal++;
  console.log(`${bien?"ok   ":"FALLA"} ${msg.slice(0,54).padEnd(56)} ${det}`);
}
console.log(mal ? `\n${mal} de ${C.length} FALLAN` : `\nlos ${C.length} casos pasan`);
process.exit(mal ? 1 : 0);
