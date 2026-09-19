/* Demo portfolio for the X-Ray walkthrough.
 *
 * Figures are illustrative but internally consistent: every cash line is the
 * running sum of its own collections and payments, so the panels never
 * contradict each other on stage.
 */

export const months = [
  'oct 24',
  'nov 24',
  'dic 24',
  'ene 25',
  'feb 25',
  'mar 25',
  'abr 25',
  'may 25',
  'jun 25',
  'jul 25',
  'ago 25',
  'sep 25',
  'oct 25',
  'nov 25',
  'dic 25',
  'ene 26',
  'feb 26',
  'mar 26',
  'abr 26',
  'may 26',
  'jun 26',
  'jul 26',
  'ago 26',
  'sep 26',
] as const

export const monthNames = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
] as const

export const currentMonth = 'septiembre 2026'

export type Decision = 'prestar' | 'vigilar' | 'no-prestar'
export type Band = 'sano' | 'vigilar' | 'riesgo'
export type Shape = 'estable' | 'mejora' | 'bache' | 'deterioro' | 'caida'

export const decisionLabel: Record<Decision, string> = {
  prestar: 'Prestar',
  vigilar: 'Vigilar',
  'no-prestar': 'No prestar',
}

export const shapeLabel: Record<Shape, string> = {
  estable: 'Estabilidad sostenida',
  mejora: 'Recuperación confirmada',
  bache: 'Bache temporal',
  deterioro: 'Deterioro persistente',
  caida: 'Caída estructural',
}

/** A signal's weight is its share of the score move, so the bar length in the
 *  interface is the criticality itself and not a decoration. */
export interface Signal {
  label: string
  detail: string
  weight: number
  direction: 'up' | 'down' | 'flat'
}

export interface MonthFlow {
  month: string
  in: number
  out: number
  cash: number
}

export interface Company {
  id: string
  name: string
  sector: string
  group: string
  score: number
  band: Band
  decision: Decision
  shape: Shape
  delta3: number
  delta12: number
  history: number[]
  forecast: number[]
  /** Month index where the trajectory signal fired. */
  detectedAt: number | null
  /** Month index where the level alone crossed into the new band. */
  levelAt: number | null
  headline: string
  why: string
  action: string
  runway: { now: number; prev: number }
  dso: { now: number; prev: number }
  dpo: { now: number; prev: number }
  rate: string
  amount: number
  term: number
  erp: boolean
  monthsConnected: number
  coverage: number
  flows?: MonthFlow[]
  signals?: Signal[]
}

const flowMonths = months.slice(16) as unknown as string[]

function buildFlows(start: number, ins: number[], outs: number[]): MonthFlow[] {
  let cash = start
  return ins.map((value, index) => {
    cash = cash + value - outs[index]!
    return {
      month: flowMonths[index]!,
      in: value * 1000,
      out: outs[index]! * 1000,
      cash: cash * 1000,
    }
  })
}

