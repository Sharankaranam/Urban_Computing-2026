import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Gauge } from '@/components/watermelon/gauge'
import { ErrorNote, Panel, SectionHead, Skeleton } from '@/components/ui'
import { api, type Protoform, type SummaryResponse } from '@/lib/api'
import { useT } from '@/lib/i18n'
import { animate, stagger } from '@/lib/motion'
import { SeasonSelect } from '@/lib/seasons'
import { cn } from '@/lib/utils'

/** Render the backend's **bold** markers without innerHTML. */
function md(s: string): ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') ? (
      <strong key={i} className="font-semibold text-ink">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    ),
  )
}

const truthColor = (t: number) => (t >= 0.7 ? 'var(--s-ideal)' : t >= 0.4 ? 'var(--s-okay)' : 'var(--s-avoid)')

export function SummaryView({ season, setSeason }: { season: string; setSeason: (s: string) => void }) {
  const { t, lang } = useT()
  const [data, setData] = useState<SummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const [q, setQ] = useState('most')
  const [b, setB] = useState('all_day')
  const [s, setS] = useState('ideal')
  const [ev, setEv] = useState<(Protoform & { status: string }) | null>(null)
  const listRef = useRef<HTMLOListElement>(null)

  useEffect(() => {
    const ctl = new AbortController()
    setData(null)
    api
      .summary(season, lang, ctl.signal)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e) => e.name !== 'AbortError' && setError(t('error')))
    return () => ctl.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season, lang, nonce])

  useEffect(() => {
    const ctl = new AbortController()
    api
      .evaluate({ season, quantifier: q, qualifier: b, summarizer: s, lang }, ctl.signal)
      .then(setEv)
      .catch(() => {})
    return () => ctl.abort()
  }, [season, q, b, s, lang])

  // anime.js: narrative lines draw in one after another
  useEffect(() => {
    if (!data || !listRef.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const items = listRef.current.querySelectorAll('li')
    const a = animate(items, { opacity: [0.35, 1], translateX: [-6, 0], delay: stagger(70), duration: 480, ease: 'outExpo' })
    return () => {
      a.revert()
    }
  }, [data])

  return (
    <div className="space-y-6">
      <header className="grid gap-6 border-b border-line pb-6 lg:grid-cols-[1fr_320px] lg:items-end">
        <div>
          {data ? (
            <h1 className="max-w-[30ch] text-[clamp(1.6rem,3.2vw,2.4rem)] font-semibold leading-[1.15] tracking-[-0.025em] text-balance">
              {data.headline}
            </h1>
          ) : (
            <Skeleton className="mt-2 h-10 w-3/4" />
          )}
          <p className="mt-3 max-w-[62ch] text-base leading-relaxed text-ink-2">{t('summSubtitle')}</p>
        </div>
        <SeasonSelect id="season-summary" value={season} onChange={setSeason} />
      </header>

      {error && <ErrorNote message={error} onRetry={() => setNonce((n) => n + 1)} retry={t('retry')} />}

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel>
          <SectionHead title={t('narrative')} note={data ? <span className="num">{data.date}</span> : undefined} />
          {data ? (
            <ol ref={listRef} className="space-y-3">
              {data.narrative.map((n, i) => (
                <li key={i} className="max-w-[60ch] text-base leading-relaxed text-ink-2">
                  {md(n)}
                </li>
              ))}
            </ol>
          ) : (
            <div className="space-y-3">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-5" />
              ))}
            </div>
          )}
        </Panel>

        <Panel>
          <SectionHead title={t('builder')} note={t('summCalcSubtitle')} />
          <div className="grid gap-3 sm:grid-cols-3">
            <Pick label="Q" value={q} onChange={setQ} options={data?.quantifiers} />
            <Pick label="B" value={b} onChange={setB} options={data?.qualifiers} />
            <Pick label="S" value={s} onChange={setS} options={data?.summarizers} />
          </div>
          <div className="mt-5 flex items-center gap-5 rounded-xl bg-sunken p-4">
            <Gauge
              value={ev ? Math.round(ev.truth_degree * 100) : 0}
              size={104}
              strokeWidth={9}
              unit=""
              primary={ev ? truthColor(ev.truth_degree) : 'var(--line-strong)'}
              secondary="var(--line)"
              className={{ textClassName: 'fill-[var(--ink)] font-mono' }}
            />
            <div className="min-w-0">
              <div className="eyebrow">
                {t('truth')} T = μ<sub>Q</sub>(r){ev ? ` · ${ev.status}` : ''}
              </div>
              <p className="mt-1 text-[17px] font-medium leading-snug text-ink text-pretty">{ev?.statement ?? '…'}</p>
            </div>
          </div>
          <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
            <Metric k={t('ratio')} v={ev ? `${(ev.cardinality_ratio * 100).toFixed(1)}%` : '—'} />
            <Metric k={t('coverage')} v={ev ? `${(ev.coverage_degree * 100).toFixed(1)}%` : '—'} />
            <Metric k={t('structure')} v={ev ? (ev.protoform_type === 'type_2' ? 'Type II · Q B y are S' : 'Type I · Q y are S') : '—'} />
          </dl>
        </Panel>
      </div>

      <Panel className="p-0 sm:p-0">
        <div className="px-5 pt-5 sm:px-6">
          <SectionHead className="mb-0" title={t('protoforms')} note={t('summProtoSubtitle')} />
        </div>
        <ul className="mt-4 divide-y divide-line border-t border-line">
          {data
            ? data.top_protoforms.map((p, i) => (
                <li
                  key={i}
                  className="grid gap-3 px-5 py-4 sm:grid-cols-[1fr_220px] sm:items-center sm:px-6"
                >
                  <div className="min-w-0">
                    <p className="text-[15px] leading-snug text-ink">{p.statement}</p>
                    <p className="num mt-1 text-xs text-ink-3">
                      {p.quantifier} · {p.qualifier ?? '—'} · {p.summarizer}
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <Bar label={t('truth')} v={p.truth_degree} color={truthColor(p.truth_degree)} />
                    <Bar label={t('coverage')} v={p.coverage_degree} color="var(--price)" />
                  </div>
                </li>
              ))
            : [0, 1, 2].map((i) => (
                <li key={i} className="px-6 py-4">
                  <Skeleton className="h-10" />
                </li>
              ))}
        </ul>
      </Panel>

      <aside className="rounded-2xl border border-dashed border-line-strong p-5 text-sm leading-relaxed text-ink-2 sm:p-6">
        <h2 className="mb-2 text-[15px] font-semibold text-ink">Formalism</h2>
        <p>
          <b className="font-semibold text-ink">Type I</b> <code className="num">Q y are S</code>: r = (1/N) Σ μ<sub>S</sub>(xᵢ), T = μ<sub>Q</sub>(r).{' '}
          <b className="font-semibold text-ink">Type II</b> <code className="num">Q B y are S</code>: r = Σ min(μ<sub>B</sub>, μ<sub>S</sub>) / Σ μ<sub>B</sub>, T = μ<sub>Q</sub>(r).
          Quality is judged on truth (T₁), fuzziness (T₂), coverage (T₃) and an overall validity score.
        </p>
      </aside>
    </div>
  )
}

function Pick({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options?: { id: string; label: string }[]
}) {
  return (
    <label className="block min-w-0">
      <span className="num text-xs text-ink-3">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={!options}
        className="mt-1 h-10 w-full truncate rounded-xl border border-line bg-paper px-2.5 text-sm text-ink hover:border-line-strong focus:border-ink disabled:opacity-50"
      >
        {(options ?? [{ id: value, label: value }]).map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function Metric({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0">
      <dt className="eyebrow">{k}</dt>
      <dd className="num mt-1 truncate text-[13px] text-ink">{v}</dd>
    </div>
  )
}

function Bar({ label, v, color }: { label: string; v: number; color: string }) {
  return (
    <div className="grid grid-cols-[64px_1fr_36px] items-center gap-2 text-xs">
      <span className="text-ink-3">{label}</span>
      <span className="h-1.5 overflow-hidden rounded-full bg-sunken">
        <span className={cn('block h-full rounded-full')} style={{ width: `${v * 100}%`, background: color }} />
      </span>
      <span className="num text-right text-ink-2">{v.toFixed(2)}</span>
    </div>
  )
}
