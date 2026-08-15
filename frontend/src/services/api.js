const API = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(url, options = {}) {
  const response = await fetch(`${API}/v1${url}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error?.message || `Erreur ${response.status}`);
  return payload.data;
}

export const listWorkspaces = () => request("/workspaces");
export const createWorkspace = (payload) => request("/workspaces", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const getWorkspace = (workspaceId) => request(`/workspaces/${workspaceId}`);
export const updateWorkspace = (workspaceId, payload) => request(`/workspaces/${workspaceId}`, {
  method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
});
export const getOverview = (workspaceId) => request(`/workspaces/${workspaceId}/overview`);
export const listConversations = (workspaceId) => request(`/workspaces/${workspaceId}/conversations`);
export const createConversation = (workspaceId, title) => request(`/workspaces/${workspaceId}/conversations`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }),
});
export const getConversation = (workspaceId, conversationId) => request(`/workspaces/${workspaceId}/conversations/${conversationId}`);
export const sendWorkspaceMessage = (workspaceId, conversationId, content) => request(`/workspaces/${workspaceId}/conversations/${conversationId}/messages`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }),
});
export const listDocuments = (workspaceId) => request(`/workspaces/${workspaceId}/documents`);
export const deleteDocument = (workspaceId, documentId) => request(`/workspaces/${workspaceId}/documents/${documentId}`, { method: "DELETE" });
export async function uploadDocument(workspaceId, file) {
  const form = new FormData(); form.append("file", file);
  return request(`/workspaces/${workspaceId}/documents`, { method: "POST", body: form });
}
