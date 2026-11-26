import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ArrowUpRight, CarFront, Heater, ShieldCheck, Shirt, TriangleAlert, UtensilsCrossed, WashingMachine } from 'lucide-react'
import type { EChartsOption } from 'echarts'
import CountUp from '@/components/reactbits/CountUp'
import { Chart, ErrorNote, NumberField, Panel, SectionHead, Segmented, Skeleton, SuitPill, Toggle } from '@/components/ui'
import { api, type DeviceItem, type PreviewResponse, type ScheduleResponse } from '@/lib/api'
import { deviceName, useT } from '@/lib/i18n'
import { SeasonSelect, SEASONS } from '@/lib/seasons'
import { fmtCHF, labelFor, slotTime } from '@/lib/suit'
import { alpha, useTokens } from '@/lib/theme'
import { cn } from '@/lib/utils'

interface DeviceState {
  id: string
  icon: ReactNode
  power_kw: number
  contiguous: boolean
  enabled: boolean
  energy: number
  deadline: number
  energyRange: [number, number, number]
}

const INITIAL: DeviceState[] = [
  { id: 'ev', icon: <CarFront size={18} />, power_kw: 7.4, contiguous: false, enabled: true, energy: 22.2, deadline: 10, energyRange: [5, 80, 1] },
  { id: 'heat_pump', icon: <Heater size={18} />, power_kw: 2.5, contiguous: false, enabled: true, energy: 7.5, deadline: 24, energyRange: [2, 25, 0.5] },
  { id: 'washer', icon: <WashingMachine size={18} />, power_kw: 2.0, contiguous: true, enabled: true, energy: 3.0, deadline: 16, energyRange: [1, 5, 0.5] },
  { id: 'dryer', icon: <Shirt size={18} />, power_kw: 2.5, contiguous: true, enabled: true, energy: 3.5, deadline: 18, energyRange: [1, 6, 0.5] },
  { id: 'dishwasher', icon: <UtensilsCrossed size={18} />, power_kw: 1.5, contiguous: true, enabled: true, energy: 1.8, deadline: 20, energyRange: [1, 4, 0.2] },
]

const PEAK_START = 70 // 17:30
const PEAK_END = 82 // 20:30

