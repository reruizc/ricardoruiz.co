# Integración · línea B, ministerios (tanda 3, 1-nov-2026)

Rama `claude/caudal-ministerios-t3-7c6e04`. Cosechadores nuevos: `harvest_minagricultura.py`,
`harvest_minambiente.py`, `harvest_mindeporte.py` y `harvest_mincultura.py`. Ampliado:
`harvest_mincomercio.py`, que suma `eventos.json`. Esta rama no tocó `build.py`, `catalogo.py`,
`comun.py`, `run_diario.sh`, CAUDAL.md ni la Lambda. Nada se subió a S3.

Todo lo de abajo se ensayó con una copia de `build.py`: los cuatro reemplazos aplican tal cual y
las cinco fuentes arman sus filas. La Lambda no necesita cambios: `subtipo` puede ser
`Convocatoria` o `Aviso de convocatoria` y sigue siendo tipo `COMUNICADOS`.

## Medido el 1-nov-2026, corrido de verdad y dos veces seguidas con igual resultado

| Entidad | Borradores | Normas | Noticias y convocatorias | Eventos | Tiempo |
|---|---|---|---|---|---|
| MinAgricultura | no aplica (SUCOP) | 114 resoluciones · 2 decretos | 90 noticias | no aplica | 18 s |
| MinAmbiente | 120 (0 abiertos) | 176 resoluciones · 15 circulares · 2 decretos | 120 noticias | 50 (0 por venir) | 82 s |
| MinDeporte | 11 (0 abiertos) | 83 resoluciones | 2 convocatorias | no aplica | 25 s |
| MinCultura | no aplica (SUCOP) | no aplica | 968 noticias · 61 avisos | no aplica | 7 s |
| MinComercio | 121 (3 abiertos, ya entraban) | no aplica | no aplica | 4 (3 por venir) | 23 s |

Desde 2025 en todas las columnas de histórico, salvo los eventos de MinComercio, que van del mes
en curso a seis meses adelante, más lo que ya pasó y se acumula.

**Fuentes que no dan lo que el plan esperaba, con su causa.** Ninguna quedó como cero por error:

- **MinAmbiente · eventos: 0 por venir.** `/agenda/` dice «¡No hay eventos!» y el iCal termina el
  7-jul-2026. Es la fuente la que está parada. La API de eventos responde 401.
- **MinAmbiente y MinDeporte · 0 borradores abiertos.** Es real hoy: el último plazo de MinAmbiente
  cerró el 24-oct-2026 y el de MinDeporte el 14-may-2026.
- **MinDeporte · convocatorias: 2.** Su página no se toca desde el 18-feb-2025: dos circulares y
  un enlace a una ficha fija. Hoy ninguna noticia vigente tiene «convocatoria» en la ruta.
- **MinCultura · 9 avisos fuera.** Los 9 son tutelas publicadas por orden judicial, varias con el
  nombre de quien la interpone en el rótulo. No se guardan.
- **MinComercio · el calendario son 4 eventos.** La guarda de eventos no juzga por debajo de 6.
- **MinAgricultura · 85 de 116 normas sin fecha.** El título solo trae el año y sus PDF son
  escaneados. Lo nuevo entra con el día en que aparece, como en UGPP y MinVivienda. Esas 85 quedan
  con año y sin día: el Diario Oficial sigue siendo la fuente de la fecha.

**Decisiones de esta rama.**

- **Decretos:** Presidencia ya trae 34 de los 36 de MinAgricultura y 9 de los 11 de MinAmbiente.
  La Lambda suma `normativa.jsonl` y `entidades-normas.jsonl` sin deduplicar, así que cada
  cosechador compara contra `normativa.jsonl` y solo deja los 4 que faltan (MinAgricultura 765 de
  2026 y 1139 de 2025; MinAmbiente 800 y 766 de 2026). Estos llevan tipo `DECRETOS` y
  `_fuente_simple` los deja pasar: no filtrarlos ahí. Si S3 no responde, van todos ese día.
