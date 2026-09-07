#!/usr/bin/env python3
"""
Nota técnica de insumos para el "Diagnóstico del sector TIC en Colombia —
insumos para el PND 2026-2030" de la DENDD, temas 6, 7, 9 y 10.

Responde a la solicitud de la coordinación del diagnóstico: identificar qué
puede aportar este contrato a los cuatro temas de la dimensión III
(Transformación digital) y dejar cada dato con su fuente verificable.

El criterio que organiza la nota es el de trazabilidad: como el uso de
herramientas de inteligencia artificial en la elaboración del diagnóstico
está condicionado a que la evidencia sea verificable, cada cifra se clasifica
en uno de tres niveles de verificación (capítulo 2) y ninguna cifra entra sin
enlace a la publicación que la sostiene.

Reusa la infraestructura de formato de tools/dnp-entregas/build_entrega2.py
(pautas DENDD: carta, márgenes 2,54 cm, Arial 11, interlineado 1,5,
numeración decimal, encabezado con logo y "Página X de Y", tablas numeradas
con título arriba y fuente abajo).

Uso:
    python3 build_nota_temas.py [--salida RUTA.docx] [--pdf]
"""

import argparse
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "tools", "dnp-entregas"))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.shared import Cm

import build_entrega2 as base
from build_entrega2 import (configurar_estilos, encabezado_paginado, margenes,
                            parrafo, portada, salto, titulo, vineta)

from fuentes import FUENTES

SALIDA_DEFECTO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Nota-Fuentes-Temas-6-7-9-10-DiagnosticoTIC-v1.docx",
)

# LibreOffice cambia de ruta entre el equipo de trabajo (macOS) y los entornos
# Linux donde también se compila; se toma la primera que exista.
SOFFICE = next((r for r in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                            "/usr/bin/soffice", "/usr/bin/libreoffice")
                if os.path.exists(r)), None)


def tabla(doc, *args, **kwargs):
    """base.tabla fija el ancho en cada celda, que es lo que lee Word, pero no
    la cuadrícula (w:tblGrid), que es lo que lee LibreOffice al convertir a
    PDF. Sin esto las columnas salen todas iguales en la vista previa."""
    t = base.tabla(doc, *args, **kwargs)
    anchos = kwargs.get("anchos") or (args[4] if len(args) > 4 else None)
    if anchos:
        grid = t._tbl.find(qn("w:tblGrid"))
        if grid is not None:
            for col, ancho in zip(grid.findall(qn("w:gridCol")), anchos):
                col.set(qn("w:w"), str(int(Cm(ancho).twips)))
    return t


# --------------------------------------------------------------------------
# Preliminares
# --------------------------------------------------------------------------

def pagina_legal(doc):
    titulo(doc, "Página legal y control documental", 1)
    parrafo(doc,
            "Esta nota es un insumo interno para la construcción del documento "
            "«Diagnóstico del sector TIC en Colombia. Insumos para la "
            "construcción del Plan Nacional de Desarrollo 2026-2030» de la "
            "Dirección de Economía Naranja y Desarrollo Digital. No es un "
            "documento de política ni una entrega contractual: su función es "
            "poner a disposición de los responsables de los temas 6, 7, 9 y 10 "
            "el material ya producido por el contrato DNP-1025-2026 y el "
            "registro de fuentes verificables asociado a cada tema.")
    tabla(doc, "Control documental",
          ["Campo", "Contenido"],
          [["Título", "Fuentes verificables y aportes disponibles para los temas 6, 7, "
                      "9 y 10 del diagnóstico del sector TIC"],
           ["Tipo documental", "Nota técnica de insumos"],
           ["Documento al que sirve", "Diagnóstico del sector TIC — insumos PND 2026-2030 "
                                      "(borrador de septiembre de 2026)"],
           ["Versión", "1"],
           ["Dependencia responsable", "Dirección de Economía Naranja y Desarrollo Digital"],
           ["Elabora", "Ricardo Esteban Ruiz Castro, contratista"],
           ["Destinatarios", "Responsables de los temas 6 (Edward), 7 (Margarita), "
                             "9 (Edward y Carlos) y 10 (Margarita), y coordinación "
                             "del diagnóstico"],
           ["Fecha de la versión", "Septiembre de 2026"],
           ["Fecha de corte de la consulta de fuentes", "7 de septiembre de 2026"]],
          "elaboración propia.", anchos=[4.5, 11.5])


def siglas(doc):
    titulo(doc, "Siglas y abreviaturas", 1)
    tabla(doc, "Siglas y abreviaturas empleadas en la nota",
          ["Sigla", "Significado"],
          [["CCCE", "Cámara Colombiana de Comercio Electrónico"],
           ["Cenia", "Centro Nacional de Inteligencia Artificial (Chile)"],
           ["Cepal", "Comisión Económica para América Latina y el Caribe"],
           ["CONPES", "Consejo Nacional de Política Económica y Social"],
           ["CRC", "Comisión de Regulación de Comunicaciones"],
           ["CSTIC", "Cuenta Satélite de las Tecnologías de la Información y las Comunicaciones"],
           ["DANE", "Departamento Administrativo Nacional de Estadística"],
           ["DENDD", "Dirección de Economía Naranja y Desarrollo Digital"],
           ["DNP", "Departamento Nacional de Planeación"],
           ["EGDI", "Índice de Desarrollo del Gobierno Electrónico (Naciones Unidas)"],
           ["ENSD", "Estrategia Nacional de Seguridad Digital"],
           ["ENTIC", "Encuesta de Tecnologías de la Información y las Comunicaciones"],
           ["IA", "Inteligencia artificial"],
           ["IGD", "Índice de Gobierno Digital"],
           ["ILIA", "Índice Latinoamericano de Inteligencia Artificial"],
           ["MinTIC", "Ministerio de Tecnologías de la Información y las Comunicaciones"],
           ["OCDE", "Organización para la Cooperación y el Desarrollo Económicos"],
           ["ONIA", "Observatorio Nacional de Inteligencia Artificial"],
           ["ONTIC", "Observatorio del sector TIC del MinTIC"],
           ["PAS", "Plan de Acción y Seguimiento"],
           ["Renadia", "Red Nacional de Datos e Inteligencia Artificial"],
           ["SisCONPES", "Sistema de Seguimiento a Documentos CONPES"],
           ["SODA", "Interfaz de consulta del Portal de Datos Abiertos (Socrata Open Data API)"],
           ["UIT", "Unión Internacional de Telecomunicaciones"]],
          "elaboración propia.", anchos=[3.0, 13.0])


