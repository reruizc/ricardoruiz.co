# Integración · línea D · tanda 5 (territorio), 1-nov-2026

Rama `claude/caudal-territorio-t5-d0ef25`. Esta rama solo crea `harvest_gobernacion.py` y
`harvest_alcaldia.py`, y edita `harvest_territorial.py`. Todo lo de abajo le toca a la sesión
principal. Las cifras son de la corrida real del 1-nov-2026.

## Resultado por fuente

| Fuente | Vía real | Frescura | Texto | Volumen 2026 | Estado |
|---|---|---|---|---|---|
| Gobernación de Antioquia | Gaceta Departamental `/gaceta-departamental-2026` | Última gaceta 29-oct, subida el 30-oct | Sumario digital. Actos en OCR. 23 gacetas son escaneo puro | 557 de 560 gacetas · 8.155 actos · 940 de alcance general | Construida |
| Alcaldía de Medellín | Gaceta Oficial `/statements/innovaciondigital/gacetas/` | Última gaceta 30-oct, con actos del mismo día | Ficha estructurada. PDF en OCR | 62 gacetas nuevas + histórico · 1.897 actos · 350 de alcance general | Construida |
| Asamblea · actas | WordPress, categoría 217 | Comisiones al día siguiente. Plenarias a los 8 días | PDF | 702 actas, 147 de 2026 | Construida |
| Asamblea · agenda | Google Calendar público que embebe `/agenda/` | Sesiones hasta el 11-nov | Texto | 43 sesiones, 11 por venir | Construida |
| Concejo · PDF y ponencia | Pestañas de SIMI | n/a | n/a | 0 | **No se pudo** (causa abajo) |
| Concejo · ficha pública | `interna-proyectos-de-acuerdo?simi_id=N` | En vivo | Texto | 12 proyectos con proponentes y ponentes | Construida, parcial |

### Verificación de los números

- **Gobernación.** La serie de decretos de 2026 llega al 5.108 y la gaceta trae 5.008: **98,0 %**.
  El radicado del sumario aparece en la página del acto en 6.190 de 7.643 actos con texto; el resto
  es OCR o formato sin recuadro. Cotejo contra la imagen de la página: 3 de 3 con número y fecha
  correctos, incluida una gaceta sin capa de texto.
- **Medellín.** Cotejo ficha contra PDF en 18 gacetas: 182 de 187 actos coinciden. Cuatro fallos son
  solo de formato (`Acuerdo Metropolitano N°12`). Uno es un error de la ficha: la 5741 dice decreto
  0477 y el PDF no lo trae. Ese tipo de error no se corrige solo en el histórico.
- **Ficha cortada.** `MED_2026_40_00012` es en el documento `MED_2026_40_000125`. El cosechador lo
  corrige con el PDF. Fue el único de 20 números `MED_`.

### Lo que no se pudo, y por qué

- **PDF y ponencia del Concejo.** La lista de archivos existe: el proyecto 114-2026 trae texto, carta
  de delegación y conceptos. Vive en una pestaña dinámica de SIMI. En el navegador abre. Por curl, la
  petición con el parámetro correcto (`_currentTab`) devolvió «Sorry, you have been blocked» de
  Cloudflare, Ray ID `a5406c192a983405`. **Es una regla de seguridad del sitio y no se intentó
  esquivar**: ni cabeceras disfrazadas, ni navegador automatizado. El GET normal siguió en 200, así
  que el cosechador del listado no se afectó. Cuando salió ese bloqueo se dejó de tocar esa ruta.
  Alternativas legítimas: pedirle al Concejo una exportación o que permita el acceso, o un derecho de
  petición. Los acuerdos ya aprobados sí entran con texto por la Gaceta de Medellín.
- **Ficha pública del Concejo.** Solo existe para proyectos abiertos a participación (12 de 27
  vivos). A los demás el sitio les responde 200 con una página genérica. Por eso se enlaza solo si la
  ficha trae ese número de proyecto.
- **Títulos de la Gobernación en escaneos.** 454 actos (5,6 %) tienen número, fecha y PDF, sin título.
  Falta OCR. Ni esta máquina ni la EC2 tienen tesseract. Instalarlo en la EC2 los recupera: la
  imagen se lee bien.
