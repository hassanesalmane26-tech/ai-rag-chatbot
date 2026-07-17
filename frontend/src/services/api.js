const API = "/api";

async function request(url, options = {}) {
  const response = await fetch(`${API}${url}`, options);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
}

export function sendMessage(message) {
  return request("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });
}

export function getDocuments() {
  return request("/documents");
}

export function deleteDocument(filename) {
  return request(`/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
}
