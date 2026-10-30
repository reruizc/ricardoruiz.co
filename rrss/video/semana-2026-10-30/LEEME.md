# Edición del 30-oct-2026 · Ley de Rescate Económico (PL 477 de 2026 Cámara)

Tres videos de ~2 minutos y una página interactiva. Todo sale del texto radicado, no de la prensa.

```
guion-v1-quien-paga.md         video 1 · ¿quién paga? (cuadros 01-08, incluye los dos diagramas de fuerzas)
guion-v2-como-le-pega.md       video 2 · ¿cómo le pega a usted? (cuadros 11-17) + dónde está cada dato en el PDF
guion-v3-polemicas.md          video 3 · los 8 artículos que van a dar pelea (cuadros 21-24 + 04·05·12·17) + texto literal y página de cada uno
fuente-reel-v1/                edición del video 1 (cortar.py + generar.py, patrón de semana-2026-10-28)
hallazgos-ley-rescate.md       notas de la lectura del PDF, con páginas
cuadros/{html,png}/            19 cuadros 1080×1920 · hoja-de-contactos.jpg
../../../ley-de-rescate.html   calculadora: perfil + ingreso → qué le cambia, con el artículo al lado
../../../tools/video-semanal/build_cuadros_2026-10-30.py   genera los cuadros (datos y páginas embebidos)
Bases de datos/video-semanal/2026-10-30/pl477.{pdf,txt}    el proyecto radicado y su texto extraído
```

## Verificación del documento
- `pl477.pdf` tiene SHA-256 `4a7e52938b91a30da837c41e3e6ad4a28e667d546aafac4add16892f5a6ef6cf`, igual al que sirve
  camara.gov.co en `wp-content/uploads/2026/10/proyectos-ley/documentos/proyecto-36548/PROYECTO-DE-LEY-Rescate-Economico-2026-VSD-RADICADA-1.pdf`.
  334 páginas, creado el 29-oct-2026 en Word. La ficha oficial (`camara.gov.co/ley-rescate-economico`) dice: 477/2026C,
  origen Cámara, radicado 29/10/2026, autor MinHacienda Miguel Gómez Martínez, estado «Trámite en Comisión».
- Páginas 1-213: exposición de motivos. 214-334: articulado (106 artículos). Las páginas de los cuadros son las del PDF.
- IVA: los artículos 42 (excluidos), 45 (servicios) y 46 (exentos) se compararon partida por partida con los artículos
  424, 468-1 y 477 vigentes bajados de la compilación oficial de la Secretaría del Senado (secretariasenado.gov.co,
  `estatuto_tributario_pr017/019.html`). Lo que no está en la lista nueva pasa al 19 % desde el 1-ene-2028 (el 468-1
  se deroga en esa fecha; los vehículos eléctricos, desde la vigencia de la ley).
- ⚠ Contradicción interna del proyecto: la exposición (p. 92) dice que no se gravan «la sal» ni «los granos», pero el
  artículo 42 no trae la partida 25.01 (sal) ni la 07.13 (legumbres secas: fríjol, lenteja, garbanzo). Se dice así en el
  video; no se afirma que sea intención.

## Lo que es cálculo propio (y así se rotula)
- «1 de cada 4 pesos es recorte»: Tabla 14 (p. 204), sumando eficiencia del gasto + gastos de personal + OPS sobre el
  efecto total de la ley: 25 % en 2027 y 2030, 21 % en 2028.
- «Cuánto más al mes» (cuadro 13 y la calculadora): salud nueva (art. 21) + retención nueva (art. 50) − retención actual
  (art. 383 ET), con la renta exenta del 25 % y sus topes (790 → 630 UVT), sin otras deducciones ni IVA. UVT $52.374,
  mínimo $1.750.905. Cruza con La Silla Vacía ($2,1 M/año con $6 M; $4,3 M con $10 M).
- La calculadora, para empresas, supone sueldos de 2,5 y 3,5 mínimos en los tramos 2-3 y >3.

## Fuerzas
- Internas: rosters oficiales de las Comisiones Terceras (camara.gov.co/representantes · API del Senado), 13 y 31
  miembros. Sin voto nominal de esta ley; la API del Senado no publica votaciones desde el 23-sep-2026 (no está el
  PGN 2027). El color es lo DICHO por cada bancada o persona entre el 29 y el 30 de octubre, con fuente en el cuadro 08.
  Precedente: comunicado del Senado del 11-dic-2024 (financiamiento archivada: Tercera Senado 8-6, Cuarta Senado 8-6,
  Cuarta Cámara 16-10).
- Externas: `tools/mi-congreso/build_fuerzas_externas.py --solo 477/2026C` solo encontró 2 titulares (consulta muy
  estrecha); el cuadro 08 se armó a mano con las citas de El Tiempo, Semana, Vanguardia, Infobae y La FM.
  ANDI, Fenalco, Fedesarrollo, Asobancaria y el CARF no tenían pronunciamiento al 30-oct a mediodía.

## Pendiente antes de publicar
- Mensaje de urgencia: no confirmado (El Tiempo lo daba por hecho antes de la radicación). Si lo hay, las comisiones
  sesionan juntas y la plenaria es de cuatro debates en dos.
- Si aparece el voto nominal del PGN 2027 o una postura formal de liberales/conservadores, regenerar el cuadro 07.
