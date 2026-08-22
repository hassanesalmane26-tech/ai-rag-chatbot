import { lazy } from "react";
import { Activity, BookOpen, Brain, Files, House, MessagesSquare, Settings, Shapes } from "lucide-react";

export const workspaceModules = Object.freeze([
  { id: "home", label: "Accueil", icon: House, section: "primary", mobile: true, view: lazy(() => import("../../features/home/WorkspaceHome")) },
  { id: "conversations", label: "Nova", icon: MessagesSquare, section: "primary", mobile: true, view: lazy(() => import("../../features/chat/ConversationsView")) },
  { id: "knowledge", label: "Knowledge", icon: BookOpen, section: "primary", mobile: true, view: lazy(() => import("../../features/documents/DocumentsView")) },
  { id: "memory", label: "Memory", icon: Brain, section: "primary", mobile: true, view: lazy(() => import("../../features/memory/MemoryView")) },
  { id: "files", label: "Fichiers", icon: Files, section: "primary", view: lazy(() => import("../../features/files/FilesView")) },
  { id: "artifacts", label: "Artefacts", icon: Shapes, section: "primary", view: lazy(() => import("../../features/artifacts/ArtifactsView")) },
  { id: "activity", label: "Activité", icon: Activity, section: "secondary", view: lazy(() => import("../../features/activity/ActivityView")) },
  { id: "settings", label: "Paramètres", icon: Settings, section: "secondary", view: lazy(() => import("../../features/settings/SettingsView")) },
]);

export function workspaceModule(moduleId) {
  return workspaceModules.find((module) => module.id === moduleId) || workspaceModules[0];
}
