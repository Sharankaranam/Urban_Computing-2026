import type { SuitLabel } from './api'

export const SUIT_ORDER: SuitLabel[] = ['ideal', 'good', 'okay', 'wait', 'avoid']

export function labelFor(score: number): SuitLabel {
  if (score >= 80) return 'ideal'
  if (score >= 60) return 'good'
  if (score >= 40) return 'okay'
  if (score >= 25) return 'wait'
  return 'avoid'
}

export const SUIT_TEXT: Record<SuitLabel, string> = {
  ideal: 'bg-ideal/15 text-ink ring-ideal/40',
  good: 'bg-good/15 text-ink ring-good/40',
  okay: 'bg-okay/20 text-ink ring-okay/50',
  wait: 'bg-wait/15 text-ink ring-wait/45',
  avoid: 'bg-avoid/15 text-ink ring-avoid/45',
}

export const fmtCHF = (v: number) => `CHF ${v.toFixed(2)}`
export const slotTime = (s: number) => {
  const m = s * 15
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}
