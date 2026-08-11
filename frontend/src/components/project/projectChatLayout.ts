export type ProjectChatLayoutState = {
  contentTakesPrecedence: boolean;
  chatCollapsed: boolean;
  chatFullScreen: boolean;
};

export function projectChatLayoutState({
  activeView,
  chatPanelCollapsed,
  hasTenderOutlet = false,
  /**
   * Keep the middle-panel artefact visible when chat expands (split layout
   * instead of chat full-screen). Used by Cost Plan so a submitted agent turn
   * can show conversation history without hiding the grid.
   */
  preferSplitChat = false,
}: {
  activeView: string;
  chatPanelCollapsed: boolean;
  hasTenderOutlet?: boolean;
  preferSplitChat?: boolean;
}): ProjectChatLayoutState {
  const contentTakesPrecedence = activeView !== "workbench" && !hasTenderOutlet;
  const chatOnWorkbench = activeView === "workbench" || hasTenderOutlet;
  const chatCanTakeMiddle = chatOnWorkbench && !preferSplitChat;

  return {
    contentTakesPrecedence,
    chatCollapsed:
      contentTakesPrecedence || (chatOnWorkbench && chatPanelCollapsed),
    chatFullScreen: chatCanTakeMiddle && !chatPanelCollapsed,
  };
}
