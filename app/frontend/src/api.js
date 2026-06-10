const BASE = '/api'

async function get(path, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ).toString()
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}

export const fetchCities = () => get('/cities')
export const fetchScenarios = () => get('/scenarios')
export const fetchOpportunities = (city, scenario, marginalRate, yearsAbroad, financing = {}, source = 'all', sort = 'after_tax_yield') =>
  get('/opportunities', {
    city, scenario, marginal_rate: marginalRate, years_abroad: yearsAbroad, source, sort,
    ltv: financing.ltv, mortgage_rate: financing.rate, mortgage_term_years: financing.term,
  })
export const fetchFullAnalysis = (id, marginalRate, yearsAbroad, financing = {}) =>
  get(`/opportunities/${id}/full-analysis`, {
    marginal_rate: marginalRate, years_abroad: yearsAbroad,
    ltv: financing.ltv, mortgage_rate: financing.rate, mortgage_term_years: financing.term,
  })
export const fetchProfessionals = (city, type) =>
  get('/professionals', { city, type })
export const fetchVetting = () => get('/vetting')
export const fetchAreas = (city) => get('/areas', { city })
export const fetchHistory = (city, includeIrrelevant) =>
  get('/history', { city, include_irrelevant: includeIrrelevant })
export const setHistoryStatus = async (id, status, note = '') => {
  const qs = new URLSearchParams({ status, note }).toString()
  const res = await fetch(`${BASE}/history/${id}/status?${qs}`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}
export const fetchLiveStatus = () => get('/listings/live-status')
export const refreshListings = async (city) => {
  const qs = city ? `?city=${encodeURIComponent(city)}` : ''
  const res = await fetch(`${BASE}/listings/refresh${qs}`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}
