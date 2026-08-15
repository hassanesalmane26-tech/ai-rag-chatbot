import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { deleteDocument, listDocuments, uploadDocument } from "../../services/api";

export default function DocumentsView() {
  const { activeWorkspaceId } = useWorkspaceContext();
  const [documents, setDocuments] = useState([]);
  const [pendingWorkspaceId, setPendingWorkspaceId] = useState(null);
  const [error, setError] = useState("");
  const activeWorkspaceRef = useRef(activeWorkspaceId);
  const requestVersionRef = useRef(0);

  useEffect(() => {
    activeWorkspaceRef.current = activeWorkspaceId;
  }, [activeWorkspaceId]);

  const refresh = useCallback(async () => {
    if (!activeWorkspaceId) {
      setDocuments([]);
      return;
    }
    const request = ++requestVersionRef.current;
    const values = await listDocuments(activeWorkspaceId);
    if (request !== requestVersionRef.current || activeWorkspaceRef.current !== activeWorkspaceId) return;
    setDocuments(values);
  }, [activeWorkspaceId]);

  useEffect(() => {
    setDocuments([]);
    setError("");
    refresh().catch((err) => {
      if (activeWorkspaceRef.current === activeWorkspaceId) setError(err.message);
    });
    return () => { requestVersionRef.current += 1; };
  }, [activeWorkspaceId, refresh]);

  async function addFile(event) {
    const file = event.target.files?.[0];
    const workspaceId = activeWorkspaceId;
    if (!file || !workspaceId) return;
    setPendingWorkspaceId(workspaceId);
    setError("");
    try {
      const document = await uploadDocument(workspaceId, file);
      if (activeWorkspaceRef.current === workspaceId) setDocuments((items) => [document, ...items]);
    } catch (err) {
      if (activeWorkspaceRef.current === workspaceId) setError(err.message);
    } finally {
      setPendingWorkspaceId((current) => current === workspaceId ? null : current);
      event.target.value = "";
    }
  }

  async function remove(document) {
    const workspaceId = activeWorkspaceId;
    if (!workspaceId || !window.confirm(`Supprimer ${document.display_name} ?`)) return;
    setPendingWorkspaceId(workspaceId);
    setError("");
    try {
      await deleteDocument(workspaceId, document.id);
      if (activeWorkspaceRef.current === workspaceId) setDocuments((items) => items.filter((item) => item.id !== document.id));
    } catch (err) {
      if (activeWorkspaceRef.current === workspaceId) setError(err.message);
    } finally {
      setPendingWorkspaceId((current) => current === workspaceId ? null : current);
    }
  }

  const busy = pendingWorkspaceId === activeWorkspaceId;
  return <section className="knowledge-view"><header><div><span>KNOWLEDGE</span><h2>Connaissances du Workspace</h2><p>Les documents importés sont disponibles pour les conversations de cet espace.</p></div><label className="upload-action"><Upload size={17} /> {busy ? "Indexation…" : "Importer"}<input type="file" accept=".pdf,.txt,.docx" onChange={addFile} disabled={busy} /></label></header>{error && <p className="inline-error" role="alert">{error}</p>}<div className="document-grid">{documents.length === 0 ? <div className="empty-state"><FileText size={30} /><h3>Knowledge est vide</h3><p>Importez un document pour enrichir ce Workspace.</p></div> : documents.map((document) => <article key={document.id} className="document-card"><FileText size={24} /><div><strong>{document.display_name}</strong><span>{Math.ceil(document.size_bytes / 1024)} Ko · {document.status === "indexed" ? "Prêt pour Nova" : document.status}</span></div><button type="button" onClick={() => remove(document)} aria-label={`Supprimer ${document.display_name}`} disabled={busy}><Trash2 size={16} /></button></article>)}</div></section>;
}