- **`administrativo`:** MinAmbiente marca 135 de 193 (sancionatorios, sustracciones de reserva,
  contratos) y MinDeporte 51 de 83 (pagos de sentencias y conciliaciones). Se marcan, no se borran.
- **Agendas:** no se leyeron. Las consultas de «Agenda Regulatoria» de MinAmbiente y MinDeporte se
  excluyen para no pisar la línea de agendas 2027.
- **MinAgricultura · proyectos:** no se cosechan. De 78 de 2025-2026 en su página, 77 enlazan a
  SUCOP. Falta 1 de 2025, que no vale un cosechador.

**La muestra contra el sitio** se hizo en el navegador, con la página renderizada: resoluciones,
decretos y noticias de MinAgricultura; borradores y circulares de MinAmbiente; resoluciones y la
ventana de un proyecto de MinDeporte; noticias y avisos de MinCultura; una ficha del calendario de
MinComercio. Títulos, números, fechas y plazos coinciden. Dos errores que destapó la comparación
ya están corregidos: las notas `Visible=false` de MinCultura sí se publican (eran 87 noticias
perdidas), y lo que quedaba sin fecha se estampaba con la fecha de hoy en la segunda corrida.

**La guarda** se probó inflando el conteo anterior: MinAgricultura, MinAmbiente, MinDeporte,
MinCultura y MinComercio rechazan la corrida, conservan lo que había y salen con código 1. Compara
`leidos` (lo que dio la fuente), no lo acumulado. Falla si cae a menos de la mitad o a cero. Si la
caída es real, se borra `leidos` del JSON en `raw/<entidad>/` (en MinCultura, `leidos_noticias` o
`leidos_avisos`) y la siguiente corrida fija el nuevo piso. La función está repetida en los cuatro
archivos nuevos porque `comun.py` no se podía tocar; conviene subirla ahí al integrar.

## build.py

<!-- reemplazar -->
```python
def fuente_mincomercio():
    """Solo borradores por ahora (punto 3 de la fase 1); sus normas expedidas
    ya llegan por el Diario Oficial."""
    ent, sector, fuente = 'Ministerio de Comercio, Industria y Turismo', 'Comercio, Industria y Turismo', 'mincomercio'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(C.RAW / 'mincomercio' / 'proyectos.json', {}) or {}).get('items', {})
    return [borrador_sucop(r, ent, sector, fuente, hoy) for r in items.values()], [], []
```
<!-- por -->
```python
def fuente_mincomercio():
    """Borradores y calendario de eventos; sus normas expedidas ya llegan por el
    Diario Oficial."""
    ent, sector, fuente = 'Ministerio de Comercio, Industria y Turismo', 'Comercio, Industria y Turismo', 'mincomercio'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(C.RAW / 'mincomercio' / 'proyectos.json', {}) or {}).get('items', {})
    eventos = [{**e, 'entidad': ent, 'fuente': fuente, 'q': _q(e.get('titulo'), e.get('descripcion'))}
               for e in (C.leer(C.RAW / 'mincomercio' / 'eventos.json', {}) or {}).get('items', [])]
    return [borrador_sucop(r, ent, sector, fuente, hoy) for r in items.values()], [], eventos
```

`_fuente_simple` gana `eventos.json`. Es inofensivo para las demás: sin el archivo da lista vacía.

<!-- reemplazar -->
```python
                  for r in (C.leer(raw / f'{nombre}.json', {}) or {}).get('items', []) if r.get('descripcion')]
        return borr, normas, []
    return f
```
<!-- por -->
```python
                  for r in (C.leer(raw / f'{nombre}.json', {}) or {}).get('items', []) if r.get('descripcion')]
        eventos = [{**e, 'entidad': ent, 'fuente': clave,
                    'q': _q(e.get('titulo'), e.get('descripcion'), ' '.join(e.get('categorias') or []))}
                   for e in (C.leer(raw / 'eventos.json', {}) or {}).get('items', [])]
        return borr, normas, eventos
    return f
```

