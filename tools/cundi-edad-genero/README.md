# Votación por municipio × partido × sexo × edad — Congreso Cundinamarca

Estima la votación de **Cámara y Senado** en los **116 municipios de
Cundinamarca** (departamento electoral RNEC **15**, sin Bogotá), desglosada por
**sexo × grupo de edad** (10 celdas: H/M × {18-25, 26-35, 36-45, 46-60, 61+}),
**por cada lista y en general**, para **2022 (observado)** y **2026
(proyectado)**.

Adapta el motor de inferencia ecológica de `tools/edad-1v-2026/` (presidencial)
a Congreso, celdas sexo×edad y salida municipal.

## Qué es dato y qué es estimación

- **«En general»** (votantes por sexo×edad de cada municipio): **dato
  observado** en 2022 (RNEC Edad y Género, joint sexo×edad por mesa);
  **proyección DANE** en 2026 (no existe aún el Edad y Género 2026).
- **«Por partido»** (voto de cada lista por celda): **inferencia ecológica**
  RxC — las urnas nunca registran por quién votó cada grupo. Modelo Goodman/King
  con símplex, calibrado con la variación entre ~5.800 mesas (2022) / ~600
  puestos (2026) del departamento, y **ajustado por raking a los dos márgenes
  reales** de cada municipio (voto por lista + composición por celda). Por eso
  toda estimación cuadra exacto con los totales reales.

## Identificación: la edad sí, el sexo casi no

Diagnóstico medido sobre las mesas de 2022 (`probe` en los commits):

- **Edad**: la composición etaria varía mucho entre puestos y correlaciona
  fuerte con el voto (Pacto Cámara: corr(%18-25)=+0,40, corr(%61+)=−0,34) →
  el perfil de edad de cada lista es **robusto**.
- **Sexo**: las mesas están segregadas por sexo (%mujeres va de ~2% a ~99%
  entre mesas) **pero** el %mujeres NO predice el voto (corr ≈ 0). El dato no
  identifica un sesgo de sexo robusto. → se **penaliza el contraste de sexo**
  (β_Hg→β_Mg dentro de cada grupo) salvo que el dato lo sostenga; queda gap
  H−M < 2 pp. Un sesgo de sexo fuerte sería artefacto de esquina.
  Mejora pendiente para sexo: efectos fijos de puesto a nivel **mesa**
  (ver `reference_voto_genero_mesa_ef` en la memoria del proyecto).

## Incertidumbre (3 columnas por celda)

- `punto` — estimación central (cuadra con los totales reales).
- `cota_min`/`cota_max` — **cotas duras de Duncan-Davis (King)**: rango
  permitido por pura aritmética de márgenes, sin supuestos. Lo 100% defendible.
- `ic_lo`/`ic_hi` — **IC 90%** por bootstrap de municipios (incertidumbre del
  modelo de preferencias). Más estrecho que las cotas duras.

## Pipeline (orden de corrida)

```
python3 01_extract_edad.py    # Edadygenero.xlsx -> mesas Congreso 2018/2022 dep15 (joint sexo×edad)
python3 02_votes.py           # GCS_2022CON (mesa) + MMV declarados 2026 (puesto) -> votos por lista
python3 03_composition.py     # 2022 observado + 2026 proyectado (rho×DANE + IPF) por celda
python3 04_ei.py              # EI regularizada + raking municipal + cotas DD + bootstrap
python3 05_xlsx.py            # ensambla el Excel entregable
```

`common.py` — helpers (celdas, mapeo de bandas, loader DANE sexo×edad).

## Entregable

`Bases de datos/output_cundi_edad_genero/Cundinamarca_Congreso_Edad_Genero_2022_2026.xlsx`

Hojas: **Léeme** · **Resumen depto** (composición del electorado por lista) ·
**General 2022/2026** (votantes por sexo×edad por municipio) · **Senado
2022/2026** · **Cámara 2022/2026** (por lista, formato largo: punto + cotas +
IC) · **Beta (motor)** (β por celda + cotas duras).

Insumos intermedios (CSV) en la misma carpeta. Largo plano:
`ei-cundi-long.csv` (56.730 filas).

## Fuentes y claves

- RNEC Edad y Género `Edadygenero.xlsx` (sufragantes mesa × sexo × edad, 2022).
- Escrutinio Congreso 2022 `FINAL SUBIDA GCS/GCS_2022CON.csv`.
- Declarados Congreso 2026 por mesa `DEPTOS_DECLARADOS/MMV_..._15_..._1008.csv`.
- DANE `DANE-AreaSexoEdadDep-2018-2050_VP.xlsx` (población área×sexo×edad×depto).
- Códigos electorales RNEC consistentes 2022↔2026: Cundinamarca=15, Bogotá=16.
  Municipios alfabéticos 004 Agua de Dios … 340 Zipaquirá.

## Parámetros tuneables (`04_ei.py`)

- `PARTY_MIN_SHARE = 0.008` — umbral para nombrar una lista (resto → «Otras
  listas»; incluye circ. especiales afro/indígena/CITREP).
- `LAM_SEX_FRAC = 1.0` — fuerza del shrink al contraste de sexo.
- `LAM0_FRAC = 0.30` — ridge global (levanta ceros exactos sin aplanar la edad).
- `B_BOOT = 200` — réplicas de bootstrap.

## Decisiones

- Unidad de EI: **mesa** en 2022 (composición observada), **puesto** en 2026
  (composición proyectada — las mesas no persisten entre elecciones).
- Universo repartido = **válido + blanco** por corporación; nulos/no-marcados
  fuera. «En general» = sufragantes totales (incluye nulos).
- 2022 y 2026 NO se fuerzan a un set de partidos común (las coaliciones
  cambian); cada año lista sus propias listas reales.
