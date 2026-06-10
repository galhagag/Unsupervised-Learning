import { useEffect, useState } from 'react'
import { fetchOpportunities, fetchScenarios, fetchFullAnalysis, fetchLiveStatus, refreshListings } from './api.js'
import CityFilter from './CityFilter.jsx'
import AreasPanel from './AreasPanel.jsx'

const eur = (n) => `€${Number(n).toLocaleString()}`

export default function OpportunitiesTab({ city, setCity }) {
  const [scenarios, setScenarios] = useState([])
  const [scenario, setScenario] = useState('abroad')
  const [marginalRate, setMarginalRate] = useState(0.47)
  const [yearsAbroad, setYearsAbroad] = useState(5)
  const [ltv, setLtv] = useState(0)
  const [rate, setRate] = useState(4.5)
  const [term, setTerm] = useState(20)
  const [source, setSource] = useState('all')
  const [liveStatus, setLiveStatus] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const financing = { ltv: ltv / 100, rate: rate / 100, term }

  useEffect(() => { fetchScenarios().then(setScenarios).catch((e) => setError(e.message)) }, [])
  useEffect(() => { fetchLiveStatus().then(setLiveStatus).catch(() => {}) }, [])
  useEffect(() => {
    setError(null)
    fetchOpportunities(city, scenario, marginalRate, yearsAbroad, financing, source)
      .then(setData).catch((e) => setError(e.message))
  }, [city, scenario, marginalRate, yearsAbroad, ltv, rate, term, source])

  const doRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const status = await refreshListings(city || undefined)
      setLiveStatus(status)
      const d = await fetchOpportunities(city, scenario, marginalRate, yearsAbroad, financing, source)
      setData(d)
    } catch (e) { setError(e.message) } finally { setRefreshing(false) }
  }

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
      <div className="controls financing-row">
        <span className="rate-input">
          <label>Mortgage LTV</label>
          <input type="number" min="0" max="80" step="5" value={ltv}
            onChange={(e) => setLtv(Number(e.target.value))} />%
          <span className="note"> (0 = cash purchase)</span>
        </span>
        {ltv > 0 && (
          <>
            <span className="rate-input">
              <label>Rate</label>
              <input type="number" min="0.5" max="15" step="0.1" value={rate}
                onChange={(e) => setRate(Number(e.target.value))} />%
            </span>
            <span className="rate-input">
              <label>Term</label>
              <input type="number" min="5" max="35" step="1" value={term}
                onChange={(e) => setTerm(Number(e.target.value))} /> yrs
            </span>
          </>
        )}
        <span className="city-filter">
          {['all', 'sample', 'researched', 'live'].map((s) => (
            <button key={s} className={source === s ? 'chip active' : 'chip'} onClick={() => setSource(s)}>
              {s === 'all' ? 'All data' : s === 'sample' ? 'Curated' : s === 'researched' ? 'Researched' : 'Live'}
            </button>
          ))}
        </span>
        <button className="compare-btn" onClick={doRefresh} disabled={refreshing}>
          {refreshing ? 'Fetching portals…' : `Refresh live listings${city ? ` (${city})` : ''}`}
        </button>
      </div>
      {liveStatus?.fetched_at && (
        <p className="note">Live data: {liveStatus.live_count} listings, fetched {liveStatus.fetched_at}.{' '}
          {Object.values(liveStatus.status || {}).join(' · ')}</p>
      )}
      {active && <p className="scenario-desc">{active.description}</p>}
      <AreasPanel city={city} />
      {scenario === 'returning_resident' && yearsAbroad < 6 && (
        <p className="warning">With {yearsAbroad} years abroad you are NOT eligible for the
          returning-resident exemption (needs 6+ consecutive years) — figures below fall back
          to the cheaper of the two regular Israeli tracks.</p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="cards">
        {data?.results.map((r) => (
          <ListingCard key={r.id} listing={r} marginalRate={marginalRate}
            yearsAbroad={yearsAbroad} financing={financing} />
        ))}
      </div>
    </div>
  )
}

function ListingCard({ listing, marginalRate, yearsAbroad, financing }) {
  const [compare, setCompare] = useState(null)
  const f = listing.financials
  const sl = listing.financials_short_let

  const toggleCompare = async () => {
    if (compare) { setCompare(null); return }
    setCompare(await fetchFullAnalysis(listing.id, marginalRate, yearsAbroad, financing))
  }

  return (
    <article className="card">
      <div className="card-head">
        <span className="city-pill">{listing.city}</span>
        {listing.score && (
          <span className={`grade grade-${listing.score.grade[0]}`}
            title={listing.score.rationale.join(' ')}>
            {listing.score.grade} · {listing.score.total}
          </span>
        )}
        <span className="price">{eur(listing.price_eur)}</span>
      </div>
      <h3>{listing.title}</h3>
      {listing.score?.area && (
        <p className="note">Area: {listing.score.area} — {listing.score.area_verdict}</p>
      )}
      {listing.listing_url && (
        <a href={listing.listing_url} target="_blank" rel="noreferrer" className="note">
          View original listing on {listing.data_source} ↗
        </a>
      )}
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
      {f.financing && (
        <div className="fin-grid">
          <Stat label="Equity in" value={eur(f.financing.equity_invested)} />
          <Stat label="Debt service / yr" value={eur(f.financing.annual_debt_service)} />
          <Stat label="Cash flow after debt" value={eur(f.financing.after_tax_cash_flow_after_debt)} strong />
          <Stat label="Cash-on-cash" value={`${f.financing.cash_on_cash_pct}%`} strong />
        </div>
      )}

      {listing.score && (
        <details className="notes">
          <summary>Score breakdown — {listing.score.grade} ({listing.score.total}/100)</summary>
          <ul>
            {Object.entries(listing.score.components).map(([k, v]) => (
              <li key={k}>{k}: {v}/100</li>
            ))}
            <li>risk adjustment: {listing.score.risk_adjustment}</li>
            {listing.score.rationale.map((r) => <li key={r} className="note">{r}</li>)}
          </ul>
        </details>
      )}
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
