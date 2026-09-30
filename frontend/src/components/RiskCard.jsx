import React from 'react';
import { RISK_LEVELS } from '../utils/constants';

export default function RiskCard({ hazard, riskLevel, riskScore, indicator, icon }) {
  const levelKey = (riskLevel || 'LOW').toUpperCase();
  const levelMeta = RISK_LEVELS[levelKey] || RISK_LEVELS.LOW;

  return (
    <div className="risk-card">
      <div className="risk-card-header">
        <div className="risk-hazard-title">
          <span className="risk-icon">{icon}</span>
          <span className="risk-hazard-name">{hazard}</span>
        </div>
        <span
          className="risk-level-badge"
          style={{
            color: levelMeta.color,
            backgroundColor: levelMeta.bg,
            borderColor: levelMeta.border,
          }}
        >
          {levelMeta.label}
        </span>
      </div>

      <div className="risk-card-score-container">
        <div className="risk-score-value">
          <span className="risk-number">{riskScore}</span>
          <span className="risk-percent">%</span>
        </div>
        <span className="risk-score-caption">Risk Score</span>
      </div>

      <div className="risk-meter-track">
        <div
          className="risk-meter-bar"
          style={{
            width: `${Math.min(100, Math.max(0, riskScore))}%`,
            backgroundColor: levelMeta.color,
            boxShadow: `0 0 10px ${levelMeta.color}60`,
          }}
        ></div>
      </div>

      <div className="risk-card-footer">
        <span className="risk-card-indicator">{indicator}</span>
        <span className="risk-demo-pill">Demo Value</span>
      </div>
    </div>
  );
}
