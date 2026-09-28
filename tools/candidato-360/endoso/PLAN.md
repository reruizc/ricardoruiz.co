# Endoso de aliados · `candidato-360-endoso.html` — plan de trabajo

Panel propio del módulo 08 del CRM (hoy es un modal dentro de `candidato-360.js`,
sección «9 bis», commit `58d60118`). Pasa a ser un panel como el 06 (electorado) y
el 09 (Día D): HTML propio + motor compartido, con la regla de siempre: **la tarjeta
del CRM y el panel llaman la MISMA función**, no pueden dar cifras distintas.

## Lo que ya existe (y se conserva)

- Buscador de aliados sobre `CandRegistry.acRank` (439k candidaturas 2010-2026).
- Recorte al territorio de campaña por código electoral (`mesaEnAlcance`).
- Tasa medida con el par aliado → a quién apoyó: `Σ min(A, B) / Σ A`, por mesa si
  es la misma jornada y por puesto si son años distintos. Descarta el mismo
  tarjetón y el par saturado (el apoyado lo supera en ≥95 % de sus mesas).
- Sin medición: mediana de los medidos → si no hay, supuesto 30 % rotulado.
- Solape con el voto propio (parte del endoso puede ser voto que ya tiene).
- Aliados en `localStorage['c360-aliados:<correo>:<candidatura>']`.

## Lo que está mal o falta

1. **Σ min es una cota superior**, no una tasa: mide cuánto electorado pudieron
   compartir. Y el supuesto de 30 % no sale de ningún dato.
2. **Los aliados se suman**: dos líderes del mismo barrio se cuentan dos veces.
3. **No proyecta a 2027** (crecimiento del electorado por corporación).
4. **No existe el líder de zona sin candidatura propia** (presidente de JAC,
   pastor, líder comunal): es el caso más común en territoriales y hoy no entra.
5. El endoso no se cruza con la meta ni con el Día D.

## Las dos fórmulas

### A · Excandidato (tiene votación propia en el registro)

```
endoso_i = votos del aliado en el territorio × retención × tasa_i × crecimiento_2027
```

- **retención**: cuánto de su propio voto conserva una candidatura de una elección
  a la siguiente, medido sobre el registro con la MISMA persona en dos elecciones
  (`agruparPersonas`), por tipo de salto (JAL→Concejo, Concejo→Concejo…) y años de
  distancia. Es el techo empírico: un aliado no puede pasar más de lo que él mismo
  retiene. Reusa la infraestructura de `tools/candidato-360/saltos/estudio.mjs`.
- **tasa**: tres lecturas, de más a menos exigente:
  1. *Regresión ecológica por puesto* (share del apoyado en t+1 contra share del
     aliado en t, ponderada por censo) → pendiente = tasa de transferencia, con
     intervalo. Necesita válidos por puesto (ver D1).
  2. *Σ min* (lo de hoy) → pasa a ser el **techo** del rango, no la cifra.
  3. Sin par medido → mediana de la calibración de retención del tipo de salto,
     no un 30 % fijo.
- Se publica como **rango: piso · probable · techo**, nunca una cifra sola.

### B · Líder de zona (sin candidatura propia)

El usuario marca la zona en el mapa (puestos, barrios o comuna) y dice a quién
apoyó el líder en qué elección. Se mide el **sobre-rendimiento** del apoyado ahí:

```
efecto = votos del apoyado en la zona − esperado sin el líder
esperado = share del apoyado en los puestos comparables fuera de la zona
           (misma comuna / vecinos) × válidos de la zona
endoso_líder = max(0, efecto) × retención × crecimiento_2027
```

Variante diferencia-en-diferencias cuando hay dato de dos elecciones: cambio del
apoyado (o de su partido) en la zona menos el cambio fuera de ella.
Sin elección de referencia: el usuario escribe «maneja N votos» → queda rotulado
como declarado y se contrasta con la zona (N contra votantes reales de esos
puestos; aviso si N supera un % razonable).

### Combinación de aliados · sin doble conteo

