import Sidebar from "../../components/Sidebar";
import Header from "../../components/navigation/Header";
import VisualEnvironment from "../../components/visual/VisualEnvironment";
import MobileWorkspaceSelector from "../../components/workspace/MobileWorkspaceSelector";
import { useState } from "react";
import "./MainLayout.css";

export default function MainLayout({ children }) {
  const [isWorkspaceSelectorOpen, setWorkspaceSelectorOpen] = useState(false);
  return (
    <div className="main-layout">
      <VisualEnvironment />
      <Sidebar />

      <main className="main-content">
        <Header onOpenWorkspaces={() => setWorkspaceSelectorOpen(true)} />
        {children}
      </main>
      <MobileWorkspaceSelector open={isWorkspaceSelectorOpen} onClose={() => setWorkspaceSelectorOpen(false)} />
    </div>
  );
}