def presentacion(doc):
    titulo(doc, "Presentación", 1)
    parrafo(doc,
            "La coordinación del diagnóstico pidió revisar la estructura "
            "temática del documento e identificar, desde el material ya "
            "producido por este contrato, qué se puede aportar a los temas de "
            "la dimensión III y con qué fuentes. Esta nota responde esa "
            "solicitud para los cuatro temas señalados: economía digital y "
            "transformación productiva (6), inteligencia artificial y "
            "tecnologías emergentes (7), gobierno digital y territorios "
            "inteligentes (9) y confianza y seguridad digital (10).")
    parrafo(doc,
            "La nota parte de una restricción explícita del encargo: el uso de "
            "herramientas de inteligencia artificial en la elaboración del "
            "diagnóstico está condicionado a que la evidencia sea verificable. "
            "Esa restricción se toma aquí no como una limitación sino como el "
            "criterio de organización del documento. Por eso el capítulo 2 fija "
            "un protocolo de tres niveles de verificación, cada cifra de los "
            "capítulos 4 a 7 lleva su nivel, y el capítulo 8 consolida el "
            "registro de fuentes con el enlace de cada una. Ninguna cifra "
            "aparece sin la publicación que la sostiene.")
    parrafo(doc,
            "El aporte principal de este contrato a los cuatro temas no es un "
            "conjunto de cifras nuevas, sino tres cosas que ya están "
            "construidas y son reutilizables: rutinas de consulta que "
            "reproducen cada cifra sectorial desde su fuente pública sin "
            "procesamiento manual; la única evaluación intermedia disponible "
            "de la Política Nacional de Inteligencia Artificial, hecha sobre "
            "los reportes de SisCONPES; y evidencia primaria propia sobre las "
            "barreras que los servidores públicos identifican para adoptar "
            "datos e IA, recogida en el piloto de Renadia.")


# --------------------------------------------------------------------------
# Cuerpo
# --------------------------------------------------------------------------

def alcance(doc):
    titulo(doc, "1. Alcance de la nota", 1)
    parrafo(doc,
            "El borrador de septiembre de 2026 tiene desarrollados los temas 1 "
            "y 2 y deja los ocho restantes como títulos. Esta nota no redacta "
            "ninguno de ellos: entrega el material y las fuentes para que sus "
            "responsables lo hagan, respetando la estructura de cinco preguntas "
            "que fijó la metodología (situación actual, evolución, brechas, "
            "retos 2026-2030 y mensaje para el PND) y el límite de dos páginas "
            "por tema.")
    parrafo(doc,
            "En consecuencia, cada capítulo temático de esta nota se organiza en "
            "tres partes: qué puede aportar el material ya producido por el "
            "contrato, qué fuentes externas verificables alimentan las cinco "
            "preguntas, y qué vacío queda abierto. Las lecturas analíticas que "
            "se proponen se presentan como tales y son discutibles; los datos "
            "que las sostienen son los que llevan fuente.")
    parrafo(doc,
            "Dos advertencias de alcance. La primera es que esta nota no "
            "reemplaza la consulta directa de las publicaciones: el capítulo 2 "
            "explica en qué condiciones se verificó cada dato y cuáles exigen "
            "cotejo antes de entrar al documento. La segunda es que los temas 6 "
            "y 9 tienen responsables asignados que conocen su materia; lo que "
            "aquí se ofrece es insumo, no sustitución.")


def protocolo(doc):
    titulo(doc, "2. Protocolo de verificación de la evidencia", 1)
    parrafo(doc,
            "Toda cifra que se incorpore al diagnóstico debe poder rastrearse "
            "hasta un documento publicado. Para que esa exigencia sea operativa "
            "y no retórica, esta nota clasifica cada dato en uno de tres "
            "niveles, que se indican entre corchetes junto a la cifra.")
    tabla(doc, "Niveles de verificación empleados en esta nota",
          ["Nivel", "Qué significa", "Uso admisible en el diagnóstico"],
          [["A",
            "Cifra producida o reproducida por este contrato a partir de la "
            "fuente primaria, con la rutina de consulta documentada y "
            "ejecutable. Se puede volver a calcular en cualquier momento.",
            "Citable directamente. La rutina se anexa como soporte."],
           ["B",
            "Cifra publicada por una entidad oficial o un organismo "
            "multilateral, con documento y enlace identificados, tomada de esa "
            "publicación pero sin cotejo página a página por parte de quien "
            "elabora esta nota.",
            "Citable previa apertura del documento y confirmación del dato "
            "exacto, que toma minutos. Nunca citar solo desde esta nota."],
           ["C",
            "Cifra que circula en prensa, en comunicados o en resúmenes de "
            "terceros, sin que se haya identificado la publicación primaria que "
            "la produce.",
            "No citable. Sirve únicamente como pista para ir a buscar la fuente "
            "primaria."]],
          "elaboración propia.", anchos=[1.6, 7.4, 7.0])
    parrafo(doc,
            "La distinción importa porque el diagnóstico va a ser leído con "
            "atención a la trazabilidad. Un dato de nivel C que entre al "
            "documento sin fuente primaria es exactamente el tipo de hallazgo "
            "que compromete la credibilidad del conjunto, aunque la cifra sea "
            "correcta. El capítulo 7 documenta un caso concreto de este riesgo "
            "en materia de seguridad digital.")
    parrafo(doc,
            "Sobre el uso de herramientas de inteligencia artificial en la "
            "elaboración de esta nota, la declaración correspondiente está en "
            "el Anexo A, siguiendo la práctica ya adoptada en las entregas 2 y "
            "3 de este contrato.")


