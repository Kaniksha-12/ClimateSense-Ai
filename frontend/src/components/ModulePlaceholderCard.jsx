import React from 'react';

export default function ModulePlaceholderCard({ title, description, icon, status = 'Planned' }) {
  return (
    <div className="module-card">
      <div className="module-card-header">
        <span className="module-icon">{icon}</span>
        <span className="module-badge">{status}</span>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
