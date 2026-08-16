import { lazy } from "react";
import { BookOpen, Brain, House, MessagesSquare } from "lucide-react";

export const workspaceModules = Object.freeze([
  { id: "home", label: "Accueil", icon: House, view: lazy(() => import("../../features/home/WorkspaceHome")) },
  { id: "conversations", label: "Conversations", icon: MessagesSquare, view: lazy(() => import("../../features/chat/ConversationsView")) },
  { id: "knowledge", label: "Knowledge", icon: BookOpen, view: lazy(() => import("../../features/documents/DocumentsView")) },
  { id: "memory", label: "Memory", icon: Brain, view: lazy(() => import("../../features/memory/MemoryView")) },
]);

export function workspaceModule(moduleId) {
  return workspaceModules.find((module) => module.id === moduleId) || workspaceModules[0];
}
