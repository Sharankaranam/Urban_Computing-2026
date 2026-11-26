import { useT } from './i18n'

/** Scenario keys understood by the backend's _load_day_df. */
export const SEASONS: { group: 'benchmark' | 'practice' | 'live'; id: string; label: string; date: string }[] = [
  { group: 'benchmark', id: 'winter', label: 'Winter', date: '15 Jan 2025' },
  { group: 'benchmark', id: 'spring', label: 'Spring', date: '12 Apr 2025' },
  { group: 'benchmark', id: 'summer', label: 'Summer PV', date: '21 Jun 2025' },
  { group: 'benchmark', id: 'autumn', label: 'Autumn', date: '15 Oct 2025' },
  { group: 'practice', id: 'autumn_dst', label: 'Autumn DST', date: '25 Oct 2026' },
  { group: 'practice', id: 'november_wind', label: 'November wind', date: '13 Nov 2026' },
  { group: 'practice', id: 'winter_cold_snap', label: 'Cold snap', date: '15 Dec 2026' },
  { group: 'practice', id: 'holiday_flat', label: 'Holiday, flat', date: '25 Dec 2026' },
  { group: 'practice', id: 'january_spike', label: 'January spike', date: '18 Jan 2027' },
  { group: 'practice', id: 'february_solar', label: 'February solar', date: '18 Feb 2027' },
  { group: 'live', id: 'live_ekz', label: 'EKZ API, today', date: '' },
]

export function SeasonSelect({ value, onChange, id = 'season' }: { value: string; onChange: (v: string) => void; id?: string }) {
  const { t } = useT()
  const groups = ['benchmark', 'practice', 'live'] as const
  return (
    <div>
      <label htmlFor={id} className="eyebrow">
        {t('scenario')}
      </label>
      <div className="relative mt-1.5">
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-full appearance-none rounded-xl border border-line bg-paper pl-3 pr-9 text-sm font-medium text-ink hover:border-line-strong focus:border-ink"
        >
          {groups.map((g) => (
            <optgroup key={g} label={t(g)}>
              {SEASONS.filter((s) => s.group === g).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                  {s.date ? ` · ${s.date}` : ''}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <svg className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-3" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
    </div>
  )
}
