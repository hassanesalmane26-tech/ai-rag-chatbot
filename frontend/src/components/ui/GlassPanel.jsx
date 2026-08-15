export default function GlassPanel({ as: Component = "section", className = "", elevated = false, ...props }) {
  return <Component className={`ds-glass-panel ${elevated ? "ds-glass-panel--elevated" : ""} ${className}`.trim()} {...props} />;
}
