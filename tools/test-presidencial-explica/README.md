# test-presidencial-explica

Lambda que recibe el `STATE` del test presidencial 2026 y devuelve una
lectura personalizada redactada por DeepSeek V3. Sin scoring propio —
solo redacción a partir de variables ya calculadas en el frontend.

## Estructura

```
tools/test-presidencial-explica/
├── lambda_handler.py     · código de la Lambda
└── README.md             · este archivo
```

## Variables de entorno

| Var | Default | Notas |
|---|---|---|
| `DEEPSEEK_API_KEY` | (vacío) | Obligatoria. Reusa la de agenda-medios-recomienda. |
| `DEEPSEEK_URL` | `https://api.deepseek.com/chat/completions` | |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | DeepSeek V4 Flash — rápido y barato, óptimo para redacción estructurada. |
| `S3_BUCKET` | `elecciones-2026` | Para cache |
| `CACHE_PREFIX` | `ricardoruiz.co/test-presidencial-2026/cache` | |
| `CACHE_TTL_DIAS` | `14` | Una respuesta cacheada vence en 14 días |

## Pruebas locales

```bash
export DEEPSEEK_API_KEY=sk-xxx
cd tools/test-presidencial-explica
python3 lambda_handler.py
```

Esto corre el handler con un sample real (Cepeda · popular · arquetipo
Castigo dominante) y muestra la respuesta JSON. Debe imprimir un objeto
con `lectura`, `mensaje_corto`, `alineacion`, etc.

## Deploy a AWS Lambda

### 1. Construir el ZIP

```bash
cd tools/test-presidencial-explica
zip -j ../../lambda-test-explica.zip lambda_handler.py
```

(No requiere dependencias externas — solo stdlib + boto3 que ya viene
en el runtime de Lambda.)

### 2. Crear el role IAM (una sola vez)

```bash
# Trust policy: permite a Lambda asumir el role
cat > /tmp/trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole" }
  ]
}
EOF

aws iam create-role --role-name lambda-test-presidencial-explica \
  --assume-role-policy-document file:///tmp/trust.json

# Permisos: CloudWatch logs + S3 sobre el prefijo del cache
aws iam attach-role-policy --role-name lambda-test-presidencial-explica \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

cat > /tmp/s3-cache.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::elecciones-2026/ricardoruiz.co/test-presidencial-2026/cache/*"
    }
  ]
}
EOF

aws iam put-role-policy --role-name lambda-test-presidencial-explica \
  --policy-name s3-cache --policy-document file:///tmp/s3-cache.json
```

### 3. Crear la Lambda

```bash
aws lambda create-function \
  --function-name test-presidencial-explica \
  --runtime python3.13 \
  --role arn:aws:iam::167386641785:role/lambda-test-presidencial-explica \
  --handler lambda_handler.handler \
  --timeout 30 \
  --memory-size 256 \
  --architectures x86_64 \
  --zip-file fileb://lambda-test-explica.zip \
  --environment "Variables={DEEPSEEK_API_KEY=sk-xxx}"
```

### 4. Crear API Gateway HTTP API

```bash
# 1) Crear la API
API_ID=$(aws apigatewayv2 create-api \
  --name test-presidencial-api \
  --protocol-type HTTP \
  --cors-configuration "AllowOrigins=*,AllowMethods=POST,OPTIONS,AllowHeaders=Content-Type" \
  --query 'ApiId' --output text)
echo "API_ID=$API_ID"

# 2) Lambda integration
INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:167386641785:function:test-presidencial-explica \
  --integration-method POST \
  --payload-format-version "2.0" \
  --query 'IntegrationId' --output text)

# 3) Route POST /explica
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "POST /explica" \
  --target "integrations/$INT_ID"

# 4) Stage default $default → auto-deploy
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --auto-deploy

# 5) Permiso para que API Gateway invoque la Lambda
aws lambda add-permission \
  --function-name test-presidencial-explica \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:167386641785:$API_ID/*/*"

# Endpoint final
echo "POST https://$API_ID.execute-api.us-east-1.amazonaws.com/explica"
```

### 5. Probar el endpoint

```bash
curl -X POST https://$API_ID.execute-api.us-east-1.amazonaws.com/explica \
  -H "Content-Type: application/json" \
  -d '{
    "registro": "popular",
    "candidato": {"id":"ic","nombre":"Iván Cepeda","partido":"Pacto Histórico"},
    "candidato_origen": "declarado",
    "demografia": {"edad":"36-50","identidad":"barrio"},
    "prio": ["salud"],
    "arquetipo_dominante": {"id":"castigo","nombre":"Castigo a la restauración y demanda de alternancia","pct":42},
    "arquetipo_secundario": {"id":"pertenencia","nombre":"Pertenencia comunitaria y autonomía territorial","pct":24},
    "arq_score": {"proteccion":2,"estabilidad":4,"supervivencia":2,"castigo":14,"pertenencia":8}
  }'
```

### 6. Updates posteriores del código

```bash
zip -j ../../lambda-test-explica.zip lambda_handler.py
aws lambda update-function-code \
  --function-name test-presidencial-explica \
  --zip-file fileb://../../lambda-test-explica.zip
```

## Frontend wiring

Una vez tengas el endpoint URL, en `test-presidencial-2026.html` se
añade en la sección de config:

```js
const EXPLICA_URL = 'https://XXXXX.execute-api.us-east-1.amazonaws.com/explica';
```

Y en `renderResultado()`:

```js
const body = {
  registro: STATE.registro,
  candidato: cand,
  candidato_origen: STATE.candOrigen,
  demografia: STATE.demo,
  prio: STATE.prio,
  arquetipo_dominante: { id: winnerId, nombre: winner.nombre_2027, pct: winnerPct },
  arquetipo_secundario: { id: secondId, nombre: second.nombre_2027, pct: secondPct },
  arq_score: STATE.arqScore,
};

fetch(EXPLICA_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})
  .then(r => r.json())
  .then(data => {
    $('#ai-message-body').textContent = data.lectura;
    // Opcional: data.mensaje_corto para el meme
  })
  .catch(() => {
    // fallback al placeholder actual
  });
```
