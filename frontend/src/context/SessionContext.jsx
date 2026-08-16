import { useCallback, useEffect, useMemo, useState } from "react";
import {
  endSession,
  getCurrentSession,
  getSessionConfiguration,
  selectSessionContext,
  startSessionLogin,
} from "../services/api";
import { SessionContext } from "./sessionContext";

export function SessionProvider({ children }) {
  const [state, setState] = useState("loading");
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setState("loading");
    try {
      const configuration = await getSessionConfiguration();
      if (!configuration.enabled) {
        setSession(null); setState("unavailable"); setError(null); return;
      }
      try {
        const value = await getCurrentSession();
        setSession(value); setState("authenticated"); setError(null);
      } catch (cause) {
        if (cause.status === 401) {
          setSession(null); setState("anonymous"); setError(null);
        } else {
          setSession(null); setState("error"); setError(cause.message);
        }
      }
    } catch (cause) {
      setState("error"); setError(cause.message);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = useCallback(async () => {
    setError(null);
    try {
      const result = await startSessionLogin(window.location.pathname || "/");
      window.location.assign(result.authorization_url);
    } catch (cause) {
      setState("error");
      setError(cause.message);
      throw cause;
    }
  }, []);

  const logout = useCallback(async () => {
    const result = await endSession();
    setSession(null); setState("anonymous");
    if (result.end_session_url) window.location.assign(result.end_session_url);
  }, []);

  const selectContext = useCallback(async (organizationId, workspaceId) => {
    setError(null);
    try {
      const value = await selectSessionContext(organizationId, workspaceId);
      if (workspaceId) window.localStorage.setItem("trident.genesis.active_workspace_id", workspaceId);
      setSession(value);
      return value;
    } catch (cause) {
      setError(cause.message);
      throw cause;
    }
  }, []);

  const value = useMemo(() => ({ state, session, error, refresh, login, logout, selectContext }),
    [state, session, error, refresh, login, logout, selectContext]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