export function SchedulerView({
  season,
  setSeason,
  onInspect,
}: {
  season: string
  setSeason: (s: string) => void
  onInspect: () => void
}) {
  const { t, lang } = useT()
  const [conc, setConc] = useState(1)
  const [devices, setDevices] = useState(INITIAL)
  const [data, setData] = useState<ScheduleResponse | null>(null)
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  const active = devices.filter((d) => d.enabled)
  const payload: DeviceItem[] = useMemo(
    () =>
      active.map((d) => ({
        id: d.id,
        name: deviceName(lang, d.id),
        power_kw: d.power_kw,
        energy_kwh: d.energy,
        deadline_hours: d.deadline,
        contiguous: d.contiguous,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(active), lang],
  )

  useEffect(() => {
    if (!payload.length) {
      setData(null)
      setLoading(false)
      return
    }
    const ctl = new AbortController()
    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const [s, p] = await Promise.all([
          // API caps this at 10; with five appliances that is effectively unlimited
          api.schedule({ season, max_concurrent_devices: Math.min(conc, 10), devices: payload, lang }, ctl.signal),
          api.preview(season, lang, ctl.signal),
        ])
        setData(s)
        setPreview(p)
        setError(null)
      } catch (e) {
        if ((e as Error).name !== 'AbortError') setError(t('errorApi'))
      } finally {
        if (!ctl.signal.aborted) setLoading(false)
      }
    }, 220)
    return () => {
      clearTimeout(timer)
      ctl.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season, conc, payload, lang, nonce])

  const update = useCallback((id: string, patch: Partial<DeviceState>) => {
    setDevices((ds) => ds.map((d) => (d.id === id ? { ...d, ...patch } : d)))
  }, [])

  const peakHit = !!data?.devices.some((d) => d.slots.some((s) => s >= PEAK_START && s < PEAK_END))
  const meta = SEASONS.find((s) => s.id === season)

  return (
    <div className="space-y-6">
      {/* Hero: one sentence that answers "what does this save me?", then the day itself */}
      <section className="border-b border-line pb-8">
        <h1 className="max-w-[30ch] text-[clamp(1.9rem,4.2vw,3.25rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-ink">
          {data ? <Headline data={data} /> : <span className="text-ink-3">{t('loading')}</span>}
        </h1>
        <p className="mt-4 max-w-[60ch] text-base leading-relaxed text-ink-2">{t('heroLead')}</p>

        <div className="mt-8">
          <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <h2 className="text-[15px] font-semibold">{t('ribbon')}</h2>
            <span className="text-sm text-ink-2">
              {meta?.label}
              {data?.date ? <span className="num"> · {data.date}</span> : null}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-ink-3">{t('ribbonNote')}</p>
          {preview && data ? <DayRibbon preview={preview} data={data} /> : <Skeleton className="mt-3 h-16" />}
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <span className={cn('inline-flex items-center gap-2', peakHit ? 'text-ink' : 'text-ink-2')}>
              {peakHit ? <TriangleAlert size={16} className="text-avoid" /> : <ShieldCheck size={16} className="text-ideal" />}
              {peakHit ? t('peakHit') : t('peakClear')}
            </span>
            {data && (
              <span className="text-ink-2">
                <span className="num text-ink">{data.savings_percent.toFixed(1)}%</span> {t('savedWord')} ·{' '}
                <span className="num line-through decoration-1">{fmtCHF(data.total_peak_cost_chf)}</span> → <span className="num text-ink">{fmtCHF(data.total_cost_chf)}</span>
              </span>
            )}
          </div>
        </div>
      </section>

      {error && <ErrorNote message={error} onRetry={() => setNonce((n) => n + 1)} retry={t('retry')} />}

      <div className="grid gap-6 lg:grid-cols-[minmax(300px,380px)_1fr]">
        {/* Controls */}
        <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          <Panel className="space-y-5">
            <SeasonSelect value={season} onChange={setSeason} />
            <div>
              <div className="eyebrow">{t('breaker')}</div>
              <Segmented
                className="mt-1.5 flex w-full"
                label={t('breaker')}
                value={conc}
                onChange={setConc}
                options={[
                  { value: 1, label: '1', hint: t('conc_1_desc') },
                  { value: 2, label: '2', hint: t('conc_2_desc') },
                  { value: 3, label: '3', hint: t('conc_3_desc') },
                  { value: 99, label: '∞', hint: t('conc_99_desc') },
                ]}
              />
              <p className="mt-2 text-sm leading-relaxed text-ink-3">{t(`conc_${conc}_desc`)}</p>
            </div>
          </Panel>

          <Panel className="p-0 sm:p-0">
            <div className="flex items-center justify-between px-5 pt-5 sm:px-6">
              <h2 className="text-[15px] font-semibold">{t('appliances')}</h2>
              <span className="num text-xs text-ink-3">
                {active.length}/{devices.length} · {active.reduce((a, d) => a + d.power_kw, 0).toFixed(1)} kW
              </span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 border-b border-line px-5 pb-2 pl-[4.25rem] text-sm text-ink-2 sm:px-6 sm:pl-[4.5rem]" aria-hidden="true">
              <span>{t('colEnergy')}</span>
              <span>{t('colReady')}</span>
            </div>
            <ul className="divide-y divide-line">
              {devices.map((d) => (
                <li key={d.id} className={cn('px-5 py-4 transition-opacity sm:px-6', !d.enabled && 'opacity-55')}>
                  <div className="flex items-center gap-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sunken text-ink-2">{d.icon}</span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{deviceName(lang, d.id)}</div>
                      <div className="num text-xs text-ink-3">
                        {d.power_kw.toFixed(1)} kW · {d.contiguous ? t('recContinuous') : t('recFlexibleSlots')}
                      </div>
                    </div>
                    <Toggle checked={d.enabled} onChange={(v) => update(d.id, { enabled: v })} label={deviceName(lang, d.id)} />
                  </div>
                  {d.enabled && (
                    <div className="mt-3 grid grid-cols-2 gap-3 pl-12">
                      <NumberField
                        hideLabel
                        label={`${t('colEnergy')} · ${deviceName(lang, d.id)}`}
                        unit="kWh"
                        value={d.energy}
                        min={d.energyRange[0]}
                        max={d.energyRange[1]}
                        step={d.energyRange[2]}
                        onChange={(v) => update(d.id, { energy: v })}
                      />
                      <NumberField
                        hideLabel
                        label={`${t('colReady')} · ${deviceName(lang, d.id)}`}
                        unit={t('hours')}
                        value={d.deadline}
                        min={1}
                        max={24}
                        step={1}
                        onChange={(v) => update(d.id, { deadline: v })}
                      />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
        </aside>

        {/* Results */}
        <div className="min-w-0 space-y-6">
          <Panel>
            <SectionHead
              title={t('dayCurve')}
              note={t('dayCurveNote')}
              aside={
                <button
                  onClick={onInspect}
                  className="inline-flex items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-ink hover:text-ink"
                >
                  {t('connBtn')} <ArrowUpRight size={14} />
                </button>
              }
            />
            {data && preview ? <DayChart data={data} preview={preview} /> : <Skeleton className="h-[280px]" />}
            <Legend />
          </Panel>

          <Panel>
            <SectionHead title={t('timeline')} note={t('timelineNote')} />
            {!payload.length ? (
              <p className="py-8 text-center text-sm text-ink-3">{t('noDevices')}</p>
            ) : data ? (
              <Timeline data={data} />
            ) : (
              <Skeleton className="h-[220px]" />
            )}
          </Panel>

          <Panel className="p-0 sm:p-0">
            <div className="flex items-center justify-between px-5 pt-5 sm:px-6">
              <h2 className="text-[15px] font-semibold">{t('plan')}</h2>
              {loading && <span className="text-xs text-ink-3">{t('loading')}</span>}
            </div>
            {data && payload.length ? (
              <PlanTable data={data} />
            ) : (
              <p className="px-6 py-8 text-sm text-ink-3">{payload.length ? t('loading') : t('noDevices')}</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}

function Headline({ data }: { data: ScheduleResponse }) {
  const { t } = useT()
  const parts = t('heroHeadline').split(/(\{cost\}|\{saved\})/)
  return (
    <>
      {parts.map((part, i) =>
        part === '{cost}' ? (
          <span key={i} className="tabular-nums">
            {fmtCHF(data.total_cost_chf)}
          </span>
        ) : part === '{saved}' ? (
          <span key={i} className="inline-block whitespace-nowrap border-b-[0.07em] border-ideal/45 leading-[1.05] tabular-nums text-ideal">
            CHF{' '}
            <CountUp key={data.total_savings_chf} to={data.total_savings_chf} decimals={2} duration={1.1} mode="roll" easing="spring" trigger="load" />
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

/** 96 fifteen-minute cells coloured by suitability, with ticks where any appliance runs. */
function DayRibbon({ preview, data }: { preview: PreviewResponse; data: ScheduleResponse }) {
  const { t } = useT()
  const running = new Map<number, string[]>()
  data.devices.forEach((d) => d.slots.forEach((s) => running.set(s, [...(running.get(s) ?? []), d.name])))
  const steps = preview.steps.slice(0, 96)
  const n = steps.length || 96
  const best = steps.reduce((bi, s, i, arr) => (s.score > arr[bi].score ? i : bi), 0)
  return (
    <div className="mt-3" role="img" aria-label={`${t('ribbon')} · ${data.date}`}>
      <div className="relative pt-2">
        <svg viewBox={`0 0 ${n * 10} 64`} preserveAspectRatio="none" className="block h-16 w-full overflow-visible">
          {steps.map((s, i) => (
            <rect
              key={i}
              x={i * 10}
              y={0}
              width={9}
              height={48}
              fill={`var(--s-${s.label})`}
              opacity={running.has(i) ? 1 : 0.42}
            >
              <title>{`${s.time} · S ${s.score.toFixed(0)} · ${s.total_rp.toFixed(1)} Rp./kWh${running.has(i) ? ' · ' + running.get(i)!.join(', ') : ''}`}</title>
            </rect>
          ))}
          {steps.map((_, i) => (running.has(i) ? <rect key={`r${i}`} x={i * 10} y={54} width={9} height={6} fill="var(--ink)" /> : null))}
          <rect
            x={PEAK_START * 10 - 3}
            y={-4}
            width={(PEAK_END - PEAK_START) * 10 + 2}
            height={56}
            fill="none"
            stroke="var(--ink)"
            strokeOpacity={0.55}
            strokeDasharray="6 5"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <div className="pointer-events-none absolute top-0 size-0" style={{ left: `${((best + 0.5) / n) * 100}%` }}>
          <div className="-translate-x-1/2 -translate-y-1 border-x-[5px] border-t-[6px] border-x-transparent border-t-ink" />
        </div>
      </div>
      <div className="num mt-1.5 flex justify-between text-xs text-ink-3">
        {['00', '03', '06', '09', '12', '15', '18', '21', '24'].map((h) => (
          <span key={h}>{h}:00</span>
        ))}
      </div>
    </div>
  )
}

function Legend() {
  const { t } = useT()
  const items: [string, string][] = [
    ['ideal', t('legendIdeal')],
    ['good', t('legendGood')],
    ['okay', t('legendOkay')],
    ['wait', t('legendWait')],
    ['avoid', t('legendAvoid')],
  ]
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-3">
      {items.map(([k, v]) => (
        <span key={k} className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-sm" style={{ background: `var(--s-${k})` }} />
          {v}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <span className="h-0.5 w-3 rounded" style={{ background: 'var(--price)' }} />
        Rp./kWh
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-sm bg-ink-3 opacity-40" />
        {t('legendIdle')}
      </span>
    </div>
  )
}

function axisBase(tk: Record<string, string>) {
  return {
    axisLine: { lineStyle: { color: tk['--line-strong'] } },
    axisTick: { show: false },
    axisLabel: { color: tk['--ink-3'], fontFamily: 'IBM Plex Mono', fontSize: 11 },
    splitLine: { lineStyle: { color: tk['--line'], type: 'dashed' as const } },
  }
}

function tooltipBase(tk: Record<string, string>) {
  return {
    backgroundColor: tk['--surface'],
    borderColor: tk['--line'],
    textStyle: { color: tk['--ink'], fontFamily: 'Schibsted Grotesk', fontSize: 12 },
    extraCssText: 'border-radius:10px;box-shadow:0 8px 24px rgb(0 0 0 / .12);',
  }
}

function DayChart({ data, preview }: { data: ScheduleResponse; preview: PreviewResponse }) {
  const tk = useTokens()
  const { t } = useT()
  const hours = data.hourly_fuzzy_scores.map((_, h) => String(h).padStart(2, '0'))
  const hourlyPrice = hours.map((_, h) => {
    const s = preview.steps.slice(h * 4, h * 4 + 4)
    return s.length ? Number((s.reduce((a, x) => a + x.total_rp, 0) / s.length).toFixed(2)) : null
  })

  const option: EChartsOption = {
    animationDuration: 700,
    animationEasing: 'cubicOut',
    grid: { left: 36, right: 44, top: 26, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      ...tooltipBase(tk),
      formatter: (ps: unknown) => {
        const arr = ps as { dataIndex: number }[]
        const h = arr[0].dataIndex
        const sc = data.hourly_fuzzy_scores[h]
        const al = data.hourly_allocations[h]
        return `<div style="font-weight:600;margin-bottom:4px">${hours[h]}:00</div>
          <div>${t('suitability')}: <b style="font-family:IBM Plex Mono">${sc.toFixed(1)}</b> · ${data.hourly_fuzzy_labels[h]}</div>
          <div>${t('price')}: <b style="font-family:IBM Plex Mono">${hourlyPrice[h] ?? '—'}</b> Rp./kWh</div>
          <div style="color:${tk['--ink-3']};margin-top:4px">${al.length ? al.join(', ') : t('hourNone')}</div>`
      },
    },
    xAxis: { type: 'category', data: hours, ...axisBase(tk), splitLine: { show: false } },
    yAxis: [
      { type: 'value', min: 0, max: 100, interval: 25, ...axisBase(tk) },
      { type: 'value', ...axisBase(tk), splitLine: { show: false }, axisLabel: { ...axisBase(tk).axisLabel, formatter: '{value}' } },
    ],
    series: [
      {
        type: 'bar',
        name: 'S',
        barCategoryGap: '22%',
        data: data.hourly_fuzzy_scores.map((v, h) => ({
          value: v,
          itemStyle: {
            color: tk[`--s-${data.hourly_fuzzy_labels[h] ?? labelFor(v)}`],
            borderRadius: [3, 3, 0, 0],
            opacity: data.hourly_allocations[h].length ? 1 : 0.55,
          },
        })),
        markArea: {
          silent: true,
          itemStyle: { color: alpha(tk['--s-avoid'], 0.08) },
          label: { show: true, position: 'top', distance: 4, color: tk['--ink-3'], fontSize: 10, fontFamily: 'IBM Plex Mono', formatter: '17:30–20:30' },
          data: [[{ xAxis: '17' }, { xAxis: '20' }]],
        },
      },
      {
        type: 'line',
        name: 'Rp./kWh',
        yAxisIndex: 1,
        data: hourlyPrice,
        smooth: 0.35,
        symbol: 'none',
        lineStyle: { width: 2, color: tk['--price'] },
      },
    ],
  }
  return <Chart option={option} height={280} label={t('dayCurve')} />
}

function Timeline({ data }: { data: ScheduleResponse }) {
  const tk = useTokens()
  const { t } = useT()
  const names = data.devices.map((d) => d.name)
  const blocks: { value: [number, number, number, number]; itemStyle: { color: string } }[] = []
  data.devices.forEach((d, i) => {
    const s = [...d.slots].sort((a, b) => a - b)
    let start = s[0]
    for (let k = 1; k <= s.length; k++) {
      if (k === s.length || s[k] !== s[k - 1] + 1) {
        blocks.push({ value: [i, start, s[k - 1] + 1, d.avg_fuzzy_score], itemStyle: { color: tk[`--s-${d.fuzzy_label}`] } })
        start = s[k]
      }
    }
  })

  const option: EChartsOption = {
    animationDuration: 650,
    grid: { left: 8, right: 26, top: 8, bottom: 26, containLabel: true },
    tooltip: {
      ...tooltipBase(tk),
      formatter: (p: unknown) => {
        const v = (p as { value: number[] }).value
        return `<b>${names[v[0]]}</b><br/><span style="font-family:IBM Plex Mono">${slotTime(v[1])} – ${slotTime(v[2])}</span>`
      },
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 96,
      interval: 12,
      ...axisBase(tk),
      axisLabel: { ...axisBase(tk).axisLabel, formatter: (v: number) => slotTime(v) },
    },
    yAxis: {
      type: 'category',
      data: names,
      inverse: true,
      ...axisBase(tk),
      axisLine: { show: false },
      splitLine: { show: false },
      axisLabel: { color: tk['--ink-2'], fontSize: 12, fontFamily: 'Schibsted Grotesk' },
    },
    series: [
      {
        type: 'custom',
        encode: { x: [1, 2], y: 0 },
        data: blocks,
        renderItem: (_params: unknown, api: any) => {
          const cat = api.value(0)
          const a = api.coord([api.value(1), cat])
          const b = api.coord([api.value(2), cat])
          const h = api.size([0, 1])[1] * 0.56
          return {
            type: 'rect',
            shape: { x: a[0], y: a[1] - h / 2, width: Math.max(2, b[0] - a[0] - 1), height: h, r: 4 },
            style: api.style(),
          }
        },
        markArea: {
          silent: true,
          itemStyle: { color: alpha(tk['--s-avoid'], 0.08) },
          data: [[{ xAxis: PEAK_START }, { xAxis: PEAK_END }]],
        },
      } as any,
    ],
  }
  return <Chart option={option} height={Math.max(160, 48 + names.length * 40)} label={t('timeline')} />
}

function PlanTable({ data }: { data: ScheduleResponse }) {
  const { t } = useT()
  return (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="text-left">
            {['', t('runs'), t('score'), t('avgTariff'), t('rules'), t('saves')].map((h, i) => (
              <th key={i} className={cn('eyebrow px-3 py-2 font-semibold first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6', i === 5 && 'text-right')}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line border-t border-line">
          {data.devices.map((d) => (
            <tr key={d.id} className="align-top transition-colors hover:bg-sunken/60">
              <td className="py-3.5 pl-5 pr-3 sm:pl-6">
                <div className="font-medium">{d.name}</div>
                <div className="num text-xs text-ink-3">
                  {d.energy_kwh} kWh · {d.duration_hours} h
                </div>
              </td>
              <td className="num px-3 py-3.5 text-[13px]">
                {d.time_windows.length ? d.time_windows.map((w) => <div key={w}>{w}</div>) : t('recFlexibleOvernight')}
              </td>
              <td className="px-3 py-3.5">
                <div className="flex items-center gap-2">
                  <span className="num text-[13px]">{d.avg_fuzzy_score.toFixed(1)}</span>
                  <SuitPill label={d.fuzzy_label} />
                </div>
              </td>
              <td className="num px-3 py-3.5 text-[13px]">{d.avg_price_rp.toFixed(2)} Rp.</td>
              <td className="px-3 py-3.5">
                <div className="flex flex-wrap gap-1">
                  {d.fired_rules.map((r) => (
                    <span key={r} className="num rounded bg-sunken px-1.5 py-0.5 text-[11px] text-ink-2 ring-1 ring-line">
                      {r}
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-3.5 pl-3 pr-5 text-right sm:pr-6">
                <div className="num font-medium text-ink">{fmtCHF(d.saved_chf)}</div>
                <div className="num text-xs text-ink-3">{fmtCHF(d.cost_chf)}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