def productos(doc):
    titulo(doc, "3. Qué aporta el material ya producido por el contrato", 1)
    parrafo(doc,
            "Antes de entrar tema por tema conviene inventariar lo que ya "
            "existe, porque buena parte es transversal a los cuatro temas y "
            "está disponible de inmediato.")

    titulo(doc, "3.1. Rutinas reproducibles de consulta sectorial", 2)
    parrafo(doc,
            "El Anexo A de la Entrega 3 es un conjunto de rutinas que consultan "
            "el Portal de Datos Abiertos mediante su interfaz de programación y "
            "reproducen, sin intervención manual, las series del sector: la "
            "serie nacional de accesos fijos, los agregados departamentales y "
            "municipales, la distribución de velocidades, la composición por "
            "estrato y el procesamiento del registro de formación en IA. Operan "
            "sobre el conjunto del MinTIC de accesos fijos por tecnología y "
            "segmento, que tiene 2,79 millones de registros con desagregación "
            "municipal, trimestral y por operador [A].")
    parrafo(doc,
            "Su valor para este diagnóstico es directo: cualquier cifra "
            "sectorial que entre al documento por esta vía queda acompañada de "
            "la consulta exacta que la produce, de modo que un tercero puede "
            "reejecutarla y obtener el mismo número. Es la respuesta más "
            "sólida disponible frente a la exigencia de trazabilidad, y sirve "
            "igual para los cuatro temas.")

    titulo(doc, "3.2. Evaluación de la Política Nacional de Inteligencia Artificial", 2)
    parrafo(doc,
            "La Entrega 3 contiene la evaluación de diseño y la evaluación "
            "intermedia del CONPES 4144, construidas sobre el Plan de Acción y "
            "Seguimiento y sobre los reportes de SisCONPES con corte al 21 de "
            "julio de 2026, ambos facilitados por la Dirección. Ese material no "
            "es público: el Anexo A del CONPES se publica sin contenido, de "
            "manera que este análisis es, hasta donde alcanza la revisión "
            "hecha, el único disponible sobre la ejecución efectiva de la "
            "política [A].")

    titulo(doc, "3.3. Analítica de texto sobre el corpus de política", 2)
    parrafo(doc,
            "La Entrega 2 incorpora un procedimiento de analítica de texto que "
            "compara los documentos CONPES 3975 de 2019 y 4144 de 2025 por "
            "párrafo, midiendo la presencia de tres familias léxicas "
            "—territorial, diferencial y de habilidades— y la frecuencia de los "
            "términos de política. El código está anexado y descarga los PDF "
            "desde la biblioteca pública del DNP, de modo que los porcentajes "
            "se recalculan en cualquier momento [A]. Es el instrumento natural "
            "para responder la pregunta de evolución («¿qué ha cambiado durante "
            "los dos últimos gobiernos?») en los temas que tienen dos "
            "documentos CONPES comparables, que son el 7 y el 10.")

    titulo(doc, "3.4. Evidencia primaria propia: el piloto de Renadia", 2)
    parrafo(doc,
            "El piloto del microsite de Renadia recogió respuestas de "
            "servidores públicos, sector privado, entidades territoriales y "
            "academia entre el 6 y el 9 de julio de 2026: 33 participantes y 73 "
            "partidas, con la distribución y los resultados consolidados en el "
            "informe de resultados del piloto [A]. Entre lo que los "
            "participantes señalaron como principal freno para avanzar en datos "
            "e IA, las cuatro respuestas más frecuentes fueron la falta de "
            "capacidades o talento (33 %), la falta de pares con quienes "
            "intercambiar experiencias (28 %), la falta de claridad para usar "
            "IA con ética (19 %) y la falta de datos de calidad (19 %).")
    parrafo(doc,
            "Estos resultados deben usarse con una advertencia explícita y no "
            "negociable: se trata de una muestra pequeña y autoseleccionada, "
            "sin representatividad estadística. No sirven para afirmar una "
            "proporción poblacional, pero sí para ilustrar cualitativamente un "
            "orden de prioridades que ninguna fuente oficial recoge hoy, y esa "
            "es una carencia relevante en sí misma para los temas 7 y 9. "
            "Presentados como evidencia exploratoria y con la advertencia "
            "puesta, aportan; presentados como estadística, restan.")

    titulo(doc, "3.5. Diagnóstico del uso de tableros en entidades públicas", 2)
    parrafo(doc,
            "La propuesta de mesas temáticas y diálogos bilaterales de Renadia "
            "desarrolla, en su mesa piloto, el ciclo de vida de los tableros de "
            "datos en entidades públicas nacionales y territoriales: creación, "
            "uso, administración, sostenimiento y abandono. El alcance temático "
            "y las preguntas de esa mesa constituyen un diagnóstico cualitativo "
            "estructurado de un problema que el tema 9 tiene que nombrar y "
            "sobre el que no hay medición oficial.")