- **Tres gacetas rotas.** 25.610, 25.611 y 25.612 están en el listado y dan 404 en el sitio de la
  Gobernación. Se reintentan solas y no tumban la etapa.
- **Gaceta 5969 de Medellín.** Tiene ficha y PDF, pero no sale en el listado y dice «Fecha de
  Generación». Sus 3 actos quedan fuera hasta que la listen.

## Ojo antes de publicar

- **Lo normal es ruido.** 83 % de la Gaceta Departamental son actos particulares y 53 % de los actos
  de Medellín son movimientos presupuestales. Por eso el índice solo recibe los 1.290 de alcance
  general. El resto queda en raw y se declara con su conteo. El filtro es por palabras: puede ocultar
  algo legítimo, así que hay que revisar una muestra de `administrativo: true` antes de vender la
  fuente como completa.
- **Primera corrida en la EC2.** Copia `raw/gobernacion-antioquia/` y `raw/alcaldia-medellin/` desde
  acá o espera unos 5 días: el tope es 60 gacetas por corrida, de la más nueva a la más vieja. Si no,
  son unos 5 GB de bajada.
- **pypdf.** Probado con 14 gacetas: 141 de 142 actos iguales que pymupdf (una gaceta da un acto
  menos) y 58 de 58 títulos de Medellín. Es 13 veces más lento: unos 6 s por gaceta. Cabe en 900 s.
- **Sin probar en la EC2.** Todo corrió en esta Mac. Falta una corrida allá, con su IP.
- **`harvest_alcaldia.py` importa de `harvest_gobernacion.py`** (`paginas`, `particular`): no se tocó
  `comun.py`. Conviene moverlos ahí al integrar.

## `build.py`

Agregar antes de `def territorial():`

```python
_GACETAS_TERRITORIALES = (('gobernacion-antioquia', 'Gobernación de Antioquia'),
                          ('alcaldia-medellin', 'Alcaldía de Medellín'))


def gacetas_territoriales():
    """Decretos, resoluciones y circulares de alcance general. Lo particular, lo
    presupuestal de rutina y lo escaneado sin título quedan en raw y se cuentan."""
    out, por = [], {}
    for clave, corp in _GACETAS_TERRITORIALES:
        items = (C.leer(C.RAW / clave / 'normas.json', {}) or {}).get('items', [])
        cuenta = {'total': len(items), 'particulares': 0, 'rutinarios': 0, 'sin_texto': 0, 'publicados': 0}
        for x in items:
            if x['subtipo'] not in ('Decreto', 'Resolución', 'Circular'):
                continue
            if x['sin_texto'] or x['administrativo'] or x.get('rutinario'):
                cuenta['sin_texto' if x['sin_texto'] else 'particulares' if x['administrativo'] else 'rutinarios'] += 1
                continue
            cuenta['publicados'] += 1
            out.append({'corporacion': corp, 'fuente': clave, 'tipo': 'norma', 'tipo_nombre': x['subtipo'],
                        'numero': x['numero'], 'anio': x['anio'], 'fecha': x['fecha'], 'titulo': x['titulo'],
                        'estado': 'Expedida', 'en_tramite': False, 'url': _u(x['url']), 'pagina': _u(x['url']),
                        'dependencia': x.get('dependencia') or '', 'gaceta': x['gaceta'],
                        'q': _q(x['titulo'], corp, x.get('dependencia'), x['subtipo'])})
        por[clave] = cuenta
    return out, por
```

Dentro de `territorial()`, después del `for` de ordenanzas de la Asamblea:

```python
    for x in a.get('actas', []):
        out.append({'corporacion': corp, 'fuente': 'asamblea-antioquia', 'tipo': 'acta',
                    'tipo_nombre': 'Acta de sesión', 'numero': x['numero'], 'anio': x['anio'], 'fecha': x['fecha'],
                    'titulo': x['titulo'], 'estado': x['instancia'] or 'Publicada', 'en_tramite': False,
                    'url': _u(x['url']), 'pagina': x.get('pagina') or '', 'q': _q(x['titulo'], corp, 'acta')})
    for e in a.get('eventos', []):
        eventos.append({**e, 'entidad': corp, 'fuente': 'asamblea-antioquia',
                        'q': _q(e.get('titulo'), e.get('descripcion'), ' '.join(e.get('categorias') or []))})
```

