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
      {/* 1. CINEMATIC HERO SECTION */}
      <section className="landing-hero-section">
        {/* Background Grid & Radial Glow */}
        <div className="hero-grid-overlay"></div>
        <div className="hero-glow-orb hero-glow-1"></div>
        <div className="hero-glow-orb hero-glow-2"></div>

        <div className="landing-hero-container">
          {/* Top Technical Metadata Pill */}
          <div className="hero-sys-badge">
            <span className="badge-pulse-dot"></span>
            <span className="badge-sys-code">SYSTEM // CLIMATE INTELLIGENCE</span>
            <span className="badge-divider">|</span>
            <span className="badge-status-text">
              {isLiveBackend ? 'FASTAPI REST BACKEND ONLINE' : 'DEMO BASELINE ACTIVE'}
            </span>
          </div>

          {/* Main Cinematic Headings */}
          <h1 className="hero-main-title">CLIMATESENSE AI</h1>
          <h2 className="hero-sub-title">CLIMATE INTELLIGENCE &amp; EARLY WARNING SYSTEM</h2>

          {/* Philosophy / Core Directive Quote */}
          <div className="hero-tagline-bracket">
            <span className="bracket-mark">[</span>
            <span className="tagline-core-text">Observe. Predict. Map. Warn.</span>
            <span className="bracket-mark">]</span>
          </div>

          <p className="hero-description">
            An AI-powered climate intelligence platform combining environmental data,
            machine learning and GIS to identify and visualize emerging climate risks.
          </p>

          {/* Action CTAs */}
          <div className="hero-actions-group">
            <button
              type="button"
              className="cta-enter-btn glow-effect"
              onClick={onEnterApp}
            >
              <span className="btn-bracket">⟪</span>
              <span className="btn-label">ENTER CLIMATE INTELLIGENCE</span>
              <span className="btn-bracket">⟫</span>
            </button>

            <button
              type="button"
              className="cta-explore-btn"
              onClick={() => scrollTo('section-observe')}
            >
              EXPLORE CAPABILITIES ↓
            </button>
          </div>

          {/* Hero Live Telemetry Ribbon */}
          <div className="hero-telemetry-hud">
            <div className="hud-metric">
              <span className="hud-metric-label">ATMOSPHERIC TEMP</span>
              <span className="hud-metric-val">{weather?.temperature ?? 29.5}°C</span>
              <span className="hud-metric-sub">Central Station</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">AIR QUALITY INDEX</span>
              <span className="hud-metric-val aqi-val">{aqi?.aqi ?? 165} AQI</span>
              <span className="hud-metric-sub">PM2.5: {aqi?.pm25 ?? 78.4} µg/m³</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">COMPOSITE RISK</span>
              <span className="hud-metric-val" style={{ color: overallMeta.color }}>
                {overallRisk?.overall_risk_score ?? 60.5} / 100
              </span>
              <span className="hud-metric-sub">{overallRisk?.overall_risk_level ?? 'High'} Tier</span>
            </div>
            <div className="hud-divider"></div>
            <div className="hud-metric">
              <span className="hud-metric-label">ACTIVE WARNINGS</span>
              <span className="hud-metric-val alert-val">{alerts?.length ?? 3} Active</span>
              <span className="hud-metric-sub">Advisories Issued</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. SCROLL STORY: SECTION 01 — OBSERVE */}
      <section className="story-section" id="section-observe">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">01</span>
              <span className="story-label">// OBSERVE</span>
            </div>
            <h2 className="story-title">Continuous Environmental Monitoring</h2>
            <p className="story-lead">
              Real-time atmospheric telemetry ingesting continuous observations across ambient temperature,
              humidity levels, precipitation indices, surface wind velocity, and ambient air pollution.
            </p>
          </div>

          <div className="observe-grid">
            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">THERMAL SPECTRUM</span>
                <span className="observe-icon">🌡️</span>
              </div>
              <div className="observe-metric-value">{weather?.temperature ?? 29.5}<span className="unit">°C</span></div>
              <div className="observe-metric-name">Ambient Temperature</div>
              <p className="observe-metric-desc">Continuous sensor feed measuring regional heat load across microclimates.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.temperature ?? 29.5) / 50) * 100)}%`, backgroundColor: '#06b6d4' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">MOISTURE SATURATION</span>
                <span className="observe-icon">💧</span>
              </div>
              <div className="observe-metric-value">{weather?.humidity ?? 62.0}<span className="unit">%</span></div>
              <div className="observe-metric-name">Relative Humidity</div>
              <p className="observe-metric-desc">Critical indicator for vapor pressure deficit and extreme heat stress indices.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${weather?.humidity ?? 62}%`, backgroundColor: '#3b82f6' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">PRECIPITATION INDEX</span>
                <span className="observe-icon">🌧️</span>
              </div>
              <div className="observe-metric-value">{weather?.rainfall ?? 14.2}<span className="unit">mm</span></div>
              <div className="observe-metric-name">Rainfall Gauge</div>
              <p className="observe-metric-desc">Cumulative 24h precipitation tracking surface water saturation and runoff risks.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.rainfall ?? 14.2) / 50) * 100)}%`, backgroundColor: '#f59e0b' }}></div>
              </div>
            </div>

            <div className="observe-card">
              <div className="observe-card-header">
                <span className="observe-tag">ATMOSPHERIC DYNAMICS</span>
                <span className="observe-icon">💨</span>
              </div>
              <div className="observe-metric-value">{weather?.wind_speed ?? 18.5}<span className="unit">km/h</span></div>
              <div className="observe-metric-name">Wind Velocity</div>
              <p className="observe-metric-desc">Vector analysis for aerosol dispersion and localized convective front acceleration.</p>
              <div className="observe-bar-track">
                <div className="observe-bar-fill" style={{ width: `${Math.min(100, ((weather?.wind_speed ?? 18.5) / 60) * 100)}%`, backgroundColor: '#10b981' }}></div>
              </div>
            </div>

            <div className="observe-card observe-card-span-2">
              <div className="observe-card-header">
                <span className="observe-tag">PARTICULATE CONCENTRATION</span>
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

      {/* 3. SCROLL STORY: SECTION 02 — PREDICT */}
      <section className="story-section story-alt-bg" id="section-predict">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">02</span>
              <span className="story-label">// PREDICT</span>
            </div>
            <h2 className="story-title">AI / ML Climate Hazard Prediction</h2>
            <p className="story-lead">
              Multi-hazard machine learning pipelines forecasting extreme climate events before they manifest.
              Our architecture isolates model interfaces to support production integration of trained weights.
            </p>
            <div className="honest-model-notice">
              <span className="notice-icon">ℹ️</span>
              <span>
                <strong>System Transparency Notice:</strong> Current models operate as <em>Development Models &amp; Model Interfaces</em> calibrated for baseline multi-hazard evaluation. The modular backend architecture is fully prepared to receive production weights from Member 2.
              </span>
            </div>
          </div>

          <div className="predict-story-grid">
            {predictions.map((pred) => {
              const scorePct = Math.round((pred.risk_score || 0) * 100);
              const isHigh = scorePct >= 60;
              const isMod = scorePct >= 40 && scorePct < 60;
              const accentColor = isHigh ? '#f97316' : isMod ? '#f59e0b' : '#10b981';

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
                        <span className="score-label">Predicted Hazard Probability</span>
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

      {/* 4. SCROLL STORY: SECTION 03 — MAP */}
      <section className="story-section" id="section-map">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">03</span>
              <span className="story-label">// MAP</span>
            </div>
            <h2 className="story-title">GIS Spatial Risk Intelligence</h2>
            <p className="story-lead">
              Geographic vulnerability delineated into micro-zones using standard GeoJSON spatial vectors.
              Exposing environmental risks with geographic coordinates and topographical exposure indicators.
            </p>
          </div>

          <div className="map-story-layout">
            {/* Visual Stylized Map Canvas Preview */}
            <div className="map-preview-canvas">
              <div className="map-radar-grid"></div>
              <div className="map-radar-rings"></div>
              <div className="map-center-reticle">
                <span className="reticle-core"></span>
                <span className="reticle-label">NCR BASIN • 28.6139° N, 77.2090° E</span>
              </div>

              {/* Zone Pins */}
              {mapZones.map((zone, i) => {
                const isHigh = zone.risk_level === 'High' || zone.risk_level === 'Severe';
                const pinColor = isHigh ? '#f97316' : '#f59e0b';
                const posStyles = [
                  { top: '35%', left: '42%' },
                  { top: '20%', left: '60%' },
                  { top: '65%', left: '30%' },
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

            {/* Zone Telemetry List */}
            <div className="map-zones-column">
              <h3 className="column-title">Monitored Geospatial Zones</h3>
              <div className="zones-list">
                {mapZones.map((zone) => (
                  <div key={zone.id} className="zone-summary-card">
                    <div className="zone-summary-header">
                      <span className="zone-name">{zone.name}</span>
                      <span
                        className="zone-level-pill"
                        style={{
                          color: zone.risk_level === 'Severe' || zone.risk_level === 'High' ? '#f97316' : '#10b981',
                        }}
                      >
                        {zone.risk_level}
                      </span>
                    </div>
                    <p className="zone-desc">{zone.details}</p>
                    <div className="zone-coords">
                      <span>Coordinates: [{zone.coordinates?.join(', ')}]</span>
                      <span>Primary Hazard: <strong>{zone.hazard}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="map-integration-note">
                <span>GeoJSON Layer Ready</span>
                <code>GET /api/v1/map/risk</code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. SCROLL STORY: SECTION 04 — WARN */}
      <section className="story-section story-alt-bg" id="section-warn">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">04</span>
              <span className="story-label">// WARN</span>
            </div>
            <h2 className="story-title">Early Warning &amp; Emergency Advisories</h2>
            <p className="story-lead">
              Automated threshold trigger matrices that convert raw prediction scores and sensor anomalies
              into time-stamped, actionable advisories for disaster response teams and civic authorities.
            </p>
          </div>

          <div className="warn-story-grid">
            {alerts.map((al) => {
              const isCrit = al.severity === 'Severe' || al.severity === 'High';
              const sevColor = isCrit ? '#ef4444' : '#f59e0b';

              return (
                <div key={al.id} className="warn-story-card" style={{ borderLeftColor: sevColor }}>
                  <div className="warn-card-header">
                    <div className="warn-type-group">
                      <span className="warn-dot" style={{ backgroundColor: sevColor }}></span>
                      <span className="warn-hazard">{al.hazard.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <span className="warn-sev-badge" style={{ color: sevColor, borderColor: `${sevColor}40` }}>
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

      {/* 6. SCROLL STORY: SECTION 05 — ARCHITECTURE */}
      <section className="story-section" id="section-architecture">
        <div className="story-container">
          <div className="story-header-block">
            <div className="story-badge">
              <span className="story-index">05</span>
              <span className="story-label">// ARCHITECTURE</span>
            </div>
            <h2 className="story-title">Modular System Architecture</h2>
            <p className="story-lead">
              Our decoupled multi-tier design ensures that Member 1 (Data Preprocessing),
              Member 2 (Machine Learning), and Member 3 (GIS Mapping) seamlessly plug into the Member 4
              API and interactive intelligence layers without architectural refactoring.
            </p>
          </div>

          <ArchitectureFlow />
        </div>
      </section>

      {/* 7. FINAL CTA SECTION */}
      <section className="landing-final-cta-section">
        <div className="final-cta-container">
          <div className="cta-tech-tag">SYSTEM STATUS: FULLY ARMED</div>
          <h2 className="cta-title">CLIMATE INTELLIGENCE READY</h2>
          <p className="cta-subtitle">
            Enter the operational command center to inspect live regional telemetry, execute spatial queries,
            and monitor active multi-hazard climate threats in real time.
          </p>

          <button
            type="button"
            className="cta-enter-btn-large glow-effect"
            onClick={onEnterApp}
          >
            <span className="btn-bracket">⟪</span>
            <span className="btn-label">ENTER CLIMATE INTELLIGENCE</span>
            <span className="btn-bracket">⟫</span>
          </button>

          <div className="cta-spec-badges">
            <span className="spec-badge">FastAPI REST v1 Online</span>
            <span className="spec-badge">GeoJSON Geospatial Vector Layer</span>
            <span className="spec-badge">Multi-Hazard Inference Matrix</span>
            <span className="spec-badge">Autonomous Alert Engine</span>
          </div>
        </div>
      </section>
    </div>
  );
}
