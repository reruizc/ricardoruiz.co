#!/usr/bin/env python3
"""
Caudal · diccionario de EMPRESAS y GREMIOS (traductor de la búsqueda general).

El problema que resuelve: el cliente busca con el nombre de la empresa, pero
el Estado casi nunca la nombra así. Medido sobre el dataset real (jul-2026):

  «Uber» →  Congreso ....  0 títulos   (el Congreso dice "plataformas
                                        tecnológicas": ~20 proyectos)
            Ejecutivo ...  3 menciones sueltas
            Regulatorio .  1 sanción real ("UBER Colombia S.A.S",
                           Supertransporte) + 3 FALSOS por substring
                           ("UBERNETH URANGO", "YUBER CALIXTO", "UBER DARIO")

O sea que no es un solo problema, son dos, y cada uno pide lo suyo:

  1. IDENTIDAD  — cómo aparece la empresa como entidad legal. Sirve al pilar
     Regulatorio (campo `sancionado`) y a Contratación (proveedor de SECOP).
     Match por PALABRA COMPLETA + lista de exclusiones, nunca por substring:
     'claro' como substring trae "CESAR AUGUSTO CLAROS MURCIA" y "PESQUERA RIO
     CLARO"; los que quedan se vetan con `excluir`.
  2. TEMA      — qué vocabulario legislativo la toca. Sirve a Congreso y
     Ejecutivo, que legislan sobre la ACTIVIDAD, no sobre la marca. Se expresa
     como llaves del tesauro SINONIMOS de caudal_core (no se repiten términos
     acá: si el tópico cambia, las ~200 empresas lo heredan).

Este módulo es DATO + funciones puras: no importa caudal_core (sería ciclo —
caudal_core importa este). La validación de que cada llave de `topicos` existe
en SINONIMOS corre en `verificar()`, que sí importa caudal_core en caliente.

Formato de cada fila (tupla de 7, compacta a propósito para que 200 entradas
sigan siendo legibles y editables):

  (k, nombre, sector, alias, topicos, entidad, excluir)

  k        · llave estable (no cambiarla: viaja al frontend y al cache)
  nombre   · como se le muestra al usuario
  sector   · agrupador propio del diccionario (no es el sector de sanciones)
  alias    · '|' · cómo la nombran el usuario y la prensa. Dispara la entrada
             desde la consulta Y matchea registros. NUNCA poner acá una palabra
             común suelta ('éxito', 'meta', 'ara'): usar la forma larga
             ('grupo exito', 'meta platforms', 'tiendas ara').
  topicos  · ',' · llaves de SINONIMOS (caudal_core) que la afectan, en orden.
             NÚCLEO vs CONTEXTO: la primera es el núcleo (la actividad que ES la
             empresa) y es la que se busca POR DEFECTO; las demás son contexto
             (la tocan, pero no la definen) y solo entran si el usuario amplía.
             Medido: «Uber» con núcleo = 35 proyectos, con todo = 124 — y los 89
             extra son 'reforma laboral' genérica. Precisión primero; ampliar es
             un clic. Una empresa con DOS actividades de verdad centrales marca
             la segunda con '*' (p. ej. Rappi: '*laboral' — el debate de los
             repartidores sí la define).
  entidad  · '|' · razón social y variantes legales (solo para matchear
             registros, no dispara desde la consulta)
  excluir  · '|' · substrings que VETAN un registro. Son los falsos positivos
             medidos, no hipótesis.

CLI:
  python3 tools/caudal/empresas.py verificar        # llaves de tópico + choques
  python3 tools/caudal/empresas.py buscar "uber"
"""
import re
import sys
import unicodedata


def _n(s):
    """Normaliza: sin tildes, minúsculas, puntuación colapsada a espacio."""
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s.lower())).strip()


