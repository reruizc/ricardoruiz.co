# Deploy · Lambda `leyes-en-vivo` (feed "Proyectos de ley en vivo")

Alimenta la sección **En vivo** de `legislativo.html` con los últimos 5
proyectos de ley radicados en Senado + Cámara (legislatura 2026-2027).

- **Código:** `tools/leyes-senado/leyes_en_vivo.py` (stdlib pura + boto3 del
  runtime — sin capa de dependencias).
- **Handler:** `leyes_en_vivo.handler`
- **Salida:** `s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/en-vivo.json`
  + PDFs en `…/legislativo/en-vivo/{senado,camara}/{NUMERO}.pdf`
- **Frontend:** ya lee ese JSON (`EN_VIVO_URL` en `legislativo.html`).

## Fuentes
- Senado: `POST leyes.senado.gov.co/api/search_pdly.php {legislatura:2026-2027}`
  + `GET get_detalle_pdly.php?id=N`. ⚠ WAF por fingerprint TLS ante ráfagas;
  el feed hace poco volumen (1 lista + 5 detalles + PDFs que falten) y es
  idempotente (no re-baja PDFs ya en S3). Bajo régimen casi no toca Senado.
- Cámara: `POST camara.gov.co/wp-admin/admin-ajax.php
  {action:download_proyectos_ley_xlsx, legislatura:20}` → XLSX ordenado del más
  nuevo al más viejo. `legislatura=20` = 2026-2027. Sin WAF agresivo.

## 1 · Empaquetar
```bash
python3 tools/leyes-senado/build_zip_en_vivo.py
# → tools/leyes-senado/leyes-en-vivo.zip  (solo leyes_en_vivo.py)
```

## 2 · IAM role (una vez · requiere admin, ricardo-mac-cli NO tiene iam:CreateRole)
```bash
aws iam create-role --role-name lambda-leyes-en-vivo \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name lambda-leyes-en-vivo \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name lambda-leyes-en-vivo --policy-name s3-legislativo \
  --policy-document '{"Version":"2012-10-17","Statement":[
    {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject"],
     "Resource":"arn:aws:s3:::elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/*"}]}'
```

## 3 · Crear la función
```bash
ACCOUNT=167386641785
aws lambda create-function --function-name leyes-en-vivo \
  --runtime python3.13 --architectures x86_64 \
  --role arn:aws:iam::$ACCOUNT:role/lambda-leyes-en-vivo \
  --handler leyes_en_vivo.handler --timeout 300 --memory-size 512 \
  --zip-file fileb://tools/leyes-senado/leyes-en-vivo.zip
```
(Timeout 300 s por los delays anti-WAF de Senado + descarga de PDFs.)

Actualizar código luego:
```bash
python3 tools/leyes-senado/build_zip_en_vivo.py
aws lambda update-function-code --function-name leyes-en-vivo \
  --zip-file fileb://tools/leyes-senado/leyes-en-vivo.zip
```

## 4 · EventBridge · 3×/día (08:00, 13:00, 18:00 hora Colombia = UTC-5)

> ⚠ **REQUIERE IDENTIDAD ADMIN.** `ricardo-mac-cli` NO tiene `events:*` ni puede
> auto-otorgárselo (`iam:PutUserPolicy` está bloqueado — guardarraíl anti-escalada).
> Corre estos 3 comandos con una identidad admin, **o** primero concédele a
> `ricardo-mac-cli` el permiso y luego corre los comandos con la CLI normal:
> ```bash
> aws iam put-user-policy --user-name ricardo-mac-cli --policy-name eventbridge-leyes-en-vivo \
>   --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["events:PutRule","events:PutTargets","events:DeleteRule","events:RemoveTargets","events:DescribeRule","events:ListTargetsByRule","events:EnableRule","events:DisableRule"],"Resource":"arn:aws:events:us-east-1:167386641785:rule/leyes-en-vivo*"}]}'
> ```
> Estado actual: la Lambda `leyes-en-vivo` YA existe y corre (probada, siembra S3);
> solo falta este trigger. Mientras tanto se puede refrescar a mano con
> `aws lambda invoke --function-name leyes-en-vivo /tmp/o.json`.

```bash
ACCOUNT=167386641785
aws events put-rule --name leyes-en-vivo-3x \
  --schedule-expression "cron(0 13,18,23 * * ? *)" \
  --description "Proyectos de ley en vivo · Senado+Cámara 3x/día"
aws lambda add-permission --function-name leyes-en-vivo \
  --statement-id evb-leyes-en-vivo --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:$ACCOUNT:rule/leyes-en-vivo-3x
aws events put-targets --rule leyes-en-vivo-3x \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:$ACCOUNT:function:leyes-en-vivo"
```

## 5 · Probar
```bash
aws lambda invoke --function-name leyes-en-vivo --payload '{}' /tmp/out.json && cat /tmp/out.json
curl -s "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/legislativo/en-vivo.json" | python3 -m json.tool | head
```

## Notas
- Si el WAF de Senado bloquea a la Lambda (fingerprint TLS de urllib), el feed
  conserva la última data buena de Senado (lee el en-vivo.json previo de S3
  antes de reescribir) y sigue mostrando Cámara. Alternativa si pasa seguido:
  bundlear `curl-cffi` (imita el TLS de Chrome) en una capa.
- Cámara 2026-2027 aún puede venir vacía (0 radicados); el feed lo maneja y el
  frontend muestra el estado "aún no hay proyectos".
- Bump del cache: el frontend agrega `?v=<hora>` al fetch; S3 sirve con
  `max-age=300`.
