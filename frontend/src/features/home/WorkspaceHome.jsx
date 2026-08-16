import { useEffect, useState } from "react";
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
  useEffect(() => { if (!activeWorkspaceId) return; getOverview(activeWorkspaceId).then(setOverview).catch(() => setOverview(null)); }, [activeWorkspaceId]);
  const metrics = overview?.metrics || { conversations: 0, documents: 0, messages: 0, memories: 0 };
  return <section className="genesis-home"><GlassPanel className="genesis-hero" elevated><div className="genesis-hero__copy"><span>WORKSPACE INTELLIGENT</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Centralisez vos conversations et vos connaissances."}</p><div className="hero-actions"><Button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir les conversations</Button><Button variant="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Ajouter des connaissances</Button></div></div><aside className="workspace-core" aria-label="Capacités actives du Workspace"><TridentMark /><span>WORKSPACE CORE</span><strong>GENESIS</strong><div><i /> Conversations <i /> Knowledge <i /> Memory</div></aside></GlassPanel><div className="metric-grid"><MetricCard icon={MessageSquare} value={metrics.conversations} label="Conversations" /><MetricCard icon={BookOpen} value={metrics.documents} label="Documents" /><MetricCard icon={Sparkles} value={metrics.messages} label="Interactions IA" /><MetricCard icon={Brain} value={metrics.memories} label="Mémoires explicites" /></div><GlassPanel className="genesis-next"><h3>Votre Workspace est prêt</h3><p>Ajoutez des documents dans Knowledge, puis interrogez-les depuis une conversation. Toutes les données restent rattachées à cet espace.</p></GlassPanel></section>;
}
