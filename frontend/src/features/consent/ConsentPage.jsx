import { useCallback, useEffect, useMemo, useState } from "react";
import {
  authorizationId,
  requestedScopes,
  safeAuthorizationRedirect,
} from "./consentState";
import { consentClient } from "./supabaseClient";
import "./ConsentPage.css";

export default function ConsentPage() {
  const requestId = useMemo(
    () => authorizationId(window.location.search),
    []
  );

  const supabase = useMemo(() => consentClient(), []);

  const [state, setState] = useState("loading");
  const [details, setDetails] = useState(null);
  const [mode, setMode] = useState("login");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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

    const { data, error: detailsError } =
      await supabase.auth.oauth.getAuthorizationDetails(requestId);

    if (detailsError || !data) {
      setError("La demande d’autorisation est invalide ou expirée.");
      setState("error");
      return;
    }

    if (!("authorization_id" in data) && data.redirect_url) {
      window.location.assign(
        safeAuthorizationRedirect(data.redirect_url)
      );
      return;
    }

    setDetails(data);
    setState("consent");
  }, [requestId, supabase]);

  useEffect(() => {
    loadAuthorization().catch(() => {
      setError(
        "Le service d’identité est momentanément indisponible."
      );
      setState("error");
    });
  }, [loadAuthorization]);

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
    setNotice("");
    setPassword("");
    setConfirmPassword("");
  }

  async function login(event) {
    event.preventDefault();

    setState("working");
    setError("");
    setNotice("");

    try {
      const { error: loginError } =
        await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

      setPassword("");

      if (loginError) throw loginError;

      await loadAuthorization();
    } catch {
      setPassword("");
      setError(
        "Connexion refusée. Vérifiez votre email et votre mot de passe."
      );
      setState("login");
    }
  }

  async function signup(event) {
    event.preventDefault();

    setError("");
    setNotice("");

    const normalizedEmail = email.trim();

    if (password.length < 8) {
      setError(
        "Votre mot de passe doit contenir au moins 8 caractères."
      );
      return;
    }

    if (password !== confirmPassword) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setState("working");

    try {
      const { data, error: signupError } =
        await supabase.auth.signUp({
          email: normalizedEmail,
          password,
        });

      setPassword("");
      setConfirmPassword("");

      if (signupError) throw signupError;

      /*
       * Supabase peut être configuré :
       * - avec confirmation email => session absente ;
       * - sans confirmation => session immédiate.
       */
      if (data?.session) {
        await loadAuthorization();
        return;
      }

      setNotice(
        "Compte créé. Vérifiez votre boîte mail pour confirmer votre adresse, puis revenez vous connecter à TRIDENT."
      );
      setMode("login");
      setState("login");
    } catch {
      setPassword("");
      setConfirmPassword("");

      setError(
        "Création du compte impossible. Vérifiez vos informations ou essayez de vous connecter si ce compte existe déjà."
      );
      setState("login");
    }
  }

  async function decide(decision) {
    setState("working");
    setError("");

    try {
      const operation =
        decision === "approve"
          ? supabase.auth.oauth.approveAuthorization(requestId)
          : supabase.auth.oauth.denyAuthorization(requestId);

      const { data, error: decisionError } = await operation;

      if (decisionError || !data?.redirect_url) {
        throw decisionError || new Error("Missing redirect");
      }

      window.location.assign(
        safeAuthorizationRedirect(data.redirect_url)
      );
    } catch {
      setError("La décision n’a pas pu être enregistrée.");
      setState("consent");
    }
  }

  const scopes = requestedScopes(details?.scope);
  const authWorking = state === "working" && !details;

  return (
    <main className="consent-shell">
      <section className="consent-card" aria-live="polite">
        <div className="consent-mark" aria-hidden="true">
          ♆
        </div>

        <p className="consent-eyebrow">
          TRIDENT AI · ACCÈS SÉCURISÉ
        </p>

        {state === "loading" && (
          <>
            <h1>Vérification de la demande</h1>
            <p>Connexion sécurisée à TRIDENT…</p>
          </>
        )}

        {state === "unavailable" && (
          <>
            <h1>Autorisation indisponible</h1>
            <p>
              Le service d’identité TRIDENT ne peut pas traiter
              cette demande.
            </p>
          </>
        )}

        {(state === "login" || authWorking) && (
          <div className="consent-auth">
            <div
              className="consent-tabs"
              role="tablist"
              aria-label="Accès TRIDENT"
            >
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={mode === "login" ? "active" : ""}
                disabled={authWorking}
                onClick={() => switchMode("login")}
              >
                Connexion
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={mode === "signup"}
                className={mode === "signup" ? "active" : ""}
                disabled={authWorking}
                onClick={() => switchMode("signup")}
              >
                Créer un compte
              </button>
            </div>

            {mode === "login" ? (
              <form onSubmit={login}>
                <div className="consent-heading">
                  <h1>Bienvenue sur TRIDENT</h1>
                  <p>
                    Connectez-vous pour accéder à votre Workspace.
                  </p>
                </div>

                <label>
                  Email
                  <input
                    type="email"
                    inputMode="email"
                    autoCapitalize="none"
                    autoComplete="username"
                    required
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                  />
                </label>

                <label>
                  Mot de passe
                  <input
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                  />
                </label>

                {notice && (
                  <p className="consent-notice" role="status">
                    {notice}
                  </p>
                )}

                {error && (
                  <p className="consent-error" role="alert">
                    {error}
                  </p>
                )}

                <button
                  className="consent-primary"
                  type="submit"
                  disabled={authWorking}
                >
                  {authWorking ? "Connexion…" : "Se connecter"}
                </button>

                <p className="consent-switch">
                  Nouveau sur TRIDENT ?{" "}
                  <button
                    type="button"
                    className="consent-link"
                    onClick={() => switchMode("signup")}
                  >
                    Créer un compte
                  </button>
                </p>
              </form>
            ) : (
              <form onSubmit={signup}>
                <div className="consent-heading">
                  <h1>Créer votre accès TRIDENT</h1>
                  <p>
                    Un compte sécurisé suffit pour commencer votre
                    Workspace.
                  </p>
                </div>

                <label>
                  Email
                  <input
                    type="email"
                    inputMode="email"
                    autoCapitalize="none"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                  />
                </label>

                <label>
                  Mot de passe
                  <input
                    type="password"
                    minLength={8}
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                  />
                  <span className="consent-hint">
                    8 caractères minimum
                  </span>
                </label>

                <label>
                  Confirmer le mot de passe
                  <input
                    type="password"
                    minLength={8}
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                  />
                </label>

                {error && (
                  <p className="consent-error" role="alert">
                    {error}
                  </p>
                )}

                <button
                  className="consent-primary"
                  type="submit"
                  disabled={authWorking}
                >
                  {authWorking
                    ? "Création…"
                    : "Créer mon compte"}
                </button>

                <p className="consent-legal">
                  Votre compte est protégé par le service
                  d’identité sécurisé de TRIDENT.
                </p>

                <p className="consent-switch">
                  Déjà un compte ?{" "}
                  <button
                    type="button"
                    className="consent-link"
                    onClick={() => switchMode("login")}
                  >
                    Se connecter
                  </button>
                </p>
              </form>
            )}
          </div>
        )}

        {(state === "consent" ||
          (state === "working" && details)) && (
          <div>
            <h1>
              Autoriser{" "}
              {details?.client?.name || "TRIDENT"} ?
            </h1>

            <p>
              L’application demande l’accès aux informations
              suivantes :
            </p>

            <ul>
              {scopes.map((scope) => (
                <li key={scope}>{scope}</li>
              ))}
            </ul>

            <p className="consent-destination">
              Destination vérifiée : {details?.redirect_uri}
            </p>

            {error && (
              <p className="consent-error" role="alert">
                {error}
              </p>
            )}

            <div className="consent-actions">
              <button
                type="button"
                className="secondary"
                disabled={state === "working"}
                onClick={() => decide("deny")}
              >
                Refuser
              </button>

              <button
                type="button"
                disabled={state === "working"}
                onClick={() => decide("approve")}
              >
                Autoriser
              </button>
            </div>
          </div>
        )}

        {state === "error" && (
          <>
            <h1>Demande indisponible</h1>
            <p className="consent-error" role="alert">
              {error}
            </p>
          </>
        )}

        <p className="consent-signature">
          Created by Salmane Hassan
        </p>
      </section>
    </main>
  );
}
