import { useCallback, useEffect, useRef, useState } from "react";
import { listWorkspaceActivity } from "../../services/api";
import { acceptsActivityResult, activityLifecycle, normalizeActivityEvents } from "./activityState";

export default function useWorkspaceActivity(workspaceId) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestVersion = useRef(0);
  const workspaceRef = useRef(workspaceId);

  const refresh = useCallback(async () => {
    if (!workspaceId) { setLoading(false); return []; }
    const requestWorkspaceId = workspaceId;
    const version = ++requestVersion.current;
    setLoading(true); setError("");
    try {
      const values = normalizeActivityEvents(await listWorkspaceActivity(requestWorkspaceId));
      if (version === requestVersion.current && acceptsActivityResult(workspaceRef.current, requestWorkspaceId)) setEvents(values);
      return values;
    } catch (cause) {
      if (version === requestVersion.current && acceptsActivityResult(workspaceRef.current, requestWorkspaceId)) setError(cause.message);
      return [];
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    workspaceRef.current = workspaceId; setEvents([]); setError(""); refresh();
    return () => { requestVersion.current += 1; };
  }, [workspaceId, refresh]);

  return { events, loading, error, lifecycle: activityLifecycle({ workspaceId, loading, error, count: events.length }), refresh };
}
