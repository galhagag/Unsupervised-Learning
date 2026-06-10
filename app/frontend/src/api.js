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

// Phase 1: profile, projection, recommendation, compare, memo
export const fetchProfile = () => get('/profile')
export const saveProfile = async (patch) => {
  const res = await fetch(`${BASE}/profile`, {
    method: 'PUT', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}
export const fetchProjection = (id, stress = {}) => get(`/opportunities/${id}/projection`, stress)
export const fetchRecommendation = (city, source) => get('/recommendation', { city, source })
export const fetchMemo = (id) => get(`/opportunities/${id}/memo`)
export const postCompare = async (ids) => {
  const res = await fetch(`${BASE}/compare`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}

// Phase 2: playbooks & deals
export const fetchPlaybook = (country) => get(`/playbooks/${country}`)
export const fetchDeals = () => get('/deals')
export const fetchDeal = (id) => get(`/deals/${id}`)
const post = async (path, body) => {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}
const put = async (path, body) => {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT', headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}
export const createDeal = (listingId) => post('/deals', { listing_id: listingId })
export const updateDealStage = (id, stageKey, patch) => put(`/deals/${id}/stages/${stageKey}`, patch)

// Phase 3: properties, ledger, obligations, alerts
export const fetchProperties = () => get('/properties')
export const fetchProperty = (id) => get(`/properties/${id}`)
export const createProperty = (body) => post('/properties', body)
export const addLedgerEntry = (id, entry) => post(`/properties/${id}/ledger`, entry)
export const fetchObligations = (country) => get(`/obligations/${country}`)
export const fetchAlerts = () => get('/alerts')

// Phase 4: market intelligence
export const fetchFx = () => get('/fx')
export const fetchPriceChanges = () => get('/price-changes')
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
