const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

async function getJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`)
  }
  return response.json()
}

export const getHealth = () => getJson('/api/health')
export const getGIS = () => getJson('/api/gis')
export const getConditions = () => getJson('/api/conditions')
export const getPredictions = () => getJson('/api/predictions')
export const getRisks = () => getJson('/api/risks')
export const getAlerts = () => getJson('/api/alerts')
