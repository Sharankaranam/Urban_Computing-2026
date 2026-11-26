/**
 * Scrub slider — adapted from Watermelon UI (ui.watermelon.sh/r/scrub-slider).
 * Changes from the original: controlled value with arbitrary min/max/step,
 * pointer events instead of separate mouse/touch handlers, keyboard support
 * (role="slider", arrows/Home/End/PageUp/PageDown), and theme tokens.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FC, type ReactNode } from 'react'
import { motion, useMotionValue, useSpring, type Transition } from 'motion/react'
import { cn } from '@/lib/utils'

const SPRING: Transition = { stiffness: 260, damping: 28 }
const PAD = 14

interface ScrubSliderProps {
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  label: ReactNode
  format?: (v: number) => string
  ticks?: string[]
  className?: string
}

export const ScrubSlider: FC<ScrubSliderProps> = ({
  value,
  min,
  max,
  step,
  onChange,
  label,
  format = (v) => String(v),
  ticks,
  className,
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  const [dragging, setDragging] = useState(false)
  const x = useMotionValue(PAD)
  const sx = useSpring(x, SPRING)
  const fillW = useSpringWidth(sx)
  const count = Math.round((max - min) / step) + 1
  const tickEvery = Math.max(1, Math.round(count / 40))

  const toX = useCallback((v: number) => PAD + ((v - min) / (max - min)) * width, [min, max, width])

  useLayoutEffect(() => {
    if (!ref.current) return
    const measure = () => setWidth(ref.current!.getBoundingClientRect().width - PAD * 2)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    x.set(toX(value))
  }, [value, toX, x])

  const snap = useCallback(
    (v: number) => {
      const clamped = Math.min(max, Math.max(min, v))
      const snapped = Math.round((clamped - min) / step) * step + min
      return Number(snapped.toFixed(4))
    },
    [min, max, step],
  )

  const fromClient = (clientX: number) => {
    if (!ref.current || !width) return
    const left = ref.current.getBoundingClientRect().left + PAD
    const v = snap(min + ((clientX - left) / width) * (max - min))
    if (v !== value) onChange(v)
  }

  const onKey = (e: React.KeyboardEvent) => {
    const big = step * Math.max(1, Math.round(count / 10))
    const map: Record<string, number> = {
      ArrowRight: value + step,
      ArrowUp: value + step,
      ArrowLeft: value - step,
      ArrowDown: value - step,
      PageUp: value + big,
      PageDown: value - big,
      Home: min,
      End: max,
    }
    if (e.key in map) {
      e.preventDefault()
      onChange(snap(map[e.key]))
    }
  }

  return (
    <div className={cn('select-none', className)}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <span className="text-sm text-ink-2">{label}</span>
        <motion.span
          animate={{ scale: dragging ? 1.06 : 1 }}
          transition={SPRING}
          className="num rounded-md bg-ink px-2 py-0.5 text-sm font-medium text-paper"
        >
          {format(value)}
        </motion.span>
      </div>
      <div
        ref={ref}
        role="slider"
        tabIndex={0}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={format(value)}
        aria-label={typeof label === 'string' ? label : undefined}
        onKeyDown={onKey}
        onPointerDown={(e) => {
          ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
          setDragging(true)
          fromClient(e.clientX)
        }}
        onPointerMove={(e) => dragging && fromClient(e.clientX)}
        onPointerUp={() => setDragging(false)}
        onPointerCancel={() => setDragging(false)}
        onLostPointerCapture={() => setDragging(false)}
        onBlur={() => setDragging(false)}
        className="relative h-12 cursor-ew-resize touch-none overflow-hidden rounded-xl border border-line bg-surface transition-colors hover:border-line-strong"
      >
        <div className="absolute inset-y-3" style={{ left: PAD, right: PAD }}>
          {Array.from({ length: count }).map((_, i) =>
            i % tickEvery === 0 ? (
              <div
                key={i}
                className={cn(
                  'absolute w-px -translate-x-1/2 bg-line-strong',
                  i % (tickEvery * 5) === 0 ? 'inset-y-0' : 'inset-y-[30%]',
                )}
                style={{ left: (i / (count - 1)) * width }}
              />
            ) : null,
          )}
        </div>
        <motion.div
          style={{ left: PAD, width: fillW }}
          className="pointer-events-none absolute inset-y-0 bg-ink/[0.06]"
        />
        <motion.div
          style={{ left: sx }}
          animate={{ scaleY: dragging ? 1.12 : 1 }}
          transition={SPRING}
          className="pointer-events-none absolute inset-y-2 w-[3px] -translate-x-1/2 rounded-full bg-ink"
        />
      </div>
      {ticks && (
        <div className="mt-1.5 flex justify-between text-[11px] text-ink-3">
          {ticks.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}

/** Width of the filled track, derived from the spring position. */
function useSpringWidth(sx: ReturnType<typeof useSpring>) {
  const w = useMotionValue(0)
  useEffect(() => sx.on('change', (v) => w.set(Math.max(0, v - PAD))), [sx, w])
  return w
}
