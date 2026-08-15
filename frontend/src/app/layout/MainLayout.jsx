import Sidebar from "../../components/Sidebar";
import Header from "../../components/navigation/Header";
import "./MainLayout.css";

export default function MainLayout({ children }) {
  return (
    <div className="main-layout">
      <Sidebar />

      <main className="main-content">
        <Header title="TRIDENT GENESIS" />
        {children}
      </main>
    </div>
  );
}
