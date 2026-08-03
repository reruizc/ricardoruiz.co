# Sacar el cron de Caudal del Mac — evaluación y recomendación

**Estado: documento de decisión. Nada de esto está implementado.**
Escrito ago-2026, con el pipeline corriendo en el Mac vía launchd 2×/día.

---

## 1. El problema, dicho sin adornos

Hoy el dato que se le vende a un cliente depende de que **el portátil de Ricardo
esté despierto** a las 08:00 y a las 19:30. Si viaja, si el Mac se queda dormido,
si se llena el disco (250 GB, ya apretado), el pipeline no corre. `launchd` corre
la agendada perdida al despertar, así que el manifiesto se recupera solo — pero
entre medias el cliente ve dato viejo y nadie se lo advirtió.

Con el chequeo de salud de esta carpeta ya *sabemos* cuándo pasa. Lo que sigue es
que deje de pasar.

## 2. Por qué no es un `lambda deploy` y ya

Las tres razones están medidas, no supuestas:

1. **El estado vive en el filesystem local.** El diff diario compara contra
   `diario/{leg}/proyectos.json`, y el "¿ya tengo este PDF?" es un
   `pdf_path.exists()` sobre archivos en disco. Entre las órdenes del día, los
   textos y los raws de SECOP hay **~1,5 GB** de caché que hace que una corrida
   normal dure minutos en vez de horas. Un runtime efímero llega siempre frío:
   creería que todo es nuevo y bajaría todo de golpe.
2. **Ese "todo de golpe" es exactamente lo que el WAF castiga.**
   `leyes.senado.gov.co` banea ~10 min por ráfaga (fingerprint TLS + volumen).
   El ritmo lento embebido (3 s por ficha, 6 s por PDF, tope de 20 PDF por
   corrida) es lo que nos mantiene dentro. Eso implica **corridas largas**, y
   Lambda corta a los 15 min.
3. **Dependencias y binarios.** `pypdf` es externa (rompe el patrón
   stdlib+boto3 del resto de Lambdas del proyecto) y los scripts llaman a
   `/usr/bin/curl` y al `aws` CLI, que no vienen en el runtime de Lambda.

Traducción: no necesitamos *serverless*, necesitamos **una máquina POSIX barata
con disco persistente que no se duerma**. Eso cambia mucho el abanico.

## 3. Opciones

| # | Opción | Costo/mes | Trabajo | Riesgo |
|---|---|---|---|---|
| A | Dejarlo en el Mac + alertas | $0 | ya hecho | el Mac sigue siendo el punto único de falla |
| B | Mac como servidor (`pmset`, no dormir) | $0 | 15 min | sigue atado a un portátil que viaja |
| C | **EC2 chico (t4g.small) + cron** | **~$5-14** | **2-3 h** | **IP de datacenter frente al WAF** |
| D | Fargate + EFS + EventBridge Scheduler | ~$3-5 | 1-2 días | ídem IP, + un Dockerfile que mantener |
| E | VPS externo (Hetzner/DO) | ~$5 | 3-4 h | otro proveedor, credenciales AWS afuera |
| F | GitHub Actions programado | ~$0 | 1 día | estado en caché de 10 GB, IP compartida muy quemada |

Descartes rápidos:

- **F (GitHub Actions).** Restaurar y volver a guardar 1,5 GB de caché en cada
  corrida es más lento que la corrida, y los rangos de IP de los runners son de
  los primeros que un WAF colombiano bloquea. Además el repo es público: cada
  corrida quedaría a la vista. No.
- **D (Fargate).** Es la opción "bonita" y la más barata en estado estacionario,
  pero cada cambio de script pasa a ser `docker build` + push + revisión de la
  task definition. Para un dev solo, eso convierte un `Edit` de dos líneas en un
  despliegue. Vale la pena solo si algún día hay más de un pipeline.
- **E (VPS externo).** Igual de bueno que C, pero obliga a sacar credenciales de
  AWS a otro proveedor y a mantener dos consolas. Solo gana si la IP de AWS
  resulta bloqueada y la de Hetzner no — cosa que hay que medir, no suponer.

## 4. Recomendación: C, en dos fases, y con un piloto antes de mover nada

### Fase 0 — el piloto (medio día, imprescindible)

**El riesgo que puede tumbar toda la migración es la IP.** El Mac sale por una
IP residencial colombiana; una instancia de `us-east-1` sale por un rango de
datacenter que los WAF tratan mucho peor. Antes de mover nada:

