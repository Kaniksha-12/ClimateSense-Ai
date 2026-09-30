import React from 'react';

export default function ClimateCard({ label, value, unit, icon, indicator, statusColor, subtext }) {
  return (
    <div className="climate-card">
      <div className="climate-card-top">
        <span className="climate-card-icon">{icon}</span>
        {indicator && (
          <span
            className="climate-card-indicator"
            style={{
              color: statusColor || 'var(--text-secondary)',
              borderColor: statusColor ? `${statusColor}40` : 'var(--border-subtle)',
              backgroundColor: statusColor ? `${statusColor}15` : 'rgba(255,255,255,0.03)',
            }}
          >
            {indicator}
          </span>
        )}
      </div>
      <div className="climate-card-body">
        <span className="climate-card-label">{label}</span>
        <div className="climate-card-value-wrap">
          <span className="climate-card-value">{value}</span>
          <span className="climate-card-unit">{unit}</span>
        </div>
        {subtext && <span className="climate-card-subtext">{subtext}</span>}
      </div>
    </div>
  );
}