En el `for x in c.get('proyectos', [])` del Concejo, cambiar la `q` para que busque por proponente y ponente:

```python
                    'q': _q(x['titulo'], x['estado'], corp, x.get('proponentes'), x.get('ponentes'))})
```

Al final de `territorial()`, antes del `return`:

```python
    gac, _ = gacetas_territoriales()
    out += gac
```

En `build()`, junto a `por['territorial']`, declarar lo que no se publicó:

```python
    por['gacetas_territoriales'] = gacetas_territoriales()[1]
```

Resultado medido con este bloque: 1.290 filas nuevas (940 Gobernación, 350 Alcaldía), unos 1,1 MB.
Con las 702 actas, `entidades-territorial.jsonl` queda en 4.110 filas (hoy 2.118).

## `tools/leyes-senado/run_diario.sh`

Después de la etapa `entidades_territorial`:

```bash
  etapa --nombre entidades_gobernacion --timeout 900 \
        --desc "Gobernación de Antioquia: decretos y resoluciones por la Gaceta Departamental" \
        -- python3 tools/caudal/entidades/harvest_gobernacion.py fetch
  etapa --nombre entidades_alcaldia --timeout 900 \
        --desc "Alcaldía de Medellín: decretos, resoluciones y circulares por la Gaceta Oficial" \
        -- python3 tools/caudal/entidades/harvest_alcaldia.py fetch
```

El histórico de Medellín está congelado desde el 28-ago: `harvest_alcaldia.py fetch --historico 2026`
corre solo una vez, a mano. No va al cron.

## `catalogo.py`

Reemplazar las fichas de territoriales:

```python
    dict(k='asamblea-antioquia', nombre='Asamblea de Antioquia', alias=['asamblea de antioquia', 'asamblea departamental de antioquia'],
         estado='conectada', cubre=['Proyectos de ordenanza con su estado', 'Informes de ponencia', 'Ordenanzas (con PDF)',
                                    'Actas de sesión (con PDF)', 'Agenda de sesiones'],
         falta=[], nota=''),
    dict(k='concejo-medellin', nombre='Concejo de Medellín', alias=['concejo de medellin'],
         estado='parcial', cubre=['Proyectos de acuerdo con su estado', 'Acuerdos', 'Citaciones de control político',
                                  'Sesiones de plenaria programadas', 'Reuniones de comisiones permanentes',
                                  'Proponentes y ponentes de los proyectos abiertos a participación'],
         falta=['Texto de cada proyecto (PDF) y su ponencia'],
         nota='El sistema del Concejo bloquea la lectura automática de esos documentos.'),
    dict(k='gobernacion-antioquia', nombre='Gobernación de Antioquia', alias=['gobernacion de antioquia'],
         estado='conectada', cubre=['Decretos y resoluciones por la Gaceta Departamental (98 % de la serie de decretos de 2026)'],
         falta=['Título de los actos en gacetas escaneadas (número, fecha y PDF sí)'],
         nota='Los actos particulares de personal se cuentan, pero no se listan.'),
    dict(k='alcaldia-medellin', nombre='Alcaldía de Medellín', alias=['alcaldia de medellin', 'distrito de medellin'],
         estado='conectada', cubre=['Decretos, resoluciones y circulares por la Gaceta Oficial'],
         falta=[], nota='Los actos particulares y los movimientos presupuestales se cuentan, pero no se listan.'),
```

Nueva ficha, si se acepta la recomendación de abajo:

```python
    dict(k='contraloria', nombre='Contraloría General de la República', alias=['contraloria general'],
         estado='parcial', cubre=['Fallos con responsabilidad fiscal (panel de sanciones)'],
         falta=['Comunicados', 'Conceptos y jurisprudencia fiscal (relatoría)'], nota=''),
```

## Lambda y sitio (nadie más los toca: van en esta integración)

- `lambda_handler.py:4737` · `corps` solo tiene Asamblea y Concejo. Sumar `gobernacion de antioquia`
  y `alcaldia de medellin`, o las normas nuevas no llegan al radar.
