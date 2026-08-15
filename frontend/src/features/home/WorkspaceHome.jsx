import { useEffect, useState } from "react";
import { BookOpen, MessageSquare, Sparkles } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { getOverview } from "../../services/api";
import TridentMark from "../../components/visual/TridentMark";

export default function WorkspaceHome() {
  const { activeWorkspace, activeWorkspaceId, setActiveView } = useWorkspaceContext();
  const [overview, setOverview] = useState(null);
  useEffect(() => { if (!activeWorkspaceId) return; getOverview(activeWorkspaceId).then(setOverview).catch(() => setOverview(null)); }, [activeWorkspaceId]);
  const metrics = overview?.metrics || { conversations: 0, documents: 0, messages: 0 };
  return <section className="genesis-home"><div className="genesis-hero"><div className="genesis-hero__copy"><span>WORKSPACE INTELLIGENT</span><h2>{activeWorkspace?.name || "Chargement du Workspace"}</h2><p>{activeWorkspace?.description || "Centralisez vos conversations et vos connaissances."}</p><div className="hero-actions"><button onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir les conversations</button><button className="secondary" onClick={() => setActiveView("knowledge")}><BookOpen size={17} /> Ajouter des connaissances</button></div></div><aside className="workspace-core" aria-label="Capacités actives du Workspace"><TridentMark /><span>WORKSPACE CORE</span><strong>GENESIS</strong><div><i /> Conversations <i /> Knowledge</div></aside></div><div className="metric-grid"><article><MessageSquare /><strong>{metrics.conversations}</strong><span>Conversations</span></article><article><BookOpen /><strong>{metrics.documents}</strong><span>Documents</span></article><article><Sparkles /><strong>{metrics.messages}</strong><span>Interactions IA</span></article></div><section className="genesis-next"><h3>Votre Workspace est prêt</h3><p>Ajoutez des documents dans Knowledge, puis interrogez-les depuis une conversation. Toutes les données restent rattachées à cet espace.</p></section></section>;
}
