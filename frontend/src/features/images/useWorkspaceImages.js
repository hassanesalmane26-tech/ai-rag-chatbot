import { useCallback, useEffect, useState } from "react";
import { getImageCapability, listImages } from "../../services/api";
import { isImagePending } from "./imageState";

// Both capabilities and image records are discarded synchronously on scope change.
export default function useWorkspaceImages(workspaceId, conversationId, revision = 0) {
  const scope = `${workspaceId}:${conversationId ?? "all"}`;
  const [snapshot, setSnapshot] = useState(null);
  const [request, setRequest] = useState(0);
  const refresh = useCallback(() => setRequest((value) => value + 1), []);
  useEffect(() => {
    let current = true;
    let timer;
    let capability;
    async function load() {
      try {
        capability ||= await getImageCapability(workspaceId);
        const images = conversationId === null ? [] : await listImages(workspaceId, conversationId);
        if (current) {
          setSnapshot({ scope, capability, images, loading: false, error: "" });
          // No idle polling; pending durable jobs alone need status updates.
          if (images.some(isImagePending)) timer = setTimeout(load, document.hidden ? 15000 : 4000);
        }
      } catch (error) {
        if (current) setSnapshot({ scope, images: [], capability: null, loading: false, error: error.message });
      }
    }
    if (workspaceId) load();
    return () => { current = false; clearTimeout(timer); };
  }, [workspaceId, conversationId, scope, request, revision]);
  return { ...(snapshot?.scope === scope ? snapshot : { images: [], capability: null, loading: true, error: "" }), refresh };
}
