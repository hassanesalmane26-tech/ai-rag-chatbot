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
  const requestVersion = useRef(0);
  useEffect(() => {
    if (!activeWorkspaceId) return undefined;
    const version = ++requestVersion.current;
    setOverview(null);
    getOverview(activeWorkspaceId).then((value) => { if (version === requestVersion.current) setOverview(value); }).catch(() => { if (version === requestVersion.current) setOverview(null); });
    return () => { requestVersion.current += 1; };
  }, [activeWorkspaceId]);
  const metrics = overview?.metrics || { conversations: 0, documents: 0, messages: 0, memories: 0 };
  return <section className="genesis-home"><GlassPanel className="genesis-hero" elevated><div className="genesis-hero__copy"><span>TRIDENT AI · INTELLIGENT WORKSPACE</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Votre espace central pour converser, structurer la connaissance et piloter la mémoire."}</p><div className="hero-actions"><Button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</Button><Button variant="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Enrichir Knowledge</Button></div></div><aside className="workspace-core" aria-label="Capacités actives du Workspace"><TridentMark /><span>WORKSPACE CORE</span><strong>INTELLIGENT CORE</strong><div><i /> Nova <i /> Knowledge <i /> Memory</div></aside></GlassPanel><div className="metric-grid"><MetricCard icon={MessageSquare} value={metrics.conversations} label="Conversations" /><MetricCard icon={BookOpen} value={metrics.documents} label="Sources" /><MetricCard icon={Sparkles} value={metrics.messages} label="Interactions IA" /><MetricCard icon={Brain} value={metrics.memories} label="Mémoires" /></div><GlassPanel className="genesis-next"><h3>Votre Workspace est opérationnel</h3><p>Knowledge alimente Nova et vos mémoires explicites restent sous votre contrôle, dans cet espace uniquement.</p></GlassPanel></section>;
}