export const companies: Company[] = [
  {
    id: 'solis',
    name: 'Panadería Solís',
    sector: 'Alimentación',
    group: 'Grupo Solís',
    score: 91,
    band: 'sano',
    decision: 'prestar',
    shape: 'estable',
    delta3: 1,
    delta12: 2,
    history: [
      86, 87, 86, 88, 87, 88, 89, 88, 87, 89, 88, 89, 90, 89, 88, 90, 89, 90,
      88, 89, 90, 90, 90, 91,
    ],
    forecast: [91, 91, 92],
    detectedAt: null,
    levelAt: null,
    headline: 'Dos años sin un mes en negativo',
    why: 'El dinero en la cuenta cubre más de siete meses de pagos y los clientes pagan a los 31 días. Nada ha cambiado en dos años.',
    action: 'Presta el importe completo. Revisa en seis meses.',
    runway: { now: 7.6, prev: 7.1 },
    dso: { now: 31, prev: 32 },
    dpo: { now: 35, prev: 34 },
    rate: '4,6',
    amount: 30000,
    term: 12,
    erp: true,
    monthsConnected: 24,
    coverage: 0.98,
    flows: buildFlows(
      240,
      [96, 101, 99, 104, 102, 108, 106, 111],
      [88, 92, 90, 95, 93, 97, 96, 99],
    ),
    signals: [
      {
        label: 'El dinero de la cuenta sigue creciendo',
        detail: '317 k€, siete meses de pagos cubiertos',
        weight: 0.44,
        direction: 'up',
      },
      {
        label: 'Los clientes pagan igual de rápido',
        detail: '31 días, un día menos que el año pasado',
        weight: 0.21,
        direction: 'flat',
      },
      {
        label: 'Entra más de lo que sale todos los meses',
        detail: '24 meses seguidos en positivo',
        weight: 0.26,
        direction: 'up',
      },
      {
        label: 'Contabilidad conectada y conciliada',
        detail: '98 % de los movimientos con factura',
        weight: 0.09,
        direction: 'flat',
      },
    ],
  },
  {
    id: 'vidal',
    name: 'Talleres Vidal',
    sector: 'Metalurgia industrial',
    group: 'Vidal Hermanos',
    score: 65,
    band: 'vigilar',
    decision: 'vigilar',
    shape: 'mejora',
    delta3: 20,
    delta12: 22,
    history: [
      72, 70, 67, 64, 61, 58, 55, 52, 50, 48, 47, 45, 44, 43, 42, 44, 46, 48,
      48, 43, 45, 51, 59, 65,
    ],
    forecast: [69, 72, 74],
    detectedAt: 21,
    levelAt: 23,
    headline: 'Cobra antes y vuelve a tener caja',
    why: 'Tarda 27 días menos en cobrar que en marzo y ha recuperado 217 k€ en la cuenta. La mejora lleva tres meses seguidos.',
    action: 'Vigila un mes más. Si aguanta en septiembre, presta.',
    runway: { now: 4.3, prev: 1.1 },
    dso: { now: 41, prev: 68 },
    dpo: { now: 44, prev: 71 },
    rate: '6,1',
    amount: 20000,
    term: 12,
    erp: true,
    monthsConnected: 19,
    coverage: 0.91,
    flows: buildFlows(
      96,
      [148, 152, 161, 174, 183, 197, 206, 218],
      [171, 168, 165, 162, 159, 161, 164, 168],
    ),
    signals: [
      {
        label: 'Tarda mucho menos en cobrar',
        detail: 'De 68 a 41 días desde marzo',
        weight: 0.38,
        direction: 'up',
      },
      {
        label: 'El dinero de la cuenta se ha multiplicado por cuatro',
        detail: 'De 53 k€ en abril a 217 k€',
        weight: 0.31,
        direction: 'up',
      },
      {
        label: 'Ha dejado de estirar los pagos a proveedores',
        detail: 'De 71 a 44 días',
        weight: 0.19,
        direction: 'up',
      },
      {
        label: 'Sigue por debajo de su nivel de 2024',
        detail: '65 frente a 72 hace dos años',
        weight: 0.12,
        direction: 'down',
      },
    ],
  },
  {
    id: 'nortex',
    name: 'Nortex Logística',
    sector: 'Transporte y logística',
    group: 'Nortex Group',
    score: 74,
    band: 'sano',
    decision: 'prestar',
    shape: 'bache',
    delta3: -2,
    delta12: -1,
    history: [
      70, 71, 72, 73, 74, 73, 75, 74, 76, 75, 74, 76, 75, 76, 77, 76, 75, 76,
      75, 76, 76, 72, 73, 74,
    ],
    forecast: [75, 76, 76],
    detectedAt: null,
    levelAt: null,
    headline: 'Un pago único, no un problema',
    why: 'En julio salieron 398 k€ de una liquidación de impuestos. Los cobros no se movieron y la caja ya se está reponiendo.',
    action: 'Presta. El bache de julio no cambia la decisión.',
    runway: { now: 4.8, prev: 5.1 },
    dso: { now: 39, prev: 38 },
    dpo: { now: 46, prev: 45 },
    rate: '5,9',
    amount: 25000,
    term: 12,
    erp: true,
    monthsConnected: 24,
    coverage: 0.94,
    flows: buildFlows(
      310,
      [214, 221, 209, 218, 226, 231, 224, 229],
      [198, 205, 212, 201, 209, 398, 206, 213],
    ),
    signals: [
      {
        label: 'Una salida extraordinaria de un solo mes',
        detail: '398 k€ en julio, el doble de lo habitual',
        weight: 0.41,
        direction: 'down',
      },
      {
        label: 'Los cobros no se han movido',
        detail: '39 días, igual que los doce meses anteriores',
        weight: 0.29,
        direction: 'flat',
      },
      {
        label: 'La caja ya se está reponiendo',
        detail: 'De 206 a 240 k€ en dos meses',
        weight: 0.22,
        direction: 'up',
      },
      {
        label: 'Ningún pago a proveedores retrasado',
        detail: '46 días, sin cambios',
        weight: 0.08,
        direction: 'flat',
      },
    ],
  },
  {
    id: 'iberica',
    name: 'Distribuciones Ibérica',
    sector: 'Distribución alimentaria',
    group: 'Ibérica Retail',
    score: 68,
    band: 'vigilar',
    decision: 'vigilar',
    shape: 'deterioro',
    delta3: -14,
    delta12: -17,
    history: [
      83, 84, 86, 85, 84, 86, 87, 86, 85, 86, 85, 84, 86, 85, 87, 86, 85, 85,
      85, 82, 80, 78, 73, 68,
    ],
    forecast: [64, 61, 59],
    detectedAt: 19,
    levelAt: 23,
    headline: 'La caja se agota mientras sube el coste de la deuda',
    why: 'El dinero disponible cubre 3,9 meses de pagos, frente a 9,4 en marzo. Paga a proveedores 23 días más tarde y el coste de su deuda ha subido 1,8 puntos. Los clientes siguen pagando igual.',
    action: 'No amplíes. Renueva solo con garantía y revisa cada mes.',
    runway: { now: 3.9, prev: 9.4 },
    dso: { now: 45, prev: 44 },
    dpo: { now: 61, prev: 38 },
    rate: '7,4',
    amount: 25000,
    term: 12,
    erp: true,
    monthsConnected: 24,
    coverage: 0.96,
    flows: buildFlows(
      450,
      [412, 398, 405, 388, 371, 349, 336, 318],
      [376, 381, 392, 401, 408, 402, 397, 389],
    ),
    signals: [
      {
        label: 'El dinero de la cuenta cubre menos de la mitad de tiempo',
        detail: 'De 9,4 a 3,9 meses de pagos cubiertos',
        weight: 0.43,
        direction: 'down',
      },
      {
        label: 'Su deuda le cuesta más cada mes',
        detail: '+1,8 puntos de interés desde marzo',
        weight: 0.24,
        direction: 'down',
      },
      {
        label: 'Paga a los proveedores mucho más tarde',
        detail: 'De 38 a 61 días, tres proveedores afectados',
        weight: 0.19,
        direction: 'down',
      },
      {
        label: 'Los clientes pagan como siempre',
        detail: '45 días, un día más que en marzo',
        weight: 0.08,
        direction: 'flat',
      },
      {
        label: 'Contabilidad conectada, sin huecos',
        detail: '96 % de los movimientos con factura',
        weight: 0.06,
        direction: 'flat',
      },
    ],
  },
  {
    id: 'sureste',
    name: 'Recolectora Sureste',
    sector: 'Agroindustria',
    group: 'Sureste Agro',
    score: 39,
    band: 'riesgo',
    decision: 'no-prestar',
    shape: 'caida',
    delta3: -13,
    delta12: -23,
    history: [
      78, 77, 76, 75, 74, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 64, 62, 61,
      60, 56, 52, 48, 43, 39,
    ],
    forecast: [35, 33, 31],
    detectedAt: 18,
    levelAt: 21,
    headline: 'La caja ya no cubre un mes de pagos',
    why: 'Los pagos superan los cobros desde febrero y quedan 6 k€ en la cuenta. Ha dejado de pagar a proveedores para aguantar: 78 días frente a 41 en febrero.',
    action: 'No prestar. Revisa la exposición que ya tienes con ella.',
    runway: { now: 0.1, prev: 5.2 },
    dso: { now: 63, prev: 52 },
    dpo: { now: 78, prev: 41 },
    rate: '9,8',
    amount: 15000,
    term: 12,
    erp: true,
    monthsConnected: 22,
    coverage: 0.88,
    flows: buildFlows(
      520,
      [268, 254, 241, 233, 219, 205, 198, 186],
      [281, 289, 296, 302, 311, 308, 301, 230],
    ),
    signals: [
      {
        label: 'Ya no queda dinero en la cuenta',
        detail: '6 k€ frente a 520 k€ en enero',
        weight: 0.48,
        direction: 'down',
      },
      {
        label: 'Sale más de lo que entra desde febrero',
        detail: 'Ocho meses seguidos en negativo',
        weight: 0.26,
        direction: 'down',
      },
      {
        label: 'Ha dejado de pagar a proveedores',
        detail: 'De 41 a 78 días, los pagos caen un 24 %',
        weight: 0.17,
        direction: 'down',
      },
      {
        label: 'Sus clientes también tardan más',
        detail: 'De 52 a 63 días',
        weight: 0.09,
        direction: 'down',
      },
    ],
  },
  {
    id: 'atlas-frio',
    name: 'Atlas Frío',
    sector: 'Cadena de frío',
    group: 'Atlas Industrial',
    score: 83,
    band: 'sano',
    decision: 'prestar',
    shape: 'mejora',
    delta3: 6,
    delta12: 9,
    history: [
      71, 72, 70, 73, 74, 72, 75, 74, 76, 75, 77, 76, 78, 77, 79, 78, 77, 79,
      77, 78, 80, 81, 82, 83,
    ],
    forecast: [84, 85, 85],
    detectedAt: 20,
    levelAt: 22,
    headline: 'Crece sin estirar los pagos',
    why: 'Factura un 18 % más que hace un año y mantiene los plazos de pago. La caja crece al mismo ritmo que la facturación.',
    action: 'Presta y ofrécele ampliar el límite.',
    runway: { now: 6.2, prev: 5.4 },
    dso: { now: 36, prev: 38 },
    dpo: { now: 42, prev: 42 },
    rate: '4,9',
    amount: 40000,
    term: 18,
    erp: true,
    monthsConnected: 24,
    coverage: 0.95,
  },
  {
    id: 'altea',
    name: 'Cerámicas Altea',
    sector: 'Materiales de construcción',
    group: 'Altea Cerámica',
    score: 78,
    band: 'sano',
    decision: 'prestar',
    shape: 'estable',
    delta3: 0,
    delta12: 1,
    history: [
      76, 77, 76, 78, 77, 79, 78, 77, 79, 78, 77, 78, 79, 78, 77, 79, 78, 79,
      78, 78, 79, 78, 78, 78,
    ],
    forecast: [78, 78, 79],
    detectedAt: null,
    levelAt: null,
    headline: 'Sin movimiento en dos años',
    why: 'Los cobros, los pagos y la caja se repiten mes a mes con variaciones de menos de dos puntos.',
    action: 'Presta. Es el perfil más predecible de la cartera.',
    runway: { now: 5.5, prev: 5.6 },
    dso: { now: 43, prev: 43 },
    dpo: { now: 48, prev: 47 },
    rate: '5,2',
    amount: 28000,
    term: 12,
    erp: true,
    monthsConnected: 24,
    coverage: 0.93,
  },
  {
    id: 'ledesma',
    name: 'Grupo Ledesma',
    sector: 'Servicios industriales',
    group: 'Ledesma Servicios',
    score: 54,
    band: 'vigilar',
    decision: 'vigilar',
    shape: 'deterioro',
    delta3: -7,
    delta12: -11,
    history: [
      67, 66, 68, 65, 66, 64, 65, 63, 64, 62, 63, 61, 62, 60, 61, 59, 60, 58,
      59, 61, 58, 56, 55, 54,
    ],
    forecast: [53, 52, 51],
    detectedAt: 21,
    levelAt: 23,
    headline: 'Solo vemos los bancos, no las facturas',
    why: 'La caja baja despacio desde 2024. Sin contabilidad conectada no podemos decir si es por cobros, por margen o por deuda nueva.',
    action: 'Pide la conexión del ERP antes de decidir.',
    runway: { now: 2.4, prev: 3.6 },
    dso: { now: 0, prev: 0 },
    dpo: { now: 0, prev: 0 },
    rate: '8,2',
    amount: 18000,
    term: 9,
    erp: false,
    monthsConnected: 11,
    coverage: 0.34,
  },
]

