import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ProjectShell({
  leftNav,
  children,
  repository,
  chatBar,
  onShowWorkbench,
}: {
  leftNav: ReactNode;
  children: ReactNode;
  repository: ReactNode;
  chatBar: ReactNode;
  onShowWorkbench: () => void;
}) {
  const [repoCollapsed, setRepoCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-secondary">
      <div
        className={cn(
          "cockpit-shell grid min-h-screen max-lg:grid-cols-1",
          repoCollapsed && "cockpit-shell--repo-collapsed max-lg:grid-cols-1",
        )}
      >
        <aside className="min-w-0 border-b bg-card lg:border-r lg:border-b-0">
          {leftNav}
        </aside>

        <main className="relative flex min-h-[48rem] min-w-0 flex-col bg-background">
          <div className="flex shrink-0 items-center gap-1 border-b px-2 py-1.5">
            <button
              type="button"
              className="hidden text-xs text-muted-foreground transition-colors hover:text-foreground lg:inline"
              onClick={onShowWorkbench}
            >
              Workbench
            </button>
            <div className="ml-auto flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="hidden lg:inline-flex"
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
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
          {chatBar}
        </main>

        <aside
          className={cn(
            "min-w-0 border-t bg-background lg:border-t-0 lg:border-l",
            repoCollapsed && "cockpit-panel-collapsed max-lg:hidden",
          )}
        >
          {repository}
        </aside>
      </div>
    </div>
  );
}
