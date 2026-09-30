import React, { useCallback, useEffect, useState } from 'react';
import AlertCard from '../components/AlertCard';
import ClimateCard from '../components/ClimateCard';
import PredictionCard from '../components/PredictionCard';
import RiskCard from '../components/RiskCard';
import RiskMap from '../components/RiskMap';
import SectionHeader from '../components/SectionHeader';
import { parseGeoJSONFeaturesToZones } from '../map';
import {
  checkBackendHealth,
  getAlerts,
  getAQI,
  getPredictions,
  getRisk,
  getRiskMap,
  getWeather,
} from '../services/api';
import { DEV_DATA, RISK_LEVELS } from '../utils/constants';

export default function DashboardOverview({
  onStatusChange,
  onBackToLanding,
  initialWorkspace = 'overview',
}) {
  const [activeWorkspace, setActiveWorkspace] = useState(initialWorkspace);
  const [weather, setWeather] = useState(DEV_DATA.weather);
  const [aqi, setAqi] = useState(DEV_DATA.aqi);
  const [overallRisk, setOverallRisk] = useState(DEV_DATA.overallRisk);
  const [predictions, setPredictions] = useState(DEV_DATA.predictions);
  const [mapZones, setMapZones] = useState(DEV_DATA.mapZones);
  const [alerts, setAlerts] = useState(DEV_DATA.alerts);

  const [isLiveBackend, setIsLiveBackend] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const health = await checkBackendHealth();
      const live = health.status === 'online';
      setIsLiveBackend(live);
      if (onStatusChange) onStatusChange(live);

      // Concurrently query all backend v1 endpoints
      const [wRes, aqiRes, rRes, pRes, mapRes, alRes] = await Promise.all([
        getWeather(),
        getAQI(),
        getRisk(),
        getPredictions(),
        getRiskMap(),
        getAlerts(),
      ]);

      if (wRes.data) setWeather(wRes.data);
      if (aqiRes.data) setAqi(aqiRes.data);
      if (rRes.data) setOverallRisk(rRes.data);
      if (pRes.data && Array.isArray(pRes.data)) setPredictions(pRes.data);
      if (mapRes.data) setMapZones(parseGeoJSONFeaturesToZones(mapRes.data));
      if (alRes.data && Array.isArray(alRes.data)) setAlerts(alRes.data);

      setLastSyncTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.warn('[Dashboard] Data fetch caught exception; continuing with fallback:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  const overallLevelKey = (overallRisk.overall_risk_level || 'HIGH').toUpperCase();
  const overallMeta = RISK_LEVELS[overallLevelKey] || RISK_LEVELS.HIGH;

  return (
    <main className="dashboard-main cockpit-application">
      {/* COCKPIT COMMAND SITUATION BAR */}
      <section className="cockpit-situation-bar">
        <div className="situation-left">
          {onBackToLanding && (
            <button
              type="button"
              className="cockpit-back-btn"
              onClick={onBackToLanding}
              title="Return to Story & System Architecture"
            >
              ← Mission Brief
            </button>
          )}
          <div className="cockpit-title-group">
            <span className="cockpit-tag">COMMAND APPLICATION // LAYER 2</span>
            <h2 className="cockpit-title">Climate Intelligence Cockpit</h2>
          </div>
        </div>

        {/* Cockpit Workspace Navigation Tabs */}
        <div className="cockpit-nav-tabs">
          <button
            type="button"
            className={`cockpit-tab ${activeWorkspace === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveWorkspace('overview')}
          >
            <span className="tab-icon">📊</span>
            <span className="tab-name">Overview</span>
          </button>

          <button
            type="button"
            className={`cockpit-tab ${activeWorkspace === 'predictions' ? 'active' : ''}`}
            onClick={() => setActiveWorkspace('predictions')}
          >
            <span className="tab-icon">🔮</span>
            <span className="tab-name">Predictions</span>
            <span className="tab-badge">{predictions.length}</span>
          </button>

          <button
            type="button"
            className={`cockpit-tab ${activeWorkspace === 'risk-map' ? 'active' : ''}`}
            onClick={() => setActiveWorkspace('risk-map')}
          >
            <span className="tab-icon">🗺️</span>
            <span className="tab-name">Risk Map</span>
            <span className="tab-badge">{mapZones.length}</span>
          </button>

          <button
            type="button"
            className={`cockpit-tab ${activeWorkspace === 'alerts' ? 'active' : ''}`}
            onClick={() => setActiveWorkspace('alerts')}
          >
            <span className="tab-icon">🚨</span>
            <span className="tab-name">Alerts</span>
            <span className={`tab-badge ${alerts.length > 0 ? 'badge-alert' : ''}`}>
              {alerts.length}
            </span>
          </button>

          <button
            type="button"
            className={`cockpit-tab ${activeWorkspace === 'all' ? 'active' : ''}`}
            onClick={() => setActiveWorkspace('all')}
          >
            <span className="tab-icon">⚡</span>
            <span className="tab-name">All Workspaces</span>
          </button>
        </div>

        {/* Cockpit Telemetry Status & Manual Sync */}
        <div className="situation-right">
          <div className="cockpit-sync-group">
            <button
              type="button"
              onClick={handleManualRefresh}
              className="refresh-btn cockpit-refresh"
              title="Sync with backend API"
              disabled={isRefreshing}
            >
              {isRefreshing ? 'Syncing...' : '↻ Sync Data'}
            </button>
            <span className="cockpit-sync-time">
              {lastSyncTime ? `Synced: ${lastSyncTime}` : 'Telemetry Initialized'}
            </span>
          </div>
        </div>
      </section>

      {/* WORKSPACE 1: OVERVIEW */}
      {(activeWorkspace === 'overview' || activeWorkspace === 'all') && (
        <div className="workspace-block fade-in" id="overview">
          {/* SECTION G: VISUALLY PROMINENT OVERALL RISK SUMMARY */}
          <section className="overall-risk-hero">
            <div className="overall-risk-container">
              <div className="overall-risk-left">
                <div className="hero-top-row">
                  <span className="risk-hero-badge">Regional Environmental Intelligence</span>
                  <span className="workspace-badge">WORKSPACE: OVERVIEW</span>
                </div>

                <h2 className="overall-risk-heading">Overall Climate Risk Assessment</h2>
                <p className="overall-risk-location">
                  📍 {overallRisk.location || 'National Capital Region'}
                  {lastSyncTime && <span className="sync-timestamp"> • Updated: {lastSyncTime}</span>}
                </p>

                <div className="overall-score-display">
                  <div
                    className="overall-score-circle"
                    style={{
                      borderColor: overallMeta.color,
                      boxShadow: `0 0 30px ${overallMeta.color}35`,
                    }}
                  >
                    <span className="circle-score-val">{overallRisk.overall_risk_score}</span>
                    <span className="circle-score-max">/ 100</span>
                  </div>
                  <div className="overall-level-callout">
                    <span className="level-subtitle">Assessed Risk Tier</span>
                    <span
                      className="level-badge-large"
                      style={{
                        color: overallMeta.color,
                        backgroundColor: overallMeta.bg,
                        borderColor: overallMeta.border,
                      }}
                    >
                      {overallRisk.overall_risk_level} Risk
                    </span>
                    <span className="risk-model-disclaimer">
                      {isLiveBackend
                        ? 'Synthesized live from Member 2 model registry & prediction service (/api/v1/risk)'
                        : 'Multi-hazard baseline • Ready for calibrated model inputs'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="overall-hazard-breakdown">
                <h3 className="breakdown-title">Contributing Hazards</h3>
                <div className="hazard-bars-list">
                  <div className="hazard-bar-row">
                    <div className="hazard-bar-info">
                      <span>🌊 Flood Risk</span>
                      <span className="hazard-bar-num">{overallRisk.flood_risk}%</span>
                    </div>
                    <div className="hazard-bar-track">
                      <div
                        className="hazard-bar-fill"
                        style={{
                          width: `${overallRisk.flood_risk}%`,
                          backgroundColor: '#f97316',
                        }}
                      ></div>
                    </div>
                  </div>

                  <div className="hazard-bar-row">
                    <div className="hazard-bar-info">
                      <span>☀️ Drought Risk</span>
                      <span className="hazard-bar-num">{overallRisk.drought_risk}%</span>
                    </div>
                    <div className="hazard-bar-track">
                      <div
                        className="hazard-bar-fill"
                        style={{
                          width: `${overallRisk.drought_risk}%`,
                          backgroundColor: '#10b981',
                        }}
                      ></div>
                    </div>
                  </div>

                  <div className="hazard-bar-row">
                    <div className="hazard-bar-info">
                      <span>🔥 Heatwave Risk</span>
                      <span className="hazard-bar-num">{overallRisk.heatwave_risk}%</span>
                    </div>
                    <div className="hazard-bar-track">
                      <div
                        className="hazard-bar-fill"
                        style={{
                          width: `${overallRisk.heatwave_risk}%`,
                          backgroundColor: '#f59e0b',
                        }}
                      ></div>
                    </div>
                  </div>

                  <div className="hazard-bar-row">
                    <div className="hazard-bar-info">
                      <span>💨 Air Quality Risk</span>
                      <span className="hazard-bar-num">{overallRisk.air_quality_risk}%</span>
                    </div>
                    <div className="hazard-bar-track">
                      <div
                        className="hazard-bar-fill"
                        style={{
                          width: `${overallRisk.air_quality_risk}%`,
                          backgroundColor: '#ef4444',
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
                <div className="breakdown-footer-tag">
                  Status: <strong>{isLiveBackend ? 'Connected to' : 'Mocking'}</strong> <code>GET /api/v1/risk</code>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION B: CURRENT ENVIRONMENTAL CONDITIONS */}
          <section className="dashboard-section">
            <SectionHeader
              title="Current Environmental Conditions"
              subtitle="Real-time atmospheric observations and pollution sensor telemetry."
              badge={isLiveBackend ? 'Live API Feed (/weather, /aqi)' : 'Demo Baseline'}
            />
            <div className="climate-cards-grid">
              <ClimateCard
                label="Temperature"
                value={weather.temperature}
                unit="°C"
                icon="🌡️"
                indicator="Nominal"
                statusColor="#06b6d4"
              />
              <ClimateCard
                label="Humidity"
                value={weather.humidity}
                unit="%"
                icon="💧"
                indicator="Moderate"
                statusColor="#3b82f6"
              />
              <ClimateCard
                label="Rainfall"
                value={weather.rainfall}
                unit="mm"
                icon="🌧️"
                indicator="Precipitation Watch"
                statusColor="#f59e0b"
              />
              <ClimateCard
                label="Wind Speed"
                value={weather.wind_speed}
                unit="km/h"
                icon="💨"
                indicator="Gentle Breeze"
                statusColor="#10b981"
              />
              <ClimateCard
                label="Atmospheric Pressure"
                value={weather.pressure || 1012.3}
                unit="hPa"
                icon="🧭"
                indicator="Stable"
                statusColor="#8b5cf6"
              />
              <ClimateCard
                label="Air Quality Index"
                value={aqi.aqi}
                unit="AQI"
                icon="🏭"
                indicator={aqi.aqi > 150 ? 'Unhealthy' : 'Moderate'}
                statusColor={aqi.aqi > 150 ? '#ef4444' : '#f59e0b'}
                subtext={`PM2.5: ${aqi.pm25 || 78.4} µg/m³ • PM10: ${aqi.pm10 || 142.1} µg/m³`}
              />
            </div>
          </section>

          {/* SECTION C: CLIMATE RISK OVERVIEW */}
          <section className="dashboard-section">
            <SectionHeader
              title="Multi-Hazard Threat Overview"
              subtitle="Multi-hazard risk evaluation breakdown across key environmental threat vectors."
              badge={isLiveBackend ? 'Live Aggregation' : 'Development Baseline'}
            />
            <div className="risk-cards-grid">
              {DEV_DATA.risks.map((item) => {
                let liveScore = item.risk_score;
                let liveLevel = item.risk_level;
                if (isLiveBackend && overallRisk) {
                  if (item.id === 'flood') {
                    liveScore = Math.round(overallRisk.flood_risk);
                    liveLevel = liveScore >= 60 ? 'High' : 'Moderate';
                  } else if (item.id === 'drought') {
                    liveScore = Math.round(overallRisk.drought_risk);
                    liveLevel = liveScore >= 60 ? 'High' : 'Low';
                  } else if (item.id === 'heatwave') {
                    liveScore = Math.round(overallRisk.heatwave_risk);
                    liveLevel = liveScore >= 60 ? 'High' : 'Moderate';
                  } else if (item.id === 'air_quality') {
                    liveScore = Math.round(overallRisk.air_quality_risk);
                    liveLevel = liveScore >= 60 ? 'High' : 'Moderate';
                  }
                }
                return (
                  <RiskCard
                    key={item.id}
                    hazard={item.hazard}
                    riskLevel={liveLevel}
                    riskScore={liveScore}
                    indicator={item.indicator}
                    icon={item.icon}
                  />
                );
              })}
            </div>
          </section>
        </div>
      )}

      {/* WORKSPACE 2: PREDICTIONS */}
      {(activeWorkspace === 'predictions' || activeWorkspace === 'all') && (
        <div className="workspace-block fade-in" id="predictions">
          <section className="dashboard-section">
            <SectionHeader
              title="AI / ML Hazard Predictions"
              subtitle="Multi-hazard inference served from Member 2's prediction pipelines."
              badge={isLiveBackend ? 'Live API Feed (/predictions)' : 'Model Integration Ready'}
            />
            <div className="model-integration-notice-bar">
              <span className="notice-icon">⚙️</span>
              <div className="notice-text">
                <strong>Model Interface Architecture:</strong> Predictions currently reflect calibrated baseline interfaces (<code>xgboost_flood_baseline</code>, <code>random_forest_drought_baseline</code>, <code>lstm_temperature_baseline</code>, <code>ensemble_aqi_baseline</code>). Ready for trained weights.
              </div>
            </div>
            <div className="predictions-grid">
              {predictions.map((pred) => (
                <PredictionCard
                  key={pred.hazard}
                  hazard={pred.hazard}
                  title={pred.title || `${pred.hazard.replace('_', ' ').toUpperCase()} Prediction`}
                  prediction={pred.prediction}
                  riskScore={pred.risk_score}
                  riskLevel={pred.risk_level}
                  model={pred.model}
                  icon={
                    pred.hazard === 'flood'
                      ? '🌊'
                      : pred.hazard === 'drought'
                      ? '☀️'
                      : pred.hazard === 'heatwave'
                      ? '🔥'
                      : '💨'
                  }
                />
              ))}
            </div>
          </section>
        </div>
      )}

      {/* WORKSPACE 3: RISK MAP */}
      {(activeWorkspace === 'risk-map' || activeWorkspace === 'all') && (
        <div className="workspace-block fade-in" id="risk-map">
          <section className="dashboard-section">
            <SectionHeader
              title="Spatial Risk & GIS Mapping"
              subtitle="Geospatial monitoring zones and GeoJSON risk layer integration."
              badge={isLiveBackend ? 'Live GeoJSON (/map/risk)' : 'GIS Integration Layer'}
            />
            <RiskMap mapZones={mapZones} isLive={isLiveBackend} />
          </section>
        </div>
      )}

      {/* WORKSPACE 4: ALERTS */}
      {(activeWorkspace === 'alerts' || activeWorkspace === 'all') && (
        <div className="workspace-block fade-in" id="alerts">
          <section className="dashboard-section">
            <SectionHeader
              title="Early Warning Alerts & Advisories"
              subtitle="Actionable emergency notifications triggered by elevated prediction risk scores."
              badge={isLiveBackend ? `${alerts.length} Live Alerts (/alerts)` : `${alerts.length} Demo Advisories`}
            />
            <div className="alerts-list">
              {alerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} isLive={isLiveBackend} />
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