1. Levantar la instancia, instalar `python3` + `pypdf` + `aws` CLI.
2. Correr **solo** `harvest_diario.py` desde ahí durante 3-4 días, en paralelo
   con el Mac (sin subir a S3: `build_diario_s3.py` sin `--upload`).
3. Comparar: ¿mismos proyectos?, ¿mismos PDFs bajados?, ¿aparece el 403/timeout
   del WAF?

Si la IP de AWS resulta bloqueada, la respuesta **no** es insistir: es quedarse
en la fase 1 (abajo), que ya resuelve el 70% del problema sin tocar el host
sensible.

### Fase 1 — mover lo que NO tiene WAF (bajo riesgo, gana solo)

Cuatro de las cinco familias de fuentes no tienen WAF y no dependen del estado
local pesado:

| Etapa | Host | ¿Estado local? |
|---|---|---|
| `camara_radicados` / `camara_upload` | camara.gov.co (wp-json) | snapshot chico |
| `ordenes_camara` | camara.gov.co | caché de PDFs (grande, pero movible) |
| `ordenes_senado_*` | senado.gov.co / secretariasenado.gov.co | caché de docs |
| `secop_*` | datos.gov.co | raws regenerables |

Estas se mueven a la instancia sin drama. En el Mac queda **solo la etapa del
Senado con WAF**. Ganancia inmediata: si el Mac está dormido, el cliente sigue
viendo Cámara, órdenes del día, bloqueo y SECOP al día; solo se atrasan los
radicados del Senado. El punto único de falla pasa de "todo" a "una etapa".

### Fase 2 — mover el resto (solo si el piloto salió bien)

1. `rsync -a "Bases de datos/leyes-senado/" ec2:/srv/caudal/` — el estado viaja
   tal cual, sin conversión. Ese es el argumento fuerte de C sobre D: **cero
   cambios de código**, los scripts ven el mismo árbol de directorios.
2. Rol IAM en la instancia (nada de llaves en disco) con permiso de escritura
   sobre `caudal-legislativo/metadata/*`, `radicados-*`, y sobre el prefijo
   público `ricardoruiz.co/congreso-2026/output/legislativo/*`.
3. `crontab` con las mismas dos horas, llamando al **mismo `run_diario.sh`**.
   El candado, los timeouts, `estado.json` y el chequeo de salud funcionan igual;
   ya no queda nada específico de macOS (el `stat` del rotador prueba BSD y cae a
   GNU). Lo único que hay que ajustar son las **dos primeras líneas**: `REPO` y
   el `PATH` que apunta a `/opt/homebrew/bin`.
4. Dejar el launchd del Mac desactivado, no borrado, una o dos semanas.

**Rollback:** `launchctl bootstrap` del plist y apagar el cron remoto. El estado
local sigue en el Mac; a lo sumo hay que re-`rsync` en sentido contrario.

### Dimensionamiento y costo

- `t4g.small` (2 vCPU ARM, 2 GB) bajo demanda ≈ **$12/mes**; con Savings Plan de
  1 año ≈ $7. Un `t4g.micro` (1 GB) alcanza si no se corre OCR — hoy el cron no
  lo corre — y baja a ~$6.
- EBS gp3 30 GB ≈ **$2,4/mes**. Con 1,5 GB de estado actual sobra sitio para dos
  años de PDFs.
- Total realista: **$8-15/mes**. Menos que una hora de consultoría.
- Alternativa de $0: apagar la instancia entre corridas con EventBridge
  (start/stop) — ahorra ~80% del compute pero suma piezas móviles. No vale la
  pena a este precio.

### Lo que NO hay que hacer al migrar

- **No paralelizar** "ya que hay más CPU". El límite es el WAF, no la máquina.
- **No** poner una Elastic IP y olvidarse: si esa IP queda baneada, el pipeline
  muere entero y sin aviso. El chequeo de salud lo detectaría a las 26 h; mejor
  vigilar el rc de la etapa del Senado desde el primer día.
- **No** meter secretos en el repo: `run_diario.sh` ya lee `~/.caudal.env`, que
  es el mismo mecanismo que funcionará en la instancia.

## 5. Quién vigila al vigilante

Una vez fuera del Mac, `check.py` corre en la misma instancia — con lo cual, si
la instancia se cae, nadie lo dice. El cierre correcto es que la **alerta** viva
en otro lado (Lambda + EventBridge leyendo `estado.json` desde S3, o el worker de
Cloudflare que ya existe). Eso es de la otra conversación; lo que hace falta de
este lado es publicar `estado.json` a S3 al final de cada corrida — una línea de
`aws s3 cp` en `run_diario.sh` el día que se decida el canal.
