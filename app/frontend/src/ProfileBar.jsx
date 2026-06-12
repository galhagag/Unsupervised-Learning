import { useEffect, useState } from 'react'
import { fetchProfile, saveProfile, fetchFx } from './api.js'

// Compact, always-visible investor profile. Changes persist server-side and
// feed every projection and recommendation.
export default function ProfileBar({ onChange }) {
  const [p, setP] = useState(null)
  const [fx, setFx] = useState(null)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => { fetchProfile().then(setP); fetchFx().then(setFx).catch(() => {}) }, [])

  const field = (key, val, isPct) => {
    const next = { ...p, [key]: isPct ? val / 100 : val }
    setP(next)
  }
  const persist = async () => {
    setSaving(true)
    try { const saved = await saveProfile(p); setP(saved); onChange?.(saved) }
    finally { setSaving(false) }
  }
  if (!p) return null

  return (
    <section className="profile-bar">
      <button className="profile-summary" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} <strong>Your profile</strong> — {p.years_abroad_at_purchase}y abroad ·
        move back yr {p.move_back_year ?? '—'} · {Math.round(p.marginal_rate * 100)}% marginal ·
        €{(p.equity_budget_eur || 0).toLocaleString()} budget · {p.hold_years}y hold
        {fx && <span className="note"> · EUR/ILS {fx.eur_ils}</span>}
      </button>
      {open && (
        <div className="profile-fields">
          <Num label="Years abroad at purchase" v={p.years_abroad_at_purchase} on={(x) => field('years_abroad_at_purchase', x)} />
          <Num label="Move-back hold-year" v={p.move_back_year ?? ''} on={(x) => field('move_back_year', x)} />
          <Num label="Marginal rate %" v={Math.round(p.marginal_rate * 100)} on={(x) => field('marginal_rate', x, true)} />
          <Num label="Equity budget €" v={p.equity_budget_eur} step={5000} on={(x) => field('equity_budget_eur', x)} />
          <Num label="Hold years" v={p.hold_years} on={(x) => field('hold_years', x)} />
          <Num label="LTV %" v={Math.round((p.ltv || 0) * 100)} on={(x) => field('ltv', x, true)} />
          <Num label="Rent growth %/yr" v={p.rent_growth_pct} step={0.5} on={(x) => field('rent_growth_pct', x)} />
          <Num label="Appreciation %/yr" v={p.appreciation_pct} step={0.5} on={(x) => field('appreciation_pct', x)} />
          <Num label="Vacancy %" v={p.vacancy_pct} step={0.5} on={(x) => field('vacancy_pct', x)} />
          <Num label="Discount rate %" v={p.discount_rate_pct} step={0.5} on={(x) => field('discount_rate_pct', x)} />
          <label className="rate-input">Strategy
            <select value={p.rent_strategy} onChange={(e) => field('rent_strategy', e.target.value)}>
              <option value="long_let">Long let</option>
              <option value="short_let">Short let</option>
            </select>
          </label>
          <button className="compare-btn" onClick={persist} disabled={saving}>
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      )}
    </section>
  )
}

function Num({ label, v, on, step = 1 }) {
  return (
    <label className="rate-input">{label}
      <input type="number" step={step} value={v}
        onChange={(e) => on(e.target.value === '' ? null : Number(e.target.value))} />
    </label>
  )
}
