import {
  CircleUserRound,
  PanelsTopLeft,
  Search,
} from "lucide-react";
import TridentMark from "../visual/TridentMark";
import IconButton from "../ui/IconButton";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { workspaceModule } from "../../app/modules/registry";

export default function Header({
  onOpenWorkspaces,
  onOpenCommand,
}) {
  const { activeWorkspace, activeView, setActiveView } = useWorkspaceContext();
  const currentModule = workspaceModule(activeView);
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo"><TridentMark label="TRIDENT AI" /></div>

        <div>
          <p className="topbar-breadcrumb">Workspace / {activeWorkspace?.name || "…"} / {currentModule.label}</p>
          <h1>{currentModule.label}</h1>
        </div>

        <IconButton className="topbar-workspace-action" aria-label="Ouvrir les Workspaces" title="Workspaces" onClick={onOpenWorkspaces}>
          <PanelsTopLeft size={18} />
        </IconButton>
      </div>

      <button className="topbar-command" type="button" onClick={onOpenCommand} aria-label="Ouvrir Search or ask TRIDENT"><Search size={17} /><span>Search or ask TRIDENT…</span><kbd>⌘ K</kbd></button>

      <div className="topbar-right">
        <span className="workspace-status"><i /> Workspace actif</span>
        <IconButton className="profile-btn" aria-label="Ouvrir les paramètres du compte" title="Compte et paramètres" onClick={() => setActiveView("settings")}><CircleUserRound size={18} /></IconButton>
      </div>
    </header>
  );
}
