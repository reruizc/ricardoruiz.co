# Sacar el cron de Caudal de la Mac → EC2

Decisión de sep-2026: el pipeline diario deja de depender del portátil. Corre en
una instancia chica de AWS con `cron`, **con los mismos scripts y el mismo estado**
(`rsync`), sin cambio de código. Evaluación completa en
`tools/caudal/salud/PLAN-salir-del-mac.md`; esto es la ejecución.

Por qué no Lambda + EventBridge, en una línea: la corrida dura ~40 min (Lambda
corta a 15), el diff diario vive en ~8 GB de estado en disco, y el WAF del Senado
castiga justo la ráfaga que un runtime vacío produciría.

## Lo que lanza Ricardo (una vez · cuenta admin)

`ricardo-mac-cli` está acotado a S3 y Lambda: no puede crear roles ni instancias.
Todo esto va con el perfil admin (`--profile admin` o el usuario raíz desde la consola).

### 1 · Rol de la instancia (sin llaves en disco)
```bash
cd /Users/ricardoruiz/ricardoruiz.co
aws iam create-role --role-name ec2-caudal-cron \
  --assume-role-policy-document file://tools/caudal/ec2/iam-trust-ec2.json
aws iam put-role-policy --role-name ec2-caudal-cron --policy-name caudal-cron \
  --policy-document file://tools/caudal/ec2/iam-policy-caudal-cron.json
aws iam create-instance-profile --instance-profile-name ec2-caudal-cron
aws iam add-role-to-instance-profile --instance-profile-name ec2-caudal-cron --role-name ec2-caudal-cron
```
La política solo escribe en `caudal-legislativo` y en los dos prefijos de
`elecciones-2026` que el cron toca, y lee la configuración de `caudal-analiza`
(de ahí sale la key de DeepSeek para los resúmenes ciudadanos).

### 2 · Llave SSH y grupo de seguridad (solo tu IP)
```bash
aws ec2 create-key-pair --key-name caudal-cron --query KeyMaterial --output text > ~/.ssh/caudal-cron.pem
chmod 600 ~/.ssh/caudal-cron.pem
MI_IP=$(curl -s https://checkip.amazonaws.com)
SG=$(aws ec2 create-security-group --group-name caudal-cron --description "Caudal cron · SSH" --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MI_IP/32"
```

### 3 · La instancia
`t4g.small` (2 vCPU ARM · 2 GB · ~USD 12/mes a demanda, ~USD 7 con Savings Plan)
· Amazon Linux 2023 arm64 · **50 GB** gp3 (el estado son ~8 GB y crece; el disco
cuesta ~USD 4/mes). Si los builds del dataset se quedan sin memoria pese al swap,
subir a `t4g.medium` (4 GB) es un `stop` + `modify-instance-attribute`.
```bash
AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --query Parameter.Value --output text)
aws ec2 run-instances --image-id "$AMI" --instance-type t4g.small \
  --key-name caudal-cron --security-group-ids "$SG" \
  --iam-instance-profile Name=ec2-caudal-cron \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]' \
  --user-data file://tools/caudal/ec2/user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=caudal-cron}]' \
  --query 'Instances[0].InstanceId' --output text
```
Espera ~5 min (cloud-init instala Python 3.12, aws CLI, clona el repo y deja el
crontab). Luego:
```bash
aws ec2 describe-instances --filters Name=tag:Name,Values=caudal-cron \
  --query 'Reservations[0].Instances[0].PublicDnsName' --output text
```
Ese DNS (o una IP elástica, si quieres que no cambie al reiniciar) es lo único
que me pasas. **Desde la consola web** es lo mismo: Launch instance → AL2023
arm64 → t4g.small → key `caudal-cron` → SG solo SSH desde tu IP → IAM profile
`ec2-caudal-cron` → 50 GB → *Advanced details → User data* = el contenido de
`user-data.sh`.

## Fase 0 · RESULTADO (20-sep-2026): la IP de AWS **no** es el obstáculo

