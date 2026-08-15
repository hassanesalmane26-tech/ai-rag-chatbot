import { useState } from "react";
import { BookOpen, House, MessageSquarePlus, MessagesSquare } from "lucide-react";
import useWorkspaceContext from "../hooks/useWorkspaceContext";
import WorkspaceSelector from "./workspace/WorkspaceSelector";
import TridentMark from "./visual/TridentMark";

const items = [
  ["home", "Accueil", House],
  ["conversations", "Conversations", MessagesSquare],
  ["knowledge", "Knowledge", BookOpen],
];

export default function Sidebar() {
  const { activeView, setActiveView, createWorkspace } = useWorkspaceContext();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  async function submit(event) { event.preventDefault(); if (!name.trim()) return; await createWorkspace(name.trim()); setName(""); setCreating(false); }
  return <aside className="sidebar" aria-label="Navigation du Workspace">
    <div className="sidebar-brand"><div className="brand-icon"><TridentMark /></div><div><h2>TRIDENT</h2><span>GENESIS / WORKSPACE OS</span></div></div>
    <nav className="sidebar-menu">{items.map(([id, label, Icon]) => <button key={id} className={`menu-item ds-nav-control ${activeView === id ? "active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => setActiveView(id)}><Icon size={17} />{label}</button>)}</nav>
    <div className="sidebar-documents"><WorkspaceSelector /></div>
    <div className="sidebar-create">{creating ? <form onSubmit={submit}><input aria-label="Nom du nouveau Workspace" autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Nom du Workspace" /><button type="submit">Créer</button></form> : <button onClick={() => setCreating(true)}><MessageSquarePlus size={16} /> Nouveau Workspace</button>}</div>
    <div className="sidebar-footer"><div className="status-dot"></div><div><strong>Mode GENESIS</strong><p>Workspace local</p></div></div>
  </aside>;
}