# (k, nombre, sector, alias, topicos, entidad, excluir)
_RAW = [
    # ---- transporte y plataformas de reparto ----------------------------
    ('uber', 'Uber', 'transporte', 'uber|uber colombia|uber eats',
     'transporte por plataformas,laboral,competencia y consumidor',
     'uber colombia sas|uber technologies', 'uberneth|yuber|uber dario|uberto|huber'),
    ('didi', 'DiDi', 'transporte', 'didi|didi colombia|didi food',
     'transporte por plataformas,laboral', 'didi mobility', 'didier|dididier|dido'),
    ('cabify', 'Cabify', 'transporte', 'cabify', 'transporte por plataformas,laboral', '', ''),
    ('indrive', 'inDrive', 'transporte', 'indrive|in drive',
     'transporte por plataformas,laboral', '', ''),
    ('picap', 'Picap', 'transporte', 'picap', 'transporte por plataformas,laboral', '', ''),
    ('rappi', 'Rappi', 'transporte', 'rappi|rappipay|rappi colombia',
     'transporte por plataformas,*laboral,comercio y retail,competencia y consumidor',
     'rappi sas', ''),
    ('mercadolibre', 'Mercado Libre', 'tecnologia', 'mercado libre|mercadolibre|mercado pago',
     'comercio y retail,competencia y consumidor,tecnologia digital / IA', '', ''),

    # ---- telecomunicaciones ---------------------------------------------
    ('claro', 'Claro (Comcel)', 'telecom', 'claro|comcel|claro colombia',
     'telecomunicaciones,competencia y consumidor,datos personales / habeas data',
     'comcel sa|claro sa',
     # 'Claro' es también apellido y topónimo: estos son falsos positivos MEDIDOS
     # sobre sanciones.jsonl, no hipótesis. El límite de palabra no basta acá
     # porque en "CARVAJAL DE CLARO GLADYS" el apellido SÍ es palabra completa.
     'rio claro|claro de luna|claros|clarita|clara|agua clara|de claro'),
    ('movistar', 'Movistar (Telefónica)', 'telecom', 'movistar|telefonica',
     'telecomunicaciones,competencia y consumidor,datos personales / habeas data',
     'colombia telecomunicaciones', ''),
    ('tigo', 'Tigo (Millicom/UNE)', 'telecom', 'tigo|tigo une|millicom',
     'telecomunicaciones,competencia y consumidor', 'colombia movil', ''),
    ('wom', 'WOM', 'telecom', 'wom colombia|partners telecom',
     'telecomunicaciones,competencia y consumidor', 'partners telecom colombia', ''),
    ('etb', 'ETB', 'telecom', 'etb|empresa de telecomunicaciones de bogota',
     'telecomunicaciones', '', ''),
    ('directv', 'DirecTV', 'telecom', 'directv|direct tv',
     'telecomunicaciones,competencia y consumidor', '', ''),

    # ---- banca y financiero ---------------------------------------------
    ('bancolombia', 'Bancolombia', 'financiero', 'bancolombia|grupo bancolombia|bancolombia sa',
     'sector financiero,competencia y consumidor,datos personales / habeas data', '', ''),
    ('davivienda', 'Davivienda', 'financiero', 'davivienda|daviplata|grupo bolivar',
     'sector financiero,competencia y consumidor', 'banco davivienda', ''),
    ('bancodebogota', 'Banco de Bogotá', 'financiero', 'banco de bogota',
     'sector financiero', '', ''),
    ('bbva', 'BBVA Colombia', 'financiero', 'bbva', 'sector financiero', 'bbva colombia', ''),
    ('scotiabank', 'Scotiabank Colpatria', 'financiero', 'scotiabank|colpatria',
     'sector financiero', 'scotiabank colpatria', ''),
    ('itau', 'Itaú', 'financiero', 'itau', 'sector financiero', 'itau corpbanca', ''),
    ('bancopopular', 'Banco Popular', 'financiero', 'banco popular', 'sector financiero', '', ''),
    ('bancoccidente', 'Banco de Occidente', 'financiero', 'banco de occidente',
     'sector financiero', '', ''),
    ('avvillas', 'AV Villas', 'financiero', 'av villas|banco av villas', 'sector financiero', '', ''),
    ('grupoaval', 'Grupo Aval', 'financiero', 'grupo aval', 'sector financiero', '', ''),
    ('bancoagrario', 'Banco Agrario', 'financiero', 'banco agrario',
     'sector financiero,sector agropecuario', '', ''),
    ('bancocajasocial', 'Banco Caja Social', 'financiero', 'banco caja social',
     'sector financiero', '', ''),
    ('bancamia', 'Bancamía', 'financiero', 'bancamia', 'sector financiero', '', ''),
    ('bancow', 'Banco W', 'financiero', 'banco w', 'sector financiero', '', ''),
    ('bancofalabella', 'Banco Falabella', 'financiero', 'banco falabella',
     'sector financiero,comercio y retail', '', ''),
    ('bancopichincha', 'Banco Pichincha', 'financiero', 'banco pichincha', 'sector financiero', '', ''),
    ('nequi', 'Nequi', 'financiero', 'nequi', 'sector financiero,tecnologia digital / IA', '', ''),
    ('nubank', 'Nu (Nubank)', 'financiero', 'nubank|nu colombia',
     'sector financiero,tecnologia digital / IA', '', ''),
    ('lulobank', 'Lulo Bank', 'financiero', 'lulo bank', 'sector financiero', '', ''),
    ('bvc', 'Bolsa de Valores de Colombia', 'financiero', 'bolsa de valores de colombia|bvc',
     'sector financiero', '', ''),

    # ---- seguros ---------------------------------------------------------
    ('surax', 'Seguros SURA', 'seguros', 'sura|seguros sura|suramericana|grupo sura',
     'seguros,salud / EPS e IPS', 'seguros generales suramericana', ''),
    ('segurosbolivar', 'Seguros Bolívar', 'seguros', 'seguros bolivar', 'seguros', '', ''),
    ('allianz', 'Allianz', 'seguros', 'allianz', 'seguros', 'allianz seguros', ''),
    ('mapfre', 'Mapfre', 'seguros', 'mapfre', 'seguros', '', ''),
    ('liberty', 'Liberty Seguros', 'seguros', 'liberty seguros', 'seguros', '', ''),
    ('axacolpatria', 'AXA Colpatria', 'seguros', 'axa colpatria|axa', 'seguros', '', ''),
    ('previsora', 'La Previsora', 'seguros', 'la previsora|previsora sa', 'seguros', '', ''),
    ('equidad', 'La Equidad Seguros', 'seguros', 'la equidad seguros', 'seguros', '', ''),
    ('chubb', 'Chubb', 'seguros', 'chubb', 'seguros', '', ''),

    # ---- pensiones y cesantías ------------------------------------------
    ('porvenir', 'Porvenir', 'pensiones', 'porvenir', 'pensiones y cesantias,sector financiero',
     'sociedad administradora de fondos de pensiones y cesantias porvenir', 'buen porvenir'),
    ('proteccionafp', 'Protección', 'pensiones', 'proteccion sa|afp proteccion',
     'pensiones y cesantias,sector financiero', '', ''),
    ('colfondos', 'Colfondos', 'pensiones', 'colfondos', 'pensiones y cesantias', '', ''),
    ('skandia', 'Skandia', 'pensiones', 'skandia', 'pensiones y cesantias', '', ''),
    ('colpensiones', 'Colpensiones', 'pensiones', 'colpensiones', 'pensiones y cesantias', '', ''),

    # ---- salud · EPS, IPS y prestadores ---------------------------------
    ('epssura', 'EPS SURA', 'salud', 'eps sura|eps y medicina prepagada suramericana',
     'salud / EPS e IPS,farmaceutico / medicamentos', '', ''),
    ('sanitas', 'Sanitas (Keralty)', 'salud', 'sanitas|keralty|colsanitas',
     'salud / EPS e IPS', 'eps sanitas', ''),
    ('compensar', 'Compensar', 'salud', 'compensar', 'salud / EPS e IPS', '', ''),
    ('nuevaeps', 'Nueva EPS', 'salud', 'nueva eps', 'salud / EPS e IPS', '', ''),
    ('saludtotal', 'Salud Total', 'salud', 'salud total', 'salud / EPS e IPS', '', ''),
    ('coosalud', 'Coosalud', 'salud', 'coosalud', 'salud / EPS e IPS', '', ''),
    ('famisanar', 'Famisanar', 'salud', 'famisanar', 'salud / EPS e IPS', '', ''),
    ('mutualser', 'Mutual SER', 'salud', 'mutual ser', 'salud / EPS e IPS', '', ''),
    ('saviasalud', 'Savia Salud', 'salud', 'savia salud', 'salud / EPS e IPS', '', ''),
    ('medimas', 'Medimás', 'salud', 'medimas', 'salud / EPS e IPS', '', ''),
    ('colsubsidio', 'Colsubsidio', 'salud', 'colsubsidio', 'salud / EPS e IPS,*laboral', '', ''),
    ('cafam', 'Cafam', 'salud', 'cafam', 'salud / EPS e IPS,*laboral', '', ''),

    # ---- farmacéutico y droguerías --------------------------------------
    ('tecnoquimicas', 'Tecnoquímicas', 'farma', 'tecnoquimicas',
     'farmaceutico / medicamentos', '', ''),
    ('procaps', 'Procaps', 'farma', 'procaps', 'farmaceutico / medicamentos', '', ''),
    ('genfar', 'Genfar', 'farma', 'genfar', 'farmaceutico / medicamentos', '', ''),
    ('lasante', 'La Santé', 'farma', 'la sante', 'farmaceutico / medicamentos', '', ''),
    ('bayer', 'Bayer', 'farma', 'bayer',
     'farmaceutico / medicamentos,sector agropecuario', '', ''),
    ('pfizer', 'Pfizer', 'farma', 'pfizer', 'farmaceutico / medicamentos', '', ''),
    ('abbott', 'Abbott', 'farma', 'abbott', 'farmaceutico / medicamentos', '', ''),
    ('novartis', 'Novartis', 'farma', 'novartis', 'farmaceutico / medicamentos', '', ''),
    ('sanofi', 'Sanofi', 'farma', 'sanofi', 'farmaceutico / medicamentos', '', ''),
    ('roche', 'Roche', 'farma', 'roche', 'farmaceutico / medicamentos', '', ''),
    ('cruzverde', 'Cruz Verde', 'farma', 'cruz verde',
     'farmaceutico / medicamentos,comercio y retail', '', ''),
    ('farmatodo', 'Farmatodo', 'farma', 'farmatodo',
     'farmaceutico / medicamentos,comercio y retail', '', ''),
    ('copidrogas', 'Copidrogas / Drogas La Rebaja', 'farma', 'copidrogas|drogas la rebaja',
     'farmaceutico / medicamentos', '', ''),
    ('audifarma', 'Audifarma', 'farma', 'audifarma',
     'farmaceutico / medicamentos,salud / EPS e IPS', '', ''),

    # ---- energía, petróleo, gas y minería -------------------------------
    ('ecopetrol', 'Ecopetrol', 'energia', 'ecopetrol',
     'mineria e hidrocarburos,*energia y servicios publicos,ambiental / medio ambiente', '', ''),
    ('terpel', 'Terpel', 'energia', 'terpel', 'mineria e hidrocarburos,energia y servicios publicos', '', ''),
    ('primax', 'Primax', 'energia', 'primax', 'mineria e hidrocarburos', '', ''),
    ('biomax', 'Biomax', 'energia', 'biomax', 'mineria e hidrocarburos', '', ''),
    ('promigas', 'Promigas', 'energia', 'promigas', 'energia y servicios publicos', '', ''),
    ('vanti', 'Vanti', 'energia', 'vanti|gas natural fenosa', 'energia y servicios publicos', '', ''),
    ('celsia', 'Celsia', 'energia', 'celsia', 'energia y servicios publicos', '', ''),
    ('epm', 'EPM', 'energia', 'epm|empresas publicas de medellin',
     'energia y servicios publicos,*agua y saneamiento', '', ''),
    ('isa', 'ISA', 'energia', 'interconexion electrica|isa sa', 'energia y servicios publicos', '', ''),
    ('isagen', 'Isagen', 'energia', 'isagen', 'energia y servicios publicos', '', ''),
    ('enel', 'Enel Colombia (Codensa/Emgesa)', 'energia', 'enel|codensa|emgesa',
     'energia y servicios publicos,competencia y consumidor', 'enel colombia', ''),
    ('aire', 'Air-e', 'energia', 'air e|aire sas esp', 'energia y servicios publicos', '', ''),
    ('afinia', 'Afinia', 'energia', 'afinia', 'energia y servicios publicos', '', ''),
    ('essa', 'ESSA', 'energia', 'electrificadora de santander|essa',
     'energia y servicios publicos', '', ''),
    ('electricaribe', 'Electricaribe', 'energia', 'electricaribe',
     'energia y servicios publicos', '', ''),
    ('xm', 'XM', 'energia', 'xm sa|xm compania de expertos', 'energia y servicios publicos', '', ''),
    ('canacol', 'Canacol Energy', 'energia', 'canacol', 'mineria e hidrocarburos', '', ''),
    ('frontera', 'Frontera Energy', 'energia', 'frontera energy|pacific rubiales',
     'mineria e hidrocarburos', '', ''),
    ('geopark', 'GeoPark', 'energia', 'geopark', 'mineria e hidrocarburos', '', ''),
    ('parex', 'Parex Resources', 'energia', 'parex', 'mineria e hidrocarburos', '', ''),
    ('grantierra', 'Gran Tierra Energy', 'energia', 'gran tierra', 'mineria e hidrocarburos', '', ''),
    ('drummond', 'Drummond', 'mineria', 'drummond',
     'mineria e hidrocarburos,*ambiental / medio ambiente,laboral', '', ''),
    ('cerrejon', 'Cerrejón', 'mineria', 'cerrejon',
     'mineria e hidrocarburos,*ambiental / medio ambiente', '', ''),
    ('prodeco', 'Prodeco (Glencore)', 'mineria', 'prodeco|glencore', 'mineria e hidrocarburos', '', ''),
    ('arismining', 'Aris Mining (Gran Colombia Gold)', 'mineria', 'aris mining|gran colombia gold',
     'mineria e hidrocarburos', '', ''),
    ('minerossa', 'Mineros S.A.', 'mineria', 'mineros sa', 'mineria e hidrocarburos', '', ''),

    # ---- alimentos, bebidas, licores y tabaco ---------------------------
    ('nutresa', 'Grupo Nutresa', 'alimentos', 'nutresa|grupo nutresa',
     'alimentos / etiquetado,competencia y consumidor', '', ''),
    ('alpina', 'Alpina', 'alimentos', 'alpina', 'alimentos / etiquetado', '', ''),
    ('colanta', 'Colanta', 'alimentos', 'colanta', 'alimentos / etiquetado,sector agropecuario', '', ''),
    ('alqueria', 'Alquería', 'alimentos', 'alqueria', 'alimentos / etiquetado,sector agropecuario', '', ''),
    ('postobon', 'Postobón', 'alimentos', 'postobon|gaseosas lux',
     'alimentos / etiquetado,tributario', '', ''),
    ('cocacola', 'Coca-Cola FEMSA', 'alimentos', 'coca cola|cocacola|femsa',
     'alimentos / etiquetado,tributario', '', ''),
    ('bavaria', 'Bavaria (AB InBev)', 'alimentos', 'bavaria|ab inbev',
     'licores y tabaco,tributario,competencia y consumidor', 'bavaria sa', ''),
    ('nestle', 'Nestlé', 'alimentos', 'nestle', 'alimentos / etiquetado', '', ''),
    ('bimbo', 'Bimbo', 'alimentos', 'bimbo', 'alimentos / etiquetado', '', ''),
    ('teamfoods', 'Team Foods', 'alimentos', 'team foods', 'alimentos / etiquetado', '', ''),
    ('colombina', 'Colombina', 'alimentos', 'colombina', 'alimentos / etiquetado', '', ''),
    ('quala', 'Quala', 'alimentos', 'quala', 'alimentos / etiquetado', '', ''),
    ('casaluker', 'Casa Luker', 'alimentos', 'casa luker|luker', 'alimentos / etiquetado', '', ''),
    ('diageo', 'Diageo', 'alimentos', 'diageo', 'licores y tabaco,tributario', '', ''),
    ('pernod', 'Pernod Ricard', 'alimentos', 'pernod ricard', 'licores y tabaco', '', ''),
    ('coltabaco', 'Coltabaco (Philip Morris)', 'alimentos', 'coltabaco|philip morris',
     'licores y tabaco,tributario', '', ''),
    ('bat', 'British American Tobacco', 'alimentos', 'british american tobacco|protabaco',
     'licores y tabaco,tributario', '', ''),
    ('manuelita', 'Manuelita', 'alimentos', 'manuelita', 'sector agropecuario,alimentos / etiquetado', '', ''),
    ('riopaila', 'Riopaila Castilla', 'alimentos', 'riopaila', 'sector agropecuario', '', ''),
    ('incauca', 'Incauca', 'alimentos', 'incauca', 'sector agropecuario', '', ''),
    ('italcol', 'Italcol', 'alimentos', 'italcol', 'sector agropecuario', '', ''),

    # ---- comercio y retail ----------------------------------------------
    ('exito', 'Grupo Éxito', 'retail', 'grupo exito|almacenes exito|almacenes éxito',
     'comercio y retail,competencia y consumidor,alimentos / etiquetado', '', ''),
    ('olimpica', 'Olímpica', 'retail', 'olimpica|supertiendas olimpica', 'comercio y retail', '', ''),
    ('d1', 'Tiendas D1', 'retail', 'tiendas d1|koba colombia', 'comercio y retail', '', ''),
    ('ara', 'Tiendas Ara', 'retail', 'tiendas ara|jeronimo martins', 'comercio y retail', '', ''),
    ('falabella', 'Falabella', 'retail', 'falabella',
     'comercio y retail,competencia y consumidor', '', ''),
    ('alkosto', 'Alkosto', 'retail', 'alkosto|ktronix', 'comercio y retail', '', ''),
    ('cencosud', 'Cencosud (Jumbo)', 'retail', 'cencosud|jumbo', 'comercio y retail', '', ''),
    ('homecenter', 'Homecenter (Sodimac)', 'retail', 'homecenter|sodimac',
     'comercio y retail,vivienda y construccion', '', ''),
    ('makro', 'Makro', 'retail', 'makro', 'comercio y retail', '', ''),
    ('pricesmart', 'PriceSmart', 'retail', 'pricesmart', 'comercio y retail', '', ''),
    ('temu', 'Temu', 'retail', 'temu',
     'comercio y retail,comercio exterior y aduanas,competencia y consumidor', '', ''),
    ('shein', 'Shein', 'retail', 'shein',
     'comercio y retail,comercio exterior y aduanas,tributario', '', ''),
    ('amazon', 'Amazon', 'tecnologia', 'amazon|amazon web services|aws',
     'comercio y retail,*tecnologia digital / IA,tributario', '', ''),

    # ---- construcción, cemento y vivienda -------------------------------
    ('argos', 'Cementos Argos', 'construccion', 'argos|cementos argos',
     'vivienda y construccion,competencia y consumidor,ambiental / medio ambiente', '', ''),
    ('cemex', 'Cemex', 'construccion', 'cemex',
     'vivienda y construccion,competencia y consumidor', '', ''),
    ('ultracem', 'Ultracem', 'construccion', 'ultracem', 'vivienda y construccion', '', ''),
    ('corona', 'Organización Corona', 'construccion', 'organizacion corona|corona sa',
     'vivienda y construccion', '', 'corona virus|coronavirus'),
    ('amarilo', 'Amarilo', 'construccion', 'amarilo', 'vivienda y construccion', '', ''),
    ('constructorabolivar', 'Constructora Bolívar', 'construccion', 'constructora bolivar',
     'vivienda y construccion', '', ''),
    ('marval', 'Marval', 'construccion', 'marval', 'vivienda y construccion', '', ''),
    ('conconcreto', 'Conconcreto', 'construccion', 'conconcreto',
     'vivienda y construccion,puertos y logistica', '', ''),
    ('odinsa', 'Odinsa', 'construccion', 'odinsa', 'puertos y logistica', '', ''),
    ('sacyr', 'Sacyr', 'construccion', 'sacyr', 'puertos y logistica', '', ''),

    # ---- aviación, turismo y hotelería ----------------------------------
    ('avianca', 'Avianca', 'aviacion', 'avianca',
     'aviacion / transporte aereo,competencia y consumidor,laboral', '', ''),
    ('latam', 'LATAM Airlines', 'aviacion', 'latam',
     'aviacion / transporte aereo,competencia y consumidor', '', ''),
    ('wingo', 'Wingo', 'aviacion', 'wingo', 'aviacion / transporte aereo', '', ''),
    ('copa', 'Copa Airlines', 'aviacion', 'copa airlines', 'aviacion / transporte aereo', '', ''),
    ('satena', 'Satena', 'aviacion', 'satena', 'aviacion / transporte aereo', '', ''),
    ('vivaair', 'Viva Air', 'aviacion', 'viva air|vivaair',
     'aviacion / transporte aereo,competencia y consumidor', '', ''),
    ('easyfly', 'EasyFly', 'aviacion', 'easyfly', 'aviacion / transporte aereo', '', ''),
    ('despegar', 'Despegar', 'turismo', 'despegar', 'turismo y hoteleria,competencia y consumidor', '', ''),
    ('aviatur', 'Aviatur', 'turismo', 'aviatur', 'turismo y hoteleria', '', ''),
    ('booking', 'Booking', 'turismo', 'booking', 'turismo y hoteleria,tributario', '', ''),
    ('airbnb', 'Airbnb', 'turismo', 'airbnb',
     'turismo y hoteleria,tributario,*vivienda y construccion', '', ''),
    ('decameron', 'Decameron', 'turismo', 'decameron', 'turismo y hoteleria', '', ''),

    # ---- agua, aseo y servicios domiciliarios ---------------------------
    ('eaab', 'Acueducto de Bogotá', 'agua', 'acueducto de bogota|eaab',
     'agua y saneamiento,energia y servicios publicos', '', ''),
    ('veolia', 'Veolia', 'agua', 'veolia', 'agua y saneamiento', '', ''),
    ('triplea', 'Triple A', 'agua', 'triple a', 'agua y saneamiento', '', ''),
    ('emcali', 'Emcali', 'agua', 'emcali',
     'agua y saneamiento,*energia y servicios publicos,telecomunicaciones', '', ''),

    # ---- logística, puertos y mensajería --------------------------------
    ('servientrega', 'Servientrega', 'logistica', 'servientrega', 'puertos y logistica', '', ''),
    ('coordinadora', 'Coordinadora', 'logistica', 'coordinadora mercantil|coordinadora sa',
     'puertos y logistica', '', ''),
    ('deprisa', 'Deprisa', 'logistica', 'deprisa', 'puertos y logistica', '', ''),
    ('dhl', 'DHL', 'logistica', 'dhl', 'puertos y logistica,comercio exterior y aduanas', '', ''),
    ('fedex', 'FedEx', 'logistica', 'fedex', 'puertos y logistica,comercio exterior y aduanas', '', ''),
    ('tcc', 'TCC', 'logistica', 'tcc sa|transportes tcc', 'puertos y logistica', '', ''),
    ('puertocartagena', 'Puerto de Cartagena', 'logistica',
     'puerto de cartagena|sociedad portuaria regional de cartagena',
     'puertos y logistica,comercio exterior y aduanas', '', ''),
    ('puertobuenaventura', 'Puerto de Buenaventura', 'logistica',
     'puerto de buenaventura|sociedad portuaria de buenaventura',
     'puertos y logistica,comercio exterior y aduanas', '', ''),

    # ---- tecnología global -----------------------------------------------
    ('google', 'Google', 'tecnologia', 'google|alphabet',
     'tecnologia digital / IA,*datos personales / habeas data,tributario,competencia y consumidor', '', ''),
    ('meta', 'Meta (Facebook/Instagram/WhatsApp)', 'tecnologia',
     'meta platforms|facebook|instagram|whatsapp',
     'tecnologia digital / IA,*datos personales / habeas data,tributario', '', ''),
    ('netflix', 'Netflix', 'tecnologia', 'netflix', 'tecnologia digital / IA,tributario', '', ''),
    ('spotify', 'Spotify', 'tecnologia', 'spotify', 'tecnologia digital / IA,propiedad intelectual', '', ''),
    ('tiktok', 'TikTok', 'tecnologia', 'tiktok|bytedance',
     'tecnologia digital / IA,*datos personales / habeas data', '', ''),
    ('twitter', 'X (Twitter)', 'tecnologia', 'twitter',
     'tecnologia digital / IA,datos personales / habeas data', '', ''),
    ('microsoft', 'Microsoft', 'tecnologia', 'microsoft', 'tecnologia digital / IA', '', ''),
    ('apple', 'Apple', 'tecnologia', 'apple', 'tecnologia digital / IA,competencia y consumidor', '', ''),
    ('openai', 'OpenAI', 'tecnologia', 'openai|chatgpt', 'tecnologia digital / IA', '', ''),

    # ---- medios -----------------------------------------------------------
    ('caracol', 'Caracol', 'medios', 'caracol television|caracol radio',
     'telecomunicaciones,tecnologia digital / IA', '', ''),
    ('rcn', 'RCN', 'medios', 'rcn television|rcn radio', 'telecomunicaciones', '', ''),
    ('eltiempo', 'El Tiempo', 'medios', 'casa editorial el tiempo', 'telecomunicaciones', '', ''),
    ('semana', 'Semana', 'medios', 'publicaciones semana', 'telecomunicaciones', '', ''),

    # ---- juegos de suerte y azar -----------------------------------------
    ('betplay', 'BetPlay', 'juegos', 'betplay|corredor empresarial',
     'juegos de suerte y azar,tributario', '', ''),
    ('wplay', 'Wplay', 'juegos', 'wplay', 'juegos de suerte y azar', '', ''),
    ('rushbet', 'Rushbet', 'juegos', 'rushbet', 'juegos de suerte y azar', '', ''),
    ('codere', 'Codere', 'juegos', 'codere', 'juegos de suerte y azar', '', ''),

    # ---- automotriz -------------------------------------------------------
    ('sofasa', 'Renault Sofasa', 'automotriz', 'sofasa|renault',
     'comercio exterior y aduanas,ambiental / medio ambiente', '', ''),
    ('colmotores', 'GM Colmotores', 'automotriz', 'colmotores|general motors',
     'comercio exterior y aduanas', '', ''),
    ('toyota', 'Toyota', 'automotriz', 'toyota', 'comercio exterior y aduanas', '', ''),

    # ---- comisionistas de bolsa, fiduciarias y financiero especializado ---
    # (el bloque más denso de sanciones de la Superfinanciera en el dataset)
    ('interbolsa', 'Interbolsa', 'financiero', 'interbolsa', 'sector financiero', '', ''),
    ('alianzafid', 'Alianza Fiduciaria', 'financiero', 'alianza fiduciaria', 'sector financiero', '', ''),
    ('credicorp', 'Credicorp Capital', 'financiero', 'credicorp', 'sector financiero', '', ''),
    ('ultraserfinco', 'Ultraserfinco', 'financiero', 'ultraserfinco|serfinco', 'sector financiero', '', ''),
    ('globalsec', 'Global Securities', 'financiero', 'global securities', 'sector financiero', '', ''),
    ('corredoresdav', 'Corredores Davivienda', 'financiero', 'corredores davivienda', 'sector financiero', '', ''),
    ('accionfid', 'Acción Fiduciaria', 'financiero', 'accion fiduciaria|accion sociedad fiduciaria', 'sector financiero', '', ''),
    ('fidubancolombia', 'Fiduciaria Bancolombia', 'financiero', 'fiduciaria bancolombia|fiducolombia', 'sector financiero', '', ''),
    ('fiducoldex', 'Fiducoldex', 'financiero', 'fiducoldex', 'sector financiero', '', ''),
    ('btg', 'BTG Pactual', 'financiero', 'btg pactual', 'sector financiero', '', ''),
    ('casadebolsa', 'Casa de Bolsa', 'financiero', 'casa de bolsa', 'sector financiero', '', ''),
    ('coltefinanciera', 'Coltefinanciera', 'financiero', 'coltefinanciera', 'sector financiero', '', ''),
    ('corficolombiana', 'Corficolombiana', 'financiero', 'corficolombiana', 'sector financiero', '', ''),
    ('bancoldex', 'Bancóldex', 'financiero', 'bancoldex', 'sector financiero,comercio exterior y aduanas', '', ''),
    ('findeter', 'Findeter', 'financiero', 'findeter', 'sector financiero,vivienda y construccion', '', ''),
    ('finagro', 'Finagro', 'financiero', 'finagro', 'sector financiero,*sector agropecuario', '', ''),
    ('fna', 'Fondo Nacional del Ahorro', 'financiero', 'fondo nacional del ahorro',
     'vivienda y construccion,*pensiones y cesantias', '', ''),
    ('coomeva', 'Coomeva', 'financiero', 'coomeva', 'sector financiero,*salud / EPS e IPS', '', ''),
    ('datacredito', 'Datacrédito', 'financiero', 'datacredito|experian',
     'datos personales / habeas data,*sector financiero', '', ''),
    ('transunion', 'TransUnion (Cifin)', 'financiero', 'transunion|cifin',
     'datos personales / habeas data,*sector financiero', '', ''),

    # ---- salud · EPS, IPS y clínicas (2ª tanda) --------------------------
    ('emssanar', 'Emssanar', 'salud', 'emssanar', 'salud / EPS e IPS', '', ''),
    ('asmetsalud', 'Asmet Salud', 'salud', 'asmet salud', 'salud / EPS e IPS', '', ''),
    ('capitalsalud', 'Capital Salud', 'salud', 'capital salud', 'salud / EPS e IPS', '', ''),
    ('sos', 'EPS SOS', 'salud', 'eps sos|servicio occidental de salud', 'salud / EPS e IPS', '', ''),
    ('aliansalud', 'Aliansalud', 'salud', 'aliansalud', 'salud / EPS e IPS', '', ''),
    ('ecoopsos', 'Ecoopsos', 'salud', 'ecoopsos', 'salud / EPS e IPS', '', ''),
    ('comfenalco', 'Comfenalco', 'salud', 'comfenalco', 'salud / EPS e IPS,*laboral', '', ''),
    ('comfandi', 'Comfandi', 'salud', 'comfandi', 'salud / EPS e IPS,*laboral', '', ''),
    ('comfama', 'Comfama', 'salud', 'comfama', 'salud / EPS e IPS,*laboral', '', ''),
    ('santafe', 'Fundación Santa Fe', 'salud', 'fundacion santa fe', 'salud / EPS e IPS', '', ''),
    ('country', 'Clínica del Country', 'salud', 'clinica del country', 'salud / EPS e IPS', '', ''),
    ('mederi', 'Méderi', 'salud', 'mederi', 'salud / EPS e IPS', '', ''),
    ('sanvicente', 'Hospital San Vicente', 'salud', 'hospital san vicente', 'salud / EPS e IPS', '', ''),

    # ---- farmacéutico (2ª tanda) -----------------------------------------
    ('jnj', 'Johnson & Johnson', 'farma', 'johnson johnson|janssen', 'farmaceutico / medicamentos', '', ''),
    ('gsk', 'GSK', 'farma', 'glaxosmithkline|gsk', 'farmaceutico / medicamentos', '', ''),
    ('astrazeneca', 'AstraZeneca', 'farma', 'astrazeneca', 'farmaceutico / medicamentos', '', ''),
    ('msd', 'MSD (Merck)', 'farma', 'msd colombia|merck', 'farmaceutico / medicamentos', '', ''),
    ('boehringer', 'Boehringer Ingelheim', 'farma', 'boehringer', 'farmaceutico / medicamentos', '', ''),
    ('takeda', 'Takeda', 'farma', 'takeda', 'farmaceutico / medicamentos', '', ''),
    ('amgen', 'Amgen', 'farma', 'amgen', 'farmaceutico / medicamentos', '', ''),
    ('baxter', 'Baxter', 'farma', 'baxter', 'farmaceutico / medicamentos', '', ''),
    ('fresenius', 'Fresenius', 'farma', 'fresenius', 'farmaceutico / medicamentos,*salud / EPS e IPS', '', ''),
    ('lafrancol', 'Lafrancol', 'farma', 'lafrancol', 'farmaceutico / medicamentos', '', ''),

    # ---- industria y manufactura -----------------------------------------
    ('familia', 'Productos Familia', 'industria', 'productos familia|papeles familia',
     'comercio y retail,*competencia y consumidor', '', ''),
    ('kimberly', 'Kimberly-Clark', 'industria', 'kimberly clark', 'comercio y retail', '', ''),
    ('colgate', 'Colgate-Palmolive', 'industria', 'colgate', 'comercio y retail,*competencia y consumidor', '', ''),
    ('unilever', 'Unilever', 'industria', 'unilever', 'comercio y retail,*alimentos / etiquetado', '', ''),
    ('pg', 'Procter & Gamble', 'industria', 'procter gamble', 'comercio y retail', '', ''),
    ('belcorp', 'Belcorp', 'industria', 'belcorp|esika|lbel', 'comercio y retail', '', ''),
    ('yanbal', 'Yanbal', 'industria', 'yanbal', 'comercio y retail', '', ''),
    ('avon', 'Avon', 'industria', 'avon', 'comercio y retail', '', ''),
    ('ramo', 'Ramo', 'industria', 'productos ramo', 'alimentos / etiquetado', '', ''),
    ('pintuco', 'Pintuco (Grupo Orbis)', 'industria', 'pintuco|grupo orbis', 'vivienda y construccion', '', ''),
    ('sika', 'Sika', 'industria', 'sika colombia', 'vivienda y construccion', '', ''),
    ('haceb', 'Haceb', 'industria', 'haceb', 'comercio y retail', '', ''),
    ('mabe', 'Mabe', 'industria', 'mabe colombia', 'comercio y retail', '', ''),
    ('challenger', 'Challenger', 'industria', 'challenger', 'comercio y retail', '', ''),
    ('michelin', 'Michelin / Icollantas', 'industria', 'icollantas|michelin', 'comercio y retail', '', ''),
    ('goodyear', 'Goodyear', 'industria', 'goodyear', 'comercio y retail', '', ''),
    ('pazdelrio', 'Acerías Paz del Río', 'industria', 'paz del rio|acerias paz del rio',
     'mineria e hidrocarburos,*ambiental / medio ambiente', '', ''),
    ('ternium', 'Ternium / Tenaris', 'industria', 'ternium|tenaris|tubocaribe',
     'mineria e hidrocarburos,*comercio exterior y aduanas', '', ''),
    ('smurfit', 'Smurfit Kappa Cartón de Colombia', 'industria', 'smurfit|carton de colombia',
     'ambiental / medio ambiente,*comercio y retail', '', ''),
    ('carvajal', 'Carvajal', 'industria', 'carvajal sa|organizacion carvajal',
     'comercio y retail', '', 'carvajal de claro|carvajal zapata'),
    ('peldar', 'Peldar (O-I)', 'industria', 'peldar|owens illinois', 'comercio y retail', '', ''),
    ('tetrapak', 'Tetra Pak', 'industria', 'tetra pak', 'alimentos / etiquetado', '', ''),

    # ---- textil y moda ----------------------------------------------------
    ('fabricato', 'Fabricato', 'textil', 'fabricato', 'comercio y retail,*comercio exterior y aduanas', '', ''),
    ('coltejer', 'Coltejer', 'textil', 'coltejer', 'comercio y retail,*comercio exterior y aduanas', '', ''),
    ('leonisa', 'Leonisa', 'textil', 'leonisa', 'comercio y retail', '', ''),
    ('crystal', 'Crystal', 'textil', 'crystal sas|grupo crystal', 'comercio y retail', '', ''),
    ('arturocalle', 'Arturo Calle', 'textil', 'arturo calle', 'comercio y retail', '', ''),
    ('totto', 'Totto', 'textil', 'totto', 'comercio y retail', '', ''),
    ('velez', 'Cueros Vélez', 'textil', 'cueros velez', 'comercio y retail', '', ''),
    ('offcorss', 'Offcorss', 'textil', 'offcorss', 'comercio y retail', '', ''),

    # ---- restaurantes y consumo -------------------------------------------
    ('crepes', 'Crepes & Waffles', 'consumo', 'crepes waffles', 'alimentos / etiquetado,*laboral', '', ''),
    ('frisby', 'Frisby', 'consumo', 'frisby', 'alimentos / etiquetado', '', ''),
    ('elcorral', 'El Corral', 'consumo', 'el corral|hamburguesas el corral', 'alimentos / etiquetado', '', ''),
    ('mcdonalds', 'McDonald\'s', 'consumo', 'mcdonalds', 'alimentos / etiquetado', '', ''),
    ('juanvaldez', 'Juan Valdez', 'consumo', 'juan valdez|procafecol',
     'alimentos / etiquetado,*sector agropecuario', '', ''),
    ('kokoriko', 'Kokoriko', 'consumo', 'kokoriko', 'alimentos / etiquetado', '', ''),
    ('presto', 'Presto', 'consumo', 'hamburguesas presto', 'alimentos / etiquetado', '', ''),
    ('andrescarne', 'Andrés Carne de Res', 'consumo', 'andres carne de res', 'alimentos / etiquetado', '', ''),

    # ---- agro y alimentos (2ª tanda) --------------------------------------
    ('cargill', 'Cargill', 'agro', 'cargill', 'sector agropecuario,*alimentos / etiquetado', '', ''),
    ('bunge', 'Bunge', 'agro', 'bunge', 'sector agropecuario', '', ''),
    ('solla', 'Solla', 'agro', 'solla sa', 'sector agropecuario', '', ''),
    ('contegral', 'Contegral', 'agro', 'contegral', 'sector agropecuario', '', ''),
    ('kikes', 'Huevos Kikes', 'agro', 'huevos kikes|incubadora santander',
     'sector agropecuario,*alimentos / etiquetado', '', ''),
    ('bucanero', 'Pollos Bucanero', 'agro', 'pollos bucanero', 'sector agropecuario', '', ''),
    ('daabon', 'Grupo Daabon', 'agro', 'daabon', 'sector agropecuario,*ambiental / medio ambiente', '', ''),
    ('mayaguez', 'Ingenio Mayagüez', 'agro', 'mayaguez', 'sector agropecuario', '', ''),

    # ---- transporte masivo y terrestre -------------------------------------
    ('metromedellin', 'Metro de Medellín', 'transporte', 'metro de medellin', 'puertos y logistica', '', ''),
    ('transmilenio', 'TransMilenio', 'transporte', 'transmilenio', 'puertos y logistica', '', ''),
    ('metrolinea', 'Metrolínea', 'transporte', 'metrolinea', 'puertos y logistica', '', ''),
    ('mio', 'MIO (Metrocali)', 'transporte', 'metrocali|masivo integrado de occidente', 'puertos y logistica', '', ''),
    ('megabus', 'Megabús', 'transporte', 'megabus', 'puertos y logistica', '', ''),
    ('brasilia', 'Expreso Brasilia', 'transporte', 'expreso brasilia', 'puertos y logistica', '', ''),
    ('copetran', 'Copetran', 'transporte', 'copetran', 'puertos y logistica', '', ''),
    ('bolivariano', 'Expreso Bolivariano', 'transporte', 'expreso bolivariano', 'puertos y logistica', '', ''),
    ('rapidoochoa', 'Rápido Ochoa', 'transporte', 'rapido ochoa', 'puertos y logistica', '', ''),
    ('opain', 'Opain (El Dorado)', 'transporte', 'opain', 'aviacion / transporte aereo', '', ''),
    ('airplan', 'Airplan', 'transporte', 'airplan', 'aviacion / transporte aereo', '', ''),

    # ---- servicios públicos regionales --------------------------------------
    ('surtigas', 'Surtigas', 'energia', 'surtigas', 'energia y servicios publicos', '', ''),
    ('gasesoccidente', 'Gases de Occidente', 'energia', 'gases de occidente', 'energia y servicios publicos', '', ''),
    ('alcanos', 'Alcanos', 'energia', 'alcanos', 'energia y servicios publicos', '', ''),
    ('efigas', 'Efigás', 'energia', 'efigas', 'energia y servicios publicos', '', ''),
    ('chec', 'CHEC', 'energia', 'chec sa|central hidroelectrica de caldas', 'energia y servicios publicos', '', ''),
    ('cens', 'CENS', 'energia', 'centrales electricas del norte de santander|cens', 'energia y servicios publicos', '', ''),
    ('emsa', 'EMSA', 'energia', 'electrificadora del meta', 'energia y servicios publicos', '', ''),
    ('enertolima', 'Enertolima', 'energia', 'enertolima', 'energia y servicios publicos', '', ''),
    ('electrohuila', 'Electrohuila', 'energia', 'electrohuila', 'energia y servicios publicos', '', ''),
    ('dispac', 'Dispac', 'energia', 'dispac', 'energia y servicios publicos', '', ''),

    # ---- educación superior --------------------------------------------------
    ('uniandes', 'Universidad de los Andes', 'educacion', 'universidad de los andes|uniandes', 'educacion superior', '', ''),
    ('javeriana', 'Universidad Javeriana', 'educacion', 'universidad javeriana|pontificia universidad javeriana', 'educacion superior', '', ''),
    ('unal', 'Universidad Nacional', 'educacion', 'universidad nacional de colombia', 'educacion superior', '', ''),
    ('udea', 'Universidad de Antioquia', 'educacion', 'universidad de antioquia', 'educacion superior', '', ''),
    ('eafit', 'EAFIT', 'educacion', 'eafit', 'educacion superior', '', ''),
    ('externado', 'Universidad Externado', 'educacion', 'universidad externado', 'educacion superior', '', ''),
    ('rosario', 'Universidad del Rosario', 'educacion', 'universidad del rosario', 'educacion superior', '', ''),
    ('sabana', 'Universidad de La Sabana', 'educacion', 'universidad de la sabana', 'educacion superior', '', ''),
    ('areandina', 'Areandina', 'educacion', 'areandina|fundacion universitaria del area andina', 'educacion superior', '', ''),
    ('poligran', 'Politécnico Grancolombiano', 'educacion', 'politecnico grancolombiano', 'educacion superior', '', ''),
    ('uniminuto', 'Uniminuto', 'educacion', 'uniminuto|minuto de dios', 'educacion superior', '', ''),
    ('sena', 'SENA', 'educacion', 'sena|servicio nacional de aprendizaje', 'educacion superior,*laboral', '', ''),

    # ---- tecnología y servicios TI --------------------------------------------
    ('globant', 'Globant', 'tecnologia', 'globant', 'tecnologia digital / IA', '', ''),
    ('ibm', 'IBM', 'tecnologia', 'ibm colombia', 'tecnologia digital / IA', '', ''),
    ('oracle', 'Oracle', 'tecnologia', 'oracle', 'tecnologia digital / IA', '', ''),
    ('sap', 'SAP', 'tecnologia', 'sap colombia', 'tecnologia digital / IA', '', ''),
    ('accenture', 'Accenture', 'tecnologia', 'accenture', 'tecnologia digital / IA', '', ''),
    ('sofka', 'Sofka Technologies', 'tecnologia', 'sofka', 'tecnologia digital / IA', '', ''),

    # ---- seguridad y vigilancia (2ª tanda) --------------------------------------
    ('prosegur', 'Prosegur', 'seguridad', 'prosegur', 'seguridad privada', '', ''),
    ('securitas', 'Securitas', 'seguridad', 'securitas', 'seguridad privada', '', ''),
    ('fortox', 'Fortox', 'seguridad', 'fortox', 'seguridad privada', '', ''),

    # ---- seguridad privada -------------------------------------------------
    ('brinks', "Brink's", 'seguridad', 'brinks', 'seguridad privada', '', ''),
    ('atlas', 'Seguridad Atlas', 'seguridad', 'seguridad atlas', 'seguridad privada', '', ''),
]

