# Integración · línea A, agendas regulatorias 2027

Rama `claude/caudal-agendas-2027-f84cd1`. Trae `harvest_agendas.py` y `prueba_agendas.py`. No toca
ningún archivo compartido: todo lo de abajo lo aplica la sesión principal.

## Lo que hay

- **Línea base:** `agendas-2027-20261101T233009.json`, capturada el 1-nov-2026 a las 23:30.
  sha256 `fbc58d70fa6377aacf0ee9510d3293f634760c5d7803ca9af904e0566ed6fdca`.
  33 entidades, 802 normas; 401 son de las 13 obligadas.
- **Copia a salvo** en el checkout principal, con los 31 originales:
  `Bases de datos/caudal-entidades/raw/agendas/{fotos,originales,linea-base.json}`.
- **SUCOP no consolida a las 13.** Trae 8 de ellas más otras 20 entidades. El cosechador lee SUCOP
  primero y va al sitio propio de las 5 restantes.

| Obligada | Estado el 1-nov | Normas | Con fecha | Dónde |
|---|---|---:|---:|---|
| MinTrabajo | En consulta hasta 30-nov | 41 | 41 | SUCOP |
| MinVivienda | En consulta hasta 30-nov | 33 | 33 | SUCOP |
| MinEducación | En consulta hasta 30-nov | 34 | 34 | SUCOP |
| MinCultura | En consulta hasta 30-nov | 20 | 20 | SUCOP |
| MinAgricultura | En consulta hasta 30-nov | 5 | 5 | SUCOP |
| MinHacienda | En consulta hasta 1-dic | 40 | 40 | SUCOP |
| DNP | En consulta hasta 30-nov | 33 | 33 | SUCOP |
| Presidencia | En consulta hasta 30-nov | 5 | 5 | SUCOP |
| MinSalud | Proyecto, solo en su sitio | 145 | 37 | ZIP con XLSX |
| MinComercio | Proyecto, solo en su sitio | 43 | 43 | XLSX |
| Función Pública | Preagenda, solo en su sitio | 2 | 0 | XLSX |
| MinAmbiente | **No publicada** | 0 | — | Página, sitemap de consultas y SUCOP |
| MinDeporte | **No publicada** | 0 | — | Página 2027 con 404, sitemap y SUCOP |

Ninguna quedó sin leer. «No publicada» significa que se leyeron esas fuentes y 2027 no aparece.

De MinSalud, 98 normas no traen fecha y 10 traen solo texto («Por definir…»). Función Pública dejó vacía
la columna de fecha.

## Verificación medida

- 51 casos en `prueba_agendas.py`, sin red.
- Segunda captura real, 3 minutos después: 802 normas y cero cambios en la comparación.
- Cambios conocidos sobre una copia de la foto real: la comparación halló las 3 salidas, 2 entradas,
  2 cambios de fecha, 1 título corregido, 1 agenda tardía y 1 entidad sin leer, que no contó como vacía.
- Contra los PDF oficiales de SUCOP, 8 obligadas, 211 normas: 206 casan por nombre. Las otras 5 están
  en el PDF por fragmentos; el corte de línea impide el casado exacto.
- MinSalud pegó un bloque dos veces, y solo la segunda copia trae fecha. De 185 filas quedan 145 normas,
  y 23 fechas se recuperan de la copia repetida. MinComercio repite 6 filas (43 de 49). Cada agenda lo
  declara en `descartes`.

## 1. Semilla en la EC2 (antes del primer cron)

**Esto va primero.** La primera foto que encuentre un directorio vacío se marca como línea base. Si la EC2
corre sin semilla, marcará como base una foto de noviembre y esconderá lo agregado desde el 1-nov.

Copia `raw/agendas/{fotos,originales,linea-base.json}` del checkout principal a la instancia.
`tools/caudal/ec2/sync-estado.sh` sirve de patrón. Comprueba después que `linea-base.json` diga la foto de
arriba y que `shasum -a 256` del archivo coincida.

