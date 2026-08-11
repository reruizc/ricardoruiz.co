# ¿Quién queda? — mercados de pronóstico sobre elecciones de segundo grado

Índice de opción para las elecciones que **no** decide el voto popular: Contralor,
magistrados del CNE, Defensor, Procurador. Página pública: `quien-queda.html`.

```
motor.py            el motor (cosecha + scoring + estado)
mercados.json       definición de mercados — agregar uno NO requiere tocar código
run_pronosticos.sh  corrida cada 6 h (launchd)
co.ricardoruiz.pronosticos.plist   → instalado en ~/Library/LaunchAgents/
```

Salida local (gitignored) en `Bases de datos/pronosticos/`; pública en
`s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pronosticos/`
(ese prefijo ya está cubierto por la bucket policy — no hubo que tocarla).

## El cálculo

```
índice = 0,60·respaldo + 0,25·convergencia + 0,15·puntaje_norm
prob   = índice / Σ índices          (suma 100 entre todos los elegibles)
```

- **respaldo (60%)** — el componente de juicio. Lo mueve DeepSeek leyendo los
  titulares nuevos de cada corrida. Escala documentada en el `SYSTEM` del motor.
- **convergencia (25%)** — presencia en el reporteo, medida sola.
- **puntaje_norm (15%)** — el puntaje oficial del concurso, reescalado.

## Las salvaguardas (el ajuste es automático; la revisión, diaria)

| Riesgo | Mitigación |
|---|---|
| El modelo inventa un hecho | Todo ajuste debe citar un titular que exista **literalmente** en el corpus. Si no, se descarta y queda contado en `descartados_ultima`. |
| Un titular mal leído hunde a alguien | `MAX_DELTA = 12` puntos de respaldo por corrida. Con 4 corridas/día el techo sigue siendo 48, suficiente para una caída real. |
| Una nota especulativa pesa como una investigación | **`peso_medio()`**: referencia ×1,0 · secundario ×0,6 · desconocido ×0,35. Pondera **antes** del tope. No vetea a nadie: una exclusiva de un medio chico entra, pero mueve poco hasta que otro la confirme. |
| El modelo devuelve basura | Si el JSON no valida, se conserva el estado anterior (falla cerrado). |
| Nadie puede auditar | Cada cambio queda en `log` con titular, medio, enlace, peso de la fuente y cuánto se pidió vs cuánto se aplicó. La página lo publica. |
| El automatismo se desvía | **Revisión humana diaria** de Ricardo sobre el tablero; se corrige a mano lo que el modelo lea mal. Declarado en la página. |

⚠️ **La ponderación se agregó porque el caso ocurrió**: el modelo subió a Castro 6 puntos
por un titular especulativo de un diario regional ("En la sombra Uribe y Petro elegirán a
Andrés Castro Franco"). Con `peso_medio` ese mismo titular mueve 2 y, en la práctica, el
ajuste ya no se aplicó. Al agregar medios nuevos a las listas, mantener el criterio:
**reporteo político propio y verificable** para ×1,0; agregadores y prensa regional
establecida para ×0,6; el resto queda en el default conservador.

## Tres cosas que se midieron y cambiaron el diseño

**1. Buscar sólo por tema deja ciego al motor.** Con las consultas temáticas, el
corpus traía **un solo titular sobre Zuluaga, del 3-ago y favorable**, justo el día
en que Cambio publicaba que perdía los votos. La caída existía y el motor no la veía.
`queries_de()` añade una consulta **por candidato vivo**; con eso la nota de Cambio
entró y el modelo bajó a Zuluaga de 40 a 30 citándola.

**2. El share of voice proporcional ordena por ruido.** El corpus de una ventana son
decenas de titulares, no miles: en una corrida hubo **9 menciones en total**. Con
share proporcional, Zuluaga sacaba 0 y se hundía; Castro caía a 22% frente a Laverde
sólo por 2 menciones contra 6. La convergencia es **escalonada** (ausente 25 · presente
65 · fuerte 85 · líder 100), con suavizado de Laplace y media móvil. Mide *presencia*,
que es para lo que sirve, no volumen.

**3. "Cambió" tiene que ser un hecho, no un temblor de redondeo.** El suavizado movía
las probabilidades ±1 punto en cada corrida; sin filtro, la página habría dicho "se
acaba de mover" cuatro veces al día sin que pasara nada. Ahora sólo cuenta como cambio
un ajuste del modelo o un movimiento ≥2 puntos, y la página muestra **la fecha del
último cambio real**, no la de la última corrida.

## Gotchas

- ⚠️ **DeepSeek V4 devuelve `content` vacío con `finish_reason=length`** si el prompt
  es largo: gasta el presupuesto en razonamiento. Medido: con 8.000 de techo gastó
  8.000 tokens de razonamiento y devolvió nada. El motor arranca en **16.000** y
  reintenta con 24.000. Subir el techo no encarece: sólo se cobran los tokens generados.
- ⚠️ **Cambio Colombia y La Silla Vacía dan 403 a fetch directo** y Cambio aparece en
  Google News sólo vía la consulta por nombre. Si un mercado nuevo depende de un medio
  que Google News no indexa, hay que declararlo como hueco de cobertura.
- ⚠️ Los enlaces del log son URLs de Google News que **redirigen** al artículo. Es feo
  pero funciona; resolverlas exigiría una petición extra por titular.
- El homónimo del futbolista "Carlos Mario Zuluaga" se cae solo con el filtro
  `contexto` del mercado. No quitarlo.

## Operación

```bash
python3 tools/pronosticos/motor.py                  # todos los mercados abiertos
python3 tools/pronosticos/motor.py contralor-2026   # uno
python3 tools/pronosticos/motor.py --dry-run        # no escribe
python3 tools/pronosticos/motor.py --sin-llm        # sólo la parte medible

launchctl list | grep pronosticos                                   # ¿cargado?
launchctl kickstart -k gui/$(id -u)/co.ricardoruiz.pronosticos      # correr ya
tail -30 "Bases de datos/pronosticos/cron.log"
```

Cerrar un mercado tras la votación: poner `"estado": "cerrado"` en `mercados.json`.

## Pendiente · mover el cron a la nube

Hoy dispara **launchd en el Mac**, así que si el portátil está dormido a las 6:10 la
corrida se pierde (launchd la ejecuta al despertar). Para independizarlo hace falta
que `ricardo-mac-cli` tenga permisos de EventBridge, que hoy **no tiene**:

```
User: ricardo-mac-cli is not authorized to perform: events:ListRules
```

Con `events:PutRule`, `events:PutTargets`, `events:ListRules` y `events:DescribeRule`
otorgados, el motor se empaqueta como Lambda (rol `lambda-pronosticos`, que encaja en
el `PassRole` ya permitido) y se programa con:

```bash
aws events put-rule --name pronosticos-6h --schedule-expression 'rate(6 hours)'
aws lambda add-permission --function-name pronosticos-actualiza \
  --statement-id ev --action lambda:InvokeFunction --principal events.amazonaws.com
aws events put-targets --rule pronosticos-6h \
  --targets 'Id=1,Arn=arn:aws:lambda:us-east-1:167386641785:function:pronosticos-actualiza'
```
