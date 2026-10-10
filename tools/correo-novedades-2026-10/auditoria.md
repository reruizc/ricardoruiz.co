# Auditoría para el correo de novedades · octubre 2026

Correo para los 334 usuarios registrados en plan gratuito (`free`, rotulado «Básico»). Auditoría del 10-oct-2026 sobre `main` en 59405dc.

**Cómo se hizo y qué no se pudo comprobar**

- **ricardoruiz.co no fue accesible desde el entorno de trabajo**: la política de red lo bloqueó con un 403 del proxy. Como el sitio es GitHub Pages (`CNAME`), tomé el HTML/JS del repo como lo publicado. No hay capturas del sitio en vivo.
- **S3 sí respondió.** Todas las cifras de datos se descargaron de `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/...` y se leyeron en el JSON; la fecha de cada dato es el corte del JSON o el `Last-Modified`.
- **El worker `rr-auth.reruizc.workers.dev` no se pudo consultar** (login, `/auth/me`, `/caudal/api`, `/juez/*`, `/micongreso/*`), y tampoco `checkout.wompi.co`. Todo lo que depende de ellos va como **SIN VERIFICAR**.
- **CLAUDE.md ya no está en el repo**: salió el 15-ago-2026 (commit 81019e0) y está en `.gitignore`. Usé la última versión del historial (14-ago) solo como lista de cifras candidatas. Ninguna cifra de este informe sale de ahí sin confirmar contra el dato publicado.
- «Cálculo propio» = suma, resta o porcentaje hecho sobre el dato publicado; se indica la fórmula.
- Abreviaturas de rutas: `S3` = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output` · `S3DL` = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/DESCARGAS`.
- El gate de planes es `plan-gate.js` (`PLAN_RANK` en :47). **Solo lo usan veleta, oportunidad, los 3 tableros 2023 y brújula.** Las demás páginas tienen chequeos propios o ninguno.

---

## (a) Tabla por página

Leyenda de problemas: 🔴 impide anunciar · 🟠 importante · ⚪ cosmético. El detalle y la propuesta de arreglo de cada uno están en (c) y en el anexo.

### Elecciones

| Página | URL pública | Qué ve el usuario gratis | Datos hasta | Dato gancho | Fuente | Problemas |
|---|---|---|---|---|---|---|
| presidencial-2026.html | https://ricardoruiz.co/presidencial-2026.html | Todo el visor (1ª y 2ª vuelta, mapa hasta comuna/zona, KPI). Solo pide Pro el botón Excel (:1246), que además no hace nada. | Escrutinio 1V 31-may y 2V 21-jun-2026; exterior por preconteo. S3 del 08-oct-2026 | La 2ª vuelta se decidió por **247.586 votos** (12.951.256 De La Espriella frente a 12.703.670 Cepeda, **0,95 pp**). Cepeda ganó **19 de 33 departamentos** y perdió. | `S3/pres-escr/2026/resumen.json` → `.consultas[1].candidatos[0..1].votos`; departamentos: conteo propio sobre `S3/pres-escr/2026/deps.json` `."2v"` (sin cod 88) | 🟠 Excel con `TODO` (:1247) · 🟠 electoral.html:1539/:1549 promete «hasta puesto» · 🟠 margen distinto en otras páginas · ⚪ «Free» en vez de «Básico» |
| presidencial-2010.html | https://ricardoruiz.co/presidencial-2010.html | Todo; Excel pide Pro y no hace nada (:1242) | Escrutinio 2010 (S3 del 08-oct-2026) | Santos: **9.028.943 votos (69,13 %)**; ganó **32 de 33 departamentos**, todos menos Putumayo | `S3/pres-escr/2010/resumen.json` `.consultas[1]`; 32/33 = conteo propio sobre `deps.json` | 🟠 Excel `TODO` · ⚪ el pie dice «2026» (:340) |
| senado-2022.html | https://ricardoruiz.co/senado-2022.html | Todo, hasta mesa; Excel pide Pro (:2241) | Escrutinio 13-mar-2022 (`generado_en` 08-oct-2026) | **Gilberto Tobón**, 5º más votado (**175.557**), se quedó por fuera: su partido sacó 431.166 y el umbral era **509.709** | `S3/senado-2022/resumen.json` → `.partidos[FUERZA CIUDADANA…]`, `.umbral`; el puesto 5º es ordenamiento propio | ⚪ sin nota de curules de Comunes · ⚪ modo día visible de 7 a 19 h |
| camara-2018.html | https://ricardoruiz.co/camara-2018.html | Todo, hasta mesa; Excel pide Pro (:1379) | Escrutinio 11-mar-2018 (`generado_en` 08-oct-2026) | **1.676.352 votos nulos**, el 9,85 % de los votantes | `S3/camara-2018/resumen.json` `.votnul` / `.votant` (% propio) | Ninguno relevante |
| consultas-pacto-2025.html | https://ricardoruiz.co/consultas-pacto-2025.html | Todo; Excel pide Pro y no hace nada (:1242) | Escrutinio 26-oct-2025 | Senado: **Pedro Hernando Flórez, 185.029 votos (7,91 %)** entre 144 aspirantes | `S3/pres-escr/pacto2025/resumen.json` `.consultas[0].candidatos[0]` | 🟠 Excel `TODO` · ⚪ solo Senado y Cámara, no la consulta presidencial · ⚪ pie «2026» |
| atipica.html | https://ricardoruiz.co/atipica.html | Todo, sin gate | **28 atípicas** 2025-2026 en el índice, **8 con resultado**; la más reciente es Cartago, 20-sep-2026 | Gobernación del Vichada definida por **397 votos** | `atipicas/vichada-2025.json` (repo), suma de `.puestos[].v`; KPI en :211 | ⚪ la meta dice «escrutinio» y Tunja/Cartago son preconteo |
| atipica-tunja-2026.html | https://ricardoruiz.co/atipica-tunja-2026.html | Todo | Elección del 26-jul-2026, **ya con resultado** (preconteo, boletín 12, 100 % mesas) | Rafael Acevedo ganó con **10.758 votos, el 24,8 % de los válidos**; votó el **30,7 %** del censo | `atipica-tunja-2026.html:75-77` (`const R`), % de los KPI de la página | ⚪ «Volver» va a electoral.html |
| atipica-cartago-2026.html | https://ricardoruiz.co/atipica-cartago-2026.html | Todo | Elección del 20-sep-2026, **ya con resultado** (preconteo, boletín 9, 100 % mesas) | El Consejo de Estado anuló la elección de Piedrahita y él **volvió a ganar con 17.894 votos (56,3 %)** | `atipica-cartago-2026.html:59,71-73` | ⚪ «Volver» va a electoral.html |
| analisis-candidato.html | https://ricardoruiz.co/analisis-candidato.html | Buscador y ficha de cualquier candidato; con sesión, detalle municipal y Excel por depto./municipio. Bloqueado: Excel por comuna (Pro, :3807) y por puesto/mesa (Premium, :3974) | 29 índices 2010-2026; último resultado 2V 2026 (índice presidencial `v` 2026-07-14); índices actualizados hasta el 29-sep-2026 | Galán, **1.499.734** votos (Alcaldía 2023), frente al senador más votado del archivo, Uribe, **891.964** (2018). Paloma: **3.248.589** en la consulta y **1.637.665** en 1V | `S3/alcaldia-2023/index-alcaldia-2023.json` y `S3/congreso-2018/index-congreso-2018.json` `.candidatos[]`; `S3/presidencial/index-presidencial.json` `.personas[paloma]` | 🟠 pantalla de carga: «consulta de 2022» (:2906) y «la votación más alta es Petro 2022» (:2913) · ⚪ sin medición · ⚪ «Free» |
| edades-1v.html | https://ricardoruiz.co/edades-1v.html | Todo | Preconteo 1V 31-may-2026; publicada el 10-jun-2026 | Cepeda **~60 %** entre 18-25 años y Abelardo **~79 %** entre mayores de 60 (inferencia ecológica, IC en la página) | `edades-1v.html:118-124` y `analisis-edades/04_perfil_2026.png`. Sin JSON publicado: verificado solo contra el gráfico | ⚪ «40,5 % → 41,2 %» (:141) no cuadra con el CSV publicado (40,92 %) |
| ciudades-2v-barrios.html | https://ricardoruiz.co/ciudades-2v-barrios.html | Todo (14 ciudades, 1V/2V) | Preconteo 1V y 2V; JSON del 23-jun-2026 | Barranquilla pasó de empate (**Cepeda +1,6**) a **Cepeda +9,6**. Cepeda ganó Bogotá (53,7 %), Cali (60,6 %) y Barranquilla (54,8 %); Abelardo, Medellín (66,3 %) | `S3/prec-2v/ciudades-barrios-2v.json` → `.{ciudad}.meta.m1/.m2/.cep2/.abe2` (% propio, misma fórmula que :217) | ⚪ el texto anuncia 8 ciudades y hay 14 · ⚪ sin medición |
| voto-fusil-2026.html | https://ricardoruiz.co/voto-fusil-2026.html | Todo | Preconteo 2V 21-jun-2026; análisis cerrado en jul-2026 | **675 mesas** con 100 % para Cepeda y **81** para Abelardo (64 en el exterior); suman el **0,33 %** del voto | Conteo propio sobre `S3/presidencial/PRES2V_IVAN_CEPEDA_CASTRO.json` y `PRES2V_ABELARDO_DE_LA_ESPRIELLA.json` `.mesas[]`; la página lo dice en :83, :92 | 🟠 huérfana (nadie la enlaza) · 🟠 `og:image` relativa (:10) · 🟠 «250.830» (:92) · ⚪ sin medición |
| bogota-1v-barrios.html | https://ricardoruiz.co/bogota-1v-barrios.html | Todo, incluida la descarga del preconteo por mesa (el gate solo frena al anónimo, :134-144) | Preconteo 1V 31-may-2026 | Cepeda ganó **435 barrios** y Abelardo **223** (de 658) | Conteo de `.win` en `const BARRIOS` (`bogota-1v-barrios.html:92`); lead en :66 | 🟠 meta/og dicen 361/196 (:5, :7) · ⚪ sin medición |
| descargas.html | https://ricardoruiz.co/descargas.html | **Por diseño, nada**: a los 1,4 s sale un modal «Tu cuenta no tiene un plan activo» (:1628). **En la práctica** las secciones 01-04 quedan descargables por un fallo de orden (:1612 frente a :1657) | 2V por puesto actualizada el 08-oct-2026; Congreso, 13-abr-2026 | Escrutinio 2026 por puesto: **14.420** (1V) y **14.435** (2V) filas; **267 elegidos** al Congreso (102 + 165) | Conteo de filas de `S3DL/ESCRUTINIO_{1V,2V}_2026_PUESTO.csv` y `S3DL/oficial-cne/Congreso_2026_elegidos.csv` | 🔴 no anunciar como algo del plan gratis · 🟠 gate roto · 🟠 15 CITREP dan 403 · ⚪ sin medición |

### Congreso

| Página | URL pública | Qué ve el usuario gratis | Datos hasta | Dato gancho | Fuente | Problemas |
|---|---|---|---|---|---|---|
| legislativo.html | https://ricardoruiz.co/legislativo.html | Todo; no hay gate | Radicados al 6-oct-2026 (consolidado al 18-sep, provisional desde el 19-sep); órdenes del día hasta el 14-oct-2026; actualización automática ~2 veces al día | **639** proyectos de ley radicados del 20-jul al 6-oct, frente a **381** en 2022 (+68 %) y **337** en 2018 (+90 %) | `S3/legislativo/ritmo-legislaturas.json` → `.series["2026"\|"2022"\|"2018"].total` (`.v` 2026-10-09); % calculados por la página (:376-387) | ⚪ «lectura exclusiva de deuda» (:110) para algo gratis · ⚪ «Free» (legislativo-base.js:81) · ⚪ 14.055 proyectos desde 1990 (:149) choca con 13.831 y «más de 10.600» |
| legislativo-en-vivo.html | https://ricardoruiz.co/legislativo-en-vivo.html | Todo (30 radicados con resumen en lenguaje llano y PDF) | Senado al 6-oct-2026 y Cámara al 1-oct-2026 (`en-vivo.json` del 09-oct) | Hay un proyecto para un **impuesto del 3 %** a plataformas y redes para financiar salud mental (PL 417/2026C) | `S3/legislativo/en-vivo.json` → `.camara[numero="417/2026C"].explica.titular`. Rota: sale del feed con nuevas radicaciones | 🟠 12 de 15 resúmenes del Senado salen solo del título aunque la fila diga «Texto disponible» · ⚪ el resumen de PL 412 contradice su fecha |
| legislativo-historico.html | https://ricardoruiz.co/legislativo-historico.html | Todo | «Corte del histórico: agosto de 2026» (:149); las cifras vivas vienen de la API (SIN VERIFICAR) | En 2022-2026 circulan **3.447** proyectos de ley, pero son **2.826** únicos: **621** se cuentan dos veces | `legislativo-historico.html:125-127` y `CUAT_PL` (:177); resta propia | 🟠 la fila 2026-2030 dice **205** proyectos (:177) frente a los 639 del hub · ⚪ 18,5 % (:107) frente a 18,4 % |
| pgn-2027.html | https://ricardoruiz.co/pgn-2027.html | Todo, incluido el modo «solo deuda» | **Corte 28-ago-2026** (:119); no hace fetch | El servicio de la deuda pasa de **$100,4 B** a **$155,4 B** (+$55 B) | `YEARS` en `pgn-2027.html:127-128` | 🔴 congelada: estado «En trámite» y calendario en futuro («antes del 15 sep», :102) |
| mi-congreso.html | https://ricardoruiz.co/mi-congreso.html | Todo, **sin cuenta**: elige cualquiera de los 285 congresistas y activa **alertas por correo gratis** (un congresista por suscripción, :594) | Comisiones al 1-sep-2026; agenda al 14-oct-2026; proyectos, votos y prensa desde la API (SIN VERIFICAR) | **285** congresistas (103 Senado, 182 Cámara): eliges uno y te llega un correo cuando sus proyectos se mueven | Conteo de `ELECTOS_RAW` en `legislativo-electos.js` y `S3/legislativo/comisiones-2026.json` | 🔴/🟠 el tablero depende del worker: probarlo antes · 🟠 vendida «para congresistas y UTL» |

### Seguridad

| Página | URL pública | Qué ve el usuario gratis | Datos hasta | Dato gancho | Fuente | Problemas |
|---|---|---|---|---|---|---|
| policia.html | https://ricardoruiz.co/policia.html | Todo (hub sin gate) | **Agosto 2026** (`meta.json` `.anio_parcial.hasta_mes` = 8; LM 30-sep-2026) | **10.449.231** hechos denunciados, 21 delitos, **1.112** municipios, 2015-ago 2026 | `S3/ponal/meta.json` → `.hechos`, `.delitos`, `.municipios` | 🟠 las 3 imágenes de las tarjetas dan 404 (:80, :88, :96) · 🟠 la tarjeta de la home dice «2015-2024» (index.html:629) · ⚪ 1.111 frente a 1.112 |
| policia-mapa.html | https://ricardoruiz.co/policia-mapa.html | Todo (país → depto → municipio; comuna/barrio en Bogotá, Medellín y Cali) | Ago-2026; tasas solo para años completos desde 2018 | Homicidios 2025 por 100.000 hab.: **Guaviare 81,5**, San Andrés 63,1, Cauca 53,0 | Cálculo propio, misma fórmula de la página (:249-251): `S3/ponal/deptos.json` `.deptos["95"].d.homicidios.y[10]` = 69 × 100.000 / `S3/ponal/poblacion.json` `.deptos["95"].p[7]` = 84.696 | ⚪ meta dice 1.111 municipios |
| policia-historico.html | https://ricardoruiz.co/policia-historico.html | Todo | Ene-ago 2026 contra ene-ago 2025 | Violencia intrafamiliar: **107.265** denuncias ene-ago 2026 frente a **93.509** en 2025 (**+14,7 %**), la cifra más alta de ese tramo desde 2015 | `S3/ponal/nacional.json` → `.ytd.por_delito.violencia_intra[11]` y `[10]`; el % lo calcula la página (:243) | 🟠 extorsión 2023 = 33.466 (SIEDCO) frente a 11.078 (MinDefensa), sin nota: no usar extorsión |
| policia-abiertos.html | https://ricardoruiz.co/policia-abiertos.html | Todo (13 secciones) | MinDefensa al 31-ago-2026; DIJIN al 31-jul-2026 | Masacres: **72 casos y 260 víctimas** en ene-ago 2026, frente a **90 y 315** en todo 2025 | `S3/ponal/mindefensa.json` → `.masacres.anio["2026"\|"2025"]`; `.corte` | ⚪ «127 conjuntos» frente a 63 listados |

### Lab y herramientas ciudadanas

| Página | URL pública | Qué ve el usuario gratis | Datos hasta | Dato gancho | Fuente | Problemas |
|---|---|---|---|---|---|---|
| pensamiento-investigativo.html | https://ricardoruiz.co/pensamiento-investigativo.html | Todo (ensayo) | n/a | Lectura de 15 minutos, 7 secciones, la última «Un primer proyecto, esta tarde» | `pensamiento-investigativo.html:219-221,235,604` | 🟠 sin medición · 🟠 solo la enlaza analisis-estructural.html · ⚪ «Escríbame» lleva a index.html (:634) |
| tutelas-salud.html | https://ricardoruiz.co/tutelas-salud.html | Todo, «gratis · sin registro» (:485) | Panel: microdato de la Corte, vigencia 2025 (JSON del 21-jul-2026). Hero: MinSalud, abr-2026 | **274.510 tutelas** por salud en 2025 (**+15,7 %**); el **64,85 %** pide servicios que ya están en el plan de beneficios | `tutelas-salud.html:506,515-521`, que cita el informe de MinSalud. **SIN VERIFICAR** contra el informe | 🟠 promete «tus datos no salen de tu dispositivo» y envía diagnóstico, EPS y fechas a una Lambda (:3281-3303) · 🟠 «tutelas» frente a peticiones (462.361) · 🟠 huérfana · 🟠 sin medición |
| quien-quiere-ser-juez.html | https://ricardoruiz.co/quien-quiere-ser-juez.html | Todo el juego. «Tu diagnóstico» y el ranking piden el **registro propio del juego** (:398-404, :447-470), no la cuenta del sitio | Banco v4 del 13-ago-2026 | 30 preguntas por partida en **8 salas**, al ritmo del examen real (4h30 para 200 preguntas), con corte en **800/1000**; banco de **más de 500** preguntas (524 por conteo propio) | `banco-judicial.js` → `.examen` y conteo de `window.BANCO_JUDICIAL`; `quien-quiere-ser-juez.html:324-333` | 🟠 faltan los 8 mp3 · 🟠 no hay enlace desde la home · 🟠 la cuota de escrituras KV del worker puede tumbar el registro en un pico (SIN VERIFICAR) |

### Lo que pide plan (cierre del correo)