export const companyById = (id: string) =>
  companies.find((company) => company.id === id)

export const leadCompany = companies.find((c) => c.id === 'iberica')!

/** Two companies that drop the same four points in a month. The product calls
 *  one a bump and the other a structural fall, and says why. */
export const dipVsFall = {
  offsets: ['-2', '-1', 'caída', '+1', '+2'],
  bump: {
    id: 'nortex',
    name: 'Nortex Logística',
    month: 'julio 2026',
    relative: [4, 4, 0, 1, 2],
    verdict: 'Bache temporal',
    cause: 'Una liquidación de impuestos de 398 k€ en un solo mes.',
    evidence: 'Los cobros no se movieron y la caja se repuso en dos meses.',
    decision: 'prestar' as Decision,
    outcome: 'La decisión no cambia.',
  },
  fall: {
    id: 'sureste',
    name: 'Recolectora Sureste',
    month: 'mayo 2026',
    relative: [5, 4, 0, -4, -8],
    verdict: 'Caída estructural',
    cause: 'Los pagos superan los cobros el tercer mes seguido.',
    evidence: 'La caja pasa de cubrir cinco meses a no cubrir uno.',
    decision: 'no-prestar' as Decision,
    outcome: 'Retirar la línea.',
  },
}

export interface Perspective {
  id: 'embat' | 'empresa'
  name: string
  person: string
  initials: string
  job: string
  reads: string
}

