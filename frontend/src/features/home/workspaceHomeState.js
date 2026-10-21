export function imageMetricValue({ loading, error, count }) {
  if (loading) return "…";
  if (error || !Number.isInteger(count) || count < 0) return "—";
  return count;
}