Por puesto, unión probabilística en vez de suma:
`E_puesto = V · (1 − Π (1 − e_i / V))`, con `V` = votantes esperados del puesto
(censo 2026 × participación de la corporación). Dos aliados del mismo barrio
suman menos que por separado; dos de barrios distintos suman casi completo.

## Datos que faltan

- **D1 · Válidos (y partidos) por puesto por elección.** Los JSON de candidato
  solo traen SUS votos, sin denominador. Hoy hay denominador para Concejo/JAL 2023
  en 11 ciudades (detalle por comuna) y Asamblea 2023 (detalle por municipio).
  Builder nuevo `build_totales_puesto.py` desde los GCS: un JSON liviano por
  elección × municipio `{puesto: {validos, votantes, partidos}}`.
  Prioridad: 2023 y 2019 territoriales, Congreso 2022/2026.
- **D2 · Censo por puesto** para el tope de la unión: HVP 2026 (ya en S3) y los
  censos 2018-2026 de la Registraduría (solo locales; son agregados, se pueden
  subir).
- **D3 · Calibración de retención** → `endoso-calibracion.json` (KB), mediana y
  cuartiles por tipo de salto y años de distancia.

## Fases

| # | Qué | Sale |
|---|---|---|
| 1 ✅ | Extraer el motor a `candidato-360-endoso.js` (`window.C360Endoso`), sin cambiar cifras. La tarjeta 08 lo usa. Prueba en Node con JSON reales (`prueba-endoso.mjs`). | **hecho 27-sep-2026** |
| 2 ✅ | Panel `candidato-360-endoso.html` con los excandidatos: ficha por aliado, mapa de sus votos en el territorio, tasa con su método, total. La tarjeta 08 pasa a enlace (como 06 y 09); se retira el modal. | **hecho 27-sep-2026** |
| 3 ✅ | D3 calibración de retención → reemplaza el 30 %. Rango piso/probable/techo. Crecimiento 2027 (decidido no sumarlo, ver bitácora). | **hecho 27-sep-2026** |
| 4 ✅ | D1 totales por puesto (2023 primero) → regresión ecológica en la fórmula A. | **hecho 28-sep-2026** |
| 5 ✅ | Unión probabilística por puesto + mapa combinado + matriz de solape entre aliados. | **hecho 28-sep-2026** |
| 6 ✅ | Líder de zona: selector de zona en el mapa, sobre-rendimiento, «maneja N votos» contrastado (DiD queda pendiente, ver bitácora). | **hecho 28-sep-2026** |
| 7 | Integración: % de la meta por escalón, puestos donde el endoso cierra la brecha → Día D, CSV, entrada en `VISTAS` de Candi + `C360_CANDI_VISTAS` del worker, `candidato-360.md`. | cierre |

## Bitácora

**Fase 1 (27-sep-2026).** El motor vive en `candidato-360-endoso.js`, sin DOM ni
CRM: el recorte al territorio (`enAlcance`), el nombre del área (`areaDe`) y el
voto propio (`propio`) se le pasan desde afuera. En `candidato-360.js` quedaron
solo `endosoAlcance`, `endosoLugar`, `endosoArea` y la UI del modal.
Verificado contra el código anterior (sacado de `HEAD`) con 7 aliados reales de
Bogotá: salida idéntica campo por campo (total 135.894 de 207.208). Esas cifras
quedaron fijadas en `tools/candidato-360/prueba-endoso.mjs` (`--sin-red` corre
solo los casos sintéticos).

Cosas vistas al pasar, sin tocar (cambiarían cifras, van a la fase 3):
- La «mediana» con un número par de medidas toma la MENOR de las dos del medio
  (`floor((n−1)/2)`), no el promedio.
- En «Dónde se concentra» aparecen áreas tipo «Puesto 11-00» con pocos votos:
  mesas sin comuna que caen al nombre del puesto.

