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
  const chatCanTakeMiddle = activeView === "workbench" || hasTenderOutlet;

  return {
    contentTakesPrecedence,
    chatCollapsed:
      contentTakesPrecedence || (chatCanTakeMiddle && chatPanelCollapsed),
    chatFullScreen: chatCanTakeMiddle && !chatPanelCollapsed,
  };
}
