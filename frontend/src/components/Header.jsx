import { Activity, RefreshCw } from 'lucide-react'

function Header({ apiStatus, onRetry }) {
  const statusLabel = {
    connecting: 'Checking backend',
    connected: 'Backend connected',
    unavailable: 'Backend unavailable',
  }[apiStatus]

  return (
    <header className="app-header">
      <a className="brand" href="#overview" aria-label="ClimateSense AI overview">
        <span className="brand-mark"><Activity size={20} strokeWidth={2.2} aria-hidden="true" /></span>
        <span className="brand-copy">
          <strong>ClimateSense <span>AI</span></strong>
          <small>AI-powered climate risk intelligence</small>
        </span>
      </a>
      <div className="header-meta">
        <span className="demo-badge"><span aria-hidden="true" /> DEMO DATA</span>
        <div className={`connection-status ${apiStatus}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          <span>{statusLabel}</span>
          {apiStatus === 'unavailable' && (
            <button className="status-retry" type="button" onClick={onRetry} aria-label="Retry backend health check" title="Retry connection">
              <RefreshCw size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
