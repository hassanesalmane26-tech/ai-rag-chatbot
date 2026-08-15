export default function Workspace({
  children,
}) {
  return (
    <section className="workspace">
      <div className="workspace-container">
        {children}
      </div>
    </section>
  );
}
