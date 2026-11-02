# Integración · línea C · bloqueados (tanda 4, 1-nov-2026)

Tres cosechadores nuevos: `harvest_supervigilancia.py`, `harvest_minhacienda.py` y
`harvest_presidencia.py`. No se tocó ningún archivo compartido. Las líneas de abajo ya se
probaron importando `build.py` desde un script aparte. Nada subió a S3.

Integrado en `main` el 2-nov-2026. El punto 8 se resolvió: el RSS no se usa.

## 1. `build.py`: entidades

Junto a las demás `_fuente_simple`:

```python
fuente_supervigilancia = _fuente_simple('supervigilancia', 'Superintendencia de Vigilancia y Seguridad Privada', 'Defensa')
fuente_presidencia = _fuente_simple('presidencia', 'Presidencia de la República', 'Presidencia de la República')
```

MinHacienda NO va por `_fuente_simple`: esa función deja `estado_vista` en «Consulta cerrada» y
pierde las marcas, y de estos borradores no se sabe si la consulta sigue abierta.

```python
def fuente_minhacienda():
    """Borradores de los que solo se tiene la dirección: el antibots no deja abrirlos.
    `objeto` le dice al lector que el título es reconstruido y que no hay texto."""
    ent, sector, fuente = 'Ministerio de Hacienda y Crédito Público', 'Hacienda y Crédito Público', 'minhacienda'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(C.RAW / 'minhacienda' / 'proyectos.json', {}) or {}).get('items', {})
    borr = []
    for r in items.values():
        b = borrador_sucop(r, ent, sector, fuente, hoy)
        b.update(objeto=r['objeto'], estado_fuente='Sin plazo conocido', estado_vista='Sin plazo conocido', n_documentos=0,
                 titulo_reconstruido=True, sin_texto=True, visto=r.get('visto') or '')
        borr.append(b)
    return borr, [], []
```

## 2. `build.py`: `FUENTES`

Sumar al final de la lista:

```python
           ('supervigilancia', fuente_supervigilancia), ('minhacienda', fuente_minhacienda),
           ('presidencia', fuente_presidencia),
```

## 3. `run_diario.sh`: etapas

Antes de `entidades_build`:

```bash
  etapa --nombre entidades_supervigilancia --timeout 300 \
        --desc "Supervigilancia: resoluciones, circulares, proyectos y noticias" \
        -- python3 tools/caudal/entidades/harvest_supervigilancia.py fetch
  etapa --nombre entidades_minhacienda --timeout 300 \
        --desc "MinHacienda: títulos de borradores desde el sitemap (sin texto, antibots)" \
        -- python3 tools/caudal/entidades/harvest_minhacienda.py fetch
  etapa --nombre entidades_presidencia --timeout 600 \
        --desc "Presidencia: prensa del sitemap y PDF directos de dapre" \
        -- python3 tools/caudal/entidades/harvest_presidencia.py fetch
```

Tiempos medidos: Supervigilancia ~40 s; MinHacienda 11 s; Presidencia ~7 min en la primera corrida
(60 notas y 140 cabeceras de PDF). Con pocos actos nuevos debería bajar a unos 2 min, sin medir aún.

`harvest_minhacienda.py fetch --todo` repasa los 1.077 sub-sitemaps en ~30 min. No va en el cron:
se corre a mano si salta la guarda.

## 4. `catalogo.py`: fichas

```python
    dict(k='supervigilancia', nombre='Superintendencia de Vigilancia y Seguridad Privada', alias=['vigilancia y seguridad privada', 'supervigilancia'],
         estado='conectada', cubre=['Resoluciones', 'Circulares', 'Proyectos propios', 'Noticias', DO],
         falta=['Conceptos: los congeló en 2018', 'Eventos: la sección está vacía'],
         nota='Varias resoluciones y circulares son PDF escaneados: se leen por el nombre que publica la entidad. '
              'Sus proyectos casi nunca publican el plazo de comentarios.'),
```

```python
    dict(k='minhacienda', nombre='Ministerio de Hacienda y Crédito Público', alias=['ministerio de hacienda', 'minhacienda', 'hacienda y credito publico'],
         estado='parcial', cubre=['Aviso de borradores propios, con título deducido de su dirección web', DO],
         falta=['Texto de sus borradores', 'Título oficial y plazo de comentarios de esos borradores',
                'Noticias, circulares y conceptos de su sitio'],
         nota='Todo su sitio está detrás de un antibots que bloquea abrir cada documento; solo queda abierto el mapa del sitio. '
              'Caudal avisa que hay un borrador nuevo y muestra lo que dice su dirección web, que puede ser una sigla o venir '
              'cortado, pero no tiene el texto. Lo expedido llega por el Diario Oficial.'),
```

