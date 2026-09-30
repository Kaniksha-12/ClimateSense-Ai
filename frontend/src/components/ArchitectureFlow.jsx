import React, { useState } from 'react';

const ARCHITECTURE_STAGES = [
  {
    step: '01',
    id: 'sources',
    title: 'Data Sources',
    subtitle: 'Environmental Telemetry',
    tech: 'Weather Stations & AQI Sensors',
    description: 'Ingestion of atmospheric weather station readings, particulate matter sensors, and satellite surface temperature observations.',
    inputs: ['Ambient Temperature & Humidity', 'Rainfall Gauges (mm)', 'Particulate Matter (PM2.5, PM10)', 'Atmospheric Pressure'],
    color: '#0284c7',
  },
  {
    step: '02',
    id: 'processing',
    title: 'Preprocessing',
    subtitle: 'Member 1 Pipeline Hook',
    tech: 'Data Cleaning & Validation',
    description: 'Data cleaning, outlier removal, missing value imputation, coordinate normalization (WGS-84), and feature vector extraction.',
    inputs: ['Outlier Filtering', 'Spatial Coordinate Indexing', 'Missing Value Imputation', 'Data Validation (Pydantic)'],
    color: '#2563eb',
  },
  {
    step: '03',
    id: 'aiml',
    title: 'ML Predictions',
    subtitle: 'Member 2 Model Registry',
    tech: 'Hazard Inference Models',
    description: 'Standardized model interfaces evaluating flood, drought, heatwave, and air quality risk based on environmental features.',
    inputs: ['XGBoost Flood Interface', 'Random Forest Drought Interface', 'LSTM Temperature Trend Interface', 'Ensemble AQI Model Interface'],
    color: '#7c3aed',
  },
  {
    step: '04',
    id: 'risk',
    title: 'Risk Engine',
    subtitle: 'Multi-Hazard Synthesis',
    tech: 'Weighted Risk Aggregation',
    description: 'Synthesizes individual hazard probabilities into a unified regional score (0-100) using weighted aggregation.',
    inputs: ['Flood Weight (35%)', 'Air Quality Weight (25%)', 'Heatwave Weight (20%)', 'Drought Weight (20%)'],
    color: '#d97706',
  },
  {
    step: '05',
    id: 'gis',
    title: 'GIS Mapping',
    subtitle: 'Member 3 Spatial Layer',
    tech: 'GeoJSON Specifications',
    description: 'Structures spatial risk data into RFC 7946 GeoJSON FeatureCollections for regional zone and coordinate visualization.',
    inputs: ['FeatureCollection Payloads', 'Zone Coordinates [lon, lat]', 'Vulnerability Metadata', 'CRS EPSG:4326 Standards'],
    color: '#059669',
  },
  {
    step: '06',
    id: 'alerts',
    title: 'Early Warnings',
    subtitle: 'Alert Trigger Matrix',
    tech: 'Threshold Notifications',
    description: 'Evaluates hazard probabilities against configurable thresholds (default: 50%) to automatically generate actionable advisories.',
    inputs: ['Flash Flood Advisories', 'Air Quality Alerts', 'Thermal Anomaly Warnings', 'Severity Tiers (Low - Severe)'],
    color: '#ea580c',
  },
  {
    step: '07',
    id: 'dashboard',
    title: 'Dashboard',
    subtitle: 'Web Application',
    tech: 'React 18 & FastAPI REST',
    description: 'User dashboard delivering regional risk assessments, sensor telemetry cards, interactive GIS zones, and live alert feeds.',
    inputs: ['Summary Overview Tab', 'ML Predictions Workspace', 'Interactive GIS Zone Inspector', 'FastAPI REST Endpoints (/api/v1)'],
    color: '#0284c7',
  },
];

export default function ArchitectureFlow() {
  const [activeStageId, setActiveStageId] = useState('risk');
  const activeStage = ARCHITECTURE_STAGES.find((s) => s.id === activeStageId) || ARCHITECTURE_STAGES[3];

  return (
    <div className="arch-flow-wrapper">
      {/* Top Pipeline Stepper */}
      <div className="arch-nodes-container">
        {ARCHITECTURE_STAGES.map((stage, idx) => {
          const isActive = stage.id === activeStageId;
          return (
            <React.Fragment key={stage.id}>
              <div
                className={`arch-node-card ${isActive ? 'active' : ''}`}
                onClick={() => setActiveStageId(stage.id)}
                style={{
                  '--accent-color': stage.color,
                }}
              >
                <div className="arch-node-step">Stage {stage.step}</div>
                <div className="arch-node-title">{stage.title}</div>
                <div className="arch-node-subtitle">{stage.subtitle}</div>
                <div className="arch-node-tech">{stage.tech}</div>
              </div>

              {idx < ARCHITECTURE_STAGES.length - 1 && (
                <div className="arch-connector">
                  <span className="connector-arrow">➔</span>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Inspector Panel for Selected Stage */}
      <div className="arch-detail-inspector">
        <div className="inspector-header">
          <div className="inspector-tags">
            <span className="inspector-step-tag">Stage {activeStage.step} Specification</span>
            <span className="inspector-tech-tag" style={{ color: activeStage.color, borderColor: `${activeStage.color}40`, backgroundColor: `${activeStage.color}15` }}>
              {activeStage.tech}
            </span>
          </div>
          <h3 className="inspector-title">{activeStage.title}</h3>
          <p className="inspector-subtitle">{activeStage.subtitle}</p>
        </div>

        <p className="inspector-desc">{activeStage.description}</p>

        <div className="inspector-inputs-grid">
          {activeStage.inputs.map((item, i) => (
            <div key={i} className="inspector-input-item">
              <span className="input-bullet" style={{ color: activeStage.color }}>•</span>
              <span className="input-text">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
