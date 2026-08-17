import { lazy, Suspense } from "react";
import { WorkspaceProvider } from "./context/WorkspaceContext";
import { SessionProvider } from "./context/SessionContext";
import useSessionContext from "./hooks/useSessionContext";
import EntryExperience from "./features/session/EntryExperience";
import { canEnterWorkspace } from "./features/session/sessionState";

import "./App.css";

import MainLayout from "./app/layout/MainLayout";
import Workspace from "./features/workspace/components/Workspace";
import WorkspaceRouter from "./features/workspace/components/WorkspaceRouter";

const ConsentPage = lazy(() => import("./features/consent/ConsentPage"));


function WorkspaceContent() {
  return (
    <Workspace>
      <WorkspaceRouter />
    </Workspace>
  );
}

function SessionGate() {
  const { state, session } = useSessionContext();
  if (!canEnterWorkspace(state, session)) return <EntryExperience />;
  return <WorkspaceProvider><MainLayout><WorkspaceContent /></MainLayout></WorkspaceProvider>;
}

export default function App() {
  if (window.location.pathname === "/oauth/consent") {
    return <Suspense fallback={<main className="consent-shell" aria-live="polite">Chargement de l’autorisation…</main>}><ConsentPage /></Suspense>;
  }
  return (
    <SessionProvider>
      <SessionGate />
    </SessionProvider>
  );
}
