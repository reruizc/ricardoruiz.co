// Genera el documento descriptivo (.docx) que acompaña el Excel.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, TableOfContents, PageBreak,
} = require("docx");

const OUTDIR = path.join(__dirname, "..", "..", "Bases de datos", "output_cundi_edad_genero");
const D = JSON.parse(fs.readFileSync(path.join(OUTDIR, "doc-data.json"), "utf8"));

const OX = "8A1E16", INK = "1A1510", CREAM = "F4F0E7", GREY = "6B6258";
const CW = 9360; // content width US Letter, 1" margins
const GROUPS = ["18-25", "26-35", "36-45", "46-60", "61+"];

const fmt = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const pct = (x) => x.toFixed(1).replace(".", ",") + "%";

// ---- helpers ----
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
function P(text, opts = {}) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text, ...opts })];
  return new Paragraph({ children: runs, spacing: { after: 120, line: 276 },
    alignment: opts.center ? AlignmentType.CENTER : AlignmentType.JUSTIFIED });
}
const R = (t, o = {}) => new TextRun({ text: t, ...o });
function bullet(runs) {
  return new Paragraph({ numbering: { reference: "b", level: 0 },
    children: Array.isArray(runs) ? runs : [new TextRun(runs)], spacing: { after: 80, line: 270 } });
}
const border = { style: BorderStyle.SINGLE, size: 1, color: "D8CFC0" };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(content, w, { head = false, fill = null, align = AlignmentType.LEFT, bold = false } = {}) {
  const runs = (Array.isArray(content) ? content : [content]).map((c) =>
    typeof c === "string" ? new TextRun({ text: c, bold: head || bold,
      color: head ? "FFFFFF" : INK, size: head ? 18 : 18 }) : c);
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: { fill: head ? OX : (fill || "FFFFFF"), type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: align, children: runs })],
  });
}
function table(headers, rows, widths, aligns) {
  const al = aligns || headers.map(() => AlignmentType.LEFT);
  const head = new TableRow({ tableHeader: true, children:
    headers.map((h, i) => cell(h, widths[i], { head: true, align: al[i] })) });
  const body = rows.map((r, ri) => new TableRow({ children:
    r.map((v, i) => cell(v, widths[i], { align: al[i], fill: ri % 2 ? CREAM : null })) }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: widths,
    rows: [head, body].flat() });
}
const spacer = () => new Paragraph({ children: [], spacing: { after: 80 } });

// ---- party profile table ----
function partyTable(key) {
  const rows = D.party[key].map((r) => [
    r.p.length > 34 ? r.p.slice(0, 33) + "…" : r.p, fmt(r.tot), pct(r.muj),
    ...GROUPS.map((g) => pct(r[g])),
  ]);
  const w = [2680, 1040, 940, 940, 940, 940, 940, 940];
  const al = [AlignmentType.LEFT, AlignmentType.RIGHT, ...Array(6).fill(AlignmentType.CENTER)];
  return table(["Lista / partido", "Votos", "% muj", "18-25", "26-35", "36-45", "46-60", "61+"],
    rows, w, al);
}

// ================= documento =================
const content = [];