<!-- reemplazar -->
```python
fuente_dnp = _fuente_simple('dnp', 'Departamento Nacional de Planeación', 'Planeación')
```
<!-- por -->
```python
fuente_dnp = _fuente_simple('dnp', 'Departamento Nacional de Planeación', 'Planeación')
fuente_minagricultura = _fuente_simple('minagricultura', 'Ministerio de Agricultura y Desarrollo Rural', 'Agropecuario, Pesquero y de Desarrollo Rural')
fuente_minambiente = _fuente_simple('minambiente', 'Ministerio de Ambiente y Desarrollo Sostenible', 'Ambiente y Desarrollo Sostenible')
fuente_mindeporte = _fuente_simple('mindeporte', 'Ministerio del Deporte', 'Del Deporte, la Recreación, la Actividad Física y el Aprovechamiento del Tiempo Libre')
fuente_mincultura = _fuente_simple('mincultura', 'Ministerio de las Culturas, las Artes y los Saberes', 'Cultura')
```

Los sectores son los que usa SUCOP para esas entidades.

<!-- reemplazar -->
```python
           ('sena', fuente_sena), ('dnp', fuente_dnp)]
```
<!-- por -->
```python
           ('sena', fuente_sena), ('dnp', fuente_dnp), ('minagricultura', fuente_minagricultura),
           ('minambiente', fuente_minambiente), ('mindeporte', fuente_mindeporte), ('mincultura', fuente_mincultura)]
```

## run_diario.sh

En `tools/leyes-senado/run_diario.sh`, justo después de `entidades_dnp` y antes de `entidades_build`.
`entidades_mincomercio` ya existe y no cambia, aunque ahora tarda 25 s y lee también el calendario.

```bash
  etapa --nombre entidades_minagricultura --timeout 300 \
        --desc "MinAgricultura: resoluciones, decretos que Presidencia no trae y noticias" \
        -- python3 tools/caudal/entidades/harvest_minagricultura.py fetch
  etapa --nombre entidades_minambiente --timeout 300 \
        --desc "MinAmbiente: borradores (AJAX), normas, RSS e iCal" \
        -- python3 tools/caudal/entidades/harvest_minambiente.py fetch
  etapa --nombre entidades_mindeporte --timeout 300 \
        --desc "MinDeporte: borradores, resoluciones y convocatorias" \
        -- python3 tools/caudal/entidades/harvest_mindeporte.py fetch
  etapa --nombre entidades_mincultura --timeout 300 \
        --desc "MinCultura: noticias (SharePoint) y avisos de convocatorias" \
        -- python3 tools/caudal/entidades/harvest_mincultura.py fetch
```

MinDeporte lee epígrafes de PDF a ~9 s cada uno, con un tope de 15 nuevos por corrida
(`MAX_PDF`): en la EC2 necesita unas 4 corridas para completar los 49 que no lo traen en la tarjeta, y
hasta entonces esas resoluciones salen como `administrativo`.

## catalogo.py

Reemplazan las fichas de esas cinco claves. Cada una deja la agenda en `falta`: si la línea de
agendas 2027 entra antes, pásala a `cubre`. `SALIDA[...]` es solo para copiar el `dict(...)`.

