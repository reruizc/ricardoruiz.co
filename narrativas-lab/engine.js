/* ════════════════════════════════════════════════════════════════
   NarrativasLab · engine.js
   Motor de reacción determinista + data simulada + helpers de color.
   Extraído verbatim de narrativas-lab.html (single-page) para compartirlo
   entre las subpáginas narrativas (construir/testear/escenarios) y los mapas.
   Todo SIMULADO salvo el ancla de sesgo electoral (personaFromBias) que
   recibe el vector real `b` de la huella territorial.
   Las consts top-level quedan visibles por nombre para los scripts inline
   de cada página (clásico multi-script). También en window.NLEngine.
   ════════════════════════════════════════════════════════════════ */

/* ── Arquetipos psicopolíticos (modelo propio · 5) ── */
const ARQ = {
  proteccion:   { nombre:'Protección',   color:'#1e6fb8' },
  continuidad:  { nombre:'Continuidad',  color:'#2f6b3f' },
  supervivencia:{ nombre:'Supervivencia',color:'#c9682e' },
  castigo:      { nombre:'Castigo',      color:'#a02020' },
  pertenencia:  { nombre:'Pertenencia',  color:'#7a3b8f' }
};

const TEMAS = {
  seguridad:'Seguridad', orden:'Orden', empleo:'Empleo', costo_vida:'Costo de vida',
  movilidad:'Movilidad', educacion:'Educación', corrupcion:'Anticorrupción',
  salud:'Salud', ambiente:'Ambiente', servicios:'Servicios públicos',
  vivienda:'Vivienda', impuestos:'Impuestos', genero:'Género'
};

/* educ = proxy de comprensión · escept = escepticismo · apertura = persuadabilidad
   engage = actividad digital · moodVal = valencia de ánimo (-1..1) · ideo (-1 izq .. +1 der) */
const PERSONAS = [
  { id:'simon', nombre:'Simón Bolívar', edad:47, localidad:'Kennedy', estrato:2,
    ocup:'Conductor de plataforma', arq:'supervivencia', ideo:-0.15, educ:0.45,
    escept:0.6, apertura:0.6, engage:0.5, moodVal:-0.25, emoDom:'Frustración con esperanza',
    emoAfin:['esperanza','indignacion'], temaTop:'el costo de vida',
    temas:{ costo_vida:0.95, empleo:0.9, seguridad:0.7, salud:0.6, movilidad:0.65, impuestos:0.7 },
    socio:'Ingreso variable día a día; sin ahorro; aporta a casa de 4.',
    senal:'Sube fotos del precio de la gasolina, comparte memes sobre peajes y pregunta por subsidios al gremio.' },

  { id:'carmen', nombre:'Carmen Elisa Rojas', edad:62, localidad:'Usaquén', estrato:5,
    ocup:'Empresaria pensionada', arq:'proteccion', ideo:0.45, educ:0.8,
    escept:0.7, apertura:0.35, engage:0.4, moodVal:-0.2, emoDom:'Ansiedad por seguridad',
    emoAfin:['seguridad','firmeza'], temaTop:'la seguridad',
    temas:{ seguridad:0.95, orden:0.9, impuestos:0.75, salud:0.6, corrupcion:0.7 },
    socio:'Patrimonio consolidado; preocupada por seguridad y por impuestos.',
    senal:'Reenvía cadenas de WhatsApp sobre robos en el conjunto y pide más policía y cámaras.' },

  { id:'daniela', nombre:'Daniela Quintero', edad:26, localidad:'Chapinero', estrato:4,
    ocup:'Diseñadora freelance', arq:'castigo', ideo:-0.6, educ:0.85,
    escept:0.55, apertura:0.75, engage:0.9, moodVal:-0.1, emoDom:'Indignación idealista',
    emoAfin:['indignacion','esperanza'], temaTop:'la corrupción y el ambiente',
    temas:{ ambiente:0.85, genero:0.8, corrupcion:0.9, movilidad:0.7, empleo:0.6 },
    socio:'Ingreso por proyectos; sin estabilidad pero con capital cultural alto.',
    senal:'Muy activa en X e Instagram: comparte hilos de clima y denuncias de corrupción, hace stories de opinión.' },

  { id:'jose', nombre:'José Gregorio Pájaro', edad:54, localidad:'Bosa', estrato:2,
    ocup:'Tendero', arq:'continuidad', ideo:0.05, educ:0.4,
    escept:0.65, apertura:0.45, engage:0.35, moodVal:-0.15, emoDom:'Cansancio pragmático',
    emoAfin:['firmeza','esperanza'], temaTop:'el negocio y la seguridad',
    temas:{ seguridad:0.85, empleo:0.7, impuestos:0.8, costo_vida:0.8, movilidad:0.5 },
    socio:'Negocio propio chico; márgenes apretados; teme la extorsión.',
    senal:'En grupos de comerciantes del barrio; se queja de la extorsión, los impuestos y la inseguridad nocturna.' },

  { id:'luz', nombre:'Luz Marina Cifuentes', edad:38, localidad:'Ciudad Bolívar', estrato:1,
    ocup:'Líder comunal · madre cabeza de hogar', arq:'pertenencia', ideo:-0.5, educ:0.5,
    escept:0.6, apertura:0.65, engage:0.7, moodVal:-0.05, emoDom:'Resiliencia desconfiada',
    emoAfin:['esperanza','pertenencia','indignacion'], temaTop:'los servicios y la educación',
    temas:{ servicios:0.9, educacion:0.85, seguridad:0.8, vivienda:0.8, salud:0.7 },
    socio:'Ingreso informal; vive del rebusque y el trabajo comunitario.',
    senal:'Organiza por Facebook y WhatsApp comunal; pide agua, colegios y rutas de transporte para el barrio.' },

  { id:'andres', nombre:'Andrés Felipe Moreno', edad:33, localidad:'Suba', estrato:3,
    ocup:'Ingeniero asalariado', arq:'proteccion', ideo:0.25, educ:0.8,
    escept:0.6, apertura:0.55, engage:0.6, moodVal:-0.1, emoDom:'Escepticismo aspiracional',
    emoAfin:['firmeza','esperanza'], temaTop:'la movilidad',
    temas:{ movilidad:0.9, seguridad:0.8, empleo:0.7, impuestos:0.75 },
    socio:'Clase media; crédito de vivienda; valora resultados medibles.',
    senal:'Comparte quejas de TransMilenio y trancones; mira propuestas con lupa y pide datos.' }
];