// portada
content.push(
  new Paragraph({ spacing: { before: 1200, after: 0 }, children: [
    new TextRun({ text: "Votación por municipio, partido, sexo y edad",
      bold: true, size: 40, color: OX, font: "Calibri" })] }),
  new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: "Cámara y Senado · Elecciones de 2022 y 2026 · Departamento de Cundinamarca",
      bold: true, size: 24, color: INK })] }),
  new Paragraph({ spacing: { after: 60 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: OX, space: 6 } }, children: [] }),
  new Paragraph({ spacing: { before: 120, after: 40 }, children: [
    new TextRun({ text: "Documento descriptivo del archivo ", size: 20, color: GREY }),
    new TextRun({ text: "Cundinamarca_Congreso_Edad_Genero_2022_2026.xlsx", size: 20, color: GREY, italics: true })] }),
  new Paragraph({ spacing: { after: 600 }, children: [
    new TextRun({ text: "Estimación por inferencia ecológica con cotas · Junio de 2026 · Borrador analítico",
      size: 20, color: GREY })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// 1. Resumen ejecutivo
content.push(H1("1. Resumen ejecutivo"));
content.push(P([
  R("Este documento acompaña el libro de Excel que estima, para los "),
  R("116 municipios de Cundinamarca", { bold: true }),
  R(" (departamento electoral 15, sin Bogotá), cuántos votos recibió cada lista al "),
  R("Senado y a la Cámara", { bold: true }),
  R(" desglosados por las diez combinaciones de "),
  R("sexo × grupo de edad", { bold: true }),
  R(" (Hombres y Mujeres en 18-25, 26-35, 36-45, 46-60 y 61+), tanto para cada partido como en general, en las elecciones de "),
  R("2022 y 2026", { bold: true }), R("."),
]));
content.push(P([
  R("La idea central que conviene tener presente: ", {}),
  R("las urnas nunca registran por quién votó cada grupo de edad o sexo", { bold: true }),
  R(". Por eso el desglose por partido es una "),
  R("estimación estadística (inferencia ecológica)", { italics: true }),
  R(", no un conteo. Para que sea defendible, cada cifra se acompaña de sus cotas y, por construcción, "),
  R("siempre cuadra con los totales reales", { bold: true }),
  R(" de cada municipio."),
]));
content.push(P("Hallazgos principales:", { bold: true }));
[
  [R("Choque generacional nítido. ", { bold: true }), R("El Pacto Histórico tiene el electorado más joven (en Cámara 2026, "+pct(D.party.CAMARA_2026[0]["18-25"])+" en 18-25 y apenas "+pct(D.party.CAMARA_2026[0]["61+"])+" con 61 o más). En el otro extremo, el Partido Conservador concentra "+pct(D.party.CAMARA_2026.find(r=>r.p.includes("CONSERVADOR"))["61+"])+" de su voto en mayores de 60; Cambio Radical, Liberal y Centro Democrático también envejecidos.")],
  [R("El sexo casi no mueve el voto. ", { bold: true }), R("El porcentaje de mujeres de una mesa no predice su votación (correlación ≈ 0). El reparto por sexo dentro de cada grupo de edad se mantiene cercano a la composición poblacional; un sesgo de sexo fuerte sería un artefacto del método, no un hallazgo.")],
  [R("La edad sí se identifica con fuerza. ", { bold: true }), R("La composición etaria varía mucho entre puestos y se correlaciona claramente con el voto (Pacto: +0,40 con el % de jóvenes, −0,34 con el % de mayores), así que el perfil de edad de cada lista es robusto.")],
  [R("Las estimaciones cuadran con la realidad. ", { bold: true }), R("La suma de las diez celdas reproduce exactamente la votación real de cada lista en cada municipio y la composición real de votantes (diferencia = 0).")],
].forEach((r) => content.push(bullet(r)));

// 2. Contenido del Excel
content.push(H1("2. Qué contiene el archivo de Excel"));
content.push(P("El libro tiene nueve hojas:"));
content.push(table(["Hoja", "Contenido"], [
  ["Léeme", "Metodología resumida y guía de lectura de las cotas."],
  ["Resumen depto", "Composición del electorado de cada lista (% de mujeres y % por edad) a nivel departamental."],
  ["General 2022 / 2026", "Votantes por sexo × edad en cada municipio. 2022 es dato observado; 2026 es proyección."],
  ["Senado 2022 / 2026", "Por lista: votos estimados por municipio × sexo × edad, con cotas e intervalo."],
  ["Cámara 2022 / 2026", "Igual que Senado, para la Cámara de Representantes."],
  ["Beta (motor)", "Parámetro β: % del voto de cada lista dentro de cada celda, con sus cotas duras."],
], [2200, 7160]));

// 3. Metodología
content.push(H1("3. Metodología"));

content.push(H2("3.1. Fuentes de datos"));
content.push(table(["Fuente", "Qué aporta"], [
  ["RNEC · Edad y Género", "Sufragantes por mesa × sexo × edad (joint), Congreso 2022. Es el dato que ancla la composición."],
  ["Escrutinio Congreso 2022 (GCS)", "Votos por mesa y por lista, Senado y Cámara, en Cundinamarca."],
  ["Declarados Congreso 2026 (RNEC)", "Votos por mesa y por lista, Senado y Cámara, en 2026 (escrutinio declarado)."],
  ["Proyecciones de población DANE", "Población por área, sexo y edad simple por departamento, 2018-2050. Base de la proyección 2026."],
], [3000, 6360]));

content.push(H2("3.2. Lo que es dato y lo que es estimación"));
content.push(P([
  R("El total de votantes por sexo y edad de cada municipio (hojas «General») es ", {}),
  R("dato observado", { bold: true }),
  R(" en 2022 y "), R("proyección demográfica", { bold: true }),
  R(" en 2026 (todavía no existe el archivo de Edad y Género de 2026). El desglose del voto por lista (hojas Senado/Cámara) es "),
  R("inferencia ecológica", { bold: true }),
  R(": se estima a partir de cómo cambia la votación entre puestos con distinta composición demográfica."),
]));

content.push(H2("3.3. El modelo de inferencia ecológica"));
content.push(P([
  R("Se usa un modelo de tablas (tipo Goodman/King, RxC). En cada unidad territorial —"),
  R("mesa en 2022", { bold: true }), R(" (~"+fmt(D.ctrl.mesas2022)+" mesas) y "),
  R("puesto en 2026", { bold: true }), R(" (~"+fmt(D.ctrl.puestos2026)+" puestos)— la fracción del voto de cada lista es una mezcla de sus preferencias por celda:"),
]));
content.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 }, children: [
  new TextRun({ text: "voto_lista / total = Σ  β(lista, celda) × composición(celda)", italics: true, size: 22, color: INK })] }));