def tema6(doc):
    titulo(doc, "4. Tema 6. Economía digital y transformación productiva", 1)

    titulo(doc, "4.1. Lectura que se propone", 2)
    parrafo(doc,
            "Hay un contraste que conviene poner en el centro de este tema, "
            "porque cambia el mensaje para el PND. Según la Cuenta Satélite "
            "TIC, la participación del sector TIC en el valor agregado nacional "
            "fue de 3,6 % en 2023p y de 3,5 % en 2024pr [B], y el propio "
            "borrador del diagnóstico reporta 3,47 % para 2025pr. Es decir: la "
            "serie viene descendiendo, no creciendo. En el mismo período, el "
            "comercio electrónico pasó de 35,8 billones de pesos en 2019 a "
            "145,4 billones en 2025 [B].")
    parrafo(doc,
            "La lectura que se desprende es que la economía digital crece mucho "
            "más rápido que el sector que la provee. El valor de la "
            "digitalización se está realizando fuera del sector TIC, en el "
            "comercio, la banca, la logística y los servicios. Si eso es así, "
            "medir el éxito de la política por el tamaño del sector TIC es "
            "medir la variable equivocada, y el mensaje para el PND es que el "
            "indicador de resultado debería ser el grado de digitalización del "
            "resto de la economía, no el peso del proveedor.")
    parrafo(doc,
            "Un segundo dato apunta en la misma dirección y tiene lectura de "
            "inclusión: en 2025 las transacciones de comercio electrónico "
            "crecieron 19,9 % mientras el ticket promedio cayó 7,3 %, hasta "
            "212.373 pesos [B]. Más gente comprando cosas más baratas y con más "
            "frecuencia es masificación por abajo, un hecho de política social "
            "y no solo de comercio, y conecta este tema con el 4 y el 5.")

    titulo(doc, "4.2. Fuentes que alimentan las cinco preguntas", 2)
    tabla(doc, "Fuentes verificables para el tema 6",
          ["Pregunta", "Fuente", "Qué aporta", "Nivel"],
          [["Situación actual",
            "DANE, Cuenta Satélite TIC 2024pr (boletín del 28 de marzo de 2025)",
            "Participación del sector en el valor agregado nacional y "
            "composición interna: servicios TI 40,1 %, telecomunicaciones "
            "36,6 %, comercio TIC 12,8 %, contenidos y medios 9,6 %, industria "
            "manufacturera TIC 0,5 % (2024pr).", "B"],
           ["Situación actual",
            "CCCE, Informe de cierre eCommerce 2025 (versión pública)",
            "Ventas en línea de 145,4 billones nominales (+11,1 %) y 105,7 "
            "billones reales (+5,9 %); 684,6 millones de transacciones "
            "(+19,9 %); ticket promedio de 212.373 pesos (−7,3 %).", "B"],
           ["Evolución",
            "DANE, serie histórica de la Cuenta Satélite TIC",
            "Trayectoria de la participación sectorial 2022-2025pr, que es el "
            "dato que sostiene la lectura de desacople del apartado 4.1.", "B"],
           ["Situación actual y brechas",
            "DANE, Indicadores básicos de TIC en empresas / ENTIC Empresas",
            "Adopción tecnológica empresarial por tamaño y sector, incluido el "
            "uso de IA; es la fuente que permite desagregar la digitalización "
            "productiva más allá del agregado.", "B"],
           ["Situación actual y brechas",
            "MinTIC, ONTIC, sección de indicadores «Transformación digital "
            "productiva»",
            "Fichas por indicador con serie, fuente primaria y periodicidad: "
            "empresas que usaron internet y herramientas tecnológicas, "
            "micronegocios que usaron dispositivos electrónicos, teletrabajo, "
            "personal ocupado que usó internet.", "B"],
           ["Brechas y retos",
            "Contrato DNP-1025-2026, rutinas del Anexo A de la Entrega 3",
            "Método de brecha territorial aplicable a los indicadores de "
            "adopción empresarial, con la misma lógica de concentración y "
            "divergencia usada para conectividad.", "A"]],
          "elaboración propia. Los enlaces de cada fuente están en el capítulo 8.",
          anchos=[2.8, 4.2, 6.6, 1.4])

    titulo(doc, "4.3. Vacío que queda abierto", 2)
    parrafo(doc,
            "El dato que falta y que este tema necesita es el porcentaje de "
            "empresas que usan IA en procesos productivos o de gestión, "
            "desagregado por tamaño y sector. La ENTIC Empresas lo recoge y "
            "ONTIC publica indicadores de la sección de IA construidos sobre "
            "esa fuente, pero no se pudo cotejar el valor exacto ni el año de "
            "referencia más reciente durante la elaboración de esta nota. Es "
            "una consulta de pocos minutos para quien tenga acceso directo al "
            "boletín, y sostiene por sí sola la pregunta de brechas del tema.")


