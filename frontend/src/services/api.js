/**
 * API Service layer for ClimateSense AI backend communication.
 * Connects to FastAPI backend (/api/v1) with seamless fallback to DEV_DATA fixtures
 * so the frontend dashboard renders immediately even when the backend is offline.
 */

import { DEV_DATA } from '../utils/constants';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * Generic fetch wrapper with timeout and automatic demo data fallback.
 */
async function fetchWithFallback(endpoint, fallbackData) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${API_V1}${endpoint}`, {
      signal: controller.signal,
      headers: { 'Accept': 'application/json' },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      console.warn(`[API] Endpoint ${endpoint} returned status ${res.status}. Falling back to demo data.`);
      return { data: fallbackData, isLive: false, error: `HTTP ${res.status}` };
    }

    const json = await res.json();
    return { data: json, isLive: true, error: null };
  } catch (err) {
    // Backend offline or network timeout -> return demo data safely
    return { data: fallbackData, isLive: false, error: err.message };
  }
}

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_V1}/health`, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      const data = await res.json();
      return { status: 'online', data };
    }
    return { status: 'degraded' };
  } catch {
    return { status: 'offline' };
  }
}

export async function getWeather(location = null) {
  const query = location ? `?location=${encodeURIComponent(location)}` : '';
  return fetchWithFallback(`/weather${query}`, DEV_DATA.weather);
}

export async function getAQI(location = null) {
  const query = location ? `?location=${encodeURIComponent(location)}` : '';
  return fetchWithFallback(`/aqi${query}`, DEV_DATA.aqi);
}

export async function getPredictions(location = null) {
  const query = location ? `?location=${encodeURIComponent(location)}` : '';
  return fetchWithFallback(`/predictions${query}`, DEV_DATA.predictions);
}

export async function getPredictionByHazard(hazard, location = null) {
  const query = location ? `?location=${encodeURIComponent(location)}` : '';
  const fallback = DEV_DATA.predictions.find(
    (p) => p.hazard.toLowerCase() === hazard.toLowerCase()
  ) || DEV_DATA.predictions[0];
  return fetchWithFallback(`/predictions/${hazard}${query}`, fallback);
}

export async function getRisk(location = null) {
  const query = location ? `?location=${encodeURIComponent(location)}` : '';
  return fetchWithFallback(`/risk${query}`, DEV_DATA.overallRisk);
}

export async function getRiskMap() {
  return fetchWithFallback('/map/risk', {
    type: 'FeatureCollection',
    features: DEV_DATA.mapZones.map((zone) => ({
      type: 'Feature',
      id: zone.id,
      geometry: { type: 'Point', coordinates: zone.coordinates },
      properties: {
        name: zone.name,
        dominant_hazard: zone.hazard.toLowerCase(),
        overall_risk_level: zone.risk_level,
        overall_risk_score: zone.risk_score,
        details: zone.details,
      },
    })),
  });
}

export async function getAlerts() {
  return fetchWithFallback('/alerts', DEV_DATA.alerts);
}
