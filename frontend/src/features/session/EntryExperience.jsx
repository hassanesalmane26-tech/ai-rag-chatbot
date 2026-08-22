import TridentMark from "../../components/visual/TridentMark";
import VisualEnvironment from "../../components/visual/VisualEnvironment";
import useSessionContext from "../../hooks/useSessionContext";
import { organizationChoices } from "./sessionState";
import "./EntryExperience.css";

export default function EntryExperience() {
  const { state, session, error, login, logout, refresh, selectContext } = useSessionContext();
  const organizations = organizationChoices(session);
  return <main className="entry-experience">
    <VisualEnvironment />
    <section className="entry-panel ds-glass-panel ds-glass-panel--elevated">
      <TridentMark label="TRIDENT AI" />
      <span className="entry-kicker">TRIDENT AI · WORKSPACE OPERATING SYSTEM</span>
      {state === "loading" && <><h1>Ouverture de TRIDENT</h1><p>Validation sécurisée de votre session…</p></>}
      {state === "onboarding" && <><h1>Création de votre espace TRIDENT AI</h1><p>Préparation sécurisée de votre Organization et de votre premier Workspace…</p></>}
      {state === "unavailable" && <><h1>Accès sécurisé non configuré</h1><p>TRIDENT protège les données du Workspace. Un fournisseur OIDC réel doit être configuré avant la connexion.</p></>}
      {state === "anonymous" && <><h1>Entrez dans votre Workspace</h1><p>Authentification sécurisée par Authorization Code et PKCE.</p><button className="ds-button" type="button" onClick={() => login().catch(() => {})}>Se connecter</button></>}
      {state === "error" && <><h1>Session indisponible</h1><p role="alert">{error}</p><button className="ds-button" type="button" onClick={refresh}>Réessayer</button></>}
      {state === "authenticated" && organizations.length === 0 && <><h1>Votre espace est presque prêt</h1><p>TRIDENT AI n’a pas pu ouvrir votre Workspace automatiquement.</p><button className="ds-button" type="button" onClick={refresh}>Réessayer</button><button className="ds-button ds-button--secondary" type="button" onClick={() => logout().catch(() => {})}>Se déconnecter</button></>}
      {state === "authenticated" && organizations.length > 0 && <><h1>Sélectionnez votre environnement</h1><p>Votre Workspace reste le centre de TRIDENT.</p><div className="entry-organizations">{organizations.map((organization) => <article key={organization.id}><strong>{organization.name}</strong><span>{organization.role}</span><div>{organization.workspaces.length ? organization.workspaces.map((workspace) => <button key={workspace.id} type="button" onClick={() => selectContext(organization.id, workspace.id).catch(() => {})}>{workspace.name}</button>) : <button type="button" onClick={() => selectContext(organization.id, null).catch(() => {})}>Ouvrir l’Organization</button>}</div></article>)}</div><button className="entry-logout" type="button" onClick={() => logout().catch(() => {})}>Se déconnecter</button></>}
    </section>
  </main>;
}
