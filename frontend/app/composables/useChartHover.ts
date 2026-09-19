import type { Ref } from 'vue'

/* Lectura por encima de las gráficas.
 *
 * Trabaja en porcentajes del ancho del plot porque así es como los charts
 * colocan ya sus superposiciones: el punto activo, el globo y el cursor
 * comparten el mismo sistema de coordenadas que las etiquetas del eje.
 */
export function useChartHover(count: Ref<number>, xAt: (index: number) => number) {
  const plot = ref<HTMLElement | null>(null)
  const active = ref<number | null>(null)

  /** El mes más cercano al puntero, no el que queda a su izquierda: en los
   *  bordes del gráfico lo segundo se siente como un mes de retraso. */
  const nearest = (percent: number) => {
    let best = 0
    let closest = Infinity
    for (let index = 0; index < count.value; index += 1) {
      const gap = Math.abs(xAt(index) - percent)
      if (gap < closest) {
        closest = gap
        best = index
      }
    }
    return best
  }

  const track = (event: PointerEvent) => {
    const box = plot.value?.getBoundingClientRect()
    if (!box?.width || !count.value) return
    active.value = nearest(((event.clientX - box.left) / box.width) * 100)
  }

  const clear = () => {
    active.value = null
  }

  const step = (delta: number) => {
    const from = active.value ?? (delta > 0 ? -1 : count.value)
    active.value = Math.min(count.value - 1, Math.max(0, from + delta))
  }

  /** Las flechas recorren la serie y Escape suelta la lectura, para que el
   *  dato se pueda leer sin ratón. */
  const keys = (event: KeyboardEvent) => {
    if (event.key === 'ArrowRight') step(1)
    else if (event.key === 'ArrowLeft') step(-1)
    else if (event.key === 'Home') active.value = 0
    else if (event.key === 'End') active.value = count.value - 1
    else if (event.key === 'Escape') clear()
    else return
    event.preventDefault()
  }

  /* Un corte que se acorta no puede dejar activo un mes que ya no existe. */
  watch(count, (length) => {
    if (active.value != null && active.value > length - 1) clear()
  })

  return { plot, active, track, clear, keys }
}
