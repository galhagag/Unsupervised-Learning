import { useEffect, useState } from 'react'
import { fetchAreas } from './api.js'

export default function AreasPanel({ city }) {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(true)

  useEffect(() => { fetchAreas(city).then(setData).catch(() => {}) }, [city])
  if (!data?.results.length) return null

  return (
    <section className="areas-panel">
      <button className="areas-toggle" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} Recommended areas{city ? ` — ${city}` : ''} (as of {data.as_of})
      </button>
      {open && (
        <>
          <div className="cards areas-cards">
            {data.results.map((a) => (
              <article className="card area-card" key={`${a.city}-${a.name}`}>
                <div className="card-head">
                  <span className="city-pill">{a.city}</span>
                  <span className="verdict-pill">{a.verdict}</span>
                </div>
                <h3>{a.name}</h3>
                <p className="overview">{a.summary}</p>
                <div className="fin-grid area-grid">
                  <ScoreBar label="Location" value={a.scores.location} />
                  <ScoreBar label="Growth" value={a.scores.growth} />
                  <ScoreBar label="Liquidity" value={a.scores.liquidity} />
                  <div className="stat">
                    <span className="stat-label">Benchmark</span>
                    <span className="stat-value">€{a.price_eur_m2.toLocaleString()}/m²</span>
                  </div>
                </div>
                <ul className="highlights">
                  {a.watch_outs.map((w) => <li key={w} className="risk">⚠ {w}</li>)}
                </ul>
              </article>
            ))}
          </div>
          <p className="note">{data.note}</p>
        </>
      )}
    </section>
  )
}

function ScoreBar({ label, value }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}/10</span>
      <div className="bar"><div className="bar-fill" style={{ width: `${value * 10}%` }} /></div>
    </div>
  )
}
