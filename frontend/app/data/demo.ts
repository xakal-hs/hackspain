export const perspectives = [
  {
    id: "embat",
    name: "Embat",
    person: "Equipo Embat",
    initials: "EM",
    description: "Supervisa el ecosistema y conecta empresas con financiación.",
  },
  {
    id: "empresa",
    name: "Empresa",
    person: "Distribuciones Ibérica",
    initials: "DI",
    description: "Entiende tu salud financiera y compara tus ofertas.",
  },
  {
    id: "banco",
    name: "Banco",
    person: "Banco Meridiano",
    initials: "BM",
    description: "Encuentra oportunidades y decide con señales de tesorería.",
  },
] as const;
export type Perspective = (typeof perspectives)[number]["id"];
export const demoCompanies = [
  {
    id: "solis",
    name: "Panadería Solís",
    sector: "Alimentación",
    score: 91,
    delta: 1,
    rate: "4,6",
    amount: 30000,
    action: "Prestar",
    why: "El dinero en la cuenta cubre los próximos pagos. Los clientes pagan a tiempo.",
    signal: "Estabilidad sostenida",
    history: [88, 89, 90, 90, 90, 91],
  },
  {
    id: "vidal",
    name: "Talleres Vidal",
    sector: "Metalurgia industrial",
    score: 65,
    delta: 20,
    rate: "6,1",
    amount: 20000,
    action: "Vigilar",
    why: "Cobra antes y recupera dinero en la cuenta. Conviene confirmar que la mejora se mantiene.",
    signal: "Recuperación temprana",
    history: [48, 43, 45, 51, 59, 65],
  },
  {
    id: "nortex",
    name: "Nortex Logística",
    sector: "Transporte y logística",
    score: 74,
    delta: -2,
    rate: "5,9",
    amount: 25000,
    action: "Prestar",
    why: "Un pago extraordinario reduce la caja, pero los cobros habituales se mantienen.",
    signal: "Bache temporal",
    history: [75, 76, 76, 72, 73, 74],
  },
  {
    id: "iberica",
    name: "Distribuciones Ibérica",
    sector: "Distribución alimentaria",
    score: 68,
    delta: -14,
    rate: "7,4",
    amount: 25000,
    action: "Vigilar",
    why: "El coste de financiación sube y se retrasa el pago a 3 proveedores. Los cobros de clientes siguen normales.",
    signal: "Deterioro persistente",
    history: [85, 84, 82, 78, 73, 68],
  },
  {
    id: "sureste",
    name: "Recolectora Sureste",
    sector: "Agroindustria",
    score: 39,
    delta: -13,
    rate: "9,8",
    amount: 15000,
    action: "No prestar",
    why: "Los pagos superan los cobros durante tres meses. El dinero disponible ya no cubre el siguiente mes.",
    signal: "Caída estructural",
    history: [60, 56, 52, 48, 43, 39],
  },
];
export interface DemoOffer {
  id: string;
  bank: string;
  amount: number;
  rate: string;
  months: number;
  note: string;
  accepted: boolean;
}
export const initialOffers: DemoOffer[] = [
  {
    id: "meridiano",
    bank: "Banco Meridiano",
    amount: 20000,
    rate: "7,1",
    months: 12,
    note: "El tipo subió 0,4 puntos este mes por el cambio de score.",
    accepted: false,
  },
  {
    id: "atlas",
    bank: "Fondo Atlas",
    amount: 25000,
    rate: "7,6",
    months: 9,
    note: "Un plazo corto para cubrir tus necesidades de liquidez.",
    accepted: false,
  },
  {
    id: "sur",
    bank: "Prestamista Sur",
    amount: 15000,
    rate: "6,9",
    months: 18,
    note: "El menor tipo, con un plazo de devolución más largo.",
    accepted: false,
  },
];
export const euros = (value: number) =>
  new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
