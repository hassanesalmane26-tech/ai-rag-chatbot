const API = import.meta.env.VITE_API_BASE_URL || "/api";
const REQUEST_TIMEOUT_MS = 30000;
let accessTokenProvider = null;

// AI-3 owns session acquisition. AI-2 only provides the injection seam; it never
// reads an unverified identity or stores a credential on its own.
export function setAccessTokenProvider(provider) {
  if (provider !== null && typeof provider !== "function") {
    throw new TypeError("Le fournisseur de jeton doit être une fonction.");
  }
  accessTokenProvider = provider;
}

function requestId() {
  return globalThis.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function requestEnvelope(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const token = accessTokenProvider ? await accessTokenProvider() : null;
    const authorization = token ? { Authorization: `Bearer ${token}` } : {};
    const csrf = document.cookie.split("; ").find((item) => item.startsWith("trident_csrf="))?.split("=")[1];
    const csrfHeader = !["GET", "HEAD", "OPTIONS"].includes(options.method || "GET") && csrf
      ? { "X-CSRF-Token": decodeURIComponent(csrf) }
      : {};
    const response = await fetch(`${API}/v1${url}`, {
      ...options,
      credentials: "include",
      headers: { "X-Request-ID": requestId(), ...authorization, ...csrfHeader, ...options.headers },
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error?.message || `Erreur ${response.status}`);
      error.status = response.status;
      error.code = payload.error?.code;
      throw error;
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("Le service TRIDENT met trop de temps à répondre.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function request(url, options = {}) {
  return (await requestEnvelope(url, options)).data;
}

async function requestBinary(url) {
  const token = accessTokenProvider ? await accessTokenProvider() : null;
  const response = await fetch(`${API}/v1${url}`, {
    credentials: "include",
    headers: { "X-Request-ID": requestId(), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.error?.message || `Erreur ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.blob();
}

async function listAll(url) {
  const values = [];
  let offset = 0;
  while (offset <= 100000) {
    const separator = url.includes("?") ? "&" : "?";
    const envelope = await requestEnvelope(`${url}${separator}limit=100&offset=${offset}`);
    values.push(...(Array.isArray(envelope.data) ? envelope.data : []));
    if (!envelope.meta?.pagination?.has_more) return values;
    offset += 100;
  }
  throw new Error("La pagination TRIDENT dépasse la limite contractuelle.");
}

export const getSessionConfiguration = () => request("/session/configuration");
export const startSessionLogin = (returnTo = "/") => request("/session/login", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ return_to: returnTo }),
});
export const getCurrentSession = () => request("/session");
export const onboardCurrentUser = () => request("/session/onboarding", { method: "POST" });
export const selectSessionContext = (organizationId, workspaceId = null) => request("/session/context", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ organization_id: organizationId, workspace_id: workspaceId }),
});
export const endSession = () => request("/session/logout", { method: "POST" });

export const listWorkspaces = () => listAll("/workspaces");
export const createWorkspace = (payload) => request("/workspaces", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const getWorkspace = (workspaceId) => request(`/workspaces/${workspaceId}`);
export const updateWorkspace = (workspaceId, payload) => request(`/workspaces/${workspaceId}`, {
  method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const getOverview = (workspaceId) => request(`/workspaces/${workspaceId}/overview`);
export const listConversations = (workspaceId) => listAll(`/workspaces/${workspaceId}/conversations`);
export const createConversation = (workspaceId, title) => request(`/workspaces/${workspaceId}/conversations`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }),
});
export const getConversation = (workspaceId, conversationId) => request(`/workspaces/${workspaceId}/conversations/${conversationId}`);
export const sendWorkspaceMessage = (workspaceId, conversationId, content) => request(`/workspaces/${workspaceId}/conversations/${conversationId}/messages`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }),
});
export const listDocuments = (workspaceId) => listAll(`/workspaces/${workspaceId}/documents`);
export const deleteDocument = (workspaceId, documentId) => request(`/workspaces/${workspaceId}/documents/${documentId}`, { method: "DELETE" });
export const retryDocument = (workspaceId, documentId) => request(`/workspaces/${workspaceId}/documents/${documentId}/retry`, { method: "POST" });
export const downloadDocument = (workspaceId, documentId) => requestBinary(`/workspaces/${workspaceId}/documents/${documentId}/original`);
export async function uploadDocument(workspaceId, file) {
  const form = new FormData(); form.append("file", file);
  return request(`/workspaces/${workspaceId}/documents`, { method: "POST", body: form });
}
export const listMemories = (workspaceId) => listAll(`/workspaces/${workspaceId}/memories`);
export const createMemory = (workspaceId, payload) => request(`/workspaces/${workspaceId}/memories`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const updateMemory = (workspaceId, memoryId, payload) => request(`/workspaces/${workspaceId}/memories/${memoryId}`, {
  method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const deleteMemory = (workspaceId, memoryId) => request(`/workspaces/${workspaceId}/memories/${memoryId}`, { method: "DELETE" });
export const listWorkspaceModules = (workspaceId) => request(`/workspaces/${workspaceId}/modules`);
export const listWorkspaceActivity = (workspaceId) => listAll(`/workspaces/${workspaceId}/activity`);
