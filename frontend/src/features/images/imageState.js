export const imageStatus = Object.freeze({
  queued: "En attente", generating: "Création en cours", completed: "Image créée",
  failed: "Création interrompue", cancelled: "Création annulée",
});
export const isImagePending = (item) => ["queued", "generating"].includes(item.status);
export function validateImageFile(file) {
  if (!file) return "";
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) return "Choisissez une image PNG, JPEG ou WebP.";
  if (file.size > 12 * 1024 * 1024) return "L’image doit faire moins de 12 Mo.";
  return "";
}
