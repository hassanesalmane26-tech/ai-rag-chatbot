export default function MetricCard({ icon: Icon, value, label }) {
  return <article className="metric-card ds-glass-panel">
    <Icon size={18} aria-hidden="true" />
    <strong>{value}</strong>
    <span>{label}</span>
  </article>;
}
