/**
 * GIS and Map configuration & GeoJSON utilities for ClimateSense AI.
 * Handles parsing of GeoJSON FeatureCollection payloads from GET /api/v1/map/risk.
 */

import { DEV_DATA } from '../utils/constants';

export const MAP_CONFIG = {
  defaultCenter: [28.6139, 77.2090], // [lat, lng]
  defaultZoom: 10,
  crs: 'EPSG:4326',
  tileLayer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
};

/**
 * Format a GeoJSON FeatureCollection into standardized spatial risk zones.
 *
 * @param {Object} featureCollection - GeoJSON FeatureCollection from backend /api/v1/map/risk
 * @returns {Array} Array of formatted zone objects for the RiskMap visualizer
 */
export function parseGeoJSONFeaturesToZones(featureCollection) {
  if (!featureCollection || !Array.isArray(featureCollection.features) || featureCollection.features.length === 0) {
    return DEV_DATA.mapZones;
  }

  return featureCollection.features.map((feat, idx) => {
    const props = feat.properties || {};
    const coords = feat.geometry?.coordinates || [77.2090, 28.6139];

    // Format any extra GIS properties into a readable detail string
    const details = Object.entries(props)
      .filter(([k]) => !['name', 'dominant_hazard', 'overall_risk_level', 'overall_risk_score'].includes(k))
      .map(([k, v]) => `${k.replace('_', ' ')}: ${v}`)
      .join(' • ');

    const hazardName = props.dominant_hazard
      ? props.dominant_hazard.replace('_', ' ').toUpperCase()
      : 'GENERAL';

    return {
      id: feat.id || props.name || `zone-${idx + 1}`,
      name: props.name || `Monitoring Zone ${idx + 1}`,
      hazard: hazardName,
      risk_level: props.overall_risk_level || 'Moderate',
      risk_score: typeof props.overall_risk_score === 'number' ? props.overall_risk_score : 50,
      coordinates: coords, // [lon, lat] per RFC 7946 GeoJSON standard
      details: details || 'Spatial GIS observation station telemetry',
    };
  });
}