def tema7(doc):
    titulo(doc, "5. Tema 7. Inteligencia artificial y tecnologías emergentes", 1)

    titulo(doc, "5.1. Lectura que se propone", 2)
    parrafo(doc,
            "Este es el tema donde el contrato tiene más para aportar, porque "
            "la evaluación intermedia del CONPES 4144 responde de manera "
            "directa tres de las cinco preguntas de la metodología y lo hace "
            "con información que no es pública.")
    parrafo(doc,
            "El hallazgo más relevante para el PND no es el nivel de avance "
            "sino la estructura del sistema de medición: el Plan de Acción y "
            "Seguimiento del CONPES 4144 contiene 76 indicadores de gestión y "
            "30 de producto, y ninguno de resultado [A]. Una política que no "
            "mide resultados no puede ser evaluada por sus efectos, solo por su "
            "actividad. Si el PND 2026-2030 hereda ese diseño, hereda también "
            "la imposibilidad de saber si la inversión en IA sirvió para algo. "
            "Ese es un mensaje concreto, verificable y accionable dentro del "
            "Plan.")
    parrafo(doc,
            "A ese hallazgo se suman otros tres del mismo análisis [A]: el "
            "avance físico promedio es del 43,3 % con financiación completa, de "
            "modo que el freno no es presupuestal; quince de las dieciocho "
            "acciones que vencían en 2025 cerraron sin cumplimiento total; y la "
            "ejecución descansa en un núcleo de tres entidades que participa en "
            "el 80,2 % de las acciones, mientras la mitad de las 56 entidades "
            "involucradas figura en una sola. La política está bien financiada "
            "y mal distribuida.")
    parrafo(doc,
            "Un cuarto hallazgo es distributivo y conviene que el diagnóstico "
            "lo recoja porque es corregible: las acciones asociadas al enfoque "
            "de derechos y a los grupos poblacionales excluidos figuran entre "
            "las de menor avance [A]. En el mismo sentido apunta el análisis "
            "del registro de formación en IA, donde la brecha de género se "
            "produce en el acceso al programa y no en la permanencia dentro de "
            "él [A], que son dos problemas de política distintos y exigen "
            "respuestas distintas.")
    parrafo(doc,
            "Finalmente, un dato de demanda que ordena el conjunto: según la "
            "ENTIC Hogares 2024, el 18,0 % de las personas de cinco años o más "
            "que usaron internet lo hicieron para utilizar herramientas de IA "
            "[B]. La adopción ciudadana va por delante de la política. Ese "
            "contraste —una quinta parte de los usuarios de internet ya usa IA "
            "mientras la política que debe gobernarla avanza al 43 %— es "
            "probablemente la mejor formulación del problema público para este "
            "tema.")

    titulo(doc, "5.2. Fuentes que alimentan las cinco preguntas", 2)
    tabla(doc, "Fuentes verificables para el tema 7",
          ["Pregunta", "Fuente", "Qué aporta", "Nivel"],
          [["Situación actual y evolución",
            "DNP, CONPES 4144 de 2025 y su Plan de Acción y Seguimiento; "
            "reportes de SisCONPES con corte al 21 de julio de 2026",
            "Estructura de la política, asignación de recursos por objetivo, "
            "avance físico y financiero por acción y distribución "
            "institucional. Base de todo el apartado 5.1.", "A"],
           ["Evolución",
            "Contrato DNP-1025-2026, analítica de texto sobre CONPES 3975 y 4144",
            "Medición del desplazamiento del vocabulario de política entre 2019 "
            "y 2025 en las dimensiones territorial, diferencial y de "
            "habilidades. Responde la pregunta de evolución con evidencia, no "
            "con apreciación.", "A"],
           ["Situación actual",
            "DANE, ENTIC Hogares 2024 (boletín del 1 de agosto de 2025)",
            "Uso de herramientas de IA por parte de la población que usa "
            "internet (18,0 %), con desagregación de la encuesta.", "B"],
           ["Situación actual y brechas",
            "MinTIC, ONTIC, sección de indicadores «Inteligencia Artificial (IA)»",
            "Fichas por indicador con serie y fuente primaria, entre ellas "
            "empresas que desarrollan alguna herramienta o aplicación de IA.", "B"],
           ["Brechas",
            "MinTIC, participantes certificados en IA (SENATIC), conjunto de "
            "datos abiertos m2uu-cu4q",
            "Composición por sexo, grupo poblacional y municipio, y tasa de "
            "certificación sobre inscripción. Permite distinguir brecha de "
            "acceso de brecha de permanencia.", "A"],
           ["Retos 2026-2030",
            "Cepal y Cenia, Índice Latinoamericano de Inteligencia Artificial "
            "(ILIA) 2025, incluidas las fichas de país",
            "Posición comparada de Colombia en el grupo de países «adoptantes» "
            "y desagregación por factores habilitantes, investigación y "
            "gobernanza. Referente regional citado por el propio CONPES 4144.",
            "B"],
           ["Retos 2026-2030",
            "MinTIC, Plan TIC 2026-2030 «Colombia el milagro tecnológico»",
            "Misiones y prioridades declaradas del sector para el período, "
            "necesarias para contrastar el diagnóstico con la agenda anunciada.",
            "B"],
           ["Brechas (evidencia cualitativa)",
            "Contrato DNP-1025-2026, informe de resultados del piloto de Renadia",
            "Barreras declaradas para adoptar datos e IA en el sector público. "
            "Muestra pequeña y autoseleccionada: usar con la advertencia del "
            "apartado 3.4.", "A"]],
          "elaboración propia. Los enlaces de cada fuente están en el capítulo 8.",
          anchos=[2.8, 4.2, 6.6, 1.4])

    titulo(doc, "5.3. Vacío que queda abierto", 2)
    parrafo(doc,
            "El estado de operación del Observatorio Nacional de Inteligencia "
            "Artificial es información que la Dirección tiene y que no se pudo "
            "documentar con fuente publicada. Como el cierre de la estrategia "
            "anticipatoria del CONPES 4144 —vencida y con 38 % de avance [A]— "
            "puede apalancarse precisamente en la consolidación del "
            "Observatorio, conviene que el tema 7 lo trate de manera explícita "
            "y con el estado real de avance.")


