# Candidato 360

> Documento de trabajo del producto. Está escrito para que alguien —persona o
> modelo— pueda entender **qué es, por qué está hecho así y dónde tocar** sin
> leer 4.000 líneas de JavaScript primero. Si va a proponer cambios, lea
> primero «Las reglas que no se negocian»: casi todo lo demás es discutible.
>
> Última revisión: septiembre de 2026.

---

## 1. Qué es

Un **CRM electoral para candidaturas territoriales colombianas de 2027**
(concejo, alcaldía, JAL, asamblea, gobernación), construido sobre el historial
electoral público. La persona se busca por su nombre, encuentra sus
candidaturas anteriores, dice a qué se lanza ahora y el producto arma un punto
de partida: mapa de su votación, meta de votos, perfil del electorado, lectura
del territorio y seguimiento.

No es una encuesta ni un predictor. Todo sale de **resultados oficiales y censo
electoral**, y cuando algo se estima, se dice que se estima y con qué.

- Vive en `https://ricardoruiz.co/candidato-360.html` (GitHub Pages, rama `main`).
- Datos públicos en S3 (`elecciones-2026/ricardoruiz.co/congreso-2026/output/`).
- Lo privado (sesión, vínculo, briefing) lo resuelve un Worker de Cloudflare
  aparte, **rr-auth**, en `/c360/*`.

## 2. El recorrido

```
Portada
  ├── «Ya me he lanzado»  →  buscar nombre  →  su historial  →  ruta (paso 2)
  └── «Es mi primera vez» →  wizard de 6 pasos
                                        ↓
                                  CRM (tablero)
                                        ↓
        paneles propios: 04 medios · 05 redes · 07 electorado
```

**La ruta (paso 2)** hace *una pregunta por tarjeta*, con salto de animación y
botón «Atrás»:

```
¿misma corporación?
   ├── sí  → ¿con qué partido?
   └── no  → ¿a cuál?  →  ¿dónde?  →  ¿con qué partido o por firmas?
```

**El CRM** son ocho tarjetas: 01 mapa del historial, 02 meta de votos,
03 briefing, 04 lectura de noticias, 05 redes, 06 arquetipos, 07 perfil del
votante, 08 recolección de firmas (solo si va por firmas).

## 3. Las reglas que no se negocian

1. **El voto es secreto.** Nada dice ni insinúa quién votó por alguien. Se
   describe el **censo de los puestos** donde están sus votos, ponderado por
   cuántos sacó en cada uno, y se compara con el territorio. La página
   `candidato-360-perfil.html` explica el método (inferencia ecológica) y por
   qué eso no viola el secreto.
2. **Nada estimado se presenta como propio.** Si falta la fuente, la tarjeta lo
   dice. Ejemplo vivo: la edad del electorado espera `CENSO_EDAD_PUESTO.json`;
   mientras no esté, la sección dice «todavía no» en vez de usar el promedio
   del municipio.
3. **Se dice de dónde sale cada número.** Cada ficha termina en su fuente y en
   su cobertura («cubre el 76 % de su votación»).
4. **El índice electoral es la vitrina.** Un visitante sin cuenta busca, entra
   y ve su historial completo; el muro cae en el CRM, que es lo que se cobra.
5. **Una cuenta, una candidatura.** El vínculo se guarda en el Worker y no se
   cambia desde la plataforma.
6. **Heurística declarada.** Donde hay una regla discutible (bloques
   ideológicos, arquetipos, arraigo) se marca como heurística, se documenta el
   criterio y existe la salida «no sabemos».

## 4. Decisiones de producto que explican el código

