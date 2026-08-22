import { Activity, LoaderCircle, RefreshCw } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useWorkspaceActivity from "./useWorkspaceActivity";
import { formatActivityTime } from "./activityState";

export default function ActivityView() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspaceContext();
  const { events, loading, error, refresh } = useWorkspaceActivity(activeWorkspaceId);
  return <section className="product-view activity-view" aria-labelledby="activity-title">
    <header className="product-view__header"><div><span>HISTORIQUE DU WORKSPACE</span><h2 id="activity-title">Activité</h2><p>Les événements utiles et récents de {activeWorkspace?.name}, sans détails d’audit sensibles.</p></div><button type="button" className="view-refresh" onClick={refresh} aria-label="Actualiser l’activité"><RefreshCw size={17} /></button></header>
    {error && <div className="inline-error" role="alert"><span>{error}</span><button type="button" onClick={refresh}>Réessayer</button></div>}
    {loading ? <div className="document-loading" aria-live="polite"><LoaderCircle className="spin" /> Chargement de l’activité…</div> : events.length === 0 ? <div className="empty-state"><Activity size={30} /><h3>Le Workspace attend sa première action</h3><p>Les conversations, sources Knowledge et mémoires apparaîtront ici.</p></div> : <ol className="activity-timeline">{events.map((event) => <li key={event.id}><span className="activity-timeline__mark" aria-hidden="true" /><div><strong>{event.label}</strong><span>{formatActivityTime(event.created_at)}</span></div></li>)}</ol>}
  </section>;
}
