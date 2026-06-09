import { useEffect, useState } from 'react'
import { fetchOpportunities, fetchScenarios, fetchFullAnalysis } from './api.js'
import CityFilter from './CityFilter.jsx'

const eur = (n) => `€${Number(n).toLocaleString()}`

export default function OpportunitiesTab({ city, setCity }) {
  const [scenarios, setScenarios] = useState([])
  const [scenario, setScenario] = useState('abroad')
  const [marginalRate, setMarginalRate] = useState(0.47)
  const [yearsAbroad, setYearsAbroad] = useState(5)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { fetchScenarios().then(setScenarios).catch((e) => setError(e.message)) }, [])
  useEffect(() => {
    setError(null)
    fetchOpportunities(city, scenario, marginalRate, yearsAbroad)
      .then(setData).catch((e) => setError(e.message))
  }, [city, scenario, marginalRate, yearsAbroad])

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
          {scenario === 'returning_resident' && (
            <span className="rate-input">
              <label>Years abroad</label>
              <input type="number" min="0" max="40" step="1"
                value={yearsAbroad}
                onChange={(e) => setYearsAbroad(Number(e.target.value))} />
            </span>
          )}
        </div>
      </div>
      {active && <p className="scenario-desc">{active.description}</p>}
      {scenario === 'returning_resident' && yearsAbroad < 6 && (
        <p className="warning">With {yearsAbroad} years abroad you are NOT eligible for the
          returning-resident exemption (needs 6+ consecutive years) — figures below fall back
          to the cheaper of the two regular Israeli tracks.</p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="cards">
        {data?.results.map((r) => (
          <ListingCard key={r.id} listing={r} marginalRate={marginalRate} yearsAbroad={yearsAbroad} />
        ))}
      </div>
    </div>
  )
}

function ListingCard({ listing, marginalRate, yearsAbroad }) {
  const [compare, setCompare] = useState(null)
  const f = listing.financials
  const sl = listing.financials_short_let

  const toggleCompare = async () => {
    if (compare) { setCompare(null); return }
    setCompare(await fetchFullAnalysis(listing.id, marginalRate, yearsAbroad))
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

      <table className="compare strategy-compare">
        <thead>
          <tr><th></th><th>Long let</th><th>Short let</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Gross income / yr</td>
            <td>{eur(f.gross_rent)}</td>
            <td>{sl ? eur(sl.gross_rent) : '—'}</td>
          </tr>
          <tr>
            <td>Total tax / yr</td>
            <td>{eur(f.total_tax)}</td>
            <td>{sl ? eur(sl.total_tax) : '—'}</td>
          </tr>
          <tr>
            <td>After-tax income</td>
            <td><strong>{eur(f.after_tax_income)}</strong></td>
            <td><strong>{sl ? eur(sl.after_tax_income) : '—'}</strong></td>
          </tr>
          <tr>
            <td>After-tax yield</td>
            <td><strong>{f.after_tax_yield_pct}%</strong></td>
            <td><strong>{sl ? `${sl.after_tax_yield_pct}%` : '—'}</strong></td>
          </tr>
        </tbody>
      </table>
      {!sl && listing.short_let?.note && (
        <p className="note">Short let unavailable: {listing.short_let.note}</p>
      )}

      <div className="fin-grid">
        <Stat label="Gross yield" value={`${f.gross_yield_pct}%`} />
        <Stat label="Net pre-tax yield" value={`${f.net_pre_tax_yield_pct}%`} />
        <Stat label="Local tax" value={eur(f.local_tax)} />
        <Stat label="Israeli tax" value={eur(f.israeli_tax)} />
      </div>

      <details className="exit">
        <summary>Exit: capital gains on sale (assumes +{f.exit_cgt_estimate.assumed_gain_pct}% after {f.exit_cgt_estimate.assumed_holding_years} yrs)</summary>
        <p>Local CGT {eur(f.exit_cgt_estimate.local_cgt)} · Israeli CGT after credit {eur(f.exit_cgt_estimate.israeli_cgt_after_credit)} · <strong>total {eur(f.exit_cgt_estimate.total_cgt)}</strong></p>
        <p className="note">{f.exit_cgt_estimate.local_rule} {f.exit_cgt_estimate.israeli_rule}</p>
      </details>
      <details className="notes">
        <summary>Tax notes & assumptions (long let)</summary>
        <ul>{f.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </details>
      {sl && (
        <details className="notes">
          <summary>Tax notes & assumptions (short let)</summary>
          <ul>{sl.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </details>
      )}
      <button className="compare-btn" onClick={toggleCompare}>
        {compare ? 'Hide scenario comparison' : 'Compare all 4 tax scenarios'}
      </button>
      {compare && <ScenarioCompare data={compare} />}
    </article>
  )
}

function ScenarioCompare({ data }) {
  const long = data.strategies.long_let
  const short = data.strategies.short_let
  const rows = Object.values(long)
  return (
    <table className="compare">
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Long let: tax / income / yield</th>
          {short && <th>Short let: tax / income / yield</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const s = short?.[r.scenario.id]
          return (
            <tr key={r.scenario.id}>
              <td>{r.scenario.label}</td>
              <td>{eur(r.total_tax)} / {eur(r.after_tax_income)} / <strong>{r.after_tax_yield_pct}%</strong></td>
              {short && (
                <td>{eur(s.total_tax)} / {eur(s.after_tax_income)} / <strong>{s.after_tax_yield_pct}%</strong></td>
              )}
            </tr>
          )
        })}
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
