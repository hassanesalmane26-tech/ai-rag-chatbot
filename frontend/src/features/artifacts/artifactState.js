// Generation availability is server-owned; persisted results stay readable
// even if the provider is subsequently disabled.
export function artifactSurfaceState({ loading, error, images }) {
  if (loading) return "loading";
  if (error) return "error";
  return images.length ? "ready" : "empty";
}
