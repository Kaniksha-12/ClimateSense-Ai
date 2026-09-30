import React from 'react';
import { RISK_LEVELS } from '../utils/constants';

export default function PredictionCard({ hazard, title, prediction, riskScore, riskLevel, model, icon }) {
  const normalizedScore = riskScore > 1.0 ? riskScore : Math.round(riskScore * 100);
  const levelKey = (riskLevel || 'LOW').toUpperCase();
  const levelMeta = RISK_LEVELS[levelKey] || RISK_LEVELS.LOW;

  return (
    <div className="prediction-card">
      <div className="prediction-card-header">
        <div className="prediction-title-group">
          <span className="prediction-icon">{icon}</span>
          <div>
            <h3 className="prediction-hazard-title">{title || hazard}</h3>
            <span className="prediction-hazard-type">Hazard Category: {hazard}</span>
          </div>
        </div>
        <div className="prediction-badge-wrap">
          <span
            className="prediction-level-badge"
            style={{
              color: levelMeta.color,
              backgroundColor: levelMeta.bg,
              borderColor: levelMeta.border,
            }}
          >
            {levelMeta.label} ({normalizedScore}%)
          </span>
        </div>
      </div>

      <p className="prediction-statement">{prediction}</p>

      <div className="prediction-footer">
        <div className="model-tag-wrap">
          <span className="model-label">Model Interface:</span>
          <code className="model-code">{model}</code>
        </div>
        <span className="demo-notice-tag">Development Model</span>
      </div>
    </div>
  );
}
