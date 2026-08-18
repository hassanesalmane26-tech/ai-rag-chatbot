import { useState } from "react";
import { MessageSquarePlus } from "lucide-react";
import { workspaceModules } from "../app/modules/registry";
import useWorkspaceContext from "../hooks/useWorkspaceContext";
import WorkspaceSelector from "./workspace/WorkspaceSelector";
import TridentMark from "./visual/TridentMark";

export default function Sidebar() {
  const { activeView, setActiveView, createWorkspace, mutation } = useWorkspaceContext();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  async function submit(event) { event.preventDefault(); if (!name.trim() || mutation) return; try { await createWorkspace(name.trim()); setName(""); setCreating(false); } catch { /* The Workspace selector exposes the recoverable request error. */ } }
  return <aside className="sidebar" aria-label="Navigation du Workspace">
    <div className="sidebar-brand"><div className="brand-icon"><TridentMark /></div><div><h2>TRIDENT</h2><span>AI / WORKSPACE OS</span></div></div>
    <nav className="sidebar-menu">{workspaceModules.map(({ id, label, icon: Icon }) => <button key={id} className={`menu-item ds-nav-control ${activeView === id ? "active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => setActiveView(id)}><Icon size={17} />{label}</button>)}</nav>
    <div className="sidebar-documents"><WorkspaceSelector /></div>
    <div className="sidebar-create">{creating ? <form onSubmit={submit}><input aria-label="Nom du nouveau Workspace" autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Nom du Workspace" disabled={Boolean(mutation)} /><button type="submit" disabled={Boolean(mutation)}>{mutation === "creating" ? "Création…" : "Créer"}</button></form> : <button onClick={() => setCreating(true)} disabled={Boolean(mutation)}><MessageSquarePlus size={16} /> Nouveau Workspace</button>}</div>
    <div className="sidebar-footer"><div className="status-dot"></div><div><strong>TRIDENT AI</strong><p>Created by Salmane Hassan</p></div></div>
  </aside>;
}
