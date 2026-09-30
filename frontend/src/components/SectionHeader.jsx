import React from 'react';

export default function SectionHeader({ title, subtitle, badge }) {
  return (
    <div className="section-header">
      <div className="section-title-wrap">
        <h2 className="section-title">{title}</h2>
        {badge && <span className="section-badge">{badge}</span>}
      </div>
      {subtitle && <p className="section-subtitle">{subtitle}</p>}
    </div>
  );
}
