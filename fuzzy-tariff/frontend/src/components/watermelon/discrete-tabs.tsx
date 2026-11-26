/**
 * Discrete tabs — adapted from Watermelon UI (ui.watermelon.sh/r/discrete-tabs).
 * Changes: controlled `value`, roving-tabindex keyboard nav (role="tablist"),
 * compact sizing, theme tokens; the shine sweep is kept.
 */
import { useEffect, useRef, useState, type FC, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '@/lib/utils'

export interface TabItem {
  id: string
  icon: ReactNode
  label: string
}

interface DiscreteTabsProps {
  tabs: TabItem[]
  value: string
  onChange: (id: string) => void
  className?: string
}

export const DiscreteTabs: FC<DiscreteTabsProps> = ({ tabs, value, onChange, className }) => {
  const [shine, setShine] = useState(false)
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  useEffect(() => {
    const timer = setTimeout(() => setShine(true), 450)
    return () => {
      clearTimeout(timer)
      setShine(false)
    }
  }, [value])

  const onKey = (e: React.KeyboardEvent, i: number) => {
    const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!dir) return
    e.preventDefault()
    const next = (i + dir + tabs.length) % tabs.length
    refs.current[next]?.focus()
    onChange(tabs[next].id)
  }

  return (
    <motion.div layout role="tablist" className={cn('flex items-center gap-1.5', className)}>
      {tabs.map((tab, i) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            ref={(n) => {
              refs.current[i] = n
            }}
            role="tab"
            aria-selected={active}
            aria-label={tab.label}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(e) => onKey(e, i)}
            className="relative rounded-full focus-visible:outline-offset-1"
          >
            <motion.div
              layout="position"
              transition={{ type: 'spring', stiffness: 260, damping: 24 }}
              className={cn(
                'flex h-9 items-center justify-center rounded-full border px-2.5 transition-colors duration-200',
                active
                  ? 'border-ink bg-ink text-paper'
                  : 'border-line bg-surface text-ink-2 hover:border-line-strong hover:text-ink',
              )}
            >
              <span className="flex size-4 items-center justify-center">{tab.icon}</span>
              <motion.span
                initial={false}
                animate={{ width: active ? 'auto' : 0, opacity: active ? 1 : 0, marginLeft: active ? 7 : 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="relative overflow-hidden whitespace-nowrap text-sm font-medium"
              >
                {tab.label}
                <AnimatePresence>
                  {active && shine && (
                    <motion.span
                      initial={{ left: '-120%' }}
                      animate={{ left: '120%' }}
                      transition={{ duration: 0.55, ease: 'linear' }}
                      className="absolute inset-y-0 w-10 bg-gradient-to-r from-transparent via-paper/40 to-transparent"
                    />
                  )}
                </AnimatePresence>
              </motion.span>
            </motion.div>
          </button>
        )
      })}
    </motion.div>
  )
}
