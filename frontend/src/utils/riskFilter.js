export function filterByRiskType(records, selectedType) {
  if (selectedType === 'all') return records
  return records.filter((record) => record.risk_type === selectedType)
}