content.push(P([
  R("Se estima β —el "), R("% del voto de cada lista dentro de cada celda", { italics: true }),
  R("— con mínimos cuadrados ponderados por votos, exigiendo que cada celda reparta el 100% entre las listas. El motor (hoja «Beta») muestra estos β con sus cotas."),
]));
content.push(P([R("Se usa la mesa como unidad en 2022 (composición observada) y el puesto en 2026, porque "),
  R("las mesas no se mantienen entre elecciones", { italics: true }),
  R(" (se reasignan por orden de cédula), mientras que los puestos sí persisten y permiten proyectar."),
]));

content.push(H2("3.4. Por qué siempre cuadra con la realidad (anclaje por raking)"));
content.push(P([
  R("La estructura de preferencias (β) se aprende a nivel departamental, pero en cada municipio la estimación se "),
  R("reajusta (raking iterativo) a dos márgenes que sí son observados", { bold: true }),
  R(": la votación real de cada lista y la composición real de votantes por celda. Así, la suma por lista da su voto real y la suma por celda da el total de votantes de esa celda. El β solo decide el reparto interno; los totales nunca se inventan."),
]));

content.push(H2("3.5. La proyección de 2026"));
content.push(P([
  R("Como no existe el Edad y Género de 2026, la composición de votantes por sexo y edad se proyecta así: se calcula la tasa de participación por celda en 2022 (votantes ÷ población DANE 2022), se aplica a la población DANE 2026 por sexo y edad del departamento, y se reajusta a los votantes reales de cada puesto en 2026. "),
  R("Supuesto", { bold: true }),
  R(": la forma del perfil de participación por sexo y edad es estable entre 2022 y 2026; el nivel lo fija el dato real de 2026. En el modelo presidencial análogo, este supuesto se validó con un backtest 2018→2022 (error nacional de 0,32 pp por banda)."),
]));

content.push(H2("3.6. La edad se identifica bien; el sexo casi no"));
content.push(P([
  R("Es la advertencia metodológica más importante. Las mesas de 2022 están "),
  R("segregadas por sexo", { bold: true }),
  R(" (el % de mujeres por mesa va de "+pct(D.diag.fem_sd>0?1.8:1.8)+" a casi 99%, con desviación de "+D.diag.fem_sd.toString().replace(".",",")+" pp), pero ese % "),
  R("no predice el voto", { bold: true }),
  R(" (correlación con el voto del Pacto = "+D.diag.pacto_fem.toString().replace(".",",")+"; con el Conservador = "+D.diag.cons_fem.toString().replace(".",",")+"). En cambio la edad sí: el % de jóvenes correlaciona +0,40 con el Pacto y el % de mayores −0,34."),
]));
content.push(P([
  R("Sin restricciones, el estimador aprovecha esa dirección no identificada y produce sesgos de sexo absurdos. Por eso se "),
  R("penaliza el contraste de sexo", { bold: true }),
  R(" dentro de cada grupo de edad (salvo que el dato lo sostenga), dejando la edad libre. Resultado: las diferencias H–M quedan por debajo de 2 pp y el reparto por sexo sigue la composición poblacional. La estimación de sexo más fina exigiría un método de efectos fijos de puesto a nivel mesa, pendiente."),
]));

