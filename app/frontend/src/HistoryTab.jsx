import { useEffect, useState } from 'react'
import { fetchHistory, setHistoryStatus } from './api.js'
import CityFilter from './CityFilter.jsx'

const eur = (n) => `€${Number(n).toLocaleString()}`
const STATUS_LABEL = {
  active: 'Active', stale: 'Stale — not re-confirmed',
  delisted: 'Delisted', sold: 'Sold', irrelevant: 'No longer relevant',
}

export default function HistoryTab({ city, setCity }) {
  const [showIrrelevant, setShowIrrelevant] = useState(true)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    fetchHistory(city, showIrrelevant).then(setData).catch((e) => setError(e.message))
  }
  useEffect(load, [city, showIrrelevant])

  const mark = async (id, status) => {
    try { await setHistoryStatus(id, status); load() } catch (e) { setError(e.message) }
  }

  return (
    <div>
      <div className="controls">
        <CityFilter city={city} setCity={setCity} />
        <label className="toggle">
          <input type="checkbox" checked={showIrrelevant}
            onChange={(e) => setShowIrrelevant(e.target.checked)} />
          Show sold / delisted / irrelevant
        </label>
      </div>
      {data && (
        <p className="note">
          {data.count} listings tracked{showIrrelevant ? ` (${data.irrelevant_count} no longer relevant)` : ''}.
          Every listing the app has seen is recorded here with its score snapshot;
          live listings that vanish from a portal refresh are auto-marked delisted,
          and anything unconfirmed for 30+ days goes stale.
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {data && (
        <table className="compare history-table">
          <thead>
            <tr>
              <th>Listing</th><th>City</th><th>Price</th><th>Score</th>
              <th>Seen</th><th>Status</th><th>Highlights</th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <tr key={r.id} className={r.relevant ? '' : 'row-irrelevant'}>
                <td>
                  {r.listing_url
                    ? <a href={r.listing_url} target="_blank" rel="noreferrer">{r.title}</a>
                    : r.title}
                  <br /><span className="note">{r.data_source}</span>
                </td>
                <td>{r.city}</td>
                <td>{eur(r.price_eur)}</td>
                <td>{r.score_grade
                  ? <span className={`grade grade-${r.score_grade[0]}`}>{r.score_grade} {r.score_total}</span>
                  : '—'}</td>
                <td className="note">{r.first_seen}{r.last_seen !== r.first_seen ? ` → ${r.last_seen}` : ''}</td>
                <td>
                  <span className={`status-pill status-${r.status}`}>{STATUS_LABEL[r.status] || r.status}</span>
                  {r.status_note && <><br /><span className="note">{r.status_note}</span></>}
                </td>
                <td className="note">{r.highlights.join(' · ')}</td>
                <td>
                  {r.relevant ? (
                    <>
                      <button className="mini-btn" onClick={() => mark(r.id, 'sold')}>Sold</button>
                      <button className="mini-btn" onClick={() => mark(r.id, 'irrelevant')}>Not relevant</button>
                    </>
                  ) : (
                    <button className="mini-btn" onClick={() => mark(r.id, 'active')}>Restore</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