Corrido desde `caudal-runner` (`13.221.66.8`, us-east-1) contra la Mac
(`186.28.93.164`, residencial colombiana), **el mismo script en las dos a la vez**
(`sondeo-waf.sh`), de madrugada.

| | Mac (residencial CO) | EC2 (us-east-1) |
|---|---|---|
| Senado · home ×4 | 4/4 · 0,58-1,6 s | **4/4 · 0,28 s** |
| Senado · API de la lista | 200 · 254 filas | 200 · **254 filas, idénticas** |
| BanRep ×5-6 (método del harvester) | 3/5 ok · 0 captcha | **5/6 ok · 0 captcha** |

**Va igual o mejor que la Mac**, y contra el Senado el doble de rápido (menos
saltos hasta el datacenter). No hay bloqueo por reputación del bloque de IP, que
era el riesgo que podía tumbar la migración entera.

**La prueba que de verdad importaba — la ráfaga:**

```
ráfaga 1   110 peticiones en 6 min          →  110 ok, cero bans
ráfaga 2   arrancada PEGADA a la anterior   →  ban en la petición 32
                                               (~141 acumuladas), rc=52
tras 10 min de reposo                       →  3/3 ok: el ban se levanta solo
```

`rc=52` («Empty reply from server») es **exactamente el síntoma que
`harvest_diario.py` documenta para la Mac**. Conclusión: el WAF trata a la EC2
**como a la Mac** — deja trabajar y corta por volumen acumulado, no por ser de
datacenter. El umbral observado (~141) fue incluso más alto que los ~85
documentados en la Mac.

⚠️ **Lo que esto NO prueba**, para no estirarlo más de lo que da:

- Es **una sesión de madrugada** (02:00-03:00 Bogotá), cuando el Senado tiene poco
  tráfico. De día el WAF puede estar más sensible.
- El umbral de ~141 es **una sola observación**, no una medida.
- **No se corrió el harvester completo.** Lo probado es el comportamiento del WAF,
  no el pipeline entero. El piloto largo de `piloto-waf.sh` (3-4 días en paralelo,
  comparando novedades con la Mac) sigue siendo el paso que falta antes de la Fase 2.
- La IP es la que tiene hoy esa instancia; sin IP elástica cambia al reiniciarla.

⚠️⚠️ **El BanRep exige el juego COMPLETO de headers.** Probándolo solo con `-A`
da captcha siempre y parece un bloqueo de IP que no existe — me pasó en este mismo
piloto y casi lo reporto como hallazgo. `sondeo-waf.sh` ya los lleva.

### Estado de la instancia al 20-sep

`caudal-runner` (t4g.small arm64, `i-002d6e063def76d1b`) llevaba **22 días
encendida sin nada**: sin repo, sin crontab, carga 0.00 (~USD 9 gastados,
~USD 12/mes si sigue). No es la del procedimiento de arriba: es **Ubuntu, sin
llave SSH y gestionada por SSM** (perfil `CaudalRunner`), así que se opera con
`aws ssm send-command`, no con `ssh`. O se usa para la Fase 1, o se apaga.

## Fase 1 · la partición NO es «lo que no tiene WAF»

⚠️⚠️ **El plan decía «mover las etapas sin WAF» y eso no se puede hacer así.** Las
etapas no son independientes: **comparten carpetas de estado en disco**, y una
familia partida en dos máquinas trabaja con datos a medias. Medido script por
script (20-sep-2026):

| etapas | grupo · estado compartido | WAF dentro |
|---|---|---|
| 19 | legislativo · `actas/` `diario/` `diario-camara/` `gacetas/` `en-vivo/` | **senado_radicados** |
| 11 | regulatorio · `supers/` | **banrep_fetch** |
| 6 | sucop · `sucop/` (temas_* también lee de ahí) | — |
| 3 | secop · `secop/` | — |
| 3 | ejecutivo · sin estado | — |
| 1 | `red_lista` · sin estado | — |

Los dos hosts con WAF caen en **grupos distintos**, y los dos son grandes. Casos
concretos de por qué no se puede partir dentro de un grupo:

