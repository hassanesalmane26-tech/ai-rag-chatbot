import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowUpRight, BookOpen, Brain, Files, MessageSquare, Shapes, Sparkles } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { getOverview } from "../../services/api";
import TridentMark from "../../components/visual/TridentMark";
import Button from "../../components/ui/Button";
import GlassPanel from "../../components/ui/GlassPanel";
import MetricCard from "../../components/ui/MetricCard";
import useWorkspaceActivity from "../activity/useWorkspaceActivity";
import { formatActivityTime } from "../activity/activityState";

const coreSystems = ["Nova", "Knowledge", "Memory", "Fichiers", "Artefacts"];

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
  return <section className="workspace-home workspace-home--definitive">
    <div className="workspace-home__primary">
    <GlassPanel className="workspace-hero" elevated>
      <div className="workspace-hero__copy"><span>TRIDENT AI · WORKSPACE INTELLIGENT</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Votre environnement central pour travailler avec Nova, structurer Knowledge et piloter Memory."}</p><div className="hero-actions"><Button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</Button><Button variant="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Ajouter à Knowledge</Button></div></div>
      <aside className="workspace-core" aria-label="Systèmes connectés du Workspace"><div className="workspace-core__identity"><TridentMark /><span>INTELLIGENT CORE</span><strong>Workspace actif</strong></div><div className="workspace-core__orbit" aria-hidden="true">{coreSystems.map((system) => <span key={system}><i />{system}</span>)}</div></aside>
    </GlassPanel>
    <div className="metric-grid metric-grid--v1" aria-busy={overviewState === "loading"}><MetricCard icon={MessageSquare} value={metricValue(metrics.conversations)} label="Conversations" /><MetricCard icon={BookOpen} value={metricValue(metrics.documents)} label="Sources Knowledge" /><MetricCard icon={Sparkles} value={metricValue(metrics.messages)} label="Interactions IA" /><MetricCard icon={Brain} value={metricValue(metrics.memories)} label="Mémoires" /><MetricCard icon={Files} value={metricValue(metrics.documents)} label="Fichiers" /><MetricCard icon={Shapes} value={metricValue(0)} label="Artefacts" /></div>
    {overviewState === "error" && <div className="inline-error" role="alert"><span>Les métriques ne peuvent pas être synchronisées. Vos systèmes restent disponibles.</span><button type="button" onClick={refreshOverview}>Réessayer</button></div>}
    <GlassPanel className="workspace-system-map" aria-label="Systèmes intelligents disponibles"><header><div><span>ENVIRONNEMENT INTELLIGENT</span><h3>Un Workspace, plusieurs systèmes connectés</h3></div><TridentMark /></header><div>{coreSystems.map((system, index) => <button key={system} type="button" onClick={() => setActiveView(["conversations", "knowledge", "memory", "files", "artifacts"][index])}><i /><span>{system}</span><ArrowUpRight size={15} /></button>)}</div></GlassPanel>
    </div>
    <aside className="workspace-home__rail" aria-label="Contexte intelligent du Workspace">
      <GlassPanel className="workspace-intelligence"><span>WORKSPACE INTELLIGENCE</span><h3>Ce que Nova comprend ici</h3><dl><div><dt>Knowledge</dt><dd>{metricValue(metrics.documents)} source(s)</dd></div><div><dt>Memory explicite</dt><dd>{metricValue(metrics.memories)}</dd></div><div><dt>Fichiers disponibles</dt><dd>{metricValue(metrics.documents)}</dd></div><div><dt>Activité récente</dt><dd>{activityLoading ? "…" : events.length}</dd></div></dl><p>Nova utilise uniquement le contexte autorisé de ce Workspace.</p><Button onClick={() => setActiveView("conversations")}><Sparkles size={17} /> Demander à Nova</Button></GlassPanel>
      <GlassPanel className="workspace-activity-preview"><header><div><span>ACTIVITÉ DU WORKSPACE</span><h3>Derniers mouvements</h3></div><button type="button" onClick={() => setActiveView("activity")}>Tout voir</button></header>{activityError ? <div className="home-activity-state" role="alert">Activité indisponible. <button type="button" onClick={refreshActivity}>Réessayer</button></div> : activityLoading ? <div className="home-activity-state" aria-live="polite">Synchronisation…</div> : events.length === 0 ? <div className="home-activity-state"><Activity size={20} /> Votre prochaine action apparaîtra ici.</div> : <ol>{events.slice(0, 4).map((event) => <li key={event.id}><i /><div><strong>{event.label}</strong><span>{formatActivityTime(event.created_at)}</span></div></li>)}</ol>}</GlassPanel>
      <GlassPanel className="workspace-rail-status"><span>TRIDENT AI</span><strong>{activeWorkspace?.name || "Workspace"}</strong><p><i /> Contexte serveur actif</p><small>Les données affichées restent limitées à ce Workspace.</small></GlassPanel>
    </aside>
  </section>;
}
