import { useEffect, useState } from 'react'
import { fetchOpportunities, fetchScenarios, fetchFullAnalysis, fetchLiveStatus, refreshListings, fetchProjection, fetchMemo, createDeal, fetchTiming, fetchMonteCarlo } from './api.js'
import CityFilter from './CityFilter.jsx'
import AreasPanel from './AreasPanel.jsx'
import AddListingPanel from './AddListingPanel.jsx'

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
  const [sort, setSort] = useState('after_tax_yield')
  const [liveStatus, setLiveStatus] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const financing = { ltv: ltv / 100, rate: rate / 100, term }

  useEffect(() => { fetchScenarios().then(setScenarios).catch((e) => setError(e.message)) }, [])
  useEffect(() => { fetchLiveStatus().then(setLiveStatus).catch(() => {}) }, [])
  useEffect(() => {
    // Debounce so typing in the numeric inputs doesn't fire a request per keystroke.
    setLoading(true)
    const t = setTimeout(() => {
      setError(null)
      fetchOpportunities(city, scenario, marginalRate, yearsAbroad, financing, source, sort)
        .then(setData).catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    }, 350)
    return () => clearTimeout(t)
  }, [city, scenario, marginalRate, yearsAbroad, ltv, rate, term, source, sort])

  const doRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const status = await refreshListings(city || undefined)
      setLiveStatus(status)
      const d = await fetchOpportunities(city, scenario, marginalRate, yearsAbroad, financing, source, sort)
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
          {['all', 'sample', 'researched', 'live', 'manual'].map((s) => (
            <button key={s} className={source === s ? 'chip active' : 'chip'} onClick={() => setSource(s)}>
              {{ all: 'All data', sample: 'Curated', researched: 'Researched', live: 'Live', manual: 'My listings' }[s]}
            </button>
          ))}
        </span>
        <span className="rate-input">
          <label>Sort by</label>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="after_tax_yield">After-tax yield</option>
            <option value="score">Score</option>
            <option value="gross_yield">Gross yield</option>
            <option value="price">Price (low to high)</option>
          </select>
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
      <AddListingPanel onSaved={() => { setSource('manual') }} />
      <AreasPanel city={city} />
      {scenario === 'returning_resident' && yearsAbroad < 6 && (
        <p className="warning">With {yearsAbroad} years abroad you are NOT eligible for the
          returning-resident exemption (needs 6+ consecutive years) — figures below fall back
          to the cheaper of the two regular Israeli tracks.</p>
      )}
      {error && <p className="error">{error}</p>}
      {data?.closed_excluded > 0 && (
        <p className="note">{data.closed_excluded} listing{data.closed_excluded > 1 ? 's' : ''} marked
          sold / no longer relevant hidden — manage in the History tab.</p>
      )}
      {loading && !data && <p className="note">Loading opportunities…</p>}
      {!loading && data?.results.length === 0 && (
        <div className="empty-state">
          {source === 'live'
            ? <>No live listings cached yet. Hit <strong>Refresh live listings</strong> — note the
                portals can only be reached from a machine with open internet (see the status line
                for per-portal results).</>
            : <>No listings match the current filters.</>}
        </div>
      )}
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
  const [proj, setProj] = useState(null)
  const [memo, setMemo] = useState(null)
  const [timingData, setTimingData] = useState(null)
  const [mc, setMc] = useState(null)
  const [dealMsg, setDealMsg] = useState(null)
  const f = listing.financials
  const sl = listing.financials_short_let

  const toggleCompare = async () => {
    if (compare) { setCompare(null); return }
    setCompare(await fetchFullAnalysis(listing.id, marginalRate, yearsAbroad, financing))
  }
  const toggleProj = async () => {
    if (proj) { setProj(null); return }
    setProj(await fetchProjection(listing.id))
  }
  const toggleMemo = async () => {
    if (memo) { setMemo(null); return }
    setMemo((await fetchMemo(listing.id)).markdown)
  }
  const startDeal = async () => {
    const d = await createDeal(listing.id)
    setDealMsg(`Deal #${d.id} started — open the Acquire tab to track it.`)
  }
  const toggleTiming = async () => {
    if (timingData) { setTimingData(null); return }
    setTimingData(await fetchTiming(listing.id))
  }
  const toggleMc = async () => {
    if (mc) { setMc(null); return }
    setMc(await fetchMonteCarlo(listing.id))
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
        <span className="price">{eur(listing.price_eur)}
          <span className="ppm2"> · {eur(Math.round(listing.price_eur / listing.size_m2))}/m²</span>
        </span>
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
      <div className="card-actions">
        <button className="compare-btn" onClick={toggleProj}>{proj ? 'Hide projection' : '10-yr projection'}</button>
        <button className="compare-btn" onClick={toggleCompare}>{compare ? 'Hide scenarios' : 'Tax scenarios'}</button>
        <button className="compare-btn" onClick={toggleTiming}>{timingData ? 'Hide timing' : 'Timing'}</button>
        <button className="compare-btn" onClick={toggleMc}>{mc ? 'Hide risk' : 'Risk'}</button>
        <button className="compare-btn" onClick={toggleMemo}>{memo ? 'Hide memo' : 'Memo'}</button>
        <button className="compare-btn" onClick={startDeal}>Start deal</button>
      </div>
      {dealMsg && <p className="note">{dealMsg}</p>}
      {proj && <ProjectionPanel proj={proj} />}
      {timingData && <TimingPanel data={timingData} />}
      {mc && <RiskPanel mc={mc} />}
      {compare && <ScenarioCompare data={compare} />}
      {memo && <pre className="memo">{memo}</pre>}
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

function ProjectionPanel({ proj }) {
  const m = proj.metrics
  return (
    <div className="projection">
      <div className="fin-grid">
        <Stat label="IRR" value={`${m.irr_pct ?? '—'}%`} strong />
        <Stat label="After-tax profit" value={eur(m.total_after_tax_profit)} strong />
        <Stat label="NPV" value={eur(m.npv)} />
        <Stat label="Equity multiple" value={m.equity_multiple ?? '—'} />
      </div>
      {proj.milestones.length > 0 && (
        <ul className="highlights">{proj.milestones.map((ms) => <li key={ms}>★ {ms}</li>)}</ul>
      )}
      <details>
        <summary>Year-by-year cash flow ({proj.years.length}y, exit included)</summary>
        <table className="compare">
          <thead><tr><th>Yr</th><th>Regime</th><th>Net rent</th><th>Tax</th><th>Free CF</th><th>Value</th></tr></thead>
          <tbody>
            {proj.years.map((y) => (
              <tr key={y.year}>
                <td>{y.year}</td>
                <td className="note">{y.scenario.replace('_', ' ')}</td>
                <td>{eur(y.gross_rent)}</td><td>{eur(y.tax)}</td>
                <td>{eur(y.free_cash_flow)}</td><td>{eur(y.property_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note">Exit yr {proj.exit.scenario.replace('_', ' ')}: sale {eur(proj.exit.sale_value)},
          local CGT {eur(proj.exit.local_cgt)}, Israeli CGT {eur(proj.exit.israeli_cgt)},
          net proceeds {eur(proj.exit.net_sale_proceeds)}. {proj.exit.note}</p>
      </details>
    </div>
  )
}

function TimingPanel({ data }) {
  const mb = data.move_back
  const ex = data.exit
  return (
    <div className="projection">
      <h4>Move-back timing</h4>
      {mb.six_year_cliff_note && <p className="warning">{mb.six_year_cliff_note}</p>}
      <p className="note">
        Current plan (return yr {mb.current_plan.move_back_year ?? 'never'},
        {' '}{mb.current_plan.exemption}): {eur(mb.current_plan.total_after_tax_profit)} profit.
        Best: return yr {mb.best_plan.move_back_year} ({mb.best_plan.exemption}) —
        {' '}{eur(mb.best_plan.total_after_tax_profit)}.
        {mb.improvement_eur > 0 && <strong> Delta {eur(mb.improvement_eur)} (~₪{Number(mb.improvement_ils).toLocaleString()}).</strong>}
      </p>
      <details>
        <summary>Profit by move-back year</summary>
        <table className="compare">
          <thead><tr><th>Return yr</th><th>Yrs abroad</th><th>Exemption</th><th>IRR</th><th>Profit</th></tr></thead>
          <tbody>
            {mb.rows.map((r) => (
              <tr key={String(r.move_back_year)}>
                <td>{r.move_back_year ?? 'never'}</td><td>{r.years_abroad_at_return ?? '—'}</td>
                <td>{r.exemption}</td><td>{r.irr_pct}%</td><td>{eur(r.total_after_tax_profit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      <h4>Exit timing</h4>
      <p className="note">Best IRR selling in <strong>year {ex.best_irr.sale_year}</strong> ({ex.best_irr.irr_pct}%);
        max profit in year {ex.best_profit.sale_year} ({eur(ex.best_profit.total_after_tax_profit)}).
        {ex.notes.map((n) => ` ${n}`)}</p>
      <details>
        <summary>IRR by sale year</summary>
        <table className="compare">
          <thead><tr><th>Sale yr</th><th>IRR</th><th>Profit</th><th>Local CGT</th><th>IL CGT</th></tr></thead>
          <tbody>
            {ex.rows.map((r) => (
              <tr key={r.sale_year}>
                <td>{r.sale_year}</td><td>{r.irr_pct}%</td>
                <td>{eur(r.total_after_tax_profit)}</td>
                <td>{eur(r.local_cgt)}</td><td>{eur(r.israeli_cgt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

function RiskPanel({ mc }) {
  return (
    <div className="projection">
      <h4>Monte Carlo risk bands ({mc.draws} draws)</h4>
      <div className="fin-grid">
        <Stat label="IRR P10 (bad case)" value={`${mc.irr.p10}%`} />
        <Stat label="IRR P50" value={`${mc.irr.p50}%`} strong />
        <Stat label="IRR P90 (good case)" value={`${mc.irr.p90}%`} />
        <Stat label="P(negative cash flow)" value={`${mc.prob_negative_cash_flow_pct}%`} />
        <Stat label="Profit P10" value={eur(mc.profit.p10)} />
        <Stat label="Profit P50" value={eur(mc.profit.p50)} strong />
        <Stat label="Profit P90" value={eur(mc.profit.p90)} />
        <Stat label="P(overall loss)" value={`${mc.prob_loss_pct}%`} />
      </div>
      <p className="note">Perturbed per draw: {mc.assumption_ranges}.</p>
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
