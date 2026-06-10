import { useEffect, useState } from 'react'
import { fetchPlaybook, fetchDeals, fetchDeal, updateDealStage } from './api.js'

const COUNTRIES = [['bulgaria', 'Bulgaria (Sofia)'], ['italy', 'Italy (Sicily)'], ['greece', 'Greece (Athens)']]
const eur = (n) => (n == null ? '' : `€${Number(n).toLocaleString()}`)

export default function AcquireTab() {
  const [country, setCountry] = useState('italy')
  const [pb, setPb] = useState(null)
  const [deals, setDeals] = useState([])
  const [openDeal, setOpenDeal] = useState(null)
  const [error, setError] = useState(null)

  const loadDeals = () => fetchDeals().then((d) => setDeals(d.results)).catch((e) => setError(e.message))
  useEffect(() => { fetchPlaybook(country).then(setPb).catch((e) => setError(e.message)) }, [country])
  useEffect(() => { loadDeals() }, [])

  const open = async (id) => setOpenDeal(await fetchDeal(id))
  const toggleStage = async (dealId, key, done) => {
    await updateDealStage(dealId, key, { done })
    setOpenDeal(await fetchDeal(dealId))
    loadDeals()
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}
      {deals.length > 0 && (
        <>
          <h2>Your deals</h2>
          <div className="cards">
            {deals.map((d) => {
              const done = Object.values(d.stages).filter((s) => s.done).length
              return (
                <article className="card" key={d.id}>
                  <div className="card-head">
                    <span className="city-pill">{d.city}</span>
                    <span className={`status-pill status-${d.status === 'completed' ? 'sold' : 'active'}`}>{d.status}</span>
                  </div>
                  <h3>{d.title}</h3>
                  <p className="note">{done} stage{done !== 1 ? 's' : ''} done · started {d.created_at?.slice(0, 10)}</p>
                  <button className="mini-btn" onClick={() => open(d.id)}>Open tracker</button>
                </article>
              )
            })}
          </div>
        </>
      )}

      {openDeal && <DealTracker deal={openDeal} onToggle={toggleStage} onClose={() => setOpenDeal(null)} />}

      <h2>Acquisition playbook</h2>
      <div className="city-filter">
        {COUNTRIES.map(([k, label]) => (
          <button key={k} className={country === k ? 'chip active' : 'chip'} onClick={() => setCountry(k)}>{label}</button>
        ))}
      </div>
      {pb && (
        <>
          <p className="note">{pb.disclaimer} · Typical timeline: {pb.typical_total_weeks} weeks.</p>
          <ol className="playbook">
            {pb.stages.map((s) => (
              <li key={s.key} className="card playbook-stage">
                <h3>{s.title}</h3>
                <p className="note">{s.owner} · ~{s.duration_weeks} wk · {s.typical_cost_eur}</p>
                <p className="overview">{s.detail}</p>
                {s.documents?.length > 0 && <p className="note"><strong>Documents:</strong> {s.documents.join(' · ')}</p>}
                {s.links?.map((l) => <a key={l.url} href={l.url} target="_blank" rel="noreferrer" className="note">{l.label} ↗ </a>)}
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  )
}

function DealTracker({ deal, onToggle, onClose }) {
  const stages = deal.playbook?.stages || []
  const totalCost = Object.values(deal.stages).reduce((a, s) => a + (s.cost_eur || 0), 0)
  return (
    <div className="card deal-tracker">
      <div className="card-head">
        <h3>{deal.title} — deal #{deal.id}</h3>
        <button className="mini-btn" onClick={onClose}>Close</button>
      </div>
      <p className="note">Recorded costs so far: {eur(totalCost) || '€0'}</p>
      <ol className="playbook">
        {stages.map((s) => {
          const st = deal.stages[s.key] || {}
          return (
            <li key={s.key} className={st.done ? 'stage-done' : ''}>
              <label className="toggle">
                <input type="checkbox" checked={!!st.done} onChange={(e) => onToggle(deal.id, s.key, e.target.checked)} />
                <strong>{s.title}</strong>
              </label>
              <span className="note"> — {s.owner}{st.cost_eur ? ` · ${eur(st.cost_eur)}` : ''}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
