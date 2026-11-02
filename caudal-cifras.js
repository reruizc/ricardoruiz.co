/* Generado por tools/caudal/build_cifras_portada.py — NO editar a mano: cada cifra
   sale de la API de Caudal y del catálogo de entidades. Volver a correrlo antes de
   presentar Caudal. */
window.CAUDAL_CIFRAS = {
 "corte": "2026-11-02",
 "corte_txt": "2 de noviembre de 2026",
 "hero": {
  "congreso": "15.450",
  "congreso_l": "registros del Congreso · 1991–2026",
  "actos": "81.735",
  "actos_l": "actos regulatorios · 17 fuentes",
  "entidades": 36,
  "entidades_l": "entidades del Estado leídas en su fuente · 10 en parte"
 },
 "entidades": {
  "conectada": 26,
  "parcial": 10,
  "sin_fuente": 1,
  "no_aplica": 0
 },
 "pilares": {
  "congreso": {
   "n": "15.450",
   "unit": "registros · 1991–2026",
   "desc": "14.345 proyectos de ley y 1.105 actos legislativos desde 1991, con su trámite, sus ponentes y el voto nominal de cada congresista. Cuántas veces se intentó, por qué se cae, quién lo empuja.",
   "fuentes": [
    {
     "n": "Senado · registro de proyectos",
     "e": "conectada",
     "l": "Todos los proyectos de ley y actos legislativos desde 1991, con su estado"
    },
    {
     "n": "Cámara · fichas de proyectos",
     "e": "conectada",
     "l": "Fecha de radicación, ponentes y trámite de cada proyecto"
    },
    {
     "n": "Votaciones nominales",
     "e": "conectada",
     "l": "API del Senado y actas de plenaria de la Cámara: cómo votó cada congresista"
    },
    {
     "n": "Órdenes del día",
     "e": "conectada",
     "l": "Comisiones y plenarias de las dos cámaras, leídas dos veces al día"
    }
   ]
  },
  "regulatorio": {
   "n": "81.735",
   "unit": "actos · 17 fuentes",
   "desc": "Resoluciones, circulares, conceptos y sanciones de las superintendencias y los reguladores —7.333 de ellos sanciones—, más lo que cada superintendencia publica en su propio sitio. Cada acto cita su resolución o comunicado.",
   "fuentes": [
    {
     "n": "Supersubsidio",
     "e": "conectada",
     "l": "Borradores propios · Circulares · Resoluciones"
    },
    {
     "n": "Supersalud",
     "e": "conectada",
     "l": "Sanciones · Registro de actos · Comunicados de intervención"
    },
    {
     "n": "SIC",
     "e": "conectada",
     "l": "Sanciones · Circulares · Resoluciones de carácter general"
    },
    {
     "n": "Supersociedades",
     "e": "conectada",
     "l": "Sanciones · Normas · Conceptos jurídicos (Tesauro, 13.002)"
    },
    {
     "n": "Superfinanciera",
     "e": "parcial",
     "l": "Sanciones del mercado de valores · Proyectos de norma y documentos técnicos · Circulares externas. Falta: conceptos"
    },
    {
     "n": "Supervigilancia",
     "e": "conectada",
     "l": "Resoluciones · Circulares · Proyectos propios"
    },
    {
     "n": "Supertransporte",
     "e": "parcial",
     "l": "Sanciones. Falta: circulares"
    },
    {
     "n": "UGPP",
     "e": "conectada",
     "l": "Resoluciones, circulares y acuerdos de su sitio · Proyectos de resolución · Noticias"
    },
    {
     "n": "DIAN",
     "e": "conectada",
     "l": "Resoluciones y circulares · Conceptos y oficios (doctrina)"
    },
    {
     "n": "UIAF",
     "e": "parcial",
     "l": "Obligaciones de reporte ALA/CFT. Falta: revisión pendiente de lo demás que publica"
    },
    {
     "n": "Banco de la República",
     "e": "parcial",
     "l": "Junta Directiva y régimen cambiario. Falta: revisión pendiente de lo demás que publica"
    },
    {
     "n": "ANLA",
     "e": "conectada",
     "l": "Gaceta Ambiental: licencias, sanciones y archivos"
    },
    {
     "n": "INVIMA",
     "e": "conectada",
     "l": "Sanciones sanitarias por sector"
    },
    {
     "n": "SECOP I y II",
     "e": "conectada",
     "l": "Multas y sanciones contractuales impuestas por cada entidad"
    },
    {
     "n": "Junta Central de Contadores",
     "e": "conectada",
     "l": "Sanciones disciplinarias"
    }
   ]
  },
  "medios": {
   "n": "+1.800",
   "unit": "medios rastreables · en vivo",
   "desc": "No es un listado de titulares: mide a qué ritmo crece la cobertura de un tema, quién la sostiene, en qué departamentos no se cubre — y lo contrasta con lo que el Estado está tramitando en ese mismo momento. Cualquier medio indexado en Google News Colombia (más de 1.800 observados hasta hoy), sin un conector por medio.",
   "fuentes": [
    {
     "n": "Google News Colombia",
     "e": "conectada",
     "l": "Prensa nacional y regional por tema, con medio, alcance y departamento"
    },
    {
     "n": "Salas de prensa oficiales",
     "e": "conectada",
     "l": "Comunicados de ministerios, superintendencias y Presidencia, leídos en su sitio"
    }
   ]
  },
  "datos": {
   "n": "5,68 M",
   "unit": "contratos · SECOP II",
   "desc": "Todos los contratos electrónicos del Estado y los procesos que los preceden, consultados en vivo y actualizados a diario, más la doctrina de Colombia Compra Eficiente. Cada uno enlaza su expediente en SECOP.",
   "fuentes": [
    {
     "n": "SECOP II · contratos",
     "e": "conectada",
     "l": "5.678.121 contratos electrónicos, con entidad, valor y modalidad"
    },
    {
     "n": "SECOP II · procesos",
     "e": "conectada",
     "l": "Licitaciones y procesos abiertos antes de adjudicarse"
    },
    {
     "n": "Colombia Compra Eficiente",
     "e": "conectada",
     "l": "Conceptos de su relatoría, circulares y convocatorias de participación"
    }
   ]
  },
  "control": {
   "n": "10.861",
   "unit": "providencias · Corte Constitucional desde 2021",
   "desc": "Sentencias y autos de la Corte Constitucional que cambian la lectura de la norma en contratación, salud, pensiones, ambiente y elecciones, más los fallos de responsabilidad fiscal de la Contraloría. Consejo de Estado y Corte Suprema entran en el siguiente corte.",
   "fuentes": [
    {
     "n": "Corte Constitucional",
     "e": "conectada",
     "l": "Sentencias y autos, con su enlace oficial"
    },
    {
     "n": "Contraloría",
     "e": "parcial",
     "l": "Fallos con responsabilidad fiscal (panel de sanciones). Falta: comunicados"
    },
    {
     "n": "Consejo de Estado",
     "e": "sin_fuente",
     "l": "Falta: sentencias y conceptos de la Sala de Consulta"
    },
    {
     "n": "Corte Suprema de Justicia",
     "e": "sin_fuente",
     "l": "Sin conectar todavía"
    },
    {
     "n": "Procuraduría",
     "e": "sin_fuente",
     "l": "Sin conectar todavía"
    }
   ]
  },
  "ejecutivo": {
   "n": "12.124",
   "unit": "normas de Presidencia · desde 2016",
   "desc": "Decretos —10.626—, leyes, directivas y circulares de la Presidencia, más las resoluciones, conceptos y borradores que publican en su propio sitio los ministerios y departamentos (9.833 normas más) y sus agendas regulatorias 2027. Cada norma enlaza su texto oficial.",
   "fuentes": [
    {
     "n": "Presidencia",
     "e": "parcial",
     "l": "Decretos, leyes y directivas del Diario Oficial y de datos.gov.co. Falta: listado oficial de normativa de su sitio"
    },
    {
     "n": "MinTrabajo",
     "e": "conectada",
     "l": "Resoluciones · Circulares · Conceptos institucionales"
    },
    {
     "n": "MinVivienda",
     "e": "conectada",
     "l": "Resoluciones y circulares · Conceptos jurídicos · Prensa"
    },
    {
     "n": "MinSalud",
     "e": "conectada",
     "l": "Borradores propios (con historial: borra los cerrados) · Análisis de impacto normativo · Normograma"
    },
    {
     "n": "MinEducación",
     "e": "conectada",
     "l": "Resoluciones, circulares y directivas · Comunicados · Agenda regulatoria (vía SUCOP)"
    },
    {
     "n": "MinCulturas",
     "e": "conectada",
     "l": "Noticias · Avisos de convocatorias"
    },
    {
     "n": "MinComercio",
     "e": "conectada",
     "l": "Borradores propios (no publica en SUCOP desde 2025) · Calendario de eventos"
    },
    {
     "n": "MinAgricultura",
     "e": "conectada",
     "l": "Resoluciones · Noticias · Decretos que no están en Presidencia"
    },
    {
     "n": "MinAmbiente",
     "e": "conectada",
     "l": "Borradores propios (no publica en SUCOP desde 2025) · Resoluciones y circulares · Decretos que no están en Presidencia"
    },
    {
     "n": "MinDeporte",
     "e": "conectada",
     "l": "Borradores propios (no publica en SUCOP desde 2025) · Resoluciones · Convocatorias"
    },
    {
     "n": "MinHacienda",
     "e": "parcial",
     "l": "Aviso de borradores propios, con título deducido de su dirección web. Falta: texto de sus borradores"
    },
    {
     "n": "MinInterior",
     "e": "parcial",
     "l": "Falta: proyectos y circulares de su sitio"
    },
    {
     "n": "MinTransporte",
     "e": "parcial",
     "l": "Falta: resoluciones y circulares de su sitio"
    },
    {
     "n": "DNP",
     "e": "conectada",
     "l": "Circulares y resoluciones · Proyectos propios que no están en SUCOP"
    },
    {
     "n": "Función Pública",
     "e": "conectada",
     "l": "Proyectos propios · Conceptos del Gestor Normativo · Circulares y resoluciones"
    },
    {
     "n": "SENA",
     "e": "conectada",
     "l": "Proyectos propios · Resoluciones, acuerdos y circulares del normograma"
    },
    {
     "n": "Servicio Público de Empleo",
     "e": "conectada",
     "l": "Resoluciones y circulares · Noticias"
    },
    {
     "n": "Agendas regulatorias 2027",
     "e": "conectada",
     "l": "802 normas anunciadas por [{'k': 'funcionpublica', 'entidad': 'Departamento Administrativo de la Función Pública', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sitio', 'url': 'https://www1.funcionpublica.gov.co/agenda-regulatoria', 'n_normas': 2, 'nota': '«Pre Agenda Regulatoria» en su página; no está en SUCOP.', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'presidencia', 'entidad': 'Departamento Administrativo de la Presidencia de la República', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/presidencia/Agenda?IDAgenda=34653', 'n_normas': 5, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'dnp', 'entidad': 'Departamento Nacional de Planeación', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/DNP/Agenda?IDAgenda=34940', 'n_normas': 33, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'minagricultura', 'entidad': 'Ministerio de Agricultura y Desarrollo Rural', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minagricultura/Agenda?IDAgenda=34936', 'n_normas': 5, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'minambiente', 'entidad': 'Ministerio de Ambiente y Desarrollo Sostenible', 'obligada': True, 'estado': 'no_publicada', 'leida': True, 'publicada': False, 'via': 'sitio', 'url': 'https://www.minambiente.gov.co/normativa/agenda-regulatoria/', 'n_normas': 0, 'nota': 'Ni su página de agenda ni su sitemap de consultas traen 2027. La última es la V4 de 2026.', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'mincomercio', 'entidad': 'Ministerio de Comercio, Industria y Turismo', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sitio', 'url': 'https://www.mincit.gov.co/normatividad/agenda-regulatoria/agenda-regulatoria-2027', 'n_normas': 43, 'nota': 'En su página; no está en SUCOP.', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'mineducacion', 'entidad': 'Ministerio de Educación Nacional', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mineducacion/Agenda?IDAgenda=33521', 'n_normas': 34, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'minhacienda', 'entidad': 'Ministerio de Hacienda y Crédito Público', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minhacienda/Agenda?IDAgenda=34171', 'n_normas': 40, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-12-01'}, {'k': 'mincultura', 'entidad': 'Ministerio de las Culturas, las Artes y los Saberes', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mincultura/Agenda?IDAgenda=34117', 'n_normas': 20, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'minsalud', 'entidad': 'Ministerio de Salud y Protección Social', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sitio', 'url': 'https://www.minsalud.gov.co/Normativa/Paginas/agenda-regulatoria.aspx', 'n_normas': 145, 'nota': '«Proyecto de Agenda Regulatoria 2027» en su página.', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'minvivienda', 'entidad': 'Ministerio de Vivienda, Ciudad y Territorio', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minvivienda/Agenda?IDAgenda=34374', 'n_normas': 33, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-29', 'consulta_fin': '2026-11-30'}, {'k': 'mindeporte', 'entidad': 'Ministerio del Deporte', 'obligada': True, 'estado': 'no_publicada', 'leida': True, 'publicada': False, 'via': 'sitio', 'url': 'https://www.mindeporte.gov.co/transparencia-y-acceso-a-informacion-publica/2-normativa/2-1-normatividad/agenda-regulatoria', 'n_normas': 0, 'nota': 'Su página 2027 da 404 y su sitemap no la trae. Su página de agenda llega hasta 2026.', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'mintrabajo', 'entidad': 'Ministerio del Trabajo', 'obligada': True, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mintrabajo/Agenda?IDAgenda=35326', 'n_normas': 41, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-31', 'consulta_fin': '2026-11-30'}, {'k': 'alcaldiaenvigado', 'entidad': 'Alcaldía de Envigado', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/alcaldiaenvigado/Agenda?IDAgenda=34681', 'n_normas': 28, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'alcaldiaibague', 'entidad': 'Alcaldía de Ibagué', 'obligada': False, 'estado': 'en_formulacion', 'leida': True, 'publicada': False, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/alcaldiaibague/Agenda?IDAgenda=33145', 'n_normas': 0, 'nota': '', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'alcaldiamadrid', 'entidad': 'Alcaldía de Madrid', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/alcaldiamadrid/Agenda?IDAgenda=34320', 'n_normas': 9, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'alcaldianeiva', 'entidad': 'Alcaldía de Neiva', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/alcaldianeiva/Agenda?IDAgenda=34355', 'n_normas': 9, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-28', 'consulta_fin': '2026-11-30'}, {'k': 'alcaldiapitalito', 'entidad': 'Alcaldía de Pitalito', 'obligada': False, 'estado': 'en_formulacion', 'leida': True, 'publicada': False, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/alcaldiapitalito/Agenda?IDAgenda=27172', 'n_normas': 0, 'nota': '', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'yopal', 'entidad': 'Alcaldía de Yopal', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/yopal/Agenda?IDAgenda=28216', 'n_normas': 20, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'prosperidadsocial', 'entidad': 'Departamento Administrativo para la Prosperidad Social', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/prosperidadsocial/Agenda?IDAgenda=33981', 'n_normas': 29, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'ica', 'entidad': 'Instituto Colombiano Agropecuario', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/ica/Agenda?IDAgenda=34061', 'n_normas': 41, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-21', 'consulta_fin': '2026-11-23'}, {'k': 'icbf', 'entidad': 'Instituto Colombiano De Bienestar Familiar - ICBF', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/icbf/Agenda?IDAgenda=34253', 'n_normas': 4, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-28', 'consulta_fin': '2026-11-27'}, {'k': 'minciencias', 'entidad': 'Ministerio De Innovación, Ciencia Y Tecnología', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minciencias/Agenda?IDAgenda=34604', 'n_normas': 8, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'minjusticia', 'entidad': 'Ministerio de Justicia y del Derecho', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minjusticia/Agenda?IDAgenda=34488', 'n_normas': 5, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-29', 'consulta_fin': '2026-11-29'}, {'k': 'minenergia', 'entidad': 'Ministerio de Minas y Energía', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/minenergia/Agenda?IDAgenda=34118', 'n_normas': 67, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'cancilleria', 'entidad': 'Ministerio de Relaciones Exteriores', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/cancilleria/Agenda?IDAgenda=34699', 'n_normas': 34, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'mintic', 'entidad': 'Ministerio de Tecnologías de la Información y Las Comunicaciones', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mintic/Agenda?IDAgenda=34475', 'n_normas': 27, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-31', 'consulta_fin': '2026-11-30'}, {'k': 'mintransporte', 'entidad': 'Ministerio de Transporte', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mintransporte/Agenda?IDAgenda=34145', 'n_normas': 73, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'mininterior', 'entidad': 'Ministerio del Interior', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/mininterior/Agenda?IDAgenda=34647', 'n_normas': 19, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}, {'k': 'sena', 'entidad': 'Servicio Nacional de Aprendizaje - SENA', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/sena/Agenda?IDAgenda=34646', 'n_normas': 14, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-25'}, {'k': 'sic', 'entidad': 'Superintendencia de Industria y Comercio', 'obligada': False, 'estado': 'en_formulacion', 'leida': True, 'publicada': False, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/sic/Agenda?IDAgenda=34642', 'n_normas': 1, 'nota': '', 'consulta_inicio': '', 'consulta_fin': ''}, {'k': 'supertransporte', 'entidad': 'Superintendencia de Puertos y Transporte', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/supertransporte/Agenda?IDAgenda=33839', 'n_normas': 6, 'nota': '2 PDF en SUCOP', 'consulta_inicio': '2026-10-27', 'consulta_fin': '2026-11-10'}, {'k': 'aerocivil', 'entidad': 'Unidad Administrativa Especial de Aeronáutica Civil', 'obligada': False, 'estado': 'publicada', 'leida': True, 'publicada': True, 'via': 'sucop', 'url': 'https://www.sucop.gov.co/entidades/aerocivil/Agenda?IDAgenda=34560', 'n_normas': 7, 'nota': '1 PDF en SUCOP', 'consulta_inicio': '2026-10-30', 'consulta_fin': '2026-11-30'}] entidades, con sus cambios día a día"
    }
   ]
  },
  "sucop": {
   "n": "4.505",
   "unit": "borradores · desde 2020",
   "desc": "Proyectos de decreto y resolución abiertos a comentarios antes de expedirse: la señal más temprana de Caudal. Además de SUCOP, se leen los borradores que 15 entidades publican solo en su sitio.",
   "fuentes": [
    {
     "n": "SUCOP · DNP",
     "e": "conectada",
     "l": "4.505 borradores desde 2020; hoy 57 abiertos a comentarios"
    },
    {
     "n": "Sitios propios de las entidades",
     "e": "conectada",
     "l": "669 borradores de MinSalud, MinComercio, Supersubsidio, Colombia Compra Eficiente, SIC, Superfinanciera, Supersalud, Función Pública, UGPP, SENA, DNP, Supervigilancia, MinHacienda, MinAmbiente, MinDeporte, incluidos los que no pasan por SUCOP"
    }
   ]
  },
  "gacetas": {
   "n": "32.585",
   "unit": "gacetas del Congreso · desde 2000",
   "desc": "La Gaceta del Congreso enumerada y cruzada con el trámite: qué proyecto cita cada una y como qué documento. El Diario Oficial completo —4.701 actos de 175 entidades este año— y las gacetas de Antioquia y Medellín.",
   "fuentes": [
    {
     "n": "Gaceta del Congreso",
     "e": "conectada",
     "l": "32.585 gacetas: exposiciones de motivos, ponencias, textos aprobados y conciliaciones"
    },
    {
     "n": "Diario Oficial",
     "e": "conectada",
     "l": "Resoluciones, circulares y acuerdos de 175 entidades, leídos a diario"
    },
    {
     "n": "Gaceta Departamental de Antioquia",
     "e": "conectada",
     "l": "Decretos y resoluciones de la Gobernación"
    },
    {
     "n": "Gaceta Oficial de Medellín",
     "e": "conectada",
     "l": "Decretos, resoluciones y circulares de la Alcaldía"
    }
   ]
  },
  "territorial": {
   "n": "7.888",
   "unit": "registros · Antioquia y Medellín",
   "desc": "La Asamblea de Antioquia y el Concejo de Medellín: proyectos con su estado, ordenanzas y acuerdos, control político y sesiones programadas; y los decretos de la Gobernación y la Alcaldía por sus gacetas. Otras gobernaciones y concejos entran después.",
   "fuentes": [
    {
     "n": "Asamblea de Antioquia",
     "e": "conectada",
     "l": "Proyectos de ordenanza con su estado · Informes de ponencia · Ordenanzas (con PDF)"
    },
    {
     "n": "Concejo de Medellín",
     "e": "parcial",
     "l": "Proyectos de acuerdo con su estado · Acuerdos · Citaciones de control político. Falta: texto de cada proyecto (PDF) y su ponencia"
    },
    {
     "n": "Gobernación de Antioquia",
     "e": "conectada",
     "l": "Decretos y resoluciones por la Gaceta Departamental (98 % de la serie de decretos de 2026)"
    },
    {
     "n": "Alcaldía de Medellín",
     "e": "conectada",
     "l": "Decretos, resoluciones y circulares por la Gaceta Oficial"
    },
    {
     "n": "Otras gobernaciones y concejos",
     "e": "sin_fuente",
     "l": "Se suman una a una"
    }
   ]
  },
  "redes": {
   "n": "94",
   "unit": "entidades y gremios · cuentas verificadas",
   "desc": "Diccionario de cuentas oficiales del Estado, reguladores, cortes, Congreso y gremios, con el cargo que habla por cada uno. Las cuentas se leen del sitio oficial, no de memoria.",
   "fuentes": [
    {
     "n": "Sitio oficial de cada entidad",
     "e": "conectada",
     "l": "80 de 94 con las cuentas leídas de su pie de página"
    },
    {
     "n": "Verificación manual",
     "e": "parcial",
     "l": "9 entidades cuyo sitio no publica sus cuentas"
    }
   ]
  }
 }
};
