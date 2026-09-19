export type ThemeName = 'dark' | 'light'

const THEME_COOKIE = 'xray-theme'

/**
 * Theme lives in a cookie so the server renders the right palette on the first
 * byte and the page never flashes the wrong background. Light is the default,
 * as it is on Embat's own product; the navy rail frames it either way.
 */
export function useTheme() {
  const cookie = useCookie<ThemeName>(THEME_COOKIE, {
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
    default: () => 'light',
  })

  const theme = useState<ThemeName>('xray-theme', () =>
    cookie.value === 'dark' ? 'dark' : 'light',
  )

  function setTheme(next: ThemeName) {
    theme.value = next
    cookie.value = next
  }

  return {
    theme,
    setTheme,
    toggle: () => setTheme(theme.value === 'dark' ? 'light' : 'dark'),
  }
}
