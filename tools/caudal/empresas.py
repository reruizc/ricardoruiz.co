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

Formato de cada fila (tupla de 7 —u 8 con banderas—, compacta a propósito para
que 200 entradas sigan siendo legibles y editables):

  (k, nombre, sector, alias, topicos, entidad, excluir[, flags])

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
  flags    · ',' · opcional. Hoy solo 'extranjera' (ver abajo).

--- 'extranjera': la empresa que solo tiene una de las dos caras -------------

El modelo de arriba asume que la empresa existe jurídicamente en Colombia. Una
que NO —una exchange de cripto, una plataforma que le vende al usuario desde
afuera— usa la cara de TEMA con normalidad, pero la de IDENTIDAD solo a medias:
sale en PRENSA con su nombre propio, y NO puede salir en SECOP (no es
proveedor del Estado) ni tener acto de una super (no la vigila ninguna).

Sin marcarla, `es_razon_social` la trataría como local: el gate no encontraría
razón social, el pilar Contratación gastaría sus 6 consultas a Socrata para
nada y —peor— cualquier homónimo que el gate dejara pasar entraría como si
fuera ella. La bandera lo vuelve explícito: búscala en prensa, no la busques en
SECOP. `es_razon_social` y `empieza_por_marca` devuelven False de entrada, así
que el pilar responde `sin_contratos` (que es la verdad) en vez de un vacío sin
explicación. `casa_registro` NO se toca: prensa y Regulatorio siguen igual, y
el día que una super la sancione el acto aparece solo.

