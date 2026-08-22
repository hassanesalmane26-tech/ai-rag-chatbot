import {
  LogOut,
  PanelsTopLeft,
} from "lucide-react";
import TridentMark from "../visual/TridentMark";
import IconButton from "../ui/IconButton";
import useSessionContext from "../../hooks/useSessionContext";

export default function Header({
  title = "TRIDENT AI",
  onOpenWorkspaces,
}) {
  const { logout } = useSessionContext();
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo"><TridentMark label="TRIDENT AI" /></div>

        <div>
          <h1>{title}</h1>
          <p>AI OPERATING SYSTEM · WORKSPACE</p>
        </div>

        <IconButton className="topbar-workspace-action" aria-label="Ouvrir les Workspaces" title="Workspaces" onClick={onOpenWorkspaces}>
          <PanelsTopLeft size={18} />
        </IconButton>
      </div>

      <div className="topbar-right">
        <IconButton className="icon-btn" aria-label="Se déconnecter" title="Se déconnecter" onClick={() => logout().catch(() => {})}>
          <LogOut size={18} />
        </IconButton>
      </div>
    </header>
  );
}
