import { useState } from 'react'
import OpportunitiesTab from './OpportunitiesTab.jsx'
import ProfessionalsTab from './ProfessionalsTab.jsx'
import TaxGuideTab from './TaxGuideTab.jsx'

const TABS = [
  { id: 'opportunities', label: 'Opportunities' },
  { id: 'professionals', label: 'Realtors & Lawyers' },
  { id: 'tax', label: 'Israel Tax Guide' },
]

export default function App() {
  const [tab, setTab] = useState('opportunities')
  const [city, setCity] = useState('')

  return (
    <div className="app">
      <header>
        <h1>Relocation Investment Explorer</h1>
        <p className="subtitle">Sofia · Sicily · Athens — opportunities, financials & the move-back-to-Israel tax picture</p>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'opportunities' && <OpportunitiesTab city={city} setCity={setCity} />}
        {tab === 'professionals' && <ProfessionalsTab city={city} setCity={setCity} />}
        {tab === 'tax' && <TaxGuideTab />}
      </main>
      <footer>
        Sample data for decision support only — not tax, legal or investment advice.
      </footer>
    </div>
  )
}