- `lambda_handler.py:5512` · las próximas sesiones filtran `fuente == 'concejo-medellin'`. Sumar
  `asamblea-antioquia`.
- `lambda_handler.py:4574` · igual para las plenarias del Norte.
- `lambda_handler.py:5520` · el `tipo: 'acta'` caería como norma. Agregar `'acta': 'actas'`.
- `caudal.html:328-350` · el texto dice que faltan actas y agenda, y que la Gobernación no tiene
  fuente. Actualizarlo.
- `caudal.html:618` · `n:'2'` pasa a 4.
- `caudal.html:1422` · `TERR_F` necesita los filtros de Gobernación y Alcaldía.
- Sale todo junto, como la vez pasada: el sitio sin la Lambda queda desalineado.

## Contraloría General · recomendación

**Que entre como entidad, con ficha propia en `parcial`.** No puede quedarse en el pilar de control,
porque ahí no hay nada suyo.

Evidencia medida:

- **Pilar de control:** 10.861 registros, todos de `corte_constitucional`. Cero de la Contraloría.
- **Catálogo:** no tiene ficha, así que hoy sale como desconocida en «Tus entidades».
- **Panel de sanciones:** sí la cubre, con 60 fallos de `jr8e-e8tu` en datos.gov.co. Hay filas desde
  2007; no se midió el corte de ese dataset.
- **Diario Oficial:** 1 solo acto en 4.701 lleva su nombre en `entidad`, y no es de control fiscal.
  No es red de seguridad.
- **Comunicados:** viables. Liferay renderizado en servidor, último del 27-oct-2026, y 30 fechas de
  2026 en la primera página. Traen hallazgos y advertencias con cifra, que es lo que le importa a
  un cliente. Costo: medio día.
- **Relatoría:** `cgr-sistemarelatoria.contraloria.gov.co` es una aplicación de JavaScript que
  responde HTML vacío. No se exploró su API.
- **Boletín jurídico, decisiones destacadas y proyectos normativos:** sin documentos de 2026 en el
  HTML. La página de proyectos es un texto genérico, sin proyectos.

Orden sugerido: comunicados en la línea E, y la relatoría solo si un cliente la pide. El cliente que
pidió el seguimiento no la incluyó en su listado.

## Nota para CAUDAL.md

```markdown
#### Gobernación, Alcaldía, actas y agenda (`harvest_gobernacion.py`, `harvest_alcaldia.py`, `harvest_territorial.py` · nov-1-2026)

Tanda 5 del plan. Detalle y evidencia en `tools/caudal/entidades/integrar/territorio.md`.
- **Gobernación**: Gaceta Departamental, una página Joomla por año y un PDF por edición. Sumario digital
  en la página 2: número, fecha y página exactos. El título sale del OCR de la página del acto.
  ⚠️ 23 gacetas son escaneo puro: 454 actos sin título, marcados `sin_texto`. ⚠️ Las ediciones de un
  acto traen «Número · Descripción». ⚠️ Los nombres de archivo no son uniformes. 98,0 % de la serie de
  decretos de 2026. 83 % son actos particulares.
- **Alcaldía**: iframe a una app Laravel, con corte el 28-ago-2026: `consulta-publica` (fichas) e
  `historico-mercurio` (un acto por fila). ⚠️ 192 de 347 fichas traen objeto de relleno: el título sale
  del PDF. ⚠️ Un número `MED_` venía cortado. ⚠️ La 5969 tiene ficha y no está listada: no se publica.
  ⚠️ El id del PDF no es el número de gaceta.
- **Asamblea**: actas en la categoría 217. La categoría 227 murió en 2022: la agenda vigente es el ICS
  público del Google Calendar que embebe `/agenda/`.
- **Concejo**: ⚠️ el PDF y la ponencia viven en pestañas de SIMI. La petición que las carga la bloquea
  Cloudflare («Sorry, you have been blocked»). No se esquiva: es un control de seguridad del sitio.
  La ficha `interna-proyectos-de-acuerdo?simi_id=<data-rk>` solo existe para proyectos abiertos a
  participación; a los demás les responde 200 con una página genérica.
```