/* ── Variantes-ejemplo de mensaje ── */
const EX_A = { texto:'Bogotá necesita orden. Mano firme contra el crimen, cámaras en cada esquina y cero tolerancia con la extorsión.',
  ganz:'Yo crecí cuidando lo mío. / Nosotros merecemos vivir sin miedo. / Ahora recuperamos la calle.',
  frame:'Valor central: seguridad. Metáfora: la casa que se protege. Palabras propias: orden, autoridad, respeto.',
  tono:'firmeza', emocion:'seguridad', ideo:0.4, complejidad:0.30, concrecion:0.6,
  temas:{ seguridad:1.0, orden:0.9 } };
const EX_B = { texto:'Bogotá se cuida cuidando a su gente: empleo digno, transporte que funcione y barrios con oportunidades para los jóvenes.',
  ganz:'Yo también la he peleado duro. / Nosotros somos una ciudad que no se rinde. / Ahora construimos oportunidades.',
  frame:'Valor central: oportunidad. Metáfora: la ciudad que cuida. Palabras propias: dignidad, futuro, juntos.',
  tono:'esperanza', emocion:'esperanza', ideo:-0.2, complejidad:0.45, concrecion:0.45,
  temas:{ empleo:0.9, costo_vida:0.7, movilidad:0.6, seguridad:0.5, educacion:0.5 } };

/* ── Escenarios: moodShift global + multiplicadores de saliencia + penalización de credibilidad ── */
const SCENARIOS = [
  { id:'base', nombre:'Línea base (hoy)', moodShift:0, credPenalty:0, sal:{} },
  { id:'inseg', nombre:'Ola de inseguridad', moodShift:-0.15, credPenalty:0, sal:{ seguridad:1.4, orden:1.3 } },
  { id:'corrup', nombre:'Escándalo de corrupción', moodShift:-0.2, credPenalty:0.15, sal:{ corrupcion:1.6 } },
  { id:'economia', nombre:'Mejora económica', moodShift:0.2, credPenalty:0, sal:{ empleo:1.3, costo_vida:1.3 } }
];