# Gremios y asociaciones: no son empresas, pero SON quienes contratan a Cauce y
# quienes el cliente escribe en el buscador. Mismo shape (el 3er campo queda
# como sector) y se marcan tipo='gremio'.
_RAW_GREMIOS = [
    ('andi', 'ANDI', 'multisectorial', 'andi|asociacion nacional de empresarios',
     'tributario,laboral,comercio exterior y aduanas,competencia y consumidor', '', 'andina|andino'),
    ('fenalco', 'Fenalco', 'comercio', 'fenalco',
     'comercio y retail,tributario,competencia y consumidor', '', ''),
    ('asobancaria', 'Asobancaria', 'financiero', 'asobancaria',
     'sector financiero,tributario', '', ''),
    ('fasecolda', 'Fasecolda', 'seguros', 'fasecolda', 'seguros,sector financiero', '', ''),
    ('asofondos', 'Asofondos', 'pensiones', 'asofondos', 'pensiones y cesantias', '', ''),
    ('acemi', 'ACEMI', 'salud', 'acemi', 'salud / EPS e IPS', '', ''),
    ('afidro', 'AFIDRO', 'farma', 'afidro',
     'farmaceutico / medicamentos,propiedad intelectual', '', ''),
    ('asocoldro', 'Asocoldro', 'farma', 'asocoldro', 'farmaceutico / medicamentos', '', ''),
    ('camacol', 'Camacol', 'construccion', 'camacol', 'vivienda y construccion', '', ''),
    ('cci', 'Cámara Colombiana de la Infraestructura', 'construccion',
     'camara colombiana de la infraestructura', 'puertos y logistica', '', ''),
    ('andesco', 'Andesco', 'servicios', 'andesco',
     'energia y servicios publicos,*agua y saneamiento,telecomunicaciones', '', ''),
    ('acolgen', 'Acolgen', 'energia', 'acolgen', 'energia y servicios publicos', '', ''),
    ('naturgas', 'Naturgas', 'energia', 'naturgas', 'energia y servicios publicos', '', ''),
    ('acp', 'ACP · Asoc. Colombiana del Petróleo', 'energia',
     'asociacion colombiana del petroleo|campetrol', 'mineria e hidrocarburos', '', ''),
    ('asomineros', 'Asomineros', 'mineria', 'asomineros', 'mineria e hidrocarburos', '', ''),
    ('fenalcarbon', 'Fenalcarbón', 'mineria', 'fenalcarbon', 'mineria e hidrocarburos', '', ''),
    ('asomovil', 'Asomóvil', 'telecom', 'asomovil', 'telecomunicaciones', '', ''),
    ('acopi', 'Acopi', 'multisectorial', 'acopi', 'tributario,laboral', '', ''),
    ('analdex', 'Analdex', 'comercio', 'analdex', 'comercio exterior y aduanas', '', ''),
    ('cotelco', 'Cotelco', 'turismo', 'cotelco', 'turismo y hoteleria', '', ''),
    ('anato', 'Anato', 'turismo', 'anato', 'turismo y hoteleria,aviacion / transporte aereo', '', ''),
    ('colfecar', 'Colfecar', 'logistica', 'colfecar', 'puertos y logistica', '', ''),
    ('fedetranscarga', 'Fedetranscarga', 'logistica', 'fedetranscarga', 'puertos y logistica', '', ''),
    ('sac', 'SAC · Sociedad de Agricultores', 'agro',
     'sociedad de agricultores de colombia', 'sector agropecuario', '', ''),
    ('fedegan', 'Fedegán', 'agro', 'fedegan', 'sector agropecuario', '', ''),
    ('fedecafe', 'Federación Nacional de Cafeteros', 'agro',
     'federacion nacional de cafeteros|fedecafe', 'sector agropecuario', '', ''),
    ('fedearroz', 'Fedearroz', 'agro', 'fedearroz', 'sector agropecuario', '', ''),
    ('fedepalma', 'Fedepalma', 'agro', 'fedepalma',
     'sector agropecuario,ambiental / medio ambiente', '', ''),
    ('asocana', 'Asocaña', 'agro', 'asocana', 'sector agropecuario', '', ''),
    ('augura', 'Augura', 'agro', 'augura', 'sector agropecuario', '', ''),
    ('fenavi', 'Fenavi', 'agro', 'fenavi', 'sector agropecuario,alimentos / etiquetado', '', ''),
    ('porkcolombia', 'Porkcolombia', 'agro', 'porkcolombia', 'sector agropecuario', '', ''),
    ('fenalce', 'Fenalce', 'agro', 'fenalce', 'sector agropecuario', '', ''),
    ('asocolflores', 'Asocolflores', 'agro', 'asocolflores',
     'sector agropecuario,comercio exterior y aduanas', '', ''),
    ('acoplasticos', 'Acoplásticos', 'industria', 'acoplasticos',
     'ambiental / medio ambiente,comercio exterior y aduanas', '', ''),
    ('andemos', 'Andemos', 'automotriz', 'andemos', 'comercio exterior y aduanas', '', ''),
    ('ascun', 'ASCUN', 'educacion', 'ascun', 'educacion superior', '', ''),
    ('acodres', 'Acodres', 'comercio', 'acodres',
     'comercio y retail,alimentos / etiquetado,turismo y hoteleria', '', ''),
    ('asobares', 'Asobares', 'comercio', 'asobares', 'licores y tabaco,comercio y retail', '', ''),
    ('fedeseguridad', 'Fedeseguridad', 'seguridad', 'fedeseguridad', 'seguridad privada', '', ''),
    ('anif', 'ANIF', 'financiero', 'anif', 'sector financiero,tributario', '', ''),
    ('acm', 'ACM · Asoc. Colombiana de Minería', 'mineria',
     'asociacion colombiana de mineria', 'mineria e hidrocarburos', '', ''),
    ('asocodis', 'Asocodis', 'energia', 'asocodis', 'energia y servicios publicos', '', ''),
    ('andeg', 'Andeg', 'energia', 'andeg', 'energia y servicios publicos', '', ''),
    ('acodal', 'Acodal', 'servicios', 'acodal', 'agua y saneamiento', '', ''),
    ('aciem', 'ACIEM', 'servicios', 'aciem', 'energia y servicios publicos', '', ''),
    ('asofiduciarias', 'Asofiduciarias', 'financiero', 'asofiduciarias', 'sector financiero', '', ''),
    ('asobolsa', 'Asobolsa', 'financiero', 'asobolsa', 'sector financiero', '', ''),
    ('asomicrofinanzas', 'Asomicrofinanzas', 'financiero', 'asomicrofinanzas', 'sector financiero', '', ''),
    ('titularizadora', 'Titularizadora Colombiana', 'financiero', 'titularizadora colombiana',
     'sector financiero,*vivienda y construccion', '', ''),
    ('achc', 'ACHC · Clínicas y Hospitales', 'salud',
     'asociacion colombiana de hospitales y clinicas', 'salud / EPS e IPS', '', ''),
    ('gestarsalud', 'Gestarsalud', 'salud', 'gestarsalud', 'salud / EPS e IPS', '', ''),
    ('acesi', 'ACESI', 'salud', 'acesi', 'salud / EPS e IPS', '', ''),
    ('asocolflores2', 'Acolfa', 'automotriz', 'acolfa', 'comercio exterior y aduanas', '', ''),
    ('asopartes', 'Asopartes', 'automotriz', 'asopartes', 'comercio exterior y aduanas', '', ''),
    ('fedemetal', 'Fedemetal', 'industria', 'fedemetal', 'comercio exterior y aduanas', '', ''),
    ('fedecacao', 'Fedecacao', 'agro', 'fedecacao', 'sector agropecuario', '', ''),
    ('conalgodon', 'Conalgodón', 'agro', 'conalgodon', 'sector agropecuario', '', ''),
    ('fedepanela', 'Fedepanela', 'agro', 'fedepanela', 'sector agropecuario', '', ''),
    ('asohofrucol', 'Asohofrucol', 'agro', 'asohofrucol', 'sector agropecuario', '', ''),
    ('ccb', 'Cámara de Comercio de Bogotá', 'multisectorial',
     'camara de comercio de bogota', 'comercio y retail,*tributario', '', ''),
    ('confecamaras', 'Confecámaras', 'multisectorial', 'confecamaras', 'comercio y retail', '', ''),
    ('asomedios', 'Asomedios', 'medios', 'asomedios', 'telecomunicaciones', '', ''),
    ('andiarios', 'Andiarios', 'medios', 'andiarios', 'telecomunicaciones', '', ''),
    ('acofi', 'ACOFI', 'educacion', 'acofi', 'educacion superior', '', ''),
    ('asotrans', 'Asotrans', 'logistica', 'asotrans', 'puertos y logistica', '', ''),
    ('defencarga', 'Defencarga', 'logistica', 'defencarga', 'puertos y logistica', '', ''),
    ('asojuegos', 'Asojuegos', 'juegos', 'asojuegos|fecoljuegos',
     'juegos de suerte y azar', '', ''),
]


