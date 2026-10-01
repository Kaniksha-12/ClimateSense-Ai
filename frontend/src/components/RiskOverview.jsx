import FilterTabs from './FilterTabs.jsx'
import ResourceState from './ResourceState.jsx'
import RiskCard from './RiskCard.jsx'
import { filterByRiskType } from '../utils/riskFilter.js'

function RiskOverview({ resource, filter, onFilterChange }) {
  const risks = resource.data?.items ?? []
  const filteredRisks = filterByRiskType(risks, filter)

  return (
    <section className="dashboard-section" id="risk-analysis" aria-labelledby="risk-title">
      <div className="section-heading risk-heading">
        <div><span className="section-kicker">RISK REGISTER</span><h2 id="risk-title">Risk analysis</h2></div>
        <FilterTabs value={filter} onChange={onFilterChange} label="Filter risk analysis by type" />
      </div>
      <ResourceState
        status={resource.status}
        errorMessage="Unable to load risk data. Please try again."
        onRetry={resource.retry}
        loadingMessage="Loading risk analysis..."
      >
        {filteredRisks.length ? (
          <div className="risk-grid">
            {filteredRisks.map((risk, index) => (
              <RiskCard key={`${risk.location}-${risk.risk_type}-${index}`} risk={risk} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>{risks.length ? 'No risks for this category' : 'No risk data available'}</strong>
            <span>{risks.length ? 'Choose another risk type to see its records.' : 'The risks API returned an empty list.'}</span>
          </div>
        )}
      </ResourceState>
      {resource.status === 'success' && resource.data?.demo && <p className="demo-note">Illustrative API records only. Risk scores are not real assessments.</p>}
    </section>
  )
}

export default RiskOverview
