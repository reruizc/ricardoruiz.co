#!/usr/bin/env python3
"""
Inventario de fuentes del aporte al diagnóstico del sector TIC (PND 2026-2030),
temas 6, 7, 9 y 10.

Es la única fuente de verdad de las referencias: `build_nota_temas.py` arma con
esto el registro del capítulo 8 y `verificar_fuentes.py` vuelve a pedir cada URL
para dejar constancia de que estaba publicada.

Campos de cada entrada:

    sigla   identificador corto, el que se usa al citar en el cuerpo del texto
    fuente  entidad y título de la publicación, como va en el registro
    url     dirección de la publicación primaria del dato
    temas   temas del diagnóstico a los que alimenta
    nivel   nivel de verificación según el protocolo del capítulo 2 de la nota:
            "A" cifra reproducida por el contrato desde la fuente primaria, con
                rutina documentada y ejecutable;
            "B" cifra publicada por entidad oficial u organismo multilateral,
                con documento y enlace identificados, sin cotejo página a
                página; exige confirmar el dato antes de citarlo;
            "C" cifra de prensa o de resúmenes de terceros sin publicación
                primaria identificada; no citable.

Ninguna entrada de nivel C se registra aquí: por definición no es citable, y lo
que corresponde con ella es buscar la fuente primaria, no inventariarla.
"""