def tema9(doc):
    titulo(doc, "6. Tema 9. Gobierno digital, ciudades y territorios inteligentes", 1)

    titulo(doc, "6.1. Lectura que se propone", 2)
    parrafo(doc,
            "Este tema tiene una paradoja documentable con dos fuentes "
            "oficiales y vale la pena construirlo alrededor de ella. Colombia "
            "obtuvo 0,71 en el Índice de Gobierno Digital de la OCDE, por "
            "encima del promedio de la organización (0,70), y pasó del grupo "
            "«alto» al «muy alto» del índice de gobierno electrónico de "
            "Naciones Unidas entre 2022 y 2024 [B]. Al mismo tiempo, el "
            "promedio del Índice de Gobierno Digital de las entidades "
            "territoriales fue de 59,94 en 2025 [B].")
    parrafo(doc,
            "El desempeño internacional de Colombia se explica por el nivel "
            "nacional y oculta la brecha territorial. Un país que está sobre el "
            "promedio de la OCDE tiene mil cien alcaldías que en promedio no "
            "llegan a 60 sobre 100. Esa es, formulada con dos cifras "
            "verificables, la brecha central del tema, y es la que el PND tiene "
            "que atacar.")
    parrafo(doc,
            "Hay dos matices que refuerzan el argumento en lugar de "
            "debilitarlo. El primero es que el puntaje de la OCDE bajó 0,03 "
            "frente a 2023 [B]: el país no está mejorando en la comparación "
            "internacional, se está quedando quieto mientras otros avanzan. El "
            "segundo es que la dimensión más débil de Colombia en ese índice es "
            "la accesibilidad de los datos, con 0,60 frente a un promedio OCDE "
            "de 0,67 [B], justo donde el país es fuerte en las demás "
            "dimensiones de datos (sector público guiado por datos, 0,87 frente "
            "a 0,74). Colombia produce datos y le cuesta ponerlos a disposición: "
            "esa distinción es útil y conecta este tema con el 8.")
    parrafo(doc,
            "Sobre el lado territorial hay un aporte metodológico barato y "
            "concreto: el análisis de brechas de la Entrega 3 distingue "
            "concentración (dónde está la capacidad) de divergencia (hacia "
            "dónde se mueve la brecha), y encontró que en conectividad el país "
            "crece más donde ya había más [A]. Ese mismo instrumento se puede "
            "aplicar tal cual a los puntajes municipales del IGD para "
            "establecer si el gobierno digital territorial está convergiendo o "
            "divergiendo. Requiere el microdato por entidad, que es del MinTIC.")

    titulo(doc, "6.2. Fuentes que alimentan las cinco preguntas", 2)
    tabla(doc, "Fuentes verificables para el tema 9",
          ["Pregunta", "Fuente", "Qué aporta", "Nivel"],
          [["Situación actual y brechas",
            "MinTIC, resultados del Índice de Gobierno Digital 2025",
            "Promedio territorial de 59,94 (+5,11 frente al año anterior); "
            "mejores gobernaciones (Meta 97,80; Bolívar 96,17; Cundinamarca "
            "95,75) y alcaldías (Bogotá 98,29; Bahía Solano 96,41; Cartagena "
            "96,15); avances por elemento de la política.", "B"],
           ["Situación actual y retos",
            "OCDE, Digital Government Outlook 2026, capítulo de Colombia",
            "Puntaje de 0,71 frente a promedio OCDE de 0,70, variación de −0,03 "
            "desde 2023 y desagregación por dimensión, incluida accesibilidad "
            "de datos (0,60 frente a 0,67).", "B"],
           ["Evolución",
            "Naciones Unidas, E-Government Survey 2024",
            "Paso de Colombia del grupo «alto» al «muy alto» del EGDI entre "
            "2022 y 2024, con el índice y sus subíndices por país.", "B"],
           ["Situación actual (ciudades)",
            "MinTIC, Modelo de Medición de Madurez de Ciudades y Territorios "
            "Inteligentes y Resolución 1117 de 2022",
            "Instrumento de autodiagnóstico territorial en seis dimensiones y "
            "los lineamientos que lo hacen exigible. Es el marco normativo del "
            "componente de ciudades del tema.", "B"],
           ["Brechas",
            "Contrato DNP-1025-2026, método de concentración y divergencia de "
            "la Entrega 3",
            "Instrumento aplicable a los puntajes municipales del IGD para "
            "determinar si la brecha territorial de gobierno digital converge o "
            "diverge. Requiere el microdato por entidad.", "A"],
           ["Brechas (evidencia cualitativa)",
            "Contrato DNP-1025-2026, mesa piloto de Renadia sobre tableros en "
            "entidades públicas",
            "Diagnóstico estructurado del ciclo de vida de los tableros de "
            "datos en entidades nacionales y territoriales, un problema sin "
            "medición oficial.", "A"],
           ["Retos 2026-2030",
            "OCDE, Digital Government Index and OURdata Index (documento "
            "metodológico de 2026)",
            "Metodología y comparabilidad de los índices, necesaria para "
            "interpretar correctamente la variación del puntaje.", "B"]],
          "elaboración propia. Los enlaces de cada fuente están en el capítulo 8.",
          anchos=[2.8, 4.2, 6.6, 1.4])

    titulo(doc, "6.3. Vacío que queda abierto", 2)
    parrafo(doc,
            "Falta el microdato del Índice de Gobierno Digital por entidad. Los "
            "resultados publicados dan el promedio y los mejores puntajes, que "
            "sirven para el titular pero no para el análisis de brechas, que es "
            "lo que el tema necesita. Con el archivo por entidad, el análisis "
            "territorial descrito en el apartado 6.1 se produce en pocos días.")
    parrafo(doc,
            "Un segundo punto por resolver es de precisión: los comunicados del "
            "MinTIC sobre el acompañamiento a territorios inteligentes hablan "
            "en un caso de 60 ciudades y en otro de 61. Es menor, pero si la "
            "cifra entra al diagnóstico conviene tomarla del acto "
            "administrativo o del informe de gestión y no del comunicado.")


