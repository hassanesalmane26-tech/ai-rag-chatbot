import { MessageSquare, Shapes } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";

export default function ArtifactsView() {
  const { activeWorkspace, setActiveView } = useWorkspaceContext();
  return <section className="product-view artifacts-view" aria-labelledby="artifacts-title">
    <header className="product-view__header"><div><span>PRODUCTIONS DU WORKSPACE</span><h2 id="artifacts-title">Artefacts</h2><p>Les livrables produits avec Nova resteront distincts des fichiers importés dans {activeWorkspace?.name}.</p></div></header>
    <div className="artifact-boundary"><div className="artifact-boundary__visual"><Shapes size={34} /><span>0 artefact</span></div><div><h3>Aucun artefact généré</h3><p>TRIDENT AI n’enregistre pas automatiquement les réponses de Nova comme fichiers. Un artefact n’apparaîtra ici qu’après la création d’un livrable explicite et durable.</p><button type="button" className="ds-button" onClick={() => setActiveView("conversations")}><MessageSquare size={17} /> Ouvrir Nova</button></div></div>
  </section>;
}
