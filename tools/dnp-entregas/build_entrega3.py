#!/usr/bin/env python3
"""
Genera el Informe Técnico - Entrega 3 (contrato DNP-1025-2026) en formato
.docx, conforme a las Pautas de la DENDD. Reusa la infraestructura de formato
y el compilador de dos pasadas de build_entrega2.py (tabla de contenido y
listas con números de página reales, sin campos de Word).

Contenido contractual (Modificación No. 01): estado del arte del producto,
análisis estadísticos, comparativos y de tendencias sobre la información del
sector TIC, identificación de brechas territoriales, aplicación de modelos de
evaluación ex ante e intermedia, y reporte parcial con resultados y
visualizaciones preliminares.

Uso:
    python3 build_entrega3.py --figs DIR [--salida RUTA.docx]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Cm, Pt

import build_entrega2 as base
from build_entrega2 import (DIR_FIGURAS, FUENTE, LOGO, NEGRO, compilar,
                            configurar_estilos, encabezado_paginado, figura,
                            margenes, parrafo, portada, salto, tabla, titulo,
                            toc_estatica)

SALIDA_DEFECTO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Bases de datos", "DNP", "productos",
    "Entrega3_InformeTecnico_RuizCastro_v1.docx",
)

# --------------------------------------------------------------------------

def pagina_legal(doc):
    titulo(doc, "Página legal y control documental", 1)
    parrafo(doc,
            "Este documento corresponde a la tercera entrega del contrato de "
            "prestación de servicios profesionales DNP-1025-2026 y se elabora "
            "para uso de la Dirección de Economía Naranja y Desarrollo Digital "
            "del Departamento Nacional de Planeación. Su contenido puede "
            "reproducirse total o parcialmente citando la fuente. Las cifras de "
            "avance de la política provienen de reportes institucionales "
            "parcialmente en revisión y no constituyen todavía el dato oficial "
            "definitivo.")
    tabla(doc, "Control documental",
          ["Campo", "Contenido"],
          [["Título", "Estado del arte, análisis del sector TIC y evaluación "
                      "preliminar de la Política Nacional de Inteligencia Artificial"],
           ["Tipo documental", "Informe técnico"],
           ["Entrega contractual", "Entrega 3 de 4 – contrato DNP-1025-2026"],
           ["Versión", "1"],
           ["Dependencia responsable", "Dirección de Economía Naranja y Desarrollo Digital"],
           ["Elabora", "Ricardo Esteban Ruiz Castro, contratista"],
           ["Revisa y aprueba", "Edwin Alejandro Buenhombre Moreno, Director Técnico"],
           ["Fecha de la versión", "Agosto de 2026"],
           ["Fecha de corte de la información", "Estadística sectorial: 4 de agosto de 2026. "
            "Reportes de SisCONPES: 21 de julio de 2026."]],
          "elaboración propia.", anchos=[4.5, 11.5])


def siglas(doc):
    titulo(doc, "Siglas y abreviaturas", 1)
    tabla(doc, "Siglas y abreviaturas empleadas en el documento",
          ["Sigla", "Significado"],
          [["CONPES", "Consejo Nacional de Política Económica y Social"],
           ["DANE", "Departamento Administrativo Nacional de Estadística"],
           ["DENDD", "Dirección de Economía Naranja y Desarrollo Digital"],
           ["DNP", "Departamento Nacional de Planeación"],
           ["ECV", "Encuesta Nacional de Calidad de Vida"],
           ["FTTH", "Fibra óptica hasta el hogar (fiber to the home)"],
           ["HFC", "Red híbrida de fibra y coaxial (hybrid fiber-coaxial)"],
           ["IA", "Inteligencia artificial"],
           ["IPD", "Índice de Pobreza Digital"],
           ["MinTIC", "Ministerio de Tecnologías de la Información y las Comunicaciones"],
           ["ONIA", "Observatorio Nacional de Inteligencia Artificial"],
           ["PAS", "Plan de Acción y Seguimiento"],
           ["SisCONPES", "Sistema de Seguimiento a Documentos CONPES"],
           ["SODA", "Interfaz de consulta del Portal de Datos Abiertos (Socrata Open Data API)"],
           ["TIC", "Tecnologías de la información y las comunicaciones"],
           ["xDSL", "Tecnologías de línea de abonado digital sobre par de cobre"]],
          "elaboración propia.", anchos=[3.0, 13.0])


def presentacion(doc):
    titulo(doc, "Presentación", 1)
    parrafo(doc,
            "Las dos primeras entregas de este contrato construyeron el andamiaje "
            "del estudio: el plan de trabajo, el marco conceptual y normativo, el "
            "inventario de fuentes y la matriz de indicadores. Esta tercera "
            "entrega es la primera que produce resultados. Analiza la información "
            "del sector con datos reales, aplica los modelos de evaluación de "
            "diseño y de avance intermedio sobre la Política Nacional de "
            "Inteligencia Artificial, y presenta las visualizaciones que "
            "acompañarán el documento final.")
    parrafo(doc,
            "Del análisis se desprenden cuatro hallazgos que organizan la exposición. El sector crece y se "
            "moderniza —la fibra óptica al hogar casi cuadruplicó su "
            "participación en cinco años—, pero diverge territorialmente: seis "
            "departamentos de la periferia retrocedieron en accesos fijos "
            "mientras el país crecía 27,5%. La política está financiada y "
            "reporta con disciplina, pero llega rezagada: el avance físico "
            "promedio es del 43,3% y quince de las dieciocho acciones que "
            "vencían en 2025 cerraron sin cumplimiento total. Un cuarto de las "
            "acciones ya está finalizado, incluidos hitos verificables como la "
            "estadística oficial de pobreza digital. Y el rezago no es neutro: "
            "las acciones asociadas al enfoque de derechos y a los grupos "
            "poblacionales excluidos —el foco de este contrato— figuran entre "
            "las de menor avance.")
    parrafo(doc,
            "En cuanto a su destinatario, el informe se dirige a la supervisión "
            "del contrato y al equipo del Centro de Pensamiento de Desarrollo "
            "Digital, y sus resultados son preliminares por diseño, puesto que "
            "la entrega final consolidará el análisis con el cierre de la "
            "vigencia y con los reportes aprobados del segundo semestre.")


def resumen_ejecutivo(doc):
    titulo(doc, "Resumen ejecutivo", 1)
    parrafo(doc,
            "Este informe constituye la tercera entrega del contrato "
            "DNP-1025-2026 y presenta el estado del arte del producto, el "
            "análisis estadístico y territorial del sector TIC, y la primera "
            "aplicación de los modelos de evaluación ex ante e intermedia sobre "
            "la Política Nacional de Inteligencia Artificial, con corte "
            "estadístico al 4 de agosto de 2026 y corte de reportes de ejecución "
            "al 21 de julio de 2026.")
    parrafo(doc,
            "Sobre el sector, el análisis documenta una transformación de "
            "profundidad más que de extensión: mientras los accesos fijos "
            "crecieron 27,5% entre 2019 y 2023, la proporción con velocidades de "
            "cien megabits o más pasó del 3,5% al 67,1%, la fibra al hogar "
            "multiplicó por casi cinco su participación y los estratos 1 y 2 "
            "llegaron a concentrar el 47,3% del parque, creciendo por encima del "
            "promedio nacional. La cara opuesta es territorial: seis "
            "departamentos periféricos —Guainía, Guaviare, Vichada, Amazonas, "
            "Chocó y Vaupés— retrocedieron en términos absolutos, uno de cada "
            "cuatro municipios reporta menos de cien accesos fijos, y la brecha "
            "activa del país ya no es de nivel sino de divergencia: crece más "
            "donde ya había más.")
    parrafo(doc,
            "Sobre el diseño de la política, la evaluación ex ante encuentra una "
            "formulación que aprendió las lecciones territoriales y "
            "diferenciales de su antecesora, pero con tres vacíos "
            "estructurales: asigna quince veces más recursos a infraestructura "
            "que a capacidades sin explicitar la hipótesis que conecta ambas; su "
            "sistema de seguimiento contiene 76 indicadores de gestión y 30 de "
            "producto pero ninguno de resultado; y su ejecución descansa en un "
            "núcleo de tres entidades que participa en el 80,2% de las acciones, "
            "mientras la mitad de las 56 entidades involucradas figura en una "
            "sola.")
    parrafo(doc,
            "Sobre la ejecución, el avance físico promedio es del 43,3% con "
            "financiación completa: el freno no es presupuestal. Veinticuatro "
            "acciones están cerradas —incluida la estadística oficial de pobreza "
            "digital, que este estudio usa como referente de resultado—, pero "
            "quince de las dieciocho que vencían en 2025 terminaron sin "
            "cumplimiento total, el núcleo de gobernanza está en mora y las "
            "acciones del enfoque de derechos, precisamente las que protegen a "
            "los grupos priorizados por la propia política, figuran entre las de "
            "menor avance. El hallazgo distributivo se replica en el terreno: en "
            "el programa de formación en inteligencia artificial analizado, la "
            "brecha de género se produce en el acceso y no en la permanencia.")
    parrafo(doc,
            "De cara a la entrega final, el informe deja tres productos "
            "operativos: un conjunto de rutinas reproducibles que permiten "
            "actualizar todas las cifras sectoriales sin procesamiento manual; "
            "tres ajustes concretos a la matriz de indicadores, derivados de la "
            "evidencia; y una alerta temprana sobre el rezago de las acciones de "
            "equidad, formulada a tiempo para que sea corregible dentro de la "
            "vigencia. Las recomendaciones estratégicas consolidadas "
            "corresponden a la entrega final de diciembre.")


def introduccion(doc):
    titulo(doc, "1. Introducción", 1)
    parrafo(doc,
            "Este informe corresponde a la tercera entrega del contrato "
            "DNP-1025-2026, que según la modificación número 1 comprende la "
            "presentación del estado del arte del producto, los análisis "
            "estadísticos, comparativos y de tendencias sobre la información del "
            "sector TIC, la identificación de brechas territoriales, la "
            "aplicación de modelos de evaluación ex ante e intermedia, y un "
            "reporte parcial con resultados y visualizaciones preliminares.")
    parrafo(doc,
            "Para cumplir ese encargo, el documento se organiza alrededor de tres "
            "preguntas encadenadas: cómo se está comportando el sector TIC y "
            "dónde se concentran sus brechas; qué tan bien diseñada está la "
            "Política Nacional de Inteligencia Artificial para producir los "
            "resultados que promete; y cuánto ha avanzado su ejecución al corte "
            "disponible. Dado que cada una corresponde a un tipo de análisis "
            "distinto —descriptivo, de diseño y de implementación—, se abordan "
            "por separado y confluyen luego en la síntesis del capítulo 9.")
    parrafo(doc,
            "En materia de alcance, el documento mantiene las delimitaciones "
            "fijadas en la Entrega 2, de manera que el análisis cubre las políticas del sector TIC vigentes en 2026, con el "
            "CONPES 4144 como instrumento central. Las cifras de avance provienen "
            "del corte del 21 de julio de 2026 y una parte de los reportes está "
            "aún en revisión, de modo que los valores pueden ajustarse; el "
            "documento lo advierte en cada caso. La evaluación de impacto en "
            "sentido estricto —el efecto causal atribuible— corresponde a la "
            "entrega final y solo en la medida en que los datos la permitan.")
    parrafo(doc,
            "En cuanto a su organización, el informe presenta en el capítulo 2 el "
            "estado del arte del producto junto con los referentes metodológicos "
            "que sustentan los modelos aplicados, y en el 3 la metodología. Los "
            "capítulos 4 y 5 desarrollan el análisis del sector y de sus brechas "
            "territoriales, mientras que los capítulos 6 y 7 recogen la "
            "evaluación ex ante del diseño de la política, repartida entre el "
            "examen del diagnóstico y los recursos, por un lado, y el del sistema "
            "de medición y la capacidad de ejecución, por otro. El capítulo 8 "
            "presenta la evaluación intermedia de la ejecución, el 9 la síntesis "
            "de resultados preliminares y el 10 las conclusiones parciales junto "
            "con los próximos pasos hacia la entrega final.")


def estado_arte(doc):
    titulo(doc, "2. Estado del arte del producto", 1)

    titulo(doc, "2.1. Estado de los componentes", 2)
    parrafo(doc,
            "El producto contractual —un documento de análisis de datos y "
            "evaluación de impacto de las políticas públicas del sector TIC— se "
            "construye de forma acumulativa a lo largo de cuatro entregas. Al "
            "corte de esta entrega, sus componentes presentan el siguiente "
            "estado.")
    tabla(doc, "Estado de los componentes del producto contractual",
          ["Componente", "Estado", "Dónde se desarrolla"],
          [["Plan de trabajo y enfoque metodológico", "Completo", "Entrega 1"],
           ["Marco conceptual y normativo", "Completo", "Entrega 2, capítulos 3 y 4"],
           ["Inventario de fuentes de información", "Completo y verificado", "Entrega 2, capítulo 7"],
           ["Matriz de indicadores de resultado e impacto", "Propuesta, en validación", "Entrega 2, capítulo 8"],
           ["Base del Plan de Acción y Seguimiento procesada", "Completa", "Entrega 2, capítulo 10"],
           ["Análisis estadístico y de tendencias", "Primera versión", "Este informe, capítulo 4"],
           ["Identificación de brechas territoriales", "Primera versión", "Este informe, capítulo 5"],
           ["Evaluación ex ante (diseño)", "Primera versión", "Este informe, capítulo 6"],
           ["Evaluación intermedia (ejecución)", "Primera versión, corte julio de 2026", "Este informe, capítulo 7"],
           ["Análisis con enfoque diferencial", "Demostrado en registros administrativos", "Entrega 2 y este informe"],
           ["Evaluación ex post y recomendaciones finales", "Pendiente", "Entrega final"]],
          "elaboración propia.", anchos=[6.4, 4.6, 5.0])
    parrafo(doc,
            "Dos piezas de infraestructura acompañan el producto y quedan a "
            "disposición de la Dirección: la rutina de análisis del corpus de "
            "política entregada con la Entrega 2, y la rutina de consultas "
            "reproducibles sobre el Portal de Datos Abiertos que sustenta los "
            "capítulos 4 y 5 de este informe, entregada como Anexo A. Ambas "
            "permiten actualizar las cifras cuando las fuentes publiquen nuevos "
            "cortes, sin depender de procesamientos manuales.")

    titulo(doc, "2.2. Referentes metodológicos de los modelos de evaluación", 2)
    parrafo(doc,
            "Los modelos de evaluación que este informe aplica no parten de cero, "
            "sino que se apoyan en la revisión bibliográfica desarrollada en la "
            "Entrega 2. Conviene recapitular esos referentes con algún detalle, "
            "porque son los que dan forma a los capítulos 6, 7 y 8, y porque "
            "explicitar el marco es la única manera de que un tercero pueda "
            "juzgar si las conclusiones se siguen de la evidencia o del punto de "
            "vista de quien la interpreta.")
    parrafo(doc,
            "Como se recordará, el armazón general proviene de la cadena de valor de las "
            "intervenciones públicas, que distingue insumos, actividades, "
            "productos, resultados e impactos (Bonnefoy y Armijo, 2005). De esa "
            "distinción se derivan tanto el criterio para clasificar los "
            "indicadores del plan de acción según lo que efectivamente miden "
            "—clasificación que sustenta el hallazgo del numeral 7.1— como la "
            "secuencia de los tres tipos de evaluación que este informe practica, "
            "y que se resumen a continuación.")
    tabla(doc, "Modelos de evaluación aplicados en este informe",
          ["Modelo", "Qué examina", "Fuente teórica", "Dónde se aplica"],
          [["Evaluación de diseño (ex ante)",
            "Consistencia entre el problema diagnosticado, la teoría causal implícita, la asignación de recursos y el sistema de medición.",
            "Gertler et al. (2017); Bonnefoy y Armijo (2005)",
            "Capítulos 6 y 7"],
           ["Evaluación de proceso (intermedia)",
            "Grado de ejecución frente a lo programado, ritmo, cuellos de botella y consistencia entre avance físico y financiero.",
            "Bonnefoy y Armijo (2005)",
            "Capítulo 8"],
           ["Análisis descriptivo y territorial",
            "Nivel, tendencia y distribución espacial de los resultados sectoriales que la política busca modificar.",
            "OCDE (2019, 2026); UIT (2024); Vanegas Barrero et al. (2024)",
            "Capítulos 4 y 5"]],
          "elaboración propia.", anchos=[3.6, 6.2, 3.4, 2.8])
    parrafo(doc,
            "La evaluación ex ante, que ocupa los capítulos 6 y 7, sigue el "
            "enfoque de análisis de diseño propio de la literatura de evaluación "
            "de impacto: antes de preguntar si una política funcionó, es preciso "
            "establecer si su lógica causal es plausible, si sus recursos guardan "
            "proporción con el problema diagnosticado y si su sistema de medición "
            "puede capturar los efectos que promete (Gertler et al., 2017). Este "
            "orden de preguntas tiene una ventaja práctica considerable, y es que "
            "puede aplicarse desde el primer día de la implementación, cuando "
            "todavía hay margen para corregir; una evaluación que solo llega al "
            "final identifica problemas cuando ya no se pueden resolver.")
    parrafo(doc,
            "La evaluación intermedia del capítulo 8, por su parte, corresponde a "
            "lo que esa misma tradición denomina evaluación de proceso. Su objeto "
            "no es el efecto sino la ejecución: examina el grado de avance frente "
            "a lo programado, identifica dónde se producen los cuellos de botella "
            "y, sobre todo, distingue los problemas atribuibles a la gestión de "
            "aquellos que provienen del diseño. Esa distinción resulta decisiva "
            "en términos de recomendación, puesto que un rezago de gestión se "
            "corrige con seguimiento y uno de diseño exige modificar el "
            "instrumento. Debe subrayarse que este tipo de evaluación no estima "
            "efectos causales —para ello se requiere el cierre de la intervención "
            "y la construcción de un contrafactual, como se explicó en la Entrega "
            "2—, pero sí anticipa dónde la evaluación ex post encontrará "
            "resultados medibles y dónde encontrará vacíos.")
    parrafo(doc,
            "Finalmente, el análisis descriptivo y territorial de los capítulos 4 "
            "y 5 se apoya en los marcos internacionales de medición del "
            "desarrollo digital, que aportan las dimensiones estándar de "
            "infraestructura, adopción e impacto (OCDE, 2019; OCDE, 2026; UIT, "
            "2024), y en la medición multidimensional de la pobreza digital "
            "producida por la propia Dirección, que provee el referente nacional "
            "de resultado (Vanegas Barrero et al., 2024). La combinación de "
            "ambos permite leer las cifras sectoriales no como datos sueltos sino "
            "como posiciones dentro de un marco comparable.")
    parrafo(doc,
            "Un último referente, de orden interpretativo más que técnico, "
            "proviene del enfoque de gobernanza anticipatoria y de la literatura "
            "sobre gobernanza de la inteligencia artificial (Miller, 2018; "
            "Taeihagh, 2021). Su aporte a este informe consiste en advertir que "
            "una política sobre una tecnología de cambio acelerado no puede "
            "evaluarse únicamente por su cumplimiento formal, ya que sus acciones "
            "pueden ejecutarse al ciento por ciento y aun así quedar desfasadas "
            "respecto del problema que pretendían resolver. Esa advertencia "
            "informa la lectura del capítulo 8 y la agenda propuesta para la "
            "entrega final.")


def metodologia(doc):
    titulo(doc, "3. Metodología", 1)

    titulo(doc, "3.1. Fuentes de información y criterios de selección", 2)
    parrafo(doc,
            "El inventario de la Entrega 2 identificó más fuentes de las que un "
            "informe puede procesar con rigor, de manera que la primera decisión "
            "metodológica consistió en seleccionar aquellas que cumplieran tres "
            "condiciones: cobertura nacional o desagregación territorial "
            "suficiente, acceso verificable en el momento de la consulta, y "
            "posibilidad de reproducir el procesamiento sin intermediación "
            "manual. Las fuentes que no cumplían las tres se reservaron para la "
            "entrega final o se descartaron, y así se indica cuando corresponde.")
    parrafo(doc,
            "Sobre esa base, el análisis de tendencias y brechas del sector se "
            "construyó con dos fuentes de acceso público que se complementan "
            "deliberadamente. La primera es el conjunto de datos del MinTIC sobre "
            "accesos fijos a internet por tecnología y segmento (MinTIC, 2024), "
            "que registra 2,79 millones de filas con desagregación municipal, "
            "trimestral y por operador entre 2016 y el tercer trimestre de 2023. "
            "Su origen en registros administrativos de los proveedores le da una "
            "granularidad que ninguna encuesta alcanza, pero mide infraestructura "
            "contratada y no uso efectivo, razón por la cual se complementa con "
            "la Encuesta Nacional de Calidad de Vida del DANE, cuya edición 2024 "
            "aporta el acceso declarado por los hogares con desagregación por "
            "zona y departamento (DANE, 2025). Leer ambas en paralelo permite "
            "distinguir entre oferta disponible y demanda efectiva, distinción "
            "que resulta decisiva en el capítulo 5.")
    parrafo(doc,
            "Todas las agregaciones sobre el conjunto del MinTIC se ejecutaron "
            "mediante la interfaz de consulta del portal de datos abiertos, que "
            "permite realizar sumas, agrupaciones y filtros del lado del servidor "
            "sin descargar el archivo completo, y quedan reproducidas en la "
            "rutina del Anexo A. Los registros correspondientes a 2016 y al "
            "primer trimestre de 2017 presentan carga parcial en la fuente "
            "—suman apenas unas centenas de accesos frente a los millones de los "
            "trimestres siguientes— y se excluyeron de la serie por tratarse "
            "evidentemente de un artefacto de cargue y no de un dato real.")

    titulo(doc, "3.2. Procedimiento de la evaluación de diseño", 2)
    parrafo(doc,
            "La evaluación ex ante de los capítulos 6 y 7 se apoya en dos "
            "insumos construidos durante la Entrega 2. El primero es el análisis "
            "del corpus documental de los CONPES 3975 y 4144, que midió la "
            "extensión temática de tres familias léxicas —territorial, de enfoque "
            "diferencial y de habilidades— sobre el total de párrafos "
            "argumentativos de cada documento. El segundo es el procesamiento "
            "completo del Plan de Acción y Seguimiento (DNP, 2025c), que permitió "
            "reconstruir la distribución de las 106 acciones por objetivo y por "
            "entidad responsable, la programación de recursos por año y por eje, "
            "y la clasificación de los indicadores de cumplimiento según su tipo.")
    parrafo(doc,
            "Con esos insumos, la valoración del diseño examina tres "
            "consistencias sucesivas. La primera contrasta el diagnóstico oficial "
            "del problema con la asignación de recursos, para establecer si la "
            "política invierte donde dice que está la carencia. La segunda "
            "contrasta los objetivos declarados con el sistema de medición, para "
            "establecer si el instrumento puede verificar el logro de aquello que "
            "promete. Y la tercera contrasta la ambición del plan con la "
            "capacidad institucional disponible, para estimar el riesgo de "
            "ejecución. Cada una de las tres corresponde a un capítulo o numeral "
            "propio en este informe.")

    titulo(doc, "3.3. Procedimiento de la evaluación intermedia", 2)
    parrafo(doc,
            "La evaluación de la ejecución utiliza los reportes del módulo de "
            "reporte y revisión de SisCONPES con corte al 21 de julio de 2026, "
            "facilitados por la Dirección (DNP, 2026). Al corte, 93 de las 106 "
            "acciones tienen reporte registrado, de las cuales 53 cuentan con "
            "reporte aprobado y 40 se encuentran en revisión; las 13 restantes no "
            "reportan porque su fecha de inicio programada es 2026 o posterior, "
            "de modo que su ausencia no constituye incumplimiento.")
    parrafo(doc,
            "Los promedios que se citan a lo largo del capítulo 8 son promedios "
            "simples calculados sobre las acciones con reporte, y no promedios "
            "ponderados por la importancia relativa que el plan asigna a cada "
            "acción. Se optó por el promedio simple por dos razones: porque "
            "permite comparar objetivos con distinto número de acciones sin que "
            "la ponderación introduzca supuestos adicionales, y porque es el "
            "criterio con el que la propia Dirección construye sus balances "
            "internos, lo que facilita el contraste. Cuando la ponderación "
            "cambiaría sustantivamente la lectura, así se advierte.")
    parrafo(doc,
            "Una precaución adicional merece registrarse, pues afecta la "
            "comparabilidad de las cifras. Los reportes disponibles conviven en "
            "dos periodos —2025-1 y 2025-2— con valores distintos para una misma "
            "acción, ya que el segundo acumula sobre el primero. En este informe "
            "se emplea siempre el corte más reciente disponible para cada acción, "
            "y toda cifra de avance debe entenderse referida al 21 de julio de "
            "2026, con la advertencia de que los reportes en revisión pueden "
            "modificarse durante el proceso de aprobación.")

    titulo(doc, "3.4. Limitaciones", 2)
    parrafo(doc,
            "Cuatro limitaciones acotan el alcance de las conclusiones y conviene "
            "enunciarlas antes de presentar los resultados. En primer lugar, la "
            "serie sectorial públicamente disponible llega al tercer trimestre de "
            "2023, de manera que el análisis de tendencias no captura los dos "
            "últimos años de intervenciones ni el periodo de implementación de la "
            "política evaluada; las conclusiones territoriales describen, "
            "entonces, la situación heredada sobre la cual la política opera, y "
            "no su efecto.")
    parrafo(doc,
            "En segundo lugar, y como ya se advirtió, los accesos fijos miden "
            "infraestructura contratada y no uso efectivo, ni capturan el acceso "
            "móvil, que en los territorios de menor densidad puede ser la vía "
            "predominante de conexión. En tercer lugar, el 43% de los reportes de "
            "avance está pendiente de aprobación, por lo que las cifras de "
            "ejecución del capítulo 8 son provisionales y podrían ajustarse en el "
            "corte siguiente.")
    parrafo(doc,
            "Por último, el ejercicio con enfoque diferencial del capítulo 9 se "
            "realizó sobre un registro administrativo de cobertura "
            "predominantemente municipal, de modo que ilustra el método y "
            "sustenta una hipótesis, pero no autoriza conclusiones de alcance "
            "nacional. Replicar ese análisis sobre fuentes representativas es una "
            "de las tareas de la entrega final.")


def tendencias(doc):
    titulo(doc, "4. Análisis estadístico y de tendencias del sector", 1)
    parrafo(doc,
            "Evaluar una política exige conocer primero el terreno sobre el que "
            "actúa, y ese es el propósito de este capítulo: establecer en qué "
            "estado encontró la Política Nacional de Inteligencia Artificial al "
            "sector que pretende transformar. Sin esa referencia, cualquier "
            "avance reportado carece de escala, porque no hay manera de "
            "distinguir entre un logro de la política y la continuación de una "
            "tendencia que ya venía en curso.")
    parrafo(doc,
            "El sector TIC admite muchas mediciones posibles, de modo que la "
            "selección requiere justificarse. Este análisis se concentra en la "
            "conectividad por tres razones. La primera es de pertinencia: el eje "
            "de datos e infraestructura concentra el 59,3% de los recursos "
            "programados de la política, lo que lo convierte en su apuesta "
            "principal y, por tanto, en el frente donde la evaluación debe ser "
            "más exigente. La segunda es de precedencia lógica, pues la "
            "conectividad es condición habilitante de todos los demás ejes: sin "
            "red no hay adopción de inteligencia artificial en empresas, ni "
            "servicios digitales del Estado, ni formación en línea. Y la tercera "
            "es de disponibilidad, ya que la conectividad es la única dimensión "
            "del sector con series históricas largas, desagregación municipal y "
            "actualización periódica, condiciones sin las cuales el análisis de "
            "tendencias no es posible.")
    parrafo(doc,
            "Conviene explicitar también lo que este recorte deja fuera. La "
            "adopción empresarial de tecnología, la capacidad de cómputo "
            "instalada y la disponibilidad de talento especializado son "
            "dimensiones igualmente relevantes del sector, pero sus fuentes son "
            "de periodicidad irregular o de cobertura parcial, y su tratamiento "
            "se reserva para la entrega final. El capítulo procede entonces en "
            "tres pasos: la evolución del volumen de accesos, la transformación "
            "de su composición tecnológica y el contraste con lo que declaran los "
            "hogares.")

    titulo(doc, "4.1. La serie nacional de accesos fijos", 2)
    parrafo(doc,
            "Los accesos fijos a internet pasaron de 6,35 millones al cierre de "
            "2017 a 8,95 millones en el tercer trimestre de 2023, un crecimiento "
            "del 40,8% en el período y del 27,5% desde 2019 (MinTIC, 2024). La "
            "Figura 1 muestra la trayectoria completa.")
    figura(doc, "fig1_serie_accesos.png",
           "Accesos fijos a internet en Colombia, 2017-2023",
           "elaboración propia a partir de MinTIC (2024), corte por cuarto "
           "trimestre; 2023 corresponde al tercer trimestre, último disponible.")
    parrafo(doc,
            "Más allá del agregado, la serie revela tres regímenes claramente diferenciados. Entre 2017 "
            "y 2019 el parque creció a un ritmo moderado, cercano al 5% anual: "
            "un mercado maduro expandiéndose por goteo. Entre 2019 y 2021 el "
            "ritmo se duplicó —12,4% en 2020 y 7,9% en 2021—, el salto de la "
            "pandemia, cuando la conexión domiciliaria se convirtió en condición "
            "de acceso al trabajo, a la educación y a los servicios del Estado. "
            "Y desde 2022 la curva se aplana: el crecimiento de 2022 fue del "
            "5,2% y el nivel de 2023 está prácticamente al del año anterior, "
            "con una leve caída entre el segundo y el tercer trimestre.")
    parrafo(doc,
            "Por su parte, la meseta reciente admite dos lecturas que la entrega final deberá "
            "arbitrar con datos de uso. Puede reflejar saturación del segmento "
            "de hogares con capacidad de pago —lo que desplazaría el margen de "
            "crecimiento hacia los hogares de menores ingresos, justo donde el "
            "Índice de Pobreza Digital localiza las privaciones (DNP, 2025b)— o "
            "sustitución por acceso móvil, que esta fuente no captura. En "
            "cualquiera de los dos casos, la implicación de política es la "
            "misma: el crecimiento inercial del mercado se agotó, y lo que "
            "siga dependerá de intervención pública o de cambios en el precio "
            "relativo del servicio.")

    titulo(doc, "4.2. Modernización tecnológica del parque instalado", 2)
    parrafo(doc,
            "Detrás del número agregado hay una transformación cualitativa que "
            "merece registrarse como el avance más claro del sector en el "
            "período. La composición tecnológica de los accesos cambió de forma "
            "acelerada: la fibra óptica hasta el hogar pasó del 8,5% de los "
            "accesos en 2019 al 32,5% en 2023 —de 596.000 a 2,9 millones de "
            "accesos, casi cinco veces más—, mientras las tecnologías xDSL "
            "sobre par de cobre, las de peor desempeño, cayeron del 22,2% al "
            "5,3% (MinTIC, 2024).")
    figura(doc, "fig6_tecnologia.png",
           "Composición tecnológica de los accesos fijos, 2019 frente a 2023",
           "elaboración propia a partir de MinTIC (2024), tercer trimestre de "
           "cada año.")
    parrafo(doc,
            "Esta transformación admite una lectura doblemente positiva. Primero, porque la calidad "
            "promedio del acceso mejoró aunque la cantidad se haya estancado: "
            "buena parte del esfuerzo del mercado en estos años no fue conectar "
            "hogares nuevos sino migrar hogares conectados hacia tecnologías de "
            "mayor capacidad, un progreso que el conteo simple de accesos no "
            "registra. Segundo, porque la infraestructura de fibra es la que "
            "exigen los servicios que la Política Nacional de Inteligencia "
            "Artificial promueve —computación en la nube, transmisión masiva de "
            "datos, servicios digitales del Estado—, de modo que el sector llegó "
            "a la política con una base técnica sustancialmente mejor que la de "
            "cinco años atrás.")
    parrafo(doc,
            "El cambio de tecnología se refleja, como era de esperarse, en la "
            "calidad medida del servicio. En el tercer trimestre de 2019 apenas "
            "el 3,5% de los accesos fijos del país contrataba velocidades de "
            "bajada de 100 megabits por segundo o más, y solo el 14,8% alcanzaba "
            "los 25 megabits que suelen tomarse como umbral de banda ancha "
            "funcional para un hogar. Cuatro años después, esas proporciones son "
            "del 67,1% y del 81,0% respectivamente (MinTIC, 2024). Dicho de otro "
            "modo, el acceso típico de 2023 pertenece a una categoría de "
            "servicio que en 2019 era excepcional, y esa mejora ocurrió en un "
            "periodo en el que el número total de accesos apenas creció una "
            "cuarta parte: el sector invirtió estos años en profundidad más que "
            "en extensión.")
    figura(doc, "fig_velocidad.png",
           "Proporción de accesos fijos por velocidad de bajada contratada, "
           "2019 frente a 2023",
           "elaboración propia a partir de MinTIC (2024), tercer trimestre de "
           "cada año.")
    parrafo(doc,
            "La magnitud del salto que muestra la figura merece subrayarse, "
            "porque no es un cambio incremental sino un reemplazo casi completo "
            "del estándar de servicio en cuatro años. Una banda ancha de cien "
            "megabits no es un lujo estadístico: es la capacidad que exigen la "
            "telemedicina, la educación remota con video simultáneo y el trabajo "
            "sobre plataformas en la nube, es decir, los usos que convierten la "
            "conexión en oportunidad. Que dos de cada tres accesos del país ya "
            "estén en ese nivel significa que, para la población conectada, la "
            "restricción activa dejó de ser la capacidad del canal; lo que "
            "refuerza, por otra vía, la conclusión de que el margen de la "
            "política está en quienes no acceden y en quienes accediendo no "
            "saben aprovecharlo.")
    parrafo(doc,
            "La contracara es distributiva: la migración a fibra ocurre donde ya "
            "hay mercado. La pregunta que el capítulo siguiente responde es qué "
            "pasó mientras tanto en los territorios donde el mercado no llega "
            "solo.")

    titulo(doc, "4.3. El acceso de los hogares y la composición de la brecha", 2)
    parrafo(doc,
            "La encuesta de hogares complementa la lectura de infraestructura. "
            "El 65,6% de los hogares contaba con conexión a internet en 2024, "
            "con un aumento de 1,7 puntos porcentuales frente a 2023 (DANE, "
            "2025); al ritmo de los últimos dos años, cerca de 300.000 hogares "
            "se suman cada año a la población conectada. La distancia entre "
            "cabeceras (72,5%) y área rural dispersa (41,9%) supera los treinta "
            "puntos, y la medición multidimensional de la Dirección establece "
            "que la privación más extendida no es la conexión sino la capacidad "
            "de uso: el 60% de la población presenta brechas en habilidades "
            "digitales básicas, frente al 39% con deficiencias de calidad o "
            "frecuencia de conexión y al 33% con insuficiencia de dispositivos "
            "(DNP, 2025b).")
    parrafo(doc,
            "Antes de cerrar el diagnóstico conviene añadir una dimensión que "
            "suele pasarse por alto y que matiza favorablemente el cuadro: la "
            "composición social del parque de accesos. Contra la intuición de "
            "que el internet fijo es un servicio de hogares acomodados, los "
            "estratos 1 y 2 concentran el 47,3% de los accesos residenciales y "
            "no residenciales del país, con 4,23 millones de conexiones, y su "
            "participación viene en aumento: crecieron 31,5% entre 2019 y 2023, "
            "por encima del 27,5% nacional, mientras los estratos 5 y 6 —ya "
            "saturados— redujeron su peso relativo del 6,2% al 5,6% (MinTIC, "
            "2024). El crecimiento reciente del sector fue, por tanto, un "
            "crecimiento de base popular, y esa es una condición favorable para "
            "una política cuyo mandato contractual es precisamente la inclusión "
            "digital.")
    parrafo(doc,
            "Leídas juntas, las tres fuentes describen un sector cuyo problema "
            "cambió de naturaleza. La década pasada fue de expansión de "
            "infraestructura y la evidencia del numeral anterior muestra que esa "
            "expansión además se modernizó y se popularizó; el margen actual "
            "está en quién usa la red y para qué. Esa transición es la que los "
            "indicadores propuestos en la Entrega 2 buscan capturar y la que el "
            "diseño de la política, como se verá en el capítulo 6, todavía no "
            "acompaña del todo.")


def brechas(doc):
    titulo(doc, "5. Brechas territoriales", 1)

    titulo(doc, "5.1. Qué se entiende aquí por brecha territorial", 2)
    parrafo(doc,
            "La expresión brecha digital se usa con tanta frecuencia y con "
            "sentidos tan distintos que conviene precisar cuál se emplea en este "
            "informe antes de presentar cifras. En su acepción más común designa "
            "la diferencia entre quienes tienen acceso a las tecnologías "
            "digitales y quienes no; esa definición, sin embargo, resulta "
            "insuficiente para orientar política pública, porque no dice nada "
            "sobre dónde está la diferencia, de qué magnitud es ni hacia dónde se "
            "mueve.")
    parrafo(doc,
            "Por brecha territorial se entiende aquí, de manera específica, la "
            "desigualdad en el acceso a la infraestructura digital entre las "
            "unidades geográficas del país, medida sobre una misma variable y en "
            "un mismo momento. Esa desigualdad admite dos lecturas "
            "complementarias que este capítulo aborda por separado, porque "
            "responden preguntas distintas y tienen implicaciones de política "
            "también distintas.")
    parrafo(doc,
            "La primera lectura es la de concentración, que describe cómo se "
            "distribuye el total nacional entre los territorios en un momento "
            "dado. Responde a la pregunta de dónde está la infraestructura, y su "
            "utilidad es diagnóstica: permite dimensionar la desigualdad "
            "existente y localizar los extremos. Su limitación es que se trata de "
            "una fotografía estática, y una concentración alta puede ser tanto el "
            "resultado de un rezago histórico que se está corrigiendo como el de "
            "uno que se está agravando.")
    parrafo(doc,
            "La segunda lectura, que es la que este informe considera más "
            "informativa, es la de convergencia o divergencia. Tomada de la "
            "literatura de economía regional, la noción examina si las unidades "
            "que partían de niveles más bajos crecen más rápido que las que "
            "partían de niveles más altos —en cuyo caso las distancias se acortan "
            "y hay convergencia— o si ocurre lo contrario y las distancias se "
            "amplían, situación que se denomina divergencia. Se mide comparando "
            "las tasas de variación entre dos momentos y contrastándolas con el "
            "nivel de partida de cada unidad.")
    parrafo(doc,
            "Ahora bien, la razón de fondo para incorporar esta segunda lectura es que la "
            "concentración por sí sola puede llevar a conclusiones equivocadas de "
            "política. Un territorio con poca infraestructura que está creciendo "
            "aceleradamente no requiere el mismo tipo de intervención que uno con "
            "poca infraestructura y en retroceso, aunque en la fotografía "
            "estática ambos aparezcan igual de rezagados. Distinguirlos es "
            "precisamente lo que permite priorizar, y esa distinción es la que "
            "arroja el hallazgo principal de este capítulo.")

    titulo(doc, "5.2. Concentración: dónde está la infraestructura", 2)
    parrafo(doc,
            "La distribución de los accesos fijos entre departamentos revela una "
            "concentración pronunciada. Cinco departamentos —Bogotá, Antioquia, "
            "Valle del Cauca, Cundinamarca y Atlántico— reúnen el 66% de los "
            "accesos del país, y Bogotá por sí sola concentra el 25,2%, esto es, "
            "2,25 millones de accesos, más que los veinticinco departamentos de "
            "menor tamaño sumados (MinTIC, 2024). En el extremo opuesto, los "
            "cinco departamentos amazónicos y de la Orinoquia oriental "
            "—Amazonas, Guainía, Guaviare, Vaupés y Vichada— suman 3.785 accesos "
            "fijos, equivalentes al 0,04% del total nacional.")
    parrafo(doc,
            "El descenso al nivel municipal agrega resolución al mismo cuadro. De "
            "los 1.117 municipios y áreas no municipalizadas que registran algún "
            "acceso en la fuente, 286 —uno de cada cuatro— reportan menos de "
            "cien accesos fijos en todo su territorio, y 37 reportan menos de "
            "diez, lo que en la práctica equivale a la ausencia del servicio "
            "(MinTIC, 2024). En el otro extremo, los cinco municipios más "
            "grandes concentran el 45,3% de los accesos del país. La brecha "
            "territorial no es, entonces, solamente un asunto de departamentos "
            "periféricos: dentro de casi todos los departamentos existe una "
            "periferia municipal donde el servicio fijo es testimonial.")
    parrafo(doc,
            "Estas magnitudes deben leerse con una advertencia, y es que la "
            "concentración de infraestructura sigue en buena medida a la "
            "concentración de población y de actividad económica, de modo que "
            "ningún país presenta una distribución uniforme. El dato relevante "
            "para política pública no es entonces que exista concentración, sino "
            "si su intensidad excede lo que la distribución poblacional "
            "explicaría y, sobre todo, qué está ocurriendo con ella en el tiempo. "
            "A esto último se dedica el numeral siguiente.")

    titulo(doc, "5.3. Divergencia: hacia dónde se mueve la brecha", 2)
    parrafo(doc,
            "Al pasar de la fotografía al movimiento, el diagnóstico se agrava. "
            "Entre el tercer trimestre de 2019 y el de 2023, mientras el conjunto "
            "del país crecía 27,5%, seis departamentos retrocedieron en términos "
            "absolutos: Guainía (−62,8%), Guaviare (−47,8%), Vichada (−38,9%), "
            "Amazonas (−29,4%), Chocó (−14,5%) y Vaupés (MinTIC, 2024). No se "
            "trata, por tanto, de crecimiento lento ni de convergencia "
            "insuficiente, sino de retroceso: hay hoy menos accesos fijos que "
            "hace cuatro años justamente en los territorios que ya tenían menos.")
    tabla(doc, "Departamentos con retroceso absoluto en accesos fijos, 2019-2023",
          ["Departamento", "Accesos 2019-T3", "Accesos 2023-T3", "Variación", "Hogares con internet (ECV 2024)"],
          [["Guainía", "1.520", "565", "−62,8%", "Inferior al 30%"],
           ["Guaviare", "2.648", "1.382", "−47,8%", "Sin dato desagregado publicado"],
           ["Vichada", "1.331", "813", "−38,9%", "Inferior al 30%"],
           ["Amazonas", "1.332", "941", "−29,4%", "Sin dato desagregado publicado"],
           ["Chocó", "24.179", "20.683", "−14,5%", "Inferior al 30%"],
           ["Vaupés", "88", "84", "−4,5%", "Inferior al 30%"]],
          "elaboración propia a partir de MinTIC (2024) y DANE (2025).",
          anchos=[2.8, 2.9, 2.9, 2.2, 5.2])
    parrafo(doc,
            "La tabla permite apreciar, de paso, la escala absoluta del "
            "problema, que los porcentajes tienden a ocultar: Vaupés, un "
            "departamento de más de cuarenta mil habitantes, cuenta con 84 "
            "accesos fijos a internet en total, menos que un solo edificio "
            "residencial de una ciudad capital. En magnitudes así, la discusión "
            "sobre tasas de crecimiento pierde sentido y lo que queda es una "
            "pregunta de presencia estatal básica.")
    parrafo(doc,
            "En términos del marco expuesto en el numeral 5.1, el país no "
            "presenta convergencia parcial sino divergencia en el extremo "
            "inferior de la distribución. Y esa forma de divergencia es la más "
            "problemática desde el punto de vista de la política pública, porque "
            "significa que la dinámica espontánea del mercado no solo no corrige "
            "la desigualdad sino que la profundiza, de manera que sin "
            "intervención dirigida la brecha seguirá ampliándose por sí sola.")
    figura(doc, "fig2_divergencia.png",
           "Variación de accesos fijos por departamento, 2019-2023 (mayores "
           "crecimientos y todos los retrocesos)",
           "elaboración propia a partir de MinTIC (2024).")
    parrafo(doc,
            "La Figura 3 merece leerse por sus dos extremos, porque cuentan "
            "historias opuestas y ambas son informativas. El extremo inferior "
            "—los seis retrocesos— coincide con la encuesta de hogares: Vichada, "
            "Chocó y Vaupés reportan menos del 30% de hogares conectados, "
            "frente al 82,7% de Bogotá (DANE, 2025). La coincidencia de dos "
            "fuentes independientes, una de oferta y una de demanda, descarta "
            "que el retroceso sea un artefacto del registro administrativo: en "
            "esos territorios el servicio fijo se está contrayendo de verdad, "
            "sea por salida de operadores, por sustitución hacia soluciones "
            "satelitales y móviles, o por pérdida de capacidad de pago de los "
            "hogares. Distinguir entre esas causas es una de las tareas de la "
            "entrega final.")
    parrafo(doc,
            "El extremo superior es la mejor noticia territorial del período: "
            "San Andrés y Providencia casi triplicó sus accesos (+182,5%), y "
            "Putumayo (+77,1%) y Arauca (+76,5%) —dos departamentos periféricos, "
            "sin ventajas de mercado evidentes— crecieron a casi el triple del "
            "ritmo nacional. Los tres casos comparten intervención pública "
            "sostenida en conectividad. La brecha, en otras palabras, no es un "
            "destino geográfico: donde hubo inversión dirigida, la periferia "
            "convergió, y esa es exactamente la evidencia que justifica que el "
            "eje de infraestructura de la política concentre recursos.")
    parrafo(doc,
            "Para la política evaluada, el dato fija una vara concreta: el eje "
            "de datos e infraestructura, que concentra el 59,3% de los recursos "
            "(DNP, 2025c), tiene en los seis departamentos en retroceso su caso "
            "de prueba más exigente. Si al cierre del cuatrienio la serie "
            "territorial no revierte el signo en la Amazonia y en Chocó, la "
            "inversión habrá crecido donde ya había red.")


def ex_ante(doc):
    titulo(doc, "6. Evaluación ex ante (I): el diagnóstico y la asignación de recursos", 1)
    parrafo(doc,
            "La evaluación de diseño responde si la política, tal como está "
            "formulada, puede producir los resultados que promete. Siguiendo el "
            "marco del capítulo 2, se examinan tres consistencias: entre el "
            "diagnóstico y la asignación de recursos, entre los objetivos y el "
            "sistema de medición, y entre la formulación y las capacidades "
            "institucionales de ejecución.")

    titulo(doc, "6.1. Lo que el diagnóstico oficial establece", 2)
    parrafo(doc,
            "Antes de señalar el vacío conviene registrar lo que el diseño hace "
            "bien, porque es medible y es mérito de la formulación. El análisis "
            "de corpus de la Entrega 2 mostró que el CONPES 4144 triplicó la "
            "presencia de la dimensión territorial frente a su antecesor de 2019 "
            "—del 5,1% al 16,7% de los párrafos— e incorporó por primera vez el "
            "enfoque diferencial, ausente por completo del CONPES 3975 y "
            "presente en el 7,1% de los párrafos del documento vigente. En la "
            "formulación, la política aprendió exactamente las lecciones que el "
            "diagnóstico territorial del capítulo 5 sugiere. El diagnóstico "
            "oficial del sector, por su parte, localiza la privación dominante "
            "en las habilidades digitales —60% de la población— por encima de "
            "la conectividad (DNP, 2025b).")
    figura(doc, "fig3_recursos_eje.png",
           "Recursos programados por eje de la política, 2025-2030",
           "elaboración propia a partir del Plan de Acción y Seguimiento del "
           "CONPES 4144 (DNP, 2025c).")
    parrafo(doc,
            "La asignación de recursos, sin embargo, sigue el orden inverso al "
            "diagnóstico: el 59,3% se destina a datos e infraestructura y el "
            "3,8% a capacidades y talento digital, una proporción de quince a "
            "uno (DNP, 2025c). Como se planteó en la Entrega 2, la diferencia no "
            "es en sí misma un error de diseño —la infraestructura tiene costos "
            "unitarios mayores, es condición del uso, y el capítulo 5 acaba de "
            "mostrar que la inversión dirigida en conectividad produce "
            "convergencia—, pero el instrumento no formula la hipótesis que "
            "conecta la inversión en red con el cierre de la brecha de "
            "capacidades, y esa hipótesis ausente es el principal vacío de "
            "diseño de la política.")
    parrafo(doc,
            "Vale la pena precisar qué significaría formular esa hipótesis, "
            "porque la observación puede sonar más abstracta de lo que es. Una "
            "política que invierte en red esperando cerrar una brecha de "
            "habilidades está suponiendo, aunque no lo escriba, alguno de tres "
            "mecanismos de transmisión: que el acceso genera aprendizaje por "
            "uso, de modo que basta conectar para que las capacidades lleguen "
            "solas; que la red habilita la oferta formativa de terceros "
            "—escuelas, plataformas, programas públicos—, que son quienes "
            "efectivamente cierran la brecha; o que la demanda empresarial de "
            "personal capacitado, estimulada por la conectividad, arrastra la "
            "formación. Cada mecanismo implica intervenciones complementarias "
            "distintas y, sobre todo, indicadores de verificación distintos.")
    parrafo(doc,
            "Mientras el instrumento no diga cuál de esos mecanismos espera, la "
            "evaluación no puede establecer si la apuesta de infraestructura "
            "está funcionando como vía de inclusión o solo como despliegue de "
            "red. La evidencia disponible, además, invita al escepticismo frente "
            "al primer mecanismo: el propio Índice de Pobreza Digital muestra "
            "que el 60% de la población presenta brechas de habilidades en un "
            "país donde dos tercios de los hogares ya están conectados, es "
            "decir, que el acceso por sí solo no ha producido el aprendizaje "
            "esperado (DNP, 2025b). Explicitar la hipótesis de transmisión no "
            "es, entonces, un refinamiento académico, sino la condición para que "
            "la entrega final pueda pronunciarse con fundamento sobre la "
            "eficacia de la principal apuesta presupuestal de la política.")

    parrafo(doc,
            "La consistencia entre diagnóstico y recursos, sin embargo, es solo "
            "el primero de los tres exámenes anunciados. Los dos restantes "
            "—referidos al sistema de medición y a la capacidad institucional de "
            "ejecución— se desarrollan en el capítulo siguiente.")


def ex_ante_medicion(doc):
    titulo(doc, "7. Evaluación ex ante (II): el sistema de medición y la capacidad de ejecución", 1)
    parrafo(doc,
            "Establecida en el capítulo anterior la relación entre el "
            "diagnóstico y los recursos, corresponde ahora examinar si la "
            "política puede saber si está funcionando y si cuenta con quién la "
            "ejecute. Ambos exámenes son de diseño y no de gestión: apuntan a "
            "propiedades del instrumento que existen desde su formulación y que, "
            "por tanto, podían anticiparse antes de que la implementación "
            "comenzara.")

    titulo(doc, "7.1. Objetivos y sistema de medición", 2)
    parrafo(doc,
            "Corresponde ahora el segundo examen, referido al sistema de medición. Los 106 "
            "indicadores del Plan de Acción y Seguimiento se dividen en 76 de "
            "gestión y 30 de producto; ninguno mide resultados (DNP, 2025c). El "
            "sistema puede verificar que las acciones se ejecuten, pero no puede "
            "establecer si la ejecución modifica la conectividad, las "
            "habilidades o la adopción de tecnología. En términos de la cadena "
            "de valor adoptada en la Entrega 2, la política se mide a sí misma "
            "hasta el eslabón de productos y deja los eslabones de resultado e "
            "impacto sin instrumentación propia.")
    parrafo(doc,
            "Ese vacío es el que justifica la matriz de indicadores propuesta en "
            "la Entrega 2, que se alimenta de fuentes externas al instrumento "
            "—encuestas del DANE, el Índice de Pobreza Digital, registros "
            "administrativos— precisamente porque el instrumento no produce esa "
            "información. Vale anotar que no se trata de una anomalía de esta "
            "política: la literatura de indicadores de desempeño documenta que "
            "los planes de acción de política pública tienden a instrumentar la "
            "gestión antes que el resultado (Bonnefoy y Armijo, 2005). La "
            "diferencia es que esta política dispone, gracias a una de sus "
            "propias acciones ya cerradas, de una estadística oficial de "
            "resultado —la medición de pobreza digital— con la cual podría "
            "instrumentarse a sí misma.")

    titulo(doc, "7.2. Formulación y capacidad de ejecución", 2)
    parrafo(doc,
            "Queda por revisar la dimensión institucional, y en ella el dato de partida es que tres entidades —MinTIC, DNP y "
            "MinCiencias— participan en el 80,2% de las acciones, de modo que "
            "el desempeño de la política depende de la capacidad de ejecución de "
            "un núcleo muy reducido (DNP, 2025c). La otra cara de esa "
            "concentración es una cola larga de participación simbólica, pues de "
            "las 56 entidades involucradas en el plan la mitad figura en una "
            "sola acción, lo que en la práctica significa que su compromiso con "
            "la política se agota en un entregable puntual y que el andamiaje de "
            "coordinación descansa casi por completo sobre el núcleo. El "
            "calendario agrava esa "
            "dependencia: el 45,3% de las acciones vence a más tardar en "
            "diciembre de 2026 y los años 2025 y 2026 concentran el 63,7% del "
            "costo total. La política apostó por un arranque rápido ejecutado "
            "por pocas entidades; el capítulo siguiente muestra qué tanto se "
            "está cumpliendo esa apuesta.")


def intermedia(doc):
    titulo(doc, "8. Evaluación intermedia: la ejecución al corte de julio de 2026", 1)

    titulo(doc, "8.1. Balance general", 2)
    parrafo(doc,
            "A diecisiete meses de la aprobación de la política, el avance "
            "físico promedio de las 93 acciones con reporte es del 43,3% y el "
            "financiero del 41,1% (DNP, 2026). Veinticuatro acciones alcanzan "
            "el 100% y treinta permanecen en 0%. La política avanza, pero de "
            "forma heterogénea y con una alerta de calendario: de las dieciocho "
            "acciones cuya vigencia vencía en 2025, solo tres cerraron con "
            "cumplimiento total; las otras quince terminaron su período con "
            "avances entre el 0% y el 70%, un rezago estructural del primer año "
            "que la vigencia 2026 hereda.")
    parrafo(doc,
            "Junto a esa alerta, dos aspectos del balance resultan positivos y conviene decirlos con la "
            "misma claridad que los rezagos. El primero es la disciplina de "
            "reporte: el 87,7% de las acciones tiene reporte registrado en el "
            "sistema, un nivel de cumplimiento del deber de informar que no es "
            "frecuente en políticas con más de cincuenta entidades involucradas "
            "y que le da al seguimiento una base creíble. El segundo es que el "
            "freno no es presupuestal: los recursos asignados en el plan igualan "
            "los costos programados año a año, de modo que la política figura "
            "como financiada y la restricción está en la ejecución (DNP, 2026). "
            "Un rezago con plata es recuperable; uno sin plata, no.")
    parrafo(doc,
            "Para completar el cuadro conviene precisar el universo sobre el que "
            "se calcula todo lo anterior. Las 13 acciones sin reporte no están "
            "incumplidas: su fecha de inicio programada es 2026 o posterior "
            "—entre ellas la incorporación al sistema multilateral de gobernanza "
            "(1.6), tres acciones de gestión de riesgos de largo aliento y "
            "cuatro del frente de adopción sectorial—, de modo que su silencio es "
            "calendario y no rezago (DNP, 2026). De las 93 restantes, 24 "
            "acciones, equivalentes al 25,8% de las reportadas, ya alcanzaron el "
            "cierre total.")
    parrafo(doc,
            "A ello se suma un desacoplamiento entre las dimensiones física y "
            "financiera en varias acciones —tres reportan 100% físico con 0% "
            "financiero—, que indica más un problema de calidad del reporte que "
            "de gestión, y que amerita depuración en el próximo corte.")

    titulo(doc, "8.2. Lo que ya está funcionando", 2)
    parrafo(doc,
            "Las veinticuatro acciones cerradas al 100% no son las de menor "
            "calado. Entre ellas hay piezas que producen efectos verificables "
            "sobre el resto de la política y sobre este mismo estudio.")
    tabla(doc, "Acciones cerradas al 100% con efecto verificable, selección",
          ["Acción", "Logro", "Por qué importa"],
          [["1.4", "Lineamientos éticos para el uso de IA en entidades públicas, adoptados",
            "Primera pieza normativa del eje de gobernanza en operación."],
           ["2.8", "Estadística oficial de pobreza digital",
            "Es la medición de resultado con la que este estudio evalúa la política: la política produjo su propio instrumento de evaluación."],
           ["2.14", "Instrumento para centros de datos a hiperescala",
            "Condición habilitante de la infraestructura de cómputo que la IA requiere."],
           ["2.30", "Red de colaboración de analítica de datos en el sector público",
            "Una de las tres acciones de 2025 cerradas a tiempo; liderada por el DNP."],
           ["4.6 y 4.8", "Oferta de formación y programas de alfabetización en IA",
            "El canal por el que el eje de talento llega a la población; su calidad distributiva se examina en el capítulo 9."],
           ["5.1 y 5.5", "Modelos de seguridad y privacidad de la información y de seguridad digital, actualizados",
            "Base del buen desempeño del objetivo de mitigación de riesgos."],
           ["6.1", "Lineamientos de compra pública de soluciones de IA",
            "Ordena la puerta de entrada de la IA al Estado, el frente de mayor riesgo de adopción desordenada."]],
          "elaboración propia a partir de DNP (2026).", anchos=[1.8, 6.6, 7.6])
    parrafo(doc,
            "La acción 2.8 merece subrayarse por su circularidad virtuosa: la "
            "estadística de pobreza digital que este informe usa como referente "
            "de resultado es, ella misma, un producto ya entregado de la "
            "política que se evalúa. Es el mejor ejemplo disponible de que el "
            "plan puede producir instrumentos de medición de resultado cuando "
            "se lo propone, y el precedente natural para la recomendación de "
            "instrumentar los demás ejes.")

    titulo(doc, "8.3. Avance por objetivo", 2)
    figura(doc, "fig4_avance_obj.png",
           "Avance físico y financiero promedio por objetivo, corte del 21 de "
           "julio de 2026",
           "elaboración propia a partir de DNP (2026); promedios simples sobre "
           "las acciones con reporte.")
    tabla(doc, "Avance promedio por objetivo de la política",
          ["Objetivo", "Acciones reportadas", "Avance físico", "Avance financiero"],
          [["1. Ética y gobernanza", "5 de 6", "47,6%", "100%"],
           ["2. Datos e infraestructura", "29 de 30", "44,4%", "34,7%"],
           ["3. Investigación, desarrollo e innovación", "5 de 6", "29,2%", "20,0%"],
           ["4. Capacidades y talento digital", "14 de 14", "44,9%", "52,6%"],
           ["5. Mitigación de riesgos", "16 de 21", "54,2%", "50,2%"],
           ["6. Uso y adopción de la IA", "24 de 29", "35,7%", "28,2%"]],
          "elaboración propia a partir de DNP (2026), corte del 21 de julio de 2026.",
          anchos=[6.0, 3.4, 3.2, 3.4])
    parrafo(doc,
            "La Figura 5 permite tres lecturas que la tabla sola no muestra. La "
            "primera es la forma general: ningún objetivo está por debajo del "
            "29% ni por encima del 55%, es decir, no hay ejes abandonados ni "
            "ejes terminados; la política avanza en bloque, con una dispersión "
            "de 25 puntos entre el mejor y el peor. La segunda es la relación "
            "entre las dos barras de cada objetivo: donde la barra financiera "
            "supera a la física (objetivos 1 y 4) el dinero fluye más rápido que "
            "los productos, y donde ocurre lo contrario (objetivos 2, 3 y 6) hay "
            "productos reportados con recursos sin ejecutar o sin registrar, el "
            "patrón que sugiere problemas de calidad del reporte financiero. La "
            "tercera es la paradoja del objetivo 1: ejecutó el 100% de sus "
            "recursos con un avance físico del 47,6%.")
    parrafo(doc,
            "Más allá de la forma general, la lectura por objetivo revela tres patrones sustantivos. En primer lugar, el "
            "objetivo de mitigación de riesgos lidera el avance (54,2%), "
            "impulsado por el paquete de seguridad digital ya cerrado. El de "
            "investigación, desarrollo e innovación es el más rezagado (29,2%), "
            "con tres de sus cinco acciones reportadas en 0%, incluidos el "
            "mecanismo de financiación conjunta y los centros regionales de "
            "I+D+i: el eje que sustenta las capacidades científicas de la "
            "política es el que menos se mueve. Y el núcleo de gobernanza "
            "presenta sus piezas articuladoras rezagadas: el modelo de "
            "gobernanza al 35%, el Consejo Asesor de Expertos al 15% —con "
            "vigencia vencida desde agosto de 2025— y la estrategia "
            "anticipatoria al 38% (DNP, 2026).")
    parrafo(doc,
            "El rezago de la estrategia anticipatoria merece atención particular "
            "de la Dirección: es la acción sobre la cual se fundamenta el "
            "Observatorio Nacional de Inteligencia Artificial, y su vigencia "
            "venció en diciembre de 2025 con un avance del 38%. Consolidar el "
            "Observatorio durante 2026 es, además de un objetivo institucional, "
            "la vía de cierre de una acción en mora.")
    parrafo(doc,
            "Dentro de cada objetivo, por último, la ejecución tampoco es "
            "homogénea, y el detalle por frente ayuda a localizar dónde está el "
            "movimiento real. En el objetivo de infraestructura conviven avances "
            "intermedios sólidos —el informe anual de gobierno digital y la "
            "estrategia de datos abiertos van en 70%, y el fortalecimiento de la "
            "infraestructura tecnológica del sector público en 66%— con un "
            "componente de espectro radioeléctrico y despliegue de red "
            "prácticamente detenido, en el que cuatro acciones consecutivas "
            "reportan 0% (DNP, 2026). En el frente sectorial del objetivo de "
            "adopción, el sector minero-energético sostiene tres acciones en 50%, "
            "el de salud avanza entre el 40% y el 61% —con la mejor ejecución "
            "financiera del objetivo—, y el cultural registra 46% con recursos "
            "plenamente ejecutados, mientras que las apuestas de mayor "
            "complejidad técnica, como los gemelos digitales, el modelo de "
            "simulación territorial y las estrategias con el sector transporte, "
            "permanecen en cero. El patrón que emerge es consistente: avanza lo "
            "que depende de una sola entidad con capacidad instalada, y se "
            "estanca lo que exige coordinación interinstitucional o desarrollo "
            "técnico nuevo.")

    titulo(doc, "8.4. El rezago no es neutro: lectura con enfoque diferencial", 2)
    parrafo(doc,
            "Al ordenar las acciones estancadas por su contenido, aparece un "
            "patrón directamente pertinente al foco de este contrato. Dentro del "
            "objetivo de mitigación de riesgos —el de mejor promedio general— "
            "permanecen en 0% precisamente las acciones del enfoque de "
            "derechos: la prevención de afectaciones a poblaciones étnicas, "
            "personas LGBTIQ+ y grupos históricamente excluidos (5.17), la "
            "estrategia contra las violencias basadas en género en entornos "
            "digitales, incluidos los deepfakes (5.18), los lineamientos sobre "
            "el impacto ambiental del consumo energético de la IA (5.19), la "
            "protección laboral frente a la automatización (5.10) y las "
            "capacidades mínimas de seguridad digital (5.6) (DNP, 2026).")
    parrafo(doc,
            "En el objetivo de talento ocurre algo análogo: las cinco acciones "
            "en 0% corresponden al sistema de cualificaciones, el "
            "reconocimiento de aprendizajes previos, la sensibilización de "
            "instituciones de educación superior y las operaciones estadísticas "
            "del DANE, es decir, a la arquitectura que permitiría medir y "
            "certificar las habilidades de las poblaciones que hoy están fuera. "
            "Mientras tanto, la acción de enfoque diferencial en el ciclo de "
            "vida de los datos (2.17) avanza 66% físico con solo 5% de "
            "ejecución financiera.")
    parrafo(doc,
            "La conclusión preliminar es incómoda pero está en los datos: el "
            "componente de la política que protege y habilita a los grupos en "
            "desventaja avanza más lento que el promedio. Si el patrón persiste "
            "al cierre de 2026, la política habrá sido más eficaz en construir "
            "infraestructura y regular la técnica que en garantizar que sus "
            "beneficios alcancen a quienes el propio CONPES priorizó. El dato "
            "tiene, con todo, una cara aprovechable: identificado a tiempo, es "
            "el tipo de rezago que una alerta temprana en las instancias de "
            "seguimiento puede corregir dentro de la vigencia, y este informe "
            "cumple justamente esa función.")

    titulo(doc, "8.5. Horizonte de cierre de la vigencia", 2)
    parrafo(doc,
            "Queda por dimensionar lo que el segundo semestre tiene por delante, "
            "y para ello ayuda descomponer las treinta acciones cuya vigencia "
            "termina en 2026 según su estado al corte.")
    tabla(doc, "Estado de las acciones con vigencia hasta 2026, corte del 21 de julio",
          ["Estado al corte", "Acciones", "Lectura"],
          [["Cerradas al 100%", "11",
            "Cierre asegurado; incluyen piezas de infraestructura, talento y seguridad digital."],
           ["En curso, con avance parcial", "7",
            "Promedio del 52,9% entre las reportadas; su cierre depende del ritmo del semestre."],
           ["En 0% con vigencia venciendo", "8",
            "El grupo crítico: sin arranque visible y con menos de seis meses de plazo."],
           ["Iniciadas en 2026, aún sin reporte", "4",
            "Su primer reporte llegará en el corte del segundo semestre."]],
          "elaboración propia a partir de DNP (2026).", anchos=[4.2, 2.0, 9.8])
    parrafo(doc,
            "A ese frente se suman las quince acciones rezagadas de 2025, de "
            "modo que el semestre define si la política llega al cierre del año "
            "con cerca de un tercio de sus acciones finalizadas —el escenario "
            "alcanzable si se consolidan las que están en curso— o con un rezago "
            "acumulado que comprometa el cuatrienio. Las condiciones críticas "
            "son tres: aprobar los cuarenta reportes en revisión para "
            "estabilizar la línea oficial de avance, destrabar los frentes de "
            "gobernanza, I+D+i y espectro, y normalizar el reporte financiero.")


def resultados(doc):
    titulo(doc, "9. Reporte parcial de resultados", 1)

    titulo(doc, "9.1. Síntesis de hallazgos preliminares", 2)
    tabla(doc, "Hallazgos preliminares del estudio al corte de agosto de 2026",
          ["Ámbito", "Hallazgo", "Evidencia"],
          [["Sector", "El crecimiento de la conectividad fija se desaceleró, pero el parque se modernizó: la fibra al hogar pasó del 8,5% al 32,5% de los accesos. El margen del sector se desplazó del despliegue de red al uso y las habilidades.",
            "MinTIC (2024); DANE (2025); DNP (2025b)"],
           ["Territorio", "Seis departamentos periféricos retroceden en accesos fijos mientras el país crece 27,5%; donde hubo intervención sostenida (San Andrés, Putumayo, Arauca) la periferia convergió a ritmos de hasta el triple del promedio nacional.",
            "MinTIC (2024)"],
           ["Diseño", "La formulación incorporó el enfoque territorial y diferencial de forma medible, pero asigna quince veces más recursos a infraestructura que a capacidades sin formular la hipótesis que las conecta; el sistema de medición no contiene indicadores de resultado.",
            "DNP (2025c); análisis de corpus, Entrega 2"],
           ["Ejecución", "Avance físico del 43,3% con financiación completa y disciplina de reporte del 87,7%; 24 acciones cerradas, entre ellas la estadística de pobreza digital; 15 de 18 acciones vencidas en 2025 sin cierre y el núcleo de gobernanza rezagado.",
            "DNP (2026)"],
           ["Equidad", "Las acciones del enfoque de derechos y de la arquitectura de habilidades son las más rezagadas; la brecha de género en formación en IA se produce en el acceso, no en la permanencia.",
            "DNP (2026); MinTIC (2026b)"]],
          "elaboración propia.", anchos=[2.6, 8.6, 4.8])

    titulo(doc, "9.2. La brecha de género en formación, revisitada", 2)
    parrafo(doc,
            "La prueba de viabilidad de la Entrega 2 se consolida aquí como "
            "resultado preliminar del estudio, porque su implicación de política "
            "es mayor de lo que su tamaño sugiere. En el registro administrativo "
            "de formación en inteligencia artificial analizado —1.549 "
            "participantes de un programa ejecutado en 2025 (MinTIC, 2026b)—, "
            "mujeres y hombres culminan en proporciones casi idénticas (30,1% y "
            "30,4%), pero las mujeres son solo el 37,1% de quienes ingresan.")
    figura(doc, "fig5_senatic.png",
           "Formación en IA: composición de inscritos y tasa de certificación "
           "por sexo",
           "elaboración propia a partir de MinTIC (2026b); 1.549 registros de "
           "2025, cobertura predominantemente municipal.")
    parrafo(doc,
            "La Figura 6 condensa el hallazgo en dos paneles que deben leerse en "
            "contraste. El panel izquierdo muestra una brecha grande: por cada "
            "diez personas que entran al programa, apenas cuatro son mujeres. El "
            "panel derecho muestra que esa brecha desaparece por completo una "
            "vez adentro: la diferencia en la tasa de certificación es de tres "
            "décimas de punto, estadísticamente indistinguible de cero en una "
            "muestra de este tamaño. La combinación descarta las explicaciones "
            "habituales del rezago femenino en formación tecnológica —menor "
            "disponibilidad de tiempo, menor afinidad previa con el contenido, "
            "abandono por cargas de cuidado—, porque todas ellas predicen una "
            "brecha en la permanencia que los datos no muestran.")
    parrafo(doc,
            "Lo que queda en pie es una brecha de convocatoria: el problema "
            "ocurre antes de la inscripción, en cómo circula la información del "
            "programa, en qué canales se difunde y a quién le habla la "
            "invitación. Para el diseño de los programas del eje de talento "
            "—incluida la acción 4.8, ya cerrada, y la herramienta de "
            "orientación de la acción 4.14— la consecuencia operativa es "
            "concreta: los recursos de cierre de brecha rinden más en "
            "convocatoria y difusión focalizada que en mecanismos de retención, "
            "que es donde suelen invertirse.")
    parrafo(doc,
            "El dato de los docentes agrega una segunda pista de diseño: su tasa "
            "de certificación del 80% —contra 34,1% de la población general y "
            "21,5% de los estudiantes— los señala como el segmento de mayor "
            "aprovechamiento por peso invertido, y sugiere que la formación de "
            "formadores es el canal con mejor relación costo-efecto para "
            "escalar la alfabetización en inteligencia artificial, un resultado "
            "consistente con la apuesta de la política por la apropiación "
            "social del conocimiento.")
    parrafo(doc,
            "El alcance del dato sigue siendo local —el 99,7% de los registros "
            "corresponde a un municipio— y por eso se presenta como ilustración "
            "del método y no como medición nacional. Su valor está en demostrar "
            "que la desagregación necesaria existe en los registros "
            "administrativos del sector, y en anticipar el tipo de resultado que "
            "la entrega final buscará replicar sobre fuentes de cobertura "
            "nacional, en particular la encuesta de tecnologías de la "
            "información del DANE.")

    titulo(doc, "9.3. Situación deseada y punto de partida, actualización", 2)
    parrafo(doc,
            "Frente al balance presentado en la Entrega 2, el estado del estudio "
            "avanzó en tres frentes: el análisis descriptivo y territorial pasó "
            "de previsto a ejecutado en primera versión; la evaluación de diseño "
            "quedó completa; y la evaluación intermedia quedó construida sobre "
            "el corte de julio. Las dos condiciones pendientes para la entrega "
            "final son la validación de la matriz de indicadores con la "
            "supervisión y la disponibilidad de los reportes aprobados del "
            "segundo semestre, que estabilizarán las cifras de ejecución hoy "
            "provisionales.")
    parrafo(doc,
            "Los hallazgos de este informe permiten, además, refinar esa matriz "
            "antes de su validación, y ese es quizás su aporte más directo a la "
            "continuidad del producto. Tres ajustes se desprenden de la "
            "evidencia. Primero, el indicador de brecha de conectividad debería "
            "medirse no solo como distancia de niveles entre cabecera y zona "
            "rural, sino también como signo de la variación por departamento, "
            "porque el capítulo 5 mostró que el problema activo es la "
            "divergencia y un indicador de nivel no la captura. Segundo, "
            "conviene incorporar la proporción de accesos con velocidad igual o "
            "superior a cien megabits como indicador de calidad, dado que el "
            "capítulo 4 demostró que la transformación reciente del sector "
            "ocurrió en profundidad y no en extensión, y medir solo cantidad "
            "dejaría fuera el cambio más importante del periodo. Y tercero, la "
            "composición por estrato de los accesos merece seguimiento propio, "
            "pues es el dato que conecta la política sectorial con el mandato "
            "contractual de inclusión digital y ya mostró capacidad de registrar "
            "movimientos en plazos cortos.")


def conclusiones(doc):
    titulo(doc, "10. Conclusiones parciales y próximos pasos", 1)
    parrafo(doc,
            "El sector TIC colombiano llega a 2026 con un balance de dos caras "
            "documentado en este informe. Del lado positivo, el parque de "
            "conectividad se modernizó a un ritmo notable —la fibra al hogar "
            "casi se quintuplicó en cinco años—, los hogares conectados siguen "
            "aumentando, y los casos de San Andrés, Putumayo y Arauca demuestran "
            "que la inversión pública dirigida produce convergencia territorial "
            "real. Del lado crítico, el crecimiento agregado se estancó, seis "
            "departamentos periféricos retroceden, y la privación dominante ya "
            "no está en la red sino en las capacidades de uso.")
    parrafo(doc,
            "La Política Nacional de Inteligencia Artificial muestra un patrón "
            "análogo. A su favor: está completamente financiada, reporta con una "
            "disciplina del 87,7%, incorporó en su formulación el enfoque "
            "territorial y diferencial que su antecesora no tenía, y cerró "
            "veinticuatro acciones entre las que se cuentan piezas de valor "
            "verificable, incluida la estadística oficial con la que este "
            "estudio la evalúa. En contra: su ejecución va a menos de la mitad, "
            "su núcleo de gobernanza está en mora, y las acciones de equidad "
            "avanzan más lento que el promedio.")
    parrafo(doc,
            "Para la Dirección, los resultados preliminares dejan tres asuntos "
            "accionables. Primero, el cierre de la estrategia anticipatoria "
            "—vencida con 38% de avance— puede apalancarse en la consolidación "
            "del Observatorio Nacional de Inteligencia Artificial durante el "
            "segundo semestre. Segundo, la aprobación de los cuarenta reportes "
            "en revisión es condición para que el balance de la vigencia se haga "
            "sobre cifras estables. Tercero, el rezago de las acciones del "
            "enfoque de derechos amerita señalarse en las instancias de "
            "seguimiento de la política antes del cierre del año, cuando "
            "todavía es corregible; la experiencia de la acción 2.8 —que "
            "produjo una estadística oficial de resultado en menos de un año— "
            "demuestra que los cierres rápidos son posibles cuando hay decisión "
            "institucional.")
    parrafo(doc,
            "Hacia la entrega final, el plan de trabajo es el siguiente: validar "
            "la matriz de indicadores con la supervisión, incorporando los tres "
            "ajustes propuestos en el numeral 9.3; actualizar las series "
            "sectoriales con los cortes que publiquen el MinTIC y el DANE en el "
            "segundo semestre; incorporar el reporte de SisCONPES del cierre de "
            "2026 y recalcular la evaluación intermedia sobre reportes "
            "aprobados; aplicar la aproximación ex post sobre las 48 acciones "
            "cuya vigencia termina este año; profundizar el análisis de las "
            "causas del retroceso territorial en los seis departamentos "
            "identificados; y consolidar el documento final con las "
            "recomendaciones estratégicas para la Dirección.")
    parrafo(doc,
            "Ese plan enfrenta dos riesgos que conviene dejar identificados desde "
            "ahora, junto con su mitigación. El primero es de datos: si el "
            "reporte de cierre de vigencia en SisCONPES se publica con retraso, o "
            "si una parte sustancial de los cuarenta reportes en revisión se "
            "modifica durante la aprobación, la evaluación ex post tendría que "
            "construirse sobre cifras inestables; la mitigación acordable con la "
            "supervisión consiste en fijar desde ya un corte de referencia y "
            "documentar cualquier diferencia posterior como nota de "
            "actualización, en lugar de recalcular en cadena. El segundo es de "
            "calendario: la entrega final vence el 22 de diciembre, pocos días "
            "después del cierre administrativo del año, de modo que el margen "
            "para incorporar información de última hora es estrecho; por ello el "
            "grueso del procesamiento quedará listo en noviembre y diciembre se "
            "reservará para la actualización de cifras y la redacción final.")


def referencias(doc):
    titulo(doc, "Referencias", 1)
    refs = [
        "Barzelay, M. (2001). The new public management: Improving research and policy dialogue. University of California Press.",
        "Bonnefoy, J. C., y Armijo, M. (2005). Indicadores de desempeño en el sector público (Serie Manuales n.º 45). Instituto Latinoamericano y del Caribe de Planificación Económica y Social, Cepal.",
        "Departamento Administrativo Nacional de Estadística. (2025). Encuesta Nacional de Calidad de Vida 2024: boletín técnico. DANE.",
        "Departamento Nacional de Planeación. (2019). Documento CONPES 3975. Política nacional para la transformación digital e inteligencia artificial. DNP.",
        "Departamento Nacional de Planeación. (2025). Documento CONPES 4144. Política nacional de inteligencia artificial. DNP. https://colaboracion.dnp.gov.co/CDT/Conpes/Económicos/4144.pdf",
        "Departamento Nacional de Planeación. (2025b). Índice de Pobreza Digital: resultados. DNP.",
        "Departamento Nacional de Planeación. (2025c). Anexo A. Plan de Acción y Seguimiento del documento CONPES 4144 [instrumento de seguimiento, SisCONPES]. DNP.",
        "Departamento Nacional de Planeación. (2026). Reporte y revisión del documento CONPES 4144 [módulo de SisCONPES, corte del 21 de julio de 2026]. DNP.",
        "Dunleavy, P., Margetts, H., Bastow, S., y Tinkler, J. (2006). New public management is dead—Long live digital-era governance. Journal of Public Administration Research and Theory, 16(3), 467-494.",
        "Gertler, P. J., Martínez, S., Premand, P., Rawlings, L. B., y Vermeersch, C. M. J. (2017). La evaluación de impacto en la práctica (2.ª ed.). Banco Mundial.",
        "Miller, R. (Ed.). (2018). Transforming the future: Anticipation in the 21st century. Unesco y Routledge.",
        "Ministerio de Tecnologías de la Información y las Comunicaciones. (2024). Internet fijo: accesos por tecnología y segmento [conjunto de datos, identificador n48w-gutb]. Portal de Datos Abiertos de Colombia. https://www.datos.gov.co/",
        "Ministerio de Tecnologías de la Información y las Comunicaciones. (2026b). Participantes certificados en inteligencia artificial – SENATIC [conjunto de datos, identificador m2uu-cu4q]. Portal de Datos Abiertos de Colombia. https://www.datos.gov.co/",
        "Organización para la Cooperación y el Desarrollo Económicos. (2019). Measuring the digital transformation: A roadmap for the future. OECD Publishing.",
        "Organización para la Cooperación y el Desarrollo Económicos. (2026). The OECD going digital measurement roadmap 2026. OECD Publishing.",
        "Ruiz Castro, R. E. (2026). Marco conceptual, normativo y de fuentes para el análisis de datos y la evaluación de impacto de las políticas públicas del sector TIC (Informe técnico, Entrega 2, contrato DNP-1025-2026). Departamento Nacional de Planeación, DENDD.",
        "Taeihagh, A. (2021). Governance of artificial intelligence. Policy and Society, 40(2), 137-157.",
        "Unión Internacional de Telecomunicaciones. (2024). Measuring digital development: Facts and figures 2024. UIT.",
        "Vanegas Barrero, V., Dávila Barragán, J., y Barreto Nieto, C. A. (2024, noviembre). Pobreza digital, una nueva perspectiva para fortalecer la inclusión social en Colombia. Planeación & Desarrollo. Departamento Nacional de Planeación.",
    ]
    for r in refs:
        parrafo(doc, r, sangria_francesa=True, space_after=6)


def anexos(doc):
    titulo(doc, "Anexos", 1)
    titulo(doc, "Anexo A. Código de reproducción de las consultas de datos", 2)
    parrafo(doc,
            "Las cifras de los capítulos 4, 5 y 8 se reproducen con la rutina "
            "consultas_sector_tic.py, que ejecuta las agregaciones sobre los "
            "conjuntos de datos del Portal de Datos Abiertos mediante su "
            "interfaz de consulta e imprime los resultados. No tiene "
            "dependencias fuera de la biblioteca estándar y se entrega como "
            "archivo adjunto, junto con la rutina de análisis de corpus ya "
            "entregada con la Entrega 2.")
    titulo(doc, "Anexo B. Declaración de uso de herramientas de inteligencia artificial", 2)
    parrafo(doc,
            "Conforme a las Pautas para la elaboración, revisión y entrega de "
            "documentos técnicos de la Dirección, se declara el uso de "
            "herramientas de inteligencia artificial generativa como apoyo en la "
            "organización del documento, la redacción de borradores, la "
            "construcción de las consultas de datos y la generación de las "
            "visualizaciones. Todo contenido producido con ese apoyo fue "
            "verificado por el autor contra las fuentes primarias citadas; las "
            "herramientas no son autoras del documento y sus salidas se tratan "
            "como resultado de un procedimiento y no como fuente de hechos. Las "
            "cifras de los capítulos 4 y 5 son reproducibles con el código del "
            "Anexo A; las del capítulo 7 provienen de los reportes "
            "institucionales citados.")


def construir(salida):
    base._CONTADOR_TABLAS[0] = 0
    base._CONTADOR_FIGURAS[0] = 0
    doc = Document()
    configurar_estilos(doc)
    s0 = doc.sections[0]
    margenes(s0)
    s0.different_first_page_header_footer = True
    portada(doc,
            "Estado del arte, análisis del sector TIC y evaluación preliminar de "
            "la Política Nacional de Inteligencia Artificial",
            "Informe técnico – Entrega 3 – Vigencia 2026", "Versión 1")
    s1 = doc.add_section(WD_SECTION.NEW_PAGE)
    margenes(s1)
    encabezado_paginado(s1)
    pagina_legal(doc)
    salto(doc)
    toc_estatica(doc)
    salto(doc)
    siglas(doc)
    salto(doc)
    presentacion(doc)
    salto(doc)
    resumen_ejecutivo(doc)
    salto(doc)
    introduccion(doc)
    estado_arte(doc)
    metodologia(doc)
    tendencias(doc)
    brechas(doc)
    ex_ante(doc)
    ex_ante_medicion(doc)
    intermedia(doc)
    resultados(doc)
    conclusiones(doc)
    salto(doc)
    referencias(doc)
    anexos(doc)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    doc.save(salida)
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=SALIDA_DEFECTO)
    ap.add_argument("--figs", required=True, help="directorio con las figuras PNG")
    args = ap.parse_args()
    DIR_FIGURAS[0] = args.figs
    print(f"documento generado: {compilar(construir, args.salida)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
