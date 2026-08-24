import { useCallback, useRef } from "react";
import { BookOpen, Brain, Sparkles, X } from "lucide-react";
import useSessionContext from "../../hooks/useSessionContext";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";

export default function ProductOnboarding({ onClose }) {
  const { session } = useSessionContext();
  const { activeWorkspace, setActiveView } = useWorkspaceContext();
  const storageKey = `trident.ai.product_onboarding.${session?.user?.id || "anonymous"}`;
  const closeRef = useRef(null);
  const dialogRef = useRef(null);
  function complete(moduleId) {
    try { window.localStorage.setItem(storageKey, "complete"); } catch { /* Presentation-only state may be unavailable. */ }
    if (moduleId) setActiveView(moduleId);
    onClose();
  }
  const dismiss = useCallback(() => {
      try { window.localStorage.setItem(storageKey, "complete"); } catch { /* Presentation-only state may be unavailable. */ }
      onClose();
  }, [onClose, storageKey]);
  useModalFocus({ containerRef: dialogRef, initialRef: closeRef, onClose: dismiss });
  return <div className="onboarding-overlay"><section ref={dialogRef} className="product-onboarding ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="product-onboarding-title" tabIndex={-1}><button ref={closeRef} className="product-onboarding__close" type="button" aria-label="Ignorer la présentation" onClick={() => complete()}><X size={18} /></button><span>BIENVENUE DANS TRIDENT AI</span><h2 id="product-onboarding-title">Votre Workspace est votre environnement intelligent.</h2><p>{activeWorkspace?.name} réunit Nova, vos sources Knowledge et votre Memory explicite dans un même environnement sécurisé.</p><div className="onboarding-flow" aria-label="Votre Workspace relie Nova, Knowledge et Memory"><strong>VOTRE WORKSPACE</strong><i /><span>Nova</span><span>Knowledge</span><span>Memory</span></div><div className="onboarding-capabilities"><article><Sparkles size={21} /><strong>Nova</strong><span>Converse avec le contexte autorisé du Workspace.</span></article><article><BookOpen size={21} /><strong>Knowledge</strong><span>Ajoute les sources privées qui enrichissent les réponses.</span></article><article><Brain size={21} /><strong>Memory</strong><span>Conserve uniquement les repères que vous contrôlez.</span></article></div><div className="onboarding-actions"><button className="ds-button" type="button" onClick={() => complete("conversations")}>Commencer avec Nova</button><button className="ds-button ds-button--secondary" type="button" onClick={() => complete("knowledge")}>Ajouter une source</button><button type="button" onClick={() => complete()}>Explorer librement</button></div></section></div>;
}
