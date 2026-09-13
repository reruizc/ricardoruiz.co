# Candidato 360 · logos de partido

Un nombre en mayúsculas no se reconoce; el logo sí. El campo «¿con qué partido
o movimiento se va a lanzar?» muestra el logo al lado de cada organización
sugerida y del que la persona ya escribió.

La regla es que **nunca haya una imagen rota**: `index.json` lista solo los
archivos que están en la carpeta, y el frontend no pide nada más. Mientras un
logo falte, simplemente no aparece.

```
candidato-360-data/logos-partidos/<dep>/index.json   ← lo genera el script
candidato-360-data/logos-partidos/<dep>/<slug>.png   ← los archivos
```

`<dep>` es el código ELECTORAL del departamento, el mismo de
`candidato-360-data/partidos/<dep>.js`. **Bogotá D.C. es `16`** y es por donde
se empezó: 37 organizaciones con votación en la ciudad.

## Bogotá hace de catálogo nacional

Un logo es de la **organización**, no del departamento: el Partido Liberal se ve
igual en Antioquia que en Bogotá. La carpeta está partida por departamento
porque ahí viven también los movimientos locales («Bogotá entre todos», «Lara
Bogotá»), pero mientras solo exista la de Bogotá esa sirve de **base para todo
el país**: `logoDePartido(nombre, dep)` busca primero en el departamento y
después en `16`. El día que Antioquia tenga la suya, la suya manda.

Quien decide qué organizaciones se ven es el catálogo del departamento
(`partidos/<dep>.js`), no la carpeta de logos: en Antioquia salen las que
inscribieron candidatura allá y tienen logo, y los movimientos bogotanos no
aparecen porque no están en ese catálogo. Sin esta herencia, fuera de Bogotá la
vitrina se quedaba vacía y la pregunta del partido volvía a ser un campo de
texto en blanco.

## Cuando lleguen logos nuevos

```
node tools/candidato-360/logos/construir.mjs 16            # actualiza index.json
node tools/candidato-360/logos/construir.mjs 16 --encargo  # + lista lo que falta
```

## El encargo, tal como hay que pedirlo

> Necesito el logo oficial de cada uno de estos partidos y movimientos
> colombianos, como PNG de 512×512 px, **fondo transparente**, el logo centrado
> y ocupando todo el cuadro menos un margen parejo de ~6 %, sin texto añadido,
> sin marco ni sombra, y sin recortar el logo para volverlo cuadrado (si es
> apaisado, se centra y sobra transparencia arriba y abajo). El nombre de cada
> archivo tiene que ser EXACTAMENTE el que va en la primera columna.

Y se le pasa la lista que imprime `--encargo`, que es nombre de archivo +
nombre oficial de la organización. Los archivos van tal cual a
`candidato-360-data/logos-partidos/16/`.

Dos cosas que conviene revisar al recibirlos, porque son las que se cuelan:

- **Coaliciones y listas locales** («Con toda por Bogotá», «Juntos por Barrios
  Unidos») muchas veces no tienen logo público. Es mejor no poner nada que
  poner uno inventado: el manifiesto simplemente no las lista.
- **Partidos con el mismo nombre en versiones distintas** (el Nuevo Liberalismo
  y «Nuevo Liberalismo en Marcha») llevan archivos distintos; si es el mismo
  logo, se copia el archivo con los dos nombres.

El `slug` sale del nombre oficial: minúsculas, sin tildes ni signos, con
guiones. No se inventa a mano — lo imprime el script.
