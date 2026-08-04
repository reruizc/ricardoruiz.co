```
CAUDAL · calibración del eje 1 (¿va a avanzar?)
========================================================================

Histórico cargado: 14924 registros (proyectos de ley + actos legislativos)
Índice de trayectoria de firmantes: 4191 personas

[1] Auditoría anti-fuga (600 casos con el desenlace borrado + 200 con el índice de firmantes reconstruido a su época):
    OK — el vector de features no cambia en ninguno de los 800.

[2] Universo etiquetable (registro Senado): 10293 · tasa de ley 24.5%
    descartados por desenlace abierto: 508  (EN_TRAMITE vivo + SIN_DATO)
    resultados en el registro: {'ARCHIVADO_OTRO': 4172, 'ARCHIVADO_TIEMPO': 2817, 'LEY': 2521, 'RETIRADO': 555, 'EN_TRAMITE': 319}

[3] Partición temporal (out-of-time)
    train: radicados < 2015  → n=6364  ley=27.1%
    test : 2015-2024            → n=3653  ley=21.5%

[4] Desempeño
  train (en muestra): n=6364  base=0.271  AUC=0.8122  Brier=0.1444  logloss=0.4475
    top 10%: 0.805 de tasa vs 0.271 de base → lift 2.98×
  TEST out-of-time: n=3653  base=0.215  AUC=0.7447  Brier=0.1470  logloss=0.4574
    top 10%: 0.567 de tasa vs 0.215 de base → lift 2.64×

[5] Contra qué se compara (mismo test, misma métrica)
    solo "lo radica el Gobierno"               AUC=0.5827
    solo "es tratado internacional"            AUC=0.5308
    Gobierno + tratado + comisión              AUC=0.6945
    modelo completo                            AUC=0.7447

[5b] Rolling origin — se repite la validación moviendo el corte
     corte   n_train  n_test   AUC_test
     <2006     3828    6189   0.7429
     <2010     5097    4920   0.7668
     <2014     6166    3851   0.7370
     <2018     7141    2876   0.7379
     rango 0.7370–0.7668 · el número no depende de dónde se corte

    [contraste] split aleatorio 70/30: AUC=0.7885  — más optimista, ve el mismo cuatrienio de los dos lados

[6] Calibración en test (predicho vs observado por decil)
    decil     n   predicho  observado
       1    365    0.023      0.011
       2    365    0.060      0.096
       3    365    0.089      0.090
       4    366    0.116      0.126
       5    365    0.144      0.200
       6    365    0.173      0.164
       7    366    0.215      0.251
       8    365    0.272      0.263
       9    365    0.384      0.378
      10    366    0.688      0.566

[7] Aplicado al registro de Cámara (fuera del universo de entrenamiento)
    n=3785  tasa de ley observada=0.69%  AUC=0.6934
    Se reporta, no se corrige: en ese registro "llegar a ley" casi no se
    observa porque el que cruza queda bajo el registro del Senado. El AUC
    de aquí NO es comparable con el de arriba.

[8] Qué aprendió (peso en la escala original; + empuja a ley)
    es_acto_legislativo        -2.358
    gobierno                   +1.653
    com_economicas             +1.307
    orden_publico_fiscal       +1.186
    previo_llego_lejos         +1.131
    es_tratado                 +1.083
    entidad_control            +1.074
    autor_veterano             -0.934
    com_segunda                +0.932
    radica_tarde               -0.908
    com_tercera                +0.814
    tipo_honores               +0.712
    autor_muchas_leyes         +0.651
    previos_2                  -0.638
    com_cuarta                 +0.622
    firmas_1                   -0.516

[8b] Corrección de nivel por deriva de época: intercepto -1.454 → -1.495 (-0.041)
     media predicha en 2015-2024 ahora 0.215 contra 0.215 observado. No altera el orden (AUC intacto).

[9] Modelo final (reajustado sobre las 10293 filas) → /Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-modelo.json
    antecedentes por parecido de título: 452 de 1090 proyectos vivos · 250 ganan historia que el cluster exacto no veía → /Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-antecedentes.json
    trayectoria de 4146 firmantes hasta 2026 → /Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-autores.json
    subir:
      aws s3 cp "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-modelo.json" s3://caudal-legislativo/metadata/importancia-modelo.json
      aws s3 cp "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-autores.json" s3://caudal-legislativo/metadata/importancia-autores.json
      aws s3 cp "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/leyes-senado/dist/s3/importancia-antecedentes.json" s3://caudal-legislativo/metadata/importancia-antecedentes.json
```