| Decisión | Por qué |
|---|---|
| **Una tarjeta por persona**, no por candidatura | La base tiene 439.015 candidaturas. Se unifican por nombre: cuatro componentes iguales siempre; tres componentes solo si todas sus candidaturas territoriales caen en el mismo departamento («Daniel Carvalho Mejía» sí, «Juan Carlos López» no). Los casos dudosos se revisan a mano con `personas/homonimos-xlsx.py`. |
| **Una pregunta por tarjeta** en la ruta | El paso 2 mostraba todo a la vez con la mitad de los campos deshabilitados esperando que alguien adivinara el orden. |
| **El territorio manda** sobre el historial | Quien se muda de municipio no puede ver el mapa de su ciudad vieja. El mapa, la meta, las firmas y la lectura ideológica se calculan sobre el territorio de la **campaña**. |
| **Mapa con drill down** en la pregunta del lugar | Elegir «Boyacá» entre 33 nombres parecidos no confirma nada. Sin departamento: Colombia apagada; con departamento: su silueta con municipios; con municipio: el municipio encendido. Los municipios se pueden tocar. |
| **Aval: partido o firmas** | A alcaldía y gobernación se llega de las dos maneras. Por firmas no hay partido: se pregunta el espectro (5 posiciones) y con eso se ordena la recolección. |
| **La capital, de primeras** en el desplegable de municipios | Concentra las candidaturas. La regla sale del dato (código Divipola `001`), no de una tabla de 33 capitales. |
| **Nombres de lugar en tipo oración** | La Registraduría escribe «MEDELLÍN» y los departamentos llegan «Antioquia»: media línea gritando. Solo cambia la presentación; el valor guardado sigue siendo el original, que es la llave contra la Divipola. |
| **Logos de partido** en la elección del aval | Un nombre en mayúsculas no se reconoce; el logo sí. |

## 5. Arquitectura

### Páginas

| Archivo | Qué es |
|---|---|
| `candidato-360.html` / `.js` / `.css` | La aplicación: portada, búsqueda, ruta, wizard y CRM. El `.js` es el grueso (~3.400 líneas) y está dividido en secciones numeradas con comentarios de cabecera. |
| `candidato-360-medios.html` | Panel 04: sus tres ideas contra la prensa de su territorio. |
| `candidato-360-redes.html` | Panel 05: sus cuentas, buscadas y validadas. |
| `candidato-360-electorado.html` | Panel 07: el análisis del electorado, con figuras y gráficos. |
| `candidato-360-perfil.html` | El método: cómo se lee un electorado sin violar el secreto del voto. |

### Módulos compartidos

| Archivo | Qué resuelve |
|---|---|
| `cand-index.js` | El índice de candidaturas: baja las fuentes de S3, normaliza nombres, agrupa personas y resuelve `slug → URL` del JSON mesa a mesa. |
| `partidos-bloques.js` | **Un solo diccionario** partido/coalición/movimiento → familia ideológica (izq, ci, c, cd, d, sc). Lo usan el mapa de alcaldías y Candidato 360: dos diccionarios serían dos opiniones. |
| `candidato-360-electorado.js` | Las cuentas del electorado (perfil del censo, ideología del territorio, votación objetivo). Compartido por la tarjeta 07 y su página: si cada pantalla calculara por su lado, darían cifras distintas sobre lo mismo. Devuelve **datos**, no texto. |
| `candidato-360-panel.js` | El chasis de los paneles: sesión, vínculo, muro, territorio y helpers de formato. |
| `vote-target.js` | La meta de votos: referencia territorial, censo, participación y margen. |
| `partidos-bloques.js` + `candidato-360-data/partidos/<dep>.js` | Catálogo de organizaciones por departamento para el sugeridor. |
| `data-client.js`, `platform-config.js` | Dónde viven los datos públicos y la API privada. Ningún secreto en el navegador: este repo es público. |

### Datos

Base pública: `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/`

| Ruta | Qué trae |
|---|---|
| `<corp>-<año>/index-*.json` | Índice de candidaturas (nombre, slug, corporación, partido, votos). |
| `<corp>-<año>/<slug>.json` | Una candidatura mesa a mesa (`mesas[]` con dep, mun, zona, puesto, votos). |
| `mapas-2026/DEPARTAMENTOS2.json` | Colombia por departamentos. |
| `mapas-2026/Departamentos-mps/<dep>.json` | Un departamento por municipios (trae `mun_elec`, el código **electoral**, y `mpio_cnmbr`). |
| `mapas-2026/Ciudades-COM-LOC/` | Comunas y localidades de las ciudades con cartografía. |
| `mapas-2026/PUESTOS_GEOREF.csv` | Cada puesto de votación: coordenada, barrio, comuna y **censo por sexo**. |
| `mapas-2026/CENSO_EDAD_PUESTO.json` | Censo por edad y puesto. **Todavía no publicado**; ver §8. |
| `asamblea-2023/dep/<dep>.json` | Resultados de asamblea por **municipio**: la única elección que baja a todos los municipios del país con voto por partido. |
| `concejo-2023/resultados-concejo-2023.json` | Concejo por **comuna**, solo en once ciudades. |
| `candidato-360-data/` (en el repo) | Logos de partido, barrios aproximados, catálogos por departamento y los Excel de homónimos. |

