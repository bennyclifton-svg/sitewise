import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useSyncExternalStore, useState, type ReactNode } from "react";

import { CockpitPanelResizeHandle } from "@/components/project/CockpitPanelResizeHandle";
import { CockpitShellResizeProvider } from "@/components/project/CockpitShellResizeProvider";
import {
  clampPanelWidth,
  COCKPIT_LEFT_PANEL_DEFAULT_WIDTH,
  COCKPIT_LEFT_PANEL_MAX_WIDTH,
  COCKPIT_LEFT_PANEL_MIN_WIDTH,
  COCKPIT_LEFT_PANEL_WIDTH_KEY,
  COCKPIT_REPO_PANEL_DEFAULT_WIDTH,
  COCKPIT_REPO_PANEL_MAX_WIDTH,
  COCKPIT_REPO_PANEL_MIN_WIDTH,
  COCKPIT_REPO_PANEL_WIDTH_KEY,
  readStoredPanelWidth,
  writeStoredPanelWidth,
} from "@/components/project/cockpitShellLayout";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function subscribeToLargeLayout(onStoreChange: () => void) {
  const mediaQuery = window.matchMedia("(min-width: 1024px)");
  mediaQuery.addEventListener("change", onStoreChange);
  return () => mediaQuery.removeEventListener("change", onStoreChange);
}

function getLargeLayoutSnapshot() {
  return window.matchMedia("(min-width: 1024px)").matches;
}

function getLargeLayoutServerSnapshot() {
  return false;
}

export function ProjectShell({
  leftNav,
  children,
  repository,
  onShowWorkbench,
}: {
  leftNav: ReactNode;
  children: ReactNode;
  repository: ReactNode;
  onShowWorkbench: () => void;
}) {
  const [repoCollapsed, setRepoCollapsed] = useState(false);
  const [leftWidth, setLeftWidth] = useState(() =>
    readStoredPanelWidth(COCKPIT_LEFT_PANEL_WIDTH_KEY, COCKPIT_LEFT_PANEL_DEFAULT_WIDTH),
  );
  const [repoWidth, setRepoWidth] = useState(() =>
    readStoredPanelWidth(COCKPIT_REPO_PANEL_WIDTH_KEY, COCKPIT_REPO_PANEL_DEFAULT_WIDTH),
  );
  const largeLayout = useSyncExternalStore(
    subscribeToLargeLayout,
    getLargeLayoutSnapshot,
    getLargeLayoutServerSnapshot,
  );

  function resizeLeftPanel(deltaX: number) {
    setLeftWidth((current) => {
      const next = clampPanelWidth(
        current + deltaX,
        COCKPIT_LEFT_PANEL_MIN_WIDTH,
        COCKPIT_LEFT_PANEL_MAX_WIDTH,
      );
      writeStoredPanelWidth(COCKPIT_LEFT_PANEL_WIDTH_KEY, next);
      return next;
    });
  }

  function resizeRepoPanel(deltaX: number) {
    setRepoWidth((current) => {
      const next = clampPanelWidth(
        current - deltaX,
        COCKPIT_REPO_PANEL_MIN_WIDTH,
        COCKPIT_REPO_PANEL_MAX_WIDTH,
      );
      writeStoredPanelWidth(COCKPIT_REPO_PANEL_WIDTH_KEY, next);
      return next;
    });
  }

  const shellColumns = largeLayout
    ? repoCollapsed
      ? `${leftWidth}px minmax(0, 1fr) 0px`
      : `${leftWidth}px minmax(0, 1fr) ${repoWidth}px`
    : undefined;

  return (
    <div className="cockpit-page min-h-screen lg:h-screen lg:overflow-hidden">
      <div
        className={cn(
          "cockpit-shell grid min-h-screen max-lg:grid-cols-1 lg:h-full lg:min-h-0 lg:overflow-hidden",
          repoCollapsed && "cockpit-shell--repo-collapsed max-lg:grid-cols-1",
        )}
        style={shellColumns ? { gridTemplateColumns: shellColumns } : undefined}
      >
        <aside className="project-left-nav relative min-w-0 overflow-hidden border-b lg:h-full lg:min-h-0 lg:border-b-0">
          <CockpitShellResizeProvider
            onResizeLeftPanel={largeLayout ? resizeLeftPanel : undefined}
          >
            {leftNav}
          </CockpitShellResizeProvider>
          {largeLayout ? (
            <CockpitPanelResizeHandle
              ariaLabel="Resize chat rail"
              edge="end"
              onResize={resizeLeftPanel}
            />
          ) : null}
        </aside>

        <main className="project-main-panel relative flex min-h-[48rem] min-w-0 flex-col overflow-hidden lg:h-full lg:min-h-0 lg:max-h-full">
          <div className="cockpit-shell-header shrink-0">
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="group relative hidden px-4 py-1.5 lg:inline"
                onClick={onShowWorkbench}
              >
                <span
                  aria-hidden
                  className="absolute inset-0 border border-[var(--gr-300)] [clip-path:polygon(0.5rem_0,100%_0,calc(100%-0.5rem)_100%,0_100%)] transition-colors group-hover:border-[var(--gr-500)]"
                />
                <span className="relative block text-[1.125rem] font-medium leading-none text-[var(--gr-600)] transition-colors group-hover:text-[var(--gr-900)]">
                  SiteWise
                </span>
              </button>
              <div className="ml-auto flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="hidden text-[var(--gr-700)] hover:bg-black/5 hover:text-[var(--gr-900)] lg:inline-flex"
                  aria-label={
                    repoCollapsed ? "Expand document repository" : "Collapse document repository"
                  }
                  onClick={() => setRepoCollapsed((current) => !current)}
                >
                  {repoCollapsed ? (
                    <PanelRightOpen className="size-4" aria-hidden />
                  ) : (
                    <PanelRightClose className="size-4" aria-hidden />
                  )}
                </Button>
              </div>
            </div>
          </div>
          <div className="cockpit-scroll min-h-0 flex-1 overflow-y-auto">{children}</div>
        </main>

        <aside
          className={cn(
            "project-side-panel relative min-w-0 overflow-hidden border-t lg:h-full lg:min-h-0 lg:border-t-0",
            repoCollapsed && "cockpit-panel-collapsed max-lg:hidden",
          )}
        >
          {!repoCollapsed ? (
            <CockpitPanelResizeHandle
              ariaLabel="Resize documents panel"
              edge="start"
              onResize={resizeRepoPanel}
            />
          ) : null}
          {repository}
        </aside>
      </div>
    </div>
  );
}
