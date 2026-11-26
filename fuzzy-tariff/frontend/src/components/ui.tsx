import { useId, type ReactNode } from 'react'
import { motion } from 'motion/react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { BarChart, CustomChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { cn } from '@/lib/utils'
import type { SuitLabel } from '@/lib/api'
import { SUIT_TEXT } from '@/lib/suit'

echarts.use([
  BarChart,
  LineChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  MarkLineComponent,
  VisualMapComponent,
  CanvasRenderer,
])

export function Chart({
  option,
  height,
  className,
  onEvents,
  label,
}: {
  option: EChartsOption
  height: number
  className?: string
  onEvents?: Record<string, (p: unknown) => void>
  label: string
}) {
  return (
    <div role="img" aria-label={label} className={className}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        notMerge
        lazyUpdate
        style={{ height, width: '100%' }}
        onEvents={onEvents}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}

export function SectionHead({
  title,
  note,
  aside,
  className,
}: {
  title: ReactNode
  note?: ReactNode
  aside?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-2', className)}>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>
        {note && <p className="mt-1 max-w-[68ch] text-sm leading-relaxed text-ink-3">{note}</p>}
      </div>
      {aside}
    </div>
  )
}

export function Panel({ children, className, ...rest }: { children: ReactNode; className?: string } & Record<string, unknown>) {
  return (
    <section className={cn('rounded-2xl border border-line bg-surface p-5 sm:p-6', className)} {...rest}>
      {children}
    </section>
  )
}

/** Segmented single-choice control with a sliding indicator. */
export function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  label,
  className,
  size = 'md',
}: {
  options: { value: T; label: ReactNode; hint?: string }[]
  value: T
  onChange: (v: T) => void
  label: string
  className?: string
  size?: 'sm' | 'md'
}) {
  const id = useId()
  return (
    <div role="radiogroup" aria-label={label} className={cn('inline-flex rounded-xl bg-sunken p-1 ring-1 ring-line', className)}>
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={String(o.value)}
            role="radio"
            aria-checked={active}
            title={o.hint}
            onClick={() => onChange(o.value)}
            className={cn(
              'relative flex-1 whitespace-nowrap rounded-lg font-medium transition-colors',
              size === 'sm' ? 'min-h-8 px-3 py-1.5 text-[13px]' : 'min-h-9 px-3 py-2 text-sm',
              active ? 'text-ink' : 'text-ink-3 hover:text-ink',
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                className="absolute inset-0 rounded-lg bg-surface ring-1 ring-line-strong"
              />
            )}
            <span className="relative">{o.label}</span>
          </button>
        )
      })}
    </div>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-10 shrink-0 items-center rounded-full transition-colors duration-200',
        checked ? 'bg-ink' : 'bg-line-strong',
      )}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 32 }}
        className={cn('size-[18px] rounded-full bg-paper shadow-sm', checked ? 'ml-[19px]' : 'ml-[3px]')}
      />
    </button>
  )
}

export function SuitPill({ label, children, className }: { label: SuitLabel; children?: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        SUIT_TEXT[label],
        className,
      )}
    >
      <span className="size-1.5 rounded-full" style={{ background: `var(--s-${label})` }} />
      {children ?? label}
    </span>
  )
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  hideLabel,
}: {
  hideLabel?: boolean
  label: string
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  step: number
  unit: string
}) {
  const id = useId()
  const clamp = (v: number) => Math.min(max, Math.max(min, Number(v.toFixed(2))))
  return (
    <div className="min-w-0">
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'text-sm text-ink-2'}>
        {label}
      </label>
      <div className={cn(hideLabel ? '' : 'mt-1', 'flex h-10 items-stretch overflow-hidden rounded-lg border border-line bg-paper focus-within:border-ink')}>
        <button
          type="button"
          aria-label={`− ${label}`}
          onClick={() => onChange(clamp(value - step))}
          className="w-9 text-ink-2 transition-colors hover:bg-sunken hover:text-ink"
        >
          −
        </button>
        <input
          id={id}
          type="number"
          inputMode="decimal"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => {
            const v = parseFloat(e.target.value)
            if (!Number.isNaN(v)) onChange(clamp(v))
          }}
          className="num w-full min-w-0 bg-transparent text-center text-sm text-ink outline-none"
        />
        <span className="flex items-center pr-2 text-xs text-ink-3">{unit}</span>
        <button
          type="button"
          aria-label={`+ ${label}`}
          onClick={() => onChange(clamp(value + step))}
          className="w-9 border-l border-line text-ink-2 transition-colors hover:bg-sunken hover:text-ink"
        >
          +
        </button>
      </div>
    </div>
  )
}

export function ErrorNote({ message, onRetry, retry }: { message: string; onRetry: () => void; retry: string }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-avoid/40 bg-avoid/10 px-4 py-3 text-sm">
      <span className="text-ink">{message}</span>
      <button onClick={onRetry} className="rounded-lg bg-ink px-3 py-1 text-sm font-medium text-paper">
        {retry}
      </button>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-lg bg-sunken', className)} />
}
