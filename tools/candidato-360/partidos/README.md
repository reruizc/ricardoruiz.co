# Candidato 360 · con qué partido se lanza

Dos supuestos que la página daba por buenos:

1. **Que quien tiene historial repite aval.** No: cambiar de partido entre una
   elección y la siguiente es corriente, y el reparto de la meta en un salto de
   corporación sigue la **huella del partido** en el territorio de destino. Con
   el partido viejo, reparte mal. Ahora se pregunta, precargado con el de su
   última elección pero abierto.
2. **Que un desplegable nacional sirve.** En las territoriales de 2023 se
   inscribieron **2.258 organizaciones distintas** en el país. Muchas son la
   misma coalición escrita de diez formas («PARTIDO CAMBIO RADICAL - PARTIDO
   POLITICO MIRA», «CAMBIO RADICAL MIRA», «CAMBIO RADICAL - MIRA»…) y muchas
   solo existen en un departamento. Ahora se escribe y se sugiere, filtrado por
   el departamento de la candidatura.

| Departamento | Organizaciones en 2023 |
|---|---|
| Bogotá D.C. | 43 |
| Valle del Cauca | 143 |
| Antioquia | 341 |
| Cundinamarca | 357 |
| **Todo el país** | **2.258** |

## El catálogo

`construir.mjs` baja los cinco índices territoriales de 2023 (Concejo, JAL,
Asamblea, Alcaldía, Gobernación) y arma, por departamento, la lista de
organizaciones que inscribieron candidatura allí y cuántas. El código de
departamento sale del **slug**: su segundo segmento es el código ELECTORAL
(`JAL2023-16-…` es Bogotá), el mismo del resto de la plataforma.

Los nombres se guardan **tal cual los publica la Registraduría** —es lo que la
persona reconoce— pero se deduplican por una llave normalizada: sin tildes, sin
puntuación, sin las palabras estructurales (`PARTIDO`, `MOVIMIENTO`, `DE`, `LA`,
`Y`…) y con el resto **ordenado alfabéticamente**. Así «PARTIDO A - MOVIMIENTO
B» y «MOVIMIENTO B - PARTIDO A» son una sola organización, que es el problema
que motivó todo esto. Gana como etiqueta la forma más frecuente. Palabras como
`COALICIÓN`, `ALIANZA` o `POR` **no** se quitan: en los movimientos locales
cargan significado y quitarlas fundía organizaciones distintas.

```
node tools/candidato-360/partidos/construir.mjs
```

Escribe `candidato-360-data/partidos/{dep}.js` (33 archivos, 132 KB en total,
Bogotá 2,2 KB). La página carga **solo el del departamento elegido**. Van en el
repo y no en S3 porque pesan poco y porque son catálogo de interfaz: si no
cargan, no hay autocompletado y el campo queda en texto libre, que es un modo
degradado aceptable.

Al final el script imprime las organizaciones cuyo nombre venía escrito de más
de una forma, para poder auditar las fusiones a ojo.

## En la página

El campo **nunca obliga a elegir del catálogo**: una coalición que se inscribe
en 2027 no está en ningún archivo de 2023. Si lo escrito no aparece, la nota lo
dice y se guarda como está. El partido de la campaña viaja en `campana.partido`
(el worker lo conserva desde `_c360NormalizarCampana`) y es el que usa
`partidoVigente()` para repartir la meta.

## Pruebas

```
node tools/candidato-360/prueba-partido.mjs     # el campo, el filtro y el reparto (15)
node test/c360-campana.test.mjs                 # en rr-auth: que el worker no bote el partido (11)
```
