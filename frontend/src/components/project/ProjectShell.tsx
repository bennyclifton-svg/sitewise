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

function SiteWiseMarkButton({ onShowWorkbench }: { onShowWorkbench: () => void }) {
  return (
    <button
      type="button"
      className="cockpit-sitewise-mark group relative hidden shrink-0 items-center justify-center lg:inline-flex"
      aria-label="SiteWise"
      title="SiteWise"
      onClick={onShowWorkbench}
    >
      <span className="text-center text-[1.04rem] font-semibold lowercase leading-[1.05] tracking-tight text-black transition-colors group-hover:text-black">
        site
        <br />
        wise
      </span>
    </button>
  );
}

function CockpitRibbonContent({
  projectTitle,
  projectAddress,
  onShowWorkbench,
}: {
  projectTitle?: string;
  projectAddress?: string;
  onShowWorkbench: () => void;
}) {
  return (
    <div className="flex min-w-0 items-center gap-5">
      <SiteWiseMarkButton onShowWorkbench={onShowWorkbench} />
      {projectTitle ? (
        <div className="flex min-w-0 flex-col gap-0.5 pl-2">
          <h1 className="truncate text-[1.3rem] font-semibold leading-[1.05] tracking-tight text-[var(--cockpit-sitewise-surface)]">
            {projectTitle}
          </h1>
          <p
            className={
              projectAddress
                ? "truncate text-[0.65rem] font-medium leading-[1.1] tracking-tight text-[var(--cockpit-sitewise-surface)]"
                : "truncate text-[0.65rem] font-medium leading-[1.1] tracking-tight text-[var(--cockpit-sitewise-surface)]/55"
            }
          >
            {projectAddress ?? "Site address TBC"}
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function ProjectShell({
  leftNav,
  children,
  repository,
  chatPanel,
  chatCollapsed = false,
  chatFullScreen = false,
  projectTitle,
  projectAddress,
  onShowWorkbench,
}: {
  leftNav: ReactNode;
  children: ReactNode;
  repository: ReactNode;
  chatPanel?: ReactNode;
  chatCollapsed?: boolean;
  chatFullScreen?: boolean;
  projectTitle?: string;
  projectAddress?: string;
  onShowWorkbench: () => void;
}) {
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
    ? `${leftWidth}px minmax(0, 1fr) ${repoWidth}px`
    : undefined;

  return (
    <div className="cockpit-page min-h-screen lg:h-screen lg:overflow-hidden">
      <div
        className={cn(
          "cockpit-shell grid min-h-screen max-lg:grid-cols-1 lg:h-full lg:min-h-0 lg:overflow-hidden",
        )}
        style={
          shellColumns
            ? {
                gridTemplateColumns: shellColumns,
                ...(largeLayout ? { gridTemplateRows: "auto 1fr" } : {}),
              }
            : undefined
        }
      >
        <aside className="project-left-nav relative min-w-0 overflow-hidden lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:h-full lg:min-h-0">
          <CockpitShellResizeProvider
            onResizeLeftPanel={largeLayout ? resizeLeftPanel : undefined}
          >
            {leftNav}
          </CockpitShellResizeProvider>
          {largeLayout ? (
            <CockpitPanelResizeHandle
              ariaLabel="Resize navigation panel"
              edge="end"
              onResize={resizeLeftPanel}
            />
          ) : null}
        </aside>

        <div className="cockpit-shell-header max-lg:hidden shrink-0 lg:col-span-2 lg:col-start-2 lg:row-start-1">
          <CockpitRibbonContent
            projectTitle={projectTitle}
            projectAddress={projectAddress}
            onShowWorkbench={onShowWorkbench}
          />
        </div>

        <main className="project-main-panel relative flex min-h-[48rem] min-w-0 flex-col overflow-hidden lg:col-start-2 lg:row-start-2 lg:h-full lg:min-h-0 lg:max-h-full">
          <div className="cockpit-shell-header shrink-0 lg:hidden">
            <CockpitRibbonContent
              projectTitle={projectTitle}
              projectAddress={projectAddress}
              onShowWorkbench={onShowWorkbench}
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col">
            {!chatFullScreen ? (
              <div className="cockpit-scroll min-h-0 flex-1 overflow-y-auto">{children}</div>
            ) : null}
            {chatPanel ? (
              <div
                className={cn(
                  "flex min-h-0 flex-col",
                  chatFullScreen && "flex-1",
                  chatCollapsed && "shrink-0 border-t border-border",
                  !chatFullScreen &&
                    !chatCollapsed &&
                    "flex-[1.35] border-t border-border",
                )}
              >
                {chatPanel}
              </div>
            ) : null}
          </div>
        </main>

        <aside className="project-side-panel relative min-w-0 overflow-hidden border-t lg:col-start-3 lg:row-start-2 lg:h-full lg:min-h-0 lg:border-t-0">
          <CockpitPanelResizeHandle
            ariaLabel="Resize documents panel"
            edge="start"
            onResize={resizeRepoPanel}
          />
          {repository}
        </aside>
      </div>
    </div>
  );
}
