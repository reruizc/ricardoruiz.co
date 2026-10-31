"""Caudal · catálogo de cobertura por entidad (alerta «Tus entidades», oct-2026).

Es la tabla de la sección 2 de `Bases de datos/caudal-entidades/plan.md` en datos:
qué lee Caudal de cada entidad y qué no, y por qué. `build.py` le suma los conteos
reales (actos en el Diario Oficial, borradores abiertos, normas y eventos) y lo
sube como `metadata/entidades-catalogo.json`. La Lambda lo cruza con los
interlocutores de cada perfil para que el cliente sepa qué se vigila y qué no,
sin tener que suponerlo.

Al conectar una fuente nueva: actualizar aquí `estado`, `cubre` y `falta`.

estado: conectada · parcial · sin_fuente · no_aplica
`alias`: fragmentos plegados (minúsculas, sin tildes) con que puede aparecer la
entidad en una ficha de cliente o en el Diario Oficial. Basta con que uno esté
contenido en el nombre o viceversa.
"""

DO = 'Diario Oficial (resoluciones, circulares y acuerdos)'
SUCOP = 'Borradores en SUCOP'

CATALOGO = [
    # ── superintendencias y UGPP ──
    dict(k='ssf', nombre='Superintendencia del Subsidio Familiar', alias=['subsidio familiar', 'supersubsidio'],
         estado='conectada', cubre=['Borradores propios', 'Circulares', 'Resoluciones', 'Relatoría jurídica (conceptos)',
                                    'Noticias', 'Calendario oficial', DO],
         falta=[], nota='Su calendario oficial dejó de alimentarse el 26 de junio de 2026 y su relatoría va con rezago: '
                        'el concepto más reciente es de marzo de 2026.'),
    dict(k='supersalud', nombre='Superintendencia Nacional de Salud', alias=['supersalud', 'superintendencia nacional de salud'],
         estado='conectada', cubre=['Sanciones', 'Registro de actos', 'Comunicados de intervención', 'Circulares externas',
                                    'Boletín jurídico', 'Proyectos en consulta (anunciados en noticias)', DO],
         falta=['Resoluciones particulares (463 en 2026, con título de solo un número)'],
         nota='Sus resoluciones que importan llegan por el Diario Oficial.'),
    dict(k='sic', nombre='Superintendencia de Industria y Comercio', alias=['industria y comercio', 'superindustria'],
         estado='conectada', cubre=['Sanciones', 'Circulares', 'Resoluciones de carácter general', 'Proyectos propios',
                                    'Conceptos de abogacía de la competencia', 'Eventos', SUCOP, DO],
         falta=['Doctrina jurídica: la SIC la congeló en 2021'], nota=''),
    dict(k='supervigilancia', nombre='Superintendencia de Vigilancia y Seguridad Privada', alias=['vigilancia y seguridad privada', 'supervigilancia'],
         estado='parcial', cubre=[DO], falta=['Resoluciones y circulares propias', 'Proyectos', 'Noticias'],
         nota='Sus conceptos están congelados desde 2018.'),
    dict(k='supersociedades', nombre='Superintendencia de Sociedades', alias=['superintendencia de sociedades', 'supersociedades'],
         estado='conectada', cubre=['Sanciones', 'Normas', 'Conceptos jurídicos (Tesauro, 13.002)', DO],
         falta=['Eventos: su calendario responde error'], nota='Su relatoría va con rezago: el concepto más reciente es de marzo de 2026.'),
    dict(k='superfinanciera', nombre='Superintendencia Financiera de Colombia', alias=['superintendencia financiera', 'superfinanciera'],
         estado='parcial', cubre=['Sanciones del mercado de valores', 'Proyectos de norma y documentos técnicos',
                                  'Circulares externas', 'Cartas circulares', 'Resoluciones', DO],
         falta=['Conceptos: su catálogo no deja filtrar y lo último visible es de 2021'], nota=''),
    dict(k='ugpp', nombre='Unidad de Gestión Pensional y Parafiscales (UGPP)', alias=['ugpp', 'gestion pensional'],
         estado='conectada', cubre=['Resoluciones, circulares y acuerdos de su sitio', 'Proyectos de resolución', 'Noticias', DO],
         falta=['Capacitaciones: su calendario no tiene eventos publicados'],
         nota='No publica conceptos: la categoría existe y está vacía. La única vía es un derecho de petición. '
              'Sus fichas no traen fecha: lo que ya existía entra sin fecha y lo nuevo con el día en que aparece.'),
    # ── ministerios ──
    dict(k='mintrabajo', nombre='Ministerio del Trabajo', alias=['ministerio del trabajo', 'ministerio de trabajo', 'mintrabajo'],
         estado='conectada', cubre=['Resoluciones', 'Circulares', 'Conceptos institucionales', 'Agenda regulatoria',
                                    'Comunicados', SUCOP, DO], falta=[],
         nota='La fecha de sus conceptos es la de publicación en el sitio, aproximada: la lista no trae la de expedición.'),
    dict(k='minvivienda', nombre='Ministerio de Vivienda, Ciudad y Territorio', alias=['ministerio de vivienda', 'minvivienda', 'fondo nacional de vivienda'],
         estado='conectada', cubre=['Resoluciones y circulares', 'Conceptos jurídicos', 'Prensa', 'Agenda regulatoria (vía SUCOP)',
                                    SUCOP, DO], falta=[],
         nota='De las resoluciones de Fonvivienda solo entran las de cupos y convocatorias: el resto son actos particulares. '
              'Sus conceptos no traen fecha: lo que ya existía entra sin fecha y lo nuevo con el día en que aparece.'),
    dict(k='minsalud', nombre='Ministerio de Salud y Protección Social', alias=['ministerio de salud', 'minsalud'],
         estado='conectada', cubre=['Borradores propios (con historial: borra los cerrados)', 'Análisis de impacto normativo',
                                    'Normograma', 'Conceptos jurídicos', 'Calendario oficial', DO],
         falta=['Noticias'], nota=''),
    dict(k='mineducacion', nombre='Ministerio de Educación Nacional', alias=['ministerio de educacion', 'mineducacion'],
         estado='conectada', cubre=['Resoluciones, circulares y directivas', 'Comunicados', 'Agenda regulatoria (vía SUCOP)', SUCOP, DO],
         falta=[], nota='Sus conceptos no se publican al día. Su sala de prensa solo muestra los últimos comunicados: se acumulan desde oct-2026.'),
    dict(k='mincultura', nombre='Ministerio de las Culturas, las Artes y los Saberes', alias=['ministerio de las culturas', 'ministerio de cultura', 'mincultura'],
         estado='parcial', cubre=[SUCOP, DO], falta=['Noticias y convocatorias'],
         nota='Sus resoluciones de 2026 no están en su sitio: solo por el Diario Oficial. No publica conceptos.'),
    dict(k='mincomercio', nombre='Ministerio de Comercio, Industria y Turismo', alias=['ministerio de comercio', 'mincomercio', 'mincit'],
         estado='parcial', cubre=['Borradores propios (no publica en SUCOP desde 2025)', DO],
         falta=['Agenda regulatoria', 'Calendario de eventos'], nota='No publica conceptos.'),
    dict(k='minagricultura', nombre='Ministerio de Agricultura y Desarrollo Rural', alias=['ministerio de agricultura', 'minagricultura'],
         estado='parcial', cubre=[SUCOP, DO], falta=['Agenda regulatoria', 'Noticias'], nota='No publica conceptos.'),
    dict(k='minambiente', nombre='Ministerio de Ambiente y Desarrollo Sostenible', alias=['ministerio de ambiente', 'minambiente'],
         estado='parcial', cubre=[DO], falta=['Borradores propios', 'Agenda regulatoria', 'Eventos'],
         nota='Sus conceptos se congelaron en 2025.'),
    dict(k='mindeporte', nombre='Ministerio del Deporte', alias=['ministerio del deporte', 'mindeporte'],
         estado='parcial', cubre=[DO], falta=['Borradores propios', 'Agenda regulatoria', 'Convocatorias'],
         nota='Sus conceptos se congelaron en 2024.'),
    dict(k='minhacienda', nombre='Ministerio de Hacienda y Crédito Público', alias=['ministerio de hacienda', 'minhacienda', 'hacienda y credito publico'],
         estado='parcial', cubre=[DO], falta=['Texto de sus borradores'],
         nota='Su sitio está detrás de un antibots: lo expedido llega por el Diario Oficial, sus borradores no.'),
    # ── otras del Ejecutivo ──
    dict(k='dnp', nombre='Departamento Nacional de Planeación', alias=['planeacion nacional', 'departamento nacional de planeacion', 'dnp'],
         estado='conectada', cubre=['Circulares y resoluciones', 'Proyectos propios que no están en SUCOP', SUCOP, DO],
         falta=['Eventos: su página es un archivo de seminarios viejos'],
         nota='No publica conceptos. Sus circulares suelen ser escaneadas: quedan con el título.'),
    dict(k='funcionpublica', nombre='Departamento Administrativo de la Función Pública', alias=['funcion publica'],
         estado='conectada', cubre=['Proyectos propios', 'Conceptos del Gestor Normativo', 'Circulares y resoluciones',
                                    'Agenda regulatoria', DO],
         falta=['Capacitaciones: viven en un widget de la portada'], nota=''),
    dict(k='spe', nombre='Unidad del Servicio Público de Empleo', alias=['servicio publico de empleo'],
         estado='conectada', cubre=['Resoluciones y circulares', 'Noticias', DO], falta=[],
         nota='No publica conceptos. Sus actos no tienen listado: salen de los PDF de su biblioteca y un escaneado queda sin objeto.'),
    dict(k='sena', nombre='Servicio Nacional de Aprendizaje (SENA)', alias=['servicio nacional de aprendizaje', 'sena'],
         estado='conectada', cubre=['Proyectos propios', 'Resoluciones, acuerdos y circulares del normograma', DO], falta=[],
         nota='El normograma va con un mes de rezago y no da la fecha de expedición: se usa el fin del mes en que se incorporó.'),
    dict(k='cce', nombre='Colombia Compra Eficiente', alias=['colombia compra', 'contratacion publica'],
         estado='conectada', cubre=['Convocatorias de participación', 'Circulares', 'Conceptos de la relatoría', 'Capacitaciones', SUCOP, DO],
         falta=[], nota=''),
    dict(k='presidencia', nombre='Presidencia de la República', alias=['presidencia de la republica', 'presidencia'],
         estado='parcial', cubre=['Decretos y leyes', 'Directivas', DO],
         falta=['Su sitio web'], nota='Su sitio está detrás de un antibots; lo que expide llega por el Diario Oficial.'),
    dict(k='dian', nombre='Dirección de Impuestos y Aduanas Nacionales (DIAN)', alias=['impuestos y aduanas', 'dian'],
         estado='conectada', cubre=['Resoluciones y circulares', 'Conceptos y oficios (doctrina)', SUCOP, DO],
         falta=[], nota=''),
    dict(k='mininterior', nombre='Ministerio del Interior', alias=['ministerio del interior', 'mininterior'],
         estado='parcial', cubre=[SUCOP, DO], falta=['Proyectos y circulares de su sitio'], nota=''),
    dict(k='mintransporte', nombre='Ministerio de Transporte', alias=['ministerio de transporte', 'mintransporte'],
         estado='parcial', cubre=[SUCOP, DO], falta=['Resoluciones y circulares de su sitio'], nota=''),
    dict(k='supertransporte', nombre='Superintendencia de Transporte', alias=['superintendencia de transporte', 'supertransporte'],
         estado='parcial', cubre=['Sanciones', DO], falta=['Circulares', 'Conceptos'], nota=''),
    dict(k='uiaf', nombre='Unidad de Información y Análisis Financiero (UIAF)', alias=['uiaf', 'informacion y analisis financiero'],
         estado='parcial', cubre=['Obligaciones de reporte ALA/CFT', DO], falta=['Revisión pendiente de lo demás que publica'], nota=''),
    dict(k='banrep', nombre='Banco de la República', alias=['banco de la republica', 'banrep'],
         estado='parcial', cubre=['Junta Directiva y régimen cambiario'], falta=['Revisión pendiente de lo demás que publica'], nota=''),
    dict(k='superintendencias', nombre='Superintendencias (en general)', alias=['superintendencias'],
         estado='parcial', cubre=['Sanciones y normas de las superintendencias en el pilar Regulatorio'],
         falta=['Cada superintendencia tiene su propia cobertura: agrégalas una por una'], nota=''),
    # ── altas cortes ──
    dict(k='corte-constitucional', nombre='Corte Constitucional', alias=['corte constitucional'],
         estado='conectada', cubre=['Sentencias (pilar Órganos de control y altas cortes)'], falta=[], nota=''),
    dict(k='consejo-estado', nombre='Consejo de Estado', alias=['consejo de estado'],
         estado='sin_fuente', cubre=[], falta=['Sentencias y conceptos de la Sala de Consulta'], nota=''),
    # ── territoriales (fase 2) ──
    dict(k='asamblea-antioquia', nombre='Asamblea de Antioquia', alias=['asamblea de antioquia', 'asamblea departamental de antioquia'],
         estado='conectada', cubre=['Proyectos de ordenanza con su estado', 'Informes de ponencia', 'Ordenanzas (con PDF)'],
         falta=['Actas de sesión', 'Agenda semanal'], nota=''),
    dict(k='concejo-medellin', nombre='Concejo de Medellín', alias=['concejo de medellin'],
         estado='parcial', cubre=['Proyectos de acuerdo con su estado', 'Acuerdos', 'Citaciones de control político',
                                  'Sesiones de plenaria programadas', 'Reuniones de comisiones permanentes'],
         falta=['Texto de cada proyecto (PDF) y su ponencia', 'Enlace propio por registro (SIMI no lo da)'], nota=''),
    dict(k='gobernacion-antioquia', nombre='Gobernación de Antioquia', alias=['gobernacion de antioquia'],
         estado='sin_fuente', cubre=[], falta=['Decretos y resoluciones departamentales'], nota='En construcción (fase 2).'),
    dict(k='alcaldia-medellin', nombre='Alcaldía de Medellín', alias=['alcaldia de medellin', 'distrito de medellin'],
         estado='sin_fuente', cubre=[], falta=['Decretos y resoluciones municipales'], nota=''),
    dict(k='alcaldias', nombre='Alcaldías', alias=['alcaldias'],
         estado='sin_fuente', cubre=[], falta=['Decretos y resoluciones municipales'], nota='Caudal todavía no lee alcaldías.'),
    # ── no son entidades del Estado ──
    dict(k='asocajas', nombre='Asocajas', alias=['asocajas'], estado='no_aplica', cubre=[], falta=[],
         nota='Es un gremio, no una entidad del Estado: se sigue por prensa y redes.'),
    dict(k='congreso', nombre='Congreso de la República', alias=['congreso de la republica', 'congreso'],
         estado='conectada', cubre=['Proyectos de ley', 'Votaciones', 'Gacetas', 'Órdenes del día'], falta=[], nota=''),
]
