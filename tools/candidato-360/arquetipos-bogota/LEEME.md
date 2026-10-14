# Candidato 360 · arquetipos de voto de Bogotá (v1 · integrado al panel 05 el 14-oct-2026)

Arquetipos de **comportamiento electoral observado**, barrio por barrio, por
corporación (Concejo y Alcaldía 2023). No son la cartografía emocional de
Medellín y Cartagena: aquí no hay estudio cualitativo detrás, solo resultados
oficiales, censo y estrato. Se pueden combinar después, pero no se homologan.

La lectura para discutir (nombres, cifras, mapas, límites) está en
`Propuestas/candidato-360/arquetipos-bogota/borrador.md`.

## Correr

```bash
python3 tools/candidato-360/arquetipos-bogota/extraer.py ter2023   # ~5 s c/u
python3 tools/candidato-360/arquetipos-bogota/extraer.py ter2019
python3 tools/candidato-360/arquetipos-bogota/extraer.py jal2019   # trayectoria (ex candidaturas a JAL)
python3 tools/candidato-360/arquetipos-bogota/extraer.py jal2023   # para cuando se hagan los de JAL
node    tools/candidato-360/arquetipos-bogota/familias.mjs         # familia política (partidos-bloques.js)
python3 tools/candidato-360/arquetipos-bogota/medir.py             # variables por barrio
python3 tools/candidato-360/arquetipos-bogota/arquetipos.py        # tipologías + mezcla + confianza (~6 s)
python3 tools/candidato-360/arquetipos-bogota/validar.py           # 2019 vs 2023, casos conocidos, voto cruzado
python3 tools/candidato-360/arquetipos-bogota/mapas.py             # PNG del borrador
python3 tools/candidato-360/arquetipos-bogota/publicar.py          # lo que lee el panel 05
```

**Publicar** (lo lee `candidato-360-arq-lectura.js`; los dos van comprimidos y
verificados byte a byte contra el local):

```bash
cd "Bases de datos/arquetipos-bogota/publicar"
for f in arquetipos-bogota.json barrios-bogota.json; do
  gzip -9 -c $f > /tmp/$f.gz
  aws s3 cp /tmp/$f.gz "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/arquetipos-bogota/$f" \
    --content-type application/json --content-encoding gzip --cache-control "public, max-age=3600"
done
```

⚠️ Al regenerar, subir el `?v=` de `ARQ_BOG_URL` y `BOG_GEO_URL` en
`candidato-360-arq-lectura.js` (y el `?v=` de ese archivo en
`candidato-360.html` y `candidato-360-arquetipos.html`).

Los textos de cada arquetipo (`TEXTOS`: lema, cómo vota, criterio de oficio)
y los colores (`COLOR`, validados con el validador de paleta) viven en
`publicar.py`. «decide» describe lo medido; «oficio» es criterio de campaña y
el panel lo rotula así.

Salidas en `Bases de datos/arquetipos-bogota/` (gitignored): `raw/*.json`,
`candidatos-concejo-2023.csv`, `barrios.csv`, `arquetipos-bogota.json`
(506 KB, 85 KB en gzip) y `validacion.md`. Requiere numpy, scipy, scikit-learn,
geopandas (`pip3 install --break-system-packages scikit-learn` en la Mac M5).

## Unidad y cruces

- **Barrio catastral** (`codigo` de BOG-BARRIOS-CATASTRALES = el de
  `candidato-360-data/bogota-barrios`). Puesto → barrio con
  `candidato-360-data/bogota-puesto-barrio.js`, la misma regla del CRM.
  Fuera: zonas 90 (puesto censo) y 98 (cárceles). Cobertura: 98,2 % del voto
  válido al Concejo; 519 barrios con ≥300 votos y estrato.
- 2019: el código de puesto no siempre es el mismo lugar en 2026; se ubica con
  el detalle por comuna de 2019, que ya lo resolvió por nombre.
- Totales validados al voto contra el oficial: Galán 1.499.734 · Oviedo 616.902 ·
  Bolívar 571.948 · Claudia López 2019 1.109.362 · lista del Pacto 381.804 ·
  Concejo válidos 2.437.317 · Forero 70.032.

## La medida de «gestión»: votos con base propia

Para cada candidatura al Concejo: cuánto se aparta su votación de la
**geografía de su propia lista** (no de la ciudad: un candidato del Centro
Democrático concentrado en el norte no tiene base propia, vota donde vota su
partido), menos lo que un candidato de su tamaño se apartaría **por puro azar**
(simulación multinomial). Ese exceso son sus votos de arraigo, repartidos en las
unidades donde le sobra votación. Se mide a escala de localidad y de barrio y
se toma la mayor (13,0 % y 13,4 % del voto a nombres: la medida es estable).

⚠️ En listas de coalición, la «base propia» puede ser la red del partido
pequeño dentro de la coalición (Samir Bedoya Piraquive, MIRA dentro de
CR-MIRA-La U). No es un error de la medida, pero no es lo mismo que un líder de
barrio.

⚠️ El voto al logo de una lista **cerrada** (Pacto, Creemos, Liga en 2023) no es
una elección del votante: va aparte del logo en listas abiertas.

## Gotchas

- `cands` de los JSON por comuna es `[nombre, índice_de_partido]`; los votos
  están en los arrays `v`. Y el índice de partido es POR ARCHIVO.
- JAL: el `COD_CAN` se reinicia por localidad → la llave lleva la zona.
- La caché de la concentración por azar va por (escala, lista, tamaño): con una
  sola llave por tamaño, la primera lista contaminaba a las demás.
- Inter (subset) no trae `≥`: en los PNG va «80 % o más».
- Seis colores categóricos en un mismo mapa no pasan el validador (pares
  vecinos indistinguibles): los mapas van en paneles, un tono por confianza.
