/**
 * Marks which section of the page is being read, so the rail index reports a
 * position instead of only offering links. No animation, just a state change.
 */
export function useSectionIndex(ids: string[]) {
  const active = ref(ids[0] ?? '')

  onMounted(() => {
    const sections = ids
      .map((id) => document.getElementById(id))
      .filter((node): node is HTMLElement => Boolean(node))

    if (!sections.length || !('IntersectionObserver' in window)) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) active.value = visible.target.id
      },
      { rootMargin: '-45% 0px -45% 0px', threshold: [0, 0.25, 0.5, 1] },
    )

    sections.forEach((section) => observer.observe(section))
    onBeforeUnmount(() => observer.disconnect())
  })

  return active
}