- `supers_consolida` junta las 12 fuentes del pilar Regulatorio desde `supers/`.
  Si `banrep_fetch` cosecha en el Mac y el consolidado corre en la EC2, **el
  consolidado no ve lo del BanRep**: sale incompleto y `supers_verifica` lo tumba.
- `dataset_build` y `texto_index` leen `diario/` (Senado) **y** `diario-camara/`
  (Cámara) del disco. Partir Senado y Cámara obliga a sincronizar en cada corrida.
- `senado_radicados` también escribe en `actas/`, que es de donde comen
  `ordenes_*`, `bloqueo_*` y `citaciones_*`.

### La partición que sí funciona

**El BanRep se muda con su grupo.** La Fase 0 lo respalda: desde la EC2 dio 5/6
con cero captchas, mejor que el Mac. Queda:

```
Mac   19 etapas   todo lo legislativo (se queda el WAF del Senado)
      CAUDAL_ETAPAS="red_lista,senado_*,camara_*,ordenes_*,bloqueo_*,citaciones_*,dataset_*,texto_index,en_vivo,ritmo"

EC2   24 etapas   regulatorio + sucop + secop + ejecutivo
      CAUDAL_ETAPAS="red_lista,banrep_fetch,anla_*,dian_*,uiaf_*,supersociedades_*,supers_*,sucop_*,temas_*,secop_*,ejecutivo_*"
      CAUDAL_PUBLICA=no
```

**Estado a sincronizar: ~1 GB** (`supers/` 824 MB + `sucop/` + `secop/`), no los
14 GB del árbol completo. Eso cabe de sobra en los 21 GB libres de la instancia.

### Quién publica el latido

**Solo el Mac** (`CAUDAL_PUBLICA=si`, que es el default). No es arbitrario:
`check.py` no juzga únicamente las etapas que corrieron ahí, también mide la
**frescura de los 31 archivos de S3**, incluidos los que sube la EC2. Así que el
latido del Mac vigila el producto entero: si la EC2 deja de subir
`sanciones.jsonl` o `sucop.jsonl`, esos archivos envejecen y el Mac lo reporta.
**Cero cambios en el worker `rr-auth`.** La EC2 escribe igual su `estado.json`
local, que es lo que se mira al depurarla.

### Estado del despliegue (20-sep-2026)

Hecho y verificado **sin tocar producción**:

- Instancia preparada: swap de 2 GB (tenía 1,8 GB de RAM y **cero** swap),
  `pypdf` + `openpyxl`, repo clonado, zona horaria Bogotá, 21 GB libres.
- Estado sincronizado vía S3 (no hay llave SSH): `supers/` + `sucop/` + `secop/`,
  **835 MB → 120 MB comprimidos**.
- Etapas corridas a mano en la EC2, **sin subir nada**:

```
sucop_fetch        rc=0 · 3.994 carpetas
sucop_build        rc=0 · 3.984 procesos
supers_consolida   rc=0
supers_verifica    rc=0 · "80.770 actos · 7.333 sanciones · 17 fuentes,
                           ninguna por debajo de su piso"
supers_build_s3    rc=0 · 7.333 sanciones, COP 17,5 billones
ejecutivo_fetch    rc=0 · 12.030 filas
ejecutivo_build    rc=0
RAM durante todo:  1.359 MB libres · 16 MB de swap  → la memoria no es problema
```

Los 7.333 y los 12.030 **coinciden con lo que reporta la Lambda desde el Mac**,
así que el estado que viajó es el bueno.

⚠️⚠️ **Al sincronizar desde macOS: `COPYFILE_DISABLE=1 tar …`**. Sin eso el tar
mete un `._archivo` por cada archivo —los AppleDouble de los xattrs— que en macOS
son invisibles y en Linux son archivos de verdad: **se colaron 3.655** y
`supers_verifica` los leyó como fuentes fantasma («hay raw en disco pero NO salió
en el consolidado»). Se borran con
`find … -name '._*' -delete`, pero es mejor no crearlos.

