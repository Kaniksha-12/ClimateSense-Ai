import { CloudSun, Droplets, Thermometer, Wind } from 'lucide-react'
import ResourceState from './ResourceState.jsx'
import StatCard from './StatCard.jsx'

function ConditionOverview({ resource }) {
  const conditions = resource.data
  const values = conditions && [
    { label: 'Temperature', value: conditions.temperature, unit: '°C', icon: Thermometer, tone: 'moss' },
    { label: 'Humidity', value: conditions.humidity, unit: '%', icon: Droplets, tone: 'blue' },
    { label: 'Rainfall', value: conditions.rainfall, unit: 'mm', icon: CloudSun, tone: 'clay' },
    { label: 'Air quality', value: conditions.air_quality, unit: 'AQI', icon: Wind, tone: 'sage' },
  ]

  return (
    <section className="dashboard-section" id="conditions" aria-labelledby="conditions-title">
      <div className="section-heading">
        <div><span className="section-kicker">OBSERVATIONS</span><h2 id="conditions-title">Current conditions</h2></div>
        <span className="section-location">{conditions?.location ?? 'Conditions feed'}</span>
      </div>
      <ResourceState
        status={resource.status}
        errorMessage="Unable to load climate data. Please try again."
        onRetry={resource.retry}
        loadingMessage="Loading climate data..."
      >
        {values?.length ? (
          <div className="stat-grid">
            {values.map((item) => (
              <StatCard key={item.label} {...item} note={conditions.demo ? 'Sample condition' : 'Dataset condition'} />
            ))}
          </div>
        ) : (
          <div className="empty-state"><strong>No conditions available</strong><span>The conditions API returned no values.</span></div>
        )}
      </ResourceState>
      {resource.status === 'success' && conditions?.demo && (
        <p className="demo-note">Sample conditions for interface development. These values are not live observations.</p>
      )}
    </section>
  )
}

export default ConditionOverview
