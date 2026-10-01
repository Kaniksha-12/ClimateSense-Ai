function StatCard({ label, value, unit, note, icon: Icon, tone }) {
  return (
    <article className={`stat-card ${tone}`}>
      <div className="stat-card-top">
        <span className="stat-icon"><Icon size={18} strokeWidth={1.8} aria-hidden="true" /></span>
        <span className="stat-label">{label}</span>
      </div>
      <div className="stat-value" aria-label={`${label}: ${value} ${unit}`}>
        {value}<span>{unit}</span>
      </div>
      <p className="stat-note">{note}</p>
    </article>
  )
}

export default StatCard
