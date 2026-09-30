import React from 'react';
import ArchitectureFlow from '../components/ArchitectureFlow';
import { DEV_DATA, RISK_LEVELS } from '../utils/constants';

export default function LandingPage({
  onEnterApp,
  isLiveBackend = false,
  weather = DEV_DATA.weather,
  aqi = DEV_DATA.aqi,
  overallRisk = DEV_DATA.overallRisk,
  predictions = DEV_DATA.predictions,
  mapZones = DEV_DATA.mapZones,
  alerts = DEV_DATA.alerts,
}) {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const overallLevelKey = (overallRisk?.overall_risk_level || 'HIGH').toUpperCase();
  const overallMeta = RISK_LEVELS[overallLevelKey] || RISK_LEVELS.HIGH;

  return (
    <div className="landing-experience">
      {/* 1. CLEAN ENGINEERING HERO SECTION */}
      <section className="landing-hero-section">
        <div className="landing-hero-container">
          {/* Status Badge */}
          <div className="hero-sys-badge">
            <span className="badge-pulse-dot"></span>
            <span className="badge-sys-code">System Status:</span>
            <span className="badge-status-text">
              {isLiveBackend ? 'FastAPI Backend Connected' : 'Demo Baseline Active'}
            </span>
          </div>

          {/* Main Title & Subtitle */}
          <h1 className="hero-main-title">ClimateSense AI</h1>
          <h2 className="hero-sub-title">AI-Powered Climate Risk Monitoring &amp; Early Warning System</h2>

          <p className="hero-description">
            A climate intelligence platform combining environmental sensor telemetry, machine learning hazard models,
            and GIS mapping to identify, evaluate, and visualize regional climate risks.
          </p>

          {/* Primary Action Buttons */}
          <div className="hero-actions-group">
            <button
              type="button"
              className="cta-enter-btn"
              onClick={onEnterApp}
            >
              Open Dashboard ➔
            </button>

            <button
              type="button"
              className="cta-explore-btn"
              onClick={() => scrollTo('section-observe')}
            >
              How It Works ↓
            </button>
          </div>

          {/* Live Telemetry Overview Bar */}
          <div className="hero-telemetry-hud">
            <div className="hud-metric">
              <span className="hud-metric-label">Atmospheric Temperature</span>
              <span className="hud-metric-val">{weather?.temperature ?? 29.5}°C</span>
              <span className="hud-metric-sub">Weather Station</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">Air Quality Index</span>
              <span className="hud-metric-val aqi-val">{aqi?.aqi ?? 165} AQI</span>
              <span className="hud-metric-sub">PM2.5: {aqi?.pm25 ?? 78.4} µg/m³</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">Composite Risk</span>
              <span className="hud-metric-val" style={{ color: overallMeta.color }}>
                {overallRisk?.overall_risk_score ?? 60.5} / 100
              </span>
              <span className="hud-metric-sub">{overallRisk?.overall_risk_level ?? 'High'} Tier</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">Active Advisories</span>
              <span className="hud-metric-val alert-val">{alerts?.length ?? 3} Active</span>
              <span className="hud-metric-sub">Early Warnings</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. SECTION 01 — ENVIRONMENTAL MONITORING */}
      <section className="story-section" id="section-observe">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">01</span>
              <span className="story-label">Environmental Monitoring</span>
            </div>
            <h2 className="story-title">Continuous Sensory Data Collection</h2>
            <p className="story-lead">
              ClimateSense collects environmental indicators including temperature, relative humidity,
              precipitation levels, wind velocity, atmospheric pressure, and air pollution measurements.
            </p>
          </div>

          <div className="observe-grid">
            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">Thermal Sensor</span>
                <span className="observe-icon">🌡️</span>
              </div>
              <div className="observe-metric-value">{weather?.temperature ?? 29.5}<span className="unit">°C</span></div>
              <div className="observe-metric-name">Ambient Temperature</div>
              <p className="observe-metric-desc">Continuous observation tracking regional thermal patterns and surface heat build-up.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.temperature ?? 29.5) / 50) * 100)}%`, backgroundColor: '#0284c7' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">Humidity Sensor</span>
                <span className="observe-icon">💧</span>
              </div>
              <div className="observe-metric-value">{weather?.humidity ?? 62.0}<span className="unit">%</span></div>
              <div className="observe-metric-name">Relative Humidity</div>
              <p className="observe-metric-desc">Atmospheric moisture content indicating convective potential and thermal comfort index.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${weather?.humidity ?? 62}%`, backgroundColor: '#2563eb' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">Rain Gauge</span>
                <span className="observe-icon">🌧️</span>
              </div>
              <div className="observe-metric-value">{weather?.rainfall ?? 14.2}<span className="unit">mm</span></div>
              <div className="observe-metric-name">Precipitation</div>
              <p className="observe-metric-desc">Cumulative 24-hour rainfall monitoring for hydrological run-off and drainage accumulation.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.rainfall ?? 14.2) / 50) * 100)}%`, backgroundColor: '#d97706' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">Anemometer</span>
                <span className="observe-icon">💨</span>
              </div>
              <div className="observe-metric-value">{weather?.wind_speed ?? 18.5}<span className="unit">km/h</span></div>
              <div className="observe-metric-name">Wind Velocity</div>
              <p className="observe-metric-desc">Surface wind speed analysis for pollutant dispersal and convective front tracking.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.wind_speed ?? 18.5) / 60) * 100)}%`, backgroundColor: '#059669' }}></div>
              </div>
            </div>

            <div className="observe-card observe-card-span-2">
              <div className="observe-card-header">
                <span className="observe-tag">Air Quality Station</span>
                <span className="observe-icon">🏭</span>
              </div>
              <div className="observe-aqi-row">
                <div className="observe-aqi-main">
                  <div className="observe-metric-value aqi-accent">
                    {aqi?.aqi ?? 165}<span className="unit">AQI</span>
                  </div>
                  <div className="observe-metric-name">Air Quality Index • Unhealthy</div>
                </div>
                <div className="observe-aqi-subgrid">
                  <div className="subgrid-stat">
                    <span className="subgrid-label">PM2.5</span>
                    <span className="subgrid-val">{aqi?.pm25 ?? 78.4} µg/m³</span>
                  </div>
                  <div className="subgrid-stat">
                    <span className="subgrid-label">PM10</span>
                    <span className="subgrid-val">{aqi?.pm10 ?? 142.1} µg/m³</span>
                  </div>
                  <div className="subgrid-stat">
                    <span className="subgrid-label">NO2</span>
                    <span className="subgrid-val">{aqi?.no2 ?? 34.6} ppb</span>
                  </div>
                  <div className="subgrid-stat">
                    <span className="subgrid-label">SO2</span>
                    <span className="subgrid-val">{aqi?.so2 ?? 12.1} ppb</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. SECTION 02 — CLIMATE RISK PREDICTION */}
      <section className="story-section story-alt-bg" id="section-predict">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">02</span>
              <span className="story-label">Climate Risk Prediction</span>
            </div>
            <h2 className="story-title">Machine Learning Hazard Forecasting</h2>
            <p className="story-lead">
              Prediction interfaces are designed to integrate trained models for flood, drought, heatwave,
              and air quality risks. Our decoupled architecture defines standardized interfaces for model integration.
            </p>
            <div className="honest-model-notice">
              <span className="notice-icon">ℹ️</span>
              <span>
                <strong>Integration Note:</strong> Current predictions represent calibrated <em>Development Model Interfaces</em>.
                The architecture is ready to load Member 2's trained models (XGBoost, Random Forest, LSTM) without modifying routes or UI code.
              </span>
            </div>
          </div>

          <div className="predict-story-grid">
            {predictions.map((pred) => {
              const scorePct = Math.round((pred.risk_score || 0) * 100);
              const isHigh = scorePct >= 60;
              const isMod = scorePct >= 40 && scorePct < 60;
              const accentColor = isHigh ? '#ea580c' : isMod ? '#d97706' : '#059669';

              return (
                <div key={pred.hazard} className="predict-story-card">
                  <div className="predict-card-top">
                    <div className="hazard-pill">
                      <span className="hazard-emoji">
                        {pred.hazard === 'flood' ? '🌊' : pred.hazard === 'drought' ? '☀️' : pred.hazard === 'heatwave' ? '🔥' : '💨'}
                      </span>
                      <span className="hazard-name">{pred.hazard.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <span className="model-interface-tag">Model Interface</span>
                  </div>

                  <h3 className="predict-title">{pred.title}</h3>
                  <p className="predict-text">{pred.prediction}</p>

                  <div className="predict-score-row">
                    <div className="score-meter-wrap">
                      <div className="score-meta">
                        <span className="score-label">Predicted Hazard Likelihood</span>
                        <span className="score-value" style={{ color: accentColor }}>
                          {scorePct}% ({pred.risk_level})
                        </span>
                      </div>
                      <div className="score-track">
                        <div
                          className="score-fill"
                          style={{ width: `${scorePct}%`, backgroundColor: accentColor }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  <div className="predict-card-footer">
                    <span className="model-registry-name"><code>{pred.model}</code></span>
                    <span className="location-tag">📍 {pred.location}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. SECTION 03 — GIS RISK MAPPING */}
      <section className="story-section" id="section-map">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">03</span>
              <span className="story-label">GIS Risk Mapping</span>
            </div>
            <h2 className="story-title">Geospatial Risk Zone Delineation</h2>
            <p className="story-lead">
              Spatial risk data is exchanged as GeoJSON FeatureCollections and visualized as regional monitoring
              zones with geographic coordinates and exposure metrics.
            </p>
          </div>

          <div className="map-story-layout">
            {/* Visual Map Canvas Preview */}
            <div className="map-preview-canvas">
              <div className="map-radar-grid"></div>
              <div className="map-center-reticle">
                <span className="reticle-core"></span>
                <span className="reticle-label">National Capital Region • 28.6139° N, 77.2090° E</span>
              </div>

              {/* Zone Pins */}
              {mapZones.map((zone, i) => {
                const isHigh = zone.risk_level === 'High' || zone.risk_level === 'Severe';
                const pinColor = isHigh ? '#ea580c' : '#d97706';
                const posStyles = [
                  { top: '35%', left: '45%' },
                  { top: '22%', left: '65%' },
                  { top: '65%', left: '32%' },
                ];
                const pos = posStyles[i % posStyles.length];

                return (
                  <div
                    key={zone.id}
                    className="map-zone-pin"
                    style={{ ...pos, borderColor: pinColor }}
                  >
                    <span className="pin-pulse" style={{ backgroundColor: pinColor }}></span>
                    <div className="pin-popup">
                      <span className="pin-title">{zone.name}</span>
                      <span className="pin-badge" style={{ color: pinColor }}>
                        {zone.risk_level} • {zone.hazard}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Zone Information List */}
            <div className="map-zones-column">
              <h3 className="column-title">Monitored Regional Zones</h3>
              <div className="zones-list">
                {mapZones.map((zone) => (
                  <div key={zone.id} className="zone-summary-card">
                    <div className="zone-summary-header">
                      <span className="zone-name">{zone.name}</span>
                      <span
                        className="zone-level-pill"
                        style={{
                          color: zone.risk_level === 'Severe' || zone.risk_level === 'High' ? '#ea580c' : '#059669',
                        }}
                      >
                        {zone.risk_level}
                      </span>
                    </div>
                    <p className="zone-desc">{zone.details}</p>
                    <div className="zone-coords">
                      <span>Coordinates: [{zone.coordinates?.join(', ')}]</span>
                      <span>Dominant: <strong>{zone.hazard}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="map-integration-note">
                <span>GeoJSON Layer:</span>
                <code>GET /api/v1/map/risk</code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. SECTION 04 — EARLY WARNING ALERTS */}
      <section className="story-section story-alt-bg" id="section-warn">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">04</span>
              <span className="story-label">Early Warnings</span>
            </div>
            <h2 className="story-title">Automated Advisory Notifications</h2>
            <p className="story-lead">
              Configurable threshold triggers evaluate hazard probabilities to automatically dispatch
              prioritized advisories with location details, severity categories, and timestamps.
            </p>
          </div>

          <div className="warn-story-grid">
            {alerts.map((al) => {
              const isCrit = al.severity === 'Severe' || al.severity === 'High';
              const sevColor = isCrit ? '#dc2626' : '#d97706';

              return (
                <div key={al.id} className="warn-story-card" style={{ borderLeftColor: sevColor }}>
                  <div className="warn-card-header">
                    <div className="warn-type-group">
                      <span className="warn-dot" style={{ backgroundColor: sevColor }}></span>
                      <span className="warn-hazard">{al.hazard.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <span className="warn-sev-badge" style={{ color: sevColor, borderColor: `${sevColor}40`, backgroundColor: `${sevColor}10` }}>
                      {al.severity} Severity
                    </span>
                  </div>

                  <h3 className="warn-title">{al.title}</h3>
                  <p className="warn-msg">{al.message}</p>

                  <div className="warn-footer">
                    <span className="warn-loc">📍 {al.location}</span>
                    <span className="warn-time">⏱ {al.timestamp}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 6. SECTION 05 — SYSTEM ARCHITECTURE */}
      <section className="story-section" id="section-architecture">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">05</span>
              <span className="story-label">System Architecture</span>
            </div>
            <h2 className="story-title">End-to-End Pipeline Overview</h2>
            <p className="story-lead">
              Our modular pipeline decouples data collection, machine learning models, GIS mapping,
              and dashboard presentation so that individual team member modules integrate cleanly.
            </p>
          </div>

          <ArchitectureFlow />
        </div>
      </section>

      {/* 7. FINAL CALL-TO-ACTION SECTION */}
      <section className="landing-final-cta-section">
        <div className="final-cta-container">
          <div className="cta-tech-tag">Climate Risk Monitoring</div>
          <h2 className="cta-title">Explore the Live System</h2>
          <p className="cta-subtitle">
            Open the dashboard to view synthesized regional risk assessments, sensor telemetry,
            multi-hazard predictions, and active early-warning advisories.
          </p>

          <button
            type="button"
            className="cta-enter-btn-large"
            onClick={onEnterApp}
          >
            Open Dashboard ➔
          </button>

          <div className="cta-spec-badges">
            <span className="spec-badge">FastAPI REST Backend</span>
            <span className="spec-badge">GeoJSON GIS Layer</span>
            <span className="spec-badge">Multi-Hazard Models</span>
            <span className="spec-badge">Automated Alerts</span>
          </div>
        </div>
      </section>
    </div>
  );
}
