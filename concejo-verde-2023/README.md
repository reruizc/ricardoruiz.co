# Primera vuelta 2026, leída hasta el barrio · el voto Verde en Bogotá

Deck de análisis electoral (9 láminas): **2 nacionales + 5 Bogotá + portada + cierre**.
Del resultado presidencial 1V 2026 al cruce del voto de dos concejales del
**Partido Verde** (Alianza Verde, Concejo de Bogotá 2023) con cómo votó hoy su
territorio (Cepeda vs Abelardo), barrio por barrio.

- `presentacion.html` — el deck (autocontenido salvo `img/`). Controles: → / espacio,
  ← atrás, **N** notas del orador, **F** pantalla completa, **?** ayuda.
- `presentacion.pdf` — respaldo (9 páginas 1280×720).
- `data.json` — cifras del cruce que cita el deck.
- `img/` — mapas (5 nuevos + 3 reutilizados del informe Pacto / charla Sabana).

## Estructura
1. Portada
2. Nacional · el resultado (Abelardo 43,7% · Cepeda 40,9% · mapa por depto)
3. Nacional · la fractura joven/mayor (perfil por edad)
4. Bogotá · quién ganó cada barrio (435 Cepeda / 223 Abelardo)
5. Ronald Vargas (Verde) · dónde está su voto (13.942, centro-occidente)
6. Ronald · el cruce → su gente ladea **Abelardo** (+2,8 pp vs ciudad)
7. Julián Espinosa (Verde) · dónde está su voto (19.565, sur popular)
8. Julián · el cruce → su gente calca a la ciudad y ladea **Cepeda** (63% en barrios Cepeda)
9. Cierre · "Dos Verdes, dos Bogotás" + nota metodológica

## Hallazgo
Mismo partido, dos electorados a lado y lado de la fractura 2026: Julián (Kennedy,
Bosa, Tunjuelito, Usme — sur popular) → Cepeda; Ronald (Suba, Engativá, Teusaquillo,
Fontibón — occidente de clase media) → Abelardo, +2,8 pp más que el promedio bogotano.

## Datos
- Concejales: `RONALD FELIPE VARGAS SANCHEZ` (COD_CAN 13) y `JULIAN ESPINOSA ORTIZ`
  (COD_CAN 2), `GCS_2023TER.csv`, dep 16, escrutinio **por mesa**.
- Agregación a barrio catastral por el mapa puesto→barrio PIP ya existente
  (`output_trasvase/bog-puesto-to-barrio-pip.json`). Cobertura 99,5%.
- Cruce contra el presidencial 1V 2026 por barrio
  (`output_trasvase/bogota-1v-por-barrio.json`, Cepeda/Abelardo).
- **Inferencia ecológica**: se mide cómo votó el *barrio* donde vive su voto, no la
  persona; Concejo 2023 y presidencial 2026 son elecciones distintas (3 años aparte).

## Regenerar
```bash
python3 tools/concejo-verde-2023/build.py     # data.json + los 5 mapas nuevos
# (re-extrae de GCS_2023TER.csv a /tmp si hace falta)
# PDF:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="concejo-verde-2023/presentacion.pdf" \
  "file://$PWD/concejo-verde-2023/presentacion.html"
```
