/**
 * Renderizador de las respuestas del asistente.
 *
 * Devuelve DATOS, no HTML: la plantilla pinta cada trozo con `<strong>`, `<em>` o `<code>`
 * y nunca usa `v-html` con texto del modelo. Es la razón de no traer una librería de markdown:
 * un LLM no puede inyectar etiquetas en algo que jamás se interpreta como HTML.
 *
 * Cubre lo que el asistente escribe de verdad: negrita, cursiva, tachado, código en línea,
 * listas (con sublistas), títulos, citas y separadores. No hay tablas ni enlaces a propósito —
 * las tablas viven en el panel de análisis, y el agente no tiene a dónde enlazar.
 */
export type Inline = {
  text: string
  bold?: boolean
  italic?: boolean
  strike?: boolean
  code?: boolean
}
export type BlockKind = 'p' | 'li' | 'ol' | 'h' | 'quote' | 'hr'
export type Block = {
  kind: BlockKind
  inline: Inline[]
  /** Número ya escrito de una lista ordenada, p. ej. «2.». */
  n?: string
  /** Nivel de sangría de una lista, empezando en 0. */
  depth?: number
}

/* El orden importa: el código va primero para que un `**` dentro de backticks no se lea como negrita. */
const MARKS: { re: RegExp, key: keyof Omit<Inline, 'text'> }[] = [
  { re: /`([^`]+)`/, key: 'code' },
  { re: /\*\*([\s\S]+?)\*\*/, key: 'bold' },
  { re: /__([\s\S]+?)__/, key: 'bold' },
  { re: /~~([^~]+)~~/, key: 'strike' },
  { re: /(?<![*\w])\*([^*\n]+)\*(?!\*)/, key: 'italic' },
  { re: /(?<![_\w])_([^_\n]+)_(?!\w)/, key: 'italic' },
]

/**
 * Marcador abierto al final del stream. Mientras llega `**61**`, por un instante el texto es
 * `**6` y se verían los asteriscos; se quita el marcador solo si está sin pareja y está en la
 * punta del texto, que es donde el stream corta.
 */
function closeDangling(text: string): string {
  let out = text
  for (const mark of ['`', '**', '__', '~~']) {
    if ((out.split(mark).length - 1) % 2 === 0) continue
    const i = out.lastIndexOf(mark)
    if (out.slice(i).includes('\n')) continue
    out = out.slice(0, i) + out.slice(i + mark.length)
  }
  for (const mark of ['*', '_']) {
    // los dobles ya están resueltos: se descuentan para no contarlos como simples
    if ((out.split(mark + mark).join('').split(mark).length - 1) % 2 === 0) continue
    const i = out.lastIndexOf(mark)
    if (out.slice(i).includes('\n') || out[i - 1] === mark || out[i + 1] === mark) continue
    out = out.slice(0, i) + out.slice(i + 1)
  }
  return out
}

export function inline(text: string, open: Partial<Inline> = {}): Inline[] {
  for (const { re, key } of MARKS) {
    const m = re.exec(text)
    if (!m) continue
    const before = text.slice(0, m.index)
    const after = text.slice(m.index + m[0].length)
    return [
      ...(before ? inline(before, open) : []),
      // dentro del código no se busca más marcado: un backtick es literal por definición
      ...(key === 'code' ? [{ ...open, text: m[1]!, code: true }] : inline(m[1]!, { ...open, [key]: true })),
      ...(after ? inline(after, open) : []),
    ]
  }
  return text ? [{ ...open, text }] : []
}

/** Una lista sangrada dos espacios (o un tabulador) es una sublista. */
const depthOf = (indent: string) => Math.min(3, Math.floor(indent.replace(/\t/g, '  ').length / 2))

export function blocks(text: string): Block[] {
  // el marcador a medio escribir se oculta hasta que el stream lo cierre
  const clean = closeDangling(text)
  return clean
    .split('\n')
    .map(line => line.replace(/\s+$/, ''))
    .filter(line => line.trim())
    .map((line): Block => {
      const bare = line.trim()
      if (/^([-*_])\1{2,}$/.test(bare)) return { kind: 'hr', inline: [] }

      const head = bare.match(/^(#{1,4})\s+(.*)$/)
      if (head) return { kind: 'h', inline: inline(head[2]!), depth: head[1]!.length - 1 }

      const quote = bare.match(/^>\s?(.*)$/)
      if (quote) return { kind: 'quote', inline: inline(quote[1]!) }

      const indent = line.match(/^[ \t]*/)![0]
      const num = bare.match(/^(\d+)[.)]\s+(.*)$/)
      if (num) return { kind: 'ol', n: num[1], depth: depthOf(indent), inline: inline(num[2]!) }

      const item = bare.match(/^[-*•]\s+(.*)$/)
      if (item) return { kind: 'li', depth: depthOf(indent), inline: inline(item[1]!) }

      return { kind: 'p', inline: inline(bare) }
    })
}