/* ── Escucha social (maqueta) ── */
const SOCIAL_TOPICS = [
  { t:'Seguridad / hurtos', vol:92, sent:-0.55 },
  { t:'Costo de vida', vol:81, sent:-0.40 },
  { t:'Movilidad / transporte', vol:74, sent:-0.48 },
  { t:'Corrupción', vol:63, sent:-0.62 },
  { t:'Empleo / oportunidades', vol:57, sent:-0.18 },
  { t:'Servicios públicos', vol:44, sent:-0.30 },
  { t:'Ambiente', vol:31, sent:0.05 }
];
const SOCIAL_EMO = [
  { l:'Indignación', v:34, c:'#a02020' },
  { l:'Miedo', v:24, c:'#1e6fb8' },
  { l:'Esperanza', v:19, c:'#2f6b3f' },
  { l:'Cansancio', v:14, c:'#c9682e' },
  { l:'Orgullo', v:6, c:'#7a3b8f' },
  { l:'Otros', v:3, c:'#888' }
];
const SOCIAL_LOC = [
  { loc:'Norte', sent:-0.38, tema:'Seguridad' },
  { loc:'Centro', sent:-0.29, tema:'Corrupción' },
  { loc:'Sur', sent:-0.49, tema:'Servicios públicos' },
  { loc:'Occidente', sent:-0.46, tema:'Movilidad' },
  { loc:'Oriente', sent:-0.42, tema:'Costo de vida' }
];

/* ════════════════════════════════════════════════════════
   MOTOR DE REACCIÓN (heurística determinista)
   ════════════════════════════════════════════════════════ */
const clamp = (x,a,b)=>Math.max(a,Math.min(b,x));

function temaOverlap(p, msg, scen){
  let num=0, den=0;
  for (const t in msg.temas){
    const sal = (scen && scen.sal && scen.sal[t]) ? scen.sal[t] : 1;
    const mi = msg.temas[t] * sal;
    den += mi; num += mi * (p.temas[t]||0);
  }
  return den ? clamp(num/den,0,1) : 0;
}
const ideoDist = (p,msg)=>Math.abs(p.ideo - msg.ideo)/2;       // 0..1
const ideoAlign = (p,msg)=>1 - ideoDist(p,msg);                 // 0..1

function simular(p, msg, scen){
  scen = scen || SCENARIOS[0];
  const align = ideoAlign(p,msg);
  const overlap = temaOverlap(p,msg,scen);
  const mood = clamp(p.moodVal + (scen.moodShift||0), -1, 1);

  let comp = 100*(1 - msg.complejidad*(1.15 - 0.45*p.educ)) + msg.concrecion*8 + (mood>0?3:-3);
  comp = clamp(comp, 6, 99);

  let cred = 100*(0.45*align + 0.35*msg.concrecion + 0.20*(1-p.escept));
  cred = clamp(cred - (scen.credPenalty||0)*100 - (1-align)*p.escept*30, 5, 98);

  let reso = 100*(0.55*overlap + 0.25*align + 0.20*((mood+1)/2));
  if (msg.emocion && p.emoAfin.includes(msg.emocion)) reso += 8;
  if (scen.sal){ let sb = 0; for (const tt in msg.temas){ const s = (scen.sal[tt]||1) - 1; if (s > 0) sb += s * msg.temas[tt] * (p.temas[tt]||0); } reso += sb * 24; }
  reso = clamp(reso, 4, 99);

  let pers = 100*(0.40*(reso/100) + 0.35*(cred/100) + 0.25*p.apertura) * (0.62 + 0.38*align);
  pers = clamp(pers, 3, 97);

  let risk = 100*(0.55*ideoDist(p,msg) + 0.25*p.escept + 0.20*p.engage);
  if (msg.tono==='indignacion' && align<0.45) risk += 12;
  if (mood<-0.3 && align<0.5) risk += 8;
  risk = clamp(risk - align*15, 2, 96);

  return { comp:Math.round(comp), cred:Math.round(cred), reso:Math.round(reso),
           pers:Math.round(pers), risk:Math.round(risk) };
}

function _reaccion(p, msg, s){
  if (s.risk >= 62) return `Lo siente como un mensaje que no es para ${p.nombre.split(' ')[0]}: choca con su mirada y activa rechazo. Riesgo de que lo comparta para criticarlo.`;
  if (s.pers >= 66) return `Conecta fuerte: lo lee como una respuesta directa a lo que le importa: ${p.temaTop}. Alta probabilidad de que lo amplifique.`;
  if (s.pers >= 46) return `Lo escucha con interés, pero pide pruebas concretas sobre ${p.temaTop} antes de creerlo del todo.`;
  return `Indiferencia: el mensaje no toca su prioridad (${p.temaTop}). Pasa de largo sin reaccionar.`;
}