content.push(H2("3.7. Cómo se mide la incertidumbre (tres columnas por celda)"));
[
  [R("punto", { bold: true }), R(" — estimación central; cuadra con los totales reales.")],
  [R("cota_min / cota_max", { bold: true }), R(" — cotas duras de Duncan-Davis (King): el rango que los datos permiten sin ningún supuesto, solo por aritmética de márgenes. Es lo defendible al 100% y suele ser ancho.")],
  [R("ic_lo / ic_hi", { bold: true }), R(" — intervalo del 90% por remuestreo (bootstrap) de municipios; refleja la incertidumbre del modelo de preferencias. Es más estrecho, pero depende del supuesto del modelo.")],
].forEach((r) => content.push(bullet(r)));

// 4. Cómo leer
content.push(H1("4. Cómo leer las tablas: un ejemplo"));
content.push(P([
  R("En la hoja «Cámara 2026», filtrando por Soacha y el Movimiento Político Pacto Histórico (total real "),
  R(fmt(D.soacha.tot) + " votos", { bold: true }), R("), las diez celdas se ven así:"),
]));
content.push(table(
  ["Sexo", "Edad", "Votos (est.)", "Cota mín", "Cota máx", "IC90"],
  D.soacha.rows.map((r) => [r.sx, r.g, fmt(r.pt), fmt(r.lo), fmt(r.hi), fmt(r.il) + "–" + fmt(r.ih)]),
  [1500, 1260, 1700, 1500, 1500, 1900],
  [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.CENTER]
));
content.push(P([
  R("Se lee: «se estima que ~"+fmt(D.soacha.rows.find(r=>r.sx==="Mujeres"&&r.g==="26-35").pt)+" votos del Pacto en Soacha vinieron de mujeres de 26-35». La "),
  R("cota máxima", { italics: true }),
  R(" indica el techo que la aritmética permite; el "),
  R("IC90", { italics: true }),
  R(" es el rango más probable según el modelo. La suma de las diez celdas da exactamente "+fmt(D.soacha.tot)+"."),
]), );

// 5. Hallazgos
content.push(new Paragraph({ children: [new PageBreak()] }));
content.push(H1("5. Hallazgos"));

content.push(H2("5.1. Composición general del electorado"));
content.push(P("Distribución de todos los votantes de Cundinamarca por grupo de edad (ambos sexos) y participación de mujeres. 2022 es observado; 2026, proyectado:"));
content.push(table(
  ["Grupo", "2022 (observado)", "2026 (proyectado)"],
  [...GROUPS.map((g) => [g, pct(D.gen[2022].grp[g]), pct(D.gen[2026].grp[g])]),
   ["% mujeres", pct(D.gen[2022].muj), pct(D.gen[2026].muj)],
   ["Total votantes", fmt(D.gen[2022].tot), fmt(D.gen[2026].tot)]],
  [3360, 3000, 3000],
  [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.CENTER]
));
content.push(P("El electorado envejece levemente entre 2022 y 2026 (crece el peso de 61+ y 46-60) y se mantiene mayoritariamente femenino (~53-54%), en línea con la pirámide del DANE.", { italics: true }));

content.push(H2("5.2. Perfil por lista — Cámara 2026"));
content.push(P("Composición del electorado de cada lista (cada fila suma 100% entre las cinco edades; «% muj» es aparte):"));
content.push(partyTable("CAMARA_2026"));

content.push(H2("5.3. Perfil por lista — Cámara 2022"));
content.push(partyTable("CAMARA_2022"));

content.push(H2("5.4. Perfil por lista — Senado 2026"));
content.push(partyTable("SENADO_2026"));

