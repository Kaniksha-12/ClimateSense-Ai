import { AlertTriangle, ShieldCheck } from 'lucide-react'
import ResourceState from './ResourceState.jsx'

function AlertList({ resource }) {
  const alerts = resource.data?.items ?? []

  return (
    <section className="dashboard-section" id="alerts" aria-labelledby="alerts-title">
      <div className="section-heading">
        <div><span className="section-kicker">NOTICE FEED</span><h2 id="alerts-title">Alerts</h2></div>
        {resource.status === 'success' && <span className="section-count">{alerts.length} {alerts.length === 1 ? 'alert' : 'alerts'}</span>}
      </div>
      <ResourceState
        status={resource.status}
        errorMessage="Unable to load alerts. Please try again."
        onRetry={resource.retry}
        loadingMessage="Loading alerts..."
      >
        {alerts.length ? (
          <div className="alert-list">
            {alerts.map((alert) => (
              <article className={`alert-card alert-${alert.severity.toLowerCase()}`} key={alert.id}>
                <span className="alert-icon" aria-hidden="true"><AlertTriangle size={18} /></span>
                <div className="alert-content">
                  <div className="alert-title-row">
                    <h3>{alert.location} <span>·</span> <span className="capitalize">{alert.risk_type.replaceAll('_', ' ')}</span></h3>
                    <span className={`risk-level-badge ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</span>
                  </div>
                  <p>{alert.message}</p>
                  <span className="alert-meta">Severity: <strong>{alert.severity}</strong></span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state alert-empty-state">
            <ShieldCheck size={20} aria-hidden="true" />
            <strong>No active alerts</strong>
            <span>{resource.data?.demo ? 'No other sample alerts are available.' : 'The alert feed returned no active notices.'}</span>
          </div>
        )}
      </ResourceState>
      {resource.status === 'success' && alerts.length > 0 && <p className="demo-note">{resource.data?.source}</p>}
    </section>
  )
}

export default AlertList
