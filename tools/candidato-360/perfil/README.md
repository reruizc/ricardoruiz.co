# Candidato 360 · perfil del votante (tarjeta 07)

El voto es secreto: **nadie** puede decir quién votó por una persona. Lo que sí
se puede es describir el **electorado de los puestos donde están sus votos**,
ponderado por cuántos votos sacó en cada uno, y compararlo con el promedio del
municipio —que es lo que hace que el número signifique algo—. La tarjeta lo dice
con esas palabras: es una lectura del terreno, no de sus votantes.

| Dimensión | Fuente | Estado |
|---|---|---|
| **Sexo** | `PUESTOS_GEOREF.csv`, columnas MUJERES y HOMBRES (censo electoral por puesto) | publicado |
| **Rural / urbano** | zona electoral de cada mesa: `99` es la zona rural del municipio; `90` y `98` (censo consolidado y cárceles) no son ni lo uno ni lo otro | publicado |
| **Edad** | `CENSO_EDAD_PUESTO.json` (lo produce `construir-edad.mjs`) | **falta subirlo** |

Mientras el archivo de edad no esté en
`congreso-2026/output/mapas-2026/CENSO_EDAD_PUESTO.json`, el modal dice que
falta en vez de estimar la edad con el promedio del municipio y presentarla como
suya. En cuanto esté, la tarjeta lo lee sola:

```
node tools/candidato-360/perfil/construir-edad.mjs \
  --w26="Bases de datos/output_edad_1v/w26-puesto.csv"
```

`w26-puesto.csv` sale de `tools/edad-1v-2026/build_w26.py` (perfil etario 2022
por puesto de la Registraduría + deriva DANE 2022→2026, con raking IPF a los
votantes reales de 2026). El JSON publicable son cuatro bandas por puesto
—18-25, 26-40, 41-60 y 61+— y pesa ~700 KB.