**Fase 2 (27-sep-2026).** Panel `candidato-360-endoso.html`: búsqueda sobre el
índice completo (439.015 candidaturas, con las de su departamento primero),
fichas por aliado con la tasa y su método, total contra la meta guardada en
`campana.meta`, mapa de puestos (tamaño = endoso, color = aliado que más pesa;
se encuadra sobre el 95 % del endoso) y desglose por localidad/comuna/municipio.
La tarjeta 08 pasa a enlace y el modal se retiró.

El motor ganó lo que el panel necesitaba sin el CRM: `alcanceDe` (el territorio
desde la campaña guardada, con el municipio por **código electoral** vía
`C360Electorado.codigoMunicipio`), `enAlcance` (puerto de `mesaEnAlcance`),
`areaDe`, `porPuesto` y `candidaturaId`. El CRM ahora resuelve el territorio con
`alcanceDe` cuando el formulario no lo tiene, lo que corrige dos cosas de paso:
la candidatura nueva buscaba el municipio por NOMBRE (el formulario escribe
«Cartagena de Indias» y la Registraduría «CARTAGENA») y la ruta «otra
corporación» sin formulario caía a su votación anterior en vez de a la campaña.

⚠️ `enAlcance` duplica `mesaEnAlcance` a propósito (el panel no carga el CRM).
`prueba-endoso.mjs` extrae la del CRM y las compara en 24 casos sintéticos y
26.801 mesas reales: si alguien cambia una sin la otra, falla.

Verificado en el navegador con dos campañas: Concejo de Bogotá por «la misma
corporación» (cifras idénticas a la prueba) y JAL de Suba por «otra
corporación» (el concejal Briceño baja de 49.894 a sus 11.237 votos en Suba).
Sin desborde a 375 px. Candi tiene la vista `endoso` en el frontend; en el
worker (`C360_CANDI_VISTAS`) está escrita pero **sin desplegar**.

**Fase 3 (27-sep-2026).** El 30 % supuesto se reemplazó por la **retención**:
cuánto de su propio voto conserva, puesto por puesto, la misma persona que se
relanza a la misma corporación 4, 8 o 12 años después
(`tools/candidato-360/endoso/calibrar.mjs`, ~9.800 personas 2011-2023 y
Congreso 2014-2022, 400 pares por corporación y par de años). Si la persona
creció, su segunda votación se escala al tamaño de la primera antes de comparar:
sin eso la suma de mínimos se saturaba (alcaldía daba 99 %) y medía el mérito de
su campaña, que no se transfiere. El script reescribe el bloque RETENCION del
motor entre sus marcas: no se edita a mano.

| Mediana (p25–p75) | 4 años | 8 años | 12 años |
|---|---|---|---|
| JAL | 66 % (31–83) | 52 % (9–77) | 38 % (0–69) |
| Concejo | 71 % (47–87) | 65 % (36–86) | 56 % (26–79) |
| Alcaldía | 89 % (66–96) | 74 % (37–92) | 68 % (23–90) |
| Asamblea | 56 % (43–66) | 46 % (33–57) | 38 % (22–49) |
| Cámara | 58 % (43–68) | 49 % (33–57) | — |
| Senado | 27 % (13–48) | 14 % (9–31) | — |

Cómo entra: con par medido, `min(tasa medida, retención)` en p25 · mediana ·
p75; sin par, la retención sola; con tasa escrita, esa sin rango. La
corporación propia solo si tiene ≥ 20 casos a ±2 años de la distancia del
aliado a 2027; si no, la de todas juntas (presidencia, consultas, gobernación a
12 años). La mediana de las tasas medidas ahora promedia las dos del medio y ya
no se aplica a los aliados sin medir.

Tres límites que el panel declara: (1) quien repite suele ser a quien le fue
bien, así que la retención es generosa —un techo, no un promedio—; (2) en
alcaldía el voto cubre todo el municipio y su mapa casi no cambia, así que ahí
el techo es flojo; (3) no se suma el crecimiento del censo a 2027 porque la
retención ya se midió con el electorado de cada año. Por departamento (Concejo,
4 años) no hay anomalías: Atlántico da 73 %, así que el cambio de códigos de
puesto de Barranquilla no se nota en el agregado.

