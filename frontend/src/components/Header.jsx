import React from 'react';

export default function Header({
  isLiveBackend = false,
  viewMode = 'landing', // 'landing' | 'cockpit'
  onNavigate,
  activeWorkspace = 'overview',
  onSelectWorkspace,
}) {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="header-container">
      <div className="header-content">
        <div
          className="brand-section"
          onClick={() => onNavigate('landing')}
          style={{ cursor: 'pointer' }}
          title="Return to home page"
        >
          <div className="brand-icon">🌍</div>
          <div className="brand-titles">
            <div className="brand-header-row">
              <h1>ClimateSense AI</h1>
              <span className="brand-layer-tag">
                {viewMode === 'cockpit' ? 'Dashboard' : 'Research Prototype'}
              </span>
            </div>
            <p>Climate Risk Monitoring &amp; Early Warning System</p>
          </div>
        </div>

        {/* Dynamic Navigation according to View Mode */}
        <nav className="header-nav">
          {viewMode === 'landing' ? (
            <>
              <button type="button" onClick={() => scrollTo('section-observe')} className="nav-link">
                Monitoring
              </button>
              <button type="button" onClick={() => scrollTo('section-predict')} className="nav-link">
                Predictions
              </button>
              <button type="button" onClick={() => scrollTo('section-map')} className="nav-link">
                Risk Map
              </button>
              <button type="button" onClick={() => scrollTo('section-warn')} className="nav-link">
                Alerts
              </button>
              <button type="button" onClick={() => scrollTo('section-architecture')} className="nav-link">
                Architecture
              </button>
              <button
                type="button"
                onClick={() => onNavigate('cockpit')}
                className="nav-link nav-link-highlight"
              >
                Open Dashboard ➔
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => onNavigate('landing')}
                className="nav-link nav-link-return"
              >
                ← Overview
              </button>
              <button
                type="button"
                onClick={() => onSelectWorkspace && onSelectWorkspace('overview')}
                className={`nav-link ${activeWorkspace === 'overview' ? 'active' : ''}`}
              >
                Summary
              </button>
              <button
                type="button"
                onClick={() => onSelectWorkspace && onSelectWorkspace('predictions')}
                className={`nav-link ${activeWorkspace === 'predictions' ? 'active' : ''}`}
              >
                Predictions
              </button>
              <button
                type="button"
                onClick={() => onSelectWorkspace && onSelectWorkspace('risk-map')}
                className={`nav-link ${activeWorkspace === 'risk-map' ? 'active' : ''}`}
              >
                Risk Map
              </button>
              <button
                type="button"
                onClick={() => onSelectWorkspace && onSelectWorkspace('alerts')}
                className={`nav-link ${activeWorkspace === 'alerts' ? 'active' : ''}`}
              >
                Alerts
              </button>
            </>
          )}
        </nav>

        {/* System Status Indicator */}
        <div className="system-status-badge">
          <span className={`status-dot ${isLiveBackend ? 'online' : 'demo'}`}></span>
          <span>{isLiveBackend ? 'API Connected' : 'Demo Baseline'}</span>
        </div>
      </div>
    </header>
  );
}
