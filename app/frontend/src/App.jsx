import { useState } from 'react'
import OpportunitiesTab from './OpportunitiesTab.jsx'
import RecommendationTab from './RecommendationTab.jsx'
import AcquireTab from './AcquireTab.jsx'
import PortfolioTab from './PortfolioTab.jsx'
import ProfessionalsTab from './ProfessionalsTab.jsx'
import TaxGuideTab from './TaxGuideTab.jsx'
import HistoryTab from './HistoryTab.jsx'
import ProfileBar from './ProfileBar.jsx'

const TABS = [
  { id: 'recommendation', label: 'Best Pick' },
  { id: 'opportunities', label: 'Opportunities' },
  { id: 'acquire', label: 'Acquire' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'history', label: 'History' },
  { id: 'professionals', label: 'Realtors & Lawyers' },
  { id: 'tax', label: 'Israel Tax Guide' },
]

export default function App() {
  const [tab, setTab] = useState('recommendation')
  const [city, setCity] = useState('')
  const [profileVersion, setProfileVersion] = useState(0)

  return (
    <div className="app">
      <header>
        <h1>Relocation Investment Explorer</h1>
        <p className="subtitle">Sofia · Sicily · Athens — find the best investment, acquire it, and run it for years</p>
        <ProfileBar onChange={() => setProfileVersion((v) => v + 1)} />
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'recommendation' && <RecommendationTab city={city} setCity={setCity} profileVersion={profileVersion} />}
        {tab === 'opportunities' && <OpportunitiesTab city={city} setCity={setCity} profileVersion={profileVersion} />}
        {tab === 'acquire' && <AcquireTab />}
        {tab === 'portfolio' && <PortfolioTab />}
        {tab === 'history' && <HistoryTab city={city} setCity={setCity} />}
        {tab === 'professionals' && <ProfessionalsTab city={city} setCity={setCity} />}
        {tab === 'tax' && <TaxGuideTab />}
      </main>
      <footer>
        Sample data for decision support only — not tax, legal or investment advice.
      </footer>
    </div>
  )
}
