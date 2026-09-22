import { useEffect, useRef, useState } from "react";
import { Download, Image, LoaderCircle, RefreshCw, X } from "lucide-react";
import { cancelImage, readImage, retryImage } from "../../services/api";
import { imageStatus, isImagePending } from "./imageState";

export default function ImageCard({ image, workspaceId, available, onChange, onEdit, onRegenerate }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);
  const container = useRef(null);
  useEffect(() => {
    if (!window.IntersectionObserver) { setVisible(true); return undefined; }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
    }, { rootMargin: "300px" });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let current = true;
    let objectUrl;
    setUrl(null); setError("");
    if (visible && image.status === "completed") readImage(workspaceId, image.id).then((blob) => {
      if (current) { objectUrl = URL.createObjectURL(blob); setUrl(objectUrl); }
    }).catch((err) => { if (current) setError(err.message); });
    return () => { current = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [workspaceId, image.id, image.status, visible]);
  async function action(operation) {
    if (busy) return;
    setBusy(true); setError("");
    try { await operation(workspaceId, image.id); onChange(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <section ref={container} className="nova-image" aria-label="Image Nova" aria-busy={busy}>
    <header><Image size={16} /><span>{imageStatus[image.status] || "État indisponible"}</span><small>{image.aspect_ratio}</small></header>
    {url ? <a href={url} target="_blank" rel="noreferrer" aria-label="Ouvrir l’image"><img src={url} width={image.width} height={image.height} alt={image.prompt} loading="lazy" /></a> : <p className="nova-image__state" style={image.status === "completed" ? { aspectRatio: `${image.width || 1}/${image.height || 1}` } : undefined} role="status">{isImagePending(image) && <LoaderCircle size={18} className="spin" />}{image.error || (image.status === "completed" ? "Chargement de l’image…" : imageStatus[image.status])}</p>}
    <p>{image.prompt}</p>
    {error && <p role="alert" className="inline-error">{error}</p>}
    <footer>
      {url && <a className="ds-button ds-button--secondary" href={url} download={`nova-${image.id}.png`}><Download size={15} /> Télécharger</a>}
      {image.status === "completed" && onEdit && <button type="button" disabled={!available} onClick={() => onEdit(image)}>Modifier</button>}
      {image.status === "completed" && onRegenerate && <button type="button" disabled={!available} onClick={() => onRegenerate(image)}>Variante</button>}
      {image.can_retry && <button type="button" disabled={busy || !available} onClick={() => action(retryImage)}><RefreshCw size={15} /> Réessayer</button>}
      {image.can_cancel && <button type="button" disabled={busy} onClick={() => action(cancelImage)}><X size={15} /> Annuler</button>}
    </footer>
  </section>;
}
