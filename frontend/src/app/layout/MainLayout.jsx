import Sidebar from "../../components/Sidebar";
import Header from "../../components/navigation/Header";
import VisualEnvironment from "../../components/visual/VisualEnvironment";
import MobileWorkspaceSelector from "../../components/workspace/MobileWorkspaceSelector";
import CommandPalette from "../../components/command/CommandPalette";
import ProductOnboarding from "../../features/onboarding/ProductOnboarding";
import useSessionContext from "../../hooks/useSessionContext";
import { useCallback, useEffect, useState } from "react";
import "./MainLayout.css";

export default function MainLayout({ children }) {
  const [isWorkspaceSelectorOpen, setWorkspaceSelectorOpen] = useState(false);
  const [isCommandOpen, setCommandOpen] = useState(false);
  const { session } = useSessionContext();
  const onboardingKey = `trident.ai.product_onboarding.${session?.user?.id || "anonymous"}`;
  const [isOnboardingOpen, setOnboardingOpen] = useState(false);
  useEffect(() => {
    try { setOnboardingOpen(window.localStorage.getItem(onboardingKey) !== "complete"); }
    catch { setOnboardingOpen(true); }
  }, [onboardingKey]);
  const closeCommand = useCallback(() => setCommandOpen(false), []);
  useEffect(() => {
    const openCommand = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen(true); }
    };
    window.addEventListener("keydown", openCommand);
    return () => window.removeEventListener("keydown", openCommand);
  }, []);
  return (
    <div className="main-layout">
      <VisualEnvironment />
      <Sidebar />

      <main className="main-content">
        <Header onOpenWorkspaces={() => setWorkspaceSelectorOpen(true)} onOpenCommand={() => setCommandOpen(true)} />
        {children}
      </main>
      <MobileWorkspaceSelector open={isWorkspaceSelectorOpen} onClose={() => setWorkspaceSelectorOpen(false)} />
      <CommandPalette open={isCommandOpen} onClose={closeCommand} />
      {isOnboardingOpen && <ProductOnboarding onClose={() => setOnboardingOpen(false)} />}
    </div>
  );
}
