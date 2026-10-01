const filters = [
  { value: 'all', label: 'All' },
  { value: 'flood', label: 'Flood' },
  { value: 'drought', label: 'Drought' },
  { value: 'heatwave', label: 'Heatwave' },
  { value: 'air_quality', label: 'Air Quality' },
]

function FilterTabs({ value, onChange, label = 'Filter by risk type' }) {
  return (
    <div className="filter-tabs" role="group" aria-label={label}>
      {filters.map((filter) => (
        <button
          aria-pressed={value === filter.value}
          className={value === filter.value ? 'selected' : ''}
          key={filter.value}
          onClick={() => onChange(filter.value)}
          type="button"
        >
          {filter.label}
        </button>
      ))}
    </div>
  )
}

export default FilterTabs
