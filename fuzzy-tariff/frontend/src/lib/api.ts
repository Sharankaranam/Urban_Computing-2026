export type Lang = 'en' | 'de' | 'fr' | 'it'
export type SuitLabel = 'ideal' | 'good' | 'okay' | 'wait' | 'avoid'

export interface DeviceItem {
  id: string
  name: string
  power_kw: number
  energy_kwh: number
  deadline_hours: number
  contiguous: boolean
}

export interface ScheduledDevice {
  id: string
  name: string
  power_kw: number
  energy_kwh: number
  duration_hours: number
  slots: number[]
  time_windows: string[]
  avg_price_rp: number
  avg_fuzzy_score: number
  fuzzy_label: SuitLabel
  stage2_action: string
  fired_rules: string[]
  cost_chf: number
  peak_cost_chf: number
  saved_chf: number
  advice_text: string
}

export interface ScheduleResponse {
  season: string
  date: string
  max_concurrent_devices: number
  total_cost_chf: number
  total_peak_cost_chf: number
  total_savings_chf: number
  savings_percent: number
  cheapest_window_overall: string
  peak_window_to_avoid: string
  devices: ScheduledDevice[]
  hourly_allocations: string[][]
  hourly_fuzzy_scores: number[]
  hourly_fuzzy_labels: SuitLabel[]
}

export interface TariffStep {
  time: string
  spot_eur_mwh: number
  net_load_mw: number
  energy_rp: number
  grid_rp: number
  sdl_rp: number
  total_rp: number
  score: number
  label: SuitLabel
  text: string
}

export interface PreviewResponse {
  season: string
  date: string
  steps: TariffStep[]
}

export interface ScoreResponse {
  score: number
  label: SuitLabel
  text: string
  memberships: Record<string, number>
  fired_rules: { id: string; strength: number; description: string }[]
}

export interface MfSet {
  shape: 'tri' | 'trap'
  params: number[]
}
export interface FisVar {
  universe: [number, number]
  sets: Record<string, MfSet>
}
export interface FisRule {
  id: string
  if: Record<string, string>
  then: string
  description: string
}
export interface FisStage {
  name: string
  inputs: Record<string, FisVar>
  output: FisVar
  rules: FisRule[]
}
export interface FisConfig {
  version: string | number
  stage1: FisStage
  stage2: FisStage
}

export interface Protoform {
  protoform_type: string
  quantifier: string
  quantifier_label: string
  qualifier: string | null
  qualifier_label: string | null
  summarizer: string
  summarizer_label: string
  cardinality_ratio: number
  truth_degree: number
  coverage_degree: number
  validity_score: number
  statement: string
  status?: string
}

export interface Option {
  id: string
  label: string
}

export interface SummaryResponse {
  season: string
  date: string
  lang: Lang
  headline: string
  narrative: string[]
  top_protoforms: Protoform[]
  quantifiers: Option[]
  qualifiers: Option[]
  summarizers: Option[]
}

async function req<T>(url: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text.slice(0, 200)}` : ''}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  schedule: (b: { season: string; max_concurrent_devices: number; devices: DeviceItem[]; lang: Lang }, s?: AbortSignal) =>
    req<ScheduleResponse>('/v1/smart-schedule', b, s),
  preview: (season: string, lang: Lang, s?: AbortSignal) =>
    req<PreviewResponse>(`/v1/tariff/preview?season=${encodeURIComponent(season)}&lang=${lang}`, undefined, s),
  score: (b: { P: number; A: number; G: number; T: number; lang: Lang }, s?: AbortSignal) =>
    req<ScoreResponse>('/v1/score', b, s),
  config: () => req<FisConfig>('/v1/config'),
  summary: (season: string, lang: Lang, s?: AbortSignal) =>
    req<SummaryResponse>(`/v1/summarize/daily?season=${encodeURIComponent(season)}&lang=${lang}`, undefined, s),
  evaluate: (
    b: { season: string; quantifier: string; qualifier: string; summarizer: string; lang: Lang },
    s?: AbortSignal,
  ) => req<Protoform & { status: string }>('/v1/summarize/evaluate', b, s),
}

/** Membership degree for a triangular / trapezoidal set, same maths as the engine. */
export function mu(set: MfSet, x: number): number {
  const p = set.params
  if (set.shape === 'tri') {
    const [a, b, c] = p
    if (x === b) return 1
    if (x <= a || x >= c) return 0
    return x < b ? (x - a) / (b - a) : (c - x) / (c - b)
  }
  const [a, b, c, d] = p
  if (x >= b && x <= c) return 1
  if (x <= a || x >= d) return 0
  return x < b ? (x - a) / (b - a) : (d - x) / (d - c)
}