La EC2 trae `openpyxl`, pero no `xlrd`. MinDeporte publicó sus agendas anteriores en `.xls`: sin `xlrd`, la
suya quedará `no_leida`, no vacía. Instálalo con `user-data.sh` y en la instancia.

## 2. Etapa del cron (`tools/leyes-senado/run_diario.sh`)

Junto a las de entidades. Tarda unos 90 s. Sale con 1 solo si SUCOP no responde; un sitio caído queda
`no_leida` en la foto y no tumba la etapa.

```bash
  etapa --nombre entidades_agendas --timeout 420 \
        --desc "Agendas regulatorias 2027: foto diaria y cambios contra la línea base" \
        -- python3 tools/caudal/entidades/harvest_agendas.py fetch
```

Cada corrida deja una foto de 0,9 MB: unos 330 MB al año si la etapa corre una vez al día y el doble si queda
en un bloque de 2x/día. Una vez al día basta. Si `raw/agendas/` no entra a ningún respaldo, sube `fotos/` y
`linea-base.json` a una ruta privada de S3, con visto bueno: los XLSX de `originales/` traen nombres de
funcionarios y no pueden quedar públicos.

## 3. Índice `agenda-regulatoria` (`build.py`)

Sale de `raw/agendas/agendas.json`, no de las fotos: esa vista ya conserva las filas de una entidad que no
se pudo leer (marcadas con `conservada: true`) y trae `novedad` contra la línea base.

```python
def agenda_regulatoria():
    """metadata/agenda-regulatoria.jsonl: una fila por norma anunciada. El stats declara
    el estado de cada entidad: una agenda sin leer no es una agenda vacía."""
    v = C.leer(C.RAW / 'agendas' / 'agendas.json')
    if not v:
        return None
    filas = [{**f, 'q': _q(f['nombre'], f['tema'], f['entidad'], f['tipo_norma'], f['norma_concreta'])} for f in v['filas']]
    filas.sort(key=lambda f: (not f.get('novedad'), f.get('fecha_prevista') or '9999'))
    C.DIST.mkdir(parents=True, exist_ok=True)
    with (C.DIST / 'agenda-regulatoria.jsonl').open('w', encoding='utf-8') as fh:
        for f in filas:
            fh.write(json.dumps(f, ensure_ascii=False) + '\n')
    C.escribir(C.DIST / 'agenda-regulatoria-stats.json', {
        'generado': v['generado'], 'foto': v['foto'], 'linea_base': v['linea_base'], 'n': len(filas),
        'agendas': [{c: a.get(c, '') for c in ('k', 'entidad', 'obligada', 'estado', 'leida', 'publicada', 'via', 'url', 'n_normas',
                                               'nota', 'consulta_inicio', 'consulta_fin')} for a in v['agendas']],
        'vs_linea_base': v['vs_linea_base'], 'vs_anterior': v['vs_anterior']})
    return len(filas)
```

Llámala en `build()` con el mismo `try` de `territorial()`. En `subir()` agrega `agenda-regulatoria.jsonl` y
`agenda-regulatoria-stats.json` bajo `metadata/`, con la guarda de siempre.

Las claves de catálogo de las 13 son las de `catalogo.py`. Las demás usan la abreviatura de SUCOP
(`mininterior`, `mintransporte`, `cancilleria`…).

## 4. Catálogo (`catalogo.py`)

Define `AGENDA = 'Agenda regulatoria 2027 (línea base y cambios)'` y súmala a `cubre` en las 11 que la
publicaron. La SIC, además, tiene proceso en SUCOP en formulación, con 1 norma visible.

- `minambiente` y `mindeporte`: en `falta`, «Agenda regulatoria 2027: no publicada al 1-nov-2026, se revisa a
  diario». Quítalo cuando la foto la encuentre.
- `minsalud`, `mincomercio`, `funcionpublica`: en `nota`, «Publicó su agenda 2027 en su sitio, no en SUCOP».
  Es un hecho, no un juicio: la Circular 04 de 2026 pide publicarla a través de SUCOP.
- La nota de cobertura de MinHacienda y Presidencia puede decir que su agenda sí se lee, por SUCOP: el
  antibots no afecta esa ruta.

