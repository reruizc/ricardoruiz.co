/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · lo que se le dice a cada candidatura según DÓNDE compite
   ───────────────────────────────────────────────────────────────────────────
   Antes el CRM tenía una frase por familia política para todo el país: lo
   mismo le decía al centro-derecha en Casanare que en Cali. Aquí va en tres
   capas, de la más escrita a la más medida:

   1. REGIONES: una entrada por departamento (código ELECTORAL, el de
      DEP_CODES) y por ciudad principal, con el tema que pesa ahí y una
      lectura por espectro. La ciudad manda sobre su departamento.
   2. PARTIDOS: una línea de identidad por organización grande, en tono
      descriptivo. No es propaganda ni juicio: es cómo se ubica cada una.
   3. dato(): la frase MEDIDA —cuánto sacó esa familia o ese partido en ese
      territorio en 2023— desde los mismos JSON que usa el resto del CRM.
      Es lo único con cifras, y sale de la fuente, no de este archivo.

   ⚠️ Regla de redacción: las capas 1 y 2 NO llevan cifras ni nombres propios
   de personas. Las cifras envejecen y los nombres exponen; eso lo pone la
   capa 3 con dato publicado. Tono: usted, como el resto del CRM.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');

  /* ── 1. Departamentos ─────────────────────────────────────────────────── */
  const DEPARTAMENTOS = {
    '01': { n: 'Antioquia', tema: 'seguridad, vías y el peso del voto de los municipios frente al Valle de Aburrá',
      izq: 'En Antioquia la izquierda juega de visitante: su voto está en los barrios populares del Valle de Aburrá, en Urabá y en el Bajo Cauca, y la campaña se gana ahí, no disputándole el oriente a la derecha.',
      ci: 'En Antioquia el centro-izquierda compite contra una identidad regional muy fuerte: el mensaje funciona cuando habla de gestión y de ciudad, no de ideología.',
      c: 'En Antioquia el centro tiene espacio entre dos bandos muy marcados: el votante cansado de la pelea existe, sobre todo en el área metropolitana, pero hay que ir a buscarlo.',
      cd: 'En Antioquia el centro-derecha juega en casa, pero comparte base con la derecha: la diferencia se hace con gestión concreta en cada municipio.',
      d: 'Antioquia es el bastión de la derecha y fue la que definió la presidencial de 2026: el reto no es convencer, es que su votante salga y no se lo lleve otra lista de la misma familia.' },
    '03': { n: 'Atlántico', tema: 'servicios públicos, el área metropolitana de Barranquilla y estructuras políticas de larga data',
      izq: 'En el Atlántico la izquierda creció en la presidencial de 2026 y ganó Barranquilla en segunda vuelta: el reto es convertir ese voto nacional en voto local, que aquí se mueve por otras lealtades.',
      ci: 'En el Atlántico el centro-izquierda tiene que competir con maquinarias muy aceitadas: la diferencia está en el voto de opinión de Barranquilla y en los barrios que se quejan de los servicios.',
      c: 'En el Atlántico el centro compite entre grandes estructuras: su espacio es el votante que quiere resultados sin padrinos.',
      cd: 'En el Atlántico el centro-derecha tiene tradición de gobierno local: el mensaje de obra y gestión está probado, y la competencia es con listas de la misma orilla.',
      d: 'En el Atlántico la derecha nacional no siempre coincide con el voto local: aquí la gestión y la estructura pesan más que la etiqueta.' },
    '05': { n: 'Bolívar', tema: 'Cartagena, el sur de Bolívar y la brecha entre la ciudad turística y los barrios populares',
      izq: 'En Bolívar el voto de izquierda está en los barrios populares de Cartagena y en el sur del departamento: es un voto de demanda social que responde a presencia, no a discurso.',
      ci: 'En Bolívar el centro-izquierda tiene su espacio en el voto de opinión de Cartagena, cansado de la corrupción local: ahí el mensaje de transparencia rinde.',
      c: 'En Bolívar el centro compite entre la política tradicional y el voto de protesta: el votante que pide que la plata llegue es su cancha.',
      cd: 'En Bolívar el centro-derecha se mueve bien en los municipios y en las estructuras regionales: la clave es la presencia territorial.',
      d: 'En Bolívar la derecha tiene voto en la Cartagena de clase media y en zonas ganaderas: el mensaje de seguridad y orden le habla directo.' },
    '07': { n: 'Boyacá', tema: 'el campo, la leche, las vías terciarias y una tradición de voto independiente',
      izq: 'En Boyacá la izquierda tiene voto campesino y en Tunja y Sogamoso: el mensaje que funciona es el del campo que no recibe precio justo.',
      ci: 'Boyacá tiene tradición de voto verde e independiente: el centro-izquierda juega de local si habla de campo, agua y transparencia.',
      c: 'En Boyacá el centro compite con un votante pragmático y muy territorial: vereda por vereda, lo que cuenta es haber llegado.',
      cd: 'En Boyacá el centro-derecha tiene raíces conservadoras en los municipios: la estructura existe, el reto es renovarla.',
      d: 'En Boyacá la derecha tiene voto rural y de orden: el mensaje de seguridad en las vías y apoyo al productor le funciona.' },
    '09': { n: 'Caldas', tema: 'el café, el Eje Cafetero y una política liberal y conservadora de mucha tradición',
      izq: 'En Caldas la izquierda crece sobre todo en Manizales y en la juventud universitaria: afuera, el voto tradicional pesa mucho.',
      ci: 'En Caldas el centro-izquierda tiene su nicho en el voto universitario y de opinión de Manizales: ahí se hace la diferencia.',
      c: 'En Caldas el centro dialoga con un electorado de partidos tradicionales: el votante liberal que busca algo nuevo es su puerta.',
      cd: 'En Caldas el centro-derecha tiene una base conservadora histórica en los municipios cafeteros: la estructura ayuda, la renovación también.',
      d: 'En Caldas la derecha tiene voto fuerte en los municipios cafeteros: el mensaje de campo, precio del café y seguridad le habla directo.' },
    '11': { n: 'Cauca', tema: 'el conflicto armado, la tierra y los pueblos indígenas y campesinos',
      izq: 'En las presidenciales el Cauca vota fuerte por la izquierda, y tiene organización indígena y campesina: aquí la meta se hace con esas organizaciones, no a su alrededor.',
      ci: 'En el Cauca el centro-izquierda compite con una izquierda muy organizada: su espacio está en Popayán y en el voto urbano que pide paz con institucionalidad.',
      c: 'En el Cauca el centro tiene que hablar de seguridad y de paz a la vez: el votante que quiere las dos cosas existe, sobre todo en Popayán.',
      cd: 'En el Cauca el centro-derecha tiene su voto en Popayán y en la tradición conservadora: la clave es hablar de seguridad sin dejar de lado lo rural.',
      d: 'En el Cauca la derecha compite en cancha difícil: su voto está en Popayán y en zonas productivas golpeadas por la violencia, y el mensaje de seguridad es el que llega.' },
    '12': { n: 'Cesar', tema: 'el carbón, la ganadería, el agua y Valledupar',
      izq: 'En el Cesar la izquierda tiene voto en los barrios de Valledupar y en la zona minera: el mensaje de trabajo digno y de lo que dejan las regalías rinde.',
      ci: 'En el Cesar el centro-izquierda tiene espacio en el voto urbano de Valledupar, que se cansa de las mismas caras.',
      c: 'En el Cesar el centro compite con estructuras regionales fuertes: su puerta es el votante que quiere que las regalías se vean.',
      cd: 'En el Cesar el centro-derecha tiene base en la tradición política regional: la presencia en cada municipio es lo que cuenta.',
      d: 'En el Cesar la derecha tiene voto ganadero y rural: el mensaje de seguridad y apoyo al campo le funciona.' },
    '13': { n: 'Córdoba', tema: 'la tierra, la ganadería, Montería y estructuras familiares tradicionales',
      izq: 'En Córdoba la izquierda tiene voto campesino y en los barrios populares de Montería: se gana con presencia, porque la competencia tiene mucha estructura.',
      ci: 'En Córdoba el centro-izquierda tiene espacio en el voto joven y de opinión de Montería: ahí el discurso de renovación funciona.',
      c: 'En Córdoba el centro compite con maquinarias muy fuertes: el voto de opinión urbano es su terreno.',
      cd: 'En Córdoba el centro-derecha se mueve en estructuras regionales de larga data: la clave es el trabajo municipio por municipio.',
      d: 'En Córdoba la derecha tiene voto fuerte en la zona ganadera: el mensaje de orden y de apoyo al productor le habla directo.' },
    '15': { n: 'Cundinamarca', tema: 'la Sabana, la movilidad hacia Bogotá y el contraste entre municipios dormitorio y rurales',
      izq: 'En Cundinamarca la izquierda tiene voto en Soacha y en los municipios dormitorio: el mensaje de transporte y costo de vida es el que llega.',
      ci: 'En Cundinamarca el centro-izquierda compite bien en la Sabana, con voto de opinión que vive en el municipio y trabaja en Bogotá.',
      c: 'En Cundinamarca el centro tiene espacio en los municipios que crecen rápido: el votante nuevo no tiene lealtad de partido.',
      cd: 'En Cundinamarca el centro-derecha tiene base en los municipios rurales y tradicionales: la estructura municipal es su fuerza.',
      d: 'En Cundinamarca la derecha tiene voto rural y en la Sabana de clase media: seguridad y vías son el mensaje.' },
    '16': { n: 'Bogotá', tema: 'el metro, la seguridad, la movilidad y la brecha entre el norte y el sur',
      izq: 'En Bogotá la izquierda tiene su voto en el sur y el occidente —Bosa, Kennedy, Ciudad Bolívar, Usme—: ahí la meta se gana con presencia en el barrio.',
      ci: 'En Bogotá el centro-izquierda tiene un voto de opinión grande y exigente: se gana con propuestas concretas de movilidad y ciudad.',
      c: 'En Bogotá el centro compite por el votante que no se casa con nadie, que es mucho: el mensaje de gestión y datos le llega.',
      cd: 'En Bogotá el centro-derecha compite entre el voto de gestión y el de la derecha: su espacio está en la clase media que pide resultados.',
      d: 'En Bogotá la derecha tiene su voto en el norte y el noroccidente —Usaquén, Suba, Engativá, Chapinero—: seguridad y gestión son el mensaje.' },
    '19': { n: 'Huila', tema: 'el café, el agro, las represas y Neiva',
      izq: 'En el Huila la izquierda tiene voto campesino y cafetero que pide precio y tierra: se gana en la zona rural.',
      ci: 'En el Huila el centro-izquierda tiene espacio en Neiva y en el voto joven que quiere algo distinto.',
      c: 'En el Huila el centro dialoga con un electorado de tradición liberal y conservadora: el votante pragmático es su puerta.',
      cd: 'En el Huila el centro-derecha tiene base conservadora histórica: la estructura existe en cada municipio.',
      d: 'En el Huila la derecha tiene voto fuerte en el campo: seguridad y apoyo al productor cafetero son el mensaje.' },
    '21': { n: 'Magdalena', tema: 'Santa Marta, el agua, la Sierra Nevada y movimientos políticos regionales propios',
      izq: 'El Magdalena tiene un movimiento regional de izquierda con estructura propia: competir en esa orilla exige diferenciarse o sumarse.',
      ci: 'En el Magdalena el centro-izquierda compite con una izquierda regional muy fuerte: su espacio es el voto de opinión de Santa Marta.',
      c: 'En el Magdalena el centro tiene su puerta en el votante que pide agua y servicios, cansado de la pelea entre bandos.',
      cd: 'En el Magdalena el centro-derecha tiene estructuras en los municipios: la clave es la presencia fuera de Santa Marta.',
      d: 'En el Magdalena la derecha compite contra un movimiento regional fuerte: su voto está en la zona bananera y en la clase media samaria.' },
    '23': { n: 'Nariño', tema: 'la frontera, el Pacífico, los cultivos y una identidad regional muy propia',
      izq: 'En las presidenciales Nariño vota fuerte por la izquierda y tiene identidad regional marcada: el mensaje que funciona habla del sur como región, no solo de ideología.',
      ci: 'En Nariño el centro-izquierda tiene espacio en Pasto y en el voto que pide paz con institucionalidad.',
      c: 'En Nariño el centro compite con una izquierda fuerte: su votante está en Pasto y en la clase media que pide gestión.',
      cd: 'En Nariño el centro-derecha tiene base conservadora en municipios de la cordillera: la presencia territorial es la clave.',
      d: 'En Nariño la derecha compite en cancha difícil: el mensaje de seguridad en la frontera y en el Pacífico es el que llega.' },
    '25': { n: 'Norte de Santander', tema: 'el Catatumbo, la frontera con Venezuela y la migración',
      izq: 'En Norte de Santander la izquierda tiene voto en el Catatumbo y en barrios de Cúcuta: el mensaje de paz y presencia del Estado le habla directo.',
      ci: 'En Norte de Santander el centro-izquierda compite en cancha de derecha: su espacio es el voto de opinión de Cúcuta.',
      c: 'En Norte de Santander el centro tiene su puerta en el votante que pide frontera abierta y empleo, más allá de la pelea.',
      cd: 'En Norte de Santander el centro-derecha tiene base amplia: el mensaje de seguridad y comercio fronterizo funciona.',
      d: 'En las presidenciales Norte de Santander vota fuerte por la derecha: en lo local el reto es que ese voto no se divida entre listas de la misma orilla.' },
    '24': { n: 'Risaralda', tema: 'Pereira, el Eje Cafetero y el empleo',
      izq: 'En Risaralda la izquierda tiene voto en Pereira y Dosquebradas, pero el departamento giró a la derecha en 2026: hay que ir a buscarlo barrio por barrio.',
      ci: 'En Risaralda el centro-izquierda tiene espacio en el voto universitario y de opinión de Pereira.',
      c: 'En Risaralda el centro dialoga con un electorado de tradición liberal: el votante pragmático de Pereira es su puerta.',
      cd: 'En Risaralda el centro-derecha tiene base en los municipios y en la tradición de partido: la estructura ayuda.',
      d: 'Risaralda se inclinó a la derecha en la presidencial de 2026: el mensaje de seguridad y empleo tiene terreno ganado.' },
    '26': { n: 'Quindío', tema: 'el café, el turismo y Armenia',
      izq: 'En el Quindío la izquierda tiene voto en Armenia, pero el departamento giró a la derecha en 2026: la campaña se hace barrio por barrio.',
      ci: 'En el Quindío el centro-izquierda tiene espacio en el voto de opinión de Armenia, que pide turismo y empleo.',
      c: 'En el Quindío el centro compite por un votante pragmático: turismo, empleo y gestión son su mensaje.',
      cd: 'En el Quindío el centro-derecha tiene base en la tradición cafetera: la estructura municipal es su fuerza.',
      d: 'El Quindío se inclinó a la derecha en la presidencial de 2026: el mensaje de seguridad y campo tiene terreno ganado.' },
    '27': { n: 'Santander', tema: 'Bucaramanga, Barrancabermeja y una tradición de voto independiente',
      izq: 'En Santander la izquierda tiene voto fuerte en Barrancabermeja y el Magdalena Medio: en el área de Bucaramanga compite en cancha más difícil.',
      ci: 'En Santander el voto independiente tiene tradición: el centro-izquierda juega bien si habla de transparencia y gestión.',
      c: 'Santander premia al que se presenta como independiente: el centro tiene espacio si no suena a partido tradicional.',
      cd: 'En Santander el centro-derecha tiene base en los municipios: el mensaje de gestión y seguridad funciona.',
      d: 'En Santander la derecha tiene voto fuerte en el área metropolitana de Bucaramanga: el reto es no dividirse con los independientes de la misma orilla.' },
    '28': { n: 'Sucre', tema: 'las sabanas, la ganadería, Sincelejo y estructuras familiares tradicionales',
      izq: 'En Sucre la izquierda tiene voto campesino y en los barrios de Sincelejo: la presencia es lo que se premia.',
      ci: 'En Sucre el centro-izquierda compite con estructuras muy aceitadas: su espacio es el voto de opinión urbano.',
      c: 'En Sucre el centro tiene su puerta en el votante joven de Sincelejo, que pide empleo y transparencia.',
      cd: 'En Sucre el centro-derecha se mueve en estructuras regionales: el trabajo municipio por municipio es la clave.',
      d: 'En Sucre la derecha tiene voto en la zona ganadera: seguridad y apoyo al campo son el mensaje.' },
    '29': { n: 'Tolima', tema: 'el agro, el arroz, Ibagué y una tradición liberal fuerte',
      izq: 'En el Tolima la izquierda tiene voto campesino en el sur y en barrios de Ibagué: el mensaje de campo y tierra funciona.',
      ci: 'En el Tolima el centro-izquierda tiene espacio en el voto de opinión de Ibagué.',
      c: 'El Tolima tiene una tradición liberal muy fuerte: el centro juega de local si habla con ese votante.',
      cd: 'En el Tolima el centro-derecha tiene base conservadora en los municipios: la estructura existe.',
      d: 'En el Tolima la derecha tiene voto rural y arrocero: seguridad y apoyo al productor son el mensaje.' },
    '31': { n: 'Valle del Cauca', tema: 'Cali, Buenaventura, el norte del Valle y la seguridad',
      izq: 'En el Valle la izquierda ganó Cali en la presidencial de 2026 y es fuerte en Buenaventura: la meta está en el oriente de Cali y en el Pacífico.',
      ci: 'En el Valle el centro-izquierda tiene un voto de opinión grande en Cali: se gana con propuestas de ciudad y de seguridad a la vez.',
      c: 'En el Valle el centro compite por el votante caleño que no se casa con nadie: gestión y seguridad son su mensaje.',
      cd: 'En el Valle el centro-derecha tiene base en el norte del departamento y en la clase media: la estructura ayuda.',
      d: 'En el Valle la derecha tiene voto en el sur de Cali y en el norte del departamento: seguridad es el mensaje que llega.' },
    '40': { n: 'Arauca', tema: 'el petróleo, la frontera y la violencia de los grupos armados',
      izq: 'En Arauca la izquierda tiene voto rural, pero compite en un territorio golpeado por la violencia: la seguridad de sus testigos es parte de la campaña.',
      ci: 'En Arauca el centro-izquierda tiene espacio en el voto urbano que pide paz y que las regalías se vean.',
      c: 'En Arauca el centro tiene su puerta en el votante cansado de la violencia, que pide Estado.',
      cd: 'En Arauca el centro-derecha tiene base en la capital y en el sector productivo: seguridad es el mensaje.',
      d: 'En Arauca la derecha habla de seguridad en un territorio que la vive a diario: es el tema, y su votante lo espera.' },
    '44': { n: 'Caquetá', tema: 'la deforestación, la ganadería y el posconflicto',
      izq: 'En el Caquetá la izquierda tiene voto en el posconflicto y en el campo: el mensaje de tierra y oportunidades funciona.',
      ci: 'En el Caquetá el centro-izquierda tiene espacio en Florencia y en el voto que pide cuidar la selva sin castigar al campesino.',
      c: 'En el Caquetá el centro compite por el votante pragmático de Florencia: gestión y vías son su mensaje.',
      cd: 'En el Caquetá el centro-derecha tiene base ganadera y en los municipios: la estructura existe.',
      d: 'En el Caquetá la derecha tiene voto ganadero: seguridad y apoyo al productor le hablan directo.' },
    '46': { n: 'Casanare', tema: 'el petróleo, la ganadería y Yopal',
      izq: 'En las presidenciales Casanare es cancha difícil para la izquierda: su voto está en los barrios de Yopal y en el trabajador del petróleo.',
      ci: 'En Casanare el centro-izquierda compite en territorio de derecha: su espacio es el voto urbano de Yopal.',
      c: 'En Casanare el centro tiene su puerta en el votante que pide que la plata del petróleo se vea.',
      cd: 'En Casanare el centro-derecha tiene base amplia: el mensaje de gestión y regalías funciona.',
      d: 'En las presidenciales Casanare vota fuerte por la derecha, pero en lo local ese voto se reparte entre muchas listas: el reto es juntarlo.' },
    '48': { n: 'La Guajira', tema: 'el agua, la niñez wayuu, el carbón y la energía eólica',
      izq: 'En La Guajira la izquierda tiene voto en Riohacha y en comunidades wayuu: el mensaje de agua y derechos es el que llega.',
      ci: 'En La Guajira el centro-izquierda tiene espacio en el voto de opinión de Riohacha, cansado de la corrupción.',
      c: 'En La Guajira el centro compite con estructuras fuertes: el votante que pide agua y transparencia es su puerta.',
      cd: 'En La Guajira el centro-derecha tiene base en las estructuras municipales: la presencia es la clave.',
      d: 'En La Guajira la derecha habla de orden y de que la plata llegue: en un territorio que pide Estado, ese es el mensaje.' },
    '52': { n: 'Meta', tema: 'los Llanos, la agroindustria, Villavicencio y las vías',
      izq: 'En el Meta la izquierda tiene voto en los barrios de Villavicencio y en el campo del Ariari: se gana con presencia.',
      ci: 'En el Meta el centro-izquierda tiene espacio en el voto de opinión de Villavicencio.',
      c: 'En el Meta el centro tiene su puerta en el votante que pide la vía al Llano y empleo.',
      cd: 'En el Meta el centro-derecha tiene base amplia en los municipios: gestión y vías son el mensaje.',
      d: 'En las presidenciales el Meta vota fuerte por la derecha: seguridad y apoyo al productor llanero le hablan directo, y en lo local hay que juntar ese voto.' },
    '56': { n: 'San Andrés y Providencia', tema: 'el pueblo raizal, la conectividad con el continente y la reconstrucción',
      izq: 'En San Andrés la conversación es raizal y de soberanía sobre el mar: cualquier familia política tiene que hablar ese idioma primero.',
      ci: 'En San Andrés el centro-izquierda tiene espacio si pone al pueblo raizal en el centro del mensaje.',
      c: 'En San Andrés el centro compite por un votante que pide conectividad, agua y trabajo: lo local manda sobre lo nacional.',
      cd: 'En San Andrés el centro-derecha tiene base en el sector turístico y comercial: la clave es hablar de empleo.',
      d: 'En San Andrés la derecha tiene voto en el comercio y el turismo: el mensaje de seguridad y soberanía funciona.' },
    '50': { n: 'Guainía', tema: 'los pueblos indígenas, la minería ilegal y la conectividad',
      izq: 'En el Guainía el electorado es pequeño y mayoritariamente indígena: la campaña se hace comunidad por comunidad, y hablando de su territorio.',
      ci: 'En el Guainía el centro-izquierda tiene espacio si habla de cuidar el territorio frente a la minería ilegal.',
      c: 'En el Guainía cada voto cuenta y el candidato se conoce en persona: la presencia pesa más que el partido.',
      cd: 'En el Guainía el centro-derecha tiene base en Inírida: gestión y conectividad son el mensaje.',
      d: 'En el Guainía la derecha habla de seguridad frente a la minería ilegal: es un tema que la gente vive.' },
    '54': { n: 'Guaviare', tema: 'la deforestación, el posconflicto y San José',
      izq: 'En el Guaviare la izquierda tiene voto en el posconflicto y en el campo: tierra y oportunidades son el mensaje.',
      ci: 'En el Guaviare el centro-izquierda tiene espacio si habla de cuidar la selva sin castigar al campesino.',
      c: 'En el Guaviare el electorado es pequeño y muy territorial: la presencia pesa más que el partido.',
      cd: 'En el Guaviare el centro-derecha tiene base en San José: gestión y vías son el mensaje.',
      d: 'En el Guaviare la derecha tiene voto ganadero: seguridad y apoyo al productor le hablan directo.' },
    '60': { n: 'Amazonas', tema: 'Leticia, la frontera con Brasil y Perú, los pueblos indígenas y el turismo',
      izq: 'En el Amazonas el electorado es pequeño y en buena parte indígena: la campaña se hace en persona y hablando del territorio.',
      ci: 'En el Amazonas el centro-izquierda tiene espacio si habla de cuidar la selva y de la vida en la frontera.',
      c: 'En el Amazonas cada voto cuenta y la presencia es lo que decide: la etiqueta pesa poco.',
      cd: 'En el Amazonas el centro-derecha tiene base en Leticia y en el comercio: turismo y conectividad son el mensaje.',
      d: 'En el Amazonas la derecha habla de seguridad en la frontera: es un tema que la gente conoce.' },
    '64': { n: 'Putumayo', tema: 'el petróleo, los cultivos y la frontera con Ecuador',
      izq: 'En el Putumayo la izquierda tiene voto campesino y en el posconflicto: el mensaje de sustitución y oportunidades funciona.',
      ci: 'En el Putumayo el centro-izquierda tiene espacio en Mocoa y en el voto que pide Estado sin violencia.',
      c: 'En el Putumayo el centro tiene su puerta en el votante que pide vías y empleo.',
      cd: 'En el Putumayo el centro-derecha tiene base en los municipios: la estructura cuenta.',
      d: 'En el Putumayo la derecha habla de seguridad y frontera: es el tema, y su votante lo espera.' },
    '68': { n: 'Vaupés', tema: 'los pueblos indígenas, el aislamiento y la conectividad',
      izq: 'En las presidenciales el Vaupés vota fuerte por la izquierda, y su electorado es mayoritariamente indígena: la campaña se hace con las comunidades.',
      ci: 'En el Vaupés el centro-izquierda tiene espacio si habla de salud, educación y conectividad para las comunidades.',
      c: 'En el Vaupés el electorado es muy pequeño y todo se hace en persona: la presencia decide.',
      cd: 'En el Vaupés el centro-derecha tiene base en Mitú: gestión y conectividad son el mensaje.',
      d: 'En el Vaupés la derecha compite en cancha difícil: el mensaje que llega es el de presencia del Estado.' },
    '72': { n: 'Vichada', tema: 'la Orinoquía, la frontera con Venezuela y la conectividad',
      izq: 'En el Vichada la izquierda tiene voto en comunidades indígenas y en Puerto Carreño: la presencia decide.',
      ci: 'En el Vichada el centro-izquierda tiene espacio si habla de vías, agua y conectividad.',
      c: 'En el Vichada el electorado es pequeño: el candidato se conoce en persona y eso pesa más que la etiqueta.',
      cd: 'En el Vichada el centro-derecha tiene base en la capital y en el sector productivo: gestión es el mensaje.',
      d: 'En el Vichada la derecha habla de frontera y seguridad: es un tema que la gente vive.' },
    '17': { n: 'Chocó', tema: 'la falta de servicios públicos, el Atrato y el abandono del Estado',
      izq: 'En las presidenciales el Chocó vota fuerte por la izquierda: la meta se hace con las organizaciones afro e indígenas y hablando de agua, luz y vías.',
      ci: 'En el Chocó el centro-izquierda tiene espacio en Quibdó, en el voto que pide gestión transparente.',
      c: 'En el Chocó el centro compite por el votante que pide que las cosas lleguen: servicios públicos es el tema.',
      cd: 'En el Chocó el centro-derecha tiene base en las estructuras municipales: la presencia es la clave.',
      d: 'En el Chocó la derecha compite en cancha difícil: el mensaje de presencia del Estado y seguridad es el que puede llegar.' },
  };

  /* ── 1b. Ciudades principales: mandan sobre su departamento ───────────── */
  const CIUDADES = {
    MEDELLIN: { dep: '01', n: 'Medellín', tema: 'seguridad, movilidad y la diferencia entre las laderas y el centro-sur de la ciudad',
      izq: 'En Medellín la izquierda tiene su voto en las comunas de ladera —Popular, Santa Cruz, Manrique, Robledo—: la meta se hace ahí, comuna por comuna.',
      ci: 'En Medellín el centro-izquierda tiene un voto de opinión que se cansó de la polarización: gestión y cultura ciudadana son su mensaje.',
      c: 'En Medellín el centro compite con una derecha muy fuerte: el votante de Laureles y Belén que pide gestión sin pelea es su puerta.',
      cd: 'En Medellín el centro-derecha comparte base con la derecha: la diferencia se hace con propuestas concretas por comuna.',
      d: 'Medellín vota fuerte por la derecha: El Poblado, Laureles y Belén votan fuerte por esa orilla; el reto es que el voto salga y no se divida.' },
    CALI: { dep: '31', n: 'Cali', tema: 'la seguridad, el oriente de la ciudad y la herencia del estallido de 2021',
      izq: 'En Cali la izquierda ganó la presidencial de 2026 con fuerza: el oriente —el Distrito de Aguablanca— y las laderas son su base.',
      ci: 'En Cali el centro-izquierda tiene espacio en el voto joven y de opinión que pide seguridad sin estigmatizar.',
      c: 'En Cali el centro compite por el votante cansado de la pelea: gestión y seguridad son su mensaje.',
      cd: 'En Cali el centro-derecha tiene base en el sur y en la clase media: seguridad y gestión funcionan.',
      d: 'En Cali la derecha tiene su voto en el sur —Pance, Ciudad Jardín— y en la clase media que pide seguridad: ese es el mensaje.' },
    BARRANQUILLA: { dep: '03', n: 'Barranquilla', tema: 'servicios públicos, el río y estructuras políticas de larga data',
      izq: 'En Barranquilla la izquierda dio el mayor giro de las grandes ciudades en 2026 y ganó la segunda vuelta: los barrios del sur y el suroccidente son su base.',
      ci: 'En Barranquilla el centro-izquierda compite con una estructura local muy fuerte: su espacio es el voto de opinión que pide servicios.',
      c: 'En Barranquilla el centro tiene su puerta en el votante que quiere resultados sin padrinos.',
      cd: 'En Barranquilla el centro-derecha tiene tradición de gobierno local: el mensaje de obra está probado.',
      d: 'En Barranquilla la derecha tiene voto en el norte —Riomar y alrededores—: seguridad y gestión son el mensaje.' },
    CARTAGENA: { dep: '05', n: 'Cartagena', tema: 'la corrupción local, la brecha social y el turismo',
      izq: 'En Cartagena la izquierda tiene su voto en las Unidades Comuneras del sur y en la zona rural e insular: ahí se gana la meta.',
      ci: 'En Cartagena el centro-izquierda tiene espacio en el voto que se cansó de la corrupción: transparencia es su mensaje.',
      c: 'En Cartagena el centro compite por el votante que pide que la plata del turismo llegue a los barrios.',
      cd: 'En Cartagena el centro-derecha tiene base en la clase media y el comercio: gestión y seguridad funcionan.',
      d: 'En Cartagena la derecha tiene voto en los barrios de clase media y alta: seguridad y orden son el mensaje.' },
    BUCARAMANGA: { dep: '27', n: 'Bucaramanga', tema: 'la seguridad, la movilidad del área metropolitana y el voto independiente',
      izq: 'En Bucaramanga la izquierda juega en cancha difícil: su voto está en el norte y en los barrios populares.',
      ci: 'Bucaramanga premia al independiente: el centro-izquierda juega bien si no suena a partido tradicional.',
      c: 'En Bucaramanga el voto independiente es grande: el centro tiene espacio si se presenta así.',
      cd: 'En Bucaramanga el centro-derecha tiene base amplia: seguridad y gestión son su mensaje.',
      d: 'En Bucaramanga la derecha tiene voto fuerte: el reto es no dividirse con los independientes de la misma orilla.' },
    CUCUTA: { dep: '25', n: 'Cúcuta', tema: 'la frontera, la migración y el empleo',
      izq: 'En Cúcuta la izquierda tiene su voto en los barrios populares: el mensaje de empleo y frontera abierta llega.',
      ci: 'En Cúcuta el centro-izquierda compite en cancha de derecha: su espacio es el voto de opinión.',
      c: 'En Cúcuta el centro tiene su puerta en el votante que pide comercio fronterizo y empleo.',
      cd: 'En Cúcuta el centro-derecha tiene base amplia: seguridad y comercio son su mensaje.',
      d: 'En las presidenciales Cúcuta vota fuerte por la derecha: en lo local el reto es que ese voto no se divida.' },
    PEREIRA: { dep: '24', n: 'Pereira', tema: 'el empleo, la movilidad y la seguridad',
      izq: 'En Pereira la izquierda tiene voto en los barrios populares, pero la ciudad giró a la derecha en 2026: hay que ir a buscarlo.',
      ci: 'En Pereira el centro-izquierda tiene espacio en el voto universitario y de opinión.',
      c: 'En Pereira el centro dialoga con un electorado pragmático: gestión y empleo son su mensaje.',
      cd: 'En Pereira el centro-derecha tiene base en la tradición de partido: la estructura ayuda.',
      d: 'Pereira se inclinó a la derecha en 2026: el mensaje de seguridad y empleo tiene terreno ganado.' },
    MANIZALES: { dep: '09', n: 'Manizales', tema: 'la universidad, la movilidad y una política de mucha tradición',
      izq: 'En Manizales la izquierda crece sobre todo en el voto universitario y joven: ahí está la meta.',
      ci: 'En Manizales el centro-izquierda tiene un voto de opinión fuerte en la ciudad universitaria.',
      c: 'En Manizales el centro dialoga con un electorado educado y de tradición: gestión y datos le llegan.',
      cd: 'En Manizales el centro-derecha tiene base conservadora histórica: la estructura existe.',
      d: 'En Manizales la derecha tiene voto fuerte en la clase media: seguridad y gestión son el mensaje.' },
    IBAGUE: { dep: '29', n: 'Ibagué', tema: 'el empleo, la movilidad y la tradición liberal del Tolima',
      izq: 'En Ibagué la izquierda tiene voto en los barrios populares: empleo y costo de vida son el mensaje.',
      ci: 'En Ibagué el centro-izquierda tiene espacio en el voto de opinión que pide gestión transparente.',
      c: 'Ibagué tiene tradición liberal: el centro juega de local si habla con ese votante.',
      cd: 'En Ibagué el centro-derecha tiene base en la tradición conservadora: la estructura ayuda.',
      d: 'En Ibagué la derecha tiene voto en la clase media: seguridad y empleo son el mensaje.' },
    VILLAVICENCIO: { dep: '52', n: 'Villavicencio', tema: 'la vía al Llano, el crecimiento de la ciudad y la seguridad',
      izq: 'En Villavicencio la izquierda tiene voto en los barrios populares que crecieron rápido: presencia y servicios son la clave.',
      ci: 'En Villavicencio el centro-izquierda tiene espacio en el voto de opinión.',
      c: 'En Villavicencio el centro compite por un votante nuevo, sin lealtad de partido.',
      cd: 'En Villavicencio el centro-derecha tiene base amplia: gestión y vías son el mensaje.',
      d: 'En las presidenciales Villavicencio vota fuerte por la derecha: seguridad y la vía al Llano le hablan directo.' },
    SANTAMARTA: { dep: '21', n: 'Santa Marta', tema: 'el agua, el turismo y un movimiento político regional propio',
      izq: 'En Santa Marta la izquierda regional tiene estructura propia: competir en esa orilla exige diferenciarse o sumarse.',
      ci: 'En Santa Marta el centro-izquierda tiene espacio en el voto de opinión que pide agua y transparencia.',
      c: 'En Santa Marta el tema es el agua: quien lo resuelva en su mensaje tiene al votante indeciso.',
      cd: 'En Santa Marta el centro-derecha tiene base en el comercio y el turismo.',
      d: 'En Santa Marta la derecha compite contra un movimiento regional fuerte: su voto está en la clase media.' },
    PASTO: { dep: '23', n: 'Pasto', tema: 'la identidad del sur, la movilidad y el empleo',
      izq: 'En las presidenciales Pasto vota fuerte por la izquierda, con identidad propia: el sur como región es el mensaje.',
      ci: 'En Pasto el centro-izquierda tiene un voto de opinión grande y exigente.',
      c: 'En Pasto el centro compite con una izquierda fuerte: gestión y empleo son su puerta.',
      cd: 'En Pasto el centro-derecha tiene base conservadora tradicional: la estructura existe.',
      d: 'En Pasto la derecha compite en cancha difícil: seguridad y gestión son lo que puede llegar.' },
    MONTERIA: { dep: '13', n: 'Montería', tema: 'el río Sinú, el crecimiento de la ciudad y la política tradicional',
      izq: 'En Montería la izquierda tiene voto en los barrios populares y en la periferia: presencia es la clave.',
      ci: 'En Montería el centro-izquierda tiene espacio en el voto joven que pide renovación.',
      c: 'En Montería el centro compite con estructuras fuertes: el voto de opinión es su terreno.',
      cd: 'En Montería el centro-derecha tiene tradición de gobierno: la gestión urbana es su mensaje.',
      d: 'En Montería la derecha tiene voto fuerte en la clase media y la zona ganadera: orden y gestión son el mensaje.' },
    NEIVA: { dep: '19', n: 'Neiva', tema: 'el empleo, la seguridad y el agro del Huila',
      izq: 'En Neiva la izquierda tiene voto en los barrios populares: empleo y costo de vida son el mensaje.',
      ci: 'En Neiva el centro-izquierda tiene espacio en el voto de opinión y joven.',
      c: 'En Neiva el centro dialoga con un electorado pragmático: gestión es su mensaje.',
      cd: 'En Neiva el centro-derecha tiene base conservadora: la estructura ayuda.',
      d: 'En Neiva la derecha tiene voto en la clase media: seguridad y empleo son el mensaje.' },
    POPAYAN: { dep: '11', n: 'Popayán', tema: 'la ciudad universitaria en medio de un Cauca en conflicto',
      izq: 'En Popayán la izquierda tiene voto universitario y en los barrios populares, en un departamento donde es muy fuerte.',
      ci: 'En Popayán el centro-izquierda tiene espacio en el voto que pide paz con institucionalidad.',
      c: 'En Popayán el centro tiene su puerta en el votante que quiere seguridad y paz a la vez.',
      cd: 'En Popayán el centro-derecha tiene base en la tradición conservadora de la ciudad.',
      d: 'En Popayán está buena parte del voto de derecha del Cauca: seguridad es el mensaje que llega.' },
    ARMENIA: { dep: '26', n: 'Armenia', tema: 'el turismo, el empleo y el café',
      izq: 'En Armenia la izquierda tiene voto en los barrios populares, en un departamento que giró a la derecha en 2026.',
      ci: 'En Armenia el centro-izquierda tiene espacio en el voto de opinión.',
      c: 'En Armenia el centro compite por un votante pragmático: turismo y empleo son su mensaje.',
      cd: 'En Armenia el centro-derecha tiene base en la tradición cafetera.',
      d: 'Armenia se inclinó a la derecha en 2026: seguridad y empleo tienen terreno ganado.' },
    VALLEDUPAR: { dep: '12', n: 'Valledupar', tema: 'el agua, el empleo y lo que dejan las regalías',
      izq: 'En Valledupar la izquierda tiene voto en los barrios populares: empleo y regalías son el mensaje.',
      ci: 'En Valledupar el centro-izquierda tiene espacio en el voto urbano que pide renovación.',
      c: 'En Valledupar el centro compite con estructuras regionales: su puerta es el voto de opinión.',
      cd: 'En Valledupar el centro-derecha tiene base en la tradición política regional.',
      d: 'En Valledupar la derecha tiene voto en la clase media y ganadera: orden y gestión son el mensaje.' },
    SINCELEJO: { dep: '28', n: 'Sincelejo', tema: 'el empleo y la política tradicional de las sabanas',
      izq: 'En Sincelejo la izquierda tiene voto en los barrios populares: presencia es la clave.',
      ci: 'En Sincelejo el centro-izquierda tiene espacio en el voto joven.',
      c: 'En Sincelejo el centro compite con estructuras fuertes: el voto de opinión es su terreno.',
      cd: 'En Sincelejo el centro-derecha se mueve en estructuras regionales de larga data.',
      d: 'En Sincelejo la derecha tiene voto en la clase media: orden y gestión son el mensaje.' },
    TUNJA: { dep: '07', n: 'Tunja', tema: 'la universidad, el empleo y la tradición independiente de Boyacá',
      izq: 'En Tunja la izquierda tiene voto universitario y joven: ahí está la meta.',
      ci: 'Tunja tiene tradición de voto verde e independiente: el centro-izquierda juega de local.',
      c: 'En Tunja el centro dialoga con un electorado educado: gestión y datos le llegan.',
      cd: 'En Tunja el centro-derecha tiene base conservadora tradicional.',
      d: 'En Tunja la derecha tiene voto en la clase media: seguridad y gestión son el mensaje.' },
    QUIBDO: { dep: '17', n: 'Quibdó', tema: 'los servicios públicos, el empleo y la seguridad',
      izq: 'En las presidenciales Quibdó vota fuerte por la izquierda: agua, luz y empleo son el mensaje.',
      ci: 'En Quibdó el centro-izquierda tiene espacio en el voto que pide gestión transparente.',
      c: 'En Quibdó el centro compite por el votante que pide que las cosas lleguen.',
      cd: 'En Quibdó el centro-derecha tiene base en las estructuras locales.',
      d: 'En Quibdó la derecha compite en cancha difícil: presencia del Estado y seguridad es lo que puede llegar.' },
    RIOHACHA: { dep: '48', n: 'Riohacha', tema: 'el agua, la niñez y la corrupción local',
      izq: 'En Riohacha la izquierda tiene voto en los barrios populares y en comunidades wayuu: agua y derechos son el mensaje.',
      ci: 'En Riohacha el centro-izquierda tiene espacio en el voto cansado de la corrupción.',
      c: 'En Riohacha el centro tiene su puerta en el votante que pide agua y transparencia.',
      cd: 'En Riohacha el centro-derecha tiene base en las estructuras locales.',
      d: 'En Riohacha la derecha habla de orden y de que la plata llegue: ese es el mensaje.' },
    SOACHA: { dep: '15', n: 'Soacha', tema: 'el transporte hacia Bogotá, el costo de vida y los barrios que crecieron sin servicios',
      izq: 'En Soacha la izquierda tiene un voto grande y popular: transporte y costo de vida son el mensaje.',
      ci: 'En Soacha el centro-izquierda tiene espacio en el voto joven que trabaja en Bogotá.',
      c: 'En Soacha el centro compite por un votante nuevo, sin lealtad de partido.',
      cd: 'En Soacha el centro-derecha tiene base en la estructura municipal.',
      d: 'En Soacha la derecha habla de seguridad: es el tema que la gente vive a diario.' },
    BUENAVENTURA: { dep: '31', n: 'Buenaventura', tema: 'el puerto, la violencia y la falta de servicios',
      izq: 'En las presidenciales Buenaventura vota fuerte por la izquierda: agua, empleo del puerto y seguridad son el mensaje.',
      ci: 'En Buenaventura el centro-izquierda tiene espacio en el voto que pide que el puerto deje algo en la ciudad.',
      c: 'En Buenaventura el centro compite por el votante que pide que las cosas lleguen.',
      cd: 'En Buenaventura el centro-derecha tiene base en el comercio y el puerto.',
      d: 'En Buenaventura la derecha compite en cancha difícil: seguridad es lo que puede llegar.' },
  };
  /* Bogotá es municipio y departamento a la vez: una sola entrada. */
  CIUDADES.BOGOTA = Object.assign({ dep: '16' }, DEPARTAMENTOS['16']);
  CIUDADES.BOGOTADC = CIUDADES.BOGOTA;

  /* ── 2. Partidos: cómo se ubica cada uno ──────────────────────────────── */
  const PARTIDOS = [
    [/PACTO HISTORICO|COLOMBIA HUMANA/, 'el Pacto Histórico llega como la fuerza del gobierno anterior: su mensaje es de derechos sociales y de defender lo que se hizo'],
    [/POLO DEMOCRATICO/, 'el Polo es la izquierda de trayectoria larga: su voto es de convicción, pequeño pero fiel'],
    [/ALIANZA VERDE/, 'la Alianza Verde es una casa amplia de independientes: su voto es de opinión y castiga la corrupción'],
    [/NUEVO LIBERALISMO/, 'el Nuevo Liberalismo se presenta como renovación del liberalismo: su votante es urbano, de opinión y exige propuesta'],
    [/DIGNIDAD/, 'Dignidad y Compromiso es centro de opinión: su votante es educado, urbano y pide coherencia'],
    [/EN MARCHA/, 'En Marcha es centro-izquierda moderado: su voto es de opinión y pragmático'],
    [/LIBERAL COLOMBIANO|PARTIDO LIBERAL/, 'el Partido Liberal tiene la estructura más extendida del país: su fuerza está en la presencia municipal y en sus líderes locales'],
    [/PARTIDO DE LA U|UNION POR LA GENTE/, 'La U es un partido de gobierno local y regional: su voto se mueve por la gestión y por la estructura'],
    [/CONSERVADOR/, 'el Partido Conservador tiene raíces en los municipios y en el voto de tradición: familia, orden y región'],
    [/CAMBIO RADICAL/, 'Cambio Radical es partido de gestión y de obra, con estructuras regionales fuertes'],
    [/CENTRO DEMOCRATICO/, 'el Centro Democrático es la derecha de identidad: su votante es fiel y se moviliza con seguridad y firmeza'],
    [/CREEMOS/, 'Creemos es la derecha que nació en Medellín: su mensaje es gestión con firmeza'],
    [/SALVACION NACIONAL/, 'Salvación Nacional es la derecha conservadora de valores: su votante es de convicción'],
    [/LIGA/, 'la Liga de Gobernantes Anticorrupción se presenta como antipolítica: su voto es de protesta contra los partidos'],
    [/MIRA/, 'MIRA tiene un voto disciplinado y de base comunitaria: organización antes que opinión'],
    [/COLOMBIA JUSTA LIBRES/, 'Colombia Justa Libres tiene un voto de base cristiana, organizado desde las iglesias'],
    [/COMUNES/, 'Comunes es el partido del Acuerdo de Paz: su voto está en el posconflicto'],
    [/FUERZA CIUDADANA/, 'Fuerza Ciudadana es un movimiento regional con estructura propia en el Caribe'],
    [/AICO|AUTORIDADES INDIGENAS/, 'AICO representa a autoridades indígenas: su voto es comunitario'],
    [/MAIS|ALTERNATIVO INDIGENA/, 'MAIS nació del movimiento indígena y hoy presta aval a candidaturas muy diversas: su huella depende del territorio'],
    [/ASI|ALIANZA SOCIAL INDEPENDIENTE/, 'la ASI presta aval a candidaturas muy distintas: su huella depende de quién la lleva en cada territorio'],
    [/ESPERANZA DEMOCRATICA/, 'Esperanza Democrática es centro-izquierda de opinión'],
    [/OXIGENO/, 'Verde Oxígeno es centro de opinión y de causa ambiental'],
  ];
  const PB = () => global.PartidosBloques;
  function partido(nombre) {
    const k = PB()?.norm ? PB().norm(nombre) : String(nombre || '').toUpperCase();
    const hit = PARTIDOS.find(([re]) => re.test(k));
    return hit ? hit[1] : '';
  }

  /* ── Resolver la región ───────────────────────────────────────────────── */
  function region({ dep, municipio } = {}) {
    const d = String(dep || '').replace(/\D/g, '').padStart(2, '0');
    const m = norm(municipio);
    if (m) { const c = CIUDADES[m]; if (c && (!dep || c.dep === d)) return c; }
    return DEPARTAMENTOS[d] || null;
  }
  /* La lectura por espectro del lugar; '' si no hay región o familia. */
  function linea({ dep, municipio, bloque } = {}) {
    const r = region({ dep, municipio });
    return (r && bloque && r[bloque]) || '';
  }
  function tema({ dep, municipio } = {}) { return region({ dep, municipio })?.tema || ''; }

  /* ── 3. El dato medido ────────────────────────────────────────────────────
     Asamblea 2023 por departamento, o por municipio si la campaña es
     municipal: es la única elección de ese año con el voto por partido en
     todos los municipios. En Bogotá, que no tiene Asamblea, el Concejo. */
  const S3 = () => (global.RRData?.publicUrl?.('congreso-2026/output')) || 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const cache = new Map();
  const json = url => { if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : null).catch(() => null)); return cache.get(url); };
  const LABEL = { izq: 'la izquierda', ci: 'el centro-izquierda', c: 'el centro', cd: 'el centro-derecha', d: 'la derecha' };
  const pct = x => `${Math.round(x * 100)} %`;
  const orden = n => ['', 'primera', 'segunda', 'tercera', 'cuarta', 'quinta'][n] || `${n}.ª`;

  async function partidosDe({ dep, municipio, codigoMunicipio }) {
    const d = String(dep || '').replace(/\D/g, '').padStart(2, '0');
    if (d === '16') {
      const r = await json(`${S3()}/concejo-2023/resultados-concejo-2023.json`);
      const c = r?.data?.['16-001']?.comunas; if (!c) return null;
      const t = {}; Object.values(c).forEach(u => (u.partidos || []).forEach(([n, v]) => { t[n] = (t[n] || 0) + Number(v || 0); }));
      return { lista: Object.entries(t), lugar: 'Bogotá', eleccion: 'el Concejo' };
    }
    const r = await json(`${S3()}/asamblea-2023/dep/${d}.json`); if (!r) return null;
    const mun = codigoMunicipio ? String(codigoMunicipio).padStart(3, '0') : '';
    if (mun && r.comunas?.[mun]) return { lista: r.comunas[mun].partidos || [], lugar: r.comunas[mun].name || municipio, eleccion: 'la Asamblea', municipal: true };
    const t = {}; Object.values(r.comunas || {}).forEach(u => (u.partidos || []).forEach(([n, v]) => { t[n] = (t[n] || 0) + Number(v || 0); }));
    return { lista: Object.entries(t), lugar: r.name || '', eleccion: 'la Asamblea' };
  }

  async function dato({ dep, municipio, codigoMunicipio, bloque, partido: nombre } = {}) {
    const P = await partidosDe({ dep, municipio, codigoMunicipio }); if (!P || !P.lista.length) return '';
    const total = P.lista.reduce((s, [, v]) => s + Number(v || 0), 0); if (!total) return '';
    /* El nombre bonito sale del diccionario (con tildes); el del JSON viene en
       mayúsculas y sin ellas. Con dato municipal, se dice el municipio y la
       elección por separado: «la Asamblea de Medellín» no existe. */
    const bonito = P.municipal ? CIUDADES[norm(municipio)]?.n : (region({ dep })?.n || '');
    const lugar = bonito
      || String(P.lugar || '').toLowerCase().replace(/(^|[\s.-])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
    const donde = P.municipal ? `en ${lugar}, en la votación a la Asamblea` : `en ${P.eleccion} de ${lugar}`;
    /* Las frases escritas hablan del voto nacional; esta es la foto LOCAL, que
       a veces es otra (en Casanare la derecha arrasa en presidenciales y queda
       tercera en la Asamblea). Se dice que es local para que no parezca una
       contradicción. */
    /* Con partido: su puesto y su porcentaje, si se encuentra en la lista. */
    if (nombre && PB()?.norm) {
      const k = PB().norm(nombre);
      const orden_ = [...P.lista].sort((a, b) => b[1] - a[1]);
      const i = orden_.findIndex(([n]) => { const x = PB().norm(n); return x === k || x.includes(k) || k.includes(x); });
      if (i >= 0) {
        const [, v] = orden_[i];
        return `En lo local, en 2023, ${donde}, ese partido fue la ${orden(i + 1)} fuerza, con el ${pct(v / total)} de los votos por partido.`;
      }
    }
    /* Sin partido (o sin encontrarlo): la fuerza de la familia. */
    if (!bloque || !LABEL[bloque] || !PB()?.bloqueDeOrganizacion) return '';
    const por = {}; P.lista.forEach(([n, v]) => { const b = PB().bloqueDeOrganizacion(n) || 'sc'; por[b] = (por[b] || 0) + Number(v || 0); });
    const propia = por[bloque] || 0;
    const rango = Object.entries(por).filter(([b]) => b !== 'sc').sort((a, b) => b[1] - a[1]).findIndex(([b]) => b === bloque) + 1;
    /* Menos del 1 % no es un puesto en el ranking: es no haber tenido lista. */
    if (propia / total < .01) return `En lo local, en 2023, ${donde}, ${LABEL[bloque]} casi no tuvo lista propia (menos del 1 % de los votos): aquí se empieza desde muy abajo, y la meta se mide con las familias vecinas.`;
    return `En lo local, en 2023, ${donde}, ${LABEL[bloque]} sacó el ${pct(propia / total)} de los votos${rango ? ` y fue la ${orden(rango)} familia política` : ''}.`;
  }

  global.C360Frases = { DEPARTAMENTOS, CIUDADES, PARTIDOS, region, linea, tema, partido, dato };
})(window);
