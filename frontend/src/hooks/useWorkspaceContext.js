import { useContext } from "react";
import { WorkspaceContext } from "../context/workspaceContext";

export default function useWorkspaceContext() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspaceContext must be used inside WorkspaceProvider");
  return value;
}
