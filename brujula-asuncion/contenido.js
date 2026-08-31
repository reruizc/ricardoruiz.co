/* Brújula Asunción 2026 · contenido editorial
   Fuente: BRUJULA ASUNCIÓN AJUSTADA 2 CANDIDATOS.docx (corte 24-ago-2026).
   Para actualizar una posición: cambiar `pos` (1-5) y `conf` ('A' alta · 'M' media · 'B' baja).
   ⚠ conf:'B' = "posición pendiente de verificación": la pregunta NO entra al cálculo de
   afinidad de ese candidato (ni lo favorece ni lo perjudica). El 3 que lleva es provisional. */
window.BRUJULA = {
  version: '2026-08-26',
  eleccion: { fecha: '4 de octubre de 2026', cargo: 'Intendencia de Asunción', corte: '24 de agosto de 2026' },

  candidatos: [
    { id:'camilo', nombre:'Camilo Pérez', nombreLargo:'Camilo Pérez López Moreira', partido:'ANR – Partido Colorado', lista:'1', color:'#c8102e', foto:true,
      arquetipo:'Gerente conservador-desarrollista', ubicacion:'7,5 / 10 · centroderecha pragmática',
      resumen:'Presidente del Comité Olímpico Paraguayo desde 2011 y miembro del COI. Ganó la interna colorada de junio. Su narrativa traslada la gestión deportiva a la administración urbana: infraestructura, ejecución y resultados. No propone una Municipalidad chica: propone que la que hay funcione y se conecte con capital privado.',
      frase:'“El problema no es que la Municipalidad exista o sea grande; el problema es que funcione mal.”',
      redes:{ ig:'Camilo Pérez Intendente 2026', x:'@CamiloPerezLM' } },
    { id:'soledad', nombre:'Soledad Núñez', nombreLargo:'Soledad Núñez Méndez', partido:'Alianza Juntos por Asunción', lista:'4', color:'#1f5fbf', foto:true,
      arquetipo:'Tecnócrata reformista', ubicacion:'4,5 / 10 · centro reformista',
      resumen:'Ingeniera civil, ex secretaria ejecutiva de Senavitat (2014-2018) y candidata a la Vicepresidencia en 2023. Encabeza una coalición de 16 partidos. Su mensaje: reconstrucción institucional, saneamiento financiero y profesionalización de la Municipalidad.',
      frase:'“El problema es una institución capturada y mal administrada; hay que profesionalizarla y reconstruirla.”',
      redes:{ ig:'@sole.nu', x:'@solenu' } },
  ],

  /* Los 5 bloques del pentágono. Cada vértice promedia las preguntas del cuestionario que
     caen en sus temas, en la escala 1-5 del banco normalizada a 0-1.
     ⚠️ `inv:true` porque la escala de ese tema corre al revés que la de los demás: en
     movilidad el 1 es transporte público y el 5 el automóvil, mientras que en los otros
     once el 1 es mercado/control y el 5 público/comunitario. Sin invertirlo, ese tema
     tiraría del vértice hacia el lado contrario al que dice la respuesta.
     ⚠️ No se rotulan como izquierda/derecha: solo cuatro temas (3, 7, 9 y 11) tienen la
     escala ideológica del ajuste; el resto son ejes programáticos. Los polos describen
     lo que de verdad separa a las opciones. */
  bloques: [
    { id:'movimiento', nombre:'Ciudad en Movimiento', corto:'Movimiento',
      temas:[{t:1},{t:3},{t:6,inv:true}],
      polos:['Obra rápida, autos y ejecución privada','Obra de fondo, transporte público y red pública'] },
    { id:'cuida', nombre:'Ciudad que Cuida', corto:'Cuida',
      temas:[{t:2},{t:12}],
      polos:['Servicios tercerizados y salud del nivel nacional','Servicio municipal directo y prevención territorial'] },
    { id:'funciona', nombre:'Muni que Funciona', corto:'Funciona',
      temas:[{t:4},{t:5}],
      polos:['Ajustar la estructura y pagar la deuda primero','Sostener la estructura, las obras y los servicios'] },
    { id:'barrios', nombre:'Barrios Vivos', corto:'Barrios',
      temas:[{t:7},{t:8}],
      polos:['Concesiones privadas y vigilancia','Espacio público garantizado y prevención comunitaria'] },
    { id:'oportunidades', nombre:'Oportunidades Urbanas', corto:'Oportunidades',
      temas:[{t:9},{t:10},{t:11}],
      polos:['Mercado inmobiliario y empleo desde el sector privado','Protección de residentes y empleo como política pública'] },
  ],

  /* Temas de la conversación pública (códigos del rastreo de prensa) y a qué pregunta pesan. */
  temas: [
    { cod:'CV', nombre:'Calles, baches y veredas', q:[1] },
    { cod:'BA', nombre:'Basura y recolección', q:[2] },
    { cod:'RA', nombre:'Raudales, inundaciones y desagües', q:[3] },
    { cod:'OB', nombre:'Obras inconclusas', q:[3,1] },
    { cod:'GM', nombre:'Gestión municipal, deuda e impuestos', q:[4,5] },
    { cod:'TM', nombre:'Transporte, tránsito y movilidad', q:[6] },
    { cod:'EP', nombre:'Plazas y espacios públicos', q:[7] },
    { cod:'AM', nombre:'Ambiente, arroyos y áreas verdes', q:[7,9] },
    { cod:'IN', nombre:'Inseguridad e iluminación', q:[8] },
    { cod:'UR', nombre:'Urbanismo, ruido y densificación', q:[9] },
    { cod:'VA', nombre:'Vivienda, arraigo y titulación', q:[10] },
    { cod:'RC', nombre:'Centro Histórico', q:[9,7] },
  ],

  preguntas: [
    { n:1, tema:'CV', tag:'Calles', texto:'Cuando hay baches y calles en mal estado en Asunción, ¿qué te parece que debería priorizar la Muni?',
      escala:['Arreglar rápido la mayor cantidad de calles posible','Dar más prioridad a arreglos rápidos','Combinar arreglos rápidos con obras de fondo','Dar más prioridad a obras integrales','Hacer soluciones completas y duraderas en las calles más críticas, aunque se intervengan menos'],
      pos:{ camilo:{pos:2,conf:'A',txt:'Está claramente cerca del polo de intervención rápida y extensa. Su plan de 100 días pone el bacheo entre las prioridades y ha planteado aumentar la capacidad operativa, adquirir nuevas plantas asfálticas y acelerar pavimentaciones. También reconoce problemas de calidad en el bacheo, por lo cual no queda en 1 absoluto.'},
            soledad:{pos:4,conf:'A',txt:'Su propuesta habla de un Plan de Infraestructura Integral, identificación tecnológica de puntos críticos, cronogramas de bacheo, recapado, pavimentación y desagüe, laboratorio de calidad y mantenimiento planificado. El énfasis está más en planificación y durabilidad que en “tapar todos los huecos”.'},
            rodri:{pos:2,conf:'A',txt:'Su programa promete explícitamente intervenir todos los puntos críticos y cerrar todos los baches, además de corregir defectos de asfaltados y empedrados. La lógica es recuperar rápidamente la funcionalidad general de la ciudad.'},
            arlene:{pos:5,conf:'A',txt:'Es la posición más inequívoca: su programa contrapone directamente los parches con las “soluciones definitivas”, prioriza zonas de alto riesgo, control de calidad, coordinación con ESSAP e intervenciones durables.'} } },
    { n:2, tema:'BA', tag:'Basura', texto:'¿Cómo te parece que debería manejarse principalmente la recolección de basura en Asunción?',
      escala:['Contratar empresas privadas, con metas claras y control de la Muni','Que la mayor parte del servicio esté a cargo de empresas privadas','Combinar servicio municipal con empresas privadas','Que la mayor parte del servicio esté a cargo de la Muni','Que la Muni preste directamente todo el servicio'],
      pos:{ camilo:{pos:5,conf:'A',txt:'Su propuesta concreta pasa por fortalecer la operación municipal: reorganizar recursos humanos, optimizar rutas, GPS y cámaras en recolectores, duplicar capacidad e incorporar nuevos vehículos a la flota municipal. No propone sustituir la recolección por concesionarios privados.'},
            soledad:{pos:3,conf:'A',txt:'Representa prácticamente el modelo mixto. Plantea evaluar servicio por servicio y recurrir a concesiones o APP cuando resulte conveniente, manteniendo las funciones esenciales del Estado. Para limpieza propone brigadas, barrenderos y camiones con GPS.'},
            rodri:{pos:1,conf:'A',txt:'Es quien lleva más lejos la apertura competitiva. Propone servicios municipales mediante un sistema “abierto, competitivo y plural”, con empresas privadas, cooperativas, organizaciones comunitarias y comisiones vecinales, dejando a la Municipalidad la regulación, supervisión y control.'},
            arlene:{pos:4,conf:'A',txt:'Mantiene un núcleo municipal de limpieza y recolección —incluso con medidas específicas para esos trabajadores— pero lo complementa con vecinos, empresas de reciclaje, comercios e industrias. Modelo principalmente municipal con alianzas.'} } },
    { n:3, tema:'RA', tag:'Desagües', texto:'Cuando hay raudales e inundaciones, ¿dónde te parece que debería ponerse primero la plata para los desagües?',
      escala:['Terminar primero las grandes obras de desagüe que ya empezaron','Dar prioridad a las grandes obras','Combinar grandes obras con soluciones en los barrios','Dar más prioridad a intervenciones barriales','Repartir los recursos en muchas soluciones puntuales en distintos barrios'],
      pos:{ camilo:{pos:3,conf:'B',txt:'Hay referencias a infraestructura, asfaltado y recuperación vial, pero no una definición explícita sobre este dilema: terminar grandes sistemas de desagüe versus distribuir recursos en intervenciones pequeñas. Queda provisionalmente en 3.'},
            soledad:{pos:3,conf:'M',txt:'Su Plan de Infraestructura Integral incluye desagües y selección de puntos críticos, combinando planificación general con intervenciones localizadas. No plantea abandonar los grandes proyectos ni concentrarse exclusivamente en ellos.'},
            rodri:{pos:4,conf:'M',txt:'Su programa se inclina hacia intervenir puntos críticos y causas localizadas: defectos de asfaltados y empedrados, cauces, zonas peligrosas y medidas físicas frente a raudales. Eso lo acerca al enfoque territorial distribuido, aunque no formula el dilema “megaobra vs. pequeñas obras”.'},
            arlene:{pos:3,conf:'B',txt:'Su programa contempla recuperación de arroyos y actuación barrio por barrio, pero todavía no permite saber qué priorizaría presupuestariamente entre grandes colectores y pequeñas soluciones territoriales.'} } },
    { n:4, tema:'GM', tag:'Gasto municipal', texto:'Con los problemas financieros de la Muni, ¿qué te parece que habría que hacer con el gasto administrativo?',
      escala:['Hacer una reestructuración fuerte para liberar plata para servicios y obras','Reducir bastante el gasto administrativo','Buscar un punto medio','Hacer ajustes moderados','Mantener en gran parte la estructura actual y hacer cambios de a poco'],
      pos:{ camilo:{pos:4,conf:'A',txt:'Aquí se diferencia fuertemente de Franco. Rechaza el despido masivo: plantea jubilaciones anticipadas, reubicaciones y sanción a planilleros. Ha dicho que los funcionarios que efectivamente trabajan no deben ser despedidos indiscriminadamente.'},
            soledad:{pos:2,conf:'A',txt:'Propone actualización del organigrama, eliminación de funciones duplicadas, profesionalización y tolerancia cero a planilleros, junto con auditoría y revisión de contratos. Es una reforma importante, aunque no llega al achicamiento numérico extremo de Franco.'},
            rodri:{pos:1,conf:'A',txt:'Es el extremo inequívoco de esta escala: propone pasar de unas 60 direcciones a 12 y bajar la plantilla a menos de 5.000 personas, además de no renovar determinados contratos, jubilar, reasignar y despedir planilleros.'},
            arlene:{pos:3,conf:'M',txt:'Plantea reestructuración presupuestaria, reducción de gastos superfluos, digitalización, evaluación por resultados y capacitación de funcionarios, pero su propuesta no está construida alrededor de una reducción masiva de la planta municipal.'} } },
    { n:5, tema:'GM', tag:'Deuda', texto:'Si la plata de la Muni no alcanza para todo, ¿qué debería tener más prioridad para vos?',
      escala:['Bajar primero la deuda municipal','Dar más prioridad al pago de la deuda','Equilibrar deuda, servicios y obras','Dar más prioridad a servicios y obras','Mantener servicios y obras, aunque la deuda baje más despacio'],
      pos:{ camilo:{pos:4,conf:'A',txt:'No propone pagar aceleradamente la deuda. Busca refinanciarla, recomprar bonos caros, obtener mejores condiciones y un período de gracia, mientras recupera capacidad de inversión y prestación de servicios.'},
            soledad:{pos:3,conf:'A',txt:'Es probablemente la formulación más equilibrada. Propone un mapa real de la deuda y un plan responsable de pago, priorizando servicios esenciales como limpieza, seguridad e infraestructura, y considera reducir deuda y ordenar las cuentas como condiciones para recuperar la Municipalidad.'},
            rodri:{pos:2,conf:'A',txt:'Propone auditar toda la deuda, separar obligaciones legítimas e ilegítimas y calendarizar el pago de las legítimas dentro de un régimen de austeridad y prioridades estrictas. Inclinación fiscal más fuerte.'},
            arlene:{pos:4,conf:'M',txt:'Su formulación pone énfasis en reordenar presupuesto, eliminar gasto superfluo, mejorar recaudación y priorizar infraestructura, más que en hacer del pago acelerado de deuda el objetivo principal.'} } },
    { n:6, tema:'TM', tag:'Movilidad', texto:'Para movernos mejor por Asunción, ¿qué te parece que debería tener más prioridad?',
      escala:['Colectivos, veredas y otras alternativas al auto','Principalmente colectivos y peatones','Equilibrar los distintos medios de transporte','Principalmente mejorar la circulación vehicular','Mejorar la fluidez de los autos, el estacionamiento y la capacidad de las calles'],
      pos:{ camilo:{pos:3,conf:'A',txt:'Deliberadamente equilibrado. Ha dicho que debe haber una mejora profunda del transporte público, pero sin perjudicar a quienes usan automóvil. Es crítico del diseño de algunas bicisendas y prioriza mejorar pavimento para aumentar fluidez vehicular.'},
            soledad:{pos:2,conf:'A',txt:'Apuesta por transporte interno con cobertura en todos los barrios, reingeniería de rutas, frecuencias, corredores prioritarios, paradas seguras y hasta alternativas fluviales; simultáneamente incorpora semáforos inteligentes para mejorar el flujo vehicular.'},
            rodri:{pos:2,conf:'A',txt:'Propone nuevas licitaciones de buses y una diversificación considerable: tranvía eléctrico, monorriel y transporte fluvial, aunque también medidas explícitas para aumentar la fluidez de vehículos.'},
            arlene:{pos:2,conf:'M',txt:'Su programa de tránsito incluye prioridad al peatón, tránsito calmado en barrios residenciales, ordenamiento de estacionamiento y prevención vial. Menos detallado que Núñez y Franco en cuanto al sistema de buses.'} } },
    { n:7, tema:'EP', tag:'Plazas', texto:'Cuando hablamos de plazas, parques y áreas verdes, ¿qué te parece que debería pesar más?',
      escala:['Cuidarlos principalmente como espacios públicos y verdes','Dar más protección al uso público y a las áreas verdes','Buscar un equilibrio','Permitir algunos usos privados, pero regulados','Permitir usos comerciales o privados si ayudan a pagar su mantenimiento'],
      pos:{ camilo:{pos:2,conf:'A',txt:'Quiere recuperar y “deportivizar” plazas manteniéndolas como espacios municipales y verdes, aunque utilizando alianzas privadas para financiarlas.'},
            soledad:{pos:1,conf:'A',txt:'Plantea recuperar plazas, incluso las ocupadas por seccionales, y mantenerlas como espacios públicos cuidados.'},
            rodri:{pos:1,conf:'A',txt:'Formula el principio más fuerte de dominio público: defender terrenos destinados a plazas y recuperar los ocupados ilegalmente, aunque acepta concesiones privadas para mantenimiento.'},
            arlene:{pos:2,conf:'A',txt:'Combina plazas accesibles e inclusivas y recuperación de espacios con APP para mantenimiento, no para convertirlos prioritariamente en explotación comercial.'} } },
    { n:8, tema:'IN', tag:'Seguridad', texto:'Para que calles, plazas y otros espacios públicos sean más seguros, ¿qué te parece que debería priorizar la Muni?',
      escala:['Más cámaras, vigilancia y control','Principalmente vigilancia y presencia de control','Combinar vigilancia con prevención','Principalmente mejor iluminación y recuperación de espacios','Iluminación, mantenimiento de los espacios y prevención con los vecinos'],
      pos:{ camilo:{pos:2,conf:'A',txt:'Su eje central es una Policía Municipal de Cercanía con tecnología, monitoreo y cámaras; su campaña ha entregado cámaras en barrios. Lo complementa con recuperación e iluminación de espacios públicos, por eso queda en 2 y no en 1.'},
            soledad:{pos:3,conf:'A',txt:'Es casi exactamente el modelo combinado: cuerpo municipal disuasivo, vigilancia coordinada, iluminación, ocupación de espacios, cámaras, botones de auxilio, comités de seguridad y redes comunitarias.'},
            rodri:{pos:1,conf:'A',txt:'La propuesta más orientada a control: videovigilancia permanente, despliegue de Policía Municipal, “Vecinos en Alerta” y otras medidas de seguridad activa.'},
            arlene:{pos:3,conf:'A',txt:'Propone seguridad barrial coordinada con la Policía y combina esa presencia con iluminación, prevención vial, recuperación de espacios y cooperación comunitaria.'} } },
    { n:9, tema:'UR', tag:'Barrios y edificios', texto:'Cuando se construyen nuevos edificios o llegan nuevos comercios a barrios residenciales, ¿qué te parece que debería priorizarse?',
      escala:['Poner reglas más estrictas para cuidar las características del barrio','Dar mayor protección al barrio','Buscar un equilibrio','Dar más flexibilidad a nuevos proyectos e inversiones','Facilitar nuevas inversiones y mayor densidad, siempre que cumplan las normas técnicas'],
      pos:{ camilo:{pos:5,conf:'A',txt:'Posición particularmente clara. Ha planteado que la Municipalidad sea aliada de los desarrolladores, que las inmobiliarias sean socios estratégicos y que unos 9.000 terrenos municipales puedan ponerse en valor junto con privados, bajo reglas claras y planificación ordenada.'},
            soledad:{pos:3,conf:'B',txt:'Su programa habla de planificación, infraestructura, crecimiento, recuperación urbana y colaboración público-privada, pero no hay una definición precisa sobre cuánto flexibilizar densidad o usos frente a la defensa del carácter residencial de barrios concretos.'},
            rodri:{pos:4,conf:'M',txt:'Relaciona modernización del catastro con inversiones inmobiliarias, transferencias y desarrollo urbano y propone un plan moderno de desarrollo de largo plazo. Favorable al desarrollo, aunque sujeto a planificación.'},
            arlene:{pos:3,conf:'B',txt:'Habla de ordenamiento territorial y tránsito calmado en zonas residenciales, pero eso todavía no permite determinar cómo resolvería el dilema entre mayor densificación y protección del carácter de un barrio.'} } },
    { n:10, tema:'VA', tag:'Titulación', texto:'Si un nuevo proyecto urbano afecta a familias que todavía están esperando regularizar o titular sus casas, ¿qué te parece que debería hacerse primero?',
      escala:['Resolver primero la situación de las familias que ya viven ahí','Dar más prioridad a los vecinos residentes','Resolver las dos cosas al mismo tiempo','Dar más prioridad al nuevo proyecto','Dejar que el proyecto avance mientras se resuelven o compensan los casos afectados'],
      pos:{ camilo:{pos:2,conf:'M',txt:'Ha planteado regularizar terrenos municipales y brindar seguridad jurídica a familias, lo que lo coloca hacia la regularización previa. Pero tiene una agenda muy favorable al desarrollo de activos municipales con privados, por lo que no queda en 1.'},
            soledad:{pos:3,conf:'B',txt:'Su programa desarrolla catastro, gestión urbana y políticas territoriales, pero no hay una regla pública específica para el caso de familias en proceso de titulación enfrentadas a un proyecto inmobiliario concreto. No sería correcto adjudicarle 1 o 2 solo por su trayectoria anterior en vivienda.'},
            rodri:{pos:3,conf:'B',txt:'Su programa vincula catastro, claridad jurídica y “paz social”, pero no especifica qué prevalecería cuando la regularización de residentes entra en conflicto con un proyecto de inversión.'},
            arlene:{pos:1,conf:'A',txt:'Uno de sus posicionamientos más definidos: ha propuesto titulación masiva y la presenta como herramienta de seguridad jurídica, paz ciudadana y fortalecimiento de la recaudación municipal.'} } },
    { n:11, tema:'EM', tag:'Empleo', texto:'¿Qué papel debería asumir la Municipalidad en la generación de oportunidades laborales?',
      escala:['No es una función municipal relevante','Un papel limitado de facilitación','Apoyo complementario','Un rol activo de articulación y programas','Considerar empleo y oportunidades una prioridad municipal'],
      pos:{ camilo:{pos:4,conf:'A',txt:'Su programa propone facilitar inversión, simplificar trámites y articular al sector privado para generar actividad económica y empleo.'},
            soledad:{pos:5,conf:'A',txt:'Propone una Municipalidad activa en la articulación de oportunidades, formación y desarrollo económico local.'},
            rodri:{pos:4,conf:'A',txt:'Plantea simplificación, competencia y condiciones para que el sector privado genere empleo, con un rol municipal de facilitación activa.'},
            arlene:{pos:5,conf:'A',txt:'Su propuesta vincula oportunidades, formación, economía barrial y acompañamiento municipal directo.'} } },
    { n:12, tema:'SP', tag:'Dengue y salud', texto:'¿Qué papel debería asumir la Municipalidad en la prevención del dengue y otras arbovirosis?',
      escala:['Responsabilidad principalmente del sistema nacional de salud','Un papel municipal limitado','Coordinación regular con Salud y SENEPA','Intervención municipal activa','Prevención territorial permanente como responsabilidad municipal compartida'],
      pos:{ camilo:{pos:3,conf:'B',txt:'La evidencia pública disponible no permite ubicar con certeza el alcance de su propuesta municipal específica frente al dengue.'},
            soledad:{pos:4,conf:'M',txt:'Su enfoque de servicios, prevención y gestión territorial permite inferir una intervención municipal activa, coordinada con el sistema nacional.'},
            rodri:{pos:4,conf:'A',txt:'Propone una Municipalidad activa en servicios y presencia territorial, incluyendo prevención y respuesta en los barrios.'},
            arlene:{pos:5,conf:'A',txt:'Su propuesta prioriza una presencia territorial sostenida, servicios básicos y prevención cercana a los barrios.'} } },
  ],

  /* Pregunta de contexto nacional. NO entra al cálculo de afinidad ni a los ejes:
     no hay posición de candidatos porque no es una pregunta municipal. Se guarda aparte
     en el payload (`presidente`) para que no ensucie el promedio por pregunta del panel.
     Escala 1-5 donde 5 = muy buena. `orden` fija la presentación de mejor a peor y, de
     paso, impide que renderQ la baraje (una escala de valoración no se baraja). */
  extra: {
    presidente: {
      codigo:'PR', tag:'Gestión nacional', extra:true, orden:[5,4,3,2,1],
      texto:'Pensando en cómo viene gobernando el presidente Santiago Peña, ¿cómo calificarías su gestión?',
      escala:['Muy mala','Mala','Ni buena ni mala','Buena','Muy buena'],
      popular:{ texto:'¿Y cómo ves al presidente Santiago Peña? ¿Le está yendo bien o le está yendo mal?',
                escala:['Muy mal nomás','Mal','Ahí nomás','Bien','Muy bien'] },
      nota:'Esta no cuenta para tu resultado: no es una pregunta municipal. La preguntamos porque nos sirve para el estudio.'
    }
  },

  /* 5 arquetipos sociodigitales del modelo territorial (inferenciales) */
  arquetipos: {
    A1:{ nombre:'Influencer aspiracional urbana', img:'img/arq-influencer.jpg', color:'#b5224e', lectura:'Voto joven y urbano, sensible a la estética de la ciudad, la movilidad, la cultura y el estilo de vida. No vota por identidad partidaria: evalúa si una candidatura representa una ciudad deseable.', claves:['La ciudad moderna también se vota.','Asunción con movilidad, cultura y oportunidades.','Menos promesas viejas; más soluciones que se ven.'] },
    A2:{ nombre:'Profesional conectado de gestión', img:'img/arq-profesional.jpg', color:'#1b6a8a', lectura:'Voto urbano técnico, informado y exigente. Compara candidatos, revisa trayectoria, calcula viabilidad y castiga contradicciones, slogans vacíos y promesas inviables.', claves:['Gestión que se mide, no solo se anuncia.','Una capital funcional exige administración competente.','Transparencia, movilidad y servicios con resultados.'] },
    A3:{ nombre:'Familia viral comunitaria', img:'img/arq-familia.jpg', color:'#2f6b3f', lectura:'El arquetipo más voluminoso y transversal: vida familiar, redes de barrio, WhatsApp y Facebook. Vota por quien aparece, escucha y soluciona: seguridad, limpieza, servicios y respuesta cercana.', claves:['La ciudad se arregla cuidando cada barrio.','Seguridad, limpieza y servicios para la familia.','Escuchar, responder y volver con soluciones.'] },
    A4:{ nombre:'Joven viral popular', img:'img/arq-joven.jpg', color:'#d96a1a', lectura:'Jóvenes de barrios populares y mixtos, intensivos en TikTok y Reels. Decisión emocional, baja lealtad, alta exigencia de autenticidad. Se activa por transporte, empleo, deporte y trato digno.', claves:['Que la política se note en la vida joven.','Trabajo, transporte, deporte y cultura para empezar.','Tu barrio también tiene futuro.'] },
    A5:{ nombre:'Residente resiliente del Bañado', img:'img/arq-banado.jpg', color:'#5c4a1e', lectura:'Electorado de zonas de vulnerabilidad y asentamientos. Evalúa quién aparece antes, durante y después de los problemas. Responde a referentes reales, soluciones de emergencia y compromisos de gestión básica.', claves:['Dignidad primero, soluciones reales siempre.','Los Bañados no se visitan: se escuchan y se atienden.','Servicios, vivienda, salud y seguridad con ruta concreta.'] },
  },

  demo: {
    edades: [ {id:'18_24',l:'18 a 24'}, {id:'25_34',l:'25 a 34'}, {id:'35_44',l:'35 a 44'}, {id:'45_59',l:'45 a 59'}, {id:'60_mas',l:'60 o más'} ],
    canales: [
      { id:'ig', l:'Instagram, TikTok y reels de ciudad, gastronomía o cultura', arq:{A1:3,A4:1} },
      { id:'x',  l:'X, YouTube, prensa digital, debates y entrevistas', arq:{A2:3} },
      { id:'fb', l:'WhatsApp de la familia, Facebook y grupos del barrio', arq:{A3:3,A5:1} },
      { id:'tt', l:'TikTok, Shorts, fútbol, música y memes', arq:{A4:3,A1:1} },
      { id:'rd', l:'Radio, comisión vecinal, iglesia y referentes del barrio', arq:{A5:3,A3:1} },
    ],
  },
};