export const perspectives: Perspective[] = [
  {
    id: 'empresa',
    name: 'Empresa',
    person: 'Distribuciones Ibérica',
    initials: 'DI',
    job: 'Entender por qué me suben el tipo y qué puedo cambiar',
    reads: 'Mira primero qué señal se movió y qué la devuelve a su sitio.',
  },
  {
    id: 'embat',
    name: 'Embat',
    person: 'Equipo Embat',
    initials: 'EM',
    job: 'Avisar a tiempo a las dos partes',
    reads: 'Mira primero cuántos meses de ventaja damos sobre el nivel.',
  },
]

export type PerspectiveId = Perspective['id']

export const perspectiveById = (id: string) =>
  perspectives.find((p) => p.id === id)

export interface Offer {
  id: string
  bank: string
  amount: number
  rate: string
  months: number
  note: string
  accepted: boolean
}

export const initialOffers: Offer[] = [
  {
    id: 'norte',
    bank: 'Financiador Norte',
    amount: 20000,
    rate: '7,1',
    months: 12,
    note: 'El tipo subió 0,4 puntos este mes al caer tu score a 68.',
    accepted: false,
  },
  {
    id: 'atlas',
    bank: 'Fondo Atlas',
    amount: 25000,
    rate: '7,6',
    months: 9,
    note: 'Plazo corto, pensado para cubrir el hueco de caja de este trimestre.',
    accepted: false,
  },
  {
    id: 'sur',
    bank: 'Prestamista Sur',
    amount: 15000,
    rate: '6,9',
    months: 18,
    note: 'El tipo más bajo de los tres, a cambio de devolverlo en 18 meses.',
    accepted: false,
  },
]

