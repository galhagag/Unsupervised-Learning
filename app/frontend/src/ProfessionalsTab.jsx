import { useEffect, useState } from 'react'
import { fetchProfessionals } from './api.js'
import CityFilter from './CityFilter.jsx'

export default function ProfessionalsTab({ city, setCity }) {
  const [type, setType] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setError(null)
    fetchProfessionals(city, type).then(setData).catch((e) => setError(e.message))
  }, [city, type])

  return (
    <div>
      <div className="controls">
        <CityFilter city={city} setCity={setCity} />
        <div className="city-filter">
          {['', 'realtor', 'lawyer'].map((t) => (
            <button key={t || 'all'} className={type === t ? 'chip active' : 'chip'} onClick={() => setType(t)}>
              {t === '' ? 'All roles' : t === 'realtor' ? 'Realtors' : 'Lawyers'}
            </button>
          ))}
        </div>
      </div>
      {data && (
        <>
          <div className="methodology">
            <strong>How these were selected:</strong> {data.methodology}
            <p className="note">{data.disclaimer}</p>
          </div>
          <div className="cards">
            {data.results.map((p) => (
              <article className="card pro-card" key={p.id}>
                <div className="card-head">
                  <span className="city-pill">{p.city}</span>
                  <span className={`role-pill ${p.type}`}>{p.type}</span>
                </div>
                <h3>{p.name}</h3>
                <p className="overview">{p.specialty}</p>
                <p><strong>Why listed:</strong> {p.why_recommended}</p>
                <p className="note">Languages: {p.languages.join(', ')}
                  {p.independent_of_agents && ' · Independent of selling agents'}</p>
                <a href={p.source_url} target="_blank" rel="noreferrer">Source / website ↗</a>
              </article>
            ))}
          </div>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
