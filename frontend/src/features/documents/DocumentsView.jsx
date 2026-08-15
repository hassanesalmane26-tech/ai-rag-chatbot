import { useCallback, useEffect, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { deleteDocument, listDocuments, uploadDocument } from "../../services/api";

export default function DocumentsView() {
  const { activeWorkspaceId } = useWorkspaceContext();
  const [documents, setDocuments] = useState([]); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const refresh = useCallback(async () => { if (!activeWorkspaceId) return; setDocuments(await listDocuments(activeWorkspaceId)); }, [activeWorkspaceId]);
  useEffect(() => { refresh().catch((err) => setError(err.message)); }, [refresh]);
  async function addFile(event) { const file = event.target.files?.[0]; if (!file) return; setBusy(true); setError(""); try { const document = await uploadDocument(activeWorkspaceId, file); setDocuments((items) => [document, ...items]); } catch (err) { setError(err.message); } finally { setBusy(false); event.target.value = ""; } }
  async function remove(document) { if (!window.confirm(`Supprimer ${document.display_name} ?`)) return; await deleteDocument(activeWorkspaceId, document.id); setDocuments((items) => items.filter((item) => item.id !== document.id)); }
  return <section className="knowledge-view"><header><div><span>KNOWLEDGE</span><h2>Connaissances du Workspace</h2><p>Les documents importés sont disponibles pour les conversations de cet espace.</p></div><label className="upload-action"><Upload size={17} /> {busy ? "Indexation…" : "Importer"}<input type="file" accept=".pdf,.txt,.docx" onChange={addFile} disabled={busy} /></label></header>{error && <p className="inline-error" role="alert">{error}</p>}<div className="document-grid">{documents.length === 0 ? <div className="empty-state"><FileText size={30} /><h3>Knowledge est vide</h3><p>Importez un document pour enrichir ce Workspace.</p></div> : documents.map((document) => <article key={document.id} className="document-card"><FileText size={24} /><div><strong>{document.display_name}</strong><span>{Math.ceil(document.size_bytes / 1024)} Ko · {document.status === "indexed" ? "Prêt pour Nova" : document.status}</span></div><button onClick={() => remove(document)} aria-label={`Supprimer ${document.display_name}`}><Trash2 size={16} /></button></article>)}</div></section>;
}
