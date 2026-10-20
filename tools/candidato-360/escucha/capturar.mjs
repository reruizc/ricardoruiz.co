/* capturar.mjs — una lectura de escucha social, de punta a punta.
   ------------------------------------------------------------------
   Es el motor que hay detrás de «Lo que se publica en sus cuentas» en
   candidato-360-escucha.html. Toma el vínculo, arma el perfil (perfil.mjs),
   raspa las dos capas con Apify (apify.mjs), clasifica postura, tema y tono
   con el modelo y escribe UNA captura con el contrato que consume el panel
   (README · «Contrato · GET /c360/captura»).

   Es el ensayo A MANO: sin --gastar solo dice qué haría. La lectura en sí vive
   en captura.mjs y la comparte recolectar.mjs, que la corre sola cada día para
   las cuentas con el módulo de escucha (oct-2026).

   Uso:
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json              # ensayo
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json --gastar --salida=captura.json
     node tools/candidato-360/escucha/capturar.mjs --vinculo=v.json --gastar --sin-modelo   # raspa, no clasifica

   Reglas que sostienen esto:
   · Cero resultados NO es «no hay conversación»: sale como `sin_datos` con
     motivo, nunca como cero conversación.
   · La postura es del modelo y el modelo se equivoca con el sarcasmo: cada
     cifra va con sus citas, para que el candidato lea y corrija.
   · Los comentarios no son la localidad: son quienes comentan. El panel lo
     dice; acá se guarda la muestra para que lo pueda decir.                  */

import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarVinculo } from './perfil.mjs';
import { AYUDA_TOKEN } from './apify.mjs';
import { capturar, planDe, llaveModelo, tokenApify } from './captura.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const m = a.match(/^--([^=]+)=(.*)$/); return m ? [m[1], m[2]] : [a.replace(/^--/, ''), true]; }));
const GASTAR = Boolean(args.gastar), SIN_MODELO = Boolean(args['sin-modelo']);
const TOPE = args.tope ? Number(args.tope) : null;
const { vinculo, ruta: rutaVinculo, esEjemplo } = cargarVinculo(args);
const { PERFIL, filasPosts, filasCom } = planDe(vinculo, args);

console.log(`\n═══ CAPTURA · ${PERFIL.candidato} ═══`);
console.log(esEjemplo ? `Vínculo de EJEMPLO (${path.relative(process.cwd(), rutaVinculo)})` : `Vínculo: ${path.relative(process.cwd(), rutaVinculo)}`);
console.log(`Temas: ${PERFIL.temas.map(t => `«${t}»`).join(' · ') || '—'}   Escalas: ${PERFIL.escalas.join(' y ')}`);
for (const f of filasPosts) console.log(`  ${f.etiqueta.padEnd(10)} ${f.motivo ? '— ' + f.motivo : `${f.consultas.length} consultas × ${TOPE ?? f.tope} + comentarios de ${filasCom.find(c => c.red === f.red)?.posts || 0} posts`}`);

if (!GASTAR) { console.log(`\nEnsayo: no se llamó a Apify ni al modelo. Con --gastar se produce la captura completa.\n`); process.exit(0); }

const token = await tokenApify(); if (!token) { console.error('\n' + AYUDA_TOKEN + '\n'); process.exit(1); }
const llave = SIN_MODELO ? null : await llaveModelo();
if (!SIN_MODELO && !llave) { console.error('\nFalta DEEPSEEK_API_KEY (en el entorno o en .env). Para raspar sin clasificar: --sin-modelo\n'); process.exit(1); }

const captura = await capturar(vinculo, { token, llave, sinModelo: SIN_MODELO, tope: TOPE, overrides: args });
const salida = args.salida ? path.resolve(String(args.salida)) : path.join(AQUI, 'captura.json');
await writeFile(salida, JSON.stringify(captura, null, 2));
console.log(`\nCaptura escrita en ${path.relative(process.cwd(), salida)} · Apify $${captura.costo.apifyUsd.toFixed(4)} · modelo $${captura.costo.modeloUsd.toFixed(4)}\n`);