Caso de control (Bogotá, 3 aliados, medido con los dos motores): pasa de «hasta 46.247» a «entre 25.529 y
52.598, punto medio 42.118».

⚠️ El commit `602e3a46` de otra sesión se llevó una versión intermedia del
motor y del calibrador (tabla vacía): entre ese commit y el de la fase 3, los
aliados sin medir usaron el 30 % y no la mediana. Sin efecto después.

**Fase 4 (28-sep-2026).** Dos piezas:

1. **Totales por puesto** (`tools/candidato-360/endoso/build_totales_puesto.py`):
   `[válidos, votantes, blanco]` por puesto para las 26 elecciones con
   candidaturas en el registro — territoriales 2011 · 2015 · 2019 · 2023 (JAL,
   Concejo, Alcaldía, Asamblea, Gobernación) y Senado/Cámara 2014 · 2018 · 2022.
   Una pasada por GCS, ~2 minutos todo. En S3 comprimidos en
   `congreso-2026/output/totales-puesto/{corp}-{año}.json` (~100 KB cada uno).
   Validado: (a) 96 candidaturas de 8 elecciones, 36.000 puestos: todos casan con
   su total y ninguno supera los válidos; (b) Concejo de Bogotá 2023 = 2.806.148
   válidos, y 2.806.148 − 368.831 de blanco = 2.437.317, la cifra de la meta.
   ⚠️ Esa cifra de la meta NO incluye el blanco; por ley sí es válido. Por eso el
   archivo trae el blanco aparte. Los tres archivos que escriben distinto el texto
   (2011, 2015 y JAL 2019) usan los mismos códigos 996/997/998.
2. **Regresión ecológica** en el motor (`regresion`): participación del apoyado
   contra la del aliado, puesto por puesto, ponderada por los válidos del
   apoyado; α + β es qué parte de los votantes del aliado votó por el apoyado y α,
   la del resto. El universo son los puestos donde LOS DOS estaban en el tarjetón
   (JAL: la zona). Se descarta con menos de 20 puestos, fuera de [−5 %, 105 %] o
   con error mayor a ± 29 puntos. Entra al rango así: centro = min(τ, retención
   mediana), piso = min(τ − 1,96 errores, retención p25), techo = min(Σ min,
   retención p75); Σ min queda solo como techo.

Controles con datos reales: la misma persona (concejal de Bogotá 2019 → 2023)
da 60 % ± 7,5, coherente con la retención de la fase 3; Galán 2019 → 2023 da
123 % y se descarta (con candidatos grandes y parejos en toda la ciudad la
regresión no separa). Un edil de Suba 2023 → un concejal: 42,5 % (Σ min decía
68 %). Un concejal → Galán: Σ min estaba saturado y no medía; la regresión da
38 %, contra 49 % del resto de Bogotá: sus votantes se inclinaron MENOS por Galán
que el resto, y el panel lo avisa. Caso de control de 6 aliados: el punto medio
baja de 137.205 a 116.819.

Pendiente de esta línea: Congreso 2026 (la fuente `endoso`) y presidenciales no
tienen totales por puesto todavía; sus pares siguen con Σ min + retención.

**Fase 5 (28-sep-2026).** Los aliados ya no se suman: en cada puesto se combinan
`V · (1 − Π (1 − e_i / V))`, con V = los válidos 2023 de la corporación de la
campaña (`corpCampana`, que el CRM y el panel sacan de la campaña guardada; el
archivo es el mismo `totales-puesto/` de la fase 4). Se aplica a los tres niveles
del rango; el mapa y «dónde se concentra» salen de la unión, con la parte de cada
aliado en proporción. `solapes()` da, para cada par, qué parte de los votos del
más chico cae en puestos del otro (Σ min ÷ min de los dos totales).