/* ── Persona sintética anclada en sesgo electoral REAL (vector huella `b`) ──
   b = { ic,ae,pv,sf,cl,rb } (multiplicador de afinidad, 1.0 = neutro).
   ic=Cepeda(izq) ae=De la Espriella(der) pv=Paloma(der) sf=Fajardo(centro)
   cl=Claudia(centro) rb=Roy(centro-izq). Solo el ancla (ideo/temas) es real;
   la reacción la sigue calculando `simular`, que es maqueta. */
function personaFromBias(b, opts){
  opts = opts || {};
  const g = k => (b && typeof b[k]==='number' && isFinite(b[k])) ? b[k] : 1;
  const right = (g('ae') + g('pv')) / 2;
  const left  = (g('ic') + g('rb')) / 2;
  return personaFromIdeo(clamp((right - left) * 0.6, -0.85, 0.85), opts);
}
// Persona a partir de un ideo ya derivado (p.ej. del share Cepeda/Abelardo 2V por barrio).
function personaFromIdeo(ideo, opts){
  opts = opts || {};
  ideo = clamp(ideo, -0.85, 0.85);
  const der   = (ideo + 0.85) / 1.7;                 // 0 izq .. 1 der
  const educ  = clamp(0.5 + 0.18*(opts.educBias||0) + 0.15*der, 0.2, 0.95);
  const noise = opts.noise || 0;
  const temas = {
    seguridad: 0.6 + 0.3*der, orden: 0.3 + 0.5*der, impuestos: 0.3 + 0.45*der,
    movilidad: 0.55, costo_vida: 0.9 - 0.5*der,
    empleo: 0.85 - 0.4*der, servicios: 0.85 - 0.55*der, educacion: 0.7 - 0.3*der
  };
  const temaTop = Object.keys(temas).reduce((a,k)=> temas[k] > temas[a] ? k : a);
  const emoAfin = ideo > 0.2 ? ['seguridad','firmeza']
                : ideo < -0.2 ? ['esperanza','indignacion','pertenencia']
                : ['esperanza','firmeza'];
  return { ideo, educ, temas, temaTop, emoAfin,
    moodVal: -0.12 + noise, escept: 0.5 + 0.12*educ,
    apertura: clamp(0.6 - 0.18*Math.abs(ideo) + noise, 0.3, 0.9), engage: 0.45 + 0.18*educ };
}

/* ── Helpers de presentación / color ── */
const DIMS = [
  { k:'comp', l:'Comprensión', inv:false },
  { k:'cred', l:'Credibilidad', inv:false },
  { k:'reso', l:'Resonancia', inv:false },
  { k:'pers', l:'Persuasión', inv:false },
  { k:'risk', l:'Riesgo rechazo', inv:true }
];
const scoreColor = (v, invert)=>{ const x = invert ? 100-v : v; return x>=60?'var(--good)':x>=40?'var(--mid)':'var(--bad)'; };
const initials = n => n.split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();

function _hx(h){ h=h.replace('#',''); return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]; }
function _mix(a, b, t){ const A=_hx(a), B=_hx(b); return `rgb(${Math.round(A[0]+(B[0]-A[0])*t)},${Math.round(A[1]+(B[1]-A[1])*t)},${Math.round(A[2]+(B[2]-A[2])*t)})`; }
const C_BAD='#cf5b46', C_MID='#d2a236', C_GOOD='#3f9d63', C_NEU='#b9b3a6';
function persColor(v){ const t=clamp(v/100,0,1); return t<0.5 ? _mix(C_BAD,C_MID,t*2) : _mix(C_MID,C_GOOD,(t-0.5)*2); }
function swingColor(d){ const t=clamp(d/16,-1,1); return t>=0 ? _mix(C_NEU,C_GOOD,t) : _mix(C_NEU,C_BAD,-t); }

window.NLEngine = {
  ARQ, TEMAS, PERSONAS, EX_A, EX_B, SCENARIOS, SOCIAL_TOPICS, SOCIAL_EMO, SOCIAL_LOC,
  clamp, temaOverlap, ideoDist, ideoAlign, simular, _reaccion, personaFromBias, personaFromIdeo,
  DIMS, scoreColor, initials, persColor, swingColor, C_BAD, C_MID, C_GOOD, C_NEU
};
