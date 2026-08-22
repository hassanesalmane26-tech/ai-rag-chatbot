import { LogOut, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import WorkspaceSelector from "../../components/workspace/WorkspaceSelector";
import useSessionContext from "../../hooks/useSessionContext";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { membershipRoleLabel } from "../session/sessionState";

export default function SettingsView() {
  const { session, logout } = useSessionContext();
  const { activeWorkspace, updateWorkspace, mutation } = useWorkspaceContext();
  const [description, setDescription] = useState(activeWorkspace?.description || "");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");
  const organization = session?.organizations?.find((item) => item.id === session.active_organization_id);

  useEffect(() => { setDescription(activeWorkspace?.description || ""); setSaved(false); setSaveError(""); }, [activeWorkspace?.id, activeWorkspace?.description]);

  async function saveDescription(event) {
    event.preventDefault();
    if (!activeWorkspace || mutation) return;
    setSaveError("");
    try { await updateWorkspace(activeWorkspace.id, { description: description.trim() || null }); setSaved(true); }
    catch (cause) { setSaveError(cause.message); }
  }

  return <section className="product-view settings-view" aria-labelledby="settings-title">
    <header className="product-view__header"><div><span>WORKSPACE CONTROL</span><h2 id="settings-title">Settings</h2><p>Compte, Workspace, confidentialité et session TRIDENT AI.</p></div></header>
    <div className="settings-grid">
      <section className="settings-card"><header><UserRound size={20} /><div><span>ACCOUNT</span><h3>Identité vérifiée</h3></div></header><dl><div><dt>Identifiant TRIDENT</dt><dd title={session?.user?.id}>{session?.user?.id || "Indisponible"}</dd></div><div><dt>Organization</dt><dd>{organization?.name || "Indisponible"}</dd></div><div><dt>Rôle</dt><dd>{membershipRoleLabel(organization?.role)}</dd></div><div><dt>Édition</dt><dd>TRIDENT AI</dd></div></dl></section>
      <section className="settings-card settings-card--workspace"><header><Sparkles size={20} /><div><span>WORKSPACE</span><h3>{activeWorkspace?.name}</h3></div></header><WorkspaceSelector /><form className="workspace-description-form" onSubmit={saveDescription}><label htmlFor="workspace-description">Description du Workspace</label><textarea id="workspace-description" rows="3" maxLength="1000" value={description} onChange={(event) => { setDescription(event.target.value); setSaved(false); setSaveError(""); }} /><button className="ds-button" type="submit" disabled={Boolean(mutation)}>{mutation === "updating" ? "Enregistrement…" : "Enregistrer"}</button>{saved && <span role="status">Description enregistrée.</span>}{saveError && <span className="settings-save-error" role="alert">{saveError}</span>}</form></section>
      <section className="settings-card"><header><ShieldCheck size={20} /><div><span>PRIVACY & MEMORY</span><h3>Contrôle explicite</h3></div></header><p>TRIDENT AI ne crée pas silencieusement de Memory explicite. Vous pouvez consulter, désactiver, modifier ou supprimer chaque repère depuis le module Memory.</p></section>
      <section className="settings-card"><header><LogOut size={20} /><div><span>SESSION</span><h3>Session sécurisée</h3></div></header><p>Votre session opaque reste séparée des jetons OIDC. La déconnexion la révoque côté serveur.</p><button className="ds-button ds-button--secondary" type="button" onClick={() => logout().catch(() => {})}><LogOut size={17} /> Se déconnecter</button></section>
      <section className="settings-card settings-card--about"><span>ABOUT</span><h3>TRIDENT AI</h3><p>AI Operating System centré sur un Workspace intelligent.</p><strong>Created by Salmane Hassan</strong><small>A TRIDENT Project</small></section>
    </div>
  </section>;
}