⚠️ **Lo que se midió y hay que tener presente:** la unión con votantes
independientes corrige POCO — en el caso de control de 6 aliados de Bogotá,
1.488 votos de 116.819 (1,3 %) — porque cada aliado aporta poco frente a los
3.000-5.000 válidos de un puesto. La geografía, en cambio, se pisa mucho: los dos
ediles de Suba 2023 coinciden en un 94 %. Si los aliados son de la misma
corriente sus votantes son en buena parte los mismos y el solape real es mucho
mayor que el de la unión. Por eso la lectura trae `siSeRepiten` —si en cada
puesto los votantes fueran los mismos, solo cuenta el aliado más fuerte— y el
panel dice los dos extremos juntos (4 aliados: sumados 47.286, unión 46.913, si
se repiten 36.851). No se endureció la fórmula a ciegas: medir el solape de
votantes entre dos aliados es otra regresión (aliado i contra aliado j) y queda
como mejora posible.

**Fase 6 (28-sep-2026).** El líder de zona sin candidatura propia:
`{tipo:'lider', nombre, zona:[{code, nombre, comNom, munNom}], apoyo, declarado}`
en la misma lista del navegador. En el panel se arma con un formulario: nombre,
a quién apoyó (el buscador de siempre), la zona en un mapa (tocar puestos o sumar
una localidad o comuna entera) y cuántos votos dice manejar.

`medirLider`: en sus puestos, los votos de quien apoyó contra lo esperado si su
zona votara como el resto de su COMUNA (≥ 8 puestos para comparar; si no, el
municipio), con los totales por puesto de la fase 4. Error por la variación de
esa participación entre los puestos de comparación. El efecto se reparte en los
puestos donde el apoyado sacó de más y entra como un aliado más: retención de
todas las corporaciones a su distancia, unión de la fase 5, mapa y solapes. Lo
declarado entra solo si no hay medición, rotulado, y se contrasta con los votos
válidos 2023 de esos puestos (aviso por encima del 30 %).

⚠️ La comuna de cada puesto sale del georef con `comunaDesde` del motor: el CRM y
el panel la usan igual (si cada uno armara la suya, el mismo líder daría cifras
distintas). Verificado en el navegador: tarjeta y panel dan 872 · 1.893 · 2.514
para el mismo líder.
⚠️ El georef escribe la misma localidad de dos formas («CIUDAD BOLIVAR» y
«CIUDAD BOLÍVAR», «CANDELARIA» y «LA CANDELARIA»): el selector las agrupa por
nombre pelado y no ofrece NULL, cárceles ni puesto censo. Bogotá: 20 opciones.
⚠️ El mapa de puestos es de 2026: marcar Suba entera trae 15 puestos que no
existían en 2023; se dicen aparte de los puestos donde el apoyado no estaba en
el tarjetón, que son otra cosa.

Caso real: un líder de toda Suba que apoyó a Baena (Concejo 2023): sacó 9.812
votos en 99 puestos donde, votando como el resto de Bogotá, habría sacado 6.869
→ 2.943 de más (± 848) → endoso entre 872 y 2.514. Ojo: con la localidad entera
no queda comuna para comparar y se compara con toda la ciudad, así que ese
«efecto» incluye cuánto le va mejor a Baena en Suba por sí mismo; con una zona
chica dentro de la comuna la comparación es más limpia.

Pendiente de esta fase: la diferencia en diferencias (el cambio del apoyado en
la zona entre dos elecciones, menos el de afuera) necesita votos por PARTIDO y
puesto, que `totales-puesto/` todavía no trae.

## Decisiones abiertas (de Ricardo)

1. ~~**Datos de terceros**~~ **Decidido (Ricardo, 28-sep-2026): el nombre del
   líder vive solo en el navegador.** Candi lo dice al guardar cada líder, para
   dar tranquilidad en el momento en que importa.
2. ¿El panel entra en el plan base o solo en «Completo»? (hoy la card dice
   «Endoso, estrategia y acciones de campaña» en Completo).
3. En vitrina (sin acceso): ¿se deja sumar un aliado de muestra con el detalle
   borroso, como el mapa?