| Página | URL pública | Qué ve el usuario gratis | Datos hasta | Dato gancho | Fuente | Problemas |
|---|---|---|---|---|---|---|
| resultados-jal-2023.html | https://ricardoruiz.co/resultados-jal-2023.html | 12 ciudades, mapa y detalle completo de cada comuna. **Pro**: barrios, puestos. **Premium**: mesas (`GATE_FEATURES` :437) | Elección del 29-oct-2023 (JSON `v` 2026-09-17) | En Medellín, **Creemos ganó la JAL en 19 de 20** comunas y corregimientos | Conteo propio sobre `S3/jal-2023/resultados-jal-2023.json` `.data["01-001"].comunas[].partidos[0][0]` | ⚪ «Votos válidos» sin el blanco (:728) · ⚪ «Plan Free» |
| resultados-concejo-2023.html | https://ricardoruiz.co/resultados-concejo-2023.html | Igual que JAL (:436-437) | 29-oct-2023 | En Cali, **la U ganó el Concejo en 25 de 37 comunas** | Conteo propio sobre `S3/concejo-2023/resultados-concejo-2023.json` `.data["31-001"].comunas[]` | ⚪ mismos de JAL |
| resultados-asamblea-2023.html | https://ricardoruiz.co/resultados-asamblea-2023.html | 32 departamentos y detalle por municipio. Pro: barrios y puestos. Premium: mesas | 29-oct-2023 | En Antioquia, el Liberal ganó la Asamblea en **36** municipios, el Conservador en **35** y el CD en **33** | Conteo propio sobre `S3/asamblea-2023/dep/01.json` `.comunas[].partidos[0][0]` | ⚪ mismos de JAL |
| brujula-2027.html | https://ricardoruiz.co/brujula-2027.html | Ficha de cualquier candidatura, top 5 de barrios, duelo por edad, datos fríos. Pro: «ver los 20 barrios» | Hasta 1V-2026; edad, jul-2026; indicadores, 2024 | (no recomendado) Bogotá: Cepeda **73,3 %** del duelo entre 18-35 años y **8,5 %** entre mayores de 61 (inferencia ecológica) | `S3/edad-1v/edad-geo.json` `.ciudades["Bogotá"].cep` | 🔴 borrador, sin enlaces entrantes · 🔴 6 candados que no abren nada aunque se pague · 🟠 medios vía Caudal |
| veleta.html | https://ricardoruiz.co/veleta.html | País → depto → municipio, 3 candidatos. Pro: ciudades, Excel. **Premium**: barrios, PDF (:686-695) | **25-may-2026**, antes de la 1ª vuelta | Ninguno (modelo previo a la 1V) | `…/output_ponderador/ponderador-actual.json` `fecha_corte` | 🔴 no es novedad: datos y textos previos a la 1V · 🟠 barrios Premium aquí y Pro en pricing/oportunidad |
| oportunidad.html | https://ricardoruiz.co/oportunidad.html | 6 candidatos, capas, depto/municipio. Pro: comunas, barrios, CSV. Premium: puestos, PDF (:1060-1075) | **25-may-2026** | Ninguno | ídem | 🔴 no es novedad (previa a la 1V) |
| pricing.html | https://ricardoruiz.co/pricing.html | La tarjeta Básico marcada como «Plan actual». Pro **$79.900/mes** ($59.900 anual); Premium **$219.000/mes** ($179.000 anual); coincide con plan-gate.js:50-53 | n/a | n/a | `pricing.html:417,433` | 🔴 login.html manda a links de Wompi distintos · 🟠 Policía «próximamente» (:397, :442, :463, :475) · 🟠 «−20 %» inexacto · 🟠 lo prometido por plan no coincide con las páginas |

**Fuera de la lista pero en el camino del lector:** `dashboard.html`, donde aterriza el usuario al entrar. Para el plan `free` solo muestra «Histórico Electoral» y «Consulta 2025» (`dashboard.html:1184-1189`). No aparecen Congreso, Seguridad ni Lab, así que el panel contradice la idea de los cuatro frentes (ver (c)).

---

## (b) Los mejores datos gancho, listos para pegar

Todos están verificados contra el dato publicado, salvo donde se indica. Cada gancho lleva el enlace donde el lector puede comprobarlo.

**Elecciones**

1. **La Presidencia se decidió por 247.586 votos.** Abelardo De La Espriella sacó 12.951.256 y Iván Cepeda 12.703.670 en la segunda vuelta: 0,95 puntos de diferencia. Cepeda ganó 19 de los 33 departamentos, Bogotá incluida, y aun así perdió.
   → https://ricardoruiz.co/presidencial-2026.html?c=2v
   Fuente: `S3/pres-escr/2026/resumen.json` `.consultas[1].candidatos[0..1].votos` (escrutinio; archivo del 08-oct-2026). Los 19 departamentos son conteo propio sobre `deps.json` `."2v"`.
   *Ojo: usar 247.586 en todo el correo. Otras páginas del sitio dicen 248.050 (preconteo) y 250.830 (voto-fusil-2026.html:92). Ver (c).*

2. **Barranquilla pasó del empate a Cepeda +9,6.** En la primera vuelta la ciudad estaba en Cepeda +1,6; en la segunda, 54,8 % frente a 45,2 %. Cepeda ganó tres de las cuatro grandes ciudades (Bogotá 53,7 %, Cali 60,6 %, Barranquilla 54,8 %) y Abelardo ganó Medellín con 66,3 %. Todo, barrio por barrio.
   → https://ricardoruiz.co/ciudades-2v-barrios.html
   Fuente: `S3/prec-2v/ciudades-barrios-2v.json` `.{ciudad}.meta.m1/.m2/.cep2/.abe2` (preconteo; JSON del 23-jun-2026). Los porcentajes son cálculo propio con la fórmula de la página.

**Congreso**

3. **El Congreso nuevo arrancó radicando un 68 % más que el anterior.** Del 20 de julio al 6 de octubre se radicaron al menos 639 proyectos de ley. En los mismos días de 2022 fueron 381 (+68 %) y en 2018, 337.
   → https://ricardoruiz.co/legislativo.html
   Fuente: `S3/legislativo/ritmo-legislaturas.json` `.series["2026"|"2022"|"2018"].total` (dato del 09-oct-2026). *Decir «al menos»: desde el 19-sep la cifra es provisional y puede subir.*

4. **Sigue a tu congresista sin pagar nada.** Elige a cualquiera de los 285 congresistas (103 senadores y 182 representantes) y te llega un correo cuando sus proyectos cambian de estado o entran al orden del día.
   → https://ricardoruiz.co/mi-congreso.html
   Fuente: conteo de `ELECTOS_RAW` en `legislativo-electos.js`. *SIN VERIFICAR que el tablero y el alta de alertas respondan (dependen del worker): probarlo antes de enviar.*
   Alternativa sin worker: «En 2022-2026 se habla de 3.447 proyectos de ley, pero son 2.826: 621 se contaron dos veces porque pasaron por las dos cámaras» (`legislativo-historico.html:125-127`).

**Seguridad**

5. **La violencia intrafamiliar, en su punto más alto desde 2015.** De enero a agosto de 2026 hubo 107.265 denuncias, frente a 93.509 en el mismo periodo de 2025 (+14,7 %). Es la cifra más alta para esos ocho meses desde 2015.
   → https://ricardoruiz.co/policia-historico.html
   Fuente: `S3/ponal/nacional.json` `.ytd.por_delito.violencia_intra[11]` y `[10]` (datos a ago-2026; LM 30-sep-2026). El máximo es comparación propia sobre la misma serie.