content.push(H2("5.5. Lectura de los patrones"));
[
  "El eje de edad ordena el sistema de partidos: izquierda (Pacto, Verde) joven; partidos tradicionales y de derecha (Conservador, Liberal, Cambio Radical, Centro Democrático) mayores. El voto en blanco es marcadamente joven.",
  "Entre 2022 y 2026 el electorado del Pacto se rejuvenece aún más (baja su peso de mayores), coherente con una movilización juvenil creciente.",
  "El género no estructura el voto en Cundinamarca: las diferencias estimadas entre hombres y mujeres de la misma edad son menores a 2 pp y no robustas. Conviene comunicarlo así y no como un sesgo de sexo.",
].forEach((t) => content.push(bullet(t)));

// 6. Limitaciones
content.push(H1("6. Limitaciones y advertencias"));
[
  [R("Es inferencia ecológica. ", { bold: true }), R("Estima comportamientos de grupo, no de individuos (falacia ecológica, Robinson 1950). Acompañe siempre las cifras de sus cotas; las cifras por celda no son conteos.")],
  [R("El sexo es la dimensión débil. ", { bold: true }), R("El dato no identifica un sesgo de sexo robusto; el reparto por sexo es esencialmente la composición poblacional. No publicar diferencias de sexo fuertes a partir de esta tabla.")],
  [R("2026 es proyección. ", { bold: true }), R("La composición por sexo y edad de 2026 se proyecta del perfil 2022 y del DANE; si la RNEC publica el Edad y Género 2026, el paso de proyección se reemplaza por dato y el modelo mejora.")],
  [R("2022 y 2026 no son el mismo sistema de listas. ", { bold: true }), R("Las coaliciones cambiaron; cada año reporta sus propias listas. Las comparaciones directas de una «misma» lista deben hacerse con cuidado.")],
  [R("Listas menores y circunscripciones especiales. ", { bold: true }), R("Las listas con menos de 0,8% del voto y las circunscripciones especiales (afro, indígena, CITREP) se agrupan en «Otras listas». Nulos y no marcados se excluyen del universo repartido.")],
].forEach((r) => content.push(bullet(r)));

// 7. Ficha técnica
content.push(H1("7. Ficha técnica y reproducibilidad"));
content.push(table(["Concepto", "Valor"], [
  ["Territorio", "Cundinamarca (departamento electoral RNEC 15) · 116 municipios · sin Bogotá D.C."],
  ["Votantes 2022 / 2026 (general)", fmt(D.ctrl.gen2022) + " / " + fmt(D.ctrl.gen2026)],
  ["Válidos+blanco Senado 2022 / 2026", fmt(D.ctrl.sen2022) + " / " + fmt(D.ctrl.sen2026)],
  ["Válidos+blanco Cámara 2022 / 2026", fmt(D.ctrl.cam2022) + " / " + fmt(D.ctrl.cam2026)],
  ["Unidades de estimación", fmt(D.ctrl.mesas2022) + " mesas (2022) · " + fmt(D.ctrl.puestos2026) + " puestos (2026)"],
  ["Celdas demográficas", "10 (2 sexos × 5 grupos de edad)"],
  ["Estimador", "Mínimos cuadrados con símplex + penalización de sexo + raking municipal; cotas Duncan-Davis; IC bootstrap (200)"],
], [3000, 6360]));
content.push(spacer());
content.push(P([
  R("Reproducibilidad: ", { bold: true }),
  R("el pipeline (scripts 01 a 05 + build_doc) y este documento se generan desde "),
  R("tools/cundi-edad-genero/", { italics: true }),
  R(". El README detalla cada paso, los parámetros y las fuentes."),
]));
content.push(P([
  R("Advertencia. ", { bold: true, color: OX }),
  R("Borrador analítico. Las cifras por partido × sexo × edad son estimaciones de comportamiento de grupo con incertidumbre; léanse junto a sus cotas.", { italics: true }),
]));

// ---- documento ----
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Calibri", color: OX },
        paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Calibri", color: INK },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: content,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(OUTDIR, "Cundinamarca_Congreso_Edad_Genero_DESCRIPCION.docx");
  fs.writeFileSync(out, buf);
  console.log("-> " + out + "  (" + Math.round(buf.length / 1024) + " KB)");
});
