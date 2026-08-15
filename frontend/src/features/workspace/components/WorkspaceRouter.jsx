import useWorkspaceContext from "../../../hooks/useWorkspaceContext";
import WorkspaceHome from "../../home/WorkspaceHome";
import ConversationsView from "../../chat/ConversationsView";
import DocumentsView from "../../documents/DocumentsView";

export default function WorkspaceRouter() {
  const { activeView } = useWorkspaceContext();
  if (activeView === "conversations") return <ConversationsView />;
  if (activeView === "knowledge") return <DocumentsView />;
  return <WorkspaceHome />;
}