/** What the product is worth on this portfolio, from the CFO row. */
export const value = [
  {
    figure: '4 meses',
    label: 'de ventaja media sobre el nivel',
    note: 'En las cinco empresas que cambiaron de tramo, la trayectoria avisó antes que el score.',
  },
  {
    figure: '1 de 4',
    label: 'caídas eran solo un bache',
    note: 'Cuatro empresas perdieron puntos y una solo había pagado impuestos. Distinguirlas evita retirar una línea que no había que retirar.',
  },
  {
    figure: '58 k€',
    label: 'de exposición avisada a tiempo',
    note: 'Lo que un prestamista tenía colocado en las tres empresas que se deterioraron de verdad.',
  },
]

export const euros = (value: number) =>
  new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)

/** Compact form for chart axes and dense cells: 318 k€, 1,2 M€. */
export const compactEuros = (value: number) => {
  const abs = Math.abs(value)
  if (abs >= 1_000_000)
    return `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 }).format(value / 1_000_000)} M€`
  if (abs >= 1000)
    return `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 }).format(value / 1000)} k€`
  return `${value} €`
}

export const signed = (value: number) =>
  `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value)}`

export const leadMonths = (company: Company) =>
  company.detectedAt !== null && company.levelAt !== null
    ? company.levelAt - company.detectedAt
    : 0
