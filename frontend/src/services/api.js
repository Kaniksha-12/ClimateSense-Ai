import { requestJson } from './requestJson.js'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

const getJson = (path, options) => requestJson(`${API_BASE_URL}${path}`, options)

export const getHealth = (options) => getJson('/api/health', options)
export const getGIS = (options) => getJson('/api/gis', options)
export const getConditions = (options) => getJson('/api/conditions', options)
export const getPredictions = (options) => getJson('/api/predictions', options)
export const getRisks = (options) => getJson('/api/risks', options)
export const getAlerts = (options) => getJson('/api/alerts', options)