def tema10(doc):
    titulo(doc, "7. Tema 10. Confianza y seguridad digital", 1)

    titulo(doc, "7.1. Advertencia de trazabilidad que conviene atender primero", 2)
    parrafo(doc,
            "Este es el tema donde el riesgo de trazabilidad descrito en el "
            "capítulo 2 es más agudo, y por eso conviene empezar por ahí. Las "
            "cifras que circulan sobre ciberataques en Colombia —del orden de "
            "decenas de miles de millones de «intentos de afectación» anuales— "
            "provienen habitualmente de telemetría de proveedores privados de "
            "seguridad, no de estadística oficial. Son cifras de exposición "
            "medida por sensores comerciales, no de incidentes verificados, y "
            "su metodología no es pública ni comparable entre años.")
    parrafo(doc,
            "La recomendación es explícita: no incorporar ese tipo de cifra al "
            "diagnóstico, o incorporarla nombrando al proveedor que la produce "
            "y advirtiendo qué mide. En su lugar, el tema debería apoyarse en "
            "las denuncias registradas por la Policía Nacional, que son "
            "estadística oficial con serie, desagregación territorial y "
            "tipificación penal, y en los indicadores de gobernanza de datos y "
            "ciberseguridad que publica ONTIC.")

    titulo(doc, "7.2. Lectura que se propone", 2)
    parrafo(doc,
            "El aporte de este contrato al tema 10 es menos de datos propios y "
            "más de método, y hay una oportunidad concreta. La Política "
            "Nacional de Confianza y Seguridad Digital, el CONPES 3995, fue "
            "aprobada el 1 de julio de 2020 y su horizonte ya venció [B]; hasta "
            "donde alcanza la revisión hecha para esta nota, no existe una "
            "evaluación pública de su ejecución. El mismo instrumento que la "
            "Entrega 3 aplicó al CONPES 4144 —evaluación de diseño sobre el "
            "plan de acción y evaluación de avance sobre los reportes de "
            "SisCONPES— es directamente aplicable al 3995, y produciría para el "
            "PND algo que hoy no existe: el balance de qué quedó cumplido de la "
            "política de seguridad digital anterior antes de formular la "
            "siguiente.")
    parrafo(doc,
            "El segundo aporte conecta este tema con el 7. En el piloto de "
            "Renadia, la falta de claridad para usar IA con ética apareció "
            "entre los principales frenos declarados (19 % de las respuestas) "
            "[A]. La confianza no es solo un asunto de protección frente a "
            "amenazas externas: es también una barrera interna de adopción "
            "dentro del propio Estado. Formular el tema 10 únicamente en clave "
            "de ciberseguridad deja fuera esa mitad del problema, que es "
            "justamente la que el PND puede intervenir con instrumentos "
            "propios.")

    titulo(doc, "7.3. Fuentes que alimentan las cinco preguntas", 2)
    tabla(doc, "Fuentes verificables para el tema 10",
          ["Pregunta", "Fuente", "Qué aporta", "Nivel"],
          [["Situación actual y retos",
            "MinTIC, Estrategia Nacional de Seguridad Digital de Colombia "
            "2025-2027",
            "Ejes de la estrategia vigente, diagnóstico institucional y "
            "creación del centro de operaciones de seguridad. Es el instrumento "
            "de política que el diagnóstico tiene que describir.", "B"],
           ["Evolución",
            "DNP, CONPES 3995 de 2020, Política Nacional de Confianza y "
            "Seguridad Digital",
            "Política anterior, con su diagnóstico y su plan de acción; base "
            "para la pregunta de evolución y para la evaluación propuesta en el "
            "apartado 7.2.", "B"],
           ["Evolución",
            "DNP, CONPES 3854 de 2016, Política Nacional de Seguridad Digital",
            "Primer instrumento de la serie; completa la trayectoria de tres "
            "documentos que permite responder qué cambió entre gobiernos.", "B"],
           ["Situación actual y brechas",
            "Policía Nacional, Dirección de Investigación Criminal e Interpol, "
            "y Centro Cibernético Policial",
            "Denuncias por delitos informáticos con tipificación penal, serie y "
            "desagregación territorial. Es la estadística oficial que debe "
            "reemplazar las cifras de telemetría privada.", "B"],
           ["Situación actual",
            "MinTIC, ONTIC, sección de indicadores de gobernanza de datos y "
            "ciberseguridad",
            "Fichas por indicador con fuente primaria y periodicidad, "
            "consistentes con el resto del diagnóstico.", "B"],
           ["Retos 2026-2030",
            "UIT, Global Cybersecurity Index 2024 (quinta edición)",
            "Posición comparada de Colombia en los cinco pilares de "
            "ciberseguridad. Tomar el puntaje y el nivel del informe de la UIT, "
            "no de las notas de prensa que lo resumen.", "B"],
           ["Evaluación (propuesta)",
            "Contrato DNP-1025-2026, modelos de evaluación de diseño e "
            "intermedia de la Entrega 3",
            "Instrumento aplicable al CONPES 3995 para producir el balance de "
            "cierre de la política anterior. Requiere el plan de acción y los "
            "reportes de SisCONPES del 3995.", "A"],
           ["Brechas (evidencia cualitativa)",
            "Contrato DNP-1025-2026, informe de resultados del piloto de Renadia",
            "La falta de claridad ética para usar IA como barrera interna de "
            "adopción. Muestra pequeña y autoseleccionada: usar con la "
            "advertencia del apartado 3.4.", "A"]],
          "elaboración propia. Los enlaces de cada fuente están en el capítulo 8.",
          anchos=[2.8, 4.2, 6.6, 1.4])

    titulo(doc, "7.4. Vacío que queda abierto", 2)
    parrafo(doc,
            "Las cifras de denuncias por delitos informáticos que circulan en "
            "prensa —del orden de sesenta mil denuncias anuales y una "
            "concentración cercana al 88 % en hurto por medios informáticos, "
            "acceso abusivo a sistema informático y violación de datos "
            "personales— son verosímiles y coherentes entre sí, pero se "
            "clasifican en nivel C mientras no se identifique el boletín del "
            "Centro Cibernético Policial o el conjunto de datos abiertos que "
            "las produce. Localizar esa fuente primaria es la tarea más "
            "rentable de este tema: convierte de una sola vez el núcleo "
            "empírico del capítulo en material citable.")


def registro(doc):
    titulo(doc, "8. Registro de fuentes con enlace", 1)
    parrafo(doc,
            "Las fuentes se listan con la dirección de consulta verificada el 7 "
            "de septiembre de 2026. Las de nivel B exigen abrir el documento y "
            "confirmar el dato exacto antes de citarlo, según el protocolo del "
            "capítulo 2.")
    parrafo(doc,
            "El inventario vive en el archivo fuentes.py que acompaña a esta "
            "nota, de modo que la tabla siguiente y la rutina de verificación de "
            "disponibilidad leen exactamente el mismo listado y no pueden "
            "desincronizarse.")
    filas = [[f["fuente"], f["url"],
              ", ".join(str(t) for t in f["temas"]), f["nivel"]]
             for f in FUENTES]
    tabla(doc, "Registro de fuentes externas empleadas en esta nota",
          ["Fuente", "Enlace", "Temas", "Nivel"], filas,
          "elaboración propia. Los enlaces corresponden a la publicación primaria "
          "de cada dato citado en los capítulos 4 a 7.",
          anchos=[5.2, 7.4, 1.6, 1.4], tam=8)


