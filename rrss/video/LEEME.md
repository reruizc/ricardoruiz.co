# Videos de datos — HyperFrames

Videos verticales (1080×1920) renderizados desde HTML+CSS+GSAP con
[hyperframes](https://github.com/heygen-com/hyperframes) (Apache 2.0). Se
renderizan **local y gratis**: no hay cuenta ni créditos de HeyGen de por medio.

## Archivos

| Archivo | Duración | Qué es |
|---|---|---|
| `congreso-2026-2027-60s.mp4` | 60 s · 4,0 MB | El bueno. 5 escenas con narración. |
| `congreso-2026-2027-41s.mp4` | 41 s · 2,9 MB | Primera versión, 4 escenas. |
| `fuente-congreso-60s/` | — | El proyecto para regenerarlo o editarlo. |

Ambos llevan audio AAC y la Helvetica Neue del repo incrustada.

## Datos del video de 60 s (verificados ago-2026)

- **254 proyectos de ley** en la legislatura 2026-2027 · 154 Senado + 100 Cámara.
  Auditado contra el registro en vivo: Senado 154/154 con numeración 1-154 sin
  huecos; Cámara 104 publicados = 104 cosechados.
- **Ritmo**: 78 radicados en 10 días hábiles, contra 60 en 2022 y 39 en 2018.
  Solo registro del Senado — es el único que publica fecha, así que incluir
  Cámara haría incomparables los tres periodos.
- **Autoría**: solo Senado. En Cámara los firmantes vienen alfabetizados (94-97%
  en listas largas), así que su "primer firmante" no es el autor.
- **Embudo histórico**: 18,4% de los radicados llega a ley; 63,6% muere antes del
  primer debate. Sobre 13.420 proyectos con fecha.

⚠️ El registro de Cámara va **~10 días rezagado** (su numeración llega al 152
pero solo publica 104 fichas). Las cifras son fieles a *lo publicado*, no a *lo
radicado*; por eso el pie dice la fecha de corte.

## Regenerar

```bash
cd rrss/video/fuente-congreso-60s
npx --yes hyperframes@0.7.101 check     # lint + layout + contraste WCAG
npx --yes hyperframes@0.7.101 render    # → renders/*.mp4  (~1 min 45 s)
```

Requiere Node 22+ y ffmpeg (ya instalados en el Mac).

## Narración

Voz del sistema, gratis:

```bash
say -v Paulina -r 168 -o e1.aiff "texto de la escena"
ffmpeg -y -i e1.aiff -filter:a atempo=1.10 -ar 44100 -b:a 160k e1.mp3
```

`atempo` acelera **sin subir el tono**; subirle el `-r` a `say` atropella las
sílabas. Paulina (es_MX) es la más neutra para Colombia; Mónica es peninsular.

**El orden importa: primero la voz, se mide cada mp3, y con esas duraciones se
arma la animación.** Al revés no calza. `check` avisa si `data-duration` no
coincide con el mp3.

## Dos reglas de guion

1. **La voz no lee lo que está en pantalla.** La pantalla lleva las cifras; la
   voz, el contexto y la advertencia metodológica.
2. **Silencios de 1 a 4 s por escena.** El video respira y no suena a teleprónter.
