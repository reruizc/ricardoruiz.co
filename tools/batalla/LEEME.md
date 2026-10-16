# Anatomía de una batalla · `batalla.html` + `tools/batalla/`

Tablero en vivo de una **batalla de enmarcado**: la disputa entre bandos por cómo
queda contado un hecho con fecha y hora conocidas (una marcha, una votación, un
decreto). Nació para la marcha del 14-oct-2026 contra el gobierno De la Espriella. Idea de fondo: *la guerra es la continuación de la
política* (Clausewitz) y aquí la guerra es por quedar del lado correcto de la
historia; cada marcha, votación o decreto es una batalla de esa guerra larga.

```
batalla.html                     el tablero (sistema visual v2, lee S3 cada 2 min)
tools/batalla/batalla.py         recolector + clasificador + métricas
tools/batalla/batallas/<id>.json una batalla: bandos, marcos, hechos, actores, consultas
tools/batalla/ciudades.json      61 ciudades detectables con su centro (build_ciudades.py)
tools/batalla/run_batalla.sh     corrida + publicación (con candado y fecha de cierre)
tools/batalla/co.ricardoruiz.batalla.plist   agente launchd cada 10 min
Bases de datos/batalla/<id>/     corpus, clasificación en caché, salida, log (gitignored)
s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/batalla/<id>.json   (gzip, público)
```

## Qué mide (y de dónde sale cada cosa)

| Sección | Cálculo |
|---|---|
| Fases | Preparación → Despliegue → Choque → Quiebre → Desenlace → Secuelas, según los hechos reportados en los 90 min anteriores (`fase_en`) |
| Marcador | Ley cuadrática de Lanchester: `F = N² × q`. N = medios distintos que llevan un marco del bando; q = peso medio del medio (nacional 1 · oficial 0,8 · regional 0,6 · otro 0,4) |
| Frente | Cada marco como batallón: fuerza, primer disparo, medios nuevos en la última hora |
| Posesión | Marcador móvil de 3 h cada 30 min |
| Iniciativa | Para el primer choque de cada ciudad, cuánto tarda la voz del Gobierno y la de la Oposición |
| Voz oficial | Titulares cuya fuente destacada es el Gobierno; quién la repite y a qué ritmo |
| Colisión | % de titulares con los dos marcos; medios que solo llevan uno (cámaras de eco) |
| Matices | Mezcla de marcos dentro de cada bando (p. ej. indignación vs. reclamo social) |
| Terreno | Ciudades nombradas: tamaño = titulares, color = bando que más la enmarca, anillo = choque |
| Mirada externa | Prensa en inglés y financiera (riesgo vs. confianza) + TRM de datos.gov.co |

## Clasificación

Cada titular lo etiqueta **DeepSeek V4 Flash** con el libro de códigos del JSON de
la batalla (`marcos[].nota`): pertinencia, marcos (multi-etiqueta), nivel de hecho
(0-3) y **voz** (quién habla: G/O/T). Caché por titular en
`clasificacion.json`; al cambiar el prompt se sube `CLAS_VERSION` y se reclasifica
todo (~5-8 min la primera vez; después solo lo nuevo). El diccionario `terminos`
queda como respaldo (si no hay llave o falla el modelo) y como auditoría.
Llave: `DEEPSEEK_API_KEY` o, si no está, la de la Lambda `caudal-analiza` vía AWS CLI.

⚠️ Lo que aprendimos al calibrar (14-oct):
- Sin filtro de pertinencia se colaban notas ajenas: «Muertes en festival EDC»
  (Medellín) salió como primer choque de la marcha. El modelo marca `rel`; sin
  modelo, el `ancla` del JSON.
- La v1 confundía «la oposición convoca» con «Petro desestabiliza» y marcaba como
  choque los anuncios preventivos («Gobierno anuncia controles ante bloqueos»).
  Las definiciones del libro de códigos ahora lo excluyen explícitamente.
- Una marca de un actor NO es su voz: «Manifestaciones en rechazo a De la
  Espriella» nombra al Gobierno pero no habla el Gobierno. Por eso `v` existe.
- Google News trae títulos con mojibake (Aporrea): se re-decodifican al leer.

## Operación

```bash
python3 tools/batalla/batalla.py marcha-14oct-2026            # recoge y calcula (sin subir)
python3 tools/batalla/batalla.py marcha-14oct-2026 --subir    # + S3
python3 tools/batalla/batalla.py marcha-14oct-2026 --offline  # recalcula sin red
# agente cada 10 min (se apaga solo después de "hasta"):
cp tools/batalla/co.ricardoruiz.batalla.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/co.ricardoruiz.batalla.plist
launchctl bootout gui/$(id -u)/co.ricardoruiz.batalla          # apagarlo
```
`batalla.html?local=1` lee la salida local; `?b=<id>` elige otra batalla.