def _fila(t, tipo):
    k, nombre, sector, alias, top, ent, exc = t
    al = [_n(a) for a in alias.split('|') if a.strip()]
    tops = [x.strip() for x in top.split(',') if x.strip()]
    nucleo, contexto = [], []
    for i, x in enumerate(tops):
        # núcleo = la primera, más las marcadas con '*' (doble actividad central)
        (nucleo if (i == 0 or x.startswith('*')) else contexto).append(x.lstrip('*'))
    return {
        'k': k, 'nombre': nombre, 'sector': sector, 'tipo': tipo,
        'alias': al,
        'topicos': [x.lstrip('*') for x in tops],
        'nucleo': nucleo, 'contexto': contexto,
        # identidad = con lo que se matchea un registro (alias + razón social)
        'entidad': al + [_n(e) for e in ent.split('|') if e.strip()],
        'excluir': [_n(e) for e in exc.split('|') if e.strip()],
    }


EMPRESAS = ([_fila(t, 'empresa') for t in _RAW] +
            [_fila(t, 'gremio') for t in _RAW_GREMIOS])


def _re_frase(frase):
    """Regex de la frase con límites de palabra en los extremos. Es LA pieza que
    evita el ruido: 'claro' NO puede casar dentro de 'CLAROS MURCIA'."""
    return re.compile(r'(?<![a-z0-9])' + re.escape(frase) + r'(?![a-z0-9])')


