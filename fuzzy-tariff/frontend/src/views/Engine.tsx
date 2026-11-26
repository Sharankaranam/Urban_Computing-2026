import { useEffect, useMemo, useRef, useState } from 'react'
import type { EChartsOption } from 'echarts'
import { Gauge } from '@/components/watermelon/gauge'
import { ScrubSlider } from '@/components/watermelon/scrub-slider'
import { Chart, ErrorNote, Panel, SectionHead, Segmented, Skeleton, SuitPill } from '@/components/ui'
import { api, mu, type FisConfig, type FisVar, type ScoreResponse } from '@/lib/api'
import { useT } from '@/lib/i18n'
import { pulse } from '@/lib/motion'
import { SUIT_ORDER } from '@/lib/suit'
import { alpha, useTokens } from '@/lib/theme'
import { cn } from '@/lib/utils'

type Inputs = { P: number; A: number; G: number; T: number }
const PRESETS: Record<string, Inputs> = {
  night: { P: 10, A: 0.14, G: 0.1, T: 0 },
  solar: { P: 30, A: 0.18, G: 0.25, T: -0.3 },
  peak: { P: 95, A: 0.34, G: 0.9, T: 0.5 },
}

export function EngineView() {
  const { t, lang } = useT()
  const [inp, setInp] = useState<Inputs>(PRESETS.night)
  const [preset, setPreset] = useState<string>('night')
  const [cfg, setCfg] = useState<FisConfig | null>(null)
  const [res, setRes] = useState<ScoreResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const tableRef = useRef<HTMLTableSectionElement>(null)
  const prevFired = useRef<Set<string>>(new Set())

  useEffect(() => {
    api.config().then(setCfg).catch(() => setError(t('error')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce])

  useEffect(() => {
    const ctl = new AbortController()
    const timer = setTimeout(() => {
      api
        .score({ ...inp, lang }, ctl.signal)
        .then((r) => {
          setRes(r)
          setError(null)
        })
        .catch((e) => e.name !== 'AbortError' && setError(t('error')))
    }, 60)
    return () => {
      clearTimeout(timer)
      ctl.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inp, lang, nonce])

  // Pulse rows that just started firing (anime.js)
  useEffect(() => {
    if (!res || !tableRef.current) return
    const now = new Set(res.fired_rules.map((f) => f.id))
    const fresh = [...now].filter((id) => !prevFired.current.has(id))
    prevFired.current = now
    const rows = fresh.map((id) => tableRef.current!.querySelector(`[data-rule="${id}"]`)).filter(Boolean) as Element[]
    pulse(rows)
  }, [res])

  const set = (k: keyof Inputs) => (v: number) => {
    setPreset('')
    setInp((s) => ({ ...s, [k]: v }))
  }

  const strength = useMemo(() => new Map(res?.fired_rules.map((f) => [f.id, f.strength]) ?? []), [res])
  const s1 = cfg?.stage1

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <h1 className="text-[clamp(1.6rem,3.2vw,2.4rem)] font-semibold leading-tight tracking-[-0.025em]">{t('engineTitle')}</h1>
          <p className="mt-3 max-w-[62ch] text-base leading-relaxed text-ink-2">{t('engineSubtitle')}</p>
        </div>
        <div>
          <div className="eyebrow mb-1.5">{t('presets')}</div>
          <Segmented
            size="sm"
            label={t('presets')}
            value={preset}
            onChange={(p) => {
              setPreset(p)
              setInp(PRESETS[p])
            }}
            options={[
              { value: 'night', label: t('presetNight') },
              { value: 'solar', label: t('presetSolar') },
              { value: 'peak', label: t('presetPeak') },
            ]}
          />
        </div>
      </header>

      {error && <ErrorNote message={error} onRetry={() => setNonce((n) => n + 1)} retry={t('retry')} />}

      <div className="grid gap-6 lg:grid-cols-[minmax(320px,400px)_1fr]">
        <div className="space-y-6">
          <Panel className="space-y-5">
            <SectionHead className="mb-0" title={t('inputs')} />
            <ScrubSlider
              label={t('lblSliderP')}
              value={inp.P}
              min={0}
              max={100}
              step={1}
              onChange={set('P')}
              format={(v) => `${v.toFixed(0)}%`}
              ticks={[t('pRangeCheap'), t('pRangeMed'), t('pRangeExp')]}
            />
            <ScrubSlider
              label={t('lblSliderA')}
              value={inp.A}
              min={0.05}
              max={0.5}
              step={0.01}
              onChange={set('A')}
              format={(v) => `CHF ${v.toFixed(2)}`}
              ticks={['0.05', '0.25', '0.50']}
            />
            <ScrubSlider
              label={t('lblSliderG')}
              value={inp.G}
              min={0}
              max={1}
              step={0.05}
              onChange={set('G')}
              format={(v) => v.toFixed(2)}
              ticks={[t('gRangeLow'), t('gRangeMed'), t('gRangeCrit')]}
            />
            <ScrubSlider
              label={t('lblSliderT')}
              value={inp.T}
              min={-1}
              max={1}
              step={0.1}
              onChange={set('T')}
              format={(v) => (v > 0 ? '+' : '') + v.toFixed(1)}
              ticks={[t('tRangeFall'), t('tRangeFlat'), t('tRangeRise')]}
            />
          </Panel>

          <Panel>
            <h2 className="text-[15px] font-semibold">{t('output')}</h2>
            <div className="mt-3 flex items-center gap-5">
              <Gauge
                value={res?.score ?? 0}
                size={132}
                strokeWidth={9}
                gaugeType="full"
                showValue
                unit=""
                primary={res ? `var(--s-${res.label})` : 'var(--line-strong)'}
                secondary="var(--line)"
                className={{ textClassName: 'fill-[var(--ink)] font-mono' }}
              />
              <div className="min-w-0">
                {res && <SuitPill label={res.label} className="text-sm" />}
                <p className="mt-2 text-sm text-ink">{res?.text}</p>
                <p className="mt-2 text-[13px] leading-relaxed text-ink-3">{t('engineDefuzzNote')}</p>
              </div>
            </div>
          </Panel>
        </div>

        <div className="min-w-0 space-y-6">
          <Panel>
            <SectionHead title={t('membership')} note={t('membershipNote')} />
            {s1 ? (
              <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {(['P', 'A', 'G', 'T'] as const).map((k) => (
                  <MfChart key={k} name={k} v={s1.inputs[k]} x={k === 'A' ? Math.min(1, inp.A) : inp[k]} />
                ))}
              </div>
            ) : (
              <Skeleton className="h-[300px]" />
            )}
          </Panel>

          <Panel>
            <SectionHead title={t('outputSets')} note="μ clipped at each set's activation; dashed line = centroid S" />
            {s1 && res ? <OutputChart v={s1.output} res={res} /> : <Skeleton className="h-[200px]" />}
          </Panel>
        </div>
      </div>

      <Panel className="p-0 sm:p-0">
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5 sm:px-6">
          <h2 className="text-[15px] font-semibold">{t('ruleBase')}</h2>
          <span className="text-xs text-ink-3">
            <span className="num">{res?.fired_rules.length ?? 0}</span> / <span className="num">{s1?.rules.length ?? 19}</span> {t('firing')}
          </span>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="text-left">
                {[t('thRuleId'), 'IF', 'THEN', '', t('strength')].map((h, i) => (
                  <th key={i} className="eyebrow px-3 py-2 font-semibold first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody ref={tableRef} className="divide-y divide-line border-t border-line">
              {s1?.rules.map((r) => {
                const w = strength.get(r.id) ?? 0
                const on = w > 0
                return (
                  <tr key={r.id} data-rule={r.id} className={cn('origin-left transition-colors', on ? 'bg-ideal/[0.07]' : 'text-ink-3')}>
                    <td className="num py-2.5 pl-5 pr-3 text-[13px] font-medium sm:pl-6">{r.id}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(r.if).map(([k, v], i) => (
                          <span key={k} className="text-[13px]">
                            {i > 0 && <span className={cn('mr-1', on ? 'text-ink-2' : 'text-ink-3')}>and</span>}
                            <span className="num">{k}</span> <span className={on ? 'text-ink-2' : 'text-ink-3'}>is</span>{' '}
                            <span className={cn('font-medium', on && 'text-ink')}>{v.replace('_', ' ')}</span>
                          </span>
                        ))}
                      </div>
                      <div className={cn('mt-0.5 text-xs', on ? 'text-ink-2' : 'text-ink-3')}>{r.description}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <SuitPill label={r.then as never} />
                    </td>
                    <td className="w-[28%] px-3 py-2.5">
                      <div className="h-1.5 overflow-hidden rounded-full bg-sunken">
                        <div
                          className="h-full rounded-full transition-[width] duration-300 ease-out"
                          style={{ width: `${w * 100}%`, background: `var(--s-${r.then})` }}
                        />
                      </div>
                    </td>
                    <td className="num py-2.5 pl-3 pr-5 text-right text-[13px] sm:pr-6">{on ? w.toFixed(2) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

const SET_COLORS = ['--s-ideal', '--s-good', '--s-okay', '--s-wait', '--s-avoid', '--price']

function sample(v: FisVar, n = 120) {
  const [lo, hi] = v.universe
  return Array.from({ length: n + 1 }, (_, i) => lo + ((hi - lo) * i) / n)
}

function MfChart({ name, v, x }: { name: string; v: FisVar; x: number }) {
  const tk = useTokens()
  const xs = sample(v)
  const sets = Object.entries(v.sets)
  // Cheap → expensive sets map onto the ideal → avoid palette; trend gets its own order.
  const colorFor = (i: number) => tk[SET_COLORS[Math.round((i / Math.max(1, sets.length - 1)) * 4)]]
  const option: EChartsOption = {
    animation: false,
    grid: { left: 26, right: 8, top: 26, bottom: 22 },
    xAxis: {
      type: 'value',
      min: v.universe[0],
      max: v.universe[1],
      axisLine: { lineStyle: { color: tk['--line-strong'] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: tk['--ink-3'], fontSize: 10, fontFamily: 'IBM Plex Mono' },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      interval: 1,
      axisLabel: { color: tk['--ink-3'], fontSize: 10, fontFamily: 'IBM Plex Mono' },
      splitLine: { lineStyle: { color: tk['--line'], type: 'dashed' } },
    },
    series: [
      ...sets.map(([sn, s], i) => {
        const m = mu(s, x)
        return {
          type: 'line' as const,
          name: sn,
          data: xs.map((xx) => [xx, mu(s, xx)]),
          symbol: 'none',
          lineStyle: { width: m > 0 ? 2 : 1.25, color: colorFor(i), opacity: m > 0 ? 1 : 0.45 },
          areaStyle: m > 0 ? { color: alpha(colorFor(i), 0.12) } : undefined,
        }
      }),
      {
        type: 'line',
        data: [],
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: tk['--ink'], width: 1.5, type: 'solid' },
          label: { show: false },
          data: [{ xAxis: x }],
        },
      },
    ],
  }
  const active = sets.map(([sn, s]) => [sn, mu(s, x)] as const).filter(([, m]) => m > 0)
  return (
    <div>
      <div className="flex items-baseline justify-between text-[13px]">
        <span className="num font-medium">{name}</span>
        <span className="truncate pl-2 text-xs text-ink-3">
          {active.map(([sn, m]) => `${sn.replace('_', ' ')} ${m.toFixed(2)}`).join(' · ')}
        </span>
      </div>
      <Chart option={option} height={130} label={`Membership functions for ${name}`} />
    </div>
  )
}

function OutputChart({ v, res }: { v: FisVar; res: ScoreResponse }) {
  const tk = useTokens()
  const xs = sample(v, 200)
  const option: EChartsOption = {
    animationDuration: 300,
    grid: { left: 26, right: 10, top: 28, bottom: 22 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: tk['--line-strong'] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: tk['--ink-3'], fontSize: 10, fontFamily: 'IBM Plex Mono' },
    },
    yAxis: { type: 'value', min: 0, max: 1, interval: 1, axisLabel: { color: tk['--ink-3'], fontSize: 10 }, splitLine: { lineStyle: { color: tk['--line'], type: 'dashed' } } },
    series: [
      ...SUIT_ORDER.filter((k) => v.sets[k]).flatMap((k) => {
        const s = v.sets[k]
        const cap = res.memberships[k] ?? 0
        const col = tk[`--s-${k}`]
        return [
          { type: 'line' as const, data: xs.map((x) => [x, mu(s, x)]), symbol: 'none', lineStyle: { width: 1, color: col, opacity: 0.5, type: 'dashed' as const } },
          {
            type: 'line' as const,
            data: xs.map((x) => [x, Math.min(cap, mu(s, x))]),
            symbol: 'none',
            lineStyle: { width: cap > 0 ? 2 : 0, color: col },
            areaStyle: cap > 0 ? { color: alpha(col, 0.35) } : undefined,
          },
        ]
      }),
      {
        type: 'line',
        data: [],
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: tk['--ink'], width: 1.5, type: 'dashed' },
          label: { color: tk['--ink'], fontFamily: 'IBM Plex Mono', formatter: `S = ${res.score.toFixed(1)}` },
          data: [{ xAxis: res.score }],
        },
      },
    ],
  }
  return <Chart option={option} height={200} label="Aggregated output sets with centroid" />
}

