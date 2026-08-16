import { Suspense } from "react";
import useWorkspaceContext from "../../../hooks/useWorkspaceContext";
import { workspaceModule } from "../../../app/modules/registry";

export default function WorkspaceRouter() {
  const { activeView, activeWorkspace, loading, error, refreshWorkspaces } = useWorkspaceContext();
  if (loading && !activeWorkspace) return <section className="empty-state" aria-live="polite"><h2>Préparation du Workspace</h2><p>Chargement de votre environnement TRIDENT…</p></section>;
  if (error && !activeWorkspace) return <section className="empty-state" role="alert"><h2>Workspace indisponible</h2><p>{error}</p><button type="button" onClick={() => refreshWorkspaces().catch(() => {})}>Réessayer</button></section>;
  if (!activeWorkspace) return <section className="empty-state"><h2>Aucun Workspace actif</h2><p>Créez ou sélectionnez un Workspace pour continuer.</p></section>;
  const ModuleView = workspaceModule(activeView).view;
  return <Suspense fallback={<section className="empty-state" aria-live="polite"><h2>Ouverture du module</h2><p>Préparation du Workspace…</p></section>}><ModuleView key={`${activeWorkspace.id}:${activeView}`} workspaceId={activeWorkspace.id} /></Suspense>;
}
