# Fotos de candidatos · ¿Quién queda?

Una imagen por candidato, nombrada con su `id` de `tools/pronosticos/mercados.json`:

```
laverde.jpg   castro.jpg   zuluaga.jpg   monsalvo.jpg   abadia.jpg   torres.jpg
```

Cuadradas, mínimo 200×200, encuadre de rostro (se recortan en círculo con
`object-position: top center`, así que dejar aire arriba).

**Para activar una**: poner el archivo aquí Y marcar `"foto": true` en ese
candidato en `mercados.json`. Sin el flag la página no la pide — así no queda
un 404 por candidato en la consola mientras faltan.

Normalizar tamaño:
```bash
sips -Z 400 laverde.jpg
```
