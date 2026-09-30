import React, { useEffect, useState } from 'react';
import { DEV_DATA, RISK_LEVELS } from '../utils/constants';

export default function RiskMap({ mapZones = DEV_DATA.mapZones, isLive = false }) {
  const safeZones = Array.isArray(mapZones) && mapZones.length > 0 ? mapZones : DEV_DATA.mapZones;
  const [selectedZone, setSelectedZone] = useState(safeZones[0] || null);

  useEffect(() => {
    if (safeZones && safeZones.length > 0) {
      setSelectedZone((prev) => {
        const stillExists = safeZones.find((z) => z.id === prev?.id);
        return stillExists || safeZones[0];
      });
    }
  }, [safeZones]);

  const getRiskColor = (level) => {
    const key = (level || 'LOW').toUpperCase();
    return RISK_LEVELS[key]?.color || '#10b981';
  };

  return (
    <div className="risk-map-container" id="risk-map">
      <div className="risk-map-toolbar">
        <div className="map-toolbar-left">
          <span className="map-icon">🗺️</span>
          <div>
            <h3 className="map-title">Climate Risk Map</h3>
            <span className="map-crs-label">
              CRS: EPSG:4326 • {isLive ? 'Live GeoJSON FeatureCollection' : 'GeoJSON Integration Layer'}
            </span>
          </div>
        </div>

        <div className="map-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#10b981' }}></span>
            <span>🟢 Low Risk</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }}></span>
            <span>🟡 Moderate Risk</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#f97316' }}></span>
            <span>🟠 High Risk</span>
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#ef4444' }}></span>
            <span>🔴 Critical Risk</span>
          </span>
        </div>
      </div>

      <div className="map-canvas-area">
        <div className="map-grid-overlay">
          <div className="map-reticle-center"></div>
          <div className="map-coords-badge">LAT 28.6139° N • LON 77.2090° E</div>
          <div className="map-integration-banner">
            <span>
              {isLive
                ? 'Connected to GET /api/v1/map/risk (Live Spatial Layer)'
                : 'Ready for Member 3 GIS & QGIS GeoJSON Ingestion (/api/v1/map/risk)'}
            </span>
          </div>

          {/* Spatial Risk Hotspot Nodes */}
          <div className="spatial-nodes-layer">
            {safeZones.map((zone, idx) => {
              const isSelected = selectedZone?.id === zone.id;
              const color = getRiskColor(zone.risk_level);
              return (
                <button
                  type="button"
                  key={zone.id || idx}
                  onClick={() => setSelectedZone(zone)}
                  className={`spatial-node node-pos-${(idx % 3) + 1} ${isSelected ? 'active' : ''}`}
                  style={{
                    borderColor: color,
                    backgroundColor: isSelected ? 'rgba(30, 41, 59, 0.95)' : 'rgba(15, 23, 42, 0.85)',
                  }}
                  title={zone.name}
                >
                  <span className="node-pulse" style={{ backgroundColor: color }}></span>
                  <span className="node-tag" style={{ color: color }}>
                    {zone.hazard} ({zone.risk_score}%)
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Zone Inspector Panel */}
        {selectedZone && (
          <div className="map-zone-inspector">
            <div className="zone-inspector-header">
              <span className="zone-title">{selectedZone.name}</span>
              <span
                className="zone-level-pill"
                style={{
                  color: getRiskColor(selectedZone.risk_level),
                  borderColor: `${getRiskColor(selectedZone.risk_level)}40`,
                  backgroundColor: `${getRiskColor(selectedZone.risk_level)}15`,
                }}
              >
                {selectedZone.risk_level} Risk
              </span>
            </div>
            <div className="zone-meta-grid">
              <div className="zone-meta-item">
                <span className="meta-label">Coordinates:</span>
                <span className="meta-val">
                  {Array.isArray(selectedZone.coordinates)
                    ? `${selectedZone.coordinates[1]}°N, ${selectedZone.coordinates[0]}°E`
                    : 'N/A'}
                </span>
              </div>
              <div className="zone-meta-item">
                <span className="meta-label">Dominant Hazard:</span>
                <span className="meta-val">{selectedZone.hazard}</span>
              </div>
              <div className="zone-meta-item">
                <span className="meta-label">Composite Risk:</span>
                <span className="meta-val font-semibold">{selectedZone.risk_score}%</span>
              </div>
              <div className="zone-meta-item">
                <span className="meta-label">Field Metrics:</span>
                <span className="meta-val">{selectedZone.details}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