```python
    dict(k='presidencia', nombre='Presidencia de la República', alias=['presidencia de la republica', 'presidencia'],
         estado='parcial', cubre=['Decretos y leyes', 'Directivas', 'Circulares y resoluciones ejecutivas', 'Prensa (notas y videos)', DO],
         falta=['Listado oficial de normativa de su sitio', 'Lo que expide y no pasa por el Diario Oficial'],
         nota='Su listado de normativa está detrás de un antibots y su archivo robots.txt lo excluye, y el conjunto en datos.gov.co '
              'está parado desde el 31 de agosto de 2026. Caudal parte del Diario Oficial y busca el PDF de cada acto en el sitio de '
              'Presidencia: una circular o directiva que no pase por el Diario Oficial no aparece. Las notas de prensa antiguas '
              'pueden traer el título deducido de su dirección web.'),
```

## 5. `tools/caudal/ejecutivo/harvest_decretos.py`: PDF de decretos y leyes

Aplicado en la integración. 94 filas de `normativa.jsonl` traen `url` vacía y `pdfs.json` tiene 89.
⚠️ `ejecutivo_*` corre en la EC2 y `harvest_presidencia.py` en el Mac: el mapa viaja por S3
(`metadata/presidencia-pdfs.json`, lo sube `build.py --subir`) y `fusionar()` lo lee de ahí. La EC2 toma
el cambio cuando el commit llega a `origin`; hasta entonces los decretos siguen sin enlace.

## 6. Lambda: que un borrador nuevo de MinHacienda llegue al radar

Sin esto el borrador sale en Consulta pública, pero no avisa: `_sucop_para_perfil` solo mira
consultas abiertas y estos no tienen plazo. `visto` es la fecha en que Caudal lo vio por primera vez
(en la línea base es el `lastmod`, para que el histórico no salga como novedad).

```python
    limite = (_sucop_hoy() - datetime.timedelta(days=15)).isoformat()
    hits = [r for r in _sucop()
            if (r.get('estado_consulta') in ('abierta', 'cierra_pronto')
                or (r.get('sin_texto') and (r.get('visto') or '') >= limite))
            and any(t in (r.get('q') or '') for t in temas)]
```

Y en la `accion`, antes del caso `if fin`:

```python
        if r.get('sin_texto'):
            accion = ('Borrador nuevo en el sitio de la entidad. Caudal no tiene su texto ni su plazo: '
                      'el título sale de la dirección web y hay que abrirlo en el navegador')
```

## 7. Nota para CAUDAL.md

