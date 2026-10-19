/* Candidaturas por LISTA CERRADA · tabla curada a mano (19-oct-2026)
   ─────────────────────────────────────────────────────────────────────────
   En una lista cerrada la Registraduría solo registra el voto al logo
   (COD_CAN 0): los candidatos no existen en el GCS, ni con cero votos. Sin
   esta tabla, quien encabezó o salió por una lista cerrada «no compitió» ese
   año en Candidato 360. candidato-360.js (candidaturasPorListaCerrada) las
   suma al historial de la persona como registros SIN voto propio.

   Reglas:
   · Solo entra lo que tiene fuente; cada lista trae las suyas.
   · `renglon: null` = el orden no está verificado (no se adivina).
   · `elegidos` es la DECLARATORIA original. Los reemplazos posteriores van en
     `nota`, no en la lista.
   · `cabeza` se registra aunque la lista no haya sacado curul.
   · `votosLista` es el escrutinio (índice concejo-AAAA, campo `listas`).

   ⚠ Concejo de Bogotá: la cifra repartidora se aplica sobre 44 curules; la 45
   es la del Estatuto de la Oposición (Galán en 2019, Oviedo en 2023). Con 45 el
   Pacto 2023 saldría con 8 curules; la declaratoria le dio 7. */
window.Candidato360ListasCerradas = [
  { anio: 2019, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'PARTIDO COLOMBIA JUSTA LIBRES', votosLista: 101604, curules: 2,
    cabeza: 'EMEL ROJAS CASTILLO',
    elegidos: [{ nombre: 'EMEL ROJAS CASTILLO', renglon: 1 }, { nombre: 'MARCO FIDEL ACOSTA RICO', renglon: 2 }],
    nota: 'Renglón 2 deducido: lista cerrada con 2 curules.',
    fuentes: ['https://www.eltiempo.com/bogota/candidatos-al-concejo-de-bogota-417146',
      'https://bogota.gov.co/mi-ciudad/gestion-publica/los-45-concejales-de-bogota-que-ya-tomaron-posesion-de-su-cargo',
      'https://sabanerox.com/2019/10/28/como-queda-el-concejo-de-bogota-para-el-periodo-2020-2023/'] },
  { anio: 2019, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'COAL. COLOMBIA HUMANA', votosLista: 188804, curules: 4,
    cabeza: null,
    elegidos: [{ nombre: 'ANA TERESA BERNAL MONTAÑEZ', renglon: null }, { nombre: 'HEIDY LORENA SANCHEZ BARRETO', renglon: null },
      { nombre: 'ATI SEYGUNDIBA QUIGUA IZQUIERDO', renglon: null }, { nombre: 'MARIA SUSANA MUHAMAD GONZALEZ', renglon: 4 }],
    nota: 'Coalición Colombia Humana - UP. El orden de los renglones 1 a 3 no está verificado. La 4.ª curul la anuló el Tribunal Administrativo de Cundinamarca (9-jun-2022, confirmado por el Consejo de Estado) y pasó a Cambio Radical.',
    fuentes: ['https://www.consejodeestado.gov.co/wp-content/uploads/2022/ConcBta.pdf',
      'https://bogota.gov.co/mi-ciudad/gestion-publica/los-45-concejales-de-bogota-que-ya-tomaron-posesion-de-su-cargo',
      'https://www.elespectador.com/bogota/por-decision-judicial-colombia-humana-pierde-curul-en-el-concejo-de-bogota/'] },
  { anio: 2019, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'PARTIDO COLOMBIA RENACIENTE', votosLista: 25057, curules: 0,
    cabeza: 'CLARA EUGENIA LOPEZ OBREGON', elegidos: [],
    nota: 'No superó el umbral (32.713 votos).',
    fuentes: ['https://www.noticiasrcn.com/bogota/elizabeth-loaiza-quiere-llegar-al-concejo-de-bogota-345346'] },
  { anio: 2023, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'PACTO HISTORICO', votosLista: 381804, curules: 7,
    cabeza: 'HEIDY LORENA SANCHEZ BARRETO',
    elegidos: [{ nombre: 'HEIDY LORENA SANCHEZ BARRETO', renglon: 1 }, { nombre: 'ANA TERESA BERNAL MONTAÑEZ', renglon: 2 },
      { nombre: 'ROCIO DUSSAN PEREZ', renglon: 3 }, { nombre: 'OSCAR FERNANDO BASTIDAS JACANAMIJOY', renglon: 4 },
      { nombre: 'JOSE DEL CARMEN CUESTA NOVOA', renglon: 5 }, { nombre: 'QUENA MARIA RIBADENEIRA MIÑO', renglon: 6 },
      { nombre: 'DONKA ATANASSOVA IAKIMOVA', renglon: 7 }],
    nota: 'Desde jun-2025 Jairo Alonso Avellaneda García (renglón 8) ocupa la curul de oposición que dejó Juan Daniel Oviedo (Resolución 002 de 2025 del Concejo, recálculo del CNE).',
    fuentes: ['https://www.publimetro.co/bogota/2023/09/21/quienes-estan-en-la-lista-cerrada-al-concejo-de-bogota-del-pacto-historico/',
      'https://bogota.gov.co/mi-ciudad/gobierno/como-quedo-conformado-el-concejo-de-bogota-del-periodo-2024-2027',
      'https://concejodebogota.gov.co/concejo/site/docs/20250311/asocfile/20250311171233/edicion_777_resolucion_002_del_2025.pdf'] },
  { anio: 2023, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'PARTIDO POLÍTICO CREEMOS', votosLista: 5207, curules: 0,
    cabeza: 'LUIS ALBERTO MOORE PEREA', elegidos: [],
    fuentes: ['https://www.eltiempo.com/bogota/luis-moore-creemos-opinion-815999',
      'https://www.elnuevosiglo.com.co/politica/estas-son-las-listas-al-concejo-de-bogota'] },
  { anio: 2023, corpLabel: 'CONCEJO', circunscripcion: 'BOGOTÁ D.C.', dep: '16', mun: '001',
    partido: 'PARTIDO LIGA GOBERNANTES ANTICORRUPCIÓN - LIGA', votosLista: 4924, curules: 0,
    cabeza: 'YADIRA JIMENEZ ROMERO', elegidos: [],
    fuentes: ['https://www.elnuevosiglo.com.co/politica/estas-son-las-listas-al-concejo-de-bogota',
      'https://www.las2orillas.co/los-15-elegidos-por-los-partidos-para-encabezar-sus-listas-al-concejo-de-bogota/'] },
];