**Nueva batalla** = copiar el JSON, cambiar `id`, `inicio`, `hasta`, consultas,
actores y (si hace falta) marcos. No se toca código.

## v2 (14-oct-2026, noche): corte, sets, atención, departamentos y X

- **Corte** (`corte` en el JSON de la batalla): pasado el corte todo se calcula a esa hora, la
  página dice FINAL y deja de refrescarse. El agente launchd se apaga con `launchctl bootout`.
- **Fases recalibradas** (`fase_en`): choque = 2+ medios distintos con hecho de choque en 90 min;
  desenlace = pasadas 3 h, la atención cae bajo la mitad del pico; después de un choque no se
  vuelve a «despliegue». La regla vieja dejó la marcha en despliegue hasta las 7 p. m.
- **Sets**: horas seguidas con la misma fase = un set, con su ganador (≥55 % de la fuerza).
- **Ponderado por atención**: la fuerza móvil de 3 h de cada media hora pesa por los titulares
  de esa media hora frente al pico. Mide «pegó fuerte, pero cuando ya nadie miraba».
- **Departamentos** (`terreno_dep`): ciudades nombradas + nombres de departamento sin ambigüedad
  (fuera Bolívar, Nariño, Meta, Cesar, Magdalena… y Cauca solo si no es «Valle del Cauca»).
- **Choque o paralelas**: vocabulario propio/compartido (log-odds), ¿se miran? (qué parte de los
  titulares de cada bando nombra a un actor del otro), choque por tramos, puentes y cámaras.
- **X por tramos de 2 h** (`x_capa.py --ventanas --orden Top --gastar`): las publicaciones más
  destacadas de cada tramo; fuerza por tramo, nodos, respuestas y citas cruzadas, cuentas puente.
  `--reusar` reclasifica lo ya capturado sin volver a pagar. Captura del 14-oct: 1.580 ítems,
  668 únicos, US$0,334.
- **Respaldo de modelo**: DeepSeek se cayó la noche del 14-oct (timeouts y respuestas sin
  `choices`). `BATALLA_LLM=claude` usa Claude Opus 5.5 con esfuerzo bajo por HTTP directo (llave
  en `~/.config/caudal/anthropic.env`, mismo patrón que los briefs). Por defecto intenta DeepSeek
  y cae a Claude si falla.
- Página en pestañas, con el veredicto y los sets siempre arriba, repetición jugada a jugada,
  mapa por departamentos con tres modos y panel de detalle, batallones clicables y filtros.

## Lo que falta (en orden)

1. Capa X en vivo cada 30 min durante una batalla (hoy se corrió una vez, al corte).
2. **Capa estructural (Turchin)**: presión de fondo (salario real, precio de los
   alimentos, desempleo juvenil, competencia entre élites, estrés fiscal) como el
   «terreno» lento sobre el que se libran las batallas.
3. **Lentes por actor**: cómo entiende Colombia cada actor relevante (Abelardo,
   Petro, el inversionista) — qué marcos usa, qué teme, qué datos mira.
4. GDELT como segunda fuente de volumen y tono (API gratis, 1 consulta cada 5 s).

## v3 (16-oct-2026): prensa internacional aparte y lenguaje sin «ganar»

- **Prensa internacional** (`internacional()` en `batalla.py`): por el país del dominio (`dom`, que se guarda
  desde ahora) o, sin dominio, por la lista `INTERNACIONAL`. No suma al marcador, a las fases ni al mapa; va
  en `externa.internacional` y en la pestaña «Cómo nos ven afuera». En la marcha eran 90 titulares de 66
  medios, 68 % con el marco de la Oposición: al sacarlos, el despliegue y el choque quedaron parejos y el
  ponderado pasó de 59–41 a 70–30 para el Gobierno.
- **Lenguaje**: «ventaja», «puntos», «parejo» (bajo 55 %); nada de «ganó». El prompt de la lectura lo prohíbe
  (`LECTURA_VERSION` v5). `--sin-lectura` ahora conserva la lectura guardada (útil para una escrita a mano).
- **Colores** sin evocar partidos: Gobierno `#1f9e92` (verde azulado), Oposición `#d4702a` (naranja),
  validados para daltonismo; «los dos marcos» y «sin marco» en neutros.
