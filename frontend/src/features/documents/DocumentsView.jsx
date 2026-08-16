import { useRef, useState } from "react";
import { AlertTriangle, FileText, LoaderCircle, RefreshCw, ShieldCheck, Trash2, Upload } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import {
  documentStatusLabel,
  formatDocumentSize,
} from "./documentState";
import useWorkspaceDocuments from "./useWorkspaceDocuments";

export default function DocumentsView() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspaceContext();
  const { documents, loading, uploading, deletingId, retryingId, error, refresh, uploadDocument, deleteDocument, retryDocument } = useWorkspaceDocuments(activeWorkspaceId);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  async function importFile(file) {
    const imported = await uploadDocument(file);
    if (imported && inputRef.current) inputRef.current.value = "";
  }

  function chooseFile(event) {
    const file = event.target.files?.[0];
    if (file) importFile(file);
  }

  function dropFile(event) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) importFile(file);
  }

  function remove(document) {
    if (window.confirm(`Supprimer définitivement « ${document.display_name} » de ce Workspace ?`)) {
      deleteDocument(document.id);
    }
  }

  return <section className="knowledge-view" aria-labelledby="knowledge-title">
    <header className="knowledge-header">
      <div><span>KNOWLEDGE ENGINE</span><h2 id="knowledge-title">Connaissances du Workspace</h2><p>Une bibliothèque privée et contextualisée pour {activeWorkspace?.name}.</p></div>
      <div className="knowledge-summary" aria-label={`${documents.length} documents dans le Workspace`}><strong>{documents.length}</strong><span>source{documents.length === 1 ? "" : "s"} active{documents.length === 1 ? "" : "s"}</span></div>
    </header>

    <div className={`document-dropzone ${dragging ? "is-dragging" : ""}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }} onDrop={dropFile}>
      <div className="document-dropzone__icon" aria-hidden="true">{uploading ? <LoaderCircle className="spin" /> : <Upload />}</div>
      <div><h3>{uploading ? "Indexation dans le Workspace…" : "Ajoutez une source à votre Workspace"}</h3><p>PDF, TXT ou DOCX · 20 Mo maximum</p></div>
      <label className="upload-action">{uploading ? "Traitement…" : "Choisir un document"}<input ref={inputRef} type="file" accept=".pdf,.txt,.docx" onChange={chooseFile} disabled={uploading} /></label>
    </div>

    {error && <div className="inline-error document-error" role="alert"><AlertTriangle size={18} /><span>{error}</span><button type="button" onClick={refresh} disabled={loading}>Réessayer</button></div>}

    <div className="document-section-heading"><div><span>BIBLIOTHÈQUE DU WORKSPACE</span><h3>Sources disponibles</h3></div>{!loading && documents.length > 0 && <button type="button" className="document-refresh" onClick={refresh} aria-label="Actualiser les documents"><RefreshCw size={16} /> Actualiser</button>}</div>

    {loading ? <div className="document-loading" aria-live="polite"><LoaderCircle className="spin" /><span>Synchronisation de Knowledge…</span></div> : <div className="document-grid">{documents.length === 0 ? <div className="empty-state"><FileText size={30} /><h3>Knowledge est vide</h3><p>Importez une source pour donner à Nova le contexte de ce Workspace.</p></div> : documents.map((document) => <article key={document.id} className={`document-card document-card--${document.status}`}>
      <div className="document-card__icon"><FileText size={22} /></div>
      <div className="document-card__body"><strong title={document.display_name}>{document.display_name}</strong><span>{formatDocumentSize(document.size_bytes)} · {documentStatusLabel(document.status)}</span>{document.error_message && <small>{document.error_message}</small>}</div>
      <div className="document-card__status" title={documentStatusLabel(document.status)}>{document.status === "failed" ? <AlertTriangle size={15} /> : <ShieldCheck size={15} />}<span>{document.status === "indexed" ? "INDEXÉ" : document.status.toUpperCase()}</span></div>
      <div className="document-card__actions">
        {document.status === "failed" && <button className="document-card__retry" type="button" onClick={() => retryDocument(document.id)} aria-label={`Relancer l’indexation de ${document.display_name}`} disabled={Boolean(retryingId) || Boolean(deletingId)}>{retryingId === document.id ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}</button>}
        <button className="document-card__delete" type="button" onClick={() => remove(document)} aria-label={`Supprimer ${document.display_name}`} disabled={Boolean(deletingId) || Boolean(retryingId) || uploading}>{deletingId === document.id ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}</button>
      </div>
    </article>)}</div>}
  </section>;
}
