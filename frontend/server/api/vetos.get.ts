/**
 * El catálogo de vetos: los hechos de hoy que mandan sobre la nota.
 *
 * Un veto es verificable y discutible — el CFO enseña el justificante y se cae — y nunca
 * mejora la decisión, solo la bloquea. Por eso vive encima del score y no dentro.
 */
export default defineEventHandler(async () => {
  const catalog = await scoreCatalog()
  return { vetos: catalog.vetos, acciones: catalog.acciones }
})