**Falta solo el switch**, que tiene que ser simultáneo en las dos máquinas o
ambas suben los mismos objetos a S3 y cosechan dos veces las mismas fuentes
(el BanRep tiene WAF: dos ráfagas es peor que una):

```bash
# en la EC2
crontab /srv/caudal/ricardoruiz.co/tools/caudal/ec2/crontab-fase1
# en el Mac: añadir al plist de co.ricardoruiz.leyes-diario
CAUDAL_ETAPAS=!banrep_fetch,!anla_*,!dian_*,!uiaf_*,!supersociedades_*,!supers_*,!sucop_*,!secop_*,!ejecutivo_*
```

Rollback: `crontab -r` en la EC2 y quitar `CAUDAL_ETAPAS` del plist. El Mac
vuelve solo a correrlo todo, porque sin la variable corre las 44 etapas.

### El mecanismo

`run_diario.sh` acepta `CAUDAL_ETAPAS` (lista con comodines; `!` excluye) y
`CAUDAL_PUBLICA`. Sin ellas corre todo y publica, que es como corre el Mac hoy.
Pruebas: `bash tools/caudal/ec2/prueba-selector-etapas.sh` — verifican que la
partición **cubre todas las etapas, que ninguna queda sin dueño y que ninguna
corre en las dos** (salvo `red_lista`, que sí debe correr en ambas).

⚠️ Cazado por esas pruebas: `for pat in $CAUDAL_ETAPAS` sin comillas hace
**expansión de rutas** además de word splitting, y como `run_diario.sh` hace
`cd $REPO`, un patrón como `*` se expandía contra los archivos del repo. De ahí
el `set -f` dentro de `_le_toca`.

## Lo que hago yo después (con el DNS)

1. **Estado y secretos.** `tools/caudal/ec2/sync-estado.sh ec2-user@DNS` (~8 GB,
   resumible) y por scp `~/.config/caudal/alertas.env` + `~/.caudal.env` a
   `~/.config/caudal/` de la instancia (chmod 600). No van al repo ni al user-data.
2. **Fase 0 · piloto del WAF (3-4 días).** `tools/caudal/ec2/piloto-waf.sh` corre
   solo el rastreo del Senado desde la instancia, sin subir nada, y deja en
   `diario/piloto-waf.log` la IP, los 403, los timeouts y el archivo de novedades
   del día para compararlo con el de la Mac. La Mac sigue publicando.
3. **Fase 1 · lo que no tiene WAF** (Cámara, órdenes del día, SECOP, SUCOP, ANLA,
   consolidado regulatorio, dataset, gacetas) pasa a la instancia enseguida —
   `run_diario.sh` ya tolera que una etapa falle sin arrastrar a las demás.
4. **Fase 2 · el Senado** solo si el piloto pasó. Si la IP de AWS resulta
   bloqueada, esa etapa se queda en la Mac y el punto único de falla pasa de
   «todo» a «una etapa»; la alternativa es un VPS con IP colombiana.
5. Apagar los launchd de la Mac (`launchctl bootout`), no borrarlos, dos semanas.
   Rollback = volver a cargarlos.

## Operar la instancia
```bash
ssh -i ~/.ssh/caudal-cron.pem ec2-user@DNS
crontab -l                                            # las 6 líneas de tools/caudal/ec2/crontab
tail -f "/srv/caudal/ricardoruiz.co/Bases de datos/leyes-senado/diario/cron.log"
sudo tail /var/log/caudal-user-data.log               # si algo del arranque falló
```
El repo se actualiza solo a las 07:50 (`git pull --ff-only`): lo que se pushea a
`main` llega a la instancia sin scp. Los `run_*.sh` leen `CAUDAL_REPO` del
crontab y en la Mac siguen cayendo a `/Users/ricardoruiz/ricardoruiz.co`.

`gastos` (el lector de correos del banco) **se queda en la Mac**: es personal,
lee IMAP con tu contraseña de aplicación y no tiene por qué vivir en AWS.
