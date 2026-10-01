import { AlertCircle, RefreshCw } from 'lucide-react'

function ResourceState({ status, errorMessage, onRetry, loadingMessage, children }) {
  if (status === 'loading') {
    return (
      <div className="resource-state loading-state" role="status" aria-live="polite">
        <span className="loading-spinner" aria-hidden="true" />
        <span>{loadingMessage}</span>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="resource-state error-state" role="alert">
        <AlertCircle size={19} aria-hidden="true" />
        <span>{errorMessage}</span>
        <button className="retry-button" type="button" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden="true" /> Retry
        </button>
      </div>
    )
  }

  return children
}

export default ResourceState
