import { useState } from "react";
import { LogOut, MessageSquarePlus } from "lucide-react";
import { workspaceModules } from "../app/modules/registry";
import useWorkspaceContext from "../hooks/useWorkspaceContext";
import WorkspaceSelector from "./workspace/WorkspaceSelector";
import TridentMark from "./visual/TridentMark";
import useSessionContext from "../hooks/useSessionContext";

export default function Sidebar() {
  const { activeView, setActiveView, createWorkspace, mutation } = useWorkspaceContext();
  const { session, logout } = useSessionContext();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  async function submit(event) { event.preventDefault(); if (!name.trim() || mutation) return; try { await createWorkspace(name.trim()); setName(""); setCreating(false); } catch { /* The Workspace selector exposes the recoverable request error. */ } }
  return <aside className="sidebar" aria-label="Navigation du Workspace">
    <div className="sidebar-brand"><div className="brand-icon"><TridentMark /></div><div><h2>TRIDENT</h2><span>AI / WORKSPACE OS</span></div></div>
    <div className="sidebar-documents"><WorkspaceSelector /></div>
    <div className="sidebar-create">{creating ? <form onSubmit={submit}><input aria-label="Nom du nouveau Workspace" autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Nom du Workspace" disabled={Boolean(mutation)} /><button type="submit" disabled={Boolean(mutation)}>{mutation === "creating" ? "Création…" : "Créer"}</button></form> : <button onClick={() => setCreating(true)} disabled={Boolean(mutation)}><MessageSquarePlus size={16} /> Nouveau Workspace</button>}</div>
    <nav className="sidebar-menu" aria-label="Modules principaux">{workspaceModules.filter((item) => item.section === "primary").map(({ id, label, icon: Icon, mobile }) => <button key={id} className={`menu-item ds-nav-control ${mobile ? "menu-item--mobile" : ""} ${activeView === id ? "active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => setActiveView(id)}><Icon size={17} />{label}</button>)}</nav>
    <nav className="sidebar-menu sidebar-menu--secondary" aria-label="Workspace et paramètres">{workspaceModules.filter((item) => item.section === "secondary").map(({ id, label, icon: Icon }) => <button key={id} className={`menu-item ds-nav-control ${activeView === id ? "active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => setActiveView(id)}><Icon size={17} />{label}</button>)}</nav>
    <div className="sidebar-footer"><div className="status-dot" aria-hidden="true" /><div className="sidebar-account"><strong>{session?.user?.display_name || "Compte TRIDENT"}</strong><span>Édition TRIDENT AI</span><p>Created by Salmane Hassan</p><small>A TRIDENT Project</small></div><button type="button" aria-label="Se déconnecter" title="Se déconnecter" onClick={() => logout().catch(() => {})}><LogOut size={16} /></button></div>
  </aside>;
}
