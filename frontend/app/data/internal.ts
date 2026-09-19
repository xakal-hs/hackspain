/* Lo que Embat mira de sí mismo, no de una empresa de la cartera.
 *
 * Las tres vistas internas —monitor, revenue y métricas del modelo— leen de
 * aquí. Van aparte de `demo.ts` porque el sujeto es otro: allí cada fila es una
 * empresa a la que se le presta; aquí el sujeto es el propio producto.
 *
 * Cifras ilustrativas pero cuadradas entre sí: los cuatro productos suman el
 * revenue del mes, y el anualizado es ese mes por doce.
 */

/** Los acentos de X-Ray, cada uno con su único trabajo. `ahead` no aparece
 *  aquí: está reservado a lo que el producto sabe antes de que pase. */
export type Tone = 'mint' | 'coral' | 'amber' | 'crimson' | 'live'

export const modelVersion = 'X-Ray v7'

export interface Reading {
  id: string
  label: string
  /** Solo la cifra: la unidad va aparte para poder componerla en la tipografía
   *  de interfaz, que es donde se lee, y no en la mono del instrumento. */
  value: string
  unit?: string
  note: string
  /** Sin tono, la lectura es neutra: un número no es una alarma por sí solo. */
  tone?: Tone
}

export const activeCompanies = 1286

/** Las tres lecturas que abren el monitor, en el orden en que se leen: cuánto
 *  entra, a cuántas empresas y qué está roto ahora mismo. */
export const opsPulse: Reading[] = [
  {
    id: 'revenue',
    label: 'Revenue del mes',
    value: '1,08',
    unit: 'M €',
    note: '+18 % sobre agosto',
    tone: 'mint',
  },
  {
    id: 'empresas',
    label: 'Empresas activas',
    value: activeCompanies.toLocaleString('es-ES'),
    note: '12 nuevas esta semana',
    tone: 'mint',
  },
  {
    id: 'alertas',
    label: 'Alertas abiertas',
    value: '7',
    note: '3 sin contactar todavía',
    tone: 'crimson',
  },
]

export interface RevenueProduct {
  id: string
  label: string
  /** Euros del mes en curso. La barra apilada se dibuja con esto, no con el
   *  porcentaje, para que el reparto no pueda contradecir a los importes. */
  amount: number
  note: string
  tone: Tone
}

export const revenueProducts: RevenueProduct[] = [
  {
    id: 'colchon',
    label: 'Colchón Dinámico',
    amount: 486_000,
    note: 'Comisión sobre lo colocado',
    tone: 'mint',
  },
  {
    id: 'divisa',
    label: 'Divisa Inteligente',
    amount: 335_000,
    note: 'Margen sobre el cambio',
    tone: 'live',
  },
  {
    id: 'saas',
    label: 'SaaS · 350 €/mes',
    amount: 238_000,
    note: 'Suscripción por empresa',
    tone: 'amber',
  },
  {
    id: 'marketplace',
    label: 'Marketplace',
    amount: 18_000,
    note: 'Fee sobre la financiación cerrada',
    tone: 'coral',
  },
]

export const revenueMonth = revenueProducts.reduce(
  (total, product) => total + product.amount,
  0,
)

/** Proyección a doce meses del mes en curso. Es una extrapolación, no una
 *  previsión del modelo, y la vista lo dice con esas palabras. */
export const revenueAnnualised = revenueMonth * 12

export const revenueGrowth = '+18 %'

export interface OpsAlert {
  id: string
  company: string
  when: string
  text: string
  tone: Tone
}

/* Nominales a propósito: esta es la vista interna, y Embat opera la cartera
 * entera. Lo que se anonimiza es la comparativa de sector que ve la empresa. */
export const opsAlerts: OpsAlert[] = [
  {
    id: 'iberica',
    company: 'Distribuciones Ibérica',
    when: 'hace 12 min',
    text: 'Score 82 → 68. Aviso enviado al CFO y ticket de éxito abierto.',
    tone: 'crimson',
  },
  {
    id: 'sureste',
    company: 'Recolectora Sureste',
    when: 'hace 2 h',
    text: 'Score 52 → 39. Deterioro sostenido, aún sin contactar.',
    tone: 'crimson',
  },
  {
    id: 'vidal',
    company: 'Talleres Vidal',
    when: 'hoy, 09:00',
    text: 'Score 45 → 65. Oportunidad de upsell de marketplace.',
    tone: 'mint',
  },
  {
    id: 'marina',
    company: 'Grupo Marina SA',
    when: 'ayer',
    text: 'Colocación de 400 k€ ejecutada. Revenue +550 €/mes.',
    tone: 'mint',
  },
]

export interface ModelMetric {
  id: string
  label: string
  /** Cifra y unidad por separado, como en las lecturas del pulso: la mono es
   *  para el número y la tipografía de interfaz para lo que lo acompaña. */
  value: string
  unit?: string
  /** Qué había que batir y qué significa haberlo batido, en ese orden. */
  target: string
  meaning: string
  beatsTarget: boolean
}

export const modelMetrics: ModelMetric[] = [
  {
    id: 'auc-tension',
    label: 'AUC tensión a 6 meses',
    value: '0,78',
    target: 'Objetivo 0,70',
    meaning:
      'De cada dos empresas, ordena bien cuál de las dos se tensiona antes en casi ocho de cada diez pares.',
    beatsTarget: true,
  },
  {
    id: 'auc-caida',
    label: 'AUC caída a 6 meses',
    value: '0,74',
    target: 'Objetivo 0,65',
    meaning:
      'Lo mismo para la caída estructural, que es el caso que cuesta dinero de verdad.',
    beatsTarget: true,
  },
  {
    id: 'lead',
    label: 'Ventaja mediana',
    value: '2,3',
    unit: 'meses',
    target: '62 % con dos meses o más',
    meaning:
      'Cuánto antes marcamos la trayectoria que el score cambia de tramo. Es el número que vende el producto.',
    beatsTarget: true,
  },
  {
    id: 'silencio',
    label: 'Precisión del silencio',
    value: '98,4',
    unit: '%',
    target: 'Sin falsas alertas',
    meaning:
      'Cuando callamos, acertamos. Un aviso en falso cuesta más que un mes de retraso.',
    beatsTarget: true,
  },
  {
    id: 'skill',
    label: 'Mejora sobre AR(1)',
    value: '+42',
    unit: '%',
    target: 'MAE a tres meses frente al baseline',
    meaning:
      'Lo que aporta el modelo sobre repetir el último mes. Por debajo de cero, no habría producto.',
    beatsTarget: true,
  },
]

export const modelAllClear = modelMetrics.every((metric) => metric.beatsTarget)

/** Importe corto para la barra de revenue: «486 k €», nunca «486.000 €», para
 *  que la etiqueta quepa dentro de su propio tramo. */
export const thousands = (amount: number) =>
  `${Math.round(amount / 1000).toLocaleString('es-ES')} k €`

export const millions = (amount: number) =>
  `${(amount / 1_000_000).toLocaleString('es-ES', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} M €`

export const share = (amount: number, total = revenueMonth) =>
  Math.round((amount / total) * 100)
