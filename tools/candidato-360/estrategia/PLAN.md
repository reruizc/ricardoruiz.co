# Estrategia · dentro de `candidato-360.html` (plan de trabajo)

Estado: **fases 1 y 2 construidas** (19-oct-2026): banco, motor, prueba, tarjeta 11 y vista ampliada con Posicionamiento y Territorio. Faltan la redacción (fase 3) y los formatos (fase 4). Bitácora en `candidato-360.md` §11, «Módulo 11 · Estrategia». Sale de la primera consultoría
hecha a mano para un concejal de Bogotá: el documento se armó juntando piezas que
Candidato 360 ya tiene (historial, arquetipos, territorio, escucha, contendientes)
más un banco de literatura. Este módulo lo vuelve repetible para cualquier
candidatura.

Tarjeta **11** del CRM. ⚠️ **Decisión de Ricardo (19-oct-2026): todo vive DENTRO
de `candidato-360.html`**, al cargar la candidatura. No hay página aparte: la
tarjeta se despliega en una vista ampliada dentro del mismo CRM, con lo que ya
tiene cargado el vínculo (historial, territorio, arquetipos). El motor va en
`candidato-360-estrategia.js` (`window.C360Estrategia`, sin DOM), con el mismo
patrón de motor compartido del endoso (08), el Día D (09) y los contendientes
(10): la tarjeta y la vista ampliada leen el mismo cálculo y no pueden dar
cifras distintas.

Responde cuatro preguntas, en este orden:

1. **¿Qué lugar ocupa?** El posicionamiento: temas propios y personaje.
2. **¿Dónde y con quién?** El territorio, arquetipo por arquetipo: dónde retener,
   dónde hacerse conocer, dónde tomar posición y dónde movilizar.
3. **¿Qué hace este mes?** Las acciones de la fase en curso, con sus
   principios y referencias.
4. **¿Qué formato usa esta semana?** Los formatos de moda que le sirven, ya
   filtrados por su registro y con fecha de vencimiento.

---

## 1. Las reglas (heredadas de §3 de `candidato-360.md`)

- **Nada que insinúe quién votó por quién.** El territorio se describe por el
  censo y el comportamiento de los barrios donde están sus votos.
- **Cada recomendación dice de dónde sale:** un principio del banco, con su
  referencia, o «criterio de oficio», rotulado como tal.
- **No es un predictor.** Ofrece escenarios, nunca «usted gana».
- **La redacción con IA no inventa:** solo puede citar fichas del banco, y el
  servidor descarta las que no existan (mismo patrón que `/c360/escucha/lectura`).

## 2. Insumos

**Los que ya existen en el CRM**

| Insumo | De dónde sale | Para qué |
|---|---|---|
| Historial y votos por puesto | Índices de `cand-index.js` | Base propia, dispersión, «figura o barrio» (`arraigo` de los arquetipos de Bogotá) |
| Territorio y meta | Vínculo (`campana`) y `vote-target.js` | Escala y cifra repartidora proyectada |
| Arquetipos y afinidad | Panel 05 (`C360ArqLectura.afinidad`) | Peso de cada principio y tabla de territorio |
| Perfil del votante | Panel 06 | Audiencias transversales (edad, sexo) |
| Contendientes | Panel 10 | Competencia dentro de la lista y vecinos de espectro |
| Escucha | Capturas (`capturar.mjs`) | Si los temas propios ya tienen dueño, el sentimiento, los formatos que suben |

**Los que pide al candidato** (un cuestionario corto, como el de la escucha)

- **Registro**, en tres ejes:
  - tono, de 1 a 5: solemne, serio, cercano, humorístico, irreverente;
  - generación;
  - personaje: autoridad, gestor, vecino, retador o denunciante.
- **Temas propios:** hasta 3 candidatos, y la página le muestra cuánto pesa cada
  uno en la conversación de su territorio.
- **Vehículo:** partido, tipo de lista (abierta o cerrada) y renglón.
- **Flancos que conoce:** texto libre. Ejemplos: un voto polémico, la asistencia.

## 3. El banco · `candidato-360-data/estrategia-banco.json`

Sale del banco hecho a mano, que es literatura pública y puede vivir en el repo.
Los nombres de candidatos reales no van ahí.

```jsonc
{ "v": "2026-10-19",
  "principios": [ { "id": "A5", "texto": "La movilización rinde más que la persuasión…", "fichas": ["T13","T14","T15","T16"] } ],
  "fichas": [ { "id": "T13", "ref": "Green y Gerber 2019…", "doi": "…", "tipo": "evidencia|oficio",
                "lectura": "leido|resumen|ficha", "idea": "…",
                "modula": { "PRO": "…", "PVP": "central: ya lo prefiere, no sale" } } ],
  "ramas": [ { "id": "R2", "nace_de": ["T13"], "arquetipos": ["PVP"], "fichas": ["R2.1","R2.2"] } ],
  "matriz": { "PVP": { "A5": 2, "A7": -1, "A8": -1 } }   // 2 central · 1 útil · 0 igual · -1 riesgo
}
```

⚠️ La «modulación por arquetipo» y la matriz son hipótesis del equipo, no
hallazgos de los autores. La página lo dice.

