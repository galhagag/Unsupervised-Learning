import { useEffect, useState } from 'react'
import { fetchProperties, fetchProperty, addLedgerEntry, fetchAlerts } from './api.js'

const eur = (n) => (n == null ? '—' : `€${Number(n).toLocaleString()}`)
const today = () => new Date().toISOString().slice(0, 10)

export default function PortfolioTab() {
  const [props, setProps] = useState([])
  const [alerts, setAlerts] = useState([])
  const [open, setOpen] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    fetchProperties().then((d) => setProps(d.results)).catch((e) => setError(e.message))
    fetchAlerts().then((d) => setAlerts(d.results)).catch(() => {})
  }
  useEffect(load, [])

  return (
    <div>
      {error && <p className="error">{error}</p>}
      {alerts.length > 0 && (
        <>
          <h2>Alerts & upcoming obligations</h2>
          <div className="alerts">
            {alerts.map((a, i) => (
              <div key={i} className={`alert alert-${a.severity}`}>
                <strong>{a.title}</strong> — {a.detail}
                {a.link && <> <a href={a.link} target="_blank" rel="noreferrer">portal ↗</a></>}
              </div>
            ))}
          </div>
        </>
      )}

      <h2>Owned properties</h2>
      {props.length === 0 && (
        <p className="empty-state">No properties yet. Complete a deal in the Acquire tab, or they
          appear here once you record a purchase. This is where the years of ownership live:
          rent/expense ledger, capex that builds your CGT cost basis, and the obligations calendar.</p>
      )}
      <div className="cards">
        {props.map((p) => (
          <article className="card" key={p.id}>
            <div className="card-head">
              <span className="city-pill">{p.city}</span>
              <span className="price">{eur(p.purchase_price_eur)}</span>
            </div>
            <h3>{p.title}</h3>
            <div className="fin-grid">
              <Stat label="Rent collected" value={eur(p.totals.rent_income)} />
              <Stat label="Expenses" value={eur(p.totals.operating_expense)} />
              <Stat label="Capex (CGT basis)" value={eur(p.totals.capex_basis)} strong />
              <Stat label="Net" value={eur(p.totals.net)} strong />
            </div>
            <button className="mini-btn" onClick={async () => setOpen(await fetchProperty(p.id))}>
              Open ledger & obligations
            </button>
          </article>
        ))}
      </div>

      {open && <PropertyDetail property={open} onAdd={async (entry) => {
        await addLedgerEntry(open.id, entry); setOpen(await fetchProperty(open.id)); load()
      }} onClose={() => setOpen(null)} />}
    </div>
  )
}

function PropertyDetail({ property, onAdd, onClose }) {
  const [form, setForm] = useState({ date: today(), kind: 'rent', description: '', amount_eur: '', capex: false })
  const submit = () => {
    if (!form.amount_eur) return
    let amt = Number(form.amount_eur)
    if (form.kind !== 'rent') amt = -Math.abs(amt)
    onAdd({ ...form, amount_eur: amt, capex: form.kind === 'capex' })
    setForm({ ...form, description: '', amount_eur: '' })
  }
  return (
    <div className="card deal-tracker">
      <div className="card-head">
        <h3>{property.title}</h3>
        <button className="mini-btn" onClick={onClose}>Close</button>
      </div>

      <h4>Add ledger entry</h4>
      <div className="ledger-form">
        <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
          <option value="rent">Rent (in)</option>
          <option value="expense">Expense (out)</option>
          <option value="capex">Capex — adds CGT basis (out)</option>
        </select>
        <input placeholder="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input type="number" placeholder="€ amount" value={form.amount_eur} onChange={(e) => setForm({ ...form, amount_eur: e.target.value })} />
        <button className="mini-btn" onClick={submit}>Add</button>
      </div>

      <table className="compare">
        <thead><tr><th>Date</th><th>Type</th><th>Description</th><th>€</th></tr></thead>
        <tbody>
          {property.ledger.map((e) => (
            <tr key={e.id}><td>{e.date}</td><td>{e.kind}{e.capex ? ' (capex)' : ''}</td>
              <td>{e.description}</td><td>{eur(e.amount_eur)}</td></tr>
          ))}
        </tbody>
      </table>

      <h4>Obligations calendar — {property.obligations?.label}</h4>
      <ul className="checklist">
        {property.obligations?.obligations?.map((o) => (
          <li key={o.key}><strong>{o.title}</strong> ({o.frequency}, due {o.due}) — {o.detail}
            {o.link && <> <a href={o.link} target="_blank" rel="noreferrer">portal ↗</a></>}</li>
        ))}
      </ul>
      <h4>Once you're an Israeli resident again</h4>
      <ul className="checklist">
        {property.israel_obligations?.obligations?.map((o) => (
          <li key={o.key}><strong>{o.title}</strong> (due {o.due}) — {o.detail}</li>
        ))}
      </ul>
    </div>
  )
}

function Stat({ label, value, strong }) {
  return (
    <div className={strong ? 'stat strong' : 'stat'}>
      <span className="stat-label">{label}</span><span className="stat-value">{value}</span>
    </div>
  )
}
