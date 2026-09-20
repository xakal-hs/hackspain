/**
 * Qué aprendió el modelo: un peso por señal, dos números de escala y las bandas.
 *
 * Se publica desde el artefacto con `scripts/export_decision_publication.py`, así que lo
 * que se enseña aquí es el modelo que produjo las notas, no una descripción escrita aparte.
 */
export default defineEventHandler(async () => {
  const catalog = await scoreCatalog()
  return {
    score_version: catalog.score_version,
    target: catalog.target,
    alpha_ewma: catalog.alpha_ewma,
    weights: catalog.weights,
    scale: catalog.scale,
    bands: catalog.bands,
    pillars: catalog.pillars,
    anclas: catalog.anclas,
    probabilities: catalog.probabilities,
    features: catalog.features,
  }
})