/* La versión de barrio conserva la escala y las posiciones; solo cambia la redacción. */
const VERSION_BARRIO = {
  1:{texto:'Cuando la calle está llena de baches, ¿qué tiene que hacer primero la Muni?',escala:['Arreglar rápido la mayor cantidad posible','Arreglar rápido en más lugares','Mezclar arreglos rápidos con obras de fondo','Hacer más arreglos completos','Arreglar de raíz las calles más críticas, aunque sean menos']},
  2:{texto:'Con la basura, ¿quién tiene que hacerse cargo principalmente?',escala:['Empresas privadas, bien controladas por la Muni','Mayormente empresas privadas','Muni y empresas trabajando juntas','Mayormente la Muni','La Muni directamente de punta a punta']},
  3:{texto:'Cuando vienen los raudales, ¿dónde hay que poner primero la plata para desagües?',escala:['Terminar las obras grandes que ya arrancaron','Dar más prioridad a las obras grandes','Mezclar obras grandes y soluciones de barrio','Meter más soluciones en los barrios','Repartir en muchas soluciones puntuales por los barrios']},
  4:{texto:'Con la plata corta, ¿qué hacemos con el gasto de oficina de la Muni?',escala:['Recortar fuerte para que alcance para servicios y obras','Bajar bastante el gasto de oficina','Buscar un punto medio','Hacer ajustes moderados','Dejar casi igual y cambiar de a poco']},
  5:{texto:'Si la plata de la Muni no alcanza para todo, ¿qué tendría que ir primero?',escala:['Bajar primero la deuda','Dar más prioridad a pagar la deuda','Equilibrar deuda, servicios y obras','Dar más prioridad a servicios y obras','Mantener servicios y obras aunque la deuda baje más lento']},
  6:{texto:'Para movernos mejor por Asunción, ¿qué tiene que ir primero?',escala:['Colectivos, veredas y otras opciones al auto','Principalmente colectivo y peatón','Equilibrar todos los medios','Mejorar más la circulación de autos','Dar prioridad a autos, estacionamiento y calles']},
  7:{texto:'Con las plazas y parques, ¿qué tendría que pesar más?',escala:['Cuidarlos como espacios verdes y de todos','Proteger más lo público y verde','Buscar equilibrio','Permitir algunos usos privados, con reglas','Permitir usos privados si ayudan a mantenerlos']},
  8:{texto:'Para sentirnos más seguros en la calle y la plaza, ¿qué tendría que hacer primero la Muni?',escala:['Más cámaras, vigilancia y control','Más presencia de control','Mezclar vigilancia y prevención','Más iluminación y recuperar espacios','Iluminación, espacios cuidados y prevención con vecinos']},
  9:{texto:'Cuando llegan edificios o negocios nuevos al barrio, ¿qué tendría que pesar más?',escala:['Poner reglas fuertes para cuidar el barrio','Proteger más al barrio','Buscar equilibrio','Dar más lugar a proyectos e inversión','Facilitar inversión y más edificios si cumplen las reglas']},
  10:{texto:'Si una obra nueva afecta a familias que todavía esperan el título de su casa, ¿qué hay que hacer primero?',escala:['Resolver primero lo de las familias que ya viven ahí','Dar más prioridad a los vecinos','Resolver las dos cosas al mismo tiempo','Dar más prioridad a la obra nueva','Dejar avanzar la obra mientras se arreglan o compensan los casos']},
  11:{texto:'¿La Muni pio tiene que ayudar a que haya más laburo en Asunción?',escala:['Eso no le toca mucho a la Muni','Que ayude poquito nomás','Que acompañe en algunas cosas','Que se mueva bastante con empresas y cursos','Sí, que se mueva para que haya laburo, no discurso nomás']},
  12:{texto:'Con el dengue dando vueltas cada verano, ¿la Muni pio tiene que meterse fuerte o dejarle casi todo a Salud y SENEPA?',escala:['Eso es más de Salud y SENEPA','Que la Muni ayude poquito nomás','Que trabajen juntos seguido','Que la Muni se mueva fuerte nomás','Sí, barrio por barrio y todo el año; no aparecer solo cuando explota el dengue']},
};
window.BRUJULA.preguntas.forEach(q=>{ q.popular=VERSION_BARRIO[q.n]; });
