function RiskCard({ risk }) {
  const level = risk.risk_level.toLowerCase()

  return (
    <article className={`risk-card risk-${level}`}>
      <div className="risk-card-top">
        <span className="risk-type">{risk.risk_type.replaceAll('_', ' ')}</span>
        <span className={`risk-level-badge ${level}`}>{risk.risk_level}</span>
      </div>
      <div className="risk-card-score"><strong>{risk.risk_score.toFixed(2)}</strong><span> / 1.00</span></div>
      <div className="risk-card-bottom"><span>{risk.location}</span><span>Risk score</span></div>
    </article>
  )
}

export default RiskCard
