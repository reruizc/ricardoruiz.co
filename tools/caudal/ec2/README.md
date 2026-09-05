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
