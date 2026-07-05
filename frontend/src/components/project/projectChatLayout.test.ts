import { describe, expect, it } from "vitest";

import { projectChatLayoutState } from "@/components/project/projectChatLayout";

describe("projectChatLayoutState", () => {
  it("collapses chat while a draft or document takes precedence", () => {
    expect(
      projectChatLayoutState({
        activeView: "draft",
        chatPanelCollapsed: false,
      }),
    ).toEqual({
      contentTakesPrecedence: true,
      chatCollapsed: true,
      chatFullScreen: false,
    });
  });

  it("lets chat take the middle panel on the workbench after the user submits", () => {
    expect(
      projectChatLayoutState({
        activeView: "workbench",
        chatPanelCollapsed: false,
      }),
    ).toEqual({
      contentTakesPrecedence: false,
      chatCollapsed: false,
      chatFullScreen: true,
    });
  });

  it("keeps the workbench visible while chat is collapsed", () => {
    expect(
      projectChatLayoutState({
        activeView: "workbench",
        chatPanelCollapsed: true,
      }),
    ).toEqual({
      contentTakesPrecedence: false,
      chatCollapsed: true,
      chatFullScreen: false,
    });
  });
});
