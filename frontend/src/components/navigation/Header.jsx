import {
  Bell,
  Search,
  Sparkles,
  UserCircle2,
} from "lucide-react";
import TridentMark from "../visual/TridentMark";

export default function Header({
  title = "TRIDENT",
}) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo"><TridentMark label="TRIDENT GENESIS" /></div>

        <div>
          <h1>{title}</h1>
          <p>WORKSPACE CORE / GENESIS</p>
        </div>
      </div>

      <div className="topbar-right">
        <div className="search-box" aria-label="Recherche indisponible dans Genesis">
          <Search size={18} />

          <input
            type="text"
            placeholder="Recherche bientôt disponible"
            aria-label="Recherche indisponible dans Genesis"
            disabled
          />
        </div>

        <button className="icon-btn" aria-label="Assistant IA indisponible dans Genesis" title="Indisponible dans Genesis" disabled>
          <Sparkles size={18} />
        </button>

        <button className="icon-btn" aria-label="Notifications indisponibles dans Genesis" title="Indisponible dans Genesis" disabled>
          <Bell size={18} />
        </button>

        <button className="profile-btn" aria-label="Profil indisponible dans Genesis" title="Indisponible dans Genesis" disabled>
          <UserCircle2 size={22} />
        </button>
      </div>
    </header>
  );
}
