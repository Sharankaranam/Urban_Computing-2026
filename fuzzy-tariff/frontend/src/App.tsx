import { useEffect, useRef, useState } from 'react'
import { BookOpenText, CalendarClock, Cpu, MessageSquareQuote } from 'lucide-react'
import { DiscreteTabs } from '@/components/watermelon/discrete-tabs'
import SwitchButton from '@/components/kokonutui/switch-button'
import { LangContext, translate } from '@/lib/i18n'
import type { Lang } from '@/lib/api'
import { MotionConfig } from 'motion/react'
import { SchedulerView } from '@/views/Scheduler'
import { EngineView } from '@/views/Engine'
import { SummaryView } from '@/views/Summary'
import { ReportView } from '@/views/Report'

type View = 'scheduler' | 'engine' | 'summary' | 'report'
const VIEWS: View[] = ['scheduler', 'engine', 'summary', 'report']

const readHash = (): View => {
  const h = window.location.hash.replace('#', '') as View
  return VIEWS.includes(h) ? h : 'scheduler'
}

const LANGS: { id: Lang; label: string }[] = [
  { id: 'en', label: 'EN' },
  { id: 'de', label: 'DE' },
  { id: 'fr', label: 'FR' },
  { id: 'it', label: 'IT' },
]

function safeGet(k: string) {
  try {
    return localStorage.getItem(k)
  } catch {
    return null
  }
}
function safeSet(k: string, v: string) {
  try {
    localStorage.setItem(k, v)
  } catch {
    /* storage blocked */
  }
}

export default function App() {
  const [view, setView] = useState<View>(readHash)
  const [lang, setLang] = useState<Lang>(() => (safeGet('lang') as Lang) || 'en')
  const [season, setSeason] = useState('winter')
  const main = useRef<HTMLElement>(null)
  const t = (k: string) => translate(lang, k)

  useEffect(() => {
    const onHash = () => setView(readHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
    safeSet('lang', lang)
  }, [lang])

  const go = (v: string) => {
    window.history.replaceState(null, '', `#${v}`)
    setView(v as View)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <LangContext.Provider value={lang}>
      <MotionConfig reducedMotion="user">
      <div className="mx-auto flex min-h-dvh max-w-[1320px] flex-col px-4 sm:px-6 lg:px-8">
        <header className="sticky top-0 z-40 -mx-4 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper/85 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <a href="#scheduler" onClick={(e) => (e.preventDefault(), go('scheduler'))} className="flex items-center gap-2.5">
            <SwissMark />
            <span className="flex flex-col leading-none">
              <span className="text-[15px] font-bold tracking-[-0.02em]">{t('appName')}</span>
              <span className="mt-0.5 hidden text-[11px] text-ink-3 sm:block">{t('appTag')}</span>
            </span>
          </a>

          <nav aria-label="Views" className="order-3 w-full overflow-x-auto md:order-none md:w-auto">
            <DiscreteTabs
              value={view}
              onChange={go}
              tabs={[
                { id: 'scheduler', icon: <CalendarClock size={16} />, label: t('navScheduler') },
                { id: 'engine', icon: <Cpu size={16} />, label: t('navEngine') },
                { id: 'summary', icon: <MessageSquareQuote size={16} />, label: t('navSummary') },
                { id: 'report', icon: <BookOpenText size={16} />, label: t('navReport') },
              ]}
            />
          </nav>

          <div className="flex items-center gap-2">
            <label className="sr-only" htmlFor="lang">
              {t('language')}
            </label>
            <select
              id="lang"
              value={lang}
              onChange={(e) => setLang(e.target.value as Lang)}
              className="h-9 rounded-lg border border-line bg-surface px-2 text-sm font-medium text-ink hover:border-line-strong"
            >
              {LANGS.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.label}
                </option>
              ))}
            </select>
            <SwitchButton
              showLabel={false}
              onThemeChange={(th) => safeSet('theme', th)}
              className="border-line bg-surface text-ink hover:border-line-strong hover:bg-sunken dark:border-line dark:bg-surface dark:text-ink dark:hover:bg-sunken"
            />
          </div>
        </header>

        <main ref={main} className="flex-1 py-6 sm:py-8">
          {view === 'scheduler' && <SchedulerView season={season} setSeason={setSeason} onInspect={() => go('engine')} />}
          {view === 'engine' && <EngineView />}
          {view === 'summary' && <SummaryView season={season} setSeason={setSeason} />}
          {view === 'report' && <ReportView />}
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line py-5 text-xs text-ink-3">
          <span>{translate(lang, 'footerBrand')}</span>
          <span className="flex gap-4">
            <a className="hover:text-ink" href="/docs" target="_blank" rel="noreferrer">
              {t('apiDocs')}
            </a>
            <a className="hover:text-ink" href="/v1/config" target="_blank" rel="noreferrer">
              {t('config')}
            </a>
          </span>
        </footer>
      </div>
      </MotionConfig>
    </LangContext.Provider>
  )
}

function SwissMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--signal)" />
      <path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" fill="#fff" />
    </svg>
  )
}
