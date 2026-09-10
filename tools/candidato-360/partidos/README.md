# Candidato 360 · con qué partido se lanza

Dos supuestos que la página daba por buenos:

1. **Que quien tiene historial repite aval.** No: cambiar de partido entre una
   elección y la siguiente es corriente, y el reparto de la meta en un salto de
   corporación sigue la **huella del partido** en el territorio de destino. Con
   el partido viejo, reparte mal. Ahora se pregunta, precargado con el de su
   última elección pero abierto.
2. **Que un desplegable nacional sirve.** Entre las dos elecciones hay **2.309
   organizaciones distintas** en el país. Muchas son la misma coalición escrita
   de diez formas («PARTIDO CAMBIO RADICAL - PARTIDO POLITICO MIRA», «CAMBIO
   RADICAL MIRA», «CAMBIO RADICAL - MIRA»…) y muchas solo existen en un
   departamento. Ahora se escribe y se sugiere, filtrado por el departamento de
   la candidatura.
3. **Que con 2023 basta.** Salvación Nacional no existía en 2023 y sacó
   **190.113 votos a Cámara en Bogotá** en 2026. Un catálogo que solo mira
   atrás no tiene el partido de quien se lanza hoy.

| Departamento | Organizaciones | Solo en Cámara 2026 |
|---|---|---|
| Bogotá D.C. | 51 | 8 |
| Valle del Cauca | 149 | 6 |
| Antioquia | 347 | 6 |
| Cundinamarca | 360 | 3 |
| **Todo el país** | **2.309** | |

## El catálogo

`construir.mjs` cruza dos elecciones, porque ninguna sola alcanza:

| Fuente | Qué aporta |
|---|---|
| Los cinco índices territoriales de **2023** (Concejo, JAL, Asamblea, Alcaldía, Gobernación) | Los movimientos locales que solo existen en un municipio y que sí avalan una candidatura territorial. El departamento sale del **slug**: su segundo segmento es el código ELECTORAL (`JAL2023-16-…` es Bogotá) |
| La **Cámara de 2026** (`camara/dep-XX.json`) | Qué está vivo hoy, con cuántos votos. Se toma `por_circunscripcion.TERRITORIAL`, no el total: las listas de las circunscripciones especiales (consejos comunitarios, indígenas) no avalan una candidatura territorial de 2027 |

### La sucursal regional

En 2023 el Pacto se inscribió en Bogotá como «PACTO HISTÓRICO BOGOTÁ» y en 2026
la lista se llama «MOVIMIENTO POLÍTICO PACTO HISTÓRICO»: es la misma
organización y quedaba como dos. Se funden, con **dos condiciones**:

1. Al quitar el nombre del departamento tiene que quedar un nombre que **ya
   existe en ese mismo departamento**. Sin eso, quitar «Bogotá» a diestra y
   siniestra fundiría movimientos que no son sucursal de nada: «BOGOTÁ ENTRE
   TODOS» y «BOGOTÁ MÁS FUERTE» son ellos mismos y su nombre **es** la ciudad.
2. Lo que queda tiene que tener **dos palabras o más**. Con una sola, cualquier
   movimiento regional cae en un genérico: «FUERZA TOLIMA» aterrizaba en «LA
   FUERZA» y «ALMA DEL HUILA» en «ALMA», que no son sus casas matrices.

Con las dos condiciones se funden 11, todas variantes departamentales del Pacto.
El script las imprime al final para poder revisarlas.

Cada entrada queda como `[nombre, candidaturas de 2023, votos a Cámara 2026]`.
Cuando una organización está en las dos, la etiqueta que se muestra es la de
**2026**: es su nombre vigente. En el orden de las sugerencias las dos cifras se
miden cada una contra la mayor de su columna y gana la más alta de las dos; sin
eso, un movimiento local de 2023 con trescientas candidaturas aplastaría a
Salvación Nacional, que no tiene ninguna.

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

Escribe `candidato-360-data/partidos/{dep}.js` (33 archivos, 141 KB en total,
Bogotá 2,7 KB). La página carga **solo el del departamento elegido**. Van en el
repo y no en S3 porque pesan poco y porque son catálogo de interfaz: si no
cargan, no hay autocompletado y el campo queda en texto libre, que es un modo
degradado aceptable.

Al final el script imprime las organizaciones cuyo nombre venía escrito de más
de una forma, para poder auditar las fusiones a ojo.

## En la página

El campo **nunca obliga a elegir del catálogo**: una coalición que se inscribe
en 2027 no está en ningún archivo anterior. Si lo escrito no aparece, la nota lo
dice y se guarda como está. El partido de la campaña viaja en `campana.partido`
(el worker lo conserva desde `_c360NormalizarCampana`) y es el que usa
`partidoVigente()` para repartir la meta.

## Pruebas

```
node tools/candidato-360/prueba-partido.mjs     # el campo, el filtro y el reparto (19)
node test/c360-campana.test.mjs                 # en rr-auth: que el worker no bote el partido (11)
```
