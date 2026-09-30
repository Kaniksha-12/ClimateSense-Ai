import React, { useEffect, useState } from 'react';

const BOOT_STEPS = [
  { id: 'env', text: 'Connecting environmental data providers', detail: 'Weather observations & AQI metrics' },
  { id: 'ml', text: 'Initializing climate model registry', detail: 'Flood, drought, heatwave & AQI interfaces' },
  { id: 'gis', text: 'Loading spatial GIS layers', detail: 'GeoJSON regional monitoring boundaries' },
  { id: 'warn', text: 'Configuring early warning alert thresholds', detail: 'Multi-hazard notification engine' },
];

export default function BootSequence({ onComplete }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [progress, setProgress] = useState(25);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
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
            setTimeout(onComplete, 350);
          }, 300);
          return prev;
        }
      });
    }, 350);

    return () => clearInterval(interval);
  }, [onComplete]);

  const handleSkip = () => {
    setIsFadingOut(true);
    setTimeout(onComplete, 150);
  };

  return (
    <div className={`boot-overlay ${isFadingOut ? 'fade-out' : ''}`}>
      <div className="boot-dialog">
        {/* Header */}
        <div className="boot-dialog-header">
          <div className="boot-brand-wrap">
            <span className="boot-icon">🌍</span>
            <div>
              <h2 className="boot-app-name">ClimateSense AI</h2>
              <span className="boot-app-tagline">Climate Risk Monitoring &amp; Early Warning System</span>
            </div>
          </div>
          <button type="button" className="boot-skip-btn" onClick={handleSkip}>
            Skip ➔
          </button>
        </div>

        {/* Progress Bar */}
        <div className="boot-progress-wrap">
          <div className="boot-progress-header">
            <span className="boot-progress-title">Starting system services...</span>
            <span className="boot-progress-value">{progress}%</span>
          </div>
          <div className="boot-progress-track">
            <div className="boot-progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
        </div>

        {/* Checklist */}
        <div className="boot-steps-list">
          {BOOT_STEPS.map((step, idx) => {
            const isDone = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;

            return (
              <div
                key={step.id}
                className={`boot-step-row ${isCurrent ? 'current' : ''} ${isDone ? 'done' : 'waiting'}`}
              >
                <div className="boot-step-indicator">
                  {isDone ? (
                    <span className="step-check">✓</span>
                  ) : isCurrent ? (
                    <span className="step-spinner"></span>
                  ) : (
                    <span className="step-bullet">○</span>
                  )}
                </div>
                <div className="boot-step-content">
                  <span className="boot-step-title">{step.text}</span>
                  <span className="boot-step-subtext">{step.detail}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer info */}
        <div className="boot-dialog-footer">
          <span>FastAPI Backend • Port 8000</span>
          <span>GeoJSON WGS-84</span>
          <span>Development Prototype</span>
        </div>
      </div>
    </div>
  );
}
