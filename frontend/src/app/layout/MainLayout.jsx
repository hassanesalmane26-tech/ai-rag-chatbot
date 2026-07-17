import Sidebar from "../../components/Sidebar";

export default function MainLayout({ children }) {
  return (
    <div className="layout">
      <Sidebar />

      <main className="main">
        {children}
      </main>
    </div>
  );
}
