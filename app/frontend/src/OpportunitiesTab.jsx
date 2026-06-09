import { useEffect, useState } from 'react'
import { fetchOpportunities, fetchScenarios, fetchFullAnalysis } from './api.js'
import CityFilter from './CityFilter.jsx'

const eur = (n) => `€${Number(n).toLocaleString()}`

export default function OpportunitiesTab({ city, setCity }) {
  const [scenarios, setScenarios] = useState([])
  const [scenario, setScenario] = useState('abroad')
  const [marginalRate, setMarginalRate] = useState(0.47)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { fetchScenarios().then(setScenarios).catch((e) => setError(e.message)) }, [])
  useEffect(() => {
    setError(null)
    fetchOpportunities(city, scenario, marginalRate).then(setData).catch((e) => setError(e.message))
  }, [city, scenario, marginalRate])

  const active = scenarios.find((s) => s.id === scenario)

  return (
    <div>
      <div className="controls">
        <CityFilter city={city} setCity={setCity} />
        <div className="scenario-picker">
          <label>Tax scenario</label>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {scenarios.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          {scenario === 'israel_marginal_track' && (
            <span className="rate-input">
              <label>Marginal rate</label>
              <input type="number" min="10" max="50" step="1"
                value={Math.round(marginalRate * 100)}
                onChange={(e) => setMarginalRate(Number(e.target.value) / 100)} />%
            </span>
          )}
        </div>
      </div>
      {active && <p className="scenario-desc">{active.description}</p>}
      {error && <p className="error">{error}</p>}
      <div className="cards">
        {data?.results.map((r) => <ListingCard key={r.id} listing={r} marginalRate={marginalRate} />)}
      </div>
    </div>
  )
}

function ListingCard({ listing, marginalRate }) {
  const [compare, setCompare] = useState(null)
  const f = listing.financials

  const toggleCompare = async () => {
    if (compare) { setCompare(null); return }
    setCompare(await fetchFullAnalysis(listing.id, marginalRate))
  }

  return (
    <article className="card">
      <div className="card-head">
        <span className="city-pill">{listing.city}</span>
        <span className="price">{eur(listing.price_eur)}</span>
      </div>
      <h3>{listing.title}</h3>
      <p className="overview">{listing.overview}</p>
      <ul className="highlights">
        {listing.highlights.map((h) => <li key={h}>✓ {h}</li>)}
        {listing.risks.map((r) => <li key={r} className="risk">⚠ {r}</li>)}
      </ul>
      <div className="fin-grid">
        <Stat label="Gross yield" value={`${f.gross_yield_pct}%`} />
        <Stat label="Net pre-tax yield" value={`${f.net_pre_tax_yield_pct}%`} />
        <Stat label="After-tax yield" value={`${f.after_tax_yield_pct}%`} strong />
        <Stat label="Rent / year" value={eur(f.gross_rent)} />
        <Stat label="Local tax" value={eur(f.local_tax)} />
        <Stat label="Israeli tax" value={eur(f.israeli_tax)} />
        <Stat label="After-tax income" value={eur(f.after_tax_income)} strong />
        <Stat label="Effective tax" value={`${f.effective_tax_rate_pct}% of rent`} />
      </div>
      <details className="exit">
        <summary>Exit: capital gains on sale (assumes +{f.exit_cgt_estimate.assumed_gain_pct}% after {f.exit_cgt_estimate.assumed_holding_years} yrs)</summary>
        <p>Local CGT {eur(f.exit_cgt_estimate.local_cgt)} · Israeli CGT after credit {eur(f.exit_cgt_estimate.israeli_cgt_after_credit)} · <strong>total {eur(f.exit_cgt_estimate.total_cgt)}</strong></p>
        <p className="note">{f.exit_cgt_estimate.local_rule} {f.exit_cgt_estimate.israeli_rule}</p>
      </details>
      <details className="notes">
        <summary>Tax notes & assumptions</summary>
        <ul>{f.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </details>
      <button className="compare-btn" onClick={toggleCompare}>
        {compare ? 'Hide scenario comparison' : 'Compare all 4 tax scenarios'}
      </button>
      {compare && <ScenarioCompare data={compare} />}
    </article>
  )
}

function ScenarioCompare({ data }) {
  const rows = Object.values(data.scenarios)
  return (
    <table className="compare">
      <thead>
        <tr><th>Scenario</th><th>Total tax / yr</th><th>After-tax income</th><th>After-tax yield</th></tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.scenario.id}>
            <td>{r.scenario.label}</td>
            <td>{eur(r.total_tax)}</td>
            <td>{eur(r.after_tax_income)}</td>
            <td><strong>{r.after_tax_yield_pct}%</strong></td>
          </tr>
        ))}
      </tbody>
    </table>
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
