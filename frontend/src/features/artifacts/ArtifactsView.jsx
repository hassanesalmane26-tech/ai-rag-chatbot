import { MessageSquare, Shapes } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useWorkspaceImages from "../images/useWorkspaceImages";
import ImageCard from "../images/ImageCard";
import { artifactSurfaceState } from "./artifactState";

export default function ArtifactsView() {
  const { activeWorkspace, activeWorkspaceId, openNovaConversation, setActiveView } = useWorkspaceContext();
  const { images, capability, loading, error, refresh } = useWorkspaceImages(activeWorkspaceId);
  return <section className="product-view artifacts-view" data-artifact-state={artifactSurfaceState({ images, loading, error })} aria-labelledby="artifacts-title" aria-busy={loading}>
    <header className="product-view__header"><div><span>PRODUCTIONS DU WORKSPACE</span><h2 id="artifacts-title">Artefacts</h2><p>Les images créées avec Nova dans {activeWorkspace?.name}. Vos fichiers importés restent dans Fichiers.</p></div><button type="button" className="ds-button ds-button--secondary" onClick={refresh}>Actualiser</button></header>
    {loading ? <p role="status">Chargement des créations…</p> : error ? <div role="alert"><p>{error}</p><button type="button" onClick={refresh}>Réessayer</button></div> : images.length ? <div className="artifact-grid">{images.map((image) => <div key={image.id}><ImageCard image={image} workspaceId={activeWorkspaceId} available={capability?.available} onChange={refresh} /><button type="button" className="ds-button ds-button--secondary" onClick={() => openNovaConversation({ id: image.conversation_id })}><MessageSquare size={16} /> Conversation source</button></div>)}</div> : <div className="artifact-boundary"><Shapes size={32} /><div><h3>Un espace pour vos créations</h3><p>{capability?.available ? "Créez votre première image avec Nova. Elle sera conservée ici, avec sa conversation." : "La création d’images n’est pas configurée. Aucune création n’est simulée."}</p><button type="button" className="ds-button" onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</button></div></div>}
  </section>;
}
