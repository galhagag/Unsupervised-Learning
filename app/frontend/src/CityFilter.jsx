import { useEffect, useState } from 'react'
import { fetchCities } from './api.js'

export default function CityFilter({ city, setCity }) {
  const [cities, setCities] = useState([])
  useEffect(() => { fetchCities().then(setCities).catch(() => setCities(['Sofia', 'Sicily', 'Athens'])) }, [])

  return (
    <div className="city-filter">
      <button className={!city ? 'chip active' : 'chip'} onClick={() => setCity('')}>All cities</button>
      {cities.map((c) => (
        <button key={c} className={city === c ? 'chip active' : 'chip'} onClick={() => setCity(c)}>{c}</button>
      ))}
    </div>
  )
}
