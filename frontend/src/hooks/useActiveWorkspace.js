import useWorkspaceContext from "./useWorkspaceContext";

export default function useActiveWorkspace() {
  const { activeWorkspace, activeWorkspaceId, state } = useWorkspaceContext();
  return { activeWorkspace, activeWorkspaceId, state };
}
