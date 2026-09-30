import React from 'react';
import { RISK_LEVELS } from '../utils/constants';

export default function AlertCard({ alert, isLive = false }) {
  const { hazard, severity, title, message, location, timestamp, active } = alert;
  const severityKey = (severity || 'MODERATE').toUpperCase();
  const meta = RISK_LEVELS[severityKey] || RISK_LEVELS.MODERATE;

  const getHazardIcon = (h) => {
    switch ((h || '').toLowerCase()) {
      case 'flood':
        return '🌊';
      case 'air_quality':
      case 'aqi':
        return '💨';
      case 'heatwave':
        return '🔥';
      case 'drought':
        return '☀️';
      default:
        return '⚠️';
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Just now';
    try {
      const d = new Date(ts);
      if (!isNaN(d.getTime())) {
        return d.toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZoneName: 'short',
        });
      }
    } catch {
      // Fallback to raw string
    }
    return String(ts);
  };

  return (
    <div
      className="alert-card"
      style={{
        borderLeftColor: meta.color,
      }}
    >
      <div className="alert-card-header">
        <div className="alert-title-wrap">
          <span className="alert-hazard-icon">{getHazardIcon(hazard)}</span>
          <div>
            <h4 className="alert-headline">{title}</h4>
            <span className="alert-location-tag">📍 {location}</span>
          </div>
        </div>
        <div className="alert-meta-badges">
          <span
            className="alert-severity-badge"
            style={{
              color: meta.color,
              backgroundColor: meta.bg,
              borderColor: meta.border,
            }}
          >
            {severity} Severity
          </span>
          {active && <span className="alert-active-pulse">Active</span>}
        </div>
      </div>

      <p className="alert-message-text">{message}</p>

      <div className="alert-card-footer">
        <span className="alert-timestamp">Issued: {formatTimestamp(timestamp)}</span>
        <span className="alert-demo-tag">
          {isLive ? 'Live API Alert (/api/v1/alerts)' : 'Demo Baseline Alert'}
        </span>
      </div>
    </div>
  );
}