⚠ 'extranjera' NO es 'multinacional'. Pfizer, Bayer, Huawei y Holcim tienen
casa matriz afuera y filial acá: le venden al Estado y las sancionan las supers
—van SIN bandera, y marcarlas las sacaría de SECOP sin razón—. La bandera es
"no está inscrita en Colombia", no "es de afuera". Ante la duda, sin bandera:
el costo de no marcar una es unas consultas de más; el de marcar mal es
esconderle al cliente contratos que sí existen.

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
    ('teamfoods', 'Team Foods (Alianza Team)', 'alimentos', 'team foods|alianza team',
     'alimentos / etiquetado,*palma y biocombustibles', 'sociedad industrial de grasas vegetales sigra', ''),
    ('colombina', 'Colombina', 'alimentos', 'colombina', 'alimentos / etiquetado', '', ''),
    ('quala', 'Quala', 'alimentos', 'quala', 'alimentos / etiquetado', '', ''),
    ('casaluker', 'Casa Luker', 'alimentos', 'casa luker|luker', 'alimentos / etiquetado', '', ''),
    ('diageo', 'Diageo', 'alimentos', 'diageo', 'licores y tabaco,tributario', '', ''),
    ('pernod', 'Pernod Ricard', 'alimentos', 'pernod ricard', 'licores y tabaco', '', ''),
    ('coltabaco', 'Coltabaco (Philip Morris)', 'alimentos', 'coltabaco|philip morris',
     'licores y tabaco,tributario', '', ''),
    ('bat', 'British American Tobacco', 'alimentos', 'british american tobacco|protabaco',
     'licores y tabaco,tributario', '', ''),
    ('manuelita', 'Manuelita', 'alimentos', 'manuelita',
     'sector agropecuario,*palma y biocombustibles,alimentos / etiquetado', '', ''),
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
    # ⚠ 'ambiental' se mantiene CENTRAL: ya lo era, y bajarlo a contexto le
    # habría quitado alcance por defecto a la entrada — el ángulo ambiental es
    # justo el perfil de Daabon (palma orgánica certificada).
    ('daabon', 'Grupo Daabon', 'agro', 'daabon',
     'palma y biocombustibles,*ambiental / medio ambiente,*sector agropecuario', '', ''),
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

    # =====================================================================
    # ⑤ AMPLIACIÓN (ago-2026) · 388 -> ~525 entradas.
    # Derivada del DATO, no de memoria. Cada nombre se probó contra las tres
    # fuentes que ya tenemos antes de entrar (arnés en la nota de CLAUDE.md):
    #   · texto-index.json  → el articulado de las gacetas lo nombra
    #   · sanciones.jsonl   → tiene acto regulatorio propio (razón social real)
    #   · normativa.jsonl   → el Ejecutivo lo nombra
    # Los números al lado de cada bloque son esa medición, no una estimación.
    # Lo que NO se deriva y va curado a mano es el TEMA (a qué tópicos mapea,
    # cuál es núcleo y cuál contexto).
    # =====================================================================

    # ---- minería · el sector más flaco frente a su peso real -------------
    # Era 8 entradas para el sector que hace >50% de las exportaciones. La
    # regulación que de verdad los mueve no es solo 'minería': es la licencia
    # ambiental y la consulta previa, por eso van como segunda actividad
    # central ('*') y no como contexto.
    ('anglogold', 'AngloGold Ashanti', 'mineria', 'anglogold|anglogold ashanti',
     'mineria e hidrocarburos,*ambiental / medio ambiente,'
     'consulta previa / comunidades etnicas,laboral',
     'anglogold ashanti colombia', ''),          # texto=24
    ('cerromatoso', 'Cerro Matoso (South32)', 'mineria', 'cerro matoso|cerromatoso|south32',
     'mineria e hidrocarburos,*ambiental / medio ambiente,'
     'consulta previa / comunidades etnicas', '', ''),                    # texto=17
    ('continentalgold', 'Continental Gold (Zijin)', 'mineria', 'continental gold|zijin',
     'mineria e hidrocarburos,ambiental / medio ambiente', '', ''),
    ('minesa', 'Minesa', 'mineria', 'minesa|sociedad minera de santander',
     'mineria e hidrocarburos,*ambiental / medio ambiente', '', ''),      # texto=7
    ('redeagle', 'Red Eagle Mining', 'mineria', 'red eagle',
     'mineria e hidrocarburos,ambiental / medio ambiente', '', ''),       # texto=16
    ('carboandes', 'Carboandes', 'mineria', 'carboandes', 'mineria e hidrocarburos', '', ''),
    ('norcarbon', 'Norcarbón', 'mineria', 'norcarbon', 'mineria e hidrocarburos', '', ''),
    ('fenoco', 'Fenoco', 'mineria', 'fenoco',
     'mineria e hidrocarburos,*puertos y logistica,ambiental / medio ambiente', '', ''),

    # ---- hidrocarburos · operadoras, transporte y refinación -------------
    ('sierracol', 'SierraCol Energy', 'energia', 'sierracol', 'mineria e hidrocarburos', '', ''),
    ('oxy', 'Occidental de Colombia', 'energia', 'occidental de colombia|oxy colombia',
     'mineria e hidrocarburos', '', ''),
    ('hocol', 'Hocol', 'energia', 'hocol', 'mineria e hidrocarburos', '', ''),      # texto=6
    ('equion', 'Equión Energía', 'energia', 'equion', 'mineria e hidrocarburos', '', ''),
    ('mansarovar', 'Mansarovar Energy', 'energia', 'mansarovar',
     'mineria e hidrocarburos', '', ''),                                            # texto=10
    ('emeraldenergy', 'Emerald Energy', 'energia', 'emerald energy',
     'mineria e hidrocarburos', '', ''),
    ('tecpetrol', 'Tecpetrol', 'energia', 'tecpetrol', 'mineria e hidrocarburos', '', ''),
    ('lewisenergy', 'Lewis Energy', 'energia', 'lewis energy', 'mineria e hidrocarburos', '', ''),
    ('hupecol', 'Hupecol', 'energia', 'hupecol', 'mineria e hidrocarburos', '', ''),
    ('vetra', 'Vetra Energía', 'energia', 'vetra', 'mineria e hidrocarburos', '', ''),
    ('petrobras', 'Petrobras', 'energia', 'petrobras', 'mineria e hidrocarburos', '', ''),
    ('repsol', 'Repsol', 'energia', 'repsol', 'mineria e hidrocarburos', '', ''),
    ('exxonmobil', 'ExxonMobil', 'energia', 'exxonmobil|exxon mobil',
     'mineria e hidrocarburos', '', ''),                                            # texto=15
    ('chevron', 'Chevron', 'energia', 'chevron', 'mineria e hidrocarburos', '', ''),
    ('shellco', 'Shell Colombia', 'energia', 'shell colombia',
     'mineria e hidrocarburos', '', ''),
    ('cenit', 'Cenit Transporte y Logística', 'energia', 'cenit',
     'mineria e hidrocarburos,*puertos y logistica', 'cenit transporte', ''),       # texto=31
    ('ocensa', 'Ocensa', 'energia', 'ocensa',
     'mineria e hidrocarburos,puertos y logistica', '', ''),
    ('tgi', 'TGI · Transportadora de Gas Internacional', 'energia',
     'transportadora de gas internacional|tgi sa', 'energia y servicios publicos', '', ''),
    ('reficar', 'Refinería de Cartagena', 'energia', 'reficar|refineria de cartagena',
     'mineria e hidrocarburos,*ambiental / medio ambiente', '', ''),                # texto=21
    ('esenttia', 'Esenttia (Propilco)', 'industria', 'esenttia|propilco',
     'mineria e hidrocarburos,ambiental / medio ambiente', '', ''),
    ('monomeros', 'Monómeros', 'industria', 'monomeros',
     'sector agropecuario,*comercio exterior y aduanas', '', ''),                   # texto=26
    ('schlumberger', 'SLB (Schlumberger)', 'energia', 'schlumberger',
     'mineria e hidrocarburos', 'schlumberger surenco', ''),
    ('halliburton', 'Halliburton', 'energia', 'halliburton', 'mineria e hidrocarburos', '', ''),
    ('bakerhughes', 'Baker Hughes', 'energia', 'baker hughes', 'mineria e hidrocarburos', '', ''),

    # ---- generación y servicios públicos regionales ----------------------
    ('gecelca', 'Gecelca', 'energia', 'gecelca', 'energia y servicios publicos', '', ''),
    ('termocandelaria', 'Termocandelaria', 'energia', 'termocandelaria',
     'energia y servicios publicos', '', ''),
    ('tebsa', 'Tebsa', 'energia', 'tebsa|termobarranquilla',
     'energia y servicios publicos', '', ''),
    ('geb', 'Grupo Energía Bogotá', 'energia', 'grupo energia de bogota|grupo energia bogota',
     'energia y servicios publicos,*mineria e hidrocarburos', '', ''),
    ('ruitoque', 'Ruitoque ESP', 'energia', 'ruitoque', 'energia y servicios publicos', '', ''),
    ('enerca', 'Enerca', 'energia', 'enerca', 'energia y servicios publicos', '', ''),

    # ---- agua y aseo · el sector tenía 4 entradas ------------------------
    ('interaseo', 'Interaseo', 'agua', 'interaseo',
     'agua y saneamiento,*ambiental / medio ambiente', '', ''),                     # sanc=3
    ('cgrdonajuana', 'CGR Doña Juana', 'agua', 'cgr dona juana',
     'agua y saneamiento,*ambiental / medio ambiente', '', ''),                     # sanc=4
    ('promoambiental', 'Promoambiental', 'agua', 'promoambiental',
     'agua y saneamiento,ambiental / medio ambiente', '', ''),
    ('aguascartagena', 'Aguas de Cartagena', 'agua', 'aguas de cartagena|acuacar',
     'agua y saneamiento', '', ''),
    ('emvarias', 'Emvarias', 'agua', 'emvarias',
     'agua y saneamiento,ambiental / medio ambiente', '', ''),
    ('aguasmanizales', 'Aguas de Manizales', 'agua', 'aguas de manizales',
     'agua y saneamiento', '', ''),

    # ---- fiduciarias y comisionistas · el bloque más denso de sanciones ---
    # Todas salen del campo `sancionado` de sanciones.jsonl (Superfinanciera).
    # ⚠ El alias corto evita anidar con una entrada existente: 'fiduciaria la
    # previsora' contendría el alias 'la previsora' y dispararía un choque —
    # la razón social larga vive en `entidad`, que no participa del choque.
    ('fiduprevisora', 'Fiduprevisora', 'financiero', 'fiduprevisora',
     'sector financiero', 'fiduciaria la previsora', ''),                           # sanc=5
    ('fiduagraria', 'Fiduagraria', 'financiero', 'fiduagraria',
     'sector financiero,*sector agropecuario',
     'fiduciaria de desarrollo agropecuario', ''),                                  # sanc=4
    ('fidubogota', 'Fiduciaria Bogotá', 'financiero', 'fidubogota|fiduciaria bogota',
     'sector financiero', '', ''),                                                  # sanc=5
    ('fidupopular', 'Fiduciaria Popular', 'financiero', 'fiduciaria popular|fidupopular',
     'sector financiero', '', ''),                                                  # sanc=5
    ('fiduoccidente', 'Fiduciaria de Occidente', 'financiero',
     'fiduoccidente|fiduciaria de occidente', 'sector financiero', '', ''),         # sanc=7
    ('fidupetrolera', 'Fiduciaria Petrolera', 'financiero', 'fiduciaria petrolera|fidupetrol',
     'sector financiero', '', ''),                                                  # sanc=5
    ('fiducentral', 'Fiduciaria Central', 'financiero', 'fiduciaria central',
     'sector financiero', '', ''),
    ('proyectarvalores', 'Proyectar Valores', 'financiero', 'proyectar valores',
     'sector financiero', '', ''),                                                  # sanc=12
    ('valoralta', 'Valoralta', 'financiero', 'valoralta', 'sector financiero', '', ''),
    ('progresionbolsa', 'Progresión Comisionista', 'financiero',
     'progresion sociedad comisionista', 'sector financiero',
     'progresion sociedad comisionista de bolsa', ''),                              # sanc=7
    ('profesionalesbolsa', 'Cía. de Profesionales de Bolsa', 'financiero',
     'profesionales de bolsa', 'sector financiero',
     'compania de profesionales de bolsa', ''),                                     # sanc=8
    ('mercanciasvalores', 'Mercancías y Valores', 'financiero', 'mercancias y valores',
     'sector financiero', '', ''),
    ('ualet', 'Ualet', 'financiero', 'ualet', 'sector financiero,tecnologia digital / IA', '', ''),
    ('alianzavalores', 'Alianza Valores', 'financiero', 'alianza valores',
     'sector financiero', '', ''),
    ('cfagropecuarios', 'Comisionistas Financieros Agropecuarios', 'financiero',
     'comisionistas financieros agropecuarios',
     'sector financiero,*sector agropecuario', '', ''),                             # sanc=6

    # ---- banca y sector solidario ----------------------------------------
    ('bancoserfinanza', 'Banco Serfinanza', 'financiero', 'banco serfinanza|serfinanza',
     'sector financiero', '', ''),
    ('bancomundomujer', 'Banco Mundo Mujer', 'financiero', 'banco mundo mujer|mundo mujer',
     'sector financiero', '', ''),
    ('confiar', 'Confiar Cooperativa', 'financiero', 'confiar cooperativa',
     'economia solidaria / cooperativas,*sector financiero', '', ''),
    ('cfantioquia', 'Cooperativa Financiera de Antioquia', 'financiero',
     'cooperativa financiera de antioquia',
     'economia solidaria / cooperativas,*sector financiero', '', ''),
    ('coopcentral', 'Banco Cooperativo Coopcentral', 'financiero',
     'coopcentral|banco cooperativo coopcentral',
     'economia solidaria / cooperativas,*sector financiero', '', ''),
    ('juriscoop', 'Juriscoop', 'financiero', 'juriscoop',
     'economia solidaria / cooperativas,sector financiero', '', ''),

    # ---- seguros · aseguradoras del Estado y generales -------------------
    # ⚠ 'positiva' NO puede ir suelta como alias: es un adjetivo corriente
    # ("acción positiva", "discriminación positiva") y dispararía la empresa
    # en consultas que no la nombran.
    ('segurosestado', 'Seguros del Estado', 'seguros', 'seguros del estado',
     'seguros', '', ''),
    ('positivaseg', 'Positiva Compañía de Seguros', 'seguros',
     'positiva compania de seguros|positiva seguros',
     'seguros,*laboral', '', ''),                                                   # norm=11
    ('segurosmundial', 'Seguros Mundial', 'seguros',
     'seguros mundial|compania mundial de seguros', 'seguros', '', ''),
    ('solidariaseg', 'Aseguradora Solidaria', 'seguros', 'aseguradora solidaria',
     'seguros,economia solidaria / cooperativas', '', ''),
    ('segurexpo', 'Segurexpo', 'seguros', 'segurexpo',
     'seguros,*comercio exterior y aduanas', '', ''),

    # ---- transporte masivo y concesiones viales --------------------------
    ('metrocinco', 'Metrocinco Plus', 'transporte', 'metrocinco',
     'puertos y logistica', 'metrocinco plus', ''),                                 # sanc=25
    ('movilizamos', 'Movilizamos', 'transporte', 'movilizamos', 'puertos y logistica', '', ''),
    ('egobus', 'Egobus', 'transporte', 'egobus', 'puertos y logistica', '', ''),
    ('coobus', 'Coobus', 'transporte', 'coobus', 'puertos y logistica', '', ''),
    ('ferrocarrilpacifico', 'Ferrocarril del Pacífico', 'transporte',
     'ferrocarril del pacifico', 'puertos y logistica', '', ''),                    # sanc=9
    ('coviandes', 'Coviandes', 'construccion', 'coviandes|concesionaria vial de los andes',
     'puertos y logistica', '', ''),
    ('coviandina', 'Coviandina', 'construccion', 'coviandina|concesionaria vial andina',
     'puertos y logistica', '', ''),
    ('devimed', 'Devimed', 'construccion', 'devimed', 'puertos y logistica', '', ''),
    ('spperinsula', 'Sociedad Portuaria de la Península', 'logistica',
     'sociedad portuaria de la peninsula', 'puertos y logistica', '', ''),

    # ---- empresas del Estado y certificación -----------------------------
    ('indumil', 'Indumil', 'industria', 'indumil|industria militar colombiana',
     'seguridad privada,*comercio exterior y aduanas', '', ''),                     # texto=76
    ('imprentanacional', 'Imprenta Nacional', 'industria', 'imprenta nacional',
     'comercio y retail', '', ''),
    ('servipostales', 'Servicios Postales Nacionales (4-72)', 'logistica',
     'servicios postales nacionales', 'puertos y logistica', '', ''),
    ('icontec', 'Icontec', 'servicios', 'icontec',
     'competencia y consumidor,comercio exterior y aduanas', '', ''),               # texto=216
    ('certicamara', 'Certicámara', 'tecnologia', 'certicamara',
     'tecnologia digital / IA,*datos personales / habeas data', '', ''),
    ('artesaniascol', 'Artesanías de Colombia', 'industria', 'artesanias de colombia',
     'comercio y retail,*turismo y hoteleria', '', ''),
    ('rtvc', 'RTVC', 'medios', 'rtvc|radio television nacional de colombia',
     'telecomunicaciones', '', ''),

    # ---- medios ----------------------------------------------------------
    ('elespectador', 'El Espectador', 'medios', 'el espectador',
     'telecomunicaciones', 'comunican sa', ''),
    ('bluradio', 'Blu Radio', 'medios', 'blu radio', 'telecomunicaciones', '', ''),
    ('teleantioquia', 'Teleantioquia', 'medios', 'teleantioquia', 'telecomunicaciones', '', ''),
    ('telecafe', 'Telecafé', 'medios', 'telecafe', 'telecomunicaciones', '', ''),

    # ---- infraestructura de telecom y TI ---------------------------------
    ('huawei', 'Huawei', 'tecnologia', 'huawei',
     'telecomunicaciones,*tecnologia digital / IA,comercio exterior y aduanas', '', ''),
    ('ericsson', 'Ericsson', 'tecnologia', 'ericsson', 'telecomunicaciones', '', ''),
    ('nokia', 'Nokia', 'tecnologia', 'nokia', 'telecomunicaciones', '', ''),
    ('digitalware', 'Digital Ware', 'tecnologia', 'digital ware',
     'tecnologia digital / IA', '', ''),

    # ---- salud · clínicas, IPS y EPS (3ª tanda) --------------------------
    ('medilaser', 'Clínica Medilaser', 'salud', 'medilaser|clinica medilaser',
     'salud / EPS e IPS', '', ''),
    ('dumian', 'Dumian Medical', 'salud', 'dumian medical|dumian',
     'salud / EPS e IPS', '', ''),                                                  # sanc=15
    ('oncologosocc', 'Oncólogos del Occidente', 'salud',
     'oncologos del occidente|oncologos de occidente', 'salud / EPS e IPS', '', ''),
    ('coltrasplantes', 'Colombiana de Trasplantes', 'salud', 'colombiana de trasplantes',
     'salud / EPS e IPS', '', ''),
    ('saludbolivar', 'Salud Bolívar EPS', 'salud', 'salud bolivar eps',
     'salud / EPS e IPS', '', ''),
    ('cruzblanca', 'Cruz Blanca EPS', 'salud', 'cruz blanca eps', 'salud / EPS e IPS', '', ''),
    ('colsaludcia', 'Compañía Colombiana de Salud', 'salud', 'colsalud',
     'salud / EPS e IPS', 'compania colombiana de salud colsalud', ''),

    # ---- cajas de compensación -------------------------------------------
    ('cajacopi', 'Cajacopi', 'salud', 'cajacopi', 'salud / EPS e IPS,*laboral', '', ''),
    ('comfacor', 'Comfacor', 'salud', 'comfacor', 'salud / EPS e IPS,*laboral', '', ''),
    ('comfaoriente', 'Comfaoriente', 'salud', 'comfaoriente',
     'salud / EPS e IPS,*laboral', '', ''),

    # ---- droguerías y distribución farmacéutica --------------------------
    ('pasteur', 'Droguerías Pasteur', 'farma', 'droguerias pasteur|distribuidora pasteur',
     'farmaceutico / medicamentos,comercio y retail', '', ''),
    ('copservir', 'Copservir', 'farma', 'copservir',
     'farmaceutico / medicamentos,*economia solidaria / cooperativas', '', ''),
    ('locatel', 'Locatel', 'farma', 'locatel',
     'farmaceutico / medicamentos,comercio y retail', '', ''),

    # ---- retail y consumo (3ª tanda) -------------------------------------
    ('la14', 'Almacenes La 14', 'retail', 'almacenes la 14', 'comercio y retail', '', ''),
    ('surtimax', 'Surtimax', 'retail', 'surtimax', 'comercio y retail', '', ''),
    ('cooratiendas', 'Cooratiendas', 'retail', 'cooratiendas',
     'comercio y retail,*economia solidaria / cooperativas', '', ''),
    ('merqueo', 'Merqueo', 'retail', 'merqueo',
     'comercio y retail,tecnologia digital / IA', '', ''),
    ('inditex', 'Inditex (Zara)', 'textil', 'inditex',
     'comercio y retail,*comercio exterior y aduanas', '', ''),

    # ---- motos y automotriz · el parque real del país ---------------------
    ('auteco', 'Auteco', 'automotriz', 'auteco',
     'comercio exterior y aduanas,*puertos y logistica', '', ''),
    ('incolmotos', 'Incolmotos Yamaha', 'automotriz', 'incolmotos|yamaha',
     'comercio exterior y aduanas', '', ''),
    ('fanalca', 'Fanalca', 'automotriz', 'fanalca',
     'comercio exterior y aduanas,*puertos y logistica', '', ''),
    ('aktmotos', 'AKT Motos', 'automotriz', 'akt motos', 'comercio exterior y aduanas', '', ''),

    # ---- alimentos y agro (3ª tanda) -------------------------------------
    ('macpollo', 'Avidesa Mac Pollo', 'agro', 'mac pollo|avidesa',
     'sector agropecuario,*alimentos / etiquetado', '', ''),
    ('florhuila', 'Flor Huila', 'agro', 'florhuila', 'sector agropecuario', '', ''),
    ('levapan', 'Levapan', 'alimentos', 'levapan', 'alimentos / etiquetado', '', ''),
    ('harineravalle', 'Harinera del Valle', 'alimentos', 'harinera del valle',
     'alimentos / etiquetado,*sector agropecuario', '', ''),
    ('arrozdiana', 'Arroz Diana', 'agro', 'arroz diana|diana corporacion',
     'sector agropecuario,alimentos / etiquetado', '', ''),
    ('superalimentos', 'Super de Alimentos', 'alimentos', 'super de alimentos',
     'alimentos / etiquetado', '', ''),

    # ---- licoreras departamentales · monopolio rentístico ----------------
    ('fla', 'Fábrica de Licores de Antioquia', 'alimentos',
     'fabrica de licores de antioquia|licorera de antioquia',
     'licores y tabaco,*tributario', '', ''),
    ('ilc', 'Industria Licorera de Caldas', 'alimentos',
     'industria licorera de caldas|licorera de caldas',
     'licores y tabaco,*tributario', '', ''),
    ('elc', 'Empresa de Licores de Cundinamarca', 'alimentos',
     'empresa de licores de cundinamarca|licorera de cundinamarca',
     'licores y tabaco,*tributario', '', ''),

    # =====================================================================
    # ⑥ PALMA Y CONSTRUCCIÓN (ago-2026) · 529 -> 583 entradas.
    # Los dos sectores tenían un problema distinto y cada uno pidió lo suyo:
    #
    #  · PALMA existía como 4 entradas colgadas de 'sector agropecuario', que
    #    es el corpus de TODO el agro: el cliente palmero se perdía entre café,
    #    arroz y ganadería. Ahora tienen tópico propio y el agro queda como
    #    segunda actividad central ('*'), así que la búsqueda por defecto trae
    #    las dos cosas y no encoge.
    #  · CONSTRUCCIÓN ya tenía 16, pero le faltaba la mitad del negocio: quien
    #    construye vivienda y quien hace obra pública son clientes distintos,
    #    con regulación distinta, y el diccionario los metía en el mismo saco.
    #
    # La evidencia también salió distinta, y conviene saberlo:
    #  · palma vive en el ARTICULADO (texto-index: 'biocombustibles' 311,
    #    'biodiesel' 140, 'palmicultor' 40) y NO en Regulatorio — INVIMA, SIC y
    #    Superfinanciera no regulan cultivadores. Su regulador es la ANLA, que
    #    todavía no es una fuente de Caudal.
    #  · construcción vive en SECOP, donde es proveedor con nombre propio
    #    (Coninsa 11 contratos · Mincivil 8 · Acesco 6 · Holcim 2). Ojo: los
    #    grandes de infraestructura licitan en CONSORCIO, y `es_razon_social`
    #    los rechaza a propósito — por eso Conconcreto sale con pocos. Es la
    #    precisión funcionando, no un hueco que haya que tapar aflojándola.
    # =====================================================================

    # ---- palma · plantaciones, extractoras y biodiésel --------------------
    ('indupalma', 'Indupalma', 'agro', 'indupalma',
     'palma y biocombustibles,*sector agropecuario,laboral', '', ''),          # texto=6
    ('poligrow', 'Poligrow', 'agro', 'poligrow',
     'palma y biocombustibles,*sector agropecuario,'
     'ambiental / medio ambiente,consulta previa / comunidades etnicas', '', ''),  # texto=16
    ('guaicaramo', 'Guaicaramo', 'agro', 'guaicaramo',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('gradesa', 'Gradesa', 'agro', 'gradesa',
     'palma y biocombustibles,*alimentos / etiquetado', '', ''),               # texto=8
    ('santandereanaceites', 'Santandereana de Aceites', 'agro',
     'santandereana de aceites', 'palma y biocombustibles,*sector agropecuario', '', ''),
    ('oleoflores', 'Oleoflores', 'agro', 'oleoflores',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('palmascesar', 'Palmas del Cesar', 'agro', 'palmas del cesar',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('palmerascosta', 'Palmeras de la Costa', 'agro', 'palmeras de la costa',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('unipalma', 'Unipalma', 'agro', 'unipalma',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('lacabana', 'Hacienda La Cabaña', 'agro', 'hacienda la cabana',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('palmaroriente', 'Palmar del Oriente', 'agro', 'palmar del oriente',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    ('murgas', 'Grupo Murgas', 'agro', 'grupo murgas',
     'palma y biocombustibles,*sector agropecuario', '', ''),
    # biodiésel · la salida industrial de la palma, y donde está el debate
    # regulatorio de verdad (mezcla obligatoria, precio, exención tributaria)
    ('ecodiesel', 'Ecodiesel Colombia', 'energia', 'ecodiesel',
     'palma y biocombustibles,*energia y servicios publicos,tributario', '', ''),
    ('biod', 'Bio D', 'energia', 'bio d sas|biodiesel bio d',
     'palma y biocombustibles,*energia y servicios publicos', '', ''),
    ('odinenergy', 'Odin Energy', 'energia', 'odin energy',
     'palma y biocombustibles,energia y servicios publicos', '', ''),
    ('acepalma', 'Acepalma', 'agro', 'acepalma',
     'palma y biocombustibles,*comercio exterior y aduanas', '', ''),
    ('cenipalma', 'Cenipalma', 'agro', 'cenipalma',
     'palma y biocombustibles,*sector agropecuario', '', ''),                  # texto=28

    # ---- cemento, acero y materiales -------------------------------------
    ('holcim', 'Holcim Colombia', 'construccion', 'holcim',
     'vivienda y construccion,*ambiental / medio ambiente,'
     'competencia y consumidor', '', ''),                                      # texto=14 · SECOP
    ('cementostequendama', 'Cementos Tequendama', 'construccion',
     'cementos tequendama', 'vivienda y construccion', '', ''),
    ('titancementos', 'Cementos Titán', 'construccion', 'titan cementos|cementos titan',
     'vivienda y construccion', '', ''),
    ('cementosalion', 'Cementos Alión', 'construccion', 'cementos alion',
     'vivienda y construccion', '', ''),
    ('cementossanmarcos', 'Cementos San Marcos', 'construccion', 'cementos san marcos',
     'vivienda y construccion', '', ''),
    ('diaco', 'Gerdau Diaco', 'industria', 'diaco|gerdau',
     'vivienda y construccion,*comercio exterior y aduanas', '', ''),
    ('acesco', 'Acesco', 'industria', 'acesco',
     'vivienda y construccion,*comercio exterior y aduanas', '', ''),
    ('corpacero', 'Corpacero', 'industria', 'corpacero',
     'vivienda y construccion,comercio exterior y aduanas', '', ''),
    ('ladrillerasantafe', 'Ladrillera Santafé', 'construccion', 'ladrillera santafe',
     'vivienda y construccion,*ordenamiento territorial y urbanismo', '', ''),
    ('eternit', 'Eternit', 'construccion', 'eternit',
     'vivienda y construccion,*asbesto', '', ''),                              # texto=13
    ('pavco', 'Pavco Wavin', 'construccion', 'pavco|mexichem',
     'vivienda y construccion,*agua y saneamiento', '', ''),
    ('alfaceramica', 'Alfa', 'construccion', 'alfa ceramica|ceramica italia',
     'vivienda y construccion', '', ''),

    # ---- constructoras de vivienda ---------------------------------------
    ('coninsa', 'Coninsa Ramón H.', 'construccion', 'coninsa|coninsa ramon h',
     'vivienda y construccion,*obra publica y contratacion estatal', '', ''),   # SECOP=11
    ('cusezar', 'Cusezar', 'construccion', 'cusezar', 'vivienda y construccion', '', ''),
    ('prodesa', 'Prodesa', 'construccion', 'prodesa', 'vivienda y construccion', '', ''),
    ('arqconcreto', 'Arquitectura y Concreto', 'construccion', 'arquitectura y concreto',
     'vivienda y construccion', '', ''),
    ('londonogomez', 'Londoño Gómez', 'construccion', 'londono gomez',
     'vivienda y construccion', '', ''),
    ('constructoracapital', 'Constructora Capital', 'construccion', 'constructora capital',
     'vivienda y construccion', '', ''),
    ('oikos', 'Oikos', 'construccion', 'oikos', 'vivienda y construccion', '', ''),
    ('ospinas', 'Ospinas & Cía.', 'construccion', 'ospinas',
     'vivienda y construccion,*ordenamiento territorial y urbanismo', '', ''),
    ('apiros', 'Apiros', 'construccion', 'apiros', 'vivienda y construccion', '', ''),

    # ---- obra pública, vías y concesiones --------------------------------
    # Núcleo distinto al de vivienda a propósito: a este cliente lo mueven los
    # pliegos y la contratación estatal, no la política de vivienda.
    ('elcondor', 'Construcciones El Cóndor', 'construccion',
     'construcciones el condor', 'obra publica y contratacion estatal,*puertos y logistica',
     'construcciones el condor', ''),
    ('mincivil', 'Mincivil', 'construccion', 'mincivil',
     'obra publica y contratacion estatal,*puertos y logistica', '', ''),       # SECOP=8
    ('pavimentoscol', 'Pavimentos Colombia', 'construccion', 'pavimentos colombia',
     'obra publica y contratacion estatal,puertos y logistica', '', ''),
    ('gisaico', 'Gisaico', 'construccion', 'gisaico',
     'obra publica y contratacion estatal', '', ''),
    ('valorcon', 'Valorcon', 'construccion', 'valorcon',
     'obra publica y contratacion estatal', '', ''),
    ('icein', 'Grupo ICEIN', 'construccion', 'grupo icein',
     'obra publica y contratacion estatal', '', ''),
    ('estyma', 'Estyma', 'construccion', 'estyma',
     'obra publica y contratacion estatal', '', ''),
    ('hbestructuras', 'HB Estructuras Metálicas', 'construccion', 'hb estructuras',
     'obra publica y contratacion estatal,vivienda y construccion', '', ''),
    ('solarte', 'Grupo Solarte', 'construccion', 'grupo solarte|solarte y solarte',
     'obra publica y contratacion estatal,*puertos y logistica', '', ''),
    ('mhc', 'Mario Huertas Cotes', 'construccion', 'mario huertas cotes|mhc ingenieria',
     'obra publica y contratacion estatal,*puertos y logistica', '', ''),
    ('via40express', 'Vía 40 Express', 'construccion', 'via 40 express',
     'puertos y logistica,*obra publica y contratacion estatal', '', ''),       # texto=43
    ('autopistasnordeste', 'Autopistas del Nordeste', 'construccion',
     'autopistas del nordeste', 'puertos y logistica', '', ''),
    ('covioriente', 'Covioriente', 'construccion', 'covioriente',
     'puertos y logistica', '', ''),
    ('metrobogota', 'Metro de Bogotá', 'transporte', 'metro de bogota|empresa metro de bogota',
     'puertos y logistica,*obra publica y contratacion estatal', '', ''),

    # ---- contratantes públicos de obra ------------------------------------
    # No son clientes, pero SÍ son la contraparte que el cliente rastrea: el
    # pliego, la adjudicación y la interventoría salen de acá.
    ('invias', 'Invías', 'construccion', 'invias|instituto nacional de vias',
     'obra publica y contratacion estatal,*puertos y logistica', '', ''),       # norm=7
    ('ani', 'ANI · Agencia Nacional de Infraestructura', 'construccion',
     'agencia nacional de infraestructura',
     'obra publica y contratacion estatal,*puertos y logistica', '', ''),       # norm=7
    ('enterritorio', 'Enterritorio', 'construccion', 'enterritorio',
     'obra publica y contratacion estatal,*vivienda y construccion',
     'empresa nacional promotora del desarrollo territorial', ''),              # texto=16

    # =====================================================================
    # ⑦ CRIPTOACTIVOS (ago-2026) · el primer sector que el diccionario no podía
    # representar, porque casi todo él es EXTRANJERO (ver la bandera arriba).
    #
    # El síntoma medido: «Binance» no estaba → no se podía poner de vigilada en
    # un perfil → el perfil quedaba sin identidad → la prensa nunca disparaba, y
    # eso con la acción `medios` devolviendo 15 titulares suyos en 7 días. El
    # cliente no recibía nada de una empresa que la prensa cubre a diario.
    #
    # Las tres fuentes, medidas una por una sobre el dataset local (ago-2026):
    #   · sanciones.jsonl (62.538) → 0 para las 15. Ninguna la vigila una super.
    #   · normativa.jsonl (11.611) → 0. El Ejecutivo no las nombra.
    #   · títulos del Congreso     → 0 por marca; el debate es por ACTIVIDAD
    #     (el tópico nuevo del tesauro), que es justo lo que el diccionario
    #     traduce.
    # Esos ceros no son un hueco del dato: son el retrato de una industria sin
    # presencia jurídica local. Por eso van con bandera y su pilar es prensa.
    #
    # ⚠ Ningún alias de una palabra corriente: 'buda' (Buda) y 'panda' (medido:
    # 1 acto de la ANLA para un producto que se llama así) van COMPUESTOS.
    # Gemini y Circle quedaron FUERA del todo: 'gemini' choca de frente con el
    # modelo de Google, que es justo lo que domina la prensa de tecnología, y
    # 'circle' es una palabra inglesa suelta. Entran el día que valgan un alias
    # compuesto que alguien de verdad escriba, no con la marca pelada.
    # =====================================================================
    ('binance', 'Binance', 'cripto', 'binance',
     'criptoactivos y activos virtuales,sector financiero,tributario,'
     'competencia y consumidor',
     'binance holdings', '', 'extranjera'),
    ('coinbase', 'Coinbase', 'cripto', 'coinbase',
     'criptoactivos y activos virtuales,sector financiero,tributario', '', '', 'extranjera'),
    ('kraken', 'Kraken', 'cripto', 'kraken',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('bybit', 'Bybit', 'cripto', 'bybit',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('okx', 'OKX', 'cripto', 'okx',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('kucoin', 'KuCoin', 'cripto', 'kucoin',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('cryptocom', 'Crypto.com', 'cripto', 'crypto com',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('bitfinex', 'Bitfinex', 'cripto', 'bitfinex',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    # las de la región · son las que de verdad operan sobre el peso colombiano
    ('bitso', 'Bitso', 'cripto', 'bitso',
     'criptoactivos y activos virtuales,sector financiero,tecnologia digital / IA',
     '', '', 'extranjera'),
    ('buda', 'Buda.com', 'cripto', 'buda com',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    # ⚠ RIPIO (exchange argentino) quedó FUERA, y no por poco peso: «ripio» es
    # una palabra corriente —el material de afirmado de una vía— y el control
    # de trampas la disparó con «ripio de construcción». En un país cuyo
    # Congreso legisla sobre vías, eso le mete una exchange al cliente de
    # infraestructura. Es la regla de siempre (ningún alias puede ser palabra
    # común suelta), y acá no hay compuesto que sirva: nadie escribe «ripio
    # exchange». Entra el día que la nombren distinto, no antes.
    ('lemoncash', 'Lemon Cash', 'cripto', 'lemon cash',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('banexcoin', 'Banexcoin', 'cripto', 'banexcoin',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    ('bitpoint', 'Bitpoint', 'cripto', 'bitpoint',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    # emisores de stablecoin · no son exchange, pero son la contraparte de todo
    # el debate de medios de pago y de la exposición cambiaria
    ('tether', 'Tether (USDT)', 'cripto', 'tether|usdt',
     'criptoactivos y activos virtuales,sector financiero,tributario', '', '', 'extranjera'),
    ('ripple', 'Ripple (XRP)', 'cripto', 'ripple|xrp',
     'criptoactivos y activos virtuales,sector financiero', '', '', 'extranjera'),
    # ⚠ Panda va SIN bandera: es colombiana (Medellín), así que sí puede
    # aparecer como proveedora o vigilada. Es el contraejemplo que muestra que
    # la bandera es por presencia jurídica y no por sector.
    ('pandaexchange', 'Panda Exchange', 'cripto', 'panda exchange',
     'criptoactivos y activos virtuales,sector financiero,tecnologia digital / IA', '', ''),
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
    ('acemi', 'ACEMI', 'salud', 'acemi',
     'salud / EPS e IPS,farmaceutico / medicamentos,laboral,tributario', '', ''),
    ('afidro', 'AFIDRO', 'farma', 'afidro',
     'farmaceutico / medicamentos,propiedad intelectual', '', ''),
    # ASINFAR es la CONTRAPARTE de AFIDRO en el mismo debate: la industria
    # nacional de genéricos frente a las multinacionales innovadoras. Mapea al
    # mismo vocabulario a propósito —el diccionario traduce temas, no toma
    # partido—, pero la patente es su pelea definitoria, no un contexto, así
    # que 'propiedad intelectual' va como segunda actividad central.
    ('asinfar', 'ASINFAR', 'farma', 'asinfar',
     'farmaceutico / medicamentos,*propiedad intelectual,'
     'salud / EPS e IPS,comercio exterior y aduanas',
     'asociacion de industrias farmaceuticas en colombia', ''),           # texto=10
    ('asocoldro', 'Asocoldro', 'farma', 'asocoldro', 'farmaceutico / medicamentos', '', ''),
    ('camacol', 'Camacol', 'construccion', 'camacol', 'vivienda y construccion', '', ''),
    ('cci', 'Cámara Colombiana de la Infraestructura', 'construccion',
     'camara colombiana de la infraestructura', 'puertos y logistica', '', ''),
    ('andesco', 'Andesco', 'servicios', 'andesco',
     'energia y servicios publicos,*agua y saneamiento,telecomunicaciones', '', ''),
    ('acolgen', 'Acolgen', 'energia', 'acolgen', 'energia y servicios publicos', '', ''),
    ('naturgas', 'Naturgas', 'energia', 'naturgas', 'energia y servicios publicos', '', ''),
    # Campetrol salió de este alias en ago-2026: es un gremio distinto (bienes
    # y servicios petroleros, no las operadoras) y ahora tiene entrada propia.
    ('acp', 'ACP · Asoc. Colombiana del Petróleo', 'energia',
     'asociacion colombiana del petroleo', 'mineria e hidrocarburos', '', ''),
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
    # ⑥ el núcleo pasa a ser palma: colgada solo de 'sector agropecuario', se
    # perdía en el corpus de todo el agro (café, arroz, ganadería). El agro
    # queda como segunda actividad central, así que no pierde alcance.
    ('fedepalma', 'Fedepalma', 'agro', 'fedepalma',
     'palma y biocombustibles,*sector agropecuario,ambiental / medio ambiente', '', ''),
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
    ('asobares', 'Asobares', 'comercio', 'asobares',
     'licores y tabaco,comercio y retail,tributario,'
     'ordenamiento territorial y urbanismo', '', ''),
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

    # ---- ⑤ ampliación ago-2026 · gremios que faltaban --------------------
    # El hueco más caro era el de minería e hidrocarburos: el gremio es quien
    # contrata, y el diccionario solo tenía 4 para todo el sector.
    ('campetrol', 'Campetrol', 'energia',
     'campetrol|camara colombiana de bienes y servicios petroleros',
     'mineria e hidrocarburos', '', ''),                                  # texto=15
    ('acipet', 'ACIPET · Ingenieros de Petróleos', 'energia', 'acipet',
     'mineria e hidrocarburos', '', ''),
    ('asoenergia', 'Asoenergía', 'energia', 'asoenergia',
     'energia y servicios publicos,*mineria e hidrocarburos', '', ''),
    ('asogravas', 'Asogravas', 'mineria', 'asogravas',
     'mineria e hidrocarburos,vivienda y construccion', '', ''),
    ('fedebiocombustibles', 'Fedebiocombustibles', 'energia', 'fedebiocombustibles',
     'energia y servicios publicos,*sector agropecuario', '', ''),
    ('asocolcanna', 'Asocolcanna', 'farma', 'asocolcanna',
     'cannabis,*farmaceutico / medicamentos', '', ''),                    # texto=6
    ('confecoop', 'Confecoop', 'multisectorial', 'confecoop',
     'economia solidaria / cooperativas,*sector financiero', '', ''),
    ('analfe', 'Analfe · Fondos de Empleados', 'multisectorial', 'analfe',
     'economia solidaria / cooperativas,*laboral', '', ''),
    ('asocajas', 'Asocajas', 'salud', 'asocajas',
     'laboral,*salud / EPS e IPS', '', ''),
    ('fedelonjas', 'Fedelonjas', 'construccion', 'fedelonjas',
     'vivienda y construccion', '', ''),
    ('asoportuaria', 'Asoportuaria', 'logistica', 'asoportuaria',
     'puertos y logistica,comercio exterior y aduanas', '', ''),
    ('fitac', 'FITAC · Agentes de Aduana', 'logistica', 'fitac',
     'comercio exterior y aduanas,*puertos y logistica', '', ''),
    ('asoleche', 'Asoleche', 'agro', 'asoleche',
     'sector agropecuario,alimentos / etiquetado', '', ''),
    ('ccmedellin', 'Cámara de Comercio de Medellín', 'multisectorial',
     'camara de comercio de medellin', 'comercio y retail,*tributario', '', ''),
    ('asocapitales', 'Asocapitales', 'multisectorial', 'asocapitales',
     'tributario,agua y saneamiento,puertos y logistica', '', ''),
    ('fedemunicipios', 'Federación Colombiana de Municipios', 'multisectorial',
     'federacion colombiana de municipios', 'tributario,agua y saneamiento', '', ''),

    # ---- ⑥ gremios de palma y construcción -------------------------------
    ('asograsas', 'Asograsas', 'agro', 'asograsas',
     'palma y biocombustibles,*alimentos / etiquetado', '', ''),               # texto=13
    ('asocreto', 'Asocreto', 'construccion', 'asocreto',
     'vivienda y construccion,*obra publica y contratacion estatal', '', ''),
    ('sci', 'Sociedad Colombiana de Ingenieros', 'construccion',
     'sociedad colombiana de ingenieros',
     'obra publica y contratacion estatal,*vivienda y construccion', '', ''),
    ('scarq', 'Sociedad Colombiana de Arquitectos', 'construccion',
     'sociedad colombiana de arquitectos',
     'ordenamiento territorial y urbanismo,*vivienda y construccion', '', ''),

    # ---- ⑦ el interlocutor local de un sector extranjero -------------------
    # Las 15 exchanges no tienen presencia jurídica acá, pero el proyecto de ley
    # de PSAV sí tiene quién lo negocie: Colombia Fintech es el gremio que se
    # sienta en esa mesa, y es colombiano (sin bandera: sí puede tener contrato
    # y sí lo puede sancionar una super). Su agenda no es SOLO cripto —crédito
    # digital, pagos, finanzas abiertas— así que el núcleo es doble: lo
    # financiero y lo cripto. Con cripto de contexto, el cliente que lo consulta
    # no vería por defecto el proyecto que está negociando.
    ('colombiafintech', 'Colombia Fintech', 'financiero', 'colombia fintech',
     'sector financiero,*criptoactivos y activos virtuales,'
     'tecnologia digital / IA,tributario,datos personales / habeas data',
     'asociacion colombiana de empresas de tecnologia e innovacion financiera', ''),
]


FLAGS_VALIDAS = {'extranjera'}


def _fila(t, tipo):
    # la 8ª posición (banderas) es opcional: las ~590 filas que no la traen
    # siguen siendo tuplas de 7 y no hay que tocarlas.
    k, nombre, sector, alias, top, ent, exc = t[:7]
    flags = {f.strip() for f in (t[7] if len(t) > 7 else '').split(',') if f.strip()}
    al = [_n(a) for a in alias.split('|') if a.strip()]
    tops = [x.strip() for x in top.split(',') if x.strip()]
    nucleo, contexto = [], []
    for i, x in enumerate(tops):
        # núcleo = la primera, más las marcadas con '*' (doble actividad central)
        (nucleo if (i == 0 or x.startswith('*')) else contexto).append(x.lstrip('*'))
    return {
        'k': k, 'nombre': nombre, 'sector': sector, 'tipo': tipo,
        'flags': sorted(flags),
        # sin presencia jurídica local → prensa sí, SECOP/supers no
        'extranjera': 'extranjera' in flags,
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


# --- razón social · el gate que pide SECOP ----------------------------------
# `casa_registro` (palabra completa + excluir) alcanza para el pilar Regulatorio,
# donde `sancionado` son decenas de nombres de empresa. En CONTRATACIÓN no: el
# proveedor de SECOP II son 5,87 M filas dominadas por PERSONAS NATURALES, y las
# marcas de este diccionario son nombres y apellidos corrientes en Colombia.
# Medido jul-2026 sobre el dataset real: de las filas que `casa_registro` deja
# pasar, 42/42 en «uber» ("JOSE UBER ESCOBAR", "UBER DANIEL CHARA CERON") y
# 34/34 en «claro» ("Álvaro José Claro Ríos") son personas, no la empresa.
# La lista `excluir` no puede cubrirlo: se curó contra decenas de sanciones, y
# acá el universo son millones de cédulas.
#
# El discriminador que sí funciona es la FORMA del nombre: una razón social es
# la marca más decoración societaria ("COMCEL S.A.", "Rappi S.A.S.",
# "BANCOLOMBIA"); una persona lleva la marca entre otros nombres propios. Se
# quita la decoración y se exige que lo que queda SEA la marca.
_DECOR = {
    'sas', 'sa', 's', 'a', 'as', 'ltda', 'limitada', 'esp', 'e', 'p', 'eice',
    'eu', 'sca', 'spa', 'inc', 'llc', 'ltd', 'plc', 'corp', 'cia', 'compania',
    'y', 'de', 'del', 'la', 'el', 'los', 'las', 'en', 'c', 'bic', 'zomac',
    'sucursal', 'colombia', 'colombiana', 'sucursales', 'nit', 'sociedad',
    'anonima', 'simplificada', 'sucursal colombia',
}
# Palabras de LÍNEA DE NEGOCIO: pueden acompañar a la marca sin dejar de ser la
# empresa ("Fiduciaria Bancolombia"). NO entran acá los marcadores de "otra
# entidad que solo menciona la marca" —cooperativa, consorcio, union, temporal,
# fundacion, asociacion, junta—, que son justo los falsos positivos medidos
# ("COOPERATIVA DE TRABADORES DE AVIANCA", "CONSORCIO CLARO HITSS").
_LINEA = {
    'telecomunicaciones', 'telefonia', 'movil', 'moviles', 'celular', 'soluciones',
    'servicios', 'energia', 'gas', 'seguros', 'seguros generales', 'vida',
    'fiduciaria', 'fiducia', 'banco', 'bancario', 'comisionista', 'bolsa',
    'eps', 'ips', 'salud', 'medicina', 'prepagada', 'alimentos', 'bebidas',
    'comercial', 'industrial', 'logistica', 'transporte', 'carga', 'aereo',
    'holding', 'group', 'international', 'andina', 'americas', 'sucursal',
    'pay', 'tecnologias', 'technologies', 'sistemas', 'digital',
}


def _tokens_marca(nombre):
    """Nombre sin decoración societaria → los tokens que de verdad identifican."""
    return [t for t in _n(nombre).split() if t not in _DECOR]


def es_razon_social(nombre, emp):
    """¿Este nombre ES la empresa, o solo la contiene? Verificado contra SECOP:
    ✓ 'COMCEL S.A.' · 'Rappi S.A.S.' · 'BANCOLOMBIA' · 'Fiduciaria Bancolombia'
    ✗ 'JOSE UBER ESCOBAR' · 'Álvaro José Claro Ríos' (personas naturales)
    ✗ 'COOPERATIVA DE TRABADORES DE AVIANCA' · 'CONSORCIO CLARO HITSS'
      (otras entidades legales que nombran la marca)
    Precisión antes que cobertura: una razón social larga que el diccionario no
    registre queda fuera, y el sitio correcto de arreglarlo es su campo
    `entidad`, no aflojar esta regla."""
    # una empresa sin presencia jurídica local no tiene razón social colombiana
    # que encontrar: lo que el gate deje pasar sería un homónimo, no ella.
    if emp.get('extranjera'):
        return False
    toks = _tokens_marca(nombre)
    if not toks:
        return False
    tn = _n(nombre)
    if any(_casa(x, tn) for x in emp['excluir']):
        return False
    for ident in emp['entidad']:
        it = _tokens_marca(ident)
        if not it:
            continue
        if toks == it:
            return True
        # la marca completa + palabras de línea de negocio ("Fiduciaria X")
        resto = list(toks)
        for t in it:
            if t not in resto:
                break
            resto.remove(t)
        else:
            if resto and all(t in _LINEA for t in resto):
                return True
    return False


def razon_social_any(emps, nombre):
    return any(es_razon_social(nombre, e) for e in emps)


def empieza_por_marca(nombre, emp):
    """Regla laxa para nombres de ENTIDAD PÚBLICA, donde no hay personas
    naturales y la marca encabeza la dependencia: 'SENA REGIONAL VALLE Grupo de
    Apoyo Administrativo Mixto' es el SENA comprando. Medido: sobre
    `nombre_entidad` no añade un solo falso en claro/uber/ecopetrol, y le suma
    al SENA los ~323 k contratos en que es la entidad contratante.
    NO usar sobre el proveedor: ahí 'UBER DANIEL CHARA CERON' también empieza
    por la marca."""
    if emp.get('extranjera'):     # tampoco es una entidad pública colombiana
        return False
    tk = _tokens_marca(nombre)
    if not tk:
        return False
    tn = _n(nombre)
    if any(_casa(x, tn) for x in emp['excluir']):
        return False
    for ident in emp['entidad']:
        it = _tokens_marca(ident)
        if it and tk[:len(it)] == it:
            return True
    return False


def marca_lidera_any(emps, nombre):
    return any(empieza_por_marca(nombre, e) for e in emps)


def sin_presencia_local(emps):
    """Las de la lista que no pueden aparecer en SECOP ni en actos de una super.

    Los dos gates de arriba ya las rechazan solos, así que nadie NECESITA llamar
    esto para que el filtro sea correcto. Sirve para otras dos cosas: decirle al
    usuario POR QUÉ su vigilada no tiene contratos (es un hecho de la empresa,
    no un hueco del dato) y ahorrarse el descubrimiento en Socrata cuando todas
    las de la consulta son extranjeras —hoy son 6 consultas que, por
    construcción, no pueden devolver nada—."""
    return [e['nombre'] for e in emps if e.get('extranjera')]


def solo_extranjeras(emps):
    """¿Ninguna de las nombradas tiene presencia jurídica local? (lista vacía →
    False: 'no hay empresas' no es 'todas son extranjeras')."""
    return bool(emps) and all(e.get('extranjera') for e in emps)


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
            marca = ' · SIN PRESENCIA LOCAL (prensa sí, SECOP no)' if e['extranjera'] else ''
            print(f"{e['nombre']}  [{e['tipo']} · {e['sector']}{marca}]")
            print('   tópicos:', ', '.join(e['topicos']))
            print('   identidad:', ' | '.join(e['entidad']))
        return
    # verificar: llaves de tópico inexistentes + alias que chocan entre empresas
    from caudal_core import SINONIMOS
    validas = {t['k'] for t in SINONIMOS}
    malas = [(e['k'], t) for e in EMPRESAS for t in e['topicos'] if t not in validas]
    print(f'{len(EMPRESAS)} entradas '
          f"({sum(1 for e in EMPRESAS if e['tipo']=='empresa')} empresas, "
          f"{sum(1 for e in EMPRESAS if e['tipo']=='gremio')} gremios · "
          f"{sum(1 for e in EMPRESAS if e['extranjera'])} sin presencia local) · "
          f'{len(validas)} tópicos en el tesauro')
    print('llaves de tópico inválidas:', malas or 'ninguna')
    # una bandera mal escrita no puede pasar en silencio: 'extrangera' dejaría a
    # la empresa tratada como local y de vuelta al problema que ⑦ resolvió.
    flags_malas = [(e['k'], f) for e in EMPRESAS for f in e['flags']
                   if f not in FLAGS_VALIDAS]
    print('banderas desconocidas:', flags_malas or 'ninguna')
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
