# Hilo Twitter/X — Cómo votó Colombia por edades · 1V 2026

Publicar jun 2026. Tuteo, datos. Link final → ricardoruiz.co
Fuente: edad de los sufragantes por puesto (Registraduría, 2018 y 2022) +
preconteo 1V-2026 por mesa (Registraduría) + proyección de población DANE.
Método: inferencia ecológica por puesto (estima comportamientos de grupo,
no de personas). 13 trinos · 1 imagen por trino (carrusel de 9 piezas).

Colores: 🔴 Cepeda / izquierda · 🔵 Abelardo / derecha.

---

**1/** 🧵 ¿A qué edades le ganó cada candidato en la primera vuelta? El voto es
secreto, pero la Registraduría sí publica cuántas personas votaron por edad en
cada puesto. Cruzamos eso con los resultados y reconstruimos la elección por
generaciones. Lo que salió 👇
[IMG 01_portada.png]

**2/** Primero, el panorama: ¿quién va adelante en cada departamento? La
izquierda sigue arriba en **18 de 33** —Caribe, Pacífico, suroccidente—. Pero
frente a una derecha ya unificada, su ventaja **se encogió en 20 de los 33**:
en Bogotá pasó de +25 puntos sobre el mejor de la derecha a apenas **+4**.
[IMG 02_shift_deptos.png]

**3/** ¿Y en votos propios? Ahí la izquierda NO se hundió: Cepeda igualó o
superó la votación de Petro en **27 de 33 departamentos** —Orinoquía, Amazonía,
Santander—. Pero cayó justo donde más votos hay: **Bogotá (−5,4 pp) y
Atlántico**. Resultado: clavada en su marca nacional (40,5% → 41,2%).
[IMG 03_mapa_shift.png]

**4/** Y ahí aparece lo importante: la elección fue, sobre todo, un **choque de
generaciones**. Entre los más jóvenes ganó Cepeda con claridad; entre los
mayores, Abelardo arrasó. Una línea baja, la otra sube, casi en espejo.
[IMG 04_perfil_2026.png]

**5/** Las cifras: 🔴 Cepeda se llevó cerca del **60% del voto de los 18 a 25
años** y apenas **7% entre los mayores de 60**. 🔵 Abelardo hizo el camino
inverso: 23% entre los jóvenes y **79% entre los mayores**. De hecho Cepeda
puntea en todas las edades… menos entre los mayores de 60, donde Abelardo se
dispara.

**6/** Lo más llamativo es que esto **se heredó de 2022**. Cepeda calcó el perfil
joven de Petro; Abelardo heredó —y amplificó— el perfil mayor de Fico. Cada
bloque se quedó con la edad de su antecesor; solo se hizo más extremo.
[IMG 05_herencia.png]

**7/** Vale la pena darle la vuelta: ¿de qué edades es el voto de cada uno? El
**49% de los votos de Cepeda viene de menores de 36**. El **38% de los de
Abelardo, de mayores de 60**. Paloma es aún más mayor: 7 de cada 10 de sus
votos son de personas de más de 45.
[IMG 06_electorado.png]

**8/** ¿Pasa solo a nivel nacional? No: pasa **ciudad por ciudad**. En Bogotá,
Cali, Cartagena, Barranquilla, Medellín y Bucaramanga el voto se voltea de joven
a mayor. Entre los dos punteros, los jóvenes se inclinan por Cepeda y los
mayores, por Abelardo. En todas.
[IMG 07_ciudades_edad.png]

**9/** Con matices: en **Cartagena y Cali** Cepeda barrió entre los jóvenes
(85% y 79% del duelo). En **Medellín y Bucaramanga** la pelea joven fue pareja
(Abelardo incluso puntea entre los jóvenes de Bucaramanga). Pero entre los
mayores, en las seis ciudades, ganó Abelardo.

**10/** Llevado al mapa, da para dos países distintos según la edad. 👇
🔴 Si solo votaran los jóvenes, Cepeda ganaría casi todo el país.
🔵 Si solo votaran los mayores, Abelardo ganaría en **todos** los departamentos.
[IMG 08_mapa_edad.png]

**11/** Las excepciones cuentan la historia: entre los **jóvenes**, Abelardo
aguanta en **Antioquia y los Llanos**. Y entre los **mayores**, donde menos mal
le va a Abelardo es en el Pacífico y el Caribe —Nariño, Cauca, Sucre— los
bastiones históricos de la izquierda. Ni ahí gana Cepeda al grupo mayor.

**12/** Cómo lo hicimos, sin letra chica: esto es **inferencia ecológica** —
estima cómo votó cada grupo de edad, no cómo votó cada persona (el voto sigue
siendo secreto). En las grandes ciudades, edad e ingreso van de la mano, así que
el voto de Cepeda entre mayores de barrios ricos se estima muy bajo. Y 2026 es
preconteo.

**13/** El resumen: una izquierda que resistió pero no creció, una derecha que se
unió, y un país partido por la edad como no se veía hace años. Toda la
metodología y los gráficos en alta:
👉 ricardoruiz.co
[IMG 09_cierre.png]

---

## Notas / control
- Margen cara a cara (Pacto − candidato de derecha más votado): izquierda
  adelante en 19 deptos (2022) → 18 (2026); el margen se cerró en 20/33.
  Bogotá +24,9 → +4,0. Flips a la derecha: Quindío, Risaralda; a la izquierda:
  Vichada. En Santander/Arauca/Casanare la izquierda RECORTÓ (fin del efecto
  Rodolfo). Fuente: blocs-depto.csv (h2h22/h2h26).
- Cepeda vs Petro por depto (share de válidos): creció en 27/33 (cae en Bogotá
  −5,4 · Atlántico −2,7 · Nariño −1,8 · Cauca −1,5 · Huila −0,3 · Valle −0,2).
  Nacional 40,5→41,2.
- Perfil nacional por edad (% del voto del grupo, IC95%): Cepeda 18-25 ~60
  (54-66), 61+ ~7 (3-13). Abelardo 18-25 ~23, 61+ ~79 (72-85). Fuente: fit_ei.py.
- Ciudades = duelo cara a cara Cepeda vs Abelardo (suma 100), fit_ei_geo.py.
- Electorado: Cepeda <36 = 21+28 = 49%. Abelardo 61+ = 38%. Paloma 46+ = 72%.
- Honestidad: EI no fija conducta individual; valores extremos (0%, 79%) van
  con su rango; en ciudades edad↔ingreso confunde el dato de mayores-Cepeda;
  2026 es preconteo (no escrutinio definitivo).

## Caption Instagram (carrusel 9 piezas)
Colombia votó por edades 🗳️ En la primera vuelta de 2026, la elección fue un
choque de generaciones: Cepeda barrió entre los jóvenes (≈60% de los 18-25) y
Abelardo entre los mayores (≈79% de los +60). Pasó en casi todas las ciudades y
casi todos los departamentos. Reconstruimos cómo votó cada grupo de edad
cruzando el preconteo con la edad de los sufragantes (Registraduría + DANE).
Desliza →
Metodología completa en ricardoruiz.co (link en bio).
#Elecciones2026 #Colombia #PrimeraVuelta #Cepeda #Abelardo #DatosElectorales
