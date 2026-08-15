import Sidebar from "../../components/Sidebar";
import Header from "../../components/navigation/Header";
import VisualEnvironment from "../../components/visual/VisualEnvironment";
import "./MainLayout.css";

export default function MainLayout({ children }) {
  return (
    <div className="main-layout">
      <VisualEnvironment />
      <Sidebar />

      <main className="main-content">
        <Header />
        {children}
      </main>
    </div>
  );
}
