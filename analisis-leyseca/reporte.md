# ¿Sirve extender la ley seca al viernes en Bogotá?

**Análisis histórico · 4 elecciones presidenciales 1V (2010, 2014, 2018, 2022)**
Datos: DIJIN — Policía Nacional · homicidio intencional + lesiones personales · año completo.

## El problema

La Alcaldía Mayor de Bogotá expidió el **Decreto Distrital 191 del 28 de
mayo de 2026**, que adelanta la ley seca al **viernes 29 de mayo 6:00 pm**
y la extiende hasta el lunes 1 de junio mediodía. A nivel nacional y en
Bogotá, la ley seca presidencial **ha arrancado siempre el sábado 6:00 pm**:
así fue en 2018 (gobierno Duque, Alcaldía Peñalosa, estándar nacional),
en 2022 primera vuelta (Decreto Nacional 830/2022, Alcaldía Claudia López)
y en 2022 segunda vuelta (Decreto Distrital 244/2022 de López). **2026 es
la primera elección presidencial en la que Bogotá adelanta el cierre al
viernes.**

La pregunta operativa: ¿el viernes pre-electoral en Bogotá ha sido
históricamente más violento que un viernes normal? Si no lo ha sido, la
ampliación no tiene base empírica para justificarse con datos de delito —
y, en cambio, los 4 viernes pre-electorales 2010-2022 son un contrafactual
limpio (sin ley seca) para evaluar la medida que ahora se aplica por
primera vez.

## Metodología

**Variable de tratamiento implícita:** ley seca durante la elección.
**Contrafactual válido para el viernes:** los 4 viernes pre-electorales
2010-2022 NO tuvieron ley seca a nivel nacional ni en Bogotá. Son
viernes electorales "limpios" del efecto de la medida que ahora propone Galán.

**Baseline:** promedio del mismo día de la semana del año, excluyendo el
fin de semana electoral (n≈51 por punto). Esto absorbe estacionalidad
semanal (viernes vs domingo vs lunes tienen patrones distintos).

**Tratamiento aplicado:** comparar día observado vs baseline del mismo
día de semana del año. Diferencia porcentual + dispersión.

**Limitación honesta:** sábado, domingo y lunes electorales han tenido
SIEMPRE ley seca (todas las elecciones 2010-2022). No hay contrafactual
directo para esos días: lo que medimos ahí es ley seca + día de
elecciones (movilización masiva, policía desplegada, cierre voluntario,
ciudadanía en casa votando). No es separable. Por eso el viernes es el
único día con contrafactual válido para la pregunta de Galán.

## Agregado 4 elecciones (2010 + 2014 + 2018 + 2022)

### Bogotá — el dato que importa para esta decisión

| Día                    | Observado Σ4 años | Baseline Σ4 años | Δ%       |
|------------------------|------------------:|-----------------:|---------:|
| **VIERNES (SIN ley seca histórica)** | **158 lesiones**  | **169.4**        | **−6.7%** |
| Sábado (con ley seca)  | 205               | 231.0            | −11.3%   |
| Domingo (elección, ley seca) | 158         | 294.0            | −46.3%   |
| Lunes (con ley seca)   | 142               | 167.2            | −15.1%   |

| Día (homicidios)       | Observado Σ4 años | Baseline Σ4 años | Δ%       |
|------------------------|------------------:|-----------------:|---------:|
| Viernes                | 7 (1, 2, 3, 1)    | 11.1             | −37.1%*  |
| Sábado                 | 6 (3, 2, 1, 0)    | 16.7             | −64.1%*  |
| Domingo                | 14 (3, 3, 4, 4)   | 23.4             | −40.1%*  |
| Lunes                  | 12 (1, 3, 4, 4)   | 10.6             | +13.6%*  |

\* En homicidios de Bogotá el N por día es 0-4 — los porcentajes son
estadísticamente débiles. Lesiones es la métrica con suficiente N.

### Nacional (control de robustez)

| Día (lesiones)         | Observado Σ4 años | Baseline Σ4 años | Δ%       |
|------------------------|------------------:|-----------------:|---------:|
| Viernes (sin ley seca) | 808               | 845.0            | −4.4%    |
| Sábado (con ley seca)  | 1.053             | 1.208            | −12.9%   |
| Domingo                | 1.079             | 1.766            | −38.9%   |
| Lunes                  | 892               | 1.027            | −13.2%   |

## Lectura

1. **El viernes electoral, en lesiones personales Bogotá, NO se distingue
   estadísticamente de un viernes normal del mismo año.** −6.7% sobre 4
   elecciones agregadas está dentro del ruido (la desviación estándar de
   un viernes promedio Bogotá es 11-13 lesiones; el delta observado es
   2-3 lesiones por viernes).

2. **El gran descenso es el domingo** (−46% lesiones Bogotá, −39%
   nacional). Eso es: ley seca + cierre electoral + nadie está en
   bares + transporte limitado + ciudadanía en casa votando. No es
   separable; no se le puede atribuir todo a la ley seca.

3. **Sábado y lunes electorales caen mucho menos que el domingo**
   (−11% sábado, −15% lunes en lesiones Bogotá). La ley seca rige todo
   el fin de semana, pero el efecto está concentrado en el día electoral.
   Sugiere que la mayor parte del descenso obedece al evento "elecciones",
   no al cierre de licores.

4. **El argumento "ampliar al viernes para reducir delitos" no se
   sostiene en datos históricos.** Los viernes pre-electorales Bogotá
   no tienen pico delictivo. Si la decisión es preventiva por temor a
   un viernes atípico esta vez, debería declararse así — no como medida
   con respaldo empírico.

## Nota metodológica

Este análisis es cuasi-experimental con controles temporales del mismo
día de semana (n=51 días/año por dow) y agregación de 4 ciclos electorales
para robustez. Es compatible con el marco OCDE-DAC (relevance + impact)
del [Lab de Políticas Públicas](https://ricardoruiz.co/evaluacion.html)
de este sitio. La principal limitación está documentada arriba: no hay
contrafactual limpio para sábado/domingo/lunes electorales porque la ley
seca ha sido universal en todas las elecciones del período. El viernes,
en cambio, sí lo tiene.

Datos crudos: Policía Nacional, DIJIN, Grupo de Información de
Criminalidad. Cobertura nacional + Bogotá D.C. Cifras agregadas a partir
de los Excel oficiales con código abierto en el repo del análisis.