⚠️ **Dos sistemas de códigos.** El *electoral* (el de la Registraduría, el que
viene en los slugs y en las mesas) y el *DANE/Divipola* (el de la cartografía).
No coinciden: Antioquia es `01` electoral y `05` DANE. Los archivos de
`Departamentos-mps` traen los dos, y por eso son los que traducen.

### El Worker (`rr-auth`, repo aparte)

`/c360/me` sesión y vínculo · `/c360/vinculo` crear · `/c360/campana` guardar la
campaña · `/c360/escucha` ideas y redes · `/c360/briefing` · `/c360/redes`
validación de cuentas · `/c360/planes`. Los administradores (`ADMIN_EMAILS`)
pueden abrir cualquier candidatura sin vincularse.

## 6. Las piezas con método propio

Cada una tiene su README en `tools/candidato-360/<tema>/`:

| Tema | Qué decide | Dónde |
|---|---|---|
| **personas** | Cuándo dos candidaturas son la misma persona | `personas/` |
| **meta** | Cuántos votos se necesitan para ganar o para una curul | `meta/` |
| **mapas** | Las escalas del mapa (municipio, comuna, barrio, puesto) y el mapita del lugar | `mapas/` |
| **saltos** | Cómo se reparte la meta cuando se cambia de corporación (arraigo empírico) | `saltos/` |
| **partidos** | Familias ideológicas, coaliciones y movimientos regionales | `partidos/` |
| **firmas** | Cuántas firmas y dónde recogerlas | `firmas/` |
| **perfil** | El electorado: sexo, edad, campo y ciudad, y la votación objetivo | `perfil/` |
| **arquetipos** | Qué mueve el voto en cada barrio (Medellín, Proyecto DC) | `arquetipos/` |
| **barrios-voronoi** | Barrios aproximados donde no hay cartografía oficial | `barrios-voronoi/` |
| **logos** | Los logos de partido y su manifiesto | `logos/` |
| **briefing / redes** | El correo cada tres días y la validación de cuentas | `briefing/`, `redes/` |

Tres que conviene conocer antes de tocar nada:

- **Familias políticas.** El diccionario clasifica partidos; las coaliciones se
  resuelven por sus partes y los movimientos regionales se **miden** (de dónde
  vienen los candidatos que llevaron ese aval en otras elecciones). ASI, MAIS y
  AICO entran por la identidad del partido, pero están marcados como *aval
  amplio*: prestan su aval y sus listas vienen de todas las familias —el bloque
  más repetido entre las otras candidaturas de quienes se lanzaron con la ASI
  en 2023 reúne apenas el 35 %—, y la ficha lo advierte. Sin bloque queda el
  9,1 % de los votos de asamblea 2023 (era 22,3 %).
- **Firmas.** 20 % del censo del territorio dividido por los cargos a proveer
  (uno, en alcaldía y gobernación), con tope de 50.000 (Ley 130/1994 art. 9 y
  las resoluciones de la Registraduría). En municipios pequeños **piden más
  firmas que los votos con los que se gana**, y la tarjeta lo dice en vez de
  dejar pensando que el cálculo está mal.
- **Votación objetivo.** Los votos que faltan para la meta no se parecen a la
  base —esos ya los tiene— sino al territorio del que van a salir, así que el
  perfil objetivo es el promedio de los dos pesado por votos.

## 7. Convenciones del código

- **Sin framework, sin build.** HTML + CSS + JS plano servido por GitHub Pages.
  Todo lo pesado se pide a S3 y se cachea en memoria por sesión.
