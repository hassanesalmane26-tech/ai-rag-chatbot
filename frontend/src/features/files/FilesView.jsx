import { Download, FileText, Files, LoaderCircle, RefreshCw } from "lucide-react";
import { useState } from "react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { downloadDocument } from "../../services/api";
import { documentStatusLabel, formatDocumentSize } from "../documents/documentState";
import useWorkspaceDocuments from "../documents/useWorkspaceDocuments";

export default function FilesView() {
  const { activeWorkspace, activeWorkspaceId, setActiveView } = useWorkspaceContext();
  const { documents, loading, error, refresh } = useWorkspaceDocuments(activeWorkspaceId);
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadError, setDownloadError] = useState("");

  async function download(document) {
    setDownloadingId(document.id); setDownloadError("");
    try {
      const blob = await downloadDocument(activeWorkspaceId, document.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url; anchor.download = document.display_name; anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setDownloadError(cause.message);
    } finally {
      setDownloadingId(null);
    }
  }

  return <section className="product-view files-view" aria-labelledby="files-title">
    <header className="product-view__header"><div><span>WORKSPACE FILES</span><h2 id="files-title">Files</h2><p>Les originaux privés utilisés par Knowledge dans {activeWorkspace?.name}.</p></div><button type="button" className="view-refresh" onClick={refresh} aria-label="Actualiser Files"><RefreshCw size={17} /></button></header>
    {(error || downloadError) && <div className="inline-error" role="alert"><span>{downloadError || error}</span><button type="button" onClick={refresh}>Réessayer</button></div>}
    {loading ? <div className="document-loading" aria-live="polite"><LoaderCircle className="spin" /> Synchronisation des fichiers…</div> : documents.length === 0 ? <div className="empty-state"><Files size={30} /><h3>Aucun fichier dans ce Workspace</h3><p>Ajoutez une source dans Knowledge pour conserver son original dans Files.</p><button type="button" onClick={() => setActiveView("knowledge")}>Ajouter via Knowledge</button></div> : <div className="file-table" role="list">{documents.map((document) => <article key={document.id} className="file-row" role="listitem"><div className="file-row__icon"><FileText size={20} /></div><div className="file-row__body"><strong>{document.display_name}</strong><span>{formatDocumentSize(document.size_bytes)} · {document.media_type} · {documentStatusLabel(document.status)}</span></div><span className={`file-row__status file-row__status--${document.status}`}>{document.status === "indexed" ? "KNOWLEDGE" : documentStatusLabel(document.status)}</span><button type="button" onClick={() => download(document)} disabled={downloadingId === document.id} aria-label={`Télécharger ${document.display_name}`}>{downloadingId === document.id ? <LoaderCircle className="spin" size={17} /> : <Download size={17} />}</button></article>)}</div>}
  </section>;
}
