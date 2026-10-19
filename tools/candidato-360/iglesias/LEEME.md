# Votación al Concejo de Bogotá 2023 y cercanía de iglesias cristianas no católicas

```bash
python3 tools/candidato-360/iglesias/analisis.py            # usa el crudo guardado
python3 tools/candidato-360/iglesias/analisis.py --bajar    # vuelve a pedir OSM y Catastro
```

Salida: `candidato-360-data/iglesias-concejo-bogota-2023.json` (~30 KB).
Crudo (gitignored): `Bases de datos/iglesias-bogota/`.

## La pregunta

¿La votación de un candidato se concentra en los puestos que tienen más
iglesias cristianas no católicas cerca? Se responde para diez candidatos al
Concejo de Bogotá 2023: cinco de partidos o coaliciones de base cristiana
(Bogotá Más Fuerte, MIRA dentro de la coalición CR-MIRA-U, Colombia Justa
Libres dentro de la coalición Conservador-CJL) y cinco controles de votación
parecida sin base religiosa (Centro Democrático, Liberal ×2, Nuevo
Liberalismo, Alianza Verde). La lista y su grupo están en `CANDIDATOS`.

**Regla del producto (candidato-360.md §3):** se describe el territorio de los
puestos, nunca a los votantes. Es correlación ecológica. Que un puesto tenga
iglesias cerca no dice quién votó ni por qué; no se puede escribir «los
evangélicos votaron por X».

## Fuentes

| Qué | De dónde |
|---|---|
| Templos | OpenStreetMap vía Overpass, `amenity=place_of_worship`, recuadro 3,70-4,85 N / 74,50-73,90 O (cubre Bogotá, Sumapaz y los municipios vecinos: un templo al otro lado del límite también es vecino de un puesto) |
| Auditoría de cobertura | Catastro Bogotá · Nombre Geográfico, clase `CULT`, sin los registros cuya fuente es OSM |
| Votos por candidato | Fichas mesa a mesa en S3 `concejo-2023/<slug>.json` (caché en `Bases de datos/iglesias-bogota/candidatos/`), cotejadas contra GCS_2023TER |
| Válidos por puesto | `Bases de datos/arquetipos-bogota/raw/ter2023.json` (de GCS_2023TER, Concejo COD_COR 4): candidatos + voto de lista (COD_CAN 0); sin blanco, nulos ni no marcados. Total 2.437.317 |
| Coordenadas | `PUESTOS_GEOREF.csv` (corte 2026), clave zona-puesto |
| Estrato | Estrato medio del barrio del puesto: `bogota-puesto-barrio.js` + `arquetipos-bogota/barrios.csv` |

## Clasificación de templos

1. Nombre de Testigos de Jehová, Santos de los Últimos Días u ortodoxa →
   **otra cristiana** (no entra a la medida: otra tradición y otra relación con
   lo electoral). Va antes de la denominación porque hay templos SUD etiquetados
   `evangelical` en OSM.
2. `denomination` catholic/roman_catholic → **católica**.
3. `denomination` evangélica, pentecostal, protestante, bautista, adventista,
   menonita, presbiteriana, luterana, anglicana, cuadrangular… → **no católica**.
4. Por nombre: Parroquia, Capilla, Nuestra Señora, Basílica… → católica;
   Cristiana, Evangélica, Pentecostal, IPUC, Cuadrangular, MIRA, Iglesia de Dios,
   Centro Cristiano, Carismática, Tabernáculo, Asambleas de Dios… → no católica;
   San/Santa/Santo, Sagrado, Divino Niño… → católica.
5. `denomination=christian` sin otra pista → no católica (en Colombia la
   etiqueta «cristiana» genérica casi siempre es evangélica).
6. Sin nombre ni denominación → **desconocida** (se usa en una prueba de
   sensibilidad).

