export default function Workspace({
  title = "Workspace",
  children,
}) {
  return (
    <section className="workspace">
      <div className="workspace-header">
        <h2>{title}</h2>
      </div>

      <div className="workspace-container">
        {children}
      </div>
    </section>
  );
}
