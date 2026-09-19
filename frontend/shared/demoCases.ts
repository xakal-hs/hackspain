/** Un caso real por cada salida de la pestaña Flujo de caja (ver server/api/flujo/[id].get.ts).
 * scripts/build_prevision.py comprueba que el excedente y la rotura se siguen cumpliendo. */
export const demoCases: Record<string, { label: string }> = {
  COMP_0835: { label: 'Excedente y score sano: botón' },
  COMP_0837: { label: 'Excedente sin score sano: nada' },
  COMP_0829: { label: 'Rotura de caja: aviso' },
}
