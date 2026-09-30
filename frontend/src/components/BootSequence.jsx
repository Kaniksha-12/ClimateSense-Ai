import React, { useEffect, useState } from 'react';

const BOOT_STEPS = [
  { id: 'sys', text: 'SYSTEM INITIALIZING...', detail: 'Kernel v4.2 • Core memory mapped' },
  { id: 'env', text: 'ENVIRONMENTAL DATA // INGESTION ONLINE', detail: 'Weather sensors & AQI telemetry connected' },
  { id: 'ml', text: 'AI RISK ENGINE // MODEL INTERFACES LOADED', detail: 'XGBoost • Random Forest • LSTM baselines active' },
  { id: 'gis', text: 'GIS INTELLIGENCE // SPATIAL MATRIX READY', detail: 'GeoJSON vector layer & coordinate grid aligned' },
  { id: 'warn', text: 'EARLY WARNING // TELEMETRY WATCH ARMED', detail: 'Multi-hazard threshold triggers enabled' },
];

export default function BootSequence({ onComplete }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [progress, setProgress] = useState(15);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    // Step advancement timer
    const interval = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < BOOT_STEPS.length - 1) {
          const next = prev + 1;
          setProgress(Math.round(((next + 1) / BOOT_STEPS.length) * 100));
          return next;
        } else {
          clearInterval(interval);
          setProgress(100);
          setTimeout(() => {
            setIsFadingOut(true);
            setTimeout(onComplete, 500);
          }, 400);
          return prev;
        }
      });
    }, 450);

    return () => clearInterval(interval);
  }, [onComplete]);

  const handleSkip = () => {
    setIsFadingOut(true);
    setTimeout(onComplete, 200);
  };

  return (
    <div className={`boot-overlay ${isFadingOut ? 'fade-out' : ''}`}>
      <div className="boot-terminal">
        {/* Terminal Header */}
        <div className="boot-header">
          <div className="boot-reticle-group">
            <span className="boot-reticle-dot"></span>
            <span className="boot-header-title">CLIMATESENSE AI // INITIALIZATION SEQUENCE</span>
          </div>
          <button type="button" className="boot-skip-btn" onClick={handleSkip}>
            SKIP [ESC] ➔
          </button>
        </div>

        {/* Radar / Reticle Centerpiece */}
        <div className="boot-center-graphic">
          <div className="boot-radar-circle outer"></div>
          <div className="boot-radar-circle middle"></div>
          <div className="boot-radar-circle inner"></div>
          <div className="boot-radar-sweep"></div>
          <div className="boot-radar-crosshair-h"></div>
          <div className="boot-radar-crosshair-v"></div>
          <div className="boot-center-brand">
            <span className="boot-brand-globe">🌍</span>
            <span className="boot-brand-text">CLIMATESENSE</span>
          </div>
        </div>

        {/* Progress Display */}
        <div className="boot-progress-section">
          <div className="boot-progress-info">
            <span className="boot-progress-label">INITIALIZING SYSTEM PIPELINE</span>
            <span className="boot-progress-pct">{progress}%</span>
          </div>
          <div className="boot-progress-track">
            <div className="boot-progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        </div>

        {/* Terminal Step Logs */}
        <div className="boot-log-feed">
          {BOOT_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;
            const isPending = idx > currentStepIndex;

            return (
              <div
                key={step.id}
                className={`boot-log-item ${isCurrent ? 'active' : ''} ${isCompleted ? 'done' : ''} ${
                  isPending ? 'pending' : ''
                }`}
              >
                <span className="boot-log-status">
                  {isCompleted ? '✓ READY' : isCurrent ? '▶ LOAD' : '○ WAIT'}
                </span>
                <span className="boot-log-name">{step.text}</span>
                <span className="boot-log-detail">{step.detail}</span>
              </div>
            );
          })}
        </div>

        <div className="boot-footer-meta">
          <span>SECURE TELEMETRY LINK • PORT 8000</span>
          <span>DEV_DATA FALLBACK ARMED</span>
          <span>GEOSPATIAL WGS-84</span>
        </div>
      </div>
    </div>
  );
}
