/* Small SVG helpers. Series are drawn with straight segments on purpose: a
 * smoothed curve invents months that never happened. */

export type Point = [number, number]

export function linearScale(
  domain: [number, number],
  range: [number, number],
): (value: number) => number {
  const span = domain[1] - domain[0] || 1
  return (value) =>
    range[0] + ((value - domain[0]) / span) * (range[1] - range[0])
}

const r = (value: number) => Math.round(value * 100) / 100

export function polyline(points: Point[]): string {
  return points.map(([x, y]) => `${r(x)},${r(y)}`).join(' ')
}

export function linePath(points: Point[]): string {
  if (!points.length) return ''
  return points
    .map(([x, y], index) => `${index ? 'L' : 'M'}${r(x)} ${r(y)}`)
    .join(' ')
}

export function areaPath(points: Point[], baseline: number): string {
  if (!points.length) return ''
  const first = points[0]!
  const last = points[points.length - 1]!
  return `${linePath(points)} L${r(last[0])} ${r(baseline)} L${r(first[0])} ${r(baseline)} Z`
}

/** Pads a numeric domain so the trace never touches the panel edge. */
export function paddedDomain(values: number[], pad = 0.12): [number, number] {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return [min - span * pad, max + span * pad]
}
