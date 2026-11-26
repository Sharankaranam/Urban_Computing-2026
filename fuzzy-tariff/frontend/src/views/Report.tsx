import { useEffect, useState, type ReactNode } from 'react'
import type { EChartsOption } from 'echarts'
import { Chart } from '@/components/ui'
import { useT } from '@/lib/i18n'
import { useTokens } from '@/lib/theme'
import { cn } from '@/lib/utils'

function Formula({ children }: { children: ReactNode }) {
  return (
    <div className="num my-4 overflow-x-auto rounded-xl bg-sunken px-4 py-3 text-[13px] leading-7 text-ink ring-1 ring-line">{children}</div>
  )
}

function Section({ n, id, title, children }: { n: number; id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-28 border-t border-line pt-8 first:border-t-0 first:pt-0">
      <h2 className="text-[22px] font-semibold tracking-[-0.02em] text-ink">
        <span className="num mr-2 font-normal text-ink-3">{n}</span>
        {title}
      </h2>
      <div className="mt-3 space-y-3 text-base leading-[1.7] text-ink-2 [&_b]:font-semibold [&_b]:text-ink [&>ol]:max-w-[60ch] [&>p]:max-w-[60ch]">{children}</div>
    </section>
  )
}

export function ReportView() {
  const { t } = useT()
  const tk = useTokens()
  const [active, setActive] = useState('s1')
  const titles = [1, 2, 3, 4, 5, 6, 7].map((n) => t(`repSec${n}H2`))

  // Scroll-spy: highlight the section nearest the top of the viewport
  useEffect(() => {
    const els = [1, 2, 3, 4, 5, 6, 7].map((n) => document.getElementById(`s${n}`)).filter(Boolean) as HTMLElement[]
    const obs = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
        if (hit) setActive(hit.target.id)
      },
      { rootMargin: '-96px 0px -65% 0px' },
    )
    els.forEach((el) => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  const bench: EChartsOption = {
    animationDuration: 800,
    grid: { left: 8, right: 16, top: 30, bottom: 8, containLabel: true },
    legend: undefined,
    tooltip: {
      trigger: 'axis',
      backgroundColor: tk['--surface'],
      borderColor: tk['--line'],
      textStyle: { color: tk['--ink'], fontSize: 12 },
    },
    xAxis: { type: 'value', axisLabel: { color: tk['--ink-3'], fontFamily: 'IBM Plex Mono', fontSize: 10 }, splitLine: { lineStyle: { color: tk['--line'], type: 'dashed' } } },
    yAxis: {
      type: 'category',
      data: ['Label flips / day', '% of load in peak'],
      axisLabel: { color: tk['--ink-2'], fontSize: 12 },
      axisLine: { lineStyle: { color: tk['--line-strong'] } },
      axisTick: { show: false },
    },
    series: [
      {
        name: 'Fixed threshold',
        type: 'bar',
        data: [14, 31],
        barWidth: 14,
        itemStyle: { color: tk['--line-strong'], borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: tk['--ink-3'], fontFamily: 'IBM Plex Mono', fontSize: 11 },
      },
      {
        name: 'Two-stage FIS',
        type: 'bar',
        data: [4.9, 0],
        barWidth: 14,
        itemStyle: { color: tk['--s-ideal'], borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: tk['--ink'], fontFamily: 'IBM Plex Mono', fontSize: 11 },
      },
    ],
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[220px_minmax(0,720px)] lg:justify-center">
      <nav aria-label="Report sections" className="hidden lg:block">
        <ol className="sticky top-28 space-y-1 border-l border-line">
          {titles.map((title, i) => (
            <li key={i}>
              <a
                href={`#s${i + 1}`}
                onClick={(e) => {
                  e.preventDefault()
                  setActive(`s${i + 1}`)
                  document.getElementById(`s${i + 1}`)?.scrollIntoView({ behavior: 'smooth' })
                }}
                className={cn(
                  '-ml-px block border-l py-1 pl-3 text-[13px] leading-snug transition-colors',
                  active === `s${i + 1}` ? 'border-ink text-ink' : 'border-transparent text-ink-3 hover:text-ink',
                )}
              >
                {title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <article className="min-w-0 space-y-10">
        <header>
          <h1 className="text-[clamp(1.9rem,4vw,2.9rem)] font-semibold leading-[1.08] tracking-[-0.03em] text-balance">
            A two-stage fuzzy system for Swiss dynamic electricity tariffs
          </h1>
          <p className="mt-3 max-w-[60ch] text-[17px] leading-relaxed text-ink-2">
            Turning 96 volatile 15-minute prices a day into one decision households can act on: run it now, or wait.
          </p>
        </header>

        <Section n={1} id="s1" title={titles[0]}>
          <p>
            Under the revised Swiss Federal Electricity Act (StromVG, January 2026), smart meters bring dynamic retail tariffs with two
            parts: a 15-minute wholesale spot price (ENTSO-E) and a grid-use tariff that grows with transformer net load squared.
          </p>
          <p>
            <b>The problem.</b> Households face volatile prices and have no time to read market equations. Fixed thresholds break
            across seasons (€40/MWh is a summer peak but a winter bargain), so labels flicker and appliances switch on and off. Starting
            an EV, heat pump and dryer together can also trip a 16 A or 25 A breaker and add a local grid peak.
          </p>
          <p>
            <b>The proposal.</b> A hierarchical two-stage Mamdani fuzzy inference system plus a constraint-driven scheduler. Stage 1
            turns price percentile and grid strain into a suitability score S ∈ [0, 100]. Stage 2 models household urgency. The
            scheduler places heavy loads under the breaker limit with no market input from the user.
          </p>
        </Section>

        <Section n={2} id="s2" title={titles[1]}>
          <p>The system runs on 2025 Swiss market data at 15-minute resolution: 35,040 intervals a year, 96 a day.</p>
          <Formula>
            Spot price (ENTSO-E): day-ahead EUR/MWh → CHF Rp./kWh
            <br />
            Swissgrid substation net load: transformer active power, MW
            <br />
            Ancillary services (SDL): ≈ 0.27 Rp./kWh
            <br />
            T(t) = Energy(t) + GridTariff(net_load(t)²) + SDL
          </Formula>
        </Section>

        <Section n={3} id="s3" title={titles[2]}>
          <p>Each 24-hour cycle is normalised so the rules see relative and absolute context together.</p>
          <Formula>
            P(t) = 100 · (T(t) − min) / (max − min) ∈ [0, 100]
            <br />
            A(t) = T(t) in CHF/kWh ∈ [0, 1]
            <br />
            G(t) = clamp((NetLoad(t) − 100) / 100, 0, 1)
            <br />
            T(t) = sign(ΔP) · min(1, |ΔP| / 10 Rp./kWh) ∈ [−1, 1]
          </Formula>
        </Section>

        <Section n={4} id="s4" title={titles[3]}>
          <p>
            Inputs map onto linguistic terms with triangular and trapezoidal membership functions. The live definitions are in the
            Engine view and at <a className="underline decoration-line-strong underline-offset-2 hover:decoration-ink" href="/v1/config">/v1/config</a>.
          </p>
          <Formula>
            P: very_low, low, medium, high, very_high
            <br />
            A, G: low, medium, high · T: falling, stable, rising
            <br />
            S: avoid, wait, okay, good, ideal
          </Formula>
        </Section>

        <Section n={5} id="s5" title={titles[4]}>
          <p>
            Stage 1 uses <b>19 Mamdani rules</b> drawn from power-engineering heuristics. Cheap price on an empty grid is ideal; an
            overloaded grid overrides a cheap spot price to protect the transformer.
          </p>
          <p>The aggregated output is defuzzified to a crisp score with the centroid method:</p>
          <Formula>S = ∫ y · μ_B(y) dy ⁄ ∫ μ_B(y) dy</Formula>
        </Section>

        <Section n={6} id="s6" title={titles[5]}>
          <p>The application on this server is the working implementation of that architecture:</p>
          <ol className="list-decimal space-y-1 pl-5 marker:text-ink-3">
            <li>Ingest the day's 96 fifteen-minute intervals.</li>
            <li>Stage 1 FIS: compute S(t) ∈ [0, 100] per slot.</li>
            <li>Stage 2 advisor: fuzzify urgency U = duration / deadline, decide start now or wait.</li>
            <li>Scheduler: place each load in its best S(t) slots without exceeding the breaker limit.</li>
          </ol>
        </Section>

        <Section n={7} id="s7" title={titles[6]}>
          <p>On the full 2025 dataset the fuzzy system beats a fixed threshold on stability and peak avoidance while matching it on cost.</p>
          <div className="my-4 rounded-xl ring-1 ring-line">
            <div className="flex flex-wrap gap-4 px-4 pt-3 text-xs text-ink-3">
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-sm" style={{ background: 'var(--line-strong)' }} /> Fixed threshold
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-sm" style={{ background: 'var(--s-ideal)' }} /> Two-stage FIS
              </span>
            </div>
            <Chart option={bench} height={150} label="Benchmark: fixed threshold vs fuzzy system" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-line text-left">
                  <th className="eyebrow py-2 pr-3 font-semibold">Metric</th>
                  <th className="eyebrow px-3 py-2 font-semibold">Fixed</th>
                  <th className="eyebrow px-3 py-2 font-semibold">FIS</th>
                  <th className="eyebrow py-2 pl-3 font-semibold">Effect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {[
                  ['Label flips per day', '14.0', '4.9', '−65%'],
                  ['EV 22.2 kWh cost saving', 'CHF 3.82', 'CHF 3.87', '99.5% of oracle'],
                  ['Load in 17:30–20:30 peak', '31%', '0%', 'Peak avoided'],
                ].map((r) => (
                  <tr key={r[0]}>
                    <td className="py-2.5 pr-3 text-ink">{r[0]}</td>
                    <td className="num px-3 py-2.5 text-ink-3">{r[1]}</td>
                    <td className="num px-3 py-2.5 font-medium text-ink">{r[2]}</td>
                    <td className="py-2.5 pl-3 text-ink-2">{r[3]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            <b>Next.</b> Add a rooftop PV forecast PV(t) to the input vector, and drive appliances directly over OCPP and Matter.
          </p>
        </Section>
      </article>
    </div>
  )
}