_RX = {}


def _casa(frase, texto_n):
    rx = _RX.get(frase)
    if rx is None:
        rx = _RX[frase] = _re_frase(frase)
    return bool(rx.search(texto_n))


def empresas_en(query):
    """Empresas/gremios que la consulta nombra. Match por alias como palabra
    completa: 'sanciones a rappi' ✓, 'clarisa' ✗."""
    qn = _n(query)
    if not qn:
        return []
    return [e for e in EMPRESAS if any(_casa(a, qn) for a in e['alias'])]


def topicos_de(emps, ampliar=False):
    """Llaves de SINONIMOS que activan estas empresas, sin repetir y en orden.
    Por defecto solo el NÚCLEO (precisión); `ampliar=True` suma el contexto."""
    campos = ('nucleo', 'contexto') if ampliar else ('nucleo',)
    out, vistos = [], set()
    for e in emps:
        for campo in campos:
            for t in e[campo]:
                if t not in vistos:
                    vistos.add(t)
                    out.append(t)
    return out


def casa_registro(emp, texto):
    """¿Este registro (sanción, norma, contrato) es DE esta empresa? Palabra
    completa sobre su identidad, y `excluir` tiene la última palabra."""
    tn = _n(texto)
    if not tn:
        return False
    if any(_casa(x, tn) for x in emp['excluir']):
        return False
    return any(_casa(x, tn) for x in emp['entidad'])


