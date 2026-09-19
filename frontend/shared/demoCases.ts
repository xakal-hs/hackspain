/** Los dos casos reales de la demo de Flujo de caja. scripts/build_prevision.py comprueba que se siguen cumpliendo. */
export const demoCases: Record<string, { kind: 'excedente' | 'rotura'; label: string }> = {
  COMP_0835: { kind: 'excedente', label: 'Excedente de caja' },
  COMP_0829: { kind: 'rotura', label: 'Rotura de caja' },
}