6. **Los delitos informáticos suben 39,6 % en un año.** Fueron 65.685 denuncias de enero a agosto de 2026, frente a 47.056 en el mismo tramo de 2025.
   → misma página, misma tabla.
   Fuente: `S3/ponal/nacional.json` `.ytd.por_delito.del_informaticos[11]` y `[10]`.
   Alternativa: «Masacres: 72 casos y 260 víctimas en ocho meses de 2026; en todo 2025 fueron 90 y 315» (`S3/ponal/mindefensa.json` `.masacres.anio`, corte 31-ago-2026, en https://ricardoruiz.co/policia-abiertos.html).

**Lab y herramientas ciudadanas**

7. **¿Quieres ser juez? Pruébate.** Un simulador del concurso de méritos con 30 preguntas por partida en 8 especialidades, al ritmo del examen real (4 h 30 para 200 preguntas) y con el corte en 800 sobre 1.000. El banco tiene más de 500 preguntas.
   → https://ricardoruiz.co/quien-quiere-ser-juez.html
   Fuente: `banco-judicial.js` `.examen` y conteo propio (524). *No decir «regístrate en el sitio»: el diagnóstico pide el registro del juego, no la cuenta.*

8. **274.510 tutelas por salud en 2025, +15,7 %.** El 64,85 % pide servicios que ya están en el plan de beneficios. La herramienta te ayuda a preparar la tuya, gratis.
   → https://ricardoruiz.co/tutelas-salud.html
   Fuente: `tutelas-salud.html:506,515-521`, que cita el informe de MinSalud de abril de 2026. **SIN VERIFICAR contra el informe original.** *No repetir «tus datos no salen de tu dispositivo» y no mezclar con el 462.361 del panel (ver (c)).*

**Para el cierre (qué pide plan).** Con la cuenta gratis ya se ve todo lo anterior y, en los tableros 2023 (JAL, Concejo, Asamblea), el detalle completo por comuna o municipio. Pro ($79.900/mes) abre barrios y puestos en esos tableros y las ciudades en Veleta/Oportunidad. Premium ($219.000/mes) abre mesa a mesa y las descargas. Gancho para el cierre: «En Medellín, Creemos ganó la JAL en 19 de 20 comunas; con Pro lo ves barrio por barrio» (https://ricardoruiz.co/resultados-jal-2023.html; conteo propio sobre `S3/jal-2023/resultados-jal-2023.json`). Antes de enviar, ver los 🔴 de pricing/login.

---

## (c) Problemas, ordenados por gravedad

### 🔴 Impiden anunciar la página, o el CTA de pago, tal como está

1. **Los usuarios con sesión vencida pagan con links de Wompi viejos.** `login.html:805-806` usa los mensuales `PLslXs` (Pro) y `YIczAd` (Premium); `pricing.html:1078-1079` usa `Ds08zS` y `E1ZVCn`. El camino del lector es: pricing sin sesión → `register.html?next=pay` → login → **link viejo**. Si ese link ya no está en el mapa del worker, el pago **no activa el plan**. SIN VERIFICAR en el worker y en Wompi, pero el código está confirmado. **Arreglo:** poner en login.html los mismos `WOMPI_LINKS` que en pricing.html (o sacarlos a un .js común) y confirmar el mapa del worker antes de enviar.
2. **descargas.html no sirve para el plan gratis.** Al usuario gratis le sale a los 1,4 s el modal «Tu cuenta no tiene un plan activo. Actualiza a Pro o Premium» (`descargas.html:1626-1634`). Además el gate falla: la IIFE (:1577-1652) desactiva `.dl-btn` antes de que `renderGrid` los pinte (:1657-1660). Por eso las secciones 01-04 (presidencial por puesto, CNE, Congreso) quedan descargables para el usuario gratis **y para el anónimo**. **Arreglo:** decidir si se regala eso al plan gratis. Si sí, quitar el modal en esas pestañas y decirlo en el correo. Si no, mover las llamadas a `renderGrid` antes de la IIFE. Mientras tanto, no anunciar descargas.html en el correo.
3. **pgn-2027.html está congelada al 28-ago-2026.** Sigue en «En trámite» y el calendario habla en futuro de fechas que ya pasaron («Antes del 15 sep · Se fija el monto», «Antes del 25 sep · Primer debate», `pgn-2027.html:48-50, :102, :119`). **Arreglo:** actualizar el estado del trámite y la fecha de corte, o dejarla fuera del correo.
4. **brujula-2027.html es un borrador y vende funciones que no existen.** Tiene la etiqueta «Muestra gratuita · borrador» (:279) y ninguna página la enlaza. Seis botones con candado («Ver mesa a mesa», «Comparar dos elecciones», «Exportar Excel», «Alertas semanales», «Análisis de tono con IA», «Arquetipos», en :341-343, :417-418, :454) no hacen nada ni siquiera pagando. Su módulo de medios usa `/caudal/api`. **Arreglo:** no mencionarla, o rotular esos botones «Próximamente» sin el modal de pago.
5. **veleta.html y oportunidad.html no son novedad.** Usan datos al 25-may-2026 y textos para «ganar la 1ª vuelta» (veleta.html:489). Se pueden citar como archivo, no como novedad.
6. **mi-congreso.html hay que probarla antes de anunciarla.** La agenda y el padrón vienen de S3 y funcionan. Pero proyectos, votos, control político, prensa y el alta de alertas (`/micongreso/alerta`, :584-609) dependen del worker, que no se pudo probar. Si la ruta falla, la página dice «Las alertas por correo se están activando en estos días» (:613). **Arreglo:** antes de enviar, probar en un navegador sin sesión y con una cuenta gratis: elegir un congresista y activar una alerta.

### 🟠 Importantes: se puede anunciar, pero conviene arreglar antes de enviar

7. **El panel del usuario contradice el correo.** En `dashboard.html:1184-1189` el plan `free` tiene solo `['electoral','consulta2025']`, y `ALL_TOOLS` (:1204) no incluye Congreso, Seguridad ni Lab. Quien entre tras leer el correo verá un sitio solo electoral con 4 de 6 tarjetas bloqueadas. Además, la columna «Lo último» toma las 3 noticias más recientes de noticias.html, la primera del **9-jul-2026**. **Arreglo:** añadir tarjetas de los nuevos frentes y una noticia de octubre.
8. **pricing.html dice que Policía llegará «próximamente»** (:397, :442, :463, :475), pero las cuatro páginas de Policía ya están publicadas y abiertas. Esto contradice el frente de seguridad del correo. **Arreglo:** actualizar ese texto.
9. **Páginas sin ninguna entrada desde el sitio.** `voto-fusil-2026.html` y `tutelas-salud.html` no las enlaza nadie. `quien-quiere-ser-juez.html` solo se enlaza desde dashboard y admin. `pensamiento-investigativo.html` solo desde analisis-estructural.html. **Arreglo:** si van en el correo, añadirlas a la home o a noticias para que el lector pueda volver a ellas.
10. **14 páginas no miden visitas** (no cargan `theme.js`, que inyecta `/track.js`, ni `track.js`): atipica, atipica-tunja-2026, atipica-cartago-2026, analisis-candidato, ciudades-2v-barrios, voto-fusil-2026, bogota-1v-barrios, descargas, pensamiento-investigativo, tutelas-salud, resultados-jal/concejo/asamblea-2023 y brujula-2027. **Arreglo:** añadir `<script defer src="/track.js"></script>` a las que se enlacen, o el correo no tendrá medición de clics por página.
11. **tutelas-salud.html promete más privacidad de la que da.** Dice «tus datos no salen de tu dispositivo» (:7, :510, :721), pero `registroPayload` envía a una Lambda el diagnóstico (texto libre), la EPS, la IPS, el municipio y las fechas (:3281-3303). **Arreglo:** corregir el aviso, o dejar de enviar el diagnóstico. En el correo, no repetir la frase.
12. **tutelas-salud.html usa «tutelas» para dos cosas distintas.** El panel llama «tutelas» a las peticiones (462.361 en 2025; «Entre las N tutelas…», :2895), y el hero da 274.510 tutelas. **Arreglo:** escribir «peticiones de tutela» en el panel.
13. **El margen de la 2ª vuelta cambia según la página:** 247.586 en presidencial-2026 (escrutinio), 248.050 en los índices de analisis-candidato (preconteo) y «250.830» escrito a mano en `voto-fusil-2026.html:92` y «250 mil» en :136. **Arreglo:** citar el escrutinio en voto-fusil o aclarar la fuente.
14. **La pantalla de carga de analisis-candidato tiene dos errores.** Dice «Paloma Valencia… consulta de **2022**» y fue la de 2026 (:2906, :2925, :2944). Y dice «la votación más alta es la de Petro 2022: 11.292.758», cuando De La Espriella 2026 sacó 12.950.642 (:2913, :2932, :2951). **Arreglo:** corregir las dos frases en los tres idiomas.
15. **bogota-1v-barrios.html: la vista previa dice otra cosa que la página.** La meta y el og dicen «361 barrios / 196» (:5, :7) y la página dice 435/223. `noticias.html:340` dice 412/213. Al compartir el enlace del correo saldrá la cifra vieja. **Arreglo:** poner 435/223 en los tres sitios.
16. **voto-fusil-2026.html: `og:image` con ruta relativa** (:10). Al compartir no sale imagen. **Arreglo:** usar la URL absoluta.
17. **policia.html: las 3 imágenes de las tarjetas no existen** (`imagenes/policia-{mapa,historico,abiertos}.jpg`, :80, :88, :96). **Arreglo:** subirlas.
18. **La home dice «Delitos 2015-2024»** (`index.html:629`, más :712, :793, :876 en las otras lenguas), y los datos llegan a ago-2026. **Arreglo:** «2015–ago 2026».
19. **legislativo-historico.html: la fila 2026-2030 dice 205 proyectos** (`CUAT_PL` y `CUAT_AL`, :177-178, de agosto), mientras el hub dice 639. **Arreglo:** regenerar la fila o leerla de `ritmo-legislaturas.json`.
20. **legislativo-en-vivo.html: 12 de 15 resúmenes del Senado se hicieron solo con el título** (`explica.base = "titulo"`), aunque la fila diga «● Texto disponible» (:118). **Arreglo:** pasar OCR a los PDF o cambiar el rótulo.
21. **El botón «Descarga Excel» no hace nada, ni pagando:** `console.log('TODO excel export')` en presidencial-2026.html:1247, presidencial-2010.html:1242 y consultas-pacto-2025.html:1242. **Arreglo:** implementarlo (como en senado-2022.html:2241-2300) o quitarlo.
22. **electoral.html promete el escrutinio presidencial «hasta puesto»** (:1539, :1549), pero el visor llega solo a zona/comuna. **Arreglo:** cambiar el texto. En el correo, no decir «por puesto» de esa página.
23. **pricing.html promete por plan algo distinto de lo que hacen las páginas.**
    - El «−20 %» anual es inexacto (:339, :388, :1138): el ahorro real es 25,0 % en Pro y 18,3 % en Premium (cálculo propio: 59.900/79.900 y 179.000/219.000).
    - Pro incluye «barrios» (:423), pero en Veleta son Premium (veleta.html:691-692).
    - Los puestos aparecen como Premium (:472), pero en los tableros 2023 son Pro.
    - El plan Básico sale con «—» en detalle territorial, aunque el usuario gratis sí ve comunas y municipios.
24. **Extorsión 2023 en Policía:** 33.466 según SIEDCO (`S3/ponal/nacional.json` `.por_anio.extorsiones[8]`) frente a 11.078 según MinDefensa, sin ninguna nota en la página. **Arreglo:** añadir una nota de calidad. Mientras tanto, no usar extorsión en el correo.
25. **quien-quiere-ser-juez.html:**
    - Faltan los 8 mp3 de `quien-quiere-ser-juez/audio/` (:538-547).
    - El registro y el ranking dependen de la cuota de escrituras KV del worker. SIN VERIFICAR: revisar la cuota antes del envío.
26. **descargas.html: la fila CITREP del selector por departamento** (:1068) ofrece archivos que no existen en 15 departamentos (dan 403). Afecta solo a quien paga.

### ⚪ Cosméticos

- El plan gratis se llama «Free», «Plan Free» o «Básico» según la página. Aparece como «Free» en legislativo-base.js:81, analisis-candidato.html:1211, presidencial-2026.html:1244, descargas.html:1599 y pricing.html:1289, y como «Plan Free» en resultados-*-2023.html:1029. **Unificar en «Básico».**
- Hay tres cifras de «proyectos desde 1990»: 14.055 (legislativo.html:149), 13.831 (legislativo-historico.html) y «más de 10.600» (legislativo-en-vivo.html:86, legislativo-proyectos.html:55).
- El respaldo de legislativo-historico.html:107 dice 18,5 %; el dato da 18,4 %.
- legislativo.html:110 dice «lectura **exclusiva** de deuda», pero es gratis.
- En pgn-2027.html:66, «−$1,5 B en inversión» no cuadra con `YEARS` (−1,4).
- 1.111 municipios en el texto frente a 1.112 en el dato (policia.html:71, policia-mapa.html:8). «127 conjuntos» frente a 63 listados (policia-abiertos.html:151, :339, :530; policia.html:98). «Las tasas llegan hasta 2018» debería decir «arrancan» (policia-historico.html:490).
- edades-1v.html:141: «40,5 % → 41,2 %» no cuadra con el CSV publicado (40,92 % de válidos). SIN VERIFICAR qué base usó el modelo.
- ciudades-2v-barrios.html:95 y :120 anuncian 8 ciudades; hay 14. Bogotá en 1V da 406/211 aquí y 435/223 en bogota-1v-barrios (cruces distintos).
- En presidencial-2010.html:340 y consultas-pacto-2025.html:340 el pie dice «Elecciones Colombia 2026».
- senado-2022.html: falta la nota de las curules de Comunes, y el modo día aparece de 7 a 19 h.
- presidencial-2026: los porcentajes se calculan sobre válidos con blanco, pero la tabla no tiene fila de blanco (el ganador sale con 49,66 %).
- atipica.html:9 dice «escrutinio», y Tunja y Cartago son preconteo. En atipica-{tunja,cartago}-2026.html:53, «Volver» lleva a electoral.html y no a atipica.html.
- descargas.html:774 dice «118.350 mesas», pero el CSV suma 118.313 (SIN VERIFICAR cuál es la buena). En :775 menciona un botón de WhatsApp que ya no existe.
- En los tableros 2023, «Votos válidos» excluye el blanco (:728). En resultados-asamblea-2023.html:380, el selector dice «Ciudad» sin JS.
- legislativo-en-vivo: el resumen del PL 412/2026C contradice su fecha, y el PL 410/2026C es un acto legislativo dentro del feed de proyectos de ley.
- En mi-congreso.html:164, el primer ejemplo (Wilson Arias, lista cerrada) muestra el caso con menos datos.
- pensamiento-investigativo.html:634: «Escríbame» lleva a index.html.
- analisis-candidato.html:1154: `MUNICIPIOS.json` da 403, pero es código muerto.

### Nota fuera del alcance del correo

El repo es público y el código de algunas páginas incluye listas de correos personales en claro: `descargas.html:1187-1195` (`ADMIN_EMAILS`, `FULL_ACCESS_EMAILS`, `FILE_GRANTS`) y `dashboard.html` (`allowedEmails`). No los copio aquí. Conviene moverlos al worker, como se hizo con CLAUDE.md.

---

## Anexo: fichas por página

Detalle completo de las 33 páginas: fuentes con estado HTTP, rutas exactas, gates con archivo:línea, ganchos alternativos y propuestas de arreglo. Una corrección respecto a lo que dicen las fichas sobre `track.js`: la mayoría de las páginas lo cargan a través de `theme.js` (theme.js:88-92). La lista válida de páginas sin medición es la del punto 10 de (c).


### Grupo: elecciones-resultados (frente Elecciones)

Auditado sobre el repo en HEAD 59405dc (= lo publicado en GitHub Pages). S3 consultado el 2026-10-10 con `curl -sS --compressed`.

Prefijo S3 usado abajo: `S3OUT = https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output`
y `S3DL = https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/DESCARGAS`.

Notas generales del grupo:
- Ninguna de las 9 páginas carga `plan-gate.js`, `track.js`, `data-client.js` ni `platform-config.js`. Cada una tiene su chequeo propio (`rr-token` / `rr-user.plan`), o ninguno.
- Enlaces internos: revisé todos los `*.html` citados en las 9 páginas. **Ninguno roto** (todos existen en el repo).
- Mapas compartidos (`S3OUT/mapas-2026/DEPARTAMENTOS2.json`, `Departamentos-mps/NN.json`, `Ciudades-COM-LOC/*X.json` y `zona-comuna.json`): todos responden **200**.

---

#### presidencial-2026.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/presidencial-2026.html (desde electoral.html: `?c=1v` en electoral.html:1539 y `?c=2v` en electoral.html:1549)
- Fuente de datos: `S3OUT/pres-escr/2026/resumen.json` (200), `S3OUT/pres-escr/2026/deps.json` (200), `S3OUT/pres-escr/2026/dep-NN.json` (los 34 responden 200 al HEAD, incluido `dep-88` = Consulados). Las carga presidencial-2026.html:460 y :468.
- Datos hasta: **1ª vuelta (31-may-2026) y 2ª vuelta (21-jun-2026), las dos**: `resumen.json .consultas[]` trae `clave:"1v"` y `clave:"2v"`. Es el escrutinio de comisiones de los 33 departamentos; el exterior sale del preconteo, como dice la etiqueta de fuente (presidencial-2026.html:278). El JSON no trae fecha de corte. Last-Modified de resumen.json y deps.json: **Thu, 08 Oct 2026 04:38:19 GMT**.
  - Contraste: los CSV de descargas `S3DL/ESCRUTINIO_1V_2026_PUESTO.csv` y `S3DL/ESCRUTINIO_2V_2026_PUESTO.csv`, sumados columna por columna (cálculo propio), dan **exactamente** las mismas cifras por candidato que `resumen.json`.
- Resultado que trae:
  - 1V: De La Espriella 10.350.765 · Cepeda 9.697.799 · Valencia 1.638.922 · Fajardo 1.007.884 (… 11 candidatos). `votos` = 23.650.428 (candidatos + blanco).
  - 2V: **Abelardo De La Espriella 12.951.256 · Iván Cepeda Castro 12.703.670**, blanco 426.828, nulos 220.024, no marcados 29.415. `votos` = 26.081.754 (candidatos + blanco).
- Usuario gratis ve: todo el visor. Puede cambiar de vuelta, ver el mapa (nacional → depto → municipio → comuna/localidad), los KPI, el ranking y el donut. No hay gate de vista. La protección de copia aplica solo al anónimo (presidencial-2026.html:1250).
  Bloqueado: solo el botón «⬇ Descarga Excel», que exige pro/premium/full y muestra el toast «Sólo disponible en plan Pro» (presidencial-2026.html:1246-1247).
- Dato gancho 1: «En la 2ª vuelta, Abelardo De La Espriella ganó por **247.586 votos** (12.951.256 frente a 12.703.670), apenas **0,95 pp**». Fuente: `S3OUT/pres-escr/2026/resumen.json` → `.consultas[1].candidatos[0].votos` y `.consultas[1].candidatos[1].votos`. El margen es una resta (cálculo propio) y es el mismo que la página calcula y muestra en el KPI «Margen 1° – 2°» (presidencial-2026.html:752): 247.586 y 0.95 pp = 247.586/26.081.754. Fecha del dato: escrutinio 2V del 21-jun-2026, archivo del 08-oct-2026. Dónde lo ve el lector: chip «Segunda vuelta» → fila de KPI («Puntero: De La Espriella · 12.951.256 votos · 49.66%» y «Margen 1° – 2°: 247.586»). — **VERIFICADO**
- Dato gancho 2: «Cepeda ganó en **19 de los 33 departamentos** (Bogotá incluida: 2.234.979 frente a 1.933.644) y aun así perdió la Presidencia». Fuente: `S3OUT/pres-escr/2026/deps.json` → para cada `.[]` con `cod != "88"` se toma el ganador de `."2v".candidatos`: 19 Cepeda, 14 De La Espriella. Es un conteo propio. Bogotá = `.[] | select(.cod=="16") ."2v".candidatos`. Dónde: mapa en «Segunda vuelta» con «Ganador por territorio» (vista por defecto); el detalle de Bogotá sale al hacer clic en el departamento. — **VERIFICADO** (conteo propio)
  - Extra, no visible en la página: en el exterior De La Espriella sacó 382.064 y Cepeda 208.561 (`deps.json .[]|select(.cod=="88")."2v"`). Esa diferencia de 173.503 (cálculo propio) es el 70 % del margen nacional. El visor no lo muestra porque `DEPARTAMENTOS2.json` tiene 33 polígonos y ninguno es el exterior. Sí está en el CSV de descargas. Úsalo solo si el correo enlaza a la descarga.
- Problemas:
  - [IMPORTANTE] electoral.html promete «Comisiones escrutadoras · **hasta puesto**» (electoral.html:1539 y :1549), pero el visor llega solo a zona/comuna: en el nivel zona `children: []` (presidencial-2026.html:654) y el JS no usa `puestos` en ninguna parte. Los datos sí traen puestos (`dep-NN.json .municipios[].zonas[].puestos[]`). Arreglo: cambiar el texto a «hasta comuna/zona» o añadir el nivel puesto. En el correo no decir «por puesto» para esta página.
  - [IMPORTANTE] El botón Excel no hace nada ni con plan Pro: después del gate solo ejecuta `console.log('TODO excel export')` (presidencial-2026.html:1247). Al usuario free solo le sale el toast de Pro. Arreglo: implementarlo como en senado-2022.html:2241-2300, o quitar el botón.
  - [COSMÉTICO] Los porcentajes se calculan sobre válidos con blanco, pero la tabla no tiene fila de blanco: en la 2V el ganador sale con 49.66 % y los dos suman 98,37 %. Arreglo: añadir la fila «Voto en blanco» o una nota.
  - [COSMÉTICO] La etiqueta del plan en la nav muestra `free` → «Free» (presidencial-2026.html:1244), mientras que plan-gate lo llama «Básico».

#### presidencial-2010.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/presidencial-2010.html (tarjeta en electoral.html:895)
- Fuente de datos: `S3OUT/pres-escr/2010/resumen.json` (200), `S3OUT/pres-escr/2010/deps.json` (200) y `dep-NN.json` (los 34 dan 200). Cargados en presidencial-2010.html:455 y :463. Es el mismo visor que presidencial-2026, sin el CTA de endoso.
- Datos hasta: escrutinio definitivo de la 1V del 30-may-2010 y la 2V del 20-jun-2010 (presidencial-2010.html:276). Last-Modified: **Thu, 08 Oct 2026 05:09:40 GMT**.
- Usuario gratis ve: todo. Bloqueado: el botón Excel, que pide Pro y, como en 2026, no hace nada (presidencial-2010.html:1242).
- Dato gancho 1: «Santos ganó la 2ª vuelta de 2010 con **9.028.943 votos (69,13 %)** frente a 3.587.975 de Mockus; ganó en 32 de 33 departamentos (Mockus solo en Putumayo)». Fuente: `S3OUT/pres-escr/2010/resumen.json` → `.consultas[1].candidatos[0].votos` y `[1].votos`. El 69,13 % = 9.028.943/13.061.192 (`.consultas[1].votos`) es el mismo cálculo que hace la página. El 32/33 es un conteo propio sobre `deps.json` `."2v"`. Dónde: chip «Segunda vuelta», KPI «Puntero» y tabla; el mapa «Ganador por territorio» muestra a Putumayo como única excepción. CLAUDE.md lo da como «validado contra el oficial» (9.028.943 / 3.587.975). — **VERIFICADO**
- Problemas:
  - [IMPORTANTE] Excel con `TODO` (presidencial-2010.html:1242). Mismo arreglo que en 2026.
  - [COSMÉTICO] El pie dice «ricardoruiz.co · Elecciones Colombia 2026» (presidencial-2010.html:340). Arreglo: «… 2010».

#### senado-2022.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/senado-2022.html (electoral.html:1509)
- Fuente de datos: `S3OUT/senado-2022/resumen.json` (200), `circunscripciones.json` (200), `departamentos.json` (200), `censo.csv` (200) y `departamentos/{dep}/{municipios|puestos|comunas|mesas}.json` (probado con dep 16: los 4 dan 200). Las carga senado-2022.html:573, :581 y :883.
- Datos hasta: escrutinio del Senado del 13-mar-2022. Según `resumen.json .fuente_nacional` es el «consolidado del escrutinio (GCS)». `generado_en` = 2026-10-08T17:30:02Z. Last-Modified: 08 Oct 2026 17:35:45 GMT.
- Usuario gratis ve: todo, hasta mesa, sin toast ni bloqueo de copia/selección; al anónimo esos dos se le bloquean (senado-2022.html:1372, :1376, :2319-2326). Bloqueado: «Descarga Excel», que pide pro/premium/full (senado-2022.html:2241-2245).
- Dato gancho 1: «**Gilberto Tobón** fue el 5º candidato más votado del Senado 2022 (**175.557 votos**) y no llegó al Senado: Fuerza Ciudadana sacó 431.166 votos y el umbral era **509.709**». Fuente: `S3OUT/senado-2022/resumen.json`. Los votos de Tobón están en `.partidos[] | select(.partido=="FUERZA CIUDADANA LA FUERZA DEL CAMBIO") .candidatos[]`. El partido tiene `.votos`=431166 y `.curules`=0, y el umbral está en `.umbral`=509709. El puesto 5º es un ordenamiento propio de todos los `.partidos[].candidatos[]`. Dónde: tabla de partidos (Fuerza Ciudadana con 0 curules, «▸ 83 candidatos» para desplegar) y el bloque «Umbral 3 %» (senado-2022.html:516-517, que se llena en :1023). — **VERIFICADO** en el dato. El orden 5º es cálculo propio.
- Dato gancho 2: «Pacto Histórico: **2.880.254 votos y 20 curules**. La cifra repartidora fue **144.013**». Fuente: `resumen.json .partidos[0]` y `.cifra`. Dónde: tabla nacional y «Cifra repartidora» (senado-2022.html:515). — **VERIFICADO**
- Problemas:
  - [COSMÉTICO] El hemiciclo dice «102 curules · Nacional + Indígena» (senado-2022.html:458) y Comunes aparece con 0. No hay ninguna nota sobre las 5 curules de Comunes por el Acuerdo de Paz ni sobre la del estatuto de oposición; camara-2018 sí la tiene (camara-2018.html:399). Arreglo: copiar esa nota.
  - [COSMÉTICO] Senado 2014/2018/2022/2026 no tienen el script que retira el modo día: de 7 a 19 h theme.js pone fondo claro y el botón «☀ Modo día» queda visible (la regla `.theme-btn` de senado-2022.html:211 no tiene `display:none`). Las demás páginas v2 son siempre oscuras. Arreglo: el mismo bloque «modo dia retirado» de camara-2018.
  - [COSMÉTICO, invisible] El comentario de senado-2022.html:1016 cita «19.478.739 en la declaratoria del CNE», cifra de 2026. El texto mostrado sale bien del JSON (16.990.304).

#### camara-2018.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/camara-2018.html (electoral.html:1503)
- Fuente de datos: `S3OUT/camara-2018/resumen.json` (200), `departamentos.json` (200), `censo.csv` (200), `dep-{NN}.json` (los 33+88 dan 200) y `dep-{NN}/com-{mun}-{zona}.json` (probado `dep-16/com-001-000.json`: 200). Las carga camara-2018.html:695, :703 y :886. (`camara-2018/circunscripciones.json` da 403 porque no existe, pero esta página no lo pide.)
- Datos hasta: escrutinio de la Cámara del 11-mar-2018 (`.fuente_nacional`). `generado_en` = 2026-10-08T19:06:41Z. Last-Modified: 08 Oct 2026 19:07:14 GMT.
- Usuario gratis ve: todo, hasta mesa. El toast de invitación y el bloqueo de copia/selección son solo para el anónimo (camara-2018.html:1330, :1355, :2472-2478). Bloqueado: Excel, que pide Pro (camara-2018.html:1379-1383).
- Dato gancho 1: «En la Cámara 2018 hubo **1.676.352 votos nulos**: casi 1 de cada 10 votantes (9,85 %)». Fuente: `S3OUT/camara-2018/resumen.json .votnul` / `.votant` (17.023.901). El porcentaje es cálculo propio. Dónde: donut de participación, porción «Nulos» (camara-2018.html:949-955). — **VERIFICADO** en el dato; **SIN VERIFICAR** contra el boletín oficial.
- Dato gancho 2: «El representante más votado fue **Edward Rodríguez (CD), con 105.623 votos**; el partido más votado, el Liberal (2.447.321)». Fuente: `resumen.json .partidos[].candidatos[]` (máximo) y `.partidos[0].votos`. — **VERIFICADO** en el dato.
- Problemas: ninguno que bloquee. [COSMÉTICO] La nota del año dice «No incluye las 5 curules del partido FARC…» (camara-2018.html:399). Está bien; solo la registro como referencia para senado-2022.

#### consultas-pacto-2025.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/consultas-pacto-2025.html (`?c=senado` en electoral.html:1175, `?c=camara` en :1184)
- Fuente de datos: `S3OUT/pres-escr/pacto2025/resumen.json` (200), `deps.json` (200) y `dep-NN.json` (los 33 dan 200; no hay fila del exterior). Cargadas en consultas-pacto-2025.html:455 y :463.
- Datos hasta: escrutinio definitivo de las consultas internas del 26-oct-2025 (consultas-pacto-2025.html:276). Last-Modified: 08 Oct 2026 04:38:22 GMT. La suma de deps es igual al total nacional en las dos consultas.
- Qué trae: **solo las consultas de Senado (144 aspirantes, 2.338.922 votos) y Cámara (374 aspirantes, 2.276.487)**. La consulta presidencial del Pacto de ese mismo día **no está** en este visor; solo está como crudo en descargas.
- Usuario gratis ve: todo. Bloqueado: Excel, que pide Pro y no hace nada (consultas-pacto-2025.html:1242).
- Dato gancho 1: «En la consulta al Senado del Pacto, el más votado entre 144 aspirantes fue **Pedro Hernando Flórez, con 185.029 votos** (7,91 %)». Fuente: `S3OUT/pres-escr/pacto2025/resumen.json .consultas[0].candidatos[0]`. El 7,91 % = 185.029/2.338.922 es el cálculo de la página. Dónde: KPI «Puntero» con «Consulta Senado» activa. — **VERIFICADO**
- Problemas:
  - [IMPORTANTE] Excel con `TODO` (consultas-pacto-2025.html:1242).
  - [COSMÉTICO] El pie dice «Elecciones Colombia 2026» (consultas-pacto-2025.html:340).
  - [COSMÉTICO] Si el correo habla de «la consulta del Pacto», aclarar que aquí están Senado y Cámara, no la presidencial.

#### atipica.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/atipica.html (índice) y https://ricardoruiz.co/atipica.html?e=<clave>
- Fuente de datos: el índice está embebido en `ATIPICAS` (atipica.html:103-132). El detalle sale de los JSON del repo `atipicas/{apartado-2025,bucaramanga-2025,duitama-2025,giron-2026,vichada-2025}.json` (fetch en atipica.html:164 con `?v=20261008`). Los mapas vienen de `S3OUT/mapas-2026/Departamentos-mps/{01,07,27,72}.json`: todos 200.
- Datos hasta: la atípica más reciente es Cartago (20-sep-2026). Commit e2fa533 (08-oct-2026). Índice: **28 atípicas** de 2025-2026. Hay resultado para **8** (5 por puesto: Girón, Magdalena, Vichada, Duitama, Apartadó; 3 solo total: Bucaramanga, Tunja, Cartago). Las otras 20 dicen «Sin resultado publicado».
- Usuario gratis ve: todo. No hay ningún gate (ni `rr-token` ni plan) en atipica.html. Bloqueado: nada.
- Dato gancho 1: «La Gobernación del Vichada (15-jun-2025) se definió por **397 votos**: Fulberto Guevara 14.598 frente a Juan Carlos Cordero». Fuente: `atipicas/vichada-2025.json`. La página suma `.puestos[].v` por candidato (atipica.html:176-184) y lo muestra en el KPI «Diferencia con el 2º» (atipica.html:211). Lo recalculé igual. Dónde: atipica.html?e=vichada-2025. — **VERIFICADO**
- Problemas:
  - [COSMÉTICO] El meta description dice «Resultados oficiales… del escrutinio» (atipica.html:9), pero Tunja y Cartago son preconteo. Arreglo: «escrutinio o preconteo».

#### atipica-tunja-2026.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/atipica-tunja-2026.html (electoral.html:1484; atipica.html:105)
- Fuente de datos: cifras embebidas `const R` (atipica-tunja-2026.html:75-87). No hace ningún fetch.
- Datos hasta: **elección del 26-jul-2026, ya con resultado** (no es una página previa). Son los datos del **boletín de preconteo n.º 12 (26-jul-2026, 17:12) con el 100 % de las mesas** (atipica-tunja-2026.html:57, :59 y :70). No hay escrutinio ni resultado por puesto.
- Cuadre interno (cálculo propio): candidatos 41.886 + blanco 1.537 = válidos 43.423; con nulos 423 y no marcados 24 da 43.870, igual a `votantes`. Cuadra.
- Usuario gratis ve: todo (no hay gate). Los dos enlaces de la página llevan a `tunja-atipica.html`, que tiene gate propio (`rr-token`/`PLAN_RANK`, tunja-atipica.html:503-540), y a `tunja-tactico.html`, sin gate. Los dos existen.
- Dato gancho 1: «En Tunja ganó **Rafael Acevedo (ASI) con 10.758 votos: apenas el 24,8 % de los válidos**, 1.541 por encima de Yamir López. Votó el **30,7 %** del censo (43.870 de 142.847)». Fuente: atipica-tunja-2026.html:75-77. Los porcentajes y la diferencia los calcula la página en los KPI (atipica-tunja-2026.html:93-96). — **VERIFICADO** contra el dato embebido; **SIN VERIFICAR** contra la Registraduría, porque el boletín no se puede consultar.
- Problemas: [COSMÉTICO] «← Volver» va a electoral.html (atipica-tunja-2026.html:53) y no a atipica.html.

#### atipica-cartago-2026.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/atipica-cartago-2026.html (electoral.html:1487; atipica.html:104)
- Fuente de datos: cifras embebidas `const R` (atipica-cartago-2026.html:71-76). No hace ningún fetch.
- Datos hasta: **elección del 20-sep-2026, ya con resultado**. Son los datos del **boletín de preconteo n.º 9 (20-sep-2026, 16:45) con el 100 % de las mesas** (atipica-cartago-2026.html:57, :59 y :66). El mesa a mesa no está publicado.
- Cuadre interno (cálculo propio): 30.885 + blanco 895 = 31.780 válidos; con 442 nulos y 77 no marcados da 32.299, igual a `votantes`. Cuadra.
- Usuario gratis ve: todo (no hay gate).
- Dato gancho 1: «En Cartago, el Consejo de Estado anuló la elección de Juan David Piedrahita… y él **volvió a ganar con 17.894 votos (56,3 %)**, 6.524 más que el segundo. Votó el 26,4 % del censo». Fuente: atipica-cartago-2026.html:59 (motivo) y :71-73 (cifras). Los porcentajes salen de los KPI de la página. — **VERIFICADO** contra el dato embebido; **SIN VERIFICAR** contra la Registraduría.
- Problemas: [COSMÉTICO] «← Volver» va a electoral.html (atipica-cartago-2026.html:53) y no a atipica.html.

#### descargas.html
- Frente: Elecciones (centro de descargas)
- URL pública: https://ricardoruiz.co/descargas.html
- Fuente de datos (todas con HEAD el 2026-10-10):
  - 01 Presidencial 2026 por puesto (`S3DL/`): `Resultados_Escrutinio_1V_2026_por_puesto.xlsx` 200 (LM 11-jun-2026), `ESCRUTINIO_1V_2026_PUESTO.csv` 200 (11-jun), `Resultados_Escrutinio_2V_2026_por_puesto.xlsx` 200 (08-oct-2026), `ESCRUTINIO_2V_2026_PUESTO.csv` 200 (08-oct).
  - 02 CNE oficial (`S3DL/oficial-cne/`): `Senado_2026_oficial_CNE.{xlsx,csv}` y `Congreso_2026_elegidos.{xlsx,csv}`, los 4 con 200 (08-oct-2026).
  - 03/04 Congreso por corporación y por circunscripción (`S3DL/descargas_declaradosfin/`): los 9 archivos dan 200 (13-abr-2026).
  - 05 Por departamento: 34 deptos × 5 archivos = 170 URLs. Dan **155 con 200 y 15 con 403**. Todos los 403 son `por_corporacion_depto/CITREP/<DEPTO>_DECLARADOS.xlsx` en deptos sin CITREP: AMAZONAS, ATLANTICO, BOGOTA_D.C., BOYACA, CALDAS, CASANARE, CONSULADOS, CUNDINAMARCA, GUAINIA, QUINDIO, RISARALDA, SAN_ANDRES, SANTANDER, VAUPES, VICHADA.
  - Crudos (`S3DL/raw/…`): las 82 combinaciones que el catálogo `CRUDOS` puede generar (mesa/puesto × csv/xlsx/zip) dan **200**.
- Datos hasta: la 2V presidencial por puesto se actualizó el 08-oct-2026. Las filas cuadran con el visor: el CSV 1V tiene 14.420 filas y el 2V 14.435, igual que la tarjeta, y los totales por candidato son idénticos a `pres-escr/2026/resumen.json`.
- Usuario gratis ve / Bloqueado: **por diseño, el plan free no puede bajar nada.** El gate (descargas.html:1577-1652) define `isPaid` = pro/premium/full (descargas.html:1612). Al no pagado le desactiva `.dl-btn` y `.dept-dl-btn` y a los 1,4 s le abre un modal con candado: «Contenido exclusivo · Tu cuenta no tiene un plan activo. Actualiza a Pro o Premium…» (descargas.html:1628 y :1634). Los crudos quedan `locked` y abren el modal de Plan Datos; con Premium hay 1 archivo de muestra (descargas.html:1210-1226, :1340-1356). La pestaña «Datos por barrio» se vende archivo por archivo (850.000 COP; solo 2 de los 6 productos tienen link de Wompi, descargas.html:1001-1008). Esos links no los probé.
  - **Comportamiento real (por lectura del código, no lo probé en navegador):** la IIFE del gate corre *antes* de que se pinten las tarjetas (`renderGrid` en descargas.html:1657-1660). Cuando busca `.dl-btn` todavía no existe ninguno, así que **las secciones 01-04 quedan con enlaces activos para el free** (y para el anónimo) en cuanto cierra el modal. Eso incluye la Presidencial 2026 1V/2V por puesto, el CNE oficial y el Congreso por corporación y por circunscripción. Solo la sección 05 (por departamento) sí queda desactivada, porque se envuelve `renderDeptGen` (descargas.html:1650).
- Dato gancho 1: «Puedes bajar el escrutinio presidencial 2026 de **1ª y 2ª vuelta por puesto de votación**: 14.420 y 14.435 puestos en Excel o CSV». Fuente: tarjetas `ESC1V` (descargas.html:904-909) y filas reales de los CSV (conteo propio). — **VERIFICADO** en el dato. **No anunciarlo como beneficio del plan gratis** hasta resolver el gate (ver abajo).
- Dato gancho 2: «Lista de los **267 elegidos al Congreso 2026-2030 (102 senadores y 165 representantes)**». Fuente: `S3DL/oficial-cne/Congreso_2026_elegidos.csv` (267 filas: SENADO 102, CÁMARA 165) y la tarjeta en descargas.html:917. — **VERIFICADO**
- Problemas:
  - [BLOQUEANTE para anunciarla a usuarios free] Un free que entre desde el correo ve a los 1,4 s el modal con candado que le dice que su cuenta «no tiene un plan activo» (descargas.html:1626-1634). Propuesta: no mencionar descargas.html en el correo como algo del plan gratis, o antes decidir qué baja el free y ajustar el gate y el texto del modal (p. ej. «Tu plan Básico no incluye descargas»).
  - [IMPORTANTE] El gate no tapa las secciones 01-04 por el orden de ejecución (gate en :1612-1622 y render en :1657-1660), así que free y anónimo bajan esos archivos. Además las URL de S3 son públicas. Arreglo: llamar `renderGrid(...)` antes de la IIFE, o hacer que `renderGrid` reciba `isPaid` y pinte el botón desactivado. Si la intención es regalar la presidencial 2026 al free, hacerlo explícito y quitar el modal en esa pestaña.
  - [IMPORTANTE, solo para pagos] La fila «CITREP» del selector por departamento (descargas.html:1068) aparece en los 34 deptos, pero en 15 el archivo no existe (S3 da 403). Arreglo: mostrar CITREP solo en los deptos que tienen esa circunscripción.
  - [COSMÉTICO] El aviso dice «…a través del botón de WhatsApp» (descargas.html:775), pero la página no tiene botón ni enlace de WhatsApp; el modal viejo se reemplazó, según el comentario de :1496. Arreglo: quitar la mención o enlazar el contacto.
  - [COSMÉTICO] El aviso dice «118.350 mesas» de escrutinio en la 1V (descargas.html:774), pero el CSV publicado suma 118.313 en las filas `fuente=escrutinio` (cálculo propio). **SIN VERIFICAR** cuál es la buena; revisar.
  - [COSMÉTICO] La nav muestra `free` como «Free» y no como «Básico» (descargas.html:1599).

---

### Grupo: elecciones-analisis (frente Elecciones)

Auditado el 2026-10-10 sobre el repo (HEAD 59405dc).
Todas las URL de S3 se comprobaron con `curl -sSI`; las fechas son el Last-Modified.
El worker `rr-auth.reruizc.workers.dev` está BLOQUEADO desde este entorno (CONNECT 403 del proxy), así que no pude probar
`/auth/me` ni `/caudal/api`. Las páginas que lo usan lo tratan como opcional (ver cada bloque).

---

#### analisis-candidato.html
- Frente: Elecciones (también da servicio a Congreso: récord de votos nominales)
- URL pública: https://ricardoruiz.co/analisis-candidato
- Fuente de datos: base `RRData.publicUrl('congreso-2026/output')` = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output` (platform-config.js:9, analisis-candidato.html:1151-1164; registro en cand-index.js:25-75).
  - `presidencial/index-presidencial.json` · 200 · 21-ago-2026 (dentro: `"v":"2026-07-14"`); los JSON por candidato `PRES2V_*.json`/`PRES1V_*.json` dan 200 (15-jul-2026).
  - 29 índices del registro (endoso, asamblea 2011-2023, gobernación/alcaldía 2011-2023, congreso 2014/2018/2022, pres 2010-2022, consu-2022, concejo y JAL 2011-2023): **todos 200**. Last-Modified entre el 21-ago y el 29-sep-2026 (los más nuevos son concejo-2023, jal-2023 y asamblea-2023, del 29-sep-2026).
  - Mapas: DEPARTAMENTOS2.json, Departamentos-mps/{dd}.json, BOG-LOCALIDADX, MEDELLINX, CALIX, PEREIRAX, IBAGUEX, BARRANQUILLAX, MONTERIAX, MANIZALESX, PUESTOS_GEOREF.csv y Divipole-actualizado/COMUNAS_DATA.csv dan 200 (abr-2026). **`mapas-2026/MUNICIPIOS.json` da 403**: ver Problemas.
  - Archivos del repo: `congreso-edades.json` (existe). Opcional: `rr-auth…/caudal/api` (bloqueado aquí; sin él la página sigue funcionando, :2799-2808).
- Datos hasta: el último resultado es la 2ª vuelta presidencial 2026 (21-jun-2026, preconteo; índice presidencial `v` 2026-07-14). El histórico cubre de 2010/2011 a 2026. La última actualización de índices es del 29-sep-2026.
- Usuario gratis ve: buscador completo, ficha, mapa, radar, score e histórico de cada persona. Con sesión (`rr-token`) se desbloquean el detalle municipal (:3655, :4053, :4357; el anónimo ve el overlay `mun-lock-overlay`) y las descargas Excel por **Depto.** y **Municipio** (`canDlLevel`, :3813-3817).
  / Bloqueado: descarga por **Com./Localidad** (exige plan pro/premium/full, `isProOrHigher` :3807-3810), por **Puesto** y por **Mesa** (premium/full, `isPremiumOrFull` :3974-3977) y el botón «Descargar votación excel candidato» (:3980-3996). No usa plan-gate.js: tiene chequeos propios contra `localStorage rr-user.plan`.
- Dato gancho 1: «Paloma Valencia sacó **3.248.589** votos en la consulta de marzo y **1.637.665** en la 1ª vuelta», o sea que conservó el 50,4 % (cálculo propio: 1.637.665 / 3.248.589). Fuente: index-presidencial.json → `.personas[persona=="paloma"].consulta.votos` = 3248589 y `.personas[persona=="paloma"].elecciones[0].votos` = 1637665. Dato del 2026-07-14. El lector lo ve buscando «Paloma» en la barra de histórico bajo la foto («Consulta · 2026» y «1ª vuelta · 2026», renderHistorial :3393-3420). VERIFICADO (el 50,4 % es cálculo propio y la página no lo muestra).
- Dato gancho 2: «**Carlos Fernando Galán** sacó **1.499.734** votos en la Alcaldía de Bogotá 2023, más que el senador más votado del archivo, **Álvaro Uribe** (Senado 2018), con **891.964**». Fuente: `alcaldia-2023/index-alcaldia-2023.json` → `.candidatos[nombre=="CARLOS FERNANDO GALAN PACHON"].votos` = 1499734, y `congreso-2018/index-congreso-2018.json` → `.candidatos[nombre=="ALVARO URIBE VELEZ"].votos` = 891964 (corp «SENADO · 2018»). Índices del 21-ago y el 21-sep-2026. El lector lo ve en la pantalla de carga (analisis-candidato.html:2907) y en las fichas de los dos. VERIFICADO.
  - Alternativa: «437.845 candidaturas reales». Sale de los 29 índices: 439.015 entradas que no son partidos (cálculo propio) menos 537 «REVOCADO(A)» y 633 retiradas, según el propio texto de :2911 y :2917. El total de 439.015 está VERIFICADO; mi conteo de revocadas da 542 por diferencias de filtro, así que la cifra de 437.845 es coherente pero no la reproduje exacta.
- Problemas:
  - [IMPORTANTE] La pantalla de carga dice «Paloma Valencia, con 3.248.589 en la **consulta de 2022**», pero el dato es de la consulta de **2026**: el slug es `PALOMA_SUSANA_VALENCIA_LASERNA_2026-CONSULTAS` en `endoso/index.json`, partido «LA GRAN CONSULTA POR COLOMBIA», y `consu-2022` no la incluye. La propia ficha lo rotula «Consulta · 2026» (:1205). Está en analisis-candidato.html:2906 (y en inglés :2925 y chino :2944). Arreglo: cambiar «2022» por «2026» en los tres idiomas. Además, la misma pantalla puede salir en endoso/comparar si comparten el banco de datos curiosos.
  - [IMPORTANTE] La pantalla de carga dice «La votación más alta es la de Gustavo Petro en la segunda vuelta de 2022: 11.292.758» (:2913, :2932, :2951). Pero la misma página carga a Abelardo 2V 2026 con 12.950.642 y a Cepeda 2V 2026 con 12.702.592 (index-presidencial.json) y les da score 100/99. Arreglo: decir «la más alta antes de 2026» o poner a Abelardo 12.950.642 como máximo.
  - [COSMÉTICO] `MUNICIPIOS_GEOJSON_URL` (:1154) apunta a `mapas-2026/MUNICIPIOS.json`, que da **403**. La función `loadMunicipiosLayer` (:1814) no se llama en ningún sitio, así que hoy no afecta al usuario. Arreglo: quitar la constante y la función muertas, o subir el archivo.
  - [COSMÉTICO] El rótulo del plan en la nav es `plans.free = 'Free'` (:1211, también en/zh). El resto del sitio rotula `free` como «Básico». Arreglo: `free:'Básico'`.
  - [COSMÉTICO] El panel «Cómo votó en el Congreso» depende de `rr-auth…/caudal/api` (:2777). Desde aquí da 403 por política del proxy y no pude verificarlo. Si falla, el panel se oculta sin romper la ficha.

#### edades-1v.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/edades-1v
- Fuente de datos: página estática. No hace fetch de datos; las cifras están en el texto HTML y en 9 PNG del repo, `analisis-edades/01…09_*.png` (todos presentes). Los resultados del modelo (ei-report / ei-final / ei-ciudades) **no están publicados** ni en el repo ni en S3, así que solo pude contrastar el texto contra los gráficos. Carga `/track.js` (:4).
- Datos hasta: preconteo 1ª vuelta del 31-may-2026 (CSV publicado `DESCARGAS/PRECONTEO_1V_2026_MESA_con_Claudia.csv`, 200, Last-Modified 03-jun-2026, `fecha_actualizacion` máx. 2026-05-31 23:30:27) cruzado con la edad de sufragantes de 2022 (Registraduría) y la proyección DANE. Byline del 10-jun-2026 (:111).
- Usuario gratis ve: todo; no hay gate (no hay plan-gate, rr-token ni login). / Bloqueado: nada.
- Dato gancho 1: «Cepeda ganó **~60 %** del voto de 18-25 años (IC 95 %: 54-66) y Abelardo **~79 %** del de mayores de 60 (IC 95 %: 72-85)». Fuente: edades-1v.html:118-124 (hero) y gráfico `analisis-edades/04_perfil_2026.png` (rótulos «60», «Abelardo 79%», «23», «Cepeda 7%»). Dato del 10-jun-2026. El lector lo ve en las tarjetas del hero y en el gráfico «El choque generacional». VERIFICADO contra el gráfico publicado; no hay JSON fuente público para recalcularlo (es estimación por inferencia ecológica).
- Dato gancho 2: «El **49 %** de los votos de Cepeda viene de menores de 36 años; el **38 %** de los de Abelardo, de mayores de 60». Fuente: edades-1v.html:162 y `analisis-edades/06_electorado.png` (Cepeda 21 + 28 = 49; Abelardo 61+ = 38). VERIFICADO contra el gráfico.
- Problemas:
  - [COSMÉTICO] «la izquierda quedó casi clavada en su marca nacional (40,5 % → 41,2 %)» (:141). Con el CSV de preconteo 1V publicado, Cepeda saca 9.680.095 / 23.657.546 válidos (candidatos + blanco) = **40,92 %**, o 41,63 % sobre votos a candidatos (cálculo propio). Ninguna base da 41,2 %. Probablemente es la cifra de la muestra de puestos del modelo. SIN VERIFICAR. Arreglo: aclarar «en los puestos analizados» o usar el total nacional.
  - [COSMÉTICO] «27/33 departamentos donde Cepeda igualó o superó a Petro» (:128, :141) y «18 de 33» / «20 de los 33» / «+25 a +4 en Bogotá» (:134) salen del modelo; no hay dato publicado para verificarlos. SIN VERIFICAR (coinciden con la copia de CLAUDE.md).
  - Enlaces internos (noticias, index, bogota-1v-barrios, medellin-1v-barrios, trasvase-paloma): todos existen. Nada bloqueante.

#### ciudades-2v-barrios.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/ciudades-2v-barrios
- Fuente de datos: `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/prec-2v/ciudades-barrios-2v.json?v=20260623c` (ciudades-2v-barrios.html:132; fetch :277) · **200** · Last-Modified 23-jun-2026 19:51 GMT · 620 KB, con 14 ciudades. La cartografía sale de `.{ciudad}.meta.url` (fetch :208): las 14 URL de S3 (BOG-BARRIOS-CATASTRALES, MEDELLIN_BARRIOS_OFICIAL, …, QUIBDO-BARRIOS) dan **200**.
- Datos hasta: preconteo de 1V (31-may-2026) y 2V (21-jun-2026) por mesa, agregados a puesto y luego a barrio. El JSON es del 23-jun-2026.
- Usuario gratis ve: todo (14 ciudades, toggle 1V/2V, modo Ganador/Cambio, tops). No hay gate. / Bloqueado: nada.
- Dato gancho 1: «En Barranquilla, la 1ª vuelta fue un empate (Cepeda +1,6) y en la 2ª Cepeda ganó por **9,6 puntos**: el mayor giro de las grandes ciudades». Fuente: ciudades-barrios-2v.json → `.barranquilla.meta.m1` = -1.6 y `.barranquilla.meta.m2` = -9.6 (negativo = Cepeda). Votos: `.cep2` = 375178, `.abe2` = 309652, es decir 54,8 % frente a 45,2 % (cálculo propio, igual al que hace la página en :217). Dato del 23-jun-2026. El lector lo ve eligiendo Barranquilla: el panel dice «Cepeda gana la ciudad por 9.6 pts» y «Cepeda amplió su ventaja 8.0 pts» (:220-226), y en el toggle 1ª vuelta sale «por 1.6 pts». VERIFICADO.
- Dato gancho 2: «Cepeda ganó 3 de las 4 grandes en la 2ª vuelta: Bogotá **53,7 %**, Cali **60,6 %**, Barranquilla **54,8 %**. Abelardo ganó Medellín con **66,3 %**». Fuente: `.{bogota|cali|barranquilla|medellin}.meta.cep2/abe2` (Bogotá 2197967/1896249 · Cali 682166/443047 · B/quilla 375178/309652 · Medellín 395320/778757). Los porcentajes son cálculo propio sobre los dos candidatos, con la misma fórmula de la página (:217). VERIFICADO. Extra: Cúcuta da a Abelardo **80,1 %** y **60 de 60** barrios con dato (`.cucuta.meta.abe_gana2` = 60, `.cep_gana2` = 0).
- Problemas:
  - [COSMÉTICO] El subtítulo dice «Explora también Bucaramanga, Soledad, Manizales y Pereira» (:95) y la nota de cartografía enumera solo 8 ciudades (:120). El menú carga 14 (además Cartagena, Cúcuta, Santa Marta, Popayán, Buenaventura y Quibdó, :134). Arreglo: actualizar las dos frases.
  - [COSMÉTICO] Hay incoherencia entre páginas para Bogotá 1V. Aquí, con el toggle 1V, salen **406** barrios Cepeda / **211** Abelardo de **617** con dato (`.bogota.meta.cep_gana1/abe_gana1/n`). En bogota-1v-barrios.html salen **435 / 223 de 658**. Son motores distintos: el override por nombre solo está en la página de Bogotá. Arreglo: una nota en el método o regenerar con el mismo cruce.
  - [COSMÉTICO] No carga `/track.js` (edades-1v sí lo carga). Arreglo: añadir `<script defer src="/track.js">` si se quiere medir el clic del correo.

#### voto-fusil-2026.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/voto-fusil-2026
- Fuente de datos: los datos de las 10 zonas están embebidos en `const ZONAS=[…]` (voto-fusil-2026.html:177-188) y las figuras son PNG del repo `rrss/twitter/voto-fusil-png/` (los 8 existen). Para el mapa usa Leaflet desde unpkg y teselas de CARTO. No consume JSON propio. Contrasté las cifras contra los JSON mesa a mesa de la 2V: `…/congreso-2026/output/presidencial/PRES2V_IVAN_CEPEDA_CASTRO.json` y `…/PRES2V_ABELARDO_DE_LA_ESPRIELLA.json` · ambos **200** · Last-Modified 15-jul-2026.
- Datos hasta: preconteo 2V del 21-jun-2026 (más 1V del 31-may) y prensa de mar-jun 2026. La página no lleva fecha visible; según la copia de CLAUDE.md el análisis se cerró en jul-2026.
- Usuario gratis ve: todo. No hay gate. / Bloqueado: nada.
- Dato gancho 1: «Cepeda sacó el **100 % en 675 mesas**; Abelardo en **81**, de las cuales **64** están en el exterior». Fuente: cálculo propio sobre PRES2V_IVAN_CEPEDA_CASTRO.json `.mesas[].v` y PRES2V_ABELARDO_DE_LA_ESPRIELLA.json `.mesas[].v`, emparejando por (dep, mun, zon, pue, mesa) y contando las mesas con v>0 para uno y 0 para el otro. Salen 675 / 81 / 64 con dep 88. Además, Nariño 253 + Cauca 158 + Chocó 121 = 532, que coincide con el «532 en Cauca/Chocó/Nariño» de CLAUDE.md. Dato del 2026-07-14/15. El lector lo ve en el hero (:83) y en la sección 1 (:92). VERIFICADO.
- Dato gancho 2: «Esas mesas 100 % pesan menos del 0,5 % del voto». Son 84.302 votos de Cepeda sobre 25.653.234 votos a los dos candidatos, un **0,33 %** (cálculo propio con los mismos JSON). La página lo dice en :92 («menos del 0,5% del total»). VERIFICADO. Lo usaría junto con el gancho 1.
- Problemas:
  - [IMPORTANTE] La página está **huérfana**: ningún .html del repo enlaza a `voto-fusil-2026.html`, ni noticias.html ni index.html. Tampoco tiene botón «← Noticias»; solo el logo a index (:73). Quien llegue desde el correo no tiene cómo seguir navegando. Arreglo: añadir una card en noticias.html y el botón de vuelta a Noticias.
  - [IMPORTANTE] `og:image` es una ruta relativa, `rrss/twitter/voto-fusil-png/inversion-territorio.png` (:10). Al compartir el enlace no saldrá imagen de vista previa. Arreglo: usar `https://ricardoruiz.co/rrss/twitter/voto-fusil-png/inversion-territorio.png`.
  - [COSMÉTICO] «Abelardo ganó por 250.830 votos» (:92) y «Abelardo ganó por 250 mil» (:136) es la cifra de control nacional o escrutinio, no la del dato publicado del sitio. Con index-presidencial.json (`.personas[abelardo].elecciones[1].votos` 12.950.642 − `.personas[cepeda].elecciones[1].votos` 12.702.592) el margen da **248.050** (cálculo propio, preconteo). SIN VERIFICAR contra JSON publicado. Arreglo: citar la fuente («escrutinio») o decir «unos 250 mil».
  - [COSMÉTICO] Las cifras «~0,2 % del voto nacional» (:86), «89 tijeras», «976 puestos (7 %)», «42 %», «78 % étnico» y «52 % afro / 27 % resguardo» salen del análisis local (master_unificado_puesto + capas ANT), que no está publicado. Coinciden con los gráficos del repo (inversion-territorio.png, participacion-movilizacion.png) pero no se pueden recalcular. SIN VERIFICAR contra datos.
  - [COSMÉTICO] No carga `/track.js`.

#### bogota-1v-barrios.html
- Frente: Elecciones
- URL pública: https://ricardoruiz.co/bogota-1v-barrios
- Fuente de datos: resultados embebidos `const BARRIOS={…}` (bogota-1v-barrios.html:92, 658 barrios) y `const FILL={…}` (:94, 341 barrios de relleno). Cartografía: `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/BOG-BARRIOS-CATASTRALES.json` (:95) · **200** · 13-may-2026. Descargas (:132-133): `DESCARGAS/Resultados_1V_2026_por_mesa.xlsx` · **200** · 03-jun-2026 · 13,1 MB, y `DESCARGAS/PRECONTEO_1V_2026_MESA_con_Claudia.csv` · **200** · 03-jun-2026 · 11,1 MB · 121.863 mesas. Para comprobar el plan usa `rr-auth.reruizc.workers.dev/auth/me` (:131), que está bloqueado aquí.
- Datos hasta: preconteo 1ª vuelta del 31-may-2026 (la `fecha_actualizacion` máxima del CSV es 2026-05-31 23:30:27). Página publicada el 2-jun-2026 (:62, :89).
- Usuario gratis ve: el mapa, los tops y las **descargas del preconteo nacional por mesa**. El gate es `plan!=='anonymous'` (:134-144); un free con `rr-user` en localStorage ya cuenta como registrado aunque `/auth/me` falle. / Bloqueado: nada para el free; el anónimo ve «Regístrate gratis para descargar» → `elige-plan.html` (:143).
- Dato gancho 1: «Cepeda ganó **435 barrios** de Bogotá y Abelardo **223** en la 1ª vuelta». Fuente: conteo de `.win` en el objeto `BARRIOS` de bogota-1v-barrios.html:92: Cepeda 435, Abelardo 223, 658 en total (cálculo propio = conteo). Dato del 31-may-2026. El lector lo ve en el lead (:66) y en el pie del mapa, «658 barrios con dato directo» (:69). VERIFICADO.
- Dato gancho 2: «Bogotá votó **Cepeda 41,3 %** y **Abelardo 37,4 %**». Fuente: CSV publicado `PRECONTEO_1V_2026_MESA_con_Claudia.csv`, filtrando `cod_departamento=="16"`: Cepeda 1.706.148 y Abelardo 1.543.368 sobre `total_votos_urna` 4.129.804, es decir 41,31 % y 37,37 % (cálculo propio). Lo ve en el lead (:66). VERIFICADO (la base es el total de votos en urna, incluidos los nulos). Extra para la lista: el barrio más Abelardo es **Santa Bárbara Central (Usaquén) 67,0 %** y el más Cepeda **Centro Usme Urbano I 71,7 %**, ambos de `BARRIOS` y mostrados en «Los extremos de cada lado» (:123-128).
- Problemas:
  - [IMPORTANTE] La `meta description` y la `og:description` dicen «Cepeda ganó **361** barrios, Abelardo **196**» (:5, :7), pero el cuerpo y los datos dicen **435 / 223** (:66). Eso es lo que verá quien comparta el enlace del correo. Arreglo: actualizar a 435/223. Además noticias.html:340 dice «412 / 213», que es otra versión vieja; conviene alinearla también.
  - [COSMÉTICO] No tiene `og:image` ni carga `/track.js`.
  - [COSMÉTICO] Hay incoherencia con ciudades-2v-barrios.html en el toggle 1V (406/211 de 617). Ver ese bloque.
  - Enlaces internos (noticias, index, previa-1v, veleta, oportunidad, trasvase-paloma, elige-plan): todos existen.

---

#### Resumen para el editor
Mejores ganchos (todos verificados contra datos publicados):
1. Voto fusil: «675 mesas con 100 % para Cepeda (81 para Abelardo, 64 en el exterior), que suman apenas el 0,33 % del voto». Es cálculo propio con los JSON 2V de S3 (voto-fusil-2026.html:83, :92).
2. Barranquilla pasó de un empate (+1,6) a Cepeda +9,6 en 2V. Cepeda ganó 3 de las 4 grandes (Bogotá 53,7 %, Cali 60,6 %, B/quilla 54,8 %) y Abelardo, Medellín con 66,3 % (ciudades-barrios-2v.json, `.meta.m1/m2/cep2/abe2`).
3. Analisis-candidato: Galán (1.499.734 en Alcaldía 2023) supera al senador más votado del archivo, Uribe (891.964). Paloma: 3.248.589 en la consulta y 1.637.665 en 1V.

Bloqueantes: ninguno. Las 5 páginas cargan, sus fetch dan 200 y el usuario free ve todo el contenido. En analisis-candidato solo quedan bloqueadas al free las descargas por comuna, puesto y mesa.
Importantes antes de enviar: voto-fusil-2026.html está huérfana (nadie la enlaza) y su og:image es relativa. La meta/og de bogota-1v-barrios dice 361/196 en vez de 435/223. La pantalla de carga de analisis-candidato fecha mal la consulta de Paloma (2022 en vez de 2026) y presenta a Petro 2022 como la votación más alta, aunque Abelardo 2026 la supera.

---

### Grupo «congreso» · Frente: Congreso

Auditado el 2026-10-10 (UTC 01:27; en Bogotá aún era el 9-oct, 20:27) sobre el repo en HEAD 59405dc. Fuente de lo publicado: el HTML/JS del repo.
Base S3 = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output`.

**Contexto común a las 5 páginas**
- **Ninguna usa plan-gate.js ni tiene gate por plan.** El único código de sesión es el chip del menú (`legislativo-base.js:68-90`): muestra el plan si hay `rr-token`+`rr-user` y, si no, «Iniciar sesión / Registrarse». Todo el contenido lo ve igual un anónimo, un usuario free o uno Pro.
- La API dinámica (`stats`, `bloqueo`, `radicados`, `congresista`, `medios`) va por `https://rr-auth.reruizc.workers.dev/caudal/api` (`legislativo-base.js:31`). **SIN VERIFICAR desde este entorno:** el clasificador de permisos me negó la petición POST al worker. Por eso, las cifras que salen solo de esa API quedan sin verificar. Las de S3 sí respondieron 200.
- **Caudal:** ninguna de las 5 páginas tiene un enlace visible a `caudal.html`. El nombre solo aparece en código interno: la ruta del proxy `/caudal/api` (`legislativo-base.js:27-31`) y un comentario JS (`legislativo-historico.html:166`). El usuario no lo ve. No hay que mencionarlo en el correo.
- **Actualización automática.** Los workflows `ordenes-legislativo.yml` (cron `0 13,18,23 * * *`, dispara la Lambda `?job=ordenes` y comprueba que `ordenes-vigentes.json` tenga menos de 10 min) y `mi-congreso-alertas.yml` (cron `40 13,23 * * *`) no tienen fecha de fin y corren indefinidamente. `gh run list` muestra todo en verde, pero solo hay unas **2 corridas efectivas al día**, con retraso del scheduler de GitHub. Últimos éxitos: órdenes, 2026-10-09 18:33 UTC; alertas, 2026-10-09 18:57 UTC. `en-vivo.json` y `ritmo-legislaturas.json` **no** salen de ningún workflow del repo: los publica otro proceso, fuera del repo. Aun así están frescos (Last-Modified 9-oct-2026 14:05 y 14:07 UTC).
- **¿Hasta cuándo llegan los datos de la legislatura 2026-2030 (desde el 20-jul-2026)?**
  - Radicados del feed en vivo: Senado hasta el **6-oct-2026** (PL 289/26) y Cámara hasta el **1-oct-2026** (PL 426/2026C).
  - Monitor de ritmo: acumula del 20-jul al **6-oct-2026**. La cifra está consolidada solo hasta el **18-sep-2026** (`ventana.consolidada_hasta`); del 19-sep en adelante es provisional (`ventana.lag_dias` = 21).
  - Órdenes del día publicadas: del **12 al 14-oct-2026** (ventana del feed hasta el 23-oct). El feed es del 2026-10-09T18:33:29Z, con 17 fuentes OK y 0 errores.

---

#### legislativo.html
- Frente: Congreso
- URL pública: https://ricardoruiz.co/legislativo.html
- Fuente de datos (todas 200, comprobado con `curl -sSI`):
  - Ticker «En agenda»: `{S3}/legislativo/ordenes-vigentes.json` (legislativo.html:192) · Last-Modified 9-oct-2026 18:34 UTC.
  - KPI «último radicado»: `{S3}/legislativo/en-vivo.json` (legislativo.html:257) · 9-oct-2026 14:05 UTC.
  - Monitor de ritmo: `{S3}/legislativo/ritmo-legislaturas.json` (legislativo.html:292) · 9-oct-2026 14:07 UTC, `.v` = "2026-10-09".
  - KPIs «proyectos desde 1990» y «% termina en ley»: API `stats` vía worker (legislativo.html:276-284) · SIN VERIFICAR. El respaldo en HTML es 14.055 y 18% (legislativo.html:149,157).
  - Fichas con cifras fijas en HTML: 285 congresistas, 7 comisiones, 15 bancadas, 17 integrantes de Acusación (legislativo.html:125-165).
- Datos hasta:
  - Órdenes del día publicadas hasta el 14-oct-2026 (`.ordenes[].fecha` máx.; `.hasta` = 2026-10-23).
  - Último radicado: 6-oct-2026 (máx. de `.senado[].fecha` y `.camara[].fecha`).
  - Ritmo: 20-jul → 6-oct-2026, consolidado hasta el 18-sep.
- Usuario gratis ve: todo (hub, ticker de agenda, monitor de ritmo y las 9 tarjetas) / Bloqueado: nada. No hay gate (solo el chip de sesión en legislativo-base.js:68-90).
- Dato gancho 1: «**639** proyectos de ley radicados del 20 de julio al 6 de octubre, frente a **381** en los mismos días hábiles de 2022 y **337** en 2018».
  - Fuente: `ritmo-legislaturas.json` → `.series["2026"].total` = 639, `.series["2022"].total` = 381, `.series["2018"].total` = 337. Desglose 2026: `.total_senado` = 277 y `.total_camara` = 362.
  - Fecha del dato: 2026-10-09.
  - Dónde lo ve el lector: leyenda del monitor «El arranque, legislatura contra legislatura», arriba a la derecha del hub. La línea de comparación la calcula el JS de la página (legislativo.html:376-387): «639 proyectos en 57 días hábiles — +258 (+68%) vs 2022 · +302 (+90%) vs 2018 en las mismas fechas. 277 en Senado · 362 en Cámara». Los porcentajes son cálculo de la página: round(100·(639−381)/381) = 68 y round(100·(639−337)/337) = 90.
  - Matiz para el correo: los últimos 21 días son provisionales y pueden subir. Si se cita el +68%, decir «al menos» o «hasta el 6 de octubre».
  - VERIFICADO (JSON y lógica de la página).
- Dato gancho 2: «Esta semana hay **12** órdenes del día publicadas en Cámara y Senado (12–14 oct), de **17** fuentes oficiales».
  - Fuente: `ordenes-vigentes.json` → `.n` = 12 y `.fuentes_ok` = 17 · v = 2026-10-09T18:33Z.
  - Dónde: ticker «En agenda» y botón «Ver 12 agendas».
  - VERIFICADO, pero cambia cada día. Mejor no ponerlo en el correo como cifra fija.
- Problemas:
  - [COSMÉTICO] La tarjeta del PGN dice «activa la lectura exclusiva de deuda». En pgn-2027.html ese interruptor es gratis y abierto a todos, y «exclusiva» sugiere un plan de pago. — legislativo.html:110 — Cambiar por «activa la lectura de deuda».
  - [COSMÉTICO] La tarjeta de Mi Congreso se rotula «Nuevo · para congresistas y UTL». Para el correo a ciudadanos conviene presentarla como «sigue a tu congresista», porque cualquiera puede usarla. — legislativo.html:106-107.
  - [COSMÉTICO] El chip de plan del menú rotula `free` como «Free», mientras plan-gate.js lo rotula «Básico» (plan-gate.js:48). — legislativo-base.js:81 — Unificar en `free:'Básico'`.
  - [COSMÉTICO] El respaldo «14.055 proyectos desde 1990» no cuadra con el respaldo de legislativo-historico.html (13.831) ni con el texto «más de 10.600» de en-vivo y proyectos (ver abajo). Si la API responde, las dos primeras se igualan (SIN VERIFICAR). — legislativo.html:149.
  - [COSMÉTICO] Cobertura del feed de órdenes según `.cobertura`: «Cámara: 14 comisiones y plenaria. Senado: plenaria y comisiones Cuarta, Quinta y Sexta». Faltan la 1ª, 2ª, 3ª y 7ª del Senado. No es un error, pero no prometer «todas las comisiones».

#### legislativo-en-vivo.html
- Frente: Congreso
- URL pública: https://ricardoruiz.co/legislativo-en-vivo.html
- Fuente de datos: `{S3}/legislativo/en-vivo.json` (legislativo-en-vivo.html:102) · 200 · Last-Modified 9-oct-2026 14:05 UTC · `.actualizado` = 2026-10-09T14:03:10Z. Los PDF van en `{S3}/legislativo/en-vivo/{senado|camara}/*.pdf`; probé 281-26.pdf y 412-2026C.pdf y dan 200.
- Datos hasta: Senado, 15 radicados del 25-sep al **6-oct-2026** (PL 289/26 a 275/26). Cámara, 15 radicados del 30-sep al **1-oct-2026** (PL 426/2026C a 409/2026C). Rutas `.senado[].fecha` y `.camara[].fecha`.
- Usuario gratis ve: todo (los 30 proyectos, el resumen en lenguaje llano en un modal, la descarga del PDF, el buscador y la paginación) / Bloqueado: nada. Sin gate.
- Dato gancho 1: «Un proyecto propone un impuesto del **3%** a plataformas digitales y redes sociales para financiar la salud mental».
  - Fuente: `en-vivo.json` → `.camara[]` con `numero` = "417/2026C"; `.explica.titular` = "Crea un impuesto del 3% a plataformas digitales y redes sociales para financiar salud mental"; `.explica.base` = "pdf"; `fecha` = 2026-10-01.
  - Dónde: columna Cámara, primera página (con 5 por página es el 7º, así que queda en la página 2), clic en «Ver resumen».
  - VERIFICADO en el JSON. Es un resumen automático (IA) del PDF, no el articulado. Sale de la cola del feed (solo 15 por cámara) en la siguiente radicación, así que no conviene anclarlo al correo si sale tarde.
- Dato gancho 2 (alternativo): «Los **30** radicados más recientes (15 por cámara) traen todos un resumen en lenguaje llano: qué cambia, a quién le aplica y un "ojo"».
  - Fuente: cálculo propio = número de items con `.explica` en `.senado` (15/15) y `.camara` (15/15).
  - VERIFICADO.
- Problemas:
  - [IMPORTANTE] Senado: 12 de 15 resúmenes se basan solo en el título (`explica.base` = "titulo"), aunque 14 de 15 traen PDF. La fila muestra «● Texto disponible» y el modal dice «solo se conoce el título», lo que se contradice para el lector. Probablemente son PDF escaneados sin texto. — en-vivo.json `.senado[].explica.base` y legislativo-en-vivo.html:118 — Pasar OCR a los PDF del Senado antes de explicar, o mostrar «Texto escaneado» en vez de «Texto disponible».
  - [COSMÉTICO] PL 412/2026C (IVA de tiquetes aéreos): `fecha` = 2026-09-30, pero su `explica.ojo` dice «Apenas se radicó el 9 de septiembre de 2026». — en-vivo.json `.camara[numero=412/2026C]` — Regenerar el resumen o quitar la fecha del prompt.
  - [COSMÉTICO] PL 410/2026C sale en el feed de «proyectos de ley», pero su resumen dice «Es una reforma a la Constitución» (acto legislativo). — en-vivo.json — Filtrar o etiquetar por `tipo`.
  - [COSMÉTICO] La nota dice «más de 10.600 proyectos desde 1990». El hub dice 14.055 y el histórico 13.831. — legislativo-en-vivo.html:86 (igual en legislativo-proyectos.html:55) — Actualizar a la cifra de `stats` o quitar el número.
  - [COSMÉTICO] Fechas con formato mixto en el JSON: Senado usa `2026/10/06` y Cámara `2026-10-01`. La página las normaliza, así que no se ve.

#### legislativo-historico.html
- Frente: Congreso
- URL pública: https://ricardoruiz.co/legislativo-historico.html
- Fuente de datos:
  - API `stats` y `bloqueo` vía worker (`legislativo-base.js:31`; llamadas en legislativo-historico.html:249 y la de `bloqueo` más abajo) · **SIN VERIFICAR** (POST denegado en el entorno).
  - Respaldo embebido: `STATS_FALLBACK` (legislativo-historico.html:168-171), `CUAT_PL` (:177) y `CUAT_AL` (:178).
  - Cifras fijas en HTML: tabla «¿Cuántos proyectos se radicaron en el cuatrienio 2022-2026?» (:121-136) y hallazgos (:142-147).
- Datos hasta: «Corte del histórico: agosto de 2026» (legislativo-historico.html:149, texto de la página). La mortandad y el bloqueo solo se pintan si responde la API; sin ella salen «Sin datos … por ahora».
- Usuario gratis ve: todo / Bloqueado: nada. Sin gate.
- Dato gancho 1: «Solo 1 de cada 5 proyectos termina en ley: **2.467** de **13.387** radicados desde 1990 (**18,4%**)».
  - Fuente: legislativo-historico.html:143 (texto) y `STATS_FALLBACK.embudo_universo` (`radicado`: 13387, `ley`: 2467) en :169. 2467/13387 = 18,43% (cálculo propio, coincide con el texto).
  - Fecha: corte de agosto de 2026.
  - Dónde: tarjeta «1 de 5 · termina en ley» y embudo «Terminó en ley».
  - VERIFICADO contra el HTML. El valor vivo de la API está SIN VERIFICAR.
- Dato gancho 2: «Para el cuatrienio 2022-2026 circulan cifras de 3.447 proyectos de ley. Los únicos son **2.826**: **621** se cuentan dos veces porque pasaron por las dos cámaras».
  - Fuente: legislativo-historico.html:125-127 (tabla), cuadrado con `CUAT_PL` fila "2022-2026" = 2826 (:177). 1.496 + 1.951 = 3.447 y 3.447 − 2.826 = 621 (cálculo propio, cuadra).
  - Cifra cerrada (cuatrienio terminado el 20-jul-2026).
  - Dónde: panel «¿Cuántos proyectos se radicaron en el cuatrienio 2022-2026?».
  - VERIFICADO (HTML).
  - Alternativa: «Ser el 1º del orden del día en comisión: 53% de probabilidad de debate, contra 21% del 4º en adelante» (:145, texto fijo; el gráfico vivo depende de `bloqueo`, SIN VERIFICAR).
- Problemas:
  - [IMPORTANTE] Las tablas por cuatrienio muestran la fila **2026-2030 con 205 proyectos de ley y 3 actos legislativos** (`CUAT_PL`/`CUAT_AL` embebidos, corte de agosto; :177-178). El código dice que `stats` todavía no trae `por_cuatrienio`, así que es casi seguro que ese 205 sigue saliendo. El hub, en la misma sección, dice 639 radicados al 6-oct. — Regenerar `CUAT_PL`/`CUAT_AL` o leer la fila 2026-2030 de `ritmo-legislaturas.json`.
  - [COSMÉTICO] El KPI de respaldo dice «18,5%» (:107), pero el mismo respaldo da 2467/13387 = 18,4% y la tarjeta (:143) dice 18,4%. Cuando la API responde se recalcula. — Cambiar el respaldo a 18,4%.
  - [COSMÉTICO] Si el worker falla, mortandad y bloqueo quedan como «Sin datos por ahora». No hay respaldo embebido como en el embudo.

#### pgn-2027.html
- Frente: Congreso
- URL pública: https://ricardoruiz.co/pgn-2027.html
- Fuente de datos: todo embebido; **no hace ningún fetch**. Objetos `YEARS` (pgn-2027.html:124-129), `ENTITY_TOTALS` (:139) y `ENTITIES` (:140-149), más las cifras escritas en el HTML (:48-103). Fuentes externas citadas (PTE, mensaje presidencial, expediente de Cámara) en :119. No comprobé sus enlaces porque son externos.
- Datos hasta: «Corte: 28 de agosto de 2026» (pgn-2027.html:119).
- Usuario gratis ve: todo (comparador de 4 PGN, interruptor «Mirar solo el pago de la deuda», selector de sector y de entidad) / Bloqueado: nada. Sin gate; el interruptor de deuda es un checkbox libre (:74).
- Dato gancho 1: «El servicio de la deuda pasa de **$100,4 billones** (PGN 2026) a **$155,4 billones** en el proyecto 2027: **+$55,0 billones**. El crédito financia **$238,6 billones**, el **37,6%** del presupuesto».
  - Fuente: `YEARS` en pgn-2027.html:127-128 (`debt` 100.4 → 155.4); textos en :66 y :91. Comprobación propia: 155,4 − 100,4 = 55,0; 150,9 + 87,7 = 238,6; 238,6/634,952 = 37,6%.
  - Fecha: corte del 28-ago-2026.
  - Dónde: sección «2 · La prueba de estrés» y el modo «Mirar solo el pago de la deuda».
  - VERIFICADO contra el HTML. Que coincida con el proyecto oficial está SIN VERIFICAR.
- Dato gancho 2: «El Ministerio de Ambiente cae de **$1,24 B** (2026) a **$0,79 B** en 2027: **−36,3%**».
  - Fuente: `ENTITIES.ambiente.values` (`2026`: 1.240, `2027`: .790) en pgn-2027.html:146. El porcentaje lo calcula `renderEntity` (:162): 0,790/1,240 − 1 = −36,3%.
  - Dónde: sección «8 · ¿Qué entidades ganan espacio?», eligiendo «Ministerio de Ambiente».
  - VERIFICADO (cálculo de la página reproducido).
- Problemas:
  - [IMPORTANTE, casi BLOQUEANTE] **Página congelada al 28-ago-2026 con calendario en futuro.** La cabecera sigue en «En trámite» y la línea de tiempo dice «Antes del 15 sep · Se fija el monto» y «Antes del 25 sep · Primer debate» (:102). Hoy es 10-oct y quedan 10 días para el plazo del 20-oct. Si el monto o el primer debate ya cambiaron la cifra de $634,95 B (no pude verificarlo, el sitio y las fuentes externas están fuera del alcance), el correo anunciaría un dato viejo. — pgn-2027.html:48-50, :102, :119 — Antes de enviar, actualizar el estado del trámite (monto aprobado en comisiones y resultado del primer debate) y la fecha de corte, o no usar el titular «$635 billones».
  - [COSMÉTICO] «−$1,5 B · Inversión frente al PGN 2026» (:66) no cuadra con `YEARS`: 87,0 − 88,4 = −1,4 (:127-128). Probablemente es redondeo de cifras con más decimales. — Unificar.
  - [COSMÉTICO] La sección 5 compara contra el programa «Defensores de la Patria · El milagro de los nunca» (:87-96). Es contenido político sensible: revisar el tono antes de destacarlo en el correo.
  - [COSMÉTICO] La página no carga `lang.js` ni tiene selector de país, a diferencia de las hermanas. No afecta a nadie.

#### mi-congreso.html
- Frente: Congreso
- URL pública: https://ricardoruiz.co/mi-congreso.html
- Fuente de datos:
  - S3, todas 200: `{S3}/legislativo/comisiones-2026.json` (:239; Last-Modified 2-sep-2026, `.v` = 2026-09-01), `{S3}/legislativo/ordenes-vigentes.json` (:240; 9-oct-2026), `{S3}/endoso/index.json` (:241; 21-ago-2026).
  - S3, comprobado con Juvinao: `{S3}/endoso/{slug}.json`, `{S3}/fotos-candidatos/{slug}.jpg`, `{S3}/mapas-2026/...` (:392-394), todos 200.
  - Embebido: `legislativo-electos.js` (285 electos).
  - API vía worker, **SIN VERIFICAR**: `radicados` (:515), `congresista` (:534), `medios` (:571).
  - Alta de alertas: POST `https://rr-auth.reruizc.workers.dev/micongreso/alerta` (:584-609), no probado (escribiría en producción).
- Datos hasta: agenda con órdenes del día publicadas hasta el 14-oct-2026. Composición de comisiones al 1-sep-2026: 103 senadores + 182 representantes asignados (cálculo propio sobre `.comisiones[*].senado|camara`), cuadra con los 285 electos. Proyectos, votos y prensa: SIN VERIFICAR (API).
- **Usuario gratis ve: todo, y no necesita cuenta.** No hay gate de plan ni de login.
  - Elige a cualquiera de los 285 congresistas. La elección se guarda solo en su navegador (localStorage `mi-congreso-v1`, :243 y :308).
  - Ve el tablero completo: agenda de su comisión y de la plenaria, proyectos que firma en 2026-27, voto nominal en plenaria y alineación con la bancada de gobierno, citaciones de control político, prensa de los últimos 30 días, su bancada, y mapa de votación 2026 si su lista fue abierta.
  - **Puede activar alertas por correo gratis y sin iniciar sesión** (:185-205 y :598-621): correo, casilla de consentimiento (Ley 1581) y confirmación por enlace (72 h). Cada correo trae enlace de baja.
  - Límite práctico: **un congresista por suscripción**. Si activa otro, «las alertas pasan a este» (:594). El estado de la alerta se recuerda solo en ese navegador (localStorage `mi-congreso-alerta-v1`).
  - Las alertas (máx. 2 correos al día, solo si hay novedad) avisan cuando un proyecto que firma ese congresista cambia de estado, cuando entra a un orden del día, o cuando su comisión o plenaria publica sesión (tools/mi-congreso/alertas/README.md). El motor corre 2 veces al día y está en verde (último éxito 9-oct 18:57 UTC).
  - Bloqueado: nada. El enlace «Mi ficha electoral» (:379) lleva a analisis-candidato.html, donde el free ve los niveles departamento y municipio, y el nivel comuna exige Pro (analisis-candidato.html:3812-3816).
- Dato gancho 1: «Elige a cualquiera de los **285** congresistas (103 en Senado y 182 en Cámara) y recibe gratis un correo cuando sus proyectos se muevan o entren al orden del día».
  - Fuente: `legislativo-electos.js` (`ELECTOS_RAW`: 285 filas, 103 "S" y 182 "C"; conteo propio) y `comisiones-2026.json` (103/182 asignados).
  - Dónde: buscador «¿Quién eres?» y panel «Alertas por correo».
  - VERIFICADO (conteos). El envío real de alertas está SIN VERIFICAR, aunque el workflow corre en verde.
- Dato gancho 2: SIN VERIFICAR. Las cifras personales (proyectos firmados, % de votos con el gobierno, citaciones) salen de la API, que no pude consultar. Una que sí está en S3: Catherine Juvinao (ejemplo sugerido en la página, :164) aparece con **47.473** votos en 2026 (`endoso/index.json` → registro `slug` = "CATHERINE_JUVINAO_CLAVIJO_2026-CAMARA", `.votos` = 47473). Se ve en el chip «47.473 votos en 2026». VERIFICADO, pero es un dato electoral, no legislativo.
- Problemas:
  - [IMPORTANTE] Toda la parte legislativa del tablero (proyectos, votos, control político, prensa) depende del worker `rr-auth…/caudal/api`. No pude comprobar que responda a anónimos, sobre todo `medios`, que base.js:27-30 describe como «ninguna usa una acción cara». Hay que probar en un navegador real con una cuenta free y sin sesión antes de anunciar la página.
  - [IMPORTANTE] El texto de la página y el hub la venden «para congresistas y UTL» (:150-152, legislativo.html:106). Para 334 usuarios free conviene un ángulo ciudadano («sigue a tu congresista») o un subtítulo que lo diga.
  - [COSMÉTICO] Agenda incompleta para senadores de las comisiones 1ª, 2ª, 3ª y 7ª: el feed de órdenes no las cubre (ver `.cobertura`). Su panel «Mi agenda» solo mostrará la plenaria.
  - [COSMÉTICO] Si el worker devuelve 404 en `/micongreso/alerta`, la página dice «Las alertas por correo se están activando en estos días» (:613). No pude comprobar si la ruta ya está en producción. Probar una alta real.
  - [COSMÉTICO] Senadores de lista cerrada (p. ej. Wilson Arias, ejemplo de la propia página :164) no tienen mapa ni chip de votos. La página lo explica (:374), pero el primer ejemplo sugerido muestra el caso más pobre. Poner primero a Juvinao o a Ape Cuello.

---

### Grupo seguridad-lab — Seguridad (Policía) + Lab y herramientas ciudadanas

Auditoría del 2026-10-10 sobre el repo en 59405dc.
Abreviaturas: `S3P` = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/ponal`,
`S3T` = `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/tutelas`.

**Gate (todo el grupo):** ninguna de las 7 páginas carga `plan-gate.js`, `data-client.js` ni `platform-config.js`, y ninguna
hace chequeos de `plan`/`isPro`/`requireAuth`. Las cuatro de Policía solo leen `rr-token`/`rr-user` para pintar el chip de sesión
(`legislativo-base.js:68-90`). Un usuario free ve el 100 % de estas páginas, igual que un anónimo. La única "pared" que existe es
el registro propio del simulador de juez (ver abajo), que es independiente de la cuenta del sitio.

---

#### policia.html
- Frente: Seguridad
- URL pública: https://ricardoruiz.co/policia.html
- Fuente de datos: `S3P/meta.json` (vía `ponal-base.js:7,14,27`) · 200 OK · Last-Modified 30-sep-2026 23:22 GMT. El KPI «127 conjuntos públicos» está escrito a mano en `policia.html:98`.
- Datos hasta: **agosto de 2026**. Sale de `meta.json` → `.anio_parcial = {anio:2026, hasta_mes:8, ultimo_completo:2025}` y `.v = "2026-09-30"`. Las fuentes son la base PONAL 2015-2024 más SIEDCO 2025 y ene-ago 2026 (`.fuente`).
- Usuario gratis ve: todo (es un hub de 3 tarjetas sin gate). / Bloqueado: nada.
- Dato gancho 1: «10.449.231 hechos denunciados» (la página lo muestra como «10,4 M»). Fuente: `S3P/meta.json` → `.hechos`, corte ago-2026. Se ve en la franja del hero (`policia.html:125`) y en la tarjeta «El histórico en cifras» (`policia.html:121-122`). VERIFICADO.
- Dato gancho 2: «21 delitos en 1.112 municipios, 2015–ago 2026». Fuente: `.delitos | length` = 21 y `.municipios` = 1112, en la franja del hero (`policia.html:126-128`). VERIFICADO, con un matiz: el texto fijo de la página dice 1.111 (ver Problemas).
- Problemas:
  - [IMPORTANTE] Las tres tarjetas usan fondos `imagenes/policia-mapa.jpg`, `imagenes/policia-historico.jpg` e `imagenes/policia-abiertos.jpg`, y **ninguno existe en el repo**. Las tres imágenes dan 404 y las tarjetas salen como cajas planas, a diferencia del hub de Legislativo. — `policia.html:80,88,96` — Exportar las 3 imágenes a `imagenes/` (JPG, como dice `imagenes/.gitignore`).
  - [COSMÉTICO] El texto dice «1.111 municipios», pero la franja que sale del JSON pinta 1.112 (`meta.municipios`). — `policia.html:71`, también `policia-mapa.html:8` — Cambiar a 1.112 o leerlo de `meta.json`.
  - [COSMÉTICO] La meta description dice «Diez millones», cuando el dato es 10,4 M. — `policia.html:10`
  - [IMPORTANTE, fuera de la página] La tarjeta de la home que lleva aquí dice «Policía Nacional · Delitos 2015-2024». Está desactualizada, porque ahora cubre hasta ago-2026. — `index.html:629` (y sus traducciones en `index.html:712,793,876`) — Cambiar a «2015–ago 2026».
  - [COSMÉTICO] El chip de sesión rotula al plan free como «Free», mientras que plan-gate lo llama «Básico». — `legislativo-base.js:81`
  - Sin enlaces a MxD ni al observatorio de la mujer en las 4 páginas de Policía (grep de `mujer*.html`, `observatorio` y `mxd`: 0 resultados).

#### policia-mapa.html
- Frente: Seguridad
- URL pública: https://ricardoruiz.co/policia-mapa.html
- Fuente de datos: `S3P/meta.json`, `S3P/deptos.json`, `S3P/municipios.json` (1,09 MB), `S3P/ciudades.json`, `S3P/poblacion.json`, `S3P/homicidio-modalidad.json` y `S3P/ciudades/{dane}.json` (20 ciudades). Geometrías: `…/congreso-2026/output/mapas-2026/DEPARTAMENTOS2.json`, `…/Departamentos-mps/{01..72}.json` (33 archivos) y `…/Ciudades-COM-LOC/{BOG-LOCALIDADX,MEDELLINX,CALIX}.json`. Todo responde 200/206. Last-Modified: 30-sep-2026 (población 30-sep 22:33; modalidad 01-oct-2026 01:30). Leaflet sale de unpkg@1.9.4.
- Datos hasta: delitos hasta **ago-2026** (`meta.anio_parcial`). Modalidad del homicidio hasta **31-ago-2026** (`homicidio-modalidad.json` → `.corte`). Población DANE de 2018 a 2026 (`poblacion.json` → `.anios`). La tasa solo se calcula para años completos ≥2018 (`policia-mapa.html:223-229`).
- Usuario gratis ve: todo (mapa nacional → departamento → municipio, y comuna/barrio en Bogotá, Medellín y Cali). / Bloqueado: nada.
- Dato gancho 1: «En tasa, el departamento con más homicidios en 2025 fue Guaviare, con 81,5 por 100.000 habitantes (69 homicidios), por delante de San Andrés (63,1), Cauca (53,0) y Valle (50,9)». Fuente: `S3P/deptos.json` → `.deptos["95"].d.homicidios.y[10]` = 69 y `S3P/poblacion.json` → `.deptos["95"].p[7]` = 84.696. La fórmula es 69×100.000/84.696, la misma que usa la página (`policia-mapa.html:249-251`). **Cálculo propio** que replica el de la página. El dato es de 2025. Para verlo: Delito «Homicidios» → Año «2025» → «Ver tasa por 100.000 hab.», y aparece el ranking lateral «Dónde más se denuncia». VERIFICADO (por cálculo; el render en navegador no se pudo probar porque ricardoruiz.co está bloqueado).
- Dato gancho 2: (alternativo) el mismo cálculo para 2022 da Arauca 129,5, Putumayo 59,8, Cauca 55,3 y Chocó 50,7. Coincide con lo que anotaba CLAUDE.md. VERIFICADO (cálculo propio).
- Problemas:
  - [COSMÉTICO] La meta description dice «1.111 municipios», pero el dato es 1.112. — `policia-mapa.html:8`
  - Sin otros problemas detectados: todas las URL de datos y geometrías responden.

#### policia-historico.html
- Frente: Seguridad
- URL pública: https://ricardoruiz.co/policia-historico.html
- Fuente de datos: `S3P/meta.json`, `S3P/nacional.json` (50 KB) y `S3P/homicidio-modalidad.json`. Todo 200. Last-Modified 30-sep-2026 / 01-oct-2026.
- Datos hasta: **ago-2026**. Hay series anuales 2015-2025 completas, más la columna «ene–ago» que compara 2025 con 2026 (`nacional.json` → `.ytd.hasta_mes = 8`).
- Usuario gratis ve: todo (tabla de tendencia, perfil por delito, modalidad del homicidio y notas de calidad). / Bloqueado: nada.
- Dato gancho 1: «Violencia intrafamiliar: 107.265 denuncias de enero a agosto de 2026, contra 93.509 en el mismo tramo de 2025 (+14,7 %). Es la cifra más alta para ese tramo desde 2015». Fuente: `S3P/nacional.json` → `.ytd.por_delito.violencia_intra[11]` = 107265 y `[10]` = 93509. El % lo calcula la página como round(1000×(yb−ya)/ya)/10 (`policia-historico.html:243`). Que sea el máximo desde 2015 es comparación propia sobre `.ytd.por_delito.violencia_intra`. El dato llega a ago-2026. Se ve en la tabla «Qué subió y qué bajó», en la fila Violencia intrafamiliar, columnas «Ene–ago 2025 / Ene–ago 2026 / Cambio». VERIFICADO.
- Dato gancho 2: «Delitos informáticos: 65.685 denuncias de ene-ago 2026 contra 47.056 de ene-ago 2025 (+39,6 %). En 2015 hubo 7.404 en el año entero y en 2025 fueron 69.328 (+836 %)». Fuente: `.ytd.por_delito.del_informaticos[11]` / `[10]` y `.por_anio.del_informaticos[0]` / `[10]`. Los % los calcula la propia página (`policia-historico.html:236,243`). La fila «Delitos informáticos» de la misma tabla los muestra. VERIFICADO.
- Dato gancho extra: «Secuestro: 701 denuncias en 2025, frente a 279 en 2024 y 213 en 2015 (+229 % según la página)». Fuente: `.por_anio.secuestros`. MinDefensa da la misma cifra para 2025: `S3P/mindefensa.json` → `.delitos.secuestros.anio["2025"]` = 701. Ojo: en ene-ago 2026 baja a 239 contra 434 en ene-ago 2025 (−44,9 %). VERIFICADO.
- Problemas:
  - [IMPORTANTE] Extorsión 2023 = **33.466** en SIEDCO (`nacional.json` → `.por_anio.extorsiones[8]`), frente a 11.078 en MinDefensa (`mindefensa.json` → `.delitos.extorsiones.anio["2023"]`), y 8.632 y 12.334 en los años vecinos. Es un pico ×3 que no avisa ninguna nota y que se ve en la curva y en el mapa de 2023. — Datos en `S3P/nacional.json`. La página lo pinta sin aviso en `policia-historico.html:231-262`. — Revisar el lote 2023 de extorsión en el builder o añadir una nota de calidad. Mientras tanto, **no usar extorsión como gancho**.
  - [COSMÉTICO] «Las tasas por habitante llegan hasta 2018» debería decir que *arrancan* en 2018. — `policia-historico.html:490`
  - [COSMÉTICO] El comentario del hub habla de un «archivo cerrado 2015-2024». No es visible. — `policia.html:78`

#### policia-abiertos.html
- Frente: Seguridad
- URL pública: https://ricardoruiz.co/policia-abiertos.html
- Fuente de datos: `S3P/mindefensa.json` (445 KB), `S3P/siedco-mes.json`, `S3P/arma_anio.json`, `S3P/poblacion.json`, `S3P/nacional.json`, `S3P/meta.json`, `S3P/ciudades-mes/index.json` y `S3P/ciudades-mes/{11001,05001,76001,08001,13001,68001,54001,66001,17001}.json`. Estos JSON apuntan a 18 GeoJSON de comuna/barrio que responden todos (uno vive en `…/ricardoruiz.co/bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json`). Todo 200/206. Last-Modified 01-oct-2026 (00:51; el índice de ciudades a las 03:40). Cache-buster `DATA_V='20260930'` (`policia-abiertos.html:380`).
- Datos hasta: MinDefensa al **31-ago-2026** y DIJIN al **31-jul-2026** (`mindefensa.json` → `.corte`). Ciudades mes a mes de 2025-01 a **2026-08** (`ciudades-mes/index.json` → `.meses`). Capturas 2026 rotuladas «ene-jul» (`policia-abiertos.html:1027`).
- Usuario gratis ve: todo (13 secciones: cuadre, ciudades, modalidad, feminicidio, armas, capturas, masacres, mapa, Código de Policía, NNA, inventario). / Bloqueado: nada.
- Dato gancho 1: «Masacres: 72 casos y 260 víctimas de enero a agosto de 2026, frente a 90 casos y 315 víctimas en todo 2025». Fuente: `S3P/mindefensa.json` → `.masacres.anio["2026"]` = {casos:72, victimas:260} y `["2025"]` = {casos:90, victimas:315}. Corte 31-ago-2026 (`.corte.mindefensa`). Que el conjunto de masacres u8eq-92tb tenga exactamente ese corte es SIN VERIFICAR: su ficha dice actualizado 2026-09-16. Se ve en la sección «09 · Masacres y Fuerza Pública», gráfico «Masacres por año», al pasar el cursor. VERIFICADO (cifra en el JSON).
- Dato gancho 2: «Policías y militares asesinados: 174 en 2025, frente a 101 en 2024. Es la cifra más alta desde 2015 (177)». Fuente: `.fuerza_publica.anio.ASESINADO["2025"]` = 174, `["2024"]` = 101 y `["2015"]` = 177. La comparación es propia. Ene-ago 2026: 73. Va en el mismo bloque 09. VERIFICADO.
- Problemas:
  - [COSMÉTICO] «Los 127 conjuntos» (índice) y el KPI «127» están escritos a mano. La tabla de inventario lista 63 (`mindefensa.json` → `.inventario | length`). El texto de la sección lo explica («estos son los que sirven»), pero el ancla del índice promete 127. — `policia-abiertos.html:151,339,530` y `policia.html:98` — Cambiar el ancla a «Los conjuntos útiles» o mostrar «63 de 127».
  - Tiene una sección de feminicidio con datos de MinDefensa (`policia-abiertos.html:233-244`). No enlaza al observatorio MxD y no estorba.

---

#### pensamiento-investigativo.html
- Frente: Lab y herramientas ciudadanas
- URL pública: https://ricardoruiz.co/pensamiento-investigativo.html
- Fuente de datos: ninguna. Es un ensayo estático, sin fetch. Solo usa `localStorage rr-theme` para el tema (`:641-654`).
- Datos hasta: n/a
- Usuario gratis ve: todo. / Bloqueado: nada.
- Dato gancho 1: «Lectura de 15 minutos, sin requisitos previos, con ejemplos en Python y 7 secciones, la última "Un primer proyecto, esta tarde"». — `pensamiento-investigativo.html:219-221,235,604` — VERIFICADO (texto de la página).
- Dato gancho 2: no usar «ese "y otros" resulta ser casi la cuarta parte de los votos» (`:283`): no cita fuente ni elección. SIN VERIFICAR.
- Problemas:
  - [IMPORTANTE] **No carga `track.js`**, así que las visitas que traiga el correo no se medirán. — cabecera de `pensamiento-investigativo.html` — Añadir `<script defer src="/track.js"></script>`.
  - [COSMÉTICO] «Escríbame» enlaza a `index.html`, no a un contacto. — `pensamiento-investigativo.html:634` — Usar `mailto:hola@ricardoruiz.co`.
  - No tiene enlaces de entrada desde la home: solo llega desde `analisis-estructural.html:2103`. Sus enlaces internos (analisis-estructural, problema-publico, mactor, comunicar) existen, y sus 8 anclas también.

#### tutelas-salud.html
- Frente: Lab y herramientas ciudadanas
- URL pública: https://ricardoruiz.co/tutelas-salud.html
- Fuente de datos:
  - Cifras del hero escritas a mano: 274.510 tutelas, +15,7 %, 64,85 %, 89,5 % y 59,2 % (`tutelas-salud.html:506,515-527`). Fuente declarada: «MinSalud, Informe de Tutelas por Vulneración del Derecho a la Salud (abril de 2026), vigencia 2025» (`:532`, `:1200`). No está en el repo ni en S3.
  - Panel «Cómo le ha ido a casos como el tuyo»: `S3T/tasas-tutela-salud.json` (`:2770`) · 200 · Last-Modified **23-jul-2026** · 522 KB. Es el microdato de la Corte Constitucional, conjunto datos.gov.co **g3ma-7zce**, «Pretensiones reclamadas en las tutelas», CC BY-SA 4.0.
  - Autocompletar IPS: `S3T/ips/ips-{cod}.json` (`:1890`) · 206 OK en las muestras 11, 05 y 76 · REPS.
  - Lambdas: «lectura de jueces» `https://flqjezr1ld.execute-api.us-east-1.amazonaws.com` (`:2940`; OPTIONS → 204) y «registro estadístico» `https://8jzog5bhe8.execute-api.us-east-1.amazonaws.com` (`:3271`; OPTIONS → 400, responde).
- Datos hasta: **corte del dato de la Corte: vigencia 2025**. Sale de `.metodologia.ventana_score = ["2025"]`; el JSON se generó el 21-jul-2026 (`.generado`) y trae además una serie 2026 parcial (`.serie_nacional["2026"].n` = 200.818) que la página no usa. Las cifras MinSalud del hero son de la vigencia 2025, en un informe de abril de 2026.
- Usuario gratis ve: todo. La página es «Gratis · sin registro» (`:485`) y no lee la sesión. / Bloqueado: nada. La «revisión automática» de tutelas está anunciada como «muy pronto» (opción 2).
- Dato gancho 1: «En 2025 se radicaron 274.510 tutelas por salud en Colombia, +15,7 % frente a 2024, y el 64,85 % reclama servicios que ya están en el plan de beneficios». Fuente: `tutelas-salud.html:506,515-521`, que cita el informe MinSalud de abril de 2026. Se ve en el hero. SIN VERIFICAR contra el informe original (no está en el repo; solo se comprobó que la página lo dice).
- Dato gancho 2: «En 2025, el 95 % de las peticiones de tutela por entrega de medicamentos registradas por la Corte se resolvieron a favor de quien tuteló (112.712 casos)». Fuente: `S3T/tasas-tutela-salud.json` → `.por_pretension["Entrega oportuna de medicamentos o insumos"]` = {n:112712, p:0.9543}. «A favor» suma concede, concede parcial y hecho superado (`.metodologia.favorable`). Dato de 2025. Dónde se ve: solo dentro del asistente, al elegir el caso «medicamentos». El número exacto depende del departamento y de la protección especial que se marquen (cascada en `:2795-2808`), así que el lector puede ver otro porcentaje. VERIFICADO en el JSON; mejor redactarlo como «más del 90 %», con la cifra nacional `.nacional.p` = 0,9252.
- Problemas:
  - [IMPORTANTE] **Promesa de privacidad más fuerte que lo que hace el código.** La meta description y el hero dicen «tus datos no salen de tu dispositivo» (`:7`, `:510`, `:721`). Pero `registroPayload` envía a la Lambda de registro el diagnóstico (`diag`, hasta 300 caracteres de texto libre), el servicio y la dosis, EPS, IPS, municipio, estrato, régimen y las fechas del caso (`:3281-3303`). Además `lecturaPayload` manda campos estructurados a otra Lambda (`:2943-2960`). El aviso del paso 1 (`:743`) declara una «estadística anónima», pero no menciona el diagnóstico ni las fechas. — Ajustar el aviso para que nombre el diagnóstico (dato sensible de salud) o dejar de enviarlo. **En el correo no repetir «tus datos no salen de tu dispositivo»**: decir «tu nombre y tu cédula no salen de tu navegador», que sí es cierto.
  - [IMPORTANTE] El panel dice «Entre las **N tutelas**…» (`:2895`), pero N cuenta *pretensiones* del microdato: en 2025 suman 462.361 (`.nacional.n`), más que las 274.510 tutelas que el hero cita de MinSalud. Las dos cifras se contradicen a simple vista. — Cambiar «tutelas» por «peticiones de tutela» en el panel. **En el correo no mezclar 274.510 con 462.361.**
  - [COSMÉTICO] Hay dos tasas de éxito con definiciones distintas: el hero da 89,5 % concedidas en primera instancia (MinSalud) y el panel da 92,5 % «a favor» (Corte, que incluye el hecho superado). Conviene una línea que lo aclare.
  - [IMPORTANTE] **No carga `track.js`**: no se podrán medir las visitas que traiga el correo. — cabecera — Decidir si se quiere medir esta página (sería coherente con su promesa de privacidad si se declara).
  - [IMPORTANTE] Página huérfana: ninguna otra página del sitio enlaza a ella (grep sin resultados fuera de sí misma). El correo sería su única puerta de entrada. Conviene añadirla a la home.

#### quien-quiere-ser-juez.html
- Frente: Lab y herramientas ciudadanas
- URL pública: https://ricardoruiz.co/quien-quiere-ser-juez.html
- Fuente de datos: banco de preguntas en el repo, `banco-judicial.js` (cargado como `banco-judicial.js?v=20260813d`, `quien-quiere-ser-juez.html:499`); `.v = "2026-08-13-v4"`. El ranking y las partidas van al worker `https://rr-auth.reruizc.workers.dev/juez/{ranking,partida,save}` (`:504,1098,1113,1294`). **Bloqueado desde este entorno** (CONNECT 403), así que el ranking queda SIN VERIFICAR. Si el worker falla, la página cae a un ranking local que solo muestra al propio jugador (`:1300-1307`).
- Datos hasta: banco v4 del 13-ago-2026. Las cifras del examen real vienen de `banco-judicial.js` → `.examen` (200 preguntas, 4h30, aprueba con 800/1000; instructivo de la Convocatoria 27).
- **Banco (contado con node sobre `window.BANCO_JUDICIAL`)**: **524 preguntas, todas con id único**. Comunes: general 49, aptitudes 34, actualidad 19, comportamental 21. Por sala: civil 68, penal 60, laboral 68, administrativo 60, disciplinario 57, ejecución de penas 42, familia 46. Por dificultad (`n`): 84 de nivel 1, 173 de nivel 2 y 267 de nivel 3. Hay 6 marcadas `f:'oficial'`. **Salas: 8**: Civil, Penal, Laboral, Administrativo, Disciplinario, Ejecución de Penas, Familia y Promiscuo Municipal. Esta última es compuesta (`mezcla: civil+penal+laboral+familia`, `banco-judicial.js:109-112`) y no tiene banco propio. Cargos que se eligen antes de jugar: 4 (empleado, juez municipal, juez de circuito, magistrado).
- Usuario gratis ve: todo el juego. Puede jugar las 30 preguntas en cualquiera de las 8 salas y ve el puntaje sobre 1.000, el desglose por bloque, la retroalimentación pregunta a pregunta y el bloque «Para repasar». / **Requiere registro**: el panel «Tu diagnóstico» sale borroso con 🔒 «Regístrate para ver tu diagnóstico» (`:398-404`, lógica en `:1224-1233`), y aparecer en el ranking también exige registrarse (`:447-470`). **Ojo: no es la cuenta del sitio.** Es un formulario propio que pide nombre, WhatsApp o correo, universidad y el consentimiento de la Ley 1581, y se guarda en `localStorage jz-reg`. La página no lee `rr-token` ni `rr-user` (0 coincidencias), así que un usuario free con sesión iniciada **también** tiene que llenar ese formulario.
- Dato gancho 1: «30 preguntas por partida en 8 especialidades, con 81 segundos por pregunta (el ritmo del examen real: 4h30 para 200 preguntas) y el corte en 800/1000». — `quien-quiere-ser-juez.html:324-333,534` y `banco-judicial.js` → `.examen`. Visible en el inicio del juego. VERIFICADO.
- Dato gancho 2: «Un banco de más de 500 preguntas (524) que citan la norma o la sentencia que las sustenta». Fuente: conteo propio sobre `banco-judicial.js`. **La página no muestra ese número** en ningún sitio, así que el lector no lo puede comprobar. La cabecera de `banco-judicial.js:12` dice 523, uno menos que el conteo real. VERIFICADO como conteo propio; en el correo conviene decir «más de 500».
- Problemas:
  - [IMPORTANTE] Faltan los 8 audios: `quien-quiere-ser-juez/audio/*.mp3` (`:538-547`) no están en el repo (solo está `portada-20260902.png`). Cada efecto da un 404 silencioso y el botón 🔊 no hace nada. — Subir los mp3 o esconder el botón de silencio.
  - [IMPORTANTE] Página huérfana: la home no la enlaza (solo aparece en `dashboard.html` y `admin-juez.html`). Para el usuario del correo, el enlace del correo sería la única entrada.
  - [IMPORTANTE] El ranking depende del worker y de su cuota de KV del plan gratuito (1.000 escrituras/día compartidas por todo el sitio, según CLAUDE.md v5.2). Un pico de tráfico por el correo puede devolver 503 en `/juez/save`, y el registro quedaría solo en el dispositivo. No se pudo comprobar el estado desde aquí (403). — Revisar la cuota o el plan Workers antes del envío.
  - [COSMÉTICO] El texto del correo no debe decir «regístrate en el sitio para ver el diagnóstico»: el registro es el del juego, no la cuenta.

---

### Grupo "plan": lo que pide plan (cierre del correo)

Auditado sobre el repo en 59405dc (HTML del repo = HTML publicado). Fecha de la auditoría: 2026-10-10.
Hosts bloqueados por el proxy del entorno (no se pudo comprobar): `rr-auth.reruizc.workers.dev` (login, /auth/me, /dl, /caudal/api) y `checkout.wompi.co` (los 6 links de pago). Todo lo de S3 respondió 200.

#### Resumen del gate (plan-gate.js)

- `plan-gate.js:47` `PLAN_RANK = {anonymous:0, free:1, basico:1, pro:2, premium:3, full:3}`; `plan-gate.js:60`: una feature que no está en `GATE_FEATURES.plan` queda en 'free'.
- `plan-gate.js:50-53` **PLAN_PRICE confirmado**: Pro `$79.900 COP` "al mes · $59.900/mes pagando anual"; Premium `$219.000 COP` "al mes · $179.000/mes pagando anual".
- Contraste con pricing.html (ES `:417` y `:433`, y lo mismo en EN/CN/BR `:571/:589/:736/:754/:901/:919`): Pro `priceCOP 59900` (anual) / `priceCOPMonthly 79900`; Premium `179000` / `219000`. **Los precios coinciden** en plan-gate.js, pricing.html, veleta.html:712-715, oportunidad.html:1096-1099, brujula-2027.html:476 (solo mensual) y elige-plan.html:165/181 (solo mensual). USD: Pro 39 (anual) / 49 (mensual, calculado como 39/0,8, `pricing.html:1066`); Premium 99 / 124.
- `plan-gate.js:150-155` `requireOrSample`: las muestras gratis solo cuentan para el anónimo. Al usuario `free` le pasa todo lo que pide 'free' y se le abre el modal para lo que pide 'pro' o 'premium'.
- Modal para el usuario free (`plan-gate.js:247,269`): etiqueta "Disponible en Pro/Premium", el precio y el botón → `pricing.html`. Si el worker devuelve 401 (`plan-gate.js:113`), la sesión se borra y el usuario vuelve a ser anónimo, con muestras y "Crear cuenta gratis" → `register.html`.

#### Tabla para el cierre del correo (usuario free con sesión)

| Página | Gratis (Básico) | Pro | Premium |
|---|---|---|---|
| resultados-jal/concejo-2023 | Mapa de 12 ciudades, ganador y participación por comuna/localidad, detalle completo de cada comuna (partidos y todos los candidatos) | Barrios, puestos de votación | Mesa a mesa |
| resultados-asamblea-2023 | 32 departamentos, mapa por municipio, detalle de cada municipio (partidos y candidatos) | Barrios, puestos | Mesa a mesa |
| brujula-2027 | Ficha de cualquier candidatura (sin límite), top 5 barrios por bloque, duelo por edad, medios, datos fríos | Ver los 20 barrios (las "alertas", el "comparador" y el "Excel" son candados sin función) | ("mesa a mesa" y "arquetipos" también son candados sin función) |
| veleta | Nacional → departamento → municipio, los 3 candidatos | 15 ciudades por comuna/UPL, toggle Local/Nacional, Excel 3/mes | Barrios de Bogotá y Medellín, PDF, 10 descargas/mes |
| oportunidad | Los 6 candidatos, capa Oportunidad/Abstención, departamento/municipio, detalle al pasar el cursor | Comunas de 15 ciudades, UPL y barrios de Bogotá/Medellín, transferencias, pesos por fuente, CSV 3/mes | Capa de puestos, reporte PDF, 10 descargas/mes |

---

#### resultados-jal-2023.html
- Frente: Elecciones (territoriales 2023)
- URL pública: https://ricardoruiz.co/resultados-jal-2023.html
- Fuente de datos: `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/jal-2023/resultados-jal-2023.json` (resultados-jal-2023.html:424-426) · 200. Detalle por comuna `…/jal-2023/comuna/{ciudad}-{comuna}.json` (`:789`, p. ej. `11-001-01.json`) · 200. Mapas `…/mapas-2026/Ciudades-COM-LOC/*.json`: los 12 de ciudad y los de barrios comprobados · 200. Barrios de Medellín en `…/bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json` · 200.
- Datos hasta: elección del 29-oct-2023 (Registraduría). Versión del JSON `.v = "2026-09-17"`. Last-Modified 20-sep-2026 18:27 GMT.
- Usuario gratis ve: selector de 12 ciudades (`.cities`, 12 entradas), mapa por partido ganador o participación, KPIs de ciudad, grid de comunas y detalle completo de cualquier comuna: votos por partido y tabla de todos los candidatos. `drill:'free'` en `:437`; la muestra de 1 comuna aplica solo al anónimo (`:806`).
  Bloqueado: selector y mapa de barrios (Pro, `:909-929`), pestaña Puestos (Pro, `:837`, `:974-985`), Mesas (Premium, `:838`, `:991`). `GATE_FEATURES.plan = {drill:'free', barrios:'pro', puestos:'pro', mesas:'premium'}` en `:437`. Lo bloqueado se ve borroso (paywall).
- Dato gancho 1: «En Medellín, Creemos ganó la JAL en 19 de las 20 comunas y corregimientos; solo San Antonio de Prado fue para el Centro Democrático». Fuente: resultados-jal-2023.json, `.data["01-001"].comunas[].partidos[0][0]`, conteo propio (19 Creemos, 1 CD, 20 unidades). Dato del 29-oct-2023. El lector lo ve al elegir Medellín, en el panel "Partido ganador por comuna" (`:735-740`): "PARTIDO POLÍTICO CREEMOS 19". VERIFICADO.
- Dato gancho 2: «En Popayán, el voto en blanco a JAL fue 43.602, frente a 58.622 votos por partidos: 42,7 % del total». Fuente: `.cities[] | select(.key=="11-001") | .blanco` = 43602 y `.validos` = 58622. **Cálculo propio**: blanco/(validos+blanco); excluye nulos. El lector ve los dos números en los KPIs de la ciudad ("Votos válidos" y "Voto en blanco", `:728-729`), no el porcentaje. VERIFICADO (cifras); porcentaje = cálculo propio.
- Problemas:
  - [COSMÉTICO] El KPI "Votos válidos" excluye el voto en blanco (en el JSON, `validos` = suma de partidos), pero en Colombia el blanco es voto válido. Puede confundir a quien compare con la Registraduría. `resultados-jal-2023.html:728` — rotular "Votos por partidos" o sumar el blanco.
  - [COSMÉTICO] En la nav de estos tableros, el usuario free aparece como "Plan Free" (`:1029` `PLAN_LABEL.free='Plan Free'`), mientras plan-gate y pricing lo llaman "Básico". Unificar como "Plan Básico".
  - [COSMÉTICO] Los comentarios del código hablan de "11 ciudades" (`:419`) y electoral.html:1562 también dice "11 ciudades", pero el JSON trae 12. Actualizar el texto de electoral.html.
  - [COSMÉTICO] El gate es de producto, no de seguridad (lo dice el código en `:971-973`): el JSON de puestos y mesas llega completo al navegador del usuario free. Es decisión de producto; solo se anota.

#### resultados-concejo-2023.html
- Frente: Elecciones (territoriales 2023)
- URL pública: https://ricardoruiz.co/resultados-concejo-2023.html
- Fuente de datos: `…/congreso-2026/output/concejo-2023/resultados-concejo-2023.json` · 200 (2,57 MB). Detalle `…/concejo-2023/comuna/{key}.json` (`:790`) · 200.
- Datos hasta: elección del 29-oct-2023. `.v = "2026-09-17"`. Last-Modified 20-sep-2026 08:07 GMT.
- Usuario gratis ve / Bloqueado: idéntico a JAL (mismo código). `GATE_FEATURES` en `:436-437`: drill 'free', barrios y puestos 'pro', mesas 'premium'. Muestra para anónimo en `:807`; candados en `:838-839`, `:910-929`, `:976-983`.
- Dato gancho 1: «En Cali, el Partido de la U ganó el Concejo en 25 de las 37 comunas». Fuente: resultados-concejo-2023.json, `.data["31-001"].comunas[].partidos[0][0]`, conteo propio (U 25, CD 5, Pacto 3, Conservador 2, Liberal 1, Verde 1 = 37). Dato del 29-oct-2023. Se ve en el panel "Partido ganador por comuna" al elegir Cali. VERIFICADO.
- Dato gancho 2 (cruce con JAL): «El mismo día, en Popayán, el voto en blanco pesó 10,0 % en Concejo y 42,7 % en JAL». Concejo: `.cities[]|select(.key=="11-001")` blanco 12907, validos 116368. JAL: 43602 y 58622. **Cálculo propio** con la misma fórmula que arriba. Las cifras absolutas se ven en los KPIs de ciudad de cada tablero. VERIFICADO (cifras); porcentajes = cálculo propio.
- Problemas: los mismos COSMÉTICOS de JAL ("Votos válidos" sin blanco `:729`, "Plan Free" `:1030`). Nada bloqueante. Los enlaces del pie (concejo-2023.html, resultados-jal-2023.html, electoral.html) existen.

#### resultados-asamblea-2023.html
- Frente: Elecciones (territoriales 2023)
- URL pública: https://ricardoruiz.co/resultados-asamblea-2023.html
- Fuente de datos: índice `…/congreso-2026/output/asamblea-2023/resultados-asamblea-2023.json` · 200 (32 departamentos en `.cities`). Por departamento `…/asamblea-2023/dep/{dd}.json` (`:485-489`, comprobados 01, 15, 68) · 200. Detalle `…/asamblea-2023/mun/{dd}-{mmm}.json` (`:779`, comprobado 01-001) · 200. Mapa `…/mapas-2026/Departamentos-mps/{dd}.json` · 200.
- Datos hasta: elección del 29-oct-2023. `.v = "2026-09-17"`. Last-Modified 20-sep-2026 05:26 GMT (índice) y 05:22-05:23 (departamentos).
- Usuario gratis ve: 32 departamentos, mapa municipio a municipio y detalle completo de cada municipio (partidos y diputados). Bloqueado: barrios y puestos (Pro), mesas (Premium). `GATE_FEATURES` en `:436-437`; candados en `:827-828`, `:899-918`, `:965-972`; muestra para anónimo en `:796`.
- Dato gancho 1: «En Antioquia, el Centro Democrático fue el partido más votado a la Asamblea (412.971 votos), pero ganó en menos municipios (33) que el Liberal (36) y el Conservador (35)». Fuente: `…/asamblea-2023/dep/01.json`, `.totals.top_partidos[0]` = ["PARTIDO CENTRO DEMOCRÁTICO", 412971]. Conteos propios sobre `.comunas[].partidos[0][0]` (124 municipios). Dato del 29-oct-2023. El lector ve los conteos 36/35/33 en el panel "Partido ganador por municipio" al elegir Antioquia; **los 412.971 votos del CD no aparecen en la página** (`top_partidos` no se pinta). Para el correo, usar solo los conteos. VERIFICADO.
- Problemas:
  - [COSMÉTICO] El selector dice "Ciudad" en el HTML (`:380`) y JS lo cambia a "Departamento" (`:532`). Sin JS se ve mal; con JS está bien.
  - [COSMÉTICO] Los mismos de "Votos válidos" (`:718`) y "Plan Free".

#### brujula-2027.html
- Frente: Elecciones / herramientas para candidatos 2027 (la página se rotula "Muestra gratuita · borrador", `:279`)
- URL pública: https://ricardoruiz.co/brujula-2027.html
- Fuente de datos (todas 200 salvo la API de medios):
  - Índices de candidaturas vía cand-index.js (`:508`): 29 índices en `…/congreso-2026/output/{endoso,asamblea-*,gobernacion-*,alcaldia-*,congreso-*,pres-*,consu-2022,concejo-*,jal-*}/index-*.json`. Los 29 dan 200.
  - `…/output/huella/huella-territorial.json` (`:516`): `.v = "2026-05-18"`, 2.506 barrios, 1.122 municipios. Last-Modified 18-may-2026.
  - `…/output/edad-1v/edad-geo.json` (`:517`): `.v = "20260729"`. Last-Modified 29-jul-2026.
  - `…/bases+de+datos/indicadores-mun/indicadores-mun.json` (lab-indicadores.js:34): `.v = "20260526"`, `.periodo = [2018,2024]`, 1.108 municipios. Last-Modified 26-may-2026.
  - Medios: `https://rr-auth.reruizc.workers.dev/caudal/api` (`:521`, `:923`). **Bloqueado en este entorno, SIN VERIFICAR**. Además usa el backend de Caudal, que está excluido del correo.
- Datos hasta: resultados electorales hasta 1V-2026; duelo por edad, jul-2026; datos fríos, 2024 (publicados 26-may-2026).
- Usuario gratis ve: buscador y ficha de cualquier candidatura, sin límite (`ficha:'free'` en `:497`; el límite de 3 en `:622` es solo para el anónimo), con mapa y top de territorios. También: barrios donde sobre-indexa cada bloque (top 5 de hasta 20, `:827-841`), duelo y brecha por edad, medios y datos fríos.
  Bloqueado: "Ver los 20 barrios" (Pro, `:841`). Además hay botones-candado **sin función detrás** (`:341-343`, `:417-418`, `:454`): "Ver mesa a mesa" (Premium), "Comparar dos elecciones" (Pro), "Exportar Excel" (Pro), "Alertas semanales" (Pro), "Análisis de tono con IA" (Pro) y "Arquetipos de tu territorio" (Premium). `GATE_FEATURES` en `:495-504`: `{ficha:'free', barrios:'pro', alertas:'pro', mesas:'premium'}`.
- Dato gancho 1: «En Bogotá, entre votantes de 18 a 35 años Cepeda se llevó 73,3 % del duelo con Abelardo en 1ª vuelta; entre mayores de 61, solo 8,5 %». Fuente: `…/edad-1v/edad-geo.json`, `.ciudades["Bogotá"].cep` = [73.3, 56.3, 8.5] (IC95 en `.ic`). Es una estimación por inferencia ecológica, no un conteo, y el correo debe decirlo. v 2026-07-29. Dónde lo ve el lector: modo "Soy candidato nuevo" → ciudad Bogotá → "El duelo por generaciones". La página redondea (`toFixed(0)`, `:887-888`): muestra "73%" en 18-35; en 61+ no rotula el lado izquierdo y muestra "92%" a la derecha. VERIFICADO (JSON); el render redondeado se dedujo del código.
- Dato gancho 2: «Más de 120.000 candidaturas reales» (texto de `:321`). Suma propia de los índices que la página nombra (Concejo y JAL 2023, Asamblea 2023, Congreso 2014/2018/2022, endoso 2026): 94.467 + 13.590 + 3.307 + 1.940 + 2.379 + 2.254 + 2.822 = 120.759. Coincide. Pero la página en realidad busca en los 29 índices: **439.377 registros** (cálculo propio, suma de `.candidatos|length`), con alcaldías, gobernaciones y Concejo/JAL 2011-2019 incluidos. VERIFICADO; el 439.377 es un conteo de registros, no de personas (el registro agrupa por persona en las fuentes no locales).
- Problemas:
  - [IMPORTANTE] Seis botones-candado prometen funciones que no existen. A un Pro o Premium que hace clic, `PlanGate.require` le devuelve true y no pasa nada (`:341-343`, `:417-418`, `:454`). Un usuario free que pague por "alertas semanales" o "mesa a mesa" en Brújula no recibe nada. Además "Comparar dos elecciones" y "Exportar Excel" reusan la feature 'barrios', y "Arquetipos" reusa 'mesas'. Propuesta: no vender Brújula en el correo, o rotular esos candados "Próximamente" y quitarles el upsell.
  - [IMPORTANTE] La página es un borrador sin enlaces entrantes: ninguna página del sitio enlaza a brujula-2027.html (solo hay comentarios de código). Si el correo la anuncia, habría que decidir antes si sale del borrador (badge `:279`, pie de página: "muestra comercial en borrador").
  - [IMPORTANTE] El módulo de medios depende de `rr-auth…/caudal/api` (`:521`). No se pudo verificar aquí, y Caudal está excluido del correo. Si se anuncia Brújula, no destacar "medios".
  - [COSMÉTICO] "Datos fríos actualizados cada mes" (`:470`, CTA) y "alertas cada semana": `indicadores-mun.json` no cambia desde el 26-may-2026 (serie hasta 2024).
  - [COSMÉTICO] Los 3 barrios "borrosos" de la lista bloqueada están renderizados en el DOM (`:840`); no es protección real.
  - [COSMÉTICO] La página no carga track.js ni lang.js (las demás sí), así que las visitas del correo no se medirán.

#### veleta.html
- Frente: Elecciones (presidencial 2026, herramienta previa a la 1ª vuelta)
- URL pública: https://ricardoruiz.co/veleta.html
- Fuente de datos (`veleta.html:735-752`, todas 200): `…/bases+de+datos/output_bloques/{por-mun,por-depto,nacional}.json` (`generado_en 2026-05-13`, LM 13-may-2026); `…/output_ponderador/ponderador-actual.json` (`fecha_corte "2026-05-25"`, LM 25-may-2026); `…/congreso-2026/output/puestos-censos-agg.json` (LM 05-may); `…/output_bloques/ciudades/bogota.json` (LM 13-may); `…/output_ponderador/proyeccion-por-{upl,barrio}-bogota.json` y `…-barrio-medellin.json` (LM 12/13-may); mapas `mapas-2026/*` (LM abr-2026).
- Datos hasta: **25-may-2026**, antes de la 1ª vuelta (ponderador: Cepeda 37,58 %, De la Espriella 28,69 %, Valencia 18,62 %).
- Usuario gratis ve: mapa nacional → departamento → municipios (`nivel-mun:'free'`, `:686`, gate en `:1995`) y cambio libre entre los 3 candidatos (`:687`, `:2423`). Chip "Plan: Básico ↑ Upgrade" → pricing (`:727-728`).
  Bloqueado: ciudades por comuna/UPL/UCG (Pro, `:689`, gate `:1735`; incluye Bogotá, porque el clic en el departamento 16 salta directo a la ciudad, `:1998-2000`), toggle Local/Nacional (Pro, `:690`, `:2392`), Excel (Pro 3/mes, `:693`, `:2881`), barrios de Bogotá y Medellín (**Premium**, `:691-692`, `:1355`, `:1829`), PDF (Premium, `:695`, `:3083`). Descargas: `DL_QUOTA free:0` (`:2498`).
- Dato gancho: no recomiendo ninguno. Es un modelo de "dónde concentrar esfuerzo para ganar la 1ª vuelta" con encuestas al 25-may-2026, y la elección ya pasó. Si se quiere citar algo: `ponderador-actual.json .candidatos.Cepeda.pct = 37.58` (corte 25-may-2026), solo como histórico. VERIFICADO, pero no es un gancho.
- Problemas:
  - [IMPORTANTE] Datos y texto viejos. La página habla en presente de "ganar la 1ª vuelta" (`:489`) y "ponderador 2026" (`:479`), con corte del 25-may-2026. No anunciarla como novedad, o ponerle un aviso de "herramienta archivada · pre-1V".
  - [IMPORTANTE] Incoherencia con pricing. pricing.html:423 promete en Pro "Territorio: ciudades, comunas, UPL y barrios", pero en Veleta los barrios de Bogotá y Medellín son **Premium** (`:691-692`). En Oportunidad los mismos barrios son Pro (`oportunidad.html:1065-1066`). Unificar: o barrios = Pro en Veleta, o matizar pricing.
  - [COSMÉTICO] `descarga-xlsx-quota` pide 'pro' (`:694`): a un Pro sin cuota le sale "Disponible en Pro · Empezar con Pro". En Oportunidad el alias equivalente pide 'premium' (`oportunidad.html:1072`). Pasar el de Veleta a 'premium'.

#### oportunidad.html
- Frente: Elecciones (presidencial 2026, previa a la 1ª vuelta)
- URL pública: https://ricardoruiz.co/oportunidad.html
- Fuente de datos (`oportunidad.html:1648-1742`, `:2712-2741`; muestra comprobada, todas 200): `…/output/historicos/{pres-2018-v1,pres-2022-v1,consulta-2025-pacto,consulta-2026-gran,consulta-2026-frente,consulta-2026-soluciones}/por-mun.json` (LM 23-24-abr-2026); `historicos/pres-2022-v1/por-puesto.json` (LM 04-may); `senado/departamentos.json` y `camara/municipios.json` (LM 14-abr); `puestos-censos-agg-{2018,2022}.json`, `censos-puesto-2026.json`, `puesto-context.json` (LM 13-may); `puestos-nacional-light.json` (LM 05-may); ponderador (corte 25-may-2026); mapas de ciudad (BOG-UPL, BARRANQUILLAX, CARTAGENA-UCG, PEREIRAX, SINCELEJOX) · 200.
- Datos hasta: consultas del 8-mar-2026 y ponderador al **25-may-2026**, antes de la 1ª vuelta.
- Usuario gratis ve: cambio entre los 6 candidatos (`:1060`, `:5692`), capa Oportunidad/Abstención (`:1062`, `:5921`), departamento/municipio (`:1063`, `:3823`, `:5990`) y detalle al pasar el cursor (`:1064`).
  Bloqueado: Pro → comunas de 15 ciudades (`:1065`, `:4990`), UPL y barrios de Bogotá (`:1066-1067`, `:4620-4621`), barrios de Medellín (`:1068`, `:4315`), transferencia intra-bloque (`:1069`, tarjeta con candado `:929`), pesos por fuente (`:1070`, `:946`), CSV 3/mes (`:1071`, `:1293`). Premium → capa de puestos (`:1074`, `:5920`) y reporte PDF (`:1075`, `:1467`). `DL_QUOTA free:0` (`:1175`).
- Dato gancho: no recomiendo ninguno, por la misma razón que Veleta (modelo pre-1V).
- Problemas:
  - [IMPORTANTE] Herramienta pre-1V con datos al 25-may-2026. Ver Veleta.
  - [COSMÉTICO] Los barrios son Pro aquí y Premium en Veleta (ver arriba).

#### pricing.html
- Frente: transversal (planes)
- URL pública: https://ricardoruiz.co/pricing.html
- Fuente de datos: embebida (i18n en `pricing.html:380-1000`). Sin S3. Pago: `WOMPI_LINKS` en `:1077-1080`.
- Datos hasta: N/A.
- Usuario gratis ve: la tarjeta Básico como "Plan actual", deshabilitada (`:1119`, si `user.plan==='free'`). Los botones Pro y Premium llaman a `startPayment` (`:1082-1107`): con sesión → Wompi directo con `customer-email` y `reference`; sin sesión → `register.html?next=pay` (`:1095`).
- Enlaces: register.html, login.html, elige-plan.html, dashboard.html, descargas.html, index.html, /track.js y lang.js existen. WhatsApp para Personalizado. Wompi `checkout.wompi.co/l/{Ds08zS,2Kdoxx,E1ZVCn,XWAdkz}`: **bloqueado en este entorno, SIN VERIFICAR** que respondan ni sus montos.
- Problemas:
  - [BLOQUEANTE para el upsell, a confirmar] **login.html usa otros links de Wompi**. Un usuario sin sesión que hace clic en "Empezar con Pro/Premium" pasa por register.html?next=pay; si ya tiene cuenta, entra por login.html, que lo manda a Wompi con `WOMPI_LINKS` propios (`login.html:804-807`): mensual Pro `PLslXs`, mensual Premium `YIczAd`. pricing.html usa `Ds08zS` y `E1ZVCn` (`:1078-1079`). Según la copia de CLAUDE.md, los mensuales vigentes son `Ds08zS`/`E1ZVCn`, y un link que no está en `LINK_PLAN_MAP` del worker da `unknown_link_id` y **no activa el plan**. Los 334 usuarios del correo tienen cuenta: los que tengan la sesión vencida caen justo en este flujo. Arreglo: poner en login.html:805-806 los mismos links que pricing.html (mejor aún, sacar `WOMPI_LINKS` a un .js compartido) y confirmar en el worker. Los links anuales `2Kdoxx`/`XWAdkz` son iguales en ambos archivos, pero la copia de CLAUDE.md (jul-2026) los marcaba "TODO: rotar". Estado actual SIN VERIFICAR.
  - [IMPORTANTE] "−20%" en el toggle anual (`:339`, `:388`) y "20% de ahorro vs mensual" (`:1138`) son inexactos. Cálculo propio: Pro 59.900/79.900 = 25,0 % de ahorro; Premium 179.000/219.000 = 18,3 %. Cambiar a "hasta −25%" o mostrar el ahorro por plan.
  - [IMPORTANTE] Pricing promete cosas que las páginas no cumplen igual:
    - Pro "Territorio: … barrios" (`:423`), pero Veleta los pone en Premium.
    - La tabla "Detalle territorial" (`:472`) dice Pro "Ciudades y barrios" y Premium "Puesto y mesa", pero en los tableros 2023 los **puestos son Pro** (`resultados-*-2023.html:437`).
    - En la misma fila, Básico aparece con "—", y el free sí ve el detalle por comuna, localidad y municipio con todos los candidatos en los tableros 2023. Pricing vende por debajo lo gratis.
    - Las "alertas", el "comparador" y el "Excel" que Brújula vende como Pro no figuran en pricing y no existen.
  - [IMPORTANTE] Texto viejo sobre seguridad. ctxDesc (`:397`), FAQ (`:463`) y la tabla (`:475`, "futuro seguimiento de datos de la Policía"), más el ítem Premium "Prioridad en próximas capas, incluido Policía" (`:442`), presentan a la Policía como "próximamente". Pero policia.html, policia-mapa.html, policia-historico.html y policia-abiertos.html ya están publicadas (policia.html modificada el 08-oct-2026) y no tienen gate. Contradice el frente "seguridad" del correo. Actualizar el texto.
  - [COSMÉTICO] Nombre del plan gratis inconsistente: la tarjeta dice "Básico" (`:401`), la nav con sesión dice "Free" (`:1289`, `planLabels.free='Free'`), plan-gate "Básico" y los tableros 2023 "Plan Free". Si el worker devolviera `plan:'basico'`, la tarjeta no se marcaría como "Plan actual" (`:1119` compara con 'free').
  - [COSMÉTICO] Código muerto del "Plan Datos" (`datosTiers`, `renderDatos`): no existe `#datos-tiers` en el HTML, así que no se ve. Sin impacto.
  - [COSMÉTICO] USD: los precios en USD se muestran, pero Wompi cobra en COP.

---
