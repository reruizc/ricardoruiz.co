# Monitor mediático de Julián

Lambda horaria que consulta el índice RSS de Google News para agenda Bogotá y
menciones directas a Julián Rodríguez Sastoque. Escoge la noticia dominante,
pide a DeepSeek una guía de vocería y publica `monitor.json` para el frontend.

## Despliegue

1. Ejecutar `./build.sh`.
2. Crear la Lambda `julian-sastoque-agenda` (Python 3.14, x86_64, 256 MB, 60 s)
   y subir `deployment.zip`; handler: `lambda_handler.handler`.
3. Definir `DEEPSEEK_API_KEY` como secreto y
   `DEEPSEEK_MODEL=deepseek-chat`. El monitor desplegado usa este modelo porque
   entrega el JSON completo dentro del timeout de la ejecución horaria.
4. Conceder `s3:PutObject` sobre
   `ricardoruiz.co/julian-rodriguez-sastoque/agenda/monitor.json` en el bucket
   `elecciones-2026` y crear una regla EventBridge de una hora.

La Function URL pública sirve únicamente la última captura guardada (nunca el
secreto ni una invocación nueva a DeepSeek) y el frontend apunta a ella. Si no
existe o falla la captura, muestra un estado vacío explícito, sin fabricar
noticia ni recomendación.
