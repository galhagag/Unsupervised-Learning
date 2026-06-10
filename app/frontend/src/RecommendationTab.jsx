import { useEffect, useState } from 'react'
import { fetchRecommendation } from './api.js'
import CityFilter from './CityFilter.jsx'

const eur = (n) => (n == null ? '—' : `€${Number(n).toLocaleString()}`)

export default function RecommendationTab({ city, setCity, profileVersion }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true); setError(null)
    fetchRecommendation(city).then(setData).catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [city, profileVersion])

  if (loading) return <p className="note">Computing the best fit for your profile…</p>
  if (error) return <p className="error">{error}</p>
  if (!data?.top_pick) return <p className="note">No listings to evaluate.</p>

  return (
    <div>
      <CityFilter city={city} setCity={setCity} />
      <div className="top-pick card">
        <span className="grade grade-A">TOP PICK · fit {data.top_pick.fit_score}/100</span>
        <h2>{data.top_pick.title}</h2>
        <p className="overview">{data.rationale}</p>
        <div className="fin-grid">
          <Stat label="Projected IRR" value={`${data.top_pick.irr_pct ?? '—'}%`} strong />
          <Stat label="After-tax profit" value={eur(data.top_pick.total_after_tax_profit)} strong />
          <Stat label="NPV" value={eur(data.top_pick.npv)} />
          <Stat label="Equity in" value={eur(data.top_pick.equity_invested)} />
          <Stat label="Asset grade" value={data.top_pick.asset_grade} />
          <Stat label="In budget?" value={data.top_pick.affordable ? 'Yes' : 'Over budget'} />
        </div>
      </div>

      <h2>Best in each city</h2>
      <div className="cards">
        {Object.values(data.per_city).map((r) => (
          <article className="card" key={r.id}>
            <div className="card-head">
              <span className="city-pill">{r.city}</span>
              <span className={`grade grade-${r.asset_grade[0]}`}>fit {r.fit_score}</span>
            </div>
            <h3>{r.title}</h3>
            <p className="note">{r.area} {r.area_verdict ? `— ${r.area_verdict}` : ''}</p>
            <div className="fin-grid">
              <Stat label="IRR" value={`${r.irr_pct ?? '—'}%`} />
              <Stat label="Profit" value={eur(r.total_after_tax_profit)} />
              <Stat label="Equity" value={eur(r.equity_invested)} />
              <Stat label="Budget" value={r.affordable ? '✓' : '✗ over'} />
            </div>
          </article>
        ))}
      </div>

      <h2>Full ranking ({data.ranked.length})</h2>
      <table className="compare">
        <thead><tr><th>#</th><th>Listing</th><th>City</th><th>Fit</th><th>IRR</th><th>Profit</th><th>Equity</th><th>Budget</th></tr></thead>
        <tbody>
          {data.ranked.map((r, i) => (
            <tr key={r.id} className={r.affordable ? '' : 'row-irrelevant'}>
              <td>{i + 1}</td><td>{r.title}</td><td>{r.city}</td>
              <td><strong>{r.fit_score}</strong></td><td>{r.irr_pct ?? '—'}%</td>
              <td>{eur(r.total_after_tax_profit)}</td><td>{eur(r.equity_invested)}</td>
              <td>{r.affordable ? '✓' : '✗'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Stat({ label, value, strong }) {
  return (
    <div className={strong ? 'stat strong' : 'stat'}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  )
}