⚠️ Los arquetipos llevan un código por ciudad. Hay 5 emocionales de referencia,
los 6 de Concejo de Bogotá y los 8 de Cartagena. La matriz necesita una fila por
cada arquetipo de cada ciudad que entre al módulo. Arranca con los 6 de Bogotá y
los 5 emocionales.

## 4. El motor (determinista, sin modelo)

1. **Fase**, según la fecha y el calendario electoral (posicionamiento,
   precampaña, campaña, Día D). El calendario es un JSON que se actualiza cuando
   la Registraduría expida la resolución.
2. **Peso de cada principio** = Σ sobre los arquetipos de *(peso del arquetipo
   en su votación × afinidad acotada)* × la celda de la matriz. El resultado es
   un orden de los 8 principios para esta candidatura, con las fichas que lo
   sostienen.
3. **Tabla de territorio:** cada arquetipo cae en un cuadrante según su
   **afinidad** y su **peso en la ciudad**.

   | | Arquetipo grande | Arquetipo chico |
   |---|---|---|
   | **Afinidad alta** | retener | retener y crecer |
   | **Afinidad baja** | hacerse conocer, o movilizar si es de baja participación | no gastar ahí |

   Debajo van los barrios fuertes y los huecos de cada uno (el mismo cálculo que
   ya hace el panel 05).
4. **Figura o barrio:** con el arraigo medido (`arraigo_barrio` de los
   arquetipos de Bogotá), la estrategia se inclina a reputación de ciudad (A1,
   A7) o a trabajo de barrio (R3).
5. **Competencia en la lista:** los rivales de la misma lista que salen en el
   panel 10. En lista abierta, el rival principal está adentro.

Pruebas en `prueba-estrategia.mjs`, con dos casos: un concejal «figura» de
Bogotá y una edilesa de barrio. Se fijan el orden de los principios y la tabla
de territorio.

## 5. La redacción · `POST /c360/estrategia/redactar` (worker `rr-auth`)

- El navegador manda el esqueleto del motor: fase, principios ordenados, tabla
  de territorio, temas, registro, vehículo y flancos.
- El worker pide a DeepSeek el texto por fase: qué hacer este mes, mensajes por
  arquetipo y respuesta a flancos.
- **Cada párrafo cita ids de fichas**, y el servidor descarta los ids
  inexistentes.
- Sesión y acceso de C360. Cupo diario por cuenta, caché de 24 h y
  `C360_ESTR_PROMPT_V`.
- Se pide a mano (botón «Redactar»), no al cargar.

## 6. Los formatos de moda (capa B)

- **Registro:** `c360:formatos:<ciudad>` en KV, una ficha por formato con los
  campos de la plantilla B3 del banco: red, principio al que sirve, fechas de
  detección y de vencimiento, evidencia de que es tendencia, registro requerido y
  riesgos.
- **De dónde salen:** la capa 1 de la escucha (hashtags y videos que suben en
  TikTok e Instagram del territorio) propone candidatos, y una revisión humana
  semanal los aprueba. **Sin aprobación no se muestran.**
- **Filtro por candidato:** pasa solo si el tono del formato queda a un punto
  del suyo, si no le pide parecer de otra edad y si no contradice su personaje.
  Si no pasa, sale «con ajuste» (la versión en su registro) o no sale.
- **Vencimiento:** lo vencido se archiva, no se borra. El briefing de cada 3
  días trae «formatos de la semana compatibles con usted».

## 7. Lo que muestra

- **Tarjeta 11:** el lugar que ocupa (una frase), los 3 principios que más pesan
  y la acción de la semana.
- **Vista ampliada dentro de `candidato-360.html`** (no página aparte): cuatro
  pestañas (Posicionamiento · Territorio · Plan por fase · Formatos) y
  exportación a `.md` y `.pdf`.
- **Vitrina sin cuenta:** el esqueleto del motor sin redacción ni formatos.

## 8. Fases de construcción

1. Banco en JSON + motor + `prueba-estrategia.mjs`.
2. Tarjeta 11 y vista ampliada en `candidato-360.html`, con las pestañas Posicionamiento y Territorio.
3. Ruta de redacción en el worker y pestaña Plan por fase.
4. Capa de formatos: KV, revisión semanal y filtro, y su bloque en el briefing.
5. Los 12 arquetipos de «principal con ascendente» como insumo, cuando estén
   medidos y estables.

## 9. Lo que se aprendió del caso de referencia (sep-oct 2026)

- **Un concejal con poca base de barrio (arraigo de 7 %, la ciudad está en
  12-13 %) es una figura de ciudad.** Su estrategia es reputación, no feudos.
  El motor tiene que leer el arraigo antes de recomendar trabajo de barrio.
- **Su mayor afinidad no siempre está donde pesa más.** La «ciudadela
  movilizada» era el 5,6 % de la ciudad y su índice más alto (×1,76). El hueco
  real estaba en el arquetipo más grande («clase media de nombre», 41 %, ×0,88).
  La tabla de territorio necesita los dos ejes, peso y afinidad.
- **El contexto institucional cambia la estrategia** (comisión, votaciones
  polémicas, personería del partido, dominio web vencido) y no sale de los
  datos electorales. Por eso el cuestionario pregunta los flancos, y la
  redacción los trata primero (sesgo de negatividad, Soroka 2014).