FUENTES = [
    # -- Tema 6. Economía digital y transformación productiva ---------------
    {"sigla": "DANE-CSTIC-2024",
     "fuente": "DANE. Cuenta Satélite TIC 2024pr, boletín técnico",
     "url": "https://www.dane.gov.co/files/operaciones/CSTIC/bol-CSTIC-2024pr.pdf",
     "temas": [6], "nivel": "B"},
    {"sigla": "DANE-CSTIC",
     "fuente": "DANE. Cuenta Satélite TIC, página de la operación estadística",
     "url": "https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales"
            "/cuentas-satelite/cuenta-satelite-de-las-tecnologias-de-la-informacion-y-"
            "las-comunicaciones-cstic",
     "temas": [6], "nivel": "B"},
    {"sigla": "DANE-TIC-EMP",
     "fuente": "DANE. Indicadores básicos de TIC en empresas",
     "url": "https://www.dane.gov.co/index.php/estadisticas-por-tema/tecnologia-e-"
            "innovacion/tecnologias-de-la-informacion-y-las-comunicaciones-tic/"
            "indicadores-basicos-de-tic-en-empresas",
     "temas": [6, 7], "nivel": "B"},
    {"sigla": "CCCE-2025",
     "fuente": "CCCE. Informe de cierre eCommerce 2025, versión pública",
     "url": "https://ccce.org.co/noticias/informe-de-cierre-ecommerce-2025-version-publica/",
     "temas": [6], "nivel": "B"},
    {"sigla": "ONTIC-TDP",
     "fuente": "MinTIC, ONTIC. Indicadores de transformación digital productiva",
     "url": "https://ontic.mintic.gov.co/portal/Secciones/Indicadores/"
            "Transformacion-digital-productiva/383060:Empresas-que-usaron-Internet-y-"
            "herramientas-tecnologicas",
     "temas": [6], "nivel": "B"},

    # -- Tema 7. IA y tecnologías emergentes --------------------------------
    {"sigla": "CONPES-4144",
     "fuente": "DNP. CONPES 4144 de 2025, Política Nacional de Inteligencia Artificial",
     "url": "https://colaboracion.dnp.gov.co/CDT/Conpes/Económicos/4144.pdf",
     "temas": [7], "nivel": "A"},
    {"sigla": "DANE-ENTIC-HOG",
     "fuente": "DANE. ENTIC Hogares 2024, boletín técnico",
     "url": "https://www.dane.gov.co/files/operaciones/ENTIC/bol-ENTICHogares-2024.pdf",
     "temas": [7], "nivel": "B"},
    {"sigla": "ONTIC-IA",
     "fuente": "MinTIC, ONTIC. Indicadores de Inteligencia Artificial (IA)",
     "url": "https://ontic.mintic.gov.co/portal/Secciones/Indicadores/"
            "Inteligencia-Artificial-IA/",
     "temas": [7], "nivel": "B"},
    {"sigla": "ILIA-2025",
     "fuente": "Cepal y Cenia. ILIA 2025, publicación principal",
     "url": "https://repositorio.cepal.org/handle/11362/82514",
     "temas": [7], "nivel": "B"},
    {"sigla": "ILIA-2025-FICHAS",
     "fuente": "Cepal y Cenia. ILIA 2025, fichas de país y aspectos metodológicos",
     "url": "https://www.cepal.org/es/publicaciones/86020-indice-latinoamericano-"
            "inteligencia-artificial-ilia-2025-fichas-pais-aspectos",
     "temas": [7], "nivel": "B"},
    {"sigla": "SENATIC",
     "fuente": "MinTIC. Participantes certificados en IA, SENATIC (m2uu-cu4q), "
               "Portal de Datos Abiertos",
     "url": "https://www.datos.gov.co/resource/m2uu-cu4q.json",
     "temas": [7], "nivel": "A"},

    # -- Tema 9. Gobierno digital, ciudades y territorios inteligentes ------
    {"sigla": "IGD-2025",
     "fuente": "MinTIC. Resultados del Índice de Gobierno Digital 2025",
     "url": "https://www.mintic.gov.co/portal/inicio/Sala-de-prensa/Noticias/440318:"
            "Entidades-publicas-fortalecieron-su-transformacion-digital-MinTIC-presenta-"
            "resultados-del-Indice-de-Gobierno-Digital-2025",
     "temas": [9], "nivel": "B"},
    {"sigla": "MINTIC-MEDICIONES",
     "fuente": "MinTIC. Mediciones de la Política de Gobierno Digital",
     "url": "https://gobiernodigital.mintic.gov.co/portal/Mediciones/",
     "temas": [9], "nivel": "B"},
    {"sigla": "MINTIC-CTI",
     "fuente": "MinTIC. Modelo de medición de madurez de ciudades y territorios "
               "inteligentes",
     "url": "https://gobiernodigital.mintic.gov.co/692/articles-179100_recurso_3.pdf",
     "temas": [9], "nivel": "B"},
    {"sigla": "OCDE-DGO-CO",
     "fuente": "OCDE. Digital Government Outlook 2026, capítulo de Colombia",
     "url": "https://www.oecd.org/en/publications/digital-government-outlook-2026_"
            "d46c0555-en/colombia_cc2c0193-en.html",
     "temas": [9], "nivel": "B"},
    {"sigla": "OCDE-DGI-MET",
     "fuente": "OCDE. Digital Government Index and OURdata Index, documento metodológico",
     "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2026/02/"
            "digital-government-index-and-open-useful-and-re-usable-data-index_dbe102ed/"
            "6347ec74-en.pdf",
     "temas": [9], "nivel": "B"},
    {"sigla": "ONU-EGOV-2024",
     "fuente": "Naciones Unidas. E-Government Survey 2024",
     "url": "https://publicadministration.un.org/egovkb/en-us/Reports/"
            "UN-E-Government-Survey-2024",
     "temas": [9], "nivel": "B"},
    {"sigla": "MINTIC-N48W",
     "fuente": "MinTIC. Internet fijo, accesos por tecnología y segmento (n48w-gutb), "
               "Portal de Datos Abiertos",
     "url": "https://www.datos.gov.co/resource/n48w-gutb.json",
     "temas": [6, 9], "nivel": "A"},

    # -- Tema 10. Confianza y seguridad digital -----------------------------
    {"sigla": "ENSD-2025",
     "fuente": "MinTIC. Estrategia Nacional de Seguridad Digital de Colombia 2025-2027",
     "url": "https://www.mintic.gov.co/portal/715/articles-403023_recurso_2.pdf",
     "temas": [10], "nivel": "B"},
    {"sigla": "CONPES-3995",
     "fuente": "DNP. CONPES 3995 de 2020, Política Nacional de Confianza y "
               "Seguridad Digital",
     "url": "https://colaboracion.dnp.gov.co/cdt/Conpes/Econ%C3%B3micos/3995.pdf",
     "temas": [10], "nivel": "B"},
    # La ruta directa del 3854 en el repositorio del DNP no se pudo confirmar en la
    # fecha de corte; se registra la copia publicada por Función Pública, que sí
    # responde. Si se cita, conviene sustituirla por la del DNP cuando se ubique.
    {"sigla": "CONPES-3854",
     "fuente": "DNP. CONPES 3854 de 2016, Política Nacional de Seguridad Digital "
               "(copia publicada por Función Pública)",
     "url": "https://www1.funcionpublica.gov.co/documents/34645357/34703567/"
            "Conpes_3854_de_2016.pdf",
     "temas": [10], "nivel": "B"},
    {"sigla": "UIT-GCI-2024",
     "fuente": "UIT. Global Cybersecurity Index 2024",
     "url": "https://www.itu.int/en/ITU-D/Cybersecurity/Documents/GCIv5/"
            "2401416_1b_Global-Cybersecurity-Index-E.pdf",
     "temas": [10], "nivel": "B"},
]


def por_tema(tema):
    return [f for f in FUENTES if tema in f["temas"]]
