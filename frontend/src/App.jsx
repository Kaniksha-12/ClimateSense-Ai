import React, { useCallback, useEffect, useState } from 'react';
import BootSequence from './components/BootSequence';
import Header from './components/Header';
import { parseGeoJSONFeaturesToZones } from './map';
import DashboardOverview from './pages/DashboardOverview';
import LandingPage from './pages/LandingPage';
import {
  checkBackendHealth,
  getAlerts,
  getAQI,
  getPredictions,
  getRisk,
  getRiskMap,
  getWeather,
} from './services/api';
import { DEV_DATA } from './utils/constants';

export default function App() {
  const [hasBooted, setHasBooted] = useState(false);
  const [viewMode, setViewMode] = useState('landing'); // 'landing' | 'cockpit'
  const [activeWorkspace, setActiveWorkspace] = useState('overview');
  const [isLiveBackend, setIsLiveBackend] = useState(false);

  // Global telemetry cache so landing page displays accurate live/dev values
  const [weather, setWeather] = useState(DEV_DATA.weather);
  const [aqi, setAqi] = useState(DEV_DATA.aqi);
  const [overallRisk, setOverallRisk] = useState(DEV_DATA.overallRisk);
  const [predictions, setPredictions] = useState(DEV_DATA.predictions);
  const [mapZones, setMapZones] = useState(DEV_DATA.mapZones);
  const [alerts, setAlerts] = useState(DEV_DATA.alerts);

  const fetchGlobalData = useCallback(async () => {
    try {
      const health = await checkBackendHealth();
      const live = health.status === 'online';
      setIsLiveBackend(live);

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
    } catch (err) {
      console.warn('[App] Backend sync error, continuing with fallback baseline:', err);
    }
  }, []);

  useEffect(() => {
    fetchGlobalData();
  }, [fetchGlobalData]);

  const handleEnterCockpit = (workspace = 'overview') => {
    setActiveWorkspace(workspace);
    setViewMode('cockpit');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReturnToLanding = () => {
    setViewMode('landing');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      {/* 1. SHORT INITIALIZATION BOOT SEQUENCE */}
      {!hasBooted && (
        <BootSequence
          onComplete={() => {
            setHasBooted(true);
          }}
        />
      )}

      {/* Persistent Global Header */}
      <Header
        isLiveBackend={isLiveBackend}
        viewMode={viewMode}
        onNavigate={(mode) => {
          if (mode === 'cockpit') handleEnterCockpit();
          else handleReturnToLanding();
        }}
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={(ws) => {
          setActiveWorkspace(ws);
          if (viewMode !== 'cockpit') setViewMode('cockpit');
        }}
      />

      {/* Layer 1: Cinematic Landing Experience */}
      {viewMode === 'landing' ? (
        <LandingPage
          onEnterApp={() => handleEnterCockpit('overview')}
          isLiveBackend={isLiveBackend}
          weather={weather}
          aqi={aqi}
          overallRisk={overallRisk}
          predictions={predictions}
          mapZones={mapZones}
          alerts={alerts}
        />
      ) : (
        /* Layer 2: Functional Climate Intelligence Cockpit */
        <DashboardOverview
          onStatusChange={setIsLiveBackend}
          onBackToLanding={handleReturnToLanding}
          initialWorkspace={activeWorkspace}
        />
      )}

      {/* Footer */}
      <footer className="footer-container">
        <div className="footer-content">
          <div className="footer-left">
            <p>
              <strong>ClimateSense AI</strong> &copy; 2026 — AI-Powered Climate Intelligence &amp; Early Warning System
            </p>
            <p className="footer-subtext">
              Member 4 Architecture • Member 1 (Data) • Member 2 (ML) • Member 3 (GIS) Integration Ready
            </p>
          </div>
          <div className="footer-right">
            <button
              type="button"
              className="footer-reboot-btn"
              onClick={() => {
                setHasBooted(false);
              }}
              title="Re-run System Initialization Sequence"
            >
              ↻ Re-run Boot Sequence
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