Resultado (base OSM del 19-oct-2026), dentro de Bogotá: 646 templos · 315
católicos · **139 no católicos** · 152 desconocidos · 30 otra cristiana · 10
de otras religiones. En el recuadro completo: 801 · 392 · 171 · 181 · 46 · 11.
De los no católicos de Bogotá, 52 se clasificaron por denominación y 87 por
nombre. La Iglesia de Dios Ministerial de Jesucristo Internacional (asociada
al MIRA) tiene 11 templos mapeados en el recuadro; 105 puestos quedan a 1 km o menos de uno.

## Cobertura de OSM (es incompleto: ojo)

- Cotejo contra Catastro: de 245 templos católicos que Catastro nombra, 185
  (75,5 %) tienen un templo OSM a menos de 150 m; de 40 no católicos, 24
  (60 %). Catastro solo registra templos notables, así que esto **sobreestima**
  la cobertura real de los no católicos: buena parte de las congregaciones
  evangélicas funcionan en locales o casas sin señal en el mapa.
- No encontramos un censo público de templos evangélicos de Bogotá con el que
  medir la cobertura total (se buscó en datos.gov.co y en el portal de datos
  abiertos de Bogotá).
- 307 de 942 puestos no tienen ningún templo no católico mapeado a 1 km; la
  media es 1,4.
- Si OSM mapea mejor unas zonas que otras, eso entra al resultado como ruido o
  como sesgo. La densidad católica va de control en la regresión, en parte
  para absorber «zonas mejor mapeadas».

## Método

- **Unidad:** puesto de votación de Bogotá con coordenada. 942 de 950 puestos,
  98,7 % de los válidos. Fuera: zonas 90 (puesto censo de Corferias) y 98
  (cárceles), que no son un lugar de residencia. 887 tienen estrato.
- **Participación:** votos del candidato / válidos del puesto, en puntos
  porcentuales. No se usan votos absolutos (confundirían tamaño del puesto con
  concentración).
- **Cercanía:** número de templos de cada tipo a 500 m y a 1 km del puesto, en
  línea recta.
- **Spearman** entre participación y templos no católicos (500 m y 1 km), todos
  los puestos.
- **Regresión** por mínimos cuadrados ponderados por válidos del puesto:
  `participación ~ no_católicas_1km + católicas_1km + estrato + estrato²`, errores
  robustos HC1. `coef_reg` = puntos porcentuales de participación por cada
  templo no católico adicional a 1 km. Robustez con efectos fijos de localidad
  (`coef_reg_fe_localidad`) y contando los desconocidos como no católicos
  (`coef_reg_incl_desconocidas`).
- **Razón de cuartiles (el índice presentable):** participación agregada del
  candidato en el 25 % de puestos con más templos no católicos cerca, dividida
  por la del 25 % con menos. Con conteos enteros los cuartiles se empatan en
  ceros (un tercio de los puestos tiene cero), así que el orden se hace con una
  densidad continua (núcleo gaussiano σ = 500 m, hasta 2 km). Cuartil alto:
  236 puestos, en promedio 3,3 templos no católicos a 1 km; cuartil bajo: 236
  puestos, 0. IC 95 % por bootstrap de puestos (1.000 réplicas). **Esta razón no
  controla estrato:** léase junto con la regresión.
- **IDMJI:** participación en los puestos con un templo de la Iglesia de Dios
  Ministerial a ≤1 km contra el resto (`ratio_cerca_idmji_1k`). Pocos templos
  mapeados: indicativo.

## Límites

1. Correlación ecológica: describe puestos, no personas.
2. OSM es incompleto y desigual (ver cobertura). Una ausencia de asociación
   puede ser falta de mapa.
3. El puesto no es la casa del votante, y 1 km es un radio arbitrario (por eso
   se reportan dos).
4. Los templos se concentran en barrios populares y densos; sin el control de
   estrato, cualquier candidato de base popular «sale» cerca de iglesias (pasa
   con un control liberal en este mismo ejercicio).
5. Coordenadas de 2026 sobre puestos de 2023: en Bogotá el código casa en más
   del 95 %, pero no al 100 %.
6. Muchas comparaciones (10 candidatos × varias medidas): un coeficiente suelto
   «significativo» no basta.
