/**
 * Un renderizador mínimo para las respuestas del asistente: párrafos, listas con «- » y negritas
 * con **. Devuelve datos y no HTML, así que la plantilla nunca usa v-html con texto del modelo.
 */
export type Inline = { text: string, bold: boolean }
export type Block = { kind: 'p' | 'li', inline: Inline[] }

export function inline(text: string): Inline[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map(part => part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? { text: part.slice(2, -2), bold: true }
      : { text: part, bold: false })
}

export function blocks(text: string): Block[] {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map((line): Block => {
      const item = line.match(/^[-*•]\s+(.*)$/)
      return item ? { kind: 'li', inline: inline(item[1]!) } : { kind: 'p', inline: inline(line) }
    })
}
