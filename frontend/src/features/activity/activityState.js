export function formatActivityTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date indisponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
