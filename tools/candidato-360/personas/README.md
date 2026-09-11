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
