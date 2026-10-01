import { Layers3, Map } from 'lucide-react'
import ResourceState from './ResourceState.jsx'

function MapPanel({ resource }) {
  const geoJson = resource.data?.data
  const featureCount = Array.isArray(geoJson?.features) ? geoJson.features.length : null
  const available = resource.data?.status === 'ok'

  return (
    <section className="dashboard-section" id="gis-map" aria-labelledby="map-title">
      <div className="section-heading">
        <div><span className="section-kicker">SPATIAL LAYER</span><h2 id="map-title">Climate risk map</h2></div>
        <span className="integration-tag"><Layers3 size={13} aria-hidden="true" /> AWAITING GIS</span>
      </div>
      <ResourceState
        status={resource.status}
        errorMessage="Unable to load GIS output. Please try again."
        onRetry={resource.retry}
        loadingMessage="Loading GIS output..."
      >
        <div className={`map-panel ${available ? 'map-available' : 'map-unavailable'}`}>
          <div className="map-visual" aria-hidden="true"><span className="map-symbol"><Map size={24} strokeWidth={1.5} /></span></div>
          <div className="map-copy">
            <span className={`map-status ${available ? 'ready' : ''}`}><span /> {available ? 'GeoJSON layer received' : 'No layer connected'}</span>
            <h3>{available ? 'GIS output received' : 'GIS layer unavailable'}</h3>
            <p>{available
              ? 'Geographic output is available from the GIS service. Spatial processing remains with Member 3.'
              : resource.data?.message ?? 'Waiting for the GIS service response.'}</p>
            {available && (
              <span className="map-meta">
                {geoJson?.type ?? 'GeoJSON'}{featureCount === null ? '' : ` · ${featureCount} features`}
              </span>
            )}
          </div>
        </div>
      </ResourceState>
    </section>
  )
}

export default MapPanel
