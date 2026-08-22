import { useEffect, useRef, useState } from "react";
import { BookOpen, Brain, MessageSquare, Sparkles } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { getOverview } from "../../services/api";
import TridentMark from "../../components/visual/TridentMark";
import Button from "../../components/ui/Button";
import GlassPanel from "../../components/ui/GlassPanel";
import MetricCard from "../../components/ui/MetricCard";

export default function WorkspaceHome() {
  const { activeWorkspace, activeWorkspaceId, setActiveView } = useWorkspaceContext();
  const [overview, setOverview] = useState(null);
  const [overviewState, setOverviewState] = useState("loading");
  const requestVersion = useRef(0);
  useEffect(() => {
    if (!activeWorkspaceId) return undefined;
    const version = ++requestVersion.current;
    setOverview(null);
    setOverviewState("loading");
    getOverview(activeWorkspaceId).then((value) => { if (version === requestVersion.current) { setOverview(value); setOverviewState("ready"); } }).catch(() => { if (version === requestVersion.current) { setOverview(null); setOverviewState("error"); } });
    return () => { requestVersion.current += 1; };
  }, [activeWorkspaceId]);
  const metrics = overview?.metrics || { conversations: 0, documents: 0, messages: 0, memories: 0 };
  const metricValue = (value) => overviewState === "loading" ? "…" : overviewState === "error" ? "—" : value;
  return <section className="workspace-home"><GlassPanel className="workspace-hero" elevated><div className="workspace-hero__copy"><span>TRIDENT AI · INTELLIGENT WORKSPACE</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Votre espace central pour converser, structurer Knowledge et piloter Memory."}</p><div className="hero-actions"><Button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</Button><Button variant="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Enrichir Knowledge</Button></div></div><aside className="workspace-core" aria-label="Capacités actives du Workspace"><TridentMark /><span>WORKSPACE CORE</span><strong>INTELLIGENT CORE</strong><div><i /> Nova <i /> Knowledge <i /> Memory</div></aside></GlassPanel><div className="metric-grid" aria-busy={overviewState === "loading"}><MetricCard icon={MessageSquare} value={metricValue(metrics.conversations)} label="Conversations" /><MetricCard icon={BookOpen} value={metricValue(metrics.documents)} label="Sources" /><MetricCard icon={Sparkles} value={metricValue(metrics.messages)} label="Interactions IA" /><MetricCard icon={Brain} value={metricValue(metrics.memories)} label="Mémoires" /></div><GlassPanel className="workspace-next"><h3>{overviewState === "error" ? "Vue d’ensemble temporairement indisponible" : "Votre Workspace est opérationnel"}</h3><p>{overviewState === "error" ? "Nova, Knowledge et Memory restent accessibles depuis la navigation." : "Knowledge alimente Nova et vos mémoires explicites restent sous votre contrôle, dans cet espace uniquement."}</p></GlassPanel></section>;
}
