import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, BookOpen, Brain, Files, MessageSquare, Shapes, Sparkles } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { getOverview } from "../../services/api";
import TridentMark from "../../components/visual/TridentMark";
import Button from "../../components/ui/Button";
import GlassPanel from "../../components/ui/GlassPanel";
import MetricCard from "../../components/ui/MetricCard";
import useWorkspaceActivity from "../activity/useWorkspaceActivity";
import { formatActivityTime } from "../activity/activityState";

export default function WorkspaceHome() {
  const { activeWorkspace, activeWorkspaceId, setActiveView } = useWorkspaceContext();
  const [overview, setOverview] = useState(null);
  const [overviewState, setOverviewState] = useState("loading");
  const requestVersion = useRef(0);
  const { events, loading: activityLoading, error: activityError, refresh: refreshActivity } = useWorkspaceActivity(activeWorkspaceId);
  const refreshOverview = useCallback(() => {
    if (!activeWorkspaceId) return;
    const version = ++requestVersion.current;
    setOverviewState("loading");
    getOverview(activeWorkspaceId).then((value) => {
      if (version === requestVersion.current) { setOverview(value); setOverviewState("ready"); }
    }).catch(() => { if (version === requestVersion.current) setOverviewState("error"); });
  }, [activeWorkspaceId]);
  useEffect(() => { setOverview(null); refreshOverview(); return () => { requestVersion.current += 1; }; }, [refreshOverview]);
  const metrics = overview?.metrics || { conversations: 0, documents: 0, messages: 0, memories: 0 };
  const metricValue = (value) => overviewState === "loading" ? "…" : overviewState === "error" ? "—" : value;
  return <section className="workspace-home">
    <GlassPanel className="workspace-hero" elevated><div className="workspace-hero__copy"><span>TRIDENT AI · INTELLIGENT WORKSPACE</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Votre espace central pour converser, structurer Knowledge et piloter Memory."}</p><div className="hero-actions"><Button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</Button><Button variant="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Ajouter à Knowledge</Button></div></div><aside className="workspace-core" aria-label="État des capacités du Workspace"><TridentMark /><span>WORKSPACE CORE</span><strong>INTELLIGENT CORE</strong><div><i /> Nova <i /> Knowledge <i /> Memory <i /> Files <i /> Artifacts</div></aside></GlassPanel>
    <div className="metric-grid metric-grid--v1" aria-busy={overviewState === "loading"}><MetricCard icon={MessageSquare} value={metricValue(metrics.conversations)} label="Conversations" /><MetricCard icon={BookOpen} value={metricValue(metrics.documents)} label="Sources Knowledge" /><MetricCard icon={Sparkles} value={metricValue(metrics.messages)} label="Interactions IA" /><MetricCard icon={Brain} value={metricValue(metrics.memories)} label="Mémoires" /><MetricCard icon={Files} value={metricValue(metrics.documents)} label="Files" /><MetricCard icon={Shapes} value={metricValue(0)} label="Artifacts" /></div>
    {overviewState === "error" && <div className="inline-error" role="alert"><span>Les métriques ne peuvent pas être synchronisées. Vos modules restent disponibles.</span><button type="button" onClick={refreshOverview}>Réessayer</button></div>}
    <div className="home-context-grid"><GlassPanel className="workspace-intelligence"><span>WORKSPACE INTELLIGENCE</span><h3>Contexte disponible pour Nova</h3><dl><div><dt>Knowledge</dt><dd>{metricValue(metrics.documents)} source(s)</dd></div><div><dt>Memory active</dt><dd>{metricValue(metrics.memories)}</dd></div><div><dt>Activité récente</dt><dd>{activityLoading ? "…" : events.length}</dd></div></dl><p>Nova utilise uniquement le contexte autorisé de ce Workspace.</p><Button onClick={() => setActiveView("conversations")}><Sparkles size={17} /> Ask Nova</Button></GlassPanel><GlassPanel className="workspace-activity-preview"><header><div><span>WORKSPACE ACTIVITY</span><h3>Derniers mouvements</h3></div><button type="button" onClick={() => setActiveView("activity")}>Tout voir</button></header>{activityError ? <div className="home-activity-state" role="alert">Activité indisponible. <button type="button" onClick={refreshActivity}>Réessayer</button></div> : activityLoading ? <div className="home-activity-state" aria-live="polite">Synchronisation…</div> : events.length === 0 ? <div className="home-activity-state"><Activity size={20} /> Votre prochaine action apparaîtra ici.</div> : <ol>{events.slice(0, 4).map((event) => <li key={event.id}><i /><div><strong>{event.label}</strong><span>{formatActivityTime(event.created_at)}</span></div></li>)}</ol>}</GlassPanel></div>
  </section>;
}
