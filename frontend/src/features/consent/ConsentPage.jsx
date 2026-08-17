import { useCallback, useEffect, useMemo, useState } from "react";
import { authorizationId, requestedScopes, safeAuthorizationRedirect } from "./consentState";
import { consentClient } from "./supabaseClient";
import "./ConsentPage.css";

export default function ConsentPage() {
  const requestId = useMemo(() => authorizationId(window.location.search), []);
  const supabase = useMemo(() => consentClient(), []);
  const [state, setState] = useState("loading");
  const [details, setDetails] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loadAuthorization = useCallback(async () => {
    if (!supabase || !requestId) {
      setState("unavailable");
      return;
    }
    setError("");
    const { data: userData } = await supabase.auth.getUser();
    if (!userData?.user) {
      setState("login");
      return;
    }
    const { data, error: detailsError } = await supabase.auth.oauth.getAuthorizationDetails(requestId);
    if (detailsError || !data) {
      setError("La demande d’autorisation est invalide ou expirée.");
      setState("error");
      return;
    }
    if (!("authorization_id" in data) && data.redirect_url) {
      window.location.assign(safeAuthorizationRedirect(data.redirect_url));
      return;
    }
    setDetails(data);
    setState("consent");
  }, [requestId, supabase]);

  useEffect(() => { loadAuthorization().catch(() => { setError("Supabase Auth est momentanément indisponible."); setState("error"); }); }, [loadAuthorization]);

  async function login(event) {
    event.preventDefault();
    setState("working"); setError("");
    try {
      const { error: loginError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
      setPassword("");
      if (loginError) throw loginError;
      await loadAuthorization();
    } catch {
      setPassword("");
      setError("Connexion refusée. Vérifiez vos informations et réessayez.");
      setState("login");
    }
  }

  async function decide(decision) {
    setState("working"); setError("");
    try {
      const operation = decision === "approve"
        ? supabase.auth.oauth.approveAuthorization(requestId)
        : supabase.auth.oauth.denyAuthorization(requestId);
      const { data, error: decisionError } = await operation;
      if (decisionError || !data?.redirect_url) throw decisionError || new Error("Missing redirect");
      window.location.assign(safeAuthorizationRedirect(data.redirect_url));
    } catch {
      setError("La décision n’a pas pu être enregistrée.");
      setState("consent");
    }
  }

  const scopes = requestedScopes(details?.scope);
  return (
    <main className="consent-shell">
      <section className="consent-card" aria-live="polite">
        <div className="consent-mark" aria-hidden="true">♆</div>
        <p className="consent-eyebrow">TRIDENT · Accès sécurisé</p>
        {state === "loading" && <><h1>Vérification de la demande</h1><p>Connexion au service d’identité…</p></>}
        {state === "unavailable" && <><h1>Autorisation indisponible</h1><p>La configuration Supabase publique ou l’identifiant d’autorisation est invalide.</p></>}
        {(state === "login" || state === "working" && !details) && (
          <form onSubmit={login}>
            <h1>Se connecter pour autoriser</h1>
            <p>Votre identité est vérifiée directement par Supabase Auth.</p>
            <label>Email<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Mot de passe<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {error && <p className="consent-error" role="alert">{error}</p>}
            <button type="submit" disabled={state === "working"}>Se connecter</button>
          </form>
        )}
        {(state === "consent" || state === "working" && details) && (
          <div>
            <h1>Autoriser {details?.client?.name || "cette application"} ?</h1>
            <p>L’application demande l’accès aux informations suivantes :</p>
            <ul>{scopes.map((scope) => <li key={scope}>{scope}</li>)}</ul>
            <p className="consent-destination">Destination vérifiée : {details?.redirect_uri}</p>
            {error && <p className="consent-error" role="alert">{error}</p>}
            <div className="consent-actions">
              <button type="button" className="secondary" disabled={state === "working"} onClick={() => decide("deny")}>Refuser</button>
              <button type="button" disabled={state === "working"} onClick={() => decide("approve")}>Autoriser</button>
            </div>
          </div>
        )}
        {state === "error" && <><h1>Demande indisponible</h1><p className="consent-error" role="alert">{error}</p></>}
      </section>
    </main>
  );
}
