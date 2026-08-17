import {
  Bell,
  LogOut,
  PanelsTopLeft,
  Search,
  Sparkles,
  UserCircle2,
} from "lucide-react";
import TridentMark from "../visual/TridentMark";
import IconButton from "../ui/IconButton";
import useSessionContext from "../../hooks/useSessionContext";

export default function Header({
  title = "TRIDENT",
  onOpenWorkspaces,
}) {
  const { logout } = useSessionContext();
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo"><TridentMark label="TRIDENT AI" /></div>

        <div>
          <h1>{title}</h1>
          <p>INTELLIGENT WORKSPACE CORE</p>
        </div>

        <IconButton className="topbar-workspace-action" aria-label="Ouvrir les Workspaces" title="Workspaces" onClick={onOpenWorkspaces}>
          <PanelsTopLeft size={18} />
        </IconButton>
      </div>

      <div className="topbar-right">
        <div className="search-box" aria-label="Recherche indisponible dans TRIDENT AI">
          <Search size={18} />

          <input
            type="text"
            placeholder="Recherche bientôt disponible"
            aria-label="Recherche indisponible dans TRIDENT AI"
            disabled
          />
        </div>

        <IconButton className="icon-btn" aria-label="Assistant IA indisponible" title="Indisponible" disabled>
          <Sparkles size={18} />
        </IconButton>

        <IconButton className="icon-btn" aria-label="Notifications indisponibles" title="Indisponible" disabled>
          <Bell size={18} />
        </IconButton>

        <IconButton className="profile-btn" aria-label="Profil indisponible" title="Indisponible" disabled>
          <UserCircle2 size={22} />
        </IconButton>
        <IconButton className="icon-btn" aria-label="Se déconnecter" title="Se déconnecter" onClick={() => logout().catch(() => {})}>
          <LogOut size={18} />
        </IconButton>
      </div>
    </header>
  );
}
