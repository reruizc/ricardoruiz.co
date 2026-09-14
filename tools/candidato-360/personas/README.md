# Candidato 360 · una tarjeta por persona

El índice tiene una entrada por **candidatura** (439 mil). El buscador de
`candidato-360.html` las junta en una tarjeta por **persona** cuando el nombre
lo permite (`candidateProfile` en `candidato-360.js`):

- **Cuatro componentes** iguales → la misma persona, esté donde esté.
- **Tres componentes** iguales → la misma persona **solo si todas sus
  candidaturas territoriales caen en el mismo departamento**. «Daniel Carvalho
  Mejía» (Cámara Antioquia 2022, Concejo Medellín 2015 y 2019) es una tarjeta;
  «Juan Carlos López», que existe en veinte departamentos, sigue siendo una
  tarjeta por candidatura. Senado, presidencia y consultas no cuentan como
  departamento. El departamento sale del slug (`departamentoDelSlug`).
- Dos componentes o uno → nunca.

`similares.mjs` baja los índices y produce la lista completa de nombres de tres
componentes repetidos, con la decisión que toma la regla y el tipo de grupo,
para validarla a ojo:

```
NODE_USE_ENV_PROXY=1 node tools/candidato-360/personas/similares.mjs
```

Deja `salida/similares.csv` y `salida/similares-resumen.md` (la carpeta
`salida/` no va al repo). La categoría que merece revisión es «UNIFICA ·
varios-municipios»: la misma persona en dos concejos del mismo departamento, o
dos homónimos vecinos. La prueba de la regla en el navegador es
`tools/candidato-360/prueba-personas.mjs`.

## El Excel para revisar a mano

`homonimos-xlsx.py` convierte esa salida en un libro por departamento, pensado
para que alguien que conoce la región lo resuelva sin herramientas:

```
NODE_USE_ENV_PROXY=1 node tools/candidato-360/personas/similares.mjs
python3 tools/candidato-360/personas/homonimos-xlsx.py 1 16
```

Deja `salida/Homonimos_<Departamento>_Candidato360.xlsx` con dos hojas: «Cómo
llenarlo», con la instrucción, y «Casos», una fila por grupo dudoso con el
nombre, el tipo de caso, dónde se presentó y el detalle de las candidaturas
(corporación, municipio o localidad, año, partido y votos). Lo único que se
llena es la columna B —lista desplegable de **X** (misma persona), **N**
(homónimos) y **?** (no está claro)—, y la C para la nota cuando en un grupo de
tres sobra una candidatura.

Son tres tipos de caso, en este orden: «unificado · municipios distintos» (la
regla los juntó pero se presentaron en municipios distintos del mismo
departamento), «unificado · localidades distintas» (los juntó pero fueron a JAL
de comunas o localidades distintas) y «separado · departamentos distintos» (los
dejó aparte porque el nombre aparece en varios departamentos). Antioquia da 131
casos (43 / 19 / 69) y Bogotá 83 (0 / 17 / 66).

Las copias que circulan por correo quedan en
`candidato-360-data/homonimos/`, para poder mandar el enlace de descarga.
