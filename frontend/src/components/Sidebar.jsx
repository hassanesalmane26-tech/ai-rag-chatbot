function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>🔱 TRIDENT AI</h2>
      </div>

      <nav className="sidebar-menu">
        <button>💬 Chat</button>
        <button>📄 Documents</button>
        <button>⭐ Favoris</button>
        <button>⚙️ Paramètres</button>
      </nav>

      <div className="sidebar-documents">
        <h3>Documents</h3>

        <div className="empty">
          Aucun document importé
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