def cierre(doc):
    titulo(doc, "9. Qué se necesita de la Dirección para cerrar los vacíos", 1)
    parrafo(doc,
            "Los aportes descritos en esta nota están disponibles de inmediato, "
            "con dos excepciones que dependen de información que la Dirección "
            "puede gestionar y que se listan aquí en orden de rentabilidad.")
    vineta(doc,
           "Microdato del Índice de Gobierno Digital 2025 por entidad "
           "territorial. Habilita el análisis de convergencia o divergencia del "
           "gobierno digital territorial descrito en el apartado 6.1, que es el "
           "aporte más sustantivo disponible para el tema 9 y no existe hoy en "
           "ninguna publicación.")
    vineta(doc,
           "Plan de acción y reportes de seguimiento del CONPES 3995. "
           "Permiten aplicar al balance de la política de confianza y seguridad "
           "digital el mismo instrumento ya validado sobre el CONPES 4144, y "
           "producir para el tema 10 la evaluación de cierre que hoy no "
           "existe.")
    parrafo(doc,
            "Adicionalmente, hay tres consultas menores que cualquiera del "
            "equipo puede resolver en poco tiempo y que elevan de nivel B a "
            "nivel A varias cifras de esta nota: el porcentaje de empresas que "
            "usan IA en la ENTIC Empresas más reciente (tema 6), el puntaje y "
            "el nivel exactos de Colombia en el Global Cybersecurity Index 2024 "
            "leídos del informe de la UIT (tema 10), y el boletín del Centro "
            "Cibernético Policial que produce la serie de denuncias por delitos "
            "informáticos (tema 10).")
    parrafo(doc,
            "Por último, una observación sobre el borrador. El capítulo de "
            "valor económico del sector reporta una participación de 3,47 % "
            "para 2025pr sin la serie que la precede. Como esa serie viene "
            "descendiendo desde 3,6 % en 2023p, presentar el dato aislado puede "
            "sugerir una expansión que la fuente no respalda. Añadir los dos "
            "años anteriores es un cambio de una línea y evita una lectura "
            "equivocada en un punto que después es difícil de corregir.")


def anexo(doc):
    titulo(doc, "Anexo A. Declaración de uso de herramientas de inteligencia artificial", 1)
    parrafo(doc,
            "En la elaboración de esta nota se emplearon herramientas de "
            "inteligencia artificial para tres tareas: la búsqueda y "
            "localización de publicaciones oficiales pertinentes a cada tema, "
            "la organización del material previamente producido por el contrato "
            "y la redacción de los borradores de texto. El criterio analítico, "
            "la selección de fuentes, la clasificación de niveles de "
            "verificación y las lecturas propuestas son responsabilidad de "
            "quien elabora la nota.")
    parrafo(doc,
            "Se deja constancia de una limitación concreta del proceso, porque "
            "condiciona el uso del documento. Las cifras marcadas con nivel B "
            "fueron localizadas en la publicación oficial correspondiente y su "
            "enlace está registrado en el capítulo 8, pero no se abrió cada "
            "documento página a página para cotejarlas durante la elaboración "
            "de esta nota. Por eso el protocolo del capítulo 2 exige esa "
            "confirmación antes de que cualquiera de ellas entre al diagnóstico. "
            "Las cifras de nivel A provienen de rutinas propias sobre la fuente "
            "primaria y son reproducibles con el código anexado a las entregas "
            "2 y 3 del contrato.")
    parrafo(doc,
            "Esta declaración sigue la práctica ya adoptada en las entregas "
            "anteriores y responde al criterio de uso ético y transparente que "
            "fijó la coordinación del diagnóstico.")


# --------------------------------------------------------------------------

def construir(salida):
    doc = Document()
    configurar_estilos(doc)
    margenes(doc.sections[0])
    portada(doc,
            "Fuentes verificables y aportes disponibles para los temas 6, 7, 9 y 10",
            "Nota técnica de insumos para el diagnóstico del sector TIC "
            "(PND 2026-2030)",
            "Versión 1")
    doc.add_section(WD_SECTION.NEW_PAGE)
    seccion = doc.sections[-1]
    margenes(seccion)
    encabezado_paginado(seccion)

    pagina_legal(doc)
    salto(doc)
    siglas(doc)
    salto(doc)
    presentacion(doc)
    alcance(doc)
    protocolo(doc)
    salto(doc)
    productos(doc)
    salto(doc)
    tema6(doc)
    salto(doc)
    tema7(doc)
    salto(doc)
    tema9(doc)
    salto(doc)
    tema10(doc)
    salto(doc)
    registro(doc)
    salto(doc)
    cierre(doc)
    salto(doc)
    anexo(doc)

    doc.core_properties.title = ("Fuentes verificables y aportes para los temas 6, 7, 9 y 10 "
                                "del diagnóstico del sector TIC")
    doc.core_properties.subject = "Contrato DNP-1025-2026"
    doc.save(salida)
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=SALIDA_DEFECTO)
    ap.add_argument("--pdf", action="store_true",
                    help="convierte la salida a PDF para revisión visual")
    args = ap.parse_args()

    ruta = construir(args.salida)
    print(ruta)

    if args.pdf:
        if not SOFFICE:
            print("aviso: no se encontró LibreOffice; se omite el PDF")
            return 0
        subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                        "--outdir", os.path.dirname(ruta), ruta],
                       check=True, capture_output=True)
        print(ruta.replace(".docx", ".pdf"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
