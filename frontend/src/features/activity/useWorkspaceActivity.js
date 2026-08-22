import { useCallback, useEffect, useRef, useState } from "react";
import { listWorkspaceActivity } from "../../services/api";

export default function useWorkspaceActivity(workspaceId) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestVersion = useRef(0);

  const refresh = useCallback(async () => {
    if (!workspaceId) return [];
    const version = ++requestVersion.current;
    setLoading(true); setError("");
    try {
      const values = await listWorkspaceActivity(workspaceId);
      if (version === requestVersion.current) setEvents(values);
      return values;
    } catch (cause) {
      if (version === requestVersion.current) setError(cause.message);
      return [];
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    setEvents([]); setError(""); refresh();
    return () => { requestVersion.current += 1; };
  }, [workspaceId, refresh]);

  return { events, loading, error, refresh };
}
