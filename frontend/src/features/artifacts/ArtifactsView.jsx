import { MessageSquare, Shapes } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";

export default function ArtifactsView() {
  const { activeWorkspace, setActiveView } = useWorkspaceContext();
  return <section className="product-view artifacts-view" aria-labelledby="artifacts-title">
    <header className="product-view__header"><div><span>AI-GENERATED OUTPUTS</span><h2 id="artifacts-title">Artifacts</h2><p>Les livrables générés par Nova seront séparés des fichiers importés dans {activeWorkspace?.name}.</p></div></header>
    <div className="artifact-boundary"><div className="artifact-boundary__visual"><Shapes size={34} /><span>0 artifact</span></div><div><h3>Aucun Artifact généré</h3><p>TRIDENT AI V1 n’enregistre pas automatiquement les réponses de Nova comme fichiers. Cette surface restera vide tant qu’un livrable explicite n’aura pas de contrat de génération durable.</p><button type="button" className="ds-button" onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</button></div></div>
  </section>;
}
