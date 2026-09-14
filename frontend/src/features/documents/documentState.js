export const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024;
export const ACCEPTED_DOCUMENT_EXTENSIONS = ["pdf", "txt", "docx"];

export const DOCUMENT_STATUS = Object.freeze({
  uploaded: { label: "Accepté", tone: "pending", retryable: false },
  pending_scan: { label: "En attente du contrôle", tone: "pending", retryable: false },
  scanning: { label: "Contrôle de sécurité", tone: "processing", retryable: false },
  scan_failed: { label: "Contrôle indisponible", tone: "failed", retryable: true },
  rejected: { label: "Rejeté", tone: "rejected", retryable: false },
  pending_processing: { label: "En attente d’indexation", tone: "pending", retryable: false },
  processing: { label: "Indexation", tone: "processing", retryable: false },
  indexed: { label: "Prêt", tone: "ready", retryable: false },
  processing_failed: { label: "Indexation échouée", tone: "failed", retryable: true },
  deleting: { label: "Suppression", tone: "processing", retryable: false },
  delete_failed: { label: "Suppression incomplète", tone: "failed", retryable: false },
});

export function documentStatus(status) {
  return DOCUMENT_STATUS[status] || { label: "État inconnu", tone: "failed", retryable: false };
}

export function acceptsDocumentResult(activeWorkspaceId, requestWorkspaceId) {
  return Boolean(requestWorkspaceId) && activeWorkspaceId === requestWorkspaceId;
}

export function validateDocumentFile(file) {
  if (!file) return "Sélectionnez un document à importer.";
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!ACCEPTED_DOCUMENT_EXTENSIONS.includes(extension)) {
    return "Format non pris en charge. Utilisez un fichier PDF, TXT ou DOCX.";
  }
  if (file.size === 0) return "Le document est vide.";
  if (file.size > MAX_DOCUMENT_BYTES) return "Le document dépasse la limite de 20 Mo.";
  return null;
}

export function prependDocument(documents, document) {
  return [document, ...documents.filter((item) => item.id !== document.id)];
}

export function removeDocumentById(documents, documentId) {
  return documents.filter((document) => document.id !== documentId);
}

export function formatDocumentSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "Taille inconnue";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
}

export function documentStatusLabel(status) {
  return documentStatus(status).label;
}
