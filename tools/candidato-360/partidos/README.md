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

### Las coaliciones no se ofrecen

«PARTIDO CAMBIO RADICAL - PARTIDO POLITICO MIRA» es una lista de coalición, no
una organización con la que alguien «se lanza». Se marcan (cuarto campo en 1) y
la página **no las ofrece** al elegir, pero se quedan en el catálogo porque sí
miden la huella de cada partido en el territorio: si la persona eligió
«PARTIDO NUEVO LIBERALISMO», los votos de «NUEVO LIBERALISMO- AGRUPACION
POLITICA EN MARCHA» cuentan como suyos (`huellaPartido` compara por las
palabras que identifican al partido, sin «PARTIDO», «MOVIMIENTO», «DE», «LA»).

Es coalición si empieza por «COALICIÓN» o si, partida por sus separadores
(guion, «y», «+», coma), **dos o más** de sus partes son partidos conocidos: los
que aparecen solos en algún índice más el diccionario curado de
`partidos-bloques.js`, que trae las formas cortas que en los índices solo salen
dentro de una coalición («PARTIDO DE LA U», «PARTIDO CONSERVADOR»). Una parte
también cuenta como conocida si todas sus palabras caben en un partido conocido
(«PARTIDO CONSERVADOR» ⊂ «PARTIDO CONSERVADOR COLOMBIANO»). La condición de las
dos partes salva a «PARTIDO DE LA UNIÓN POR LA GENTE - PARTIDO DE LA U», que
lleva guion y es un solo partido. En Bogotá quedan 37 organizaciones ofrecidas
y 14 coaliciones ocultas; se escapan tres variantes con errores de escritura de
la Registraduría («COLOMBIA JUSTAS LIBRES», «PDO. CONSERVADOR COL.»).

Cada entrada queda como `[nombre, candidaturas de 2023, votos a Cámara 2026, coalición]`.
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
node tools/candidato-360/prueba-partido.mjs     # el campo, el filtro, las coaliciones y el reparto (21)
node test/c360-campana.test.mjs                 # en rr-auth: que el worker no bote el partido (11)
```

## De qué familia es cada organización

La lectura ideológica de un territorio usa `partidos-bloques.js`, que estaba
hecho para **partidos nacionales**. Con eso, el **22,3 %** de los votos de la
Asamblea 2023 quedaba «sin clasificar», que en un tablero de familias políticas
es no haber leído. Tres cosas distintas se escondían ahí:

| Qué era | Cómo se resuelve | Ejemplo |
|---|---|---|
| **Coaliciones** escritas como un solo nombre | por sus partes (`bloqueDeOrganizacion`), con el núcleo del nombre para que «CAMBIO RADICAL» calce con «PARTIDO CAMBIO RADICAL» | CAMBIO RADICAL - MIRA → centro-derecha |
| **Movimientos regionales** cuyo nombre no dice nada | se **mide** de dónde vienen sus candidatos | Renace → izquierda |
| **Avales que se prestan** | se quedan sin bloque, y la interfaz dice por qué | ASI, MAIS, AICO |

Faltaban además dos partidos nacionales en la tabla —MIRA y Colombia Justa
Libres—, que son justo los que más aparecen dentro de coaliciones.

### Medir un movimiento regional

```
NODE_USE_ENV_PROXY=1 node tools/candidato-360/partidos/clasificar-locales.mjs
```

Toma los candidatos que se lanzaron con ese aval en 2023, los busca en las otras
elecciones del índice (2011-2023, cinco corporaciones) y se queda con el bloque
más repetido entre sus **otros** avales. Entra a `MOVIMIENTO_LOCAL` la
organización con **≥ 5 personas con rastro** y **≥ 60 % de acuerdo**; lo demás se
queda gris, que es más honesto que rellenar.

### El hallazgo: hay avales sin línea

De las **848 personas** con rastro que se lanzaron con ASI en 2023, el bloque más
repetido reúne apenas el **35 %** —MAIS 31 %, AICO 34 %, «Independientes» 30 %—:
sus candidatos vienen repartidos de todas las familias. No es que no los hayamos
mirado, es que **no tienen línea**, y por eso la etiqueta del bloque `sc` dejó de
llamarse «sin clasificar» y ahora es «sin línea nacional», con los nombres a la
vista en la ficha del perfil.

Resultado: de 22,3 % a **13,2 %** de votos sin bloque, sin reclasificar ni una
sola organización que ya tuviera familia.
