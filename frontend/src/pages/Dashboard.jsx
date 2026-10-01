import { useState } from 'react'
import { MapPin } from 'lucide-react'
import AlertList from '../components/AlertList.jsx'
import ConditionOverview from '../components/ConditionOverview.jsx'
import Header from '../components/Header.jsx'
import MapPanel from '../components/MapPanel.jsx'
import Navigation from '../components/Navigation.jsx'
import PredictionTable from '../components/PredictionTable.jsx'
import RiskOverview from '../components/RiskOverview.jsx'
import useApiResource from '../hooks/useApiResource.js'
import {
  getAlerts,
  getConditions,
  getGIS,
  getHealth,
  getPredictions,
  getRisks,
} from '../services/api.js'

function Dashboard() {
  const health = useApiResource(getHealth)
  const gis = useApiResource(getGIS)
  const conditions = useApiResource(getConditions)
  const predictions = useApiResource(getPredictions)
  const risks = useApiResource(getRisks)
  const alerts = useApiResource(getAlerts)
  const [riskFilter, setRiskFilter] = useState('all')

  const apiStatus = health.status === 'loading'
    ? 'connecting'
    : health.data?.status === 'ok' ? 'connected' : 'unavailable'

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to dashboard</a>
      <Header apiStatus={apiStatus} onRetry={health.retry} />
      <div className="dashboard-layout">
        <aside className="sidebar">
          <span className="sidebar-label">WORKSPACE</span>
          <Navigation />
          <div className="sidebar-note">
            <span className="sidebar-note-mark"><MapPin size={15} aria-hidden="true" /></span>
            <span><strong>{conditions.data?.location ?? 'Regional view'}</strong><small>Sample location</small></span>
          </div>
        </aside>

        <main className="main-content" id="main-content">
          <section className="intro" id="overview" aria-labelledby="overview-title">
            <div className="intro-copy">
              <span className="section-kicker">CLIMATE INTELLIGENCE / OVERVIEW</span>
              <h1 id="overview-title">A clearer view of climate risk.</h1>
              <p>Conditions, model output, and risk indicators gathered in one place.</p>
            </div>
            <span className="sample-stamp"><span aria-hidden="true" /> DEMONSTRATION WORKSPACE</span>
          </section>

          <div className="dashboard-content">
            <ConditionOverview resource={conditions} />
            <RiskOverview resource={risks} filter={riskFilter} onFilterChange={setRiskFilter} />
            <PredictionTable resource={predictions} filter={riskFilter} onFilterChange={setRiskFilter} />
            <MapPanel resource={gis} />
            <AlertList resource={alerts} />
          </div>
          <footer className="page-footer">
            <span>ClimateSense AI <span className="footer-divider">/</span> Member 4 dashboard</span>
            <span>Sample values only · not live monitoring</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default Dashboard