## 5. Lambda y Norte del radar

- Lee el jsonl con la caché de `_entidades_jsonl` (hoy abre `entidades-*.jsonl`: dale una ruta aparte o sube
  el índice con el prefijo). Solo entran las filas del tema del cliente, igual que en `_eventos_oficiales`:
  temas sobre `q` y entidad interlocutora.
- **Norte, función `_agendas_norte(s, cap=4)`.** Orden: primero `novedad` (`agregada`, `agenda_nueva`,
  `fecha_cambiada`), después la `fecha_prevista` más cercana. Nada de lo que pase al estado `En consulta
  pública` se repite: el `Id` de `sucop:<Id>` es el mismo proceso del pilar SUCOP.
- Texto según `novedad`:
  - `agregada`: «Entró a la agenda después del 1-nov».
  - `agenda_nueva`: «Publicó su agenda después del corte».
  - `fecha_cambiada`: «Cambió de fecha: antes `fecha_base`». Si `fecha_base` viene vacía, di «ahora tiene
    fecha».
- Sin `novedad`, la norma es parte de la línea base: se muestra como «anunciada para `fecha_prevista`», sin
  tono de alerta.
- **Reglas que no se pueden perder:**
  - `sin_comparar` no es «sin cambios»: si una entidad del cliente aparece ahí, el panel lo dice.
  - `estado` `no_leida` o `publicada_sin_leer` nunca se pinta como «0 normas».
  - `conservada: true` se muestra con la fecha de la última lectura.
  - `fecha_prevista` vacía con `fecha_texto` lleno: muestra el texto, no inventes fecha. `fecha_alterna`
    significa que la entidad se contradijo.
- Ejecutivo: un bloque «Agendas 2027», por entidad, con estado y `n_normas` desde el stats.

## 6. Nota para CAUDAL.md

```markdown
### Agendas regulatorias 2027 · línea base (tanda 0 · 1-nov-2026)

`tools/caudal/entidades/harvest_agendas.py` deja por corrida una foto inmutable en
`raw/agendas/fotos/`. La primera, del 1-nov-2026, es la línea base (`linea-base.json`, con su sha256).
Cada fila es una norma anunciada. `comparar(a, b)` dice qué entra, qué sale y qué cambia de fecha.

- SUCOP trae 28 agendas 2027. La lista de agendas sale de
  `rootfolder/folders?$filter=substringof('2027',Name)` y las normas de cada una, de la consulta CAML por
  `Agenda_x003a_ID` (POST a `getitems`, con el digest anónimo de `contextinfo`).
- MinSalud, MinComercio y Función Pública publican en su sitio. MinAmbiente y MinDeporte no habían publicado
  el 1-nov; se revisan a diario en su página y sitemap.
- Lo no leído va a `sin_comparar`: nunca se reporta como salida ni como agenda vacía. La guarda deja de
  contar como leída una agenda que cae a menos de la mitad; si la caída es real, se ve al día siguiente
  contra la línea base.
- SUCOP lista una «Entidad Ejemplo» con datos de prueba: se descarta. Sus carpetas guardan CSV de
  suscripciones: solo se listan los `Agenda*.pdf`.
- Las claves de un sitio son un hash de tipo + nombre. `comparar` empareja por parecido, salvo que citen
  números distintos o sean dos id de SUCOP.
- Pruebas: `python3 tools/caudal/entidades/prueba_agendas.py`.
```

## 7. Lo que falta vigilar

- **MinSalud cierra su ciclo el 2-nov:** su archivo dice publicación final ese día. Si reemplaza el ZIP, el
  cosechador toma cualquier enlace con 2027, pero las normas que cambien saldrán en la comparación.
- **Las agendas finales** vencen el 31-dic-2026. Ese mes habrá movimiento real en la comparación.
- La línea base tiene en las filas de SUCOP la URL `…/Paginas/proceso.aspx?IDNorma=N`. Funciona, y `comparar`
  no usa la URL. Desde la siguiente foto va la canónica, `…/Normativa?IDNorma=N`.
