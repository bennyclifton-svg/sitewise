export type ProjectChatLayoutState = {
  contentTakesPrecedence: boolean;
  chatCollapsed: boolean;
  chatFullScreen: boolean;
};

export function projectChatLayoutState({
  activeView,
  chatPanelCollapsed,
  hasTenderOutlet = false,
}: {
  activeView: string;
  chatPanelCollapsed: boolean;
  hasTenderOutlet?: boolean;
}): ProjectChatLayoutState {
  const contentTakesPrecedence = activeView !== "workbench" && !hasTenderOutlet;
  const chatOnWorkbench = activeView === "workbench" || hasTenderOutlet;

  return {
    contentTakesPrecedence,
    chatCollapsed:
      contentTakesPrecedence || (chatOnWorkbench && chatPanelCollapsed),
    // Open chat always owns the middle panel; no compact strip in between.
    chatFullScreen: chatOnWorkbench && !chatPanelCollapsed,
  };
}
