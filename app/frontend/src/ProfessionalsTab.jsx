import { useEffect, useState } from 'react'
import { fetchProfessionals, fetchVetting } from './api.js'
import CityFilter from './CityFilter.jsx'

const CITY_TO_COUNTRY = { Sofia: 'Bulgaria', Sicily: 'Italy', Athens: 'Greece' }

export default function ProfessionalsTab({ city, setCity }) {
  const [type, setType] = useState('')
  const [data, setData] = useState(null)
  const [vetting, setVetting] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { fetchVetting().then(setVetting).catch((e) => setError(e.message)) }, [])
  useEffect(() => {
    setError(null)
    fetchProfessionals(city, type).then(setData).catch((e) => setError(e.message))
  }, [city, type])

  const countries = vetting?.countries.filter(
    (c) => !city || c.country.startsWith(CITY_TO_COUNTRY[city] || ''),
  )

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

      {vetting && (
        <>
          <div className="methodology">
            <strong>How to get an unbiased professional:</strong> {vetting.intro}
          </div>

          <h2>1 · Vetting checklist (applies everywhere)</h2>
          <ul className="checklist">
            {vetting.universal_checklist.map((item) => <li key={item}>{item}</li>)}
          </ul>

          <h2>2 · Verify credentials & local pitfalls</h2>
          <div className="cards">
            {countries.map((c) => (
              <article className="card" key={c.country}>
                <h3>{c.country}</h3>
                <p><strong>Lawyer registry:</strong>{' '}
                  <a href={c.lawyer_registry.url} target="_blank" rel="noreferrer">{c.lawyer_registry.name} ↗</a>
                  <br /><span className="note">{c.lawyer_registry.how}</span></p>
                <p><strong>Realtor registry:</strong>{' '}
                  <a href={c.realtor_registry.url} target="_blank" rel="noreferrer">{c.realtor_registry.name} ↗</a>
                  <br /><span className="note">{c.realtor_registry.how}</span></p>
                <p><strong>Local red flags:</strong></p>
                <ul className="highlights">
                  {c.local_red_flags.map((r) => <li key={r} className="risk">⚠ {r}</li>)}
                </ul>
              </article>
            ))}
          </div>
          <p className="note">
            EU-wide cross-check:{' '}
            <a href={vetting.eu_wide_lawyer_check.url} target="_blank" rel="noreferrer">
              {vetting.eu_wide_lawyer_check.name} ↗</a> — {vetting.eu_wide_lawyer_check.note}
          </p>

          <h2>3 · Community sources (real buyers, not marketing)</h2>
          <div className="cards">
            {countries.map((c) => (
              <article className="card" key={`${c.country}-community`}>
                <h3>{c.country}</h3>
                <ul className="community">
                  {c.community_sources.map((s) => (
                    <li key={s.name}>
                      <a href={s.url} target="_blank" rel="noreferrer">{s.name} ↗</a>
                      <br /><span className="note">{s.note}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </>
      )}

      {data && (
        <>
          <h2>4 · Starting-point shortlist</h2>
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
