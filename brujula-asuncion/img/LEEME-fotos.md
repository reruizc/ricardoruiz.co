# Fotos de los dos candidatos

## Dónde van

```
/Users/ricardoruiz/ricardoruiz.co/Proyecto BL Paraguay/brujula/img/
    cand-camilo.jpg     Camilo Pérez López Moreira   · ANR – Partido Colorado · Lista 1
    cand-soledad.jpg    Soledad Núñez Méndez         · Alianza Juntos por Asunción · Lista 4
```

Los nombres de archivo son **exactos** (minúsculas, sin tildes, `.jpg`). El `id` de cada
archivo tiene que coincidir con el `id` del candidato en `contenido.js`.

## Especificación

- **Cuadradas 1:1**, 400×400 px (mínimo 300×300). Se muestran en círculos de 42 px y de
  36 px, así que lo que importa es que la cara quede centrada y llene el cuadro.
- **Encuadre**: cabeza y hombros, cara centrada y grande. Un plano entero se ve como una
  mancha en un círculo de 42 px.
- JPG calidad ~82, menos de 80 KB cada una.
- Fondo cualquiera; el círculo recorta.

Recorte rápido si la original es rectangular (macOS, sin instalar nada):

```bash
cd "/Users/ricardoruiz/ricardoruiz.co/Proyecto BL Paraguay/brujula/img"
sips -s format jpeg -s formatOptions 82 -Z 800 original.jpg --out cand-camilo.jpg
sips -c 400 400 cand-camilo.jpg          # recorta al centro; si la cara no queda centrada, recortar a mano antes
```

## Encender las fotos

Las fotos están **apagadas por defecto**: mientras `foto:false`, el avatar muestra las
iniciales y —esto es lo importante— **no se pide la imagen**, así que no quedan 404 en la
consola. Cuando el archivo exista, en `brujula/contenido.js` cambiar en ese candidato:

```js
foto:false   →   foto:true
```

Hay una línea `foto:false` por candidato, en el bloque `candidatos:` (líneas ~11-30).
Se pueden encender de a una: el que tenga foto la muestra, el que no, sigue con iniciales.

## ⚠️ Lo que NO hay que hacer

**No generar las fotos con IA.** Son dos personas reales en campaña; una imagen
sintética de una persona real dentro de una herramienta electoral es una foto falsa,
por más que se le parezca. Tienen que ser fotografías reales, de una fuente que se pueda
citar.

Tampoco sirve un retrato "inspirado en" ni un avatar ilustrado que pretenda ser la
persona. Si no aparece una foto usable de alguno, se queda con sus iniciales: el diseño
ya contempla ese caso y no se rompe.

## Contexto para pedírselas a Grok (o a quien busque las imágenes)

Copiar y pegar:

> Necesito la foto oficial de campaña de los dos candidatos a la
> Intendencia de Asunción (Paraguay) en la elección municipal del 4 de octubre de 2026.
> Son estos dos, con sus cuentas verificadas:
>
> 1. **Camilo Pérez López Moreira** — ANR/Partido Colorado, Lista 1. Presidente del
>    Comité Olímpico Paraguayo desde 2011, miembro del COI. Instagram y Facebook
>    "Camilo Pérez Intendente 2026", X @CamiloPerezLM.
> 2. **Soledad Núñez Méndez** — Alianza Juntos por Asunción, Lista 4. Ingeniera civil,
>    ex titular de Senavitat, candidata a vicepresidenta en 2023. Instagram @sole.nu,
>    X @solenu.
>
> Para cada uno necesito: **una fotografía real** de retrato (cabeza y hombros, de frente,
> cara centrada), de su material de campaña, de sus redes verificadas o de prensa
> paraguaya (ABC Color, Última Hora, La Nación), con **la URL de dónde salió** para poder
> citarla.
>
> No generes ni recrees las imágenes con IA: tienen que ser fotos reales de estas
> personas, porque van dentro de una herramienta electoral y una imagen sintética de una
> persona real ahí sería una foto falsa. Si de alguno no encontrás una foto usable,
> decímelo en vez de sustituirla.
>
> Entregá cada una recortada cuadrada 400×400 px con la cara centrada, en JPG, nombradas
> exactamente `cand-camilo.jpg` y `cand-soledad.jpg`.

## Uso

Son figuras públicas en campaña y el uso es editorial/informativo dentro de una
herramienta de comparación programática. Aun así, **anotá de dónde salió cada una** (una
línea por foto acá abajo) por si después hay que responder por la fuente o reemplazarla.

| Archivo | Fuente | Fecha de descarga |
|---|---|---|
| cand-camilo.jpg | | |
| cand-soledad.jpg | | |
| cand-rodri.jpg | | |
| cand-arlene.jpg | | |