```python catalogo
SALIDA['mincultura'] = dict(k='mincultura', nombre='Ministerio de las Culturas, las Artes y los Saberes', alias=['ministerio de las culturas', 'ministerio de cultura', 'mincultura'],
     estado='conectada', cubre=['Noticias', 'Avisos de convocatorias', SUCOP, DO],
     falta=['Agenda regulatoria'],
     nota='Sus resoluciones de 2026 no están en su sitio: solo por el Diario Oficial. No publica conceptos. '
          'De sus avisos no se leen las tutelas que publica por orden judicial.')
SALIDA['mincomercio'] = dict(k='mincomercio', nombre='Ministerio de Comercio, Industria y Turismo', alias=['ministerio de comercio', 'mincomercio', 'mincit'],
     estado='conectada', cubre=['Borradores propios (no publica en SUCOP desde 2025)', 'Calendario de eventos', DO],
     falta=['Agenda regulatoria'], nota='No publica conceptos. Sus normas expedidas llegan por el Diario Oficial.')
SALIDA['minagricultura'] = dict(k='minagricultura', nombre='Ministerio de Agricultura y Desarrollo Rural', alias=['ministerio de agricultura', 'minagricultura'],
     estado='conectada', cubre=['Resoluciones', 'Noticias', 'Decretos que no están en Presidencia', SUCOP, DO],
     falta=['Agenda regulatoria'],
     nota='No publica conceptos. La mayoría de sus resoluciones solo trae el año: lo que ya existía entra sin fecha '
          'y lo nuevo con el día en que aparece.')
SALIDA['minambiente'] = dict(k='minambiente', nombre='Ministerio de Ambiente y Desarrollo Sostenible', alias=['ministerio de ambiente', 'minambiente'],
     estado='conectada', cubre=['Borradores propios (no publica en SUCOP desde 2025)', 'Resoluciones y circulares',
                                'Decretos que no están en Presidencia', 'Noticias', 'Calendario oficial', DO],
     falta=['Agenda regulatoria'],
     nota='Sus conceptos se congelaron en 2025. Su calendario oficial dejó de alimentarse el 7 de julio de 2026.')
SALIDA['mindeporte'] = dict(k='mindeporte', nombre='Ministerio del Deporte', alias=['ministerio del deporte', 'mindeporte'],
     estado='conectada', cubre=['Borradores propios (no publica en SUCOP desde 2025)', 'Resoluciones', 'Convocatorias', DO],
     falta=['Agenda regulatoria'],
     nota='Sus conceptos se congelaron en 2024. Su página de convocatorias no se actualiza desde febrero de 2025.')
```

Conteo si las cinco pasan a conectada: 23 conectadas (18 + 5) y 11 parciales en el catálogo de 39
fichas. Ese corte de `plan.md` §8 puede moverse con lo que integren las otras líneas.

## Nota para CAUDAL.md

Va a continuación del párrafo «Tanda 2 (oct-30-2026)»:

> - **Tanda 3 (nov-1-2026):** los ministerios que faltaban. Cada cosechador guarda `leidos` y se niega a publicar si la fuente trae menos de la mitad que la corrida anterior, o cero: el acumulado esconde la caída.
>   **MinAgricultura** (`harvest_minagricultura.py`): TYPO3, `<article class="item_norm">` con todo en `data-*`, sin paginar. ⚠️ `data-year` trae errores: manda el año del título. ⚠️ `comun.fecha_larga` no lee «DE OCTUBRE» en mayúsculas. 85 de 116 normas sin día: títulos solo con año y PDF escaneados.
>   **MinAmbiente** (`harvest_minambiente.py`): borradores por POST `consultas_paginacion-load-posts`, ⚠️ sin orden por fecha, se corta cuando una página entera es vieja. Normas por `normativa_paginacion-load-posts`; ⚠️ el id de cada año (`area2`) se descubre en la página: 2026 es 1049. Calendario parado desde el 7-jul-2026.
>   **MinDeporte** (`harvest_mindeporte.py`): lista por año (el año nuevo da 404), ventana en la ficha. ⚠️ Hay dos «Fecha de publicación»: la de la consulta va en palabras. Epígrafes faltantes del PDF, máximo 15 por corrida. Convocatorias paradas desde feb-2025.
>   **MinCultura** (`harvest_mincultura.py`): SharePoint con `$orderby=Created desc`; fecha en `notaCiudadFecha`. ⚠️ `Visible=false` NO es despublicada: el sitio muestra esas notas. Avisos de `sistemaconvocatorias`: ⚠️⚠️ las tutelas traen el nombre de quien la interpone y no entran. ⚠️ El PDF va en una URL de Azure con firma que `_u` daña (403): se enlaza la página.
>   **MinComercio** (`harvest_mincomercio.py` amplía): calendario ASP.NET, cada mes es un postback con ViewState y cookie, en cadena.
>   Decretos: se comparan con `normativa.jsonl` y solo entran los que Presidencia no trae (4), porque la Lambda no deduplica el Ejecutivo.
