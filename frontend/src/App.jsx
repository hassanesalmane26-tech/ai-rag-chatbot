import { WorkspaceProvider } from "./context/WorkspaceContext";

import "./App.css";

import MainLayout from "./app/layout/MainLayout";
import Workspace from "./features/workspace/components/Workspace";
import WorkspaceRouter from "./features/workspace/components/WorkspaceRouter";


function WorkspaceContent() {

  return (
    <Workspace title="Workspace Intelligent">
      <WorkspaceRouter />
    </Workspace>
  );
}

export default function App() {
  return (
    <WorkspaceProvider>
      <MainLayout>
        <WorkspaceContent />
      </MainLayout>
    </WorkspaceProvider>
  );
}
