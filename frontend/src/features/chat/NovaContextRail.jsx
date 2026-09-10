import { Activity, BookOpen, Brain, LoaderCircle, MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getOverview } from "../../services/api";
import useWorkspaceActivity from "../activity/useWorkspaceActivity";
import { formatActivityTime } from "../activity/activityState";

export default function NovaContextRail({ workspace, workspaceId }) {
  const [overview, setOverview] = useState(null);
  const [overviewState, setOverviewState] = useState("loading");
  const requestRef = useRef(0);
  const { events, loading: activityLoading, error: activityError } = useWorkspaceActivity(workspaceId);

  useEffect(() => {
    const request = ++requestRef.current;
    setOverview(null);
    setOverviewState("loading");
    getOverview(workspaceId).then((value) => {
      if (request === requestRef.current) { setOverview(value); setOverviewState("ready"); }
    }).catch(() => {
      if (request === requestRef.current) setOverviewState("error");
    });
    return () => { requestRef.current += 1; };
  }, [workspaceId]);

  const metrics = overview?.metrics;
  const value = (metric) => overviewState === "loading" ? "…" : overviewState === "error" ? "—" : metric ?? "—";

  return <aside className="nova-context-rail" aria-label="Contexte réel du Workspace">
    <section className="nova-context-rail__workspace">
      <span>WORKSPACE ACTIF</span>
      <strong>{workspace?.name || "Workspace"}</strong>
      <p><i />{overviewState === "ready" ? "Contexte synchronisé" : overviewState === "loading" ? "Synchronisation…" : "Contexte indisponible"}</p>
    </section>
    <section className="nova-context-rail__systems" aria-busy={overviewState === "loading"}>
      <header><span>CONTEXTE NOVA</span><small>Données réelles</small></header>
      <dl>
        <div><dt><BookOpen size={15} />Knowledge</dt><dd>{value(metrics?.documents)}</dd></div>
        <div><dt><Brain size={15} />Memory</dt><dd>{value(metrics?.memories)}</dd></div>
        <div><dt><MessageSquare size={15} />Conversations</dt><dd>{value(metrics?.conversations)}</dd></div>
      </dl>
    </section>
    <section className="nova-context-rail__activity">
      <header><span>ACTIVITÉ RÉCENTE</span><Activity size={15} /></header>
      {activityLoading ? <p aria-live="polite"><LoaderCircle className="spin" size={14} /> Synchronisation…</p> : activityError ? <p>Activité indisponible.</p> : events.length === 0 ? <p>Aucune activité récente.</p> : <ol>{events.slice(0, 3).map((event) => <li key={event.id}><i /><div><strong>{event.label}</strong><small>{formatActivityTime(event.created_at)}</small></div></li>)}</ol>}
    </section>
  </aside>;
}