def casa_registro_any(emps, texto):
    """¿El registro es de ALGUNA de estas empresas?"""
    return any(casa_registro(e, texto) for e in emps)


def filtrar_registros(emps, registros, campos):
    """Registros que pertenecen a alguna de las empresas. `campos` es la lista de
    llaves donde vive el nombre de la entidad (p. ej. ['sancionado'] en el pilar
    Regulatorio — NO el blob completo, que trae el motivo y mete ruido)."""
    out = []
    for r in registros:
        texto = ' '.join(str(r.get(c) or '') for c in campos)
        for e in emps:
            if casa_registro(e, texto):
                out.append(r)
                break
    return out


def _cli():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'verificar'
    if cmd == 'buscar':
        q = ' '.join(sys.argv[2:])
        for e in empresas_en(q):
            print(f"{e['nombre']}  [{e['tipo']} · {e['sector']}]")
            print('   tópicos:', ', '.join(e['topicos']))
            print('   identidad:', ' | '.join(e['entidad']))
        return
    # verificar: llaves de tópico inexistentes + alias que chocan entre empresas
    from caudal_core import SINONIMOS
    validas = {t['k'] for t in SINONIMOS}
    malas = [(e['k'], t) for e in EMPRESAS for t in e['topicos'] if t not in validas]
    print(f'{len(EMPRESAS)} entradas '
          f"({sum(1 for e in EMPRESAS if e['tipo']=='empresa')} empresas, "
          f"{sum(1 for e in EMPRESAS if e['tipo']=='gremio')} gremios) · "
          f'{len(validas)} tópicos en el tesauro')
    print('llaves de tópico inválidas:', malas or 'ninguna')
    ks = [e['k'] for e in EMPRESAS]
    print('llaves duplicadas:', [k for k in set(ks) if ks.count(k) > 1] or 'ninguna')
    choques = []
    for e in EMPRESAS:
        for o in EMPRESAS:
            if e is o:
                continue
            for a in e['alias']:
                if any(_casa(a, x) for x in o['alias']):
                    choques.append((a, e['k'], o['k']))
    print('alias que chocan entre entradas:', choques or 'ninguno')


if __name__ == '__main__':
    _cli()
