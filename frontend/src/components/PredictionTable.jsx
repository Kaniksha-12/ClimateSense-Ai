import FilterTabs from './FilterTabs.jsx'
import ResourceState from './ResourceState.jsx'
import { filterByRiskType } from '../utils/riskFilter.js'

function PredictionTable({ resource, filter, onFilterChange }) {
  const predictions = resource.data?.items ?? []
  const filteredPredictions = filterByRiskType(predictions, filter)

  return (
    <section className="dashboard-section" id="predictions" aria-labelledby="predictions-title">
      <div className="section-heading prediction-heading">
        <div><span className="section-kicker">MODEL OUTPUT</span><h2 id="predictions-title">Predictions</h2></div>
        <FilterTabs value={filter} onChange={onFilterChange} label="Filter predictions by risk type" />
      </div>
      <ResourceState
        status={resource.status}
        errorMessage="Unable to load predictions. Please try again."
        onRetry={resource.retry}
        loadingMessage="Loading predictions..."
      >
        {filteredPredictions.length ? (
          <div className="table-scroll" role="region" aria-label="Prediction records" tabIndex="0">
            <table className="data-table">
              <thead><tr><th scope="col">Location</th><th scope="col">Risk type</th><th scope="col">Risk score</th><th scope="col">Risk level</th></tr></thead>
              <tbody>
                {filteredPredictions.map((prediction, index) => (
                  <tr key={`${prediction.location}-${prediction.risk_type}-${index}`}>
                    <td>{prediction.location}</td>
                    <td className="capitalize">{prediction.risk_type.replaceAll('_', ' ')}</td>
                    <td>{prediction.risk_score.toFixed(2)} <span className="score-total">/ 1.00</span></td>
                    <td><span className={`risk-level-badge ${prediction.risk_level.toLowerCase()}`}>{prediction.risk_level}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>{predictions.length ? 'No predictions for this category' : 'No predictions available'}</strong>
            <span>{predictions.length ? 'Choose another risk type to see its records.' : 'Awaiting ML integration. No model output is connected.'}</span>
          </div>
        )}
      </ResourceState>
      {resource.status === 'success' && predictions.length > 0 && <p className="demo-note">{resource.data?.source}</p>}
    </section>
  )
}

export default PredictionTable