- **Los comentarios explican el POR QUÉ**, no el qué. Si un `if` existe por un
  caso real (los corregimientos de Medellín van 17-21 en la Registraduría y
  50-90 en la cartografía del DAP), eso se escribe ahí.
- **En español**, incluidos los nombres de funciones nuevas. Conviven con los
  nombres viejos en inglés; no se renombra por renombrar.
- **Nada de secretos en el navegador**: el repo es público. Las llaves viven en
  el Worker.
- **Cache busting a mano**: al tocar un `.js` o `.css` hay que subir el `?v=`
  en todas las páginas que lo cargan.
- **Cada cambio con prueba.** Las pruebas son Playwright contra el HTML real
  con **todo lo remoto simulado** (`page.route`), así que corren sin red y sin
  servidor. Están en `tools/candidato-360/prueba-*.mjs` y se corren una por
  una: `node tools/candidato-360/prueba-ruta.mjs`.
- **Git**: mensajes que cuentan la decisión, no el diff.

### Las pruebas (24 suites)

```
prueba-ruta (26)        la ruta paso a paso, el mapa del lugar, la capital
prueba-perfil (17)      la página del electorado y sus cinco lecturas
prueba-partido (27)     sugeridor, logos, filtro por departamento
prueba-meta (29)        la meta de votos en sus escenarios
prueba-firmas (16)      cuántas firmas y dónde
prueba-frases (18)      el banco de frases del punto de partida
prueba-mapa (15)        Bogotá: ventana urbana, callejero, censo
prueba-arquetipos (15)  las tarjetas 06 y 07
prueba-vitrina (14)     lo que ve un visitante sin cuenta
prueba-puestos (11)     el nivel de puestos y su desglose
prueba-jal-localidad (15) la JAL se elige por localidad, no por ciudad
…y otras once (ciudades, colores, salto, territorio, paneles, wizard, nacional)
```

## 8. Frentes abiertos

1. **`CENSO_EDAD_PUESTO.json` sin publicar.** Es lo único que separa a la
   sección de edad de existir. Se arma local y se sube:
   ```
   python3 tools/edad-1v-2026/build_w26.py
   node tools/candidato-360/perfil/construir-edad.mjs --w26="Bases de datos/output_edad_1v/w26-puesto.csv"
   aws s3 cp CENSO_EDAD_PUESTO.json s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/mapas-2026/CENSO_EDAD_PUESTO.json --content-type application/json --cache-control max-age=3600
   ```
2. **Homónimos.** 131 casos en Antioquia y 83 en Bogotá esperan revisión
   humana (`candidato-360-data/homonimos/`). Con eso se corrige la unificación
   por nombre de tres componentes.
3. **Logos fuera de Bogotá.** Solo existe la carpeta `16`, que hace de catálogo
   nacional. Un departamento con logos propios manda sobre ella.
4. **Arquetipos solo en Medellín.** La cartografía emocional del Proyecto DC
   cubre 152 barrios de Medellín; fuera de ahí la tarjeta se apaga y lo dice.
5. **Movimientos regionales sin clasificar (9,1 %).** Los que no dejan rastro
   suficiente. Bajar el umbral de `clasificar-locales.mjs` sube la cobertura y
   baja la confianza: es una decisión, no un bug.
6. **`saltos-arraigo.json`** (el estudio empírico del salto de corporación)
   está calculado pero no publicado; sin él, el reparto usa el respaldo.

## 9. Si va a proponer cambios

Lo que más ayuda, en orden:

1. **Discutir los métodos**, no el estilo: la clasificación ideológica, la
   fórmula de la meta, el reparto de firmas, el perfil objetivo. Cada uno tiene
   su README con el criterio y sus números.
2. **Traer datos que falten**: censo por edad, cartografía barrial de otras
   ciudades, logos por departamento, resultados por comuna fuera de las once.
3. **Buscar el caso que rompe**: un municipio sin comunas, una candidatura sin
   mesas, un departamento con un solo municipio, una coalición escrita de otra
   forma. Casi todos los bugs de este producto han sido eso.

Lo que no: convertirlo en un predictor, estimar lo que no está publicado, o
presentar como dato de la persona lo que es del territorio.
