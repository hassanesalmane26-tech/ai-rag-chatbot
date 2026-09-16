import { MessageSquare, Shapes } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { artifactCapability } from "./artifactState";

export default function ArtifactsView() {
  const { activeWorkspace, setActiveView } = useWorkspaceContext();
  return <section className="product-view artifacts-view" aria-labelledby="artifacts-title" data-artifact-state={artifactCapability.state}>
    <header className="product-view__header"><div><span>PRODUCTIONS DU WORKSPACE</span><h2 id="artifacts-title">Artefacts</h2><p>Cette surface reste distincte des fichiers importés dans {activeWorkspace?.name}.</p></div></header>
    <div className="artifact-boundary"><div className="artifact-boundary__visual"><Shapes size={34} /><span>Capacité indisponible</span></div><div><h3>Aucun stockage d’artefacts actif</h3><p>Cette édition ne crée ni ne persiste actuellement d’artefacts. Les réponses Nova restent dans leurs conversations.</p><button type="button" className="ds-button" onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</button></div></div>
  </section>;
}
