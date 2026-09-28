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
| 2 | Panel `candidato-360-endoso.html` con los excandidatos: ficha por aliado, mapa de sus votos en el territorio, tasa con su método, total. La tarjeta 08 pasa a enlace (como 06 y 09); se retira el modal. | panel v1 |
| 3 | D3 calibración de retención → reemplaza el 30 %. Rango piso/probable/techo. Crecimiento 2027. | fórmula A v2 |
| 4 | D1 totales por puesto (2023 primero) → regresión ecológica en la fórmula A. | fórmula A v3 |
| 5 | Unión probabilística por puesto + mapa combinado + matriz de solape entre aliados. | sin doble conteo |
| 6 | Líder de zona: selector de zona en el mapa, sobre-rendimiento, DiD, «maneja N votos» contrastado. | fórmula B |
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

## Decisiones abiertas (de Ricardo)

1. **Datos de terceros**: el líder de zona es una persona privada. Por la regla del
   Día D (no custodiamos datos del equipo del candidato), la propuesta es que su
   nombre viva solo en el navegador y el servidor, si algún día guarda aliados,
   guarde solo slugs de candidaturas públicas y zonas. ¿De acuerdo?
2. ¿El panel entra en el plan base o solo en «Completo»? (hoy la card dice
   «Endoso, estrategia y acciones de campaña» en Completo).
3. En vitrina (sin acceso): ¿se deja sumar un aliado de muestra con el detalle
   borroso, como el mapa?
