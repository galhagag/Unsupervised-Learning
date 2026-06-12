import { useState } from 'react'
import { extractListing } from './api.js'

const eur = (n) => (n == null ? '—' : `€${Number(n).toLocaleString()}`)

// Paste a listing in any language; the backend extracts structured fields
// (Claude when an API key is configured, regex heuristics otherwise),
// shows a preview, and saves into the 'manual' source on confirm.
export default function AddListingPanel({ onSaved }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [city, setCity] = useState('Sofia')
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const run = async (save) => {
    setBusy(true); setError(null)
    try {
      const res = await extractListing(text, city, save)
      setPreview(res)
      if (save) {
        setText(''); setPreview(null); setOpen(false)
        onSaved?.(res.listing)
      }
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <section className="areas-panel">
      <button className="areas-toggle" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} Add a listing — paste from any portal (any language)
      </button>
      {open && (
        <div className="paste-panel">
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Paste the listing text here — Bulgarian, Greek, Italian, English or Hebrew. Include at least the price; size and rent help. With ANTHROPIC_API_KEY set the extraction uses Claude; otherwise a regex fallback finds price/size/rent." />
          <div className="controls">
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              {['Sofia', 'Sicily', 'Athens'].map((c) => <option key={c}>{c}</option>)}
            </select>
            <button className="compare-btn" disabled={busy || text.trim().length < 30}
              onClick={() => run(false)}>{busy ? 'Extracting…' : 'Extract preview'}</button>
            {preview && (
              <button className="compare-btn" disabled={busy} onClick={() => run(true)}>
                Save to my listings
              </button>
            )}
          </div>
          {error && <p className="error">{error}</p>}
          {preview && (
            <div className="card">
              <div className="card-head">
                <span className="city-pill">{preview.listing.city}</span>
                <span className={`grade grade-${preview.score.grade[0]}`}>
                  {preview.score.grade} · {preview.score.total}</span>
                <span className="price">{eur(preview.listing.price_eur)}
                  <span className="ppm2"> · {preview.listing.size_m2} m²</span></span>
              </div>
              <h3>{preview.listing.title}</h3>
              <p className="overview">{preview.listing.overview}</p>
              <p className="note">Rent {eur(preview.listing.expected_monthly_rent_eur)}/mo
                ({preview.listing.rent_basis}) · extraction: {preview.listing.extraction_method}</p>
              {!preview.llm_used && (
                <p className="warning">Heuristic extraction — set ANTHROPIC_API_KEY on the
                  backend for full multilingual extraction with Claude. Verify every field.</p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
