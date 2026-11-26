import { useEffect, useState } from 'react'

export type Tokens = Record<string, string>

const NAMES = [
  '--paper', '--surface', '--sunken', '--line', '--line-strong', '--ink', '--ink-2', '--ink-3',
  '--signal', '--s-ideal', '--s-good', '--s-okay', '--s-wait', '--s-avoid', '--price',
]

/**
 * ECharts draws on canvas and can't read CSS variables, so resolve them to
 * rgb() strings via a probe element (handles oklch in every browser) and
 * re-resolve whenever the `dark` class flips.
 */
function read(): Tokens {
  const probe = document.createElement('span')
  probe.style.display = 'none'
  document.body.appendChild(probe)
  const out: Tokens = {}
  for (const n of NAMES) {
    probe.style.color = `var(${n})`
    out[n] = getComputedStyle(probe).color
  }
  probe.remove()
  out.dark = document.documentElement.classList.contains('dark') ? '1' : ''
  return out
}

export function useTokens(): Tokens {
  const [tokens, setTokens] = useState<Tokens>(() => read())
  useEffect(() => {
    const obs = new MutationObserver(() => setTokens(read()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => obs.disconnect()
  }, [])
  return tokens
}

/** Mix a resolved rgb()/color() string with transparency. */
export const alpha = (c: string, a: number) => `color-mix(in srgb, ${c} ${Math.round(a * 100)}%, transparent)`