```markdown
- **Tanda 4 (nov-01-2026):**
  **Supervigilancia** (`harvest_supervigilancia.py`): Odoo, tarjetas `s_dl_item`. ⚠️ «Hace 10 horas» y «Hoy» son plantilla, no
  fechas; la «Expedición» puede contradecir el radicado y manda el radicado (si el PDF no da la fecha, queda el 1.º de enero).
  ⚠️ Hay filas que enlazan otro documento: «Lineamientos… UAS» abre la resolución de plazos del reporte financiero 2026. En las
  filas sin radicado manda el PDF. Texto en Unicode NFD: recomponer antes de leer. SUCOP no tiene ninguna fila suya.
  **MinHacienda** (`harvest_minhacienda.py`): ⚠️⚠️ abrir un borrador con curl responde el bloqueo de Radware (`validate.perfdrive.com`),
  5 de 5 el 1-nov. Solo se lee `sitemap.xml`, que el `robots.txt` deja abierto. Todos los borradores están en `p_l_id=3441` (barrido
  completo de los 1.077: 2.551 URL). `lastmod` no es la fecha del borrador y el de 2024 es la migración: entra desde 2025.
  Slug cortado en 255 caracteres, duplicados con `-copiar-`. `titulo_reconstruido`, `sin_texto`, `fuente_minhacienda` propia.
  **Presidencia** (`harvest_presidencia.py`): ⚠️⚠️ el `robots.txt` de `dapre` prohíbe `/*/Forms/`, `/*?` y `/_*`: el listado de
  normativa y su RSS responden, pero NO se usan. Las páginas `Paginas/decretos-*.aspx` dan el reto de F5. El PDF directo sí está
  permitido: los números salen del Diario Oficial y se pide solo la cabecera (`curl -r 0-7`). `pdfs.json` alimenta los enlaces de los
  decretos en `harvest_decretos.py`; no van a `normas.json` para no duplicar. Prensa de `sitemap0.xml` (500 URL, ventana de ~50 días):
  se acumula; el título real sale de la nota, 60 por corrida, y se para si aparece el reto.
```

## 8. Decisión para Ricardo: el RSS de `dapre`

`dapre.presidencia.gov.co/normativa/_layouts/15/listfeed.aspx?List=7b8e3011-861d-4596-a922-51c16bfaead4`
responde sin reto y trae los 15 últimos actos del mismo día, con tipo y fecha: decretos, circulares
internas y la agenda regulatoria. Resolvería el hueco de lo que no pasa por el Diario Oficial. Pero la
regla `/*?` y la regla `/_*` del `robots.txt` lo excluyen, igual que `Forms/AllItems.aspx`.

No se usa y Presidencia queda parcial. Se pidió una vez durante el sondeo, junto con
`AllItems.aspx`, antes de leer ese `robots.txt`. Si se quiere usar, es una decisión aparte: no hay evasión técnica,
pero sería cosechar a diario lo que el sitio pide no rastrear.

## 9. Dónde corre

Las tres etapas corren en el Mac, igual que las demás `entidades_*`: es la misma IP con que se probó.
Si algún día se mudan a la EC2, hay que volver a medir, porque Radware y F5 suelen tratar peor las IP de
nube, y copiar antes `raw/{supervigilancia,minhacienda,presidencia}/`, que es la línea base de las guardas.

## 10. Conteos del 1-nov-2026

| Entidad | Medido | Sale al índice |
|---|---|---|
| Supervigilancia | 36 normas: 28 resoluciones y 8 circulares desde 2025, 21 de alcance general. 4 proyectos. 15 noticias | 4 borradores · 51 normas |
| MinHacienda | 88 borradores desde 2025 en el sitemap, 1 ya en SUCOP, 12 con título cortado | 87 borradores (79 de decreto, 8 de resolución) |
| Presidencia | 500 enlaces (351 notas y 149 videos) · 119 PDF (83 decretos, 6 leyes, 24 resoluciones ejecutivas, 5 circulares, 1 directiva) · 6 sin PDF por ahora | 530 normas (500 de prensa) |

Último dato por entidad: Supervigilancia, circular del 19-sep-2026 y noticia del 24-sep-2026.
MinHacienda, `lastmod` del 1-oct-2026. Presidencia, prensa del 1-nov-2026 y decreto del 29-oct-2026.

Títulos de prensa: 380 de 500 siguen reconstruidos mientras se abre el histórico. Bajan 60 por corrida.

## 11. Muestra comparada

**Presidencia, prensa.** 60 notas abiertas, título de la URL contra título real: 99,6 % de las palabras
del slug están en el título real y 58 de 60 coinciden del todo; las otras dos son abreviaturas del slug.
En 33 de 60 el slug recorta el título, sin decir otra cosa. No hubo ninguna contradicción.

**Presidencia, PDF.** 17 PDF bajados enteros (las 5 circulares, 6 decretos, 2 leyes y 4 resoluciones
ejecutivas): los 17 son el acto que dice el Diario Oficial, con objeto coincidente entre 0,81 y 1,00. Se
revisaron las circulares aparte porque su nombre de archivo no lleva fecha.

**Supervigilancia.** 10 documentos:
- 4 coinciden por texto.
- 2 escaneados coinciden, leídos como imagen.
- 3 escaneados no se compararon.
- 1 es un error de la fuente: «Lineamientos… UAS» abre otra resolución. Ya se corrige leyendo el PDF.

La fecha es la de publicación cuando no hay expedición, y puede ir unos días después del acto: la
circular 20261000000115CS es del 18-sep y figura el 19.

**MinHacienda.** No se puede abrir ningún borrador: 5 de 5 bloqueados por Radware, y se dejó de intentar.
Se comparó contra títulos oficiales de SUCOP, decretos y Diario Oficial de 2025-2026:
- 36 de 87 con ≥ 80 % de sus palabras en un título oficial, 24 entre 50 % y 80 %, 27 por debajo.
- De las coincidencias más altas se leyeron 14: 13 son el mismo asunto (Decreto 0573, 0368, 0510, 0977,
  0451, 1479…) y 1 es un falso cruce del comparador, no un error del título.
- Los 27 restantes incluyen borradores no expedidos y slugs opacos que no dicen nada por sí solos:
  «Cuipo», «Sach», «Hoy», «Planausteridaddelgasto2026». Por eso el aviso dice que el título es reconstruido.
- Varios borradores de 2025 ya se expidieron como decreto, y aquí no se puede saber cuáles.

## 12. Guardas probadas

Cada guarda se forzó y dejó el archivo anterior intacto:

| Caso | Resultado |
|---|---|
| Supervigilancia, 10 normas contra 999 | no publica |
| MinHacienda, 88 borradores contra 500 | no publica |
| MinHacienda, borrador quitado del archivo | reaparece como nuevo, con `visto` de hoy |
| Presidencia, 500 enlaces contra 2.000 | no publica |
| Presidencia, 14 nombres probados y ningún PDF | falla |
| Presidencia, `dapre` cerrada | se detiene y sale con error |

El reto de F5 se reconoció sobre la página real guardada del sondeo.

## 13. Rutas que se cerraron

| Ruta | Respuesta | Qué se hizo |
|---|---|---|
| `minhacienda.gov.co/w/<borrador>` | Bloqueo de Radware, 5 de 5 | No se reintentó |
| `dapre…/normativa/Paginas/decretos-*.aspx` | Reto de F5 | No se usa |
| `dapre…/normativa/normativa/Forms/AllItems.aspx` y RSS | Abren, pero `robots.txt` los prohíbe | No se usan (punto 8) |
| `dapre.presidencia.gov.co/sitemap.xml` | 404 | No existe |
| 15 sub-sitemaps de MinHacienda | 8 vacíos, 7 con 404 | Sin borradores |

Un PDF de `dapre` que no aparezca en 5 corridas se abandona: su nombre no sigue el patrón. Hoy son 6
(5 decretos y 1 resolución). El acto sigue en el pilar por el Diario Oficial, sin enlace.
