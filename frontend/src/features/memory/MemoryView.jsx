import { useState } from "react";
import { Brain, LoaderCircle, Pencil, Power, RefreshCw, Trash2, X } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { validateMemory } from "./memoryState";
import useWorkspaceMemories from "./useWorkspaceMemories";

const kindLabels = { note: "Note", preference: "Préférence", fact: "Fait" };

export default function MemoryView() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspaceContext();
  const { memories, loading, mutationId, error, refresh, create, update, toggle, remove } = useWorkspaceMemories(activeWorkspaceId);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("note");
  const [validation, setValidation] = useState("");
  const [editingId, setEditingId] = useState(null);
  async function submit(event) {
    event.preventDefault();
    const issue = validateMemory(title, content);
    setValidation(issue);
    if (issue) return;
    const saved = editingId ? await update(editingId, { title: title.trim(), content: content.trim(), kind }) : await create({ title: title.trim(), content: content.trim(), kind });
    if (saved) {
      setTitle(""); setContent(""); setValidation(""); setEditingId(null);
    }
  }
  function edit(memory) { setEditingId(memory.id); setTitle(memory.title); setContent(memory.content); setKind(memory.kind); setValidation(""); document.getElementById("memory-title-input")?.focus(); }
  function cancelEdit() { setEditingId(null); setTitle(""); setContent(""); setKind("note"); setValidation(""); }
  function confirmRemove(memory) {
    if (window.confirm(`Supprimer définitivement « ${memory.title} » de la mémoire du Workspace ?`)) remove(memory.id);
  }
  return <section className="memory-view" aria-labelledby="memory-title">
    <header className="memory-header"><div><span>WORKSPACE MEMORY</span><h2 id="memory-title">Mémoire explicite</h2><p>Des repères contrôlés pour {activeWorkspace?.name}, jamais ajoutés silencieusement.</p></div><Brain size={34} /></header>
    <form className="memory-composer" onSubmit={submit}>
      <div><label htmlFor="memory-title-input">Titre</label><input id="memory-title-input" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} /></div>
      <div><label htmlFor="memory-kind">Type</label><select id="memory-kind" value={kind} onChange={(event) => setKind(event.target.value)}><option value="note">Note</option><option value="preference">Préférence</option><option value="fact">Fait</option></select></div>
      <div className="memory-composer__content"><label htmlFor="memory-content">Contenu</label><textarea id="memory-content" value={content} onChange={(event) => setContent(event.target.value)} maxLength={4000} rows={3} /></div>
      <button type="submit" disabled={Boolean(mutationId)}>{mutationId ? <LoaderCircle className="spin" size={17} /> : editingId ? <Pencil size={17} /> : <Brain size={17} />} {editingId ? "Enregistrer" : "Mémoriser"}</button>{editingId && <button className="memory-cancel" type="button" onClick={cancelEdit}><X size={16} /> Annuler</button>}
    </form>
    {(validation || error) && <div className="inline-error" role="alert">{validation || error}</div>}
    <div className="memory-section-heading"><div><span>MÉMOIRE DU WORKSPACE</span><h3>{memories.length} repère{memories.length === 1 ? "" : "s"}</h3></div><button type="button" onClick={refresh} aria-label="Actualiser la mémoire"><RefreshCw size={17} /></button></div>
    {loading ? <div className="document-loading" aria-live="polite"><LoaderCircle className="spin" /> Chargement de Memory…</div> : <div className="memory-grid">{memories.length === 0 ? <div className="empty-state"><Brain size={30} /><h3>Créez un premier repère</h3><p>Ajoutez ci-dessus uniquement les informations que Nova doit conserver dans ce Workspace.</p></div> : memories.map((memory) => <article className={`memory-card ${memory.active ? "is-active" : ""}`} key={memory.id}><div><span>{kindLabels[memory.kind] || memory.kind}</span><h3>{memory.title}</h3><p>{memory.content}</p></div><div className="memory-card__actions"><button type="button" onClick={() => edit(memory)} disabled={Boolean(mutationId)} aria-label={`Modifier ${memory.title}`}><Pencil size={16} /></button><button type="button" onClick={() => toggle(memory)} disabled={mutationId === memory.id} aria-label={`${memory.active ? "Désactiver" : "Activer"} ${memory.title}`}><Power size={16} /></button><button type="button" onClick={() => confirmRemove(memory)} disabled={mutationId === memory.id} aria-label={`Supprimer ${memory.title}`}><Trash2 size={16} /></button></div></article>)}</div>}
  </section>;
}
