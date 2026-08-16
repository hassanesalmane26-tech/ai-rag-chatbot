import useWorkspaceContext from "../../../hooks/useWorkspaceContext";
import WorkspaceHome from "../../home/WorkspaceHome";
import ConversationsView from "../../chat/ConversationsView";
import DocumentsView from "../../documents/DocumentsView";
import MemoryView from "../../memory/MemoryView";

export default function WorkspaceRouter() {
  const { activeView, activeWorkspace, loading, error, refreshWorkspaces } = useWorkspaceContext();
  if (loading && !activeWorkspace) return <section className="empty-state" aria-live="polite"><h2>Préparation du Workspace</h2><p>Chargement de votre environnement TRIDENT…</p></section>;
  if (error && !activeWorkspace) return <section className="empty-state" role="alert"><h2>Workspace indisponible</h2><p>{error}</p><button type="button" onClick={() => refreshWorkspaces().catch(() => {})}>Réessayer</button></section>;
  if (!activeWorkspace) return <section className="empty-state"><h2>Aucun Workspace actif</h2><p>Créez ou sélectionnez un Workspace pour continuer.</p></section>;
  if (activeView === "conversations") return <ConversationsView key={activeWorkspace.id} workspaceId={activeWorkspace.id} />;
  if (activeView === "knowledge") return <DocumentsView />;
  if (activeView === "memory") return <MemoryView />;
  return <WorkspaceHome />;
}
