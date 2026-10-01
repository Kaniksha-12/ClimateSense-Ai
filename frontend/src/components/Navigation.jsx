import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CloudSun, Layers3, ShieldCheck, Sparkles } from 'lucide-react'

const sections = [
  { label: 'Overview', href: '#overview', icon: Activity },
  { label: 'Conditions', href: '#conditions', icon: CloudSun },
  { label: 'Predictions', href: '#predictions', icon: Sparkles },
  { label: 'Risk analysis', href: '#risk-analysis', icon: ShieldCheck },
  { label: 'GIS map', href: '#gis-map', icon: Layers3 },
  { label: 'Alerts', href: '#alerts', icon: AlertTriangle },
]

function Navigation() {
  const [activeSection, setActiveSection] = useState(() => window.location.hash || '#overview')

  useEffect(() => {
    const updateActiveSection = () => setActiveSection(window.location.hash || '#overview')
    window.addEventListener('hashchange', updateActiveSection)
    return () => window.removeEventListener('hashchange', updateActiveSection)
  }, [])

  return (
    <nav className="primary-nav" aria-label="Dashboard sections">
      {sections.map(({ label, href, icon: Icon }) => (
        <a
          aria-current={activeSection === href ? 'location' : undefined}
          className={`nav-item${activeSection === href ? ' active' : ''}`}
          href={href}
          key={href}
        >
          <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
          <span>{label}</span>
        </a>
      ))}
    </nav>
  )
}

export default Navigation
