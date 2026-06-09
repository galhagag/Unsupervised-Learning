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
export const fetchOpportunities = (city, scenario, marginalRate) =>
  get('/opportunities', { city, scenario, marginal_rate: marginalRate })
export const fetchFullAnalysis = (id, marginalRate) =>
  get(`/opportunities/${id}/full-analysis`, { marginal_rate: marginalRate })
export const fetchProfessionals = (city, type) =>
  get('/professionals', { city, type })
