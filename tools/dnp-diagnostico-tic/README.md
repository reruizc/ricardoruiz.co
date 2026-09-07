# Aporte al diagnóstico del sector TIC · PND 2026-2030

Insumo para la estructura temática que coordina la DENDD (documento
"Diagnóstico del sector TIC en Colombia. Insumos para la construcción del Plan
Nacional de Desarrollo 2026-2030", septiembre de 2026).

Alcance: temas **6** (economía digital y transformación productiva), **7** (IA y
tecnologías emergentes), **9** (gobierno digital, ciudades y territorios
inteligentes) y **10** (confianza y seguridad digital).

- `fuentes.py` — inventario de fuentes con URL y nivel de verificación. Es la
  única fuente de verdad de las referencias: los otros dos archivos lo leen.
- `build_nota_temas.py` — genera la nota en .docx con el formato de las Pautas
  de la DENDD (reusa `tools/dnp-entregas/build_entrega2.py`). Con `--pdf`
  produce además la vista previa.
- `verificar_fuentes.py` — vuelve a pedir cada URL del inventario y reporta el
  código de respuesta. Correr antes de cada entrega, **desde una red sin proxy**.

## Regla de evidencia

Ninguna cifra entra al documento sin la publicación que la sostiene. Cada dato
se clasifica en tres niveles, definidos en el capítulo 2 de la nota:

| Nivel | Qué es | Uso |
|---|---|---|
| **A** | Reproducida por el contrato desde la fuente primaria, con rutina ejecutable | Citable directamente |
| **B** | Publicada por entidad oficial u organismo multilateral, con enlace identificado, sin cotejo página a página | Citable tras abrir el documento y confirmar el dato |
| **C** | De prensa o de resúmenes de terceros, sin publicación primaria identificada | **No citable**; sirve solo como pista |

`verificar_fuentes.py` comprueba que la URL responde, no que la cifra esté en el
documento: un "ok" suyo no sube una fuente de nivel B a nivel A.
