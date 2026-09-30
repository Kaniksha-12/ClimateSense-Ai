import React, { useState } from 'react';

const ARCHITECTURE_STAGES = [
  {
    step: '01',
    id: 'sources',
    title: 'DATA SOURCES',
    subtitle: 'Multi-Sensor Ingestion',
    tech: 'IoT & Remote Sensing',
    description: 'Continuous ingestion of weather station observations, particulate pollution monitors, and satellite thermal bands.',
    inputs: ['Temperature & Humidity', 'Rainfall Gauges', 'PM2.5 & PM10 Sensors', 'Satellite Spectral Anomaly'],
    color: '#06b6d4',
  },
  {
    step: '02',
    id: 'processing',
    title: 'DATA PROCESSING',
    subtitle: 'Member 1 Integration Layer',
    tech: 'Cleaning & Normalization',
    description: 'Outlier detection, missing value imputation, coordinate standardization (WGS-84), and feature vector assembly.',
    inputs: ['Z-score Anomaly Filter', 'Geo-spatial Indexing', 'Rolling Averages', 'Format Validation'],
    color: '#3b82f6',
  },
  {
    step: '03',
    id: 'aiml',
    title: 'AI / ML PREDICTION',
    subtitle: 'Member 2 Model Registry',
    tech: 'Ensemble Machine Learning',
    description: 'Independent model interfaces predicting hazard likelihoods across flood, drought, heatwave, and atmospheric air quality.',
    inputs: ['XGBoost Flood Baseline', 'Random Forest Drought', 'LSTM Temperature Trend', 'Ensemble AQI Model'],
    color: '#8b5cf6',
  },
  {
    step: '04',
    id: 'risk',
    title: 'RISK ENGINE',
    subtitle: 'Multi-Hazard Synthesis',
    tech: 'Weighted Threat Scoring',
    description: 'Aggregates individual model hazard predictions into a composite regional risk score (0-100) and assigns assessed threat tiers.',
    inputs: ['Normalized Hazard Weights', 'Composite Risk Tiering', 'Dynamic Calibrations', 'Baseline Fallbacks'],
    color: '#f59e0b',
  },
  {
    step: '05',
    id: 'gis',
    title: 'GIS INTELLIGENCE',
    subtitle: 'Member 3 Spatial Layer',
    tech: 'GeoJSON Choropleths',
    description: 'Transforms multi-hazard intelligence into spatial polygon overlays, bounding coordinates, and geographic exposure zones.',
    inputs: ['GeoJSON Feature Collections', 'Regional Zone Delineation', 'Centroid Coordinates', 'Vulnerability Heatmaps'],
    color: '#10b981',
  },
  {
    step: '06',
    id: 'alerts',
    title: 'EARLY WARNING',
    subtitle: 'Automated Dispatch',
    tech: 'Advisory Trigger Matrix',
    description: 'Evaluates composite hazard scores against safety thresholds to dispatch time-stamped advisories with severity levels.',
    inputs: ['Flash Flood Alerts', 'Air Quality Advisories', 'Thermal Spike Warnings', 'Emergency Action Guidelines'],
    color: '#f97316',
  },
  {
    step: '07',
    id: 'cockpit',
    title: 'CLIMATE INTELLIGENCE',
    subtitle: 'Operational Application',
    tech: 'Mission Cockpit & API',
    description: 'Delivers actionable decision support via interactive telemetry cards, spatial GIS overlays, and RESTful FastAPI endpoints.',
    inputs: ['Real-Time Cockpit HUD', 'REST Endpoints (/api/v1)', 'Zone Inspection Panel', 'Stakeholder Reports'],
    color: '#06b6d4',
  },
];

export default function ArchitectureFlow() {
  const [activeStageId, setActiveStageId] = useState('aiml');
  const activeStage = ARCHITECTURE_STAGES.find((s) => s.id === activeStageId) || ARCHITECTURE_STAGES[2];

  return (
    <div className="arch-flow-wrapper">
      {/* Top Diagram Flow */}
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
                <div className="arch-node-step">{stage.step}</div>
                <div className="arch-node-title">{stage.title}</div>
                <div className="arch-node-subtitle">{stage.subtitle}</div>
                <div className="arch-node-tech">{stage.tech}</div>
                <div className="arch-node-indicator"></div>
              </div>

              {idx < ARCHITECTURE_STAGES.length - 1 && (
                <div className="arch-connector">
                  <div className="connector-line"></div>
                  <div className="connector-arrow">➔</div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Detail Inspector for Selected Node */}
      <div className="arch-detail-inspector" style={{ borderColor: activeStage.color }}>
        <div className="inspector-header">
          <div className="inspector-tags">
            <span className="inspector-step-tag">STAGE {activeStage.step} // PIPELINE SPECIFICATION</span>
            <span className="inspector-tech-tag" style={{ color: activeStage.color, borderColor: activeStage.color }}>
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
              <span className="input-bullet" style={{ color: activeStage.color }}>◆</span>
              <span className="input-text">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
